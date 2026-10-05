#!/usr/bin/env python3
"""Mark todo-list rows for which someone already delivered the WRONG thing.

A team member who follows our link can come back with a review of the work,
the supplement, an authors' reply, or a sibling paper with a near-identical
title. The row stays on the list, and the next person repeats the mistake
unless the list says so. This writes a short `prior_false_dl` note onto the
queue row; docs/remaining_downloads.html and the download-helper pages show it
as an amber warning beside the title.

Add an entry to FLAGS after each ingest audit, then run:

    python3 scripts/flag_prior_false_downloads.py --apply
    python3 scripts/generate_closed_access_html.py

A flag disappears by itself when the row leaves the queue (the PDF was filed).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import papers_data_io  # noqa: E402

# literature_id -> what was wrongly delivered, and what is actually wanted.
FLAGS = {
    # 2026-10-04, Andrew's delivery
    "36246": "the supplementary materials were sent; we need the article (Fishery Bulletin 124: 71-84)",
    "35067": "the supplementary materials were sent; we need the article itself",
    "36067": "the supplementary figures were sent; we need the article itself",
    "35928": "the one-page Correction was sent; we need the article itself",
    "2467": "a Geological Magazine review of this monograph was sent; we need the monograph",
    "33276": "a Geological Magazine review (by A.S.W.) was sent; we need Karpinsky's paper",
    "2532": "a Geological Magazine review was sent; we need the monograph",
    "2102": "a Geological Magazine review was sent; we need Sauvage's work",
    "2873": "a Nature review was sent; we need the memoir",
    "9275": "a one-page Nature notice was sent; we need the 32-page memoir",
    "11840": "a one-page Nature notice was sent; we need the Fishery Board report",
    "15106": "a two-page German abstract (Referat) was sent; we need the American Naturalist paper, 50: 641-663",
    "500995": "a review of this book (Cowan 1997) was sent; we need the book",
    "500859": "a review of this book (Scholz 2002) was sent; we need the book",
    "500724": "a review of this book (Compagno 2005) was sent; we need the book",
    "7722": "Orlov's 2001 conference paper was sent; we need the 2003 paper with this exact title",
    # 2026-10-05, earlier deliveries re-examined
    "35455": "the authors' Reply (Bateman & Larsson) was sent twice; we need Greenfield's Comment",
    "4858": "Duffin & Delsate 1995 (Myriacanthus paradoxus, Belgium) was sent; we need Duffin 1994 (British Late Triassic)",
    "25424": "the 2017 Arabian Seas devil ray paper was sent; we need the Mobula japanica Mediterranean paper",
    "3118": "Delsate & Duffin 1993 (Sinemurien de Belgique) was sent; we need Duffin 1993 (Late Jurassic teeth, southern Germany)",
    "500660": "a 2026 Steinkern article on chimaera egg capsules was sent; we need Stehmann 2006",
    "28090": "a 2023 Schwaebische Heimat article was sent; we need the 2001 book",
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="Write. Default is a dry run.")
    args = ap.parse_args()

    if not args.apply:
        import json
        rows = json.load(open(papers_data_io.PAPERS_DATA)) if hasattr(papers_data_io, "PAPERS_DATA") else []
        on_queue = {str(r.get("literature_id")) for r in rows}
        print(f"{len(FLAGS)} flags defined; {len(set(FLAGS) & on_queue)} of those rows are on the queue")
        print("[dry run] re-run with --apply")
        return 0

    set_n = cleared = 0
    with papers_data_io.mutate() as data:
        for e in data:
            lid = str(e.get("literature_id"))
            if lid in FLAGS:
                if e.get("prior_false_dl") != FLAGS[lid]:
                    e["prior_false_dl"] = FLAGS[lid]
                set_n += 1
            elif "prior_false_dl" in e:
                del e["prior_false_dl"]
                cleared += 1
    print(f"flagged {set_n} rows (of {len(FLAGS)} defined); cleared {cleared} stale flags")
    return 0


if __name__ == "__main__":
    sys.exit(main())
