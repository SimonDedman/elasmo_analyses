"""Text extraction + MinHash + language detection + full-text hash.

MinHash is over word-shingles of length 7 for corpus-scale Jaccard
similarity via datasketch LSH. Falls back to OCR for scanned PDFs
when `ocr_if_needed` and extracted word count < 100.

Text comes from Poppler's pdftotext (-raw) through scripts/lib/pdf_backend.py
(PyMuPDF until 21 Oct 2026). It is close to PyMuPDF's text but not identical,
so full_text_hash and MinHash values are only comparable within one backend:
schema.EXTRACTOR_VERSION was bumped to 2 so cached rows are re-extracted.
"""
from __future__ import annotations

import hashlib
import pathlib
import re
from typing import Optional

import numpy as np
from datasketch import MinHash

from . import ocr as _ocr

import sys as _sys
from pathlib import Path as _Path

_SCRIPTS = str(_Path(__file__).resolve().parents[2])
if _SCRIPTS not in _sys.path:
    _sys.path.insert(0, _SCRIPTS)
from lib import pdf_backend  # noqa: E402  pypdf + Poppler; PyMuPDF removed 21 Oct 2026 (AGPL)


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


def _extract_pages(pdf_path: pathlib.Path) -> tuple[str, Optional[str]]:
    """Return (full_text, first_page_text). Raises if the PDF cannot be read."""
    parts = pdf_backend.page_texts(pdf_path)
    first_page: Optional[str] = parts[0] if parts else None
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
            full_text, first_page_text = _extract_pages(pdf_path)
        except Exception:
            return out

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
