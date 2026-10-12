#!/bin/bash
# Daily ingest of every drop folder, then publish the todo list (16:00, user crontab).
#
# Since 2026-10-12 this runs scripts/daily_drop_ingest.py (the standard practice in
# docs/acquisition/drop_folder_ingest_practice.md): audit with an identity test, file,
# verify, credit, sort problems into named subfolders with a traced cause, then commit
# the todo list, merge it to main and push, so GitHub Pages never lags the library.
# It replaced scan_coauthor_libraries.py --delete-ingested --clicks, which filed
# without an identity test and closed rows only on this machine.
#
# Runs from the user crontab at 16:00 local time, so it follows the Pacific clock.

PROJECT="/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
SCRIPT="$PROJECT/scripts/daily_drop_ingest.py"
LOG="$PROJECT/logs/coauthor_scan_cron.log"

# The data drive is mounted with nofail, so it may be absent. Bail quietly and
# let tomorrow's run pick things up rather than erroring into the log daily.
if [ ! -f "$SCRIPT" ]; then
    echo "$(date -Iseconds) daily-ingest: script not found (drive unmounted?), skipping" >> "$LOG" 2>&1
    exit 0
fi

mkdir -p "$PROJECT/logs"
echo "$(date -Iseconds) daily-ingest: starting" >> "$LOG"
cd "$PROJECT" || exit 1

# cron has no session bus; systemd-run --user needs these to cap the job's memory
export XDG_RUNTIME_DIR="/run/user/$(id -u)"
export DBUS_SESSION_BUS_ADDRESS="unix:path=$XDG_RUNTIME_DIR/bus"
if systemd-run --user --scope --quiet -p MemoryMax=12G -p MemoryHigh=10G true 2>/dev/null; then
    systemd-run --user --scope --quiet -p MemoryMax=12G -p MemoryHigh=10G \
        /usr/bin/python3 "$SCRIPT" >> "$LOG" 2>&1
else
    echo "$(date -Iseconds) daily-ingest: no user systemd, running WITHOUT a memory cap" >> "$LOG"
    /usr/bin/python3 "$SCRIPT" >> "$LOG" 2>&1
fi
rc=$?

echo "$(date -Iseconds) daily-ingest: finished rc=$rc (summary: outputs/daily_ingest_$(date +%F).json)" >> "$LOG"
exit $rc
