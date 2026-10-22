"""Visual perceptual hashing of first/last PDF pages for deduplication.

Pages are rendered by Poppler's pdftoppm through scripts/lib/pdf_backend.py
(PyMuPDF until 21 Oct 2026). Measured on 60 corpus PDFs: identical pixel
dimensions, pHash distance 0-6 bits from the PyMuPDF render (median 0).
"""
from __future__ import annotations

import pathlib
from typing import Optional

import imagehash
from PIL import Image

import sys as _sys
from pathlib import Path as _Path

_SCRIPTS = str(_Path(__file__).resolve().parents[2])
if _SCRIPTS not in _sys.path:
    _sys.path.insert(0, _SCRIPTS)
from lib import pdf_backend  # noqa: E402  pypdf + Poppler; PyMuPDF removed 21 Oct 2026 (AGPL)

_DPI = 150
_MAX_W = 1200
_MAX_H = 1600


def _render_page(pdf_path: pathlib.Path, pno: int) -> Optional[Image.Image]:
    try:
        img = pdf_backend.render_page(pdf_path, pno, dpi=_DPI)
        if img.width > _MAX_W or img.height > _MAX_H:
            scale = min(_MAX_W / img.width, _MAX_H / img.height)
            new_size = (max(1, int(img.width * scale)), max(1, int(img.height * scale)))
            img = img.resize(new_size, Image.LANCZOS)
        return img.convert("L")
    except Exception:
        return None


def _hash_pair(img: Optional[Image.Image]) -> tuple[Optional[str], Optional[str]]:
    if img is None:
        return None, None
    try:
        p = str(imagehash.phash(img, hash_size=8))
        d = str(imagehash.dhash(img, hash_size=8))
        return p, d
    except Exception:
        return None, None


def _phash_only(img: Optional[Image.Image]) -> Optional[str]:
    if img is None:
        return None
    try:
        return str(imagehash.phash(img, hash_size=8))
    except Exception:
        return None


def compute(pdf_path: pathlib.Path) -> dict:
    result = {"phash_p1": None, "dhash_p1": None, "phash_last": None}
    try:
        n = pdf_backend.page_count(pdf_path)
    except Exception:
        return result

    try:
        if n < 1:
            return result

        first_img = _render_page(pdf_path, 0)
        result["phash_p1"], result["dhash_p1"] = _hash_pair(first_img)

        if n >= 2:
            last_img = _render_page(pdf_path, n - 1)
            result["phash_last"] = _phash_only(last_img)

        return result
    except Exception:
        return result
