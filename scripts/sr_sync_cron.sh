#!/bin/bash
# Wrapper for anacron: runs sync_shark_references.py as user simon.
# Anacron runs as root; we drop privileges with runuser (NOT su) because
# `su simon` triggers PAM/Howdy face-auth, which fails in anacron's
# non-interactive, no-camera context (exit 127 => job never ran). runuser
# does not gate the root->user transition on PAM auth. (Fixed 2026-07-01.)

PROJECT="/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
SCRIPT="$PROJECT/scripts/sync_shark_references.py"
LOG="$PROJECT/logs/sr_sync_cron.log"

# Only run once the data drive is actually mounted (nofail fstab means it may
# not be ready at early boot); bail quietly otherwise so anacron retries later.
if [ ! -f "$SCRIPT" ]; then
    echo "$(date -Iseconds) sr-sync: script not found (drive unmounted?), skipping" >> "$LOG" 2>&1
    exit 0
fi

exec runuser -u simon -- /usr/bin/python3 "$SCRIPT" >> "$LOG" 2>&1
