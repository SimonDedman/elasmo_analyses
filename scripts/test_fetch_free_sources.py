#!/usr/bin/env python3
"""Plain-assert tests for scripts/fetch_free_sources.py matching logic and
the FRDC project-number parser. Run with: python3 -m pytest -q
(mirrors the style of scripts/test_acquire_cascade.py; no network calls)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fetch_free_sources as ffs  # noqa: E402


# ---------------------------------------------------------------------------
# title_tokens / title_overlap
# ---------------------------------------------------------------------------

def test_title_tokens_lowercases_and_filters_short_words():
    toks = ffs.title_tokens("The Diet of Sharks")
    assert "the" not in toks  # stop word
    assert "diet" in toks
    assert "sharks" in toks


def test_title_tokens_handles_accents():
    toks = ffs.title_tokens("Sphyrna zygaena côte")
    assert "sphyrna" in toks
    assert any("c" in t for t in toks)  # accented token survives the [a-zà-ÿ] class


def test_title_overlap_identical_titles_is_one():
    t = "Feeding habits of the scalloped hammerhead shark Sphyrna lewini"
    assert ffs.title_overlap(t, t) == 1.0


def test_title_overlap_no_shared_words_is_zero():
    assert ffs.title_overlap("Shark feeding ecology study",
                             "Ray population genetics survey") == 0.0


def test_title_overlap_uses_longer_title_as_denominator():
    short = "Shark feeding ecology"
    longer = "Shark feeding ecology of juvenile lemon sharks in nursery habitat areas"
    score = ffs.title_overlap(short, longer)
    short_tokens = ffs.title_tokens(short)
    longer_tokens = ffs.title_tokens(longer)
    expected = len(short_tokens & longer_tokens) / max(len(short_tokens), len(longer_tokens))
    assert score == expected
    assert score < 1.0  # denominator is the longer set, not the shorter


def test_title_overlap_empty_title_is_zero():
    assert ffs.title_overlap("", "Some real title here") == 0.0
    assert ffs.title_overlap("Some real title here", "") == 0.0


# ---------------------------------------------------------------------------
# first_surname
# ---------------------------------------------------------------------------

def test_first_surname_comma_form():
    assert ffs.first_surname("Artüz, M.L. & Sakinç, M. (2025)") == "Artüz"


def test_first_surname_no_comma_uses_last_token():
    # No-comma form is assumed "Firstname Surname" (surname last), matching
    # scripts/acquire_cascade.py::_first_surname's own fallback.
    assert ffs.first_surname("John Smith (2020)") == "Smith"


def test_first_surname_single_author():
    assert ffs.first_surname("Smith, J. (2020)") == "Smith"


def test_first_surname_empty_string():
    assert ffs.first_surname("") == ""
    assert ffs.first_surname(None) == ""


# ---------------------------------------------------------------------------
# FRDC project-number parser
# ---------------------------------------------------------------------------

def test_frdc_project_two_digit_year_is_19xx():
    row = {"findspot_raw": "Final Report to FRDC Project 93/061. 45 pp."}
    assert ffs.parse_frdc_project(row) == ("1993", "061")


def test_frdc_project_lowercase_keyword():
    row = {"findspot_raw": "FRDC project 1998/108"}
    assert ffs.parse_frdc_project(row) == ("1998", "108")


def test_frdc_project_three_digit_two_digit_year():
    row = {"findspot_raw": "See FRDC 99/369 for details"}
    assert ffs.parse_frdc_project(row) == ("1999", "369")


def test_frdc_project_no_pattern():
    row = {"findspot_raw": "Final Report to FRDC Project No. 2002/064. 183 pp."}
    assert ffs.parse_frdc_project(row) == ("2002", "064")


def test_frdc_project_requires_frdc_keyword():
    # A bare project-shaped number with no FRDC anywhere in scope must not match
    # (avoids false positives on volume/issue numbers, dates, etc).
    row = {"findspot_raw": "Some Report 99/369", "journal_clean": "Unrelated Journal"}
    assert ffs.parse_frdc_project(row) is None


def test_frdc_project_frdc_present_but_no_number():
    row = {"findspot_raw": "Published by FRDC, no project number given"}
    assert ffs.parse_frdc_project(row) is None


def test_frdc_project_checks_journal_clean_too():
    row = {"findspot_raw": None,
           "journal_clean": "Final Report to FRDC Project No.",
           "notes": "2002/064"}
    assert ffs.parse_frdc_project(row) == ("2002", "064")


def test_frdc_url_pattern_matches_known_good_examples():
    for year, num, expected in [
        ("1993", "061", "1993-061-DLD.pdf"),
        ("1991", "023", "1991-023-DLD.pdf"),
        ("1999", "369", "1999-369-DLD.pdf"),
        ("1998", "108", "1998-108-DLD.pdf"),
    ]:
        url = ffs.FRDC_PDF_URL.format(year=year, num=num)
        assert url.endswith(expected)


# ---------------------------------------------------------------------------
# scope_matches / outstanding_scope / compile_patterns
# ---------------------------------------------------------------------------

def test_compile_patterns_word_boundary_avoids_substring_false_positive():
    patterns = ffs.compile_patterns("ICES")
    row_bad = {"journal": "Prices and Markets Journal", "journal_clean": "", "findspot_raw": ""}
    row_good = {"journal": "ICES Journal of Marine Science", "journal_clean": "", "findspot_raw": ""}
    assert ffs.scope_matches(row_bad, patterns) is False
    assert ffs.scope_matches(row_good, patterns) is True


def test_outstanding_scope_filters_by_status_and_pattern():
    rows = [
        {"literature_id": "1", "last_status": "needs_library", "journal": "ICES CM", "journal_clean": "", "findspot_raw": ""},
        {"literature_id": "2", "last_status": "acquired_oa", "journal": "ICES CM", "journal_clean": "", "findspot_raw": ""},
        {"literature_id": "3", "last_status": "needs_pdf", "journal": "Unrelated Journal", "journal_clean": "", "findspot_raw": ""},
    ]
    patterns = ffs.compile_patterns("ICES")
    out = ffs.outstanding_scope(rows, patterns)
    assert [r["literature_id"] for r in out] == ["1"]


def test_outstanding_scope_ids_override_bypasses_status_filter():
    rows = [
        {"literature_id": "1", "last_status": "acquired_oa", "journal": "", "journal_clean": "", "findspot_raw": ""},
        {"literature_id": "2", "last_status": "needs_library", "journal": "", "journal_clean": "", "findspot_raw": ""},
    ]
    out = ffs.outstanding_scope(rows, None, ["1"])
    assert [r["literature_id"] for r in out] == ["1"]


# ---------------------------------------------------------------------------
# manifest_row / verified_str
# ---------------------------------------------------------------------------

def test_manifest_row_has_all_required_fields():
    row = ffs.manifest_row("123", venue="X", status="downloaded")
    assert set(row.keys()) == set(ffs.MANIFEST_FIELDS)
    assert row["literature_id"] == "123"


def test_verified_str_maps_scan_true_false():
    assert ffs.verified_str(True) == "yes"
    assert ffs.verified_str(False) == "no"
    assert ffs.verified_str("scan") == "scan"


if __name__ == "__main__":
    import subprocess
    sys.exit(subprocess.call([sys.executable, "-m", "pytest", "-q", __file__]))
