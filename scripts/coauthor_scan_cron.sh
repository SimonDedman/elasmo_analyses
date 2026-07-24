#!/bin/bash
# Daily sweep of the coauthor drop folders under database/others_libraries/.
#
# Files matched against the corpus are copied into SharkPapers and the source is
# deleted, but only once a byte-verified library copy exists (see
# verified_in_library in scan_coauthor_libraries.py). Anything that fails to
# match is left in place and listed in outputs/coauthor_unresolved_<date>.xlsx —
# per the project's guiding principle those are matching failures, not new
# papers, so they need a human rather than automatic staging.
#
# Runs from the user crontab at 16:00 local time, so it follows the Pacific
# clock: PDT in summer, PST in winter.

PROJECT="/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
SCRIPT="$PROJECT/scripts/scan_coauthor_libraries.py"
LOG="$PROJECT/logs/coauthor_scan_cron.log"

# The data drive is mounted with nofail, so it may be absent. Bail quietly and
# let tomorrow's run pick things up rather than erroring into the log daily.
if [ ! -f "$SCRIPT" ]; then
    echo "$(date -Iseconds) coauthor-scan: script not found (drive unmounted?), skipping" >> "$LOG" 2>&1
    exit 0
fi

mkdir -p "$PROJECT/logs"
echo "$(date -Iseconds) coauthor-scan: starting" >> "$LOG"

# --clicks attributes deliveries to whoever fetched them; it needs network, and
# the script degrades gracefully to no attribution if the endpoint is down.
/usr/bin/python3 "$SCRIPT" --delete-ingested --clicks >> "$LOG" 2>&1
rc=$?

echo "$(date -Iseconds) coauthor-scan: finished rc=$rc" >> "$LOG"
exit $rc
