#!/usr/bin/env python3
"""Live progress display for a running sync_shark_references.py pass.

Design rules it obeys (see ~/.claude/LONG-RUNNING-TASKS.md):
  * Prints a STATE, not just a count: QUEUED / RUNNING / STALLED? / DONE / FAILED.
  * Liveness comes from /proc cmdline scanning, never `pgrep -f`.
  * Progress is SCOPED TO THE CURRENT PHASE. An earlier phase's finished
    counter must never be left on screen: on 2026-09-03 this display kept
    showing Phase 3's "2,760/2,760 100.0%" all through Phase 4, and the run was
    reported as finished when it had two more phases to go. The p4_* tallies
    are the exception: they are RUN totals, so they survive a phase change.
  * It reports the worker's OWN tallies rather than deriving its own. The
    checkpoint's phase4_downloaded_ids is a RESUME SET, not a download count:
    it includes papers whose PDF was already on disk (result "exists"), and
    phase4_failed_ids includes papers with no URL at all (result "skip"). Read
    as downloads and failures they overstate both, 39 and 320 against 8 real
    fetches.
  * Errors and failures are shown, never filtered out.
  * Rate is taken from a recent window, not from total elapsed.
  * Every ETA carries an absolute local clock time, resolved at the ETA's own
    instant, and a job that is not RUNNING renders no ETA and no percentage.
  * The fetched-PDF tally is counted independently off disk as well as from the
    worker's log, so the two can disagree visibly.

Usage:
    watch -n 60 -t -c "cd '<project root>' && python3 scripts/sr_sync_progress.py"
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
PDF_BASE = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")
WORKER = "sync_shark_references.py"

RATE_WINDOW_SECONDS = 600
STALL_SECONDS = 900

C_RESET, C_BOLD, C_DIM = "\033[0m", "\033[1m", "\033[2m"
C_GREEN, C_YELLOW, C_RED, C_CYAN = "\033[32m", "\033[33m", "\033[31m", "\033[36m"

TS_RE = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})")
PHASE_RE = re.compile(r"\bPhase ([0-9]+[a-z]?)\b:?\s*(.*)")
LETTER_RE = re.compile(r"\[(\d+)/26\] Fetching letter")
NN_RE = re.compile(r"\[(\d+)/(\d+)\]")
DIFF_RE = re.compile(r"Diff results:\s*([\d,]+) new,\s*([\d,]+) known-needing-PDF")

# Phase 4 emits one of these per paper and no [n/N] counter of its own.
P4_FETCHED = re.compile(r"\bDownloaded:")
P4_EXISTS = re.compile(r"PDF already exists:")
P4_FAILED = re.compile(r"Download failed for|PDF URL returned HTML")


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
    return time.strftime("%H:%M %Z", time.localtime(epoch))


def fmt_duration(seconds: float) -> str:
    seconds = int(max(seconds, 0))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h{m:02d}m"
    if m:
        return f"{m}m{s:02d}s"
    return f"{s}s"


def parse_log(path: Path) -> dict:
    info = {
        "phase": None, "phase_num": None, "phase_started": None,
        "first_ts": None, "last_ts": None,
        "progress": None,           # scoped to the CURRENT phase only
        "new_papers": None, "known_needing_pdf": None,
        "p4_fetched": 0, "p4_exists": 0, "p4_failed": 0, "p4_final": None,
        "errors": 0, "warnings": 0,
        "finished": False, "traceback": False,
        "phase_event_times": [],    # timestamps of current-phase progress events
        "recent": [],
    }
    try:
        lines = path.read_text(errors="replace").splitlines()
    except OSError:
        return info

    for line in lines:
        ts = None
        m = TS_RE.match(line)
        if m:
            ts = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S").timestamp()
            info["last_ts"] = ts
            if info["first_ts"] is None:
                info["first_ts"] = ts

        if " ERROR" in line:
            info["errors"] += 1
        if " WARNING" in line:
            info["warnings"] += 1
        if "Traceback (most recent call last)" in line:
            info["traceback"] = True

        # Completion must be tested BEFORE the phase block below, which
        # `continue`s and so never let "Phase 6" or "Completed in" reach a
        # check placed after it. A clean finish was reported as STOPPED EARLY.
        if "Completed in" in line or "Sync complete" in line:
            info["finished"] = True

        pm = PHASE_RE.search(line)
        if pm and "Phase" in line and line.rstrip().endswith(("...", ":")) or (
                pm and re.search(r"Phase [0-9]+[a-z]?:", line)):
            new_num = pm.group(1)
            if new_num != info["phase_num"]:
                # A new phase invalidates the previous phase's counters.
                info["phase_num"] = new_num
                info["phase"] = f"Phase {pm.group(1)}: {pm.group(2)}".strip()
                info["phase_started"] = ts
                info["progress"] = None
                info["phase_event_times"] = []
                # NB: the p4_* tallies are RUN totals and deliberately survive
                # the phase change. Zeroing them made a finished run report
                # "PDFs fetched: 0" once Phase 5 began.
            continue

        dm = DIFF_RE.search(line)
        if dm:
            info["new_papers"] = int(dm.group(1).replace(",", ""))
            info["known_needing_pdf"] = int(dm.group(2).replace(",", ""))

        lm = LETTER_RE.search(line)
        nm = NN_RE.search(line)
        if lm:
            info["progress"] = (int(lm.group(1)), 26)
            if ts:
                info["phase_event_times"].append(ts)
        elif nm:
            info["progress"] = (int(nm.group(1)), int(nm.group(2)))
            if ts:
                info["phase_event_times"].append(ts)

        # Counted unconditionally, not only while phase_num == 4: these are
        # run totals, and gating them on the current phase made a finished run
        # report zero downloads.
        if P4_FETCHED.search(line):
            info["p4_fetched"] += 1
            if ts:
                info["phase_event_times"].append(ts)
        elif P4_EXISTS.search(line):
            info["p4_exists"] += 1
            if ts:
                info["phase_event_times"].append(ts)
        elif P4_FAILED.search(line):
            info["p4_failed"] += 1
            if ts:
                info["phase_event_times"].append(ts)

        fin = re.search(r"Downloaded:\s*(\d+),\s*Failed:\s*(\d+)", line)
        if fin:
            info["p4_final"] = (int(fin.group(1)), int(fin.group(2)))

    info["recent"] = lines[-5:]
    return info


def recent_rate(event_times: list[float], window: int = RATE_WINDOW_SECONDS):
    """Items/second over the trailing window of the CURRENT phase only."""
    if not event_times:
        return None
    now = time.time()
    recent = [t for t in event_times if now - t <= window]
    if len(recent) < 2:
        return None
    span = recent[-1] - recent[0]
    return (len(recent) - 1) / span if span > 0 else None


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
    print("=" * 70)

    if log is None:
        print(f"{C_YELLOW}STATE: QUEUED{C_RESET}  — no sync log found in logs/")
        return

    info = parse_log(log)
    age = now - info["last_ts"] if info["last_ts"] else None

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
        print(f"started: {clock(info['first_ts'])}   "
              f"elapsed {fmt_duration(now - info['first_ts'])}")
    if age is not None:
        note = (f"   {C_YELLOW}<-- no output for {fmt_duration(age)}{C_RESET}"
                if age > STALL_SECONDS else "")
        print(f"last log line: {fmt_duration(age)} ago{note}")

    ck = {}
    if CHECKPOINT_FILE.exists():
        try:
            ck = json.loads(CHECKPOINT_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            ck = {}

    # --- Progress, scoped to the current phase --------------------------------
    done = total = None
    if info["phase_num"] == "4":
        # Phase 4 prints no [n/N]; its denominator is the Phase 2 diff.
        if info["new_papers"] is not None:
            total = info["new_papers"] + (info["known_needing_pdf"] or 0)
        done = len(ck.get("phase4_downloaded_ids", [])) + \
            len(ck.get("phase4_failed_ids", []))
    elif info["progress"]:
        done, total = info["progress"]

    if done is not None and total:
        if running:
            rate = recent_rate(info["phase_event_times"])
            eta_txt = ""
            if rate and rate > 0 and done < total:
                eta = (total - done) / rate
                eta_txt = (f"   eta {fmt_duration(eta)} ({clock(now + eta)})"
                           f"  [{rate*60:.1f}/min, last 10 min]")
            print(f"phase progress: {done:,}/{total:,}  "
                  f"{100*done/total:.1f}%{eta_txt}")
        else:
            print(f"phase progress: {done:,}/{total:,} at the point it stopped "
                  f"{C_DIM}(no ETA — not running){C_RESET}")

    if info["new_papers"] is not None:
        print(f"diff: {info['new_papers']:,} new papers, "
              f"{info['known_needing_pdf']:,} known but lacking a PDF")

    # --- PDF tallies, each labelled for what it actually counts ---------------
    if info["phase_num"] in ("4", "5", "5b", "6") or info["p4_fetched"]:
        on_disk = disk_pdf_count(info["first_ts"]) if info["first_ts"] else 0
        worker_n = info["p4_final"][0] if info["p4_final"] else info["p4_fetched"]
        src = "worker's own final tally" if info["p4_final"] else "worker log"
        print(f"PDFs fetched: {worker_n:,} ({src})   |   "
              f"{on_disk:,} new files on disk (counted independently)")
        if abs(worker_n - on_disk) > max(3, 0.1 * max(worker_n, 1)):
            print(f"  {C_YELLOW}tallies disagree — check before trusting either"
                  f"{C_RESET}")
        failed_n = info["p4_final"][1] if info["p4_final"] else info["p4_failed"]
        print(f"  already present: {info['p4_exists']:,}   "
              f"no PDF obtained: {failed_n:,}")
        print(f"  {C_DIM}checkpoint resume sets (NOT download counts): "
              f"{len(ck.get('phase4_downloaded_ids', [])):,} processed-ok, "
              f"{len(ck.get('phase4_failed_ids', [])):,} processed-fail{C_RESET}")

    err_colour = C_RED if info["errors"] else C_DIM
    print(f"{err_colour}errors: {info['errors']:,}{C_RESET}   "
          f"{C_DIM}warnings: {info['warnings']:,} "
          f"(mostly paywall 403s — expected){C_RESET}")

    print(f"{C_DIM}log: {log}{C_RESET}")
    print(f"{C_CYAN}--- last lines ---{C_RESET}")
    for line in info["recent"]:
        print("  " + line[:108])


if __name__ == "__main__":
    main()
