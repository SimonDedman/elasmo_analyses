#!/usr/bin/env python3
"""Live progress display for a running sync_shark_references.py pass.

Design rules it obeys (see ~/.claude/LONG-RUNNING-TASKS.md):
  * Prints a STATE, not just a count: QUEUED / RUNNING / STALLED? / DONE / FAILED.
  * Liveness comes from /proc cmdline scanning, never `pgrep -f`.
  * Errors and failures are shown, never filtered out.
  * Rate is taken from a recent window, not from total elapsed.
  * Every ETA carries an absolute local clock time, resolved at the ETA's own
    instant.
  * A job that is not RUNNING renders no ETA and no live percentage.
  * The PDF tally is counted independently off disk as well as read from the
    worker's own checkpoint, so the two can disagree visibly.

Usage:
    watch -n 60 -t -c python3 scripts/sr_sync_progress.py
"""
from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = PROJECT_ROOT / "logs"
CHECKPOINT_FILE = PROJECT_ROOT / "outputs/.sr_sync_checkpoint.json"
LOCK_FILE = Path("/tmp/sr_sync.lock")
PDF_BASE = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")
WORKER = "sync_shark_references.py"

# Rate is measured over this trailing window of log lines, never over the
# whole run: earlier phases move at completely different speeds.
RATE_WINDOW_SECONDS = 600
STALL_SECONDS = 900

C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_DIM = "\033[2m"
C_GREEN = "\033[32m"
C_YELLOW = "\033[33m"
C_RED = "\033[31m"
C_CYAN = "\033[36m"


def worker_pid() -> int | None:
    """Find the worker via /proc, not pgrep -f.

    `pgrep -f sync_shark_references.py` matches the searching shell itself in
    this harness and so always says yes. Reading /proc/<pid>/cmdline is safe
    because this script's own argv says sr_sync_progress.py.
    """
    for entry in os.listdir("/proc"):
        if not entry.isdigit():
            continue
        try:
            cmdline = Path(f"/proc/{entry}/cmdline").read_bytes().decode(errors="replace")
        except (OSError, PermissionError):
            continue
        if WORKER in cmdline and "sr_sync_progress" not in cmdline:
            return int(entry)
    return None


def todays_log() -> Path | None:
    logs = sorted(LOG_DIR.glob("sr_sync_2*.log"), key=lambda p: p.stat().st_mtime)
    return logs[-1] if logs else None


def clock(epoch: float) -> str:
    """Absolute local time WITH the zone resolved at that instant, not now."""
    lt = time.localtime(epoch)
    return time.strftime("%H:%M %Z", lt)


def fmt_duration(seconds: float) -> str:
    seconds = int(max(seconds, 0))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h{m:02d}m"
    if m:
        return f"{m}m{s:02d}s"
    return f"{s}s"


LINE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})")
PHASE_RE = re.compile(r"(Phase [0-9]+[a-z]?):?\s*(.*)")
LETTER_RE = re.compile(r"\[(\d+)/26\] Fetching letter")
DETAIL_RE = re.compile(r"\[(\d+)/(\d+)\]")


def parse_log(path: Path) -> dict:
    """Pull state out of the worker's own log rather than re-deriving it."""
    info = {
        "phase": None,
        "last_ts": None,
        "first_ts": None,
        "progress": None,      # (done, total) if the worker prints one
        "errors": 0,
        "warnings": 0,
        "new_papers": None,
        "downloaded": 0,
        "failed_dl": 0,
        "finished": False,
        "traceback": False,
        "recent": [],
    }
    try:
        lines = path.read_text(errors="replace").splitlines()
    except OSError:
        return info

    for line in lines:
        m = LINE_RE.match(line)
        if m:
            ts = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S").timestamp()
            info["last_ts"] = ts
            if info["first_ts"] is None:
                info["first_ts"] = ts
        # Never grep errors away — count them and surface them.
        if " ERROR" in line:
            info["errors"] += 1
        if " WARNING" in line:
            info["warnings"] += 1
        if "Traceback (most recent call last)" in line:
            info["traceback"] = True

        pm = PHASE_RE.search(line)
        if pm:
            info["phase"] = f"{pm.group(1)}: {pm.group(2)}".strip().rstrip(":")

        lm = LETTER_RE.search(line)
        if lm:
            info["progress"] = (int(lm.group(1)), 26)
        dm = DETAIL_RE.search(line)
        if dm and not lm:
            info["progress"] = (int(dm.group(1)), int(dm.group(2)))

        nm = re.search(r"(\d[\d,]*) (?:genuinely )?new papers", line)
        if nm:
            info["new_papers"] = int(nm.group(1).replace(",", ""))
        if re.search(r"\bDownloaded\b", line):
            info["downloaded"] += 1
        if re.search(r"download (?:failed|skipped)", line, re.I):
            info["failed_dl"] += 1
        if "Phase 6" in line or "Sync complete" in line:
            info["finished"] = True

    info["recent"] = lines[-6:]
    return info


def recent_rate(path: Path, window: int = RATE_WINDOW_SECONDS) -> float | None:
    """Items/second over the trailing window only."""
    try:
        lines = path.read_text(errors="replace").splitlines()
    except OSError:
        return None
    now = time.time()
    stamped = []
    for line in lines:
        m = LINE_RE.match(line)
        if m and DETAIL_RE.search(line):
            ts = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S").timestamp()
            if now - ts <= window:
                stamped.append(ts)
    if len(stamped) < 2:
        return None
    span = stamped[-1] - stamped[0]
    return (len(stamped) - 1) / span if span > 0 else None


def disk_pdf_count(since: float) -> int:
    """Independent count of what actually landed, beside the worker's tally."""
    n = 0
    if not PDF_BASE.exists():
        return 0
    for root, _dirs, files in os.walk(PDF_BASE):
        for f in files:
            if not f.lower().endswith(".pdf"):
                continue
            try:
                if os.path.getmtime(os.path.join(root, f)) >= since:
                    n += 1
            except OSError:
                pass
    return n


def main() -> None:
    log = todays_log()
    pid = worker_pid()
    now = time.time()

    print(f"{C_BOLD}shark-references monthly sync{C_RESET}   {clock(now)}")
    print("=" * 68)

    if log is None:
        print(f"{C_YELLOW}STATE: QUEUED{C_RESET}  — no sync log found in logs/")
        return

    info = parse_log(log)
    age = now - info["last_ts"] if info["last_ts"] else None

    # --- State, decided before anything else is rendered -------------------
    if info["traceback"]:
        state, colour = "FAILED", C_RED
    elif info["finished"] and pid is None:
        state, colour = "DONE", C_GREEN
    elif pid is None:
        state, colour = "STOPPED EARLY", C_RED
    elif age is not None and age > STALL_SECONDS:
        state, colour = "STALLED?", C_YELLOW
    else:
        state, colour = "RUNNING", C_GREEN

    running = state == "RUNNING"

    print(f"{colour}{C_BOLD}STATE: {state}{C_RESET}"
          + (f"   pid {pid}" if pid else "   (no worker process)"))
    print(f"phase:   {info['phase'] or 'starting up'}")
    if info["first_ts"]:
        print(f"started: {clock(info['first_ts'])}"
              f"   elapsed {fmt_duration(now - info['first_ts'])}")
    if age is not None:
        note = f"   {C_YELLOW}<-- no output for {fmt_duration(age)}{C_RESET}" \
            if age > STALL_SECONDS else ""
        print(f"last log line: {fmt_duration(age)} ago{note}")

    # --- Progress + ETA: only while genuinely running ----------------------
    if info["progress"]:
        done, total = info["progress"]
        if running and total:
            pct = 100.0 * done / total
            rate = recent_rate(log)
            eta_txt = ""
            if rate and rate > 0 and done < total:
                eta = (total - done) / rate
                eta_txt = (f"   eta {fmt_duration(eta)} ({clock(now + eta)})"
                           f"  [{rate*60:.1f}/min, last 10 min]")
            print(f"progress: {done:,}/{total:,}  {pct:.1f}%{eta_txt}")
        else:
            # Not running: a state line, and deliberately NO percentage or ETA.
            print(f"progress: {done:,}/{total:,} at the point it stopped "
                  f"{C_DIM}(no ETA — not running){C_RESET}")

    if info["new_papers"] is not None:
        print(f"new papers found: {info['new_papers']:,}")

    # --- Two independent tallies, shown side by side -----------------------
    ck = {}
    if CHECKPOINT_FILE.exists():
        try:
            ck = json.loads(CHECKPOINT_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            ck = {}
    ck_dl = len(ck.get("phase4_downloaded_ids", []))
    ck_fail = len(ck.get("phase4_failed_ids", []))
    if info["first_ts"]:
        on_disk = disk_pdf_count(info["first_ts"])
        print(f"PDFs:    worker says {ck_dl:,} downloaded / {ck_fail:,} failed"
              f"   |   {on_disk:,} new files on disk (counted independently)")
        if ck_dl and abs(ck_dl - on_disk) > max(5, 0.1 * ck_dl):
            print(f"  {C_YELLOW}tallies disagree — check before trusting either"
                  f"{C_RESET}")

    err_colour = C_RED if info["errors"] else C_DIM
    print(f"{err_colour}errors: {info['errors']:,}   "
          f"warnings: {info['warnings']:,}{C_RESET}")

    print(f"{C_DIM}log: {log}{C_RESET}")
    print(f"{C_CYAN}--- last lines ---{C_RESET}")
    for line in info["recent"]:
        print("  " + line[:110])


if __name__ == "__main__":
    main()
