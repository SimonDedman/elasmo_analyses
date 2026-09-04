#!/usr/bin/env python3
"""Adjudicate duplicated literature_ids in docs/papers_data.json.

papers_data.json holds rows sharing a literature_id with conflicting metadata:
id 32101 carries the same title twice under two different DOIs, and several ids
carry the same title under two different years.

The first read of that was "one of each pair must be wrong". Checking rather
than assuming showed otherwise. For 32101 Crossref confirms BOTH DOIs: the
second is the CORRIGENDUM to the first, so they are two legitimate records that
collided on one id, not a corruption. Most other groups turned out to be the
same paper recorded twice with a spelling or year variant. Only one group
(3365, "Sharks and Rays of Australia") holds a genuinely wrong DOI, and it is
wrong for BOTH rows: the DOI points at a 2011 review of the book rather than
the 1994 or 2009 editions.

That is the reason this adjudicates instead of deduplicating. A wrong DOI is
actively harmful, since the download helper links straight to it, which is how
the 2026-04 off-by-one corruption sent people to the wrong paper for three
months. But so is deleting a corrigendum because it looked like a duplicate.

This does NOT guess. For every DOI in a duplicate group it fetches the Crossref
record and compares that record's title and year against the row's own stored
title and year, reusing the Phase 3b gate. A DOI is only endorsed when Crossref
agrees on both.

Two questions are answered separately, because they need different fixes:
  * WHICH DOI is right (or neither)?
  * Are the rows the SAME paper duplicated, or DIFFERENT papers that collided
    on one id? Same-paper means deduplicate; different-paper means one of them
    needs a new id.

Outputs outputs/duplicate_literature_ids_<date>.csv and prints a summary.
Applies nothing: adjudication is a review artefact, not an edit.

Usage:  python3 scripts/resolve_duplicate_literature_ids.py
"""
from __future__ import annotations

import csv
import json
import sys
import time
from collections import defaultdict
from datetime import date
from pathlib import Path

import requests

sys.path.insert(0, "scripts")
from sync_shark_references import _title_similarity  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PAPERS = ROOT / "docs/papers_data.json"
OUT = ROOT / f"outputs/duplicate_literature_ids_{date.today():%Y-%m-%d}.csv"

API = "https://api.crossref.org/works"
MAILTO = "simondedman@gmail.com"
DELAY = 0.5
TITLE_OK = 0.75
YEAR_TOL = 1


def norm_id(v) -> str:
    return str(v).replace(".0", "").strip()


def year_of(v):
    try:
        return int(float(v))
    except (ValueError, TypeError):
        return None


def crossref(session, doi: str):
    """-> ('found', rec) | ('absent', None) | ('error', detail).

    'absent' and 'error' are kept apart deliberately. A 429 or a timeout that
    got counted as "this DOI is not real" would condemn a perfectly good DOI.
    """
    try:
        r = session.get(f"{API}/{requests.utils.quote(doi, safe='')}", timeout=45)
    except Exception as e:  # noqa: BLE001
        return "error", type(e).__name__
    if r.status_code == 404:
        return "absent", None
    if not r.ok:
        return "error", f"HTTP {r.status_code}"
    try:
        m = r.json()["message"]
    except Exception:  # noqa: BLE001
        return "error", "unparseable"
    issued = (m.get("issued", {}).get("date-parts") or [[None]])[0]
    return "found", {
        "title": (m.get("title") or [""])[0],
        "journal": (m.get("container-title") or [""])[0],
        "year": issued[0] if issued else None,
    }


def main() -> None:
    papers = json.loads(PAPERS.read_text())
    groups = defaultdict(list)
    for p in papers:
        groups[norm_id(p.get("literature_id"))].append(p)
    # A blank id is not a duplicate group. Four rows carry no literature_id at
    # all (book chapters keyed "In Kimura et al." and a Murmansk report), and
    # lumping them together inflated the duplicate count and invented a
    # nonexistent "different titles collided on one id" case.
    blanks = groups.pop("", [])
    dups = {k: v for k, v in groups.items() if len(v) > 1}
    print(f"rows: {len(papers):,}   distinct ids: {len(groups):,}   "
          f"duplicated ids: {len(dups)}   blank ids: {len(blanks)}")
    if not dups and not blanks:
        return

    session = requests.Session()
    session.headers["User-Agent"] = f"elasmo-analyses/1.0 (mailto:{MAILTO})"

    rows = []
    n_queries = 0
    for lid, members in sorted(dups.items()):
        # Are these the same paper, or two papers sharing an id?
        titles = [(m.get("title") or "").strip() for m in members]
        sims = []
        for i in range(len(titles)):
            for j in range(i + 1, len(titles)):
                s = _title_similarity(titles[i], titles[j])
                sims.append(s if s is not None else 0.0)
            # only need pairwise
        same_paper = bool(sims) and min(sims) >= 0.9
        years = {year_of(m.get("year")) for m in members}
        group_kind = ("same_title_same_year" if same_paper and len(years) == 1
                      else "same_title_DIFFERENT_year" if same_paper
                      else "DIFFERENT_titles")

        for m in members:
            doi = (m.get("doi") or "").strip()
            verdict, cr_title, cr_year, cr_journal, detail = "", "", "", "", ""
            if doi:
                status, rec = crossref(session, doi)
                n_queries += 1
                time.sleep(DELAY)
                if status == "found":
                    cr_title = rec["title"]
                    cr_year = rec["year"] or ""
                    cr_journal = rec["journal"]
                    sim = _title_similarity(m.get("title") or "", rec["title"])
                    yr = year_of(m.get("year"))
                    title_ok = sim is not None and sim >= TITLE_OK
                    year_ok = (yr is None or rec["year"] is None
                               or abs(rec["year"] - yr) <= YEAR_TOL)
                    if title_ok and year_ok:
                        verdict = "DOI_CONFIRMED"
                    elif title_ok:
                        verdict = "title_ok_YEAR_MISMATCH"
                    else:
                        verdict = "DOI_WRONG_PAPER"
                    detail = f"title_sim={sim:.2f}" if sim is not None else ""
                elif status == "absent":
                    verdict = "DOI_NOT_IN_CROSSREF"
                else:
                    # Never let a fetch failure read as a bad DOI.
                    verdict = "COULD_NOT_CHECK"
                    detail = str(rec) if rec else ""
            else:
                verdict = "NO_DOI"

            rows.append({
                "literature_id": lid,
                "suggested_action": "",
                "group_kind": group_kind,
                "year": m.get("year", ""),
                "title": (m.get("title") or "")[:180],
                "journal": (m.get("journal_clean") or m.get("journal") or "")[:80],
                "doi": doi,
                "verdict": verdict,
                "crossref_title": cr_title[:180],
                "crossref_year": cr_year,
                "crossref_journal": cr_journal[:80],
                "detail": detail,
                "decision": "",
                "notes": "",
            })
        print(f"  {lid}  {group_kind}  -> "
              f"{[r['verdict'] for r in rows if r['literature_id'] == lid]}",
              flush=True)

    for m in blanks:
        rows.append({
            "literature_id": "(BLANK)",
            "suggested_action": "ASSIGN_ORPHAN_ID",
            "group_kind": "no_literature_id",
            "year": m.get("year", ""),
            "title": (m.get("title") or "")[:180],
            "journal": (m.get("journal_clean") or m.get("journal") or "")[:80],
            "doi": (m.get("doi") or "").strip(),
            "verdict": "NO_ID",
            "crossref_title": "", "crossref_year": "", "crossref_journal": "",
            "detail": "no id at all; cannot be joined, tracked or acquired",
            "decision": "", "notes": "",
        })

    # --- Suggested action per group ------------------------------------------
    # Suggestions only. Choosing between two DOIs for one paper is exactly the
    # call that went wrong in 2026-04, so nothing here is applied.
    per_id = defaultdict(list)
    for r in rows:
        per_id[r["literature_id"]].append(r)
    for lid, grp in per_id.items():
        if lid == "(BLANK)":
            continue
        dois = {r["doi"] for r in grp if r["doi"]}
        verdicts = {r["verdict"] for r in grp}
        kind = grp[0]["group_kind"]
        corrigendum = any(r["crossref_title"].lower().startswith(("corrigendum",
                          "erratum")) for r in grp)
        if corrigendum:
            action = "SEPARATE_RECORD (one is a corrigendum of the other)"
        elif verdicts == {"title_ok_YEAR_MISMATCH"} and len(dois) == 1:
            action = "DOI_WRONG (same DOI on both, Crossref year matches neither)"
        elif kind == "same_title_same_year":
            action = ("DEDUPE_KEEP_DOI" if any(r["doi"] for r in grp)
                      else "SAFE_DEDUPE")
        elif kind == "same_title_DIFFERENT_year":
            action = "YEAR_CONFLICT (editions? pick one, or split)"
        else:
            action = "CHECK_TITLES (variant spelling, or a real id collision)"
        for r in grp:
            r["suggested_action"] = action

    OUT.parent.mkdir(exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    tally = defaultdict(int)
    for r in rows:
        tally[r["verdict"]] += 1
    acts = defaultdict(set)
    for r in rows:
        acts[r["suggested_action"]].add(r["literature_id"])
    kinds = defaultdict(set)
    for r in rows:
        kinds[r["group_kind"]].add(r["literature_id"])

    print(f"\nCrossref queries: {n_queries}")
    print("\nverdicts:")
    for k, v in sorted(tally.items(), key=lambda x: -x[1]):
        print(f"  {v:4}  {k}")
    print("\ngroup kinds:")
    for k, v in sorted(kinds.items(), key=lambda x: -len(x[1])):
        print(f"  {len(v):4}  {k}")
    print("\nsuggested actions (by id):")
    for k, v in sorted(acts.items(), key=lambda x: -len(x[1])):
        print(f"  {len(v):4}  {k}")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
