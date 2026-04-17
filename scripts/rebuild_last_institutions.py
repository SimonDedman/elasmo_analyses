#!/usr/bin/env python3
"""
Rebuild outputs/openalex_authors_last_institution.csv from scratch,
using paper_authors.csv as the authoritative source rather than OpenAlex's
unreliable `last_known_institutions` API.

For each author:
1. Find their most recent paper(s) in paper_authors with institution data
2. Pick the institution that appears most frequently among their latest year
3. Look up that institution's lat/lon from openalex_institutions.csv
4. If not in local cache, query OpenAlex institutions API

Output: replaces outputs/openalex_authors_last_institution.csv
Preserves old CSV as outputs/openalex_authors_last_institution.openalex_api.csv
"""

import csv
import shutil
import time
from collections import Counter
from pathlib import Path

import pandas as pd
import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
AUTHORS_CSV = PROJECT_ROOT / "outputs" / "openalex_unique_authors.csv"
PAPER_AUTHORS_CSV = PROJECT_ROOT / "outputs" / "openalex_paper_authors.csv"
LAST_INST_CSV = PROJECT_ROOT / "outputs" / "openalex_authors_last_institution.csv"
INSTITUTIONS_CSV = PROJECT_ROOT / "outputs" / "openalex_institutions.csv"
PARQUET = PROJECT_ROOT / "outputs" / "literature_review_enriched.parquet"

OPENALEX_BASE = "https://api.openalex.org"
MAILTO = "simondedman@gmail.com"


def strip_prefix(s) -> str:
    if isinstance(s, str) and s.startswith("https://openalex.org/"):
        return s[len("https://openalex.org/"):]
    return str(s) if s else ""


def fetch_institution_by_name(name: str, country: str = "") -> dict | None:
    """Search OpenAlex institutions by name + optional country filter."""
    url = f"{OPENALEX_BASE}/institutions"
    params = {"search": name, "per_page": 3, "mailto": MAILTO}
    if country:
        params["filter"] = f"country_code:{country.lower()}"
    try:
        r = requests.get(url, params=params, timeout=20,
                         headers={"User-Agent": f"elasmo_analyses/1.0 ({MAILTO})"})
        if r.status_code != 200:
            return None
        for inst in r.json().get("results", []):
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
    print(f"  {len(authors)} authors")

    pa = pd.read_csv(PAPER_AUTHORS_CSV)
    pa["aid"] = pa["openalex_author_id"].apply(strip_prefix)

    t = pd.read_parquet(PARQUET, columns=["literature_id", "year"])
    t["literature_id"] = t["literature_id"].apply(
        lambda v: str(int(float(v))) if pd.notna(v) else ""
    )
    year_map = dict(zip(t["literature_id"], t["year"]))

    pa["lit_id"] = pa["literature_id"].apply(
        lambda v: str(int(float(v))) if pd.notna(v) else ""
    )
    pa["year"] = pa["lit_id"].map(year_map)

    # Only rows with institution data
    pa_with = pa[pa["institution_name"].notna()].copy()

    # For each author, find their most recent year with institution data,
    # then pick the most common institution from that year
    print("Resolving most-recent institution per author...")
    results = {}
    for aid, grp in pa_with.groupby("aid"):
        if not aid or aid == "nan":
            continue
        # Most recent year
        max_year = grp["year"].max()
        if pd.isna(max_year):
            continue
        # Papers from that year
        recent = grp[grp["year"] == max_year]
        # Most common institution in that year
        counts = Counter(zip(recent["institution_name"], recent["institution_country"].fillna("")))
        (inst_name, inst_country), _ = counts.most_common(1)[0]
        results[aid] = {
            "institution_name": inst_name,
            "institution_country": inst_country,
            "year": int(max_year),
        }

    print(f"  Resolved for {len(results)} authors")

    # Backup old CSV
    if LAST_INST_CSV.exists():
        backup_path = LAST_INST_CSV.with_suffix(".openalex_api.csv")
        if not backup_path.exists():
            shutil.copy(LAST_INST_CSV, backup_path)
            print(f"  Backed up old CSV to {backup_path.name}")

    # Load existing institutions cache for coord lookup
    inst_db = pd.read_csv(INSTITUTIONS_CSV) if INSTITUTIONS_CSV.exists() else pd.DataFrame()
    name_to_inst = {}
    if not inst_db.empty:
        for _, row in inst_db.iterrows():
            key = str(row["display_name"]).lower().strip()
            name_to_inst[key] = row

    # Build output rows — geocode each institution
    print("\nGeocoding institutions...")
    out_rows = []
    api_calls = 0
    db_hits = 0

    for i, aid in enumerate(authors["aid"]):
        if i % 1000 == 0:
            print(f"  {i}/{len(authors)} (db: {db_hits}, api: {api_calls})")
        r = results.get(aid)
        if not r:
            # No institution data for this author
            out_rows.append({
                "openalex_author_id": f"https://openalex.org/{aid}",
                "last_institution_id": "",
                "last_institution_name": "",
                "last_institution_country": "",
                "last_institution_city": "",
                "last_institution_region": "",
                "last_institution_lat": "",
                "last_institution_lon": "",
                "last_institution_type": "",
            })
            continue

        inst_name = r["institution_name"]
        inst_country = r["institution_country"]

        # Try local cache by name
        db_match = name_to_inst.get(inst_name.lower().strip())
        if db_match is not None:
            db_hits += 1
            out_rows.append({
                "openalex_author_id": f"https://openalex.org/{aid}",
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

        # Fallback: API
        api_calls += 1
        time.sleep(0.12)  # polite pool: ~8 req/sec max
        inst = fetch_institution_by_name(inst_name, inst_country)
        if inst:
            out_rows.append({
                "openalex_author_id": f"https://openalex.org/{aid}",
                "last_institution_id": inst["id"],
                "last_institution_name": inst["name"],
                "last_institution_country": inst["country"],
                "last_institution_city": inst["city"],
                "last_institution_region": inst["region"],
                "last_institution_lat": inst["lat"],
                "last_institution_lon": inst["lon"],
                "last_institution_type": inst["type"],
            })
            name_to_inst[inst_name.lower().strip()] = pd.Series({
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
            # Keep institution name + country but no coords
            out_rows.append({
                "openalex_author_id": f"https://openalex.org/{aid}",
                "last_institution_id": "",
                "last_institution_name": inst_name,
                "last_institution_country": inst_country,
                "last_institution_city": "",
                "last_institution_region": "",
                "last_institution_lat": "",
                "last_institution_lon": "",
                "last_institution_type": "",
            })

    df = pd.DataFrame(out_rows)
    df.to_csv(LAST_INST_CSV, index=False)

    with_name = df["last_institution_name"].astype(str).str.len() > 0
    with_coords = df["last_institution_lat"].notna() & (df["last_institution_lat"].astype(str) != "")
    print(f"\nWrote {len(df)} rows")
    print(f"  with institution name: {with_name.sum()} ({100*with_name.sum()/len(df):.1f}%)")
    print(f"  with coordinates:      {with_coords.sum()} ({100*with_coords.sum()/len(df):.1f}%)")

    # Merge newly-learned institutions into the institutions DB
    if api_calls > 0:
        print(f"\nUpdating institutions DB ({api_calls} new entries to add)...")
        new_insts = []
        for key, val in name_to_inst.items():
            if isinstance(val, pd.Series):
                new_insts.append(dict(val))
        new_df = pd.DataFrame(new_insts)
        # Dedupe by institution_id
        if not inst_db.empty:
            combined = pd.concat([inst_db, new_df], ignore_index=True)
        else:
            combined = new_df
        combined = combined.drop_duplicates(subset="institution_id", keep="first")
        combined.to_csv(INSTITUTIONS_CSV, index=False)
        print(f"  institutions.csv now has {len(combined)} rows")


if __name__ == "__main__":
    main()
