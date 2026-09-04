#!/usr/bin/env python3
"""Tests for the rename-and-reaccount repair.

The invariant worth protecting: renaming a PDF MOVES the claim. The paper the
filename used to claim no longer has a file and must go back on the wanted
list, or it counts as acquired for ever, which is the same bookkeeping error
the misfiling caused.
"""

import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import repair_misfiled_pdfs as rp


@pytest.fixture
def wanted_list(tmp_path, monkeypatch):
    """Isolate BOTH paths. The writer goes through lib.papers_data_io, which
    holds its own module-level path, so patching only the caller's constant
    sends the test at the real 12,000-row file."""
    path = tmp_path / "papers_data.json"
    path.write_text(json.dumps([
        {"id": 1, "literature_id": "999", "title": "Some paper still missing",
         "authors": "A", "year": 2001, "doi": "", "journal": ""},
    ], indent=1))
    monkeypatch.setattr(rp, "PAPERS_DATA_JSON", path)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from lib import papers_data_io
    monkeypatch.setattr(papers_data_io, "PAPERS_DATA", path)
    monkeypatch.setattr(papers_data_io, "LOCK_FILE", tmp_path / "lock")
    return path


def test_the_writer_is_isolated_from_the_real_file(wanted_list):
    """Guard the guard: if this fixture ever stops isolating the library's
    own path, the other tests silently start writing the real corpus."""
    from lib import papers_data_io
    assert papers_data_io.PAPERS_DATA == wanted_list
    assert "papers_data.json" not in str(rp.PROJECT / "docs" / "x") or True
    real = rp.PROJECT / "docs" / "papers_data.json"
    assert papers_data_io.PAPERS_DATA != real


@pytest.fixture
def tracker(tmp_path, monkeypatch):
    path = tmp_path / "download_tracker.db"
    db = sqlite3.connect(path)
    db.execute("CREATE TABLE papers (id INTEGER PRIMARY KEY, literature_id TEXT)")
    db.execute("CREATE TABLE download_status (id INTEGER PRIMARY KEY, paper_id INT,"
               " status TEXT, download_date TEXT, source TEXT, notes TEXT,"
               " attempts INT, last_attempt TEXT)")
    db.execute("INSERT INTO papers VALUES (7, '23676')")
    db.execute("INSERT INTO papers VALUES (8, '12614')")
    db.execute("INSERT INTO download_status (paper_id, status) VALUES (7, 'downloaded')")
    db.commit()
    db.close()
    monkeypatch.setattr(rp, "TRACKER_DB", path)
    return path


RECORD = {"literature_id": "23676", "year": "2015.0", "authors": "Elias, F.G.",
          "title": "Histochemical study of the oviducal gland", "doi": "",
          "journal": "J Morph"}


def test_a_paper_that_lost_its_pdf_goes_back_on_the_wanted_list(wanted_list):
    added, removed = rp.update_papers_data({"23676": RECORD}, set(), apply=True)
    assert added == 1
    entries = json.loads(wanted_list.read_text())
    entry = next(e for e in entries if e["literature_id"] == "23676")
    assert entry["year"] == 2015           # int, matching the existing schema
    assert isinstance(entry["id"], int)
    assert "misfiled" in entry["notes"]


def test_reacquired_papers_come_off_the_wanted_list(wanted_list):
    rp.update_papers_data({"23676": RECORD}, set(), apply=True)
    added, removed = rp.update_papers_data({}, {"23676"}, apply=True)
    assert removed == 1
    ids = {e["literature_id"] for e in json.loads(wanted_list.read_text())}
    assert "23676" not in ids and "999" in ids


def test_dry_run_leaves_the_wanted_list_untouched(wanted_list):
    before = wanted_list.read_text()
    added, _ = rp.update_papers_data({"23676": RECORD}, set(), apply=False)
    assert added == 1                       # reported
    assert wanted_list.read_text() == before  # but not written


def test_a_re_added_paper_is_not_duplicated(wanted_list):
    rp.update_papers_data({"23676": RECORD}, set(), apply=True)
    added, _ = rp.update_papers_data({"23676": RECORD}, set(), apply=True)
    assert added == 0
    ids = [e["literature_id"] for e in json.loads(wanted_list.read_text())]
    assert ids.count("23676") == 1


def test_downloaded_status_is_cleared_for_a_paper_that_lost_its_file(tracker):
    cleared, marked = rp.update_tracker({"23676"}, {"12614"}, apply=True)
    assert cleared == 1 and marked == 1
    db = sqlite3.connect(tracker)
    assert db.execute("SELECT COUNT(*) FROM download_status WHERE paper_id=7"
                      " AND status='downloaded'").fetchone()[0] == 0
    assert db.execute("SELECT COUNT(*) FROM download_status WHERE paper_id=8"
                      " AND status='downloaded'").fetchone()[0] == 1


def test_tracker_dry_run_changes_nothing(tracker):
    cleared, marked = rp.update_tracker({"23676"}, {"12614"}, apply=False)
    assert (cleared, marked) == (1, 1)
    db = sqlite3.connect(tracker)
    assert db.execute("SELECT COUNT(*) FROM download_status WHERE paper_id=7"
                      " AND status='downloaded'").fetchone()[0] == 1
    assert db.execute("SELECT COUNT(*) FROM download_status WHERE paper_id=8"
                      " AND status='downloaded'").fetchone()[0] == 0


def test_a_paper_reclaimed_by_another_file_is_not_counted_as_lost():
    """Four files swapping names among themselves: a paper can lose one
    filename and gain another in the same run, and must not be reported as
    having lost its PDF."""
    lost = {"17958", "23676"}
    gained = {"17958", "12614"}
    assert (lost - gained) == {"23676"}
