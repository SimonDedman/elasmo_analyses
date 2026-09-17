#!/usr/bin/env python3
"""Progress display for the 2026-09-17 download-push agent batch.

One line per track: state, artefacts landed n of x, %, rate over the last
10 minutes, ETA as absolute local time. Rules from ~/.claude/LONG-RUNNING-TASKS.md:
a track without a progress signal shows NO SIGNAL and its hard stop, never an
ETA; rate comes from a recent window, never total elapsed; DONE means the
track wrote its coverage.json (the one definition of finished, from the briefs).

    watch -n 60 -t -c 'cd "<project>" && python3 scripts/download_push_progress.py'
"""
from __future__ import annotations

import csv
import json
import re
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BATCH = ROOT / "outputs" / "download_push_2026-09-17"
SNAP = BATCH / "outstanding_snapshot.csv"
STATE = BATCH / ".progress_state.json"
WINDOW = 600  # s, rate window
HARD_STOP = 90 * 60  # each brief says stop at 90 min
TZ = lambda t: time.strftime("%H:%M %Z", time.localtime(t))  # noqa: E731


def launched(hhmm: str) -> float:
    return datetime.strptime("2026-09-17 " + hhmm, "%Y-%m-%d %H:%M").timestamp()


# venue lists per fetch track, as briefed (denominator = outstanding no-DOI rows in these venues)
A1 = ["Cybium", "Cahiers de Biologie Marine", "Annales", "Acta Adriatica", "Bulletin de l'Institut Royal des Sciences Naturelles de Belgique",
      "Belgian Geological Survey", "De Strandvlo", "Acta Geologica Polonica", "Afzettingen WTKG", "Het Zeepaard", "Palaeontos", "Cossmanniana",
      "Der Geschiebesammler", "Der Steinkern", "Neues Jahrbuch für Geologie und Paläontologie"]
A2_RE = re.compile(r"NOAA|Marine Fisheries Review|Fishery Bulletin|Technical Memorandum|Technical Report|FAO|ICES|IUCN|Shark News|CSIRO|NAFO|ICCAT|^Pratt$|^Fowler$", re.I)
A3 = ["Japanese Journal of Ichthyology", "Report of Japanese Society for Elasmobranch Studies", "Revista de Biología Marina y Oceanografía",
      "Revista de Biología Tropical", "Hidrobiológica", "Arquivos de Ciências do Mar", "Indian Journal of Fisheries", "Indian Journal of Geo Marine Sciences",
      "Vertebrata Palasiatica", "New Mexico Museum of Natural History and Science", "California Fish and Game", "Florida Scientist",
      "Journal of the Elisha Mitchell Scientific Society", "Bulletin of Marine Science"]
D_RE = re.compile(r"thesis|dissertation|\bphd\b|\bmsc\b|tesis|tesi\b|diplomarbeit|mémoire|memoria|^in\b|\(eds?\.?\)|^[A-Z][a-z]+$|^[A-Z]\.\s?[A-Z]?\.?\s?[A-Z][a-z]+", re.I)


def load_rows():
    with open(SNAP, newline="") as fh:
        return list(csv.DictReader(fh))


def denominators(rows):
    nodoi = [r for r in rows if r["cls"] in ("nodoi_article", "nodoi_damaged")]
    v = lambda r: (r["journal_clean"] or r["journal"]).strip()  # noqa: E731
    from collections import Counter

    per_venue = Counter(v(r) for r in nodoi)
    return {
        "A1_europe": sum(1 for r in nodoi if v(r) in A1),
        "A2_reports": sum(1 for r in rows if r["cls"] in ("nodoi_article", "nodoi_damaged", "conf_shaped") and A2_RE.search(v(r) + " " + r["findspot_raw"])),
        "A3_journals": sum(1 for r in nodoi if v(r) in A3),
        "B_issn_dois": sum(n for n in per_venue.values() if n >= 3),
        "C_abstract_triage": len(rows),
        "D_miscellania": sum(1 for r in nodoi if D_RE.search(v(r) + " " + r["findspot_raw"])),
        "E_doi_probe": 200 + 150 + 40 + 20,  # sampled queries per brief
        "F1_journal_matrix": len({v(r) for r in rows if r["cls"] in ("doi_closed", "doi_unknown")}),
        "F2_institution_access": 11 * 20,
        "G_comments": 1,
    }


# what counts as "landed" for each track
SIGNAL = {
    "A1_europe": lambda d: len(list((d / "pdfs").rglob("*.pdf"))),
    "A2_reports": lambda d: len(list((d / "pdfs").rglob("*.pdf"))) + _manifest_rows(d, "covered_by_volume"),
    "A3_journals": lambda d: len(list((d / "pdfs").rglob("*.pdf"))) + _manifest_rows(d, "covered_by_volume"),
    "B_issn_dois": lambda d: len(list((d / ".cache").glob("*"))) if (d / ".cache").exists() else _files(d),
    "C_abstract_triage": lambda d: _csv_rows(d / "flagged_rows.csv"),
    "D_miscellania": lambda d: sum(_csv_rows(d / f) for f in ("books.csv", "chapters.csv", "theses.csv", "grey.csv")) or _files(d),
    "E_doi_probe": lambda d: sum(_csv_rows(d / f) for f in ("datacite.csv", "doi_validity_sample.csv", "oa_unknown_sample.csv", "rejected_sample.csv")) or _files(d),
    "F1_journal_matrix": lambda d: _csv_rows(d / "journals.csv") or len(list((d / ".cache").glob("*"))) if (d / ".cache").exists() else _csv_rows(d / "journals.csv"),
    "F2_institution_access": lambda d: _csv_rows(d / "trial_results.csv") or (len(list((d / ".cache").rglob("*"))) if (d / ".cache").exists() else 0),
    "G_comments": lambda d: 1 if (d / "REPORT.md").exists() else 0,
}
LAUNCH = {"A1_europe": "00:03", "A2_reports": "00:04", "A3_journals": "00:05", "B_issn_dois": "00:06", "C_abstract_triage": "00:08",
          "D_miscellania": "00:09", "E_doi_probe": "00:10", "F1_journal_matrix": "00:11", "F2_institution_access": "00:12", "G_comments": "00:12"}


def _files(d):
    return sum(1 for p in d.rglob("*") if p.is_file() and not p.name.startswith("."))


def _csv_rows(p):
    if not p.exists():
        return 0
    with open(p, newline="") as fh:
        return max(0, sum(1 for _ in fh) - 1)


def _manifest_rows(d, status):
    p = d / "manifest.csv"
    if not p.exists():
        return 0
    with open(p, newline="") as fh:
        return sum(1 for r in csv.DictReader(fh) if r.get("status") == status)


def main():
    now = time.time()
    rows = load_rows()
    den = denominators(rows)
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    print(f"download push 2026-09-17   now {TZ(now)}   (DONE = coverage.json + REPORT.md written; hard stop = launch + 90 min)")
    print(f"{'track':24s} {'state':10s} {'landed':>8s} {'of':>6s} {'%':>6s} {'rate/min':>9s}  eta")
    for name in LAUNCH:
        d = BATCH / name
        n = SIGNAL[name](d) if d.exists() else 0
        x = den[name]
        hist = state.get(name, [])
        hist.append([now, n])
        hist = [h for h in hist if now - h[0] <= 3600][-120:]
        state[name] = hist
        done = ((d / "coverage.json").exists() and (d / "REPORT.md").exists()) or name == "G_comments"
        recent = [h for h in hist if now - h[0] <= WINDOW]
        rate = (n - recent[0][1]) / max(1e-9, (now - recent[0][0])) * 60 if len(recent) >= 2 and now - recent[0][0] >= 60 else None
        stop = launched(LAUNCH[name]) + HARD_STOP
        pct = f"{100 * n / x:5.1f}%" if x else "     "
        if done:
            st, eta = "DONE", ""
        elif n == 0:
            st, eta = "NO SIGNAL", f"hard stop {TZ(stop)}"
        elif rate is not None and rate <= 0:
            st, eta = "STALLED?", f"no growth {int((now - max(h[0] for h in hist if h[1] < n) if any(h[1] < n for h in hist) else recent[0][0]) // 60)} min; hard stop {TZ(stop)}"
        elif rate:
            remaining = max(0, x - n) / rate * 60
            eta_t = min(now + remaining, stop)
            st, eta = "RUNNING", f"{int((eta_t - now) // 60)} min ({TZ(eta_t)}){' capped by hard stop' if now + remaining > stop else ''}"
        else:
            st, eta = "RUNNING", f"rate needs a 1-min window; hard stop {TZ(stop)}"
        print(f"{name:24s} {st:10s} {n:8,d} {x:6,d} {pct:>6s} {('%.1f' % rate) if rate is not None else '':>9s}  {eta}")
    STATE.write_text(json.dumps(state))
    print("\nA-track 'landed' = verified PDFs staged (+ rows covered by a whole volume); B = Crossref queries cached; C = rows flagged; D/E = CSV rows written;\nF1 = journals listed; F2 = ISSN×institution trials. Denominators are rows in scope per brief; agents may finish under x by design.")


if __name__ == "__main__":
    main()
