# Project Cleanup Plan - Complete Review

**Date:** 2025-10-21
**Total Files to Process:** 18 files

---

## Executive Summary

| Category | Count | Recommendation |
|----------|-------|----------------|
| **Rename to snake_case** | 8 | EXECUTE |
| **Delete test scripts** | 4 | EXECUTE |
| **Delete test outputs** | 2 | EXECUTE |
| **Delete debug files** | 1 | EXECUTE |
| **Delete lock files** | 1 | EXECUTE |
| **Delete Python cache** | 2 | EXECUTE |
| **Delete redundant docs** | 1 | EXECUTE |
| **TOTAL** | **18** | |

---

## 1. RENAME TO SNAKE_CASE (8 files)

### Documentation Files with Mixed Case

All documentation should follow `snake_case.md` convention:

```
docs/README.md
  → docs/readme.md

docs/species/BULK_DOWNLOAD_QUICKSTART.md
  → docs/species/bulk_download_quickstart.md

docs/species/shark_references_bulk_download_strategy_CORRECTED.md
  → docs/species/shark_references_bulk_download_strategy_corrected.md

docs/techniques/CLASSIFICATION_SCHEMA_VISUAL_SUMMARY.md
  → docs/techniques/classification_schema_visual_summary.md

docs/techniques/DATABASE_IMPLEMENTATION_COMPLETE.md
  → docs/techniques/database_implementation_complete.md

docs/techniques/JOHANN_ADDITIONS_SEARCH_QUERIES.md
  → docs/techniques/johann_additions_search_queries.md

docs/techniques/TECHNIQUE_CLASSIFICATION_SCHEMA_PROPOSAL.md
  → docs/techniques/technique_classification_schema_proposal.md

docs/techniques/TECHNIQUE_DATABASE_UPDATES_SUMMARY.md
  → docs/techniques/technique_database_updates_summary.md
```

**Action:** RENAME all 8 files
**Impact:** Consistent naming convention
**Risk:** LOW (git tracks renames)

---

## 2. DELETE TEST SCRIPTS (4 files)

### Development/Exploration Scripts - No Longer Needed

These were used during initial development. Their findings are now incorporated into production scripts.

```
scripts/test_detail_ajax.py (4.4 KB)
  • Purpose: Tested AJAX endpoint structure
  • Findings: Incorporated into shark_references_complete_download.py
  • Status: OBSOLETE

scripts/test_download_button.py (2.9 KB)
  • Purpose: Tested PDF URL extraction
  • Findings: Incorporated into shark_references_complete_download.py
  • Status: OBSOLETE

scripts/test_search_operators.py (3.8 KB)
  • Purpose: Tested search operators (+, OR)
  • Findings: Documented in strategy docs
  • Status: OBSOLETE

scripts/test_shark_references_fields.py (5.4 KB)
  • Purpose: Explored available fields
  • Findings: Incorporated into shark_references_complete_download.py
  • Status: OBSOLETE
```

**Action:** DELETE all 4 test scripts
**Impact:** ~16 KB freed, cleaner scripts/ directory
**Risk:** LOW (development phase complete)

---

## 3. DELETE TEST OUTPUTS (2 files)

### Sample/Test Data Files

```
outputs/shark_references_raw/TEST-sampling-cloacal_swab_test_20251017.csv (2.2 KB)
  • Purpose: Test search result from early development
  • Status: Superseded by actual bulk download
  • Action: DELETE

outputs/shark_references_raw/debug_html.html (101 KB)
  • Purpose: Debug HTML capture during development
  • Status: Development artifact
  • Action: DELETE
```

**Action:** DELETE both test output files
**Impact:** ~103 KB freed, cleaner outputs/ directory
**Risk:** LOW (sample data only)

---

## 4. DELETE TEMPORARY FILES (3 files)

### Lock Files & Python Cache

```
outputs/shark_references_bulk/.~lock.master_cumulative_2025_to_1950.csv# (86 bytes)
  • Purpose: LibreOffice lock file (temporary)
  • Status: Should not be in git
  • Action: DELETE

__pycache__/ directories and .pyc files (2 items)
  • Purpose: Compiled Python bytecode
  • Status: Should be in .gitignore, not tracked
  • Action: DELETE
```

**Action:** DELETE all 3 temporary files
**Impact:** Cleaner repository
**Risk:** NONE (regenerated automatically)

---

## 5. DELETE REDUNDANT DOCUMENTATION (1 file)

### Superseded Strategy Document

```
docs/species/shark_references_bulk_download_strategy.md
  • Status: SUPERSEDED by corrected version
  • Problem: Contains incorrect efficiency calculations
  • Correction: shark_references_bulk_download_strategy_corrected.md
  • Action: DELETE
```

**History:**
- Original calculated efficiency without accounting for paper overlap
- User corrected: "bulk download gets each paper ONCE"
- Corrected version created with accurate 10.7x efficiency analysis
- Original is now obsolete and potentially confusing

**Alternative:** Archive to `docs/archive/` (preserves history)

**Recommendation:** DELETE (corrected version documents the issue)

---

## DETAILED EXECUTION PLAN

### Phase 1: Rename Documentation (8 operations)

```bash
cd "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"

# Rename all mixed-case docs to snake_case
mv "docs/README.md" "docs/readme.md"
mv "docs/species/BULK_DOWNLOAD_QUICKSTART.md" "docs/species/bulk_download_quickstart.md"
mv "docs/species/shark_references_bulk_download_strategy_CORRECTED.md" "docs/species/shark_references_bulk_download_strategy_corrected.md"
mv "docs/techniques/CLASSIFICATION_SCHEMA_VISUAL_SUMMARY.md" "docs/techniques/classification_schema_visual_summary.md"
mv "docs/techniques/DATABASE_IMPLEMENTATION_COMPLETE.md" "docs/techniques/database_implementation_complete.md"
mv "docs/techniques/JOHANN_ADDITIONS_SEARCH_QUERIES.md" "docs/techniques/johann_additions_search_queries.md"
mv "docs/techniques/TECHNIQUE_CLASSIFICATION_SCHEMA_PROPOSAL.md" "docs/techniques/technique_classification_schema_proposal.md"
mv "docs/techniques/TECHNIQUE_DATABASE_UPDATES_SUMMARY.md" "docs/techniques/technique_database_updates_summary.md"
```

### Phase 2: Delete Test Scripts (4 operations)

```bash
# Remove development test scripts
rm "scripts/test_detail_ajax.py"
rm "scripts/test_download_button.py"
rm "scripts/test_search_operators.py"
rm "scripts/test_shark_references_fields.py"
```

### Phase 3: Delete Test/Debug Outputs (2 operations)

```bash
# Remove test and debug output files
rm "outputs/shark_references_raw/TEST-sampling-cloacal_swab_test_20251017.csv"
rm "outputs/shark_references_raw/debug_html.html"
```

### Phase 4: Delete Temporary Files (3 operations)

```bash
# Remove lock file
rm "outputs/shark_references_bulk/.~lock.master_cumulative_2025_to_1950.csv#"

# Remove Python cache
rm -rf __pycache__
find . -name "*.pyc" -delete
```

### Phase 5: Delete Redundant Documentation (1 operation)

```bash
# Remove superseded strategy doc
rm "docs/species/shark_references_bulk_download_strategy.md"
```

---

## VERIFICATION CHECKLIST

After execution:

### File Naming
- [ ] All docs/ files use snake_case
- [ ] No UPPERCASE in filenames
- [ ] README.md → readme.md

### Scripts Directory
- [ ] Only 5 production scripts remain
- [ ] No test_* scripts
- [ ] All scripts are functional

### Outputs Directory
- [ ] No TEST-* files
- [ ] No debug_* files
- [ ] No lock files
- [ ] Production data intact

### Documentation
- [ ] Only corrected strategy doc exists
- [ ] No redundant/superseded docs
- [ ] All references updated

### Git Status
- [ ] Renames tracked properly
- [ ] Deletions committed
- [ ] Clean working directory

---

## BEFORE vs AFTER

### Scripts Directory

**Before:**
```
scripts/
├── shark_references_bulk_download.py ✅
├── shark_references_bulk_download_by_year.py ✅
├── shark_references_complete_download.py ✅
├── shark_references_search.py ✅
├── test_detail_ajax.py 🧪
├── test_download_button.py 🧪
├── test_search_operators.py 🧪
├── test_shark_references_fields.py 🧪
└── update_shark_references_species.py ✅

Total: 9 files
```

**After:**
```
scripts/
├── shark_references_bulk_download.py ✅
├── shark_references_bulk_download_by_year.py ✅
├── shark_references_complete_download.py ✅
├── shark_references_search.py ✅
└── update_shark_references_species.py ✅

Total: 5 files (4 removed)
```

### Documentation - Techniques

**Before:**
```
docs/techniques/
├── CLASSIFICATION_SCHEMA_VISUAL_SUMMARY.md 🔤
├── DATABASE_IMPLEMENTATION_COMPLETE.md 🔤
├── JOHANN_ADDITIONS_SEARCH_QUERIES.md 🔤
├── TECHNIQUE_CLASSIFICATION_SCHEMA_PROPOSAL.md 🔤
├── TECHNIQUE_DATABASE_UPDATES_SUMMARY.md 🔤
├── discipline_population_report.md ✅
├── discipline_structure_analysis.md ✅
├── expansion_summary_report.md ✅
├── master_techniques_list_for_population.md ✅
├── technique_expansion_list.md ✅
└── techniques_amalgamation_report.md ✅

Total: 11 files (5 with mixed case)
```

**After:**
```
docs/techniques/
├── classification_schema_visual_summary.md ✅
├── database_implementation_complete.md ✅
├── discipline_population_report.md ✅
├── discipline_structure_analysis.md ✅
├── expansion_summary_report.md ✅
├── johann_additions_search_queries.md ✅
├── master_techniques_list_for_population.md ✅
├── technique_classification_schema_proposal.md ✅
├── technique_database_updates_summary.md ✅
├── technique_expansion_list.md ✅
└── techniques_amalgamation_report.md ✅

Total: 11 files (all snake_case)
```

### Documentation - Species

**Before:**
```
docs/species/
├── BULK_DOWNLOAD_QUICKSTART.md 🔤
├── shark_references_automation_workflow.md ✅
├── shark_references_bulk_download_strategy.md ⚠️ REDUNDANT
├── shark_references_bulk_download_strategy_CORRECTED.md 🔤
├── shark_references_species_database_extraction.md ✅
├── shark_references_update_script_readme.md ✅
├── shark_species_extraction_summary.md ✅
└── species_lookup_analysis_summary.md ✅

Total: 8 files (2 with mixed case, 1 redundant)
```

**After:**
```
docs/species/
├── bulk_download_quickstart.md ✅
├── shark_references_automation_workflow.md ✅
├── shark_references_bulk_download_strategy_corrected.md ✅
├── shark_references_species_database_extraction.md ✅
├── shark_references_update_script_readme.md ✅
├── shark_species_extraction_summary.md ✅
└── species_lookup_analysis_summary.md ✅

Total: 7 files (all snake_case, redundant removed)
```

---

## FILE SIZE SAVINGS

| Category | Size Saved |
|----------|-----------|
| Test scripts | ~16 KB |
| Test outputs | ~103 KB |
| Lock files | ~86 bytes |
| Python cache | ~varies |
| **Total** | **~120 KB** |

**Note:** Size savings minimal, main benefit is organization and clarity

---

## RISK ASSESSMENT

| Action | Files | Risk | Reversible? |
|--------|-------|------|-------------|
| Rename docs | 8 | 🟢 LOW | ✅ Yes (git) |
| Delete tests | 4 | 🟢 LOW | ✅ Yes (git) |
| Delete outputs | 2 | 🟢 LOW | ⚠️ Sample data |
| Delete temp | 3 | 🟢 NONE | ✅ Regenerated |
| Delete redundant | 1 | 🟡 MEDIUM | ✅ Yes (git) |

**Overall Risk:** 🟢 **LOW** - All actions reversible via git history

---

## RECOMMENDATIONS

### Immediate Actions (EXECUTE)

✅ **Approve all 18 operations**

Reasoning:
1. **Renames** improve consistency (snake_case standard)
2. **Test deletions** remove development artifacts
3. **Output deletions** remove sample/debug data
4. **Temp deletions** clean up lock/cache files
5. **Redundant deletion** prevents confusion (corrected version exists)

### Optional: Archive Instead of Delete

For redundant doc only:
- **Option A:** DELETE (recommended - corrected version documents the error)
- **Option B:** ARCHIVE to `docs/archive/` (preserves full history)

**My recommendation:** Option A (DELETE)

### .gitignore Updates

Add to `.gitignore`:
```
# Python
__pycache__/
*.pyc
*.pyo

# Temporary files
.~lock*
*.tmp

# Editor files
.vscode/
.idea/
```

---

## APPROVAL REQUEST

Please confirm action for each category:

### Category 1: Rename (8 files)
- [ ] **APPROVED:** Rename all docs to snake_case

### Category 2: Delete Tests (4 files)
- [ ] **APPROVED:** Delete test_*.py scripts

### Category 3: Delete Outputs (2 files)
- [ ] **APPROVED:** Delete TEST-* and debug_*.html

### Category 4: Delete Temp (3 files)
- [ ] **APPROVED:** Delete lock files and Python cache

### Category 5: Delete Redundant (1 file)
- [ ] **APPROVED - DELETE:** Remove original strategy doc
- [ ] **ALTERNATIVE - ARCHIVE:** Move to docs/archive/

---

## POST-CLEANUP ACTIONS

After cleanup:

1. **Update .gitignore** - Add patterns for temp files
2. **Commit changes** - Single commit with clear message
3. **Verify links** - Check internal doc references
4. **Update README** - If it references renamed files

---

**Status:** Ready for execution upon approval

**Total operations:** 18 files affected
**Estimated time:** < 2 minutes
**Recommendation:** EXECUTE ALL

---

