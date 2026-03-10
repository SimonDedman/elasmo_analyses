#!/usr/bin/env python3
"""Download all data from the Sharkipedia API and save locally.

Pulls species, traits/measurements, trends, and taxonomy from the
Sharkipedia JSON:API, saving both raw JSON and flattened CSVs.

Usage:
    python pull_sharkipedia_api.py

Output files (in ../api_pull/):
    species_all.json          — combined raw JSON:API responses
    species_traits_live.csv   — flattened traits/measurements
    species_trends_live.csv   — flattened trends
    species_taxonomy_live.csv — species list with IUCN codes
    raw_pages/                — incremental page saves (resumable)
    raw_species/              — individual species detail saves
"""

from __future__ import annotations

import csv
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE_URL = "https://www.sharkipedia.org/api/v1"
AUTH_TOKEN = os.environ.get("SHARKIPEDIA_TOKEN", "")
if not AUTH_TOKEN:
    sys.exit("Set SHARKIPEDIA_TOKEN environment variable before running.")
PAGE_SIZE = 50
REQUEST_DELAY = 0.5  # seconds between requests
RETRY_DELAY = 5      # seconds before retry on failure
MAX_RETRIES = 2       # retry count per request

HEADERS = {
    "Authorization": f"Token {AUTH_TOKEN}",
    "Accept": "application/vnd.api+json",
}

# Paths
SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR.parent / "api_pull"
RAW_PAGES_DIR = OUTPUT_DIR / "raw_pages"
RAW_SPECIES_DIR = OUTPUT_DIR / "raw_species"

# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def api_get(url: str, params: dict[str, str] | None = None) -> dict[str, Any] | None:
    """Make a GET request with retry logic. Returns parsed JSON or None."""
    for attempt in range(1, MAX_RETRIES + 2):
        try:
            resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 503:
                print(f"  [503 Service Unavailable] attempt {attempt} — retrying in {RETRY_DELAY}s")
            elif resp.status_code == 429:
                wait = RETRY_DELAY * attempt
                print(f"  [429 Rate limited] waiting {wait}s")
                time.sleep(wait)
                continue
            else:
                print(f"  [HTTP {resp.status_code}] {url} — attempt {attempt}")
        except requests.exceptions.RequestException as exc:
            print(f"  [Error] {exc} — attempt {attempt}")

        if attempt <= MAX_RETRIES:
            time.sleep(RETRY_DELAY)

    return None


# ---------------------------------------------------------------------------
# JSON:API helpers
# ---------------------------------------------------------------------------

def build_included_index(included: list[dict]) -> dict[tuple[str, str], dict]:
    """Index the 'included' array by (type, id) for fast lookup."""
    return {(item["type"], str(item["id"])): item for item in included}


def get_related(resource: dict, rel_name: str, index: dict) -> list[dict]:
    """Resolve a relationship by name, returning list of included items."""
    rel = resource.get("relationships", {}).get(rel_name, {}).get("data")
    if rel is None:
        return []
    if isinstance(rel, dict):
        rel = [rel]
    return [index[(r["type"], str(r["id"]))] for r in rel if (r["type"], str(r["id"])) in index]


def attr(resource: dict, key: str, default: Any = "") -> Any:
    """Get an attribute from a JSON:API resource."""
    return resource.get("attributes", {}).get(key, default)


# ---------------------------------------------------------------------------
# Step 1: Paginated species list (without includes — just to get IDs)
# ---------------------------------------------------------------------------

def fetch_all_species_list() -> list[dict]:
    """Fetch all species from paginated list endpoint. Returns list of species resources."""
    all_species: list[dict] = []
    page_num = 1

    while True:
        cache_file = RAW_PAGES_DIR / f"species_page_{page_num:03d}.json"

        # Resume from cache if available
        if cache_file.exists():
            print(f"  Page {page_num}: loading from cache")
            with open(cache_file) as f:
                data = json.load(f)
        else:
            print(f"  Page {page_num}: fetching...")
            data = api_get(f"{BASE_URL}/species", {
                "page[size]": str(PAGE_SIZE),
                "page[number]": str(page_num),
            })
            if data is None:
                print(f"  FAILED to fetch page {page_num} after retries. Stopping pagination.")
                break
            with open(cache_file, "w") as f:
                json.dump(data, f)
            time.sleep(REQUEST_DELAY)

        species_on_page = data.get("data", [])
        all_species.extend(species_on_page)
        print(f"  Page {page_num}: got {len(species_on_page)} species (total: {len(all_species)})")

        # Check for next page
        next_url = data.get("links", {}).get("next")
        if not next_url or len(species_on_page) == 0:
            break
        page_num += 1

    return all_species


# ---------------------------------------------------------------------------
# Step 2: Fetch each species individually with includes
# ---------------------------------------------------------------------------

def fetch_species_detail(species_id: str) -> dict[str, Any] | None:
    """Fetch a single species with all relationship includes."""
    cache_file = RAW_SPECIES_DIR / f"species_{species_id}.json"

    if cache_file.exists():
        with open(cache_file) as f:
            return json.load(f)

    data = api_get(
        f"{BASE_URL}/species/{species_id}",
        {"include": "observations,measurements,trends,trends.trend_observations"},
    )
    if data is not None:
        with open(cache_file, "w") as f:
            json.dump(data, f)
    return data


# ---------------------------------------------------------------------------
# Step 3: Flatten into CSVs
# ---------------------------------------------------------------------------

TRAITS_COLUMNS = [
    "species_name", "trait_class", "trait_name", "standard_name",
    "method_name", "model_name", "value", "value_type", "precision",
    "precision_type", "sample_size", "sex", "location", "reference_doi",
]

TRENDS_COLUMNS = [
    "species_name", "data_type", "sampling_method", "model", "ocean",
    "start_year", "end_year", "n_years", "location",
]

TAXONOMY_COLUMNS = [
    "species_id", "species_name", "scientific_name", "authorship",
    "iucn_code", "superorder", "order", "family", "genus",
]


def flatten_traits(species_data: dict, included_index: dict, species_name: str) -> list[dict]:
    """Extract trait/measurement rows for one species."""
    rows: list[dict] = []

    # Observations contain trait info; measurements contain values
    for obs in get_related(species_data, "observations", included_index):
        row = {
            "species_name": species_name,
            "trait_class": attr(obs, "trait_class"),
            "trait_name": attr(obs, "trait_name"),
            "standard_name": attr(obs, "standard_name"),
            "method_name": attr(obs, "method_name"),
            "model_name": attr(obs, "model_name"),
            "value": attr(obs, "value"),
            "value_type": attr(obs, "value_type"),
            "precision": attr(obs, "precision"),
            "precision_type": attr(obs, "precision_type"),
            "sample_size": attr(obs, "sample_size"),
            "sex": attr(obs, "sex"),
            "location": attr(obs, "location"),
            "reference_doi": attr(obs, "reference_doi"),
        }
        rows.append(row)

    for meas in get_related(species_data, "measurements", included_index):
        row = {
            "species_name": species_name,
            "trait_class": attr(meas, "trait_class"),
            "trait_name": attr(meas, "trait_name"),
            "standard_name": attr(meas, "standard_name"),
            "method_name": attr(meas, "method_name"),
            "model_name": attr(meas, "model_name"),
            "value": attr(meas, "value"),
            "value_type": attr(meas, "value_type"),
            "precision": attr(meas, "precision"),
            "precision_type": attr(meas, "precision_type"),
            "sample_size": attr(meas, "sample_size"),
            "sex": attr(meas, "sex"),
            "location": attr(meas, "location"),
            "reference_doi": attr(meas, "reference_doi"),
        }
        rows.append(row)

    return rows


def flatten_trends(species_data: dict, included_index: dict, species_name: str) -> list[dict]:
    """Extract trend rows for one species."""
    rows: list[dict] = []

    for trend in get_related(species_data, "trends", included_index):
        # Get trend observations for year range
        trend_obs = get_related(trend, "trend_observations", included_index)
        years = [attr(to, "year") for to in trend_obs if attr(to, "year")]
        years_int = [int(y) for y in years if y]

        row = {
            "species_name": species_name,
            "data_type": attr(trend, "data_type"),
            "sampling_method": attr(trend, "sampling_method"),
            "model": attr(trend, "model"),
            "ocean": attr(trend, "ocean"),
            "start_year": min(years_int) if years_int else "",
            "end_year": max(years_int) if years_int else "",
            "n_years": len(years_int) if years_int else "",
            "location": attr(trend, "location"),
        }
        rows.append(row)

    return rows


def flatten_taxonomy(species_data: dict) -> dict:
    """Extract taxonomy row for one species."""
    return {
        "species_id": species_data.get("id", ""),
        "species_name": attr(species_data, "name"),
        "scientific_name": attr(species_data, "scientific_name"),
        "authorship": attr(species_data, "authorship"),
        "iucn_code": attr(species_data, "iucn_code"),
        "superorder": attr(species_data, "superorder"),
        "order": attr(species_data, "order"),
        "family": attr(species_data, "family"),
        "genus": attr(species_data, "genus"),
    }


def write_csv(filepath: Path, columns: list[str], rows: list[dict]) -> None:
    """Write rows to CSV with given columns."""
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"  Wrote {len(rows)} rows to {filepath.name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Run the full download pipeline."""
    # Create output directories
    RAW_PAGES_DIR.mkdir(parents=True, exist_ok=True)
    RAW_SPECIES_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Sharkipedia API Pull")
    print("=" * 60)

    # --- Step 1: Get species list ---
    print("\n[1/4] Fetching species list (paginated)...")
    all_species_list = fetch_all_species_list()
    if not all_species_list:
        print("\nERROR: Could not fetch any species. The API may be down.")
        print("The script caches responses — re-run later to resume.")
        sys.exit(1)

    print(f"\nTotal species in list: {len(all_species_list)}")

    # --- Step 2: Fetch each species with includes ---
    print("\n[2/4] Fetching individual species with relationships...")
    all_detail_data: list[dict] = []  # combined JSON:API responses
    all_traits: list[dict] = []
    all_trends: list[dict] = []
    all_taxonomy: list[dict] = []

    failed_species: list[str] = []

    for i, sp in enumerate(all_species_list, 1):
        sp_id = str(sp["id"])
        sp_name = attr(sp, "name") or f"species_{sp_id}"

        if i % 50 == 0 or i == 1:
            print(f"\n  Progress: {i}/{len(all_species_list)} species")

        detail = fetch_species_detail(sp_id)
        if detail is None:
            print(f"  FAILED: {sp_name} (id={sp_id})")
            failed_species.append(sp_id)
            continue

        # Build included index
        included = detail.get("included", [])
        included_index = build_included_index(included)

        species_resource = detail.get("data", {})
        species_name = attr(species_resource, "name") or sp_name

        # Flatten
        all_traits.extend(flatten_traits(species_resource, included_index, species_name))
        all_trends.extend(flatten_trends(species_resource, included_index, species_name))
        all_taxonomy.append(flatten_taxonomy(species_resource))

        # Collect for combined JSON
        all_detail_data.append(detail)

        time.sleep(REQUEST_DELAY)

    print(f"\n  Completed: {len(all_detail_data)} species fetched, {len(failed_species)} failed")

    if failed_species:
        print(f"  Failed IDs: {failed_species[:20]}{'...' if len(failed_species) > 20 else ''}")

    # --- Step 3: Save combined JSON ---
    print("\n[3/4] Saving combined JSON...")
    combined = {
        "meta": {
            "total_species": len(all_detail_data),
            "downloaded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "failed_species_ids": failed_species,
        },
        "species": all_detail_data,
    }
    combined_path = OUTPUT_DIR / "species_all.json"
    with open(combined_path, "w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2)
    size_mb = combined_path.stat().st_size / (1024 * 1024)
    print(f"  Saved {combined_path.name} ({size_mb:.1f} MB)")

    # --- Step 4: Save CSVs ---
    print("\n[4/4] Saving flattened CSVs...")
    write_csv(OUTPUT_DIR / "species_traits_live.csv", TRAITS_COLUMNS, all_traits)
    write_csv(OUTPUT_DIR / "species_trends_live.csv", TRENDS_COLUMNS, all_trends)
    write_csv(OUTPUT_DIR / "species_taxonomy_live.csv", TAXONOMY_COLUMNS, all_taxonomy)

    print("\n" + "=" * 60)
    print("Done!")
    print(f"  Species:  {len(all_taxonomy)}")
    print(f"  Traits:   {len(all_traits)} rows")
    print(f"  Trends:   {len(all_trends)} rows")
    print(f"  Failed:   {len(failed_species)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
