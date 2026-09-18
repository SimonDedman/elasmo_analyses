#!/usr/bin/env python3
"""
fetch_free_sources.py

Reusable acquisition channels for free/open PDF sources, built from
recipes proven by hand on 2026-09-17 (see outputs/download_push_2026-09-17/
CHROME_strandvlo, CHROME_ices, CHROME_frdc, A3_journals, SPRINGER_api for
the original manual runs and their manifests).

Channels (subcommands):
  vliz      -- VLIZ / MarineInfo Open Marine Archive (Belgian/Dutch grey
               literature: De Strandvlo, Het Zeepaard, ...).
  ices      -- ICES library on Figshare (ices-library.figshare.com).
  frdc      -- FRDC (Australia) reports by project number.
  jstage    -- J-STAGE, scoped to Japanese Journal of Ichthyology.
  springer  -- Springer Nature Meta + Open Access (JATS) APIs, by DOI.
  all       -- run every channel in sequence.

Each channel:
  1. Reads the outstanding pool from docs/papers_data.json READ-ONLY
     (last_status in needs_library / needs_pdf / sr_sync_new).
  2. Finds a candidate PDF (or, for springer, JATS full text).
  3. Verifies it (pymupdf text + title/author match).
  4. Stages a verified PDF as outputs/oa_downloads/<literature_id>.pdf
     (or, for springer JATS, outputs/oa_downloads_text/<literature_id>.xml)
     -- skip if the destination already exists.
  5. Writes/updates outputs/free_sources/<channel>_manifest.csv and
     outputs/free_sources/<channel>_coverage.json.

This script NEVER writes docs/papers_data.json, never ingests, never
deletes. Run scripts/acquire_cascade.py --finalize-only afterwards to file
staged PDFs into the corpus.

Per ~/.claude/WEB-LOOKUPS.md: a 403/429/timeout is recorded as "blocked",
never as "not_found", and never cached; only 200 responses are cached
(outputs/free_sources/.cache/<channel>/). Coverage (rows in scope,
attempted, blocked, errors) is always recorded alongside results.

Usage:
  python3 scripts/fetch_free_sources.py vliz --dry-run
  python3 scripts/fetch_free_sources.py vliz --limit 5
  python3 scripts/fetch_free_sources.py ices --limit 5
  python3 scripts/fetch_free_sources.py frdc --limit 5
  python3 scripts/fetch_free_sources.py jstage --limit 5
  python3 scripts/fetch_free_sources.py springer --limit 5
  python3 scripts/fetch_free_sources.py springer --tdm
  python3 scripts/fetch_free_sources.py all --dry-run
  python3 scripts/fetch_free_sources.py vliz --ids 14559 --staging-dir /tmp/scratch
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import unicodedata
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

import requests

try:
    import pymupdf  # PyMuPDF
except ImportError:  # pragma: no cover
    pymupdf = None

BASE = Path(__file__).resolve().parent.parent
PAPERS_JSON = BASE / "docs" / "papers_data.json"
ENV_FILE = BASE / ".env"
DEFAULT_STAGING_DIR = BASE / "outputs" / "oa_downloads"
DEFAULT_TEXT_STAGING_DIR = BASE / "outputs" / "oa_downloads_text"
FREE_SOURCES_DIR = BASE / "outputs" / "free_sources"
CACHE_ROOT = FREE_SOURCES_DIR / ".cache"

OUTSTANDING_STATUSES = {"needs_library", "needs_pdf", "sr_sync_new"}

MANIFEST_FIELDS = ["literature_id", "venue", "url", "path", "sha256",
                    "bytes", "verified", "doi_seen", "status", "note"]

USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 "
              "(mailto:simondedman@gmail.com)")

# Figshare's ndownloader proxy (used by the ICES channel) detects a
# browser-shaped User-Agent and returns 202 "still generating" with an
# empty body indefinitely (confirmed live, 2026-09-18: 5 retries over ~15s,
# still 202) -- it only streams the file straight through (200, real bytes)
# for a non-browser UA. requests' own default UA works, but we still want
# to identify ourselves per politeness norms, so use a distinct, honest,
# non-browser UA for this one channel rather than the Chrome UA above.
API_USER_AGENT = ("elasmo_analyses-fetch_free_sources/1.0 "
                  "(Shark Oracle acquisition; mailto:simondedman@gmail.com)")

DEFAULT_SLEEP = 1.5          # polite delay between requests, seconds
VLIZ_SLEEP = 2.0             # per the proven recipe, exactly 2s
BLOCK_STATUSES = {403, 429, 503, 999}

_TOKEN_RE = re.compile(r"[a-zà-ÿ]{4,}")
_STOP = {"the", "and", "for", "from", "with", "des", "der", "die", "van",
         "een", "het", "this", "that", "into", "over", "some", "notes"}


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------

def load_env() -> dict:
    """Parse .env (KEY=VALUE lines) without printing or logging values."""
    env: dict = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def load_papers() -> list:
    return json.loads(PAPERS_JSON.read_text())


def _norm_ascii(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    return text.encode("ascii", "ignore").decode()


def title_tokens(text: str) -> set:
    """Lowercase [a-zà-ÿ]{4,} tokens, stop-word filtered. Shared matching key
    for VLIZ, ICES, J-STAGE and the pdf-verification step."""
    text = (text or "").lower()
    return {t for t in _TOKEN_RE.findall(text) if t not in _STOP}


def title_overlap(a: str, b: str) -> float:
    """Token overlap fraction on the LONGER of the two titles' token sets."""
    ta, tb = title_tokens(a), title_tokens(b)
    if not ta or not tb:
        return 0.0
    denom = max(len(ta), len(tb))
    return len(ta & tb) / denom if denom else 0.0


def first_surname(authors: str) -> str:
    """First author's surname from an "A, B. & C, D. (YEAR)"-style string.
    Mirrors scripts/acquire_cascade.py::_first_surname for consistency."""
    first = re.split(r"\s*&\s*", str(authors or "").strip())[0].strip()
    first = re.sub(r"\(\d{4}\)", "", first).strip()
    if "," in first:
        return first.split(",")[0].strip()
    parts = first.split()
    return parts[-1] if parts else ""


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def scope_matches(row: dict, patterns: list) -> bool:
    haystack = " ".join(str(row.get(f) or "") for f in
                         ("journal", "journal_clean", "findspot_raw"))
    return any(p.search(haystack) for p in patterns)


def outstanding_scope(rows: list, patterns: list = None,
                       ids: list = None) -> list:
    """Rows in scope for a channel: either an explicit --ids list (any
    status, so a validation run can target an already-finalized lid), or
    the outstanding pool filtered by `patterns` (compiled regexes)."""
    if ids:
        wanted = {str(i) for i in ids}
        by_id = {str(r.get("literature_id")): r for r in rows}
        return [by_id[i] for i in wanted if i in by_id]
    out = [r for r in rows if r.get("last_status") in OUTSTANDING_STATUSES]
    if patterns:
        out = [r for r in out if scope_matches(r, patterns)]
    return out


def compile_patterns(*terms: str) -> list:
    return [re.compile(r"\b" + re.escape(t) + r"\b", re.I) for t in terms]


# ---------------------------------------------------------------------------
# HTTP with cache-successes-only + blocked/not-found classification
# ---------------------------------------------------------------------------

class Fetcher:
    """Wraps requests with: Chrome-like UA, cache 200s only under
    outputs/free_sources/.cache/<channel>/, and blocked-vs-error
    classification per WEB-LOOKUPS.md."""

    def __init__(self, channel: str, sleep: float = DEFAULT_SLEEP,
                 timeout: int = 30, user_agent: str = USER_AGENT):
        self.channel = channel
        self.sleep = sleep
        self.timeout = timeout
        self.cache_dir = CACHE_ROOT / channel
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})
        self.counts = Counter()  # 200s / blocked / errors etc, for display

    def _cache_key(self, method: str, url: str, body: str = "") -> Path:
        h = hashlib.sha256(f"{method}\n{url}\n{body}".encode()).hexdigest()
        return self.cache_dir / f"{h}.cache"

    def _pace(self):
        time.sleep(self.sleep)

    def get(self, url: str, headers: dict = None, use_cache: bool = True):
        """Returns (status_or_None, bytes_or_None, err_or_None, from_cache)."""
        ck = self._cache_key("GET", url)
        if use_cache and ck.exists():
            self.counts["cache_hit"] += 1
            return 200, ck.read_bytes(), None, True
        self._pace()
        try:
            r = self.session.get(url, headers=headers, timeout=self.timeout)
        except requests.RequestException as e:
            self.counts["error"] += 1
            return None, None, str(e), False
        if r.status_code == 200:
            self.counts["200"] += 1
            if use_cache:
                ck.write_bytes(r.content)
            return 200, r.content, None, False
        if r.status_code in BLOCK_STATUSES:
            self.counts["blocked"] += 1
        else:
            self.counts["other_status"] += 1
        return r.status_code, None, None, False

    def post_json(self, url: str, payload: dict, use_cache: bool = True):
        body = json.dumps(payload, sort_keys=True)
        ck = self._cache_key("POST", url, body)
        if use_cache and ck.exists():
            self.counts["cache_hit"] += 1
            return 200, ck.read_bytes(), None, True
        self._pace()
        try:
            r = self.session.post(url, json=payload,
                                  headers={"Content-Type": "application/json"},
                                  timeout=self.timeout)
        except requests.RequestException as e:
            self.counts["error"] += 1
            return None, None, str(e), False
        if r.status_code == 200:
            self.counts["200"] += 1
            if use_cache:
                ck.write_bytes(r.content)
            return 200, r.content, None, False
        if r.status_code in BLOCK_STATUSES:
            self.counts["blocked"] += 1
        else:
            self.counts["other_status"] += 1
        return r.status_code, None, None, False

    def download(self, url: str, dest: Path, headers: dict = None,
                max_attempts: int = 3):
        """Streams a file straight to `dest` (not cached: could be large;
        the manifest + staged file ARE the cache).

        A 403/429/503-class response is a block: reported immediately, never
        retried (retrying a block just looks like hammering). A 404 is a
        definitive negative: also immediate. Anything else transient (a
        Figshare 202 while an S3 redirect signs, a stray 5xx, a connection
        reset) gets up to `max_attempts` tries with backoff before being
        reported as an error -- observed live: a Figshare download that
        returned 202 on first try was a clean 200 half a second later."""
        last_status, last_err = None, None
        for attempt in range(max_attempts):
            self._pace()
            try:
                r = self.session.get(url, headers=headers, timeout=60, stream=True)
            except requests.RequestException as e:
                last_status, last_err = None, str(e)
                if attempt < max_attempts - 1:
                    time.sleep(1.5 * (attempt + 1))
                continue
            if r.status_code == 200:
                with open(dest, "wb") as f:
                    for chunk in r.iter_content(1 << 16):
                        if chunk:
                            f.write(chunk)
                self.counts["200"] += 1
                return 200, None
            if r.status_code in BLOCK_STATUSES:
                self.counts["blocked"] += 1
                return r.status_code, None
            if r.status_code == 404:
                self.counts["other_status"] += 1
                return 404, None
            last_status, last_err = r.status_code, None
            if attempt < max_attempts - 1:
                time.sleep(1.5 * (attempt + 1))
        self.counts["error" if last_status is None else "other_status"] += 1
        return last_status, last_err


def classify_http_error(status) -> str:
    if status in BLOCK_STATUSES:
        return "blocked"
    return "error"


# ---------------------------------------------------------------------------
# PDF verification
# ---------------------------------------------------------------------------

def verify_pdf(path: Path, title: str = None, surname: str = None,
               pages: int = 4, min_bytes: int = 20 * 1024,
               overlap_threshold: float = 0.5):
    """Returns (verified, note). verified is True / False / "scan"
    (no extractable text layer -- untestable, not a disagreement)."""
    try:
        with open(path, "rb") as fh:
            head = fh.read(5)
        size = path.stat().st_size
    except OSError as e:
        return False, f"unreadable: {e}"
    if not head.startswith(b"%PDF") or size < min_bytes:
        return False, f"not a valid pdf or too small ({size}B)"
    if pymupdf is None:
        return "scan", "pymupdf not installed; cannot verify text"
    try:
        doc = pymupdf.open(str(path))
    except Exception as e:  # noqa: BLE001 - pymupdf raises various types
        return False, f"pymupdf open failed: {e}"
    try:
        n = min(pages, doc.page_count)
        text = "".join(doc[i].get_text() for i in range(n))
    finally:
        doc.close()
    got = title_tokens(text)
    if len(got) < 20:
        return "scan", "no extractable text layer (scanned)"
    detail = []
    ok = True
    if title:
        want = title_tokens(title)
        if want:
            hits = len(want & got)
            cov = hits / len(want)
            detail.append(f"title {hits}/{len(want)} ({cov:.2f})")
            ok = ok and cov >= overlap_threshold
    if surname:
        s = _norm_ascii(surname).lower()
        found = bool(s) and s in _norm_ascii(text).lower()
        detail.append(f"surname={'yes' if found else 'no'}")
        ok = ok and found
    if not detail:
        detail.append("no title/surname given; text layer present only")
    return ok, "; ".join(detail)


# ---------------------------------------------------------------------------
# Manifest + coverage I/O
# ---------------------------------------------------------------------------

def manifest_path(channel: str) -> Path:
    return FREE_SOURCES_DIR / f"{channel}_manifest.csv"


def coverage_path(channel: str) -> Path:
    return FREE_SOURCES_DIR / f"{channel}_coverage.json"


def read_manifest(channel: str) -> dict:
    import csv
    p = manifest_path(channel)
    if not p.exists():
        return {}
    with open(p, newline="", encoding="utf-8") as f:
        return {row["literature_id"]: row for row in csv.DictReader(f)}


def write_manifest(channel: str, rows_by_lid: dict):
    import csv
    FREE_SOURCES_DIR.mkdir(parents=True, exist_ok=True)
    p = manifest_path(channel)
    tmp = p.with_suffix(".tmp")
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=MANIFEST_FIELDS)
        w.writeheader()
        for lid in sorted(rows_by_lid, key=lambda x: (len(x), x)):
            row = {k: rows_by_lid[lid].get(k, "") for k in MANIFEST_FIELDS}
            w.writerow(row)
    tmp.replace(p)


def write_coverage(channel: str, coverage: dict):
    FREE_SOURCES_DIR.mkdir(parents=True, exist_ok=True)
    coverage_path(channel).write_text(json.dumps(coverage, indent=2))


def manifest_row(lid, venue="", url="", path="", sha256="", nbytes="",
                 verified="", doi_seen="", status="", note=""):
    return {"literature_id": str(lid), "venue": venue, "url": url,
            "path": path, "sha256": sha256, "bytes": nbytes,
            "verified": verified, "doi_seen": doi_seen, "status": status,
            "note": note}


def verified_str(v) -> str:
    if v == "scan":
        return "scan"
    return "yes" if v else "no"


# ---------------------------------------------------------------------------
# Channel processing loop (shared skeleton)
# ---------------------------------------------------------------------------

def run_loop(channel: str, rows_in_scope: list, args, process_row,
            fetcher: Fetcher, staging_dir: Path):
    """Drives one channel over its scoped rows. `process_row(row, dest,
    fetcher)` returns a dict: {status, manifest_row, error_class(optional)}.
    `status` is one of: downloaded, downloaded_scan, rejected_mismatch,
    not_found, blocked, error."""
    existing = read_manifest(channel)
    coverage = Counter()
    errors_by_class = Counter()
    coverage["rows_in_scope"] = len(rows_in_scope)
    attempted = 0
    limit = args.limit

    for row in rows_in_scope:
        lid = str(row.get("literature_id"))
        dest = staging_dir / f"{lid}.pdf"
        if dest.exists():
            coverage["already_staged"] += 1
            continue
        if limit is not None and attempted >= limit:
            coverage["not_attempted"] += 1
            continue
        if args.dry_run:
            coverage["would_attempt"] += 1
            continue

        attempted += 1
        try:
            result = process_row(row, dest, fetcher)
        except Exception as e:  # noqa: BLE001 - never let one row kill the run
            result = {"status": "error",
                      "manifest_row": manifest_row(lid, status="error",
                                                    note=f"exception: {e}"),
                      "error_class": "exception"}
        status = result["status"]
        coverage[status] += 1
        coverage["attempted"] += 1
        if status == "error":
            errors_by_class[result.get("error_class", "unknown")] += 1
        existing[lid] = result["manifest_row"]

    write_manifest(channel, existing)

    total_scoped_or_ids = len(rows_in_scope)
    out = {
        "channel": channel,
        "rows_in_scope": total_scoped_or_ids,
        "attempted": coverage.get("attempted", 0),
        "downloaded_verified": coverage.get("downloaded", 0),
        "downloaded_scan": coverage.get("downloaded_scan", 0),
        "rejected_mismatch": coverage.get("rejected_mismatch", 0),
        "not_found": coverage.get("not_found", 0),
        "blocked": coverage.get("blocked", 0),
        "errors_by_class": dict(errors_by_class),
        "already_staged": coverage.get("already_staged", 0),
        "not_attempted": coverage.get("not_attempted", 0)
                        + coverage.get("would_attempt", 0),
        "dry_run": bool(args.dry_run),
        "http_counts": dict(fetcher.counts),
    }
    write_coverage(channel, out)
    print(f"[{channel}] rows_in_scope={out['rows_in_scope']} "
          f"attempted={out['attempted']} "
          f"downloaded_verified={out['downloaded_verified']} "
          f"downloaded_scan={out['downloaded_scan']} "
          f"rejected={out['rejected_mismatch']} "
          f"not_found={out['not_found']} blocked={out['blocked']} "
          f"errors={sum(errors_by_class.values())} "
          f"already_staged={out['already_staged']} "
          f"not_attempted={out['not_attempted']}")
    return out


# ---------------------------------------------------------------------------
# Channel: VLIZ / MarineInfo
# ---------------------------------------------------------------------------

VLIZ_SEARCH_URL = "https://api.marineinfo.org/elastic/search"
VLIZ_DOC_URL = "https://marineinfo.org/doc/publication/{id}"
VLIZ_PDF_RE = re.compile(r"https://www\.vliz\.be/imisdocs/publications/[^\"'\s>]+\.pdf")

DEFAULT_VLIZ_VENUES = ["De Strandvlo", "Het Zeepaard"]


def _vliz_search_body(term: str) -> dict:
    return {
        "searchTerm": term, "current": 1, "resultsPerPage": 20,
        "filters": [], "sortField": "", "sortDirection": "",
        "facets": {
            "publicflag": [], "type": [], "title": [],
            "biblvlcode.biblvlcode": {"types": ["publication"]},
            "serie": {"types": ["publication"]},
            "pubCodes": {"types": ["publication"]},
            "wosflag": {"types": ["publication"]},
            "peerrevflag": {"types": ["publication"]},
            "vliz_pubtypes": [],
            "lendingVliz": {"types": ["publication"]},
            "date": [],
            "temporalCoverage": {"strictTypes": ["dataset"]},
            "spcolid.path.facet": {"size": 1000},
            "thesaurus.path.facet": {"size": 150000},
            "dasorigid.dasorigin.keyword": {"types": ["dataset"]},
            "dastypeid.dastype.keyword": {"types": ["dataset"]},
            "taxonomic.taxterm.keyword": [], "geographic.geoterm.keyword": [],
        },
    }


def vliz_find_candidate(fetcher: Fetcher, title: str, venue: str):
    status, body, err, _ = fetcher.post_json(VLIZ_SEARCH_URL,
                                             _vliz_search_body(title))
    if status != 200:
        return None, status, err
    try:
        data = json.loads(body)
    except json.JSONDecodeError as e:
        return None, None, f"bad json: {e}"
    hits = (data.get("hits") or {}).get("hits") or []
    best = None
    best_score = 0.0
    for h in hits:
        src = h.get("_source", {})
        if src.get("type") != "publication":
            continue
        refstr = src.get("refstrfull") or ""
        if venue.lower() not in refstr.lower():
            continue
        cand_title = src.get("standardTitle") or src.get("originalTitle") or ""
        score = title_overlap(title, cand_title)
        if score >= 0.5 and score > best_score:
            best_score = score
            best = (src.get("id"), cand_title, score)
    return best, 200, None


def vliz_process_row(row: dict, dest: Path, fetcher: Fetcher, venue: str):
    lid = row.get("literature_id")
    title = row.get("title") or ""
    cand, status, err = vliz_find_candidate(fetcher, title, venue)
    if cand is None:
        if status is not None and status != 200:
            cls = classify_http_error(status)
            return {"status": cls,
                    "manifest_row": manifest_row(lid, venue=venue,
                        status=cls, note=f"search HTTP {status}: {err or ''}"),
                    "error_class": f"search_http_{status}"}
        if err:
            return {"status": "error",
                    "manifest_row": manifest_row(lid, venue=venue,
                        status="error", note=f"search error: {err}"),
                    "error_class": "search_exception"}
        return {"status": "not_found",
                "manifest_row": manifest_row(lid, venue=venue,
                    status="not_found", note="no marineinfo hit >=0.5 overlap")}

    doc_id, cand_title, score = cand
    doc_status, doc_body, doc_err, _ = fetcher.get(VLIZ_DOC_URL.format(id=doc_id))
    if doc_status != 200:
        cls = classify_http_error(doc_status) if doc_status else "error"
        return {"status": cls,
                "manifest_row": manifest_row(lid, venue=venue,
                    status=cls,
                    note=f"doc page id={doc_id} HTTP {doc_status}: {doc_err or ''}"),
                "error_class": f"docpage_http_{doc_status}"}
    m = VLIZ_PDF_RE.search(doc_body.decode("utf-8", "ignore"))
    if not m:
        return {"status": "not_found",
                "manifest_row": manifest_row(lid, venue=venue,
                    url=VLIZ_DOC_URL.format(id=doc_id), status="not_found",
                    note=f"marineinfo id={doc_id} overlap {score:.2f}; no PDF link on doc page")}
    pdf_url = m.group(0)
    dl_status, dl_err = fetcher.download(pdf_url, dest)
    if dl_status != 200:
        cls = classify_http_error(dl_status) if dl_status else "error"
        return {"status": cls,
                "manifest_row": manifest_row(lid, venue=venue, url=pdf_url,
                    status=cls, note=f"download HTTP {dl_status}: {dl_err or ''}"),
                "error_class": f"download_http_{dl_status}"}

    verified, note = verify_pdf(dest, title=title, pages=4)
    size = dest.stat().st_size
    digest = sha256_of(dest)
    if verified is False:
        dest.unlink(missing_ok=True)
        return {"status": "rejected_mismatch",
                "manifest_row": manifest_row(lid, venue=venue, url=pdf_url,
                    sha256=digest, nbytes=size, verified="no",
                    status="rejected_mismatch",
                    note=f"marineinfo id={doc_id} overlap {score:.2f}; {note}")}
    status_out = "downloaded" if verified is True else "downloaded_scan"
    return {"status": status_out,
            "manifest_row": manifest_row(lid, venue=venue, url=pdf_url,
                path=str(dest), sha256=digest, nbytes=size,
                verified=verified_str(verified), status="downloaded",
                note=f"marineinfo id={doc_id} overlap {score:.2f}; {note}")}


def cmd_vliz(args):
    rows = load_papers()
    if args.venue:
        venues = [args.venue]
        patterns = compile_patterns(args.venue)
    else:
        venues = DEFAULT_VLIZ_VENUES
        patterns = compile_patterns(*DEFAULT_VLIZ_VENUES)
    ids = args.ids.split(",") if args.ids else None
    scope = outstanding_scope(rows, patterns, ids)
    # attach the matched venue per row so process_row knows which venue
    # string to require in refstrfull
    row_venue = {}
    for r in scope:
        hay = " ".join(str(r.get(f) or "") for f in
                       ("journal", "journal_clean", "findspot_raw"))
        row_venue[str(r["literature_id"])] = next(
            (v for v in venues if v.lower() in hay.lower()), venues[0])

    staging_dir = Path(args.staging_dir) if args.staging_dir else DEFAULT_STAGING_DIR
    staging_dir.mkdir(parents=True, exist_ok=True)
    fetcher = Fetcher("vliz", sleep=args.sleep or VLIZ_SLEEP)

    def process(row, dest, f):
        v = row_venue.get(str(row["literature_id"]), venues[0])
        return vliz_process_row(row, dest, f, v)

    return run_loop("vliz", scope, args, process, fetcher, staging_dir)


# ---------------------------------------------------------------------------
# Channel: ICES library on Figshare
# ---------------------------------------------------------------------------

FIGSHARE_SEARCH_URL = "https://api.figshare.com/v2/articles/search"
FIGSHARE_ARTICLE_URL = "https://api.figshare.com/v2/articles/{id}"


def figshare_search(fetcher: Fetcher, term: str):
    status, body, err, _ = fetcher.post_json(FIGSHARE_SEARCH_URL,
                                             {"search_for": term, "page_size": 10})
    if status != 200:
        return None, status, err
    try:
        return json.loads(body), 200, None
    except json.JSONDecodeError as e:
        return None, None, f"bad json: {e}"


def ices_find_candidate(fetcher: Fetcher, row: dict):
    title = row.get("title") or ""
    surname = first_surname(row.get("authors") or "")
    year = row.get("year")

    for term in (title, f"{surname} {year}".strip()):
        if not term.strip():
            continue
        hits, status, err = figshare_search(fetcher, term)
        if hits is None:
            if status is not None and status != 200:
                return None, status, err
            continue
        best, best_score = None, 0.0
        for h in hits:
            url = (h.get("url_public_html") or "")
            if "ices-library" not in url.lower():
                continue
            score = title_overlap(title, h.get("title") or "")
            if score >= 0.5 and score > best_score:
                best_score = score
                best = (h.get("id"), h.get("title"), score)
        if best:
            return best, 200, None
    return None, 200, None


def ices_process_row(row: dict, dest: Path, fetcher: Fetcher):
    lid = row.get("literature_id")
    title = row.get("title") or ""
    surname = first_surname(row.get("authors") or "")
    cand, status, err = ices_find_candidate(fetcher, row)
    if cand is None:
        if status is not None and status != 200:
            cls = classify_http_error(status)
            return {"status": cls,
                    "manifest_row": manifest_row(lid, venue="ICES",
                        status=cls, note=f"search HTTP {status}: {err or ''}"),
                    "error_class": f"search_http_{status}"}
        return {"status": "not_found",
                "manifest_row": manifest_row(lid, venue="ICES",
                    status="not_found", note="no ices-library hit >=0.5 overlap")}

    fid, cand_title, score = cand
    art_status, art_body, art_err, _ = fetcher.get(FIGSHARE_ARTICLE_URL.format(id=fid))
    if art_status != 200:
        cls = classify_http_error(art_status) if art_status else "error"
        return {"status": cls,
                "manifest_row": manifest_row(lid, venue="ICES",
                    status=cls,
                    note=f"figshare article={fid} HTTP {art_status}: {art_err or ''}"),
                "error_class": f"article_http_{art_status}"}
    try:
        art = json.loads(art_body)
    except json.JSONDecodeError as e:
        return {"status": "error",
                "manifest_row": manifest_row(lid, venue="ICES", status="error",
                    note=f"bad article json: {e}"),
                "error_class": "bad_json"}
    files = art.get("files") or []
    if not files:
        return {"status": "not_found",
                "manifest_row": manifest_row(lid, venue="ICES",
                    url=f"https://api.figshare.com/v2/articles/{fid}",
                    status="not_found",
                    note=f"figshare article={fid} overlap {score:.2f}; no files")}
    pdf_files = [f for f in files if str(f.get("name", "")).lower().endswith(".pdf")]
    chosen = pdf_files[0] if pdf_files else files[0]
    pdf_url = chosen.get("download_url")

    dl_status, dl_err = fetcher.download(pdf_url, dest)
    if dl_status != 200:
        cls = classify_http_error(dl_status) if dl_status else "error"
        return {"status": cls,
                "manifest_row": manifest_row(lid, venue="ICES", url=pdf_url,
                    status=cls, note=f"download HTTP {dl_status}: {dl_err or ''}"),
                "error_class": f"download_http_{dl_status}"}

    verified, note = verify_pdf(dest, title=title, surname=surname, pages=2)
    size = dest.stat().st_size
    digest = sha256_of(dest)
    if verified is False:
        dest.unlink(missing_ok=True)
        return {"status": "rejected_mismatch",
                "manifest_row": manifest_row(lid, venue="ICES", url=pdf_url,
                    sha256=digest, nbytes=size, verified="no",
                    status="rejected_mismatch",
                    note=f"figshare article={fid} overlap {score:.2f}; {note}")}
    status_out = "downloaded" if verified is True else "downloaded_scan"
    return {"status": status_out,
            "manifest_row": manifest_row(lid, venue="ICES", url=pdf_url,
                path=str(dest), sha256=digest, nbytes=size,
                verified=verified_str(verified), status="downloaded",
                note=f"figshare article={fid} overlap {score:.2f}; {note}")}


def cmd_ices(args):
    rows = load_papers()
    patterns = compile_patterns(args.venue) if args.venue else compile_patterns("ICES")
    ids = args.ids.split(",") if args.ids else None
    scope = outstanding_scope(rows, patterns, ids)
    staging_dir = Path(args.staging_dir) if args.staging_dir else DEFAULT_STAGING_DIR
    staging_dir.mkdir(parents=True, exist_ok=True)
    fetcher = Fetcher("ices", sleep=args.sleep or DEFAULT_SLEEP,
                      user_agent=API_USER_AGENT)
    return run_loop("ices", scope, args, ices_process_row, fetcher, staging_dir)


# ---------------------------------------------------------------------------
# Channel: FRDC (Australia)
# ---------------------------------------------------------------------------

FRDC_KEYWORD_RE = re.compile(r"FRDC", re.I)
FRDC_PROJECT_NUM_RE = re.compile(r"\b(\d{2,4})\s*/\s*(\d{2,4})\b")
FRDC_PDF_URL = "https://www.frdc.com.au/sites/default/files/products/{year}-{num}-DLD.pdf"
FRDC_PROJECT_PAGE = "https://www.frdc.com.au/project/{year}-{num}"
FRDC_PDF_LINK_RE = re.compile(r'href="([^"]+\.pdf)"', re.I)


def parse_frdc_project(row: dict):
    """('YYYY', 'NNN') from findspot_raw/journal(_clean)/notes, or None.
    Per the brief: 2-digit years mean 19xx. The project number is
    zero-padded to at least 3 digits to match the site's -DLD.pdf naming
    (1993-061, 1998-108, 1999-369)."""
    text = " ".join(str(row.get(f) or "") for f in
                    ("findspot_raw", "journal_clean", "journal", "notes"))
    if not FRDC_KEYWORD_RE.search(text):
        return None
    m = FRDC_PROJECT_NUM_RE.search(text)
    if not m:
        return None
    year, num = m.group(1), m.group(2)
    if len(year) == 2:
        year = "19" + year
    num = num.zfill(3)
    return year, num


def frdc_process_row(row: dict, dest: Path, fetcher: Fetcher):
    lid = row.get("literature_id")
    title = row.get("title") or ""
    proj = parse_frdc_project(row)
    if proj is None:
        return {"status": "not_found",
                "manifest_row": manifest_row(lid, venue="FRDC",
                    status="not_found",
                    note="no FRDC project number parsed from findspot_raw")}
    year, num = proj
    pdf_url = FRDC_PDF_URL.format(year=year, num=num)
    dl_status, dl_err = fetcher.download(pdf_url, dest)
    if dl_status == 200:
        verified, note = verify_pdf(dest, title=title, pages=4)
        size = dest.stat().st_size
        digest = sha256_of(dest)
        if verified is False:
            dest.unlink(missing_ok=True)
            return {"status": "rejected_mismatch",
                    "manifest_row": manifest_row(lid, venue="FRDC", url=pdf_url,
                        sha256=digest, nbytes=size, verified="no",
                        status="rejected_mismatch",
                        note=f"project {year}/{num}; {note}")}
        status_out = "downloaded" if verified is True else "downloaded_scan"
        return {"status": status_out,
                "manifest_row": manifest_row(lid, venue="FRDC", url=pdf_url,
                    path=str(dest), sha256=digest, nbytes=size,
                    verified=verified_str(verified), status="downloaded",
                    note=f"project {year}/{num}; {note}")}

    first_cls = classify_http_error(dl_status) if dl_status else "error"
    # Fallback: the project page might list the PDF under a different name.
    pg_status, pg_body, pg_err, _ = fetcher.get(
        FRDC_PROJECT_PAGE.format(year=year, num=num))
    if pg_status == 200:
        m = FRDC_PDF_LINK_RE.search(pg_body.decode("utf-8", "ignore"))
        if m:
            alt_url = m.group(1)
            if alt_url.startswith("/"):
                alt_url = "https://www.frdc.com.au" + alt_url
            dl2_status, dl2_err = fetcher.download(alt_url, dest)
            if dl2_status == 200:
                verified, note = verify_pdf(dest, title=title, pages=4)
                size = dest.stat().st_size
                digest = sha256_of(dest)
                if verified is False:
                    dest.unlink(missing_ok=True)
                    return {"status": "rejected_mismatch",
                            "manifest_row": manifest_row(lid, venue="FRDC",
                                url=alt_url, sha256=digest, nbytes=size,
                                verified="no", status="rejected_mismatch",
                                note=f"project {year}/{num} via project page; {note}")}
                status_out = "downloaded" if verified is True else "downloaded_scan"
                return {"status": status_out,
                        "manifest_row": manifest_row(lid, venue="FRDC",
                            url=alt_url, path=str(dest), sha256=digest,
                            nbytes=size, verified=verified_str(verified),
                            status="downloaded",
                            note=f"project {year}/{num} via project page; {note}")}
            cls2 = classify_http_error(dl2_status) if dl2_status else "error"
            return {"status": cls2,
                    "manifest_row": manifest_row(lid, venue="FRDC", url=alt_url,
                        status=cls2,
                        note=f"project {year}/{num}: direct pattern {dl_status}, "
                             f"project-page pdf link HTTP {dl2_status}"),
                    "error_class": f"download_http_{dl2_status}"}
        return {"status": "not_found",
                "manifest_row": manifest_row(lid, venue="FRDC",
                    url=FRDC_PROJECT_PAGE.format(year=year, num=num),
                    status="not_found",
                    note=f"project {year}/{num}: direct pattern {dl_status}, "
                         f"project page has no pdf link")}

    # Both attempts failed the same way -> report the more informative one.
    overall_cls = first_cls if first_cls == "blocked" else classify_http_error(pg_status)
    return {"status": overall_cls,
            "manifest_row": manifest_row(lid, venue="FRDC",
                url=FRDC_PDF_URL.format(year=year, num=num),
                status=overall_cls,
                note=f"project {year}/{num}: direct pattern HTTP {dl_status}"
                     f"{'/'+str(dl_err) if dl_err else ''}, "
                     f"project page HTTP {pg_status}"
                     f"{'/'+str(pg_err) if pg_err else ''}"),
            "error_class": f"http_{dl_status}_{pg_status}"}


def cmd_frdc(args):
    rows = load_papers()
    ids = args.ids.split(",") if args.ids else None
    if args.venue:
        patterns = compile_patterns(args.venue)
        scope = outstanding_scope(rows, patterns, ids)
    else:
        scope = outstanding_scope(rows, None, ids) if ids else [
            r for r in rows if r.get("last_status") in OUTSTANDING_STATUSES
            and FRDC_KEYWORD_RE.search(
                " ".join(str(r.get(f) or "") for f in
                         ("findspot_raw", "journal_clean", "journal", "notes")))]
    staging_dir = Path(args.staging_dir) if args.staging_dir else DEFAULT_STAGING_DIR
    staging_dir.mkdir(parents=True, exist_ok=True)
    fetcher = Fetcher("frdc", sleep=args.sleep or DEFAULT_SLEEP)
    return run_loop("frdc", scope, args, frdc_process_row, fetcher, staging_dir)


# ---------------------------------------------------------------------------
# Channel: J-STAGE (Japanese Journal of Ichthyology)
# ---------------------------------------------------------------------------

JSTAGE_API = "https://api.jstage.jst.go.jp/searchapi/do?service=3&text={text}&issn=0021-5090"
JSTAGE_TITLE_OVERLAP_THRESHOLD = 0.75  # proven threshold from the 2026-09-17 run
JSTAGE_JOURNAL_ALIASES = ["Japanese Journal of Ichthyology", "Jpn. J. Ichthyol.",
                          "Jpn J Ichthyol"]
JSTAGE_NS = {"a": "http://www.w3.org/2005/Atom", "prism": "http://prismstandard.org/namespaces/basic/2.0/"}


def jstage_search(fetcher: Fetcher, text: str):
    import urllib.parse
    url = JSTAGE_API.format(text=urllib.parse.quote(text))
    status, body, err, _ = fetcher.get(url)
    if status != 200:
        return None, status, err
    try:
        root = ET.fromstring(body)
    except ET.ParseError as e:
        return None, None, f"bad xml: {e}"
    entries = []
    for entry in root.findall("a:entry", JSTAGE_NS):
        title_en = entry.findtext("a:article_title/a:en", default="", namespaces=JSTAGE_NS)
        link_en = entry.findtext("a:article_link/a:en", default="", namespaces=JSTAGE_NS)
        doi = entry.findtext("prism:doi", default="", namespaces=JSTAGE_NS)
        entries.append({"title": title_en, "link": link_en, "doi": doi})
    return entries, 200, None


def jstage_process_row(row: dict, dest: Path, fetcher: Fetcher):
    lid = row.get("literature_id")
    title = row.get("title") or ""
    entries, status, err = jstage_search(fetcher, title)
    if entries is None:
        if status is not None and status != 200:
            cls = classify_http_error(status)
            return {"status": cls,
                    "manifest_row": manifest_row(lid, venue="J-STAGE JJI",
                        status=cls, note=f"search HTTP {status}: {err or ''}"),
                    "error_class": f"search_http_{status}"}
        return {"status": "error",
                "manifest_row": manifest_row(lid, venue="J-STAGE JJI",
                    status="error", note=f"search error: {err}"),
                "error_class": "search_exception"}

    best, best_score = None, 0.0
    for e in entries:
        if not e["link"]:
            continue
        score = title_overlap(title, e["title"])
        if score >= JSTAGE_TITLE_OVERLAP_THRESHOLD and score > best_score:
            best_score = score
            best = e
    if best is None:
        return {"status": "not_found",
                "manifest_row": manifest_row(lid, venue="J-STAGE JJI",
                    doi_seen="", status="not_found",
                    note=f"no J-STAGE hit >= {JSTAGE_TITLE_OVERLAP_THRESHOLD} overlap "
                         f"({len(entries)} candidates)")}

    pdf_url = best["link"].replace("/_article", "/_pdf/-char/en")
    dl_status, dl_err = fetcher.download(pdf_url, dest)
    if dl_status != 200:
        cls = classify_http_error(dl_status) if dl_status else "error"
        return {"status": cls,
                "manifest_row": manifest_row(lid, venue="J-STAGE JJI", url=pdf_url,
                    doi_seen=best["doi"], status=cls,
                    note=f"download HTTP {dl_status}: {dl_err or ''}"),
                "error_class": f"download_http_{dl_status}"}

    verified, note = verify_pdf(dest, title=title, pages=4)
    size = dest.stat().st_size
    digest = sha256_of(dest)
    if verified is False:
        dest.unlink(missing_ok=True)
        return {"status": "rejected_mismatch",
                "manifest_row": manifest_row(lid, venue="J-STAGE JJI", url=pdf_url,
                    sha256=digest, nbytes=size, verified="no",
                    doi_seen=best["doi"], status="rejected_mismatch",
                    note=f"overlap {best_score:.2f}; {note}")}
    status_out = "downloaded" if verified is True else "downloaded_scan"
    return {"status": status_out,
            "manifest_row": manifest_row(lid, venue="J-STAGE JJI", url=pdf_url,
                path=str(dest), sha256=digest, nbytes=size,
                verified=verified_str(verified), doi_seen=best["doi"],
                status="downloaded", note=f"overlap {best_score:.2f}; {note}")}


def cmd_jstage(args):
    rows = load_papers()
    patterns = compile_patterns(args.venue) if args.venue else compile_patterns(*JSTAGE_JOURNAL_ALIASES)
    ids = args.ids.split(",") if args.ids else None
    scope = outstanding_scope(rows, patterns, ids)
    staging_dir = Path(args.staging_dir) if args.staging_dir else DEFAULT_STAGING_DIR
    staging_dir.mkdir(parents=True, exist_ok=True)
    fetcher = Fetcher("jstage", sleep=args.sleep or DEFAULT_SLEEP)
    return run_loop("jstage", scope, args, jstage_process_row, fetcher, staging_dir)


# ---------------------------------------------------------------------------
# Channel: Springer Nature (Meta + Open Access JATS, by DOI)
# ---------------------------------------------------------------------------

SPRINGER_META_URL = "https://api.springernature.com/meta/v2/json?q=doi:{doi}&api_key={key}"
SPRINGER_OA_URL = "https://api.springernature.com/openaccess/jats?q=doi:{doi}&api_key={key}"
SPRINGER_TDM_URL = "https://api.springernature.com/tdm/v2/pdf/{doi}?api_key={key}"  # speculative, untested
SPRINGER_DOI_PREFIXES = ("10.1007",)


def springer_meta(fetcher: Fetcher, doi: str, key: str):
    if not key:
        return None, None, "no SPRINGER_META_KEY in .env"
    url = SPRINGER_META_URL.format(doi=doi, key=key)
    status, body, err, _ = fetcher.get(url, use_cache=True)
    if status != 200:
        return None, status, err
    try:
        return json.loads(body), 200, None
    except json.JSONDecodeError as e:
        return None, None, f"bad json: {e}"


def springer_oa_jats(fetcher: Fetcher, doi: str, key: str):
    if not key:
        return None, None, "no SPRINGER_OA_KEY in .env"
    url = SPRINGER_OA_URL.format(doi=doi, key=key)
    status, body, err, _ = fetcher.get(url, use_cache=True)
    return body if status == 200 else None, status, err


def verify_jats(xml_bytes: bytes, row: dict):
    try:
        text = xml_bytes.decode("utf-8", "ignore")
    except Exception:  # noqa: BLE001
        text = ""
    stripped = re.sub(r"<[^>]+>", " ", text)[:20000]
    title = row.get("title") or ""
    surname = first_surname(row.get("authors") or "")
    got = title_tokens(stripped)
    if len(got) < 20:
        return "scan", "JATS body has almost no text"
    want = title_tokens(title)
    hits = len(want & got) if want else 0
    cov = hits / len(want) if want else 0.0
    ok_title = cov >= 0.5
    ok_surname = True
    detail = [f"title {hits}/{len(want)} ({cov:.2f})"]
    if surname:
        s = _norm_ascii(surname).lower()
        ok_surname = bool(s) and s in _norm_ascii(stripped).lower()
        detail.append(f"surname={'yes' if ok_surname else 'no'}")
    return (ok_title and ok_surname), "; ".join(detail)


def springer_process_row(row: dict, dest_pdf: Path, fetcher: Fetcher, env: dict,
                         text_staging_dir: Path):
    """`dest_pdf` is unused (Springer stages XML, not PDF) but kept for a
    uniform process_row signature; the text destination is derived here."""
    lid = row.get("literature_id")
    doi = row.get("doi") or ""
    meta, meta_status, meta_err = springer_meta(fetcher, doi, env.get("SPRINGER_META_KEY"))
    meta_openaccess = None
    meta_title = ""
    if meta:
        records = meta.get("records") or []
        if records:
            meta_openaccess = str(records[0].get("openaccess", "")).lower() == "true"
            meta_title = records[0].get("title", "")
    elif meta_status not in (None, 200):
        if meta_status == 401:
            return {"status": "error",
                    "manifest_row": manifest_row(lid, venue="Springer Nature",
                        doi_seen=doi, status="error",
                        note="meta API 401 (bad/missing SPRINGER_META_KEY)"),
                    "error_class": "auth_401"}
        cls = classify_http_error(meta_status)
        return {"status": cls,
                "manifest_row": manifest_row(lid, venue="Springer Nature",
                    doi_seen=doi, status=cls, note=f"meta HTTP {meta_status}: {meta_err or ''}")}

    xml_body, oa_status, oa_err = springer_oa_jats(fetcher, doi, env.get("SPRINGER_OA_KEY"))
    if xml_body is None:
        if oa_status == 404:
            return {"status": "not_found",
                    "manifest_row": manifest_row(lid, venue="Springer Nature",
                        doi_seen=doi, status="not_found",
                        note=f"no OA JATS text at Springer (meta_openaccess={meta_openaccess}, "
                             f"meta_title={meta_title[:60]!r})")}
        if oa_status == 401:
            return {"status": "error",
                    "manifest_row": manifest_row(lid, venue="Springer Nature",
                        doi_seen=doi, status="error",
                        note="OA API 401 (bad/missing SPRINGER_OA_KEY)"),
                    "error_class": "auth_401"}
        cls = classify_http_error(oa_status) if oa_status else "error"
        return {"status": cls,
                "manifest_row": manifest_row(lid, venue="Springer Nature",
                    doi_seen=doi, status=cls, note=f"OA JATS HTTP {oa_status}: {oa_err or ''}")}

    text_staging_dir.mkdir(parents=True, exist_ok=True)
    dest_xml = text_staging_dir / f"{lid}.xml"
    dest_xml.write_bytes(xml_body)
    verified, note = verify_jats(xml_body, row)
    size = dest_xml.stat().st_size
    digest = sha256_of(dest_xml)
    if verified is False:
        dest_xml.unlink(missing_ok=True)
        return {"status": "rejected_mismatch",
                "manifest_row": manifest_row(lid, venue="Springer Nature",
                    url=SPRINGER_OA_URL.format(doi=doi, key="***"),
                    sha256=digest, nbytes=size, verified="no", doi_seen=doi,
                    status="rejected_mismatch", note=note)}
    status_out = "downloaded" if verified is True else "downloaded_scan"
    return {"status": status_out,
            "manifest_row": manifest_row(lid, venue="Springer Nature",
                url=SPRINGER_OA_URL.format(doi=doi, key="***"),
                path=str(dest_xml), sha256=digest, nbytes=size,
                verified=verified_str(verified), doi_seen=doi,
                status="downloaded", note=note)}


def cmd_springer(args):
    env = load_env()
    if getattr(args, "tdm", False):
        key = env.get("SPRINGER_TDM_KEY")
        if not key:
            print("[springer] --tdm: no TDM key yet (SPRINGER_TDM_KEY absent from .env); "
                  "the Full Text (TDM) plan was applied for but is not yet approved. Exiting.")
            return {"channel": "springer", "tdm": True, "skipped": "no_tdm_key"}
        print("[springer] --tdm: SPRINGER_TDM_KEY present, but the real TDM endpoint "
              "shape is unconfirmed (speculative URL in code); not attempting a live "
              "fetch without a verified endpoint. Update SPRINGER_TDM_URL once "
              "Springer's approval email documents the real path.")
        return {"channel": "springer", "tdm": True, "skipped": "endpoint_unverified"}

    rows = load_papers()
    ids = args.ids.split(",") if args.ids else None
    if ids:
        scope = outstanding_scope(rows, None, ids)
    else:
        scope = [r for r in rows
                 if r.get("last_status") in OUTSTANDING_STATUSES
                 and (r.get("doi") or "").startswith(SPRINGER_DOI_PREFIXES)]
        if args.venue:
            pat = re.compile(re.escape(args.venue), re.I)
            scope = [r for r in scope if pat.search(r.get("doi") or "")]
    staging_dir = Path(args.staging_dir) if args.staging_dir else DEFAULT_STAGING_DIR
    staging_dir.mkdir(parents=True, exist_ok=True)
    text_staging_dir = (staging_dir.parent / (staging_dir.name + "_text")
                        if args.staging_dir else DEFAULT_TEXT_STAGING_DIR)
    fetcher = Fetcher("springer", sleep=args.sleep or DEFAULT_SLEEP)

    # Springer stages XML, not PDF, so "already staged" is checked against
    # the text dir, and run_loop's own `dest` (.pdf) check must not skip
    # rows that only lack a (nonexistent) PDF. Give run_loop a PDF-shaped
    # dest that never exists so its own skip-check is a no-op, and let
    # process_row do the real staging/skip check against the xml path.
    def process(row, _unused_pdf_dest, f):
        lid = str(row.get("literature_id"))
        xml_dest = text_staging_dir / f"{lid}.xml"
        if xml_dest.exists():
            return {"status": "already_staged_xml",
                    "manifest_row": manifest_row(lid, venue="Springer Nature",
                        path=str(xml_dest), status="already_staged",
                        doi_seen=row.get("doi") or "")}
        return springer_process_row(row, _unused_pdf_dest, f, env, text_staging_dir)

    out = run_loop("springer", scope, args, process, fetcher, staging_dir)
    return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="channel", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--limit", type=int, default=None,
                        help="max rows to actually attempt (network calls)")
    common.add_argument("--dry-run", action="store_true",
                        help="report rows in scope; make no network calls")
    common.add_argument("--venue", default=None,
                        help="override the channel's default venue filter "
                             "with a free-text substring match on "
                             "journal/journal_clean/findspot_raw")
    common.add_argument("--ids", default=None,
                        help="comma-separated literature_ids; overrides the "
                             "outstanding-pool scope filter (any last_status)")
    common.add_argument("--staging-dir", default=None,
                        help="override outputs/oa_downloads (e.g. for a "
                             "scratch validation run)")
    common.add_argument("--sleep", type=float, default=None,
                        help="override the per-request polite delay")

    sub.add_parser("vliz", parents=[common])
    sub.add_parser("ices", parents=[common])
    sub.add_parser("frdc", parents=[common])
    sub.add_parser("jstage", parents=[common])
    p_springer = sub.add_parser("springer", parents=[common])
    p_springer.add_argument("--tdm", action="store_true",
                            help="attempt the Full Text (TDM) endpoint; "
                                 "no-ops with exit 0 if SPRINGER_TDM_KEY "
                                 "is absent from .env")
    sub.add_parser("all", parents=[common])
    return p


CHANNEL_FUNCS = {
    "vliz": cmd_vliz, "ices": cmd_ices, "frdc": cmd_frdc,
    "jstage": cmd_jstage, "springer": cmd_springer,
}


def main(argv=None):
    args = build_parser().parse_args(argv)
    FREE_SOURCES_DIR.mkdir(parents=True, exist_ok=True)
    if args.channel == "all":
        results = {}
        for name, fn in CHANNEL_FUNCS.items():
            results[name] = fn(args)
        return results
    return CHANNEL_FUNCS[args.channel](args)


if __name__ == "__main__":
    main()
