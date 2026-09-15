#!/usr/bin/env python3
"""
enrich_altmetric.py

Query the Altmetric Details Page API for social/media attention metrics
for all papers with DOIs in the corpus.

Usage:
    python scripts/enrich_altmetric.py                 # original run (skips DOIs already done)
    python scripts/enrich_altmetric.py --resume        # same, resume from checkpoint
    python scripts/enrich_altmetric.py --refresh       # fresh pull of EVERY DOI into a dated folder
    python scripts/enrich_altmetric.py --refresh --tag 2026-09-14   # resume a refresh run

Output (original mode):
    outputs/altmetric_scores.csv  — one row per paper with attention metrics
    outputs/.altmetric_progress.json — checkpoint for resume

Output (refresh mode, never touches the files above):
    outputs/altmetric_refresh_<tag>/results.jsonl   — one line per DOI answered (found or not_found)
    outputs/altmetric_refresh_<tag>/errors.jsonl    — failed requests; NOT results, retried on resume
    outputs/altmetric_refresh_<tag>/status.json     — worker's own progress, rate, ETA, pid
    outputs/altmetric_refresh_<tag>/DONE | ABORTED  — completion or stop marker (with reason)
    outputs/altmetric_scores_<tag>.csv              — built from results.jsonl when the run finishes
    Watch it with: python3 scripts/altmetric_refresh_progress.py --tag <tag>

Outcome classes (a block must never look like "no data"):
    found      200            final
    not_found  404            final (Altmetric has no record for the DOI)
    denied     401/403        HARD STOP: key rejected or access lapsed
    error      429 after retries, 5xx, timeouts, other codes   retried on resume;
               the run stops after MAX_CONSECUTIVE_ERRORS in a row

Rate limits (SRAD key):
    3,600 requests/hour, 86,400 requests/day
    Script runs at ~1 req/sec with backoff on 429.

Author: Simon Dedman / Claude
Date: 2026-03-17 (refresh mode and outcome classes added 2026-09-14)
"""

import argparse
import json
import os
import re
import sys
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROJECT = Path(__file__).resolve().parent.parent
PARQUET = PROJECT / "outputs" / "literature_review_enriched.parquet"
OUTPUT_CSV = PROJECT / "outputs" / "altmetric_scores.csv"
PROGRESS_FILE = PROJECT / "outputs" / ".altmetric_progress.json"
LOG_FILE = PROJECT / "logs" / "altmetric_enrichment.log"

# Load API key from .env or environment
ENV_FILE = PROJECT / ".env"
API_KEY = os.environ.get("ALTMETRIC_API_KEY", "")
if not API_KEY and ENV_FILE.exists():
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if line.startswith("ALTMETRIC_API_KEY="):
            API_KEY = line.split("=", 1)[1].strip()
            break

if not API_KEY:
    print("ERROR: ALTMETRIC_API_KEY not found in .env or environment")
    sys.exit(1)

BASE_URL = "https://api.altmetric.com/v1/doi/"
CONTROL_DOI = "10.1038/s41586-020-2519-y"  # MEASURED 2026-09-14: keyed 200, keyless 403
REQUEST_DELAY = 1.0  # seconds between requests
MAX_RETRIES = 3
SAVE_EVERY = 500  # save checkpoint and CSV every N papers
MAX_CONSECUTIVE_ERRORS = 20  # refresh mode: stop rather than burn the queue on a broken service
RATE_WINDOW = 200  # refresh mode: rate and ETA from the last N answered DOIs, never total elapsed

# Fields to extract from API response
EXTRACT_FIELDS = {
    "altmetric_id": ("altmetric_id", int),
    "score": ("alt_score", float),
    "cited_by_tweeters_count": ("alt_tweeters", int),
    "cited_by_posts_count": ("alt_posts", int),
    "cited_by_fbwalls_count": ("alt_fbwalls", int),
    "cited_by_feeds_count": ("alt_blogs", int),
    "cited_by_msm_count": ("alt_news", int),
    "cited_by_policies_count": ("alt_policy", int),
    "cited_by_wikipedia_count": ("alt_wikipedia", int),
    "cited_by_rdts_count": ("alt_reddit", int),
    "cited_by_peer_review_sites_count": ("alt_peer_review", int),
}
CSV_COLUMNS = ["altmetric_id", "alt_score", "alt_tweeters", "alt_posts", "alt_fbwalls", "alt_blogs",
               "alt_news", "alt_policy", "alt_wikipedia", "alt_reddit", "alt_peer_review",
               "alt_pct_journal", "alt_pct_all", "alt_pct_similar_age", "alt_mendeley",
               "literature_id", "doi"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def log(msg: str) -> None:
    """Print and append to log file."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts} {msg}"
    print(line, flush=True)
    LOG_FILE.parent.mkdir(exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def load_progress() -> dict:
    """Load checkpoint: processed DOIs and accumulated results."""
    if PROGRESS_FILE.exists():
        try:
            with open(PROGRESS_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, KeyError):
            pass
    return {"processed_dois": [], "not_found_dois": []}


def save_progress(progress: dict) -> None:
    """Save checkpoint."""
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f)


def extract_context(data: dict) -> dict:
    """Extract score context percentiles from nested response."""
    result = {}
    context = data.get("context", {})

    # Journal percentile
    journal_ctx = context.get("journal", {})
    if isinstance(journal_ctx, dict):
        result["alt_pct_journal"] = journal_ctx.get("pct")

    # All outputs percentile
    all_ctx = context.get("all", {})
    if isinstance(all_ctx, dict):
        result["alt_pct_all"] = all_ctx.get("pct")

    # Similar age (3 months) percentile
    age_ctx = context.get("similar_age_3m", {})
    if isinstance(age_ctx, dict):
        result["alt_pct_similar_age"] = age_ctx.get("pct")

    # Mendeley readers (nested under readers)
    readers = data.get("readers", {})
    if isinstance(readers, dict):
        result["alt_mendeley"] = readers.get("mendeley")

    return result


def query_altmetric(doi: str) -> tuple[str, dict | None, str]:
    """Query Altmetric API for a single DOI.

    Returns (outcome, fields, detail) where outcome is one of
    "found", "not_found", "denied", "error" (see module docstring).
    """
    # Corpus DOIs can carry junk (e.g. "10.1071/MF16184#sthash.0BB8P7fK.dpuf"). An unencoded "#" turns the
    # ?key= into a URL fragment, the request goes out keyless, and Altmetric answers 403, which once
    # aborted a 16k-DOI refresh. Cut at whitespace or "#", and percent-encode the rest.
    clean = re.split(r"[#\s]", doi.strip(), maxsplit=1)[0]
    url = f"{BASE_URL}{quote(clean, safe='/')}?key={API_KEY}"
    detail = ""

    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, timeout=30)

            if resp.status_code == 200:
                data = resp.json()
                result = {}
                for api_field, (col_name, dtype) in EXTRACT_FIELDS.items():
                    val = data.get(api_field)
                    if val is not None:
                        try:
                            result[col_name] = dtype(val)
                        except (ValueError, TypeError):
                            result[col_name] = None
                    else:
                        result[col_name] = None

                # Extract nested fields
                result.update(extract_context(data))
                return "found", result, "200"

            elif resp.status_code == 404:
                # No Altmetric data for this DOI (common for older/niche papers)
                return "not_found", None, "404"

            elif resp.status_code in (401, 403):
                return "denied", None, f"HTTP {resp.status_code}"

            elif resp.status_code == 429:
                # Rate limited — back off
                wait = 2 ** (attempt + 2)  # 4, 8, 16 seconds
                log(f"  Rate limited (429), waiting {wait}s (attempt {attempt + 1})")
                detail = "HTTP 429 after retries"
                time.sleep(wait)
                continue

            elif resp.status_code >= 500:
                detail = f"HTTP {resp.status_code}"
                log(f"  Server error {resp.status_code} for {doi} (attempt {attempt + 1})")
                time.sleep(2 ** (attempt + 1))
                continue

            else:
                return "error", None, f"HTTP {resp.status_code}"

        except requests.RequestException as e:
            detail = f"{type(e).__name__}: {e}"
            log(f"  Request error for {doi}: {detail}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
                continue

    return "error", None, detail or "retries exhausted"


QUEUE_JSON = PROJECT / "docs" / "papers_data.json"


def load_dois(include_queue: bool = False) -> pd.DataFrame:
    """Corpus DOIs; with include_queue, also DOIs of papers still in the acquisition queue."""
    df = pd.read_parquet(PARQUET, columns=["literature_id", "doi"])
    df = df.dropna(subset=["doi"])
    df["doi"] = df["doi"].astype(str).str.strip()
    df = df[df["doi"].str.len() > 3]
    if include_queue and QUEUE_JSON.exists():
        data = json.loads(QUEUE_JSON.read_text())
        recs = data if isinstance(data, list) else data.get("papers", [])
        q = pd.DataFrame([{"literature_id": r.get("literature_id"), "doi": str(r.get("doi") or "").strip()}
                          for r in recs])
        q = q[(q["doi"].str.len() > 3) & (~q["doi"].isin(set(df["doi"])))]
        df = pd.concat([df, q], ignore_index=True)
    return df


# ---------------------------------------------------------------------------
# Original mode
# ---------------------------------------------------------------------------

def main_original():
    log("=" * 70)
    log("Altmetric Enrichment")
    log("=" * 70)

    log("Loading parquet...")
    df = load_dois()
    log(f"  Papers with DOI: {len(df):,}")

    progress = load_progress()
    processed_set = set(progress.get("processed_dois", []))
    not_found_set = set(progress.get("not_found_dois", []))
    log(f"  Already processed: {len(processed_set):,}")
    log(f"  Already not-found: {len(not_found_set):,}")

    results = []
    if OUTPUT_CSV.exists() and len(processed_set) > 0:
        existing = pd.read_csv(OUTPUT_CSV)
        results = existing.to_dict("records")
        log(f"  Loaded {len(results):,} existing results from CSV")

    all_dois = set(processed_set) | set(not_found_set)
    to_process = df[~df["doi"].isin(all_dois)].copy()
    log(f"  Remaining to process: {len(to_process):,}")

    if len(to_process) == 0:
        log("Nothing to process. Done.")
        return

    found = not_found = errors = 0
    start_time = time.time()

    for _, row in to_process.iterrows():
        doi = row["doi"]
        outcome, result, detail = query_altmetric(doi)

        if outcome == "found":
            result["literature_id"] = row["literature_id"]
            result["doi"] = doi
            results.append(result)
            processed_set.add(doi)
            found += 1
        elif outcome == "not_found":
            not_found_set.add(doi)
            not_found += 1
        elif outcome == "denied":
            log(f"ACCESS DENIED ({detail}): stopping. Progress so far is saved; nothing recorded for {doi}.")
            break
        else:
            errors += 1  # not recorded: retried on the next run

        total_done = found + not_found + errors
        if total_done % 100 == 0:
            elapsed = time.time() - start_time
            rate = total_done / elapsed if elapsed > 0 else 0
            remaining = len(to_process) - total_done
            eta_min = remaining / rate / 60 if rate > 0 else 0
            log(f"  [{total_done:,}/{len(to_process):,}] found={found:,} not_found={not_found:,} "
                f"errors={errors:,} rate={rate:.1f}/s ETA={eta_min:.0f}min")

        if total_done % SAVE_EVERY == 0:
            progress["processed_dois"] = list(processed_set)
            progress["not_found_dois"] = list(not_found_set)
            save_progress(progress)
            if results:
                pd.DataFrame(results).to_csv(OUTPUT_CSV, index=False)

        time.sleep(REQUEST_DELAY)

    progress["processed_dois"] = list(processed_set)
    progress["not_found_dois"] = list(not_found_set)
    save_progress(progress)

    if results:
        results_df = pd.DataFrame(results)
        results_df.to_csv(OUTPUT_CSV, index=False)
        log(f"\nSaved {len(results_df):,} results to {OUTPUT_CSV}")

    elapsed = time.time() - start_time
    answered = found + not_found
    log(f"\n{'=' * 70}")
    log("COMPLETE")
    log(f"{'=' * 70}")
    log(f"  Found:     {found:,}")
    log(f"  Not found: {not_found:,}")
    log(f"  Errors:    {errors:,} (not recorded; rerun to retry)")
    if answered:
        log(f"  Hit rate:  {found / answered * 100:.1f}%")
    log(f"  Time:      {elapsed / 3600:.1f} hours")
    log(f"  Output:    {OUTPUT_CSV}")


# ---------------------------------------------------------------------------
# Refresh mode
# ---------------------------------------------------------------------------

def refresh_dir(tag: str) -> Path:
    return PROJECT / "outputs" / f"altmetric_refresh_{tag}"


def read_results(path: Path) -> dict:
    """doi -> record, last write wins. Tolerates a torn final line."""
    out = {}
    if not path.exists():
        return out
    with open(path) as f:
        for line in f:
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            out[rec["doi"]] = rec
    return out


def build_refresh_csv(tag: str, df: pd.DataFrame) -> Path:
    """One row per literature_id whose DOI was found, same columns as the original CSV."""
    records = read_results(refresh_dir(tag) / "results.jsonl")
    rows = []
    for _, r in df.iterrows():
        rec = records.get(r["doi"])
        if rec and rec["outcome"] == "found":
            row = {k: rec.get(k) for k in CSV_COLUMNS}
            row["literature_id"] = r["literature_id"]
            row["doi"] = r["doi"]
            rows.append(row)
    out = PROJECT / "outputs" / f"altmetric_scores_{tag}.csv"
    pd.DataFrame(rows, columns=CSV_COLUMNS).to_csv(out, index=False)
    return out


def main_refresh(tag: str, include_queue: bool = False):
    d = refresh_dir(tag)
    d.mkdir(parents=True, exist_ok=True)
    results_path, errors_path = d / "results.jsonl", d / "errors.jsonl"
    status_path = d / "status.json"
    for marker in ("DONE", "ABORTED"):
        (d / marker).unlink(missing_ok=True)

    log("=" * 70)
    log(f"Altmetric REFRESH run {tag}")
    log("=" * 70)
    df = load_dois(include_queue)
    dois = df["doi"].drop_duplicates().tolist()

    # Order: DOIs that had scores in March first (most valuable if access ends mid-run),
    # then DOIs never queried, then March not-founds.
    prev = load_progress()
    prev_found = set(prev.get("processed_dois", []))
    prev_nf = set(prev.get("not_found_dois", []))
    order = {doi: (0 if doi in prev_found else 2 if doi in prev_nf else 1) for doi in dois}
    dois.sort(key=lambda x: order[x])

    done = read_results(results_path)
    queue = [x for x in dois if x not in done]
    total = len(dois)
    log(f"  Unique DOIs: {total:,}; already answered in this run: {len(done):,}; to query: {len(queue):,}")

    counts = {"found": sum(1 for r in done.values() if r["outcome"] == "found"),
              "not_found": sum(1 for r in done.values() if r["outcome"] == "not_found"),
              "errors": 0}
    recent = deque(maxlen=RATE_WINDOW)
    consecutive_errors = 0
    started = datetime.now().isoformat(timespec="seconds")

    def write_status(state, reason=""):
        answered = counts["found"] + counts["not_found"]
        rate = None
        if len(recent) >= 2 and recent[-1] > recent[0]:
            rate = (len(recent) - 1) / (recent[-1] - recent[0])
        eta = (total - answered) / rate if rate else None
        tmp = status_path.with_suffix(".tmp")
        tmp.write_text(json.dumps({
            "tag": tag, "pid": os.getpid(), "state": state, "reason": reason, "started": started,
            "updated": datetime.now().isoformat(timespec="seconds"), "total": total,
            "answered": answered, "found": counts["found"], "not_found": counts["not_found"],
            "errors_this_session": counts["errors"], "consecutive_errors": consecutive_errors,
            "rate_per_s": rate, "eta_s": eta,
        }))
        tmp.replace(status_path)

    write_status("RUNNING")
    with open(results_path, "a") as res_f, open(errors_path, "a") as err_f:
        for i, doi in enumerate(queue, 1):
            outcome, fields, detail = query_altmetric(doi)
            now = time.time()
            stamp = datetime.now().isoformat(timespec="seconds")

            if outcome in ("found", "not_found"):
                rec = {"doi": doi, "outcome": outcome, "fetched_at": stamp}
                if fields:
                    rec.update(fields)
                res_f.write(json.dumps(rec) + "\n")
                res_f.flush()
                if i % 25 == 0:
                    os.fsync(res_f.fileno())
                counts[outcome] += 1
                consecutive_errors = 0
                recent.append(now)
            elif outcome == "denied" and query_altmetric(CONTROL_DOI)[0] == "found":
                # the key still works (control DOI answered), so this refusal is about this DOI only
                err_f.write(json.dumps({"doi": doi, "outcome": "error", "detail": f"{detail} for this DOI only; "
                                        f"control DOI answered", "at": stamp}) + "\n")
                err_f.flush()
                counts["errors"] += 1
            elif outcome == "denied":
                err_f.write(json.dumps({"doi": doi, "outcome": outcome, "detail": detail, "at": stamp}) + "\n")
                err_f.flush()
                reason = f"ACCESS DENIED ({detail}) at {stamp}, control DOI refused too: key rejected or access lapsed"
                log(reason)
                (d / "ABORTED").write_text(reason + "\n")
                write_status("ABORTED", reason)
                os.fsync(res_f.fileno())
                return
            else:
                err_f.write(json.dumps({"doi": doi, "outcome": outcome, "detail": detail, "at": stamp}) + "\n")
                err_f.flush()
                counts["errors"] += 1
                consecutive_errors += 1
                if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                    reason = f"{consecutive_errors} consecutive errors (last: {detail}) at {stamp}"
                    log("STOPPING: " + reason)
                    (d / "ABORTED").write_text(reason + "\n")
                    write_status("ABORTED", reason)
                    os.fsync(res_f.fileno())
                    return

            if i % 25 == 0:
                write_status("RUNNING")
            if i % 500 == 0:
                log(f"  [{counts['found'] + counts['not_found']:,}/{total:,}] found={counts['found']:,} "
                    f"not_found={counts['not_found']:,} errors={counts['errors']:,}")
            time.sleep(REQUEST_DELAY)
        os.fsync(res_f.fileno())

    # Errors are not answers: a run with outstanding errors is not DONE.
    remaining = [x for x in dois if x not in read_results(results_path)]
    out = build_refresh_csv(tag, df)
    if remaining:
        reason = f"queue exhausted with {len(remaining):,} DOIs unanswered (errors); rerun with --tag {tag}"
        log(reason)
        (d / "ABORTED").write_text(reason + "\n")
        write_status("ABORTED", reason)
    else:
        msg = f"all {total:,} DOIs answered; found={counts['found']:,} not_found={counts['not_found']:,}; CSV {out.name}"
        log("DONE: " + msg)
        (d / "DONE").write_text(msg + "\n")
        write_status("DONE", msg)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--resume", action="store_true", help="original mode (resume is automatic)")
    ap.add_argument("--refresh", action="store_true", help="fresh pull of every DOI into a dated folder")
    ap.add_argument("--tag", default=datetime.now().strftime("%Y-%m-%d"), help="refresh run name (reuse to resume)")
    ap.add_argument("--build-csv", action="store_true", help="refresh mode: only rebuild the CSV from results.jsonl")
    ap.add_argument("--include-queue", action="store_true",
                    help="refresh mode: also query DOIs of papers still in the acquisition queue (docs/papers_data.json)")
    args = ap.parse_args()
    if args.refresh and args.build_csv:
        print(build_refresh_csv(args.tag, load_dois(args.include_queue)))
    elif args.refresh:
        main_refresh(args.tag, args.include_queue)
    else:
        main_original()
