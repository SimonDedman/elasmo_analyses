#!/usr/bin/env python3
"""
Infer gender from author first names using the gender_guesser library.

Adds a ``gender`` column (male / female / unknown) to the unique-authors
and paper-authors CSV files produced by ``enrich_authors_openalex.py``.

This is a standard bibliometric methodology for analysing gender
disparities in scholarly publishing.  See:

    Lariviere, V., Ni, C., Gingras, Y., Cronin, B. & Sugimoto, C.R.
    (2013). Bibliometrics: Global gender disparities in science.
    *Nature*, 504(7479), 211-213. https://doi.org/10.1038/504211a

**Limitations:** Gender inference from first names is probabilistic,
culturally biased towards Western naming conventions, and does not
capture non-binary gender identities.  Results should be interpreted
with appropriate caveats.

Usage:
    python scripts/infer_author_gender.py
    python scripts/infer_author_gender.py --input outputs/openalex_unique_authors.csv
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from pathlib import Path
from typing import Optional

import pandas as pd

# ---------------------------------------------------------------------------
# Dependency check
# ---------------------------------------------------------------------------

try:
    import gender_guesser.detector as gender_detector
except ImportError:
    print(
        "ERROR: gender_guesser package not found.\n"
        "Install it with:  pip install gender-guesser",
        file=sys.stderr,
    )
    sys.exit(1)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROJECT_BASE = Path(
    "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
)
DEFAULT_UNIQUE_AUTHORS = PROJECT_BASE / "outputs/openalex_unique_authors.csv"
DEFAULT_PAPER_AUTHORS = PROJECT_BASE / "outputs/openalex_paper_authors.csv"
SUMMARY_OUTPUT = PROJECT_BASE / "outputs/gender_inference_summary.csv"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Pre-compiled pattern: a single letter optionally followed by a full stop
_INITIAL_RE = re.compile(r"^[A-Za-z]\.?$")


# ---------------------------------------------------------------------------
# Gender inference helpers
# ---------------------------------------------------------------------------


def _is_initial(name: str) -> bool:
    """Return True if *name* looks like a bare initial (e.g. 'J' or 'J.')."""
    return bool(_INITIAL_RE.match(name.strip()))


def _simplify_gender(raw: str) -> str:
    """Collapse gender_guesser categories to male / female / unknown.

    Mapping:
        male, mostly_male   -> male
        female, mostly_female -> female
        andy, unknown        -> unknown
    """
    if raw in ("male", "mostly_male"):
        return "male"
    if raw in ("female", "mostly_female"):
        return "female"
    return "unknown"


def infer_gender(
    first_name: Optional[str],
    detector: gender_detector.Detector,
) -> str:
    """Infer gender from a first name string.

    Strategy (in order):
    1. If empty / null / initial-only, return ``unknown``.
    2. Try the full first-name string as given.
    3. For hyphenated names (e.g. "Jean-Pierre"), try the part before
       the first hyphen.
    4. For multi-word names (e.g. "Maria Jose"), try the first word.
    5. Fall back to ``unknown``.

    Args:
        first_name: The author's first name (may be None).
        detector: A ``gender_guesser.detector.Detector`` instance.

    Returns:
        One of ``"male"``, ``"female"``, or ``"unknown"``.
    """
    if not first_name or not isinstance(first_name, str):
        return "unknown"

    name = first_name.strip()
    if not name or _is_initial(name):
        return "unknown"

    # 1. Try the full name as-is
    result = _simplify_gender(detector.get_gender(name))
    if result != "unknown":
        return result

    # 2. Hyphenated name: try the first component
    if "-" in name:
        first_part = name.split("-")[0].strip()
        if first_part and not _is_initial(first_part):
            result = _simplify_gender(detector.get_gender(first_part))
            if result != "unknown":
                return result

    # 3. Multi-word name: try the first word
    if " " in name:
        first_word = name.split()[0].strip()
        if first_word and not _is_initial(first_word):
            result = _simplify_gender(detector.get_gender(first_word))
            if result != "unknown":
                return result

    return "unknown"


def build_gender_lookup(
    unique_authors: pd.DataFrame,
    detector: gender_detector.Detector,
) -> dict[str, str]:
    """Build a first_name -> gender mapping from unique first names.

    This avoids redundant look-ups when many authors share the same
    first name.

    Args:
        unique_authors: DataFrame with a ``first_name`` column.
        detector: A gender_guesser Detector instance.

    Returns:
        Dictionary mapping each distinct first name to its inferred
        gender string.
    """
    distinct_names = unique_authors["first_name"].dropna().unique()
    logger.info("Inferring gender for %d distinct first names.", len(distinct_names))

    lookup: dict[str, str] = {}
    for name in distinct_names:
        lookup[name] = infer_gender(name, detector)

    return lookup


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
    """Run gender inference on author CSV files."""
    parser = argparse.ArgumentParser(
        description="Infer gender from author first names.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_UNIQUE_AUTHORS,
        help="Path to the unique-authors CSV (default: %(default)s).",
    )
    parser.add_argument(
        "--paper-authors",
        type=Path,
        default=DEFAULT_PAPER_AUTHORS,
        help="Path to the paper-authors CSV (default: %(default)s).",
    )
    parser.add_argument(
        "--summary-output",
        type=Path,
        default=SUMMARY_OUTPUT,
        help="Path for the summary CSV (default: %(default)s).",
    )
    args = parser.parse_args()

    # Validate inputs
    if not args.input.exists():
        logger.error("Unique-authors CSV not found: %s", args.input)
        sys.exit(1)

    # Load data
    logger.info("Reading unique authors from %s", args.input)
    unique_df = pd.read_csv(args.input, dtype=str)
    logger.info("Loaded %d unique authors.", len(unique_df))

    if "first_name" not in unique_df.columns:
        logger.error(
            "Column 'first_name' not found in %s. Available columns: %s",
            args.input,
            list(unique_df.columns),
        )
        sys.exit(1)

    # Initialise detector
    detector = gender_detector.Detector()

    # Build look-up from distinct first names, then map onto all rows
    gender_lookup = build_gender_lookup(unique_df, detector)

    unique_df["gender"] = unique_df["first_name"].map(gender_lookup).fillna("unknown")

    # Save updated unique authors
    unique_df.to_csv(args.input, index=False)
    logger.info("Wrote updated unique authors (%d rows) to %s", len(unique_df), args.input)

    # Process paper-authors file if it exists
    paper_authors_path = args.paper_authors
    has_year = False
    paper_df: Optional[pd.DataFrame] = None

    if paper_authors_path.exists():
        logger.info("Reading paper authors from %s", paper_authors_path)
        paper_df = pd.read_csv(paper_authors_path, dtype=str)
        logger.info("Loaded %d paper-author rows.", len(paper_df))

        if "first_name" in paper_df.columns:
            paper_df["gender"] = (
                paper_df["first_name"].map(gender_lookup).fillna("unknown")
            )
            paper_df.to_csv(paper_authors_path, index=False)
            logger.info(
                "Wrote updated paper authors (%d rows) to %s",
                len(paper_df),
                paper_authors_path,
            )
            has_year = "year" in paper_df.columns
        else:
            logger.warning(
                "Column 'first_name' not found in %s; skipping gender merge.",
                paper_authors_path,
            )
            paper_df = None
    else:
        logger.warning(
            "Paper-authors CSV not found at %s; skipping.", paper_authors_path
        )

    # Compute and save summary
    # Use paper_df for decade breakdown (it has year); fall back to unique_df
    summary_source = paper_df if paper_df is not None else unique_df
    summary = compute_summary(summary_source, has_year=has_year)
    summary.to_csv(args.summary_output, index=False)
    logger.info("Wrote gender summary to %s", args.summary_output)

    print_summary(summary)


if __name__ == "__main__":
    main()
