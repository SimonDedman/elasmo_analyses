#!/usr/bin/env python3
"""Tests for the retraction-aware writer guards in extract_schema_columns.py:
normalize_binary_columns() and apply_incremental_results().

These are the must-fix guards for the whole-parquet `fillna(0).astype(int)`
that used to run unconditionally in extract_schema_columns.py's own main()
(~L2399 before this fix), extract_incremental.py (~L142), and
sync_shark_references.py's run_incremental_extraction() (~L1455) — which
would otherwise silently re-zero a retracted row's NULLs on the very next
incremental extraction or monthly sync, destroying the "needs re-extraction"
signal set by scripts/retract_wrong_pdf_extractions.py.

Run: python3 -m pytest tests/test_extraction_writer_guards.py -q
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import extract_schema_columns as esc  # noqa: E402

BINARY_COLS = ["eco_marine", "pr_bycatch", "d_biology"]


def _synthetic_df() -> pd.DataFrame:
    """3 rows: id 1 retracted (NULL extraction cols + provenance), id 2
    never-extracted (NULL, no status — must stay indistinguishable from a
    freshly-processed 0 the way it always has), id 3 normal (has real
    values already)."""
    return pd.DataFrame({
        "literature_id": ["1", "2", "3"],
        "eco_marine": pd.array([None, None, 1], dtype="Int64"),
        "pr_bycatch": pd.array([None, None, 0], dtype="Int64"),
        "d_biology": pd.array([None, None, 1], dtype="Int64"),
        "extraction_status": ["retracted_wrong_pdf", None, None],
        "extraction_retracted_at": ["2026-09-14T00:00:00+00:00", None, None],
        "extraction_retracted_reason": ["misfiled PDF", None, None],
    })


# ---------------------------------------------------------------------------
# normalize_binary_columns()
# ---------------------------------------------------------------------------

def test_retracted_row_keeps_nulls_non_retracted_row_gets_zero_filled():
    df = _synthetic_df()
    out = esc.normalize_binary_columns(df.copy(), BINARY_COLS)

    # id 1 (retracted): NULLs survive the fill.
    for col in BINARY_COLS:
        assert pd.isna(out.loc[0, col]), f"retracted row col {col} should stay NULL"

    # id 2 (never extracted, no retraction in play): 0-filled exactly like
    # the old unconditional fillna(0) always did.
    for col in BINARY_COLS:
        assert out.loc[1, col] == 0

    # id 3 (already has real values): untouched.
    assert out.loc[2, "eco_marine"] == 1
    assert out.loc[2, "pr_bycatch"] == 0
    assert out.loc[2, "d_biology"] == 1

    # dtype supports both real 0/1 ints and <NA> in the one column.
    for col in BINARY_COLS:
        assert str(out[col].dtype) == "Int64"


def test_no_retraction_in_play_stays_plain_int64():
    """When nothing anywhere in the frame is retracted, behaviour (fill AND
    dtype) is byte-for-byte the old unconditional fillna(0).astype(int) —
    the overwhelmingly common case must not pay for the guard."""
    df = pd.DataFrame({
        "literature_id": ["1", "2"],
        "eco_marine": [1, None],
        "extraction_status": [None, None],
    })
    out = esc.normalize_binary_columns(df.copy(), ["eco_marine"])
    assert out["eco_marine"].tolist() == [1, 0]
    assert str(out["eco_marine"].dtype) == "int64"


def test_missing_extraction_status_column_treated_as_nothing_retracted():
    """Old parquet from before this feature existed, with no
    extraction_status column at all, must still work exactly as before."""
    df = pd.DataFrame({
        "literature_id": ["1", "2"],
        "eco_marine": [None, 1],
    })
    out = esc.normalize_binary_columns(df.copy(), ["eco_marine"])
    assert out["eco_marine"].tolist() == [0, 1]
    assert str(out["eco_marine"].dtype) == "int64"


def test_parquet_roundtrip_preserves_nulls_and_values(tmp_path):
    df = _synthetic_df()
    out = esc.normalize_binary_columns(df.copy(), BINARY_COLS)
    path = tmp_path / "roundtrip.parquet"
    out.to_parquet(path, index=False)
    back = pd.read_parquet(path)
    assert pd.isna(back.loc[0, "eco_marine"])
    assert back.loc[1, "eco_marine"] == 0
    assert back.loc[2, "eco_marine"] == 1


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="R not installed")
def test_r_arrow_reads_retracted_cell_as_na(tmp_path):
    """Confirms the R pipeline's `sum(col == 1, na.rm = TRUE)` pattern (used
    throughout visualize_issue2_schema_plots.R etc.) sees a retracted cell
    as NA, not as 0 — verified live 2026-09-14, see
    outputs/misfile_blast_radius_2026-09-14/retraction_dry_run.txt."""
    df = _synthetic_df()
    out = esc.normalize_binary_columns(df.copy(), BINARY_COLS)
    path = tmp_path / "for_r.parquet"
    out.to_parquet(path, index=False)

    r_script = f'''
    library(arrow)
    df <- read_parquet("{path}")
    stopifnot(is.na(df$eco_marine[1]))
    stopifnot(df$eco_marine[2] == 0)
    stopifnot(df$eco_marine[3] == 1)
    stopifnot(sum(df$eco_marine == 1, na.rm = TRUE) == 1)
    cat("R-OK\\n")
    '''
    result = subprocess.run(
        ["Rscript", "-e", r_script], capture_output=True, text=True, timeout=60,
    )
    assert "R-OK" in result.stdout, result.stderr


# ---------------------------------------------------------------------------
# apply_incremental_results()
# ---------------------------------------------------------------------------

def test_reextraction_overwrites_nulls_and_sets_re_extracted_status():
    df_enriched = _synthetic_df()

    # Fresh process_paper()-shaped results for id 1 only — a correct PDF was
    # filed and it was reprocessed. id 2 / id 3 are not targeted this run.
    results_df = pd.DataFrame({
        "literature_id": ["1"],
        "eco_marine": [1],
        "pr_bycatch": [1],
        "d_biology": [0],
    })

    patched, n_updated = esc.apply_incremental_results(
        df_enriched, results_df, BINARY_COLS,
    )

    assert n_updated == 1
    row1 = patched.loc[patched["literature_id"] == "1"].iloc[0]
    assert row1["eco_marine"] == 1
    assert row1["pr_bycatch"] == 1
    assert row1["d_biology"] == 0
    assert row1["extraction_status"] == "re_extracted"
    # History preserved, not cleared, by design.
    assert row1["extraction_retracted_at"] == "2026-09-14T00:00:00+00:00"
    assert row1["extraction_retracted_reason"] == "misfiled PDF"

    # Rows not targeted this run are untouched.
    row2 = patched.loc[patched["literature_id"] == "2"].iloc[0]
    assert pd.isna(row2["extraction_status"])
    row3 = patched.loc[patched["literature_id"] == "3"].iloc[0]
    assert row3["eco_marine"] == 1


def test_reextraction_does_not_touch_other_still_retracted_rows():
    """Two retracted rows; only one is targeted this run. The one left
    behind must still have NULLs, not get swept into the 0-fill
    normalisation that runs as part of the same patch."""
    df_enriched = pd.DataFrame({
        "literature_id": ["1", "2"],
        "eco_marine": pd.array([None, None], dtype="Int64"),
        "extraction_status": ["retracted_wrong_pdf", "retracted_wrong_pdf"],
        "extraction_retracted_at": ["2026-09-14T00:00:00+00:00"] * 2,
        "extraction_retracted_reason": ["misfiled PDF"] * 2,
    })
    results_df = pd.DataFrame({"literature_id": ["1"], "eco_marine": [1]})

    patched, n_updated = esc.apply_incremental_results(
        df_enriched, results_df, ["eco_marine"],
    )

    assert n_updated == 1
    row1 = patched.loc[patched["literature_id"] == "1"].iloc[0]
    assert row1["eco_marine"] == 1
    assert row1["extraction_status"] == "re_extracted"

    row2 = patched.loc[patched["literature_id"] == "2"].iloc[0]
    assert pd.isna(row2["eco_marine"]), "untouched retracted row must keep its NULL"
    assert row2["extraction_status"] == "retracted_wrong_pdf"


def test_reextraction_works_when_extraction_status_column_absent():
    """A parquet with no extraction_status column at all (pre-dates the
    retraction feature) must still merge results in without erroring."""
    df_enriched = pd.DataFrame({
        "literature_id": ["1"],
        "eco_marine": [0],
    })
    results_df = pd.DataFrame({"literature_id": ["1"], "eco_marine": [1]})

    patched, n_updated = esc.apply_incremental_results(
        df_enriched, results_df, ["eco_marine"],
    )
    assert n_updated == 1
    assert patched.loc[0, "eco_marine"] == 1
    assert pd.isna(patched.loc[0, "extraction_status"])
