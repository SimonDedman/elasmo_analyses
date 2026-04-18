#!/usr/bin/env python3
"""
NamSor API enrichment for author gender, origin, and diaspora/ethnicity.

Queries all unique authors through three NamSor endpoints:
  1. Gender (1 credit/name) — with country code where available (GenderGeo)
  2. Origin (10 credits/name) — likely country of origin from name
  3. Diaspora (20 credits/name) — ethnicity/diaspora given country of residence

Uses institution_country from OpenAlex as the country code for better accuracy.

Usage:
    python scripts/enrich_namsor.py                    # full run, all endpoints
    python scripts/enrich_namsor.py --endpoint gender  # gender only
    python scripts/enrich_namsor.py --dry-run           # preview counts
    python scripts/enrich_namsor.py --limit 500         # cap total names
    python scripts/enrich_namsor.py --resume             # skip already-enriched rows

Credit budget (2M free):
    Gender:   28,952 × 1  =   28,952
    Origin:   28,952 × 10 =  289,520
    Diaspora: 28,952 × 20 =  579,040
    Total:                    897,512  (45% of 2M)
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
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
UNIQUE_AUTHORS_RAW = PROJECT_BASE / "outputs/openalex_unique_authors.csv"
UNIQUE_AUTHORS_CLEANED = PROJECT_BASE / "outputs/openalex_unique_authors_cleaned.csv"
# Prefer cleaned version if it exists; fall back to raw
UNIQUE_AUTHORS = UNIQUE_AUTHORS_CLEANED if UNIQUE_AUTHORS_CLEANED.exists() else UNIQUE_AUTHORS_RAW
PAPER_AUTHORS = PROJECT_BASE / "outputs/openalex_paper_authors.csv"
OUTPUT_DIR = PROJECT_BASE / "outputs"
LOG_DIR = PROJECT_BASE / "outputs/logs"
CACHE_PATH = OUTPUT_DIR / ".namsor_cache.json"

NAMSOR_API_KEY = "d5cad08feec313d60dead387638f9118"
NAMSOR_BASE_URL = "https://v2.namsor.com/NamSorAPIv2/api2/json"
BATCH_SIZE = 100  # NamSor max per request

# Output files
NAMSOR_GENDER_CSV = OUTPUT_DIR / "namsor_gender.csv"
NAMSOR_ORIGIN_CSV = OUTPUT_DIR / "namsor_origin.csv"
NAMSOR_DIASPORA_CSV = OUTPUT_DIR / "namsor_diaspora.csv"
NAMSOR_COMBINED_CSV = OUTPUT_DIR / "namsor_enrichment.csv"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

HEADERS = {
    "X-API-KEY": NAMSOR_API_KEY,
    "Content-Type": "application/json",
    "Accept": "application/json",
}


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------


def load_cache() -> dict:
    if CACHE_PATH.exists():
        with open(CACHE_PATH) as f:
            return json.load(f)
    return {"gender": {}, "origin": {}, "diaspora": {}}


def save_cache(cache: dict) -> None:
    with open(CACHE_PATH, "w") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------


def _make_request(endpoint: str, payload: dict, retries: int = 3) -> dict | None:
    """POST to NamSor with retry logic."""
    url = f"{NAMSOR_BASE_URL}/{endpoint}"
    for attempt in range(retries):
        try:
            resp = requests.post(url, headers=HEADERS, json=payload, timeout=60)
            if resp.status_code == 429:
                wait = 2 ** (attempt + 1)
                logger.warning("Rate limited, waiting %ds...", wait)
                time.sleep(wait)
                continue
            if resp.status_code == 401:
                logger.error("Authentication failed — check API key")
                return None
            if resp.status_code == 403:
                logger.error("Forbidden — may have exhausted credits")
                return None
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            logger.warning("Request failed (attempt %d/%d): %s", attempt + 1, retries, e)
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    return None


def check_credits() -> int | None:
    """Check remaining NamSor API credits."""
    url = f"{NAMSOR_BASE_URL}/apiUsage"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        # NamSor returns usage info — extract what we can
        remaining = data.get("subscription", {}).get("planQuota", 0) - data.get(
            "subscription", {}).get("planUsage", 0)
        logger.info("NamSor API usage: %s", json.dumps(data.get("subscription", data), indent=2))
        return remaining
    except Exception as e:
        logger.warning("Could not check credits: %s", e)
        return None


# ---------------------------------------------------------------------------
# Batch queries
# ---------------------------------------------------------------------------


def batch_gender(authors: list[dict], cache: dict) -> list[dict]:
    """Query gender endpoint. Uses GenderGeo when country available, Gender otherwise.

    Each author dict has: first_name, last_name, country_code (optional), id
    """
    results = []

    # Split into geo and non-geo batches
    geo_authors = [a for a in authors if a.get("country_code")]
    nogeo_authors = [a for a in authors if not a.get("country_code")]

    # Process geo batch (genderGeoBatch)
    for i in range(0, len(geo_authors), BATCH_SIZE):
        batch = geo_authors[i: i + BATCH_SIZE]
        payload = {
            "personalNames": [
                {
                    "id": a["id"],
                    "firstName": a["first_name"],
                    "lastName": a["last_name"],
                    "countryIso2": a["country_code"],
                }
                for a in batch
            ]
        }
        resp = _make_request("genderGeoBatch", payload)
        if resp and "personalNames" in resp:
            for entry in resp["personalNames"]:
                result = {
                    "id": entry.get("id", ""),
                    "namsor_gender": entry.get("likelyGender", ""),
                    "namsor_gender_score": entry.get("score", 0),
                    "namsor_gender_probability": entry.get("probabilityCalibrated", 0),
                }
                results.append(result)
                cache[entry.get("id", "")] = result
        elif resp is None:
            logger.error("Gender geo batch failed at offset %d", i)
            break
        _log_progress("gender(geo)", i + len(batch), len(geo_authors))
        time.sleep(0.2)

    # Process non-geo batch (genderBatch)
    for i in range(0, len(nogeo_authors), BATCH_SIZE):
        batch = nogeo_authors[i: i + BATCH_SIZE]
        payload = {
            "personalNames": [
                {
                    "id": a["id"],
                    "firstName": a["first_name"],
                    "lastName": a["last_name"],
                }
                for a in batch
            ]
        }
        resp = _make_request("genderBatch", payload)
        if resp and "personalNames" in resp:
            for entry in resp["personalNames"]:
                result = {
                    "id": entry.get("id", ""),
                    "namsor_gender": entry.get("likelyGender", ""),
                    "namsor_gender_score": entry.get("score", 0),
                    "namsor_gender_probability": entry.get("probabilityCalibrated", 0),
                }
                results.append(result)
                cache[entry.get("id", "")] = result
        elif resp is None:
            logger.error("Gender batch failed at offset %d", i)
            break
        _log_progress("gender(no-geo)", i + len(batch), len(nogeo_authors))
        time.sleep(0.2)

    return results


def batch_origin(authors: list[dict], cache: dict) -> list[dict]:
    """Query origin endpoint — likely country of origin from first+last name."""
    results = []
    for i in range(0, len(authors), BATCH_SIZE):
        batch = authors[i: i + BATCH_SIZE]
        payload = {
            "personalNames": [
                {
                    "id": a["id"],
                    "firstName": a["first_name"],
                    "lastName": a["last_name"],
                }
                for a in batch
            ]
        }
        resp = _make_request("originBatch", payload)
        if resp and "personalNames" in resp:
            for entry in resp["personalNames"]:
                result = {
                    "id": entry.get("id", ""),
                    "namsor_origin_country": entry.get("countryOrigin", ""),
                    "namsor_origin_country_alt": entry.get("countryOriginAlt", ""),
                    "namsor_origin_score": entry.get("score", 0),
                    "namsor_origin_region": entry.get("regionOrigin", ""),
                    "namsor_origin_subregion": entry.get("subRegionOrigin", ""),
                    "namsor_origin_probability": entry.get("probabilityCalibrated", 0),
                }
                results.append(result)
                cache[entry.get("id", "")] = result
        elif resp is None:
            logger.error("Origin batch failed at offset %d", i)
            break
        _log_progress("origin", i + len(batch), len(authors))
        time.sleep(0.2)

    return results


def batch_diaspora(authors: list[dict], cache: dict) -> list[dict]:
    """Query diaspora endpoint — ethnicity given country of residence.

    Only works for authors WITH a country code.
    """
    # Filter to authors with country codes only
    geo_authors = [a for a in authors if a.get("country_code")]
    if len(geo_authors) < len(authors):
        logger.info(
            "Diaspora: %d of %d authors have country codes",
            len(geo_authors), len(authors),
        )

    results = []
    for i in range(0, len(geo_authors), BATCH_SIZE):
        batch = geo_authors[i: i + BATCH_SIZE]
        payload = {
            "personalNames": [
                {
                    "id": a["id"],
                    "firstName": a["first_name"],
                    "lastName": a["last_name"],
                    "countryIso2": a["country_code"],
                }
                for a in batch
            ]
        }
        resp = _make_request("diasporaBatch", payload)
        if resp and "personalNames" in resp:
            for entry in resp["personalNames"]:
                result = {
                    "id": entry.get("id", ""),
                    "namsor_ethnicity": entry.get("ethnicity", ""),
                    "namsor_ethnicity_alt": entry.get("ethnicityAlt", ""),
                    "namsor_ethnicity_score": entry.get("score", 0),
                    "namsor_diaspora_lifted": entry.get("lifted", False),
                    "namsor_ethnicity_probability": entry.get(
                        "probabilityCalibrated", 0
                    ),
                }
                results.append(result)
                cache[entry.get("id", "")] = result
        elif resp is None:
            logger.error("Diaspora batch failed at offset %d", i)
            break
        _log_progress("diaspora", i + len(batch), len(geo_authors))
        time.sleep(0.2)

    return results


def _log_progress(endpoint: str, done: int, total: int) -> None:
    pct = done / total * 100 if total else 0
    logger.info("[%s] %d / %d (%.1f%%)", endpoint, done, total, pct)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def prepare_authors(df: pd.DataFrame, resume_cache: dict, endpoint: str) -> list[dict]:
    """Build list of author dicts from the unique authors DataFrame."""
    authors = []
    for _, row in df.iterrows():
        first = str(row.get("first_name", "")).strip()
        last = str(row.get("last_name", "")).strip()
        if not first or not last or first == "nan" or last == "nan":
            continue
        author_id = str(row.get("openalex_author_id", ""))
        if not author_id or author_id == "nan":
            # Fallback ID from name
            author_id = f"{first}_{last}".lower().replace(" ", "_")

        # Skip if already in cache for this endpoint
        if author_id in resume_cache.get(endpoint, {}):
            continue

        country = str(row.get("institution_country", "")).strip()
        if country == "nan" or len(country) != 2:
            country = ""

        authors.append({
            "id": author_id,
            "first_name": first,
            "last_name": last,
            "country_code": country,
        })
    return authors


def save_results(results: list[dict], path: Path, fieldnames: list[str]) -> None:
    """Write results list to CSV."""
    if not results:
        logger.warning("No results to save to %s", path.name)
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)
    logger.info("Saved %d rows to %s", len(results), path.name)


def merge_to_combined(gender_results, origin_results, diaspora_results) -> pd.DataFrame:
    """Merge all endpoint results into a single combined CSV keyed by author ID."""
    dfs = []
    if gender_results:
        dfs.append(pd.DataFrame(gender_results).set_index("id"))
    if origin_results:
        dfs.append(pd.DataFrame(origin_results).set_index("id"))
    if diaspora_results:
        dfs.append(pd.DataFrame(diaspora_results).set_index("id"))

    if not dfs:
        return pd.DataFrame()

    combined = dfs[0]
    for df in dfs[1:]:
        combined = combined.join(df, how="outer")

    combined = combined.reset_index().rename(columns={"index": "id"})
    return combined


def main() -> None:
    parser = argparse.ArgumentParser(description="NamSor author enrichment")
    parser.add_argument(
        "--endpoint",
        choices=["gender", "origin", "diaspora", "all"],
        default="all",
        help="Which endpoint(s) to query (default: all)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview counts only")
    parser.add_argument("--limit", type=int, default=0, help="Cap total names (0=unlimited)")
    parser.add_argument("--resume", action="store_true", help="Skip already-cached authors")
    parser.add_argument("--check-credits", action="store_true", help="Check credit balance and exit")
    args = parser.parse_args()

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    fh = logging.FileHandler(LOG_DIR / f"namsor_{today}.log")
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S"))
    logger.addHandler(fh)

    logger.info("=== NamSor enrichment run: %s ===", today)

    # Check credits
    credits_remaining = check_credits()
    if args.check_credits:
        return

    # Load data
    cache = load_cache() if args.resume else {"gender": {}, "origin": {}, "diaspora": {}}
    ua = pd.read_csv(UNIQUE_AUTHORS, dtype=str)
    logger.info("Loaded %d unique authors", len(ua))

    endpoints = (
        [args.endpoint] if args.endpoint != "all" else ["gender", "origin", "diaspora"]
    )

    gender_results = []
    origin_results = []
    diaspora_results = []

    for ep in endpoints:
        authors = prepare_authors(ua, cache, ep)
        if args.limit:
            authors = authors[: args.limit]

        n_with_country = sum(1 for a in authors if a["country_code"])
        n_without = len(authors) - n_with_country

        # Calculate credits
        credit_cost = {"gender": 1, "origin": 10, "diaspora": 20}[ep]
        total_credits = len(authors) * credit_cost

        logger.info(
            "[%s] %d authors to query (%d with country, %d without). "
            "Estimated credits: %d",
            ep, len(authors), n_with_country, n_without, total_credits,
        )

        if args.dry_run:
            print(
                f"  {ep}: {len(authors)} authors, "
                f"{n_with_country} with country code, "
                f"~{total_credits:,} credits"
            )
            continue

        if not authors:
            logger.info("[%s] All authors already cached, skipping", ep)
            continue

        if ep == "gender":
            gender_results = batch_gender(authors, cache.setdefault("gender", {}))
            save_results(
                gender_results,
                NAMSOR_GENDER_CSV,
                ["id", "namsor_gender", "namsor_gender_score", "namsor_gender_probability"],
            )
        elif ep == "origin":
            origin_results = batch_origin(authors, cache.setdefault("origin", {}))
            save_results(
                origin_results,
                NAMSOR_ORIGIN_CSV,
                [
                    "id", "namsor_origin_country", "namsor_origin_country_alt",
                    "namsor_origin_score", "namsor_origin_region",
                    "namsor_origin_subregion", "namsor_origin_probability",
                ],
            )
        elif ep == "diaspora":
            diaspora_results = batch_diaspora(authors, cache.setdefault("diaspora", {}))
            save_results(
                diaspora_results,
                NAMSOR_DIASPORA_CSV,
                [
                    "id", "namsor_ethnicity", "namsor_ethnicity_alt",
                    "namsor_ethnicity_score", "namsor_diaspora_lifted",
                    "namsor_ethnicity_probability",
                ],
            )

        # Save cache after each endpoint
        save_cache(cache)

    if args.dry_run:
        total_all = sum(
            {"gender": 1, "origin": 10, "diaspora": 20}[ep]
            * len(prepare_authors(ua, cache, ep)[: args.limit or None])
            for ep in endpoints
        )
        print(f"\n  Total estimated credits: {total_all:,}")
        if credits_remaining:
            print(f"  Credits remaining: {credits_remaining:,}")
        return

    # Merge all results into combined CSV
    combined = merge_to_combined(gender_results, origin_results, diaspora_results)
    if not combined.empty:
        combined.to_csv(NAMSOR_COMBINED_CSV, index=False)
        logger.info("Combined enrichment saved: %d rows to %s", len(combined), NAMSOR_COMBINED_CSV.name)

    # Summary
    summary = [
        f"\nNAMSOR ENRICHMENT REPORT [{today}]",
        f"  Authors processed:",
    ]
    if gender_results:
        males = sum(1 for r in gender_results if r.get("namsor_gender") == "male")
        females = sum(1 for r in gender_results if r.get("namsor_gender") == "female")
        summary.append(f"  Gender:   {len(gender_results)} ({males} male, {females} female)")
    if origin_results:
        summary.append(f"  Origin:   {len(origin_results)}")
    if diaspora_results:
        summary.append(f"  Diaspora: {len(diaspora_results)}")

    report = "\n".join(summary)
    logger.info(report)
    print(report)

    # Write report
    report_path = LOG_DIR / "namsor_latest_report.txt"
    with open(report_path, "w") as f:
        f.write(report + "\n")


if __name__ == "__main__":
    main()
