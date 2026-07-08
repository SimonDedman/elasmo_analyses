"""Corpus-wide Fable extraction — STAGE 1: pre-pass (local, no Fable).

Resolves every literature_id to its PDF, extracts text via pdftotext, and builds
the worklist the Fable burn (stage 2, fable_corpus_burn.mjs) consumes. Skips any
paper whose PDF SHA-1 already has a cache file, so re-running only picks up
newly-resolvable / un-done papers (resume across nights).

Reuses the resolution + text-extraction helpers from the validated pipeline
(fable_extract.py / extract_schema_columns.py) — no reimplementation.

Outputs (all under outputs/validation/, git-ignored):
  .fable_texts/<lit_id>.txt        materialised paper text (<=120k chars)
  fable_corpus_worklist.json       [{lit_id, text_path, sha}, ...] still to do
  fable_corpus_columns.json        [{name, description}, ...] for the 166 cols
Cache dir checked/created: .fable_corpus_cache/  (stage 2 writes <sha>.txt here)

Usage:
  python3 scripts/validation/fable_corpus_prepass.py [--limit N] [--quiet]
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/validation"
TEXTS = OUT / ".fable_texts"
CORPUS_CACHE = OUT / ".fable_corpus_cache"
WORKLIST = OUT / "fable_corpus_worklist.json"
COLUMNS_JSON = OUT / "fable_corpus_columns.json"
MAX_CHARS = 120_000  # matches the validated fable_extract prompt window

sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "validation"))


def _resolve_pdf(lit_id, meta, pdf_index, helpers):
    """literature_id -> best PDF Path, or None. Mirrors fable_extract._pdf_text
    resolution (surname + year index, title disambiguation) but stops at the
    path so the caller can SHA-gate before the expensive pdftotext."""
    _first_surname, _pick_best_pdf = helpers
    if lit_id not in meta.index:
        return None
    row = meta.loc[lit_id]
    authors = row.get("authors")
    year_raw = row.get("year")
    title = row.get("title") or ""
    if not authors or year_raw is None or (isinstance(year_raw, float) and pd.isna(year_raw)):
        return None
    surname = _first_surname(authors)
    if not surname:
        return None
    candidates = pdf_index.get((surname, int(year_raw)), [])
    return _pick_best_pdf(candidates, title)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None,
                    help="cap papers processed (smoke test)")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    from extract_schema_columns import (
        _first_surname, _pick_best_pdf, extract_text_from_pdf,
    )
    import fable_extract
    meta = fable_extract._get_paper_meta()
    pdf_index = fable_extract._get_pdf_index()

    TEXTS.mkdir(parents=True, exist_ok=True)
    CORPUS_CACHE.mkdir(parents=True, exist_ok=True)

    # Column definitions (166 binary schema cols) for the burn prompt.
    cols = fable_extract._schema_column_defs()
    COLUMNS_JSON.write_text(json.dumps(cols))

    lit_ids = list(meta.index)
    if args.limit:
        lit_ids = lit_ids[: args.limit]

    worklist = []
    n_unresolved = n_done = n_notext = n_new = 0
    helpers = (_first_surname, _pick_best_pdf)

    for i, lit in enumerate(lit_ids):
        pdf = _resolve_pdf(lit, meta, pdf_index, helpers)
        if pdf is None:
            n_unresolved += 1
            continue
        try:
            sha = hashlib.sha1(pdf.read_bytes()).hexdigest()
        except OSError:
            n_unresolved += 1
            continue
        if (CORPUS_CACHE / f"{sha}.txt").exists():
            n_done += 1
            continue
        text_path = TEXTS / f"{lit}.txt"
        if not text_path.exists():
            text = extract_text_from_pdf(pdf)
            if not text:
                n_notext += 1
                continue
            text_path.write_text(text[:MAX_CHARS])
        worklist.append({"lit_id": str(lit), "text_path": str(text_path), "sha": sha})
        n_new += 1
        if not args.quiet and (i + 1) % 500 == 0:
            print(f"  ...{i+1}/{len(lit_ids)} scanned | worklist={n_new} "
                  f"done={n_done} unresolved={n_unresolved}", file=sys.stderr)

    WORKLIST.write_text(json.dumps(worklist))

    print(f"\nPre-pass complete:")
    print(f"  papers scanned      : {len(lit_ids)}")
    print(f"  already Fable-done  : {n_done}  (cached, skipped)")
    print(f"  unresolved (no PDF) : {n_unresolved}")
    print(f"  resolved but no text: {n_notext}")
    print(f"  -> WORKLIST (to burn): {n_new}")
    print(f"  worklist  : {WORKLIST}")
    print(f"  columns   : {COLUMNS_JSON} ({len(cols)} cols)")
    print(f"  cache dir : {CORPUS_CACHE}")
    # Suggested shard count for the burn (<=900 agents/workflow).
    if n_new:
        shards = -(-n_new // 900)
        print(f"  suggested burn shards (<=900/shard): {shards}")


if __name__ == "__main__":
    main()
