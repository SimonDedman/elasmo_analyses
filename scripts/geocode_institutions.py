#!/usr/bin/env python3
"""
Precise-geocode institutions that OpenAlex has collapsed onto a generic
CITY-CENTROID coordinate (tell-tale: two or more distinct institutions
sharing bit-identical lat/lon, e.g. California Academy of Sciences and
San Francisco State University both reported at 37.77492904663086,
-122.41941833496094).

Detection scope: institutions attached to "focal" authors (paper_count
>= --min-papers, default 3, matching MIN_PAPERS in build_author_atlas.R)
via outputs/openalex_authors_last_institution.openalex_api.csv (falls
back to the non-.openalex_api variant). Restricting to focal-author
institutions keeps the run tractable under Nominatim's 1 req/sec policy
while covering everything that actually renders on the atlas.

Geocoding: OpenStreetMap Nominatim (free, no key). Query
"<institution name>, <city>, <country>". A result is accepted only if
Nominatim's own classification indicates a specific place (not a city/
town/administrative area) -- i.e. it is not itself another city-level
point. On failure (no result, or result is itself city-level) the
original OpenAlex coordinate is kept and the row is logged as failed.

Resumable: every Nominatim response (success or failure) is cached in
a JSON file keyed by query string, so re-running the script only makes
network calls for institutions not yet resolved.

Output: outputs/institution_geocode_corrections.csv with columns
institution_id, display_name, city, region, country, old_lat, old_lon,
new_lat, new_lon, status, query, nominatim_display_name

Usage:
    python3 scripts/geocode_institutions.py [--min-papers 3] [--limit N]
"""
import argparse
import json
import math
import re
import sys
import time
from pathlib import Path

import pandas as pd
import requests
from babel import Locale

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "outputs"
CACHE_PATH = OUT_DIR / ".nominatim_geocode_cache.json"
CORRECTIONS_PATH = OUT_DIR / "institution_geocode_corrections.csv"

USER_AGENT = "EEA2025-shark (mailto:simondedman@gmail.com)"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
RATE_LIMIT_SECONDS = 1.0

# Reject a geocode result if it lands further than this from the original
# OpenAlex coordinate. Multi-site orgs (CNRS, CSIRO, ...) queried without a
# city constraint can otherwise resolve to an arbitrary branch hundreds or
# thousands of km from the record's actual city -- a worse error than the
# imprecise-but-correctly-located city centroid we started with.
MAX_DISTANCE_KM = 100.0

# Nominatim classifications that indicate a generic city/administrative
# point rather than a specific institution -- reject these as "still
# city-level".
CITY_LEVEL_TYPES = {
    "city", "town", "village", "administrative", "hamlet",
    "municipality", "county", "state", "country", "suburb",
    "city_block", "borough", "postcode",
}

_EN = Locale("en")
_LEADING_ARTICLE_RE = re.compile(r"^(the|le|la|les)\s+", re.IGNORECASE)


def country_name(code: str) -> str:
    if not isinstance(code, str) or not code.strip():
        return ""
    return _EN.territories.get(code.upper(), code)


def strip_article(name: str) -> str:
    if not isinstance(name, str):
        return name
    return _LEADING_ARTICLE_RE.sub("", name).strip()


def is_city_level_result(res: dict) -> bool:
    return (not res.get("found")) or res.get("type") in CITY_LEVEL_TYPES or res.get("class_") in ("boundary", "place")


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def load_focal_institutions(min_papers: int) -> pd.DataFrame:
    li_path = OUT_DIR / "openalex_authors_last_institution.openalex_api.csv"
    if not li_path.exists():
        li_path = OUT_DIR / "openalex_authors_last_institution.csv"
    li = pd.read_csv(li_path)

    authors = pd.read_csv(OUT_DIR / "openalex_unique_authors.csv")[
        ["openalex_author_id", "paper_count"]
    ]
    merged = li.merge(authors, on="openalex_author_id", how="left")
    focal = merged[merged["paper_count"].fillna(0) >= min_papers].dropna(
        subset=["last_institution_lat", "last_institution_lon", "last_institution_id"]
    )

    inst = (
        focal.sort_values("paper_count", ascending=False)
        .drop_duplicates(subset=["last_institution_id"])
        [[
            "last_institution_id", "last_institution_name", "last_institution_city",
            "last_institution_region", "last_institution_country",
            "last_institution_lat", "last_institution_lon",
        ]]
        .rename(columns={
            "last_institution_id": "institution_id",
            "last_institution_name": "display_name",
            "last_institution_city": "city",
            "last_institution_region": "region",
            "last_institution_country": "country",
            "last_institution_lat": "lat",
            "last_institution_lon": "lon",
        })
        .reset_index(drop=True)
    )
    return inst


def detect_city_level(inst: pd.DataFrame) -> pd.DataFrame:
    """Flag institutions whose coordinate (rounded to 5dp, ~1m) is shared
    by >=2 distinct institution_id values -- i.e. a shared centroid."""
    df = inst.copy()
    df["lat_r"] = df["lat"].round(5)
    df["lon_r"] = df["lon"].round(5)
    counts = df.groupby(["lat_r", "lon_r"])["institution_id"].transform("nunique")
    df["is_city_level"] = counts >= 2
    return df


def load_cache() -> dict:
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text())
    return {}


def save_cache(cache: dict) -> None:
    CACHE_PATH.write_text(json.dumps(cache, indent=1, ensure_ascii=False))


def geocode_one(query: str, cache: dict, countrycodes: str = "") -> dict:
    """Return a dict with keys: found(bool), lat, lon, type, class_, display_name.
    Uses/updates the on-disk cache; caller is responsible for rate limiting
    (only sleeps when an actual network call is made). Cache key includes
    the countrycodes restriction so variants don't collide."""
    cache_key = f"{query}|cc={countrycodes}"
    if cache_key in cache:
        return cache[cache_key]

    params = {"q": query, "format": "json", "limit": 1, "addressdetails": 0}
    if countrycodes:
        params["countrycodes"] = countrycodes
    resp = requests.get(
        NOMINATIM_URL,
        params=params,
        headers={"User-Agent": USER_AGENT},
        timeout=15,
    )
    time.sleep(RATE_LIMIT_SECONDS)
    result = {"found": False}
    if resp.status_code == 200:
        data = resp.json()
        if data:
            top = data[0]
            result = {
                "found": True,
                "lat": float(top["lat"]),
                "lon": float(top["lon"]),
                "type": top.get("type", ""),
                "class_": top.get("class", ""),
                "display_name": top.get("display_name", ""),
            }
    cache[cache_key] = result
    return result


def geocode_with_fallback(name: str, city: str, country_code: str, cache: dict,
                           orig_lat: float, orig_lon: float) -> tuple:
    """Try a chain of increasingly loose queries; return (result_dict, query_used,
    rejected_reason) for the first one that resolves to a non-city-level place
    within MAX_DISTANCE_KM of the original OpenAlex coordinate. If all fail,
    return the last result, its query, and why it was rejected."""
    stripped = strip_article(name)
    cname = country_name(country_code)
    cc = country_code.lower() if isinstance(country_code, str) and len(country_code) == 2 else ""
    has_city = isinstance(city, str) and city.strip()

    # Queries WITH the city are tried first -- much less likely to jump to
    # the wrong branch of a multi-site org than a name-only query.
    variants = []
    if has_city:
        variants.append((f"{stripped}, {city}", cc))
        if cname:
            variants.append((f"{stripped}, {city}, {cname}", ""))
    variants.append((stripped, cc))

    last_res, last_query, last_reason = {"found": False}, variants[0][0] if variants else stripped, "no_result"
    for q, variant_cc in variants:
        res = geocode_one(q, cache, countrycodes=variant_cc)
        last_res, last_query = res, q
        if is_city_level_result(res):
            last_reason = "no_result" if not res.get("found") else "still_city_level"
            continue
        dist = haversine_km(orig_lat, orig_lon, res["lat"], res["lon"])
        if dist > MAX_DISTANCE_KM:
            last_reason = f"too_far_{dist:.0f}km"
            continue
        return res, q, None
    return last_res, last_query, last_reason


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-papers", type=int, default=3,
                     help="Only consider institutions of authors with >= this many papers (matches MIN_PAPERS in build_author_atlas.R)")
    ap.add_argument("--limit", type=int, default=None,
                     help="Cap number of institutions geocoded this run (for testing)")
    args = ap.parse_args()

    print(f"Loading focal-author institutions (min_papers={args.min_papers})...")
    inst = load_focal_institutions(args.min_papers)
    print(f"  {len(inst)} distinct institutions attached to focal authors")

    flagged = detect_city_level(inst)
    city_level = flagged[flagged["is_city_level"]].copy()
    print(f"  {len(city_level)} are city-level (coord shared by >=2 institutions)")

    if args.limit:
        city_level = city_level.head(args.limit)
        print(f"  --limit applied: geocoding {len(city_level)} this run")

    cache = load_cache()
    rows = []
    n_success = 0
    n_fail = 0
    for i, r in enumerate(city_level.itertuples(), 1):
        res, query, reject_reason = geocode_with_fallback(
            r.display_name, r.city, r.country, cache, r.lat, r.lon
        )
        if i % 20 == 0:
            save_cache(cache)  # periodic checkpoint so a crash doesn't lose progress
            print(f"  [{i}/{len(city_level)}] checkpointed cache...")

        accepted = reject_reason is None
        if accepted:
            n_success += 1
            rows.append({
                "institution_id": r.institution_id,
                "display_name": r.display_name,
                "city": r.city,
                "region": r.region,
                "country": r.country,
                "old_lat": r.lat,
                "old_lon": r.lon,
                "new_lat": res["lat"],
                "new_lon": res["lon"],
                "status": "geocoded",
                "query": query,
                "nominatim_display_name": res.get("display_name", ""),
            })
        else:
            n_fail += 1
            rows.append({
                "institution_id": r.institution_id,
                "display_name": r.display_name,
                "city": r.city,
                "region": r.region,
                "country": r.country,
                "old_lat": r.lat,
                "old_lon": r.lon,
                "new_lat": "",
                "new_lon": "",
                "status": f"failed:{reject_reason}",
                "query": query,
                "nominatim_display_name": res.get("display_name", ""),
            })

    save_cache(cache)
    out_df = pd.DataFrame(rows)
    out_df.to_csv(CORRECTIONS_PATH, index=False)

    print(f"\nDone. {n_success} geocoded, {n_fail} failed, out of {len(city_level)} city-level institutions.")
    print(f"Wrote {CORRECTIONS_PATH}")
    print(f"Cache: {CACHE_PATH}")


if __name__ == "__main__":
    sys.exit(main())
