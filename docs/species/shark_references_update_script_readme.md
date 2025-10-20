---
editor_options:
  markdown:
    wrap: 72
---

# Shark-References Species Database - Incremental Update Script

**Script:** `scripts/update_shark_references_species.py`
**Purpose:** Check for new species and update the local database without re-scraping all 1,300+ species
**Created:** 2025-10-13

---

## Overview

The incremental update script allows you to efficiently check for new species added to Shark-References since your last extraction, without having to re-scrape the entire database.

**Benefits:**
- ⚡ **Fast:** Only extracts new species (not all 1,311)
- 🔄 **Incremental:** Compares online list with local database
- 📊 **Reports:** Generates detailed report of changes
- 🛡️ **Safe:** Preserves existing data, only adds new species
- ⏱️ **Efficient:** Typical update takes 5-10 minutes (vs 65+ for full scrape)

---

## Usage

### Basic Update (Recommended)

Check for new species and update database:

```bash
cd "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
python3 scripts/update_shark_references_species.py
```

### Full Re-scrape

Force complete re-extraction of all species:

```bash
python3 scripts/update_shark_references_species.py --full
```

### Custom Delay

Adjust delay between requests (default 3 seconds):

```bash
python3 scripts/update_shark_references_species.py --delay 5
```

### Help

Show all available options:

```bash
python3 scripts/update_shark_references_species.py --help
```

---

## How It Works

### 1. Load Existing Database

Script reads your current species list:
```
data/shark_references_species_list.csv
```

If file doesn't exist, performs full extraction.

### 2. Fetch Online Species List

Scrapes all 26 alphabetical pages (A-Z) from Shark-References to get current species list.

**Time:** ~2 minutes (26 pages × 3 seconds)

### 3. Compare Lists

Identifies three categories:
- **New species:** Online but not in local database
- **Removed species:** In local database but not online (rare)
- **Unchanged species:** Present in both

### 4. Extract New Species Only

Only scrapes detailed information for new species.

**Example:**
- Last extraction: 1,311 species
- Current online: 1,315 species
- **Only extract 4 new species** (~12 seconds)

### 5. Update Database Files

Saves updated files:
- `data/shark_references_species_list.csv` (updated species list)
- `data/shark_species_detailed_complete.csv` (merged old + new data)
- `data/shark_species_update_report.txt` (human-readable summary)

---

## Output Files

### Species List (Updated)
**File:** `data/shark_references_species_list.csv`

**Columns:**
- `binomial` - Genus species (e.g., "Carcharodon carcharias")
- `binomial_url` - URL-safe format (e.g., "Carcharodon-carcharias")
- `genus` - Genus only
- `species` - Species epithet only
- `url` - Full URL to species page
- `letter` - Alphabetical category (A-Z)
- `date_checked` - Date of last check (YYYY-MM-DD)

### Detailed Species Data (Updated)
**File:** `data/shark_species_detailed_complete.csv`

**Columns:**
- All columns from species list PLUS:
- `class`, `subclass`, `superorder`, `order`, `family` - Taxonomic hierarchy
- `common_name_primary` - Primary English common name
- `common_names_json` - All common names with languages (JSON-like string)
- `distribution` - Geographic distribution text
- `habitat` - Habitat description with depth range
- `size_weight_age` - Maximum size, weight, age data
- `biology` - Reproductive mode, diet, behavior
- `short_description` - Brief species overview
- `human_uses` - Fisheries, conservation status
- `remarks` - Taxonomic notes
- `date_extracted` - Date detailed data was extracted

### Update Report (New)
**File:** `data/shark_species_update_report.txt`

**Contents:**
```
================================================================================
Shark-References Species Database Update Report
================================================================================
Date: 2025-10-13 15:30:45

SUMMARY
--------------------------------------------------------------------------------
New species found:        4
Removed species:          0
Unchanged species:        1311
Errors during extraction: 0
Total species now:        1315

NEW SPECIES
--------------------------------------------------------------------------------
  + Acroteriobatus newcombei
  + Bathyraja ishiharai
  + Callorhinchus milii
  + Dipturus australis

================================================================================
```

---

## When to Run Updates

### Recommended Schedule

**Quarterly (every 3 months):**
- Shark-References is actively maintained
- New species described regularly
- Taxonomic revisions occur

**Before major milestones:**
- Conference presentations
- Database publication
- Analysis updates

**After taxonomic events:**
- New species descriptions published
- Major taxonomic revisions
- Nomenclature updates

### How to Schedule

#### Linux/Mac (cron)

Add to crontab for quarterly updates:

```bash
# Edit crontab
crontab -e

# Add this line (runs 1st of every quarter at 2am)
0 2 1 */3 * cd "/path/to/project" && python3 scripts/update_shark_references_species.py >> logs/update.log 2>&1
```

#### Manual Tracking

Create a reminder file:

```bash
echo "Last updated: $(date)" > data/last_species_update.txt
```

---

## Example Update Scenarios

### Scenario 1: Few New Species (Typical)

**Situation:** 2-3 new species since last extraction

```bash
$ python3 scripts/update_shark_references_species.py
```

**Output:**
```
================================================================================
Shark-References Species Database Update
================================================================================
Start time: 2025-10-13 15:30:00

Loaded 1311 existing species from local database
Fetching current species list from Shark-References...
  Fetching letter A... 106 species
  [... letters B-Y ...]
  Fetching letter Z... 11 species
Total online species: 1313

COMPARISON RESULTS
--------------------------------------------------------------------------------
New species:       2
Removed species:   0
Unchanged species: 1311

Extracting details for 2 new species...
Estimated time: ~0.1 minutes

[1/2] Bathyraja ishiharai... OK
[2/2] Dipturus australis... OK

Saving updated database...
  Updated: data/shark_references_species_list.csv
  Updated: data/shark_species_detailed_complete.csv
  Report: data/shark_species_update_report.txt

Update complete!
Successfully updated: 2 new species
Errors: 0 species

End time: 2025-10-13 15:32:15
================================================================================
```

**Time:** ~2-3 minutes

### Scenario 2: No Changes

**Situation:** Database already up to date

```bash
$ python3 scripts/update_shark_references_species.py
```

**Output:**
```
================================================================================
Shark-References Species Database Update
================================================================================
[... comparison ...]

COMPARISON RESULTS
--------------------------------------------------------------------------------
New species:       0
Removed species:   0
Unchanged species: 1311

No changes detected. Database is up to date!
================================================================================
```

**Time:** ~2 minutes (only checks list, no extraction)

### Scenario 3: Major Taxonomic Revision

**Situation:** 20+ new species (rare, but possible after major revision)

```bash
$ python3 scripts/update_shark_references_species.py
```

**Time:** ~2 minutes (list) + ~1 minute (20 species × 3 sec) = **3 minutes total**

Still much faster than full re-scrape (65+ minutes)!

---

## Troubleshooting

### Error: "No existing species list found"

**Cause:** First run or `shark_references_species_list.csv` missing

**Solution:** Script automatically performs full extraction. This is expected behavior.

### Error: HTTP errors or timeouts

**Cause:** Network issues or Shark-References temporarily unavailable

**Solutions:**
1. **Wait and retry:** Website may be temporarily down
2. **Increase delay:** `python3 scripts/update_shark_references_species.py --delay 10`
3. **Check network:** Verify internet connection

### Warning: Species removed from database

**Cause:** Taxonomic revision, synonym consolidation, or website changes

**Action:** Review `shark_species_update_report.txt` for details. Removed species may have been:
- Synonymized (merged with another species)
- Reclassified to different genus
- Temporarily removed for revision

**Follow-up:** Check Shark-References website manually for explanation.

### Progress file not updating

**Cause:** Extraction in progress, haven't reached 50-species checkpoint yet

**Check status:** Progress saved every 50 species

---

## Integration with Project Workflow

### After Running Update

1. **Review report:**
   ```bash
   cat data/shark_species_update_report.txt
   ```

2. **Check for SQL updates needed:**
   If new species found, regenerate SQL species columns:
   ```bash
   Rscript scripts/generate_species_sql.R
   ```

3. **Update database schema:**
   ```bash
   # Apply new species columns to database
   duckdb database.duckdb < sql/06_add_species_columns.sql
   ```

4. **Commit changes:**
   ```bash
   git add data/shark_references_species_list.csv
   git add data/shark_species_detailed_complete.csv
   git add data/shark_species_update_report.txt
   git commit -m "Update species database: +X new species"
   ```

---

## Script Logic Flow

```
START
  ↓
Load existing species list (if exists)
  ↓
Fetch online species list (26 pages, ~2 min)
  ↓
Compare: new, removed, unchanged species
  ↓
Any changes?
  ├─ NO  → Report "up to date" → END
  └─ YES → Continue
       ↓
Extract details for new species only
  ↓
Merge with existing detailed data
  ↓
Save updated CSV files
  ↓
Generate update report
  ↓
END
```

---

## Performance Comparison

| Scenario | Full Scrape | Incremental Update | Time Saved |
|----------|-------------|-------------------|------------|
| No changes | 65+ min | ~2 min | **63 min (97%)** |
| 1-5 new species | 65+ min | ~2-3 min | **62+ min (95%)** |
| 10 new species | 65+ min | ~2.5 min | **62.5 min (96%)** |
| 50 new species | 65+ min | ~4.5 min | **60.5 min (93%)** |
| 100+ new species | 65+ min | ~7 min | **58 min (89%)** |

**Typical quarterly update:** 2-5 new species = **95% faster**

---

## Advanced Usage

### Update with Custom Output Location

Modify script to save to different directory:

```python
# In update_shark_references_species.py
DATA_DIR = Path('/path/to/custom/data')
```

### Automated Notifications

Add email notification on completion (Linux):

```bash
python3 scripts/update_shark_references_species.py && \
  echo "Species database updated: $(grep 'New species found' data/shark_species_update_report.txt)" | \
  mail -s "Shark DB Update Complete" your.email@example.com
```

### Integration with Analysis Pipeline

Create wrapper script:

```bash
#!/bin/bash
# update_and_analyze.sh

echo "Updating species database..."
python3 scripts/update_shark_references_species.py

if grep -q "New species found: [1-9]" data/shark_species_update_report.txt; then
    echo "New species found! Regenerating SQL..."
    Rscript scripts/generate_species_sql.R

    echo "Updating database..."
    duckdb database.duckdb < sql/06_add_species_columns.sql

    echo "Re-running analysis..."
    Rscript scripts/analyze_database.R
else
    echo "No new species. Skipping updates."
fi
```

---

## Maintenance & Best Practices

### Regular Maintenance

**Quarterly:**
- Run incremental update
- Review update report
- Check for taxonomic changes

**Annually:**
- Run full re-scrape with `--full` flag
- Verify data quality
- Check for HTML structure changes in website

### Data Quality Checks

After each update:

```r
# In R
library(tidyverse)

# Load updated data
species <- read_csv('data/shark_species_detailed_complete.csv')

# Check for missing common names
species %>%
  filter(is.na(common_name_primary)) %>%
  select(binomial) %>%
  print()

# Check taxonomy completeness
species %>%
  summarise(
    missing_superorder = sum(is.na(superorder)),
    missing_order = sum(is.na(order)),
    missing_family = sum(is.na(family))
  ) %>%
  print()
```

### Backup Strategy

Before running update:

```bash
# Backup current database
cp data/shark_species_detailed_complete.csv \
   data/backups/shark_species_$(date +%Y%m%d).csv
```

---

## Related Documentation

- **Full Extraction Guide:** `docs/Shark_References_Species_Database_Extraction.md`
- **Database Schema:** `docs/Database_Schema_Design.md`
- **Project TODO:** `TODO.md` (Task I1.15)

---

## Contact & Support

**Shark-References Website:** https://shark-references.com
**Contact:** info@shark-references.com

**Project Issues:** See `docs/` folder for troubleshooting guides

---

*Document created: 2025-10-13*
*Script version: 1.0*
*Python 3.8+ required*
