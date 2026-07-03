#!/bin/bash
# Daily genderize.io resolver — anacron wrapper
# Anacron runs as root, so we use su to drop privileges.
#
# Anacrontab entry (installed automatically):
#   1  10  genderize-daily  /media/simon/data/Documents/Si\ Work/PostDoc\ Work/EEA/2025/Data\ Panel/scripts/genderize_cron.sh

PROJECT="/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
SCRIPT="$PROJECT/scripts/genderize_daily.py"
REPORT="$PROJECT/outputs/logs/genderize_latest_report.txt"
LOG="$PROJECT/outputs/logs/genderize_cron.log"

# Run the resolver as simon
su simon -c "/usr/bin/python3 \"$SCRIPT\"" >> "$LOG" 2>&1

# Desktop notification (best effort — may fail if no graphical session)
su simon -c "
    export DISPLAY=:0
    export DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/\$(id -u)/bus'
    if [ -f '$REPORT' ]; then
        BODY=\$(cat '$REPORT')
        if echo \"\$BODY\" | grep -q 'WARNING\|No new names\|Queried:    0'; then
            URGENCY='critical'; ICON='dialog-warning'
        else
            URGENCY='normal'; ICON='dialog-information'
        fi
        notify-send -u \"\$URGENCY\" -i \"\$ICON\" 'Genderize Daily' \"\$BODY\" 2>/dev/null
    fi
" 2>/dev/null

