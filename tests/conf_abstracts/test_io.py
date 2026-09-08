"""Tests for segment / extract / export (no pytest)."""
import tempfile
from pathlib import Path

from conf_abstracts import segment, extract, schema, load, export, qa_ocr

FIX = Path(__file__).resolve().parent / "fixtures" / "jmih2016_p50.txt"


def test_elasmo_lexicon():
    from conf_abstracts.lexicon import is_elasmo_text
    assert is_elasmo_text("Growth Rates of Smalltooth Sawfish Pristis pectinata", "")
    assert is_elasmo_text("Population genetics of the cownose ray", "Rhinoptera bonasus")
    assert is_elasmo_text("Diet of the little skate", "Leucoraja erinacea")
    assert not is_elasmo_text("Calling Phenology of Coastal Prairie Anurans", "frogs")
    assert not is_elasmo_text("Osteology of Nurseryfish", "Kurtus gulliveri")


def test_elasmo_lexicon_ray_noise():
    """\\bray\\b matched ray-finned fishes, fin-ray counts and X-rays: 143 of
    1,226 content-flagged elasmo records were false positives (2026-09-04)."""
    from conf_abstracts.lexicon import is_elasmo_text
    assert not is_elasmo_text("Evolution of the gular muscles in ray-finned fishes", "")
    assert not is_elasmo_text("Systematic revision", "a lower count of 1st dorsal fin rays")
    assert not is_elasmo_text("Clutch frequency", "mark-recapture and X-ray analysis")
    assert not is_elasmo_text("Bembrops", "with fewer dorsal and pectoral rays")
    # the scrub must not cost us real batoids
    assert is_elasmo_text("Movement of manta rays in Indonesia", "")
    assert is_elasmo_text("Age and growth", "we sampled rays and sharks from the trawl")
    assert is_elasmo_text("Habitat use of the bat ray", "Myliobatis californica")


def test_oa_xlsx_author_split():
    from conf_abstracts.ingest_oa_xlsx import _split_authors
    # Oxford Abstracts comma-separates 'First Last', but submitters slip in
    # 'Surname, Initials', which a naive split tears in half.
    got = [a["full_name"] for a in
           _split_authors("Purushottama, G. B., Muktha, M., Swatipriyanka Sen Dash", "")]
    assert got == ["G. B. Purushottama", "M. Muktha", "Swatipriyanka Sen Dash"], got
    auth = _split_authors("Brooke Anderson, Neil Hammerschlag", "Brooke Anderson")
    assert [a["is_presenter"] for a in auth] == [1, 0]
    # presenter not found in the list -> first author, flagged as inferred
    auth = _split_authors("B. Anderson, Neil Hammerschlag", "Brooke Anderson")
    assert auth[0]["is_presenter"] == 1 and auth[0]["presenter_inferred"] == 1


def test_oa_xlsx_shared_run():
    """Programme-book titles arrive truncated, author-fused, or as a bare tail;
    a 40-char verbatim run still identifies the abstract (16 of 242, JMIH 2021)."""
    from conf_abstracts.merge_schedule import _shared_run
    full = "High resolution acoustic telemetry reveals swim speeds and inferred field metabolic rates in juvenile white sharks"
    assert _shared_run("and inferred field metabolic rates in juvenile white sharks", full)
    assert _shared_run("Delineation of Blacktip Shark Genetic Stock Structure in the Frazier, Jayne Gardiner",
                       "Delineation of Blacktip Shark Genetic Stock Structure in the Gulf of Mexico")
    assert not _shared_run("Calling phenology of the Rio Grande chirping frog", full)
    assert not _shared_run("short title", full)


def test_oa_xlsx_presentation_type():
    from conf_abstracts.ingest_oa_xlsx import _presentation_type, _award
    assert _presentation_type("Contributed 15-minute Oral Paper VIRTUAL") == "talk"
    assert _presentation_type("Student Poster Competition (all are virtual)") == "poster"
    assert _presentation_type("Contributed 5-minute Lightning Paper") == "lightning"
    assert _presentation_type("Invited Symposium (all are virtual)") == "symposium"
    assert _award("Student Oral Competition IN-PERSON") == "Student Oral Competition"
    assert _award("Contributed 15-minute Oral Paper VIRTUAL") is None


def test_oa_xlsx_2025_menu_prefix():
    """2025 writes 'Category: choice', and one category is a MENU of three
    formats. Read whole, 'Contributed Oral, Lightning or Poster Presentation:
    Regular Oral Presentation' matches 'lightning' first and calls all 379
    contributed presentations lightning talks."""
    from conf_abstracts.ingest_oa_xlsx import _presentation_type, _award, _session
    menu = "Contributed Oral, Lightning or Poster Presentation: "
    assert _presentation_type(menu + "Regular Oral Presentation (15 min)") == "talk"
    assert _presentation_type(menu + "Poster") == "poster"
    assert _presentation_type(menu + "Lightning Talk (5 min)") == "lightning"
    assert _presentation_type("Student Competition Poster: AES Carrier Award") == "poster"
    assert _presentation_type(
        "Student Competition Oral Presentation: AES Gruber Award") == "talk"
    assert _presentation_type(
        "Symposium Presentation (invited): Science in 3D (ASIH)") == "symposium"
    assert _presentation_type(
        "Plenary Presentation (invited): AES Plenary Address") == "plenary"
    # The award is the name after the colon, not the class before it.
    assert _award("Student Competition Poster: AES Carrier Award") == "AES Carrier Award"
    assert _award(menu + "Poster") is None
    assert _session("Symposium Presentation (invited): Science in 3D (ASIH)") \
        == "Science in 3D (ASIH)"
    assert _session(menu + "Poster") is None


def test_oa_xlsx_2025_elasmo_and_society():
    """The submitter's own taxon answer settles is_elasmo, and the award or
    symposium says whose meeting section it was before membership does."""
    from conf_abstracts.ingest_oa_xlsx import _elasmo, _society
    assert _elasmo("Eggshells in Gekkota", "lizard eggs",
                   "Ichthyofauna: Chondrichthyan fishes (AES)", "") == (True, "taxon_group")
    assert _elasmo("Movement of tiger sharks", "shark telemetry",
                   "Ichthyofauna: Ichthyofauna in general", "") == (True, "content")
    assert _elasmo("Catfish phylogeny", "Mystus RADSeq",
                   "Ichthyofauna: All other fishes (ASIH)", "Mystus catfish")[0] is False
    assert _society(dict(award="AES Gruber Award", session_name=None,
                         taxon_group="Ichthyofauna: All other fishes (ASIH)",
                         societies_explicit="ASIH")) == ("AES", "award")
    assert _society(dict(award=None, session_name=None,
                         taxon_group="Ichthyofauna: Chondrichthyan fishes (AES)",
                         societies_explicit="ASIH, SSAR")) == ("AES", "taxon_group")
    assert _society(dict(award=None, session_name=None, taxon_group=None,
                         societies_explicit="ASIH")) == ("ASIH", "membership")
    assert _society(dict(award=None, session_name=None, taxon_group=None,
                         societies_explicit="ASIH, SSAR")) == (None, None)


def test_program_book_poster_sections():
    """The 2023 book splits each day into Oral / Poster / Symposia / Lightning /
    Plenary banners and lists posters under a 'P<session>-<n>' id where an oral
    entry carries a start time. Missing that made JMIH 2023 come back as 389
    talks and no posters, and left 597 of 604 abstracts with no type."""
    from conf_abstracts import parse_program_book as P
    text = "\n".join([
        "Thursday 13 July 2023", "", "9:30 am", "", "Alice Smith, Bob Jones", "",
        "Movement of tiger sharks in the Gulf", "",
        "Friday 14 July \u2022 Poster Presentations", "", "P1-1", "",
        "Carol White, Dan Black", "",
        "Fine-scale space use by white sharks offshore", "",
        "Friday 14 July \u2022 Symposia", "", "10:00 am", "", "Erin Green", "",
        "Introduction to the elasmobranch symposium session", "",
    ])
    blocks = P.parse_program_book_blocks(text)
    got = {b["title"][:20]: (b["presentation_type"], b["program_number"],
                             b["session_datetime"]) for b in blocks}
    assert got["Movement of tiger sh"][0] == "talk"
    assert got["Fine-scale space use"][:2] == ("poster", "P1-1")
    # the banner carries no year; it is taken from the last full day header
    assert got["Fine-scale space use"][2] == "Friday 14 July 2023"
    # a poster id must not make the following symposium talk a poster
    assert got["Introduction to the "][0] == "symposium"


def test_program_book_drops_footers_and_fragments():
    from conf_abstracts import parse_program_book as P
    text = "\n".join([
        "Thursday 13 July 2023", "", "9:30 am", "", "Alice Smith", "",
        "Mercury in sharks from southeast estuaries JMIH 2023 Conference Program 41", "",
        "9:45 am", "", "Bob Jones", "", "and Population Projections", "",
    ])
    blocks = P.parse_program_book_blocks(text)
    titles = [b["title"] for b in blocks]
    assert titles == ["Mercury in sharks from southeast estuaries"], titles


def test_qa_classify():
    assert qa_ocr._classify(0, 0.0) == "no_text"
    assert qa_ocr._classify(5000, 0.30) == "low_quality"
    assert qa_ocr._classify(5000, 0.60) == "ok"


def test_segment_jmih_blocks():
    txt = FIX.read_text()
    blocks = segment.segment_blocks(txt, "jmih_book")
    assert len(blocks) >= 2, f"got {len(blocks)}"
    b = blocks[0]
    assert b["program_number"] and b["program_number"].isdigit(), b
    assert b["title"], b
    assert b["abstract_text"] and len(b["abstract_text"].split()) > 20, b


def test_extract_authors_asih():
    a = extract.parse_authors("Armbruster, Jonathan; de Souza, Lesley; Lujan, Nathan")
    assert a[0]["full_name"] == "Jonathan Armbruster", a[0]
    assert a[0]["position"] == 1 and a[0]["is_presenter"] == 1
    assert len(a) == 3


def test_extract_authors_superscript():
    a = extract.parse_authors("Dana Bethea1, John Carlson1, Gregg Poulakis3")
    assert [x["full_name"] for x in a] == ["Dana Bethea", "John Carlson", "Gregg Poulakis"], a


def test_extract_fields_no_llm():
    txt = FIX.read_text()
    blocks = segment.segment_blocks(txt, "jmih_book")
    rec = extract.extract_fields(blocks[0], "JMIH", use_llm=False)
    assert rec["title"] and rec["authors"]
    assert rec["presentation_type"] in {"talk", "poster", "lightning",
                                        "symposium", "plenary", "keynote"}
    assert "confidence" in rec


def test_export_roundtrip():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        con = schema.create_db(d / "t.db")
        mid = load.upsert_meeting(con, {"meeting": "SI", "year": 2026,
                                        "source_pdf": "s.pdf"})
        load.insert_abstract(con, mid, {
            "program_number": "1", "title": "Shark movement", "abstract_text": "a b c d e",
            "societies_explicit": ["AES"], "society": "AES", "is_elasmo": 1,
            "presentation_type": "talk",
            "authors": [{"full_name": "A B", "position": 1}]})
        load.insert_abstract(con, mid, {
            "program_number": "2", "title": "Frog calls", "abstract_text": "x y z",
            "societies_explicit": [], "society": "HL", "is_elasmo": 0,
            "presentation_type": "poster", "authors": []})
        pq = d / "elasmo.parquet"
        js = d / "all.json"
        xl = d / "all.xlsx"
        n_el = export.to_parquet_elasmo(con, pq)
        export.to_json(con, js)
        export.to_xlsx(con, xl)
        assert n_el == 1 and pq.exists() and js.exists() and xl.exists()
        import json
        data = json.loads(js.read_text())
        assert len(data) == 2


# ---------------------------------------------------------------------------
# parse_program_layout: the two-column programme books (2024, 2025)
# ---------------------------------------------------------------------------
_PROGRAM_BOOK_2025 = ("/media/simon/data/Documents/Si Work/Papers & Books/"
                      "SharkPapers/Conferences/2025/2025_JMIH_ProgrammeBook.pdf")


def _layout_2025():
    from pathlib import Path
    from conf_abstracts.parse_program_layout import parse_program_layout
    if not Path(_PROGRAM_BOOK_2025).exists():
        return None
    return parse_program_layout(_PROGRAM_BOOK_2025)


def test_layout_finds_the_entries_the_text_parser_drops():
    """A wide author list pushes the entry number off the start of the line, so
    the text parser's ^N.N anchor misses it. Seven JMIH 2025 talks were lost
    that way, four of them elasmo, in a year with no abstract book to fall back
    on. Each must come back with its full author list."""
    blocks = _layout_2025()
    if blocks is None:
        return
    by_num = {b["program_number"]: b for b in blocks}
    for num in ("8.4", "12.4", "25.3", "30.2", "36.6", "38.3", "49.1"):
        assert num in by_num, f"{num} still missing"
    b = by_num["30.2"]
    assert b["title"].startswith("Sharks and Rays of the Gulf of Carpentaria")
    # "Edwin Ling" is split across the column break; both halves must survive
    assert "Edwin Ling" in b["author_raw"], b["author_raw"]
    assert by_num["30.1"]["author_raw"].count(",") == 10   # eleven authors


def test_layout_reads_the_poster_half_of_the_book():
    """Poster numbers carry a P prefix that the text parser's \\d+\\.\\d+ cannot
    match, so JMIH 2025 held 343 talks and none of its 190 posters."""
    blocks = _layout_2025()
    if blocks is None:
        return
    posters = [b for b in blocks if b["presentation_type"] == "poster"]
    assert len(posters) > 150, len(posters)
    # posters are headed by a bold category line, not a "Session N:" line
    aes = [b for b in posters if b["session_name"] == "AES Posters"]
    assert aes and all(b["societies_explicit"] == ["AES"] for b in aes)


def test_layout_keeps_hyphens_broken_across_a_line():
    """These books never hyphenate to justify, so a hyphen at a line end is part
    of the word. pdftotext drops it, which is where "HatcheryRaised" and
    "longterm" came from."""
    blocks = _layout_2025()
    if blocks is None:
        return
    by_num = {b["program_number"]: b for b in blocks}
    assert "Luci Herrera-Lopez" in by_num["25.3"]["author_raw"]
    assert "Hatchery-Raised" in by_num["12.1"]["title"]
    # a suspended hyphen inside one line is left exactly as printed
    assert "Micro- and Nano-plastics" in by_num["P1.1"]["title"]


def test_layout_keeps_page_furniture_out_of_titles():
    """Room banners, the running footer and the asterisk note sit outside the
    entry; appending them to whichever entry was open put "Ballroom F" and
    "JMIH 2025 Conference Program 15" inside real titles."""
    blocks = _layout_2025()
    if blocks is None:
        return
    for b in blocks:
        t = b["title"]
        assert "Conference Program" not in t, t
        assert "Ballroom" not in t, t
        assert "asterisk" not in t, t
        # An entry with no authors is either a parse failure or a slot that has
        # none - JMIH 2025 32.3 is a bare "Discussion". Only the short ones are
        # allowed to be authorless; ingest drops them anyway.
        assert b["author_raw"] or len(t) < 30, \
            f"{b['program_number']} lost its authors: {t!r}"


_PROGRAM_BOOK_2021 = _PROGRAM_BOOK_2025.replace("2025", "2021")
_PROGRAM_BOOK_2023 = _PROGRAM_BOOK_2025.replace("2025", "2023")


def _layout(path):
    from pathlib import Path
    from conf_abstracts.parse_program_layout import parse_program_layout
    return parse_program_layout(path) if Path(path).exists() else None


def test_layout_reads_the_time_delimited_books_too():
    """2021-2023 are the same two columns as 2024/2025 but print no entry
    number, so the start time in the left column opens the entry. The 2021 book
    also heads its sessions with a bare bold line ("Reptile Conservation and
    Management I") rather than "Session N:", which is why the text parser found
    no sessions at all and merge_schedule refused to carry any."""
    blocks = _layout(_PROGRAM_BOOK_2021)
    if blocks is None:
        return
    assert len(blocks) > 200, len(blocks)
    sessions = {b["session_name"] for b in blocks if b["session_name"]}
    assert len(sessions) > 20, sessions
    assert all(b["session_datetime"] for b in blocks)
    assert all(b["author_raw"] for b in blocks)


def test_layout_reads_2023_posters_by_their_id():
    """The 2023 poster half opens each entry with "P<session>-<n>" where an oral
    entry carries a time."""
    blocks = _layout(_PROGRAM_BOOK_2023)
    if blocks is None:
        return
    posters = [b for b in blocks if b["presentation_type"] == "poster"]
    assert len(posters) > 150, len(posters)
    assert all(b["program_number"] and b["program_number"].startswith("P")
               for b in posters)
    aes = [b for b in posters if b["session_name"] == "AES Carrier Award"]
    assert aes, sorted({b["session_name"] for b in posters})[:10]


_PROGRAM_BOOK_2022 = _PROGRAM_BOOK_2025.replace("2025", "2022")


def test_layout_opens_markerless_posters_on_leading_only():
    """The 2022 poster listing prints no marker at all - no time, no id, just
    the authors beside the title - so the only separator is the extra leading
    between entries. That signal is weak, so it applies inside a poster section
    and nowhere else; the guard is that the marked books are unaffected."""
    blocks = _layout(_PROGRAM_BOOK_2022)
    if blocks is None:
        return
    posters = [b for b in blocks if b["presentation_type"] == "poster"]
    assert len(posters) > 150, len(posters)
    assert all(b["author_raw"] and b["session_datetime"] for b in posters)
    # the author index sets page numbers with dot leaders, and inside the poster
    # section those lines straddle both columns exactly like a poster does
    assert not [b for b in blocks
                if ". . ." in b["title"] or ". . ." in b["author_raw"]]


def test_leading_rule_leaves_the_marked_books_alone():
    """Applied to any two-column page the leading rule over-generates badly:
    JMIH 2025 went from 544 blocks to 668 before it was confined."""
    for path, expected in ((_PROGRAM_BOOK_2025, 544), (_PROGRAM_BOOK_2023, 620)):
        blocks = _layout(path)
        if blocks is not None:
            assert len(blocks) == expected, f"{path}: {len(blocks)} != {expected}"


def test_ocs_numbered_blocks():
    """The affiliation line fixes both boundaries, wrapped author lists are
    walked back over in full, and the back-of-book author index does not become
    the last abstract's body."""
    from conf_abstracts import parse_ocs_numbered as P
    text = "\n".join([
        "                    1",
        "Fish as proxies of ecological and environmental change",
        "Bronwyn Gillanders1",
        "1. University of Adelaide, Adelaide, SA, Australia",
        "Aquatic ecosystems have shifted from prehistoric baseline states due to change.",
        "                    2",
        "Connecting the dots: The movements of reef manta rays and what they imply",
        "Edy Setyawan1, Calvin Beale2, Mark Erdmann3, Andrew Fischer1, James Haddy1,",
        "Sianipar6",
        "1. University of Tasmania, Newnham, TAS, Australia",
        "2. Misool Eco Resort, Sorong, Indonesia",
        "Reef manta rays were tracked for three years around the Raja Ampat islands.",
        "Gillanders, B     1",
        "Setyawan, E       2",
    ])
    b = P.parse_ocs_numbered_blocks(text)
    assert [x["program_number"] for x in b] == ["1", "2"]
    assert b[0]["title"] == "Fish as proxies of ecological and environmental change"
    assert b[0]["author_raw"] == "Bronwyn Gillanders1"
    # the whole wrapped author list, not just the line above the affiliations
    assert b[1]["author_raw"].startswith("Edy Setyawan1")
    assert b[1]["author_raw"].endswith("Sianipar6")
    assert "Sianipar" not in b[1]["title"]
    assert "2. Misool" in b[1]["affiliation"]
    assert "Gillanders, B" not in (b[1]["abstract_text"] or "")
    assert P.qa_numbers(b, text)["n_missing"] == 0


def test_ocs_numbered_no_affiliation():
    """An author who gave no affiliation must not let a numbered list inside the
    body act as the anchor and pull the whole header into the title."""
    from conf_abstracts import parse_ocs_numbered as P
    text = "\n".join([
        "                    1",
        "Prey density threshold and tidal influence on reef manta ray foraging",
        "Asia O Armstrong",
        "Large tropical and sub-tropical marine animals must meet their energetic "
        "requirements in a largely oligotrophic environment, and they do so seasonally.",
        "3. The critical prey density threshold that triggered feeding was 11.2 mg per m3.",
    ])
    b = P.parse_ocs_numbered_blocks(text)
    assert len(b) == 1
    assert b[0]["title"] == "Prey density threshold and tidal influence on reef manta ray foraging"
    assert b[0]["author_raw"] == "Asia O Armstrong"
    assert b[0]["abstract_text"].startswith("Large tropical")
    assert b[0]["needs_review"] == 1


def test_joint_meeting_elasmo_flag():
    """OCS met jointly with ASFB/NZMSS in 2012, 2015, 2016 and 2019, so those
    books are mostly teleost and the blanket meeting-level elasmo rule is wrong;
    every other OCS year keeps it."""
    from conf_abstracts import tag
    teleost = dict(title="Size-at-settlement in the Southern Rock Lobster",
                   abstract_text="Settlement is a key factor in the fishery.",
                   societies_explicit=[], award=None, society_inferred=None)
    assert tag.resolve(dict(teleost), "OCS", year=2016)["is_elasmo"] == 0
    assert tag.resolve(dict(teleost), "OCS", year=2025)["is_elasmo"] == 1
    assert tag.resolve(dict(teleost), "OCS")["is_elasmo"] == 1     # year unknown
