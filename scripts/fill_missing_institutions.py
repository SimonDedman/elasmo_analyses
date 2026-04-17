#!/usr/bin/env python3
"""
Fill gaps in openalex_authors_last_institution.csv using:
1. institution_name from paper_authors.csv (most recent paper, any position) — 3,051 authors
2. For institutions we don't yet have coords for, look up via OpenAlex institutions API

Usage:
    python scripts/fill_missing_institutions.py
"""

import csv
import json
import time
from collections import defaultdict
from pathlib import Path

import pandas as pd
import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
AUTHORS_CSV = PROJECT_ROOT / "outputs" / "openalex_unique_authors.csv"
PAPER_AUTHORS_CSV = PROJECT_ROOT / "outputs" / "openalex_paper_authors.csv"
LAST_INST_CSV = PROJECT_ROOT / "outputs" / "openalex_authors_last_institution.csv"
INSTITUTIONS_CSV = PROJECT_ROOT / "outputs" / "openalex_institutions.csv"
# We'll read the parquet for year per paper
PARQUET = PROJECT_ROOT / "outputs" / "literature_review_enriched.parquet"

OPENALEX_BASE = "https://api.openalex.org"
MAILTO = "simondedman@gmail.com"


def strip_prefix(s: str) -> str:
    if isinstance(s, str) and s.startswith("https://openalex.org/"):
        return s[len("https://openalex.org/"):]
    return str(s) if s else ""


def fetch_institution_by_name(name: str, country: str) -> dict | None:
    """Search OpenAlex institutions by name, return first match with coords."""
    url = f"{OPENALEX_BASE}/institutions"
    params = {
        "search": name,
        "per_page": 3,
        "mailto": MAILTO,
    }
    if country:
        params["filter"] = f"country_code:{country.lower()}"
    try:
        r = requests.get(url, params=params, timeout=20,
                         headers={"User-Agent": f"elasmo_analyses/1.0 ({MAILTO})"})
        if r.status_code != 200:
            return None
        results = r.json().get("results", [])
        for inst in results:
            geo = inst.get("geo") or {}
            if geo.get("latitude") is not None:
                return {
                    "id": strip_prefix(inst.get("id", "")),
                    "name": inst.get("display_name", ""),
                    "country": geo.get("country_code", country),
                    "city": geo.get("city", ""),
                    "region": geo.get("region", ""),
                    "lat": geo.get("latitude"),
                    "lon": geo.get("longitude"),
                    "type": inst.get("type", ""),
                }
    except Exception as e:
        print(f"  Lookup failed for {name}: {e}")
    return None


def main():
    print("Loading data...")
    authors = pd.read_csv(AUTHORS_CSV)
    authors["aid"] = authors["openalex_author_id"].apply(strip_prefix)

    last_inst = pd.read_csv(LAST_INST_CSV)
    last_inst["aid"] = last_inst["openalex_author_id"].apply(strip_prefix)
    enriched_ids = set(last_inst[last_inst["last_institution_name"].notna()]["aid"])

    missing = set(authors["aid"]) - enriched_ids
    print(f"  Missing: {len(missing)} authors")

    pa = pd.read_csv(PAPER_AUTHORS_CSV)
    pa["aid"] = pa["openalex_author_id"].apply(strip_prefix)

    # Load year per paper
    pq = pd.read_parquet(PARQUET, columns=["literature_id", "year"])
    pq["literature_id"] = pq["literature_id"].apply(
        lambda v: str(int(float(v))) if pd.notna(v) else ""
    )
    pq = pq[pq["literature_id"] != ""]
    year_map = dict(zip(pq["literature_id"], pq["year"]))

    pa["lit_id_str"] = pa["literature_id"].apply(
        lambda v: str(int(float(v))) if pd.notna(v) else ""
    )
    pa["year"] = pa["lit_id_str"].map(year_map)

    # For each missing author, pick most recent paper with institution data
    print("Selecting most recent institution per missing author...")
    pa_missing = pa[pa["aid"].isin(missing) & pa["institution_name"].notna()].copy()
    pa_missing = pa_missing.sort_values(["aid", "year"], ascending=[True, False])
    picks = pa_missing.drop_duplicates(subset="aid", keep="first")
    print(f"  Picked {len(picks)} authors with institution data from paper_authors")

    # Load existing institutions for coord lookup
    if INSTITUTIONS_CSV.exists():
        inst_db = pd.read_csv(INSTITUTIONS_CSV)
        inst_db["name_lower"] = inst_db["display_name"].str.lower().str.strip()
        name_to_inst = {}
        for _, row in inst_db.iterrows():
            name_to_inst[row["name_lower"]] = row
    else:
        name_to_inst = {}

    # Build rows; look up coords from our existing institutions first,
    # then fall back to OpenAlex API for new institutions
    new_rows = []
    api_lookups = 0
    found_in_db = 0

    for i, row in enumerate(picks.itertuples(index=False), 1):
        if i % 200 == 0:
            print(f"  {i}/{len(picks)} (db hits: {found_in_db}, API lookups: {api_lookups})")

        inst_name = str(row.institution_name).strip()
        inst_country = str(row.institution_country) if pd.notna(row.institution_country) else ""

        # Try local DB first
        db_match = name_to_inst.get(inst_name.lower())
        if db_match is not None:
            found_in_db += 1
            new_rows.append({
                "openalex_author_id": f"https://openalex.org/{row.aid}",
                "last_institution_id": db_match["institution_id"],
                "last_institution_name": db_match["display_name"],
                "last_institution_country": db_match["country_code"],
                "last_institution_city": db_match["city"] if pd.notna(db_match["city"]) else "",
                "last_institution_region": db_match["region"] if pd.notna(db_match["region"]) else "",
                "last_institution_lat": db_match["latitude"],
                "last_institution_lon": db_match["longitude"],
                "last_institution_type": db_match["type"] if pd.notna(db_match["type"]) else "",
            })
            continue

        # Fallback: API lookup (rate-limited to 5/sec via polite pool)
        api_lookups += 1
        time.sleep(0.15)
        inst = fetch_institution_by_name(inst_name, inst_country)
        if inst:
            new_rows.append({
                "openalex_author_id": f"https://openalex.org/{row.aid}",
                "last_institution_id": inst["id"],
                "last_institution_name": inst["name"],
                "last_institution_country": inst["country"],
                "last_institution_city": inst["city"],
                "last_institution_region": inst["region"],
                "last_institution_lat": inst["lat"],
                "last_institution_lon": inst["lon"],
                "last_institution_type": inst["type"],
            })
            # Add to in-memory cache
            name_to_inst[inst_name.lower()] = pd.Series({
                "institution_id": inst["id"],
                "display_name": inst["name"],
                "country_code": inst["country"],
                "city": inst["city"],
                "region": inst["region"],
                "latitude": inst["lat"],
                "longitude": inst["lon"],
                "type": inst["type"],
            })
        else:
            # Store institution name without coords (won't place on map but shows in tooltip)
            new_rows.append({
                "openalex_author_id": f"https://openalex.org/{row.aid}",
                "last_institution_id": "",
                "last_institution_name": inst_name,
                "last_institution_country": inst_country,
                "last_institution_city": "",
                "last_institution_region": "",
                "last_institution_lat": "",
                "last_institution_lon": "",
                "last_institution_type": "",
            })

    print(f"\nFinal: {len(new_rows)} new rows")
    print(f"  From local DB: {found_in_db}")
    print(f"  From API: {api_lookups}")
    print(f"  With coords: {sum(1 for r in new_rows if r['last_institution_lat'])}")

    # Merge with existing CSV, preferring rows with non-null institution data
    existing = pd.read_csv(LAST_INST_CSV)
    new_df = pd.DataFrame(new_rows)
    # Put new_df FIRST so drop_duplicates keeps the new (data-rich) row over old NaN rows
    combined = pd.concat([new_df, existing], ignore_index=True)
    # Also sort so that rows with institution_name come before NaN within each author
    combined["_has_name"] = combined["last_institution_name"].notna().astype(int)
    combined = combined.sort_values(
        ["openalex_author_id", "_has_name"], ascending=[True, False]
    )
    combined = combined.drop_duplicates(subset="openalex_author_id", keep="first")
    combined = combined.drop(columns=["_has_name"])
    combined.to_csv(LAST_INST_CSV, index=False)

    enriched_count = combined["last_institution_name"].notna().sum()
    coord_count = combined["last_institution_lat"].notna().sum()
    print(f"\nWrote combined CSV: {len(combined)} rows")
    print(f"  with institution name: {enriched_count} ({100*enriched_count/len(combined):.1f}%)")
    print(f"  with coordinates:      {coord_count} ({100*coord_count/len(combined):.1f}%)")


if __name__ == "__main__":
    main()
