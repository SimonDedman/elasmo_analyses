"""ONE definition of "this chunk is done", imported by every stage.

An agent killed mid-write (session limit) leaves a cache file that is large and
non-empty but truncated: valid-looking JSON ending in a trailing comma with no
closing bracket. Every stage previously tested `st_size >= 2`, which such a file
passes, so:
  - conf_fable_fetch printed ALREADY_DONE and the chunk could NEVER be re-run;
  - fable_night_plan and fable_progress counted it complete;
  - conf_fable_merge's completeness guard passed the book, then merged it minus
    the truncated chunks' abstracts and reported a confident under-count.

Five chunks were in that state on 2026-09-02 (JMIH2009 x2, JMIH2018 x3).

"Done" therefore means the file PARSES. A chunk that legitimately yielded no
abstracts (a tail chunk landing in back matter) parses as [] and is done; a
truncated one does not parse and is not.
"""
import json
from pathlib import Path


def read_cache(path):
    """(ok, abstracts). ok=False means missing or truncated — re-run it."""
    p = Path(path)
    if not p.exists() or p.stat().st_size < 2:
        return False, []
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return False, []
    items = d if isinstance(d, list) else d.get("abstracts", [])
    return True, items if isinstance(items, list) else []


def is_done(path):
    return read_cache(path)[0]


def count(path):
    return len(read_cache(path)[1])
