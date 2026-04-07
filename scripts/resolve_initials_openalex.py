#!/usr/bin/env python3
"""
Resolve initials-only author names via OpenAlex author profiles.

Many authors in our database have only initials (e.g. "M. J." Smale) because
that's how they appeared on the paper we indexed. OpenAlex author profiles
often contain full names from ORCID linkage or other publications
(e.g. "Malcolm John Smale").

Pipeline:
  1. Find all unknown-gender authors whose first_name is initials-only
  2. Batch-query OpenAlex Authors API for display_name_alternatives
  3. Extract the longest first name from alternatives
  4. Check against our existing genderize cache (free, instant)
  5. Update CSVs for cache hits
  6. Report remaining names for the genderize daily queue

Usage:
    python3 scripts/resolve_initials_openalex.py              # full run
    python3 scripts/resolve_initials_openalex.py --dry-run     # preview only
    python3 scripts/resolve_initials_openalex.py --limit 50    # test with fewer

Author: Simon Dedman
Date: 2026-04-06
"""

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
UNIQUE_AUTHORS = PROJECT_BASE / "outputs/openalex_unique_authors.csv"
PAPER_AUTHORS = PROJECT_BASE / "outputs/openalex_paper_authors.csv"
CACHE_PATH = PROJECT_BASE / "outputs/.genderize_cache.json"
LOG_DIR = PROJECT_BASE / "logs"
OPENALEX_API = "https://api.openalex.org/authors"
BATCH_SIZE = 50  # OpenAlex max per request
MIN_PROBABILITY = 0.6

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

_INITIAL_RE = re.compile(r"^[A-Za-z]\.?$")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def is_initials(name: str) -> bool:
    """Check if a name is initials-only (e.g. 'M. J.', 'K', 'L.E.L.')."""
    if pd.isna(name) or not str(name).strip():
        return False
    parts = str(name).replace(".", " ").split()
    return all(len(p) <= 1 for p in parts)


def extract_best_first_name(alternatives: list[str], last_name: str) -> str | None:
    """
    From a list of name alternatives, extract the longest/fullest first name.

    E.g. from ['M J Smale', 'Malcolm John Smale', 'M.J. Smale']
    with last_name='Smale', return 'Malcolm John'.
    """
    if not alternatives or not last_name:
        return None

    ln_lower = last_name.strip().lower()
    candidates = []

    for alt in alternatives:
        alt = str(alt).strip()
        # Remove last name (case-insensitive) to get first name portion
        # Handle "LASTNAME, FIRSTNAME" format
        if "," in alt:
            parts = alt.split(",", 1)
            if parts[0].strip().lower() == ln_lower:
                first = parts[1].strip()
            else:
                first = alt
        else:
            # Remove last name from end
            words = alt.split()
            # Find last name position (could be multi-word)
            first_words = []
            for w in words:
                if w.strip().lower() == ln_lower:
                    break
                first_words.append(w)
            first = " ".join(first_words).strip()

        if not first:
            continue

        # Skip if the extracted first name is still just initials
        first_parts = first.replace(".", " ").split()
        if all(len(p) <= 1 for p in first_parts):
            continue

        # Score by length of real (non-initial) parts
        real_parts = [p for p in first_parts if len(p.strip(".")) > 1]
        score = sum(len(p) for p in real_parts)
        candidates.append((first, score))

    if not candidates:
        return None

    # Return the one with the highest score (longest real name parts)
    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates[0][0]


def extract_query_name(first_name: str) -> str | None:
    """Extract best single token to query genderize.io with."""
    if not first_name or not isinstance(first_name, str):
        return None
    name = first_name.strip()
    if not name or _INITIAL_RE.match(name):
        return None
    parts = name.replace(" ", ".").split(".")
    if all(len(p.strip()) <= 1 for p in parts if p.strip()):
        return None
    for token in name.replace("-", " ").split():
        token = token.strip(".")
        if len(token) > 1 and not _INITIAL_RE.match(token):
            # Reject 2-letter ALL-CAPS tokens — these are initials (DA, CJ, MJ)
            # but keep mixed/lower case (Li, Xu, Qi, Na) which are real names
            if len(token) == 2 and token.isupper():
                continue
            return token
    return None


def simplify_gender(gender: str | None, probability: float) -> str:
    if gender is None or probability < MIN_PROBABILITY:
        return "unknown"
    return gender


# ---------------------------------------------------------------------------
# OpenAlex batch lookup
# ---------------------------------------------------------------------------
def fetch_author_names(author_ids: list[str]) -> dict[str, dict]:
    """
    Batch-fetch author profiles from OpenAlex.

    Args:
        author_ids: list of OpenAlex author IDs (e.g. 'A5036012360')

    Returns:
        dict mapping author_id -> {display_name, alternatives, orcid}
    """
    results = {}
    session = requests.Session()
    session.headers.update({
        "User-Agent": "mailto:simondedman@gmail.com (EEA Data Panel research)",
    })

    for i in range(0, len(author_ids), BATCH_SIZE):
        batch = author_ids[i:i + BATCH_SIZE]
        id_filter = "|".join(batch)

        try:
            resp = session.get(
                OPENALEX_API,
                params={
                    "filter": f"ids.openalex:{id_filter}",
                    "per_page": BATCH_SIZE,
                    "select": "id,display_name,display_name_alternatives,orcid",
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

            for author in data.get("results", []):
                aid = author["id"].replace("https://openalex.org/", "")
                results[aid] = {
                    "display_name": author.get("display_name", ""),
                    "alternatives": author.get("display_name_alternatives", []),
                    "orcid": author.get("orcid"),
                }

        except Exception as e:
            log.warning(f"Batch {i//BATCH_SIZE + 1} failed: {e}")

        if i + BATCH_SIZE < len(author_ids):
            time.sleep(0.2)  # polite delay

        if (i // BATCH_SIZE + 1) % 10 == 0:
            log.info(f"  Fetched {min(i + BATCH_SIZE, len(author_ids))}/{len(author_ids)} authors")

    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Resolve initials-only author names via OpenAlex profiles"
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview without changes")
    parser.add_argument("--limit", type=int, default=None, help="Limit authors to process")
    args = parser.parse_args()

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(LOG_DIR / f"resolve_initials_{datetime.now():%Y%m%d}.log")
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    log.addHandler(fh)

    log.info("=" * 60)
    log.info("Resolve initials-only authors via OpenAlex")
    log.info(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    log.info("=" * 60)

    # Load data
    ua = pd.read_csv(UNIQUE_AUTHORS, dtype=str)
    init_mask = (ua["gender"] == "unknown") & ua["first_name"].apply(is_initials)
    init_authors = ua[init_mask].copy()

    log.info(f"Total unknown-gender authors: {(ua['gender'] == 'unknown').sum()}")
    log.info(f"Initials-only unknowns: {len(init_authors)}")

    if args.limit:
        init_authors = init_authors.head(args.limit)
        log.info(f"Limited to: {len(init_authors)}")

    if init_authors.empty:
        log.info("No initials-only authors to resolve")
        return

    # Extract clean OpenAlex IDs
    author_ids = []
    id_to_idx = {}  # map OA ID -> dataframe index
    for idx, row in init_authors.iterrows():
        oa_url = row.get("openalex_author_id", "")
        if pd.notna(oa_url) and oa_url:
            aid = str(oa_url).replace("https://openalex.org/", "").strip()
            if aid:
                author_ids.append(aid)
                id_to_idx[aid] = idx

    log.info(f"Querying OpenAlex for {len(author_ids)} author profiles...")

    if args.dry_run:
        log.info("DRY RUN — would query OpenAlex, then check genderize cache")
        log.info(f"Sample IDs: {author_ids[:5]}")
        return

    # Fetch from OpenAlex
    oa_data = fetch_author_names(author_ids)
    log.info(f"Received profiles: {len(oa_data)}")

    # Load genderize cache
    cache = {}
    if CACHE_PATH.exists():
        cache = json.loads(CACHE_PATH.read_text())
    cache_keys = {k.lower() for k in cache}

    # Process results
    resolved_from_cache = 0
    new_for_genderize = []
    name_updates = {}  # idx -> new_first_name
    gender_updates = {}  # idx -> gender

    for aid, profile in oa_data.items():
        idx = id_to_idx.get(aid)
        if idx is None:
            continue

        row = ua.loc[idx]
        last_name = str(row["last_name"]) if pd.notna(row["last_name"]) else ""
        full_first = extract_best_first_name(profile["alternatives"], last_name)

        if not full_first:
            continue

        query_name = extract_query_name(full_first)
        if not query_name:
            continue

        name_updates[idx] = full_first

        # Check genderize cache
        key = query_name.lower()
        if key in cache_keys:
            entry = cache.get(key, cache.get(query_name, {}))
            if isinstance(entry, str):
                gender = entry
            else:
                gender = simplify_gender(entry.get("gender"), entry.get("probability", 0))

            if gender != "unknown":
                gender_updates[idx] = gender
                resolved_from_cache += 1
        else:
            new_for_genderize.append(query_name)

    log.info(f"\n--- Results ---")
    log.info(f"Full names recovered from OpenAlex: {len(name_updates)}")
    log.info(f"Gender resolved from cache:         {resolved_from_cache}")
    log.info(f"New names for genderize queue:       {len(set(new_for_genderize))}")
    log.info(f"No full name found:                  {len(oa_data) - len(name_updates)}")

    # Show examples
    examples = list(name_updates.items())[:15]
    if examples:
        log.info("\nExamples of recovered names:")
        for idx, full_name in examples:
            row = ua.loc[idx]
            gender = gender_updates.get(idx, "(pending genderize)")
            log.info(f"  {row['first_name']} {row['last_name']} -> {full_name} [{gender}]")

    # Apply updates
    if name_updates:
        # Update first_name in unique authors
        for idx, full_name in name_updates.items():
            ua.loc[idx, "first_name"] = full_name
        log.info(f"Updated {len(name_updates)} first_name values in unique authors CSV")

    if gender_updates:
        for idx, gender in gender_updates.items():
            ua.loc[idx, "gender"] = gender
        log.info(f"Updated {len(gender_updates)} gender values in unique authors CSV")

    ua.to_csv(UNIQUE_AUTHORS, index=False)
    log.info(f"Saved {UNIQUE_AUTHORS.name}")

    # Also update paper_authors
    if gender_updates or name_updates:
        pa = pd.read_csv(PAPER_AUTHORS, dtype=str)
        pa_updated = 0

        for idx in set(list(name_updates.keys()) + list(gender_updates.keys())):
            row = ua.loc[idx]
            oa_id = row["openalex_author_id"]
            mask = pa["openalex_author_id"] == oa_id

            if idx in name_updates:
                pa.loc[mask, "first_name"] = name_updates[idx]
            if idx in gender_updates:
                pa.loc[mask, "gender"] = gender_updates[idx]
                pa_updated += mask.sum()

        pa.to_csv(PAPER_AUTHORS, index=False)
        log.info(f"Updated {pa_updated} rows in paper authors CSV")

    # Summary
    remaining_unknown = (ua["gender"] == "unknown").sum()
    total = len(ua)
    log.info(f"\n{'=' * 60}")
    log.info(f"Gender resolution summary:")
    log.info(f"  Male:    {(ua['gender'] == 'male').sum()} ({100*(ua['gender']=='male').mean():.1f}%)")
    log.info(f"  Female:  {(ua['gender'] == 'female').sum()} ({100*(ua['gender']=='female').mean():.1f}%)")
    log.info(f"  Unknown: {remaining_unknown} ({100*remaining_unknown/total:.1f}%)")
    log.info(f"  New names queued for genderize: {len(set(new_for_genderize))}")
    log.info(f"  (These will be picked up by the daily genderize cron)")
    log.info(f"{'=' * 60}")


if __name__ == "__main__":
    sys.exit(main() or 0)
