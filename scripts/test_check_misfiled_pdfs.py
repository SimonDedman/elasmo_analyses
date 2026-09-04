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
    assert cm.title_present("Bioturb stingray Ningaloo",
                            tokens(ARTICLE))[0] is True
    assert cm.title_present("Biologging horiz vert mov Tiger Sharks",
                            tokens("Biologging Tags Reveal Links Between Fine "
                                   "Scale Horizontal and Vertical Movements "
                                   "of Tiger Sharks"))[0] is True


def test_bibtex_italic_residue_still_matches_its_paper():
    """"<i>Tursiops aduncus</i>" loses its angle brackets upstream and reaches
    the filename as "iTursiops aduncusi". The species is plainly in the
    document; the tags are not."""
    text = tokens("Bite wounds on Tursiops aduncus provide the first evidence "
                  "of shark predation in this population")
    assert cm.title_present("Bite wounds on iTursiops aduncusi provide the "
                            "first", text)[0] is True


def test_a_different_paper_is_reported_absent():
    verdict, found, sought = cm.title_present(
        "The whale shark genome reveals patterns of vertebrate", tokens(ARTICLE))
    assert verdict is False
    assert sought > 0 and found < sought   # the evidence shown on the sheet


def test_a_title_too_short_to_judge_is_untestable_not_absent():
    assert cm.title_present("Raja clavata", tokens(ARTICLE))[0] is None
    assert cm.title_present("", tokens(ARTICLE))[0] is None


def test_same_paper_recognises_a_mangled_name_variant():
    assert cm.same_paper("Bite wounds on iTursiops aduncusi provide the first",
                         "Bite-wounds-on-Tursiops-aduncus-provide") is True
    assert cm.same_paper("The whale shark genome reveals patterns",
                         "Bioturbation by stingrays at Ningaloo Reef") is False


def test_non_latin_text_is_flagged_for_review_not_trusted():
    """A Japanese society bulletin is a real container whose Latin titles
    cannot be OCRed. It must not be reported as a confident misfile."""
    japanese = {"verdict": "misfiled_some_absent", "latin_fraction": 0.12,
                "n_words": 4000, "n_records": 5}
    assert cm.confidence(japanese, {"words_sought": 7})[0] == "check the scan"
    assert "non-Latin" in cm.confidence(japanese, {"words_sought": 7})[1]
    english = {"verdict": "misfiled_some_absent", "latin_fraction": 0.99,
               "n_words": 8000, "n_records": 2}
    assert cm.confidence(english, {"words_sought": 7})[0] == "strong"


def test_thin_text_is_flagged_even_when_latin():
    thin = {"verdict": "misfiled_some_absent", "latin_fraction": 1.0,
            "n_words": 120, "n_records": 2}
    assert cm.confidence(thin, {"words_sought": 7})[0] == "check the scan"


def test_a_heavily_abbreviated_title_is_not_a_confident_finding():
    """"3D mov hab select jGWS NY Bight" is the same paper as
    "Three-Dimensional Movements and Habitat Selection of Young White
    Sharks". Two or three testable words cannot settle that either way."""
    entry = {"verdict": "misfiled_some_absent", "latin_fraction": 1.0,
             "n_words": 9000, "n_records": 2}
    how_sure, why = cm.confidence(entry, {"words_sought": 3})
    assert how_sure == "short title"
    assert "abbreviated" in why
    # A full title in the same document stays a confident finding.
    assert cm.confidence(entry, {"words_sought": 7})[0] == "strong"


def test_none_matched_in_clean_text_is_strong_not_doubtful():
    """The clearest finding in the set is nineteen records on one PDF where
    none matched, judged from 4,000 words of clean text. An earlier rule
    demoted exactly that case for being 'none matched'."""
    clean = {"verdict": "misfiled_none_found", "latin_fraction": 0.96,
             "n_words": 3982, "n_records": 19}
    how_sure, why = cm.confidence(clean, {"words_sought": 7})
    assert how_sure == "strong"
    assert "NONE" in why and "19" in why


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
    assert absent[0]["words_sought"] > 0
    # The year of the paper actually in the file, which is not the year of
    # the record being questioned.
    assert entry["pdf_year"] == 2011


def test_an_unreadable_pdf_is_untestable_not_a_misfile(tmp_path, fake_pdftotext):
    fake_pdftotext("")
    g = make_group(tmp_path, ["A.2011.First paper about sharks.pdf",
                              "B.2011.Second paper about rays.pdf"],
                   b"%PDF" + b"x" * 500)
    entry = cm.judge_group(g, tmp_path)
    assert entry["verdict"] == "untestable_no_text"
    assert all(r["present"] is None for r in entry["records"])


def test_a_name_variant_is_not_reported_as_a_misfile(tmp_path, fake_pdftotext):
    """Two filenames for one paper belong in the twins workflow, not here."""
    fake_pdftotext(
        "Bite wounds on Tursiops aduncus provide the first evidence of shark "
        "predation " + ("Observations were made during boat-based surveys of "
                        "the resident population across the study area over "
                        "successive seasons and years. ") * 8)
    g = make_group(tmp_path, [
        "Smith.2019.Bite-wounds-on-Tursiops-aduncus-provide.pdf",
        "Smith.2019.Bite wounds on iTursiops aduncusi provide the first.pdf",
    ], b"%PDF" + b"x" * 500)
    entry = cm.judge_group(g, tmp_path)
    assert not any(r["present"] is False for r in entry["records"])
    assert entry["verdict"] == "container"


def test_csv_carries_only_misfiles_and_never_the_untestable(tmp_path, fake_pdftotext):
    fake_pdftotext(ARTICLE)
    g = make_group(tmp_path, [
        "Smith.2011.Bioturbation by stingrays at Ningaloo Reef.pdf",
        "Jones.2021.The whale shark genome reveals patterns of vertebrate.pdf",
    ], b"%PDF" + b"x" * 500)
    entries = [cm.judge_group(g, tmp_path),
               {"verdict": "untestable_no_text", "records": [], "year": 1900,
                "size_mb": 1, "n_records": 2, "latin_fraction": 0,
                "n_words": 0, "pdf_starts": "", "sha256": "x" * 12,
                "pdf_year": None}]
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


def _entry(sha, records, verdict):
    return {"sha256": sha, "verdict": verdict, "records": records,
            "year": 2018, "size_mb": 1, "n_records": len(records),
            "latin_fraction": 1.0, "n_words": 9000, "pdf_starts": "",
            "pdf_year": 2018}


def test_cross_check_finds_a_papers_real_home():
    """A misfiled name is not a lost paper: the same paper is often already
    filed correctly elsewhere, so deleting the wrong name loses nothing."""
    entries = [
        _entry("aaa", [
            {"title": "Delayed.healthcare.and.secondary.infections.following",
             "present": False, "path": "/lib/2018/X.2018.Delayed.healthcare.pdf",
             "year": 2018, "words_found": 5, "words_sought": 8},
            {"title": "Injuries caused by fish in a community",
             "present": True, "path": "/lib/2018/H.2018.Injuries.pdf",
             "year": 2018, "words_found": 6, "words_sought": 6}],
              "misfiled_some_absent"),
        _entry("bbb", [
            {"title": "Delayed healthcare and secondary infections following",
             "present": True, "path": "/lib/2018/S.2018.Delayed healthcare.pdf",
             "year": 2018, "words_found": 6, "words_sought": 6}], "container"),
    ]
    found = cm.find_correct_copies(entries)
    assert found["/lib/2018/X.2018.Delayed.healthcare.pdf"]["path"] \
        == "/lib/2018/S.2018.Delayed healthcare.pdf"


def test_cross_check_does_not_match_on_generic_words():
    """Searching titles against whole documents returned 85 hits of 93, a
    chance-collision rate. Matching must be title-to-title and strict."""
    entries = [
        _entry("aaa", [
            {"title": "Shore fishes of the Marquesas Islands an updated",
             "present": False, "path": "/lib/A.pdf", "year": 2015,
             "words_found": 2, "words_sought": 5},
            {"title": "Cape fur seals adjust their foraging",
             "present": True, "path": "/lib/B.pdf", "year": 2015,
             "words_found": 5, "words_sought": 5}], "misfiled_some_absent"),
        _entry("bbb", [
            {"title": "Telemetry reveals spatial separation of cooccurring fishes",
             "present": True, "path": "/lib/C.pdf", "year": 2015,
             "words_found": 6, "words_sought": 6}], "container"),
    ]
    assert cm.find_correct_copies(entries) == {}


def test_dotted_filenames_are_normalised_before_matching():
    """Dots are not what breaks matching: 136 of 180 dotted files match their
    own paper. They are a misfiled import batch, not a formatting problem."""
    dotted = "Delayed.healthcare.and.secondary.infections.following.freshwater"
    spaced = "Delayed healthcare and secondary infections following freshwater"
    assert cm.title_words(dotted) == cm.title_words(spaced)
    assert cm.is_dotted(dotted) and not cm.is_dotted(spaced)


def test_ligatures_expand_instead_of_vanishing():
    """NFKD leaves ae/oe ligatures intact and the ASCII fold then deletes
    them, so "Myliobatidae" became "myliobatid" and stopped matching the
    filename's "myliobatidae". Nineteenth century scans are full of these."""
    assert cm.norm("Myliobatidæ") == "myliobatidae"
    assert cm.norm("Chimæra monstrosa") == "chimaera monstrosa"
    assert cm.norm("Squalidæ") == "squalidae"
    assert cm.norm("Straße") == "strasse"
    assert cm._in_text("myliobatidae", sorted(cm.norm("Myliobatidæ").split()))


def test_a_ligature_title_is_found_in_a_ligature_document():
    doc = tokens("On the nomenclature of the Myliobatidæ or Ætobatidæ, "
                 "with remarks on the Chimæra of the deeper waters")
    assert cm.title_present("The nomenclature of the Myliobatidae or "
                            "Aetobatidae", doc)[0] is True


JUNK = "aes ns ee er -eOw- Pe Phat dM ene Papal epaid Alpat sae gh Ys iatead tad " * 3


def test_excerpt_skips_scanned_front_matter():
    """A scanned volume opens with plate noise, and showing that as the
    document's identity makes the row unjudgeable."""
    body = ("On the nomenclature of the Myliobatidae by Theodore Gill from "
            "the Proceedings of the United States National Museum")
    out = cm.readable_excerpt(JUNK + body)
    assert "nomenclature of the Myliobatidae" in out
    assert out.count("eOw") == 0


def test_excerpt_handles_non_english_prose():
    """An English-only function-word list would call every German and
    Portuguese paper noise and skip past its title."""
    de = ("Einige Bemerkungen über die Histologie der Pristis-Zähne von Franz "
          "Hilgendorf aus dem Sitzungsbericht der Gesellschaft")
    assert "Histologie" in cm.readable_excerpt(
        "^^UÄ^ '2fÄ* A, AÄ'W' C?iMMMMn AA / m,i " * 4 + de)
    pt = ("Conteúdo estomacal dos tubarões azul e anequim capturados no sul do "
          "Brasil com notas sobre a dieta")
    assert "estomacal" in cm.readable_excerpt(pt)


def test_excerpt_leaves_a_clean_document_at_its_opening():
    clean = ("Journal of Fish Biology (2012) 80, 1595-1607 available online at "
             "wileyonlinelibrary.com Fisheries management and conservation of "
             "the whale shark")
    assert cm.readable_excerpt(clean).startswith("Journal of Fish Biology")


def test_excerpt_of_pure_noise_returns_the_opening_not_an_error():
    out = cm.readable_excerpt(JUNK)
    assert out and out.startswith("aes ns ee")
