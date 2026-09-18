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
import copy
import csv
import json
import os
import re
import shutil
import subprocess
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
        "unpaywall_only": False,
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
    # unpaywall_only: a fast pass for rows whose DOI arrived after their
    # cascade run (Unpaywall never asked); the trawl and BHL steps cost ~20 s
    # a paper and are left to a later full --recheck.
    if stage is None and not ctx.get("unpaywall_only"):
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
    if stage is None and not ctx.get("unpaywall_only") and is_bhl_eligible(paper):
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


def _papers_data_mutate(**kwargs):
    """The locked read-modify-write from scripts/lib/papers_data_io.py.

    Imported lazily so tests can repoint the module at a temporary file
    (mirrors the pattern in sync_shark_references.py, which this module's
    QUEUE == mutate()'s PAPERS_DATA, same file).
    """
    scripts_dir = str(Path(__file__).resolve().parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    from lib import papers_data_io
    return papers_data_io.mutate(**kwargs)


# Sentinel stored in a diff dict to mean "delete this key", since a plain
# dict.update() can never remove a key -- see _row_diff / apply_run_updates.
_DELETED = object()

# Fields run_cascade_on_paper() documents itself as writing back (see the
# "Cascade, per paper" list in this file's module docstring): doi, the
# Unpaywall oa_status/oa_url, publisher (needs_library dead end), plus the
# three bookkeeping fields it always sets. A diff touching anything outside
# this set is unexpected -- surfaced as a warning rather than either
# silently written (which could paper over a real bug) or silently dropped
# (which would lose a legitimate change if this list goes stale).
CASCADE_OWNED_FIELDS = {
    "doi", "oa_status", "oa_url", "publisher",
    "last_status", "cascade_stage", "cascade_checked",
}


def _row_diff(before: dict, after: dict) -> dict:
    """Keys ``after`` added or changed relative to ``before``, plus deletions.

    Used to turn "the whole row, mutated in place by run_cascade_on_paper"
    into "only the fields this run actually touched" -- ``before`` must be
    a deep copy taken BEFORE run_cascade_on_paper() runs (a shallow copy or
    the same object would already equal ``after``, since the cascade
    mutates the dict in place). A key present in ``before`` but missing
    from ``after`` (the cascade deleting a field -- it doesn't currently,
    but this is defensive) is represented as {key: _DELETED}.
    """
    diff = {k: v for k, v in after.items() if k not in before or before[k] != v}
    for k in set(before) - set(after):
        diff[k] = _DELETED
    return diff


def apply_run_updates(papers: list, updates: dict) -> tuple:
    """Merge this run's per-paper field DIFFS into a freshly re-read list.

    ``updates`` maps normalised literature_id -> a diff dict from
    _row_diff(): only the fields this run's cascade pass actually changed
    on that row, not the whole paper dict. This is what lets the write-back
    touch ONLY those fields instead of overwriting a fresh row wholesale --
    `paper` in main()'s loop is the SAME dict object read from `queue` at
    the top of the run, hours before it is flushed, so merging the WHOLE
    row (as an earlier version of this function did) would revert any
    field a concurrent writer (backfill_findspot, DOI recovery, the
    coauthor scan) touched in between that the cascade itself never looked
    at -- e.g. a findspot filled in by backfill_findspot at 09:15 reverted
    to "" by a cascade flush at 09:25 whose snapshot was taken at 09:00.

    If this run's diff and a concurrent writer both touched the SAME
    field, this run's value wins (last writer under the lock, per field,
    not per row) -- diffs are applied via a plain per-key update/pop, with
    no attempt to detect or merge a same-field conflict.

    Only literature_ids present in ``papers`` at call time are touched: a
    row another writer removed concurrently (e.g. finalize filing it into
    the corpus) is left alone rather than re-added, since our copy of it
    is no longer authoritative.

    Returns (n_applied, missing_lids).
    """
    by_lid = {_norm_id(p.get("literature_id", "")): p for p in papers}
    applied = 0
    missing = []
    for lid, fields in updates.items():
        row = by_lid.get(lid)
        if row is None:
            missing.append(lid)
            continue
        for k, v in fields.items():
            if v is _DELETED:
                row.pop(k, None)
            else:
                row[k] = v
        applied += 1
    return applied, missing


def flush_run_updates(updates: dict) -> tuple:
    """Lock, re-read, apply this run's diffs, write -- or no-op if empty."""
    if not updates:
        return 0, []
    with _papers_data_mutate() as fresh:
        applied, missing = apply_run_updates(fresh, updates)
    return applied, missing


def record_run_update(pending: dict, before: dict, after: dict, log_unexpected=print) -> None:
    """Diff ``before``/``after`` and fold the result into ``pending`` by id.

    ``before`` must be a deep copy of the paper dict taken before
    run_cascade_on_paper() ran; ``after`` is that same dict post-cascade.
    Merges onto any existing diff already pending for this literature_id
    this run (a paper should only be processed once per run, but this
    keeps a second pass from clobbering the first's diff instead of
    accumulating it). Warns (via ``log_unexpected``, a plain print by
    default) if the diff touches a field outside CASCADE_OWNED_FIELDS,
    since that means either this function's field list is stale or
    run_cascade_on_paper changed something it doesn't document -- either
    way worth a human's attention, but not worth dropping the write over.
    """
    lid = _norm_id(after.get("literature_id", ""))
    diff = _row_diff(before, after)
    if not diff:
        return
    unexpected = sorted(k for k in diff if k not in CASCADE_OWNED_FIELDS)
    if unexpected:
        log_unexpected(f"  WARNING: cascade changed unexpected field(s) on "
                       f"literature_id={lid}: {unexpected} (still written)")
    pending.setdefault(lid, {}).update(diff)


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

# ---------------------------------------------------------------------------
# Finalize: file downloaded PDFs into the corpus, delete verified staging
# copies, and run incremental schema extraction. Mirrors sync_shark_references
# Phase 5b for the cascade path. See
# docs/superpowers/specs/2026-07-07-cascade-finalize-ingest-extract-design.md
# ---------------------------------------------------------------------------

def _norm_id(x) -> str:
    """Normalise a literature_id for comparison (strip a trailing '.0')."""
    s = str(x).strip()
    return s[:-2] if s.endswith(".0") else s


def _staged_pdfs(staging_dirs=None) -> list:
    """Staged download PDFs awaiting ingestion.

    Defaults to both source dirs. ``staging_dirs`` restricts the sweep to the
    directories given (2026-09-17): outputs/bhl_downloads/ holds a 504-PDF
    untracked remnant from July with its own booked review, and a finalize run
    aimed at a fresh batch in outputs/oa_downloads/ must not hoover that up.
    """
    staged: list = []
    for d in (staging_dirs if staging_dirs is not None
              else (BHL_DOWNLOAD_DIR, OA_DOWNLOAD_DIR)):
        if d.exists():
            staged.extend(sorted(d.glob("*.pdf")))
            staged.extend(sorted(d.glob("*.PDF")))
    return staged


# --- lid-named staging: trust the filename, sanity-check the content ------
#
# 2026-09-17: the download push staged every fetch as "<literature_id>.pdf",
# and finalize threw that identifier away and re-matched by title/author. It
# filed 11 correct downloads under a different paper's name and, on the EXISTS
# branch, deleted 8 correct downloads because an unrelated file already sat at
# the destination. The staged filename is the strongest evidence we have about
# what a file is -- we put it there ourselves -- so it now wins, subject to a
# content sanity check that only has to agree, never to choose.

OUTSTANDING_STATUSES = {"needs_library", "needs_pdf", "sr_sync_new"}
IDENTITY_MIN_COVERAGE = 0.5     # corroborating an id we already have
IDENTITY_STRICT_COVERAGE = 0.75  # choosing to DELETE the only other copy
IDENTITY_HEAD_TOKENS = 600      # a title page, not the whole document
IDENTITY_MIN_TOKENS = 40        # below this there is no text layer to judge
_IDENT_STOP = {"the", "of", "and", "a", "an", "in", "on", "for", "from",
               "with", "to", "by", "at", "its", "new", "some", "notes"}


def pdf_text(path: Path, timeout: int = 240) -> str:
    """Plain text of a PDF, or "" when there is no text layer / no pdftotext."""
    try:
        return subprocess.run(["pdftotext", str(path), "-"], capture_output=True,
                              text=True, timeout=timeout).stdout
    except (subprocess.TimeoutExpired, OSError):
        return ""


def _ident_norm(text: str) -> str:
    import unicodedata
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _ident_words(title: str) -> list:
    return [w for w in _ident_norm(title).split()
            if len(w) > 3 and w not in _IDENT_STOP]


def identity_check(text: str, row: dict,
                   min_coverage: float = IDENTITY_MIN_COVERAGE) -> tuple:
    """Does this text look like the paper ``row`` describes?

    Returns (verdict, detail). ``verdict`` is True (agrees), False (good text,
    no agreement) or None (no text layer -- untestable, NOT a disagreement).
    Agreement is either enough of the title's content words in the opening of
    the document, or the first author's surname. Both are corroboration of an
    identifier we already have; neither is asked to pick a record.
    """
    tokens = _ident_norm(text).split()
    if len(tokens) < IDENTITY_MIN_TOKENS:
        return None, "no text layer"
    head = set(tokens[:IDENTITY_HEAD_TOKENS])
    words = _ident_words(row.get("title", "") or "")
    if len(words) >= 3:
        hits = sum(1 for w in words if any(t.startswith(w) for t in head))
        cov = hits / len(words)
        if cov >= min_coverage:
            return True, f"title {hits}/{len(words)} words"
    surname = _ident_norm(_first_surname(row.get("authors", "") or ""))
    if surname and len(surname) > 3 and surname in head:
        return True, f"first author {surname}"
    detail = (f"title {len(words)} words, none matched" if words
              else "title too short to judge")
    return False, detail


def _first_surname(authors: str) -> str:
    first = re.split(r"\s*&\s*", str(authors).strip())[0].strip()
    first = re.sub(r"\(\d{4}\)", "", first).strip()
    if "," in first:
        return first.split(",")[0].strip()
    parts = first.split()
    return parts[-1] if parts else ""


def lid_named_rows(staged: list, all_rows: list, queue: list | None = None) -> dict:
    """{staged path: corpus row} for files named "<literature_id>.pdf" whose id
    is an outstanding queue row. These bypass the title/author matcher."""
    if queue is None:
        try:
            queue = load_queue()
        except (OSError, ValueError):
            queue = []
    outstanding = {_norm_id(p.get("literature_id"))
                   for p in queue
                   if p.get("last_status") in OUTSTANDING_STATUSES}
    by_lid = {}
    for r in all_rows:
        by_lid.setdefault(_norm_id(r.get("literature_id")), r)
    out = {}
    for p in staged:
        lid = _norm_id(Path(p).stem)
        if lid and lid in outstanding and lid in by_lid:
            out[str(p)] = by_lid[lid]
    return out


def _sha256(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def same_paper_as_dest(staged: Path, dest: Path, row: dict | None = None) -> tuple:
    """Is it safe to delete ``staged`` because ``dest`` holds the same paper?

    Two ways to say yes, and no third: the bytes are identical, or the
    destination passes the identity check for the record it is filed as.
    Anything else -- including "could not test" -- is a no, because a staged
    download is the only copy we have and a wrong deletion is unrecoverable.
    (2026-09-17: the old gate tested only that the destination existed and was
    bigger than 1 KB, which deleted 8 correct downloads sitting behind an
    unrelated file.)
    """
    try:
        if staged.stat().st_size == dest.stat().st_size and \
                _sha256(staged) == _sha256(dest):
            return True, "sha256 identical"
    except OSError as e:
        return False, f"unreadable: {e}"
    if not row:
        return False, "differs from destination; no record to identity-check"
    # Deleting is irreversible, so the destination has to clear a higher bar
    # than "same subject": two tiger-shark titles share most of their words.
    verdict, detail = identity_check(pdf_text(dest), row,
                                     min_coverage=IDENTITY_STRICT_COVERAGE)
    if verdict:
        return True, f"destination identity check passed ({detail})"
    if verdict is None:
        return False, "destination has no text layer; cannot verify"
    return False, f"destination is a different paper ({detail})"


def delete_verified_staging(staged: list, copied_ids: set,
                            pdf_names: dict, pdf_base: Path,
                            filed_map: dict | None = None,
                            staging_dirs=None,
                            filed_rows: dict | None = None) -> tuple:
    """Delete staged PDFs that are provably filed in the library.

    A staged file is deleted only if ALL gates pass:
      1. it resolves to a corpus id that was filed this run --
         via filed_map[str(path)] if available (authoritative: the id ingest
         actually filed it under), else the filename stem (fallback).
      2. pdf_base / pdf_names[id] exists on disk
      3. that dest is a valid, non-empty PDF (> 1 KB)
    Everything else is KEPT (unmatched, dedup-flagged, dest missing, etc.).
    A manifest of intended deletions is written BEFORE any unlink. Returns
    (deleted, kept, freed_bytes).

    Preferring filed_map over the stem catches files that matched the corpus by
    title (so their filed id differs from the '<download_id>.pdf' name) -- these
    are provably in the library and safe to remove, but the stem-only gate would
    conservatively keep them.
    """
    staging_dirs = ({d.resolve() for d in staging_dirs} if staging_dirs
                    else {BHL_DOWNLOAD_DIR.resolve(), OA_DOWNLOAD_DIR.resolve()})
    copied_norm = {_norm_id(x) for x in copied_ids}
    names_norm = {_norm_id(k): v for k, v in pdf_names.items()}
    rows_norm = {_norm_id(k): v for k, v in (filed_rows or {}).items()}

    to_delete = []   # (staged_path, dest_rel, staged_size, dest_size)
    kept = 0
    for p in staged:
        # Guard: only ever consider files physically inside a staging dir.
        if p.resolve().parent not in staging_dirs:
            kept += 1
            continue
        # Authoritative id from ingest if available, else the filename stem.
        if filed_map is not None and str(p) in filed_map:
            lid = _norm_id(filed_map[str(p)])
        else:
            lid = _norm_id(p.stem)
        if lid not in copied_norm:
            kept += 1
            continue
        dest_rel = names_norm.get(lid)
        if not dest_rel:
            kept += 1
            continue
        dest = pdf_base / dest_rel
        if not dest.exists() or dest.stat().st_size <= 1024:
            print(f"  KEEP (dest missing/too small): {p.name} -> {dest_rel}")
            kept += 1
            continue
        ok, why = same_paper_as_dest(p, dest, rows_norm.get(lid))
        if not ok:
            print(f"  KEEP (not verified same paper): {p.name} -> {dest_rel}: {why}")
            kept += 1
            continue
        to_delete.append((p, dest_rel, p.stat().st_size, dest.stat().st_size))

    # Pre-delete manifest (audit trail + re-download list) -- written FIRST.
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    manifest = BASE / f"outputs/cascade_finalize_manifest_{ts}.csv"
    with open(manifest, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["staged_path", "dest_rel", "staged_bytes", "dest_bytes", "size_match"])
        for p, dest_rel, ssz, dsz in to_delete:
            w.writerow([str(p), dest_rel, ssz, dsz, ssz == dsz])
    print(f"\nFinalize: {len(to_delete)} verified for deletion, {kept} kept.")
    print(f"Manifest -> {manifest}")

    freed = deleted = 0
    for p, _dest_rel, ssz, _dsz in to_delete:
        # Belt-and-braces containment re-check immediately before unlink.
        if p.resolve().parent not in staging_dirs:
            continue
        try:
            p.unlink()
            deleted += 1
            freed += ssz
        except OSError as e:
            print(f"  ERROR deleting {p.name}: {e}")
    return deleted, kept, freed


def finalize_acquisitions(keep_staging: bool = False, do_extract: bool = True,
                          dry_run: bool = False, skip_books: bool = True,
                          do_enrich: bool = True, staging_dirs=None) -> None:
    """Ingest staged downloads into the corpus, delete verified staging copies,
    then run incremental schema extraction on the newly-filed ids.

    ``skip_books`` (default True): detected books (>200pp scanned volumes) are
    EXCLUDED from ingestion and left untouched in staging. Filing a multi-chapter
    volume whole under one literature_id would bury the other shark chapters it
    contains -- those are handled by the separate book-chapter-mining subproject
    (see docs/superpowers/specs/2026-07-07-book-chapter-mining-design.md). Pass
    skip_books=False (CLI --include-books) only once that pipeline exists.
    """
    import ingest_pdfs as ing            # heavy deps loaded only when finalizing
    if staging_dirs:
        print(f"  staging dirs restricted to: "
              f"{', '.join(str(d) for d in staging_dirs)}")
    staged = _staged_pdfs(staging_dirs)
    if skip_books:
        before = len(staged)
        staged = [p for p in staged if not ing.detect_book(p)]
        print(f"  skip_books: excluded {before - len(staged)} detected books "
              f"(left untouched in staging for book-mining).")
    print(f"\n{'=' * 70}\n  FINALIZE: {len(staged)} staged PDFs "
          f"(skip_books={skip_books})\n{'=' * 70}")
    if not staged:
        print("  Nothing to finalize; skipping.")
        return

    all_rows, doi_lookup, ay_lookup = ing.load_database()

    if dry_run:
        ing.check_source("cascade-finalize", staged, doi_lookup, ay_lookup, all_rows,
                         prefer_lid_rows=lid_named_rows(staged, all_rows))
        print("\n[DRY RUN] No files ingested, deleted, or extracted.")
        return

    # Files we staged ourselves as "<literature_id>.pdf" are filed under THAT
    # record, not under whatever the title matcher prefers (2026-09-17).
    prefer = lid_named_rows(staged, all_rows)
    if prefer:
        print(f"  lid-named staging: {len(prefer)} of {len(staged)} files carry an "
              f"outstanding literature_id and will be filed under it")

    filed_map: dict = {}
    filed_rows: dict = {}
    copied_ids, copied_dois, pdf_names, _log = ing.ingest_source(
        "cascade-finalize", staged, doi_lookup, ay_lookup, all_rows,
        filed_map=filed_map, prefer_lid_rows=prefer, filed_rows=filed_rows)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    n_json = ing.update_papers_data_json(copied_ids, copied_dois, ts, "cascade-finalize")
    print(f"  papers_data.json: {n_json} entries removed (no longer missing)")
    ing.update_tracking_dbs(copied_ids, pdf_names, ts, "cascade-finalize")

    if keep_staging:
        print("  --keep-staging set: staging copies retained.")
    else:
        deleted, kept, freed = delete_verified_staging(
            staged, copied_ids, pdf_names, ing.PDF_BASE, filed_map=filed_map,
            staging_dirs=staging_dirs, filed_rows=filed_rows)
        print(f"  Deleted {deleted} staged copies ({freed / 1e9:.2f} GB freed); "
              f"{kept} kept for review.")

    if do_extract and copied_ids:
        ids_csv = BASE / f"outputs/.cascade_finalize_ids_{ts}.csv"
        with open(ids_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["literature_id"])
            for x in sorted({_norm_id(v) for v in copied_ids}):
                w.writerow([x])
        print(f"\n  Running incremental extraction on {len(copied_ids)} ids...")
        rc = subprocess.run(
            [sys.executable,
             str(Path(__file__).parent / "extract_incremental.py"), str(ids_csv)],
            cwd=str(BASE),
        ).returncode
        print(f"  extract_incremental.py exit code: {rc}")
    elif do_extract:
        print("  No ids ingested; extraction skipped.")

    # Enrich the corpus (OpenAlex/NamSor/Altmetric/Unpaywall) + refresh the
    # derived tables the figures read. The chain is incremental, so newly-filed
    # papers get gender/origin/ethnicity/OA/altmetric coverage instead of the NA
    # they used to carry until a manual enrichment pass. Steady-state cost is
    # tiny (only the new DOIs/authors are queried).
    if do_enrich and copied_ids:
        print(f"\n  Running enrichment chain on the refreshed corpus...")
        rc = subprocess.run(
            [sys.executable, str(Path(__file__).parent / "enrich_new_papers.py")],
            cwd=str(BASE),
        ).returncode
        print(f"  enrich_new_papers.py exit code: {rc}")
    elif do_enrich:
        print("  No ids ingested; enrichment skipped.")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Unified per-paper acquisition cascade for the EEA download queue.",
    )
    ap.add_argument("--limit", type=int, default=None, help="Process at most N papers")
    ap.add_argument("--dry-run", action="store_true",
                     help="No writes, no downloads -- report what WOULD happen")
    ap.add_argument("--recheck", action="store_true",
                     help="Re-process papers already marked cascade_checked")
    ap.add_argument("--only-oa-unknown", action="store_true",
                     help="Restrict the pool to DOI-bearing rows whose oa_status is "
                          "not a real Unpaywall colour (unknown/blank): the rows whose "
                          "DOI was recovered AFTER their cascade pass, so Unpaywall "
                          "was never asked. Implies --recheck for those rows.")
    ap.add_argument("--unpaywall-only", action="store_true",
                     help="Skip the OA trawl and BHL steps; Unpaywall lookup + download only.")
    ap.add_argument("--no-finalize", action="store_true",
                     help="Skip the finalize step (ingest/extract of staged PDFs) at "
                          "the end; leave staging for a deliberate later finalize.")
    ap.add_argument("--enable-scihub", action="store_true",
                     help="Enable the (currently inert) sci-hub/tor hook")
    ap.add_argument("--flush-every", type=int, default=50,
                     help="Flush the queue + log to disk every N papers")
    ap.add_argument("--sleep", type=float, default=0.3,
                     help="Seconds to sleep between papers (politeness)")
    ap.add_argument("--staging-dir", action="append", metavar="DIR",
                     help="Restrict finalize to this staging directory "
                          "(repeatable). Default: outputs/oa_downloads AND "
                          "outputs/bhl_downloads. Use this to finalize one "
                          "batch without sweeping the other dir's backlog.")
    ap.add_argument("--finalize-only", action="store_true",
                     help="Skip the download loop; only ingest staged PDFs, "
                          "delete verified staging copies, and extract.")
    ap.add_argument("--keep-staging", action="store_true",
                     help="During finalize, do NOT delete staged PDFs after ingest.")
    ap.add_argument("--no-extract", action="store_true",
                     help="During finalize, skip incremental schema extraction.")
    ap.add_argument("--no-enrich", action="store_true",
                     help="During finalize, skip the OpenAlex/NamSor/Altmetric/"
                          "Unpaywall enrichment chain.")
    ap.add_argument("--include-books", action="store_true",
                     help="During finalize, INCLUDE detected books (>200pp volumes). "
                          "Default excludes them; only enable once book-chapter mining exists.")
    args = ap.parse_args()
    staging_dirs = ([Path(d).resolve() for d in args.staging_dir]
                    if args.staging_dir else None)

    if args.finalize_only:
        finalize_acquisitions(keep_staging=args.keep_staging,
                              do_extract=not args.no_extract,
                              dry_run=args.dry_run,
                              skip_books=not args.include_books,
                              do_enrich=not args.no_enrich,
                              staging_dirs=staging_dirs)
        return 0

    queue = load_queue(QUEUE)
    pool = select_pool(queue, recheck=args.recheck or args.only_oa_unknown)
    if args.only_oa_unknown:
        _colours = {"gold", "green", "hybrid", "bronze", "closed"}
        pool = [p for p in pool if (p.get("doi") or "").strip()
                and (p.get("oa_status") or "").lower() not in _colours
                and p.get("last_status") in ("needs_library", "needs_pdf", "sr_sync_new")]
    if args.limit:
        pool = pool[: args.limit]

    mode = " [DRY RUN]" if args.dry_run else ""
    print(f"Acquisition cascade: {len(pool)} papers to process "
          f"(of {len(queue)} total in queue){mode}")

    if not args.dry_run and pool:
        backup_path = backup_queue(QUEUE, BACKUP_DIR)
        print(f"Backed up queue -> {backup_path}")

    ctx = make_ctx(dry_run=args.dry_run, enable_scihub=args.enable_scihub,
                   unpaywall_only=args.unpaywall_only)

    log_rows: list = []
    stage_counts: Counter = Counter()
    doi_recovered = 0
    oa_verdict_changed = 0
    # This run's per-paper field DIFFS, keyed by normalised literature_id
    # (see record_run_update / _row_diff above). Flushed through
    # lib.papers_data_io.mutate() (flush_run_updates / apply_run_updates)
    # instead of writing the whole `queue` object back -- `queue` was
    # loaded once at the top of main() and a run over the full pool can
    # take hours, long enough for another writer (the cascade's own
    # finalize step, ingest, DOI recovery, backfill_findspot, the SR sync)
    # to have added, removed, or edited OTHER fields on rows this run also
    # processed. Storing only the diff (not the whole `paper` dict, which
    # is the same hours-old object all the way through) is what stops a
    # flush from reverting a field the cascade itself never touched.
    pending_updates: dict = {}

    for i, paper in enumerate(pool):
        before_paper = copy.deepcopy(paper)
        before_doi = paper.get("doi") or ""
        before_oa = paper.get("oa_status") or ""
        result = run_cascade_on_paper(paper, ctx)

        if not before_doi and result["doi_after"]:
            doi_recovered += 1
        if before_oa != result["oa_status_after"]:
            oa_verdict_changed += 1
        stage_counts[result["cascade_stage"]] += 1
        log_rows.append(result)
        record_run_update(pending_updates, before_paper, paper)

        if not args.dry_run and (i + 1) % args.flush_every == 0:
            applied, missing = flush_run_updates(pending_updates)
            if missing:
                print(f"  WARNING: {len(missing)} processed paper(s) no longer in "
                      f"papers_data.json (removed by another writer); this run's "
                      f"update to them was dropped: {missing[:10]}")
            pending_updates = {}
            append_log_rows(log_rows)
            log_rows = []
            print(f"  flushed at {i + 1}/{len(pool)} ({applied} row(s) written)")

        if args.sleep:
            time.sleep(args.sleep)

    if not args.dry_run:
        applied, missing = flush_run_updates(pending_updates)
        if missing:
            print(f"  WARNING: {len(missing)} processed paper(s) no longer in "
                  f"papers_data.json (removed by another writer); this run's "
                  f"update to them was dropped: {missing[:10]}")
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

    # After downloading, file everything into the corpus and extract.
    if args.no_finalize:
        print("--no-finalize: staged PDFs left in place for a deliberate finalize.")
    else:
        finalize_acquisitions(keep_staging=args.keep_staging,
                              do_extract=not args.no_extract,
                              dry_run=args.dry_run,
                              skip_books=not args.include_books,
                              staging_dirs=staging_dirs)
    return 0


if __name__ == "__main__":
    sys.exit(main())
