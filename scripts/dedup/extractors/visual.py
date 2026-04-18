"""Visual perceptual hashing of first/last PDF pages for deduplication."""
from __future__ import annotations

import pathlib
from typing import Optional

import fitz
import imagehash
from PIL import Image

_DPI = 150
_MAX_W = 1200
_MAX_H = 1600


def _render_page(page: "fitz.Page") -> Optional[Image.Image]:
    try:
        zoom = _DPI / 72.0
        matrix = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        mode = "RGB" if pix.n >= 3 else "L"
        img = Image.frombytes(mode, (pix.width, pix.height), pix.samples)
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
        doc = fitz.open(pdf_path)
    except Exception:
        return result

    try:
        n = doc.page_count
        if n < 1:
            return result

        try:
            first_img = _render_page(doc.load_page(0))
        except Exception:
            first_img = None
        result["phash_p1"], result["dhash_p1"] = _hash_pair(first_img)

        if n >= 2:
            try:
                last_img = _render_page(doc.load_page(n - 1))
            except Exception:
                last_img = None
            result["phash_last"] = _phash_only(last_img)

        return result
    except Exception:
        return result
    finally:
        try:
            doc.close()
        except Exception:
            pass
