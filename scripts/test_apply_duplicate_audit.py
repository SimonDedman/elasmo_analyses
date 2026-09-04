#!/usr/bin/env python3
"""Tests for the audit applier.

Deletion is the irreversible half of this work and the files are synced, so
the behaviours pinned here are the refusals: anything that has changed since
the sheet was generated must survive.
"""

import sys
from pathlib import Path

import openpyxl
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import apply_duplicate_audit as app


@pytest.fixture
def pair(tmp_path):
    content = b"%PDF-1.4 shared volume" + b"x" * 2048
    keep = tmp_path / "Garman.1880.Synopsis.pdf"
    drop = tmp_path / "Garman.1880.Synopsis..pdf"
    keep.write_bytes(content)
    drop.write_bytes(content)
    return keep, drop


def make_workbook(tmp_path, keep, drop, decision):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "twins"
    ws.append(["group_id", "year", "keep_name", "delete_name", "difference",
               "confidence", "size_mb", "open", "decision", "notes",
               "sha256", "keep_path", "delete_path"])
    ws.append([1, 1880, keep.name, drop.name, "trailing full stop", "auto",
               0.1, "", decision, "", "abc123", str(keep), str(drop)])
    path = tmp_path / "audit.xlsx"
    wb.save(path)
    return path


def run(tmp_path, keep, drop, decision, apply=True):
    book = make_workbook(tmp_path, keep, drop, decision)
    actions, _ = app.plan(app.read_decisions(book), log=lambda *_: None)
    freed = app.execute(actions, apply=apply, log=lambda *_: None)
    return actions, freed


def test_ok_deletes_the_redundant_name(tmp_path, pair):
    keep, drop = pair
    actions, freed = run(tmp_path, keep, drop, "OK")
    assert actions[0]["status"] == "deleted"
    assert keep.exists() and not drop.exists()
    assert freed > 0


def test_swap_deletes_the_other_one(tmp_path, pair):
    keep, drop = pair
    actions, _ = run(tmp_path, keep, drop, "SWAP")
    assert actions[0]["status"] == "deleted"
    assert drop.exists() and not keep.exists()


@pytest.mark.parametrize("decision", ["KEEP BOTH", "", "  "])
def test_unapproved_rows_delete_nothing(tmp_path, pair, decision):
    keep, drop = pair
    actions, freed = run(tmp_path, keep, drop, decision)
    assert actions == [] and freed == 0
    assert keep.exists() and drop.exists()


def test_dry_run_deletes_nothing(tmp_path, pair):
    keep, drop = pair
    actions, freed = run(tmp_path, keep, drop, "OK", apply=False)
    assert actions[0]["status"] == "would delete"
    assert freed > 0
    assert keep.exists() and drop.exists()


def test_refuses_when_content_diverged_since_the_scan(tmp_path, pair):
    keep, drop = pair
    # An OCR pass landing between review and deletion makes them different
    # papers' worth of bytes; deleting either would lose work.
    keep.write_bytes(b"%PDF-1.4 freshly OCRed" + b"y" * 4096)
    actions, freed = run(tmp_path, keep, drop, "OK")
    assert actions[0]["status"].startswith("skipped")
    assert keep.exists() and drop.exists() and freed == 0


def test_refuses_when_the_survivor_is_missing(tmp_path, pair):
    keep, drop = pair
    keep.unlink()
    actions, _ = run(tmp_path, keep, drop, "OK")
    assert actions[0]["status"] == "skipped: survivor missing"
    assert drop.exists(), "never delete the last remaining copy"


def test_unrecognised_decision_is_reported_not_guessed(tmp_path, pair):
    keep, drop = pair
    book = make_workbook(tmp_path, keep, drop, "probably fine")
    actions, counts = app.plan(app.read_decisions(book), log=lambda *_: None)
    assert actions == []
    assert counts["invalid"] == 1
    assert keep.exists() and drop.exists()


def test_hardlinked_pair_is_still_deletable(tmp_path, pair):
    """After the sweep runs, twins share an inode. Deleting one name must
    still work and must leave the other readable."""
    keep, drop = pair
    drop.unlink()
    drop.hardlink_to(keep)
    actions, _ = run(tmp_path, keep, drop, "OK")
    assert actions[0]["status"] == "deleted"
    assert keep.exists() and keep.read_bytes().startswith(b"%PDF")
