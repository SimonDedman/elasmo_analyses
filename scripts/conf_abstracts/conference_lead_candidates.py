"""Rank conference series worth chasing organisers for, by how many abstracts
we would gain.

We already chase four series directly (AES, EEA, OCS, SI). The corpus cites a
great many more, and the citation strings themselves say how much is there: a
paper whose only venue is "IV Encuentro colombiano sobre condrictios (2014 -
Medellin): 48" is an abstract in a book we do not hold, and there are 79 of
them from that one meeting. Chasing its organisers is the same move that works
for EEA and OCS, and the count tells us which are worth the email.

Two things have to happen before the counts mean anything:

1. The venue string in `journal` is often OUR truncation ("Programme Booklet of
   The"), so `findspot_raw` in papers_data.json is preferred when it is longer.
2. The same meeting appears under several strings, including outright typos
   ("Progrtamm and Abstracts" for "Programm and Abstracts", 85 rows). Counting
   raw strings splits one series across several rows and buries it.

Usage:
  conference_lead_candidates.py            # writes the review workbook
  conference_lead_candidates.py --print    # summary to stdout, writes nothing
"""
import argparse
import json
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conf_abstracts import config as C  # noqa: E402

PARQUET = C.REPO / "outputs" / "literature_review_enriched.parquet"
PAPERS = C.REPO / "docs" / "papers_data.json"
OUT_XLSX = C.OUT / "conference_lead_candidates.xlsx"

# A venue string that mentions a conference at all.
_CONFERENCE = re.compile(
    r"(conferen|symposi|congres|congreso|simposi|\bmeeting\b|abstract|annual|"
    r"workshop|reuni|encuentro|jornada|colloqu|tagung|convegno|proceeding)", re.I)

# "Proceedings of the X Society" is a JOURNAL, not a meeting to chase. These are
# acquired the ordinary way and would otherwise dominate the ranking.
_JOURNAL_PROCEEDINGS = re.compile(
    r"^Proceedings of the (National Academy|Royal Society|Royal Irish|Geologists|"
    r"Biological Society|Helminthological|Zoological (Society|Institute)|"
    r"California Academy|United States National Museum|Linnean|Yorkshire|"
    r"South Dakota|Indiana|Iowa|Kansas|Oklahoma|Nebraska|Academy of Natural|"
    r"Entomological|Nova Scotian|Japan Academy|Institution of Mechanical)", re.I)

# Typos and spelling variants in the source records, normalised before matching.
_TYPOS = [
    (re.compile(r"\bProgrtamm\b", re.I), "Programm"),          # 85 rows
    (re.compile(r"\bProgramm\b(?!e)", re.I), "Programme"),
    (re.compile(r"\bcondrictios\b", re.I), "Condrictios"),
]

# Ordered rules: the first match wins. (series, organiser/contact route, region,
# already_chasing). Written against the venue strings actually present.
_SERIES = [
    (re.compile(r"Shark\s*International|Sharks\s*International", re.I),
     "Sharks International (SI)", "SI steering committee / host organisation",
     "global", True),
    (re.compile(r"European Elasmobranch Association|\bEEA\b", re.I),
     "European Elasmobranch Association (EEA)", "EEA board / Shark Trust (Cat Gordon, Ali Hood)",
     "Europe", True),
    (re.compile(r"Oceania Chondrichthyan Society", re.I),
     "Oceania Chondrichthyan Society (OCS)", "OCS council (Brit Finucci)", "Oceania", True),
    (re.compile(r"American Elasmobranch Society|\bAES\b", re.I),
     "American Elasmobranch Society (AES)", "AES / JMIH programme officer (David M. Green)",
     "Americas", True),
    (re.compile(r"Encuentro\s+colombiano\s+sobre\s+condrictios|SECC", re.I),
     "Encuentro Colombiano sobre Condrictios", "Fundacion SQUALUS / Colombian organisers",
     "Colombia", False),
    (re.compile(r"Simposium?\s+Nacional\s+de\s+Tiburones\s+y\s+Rayas", re.I),
     "Simposio Nacional de Tiburones y Rayas (Mexico)", "Mexican organising committee",
     "Mexico", False),
    (re.compile(r"Colloque international.*Requins en Afrique|Requins en Afrique", re.I),
     "Colloque international requins en Afrique", "West African organisers / IUCN SSG West Africa",
     "West Africa", False),
    (re.compile(r"SBEEL|Sociedade Brasileira para .*Elasmobr|"
                r"Reuni[ãa]o.*Elasmobr", re.I),
     "Sociedade Brasileira para o Estudo de Elasmobranquios (SBEEL)",
     "SBEEL", "Brazil", False),
    (re.compile(r"Reuni[oó]n.*Tiburones|Tiburones y Rayas", re.I),
     "Latin American shark meetings (other)", "regional organisers", "Latin America", False),
    (re.compile(r"Gulf and Caribbean Fisheries Institute|\bGCFI\b", re.I),
     "Gulf and Caribbean Fisheries Institute (GCFI)", "GCFI secretariat (proceedings are published)",
     "Caribbean", False),
    (re.compile(r"Pacific Shark Workshop", re.I),
     "Pacific Shark Workshop", "workshop conveners", "Pacific", False),
    (re.compile(r"World Congress of Herpetology", re.I),
     "World Congress of Herpetology", "WCH organisers", "global", False),
    (re.compile(r"International Coral Reef Symposium|\bICRS\b", re.I),
     "International Coral Reef Symposium (ICRS)", "ICRS / ISRS secretariat", "global", False),
    (re.compile(r"Indo-?Pacific fish", re.I),
     "Indo-Pacific Fish Conference", "IPFC organisers", "Indo-Pacific", False),
    (re.compile(r"Exploration Scientifique de la Mer|\bCIESM\b", re.I),
     "CIESM (Mediterranean Science Commission)", "CIESM secretariat", "Mediterranean", False),
    (re.compile(r"Tester Memorial Symposium", re.I),
     "Albert L. Tester Memorial Symposium", "University of Hawaii at Manoa", "Pacific", False),
    (re.compile(r"Vertebrate Morphology", re.I),
     "International Congress of Vertebrate Morphology", "ICVM organisers", "global", False),
    (re.compile(r"Mesozoic Fishes", re.I),
     "International Meeting on Mesozoic Fishes", "meeting conveners", "global (palaeo)", False),
    (re.compile(r"World Fisheries Congress", re.I),
     "World Fisheries Congress", "WFC secretariat", "global", False),
    (re.compile(r"American Fisheries Society", re.I),
     "American Fisheries Society symposia", "AFS", "Americas", False),
    (re.compile(r"Biology of Fish", re.I),
     "International Congress on the Biology of Fish", "ICBF organisers", "global", False),
    (re.compile(r"Age Determination of Ocean", re.I),
     "Workshop on Age Determination of Oceanic Pelagic Fishes", "workshop conveners",
     "global", False),
    (re.compile(r"ISC Shark Working Group", re.I),
     "ISC Shark Working Group", "ISC secretariat", "Pacific", False),
    (re.compile(r"Pal[ae][ao]ntolog|Vertebrate Pal|Geologisch|Geological Society|"
                r"Congreso .*Paleontolog|Jahrestagung", re.I),
     "Palaeontology / geology meetings (assorted)", "various", "global (palaeo)", False),
]


def _clean(v):
    v = re.sub(r"^\s*In\s+", "", str(v or "")).strip()
    for pat, rep in _TYPOS:
        v = pat.sub(rep, v)
    return re.sub(r"\s+", " ", v)


def _classify(v):
    for pat, series, contact, region, chasing in _SERIES:
        if pat.search(v):
            return series, contact, region, chasing
    return None, None, None, None


def _held_years():
    """series -> set(years) already in the abstracts DB, so a lead is not raised
    for a book we already hold."""
    out = defaultdict(set)
    con = sqlite3.connect(str(C.DB_PATH))
    for mtg, yr, n in con.execute(
            """SELECT m.meeting, m.year, COUNT(a.abstract_id) FROM meetings m
                 LEFT JOIN abstracts a ON a.meeting_id=m.meeting_id
                GROUP BY m.meeting_id HAVING COUNT(a.abstract_id) > 0"""):
        out[mtg].add(yr)
    con.close()
    return out


_DB_KEY = {"Sharks International (SI)": "SI",
           "European Elasmobranch Association (EEA)": "EEA",
           "American Elasmobranch Society (AES)": "AES"}


def collect():
    papers = {}
    for p in json.loads(PAPERS.read_text()):
        lid = str(p.get("literature_id") or "").replace(".0", "").strip()
        if lid:
            papers[lid] = p
    tbl = pq.read_table(PARQUET, columns=["literature_id", "year", "journal", "title"])
    rows = []
    for r in tbl.to_pylist():
        lid = str(r["literature_id"] or "").replace(".0", "").strip()
        p = papers.get(lid) or {}
        journal, findspot = str(r["journal"] or ""), str(p.get("findspot_raw") or "")
        # findspot is the fuller string wherever SR recorded one; journal is
        # frequently our own truncation of it.
        venue = _clean(findspot if len(findspot) > len(journal) else journal)
        if not venue or not _CONFERENCE.search(venue) or _JOURNAL_PROCEEDINGS.match(venue):
            continue
        series, contact, region, chasing = _classify(venue)
        yr = None
        m = re.search(r"\b(19|20)\d{2}\b", venue)
        if m:
            yr = int(m.group(0))
        rows.append(dict(literature_id=lid, year=r["year"], venue_year=yr, venue=venue,
                         title=r["title"], series=series, contact=contact, region=region,
                         already_chasing=chasing, outstanding=lid in papers))
    return rows


def write_workbook(rows, summary, unclassified):
    """Review workbook: Info first, then the ranked leads, the venue strings
    behind each (so a bad grouping is visible), and what stayed unclassified."""
    import pandas as pd
    from openpyxl import load_workbook
    from openpyxl.styles import Alignment, Font
    from openpyxl.utils import get_column_letter

    info = pd.DataFrame({"Conference acquisition leads": [
        "WHY THIS EXISTS",
        "We chase four conference series directly (AES, EEA, OCS, SI). The corpus cites many",
        "more, and the citation strings say how much is in each: a paper whose only venue is",
        "\"IV Encuentro colombiano sobre condrictios (2014 - Medellin): 48\" is an abstract in a",
        "book we do not hold. This ranks the series by how many such records we would gain.",
        "",
        "WHAT WAS DONE AUTOMATICALLY BEFORE YOU SAW THIS",
        "1. Venue resolved per record. The `journal` field is often our own truncation",
        "   (\"Programme Booklet of The\"), so papers_data.json's `findspot_raw` is used wherever",
        "   it is longer. That alone named 47 EEA 2011 Berlin records and 32 OCS ones.",
        "2. Typos normalised. \"Progrtamm and Abstracts\" (85 records, all EEA 2009/2012/2013)",
        "   would otherwise have ranked as a series of its own.",
        "3. Variants merged. \"Programm and Abstracts of Shark International\" and \"Programm and",
        "   Poster Abstracts of Shark International\" are one meeting, SI 2014 Durban.",
        "4. Journals excluded. \"Proceedings of the National Academy of Sciences\" and its kind",
        "   are journals, not meetings to chase, and would otherwise dominate the ranking.",
        "5. Years we already hold were subtracted, using database/conference_abstracts.db.",
        "",
        "WHAT EACH TAB HOLDS",
        "Leads      - one row per conference series, ranked by abstracts we would gain.",
        "Records    - every corpus record behind those counts, so any lead can be spot-checked.",
        "Venue strings - the raw strings grouped into each series. Read this to catch a wrong",
        "             grouping; the rules are regexes and they are not infallible.",
        "Unclassified - conference-ish venues no rule matched. Mostly truncated strings with no",
        "             findspot to resolve them, plus genuine one-off edited volumes.",
        "",
        "WHAT YOU NEED TO DO",
        "1. On 'Leads', fill the 'chase' column: YES / NO / LATER.",
        "2. On 'Leads', fill 'contact' if you know a better route than the one suggested.",
        "3. Skim 'Venue strings' for any series whose strings do not belong together, and note",
        "   it in 'notes' on the Leads tab.",
        "4. Send it back. YES rows get added to the coverage matrix as new series columns and",
        "   go into the same sourcing effort as EEA/OCS/SI.",
        "",
        "PROVENANCE AND KNOWN GAPS",
        "Source: outputs/literature_review_enriched.parquet (the corpus of record) joined to",
        "docs/papers_data.json for findspot_raw. Held years from database/conference_abstracts.db.",
        "Generated " + __import__("datetime").date.today().isoformat() + " by",
        "scripts/conf_abstracts/conference_lead_candidates.py.",
        "",
        "GAP: this only sees meetings the corpus already cites. A conference series nobody has",
        "cited into Shark References is invisible here, so absence from this list is not",
        "evidence that a series does not exist.",
        "GAP: 'want' counts records with no PDF held. A few will be papers rather than",
        "abstracts, since some meetings publish full proceedings.",
    ]})

    leads = pd.DataFrame(summary)
    leads.insert(0, "chase", "")
    leads.insert(1, "notes", "")
    leads = leads.rename(columns={"records": "records_cited", "outstanding": "want",
                                  "distinct_venue_strings": "venue_strings"})
    recs = pd.DataFrame([r for r in rows if r["series"]])[
        ["series", "year", "venue_year", "outstanding", "literature_id", "title", "venue"]]
    recs = recs.sort_values(["series", "venue_year", "year"], na_position="last")
    vs = (pd.DataFrame([dict(series=r["series"], venue=r["venue"]) for r in rows if r["series"]])
            .value_counts().reset_index(name="records").sort_values(["series", "records"],
                                                                   ascending=[True, False]))
    unc = (pd.DataFrame(sorted(unclassified.items(), key=lambda kv: -kv[1]),
                        columns=["venue", "records"]))

    C.OUT.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(OUT_XLSX, engine="openpyxl") as xw:
        info.to_excel(xw, sheet_name="Info", index=False)
        leads.to_excel(xw, sheet_name="Leads", index=False)
        recs.to_excel(xw, sheet_name="Records", index=False)
        vs.to_excel(xw, sheet_name="Venue strings", index=False)
        unc.to_excel(xw, sheet_name="Unclassified", index=False)

    wb = load_workbook(OUT_XLSX)
    for name in wb.sheetnames:
        ws = wb[name]
        ws.freeze_panes = "A2"
        for cell in ws[1]:
            cell.font = Font(bold=True)
        if name != "Info":
            ws.auto_filter.ref = ws.dimensions
        for col in ws.columns:
            letter = get_column_letter(col[0].column)
            width = max((len(str(c.value)) for c in col if c.value is not None), default=10)
            ws.column_dimensions[letter].width = min(max(width + 2, 10), 95)
        if name == "Info":
            for row in ws.iter_rows(min_row=2):
                row[0].alignment = Alignment(wrap_text=False)
    wb._sheets = [wb["Info"]] + [wb[n] for n in wb.sheetnames if n != "Info"]
    wb.save(OUT_XLSX)
    print(f"\nwrote {OUT_XLSX}")


def summarise(rows):
    held = _held_years()
    by = defaultdict(lambda: dict(records=0, outstanding=0, years=set(), venues=set(),
                                  contact=None, region=None, chasing=None))
    for r in rows:
        if not r["series"]:
            continue
        s = by[r["series"]]
        s["records"] += 1
        s["outstanding"] += bool(r["outstanding"])
        y = r["venue_year"] or r["year"]
        if y:
            s["years"].add(int(y))
        s["venues"].add(r["venue"][:120])
        s["contact"], s["region"], s["chasing"] = r["contact"], r["region"], r["already_chasing"]
    out = []
    for series, s in by.items():
        have = held.get(_DB_KEY.get(series, ""), set())
        gap = sorted(y for y in s["years"] if y not in have)
        out.append(dict(
            series=series, records=s["records"], outstanding=s["outstanding"],
            years=", ".join(str(y) for y in sorted(s["years"])),
            years_not_held=", ".join(str(y) for y in gap),
            distinct_venue_strings=len(s["venues"]),
            already_chasing="yes" if s["chasing"] else "no",
            region=s["region"], contact_route=s["contact"]))
    # rank by what a successful ask would actually add
    out.sort(key=lambda d: (-d["outstanding"], -d["records"]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--print", dest="show", action="store_true")
    a = ap.parse_args()
    rows = collect()
    summary = summarise(rows)
    unclassified = defaultdict(int)
    for r in rows:
        if not r["series"]:
            unclassified[r["venue"][:110]] += 1

    print(f"{len(rows)} corpus records cite a conference venue; "
          f"{sum(1 for r in rows if r['outstanding'])} of them we do not hold")
    print(f"{len(summary)} series identified, {sum(unclassified.values())} records unclassified\n")
    print(f"{'series':46s}{'recs':>6s}{'want':>6s}  {'chasing':8s} years not held")
    for d in summary:
        print(f"  {d['series'][:44]:44s}{d['records']:6d}{d['outstanding']:6d}  "
              f"{d['already_chasing']:8s}{d['years_not_held'][:40]}")
    if a.show:
        print("\ntop unclassified venue strings:")
        for v, n in sorted(unclassified.items(), key=lambda kv: -kv[1])[:25]:
            print(f"  {n:4d}  {v}")
        return
    write_workbook(rows, summary, unclassified)


if __name__ == "__main__":
    main()
