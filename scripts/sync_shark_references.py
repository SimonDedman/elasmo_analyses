#!/usr/bin/env python3
"""
Monthly Shark-References sync.

Phases:
  0. (opt-in) Stage orphan PDFs from `database/orphan_inbox/` (or a path
     given via --orphan-inbox). Each PDF's DOI is extracted, looked up on
     Crossref, and a new row is appended to the master CSV with id ≥ 600000.
     Their DOIs land in the "known" set before Phase 2's diff, so SR re-finding
     them in the next monthly crawl will not produce a duplicate insert.
  1. Crawl SR A-Z list pages (~5 min)
  2. Diff against our known papers (parquet + papers_data.json + orphan stage)
  3. Fetch SR detail pages for genuinely new papers
  3b. (opt-out) Verify every new paper's DOI against Crossref (title + year).
      A DOI that points at a different paper is dropped from the row and
      logged to outputs/sr_doi_quarantine.csv rather than published — see the
      2026-04 incident where 45 rows carried the next literature_id's DOI.
  4. Download PDFs (where SR has a link)
  5. Update master CSV + papers_data.json
  5b. (opt-out) Append new SR rows to the base parquet, then run incremental
      schema extraction on every newly-downloaded ID — keeps the enriched
      parquet in lockstep with the master CSV.
  6. Notify via ntfy.sh + Gmail

Usage:
    python3 scripts/sync_shark_references.py                # full run (auto-resumes if checkpoint exists)
    python3 scripts/sync_shark_references.py --dry-run      # crawl + diff only
    python3 scripts/sync_shark_references.py --no-notify    # skip notifications
    python3 scripts/sync_shark_references.py --no-resume    # ignore checkpoint, start fresh
    python3 scripts/sync_shark_references.py --verbose       # debug logging
    python3 scripts/sync_shark_references.py --orphan-inbox /path/to/folder
    python3 scripts/sync_shark_references.py --no-orphan-scan
    python3 scripts/sync_shark_references.py --no-verify-dois # skip Phase 3b DOI check
    python3 scripts/sync_shark_references.py --no-extract    # skip Phase 5b

Author: Simon Dedman
Date: 2026-04-06; updated 2026-04-27 (orphan staging + post-sync extraction),
      2026-07-24 (Phase 3b DOI verification)
"""

import argparse
import csv
import fcntl
import html as html_mod
import json
import logging
import re
import smtplib
import subprocess
import sys
import time
import urllib.request
import urllib.parse
from collections import Counter
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PDF_BASE = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")
PARQUET = PROJECT_ROOT / "outputs/literature_review_enriched.parquet"
BASE_PARQUET = PROJECT_ROOT / "outputs/literature_review.parquet"
PAPERS_DATA = PROJECT_ROOT / "docs/papers_data.json"
MASTER_CSV_DIR = PROJECT_ROOT / "outputs/shark_references_bulk"
LOG_DIR = PROJECT_ROOT / "logs"
CONFIG_FILE = Path(__file__).resolve().parent / ".sr_sync_config.json"
LOCK_FILE = Path("/tmp/sr_sync.lock")
CHECKPOINT_FILE = PROJECT_ROOT / "outputs/.sr_sync_checkpoint.json"
FEEDBACK_CSV = PROJECT_ROOT / "outputs/sr_suggested_pdf_links.csv"
# DOIs SR published that demonstrably point at a different paper. Append-only
# audit trail; also the list to send upstream to shark-references.
DOI_QUARANTINE_CSV = PROJECT_ROOT / "outputs/sr_doi_quarantine.csv"
DEFAULT_ORPHAN_INBOX = PROJECT_ROOT / "database/orphan_inbox"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BASE_URL = "https://shark-references.com/literature/listAll/{letter}"
DETAIL_URL = "https://shark-references.com/literature/detailAjax/{lit_id}"
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
REQUEST_DELAY = 10  # seconds between A-Z page requests
DETAIL_DELAY = 2    # seconds between detail AJAX requests
MAX_RETRIES = 2     # 1 retry only (3.4% success rate on retries — not worth more)
PDF_DOWNLOAD_TIMEOUT = 30  # seconds (was 120; most failures are permanent, not transient)
MIN_PDF_SIZE = 50 * 1024  # 50 KB
PDF_MAGIC = b"%PDF"

# Domains that consistently block automated downloads (Cloudflare, etc.)
# Skip these entirely — they'll be added to the todo list for manual download
SKIP_DOMAINS = {
    "biodiversitylibrary.org",
    "elasmo.org",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# --- Phase 3b: DOI verification (see verify_new_paper_dois) ------------------
CROSSREF_API = "https://api.crossref.org/works"
CROSSREF_MAILTO = "simondedman@gmail.com"
CROSSREF_BATCH = 40          # DOIs per filter query
CROSSREF_DELAY = 0.4         # seconds between batches
DOI_TITLE_MIN_SIM = 0.6      # token overlap required to accept a DOI
DOI_YEAR_TOLERANCE = 1       # publication year may differ by this much
# Words too common in this corpus to carry any matching signal
_TITLE_STOP = {
    "the", "a", "an", "of", "on", "in", "for", "and", "or", "to", "from",
    "with", "by", "using", "at", "is", "are", "new", "first", "record",
}


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
def setup_logging(verbose: bool = False) -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"sr_sync_{datetime.now():%Y%m%d}.log"

    logger = logging.getLogger("sr_sync")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s  %(levelname)-8s  %(message)s"))

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG if verbose else logging.INFO)
    ch.setFormatter(logging.Formatter("%(levelname)-8s  %(message)s"))

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


# ---------------------------------------------------------------------------
# Lock file
# ---------------------------------------------------------------------------
def acquire_lock() -> object:
    """Acquire an exclusive lock file. Returns the file handle or exits."""
    # Clear stale locks older than 24 hours
    if LOCK_FILE.exists():
        age = time.time() - LOCK_FILE.stat().st_mtime
        if age > 86400:
            LOCK_FILE.unlink()

    fh = open(LOCK_FILE, "w")
    try:
        fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fh.write(str(datetime.now()))
        fh.flush()
        return fh
    except OSError:
        fh.close()
        print("ERROR: Another sr_sync instance is already running.", file=sys.stderr)
        sys.exit(1)


def release_lock(fh):
    try:
        fcntl.flock(fh, fcntl.LOCK_UN)
        fh.close()
        LOCK_FILE.unlink(missing_ok=True)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
def load_config() -> dict:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}


# ---------------------------------------------------------------------------
# Checkpoint / resume
# ---------------------------------------------------------------------------
def load_checkpoint() -> dict:
    """Load checkpoint from previous interrupted run."""
    if CHECKPOINT_FILE.exists():
        try:
            return json.loads(CHECKPOINT_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_checkpoint(data: dict):
    """Save checkpoint atomically (write tmp then rename)."""
    tmp = CHECKPOINT_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    tmp.rename(CHECKPOINT_FILE)


def clear_checkpoint():
    """Remove checkpoint after successful completion."""
    CHECKPOINT_FILE.unlink(missing_ok=True)
    CHECKPOINT_FILE.with_suffix(".tmp").unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------
def fetch_with_retry(session, url, method="get", max_retries=None, **kwargs):
    """Fetch a URL with exponential-backoff retries."""
    retries = max_retries if max_retries is not None else MAX_RETRIES
    for attempt in range(retries):
        try:
            timeout = kwargs.pop("timeout", 60)
            if method == "get":
                resp = session.get(url, timeout=timeout, **kwargs)
            else:
                resp = session.post(url, timeout=timeout, **kwargs)
            resp.raise_for_status()
            return resp
        except (requests.RequestException, requests.Timeout) as e:
            if attempt < retries - 1:
                wait = 4 * (2 ** attempt)
                logging.getLogger("sr_sync").warning(
                    f"  Retry {attempt+1}/{retries} for {url}: {e} (waiting {wait}s)"
                )
                time.sleep(wait)
            else:
                raise


# ---------------------------------------------------------------------------
# Phase 1: Crawl A-Z pages
# ---------------------------------------------------------------------------
def crawl_all_letters(session, log) -> list[dict]:
    """Crawl all 26 letter pages, extract every paper's basic info."""
    all_papers = []

    for i, letter in enumerate(LETTERS):
        url = BASE_URL.format(letter=letter)
        log.info(f"[{i+1}/26] Fetching letter {letter}...")

        try:
            resp = fetch_with_retry(session, url)
            papers = parse_list_page(resp.text)
            all_papers.extend(papers)
            log.info(f"  {letter}: {len(papers)} papers")
        except Exception as e:
            log.error(f"  FAILED on letter {letter}: {e}")

        if i < len(LETTERS) - 1:
            time.sleep(REQUEST_DELAY)

    log.info(f"Crawl complete: {len(all_papers)} total papers on SR")
    return all_papers


def parse_list_page(html: str) -> list[dict]:
    """Parse a single letter page into paper dicts."""
    soup = BeautifulSoup(html, "html.parser")
    papers = []

    for entry in soup.find_all("div", class_="list-entry"):
        paper = {}

        # literature_id
        img = entry.find("img", attrs={"data-ajax": True})
        if img:
            m = re.search(r"/(\d+)$", img["data-ajax"])
            if m:
                paper["literature_id"] = m.group(1)
        if "literature_id" not in paper:
            continue  # skip entries we can't identify

        # PDF URL
        images_div = entry.find("div", class_="list-images")
        paper["pdf_url"] = ""
        if images_div:
            for a in images_div.find_all("a", href=True):
                if a.find("img", src=lambda x: x and "download" in x.lower() if x else False):
                    paper["pdf_url"] = a["href"]
                    break

        # Authors (includes year in parentheses)
        auth_span = entry.find("span", class_="lit-authors")
        paper["authors"] = auth_span.get_text(strip=True) if auth_span else ""

        # Year from authors string
        year_match = re.search(r"\((\d{4})\)", paper["authors"])
        paper["year"] = int(year_match.group(1)) if year_match else None

        # DOI
        doi_link = entry.find("a", href=lambda x: x and "doi.org" in x)
        paper["doi"] = doi_link.get_text(strip=True) if doi_link else ""

        # Findspot (journal)
        fs = entry.find("span", class_="lit-findspot")
        paper["findspot"] = fs.get_text(strip=True) if fs else ""

        # Title: text between authors and findspot in list-text div
        text_div = entry.find("div", class_="list-text")
        paper["title"] = ""
        if text_div:
            # Get text content, remove authors and findspot portions
            full = text_div.get_text(" ", strip=True)
            # Strip the authors portion from the beginning
            if paper["authors"] and paper["authors"] in full:
                full = full[full.index(paper["authors"]) + len(paper["authors"]):]
            # Strip DOI portion
            full = re.sub(r"DOI:\s*10\.\S+", "", full)
            # Strip findspot from the end
            if paper["findspot"] and paper["findspot"] in full:
                idx = full.index(paper["findspot"])
                full = full[:idx]
            paper["title"] = full.strip()

        papers.append(paper)

    return papers


# ---------------------------------------------------------------------------
# DOI normalisation
# ---------------------------------------------------------------------------
def _normalise_doi(doi: str) -> str:
    """Lowercase, strip URL prefix and trailing punctuation."""
    if not doi:
        return ""
    doi = doi.strip().lower()
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi)
    return doi.rstrip(".,;")


# ---------------------------------------------------------------------------
# Phase 2: Diff
# ---------------------------------------------------------------------------
def _normalise_lid(lid) -> str:
    """literature_id as a bare string: '123.0' and 123 both become '123'."""
    s = str(lid if lid is not None else "").strip()
    if s.lower() in ("", "nan", "none", "<na>"):
        return ""
    return re.sub(r"\.0+$", "", s)


def diff_papers(sr_papers, known_ids, known_dois, needs_pdf_ids, needs_pdf_dois, log,
                counts: dict | None = None):
    """
    Categorise SR papers into NEW, NEEDS_PDF, or HAVE.

    Matches by literature_id first, then by DOI to catch papers we have
    under synthetic 500k+ IDs from non-SR sources.

    A paper is KNOWN if it is in the parquet OR in papers_data.json. The two
    stores mean different things: the parquet holds papers we have (and have
    extracted), papers_data.json holds papers we want but lack. Until
    2026-09-14 only the parquet counted as known, so every paper a previous
    sync had queued without a PDF (2,642 of them on 2026-09-14) was
    re-declared "new" on every run: re-fetched in Phase 3 at 2 s each (~88
    min), and counted in the headline "N new papers" (2,760 reported against
    ~118 genuinely new on 2026-09-03). Queued papers now flow to the
    needs-PDF branch instead, which is where an SR download link for them
    belongs.

    Args:
        sr_papers: list of dicts from crawl
        known_ids: set of literature_id strings in our parquet
        known_dois: set of normalised DOI strings in our parquet
        needs_pdf_ids: set of literature_id strings in papers_data.json
        needs_pdf_dois: set of normalised DOI strings in papers_data.json
        counts: optional dict, filled with the breakdown
            {"new", "known_parquet", "known_queue_only", "needs_pdf"} so the
            summary can report the queue-only papers separately.

    Returns:
        (new_papers, needs_pdf_papers)
    """
    new_papers = []
    needs_pdf = []
    n_parquet = n_queue_only = 0

    for p in sr_papers:
        lid = _normalise_lid(p["literature_id"])
        doi = _normalise_doi(p.get("doi", ""))

        in_parquet = lid in known_ids or bool(doi and doi in known_dois)
        in_queue = (bool(lid) and lid in needs_pdf_ids) or bool(doi and doi in needs_pdf_dois)

        if not in_parquet and not in_queue:
            new_papers.append(p)
            continue

        if in_parquet:
            n_parquet += 1
        else:
            n_queue_only += 1

        # We know the paper; if it is still on the want-list and SR links a
        # PDF, try that link.
        if in_queue and p.get("pdf_url"):
            needs_pdf.append(p)

    if counts is not None:
        counts.update({"new": len(new_papers), "known_parquet": n_parquet,
                       "known_queue_only": n_queue_only, "needs_pdf": len(needs_pdf)})
    log.info(f"Diff results: {len(new_papers)} genuinely new, "
             f"{len(needs_pdf)} known-needing-PDF-with-SR-link "
             f"({n_queue_only} known only from papers_data.json, not counted as new)")
    return new_papers, needs_pdf


# ---------------------------------------------------------------------------
# Phase 3: Fetch details for new papers
# ---------------------------------------------------------------------------
def fetch_details(session, paper, log) -> dict:
    """Fetch detailed info for a single paper via detailAjax."""
    lit_id = paper["literature_id"]
    url = DETAIL_URL.format(lit_id=lit_id)

    try:
        resp = fetch_with_retry(session, url, timeout=30)
        soup = BeautifulSoup(resp.text, "html.parser")
        details = {}

        for label in soup.find_all("span", class_="label"):
            label_text = label.get_text(strip=True).rstrip(":")
            value_parts = []
            for sib in label.next_siblings:
                if sib.name == "br":
                    break
                if sib.name == "span" and "label" in sib.get("class", []):
                    break
                text = sib.get_text(strip=True) if hasattr(sib, "get_text") else str(sib).strip()
                if text:
                    value_parts.append(text)
            value = " ".join(value_parts).strip()
            if value:
                details[label_text.lower().replace(" ", "_")] = value

        # Collect download links from detail page too
        dl_links = []
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if any(x in href.lower() for x in [".pdf", "researchgate", "academia.edu"]):
                dl_links.append(href)
        if dl_links:
            details["download_links"] = "|".join(dl_links)

        return details

    except Exception as e:
        log.warning(f"  Failed to fetch details for {lit_id}: {e}")
        return {}


def enrich_new_papers(session, new_papers, checkpoint, log):
    """Fetch details for all new papers, resuming from checkpoint."""
    # Restore cached details from checkpoint
    cached_details = checkpoint.get("phase3_details", {})
    resume_after = checkpoint.get("phase3_last_id", None)

    if cached_details:
        restored = 0
        for paper in new_papers:
            lid = str(paper["literature_id"])
            if lid in cached_details:
                paper.update(cached_details[lid])
                restored += 1
        log.info(f"Restored details for {restored}/{len(new_papers)} papers from checkpoint")

    # Find where to resume
    skip = bool(resume_after)
    to_fetch = []
    for paper in new_papers:
        lid = str(paper["literature_id"])
        if lid in cached_details:
            continue  # already have details
        if skip:
            if lid == resume_after:
                skip = False  # found the resume point, start from next
            continue
        to_fetch.append(paper)

    if not to_fetch:
        log.info(f"All {len(new_papers)} paper details already cached")
        return

    log.info(f"Fetching details for {len(to_fetch)} papers ({len(new_papers) - len(to_fetch)} already cached)...")
    for i, paper in enumerate(to_fetch):
        lid = str(paper["literature_id"])
        if (i + 1) % 50 == 0 or i == 0 or i == len(to_fetch) - 1:
            log.info(f"  [{i+1}/{len(to_fetch)}] Fetching details...")
        log.debug(f"  [{i+1}/{len(to_fetch)}] detail for {lid}")
        details = fetch_details(session, paper, log)
        paper.update(details)
        cached_details[lid] = details

        # Checkpoint every 100 papers
        if (i + 1) % 100 == 0:
            checkpoint["phase3_details"] = cached_details
            checkpoint["phase3_last_id"] = lid
            save_checkpoint(checkpoint)

        if i < len(to_fetch) - 1:
            time.sleep(DETAIL_DELAY)

    # Final checkpoint for Phase 3
    checkpoint["phase3_details"] = cached_details
    checkpoint["phase3_complete"] = True
    save_checkpoint(checkpoint)


# ---------------------------------------------------------------------------
# Phase 3b: Verify each new paper's DOI actually points at that paper
#
# In 2026-04 a run landed 45 rows whose `doi` belonged to the NEXT
# literature_id, so the download helper's links opened the wrong paper for
# three months before anyone noticed. Titles and journals were correct
# throughout, which is exactly why it went unseen. The cause was never
# reproduced — parse_list_page() returns the right DOI today — so this guard
# assumes it can recur and catches it at sync time instead.
#
# A blank DOI is honest; a confidently wrong one is actively misleading. So a
# DOI that fails verification is dropped from the row and written to
# DOI_QUARANTINE_CSV with its evidence, rather than being published.
# ---------------------------------------------------------------------------
def _title_tokens(text: str) -> set:
    text = re.sub(r"<[^>]+>", " ", html_mod.unescape(text or ""))
    return {w for w in re.findall(r"[a-z]{4,}", text.lower()) if w not in _TITLE_STOP}


def _title_similarity(a: str, b: str):
    """Token overlap over the shorter title. None when either side is unusable."""
    ta, tb = _title_tokens(a), _title_tokens(b)
    if not ta or not tb:
        return None
    return len(ta & tb) / min(len(ta), len(tb))


# Two records that share a DOI are treated as the same paper only if their
# titles also agree. Token overlap over the LONGER title (two-sided), not
# _title_similarity's shorter-title denominator: that one scores a two-word
# title a perfect 1.00 against any longer title containing both words (the
# "CHIMAERAS" / "OSPREY" trap in the DOI-recovery review), and book-chapter
# rows sharing a book DOI are exactly that shape. 0.8 lets a 5-token title
# differ by one token (a trailing "[Abstract]", an authority, a translated
# word) and no more.
TITLE_AGREE_MIN = 0.8
TITLE_AGREE_YEAR_TOL = 1


def _title_agreement(a: str, b: str):
    """Token overlap over the longer title. None when either side is unusable."""
    ta, tb = _title_tokens(a), _title_tokens(b)
    if not ta or not tb:
        return None
    return len(ta & tb) / max(len(ta), len(tb))


def _doi_of(p: dict) -> str:
    """Normalised DOI of a record; "" for a missing or non-string value."""
    d = p.get("doi")
    return _normalise_doi(d) if isinstance(d, str) else ""


def _same_paper(title_a, year_a, title_b, year_b) -> bool:
    """Titles agree (two-sided >= TITLE_AGREE_MIN) and years within +/-1 when both known."""
    sim = _title_agreement(title_a or "", title_b or "")
    if sim is None or sim < TITLE_AGREE_MIN:
        return False
    ya, yb = _year_int(year_a), _year_int(year_b)
    return ya is None or yb is None or abs(ya - yb) <= TITLE_AGREE_YEAR_TOL


def _crossref_lookup(session, dois: list, log) -> dict:
    """Batch-fetch Crossref metadata. Maps lowercased DOI -> dict or None."""
    found = {}
    for i in range(0, len(dois), CROSSREF_BATCH):
        batch = dois[i:i + CROSSREF_BATCH]
        params = {
            "rows": 100,
            "select": "DOI,title,container-title,issued",
            "filter": ",".join("doi:" + d for d in batch),
            "mailto": CROSSREF_MAILTO,
        }
        try:
            resp = session.get(CROSSREF_API, params=params, timeout=60)
            items = resp.json()["message"]["items"] if resp.ok else []
        except Exception as e:
            # A failed batch must not masquerade as "not in Crossref" — that
            # would quarantine perfectly good DOIs. Retry each one singly.
            log.warning(f"  Crossref batch failed ({e}) — retrying {len(batch)} individually")
            items = []
            for d in batch:
                try:
                    r = session.get(f"{CROSSREF_API}/{d}", timeout=45)
                    if r.ok:
                        items.append(r.json()["message"])
                except Exception:
                    pass
                time.sleep(CROSSREF_DELAY)
        for it in items:
            issued = (it.get("issued", {}).get("date-parts") or [[None]])[0]
            found[it["DOI"].lower()] = {
                "title": (it.get("title") or [""])[0],
                "journal": (it.get("container-title") or [""])[0],
                "year": issued[0] if issued else None,
            }
        time.sleep(CROSSREF_DELAY)
    return {d: found.get(d) for d in dois}


def verify_new_paper_dois(session, new_papers, log) -> dict:
    """Drop any DOI whose Crossref record isn't the paper we think it is.

    Returns stats. Mutates `new_papers`: a rejected DOI is blanked in place, so
    everything written downstream (master CSV, papers_data.json, parquet) gets
    the corrected row.

    Verification needs BOTH a title match and a year match. Title alone is not
    enough: on the 2026-04 batch, three wrong DOIs scored 0.8-1.0 on title
    while being different papers published years apart (a short species-account
    title token-matched a full paper title completely). Year is what separated
    them.
    """
    withdoi = [p for p in new_papers if (p.get("doi") or "").strip()]
    if not withdoi:
        log.info("  No new papers carry a DOI — nothing to verify")
        return {"checked": 0, "ok": 0, "rejected": 0, "unverifiable": 0}

    dois = sorted({_normalise_doi(p["doi"]) for p in withdoi} - {""})
    log.info(f"  Verifying {len(dois)} DOIs across {len(withdoi)} new papers via Crossref...")
    meta = _crossref_lookup(session, dois, log)

    stats = {"checked": len(withdoi), "ok": 0, "rejected": 0, "unverifiable": 0}
    rejects = []
    for p in withdoi:
        doi = _normalise_doi(p["doi"])
        cr = meta.get(doi)
        if cr is None:
            # Not in Crossref at all (preprints, DataCite, brand-new DOIs).
            # Unverifiable is not the same as wrong — keep it, but say so.
            stats["unverifiable"] += 1
            continue

        sim = _title_similarity(p.get("title", ""), cr["title"])
        try:
            our_year = int(str(p.get("year") or "").strip() or 0)
        except ValueError:
            our_year = 0
        year_ok = (
            not our_year or cr["year"] is None
            or abs(our_year - int(cr["year"])) <= DOI_YEAR_TOLERANCE
        )

        if sim is not None and sim >= DOI_TITLE_MIN_SIM and year_ok:
            stats["ok"] += 1
            continue

        stats["rejected"] += 1
        reason = []
        if sim is None:
            reason.append("no comparable title")
        elif sim < DOI_TITLE_MIN_SIM:
            reason.append(f"title overlap {sim:.2f} < {DOI_TITLE_MIN_SIM}")
        if not year_ok:
            reason.append(f"year {our_year} vs Crossref {cr['year']}")
        rejects.append({
            "literature_id": p.get("literature_id", ""),
            "year": p.get("year", ""),
            "authors": p.get("authors", ""),
            "title": p.get("title", ""),
            "findspot": p.get("findspot", ""),
            "rejected_doi": p["doi"],
            "doi_actually_is": re.sub(r"<[^>]+>", "", html_mod.unescape(cr["title"] or "")),
            "doi_journal": cr["journal"],
            "doi_year": cr["year"],
            "reason": "; ".join(reason),
        })
        log.warning(
            f"  DOI rejected for {p.get('literature_id')}: {p['doi']} "
            f"is \"{(cr['title'] or '')[:60]}\" ({'; '.join(reason)})"
        )
        p["doi"] = ""  # never publish a link we know points elsewhere

    if rejects:
        DOI_QUARANTINE_CSV.parent.mkdir(parents=True, exist_ok=True)
        newfile = not DOI_QUARANTINE_CSV.exists()
        with open(DOI_QUARANTINE_CSV, "a", newline="", encoding="utf-8") as f:
            # verified_correct_doi is left blank here: this pass only proves a
            # DOI is wrong, not what the right one is. Fill it in by hand (or
            # from a re-crawl) before sending the file to shark-references.
            w = csv.DictWriter(f, fieldnames=[
                "detected", "literature_id", "year", "authors", "title", "findspot",
                "rejected_doi", "doi_actually_is", "doi_journal", "doi_year", "reason",
                "verified_correct_doi",
            ], extrasaction="ignore")
            if newfile:
                w.writeheader()
            stamp = f"{datetime.now():%Y-%m-%d}"
            for r in rejects:
                w.writerow({"detected": stamp, **r})
        log.warning(
            f"  {len(rejects)} DOI(s) quarantined -> {DOI_QUARANTINE_CSV.name} "
            f"(these are SR data errors worth reporting upstream)"
        )

    log.info(
        f"  DOI check: {stats['ok']} verified, {stats['rejected']} rejected, "
        f"{stats['unverifiable']} not in Crossref"
    )
    return stats


# ---------------------------------------------------------------------------
# Phase 4: Download + validate PDFs
# ---------------------------------------------------------------------------
def clean_for_filename(text: str, max_len: int = 50) -> str:
    if not text:
        return "Unknown"
    text = str(text).strip()
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", text)
    text = re.sub(r"[\n\r\t]", " ", text)
    text = re.sub(r"\s+", " ", text)
    if len(text) > max_len:
        text = text[:max_len].rsplit(" ", 1)[0]
    return text.strip() or "Unknown"


def extract_first_author(authors: str) -> str:
    if not authors:
        return "Unknown"
    authors = str(authors).strip()
    first = re.split(r"\s*&\s*", authors)[0].strip()
    first = re.sub(r"\(\d{4}\)", "", first).strip()
    if "," in first:
        return clean_for_filename(first.split(",")[0], max_len=20)
    parts = first.split()
    return clean_for_filename(parts[-1] if parts else "Unknown", max_len=20)


def build_pdf_path(paper: dict) -> Path:
    """Target path for this record, per scripts/lib/library_naming.py.

    That module is the single definition, because build_pdf_id_map.py regenerates
    this name to decide which file belongs to which paper: two copies of the rule
    means the map stops finding files the moment they drift.
    """
    from lib.library_naming import build_pdf_path as _build
    return _build(paper, base=PDF_BASE)


def validate_pdf(filepath: Path, log) -> bool:
    """Check that a downloaded file is a real PDF."""
    if not filepath.exists():
        log.warning(f"  Validation: file does not exist: {filepath.name}")
        return False

    size = filepath.stat().st_size
    if size < MIN_PDF_SIZE:
        log.warning(f"  Validation: too small ({size} bytes): {filepath.name}")
        return False

    with open(filepath, "rb") as f:
        header = f.read(4)
    if header != PDF_MAGIC:
        log.warning(f"  Validation: not a PDF (header={header!r}): {filepath.name}")
        return False

    return True


def download_pdf(session, paper, log) -> bool:
    """Download and validate a PDF. Returns True on success."""
    pdf_url = paper.get("pdf_url", "")
    if not pdf_url:
        return "skip"

    # Make absolute URL if relative
    if pdf_url.startswith("/"):
        pdf_url = "https://shark-references.com" + pdf_url

    # Skip known-blocked domains
    for domain in SKIP_DOMAINS:
        if domain in pdf_url:
            log.debug(f"  Skipping blocked domain ({domain}): {paper['literature_id']}")
            return "skip"

    target = build_pdf_path(paper)

    if target.exists():
        log.info(f"  PDF already exists: {target.name}")
        return "exists"

    try:
        resp = fetch_with_retry(session, pdf_url, timeout=PDF_DOWNLOAD_TIMEOUT)

        # Check HTTP content type as early warning
        ct = resp.headers.get("Content-Type", "")
        if "html" in ct.lower():
            # Log the literature_id too: this branch is ~27% of all Phase 4
            # failure events, and without an id none of them can be joined back
            # to corpus metadata for the failure analysis, so the single
            # largest paywall signal we have was undiagnosable by publisher.
            log.warning(f"  PDF URL returned HTML (likely paywall) for "
                        f"{paper.get('literature_id', '?')}: {pdf_url}")
            return False

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(resp.content)

        if validate_pdf(target, log):
            log.info(f"  Downloaded: {target.name}")
            return True
        else:
            target.unlink(missing_ok=True)
            return False

    except Exception as e:
        log.warning(f"  Download failed for {paper['literature_id']}: {e}")
        target.unlink(missing_ok=True)
        return False


# ---------------------------------------------------------------------------
# Phase 5: Update state
# ---------------------------------------------------------------------------
# A monthly sync genuinely adds ~100-300 papers. Appending more than this in
# one run means the dedupe has probably stopped matching, so it is logged as
# an error to make that visible rather than letting the file quietly double.
MASTER_CSV_PLAUSIBLE_APPEND = 600


def _normalise_title(text) -> str:
    """Lowercase alphanumeric words only, HTML and punctuation stripped."""
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return ""
    text = re.sub(r"<[^>]+>", " ", html_mod.unescape(str(text)))
    return " ".join(re.findall(r"[^\W_]+", text.lower()))


def _year_int(value):
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None


# Titles that recur across distinct papers by construction: a comment and
# its reply, an erratum, a book review. The live master CSV has title+year
# keys of this kind carried by different DOIs ("comment on an early miocene
# extinction in pelagic sharks", 2021), so they are never a duplicate signal.
_GENERIC_TITLE_PREFIXES = (
    "comment on", "comments on", "reply to", "response to", "a reply to",
    "erratum", "errata", "corrigendum", "correction to", "correction",
    "book review", "review of", "editorial", "introduction", "preface",
    "obituary", "in memoriam", "abstracts", "proceedings",
)


def _title_year_key(title, year) -> str:
    t, y = _normalise_title(title), _year_int(year)
    # Very short titles ("Sharks.", "Editorial") collide across papers, so
    # they are not trusted as a duplicate signal on their own.
    if y is None or len(t.split()) < 4 or t.startswith(_GENERIC_TITLE_PREFIXES):
        return ""
    return f"{y}|{t}"


def _title_year_duplicate(key: str, doi: str, key_dois: dict) -> bool:
    """A title+year hit counts only when the DOIs can't tell the rows apart.

    ``key_dois`` maps each key to the set of normalised DOIs carrying it
    ("" for a row with no DOI). Two rows that both carry a DOI and disagree
    are different papers however alike their titles.
    """
    if not key or key not in key_dois:
        return False
    dois = key_dois[key]
    return not doi or "" in dois or doi in dois


def master_row_title(row) -> str:
    """The bare title of a master-CSV row (a dict).

    Sync-appended rows carry `title`. The January bulk rows do not: their
    `citation` is title + findspot, truncated at ~150 characters, so it
    never equals a bare title. Their `full_text` is authors + title +
    findspot + DOI in full, so the title is recovered by removing the
    authors prefix, the DOI tail, and the findspot suffix.
    """
    def ok(v):
        return isinstance(v, str) and v.strip()

    if ok(row.get("title")):
        return row["title"]
    ft, a, fs = row.get("full_text"), row.get("authors"), row.get("findspot")
    if ok(ft):
        ft = re.sub(r"\s*DOI:\s*10\.\S+\s*$", "", ft.strip())
        if ok(a) and ft.startswith(a):
            ft = ft[len(a):]
        if ok(fs):
            i = ft.rfind(fs.strip())
            if i > 0:
                ft = ft[:i]
        return ft.strip()
    c = row.get("citation")
    if ok(c) and ok(fs):
        i = c.find(fs.strip()[:20])
        if i > 0:
            c = c[:i]
    return c if ok(c) else ""


def select_master_csv_appends(df_existing: pd.DataFrame, df_new: pd.DataFrame):
    """Decide which rows of ``df_new`` are genuinely absent from the master CSV.

    A row is a duplicate if it matches an existing row on ANY of
    literature_id, normalised DOI, or exact normalised title + year. These
    are supplements, not alternatives: until 2026-09-14 this was an if/elif,
    so whenever the literature_id column existed the DOI branch was never
    reached, and 30,909 of the 34,772 master rows carry no literature_id at
    all. The dedupe therefore compared against 11% of the file.

    The existing title comes from master_row_title(), since the January
    bulk rows keep it embedded in ``full_text`` rather than in ``title``.

    Returns (to_append, reasons) where ``reasons`` counts the rows dropped
    per matching key (first key that matched wins).
    """
    df_new = df_new.copy()
    if "literature_id" not in df_new.columns:
        df_new["literature_id"] = ""
    df_new["literature_id"] = df_new["literature_id"].map(_normalise_lid)

    def col(df, name):
        return df[name] if name in df.columns else pd.Series([None] * len(df), index=df.index)

    existing_ids = set(col(df_existing, "literature_id").map(_normalise_lid)) - {""}
    existing_dois = set(col(df_existing, "doi").map(
        lambda d: _normalise_doi(d) if isinstance(d, str) else "")) - {""}
    existing_ty: dict = {}
    for r in df_existing.to_dict("records"):
        k = _title_year_key(master_row_title(r), r.get("year"))
        if k:
            d = r.get("doi")
            existing_ty.setdefault(k, set()).add(_normalise_doi(d) if isinstance(d, str) else "")

    reasons = {"literature_id": 0, "doi": 0, "title_year": 0, "within_batch": 0,
               "title_year_ids": []}
    keep = []
    seen_ids, seen_dois, seen_ty = set(), set(), {}
    for _, r in df_new.iterrows():
        lid = r["literature_id"]
        doi = _normalise_doi(r.get("doi") if isinstance(r.get("doi"), str) else "")
        ty = _title_year_key(r.get("title"), r.get("year"))
        if lid and lid in existing_ids:
            reasons["literature_id"] += 1
            keep.append(False)
        elif doi and doi in existing_dois:
            reasons["doi"] += 1
            keep.append(False)
        elif _title_year_duplicate(ty, doi, existing_ty):
            # The least certain key, so the ids are kept for the log.
            reasons["title_year"] += 1
            reasons["title_year_ids"].append(lid)
            keep.append(False)
        elif ((lid and lid in seen_ids) or (doi and doi in seen_dois)
              or _title_year_duplicate(ty, doi, seen_ty)):
            reasons["within_batch"] += 1
            keep.append(False)
        else:
            keep.append(True)
            seen_ids.add(lid)
            seen_dois.add(doi)
            if ty:
                seen_ty.setdefault(ty, set()).add(doi)
    return df_new[pd.Series(keep, index=df_new.index, dtype=bool)], reasons


def check_append_plausible(n_append: int, n_input: int, log,
                           limit: int | None = None) -> str:
    """Make a dedupe that has stopped working visible.

    Returns "" when the count is plausible, else a warning message. The
    write still goes ahead (a genuinely large SR release is possible), but
    the message is logged as an error AND is meant to be put into
    ``stats["errors"]`` by the caller, so it reaches the email and the ntfy
    headline rather than only the log file.
    """
    if limit is None:
        limit = MASTER_CSV_PLAUSIBLE_APPEND
    if n_append <= limit:
        return ""
    msg = (f"IMPLAUSIBLE master CSV append: {n_append} of {n_input} offered rows "
           f"were 'new' (limit {limit}); check the dedupe before trusting it")
    log.error(f"  {msg}")
    return msg


def append_to_master_csv(new_papers, log, errors: list | None = None) -> int:
    """Append new papers to the most recent master CSV. Returns rows appended.

    An implausible append count is added to ``errors`` (pass stats["errors"]).
    """
    MASTER_CSV_DIR.mkdir(parents=True, exist_ok=True)
    csv_files = sorted(MASTER_CSV_DIR.glob("shark_references_complete_*.csv"),
                       key=lambda p: p.stat().st_mtime)
    if not csv_files:
        log.warning("No master CSV found — creating new one")
        master = MASTER_CSV_DIR / f"shark_references_complete_{datetime.now():%Y%m%d}.csv"
        df_new = pd.DataFrame(new_papers)
        df_new.to_csv(master, index=False, encoding="utf-8")
        return len(df_new)

    master = csv_files[-1]
    df_existing = pd.read_csv(master, dtype=str)
    df_new = pd.DataFrame(new_papers)

    to_append, reasons = select_master_csv_appends(df_existing, df_new)
    log.info(f"  Master CSV dedupe: {len(df_new)} offered, {len(to_append)} to append; "
             f"dropped by id {reasons['literature_id']}, DOI {reasons['doi']}, "
             f"title+year {reasons['title_year']}, within batch {reasons['within_batch']}")
    if reasons["title_year_ids"]:
        log.warning(f"  Master CSV: {reasons['title_year']} row(s) skipped only on an exact "
                    f"title+year match with an id-less row: {reasons['title_year_ids'][:20]}")
    warning = check_append_plausible(len(to_append), len(df_new), log)
    if warning and errors is not None:
        errors.append(warning)

    if len(to_append) == 0:
        log.info("No new papers to append to master CSV")
        return 0

    df_combined = pd.concat([df_existing, to_append], ignore_index=True)
    df_combined.to_csv(master, index=False, encoding="utf-8")
    log.info(f"Appended {len(to_append)} papers to {master.name}")
    return len(to_append)


def _papers_data_mutate(**kwargs):
    """The locked read-modify-write from scripts/lib/papers_data_io.py.

    papers_data.json has more than one writer (the cascade, ingest, DOI
    recovery, coauthor scan). A naive read-modify-write here would silently
    erase rows another process added while the sync ran, so every write goes
    through the shared lock. Imported lazily so tests can repoint the module
    at a temporary file.
    """
    scripts_dir = str(Path(__file__).resolve().parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    from lib import papers_data_io
    return papers_data_io.mutate(**kwargs)


def add_to_papers_data(new_papers, downloaded_ids, log) -> int:
    """Add new papers that failed download (or had no PDF) to papers_data.json.

    Returns the number of rows added. The existing-id check is made inside
    the lock, against the file as it is at write time.
    """
    if not PAPERS_DATA.exists():
        return 0

    downloaded_ids = {_normalise_lid(i) for i in downloaded_ids}
    candidates = [p for p in new_papers
                  if _normalise_lid(p.get("literature_id", "")) not in downloaded_ids]
    if not candidates:
        return 0

    added = 0
    with _papers_data_mutate() as data:
        existing_ids = {_normalise_lid(p.get("literature_id", "")) for p in data}
        for p in candidates:
            lid = _normalise_lid(p.get("literature_id", ""))
            if not lid or lid in existing_ids:
                continue  # already on the list
            existing_ids.add(lid)
            data.append({
                "id": len(data) + 1,
                "literature_id": lid,
                "year": p.get("year", ""),
                "authors": p.get("authors", ""),
                "title": p.get("title", ""),
                "journal": p.get("findspot", ""),
                "doi": p.get("doi", ""),
                "priority_group": 3,
                "last_status": "sr_sync_new",
                "notes": f"Added by SR sync. PDF URL: {p.get('pdf_url', 'none')}",
                "oa_status": "unknown",
                "oa_url": "",
                "oa_host_type": "",
                "oa_license": "",
                "journal_clean": "",
                "publisher": "",
            })
            added += 1
        # mutate() writes on clean exit whether or not anything changed; an
        # unchanged rewrite is harmless (same rows, fresh backup).

    if added:
        log.info(f"Added {added} new papers to papers_data.json (failed/no-PDF downloads)")
    return added


def remove_from_papers_data(downloaded_ids, log, downloaded_papers=None,
                            report: dict | None = None) -> int:
    """Remove successfully-downloaded papers from papers_data.json.

    A queue row is removed if its literature_id was downloaded. It is also
    removed as the DOI twin of a downloaded paper (the same paper queued
    under a synthetic 500000+ id while SR lists it under its SR id), but
    only when ALL of these hold, checked inside the lock:

      * the row's id differs from the downloaded paper's id;
      * that DOI occurs on exactly ONE row of papers_data.json (the live
        queue has 21 DOIs shared by 2-3 distinct rows: book chapters on a
        book DOI, a symposium issue's papers on one DOI);
      * the titles agree (_same_paper: two-sided token overlap >= 0.8, year
        within +/-1 when both are known).

    Any other row sharing a downloaded DOI is kept and counted into
    ``report["same_doi_kept"]`` (with examples in
    ``report["same_doi_kept_rows"]``) so the summary can show it.

    ``downloaded_papers`` are the SR paper dicts that were downloaded; only
    their literature_id, doi, title and year are read. Returns the number of
    rows removed, counted inside the lock.
    """
    downloaded_ids = {_normalise_lid(i) for i in (downloaded_ids or ())} - {""}
    refs = [p for p in (downloaded_papers or ())
            if _doi_of(p)
            and _normalise_lid(p.get("literature_id", "")) in downloaded_ids]
    if not downloaded_ids or not PAPERS_DATA.exists():
        return 0

    kept_rows = []
    with _papers_data_mutate(allow_deletions=True) as data:
        before = len(data)
        doi_count = Counter(_doi_of(p) for p in data)
        doi_count.pop("", None)
        refs_by_doi: dict = {}
        for r in refs:
            refs_by_doi.setdefault(_doi_of(r), []).append(r)

        def gone(p):
            lid = _normalise_lid(p.get("literature_id", ""))
            if lid in downloaded_ids:
                return True
            doi = _doi_of(p)
            if not doi or doi not in refs_by_doi:
                return False
            twins = [r for r in refs_by_doi[doi]
                     if _normalise_lid(r["literature_id"]) != lid
                     and _same_paper(r.get("title"), r.get("year"),
                                     p.get("title"), p.get("year"))]
            if doi_count[doi] == 1 and twins:
                return True
            kept_rows.append({"literature_id": lid, "doi": doi,
                              "doi_rows_in_queue": doi_count[doi],
                              "title_agrees": bool(twins),
                              "title": (p.get("title") or "")[:80]})
            return False

        # Slice assignment: mutate() writes the list object it handed out.
        data[:] = [p for p in data if not gone(p)]
        removed = before - len(data)
        remaining = len(data)

    if kept_rows:
        log.warning(f"  Kept {len(kept_rows)} queue row(s) sharing a downloaded paper's DOI "
                    f"(DOI on several rows, or titles disagree): "
                    f"{[r['literature_id'] for r in kept_rows[:20]]}")
    if report is not None:
        report["same_doi_kept"] = report.get("same_doi_kept", 0) + len(kept_rows)
        report.setdefault("same_doi_kept_rows", []).extend(kept_rows)
    if removed:
        log.info(f"Removed {removed} entries from papers_data.json ({remaining} remaining)")
    return removed


def generate_feedback_report(sr_papers, known_ids, needs_pdf_ids, log):
    """
    Generate CSV of papers where we have a PDF but SR doesn't list a download.
    These are candidates to suggest to SR.
    """
    # Papers in our DB that SR lists without a PDF link
    suggestions = []
    for p in sr_papers:
        lid = str(p["literature_id"])
        if lid in known_ids and lid not in needs_pdf_ids and not p.get("pdf_url"):
            # We have this paper (and have its PDF) but SR doesn't show a download
            # Check if the PDF actually exists on disk
            pdf_path = build_pdf_path(p)
            if pdf_path.exists():
                suggestions.append({
                    "literature_id": lid,
                    "authors": p.get("authors", ""),
                    "year": p.get("year", ""),
                    "title": p.get("title", ""),
                    "doi": p.get("doi", ""),
                    "our_pdf_path": str(pdf_path),
                })

    if suggestions:
        df = pd.DataFrame(suggestions)
        df.to_csv(FEEDBACK_CSV, index=False, encoding="utf-8")
        log.info(f"SR feedback report: {len(suggestions)} papers where we have PDF but SR doesn't")
    else:
        log.info("SR feedback report: no suggestions this run")

    return len(suggestions)


# ---------------------------------------------------------------------------
# Phase 5c: Hardlink sweep
# ---------------------------------------------------------------------------

def run_dedupe_sweep(log) -> tuple[int, int]:
    """Collapse byte-identical library PDFs onto shared inodes.

    Returns (bytes reclaimed, files relinked).  Delegates to
    dedupe_hardlink so the sweep, the audit workbook, and the one-off run
    all share a single definition of what counts as a duplicate.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import dedupe_hardlink as dh

    groups = dh.scan(dh.DEFAULT_ROOT, log=lambda m: log.info(f"  {m.strip()}"))
    actionable = [g for g in groups if g["n_inodes"] > 1]
    if not actionable:
        log.info("  no new duplicates")
        return 0, 0

    actions = []
    for g in actionable:
        actions.extend(dh.relink_group(g, dry_run=False,
                                       log=lambda m: log.warning(m)))
    linked = [a for a in actions if a["status"] == "linked"]
    reclaimed = sum(a["size"] for a in linked)

    ok, bad = dh.verify(actions, log=lambda m: log.error(m))
    if bad:
        # Never report a saving that failed its own check.
        log.error(f"  {bad} relinked files failed verification")
    log.info(f"  linked {len(linked)} files, reclaimed "
             f"{reclaimed / 2 ** 20:.1f} MB, verified {ok}")
    return reclaimed, len(linked)


# ---------------------------------------------------------------------------
# Phase 6: Notifications
# ---------------------------------------------------------------------------
def notify_ntfy(topic: str, message: str, title: str = "SR Sync", priority: str = "default"):
    """Send a push notification via ntfy.sh."""
    try:
        data = message.encode("utf-8")
        req = urllib.request.Request(
            f"https://ntfy.sh/{topic}",
            data=data,
            headers={
                "Title": title,
                "Priority": priority,
            },
        )
        urllib.request.urlopen(req, timeout=15)
    except Exception as e:
        logging.getLogger("sr_sync").warning(f"ntfy notification failed: {e}")


def notify_gmail(config: dict, subject: str, body: str):
    """Send a summary email via Gmail SMTP."""
    addr = config.get("gmail_address", "")
    password = config.get("gmail_app_password", "")
    to = config.get("notify_to", addr)

    if not addr or not password:
        logging.getLogger("sr_sync").warning("Gmail not configured — skipping email")
        return

    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = addr
        msg["To"] = to

        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as smtp:
            smtp.login(addr, password)
            smtp.send_message(msg)

        logging.getLogger("sr_sync").info("Summary email sent")
    except Exception as e:
        logging.getLogger("sr_sync").warning(f"Gmail notification failed: {e}")


# ---------------------------------------------------------------------------
# Phase 0 (orphan staging) and Phase 5b (parquet propagation + extraction)
# ---------------------------------------------------------------------------

def stage_orphan_inbox(inbox: Path, log) -> dict:
    """Run stage_orphan_pdfs against an inbox folder. Returns its stats dict.

    Imports lazily so the dependency is only required when the user opts in
    via --orphan-inbox.
    """
    if not inbox.exists() or not inbox.is_dir():
        log.info(f"  Orphan inbox {inbox} does not exist — skipping")
        return {"staged": 0, "failed": 0, "new_ids": [], "log_lines": []}

    pdfs = sorted(inbox.glob("*.pdf"))
    if not pdfs:
        log.info(f"  No PDFs in orphan inbox {inbox}")
        return {"staged": 0, "failed": 0, "new_ids": [], "log_lines": []}

    log.info(f"  Staging {len(pdfs)} PDFs from {inbox}")
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from stage_orphan_pdfs import stage_pdfs  # local import; large dependency
    result = stage_pdfs(pdfs, no_network=False)
    log.info(f"  Orphan staging: {result['staged']} new master rows, "
             f"{result['failed']} unresolved")
    for line in result["log_lines"]:
        log.info(f"    {line}")
    return result


def propagate_to_base_parquet(new_papers: list[dict], log) -> int:
    """Append new SR-sync-discovered papers to ``literature_review.parquet``.

    The base parquet has 1500+ technique columns from earlier extraction
    work — those stay NaN/zero for new rows and are filled in by the
    follow-up incremental extraction step. Returns the number of rows
    actually appended (after dedup by literature_id).
    """
    if not BASE_PARQUET.exists():
        log.warning(f"  Base parquet {BASE_PARQUET} not found — cannot propagate")
        return 0

    df_base = pd.read_parquet(BASE_PARQUET)
    df_base["literature_id"] = df_base["literature_id"].astype(str)
    existing_ids = set(df_base["literature_id"].dropna())

    # Build new rows. Keep only the columns the base parquet has.
    base_cols = list(df_base.columns)
    new_rows = []
    for p in new_papers:
        lid = str(p.get("literature_id", "")).strip()
        if not lid or lid in existing_ids:
            continue
        # Copy across whatever overlapping fields we have; rest default to NA.
        row = {col: p.get(col, "") for col in base_cols if col in p}
        row["literature_id"] = lid
        new_rows.append(row)

    if not new_rows:
        log.info("  No new rows to add to base parquet (all already present)")
        return 0

    df_new = pd.DataFrame(new_rows)
    # Add any missing columns expected by the base parquet schema
    for col in base_cols:
        if col not in df_new.columns:
            df_new[col] = pd.NA
    df_new = df_new[base_cols]

    df_combined = pd.concat([df_base, df_new], ignore_index=True)
    df_combined.to_parquet(BASE_PARQUET, index=False)
    log.info(f"  Base parquet: appended {len(df_new)} rows "
             f"({len(df_base)} → {len(df_combined)})")
    return len(df_new)


def run_incremental_extraction(target_ids: set[str], log) -> int:
    """Invoke extract_incremental's main logic on a set of literature_ids.

    Returns the number of papers processed (papers with PDF text). On
    error the exception is logged but not re-raised — extraction failure
    should never abort the SR sync (the next run will retry).
    """
    if not target_ids:
        return 0
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        # Lazy import to avoid pulling extraction deps when --no-extract is set
        from extract_schema_columns import (
            ALL_SCHEMAS, OUTPUT_PARQUET, EVIDENCE_CSV, PDF_BASE as EXTRACT_PDF_BASE,
            apply_incremental_results, build_pdf_index, init_worker,
            normalize_binary_columns, process_paper,
        )
    except Exception as e:
        log.error(f"  Incremental extraction unavailable (import error): {e}")
        return 0

    try:
        df_input = pd.read_parquet(BASE_PARQUET)
        df_input["literature_id"] = df_input["literature_id"].astype(str)
        needed = ["literature_id", "title", "abstract", "authors", "year", "doi"]
        rows = df_input.loc[df_input["literature_id"].isin(target_ids), needed]
        rows = rows.to_dict("records")
        if not rows:
            log.warning(f"  No matching rows in base parquet for {len(target_ids)} IDs")
            return 0

        log.info(f"  Building PDF index for incremental extraction...")
        pdf_index = build_pdf_index(EXTRACT_PDF_BASE)
        init_worker(pdf_index)

        results = []
        for r in rows:
            results.append(process_paper(r))
        evidence = []
        for r in results:
            evidence.extend(r.pop("_evidence", []))
        results_df = pd.DataFrame(results)
        with_pdf = int(results_df.get("_pdf_found", pd.Series([], dtype=bool)).sum())
        results_df = results_df.drop(columns=["_pdf_found"], errors="ignore")

        # Patch enriched parquet
        df_enr = pd.read_parquet(OUTPUT_PARQUET)
        df_enr["literature_id"] = df_enr["literature_id"].astype(str)
        results_df["literature_id"] = results_df["literature_id"].astype(str)

        # Existing rows update + brand-new rows append
        existing = set(df_enr["literature_id"])
        update_mask = results_df["literature_id"].isin(existing)
        update_df = results_df[update_mask]
        append_df = results_df[~update_mask]

        binary_cols = [c.name for s in ALL_SCHEMAS for c in s.columns]

        # apply_incremental_results() overwrites matched columns
        # unconditionally (a retracted row IS eligible for re-extraction —
        # nothing here skips it), graduates RETRACTED_STATUS ->
        # RE_EXTRACTED_STATUS for rows that were retracted before this run,
        # and normalises the binary columns so still-retracted rows
        # elsewhere in df_enr keep their NULLs. See extract_schema_columns.py.
        if len(update_df):
            df_enr, n_updated = apply_incremental_results(df_enr, update_df, binary_cols)
        else:
            n_updated = 0
        if len(append_df):
            df_enr = pd.concat([df_enr, append_df], ignore_index=True)
            df_enr = normalize_binary_columns(df_enr, binary_cols)

        df_enr.to_parquet(OUTPUT_PARQUET, index=False)
        log.info(f"  Enriched parquet: updated {len(update_df)}, "
                 f"appended {len(append_df)} (total {len(df_enr)})")

        # Append evidence rows (replacing any prior rows for these IDs)
        if evidence:
            evidence_df = pd.DataFrame(evidence)
            if EVIDENCE_CSV.exists():
                existing_ev = pd.read_csv(EVIDENCE_CSV)
                existing_ev["literature_id"] = existing_ev["literature_id"].astype(str)
                existing_ev = existing_ev[~existing_ev["literature_id"].isin(target_ids)]
                combined = pd.concat([existing_ev, evidence_df], ignore_index=True)
                combined.to_csv(EVIDENCE_CSV, index=False)
            else:
                evidence_df.to_csv(EVIDENCE_CSV, index=False)
            log.info(f"  Evidence: +{len(evidence_df)} rows")

        return with_pdf
    except Exception as e:
        log.error(f"  Incremental extraction failed: {e}", exc_info=True)
        return 0


def plan_phase5b(new_papers, needs_pdf_papers, downloaded_ids, known_ids, known_dois,
                 parquet_doi_rows: dict | None = None) -> dict:
    """Decide which downloaded papers Phase 5 removes and Phase 5b propagates.

    Returns a dict of lists of SR paper dicts:

    new_to_propagate
        genuinely new papers whose PDF was downloaded (unchanged behaviour).
    queue_only_to_propagate
        known papers that were on papers_data.json but NOT in the parquet by
        literature_id OR by DOI, whose PDF was downloaded. They need a base
        parquet row, and before 2026-09-14 they reached Phase 5b as "new"
        with Phase 3 details and Phase 3b DOI checks, so the caller runs
        those on this (small) subset before propagating.
    held_by_doi
        the SR id is not in the parquet but the DOI is, on exactly ONE
        parquet row whose title agrees (_same_paper). The parquet holds the
        paper under a synthetic 500000+ id, so it is not propagated (that
        would be a second row) and is taken off the queue.
    doi_conflict_review
        the SR id is not in the parquet and the DOI is, but on several
        parquet rows, or on one row whose title disagrees, or on a row with
        no usable title. A DOI alone cannot say whether this is the held
        paper or a different one sharing the DOI (a chapter on a book DOI).
        CHOICE: neither propagate (a wrong guess makes a duplicate row) nor
        silently skip. The paper is left on papers_data.json and counted in
        the summary as needing review, so a person decides.

    ``parquet_doi_rows`` maps a normalised DOI to [(literature_id, title,
    year), ...] for every parquet row carrying it. Without it every DOI hit
    goes to doi_conflict_review, which is the safe default.
    """
    downloaded = {_normalise_lid(i) for i in downloaded_ids} - {""}
    parquet_doi_rows = parquet_doi_rows or {}
    plan = {"new_to_propagate": [], "queue_only_to_propagate": [], "held_by_doi": [],
            "doi_conflict_review": []}
    for p in new_papers:
        if _normalise_lid(p.get("literature_id", "")) in downloaded:
            plan["new_to_propagate"].append(p)
    for p in needs_pdf_papers:
        lid = _normalise_lid(p.get("literature_id", ""))
        if not lid or lid not in downloaded or lid in known_ids:
            continue
        doi = _doi_of(p)
        if not (doi and doi in known_dois):
            plan["queue_only_to_propagate"].append(p)
            continue
        rows = parquet_doi_rows.get(doi, [])
        if len(rows) == 1 and _same_paper(p.get("title"), p.get("year"), rows[0][1], rows[0][2]):
            plan["held_by_doi"].append(p)
        else:
            plan["doi_conflict_review"].append(p)
    return plan


def phase5_removal_ids(plan: dict, downloaded_ids) -> set:
    """Downloaded ids Phase 5 may take off the queue now.

    Excludes queue-only papers (removed after Phase 5b has propagated them)
    and DOI conflicts (left queued for review; see plan_phase5b).
    """
    hold = {_normalise_lid(p["literature_id"])
            for p in plan["queue_only_to_propagate"] + plan["doi_conflict_review"]}
    return {_normalise_lid(i) for i in downloaded_ids} - {""} - hold


def build_parquet_doi_rows(df) -> dict:
    """{normalised DOI: [(literature_id, title, year), ...]} from a parquet frame."""
    out: dict = {}
    for lid, doi, title, year in zip(df["literature_id"], df["doi"], df["title"], df["year"]):
        d = _normalise_doi(doi) if isinstance(doi, str) else ""
        if d:
            out.setdefault(d, []).append((_normalise_lid(lid), title, year))
    return out


def enrich_queue_only_papers(session, papers, log) -> int:
    """Phase 3 detail fetch for the downloaded queue-only subset.

    Deliberately NOT enrich_new_papers(): that resumes from the Phase 3
    checkpoint (phase3_last_id), which would skip every paper in a different
    list, and it rewrites the checkpoint that still holds Phase 4 progress.
    The subset is small (a handful per run), so no checkpointing is needed.
    """
    for i, paper in enumerate(papers):
        paper.update(fetch_details(session, paper, log))
        if i < len(papers) - 1:
            time.sleep(DETAIL_DELAY)
    return len(papers)


def build_summary(stats: dict) -> tuple[str, str]:
    """Build short (ntfy) and long (email) summaries from run stats."""
    short = (
        f"SR sync: {stats['new_found']} new papers, "
        f"{stats['pdfs_downloaded']} PDFs downloaded, "
        f"{stats['pdf_failures']} failures"
    )
    if stats.get("orphans_staged"):
        short += f", {stats['orphans_staged']} orphans staged"
    if stats.get("extracted"):
        short += f", {stats['extracted']} extracted"
    if stats.get("dedupe_linked"):
        short += (f", {stats['dedupe_linked']} dupes linked "
                  f"({stats['dedupe_reclaimed_mb']:.0f} MB)")
    if any(str(e).startswith("IMPLAUSIBLE") for e in stats.get("errors", [])):
        short += " | WARNING implausible master CSV append (see email)"
    if stats.get("doi_conflict_review") or stats.get("same_doi_kept"):
        short += (f" | review: {stats.get('doi_conflict_review', 0)} DOI conflict(s), "
                  f"{stats.get('same_doi_kept', 0)} same-DOI row(s) kept")
    if stats.get("doi_rejected"):
        short += f" | WARNING {stats['doi_rejected']} bad DOI(s) quarantined"

    lines = [
        f"Shark-References Monthly Sync — {datetime.now():%Y-%m-%d %H:%M}",
        f"{'=' * 60}",
        f"",
        f"Papers on SR:         {stats['sr_total']:,}",
        f"Known in parquet:     {stats['known_total']:,}",
        f"Still need PDFs:      {stats['needs_pdf_total']:,}",
        f"On SR, queued in papers_data.json but not in parquet: "
        f"{stats.get('known_queue_only', 0):,} (known, NOT counted as new)",
        f"",
        f"--- Orphan staging (Phase 0) ---",
        f"Orphan PDFs scanned:  {stats.get('orphans_scanned', 0)}",
        f"Orphan rows staged:   {stats.get('orphans_staged', 0)}",
        f"Orphans unresolved:   {stats.get('orphans_failed', 0)}",
        f"",
        f"--- New papers ---",
        f"New papers found:     {stats['new_found']} (absent from parquet AND papers_data.json)",
        f"Details fetched:      {stats['details_fetched']}",
        f"",
        f"--- PDF downloads ---",
        f"PDFs downloaded:      {stats['pdfs_downloaded']}",
        f"  From new papers:    {stats['pdfs_new']}",
        f"  From known papers:  {stats['pdfs_known']}",
        f"PDF failures:         {stats['pdf_failures']}",
        f"",
        f"--- DOI verification (Phase 3b) ---",
        f"DOIs checked:         {stats.get('doi_checked', 0)}",
        f"  Verified:           {stats.get('doi_ok', 0)}",
        f"  REJECTED (dropped): {stats.get('doi_rejected', 0)}",
        f"  Not in Crossref:    {stats.get('doi_unverifiable', 0)}",
        f"",
        f"--- State updates ---",
        f"Appended to CSV:      {stats['csv_appended']}",
        f"Added to JSON:        {stats.get('json_added', 0)}",
        f"Removed from JSON:    {stats['json_removed']}",
        f"Same-DOI queue rows kept (ambiguous): {stats.get('same_doi_kept', 0)}",
        f"DOI conflicts left queued for review: {stats.get('doi_conflict_review', 0)}"
        + (f" {stats['doi_conflict_review_ids'][:20]}" if stats.get('doi_conflict_review') else ""),
        f"SR feedback entries:  {stats['feedback_count']}",
        f"",
        f"--- Parquet propagation (Phase 5b) ---",
        f"Base parquet added:   {stats.get('base_parquet_added', 0)}",
        f"Incremental extract:  {stats.get('extracted', 0)} (with PDF text)",
        f"",
        f"--- Duplicate sweep (Phase 5c) ---",
        f"PDFs hardlinked:      {stats.get('dedupe_linked', 0)}",
        f"Disk reclaimed:       {stats.get('dedupe_reclaimed_mb', 0)} MB (local only)",
        f"",
        f"Crawl errors:         {stats['crawl_errors']}",
        f"Runtime:              {stats['runtime']}",
    ]

    if stats.get("new_paper_list"):
        lines.append("")
        lines.append("--- New papers ---")
        for p in stats["new_paper_list"][:50]:  # cap at 50 in email
            lines.append(f"  [{p.get('literature_id', '?')}] {p.get('authors', '')[:60]}")
            lines.append(f"    {p.get('title', '')[:80]}")

    if stats.get("errors"):
        lines.append("")
        lines.append("--- Errors ---")
        for e in stats["errors"][:20]:
            lines.append(f"  {e}")

    return short, "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Monthly Shark-References sync",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Crawl and diff only; no downloads or state changes")
    parser.add_argument("--no-notify", action="store_true",
                        help="Skip notifications")
    parser.add_argument("--ntfy-topic", type=str, default=None,
                        help="Override ntfy.sh topic")
    parser.add_argument("--verbose", action="store_true",
                        help="Debug-level logging")
    parser.add_argument("--no-resume", action="store_true",
                        help="Ignore any existing checkpoint and start fresh")
    parser.add_argument("--orphan-inbox", type=str, default=None,
                        help=f"Folder of orphan PDFs to stage before crawling SR. "
                        f"Defaults to {DEFAULT_ORPHAN_INBOX} if it exists.")
    parser.add_argument("--no-orphan-scan", action="store_true",
                        help="Skip Phase 0 orphan staging even if inbox exists")
    parser.add_argument("--no-coauthor-scan", action="store_true",
                        help="Skip Phase 0b scan of database/others_libraries/")
    parser.add_argument("--no-verify-dois", action="store_true",
                        help="Skip Phase 3b Crossref DOI verification")
    parser.add_argument("--no-extract", action="store_true",
                        help="Skip Phase 5b parquet propagation + incremental extraction. "
                        "Downloaded papers that are queued but not in the parquet stay "
                        "on papers_data.json until the next run without this flag")
    parser.add_argument("--no-dedupe", action="store_true",
                        help="Skip Phase 5c hardlink sweep of duplicate PDFs")
    args = parser.parse_args()

    log = setup_logging(args.verbose)
    config = load_config()
    lock_fh = acquire_lock()

    checkpoint = {} if args.no_resume else load_checkpoint()
    if checkpoint:
        log.info(f"Resuming from checkpoint (phases completed: "
                 f"3={'yes' if checkpoint.get('phase3_complete') else 'partial'}, "
                 f"4={len(checkpoint.get('phase4_downloaded_ids', []))} downloaded)")

    start_time = datetime.now()
    stats = {
        "sr_total": 0, "known_total": 0, "needs_pdf_total": 0,
        "new_found": 0, "details_fetched": 0,
        "pdfs_downloaded": 0, "pdfs_new": 0, "pdfs_known": 0,
        "pdf_failures": 0, "csv_appended": 0, "json_removed": 0,
        "feedback_count": 0, "crawl_errors": 0,
        "orphans_scanned": 0, "orphans_staged": 0, "orphans_failed": 0,
        "base_parquet_added": 0, "extracted": 0,
        "new_paper_list": [], "errors": [], "runtime": "",
    }
    orphan_new_ids: set[str] = set()

    try:
        log.info("=" * 60)
        log.info("Shark-References Monthly Sync")
        log.info(f"Started: {start_time:%Y-%m-%d %H:%M:%S}")
        log.info(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
        log.info("=" * 60)

        # --- Phase 0: Stage orphan PDFs (opt-in) ---
        # Runs before the crawl so any newly-staged DOIs get included in the
        # "known" set when diffing against SR — preventing duplicate inserts.
        if not args.no_orphan_scan:
            inbox_path = Path(args.orphan_inbox) if args.orphan_inbox \
                else DEFAULT_ORPHAN_INBOX
            if inbox_path.exists():
                log.info("")
                log.info(f"Phase 0: Scanning orphan inbox {inbox_path}")
                orphan_pdfs_found = list(inbox_path.glob("*.pdf"))
                stats["orphans_scanned"] = len(orphan_pdfs_found)
                if args.dry_run:
                    log.info(f"  DRY RUN: would stage {len(orphan_pdfs_found)} orphan PDFs")
                else:
                    o_stats = stage_orphan_inbox(inbox_path, log)
                    stats["orphans_staged"] = o_stats["staged"]
                    stats["orphans_failed"] = o_stats["failed"]
                    orphan_new_ids = set(str(i) for i in o_stats["new_ids"])

        # --- Phase 0b: Scan coauthor drop folders ---
        # Coauthors deliver PDFs into database/others_libraries/<name>/ by
        # clicking links from the remaining-todo list. Nothing swept those
        # folders before, so deliveries sat unfiled indefinitely. Unlike the
        # orphan inbox this never stages new literature_ids: every delivery
        # corresponds to an existing queue entry, so anything that fails to
        # match goes to a review sheet for a human instead.
        if not args.no_coauthor_scan:
            try:
                from scan_coauthor_libraries import (  # noqa: E402
                    discover as _discover_coauthors)
                pending = sum(len(v) for v in _discover_coauthors(None).values())
            except Exception as e:  # noqa: BLE001
                log.warning(f"  Coauthor scan unavailable: {e}")
                pending = 0
            if pending:
                log.info(f"Phase 0b: {pending} PDFs in coauthor folders")
                if args.dry_run:
                    log.info("  DRY RUN: would run scan_coauthor_libraries.py")
                else:
                    rc = subprocess.call(
                        [sys.executable,
                         str(Path(__file__).parent / "scan_coauthor_libraries.py")],
                        cwd=str(PROJECT_ROOT))
                    stats["coauthor_scanned"] = pending
                    if rc != 0:
                        log.warning(f"  Coauthor scan exited {rc}")

        # --- Load our state ---
        log.info("Loading known papers...")
        df_known = pd.read_parquet(PARQUET, columns=["literature_id", "doi"])
        known_ids = set(df_known["literature_id"].map(_normalise_lid)) - {""}
        known_dois = {_normalise_doi(d) for d in df_known["doi"].dropna().astype(str)} - {""}
        stats["known_total"] = len(known_ids)
        log.info(f"  Known papers: {len(known_ids):,} (by ID), {len(known_dois):,} (by DOI)")
        # Titles for the DOI-twin checks come from the BASE parquet: 1,209
        # enriched rows have a null title (measured 2026-09-14).
        try:
            parquet_doi_rows = build_parquet_doi_rows(pd.read_parquet(
                BASE_PARQUET, columns=["literature_id", "doi", "title", "year"]))
        except Exception as e:  # noqa: BLE001
            log.warning(f"  Base parquet titles unavailable ({e}); DOI-only matches "
                        f"will be flagged for review, not treated as held")
            parquet_doi_rows = {}

        needs_pdf_ids = set()
        needs_pdf_dois = set()
        if PAPERS_DATA.exists():
            papers_data = json.loads(PAPERS_DATA.read_text())
            needs_pdf_ids = {_normalise_lid(p.get("literature_id", "")) for p in papers_data}
            needs_pdf_ids.discard("")
            needs_pdf_dois = {_normalise_doi(p.get("doi", "")) for p in papers_data} - {""}
        stats["needs_pdf_total"] = len(needs_pdf_ids)
        log.info(f"  Papers needing PDFs: {len(needs_pdf_ids):,}")

        # --- Phase 1: Crawl ---
        log.info("")
        log.info("Phase 1: Crawling A-Z pages...")
        session = requests.Session()
        session.headers.update(HEADERS)

        sr_papers = crawl_all_letters(session, log)
        stats["sr_total"] = len(sr_papers)

        # --- Phase 2: Diff ---
        log.info("")
        log.info("Phase 2: Diffing against known papers...")
        diff_counts: dict = {}
        new_papers, needs_pdf_papers = diff_papers(
            sr_papers, known_ids, known_dois, needs_pdf_ids, needs_pdf_dois, log,
            counts=diff_counts,
        )
        # new_found is GENUINELY new: absent from the parquet and from
        # papers_data.json. Papers queued by an earlier run but not yet in
        # the parquet are reported separately as known_queue_only.
        stats["new_found"] = len(new_papers)
        stats["known_queue_only"] = diff_counts["known_queue_only"]
        stats["needs_pdf_with_sr_link"] = diff_counts["needs_pdf"]
        stats["new_paper_list"] = new_papers[:50]

        if args.dry_run:
            log.info("")
            log.info("DRY RUN — stopping here. Summary:")
            log.info(f"  SR total:        {stats['sr_total']:,}")
            log.info(f"  New papers:      {stats['new_found']} (genuinely new)")
            log.info(f"  Queued, not in parquet: {stats['known_queue_only']} (not counted as new)")
            log.info(f"  Known need PDF:  {len(needs_pdf_papers)}")
            if new_papers:
                log.info("  New papers found:")
                for p in new_papers[:20]:
                    log.info(f"    [{p['literature_id']}] {p.get('authors', '')[:60]}")
            release_lock(lock_fh)
            return 0

        # --- Phase 3: Enrich new papers ---
        if new_papers:
            log.info("")
            log.info("Phase 3: Fetching details for new papers...")
            enrich_new_papers(session, new_papers, checkpoint, log)
            stats["details_fetched"] = len(new_papers)

        # --- Phase 3b: Verify DOIs before anything downstream trusts them ---
        # Must run before Phase 5 writes the master CSV / papers_data.json,
        # since it blanks rejected DOIs in `new_papers` in place.
        if new_papers and not args.no_verify_dois:
            log.info("")
            log.info("Phase 3b: Verifying new papers' DOIs against Crossref...")
            doi_stats = verify_new_paper_dois(session, new_papers, log)
            stats["doi_checked"] = doi_stats["checked"]
            stats["doi_ok"] = doi_stats["ok"]
            stats["doi_rejected"] = doi_stats["rejected"]
            stats["doi_unverifiable"] = doi_stats["unverifiable"]

        # --- Phase 4: Download PDFs ---
        log.info("")
        log.info("Phase 4: Downloading PDFs...")
        downloaded_ids = set(checkpoint.get("phase4_downloaded_ids", []))
        failed_ids = set(checkpoint.get("phase4_failed_ids", []))
        phase4_last_id = checkpoint.get("phase4_last_id", None)

        if downloaded_ids:
            log.info(f"  Resuming: {len(downloaded_ids)} already downloaded, {len(failed_ids)} already failed")
            stats["pdfs_downloaded"] = len(downloaded_ids)

        # Build combined download list: new papers then known-needing-PDF
        all_downloads = []
        for p in new_papers:
            if p.get("pdf_url"):
                all_downloads.append(("new", p))
        for p in needs_pdf_papers:
            all_downloads.append(("known", p))

        # Skip past checkpoint position
        skip = bool(phase4_last_id)
        skipped = 0
        for source, p in all_downloads:
            lid = str(p["literature_id"])

            # Skip papers already processed in a previous run
            if lid in downloaded_ids or lid in failed_ids:
                skipped += 1
                continue

            # Skip papers before the checkpoint resume point
            if skip:
                if lid == phase4_last_id:
                    skip = False
                skipped += 1
                continue

            result = download_pdf(session, p, log)
            if result == "exists":
                # PDF was already on disk — track so we skip on resume
                downloaded_ids.add(lid)
            elif result == "skip":
                # No URL or blocked domain — track so we skip on resume
                failed_ids.add(lid)
            elif result:
                downloaded_ids.add(lid)
                if source == "new":
                    stats["pdfs_new"] += 1
                else:
                    stats["pdfs_known"] += 1
                stats["pdfs_downloaded"] += 1
            else:
                failed_ids.add(lid)
                stats["pdf_failures"] += 1

            # Checkpoint every 50 new downloads/failures
            if (stats["pdfs_downloaded"] + stats["pdf_failures"]) % 50 == 0:
                checkpoint["phase4_downloaded_ids"] = list(downloaded_ids)
                checkpoint["phase4_failed_ids"] = list(failed_ids)
                checkpoint["phase4_last_id"] = lid
                save_checkpoint(checkpoint)

            # Only sleep when we actually hit the network (not for exists/skip)
            if result not in ("exists", "skip"):
                time.sleep(DETAIL_DELAY)

        if skipped:
            log.info(f"  Skipped {skipped} already-processed papers")
        log.info(f"  Downloaded: {stats['pdfs_downloaded']}, Failed: {stats['pdf_failures']}")

        # Final Phase 4 checkpoint
        checkpoint["phase4_downloaded_ids"] = list(downloaded_ids)
        checkpoint["phase4_failed_ids"] = list(failed_ids)
        checkpoint["phase4_complete"] = True
        save_checkpoint(checkpoint)

        # --- Phase 5: Update state ---
        log.info("")
        log.info("Phase 5: Updating state...")

        if new_papers:
            # Count what was actually written, not what was offered: the
            # headline used to report len(new_papers) here.
            stats["csv_appended"] = append_to_master_csv(new_papers, log,
                                                         errors=stats["errors"])
            # Add new papers that failed download (or had no PDF) to todo list
            stats["json_added"] = add_to_papers_data(new_papers, downloaded_ids, log)

        # Queue-only papers (on papers_data.json, not in the parquet) that
        # downloaded this run stay queued until Phase 5b has given them a
        # base parquet row. Removing them first meant a --no-extract run, or
        # a crash in Phase 5b, dropped them from both stores. Under
        # --no-extract they remain queued; the next extracting run finds the
        # PDF on disk ("exists" counts as downloaded) and propagates them.
        plan = plan_phase5b(new_papers, needs_pdf_papers, downloaded_ids,
                            known_ids, known_dois, parquet_doi_rows)
        deferred = plan["queue_only_to_propagate"]
        deferred_ids = {_normalise_lid(p["literature_id"]) for p in deferred}
        # DOI conflicts stay queued for a person to decide (see plan_phase5b).
        review_ids = {_normalise_lid(p["literature_id"]) for p in plan["doi_conflict_review"]}
        stats["doi_conflict_review"] = len(review_ids)
        stats["doi_conflict_review_ids"] = sorted(review_ids)
        if review_ids:
            log.warning(f"  {len(review_ids)} downloaded paper(s) share a DOI with parquet "
                        f"row(s) that are not clearly the same paper: left queued for "
                        f"review, not propagated: {sorted(review_ids)[:20]}")
        if downloaded_ids:
            remove_now = phase5_removal_ids(plan, downloaded_ids)
            stats["json_removed"] = remove_from_papers_data(
                remove_now, log,
                downloaded_papers=[p for p in list(new_papers) + list(needs_pdf_papers)
                                   if _normalise_lid(p.get("literature_id", "")) in remove_now],
                report=stats)

        feedback_count = generate_feedback_report(sr_papers, known_ids, needs_pdf_ids, log)
        stats["feedback_count"] = feedback_count

        # --- Phase 5b: Propagate to base parquet + incremental extraction ---
        # Skipped under --dry-run or --no-extract. Pulls together all IDs
        # touched in this run (new SR papers, freshly downloaded known
        # papers, and orphan-staged entries from Phase 0) so the enriched
        # parquet stays current with the master CSV.
        if not args.dry_run and not args.no_extract:
            log.info("")
            log.info("Phase 5b: Propagating to base parquet + extracting...")

            # A queue-only paper that downloaded needs a base parquet row or
            # extraction finds nothing for it. Before propagating, give it
            # what it used to get as a "new" paper: Phase 3 details and the
            # Phase 3b Crossref DOI check (respecting --no-verify-dois).
            if deferred:
                log.info(f"  {len(deferred)} downloaded queue-only paper(s): "
                         f"fetching details before propagation")
                enrich_queue_only_papers(session, deferred, log)
                if not args.no_verify_dois:
                    q_doi = verify_new_paper_dois(session, deferred, log)
                    stats["doi_checked"] = stats.get("doi_checked", 0) + q_doi["checked"]
                    stats["doi_ok"] = stats.get("doi_ok", 0) + q_doi["ok"]
                    stats["doi_rejected"] = stats.get("doi_rejected", 0) + q_doi["rejected"]
                    stats["doi_unverifiable"] = (stats.get("doi_unverifiable", 0)
                                                 + q_doi["unverifiable"])
            if plan["held_by_doi"]:
                log.info(f"  {len(plan['held_by_doi'])} downloaded paper(s) already in the "
                         f"parquet under another id (DOI match): not propagated")

            propagate_candidates = plan["new_to_propagate"] + deferred
            if propagate_candidates:
                added = propagate_to_base_parquet(propagate_candidates, log)
                stats["base_parquet_added"] = added

            # Only now, with a base row in place, take the deferred papers
            # off the queue. Their DOI is used as-is after verification (a
            # rejected DOI was blanked, so it cannot remove the wrong row).
            if deferred and BASE_PARQUET.exists():
                stats["json_removed"] = stats.get("json_removed", 0) + remove_from_papers_data(
                    deferred_ids, log, downloaded_papers=deferred, report=stats)

            ids_to_extract = set(orphan_new_ids)
            for p in new_papers:
                lid = str(p.get("literature_id", "")).strip()
                if lid and lid in downloaded_ids:
                    ids_to_extract.add(lid)
            for p in needs_pdf_papers:
                lid = str(p.get("literature_id", "")).strip()
                if lid and lid in downloaded_ids:
                    ids_to_extract.add(lid)

            if ids_to_extract:
                log.info(f"  Extracting {len(ids_to_extract)} papers...")
                extracted = run_incremental_extraction(ids_to_extract, log)
                stats["extracted"] = extracted
            else:
                log.info("  No new IDs to extract this run")

        # --- Phase 5c: Collapse byte-identical PDFs onto shared inodes ---
        # A scanned volume backs many articles, so the library accumulates
        # exact copies from every acquisition route, not just BHL: journal
        # issues, coauthor libraries, and re-downloads all produce them.
        # Sweeping here catches all of them regardless of origin, and it is
        # cheap enough to run every sync (a size-prefiltered scan of 20,000
        # PDFs takes about 20 seconds).  Idempotent: files already sharing an
        # inode are skipped.
        if not args.dry_run and not args.no_dedupe:
            log.info("")
            log.info("Phase 5c: Collapsing duplicate PDFs onto shared inodes...")
            try:
                reclaimed, linked = run_dedupe_sweep(log)
                stats["dedupe_linked"] = linked
                stats["dedupe_reclaimed_mb"] = round(reclaimed / 2 ** 20, 1)
            except Exception as e:
                log.warning(f"  dedupe sweep failed (non-fatal): {e}")

        # --- Phase 6: Notify ---
        elapsed = datetime.now() - start_time
        stats["runtime"] = str(elapsed).split(".")[0]
        short_msg, long_msg = build_summary(stats)

        log.info("")
        log.info("Phase 6: Notifications")
        log.info(short_msg)

        if not args.no_notify:
            ntfy_topic = args.ntfy_topic or config.get("ntfy_topic", "")
            if ntfy_topic:
                notify_ntfy(ntfy_topic, short_msg)
                log.info("  ntfy.sh: sent")
            else:
                log.info("  ntfy.sh: no topic configured")

            if config.get("gmail_address"):
                subject = f"SR Sync — {datetime.now():%Y-%m-%d} — {stats['new_found']} new"
                notify_gmail(config, subject, long_msg)
            else:
                log.info("  Gmail: not configured")

        log.info("")
        log.info("=" * 60)
        log.info(f"Completed in {stats['runtime']}")
        log.info("=" * 60)

        clear_checkpoint()

    except Exception as e:
        log.error(f"FATAL: {e}", exc_info=True)
        stats["errors"].append(str(e))

        # Still try to notify on failure
        if not args.no_notify:
            ntfy_topic = args.ntfy_topic or config.get("ntfy_topic", "")
            if ntfy_topic:
                notify_ntfy(ntfy_topic, f"SR sync FAILED: {e}", priority="high")
            if config.get("gmail_address"):
                notify_gmail(config, f"SR Sync FAILED — {datetime.now():%Y-%m-%d}",
                             f"Fatal error:\n{e}")

        release_lock(lock_fh)
        return 1

    release_lock(lock_fh)
    return 0


if __name__ == "__main__":
    sys.exit(main())
