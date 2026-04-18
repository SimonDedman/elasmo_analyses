#!/usr/bin/env python3
"""
Geocode institutions that are missing lat/lon in openalex_authors_last_institution.csv.

Queries Nominatim for each unique (institution_name, institution_country) pair, then:
  - Updates the authors CSV with resolved coordinates
  - Appends new entries to openalex_institutions.csv
  - Writes a debug CSV showing success/failure per institution

Usage:
    python scripts/geocode_missing_institutions.py [--limit N] [--resume]
"""

import argparse
import json
import time
from pathlib import Path

import pandas as pd
import requests

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE = Path("/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel")
AUTHORS_CSV   = BASE / "outputs/openalex_authors_last_institution.csv"
INSTIT_CSV    = BASE / "outputs/openalex_institutions.csv"
DEBUG_CSV     = BASE / "outputs/geocoded_institutions_debug.csv"
PROGRESS_JSON = BASE / "outputs/geocode_progress.json"

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
HEADERS = {"User-Agent": "elasmo_analyses/1.0 (simondedman@gmail.com)"}

# Nominatim rate-limit: 1 req/sec; back off on 429
MIN_INTERVAL = 1.2   # seconds between requests (slightly above 1/sec to be safe)
_last_request_time: float = 0.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def query_nominatim(query: str, retries: int = 3) -> dict | None:
    """Single Nominatim request with rate-limiting and retry on 429."""
    global _last_request_time

    params = {
        "q": query,
        "format": "json",
        "limit": 1,
        "addressdetails": 1,
    }

    for attempt in range(retries):
        # Enforce minimum interval between requests
        elapsed = time.monotonic() - _last_request_time
        if elapsed < MIN_INTERVAL:
            time.sleep(MIN_INTERVAL - elapsed)

        try:
            _last_request_time = time.monotonic()
            r = requests.get(NOMINATIM_URL, params=params, headers=HEADERS, timeout=15)

            if r.status_code == 429:
                wait = 5 * (2 ** attempt)  # 5, 10, 20 sec
                print(f"    [WARN] 429 rate-limit for '{query}'; waiting {wait}s (attempt {attempt+1}/{retries})")
                time.sleep(wait)
                continue

            r.raise_for_status()
            results = r.json()
            return results[0] if results else None

        except requests.exceptions.HTTPError as exc:
            print(f"    [WARN] HTTP error for '{query}': {exc}")
            return None
        except Exception as exc:
            print(f"    [WARN] Nominatim error for '{query}': {exc}")
            return None

    print(f"    [WARN] Max retries reached for '{query}'")
    return None


def geocode_institution(name: str, country: str | None) -> dict | None:
    """Try with country appended, then without."""
    # Attempt 1: name + country
    if country:
        hit = query_nominatim(f"{name}, {country}")
        if hit:
            return hit

    # Attempt 2: name only
    return query_nominatim(f"{name}")


def extract_fields(hit: dict) -> dict:
    """Pull lat, lon, city, region, country_code from a Nominatim result."""
    addr = hit.get("address", {})
    city = (
        addr.get("city")
        or addr.get("town")
        or addr.get("village")
        or addr.get("municipality")
        or addr.get("county")
        or ""
    )
    region = addr.get("state") or addr.get("region") or ""
    return {
        "lat":          float(hit["lat"]),
        "lon":          float(hit["lon"]),
        "city":         city,
        "region":       region,
        "country_code": addr.get("country_code", "").upper(),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Geocode missing institutions via Nominatim")
    parser.add_argument("--limit", type=int, default=None,
                        help="Process at most N institutions (for testing)")
    parser.add_argument("--resume", action="store_true",
                        help="Skip institutions already recorded in progress JSON")
    args = parser.parse_args()

    # Load data
    print(f"Loading {AUTHORS_CSV.name} …")
    authors_df = pd.read_csv(AUTHORS_CSV)
    print(f"Loading {INSTIT_CSV.name} …")
    instit_df  = pd.read_csv(INSTIT_CSV)

    # Identify rows that need geocoding
    missing_mask = (
        authors_df["last_institution_lat"].isna()
        & authors_df["last_institution_name"].notna()
    )
    missing_df = authors_df[missing_mask].copy()

    pairs = (
        missing_df[["last_institution_name", "last_institution_country"]]
        .drop_duplicates()
        .reset_index(drop=True)
    )
    print(f"Unique (name, country) pairs to geocode: {len(pairs)}")

    # Load progress if resuming
    progress: dict = {}
    if args.resume and PROGRESS_JSON.exists():
        with open(PROGRESS_JSON) as f:
            progress = json.load(f)
        print(f"  Resuming: {len(progress)} already processed")

    # Apply limit
    if args.limit:
        pairs = pairs.head(args.limit)
        print(f"  --limit {args.limit}: processing only first {len(pairs)} pairs")

    # Geocode loop
    results: list[dict] = []
    for idx, row in pairs.iterrows():
        name    = row["last_institution_name"]
        country = row["last_institution_country"]
        key     = f"{name}|||{country}"

        if args.resume and key in progress:
            results.append(progress[key])
            continue

        hit = geocode_institution(str(name), str(country) if pd.notna(country) else None)

        if hit:
            fields = extract_fields(hit)
            entry = {
                "institution_name":    name,
                "institution_country": country,
                "status":              "geocoded",
                **fields,
            }
        else:
            entry = {
                "institution_name":    name,
                "institution_country": country,
                "status":              "failed",
                "lat": None, "lon": None,
                "city": None, "region": None, "country_code": None,
            }

        results.append(entry)
        progress[key] = entry

        # Progress log every 50
        done = idx + 1
        if done % 50 == 0 or done == len(pairs):
            ok = sum(1 for r in results if r["status"] == "geocoded")
            print(f"  [{done}/{len(pairs)}] geocoded so far: {ok} / {done}")

        # Save progress JSON (resume support)
        with open(PROGRESS_JSON, "w") as f:
            json.dump(progress, f, indent=2)

    results_df = pd.DataFrame(results)

    # Summary
    total   = len(results_df)
    success = (results_df["status"] == "geocoded").sum()
    print(f"\nGeocoding complete: {success}/{total} successful "
          f"({100*success/total:.1f}%)")

    # Write debug CSV
    results_df.to_csv(DEBUG_CSV, index=False)
    print(f"Debug CSV written: {DEBUG_CSV}")

    # -----------------------------------------------------------------------
    # Update authors CSV
    # -----------------------------------------------------------------------
    geocoded = results_df[results_df["status"] == "geocoded"].set_index("institution_name")

    updated = 0
    for idx, row in authors_df.iterrows():
        if pd.isna(row["last_institution_lat"]) and pd.notna(row["last_institution_name"]):
            name = row["last_institution_name"]
            if name in geocoded.index:
                g = geocoded.loc[name]
                # Handle duplicate index entries (same name, different country)
                if isinstance(g, pd.DataFrame):
                    country = row["last_institution_country"]
                    match = g[g["institution_country"] == country]
                    if match.empty:
                        match = g.iloc[[0]]
                    g = match.iloc[0]
                authors_df.at[idx, "last_institution_lat"]     = g["lat"]
                authors_df.at[idx, "last_institution_lon"]     = g["lon"]
                authors_df.at[idx, "last_institution_city"]    = g["city"] if g["city"] else row["last_institution_city"]
                authors_df.at[idx, "last_institution_region"]  = g["region"] if g["region"] else row["last_institution_region"]
                updated += 1

    print(f"Updated {updated} author rows with geocoded coordinates")
    authors_df.to_csv(AUTHORS_CSV, index=False)
    print(f"Saved: {AUTHORS_CSV}")

    # -----------------------------------------------------------------------
    # Append new entries to openalex_institutions.csv
    # -----------------------------------------------------------------------
    new_rows = []
    for _, r in results_df[results_df["status"] == "geocoded"].iterrows():
        # Only append if not already in institutions file (match by display_name)
        already = (instit_df["display_name"] == r["institution_name"]).any()
        if not already:
            new_rows.append({
                "institution_id": None,
                "display_name":   r["institution_name"],
                "country_code":   r["country_code"],
                "type":           None,
                "city":           r["city"],
                "region":         r["region"],
                "latitude":       r["lat"],
                "longitude":      r["lon"],
            })

    if new_rows:
        new_df = pd.DataFrame(new_rows)
        instit_df = pd.concat([instit_df, new_df], ignore_index=True)
        instit_df.to_csv(INSTIT_CSV, index=False)
        print(f"Appended {len(new_rows)} new institutions to {INSTIT_CSV.name}")
    else:
        print("No new institutions to append (all already present)")

    # Final coverage report
    authors_final = pd.read_csv(AUTHORS_CSV)
    total_with_name = authors_final["last_institution_name"].notna().sum()
    total_with_coords = (
        authors_final["last_institution_name"].notna()
        & authors_final["last_institution_lat"].notna()
    ).sum()
    pct = 100 * total_with_coords / total_with_name if total_with_name else 0
    print(f"\nFinal coverage: {total_with_coords}/{total_with_name} "
          f"({pct:.1f}%) authors with institution name now have coordinates")


if __name__ == "__main__":
    main()
