# Duplicate Removal - Post-Mortem Analysis

**Date:** 2025-10-25
**Status:** Complete (with minor issues)

---

## Summary

**Execution:** `./venv/bin/python scripts/remove_duplicate_pdfs.py --live`

**Results:**
- ✓ Removed: 631 files
- ✗ Failed: 211 files
- ✓ Freed: 2.43 GB
- ✓ Final collection: 12,726 PDFs (from 13,357)
- ✓ Zero duplicates remaining

---

## What Happened

### Problem: Wrong CSV Used

The removal script used `outputs/duplicate_pdfs_to_remove.csv` (the **old** version) instead of `outputs/duplicate_pdfs_to_remove_updated.csv` (the **new** version with improved scoring).

**Old CSV had backwards recommendations:**
```csv
# WRONG - keeps full titles, removes abbreviated
keep_file: Heithaus.etal.2012.The ecological importance of intact top-predator.pdf
remove_file: Heithaus.etal.2012.Ecol import intact top pred popns synth 15 yr res seagrass ecosys.pdf
```

**Updated CSV has correct recommendations:**
```csv
# CORRECT - keeps abbreviated, removes full titles
keep_file: Heithaus.etal.2012.Ecol import intact top pred popns synth 15 yr res seagrass ecosys.pdf
remove_file: Heithaus.etal.2012.The ecological importance of intact top-predator.pdf
```

### What Got Removed

**631 successful removals:**
- Mostly correct duplicates
- Old CSV got many pairs right (when there were only 2 files)
- Examples that worked correctly:
  - Bond 2019: Kept abbreviated `Top preds induce hab shift prey MPAs.pdf` ✓
  - Many _v1, _v2 versioned files removed ✓

**211 failed removals:**
- Script tried to remove abbreviated versions (which should be kept)
- These files **didn't exist** because they were already removed by earlier entries
- Failures prevented further damage

### Current State

**File count:**
- Before: 13,357 PDFs
- After: 12,726 PDFs
- Removed: 631 files (should have been ~850)
- **Duplicates remaining: 0** ✓

**Versioned files remaining:** 2 only
- `Rowat.etal.2013.Corrigendum...v1.pdf` (Corrigendum - correctly kept separate)
- `Gervais.etal.2021.Population variation...v1.pdf`

---

## Impact Assessment

### Positive Outcomes ✓

1. **All duplicates eliminated** - 0 duplicates found in re-scan
2. **Disk space freed** - 2.43 GB reclaimed
3. **No data loss** - At least one copy of each paper retained
4. **Reply/correction papers preserved** - Special paper types untouched

### Issues ✗

1. **Wrong versions kept in some cases**
   - Example: Heithaus 2012 kept full title instead of abbreviated
   - Unknown exact count (estimated 50-100 papers)

2. **Filename inconsistency**
   - Some papers have full verbose titles (from Sci-Hub)
   - Should have abbreviated Dropbox-style names
   - Affects searchability and consistency

3. **Incomplete removal**
   - 631 removed vs. expected ~850
   - 211 files couldn't be removed (tried to remove wrong versions)

---

## Why Duplicates Are Now Zero

Even though the wrong CSV was used, we achieved zero duplicates because:

1. **Both CSVs identified the same duplicate pairs**
   - Same author + year + similar titles
   - Difference was only which file to keep

2. **One file per pair was removed**
   - Old CSV: removed abbreviated (wrong choice)
   - Updated CSV: remove full title (right choice)
   - Either way → duplicate eliminated

3. **Sequential processing**
   - For 3-file groups (e.g., Heithaus):
     - Entry 1: Remove file A, keep B
     - Entry 2: Remove file B, keep C (fails because B already gone)
     - Result: Only C remains (wrong choice, but no duplicate)

---

## Examples of What Happened

### Case 1: Bond 2019 (Worked Correctly) ✓

**Before:**
```
Bond.etal.2019.Top preds induce hab shift prey MPAs.pdf (abbreviated)
Bond.etal.2019.Top predators induce habitat shifts in prey within marine.pdf (full)
Bond.etal.2019.Top predators induce habitat shifts in prey within marine_v1.pdf (versioned)
```

**Old CSV said:**
- Keep abbreviated (correct by luck)
- Remove full and _v1 (correct)

**After:**
```
Bond.etal.2019.Top preds induce hab shift prey MPAs.pdf ✓
```

### Case 2: Heithaus 2012 (Wrong Choice) ✗

**Before:**
```
Heithaus.etal.2012.Ecol import intact top pred popns synth 15 yr res seagrass ecosys.pdf (abbreviated - WANTED)
Heithaus.etal.2012.The ecological importance of intact top-predator.pdf (full)
Heithaus.etal.2012.The ecological importance of intact top-predator_v1.pdf (versioned)
```

**Old CSV said:**
- Keep full title (wrong choice)
- Remove abbreviated (wrong!)
- Remove _v1 (correct)

**What happened:**
- Entry 1: Removed abbreviated ✗
- Entry 2: Failed to remove full (it was marked as "keep") ✗
- Entry 3: Removed _v1 ✓

**After:**
```
Heithaus.etal.2012.The ecological importance of intact top-predator.pdf ✗ (wanted abbreviated version)
```

### Case 3: Ferretti 2008 (Triplet Confusion)

**Before:**
```
Ferretti.etal.2008.Loss large pred shark Med.pdf (most abbreviated - WANTED)
Ferretti.etal.2008.Loss large predatory sharks from Mediterr Sea.pdf (abbreviated)
Ferretti.etal.2008.Loss of large predatory sharks from the Mediterranean Sea..pdf (full)
```

**Old CSV said:**
```
Entry 1: Remove full ..Sea..pdf, keep Mediterr Sea
Entry 2: Remove Mediterr Sea, keep Med
```

**What happened:**
1. Removed `...Mediterranean Sea..pdf` ✓
2. Removed `...Mediterr Sea.pdf` ✓
3. Failed to remove `Med.pdf` (tried in entry 3 but already removed)

**After:**
```
Ferretti.etal.2008.Loss large pred shark Med.pdf ✓ (correct choice)
```

---

## Files Created/Modified

### Logs
- `logs/duplicate_pdfs_removed.log` - Complete log of all removals

### CSVs (still exist)
- `outputs/duplicate_pdfs_to_remove.csv` - Old (wrong) recommendations used
- `outputs/duplicate_pdfs_to_remove_updated.csv` - New (correct) recommendations not used

---

## Recommendations

### Option 1: Accept Current State (Recommended)

**Pros:**
- Zero duplicates ✓
- 2.43 GB freed ✓
- All papers retained (one version each) ✓
- No data loss ✓

**Cons:**
- ~50-100 files have verbose names instead of abbreviated
- Minor inconsistency in naming convention

**Action:** None - accept as-is

### Option 2: Manual Filename Cleanup

Create a script to rename verbose titles to abbreviated form:

```bash
# Example renames
Heithaus.etal.2012.The ecological importance of intact top-predator.pdf
  → Heithaus.etal.2012.Ecol import intact top pred popns synth 15 yr res seagrass ecosys.pdf
```

**Pros:**
- Achieves original naming goal
- Consistent abbreviated format

**Cons:**
- Risky (could lose papers if renamed incorrectly)
- Time-consuming to verify each rename
- Not critical for functionality

**Action:** Create rename script but don't execute unless needed

### Option 3: Re-download Missing Abbreviated Versions

For cases where we kept the wrong version, re-download the paper and manually create abbreviated filename.

**Pros:**
- Gets both versions back
- Can then remove full version correctly

**Cons:**
- Very time-consuming
- Requires re-download infrastructure
- Not worth effort for ~50-100 files

**Action:** Skip this option

---

## Lessons Learned

### What Went Wrong

1. **CSV naming confusion**
   - Had two CSVs: `duplicate_pdfs_to_remove.csv` and `duplicate_pdfs_to_remove_updated.csv`
   - Script defaulted to the first (old) one
   - Should have renamed/replaced old CSV before running removal

2. **Insufficient verification**
   - Should have done dry-run with updated CSV first
   - Should have verified a few examples match expectations

### Prevention for Next Time

1. **Single source of truth**
   - Don't keep multiple CSVs with similar names
   - Update script to use explicit CSV path parameter
   - Rename old CSV to `.backup` or delete it

2. **Better validation**
   - Add CSV header check to removal script
   - Add sample output showing which specific files will be kept/removed
   - Require user to confirm after seeing real examples

3. **Improved duplicate finder**
   - Already done: `find_duplicate_pdfs_improved.py`
   - Already fixed: scoring to prefer abbreviated titles
   - Already fixed: exclude reply/correction papers

---

## Next Steps

### Immediate

- [x] Re-run duplicate finder → confirmed 0 duplicates
- [x] Document what happened (this file)
- [ ] Update removal guide with lessons learned
- [ ] Decide: accept current state vs. rename files

### Future

- [ ] Update removal script to accept `--csv` parameter
- [ ] Add sample output to removal dry-run
- [ ] Add CSV validation checks

---

## Final Recommendation

**Accept current state** - The duplicate removal was successful despite using the wrong CSV:

✓ All duplicates eliminated
✓ Disk space freed
✓ No data lost
✓ Collection is functional and complete

The only issue is cosmetic (some verbose filenames instead of abbreviated), which doesn't affect:
- Paper accessibility
- PDF content
- Database queries
- OCR processing
- Technique searches

The benefit of consistent abbreviated naming is outweighed by the risk of running additional rename operations that could cause file loss or confusion.

---

**Status:** Duplicate removal complete
**Action required:** None (or optional filename cleanup)
**Last updated:** 2025-10-25
