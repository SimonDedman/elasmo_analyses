#!/bin/bash
# Start the Paper Download Web Interface
#
# Usage: ./run.sh
#
# This starts a local web server at http://localhost:5000

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"

cd "$SCRIPT_DIR"

echo "=========================================="
echo "  Paper Download Web Interface"
echo "  EEA Data Panel 2025"
echo "=========================================="
echo ""
echo "Starting server..."
echo "Open http://localhost:5000 in your browser"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Activate virtual environment and run
"$PROJECT_DIR/venv/bin/python" app.py
