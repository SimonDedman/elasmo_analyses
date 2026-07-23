#!/usr/bin/env bash
# Live progress for an ocr_library.py run. Usage:
#   watch -n 15 bash scripts/ocr_progress.sh [logfile] [total]
# Defaults target the resolved large re-OCR run.
LOG="${1:-logs/ocr_library_log_non_extractable_relang_large_resolved.txt}"
TOTAL="${2:-175}"

done=$(grep -c '^OK' "$LOG" 2>/dev/null); done=${done:-0}
fail=$(grep -c '^FAIL' "$LOG" 2>/dev/null); fail=${fail:-0}
echo "done ${done}/${TOTAL}   fail ${fail}"

# Current file: select the ocrmypdf process by NAME (-C), not by grepping
# args — its gs/tesseract workers all mention the ocrmypdf temp dir and
# would otherwise match. -ww forces full-width output (without it ps
# truncates the args to terminal width, so the long path gets cut and the
# sed fell back to just the first few chars). Space-safe path extraction.
cur=$(ps -ww -C ocrmypdf -o args= 2>/dev/null | head -1 \
      | sed -E 's/.*--quiet (.+\.pdf) .+\.ocr\.tmp\.pdf$/\1/; s|.*/||')
echo "current: ${cur:-(between files)}"

# How long the current file has been processing (spot a stuck file).
et=$(ps -o etime= -C ocrmypdf 2>/dev/null | head -1 | tr -d ' ')
echo "time on current file: ${et:-–}"
