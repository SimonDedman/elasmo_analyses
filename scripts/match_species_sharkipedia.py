#!/usr/bin/env python3
"""Match species between EEA database and Sharkipedia.

Identifies which species in our literature review have trait/trend data
available in Sharkipedia, and vice versa.

Outputs:
    - species_match_both.csv: species in both databases with trait/trend counts
    - species_match_eea_only.csv: species in our DB but not in Sharkipedia
    - species_match_sharkipedia_only.csv: Sharkipedia species not in our DB
    - species_match_summary.txt: summary statistics
"""

from __future__ import annotations

import csv
from pathlib import Path

import duckdb
import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE = Path(
    "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
)
SHARK_DIR = BASE / "data" / "sharkipedia"
OUTPUT_DIR = SHARK_DIR  # outputs go alongside input files

TAXONOMY_CSV = SHARK_DIR / "Sharkipedia-Taxonomy-v1.0-22-01-25.csv"
TRAITS_CSV = SHARK_DIR / "Sharkipedia-Traits-v1.0-22-01-25.csv"
TRENDS_CSV = SHARK_DIR / "Sharkipedia-Trends-v1.2-22-06-17.csv"
DUCKDB_PATH = BASE / "outputs" / "literature_review.duckdb"

# ---------------------------------------------------------------------------
# 1. Extract species from our DuckDB (sp_* column names)
# ---------------------------------------------------------------------------
print("Extracting species from EEA database...")
con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
sp_cols = con.execute(
    "SELECT column_name FROM information_schema.columns "
    "WHERE table_name = 'literature_review' AND column_name LIKE 'sp_%' "
    "ORDER BY column_name"
).fetchall()
con.close()

eea_species: dict[str, str] = {}  # normalised -> display name
for (col_name,) in sp_cols:
    # sp_carcharodon_carcharias -> carcharodon carcharias
    raw = col_name[3:].replace("_", " ")
    # Capitalise genus
    parts = raw.split()
    display = parts[0].capitalize() + " " + " ".join(parts[1:]) if len(parts) > 1 else parts[0].capitalize()
    normalised = raw.lower().strip()
    eea_species[normalised] = display

print(f"  EEA species count: {len(eea_species)}")

# ---------------------------------------------------------------------------
# 2. Extract species from Sharkipedia taxonomy
# ---------------------------------------------------------------------------
print("Extracting species from Sharkipedia taxonomy...")
taxonomy = pd.read_csv(TAXONOMY_CSV, encoding="utf-8-sig")
taxonomy.columns = taxonomy.columns.str.strip()

sharkipedia_species: dict[str, str] = {}  # normalised -> display name
for _, row in taxonomy.iterrows():
    name = str(row["Sharkipedia Scientific name"]).strip()
    if name and name.lower() != "nan":
        normalised = name.lower().strip()
        sharkipedia_species[normalised] = name

print(f"  Sharkipedia taxonomy species count: {len(sharkipedia_species)}")

# ---------------------------------------------------------------------------
# 3. Count traits per species
# ---------------------------------------------------------------------------
print("Counting Sharkipedia traits per species...")
traits = pd.read_csv(TRAITS_CSV, usecols=["species_name", "trait_class"])
traits["species_norm"] = traits["species_name"].str.lower().str.strip()

trait_counts = traits.groupby("species_norm").size().to_dict()
trait_classes = (
    traits.groupby("species_norm")["trait_class"]
    .apply(lambda x: sorted(set(x.dropna())))
    .to_dict()
)

print(f"  Species with trait data: {len(trait_counts)}")

# ---------------------------------------------------------------------------
# 4. Count trends per species
# ---------------------------------------------------------------------------
print("Counting Sharkipedia trends per species...")
trends = pd.read_csv(TRENDS_CSV, usecols=["Genus", "Species"])
trends["species_norm"] = (
    trends["Genus"].str.strip() + " " + trends["Species"].str.strip()
).str.lower().str.strip()

trend_counts = trends.groupby("species_norm").size().to_dict()

print(f"  Species with trend data: {len(trend_counts)}")

# Also add any species from traits/trends that might not be in taxonomy
# (covers edge cases / synonyms in data files)
all_sharkipedia_names = set(sharkipedia_species.keys())
traits_only_species = set(trait_counts.keys()) - all_sharkipedia_names
trends_only_species = set(trend_counts.keys()) - all_sharkipedia_names

for sp in traits_only_species | trends_only_species:
    if sp and sp != "nan":
        parts = sp.split()
        display = parts[0].capitalize() + " " + " ".join(parts[1:]) if len(parts) > 1 else parts[0].capitalize()
        sharkipedia_species[sp] = display

print(f"  Sharkipedia total species (taxonomy + data files): {len(sharkipedia_species)}")

# ---------------------------------------------------------------------------
# 5. Match species
# ---------------------------------------------------------------------------
print("Matching species...")
eea_set = set(eea_species.keys())
shark_set = set(sharkipedia_species.keys())

in_both = sorted(eea_set & shark_set)
eea_only = sorted(eea_set - shark_set)
shark_only = sorted(shark_set - eea_set)

print(f"  In both:             {len(in_both)}")
print(f"  EEA only:            {len(eea_only)}")
print(f"  Sharkipedia only:    {len(shark_only)}")

# ---------------------------------------------------------------------------
# 6. Write output CSVs
# ---------------------------------------------------------------------------
print("Writing output files...")

# Both
both_rows = []
for sp in in_both:
    n_traits = trait_counts.get(sp, 0)
    n_trends = trend_counts.get(sp, 0)
    classes = trait_classes.get(sp, [])
    both_rows.append({
        "species_name": eea_species[sp],
        "n_sharkipedia_traits": n_traits,
        "n_sharkipedia_trends": n_trends,
        "trait_classes_available": "; ".join(classes) if classes else "",
    })

both_df = pd.DataFrame(both_rows)
both_df.to_csv(OUTPUT_DIR / "species_match_both.csv", index=False)

# EEA only
eea_only_df = pd.DataFrame(
    [{"species_name": eea_species[sp]} for sp in eea_only]
)
eea_only_df.to_csv(OUTPUT_DIR / "species_match_eea_only.csv", index=False)

# Sharkipedia only
shark_only_rows = []
for sp in shark_only:
    n_traits = trait_counts.get(sp, 0)
    n_trends = trend_counts.get(sp, 0)
    classes = trait_classes.get(sp, [])
    shark_only_rows.append({
        "species_name": sharkipedia_species[sp],
        "n_sharkipedia_traits": n_traits,
        "n_sharkipedia_trends": n_trends,
        "trait_classes_available": "; ".join(classes) if classes else "",
    })

shark_only_df = pd.DataFrame(shark_only_rows)
shark_only_df.to_csv(OUTPUT_DIR / "species_match_sharkipedia_only.csv", index=False)

# ---------------------------------------------------------------------------
# 7. Summary statistics
# ---------------------------------------------------------------------------
both_with_traits = sum(1 for r in both_rows if r["n_sharkipedia_traits"] > 0)
both_with_trends = sum(1 for r in both_rows if r["n_sharkipedia_trends"] > 0)
total_traits_matched = sum(r["n_sharkipedia_traits"] for r in both_rows)
total_trends_matched = sum(r["n_sharkipedia_trends"] for r in both_rows)

# Trait class breakdown for matched species
all_classes: dict[str, int] = {}
for r in both_rows:
    for cls in r["trait_classes_available"].split("; "):
        if cls:
            all_classes[cls] = all_classes.get(cls, 0) + 1

summary_lines = [
    "Species Matching: EEA Database vs Sharkipedia",
    "=" * 50,
    "",
    f"EEA database species:          {len(eea_species):>6}",
    f"Sharkipedia species:           {len(sharkipedia_species):>6}",
    "",
    f"Matched (in both):             {len(in_both):>6}  ({100 * len(in_both) / len(eea_species):.1f}% of EEA)",
    f"EEA only (no Sharkipedia):     {len(eea_only):>6}  ({100 * len(eea_only) / len(eea_species):.1f}% of EEA)",
    f"Sharkipedia only (no EEA):     {len(shark_only):>6}  ({100 * len(shark_only) / len(sharkipedia_species):.1f}% of Sharkipedia)",
    "",
    "Among matched species:",
    f"  With trait data:             {both_with_traits:>6}  ({100 * both_with_traits / max(len(in_both), 1):.1f}%)",
    f"  With trend data:             {both_with_trends:>6}  ({100 * both_with_trends / max(len(in_both), 1):.1f}%)",
    f"  Total trait records:         {total_traits_matched:>6}",
    f"  Total trend records:         {total_trends_matched:>6}",
    "",
    "Trait classes available for matched species:",
]
for cls in sorted(all_classes, key=all_classes.get, reverse=True):
    summary_lines.append(f"  {cls:<30} {all_classes[cls]:>5} species")

summary_lines += [
    "",
    "Output files:",
    f"  species_match_both.csv             ({len(in_both)} rows)",
    f"  species_match_eea_only.csv         ({len(eea_only)} rows)",
    f"  species_match_sharkipedia_only.csv ({len(shark_only)} rows)",
]

summary_text = "\n".join(summary_lines) + "\n"
(OUTPUT_DIR / "species_match_summary.txt").write_text(summary_text)

print()
print(summary_text)
print("Done.")
