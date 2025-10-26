#!/bin/bash
# Stop the integrated download pipeline

PROJECT_DIR="/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
cd "$PROJECT_DIR"

echo "Stopping download pipeline..."

# Check if PID files exist
if [ -f logs/doi_hunter.pid ]; then
    DOI_HUNTER_PID=$(cat logs/doi_hunter.pid)
    if ps -p $DOI_HUNTER_PID > /dev/null 2>&1; then
        kill $DOI_HUNTER_PID
        echo "  ✓ Stopped DOI hunter (PID: $DOI_HUNTER_PID)"
    else
        echo "  ✗ DOI hunter (PID: $DOI_HUNTER_PID) not running"
    fi
    rm logs/doi_hunter.pid
else
    echo "  ✗ DOI hunter PID file not found"
fi

if [ -f logs/scihub_downloader.pid ]; then
    SCIHUB_PID=$(cat logs/scihub_downloader.pid)
    if ps -p $SCIHUB_PID > /dev/null 2>&1; then
        kill $SCIHUB_PID
        echo "  ✓ Stopped Sci-Hub downloader (PID: $SCIHUB_PID)"
    else
        echo "  ✗ Sci-Hub downloader (PID: $SCIHUB_PID) not running"
    fi
    rm logs/scihub_downloader.pid
else
    echo "  ✗ Sci-Hub downloader PID file not found"
fi

echo ""
echo "Pipeline stopped."
