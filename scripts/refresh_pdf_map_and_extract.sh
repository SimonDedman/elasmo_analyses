#!/bin/sh
# Rebuild the literature_id -> PDF map, then re-extract every corpus row whose PDF
# assignment changed. Run this after any batch of filings: newly filed PDFs are
# invisible to extraction until the map knows about them.
#
#   nohup sh scripts/refresh_pdf_map_and_extract.sh > logs/refresh_pdf_map.log 2>&1 &
#
# Writes: outputs/pdf_id_map.csv, pdf_id_map_changes.csv, pdf_id_map_coverage.json,
#         outputs/reextract_<date>.csv, and a DONE or FAILED marker beside the log.
set -e
cd "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
STAMP=$(date +%Y-%m-%d)
MARK="logs/refresh_pdf_map.state"
echo "STARTED $(date '+%Y-%m-%d %H:%M:%S %Z')" > "$MARK"

echo "== 1/3 rebuilding the id -> PDF map =="
echo "STEP 1/3 map $(date '+%H:%M:%S %Z')" >> "$MARK"
python3 scripts/build_pdf_id_map.py --verify 200

echo "== 2/3 listing rows whose PDF assignment moved =="
echo "STEP 2/3 diff $(date '+%H:%M:%S %Z')" >> "$MARK"
python3 - "$STAMP" <<'PYEOF'
import csv, sys
import pandas as pd
sys.path.insert(0, "scripts")
import extract_schema_columns as X

stamp = sys.argv[1]
# build_pdf_id_map.py diffs against the previous map, so this IS the re-extract set
changed = {r["literature_id"] for r in csv.DictReader(open("outputs/pdf_id_map_changes.csv"))}
corpus = {str(v).split(".")[0] for v in
          pd.read_parquet(X.INPUT_PARQUET, columns=["literature_id"]).literature_id}
todo = sorted(changed & corpus)
pd.DataFrame({"literature_id": todo}).to_csv(f"outputs/reextract_{stamp}.csv", index=False)
print(f"rows whose PDF assignment moved: {len(changed):,}; of those in the corpus: {len(todo):,}")
PYEOF
N=$(($(wc -l < "outputs/reextract_${STAMP}.csv") - 1))
echo "== 3/3 re-extracting $N rows =="
echo "STEP 3/3 extract $N rows $(date '+%H:%M:%S %Z')" >> "$MARK"
if [ "$N" -gt 0 ]; then
  python3 scripts/extract_incremental.py "outputs/reextract_${STAMP}.csv"
else
  echo "nothing to re-extract"
fi

python3 scripts/report_corpus_stats.py --json-only
echo "DONE $(date '+%Y-%m-%d %H:%M:%S %Z')" >> "$MARK"
echo "== finished =="
