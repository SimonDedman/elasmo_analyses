"""Feature extraction orchestrator.

Runs each extractor in order. A failure in one extractor is logged to
the feature's `extractor_errors` field and does not block the others.
"""
from __future__ import annotations

import json
import time
import traceback
from pathlib import Path
from typing import Optional

from ..schema import EXTRACTOR_VERSION, PdfFeatures
from . import doi as doi_ext
from . import hashes as hashes_ext
from . import ocr as ocr_ext
from . import structure as structure_ext
from . import text as text_ext
from . import visual as visual_ext


def _safe(name: str, fn, errors: list, **kw):
    try:
        return fn(**kw)
    except Exception:
        errors.append({"stage": name, "traceback": traceback.format_exc(limit=3)})
        return None


def extract_features(
    pdf_path: Path,
    rel_path: str,
    ocr_if_needed: bool = True,
    do_doi: bool = True,
    do_crossref: bool = False,
    do_visual: bool = True,
) -> PdfFeatures:
    """Extract a full PdfFeatures row for one PDF.

    `rel_path` is the key used in the cache (e.g. "2020/Foo.pdf").
    """
    errors: list = []
    st = pdf_path.stat()
    feat = PdfFeatures(
        rel_path=rel_path,
        size_bytes=st.st_size,
        mtime=st.st_mtime,
        extracted_at=time.time(),
        extractor_version=EXTRACTOR_VERSION,
    )

    struct = _safe("structure", structure_ext.compute, errors, pdf_path=pdf_path)
    if struct:
        for k, v in struct.items():
            setattr(feat, k, v)

    if feat.is_corrupted:
        feat.extractor_errors = json.dumps(errors) if errors else None
        return feat

    h = _safe("hashes", hashes_ext.compute, errors, pdf_path=pdf_path)
    if h:
        for k, v in h.items():
            setattr(feat, k, v)

    t = _safe(
        "text",
        text_ext.compute,
        errors,
        pdf_path=pdf_path,
        ocr_if_needed=ocr_if_needed,
    )
    if t:
        for k, v in t.items():
            setattr(feat, k, v)

    if do_visual:
        v = _safe("visual", visual_ext.compute, errors, pdf_path=pdf_path)
        if v:
            for k, val in v.items():
                setattr(feat, k, val)

    if do_doi:
        d = _safe(
            "doi",
            doi_ext.compute,
            errors,
            pdf_path=pdf_path,
            xmp_doi=feat.xmp_doi,
            first_page_text=feat.first_page_text_lower,
            light_mode=not do_crossref,
        )
        if d:
            for k, val in d.items():
                setattr(feat, k, val)

    feat.extractor_errors = json.dumps(errors) if errors else None
    return feat
