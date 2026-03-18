#!/usr/bin/env python3
"""Generate per-coauthor evidence XLSX from schema extraction results.

Creates an Excel workbook with:
- Summary tab (coauthor name, paper count, evidence row count)
- One tab per team member with their papers' evidence rows
- Acronym Matches tab for validating case-sensitive acronym detection

Usage:
    python scripts/generate_coauthor_evidence_xlsx.py
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils.dataframe import dataframe_to_rows

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE = Path("/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel")
EVIDENCE_CSV = BASE / "outputs" / "schema_extraction_evidence.csv"
AUTHORS_CSV = BASE / "outputs" / "openalex_paper_authors.csv"
PARQUET = BASE / "outputs" / "literature_review_enriched.parquet"
OUTPUT = BASE / "outputs" / "schema_extraction_evidence_by_coauthor.xlsx"

# ---------------------------------------------------------------------------
# Team members: display name -> list of surname variants (lowercase, normalised)
# ---------------------------------------------------------------------------
TEAM: dict[str, list[str]] = {
    "Simon Dedman": ["dedman"],
    "David Ruiz-Garcia": ["ruiz-garcia", "ruiz-garcía"],
    "Guuske Tiktak": ["tiktak"],
    "Elena Fernandez-Corredor": ["fernandez-corredor", "fernández-corredor"],
    "David Shiffman": ["shiffman"],
}

# Acronyms to check in matched_terms
ACRONYMS = [
    "RAMP", "CPUE", "MPA", "IUU", "OMZ", "PCB", "PFAS", "ALAN", "EMF",
    "BRD", "TED", "EPM", "PRM", "ALDFG", "PAL", "DOA", "AVM", "SSB",
    "WTP", "SPR", "MSY", "CITES", "IUCN", "SNP", "BRUVs", "eDNA",
    "UAV", "ROV",
]

# Evidence tab columns (order matters)
EVIDENCE_COLS = [
    "literature_id", "year", "authors", "journal", "title",
    "column", "binary", "total_freq", "raw_freq", "section",
    "term_count", "threshold", "matched_terms", "matched_anchors", "context",
]
REVIEWER_COLS = ["Notes", "Comments"]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
DASH_CHARS = "\u2010\u2011\u2012\u2013\u2014\u2212"
_dash_table = str.maketrans({ch: "-" for ch in DASH_CHARS})

# Regex to strip illegal XML characters that openpyxl rejects
_ILLEGAL_XML_RE = re.compile(
    r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]"
)


def normalise_name(s: str | float) -> str:
    """Lowercase and replace all Unicode dashes with ASCII hyphen."""
    if pd.isna(s):
        return ""
    return str(s).lower().translate(_dash_table)


def lit_id_to_int(val: str | float) -> int:
    """Convert literature_id like '31532.0' to int 31532."""
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return -1


def style_header(ws: any) -> None:
    """Apply bold + fill to header row and freeze panes."""
    header_font = Font(bold=True)
    header_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    for cell in ws[1]:
        cell.font = header_font
        cell.fill = header_fill
    ws.freeze_panes = "A2"


def auto_width(ws: any, max_width: int = 60) -> None:
    """Set column widths based on header length (capped)."""
    for col in ws.columns:
        header_val = str(col[0].value) if col[0].value else ""
        width = min(len(header_val) + 4, max_width)
        ws.column_dimensions[col[0].column_letter].width = width


def sanitise_value(val: any) -> any:
    """Remove illegal XML characters from string values."""
    if isinstance(val, str):
        return _ILLEGAL_XML_RE.sub("", val)
    return val


def write_dataframe(ws: any, df: pd.DataFrame) -> None:
    """Write a DataFrame to a worksheet including headers."""
    for r_idx, row in enumerate(dataframe_to_rows(df, index=False, header=True), start=1):
        for c_idx, val in enumerate(row, start=1):
            val = sanitise_value(val)
            cell = ws.cell(row=r_idx, column=c_idx, value=val)
            if r_idx > 1 and isinstance(val, str) and len(val) > 80:
                cell.alignment = Alignment(wrap_text=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    print("Loading data...")

    # Load evidence
    evidence = pd.read_csv(EVIDENCE_CSV, dtype={"literature_id": str})
    evidence["lit_id_int"] = evidence["literature_id"].apply(lit_id_to_int)
    print(f"  Evidence: {len(evidence):,} rows")

    # Load author-paper mapping
    authors = pd.read_csv(
        AUTHORS_CSV,
        usecols=["literature_id", "last_name"],
        dtype={"literature_id": str},
    )
    authors["lit_id_int"] = authors["literature_id"].apply(lit_id_to_int)
    authors["last_name_norm"] = authors["last_name"].apply(normalise_name)

    # Load paper metadata from parquet
    meta = pd.read_parquet(PARQUET, columns=["literature_id", "year", "authors", "journal", "title"])
    meta["lit_id_int"] = meta["literature_id"].apply(lit_id_to_int)
    # Deduplicate (should be unique but just in case)
    meta = meta.drop_duplicates(subset="lit_id_int")
    print(f"  Papers (parquet): {len(meta):,}")
    print(f"  Author-paper rows: {len(authors):,}")

    # -----------------------------------------------------------------------
    # Build per-coauthor paper sets
    # -----------------------------------------------------------------------
    coauthor_paper_ids: dict[str, set[int]] = {}
    for name, variants in TEAM.items():
        norm_variants = [normalise_name(v) for v in variants]
        mask = authors["last_name_norm"].isin(norm_variants)
        paper_ids = set(authors.loc[mask, "lit_id_int"].unique())
        coauthor_paper_ids[name] = paper_ids
        print(f"  {name}: {len(paper_ids)} papers in OpenAlex")

    # -----------------------------------------------------------------------
    # Merge evidence with metadata
    # -----------------------------------------------------------------------
    # Drop the title column from evidence (we'll use parquet's version)
    ev_cols_from_csv = [c for c in evidence.columns if c != "title"]
    merged = evidence[ev_cols_from_csv].merge(
        meta[["lit_id_int", "year", "authors", "journal", "title"]],
        on="lit_id_int",
        how="left",
    )
    # Use integer literature_id for display
    merged["literature_id"] = merged["lit_id_int"]

    # -----------------------------------------------------------------------
    # Create workbook
    # -----------------------------------------------------------------------
    wb = Workbook()

    # -- Summary tab --
    ws_summary = wb.active
    ws_summary.title = "Summary"
    ws_summary.append(["Coauthor", "Papers in DB", "Evidence rows", "Note"])

    summary_rows: list[tuple[str, int, int, str]] = []

    for name in TEAM:
        paper_ids = coauthor_paper_ids[name]
        if not paper_ids:
            summary_rows.append((name, 0, 0, "No OpenAlex author match"))
            continue

        # Filter evidence to this coauthor's papers
        mask = merged["lit_id_int"].isin(paper_ids)
        coauthor_ev = merged.loc[mask].copy()

        n_papers = coauthor_ev["lit_id_int"].nunique()
        n_rows = len(coauthor_ev)
        note = ""
        if n_rows > 50_000:
            note = f"Large tab: {n_rows:,} rows"

        summary_rows.append((name, n_papers, n_rows, note))

        # Build tab dataframe
        tab_df = coauthor_ev[EVIDENCE_COLS].copy()
        tab_df["Notes"] = ""
        tab_df["Comments"] = ""
        tab_df = tab_df.sort_values(["literature_id", "column"]).reset_index(drop=True)

        # Write tab
        ws = wb.create_sheet(title=name)
        write_dataframe(ws, tab_df)
        style_header(ws)
        auto_width(ws)
        print(f"  Wrote tab '{name}': {n_rows:,} rows, {n_papers} papers")

    # Write summary data
    for row in summary_rows:
        ws_summary.append(list(row))
    style_header(ws_summary)
    auto_width(ws_summary)

    # -----------------------------------------------------------------------
    # Acronym Matches tab
    # -----------------------------------------------------------------------
    print("Building Acronym Matches tab...")

    # Build regex pattern: match each acronym as a standalone token in matched_terms
    # matched_terms look like: "CPUE(3); marine(1); BRUVs(2)"
    # We want to find rows where any acronym appears before a "("
    acronym_pattern = re.compile(
        r"\b(" + "|".join(re.escape(a) for a in ACRONYMS) + r")\(",
    )

    def find_acronyms(text: str | float) -> str:
        """Return comma-separated list of acronyms found in matched_terms."""
        if pd.isna(text):
            return ""
        found = acronym_pattern.findall(str(text))
        return ", ".join(sorted(set(found))) if found else ""

    merged["acronym_matched"] = merged["matched_terms"].apply(find_acronyms)
    acr_mask = merged["acronym_matched"] != ""
    acr_df = merged.loc[acr_mask, EVIDENCE_COLS + ["acronym_matched"]].copy()
    acr_df = acr_df.sort_values(["literature_id", "column"]).reset_index(drop=True)

    n_acr = len(acr_df)
    print(f"  Acronym matches: {n_acr:,} evidence rows")

    ws_acr = wb.create_sheet(title="Acronym Matches")
    write_dataframe(ws_acr, acr_df)
    style_header(ws_acr)
    auto_width(ws_acr)

    # Add acronym summary to the Summary tab
    ws_summary.append([])
    ws_summary.append(["Acronym Matches", "", n_acr, "All evidence rows with acronym term matches"])

    # Breakdown per acronym
    ws_summary.append([])
    ws_summary.append(["Acronym", "Evidence rows"])
    acr_counts: dict[str, int] = {}
    for acrs in merged.loc[acr_mask, "acronym_matched"]:
        for a in acrs.split(", "):
            acr_counts[a] = acr_counts.get(a, 0) + 1
    for acr_name, count in sorted(acr_counts.items(), key=lambda x: -x[1]):
        ws_summary.append([acr_name, count])

    # -----------------------------------------------------------------------
    # Save
    # -----------------------------------------------------------------------
    wb.save(OUTPUT)
    print(f"\nSaved to: {OUTPUT}")
    print(f"  File size: {OUTPUT.stat().st_size / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    main()
