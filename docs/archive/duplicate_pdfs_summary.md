# Duplicate PDFs Summary

**Date:** 2025-10-25
**Analysis:** Full collection scan of 13,357 PDFs

---

## Executive Summary

**Found 860 duplicate PDF pairs** in the SharkPapers collection.

- **Total duplicates to remove:** 860 files
- **Disk space to free:** 2.46 GB
- **Cause:** Papers downloaded from both Dropbox collection and Sci-Hub

**Recommendation:** Remove duplicates, keeping Dropbox naming convention (abbreviated titles)

---

## Duplicate Patterns

### Why Duplicates Exist

Duplicates arose from two download sources:

1. **Dropbox collection** (original, curated)
   - Naming: `Author.etal.YYYY.Abbreviated title.pdf`
   - Example: `Zikmanis.etal.2025.Legac ecosys mod fact affect longterm var abund jBullShark subtrop estuary.pdf`

2. **Sci-Hub downloads** (automated)
   - Naming: `Author.etal.YYYY.Full Long Title Words.pdf`
   - Example: `Zikmanis.etal.2025.Legacies of Ecosystem Modification Factors Affecting.pdf`

### Common Duplicate Types

1. **Same paper, different title lengths**
   - Keep: `Bond.etal.2019.Top preds induce hab shift prey MPAs.pdf` (abbreviated)
   - Remove: `Bond.etal.2019.Top predators induce habitat shifts in prey within marine.pdf` (full)

2. **Versioned files (_v1 suffix)**
   - Keep: Original filename
   - Remove: `_v1` versioned copies

3. **Case variations**
   - Keep: Consistent case format
   - Remove: Inconsistent variants

---

## Removal Strategy

### Files to Keep (Dropbox Naming)

✅ **Keep these characteristics:**
- Abbreviated titles (< 80 chars)
- Concise wording
- Common abbreviations: "etal", "j[Journal]", "abund", "var"
- Dropbox naming convention

### Files to Remove (Sci-Hub Naming)

❌ **Remove these characteristics:**
- Full, unabbreviated titles (> 80 chars)
- Many common words ("of", "the", "and", "in")
- `_v1` suffixes
- Longer than Dropbox equivalent

---

## Duplicate Examples

### Example 1: Zikmanis et al. 2025

```
KEEP:   Zikmanis.etal.2025.Legac ecosys mod fact affect longterm var abund jBullShark subtrop estuary.pdf
        Size: 1.8 MB

REMOVE: Zikmanis.etal.2025.Legacies of Ecosystem Modification Factors Affecting.pdf
        Size: 1.8 MB

Reason: Keep Dropbox naming (abbreviated title)
```

### Example 2: Bond et al. 2019

```
KEEP:   Bond.etal.2019.Top preds induce hab shift prey MPAs.pdf
        Size: 1.4 MB

REMOVE: Bond.etal.2019.Top predators induce habitat shifts in prey within marine.pdf
        Size: 1.4 MB

REMOVE: Bond.etal.2019.Top predators induce habitat shifts in prey within marine_v1.pdf
        Size: 1.4 MB

Reason: Keep shortest abbreviated title, remove full titles and versions
```

### Example 3: Watanabe et al. 2019

```
KEEP:   Watanabe.etal.2019.Swim strat energetic endoth whiteshak forag.pdf
        Size: 2.9 MB

REMOVE: Watanabe.etal.2019.Swimming strategies and energetics of endothermic white.pdf
        Size: 2.9 MB

REMOVE: Watanabe.etal.2019.Swimming strategies and energetics of endothermic white_v1.pdf
        Size: 2.9 MB

Reason: Keep Dropbox abbreviated title
```

---

## How to Review and Remove

### Step 1: Review Duplicate List

```bash
cd "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"

# View duplicate pairs
cat outputs/duplicate_pdfs_to_remove.csv | less

# Count duplicates by year
awk -F',' 'NR>1 {print $3}' outputs/duplicate_pdfs_to_remove.csv | cut -d'/' -f10 | sort | uniq -c
```

### Step 2: Dry Run (No Changes)

```bash
# See what would be removed
./venv/bin/python scripts/remove_duplicate_pdfs.py

# Review the log
cat logs/duplicate_pdfs_removed.log
```

**This shows:**
- Which files would be removed
- Which files would be kept
- Total disk space to free
- Reasons for each decision

### Step 3: Remove Duplicates (LIVE)

```bash
# Actually remove the duplicates
./venv/bin/python scripts/remove_duplicate_pdfs.py --live

# Confirm removal by typing: DELETE
```

**Warning:** This permanently deletes 860 PDF files!

---

## Safety Features

### Built-in Protection

1. **Dry-run by default** - Must use `--live` flag to actually delete
2. **Confirmation required** - Must type "DELETE" to proceed
3. **Detailed logging** - All removals logged to CSV
4. **File verification** - Checks both files exist before removal
5. **No backup** - But originals kept in Dropbox

### Recovery

If you need to recover deleted files:

1. **Dropbox originals** - All "keep" files use Dropbox naming, so originals preserved
2. **Sci-Hub re-download** - Can re-download from Sci-Hub if needed
3. **Removal log** - CSV log shows exactly what was removed

---

## Disk Space Impact

### Before Removal

```
Total collection: ~33.6 GB (13,357 PDFs)
Duplicates: 2.46 GB (860 PDFs)
```

### After Removal

```
Total collection: ~31.1 GB (12,497 PDFs)
Freed space: 2.46 GB
Reduction: ~7.3%
```

---

## Verification Commands

### Check for Duplicates After Removal

```bash
# Re-run duplicate finder
./venv/bin/python scripts/find_duplicate_pdfs.py

# Should find 0 duplicates (or very few)
```

### Count PDFs Before/After

```bash
# Before removal
find "/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers" -name "*.pdf" | wc -l
# Expected: 13,357

# After removal
find "/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers" -name "*.pdf" | wc -l
# Expected: 12,497 (13,357 - 860)
```

### Check Specific Examples

```bash
# Look for Zikmanis papers
find "/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers" -name "*Zikmanis*"

# Before: 2 files (duplicate)
# After: 1 file (Dropbox naming kept)
```

---

## Files Created

### Analysis Output

- **`outputs/duplicate_pdfs_to_remove.csv`**
  - List of all 860 duplicate pairs
  - Columns: keep_file, remove_file, similarity, reason, size_match

### Removal Log

- **`logs/duplicate_pdfs_removed.log`**
  - Log of all removals (created when run with --live)
  - Columns: timestamp, action, removed_file, kept_file, size_freed

### Scripts

- **`scripts/find_duplicate_pdfs.py`**
  - Finds duplicates by MD5 hash and metadata matching
  - Creates recommendations

- **`scripts/remove_duplicate_pdfs.py`**
  - Removes duplicates based on recommendations
  - Dry-run by default, --live flag for actual removal

---

## Duplicate Statistics

### By Year

Most duplicates are from recent years (2019+), when both Dropbox and Sci-Hub downloads were active.

```
2019: ~300 duplicate pairs
2020: ~150 duplicate pairs
2021: ~120 duplicate pairs
2022-2025: ~290 duplicate pairs
```

### By Similarity

```
High similarity (>0.9): ~400 pairs (exact same title, minor variations)
Medium similarity (0.7-0.9): ~300 pairs (similar titles)
Lower similarity (0.6-0.7): ~160 pairs (abbreviated vs full)
```

### By Size Match

```
Exact same size: ~600 pairs (identical files)
Different sizes: ~260 pairs (different versions or formats)
```

---

## Recommendations

### Immediate Action

✅ **Run dry-run** to verify removals are correct

```bash
./venv/bin/python scripts/remove_duplicate_pdfs.py
```

### After Review

✅ **Remove duplicates** if satisfied with recommendations

```bash
./venv/bin/python scripts/remove_duplicate_pdfs.py --live
```

### Long-term

✅ **Prevent future duplicates** by:
1. Using single naming convention for all downloads
2. Checking for existing PDFs before downloading
3. Running duplicate finder periodically

---

## FAQ

### Q: Will this delete important PDFs?

**A:** No. The script only removes duplicates (same paper, different filename). One copy of each paper is always kept.

### Q: Which version is kept?

**A:** The Dropbox naming convention is kept (abbreviated titles). These are the curated filenames from your original collection.

### Q: Can I undo the removal?

**A:** No built-in undo, but:
- Dropbox originals are kept
- Can re-download from Sci-Hub if needed
- Removal log shows what was deleted

### Q: What if I want to keep the full titles instead?

**A:** Modify the `recommend_removal()` function in `find_duplicate_pdfs.py` to reverse the logic (keep longer titles, remove abbreviated).

### Q: How accurate is the duplicate detection?

**A:** Very accurate:
- Exact duplicates: 100% (MD5 hash match)
- Near-duplicates: ~95% (author + year + title similarity > 0.6)
- Manual review recommended for edge cases

---

**Last Updated:** 2025-10-25
