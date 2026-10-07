#!/usr/bin/env python3
"""One-screen progress display for the RAG index build / sync.

    watch -n 60 -t -c 'cd "<project dir>" && python3 scripts/rag/progress.py'

Reads what the worker publishes (build_status.json, sync_state) and counts what
actually landed (rows in embeddings.npy, read by header only) rather than
deriving its own notion of done. Rate comes from a recent window of samples it
keeps in progress_samples.jsonl beside the index, never from total elapsed.
A build that is not advancing shows STALLED?/STOPPED EARLY with no ETA.
"""
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIVE = ROOT / "outputs" / "rag"
NEW = ROOT / "outputs" / "rag.new"
STALL_AFTER = 20 * 60      # s without growth before STALLED?
WINDOW = 30 * 60           # s of samples the rate is taken from


def npy_rows(path: Path):
    """Row count from the .npy header only (no load of the 300 MB array)."""
    try:
        import numpy as np
        with open(path, "rb") as fh:
            ver = np.lib.format.read_magic(fh)
            shape, _, _ = (np.lib.format.read_array_header_1_0(fh) if ver == (1, 0)
                           else np.lib.format.read_array_header_2_0(fh))
        return shape[0]
    except Exception:
        return None


def clock(epoch):
    return time.strftime("%H:%M %Z", time.localtime(epoch))


def main():
    state_lines, state_mtime = [], 0
    for d in (LIVE, NEW):
        try:
            state_lines = (d / "sync_state").read_text().splitlines()
            state_mtime = (d / "sync_state").stat().st_mtime
            break
        except OSError:
            continue
    last_state = state_lines[-1] if state_lines else ""
    rebuilding = ("rebuild" in (state_lines[0] if state_lines else "")
                  and not last_state.startswith(("DONE", "FAILED")))
    out = NEW if rebuilding and NEW.exists() else LIVE
    status = {}
    try:
        status = json.loads((out / "build_status.json").read_text())
    except (OSError, ValueError):
        pass
    if rebuilding and not status:
        # the rebuild has not reached its first checkpoint yet: nothing to count
        status = {"papers_indexed": 0, "chunks_indexed": 0, "target_papers": 0,
                  "updated_epoch": state_mtime, "complete": False}
    papers = status.get("papers_indexed", 0)
    target = status.get("target_papers") or 0
    chunks = status.get("chunks_indexed", 0)
    updated = status.get("updated_epoch", 0)
    complete = bool(status.get("complete"))
    landed = npy_rows(out / "embeddings.npy")
    now = time.time()

    # rolling samples for a windowed rate
    samples_path = out / "progress_samples.jsonl"
    samples = []
    try:
        samples = [json.loads(l) for l in samples_path.read_text().splitlines() if l.strip()]
    except OSError:
        pass
    if not samples or samples[-1]["papers"] != papers or now - samples[-1]["t"] > 300:
        samples.append({"t": now, "papers": papers})
        samples = [s for s in samples if now - s["t"] < 6 * 3600]
        try:
            samples_path.write_text("\n".join(json.dumps(s) for s in samples) + "\n")
        except OSError:
            pass
    window = [s for s in samples if now - s["t"] <= WINDOW]
    rate = None
    if len(window) >= 2 and window[-1]["t"] > window[0]["t"]:
        dp = window[-1]["papers"] - window[0]["papers"]
        dt = window[-1]["t"] - window[0]["t"]
        rate = dp / dt * 60 if dp > 0 else 0.0

    failed = last_state.startswith("FAILED")
    in_sync = last_state.startswith("STEP")
    done = (complete or last_state.startswith("DONE")) and not in_sync
    heartbeat = max(updated or 0, state_mtime if in_sync else 0)
    since = now - heartbeat if heartbeat else None
    if failed:
        state = "FAILED"
    elif done:
        state = "DONE"
    elif since is None:
        state = "QUEUED"
    elif since > STALL_AFTER:
        state = "STALLED?" if since < 2 * 3600 else "STOPPED EARLY"
    else:
        state = "RUNNING"

    print(f"SharkOracle RAG index  [{out.name}]   {time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"state      : {state}")
    if state_lines:
        print(f"sync step  : {last_state}")
    pct = f" ({papers / target * 100:.1f}%)" if target else ""
    print(f"papers     : {papers:,} / {target:,}{pct}   chunks {chunks:,}")
    print(f"landed     : {landed if landed is not None else '?'} embedding rows on disk"
          + ("" if landed is None or landed == chunks else "   <- differs from worker tally"))
    if updated:
        print(f"last write : {clock(updated)} ({since / 60:.0f} min ago)")
    if state == "RUNNING" and rate:
        remaining = max(target - papers, 0)
        eta = remaining / rate * 60
        print(f"rate       : {rate:.0f} papers/min (last {WINDOW // 60} min)")
        print(f"eta        : {eta / 3600:.1f} h  ->  {clock(now + eta)}")
    elif state == "RUNNING":
        print("rate       : (collecting samples)")
    else:
        print("rate / eta : n/a (not running)")
    prev = sorted(ROOT.glob("outputs/rag.prev_*"))
    if prev:
        print(f"previous   : {len(prev)} kept index dir(s), latest {prev[-1].name}")


if __name__ == "__main__":
    main()
