# Duplicate Removal - Final Guide

**Date:** 2025-10-25
**Status:** Ready to execute

---

## Summary

**Duplicates found:** 842 pairs (after excluding reply/correction/commentary papers)
**Disk space to free:** 2.46 GB
**Final collection:** ~12,500 PDFs (from 13,357)

---

## Improvements Made

### 1. Excludes Special Paper Types ✅

The improved duplicate finder correctly identifies and **preserves** these as separate publications:

- **Reply papers** (26 found) - Papers responding to other publications
- **Corrections/Errata** (36 found) - Published corrections to papers
- **Commentaries** (7 found) - Comment papers
- **Supplementary materials** (0 currently) - Additional methods/data files

**Example preserved:**
```
✓ KEEP: Drymon.etal.2019.Tiger sharks eat songbirds scavenging a windfall of.pdf
✓ KEEP: Drymon.etal.2019.Tiger sharks eat songbirds reply..pdf (SEPARATE PAPER)
```

### 2. Prefers Abbreviated Dropbox Titles ✅

When multiple versions exist (3+), the system now correctly selects the **abbreviated Dropbox-style** filename.

**Scoring system:**
- +20 points per abbreviation indicator (ecol, pred, popns, etc.)
- -10 points per common word (the, of, and, etc.)
- +50 points for non-versioned (_v1, _v2)
- +30 points for ideal length (40-80 chars)

**Example:**
```
File 1: Heithaus.etal.2012.The ecological importance of intact top-predator.pdf
        Score: 122 (2 abbrev, 2 common, no version)

File 2: Heithaus.etal.2012.The ecological importance of intact top-predator_v1.pdf
        Score: 69 (2 abbrev, 2 common, HAS version)

File 3: Heithaus.etal.2012.Ecol import intact top pred popns synth 15 yr res seagrass ecosys.pdf
        Score: 165 (4 abbrev, 0 common, no version) ← WINNER ✓
```

### 3. Character Encoding ✅

**Good news:** All filenames are properly UTF-8 encoded!

Files like:
- `Herman.etal.2012.Observat concernant l Evolut et la Systémat de quelques.pdf`
- `Ladwig.etal.2012.Anmerkung zu zwei Haizähnen im Artikel Nachträge zum.pdf`

Are correctly encoded (é, ä, ü are proper UTF-8). No fixing needed.

---

## Workflow

### Step 1: Update Duplicate Recommendations

This regenerates the removal list with improved scoring:

```bash
cd "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"

./venv/bin/python scripts/update_duplicate_recommendations.py
```

**Output:** `outputs/duplicate_pdfs_to_remove_updated.csv`

**Result:** 130 multi-file groups updated to prefer abbreviated titles

### Step 2: Review Recommendations

Check what will be kept/removed:

```bash
# View updated recommendations
head -50 outputs/duplicate_pdfs_to_remove_updated.csv

# Check specific examples
grep "Heithaus.*2012.*ecol" outputs/duplicate_pdfs_to_remove_updated.csv
```

**Verify:**
- Abbreviated Dropbox titles are kept ✓
- Full/versioned titles are removed ✓
- Reply papers NOT in list ✓

### Step 3: Remove Duplicates (Dry Run)

See what would happen without actually deleting:

```bash
./venv/bin/python scripts/remove_duplicate_pdfs.py \
    --duplicates outputs/duplicate_pdfs_to_remove_updated.csv
```

*(Note: You may need to update remove_duplicate_pdfs.py to accept --duplicates parameter)*

Or manually backup the old CSV and replace it:

```bash
mv outputs/duplicate_pdfs_to_remove.csv outputs/duplicate_pdfs_to_remove_old.csv
cp outputs/duplicate_pdfs_to_remove_updated.csv outputs/duplicate_pdfs_to_remove.csv

# Dry run
./venv/bin/python scripts/remove_duplicate_pdfs.py
```

### Step 4: Execute Removal

Actually remove the duplicates:

```bash
./venv/bin/python scripts/remove_duplicate_pdfs.py --live
```

**Confirmation required:** Type `DELETE` when prompted

**This will:**
- Delete ~860 duplicate PDF files
- Free 2.46 GB disk space
- Log all removals to `logs/duplicate_pdfs_removed.log`
- Keep all reply papers, corrections, and abbreviated titles

---

## Verification After Removal

### Check for Remaining Duplicates

```bash
# Re-run duplicate finder
./venv/bin/python scripts/find_duplicate_pdfs_improved.py

# Should find 0 or very few duplicates
```

### Check Specific Files Were Kept

```bash
# Verify Heithaus abbreviated version kept
find "/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers" \
    -name "*Heithaus*2012*Ecol*import*"

# Should return: Heithaus.etal.2012.Ecol import intact top pred popns synth 15 yr res seagrass ecosys.pdf

# Verify reply papers kept
find "/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers" \
    -name "*reply*"

# Should return 26 files
```

### Count Total PDFs

```bash
# Before: 13,357
# After: should be ~12,500

find "/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers" \
    -name "*.pdf" | wc -l
```

---

## Files Created

### Scripts

1. **`scripts/find_duplicate_pdfs_improved.py`**
   - Improved duplicate detection
   - Excludes reply/correction/commentary papers
   - Maps supplementary materials

2. **`scripts/update_duplicate_recommendations.py`**
   - Regenerates recommendations with improved scoring
   - Prefers abbreviated Dropbox titles
   - Handles 3+ file groups correctly

3. **`scripts/fix_filename_encoding.py`**
   - Fixes UTF-8 mojibake (not needed currently)
   - Ready if encoding issues arise

4. **`scripts/merge_sm_results_with_main.py`**
   - Merges supplementary material search results
   - For future technique querying

### Documentation

1. **`docs/database/duplicate_pdfs_summary.md`**
   - Overview of duplicate handling

2. **`docs/database/supplementary_materials_handling.md`**
   - Guide for SM files in technique searches

3. **`docs/database/duplicate_removal_final_guide.md`**
   - This file (complete workflow)

### Outputs

1. **`outputs/duplicate_pdfs_to_remove.csv`**
   - Original recommendations (842 pairs)

2. **`outputs/duplicate_pdfs_to_remove_updated.csv`**
   - Updated with improved scoring (use this!)

3. **`outputs/supplementary_materials_mapping.csv`**
   - SM-to-main paper mappings (empty currently)

---

## Summary Statistics

### Paper Types (After Classification)

| Type | Count | Action |
|------|-------|--------|
| Main papers | ~13,260 | Keep after deduplication |
| Reply papers | 26 | **Keep all** (separate publications) |
| Corrections | 36 | **Keep all** (separate publications) |
| Commentaries | 7 | **Keep all** (separate publications) |
| SM files | 0 | Keep and map to main papers |
| **Total** | **13,357** | → ~12,500 after dedupe |

### Duplicate Groups

| Size | Count | Example |
|------|-------|---------|
| 2 files | 712 | Standard duplicates |
| 3 files | 110 | Multiple versions |
| 4 files | 15 | Many versions |
| 5+ files | 5 | Extensive duplication |
| **Total** | **842** | **Groups to deduplicate** |

### Top Examples of Multi-File Groups

1. **Heithaus 2012** (3 files)
   - ✓ KEEP: `Ecol import intact top pred popns synth 15 yr res seagrass ecosys.pdf`
   - ✗ REMOVE: `The ecological importance of intact top-predator.pdf`
   - ✗ REMOVE: `The ecological importance of intact top-predator_v1.pdf`

2. **Bond 2019** (3 files)
   - ✓ KEEP: `Top preds induce hab shift prey MPAs.pdf`
   - ✗ REMOVE: `Top predators induce habitat shifts in prey within marine.pdf`
   - ✗ REMOVE: `Top predators induce habitat shifts in prey within marine_v1.pdf`

3. **Watanabe 2019** (3 files)
   - ✓ KEEP: `Swim strat energetic endoth whiteshak forag.pdf`
   - ✗ REMOVE: `Swimming strategies and energetics of endothermic white.pdf`
   - ✗ REMOVE: `Swimming strategies and energetics of endothermic white_v1.pdf`

---

## Safety Checklist

Before running --live removal, verify:

- [ ] Updated recommendations generated (outputs/duplicate_pdfs_to_remove_updated.csv)
- [ ] Reviewed sample of recommendations
- [ ] Verified abbreviated titles are kept (grep for specific examples)
- [ ] Confirmed reply papers NOT in removal list
- [ ] Confirmed corrections NOT in removal list
- [ ] System has 2.5+ GB free space (for logs)
- [ ] Ready to type "DELETE" when prompted

---

## Rollback Plan

If something goes wrong:

### Scenario 1: Wrong Files Removed

**Problem:** Realized wrong files were kept after removal

**Solution:** Cannot undo (files permanently deleted)

**Prevention:**
- Review recommendations carefully before --live
- Test on small subset first

### Scenario 2: Need to Re-Download

**Problem:** Accidentally removed files that should have been kept

**Solution:**
1. Check `logs/duplicate_pdfs_removed.log` for list of removed files
2. Re-run Sci-Hub download for those DOIs
3. Or restore from Dropbox backup if available

### Scenario 3: Process Interrupted

**Problem:** Removal script crashed mid-execution

**Solution:**
- Check `logs/duplicate_pdfs_removed.log` for what was removed
- Re-run script (will skip already-removed files)

---

## Post-Removal Next Steps

### 1. Re-run OCR (Optional)

Some removed duplicates might have been in OCR queue:

```bash
./venv/bin/python scripts/ocr_missing_pdfs.py --dry-run
```

### 2. Update Download Queue

Remove duplicates from download queue database:

```bash
# Check for files no longer needed
sqlite3 data/download_queue.db "
SELECT COUNT(*) FROM download_queue
WHERE pdf_path LIKE '%_v1.pdf' OR pdf_path LIKE '%_v2.pdf';
"
```

### 3. Update Documentation

Update project documentation with final PDF count and storage size.

---

## Quick Commands

```bash
# Generate updated recommendations
./venv/bin/python scripts/update_duplicate_recommendations.py

# Review
head -100 outputs/duplicate_pdfs_to_remove_updated.csv

# Prepare for removal
mv outputs/duplicate_pdfs_to_remove.csv outputs/duplicate_pdfs_to_remove_old.csv
cp outputs/duplicate_pdfs_to_remove_updated.csv outputs/duplicate_pdfs_to_remove.csv

# Dry run
./venv/bin/python scripts/remove_duplicate_pdfs.py

# Execute (requires typing DELETE)
./venv/bin/python scripts/remove_duplicate_pdfs.py --live

# Verify
find "/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers" -name "*.pdf" | wc -l
```

---

**Last Updated:** 2025-10-25
**Status:** Ready for execution
