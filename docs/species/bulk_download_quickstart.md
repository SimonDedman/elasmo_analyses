# Shark-References Bulk Download - Quick Start Guide
**Strategy:** Download year-by-year, **NEWEST FIRST** (2025 → 1950)

---

## Why Year-by-Year (Newest First)?

✅ **Most relevant papers first** - Recent techniques, modern studies
✅ **Natural checkpointing** - Resume by year if interrupted
✅ **Easy updates** - In 6 months, just download 2025-2026
✅ **Graceful degradation** - If stopped early, you still have what matters most
✅ **Sorted output** - Papers organized chronologically

---

## Quick Start (3 Commands)

```bash
cd "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"

# 1. Check status (optional)
python3 scripts/shark_references_bulk_download_by_year.py --check

# 2. Download everything (2-2.5 hours)
python3 scripts/shark_references_bulk_download_by_year.py --all --query ""

# Done! ✅
```

That's it. The script will:
1. Download 2025 papers → Save checkpoint
2. Download 2024 papers → Save checkpoint
3. Download 2023 papers → Save checkpoint
4. ... continues through 1950
5. Automatically filters for all 208 techniques
6. Creates technique-specific CSVs

---

## What You Get

### After Download Completes:

**Complete database:**
```
outputs/shark_references_bulk/
  └── shark_references_complete_20251020.csv  (~200 MB, ~35,000 papers, sorted newest first)
```

**Filtered by technique:**
```
outputs/shark_references_filtered/
  ├── MOV-acoustic_telemetry_20251020.csv
  ├── GEN-population_genetics_20251020.csv
  ├── BIO-stress_physiology_20251020.csv
  └── ... (208 CSV files, one per technique)
```

---

## Timeline

### Download Progress (2025 → 1950):

| Year Range | Papers (est.) | Time | Checkpoint |
|------------|---------------|------|------------|
| 2025 | ~500 | 2 min | ✓ Saved |
| 2024 | ~1,500 | 6 min | ✓ Saved |
| 2023 | ~1,500 | 6 min | ✓ Saved |
| 2022 | ~1,500 | 6 min | ✓ Saved |
| 2021 | ~1,500 | 6 min | ✓ Saved |
| ... | | | |
| 2020-2010 | ~15,000 | 60 min | ✓ Each year saved |
| 2010-2000 | ~10,000 | 40 min | ✓ Each year saved |
| 2000-1950 | ~5,000 | 20 min | ✓ Each year saved |

**Total: ~2-2.5 hours** for complete database (75 years)

### After Download:
- **Filter for techniques:** 3 minutes (local, no network)
- **TOTAL:** 2.5 hours wall-clock time

---

## If Interrupted

The script automatically saves progress after **every year**. To resume:

```bash
python3 scripts/shark_references_bulk_download_by_year.py --download --resume
```

Example:
```
✓ Downloaded 2025-2020 (6 years, 8,500 papers)
⚠️  Interrupted at 2019

Resume command: --download --resume
→ Continues from year 2019
→ You keep all 8,500 papers from 2025-2020
```

---

## Running in Background (Recommended)

Start it and forget it:

```bash
cd "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"

# Run in background
nohup python3 scripts/shark_references_bulk_download_by_year.py --all --query "" > bulk_year.log 2>&1 &

# Get process ID
echo $! > bulk_download.pid

# Monitor progress (Ctrl+C to exit monitor, doesn't stop download)
tail -f shark_references_bulk_year.log

# Or check periodically
tail -50 shark_references_bulk_year.log
```

### Check Status While Running:

```bash
# See what year we're on
grep "DOWNLOADING YEAR" shark_references_bulk_year.log | tail -5

# Count papers so far
ls -lh outputs/shark_references_bulk/
```

---

## Updating in 6 Months

When new papers are published, just download recent years:

```bash
# Download only 2025-2026 (new papers since last download)
python3 scripts/shark_references_bulk_download_by_year.py \
  --download \
  --year-start 2026 \
  --year-end 2025 \
  --query ""

# Filter for techniques (3 minutes)
python3 scripts/shark_references_bulk_download_by_year.py --filter
```

**Time:** 5-10 minutes for 2 years of new papers
**Result:** Updated database with latest research

---

## Output Structure

### 1. Complete Database (Bulk)
```csv
year,authors,citation,findspot,doi,full_text
2025,"Smith, J. & Jones, A. (2025)","Movement patterns of...","Marine Biology, 165(4)",...,"full text here"
2025,"Brown, K. et al. (2025)","Genetic diversity in...","Nature, 589(7843)",...,"full text here"
2024,"Taylor, M. (2024)","Acoustic tracking of...","PLoS ONE, 19(3)",...,"full text here"
...
```

**Sorted:** Newest first (2025 → 1950)
**Size:** ~200 MB, ~35,000 papers
**Use:** Query locally for ANY search terms

### 2. Filtered by Technique
```csv
year,authors,citation,findspot,doi,full_text
2024,"Whitney, N.M. et al. (2024)","Acoustic telemetry reveals...","Marine Ecology Progress Series",...,"..."
2023,"Hussey, N.E. et al. (2023)","Aquatic telemetry: a panoramic...","Reviews in Fish Biology",...,"..."
```

**Organized:** One CSV per technique (208 files)
**Filtered:** Only papers matching technique's search terms
**Ready:** For panelist review

---

## Command Reference

### Basic Usage

```bash
# Download everything + filter (complete workflow)
python3 shark_references_bulk_download_by_year.py --all

# Just download (no filtering)
python3 shark_references_bulk_download_by_year.py --download

# Just filter existing download
python3 shark_references_bulk_download_by_year.py --filter

# Resume interrupted download
python3 shark_references_bulk_download_by_year.py --download --resume

# Check checkpoint status
python3 shark_references_bulk_download_by_year.py --check
```

### Advanced Options

```bash
# Custom year range
python3 shark_references_bulk_download_by_year.py \
  --download \
  --year-start 2025 \
  --year-end 2010

# Slower/faster delays
python3 shark_references_bulk_download_by_year.py --download --delay 6  # Safer, slower
python3 shark_references_bulk_download_by_year.py --download --delay 2  # Faster, riskier

# Different search query (usually leave empty)
python3 shark_references_bulk_download_by_year.py --download --query "shark"
```

---

## Monitoring Progress

### Live Monitoring

```bash
# Watch live (Ctrl+C to exit)
tail -f shark_references_bulk_year.log

# Last 50 lines
tail -50 shark_references_bulk_year.log

# What year are we on?
grep "DOWNLOADING YEAR" shark_references_bulk_year.log | tail -1

# How many papers so far?
grep "Total papers" shark_references_bulk_year.log | tail -1
```

### Example Output

```
================================================================================
DOWNLOADING YEAR: 2023
================================================================================
  Papers in 2023: 1,547
  Pages: 78
  Page 1/78 - 20 entries - Total: 20/1,547 (1.3%)
  Page 2/78 - 20 entries - Total: 40/1,547 (2.6%)
  ...
  Page 78/78 - 7 entries - Total: 1,547/1,547 (100.0%)
  ✓ Year 2023 complete: 1,547 papers

  💾 Checkpoint saved - 3,094 papers from 3 years

📊 Progress: 3/76 years (3.9%)
```

---

## Troubleshooting

### "Connection timeout"
- Increase delay: `--delay 6`
- Resume: `--download --resume`

### "Script stopped"
- Check log: `tail shark_references_bulk_year.log`
- Resume: `--download --resume`

### "IP blocked"
- Wait 1 hour
- Resume with longer delay: `--download --resume --delay 8`

### "No papers found for year XXXX"
- Normal! Some years have 0 papers
- Script continues to next year automatically

---

## Verification

After download completes, verify:

```bash
# Check CSV exists
ls -lh outputs/shark_references_bulk/shark_references_complete_*.csv

# Count papers
python3 -c "import pandas as pd; df = pd.read_csv('outputs/shark_references_bulk/shark_references_complete_20251020.csv'); print(f'{len(df):,} papers'); print(f'Years: {df.year.min()}-{df.year.max()}')"

# Check filtered results
ls outputs/shark_references_filtered/*.csv | wc -l  # Should be ~208
```

---

## Next Steps After Download

1. **Review filtered results** - Check technique CSVs in `outputs/shark_references_filtered/`
2. **Query local database** - Use pandas to search bulk CSV for any terms
3. **Distribute to panelists** - Send technique-specific CSVs
4. **Add new techniques** - Just re-run `--filter` (instant)

### Example: Query Local Database

```python
import pandas as pd

# Load complete database
df = pd.read_csv('outputs/shark_references_bulk/shark_references_complete_20251020.csv')

# Search for specific terms (instant)
results = df[df['full_text'].str.contains('environmental DNA', case=False, na=False)]
print(f"Found {len(results)} papers about environmental DNA")

# Search with multiple terms
mask = (
    df['full_text'].str.contains('machine learning', case=False, na=False) &
    df['full_text'].str.contains('shark', case=False, na=False) &
    (df['year'] >= 2020)
)
recent_ml = df[mask]
print(f"Found {len(recent_ml)} papers about machine learning + shark since 2020")
```

---

## Summary

**Command:** `python3 shark_references_bulk_download_by_year.py --all`
**Time:** 2-2.5 hours
**Result:** Complete database + 208 technique CSVs
**Benefit:** Never download again, instant local queries
**Update:** Just download recent years (5-10 minutes)

**Ready to start? Run the command!** 🚀

```bash
cd "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
python3 scripts/shark_references_bulk_download_by_year.py --all --query ""
```
