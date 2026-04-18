"""DOI extraction and CrossRef enrichment.

A DOI match between two files is the strongest same-paper signal available.
CrossRef `type` distinguishes main articles from corrections / supplements,
which must not be collapsed with the paper they correct.
"""
from __future__ import annotations

import concurrent.futures
import functools
import pathlib
import re
from typing import Optional

import requests


_DOI_CORE_RE = re.compile(r"10\.\d{4,9}/\S+")
_DOI_VALIDATE_RE = re.compile(r"^10\.\d{4,9}/\S+$")
_DOI_IN_TEXT_RE = re.compile(
    r"(?:doi[:\s]*|https?://(?:dx\.)?doi\.org/)?(10\.\d{4,9}/[^\s\"'<>]+)",
    re.IGNORECASE,
)
_TRAILING_PUNCT = ".,;)]>"
_URL_PREFIXES = (
    "https://doi.org/",
    "http://doi.org/",
    "https://dx.doi.org/",
    "http://dx.doi.org/",
)
_PDF2DOI_TIMEOUT_S = 60
_CROSSREF_TIMEOUT_S = 15
_CROSSREF_HEADERS = {
    "User-Agent": "SharkPapers-dedup (mailto:simondedman@gmail.com)",
}


def _default_result() -> dict:
    return {
        "extracted_doi": None,
        "doi_source": None,
        "crossref_type": None,
        "crossref_title": None,
        "crossref_container": None,
        "crossref_year": None,
    }


def _normalise_doi(raw: Optional[str]) -> Optional[str]:
    if not raw or not isinstance(raw, str):
        return None
    try:
        s = raw.strip().lower()
        for prefix in _URL_PREFIXES:
            if s.startswith(prefix):
                s = s[len(prefix):]
                break
        if s.startswith("doi:"):
            s = s[4:].lstrip()
        while s and s[-1] in _TRAILING_PUNCT:
            s = s[:-1]
        s = s.strip()
        if _DOI_VALIDATE_RE.match(s):
            return s
        return None
    except Exception:
        return None


def _doi_from_text(text: str) -> Optional[str]:
    try:
        for m in _DOI_IN_TEXT_RE.finditer(text):
            candidate = _normalise_doi(m.group(1))
            if candidate:
                return candidate
        for m in _DOI_CORE_RE.finditer(text):
            candidate = _normalise_doi(m.group(0))
            if candidate:
                return candidate
        return None
    except Exception:
        return None


def _doi_from_pdf2doi(pdf_path: pathlib.Path) -> Optional[str]:
    try:
        import pdf2doi  # type: ignore
    except ImportError:
        return None
    except Exception:
        return None

    def _call() -> Optional[str]:
        try:
            result = pdf2doi.pdf2doi(str(pdf_path))
        except Exception:
            return None
        if not result:
            return None
        try:
            ident = result.get("identifier") if isinstance(result, dict) else None
            itype = result.get("identifier_type") if isinstance(result, dict) else None
        except Exception:
            return None
        if ident and (itype is None or str(itype).lower() == "doi"):
            return str(ident)
        return None

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            future = ex.submit(_call)
            try:
                raw = future.result(timeout=_PDF2DOI_TIMEOUT_S)
            except concurrent.futures.TimeoutError:
                return None
    except Exception:
        return None

    return _normalise_doi(raw)


@functools.lru_cache(maxsize=4096)
def _crossref_lookup(doi: str) -> Optional[dict]:
    try:
        resp = requests.get(
            f"https://api.crossref.org/works/{doi}",
            headers=_CROSSREF_HEADERS,
            timeout=_CROSSREF_TIMEOUT_S,
        )
        if resp.status_code != 200:
            return None
        payload = resp.json()
    except Exception:
        return None
    try:
        message = payload.get("message")
        if not isinstance(message, dict):
            return None
        return message
    except Exception:
        return None


def _extract_year(message: dict) -> Optional[int]:
    try:
        issued = message.get("issued") or {}
        parts = issued.get("date-parts") or [[None]]
        if not parts or not parts[0]:
            return None
        y = parts[0][0]
        if y is None:
            return None
        return int(y)
    except Exception:
        return None


def _first_or_none(value) -> Optional[str]:
    try:
        if isinstance(value, list) and value:
            v = value[0]
            return str(v) if v is not None else None
        if isinstance(value, str):
            return value
        return None
    except Exception:
        return None


def compute(
    pdf_path: pathlib.Path,
    xmp_doi: str | None = None,
    first_page_text: str | None = None,
    light_mode: bool = False,
) -> dict:
    """Extract DOI + CrossRef metadata.

    light_mode=True skips the slow pdf2doi fallback and CrossRef lookup;
    only xmp and first-page-regex are consulted. Use for bulk indexing.
    """
    out = _default_result()

    doi: Optional[str] = None
    source: Optional[str] = None

    try:
        if xmp_doi:
            candidate = _normalise_doi(xmp_doi)
            if candidate:
                doi, source = candidate, "xmp"

        if doi is None and first_page_text:
            candidate = _doi_from_text(first_page_text)
            if candidate:
                doi, source = candidate, "text_regex"

        if doi is None and not light_mode:
            candidate = _doi_from_pdf2doi(pdf_path)
            if candidate:
                doi, source = candidate, "pdf2doi"
    except Exception:
        doi, source = None, None

    if doi is None:
        return out

    out["extracted_doi"] = doi
    out["doi_source"] = source

    if light_mode:
        return out

    try:
        message = _crossref_lookup(doi)
    except Exception:
        message = None

    if not message:
        return out

    try:
        mtype = message.get("type")
        out["crossref_type"] = str(mtype) if mtype else None
    except Exception:
        pass
    try:
        out["crossref_title"] = _first_or_none(message.get("title"))
    except Exception:
        pass
    try:
        out["crossref_container"] = _first_or_none(message.get("container-title"))
    except Exception:
        pass
    try:
        out["crossref_year"] = _extract_year(message)
    except Exception:
        pass

    if source == "pdf2doi" and out["crossref_title"] is None:
        out["doi_source"] = "crossref_title"

    return out
