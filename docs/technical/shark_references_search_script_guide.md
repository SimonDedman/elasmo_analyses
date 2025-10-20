# Shark-References Search Script - Usage Guide

**Script Location:** `scripts/shark_references_search.py`
**Last Updated:** 2025-10-17
**Status:** ✅ Updated to read from Excel, ready to test

---

## What Was Updated Tonight

### Major Improvements

1. ✅ **Direct Excel Reading** - No more hardcoded search terms!
   - Reads from `data/Techniques DB for Panel Review.xlsx`
   - Uses `Full_List` tab
   - Automatically filters techniques with search queries

2. ✅ **Progress Tracking & Resumption**
   - Saves progress to `outputs/shark_references_raw/search_progress.csv`
   - Can resume interrupted searches with `--resume`
   - Never re-runs completed searches

3. ✅ **Flexible Execution Modes**
   - Test single search
   - Limit number of searches (for testing)
   - Search by discipline
   - Search all techniques

4. ✅ **Better Output Management**
   - Structured filenames: `{discipline}_{technique}_{date}.csv`
   - All outputs to `outputs/shark_references_raw/`
   - Progress and statistics logging

5. ✅ **Polite Crawling**
   - 3-second delay between requests (configurable)
   - Proper User-Agent header
   - Error handling and retry capability

---

## Installation Requirements

**One-time setup** (requires sudo):

```bash
# Install pandas (required for reading Excel)
sudo apt install python3-pandas

# Verify all dependencies
python3 -c "import requests, openpyxl, pandas; print('✓ All dependencies installed')"
```

**Already installed:**
- ✓ `requests` (for HTTP)
- ✓ `openpyxl` (for Excel reading)

---

## Usage Examples

### 1. Test Search (Start Here!)

Test with a single hardcoded query to verify everything works:

```bash
cd "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
python3 scripts/shark_references_search.py --test
```

**Expected output:**
- Creates `outputs/shark_references_raw/TEST_acoustic_telemetry_YYYYMMDD.csv`
- Shows first 500 characters of response
- Logs result count

**If successful:** You'll see ✓ and a CSV file with search results
**If failed:** Check shark_references_search.log for errors

---

### 2. Limited Test (5 Searches)

Test the full pipeline with just 5 techniques:

```bash
python3 scripts/shark_references_search.py --limit 5
```

**What this does:**
- Loads Excel database
- Searches first 5 techniques
- Saves progress after each search
- Creates CSVs in `outputs/shark_references_raw/`

**Runtime:** ~15-20 seconds (3 sec delay × 5 searches)

---

### 3. Search Single Discipline

Search all techniques in one discipline (e.g., Movement):

```bash
python3 scripts/shark_references_search.py --discipline MOV
```

**Discipline codes:**
- BEH - Behaviour & Sensory
- BIO - Biology, Health & Physiology
- CON - Conservation & Policy
- DATA - Data Science & Analytics
- FISH - Fisheries & Management
- GEN - Genetics & Genomics
- MOV - Movement & Spatial
- TRO - Trophic Ecology

**Runtime:** Depends on technique count per discipline (~10-30 minutes)

---

### 4. Search All Techniques

**⚠️ Run overnight or over weekend!**

```bash
# Start full search
python3 scripts/shark_references_search.py --all

# Or with faster delay (less polite, use sparingly)
python3 scripts/shark_references_search.py --all --delay 2
```

**Expected:**
- ~215 searches (current database)
- ~10-18 hours at 3-second delay
- Creates ~215 CSV files
- Progress tracked continuously

---

### 5. Resume Interrupted Search

If search stops for any reason:

```bash
python3 scripts/shark_references_search.py --resume --all
```

**What happens:**
- Loads `search_progress.csv`
- Skips already completed searches
- Continues where it left off

---

## Output Structure

```
outputs/shark_references_raw/
├── search_progress.csv          # Progress tracking (resumption file)
├── BEH_video_analysis_20251017.csv
├── BEH_accelerometry_20251017.csv
├── MOV_acoustic_telemetry_20251017.csv
├── MOV_satellite_tracking_20251017.csv
├── GEN_population_genetics_20251017.csv
└── ... (~215 files when complete)
```

### CSV File Naming Convention

`{discipline_code}_{technique_name_cleaned}_{date}.csv`

Examples:
- `MOV_acoustic_telemetry_20251017.csv`
- `GEN_whole_genome_sequencing_20251017.csv`
- `FISH_cpue_standardization_20251017.csv`

### Progress File Format

`search_progress.csv` contains:
- `timestamp` - When search completed
- `discipline_code` - Discipline
- `technique_name` - Technique searched
- `search_query` - Query used
- `status` - 'success' or 'error'
- `result_count` - Number of results (CSV lines)
- `error_message` - If failed

---

## Monitoring Progress

### During Execution

Watch the log file in real-time:

```bash
tail -f shark_references_search.log
```

### Check Progress

```bash
# Count completed searches
wc -l outputs/shark_references_raw/search_progress.csv

# Count CSV files created
ls outputs/shark_references_raw/*.csv | wc -l

# See recent searches
tail -20 outputs/shark_references_raw/search_progress.csv
```

### View Statistics

At end of each run, script shows:
- Total techniques processed
- Successful searches
- Empty results (no papers found)
- Failed searches
- Skipped (if resuming)

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'pandas'"

```bash
sudo apt install python3-pandas
```

### "Excel file not found"

Script expects: `data/Techniques DB for Panel Review.xlsx`

Check it exists:
```bash
ls -lh "data/Techniques DB for Panel Review.xlsx"
```

### "Connection timeout" or "Request failed"

Increase delay and retry:
```bash
python3 scripts/shark_references_search.py --resume --all --delay 5
```

### Empty results for many techniques

This is EXPECTED! Not all techniques will have papers. The script logs these as "No results found" but marks them as successful.

### Script interrupted (Ctrl+C)

No problem! Just resume:
```bash
python3 scripts/shark_references_search.py --resume --all
```

---

## Next Steps After Search Completion

### 1. Review Results

```bash
# Count total result files
ls outputs/shark_references_raw/*.csv | grep -v progress | wc -l

# See which disciplines have results
ls outputs/shark_references_raw/ | cut -d_ -f1 | sort | uniq -c

# Find largest result files (most papers)
ls -lSh outputs/shark_references_raw/*.csv | head -20
```

### 2. Check for Empty Results

```bash
# Find techniques with no results
grep ",0," outputs/shark_references_raw/search_progress.csv | wc -l

# See which had errors
grep "error" outputs/shark_references_raw/search_progress.csv
```

### 3. Add New Techniques

When panelists suggest new techniques:
1. Add row to Excel: `data/Techniques DB for Panel Review.xlsx`
2. Run search ONLY for new ones:
   ```bash
   python3 scripts/shark_references_search.py --resume --all
   ```
   (Resume mode will skip existing, only search new)

### 4. Proceed to Database Import

Once satisfied with results:
- Run `scripts/import_shark_refs_to_db.py` (to be created)
- Creates SQLite database from all CSVs
- Next phase of pipeline!

---

## Performance Expectations

### Search Speed
- **Delay:** 3 seconds between requests (default)
- **Per search:** ~3-5 seconds total (request + delay)
- **208 techniques:** ~10-17 minutes minimum
- **Real time:** 15-30 minutes (accounting for variable response times)

### Result Sizes
- **Average CSV:** 10-500 KB
- **Large results:** 1-5 MB (popular techniques)
- **Empty results:** <1 KB (just header)
- **Total expected:** 50-200 MB for all results

### When to Run
- **Test runs:** Anytime (< 1 minute)
- **Single discipline:** Daytime OK (10-30 minutes)
- **Full search:** Overnight or weekend (safer)

---

## Script Features Summary

✅ **Reads from Excel** - No code changes needed for new techniques
✅ **Progress tracking** - Never lose work
✅ **Resumable** - Interrupt and continue anytime
✅ **Flexible modes** - Test, limit, discipline, or all
✅ **Polite crawling** - Respects server with delays
✅ **Structured output** - Clean, organized CSV files
✅ **Detailed logging** - Both file and console
✅ **Error handling** - Graceful failures, continues on errors
✅ **Statistics** - Summary at completion

---

## Quick Reference Commands

```bash
# 1. First time - install pandas
sudo apt install python3-pandas

# 2. Test it works
python3 scripts/shark_references_search.py --test

# 3. Small test run
python3 scripts/shark_references_search.py --limit 5

# 4. Search one discipline
python3 scripts/shark_references_search.py --discipline MOV

# 5. Full search (overnight)
nohup python3 scripts/shark_references_search.py --all > search.out 2>&1 &

# 6. Check progress
tail -f shark_references_search.log

# 7. Resume if interrupted
python3 scripts/shark_references_search.py --resume --all
```

---

## Questions or Issues?

Check these files:
- `shark_references_search.log` - Detailed execution log
- `outputs/shark_references_raw/search_progress.csv` - What's completed
- Script itself has extensive comments and help:
  ```bash
  python3 scripts/shark_references_search.py --help
  ```

**Ready to start searching immediately once pandas is installed!**
