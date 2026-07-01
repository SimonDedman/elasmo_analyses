#!/usr/bin/env python3
"""
Species-normalised (per-species) family and genus figures for EEA 2025 Data Panel.

Companion to species_habitat_figures.py. Where that script plots *raw* paper
counts per family/genus (family_top20_barplot.png, genus_top20_barplot.png),
this one divides each family/genus paper total by the number of described
species in that family/genus (from the Sharkipedia taxonomy), giving a
research-effort-per-species ("balanced") view that corrects for the fact that
families/genera contain very different numbers of species.

Outputs (PNG 300 DPI + PDF):
  family_top20_per_species_barplot
  genus_top20_per_species_barplot

Reuses the exact data-loading, false-positive filtering, group colours and
style from species_habitat_figures.py so the two sets are directly comparable.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch

# ---------------------------------------------------------------------------
# Paths (identical to species_habitat_figures.py)
# ---------------------------------------------------------------------------
BASE = Path("/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel")
PARQUET = BASE / "outputs" / "literature_review_enriched.parquet"
TAXONOMY_CSV = BASE / "data" / "sharkipedia" / "Sharkipedia-Taxonomy-v1.0-22-01-25.csv"
FIG_DIR = BASE / "outputs" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Style constants (identical to species_habitat_figures.py)
# ---------------------------------------------------------------------------
GROUP_COLOURS: dict[str, str] = {
    "Sharks": "#2166ac",           # blue
    "Rays & Skates": "#e66101",    # coral/orange
    "Chimaeras": "#1b9e77",        # teal
    "Unknown": "#999999",
}

SUPERORDER_MAP: dict[str, str] = {
    "Galeomorphii": "Sharks",
    "Squalomorphii": "Sharks",
    "Batoidea": "Rays & Skates",
    "Holocephalimorpha": "Chimaeras",
}

# Same false-positive species filters as species_habitat_figures.py
FP_SPECIES: set[str] = {
    "sp_carcharhinus_albimarginatus",
    "sp_carcharhinus_porosus",
    "sp_atlantoraja_castelnaui",
    "sp_sympterygia_bonapartii",
    "sp_psammobatis_extenta",
    "sp_rioraja_agassizii",
    "sp_amblyraja_doellojuradoi",
    "sp_psammobatis_rudis",
    "sp_psammobatis_normani",
    "sp_dipturus_trachyderma",
    "sp_psammobatis_rutrum",
    "sp_bathyraja_schroederi",
    "sp_amblyraja_frerichsi",
    "sp_rajella_ravidula",
    "sp_dipturus_pullopunctatus",
    "sp_chimaera_cubana",
    "sp_chimaera_phantasma",
    "sp_sphyrna_corona",
}

# How many bars to show
TOP_N = 20


def italicise(name: str) -> str:
    """Wrap a family/genus name in matplotlib mathtext italics."""
    return f"$\\it{{{name.replace(' ', '\\ ')}}}$"


def save(fig: mpl.figure.Figure, name: str) -> None:
    """Save figure as PNG and PDF with tight layout."""
    for ext in ("png", "pdf"):
        path = FIG_DIR / f"{name}.{ext}"
        fig.savefig(path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  Saved {name}")


def col_to_sci(col: str) -> str:
    """Convert sp_genus_species to 'Genus species'."""
    parts = col.replace("sp_", "", 1).split("_")
    return " ".join(p.capitalize() if i == 0 else p for i, p in enumerate(parts))


# ===================================================================
# Load data (mirrors species_habitat_figures.py)
# ===================================================================
print("Loading data...")
df = pd.read_parquet(PARQUET)
tax = pd.read_csv(TAXONOMY_CSV)

tax["group"] = tax["Superorder"].map(SUPERORDER_MAP).fillna("Unknown")
tax["genus"] = tax["Sharkipedia Scientific name"].str.strip().str.split().str[0]

# Species-name -> taxonomy info
tax_lookup: dict[str, dict[str, str]] = {}
for _, row in tax.iterrows():
    sci = row["Sharkipedia Scientific name"].strip()
    tax_lookup[sci] = {
        "family": row["Family"],
        "order": row["Order"],
        "superorder": row["Superorder"],
        "group": row["group"],
    }

# Genus-level fallback lookup
genus_lookup: dict[str, dict[str, str]] = {}
for sci, info in tax_lookup.items():
    genus = sci.split()[0] if " " in sci else sci
    genus_lookup.setdefault(genus, info)

# ----- Species richness denominators (from full taxonomy) -----
# Number of described species per family / per genus.
species_per_family = tax.groupby("Family").size()
species_per_genus = tax.groupby("genus").size()
# group label per family / genus (for bar colour)
family_group = tax.groupby("Family")["group"].first()
genus_group = tax.groupby("genus")["group"].first()

# ===================================================================
# Paper counts per species (number of papers where score > 0)
# ===================================================================
sp_cols = [c for c in df.columns if c.startswith("sp_") and c not in FP_SPECIES]
print(f"  {len(sp_cols)} species columns (after FP filter)")

species_data: list[dict[str, Any]] = []
for c in sp_cols:
    count = int((df[c] > 0).sum())
    if count <= 0:
        continue
    sci = col_to_sci(c)
    info = tax_lookup.get(sci, {})
    genus = sci.split()[0]
    if not info:
        info = genus_lookup.get(genus, {})
    species_data.append({
        "scientific_name": sci,
        "genus": genus,
        "family": info.get("family", "Unknown"),
        "group": info.get("group", "Unknown"),
        "paper_count": count,
    })

sp_df = pd.DataFrame(species_data)
print(f"  {len(sp_df)} species with at least 1 paper")


def per_species_chart(level: str, richness: pd.Series, group_map: pd.Series,
                      title: str, outfile: str, italic_labels: bool) -> None:
    """Build a top-N papers-per-species horizontal bar chart for family or genus."""
    # Total papers per family/genus (only counting studied species)
    papers = sp_df.groupby(level)["paper_count"].sum()
    papers = papers.drop(labels=["Unknown"], errors="ignore")

    agg = pd.DataFrame({"papers": papers})
    agg["n_species"] = richness.reindex(agg.index)
    # Keep only taxa we have a species count for
    agg = agg.dropna(subset=["n_species"])
    agg["n_species"] = agg["n_species"].astype(int)
    agg["per_species"] = agg["papers"] / agg["n_species"]
    agg["group"] = group_map.reindex(agg.index).fillna("Unknown")

    agg = agg.sort_values("per_species", ascending=False).head(TOP_N)
    agg = agg.sort_values("per_species", ascending=True)  # for horizontal bar

    fig, ax = plt.subplots(figsize=(12, 8))
    labels = [italicise(n) for n in agg.index] if italic_labels else list(agg.index)
    ax.barh(
        range(len(agg)),
        agg["per_species"],
        color=agg["group"].map(GROUP_COLOURS),
        edgecolor="white",
    )
    ax.set_yticks(range(len(agg)))
    ax.set_yticklabels(labels, fontsize=9)

    xmax = agg["per_species"].max()
    for i, (_, row) in enumerate(agg.iterrows()):
        ax.text(
            row["per_species"] + xmax * 0.01, i,
            f"{row['per_species']:,.0f}  ({int(row['papers']):,}/{row['n_species']})",
            va="center", fontsize=8,
        )

    ax.set_xlabel("Papers per species (paper total ÷ number of species)", fontsize=12)
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.set_xlim(0, xmax * 1.18)

    legend_handles = [Patch(facecolor=c, label=g) for g, c in GROUP_COLOURS.items() if g != "Unknown"]
    ax.legend(handles=legend_handles, loc="lower right", fontsize=10)
    save(fig, outfile)


# ===================================================================
# Figure A: Top 20 families by papers-per-species
# ===================================================================
print("\nFigure A: Family top 20 per-species barplot...")
per_species_chart(
    level="family",
    richness=species_per_family,
    group_map=family_group,
    title="Top 20 families by research effort per species\n(papers ÷ number of species in family)",
    outfile="family_top20_per_species_barplot",
    italic_labels=False,
)

# ===================================================================
# Figure B: Top 20 genera by papers-per-species
# ===================================================================
print("Figure B: Genus top 20 per-species barplot...")
per_species_chart(
    level="genus",
    richness=species_per_genus,
    group_map=genus_group,
    title="Top 20 genera by research effort per species\n(papers ÷ number of species in genus)",
    outfile="genus_top20_per_species_barplot",
    italic_labels=True,
)

print("\nAll figures saved to:", FIG_DIR)
print("Done.")
