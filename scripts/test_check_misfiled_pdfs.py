#!/usr/bin/env python3
"""Tests for the misfile checker.

Both of the tool's known blind spots are pinned here, because each one turns
a limitation into a false accusation against a correctly-filed paper: an
abbreviated filename, and a scan whose Latin titles OCR cannot recover.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_misfiled_pdfs as cm


def tokens(text):
    return sorted(set(cm.norm(text).split()))


# Long enough to clear the MIN_TEXT_WORDS floor, so these tests exercise the
# title matching rather than the too-little-text guard.
ARTICLE = """
Bioturbation by stingrays at Ningaloo Reef Western Australia
Abstract Stingrays excavate large volumes of sediment while foraging on the
reef flat, and this bioturbation reshapes the benthic habitat over time.
""" + ("Sediment excavation was measured across replicate transects on the "
       "reef flat during spring tides, with pit dimensions recorded and "
       "volumes estimated from depth and area. Foraging pits persisted for "
       "several days before infilling, and their density varied with tidal "
       "state and season across the survey period at the study site. ") * 6


def test_parse_filename_splits_on_the_year():
    authors, year, title = cm.parse_filename(
        "/lib/1880/Jordan.etal.1880.Description of a new ray.pdf")
    assert authors == {"Jordan"}
    assert year == 1880
    assert title == "Description of a new ray"


def test_abbreviated_filename_still_matches_its_paper():
    """The filename says "Bioturb stingray Ningaloo"; the paper is right
    there. Literal matching called this absent and accused a good file."""
    assert cm.title_present("Bioturb stingray Ningaloo", tokens(ARTICLE)) is True
    assert cm.title_present("Biologging horiz vert mov Tiger Sharks",
                            tokens("Biologging Tags Reveal Links Between Fine "
                                   "Scale Horizontal and Vertical Movements "
                                   "of Tiger Sharks")) is True


def test_a_different_paper_is_reported_absent():
    assert cm.title_present(
        "The whale shark genome reveals patterns of vertebrate",
        tokens(ARTICLE)) is False


def test_a_title_too_short_to_judge_is_untestable_not_absent():
    assert cm.title_present("Raja clavata", tokens(ARTICLE)) is None
    assert cm.title_present("", tokens(ARTICLE)) is None


def test_non_latin_text_is_flagged_for_review_not_trusted():
    """A Japanese society bulletin is a real container whose Latin titles
    cannot be OCRed. It must not be reported as a confident misfile."""
    japanese = {"verdict": "misfiled_some_absent", "latin_fraction": 0.12,
                "n_words": 4000}
    assert cm.confidence(japanese) == "check_ocr"
    english = {"verdict": "misfiled_some_absent", "latin_fraction": 0.99,
               "n_words": 8000}
    assert cm.confidence(english) == "auto"


def test_thin_text_is_flagged_even_when_latin():
    assert cm.confidence({"verdict": "misfiled_some_absent",
                          "latin_fraction": 1.0, "n_words": 120}) \
        == "check_thin_text"


def test_latin_fraction_separates_scripts():
    assert cm.latin_fraction("Bioturbation by stingrays") > 0.9
    assert cm.latin_fraction("板鰓類研究会報 第 49号") < 0.5
    assert cm.latin_fraction("") == 0.0


def make_group(tmp_path, names, body):
    paths = []
    for name in names:
        p = tmp_path / name
        p.write_bytes(body)
        paths.append({"path": str(p), "inode": p.stat().st_ino, "nlink": 1,
                      "mtime": p.stat().st_mtime})
    return {"sha256": "deadbeef" * 8, "size": len(body), "files": paths}


@pytest.fixture
def fake_pdftotext(monkeypatch):
    def use(text):
        monkeypatch.setattr(cm, "extract_text",
                            lambda path, digest, cache: text)
    return use


def test_a_real_container_is_not_flagged(tmp_path, fake_pdftotext):
    fake_pdftotext(
        "Bulletin 1880. Description of a new ray Raia stellulata from the "
        "coast. Synopsis and descriptions of the American Rhinobatidae. "
        + ("Specimens were obtained from the market and preserved in spirits, "
           "with measurements taken from the snout to the base of the tail "
           "and compared against previously described forms from the same "
           "coast during the survey of that season. ") * 6)
    g = make_group(tmp_path, [
        "Jordan.1880.Description of a new ray Raia stellulata.pdf",
        "Garman.1880.Synopsis and descriptions of the American Rhinobatidae.pdf",
    ], b"%PDF" + b"x" * 500)
    assert cm.judge_group(g, tmp_path)["verdict"] == "container"


def test_a_misfile_is_flagged(tmp_path, fake_pdftotext):
    fake_pdftotext(ARTICLE)
    g = make_group(tmp_path, [
        "Smith.2011.Bioturbation by stingrays at Ningaloo Reef.pdf",
        "Jones.2021.The whale shark genome reveals patterns of vertebrate.pdf",
    ], b"%PDF" + b"x" * 500)
    entry = cm.judge_group(g, tmp_path)
    assert entry["verdict"] == "misfiled_some_absent"
    absent = [r for r in entry["records"] if r["present"] is False]
    assert len(absent) == 1
    assert absent[0]["title"].startswith("The whale shark genome")


def test_an_unreadable_pdf_is_untestable_not_a_misfile(tmp_path, fake_pdftotext):
    fake_pdftotext("")
    g = make_group(tmp_path, ["A.2011.First paper about sharks.pdf",
                              "B.2011.Second paper about rays.pdf"],
                   b"%PDF" + b"x" * 500)
    entry = cm.judge_group(g, tmp_path)
    assert entry["verdict"] == "untestable_no_text"
    assert all(r["present"] is None for r in entry["records"])


def test_csv_carries_only_misfiles_and_never_the_untestable(tmp_path, fake_pdftotext):
    fake_pdftotext(ARTICLE)
    g = make_group(tmp_path, [
        "Smith.2011.Bioturbation by stingrays at Ningaloo Reef.pdf",
        "Jones.2021.The whale shark genome reveals patterns of vertebrate.pdf",
    ], b"%PDF" + b"x" * 500)
    entries = [cm.judge_group(g, tmp_path),
               {"verdict": "untestable_no_text", "records": [], "year": 1900,
                "size_mb": 1, "n_records": 2, "latin_fraction": 0,
                "n_words": 0, "pdf_starts": "", "sha256": "x" * 12}]
    out = tmp_path / "review.csv"
    assert cm.write_csv(entries, out) == 1
    body = out.read_text()
    assert "whale shark genome" in body
    assert "Bioturbation" in body        # named as what the PDF holds instead


def test_text_cache_avoids_a_second_extraction(tmp_path, monkeypatch):
    calls = []

    class Result:
        stdout = ARTICLE

    def fake_run(cmd, **kw):
        calls.append(cmd)
        return Result()

    monkeypatch.setattr(cm.subprocess, "run", fake_run)
    pdf = tmp_path / "x.pdf"
    pdf.write_bytes(b"%PDF")
    for _ in range(3):
        assert cm.extract_text(str(pdf), "abc123", tmp_path / "cache") == ARTICLE
    assert len(calls) == 1
