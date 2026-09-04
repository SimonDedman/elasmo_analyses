"""Safe read-modify-write for docs/papers_data.json.

WHY THIS EXISTS
---------------
On 2026-09-04 four rows appeared in papers_data.json from a process running
concurrently with the DOI-recovery pass. Nothing was lost that time, but only
because of the order the writes happened to land in.

Every writer here does a naive read-modify-write: load the whole file, mutate
in memory, write it back. Two of those overlapping means the second write
silently erases whatever the first added. There is no error, no exception, and
no trace — the rows are simply gone, and the next person to notice is whoever
looks for a paper that should be there. That is exactly the class of failure
where "no exception" is mistaken for "it worked".

WHAT THIS PROVIDES
------------------
`mutate()` holds an exclusive advisory lock across the whole read-modify-write,
so concurrent writers queue instead of clobbering. It writes atomically
(tmp + rename), keeps a timestamped backup, and asserts afterwards that no row
present at read time has disappeared.

    from lib.papers_data_io import mutate

    with mutate() as papers:          # papers is the parsed list
        for p in papers:
            ...                       # mutate freely
    # written atomically on clean exit; left untouched on exception

The lock is advisory, so it only protects writers that use it. Any script that
writes papers_data.json should be moved onto this.
"""
from __future__ import annotations

import fcntl
import json
import os
import shutil
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PAPERS_DATA = PROJECT_ROOT / "docs/papers_data.json"
LOCK_FILE = Path("/tmp/papers_data.lock")
LOCK_TIMEOUT = 300  # seconds to wait for another writer before giving up


def _row_key(p: dict) -> tuple:
    """Identity that survives the float/string literature_id inconsistency."""
    return (str(p.get("literature_id", "")).replace(".0", "").strip(),
            (p.get("title") or "")[:80])


@contextmanager
def mutate(backup: bool = True, allow_deletions: bool = False):
    """Exclusive, atomic read-modify-write of papers_data.json.

    Args:
        backup: keep a timestamped copy before writing.
        allow_deletions: permit rows present at read time to be absent at write
            time. Off by default so an accidental drop raises instead of
            passing silently; pass True when deleting is the point.
    """
    lock_fh = open(LOCK_FILE, "w")
    try:
        # Blocking lock with a deadline: a stuck writer should surface as a
        # timeout, not as this process waiting forever with no output.
        import signal

        def _timeout(signum, frame):
            raise TimeoutError(
                f"waited {LOCK_TIMEOUT}s for another papers_data.json writer; "
                f"check for a running sync or ingest before forcing")

        old_handler = signal.signal(signal.SIGALRM, _timeout)
        signal.alarm(LOCK_TIMEOUT)
        try:
            fcntl.flock(lock_fh, fcntl.LOCK_EX)
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
        lock_fh.write(f"{os.getpid()} {datetime.now().isoformat()}\n")
        lock_fh.flush()

        papers = json.loads(PAPERS_DATA.read_text(encoding="utf-8"))
        before = {_row_key(p) for p in papers}
        n_before = len(papers)

        yield papers

        after = {_row_key(p) for p in papers}
        lost = before - after
        if lost and not allow_deletions:
            raise RuntimeError(
                f"refusing to write: {len(lost)} row(s) present at read time "
                f"are missing at write time, e.g. {sorted(lost)[:3]}. "
                f"Pass allow_deletions=True if this is intended.")

        if backup:
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            shutil.copy2(PAPERS_DATA,
                         PAPERS_DATA.with_suffix(f".backup-{stamp}.json"))

        tmp = PAPERS_DATA.with_suffix(".tmp")
        tmp.write_text(json.dumps(papers, ensure_ascii=False, indent=1),
                       encoding="utf-8")
        tmp.replace(PAPERS_DATA)
        print(f"papers_data.json written: {n_before:,} -> {len(papers):,} rows"
              + (f", {len(lost):,} removed" if lost else ""))
    finally:
        try:
            fcntl.flock(lock_fh, fcntl.LOCK_UN)
        finally:
            lock_fh.close()
