#!/bin/bash
# Wrapper for anacron: runs sync_shark_references.py as user simon
# Anacron runs as root, so we use su to drop privileges.

SCRIPT="/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel/scripts/sync_shark_references.py"

exec su simon -c "/usr/bin/python3 \"$SCRIPT\"" >> "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel/logs/sr_sync_cron.log" 2>&1
