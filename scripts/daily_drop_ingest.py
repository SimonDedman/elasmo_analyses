#!/usr/bin/env python3
"""Daily: ingest every drop folder completely, then publish the todo list.

Agreed 2026-10-12 (Simon): "scan folders for ingests daily, ingest completely, update,
merge, push". One run, per drop folder that holds PDFs:

  1. audit_drop_folder.py --recursive      (identity test on every PDF, read-only)
  2. apply_drop_audit.py --stage --file     (lid-named staging, acquire_cascade finalize)
  3. backfill_corpus_rows + build_pdf_id_map (so filings are visible), map diff kept in
     outputs/pdf_id_map_changes_pending.csv for the extraction in step 7
  4. apply_drop_audit.py --verify --credit --sort --ledger --tidy
     (verified sources deleted + credited; problems sorted into `_*` subfolders with a
     traced cause; filed-but-unverified files go to `_verify-failed`, never deleted)
then once:
  5. reconcile_queue_with_library.py --apply, flag_prior_false_downloads.py --apply,
     generate_closed_access_html.py, the dashboard into docs/acquisition/
  6. publish_todo_list.sh                   (commit the list, update main, push)
  7. refresh_pdf_map_and_extract.sh         (evidence extraction + RAG sync)

Drop folders: database/others_libraries/<Person>/ and, when the NAS is mounted,
smb://nas.local/homes/MarineScience/<Person>/. An unmounted NAS is reported, never
silently skipped. Conference abstract books, programme folders and `_*` problem
subfolders are not deliveries and are left alone.

Writes outputs/daily_ingest_<date>.json (per-folder counts, failures) and appends to
logs/daily_drop_ingest.log. Exit 1 if any step failed.

    python3 scripts/daily_drop_ingest.py            # the cron job
    python3 scripts/daily_drop_ingest.py --dry-run  # list the folders and PDFs only
    python3 scripts/daily_drop_ingest.py --no-publish --no-extract
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import audit_drop_folder as adf  # noqa: E402
import scan_coauthor_libraries as scan  # noqa: E402

PROJECT = Path("/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel")
LOCAL = PROJECT / "database/others_libraries"
NAS = Path("/run/user/1000/gvfs/smb-share:server=nas.local,share=homes/MarineScience")
PY = sys.executable
TODAY = f"{date.today():%Y-%m-%d}"
SUMMARY = PROJECT / f"outputs/daily_ingest_{TODAY}.json"
PENDING = PROJECT / "outputs/pdf_id_map_changes_pending.csv"
# Inboxes for the conference-abstracts pipeline (abstract and programme books from Brit,
# Cat and SOMEPEC), not paper deliveries. The per-file book test misses short programmes.
CONFERENCE_INBOXES = {"Brit", "Cat", "SOMEPEC"}


def log(msg: str) -> None:
    print(f"{datetime.now():%H:%M:%S} {msg}", flush=True)


def run(cmd: list[str], failures: list, what: str) -> bool:
    log("$ " + " ".join(str(c) for c in cmd))
    r = subprocess.run([str(c) for c in cmd], cwd=PROJECT)
    if r.returncode != 0:
        failures.append(f"{what}: exit {r.returncode}")
        log(f"FAILED {what} (exit {r.returncode})")
    return r.returncode == 0


def folders() -> tuple[list[tuple[str, str, Path]], list[str]]:
    out, notes = [], []
    for d in sorted(LOCAL.iterdir()):
        if (d.is_dir() and d.name not in scan.SKIP_DIRS | CONFERENCE_INBOXES
                and not d.name.startswith((".", "_"))):
            out.append((d.name, "lib", d))
    if NAS.is_dir():
        for d in sorted(NAS.iterdir()):
            if d.is_dir() and not d.name.startswith(("#", ".", "_")):
                out.append((d.name, "nas", d))
    else:
        notes.append(f"NAS NOT MOUNTED ({NAS}): its drop folders were NOT scanned")
    return out, notes


def map_rebuild(failures: list) -> None:
    run([PY, "scripts/backfill_corpus_rows.py", "--apply"], failures, "backfill corpus rows")
    if run([PY, "scripts/build_pdf_id_map.py"], failures, "build pdf id map"):
        changes = PROJECT / "outputs/pdf_id_map_changes.csv"
        if changes.exists():
            with open(changes, newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            if rows:
                new = not PENDING.exists()
                with open(PENDING, "a", newline="", encoding="utf-8") as f:
                    w = csv.DictWriter(f, fieldnames=list(rows[0]))
                    if new:
                        w.writeheader()
                    w.writerows(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-publish", action="store_true")
    ap.add_argument("--no-extract", action="store_true")
    a = ap.parse_args()

    found, notes = folders()
    for n in notes:
        log(n)
    summary = {"date": TODAY, "started": datetime.now().isoformat(timespec="seconds"),
               "notes": notes, "folders": [], "failures": []}
    failures = summary["failures"]
    todo = []
    for person, src, d in found:
        try:
            pdfs = adf.list_pdfs(d, recursive=True)
        except OSError as e:
            notes.append(f"{src}/{person}: cannot list ({e})")
            continue
        if pdfs:
            todo.append((person, src, d, len(pdfs)))
            log(f"{src}/{person}: {len(pdfs)} PDFs to ingest")
    if a.dry_run or not todo:
        log("nothing to ingest" if not todo else "dry run: stopping")
        if not a.dry_run:
            summary["finished"] = datetime.now().isoformat(timespec="seconds")
            SUMMARY.write_text(json.dumps(summary, indent=1))
        return 0

    for person, src, d, n in todo:
        audit_dir = PROJECT / f"outputs/dropaudit_{person}_{src}_{TODAY}"
        entry = {"person": person, "source": src, "folder": str(d), "pdfs": n, "audit": str(audit_dir)}
        summary["folders"].append(entry)
        if not run([PY, "scripts/audit_drop_folder.py", "--folder", d, "--person", person,
                    "--recursive", "--out", audit_dir], failures, f"audit {src}/{person}"):
            continue
        base = [PY, "scripts/apply_drop_audit.py", "--audit", audit_dir / "audit.csv",
                "--folder", d, "--person", person, "--tag", src]
        run(base + ["--stage", "--file"], failures, f"stage+file {src}/{person}")
        map_rebuild(failures)
        run(base + ["--verify", "--credit", "--sort", "--ledger", "--tidy"], failures,
            f"verify+credit+sort {src}/{person}")
        wd = PROJECT / f"outputs/ingest_{TODAY}_{person}_{src}"
        vs = wd / "verify_summary.json"
        if vs.exists():
            v = json.loads(vs.read_text())
            entry.update(staged=v["staged"], verified=v["verified"], verify_failed=v["failed"],
                         unexpected_queue_removals=v["unexpected_queue_removals"])
        cov = audit_dir / "coverage.json"
        if cov.exists():
            entry["by_bucket"] = json.loads(cov.read_text())["by_bucket"]

    run([PY, "scripts/reconcile_queue_with_library.py", "--apply"], failures, "reconcile queue")
    run([PY, "scripts/flag_prior_false_downloads.py", "--apply"], failures, "hub flags")
    run([PY, "scripts/generate_closed_access_html.py"], failures, "helper pages")
    run([PY, "scripts/build_remaining_papers_dashboard.py", "--out",
         "docs/acquisition/remaining_papers.html"], failures, "dashboard")
    filed = sum(f.get("verified", 0) for f in summary["folders"])
    if not a.no_publish:
        who = ", ".join(sorted({f["person"] for f in summary["folders"]}))
        run(["sh", "scripts/publish_todo_list.sh",
             f"data(queue): {filed} papers filed from drop folders ({who}), {TODAY}"],
            failures, "publish to main")
    summary["filed"] = filed
    summary["finished"] = datetime.now().isoformat(timespec="seconds")
    SUMMARY.write_text(json.dumps(summary, indent=1))
    if not a.no_extract:
        # hours only after a large delivery; the cron wrapper caps its memory
        run(["sh", "scripts/refresh_pdf_map_and_extract.sh"], failures, "extraction + RAG sync")
        SUMMARY.write_text(json.dumps(summary, indent=1))
    log(f"filed {filed}; failures: {len(failures)}")
    for f in failures:
        log(f"  FAILURE {f}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
