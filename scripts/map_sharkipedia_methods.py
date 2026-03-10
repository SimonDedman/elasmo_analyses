#!/usr/bin/env python3
"""Map Sharkipedia measurement methods against the EEA technique taxonomy.

Produces a mapping table showing exact matches, fuzzy matches, and gaps
between Sharkipedia's method_name/model_name fields and our 151 EEA
technique names (from paper_techniques in technique_taxonomy.db) plus
the 215 technique columns in literature_review.duckdb.

Outputs:
    - method_mapping.csv   — per-method mapping with best match and score
    - method_mapping_summary.txt — human-readable summary
"""

from __future__ import annotations

import csv
import sqlite3
from difflib import SequenceMatcher
from pathlib import Path

import duckdb

# ------------------------------------------------------------------
# Paths
# ------------------------------------------------------------------
BASE = Path(
    "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
)
SHARKIPEDIA_CSV = (
    BASE / "data" / "sharkipedia" / "Sharkipedia-Traits-v1.0-22-01-25.csv"
)
TAXONOMY_DB = BASE / "database" / "technique_taxonomy.db"
DUCKDB_PATH = BASE / "outputs" / "literature_review.duckdb"
OUT_DIR = BASE / "data" / "sharkipedia"
OUT_CSV = OUT_DIR / "method_mapping.csv"
OUT_TXT = OUT_DIR / "method_mapping_summary.txt"

FUZZY_THRESHOLD = 0.6


# ------------------------------------------------------------------
# 1. Extract Sharkipedia methods and models
# ------------------------------------------------------------------
def load_sharkipedia_methods(path: Path) -> tuple[set[str], set[str]]:
    """Return unique (method_name, model_name) sets from the traits CSV."""
    methods: set[str] = set()
    models: set[str] = set()
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            m = row.get("method_name", "").strip()
            if m:
                methods.add(m)
            n = row.get("model_name", "").strip()
            if n:
                models.add(n)
    return methods, models


# ------------------------------------------------------------------
# 2. Extract EEA technique names from both sources
# ------------------------------------------------------------------
def load_eea_techniques(
    db_path: Path, duck_path: Path
) -> tuple[set[str], set[str]]:
    """Return (paper_techniques names, duckdb column-derived names)."""
    # From SQLite paper_techniques table
    conn = sqlite3.connect(str(db_path))
    rows = conn.execute(
        "SELECT DISTINCT technique_name FROM paper_techniques"
    ).fetchall()
    conn.close()
    sqlite_names = {r[0] for r in rows if r[0]}

    # From DuckDB column names (a_*, mf_*, st_* prefixes)
    duck = duckdb.connect(str(duck_path), read_only=True)
    cols = duck.execute("DESCRIBE literature_review").fetchall()
    duck.close()
    duck_names: set[str] = set()
    for col_name, *_ in cols:
        if col_name.startswith(("a_", "mf_", "st_")):
            # Convert column name to human-readable form
            # e.g. a_stable_isotope_analysis -> Stable Isotope Analysis
            readable = col_name.split("_", 1)[1].replace("_", " ").title()
            # Preserve acronyms that are all-caps in the sqlite set
            duck_names.add(readable)

    return sqlite_names, duck_names


# ------------------------------------------------------------------
# 3. Fuzzy matching
# ------------------------------------------------------------------
def normalise(s: str) -> str:
    """Lower-case, strip punctuation/whitespace for comparison."""
    return s.lower().replace("-", " ").replace("_", " ").strip()


def best_match(
    query: str, candidates: set[str]
) -> tuple[str, float, str]:
    """Return (best_candidate, score, match_type) for *query*.

    match_type is 'exact', 'fuzzy', or 'none'.
    """
    query_norm = normalise(query)

    # Check exact (case-insensitive)
    for c in candidates:
        if normalise(c) == query_norm:
            return c, 1.0, "exact"

    # Fuzzy
    best_score = 0.0
    best_candidate = ""
    for c in candidates:
        score = SequenceMatcher(None, query_norm, normalise(c)).ratio()
        if score > best_score:
            best_score = score
            best_candidate = c

    if best_score >= FUZZY_THRESHOLD:
        return best_candidate, round(best_score, 3), "fuzzy"

    return best_candidate, round(best_score, 3), "none"


# ------------------------------------------------------------------
# 4. Main
# ------------------------------------------------------------------
def main() -> None:
    methods, models = load_sharkipedia_methods(SHARKIPEDIA_CSV)
    sqlite_techs, duck_techs = load_eea_techniques(TAXONOMY_DB, DUCKDB_PATH)

    # Merge all EEA technique names into one pool
    all_eea = sqlite_techs | duck_techs

    print(f"Sharkipedia unique methods : {len(methods)}")
    print(f"Sharkipedia unique models  : {len(models)}")
    print(f"EEA techniques (SQLite)    : {len(sqlite_techs)}")
    print(f"EEA techniques (DuckDB)    : {len(duck_techs)}")
    print(f"EEA techniques (merged)    : {len(all_eea)}")

    # Combine methods + models for mapping (tag which is which)
    shark_items: list[tuple[str, str]] = []
    for m in sorted(methods):
        shark_items.append((m, "method"))
    for m in sorted(models):
        shark_items.append((m, "model"))

    # Build mapping rows
    rows: list[dict[str, str]] = []
    matched_eea: set[str] = set()

    for item, source in shark_items:
        candidate, score, match_type = best_match(item, all_eea)
        if match_type in ("exact", "fuzzy"):
            matched_eea.add(candidate)
        rows.append(
            {
                "sharkipedia_method": item if source == "method" else "",
                "sharkipedia_model": item if source == "model" else "",
                "best_eea_match": candidate,
                "match_score": str(score),
                "match_type": match_type,
            }
        )

    # Write CSV
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "sharkipedia_method",
                "sharkipedia_model",
                "best_eea_match",
                "match_score",
                "match_type",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    # Unmatched EEA techniques
    unmatched_eea = sorted(all_eea - matched_eea)

    # Counts
    n_exact = sum(1 for r in rows if r["match_type"] == "exact")
    n_fuzzy = sum(1 for r in rows if r["match_type"] == "fuzzy")
    n_none = sum(1 for r in rows if r["match_type"] == "none")

    # Summary
    lines: list[str] = [
        "Sharkipedia ↔ EEA Technique Taxonomy Mapping Summary",
        "=" * 55,
        "",
        "Input counts:",
        f"  Sharkipedia unique methods : {len(methods)}",
        f"  Sharkipedia unique models  : {len(models)}",
        f"  Total Sharkipedia items    : {len(shark_items)}",
        f"  EEA techniques (SQLite)    : {len(sqlite_techs)}",
        f"  EEA techniques (DuckDB cols): {len(duck_techs)}",
        f"  EEA techniques (merged)    : {len(all_eea)}",
        "",
        "Match results (Sharkipedia → EEA):",
        f"  Exact matches  : {n_exact}",
        f"  Fuzzy matches  : {n_fuzzy}  (threshold ≥ {FUZZY_THRESHOLD})",
        f"  No match       : {n_none}",
        f"  Coverage       : {n_exact + n_fuzzy}/{len(shark_items)}"
        f" ({100 * (n_exact + n_fuzzy) / len(shark_items):.0f}%)",
        "",
        "Matched Sharkipedia items:",
    ]
    for r in rows:
        if r["match_type"] != "none":
            item = r["sharkipedia_method"] or r["sharkipedia_model"]
            lines.append(
                f"  {item:45s} → {r['best_eea_match']:40s}"
                f"  ({r['match_type']}, {r['match_score']})"
            )

    lines.append("")
    lines.append("Unmatched Sharkipedia items (no EEA equivalent):")
    for r in rows:
        if r["match_type"] == "none":
            item = r["sharkipedia_method"] or r["sharkipedia_model"]
            lines.append(f"  {item}")

    lines.append("")
    lines.append(
        f"EEA techniques with no Sharkipedia match"
        f" ({len(unmatched_eea)} of {len(all_eea)}):"
    )
    for t in unmatched_eea:
        lines.append(f"  {t}")

    summary = "\n".join(lines) + "\n"
    OUT_TXT.write_text(summary, encoding="utf-8")

    print(f"\nWrote {OUT_CSV}")
    print(f"Wrote {OUT_TXT}")
    print(f"\n{summary}")


if __name__ == "__main__":
    main()
