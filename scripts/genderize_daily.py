#!/usr/bin/env python3
"""
Daily genderize.io batch resolver for unknown author genders.

Queries up to 100 names/day (free tier limit) from the genderize.io API,
updates the local cache and CSV files, then prints a summary report.

Designed to run as a daily cron job. See SETUP instructions at bottom.

Usage:
    python scripts/genderize_daily.py              # normal run (up to 100 names)
    python scripts/genderize_daily.py --dry-run     # preview what would be queried
    python scripts/genderize_daily.py --limit 10    # query fewer names (testing)
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROJECT_BASE = Path(
    "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
)
CACHE_PATH = PROJECT_BASE / "outputs/.genderize_cache.json"
UNIQUE_AUTHORS = PROJECT_BASE / "outputs/openalex_unique_authors.csv"
PAPER_AUTHORS = PROJECT_BASE / "outputs/openalex_paper_authors.csv"
LOG_DIR = PROJECT_BASE / "outputs/logs"
GENDERIZE_URL = "https://api.genderize.io"
# Free tier: 100 requests/day, 10 names/request = 1,000 names/day
DAILY_LIMIT = 1000
# Minimum probability to accept a genderize.io result
MIN_PROBABILITY = 0.6

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

_INITIAL_RE = re.compile(r"^[A-Za-z]\.?$")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_cache() -> dict[str, dict]:
    """Load the genderize cache. Values are either legacy strings or dicts."""
    if not CACHE_PATH.exists():
        return {}
    with open(CACHE_PATH) as f:
        return json.load(f)


def save_cache(cache: dict[str, dict]) -> None:
    """Write cache back to disk."""
    with open(CACHE_PATH, "w") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


def extract_query_name(first_name: str | None) -> str | None:
    """Extract the best single token to query genderize.io with.

    Returns None for initials-only or empty names.
    """
    if not first_name or not isinstance(first_name, str):
        return None
    name = first_name.strip()
    if not name or _INITIAL_RE.match(name):
        return None
    # Multi-part initials like "J.A.C." or "M. R."
    parts = name.replace(" ", ".").split(".")
    if all(len(p.strip()) <= 1 for p in parts if p.strip()):
        return None
    # Try each token for a real name
    for token in name.replace("-", " ").split():
        token = token.strip(".")
        if len(token) > 1 and not _INITIAL_RE.match(token):
            return token
    return None


def simplify_gender(gender: str | None, probability: float) -> str:
    """Map genderize.io result to male/female/unknown."""
    if gender is None or probability < MIN_PROBABILITY:
        return "unknown"
    return gender  # "male" or "female"


def query_genderize(names: list[str]) -> list[dict]:
    """Query genderize.io for a batch of names (max 10 per request).

    Uses the free tier (no API key): 100 requests/day, 10 names each.
    """
    results = []
    for i in range(0, len(names), 10):
        batch = names[i : i + 10]
        params = [("name[]", n) for n in batch]
        try:
            resp = requests.get(GENDERIZE_URL, params=params, timeout=30)
            if resp.status_code == 429:
                logger.warning("Rate limit reached after %d names", len(results))
                break
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict):
                data = [data]
            results.extend(data)
        except requests.RequestException as e:
            logger.error("API request failed: %s", e)
            break
        # Be polite
        time.sleep(0.5)
    return results


def apply_cache_to_csvs(cache: dict[str, dict]) -> tuple[int, int]:
    """Re-apply gender from cache to unknown authors in both CSVs.

    Returns (unique_updated, paper_updated) counts.
    """
    # Build a fast lookup: lowercased query_name -> gender
    def resolve(first_name):
        qn = extract_query_name(first_name)
        if qn is None:
            return "unknown"
        key = qn.lower()
        if key in cache:
            entry = cache[key]
            if isinstance(entry, str):
                return entry
            return simplify_gender(entry.get("gender"), entry.get("probability", 0))
        return "unknown"

    unique_updated = 0
    if UNIQUE_AUTHORS.exists():
        ua = pd.read_csv(UNIQUE_AUTHORS, dtype=str)
        mask = ua["gender"] == "unknown"
        new_genders = ua.loc[mask, "first_name"].apply(resolve)
        changed = new_genders != "unknown"
        unique_updated = int(changed.sum())
        ua.loc[mask, "gender"] = new_genders
        ua.to_csv(UNIQUE_AUTHORS, index=False)

    paper_updated = 0
    if PAPER_AUTHORS.exists():
        pa = pd.read_csv(PAPER_AUTHORS, dtype=str)
        mask = pa["gender"] == "unknown"
        new_genders = pa.loc[mask, "first_name"].apply(resolve)
        changed = new_genders != "unknown"
        paper_updated = int(changed.sum())
        pa.loc[mask, "gender"] = new_genders
        pa.to_csv(PAPER_AUTHORS, index=False)

    return unique_updated, paper_updated


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Daily genderize.io batch resolver")
    parser.add_argument("--dry-run", action="store_true", help="Preview without querying")
    parser.add_argument("--limit", type=int, default=DAILY_LIMIT, help="Max names to query")
    args = parser.parse_args()

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    log_path = LOG_DIR / f"genderize_{today}.log"
    file_handler = logging.FileHandler(log_path)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")
    )
    logger.addHandler(file_handler)

    logger.info("=== Genderize daily run: %s ===", today)

    # Load current state
    cache = load_cache()
    ua = pd.read_csv(UNIQUE_AUTHORS, dtype=str)
    unknown = ua[ua["gender"] == "unknown"].copy()
    unknown["query_name"] = unknown["first_name"].apply(extract_query_name)
    queryable = unknown[unknown["query_name"].notna()]

    # Find names not yet in cache
    cache_keys = {k.lower() for k in cache}
    distinct_names = queryable["query_name"].str.lower().unique()
    remaining = [n for n in distinct_names if n not in cache_keys]

    logger.info("Unknown authors: %d total, %d queryable, %d distinct uncached names",
                len(unknown), len(queryable), len(remaining))

    if not remaining:
        msg = (
            f"GENDERIZE DAILY [{today}]: No new names to query. "
            f"All {len(distinct_names)} queryable names are cached. "
            f"{len(unknown)} authors remain unknown (initials/unresolvable)."
        )
        logger.warning(msg)
        print(msg)
        return

    # Take up to limit
    batch = remaining[: args.limit]
    logger.info("Querying %d names (of %d remaining)", len(batch), len(remaining))

    if args.dry_run:
        print(f"DRY RUN: would query {len(batch)} names:")
        for n in batch[:20]:
            print(f"  {n}")
        if len(batch) > 20:
            print(f"  ... and {len(batch) - 20} more")
        print(f"\n{len(remaining)} total remaining after this batch: {len(remaining) - len(batch)}")
        return

    # Query the API
    results = query_genderize(batch)

    # Process results
    new_male = 0
    new_female = 0
    new_unknown = 0
    for entry in results:
        name = entry.get("name", "").lower()
        gender_raw = entry.get("gender")
        probability = entry.get("probability", 0)
        count = entry.get("count", 0)
        gender = simplify_gender(gender_raw, probability)

        cache[name] = {
            "gender": gender_raw,
            "probability": probability,
            "count": count,
            "queried": today,
        }

        if gender == "male":
            new_male += 1
        elif gender == "female":
            new_female += 1
        else:
            new_unknown += 1

    save_cache(cache)
    logger.info("Cache updated: %d entries total", len(cache))

    # Apply new knowledge to CSVs
    unique_upd, paper_upd = apply_cache_to_csvs(cache)
    logger.info("Updated %d unique authors, %d paper-author rows", unique_upd, paper_upd)

    # Count remaining after this run
    remaining_after = len(remaining) - len(batch)
    successful = new_male + new_female
    total_queried = len(results)

    # Build report
    lines = [
        f"GENDERIZE DAILY REPORT [{today}]",
        f"  Queried:    {total_queried} names",
        f"  Resolved:   {successful} ({new_male} male, {new_female} female)",
        f"  Unresolved: {new_unknown} (below {MIN_PROBABILITY:.0%} threshold or null)",
        f"  CSV updates: {unique_upd} unique authors, {paper_upd} paper-author rows",
        f"  Remaining:  {remaining_after} uncached names",
        f"  Est. days:  {remaining_after // args.limit + (1 if remaining_after % args.limit else 0) if remaining_after else 0}",
    ]

    if successful == 0 and total_queried > 0:
        lines.append("  WARNING: No names resolved this run — may have hit API limit or all names unresolvable")

    report = "\n".join(lines)
    logger.info("\n%s", report)
    print(report)

    # Write report to a latest-report file for easy checking
    report_path = LOG_DIR / "genderize_latest_report.txt"
    with open(report_path, "w") as f:
        f.write(report + "\n")


if __name__ == "__main__":
    main()
