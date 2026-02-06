#!/bin/bash
#
# chain_after_inter_research.sh
#
# Wait for the Inter-Research downloader to finish, then launch the batch proxy downloader.
# This allows downloading from all remaining publishers in a single browser session.
#
# Usage:
#   ./scripts/chain_after_inter_research.sh
#

cd "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"

echo "=========================================="
echo "CHAINED BATCH DOWNLOADER"
echo "=========================================="
echo "Waiting for Inter-Research download to complete..."
echo ""

# Find the Inter-Research process
IR_PID=$(pgrep -f "download_inter_research.py")

if [ -n "$IR_PID" ]; then
    echo "Found Inter-Research process (PID: $IR_PID)"
    echo "Monitoring... Press Ctrl+C to cancel waiting."
    echo ""

    # Wait for the process to finish
    while kill -0 "$IR_PID" 2>/dev/null; do
        # Show a progress indicator
        PAPERS_DONE=$(grep -c "OK\|EXISTS\|FAIL\|UNAVAILABLE" logs/inter_research_*.log 2>/dev/null | tail -1 || echo "?")
        echo -ne "\r[$(date +%H:%M:%S)] Inter-Research still running... (check log for progress)    "
        sleep 10
    done

    echo ""
    echo ""
    echo "=========================================="
    echo "Inter-Research download COMPLETE!"
    echo "=========================================="
    echo ""

    # Small delay to ensure cleanup
    sleep 2
else
    echo "No Inter-Research process found running."
    echo "Either it has already finished, or hasn't started yet."
    echo ""
fi

echo "Launching batch proxy downloader for remaining publishers..."
echo "(Taylor & Francis, Royal Society, JEB, Cambridge, Nature, Oxford)"
echo ""
echo "=========================================="
echo ""

# Launch the batch downloader
# Using --visible so user can see browser and login
./venv/bin/python scripts/download_all_proxy.py

echo ""
echo "=========================================="
echo "ALL DOWNLOADS COMPLETE"
echo "=========================================="
