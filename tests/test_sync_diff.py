#!/usr/bin/env python3
"""Tests for the SR sync's diff, master-CSV dedupe, and papers_data.json writers.

Pins the three defects fixed on 2026-09-14 (outputs/sync_defects_2026-09-14/):

1. diff_papers() treated only the parquet as "known", so papers already
   queued in papers_data.json were re-declared new on every run.
2. The master-CSV dedupe was an if/elif, so the DOI check was never reached
   whenever a literature_id column existed, and 89% of master rows have no id.
3. add_to_papers_data / remove_from_papers_data did a naive read-modify-write
   instead of going through lib.papers_data_io.mutate().

Run: python3 -m pytest tests/test_sync_diff.py -q
"""

import json
import logging
import sys
from pathlib import Path

import pandas as pd
import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import sync_shark_references as sync  # noqa: E402
from lib import papers_data_io  # noqa: E402

LOG = logging.getLogger("test_sync_diff")


def sr(lid, doi="", pdf_url="", title="", year=None):
    return {"literature_id": str(lid), "doi": doi, "pdf_url": pdf_url,
            "title": title, "year": year, "authors": "A, B. (2020)"}


# ---------------------------------------------------------------------------
# Defect 1: diff_papers
# ---------------------------------------------------------------------------
class TestDiffPapers:
    def run(self, papers, known_ids=(), known_dois=(), q_ids=(), q_dois=()):
        counts = {}
        new, needs = sync.diff_papers(papers, set(known_ids), set(known_dois),
                                      set(q_ids), set(q_dois), LOG, counts=counts)
        return ({p["literature_id"] for p in new},
                {p["literature_id"] for p in needs}, counts)

    def test_genuinely_new_is_new(self):
        new, needs, c = self.run([sr(1)])
        assert new == {"1"} and needs == set()
        assert c["new"] == 1 and c["known_queue_only"] == 0

    def test_queued_but_not_in_parquet_is_not_new(self):
        # The 2,642 case: on papers_data.json, absent from the parquet.
        new, needs, c = self.run([sr(2, pdf_url="http://x/a.pdf")], q_ids={"2"})
        assert new == set()
        assert needs == {"2"}
        assert c["known_queue_only"] == 1 and c["known_parquet"] == 0

    def test_queued_without_sr_link_is_neither(self):
        new, needs, c = self.run([sr(3)], q_ids={"3"})
        assert new == set() and needs == set()
        assert c["known_queue_only"] == 1

    def test_queued_matched_by_doi_only(self):
        new, needs, _ = self.run([sr(4, doi="https://doi.org/10.1/ABC.", pdf_url="u")],
                                 q_dois={"10.1/abc"})
        assert new == set() and needs == {"4"}

    def test_in_parquet_and_not_queued_is_held(self):
        new, needs, c = self.run([sr(5, pdf_url="u")], known_ids={"5"})
        assert new == set() and needs == set()
        assert c["known_parquet"] == 1

    def test_in_parquet_by_doi_and_queued_needs_pdf(self):
        new, needs, _ = self.run([sr(6, doi="10.2/x", pdf_url="u")],
                                 known_dois={"10.2/x"}, q_ids={"6"})
        assert new == set() and needs == {"6"}

    def test_float_style_id_matches(self):
        new, _, _ = self.run([sr("7.0")], known_ids={"7"})
        assert new == set()

    def test_counts_partition_sr_list(self):
        papers = [sr(1), sr(2, pdf_url="u"), sr(3), sr(5)]
        new, needs, c = self.run(papers, known_ids={"5"}, q_ids={"2", "3"})
        assert c["new"] + c["known_parquet"] + c["known_queue_only"] == len(papers)


# ---------------------------------------------------------------------------
# Defect 2: master CSV dedupe
# ---------------------------------------------------------------------------
@pytest.fixture
def master():
    # Mirrors the real file: bulk rows have no literature_id or `title` (the
    # title sits inside `full_text`); sync-appended rows have both.
    return pd.DataFrame([
        {"literature_id": None, "doi": "10.1016/j.rsma.2025.104664", "year": "2026",
         "citation": "New record of Rostroraja velezi", "title": None},
        {"literature_id": None, "doi": None, "year": "1998", "title": None,
         "authors": "Skomal, G. (1998)", "findspot": "Fishery Bulletin, 96, 1-10",
         # citation is title + findspot truncated, so only full_text yields the title
         "citation": "Growth of the blue shark in the North Atlantic. Fishery Bull",
         "full_text": "Skomal, G. (1998) Growth of the blue shark in the North Atlantic. "
                      "Fishery Bulletin, 96, 1-10"},
        {"literature_id": "34545", "doi": None, "year": "1920",
         "citation": None, "title": "Lehrbuch der Paläozoologie."},
        {"literature_id": None, "doi": None, "year": "2001",
         "citation": "Sharks.", "title": None},
    ])


class TestMasterCsvDedupe:
    def test_doi_checked_even_when_id_column_exists(self, master):
        # The if/elif bug: this row was appended again before the fix.
        new = pd.DataFrame([sr(90001, doi="https://doi.org/10.1016/J.RSMA.2025.104664")])
        out, reasons = sync.select_master_csv_appends(master, new)
        assert len(out) == 0 and reasons["doi"] == 1

    def test_id_match(self, master):
        out, reasons = sync.select_master_csv_appends(master, pd.DataFrame([sr("34545.0")]))
        assert len(out) == 0 and reasons["literature_id"] == 1

    def test_master_row_title_from_full_text(self, master):
        row = master.iloc[1].to_dict()
        assert sync.master_row_title(row) == "Growth of the blue shark in the North Atlantic."

    def test_title_year_against_bulk_row(self, master):
        new = pd.DataFrame([sr(90002, title="Growth of the Blue Shark in the North Atlantic.",
                               year=1998)])
        out, reasons = sync.select_master_csv_appends(master, new)
        assert len(out) == 0 and reasons["title_year"] == 1
        assert reasons["title_year_ids"] == ["90002"]

    def test_title_match_needs_same_year(self, master):
        new = pd.DataFrame([sr(90003, title="Growth of the blue shark in the North Atlantic",
                               year=2004)])
        out, _ = sync.select_master_csv_appends(master, new)
        assert len(out) == 1

    def test_short_titles_are_not_a_duplicate_signal(self, master):
        out, _ = sync.select_master_csv_appends(
            master, pd.DataFrame([sr(90004, title="Sharks", year=2001)]))
        assert len(out) == 1

    def test_genuinely_new_kept_and_batch_deduped(self, master):
        new = pd.DataFrame([sr(90005, doi="10.9/new"), sr(90005, doi="10.9/new"),
                            sr(90006, doi="10.9/new")])
        out, reasons = sync.select_master_csv_appends(master, new)
        assert list(out["literature_id"]) == ["90005"]
        assert reasons["within_batch"] == 2

    def test_plausibility(self):
        assert sync.check_append_plausible(10, 20, LOG, limit=50) == ""
        assert "IMPLAUSIBLE" in sync.check_append_plausible(60, 100, LOG, limit=50)

    def test_title_year_with_differing_dois_is_not_duplicate(self, master):
        m = pd.concat([master, pd.DataFrame([
            {"literature_id": None, "doi": "10.1/comment", "year": "2021", "title": None,
             "full_text": "X, A. (2021) Early Miocene extinction in pelagic sharks revisited. J",
             "authors": "X, A. (2021)", "findspot": "J"}])], ignore_index=True)
        same_title = "Early Miocene extinction in pelagic sharks revisited."
        out, r = sync.select_master_csv_appends(
            m, pd.DataFrame([sr(90020, doi="10.1/reply", title=same_title, year=2021)]))
        assert len(out) == 1 and r["title_year"] == 0
        # With no DOI on the new row the title+year key still catches it
        out, r = sync.select_master_csv_appends(
            m, pd.DataFrame([sr(90021, title=same_title, year=2021)]))
        assert len(out) == 0 and r["title_year"] == 1

    def test_differing_dois_within_batch_both_kept(self, master):
        t = "A long enough title about blue sharks"
        out, _ = sync.select_master_csv_appends(master, pd.DataFrame([
            sr(90030, doi="10.1/a", title=t, year=2020),
            sr(90031, doi="10.1/b", title=t, year=2020)]))
        assert len(out) == 2

    def test_generic_titles_are_not_a_duplicate_signal(self):
        assert sync._title_year_key("Comment on an early Miocene extinction in pelagic sharks",
                                    2021) == ""
        assert sync._title_year_key("Erratum to: growth of the blue shark", 1999) == ""

    def test_implausible_append_reaches_stats_and_summary(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sync, "MASTER_CSV_DIR", tmp_path)
        monkeypatch.setattr(sync, "MASTER_CSV_PLAUSIBLE_APPEND", 2)
        pd.DataFrame([{"literature_id": "1", "doi": "10.0/x", "year": "2000"}]).to_csv(
            tmp_path / "shark_references_complete_20260108.csv", index=False)
        stats = {"errors": []}
        n = sync.append_to_master_csv([sr(i, doi=f"10.9/{i}") for i in range(5, 10)], LOG,
                                      errors=stats["errors"])
        assert n == 5
        assert len(stats["errors"]) == 1 and stats["errors"][0].startswith("IMPLAUSIBLE")
        full = {k: 0 for k in ("sr_total", "known_total", "needs_pdf_total", "new_found",
                               "details_fetched", "pdfs_downloaded", "pdfs_new", "pdfs_known",
                               "pdf_failures", "csv_appended", "json_removed",
                               "feedback_count", "crawl_errors")}
        full.update(runtime="0:00:01", errors=stats["errors"])
        short, long = sync.build_summary(full)
        assert "implausible master CSV append" in short
        assert "IMPLAUSIBLE master CSV append" in long

    def test_append_to_master_csv_returns_written_count(self, master, tmp_path, monkeypatch):
        monkeypatch.setattr(sync, "MASTER_CSV_DIR", tmp_path)
        f = tmp_path / "shark_references_complete_20260108.csv"
        master.to_csv(f, index=False)
        n = sync.append_to_master_csv(
            [sr(90010, doi="10.1016/j.rsma.2025.104664"), sr(90011, doi="10.9/z")], LOG)
        assert n == 1
        assert len(pd.read_csv(f, dtype=str)) == len(master) + 1


# ---------------------------------------------------------------------------
# Item 3: papers_data.json writers go through mutate()
# ---------------------------------------------------------------------------
@pytest.fixture
def queue(tmp_path, monkeypatch):
    f = tmp_path / "papers_data.json"
    f.write_text(json.dumps([
        {"id": 1, "literature_id": "100", "title": "Kept"},
        {"id": 2, "literature_id": "200.0", "title": "Downloaded"},
    ]))
    monkeypatch.setattr(papers_data_io, "PAPERS_DATA", f)
    monkeypatch.setattr(papers_data_io, "LOCK_FILE", tmp_path / "lock")
    monkeypatch.setattr(sync, "PAPERS_DATA", f)
    return f


class TestPapersDataWriters:
    def test_add_uses_lock_and_skips_existing(self, queue, monkeypatch):
        calls = []
        real = sync._papers_data_mutate
        monkeypatch.setattr(sync, "_papers_data_mutate",
                            lambda **kw: calls.append(kw) or real(**kw))
        n = sync.add_to_papers_data([sr(100), sr(300), sr(400), sr(300)], {"400"}, LOG)
        rows = json.loads(queue.read_text())
        assert n == 1 and calls == [{}]
        assert [r["literature_id"] for r in rows] == ["100", "200.0", "300"]
        assert len(list(queue.parent.glob("papers_data.backup-*.json"))) == 1

    def test_remove_normalises_ids_and_counts(self, queue):
        n = sync.remove_from_papers_data({"200"}, LOG)
        rows = json.loads(queue.read_text())
        assert n == 1 and [r["literature_id"] for r in rows] == ["100"]

    def test_add_nothing_to_do_does_not_touch_file(self, queue):
        before = queue.stat().st_mtime_ns
        assert sync.add_to_papers_data([sr(100)], {"100"}, LOG) == 0
        assert queue.stat().st_mtime_ns == before

    def test_add_sees_rows_written_by_another_process(self, queue, monkeypatch):
        # A row appears on disk after the caller built its list: the check
        # inside the lock must see it and neither duplicate nor erase it.
        data = json.loads(queue.read_text())
        data.append({"id": 3, "literature_id": "300", "title": "From the cascade"})
        queue.write_text(json.dumps(data))
        n = sync.add_to_papers_data([sr(300), sr(500)], set(), LOG)
        rows = json.loads(queue.read_text())
        assert n == 1
        assert [r["literature_id"] for r in rows] == ["100", "200.0", "300", "500"]


# ---------------------------------------------------------------------------
# Phase 5b: which downloaded papers are propagated, and queue removal by DOI
# ---------------------------------------------------------------------------
class TestPhase5bPlan:
    def ids(self, papers):
        return [p["literature_id"] for p in papers]

    def test_selection(self):
        new = [sr(1), sr(2)]                              # 1 downloaded, 2 not
        needs = [
            sr(10, doi="10.5/q", title="Queue only paper about skates"),
            sr(11, doi="10.5/held", title="Diet of the blue shark off Portugal", year=2010),
            sr(12),                                       # in parquet by id
            sr(13),                                       # queue-only, not downloaded
        ]
        rows = {"10.5/held": [("500001", "Diet of the blue shark off Portugal.", "2010")]}
        plan = sync.plan_phase5b(new, needs, {"1", "10", "11", "12.0"},
                                 known_ids={"12", "500001"}, known_dois={"10.5/held"},
                                 parquet_doi_rows=rows)
        assert self.ids(plan["new_to_propagate"]) == ["1"]
        assert self.ids(plan["queue_only_to_propagate"]) == ["10"]
        assert self.ids(plan["held_by_doi"]) == ["11"]
        assert plan["doi_conflict_review"] == []

    def test_doi_only_in_parquet_single_matching_row_is_held(self):
        # Parquet row 500001 carries DOI D with the same title; SR lists the
        # paper under its SR id; papers_data queues it.
        needs = [sr(35001, doi="https://doi.org/10.7/D", pdf_url="u",
                    title="Movements of juvenile white sharks in California", year=2019)]
        rows = {"10.7/d": [("500001", "Movements of juvenile white sharks in California.", 2019)]}
        plan = sync.plan_phase5b([], needs, {"35001"}, known_ids={"500001"},
                                 known_dois={"10.7/d"}, parquet_doi_rows=rows)
        assert plan["queue_only_to_propagate"] == []
        assert self.ids(plan["held_by_doi"]) == ["35001"]

    def test_doi_on_two_parquet_rows_is_flagged_not_propagated(self):
        needs = [sr(35002, doi="10.8/book", pdf_url="u",
                    title="Chapter three: rays of the Gulf", year=2005)]
        rows = {"10.8/book": [("500010", "Chapter one: sharks of the Gulf", 2005),
                              ("500011", "Chapter three: rays of the Gulf", 2005)]}
        plan = sync.plan_phase5b([], needs, {"35002"}, known_ids=set(),
                                 known_dois={"10.8/book"}, parquet_doi_rows=rows)
        assert plan["held_by_doi"] == [] and plan["queue_only_to_propagate"] == []
        assert self.ids(plan["doi_conflict_review"]) == ["35002"]
        # ...and it stays on the queue: Phase 5 does not remove it
        assert sync.phase5_removal_ids(plan, {"35002", "7"}) == {"7"}

    def test_doi_single_row_title_mismatch_is_flagged(self):
        needs = [sr(35003, doi="10.9/x", pdf_url="u", title="Age and growth of the tope", year=2001)]
        rows = {"10.9/x": [("500020", "Parasites of the thornback ray", 2001)]}
        plan = sync.plan_phase5b([], needs, {"35003"}, set(), {"10.9/x"}, rows)
        assert self.ids(plan["doi_conflict_review"]) == ["35003"]

    def test_no_title_evidence_is_flagged(self):
        plan = sync.plan_phase5b([], [sr(35004, doi="10.9/y", pdf_url="u")], {"35004"},
                                 set(), {"10.9/y"})
        assert self.ids(plan["doi_conflict_review"]) == ["35004"]


class TestRemoveByDoi:
    def add_rows(self, queue, rows):
        data = json.loads(queue.read_text())
        data.extend(rows)
        queue.write_text(json.dumps(data))

    def test_sibling_sharing_book_doi_survives(self, queue):
        self.add_rows(queue, [
            {"id": 3, "literature_id": "700001", "doi": "10.1/book",
             "title": "Chapter one: sharks of the Gulf", "year": 2005},
            {"id": 4, "literature_id": "700002", "doi": "10.1/book",
             "title": "Chapter two: rays of the Gulf", "year": 2005}])
        report = {}
        downloaded = [sr(700001, doi="10.1/book", title="Chapter one: sharks of the Gulf",
                         year=2005)]
        n = sync.remove_from_papers_data({"700001"}, LOG, downloaded_papers=downloaded,
                                         report=report)
        ids = [r["literature_id"] for r in json.loads(queue.read_text())]
        assert n == 1 and "700002" in ids and "700001" not in ids
        assert report["same_doi_kept"] == 1

    def test_shared_doi_kept_even_when_titles_agree(self, queue):
        # "part one"/"part two" tokenise identically (3-letter words drop out),
        # so only the doi_count == 1 guard stops both siblings being removed.
        self.add_rows(queue, [
            {"id": 3, "literature_id": "500001", "doi": "10.1/book",
             "title": "Sharks of the Gulf of California part one", "year": 2005},
            {"id": 4, "literature_id": "500002", "doi": "10.1/book",
             "title": "Sharks of the Gulf of California part two", "year": 2005}])
        report = {}
        downloaded = [sr(35001, doi="10.1/book", year=2005,
                         title="Sharks of the Gulf of California part one")]
        n = sync.remove_from_papers_data({"35001"}, LOG, downloaded_papers=downloaded,
                                         report=report)
        ids = [r["literature_id"] for r in json.loads(queue.read_text())]
        assert n == 0 and "500001" in ids and "500002" in ids
        assert report["same_doi_kept"] == 2

    def test_unique_doi_twin_with_matching_title_removed(self, queue):
        self.add_rows(queue, [{"id": 3, "literature_id": "500001", "doi": "10.7/D",
                               "title": "Movements of juvenile white sharks in California",
                               "year": 2019}])
        downloaded = [sr(35001, doi="10.7/d", year=2020,
                         title="Movements of juvenile white sharks in California.")]
        n = sync.remove_from_papers_data({"35001"}, LOG, downloaded_papers=downloaded)
        assert n == 1
        assert [r["literature_id"] for r in json.loads(queue.read_text())] == ["100", "200.0"]

    def test_unique_doi_title_mismatch_kept(self, queue):
        self.add_rows(queue, [{"id": 3, "literature_id": "500001", "doi": "10.7/D",
                               "title": "Parasites of the thornback ray", "year": 2019}])
        report = {}
        downloaded = [sr(35001, doi="10.7/d", title="Movements of juvenile white sharks",
                         year=2019)]
        assert sync.remove_from_papers_data({"35001"}, LOG, downloaded_papers=downloaded,
                                            report=report) == 0
        assert report["same_doi_kept"] == 1

    def test_unique_doi_year_mismatch_kept(self, queue):
        self.add_rows(queue, [{"id": 3, "literature_id": "500001", "doi": "10.7/D",
                               "title": "Movements of juvenile white sharks", "year": 1990}])
        downloaded = [sr(35001, doi="10.7/d", title="Movements of juvenile white sharks",
                         year=2019)]
        assert sync.remove_from_papers_data({"35001"}, LOG, downloaded_papers=downloaded) == 0

    def test_empty_doi_never_matches(self, queue):
        self.add_rows(queue, [{"id": 3, "literature_id": "300", "doi": "", "title": "Kept"}])
        downloaded = [sr(999, doi="", title="Kept")]
        assert sync.remove_from_papers_data({"999"}, LOG, downloaded_papers=downloaded) == 0
        assert len(json.loads(queue.read_text())) == 3

    def test_short_title_subset_is_not_agreement(self):
        # overlap over the longer title, so a two-word record doesn't match a long one
        assert not sync._same_paper("Chimaeras", 2010,
                                    "Field guide to sharks rays and chimaeras of Europe", 2010)
