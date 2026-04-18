#!/usr/bin/env python3
"""CLI wrapper for the ingestion-hook dedup check.

Use from the shell (or from ingest_pdfs.py via subprocess) after a new
PDF has been copied into the corpus:

    python3 scripts/check_new_pdf.py "/path/to/new.pdf"
    python3 scripts/check_new_pdf.py --no-doi file1.pdf file2.pdf

Outputs: one JSON per flagged pair on stdout. Also appended to
outputs/on_ingest_flags.jsonl.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR.parent))

from scripts.dedup.ingest_hook import check_batch  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+", help="PDF paths to check")
    ap.add_argument("--no-doi", action="store_true")
    ap.add_argument("--no-ocr", action="store_true")
    ap.add_argument("--min-confidence", type=float, default=0.55)
    args = ap.parse_args()

    res = check_batch(
        [Path(p) for p in args.paths],
        ocr_if_needed=not args.no_ocr,
        do_doi=not args.no_doi,
        min_confidence=args.min_confidence,
    )
    flagged = 0
    for path, flags in res.items():
        if not flags:
            continue
        flagged += len(flags)
        for f in flags:
            print(json.dumps(f))
    sys.stderr.write(f"Checked {len(res)} file(s); {flagged} flag(s) written.\n")


if __name__ == "__main__":
    main()
