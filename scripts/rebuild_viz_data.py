#!/usr/bin/env python3
"""Rebuild outputs/viz_data.csv from the current literature_review_enriched.parquet.

viz_data.csv is the flat CSV consumed by the viz_*.R figure scripts. It is a
merge of the base parquet (schema/technique columns) with several separately
maintained enrichment side-tables (Altmetric, NamSor gender/origin/ethnicity,
Unpaywall OA status, OpenAlex first-author institution country). Those
enrichment pipelines are NOT re-run here (that's a separate, longer job) --
this script only refreshes the corpus rows/columns from the current parquet
and re-joins whatever enrichment data already exists on disk, so newly added
papers will show as NA for enrichment columns until those pipelines are
re-run against them.

One-off refresh, ad hoc for 2026-07-06 AES figure regeneration.
"""
import pandas as pd

BASE = "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"


def clean_lit_id(series):
    """Strip pandas float '.0' suffix from literature_id strings (known bug, see MEMORY.md)."""
    return series.astype(str).str.replace(r"\.0$", "", regex=True)

print("Loading base parquet...")
df = pd.read_parquet(f"{BASE}/outputs/literature_review_enriched.parquet")
df["literature_id"] = df["literature_id"].astype(str)
print(f"  {df.shape[0]} rows, {df.shape[1]} cols")

# ---- Altmetric ----
try:
    alt = pd.read_csv(f"{BASE}/outputs/altmetric_scores.csv", dtype={"literature_id": str})
    alt["literature_id"] = clean_lit_id(alt["literature_id"])
    alt_cols = [c for c in alt.columns if c not in ("literature_id", "doi")]
    df = df.merge(alt[["literature_id"] + alt_cols], on="literature_id", how="left")
    print(f"  Altmetric joined: {alt['literature_id'].notna().sum()} rows, matched {df[alt_cols[0]].notna().sum()}")
except FileNotFoundError:
    print("  Altmetric file not found, skipping")

# ---- NamSor first-author (gender/origin/ethnicity) ----
try:
    ns = pd.read_csv(f"{BASE}/outputs/first_author_namsor.csv", dtype={"literature_id": str})
    df = df.merge(ns, on="literature_id", how="left")
    df["gender_first_author"] = df["gender_first_author_improved"]
    print(f"  NamSor first-author joined: matched {df['gender_first_author_improved'].notna().sum()}")
except FileNotFoundError:
    print("  first_author_namsor.csv not found, skipping")

# ---- Unpaywall OA status ----
try:
    oa = pd.read_csv(f"{BASE}/outputs/unpaywall_oa_by_doi.csv", dtype={"literature_id": str})
    oa["literature_id"] = clean_lit_id(oa["literature_id"])
    oa_cols = [c for c in ["oa_status", "oa_url", "oa_host_type", "oa_license"] if c in oa.columns]
    oa_small = oa[["literature_id"] + oa_cols].drop_duplicates(subset="literature_id")
    df = df.merge(oa_small, on="literature_id", how="left")
    print(f"  Unpaywall OA joined: matched {df[oa_cols[0]].notna().sum()}")
except FileNotFoundError:
    print("  unpaywall_oa_by_doi.csv not found, skipping")

# ---- OpenAlex first-author institution country ----
try:
    oap = pd.read_csv(f"{BASE}/outputs/openalex_paper_authors.csv", dtype={"literature_id": str})
    first_auth = (
        oap[oap["author_position"].astype(str).isin(["1", "first"])]
        .drop_duplicates(subset="literature_id")[["literature_id", "institution_country"]]
        .rename(columns={"institution_country": "institution_country_first"})
    )
    df = df.merge(first_auth, on="literature_id", how="left")
    # Back-compat alias: some viz_*.R scripts (A4/A5 parachute/gender maps)
    # look for "institution_country" rather than "institution_country_first".
    df["institution_country"] = df["institution_country_first"]
    print(f"  OpenAlex institution_country_first joined: matched {df['institution_country_first'].notna().sum()}")
except FileNotFoundError:
    print("  openalex_paper_authors.csv not found, skipping")

out_path = f"{BASE}/outputs/viz_data.csv"
print(f"Writing {out_path} ({df.shape[0]} rows, {df.shape[1]} cols)...")
df.to_csv(out_path, index=False)
print("Done.")
