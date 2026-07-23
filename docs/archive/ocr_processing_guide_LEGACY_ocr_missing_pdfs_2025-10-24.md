# OCR Processing Guide

**Script:** `scripts/ocr_missing_pdfs.py`
**Purpose:** Automatically OCR PDFs lacking searchable text and replace originals

---

## Quick Start

### 1. Test Run (Recommended First Step)

```bash
cd "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"

# Test on 10 random PDFs
./venv/bin/python scripts/ocr_missing_pdfs.py --test
```

### 2. Dry Run (See What Will Happen)

```bash
# Analyze all PDFs without processing
./venv/bin/python scripts/ocr_missing_pdfs.py --dry-run
```

**This will show:**
- How many PDFs need OCR
- How many already have text
- How many were already processed
- Estimated time to complete

### 3. Full Run

```bash
# Process all PDFs (uses CPU count - 1 cores)
./venv/bin/python scripts/ocr_missing_pdfs.py

# Or specify number of parallel jobs
./venv/bin/python scripts/ocr_missing_pdfs.py --jobs 4
```

---

## Features

### ✅ Smart Processing

- **Checks for text first:** Only OCRs PDFs that lack searchable text
- **Skips already done:** Maintains log of processed files
- **Safe replacement:** Backs up originals before replacing
- **Parallel processing:** Uses multiple CPU cores for speed
- **Resumable:** Can stop and restart without reprocessing

### 📝 Logging

**Log file:** `logs/ocr_processing_log.csv`

**Columns:**
- `file_path` - Full path to PDF
- `filename` - PDF filename
- `status` - Processing status
- `backup_path` - Location of backup (if OCR'd)
- `error` - Error message (if failed)
- `timestamp` - When processed

**Status values:**
- `success` - OCR'd and replaced original
- `skipped_has_text` - Already has searchable text
- `skipped_already_done` - Previously processed
- `failed` - OCR failed (see error column)

### 💾 Backups

**All originals backed up to:**
```
backups/pre_ocr/
```

**Restore a backup:**
```bash
# If you need to restore an original
cp "backups/pre_ocr/filename.pdf" "/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers/YYYY/filename.pdf"
```

---

## Command-Line Options

```bash
# Show help
./venv/bin/python scripts/ocr_missing_pdfs.py --help

# Test mode (10 PDFs only)
./venv/bin/python scripts/ocr_missing_pdfs.py --test

# Dry run (no changes)
./venv/bin/python scripts/ocr_missing_pdfs.py --dry-run

# Custom number of parallel jobs
./venv/bin/python scripts/ocr_missing_pdfs.py --jobs 8

# Combine options
./venv/bin/python scripts/ocr_missing_pdfs.py --test --dry-run
```

---

## Usage Workflow

### Day 1: Initial OCR Run

```bash
cd "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"

# 1. Dry run to see what needs OCR
./venv/bin/python scripts/ocr_missing_pdfs.py --dry-run

# Output example:
# Total PDFs: 13,357
# Already processed: 0
# Has text (skip): 13,090
# Needs OCR: 267
# Estimated time: 1.7 hours (8 parallel jobs)

# 2. Run the OCR
./venv/bin/python scripts/ocr_missing_pdfs.py

# 3. Check results
cat logs/ocr_processing_log.csv | tail -20
```

### Day 2: After Sci-Hub Downloads

```bash
# New PDFs from Sci-Hub download: ~5,000-7,000

# Run OCR again (only new PDFs will be processed)
./venv/bin/python scripts/ocr_missing_pdfs.py

# The script will:
# - Check all PDFs in collection
# - Skip already processed (from log)
# - Skip PDFs with text
# - OCR only new PDFs lacking text
```

**Automatic skipping:**
- PDFs already in log with `status=success` → skipped
- PDFs with searchable text → skipped
- Only new PDFs lacking text → processed

### Day 3+: Ongoing Maintenance

```bash
# Just run the script periodically
./venv/bin/python scripts/ocr_missing_pdfs.py

# Could even add to cron for daily runs:
# 0 3 * * * cd "/path/to/project" && ./venv/bin/python scripts/ocr_missing_pdfs.py >> logs/ocr_cron.log 2>&1
```

---

## Expected Output

### Dry Run Output

```
================================================================================
PDF OCR PROCESSOR
================================================================================

🔍 Checking dependencies...
  ✅ pdftotext found
  ✅ ocrmypdf found

📋 Loading existing OCR log...
  ✅ Found 267 previously processed PDFs

  Previous processing summary:
    success                  :    250
    failed                   :     15
    skipped_has_text         :      2

🔍 Finding all PDFs in /media/simon/data/.../SharkPapers...
  ✅ Found 13,357 PDFs

⚠️  DRY RUN MODE - No files will be modified

⚙️  Configuration:
  Parallel jobs: 8
  Min text length: 100 characters
  Test pages: 2
  Timeout per PDF: 300 seconds
  Backup directory: backups/pre_ocr

📊 Analysis (dry run)...
Analyzing: 100%|██████████| 13357/13357 [02:15<00:00, 98.4it/s]

📊 Dry run results:
  Total PDFs: 13,357
  Already processed: 250
  Has text (skip): 13,090
  Needs OCR: 17

  Estimated time: 0.1 hours (8 parallel jobs)
  Estimated disk usage (temp): 164.2 MB

  Run without --dry-run to process files
```

### Full Run Output

```
================================================================================
PDF OCR PROCESSOR
================================================================================

[dependency checks...]
[configuration...]

🚀 Processing PDFs...
  (PDFs with text will be skipped automatically)

Processing: 100%|██████████| 13357/13357 [1:45:23<00:00, 2.1it/s]

💾 Saving results...
  ✅ Results saved to logs/ocr_processing_log.csv

================================================================================
PROCESSING COMPLETE
================================================================================

Total PDFs processed: 13,357
Elapsed time: 1:45:23

Status breakdown:
  success                  :    267 (  2.0%)
  skipped_has_text         : 13,088 ( 98.0%)
  skipped_already_done     :      0 (  0.0%)
  failed                   :      2 (  0.0%)

✅ Successfully OCR'd 267 PDFs
  Originals backed up to: backups/pre_ocr
  Average time: 23.6 seconds per PDF

❌ Failed to OCR 2 PDFs

  Common errors:
    Timeout after 300 seconds                                   :   1
    pdftotext error: Syntax Warning                            :   1

⏭️  Skipped 13,088 PDFs (already have text)

================================================================================

💡 Next steps:
  1. Check log: cat logs/ocr_processing_log.csv
  2. Backups at: backups/pre_ocr
  3. Run again tomorrow to OCR new PDFs from Sci-Hub downloads
  4. To restore a backup: cp backups/pre_ocr/filename.pdf <original_location>

================================================================================
```

---

## Monitoring Progress

### While Running

**In another terminal:**

```bash
# Watch the log file grow
tail -f logs/ocr_processing_log.csv

# Count successful OCRs
grep "success" logs/ocr_processing_log.csv | wc -l

# Count failures
grep "failed" logs/ocr_processing_log.csv | wc -l

# Watch backup directory
watch -n 10 'ls -lh backups/pre_ocr/ | tail -20'

# Monitor system resources
htop
```

### After Completion

```bash
# View summary from log
cd "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"

# Count by status
awk -F',' 'NR>1 {print $3}' logs/ocr_processing_log.csv | sort | uniq -c

# Success rate
total=$(wc -l < logs/ocr_processing_log.csv)
success=$(grep -c "success" logs/ocr_processing_log.csv)
echo "Success rate: $((success * 100 / total))%"

# Failed PDFs
awk -F',' '$3=="failed" {print $2, $5}' logs/ocr_processing_log.csv

# Size of backup directory
du -sh backups/pre_ocr/
```

---

## Troubleshooting

### Script Won't Start

**Problem:** "pdftotext not found"
```bash
sudo apt-get update
sudo apt-get install poppler-utils
```

**Problem:** "ocrmypdf not found"
```bash
sudo apt-get update
sudo apt-get install ocrmypdf tesseract-ocr tesseract-ocr-eng
```

### OCR Taking Too Long

**Solution 1:** Reduce parallel jobs (less CPU intensive)
```bash
./venv/bin/python scripts/ocr_missing_pdfs.py --jobs 2
```

**Solution 2:** Increase timeout for large PDFs
Edit script:
```python
OCRMYPDF_TIMEOUT = 600  # Change from 300 to 600 seconds
```

**Solution 3:** Run in background
```bash
nohup ./venv/bin/python scripts/ocr_missing_pdfs.py > logs/ocr_run.log 2>&1 &

# Monitor progress
tail -f logs/ocr_run.log
```

### Disk Space Running Out

**Check space:**
```bash
df -h /media/simon/data/
```

**Free up space:**
```bash
# Remove backup directory (if satisfied with OCR results)
rm -rf backups/pre_ocr/

# Compress backups instead
tar -czf backups/pre_ocr_$(date +%Y%m%d).tar.gz backups/pre_ocr/
rm -rf backups/pre_ocr/
```

### Failed PDFs

**Check failures:**
```bash
# List failed PDFs
awk -F',' '$3=="failed" {print $2}' logs/ocr_processing_log.csv

# See error messages
awk -F',' '$3=="failed" {print $2 " : " $5}' logs/ocr_processing_log.csv
```

**Common failures:**
- **Timeout:** PDF too large/complex - increase timeout
- **Corrupted PDF:** Original file damaged - skip or re-download
- **OCR error:** Incompatible format - may need manual processing

**Retry failed PDFs:**
```bash
# Remove failed entries from log
grep -v "failed" logs/ocr_processing_log.csv > logs/ocr_processing_log_cleaned.csv
mv logs/ocr_processing_log_cleaned.csv logs/ocr_processing_log.csv

# Run again
./venv/bin/python scripts/ocr_missing_pdfs.py
```

---

## Performance Tuning

### Optimal Parallel Jobs

**Find your CPU count:**
```bash
nproc
# Output: 8 (for example)
```

**Recommendations:**
- **Light use:** `--jobs 2` (50% CPU, system responsive)
- **Normal use:** `--jobs 6` (75% CPU, default behavior)
- **Heavy use:** `--jobs 8` (100% CPU, fastest)
- **Background:** `--jobs 1` (minimal impact, slowest)

**Test different settings:**
```bash
# Time a test run with different job counts
time ./venv/bin/python scripts/ocr_missing_pdfs.py --test --jobs 1
time ./venv/bin/python scripts/ocr_missing_pdfs.py --test --jobs 4
time ./venv/bin/python scripts/ocr_missing_pdfs.py --test --jobs 8
```

### Speed vs Quality

The script uses balanced ocrmypdf settings:
- `--deskew` - Straighten pages (adds time but improves accuracy)
- `--rotate-pages` - Auto-rotate (adds time but necessary)
- `--clean` - Remove artifacts (adds time but cleaner output)
- `--optimize 1` - Light optimization (fast)

**For faster processing** (edit script):
```python
# Remove these lines in ocr_pdf() function:
'--deskew',
'--clean',
```

**For better quality** (edit script):
```python
# Change:
'--optimize', '1',
# To:
'--optimize', '3',
```

---

## Integration with Download Pipeline

### Automated Workflow

**Option 1: Sequential (download then OCR)**
```bash
# Start downloads
bash scripts/run_integrated_pipeline.sh

# When downloads complete (~24 hours), run OCR
./venv/bin/python scripts/ocr_missing_pdfs.py
```

**Option 2: Concurrent (OCR while downloading)**
```bash
# Terminal 1: Start downloads
bash scripts/run_integrated_pipeline.sh

# Terminal 2: Run OCR every hour
while true; do
  ./venv/bin/python scripts/ocr_missing_pdfs.py
  sleep 3600  # Wait 1 hour
done
```

**Option 3: Cron job (daily OCR)**
```bash
# Add to crontab
crontab -e

# Add line (runs daily at 3am):
0 3 * * * cd "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel" && ./venv/bin/python scripts/ocr_missing_pdfs.py >> logs/ocr_daily.log 2>&1
```

---

## File Structure

```
Project/
├── scripts/
│   └── ocr_missing_pdfs.py          # Main OCR script
├── logs/
│   └── ocr_processing_log.csv       # Processing log (persistent)
├── backups/
│   └── pre_ocr/                     # Original PDFs before OCR
│       ├── filename1.pdf
│       ├── filename2.pdf
│       └── ...
└── /media/.../SharkPapers/          # PDF collection
    ├── 2025/
    │   ├── paper1.pdf               # Original replaced with OCR'd version
    │   └── ...
    ├── 2024/
    └── ...
```

---

## FAQ

### Q: What happens if I run it twice?

**A:** Perfectly safe! PDFs already in the log are skipped automatically.

### Q: Can I stop it mid-run?

**A:** Yes! Press Ctrl+C. Progress is saved to log. Next run will skip completed PDFs.

### Q: Will it OCR PDFs that already have text?

**A:** No. Script checks for text first and skips if found.

### Q: How do I undo the OCR?

**A:** Restore from backups:
```bash
cp backups/pre_ocr/filename.pdf "/media/simon/data/.../SharkPapers/YYYY/"
```

### Q: Can I delete the backups?

**A:** Yes, once you're satisfied with OCR results. Or compress them:
```bash
tar -czf backups_$(date +%Y%m%d).tar.gz backups/pre_ocr/
rm -rf backups/pre_ocr/
```

### Q: How accurate is the OCR?

**A:** Tesseract/ocrmypdf typically achieves 95-98% accuracy on clean scans. Quality varies with scan quality.

### Q: Will this work on non-English PDFs?

**A:** Partially. Script uses English OCR by default. For better results on other languages, install additional Tesseract language packs:
```bash
# German
sudo apt-get install tesseract-ocr-deu

# French
sudo apt-get install tesseract-ocr-fra

# Spanish
sudo apt-get install tesseract-ocr-spa
```

Then edit script to add language detection.

---

## Summary

**Quick commands:**

```bash
# See what will happen
./venv/bin/python scripts/ocr_missing_pdfs.py --dry-run

# Process everything
./venv/bin/python scripts/ocr_missing_pdfs.py

# Run daily to catch new downloads
# (add to cron or run manually)
./venv/bin/python scripts/ocr_missing_pdfs.py
```

**Key features:**
- ✅ Only OCRs PDFs lacking text
- ✅ Skips already processed PDFs
- ✅ Backs up originals automatically
- ✅ Maintains log for repeatability
- ✅ Parallel processing for speed
- ✅ Safe to run multiple times

---

**Last Updated:** 2025-10-24
