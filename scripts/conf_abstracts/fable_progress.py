"""Live progress for a running Fable conference-abstract extraction batch.

Counts the CACHE FILES that actually landed on disk — the same artefact the
worker treats as resume truth — rather than the workflow's own reported tally,
so a run that logs a result but writes nothing cannot look healthy.

  watch -n 60 -t -c ./venv/bin/python scripts/conf_abstracts/fable_progress.py
"""
import json
import os
import time
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conf_abstracts.fable_cache import read_cache

REPO = Path(__file__).resolve().parents[2]
WL = REPO / "outputs" / "conf_abstracts" / "fable_worklist.json"
BATCH = REPO / "outputs" / "conf_abstracts" / "fable_batch_current.json"
STATE = REPO / "outputs" / "conf_abstracts" / ".fable_progress_state.json"
STALL_S = 900  # no new cache for this long while running -> STALLED?


def clock(ts):
    return time.strftime("%H:%M %Z", time.localtime(ts))


def main():
    batch = json.loads(BATCH.read_text())
    wl = {w["index"]: w for w in json.loads(WL.read_text())}
    idx = batch["indices"]
    started = time.mktime(time.strptime(batch["launched"][:19], "%Y-%m-%dT%H:%M:%S"))

    done, pending, abstracts, newest = [], [], 0, 0
    truncated = []
    for i in idx:
        w = wl.get(i)
        if not w:
            continue
        p = Path(w["cache_path"])
        ok, items = read_cache(p)
        if ok:
            done.append(i)
            newest = max(newest, p.stat().st_mtime)
            abstracts += len(items)
        else:
            if p.exists():
                truncated.append(i)   # exists but won't parse: killed mid-write
            pending.append(i)

    n, t = len(done), len(idx)
    now = time.time()
    # rate from the recent window (cache mtimes), never from total elapsed
    mtimes = sorted(Path(wl[i]["cache_path"]).stat().st_mtime for i in done)
    recent = [m for m in mtimes if m > now - 3600] or mtimes[-5:]
    rate = (len(recent) / max(recent[-1] - recent[0], 1) * 60) if len(recent) > 1 else 0

    # A batch whose workflow has ENDED must never render RUNNING or an ETA.
    # Staleness alone took 15 min to notice, so a finished run displayed a live
    # percentage and a future ETA for a workflow that had already stopped —
    # the ETA is the line people read. The orchestrator writes `finished` (with
    # an optional `reason`) into the batch file the moment the run returns.
    ended = batch.get("finished")
    if n == t:
        state = "DONE"
    elif ended:
        state = f"STOPPED EARLY ({batch.get('reason', 'run ended')})"
    elif newest and now - newest > STALL_S:
        state = "STALLED?"
    elif n == 0 and now - started > STALL_S:
        state = "STALLED?"
    else:
        state = "RUNNING"

    print(f"Fable batch {batch['run_id']}   state {state}")
    print(f"  chunks   {n}/{t}  ({n/t*100:5.1f}%)   abstracts cached: {abstracts}")
    print(f"  started  {clock(started)}   last cache {clock(newest) if newest else '—'}")
    if state == "RUNNING" and rate > 0 and n < t:
        eta = (t - n) / rate * 60
        print(f"  rate     {rate:.2f} chunks/min   eta {int(eta//3600)}h{int(eta%3600//60):02d}m "
              f"({clock(now + eta)})")
    elif state != "DONE":
        print("  rate     — (no ETA: not enough completions, or not running)")

    by_book = {}
    for i in idx:
        w = wl.get(i)
        if not w:
            continue
        k = w.get("book_key") or w["key"]
        d, tt = by_book.get(k, (0, 0))
        by_book[k] = (d + (i in done), tt + 1)
    print("  per book:", "  ".join(f"{k} {d}/{t2}" for k, (d, t2) in sorted(by_book.items())))
    if truncated:
        print(f"  TRUNCATED (exists but unparseable, will re-run): {truncated}")
    if pending:
        print(f"  pending indices: {pending}")
    STATE.write_text(json.dumps({"n": n, "t": t, "at": now}))


if __name__ == "__main__":
    main()
