#!/usr/bin/env python3
"""Fill the `publisher` field of queue rows that have a DOI but no usable publisher.

docs/remaining_downloads.html filters on the STORED `publisher` value, so a row
whose publisher is blank or "Unknown publisher" cannot be reached by a
`?publisher=` deep link even when its DOI prefix names the publisher outright.
This writes the value that `generate_closed_access_html.resolve_publisher()`
already computes (house PREFIX map first, Crossref member record second): one
definition of "publisher", used by the closed-access pages, the remaining-papers
dashboard, and now the hub's filter.

Rows that already carry an informative publisher are never touched. Rows without
a DOI are never touched. Writes through lib.papers_data_io.mutate().

  python3 scripts/backfill_queue_publishers.py            # dry run
  python3 scripts/backfill_queue_publishers.py --apply
"""
import argparse
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_closed_access_html import _EMPTY_PUBLISHERS, resolve_publisher  # noqa: E402
from lib.papers_data_io import mutate  # noqa: E402


PLACEHOLDER = re.compile(r"^Other \(10\.\d{4,9}\)$")  # written when the prefix was unknown at the time


def wants_fill(p: dict) -> bool:
    pub = (p.get("publisher") or "").strip()
    empty = not pub or pub.lower() in _EMPTY_PUBLISHERS or bool(PLACEHOLDER.match(pub))
    return bool(str(p.get("doi") or "").strip()) and empty


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    import json
    papers = json.load(open(Path(__file__).resolve().parent.parent / "docs" / "papers_data.json"))
    todo = {id(p): resolve_publisher({**p, "publisher": ""}) for p in papers if wants_fill(p)}
    filled = Counter(v for v in todo.values() if v and v != "Unknown publisher")
    still = sum(1 for v in todo.values() if not v or v == "Unknown publisher")
    print(f"rows: {len(papers):,} | DOI rows with no usable publisher: {len(todo):,} | "
          f"resolvable: {sum(filled.values()):,} | still unknown: {still:,}")
    for name, n in filled.most_common(25):
        print(f"  {n:5d}  {name}")
    if not args.apply:
        print("dry run: nothing written (use --apply)")
        return
    n = 0
    with mutate() as live:
        for p in live:
            if wants_fill(p):
                new = resolve_publisher({**p, "publisher": ""})
                if new and new != "Unknown publisher" and not PLACEHOLDER.match(new):
                    p["publisher"] = new
                    n += 1
    print(f"applied: {n:,} rows given a publisher")


if __name__ == "__main__":
    main()
