import json, glob, sys, collections, datetime, re
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter

S = sys.argv[1]; OUT = sys.argv[2]
cands = {c["abstract_id"]: c for c in json.load(open(f"{S}/candidates.json"))}
ext = {}
for f in sorted(glob.glob(f"{S}/results/batch_*.json")):
    for o in json.load(open(f)):
        ext[o["abstract_id"]] = o
missing = [a for a in cands if a not in ext]
print("candidates", len(cands), "extracted", len(ext), "missing", len(missing))

REL_ORDER = ["Project", "Uses citsci data", "Fisher / LEK knowledge", "Mentions only", "Not citsci"]
def relkey(r): return REL_ORDER.index(r) if r in REL_ORDER else 99

rows = []
for aid, c in cands.items():
    e = ext.get(aid, {})
    rows.append({
        "relevance": e.get("relevance") or "NOT EXTRACTED",
        "elasmo_relevant": {True: "yes", False: "no"}.get(e.get("elasmo_relevant"), ""),
        "project_name": e.get("project_name"),
        "organisation": e.get("organisation"),
        "country_region": e.get("country_region"),
        "species_taxa": e.get("species_taxa"),
        "participants": e.get("participants"),
        "data_type": e.get("data_type"),
        "platform_or_app": e.get("platform_or_app"),
        "scale_or_outputs": e.get("scale_or_outputs"),
        "summary": e.get("summary"),
        "likely_lead": e.get("likely_lead"),
        "first_affiliation": c["first_affiliation"],
        "affiliation_countries": c["affiliation_countries"],
        "authors": c["authors"],
        "conference": f'{c["meeting"]} {c["year"]}',
        "meeting_name": c["meeting_name"],
        "presentation_type": c["presentation_type"],
        "title": c["title"],
        "keyword_matches": c["match_terms"],
        "match_tier": c["tier"],
        "lexicon_elasmo_flag": "yes" if c["is_elasmo"] else "no",
        "abstract_id": aid,
        "abstract_text": c["abstract"],
    })
rows.sort(key=lambda r: (relkey(r["relevance"]), (r["project_name"] or "zzz").lower(), -int(r["conference"].split()[-1])))

wb = Workbook()
FONT = "Arial"
def style_sheet(ws, widths):
    for cell in ws[1]:
        cell.font = Font(name=FONT, bold=True)
        cell.alignment = Alignment(wrap_text=True, vertical="top")
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.font = Font(name=FONT)
            cell.alignment = Alignment(wrap_text=False, vertical="top")

# --- Info tab
info = wb.active; info.title = "Info"
counts = collections.Counter(r["relevance"] for r in rows)
named = collections.Counter(r["project_name"] for r in rows if r["project_name"] and r["relevance"] in ("Project", "Uses citsci data"))
conf_counts = collections.Counter(r["conference"].split()[0] for r in rows)
today = datetime.date.today().isoformat()
lines = [
 ("Citizen / community science in elasmobranch conference abstracts", True),
 (f"Generated {today} from database/conference_abstracts.db (23,408 abstracts, 123 meetings, 1992-2026: AES, ASIH/JMIH, EEA, OCS, Sharks International, SOMEPEC, IPFC, SQERF).", False),
 ("Purpose: feed the Shark Trust citizen-science directory (https://data.sharktrust.org/app/st_data/prod/page/citsci_directory) with projects and project leads found in conference abstracts.", False),
 ("", False),
 ("What was done automatically", True),
 ("1. Keyword screen of title + abstract + keywords for: citizen science, community science, citizen/community-based/-led, participatory, crowdsourcing, volunteer, public/diver/angler reports, sightings database/network, social media, named platforms (iNaturalist, Wildbook, Sharkbook, eOceans, Redmap, eggcase hunts, etc.), local ecological knowledge, public photo-ID.", False),
 ("2. Kept abstracts flagged as elasmobranch by the lexicon, plus every match from elasmo-only meetings (EEA, OCS, SI, SOMEPEC, AES). Non-elasmo JMIH matches (herps, teleosts) were dropped.", False),
 (f"3. Each of the {len(rows)} candidates was read by an LLM (Claude Sonnet) which classified it and pulled out project name, organisation, country, species, participants, data type, platform, scale, and likely lead. Fields are null where the abstract is silent; nothing was inferred from affiliations. LLM output is unreviewed by a human: treat it as a first pass.", False),
 ("", False),
 ("Tabs", True),
 ("Abstracts: one row per candidate abstract, sorted by relevance then project name. Filter column A.", False),
 ("Named projects: one row per distinct project/platform (relevance Project or Uses citsci data), grouped case-insensitively after dropping bracketed abbreviations and a leading The/Project or trailing Project/Programme; all spellings seen are listed in column A. Counts and leads are for working through contacts.", False),
 ("", False),
 ("Relevance values (column A of Abstracts)", True),
 ("Project = authors run or co-run a citizen/community science programme (the rows to chase for the directory).", False),
 ("Uses citsci data = study analyses data from a programme run by others (the programme is still worth listing).", False),
 ("Fisher / LEK knowledge = interviews or local ecological knowledge surveys, no ongoing public data collection.", False),
 ("Mentions only = recommended, proposed, or named in passing.", False),
 ("Not citsci = keyword false positive (volunteer assistants, ecological community, stakeholder workshops).", False),
 ("", False),
 ("Counts", True),
] + [(f"{k}: {counts[k]}", False) for k in REL_ORDER + [k for k in counts if k not in REL_ORDER]] + [
 (f"Distinct named projects/platforms: {len(named)}", False),
 ("By conference series: " + ", ".join(f"{k} {v}" for k, v in sorted(conf_counts.items())), False),
 ("", False),
 ("How to use", True),
 ("1. On Abstracts, filter relevance = Project; use likely_lead + first_affiliation + authors to find a contact (emails are not held in the database).", False),
 ("2. On Named projects, work down the list; each name links back to its abstracts via the abstract_id list.", False),
 ("3. Possible gaps: 47 of the candidates have no or a truncated abstract text (mostly SI 2026 and OCS programme-only years) and were classified from title + keywords alone, with most fields null; conference coverage is incomplete before 2005 and for OCS/EEA in some years (see outputs/conference_coverage_matrix.xlsx).", False),
 ("4. Grouping on Named projects is by normalised name only, so near-synonyms (Spot A Shark USA vs Spot-A-Shark USA, Basking Shark Watch vs Basking Shark Watch Project) may still appear as separate rows: merge by eye.", False),
]
for i, (t, bold) in enumerate(lines, 1):
    c = info.cell(row=i, column=1, value=t); c.font = Font(name=FONT, bold=bold, size=12 if i == 1 else 10)
    c.alignment = Alignment(wrap_text=True, vertical="top")
info.column_dimensions["A"].width = 140

# --- Abstracts tab
ws = wb.create_sheet("Abstracts")
cols = list(rows[0].keys())
ws.append(cols)
for r in rows: ws.append([r[c] for c in cols])
widths = {"relevance": 18, "elasmo_relevant": 8, "project_name": 32, "organisation": 28, "country_region": 22, "species_taxa": 26,
          "participants": 22, "data_type": 24, "platform_or_app": 18, "scale_or_outputs": 28, "summary": 60, "likely_lead": 22,
          "first_affiliation": 30, "affiliation_countries": 14, "authors": 40, "conference": 11, "meeting_name": 24,
          "presentation_type": 12, "title": 50, "keyword_matches": 30, "match_tier": 9, "lexicon_elasmo_flag": 8, "abstract_id": 10, "abstract_text": 60}
style_sheet(ws, [widths[c] for c in cols])
fills = {"Project": "C6EFCE", "Uses citsci data": "DDEBF7", "Fisher / LEK knowledge": "FFF2CC", "Mentions only": "F2F2F2", "Not citsci": "F8CBAD", "NOT EXTRACTED": "FF0000"}
for row in ws.iter_rows(min_row=2, max_col=1):
    f = fills.get(row[0].value)
    if f: row[0].fill = PatternFill("solid", fgColor=f)

# --- Named projects tab (pivot)
np_ = wb.create_sheet("Named projects")
def pkey(n):
    n = re.sub(r"\([^)]*\)", "", n).lower()
    n = re.sub(r"^(the|project|projeto)\s+", "", n.strip())
    n = re.sub(r"\s+(project|programme|program)$", "", n)
    return re.sub(r"[^a-z0-9]+", " ", n).strip()
groups = collections.OrderedDict()
for r in rows:
    if r["project_name"] and r["relevance"] in ("Project", "Uses citsci data"):
        for part in [s.strip() for s in r["project_name"].split(";") if s.strip()]:
            groups.setdefault(pkey(part), []).append(dict(r, _name=part))
np_.append(["project_name_variants", "n_abstracts", "best_relevance", "years", "organisation(s)", "country_region", "species_taxa", "platform_or_app", "likely_lead(s)", "first_affiliation(s)", "conferences", "abstract_ids"])
def uniq(seq):
    out = []
    for x in seq:
        if x and x not in out: out.append(x)
    return out
for i, (name, rs) in enumerate(sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0])), 2):
    yrs = sorted({int(r["conference"].split()[-1]) for r in rs})
    variants = uniq(r["_name"] for r in rs)
    np_.append(["; ".join(variants),
        len(rs),
        "Project" if any(r["relevance"] == "Project" for r in rs) else "Uses citsci data",
        f"{yrs[0]}-{yrs[-1]}" if len(yrs) > 1 else str(yrs[0]),
        "; ".join(uniq(r["organisation"] for r in rs)), "; ".join(uniq(r["country_region"] for r in rs)),
        "; ".join(uniq(r["species_taxa"] for r in rs)), "; ".join(uniq(r["platform_or_app"] for r in rs)),
        "; ".join(uniq(r["likely_lead"] for r in rs)), "; ".join(uniq(r["first_affiliation"] for r in rs)),
        "; ".join(uniq(r["conference"] for r in rs)), "; ".join(str(r["abstract_id"]) for r in rs)])
style_sheet(np_, [36, 11, 16, 10, 36, 28, 30, 20, 30, 36, 24, 20])
np_.cell(row=1, column=2).comment = None
wb._sheets = [info, ws, np_]
wb.save(OUT)
print("rows", len(rows), "named projects", len(groups), "->", OUT)
print({k: counts[k] for k in counts})
