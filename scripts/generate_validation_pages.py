#!/usr/bin/env python3
"""
Generate HTML validation pages for the elasmobranch analytical methods review.

Reads parquet + CSV data, builds per-author PAGE_DATA structures, and renders
Jinja2 templates to docs/validate/{id}.html.

Usage:
    python scripts/generate_validation_pages.py                    # all authors
    python scripts/generate_validation_pages.py --author A5086753224
    python scripts/generate_validation_pages.py --limit 100
    python scripts/generate_validation_pages.py --proxy-url URL --dispatch-token TOKEN
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd
from jinja2 import Environment, FileSystemLoader

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
DOCS_VALIDATE_DIR = PROJECT_ROOT / "docs" / "validate"
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

PARQUET_PATH = OUTPUTS_DIR / "literature_review_enriched.parquet"
EVIDENCE_PATH = OUTPUTS_DIR / "schema_extraction_evidence.csv"
PAPER_AUTHORS_PATH = OUTPUTS_DIR / "openalex_paper_authors.csv"
UNIQUE_AUTHORS_PATH = OUTPUTS_DIR / "openalex_unique_authors.csv"
ALTMETRIC_PATH = OUTPUTS_DIR / "altmetric_scores.csv"

# Prefixes that use the evidence/columns format
TIER1_PREFIXES = ["b_", "d_", "eco_", "pr_", "imp_", "gear_"]
# Prefixes that use triggered+all_options format
TIER2_PREFIXES = ["sp_", "a_"]
# ob_ uses columns format but without evidence
OB_PREFIX = "ob_"

DEFAULT_BASE_URL = "/elasmo_analyses/"
DEFAULT_VALIDATE_URL = "/elasmo_analyses/validate/"

OPENALEX_URL_PREFIX = "https://openalex.org/"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def strip_openalex_prefix(full_id: str) -> str:
    """Strip URL prefix, return bare ID like A5086753224."""
    if isinstance(full_id, str) and full_id.startswith(OPENALEX_URL_PREFIX):
        return full_id[len(OPENALEX_URL_PREFIX):]
    return str(full_id) if pd.notna(full_id) else ""


def lit_id_str(val) -> str:
    """Convert literature_id to clean string, handling float64 NaN."""
    if pd.isna(val):
        return ""
    try:
        return str(int(float(val)))
    except (ValueError, TypeError):
        return str(val)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_parquet_metadata(all_lit_ids: set[str]) -> pd.DataFrame:
    """
    Load only the needed metadata + binary columns from parquet.
    Returns a DataFrame indexed by literature_id (string).
    """
    print("Loading parquet metadata columns…")
    meta_cols = [
        "literature_id", "year", "title", "authors", "doi",
        "journal", "study_type", "country", "superregion", "epoch",
        "depth_range", "depth_min_m", "depth_max_m",
    ]
    # Also load binary columns for all prefixes
    pq_all = pd.read_parquet(PARQUET_PATH)
    all_cols = pq_all.columns.tolist()

    binary_cols = [
        c for c in all_cols
        if any(c.startswith(p) for p in TIER1_PREFIXES + TIER2_PREFIXES + [OB_PREFIX])
    ]
    keep_cols = [c for c in meta_cols if c in all_cols] + binary_cols

    df = pq_all[keep_cols].copy()
    df["literature_id"] = df["literature_id"].apply(lit_id_str)
    df = df[df["literature_id"].isin(all_lit_ids)]
    df = df.set_index("literature_id")
    print(f"  {len(df)} papers loaded from parquet (filtered to authors' papers).")
    return df


def load_evidence(all_lit_ids: set[str]) -> dict[str, dict[str, list[dict]]]:
    """
    Load schema_extraction_evidence.csv and build a nested dict:
      evidence[lit_id_str][column_name] -> list of evidence dicts
    Only TIER1 columns are in this file.
    """
    print("Loading evidence CSV…")
    ev = pd.read_csv(
        EVIDENCE_PATH,
        usecols=["literature_id", "column", "binary", "total_freq", "threshold",
                 "matched_terms", "section", "context"],
        dtype={"literature_id": str},
    )
    # Normalise literature_id: strip any .0 suffix
    ev["literature_id"] = ev["literature_id"].apply(lit_id_str)
    ev = ev[ev["literature_id"].isin(all_lit_ids)]

    evidence: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for row in ev.itertuples(index=False):
        ev_entry = {
            "matched_terms": str(row.matched_terms) if pd.notna(row.matched_terms) else "",
            "section": str(row.section) if pd.notna(row.section) else "",
            "total_freq": str(row.total_freq),
            "threshold": str(row.threshold),
            "context": str(row.context) if pd.notna(row.context) else "",
        }
        evidence[row.literature_id][row.column].append(ev_entry)

    print(f"  Evidence loaded for {len(evidence)} papers.")
    return evidence


def load_altmetric(all_lit_ids: set[str]) -> dict[str, str]:
    """Return mapping literature_id_str -> alt_score string."""
    print("Loading altmetric scores…")
    alt = pd.read_csv(ALTMETRIC_PATH, usecols=["literature_id", "alt_score"])
    alt["literature_id"] = alt["literature_id"].apply(lit_id_str)
    result = {}
    for _, row in alt.iterrows():
        lid = row["literature_id"]
        if lid in all_lit_ids:
            result[lid] = str(row["alt_score"]) if pd.notna(row["alt_score"]) else ""
    print(f"  Altmetric scores loaded for {len(result)} papers.")
    return result


def load_authors() -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load paper_authors and unique_authors CSVs.
    Strips OpenAlex URL prefix from openalex_author_id in both frames.
    Returns (paper_authors_df, unique_authors_df).
    """
    print("Loading author CSVs…")
    paper_auth = pd.read_csv(PAPER_AUTHORS_PATH)
    paper_auth["openalex_author_id"] = paper_auth["openalex_author_id"].apply(strip_openalex_prefix)
    paper_auth["literature_id"] = paper_auth["literature_id"].apply(lit_id_str)

    unique_auth = pd.read_csv(UNIQUE_AUTHORS_PATH)
    unique_auth["openalex_author_id"] = unique_auth["openalex_author_id"].apply(strip_openalex_prefix)

    print(f"  {len(paper_auth)} paper-author rows, {len(unique_auth)} unique authors.")
    return paper_auth, unique_auth


# ---------------------------------------------------------------------------
# Author merge logic
# ---------------------------------------------------------------------------

def build_merge_groups(unique_auth: pd.DataFrame) -> dict[str, str]:
    """
    Group authors by (lower display_name, lower most_common_institution).
    Within each group the primary is the one with highest paper_count;
    all others are secondaries.

    Returns a dict: secondary_id -> primary_id
    """
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for _, row in unique_auth.iterrows():
        name_key = (row["display_name"] or "").strip().lower()
        inst_key = (row["most_common_institution"] or "").strip().lower() if pd.notna(row["most_common_institution"]) else ""
        oa_id = row["openalex_author_id"]
        paper_count = int(row["paper_count"]) if pd.notna(row["paper_count"]) else 0
        groups[(name_key, inst_key)].append({"id": oa_id, "paper_count": paper_count})

    secondary_to_primary: dict[str, str] = {}
    for members in groups.values():
        if len(members) < 2:
            continue
        # Primary = highest paper_count
        members.sort(key=lambda x: x["paper_count"], reverse=True)
        primary_id = members[0]["id"]
        for m in members[1:]:
            secondary_to_primary[m["id"]] = primary_id

    return secondary_to_primary


# ---------------------------------------------------------------------------
# PAGE_DATA builder
# ---------------------------------------------------------------------------

def build_page_data(
    openalex_id: str,
    author_row: pd.Series,
    paper_lit_ids: list[str],
    pq: pd.DataFrame,
    evidence: dict[str, dict[str, list[dict]]],
    altmetric: dict[str, str],
    merged_ids: list[str],
    all_prefix_cols: dict[str, list[str]],
    today_str: str,
) -> dict:
    """Build the PAGE_DATA dict for a single author."""
    institution = (
        str(author_row["most_common_institution"])
        if pd.notna(author_row.get("most_common_institution", None))
        else ""
    )

    papers: dict[str, dict] = {}

    for lid in paper_lit_ids:
        if lid not in pq.index:
            continue
        row = pq.loc[lid]

        # --- meta ---
        year_val = row.get("year")
        year_int = int(year_val) if pd.notna(year_val) else None

        meta = {
            "year": year_int,
            "title": str(row.get("title", "")) if pd.notna(row.get("title")) else "",
            "authors": str(row.get("authors", "")) if pd.notna(row.get("authors")) else "",
            "journal": str(row.get("journal", "")) if pd.notna(row.get("journal")) else "",
            "doi": str(row.get("doi", "")) if pd.notna(row.get("doi")) else "",
            "study_type": str(row.get("study_type", "")) if pd.notna(row.get("study_type")) else "",
            "country": str(row.get("country", "")) if pd.notna(row.get("country")) else "",
            "superregion": str(row.get("superregion", "")) if pd.notna(row.get("superregion")) else "",
            "epoch": str(row.get("epoch", "")) if pd.notna(row.get("epoch")) else "",
            "alt_score": altmetric.get(lid, ""),
            "literature_id": lid,
        }

        # --- categories ---
        categories: dict = {}
        paper_evidence = evidence.get(lid, {})

        # Tier 1: columns format with evidence
        for prefix in TIER1_PREFIXES:
            cols_for_prefix = all_prefix_cols.get(prefix, [])
            col_list = []
            for col in cols_for_prefix:
                col_val = row.get(col)
                triggered = bool(col_val) if pd.notna(col_val) else False
                col_evidence = paper_evidence.get(col, [])
                col_list.append({
                    "name": col,
                    "triggered": triggered,
                    "evidence": col_evidence,
                })
            categories[prefix] = {"columns": col_list}

        # ob_: columns format without evidence
        ob_cols = all_prefix_cols.get(OB_PREFIX, [])
        ob_list = []
        for col in ob_cols:
            col_val = row.get(col)
            triggered = bool(col_val) if pd.notna(col_val) else False
            ob_list.append({
                "name": col,
                "triggered": triggered,
                "evidence": [],
            })
        categories[OB_PREFIX] = {"columns": ob_list}

        # Tier 2: triggered only (all_options in shared file, not per-paper)
        for prefix in TIER2_PREFIXES:
            all_options = all_prefix_cols.get(prefix, [])
            triggered_cols = [
                col for col in all_options
                if pd.notna(row.get(col)) and bool(row.get(col))
            ]
            categories[prefix] = {
                "triggered": triggered_cols,
            }

        # depth_
        depth_range = row.get("depth_range")
        depth_min = row.get("depth_min_m")
        depth_max = row.get("depth_max_m")
        categories["depth_"] = {
            "depth_range": str(depth_range) if pd.notna(depth_range) else "",
            "depth_min_m": float(depth_min) if pd.notna(depth_min) else None,
            "depth_max_m": float(depth_max) if pd.notna(depth_max) else None,
        }

        papers[lid] = {"meta": meta, "categories": categories}

    return {
        "openalex_id": openalex_id,
        "author_name": str(author_row["display_name"]) if pd.notna(author_row.get("display_name")) else "",
        "institution": institution,
        "page_version": today_str,
        "merged_ids": merged_ids,
        "papers": papers,
    }


# ---------------------------------------------------------------------------
# Main generation
# ---------------------------------------------------------------------------

def generate_pages(
    target_author_id: str | None = None,
    limit: int | None = None,
    proxy_url: str = "",
    dispatch_token: str = "",
) -> None:
    today_str = pd.Timestamp.today().strftime("%Y-%m-%d")

    # --- Load authors ---
    paper_auth, unique_auth = load_authors()

    # Build merge groups
    secondary_to_primary = build_merge_groups(unique_auth)

    # Build primary -> list of secondaries
    primary_to_secondaries: dict[str, list[str]] = defaultdict(list)
    for sec, pri in secondary_to_primary.items():
        primary_to_secondaries[pri].append(sec)

    # Index unique_auth by openalex_id
    unique_auth_idx = unique_auth.set_index("openalex_author_id")

    # Build: primary_id -> set of literature_ids (all papers, including merged)
    primary_to_lids: dict[str, set[str]] = defaultdict(set)
    for _, row in paper_auth.iterrows():
        oa_id = row["openalex_author_id"]
        lid = row["literature_id"]
        if not lid or not oa_id:
            continue
        # Resolve to primary
        primary = secondary_to_primary.get(oa_id, oa_id)
        primary_to_lids[primary].add(lid)

    # Collect all unique primary IDs
    all_primary_ids = [oa_id for oa_id in unique_auth_idx.index if oa_id not in secondary_to_primary]

    # Filter to target author if specified
    if target_author_id:
        # Normalise: strip prefix if full URL given
        target_author_id = strip_openalex_prefix(target_author_id)
        # If this is a secondary, redirect to primary
        if target_author_id in secondary_to_primary:
            print(f"Note: {target_author_id} is a secondary ID, primary is {secondary_to_primary[target_author_id]}")
            target_author_id = secondary_to_primary[target_author_id]
        all_primary_ids = [target_author_id]

    if limit is not None:
        all_primary_ids = all_primary_ids[:limit]

    # Gather all literature IDs we need
    all_lit_ids: set[str] = set()
    for primary_id in all_primary_ids:
        all_lit_ids.update(primary_to_lids.get(primary_id, set()))
    # Also include papers for secondaries of these primaries
    for primary_id in all_primary_ids:
        for sec_id in primary_to_secondaries.get(primary_id, []):
            all_lit_ids.update(primary_to_lids.get(sec_id, set()))

    print(f"Processing {len(all_primary_ids)} primary authors, {len(all_lit_ids)} unique papers.")

    # --- Load parquet (filtered) ---
    pq = load_parquet_metadata(all_lit_ids)

    # Build prefix -> sorted column list (from parquet columns)
    all_prefix_cols: dict[str, list[str]] = {}
    for prefix in TIER1_PREFIXES + TIER2_PREFIXES + [OB_PREFIX]:
        all_prefix_cols[prefix] = sorted([c for c in pq.columns if c.startswith(prefix)])

    # --- Load evidence ---
    evidence = load_evidence(all_lit_ids)

    # --- Load altmetric ---
    altmetric = load_altmetric(all_lit_ids)

    # --- Set up Jinja2 (autoescape=False: page_data_json is raw JSON) ---
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=False,
    )
    tmpl_page = env.get_template("validate_page.html.j2")
    tmpl_index = env.get_template("validate_index.html.j2")
    tmpl_404 = env.get_template("validate_404.html.j2")
    tmpl_redirect = env.get_template("validate_redirect.html.j2")

    DOCS_VALIDATE_DIR.mkdir(parents=True, exist_ok=True)

    base_url = DEFAULT_VALIDATE_URL
    assets_prefix = DEFAULT_BASE_URL

    generated_primary_ids: list[str] = []
    secondary_redirect_map: dict[str, str] = {}  # secondary_id -> primary_id

    print("Generating author pages…")
    for i, primary_id in enumerate(all_primary_ids):
        if i > 0 and i % 1000 == 0:
            print(f"  … {i}/{len(all_primary_ids)} authors done")

        if primary_id not in unique_auth_idx.index:
            print(f"  Warning: {primary_id} not found in unique_authors, skipping.")
            continue

        author_row = unique_auth_idx.loc[primary_id]

        # Gather all lit IDs for this primary (from all merged IDs too)
        merged_ids = sorted(primary_to_secondaries.get(primary_id, []))
        all_ids_for_author = {primary_id} | set(merged_ids)
        paper_lit_ids: list[str] = sorted(
            {
                lid
                for oa_id in all_ids_for_author
                for lid in primary_to_lids.get(oa_id, set())
                if lid  # skip empty strings
            },
            key=lambda x: int(x) if x.isdigit() else 0,
        )

        if not paper_lit_ids:
            continue

        # Build PAGE_DATA
        page_data = build_page_data(
            openalex_id=primary_id,
            author_row=author_row,
            paper_lit_ids=paper_lit_ids,
            pq=pq,
            evidence=evidence,
            altmetric=altmetric,
            merged_ids=merged_ids,
            all_prefix_cols=all_prefix_cols,
            today_str=today_str,
        )

        author_name = page_data["author_name"]
        institution = page_data["institution"]
        paper_count = len(page_data["papers"])

        page_data_json = json.dumps(page_data, ensure_ascii=False)

        html = tmpl_page.render(
            author_name=author_name,
            institution=institution,
            openalex_id=primary_id,
            paper_count=paper_count,
            merged_ids=merged_ids,
            page_data_json=page_data_json,
            proxy_url=proxy_url,
            dispatch_token=dispatch_token,
        )

        out_path = DOCS_VALIDATE_DIR / f"{primary_id}.html"
        out_path.write_text(html, encoding="utf-8")
        generated_primary_ids.append(primary_id)

        # Queue redirect pages for secondaries
        for sec_id in merged_ids:
            secondary_redirect_map[sec_id] = primary_id

    # --- Redirect pages ---
    print(f"Generating {len(secondary_redirect_map)} redirect pages…")
    for sec_id, pri_id in secondary_redirect_map.items():
        primary_url = f"{base_url}{pri_id}.html"
        html = tmpl_redirect.render(primary_url=primary_url, primary_id=pri_id)
        out_path = DOCS_VALIDATE_DIR / f"{sec_id}.html"
        out_path.write_text(html, encoding="utf-8")

    # --- Index page ---
    print("Generating index page…")
    known_ids_json = json.dumps(generated_primary_ids, ensure_ascii=False)
    index_html = tmpl_index.render(
        known_ids_json=known_ids_json,
        base_url=base_url,
    )
    (DOCS_VALIDATE_DIR / "index.html").write_text(index_html, encoding="utf-8")

    # --- Shared options file (sp_ and a_ column lists, loaded once by JS) ---
    print("Generating shared options JSON…")
    shared_options = {}
    for prefix in TIER2_PREFIXES:
        shared_options[prefix] = all_prefix_cols.get(prefix, [])
    (DOCS_VALIDATE_DIR / "assets" / "options.json").write_text(
        json.dumps(shared_options, ensure_ascii=False), encoding="utf-8"
    )

    # --- 404 page ---
    print("Generating 404 page…")
    html_404 = tmpl_404.render(
        assets_prefix=assets_prefix,
        base_url=base_url,
    )
    (PROJECT_ROOT / "docs" / "404.html").write_text(html_404, encoding="utf-8")

    print(
        f"\nDone. Generated {len(generated_primary_ids)} author pages, "
        f"{len(secondary_redirect_map)} redirects, index, and 404."
    )
    print(f"Output directory: {DOCS_VALIDATE_DIR}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate elasmobranch validation HTML pages.")
    parser.add_argument("--author", metavar="ID", help="Generate page for a single OpenAlex author ID")
    parser.add_argument("--limit", type=int, metavar="N", help="Process only the first N primary authors")
    parser.add_argument("--proxy-url", default="", metavar="URL", help="Proxy URL for submission")
    parser.add_argument("--dispatch-token", default="", metavar="TOKEN", help="GitHub dispatch token for submission")
    args = parser.parse_args()

    generate_pages(
        target_author_id=args.author,
        limit=args.limit,
        proxy_url=args.proxy_url,
        dispatch_token=args.dispatch_token,
    )


if __name__ == "__main__":
    main()
