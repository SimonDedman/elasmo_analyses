"""Progress display for fetch_gcfi_papers.py. Reads the worker's own state file
rather than deriving its own notion of done, and prints a STATE, not just a
count — a job that is not running must not render a live percentage."""
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conf_abstracts import config as C  # noqa: E402

STATE = C.OUT / "gcfi_fetch_state.json"
LOG = C.REPO / "logs" / "gcfi_fetch.log"
STAGING = C.OUT / "gcfi_papers"


def running():
    """True if a fetch_gcfi_papers process is alive. NOT pgrep -f: this harness
    puts the command on the caller's own command line, so a pattern match finds
    the searcher and always says yes."""
    for pid in filter(str.isdigit, os.listdir("/proc")):
        try:
            cmd = Path(f"/proc/{pid}/cmdline").read_bytes().decode("utf-8", "replace")
        except OSError:
            continue
        if "fetch_gcfi_papers.py" in cmd and pid != str(os.getpid()):
            return True
    return False


def main():
    if not STATE.exists():
        print("QUEUED — no state file yet")
        return
    st = json.loads(STATE.read_text())
    vols = sorted(st.items(), key=lambda kv: int(kv[0]))
    done = sum(1 for _, v in vols if v.get("done"))
    seen = sum(len(v.get("papers", {})) for _, v in vols)
    matched = sum(1 for _, v in vols for p in v.get("papers", {}).values() if p.get("matched"))
    fails = sum(len(v.get("failures", [])) for _, v in vols)
    nopath = [k for k, v in vols if not v.get("path")]
    staged = len(list(STAGING.glob("*.pdf"))) if STAGING.is_dir() else 0

    alive = running()
    age = time.time() - STATE.stat().st_mtime
    state = ("DONE" if done == len(vols) else
             "STOPPED EARLY" if not alive else
             "STALLED?" if age > 300 else "RUNNING")
    print(f"GCFI fetch — {state}   (state file last grew {age/60:.1f} min ago, "
          f"{datetime.now():%H:%M:%S %Z})")
    print(f"  volumes {done}/{len(vols)} finished   papers probed {seen}   "
          f"MATCHED {matched}/31   staged on disk {staged}   FAILURES {fails}")
    if nopath:
        print(f"  no upload path found for volume(s): {', '.join(nopath)} "
              f"— those years cannot be fetched this way")
    for k, v in vols:
        n = len(v.get("papers", {}))
        m = sum(1 for p in v.get("papers", {}).values() if p.get("matched"))
        flag = "done" if v.get("done") else ("no path" if not v.get("path") else "...")
        print(f"    v{k:>3s} ({1947 + int(k)}): {n:3d} probed, {m:2d} matched  [{flag}]")
    if LOG.exists():
        tail = [l for l in LOG.read_text().splitlines() if l.strip()][-3:]
        for l in tail:
            print(f"  | {l[:110]}")


if __name__ == "__main__":
    main()
