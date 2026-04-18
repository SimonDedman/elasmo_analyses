"""Confidence-scored pair evaluator (v8).

Given two PdfFeatures rows, fuse multiple signals into a decision with
a confidence in [0, 1] and a list of signals that drove the call.

Decision vocabulary (stable — downstream code relies on these strings):
  - same_content     : byte-identical; delete either
  - keep_1 / keep_2  : duplicate; keep the named side
  - rename_sm        : smaller side is supplementary material
  - is_corrigendum   : smaller side is a corrigendum/erratum/reply
  - is_book          : both sides are books (do not treat as a duplicate pair)
  - is_chapter       : one side is a chapter extracted from the other (book)
  - distinct         : confirmed not a duplicate
  - manual           : insufficient signal
  - file_missing     : one or both files absent

Confidence bands:
  >= 0.85   trust for auto-delete
  0.55 - 0.85 review queue
  < 0.55   treat as distinct or manual
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

import imagehash
import numpy as np
from datasketch import MinHash
from rapidfuzz import fuzz

from .schema import PdfFeatures


AUTO_THRESHOLD = 0.85
REVIEW_THRESHOLD = 0.55


@dataclass
class PairDecision:
    decision: str
    confidence: float
    rule: str
    reason: str
    signals: list[str] = field(default_factory=list)
    keep: Optional[int] = None  # 1 or 2 when decision is keep_*

    def as_dict(self) -> dict:
        return {
            "decision": self.decision,
            "confidence": round(self.confidence, 3),
            "rule": self.rule,
            "reason": self.reason,
            "signals": "; ".join(self.signals),
            "keep": self.keep,
        }


# ---------- helper signals ----------

def _phash_distance(a: Optional[str], b: Optional[str]) -> Optional[int]:
    if not a or not b or len(a) != len(b):
        return None
    try:
        ha = imagehash.hex_to_hash(a)
        hb = imagehash.hex_to_hash(b)
        return ha - hb
    except Exception:
        return None


def _minhash_jaccard(b1: Optional[bytes], b2: Optional[bytes]) -> Optional[float]:
    if not b1 or not b2 or len(b1) != len(b2):
        return None
    try:
        m1 = MinHash(num_perm=128, hashvalues=np.frombuffer(b1, dtype="<u4"))
        m2 = MinHash(num_perm=128, hashvalues=np.frombuffer(b2, dtype="<u4"))
        return m1.jaccard(m2)
    except Exception:
        return None


def _tlsh_distance(a: Optional[str], b: Optional[str]) -> Optional[int]:
    if not a or not b:
        return None
    try:
        import tlsh
        return tlsh.diff(a, b)
    except Exception:
        return None


_SM_RE = re.compile(
    r"\b(supporting\s+information|supplementary\s+(material|information|data|"
    r"table|figure|methods?|results?|text)|electronic\s+supplementary)\b"
)
_CORRIG_RE = re.compile(r"\b(corrigend|errat|correction\s+to|retraction\s+of|reply\s+to|"
                         r"response\s+to|comment\s+on)\b")
_CR_SM_TYPES = {"dataset", "peer-review", "grant", "report"}
_CR_CORRIG_TYPES = {"correction", "erratum", "retraction"}


def _first_page(f: PdfFeatures) -> str:
    return (f.first_page_text_lower or "")[:4000]


def _has_sm_markers(f: PdfFeatures) -> bool:
    bag = " ".join(x or "" for x in (f.xmp_subject, f.xmp_keywords, f.xmp_type,
                                      f.info_subject, _first_page(f))).lower()
    return bool(_SM_RE.search(bag))


def _has_corrig_markers(f: PdfFeatures) -> bool:
    bag = " ".join(x or "" for x in (f.xmp_subject, f.xmp_title, f.info_title,
                                      _first_page(f))).lower()
    return bool(_CORRIG_RE.search(bag))


def _crossref_kind(f: PdfFeatures) -> Optional[str]:
    t = (f.crossref_type or "").lower()
    if t in _CR_CORRIG_TYPES:
        return "corrigendum"
    if t in _CR_SM_TYPES:
        return "supplementary"
    return None


def _title_for_compare(f: PdfFeatures) -> Optional[str]:
    for t in (f.crossref_title, f.xmp_title, f.info_title):
        if t and len(t.strip()) >= 10:
            return t.strip().lower()
    return None


# ---------- keep-side picker ----------

def _choose_keep(f1: PdfFeatures, f2: PdfFeatures) -> tuple[int, str]:
    """Given we've decided this is a duplicate, which side to keep."""
    c1 = bool(f1.is_corrupted)
    c2 = bool(f2.is_corrupted)
    if c1 and not c2: return 2, "1 corrupted"
    if c2 and not c1: return 1, "2 corrupted"

    x1 = bool(f1.xmp_doi) + bool(f1.info_title)
    x2 = bool(f2.xmp_doi) + bool(f2.info_title)
    if x1 != x2: return (1, "richer metadata") if x1 > x2 else (2, "richer metadata")

    w1, w2 = f1.text_word_count or 0, f2.text_word_count or 0
    if w1 >= 200 and w2 >= 200:
        if w2 > 0 and w1 / max(w2, 1) >= 1.25: return 1, "more text"
        if w1 > 0 and w2 / max(w1, 1) >= 1.25: return 2, "more text"

    if f1.size_bytes != f2.size_bytes:
        return (1, "larger file") if f1.size_bytes > f2.size_bytes else (2, "larger file")
    return 1, "tie"


# ---------- main evaluator ----------

def evaluate_pair(f1: PdfFeatures, f2: PdfFeatures) -> PairDecision:
    sigs: list[str] = []

    # --- absolute short-circuits ---
    if f1.bytes_sha256 and f1.bytes_sha256 == f2.bytes_sha256:
        keep, why = _choose_keep(f1, f2)
        return PairDecision(
            decision="same_content",
            confidence=1.0,
            rule="R0_sha256_equal",
            reason=f"byte-identical; keep {keep} ({why})",
            signals=["sha256_equal"],
            keep=keep,
        )

    if f1.is_corrupted and f2.is_corrupted:
        return PairDecision("manual", 0.0, "R_corrupt_both",
                            "both corrupted", ["both_corrupt"])
    if f1.is_corrupted:
        return PairDecision("keep_2", 0.95, "R_corrupt",
                            "file 1 corrupted", ["f1_corrupt"], keep=2)
    if f2.is_corrupted:
        return PairDecision("keep_1", 0.95, "R_corrupt",
                            "file 2 corrupted", ["f2_corrupt"], keep=1)

    # --- different language → distinct (strong signal) ---
    l1, l2 = f1.detected_language, f2.detected_language
    if l1 and l2 and l1 != l2:
        return PairDecision("distinct", 0.05, "R_lang_mismatch",
                            f"languages differ ({l1} vs {l2})",
                            [f"lang={l1}|{l2}"])

    # --- book vs book, or book vs chapter ---
    if f1.looks_like_book and f2.looks_like_book:
        return PairDecision("is_book", 0.10, "R_both_books",
                            f"both look like books ({f1.page_count}pp / {f2.page_count}pp)",
                            ["both_book"])
    if f1.looks_like_book ^ f2.looks_like_book:
        pc1, pc2 = f1.page_count or 0, f2.page_count or 0
        small_pc = min(pc1, pc2)
        big_pc = max(pc1, pc2)
        if small_pc and big_pc and big_pc / max(small_pc, 1) >= 3:
            chapter = 1 if pc1 < pc2 else 2
            return PairDecision("is_chapter", 0.10, "R_chapter_of_book",
                                f"pair {chapter} looks like a chapter of the other book",
                                [f"chapter={chapter}", f"pages={small_pc}/{big_pc}"])

    # --- SM / corrigendum markers before treating as duplicate ---
    cr1 = _crossref_kind(f1); cr2 = _crossref_kind(f2)
    sm1 = cr1 == "supplementary" or _has_sm_markers(f1)
    sm2 = cr2 == "supplementary" or _has_sm_markers(f2)
    corr1 = cr1 == "corrigendum" or _has_corrig_markers(f1)
    corr2 = cr2 == "corrigendum" or _has_corrig_markers(f2)

    # --- compute positive signals ---
    score = 0.0

    doi_match = False
    d1 = f1.extracted_doi or f1.xmp_doi
    d2 = f2.extracted_doi or f2.xmp_doi
    if d1 and d2:
        if d1.lower() == d2.lower():
            score += 0.50
            sigs.append("doi_match")
            doi_match = True
        else:
            sigs.append(f"doi_differ({d1}|{d2})")
            return PairDecision("distinct", 0.05, "R_doi_differ",
                                "different DOIs", sigs)

    ph_d = _phash_distance(f1.phash_p1, f2.phash_p1)
    if ph_d is not None:
        if ph_d <= 5:
            score += 0.25; sigs.append(f"phash_p1_d={ph_d}")
        elif ph_d <= 10:
            score += 0.10; sigs.append(f"phash_p1_d={ph_d}")
        elif ph_d >= 30:
            score -= 0.10; sigs.append(f"phash_p1_d={ph_d}")

    ph_last_d = _phash_distance(f1.phash_last, f2.phash_last)
    if ph_last_d is not None and ph_last_d <= 5:
        score += 0.10; sigs.append(f"phash_last_d={ph_last_d}")

    jacc = _minhash_jaccard(f1.minhash, f2.minhash)
    if jacc is not None:
        if jacc >= 0.85:
            score += 0.25; sigs.append(f"minhash_j={jacc:.2f}")
        elif jacc >= 0.60:
            score += 0.10; sigs.append(f"minhash_j={jacc:.2f}")
        elif jacc < 0.20:
            score -= 0.20; sigs.append(f"minhash_j={jacc:.2f}")

    tl = _tlsh_distance(f1.tlsh_hash, f2.tlsh_hash)
    if tl is not None:
        if tl < 30:
            score += 0.10; sigs.append(f"tlsh_d={tl}")
        elif tl < 70:
            score += 0.05; sigs.append(f"tlsh_d={tl}")

    t1 = _title_for_compare(f1); t2 = _title_for_compare(f2)
    title_r: Optional[int] = None
    if t1 and t2:
        title_r = int(fuzz.token_set_ratio(t1, t2))
        if title_r >= 95:
            score += 0.15; sigs.append(f"title_fuzz={title_r}")
        elif title_r >= 80:
            score += 0.05; sigs.append(f"title_fuzz={title_r}")
        elif title_r < 40:
            score -= 0.30; sigs.append(f"title_fuzz={title_r}")

    if f1.full_text_hash and f1.full_text_hash == f2.full_text_hash:
        score += 0.30; sigs.append("full_text_hash_equal")

    # Page-count divergence — weak negative unless SM explains it
    pc1, pc2 = f1.page_count or 0, f2.page_count or 0
    if pc1 and pc2:
        r = max(pc1, pc2) / max(min(pc1, pc2), 1)
        if r >= 2 and not (sm1 or sm2 or corr1 or corr2):
            score -= 0.10; sigs.append(f"pc_ratio={r:.1f}")

    # --- classification of SM / corrigendum outcome ---
    same_paper_signals = doi_match or (title_r is not None and title_r >= 85) or (jacc is not None and jacc >= 0.60)

    if same_paper_signals and (sm1 ^ sm2):
        sm_side = 1 if sm1 else 2
        return PairDecision("rename_sm", 0.88, "R_sm_marker",
                            f"side {sm_side} has SM markers; same work",
                            sigs + [f"sm_side={sm_side}"],
                            keep=2 if sm_side == 1 else 1)

    if same_paper_signals and (corr1 ^ corr2):
        corr_side = 1 if corr1 else 2
        return PairDecision("is_corrigendum", 0.88, "R_corrigendum",
                            f"side {corr_side} is corrigendum/reply; same DOI paper",
                            sigs + [f"corr_side={corr_side}"],
                            keep=2 if corr_side == 1 else 1)

    confidence = max(0.0, min(1.0, score))

    if confidence >= AUTO_THRESHOLD:
        keep, why = _choose_keep(f1, f2)
        return PairDecision(f"keep_{keep}", confidence, "R_fusion_auto",
                            f"high-confidence duplicate; keep {keep} ({why})",
                            sigs, keep=keep)

    if confidence >= REVIEW_THRESHOLD:
        keep, why = _choose_keep(f1, f2)
        return PairDecision("manual", confidence, "R_fusion_review",
                            f"likely duplicate; suggested keep {keep} ({why})",
                            sigs, keep=keep)

    # Distinct if signals are actively low AND we have comparable text
    if jacc is not None and jacc < 0.3 and (title_r is None or title_r < 60):
        return PairDecision("distinct", max(0.05, confidence), "R_fusion_distinct",
                            "content differs, titles differ", sigs)

    return PairDecision("manual", confidence, "R_fusion_inconclusive",
                        "insufficient signal", sigs)
