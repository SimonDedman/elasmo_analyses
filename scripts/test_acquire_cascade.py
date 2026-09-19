#!/usr/bin/env python3
"""
test_acquire_cascade.py

Unit tests for acquire_cascade.py's pure logic: DOI recovery/extraction,
Unpaywall write-back, BHL eligibility, download-attempt gating, and the
step-ordering/short-circuit of the cascade itself. All network-touching
channel functions are monkeypatched/stubbed -- these tests make no HTTP
calls and touch no real files outside pytest's tmp_path.

Run:  python3 -m pytest scripts/test_acquire_cascade.py -v
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import acquire_cascade as ac


# ---------------------------------------------------------------------------
# extract_doi_from_text
# ---------------------------------------------------------------------------

def test_extract_doi_from_text_finds_doi_in_notes():
    text = "Found via correspondence, see doi:10.1016/j.jembe.2020.01.001 for detail."
    assert ac.extract_doi_from_text(text) == "10.1016/j.jembe.2020.01.001"


def test_extract_doi_from_text_returns_none_when_absent():
    assert ac.extract_doi_from_text("no identifier here") is None
    assert ac.extract_doi_from_text("") is None
    assert ac.extract_doi_from_text(None) is None


def test_extract_doi_from_text_strips_trailing_sentence_punctuation():
    text = "Available at https://doi.org/10.1007/s00227-019-3456-7."
    assert ac.extract_doi_from_text(text) == "10.1007/s00227-019-3456-7"


# ---------------------------------------------------------------------------
# recover_doi
# ---------------------------------------------------------------------------

def test_recover_doi_skips_if_already_has_doi():
    paper = {"doi": "10.1234/existing", "notes": "10.9999/should-not-be-used"}
    ctx = ac.make_ctx()
    assert ac.recover_doi(paper, ctx) is None


def test_recover_doi_extracts_from_notes_field():
    paper = {"doi": "", "notes": "duplicate of 10.1016/j.jembe.2020.01.001", "title": "x"}
    ctx = ac.make_ctx()
    assert ac.recover_doi(paper, ctx) == "10.1016/j.jembe.2020.01.001"


def test_recover_doi_extracts_from_oa_url_field():
    paper = {"doi": "", "oa_url": "https://doi.org/10.1007/s00227-019-3456-7", "title": "x"}
    ctx = ac.make_ctx()
    assert ac.recover_doi(paper, ctx) == "10.1007/s00227-019-3456-7"


def test_recover_doi_falls_back_to_crossref_lookup():
    paper = {"doi": "", "title": "Shark movement ecology", "authors": "Smith, J.", "year": 2020}
    ctx = ac.make_ctx(
        doi_lookup_crossref=lambda title, authors, year: {"doi": "10.1111/found-by-crossref"},
        doi_lookup_s2=lambda title, year: (_ for _ in ()).throw(AssertionError("should not reach S2")),
    )
    assert ac.recover_doi(paper, ctx) == "10.1111/found-by-crossref"


def test_recover_doi_falls_back_to_semantic_scholar_when_crossref_fails():
    paper = {"doi": "", "title": "Shark movement ecology", "authors": "Smith, J.", "year": 2020}
    ctx = ac.make_ctx(
        doi_lookup_crossref=lambda title, authors, year: None,
        doi_lookup_s2=lambda title, year: {"doi": "10.2222/found-by-s2"},
    )
    assert ac.recover_doi(paper, ctx) == "10.2222/found-by-s2"


def test_recover_doi_returns_none_when_all_channels_fail():
    paper = {"doi": "", "title": "Untraceable paper", "year": 2020}
    ctx = ac.make_ctx(
        doi_lookup_crossref=lambda title, authors, year: None,
        doi_lookup_s2=lambda title, year: None,
    )
    assert ac.recover_doi(paper, ctx) is None


def test_recover_doi_returns_none_without_title_or_notes():
    paper = {"doi": "", "notes": "", "oa_url": "", "title": ""}
    ctx = ac.make_ctx()
    assert ac.recover_doi(paper, ctx) is None


# ---------------------------------------------------------------------------
# unpaywall_writeback
# ---------------------------------------------------------------------------

def test_unpaywall_writeback_sets_oa_status_colour():
    paper = {"oa_status": "unknown", "oa_url": ""}
    record = {"oa_status": "green", "best_oa_location": None}
    ac.unpaywall_writeback(paper, record)
    assert paper["oa_status"] == "green"


def test_unpaywall_writeback_sets_pdf_url_when_present():
    paper = {"oa_status": "unknown", "oa_url": ""}
    record = {
        "oa_status": "gold",
        "best_oa_location": {"url_for_pdf": "https://example.org/paper.pdf"},
    }
    got = ac.unpaywall_writeback(paper, record)
    assert got is True
    assert paper["oa_url"] == "https://example.org/paper.pdf"
    assert paper["oa_status"] == "gold"


def test_unpaywall_writeback_returns_false_when_no_record():
    paper = {"oa_status": "unknown", "oa_url": ""}
    assert ac.unpaywall_writeback(paper, None) is False
    assert paper["oa_status"] == "unknown"   # untouched


def test_unpaywall_writeback_does_not_set_url_when_no_pdf():
    paper = {"oa_status": "unknown", "oa_url": ""}
    record = {"oa_status": "closed", "best_oa_location": None}
    got = ac.unpaywall_writeback(paper, record)
    assert got is False
    assert paper["oa_status"] == "closed"    # colour still written back
    assert paper["oa_url"] == ""             # no url to write


# ---------------------------------------------------------------------------
# is_bhl_eligible
# ---------------------------------------------------------------------------

def test_is_bhl_eligible_pre_1970():
    paper = {"year": 1955, "journal": "Some Random Journal"}
    assert ac.is_bhl_eligible(paper) is True


def test_is_bhl_eligible_taxonomy_journal_keyword():
    paper = {"year": 2015, "journal": "Journal of Vertebrate Paleontology"}
    assert ac.is_bhl_eligible(paper) is True


def test_is_bhl_eligible_false_for_modern_non_taxonomy():
    paper = {"year": 2015, "journal": "Marine Ecology Progress Series"}
    assert ac.is_bhl_eligible(paper) is False


# ---------------------------------------------------------------------------
# _attempt_download
# ---------------------------------------------------------------------------

def test_attempt_download_no_url_returns_no_url():
    called = []
    result = ac._attempt_download("", Path("/tmp/x.pdf"), lambda u, d: called.append(1) or True, dry_run=False)
    assert result == "no_url"
    assert called == []


def test_attempt_download_dry_run_returns_would_download_without_calling_downloader():
    called = []
    result = ac._attempt_download("http://x/y.pdf", Path("/tmp/x.pdf"),
                                   lambda u, d: called.append(1) or True, dry_run=True)
    assert result == "would_download"
    assert called == []   # downloader never invoked in dry-run


def test_attempt_download_calls_downloader_and_returns_downloaded():
    result = ac._attempt_download("http://x/y.pdf", Path("/tmp/x.pdf"), lambda u, d: True, dry_run=False)
    assert result == "downloaded"


def test_attempt_download_returns_failed_when_downloader_returns_false():
    result = ac._attempt_download("http://x/y.pdf", Path("/tmp/x.pdf"), lambda u, d: False, dry_run=False)
    assert result == "failed"


def test_attempt_download_returns_failed_when_downloader_raises():
    def boom(u, d):
        raise RuntimeError("network error")
    result = ac._attempt_download("http://x/y.pdf", Path("/tmp/x.pdf"), boom, dry_run=False)
    assert result == "failed"


# ---------------------------------------------------------------------------
# run_cascade_on_paper -- step ordering / short-circuit
# ---------------------------------------------------------------------------

def _base_ctx(tmp_path, **overrides):
    defaults = dict(
        doi_lookup_crossref=lambda title, authors, year: None,
        doi_lookup_s2=lambda title, year: None,
        unpaywall_fetch=lambda doi: None,
        oa_openalex=lambda doi, title, year: None,
        oa_semantic_scholar=lambda doi, title: None,
        download_pdf=lambda url, dest: True,
        bhl_search=lambda journal, year, title: None,
        bhl_download=lambda url, dest: (True, "downloaded"),
        resolve_publisher=lambda paper: "Test Publisher",
        oa_dir=tmp_path / "oa",
        bhl_dir=tmp_path / "bhl",
        dry_run=False,
    )
    defaults.update(overrides)
    return ac.make_ctx(**defaults)


def test_run_cascade_stops_at_unpaywall_when_pdf_found(tmp_path):
    paper = {"literature_id": "1", "doi": "10.1/abc", "title": "T", "year": 2020,
             "oa_status": "unknown", "oa_url": ""}
    ctx = _base_ctx(
        tmp_path,
        unpaywall_fetch=lambda doi: {"oa_status": "gold",
                                      "best_oa_location": {"url_for_pdf": "http://x/a.pdf"}},
        oa_openalex=lambda *a: (_ for _ in ()).throw(AssertionError("should not reach oa_trawl")),
    )
    result = ac.run_cascade_on_paper(paper, ctx)
    assert result["cascade_stage"] == "unpaywall"
    assert paper["last_status"] == "acquired_oa"
    assert paper["oa_status"] == "gold"
    assert paper["cascade_checked"] is True


def test_run_cascade_falls_through_to_oa_trawl_when_unpaywall_has_no_pdf():
    paper = {"literature_id": "2", "doi": "10.1/abc", "title": "T", "year": 2020,
             "oa_status": "unknown", "oa_url": ""}
    ctx = _base_ctx(
        Path("/tmp"),
        unpaywall_fetch=lambda doi: {"oa_status": "closed", "best_oa_location": None},
        oa_openalex=lambda doi, title, year: "http://x/b.pdf",
    )
    result = ac.run_cascade_on_paper(paper, ctx)
    assert result["cascade_stage"] == "oa_trawl_openalex"
    assert paper["last_status"] == "acquired_oa"


def test_run_cascade_bhl_only_triggers_for_eligible_papers():
    paper = {"literature_id": "3", "doi": "", "title": "Old paper", "year": 1930,
             "journal": "Bulletin of Something", "oa_status": "", "oa_url": ""}
    bhl_calls = []
    ctx = _base_ctx(
        Path("/tmp"),
        bhl_search=lambda journal, year, title: bhl_calls.append(1) or
            {"source": "archive.org", "match_type": "ia_journal_year", "identifier": "x", "url": "http://ia/x.pdf"},
    )
    result = ac.run_cascade_on_paper(paper, ctx)
    assert bhl_calls == [1]
    assert result["cascade_stage"] == "bhl"
    assert paper["last_status"] == "acquired_bhl"


def test_run_cascade_bhl_skipped_for_modern_non_taxonomy_paper():
    paper = {"literature_id": "4", "doi": "", "title": "Modern paper", "year": 2020,
             "journal": "Marine Ecology Progress Series", "oa_status": "", "oa_url": ""}
    bhl_calls = []
    ctx = _base_ctx(
        Path("/tmp"),
        bhl_search=lambda journal, year, title: bhl_calls.append(1) or None,
    )
    ac.run_cascade_on_paper(paper, ctx)
    assert bhl_calls == []   # never invoked -- not BHL-eligible


def test_run_cascade_needs_library_when_all_channels_fail():
    paper = {"literature_id": "5", "doi": "10.1/abc", "title": "T", "year": 2020,
             "journal": "Marine Ecology Progress Series", "oa_status": "", "oa_url": "",
             "publisher": ""}
    ctx = _base_ctx(Path("/tmp"))
    result = ac.run_cascade_on_paper(paper, ctx)
    assert result["cascade_stage"] == "needs_library"
    assert paper["last_status"] == "needs_library"
    assert paper["publisher"] == "Test Publisher"   # resolved + written back


def test_run_cascade_dry_run_does_not_call_downloader():
    called = []
    paper = {"literature_id": "6", "doi": "10.1/abc", "title": "T", "year": 2020,
             "oa_status": "unknown", "oa_url": ""}
    ctx = _base_ctx(
        Path("/tmp"),
        unpaywall_fetch=lambda doi: {"oa_status": "gold",
                                      "best_oa_location": {"url_for_pdf": "http://x/a.pdf"}},
        download_pdf=lambda url, dest: called.append(1) or True,
        dry_run=True,
    )
    result = ac.run_cascade_on_paper(paper, ctx)
    assert called == []
    assert result["cascade_stage"] == "would_unpaywall"
    assert paper["last_status"] == "would_acquire_oa"


def test_run_cascade_records_doi_before_and_after_for_reporting():
    paper = {"literature_id": "7", "doi": "", "title": "Traceable paper",
             "authors": "Smith, J.", "year": 2020, "oa_status": "", "oa_url": ""}
    ctx = _base_ctx(
        Path("/tmp"),
        doi_lookup_crossref=lambda title, authors, year: {"doi": "10.9/recovered"},
        unpaywall_fetch=lambda doi: None,
    )
    result = ac.run_cascade_on_paper(paper, ctx)
    assert result["doi_before"] == ""
    assert result["doi_after"] == "10.9/recovered"
    assert paper["doi"] == "10.9/recovered"


# ---------------------------------------------------------------------------
# select_pool -- resume-skip logic
# ---------------------------------------------------------------------------

def test_select_pool_skips_already_checked_papers_by_default():
    queue = [
        {"literature_id": "1", "cascade_checked": True},
        {"literature_id": "2", "cascade_checked": False},
        {"literature_id": "3"},
    ]
    pool = ac.select_pool(queue, recheck=False)
    assert [p["literature_id"] for p in pool] == ["2", "3"]


def test_select_pool_recheck_returns_everything():
    queue = [
        {"literature_id": "1", "cascade_checked": True},
        {"literature_id": "2", "cascade_checked": False},
    ]
    pool = ac.select_pool(queue, recheck=True)
    assert len(pool) == 2


# ---------------------------------------------------------------------------
# atomic_write_json / backup_queue -- safety around the master queue file
# ---------------------------------------------------------------------------

def test_atomic_write_json_replaces_content_and_leaves_no_tmp_file(tmp_path):
    target = tmp_path / "queue.json"
    target.write_text(json.dumps([{"a": 1}]))
    ac.atomic_write_json([{"a": 2}, {"b": 3}], target)
    assert json.loads(target.read_text()) == [{"a": 2}, {"b": 3}]
    assert not target.with_suffix(target.suffix + ".tmp").exists()


def test_backup_queue_copies_original_content(tmp_path):
    src = tmp_path / "queue.json"
    src.write_text(json.dumps([{"a": 1}]))
    backup_dir = tmp_path / "backups"
    backup_path = ac.backup_queue(src, backup_dir)
    assert backup_path.exists()
    assert json.loads(backup_path.read_text()) == [{"a": 1}]


def test_append_log_rows_honours_reassigned_module_log_path(tmp_path, monkeypatch):
    """Regression test: append_log_rows(rows) with no explicit path must
    write to whatever ac.LOG currently points at, not to a path captured
    once when the module was first imported. A mutable-default-argument
    bug here would silently write to the real outputs/cascade_log.csv
    even when the caller (or a test harness) has redirected ac.LOG."""
    fake_log = tmp_path / "redirected_log.csv"
    monkeypatch.setattr(ac, "LOG", fake_log)
    ac.append_log_rows([{
        "literature_id": "1", "doi_before": "", "doi_after": "",
        "oa_status_before": "", "oa_status_after": "",
        "cascade_stage": "needs_library", "last_status": "needs_library",
        "download_path": "",
    }])
    assert fake_log.exists(), (
        "append_log_rows() must honour the current ac.LOG value, "
        "not a stale import-time default"
    )


# ---------------------------------------------------------------------------
# lid-named staging and the deletion gate (2026-09-17 repair)
#
# The download push staged every fetch as "<literature_id>.pdf". finalize threw
# that id away, re-matched by title/author, and filed 11 correct downloads
# under other papers' names; on the EXISTS branch it deleted 8 correct
# downloads because an unrelated file already occupied the destination.
# ---------------------------------------------------------------------------

ROW_A = {"literature_id": "13330", "year": "1993",
         "authors": "Polovina, J.J. & Lau, B.B. (1993)",
         "title": "Temporal and spatial distribution of catches of tiger sharks, "
                  "Galeocerdo cuvier, in the pelagic longline fishery", "doi": ""}
ROW_B = {"literature_id": "3605", "year": "1992", "authors": "Randall, J.E. (1992)",
         "title": "Review of the biology of the tiger shark (Galeocerdo cuvier).",
         "doi": ""}

TEXT_A = ("Temporal and Spatial Distribution of Catches of Tiger Sharks, "
          "Galeocerdo cuvier, in the Pelagic Longline Fishery Around the "
          "Hawaiian Islands. Jeffrey J. Polovina and Bert B. Lau. Abstract. " * 3)


def test_identity_check_accepts_the_paper_named_by_the_staged_id():
    verdict, detail = ac.identity_check(TEXT_A, ROW_A)
    assert verdict is True, detail


ROW_C = {"literature_id": "11382", "year": "2004", "authors": "Bozzano, A. (2004)",
         "title": "Retinal specialisations in the dogfish Centroscymnus coelolepis "
                  "from the Mediterranean deep-sea", "doi": ""}


def test_identity_check_rejects_an_unrelated_paper():
    verdict, _ = ac.identity_check(TEXT_A, ROW_C)
    assert verdict is False


def test_identity_check_is_strict_enough_to_separate_same_subject_titles():
    """Corroboration tolerates a same-subject title; a deletion decision must
    not. 4 of ROW_B's 6 content words appear in ROW_A's paper."""
    assert ac.identity_check(TEXT_A, ROW_B)[0] is True
    assert ac.identity_check(TEXT_A, ROW_B,
                             min_coverage=ac.IDENTITY_STRICT_COVERAGE)[0] is False


def test_identity_check_reports_no_text_layer_as_untestable_not_as_wrong():
    verdict, detail = ac.identity_check("", ROW_A)
    assert verdict is None and "no text" in detail


def test_lid_named_rows_files_a_staged_file_under_its_own_literature_id(tmp_path):
    staged = tmp_path / "13330.pdf"
    staged.write_bytes(b"%PDF-1.4\n")
    queue = [{"literature_id": "13330", "last_status": "needs_library"}]
    prefer = ac.lid_named_rows([staged], [ROW_A, ROW_B], queue=queue)
    assert prefer[str(staged)] is ROW_A, (
        "a file named <literature_id>.pdf for an outstanding row must be filed "
        "under THAT record, never re-matched by title/author"
    )


def test_lid_named_rows_ignores_ids_that_are_not_outstanding(tmp_path):
    staged = tmp_path / "13330.pdf"
    staged.write_bytes(b"%PDF-1.4\n")
    queue = [{"literature_id": "13330", "last_status": "not_wanted"}]
    assert ac.lid_named_rows([staged], [ROW_A], queue=queue) == {}


def test_lid_named_rows_claims_acquired_but_unfiled_rows(tmp_path):
    # acquired_oa / acquired_bhl = downloaded, never filed (finalize skipped or held it). The
    # 2026-09-17 repair parked correct downloads in this state; excluding it left 427 rows
    # unfileable until 2026-09-18. The identity check still has to pass at ingest.
    staged = tmp_path / "13330.pdf"
    staged.write_bytes(b"%PDF-1.4\n")
    for status in ("acquired_oa", "acquired_bhl"):
        queue = [{"literature_id": "13330", "last_status": status}]
        assert list(ac.lid_named_rows([staged], [ROW_A], queue=queue).values()) == [ROW_A]


def test_lid_named_rows_ignores_files_not_named_after_a_record(tmp_path):
    staged = tmp_path / "5c2c637d84a43ec4.pdf"
    staged.write_bytes(b"%PDF-1.4\n")
    queue = [{"literature_id": "13330", "last_status": "needs_library"}]
    assert ac.lid_named_rows([staged], [ROW_A], queue=queue) == {}


def test_exists_branch_never_deletes_a_staged_file_whose_sha_differs(tmp_path, monkeypatch):
    """The EXISTS casualty of 2026-09-17: a staged download must survive when
    the destination is a different file, whatever its size."""
    staging = tmp_path / "staging"; staging.mkdir()
    lib = tmp_path / "library" / "2016"; lib.mkdir(parents=True)
    staged = staging / "25261.pdf"
    staged.write_bytes(b"%PDF-1.4\n" + b"the sicklefin lemon shark paper " * 200)
    dest = lib / "Mendez.etal.2016.Cestodes of the blue shark.pdf"
    dest.write_bytes(b"%PDF-1.4\n" + b"an entirely different paper " * 200)
    monkeypatch.setattr(ac, "pdf_text", lambda p, timeout=240: "")

    deleted, kept, _freed = ac.delete_verified_staging(
        [staged], {"25261"},
        {"25261": "2016/Mendez.etal.2016.Cestodes of the blue shark.pdf"},
        tmp_path / "library", staging_dirs=[staging], filed_rows={})
    assert deleted == 0 and kept == 1
    assert staged.exists(), "a staged download differing from the destination must be kept"


def test_delete_verified_staging_still_deletes_a_byte_identical_copy(tmp_path):
    staging = tmp_path / "staging"; staging.mkdir()
    lib = tmp_path / "library" / "1993"; lib.mkdir(parents=True)
    payload = b"%PDF-1.4\n" + b"same bytes both sides " * 200
    staged = staging / "13330.pdf"; staged.write_bytes(payload)
    dest = lib / "Polovina.etal.1993.Temporal and spatial distribution.pdf"
    dest.write_bytes(payload)

    deleted, kept, _freed = ac.delete_verified_staging(
        [staged], {"13330"},
        {"13330": "1993/Polovina.etal.1993.Temporal and spatial distribution.pdf"},
        tmp_path / "library", staging_dirs=[staging], filed_rows={"13330": ROW_A})
    assert deleted == 1 and kept == 0 and not staged.exists()


def test_delete_verified_staging_deletes_when_the_destination_identity_passes(
        tmp_path, monkeypatch):
    staging = tmp_path / "staging"; staging.mkdir()
    lib = tmp_path / "library" / "1993"; lib.mkdir(parents=True)
    staged = staging / "13330.pdf"
    staged.write_bytes(b"%PDF-1.4\n" + b"staged copy " * 200)
    dest = lib / "Polovina.etal.1993.Temporal and spatial distribution.pdf"
    dest.write_bytes(b"%PDF-1.4\n" + b"library copy " * 200)
    monkeypatch.setattr(ac, "pdf_text", lambda p, timeout=240: TEXT_A)

    deleted, kept, _freed = ac.delete_verified_staging(
        [staged], {"13330"},
        {"13330": "1993/Polovina.etal.1993.Temporal and spatial distribution.pdf"},
        tmp_path / "library", staging_dirs=[staging], filed_rows={"13330": ROW_A})
    assert deleted == 1 and kept == 0
