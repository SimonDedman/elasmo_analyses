#!/bin/bash
# Monitor extraction completion and push to GitHub

DB_PATH="/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel/database/technique_taxonomy.db"
REPO_PATH="/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"

cd "$REPO_PATH"

echo "Monitoring extraction progress..."
echo "Started at: $(date)"

# Wait for extraction to complete (check every 5 minutes)
while true; do
    # Count processed papers
    PROCESSED=$(./venv/bin/python -c "
import sqlite3
conn = sqlite3.connect('$DB_PATH')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM extraction_log')
count = cursor.fetchone()[0]
conn.close()
print(count)
" 2>/dev/null)

    # Check if we've processed all 12,381 papers
    if [ "$PROCESSED" -ge 12381 ]; then
        echo "Extraction complete! Processed $PROCESSED papers"
        break
    fi

    echo "$(date): Processed $PROCESSED / 12,381 papers ($(echo "scale=1; $PROCESSED * 100 / 12381" | bc)%)"
    sleep 300  # Wait 5 minutes
done

echo "Waiting 30 seconds for final database writes..."
sleep 30

# Generate final statistics
echo "Generating final statistics..."
./venv/bin/python -c "
import sqlite3
conn = sqlite3.connect('$DB_PATH')
cursor = conn.cursor()

print('\n' + '='*60)
print('EXTRACTION COMPLETE - FINAL STATISTICS')
print('='*60)

cursor.execute('SELECT COUNT(*) FROM extraction_log')
print(f'Papers processed: {cursor.fetchone()[0]:,}')

cursor.execute('SELECT COUNT(*) FROM researchers')
print(f'Researchers extracted: {cursor.fetchone()[0]:,}')

cursor.execute('SELECT COUNT(*) FROM paper_authors')
print(f'Paper-author links: {cursor.fetchone()[0]:,}')

cursor.execute('SELECT COUNT(*) FROM researcher_disciplines')
print(f'Researcher disciplines: {cursor.fetchone()[0]:,}')

cursor.execute('SELECT COUNT(*) FROM researcher_techniques')
print(f'Researcher techniques: {cursor.fetchone()[0]:,}')

cursor.execute('SELECT COUNT(*) FROM collaborations')
print(f'Collaborations: {cursor.fetchone()[0]:,}')

print('='*60)
conn.close()
"

# Git operations
echo ""
echo "Pushing changes to GitHub..."

# Add all modified and new files
git add -A

# Create commit message
COMMIT_MSG="Researcher network extraction complete

- Fixed database schema issues (first_year, last_year, authors_found, etc.)
- Completed full extraction with researcher network data
- Added schema_fixes_applied.md documentation
- Updated OVERVIEW.md for GitHub

Extraction results:
- Papers processed: $(./venv/bin/python -c "import sqlite3; conn = sqlite3.connect('$DB_PATH'); cursor = conn.cursor(); cursor.execute('SELECT COUNT(*) FROM extraction_log'); print(cursor.fetchone()[0]); conn.close()")
- Researchers: $(./venv/bin/python -c "import sqlite3; conn = sqlite3.connect('$DB_PATH'); cursor = conn.cursor(); cursor.execute('SELECT COUNT(*) FROM researchers'); print(cursor.fetchone()[0]); conn.close()")

Ready for visualization and EEA 2025 presentation."

# Commit changes
git commit -m "$COMMIT_MSG"

# Push to GitHub
git push origin main

echo ""
echo "✅ All changes pushed to GitHub!"
echo "Completed at: $(date)"
