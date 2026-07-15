#!/usr/bin/env python3
"""Build outputs/first_author_namsor.csv — the per-PAPER first-author gender /
origin / ethnicity table consumed by rebuild_viz_data.py (and thence every
gender/origin/ethnicity figure in the deck).

This builder was historically a one-off that was never committed, so the file
existed on disk with no way to regenerate it. This script recreates it from the
two upstream side-tables so incremental enrichment of new papers propagates:

    openalex_paper_authors.csv   (per paper-author; author_position, openalex_author_id)
        └─ take the FIRST author per literature_id
    namsor_enrichment.csv        (per author; key `id` = openalex_author_id)
        └─ join on openalex_author_id

Output columns (matching the legacy file rebuild_viz_data.py expects):
    literature_id, gender_first_author_improved, origin_country_first,
    origin_region_first, origin_subregion_first, ethnicity_first,
    ethnicity_alt_first, gender_probability_first

`gender_first_author_improved` = NamSor gender (title-cased Male/Female),
falling back to the OpenAlex/gender-guesser `gender` column when NamSor has no
verdict — hence "improved".

Usage:  python scripts/build_first_author_namsor.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

BASE = Path("/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel")
PAPER_AUTHORS = BASE / "outputs/openalex_paper_authors.csv"
NAMSOR = BASE / "outputs/namsor_enrichment.csv"
# gender_guesser fallback lives here (per-author). Used when NamSor has no
# verdict — the openalex_paper_authors.csv `gender` column is unreliable because
# enrich_authors_openalex.py --resume regenerates that file from raw API records
# and drops the inferred `gender` column, so we read the cleaned unique-authors
# table instead (which persists across resume runs).
UNIQUE_CLEANED = BASE / "outputs/openalex_unique_authors_cleaned.csv"
OUT = BASE / "outputs/first_author_namsor.csv"

FIRST_POS = {"1", "first", "1.0"}


def _titlecase_gender(s: pd.Series) -> pd.Series:
    m = {"male": "Male", "female": "Female", "m": "Male", "f": "Female"}
    return s.astype(str).str.strip().str.lower().map(m)


def main() -> int:
    pa = pd.read_csv(PAPER_AUTHORS, dtype=str, low_memory=False)
    ns = pd.read_csv(NAMSOR, dtype=str, low_memory=False)

    # First author per paper
    first = pa[pa["author_position"].astype(str).isin(FIRST_POS)].copy()
    first = first.drop_duplicates(subset="literature_id", keep="first")
    print(f"First authors: {len(first)} papers "
          f"(of {pa['literature_id'].nunique()} with any author)")

    # Join NamSor per-author enrichment onto the first author
    merged = first.merge(ns, left_on="openalex_author_id", right_on="id", how="left")

    # gender_guesser fallback from the cleaned unique-authors table (keyed by
    # openalex_author_id), joined on so it survives the paper_authors gender drop.
    cleaned = pd.read_csv(UNIQUE_CLEANED, dtype=str, low_memory=False)[["openalex_author_id", "gender"]]
    cleaned = cleaned.rename(columns={"gender": "gender_guesser"}).drop_duplicates("openalex_author_id")
    merged = merged.merge(cleaned, on="openalex_author_id", how="left")

    # NamSor gender (title-cased) with fallback to the gender-guesser verdict.
    ns_gender = _titlecase_gender(merged.get("namsor_gender", pd.Series(index=merged.index, dtype=str)))
    oa_gender = _titlecase_gender(merged.get("gender_guesser", pd.Series(index=merged.index, dtype=str)))
    gender = ns_gender.fillna(oa_gender)

    out = pd.DataFrame({
        "literature_id": merged["literature_id"].astype(str),
        "gender_first_author_improved": gender,
        "origin_country_first": merged.get("namsor_origin_country"),
        "origin_region_first": merged.get("namsor_origin_region"),
        "origin_subregion_first": merged.get("namsor_origin_subregion"),
        "ethnicity_first": merged.get("namsor_ethnicity"),
        "ethnicity_alt_first": merged.get("namsor_ethnicity_alt"),
        "gender_probability_first": merged.get("namsor_gender_probability"),
    })
    out = out.drop_duplicates(subset="literature_id", keep="first")
    # A first author with no gender verdict at all reads as "Unknown" in the
    # deck's gender figures (matches the legacy table's behaviour).
    out["gender_first_author_improved"] = out["gender_first_author_improved"].fillna("Unknown")
    out.to_csv(OUT, index=False)
    n_gender = out["gender_first_author_improved"].notna().sum()
    n_origin = out["origin_country_first"].notna().sum()
    print(f"Wrote {OUT.name}: {len(out)} papers | "
          f"gender {n_gender} ({100*n_gender/len(out):.1f}%) | "
          f"origin {n_origin} ({100*n_origin/len(out):.1f}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
