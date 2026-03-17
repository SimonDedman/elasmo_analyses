#!/usr/bin/env python3
"""
enrich_altmetric.py

Query the Altmetric Details Page API for social/media attention metrics
for all papers with DOIs in the corpus.

Usage:
    python scripts/enrich_altmetric.py          # full run
    python scripts/enrich_altmetric.py --resume  # resume from checkpoint

Output:
    outputs/altmetric_scores.csv  — one row per paper with attention metrics
    outputs/.altmetric_progress.json — checkpoint for resume

Rate limits (SRAD key):
    3,600 requests/hour, 86,400 requests/day
    Script runs at ~1 req/sec with backoff on 429.

Author: Simon Dedman / Claude
Date: 2026-03-17
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

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
REQUEST_DELAY = 1.0  # seconds between requests
MAX_RETRIES = 3
SAVE_EVERY = 500  # save checkpoint and CSV every N papers

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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def log(msg: str) -> None:
    """Print and append to log file."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts} {msg}"
    print(line)
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


def query_altmetric(doi: str) -> dict | None:
    """Query Altmetric API for a single DOI. Returns extracted fields or None."""
    url = f"{BASE_URL}{doi}?key={API_KEY}"

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
                return result

            elif resp.status_code == 404:
                # No Altmetric data for this DOI (common for older/niche papers)
                return None

            elif resp.status_code == 429:
                # Rate limited — back off
                wait = 2 ** (attempt + 2)  # 4, 8, 16 seconds
                log(f"  Rate limited, waiting {wait}s (attempt {attempt + 1})")
                time.sleep(wait)
                continue

            else:
                log(f"  Unexpected status {resp.status_code} for {doi}")
                return None

        except requests.RequestException as e:
            log(f"  Request error for {doi}: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
                continue
            return None

    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    log("=" * 70)
    log("Altmetric Enrichment")
    log("=" * 70)

    # Load papers
    log("Loading parquet...")
    df = pd.read_parquet(PARQUET, columns=["literature_id", "doi"])
    df = df.dropna(subset=["doi"])
    df["doi"] = df["doi"].astype(str).str.strip()
    df = df[df["doi"].str.len() > 3]
    log(f"  Papers with DOI: {len(df):,}")

    # Load progress
    progress = load_progress()
    processed_set = set(progress.get("processed_dois", []))
    not_found_set = set(progress.get("not_found_dois", []))
    log(f"  Already processed: {len(processed_set):,}")
    log(f"  Already not-found: {len(not_found_set):,}")

    # Load existing results if resuming
    results = []
    if OUTPUT_CSV.exists() and len(processed_set) > 0:
        existing = pd.read_csv(OUTPUT_CSV)
        results = existing.to_dict("records")
        log(f"  Loaded {len(results):,} existing results from CSV")

    # Filter to unprocessed
    all_dois = set(processed_set) | set(not_found_set)
    to_process = df[~df["doi"].isin(all_dois)].copy()
    log(f"  Remaining to process: {len(to_process):,}")

    if len(to_process) == 0:
        log("Nothing to process. Done.")
        return

    # Process
    found = 0
    not_found = 0
    errors = 0
    start_time = time.time()

    for i, (_, row) in enumerate(to_process.iterrows()):
        doi = row["doi"]
        lit_id = row["literature_id"]

        result = query_altmetric(doi)

        if result is not None:
            result["literature_id"] = lit_id
            result["doi"] = doi
            results.append(result)
            processed_set.add(doi)
            found += 1
        else:
            not_found_set.add(doi)
            not_found += 1

        # Progress logging
        total_done = found + not_found
        if total_done % 100 == 0:
            elapsed = time.time() - start_time
            rate = total_done / elapsed if elapsed > 0 else 0
            remaining = len(to_process) - total_done
            eta_min = remaining / rate / 60 if rate > 0 else 0
            log(f"  [{total_done:,}/{len(to_process):,}] "
                f"found={found:,} not_found={not_found:,} "
                f"rate={rate:.1f}/s ETA={eta_min:.0f}min")

        # Save checkpoint
        if total_done % SAVE_EVERY == 0:
            progress["processed_dois"] = list(processed_set)
            progress["not_found_dois"] = list(not_found_set)
            save_progress(progress)
            if results:
                pd.DataFrame(results).to_csv(OUTPUT_CSV, index=False)

        # Rate limiting
        time.sleep(REQUEST_DELAY)

    # Final save
    progress["processed_dois"] = list(processed_set)
    progress["not_found_dois"] = list(not_found_set)
    save_progress(progress)

    if results:
        results_df = pd.DataFrame(results)
        results_df.to_csv(OUTPUT_CSV, index=False)
        log(f"\nSaved {len(results_df):,} results to {OUTPUT_CSV}")

    elapsed = time.time() - start_time
    log(f"\n{'=' * 70}")
    log(f"COMPLETE")
    log(f"{'=' * 70}")
    log(f"  Found:     {found:,}")
    log(f"  Not found: {not_found:,}")
    log(f"  Total:     {found + not_found:,}")
    log(f"  Hit rate:  {found / (found + not_found) * 100:.1f}%")
    log(f"  Time:      {elapsed / 3600:.1f} hours")
    log(f"  Output:    {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
