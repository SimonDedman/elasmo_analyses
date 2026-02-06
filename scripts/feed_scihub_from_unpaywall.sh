#!/bin/bash
# Continuously feed Sci-Hub with Unpaywall failures

cd "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"

echo "=== Continuous Sci-Hub Feeder ==="
echo "Started: $(date)"
echo ""

LAST_COUNT=0

while true; do
    # Wait for current Sci-Hub to finish
    while pgrep -f "download_via_scihub_tor.py" > /dev/null; do
        sleep 30
    done
    
    # Check if Unpaywall is still running
    if ! pgrep -f "download_unpaywall.py" > /dev/null; then
        echo "$(date): Unpaywall finished, doing final Sci-Hub run..."
    fi
    
    # Generate new batch from latest Unpaywall failures
    NEW_COUNT=$(python3 << 'PYTHON'
import pandas as pd
from pathlib import Path

log = pd.read_csv('logs/unpaywall_download_log.csv')
failures = log[log['status'].isin(['not_open_access', 'failed'])].copy()
failures = failures[failures['doi'].notna()]

db = pd.read_parquet('outputs/literature_review.parquet')
db['doi_lower'] = db['doi'].str.lower()
failures['doi_lower'] = failures['doi'].str.lower()

db_info = db[['doi_lower', 'year', 'literature_id']].drop_duplicates(subset=['doi_lower'])
failures = failures.merge(db_info, on='doi_lower', how='left', suffixes=('', '_db'))

# Filter pre-2021
scihub_candidates = failures[failures['year'] < 2021].copy()

# Check what Sci-Hub already tried
scihub_log = Path('logs/scihub_tor_download_log.csv')
if scihub_log.exists():
    tried = pd.read_csv(scihub_log)
    tried_dois = set(tried['doi'].str.lower())
    scihub_candidates = scihub_candidates[~scihub_candidates['doi_lower'].isin(tried_dois)]

if len(scihub_candidates) > 0:
    output = scihub_candidates[['doi', 'literature_id_db', 'year']].rename(
        columns={'literature_id_db': 'literature_id'}
    )
    output.to_csv('outputs/scihub_from_unpaywall_failures.csv', index=False)
    
print(len(scihub_candidates))
PYTHON
)
    
    echo "$(date): Found $NEW_COUNT new papers for Sci-Hub"
    
    if [ "$NEW_COUNT" -gt 0 ]; then
        echo "Starting Sci-Hub for $NEW_COUNT papers..."
        python3 scripts/download_via_scihub_tor.py --input outputs/scihub_from_unpaywall_failures.csv 2>&1 | tee -a logs/scihub_continuous.log
    fi
    
    # If Unpaywall is done, exit
    if ! pgrep -f "download_unpaywall.py" > /dev/null; then
        echo "$(date): All done!"
        break
    fi
    
    sleep 60
done
