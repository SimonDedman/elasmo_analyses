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
    python3 scripts/sync_shark_references.py --no-extract    # skip Phase 5b

Author: Simon Dedman
Date: 2026-04-06; updated 2026-04-27 (orphan staging + post-sync extraction)
"""

import argparse
import fcntl
import json
import logging
import re
import smtplib
import sys
import time
import urllib.request
import urllib.parse
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
def diff_papers(sr_papers, known_ids, known_dois, needs_pdf_ids, needs_pdf_dois, log):
    """
    Categorise SR papers into NEW, NEEDS_PDF, or HAVE.

    Matches by literature_id first, then by DOI to catch papers we have
    under synthetic 500k+ IDs from non-SR sources.

    Args:
        sr_papers: list of dicts from crawl
        known_ids: set of literature_id strings in our parquet
        known_dois: set of normalised DOI strings in our parquet
        needs_pdf_ids: set of literature_id strings in papers_data.json
        needs_pdf_dois: set of normalised DOI strings in papers_data.json

    Returns:
        (new_papers, needs_pdf_papers)
    """
    new_papers = []
    needs_pdf = []

    for p in sr_papers:
        lid = str(p["literature_id"])
        doi = _normalise_doi(p.get("doi", ""))

        # Check if we already know this paper (by ID or DOI)
        known_by_id = lid in known_ids
        known_by_doi = doi and doi in known_dois

        if not known_by_id and not known_by_doi:
            new_papers.append(p)
        elif p.get("pdf_url"):
            # We know the paper; check if we still need its PDF
            needs_by_id = lid in needs_pdf_ids
            needs_by_doi = doi and doi in needs_pdf_dois
            if needs_by_id or needs_by_doi:
                needs_pdf.append(p)

    log.info(f"Diff results: {len(new_papers)} new, {len(needs_pdf)} known-needing-PDF-with-SR-link")
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
    """Build the target PDF path following library convention."""
    author = extract_first_author(paper.get("authors", ""))
    year = paper.get("year")
    try:
        year_str = str(int(year))
    except (TypeError, ValueError):
        year_str = "Unknown"

    title = clean_for_filename(paper.get("title", ""), max_len=60)
    has_multi = "&" in str(paper.get("authors", ""))
    if has_multi:
        filename = f"{author}.etal.{year_str}.{title}.pdf"
    else:
        filename = f"{author}.{year_str}.{title}.pdf"

    return PDF_BASE / year_str / filename


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
            log.warning(f"  PDF URL returned HTML (likely paywall): {pdf_url[:80]}")
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
def append_to_master_csv(new_papers, log):
    """Append new papers to the most recent master CSV."""
    MASTER_CSV_DIR.mkdir(parents=True, exist_ok=True)
    csv_files = sorted(MASTER_CSV_DIR.glob("shark_references_complete_*.csv"),
                       key=lambda p: p.stat().st_mtime)
    if not csv_files:
        log.warning("No master CSV found — creating new one")
        master = MASTER_CSV_DIR / f"shark_references_complete_{datetime.now():%Y%m%d}.csv"
        df_new = pd.DataFrame(new_papers)
        df_new.to_csv(master, index=False, encoding="utf-8")
        return

    master = csv_files[-1]
    df_existing = pd.read_csv(master, dtype=str)
    df_new = pd.DataFrame(new_papers)
    df_new["literature_id"] = df_new["literature_id"].astype(str)

    # Deduplicate: use literature_id if the master CSV has it, else fall back to DOI
    if "literature_id" in df_existing.columns:
        existing_ids = set(df_existing["literature_id"].dropna())
        mask = ~df_new["literature_id"].isin(existing_ids)
    elif "doi" in df_existing.columns:
        existing_dois = {_normalise_doi(d) for d in df_existing["doi"].dropna()} - {""}
        mask = ~df_new["doi"].apply(_normalise_doi).isin(existing_dois)
    else:
        mask = pd.Series([True] * len(df_new))
    to_append = df_new[mask]

    if len(to_append) == 0:
        log.info("No new papers to append to master CSV")
        return

    df_combined = pd.concat([df_existing, to_append], ignore_index=True)
    df_combined.to_csv(master, index=False, encoding="utf-8")
    log.info(f"Appended {len(to_append)} papers to {master.name}")


def add_to_papers_data(new_papers, downloaded_ids, log):
    """Add new papers that failed download (or had no PDF) to papers_data.json."""
    if not PAPERS_DATA.exists():
        return

    data = json.loads(PAPERS_DATA.read_text())
    existing_ids = {str(p.get("literature_id", "")) for p in data}

    added = 0
    for p in new_papers:
        lid = str(p.get("literature_id", ""))
        if lid in downloaded_ids or lid in existing_ids:
            continue  # successfully downloaded or already on the list
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

    if added:
        PAPERS_DATA.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        log.info(f"Added {added} new papers to papers_data.json (failed/no-PDF downloads)")


def remove_from_papers_data(downloaded_ids, log):
    """Remove successfully-downloaded papers from papers_data.json."""
    if not downloaded_ids or not PAPERS_DATA.exists():
        return

    data = json.loads(PAPERS_DATA.read_text())
    before = len(data)
    data = [p for p in data if str(p.get("literature_id", "")) not in downloaded_ids]
    after = len(data)

    if before != after:
        PAPERS_DATA.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        log.info(f"Removed {before - after} entries from papers_data.json ({after} remaining)")


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
            build_pdf_index, init_worker, process_paper,
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

        if len(update_df):
            lookup = dict(zip(update_df["literature_id"], update_df.index))
            new_cols = [c for c in update_df.columns if c != "literature_id"]
            for idx, lid in enumerate(df_enr["literature_id"]):
                if lid in lookup:
                    src = update_df.loc[lookup[lid]]
                    for col in new_cols:
                        df_enr.at[idx, col] = src[col]
        if len(append_df):
            df_enr = pd.concat([df_enr, append_df], ignore_index=True)

        binary_cols = [c.name for s in ALL_SCHEMAS for c in s.columns]
        for c in binary_cols:
            if c in df_enr.columns:
                df_enr[c] = df_enr[c].fillna(0).astype(int)
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

    lines = [
        f"Shark-References Monthly Sync — {datetime.now():%Y-%m-%d %H:%M}",
        f"{'=' * 60}",
        f"",
        f"Papers on SR:         {stats['sr_total']:,}",
        f"Known in our DB:      {stats['known_total']:,}",
        f"Still need PDFs:      {stats['needs_pdf_total']:,}",
        f"",
        f"--- Orphan staging (Phase 0) ---",
        f"Orphan PDFs scanned:  {stats.get('orphans_scanned', 0)}",
        f"Orphan rows staged:   {stats.get('orphans_staged', 0)}",
        f"Orphans unresolved:   {stats.get('orphans_failed', 0)}",
        f"",
        f"--- New papers ---",
        f"New papers found:     {stats['new_found']}",
        f"Details fetched:      {stats['details_fetched']}",
        f"",
        f"--- PDF downloads ---",
        f"PDFs downloaded:      {stats['pdfs_downloaded']}",
        f"  From new papers:    {stats['pdfs_new']}",
        f"  From known papers:  {stats['pdfs_known']}",
        f"PDF failures:         {stats['pdf_failures']}",
        f"",
        f"--- State updates ---",
        f"Appended to CSV:      {stats['csv_appended']}",
        f"Removed from JSON:    {stats['json_removed']}",
        f"SR feedback entries:  {stats['feedback_count']}",
        f"",
        f"--- Parquet propagation (Phase 5b) ---",
        f"Base parquet added:   {stats.get('base_parquet_added', 0)}",
        f"Incremental extract:  {stats.get('extracted', 0)} (with PDF text)",
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
    parser.add_argument("--no-extract", action="store_true",
                        help="Skip Phase 5b parquet propagation + incremental extraction")
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

        # --- Load our state ---
        log.info("Loading known papers...")
        df_known = pd.read_parquet(PARQUET, columns=["literature_id", "doi"])
        known_ids = set(df_known["literature_id"].dropna().astype(str))
        known_dois = {_normalise_doi(d) for d in df_known["doi"].dropna().astype(str)} - {""}
        stats["known_total"] = len(known_ids)
        log.info(f"  Known papers: {len(known_ids):,} (by ID), {len(known_dois):,} (by DOI)")

        needs_pdf_ids = set()
        needs_pdf_dois = set()
        if PAPERS_DATA.exists():
            papers_data = json.loads(PAPERS_DATA.read_text())
            needs_pdf_ids = {str(p.get("literature_id", "")) for p in papers_data}
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
        new_papers, needs_pdf_papers = diff_papers(
            sr_papers, known_ids, known_dois, needs_pdf_ids, needs_pdf_dois, log
        )
        stats["new_found"] = len(new_papers)
        stats["new_paper_list"] = new_papers[:50]

        if args.dry_run:
            log.info("")
            log.info("DRY RUN — stopping here. Summary:")
            log.info(f"  SR total:        {stats['sr_total']:,}")
            log.info(f"  New papers:      {stats['new_found']}")
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
            append_to_master_csv(new_papers, log)
            stats["csv_appended"] = len(new_papers)
            # Add new papers that failed download (or had no PDF) to todo list
            add_to_papers_data(new_papers, downloaded_ids, log)

        if downloaded_ids:
            json_before = len(needs_pdf_ids)
            remove_from_papers_data(downloaded_ids, log)
            # Re-read to get actual count
            if PAPERS_DATA.exists():
                json_after = len(json.loads(PAPERS_DATA.read_text()))
            else:
                json_after = 0
            stats["json_removed"] = json_before - (json_after if PAPERS_DATA.exists() else 0)

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

            ids_to_propagate = set(orphan_new_ids)
            for p in new_papers:
                lid = str(p.get("literature_id", "")).strip()
                if lid and lid in downloaded_ids:
                    ids_to_propagate.add(lid)

            if new_papers:
                added = propagate_to_base_parquet(
                    [p for p in new_papers
                     if str(p.get("literature_id", "")) in ids_to_propagate],
                    log,
                )
                stats["base_parquet_added"] = added

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
