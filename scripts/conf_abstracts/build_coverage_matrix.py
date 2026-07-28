"""Build the conference-abstract coverage matrix (xlsx), colour-coded red->green
by status: Missing -> Hardcopy -> OCR/Digital -> Ingested.

Rows: years 1983 (AES founding, start of elasmo abstracts) to 2026.
Columns: Year | ASIH | JMIH | AES | Other (HL/SSAR/NIA) | EEA | OCS | SI.
Each cell = "Location; Status".

Sources: the conference_abstracts DB (what we've ingested); Cat Gordon's email
(EEA locations + hardcopy/digital status, 2010-2026); Brit Finucci (OCS pending);
Carylanne Maier (has all ASIH/JMIH society abstracts 1992-2024, digitising gaps);
known SI years (quadrennial). Uncertain cells marked '?'.
"""
import sqlite3
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

REPO = Path(__file__).resolve().parents[2]
DB = REPO / "database" / "conference_abstracts.db"
OUT = REPO / "outputs" / "conference_coverage_matrix.xlsx"

# status -> fill colour (red -> green)
FILL = {
    "Missing":   "E06666",   # red
    "Hardcopy":  "F6B26B",   # orange
    "OCR":       "FFD966",   # yellow
    "Digital":   "FFE599",   # pale yellow (digital exists, not ingested)
    "Schedule":  "B6D7A8",   # light green (schedule-only ingested, no bodies)
    "Ingested":  "6AA84F",   # green
    "Pending":   "D9D2E9",   # lilac (awaiting external delivery)
    "NA":        "D9D9D9",   # grey (society/series didn't exist that year)
}

# ---- Known locations ----
EEA = {  # from Cat Gordon's email; status: hardcopy (2010-19), digital (2022+)
    2010: ("Galway", "Hardcopy"), 2011: ("Berlin", "Hardcopy"),
    2012: ("Milan", "Hardcopy"), 2013: ("Plymouth", "Hardcopy"),
    2014: ("Leeuwarden", "Hardcopy"), 2015: ("Peniche", "Hardcopy"),
    2016: ("Bristol", "Hardcopy"), 2017: ("Amsterdam", "Hardcopy"),
    2018: ("Peniche", "Digital"),  # Cat: no hardcopy, maybe online only
    2019: ("Rende", "Hardcopy"), 2020: ("online (covid)", "Digital"),
    2021: ("Leiden", "Digital"), 2022: ("Valencia (SI takeover)", "Digital"),
    2023: ("Brighton", "Digital"), 2024: ("Thessaloniki", "Digital"),
    2025: ("Rotterdam", "Digital"), 2026: ("online", "Digital"),
}
SI = {  # Sharks International, quadrennial; locations from project data + emails
    2010: ("Cairns", "Missing"), 2014: ("Durban", "Missing"),
    2018: ("Joao Pessoa", "Ingested"),      # SI2018 book ingested (427)
    2022: ("Valencia", "Digital"),          # Cat emailed the SI2022 PDF; not yet ingested
    2026: ("Colombo", "Ingested"),          # SI2026 ingested (1001)
}
# JMIH/ASIH host cities — only where known; else '?'
JMIH_LOC = {1997: "Seattle", 2026: "New Orleans"}
# JMIH/ASIH years where we hold the source file but haven't ingested abstracts
# (e.g. 2026 program is image-only, awaiting OCR).
JMIH_DIGITAL = {2026}


def db_status():
    """Return {year: dict(has_abstract_book, has_schedule, elasmo)} from the DB."""
    con = sqlite3.connect(str(DB))
    out = {}
    for yr, meeting, doc, isocr, n, el in con.execute(
        """select m.year,m.meeting,m.doc_type,m.is_ocr,count(*) n,sum(a.is_elasmo) el
           from meetings m join abstracts a on a.meeting_id=m.meeting_id
           where m.meeting in ('JMIH','ASIH') group by m.meeting_id"""):
        d = out.setdefault(yr, dict(abstract=False, schedule=False, ocr=False,
                                    elasmo=0, n=0))
        if doc == "abstract_book" and n > 1:
            d["abstract"] = True
            d["ocr"] = bool(isocr)
            d["elasmo"] += el or 0
            d["n"] += n
        elif doc == "program_book" and n > 20:   # schedule talks
            d["schedule"] = True
            d["elasmo"] += el or 0
            d["n"] += n
    con.close()
    return out


def jmih_cell(year, db, kind):
    """Cell for ASIH/JMIH/AES/Other columns (share the same source book)."""
    # series existence
    if kind == "JMIH" and year < 1997:
        return "—", "NA"                      # joint meeting started 1997
    if kind == "ASIH" and year >= 1997:
        # ASIH is a constituent of JMIH from 1997; still show status via the book
        pass
    if kind == "AES" and year < 1983:
        return "—", "NA"
    loc = JMIH_LOC.get(year, "?")
    d = db.get(year)
    if d and d["abstract"]:
        status = "Ingested" if not d["ocr"] else "OCR"  # OCR'd ones = needs-review
        if kind == "AES":
            loc = f"{loc} ({d['elasmo']} AES)" if d["elasmo"] else loc
        return loc, status
    if d and d["schedule"]:
        return loc, "Schedule"                # program book, titles/authors only
    if year in JMIH_DIGITAL:
        return loc, "Digital"                 # file held, not yet ingested
    if 1992 <= year <= 2024:
        return f"{loc}", "Hardcopy"           # Carylanne has 1992-2024
    return loc, "Missing"


def build():
    db = db_status()
    wb = Workbook()
    ws = wb.active
    ws.title = "Coverage"
    cols = ["Year", "ASIH", "JMIH", "AES", "Other (HL/SSAR/NIA)", "EEA", "OCS", "SI"]
    ws.append(cols)
    thin = Side(style="thin", color="999999")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="434343")
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = border

    def put(row, col, text, status):
        cell = ws.cell(row=row, column=col, value=text)
        cell.fill = PatternFill("solid", fgColor=FILL[status])
        cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        cell.border = border
        cell.font = Font(size=9)

    r = 2
    for year in range(1983, 2027):
        ws.cell(row=r, column=1, value=year).font = Font(bold=True)
        ws.cell(row=r, column=1).border = border
        for ci, kind in [(2, "ASIH"), (3, "JMIH"), (4, "AES"), (5, "Other")]:
            loc, st = jmih_cell(year, db, kind)
            put(r, ci, f"{loc}; {st}" if st != "NA" else "—", st)
        # EEA
        if year in EEA:
            loc, st = EEA[year]; put(r, 6, f"{loc}; {st}", st)
        elif 1997 <= year <= 2009:
            put(r, 6, "?; Hardcopy (Ali archive)", "Hardcopy")
        else:
            put(r, 6, "—", "NA")
        # OCS (Oceania Chondrichthyan Society, ~2011+, biennial) — pending Brit
        if year >= 2012 and year % 2 == 0:
            put(r, 7, "?; Pending (Brit collating)", "Pending")
        elif year >= 2012:
            put(r, 7, "", "NA")
        else:
            put(r, 7, "—", "NA")
        # SI (quadrennial)
        if year in SI:
            loc, st = SI[year]; put(r, 8, f"{loc}; {st}", st)
        else:
            put(r, 8, "", "NA")
        r += 1

    # widths + freeze + legend
    ws.column_dimensions["A"].width = 6
    for col in "BCDEFGH":
        ws.column_dimensions[col].width = 22
    ws.freeze_panes = "B2"

    leg = wb.create_sheet("Legend & Notes")
    leg.append(["Status", "Meaning", "Colour"])
    for c in leg[1]:
        c.font = Font(bold=True)
    order = [("Missing", "No known source"),
             ("Hardcopy", "Physical book exists (Carylanne / Cat / Ali), not digitised"),
             ("Digital", "Digital PDF exists but not yet ingested"),
             ("OCR", "OCR'd & ingested but low-confidence (needs_review) — old scans"),
             ("Schedule", "Program book ingested: titles/authors/type, NO abstract bodies"),
             ("Ingested", "Full abstracts ingested into the DB"),
             ("Pending", "Being collated by an external contact (OCS: Brit Finucci)"),
             ("NA", "Society/series did not exist that year")]
    for i, (st, mean) in enumerate(order, 2):
        leg.cell(row=i, column=1, value=st)
        leg.cell(row=i, column=2, value=mean)
        leg.cell(row=i, column=3).fill = PatternFill("solid", fgColor=FILL[st])
    notes = [
        "", "NOTES / ASSUMPTIONS:",
        "- ASIH the society dates to 1913; matrix starts 1983 (AES founding = start of elasmo/shark abstracts). Extend earlier on request.",
        "- ASIH/AES/JMIH/Other columns share one source book per year (the joint meeting), so their status moves together; AES cell shows the elasmo-abstract count where ingested.",
        "- 'OCR' status = the degraded 1997-2004 JMIH books (phone-photos, dewarped); all records flagged needs_review. Carylanne's planned FLATBED re-scans will upgrade these.",
        "- JMIH/ASIH host cities mostly unknown ('?') — Carylanne or the society records would have them; only 1997 (Seattle) confirmed here.",
        "- EEA 2010-2026 from Cat Gordon (Shark Trust) email 2026-07-28; pre-2010 EEA exists (founded ~1996) — Ali's archive goes back further (out of office till mid-Aug).",
        "- EEA is NOT yet ingested (no EEA books in the DB) — 2010-2019 hardcopy, 2018/2020-2026 digital, all awaiting acquisition.",
        "- OCS (Oceania Chondrichthyan Soc, ~2011+, biennial): Brit Finucci is collating all programme abstracts, pending council approval — exact years/locations TBC.",
        "- SI (Sharks International, quadrennial): 2018 Joao Pessoa + 2026 Colombo INGESTED; 2022 Valencia PDF received from Cat (not yet ingested); 2010 Cairns / 2014 Durban missing.",
        "- 'C' files (small 'YYYY ASIH.pdf' = Copeia business minutes, NOT abstracts) are DROPPED — they are the n=1 junk rows and are excluded from status here.",
        "- Carylanne Maier has ALL societies' abstracts 1992-2024 and is digitising the missing ones — so most 1992-2024 gaps are at least 'Hardcopy'.",
    ]
    for n in notes:
        leg.append([n])
    leg.column_dimensions["A"].width = 22
    leg.column_dimensions["B"].width = 90

    OUT.parent.mkdir(parents=True, exist_ok=True)
    wb.save(OUT)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    build()
