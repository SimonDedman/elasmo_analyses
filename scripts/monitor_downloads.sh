#!/bin/bash
# Live monitoring dashboard for download processes

while true; do
    clear
    echo "================================================================================"
    echo "📥 SHARK PAPER DOWNLOAD MONITOR"
    echo "================================================================================"
    echo "Updated: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""

    # Check running processes
    echo "🔄 RUNNING PROCESSES:"
    echo "--------------------------------------------------------------------------------"

    IUCN_PID=$(ps aux | grep "download_iucn_browser.py" | grep -v grep | awk '{print $2}')
    SCIHUB_PID=$(ps aux | grep "download_new_dois_scihub.py" | grep -v grep | awk '{print $2}')

    if [ -n "$IUCN_PID" ]; then
        echo "✅ IUCN Download        PID: $IUCN_PID"
    else
        echo "❌ IUCN Download        STOPPED"
    fi

    if [ -n "$SCIHUB_PID" ]; then
        echo "✅ Sci-Hub Download     PID: $SCIHUB_PID"
    else
        echo "❌ Sci-Hub Download     STOPPED"
    fi

    echo ""
    echo "📊 PROGRESS:"
    echo "--------------------------------------------------------------------------------"

    # IUCN Progress
    if [ -f logs/iucn_full_run_restart.log ]; then
        IUCN_PROGRESS=$(tail -1 logs/iucn_full_run_restart.log | grep -oP 'Downloading:\s+\K\d+%')
        IUCN_COUNT=$(tail -1 logs/iucn_full_run_restart.log | grep -oP 'Downloading:\s+\d+%\|[^|]+\|\s+\K\d+')
        if [ -n "$IUCN_PROGRESS" ]; then
            echo "🌊 IUCN Red List:       $IUCN_PROGRESS ($IUCN_COUNT/1,088 species)"
        else
            echo "🌊 IUCN Red List:       Starting..."
        fi
    fi

    # Sci-Hub Progress
    if [ -f logs/scihub_new_dois_run.log ]; then
        SCIHUB_PROGRESS=$(tail -1 logs/scihub_new_dois_run.log | grep -oP 'Downloading:\s+\K\d+%')
        SCIHUB_COUNT=$(tail -1 logs/scihub_new_dois_run.log | grep -oP 'Downloading:\s+\d+%\|[^|]+\|\s+\K\d+')
        if [ -n "$SCIHUB_PROGRESS" ]; then
            echo "📚 Sci-Hub Download:    $SCIHUB_PROGRESS ($SCIHUB_COUNT/446 DOIs)"
        else
            echo "📚 Sci-Hub Download:    Starting..."
        fi
    fi

    echo ""
    echo "📈 RECENT ACTIVITY (last 5 lines):"
    echo "--------------------------------------------------------------------------------"

    if [ -f logs/iucn_full_run_restart.log ]; then
        echo "🌊 IUCN:"
        tail -5 logs/iucn_full_run_restart.log | grep -E "(Downloaded|Error|Progress saved)" | tail -3
    fi

    echo ""

    if [ -f logs/scihub_new_dois_run.log ]; then
        echo "📚 Sci-Hub:"
        tail -5 logs/scihub_new_dois_run.log | grep -E "(Downloaded|not_found|Error|Progress saved)" | tail -3
    fi

    echo ""
    echo "================================================================================"
    echo "Press Ctrl+C to exit"
    echo "Refreshing in 10 seconds..."
    echo "================================================================================"

    sleep 10
done
