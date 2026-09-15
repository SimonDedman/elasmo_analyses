#!/usr/bin/env python3
"""Tests for the three HIGH-risk papers_data.json writers migrated onto
lib.papers_data_io.mutate() on 2026-09-14 (outputs/sync_defects_2026-09-14/):

1. acquire_cascade.py's main() loop -- used to write back a whole `queue`
   copy loaded at the top of the run, hours before a long batch finished.
   Now applies only this run's per-literature_id field changes
   (apply_run_updates / flush_run_updates) to a freshly re-read list.
   2026-09-14 follow-up: the first version of this fix stored a
   REFERENCE to the whole row dict in pending_updates, so a flush still
   stamped every one of its keys (including fields the cascade never
   touched, e.g. findspot) back onto the fresh row, reverting whatever a
   concurrent writer had set there -- and if the row's title (part of
   mutate()'s identity key) had also changed concurrently, the write
   raised RuntimeError instead. Fixed by snapshotting the row with
   copy.deepcopy() before run_cascade_on_paper() runs and storing only
   the DIFF (_row_diff / record_run_update) of what actually changed.
2. ingest_pdfs.update_papers_data_json() -- used to load-filter-write with
   no lock. Now goes through mutate(allow_deletions=True), with the id/DOI
   match sets built before the lock and the filter applied to the fresh
   in-lock list.
3. regenerate_papers_data.py's main() -- a genuine whole-file regeneration
   (every kept row gets a fresh consecutive id), so it holds the lock and
   re-runs its filter on the list mutate() re-reads, rather than writing
   back a list read before the (slow) PDF-library scan.

Each test uses a temp papers_data.json file with both papers_data_io's and
the target module's path constants monkeypatched onto it, per the
concurrent-writer scenario: a row appears on disk (added by "another
process") between when a script builds its intended changes and when it
takes the lock, and must survive the write.

Run: python3 -m pytest tests/test_papers_data_writers.py -q
"""

import copy
import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import acquire_cascade as ac              # noqa: E402
import ingest_pdfs as ing                 # noqa: E402
import regenerate_papers_data as regen    # noqa: E402
from lib import papers_data_io            # noqa: E402


def _write(path, rows):
    path.write_text(json.dumps(rows), encoding="utf-8")


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def queue_file(tmp_path, monkeypatch):
    """A temp papers_data.json, with every writer's path constant repointed."""
    f = tmp_path / "papers_data.json"
    _write(f, [
        {"id": 1, "literature_id": "100", "title": "Alpha", "doi": "10.1/a",
         "last_status": "queued"},
        {"id": 2, "literature_id": "200", "title": "Beta", "doi": "10.1/b",
         "last_status": "queued"},
        {"id": 3, "literature_id": "300", "title": "Gamma", "doi": "10.1/c",
         "last_status": "queued"},
    ])
    monkeypatch.setattr(papers_data_io, "PAPERS_DATA", f)
    monkeypatch.setattr(papers_data_io, "LOCK_FILE", tmp_path / "lock")
    monkeypatch.setattr(ac, "QUEUE", f)
    monkeypatch.setattr(ing, "PAPERS_DATA_JSON", f)
    monkeypatch.setattr(regen, "QUEUE", f)
    return f


# ---------------------------------------------------------------------------
# 1. acquire_cascade.py: apply_run_updates / flush_run_updates
# ---------------------------------------------------------------------------
class TestAcquireCascadeWriteback:
    def test_intended_updates_applied(self, queue_file):
        # Simulate run_cascade_on_paper() having mutated two in-memory paper
        # dicts, as the main() loop would collect them into pending_updates.
        updates = {
            "100": {"literature_id": "100", "title": "Alpha", "doi": "10.1/a-found",
                    "last_status": "acquired_unpaywall", "cascade_stage": "unpaywall_oa",
                    "cascade_checked": True},
            "200": {"literature_id": "200", "title": "Beta", "doi": "10.1/b",
                    "last_status": "needs_library", "cascade_stage": "needs_library",
                    "cascade_checked": True},
        }
        applied, missing = ac.flush_run_updates(updates)
        assert applied == 2 and missing == []

        rows = {r["literature_id"]: r for r in _read(queue_file)}
        assert rows["100"]["doi"] == "10.1/a-found"
        assert rows["100"]["last_status"] == "acquired_unpaywall"
        assert rows["100"]["cascade_checked"] is True
        assert rows["200"]["last_status"] == "needs_library"
        # Row untouched by this run's updates is unchanged.
        assert rows["300"] == {"id": 3, "literature_id": "300", "title": "Gamma",
                               "doi": "10.1/c", "last_status": "queued"}

    def test_unrelated_rows_untouched(self, queue_file):
        before = _read(queue_file)[2]  # literature_id 300
        ac.flush_run_updates({"100": {"literature_id": "100", "last_status": "x"}})
        after = {r["literature_id"]: r for r in _read(queue_file)}["300"]
        assert after == before

    def test_concurrent_add_survives(self, queue_file):
        # Another process (e.g. the SR sync) appends a row after this run
        # built its pending_updates dict but before it reaches the lock.
        data = _read(queue_file)
        data.append({"id": 4, "literature_id": "400", "title": "Delta From Sync",
                     "doi": "", "last_status": "queued"})
        _write(queue_file, data)

        applied, missing = ac.flush_run_updates(
            {"100": {"literature_id": "100", "last_status": "acquired_scihub"}})

        rows = {r["literature_id"]: r for r in _read(queue_file)}
        assert applied == 1
        assert "400" in rows and rows["400"]["title"] == "Delta From Sync"
        assert rows["100"]["last_status"] == "acquired_scihub"

    def test_row_removed_concurrently_is_reported_missing_not_readded(self, queue_file):
        # Another process (e.g. finalize_acquisitions filing the paper into
        # the corpus) removes row 200 before this run's flush reaches the
        # lock. Our stale copy of it must not be resurrected.
        data = [r for r in _read(queue_file) if r["literature_id"] != "200"]
        _write(queue_file, data)

        applied, missing = ac.flush_run_updates(
            {"100": {"literature_id": "100", "last_status": "x"},
             "200": {"literature_id": "200", "last_status": "would_be_lost"}})

        assert applied == 1
        assert missing == ["200"]
        rows = {r["literature_id"] for r in _read(queue_file)}
        assert "200" not in rows

    def test_empty_updates_is_a_noop_and_does_not_touch_file(self, queue_file):
        before_mtime = queue_file.stat().st_mtime_ns
        applied, missing = ac.flush_run_updates({})
        assert applied == 0 and missing == []
        assert queue_file.stat().st_mtime_ns == before_mtime

    def test_apply_run_updates_merges_without_dropping_other_fields(self):
        # A fresh row may carry fields the stale in-memory copy never had
        # (e.g. added by a schema migration on another writer's branch).
        # update() must merge onto it, not replace it.
        fresh = [{"literature_id": "100", "title": "Alpha", "doi": "10.1/a",
                  "extra_field_from_elsewhere": "keep-me"}]
        applied, missing = ac.apply_run_updates(
            fresh, {"100": {"literature_id": "100", "last_status": "acquired_unpaywall"}})
        assert applied == 1 and missing == []
        assert fresh[0]["extra_field_from_elsewhere"] == "keep-me"
        assert fresh[0]["last_status"] == "acquired_unpaywall"


# ---------------------------------------------------------------------------
# 1b. acquire_cascade.py: the deep-copy/diff fix for the whole-row-reference
#     defect found in review on 2026-09-14 -- record_run_update / _row_diff.
# ---------------------------------------------------------------------------
class TestRecordRunUpdateDiffing:
    def test_row_diff_only_changed_and_added_keys(self):
        before = {"literature_id": "1", "title": "T", "doi": "", "findspot": "J"}
        after = {"literature_id": "1", "title": "T", "doi": "10.1/x", "findspot": "J"}
        assert ac._row_diff(before, after) == {"doi": "10.1/x"}

    def test_row_diff_detects_deletions_via_sentinel(self):
        before = {"a": 1, "b": 2}
        after = {"a": 1}
        assert ac._row_diff(before, after) == {"b": ac._DELETED}

    def test_apply_run_updates_pops_key_on_deletion_sentinel(self, queue_file):
        # "doi" (not "title") -- mutate()'s row-identity key is
        # (literature_id, title[:80]), so deleting title would itself
        # trip the vanished-row check this fix is meant to avoid; that
        # interaction is exercised deliberately in the whole-row-storage
        # regression test below, not here.
        applied, missing = ac.flush_run_updates({"100": {"doi": ac._DELETED}})
        assert applied == 1 and missing == []
        rows = {r["literature_id"]: r for r in _read(queue_file)}
        assert "doi" not in rows["100"]

    def test_record_run_update_warns_on_field_outside_cascade_owned_set(self):
        before = {"literature_id": "1", "title": "T", "doi": ""}
        after = {"literature_id": "1", "title": "T", "doi": "10.1/x", "notes": "surprise"}
        pending: dict = {}
        warnings = []
        ac.record_run_update(pending, before, after, log_unexpected=warnings.append)
        assert warnings and "notes" in warnings[0]
        # Still written, just flagged -- see CASCADE_OWNED_FIELDS docstring.
        assert pending["1"] == {"doi": "10.1/x", "notes": "surprise"}

    def test_record_run_update_no_diff_leaves_pending_empty(self):
        row = {"literature_id": "1", "title": "T", "doi": "10.1/x"}
        pending: dict = {}
        ac.record_run_update(pending, copy.deepcopy(row), row)
        assert pending == {}

    def test_record_run_update_merges_repeated_id_within_one_run(self):
        pending: dict = {}
        b1 = {"literature_id": "1", "doi": ""}
        a1 = {"literature_id": "1", "doi": "10.1/x"}
        ac.record_run_update(pending, b1, a1)
        b2 = {"literature_id": "1", "doi": "10.1/x"}
        a2 = {"literature_id": "1", "doi": "10.1/x", "last_status": "needs_library"}
        ac.record_run_update(pending, b2, a2)
        assert pending["1"] == {"doi": "10.1/x", "last_status": "needs_library"}

    def test_diff_survives_concurrent_edit_to_untouched_field_and_title(self, queue_file):
        """The critical defect (2026-09-14 review): pending_updates used to
        store a REFERENCE to the whole row dict loaded at the top of
        main(), so flushing stamped every one of ITS keys back onto the
        fresh row -- reverting a concurrently-set field the cascade never
        touched (findspot), and, if the row's title (part of mutate()'s
        identity key) had also changed concurrently, making mutate() raise
        RuntimeError instead of writing. This drives the real snapshot ->
        cascade-mutate -> diff -> flush sequence main() now uses and
        asserts both survive with no exception.
        """
        row = _read(queue_file)[0]  # literature_id "100"
        before = copy.deepcopy(row)

        # run_cascade_on_paper() mutates the SAME dict object in place,
        # touching only cascade-owned fields.
        row["doi"] = "10.1/a-found"
        row["last_status"] = "acquired_unpaywall"
        row["cascade_stage"] = "unpaywall_oa"
        row["cascade_checked"] = True

        pending: dict = {}
        ac.record_run_update(pending, before, row)
        assert set(pending["100"]) == {"doi", "last_status", "cascade_stage",
                                       "cascade_checked"}

        # Meanwhile another writer edits an untouched field AND the title
        # (mutate()'s row-identity key) on disk, before this run flushes.
        data = _read(queue_file)
        data[0]["findspot"] = "Journal of Concurrent Writes, 12, 1-9"
        data[0]["title"] = "Alpha, Revised Title"
        _write(queue_file, data)

        applied, missing = ac.flush_run_updates(pending)  # must not raise

        assert applied == 1 and missing == []
        after = {r["literature_id"]: r for r in _read(queue_file)}["100"]
        assert after["findspot"] == "Journal of Concurrent Writes, 12, 1-9"
        assert after["title"] == "Alpha, Revised Title"
        assert after["doi"] == "10.1/a-found"
        assert after["last_status"] == "acquired_unpaywall"
        assert after["cascade_checked"] is True

    def test_whole_row_storage_would_have_failed_this_test(self, queue_file):
        """Proves the regression test above actually exercises the bug: with
        pending_updates storing the WHOLE row object (the pre-fix shape),
        the same scenario either silently reverts findspot or raises
        RuntimeError from mutate()'s vanished-row check -- it does not
        pass quietly. Uses apply_run_updates directly (bypassing the
        deep-copy/diff step) to reconstruct the old behaviour without
        touching the production code path.
        """
        row = _read(queue_file)[0]
        row["doi"] = "10.1/a-found"
        row["last_status"] = "acquired_unpaywall"
        row["cascade_stage"] = "unpaywall_oa"
        row["cascade_checked"] = True
        # Old code: pending_updates[lid] = paper (whole row, not a diff).
        old_style_pending = {"100": row}

        data = _read(queue_file)
        data[0]["findspot"] = "Journal of Concurrent Writes, 12, 1-9"
        data[0]["title"] = "Alpha, Revised Title"
        _write(queue_file, data)

        with pytest.raises(RuntimeError):
            # mutate()'s row-key is (literature_id, title[:80]); the old
            # whole-row write includes the STALE title "Alpha", which no
            # longer matches the fresh row's edited title, so mutate()
            # believes the row the run started with has vanished.
            ac.flush_run_updates(old_style_pending)


# ---------------------------------------------------------------------------
# 2. ingest_pdfs.update_papers_data_json
# ---------------------------------------------------------------------------
class TestIngestPdfsWriteback:
    def test_removes_matched_by_id_and_doi(self, queue_file):
        removed = ing.update_papers_data_json(
            copied_ids={"100"}, copied_dois={"10.1/b"}, timestamp="ts", source_label="test")
        assert removed == 2
        rows = {r["literature_id"] for r in _read(queue_file)}
        assert rows == {"300"}

    def test_unmatched_rows_untouched(self, queue_file):
        before = _read(queue_file)[2]
        ing.update_papers_data_json({"100"}, set(), "ts", "test")
        after = {r["literature_id"]: r for r in _read(queue_file)}["300"]
        assert after == before

    def test_no_candidates_does_not_touch_file(self, queue_file):
        before_mtime = queue_file.stat().st_mtime_ns
        removed = ing.update_papers_data_json(set(), set(), "ts", "test")
        assert removed == 0
        assert queue_file.stat().st_mtime_ns == before_mtime

    def test_concurrent_add_survives(self, queue_file):
        # A row lands (e.g. from the cascade) between this ingest run
        # building its match sets and taking the lock.
        data = _read(queue_file)
        data.append({"id": 4, "literature_id": "400", "title": "From Cascade", "doi": ""})
        _write(queue_file, data)

        removed = ing.update_papers_data_json({"100"}, set(), "ts", "test")

        rows = {r["literature_id"] for r in _read(queue_file)}
        assert removed == 1
        assert "400" in rows and "100" not in rows

    def test_float_style_id_matches(self, queue_file):
        data = _read(queue_file)
        data.append({"id": 5, "literature_id": "500.0", "title": "Float Id", "doi": ""})
        _write(queue_file, data)
        removed = ing.update_papers_data_json({"500"}, set(), "ts", "test")
        assert removed == 1
        assert "500.0" not in {r["literature_id"] for r in _read(queue_file)}


# ---------------------------------------------------------------------------
# 3. regenerate_papers_data.py's main(): a locked whole-file regeneration
# ---------------------------------------------------------------------------
class TestRegenerateWriteback:
    def _run_locked_regeneration(self, pdf_idx):
        """The inner body of main()'s non-dry-run branch, exercised directly
        (main() itself is argparse/CLI plumbing, not worth invoking here)."""
        with regen._papers_data_mutate(allow_deletions=True) as queue:
            kept, removed = regen.filter_queue(queue, pdf_idx)
            for i, entry in enumerate(kept, start=1):
                entry["id"] = i
            queue[:] = kept
        return kept, removed

    def test_matched_entries_removed_and_ids_reassigned(self, queue_file):
        # An index entry that matches row 100 (surname+year+title overlap).
        pdf_idx = {("alpha", "2020"): [{"alpha", "paper"}]}
        data = _read(queue_file)
        data[0].update(authors="Alpha, A.", year="2020", title="An Alpha Paper")
        _write(queue_file, data)

        kept, removed = self._run_locked_regeneration(pdf_idx)

        assert {r["literature_id"] for r in removed} == {"100"}
        rows = _read(queue_file)
        assert {r["literature_id"] for r in rows} == {"200", "300"}
        # Reassigned to a dense, consecutive id.
        assert sorted(r["id"] for r in rows) == [1, 2]

    def test_no_matches_keeps_everything(self, queue_file):
        kept, removed = self._run_locked_regeneration(pdf_idx={})
        assert removed == []
        rows = _read(queue_file)
        assert {r["literature_id"] for r in rows} == {"100", "200", "300"}

    def test_concurrent_add_of_an_unmatched_row_survives(self, queue_file):
        # A row appears after this call's inputs (pdf_idx) were built but
        # before the lock is taken -- decided in _run_locked_regeneration()
        # against a list the lock re-reads, not the list read earlier.
        data = _read(queue_file)
        data.append({"id": 4, "literature_id": "400", "title": "From Sync",
                     "authors": "Zed, Z.", "year": "2026"})
        _write(queue_file, data)

        kept, removed = self._run_locked_regeneration(pdf_idx={})

        rows = {r["literature_id"] for r in _read(queue_file)}
        assert "400" in rows
        assert rows == {"100", "200", "300", "400"}

    def test_concurrent_add_of_a_matched_row_is_also_removed(self, queue_file):
        # The concurrently-added row happens to match the PDF index too --
        # it should be judged on its own merits, not skipped just because
        # it wasn't part of the list this run originally saw.
        pdf_idx = {("zed", "2026"): [{"zed", "paper"}]}
        data = _read(queue_file)
        data.append({"id": 4, "literature_id": "400", "title": "A Zed Paper",
                     "authors": "Zed, Z.", "year": "2026"})
        _write(queue_file, data)

        kept, removed = self._run_locked_regeneration(pdf_idx)

        assert {r["literature_id"] for r in removed} == {"400"}
        rows = {r["literature_id"] for r in _read(queue_file)}
        assert rows == {"100", "200", "300"}
