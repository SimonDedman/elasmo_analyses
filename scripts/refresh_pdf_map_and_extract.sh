#!/bin/sh
# Rebuild the literature_id -> PDF map, then re-extract every corpus row whose PDF
# assignment changed. Run this after any batch of filings: newly filed PDFs are
# invisible to extraction until the map knows about them.
#
#   nohup sh scripts/refresh_pdf_map_and_extract.sh > logs/refresh_pdf_map.log 2>&1 &
#
# Writes: outputs/pdf_id_map.csv, pdf_id_map_changes.csv, pdf_id_map_coverage.json,
#         outputs/reextract_<date>.csv, and a DONE or FAILED marker beside the log.
# Step 4 then syncs the RAG text cache + index (scripts/rag/sync_index.sh).
set -e
cd "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
STAMP=$(date +%Y-%m-%d)
MARK="logs/refresh_pdf_map.state"
echo "STARTED $(date '+%Y-%m-%d %H:%M:%S %Z')" > "$MARK"
# any early exit leaves a FAILED line, so a stalled chain is never mistaken for a finished one
trap 'echo "FAILED $(date "+%Y-%m-%d %H:%M:%S %Z") (see logs/refresh_pdf_map.log)" >> "$MARK"' EXIT

echo "== 0/4 corpus rows for every master record =="
echo "STEP 0/4 corpus rows $(date '+%H:%M:%S %Z')" >> "$MARK"
# A record filed by the drop-folder scan or the cascade has no corpus row unless
# this runs: the map and the extraction below only see records in the parquet.
rm -f outputs/pdf_id_map_changes_backfill.csv
python3 scripts/backfill_corpus_rows.py --apply

echo "== 1/4 rebuilding the id -> PDF map =="
echo "STEP 1/4 map $(date '+%H:%M:%S %Z')" >> "$MARK"
python3 scripts/build_pdf_id_map.py --verify 200

echo "== 2/4 listing rows whose PDF assignment moved =="
echo "STEP 2/4 diff $(date '+%H:%M:%S %Z')" >> "$MARK"
python3 - "$STAMP" <<'PYEOF'
import csv, sys
import pandas as pd
sys.path.insert(0, "scripts")
import extract_schema_columns as X

stamp = sys.argv[1]
# build_pdf_id_map.py diffs against the previous map, so this IS the re-extract set
changed = {r["literature_id"] for r in csv.DictReader(open("outputs/pdf_id_map_changes.csv"))}
# step 0 rebuilt the map too when it added corpus rows; its diff holds the real changes
import os
if os.path.exists("outputs/pdf_id_map_changes_backfill.csv"):
    changed |= {r["literature_id"] for r in csv.DictReader(open("outputs/pdf_id_map_changes_backfill.csv"))}
corpus = {str(v).split(".")[0] for v in
          pd.read_parquet(X.INPUT_PARQUET, columns=["literature_id"]).literature_id}
todo = sorted(changed & corpus)
pd.DataFrame({"literature_id": todo}).to_csv(f"outputs/reextract_{stamp}.csv", index=False)
print(f"rows whose PDF assignment moved: {len(changed):,}; of those in the corpus: {len(todo):,}")
PYEOF
N=$(($(wc -l < "outputs/reextract_${STAMP}.csv") - 1))
echo "== 3/4 re-extracting $N rows =="
echo "STEP 3/4 extract $N rows $(date '+%H:%M:%S %Z')" >> "$MARK"
if [ "$N" -gt 0 ]; then
  python3 scripts/extract_incremental.py "outputs/reextract_${STAMP}.csv"
else
  echo "nothing to re-extract"
fi

python3 scripts/report_corpus_stats.py --json-only

echo "== 4/4 syncing the RAG index to the library =="
echo "STEP 4/4 rag sync $(date '+%H:%M:%S %Z')" >> "$MARK"
# texts for newly filed PDFs, embedded onto the live index; hours only when
# many papers were filed (CPU embedding), seconds when nothing changed.
# Capped so the embed, not the desktop, pays for any memory overrun.
systemd-run --user --scope --quiet -p MemoryMax=12G -p MemoryHigh=10G sh scripts/rag/sync_index.sh

trap - EXIT
echo "DONE $(date '+%Y-%m-%d %H:%M:%S %Z')" >> "$MARK"
echo "== finished =="
