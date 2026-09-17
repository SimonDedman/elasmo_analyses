"""DOI prefix -> publisher name, from Crossref's member record.

The hand-written PREFIX map in generate_closed_access_html.py only knows each
publisher's main prefix, which left 1,042 DOI-bearing queue rows "unresolved"
(Wiley 10.1002, Elsevier 10.1006, Informa 10.1080 sub-prefixes, JSTOR 10.2307
variants ...). Crossref resolves every prefix it registered, so ask it once and
cache the answer in outputs/.crossref_prefix_cache.json (a null value means
Crossref returned 404: not a Crossref prefix, e.g. DataCite/Zenodo 10.5281).

    from lib.crossref_prefix import publisher_for_doi
    publisher_for_doi("10.1002/jmor.1051")  -> "Wiley"
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
CACHE = ROOT / "outputs" / ".crossref_prefix_cache.json"
MAILTO = "simondedman@gmail.com"
_PFX = re.compile(r"\s*(10\.\d{4,9})/")
_cache: dict | None = None


def _load() -> dict:
    global _cache
    if _cache is None:
        _cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    return _cache


def _save() -> None:
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(_load(), indent=1, sort_keys=True))


def prefix_of(doi: str) -> str | None:
    m = _PFX.match(doi or "")
    return m.group(1) if m else None


def publisher_for_prefix(prefix: str, fetch: bool = True) -> str | None:
    """Crossref member name for a prefix; None if unknown. With fetch=True an
    uncached prefix costs one keyless GET (cached only on 200 or 404)."""
    cache = _load()
    if prefix in cache:
        return cache[prefix]
    if not fetch:
        return None
    import urllib.error
    import urllib.request

    req = urllib.request.Request(
        f"https://api.crossref.org/prefixes/{prefix}?mailto={MAILTO}",
        headers={"User-Agent": f"elasmo_analyses/1.0 (mailto:{MAILTO})"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            name = json.load(r)["message"].get("name")
        cache[prefix] = name
    except urllib.error.HTTPError as e:
        if e.code == 404:
            cache[prefix] = None
        else:
            return None  # 429/5xx: do not cache a transient failure
    except Exception:
        return None
    _save()
    time.sleep(0.15)
    return cache[prefix]


def publisher_for_doi(doi: str, fetch: bool = True) -> str | None:
    p = prefix_of(doi)
    return publisher_for_prefix(p, fetch) if p else None
