#!/usr/bin/env python3
"""Fix literature_id column across all project files.

Issues addressed:
1. Strip '.0' suffix from all literature_ids (pandas float64 NaN contamination)
2. Assign sequential IDs to 2,293 papers with literature_id == 'nan'
3. Propagate fixes to all downstream files

Author: Simon Dedman
Date: 2026-04-01
"""

import json
import pandas as pd
from pathlib import Path

BASE = Path("/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel")


def clean_lit_id(val: str) -> str:
    """Strip '.0' suffix from a literature_id string."""
    if isinstance(val, str) and val.endswith(".0"):
        return val[:-2]
    return val


def main() -> None:
    # ── Step 1: Load base parquet and fix IDs ────────────────────────────
    print("Loading literature_review.parquet...")
    df_base = pd.read_parquet(BASE / "outputs/literature_review.parquet")
    print(f"  Rows: {len(df_base)}")

    # Strip .0 from non-nan entries
    mask_real = df_base["literature_id"] != "nan"
    df_base.loc[mask_real, "literature_id"] = (
        df_base.loc[mask_real, "literature_id"].map(clean_lit_id)
    )

    # Find max existing ID
    existing_ids = df_base.loc[mask_real, "literature_id"].astype(int)
    max_id = existing_ids.max()
    print(f"  Max existing literature_id: {max_id}")

    # Assign new IDs to nan papers
    mask_nan = df_base["literature_id"] == "nan"
    nan_count = mask_nan.sum()
    print(f"  Papers needing new IDs: {nan_count}")

    new_ids = [str(max_id + 1 + i) for i in range(nan_count)]
    df_base.loc[mask_nan, "literature_id"] = new_ids

    # Build mapping: index -> new literature_id (for nan papers)
    # Also build DOI -> new_id mapping for papers_data.json
    nan_doi_map: dict[str, str] = {}
    nan_rows = df_base.loc[mask_nan]
    for idx, row in nan_rows.iterrows():
        doi = row.get("doi")
        if doi and isinstance(doi, str) and doi.strip():
            nan_doi_map[doi.strip().lower()] = row["literature_id"]

    print(f"  DOI->new_id mappings for papers_data.json: {len(nan_doi_map)}")

    # Verify base parquet
    assert df_base["literature_id"].isna().sum() == 0, "Found NaN values"
    assert (df_base["literature_id"] == "nan").sum() == 0, "Found 'nan' strings"
    assert df_base["literature_id"].str.endswith(".0").sum() == 0, "Found .0 suffixes"
    n_unique = df_base["literature_id"].nunique()
    print(f"  Unique literature_ids: {n_unique} (total rows: {len(df_base)})")
    # Note: pre-existing duplicates (63 groups) mean unique < total

    # Save base parquet
    print("  Saving literature_review.parquet...")
    df_base.to_parquet(BASE / "outputs/literature_review.parquet", index=False)

    # ── Step 2: Fix enriched parquet ─────────────────────────────────────
    print("\nLoading literature_review_enriched.parquet...")
    df_enr = pd.read_parquet(BASE / "outputs/literature_review_enriched.parquet")

    # Strip .0
    mask_real_e = df_enr["literature_id"] != "nan"
    df_enr.loc[mask_real_e, "literature_id"] = (
        df_enr.loc[mask_real_e, "literature_id"].map(clean_lit_id)
    )

    # Assign same new IDs (rows should be in same order)
    mask_nan_e = df_enr["literature_id"] == "nan"
    assert mask_nan_e.sum() == nan_count, (
        f"Enriched nan count {mask_nan_e.sum()} != base {nan_count}"
    )
    df_enr.loc[mask_nan_e, "literature_id"] = new_ids

    # Verify
    assert (df_enr["literature_id"] == "nan").sum() == 0
    assert df_enr["literature_id"].str.endswith(".0").sum() == 0

    print("  Saving literature_review_enriched.parquet...")
    df_enr.to_parquet(BASE / "outputs/literature_review_enriched.parquet", index=False)

    # ── Step 3: Fix viz_data.csv ─────────────────────────────────────────
    print("\nLoading viz_data.csv...")
    df_viz = pd.read_csv(BASE / "outputs/viz_data.csv", dtype=str)
    print(f"  Rows: {len(df_viz)}")

    # Strip .0 from non-null entries
    not_null = df_viz["literature_id"].notna()
    df_viz.loc[not_null, "literature_id"] = (
        df_viz.loc[not_null, "literature_id"].map(clean_lit_id)
    )

    # For null entries, we need to match them to the base parquet.
    # viz_data.csv has 30553 rows vs 30558 in parquet (5 fewer).
    # Use DOI matching to assign new IDs to null entries.
    null_mask = df_viz["literature_id"].isna()
    null_count_viz = null_mask.sum()
    print(f"  Null literature_ids in viz_data: {null_count_viz}")

    if null_count_viz > 0:
        # Try DOI matching first
        assigned = 0
        for idx in df_viz.index[null_mask]:
            doi = df_viz.at[idx, "doi"]
            if isinstance(doi, str) and doi.strip():
                new_id = nan_doi_map.get(doi.strip().lower())
                if new_id:
                    df_viz.at[idx, "literature_id"] = new_id
                    assigned += 1
        print(f"  Assigned via DOI match: {assigned}")

        # For remaining nulls, match by title
        still_null = df_viz["literature_id"].isna()
        remaining = still_null.sum()
        if remaining > 0:
            print(f"  Remaining nulls after DOI match: {remaining}")
            # Build title -> new_id map from base
            title_map: dict[str, str] = {}
            for idx, row in nan_rows.iterrows():
                title = row.get("title")
                if title and isinstance(title, str) and title.strip():
                    title_map[title.strip().lower()] = row["literature_id"]

            for idx in df_viz.index[still_null]:
                title = df_viz.at[idx, "title"]
                if isinstance(title, str) and title.strip():
                    new_id = title_map.get(title.strip().lower())
                    if new_id:
                        df_viz.at[idx, "literature_id"] = new_id
                        assigned += 1

            still_null2 = df_viz["literature_id"].isna()
            print(f"  After title match, remaining nulls: {still_null2.sum()}")

    # Verify
    remaining_dot0 = df_viz["literature_id"].dropna().str.endswith(".0").sum()
    assert remaining_dot0 == 0, f"Found {remaining_dot0} .0 suffixes in viz_data"

    print("  Saving viz_data.csv...")
    df_viz.to_csv(BASE / "outputs/viz_data.csv", index=False)

    # ── Step 4: Fix schema_extraction_evidence.csv ───────────────────────
    print("\nLoading schema_extraction_evidence.csv...")
    df_ev = pd.read_csv(
        BASE / "outputs/schema_extraction_evidence.csv",
        dtype={"literature_id": str},
    )
    print(f"  Rows: {len(df_ev)}")

    # Strip .0
    not_null_ev = df_ev["literature_id"].notna()
    df_ev.loc[not_null_ev, "literature_id"] = (
        df_ev.loc[not_null_ev, "literature_id"].map(clean_lit_id)
    )

    # Check for nan strings
    nan_ev = (df_ev["literature_id"] == "nan").sum()
    print(f"  'nan' strings in evidence: {nan_ev}")

    # Evidence file only has papers with PDFs, so nan-ID papers (from SR)
    # likely aren't in it. But if they are, assign via DOI/title.
    if nan_ev > 0:
        for idx in df_ev.index[df_ev["literature_id"] == "nan"]:
            doi = df_ev.at[idx, "doi"] if "doi" in df_ev.columns else None
            if isinstance(doi, str) and doi.strip():
                new_id = nan_doi_map.get(doi.strip().lower())
                if new_id:
                    df_ev.at[idx, "literature_id"] = new_id

    assert df_ev["literature_id"].dropna().str.endswith(".0").sum() == 0

    print("  Saving schema_extraction_evidence.csv...")
    df_ev.to_csv(BASE / "outputs/schema_extraction_evidence.csv", index=False)

    # ── Step 5: Fix papers_data.json ─────────────────────────────────────
    print("\nLoading papers_data.json...")
    with open(BASE / "docs/papers_data.json", "r") as f:
        papers = json.load(f)
    print(f"  Entries: {len(papers)}")

    # Build a quick lookup from cleaned base parquet: DOI -> lit_id, title -> lit_id
    base_doi_map: dict[str, str] = {}
    base_title_map: dict[str, str] = {}
    for _, row in df_base[["literature_id", "doi", "title"]].iterrows():
        lid = row["literature_id"]
        doi = row.get("doi")
        title = row.get("title")
        if doi and isinstance(doi, str) and doi.strip():
            base_doi_map[doi.strip().lower()] = lid
        if title and isinstance(title, str) and title.strip():
            base_title_map[title.strip().lower()] = lid

    fixed_dot0 = 0
    fixed_empty = 0
    for paper in papers:
        lit_id = paper.get("literature_id", "")
        if isinstance(lit_id, str) and lit_id.endswith(".0"):
            paper["literature_id"] = lit_id[:-2]
            fixed_dot0 += 1
        elif lit_id == "" or lit_id is None or str(lit_id) == "nan":
            # Try to find the ID from base data
            doi = paper.get("doi", "")
            title = paper.get("title", "")
            new_id = None
            if doi and isinstance(doi, str) and doi.strip():
                new_id = base_doi_map.get(doi.strip().lower())
            if not new_id and title and isinstance(title, str) and title.strip():
                new_id = base_title_map.get(title.strip().lower())
            if new_id:
                paper["literature_id"] = new_id
                fixed_empty += 1

    print(f"  Fixed .0 suffixes: {fixed_dot0}")
    print(f"  Assigned IDs to empty entries: {fixed_empty}")

    # Count remaining empties
    still_empty = sum(
        1
        for p in papers
        if p.get("literature_id", "") in ("", None, "nan")
    )
    print(f"  Remaining empty literature_ids: {still_empty}")

    print("  Saving papers_data.json...")
    with open(BASE / "docs/papers_data.json", "w") as f:
        json.dump(papers, f, indent=2, ensure_ascii=False)

    # ── Step 6: Final verification ───────────────────────────────────────
    print("\n" + "=" * 60)
    print("VERIFICATION")
    print("=" * 60)

    # Re-read and verify
    df_check = pd.read_parquet(BASE / "outputs/literature_review.parquet",
                                columns=["literature_id"])
    print(f"\nliterature_review.parquet:")
    print(f"  Rows: {len(df_check)}")
    print(f"  Unique IDs: {df_check['literature_id'].nunique()}")
    print(f"  NaN count: {df_check['literature_id'].isna().sum()}")
    print(f"  'nan' strings: {(df_check['literature_id'] == 'nan').sum()}")
    print(f"  .0 suffixes: {df_check['literature_id'].str.endswith('.0').sum()}")
    print(f"  Sample: {df_check['literature_id'].head(5).tolist()}")

    df_check2 = pd.read_parquet(BASE / "outputs/literature_review_enriched.parquet",
                                 columns=["literature_id"])
    print(f"\nliterature_review_enriched.parquet:")
    print(f"  Rows: {len(df_check2)}")
    print(f"  Unique IDs: {df_check2['literature_id'].nunique()}")
    print(f"  'nan' strings: {(df_check2['literature_id'] == 'nan').sum()}")
    print(f"  .0 suffixes: {df_check2['literature_id'].str.endswith('.0').sum()}")

    print("\nDone.")


if __name__ == "__main__":
    main()
