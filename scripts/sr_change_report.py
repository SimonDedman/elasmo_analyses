"""Report Shark-References edits to records we already hold, and apply the ones we accept.

The monthly sync (sync_shark_references.py) crawls every A-Z listing page, which
shows each record's authors (with year), title, findspot, and DOI, but it used
the crawl only to find NEW literature_ids. Edits Shark-References makes to
records we already hold (a corrected DOI, a changed year, a split record, as
Juergen Pollerspoeck did for our 23 DOI reports on 2026-10-28) never reached us.

Since 2026-10-28 the sync saves each crawl as a snapshot
(outputs/sr_crawl_snapshots/), and this script compares the latest snapshot with
the base corpus parquet:

  report   one row per differing field (doi, year, authors, title, findspot) per record.
           A DOI difference is checked against Crossref: does each DOI resolve
           to a paper whose title agrees with the record (two-sided token
           overlap >= 0.8, year within 1)? That gives a recommendation, never an
           automatic change: Shark-References makes errors too (23 DOIs on
           2026-10-13). Differences already decided (data/sr_change_decisions.csv)
           or already rejected by our DOI audit (outputs/sr_doi_quarantine.csv)
           are counted, not re-served. Records on our side that are missing from
           the listing are reported only when the crawl fetched all 26 letters.
  apply    reads the 'decision' column of a report workbook (adopt_sr /
           keep_ours), dry run unless --apply. adopt_sr writes Shark-References'
           value to the base and enriched parquets, the master CSV rows carrying
           that literature_id, and docs/papers_data.json (via papers_data_io.mutate);
           when a record adopts any change and our journal/findspot is empty, the
           listing's findspot fills it. Every decision, keep_ours too, goes to the
           ledger so it is never asked again.

Usage:
  sr_change_report.py report [--crawl] [--snapshot FILE] [--no-crossref]
  sr_change_report.py apply REPORT.xlsx [--apply]
"""
import argparse
import csv
import gzip
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sync_shark_references as S  # noqa: E402

ROOT = S.PROJECT_ROOT
SNAP_DIR = ROOT / "outputs/sr_crawl_snapshots"
LEDGER = ROOT / "data/sr_change_decisions.csv"
LEDGER_COLS = ["literature_id", "field", "sr_value", "our_value", "decision", "decided", "note"]
FIELDS = ("doi", "year", "authors", "title", "findspot")
SR_ID_MAX = 500_000
# preprint servers: when both DOIs resolve to the paper, the published one wins
PREPRINT = re.compile(r"^10\.(?:2139/ssrn|1101/|21203/rs|22541/au|31219/osf|31222/osf|32942/|20944/preprints)")          # ids at or above are our own synthetic records, not Shark-References'


# --------------------------------------------------------------------- snapshot
def save_snapshot(papers, failed_letters, log=None):
    """Called by the sync right after its crawl. Returns the snapshot path."""
    SNAP_DIR.mkdir(parents=True, exist_ok=True)
    path = SNAP_DIR / f"sr_listing_{datetime.now():%Y%m%d_%H%M}.json.gz"
    meta = dict(crawled_at=datetime.now().isoformat(timespec="seconds"), n=len(papers),
                letters_failed=list(failed_letters), complete=not failed_letters)
    tmp = path.with_suffix(".part")
    with gzip.open(tmp, "wt", encoding="utf-8") as f:
        json.dump(dict(meta=meta, papers=papers), f, ensure_ascii=False)
    os.replace(tmp, path)
    if log:
        log.info(f"  Crawl snapshot: {path.name} ({len(papers)} records, "
                 f"{'complete' if meta['complete'] else 'letters failed: ' + ','.join(failed_letters)})")
    return path


def latest_snapshot():
    snaps = sorted(SNAP_DIR.glob("sr_listing_*.json.gz"))
    if not snaps:
        raise SystemExit(f"no snapshot in {SNAP_DIR}; run with --crawl")
    return snaps[-1]


def crawl_now():
    import logging
    import requests
    log = logging.getLogger("sr_change_report")
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    session = requests.Session()
    session.headers.update(S.HEADERS)
    papers = S.crawl_all_letters(session, log)
    return save_snapshot(papers, S.LAST_CRAWL_FAILED, log)


# --------------------------------------------------------------------- compare
def _norm_text(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


_GEN = re.compile(r"(?:\s|\.)+(?:\.?j\.?r\.?|\.?s\.?r\.?|(?:\.?i){2,3}\.?|\.?i\.?v\.?)(?=\s*(?:&|$))", re.I)


def _norm_authors(s):
    """Author string without its "(year)" tail and generation suffixes (Jr., III),
    which our import mangled into ".J.r." and ".I.I.I."; the year is compared on its own."""
    s = re.sub(r"\s*\(\d{4}[a-z]?\)\s*$", "", s or "")
    return _norm_text(_GEN.sub("", s))


def _surname(s):
    return _norm_text((s or "").split(",")[0])


def _year(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def _s(v):
    return "" if v is None or (isinstance(v, float) and pd.isna(v)) else str(v).strip()


def load_decided():
    decided = set()
    if LEDGER.exists():
        with LEDGER.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                decided.add((r["literature_id"], r["field"], r["sr_value"]))
    quarantined = set()
    q = ROOT / "outputs/sr_doi_quarantine.csv"
    if q.exists():
        with q.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                quarantined.add((S._normalise_lid(r["literature_id"]), S._normalise_doi(r["rejected_doi"])))
    return decided, quarantined


def compare(snapshot_path):
    with gzip.open(snapshot_path, "rt", encoding="utf-8") as f:
        snap = json.load(f)
    sr = {S._normalise_lid(p.get("literature_id")): p for p in snap["papers"]}
    base = pd.read_parquet(S.BASE_PARQUET, columns=["literature_id", "title", "authors", "year", "doi", "journal"])
    base["lid"] = base["literature_id"].map(S._normalise_lid)
    n_dup = int(base["lid"].duplicated().sum())
    base = base.drop_duplicates("lid")
    decided, quarantined = load_decided()
    # findspot (journal, volume, pages) lives in the master CSV; the parquets'
    # journal column is mostly empty
    csv.field_size_limit(sys.maxsize)
    master = sorted(S.MASTER_CSV_DIR.glob("shark_references_complete_*.csv"), key=lambda p: p.stat().st_mtime)[-1]
    with master.open(newline="", encoding="utf-8") as f:
        our_fs = {S._normalise_lid(r.get("literature_id")): (r.get("findspot") or "").strip()
                  for r in csv.DictReader(f) if S._normalise_lid(r.get("literature_id"))}
    rows, cov = [], dict(snapshot=snapshot_path.name, crawl_complete=snap["meta"]["complete"],
                         letters_failed=snap["meta"]["letters_failed"], sr_records=len(sr),
                         our_sr_records=0, compared=0, not_on_listing=0,
                         already_decided=0, audit_rejected=0, by_field={},
                         duplicate_ids_in_base=n_dup, id_mismatch=0)
    mismatches = []
    for _, b in base.iterrows():
        lid = b["lid"]
        if not lid.isdigit() or int(lid) >= SR_ID_MAX:
            continue
        cov["our_sr_records"] += 1
        p = sr.get(lid)
        if p is None:
            if snap["meta"]["complete"]:
                cov["not_on_listing"] += 1
                rows.append(dict(literature_id=lid, field="record", change="not on the SR listing",
                                 ours=f"{_s(b['authors'])} {_s(b['title'])}"[:300], sr_now=""))
            continue
        cov["compared"] += 1
        ours = dict(doi=S._normalise_doi(_s(b["doi"])), year=_year(b["year"]),
                    authors=_s(b["authors"]), title=_s(b["title"]), findspot=our_fs.get(lid, ""))
        sr_doi = S._normalise_doi(_s(p.get("doi")))
        # SR's listing sometimes yields page markup as a "DOI" (3999, 2026-10-28): drop
        # anything that is not a DOI at all; keep malformed-but-real ones so they still
        # equal our copy of the same string
        theirs = dict(doi=sr_doi if sr_doi.startswith("10.") else "", year=_year(p.get("year")),
                      authors=_s(p.get("authors")), title=_s(p.get("title")),
                      findspot=_s(p.get("findspot")))
        agree = S._title_agreement(ours["title"], theirs["title"])
        # a different paper altogether under this id: our id assignment is wrong (or
        # SR reused the id). Not a field edit, so it goes to the id-mismatch list.
        if agree is not None and agree < 0.5 and (
                _surname(ours["authors"]) != _surname(theirs["authors"]) or ours["year"] != theirs["year"]):
            cov["id_mismatch"] += 1
            mismatches.append(dict(literature_id=lid, our_title=ours["title"], our_authors=ours["authors"],
                                   our_year=ours["year"], our_doi=ours["doi"], sr_title=theirs["title"],
                                   sr_authors=theirs["authors"], sr_year=theirs["year"], sr_doi=theirs["doi"],
                                   sr_findspot=theirs["findspot"], title_agreement=round(agree, 2)))
            continue
        diffs = []
        if ours["doi"] != theirs["doi"]:
            kind = ("SR added a DOI" if not ours["doi"] else
                    "SR removed the DOI" if not theirs["doi"] else "SR changed the DOI")
            diffs.append(("doi", kind))
        if ours["year"] and theirs["year"] and ours["year"] != theirs["year"]:
            diffs.append(("year", "SR changed the year"))
        if _norm_authors(ours["authors"]) != _norm_authors(theirs["authors"]) and theirs["authors"]:
            diffs.append(("authors", "SR changed the authors"))
        if ours["findspot"] and theirs["findspot"] and _norm_text(ours["findspot"]) != _norm_text(theirs["findspot"]):
            diffs.append(("findspot", "SR changed the findspot"))
        if agree is not None and agree < S.TITLE_AGREE_MIN:
            diffs.append(("title", f"SR changed the title (agreement {agree:.2f})"))
        for field, kind in diffs:
            srv = "" if theirs[field] is None else str(theirs[field])
            if (lid, field, srv) in decided:
                cov["already_decided"] += 1
                continue
            if field == "doi" and (lid, theirs["doi"]) in quarantined:
                cov["audit_rejected"] += 1
                continue
            cov["by_field"][field] = cov["by_field"].get(field, 0) + 1
            rows.append(dict(literature_id=lid, field=field, change=kind,
                             ours="" if ours[field] is None else str(ours[field]), sr_now=srv,
                             title=ours["title"], year=ours["year"], sr_findspot=_s(p.get("findspot"))))
    cov["_mismatches"] = mismatches
    return rows, cov


def crossref_verdicts(rows):
    """For DOI rows: does each DOI resolve to this record's paper?"""
    import logging
    import requests
    dois = sorted({d for r in rows if r["field"] == "doi" for d in (r["ours"], r["sr_now"]) if d})
    if not dois:
        return
    session = requests.Session()
    found = S._crossref_lookup(session, dois, logging.getLogger("sr_change_report"))

    def verdict(doi, r):
        if not doi:
            return "none"
        m = found.get(doi)
        if not m:
            return "lookup failed (retry)" if doi in S.LAST_CROSSREF_UNCHECKED else "not in Crossref"
        return "matches" if S._same_paper(r["title"], r["year"], m["title"], m["year"]) else \
            f"different paper: {m['title'][:90]} ({m['year']})"
    for r in rows:
        if r["field"] != "doi":
            continue
        r["our_doi_check"], r["sr_doi_check"] = verdict(r["ours"], r), verdict(r["sr_now"], r)
        o, t = r["our_doi_check"], r["sr_doi_check"]
        both = o == t == "matches"
        r["recommendation"] = ("adopt_sr" if t == "matches" and o != "matches" else
                               "keep_ours" if o == "matches" and t != "matches" else
                               "adopt_sr (published version of our preprint)"
                               if both and PREPRINT.match(r["ours"]) and not PREPRINT.match(r["sr_now"]) else
                               "keep_ours (ours is the published version)"
                               if both and PREPRINT.match(r["sr_now"]) and not PREPRINT.match(r["ours"]) else
                               "either (both match)" if both else "review")


def write_report(rows, cov):
    from openpyxl import Workbook
    from openpyxl.styles import Font
    from openpyxl.worksheet.datavalidation import DataValidation
    out = ROOT / f"outputs/sr_change_report_{datetime.now():%Y%m%d}.xlsx"
    mism = cov.pop("_mismatches", [])
    mism_path = ROOT / f"outputs/sr_id_mismatches_{datetime.now():%Y%m%d}.csv"
    if mism:
        pd.DataFrame(mism).to_csv(mism_path, index=False)
    wb = Workbook()
    info = wb.active
    info.title = "Info"
    lines = [
        f"Shark-References changes to records we hold, from crawl snapshot {cov['snapshot']}",
        f"Compared {cov['compared']:,} of our {cov['our_sr_records']:,} Shark-References records; "
        f"crawl complete: {cov['crawl_complete']} (letters failed: {', '.join(cov['letters_failed']) or 'none'}).",
        f"Outstanding: {len(rows)} rows ({json.dumps(cov['by_field'])}, plus {cov['not_on_listing']} records not on the listing). "
        f"Not shown: {cov['already_decided']} already decided (data/sr_change_decisions.csv), "
        f"{cov['audit_rejected']} DOIs our audit already rejected (outputs/sr_doi_quarantine.csv).",
        f"Also not shown: {cov['id_mismatch']} ids where Shark-References holds a different paper altogether "
        f"(title agreement < 0.5 and a different first author or year): a re-keying job, not field edits"
        + (f"; listed in outputs/{mism_path.name}." if mism else "."),
        f"Our base parquet holds {cov['duplicate_ids_in_base']} duplicate literature_ids; each was compared once.",
        "",
        "What to do:",
        "1. Open the Changes tab. Each row is one field of one record where Shark-References now differs from us.",
        "2. For DOI rows, our_doi_check and sr_doi_check say whether each DOI resolves (Crossref) to a paper whose title and year agree with this record; 'recommendation' follows from them.",
        "3. In the 'decision' column type adopt_sr (take Shark-References' value) or keep_ours. Leave blank to decide later; blank rows are asked again next month.",
        "4. Save, then run: python3 scripts/sr_change_report.py apply <this file> (dry run), then again with --apply.",
        "Nothing changes until step 4. Every decision is kept in data/sr_change_decisions.csv and never asked again.",
    ]
    for i, t in enumerate(lines, 1):
        info.cell(row=i, column=1, value=t)
    info["A1"].font = Font(bold=True)
    info.column_dimensions["A"].width = 160
    ws = wb.create_sheet("Changes")
    cols = ["literature_id", "field", "change", "ours", "sr_now", "our_doi_check", "sr_doi_check",
            "recommendation", "decision", "title", "year", "sr_findspot"]
    ws.append(cols)
    for r in rows:
        ws.append([r.get(c, "") for c in cols])
    for c in ws[1]:
        c.font = Font(bold=True)
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    dv = DataValidation(type="list", formula1='"adopt_sr,keep_ours"', allow_blank=True)
    ws.add_data_validation(dv)
    if rows:
        dv.add(f"I2:I{len(rows) + 1}")
    for col, w in zip("ABCDEFGHIJKL", (12, 8, 26, 34, 34, 30, 30, 16, 12, 60, 6, 40)):
        ws.column_dimensions[col].width = w
    wb.save(out)
    (out.with_suffix(".coverage.json")).write_text(json.dumps(cov, indent=1))
    return out


# --------------------------------------------------------------------- apply
def _backup(path):
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # never a name the master-CSV glob (shark_references_complete_*.csv) can match
    dst = path.parent / f"pre_sr_change_apply_{stamp}__{path.name}.bak"
    dst.write_bytes(path.read_bytes())
    return dst


def _year_tail(authors, e):
    """Our author strings end "(YYYY)"; carry an adopted year into that tail unless
    the authors field was adopted too (2932 Ogilby, 1915 -> 1913)."""
    if "year" not in e or "authors" in e or not isinstance(authors, str):
        return authors
    return re.sub(r"\(\d{4}([a-z]?)\)\s*$", lambda m: f"({e['year']}{m.group(1)})", authors)


def apply(report, really):
    df = pd.read_excel(report, sheet_name="Changes", dtype=str).fillna("")
    df = df[df["decision"].isin(["adopt_sr", "keep_ours"])]
    adopt = df[df["decision"] == "adopt_sr"]
    print(f"{len(df)} decided rows: {len(adopt)} adopt_sr, {len(df) - len(adopt)} keep_ours")
    edits = {}                                   # lid -> {field: value}
    findspot = {}
    for _, r in adopt.iterrows():
        if r["field"] not in FIELDS:
            print(f"  SKIP {r['literature_id']} {r['field']}: only {FIELDS} can be adopted")
            continue
        edits.setdefault(r["literature_id"], {})[r["field"]] = r["sr_now"]
        if r.get("sr_findspot"):
            findspot[r["literature_id"]] = r["sr_findspot"]
    for lid, e in edits.items():
        print(f"  {lid}: {e}")
    if not really:
        print("dry run - nothing written (add --apply)")
        return
    # parquets
    for pq in (S.BASE_PARQUET, S.PARQUET):
        d = pd.read_parquet(pq)
        _backup(pq)
        lids = d["literature_id"].map(S._normalise_lid)
        n = 0
        for lid, e in edits.items():
            m = lids == lid
            if not m.any():
                continue
            for f, v in e.items():
                col = "journal" if f == "findspot" else f
                if col in d.columns:
                    d.loc[m, col] = (float(v) if f == "year" and v else v)
            if "authors" in d.columns:
                d.loc[m, "authors"] = d.loc[m, "authors"].map(lambda a: _year_tail(a, e))
            if "journal" in d.columns and lid in findspot:
                empty = m & (d["journal"].isna() | (d["journal"].astype(str).str.strip() == ""))
                d.loc[empty, "journal"] = findspot[lid]
            n += int(m.sum())
        tmp = pq.with_suffix(".part.parquet")
        d.to_parquet(tmp, index=False)
        os.replace(tmp, pq)
        print(f"  {pq.name}: {n} rows updated")
    # master CSV: rows carrying the literature_id
    master = sorted(S.MASTER_CSV_DIR.glob("shark_references_complete_*.csv"), key=lambda p: p.stat().st_mtime)[-1]
    _backup(master)
    csv.field_size_limit(sys.maxsize)
    with master.open(newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f)
        fields, data = rd.fieldnames, list(rd)
    n = 0
    for row in data:
        e = edits.get(S._normalise_lid(row.get("literature_id")))
        if not e:
            continue
        for f, v in e.items():
            if f in row:
                row[f] = v
        if "authors" in row:
            row["authors"] = _year_tail(row["authors"], e)
        lid = S._normalise_lid(row["literature_id"])
        if lid in findspot and not (row.get("findspot") or "").strip():
            row["findspot"] = findspot[lid]
        n += 1
    tmp = master.with_name(master.name + ".part")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(data)
    os.replace(tmp, master)
    print(f"  {master.name}: {n} rows updated ({len(data)} rows written)")
    # public queue
    from lib.papers_data_io import mutate
    n = 0
    with mutate() as live:
        for p in live:
            e = edits.get(S._normalise_lid(p.get("literature_id")))
            if not e:
                continue
            for f, v in e.items():
                for col in (("journal", "findspot_raw") if f == "findspot" else (f,)):
                    if col in p:
                        p[col] = int(v) if f == "year" and v else v
            if "authors" in p:
                p["authors"] = _year_tail(p["authors"], e)
            n += 1
    print(f"  papers_data.json: {n} rows updated")
    # ledger
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    new = not LEDGER.exists()
    with LEDGER.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=LEDGER_COLS)
        if new:
            w.writeheader()
        for _, r in df.iterrows():
            w.writerow(dict(literature_id=r["literature_id"], field=r["field"], sr_value=r["sr_now"],
                            our_value=r["ours"], decision=r["decision"],
                            decided=datetime.now().strftime("%Y-%m-%d"), note=f"from {Path(report).name}"))
    print(f"  ledger: {len(df)} decisions appended to {LEDGER.relative_to(ROOT)}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("report")
    r.add_argument("--crawl", action="store_true", help="crawl the listing now (26 requests, ~5 min)")
    r.add_argument("--snapshot", type=Path)
    r.add_argument("--no-crossref", action="store_true")
    a = sub.add_parser("apply")
    a.add_argument("report", type=Path)
    a.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    if args.cmd == "report":
        snap = crawl_now() if args.crawl else (args.snapshot or latest_snapshot())
        rows, cov = compare(snap)
        if not args.no_crossref:
            crossref_verdicts(rows)
        out = write_report(rows, cov)
        print(f"{len(rows)} outstanding rows {cov['by_field']}; not on listing {cov['not_on_listing']}; "
              f"already decided {cov['already_decided']}; audit-rejected {cov['audit_rejected']}; "
              f"id mismatches {cov['id_mismatch']}; compared {cov['compared']:,}/{cov['our_sr_records']:,}; "
              f"crawl complete {cov['crawl_complete']}")
        print(out)
    else:
        apply(args.report, args.apply)


if __name__ == "__main__":
    main()
