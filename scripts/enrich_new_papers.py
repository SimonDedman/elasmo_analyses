#!/usr/bin/env python3
"""Enrichment orchestrator: bring every paper's OpenAlex / NamSor / Altmetric /
Unpaywall side-table up to date, then rebuild the derived tables the figures
read. Safe to run repeatedly — every sub-step is incremental (skips work
already done via its own progress/cache file), so this both:

  * backfills the whole corpus on first run (papers added since the last
    enrichment show up as NA until this runs), and
  * is cheap in steady state (a cascade run that added 3 papers only enriches
    those 3).

It is wired into ``acquire_cascade.finalize_acquisitions`` so new downloads get
enriched automatically, and can be run standalone:

    python scripts/enrich_new_papers.py              # full chain
    python scripts/enrich_new_papers.py --skip altmetric namsor
    python scripts/enrich_new_papers.py --only openalex unpaywall

Chain (order matters — NamSor depends on OpenAlex authors):
  1. enrich_authors_openalex.py --resume     -> openalex_paper_authors / _unique_authors
  2. merge new authors into openalex_unique_authors_cleaned.csv (NamSor's input)
  3. enrich_namsor.py --endpoint all --resume -> namsor_enrichment.csv
  4. build_first_author_namsor.py             -> first_author_namsor.csv
  5. enrich_altmetric.py                      -> altmetric_scores.csv
  6. lookup_unpaywall_oa.py                   -> unpaywall_oa_by_doi.csv
  7. analyze_oa_results.py                    -> analysis/oa_by_year.csv (slide 12)
  8. analyze_collaboration_networks.R         -> analysis/country_collaboration_*.csv (slide 9)
  9. rebuild_viz_data.py                      -> viz_data.csv (unless --no-viz)
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import pandas as pd

BASE = Path("/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel")
PY = sys.executable
UNIQUE_RAW = BASE / "outputs/openalex_unique_authors.csv"
UNIQUE_CLEANED = BASE / "outputs/openalex_unique_authors_cleaned.csv"

# (name, kind, command) — kind "py"/"r" run via interpreter, "fn" is a callable.
STEPS = [
    ("openalex", "py", ["scripts/enrich_authors_openalex.py", "--resume"]),
    ("merge_authors", "fn", None),
    ("namsor", "py", ["scripts/enrich_namsor.py", "--endpoint", "all", "--resume"]),
    ("first_author", "py", ["scripts/build_first_author_namsor.py"]),
    ("altmetric", "py", ["scripts/enrich_altmetric.py"]),
    ("unpaywall", "py", ["scripts/lookup_unpaywall_oa.py"]),
    ("oa_by_year", "py", ["scripts/analyze_oa_results.py"]),
    ("collaboration", "r", ["scripts/analyze_collaboration_networks.R"]),
    ("viz_data", "py", ["scripts/rebuild_viz_data.py"]),
]


# NOTE: the OpenAlex author-quality post-processors (clean_author_names.py,
# resolve_initials_openalex.py, apply_author_dedup.py, fill_missing_institutions.py,
# infer_author_gender.py) are intentionally NOT part of this chain — they are a
# heavier, occasionally-run pass. enrich_authors_openalex.py --resume regenerates
# openalex_paper_authors.csv from raw API records and DROPS the inferred `gender`
# column those post-processors add, so build_first_author_namsor.py deliberately
# reads its gender-guesser fallback from openalex_unique_authors_cleaned.csv
# (which persists across resume runs) rather than paper_authors. Run the full
# post-processor chain separately if the atlas/institution figures need refreshed
# institution-fill or name-dedup.
def merge_new_authors_into_cleaned() -> None:
    """NamSor reads openalex_unique_authors_cleaned.csv (a richer, deduped set)
    in preference to the raw file. OpenAlex --resume only updates the raw file,
    so append any authors newly present in raw but absent from cleaned, letting
    NamSor's --resume enrich them without losing the cleaned set's extra rows."""
    if not UNIQUE_RAW.exists():
        print("    (no raw unique-authors file; skipping author merge)")
        return
    raw = pd.read_csv(UNIQUE_RAW, dtype=str)
    if not UNIQUE_CLEANED.exists():
        raw.to_csv(UNIQUE_CLEANED, index=False)
        print(f"    cleaned file created from raw ({len(raw)} authors)")
        return
    cleaned = pd.read_csv(UNIQUE_CLEANED, dtype=str)
    have = set(cleaned["openalex_author_id"].astype(str))
    new = raw[~raw["openalex_author_id"].astype(str).isin(have)]
    if new.empty:
        print("    no new authors to add to cleaned set")
        return
    out = pd.concat([cleaned, new.reindex(columns=cleaned.columns)], ignore_index=True)
    out.to_csv(UNIQUE_CLEANED, index=False)
    print(f"    appended {len(new)} new authors to cleaned set ({len(cleaned)} -> {len(out)})")


def run_step(name: str, kind: str, cmd, dry: bool) -> bool:
    print(f"\n{'=' * 70}\n  STEP: {name}\n{'=' * 70}")
    if kind == "fn":
        if dry:
            print("    [dry-run] would merge new authors into cleaned set")
            return True
        merge_new_authors_into_cleaned()
        return True
    runner = ["Rscript"] if kind == "r" else [PY]
    full = runner + [str(BASE / cmd[0])] + cmd[1:]
    if dry:
        print("    [dry-run]", " ".join(cmd))
        return True
    rc = subprocess.run(full, cwd=str(BASE)).returncode
    print(f"    exit code: {rc}")
    return rc == 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Run the incremental enrichment chain.")
    ap.add_argument("--skip", nargs="*", default=[], help="Step names to skip.")
    ap.add_argument("--only", nargs="*", default=[], help="Run ONLY these step names.")
    ap.add_argument("--no-viz", action="store_true", help="Skip the final rebuild_viz_data step.")
    ap.add_argument("--dry-run", action="store_true", help="Print the plan without running.")
    ap.add_argument("--continue-on-error", action="store_true", default=True,
                    help="Keep going if a step fails (default: on).")
    args = ap.parse_args()

    skip = set(args.skip)
    if args.no_viz:
        skip.add("viz_data")
    only = set(args.only)

    failed = []
    for name, kind, cmd in STEPS:
        if only and name not in only:
            continue
        if name in skip:
            print(f"\n  (skipping {name})")
            continue
        ok = run_step(name, kind, cmd, args.dry_run)
        if not ok:
            failed.append(name)
            if not args.continue_on_error:
                break

    print(f"\n{'=' * 70}")
    print(f"  Enrichment chain done. Failed steps: {failed or 'none'}")
    print(f"{'=' * 70}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
