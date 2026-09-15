#!/usr/bin/env python3
"""Glanceable progress for `enrich_altmetric.py --refresh`.

    watch -n 60 -t -c 'cd "<project>" && python3 scripts/altmetric_refresh_progress.py --tag 2026-09-14'

State comes from the worker's markers and pid (DONE / ABORTED files, /proc/<pid>/cmdline), never
from a command-line pattern match. The answered count is shown twice: the worker's own tally
(status.json) and an independent count of lines actually written to results.jsonl.
ETA is printed only while RUNNING, with an absolute clock time.
"""
import argparse
import json
import time
from datetime import datetime
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
RED, GRN, YEL, BLD, RST = "\033[31m", "\033[32m", "\033[33m", "\033[1m", "\033[0m"
STALL_AFTER_S = 300


def pid_is_worker(pid) -> bool:
    try:
        argv = Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0")
    except (FileNotFoundError, TypeError, PermissionError):
        return False
    return "python" in Path(argv[0].decode()).name and any(a.endswith(b"enrich_altmetric.py") for a in argv[1:])


def clock(seconds_from_now: float) -> str:
    return time.strftime("%H:%M %Z", time.localtime(time.time() + seconds_from_now))


def fmt_dur(s: float) -> str:
    s = int(s)
    return f"{s // 3600}h{(s % 3600) // 60:02d}m" if s >= 3600 else f"{s // 60}m{s % 60:02d}s"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default=datetime.now().strftime("%Y-%m-%d"))
    tag = ap.parse_args().tag
    d = PROJECT / "outputs" / f"altmetric_refresh_{tag}"
    print(f"{BLD}Altmetric refresh {tag}{RST}   now {time.strftime('%H:%M:%S %Z')}")
    if not d.exists():
        print(f"{YEL}QUEUED / NOT STARTED{RST}: {d} does not exist")
        return
    st = json.loads((d / "status.json").read_text()) if (d / "status.json").exists() else {}
    res = d / "results.jsonl"
    written = found = nf = 0
    if res.exists():
        for line in res.open():
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            written += 1
            found += rec.get("outcome") == "found"
            nf += rec.get("outcome") == "not_found"
    err_lines = sum(1 for _ in (d / "errors.jsonl").open()) if (d / "errors.jsonl").exists() else 0
    idle = time.time() - res.stat().st_mtime if res.exists() else None
    total = st.get("total") or 0
    alive = pid_is_worker(st.get("pid"))

    if (d / "DONE").exists():
        state = f"{GRN}DONE{RST}"
    elif (d / "ABORTED").exists():
        state = f"{RED}FAILED / STOPPED: {(d / 'ABORTED').read_text().strip()}{RST}"
    elif alive and idle is not None and idle > STALL_AFTER_S:
        state = f"{YEL}STALLED? no new result for {fmt_dur(idle)}{RST}"
    elif alive:
        state = f"{GRN}RUNNING{RST} (pid {st.get('pid')})"
    else:
        state = f"{RED}STOPPED EARLY{RST}: worker not running and no DONE marker (resume with the same --tag)"
    print(f"state   {state}")

    pct = 100 * written / total if total else 0
    bar = "#" * int(pct / 2.5) + "." * (40 - int(pct / 2.5))
    print(f"answered [{bar}] {written:,}/{total:,} ({pct:.1f}%)   worker tally {st.get('answered', 0):,}")
    print(f"found {found:,}   not_found {nf:,}   "
          f"{(RED if err_lines else '')}errors logged {err_lines:,}{RST if err_lines else ''}   "
          f"consecutive errors now {st.get('consecutive_errors', 0)}")
    if "RUNNING" in state and st.get("eta_s"):
        print(f"rate {st['rate_per_s']:.2f}/s (last 200)   eta {fmt_dur(st['eta_s'])} ({clock(st['eta_s'])})   "
              f"idle {fmt_dur(idle or 0)}")
    else:
        print(f"no ETA shown (not running). Last worker update {st.get('updated', 'never')}")
    log = PROJECT / "logs" / "altmetric_enrichment.log"
    if log.exists():
        tail = log.read_text().splitlines()[-4:]
        for line in tail:
            print((RED if ("DENIED" in line or "STOP" in line or "error" in line.lower()) else "") + line[:150] + RST)


if __name__ == "__main__":
    main()
