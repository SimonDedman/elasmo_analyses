#!/usr/bin/env python3
"""Reconcile the shared "I got this" marks against what is actually filed.

A mark is a claim, not a delivery. The queue is the truth: a paper leaves
docs/papers_data.json only when its PDF is filed in the library. So a mark whose
paper is STILL outstanding means one of:

  * downloaded but not yet uploaded to the NAS drop folder,
  * uploaded but not yet ingested (check the drop folder count below),
  * clicked and nothing happened.

Either way the row must not stay locked. The hub and the download helpers expire a
mark after STALE_DAYS and put the paper back on offer; this script is the report
side: who is holding what, for how long, and whether their drop folder has anything
in it. Run it before chasing anyone.

  python3 scripts/reconcile_download_marks.py
  python3 scripts/reconcile_download_marks.py --stale-days 14 --csv outputs/mark_reconcile.csv
"""
import argparse
import csv
import datetime as dt
import json
import sys
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from generate_closed_access_html import resolve_publisher  # noqa: E402

QUEUE = ROOT / "docs" / "papers_data.json"
DROPS = ROOT / "database" / "others_libraries"
SHEET = ("https://script.google.com/macros/s/"
         "AKfycbwCmkL89I8GGK3-IoCZh9x9XAVpvTshOysMlnWiRmqoXAtICFO16TkljEPlxTwXaufR/exec")
OUTSTANDING = {"needs_library", "needs_pdf", "sr_sync_new"}
# Drop-folder name per hub display name, where they differ.
FOLDER = {"David RG": "David_RG", "David S": "DavidS", "David Green": "DavidGreen",
          "Jürgen": "Jurgen", "Tobi-Dawne": "Tobi-Dawne"}


def key(p):
    return (str(p.get("doi") or "").strip() or f"lid:{p.get('literature_id')}").lower()


def fetch_marks():
    with urllib.request.urlopen(SHEET + "?action=getAll", timeout=60) as r:
        data = json.load(r).get("data", [])
    out = {}
    for x in data:
        k = str(x.get("doi") or "").strip().lower()
        if k:
            out[k] = x
    return out


def age_days(at):
    try:
        t = dt.datetime.fromisoformat(str(at).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if t.tzinfo is None:
        t = t.replace(tzinfo=dt.timezone.utc)
    return (dt.datetime.now(dt.timezone.utc) - t).days


def drop_counts():
    out = {}
    if DROPS.exists():
        for d in DROPS.iterdir():
            if d.is_dir():
                out[d.name] = sum(1 for f in d.rglob("*") if f.is_file() and f.suffix.lower() == ".pdf")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stale-days", type=int, default=14, help="same value as STALE_DAYS in the hub and helpers")
    ap.add_argument("--csv", type=Path, help="write the still-outstanding marks here")
    args = ap.parse_args()

    marks = fetch_marks()
    papers = json.load(open(QUEUE))
    out = [p for p in papers if p.get("last_status") in OUTSTANDING and p.get("triage") != "conference_abstract"]
    held = [(p, marks[key(p)]) for p in out if key(p) in marks]
    drops = drop_counts()

    print(f"marks in the shared record: {len(marks):,}")
    print(f"  delivered (paper has left the queue): {len(marks) - len(held):,} "
          f"({100 * (len(marks) - len(held)) / max(len(marks), 1):.0f}%)")
    print(f"  still outstanding (a claim with nothing filed): {len(held):,}")
    print(f"  of those, older than {args.stale_days} days, so already back on offer: "
          f"{sum(1 for _, m in held if (age_days(m.get('at')) or 999) >= args.stale_days):,}\n")

    by_person = defaultdict(list)
    for p, m in held:
        by_person[(m.get("by") or "Anon").strip() or "Anon"].append((p, m))
    print(f"{'person':14s} {'held':>5s} {'oldest':>7s} {'newest':>7s}  {'PDFs in drop folder':>19s}  top publishers")
    for who, rows in sorted(by_person.items(), key=lambda kv: -len(kv[1])):
        ages = [a for a in (age_days(m.get("at")) for _, m in rows) if a is not None]
        folder = FOLDER.get(who, who)
        n_drop = drops.get(folder)
        pubs = Counter(resolve_publisher(p) for p, _ in rows).most_common(3)
        print(f"{who:14s} {len(rows):5d} {max(ages) if ages else 0:6d}d {min(ages) if ages else 0:6d}d  "
              f"{('no folder' if n_drop is None else n_drop):>19}  "
              + ", ".join(f"{n} {k}" for k, n in pubs))
    print("\nA person with held papers and an empty drop folder either has PDFs they have not uploaded,")
    print("or clicked without downloading. Ask; the papers are already back on offer either way.")

    if args.csv:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        with open(args.csv, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["marked_by", "marked_at", "age_days", "literature_id", "doi", "year",
                        "publisher", "journal", "title"])
            for p, m in sorted(held, key=lambda t: (t[1].get("by") or "", str(t[1].get("at") or ""))):
                w.writerow([m.get("by"), m.get("at"), age_days(m.get("at")), p.get("literature_id"),
                            p.get("doi") or "", p.get("year"), resolve_publisher(p),
                            p.get("journal_clean") or p.get("journal") or "", p.get("title")])
        print(f"\nwrote {args.csv}")


if __name__ == "__main__":
    main()
