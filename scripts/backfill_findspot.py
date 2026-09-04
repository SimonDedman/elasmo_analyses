#!/usr/bin/env python3
"""Backfill `findspot_raw` into docs/papers_data.json from Shark-References.

WHY
---
Our `journal` field comes from SR's `<span class="lit-findspot">`, but an early
pass truncated it and nothing has ever back-filled: sync Phase 2 diffs and only
enriches genuinely NEW papers, so existing rows keep whatever they were first
stored with. The full string is still live:

    stored : "In Programme Booklet of The"
    live   : "In Programme Booklet of The 15th Annual Scientific Conference of
              the European Elasmobranch Association, Berlin, 29.10.-30.10.2011"

Measured on the live B and C pages, 87% of conference-shaped rows (161/186)
recover a real conference name, usually with city, date, and the page within the
abstract book.

WHAT IT DOES NOT DO
-------------------
It never touches `journal` or `journal_clean`. For an ordinary journal the text
after the title IS volume and pages, and stripping that is correct behaviour;
overwriting `journal` with the raw findspot would undo `clean_journal_name()`
for 30,000 rows to fix 1,200. `findspot_raw` is purely additive, and consumers
opt in: Track B series identification, C1 DOI lookup, and damaged-field repair.

Also NOT a job for an LLM. The conference names are on a page we crawl monthly.
Asking a model to reconstruct "In Programme Booklet of The" into a conference
identity is asking it to guess at a fetchable fact, and a plausible wrong guess
is indistinguishable from a right one at review time.

Usage:
    python3 scripts/backfill_findspot.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sync_shark_references import (  # noqa: E402
    HEADERS, PAPERS_DATA, crawl_all_letters,
)

CONF_PAT = re.compile(
    r"abstract|programm|program\b|proceedings|congress|symposium|conference|"
    r"meeting|libro de|book of|workshop|booklet|encuentro|colloque|jornadas|"
    r"résumés|resumenes|resúmenes",
    re.I,
)
def locus_only(tail: str) -> bool:
    """True when the tail is purely a bibliographic locus — volume, issue,
    pages, article number — rather than a venue name.

    Tested by stripping the locus vocabulary and asking whether any real words
    survive. A regex alternation for this both over-matched and backtracked
    catastrophically: "Proceedings of the National Academy of Sciences ...,
    121(14), Article e2311597121" was counted as a conference row gaining a
    venue, which inflated the headline from 697 to 800.
    """
    t = tail.strip(" ,:;.")
    t = re.sub(r"\([^)]*\)", " ", t)
    t = re.sub(r"\bArticle\b|\bvol\.?\b|\bpp?\.\b|\bno\.\b", " ", t,
               flags=re.I)
    t = re.sub(r"[0-9]+", " ", t)
    t = re.sub(r"[^A-Za-zÀ-ÿ]+", " ", t)
    return not [w for w in t.split() if len(w) > 2]


def setup_log() -> logging.Logger:
    log = logging.getLogger("backfill_findspot")
    log.setLevel(logging.INFO)
    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(logging.Formatter("%(asctime)s  %(message)s",
                                     "%Y-%m-%d %H:%M:%S"))
    log.addHandler(h)
    fh = logging.FileHandler(
        Path(__file__).resolve().parent.parent
        / f"logs/backfill_findspot_{datetime.now():%Y%m%d}.log", encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s  %(message)s"))
    log.addHandler(fh)
    return log


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="crawl and report, write nothing")
    args = ap.parse_args()
    log = setup_log()

    session = requests.Session()
    session.headers.update(HEADERS)

    log.info("Crawling 26 A-Z pages for verbatim findspots...")
    sr = crawl_all_letters(session, log)
    live = {}
    for p in sr:
        lid = str(p.get("literature_id", "")).strip()
        fs = (p.get("findspot") or "").strip()
        if lid and fs:
            live[lid] = fs
    log.info(f"SR entries carrying a findspot: {len(live):,}")

    # Coverage is recorded, not assumed: a crawl that silently lost a letter
    # must not look like a complete pass.
    if len(live) < 20000:
        log.warning(f"only {len(live):,} findspots — a letter page may have "
                    f"failed; check the log above before trusting the result")

    data = json.loads(PAPERS_DATA.read_text())
    added = unchanged = conf_gain = missing = 0
    examples = []

    for row in data:
        lid = str(row.get("literature_id", "")).replace(".0", "").strip()
        fs = live.get(lid)
        if not fs:
            missing += 1
            continue
        if row.get("findspot_raw") == fs:
            unchanged += 1
            continue
        row["findspot_raw"] = fs
        added += 1

        stored = (row.get("journal") or "").strip()
        if stored and fs.startswith(stored) and len(fs) > len(stored):
            tail = fs[len(stored):]
            if CONF_PAT.search(stored) and not locus_only(tail):
                conf_gain += 1
                if len(examples) < 8:
                    examples.append((stored, fs))

    log.info("")
    log.info(f"rows in papers_data.json           : {len(data):,}")
    log.info(f"  findspot_raw written             : {added:,}")
    log.info(f"  already current                  : {unchanged:,}")
    log.info(f"  no SR findspot for this id       : {missing:,}")
    log.info(f"  conference rows GAINING a name   : {conf_gain:,}")
    for a, b in examples:
        log.info(f"     {a!r}")
        log.info(f"       -> {b[:120]!r}")

    if args.dry_run:
        log.info("\n--dry-run: nothing written")
        return
    if not added:
        log.info("\nnothing to write")
        return

    backup = PAPERS_DATA.with_suffix(
        f".backup-{datetime.now():%Y%m%d-%H%M%S}.json")
    shutil.copy2(PAPERS_DATA, backup)
    tmp = PAPERS_DATA.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    tmp.replace(PAPERS_DATA)
    log.info(f"\nwrote {PAPERS_DATA}  (backup: {backup.name})")


if __name__ == "__main__":
    main()
