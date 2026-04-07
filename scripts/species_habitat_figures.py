#!/usr/bin/env python3
"""
Species, family, genus, and habitat analysis figures for EEA 2025 Data Panel.

Generates 10 publication-quality figures saved as both PNG (300 DPI) and PDF.
"""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any

import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.colors import to_rgba

# Optional: squarify for treemap
try:
    import squarify
except ImportError:
    squarify = None
    warnings.warn("squarify not installed; treemap will be skipped. Install with: pip install squarify")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE = Path("/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel")
PARQUET = BASE / "outputs" / "literature_review_enriched.parquet"
TAXONOMY_CSV = BASE / "data" / "sharkipedia" / "Sharkipedia-Taxonomy-v1.0-22-01-25.csv"
FIG_DIR = BASE / "outputs" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Style constants
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

# Ecosystem columns to use (excluding eco_marine, guesses)
ECO_EXCLUDE = {"eco_marine", "eco_1_guess", "eco_2_guess", "eco_3_guess"}

# ---------------------------------------------------------------------------
# False-positive species filters
# ---------------------------------------------------------------------------
# Species with counts >5000 are extraction artefacts (common word fragments)
# The Argentinian skate cluster (5600-5700) is also a batch FP
# Rajella ravidula / Dipturus pullopunctatus (~2082) have 99.6% overlap = FP cluster
# Chimaera cubana / phantasma have 100% overlap with Hydrolagus novaezealandiae
# Sphyrna corona (746) contains "corona" — common word fragment
FP_SPECIES: set[str] = {
    "sp_carcharhinus_albimarginatus",  # ~15596, "margin" fragment
    "sp_carcharhinus_porosus",         # ~15569, "poros" fragment
    # Argentinian skate cluster (~5630-5692)
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
    # Rajella / Dipturus FP cluster (~2082)
    "sp_rajella_ravidula",
    "sp_dipturus_pullopunctatus",
    # Chimaera FP cluster (exact overlap with Hydrolagus)
    "sp_chimaera_cubana",
    "sp_chimaera_phantasma",
    # Common word fragment
    "sp_sphyrna_corona",
}


def adaptive_text_colour(bg_value: float, vmin: float, vmax: float) -> str:
    """Return 'white' for dark cells, '#333333' for light cells."""
    if np.isnan(bg_value):
        return "#333333"
    normalised = (bg_value - vmin) / (vmax - vmin + 1e-9)
    return "white" if normalised > 0.5 else "#333333"


def italicise(name: str) -> str:
    """Wrap a species/genus name in matplotlib mathtext italics."""
    return f"$\\it{{{name.replace(' ', '\\ ')}}}$"


def save(fig: mpl.figure.Figure, name: str) -> None:
    """Save figure as PNG and PDF with tight layout."""
    for ext in ("png", "pdf"):
        path = FIG_DIR / f"{name}.{ext}"
        fig.savefig(path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  Saved {name}")


# ===================================================================
# Load data
# ===================================================================
print("Loading data...")
df = pd.read_parquet(PARQUET)
tax = pd.read_csv(TAXONOMY_CSV)

# Build taxonomy lookup: scientific name -> (Family, Superorder, group)
tax["group"] = tax["Superorder"].map(SUPERORDER_MAP).fillna("Unknown")
tax_lookup: dict[str, dict[str, str]] = {}
for _, row in tax.iterrows():
    sci = row["Sharkipedia Scientific name"].strip()
    tax_lookup[sci] = {
        "family": row["Family"],
        "order": row["Order"],
        "superorder": row["Superorder"],
        "group": row["group"],
    }

# Also build genus-level lookup
genus_lookup: dict[str, dict[str, str]] = {}
for sci, info in tax_lookup.items():
    genus = sci.split()[0] if " " in sci else sci
    if genus not in genus_lookup:
        genus_lookup[genus] = info  # first match wins for genus-level

# Extract species columns and compute paper counts
sp_cols = [c for c in df.columns if c.startswith("sp_") and c not in FP_SPECIES]
print(f"  {len(sp_cols)} species columns (after FP filter)")

# Paper count per species (number of papers where score > 0)
species_counts: dict[str, int] = {}
for c in sp_cols:
    count = int((df[c] > 0).sum())
    if count > 0:
        species_counts[c] = count

print(f"  {len(species_counts)} species with at least 1 paper")

# Map column name to scientific name
def col_to_sci(col: str) -> str:
    """Convert sp_genus_species to 'Genus species'."""
    parts = col.replace("sp_", "", 1).split("_")
    return " ".join(p.capitalize() if i == 0 else p for i, p in enumerate(parts))


# Build master species dataframe
species_data: list[dict[str, Any]] = []
for col, count in species_counts.items():
    sci = col_to_sci(col)
    info = tax_lookup.get(sci, {})
    genus = sci.split()[0]
    if not info:
        info = genus_lookup.get(genus, {})
    species_data.append({
        "column": col,
        "scientific_name": sci,
        "genus": genus,
        "family": info.get("family", "Unknown"),
        "order": info.get("order", "Unknown"),
        "superorder": info.get("superorder", "Unknown"),
        "group": info.get("group", "Unknown"),
        "paper_count": count,
    })

sp_df = pd.DataFrame(species_data).sort_values("paper_count", ascending=False).reset_index(drop=True)
print(f"  Taxonomy matched: {(sp_df['group'] != 'Unknown').sum()}/{len(sp_df)}")

# Ecosystem columns
eco_cols = [c for c in df.columns if c.startswith("eco_") and c not in ECO_EXCLUDE]
print(f"  {len(eco_cols)} ecosystem columns")

# ===================================================================
# Figure 1: Top 30 species bar chart
# ===================================================================
print("\nFigure 1: Top 30 species barplot...")
top30 = sp_df.head(30).copy()
top30["label"] = top30["scientific_name"].apply(italicise)
top30["colour"] = top30["group"].map(GROUP_COLOURS)

fig, ax = plt.subplots(figsize=(12, 10))
bars = ax.barh(
    range(len(top30)),
    top30["paper_count"],
    color=top30["colour"],
    edgecolor="white",
    linewidth=0.5,
)
ax.set_yticks(range(len(top30)))
ax.set_yticklabels(top30["label"], fontsize=9)
ax.invert_yaxis()
ax.set_xlabel("Number of papers", fontsize=12)
ax.set_title("Top 30 most-studied elasmobranch species", fontsize=14, fontweight="bold")

# Paper count labels
for i, (_, row) in enumerate(top30.iterrows()):
    ax.text(row["paper_count"] + 10, i, f"{row['paper_count']:,}", va="center", fontsize=8)

# Legend
from matplotlib.patches import Patch
legend_handles = [Patch(facecolor=c, label=g) for g, c in GROUP_COLOURS.items() if g != "Unknown"]
ax.legend(handles=legend_handles, loc="lower right", fontsize=10)
ax.set_xlim(0, top30["paper_count"].max() * 1.12)
save(fig, "species_top30_barplot")


# ===================================================================
# Figure 2: Family treemap
# ===================================================================
if squarify is not None:
    print("Figure 2: Family treemap...")
    family_counts = sp_df.groupby(["family", "group"])["paper_count"].sum().reset_index()
    family_counts = family_counts.sort_values("paper_count", ascending=False)
    # Keep families with meaningful counts
    family_counts = family_counts[family_counts["paper_count"] > 0]

    fig, ax = plt.subplots(figsize=(14, 10))
    colours = family_counts["group"].map(GROUP_COLOURS)
    sizes = family_counts["paper_count"]
    labels = []
    for _, row in family_counts.iterrows():
        if row["paper_count"] >= sizes.quantile(0.7):
            labels.append(f"{row['family']}\n({row['paper_count']:,})")
        else:
            labels.append("")

    squarify.plot(
        sizes=sizes,
        label=labels,
        color=colours,
        alpha=0.85,
        edgecolor="white",
        linewidth=2,
        text_kwargs={"fontsize": 8, "fontweight": "bold"},
        ax=ax,
    )
    ax.set_title("Papers per family (size = paper count)", fontsize=14, fontweight="bold")
    ax.axis("off")
    legend_handles = [Patch(facecolor=c, label=g) for g, c in GROUP_COLOURS.items() if g != "Unknown"]
    ax.legend(handles=legend_handles, loc="lower right", fontsize=10)
    save(fig, "species_family_treemap")
else:
    print("Figure 2: SKIPPED (squarify not installed)")


# ===================================================================
# Figure 3: Taxonomic group comparison
# ===================================================================
print("Figure 3: Taxonomic group comparison...")
groups_order = ["Sharks", "Rays & Skates", "Chimaeras"]
metrics: dict[str, list[int]] = {
    "Total papers": [],
    "Species studied (>0 papers)": [],
    "Species with >10 papers": [],
    "Species with >100 papers": [],
}

for g in groups_order:
    gdf = sp_df[sp_df["group"] == g]
    metrics["Total papers"].append(int(gdf["paper_count"].sum()))
    metrics["Species studied (>0 papers)"].append(len(gdf))
    metrics["Species with >10 papers"].append(int((gdf["paper_count"] > 10).sum()))
    metrics["Species with >100 papers"].append(int((gdf["paper_count"] > 100).sum()))

fig, axes = plt.subplots(1, 4, figsize=(16, 5))
for i, (metric_name, values) in enumerate(metrics.items()):
    ax = axes[i]
    bars = ax.bar(
        groups_order,
        values,
        color=[GROUP_COLOURS[g] for g in groups_order],
        edgecolor="white",
    )
    ax.set_title(metric_name, fontsize=10, fontweight="bold")
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(values) * 0.02,
                f"{val:,}", ha="center", va="bottom", fontsize=9, fontweight="bold")
    ax.set_ylim(0, max(values) * 1.15)
    ax.tick_params(axis="x", rotation=25)

fig.suptitle("Research coverage by taxonomic group", fontsize=14, fontweight="bold", y=1.02)
fig.tight_layout()
save(fig, "species_group_comparison")


# ===================================================================
# Figure 4: Papers-per-species histogram
# ===================================================================
print("Figure 4: Species coverage histogram...")
fig, ax = plt.subplots(figsize=(12, 8))
for g in groups_order:
    gdf = sp_df[sp_df["group"] == g]
    counts_arr = gdf["paper_count"].values
    if len(counts_arr) == 0:
        continue
    # Use log-spaced bins
    bins = np.logspace(0, np.log10(max(counts_arr.max(), 10)), 30)
    ax.hist(counts_arr, bins=bins, alpha=0.6, label=g, color=GROUP_COLOURS[g], edgecolor="white")

ax.set_xscale("log")
ax.set_xlabel("Number of papers (log scale)", fontsize=12)
ax.set_ylabel("Number of species", fontsize=12)
ax.set_title("Distribution of papers per species", fontsize=14, fontweight="bold")
ax.legend(fontsize=11)
ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{int(x):,}" if x >= 1 else ""))
save(fig, "species_coverage_histogram")


# ===================================================================
# Figure 5: Species × ecosystem heatmap (top 20)
# ===================================================================
print("Figure 5: Species × ecosystem heatmap...")
top20_sp = sp_df.head(20)

# Build co-occurrence matrix
heat_data = np.zeros((len(top20_sp), len(eco_cols)), dtype=int)
for i, (_, row) in enumerate(top20_sp.iterrows()):
    sp_mask = df[row["column"]] > 0
    for j, eco in enumerate(eco_cols):
        heat_data[i, j] = int((sp_mask & (df[eco] > 0)).sum())

eco_labels = [c.replace("eco_", "").replace("_", " ").capitalize() for c in eco_cols]
sp_labels = [italicise(n) for n in top20_sp["scientific_name"]]

fig, ax = plt.subplots(figsize=(14, 10))
vmin, vmax = 0, heat_data.max()
im = ax.imshow(heat_data, cmap="YlOrRd", aspect="auto", vmin=vmin, vmax=vmax)

ax.set_xticks(range(len(eco_labels)))
ax.set_xticklabels(eco_labels, rotation=45, ha="right", fontsize=9)
ax.set_yticks(range(len(sp_labels)))
ax.set_yticklabels(sp_labels, fontsize=9)

# Adaptive text
for i in range(heat_data.shape[0]):
    for j in range(heat_data.shape[1]):
        val = heat_data[i, j]
        colour = adaptive_text_colour(val, vmin, vmax)
        ax.text(j, i, f"{val}", ha="center", va="center", fontsize=7, color=colour)

ax.set_title("Top 20 species × ecosystem co-occurrence", fontsize=14, fontweight="bold")
fig.colorbar(im, ax=ax, label="Number of papers", shrink=0.8)
save(fig, "species_ecosystem_heatmap_top20")


# ===================================================================
# Figure 6: Habitat bar chart
# ===================================================================
print("Figure 6: Habitat barplot...")
eco_counts = {}
for eco in eco_cols:
    eco_counts[eco] = int((df[eco] > 0).sum())

eco_series = pd.Series(eco_counts).sort_values(ascending=True)
eco_nice = [c.replace("eco_", "").replace("_", " ").capitalize() for c in eco_series.index]

fig, ax = plt.subplots(figsize=(12, 8))
bars = ax.barh(eco_nice, eco_series.values, color="#2166ac", edgecolor="white")
for i, val in enumerate(eco_series.values):
    ax.text(val + eco_series.max() * 0.01, i, f"{val:,}", va="center", fontsize=9)

ax.set_xlabel("Number of papers", fontsize=12)
ax.set_title("Papers by ecosystem/habitat type", fontsize=14, fontweight="bold")
ax.set_xlim(0, eco_series.max() * 1.12)
save(fig, "habitat_barplot")


# ===================================================================
# Figure 7: Habitat co-occurrence heatmap
# ===================================================================
print("Figure 7: Habitat co-occurrence heatmap...")
eco_binary = (df[eco_cols] > 0).astype(int)
cooc = eco_binary.T.dot(eco_binary)
cooc_labels = [c.replace("eco_", "").replace("_", " ").capitalize() for c in eco_cols]
cooc.index = cooc_labels
cooc.columns = cooc_labels

fig, ax = plt.subplots(figsize=(14, 10))
vmin_c, vmax_c = 0, cooc.values.max()
im = ax.imshow(cooc.values, cmap="YlGnBu", aspect="auto", vmin=vmin_c, vmax=vmax_c)

ax.set_xticks(range(len(cooc_labels)))
ax.set_xticklabels(cooc_labels, rotation=45, ha="right", fontsize=9)
ax.set_yticks(range(len(cooc_labels)))
ax.set_yticklabels(cooc_labels, fontsize=9)

for i in range(len(cooc_labels)):
    for j in range(len(cooc_labels)):
        val = cooc.values[i, j]
        colour = adaptive_text_colour(val, vmin_c, vmax_c)
        ax.text(j, i, f"{int(val):,}", ha="center", va="center", fontsize=6, color=colour)

ax.set_title("Habitat co-occurrence (papers studying both habitats)", fontsize=14, fontweight="bold")
fig.colorbar(im, ax=ax, label="Number of papers", shrink=0.8)
save(fig, "habitat_cooccurrence_heatmap")


# ===================================================================
# Figure 8: Top 20 families
# ===================================================================
print("Figure 8: Family top 20 barplot...")
family_agg = sp_df.groupby(["family", "group"])["paper_count"].sum().reset_index()
family_agg = family_agg.sort_values("paper_count", ascending=False).head(20)
family_agg = family_agg.sort_values("paper_count", ascending=True)  # for horizontal bar

fig, ax = plt.subplots(figsize=(12, 8))
bars = ax.barh(
    family_agg["family"],
    family_agg["paper_count"],
    color=family_agg["group"].map(GROUP_COLOURS),
    edgecolor="white",
)
for i, (_, row) in enumerate(family_agg.iterrows()):
    ax.text(row["paper_count"] + family_agg["paper_count"].max() * 0.01, i,
            f"{row['paper_count']:,}", va="center", fontsize=9)

ax.set_xlabel("Number of papers", fontsize=12)
ax.set_title("Top 20 most-studied families", fontsize=14, fontweight="bold")
ax.set_xlim(0, family_agg["paper_count"].max() * 1.12)

legend_handles = [Patch(facecolor=c, label=g) for g, c in GROUP_COLOURS.items() if g != "Unknown"]
ax.legend(handles=legend_handles, loc="lower right", fontsize=10)
save(fig, "family_top20_barplot")


# ===================================================================
# Figure 9: Top 20 genera
# ===================================================================
print("Figure 9: Genus top 20 barplot...")
genus_agg = sp_df.groupby(["genus", "group"])["paper_count"].sum().reset_index()
genus_agg = genus_agg.sort_values("paper_count", ascending=False).head(20)
genus_agg = genus_agg.sort_values("paper_count", ascending=True)
genus_agg["label"] = genus_agg["genus"].apply(italicise)

fig, ax = plt.subplots(figsize=(12, 8))
bars = ax.barh(
    range(len(genus_agg)),
    genus_agg["paper_count"],
    color=genus_agg["group"].map(GROUP_COLOURS),
    edgecolor="white",
)
ax.set_yticks(range(len(genus_agg)))
ax.set_yticklabels(genus_agg["label"], fontsize=9)
for i, (_, row) in enumerate(genus_agg.iterrows()):
    ax.text(row["paper_count"] + genus_agg["paper_count"].max() * 0.01, i,
            f"{row['paper_count']:,}", va="center", fontsize=9)

ax.set_xlabel("Number of papers", fontsize=12)
ax.set_title("Top 20 most-studied genera", fontsize=14, fontweight="bold")
ax.set_xlim(0, genus_agg["paper_count"].max() * 1.12)

legend_handles = [Patch(facecolor=c, label=g) for g, c in GROUP_COLOURS.items() if g != "Unknown"]
ax.legend(handles=legend_handles, loc="lower right", fontsize=10)
save(fig, "genus_top20_barplot")


# ===================================================================
# Figure 10: Understudied species by family
# ===================================================================
print("Figure 10: Understudied species by family...")

# All species in taxonomy, not just those in our data
all_tax_species = set(tax_lookup.keys())
studied_species = set(sp_df["scientific_name"])

# Build family-level stats from full taxonomy
family_stats: dict[str, dict[str, int]] = {}
for sci, info in tax_lookup.items():
    fam = info["family"]
    if fam not in family_stats:
        family_stats[fam] = {"total": 0, "unstudied": 0, "group": info["group"]}
    family_stats[fam]["total"] += 1
    if sci not in studied_species:
        family_stats[fam]["unstudied"] += 1

fam_df = pd.DataFrame([
    {"family": fam, "total_species": s["total"], "unstudied": s["unstudied"],
     "group": s["group"], "pct_unstudied": 100 * s["unstudied"] / s["total"] if s["total"] > 0 else 0}
    for fam, s in family_stats.items()
])
# Top 20 largest families
fam_df = fam_df.sort_values("total_species", ascending=False).head(20)
fam_df = fam_df.sort_values("pct_unstudied", ascending=True)

fig, ax = plt.subplots(figsize=(7, 10))
bars = ax.barh(
    fam_df["family"],
    fam_df["pct_unstudied"],
    color=fam_df["group"].map(GROUP_COLOURS),
    edgecolor="white",
)
max_pct = fam_df["pct_unstudied"].max()
for i, (_, row) in enumerate(fam_df.iterrows()):
    label = f"{row['pct_unstudied']:.0f}% ({row['unstudied']}/{row['total_species']})"
    ax.text(row["pct_unstudied"] + 0.5, i, label, va="center", fontsize=8)

ax.set_xlabel("Percentage of species with 0 papers (%)", fontsize=12)
ax.set_title("Research gaps: unstudied species\nin the 20 largest families", fontsize=14, fontweight="bold")
ax.set_xlim(0, max_pct + 12)

legend_handles = [Patch(facecolor=c, label=g) for g, c in GROUP_COLOURS.items() if g != "Unknown"]
ax.legend(handles=legend_handles, loc="lower right", fontsize=10)
save(fig, "species_understudied_by_group")


# ===================================================================
# Summary
# ===================================================================
print("\nAll figures saved to:", FIG_DIR)
print("Done.")
