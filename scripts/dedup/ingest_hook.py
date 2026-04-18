"""Integration point for the ingestion pipeline.

After a new PDF lands in the corpus, call `check_new_pdf(path)`. It:
  1. Extracts features for the new file (and caches them).
  2. Finds candidate duplicates in the cache (exact SHA match, DOI match,
     close pHash neighbours, recent arrivals in same year).
  3. Runs fusion against each candidate.
  4. Appends high-confidence flags to a JSONL log the user can review.

JSONL log: outputs/on_ingest_flags.jsonl
"""
from __future__ import annotations

import imagehash
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

from .cache import FeatureCache
from .extractors import extract_features
from .fusion import REVIEW_THRESHOLD, PairDecision, evaluate_pair
from .schema import PdfFeatures


PDF_BASE = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")
CACHE_PATH = Path("/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/"
                  "Data Panel/outputs/pdf_features.sqlite")
FLAG_LOG = Path("/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/"
                "Data Panel/outputs/on_ingest_flags.jsonl")

PHASH_MAX = 10  # Hamming distance up to which we treat two pHashes as "close"


def _rel_path(pdf_path: Path) -> str:
    try:
        return str(pdf_path.relative_to(PDF_BASE))
    except ValueError:
        return pdf_path.name


def _phash_candidates(new: PdfFeatures, cache: FeatureCache,
                      max_distance: int = PHASH_MAX) -> list[PdfFeatures]:
    """Linear scan — fine for corpora up to ~100k files."""
    if not new.phash_p1:
        return []
    try:
        new_hash = imagehash.hex_to_hash(new.phash_p1)
    except Exception:
        return []
    candidates: list[PdfFeatures] = []
    for path in cache.all_paths():
        if path == new.rel_path:
            continue
        f = cache.get(path)
        if f is None or not f.phash_p1:
            continue
        try:
            if (new_hash - imagehash.hex_to_hash(f.phash_p1)) <= max_distance:
                candidates.append(f)
        except Exception:
            continue
    return candidates


def _candidates_for(new: PdfFeatures, cache: FeatureCache) -> list[PdfFeatures]:
    seen: dict[str, PdfFeatures] = {}
    if new.bytes_sha256:
        for f in cache.find_by_sha256(new.bytes_sha256):
            if f.rel_path != new.rel_path:
                seen[f.rel_path] = f
    if new.extracted_doi:
        for f in cache.find_by_doi(new.extracted_doi):
            if f.rel_path != new.rel_path:
                seen.setdefault(f.rel_path, f)
    for f in _phash_candidates(new, cache):
        seen.setdefault(f.rel_path, f)
    return list(seen.values())


def check_new_pdf(
    pdf_path: Path,
    cache: Optional[FeatureCache] = None,
    ocr_if_needed: bool = True,
    do_doi: bool = True,
    log_path: Optional[Path] = FLAG_LOG,
    min_confidence: float = REVIEW_THRESHOLD,
) -> list[dict]:
    """Run dedup check on a newly-ingested PDF.

    Returns a list of flag dicts. Each is also appended as a JSONL line
    to `log_path` if provided.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        return []

    owns_cache = cache is None
    if cache is None:
        cache = FeatureCache(CACHE_PATH)

    try:
        rel = _rel_path(pdf_path)
        new_feat = extract_features(
            pdf_path, rel_path=rel,
            ocr_if_needed=ocr_if_needed, do_doi=do_doi,
        )
        cache.put(new_feat)

        flags: list[dict] = []
        for cand in _candidates_for(new_feat, cache):
            decision: PairDecision = evaluate_pair(new_feat, cand)
            if decision.confidence < min_confidence and decision.decision not in {
                "same_content", "rename_sm", "is_corrigendum", "is_chapter"
            }:
                continue
            flag = {
                "ts": datetime.now().isoformat(timespec="seconds"),
                "new_file": rel,
                "candidate": cand.rel_path,
                **decision.as_dict(),
            }
            flags.append(flag)

        if flags and log_path is not None:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(log_path, "a", encoding="utf-8") as fh:
                for flag in flags:
                    fh.write(json.dumps(flag, ensure_ascii=False) + "\n")

        return flags
    finally:
        if owns_cache:
            cache.close()


def check_batch(pdf_paths: Iterable[Path], **kw) -> dict[str, list[dict]]:
    """Convenience: run check_new_pdf on several newly-ingested files."""
    results: dict[str, list[dict]] = {}
    cache = FeatureCache(CACHE_PATH)
    try:
        for p in pdf_paths:
            results[str(p)] = check_new_pdf(Path(p), cache=cache, **kw)
    finally:
        cache.close()
    return results
