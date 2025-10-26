#!/bin/bash
# Integrated Download Pipeline Orchestrator
# Runs DOI hunter and Sci-Hub downloader in parallel

PROJECT_DIR="/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
cd "$PROJECT_DIR"

# Create logs directory
mkdir -p logs

# Log files
DOI_HUNTER_LOG="logs/doi_hunter_daemon.log"
SCIHUB_LOG="logs/scihub_downloader_daemon.log"

echo "========================================"
echo "INTEGRATED DOWNLOAD PIPELINE"
echo "========================================"
echo ""
echo "Starting both processes in background..."
echo ""
echo "Log files:"
echo "  DOI Hunter:     $DOI_HUNTER_LOG"
echo "  Sci-Hub:        $SCIHUB_LOG"
echo ""

# Start DOI hunter in background
echo "Starting DOI hunter..."
nohup ./venv/bin/python scripts/doi_hunter_daemon.py > "$DOI_HUNTER_LOG" 2>&1 &
DOI_HUNTER_PID=$!
echo "  ✓ DOI hunter started (PID: $DOI_HUNTER_PID)"

# Wait a few seconds
sleep 3

# Start Sci-Hub downloader in background
echo "Starting Sci-Hub downloader..."
nohup ./venv/bin/python scripts/scihub_downloader_daemon.py > "$SCIHUB_LOG" 2>&1 &
SCIHUB_PID=$!
echo "  ✓ Sci-Hub downloader started (PID: $SCIHUB_PID)"

# Save PIDs
echo "$DOI_HUNTER_PID" > logs/doi_hunter.pid
echo "$SCIHUB_PID" > logs/scihub_downloader.pid

echo ""
echo "========================================"
echo "BOTH PROCESSES RUNNING"
echo "========================================"
echo ""
echo "Process IDs:"
echo "  DOI Hunter:     $DOI_HUNTER_PID"
echo "  Sci-Hub:        $SCIHUB_PID"
echo ""
echo "Monitor with:"
echo "  tail -f $DOI_HUNTER_LOG"
echo "  tail -f $SCIHUB_LOG"
echo ""
echo "View progress:"
echo "  ./venv/bin/python scripts/monitor_download_progress.py"
echo ""
echo "Stop processes:"
echo "  kill $DOI_HUNTER_PID $SCIHUB_PID"
echo ""
echo "Or use:"
echo "  bash scripts/stop_pipeline.sh"
echo ""
