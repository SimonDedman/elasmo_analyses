#!/usr/bin/env python3
"""
RETIRED 21 Oct 2026: gender inference from first names is no longer run.

This script added a ``gender`` column (male / female / unknown) to the
unique-authors and paper-authors CSVs using the ``gender-guesser`` library.
That library is GPL-3.0; the repository's code is Apache-2.0, so it was
removed on 21 Oct 2026, and inferred gender is no longer published (the site
and repository were scrubbed of it the same week).

Running the script now stops with an explanation and changes nothing.
Gender columns already written to the local, git-ignored CSVs
(``outputs/openalex_unique_authors.csv``, ``outputs/openalex_paper_authors.csv``,
``outputs/openalex_unique_authors_cleaned.csv``) and the Genderize cache
(``outputs/.genderize_cache.json``) are untouched and remain usable locally.

``compute_summary`` and ``print_summary`` are kept: they tabulate an existing
``gender`` column and need no inference library.

Usage (prints the retirement notice and exits with status 1):
    python scripts/infer_author_gender.py
"""

from __future__ import annotations

import sys

import pandas as pd

REMOVED_MESSAGE = (
    "infer_author_gender.py is retired: the gender-guesser library was removed from "
    "this repository on 21 Oct 2026 for licence reasons (GPL-3.0 in an Apache-2.0 "
    "codebase), and inferred gender is no longer published. Existing cached results "
    "(the gender columns in outputs/openalex_*authors*.csv and "
    "outputs/.genderize_cache.json) are untouched and remain usable locally."
)

# ---------------------------------------------------------------------------
# Summary statistics
# ---------------------------------------------------------------------------


def _pct(count: int, total: int) -> str:
    """Format a count as a percentage string."""
    if total == 0:
        return "0.0"
    return f"{100 * count / total:.1f}"


def compute_summary(
    df: pd.DataFrame,
    has_year: bool = False,
) -> pd.DataFrame:
    """Compute gender summary statistics.

    Args:
        df: DataFrame with at least a ``gender`` column.
        has_year: If True, also break down by decade using a ``year``
            column.

    Returns:
        A summary DataFrame suitable for CSV export.
    """
    rows: list[dict[str, object]] = []

    def _add_row(label: str, subset: pd.DataFrame) -> None:
        total = len(subset)
        male = int((subset["gender"] == "male").sum())
        female = int((subset["gender"] == "female").sum())
        unknown = int((subset["gender"] == "unknown").sum())
        rows.append(
            {
                "group": label,
                "total": total,
                "male": male,
                "male_pct": _pct(male, total),
                "female": female,
                "female_pct": _pct(female, total),
                "unknown": unknown,
                "unknown_pct": _pct(unknown, total),
            }
        )

    _add_row("all", df)

    if has_year and "year" in df.columns:
        df = df.copy()
        df["year_numeric"] = pd.to_numeric(df["year"], errors="coerce")
        df["decade"] = (df["year_numeric"] // 10 * 10).astype("Int64")
        for decade, group in sorted(df.groupby("decade", dropna=True)):
            _add_row(f"{int(decade)}s", group)

    return pd.DataFrame(rows)


def print_summary(summary: pd.DataFrame) -> None:
    """Print a human-readable gender summary to the console."""
    print("\n--- Gender Inference Summary ---")
    for _, row in summary.iterrows():
        print(
            f"  {row['group']:>10s}:  "
            f"total={row['total']:>7,}  "
            f"male={row['male']:>6,} ({row['male_pct']:>5s}%)  "
            f"female={row['female']:>6,} ({row['female_pct']:>5s}%)  "
            f"unknown={row['unknown']:>6,} ({row['unknown_pct']:>5s}%)"
        )
    print()


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


def main() -> None:
    """Stop with the retirement notice; nothing is read or written."""
    print(f"ERROR: {REMOVED_MESSAGE}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
