#!/usr/bin/env python3
"""Apply author-dedup decision artefacts to the canonical author CSVs.

Inputs (decision artefacts — Apr 17):
  outputs/author_aliases.csv         alias_openalex_id -> canonical_openalex_id
  outputs/author_name_corrections.csv openalex_author_id -> corrected first/last
  outputs/author_excluded.csv        openalex_author_id -> drop entirely

Canonical targets:
  outputs/openalex_paper_authors.csv   (per-paper author rows)
  outputs/openalex_unique_authors.csv  (one row per author)

Transformations:
  1. Drop rows for excluded IDs from both CSVs.
  2. In paper_authors: rewrite alias_id -> canonical_id, then dedupe
     (paper_id, canonical_id, author_position) collisions that arise when
     the same person was listed twice under two IDs on the same paper.
  3. In unique_authors: drop alias rows (their data has merged into the
     canonical row); update paper_count for each canonical by recomputing
     from the rewritten paper_authors CSV.
  4. Apply name corrections to display_name / first_name / last_name on
     both CSVs for any surviving row whose bare ID is in the corrections
     table.

Originals are copied to outputs/.backups/<stamp>_<file> before rewriting.

Assumptions (verified against current artefacts 2026-04-18):
  - No alias chains (A -> B -> C): canonical IDs are never themselves aliased.
  - Aliases, excluded, and corrections disjoint at the ID level (no ID
    tagged in multiple lists).
  - paper_authors.openalex_author_id is stored in URL form
    (``https://openalex.org/A...``); the other three CSVs use bare IDs.
    This script normalises to bare for matching and preserves the
    paper_authors URL-form on write.
"""

from __future__ import annotations

import argparse
import logging
import re
import shutil
import sys
from pathlib import Path

import pandas as pd

LOG = logging.getLogger("apply_author_dedup")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
BACKUP_DIR = OUTPUTS_DIR / ".backups"

PAPER_AUTHORS_PATH = OUTPUTS_DIR / "openalex_paper_authors.csv"
UNIQUE_AUTHORS_PATH = OUTPUTS_DIR / "openalex_unique_authors.csv"
ALIASES_PATH = OUTPUTS_DIR / "author_aliases.csv"
CORRECTIONS_PATH = OUTPUTS_DIR / "author_name_corrections.csv"
EXCLUDED_PATH = OUTPUTS_DIR / "author_excluded.csv"

OA_URL_PREFIX = "https://openalex.org/"
BARE_ID_RE = re.compile(r"A\d+")


def _bare(oa_id: object) -> str | None:
    """Normalise an OpenAlex author ID to bare form (``A5005519696``)."""
    if not isinstance(oa_id, str):
        return None
    m = BARE_ID_RE.search(oa_id)
    return m.group(0) if m else None


def _with_url(oa_id: str) -> str:
    """Add the OpenAlex URL prefix if missing (paper_authors uses URL form)."""
    if oa_id.startswith(OA_URL_PREFIX):
        return oa_id
    return OA_URL_PREFIX + oa_id


def _backup(path: Path, stamp: str) -> Path:
    BACKUP_DIR.mkdir(exist_ok=True)
    dest = BACKUP_DIR / f"{stamp}_{path.name}"
    shutil.copy2(path, dest)
    LOG.info("backup %s -> %s", path.name, dest.relative_to(PROJECT_ROOT))
    return dest


def _build_display_name(first: str | None, last: str | None) -> str:
    """Recompose display_name from corrected first + last.

    Mirrors the convention used by the rest of the project: first last
    with single space, trimmed, no extra punctuation.
    """
    parts = [(first or "").strip(), (last or "").strip()]
    return " ".join(p for p in parts if p)


def load_artefacts() -> tuple[dict[str, str], dict[str, tuple[str, str]], set[str]]:
    """Return (alias_map, corrections_map, excluded_set), all keyed by bare IDs."""
    aliases_df = pd.read_csv(ALIASES_PATH)
    corrections_df = pd.read_csv(CORRECTIONS_PATH)
    excluded_df = pd.read_csv(EXCLUDED_PATH)

    alias_map: dict[str, str] = {}
    for _, row in aliases_df.iterrows():
        a = _bare(row["alias_openalex_id"])
        c = _bare(row["canonical_openalex_id"])
        if a and c:
            alias_map[a] = c

    corrections_map: dict[str, tuple[str, str]] = {}
    for _, row in corrections_df.iterrows():
        k = _bare(row["openalex_author_id"])
        if not k:
            continue
        first = str(row["corrected_first_name"]) if pd.notna(row["corrected_first_name"]) else ""
        last = str(row["corrected_last_name"]) if pd.notna(row["corrected_last_name"]) else ""
        corrections_map[k] = (first, last)

    excluded_set: set[str] = {
        _bare(x) for x in excluded_df["openalex_author_id"].dropna().tolist()
    }
    excluded_set.discard(None)  # type: ignore[arg-type]

    # Integrity checks (cheap)
    chains = set(alias_map.keys()) & set(alias_map.values())
    if chains:
        LOG.warning("%d alias chains detected (A->B where B is also aliased) — not handled", len(chains))
    overlap_excl_alias = excluded_set & set(alias_map.keys())
    if overlap_excl_alias:
        LOG.warning("%d IDs in both excluded and aliases — excluded takes precedence", len(overlap_excl_alias))

    LOG.info("artefacts: %d aliases, %d corrections, %d excluded",
             len(alias_map), len(corrections_map), len(excluded_set))
    return alias_map, corrections_map, excluded_set


def apply_to_paper_authors(
    alias_map: dict[str, str],
    corrections_map: dict[str, tuple[str, str]],
    excluded_set: set[str],
) -> pd.DataFrame:
    df = pd.read_csv(PAPER_AUTHORS_PATH, dtype=str)
    n_in = len(df)

    # Bare-ID column for matching
    df["_bare_id"] = df["openalex_author_id"].map(_bare)

    # Drop excluded
    excl_mask = df["_bare_id"].isin(excluded_set)
    n_dropped = int(excl_mask.sum())
    df = df[~excl_mask].copy()

    # Rewrite aliases -> canonicals (preserve URL-form in the stored column)
    alias_mask = df["_bare_id"].isin(alias_map)
    n_rewritten = int(alias_mask.sum())
    df.loc[alias_mask, "_bare_id"] = df.loc[alias_mask, "_bare_id"].map(alias_map)
    df.loc[alias_mask, "openalex_author_id"] = df.loc[alias_mask, "_bare_id"].map(_with_url)

    # Apply name corrections (surviving rows)
    corr_mask = df["_bare_id"].isin(corrections_map)
    n_corrected = int(corr_mask.sum())
    for idx in df.index[corr_mask]:
        bare = df.at[idx, "_bare_id"]
        first, last = corrections_map[bare]
        df.at[idx, "first_name"] = first
        df.at[idx, "last_name"] = last
        df.at[idx, "display_name"] = _build_display_name(first, last)

    # Dedupe: after alias rewrite, the same author may appear twice on the same
    # paper if both alias and canonical were listed. Keep the first (stable).
    before_dedup = len(df)
    df = df.drop_duplicates(subset=["literature_id", "openalex_author_id", "author_position"], keep="first")
    n_collisions = before_dedup - len(df)

    df = df.drop(columns=["_bare_id"])

    LOG.info(
        "paper_authors: %d in -> %d out (excluded=%d, aliased=%d, corrected=%d, merged_collisions=%d)",
        n_in, len(df), n_dropped, n_rewritten, n_corrected, n_collisions,
    )
    return df


def apply_to_unique_authors(
    alias_map: dict[str, str],
    corrections_map: dict[str, tuple[str, str]],
    excluded_set: set[str],
    new_paper_authors: pd.DataFrame,
) -> pd.DataFrame:
    df = pd.read_csv(UNIQUE_AUTHORS_PATH, dtype=str)
    n_in = len(df)

    df["_bare_id"] = df["openalex_author_id"].map(_bare)

    # Drop excluded + drop alias rows (merged into canonicals)
    drop_mask = df["_bare_id"].isin(excluded_set) | df["_bare_id"].isin(alias_map)
    n_dropped = int(drop_mask.sum())
    df = df[~drop_mask].copy()

    # Apply corrections
    corr_mask = df["_bare_id"].isin(corrections_map)
    n_corrected = int(corr_mask.sum())
    for idx in df.index[corr_mask]:
        bare = df.at[idx, "_bare_id"]
        first, last = corrections_map[bare]
        df.at[idx, "first_name"] = first
        df.at[idx, "last_name"] = last
        df.at[idx, "display_name"] = _build_display_name(first, last)

    # Recompute paper_count per author from rewritten paper_authors.
    # Count distinct literature_ids per openalex_author_id.
    pa = new_paper_authors.dropna(subset=["literature_id", "openalex_author_id"])
    counts = (
        pa.groupby("openalex_author_id")["literature_id"]
          .nunique()
          .rename("paper_count_new")
          .reset_index()
    )
    counts["_bare_id"] = counts["openalex_author_id"].map(_bare)
    count_map = dict(zip(counts["_bare_id"], counts["paper_count_new"]))

    updated = 0
    zeroed = 0
    for idx in df.index:
        bare = df.at[idx, "_bare_id"]
        new_pc = count_map.get(bare, 0)
        old_pc = df.at[idx, "paper_count"]
        try:
            old_pc_i = int(old_pc) if old_pc and not pd.isna(old_pc) else 0
        except (ValueError, TypeError):
            old_pc_i = 0
        if new_pc != old_pc_i:
            df.at[idx, "paper_count"] = str(int(new_pc))
            updated += 1
            if new_pc == 0:
                zeroed += 1

    df = df.drop(columns=["_bare_id"])

    LOG.info(
        "unique_authors: %d in -> %d out (dropped=%d, corrected=%d, paper_count_updated=%d, zeroed=%d)",
        n_in, len(df), n_dropped, n_corrected, updated, zeroed,
    )
    return df


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--dry-run", action="store_true", help="Compute changes but don't write.")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-7s  %(message)s",
        datefmt="%H:%M:%S",
    )

    for path in (PAPER_AUTHORS_PATH, UNIQUE_AUTHORS_PATH, ALIASES_PATH, CORRECTIONS_PATH, EXCLUDED_PATH):
        if not path.exists():
            LOG.error("required file missing: %s", path)
            return 1

    alias_map, corrections_map, excluded_set = load_artefacts()

    new_paper_authors = apply_to_paper_authors(alias_map, corrections_map, excluded_set)
    new_unique_authors = apply_to_unique_authors(
        alias_map, corrections_map, excluded_set, new_paper_authors
    )

    if args.dry_run:
        LOG.info("dry-run: skipping writes")
        return 0

    stamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    _backup(PAPER_AUTHORS_PATH, stamp)
    _backup(UNIQUE_AUTHORS_PATH, stamp)

    new_paper_authors.to_csv(PAPER_AUTHORS_PATH, index=False)
    new_unique_authors.to_csv(UNIQUE_AUTHORS_PATH, index=False)
    LOG.info("wrote %s (%d rows)", PAPER_AUTHORS_PATH.name, len(new_paper_authors))
    LOG.info("wrote %s (%d rows)", UNIQUE_AUTHORS_PATH.name, len(new_unique_authors))
    return 0


if __name__ == "__main__":
    sys.exit(main())
