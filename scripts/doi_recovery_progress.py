#!/usr/bin/env python3
"""Live progress display for a running recover_missing_dois.py pass.

Per ~/.claude/LONG-RUNNING-TASKS.md: the worker already publishes its own
progress, rate and ETA, so this PARSES those numbers rather than deriving its
own and drifting from them. It adds only what the worker cannot show: liveness,
a state, and an independent count of what actually landed.

Usage:
    watch -n 60 -t -c "cd '<project root>' && python3 scripts/doi_recovery_progress.py"
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "logs/doi_recovery_console.log"
CACHE = ROOT / "outputs/.doi_recovery_cache.json"
WORKER = "recover_missing_dois.py"
STALL_SECONDS = 600

C_RESET, C_BOLD, C_DIM = "\033[0m", "\033[1m", "\033[2m"
C_GREEN, C_YELLOW, C_RED, C_CYAN = "\033[32m", "\033[33m", "\033[31m", "\033[36m"

# e.g. "  2,300/7,878  {'rejected': 2019, 'hit': 234, ...}  eta 75m (00:46 PDT)"
PROG = re.compile(r"^\s*([\d,]+)/([\d,]+)\s+(\{.*?\})\s*(?:eta\s+(\d+)m\s*\(([^)]*)\))?")
POOL = re.compile(r"no-DOI article-shaped rows:\s*([\d,]+)\s+cached:\s*([\d,]+)")


def worker_pid() -> int | None:
    """/proc scan, never `pgrep -f` — that matches the searching shell itself.

    Prefers the actual python process over the bash wrapper that launched it:
    the wrapper's command line also contains the script name, and reporting its
    pid is misleading (killing it would not stop the work).
    """
    wrapper = None
    for e in os.listdir("/proc"):
        if not e.isdigit():
            continue
        try:
            raw = Path(f"/proc/{e}/cmdline").read_bytes()
        except (OSError, PermissionError):
            continue
        argv = raw.split(b"\0")
        c = raw.decode(errors="replace")
        if WORKER not in c or "doi_recovery_progress" in c:
            continue
        exe = os.path.basename((argv[0] or b"").decode(errors="replace"))
        if exe.startswith("python"):
            return int(e)
        wrapper = wrapper or int(e)
    return wrapper


def main() -> None:
    now = time.time()
    print(f"{C_BOLD}C1 DOI recovery (Crossref){C_RESET}   "
          f"{time.strftime('%H:%M %Z', time.localtime(now))}")
    print("=" * 68)

    if not LOG.exists():
        print(f"{C_YELLOW}STATE: QUEUED{C_RESET} — no log yet")
        return

    lines = LOG.read_text(errors="replace").splitlines()
    pid = worker_pid()
    age = now - LOG.stat().st_mtime
    finished = any("recovery rate:" in ln for ln in lines)
    failed = any("Traceback" in ln for ln in lines)

    if failed:
        state, colour = "FAILED", C_RED
    elif finished and pid is None:
        state, colour = "DONE", C_GREEN
    elif pid is None:
        state, colour = "STOPPED EARLY", C_RED
    elif age > STALL_SECONDS:
        state, colour = "STALLED?", C_YELLOW
    else:
        state, colour = "RUNNING", C_GREEN
    running = state == "RUNNING"

    print(f"{colour}{C_BOLD}STATE: {state}{C_RESET}"
          + (f"   pid {pid}" if pid else "   (no worker process)"))

    pool = cached = None
    for ln in lines:
        m = POOL.search(ln)
        if m:
            pool = int(m.group(1).replace(",", ""))
            cached = int(m.group(2).replace(",", ""))

    last = None
    for ln in reversed(lines):
        m = PROG.match(ln)
        if m:
            last = m
            break

    if last:
        done = int(last.group(1).replace(",", ""))
        total = int(last.group(2).replace(",", ""))
        try:
            counts = eval(last.group(3), {"__builtins__": {}})  # worker's own dict
        except Exception:  # noqa: BLE001
            counts = {}
        pct = 100 * done / total if total else 0
        if running and last.group(4):
            # The worker's own ETA, not one re-derived here.
            print(f"progress: {done:,}/{total:,}  {pct:.1f}%   "
                  f"eta {last.group(4)}m ({last.group(5)})")
        else:
            print(f"progress: {done:,}/{total:,}  at the point it stopped "
                  f"{C_DIM}(no ETA — not running){C_RESET}")

        hit = counts.get("hit", 0)
        err = counts.get("error", 0)
        ok = sum(v for k, v in counts.items() if k != "error")
        print(f"  hit {hit:,}   near {counts.get('near', 0):,}   "
              f"rejected {counts.get('rejected', 0):,}   "
              f"absent {counts.get('absent', 0):,}   "
              + (f"{C_RED}error {err:,}{C_RESET}" if err else f"{C_DIM}error 0{C_RESET}"))
        if ok:
            print(f"  recovery rate: {C_BOLD}{100*hit/ok:.1f}%{C_RESET} of {ok:,} "
                  f"answered queries "
                  f"{C_DIM}(errors excluded from the denominator){C_RESET}")
            if running and total:
                print(f"  {C_DIM}projected total hits at this rate: "
                      f"~{int(hit/done*total):,}{C_RESET}")

    # Independent count: the cache is written every 100 queries, so it lags the
    # log slightly. Shown so the two can visibly disagree rather than one being
    # trusted blindly.
    if CACHE.exists():
        try:
            n = len(json.loads(CACHE.read_text()))
            print(f"  {C_DIM}resume cache holds {n:,} answered queries "
                  f"(written every 100; lags the log){C_RESET}")
        except (json.JSONDecodeError, OSError):
            print(f"  {C_YELLOW}resume cache unreadable (mid-write?){C_RESET}")

    if pool is not None:
        print(f"{C_DIM}pool {pool:,} no-DOI article-shaped rows; "
              f"{cached:,} already cached at launch{C_RESET}")
    print(f"{C_DIM}log: {LOG}{C_RESET}")
    if age > 120:
        print(f"{C_YELLOW}no log output for {int(age//60)}m{C_RESET}")
    if finished:
        print(f"{C_CYAN}--- result ---{C_RESET}")
        for ln in lines[-14:]:
            print("  " + ln[:104])
    print(f"{C_DIM}nothing is written to papers_data.json without --apply{C_RESET}")


if __name__ == "__main__":
    main()
