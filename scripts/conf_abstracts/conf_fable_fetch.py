"""STAGE 2 helper — a Fable agent runs this to fetch its book assignment.

The workflow JS sandbox has no filesystem access and args must be a literal, so
each Fable agent calls `python3 conf_fable_fetch.py <index>` to obtain its cache
path, book metadata, and the full book text in one blob. If the cache already
exists (non-empty), prints ALREADY_DONE so the agent can no-op (resume).

Usage: python3 scripts/conf_abstracts/conf_fable_fetch.py <index>
"""
import json
import sys
from pathlib import Path

WORKLIST = (Path(__file__).resolve().parents[2]
            / "outputs" / "conf_abstracts" / "fable_worklist.json")


def main(index: int):
    wl = json.loads(WORKLIST.read_text(encoding="utf-8"))
    entry = next((w for w in wl if w["index"] == index), None)
    if entry is None:
        print(f"ERROR: no worklist entry with index {index}")
        return 1
    cache = Path(entry["cache_path"])
    # ">= 2" treats a legitimate empty result ("[]", 2 bytes — a programme with
    # no extractable abstracts) as done, so resume runs don't re-do it.
    if cache.exists() and cache.stat().st_size >= 2:
        print("ALREADY_DONE")
        return 0
    text = Path(entry["src_txt"]).read_text(encoding="utf-8")
    print(f"CACHE_PATH: {entry['cache_path']}")
    print(f"MEETING: {entry['meeting']}")
    print(f"YEAR: {entry['year']}")
    print(f"CITY: {entry['city'] or ''}")
    print(f"SOCIETY_HINT: {entry['society_hint']}")
    print("=== BOOK TEXT ===")
    print(text)
    print("=== END BOOK TEXT ===")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: conf_fable_fetch.py <index>")
        sys.exit(2)
    sys.exit(main(int(sys.argv[1])))
