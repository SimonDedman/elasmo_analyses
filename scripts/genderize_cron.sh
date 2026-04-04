#!/bin/bash
# Daily genderize.io resolver — cron wrapper
# Runs the Python script and sends a desktop notification with the report.
#
# Crontab entry (installed automatically):
#   7 9 * * * /media/simon/data/Documents/Si\ Work/PostDoc\ Work/EEA/2025/Data\ Panel/scripts/genderize_cron.sh

PROJECT="/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
SCRIPT="$PROJECT/scripts/genderize_daily.py"
REPORT="$PROJECT/outputs/logs/genderize_latest_report.txt"

# Desktop notifications need DBUS session address
export DISPLAY=:0
export DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$(id -u)/bus"

# Run the resolver
python3 "$SCRIPT" 2>&1

# Send desktop notification with the report
if [ -f "$REPORT" ]; then
    BODY=$(cat "$REPORT")
    # Check for warnings
    if echo "$BODY" | grep -q "WARNING\|No new names\|Queried:    0"; then
        URGENCY="critical"
        ICON="dialog-warning"
    else
        URGENCY="normal"
        ICON="dialog-information"
    fi
    notify-send -u "$URGENCY" -i "$ICON" "Genderize Daily" "$BODY"
else
    notify-send -u critical -i dialog-error "Genderize Daily" "Script ran but no report file found"
fi
