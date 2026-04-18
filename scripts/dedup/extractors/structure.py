"""PDF structure + embedded metadata via pikepdf.

Single pikepdf.open call extracts:
  - page_count, is_corrupted
  - outline depth + top-level count + looks_like_book
  - XMP /Title, /Subject, /Keywords, /doi, /Type
  - Info dict /Title, /Subject, /Producer
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Optional

import pikepdf


def _s(v: Any) -> Optional[str]:
    if v is None:
        return None
    try:
        s = str(v).strip()
    except Exception:
        return None
    return s or None


def _outline_depth_and_top(pdf: pikepdf.Pdf) -> tuple[int, int]:
    """Return (max_depth, top_level_count). Depth 0 = no outline."""
    try:
        with pdf.open_outline() as ol:
            roots = list(ol.root) if ol.root is not None else []
    except Exception:
        return 0, 0

    if not roots:
        return 0, 0

    def walk(items, depth=1) -> int:
        d = depth
        for it in items:
            try:
                child = list(it.children) if it.children else []
            except Exception:
                child = []
            if child:
                d = max(d, walk(child, depth + 1))
        return d

    return walk(roots), len(roots)


def compute(pdf_path: Path) -> dict:
    out: dict = {
        "page_count": 0,
        "is_corrupted": False,
        "outline_depth": 0,
        "outline_top_count": 0,
        "looks_like_book": False,
        "xmp_title": None,
        "xmp_subject": None,
        "xmp_keywords": None,
        "xmp_doi": None,
        "xmp_type": None,
        "info_title": None,
        "info_subject": None,
        "info_producer": None,
    }

    try:
        pdf = pikepdf.open(str(pdf_path))
    except Exception:
        out["is_corrupted"] = True
        return out

    try:
        out["page_count"] = len(pdf.pages)
    except Exception:
        out["is_corrupted"] = True

    try:
        d, n = _outline_depth_and_top(pdf)
        out["outline_depth"] = d
        out["outline_top_count"] = n
    except Exception:
        pass

    # Info dict
    try:
        docinfo = pdf.docinfo or {}
        out["info_title"] = _s(docinfo.get("/Title"))
        out["info_subject"] = _s(docinfo.get("/Subject"))
        out["info_producer"] = _s(docinfo.get("/Producer"))
    except Exception:
        pass

    # XMP metadata
    try:
        with pdf.open_metadata(set_pikepdf_as_editor=False) as meta:
            out["xmp_title"] = _s(meta.get("dc:title"))
            out["xmp_subject"] = _s(meta.get("dc:description"))
            kw = meta.get("pdf:Keywords") or meta.get("dc:subject")
            out["xmp_keywords"] = _s(kw)
            out["xmp_type"] = _s(meta.get("dc:type"))
            # DOI appears under various keys in practice
            for k in ("prism:doi", "pdfx:doi", "doi", "crossmark:doi"):
                v = meta.get(k)
                if v:
                    out["xmp_doi"] = _s(v)
                    break
    except Exception:
        pass

    try:
        pdf.close()
    except Exception:
        pass

    # Heuristic: looks_like_book
    pc = out["page_count"] or 0
    depth = out["outline_depth"] or 0
    top = out["outline_top_count"] or 0
    subj = (out["xmp_subject"] or "").lower()
    kw = (out["xmp_keywords"] or "").lower()
    xtype = (out["xmp_type"] or "").lower()
    if pc >= 100 and (depth >= 2 or top >= 5):
        out["looks_like_book"] = True
    elif re.search(r"\bbook\b", xtype) or re.search(r"\bmonograph\b", f"{subj} {kw}"):
        out["looks_like_book"] = True
    elif pc >= 200:
        out["looks_like_book"] = True

    # Normalize DOI from XMP if present
    if out["xmp_doi"]:
        m = re.search(r"10\.\d{4,9}/[^\s\"'>]+", out["xmp_doi"])
        out["xmp_doi"] = m.group(0).lower().rstrip(".,;)") if m else out["xmp_doi"].lower()

    return out
