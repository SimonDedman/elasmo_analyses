"""Build the conference-abstract coverage matrix (xlsx).

Sheets (order): Legend & Notes | Coverage | Dashboard.
- Coverage: year x series, colour-coded red->green by status. ASIH/JMIH/Other
  collapsed to one 'ASIH/JMIH' column (they share one source book); AES kept
  separate (carries the elasmo count). Cells = "Location; Status". 'No
  conference' cells are left blank/unshaded.
- Dashboard: per-society totals bar chart + abstracts-over-time line chart.

Sources: the conference_abstracts DB; Cat Gordon (EEA locations + status);
Brit Finucci (OCS pending); Carylanne (1992-2024 hardcopy); AESconfLocations
(ASIH/JMIH host cities 1916-2025); known SI years.
"""
import csv
import sqlite3
from collections import defaultdict
from pathlib import Path

from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

REPO = Path(__file__).resolve().parents[2]
DB = REPO / "database" / "conference_abstracts.db"
OUT = REPO / "outputs" / "conference_coverage_matrix.xlsx"
ASIH_CSV = REPO / "database" / "asih_meetings.csv"

FILL = {
    "Missing": "E06666", "Hardcopy": "F6B26B", "OCR": "FFD966",
    "Digital": "FFE599", "Schedule": "B6D7A8", "Ingested": "6AA84F",
    "Pending": "D9D2E9", "NA": None,          # NA -> no fill (no conference)
}
EEA = {
    2010: ("Galway", "Hardcopy"), 2011: ("Berlin", "Hardcopy"),
    2012: ("Milan", "Hardcopy"),
    2013: ("Plymouth", "Digital"),      # abstract book PDF held locally
    2014: ("Leeuwarden", "Hardcopy"),
    2015: ("Peniche", "Digital"),       # abstract book held (EEA_2015_Book_of_abstracts.pdf)
    2016: ("Bristol", "Hardcopy"),
    2017: ("Amsterdam", "Digital"),     # programme held (not abstract book)
    2018: ("Peniche", "Digital"), 2019: ("Rende", "Hardcopy"),
    2020: ("online (covid)", "Digital"), 2021: ("Leiden", "Digital"),
    2022: ("Valencia (SI)", "Digital"),
    2023: ("Brighton", "Digital"),      # programme held; abstract book TBC
    2024: ("Thessaloniki", "Digital"), 2025: ("Rotterdam", "Digital"),
    2026: ("online", "Digital"),
}
SI = {2010: ("Cairns", "Missing"), 2014: ("Durban", "Missing"),
      2018: ("Joao Pessoa", "Ingested"), 2022: ("Valencia", "Ingested"),
      2026: ("Colombo", "Ingested")}
JMIH_DIGITAL = {2026}
SERIES = ["AES", "ASIH", "HL", "SSAR", "NIA", "SI"]


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


def db_meeting_status():
    con = sqlite3.connect(str(DB))
    out = {}
    for yr, meeting, doc, isocr, n, el in con.execute(
        """select m.year,m.meeting,m.doc_type,m.is_ocr,count(*) n,sum(a.is_elasmo) el
           from meetings m join abstracts a on a.meeting_id=m.meeting_id
           where m.meeting in ('JMIH','ASIH') group by m.meeting_id"""):
        d = out.setdefault(yr, dict(abstract=False, schedule=False, ocr=False, elasmo=0))
        if doc == "abstract_book" and n > 1:
            d.update(abstract=True, ocr=bool(isocr))
            d["elasmo"] += el or 0
        elif doc == "program_book" and n > 20:
            d["schedule"] = True
            d["elasmo"] += el or 0
    con.close()
    return out


def db_year_society():
    con = sqlite3.connect(str(DB))
    cnt = defaultdict(int)
    for yr, soc, meeting, n in con.execute(
        """select m.year,a.society,m.meeting,count(*) from abstracts a
           join meetings m on a.meeting_id=m.meeting_id
           where m.meeting in ('JMIH','ASIH','SI') group by m.year,a.society,m.meeting"""):
        if meeting == "SI":
            cnt[(yr, "SI")] += n
        else:
            for s in (soc or "").split("|"):
                if s in SERIES:
                    cnt[(yr, s)] += n
    con.close()
    return cnt


def meeting_cell(year, db):
    loc = JMIH_LOC.get(year, "?")
    d = db.get(year)
    if d and d["abstract"]:
        return loc, ("OCR" if d["ocr"] else "Ingested"), d["elasmo"]
    if d and d["schedule"]:
        return loc, "Schedule", d["elasmo"]
    if year in JMIH_DIGITAL:
        return loc, "Digital", 0
    if 1992 <= year <= 2024:
        return loc, "Hardcopy", 0
    return loc, "Missing", 0


def build():
    db = db_meeting_status()
    yr_soc = db_year_society()
    wb = Workbook()
    wb.remove(wb.active)
    thin = Side(style="thin", color="CCCCCC")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    # ---- Legend & Notes (first, per Simon's tab swap) ----
    leg = wb.create_sheet("Legend & Notes")
    leg.append(["Status", "Meaning", "Colour"])
    for c in leg[1]:
        c.font = Font(bold=True)
    order = [("Missing", "No known source"),
             ("Hardcopy", "Physical book exists (Carylanne / Cat / Ali), not digitised"),
             ("Digital", "Digital PDF exists but not yet ingested"),
             ("OCR", "OCR'd & ingested but low-confidence (needs_review) — old degraded scans"),
             ("Schedule", "Program book ingested: titles/authors/type, NO abstract bodies"),
             ("Ingested", "Full abstracts ingested into the DB"),
             ("Pending", "Being collated by an external contact (OCS: Brit Finucci)")]
    for i, (st, mean) in enumerate(order, 2):
        leg.cell(row=i, column=1, value=st)
        leg.cell(row=i, column=2, value=mean)
        leg.cell(row=i, column=3).fill = PatternFill("solid", fgColor=FILL[st])
    for note in [
        "", "NOTES:",
        "- 'ASIH/JMIH' = the American joint meeting (ASIH pre-1997, JMIH from 1997). ASIH/JMIH/HL/SSAR/NIA share one source book, collapsed to this column to remove duplicates.",
        "- 'AES' (American Elasmobranch Society, founded 1983) kept separate — cell shows elasmo-abstract count where ingested. Pre-1983 = no conference (blank).",
        "- Host cities 1916-2025 from github.com/SimonDedman/AESconfLocations; 2026 = New Orleans.",
        "- 'OCR' = degraded 1997-2004 JMIH phone-photo scans (all needs_review); Carylanne's flatbed re-scans will upgrade these.",
        "- No abstracts collected pre-1992 (Carylanne's archive starts 1992) → 1916-1991 show host city but 'Missing'.",
        "- EEA 2010-2026 from Cat Gordon (Shark Trust); pre-2010 in Ali's archive. EEA not yet ingested. SI2022 Valencia PDF received (Digital).",
        "- OCS (Oceania Chondrichthyan Soc, ~2011+, biennial): Brit Finucci collating, pending council — years/locations TBC.",
        "- Blank/unshaded cell = no conference that year for that series.",
        "- Per-society counts & trends: see the Dashboard tab.",
    ]:
        leg.append([note])
    leg.column_dimensions["A"].width = 12
    leg.column_dimensions["B"].width = 95

    # ---- Coverage ----
    ws = wb.create_sheet("Coverage")
    cols = ["Year", "ASIH/JMIH", "AES", "EEA", "OCS", "SI"]
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

    r = 2
    for year in range(1916, 2027):
        ws.cell(row=r, column=1, value=year).font = Font(bold=True)
        ws.cell(row=r, column=1).border = border
        loc, st, el = meeting_cell(year, db)
        put(r, 2, f"{loc}; {st}", st)
        # AES (founded 1983)
        if year >= 1983:
            aes_txt = f"{loc}" + (f" ({el})" if el else "") + f"; {st}"
            put(r, 3, aes_txt, st)
        else:
            put(r, 3, "", "NA")
        # EEA
        if year in EEA:
            l, s = EEA[year]; put(r, 4, f"{l}; {s}", s)
        elif 1997 <= year <= 2009:
            put(r, 4, "?; Hardcopy (Ali archive)", "Hardcopy")
        else:
            put(r, 4, "", "NA")
        # OCS (biennial ~2012+)
        if year >= 2012 and year % 2 == 0:
            put(r, 5, "?; Pending (Brit)", "Pending")
        else:
            put(r, 5, "", "NA")
        # SI (quadrennial)
        if year in SI:
            l, s = SI[year]; put(r, 6, f"{l}; {s}", s)
        else:
            put(r, 6, "", "NA")
        r += 1
    ws.column_dimensions["A"].width = 6
    for col in "BCDEF":
        ws.column_dimensions[col].width = 24
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

    OUT.parent.mkdir(parents=True, exist_ok=True)
    wb.save(OUT)
    print(f"wrote {OUT}  (sheets: {wb.sheetnames})")


if __name__ == "__main__":
    build()
