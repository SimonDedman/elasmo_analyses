#!/usr/bin/env python3
"""Tests for scripts/retract_wrong_pdf_extractions.py on a small synthetic parquet.

Covers: dry-run changes nothing; --apply nulls exactly the target rows;
--restore round-trips values; --apply is idempotent; a count mismatch
refuses (and leaves the file untouched).

Run: python3 -m pytest tests/test_retract_wrong_pdf.py -q
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import retract_wrong_pdf_extractions as rw  # noqa: E402

SYNTH_COLUMNS = ["eco_marine", "pr_bycatch", "d_biology", "imp_quantified", "eco_1_guess"]


def _make_synthetic_parquet(path: Path) -> pd.DataFrame:
    """5 rows: ids 1,2,3,4,4 (4 duplicated, mirrors the real corpus's
    duplicate-row records), id 5 absent from the target list entirely."""
    df = pd.DataFrame({
        "literature_id": ["1", "2", "3", "4", "4"],
        "title": ["A", "B", "C", "D", "D"],
        "eco_marine": [1, 0, 1, 1, 1],
        "pr_bycatch": [0, 1, 0, 1, 1],
        "d_biology": [1, 1, 0, 0, 0],
        "imp_quantified": [True, False, False, True, True],
        "eco_1_guess": ["marine", None, "freshwater", "marine", "marine"],
    })
    df.to_parquet(path, index=False)
    return df


def _make_ids_csv(path: Path, ids: list[str]) -> None:
    pd.DataFrame({"literature_id": ids}).to_csv(path, index=False)


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _base_args(tmp_path: Path, target: Path, ids_csv: Path, **overrides) -> argparse.Namespace:
    defaults = dict(
        ids_csv=ids_csv,
        id_column="literature_id",
        reason="test retraction",
        targets=[target],
        apply=False,
        expected_ids=None,
        expected_rows=None,
        restore=None,
        rag=False,
        apply_rag=False,
    )
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


@pytest.fixture(autouse=True)
def isolate_retractions_dir(tmp_path, monkeypatch):
    """apply_run()/rag_apply() always write under the module-level
    RETRACTIONS_DIR constant, regardless of --targets. Point it at a tmp
    directory for every test so nothing lands in the real project's
    outputs/retractions/."""
    fake_dir = tmp_path / "_retractions"
    monkeypatch.setattr(rw, "RETRACTIONS_DIR", fake_dir)
    return fake_dir


@pytest.fixture()
def synth(tmp_path):
    target = tmp_path / "enriched.parquet"
    df = _make_synthetic_parquet(target)
    ids_csv = tmp_path / "ids.csv"
    _make_ids_csv(ids_csv, ["1", "4"])  # id 4 has 2 rows -> 3 rows total
    return target, ids_csv, df


def test_dry_run_changes_nothing(synth, capsys):
    target, ids_csv, _ = synth
    before_hash = _file_hash(target)

    args = _base_args(target.parent, target, ids_csv)
    ids = rw.load_ids(ids_csv, "literature_id")
    rw.dry_run(args, ids, SYNTH_COLUMNS)

    out = capsys.readouterr().out
    assert "ids matched:  2" in out
    assert "rows matched: 3" in out
    assert _file_hash(target) == before_hash, "dry run must not modify the target file"


def test_apply_nulls_exactly_target_rows(synth):
    target, ids_csv, original = synth
    ids = rw.load_ids(ids_csv, "literature_id")

    args = _base_args(target.parent, target, ids_csv, apply=True,
                       expected_ids=2, expected_rows=3)
    rw.apply_run(args, ids, SYNTH_COLUMNS)

    result = pd.read_parquet(target)
    # Untouched rows (id 2, id 3) keep their original values exactly.
    for idx, lid in [(1, "2"), (2, "3")]:
        for col in SYNTH_COLUMNS:
            orig = original.loc[idx, col]
            new = result.loc[idx, col]
            if pd.isna(orig):
                assert pd.isna(new)
            else:
                assert new == orig
        assert pd.isna(result.loc[idx, "extraction_status"])

    # Targeted rows (id 1, id 4 x2) are nulled across all synthetic columns.
    for idx in [0, 3, 4]:
        for col in SYNTH_COLUMNS:
            assert pd.isna(result.loc[idx, col]), f"row {idx} col {col} not nulled"
        assert result.loc[idx, "extraction_status"] == "retracted_wrong_pdf"
        assert result.loc[idx, "extraction_retracted_reason"] == "test retraction"
        assert pd.notna(result.loc[idx, "extraction_retracted_at"])


def test_apply_is_idempotent(synth):
    target, ids_csv, _ = synth
    ids = rw.load_ids(ids_csv, "literature_id")

    args = _base_args(target.parent, target, ids_csv, apply=True,
                       expected_ids=2, expected_rows=3)
    rw.apply_run(args, ids, SYNTH_COLUMNS)
    first = pd.read_parquet(target)
    first_ts = first.loc[0, "extraction_retracted_at"]

    # Re-run with the same inputs: must not error, must not change the
    # already-retracted rows' timestamp, and values stay null.
    rw.apply_run(args, ids, SYNTH_COLUMNS)
    second = pd.read_parquet(target)

    assert second.loc[0, "extraction_retracted_at"] == first_ts
    for idx in [0, 3, 4]:
        for col in SYNTH_COLUMNS:
            assert pd.isna(second.loc[idx, col])
        assert second.loc[idx, "extraction_status"] == "retracted_wrong_pdf"


def test_restore_round_trips_values(synth):
    target, ids_csv, original = synth
    ids = rw.load_ids(ids_csv, "literature_id")

    args = _base_args(target.parent, target, ids_csv, apply=True,
                       expected_ids=2, expected_rows=3)
    rw.apply_run(args, ids, SYNTH_COLUMNS)

    # Locate the snapshot apply_run() just wrote under the (monkeypatched,
    # tmp) RETRACTIONS_DIR rather than re-deriving its path.
    snapshot_path = _latest_snapshot()

    rw.restore_run(snapshot_path)
    restored = pd.read_parquet(target)

    for idx in range(len(original)):
        for col in SYNTH_COLUMNS:
            orig_val = original.loc[idx, col]
            new_val = restored.loc[idx, col]
            if pd.isna(orig_val):
                assert pd.isna(new_val)
            else:
                assert new_val == orig_val, f"row {idx} col {col}: {new_val!r} != {orig_val!r}"
        assert pd.isna(restored.loc[idx, "extraction_status"])
        assert pd.isna(restored.loc[idx, "extraction_retracted_at"])
        assert pd.isna(restored.loc[idx, "extraction_retracted_reason"])


def test_count_mismatch_refuses(synth):
    target, ids_csv, original = synth
    before_hash = _file_hash(target)
    ids = rw.load_ids(ids_csv, "literature_id")

    args = _base_args(target.parent, target, ids_csv, apply=True,
                       expected_ids=99, expected_rows=99)
    with pytest.raises(SystemExit):
        rw.apply_run(args, ids, SYNTH_COLUMNS)

    assert _file_hash(target) == before_hash, "a refused apply must not touch the file"


def test_apply_requires_expected_counts(synth):
    target, ids_csv, _ = synth
    before_hash = _file_hash(target)
    ids = rw.load_ids(ids_csv, "literature_id")

    args = _base_args(target.parent, target, ids_csv, apply=True)  # no expected_* set
    with pytest.raises(SystemExit):
        rw.apply_run(args, ids, SYNTH_COLUMNS)

    assert _file_hash(target) == before_hash


def _latest_snapshot() -> Path:
    run_dirs = sorted(rw.RETRACTIONS_DIR.glob("*"), key=lambda p: p.stat().st_mtime)
    assert run_dirs, "apply_run should have created a run directory under outputs/retractions"
    return run_dirs[-1] / "snapshot.json"
