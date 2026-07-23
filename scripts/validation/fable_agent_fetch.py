"""Corpus Fable burn — per-agent fetch helper.

Given a 0-based index into the current fable_corpus_worklist.json, prints
everything a burn subagent needs in ONE blob: the cache path to write, the
paper's literature_id, the 166 column definitions, and the full paper text.
Centralising all file I/O here (tested Python) keeps the subagent's job to just
"run this, classify, Write the cache file" — no fragile path/JSON handling in
the model.

Usage (from a burn subagent):
  python3 scripts/validation/fable_agent_fetch.py <index>
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/validation"
WORKLIST = OUT / "fable_corpus_worklist.json"
COLUMNS_JSON = OUT / "fable_corpus_columns.json"
CORPUS_CACHE = OUT / ".fable_corpus_cache"


def main():
    idx = int(sys.argv[1])
    wl = json.loads(WORKLIST.read_text())
    if idx < 0 or idx >= len(wl):
        print(f"ERROR: index {idx} out of range (worklist len {len(wl)})")
        sys.exit(2)
    item = wl[idx]
    cache_path = CORPUS_CACHE / f"{item['sha']}.txt"
    if cache_path.exists():
        # Already processed (resume / re-launched shard) — tell the agent to skip.
        print(f"ALREADY_DONE: {cache_path}")
        return
    cols = json.loads(COLUMNS_JSON.read_text())
    text_path = Path(item["text_path"])
    if not text_path.exists():
        print(f"ERROR: text file missing: {text_path}")
        sys.exit(3)
    text = text_path.read_text(errors="replace")

    cache_path = CORPUS_CACHE / f"{item['sha']}.txt"
    print(f"CACHE_PATH: {cache_path}")
    print(f"LIT: {item['lit_id']}")
    print("=== COLUMNS (name: what counts as evidence) ===")
    for c in cols:
        print(f"{c['name']}: {c['description']}")
    print("=== PAPER TEXT (the study to audit) ===")
    print(text)
    print("=== END PAPER TEXT ===")


if __name__ == "__main__":
    main()
