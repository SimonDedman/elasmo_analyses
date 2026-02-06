#!/bin/bash
# Chain Unpaywall -> Sci-Hub download
# Waits for Unpaywall to finish, then runs Sci-Hub on remaining papers

cd "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"

echo "=========================================="
echo "CHAINED DOWNLOAD: Unpaywall -> Sci-Hub"
echo "=========================================="
echo "Started: $(date)"
echo ""

# Wait for Unpaywall to finish
echo "Waiting for Unpaywall to complete..."
while pgrep -f "download_unpaywall.py" > /dev/null; do
    sleep 60
    echo "  $(date '+%H:%M:%S') - Unpaywall still running..."
done

echo ""
echo "=========================================="
echo "UNPAYWALL COMPLETE - Starting Sci-Hub"
echo "=========================================="
echo "Time: $(date)"
echo ""

# Create list of DOIs that still need downloading (pre-2021 for Sci-Hub coverage)
python3 << 'PYTHON'
import pandas as pd
from pathlib import Path

print("Preparing Sci-Hub batch...")

# Load Unpaywall results
unpaywall_log = pd.read_csv('logs/unpaywall_download_log.csv')
successful_dois = set(unpaywall_log[unpaywall_log['status'] == 'success']['doi'].str.lower())
print(f"Unpaywall successes: {len(successful_dois):,}")

# Load the batch we sent to Unpaywall
batch = pd.read_csv('outputs/unpaywall_new_batch.csv')
batch['doi_lower'] = batch['doi'].str.lower()

# Find papers that Unpaywall didn't get
remaining = batch[~batch['doi_lower'].isin(successful_dois)].copy()
print(f"Remaining after Unpaywall: {len(remaining):,}")

# Filter to pre-2021 (Sci-Hub coverage)
# Need to get year info from main database
db = pd.read_parquet('outputs/literature_review.parquet')
db_years = db[['literature_id', 'year']].drop_duplicates()
remaining = remaining.merge(db_years, on='literature_id', how='left')

# Filter to papers before 2021
scihub_candidates = remaining[remaining['year'] < 2021].copy()
print(f"Pre-2021 papers for Sci-Hub: {len(scihub_candidates):,}")

# Save for Sci-Hub
if len(scihub_candidates) > 0:
    scihub_candidates[['doi', 'literature_id', 'title', 'year']].to_csv(
        'outputs/scihub_after_unpaywall.csv', index=False
    )
    print(f"Saved to outputs/scihub_after_unpaywall.csv")
else:
    print("No papers remaining for Sci-Hub")
PYTHON

# Check if there are papers to download
if [ -f "outputs/scihub_after_unpaywall.csv" ]; then
    COUNT=$(wc -l < outputs/scihub_after_unpaywall.csv)
    COUNT=$((COUNT - 1))  # Subtract header
    
    if [ "$COUNT" -gt 0 ]; then
        echo ""
        echo "Starting Sci-Hub download for $COUNT papers..."
        echo ""
        python3 scripts/download_via_scihub_tor.py \
            --input outputs/scihub_after_unpaywall.csv \
            --max-papers 5000 \
            2>&1 | tee logs/scihub_after_unpaywall.log
    else
        echo "No papers to download via Sci-Hub"
    fi
else
    echo "No Sci-Hub input file created"
fi

echo ""
echo "=========================================="
echo "CHAIN COMPLETE"
echo "=========================================="
echo "Finished: $(date)"
