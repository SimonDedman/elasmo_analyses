#!/usr/bin/env python3
"""Act on a drop-folder audit (scripts/audit_drop_folder.py): the standard post-ingest practice.

Steps, each its own flag so a run can stop and resume between them:

  --stage    copy every bucket=ingest file whose record is an outstanding queue row to
             outputs/ingest_<date>_<person>/{papers,books}/<lid>.pdf with <lid>.identity.json
             (lid-named staging: filed by id, never re-matched). manifest.json records src->lid.
  --file     acquire_cascade.py --finalize-only on both staging dirs (books with --include-books;
             a book only reaches here when the record IS the monograph), keep-staging.
  --verify   after scripts/refresh_pdf_map_and_extract.sh: each lid must have left the queue and
             map to a library PDF with the source's page count whose text passes the identity test.
  --credit   verified files: scan-state entry (leaderboard credit), NAS source deleted, staging
             copy deleted. Unverified files are left in place and listed.
  --sort     every other bucket is moved into its named subfolder of the drop folder
             (audit_drop_folder.SUBFOLDERS), with a README.txt per subfolder.

--overrides CSV (filename,bucket[,literature_id]) re-buckets files after human review.
"""
from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import audit_drop_folder as adf  # noqa: E402
import ingest_pdfs as ing  # noqa: E402

PROJECT = ing.PROJECT
STATE_FILE = PROJECT / "outputs/.coauthor_scan_state.json"
OUTSTANDING = {"needs_library", "needs_pdf", "sr_sync_new", "acquired_bhl", "acquired_oa"}

README = {
    "_duplicate-already-filed": "Byte-identical to the PDF already in the library. Safe to delete.",
    "_already-filed-different-copy": "The record already has a PDF; this copy differs. Compare and keep the better one.",
    "_review-comment": "A review, comment, reply or discussion of the target paper, not the paper itself.",
    "_correction-erratum": "A correction, erratum or retraction notice, not the paper itself.",
    "_supplement-only": "Supplementary material only; the main paper is still needed.",
    "_wrong-paper": "The PDF is a different paper from the one named; the target is still needed.",
    "_whole-volume-needs-split": "A whole issue/volume/book; the article must be split out before filing.",
    "_not-in-database": "No database record matches; may be a new paper to add, or off-list.",
    "_unreadable-scan": "No text even after OCR, so identity could not be checked.",
    "_abstract-only": "An abstract or abstracting-journal entry; the full paper is still needed.",
    "_partial-pages-missing": "Some pages of the paper are missing; a complete copy is still needed.",
    "_ambiguous-several-records": "Two or more records pass the identity test (shared DOI or same title); pick the right one.",
    "_not-elasmo": "Not about elasmobranchs.",
}


def load_rows(audit: Path, overrides: Path | None) -> list[dict]:
    with open(audit, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if overrides and overrides.exists():
        with open(overrides, newline="", encoding="utf-8") as f:
            ov = {r["filename"]: r for r in csv.DictReader(f)}
        for r in rows:
            o = ov.get(r["filename"])
            if o:
                r["bucket"] = o["bucket"]
                r["reason"] = f"override: {o.get('note') or o['bucket']}"
                if o.get("literature_id"):
                    r["literature_id"] = o["literature_id"]
                r["source_override"] = o.get("source_override", "")
                if o.get("queue_status") is not None and o.get("queue_status") != "":
                    r["queue_status"] = o["queue_status"]
    return rows


def work_dir(person: str) -> Path:
    return PROJECT / f"outputs/ingest_{date.today():%Y-%m-%d}_{person}"


def stage(rows, folder: Path, person: str) -> None:
    wd = work_dir(person)
    manifest = []
    for r in rows:
        # records not on the queue but holding no PDF are filed too (recent SR adds)
        if r["bucket"] != "ingest" or (r["queue_status"] not in OUTSTANDING and r["lib_pdf"]):
            continue
        sub = "books" if int(r["pages"] or 0) > 200 else "papers"
        d = wd / sub
        d.mkdir(parents=True, exist_ok=True)
        lid = r["literature_id"]
        dst = d / f"{lid}.pdf"
        src = folder / r["filename"]
        # an OCR'd or split copy prepared during review replaces the raw file
        if not dst.exists():
            shutil.copy2(Path(r.get("source_override") or src), dst)
        (d / f"{lid}.identity.json").write_text(json.dumps({
            "literature_id": lid,
            "verified_by": f"Claude, {date.today()} {person} drop audit (page text read)",
            "evidence": f"title words {r['title_overlap']}, first-author surname found, "
                        f"match by {r['match']}, DOI in text: {r['doi_in_text']}; "
                        f"page one: {r['first_line'][:120]}",
            "source": str(src)}, indent=1))
        import pymupdf
        manifest.append({"person": person, "src": str(src), "lid": lid, "staged": str(dst),
                         "sha256": r["sha256"], "pages": pymupdf.open(str(dst)).page_count,
                         "prepared": r.get("source_override", "")})
    (wd / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print(f"staged {len(manifest)} files in {wd}")


def file_staged(person: str) -> None:
    wd = work_dir(person)
    shutil.copy2(PROJECT / "docs/papers_data.json", wd / "papers_data.before.json")
    for sub, extra in (("papers", []), ("books", ["--include-books"])):
        d = wd / sub
        if not d.exists() or not any(d.glob("*.pdf")):
            continue
        cmd = [sys.executable, "scripts/acquire_cascade.py", "--finalize-only", "--no-extract",
               "--no-enrich", "--keep-staging", "--staging-dir", str(d), *extra]
        print(" ".join(cmd), flush=True)
        with open(wd / f"finalize_{sub}.log", "w") as log:
            subprocess.run(cmd, cwd=PROJECT, stdout=log, stderr=subprocess.STDOUT, check=False)


def verify(person: str) -> list[dict]:
    wd = work_dir(person)
    manifest = json.loads((wd / "manifest.json").read_text())
    queue = {str(r["literature_id"]) for r in json.loads((PROJECT / "docs/papers_data.json").read_text())}
    before = {str(r["literature_id"]) for r in json.loads((wd / "papers_data.before.json").read_text())}
    pdfmap = {}
    with open(PROJECT / "outputs/pdf_id_map.csv", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            pdfmap.setdefault(str(r["literature_id"]), r["pdf"])
    adf._init()
    out = []
    for m in manifest:
        lid, problems = m["lid"], []
        if lid in queue:
            problems.append("still on queue")
        lib = pdfmap.get(lid)
        if not lib or not Path(lib).exists():
            problems.append("no library PDF in pdf_id_map")
        else:
            try:
                # Byte-identical to the staged file, whose identity the audit + review
                # established: done. Otherwise (ingest may file an OCR'd copy) re-test
                # with the audit's own rules: more pages for books, byline anywhere.
                if adf.sha256(Path(lib)) != adf.sha256(Path(m["staged"])):
                    tp = ing.ensure_text_extractable(Path(lib))
                    text, pages = adf.page_text(tp)
                    if pages > 30:
                        text, _ = adf.page_text(tp, 10)
                    if str(pages) != str(m["pages"]):
                        problems.append(f"library copy has {pages} pages, source {m['pages']}")
                    rec = adf.IDX["by_id"].get(lid, {})
                    t_ok, s_ok, *_ = adf.identity(text, rec, fuzzy=True)
                    if t_ok and not s_ok:
                        s_ok = adf.surname_present(adf.page_text(tp, 60)[0], rec.get("authors"), True)
                    if not (t_ok and s_ok):
                        problems.append("library copy differs from staged file and fails identity test")
            except Exception as e:  # noqa: BLE001
                problems.append(f"cannot open library copy: {e}")
        out.append({**m, "library_pdf": lib or "", "verified": not problems,
                    "problems": "; ".join(problems)})
    unexpected = sorted(before - queue - {m["lid"] for m in manifest})
    with open(wd / "verify.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=sorted({k for o in out for k in o}))
        w.writeheader()
        w.writerows(out)
    (wd / "verify_summary.json").write_text(json.dumps({
        "staged": len(out), "verified": sum(o["verified"] for o in out),
        "failed": [o["lid"] for o in out if not o["verified"]],
        "unexpected_queue_removals": unexpected}, indent=1))
    print(open(wd / "verify_summary.json").read())
    return out


def credit_and_clean(person: str) -> None:
    wd = work_dir(person)
    with open(wd / "verify.csv", newline="", encoding="utf-8") as f:
        ver = list(csv.DictReader(f))
    state = json.loads(STATE_FILE.read_text())
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    deleted = []
    for v in ver:
        if v["verified"] != "True":
            continue
        state["seen"][v["src"]] = {"person": person, "at": now, "literature_id": v["lid"],
                                   "note": f"filed {date.today()} via drop audit + lid-named staging; source deleted"}
        src, staged = Path(v["src"]), Path(v["staged"])
        if src.exists():
            src.unlink()
            deleted.append(str(src))
        for p in (staged, staged.with_suffix(".identity.json")):
            if p.exists():
                p.unlink()
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=1, ensure_ascii=False))
    tmp.replace(STATE_FILE)
    (wd / "sources_deleted.json").write_text(json.dumps({"deleted": deleted}, indent=1))
    print(f"credited + deleted {len(deleted)} sources")


def sort_problems(rows, folder: Path, person: str) -> None:
    moved = []
    state = json.loads(STATE_FILE.read_text())
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for r in rows:
        sub = adf.SUBFOLDERS.get(r["bucket"])
        if not sub:
            continue
        src = folder / r["filename"]
        if not src.exists():
            continue
        d = folder / sub
        d.mkdir(exist_ok=True)
        readme = d / "README.txt"
        if not readme.exists():
            readme.write_text(README.get(sub, "Record exists but is not on the todo list; review before filing.") + "\n")
        dst = d / r["filename"]
        shutil.move(str(src), str(dst))
        state["seen"][str(dst)] = {"person": person, "at": now, "held": f"{r['bucket']}: {r['reason']}",
                                   **({"candidate_id": r["literature_id"]} if r["literature_id"] else {})}
        moved.append({"filename": r["filename"], "subfolder": sub, "literature_id": r["literature_id"],
                      "reason": r["reason"]})
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=1, ensure_ascii=False))
    tmp.replace(STATE_FILE)
    wd = work_dir(person)
    wd.mkdir(parents=True, exist_ok=True)
    (wd / "sorted.json").write_text(json.dumps(moved, indent=1))
    print(f"moved {len(moved)} files into problem subfolders")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--audit", required=True, type=Path)
    ap.add_argument("--folder", required=True, type=Path)
    ap.add_argument("--person", required=True)
    ap.add_argument("--overrides", type=Path)
    for f in ("stage", "file", "verify", "credit", "sort"):
        ap.add_argument(f"--{f}", action="store_true")
    a = ap.parse_args()
    rows = load_rows(a.audit, a.overrides)
    if a.stage:
        stage(rows, a.folder, a.person)
    if a.file:
        file_staged(a.person)
    if a.verify:
        verify(a.person)
    if a.credit:
        credit_and_clean(a.person)
    if a.sort:
        sort_problems(rows, a.folder, a.person)
    return 0


if __name__ == "__main__":
    sys.exit(main())
