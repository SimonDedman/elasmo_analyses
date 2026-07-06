#!/usr/bin/env python3
"""
acquire_cascade.py

Unified, per-paper acquisition cascade. The queue (docs/papers_data.json,
~12,700 entries) went stale because our acquisition channels -- OA
discovery, DOI recovery, BHL/archive.org, Unpaywall -- were run ad-hoc on
different subsets, and most never wrote their verdict back to the queue.
This script orchestrates the existing channels in one pass, in a fixed
order, stopping at the first channel that acquires (or conclusively
classifies) each paper, and WRITES every result back onto the record so
the queue becomes self-documenting.

Reuses the existing channel implementations rather than reimplementing
them:
  - scripts/oa_discovery_trawl.py   (OpenAlex / Semantic Scholar OA lookup
                                      + PDF download/verification helper)
  - scripts/fetch_bhl_archive.py    (archive.org/BHL search + download for
                                      pre-1970 / taxonomy-paleontology papers)
  - scripts/discover_dois.py        (CrossRef / Semantic Scholar DOI
                                      discovery by title + author)
  - scripts/generate_closed_access_html.py (resolve_publisher: DOI-prefix
                                      -> publisher, for the needs_library
                                      dead end)

Cascade, per paper (stop at first step that acquires or classifies):
  1. DOI recovery       -- regex-extract from notes/oa_url, else CrossRef/S2
                            title+author lookup. Written back to `doi`.
  2. Unpaywall OA check -- full record fetched (not just the URL); the real
                            oa_status colour (gold/green/hybrid/bronze/
                            closed) is ALWAYS written back to `oa_status`,
                            and any PDF url to `oa_url`. This write-back is
                            the whole point of the script.
  3. Download if OA     -- if Unpaywall returned a PDF url, download it.
  4. OA trawl fallback  -- OpenAlex, then Semantic Scholar (oa_discovery_trawl).
  5. BHL/archive.org    -- only for pre-1970 papers or taxonomy/paleo journals.
  6. Sci-hub/tor        -- OPTIONAL hook, default OFF (--enable-scihub). The
                            existing tor script yields ~0 hits, so this is
                            wired but inert unless a callable is supplied.
  7. Else               -- last_status='needs_library', with the resolved
                            publisher recorded for the manual-download HTML.

Every processed paper gets `last_status`, `cascade_stage` (which step
concluded it) and `cascade_checked=True`. Resumable: papers with
`cascade_checked` set are skipped on the next run unless --recheck.

Safety: docs/papers_data.json is the master queue. It is backed up to
outputs/.queue_backups/ before any write, and every write is atomic
(temp file + os.replace). Progress is flushed periodically so an
interrupt doesn't lose a long run.

Usage:
  python3 scripts/acquire_cascade.py --dry-run --limit 20   # smoke test
  python3 scripts/acquire_cascade.py --limit 500             # live batch
  python3 scripts/acquire_cascade.py --recheck                # re-run all
  python3 scripts/acquire_cascade.py --enable-scihub           # + sci-hub hook

Downloaded PDFs land in outputs/oa_downloads/ or outputs/bhl_downloads/
for a later `ingest_pdfs.py` pass -- this script does NOT file them into
the corpus itself.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import sys
import time
import urllib.parse
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

BASE = Path(__file__).parent.parent
QUEUE = BASE / "docs/papers_data.json"
OA_DOWNLOAD_DIR = BASE / "outputs/oa_downloads"
BHL_DOWNLOAD_DIR = BASE / "outputs/bhl_downloads"
LOG = BASE / "outputs/cascade_log.csv"
BACKUP_DIR = BASE / "outputs/.queue_backups"

sys.path.insert(0, str(Path(__file__).parent))
import oa_discovery_trawl as oat          # noqa: E402
import fetch_bhl_archive as bhl           # noqa: E402
import discover_dois as dd                # noqa: E402
import generate_closed_access_html as gcah  # noqa: E402

EMAIL = "simondedman@gmail.com"

# 10.<4-9 digit registrant>/<suffix>, stopping before whitespace/quotes/brackets
# or trailing sentence punctuation.
DOI_RE = re.compile(r'10\.\d{4,9}/[^\s"\'<>\]\)]+')

LOG_FIELDS = [
    "literature_id", "doi_before", "doi_after",
    "oa_status_before", "oa_status_after",
    "cascade_stage", "last_status", "download_path", "timestamp",
]


# ---------------------------------------------------------------------------
# Step 1: DOI recovery
# ---------------------------------------------------------------------------

def extract_doi_from_text(text) -> Optional[str]:
    """Regex-extract a bare or doi.org-prefixed DOI from free text."""
    if not text:
        return None
    m = DOI_RE.search(str(text))
    if not m:
        return None
    doi = m.group(0).rstrip(".,;:")
    return doi or None


def recover_doi(paper: dict, ctx: dict) -> Optional[str]:
    """Attempt to recover a missing DOI. Returns the recovered DOI, or None
    if the paper already has one or nothing was found. Does not mutate
    `paper` -- the caller decides whether/how to write it back."""
    if paper.get("doi"):
        return None
    for key in ("notes", "oa_url"):
        found = extract_doi_from_text(paper.get(key))
        if found:
            return found

    title = (paper.get("title") or "").strip()
    if not title:
        return None
    authors = paper.get("authors") or ""
    year = paper.get("year")

    try:
        res = ctx["doi_lookup_crossref"](title, authors, year)
    except Exception:
        res = None
    if res and res.get("doi"):
        return res["doi"]

    try:
        res = ctx["doi_lookup_s2"](title, year)
    except Exception:
        res = None
    if res and res.get("doi"):
        return res["doi"]

    return None


# ---------------------------------------------------------------------------
# Step 2: Unpaywall write-back
# ---------------------------------------------------------------------------

def unpaywall_writeback(paper: dict, record: Optional[dict]) -> bool:
    """Write the real oa_status colour (and pdf url, if any) from a raw
    Unpaywall record onto `paper`. Returns True iff a PDF url was found
    (i.e. there is something to download)."""
    if not record:
        return False
    status = record.get("oa_status")
    if status:
        paper["oa_status"] = status
    loc = record.get("best_oa_location") or {}
    pdf_url = loc.get("url_for_pdf") or loc.get("url")
    if pdf_url:
        paper["oa_url"] = pdf_url
        return True
    return False


def default_unpaywall_fetch(doi, email: str = EMAIL) -> Optional[dict]:
    url = f"https://api.unpaywall.org/v2/{urllib.parse.quote(doi)}?email={email}"
    return oat._get(url)


# ---------------------------------------------------------------------------
# Step 5: BHL/archive.org eligibility
# ---------------------------------------------------------------------------

def is_bhl_eligible(paper: dict) -> bool:
    """Mirrors fetch_bhl_archive.load_target_papers' per-paper filter:
    pre-1970 OR a taxonomy/paleontology journal keyword match."""
    year = paper.get("year")
    pre_1970 = isinstance(year, int) and year < 1970
    journal = (paper.get("journal_clean") or paper.get("journal") or "").lower()
    kw_match = any(kw in journal for kw in bhl.TAXONOMY_PALEO_KEYWORDS)
    return pre_1970 or kw_match


# ---------------------------------------------------------------------------
# Download gating (shared by every step that has a candidate URL)
# ---------------------------------------------------------------------------

def _attempt_download(url, dest, downloader: Callable, dry_run: bool) -> str:
    """Returns one of: 'no_url', 'would_download', 'downloaded', 'failed'.
    In dry-run mode the downloader is never called (no network, no file
    writes) -- only the verdict is reported."""
    if not url:
        return "no_url"
    if dry_run:
        return "would_download"
    try:
        ok = downloader(url, dest)
    except Exception:
        ok = False
    return "downloaded" if ok else "failed"


# ---------------------------------------------------------------------------
# Dependency injection: the channel functions, overridable for tests
# ---------------------------------------------------------------------------

def make_ctx(**overrides) -> dict:
    ctx = {
        "doi_lookup_crossref": dd.search_crossref,
        "doi_lookup_s2": dd.search_semantic_scholar,
        "unpaywall_fetch": default_unpaywall_fetch,
        "oa_openalex": oat.oa_openalex,
        "oa_semantic_scholar": oat.oa_semantic_scholar,
        "download_pdf": oat._download_pdf,
        "bhl_search": bhl.search_archive_org,
        "bhl_download": bhl.download_pdf,
        "resolve_publisher": gcah.resolve_publisher,
        "normalise_doi": oat._ndoi,
        "enable_scihub": False,
        "scihub_fetch": None,
        "oa_dir": OA_DOWNLOAD_DIR,
        "bhl_dir": BHL_DOWNLOAD_DIR,
        "dry_run": False,
    }
    ctx.update(overrides)
    return ctx


# ---------------------------------------------------------------------------
# The cascade itself
# ---------------------------------------------------------------------------

def run_cascade_on_paper(paper: dict, ctx: dict) -> dict:
    """Runs the full acquisition cascade for one paper, mutating it in
    place (doi, oa_status, oa_url, publisher, last_status, cascade_stage,
    cascade_checked), and returns a log-row dict describing the outcome."""
    lid = str(paper.get("literature_id"))
    doi_before = paper.get("doi") or ""
    oa_status_before = paper.get("oa_status") or ""
    dry_run = ctx["dry_run"]

    # --- Step 1: DOI recovery -------------------------------------------------
    if not paper.get("doi"):
        recovered = recover_doi(paper, ctx)
        if recovered:
            paper["doi"] = recovered

    doi = ctx["normalise_doi"](paper.get("doi")) if paper.get("doi") else None

    stage = None
    last_status = None
    download_path = ""

    # --- Step 2 + 3: Unpaywall OA check, download if OA -----------------------
    if doi:
        try:
            record = ctx["unpaywall_fetch"](doi)
        except Exception:
            record = None
        got_pdf = unpaywall_writeback(paper, record)
        if got_pdf:
            dest = ctx["oa_dir"] / f"{lid}.pdf"
            outcome = _attempt_download(paper["oa_url"], dest, ctx["download_pdf"], dry_run)
            if outcome == "downloaded":
                stage, last_status, download_path = "unpaywall", "acquired_oa", str(dest)
            elif outcome == "would_download":
                stage, last_status = "would_unpaywall", "would_acquire_oa"
            # "failed" or "no_url" -> fall through to step 4

    # --- Step 4: OA trawl fallback (OpenAlex, then Semantic Scholar) ---------
    if stage is None:
        title = paper.get("title") or ""
        year = paper.get("year")
        trawl_channels = (
            ("openalex", lambda: ctx["oa_openalex"](doi, title, year)),
            ("s2", lambda: ctx["oa_semantic_scholar"](doi, title)),
        )
        for name, fn in trawl_channels:
            try:
                url = fn()
            except Exception:
                url = None
            if not url:
                continue
            dest = ctx["oa_dir"] / f"{lid}.pdf"
            outcome = _attempt_download(url, dest, ctx["download_pdf"], dry_run)
            if outcome == "downloaded":
                paper["oa_url"] = url
                stage, last_status, download_path = f"oa_trawl_{name}", "acquired_oa", str(dest)
                break
            elif outcome == "would_download":
                paper["oa_url"] = url
                stage, last_status = f"would_oa_trawl_{name}", "would_acquire_oa"
                break

    # --- Step 5: BHL / archive.org (pre-1970 or taxonomy/paleo only) --------
    if stage is None and is_bhl_eligible(paper):
        journal = paper.get("journal_clean") or paper.get("journal") or ""
        year_int = paper.get("year") if isinstance(paper.get("year"), int) else 0
        try:
            match = ctx["bhl_search"](journal, year_int, paper.get("title") or "")
        except Exception:
            match = None
        if match:
            dest = ctx["bhl_dir"] / f"{lid}.pdf"
            if dry_run:
                stage, last_status = "would_bhl", "would_acquire_bhl"
            else:
                try:
                    ok, _reason = ctx["bhl_download"](match["url"], dest)
                except Exception:
                    ok = False
                if ok:
                    stage, last_status, download_path = "bhl", "acquired_bhl", str(dest)

    # --- Step 6: sci-hub/tor hook (optional, default off) --------------------
    if stage is None and ctx.get("enable_scihub") and ctx.get("scihub_fetch") and doi:
        dest = ctx["oa_dir"] / f"{lid}.pdf"
        try:
            got = ctx["scihub_fetch"](doi, dest)
        except Exception:
            got = False
        if got:
            stage, last_status, download_path = "scihub", "acquired_scihub", str(dest)

    # --- Step 7: else needs_library -------------------------------------------
    if stage is None:
        try:
            resolved_pub = ctx["resolve_publisher"](paper)
        except Exception:
            resolved_pub = None
        if resolved_pub and not (paper.get("publisher") or "").strip():
            paper["publisher"] = resolved_pub
        stage, last_status = "needs_library", "needs_library"

    paper["last_status"] = last_status
    paper["cascade_stage"] = stage
    paper["cascade_checked"] = True

    return {
        "literature_id": lid,
        "doi_before": doi_before,
        "doi_after": paper.get("doi") or "",
        "oa_status_before": oa_status_before,
        "oa_status_after": paper.get("oa_status") or "",
        "cascade_stage": stage,
        "last_status": last_status,
        "download_path": download_path,
    }


# ---------------------------------------------------------------------------
# Resume / queue-file safety
# ---------------------------------------------------------------------------

def select_pool(queue: list, recheck: bool = False) -> list:
    if recheck:
        return list(queue)
    return [p for p in queue if not p.get("cascade_checked")]


def load_queue(path: Path = QUEUE) -> list:
    return json.loads(path.read_text(encoding="utf-8"))


def backup_queue(path: Path, backup_dir: Path) -> Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = backup_dir / f"{path.stem}_{ts}{path.suffix}"
    shutil.copy2(path, dest)
    return dest


def atomic_write_json(data, path: Path) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def append_log_rows(rows: list, log_path: Optional[Path] = None) -> None:
    # NB: default resolved inside the body (not `log_path: Path = LOG`) so
    # that reassigning the module-level LOG constant after import (as
    # tests, or any future --log-path override, would do) is honoured.
    # A mutable-default-argument here would silently keep writing to the
    # LOG path captured at import time no matter what the caller intends.
    if log_path is None:
        log_path = LOG
    is_new = not log_path.exists()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=LOG_FIELDS)
        if is_new:
            w.writeheader()
        ts = datetime.now().isoformat(timespec="seconds")
        for r in rows:
            row = {k: r.get(k, "") for k in LOG_FIELDS}
            row["timestamp"] = ts
            w.writerow(row)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Unified per-paper acquisition cascade for the EEA download queue.",
    )
    ap.add_argument("--limit", type=int, default=None, help="Process at most N papers")
    ap.add_argument("--dry-run", action="store_true",
                     help="No writes, no downloads -- report what WOULD happen")
    ap.add_argument("--recheck", action="store_true",
                     help="Re-process papers already marked cascade_checked")
    ap.add_argument("--enable-scihub", action="store_true",
                     help="Enable the (currently inert) sci-hub/tor hook")
    ap.add_argument("--flush-every", type=int, default=50,
                     help="Flush the queue + log to disk every N papers")
    ap.add_argument("--sleep", type=float, default=0.3,
                     help="Seconds to sleep between papers (politeness)")
    args = ap.parse_args()

    queue = load_queue(QUEUE)
    pool = select_pool(queue, recheck=args.recheck)
    if args.limit:
        pool = pool[: args.limit]

    mode = " [DRY RUN]" if args.dry_run else ""
    print(f"Acquisition cascade: {len(pool)} papers to process "
          f"(of {len(queue)} total in queue){mode}")

    if not args.dry_run and pool:
        backup_path = backup_queue(QUEUE, BACKUP_DIR)
        print(f"Backed up queue -> {backup_path}")

    ctx = make_ctx(dry_run=args.dry_run, enable_scihub=args.enable_scihub)

    log_rows: list = []
    stage_counts: Counter = Counter()
    doi_recovered = 0
    oa_verdict_changed = 0

    for i, paper in enumerate(pool):
        before_doi = paper.get("doi") or ""
        before_oa = paper.get("oa_status") or ""
        result = run_cascade_on_paper(paper, ctx)

        if not before_doi and result["doi_after"]:
            doi_recovered += 1
        if before_oa != result["oa_status_after"]:
            oa_verdict_changed += 1
        stage_counts[result["cascade_stage"]] += 1
        log_rows.append(result)

        if not args.dry_run and (i + 1) % args.flush_every == 0:
            atomic_write_json(queue, QUEUE)
            append_log_rows(log_rows)
            log_rows = []
            print(f"  flushed at {i + 1}/{len(pool)}")

        if args.sleep:
            time.sleep(args.sleep)

    if not args.dry_run:
        atomic_write_json(queue, QUEUE)
        if log_rows:
            append_log_rows(log_rows)

    print("\nPer-stage breakdown:")
    for stage, n in stage_counts.most_common():
        print(f"  {stage:28s} {n}")
    print(f"\nDOIs recovered this run:          {doi_recovered}")
    print(f"OA-status verdicts changed:       {oa_verdict_changed}")
    acquired = sum(n for s, n in stage_counts.items() if s.startswith(("unpaywall", "oa_trawl", "bhl", "scihub"))
                   and not s.startswith("would_"))
    would_acquire = sum(n for s, n in stage_counts.items() if s.startswith("would_"))
    needs_library = stage_counts.get("needs_library", 0)
    print(f"Acquired this run:                {acquired}")
    if args.dry_run:
        print(f"Would acquire (dry-run):          {would_acquire}")
    print(f"-> needs_library:                 {needs_library}")
    if not args.dry_run:
        print(f"\nQueue written back to: {QUEUE}")
        print(f"Log appended to:       {LOG}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
