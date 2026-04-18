"""Text extraction + MinHash + language detection + full-text hash.

MinHash is over word-shingles of length 7 for corpus-scale Jaccard
similarity via datasketch LSH. Falls back to OCR for scanned PDFs
when `ocr_if_needed` and extracted word count < 100.
"""
from __future__ import annotations

import hashlib
import pathlib
import re
from typing import Optional

import fitz
import numpy as np
from datasketch import MinHash

from . import ocr as _ocr


_SHINGLE_N = 7
_NUM_PERM = 128
_MIN_WORDS_FOR_MINHASH = 50
_MIN_WORDS_EXTRACTABLE = 100
_WS_RE = re.compile(r"\s+")
_WORD_RE = re.compile(r"\S+")


def _default_result() -> dict:
    return {
        "text_word_count": 0,
        "text_is_extractable": False,
        "ocr_triggered": False,
        "minhash": None,
        "detected_language": None,
        "first_page_text_lower": None,
        "full_text_hash": None,
    }


def _extract_pages(doc: "fitz.Document") -> tuple[str, Optional[str]]:
    """Return (full_text, first_page_text)."""
    parts: list[str] = []
    first_page: Optional[str] = None
    for i in range(doc.page_count):
        try:
            t = doc.load_page(i).get_text("text")
        except Exception:
            t = ""
        if i == 0:
            first_page = t
        parts.append(t)
    return "\n\f\n".join(parts), first_page


def _compute_minhash(text: str) -> Optional[bytes]:
    words = _WORD_RE.findall(text.lower())
    if len(words) < _SHINGLE_N:
        return None
    mh = MinHash(num_perm=_NUM_PERM)
    for i in range(len(words) - _SHINGLE_N + 1):
        shingle = " ".join(words[i : i + _SHINGLE_N])
        mh.update(shingle.encode("utf-8"))
    return np.asarray(mh.hashvalues, dtype="<u4").tobytes()


def _detect_language(text: str) -> Optional[str]:
    sample = text[:5000].strip()
    if not sample:
        return None
    try:
        from langdetect import detect
        from langdetect.lang_detect_exception import LangDetectException
    except Exception:
        return None
    try:
        return detect(sample)
    except LangDetectException:
        return None
    except Exception:
        return None


def _full_text_hash(text: str) -> Optional[str]:
    norm = _WS_RE.sub(" ", text.strip().lower())
    if not norm:
        return None
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


def compute(pdf_path: pathlib.Path, ocr_if_needed: bool = True) -> dict:
    out = _default_result()
    try:
        try:
            doc = fitz.open(pdf_path)
        except Exception:
            return out

        try:
            full_text, first_page_text = _extract_pages(doc)
        finally:
            try:
                doc.close()
            except Exception:
                pass

        word_count = len(full_text.split())

        if ocr_if_needed and word_count < _MIN_WORDS_EXTRACTABLE:
            ocr_text = _ocr.run_ocr(pdf_path)
            if ocr_text:
                ocr_word_count = len(ocr_text.split())
                if ocr_word_count > word_count:
                    full_text = ocr_text
                    word_count = ocr_word_count
                    ocr_first = ocr_text.split("\n\f\n", 1)[0] if ocr_text else None
                    if not first_page_text or not first_page_text.strip():
                        first_page_text = ocr_first
                    out["ocr_triggered"] = True

        out["text_word_count"] = word_count
        out["text_is_extractable"] = word_count >= _MIN_WORDS_EXTRACTABLE

        if word_count >= _MIN_WORDS_FOR_MINHASH:
            out["minhash"] = _compute_minhash(full_text)

        out["detected_language"] = _detect_language(full_text)

        if first_page_text:
            out["first_page_text_lower"] = first_page_text.lower()[:8000]

        out["full_text_hash"] = _full_text_hash(full_text)

        return out
    except Exception:
        return _default_result()
