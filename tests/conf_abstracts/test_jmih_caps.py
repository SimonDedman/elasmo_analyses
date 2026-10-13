"""parse_jmih_caps: the flatbed-rescan parser (JMIH 2001 first)."""
from conf_abstracts import parse_jmih_caps as P

BOOK = P.BOOKS[("JMIH", 2001)]

PAGE = """\f=== PAGE 62 ===
ASIH/AES
*COX FERNANDES, CRISTINA, LUNDBERG, JOHN G.
(CC) Morrill Science Center, Univ. of Massachusetts, Amherst, MA 01002: (JGL) 1900 Benjamin Franklin Pkwy, Academy of Natural
Science, Philadelphia, PA 19103

Tributary Effects on Electric Fish Diversity in Channels of the Amazon River, Brazil
Many processes at different spatial and temporal scales affect the structure of biological communities in large rivers. Tributaries are an
obvious part of the physical framework of river systems that could have significant local and regional influences on habitat and biotic
electric fishes than in mainstem stations above those confluences. (Session P-32, Monday, July 9, Penn Stater, Deans Hall)
Cole, KATHLEEN S.
P.O. Box 42451, University of Louisiana at Lafayette, Lafayette, LA 70506

Unusual gonad morphology in some Scorpaeniformes: homology or convergence due to unique aspects of reproduction?
Caracanthus typicus and C. unipinna are small-sized, obligate coral-dwelling, scorpaeniform fishes (F. Caracanthidae). Histological
analysis of gonad morphology revealed that males and females of both species have an unusual gonad architecture in which the
they may prove useful in providing new insights into phylogenetic relationships between Caracanthidae and other scorpaeniform families.
(Session 29, Monday, July 9, Penn Stater, Room 105, 9:15)
"""


def _recs():
    return P.finalise(P.parse_blocks(PAGE, 44, 137), BOOK)


def test_caps_two_records_split_at_author_lines():
    r = _recs()
    assert len(r) == 2, [x["author_raw"] for x in r]
    assert r[1]["author_raw"].startswith("Cole, KATHLEEN")      # mixed-case small caps


def test_caps_fields():
    a, b = _recs()
    assert a["title"].startswith("Tributary Effects")
    assert a["affiliation"].endswith("PA 19103")
    assert a["session_id"] == "P-32" and a["presentation_type"] == "poster"
    assert "(Session" not in a["abstract_text"]
    assert b["session_datetime"] == "Monday, July 9, 2001 9:15"
    assert b["location"] == "Penn Stater, Room 105"


def test_caps_author_pairs_and_suffixes():
    au = P.split_authors("*JENSEN, CHRISTOPHER F., PRATT, JR., HAROLD L., BRODIE III, EDMUND D.")
    assert [(x["surname"], x["given"], x["suffix"], x["presenter"]) for x in au] == [
        ("JENSEN", "CHRISTOPHER F.", "", True),
        ("PRATT", "HAROLD L.", "JR.", False),
        ("BRODIE", "EDMUND D.", "III", False)]


def test_caps_affiliation_keys():
    au = P.split_authors("*COX FERNANDES, CRISTINA, LUNDBERG, JOHN G.")
    aff = P.affiliations_by_author(
        "(CCF) Morrill Science Center, Amherst, MA 01002; (JGL) 1900 Benjamin Franklin Pkwy, Philadelphia, PA 19103", au)
    assert aff[0].startswith("Morrill") and aff[1].startswith("1900 Benjamin")


def test_caps_author_line_rejects_address():
    assert P.author_pos("A316 EMS, UCSC, Santa Cruz, CA 95064") is None
    assert P.author_pos("(CFJ, LUN, HLP, NEK) 28 Tarzwell Dr., NOAA/NMFS") is None
    assert P.author_pos("*FINK, WILLIAM L., ZELDITCH, MIRIAM L.") == 0
