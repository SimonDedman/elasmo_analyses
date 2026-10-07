#!/bin/sh
# Bring the SharkOracle RAG index in line with the PDF library.
#
#   sh scripts/rag/sync_index.sh            incremental: new texts are embedded onto
#                                           the live index in outputs/rag
#   sh scripts/rag/sync_index.sh --rebuild  full: a fresh index is built in
#                                           outputs/rag.new and swapped in when done
#                                           (the live index serves throughout)
#
# Steps: prepass (one body text per record, from outputs/pdf_id_map.csv, unbacked
# texts quarantined) -> embed (CPU, the slow step) -> filter + author sidecar ->
# FTS/BM25 sidecar when scripts/rag/build_bm25.py exists.
# Called as the last step of scripts/refresh_pdf_map_and_extract.sh, so every
# filing batch reaches the index without anyone remembering to run it.
#
# Watch:  watch -n 60 -t -c 'cd "<project dir>" && python3 scripts/rag/progress.py'
# State:  outputs/rag/sync_state (STARTED / STEP n / DONE / FAILED lines)
set -e
cd "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
FCLIP=/home/simon/.venvs/fashion-clip/bin/python
MODE=incremental
[ "$1" = "--rebuild" ] && MODE=rebuild
LIVE=outputs/rag
NEW=outputs/rag.new
STATE=$LIVE/sync_state
mkdir -p "$LIVE" logs outputs/rag_state
# one sync at a time: a second one would rerun the prepass under a running embed
# and overwrite the state file the monitor and the post-rebuild watcher read
exec 9>outputs/rag_state/sync.lock
if ! flock -n 9; then
  echo "another sync_index.sh is running (outputs/rag_state/sync.lock); not starting" >&2
  exit 75
fi
echo "STARTED $MODE $(date '+%Y-%m-%d %H:%M:%S %Z')" > "$STATE"
trap 'echo "FAILED step=$STEP $(date "+%Y-%m-%d %H:%M:%S %Z")" >> "$STATE"' EXIT

STEP=1; echo "STEP 1/4 prepass $(date '+%H:%M:%S %Z')" >> "$STATE"
python3 scripts/validation/fable_corpus_prepass.py --purge-unbacked --worklist-to-next --quiet

STEP=2; echo "STEP 2/4 embed $(date '+%H:%M:%S %Z')" >> "$STATE"
if [ "$MODE" = rebuild ]; then
  rm -rf "$NEW"; mkdir -p "$NEW"
  RAG_OUT_DIR="$NEW" nice -n 15 "$FCLIP" scripts/rag/build_from_cache.py --fresh --checkpoint-every 500
else
  nice -n 15 "$FCLIP" scripts/rag/build_from_cache.py --checkpoint-every 500
fi

STEP=3; echo "STEP 3/4 sidecars $(date '+%H:%M:%S %Z')" >> "$STATE"
OUT=$LIVE; [ "$MODE" = rebuild ] && OUT=$NEW
RAG_OUT_DIR="$OUT" "$FCLIP" scripts/rag/build_filters.py
if [ -f scripts/rag/build_bm25.py ]; then
  RAG_OUT_DIR="$OUT" "$FCLIP" scripts/rag/build_bm25.py
fi

STEP=4; echo "STEP 4/4 publish $(date '+%H:%M:%S %Z')" >> "$STATE"
if [ "$MODE" = rebuild ]; then
  # keep the sync log with the live dir; the previous index is kept once, dated
  cp "$STATE" "$NEW/sync_state"
  PREV="outputs/rag.prev_$(date +%Y%m%d_%H%M)"
  mv "$LIVE" "$PREV" && mv "$NEW" "$LIVE"
  STATE=$LIVE/sync_state
  echo "previous index kept at $PREV (delete when the new one is confirmed)" >> "$STATE"
fi
trap - EXIT
echo "DONE $MODE $(date '+%Y-%m-%d %H:%M:%S %Z')" >> "$STATE"
