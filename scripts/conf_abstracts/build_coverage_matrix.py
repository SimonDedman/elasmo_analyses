"""Build the conference-abstract coverage matrix (xlsx).

Sheets (order): Legend & Notes | Conferences | Coverage | Dashboard.
- Coverage: year x series (all 24 series), colour-coded red->green by status. ASIH/JMIH/Other
  collapsed to one 'ASIH/JMIH' column (they share one source book); AES kept
  separate (carries the elasmo count). Cells = "Location; Status". 'No
  conference' cells are left blank/unshaded.
- Dashboard: per-society totals bar chart + abstracts-over-time line chart.

Sources: the conference_abstracts DB; Cat Gordon (EEA locations + status);
Brit Finucci (OCS pending); Carylanne (1992-2024 hardcopy); AESconfLocations
(ASIH/JMIH host cities 1916-2025); known SI years.
"""
import argparse
import csv
import json
import re
import sqlite3
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

REPO = Path(__file__).resolve().parents[2]
DB = REPO / "database" / "conference_abstracts.db"
OUT = REPO / "outputs" / "conference_coverage_matrix.xlsx"
ASIH_CSV = REPO / "database" / "asih_meetings.csv"
CONFERENCES = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers/Conferences")
# mirrors config.SKIP_NAME_FRAGMENTS; this module is standalone and does not
# import the conf_abstracts package.
SKIP_NAME_FRAGMENTS = ("_phonescan", "CopeiaMeetingSummary")

# status order (red -> green). 'Programme' distinguishes a schedule/grid PDF we
# hold (NO abstract bodies, abstract book still needed) from 'Digital' = a
# parseable abstract-book PDF we hold and can ingest.
# Colour = distance from a complete, searchable set of abstracts, worst first.
# The ramp runs red -> orange -> amber -> yellow -> green in this order:
#   Missing < Schedule < Hardcopy < OCR < Programme < Pending < Digital < Ingested
# Rationale (Simon, 2026-08-27): "Digital" means the book is in hand and only
# needs processing, so it is nearly done and reads light green; "OCR" means the
# abstracts are in but from a degraded scan we still want re-sourced, so it sits
# back beside "Hardcopy" (Simon, 2026-08-27: functionally the same problem);
# "Schedule" is titles without abstract text, useful but
# not abstracts, so it sits just above Missing; "Hardcopy" and "Programme" are
# the same practical problem (we need the abstract book) and sit adjacent.
# 'Extracted' (Simon, 2026-09-01) separates "abstracts are in the DB" from
# "abstracts are in the DB at full quality". The regex parsers put real,
# body-bearing records in for several JMIH years, but their titles and author
# lists are weak and those books are queued for Fable re-extraction — calling
# that "Ingested" overclaimed, and calling it "Digital" would have hidden the
# ~2,800 abstracts we genuinely hold.
STATUS_ORDER = ["Missing", "Schedule", "Hardcopy", "OCR", "Programme",
                "Pending", "Digital", "Extracted", "Ingested"]
FILL = {
    "Missing": "E06666",    # red: nothing exists anywhere
    "Schedule": "ED9C6B",   # red-orange: titles/authors only, no abstract text
    "Hardcopy": "F6B26B",   # dark orange: paper book known, nothing digital
    "OCR": "F9CB9C",        # light orange: abstracts in but from a degraded scan
    "Programme": "FFD966",  # amber: digital programme held, book still needed
    "Pending": "FFE599",    # yellow: a named contact has it or is looking
    "Digital": "B6D7A8",    # light green: book in hand, nothing extracted yet
    "Extracted": "93C47D",  # mid green: abstracts in the DB, re-extraction queued
    "Ingested": "6AA84F",   # green: fully extracted and merged — done
    "NA": None,
}
# (location, status, action-note). status conveys what we HOLD; the note says
# what's still NEEDED so the sheet is self-documenting.
# EEA abstract books extracted via Fable (2026-08-14): 731 abstracts across 11
# meetings into conference_abstracts_fable.db. "Ingested" notes carry the count.
# Host cities for the meetings we have no book for. 2003 and 2005-2009 from the
# EEA's own meetings page (eulasmo.org/scientific-meetings, read 2026-08-27);
# meeting numbers there confirm an unbroken annual series from 1997 (1st), which
# matches the 2002 Cardiff booklet calling itself the 6th. 1998 Lisbon is from
# APECE's account of hosting that year. 1997, 1999-2001 still unknown.
EEA_EARLY = {
    2003: ("San Marino", "7th EEA; Ali Hood searching her paperwork (2026-08-27)"),
    2005: ("Monaco", "9th EEA; Ali Hood searching her paperwork (2026-08-27)"),
    2006: ("Hamburg", "10th EEA; Ali Hood searching her paperwork (2026-08-27)"),
    2007: ("Brest", "11th EEA; Ali Hood searching her paperwork (2026-08-27)"),
    2008: ("Lisbon", "12th EEA; Ali Hood searching her paperwork (2026-08-27)"),
    2009: ("Palma de Majorca", "13th EEA; Ali Hood searching her paperwork (2026-08-27)"),
}
EEA_EARLY_LOC = {1998: "Lisbon"}

# Host group per year (Cat Gordon, 2026-07-28), drives the per-group asks.
EEA_HOST = {
    2010: "IEG (Ireland)", 2011: "DEG (Germany)", 2012: "GRIS (Italy)",
    2013: "Shark Trust (UK)", 2014: "NEV (Netherlands)", 2015: "APECE (Portugal)",
    2016: "Shark Trust (UK)", 2017: "NEV (Netherlands)", 2018: "APECE (Portugal)",
    2019: "GRIS (Italy)", 2021: "NEV (Netherlands)",
    2022: "Shark Trust / Submon / Lamna", 2023: "Shark Trust (UK)",
    2024: "iSea (Greece)", 2025: "NEV (Netherlands)", 2026: "Shark Trust (UK)",
}
EEA = {
    2002: ("Cardiff", "Digital", "abstract booklet (Word) found by Ali Hood 2026-08-27; queued for extraction"),
    2004: ("London", "Ingested", "55 abstracts (Fable)"),
    2010: ("Galway", "Hardcopy", "Cat holds a hardcopy but has no scanning capacity; digital copy needed from IEG (Ireland)"),
    2011: ("Berlin", "Ingested", "58 abstracts (Fable)"),
    2012: ("Milan", "Hardcopy", "Cat holds a hardcopy but has no scanning capacity; digital copy needed from GRIS (Italy)"),
    2013: ("Plymouth", "Ingested", "93 abstracts (Fable)"),
    2014: ("Leeuwarden", "Ingested", "61 abstracts (Fable)"),
    2015: ("Peniche", "Digital", "19th EEA Book of Abstracts (99pp, born-digital) held by Simon all along; queued for extraction"),
    2016: ("Bristol", "Ingested", "93 abstracts (Fable)"),
    2017: ("Amsterdam", "Schedule", "62 talks ingested, NO abstract bodies; Cat holds a hardcopy but has no scanning capacity; abstract book needed from NEV"),
    2018: ("Peniche", "Ingested", "75 abstracts (Fable)"),
    2019: ("Rende", "Ingested", "136 abstracts (Fable)"),
    2020: ("?", "Missing", "unknown whether a meeting was held: Cat thinks it was online for covid but was on maternity leave and is unsure; organiser unknown; abstracts unknown"),
    2021: ("Leiden", "Programme", "programme only; abstract book needed from NEV"),
    2022: ("Valencia (=SI2022)", "Digital", "full SI2022 abstract book received 2026-08-27; queued for extraction"),
    2023: ("Brighton", "Ingested", "oral 64 + poster 34 = 98 abstracts (Fable)"),
    2024: ("Thessaloniki", "Digital", "clean abstract book received from Cat 2026-08-27; queued for extraction"),
    2025: ("Rotterdam", "Programme", "agenda only; Cat has no abstract book and is unsure one was produced; NEV/Irene to confirm whether it exists"),
    2026: ("online", "Pending", "will be digital (Shark Trust hosting)"),
}
SI = {2010: ("Cairns", "Missing", "find source"),
      2014: ("Durban", "Missing", "find source"),
      2018: ("Joao Pessoa", "Ingested", ""),
      2022: ("Valencia", "Digital", "full abstract book received 2026-08-27; queued (schedule already ingested)"),
      2026: ("Colombo", "Ingested", "")}
# JMIH/ASIH years where we hold a PDF that is NOT an ingestable abstract book:
# a grid programme (2017/2019 — detail doesn't extract; get the abstract book)
# or a schedule-only programme (2026 — has a text layer, no abstract bodies).
JMIH_PROGRAMME = {
    2017: "grid programme only — abstract book needed (Carylanne)",
    2019: "grid programme only — abstract book needed (Carylanne)",
    2026: "schedule-only programme (OCR text layer OK, not yet parsed) — abstract book needed",
}
# OCS meetings we can evidence from public sources (read 2026-08-27); Brit
# Finucci is confirming the full series and locations.
OCS = {
    2012: ("Adelaide", "joint with ASFB; Brit Finucci confirming"),
    2018: ("North Stradbroke Is.", "Moreton Bay Research Station; Brit Finucci confirming"),
    2024: ("Geelong", "Brit Finucci confirming"),
}
SERIES = ["AES", "ASIH", "HL", "SSAR", "NIA", "EEA", "SI"]


# Human-editable text lives here as well as in the sheet. The builder REGENERATES
# the whole workbook, so any wording Simon edits in Legend & Notes would be lost
# on the next run (it happened, 2026-08-27). On every build we first read the
# existing sheet's legend meanings and notes, persist them to this JSON, and then
# emit those rather than the code defaults. Code defaults therefore only supply
# text for statuses/notes that have never existed in the sheet.
# To deliberately adopt new code wording, run with --reset-legend.
LEGEND_STORE = REPO / "data" / "matrix_legend.json"


def harvest_legend_edits(default_meanings, default_notes):
    """Return (meanings, notes) preferring what is already in the sheet/store."""
    store = {"meanings": {}, "notes": []}
    if LEGEND_STORE.exists():
        try:
            store = json.loads(LEGEND_STORE.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"  legend store unreadable ({e}); falling back to code defaults")
    # the live sheet wins over the store: it holds the most recent human edit
    if OUT.exists():
        try:
            ws = load_workbook(OUT)["Legend & Notes"]
            for row in ws.iter_rows(min_row=2, max_row=40, max_col=2, values_only=True):
                st, mean = row[0], row[1]
                if st and mean and st in default_meanings:
                    store["meanings"][st] = mean
            notes, seen_marker = [], False
            for (val,) in ws.iter_rows(min_row=2, max_col=1, values_only=True):
                if val == "NOTES:":
                    seen_marker = True
                    continue
                if seen_marker and val:
                    notes.append(val)
            if notes:
                store["notes"] = notes
        except Exception as e:
            print(f"  could not read existing legend ({e})")
    meanings = dict(default_meanings)
    changed = []
    for st, mean in store.get("meanings", {}).items():
        if st in meanings and mean != meanings[st]:
            changed.append(st)
        meanings[st] = mean
    notes = store.get("notes") or default_notes
    missing = [n for n in default_notes if n and n not in notes]
    if changed:
        print(f"  PRESERVED edited legend wording for: {', '.join(sorted(changed))}")
    if missing:
        print(f"  {len(missing)} code-generated note(s) NOT in the sheet (kept out, "
              f"edited notes take precedence): {missing[0][:70]}...")
    LEGEND_STORE.parent.mkdir(parents=True, exist_ok=True)
    LEGEND_STORE.write_text(json.dumps({"meanings": meanings, "notes": notes},
                                       indent=1, ensure_ascii=False), encoding="utf-8")
    return meanings, notes


def load_asih_locations():
    locs = {}
    with open(ASIH_CSV) as fh:
        for row in csv.DictReader(fh):
            try:
                locs[int(row["year"])] = row["location"].strip()
            except (ValueError, KeyError):
                pass
    return locs


JMIH_LOC = load_asih_locations()
JMIH_LOC.setdefault(2026, "New Orleans, LA")


# ---------------------------------------------------------------------------
# Conference series metadata (the "Conferences" tab).
#
# One row per series: the four we chase directly, plus every other series the
# corpus cites (conference_lead_candidates.py). Years, frequency, organisers and
# websites were checked against the societies' own pages on 2026-09-04; a blank
# means NOT FOUND, never a guess, because a wrong contact address costs a real
# email to a real person.
#
# n_needed is filled in at build time, not typed here: it is the number of
# corpus records citing that series whose PDF we do not hold, straight from
# conference_lead_candidates. So it moves as the corpus does.
#
# Fields: (series, year_from, year_to, frequency, organisers, website, contact)
# frequency: 1 = annual, 2 = biennial, 4 = every four years, 0 = one-off.
CONFERENCE_META = [
    dict(series="ASIH / JMIH", lead_key=None, year_from=1913, year_to=None, frequency=1,
         organisers="Programme officers: Maureen 'Mo' Donnelly (to ~2014), Marty Crump "
                    "(2015-2019), David M. Green (2020- ). Meeting planned by the MMPC "
                    "(chairs Ed Heist, then Henry Mushinsky); logistics by Kansas State "
                    "Conference Management Services. Submissions run on Oxford Abstracts.",
         website="https://www.asih.org/meetings/recent-meetings (abstract books, 2005 on)",
         contact="david.m.green@mcgill.ca"),
    dict(series="American Elasmobranch Society (AES)",
         lead_key="American Elasmobranch Society (AES)",
         # 1985, not 1983 (corrected 2026-09-06). The ordinal->year anchor check
         # flagged this: three independent citations in our own corpus give the
         # 13th meeting as 1997, the 16th as 2000 and the 26th as 2010, and all
         # three imply a first meeting in 1985. The abstracts DB agrees — its
         # earliest located AES meeting is 1985, Knoxville TN — as does
         # elasmo.org, whose abstract bodies start at 1985 and 404 for 1983-84.
         # AES was FOUNDED in 1983; the numbered annual meetings start in 1985,
         # and it is the meeting series this column counts.
         year_from=1985, year_to=None, frequency=1,
         organisers="AES officers; meets inside JMIH, so the JMIH programme officer holds "
                    "the abstracts. EXCEPTION 2018: AES met at Sharks International instead.",
         website="https://elasmo.org/meetings/abstracts/abst<YYYY>/ — full abstracts with "
                 "bodies for EVERY year 1985-2005 (404 for 1983-84 and 2006+); harvested",
         contact="via JMIH programme officer, david.m.green@mcgill.ca"),
    dict(series="European Elasmobranch Association (EEA)",
         lead_key="European Elasmobranch Association (EEA)",
         year_from=1997, year_to=None, frequency=1,
         organisers="EEA board. Ali Hood (Secretariat, Shark Trust); Cat Gordon (Shark "
                    "Trust) holds/sources the abstract books. Host national society varies "
                    "by year (IEG, GRIS, APECE, NEV ...).",
         website="http://eulasmo.org/ ; host cities per year at "
                 "http://eulasmo.org/scientific-meetings",
         contact="Cat Gordon / Ali Hood, Shark Trust"),
    dict(series="Oceania Chondrichthyan Society (OCS)",
         lead_key="Oceania Chondrichthyan Society (OCS)",
         year_from=2005, year_to=None, frequency=2,
         organisers="OCS council. Brit Finucci (past president, and IUCN SSG Red List "
                    "Authority Coordinator) is collating the series for us, with council "
                    "approval. Meetings seen: 2008, 2011, 2012 (Adelaide, joint with ASFB), "
                    "2018, 2022 (virtual), 2024 Geelong, 2025 Mooloolaba (20th anniversary).",
         website="https://www.oceaniasharks.org.au/", contact="Brit Finucci"),
    dict(series="Sharks International (SI)", lead_key="Sharks International (SI)",
         year_from=2010, year_to=None, frequency=4,
         organisers="Rotating local host, and the SI 2018 book's executive and "
                    "scientific committees carry the previous hosts forward, which is the "
                    "best evidence available for who ran the early ones. "
                    "2010 CAIRNS (6-11 June, Rydges Esplanade Resort): no source names the "
                    "host body. Michelle Heupel (AIMS / James Cook University) is the sole "
                    "Australian on the 2018 committee, consistent with Simon's "
                    "recollection of Heupel and Colin Simpfendorfer (also JCU) running it. "
                    "TREAT AS LIKELY, NOT CONFIRMED. "
                    "2014 DURBAN (2-6 June): hosted by the KwaZulu-Natal Sharks Board, 169 "
                    "orals + 52 posters, which matches the 170 records we want almost "
                    "exactly. Geremy Cliff (Head of Research at the KZN Sharks Board for "
                    "~30 years) sits on the 2018 committee and is the obvious approach; "
                    "Sabine Wintner (KZNSB / UKZN) is the other senior elasmobranch "
                    "scientist there. No source names the committee chair. "
                    "2018 Joao Pessoa: UFPB, president Ricardo de Souza Rosa, joint with "
                    "AES, SBEEL and Fundacion SQUALUS. 2022 Valencia. 2026 Colombo, hosted "
                    "by Blue Resources Trust.",
         website="https://www.sharksinternational.org.br/noticia/23-abstract-book/"
                 "menu_abstract_book.html (2018 book, which we hold)",
         contact="sharksinternational2014@gmail.com (2014 organising committee, from the "
                 "KZN Sharks Board announcement; likely dormant — go via Geremy Cliff or "
                 "Sabine Wintner at the KZN Sharks Board for 2014, and Michelle Heupel "
                 "or Colin Simpfendorfer for 2010)"),
    dict(series="Encuentro Colombiano sobre Condrictios (ECC)",
         lead_key="Encuentro Colombiano sobre Condrictios",
         year_from=2008, year_to=2018, frequency=2,
         organisers="Fundacion SQUALUS. I 2008 Bogota, II 2010 Cali, III 2012 Santa Marta, "
                    "IV 2014 Medellin, V 2016 Bogota, VI 2018 Joao Pessoa. CONFIRMED "
                    "2026-09-04: the VI IS ALREADY HELD — the SI 2018 book is the joint "
                    "book for four meetings at once (Sharks International, the 34th AES "
                    "annual meeting, the X SBEEL Reuniao and the VI ECC), and we have its "
                    "427 abstracts. So the ask is editions I-V, and the corpus cites only "
                    "the IV.",
         website="http://squalus.org/index.php/encuentro-condrictios/ ; "
                 "https://encuentro.squalus.org",
         contact="squalus@germanm1.sg-host.com (from the site; verify before using)"),
    dict(series="Sociedade Brasileira para o Estudo de Elasmobranquios (SBEEL)",
         lead_key="Sociedade Brasileira para o Estudo de Elasmobranquios (SBEEL)",
         year_from=1997, year_to=None, frequency=2,
         organisers="SBEEL. The X Reuniao was held in 2018 inside the Sharks International "
                    "book, so at least nine earlier meetings exist. The corpus cites only "
                    "the II, which is why n_needed is 1 — that number is a floor and badly "
                    "understates this series.",
         website="", contact=""),
    dict(series="Simposio Nacional de Tiburones y Rayas (SOMEPEC, Mexico)",
         lead_key="Simposio Nacional de Tiburones y Rayas (Mexico)",
         year_from=2004, year_to=None, frequency=2,
         organisers="Sociedad Mexicana de Peces Cartilaginosos (SOMEPEC). HARVESTED "
                    "2026-09-04 from somepec.org, no request to anyone needed: I 2004 "
                    "(with the III Semana del Tiburon, UNAM), III 2008, IV 2010 (UNAM), "
                    "VII 2016, XI 2025 as abstract books, plus the IX 2021 programme. All "
                    "five books carry a clean text layer. STILL MISSING: II, V, VI 2014 "
                    "Mazatlan (the edition our corpus cites), VIII 2019 Playa del Carmen "
                    "(joint with the I Congreso Latinoamericano de Tiburones, Rayas y "
                    "Quimeras), and X. Ask info@somepec.org for exactly those five.",
         website="https://somepec.org/memorias/ ; back volumes under "
                 "https://somepec.org/wp-content/uploads/ ; scraper "
                 "scripts/conf_abstracts/scrape_somepec.py",
         contact="info@somepec.org ; +52 55 5034 1708"),
    dict(series="Colloque international requins en Afrique de l'Ouest",
         lead_key="Colloque international requins en Afrique", year_from=2011,
         year_to=2011, frequency=0,
         organisers="Commission Sous-Regionale des Peches (CSRP / SRFC), an "
                    "intergovernmental body for seven West African states. Dakar, Senegal, "
                    "25-27 July 2011, on the conservation and sustainable management of "
                    "shark populations in West Africa. A single meeting, not a series — "
                    "kept on the list anyway: 48 abstracts is one email and one book, and "
                    "it is the only West African material in the corpus.",
         website="https://spcsrp.org/", contact=""),
    dict(series="Gulf and Caribbean Fisheries Institute (GCFI)",
         lead_key="Gulf and Caribbean Fisheries Institute (GCFI)",
         year_from=1948, year_to=None, frequency=1,
         organisers="GCFI secretariat. Every meeting since 1948 is in the annual "
                    "Proceedings and every PAPER is a free PDF at proceedings.gcfi.org "
                    "(verified 2026-09-04), so nobody needs asking and nobody should be "
                    "assigned these. The 31 corpus records were sitting on the "
                    "needs-library queue and are now acquisition_route=gcfi_proceedings.",
         website="https://proceedings.gcfi.org/ (per-paper PDFs) ; https://www.gcfi.org/ ; "
                 "back volumes also in the NOAA Institutional Repository",
         contact=""),
    dict(series="Pacific Shark Workshop", lead_key="Pacific Shark Workshop",
         year_from=2011, year_to=2012, frequency=0,
         organisers="", website="", contact=""),
    dict(series="ISC Shark Working Group", lead_key="ISC Shark Working Group",
         year_from=2013, year_to=None, frequency=1,
         organisers="International Scientific Committee for Tuna and Tuna-like Species in "
                    "the North Pacific Ocean; the Shark Working Group meets within it.",
         website="https://isc.fra.go.jp/", contact=""),
    # --- lower priority / not elasmobranch meetings -------------------------
    dict(series="World Congress of Herpetology", lead_key="World Congress of Herpetology",
         year_from=1989, year_to=None, frequency=4,
         organisers="World Congress of Herpetology committee. Every 3-5 years.",
         website="https://www.worldcongressofherpetology.org/", contact=""),
    dict(series="Indo-Pacific Fish Conference (IPFC)", lead_key="Indo-Pacific Fish Conference",
         year_from=1981, year_to=None, frequency=4,
         organisers="Rotating host. IPFC-11 2023 Auckland (joint with ASFB); "
                    "IPFC-12 2025 Taiwan.",
         website="https://sfi-cybium.fr/en/indo-pacific-fish-conference", contact=""),
    dict(series="International Coral Reef Symposium (ICRS)",
         lead_key="International Coral Reef Symposium (ICRS)",
         year_from=1969, year_to=None, frequency=4,
         organisers="International Coral Reef Society. ICRS-16 2026 Auckland.",
         website="https://coralreefs.org/", contact=""),
    dict(series="World Fisheries Congress", lead_key="World Fisheries Congress",
         year_from=1992, year_to=None, frequency=4, organisers="", website="", contact=""),
    dict(series="American Fisheries Society symposia",
         lead_key="American Fisheries Society symposia",
         # 1871, not 1870 (corrected 2026-09-06). Our own citation gives the
         # 141st Annual Meeting as 2011, which implies a first meeting in 1871.
         # AFS was FOUNDED in 1870; its first annual meeting fell the next year,
         # so meeting-number arithmetic needs 1871. Single anchor, so weaker
         # evidence than the AES correction above.
         year_from=1871, year_to=None, frequency=1,
         organisers="American Fisheries Society.", website="https://fisheries.org/",
         contact=""),
    dict(series="International Congress on the Biology of Fish",
         lead_key="International Congress on the Biology of Fish",
         year_from=1994, year_to=None, frequency=2, organisers="", website="", contact=""),
    dict(series="International Meeting on Mesozoic Fishes",
         lead_key="International Meeting on Mesozoic Fishes",
         year_from=1993, year_to=None, frequency=4,
         organisers="Meeting conveners vary; 6th meeting edited by Schwarz & Kriwet.",
         website="", contact=""),
    dict(series="International Congress of Vertebrate Morphology (ICVM)",
         lead_key="International Congress of Vertebrate Morphology",
         year_from=1986, year_to=None, frequency=3, organisers="", website="", contact=""),
    dict(series="CIESM Congress (Mediterranean Science Commission)",
         lead_key="CIESM (Mediterranean Science Commission)",
         year_from=1919, year_to=None, frequency=3,
         organisers="Commission Internationale pour l'Exploration Scientifique de la Mer "
                    "Mediterranee.",
         website="https://ciesm.org/", contact=""),
    dict(series="Albert L. Tester Memorial Symposium",
         lead_key="Albert L. Tester Memorial Symposium",
         year_from=1976, year_to=None, frequency=1,
         organisers="University of Hawaii at Manoa.", website="", contact=""),
    dict(series="Workshop on Age Determination of Oceanic Pelagic Fishes",
         lead_key="Workshop on Age Determination of Oceanic Pelagic Fishes",
         year_from=1983, year_to=1983, frequency=0, organisers="", website="", contact=""),
    dict(series="Palaeontology / geology meetings (assorted)",
         lead_key="Palaeontology / geology meetings (assorted)",
         year_from=1973, year_to=None, frequency=0,
         organisers="NOT ONE SERIES — a bucket of many national and international palaeo "
                    "and geology meetings. Split it before chasing anyone.",
         website="", contact=""),
]


def _needed_by_series():
    """series -> corpus records citing it whose PDF we do not hold. Live from
    conference_lead_candidates, so it moves with the corpus. Returns {} if the
    parquet is unavailable, and the column then reads "n/a" rather than 0 —
    "we need none" and "we could not count" must not look the same."""
    try:
        import sys
        from pathlib import Path as _P
        sys.path.insert(0, str(_P(__file__).resolve().parents[1]))
        from conf_abstracts import conference_lead_candidates as L
        return {d["series"]: d["outstanding"] for d in L.summarise(L.collect())}
    except Exception as e:                                    # noqa: BLE001
        print(f"  n_needed unavailable ({type(e).__name__}: {e})")
        return {}


def _conferences_sheet(wb):
    """Metadata for every conference series we know of, chased or not."""
    ws = wb.create_sheet("Conferences")
    needed = _needed_by_series()
    cols = ["series", "year_from", "year_to", "frequency", "n_needed",
            "organisers", "website", "contact"]
    ws.append(cols)
    for c in ws[1]:
        c.font = Font(bold=True)
        c.alignment = Alignment(vertical="top")
    for m in CONFERENCE_META:
        if not needed:
            n = "n/a — count unavailable"
        elif not m["lead_key"]:
            # JMIH's elasmobranch abstracts are cited as AES; counting them here
            # too would double them.
            n = "n/a — counted under AES"
        else:
            n = needed.get(m["lead_key"], 0)
        ws.append([m["series"], m["year_from"], m["year_to"] or "ongoing",
                   m["frequency"], n, m["organisers"], m["website"], m["contact"]])
    ws.freeze_panes = "B2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(cols))}{ws.max_row}"
    for letter, width in zip("ABCDEFGH", (46, 10, 10, 11, 10, 62, 58, 40)):
        ws.column_dimensions[letter].width = width
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(vertical="top",
                                    wrap_text=c.column_letter in ("F", "G", "H"))
    # a note row under the table rather than a second sheet
    ws.append([])
    ws.append(["frequency: 1 = annual, 2 = biennial, 3 = every three years, "
               "4 = every four years, 0 = one-off / irregular"])
    ws.append(["n_needed: corpus records citing that series whose PDF we do NOT hold "
               "(scripts/conf_abstracts/conference_lead_candidates.py). It counts "
               "abstracts we can already name, so it is a floor, not the size of the series."])
    ws.append(["A BLANK organisers/website/contact means not found on 2026-09-04, "
               "never a guess — a wrong address costs a real email to a real person."])
    for r in range(ws.max_row - 2, ws.max_row + 1):
        ws.cell(row=r, column=1).font = Font(italic=True)
    return ws


# Series that get a Coverage column of their own beyond the original five, as
# (CONFERENCE_META series name, column heading, filename code for
# Conferences/<year>/<year>_<code>_*.pdf or None).
#
# The count lookup goes through each row's CONFERENCE_META lead_key, NOT through
# the name written here: typing the series name twice silently mismatched four
# of them (ECC, SOMEPEC, W Africa) and left their columns empty.
_EXTRA = [
    ("Encuentro Colombiano sobre Condrictios (ECC)", "ECC", "ECC"),
    ("Sociedade Brasileira para o Estudo de Elasmobranquios (SBEEL)", "SBEEL", "SBEEL"),
    ("Simposio Nacional de Tiburones y Rayas (SOMEPEC, Mexico)", "SOMEPEC", "SOMEPEC"),
    ("Colloque international requins en Afrique de l'Ouest", "W Africa", None),
    ("Gulf and Caribbean Fisheries Institute (GCFI)", "GCFI", None),
    ("Pacific Shark Workshop", "Pac Shark Wksp", None),
    ("ISC Shark Working Group", "ISC Shark WG", None),
    ("World Congress of Herpetology", "WCH", None),
    ("Indo-Pacific Fish Conference (IPFC)", "IPFC", None),
    ("International Coral Reef Symposium (ICRS)", "ICRS", None),
    ("World Fisheries Congress", "WFC", None),
    ("American Fisheries Society symposia", "AFS", None),
    ("International Congress on the Biology of Fish", "ICBF", None),
    ("International Meeting on Mesozoic Fishes", "Mesozoic Fishes", None),
    ("International Congress of Vertebrate Morphology (ICVM)", "ICVM", None),
    ("CIESM Congress (Mediterranean Science Commission)", "CIESM", None),
    ("Albert L. Tester Memorial Symposium", "Tester Symp", None),
    ("Workshop on Age Determination of Oceanic Pelagic Fishes", "Age Det Wksp", None),
    ("Palaeontology / geology meetings (assorted)", "Palaeo/geol", None),
]
_META_BY_NAME = {m["series"]: m for m in CONFERENCE_META}
# (meta name, heading, file code, lead_key) — lead_key resolved once, here, and
# an unknown series name is a hard error rather than a quietly empty column.
EXTRA_COLUMNS = []
for _name, _short, _code in _EXTRA:
    if _name not in _META_BY_NAME:
        raise KeyError(f"Coverage column {_short!r}: {_name!r} is not in CONFERENCE_META")
    EXTRA_COLUMNS.append((_name, _short, _code, _META_BY_NAME[_name]["lead_key"]))


# Ordinal -> meeting year, deduced across a whole series.
#
# Many series cite an ORDINAL and no year ("Proceedings of the Fifty Fifth
# Annual ..."), so `venue_year` stays empty and the coverage cell falls back to
# the PUBLICATION year. For GCFI that is 1-11 years out. But a series has a
# first year and a frequency on the Conferences tab, so the Nth meeting is
# deducible: year = year_from + (N - 1) * frequency.
#
# A formula is only trusted where it can be CHECKED. Rows that carry BOTH an
# ordinal and an explicit year are anchors; the formula is tested against them
# first and only used for that series if every anchor agrees. Irregular series
# fail that test and keep their citation year — WCH, for instance, met in 1989,
# 1993, 1997, 2001, 2005, 2008, 2012, so no fixed frequency reproduces it.
_ORD_WORDS = {
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6,
    "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10, "eleventh": 11,
    "twelfth": 12, "thirteenth": 13, "fourteenth": 14, "fifteenth": 15,
    "sixteenth": 16, "seventeenth": 17, "eighteenth": 18, "nineteenth": 19,
    "twentieth": 20, "thirtieth": 30, "fortieth": 40, "fiftieth": 50,
    "sixtieth": 60, "seventieth": 70, "eightieth": 80, "ninetieth": 90,
}
_TENS_WORDS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
               "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}
_UNIT_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
               "six": 6, "seven": 7, "eight": 8, "nine": 9}


def _ordinal_of(venue):
    """The meeting ordinal a citation names, as an int, or None."""
    # A bare "12th" is not necessarily the meeting number: "August 8th-14th,
    # 2005" reads as the 8th meeting unless the ordinal is required to sit in
    # front of a meeting noun. That misparse is what the anchor check caught.
    _NOUN = (r"(?:Annual|International|Meeting|Congress|Symposium|Simposium|"
             r"Conference|Workshop|Reuni\w+|Jornadas|Congreso)")
    m = re.search(rf"\b(\d{{1,3}})\s*(?:st|nd|rd|th)[\s,\-–]+"
                  rf"(?:[\w\-–]+[\s,\-–]+){{0,3}}?{_NOUN}", venue, re.I)
    if m and not re.search(r"(?:January|February|March|April|May|June|July|August|"
                           r"September|October|November|December)\s*$",
                           venue[:m.start()], re.I):
        return int(m.group(1))
    # Ordinal WORDS. Two traps, both hit by real citations:
    #  - the noun list must include "Conference": IPFC's 37 rows read
    #    "Proceedings of the second Indo-Pacific Fish Conference".
    #  - the ordinal is NOT adjacent to that noun there, so capture the ordinal
    #    words right after "the" and merely REQUIRE a meeting noun to follow
    #    within a short window, rather than immediately.
    m = re.search(r"\b(?:of\s+)?(?:the\s+)?((?:" + "|".join(
        list(_ORD_WORDS) + list(_TENS_WORDS) + list(_UNIT_WORDS)) +
        r")(?:[\s–\-]+(?:" + "|".join(
        list(_ORD_WORDS) + list(_TENS_WORDS) + list(_UNIT_WORDS)) + r"))*)\b",
        venue, re.I)
    if not m:
        return None
    if not re.search(r"(?:Annual|Meeting|Congress|Symposium|Simposium|Conference|"
                     r"Workshop|Reuni\w+|Jornadas|Congreso|Institute)",
                     venue[m.end():m.end() + 60], re.I):
        return None
    total, seen = 0, False
    for w in [w for w in re.split(r"[\s–\-]+", m.group(1).lower()) if w]:
        if w in _TENS_WORDS:
            total += _TENS_WORDS[w]; seen = True
        elif w in _ORD_WORDS:
            total += _ORD_WORDS[w]; seen = True
        elif w in _UNIT_WORDS:
            total += _UNIT_WORDS[w]; seen = True
        elif w in ("and", "annual"):
            continue
        else:
            return None
    return total if seen and total else None


def _deducible_series(rows, meta_by_series):
    """{series: (year_from, frequency)} for series whose ordinal->year formula
    reproduces EVERY anchor the corpus provides. Anchors are rows citing both an
    ordinal and an explicit year."""
    anchors = defaultdict(list)
    for r in rows:
        if not r.get("series") or not r.get("venue_year"):
            continue
        n = _ordinal_of(r["venue"] or "")
        if n:
            anchors[r["series"]].append((n, int(r["venue_year"])))
    ok = {}
    for series, pairs in anchors.items():
        meta = meta_by_series.get(series) or {}
        y0, freq = meta.get("year_from"), meta.get("frequency")
        if not y0 or not freq:
            continue
        if all(y0 + (n - 1) * freq == y for n, y in pairs):
            ok[series] = (y0, freq)
        else:
            bad = [(n, y, y0 + (n - 1) * freq) for n, y in pairs
                   if y0 + (n - 1) * freq != y][:3]
            print(f"  ordinal->year NOT used for {series}: formula disagrees with "
                  f"the corpus's own anchors {bad} (irregular schedule)")
    return ok


def _meeting_key(venue):
    """A venue string reduced to the MEETING it names.

    Counting distinct raw strings counts page numbers: ECC 2014 has 79 records
    that are one meeting cited 79 times, and reporting "79 distinct meetings"
    both reads as nonsense and suppresses the column's location, because a
    multi-meeting cell is not given one. So trailing page and volume references
    are stripped before the set is built.
    """
    # An ORDINAL identifies the meeting outright, so prefer it: the same
    # conference cited as "(Eds) Proceedings of the second ..." and
    # "(Eds.). Proceedings of the second ..." is ONE meeting, and string
    # normalisation alone reported IPFC 1985 and 1997 as two — which then
    # suppressed their host cities, because a multi-meeting cell is given none.
    n = _ordinal_of(venue or "")
    if n:
        return f"#{n}"
    v = re.sub(r"[\s,:;]+\d{1,4}\s*(?:[–-]\s*\d{1,4})?\s*(?:pp?\.?)?\s*$", "", venue or "")
    v = re.sub(r"[\s,:;]+(?:pp?\.|page[s]?)\s*\d.*$", "", v, flags=re.I)
    v = re.sub(r"\s+", " ", v).strip(" ,.:;–-").lower()
    return v[:90]


def _lead_year_counts():
    """{series: {year: records wanted}} from the corpus citations. A cell is
    only written where there is EVIDENCE — a citation, or a book on disk — so
    the sheet never invents a meeting year the series may not have held."""
    try:
        import sys as _s
        from pathlib import Path as _P
        _s.path.insert(0, str(_P(__file__).resolve().parents[1]))
        from conf_abstracts import conference_lead_candidates as L
        rows = [r for r in L.collect() if r["series"] and r["outstanding"]]
        # Key the metadata by BOTH the series NAME and its lead_key. The rows
        # coming back from collect() carry the LEAD KEY, which is often not the
        # meta name — "Indo-Pacific Fish Conference" vs "Indo-Pacific Fish
        # Conference (IPFC)". Keying on the name alone silently found no anchors
        # for IPFC and left its rows on the publication year, and GCFI only
        # worked because its two strings happen to be identical. This is the
        # same mismatch the EXTRA_COLUMNS comment above already warns about.
        meta_by_series = {}
        for m in CONFERENCE_META:
            meta_by_series[m["series"]] = m
            if m.get("lead_key"):
                meta_by_series[m["lead_key"]] = m
        deducible = _deducible_series(rows, meta_by_series)
        out = defaultdict(lambda: defaultdict(int))
        pub = defaultdict(lambda: defaultdict(set))   # published-year(s) per cell
        venues = defaultdict(lambda: defaultdict(set))
        for row in rows:
            y = row["venue_year"]
            if not y and row["series"] in deducible:
                n = _ordinal_of(row["venue"] or "")
                if n:
                    y0, freq = deducible[row["series"]]
                    y = y0 + (n - 1) * freq
            y = y or row["year"]
            if not y:
                continue
            y = int(y)
            out[row["series"]][y] += 1
            if row["year"] and int(row["year"]) != y:
                pub[row["series"]][y].add(int(row["year"]))
            venues[row["series"]][y].add(_meeting_key(row["venue"] or ""))
        return out, pub, venues
    except Exception as e:                                    # noqa: BLE001
        print(f"  extra-series year counts unavailable ({type(e).__name__}: {e})")
        return None, None, None


# Host city per (column code, year) for the series in columns G:X, which had no
# locations at all while B:F did. Keyed by MEETING year, matching those columns.
#
# Provenance matters more than coverage here, so each entry says where it came
# from and an unverified year stays "?" rather than being guessed:
#   [cite]  the corpus's own findspot string names the venue — the strongest
#           source available, since it is what the record itself asserts
#   [book]  read off the title/front matter of an abstract book we hold
#   [web]   an external source, named in the comment
#   "?"     looked for and not established (the same convention column B uses)
_EXTRA_LOCATIONS = {
    # [cite] "Proceedings of the First Pacific Shark Workshop, December 13-15,
    # 2011 Vancouver, Canada"
    ("Pac Shark Wksp", 2011): "Vancouver, Canada",
    # [cite] "World Congress of Herpetology, Vancouver, Canada, August 8-14, 2012"
    ("WCH", 2012): "Vancouver, Canada",
    # [web] worldcongressofherpetology.org past congresses: WCH3, Prague,
    # 2-10 August 1997. Our own citation ("Third World Congress of
    # Herpetology: 1-6") names no venue.
    ("WCH", 1997): "Prague, Czech Republic",
    # [cite] "12th International Coral Reef Symposium, 9-13 July 2012, Cairns,
    # Queensland, Australia"
    ("ICRS", 2012): "Cairns, Queensland, Australia",
    # [cite] "6th World Fisheries Congress ... 7th-11th May 2012, Edinburgh,
    # Scotland"
    ("WFC", 2012): "Edinburgh, Scotland",
    # [cite] "American Fisheries Society, 141st Meeting, 4-9 September 2011,
    # Seattle, WA."
    ("AFS", 2011): "Seattle, WA",
    # [cite] "International Congress on the Biology of Fish, Manaus, Brazil"
    ("ICBF", 2004): "Manaus, Brazil",
    # [cite] "Fourth International Meeting On Mesozoic Fishes ... Miraflores De
    # La Sierra, Madrid, Spain August 8th-14th, 2005"
    ("Mesozoic Fishes", 2005): "Miraflores de la Sierra, Madrid, Spain",
    # [cite] "6th International Meeting on Mesozoic Fishes ... Vienna, Austria
    # August 4th-10th, 2013"
    ("Mesozoic Fishes", 2013): "Vienna, Austria",
    # [cite] "8. Meeting on Mesozoic Fishes and Aquatic Tetrapods 10.-14. July
    # 2023, Stuttgart"
    ("Mesozoic Fishes", 2023): "Stuttgart, Germany",
    # [cite] "37th Annual Albert L. Tester Memorial Symposium, March 14-16,
    # 2012, University of Hawaii at Manoa"
    ("Tester Symp", 2012): "Honolulu, HI (U. Hawai'i at Manoa)",
    # [book] title page: "23 al 27 de agosto de 2004, Ciudad Universitaria,
    # Mexico" (2004_SOMEPEC_AbstractBook.pdf)
    ("SOMEPEC", 2004): "Ciudad Universitaria, Mexico City",
    # [book] front matter names Facultad de Ciencias, UNAM
    ("SOMEPEC", 2008): "Ciudad Universitaria, Mexico City",
    # [book] front matter names Ciudad Universitaria
    ("SOMEPEC", 2010): "Ciudad Universitaria, Mexico City",
    # [book] "18 al 22 de abril de 2016, Puerto Vallarta, Jal." — host
    # institution Centro Universitario de la Costa, U. de Guadalajara
    ("SOMEPEC", 2016): "Puerto Vallarta, Jalisco, Mexico",
    # [book] "06 al 10 de septiembre de 2021 ... Acuario Michin Puebla, BUAP"
    ("SOMEPEC", 2021): "Puebla, Mexico",
    # [book] running footer "Ensenada, Baja California, Mexico, Octubre 2025"
    ("SOMEPEC", 2025): "Ensenada, Baja California, Mexico",
    # [web] CONAPESCA: VI Simposium, Mazatlan, Sinaloa, 7-12 April 2014,
    # alongside the AFS international meeting. We hold no 2014 book.
    ("SOMEPEC", 2014): "Mazatlan, Sinaloa, Mexico",
    # [web] the 2011 Dakar colloquium, per the series notes already held on the
    # Conferences tab (CSRP, Dakar).
    ("W Africa", 2011): "Dakar, Senegal",
    # [web] GCFI 55, 11-15 November 2002, Xel Ha, Mexico.
    ("GCFI", 2002): "Xel Ha, Mexico",
    # [cite] the running footer of the volume's own papers: "Proceedings of the
    # 60th Gulf and Caribbean Fisheries Institute November 5 - 9, 2007 Punta
    # Cana, Dominican Republic"
    ("GCFI", 2007): "Punta Cana, Dominican Republic",
    # [cite] running footer, 78 occurrences: "November 2 - 6, 2009 Cumana,
    # Venezuela"
    ("GCFI", 2009): "Cumana, Venezuela",
    # v55/v57/v59 print a footer WITHOUT the city, and the external pages that
    # would have it (NOAA repository, IISD) return 403 to an automated fetch.
    ("GCFI", 1951): "?",
    ("GCFI", 2004): "?",
    ("GCFI", 2006): "?",
    # --- looked for, NOT established. Left explicit so the gap is visible. ---
    # Our citation says "Abstracts. University of Milan, Italy", which is the
    # publisher; secondary sources place the meeting at Serpiano, Switzerland.
    # Two sources disagree, so neither is asserted.
    ("Mesozoic Fishes", 2001): "?",
    # Citation names Universidad Autonoma del Estado de Hidalgo (Pachuca);
    # secondary sources say Saltillo, Coahuila. Unresolved.
    ("Mesozoic Fishes", 2010): "?",
    # "American Fisheries Society Symposium, 50" / "76" are BOOK volumes in a
    # series, not meetings, so a host city may not exist for these rows.
    ("AFS", 2007): "?",
    ("AFS", 2012): "?",
    ("AFS", 2014): "?",
    ("SBEEL", 2002): "?",
    ("ISC Shark WG", 2013): "?",
    ("Age Det Wksp", 1983): "?",
    ("ECC", 2014): "?",
    # [web] IPFC2, Tokyo 1985 — our 37 rows cite "the second Indo-Pacific Fish
    # Conference" and carry its 1986 proceedings year, not the meeting year.
    ("IPFC", 1985): "Tokyo, Japan",
    # [cite] "Proceedings of the 4th Indo-Pacific Fish Conference, Bankok"
    ("IPFC", 1993): "Bangkok, Thailand",
    # [cite] "Proceedings of the 5th Indo-Pacific Fish conference, Noumea -
    # New Caledonia, 3-8 November 1997"
    ("IPFC", 1997): "Noumea, New Caledonia",
    # [cite] the 2009 book's own running header: "8th Indo Pacific Fish
    # Conference & 2009 ASFB Workshop, 31 May - 5 June 2009, Fremantle,
    # Western Australia" — which also anchors the ordinal formula (1981+7*4).
    ("IPFC", 2009): "Fremantle, WA, Australia",
    ("IPFC", 2023): "Auckland, New Zealand",
    ("ICVM", 2019): "?",
    ("CIESM", 2010): "?",
}


def _extra_cell(lead_key, code, year, counts, db_years, short=None,
                pub=None, venues=None):
    """(text, status) for one extra-series cell, or (None, None) to leave blank.

    The text is prefixed with the host city, in the same "City; Status" shape
    columns B:F use, so the whole tab reads one way.
    """
    # Default to "?" rather than "": an empty prefix reads as "no location
    # applies", when what it means is "nobody has established one".
    multi = len(((venues or {}).get(lead_key, {}).get(year)) or ()) > 1
    loc = "" if multi else _EXTRA_LOCATIONS.get((short, year), "?")
    pre = f"{loc}; " if loc else ""
    held = db_years.get(code or "", {}).get(year) if code else None
    if held:
        return f"{pre}Ingested — {held} abstracts", "Ingested"
    book = sorted((CONFERENCES / str(year)).glob(f"{year}_{code}_*.pdf")) \
        if code and (CONFERENCES / str(year)).is_dir() else []
    if book:
        return (f"{pre}Digital — {len(book)} PDF held — extraction pending", "Digital")
    n = (counts or {}).get(lead_key, {}).get(year)
    if n:
        return (f"{pre}Missing — {n} abstract{'s' if n != 1 else ''} cited by the corpus"
                + _year_note(lead_key, year, pub, venues), "Missing")
    return None, None


def _year_note(lead_key, year, pub, venues):
    """' [Published YYYY]' where the proceedings appeared in a different year,
    and a meeting count where the column is an assorted bucket.

    The row is keyed on the MEETING, because the meeting is the thing being
    chased; the publication year is the detail hung off it. Columns that lump
    unrelated meetings together (Palaeo/geol) get a count instead of a place,
    since one location cannot describe seven different conferences.
    """
    bits = []
    vs = (venues or {}).get(lead_key, {}).get(year) or set()
    if len(vs) > 1:
        bits.append(f"{len(vs)} distinct meetings")
    ys = sorted((pub or {}).get(lead_key, {}).get(year) or set())
    if ys:
        bits.append("Published " + ", ".join(str(y) for y in ys))
    return f" [{'; '.join(bits)}]" if bits else ""


def db_meeting_status():
    con = sqlite3.connect(str(DB))
    out = {}
    # LEFT JOIN so a held-but-unparsed book (e.g. a degraded scan that yielded
    # 0 records) still surfaces; body count makes the status content-aware
    # (a 520-page "programme" whose records carry bodies IS an abstract book).
    for yr, meeting, doc, isocr, src, n, el, bodies in con.execute(
        """select m.year,m.meeting,m.doc_type,m.is_ocr,m.source_pdf,
                  count(a.abstract_id) n, sum(a.is_elasmo) el,
                  sum(case when length(a.abstract_text) > 50 then 1 else 0 end) bodies
           from meetings m left join abstracts a on a.meeting_id=m.meeting_id
           where m.meeting in ('JMIH','ASIH') group by m.meeting_id"""):
        d = out.setdefault(yr, dict(abstract=False, schedule=False, ocr=False,
                                    ocr_failed=False, structured=False, elasmo=0))
        has_bodies = (bodies or 0) >= max(2, 0.5 * n)
        if n > 1 and (doc == "abstract_book" or has_bodies):
            d.update(abstract=True, ocr=bool(isocr))
            # An Oxford Abstracts export is born-digital and already structured:
            # there is nothing for Fable to extract, so it is done on arrival.
            if str(src or "").lower().endswith(".xlsx"):
                d["structured"] = True
            d["elasmo"] += el or 0
        elif doc == "abstract_book" and isocr:
            d["ocr_failed"] = True  # scan held; OCR recovered nothing usable
        elif doc == "program_book" and n > 20:
            d["schedule"] = True
            d["elasmo"] += el or 0
    con.close()
    return out


def db_aes_web():
    """AES abstracts harvested from elasmo.org (meeting='AES'): year -> count."""
    con = sqlite3.connect(str(DB))
    out = {yr: n for yr, n in con.execute(
        "select m.year, count(*) from meetings m join abstracts a using(meeting_id) "
        "where m.meeting='AES' group by m.year")}
    con.close()
    return out


def db_year_society():
    con = sqlite3.connect(str(DB))
    cnt = defaultdict(int)
    for yr, soc, meeting, n in con.execute(
        """select m.year,a.society,m.meeting,count(*) from abstracts a
           join meetings m on a.meeting_id=m.meeting_id
           where m.meeting in ('JMIH','ASIH','SI','EEA','AES') group by m.year,a.society,m.meeting"""):
        if meeting in ("SI", "EEA", "AES"):
            cnt[(yr, meeting)] += n
        else:
            for s in (soc or "").split("|"):
                if s in SERIES:
                    cnt[(yr, s)] += n
    con.close()
    return cnt


_FABLE_WL = REPO / "outputs" / "conf_abstracts" / "fable_worklist.json"


@lru_cache(maxsize=None)
def _fable_books():
    """{(meeting, year): (chunks_done, chunks_total, abstracts_cached)} from the
    Fable worklist and the cache files it treats as resume truth."""
    out = {}
    if not _FABLE_WL.exists():
        return out
    try:
        wl = json.loads(_FABLE_WL.read_text(encoding="utf-8"))
    except Exception:
        return out
    # Count DISTINCT titles across a book's chunks, not the raw sum. Chunks
    # overlap by 15k chars by design and conf_fable_merge dedups by title, so a
    # raw sum overstates the extraction and made merged books (JMIH 2015/2016)
    # look unmerged against their own DB row counts.
    seen = defaultdict(set)
    tally = defaultdict(lambda: [0, 0])
    for w in wl:
        key = (w.get("meeting"), w.get("year"))
        tally[key][1] += 1
        cp = Path(w["cache_path"])
        if cp.exists() and cp.stat().st_size >= 2:
            tally[key][0] += 1
            try:
                d = json.loads(cp.read_text(encoding="utf-8"))
                for a in (d if isinstance(d, list) else d.get("abstracts", [])):
                    t = re.sub(r"[^a-z0-9]", "", str(a.get("title") or "").lower())
                    if t:
                        seen[key].add(t)
            except Exception:
                pass
    for key, (done, total) in tally.items():
        out[key] = (done, total, len(seen.get(key, ())))
    _fable_titles.cache_clear()
    _FABLE_TITLE_CACHE.update(seen)
    return out


_FABLE_TITLE_CACHE = {}


@lru_cache(maxsize=None)
def _fable_titles():
    _fable_books()
    return _FABLE_TITLE_CACHE


def fable_state(meeting, year):
    """'none' | 'partial' | 'complete' | 'merged' for this book, plus the number
    of distinct abstracts sitting in its Fable caches.

    'merged' is decided by CONTENT, not by counts: what fraction of the DB's
    titles for this meeting-year appear in the Fable cache. Two count-based
    heuristics were tried first and both misread the data — a raw cache sum
    double-counts the 15k-char chunk overlap, and a DB-vs-cache ratio breaks on
    the elasmo.org --supersede step, which legitimately DELETES merged records
    (JMIH 2005 keeps 877 of 1,033). Title overlap separates cleanly: merged
    books score 100%, unmerged ones 0-1.5%."""
    done, total, n = _fable_books().get((meeting, year), (0, 0, 0))
    if total == 0 or done == 0:
        return "none", 0
    if done < total:
        return "partial", n
    titles = _fable_titles().get((meeting, year), set())
    try:
        con = sqlite3.connect(str(DB))
        rows = [r[0] for r in con.execute(
            """select a.title from abstracts a join meetings m using(meeting_id)
               where m.year=? and m.meeting=?""", (year, meeting))]
        con.close()
    except Exception:
        return "complete", n
    if not rows or not titles:
        return "complete", n
    hit = sum(1 for t in rows if re.sub(r"[^a-z0-9]", "", str(t or "").lower()) in titles)
    return ("merged" if hit / len(rows) >= 0.80 else "complete"), n


# Years where AES did not meet with ASIH/JMIH, so the AES column must not
# inherit the JMIH column's status and there is no gap to chase.
#
# 2018: AES skipped JMIH and met at Sharks International (Joao Pessoa) instead
# (Simon, 2026-09-04). The evidence on disk agrees: the Rochester 2018 book's
# title page reads "THE JOINT MEETING OF ASIH SSAR HL" with no AES, and its
# text carries 35 shark/skate/ray tokens over 370 pages against 462-786 in
# 2019/2023/2024 — an elasmo share of 1.7% where every comparable year runs
# 18-34%. The 10 elasmo records we hold are talks given in ASIH sessions. The
# AES abstracts for that year are in the SI 2018 book, which is ingested.
# (location, note). The location is where AES actually met, and the cell schema
# is "Location; Status — note", so a note must contain no semicolon of its own:
# check_coverage_matrix.py reads whatever follows one as a status.
AES_NOT_AT_JMIH = {
    2018: ("Joao Pessoa (at SI)",
           "no AES meeting at JMIH — AES met at Sharks International instead, "
           "so those abstracts are under SI 2018"),
}


def meeting_cell(year, db):
    """Return (location, status, note, elasmo_count)."""
    loc = JMIH_LOC.get(year, "?")
    d = db.get(year)
    if d and d["abstract"]:
        if d["ocr"]:
            return loc, "OCR", "degraded scan (needs_review) — flatbed re-scan planned", d["elasmo"]
        if d.get("structured"):
            return loc, "Ingested", "Oxford Abstracts export (born-digital)", d["elasmo"]
        state, n_fable = fable_state("JMIH", year)
        if state == "merged":
            return loc, "Ingested", "", d["elasmo"]
        if state == "complete":
            return loc, "Extracted", f"Fable extraction complete ({n_fable}) — merge pending", d["elasmo"]
        note = ("regex-parsed; Fable re-extraction queued" if state == "none"
                else f"regex-parsed; Fable re-extraction part-done ({n_fable} so far)")
        return loc, "Extracted", note, d["elasmo"]
    # An abstract book sitting in Conferences/<year>/ that has produced no
    # abstracts yet outranks 'Schedule'/'Programme'/'Hardcopy': the sourcing job
    # is done and only extraction remains. Checked on disk so the sheet updates
    # itself the moment a book is filed. (JMIH 2006/2010/2014/2017/2018/2019 and
    # 2023/2024/2026 came from asih.org/meetings/recent-meetings, 2026-09-01.)
    # SKIP_NAME_FRAGMENTS matters: the 1997-2004 phone scans are named
    # <year>_JMIH_AbstractBook_phonescan.pdf, so a bare glob counted them as a
    # held, ingestable book and reported 2003/2004 as 'Digital' when they are in
    # fact the degraded scans that recovered 0-1 abstracts.
    book = [b for b in sorted((CONFERENCES / str(year)).glob(f"{year}_JMIH_AbstractBook*.pdf"))
            if not any(frag in b.name for frag in SKIP_NAME_FRAGMENTS)] \
        if (CONFERENCES / str(year)).is_dir() else []
    if book:
        state, n_fable = fable_state("JMIH", year)
        if state == "merged":
            return loc, "Ingested", "", (d or {}).get("elasmo", 0)
        if state == "complete":
            # Extracted but the merge has not run yet. Falling through here sent
            # JMIH 2010 — downloaded AND fully extracted — all the way down to
            # 'Hardcopy', the worst label on the ramp.
            return loc, "Extracted", f"Fable extraction complete ({n_fable}) — merge pending", 0
        if state == "partial":
            return loc, "Digital", (f"abstract book held — Fable extraction "
                                    f"part-done ({n_fable} so far)"), 0
        return loc, "Digital", (f"abstract book held ({len(book)} PDF"
                                f"{'s' if len(book) > 1 else ''}) — extraction pending"), 0
    if d and d["ocr_failed"]:
        return loc, "OCR", "degraded phone scan — 0 abstracts recovered — flatbed re-scan needed (Carylanne)", 0
    if d and d["schedule"]:
        return loc, "Schedule", "programme ingested (no abstract bodies) — abstract book needed", d["elasmo"]
    if year in JMIH_PROGRAMME:
        return loc, "Programme", JMIH_PROGRAMME[year], 0
    # 2020: no meeting. JMIH was replaced by the virtual BAAM-ZOOM sessions and no
    # abstract book exists (asih.org lists only a summary; Carol Spencer, ASIH
    # secretary, 2026-09-01: "no meeting in 2020"). Not a gap to chase.
    if year == 2020:
        return loc, "NA", "no meeting — virtual BAAM-ZOOM sessions only, no abstract book", 0
    if 1992 <= year <= 2024:
        return loc, "Hardcopy", "Carylanne has hardcopy (1992-2024) — get abstract book", 0
    return loc, "Missing", "", 0


def build():
    db = db_meeting_status()
    yr_soc = db_year_society()
    aes_web = db_aes_web()
    wb = Workbook()
    wb.remove(wb.active)
    thin = Side(style="thin", color="CCCCCC")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    # ---- Legend & Notes (first, per Simon's tab swap) ----
    leg = wb.create_sheet("Legend & Notes")
    leg.append(["Status", "Meaning", "Colour"])
    for c in leg[1]:
        c.font = Font(bold=True)
    # listed worst-to-best so the colour ramp reads top to bottom
    MEANING = {
        "Missing": "No known source anywhere.",
        "Schedule": "Programme ingested: titles, authors, presentation type. NO abstract text. Useful, but it isn't abstracts.",
        "Hardcopy": "A physical book is known to exist (Carylanne, Cat, Ali) but nothing digital. Needs scanning, or a digital copy from the host.",
        "Programme": "A digital programme is held, but not the abstract book. Same practical need as Hardcopy: get the book.",
        "Pending": "A named contact has it or is looking for it, not yet received (EEA: Cat and Ali; OCS: Brit).",
        "OCR": "Abstracts ingested, but from a degraded scan and flagged needs_review. Still worth re-sourcing a clean copy.",
        "Digital": "Abstract book in hand, nothing extracted into the database yet.",
        "Extracted": ("Abstracts are in the database, but from the regex parsers "
                      "(or extracted and not yet merged). Titles and author lists "
                      "are weak; full re-extraction is queued."),
        "Ingested": "Fully extracted and merged into the database. Done.",
    }
    NOTE_DEFAULTS = [
        "- 'ASIH/JMIH' = the American joint meeting (ASIH pre-1997, JMIH from 1997). ASIH/JMIH/HL/SSAR/NIA share one source book, collapsed to this column to remove duplicates.",
        "- 'AES' (American Elasmobranch Society, founded 1983) kept separate — cell shows elasmo-abstract count where ingested. Pre-1983 = no conference (blank).",
        "- Host cities 1916-2025 from github.com/SimonDedman/AESconfLocations; 2026 = New Orleans.",
        "- 'OCR' = degraded 1997-2004 JMIH phone-photo scans (all needs_review); Carylanne's flatbed re-scans would upgrade the non-AES content.",
        "- AES 1985-2005: full abstracts harvested from elasmo.org/meetings/abstracts/abst<YYYY>/ (1,305 abstracts, 2026-08-25); JMIH-book copies of the same AES talks were removed. No AES source found for 1983-84 or 2006+ online.",
        "- ASIH/JMIH pre-1992: Carylanne's archive starts 1992 → host city shown but 'Missing'.",
        "- EEA from Cat Gordon (Shark Trust). 2004-2019 + 2023 ingested via Fable and merged 2026-08-25. Received 2026-08-27: 2002 Cardiff booklet, a clean 2024 Thessaloniki book, and the full SI2022 Valencia abstract book (all queued for extraction). 2025 Rotterdam abstract book is still a corrupt file. Cat holds hardcopies of 2010/2012/2015/2017 but has no scanning capacity, so those are being sought digitally from the host groups; Ali Hood is searching her paperwork for 2003-2009. EEA began in 1997 (2002 Cardiff was the 6th).",
        "- OCS (Oceania Chondrichthyan Soc, ~2011+, biennial): Brit Finucci collating, pending council — years/locations TBC.",
        "- Blank/unshaded cell = no conference that year for that series.",
        "- Per-society counts & trends: see the Dashboard tab.",
    ]
    MEANING, NOTE_LINES = harvest_legend_edits(MEANING, NOTE_DEFAULTS)
    order = [(st, MEANING[st]) for st in STATUS_ORDER]
    for i, (st, mean) in enumerate(order, 2):
        leg.cell(row=i, column=1, value=st)
        leg.cell(row=i, column=2, value=mean)
        leg.cell(row=i, column=3).fill = PatternFill("solid", fgColor=FILL[st])
    for note in NOTE_LINES:
        leg.append([note])
    leg.column_dimensions["A"].width = 12
    leg.column_dimensions["B"].width = 95

    # ---- Coverage ----
    ws = wb.create_sheet("Coverage")
    cols = (["Year", "ASIH/JMIH", "AES", "EEA", "OCS", "SI"]
            + [short for _, short, _, _ in EXTRA_COLUMNS])
    ws.append(cols)
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="434343")
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = border

    def put(r, col, text, status):
        cell = ws.cell(row=r, column=col, value=text)
        if FILL.get(status):
            cell.fill = PatternFill("solid", fgColor=FILL[status])
        cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        cell.border = border
        cell.font = Font(size=9)

    def txt(loc, st, note):
        head = f"{loc}; {st}" if loc else st
        return head + (f" — {note}" if note else "")

    extra_counts, extra_pub, extra_venues = _lead_year_counts()
    extra_db = defaultdict(dict)
    _con = sqlite3.connect(str(DB))
    for _m, _y, _n in _con.execute(
            "SELECT m.meeting, m.year, COUNT(a.abstract_id) FROM meetings m "
            "LEFT JOIN abstracts a ON a.meeting_id=m.meeting_id GROUP BY m.meeting_id"):
        if _n:
            extra_db[_m][_y] = extra_db[_m].get(_y, 0) + _n
    _con.close()

    cover = defaultdict(lambda: {"ingested": 0, "known": 0})

    def track(series, status):
        if status in ("NA", None) or not status:
            return
        cover[series]["known"] += 1
        if status == "Ingested":
            cover[series]["ingested"] += 1

    r = 2
    for year in range(1916, 2027):
        ws.cell(row=r, column=1, value=year).font = Font(bold=True)
        ws.cell(row=r, column=1).border = border
        loc, st, note, el = meeting_cell(year, db)
        put(r, 2, txt(loc, st, note), st)
        # AES (founded 1983)
        if year in aes_web:
            # AES abstracts harvested from elasmo.org supersede the JMIH-book status
            put(r, 3, txt(f"{loc} ({aes_web[year]})", "Ingested",
                          "AES abstracts from elasmo.org (full bodies)"), "Ingested")
            track("AES", "Ingested")
        elif year in AES_NOT_AT_JMIH:
            where, note = AES_NOT_AT_JMIH[year]
            put(r, 3, txt(where, "NA", note), "NA")
            track("AES", "NA")
        elif year >= 1983:
            aloc = f"{loc}" + (f" ({el})" if el else "")
            put(r, 3, txt(aloc, st, note), st)
            track("AES", st)
        else:
            put(r, 3, "", "NA")
        # EEA
        if year in EEA:
            l, s_, n = EEA[year]; put(r, 4, txt(l, s_, n), s_); track("EEA", s_)
        elif year in EEA_EARLY:
            loc_e, note_e = EEA_EARLY[year]
            put(r, 4, txt(loc_e, "Pending", note_e), "Pending"); track("EEA", "Pending")
        elif 1997 <= year <= 2001:
            loc_e = EEA_EARLY_LOC.get(year, "?")
            nth = {1997: "1st", 1998: "2nd", 1999: "3rd", 2000: "4th", 2001: "5th"}[year]
            put(r, 4, txt(loc_e, "Missing",
                          f"{nth} EEA; no known abstract source"
                          + ("" if year in EEA_EARLY_LOC else "; host city also unknown")), "Missing")
            track("EEA", "Missing")
        else:
            put(r, 4, "", "NA")
        # OCS (biennial ~2012+)
        if year in OCS:
            oloc, onote = OCS[year]
            put(r, 5, txt(oloc, "Pending", onote), "Pending"); track("OCS", "Pending")
        elif year >= 2012 and year % 2 == 0:
            put(r, 5, "?; Pending — Brit Finucci collating; year/location to confirm", "Pending")
            track("OCS", "Pending")
        else:
            put(r, 5, "", "NA")
        # SI (quadrennial)
        if year in SI:
            l, s_, n = SI[year]; put(r, 6, txt(l, s_, n), s_); track("SI", s_)
        else:
            put(r, 6, "", "NA")
        # ---- the other series, one column each ----
        for i, (series, _short, code, lead_key) in enumerate(EXTRA_COLUMNS):
            text, status = _extra_cell(lead_key, code, year, extra_counts,
                                       extra_db, short=_short,
                                       pub=extra_pub, venues=extra_venues)
            if text:
                put(r, 7 + i, text, status)
                track(series, status)
            else:
                put(r, 7 + i, "", "NA")
        r += 1
    ws.column_dimensions["A"].width = 6
    for col in "BCDEF":
        ws.column_dimensions[col].width = 44
    for i in range(len(EXTRA_COLUMNS)):
        ws.column_dimensions[get_column_letter(7 + i)].width = 30
    ws.freeze_panes = "B2"

    # ---- Dashboard ----
    dash = wb.create_sheet("Dashboard")
    dash["A1"] = "Conference abstract coverage — dashboard"
    dash["A1"].font = Font(bold=True, size=13)
    # data table: year x series counts
    hdr_row = 3
    dash.cell(row=hdr_row, column=1, value="Year").font = Font(bold=True)
    for j, s in enumerate(SERIES, 2):
        dash.cell(row=hdr_row, column=j, value=s).font = Font(bold=True)
    years = list(range(1992, 2027))
    for i, y in enumerate(years, hdr_row + 1):
        dash.cell(row=i, column=1, value=y)
        for j, s in enumerate(SERIES, 2):
            dash.cell(row=i, column=j, value=yr_soc.get((y, s), 0))
    last = hdr_row + len(years)
    # totals row
    tot_row = last + 1
    dash.cell(row=tot_row, column=1, value="TOTAL").font = Font(bold=True)
    for j, s in enumerate(SERIES, 2):
        dash.cell(row=tot_row, column=j,
                  value=sum(yr_soc.get((y, s), 0) for y in years)).font = Font(bold=True)

    # Bar chart: totals per society
    bar = BarChart()
    bar.title = "Total abstracts ingested per society/series"
    bar.type = "col"
    bar.y_axis.title = "Abstracts"
    data = Reference(dash, min_col=2, max_col=len(SERIES) + 1, min_row=tot_row, max_row=tot_row)
    cats = Reference(dash, min_col=2, max_col=len(SERIES) + 1, min_row=hdr_row, max_row=hdr_row)
    bar.add_data(data, from_rows=True, titles_from_data=False)
    bar.set_categories(cats)
    bar.legend = None
    bar.height, bar.width = 8, 16
    dash.add_chart(bar, "I3")

    # Coverage table: share of each society's MEETINGS whose abstracts are in.
    # Denominator is meetings we know took place, not abstracts, so SI reads n/5.
    cov_hdr = tot_row + 3
    dash.cell(row=cov_hdr, column=1, value="Series").font = Font(bold=True)
    dash.cell(row=cov_hdr, column=2, value="Meetings ingested").font = Font(bold=True)
    dash.cell(row=cov_hdr, column=3, value="Meetings known").font = Font(bold=True)
    dash.cell(row=cov_hdr, column=4, value="% ingested").font = Font(bold=True)
    pct_series = ["AES", "EEA", "OCS", "SI"]
    for i, sname in enumerate(pct_series, cov_hdr + 1):
        c = cover.get(sname, {"ingested": 0, "known": 0})
        pct = round(100.0 * c["ingested"] / c["known"], 1) if c["known"] else 0.0
        dash.cell(row=i, column=1, value=sname)
        dash.cell(row=i, column=2, value=c["ingested"])
        dash.cell(row=i, column=3, value=c["known"])
        dash.cell(row=i, column=4, value=pct)
    cov_last = cov_hdr + len(pct_series)

    pbar = BarChart()
    pbar.title = "% of meetings with abstracts ingested, by society"
    pbar.type = "col"
    pbar.y_axis.title = "% of that society's meetings"
    pbar.y_axis.scaling.min = 0
    pbar.y_axis.scaling.max = 100
    pdata = Reference(dash, min_col=4, max_col=4, min_row=cov_hdr + 1, max_row=cov_last)
    pcats = Reference(dash, min_col=1, max_col=1, min_row=cov_hdr + 1, max_row=cov_last)
    pbar.add_data(pdata, titles_from_data=False)
    pbar.set_categories(pcats)
    pbar.legend = None
    pbar.height, pbar.width = 8, 16
    dash.add_chart(pbar, "S3")

    # Line chart: over time, one line per society
    line = LineChart()
    line.title = "Abstracts over time, by society/series"
    line.y_axis.title = "Abstracts"
    line.x_axis.title = "Year"
    ldata = Reference(dash, min_col=2, max_col=len(SERIES) + 1,
                      min_row=hdr_row, max_row=last)
    lcats = Reference(dash, min_col=1, min_row=hdr_row + 1, max_row=last)
    line.add_data(ldata, titles_from_data=True)
    line.set_categories(lcats)
    line.height, line.width = 10, 20
    dash.add_chart(line, "I20")
    dash.column_dimensions["A"].width = 7

    # Conferences metadata, second tab (after Legend & Notes)
    conf = _conferences_sheet(wb)
    wb._sheets.remove(conf)
    wb._sheets.insert(1, conf)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    wb.save(OUT)
    print(f"wrote {OUT}  (sheets: {wb.sheetnames})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset-legend", action="store_true",
                    help="discard preserved legend wording and re-emit the code defaults")
    a = ap.parse_args()
    if a.reset_legend and LEGEND_STORE.exists():
        LEGEND_STORE.unlink()
        print("legend store cleared; code wording will be used")
    build()
