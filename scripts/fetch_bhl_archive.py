#!/usr/bin/env python3
"""
fetch_bhl_archive.py

Acquire freely-hosted PDFs for old / taxonomy-paleontology no-DOI papers
from the Biodiversity Heritage Library (BHL) and archive.org.

Background
----------
~1,500-3,500 papers in the no-DOI queue (docs/papers_data.json) are
pre-1970 taxonomy/paleontology pieces (Copeia, Cybium, Journal of
Vertebrate Paleontology, Journal of Paleontology, Annales, old Bulletins
etc.). These journals are heavily digitised, out of copyright, and
freely hosted on archive.org (mirrored from BHL and other library
scanning projects), so they can often be fetched without a publisher
paywall or a DOI.

Channels
--------
1. **archive.org advancedsearch + metadata API** (no key required).
   Old serials are digitised issue-by-issue under identifiers like
   ``sim_copeia_1936-05-10_1`` or ``fishery-bulletin_1888_8``. We search
   by journal title, keep candidates whose identifier/title contains the
   paper's publication year, fetch the item's OCR text (``_djvu.txt``)
   and require a minimum overlap with the paper's title words before
   downloading the issue PDF. This is the PRIMARY channel here — it
   works with no registration.

2. **BHL PublicAPI (api3)**. Investigated first: EVERY op (including
   PublicationSearch, NameSearch, GetTitleMetadata) returns
   ``{"Status":"unauthorized", ...}`` when called without a registered
   API key — there is no keyless/anonymous access. A free key is
   requested via the BHL website and is not obtained programmatically
   from this environment, so BHL is wired up but INACTIVE unless a
   ``BHL_API_KEY`` env var is set. If/when a key is obtained, this
   script will start using it automatically as a secondary channel.

Because archive.org digitises whole bound issues/volumes (not single
articles), a "hit" downloads the FULL ISSUE PDF containing the target
paper, not an article-extracted PDF. This is flagged in the log
(`match_type` column) so downstream steps know the file is issue-level.

Usage
-----
    python scripts/fetch_bhl_archive.py --limit 30            # test batch
    python scripts/fetch_bhl_archive.py --limit 30 --dry-run  # search only, no download
    python scripts/fetch_bhl_archive.py                       # full run (resumable)

Outputs
-------
    outputs/bhl_downloads/<literature_id>.pdf   -- downloaded PDFs (hardlinks)
    outputs/bhl_downloads/_volumes/<sha1>.pdf   -- one copy per source URL
    outputs/bhl_matches.csv                     -- log (see MATCH_LOG_FIELDS)
    outputs/.bhl_cache/                         -- cached API responses (resumable, polite)

Does NOT modify docs/papers_data.json.
"""

from __future__ import annotations

import argparse
import csv
import errno
import gzip
import hashlib
import json
import os
import re
import shutil
import sys
import time
import unicodedata
from datetime import datetime
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PAPERS_JSON = PROJECT_ROOT / "docs/papers_data.json"
DOWNLOAD_DIR = PROJECT_ROOT / "outputs/bhl_downloads"
# Content store, keyed on source URL.  A scanned volume backs many articles:
# one 1880 volume is the match for sixteen separate Jordan and Garman papers.
# Downloading it per paper cost 16 fetches and 16 copies of 40.7 MB, so the
# volume is fetched once here and every <literature_id>.pdf is a hardlink to
# it.  Same bytes, same inode, and every consumer sees an ordinary file.
VOLUME_STORE = DOWNLOAD_DIR / "_volumes"
CACHE_DIR = PROJECT_ROOT / "outputs/.bhl_cache"
CACHE_SEARCH_DIR = CACHE_DIR / "ia_search"
CACHE_META_DIR = CACHE_DIR / "ia_metadata"
CACHE_TEXT_DIR = CACHE_DIR / "ia_text"
MATCH_LOG = PROJECT_ROOT / "outputs/bhl_matches.csv"

USER_AGENT = (
    "SharkLitReviewBot/1.0 (mailto:simondedman@gmail.com; "
    "academic literature acquisition for EEA elasmobranch systematic review; "
    "contact for any concern)"
)
REQUEST_TIMEOUT = 30
DELAY_MIN = 3.0
DELAY_MAX = 5.0

IA_SEARCH_URL = "https://archive.org/advancedsearch.php"
IA_METADATA_URL = "https://archive.org/metadata"
IA_DOWNLOAD_URL = "https://archive.org/download"

BHL_API_KEY = os.environ.get("BHL_API_KEY", "").strip()
BHL_BASE_URL = "https://www.biodiversitylibrary.org/api3"

MATCH_LOG_FIELDS = [
    "literature_id", "year", "journal", "title", "source", "match_type",
    "identifier", "url", "title_overlap", "status", "timestamp",
]

# Journals/keywords treated as taxonomy/paleontology even if year >= 1970.
# Deliberately follows the user-supplied illustrative list (Copeia, Cybium,
# JVP, Journal of Paleontology, Bulletin, Annales, ...) plus a handful of
# obvious extensions (paleontolog*, geological survey, museum memoirs, ...).
TAXONOMY_PALEO_KEYWORDS = [
    "copeia", "cybium",
    "journal of vertebrate paleontology", "journal of paleontology",
    "bulletin", "annales", "annals", "proceedings",
    "paleontolog", "palaeontolog", "geological survey",
    "natural history museum", "museum of natural history",
    "zoologische", "neues jahrbuch", "archiv fur", "memoir",
    "records of the", "transactions of the",
]

# Journal-name substrings that indicate a book/publisher/place rather than a
# serial -- for these we skip the journal+year candidate search and go
# straight to a plain title search.
NON_SERIAL_HINTS = [
    "press", "university of", "verlag", "publishing", "publisher",
]

DEFAULT_HEADERS = {"User-Agent": USER_AGENT}


# ---------------------------------------------------------------------------
# Small utilities
# ---------------------------------------------------------------------------

def polite_sleep() -> None:
    import random
    time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))


def strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", s or "")
        if not unicodedata.combining(c)
    )


def cache_key(*parts: str) -> str:
    h = hashlib.sha1("||".join(parts).encode("utf-8")).hexdigest()
    return h


def cache_read_json(path: Path):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return None
    return None


def cache_write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


STOPWORDS = {
    "the", "and", "of", "a", "an", "in", "on", "with", "for", "to", "from",
    "new", "species", "genus", "note", "notes", "some", "its", "part",
    "vol", "volume", "des", "der", "die", "das", "und", "von", "les", "sur",
    "una", "del", "sp", "nov", "sp.", "nov.",
}


def significant_words(text: str, min_len: int = 5) -> set[str]:
    text = strip_accents(text or "").lower()
    words = re.findall(r"[a-z]{%d,}" % min_len, text)
    return {w for w in words if w not in STOPWORDS}


# ---------------------------------------------------------------------------
# Loading + filtering the no-DOI queue
# ---------------------------------------------------------------------------

def load_target_papers(papers_json: Path = PAPERS_JSON) -> list[dict]:
    """Load papers_data.json and filter to the no-DOI old/taxonomy-paleo set."""
    data = json.loads(papers_json.read_text(encoding="utf-8"))
    targets = []
    for p in data:
        doi = (p.get("doi") or "").strip()
        # A 10.5962 DOI IS a BHL item, and acquisition_route=bhl is set by the
        # DOI-recovery pass for exactly that case. Skipping every DOI-bearing
        # row would drop the papers this harvester is best placed to fetch.
        bhl_doi = doi.startswith("10.5962") or p.get("acquisition_route") == "bhl"
        if doi and not bhl_doi:
            continue
        year = p.get("year")
        pre_1970 = isinstance(year, int) and year < 1970
        journal = (p.get("journal_clean") or p.get("journal") or "").lower()
        kw_match = any(kw in journal for kw in TAXONOMY_PALEO_KEYWORDS)
        if pre_1970 or kw_match or bhl_doi:
            targets.append(p)
    return targets


def clean_journal_name(paper: dict) -> str:
    """Best-effort clean journal name, stripping trailing ', vol, pages' cruft."""
    name = paper.get("journal_clean") or paper.get("journal") or ""
    name = name.strip()
    if not name:
        return ""
    # Strip a trailing ", <volume>, <pages>" or ", <volume>: <pages>" tail
    # e.g. "Bulletin of the United States Fish Commission, 7, 129-154"
    name = re.sub(
        r",\s*\(?[nsNS.]*\)?\s*\d+[a-zA-Z]?\s*[,:]\s*[\d–\-—]+.*$",
        "", name,
    )
    name = re.sub(r",\s*\d+\s*$", "", name)  # trailing lone volume number
    return name.strip(" .,;")


def is_non_serial(journal: str) -> bool:
    j = journal.lower()
    return any(h in j for h in NON_SERIAL_HINTS)


# ---------------------------------------------------------------------------
# archive.org channel
# ---------------------------------------------------------------------------

def ia_search(query: str) -> list[dict]:
    """Query archive.org advancedsearch, cached by query string."""
    key = cache_key("ia_search", query)
    cpath = CACHE_SEARCH_DIR / f"{key}.json"
    cached = cache_read_json(cpath)
    if cached is not None:
        return cached

    params = {
        "q": query,
        "fl[]": ["identifier", "title", "date"],
        "rows": 50,
        "output": "json",
    }
    try:
        r = requests.get(IA_SEARCH_URL, params=params, headers=DEFAULT_HEADERS,
                          timeout=REQUEST_TIMEOUT)
        polite_sleep()
        if r.status_code != 200:
            docs = []
        else:
            docs = r.json().get("response", {}).get("docs", [])
    except requests.RequestException as e:
        print(f"    [ia_search error] {e}")
        docs = []

    cache_write_json(cpath, docs)
    return docs


def ia_metadata(identifier: str) -> dict:
    key = cache_key("ia_metadata", identifier)
    cpath = CACHE_META_DIR / f"{key}.json"
    cached = cache_read_json(cpath)
    if cached is not None:
        return cached
    try:
        r = requests.get(f"{IA_METADATA_URL}/{identifier}",
                          headers=DEFAULT_HEADERS, timeout=REQUEST_TIMEOUT)
        polite_sleep()
        meta = r.json() if r.status_code == 200 else {}
    except (requests.RequestException, ValueError) as e:
        print(f"    [ia_metadata error] {e}")
        meta = {}
    cache_write_json(cpath, meta)
    return meta


def ia_fetch_text(identifier: str) -> str:
    """Fetch the item's OCR text (_djvu.txt), cached to disk as plain text."""
    tpath = CACHE_TEXT_DIR / f"{identifier}.txt"
    if tpath.exists():
        return tpath.read_text(encoding="utf-8", errors="ignore")

    url = f"{IA_DOWNLOAD_URL}/{identifier}/{identifier}_djvu.txt"
    try:
        r = requests.get(url, headers=DEFAULT_HEADERS, timeout=REQUEST_TIMEOUT)
        polite_sleep()
        text = r.text if r.status_code == 200 else ""
    except requests.RequestException as e:
        print(f"    [ia_fetch_text error] {e}")
        text = ""

    CACHE_TEXT_DIR.mkdir(parents=True, exist_ok=True)
    tpath.write_text(text, encoding="utf-8")
    return text


def pick_pdf_file(meta: dict) -> tuple[str, int] | None:
    """Pick the best full-item PDF file from an IA metadata record."""
    if meta.get("metadata", {}).get("access-restricted-item") == "true":
        return None
    best = None
    for f in meta.get("files", []):
        name = f.get("name", "")
        if not name.lower().endswith(".pdf"):
            continue
        size = int(f.get("size") or 0)
        if best is None or size > best[1]:
            best = (name, size)
    return best


def candidate_year_ok(doc: dict, year: int) -> bool:
    year_s = str(year)
    ident = doc.get("identifier", "")
    title = doc.get("title", "")
    if "index" in ident or "contents" in ident or "cumulative" in ident:
        return False
    return year_s in ident or year_s in title


def search_archive_org(journal: str, year: int, title: str,
                        title_overlap_threshold: float = 0.35) -> dict | None:
    """Search archive.org for a journal issue matching year, confirmed by
    OCR title-word overlap. Returns a match dict or None.
    """
    sig_words = significant_words(title)
    attempts: list[tuple[str, str]] = []  # (query, match_type)

    if journal and not is_non_serial(journal):
        attempts.append((f'title:("{journal}")', "ia_journal_year"))
    # Direct-title search only when the title carries enough distinctive
    # words to be discriminating -- a single-significant-word title (e.g.
    # "Ichthyology.") matches almost anything. With >=2 words plus the OCR
    # overlap confirmation below, loose hits are filtered out.
    if title and len(sig_words) >= 2:
        attempts.append((f'title:("{title[:120]}")', "ia_title_direct"))

    for query, match_type in attempts:
        docs = ia_search(query)
        if not docs:
            continue

        if match_type == "ia_journal_year":
            docs = [d for d in docs if candidate_year_ok(d, year)]
        for doc in docs[:8]:
            identifier = doc.get("identifier")
            if not identifier:
                continue
            meta = ia_metadata(identifier)
            pdf = pick_pdf_file(meta)
            if not pdf:
                continue
            pdf_name, pdf_size = pdf
            if pdf_size < 100_000:  # too small to be a real scanned issue
                continue

            # Confirm BOTH channels by OCR title-word overlap. For
            # journal+year the item is a whole issue (title alone can't
            # confirm the paper is inside); for direct-title it guards
            # against IA's fuzzy title matching returning a loose hit.
            overlap = 0.0
            if sig_words:
                text = ia_fetch_text(identifier)
                if text:
                    text_words = significant_words(text)
                    overlap = len(sig_words & text_words) / len(sig_words)
                if overlap < title_overlap_threshold:
                    continue
            else:
                overlap = 1.0  # no usable title words; accept on title match

            return {
                "source": "archive.org",
                "match_type": match_type,
                "identifier": identifier,
                "url": f"{IA_DOWNLOAD_URL}/{identifier}/{pdf_name}",
                "title_overlap": round(overlap, 2),
            }
    return None


# ---------------------------------------------------------------------------
# BHL channel (inactive without an API key)
# ---------------------------------------------------------------------------

def bhl_available() -> bool:
    return bool(BHL_API_KEY)


def search_bhl(title: str) -> dict | None:
    """Search BHL PublicationSearch by title. Inactive unless BHL_API_KEY set.

    NOTE: every op on api3 (verified empirically 2026-07) returns
    {"Status":"unauthorized"} without a registered key; there is no
    anonymous/demo key. Get one at https://www.biodiversitylibrary.org/
    (account + API key request form) and export BHL_API_KEY to activate.
    """
    if not bhl_available():
        return None
    params = {
        "op": "PublicationSearch",
        "searchterm": title,
        "searchtype": "F",
        "format": "json",
        "apikey": BHL_API_KEY,
    }
    try:
        r = requests.get(BHL_BASE_URL, params=params, headers=DEFAULT_HEADERS,
                          timeout=REQUEST_TIMEOUT)
        polite_sleep()
        data = r.json()
    except (requests.RequestException, ValueError) as e:
        print(f"    [bhl error] {e}")
        return None
    if data.get("Status") != "OK":
        return None
    results = data.get("Result") or []
    if not results:
        return None
    top = results[0]
    # BHL item/part records expose a PDF download link pattern:
    # https://www.biodiversitylibrary.org/itempdf/<ItemID>
    item_id = top.get("ItemID") or top.get("PartID")
    if not item_id:
        return None
    return {
        "source": "bhl",
        "match_type": "bhl_title_search",
        "identifier": str(item_id),
        "url": f"https://www.biodiversitylibrary.org/itempdf/{item_id}",
        "title_overlap": "",
    }


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------

def store_path_for(url: str) -> Path:
    return VOLUME_STORE / f"{hashlib.sha1(url.encode()).hexdigest()}.pdf"


def link_or_copy(src: Path, dest: Path) -> None:
    """Point dest at src's bytes, sharing the inode where the filesystem
    allows it.  Falls back to a copy across devices or at the link limit."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(f".{dest.name}.link{os.getpid()}")
    try:
        if tmp.exists():
            tmp.unlink()
        os.link(src, tmp)
    except OSError as exc:
        if exc.errno not in (errno.EXDEV, errno.EMLINK, errno.EPERM):
            raise
        shutil.copy2(src, tmp)
    os.replace(tmp, dest)


def download_pdf(url: str, dest: Path) -> tuple[bool, str]:
    """Fetch url into the content store, then hardlink dest to it.

    Returns ``linked`` rather than ``downloaded`` when the volume was already
    in the store, which is the common case for a heavily-cited volume and
    saves both the bandwidth and the disk.
    """
    store = store_path_for(url)
    if store.exists() and store.stat().st_size > 0:
        try:
            link_or_copy(store, dest)
            return True, "linked"
        except OSError as e:
            return False, f"link_failed_{e.__class__.__name__}"

    try:
        r = requests.get(url, headers=DEFAULT_HEADERS, timeout=120, stream=True)
        polite_sleep()
        if r.status_code != 200:
            return False, f"http_{r.status_code}"
        data = b""
        for chunk in r.iter_content(chunk_size=1 << 16):
            data += chunk
        if data[:4] != b"%PDF":
            return False, "not_a_pdf"
        if len(data) < 50_000:
            return False, "too_small"
        # Land in the store atomically, so an interrupted run cannot leave a
        # truncated volume that later papers would happily link to.
        store.parent.mkdir(parents=True, exist_ok=True)
        tmp = store.with_suffix(f".part{os.getpid()}")
        tmp.write_bytes(data)
        os.replace(tmp, store)
        link_or_copy(store, dest)
        return True, "downloaded"
    except requests.RequestException as e:
        return False, f"error_{e.__class__.__name__}"


def prune_volume_store(log=print) -> tuple[int, int]:
    """Drop store entries nothing links to any more.

    The store holds one extra link per volume, which costs no space while a
    <literature_id>.pdf still points at the same inode.  Once those are all
    ingested and removed, the store link is the last one and is keeping the
    bytes alive for nothing.
    """
    removed = freed = 0
    if not VOLUME_STORE.exists():
        return 0, 0
    for entry in VOLUME_STORE.glob("*.pdf"):
        st = entry.stat()
        if st.st_nlink > 1:
            continue
        entry.unlink()
        removed += 1
        freed += st.st_size
    log(f"  pruned {removed} unreferenced volumes, freed {freed / 2 ** 20:.1f} MB")
    return removed, freed


# ---------------------------------------------------------------------------
# Resumability / logging
# ---------------------------------------------------------------------------

def load_processed_ids() -> set[str]:
    if not MATCH_LOG.exists():
        return set()
    ids = set()
    with open(MATCH_LOG, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            ids.add(row["literature_id"])
    return ids


def append_log_row(row: dict) -> None:
    is_new = not MATCH_LOG.exists()
    MATCH_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(MATCH_LOG, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=MATCH_LOG_FIELDS)
        if is_new:
            w.writeheader()
        w.writerow(row)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def process_paper(paper: dict, dry_run: bool) -> str:
    lit_id = str(paper.get("literature_id"))
    year = paper.get("year")
    title = paper.get("title") or ""
    journal = clean_journal_name(paper)

    print(f"\n-> [{lit_id}] {year} | {journal[:50]!r} | {title[:70]}")

    match = None
    if bhl_available():
        match = search_bhl(title)
    if not match:
        match = search_archive_org(journal, year if isinstance(year, int) else 0, title)

    row = {
        "literature_id": lit_id, "year": year, "journal": journal,
        "title": title, "source": "", "match_type": "", "identifier": "",
        "url": "", "title_overlap": "", "status": "no_match",
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }

    if not match:
        print("   no match")
        append_log_row(row)
        return "no_match"

    row.update({
        "source": match["source"], "match_type": match["match_type"],
        "identifier": match["identifier"], "url": match["url"],
        "title_overlap": match["title_overlap"],
    })
    print(f"   MATCH ({match['source']} / {match['match_type']}): "
          f"{match['identifier']} overlap={match['title_overlap']}")

    if dry_run:
        row["status"] = "match_dry_run"
        append_log_row(row)
        return "match_dry_run"

    dest = DOWNLOAD_DIR / f"{lit_id}.pdf"
    if dest.exists():
        row["status"] = "already_downloaded"
        append_log_row(row)
        print(f"   already downloaded: {dest}")
        return "already_downloaded"

    ok, reason = download_pdf(match["url"], dest)
    row["status"] = "downloaded" if ok else f"download_failed_{reason}"
    append_log_row(row)
    print(f"   {'DOWNLOADED' if ok else 'DOWNLOAD FAILED (' + reason + ')'}: {dest.name}")
    return row["status"]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch pre-1970 / taxonomy-paleontology no-DOI PDFs "
                    "from archive.org (and BHL, if BHL_API_KEY is set).",
    )
    parser.add_argument("--limit", type=int, default=None,
                        help="Process at most N target papers")
    parser.add_argument("--dry-run", action="store_true",
                        help="Search + log matches only, do not download")
    parser.add_argument("--retry-failed", action="store_true",
                        help="Re-attempt papers previously logged as no_match "
                        "or download_failed_*")
    parser.add_argument("--papers-json", type=Path, default=PAPERS_JSON)
    parser.add_argument("--prune-store", action="store_true",
                        help="Drop volume-store entries nothing links to any "
                             "more, then exit")
    args = parser.parse_args()

    if args.prune_store:
        print(f"Pruning {VOLUME_STORE}...")
        prune_volume_store()
        return 0

    for d in (DOWNLOAD_DIR, CACHE_SEARCH_DIR, CACHE_META_DIR, CACHE_TEXT_DIR):
        d.mkdir(parents=True, exist_ok=True)

    targets = load_target_papers(args.papers_json)
    print(f"Loaded {len(targets):,} no-DOI old/taxonomy-paleontology target papers")
    print(f"BHL channel: {'ACTIVE (key set)' if bhl_available() else 'INACTIVE (no BHL_API_KEY -- archive.org only)'}")

    processed_ids = load_processed_ids()
    if args.retry_failed:
        # Only skip rows that were a genuine success; retry everything else.
        success_statuses = {"downloaded", "already_downloaded", "match_dry_run"}
        retry_ids = set()
        if MATCH_LOG.exists():
            with open(MATCH_LOG, newline="", encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    if r["status"] in success_statuses:
                        retry_ids.add(r["literature_id"])
        skip_ids = retry_ids
    else:
        skip_ids = processed_ids

    todo = [p for p in targets if str(p.get("literature_id")) not in skip_ids]
    print(f"Already processed: {len(targets) - len(todo):,} | Remaining: {len(todo):,}")

    if args.limit:
        todo = todo[: args.limit]
    print(f"Processing {len(todo):,} papers this run "
          f"({'DRY RUN' if args.dry_run else 'LIVE'})")
    print("=" * 70)

    from collections import Counter
    tally = Counter()
    for paper in todo:
        status = process_paper(paper, dry_run=args.dry_run)
        tally[status] += 1

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    for status, n in tally.most_common():
        print(f"  {status:30s}: {n:>5,}")
    total = sum(tally.values())
    hits = tally.get("downloaded", 0) + tally.get("already_downloaded", 0) + tally.get("match_dry_run", 0)
    if total:
        print(f"\n  Hit rate this run: {hits}/{total} ({hits/total*100:.1f}%)")
    print(f"\n  Log: {MATCH_LOG}")
    print(f"  PDFs: {DOWNLOAD_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
