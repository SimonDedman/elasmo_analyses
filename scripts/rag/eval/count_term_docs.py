#!/usr/bin/env python3
"""
List the papers whose body text contains a term verbatim, for writing
exact_term questions (their relevant_ids).

    python3 scripts/rag/eval/count_term_docs.py "Squalus bassi" "fyke net" \
        [--index-dir outputs/rag] [--json out.json]

Matching: case-sensitive, whitespace-normalised (pdftotext line breaks inside
a phrase still match), word-bounded, over outputs/validation/.fable_texts/.
Reports the total in the cache and the subset present in the index's
chunks_meta.jsonl. Takes about 90 s for a batch of terms (one pass).
"""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
TEXTS = PROJECT_ROOT / "outputs" / "validation" / ".fable_texts"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("terms", nargs="+")
    ap.add_argument("--index-dir", default=str(PROJECT_ROOT / "outputs" / "rag"))
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    indexed = set()
    with open(Path(args.index_dir) / "chunks_meta.jsonl", encoding="utf-8") as f:
        for line in f:
            lid = str(json.loads(line)["literature_id"])
            indexed.add(lid[:-2] if lid.endswith(".0") else lid)
    pats = {t: re.compile(r"\b" + re.escape(t) + r"\b") for t in args.terms}
    hits = {t: [] for t in args.terms}
    for fn in os.listdir(TEXTS):
        if not fn.endswith(".txt"):
            continue
        txt = re.sub(r"\s+", " ", (TEXTS / fn).read_text(errors="ignore"))
        for t, p in pats.items():
            if t in txt and p.search(txt):
                hits[t].append(fn[:-4])
    out = {}
    for t, ids in hits.items():
        ids = sorted(ids, key=lambda s: int(s) if s.isdigit() else 0)
        out[t] = {"total": len(ids), "in_index": [i for i in ids if i in indexed]}
        print(f"{len(ids):6d} {len(out[t]['in_index']):6d}  {t}  {out[t]['in_index'][:10]}")
    if args.json:
        Path(args.json).write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
