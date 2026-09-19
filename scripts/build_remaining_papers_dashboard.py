#!/usr/bin/env python3
"""Build a self-contained HTML dashboard of the outstanding (not yet held) papers.

Reads docs/papers_data.json (the acquisition queue), the coauthor drop-folder
scan state, the drop folders, download_tracker.db, the SharkPapers library, and
the conference-abstracts DB (for abstract-book credit), and writes one static HTML page with inline data and inline SVG
charts. No server, no build step: open the file.

    python3 scripts/build_remaining_papers_dashboard.py [--out PATH]

"Outstanding" = last_status in {needs_library, needs_pdf, sr_sync_new}. Every
outstanding row is placed in exactly ONE constitution class (see classify()).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAPERS = ROOT / "docs" / "papers_data.json"
SCAN_STATE = ROOT / "outputs" / ".coauthor_scan_state.json"
DROP_ROOT = ROOT / "database" / "others_libraries"
OUT_DEFAULT = ROOT / "outputs" / "remaining_papers_dashboard.html"

OUTSTANDING = {"needs_library", "needs_pdf", "sr_sync_new"}
OA_OPEN = {"gold", "green", "hybrid", "bronze"}
CONF_RE = re.compile(
    r"abstract|proceedings|congress|conference|symposium|meeting|booklet|"
    r"workshop|colloque|encuentro|book of|programme|program book",
    re.I,
)

# Constitution classes, in display order. Keys are stable ids used in JS.
CLASSES = [
    ("abstract", "Conference abstract (abstracts project)"),
    ("conf_shaped", "Conference-shaped venue, no DOI (awaiting Track B review)"),
    ("doi_oa", "Has DOI, flagged open access (cascade failed)"),
    ("doi_closed", "Has DOI, closed access (needs a subscription)"),
    ("doi_unknown", "Has DOI, OA status unknown"),
    ("nodoi_damaged", "No DOI, blank or stub journal (metadata repair)"),
    ("nodoi_article", "No DOI, article-shaped (DOI recovery / archival)"),
]


def year_of(p) -> int:
    try:
        return int(float(p.get("year") or 0))
    except (TypeError, ValueError):
        return 0


def venue(p) -> str:
    return (p.get("findspot_raw") or p.get("journal_clean") or p.get("journal") or "").strip()


def classify(p) -> str:
    if p.get("triage") == "conference_abstract":
        return "abstract"
    doi = (p.get("doi") or "").strip()
    if doi:
        oa = (p.get("oa_status") or "unknown").lower()
        if oa in OA_OPEN:
            return "doi_oa"
        if oa == "closed":
            return "doi_closed"
        return "doi_unknown"
    if CONF_RE.search(venue(p)):
        return "conf_shaped"
    j = (p.get("journal") or "").strip()
    if len(j) < 4 or _is_surname_stub(j, p.get("authors") or ""):
        return "nodoi_damaged"
    return "nodoi_article"


def _is_surname_stub(journal: str, authors: str) -> bool:
    """Journal field equal to the first author's surname ("SMITH", "M. Smith"):
    the retriage spec's rule, deliberately not a length test (Ambio, Copeia)."""
    m = re.match(r"\s*([A-Za-z'\-]+)", authors)
    if not m:
        return False
    sur = m.group(1).lower()
    toks = re.findall(r"[A-Za-z'\-]+", journal.lower())
    return bool(toks) and sur in toks and len(toks) <= 3


def era(y: int) -> str:
    if y == 0:
        return "unknown"
    if y < 1900:
        return "pre-1900"
    if y < 1950:
        return "1900-49"
    if y >= 2020:
        return "2020s"
    return f"{y // 10 * 10}s"


ERA_ORDER = ["pre-1900", "1900-49", "1950s", "1960s", "1970s", "1980s", "1990s", "2000s", "2010s", "2020s", "unknown"]


def oa_class(p) -> str:
    oa = (p.get("oa_status") or "unknown").lower()
    if oa in OA_OPEN:
        return "open"
    if oa == "closed":
        return "closed"
    return "unknown"


LIBRARY = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")
TRACKER = ROOT / "database" / "download_tracker.db"
ABSTRACTS = ROOT / "database" / "conference_abstracts.json"
NOT_PEOPLE = {"SOMEPEC"}  # a society's drop folder, contributor unknown
PREFIX_CACHE = ROOT / "outputs" / ".crossref_prefix_cache.json"  # DOI prefix -> Crossref member name
VENUE_ROUTING = ROOT / "data" / "venue_routing.csv"  # hand-curated: venue -> country, route, likely members
# Display names. Drop-folder / tracker names on the left; the team roster (docs/remaining_downloads.html) on the right.
NAME_MAP = {"David": "David RG", "DavidGreen": "David Green", "Elena": "Elena", "Guuske": "Guuske",
            "David S": "David Shiffman", "Chiara": "Chiara Gambardella"}  # helper-page short names -> full names
# Simon, 2026-09-18: Dovi Kacev, Rima Jabado, Nick Dulvy, Nathan Perisic, and Emily Warren are not part of the
# download push, so they no longer count towards "people below the line". Anyone who delivers PDFs still appears.
ROSTER = ["Simon", "Guuske", "David RG", "Elena", "David Shiffman", "Chris Mull", "Alex McInturf", "Sophia Pelletier", "Deven Guerrero",
          "Ryan McMullen", "Lola Riesgo", "Ulrich", "Carylanne", "Tobi-Dawne Smith", "Chiara Gambardella",
          "Andrew Temple", "Cat", "Brit", "David Green"]
ABSTRACT_TEAM = {"Carylanne", "Cat", "Brit", "David Green"}  # deliver conference programmes, a different incentive
COAUTHOR_TARGET = 500  # score points for coauthorship (Simon, 2026-09-16; to be revisited against the pool)
ABSTRACT_CREDIT = 0.25  # one abstract book of N elasmo abstracts = ceil(N/4) papers (Simon, 2026-09-16)


def _series_year(name: str):
    """('JMIH', 2012) from any of our conference-book filenames, else None."""
    m = re.match(r"(\d{4})[_ ]+([A-Za-z]+)", name)
    if not m:
        return None
    return m.group(2).upper().replace("ASIH", "JMIH"), int(m.group(1))


def _doc_type(name: str) -> str:
    n = name.lower()
    if n.endswith(".xlsx") or "export" in n:
        return "export"
    if "copeia" in n:
        return "summary"
    if "abstract" in n:
        return "abstract"
    if "program" in n:
        return "programme"
    return "other"


def book_contributors():
    """source_pdf -> (person, basis) for every document in the abstracts DB.

    Rule: the person whose drop folder holds a file of the same series, year,
    and document type supplied it (same series+year with a different type is a
    weaker fallback, flagged); phone scans and Copeia summaries are Carylanne's
    digitising; Oxford Abstracts exports are David Green's; elasmo.org harvests,
    the SI 2026 programme export, and anything nobody's folder explains are
    Simon's (flagged "assumed")."""
    exact, loose = {}, {}
    if DROP_ROOT.is_dir():
        for d in DROP_ROOT.iterdir():
            if not d.is_dir() or d.name in NOT_PEOPLE:
                continue
            for f in d.rglob("*"):
                if f.is_file() and f.suffix.lower() in (".pdf", ".xlsx", ".doc", ".docx"):
                    key = _series_year(f.name)
                    if key:
                        exact.setdefault(key + (_doc_type(f.name),), d.name)
                        loose.setdefault(key, d.name)
    out = {}
    if not ABSTRACTS.exists():
        return out
    for r in json.load(open(ABSTRACTS)):
        src = str(r.get("source_pdf") or "")
        if src in out or not src:
            continue
        name = src.rsplit("/", 1)[-1]
        key = _series_year(name)
        typ = _doc_type(name)
        if src.startswith("http"):
            out[src] = ("Simon", "elasmo.org harvest")
        elif "phonescan" in name or typ == "summary":
            out[src] = ("Carylanne", "digitised hardcopy")
        elif name.endswith("AbstractExport.xlsx"):
            out[src] = ("DavidGreen", "Oxford Abstracts export")
        elif typ == "export":
            out[src] = ("Simon", "programme export we pulled ourselves")
        elif key and key + (typ,) in exact:
            out[src] = (exact[key + (typ,)], "same document in their drop folder")
        elif key and key in loose:
            out[src] = (loose[key], "same series and year in their drop folder (document type differs; check)")
        else:
            out[src] = ("Simon", "assumed: no drop folder holds it")
    return out


def abstract_credit():
    """Per person: list of (document, elasmo abstracts, credit)."""
    who = book_contributors()
    n_el = Counter()
    if ABSTRACTS.exists():
        for r in json.load(open(ABSTRACTS)):
            if r.get("is_elasmo"):
                n_el[str(r.get("source_pdf") or "")] += 1
    import math

    per = defaultdict(list)
    for src, (person, basis) in who.items():
        n = n_el.get(src, 0)
        if n:
            per[person].append({"doc": src.rsplit("/", 1)[-1] if not src.startswith("http") else src, "elasmo": n, "credit": math.ceil(n * ABSTRACT_CREDIT), "basis": basis})
    return per


def papers_by_person():
    """Unique literature_ids delivered per person: the daily drop-folder scan
    state plus the older download_tracker rows whose source names a person's
    folder. Simon = every other PDF in the library (his own collection plus
    every automated Sci-Hub / Unpaywall / publisher run)."""
    per = defaultdict(set)
    if SCAN_STATE.exists():
        for path, v in json.load(open(SCAN_STATE)).get("seen", {}).items():
            per[v.get("person") or "?"].add(str(v.get("literature_id") or path))
    if TRACKER.exists():
        import sqlite3

        c = sqlite3.connect(TRACKER)
        for lid, src in c.execute("select p.literature_id, s.source from download_status s join papers p on p.id=s.paper_id where s.status='downloaded'"):
            s = src or ""
            m = re.search(r"others_libraries/([A-Za-z]+)", s)
            if "Shark-References NAS" in s:
                per["Jürgen (Shark-References)"].add(str(lid))
            elif m:
                per[m.group(1)].add(str(lid))
            elif s.startswith("Elena"):
                per["Elena"].add(str(lid))
    counts = {k: len(v) for k, v in per.items() if k not in NOT_PEOPLE and k != "?"}
    lib_papers = 0
    if LIBRARY.is_dir():
        for root, _dirs, files in os.walk(LIBRARY):
            if "/Conferences" in root:
                continue
            lib_papers += sum(1 for f in files if f.lower().endswith(".pdf"))
    counts["Simon"] = max(0, lib_papers - sum(counts.values()))
    return counts, lib_papers


def team_table():
    papers, lib_papers = papers_by_person()
    credit = abstract_credit()
    papers = {NAME_MAP.get(k, k): v for k, v in papers.items()}
    credit = {NAME_MAP.get(k, k): v for k, v in credit.items()}
    people = (set(papers) | set(credit) | set(ROSTER)) - NOT_PEOPLE
    rows = []
    for who in people:
        cr = sum(x["credit"] for x in credit.get(who, []))
        rows.append({"person": who, "papers": papers.get(who, 0), "credit": cr, "docs": credit.get(who, []),
                     "total": papers.get(who, 0) + cr, "abstract_team": who in ABSTRACT_TEAM})
    rows.sort(key=lambda r: (-r["total"], r["person"]))
    return rows, lib_papers


def venue_routing():
    import csv

    if not VENUE_ROUTING.exists():
        return {}
    with open(VENUE_ROUTING, newline="") as fh:
        return {r["venue"]: r for r in csv.DictReader(fh)}


def publisher_of(p, prefix_map=None) -> str:
    """The same publisher name the closed-access pages use and that
    backfill_queue_publishers.py writes into the queue, so a bar's label is
    always a value docs/remaining_downloads.html can filter on."""
    sys.path.insert(0, str(ROOT / "scripts"))
    from generate_closed_access_html import resolve_publisher  # noqa: WPS433
    return resolve_publisher(p)


def nodoi_type(p) -> str:
    """Coarse venue type for the no-DOI article-shaped pool."""
    j = (p.get("journal") or "").strip()
    f = p.get("findspot_raw") or ""
    both = (j + " " + f).lower()
    if re.search(r"suppl|abstracts?\b|program", f, re.I) and re.search(r"paleontology|comparative biology|meeting", both):
        return "meeting abstracts in a journal"
    if re.search(r"thesis|dissertation|\bphd\b|\bmsc\b|\bm\.sc|\bph\.d|tesis|tesi\b|diplomarbeit|mémoire|memoria", both):
        return "thesis"
    if re.match(r"^in\b", j.lower()) or re.match(r"^in\b", f.lower()) or re.search(r"\(eds?\.?\)|editors?\b|chapter", f.lower()):
        return "book chapter"
    if re.search(r"report|technical|tech\.|memorandum|working paper|document|circular|fao |noaa|iccat|sci\. counc|nafo|ices|\bcm ", both):
        return "report / grey"
    if len(j) < 4 or re.match(r"^[A-Z][a-z]+$", j) or re.match(r"^[A-Z]\.\s?[A-Z]?\.?\s?[A-Z][a-z]+", j):
        return "stub / editor surname"
    return "journal"


def build():
    papers = json.load(open(PAPERS))
    out = [p for p in papers if p.get("last_status") in OUTSTANDING]
    for p in out:
        p["_cls"] = classify(p)
        p["_year"] = year_of(p)
        p["_era"] = era(p["_year"])

    cls_counts = Counter(p["_cls"] for p in out)
    with_doi = [p for p in out if p["_cls"].startswith("doi_")]

    # era x class
    era_cls = defaultdict(Counter)
    for p in out:
        era_cls[p["_era"]][p["_cls"]] += 1

    # year x (with DOI / no DOI / abstract-ish), 1900..now
    year_rows = defaultdict(Counter)
    for p in out:
        y = p["_year"]
        if y >= 1900:
            grp = "abstract" if p["_cls"] in ("abstract", "conf_shaped") else ("doi" if p["_cls"].startswith("doi_") else "nodoi")
            year_rows[y][grp] += 1

    sys.path.insert(0, str(ROOT / "scripts"))
    from lib.crossref_prefix import _load as _prefix_cache  # noqa: WPS433

    prefix_map = _prefix_cache()
    # rows whose STORED publisher is empty, so the hub cannot filter to them until the backfill runs
    n_prefix_resolved = sum(1 for p in with_doi if (p.get("publisher") or "").strip() in ("", "Unknown publisher"))

    # publisher x OA class (with DOI)
    pub = defaultdict(Counter)
    for p in with_doi:
        pub[publisher_of(p, prefix_map)][oa_class(p)] += 1
    pub_sorted = sorted(pub.items(), key=lambda kv: -sum(kv[1].values()))
    TOP = 22
    pub_rows = [{"name": k, **{c: v.get(c, 0) for c in ("closed", "unknown", "open")}} for k, v in pub_sorted[:TOP]]
    tail = Counter()
    for _, v in pub_sorted[TOP:]:
        tail.update(v)
    if tail:
        pub_rows.append({"name": f"Other ({len(pub_sorted) - TOP} publishers)", **{c: tail.get(c, 0) for c in ("closed", "unknown", "open")}})

    # recent (2024+) with DOI by publisher
    recent = defaultdict(Counter)
    for p in with_doi:
        if p["_year"] >= 2024:
            recent[publisher_of(p, prefix_map)][oa_class(p)] += 1
    recent_sorted = sorted(recent.items(), key=lambda kv: -sum(kv[1].values()))
    recent_rows = [{"name": k, **{c: v.get(c, 0) for c in ("closed", "unknown", "open")}} for k, v in recent_sorted[:15]]
    rtail = Counter()
    for _, v in recent_sorted[15:]:
        rtail.update(v)
    if rtail:
        recent_rows.append({"name": f"Other ({len(recent_sorted) - 15} publishers)", **{c: rtail.get(c, 0) for c in ("closed", "unknown", "open")}})

    # no-DOI article-shaped: top venues, with routing flags, and era x type
    nodoi_venues = Counter()
    nodoi_et = defaultdict(Counter)
    nodoi_pool = [p for p in out if p["_cls"] in ("nodoi_article", "nodoi_damaged")]
    for p in nodoi_pool:
        nodoi_venues[(p.get("journal_clean") or p.get("journal") or "").strip()] += 1
        nodoi_et[p["_era"]][nodoi_type(p)] += 1
    routing = venue_routing()
    venue_rows = []
    for k, v in nodoi_venues.most_common(45):
        r = routing.get(k, {})
        venue_rows.append({"name": k or "(blank)", "n": v, "country": r.get("country", ""), "route": r.get("route", ""),
                           "members": r.get("likely_members", ""), "kind": r.get("kind", ""), "notes": r.get("notes", "")})
    NODOI_TYPES = ["journal", "meeting abstracts in a journal", "book chapter", "thesis", "report / grey", "stub / editor surname"]

    team, lib_papers = team_table()

    recent_total = sum(1 for p in out if p["_year"] >= 2024)
    recent_doi = sum(1 for p in with_doi if p["_year"] >= 2024)

    data = {
        "generated": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z"),
        "total_rows": len(papers),
        "outstanding": len(out),
        "classes": [{"id": k, "label": lab, "n": cls_counts.get(k, 0)} for k, lab in CLASSES],
        "with_doi": len(with_doi),
        "no_doi": sum(cls_counts[k] for k in ("nodoi_damaged", "nodoi_article", "conf_shaped")),
        "abstracts": cls_counts["abstract"] + cls_counts["conf_shaped"],
        "recent_total": recent_total,
        "recent_doi": recent_doi,
        "pre1950": sum(1 for p in out if 0 < p["_year"] < 1950),
        "era_order": ERA_ORDER,
        "era_cls": {e: dict(era_cls[e]) for e in ERA_ORDER if era_cls.get(e)},
        "years": [{"year": y, **dict(c)} for y, c in sorted(year_rows.items())],
        "publishers": pub_rows,
        "publishers_total": len(pub_sorted),
        "recent_publishers": recent_rows,
        "nodoi_venues": venue_rows,
        "nodoi_types": NODOI_TYPES,
        "nodoi_era_type": {e: dict(nodoi_et[e]) for e in ERA_ORDER if nodoi_et.get(e)},
        "nodoi_pool": len(nodoi_pool),
        "prefix_resolved": n_prefix_resolved,
        "team": team,
        "library_papers": lib_papers,
        "abstract_credit": ABSTRACT_CREDIT,
        "coauthor_target": COAUTHOR_TARGET,
        "roster": sorted(ROSTER, key=str.lower),
    }
    return data


HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Remaining papers</title>
<style>
:root {
  color-scheme: light;
  --page: #f9f9f7; --surface: #fcfcfb; --ink: #0b0b0b; --ink2: #52514e; --muted: #898781;
  --grid: #e1e0d9; --axis: #c3c2b7; --border: rgba(11,11,11,0.10);
  --s1: #2a78d6; --s2: #eb6834; --s3: #1baf7a; --s4: #eda100; --s5: #e87ba4; --s6: #008300; --s7: #4a3aa7; --s8: #e34948; --s9: #b0368f; --s10: #0099ad;
  --seq: #2a78d6;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    color-scheme: dark;
    --page: #0d0d0d; --surface: #1a1a19; --ink: #ffffff; --ink2: #c3c2b7; --muted: #898781;
    --grid: #2c2c2a; --axis: #383835; --border: rgba(255,255,255,0.10);
    --s1: #3987e5; --s2: #d95926; --s3: #199e70; --s4: #c98500; --s5: #d55181; --s6: #008300; --s7: #9085e9; --s8: #e66767; --s9: #c24aa0; --s10: #16a6b8;
    --seq: #3987e5;
  }
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --page: #0d0d0d; --surface: #1a1a19; --ink: #ffffff; --ink2: #c3c2b7; --muted: #898781;
  --grid: #2c2c2a; --axis: #383835; --border: rgba(255,255,255,0.10);
  --s1: #3987e5; --s2: #d95926; --s3: #199e70; --s4: #c98500; --s5: #d55181; --s6: #008300; --s7: #9085e9; --s8: #e66767; --s9: #c24aa0; --s10: #16a6b8;
  --seq: #3987e5;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--page); color: var(--ink); font: 15px/1.45 system-ui, -apple-system, "Segoe UI", sans-serif; }
main { max-width: 1240px; margin: 0 auto; padding: 24px 16px 64px; }
h1 { font-size: 26px; margin: 0 0 4px; font-weight: 650; }
.sub { color: var(--ink2); margin: 0 0 20px; }
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; margin-bottom: 24px; }
.tile { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 14px 16px; }
.tile .v { font-size: 34px; font-weight: 650; line-height: 1.1; }
.tile .k { color: var(--ink2); font-size: 13px; margin-top: 4px; }
.tile .d { color: var(--muted); font-size: 12px; margin-top: 2px; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(420px, 1fr)); gap: 16px; }
@media (max-width: 900px) { .grid { grid-template-columns: 1fr; } }
.card { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 16px 16px 10px; min-width: 0; }
.card.wide { grid-column: 1 / -1; }
.card h2 { font-size: 16px; margin: 0 0 2px; font-weight: 650; }
.card .note { color: var(--ink2); font-size: 13px; margin: 0 0 10px; }
.legend { display: flex; flex-wrap: wrap; gap: 6px 16px; font-size: 13px; color: var(--ink2); margin: 0 0 8px; }
.legend span::before { content: ""; display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 6px; vertical-align: -1px; background: var(--c); }
svg { display: block; width: 100%; height: auto; overflow: visible; }
svg text { font: 12px system-ui, -apple-system, "Segoe UI", sans-serif; fill: var(--ink2); }
svg text.lab { fill: var(--ink); }
svg a text.lab { fill: var(--link, #1a5fb4); text-decoration: underline; cursor: pointer; }
svg a:hover text.lab { opacity: .75; }
svg text.val { fill: var(--ink2); }
svg line.grid { stroke: var(--grid); stroke-width: 1; }
svg line.axis { stroke: var(--axis); stroke-width: 1; }
svg rect.bar { transition: opacity .12s; }
svg g.row:hover rect.bar, svg g.col:hover rect.bar { opacity: .82; }
details { margin-top: 8px; }
summary { cursor: pointer; color: var(--ink2); font-size: 13px; }
table { border-collapse: collapse; font-size: 13px; margin-top: 6px; width: 100%; }
th, td { text-align: left; padding: 3px 8px 3px 0; border-bottom: 1px solid var(--grid); }
td.n, th.n { text-align: right; font-variant-numeric: tabular-nums; }
#tip { position: fixed; pointer-events: none; background: var(--ink); color: var(--page); padding: 6px 9px; border-radius: 6px; font-size: 12.5px; opacity: 0; transition: opacity .08s; z-index: 10; max-width: 320px; }
.foot { color: var(--muted); font-size: 12px; margin-top: 28px; }
.namebar { position: sticky; top: 0; z-index: 20; background: var(--surface); border-bottom: 1px solid var(--border); padding: 7px 16px; display: flex; align-items: center; flex-wrap: wrap; gap: 8px; font-size: 12.5px; color: var(--ink2); }
.namebar label { font-weight: 600; }
.namebar select, .namebar input[type="text"] { font: inherit; padding: 3px 6px; border-radius: 6px; border: 1px solid var(--border); background: var(--page); color: var(--ink); }
.namebar .hint { color: var(--muted); }
.comment-ui { margin-top: 8px; }
.comment-toggle { background: none; border: 1px solid var(--border); color: var(--ink2); font: inherit; font-size: 12px; padding: 2px 9px; border-radius: 6px; cursor: pointer; }
.comment-toggle:hover { background: var(--page); }
.comment-box { display: none; margin-top: 6px; max-width: 520px; }
.comment-box.open { display: block; }
.comment-box textarea { width: 100%; min-height: 52px; font: inherit; font-size: 13px; padding: 6px 8px; border-radius: 6px; border: 1px solid var(--border); background: var(--page); color: var(--ink); resize: vertical; box-sizing: border-box; }
.comment-box .row { display: flex; align-items: center; gap: 8px; margin-top: 4px; }
.comment-box button.post { background: var(--s1); color: #fff; border: none; padding: 4px 12px; border-radius: 6px; font-size: 12.5px; cursor: pointer; }
.comment-box button.post:disabled { opacity: .5; cursor: default; }
.comment-status { font-size: 12px; color: var(--muted); }
.comment-list { margin-top: 6px; font-size: 12.5px; color: var(--ink2); display: flex; flex-direction: column; gap: 5px; max-width: 640px; }
.comment-list .c { border-left: 2px solid var(--border); padding-left: 8px; }
.comment-list .meta { color: var(--muted); }
.comment-unavailable { font-size: 12px; color: var(--muted); font-style: italic; margin: 6px 0 0; }
</style>
</head>
<body>
<div id="tip"></div>
<div class="namebar" id="namebar">
  <label for="commentName">Your name</label>
  <select id="commentName"></select>
  <input type="text" id="commentNameOther" placeholder="Your name" style="display:none; width:150px;">
  <span class="hint">used to attribute comments left on the charts below</span>
</div>
<main>
<h1>Remaining papers</h1>
<p class="sub" id="sub"></p>
<div class="tiles" id="tiles"></div>
<div class="grid" id="grid"></div>
<p class="foot" id="foot"></p>
</main>
<script id="data" type="application/json">__DATA__</script>
<script>
const D = JSON.parse(document.getElementById('data').textContent);
// Same Apps Script web app the download helper (docs/remaining_downloads.html)
// posts to. It does not yet handle getComments/addComment — see
// outputs/download_push_2026-09-17/G_comments/apps_script_additions.gs.
const COMMENTS_URL = 'https://script.google.com/macros/s/AKfycbwCmkL89I8GGK3-IoCZh9x9XAVpvTshOysMlnWiRmqoXAtICFO16TkljEPlxTwXaufR/exec';
const fmt = n => n.toLocaleString('en-GB');
// One meaning per colour on every chart (Simon, 2026-09-19): DOI family = blue (closed) / green (open) / amber
// (unknown); no DOI = orange, with teal for damaged metadata; abstracts = violet, conference-shaped = plum.
// Validated with the dataviz skill's validate_palette.js in stack order, light and dark: all checks pass.
const CLS_COLOR = { abstract:'var(--s7)', conf_shaped:'var(--s9)', doi_oa:'var(--s3)', doi_closed:'var(--s1)', doi_unknown:'var(--s4)', nodoi_damaged:'var(--s10)', nodoi_article:'var(--s2)' };
const OA_COLOR = { closed:'var(--s1)', unknown:'var(--s4)', open:'var(--s3)' };  // same as the DOI classes above
const OA_LABEL = { closed:'Closed', unknown:'OA unknown', open:'Open access (fetch failed)' };
const clsLabel = Object.fromEntries(D.classes.map(c => [c.id, c.label]));

// ---- tooltip
const tip = document.getElementById('tip');
function showTip(e, html) { tip.innerHTML = html; tip.style.opacity = 1; moveTip(e); }
function moveTip(e) { const x = Math.min(e.clientX + 14, window.innerWidth - 330); tip.style.left = x + 'px'; tip.style.top = (e.clientY + 14) + 'px'; }
function hideTip() { tip.style.opacity = 0; }
function hover(el, html) { el.addEventListener('mousemove', e => showTip(e, html)); el.addEventListener('mouseleave', hideTip); }

// ---- helpers
const NS = 'http://www.w3.org/2000/svg';
function el(tag, attrs, parent) { const n = document.createElementNS(NS, tag); for (const k in attrs) n.setAttribute(k, attrs[k]); if (parent) parent.appendChild(n); return n; }
function text(parent, x, y, s, cls, anchor) { const t = el('text', {x, y, 'text-anchor': anchor || 'start', 'dominant-baseline': 'middle'}, parent); if (cls) t.setAttribute('class', cls); t.textContent = s; return t; }
function niceMax(v) { const p = Math.pow(10, Math.floor(Math.log10(v))); const f = v / p; const m = f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10; return m * p; }
function ticks(max, n) { const step = niceMax(max / n); const out = []; for (let v = 0; v <= max + 1e-9; v += step) out.push(Math.round(v)); return out; }
// rounded end on the far side only (bars grow from a baseline)
function barPathH(x, y, w, h, r) { r = Math.min(r, w, h / 2); return `M${x},${y} h${w - r} a${r},${r} 0 0 1 ${r},${r} v${h - 2 * r} a${r},${r} 0 0 1 ${-r},${r} h${-(w - r)} z`; }
function barPathV(x, y, w, h, r) { r = Math.min(r, h, w / 2); return `M${x},${y + h} v${-(h - r)} a${r},${r} 0 0 1 ${r},${-r} h${w - 2 * r} a${r},${r} 0 0 1 ${r},${r} v${h - r} z`; }

// ---- comments: helpers ----
// Card ids are derived from the title with digits stripped first, so a chart
// whose title bakes in a live count (e.g. "Publisher of the 4,123 papers
// with a DOI") keeps the SAME id across rebuilds as that count changes —
// otherwise every corpus refresh would orphan every comment on that card.
function slugify(s) {
  return String(s).replace(/[0-9]+/g, '').toLowerCase().replace(/[^a-z]+/g, '-').replace(/^-+|-+$/g, '') || 'card';
}
const cardRegistry = [];
const usedSlugs = {};
function uniqueSlug(title) {
  const base = slugify(title); let s = base, n = 2;
  while (usedSlugs[s]) { s = base + '-' + n; n++; }
  usedSlugs[s] = true; return s;
}
function escapeHtml(s) { return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }
function fmtWhen(iso) {
  try { const d = new Date(iso); if (isNaN(d.getTime())) return iso || ''; return d.toLocaleDateString('en-GB', {day: 'numeric', month: 'short', year: 'numeric'}) + ' ' + d.toLocaleTimeString('en-GB', {hour: '2-digit', minute: '2-digit'}); }
  catch (e) { return iso || ''; }
}
function currentCommentName() {
  const sel = document.getElementById('commentName'); if (!sel) return '';
  if (sel.value === '__other__') { const o = document.getElementById('commentNameOther'); return o ? o.value.trim() : ''; }
  return sel.value.trim();
}
function postComment(cardId, by, text) {
  return fetch(COMMENTS_URL, {method: 'POST', body: JSON.stringify({action: 'addComment', card: cardId, by: by, text: text, page: 'remaining_papers_dashboard'})})
    .then(r => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
    .then(j => { if (j && j.error) throw new Error(j.error); return j; });
}
function addCommentToList(cardId, cm) {
  const list = document.getElementById('clist-' + cardId); if (!list) return;
  const row = document.createElement('div'); row.className = 'c';
  row.innerHTML = `<span class="meta">${escapeHtml(cm.by)} · ${fmtWhen(cm.at)}</span><br>${escapeHtml(cm.text)}`;
  list.insertBefore(row, list.firstChild);
  const toggle = document.querySelector(`.comment-toggle[data-id="${cardId}"]`);
  if (toggle) { const n = list.children.length; toggle.textContent = 'Comment (' + n + ')'; }
}
function addCommentUI(c, id) {
  const box = document.createElement('div'); box.className = 'comment-ui';
  box.innerHTML = `<button type="button" class="comment-toggle" data-id="${id}">Comment</button>
    <div class="comment-box" id="cbox-${id}">
      <textarea maxlength="2000" placeholder="Add a comment about this chart..."></textarea>
      <div class="row"><button type="button" class="post">Post</button><span class="comment-status"></span></div>
    </div>
    <div class="comment-list" id="clist-${id}"></div>`;
  c.appendChild(box);
  const toggle = box.querySelector('.comment-toggle'), panel = box.querySelector('.comment-box');
  toggle.addEventListener('click', () => panel.classList.toggle('open'));
  const postBtn = box.querySelector('button.post'), status = box.querySelector('.comment-status'), ta = box.querySelector('textarea');
  postBtn.addEventListener('click', () => {
    const name = currentCommentName(), body = ta.value.trim();
    if (!name) { status.textContent = 'pick your name above first'; return; }
    if (!body) { status.textContent = 'type something first'; return; }
    postBtn.disabled = true; status.textContent = 'posting…';
    postComment(id, name, body).then(() => {
      status.textContent = 'posted'; ta.value = '';
      addCommentToList(id, {by: name, at: new Date().toISOString(), text: body});
      setTimeout(() => { status.textContent = ''; }, 3000);
    }).catch(err => { status.textContent = 'error: ' + (err && err.message ? err.message : err); })
      .finally(() => { postBtn.disabled = false; });
  });
}
function markCommentsUnavailable() {
  document.querySelectorAll('.comment-ui').forEach(box => {
    box.innerHTML = '<p class="comment-unavailable">comments unavailable (endpoint not deployed yet)</p>';
  });
}

function card(title, note, wide, noComments) {
  const c = document.createElement('section'); c.className = 'card' + (wide ? ' wide' : '');
  const id = uniqueSlug(title);
  c.id = 'card-' + id;
  c.innerHTML = `<h2>${title}</h2><p class="note">${note}</p>`;
  document.getElementById('grid').appendChild(c);
  if (!noComments) { addCommentUI(c, id); cardRegistry.push({id: id, title: title, el: c}); }
  return c;
}
function legend(c, items) { const l = document.createElement('div'); l.className = 'legend'; l.innerHTML = items.map(([lab, col]) => `<span style="--c:${col}">${lab}</span>`).join(''); c.appendChild(l); }
// The download hub (docs/remaining_downloads.html) takes ?publisher= and ?journal= deep links and
// matches them against the exact stored value. Relative on the site; absolute from a local copy.
const HUB = location.protocol === 'file:' ? 'https://simondedman.github.io/elasmo_analyses/remaining_downloads.html' : '../remaining_downloads.html';
const hubLink = (param, value) => `${HUB}?${param}=${encodeURIComponent(value)}`;
const esc = s => String(s).replace(/[&<>"]/g, ch => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[ch]));
function svgLink(parent, href, title) { const a = el('a', {href, target: '_blank', rel: 'noopener'}, parent); const t = el('title', {}, a); t.textContent = title; return a; }

function tableView(c, header, rows) {
  const d = document.createElement('details'); d.innerHTML = `<summary>Table view</summary>`;
  const t = document.createElement('table');
  t.innerHTML = '<tr>' + header.map((h, i) => `<th class="${i ? 'n' : ''}">${h}</th>`).join('') + '</tr>' + rows.map(r => '<tr>' + r.map((v, i) => `<td class="${i ? 'n' : ''}">${typeof v === 'number' ? fmt(v) : (v && v.href ? `<a href="${esc(v.href)}" target="_blank" rel="noopener">${esc(v.text)}</a>` : v)}</td>`).join('') + '</tr>').join('');
  d.appendChild(t); c.appendChild(d);
}

// Horizontal bars; series = [{key,label,color}], rows = [{name, key1:n, ...}]
function hbars(c, rows, series, opts = {}) {
  const labW = opts.labW || 230, rowH = 26, barH = 18, padT = 6, padR = 60;
  const W = opts.W || 640, H = padT + rows.length * rowH + 24;
  const svg = el('svg', {viewBox: `0 0 ${W} ${H}`}, c);
  const totals = rows.map(r => series.reduce((a, s) => a + (r[s.key] || 0), 0));
  const max = niceMax(Math.max(...totals) * 1.02);
  const scale = v => (W - labW - padR) * v / max;
  for (const tv of ticks(max, 4)) { const x = labW + scale(tv); el('line', {x1: x, x2: x, y1: padT, y2: padT + rows.length * rowH, class: 'grid'}, svg); text(svg, x, H - 8, fmt(tv), '', 'middle'); }
  el('line', {x1: labW, x2: labW, y1: padT, y2: padT + rows.length * rowH, class: 'axis'}, svg);
  rows.forEach((r, i) => {
    const g = el('g', {class: 'row'}, svg); const y = padT + i * rowH + (rowH - barH) / 2;
    const name = r.name.length > 34 ? r.name.slice(0, 33) + '…' : r.name;
    const href = opts.link ? opts.link(r) : null;
    text(href ? svgLink(g, href, `Open the ${r.name} papers in the download hub`) : g, labW - 8, y + barH / 2, name, 'lab', 'end').setAttribute('title', r.name);
    let x = labW;
    const html = `<b>${r.name}</b><br>` + series.map(s => `${s.label}: ${fmt(r[s.key] || 0)}`).join('<br>') + (series.length > 1 ? `<br>Total: ${fmt(totals[i])}` : '');
    series.forEach((s, si) => {
      const v = r[s.key] || 0; if (!v) return;
      let w = scale(v); const last = series.slice(si + 1).every(t => !(r[t.key] || 0));
      const gap = last ? 0 : 2;
      const p = last ? barPathH(x, y, w - gap, barH, 4) : `M${x},${y} h${w - gap} v${barH} h${-(w - gap)} z`;
      el('path', {d: p, fill: s.color, class: 'bar'}, g); x += w;
    });
    text(g, x + 6, y + barH / 2, fmt(totals[i]), 'val');
    hover(g, html);
  });
  if (series.length > 1) legend(c, series.map(s => [s.label, s.color]));
  tableView(c, ['', ...series.map(s => s.label), ...(series.length > 1 ? ['Total'] : [])], rows.map((r, i) => [opts.link && opts.link(r) ? {text: r.name, href: opts.link(r)} : r.name, ...series.map(s => r[s.key] || 0), ...(series.length > 1 ? [totals[i]] : [])]));
}

// Vertical stacked columns; cats = x labels, series as above, get(cat,key)
function vcols(c, cats, series, get, opts = {}) {
  const W = 1180, H = 300, padL = 52, padR = 10, padT = 10, padB = 28;
  const svg = el('svg', {viewBox: `0 0 ${W} ${H}`}, c);
  const plotW = W - padL - padR, plotH = H - padT - padB;
  const totals = cats.map(cat => series.reduce((a, s) => a + get(cat, s.key), 0));
  const max = niceMax(Math.max(...totals) * 1.05);
  const sy = v => plotH * v / max;
  const slot = plotW / cats.length, bw = Math.min(opts.maxBar || 24, slot * 0.7);
  for (const tv of ticks(max, 4)) { const y = padT + plotH - sy(tv); el('line', {x1: padL, x2: W - padR, y1: y, y2: y, class: 'grid'}, svg); text(svg, padL - 8, y, fmt(tv), '', 'end'); }
  el('line', {x1: padL, x2: W - padR, y1: padT + plotH, y2: padT + plotH, class: 'axis'}, svg);
  const labelEvery = opts.labelEvery || 1;
  cats.forEach((cat, i) => {
    const g = el('g', {class: 'col'}, svg); const x = padL + i * slot + (slot - bw) / 2;
    let yTop = padT + plotH;
    const html = `<b>${cat}</b><br>` + series.map(s => `${s.label}: ${fmt(get(cat, s.key))}`).join('<br>') + `<br>Total: ${fmt(totals[i])}`;
    series.forEach((s, si) => {
      const v = get(cat, s.key); if (!v) return; const h = sy(v);
      const last = series.slice(si + 1).every(t => !get(cat, t.key)); const gap = last ? 0 : 2;
      const p = last ? barPathV(x, yTop - h, bw, h - gap, 4) : `M${x},${yTop - h + gap} h${bw} v${h - gap} h${-bw} z`;
      el('path', {d: p, fill: s.color, class: 'bar'}, g); yTop -= h;
    });
    // hit target wider than the mark
    el('rect', {x: padL + i * slot, y: padT, width: slot, height: plotH, fill: 'transparent'}, g);
    if (i % labelEvery === 0) text(svg, x + bw / 2, H - 10, String(cat), '', 'middle');
    hover(g, html);
  });
  legend(c, series.map(s => [s.label, s.color]));
  tableView(c, ['', ...series.map(s => s.label), 'Total'], cats.map((cat, i) => [cat, ...series.map(s => get(cat, s.key)), totals[i]]));
}

// ---- header
// Bridge to the download hub's headline so the two pages can be reconciled at a glance.
const flaggedAbs = (D.classes.find(k => k.id === 'abstract') || {n: 0}).n;
document.getElementById('sub').innerHTML = `${fmt(D.outstanding)} outstanding = ${fmt(D.outstanding - flaggedAbs)} papers to get (the <a href="${HUB}">download hub</a>'s "Remaining") + ${fmt(flaggedAbs)} flagged conference abstracts. ${fmt(D.total_rows - D.outstanding)} more rows in docs/papers_data.json are already downloaded and await filing. Generated ${D.generated}.`;
const belowLine = D.team.filter(t => t.person !== 'Simon' && !t.abstract_team && t.total < D.coauthor_target).length;
const assignable = D.classes.filter(k => k.id === 'doi_closed' || k.id === 'doi_unknown').reduce((a, k) => a + k.n, 0);
const tiles = [
  [D.outstanding, 'outstanding', `wanted, not held: ${fmt(D.outstanding - flaggedAbs)} papers + ${fmt(flaggedAbs)} flagged abstracts`],
  [D.with_doi, 'have a DOI', 'publisher resolves; assignable to a person'],
  [D.no_doi, 'no DOI', 'DOI recovery, metadata repair, or archival'],
  [D.abstracts, 'conference abstracts', 'abstracts project, not a download'],
  [D.recent_total, 'published 2024 or later', `${fmt(D.recent_doi)} of them have a DOI`],
  [D.pre1950, 'pre-1950', 'scans, BHL, archive.org, ILL'],
  [Math.round(assignable / Math.max(1, belowLine)), 'assignable papers per person below the line', `${fmt(assignable)} DOI + closed/unknown ÷ ${belowLine} people under ${fmt(D.coauthor_target)} pts; the 500 line should track this`],
];
document.getElementById('tiles').innerHTML = tiles.map(([v, k, d]) => `<div class="tile"><div class="v">${fmt(v)}</div><div class="k">${k}</div><div class="d">${d}</div></div>`).join('');

// ---- name bar: who is commenting ----
(function() {
  const sel = document.getElementById('commentName'), other = document.getElementById('commentNameOther');
  const roster = (D.roster || []).slice().sort((a, b) => a.localeCompare(b));
  sel.innerHTML = '<option value="">-- pick your name --</option>' +
    roster.map(n => `<option value="${escapeHtml(n)}">${escapeHtml(n)}</option>`).join('') +
    '<option value="__other__">Other…</option>';
  let saved = '', savedOther = '';
  try { saved = localStorage.getItem('eea_dashboard_comment_name') || ''; savedOther = localStorage.getItem('eea_dashboard_comment_name_other') || ''; } catch (e) {}
  if (saved) {
    sel.value = saved;
    if (sel.value !== saved) sel.value = '';  // roster no longer has this value; don't silently pick another name
  }
  if (sel.value === '__other__') { other.style.display = ''; other.value = savedOther; }
  sel.addEventListener('change', () => {
    other.style.display = sel.value === '__other__' ? '' : 'none';
    try { localStorage.setItem('eea_dashboard_comment_name', sel.value); } catch (e) {}
  });
  other.addEventListener('input', () => { try { localStorage.setItem('eea_dashboard_comment_name_other', other.value); } catch (e) {} });
})();

// ---- 1. constitution
{
  const c = card('What the outstanding set is made of', 'Every outstanding paper is in exactly one class. Only the two "has DOI" closed/unknown classes can be handed to a person with a subscription.', true);
  const rows = D.classes.map(k => ({name: k.label, n: k.n, id: k.id}));
  const labW = 420;
  // one series but per-row colour carries the class identity used in the era chart below
  const rowH = 26, barH = 18, padT = 6, padR = 70, W = 1180, H = padT + rows.length * rowH + 24;
  const svg = el('svg', {viewBox: `0 0 ${W} ${H}`}, c);
  const max = niceMax(Math.max(...rows.map(r => r.n)) * 1.02); const scale = v => (W - labW - padR) * v / max;
  for (const tv of ticks(max, 4)) { const x = labW + scale(tv); el('line', {x1: x, x2: x, y1: padT, y2: padT + rows.length * rowH, class: 'grid'}, svg); text(svg, x, H - 8, fmt(tv), '', 'middle'); }
  el('line', {x1: labW, x2: labW, y1: padT, y2: padT + rows.length * rowH, class: 'axis'}, svg);
  rows.forEach((r, i) => {
    const g = el('g', {class: 'row'}, svg); const y = padT + i * rowH + (rowH - barH) / 2;
    text(g, labW - 8, y + barH / 2, r.name, 'lab', 'end');
    el('path', {d: barPathH(labW, y, scale(r.n), barH, 4), fill: CLS_COLOR[r.id], class: 'bar'}, g);
    text(g, labW + scale(r.n) + 6, y + barH / 2, `${fmt(r.n)}  (${(100 * r.n / D.outstanding).toFixed(1)}%)`, 'val');
    hover(g, `<b>${r.name}</b><br>${fmt(r.n)} papers, ${(100 * r.n / D.outstanding).toFixed(1)}% of outstanding`);
  });
  tableView(c, ['Class', 'Papers', '% of outstanding'], rows.map(r => [r.name, r.n, (100 * r.n / D.outstanding).toFixed(1) + '%']));
}

// ---- 2. era x class
{
  const c = card('By era and class', 'Same classes as above, stacked by publication era. Colour follows the class, not the era.', true);
  const eras = D.era_order.filter(e => D.era_cls[e]);
  const series = D.classes.map(k => ({key: k.id, label: k.label.split(' (')[0], color: CLS_COLOR[k.id]}));
  vcols(c, eras, series, (e, k) => (D.era_cls[e] || {})[k] || 0, {maxBar: 60});
}

// ---- 3. year detail
{
  const c = card('By year, 1900 to now', 'Has DOI vs no DOI vs conference abstract, one column per year. Hover for values.', true);
  const years = D.years.map(r => r.year); const byY = Object.fromEntries(D.years.map(r => [r.year, r]));
  const series = [{key: 'doi', label: 'Has DOI', color: 'var(--s1)'}, {key: 'nodoi', label: 'No DOI', color: 'var(--s2)'}, {key: 'abstract', label: 'Conference abstract or conference-shaped', color: 'var(--s7)'}];
  vcols(c, years, series, (y, k) => byY[y][k] || 0, {labelEvery: 10, maxBar: 9});
}

// ---- 4. publishers
const pubLink = r => /^Other \(\d+ publishers\)$/.test(r.name) ? null : hubLink('publisher', r.name);
{
  const c = card(`Publisher of the ${fmt(D.with_doi)} papers with a DOI`, `Top ${D.publishers.length - 1} of ${D.publishers_total} publishers, plus the rest. Click a publisher to open its papers in the download hub (all of that publisher's queue rows, so the hub's count can be a little higher than the bar). ${fmt(D.prefix_resolved)} DOI papers have no stored publisher and are named from their DOI prefix; run scripts/backfill_queue_publishers.py --apply to make them filterable.`);
  hbars(c, D.publishers, [{key: 'closed', label: OA_LABEL.closed, color: OA_COLOR.closed}, {key: 'unknown', label: OA_LABEL.unknown, color: OA_COLOR.unknown}, {key: 'open', label: OA_LABEL.open, color: OA_COLOR.open}], {labW: 210, link: pubLink});
}

// ---- 5. recent
{
  const c = card(`Published 2024 or later, with a DOI (${fmt(D.recent_doi)})`, 'The embargo-and-subscription slice: newest papers, so the most likely to be behind a paywall a team member can pass. Click a publisher to open it in the download hub (all years: the hub filters one year at a time).');
  hbars(c, D.recent_publishers, [{key: 'closed', label: OA_LABEL.closed, color: OA_COLOR.closed}, {key: 'unknown', label: OA_LABEL.unknown, color: OA_COLOR.unknown}, {key: 'open', label: OA_LABEL.open, color: OA_COLOR.open}], {labW: 210, link: pubLink});
}

// ---- 6a. Simon vs everyone (thin card)
{
  const simon = D.team.find(t => t.person === 'Simon') || {papers: 0, credit: 0, total: 0};
  const rest = D.team.filter(t => t.person !== 'Simon');
  const sum = k => rest.reduce((a, t) => a + t[k], 0);
  const c = card('Simon vs everyone else', "Score = papers delivered + abstract-book credit. For banter only, it's late and I needed to pat myself on the head :)", true);
  const rows = [{name: 'Simon', papers: simon.papers, credit: simon.credit}, {name: `Everyone else (${rest.filter(t => t.total > 0).length} people)`, papers: sum('papers'), credit: sum('credit')}];
  hbars(c, rows, [{key: 'papers', label: 'Papers delivered', color: 'var(--s1)'}, {key: 'credit', label: 'Abstract-book credit', color: 'var(--s7)'}], {labW: 230, W: 1180});
}

// ---- 6b. team
{
  const rest = D.team.filter(t => t.person !== 'Simon');
  const c = card('Team contributions, against the coauthorship line', `Coauthorship needs ${fmt(D.coauthor_target)} points (provisional; to be re-set from the papers actually left to download). Papers = unique papers each person delivered into the library (drop-folder scan + download tracker). Abstract-book credit = ${Math.round(D.abstract_credit * 100)}% of the elasmo abstracts in each book they supplied, rounded up per book; the abstracts team (marked †) supply conference programmes, a different job. Everyone on the roster is listed, zeros included.`, true);
  const series = [{key: 'papers', label: 'Papers delivered', color: 'var(--s1)'}, {key: 'credit', label: 'Abstract-book credit', color: 'var(--s7)'}];
  const rows = rest.map(t => ({name: t.person + (t.abstract_team ? ' †' : ''), papers: t.papers, credit: t.credit, total: t.total}));
  const labW = 200, rowH = 15, grpH = 2 * rowH + 8, W = 1180, padT = 6, padR = 60;
  const H = padT + rows.length * grpH + 24;
  const svg = el('svg', {viewBox: `0 0 ${W} ${H}`}, c);
  const max = niceMax(Math.max(D.coauthor_target, ...rows.flatMap(r => series.map(s => r[s.key]))) * 1.05); const scale = v => (W - labW - padR) * v / max;
  for (const tv of ticks(max, 5)) { const x = labW + scale(tv); el('line', {x1: x, x2: x, y1: padT, y2: padT + rows.length * grpH, class: 'grid'}, svg); text(svg, x, H - 8, fmt(tv), '', 'middle'); }
  el('line', {x1: labW, x2: labW, y1: padT, y2: padT + rows.length * grpH, class: 'axis'}, svg);
  { const x = labW + scale(D.coauthor_target); const l = el('line', {x1: x, x2: x, y1: padT, y2: padT + rows.length * grpH}, svg); l.setAttribute('style', 'stroke: var(--ink); stroke-width: 1.5; stroke-dasharray: none; opacity: .55'); text(svg, x + 4, -6, `coauthorship: ${fmt(D.coauthor_target)} points`, 'lab'); }
  rows.forEach((r, i) => {
    const g = el('g', {class: 'row'}, svg); const y0 = padT + i * grpH + 4;
    text(g, labW - 8, y0 + (series.length * rowH) / 2, r.name, 'lab', 'end');
    series.forEach((s, si) => { const y = y0 + si * rowH; const w = scale(r[s.key]); if (w > 0) el('path', {d: barPathH(labW, y + 2, w, rowH - 4, 4), fill: s.color, class: 'bar'}, g); text(g, labW + w + 6, y + rowH / 2, fmt(r[s.key]), 'val'); });
    hover(g, `<b>${r.name}</b><br>` + series.map(s => `${s.label}: ${fmt(r[s.key])}`).join('<br>') + `<br>Score: ${fmt(r.total)}`);
  });
  legend(c, series.map(s => [s.label, s.color]));
  tableView(c, ['Person', 'Papers delivered', 'Abstract-book credit', 'Score'], D.team.map(t => [t.person + (t.abstract_team ? ' †' : ''), t.papers, t.credit, t.total]));
  const docs = D.team.flatMap(t => t.docs.map(d => [t.person, d.doc, d.elasmo, d.credit, d.basis]));
  if (docs.length) {
    const d = document.createElement('details'); d.innerHTML = '<summary>Abstract-book credit, per document (who supplied what)</summary>';
    const t = document.createElement('table');
    t.innerHTML = '<tr><th>Person</th><th>Document</th><th class="n">Elasmo abstracts</th><th class="n">Credit</th><th>Attribution basis</th></tr>' + docs.map(r => `<tr><td>${r[0]}</td><td>${r[1]}</td><td class="n">${fmt(r[2])}</td><td class="n">${fmt(r[3])}</td><td>${r[4]}</td></tr>`).join('');
    d.appendChild(t); c.appendChild(d);
  }
}

// ---- 7a. no-DOI: era x type
{
  const c = card(`The ${fmt(D.nodoi_pool)} no-DOI papers, by era and what they are`, 'Crossref was queried for every one of these (0 errors) and an independent OpenAlex probe on 100 post-2000 rows found 2 more DOIs. The rest are things that never had a DOI: meeting abstracts printed in journals, book chapters with the editor in the journal field, theses, grey reports, and regional print journals.', true);
  const eras = D.era_order.filter(e => D.nodoi_era_type[e]);
  const cols = ['var(--s1)', 'var(--s7)', 'var(--s2)', 'var(--s3)', 'var(--s4)', 'var(--s8)'];
  const series = D.nodoi_types.map((t, i) => ({key: t, label: t, color: cols[i]}));
  vcols(c, eras, series, (e, k) => (D.nodoi_era_type[e] || {})[k] || 0, {maxBar: 60});
}

// ---- 7b. no-DOI venues with routing flags
{
  const c = card(`Where the ${fmt(D.nodoi_pool)} no-DOI papers were published: top 45 venues, with a proposed route`, 'Country, route, and likely team members come from data/venue_routing.csv (Claude\'s inference, 2026-09-16, unverified: correct the CSV and rebuild). Click a venue to open its papers in the download hub. Routes: automated = free online, a script job; abstracts project = these are meeting abstracts; book = one book covers the rows; check DOI = the journal issues DOIs so the title match failed; ask member = needs a person or a library.', true);
  const rows = D.nodoi_venues;
  const labW = 300, rowH = 22, barH = 14, padT = 6, W = 1180, barW = 300, H = padT + rows.length * rowH + 24;
  const svg = el('svg', {viewBox: `0 0 ${W} ${H}`}, c);
  const max = niceMax(Math.max(...rows.map(r => r.n)) * 1.02); const scale = v => barW * v / max;
  const ROUTE_COLOR = {'automated': 'var(--s3)', 'abstracts project': 'var(--s7)', 'book': 'var(--s4)', 'check DOI': 'var(--s2)', 'ask member': 'var(--s1)', 'repair metadata': 'var(--s9)', '': 'var(--muted)'};
  for (const tv of ticks(max, 2)) { const x = labW + scale(tv); el('line', {x1: x, x2: x, y1: padT, y2: padT + rows.length * rowH, class: 'grid'}, svg); text(svg, x, H - 8, fmt(tv), '', 'middle'); }
  el('line', {x1: labW, x2: labW, y1: padT, y2: padT + rows.length * rowH, class: 'axis'}, svg);
  rows.forEach((r, i) => {
    const g = el('g', {class: 'row'}, svg); const y = padT + i * rowH + (rowH - barH) / 2;
    const name = r.name.length > 44 ? r.name.slice(0, 43) + '…' : r.name;
    const vhref = hubLink('journal', r.name || 'Unknown');  // the hub labels a blank venue "Unknown"
    text(svgLink(g, vhref, `Open the ${r.name || 'blank-venue'} papers in the download hub`), labW - 8, y + barH / 2, name, 'lab', 'end');
    el('path', {d: barPathH(labW, y, scale(r.n), barH, 4), fill: ROUTE_COLOR[r.route] || 'var(--muted)', class: 'bar'}, g);
    const flags = [r.country, r.route, r.members].filter(Boolean).join(' · ');
    text(g, labW + scale(r.n) + 6, y + barH / 2, `${fmt(r.n)}   ${flags}`, 'val');
    hover(g, `<b>${r.name}</b><br>${fmt(r.n)} papers${r.kind ? '<br>Kind: ' + r.kind : ''}${r.country ? '<br>Country: ' + r.country : ''}${r.route ? '<br>Route: ' + r.route : ''}${r.members ? '<br>Likely: ' + r.members : ''}${r.notes ? '<br><i>' + r.notes + '</i>' : ''}`);
  });
  legend(c, Object.entries(ROUTE_COLOR).filter(([k]) => k).map(([k, v]) => ['route: ' + k, v]));
  tableView(c, ['Venue', 'Papers', 'Country', 'Kind', 'Route', 'Likely members', 'Notes'], rows.map(r => [{text: r.name || '(blank)', href: hubLink('journal', r.name || 'Unknown')}, r.n, r.country, r.kind, r.route, r.members, r.notes]));
}

// ---- comments: fetch existing, render per-card + collated ----
function renderAllComments(comments) {
  const c = card('All comments', 'Every comment left on this dashboard, newest first, grouped by chart. Click a chart name to jump to it.', true, true);
  if (!comments.length) { c.insertAdjacentHTML('beforeend', '<p class="comment-unavailable">No comments yet.</p>'); return; }
  const byCard = {};
  comments.forEach(cm => { (byCard[cm.card] = byCard[cm.card] || []).push(cm); });
  const titleOf = id => { const r = cardRegistry.find(x => x.id === id); return r ? r.title : id; };
  const order = Object.keys(byCard).sort((a, b) => (byCard[b][0].at || '').localeCompare(byCard[a][0].at || ''));
  const wrap = document.createElement('div');
  order.forEach(id => {
    const grp = document.createElement('div'); grp.style.marginBottom = '10px';
    grp.innerHTML = `<a href="#card-${id}" style="font-weight:600; color:var(--ink); text-decoration:none;">${escapeHtml(titleOf(id))}</a>`;
    const list = document.createElement('div'); list.className = 'comment-list';
    byCard[id].forEach(cm => { const row = document.createElement('div'); row.className = 'c'; row.innerHTML = `<span class="meta">${escapeHtml(cm.by)} · ${fmtWhen(cm.at)}</span><br>${escapeHtml(cm.text)}`; list.appendChild(row); });
    grp.appendChild(list); wrap.appendChild(grp);
  });
  c.appendChild(wrap);
}
function renderAllCommentsUnavailable() {
  const c = card('All comments', 'Collated comments from every chart appear here once the comments endpoint is deployed.', true, true);
  c.insertAdjacentHTML('beforeend', '<p class="comment-unavailable">comments unavailable (endpoint not deployed yet)</p>');
}
(function() {
  fetch(COMMENTS_URL + '?action=getComments&page=remaining_papers_dashboard')
    .then(r => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
    .then(j => { if (!j || j.error || !Array.isArray(j.comments)) throw new Error((j && j.error) || 'unexpected response'); return j.comments; })
    .then(comments => {
      comments.sort((a, b) => (b.at || '').localeCompare(a.at || ''));
      const byCard = {};
      comments.forEach(cm => { (byCard[cm.card] = byCard[cm.card] || []).push(cm); });
      cardRegistry.forEach(r => { (byCard[r.id] || []).slice().reverse().forEach(cm => addCommentToList(r.id, cm)); });
      renderAllComments(comments);
    })
    .catch(() => { markCommentsUnavailable(); renderAllCommentsUnavailable(); });
})();

document.getElementById('foot').textContent = 'Built by scripts/build_remaining_papers_dashboard.py. Classes: a paper is a conference abstract if triaged as one; else "has DOI" split by Unpaywall OA status; else conference-shaped if its venue string names a conference, proceedings, or abstract book; else "damaged" if the journal field is blank or under 4 characters; else article-shaped.';
</script>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    a = ap.parse_args()
    data = build()
    html = HTML.replace("__DATA__", json.dumps(data).replace("</", "<\\/"))
    a.out.write_text(html)
    print(f"wrote {a.out}  outstanding={data['outstanding']:,}  with_doi={data['with_doi']:,}  no_doi={data['no_doi']:,}  abstracts={data['abstracts']:,}")
    for c in data["classes"]:
        print(f"  {c['n']:6,d}  {c['label']}")


if __name__ == "__main__":
    main()
