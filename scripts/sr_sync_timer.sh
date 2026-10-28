#!/bin/bash
# Monthly Shark-References sync, run DAILY by the user timer sr-monthly-sync.timer
# (replaces the /etc/anacrontab entry, 2026-10-28).
#
# Why: anacron fired on 3 Oct 2026 at 07:48, recorded the month as done, and
# nothing ran: no sync log, no wrapper log. Most likely the data drive was not
# yet mounted 15 min after boot; the old wrapper then exited 0 and wrote its
# "skipping" line to a log ON that unmounted drive. 139 new papers waited a
# month. So this wrapper:
#   * keeps its own log and state OFF the data drive (~/.local/state/sr-sync/);
#   * waits up to 15 min for the drive, then FAILS (exit 1) rather than
#     exiting 0, so systemd marks the run failed and sr-monthly-sync-failure
#     alerts;
#   * decides "is a sync due?" from a success marker written only after the
#     sync exits 0, so a failed or skipped month is retried the next day
#     instead of waiting another 30 days.
set -u
PROJECT="/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
SCRIPT="$PROJECT/scripts/sync_shark_references.py"
STATE="${XDG_STATE_HOME:-$HOME/.local/state}/sr-sync"
LOG="$STATE/sr-sync-timer.log"
MARKER="$STATE/last_success"
DUE_DAYS=30
mkdir -p "$STATE"
say() { echo "$(date -Iseconds) $*" | tee -a "$LOG"; }

say "invoked"
if [ -f "$MARKER" ] && [ -n "$(find "$MARKER" -mtime -"$DUE_DAYS" 2>/dev/null)" ]; then
    say "NOTHING-TO-DO: last success $(cat "$MARKER"), under $DUE_DAYS days ago"
    exit 0
fi

for i in $(seq 1 30); do
    [ -f "$SCRIPT" ] && break
    sleep 30
done
if [ ! -f "$SCRIPT" ]; then
    say "FAIL: data drive not mounted after 15 min ($SCRIPT missing); will retry tomorrow"
    exit 1
fi

RUNLOG="$PROJECT/logs/sr_sync_timer_$(date +%Y%m%d_%H%M).log"
say "RUN: sync starting, log $RUNLOG"
/usr/bin/python3 "$SCRIPT" > "$RUNLOG" 2>&1
rc=$?
if [ "$rc" -eq 0 ]; then
    date -Iseconds > "$MARKER"
    say "OK: sync finished (exit 0); next due in $DUE_DAYS days"
else
    say "FAIL: sync exited $rc; see $RUNLOG; will retry tomorrow"
fi
exit "$rc"
