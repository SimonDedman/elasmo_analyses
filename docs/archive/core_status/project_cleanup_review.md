# Project Cleanup Review

**Date:** 2025-10-21
**Purpose:** Convert filenames to snake_case and remove redundant/test files

---

## Summary

| Category | Count | Action |
|----------|-------|--------|
| Files to rename | 8 | Convert to snake_case |
| Test scripts | 4 | DELETE (development artifacts) |
| Test outputs | 1 | DELETE (sample data) |
| Redundant docs | 1 | ARCHIVE (superseded) |
| **Total files to process** | **14** | |

---

## Section 1: FILES TO RENAME (8 files)

### Documentation - Convert to snake_case

| Current Name | New Name | Action |
|--------------|----------|--------|
| `docs/README.md` | `docs/readme.md` | RENAME |
| `docs/species/BULK_DOWNLOAD_QUICKSTART.md` | `docs/species/bulk_download_quickstart.md` | RENAME |
| `docs/species/shark_references_bulk_download_strategy_CORRECTED.md` | `docs/species/shark_references_bulk_download_strategy_corrected.md` | RENAME |
| `docs/techniques/CLASSIFICATION_SCHEMA_VISUAL_SUMMARY.md` | `docs/techniques/classification_schema_visual_summary.md` | RENAME |
| `docs/techniques/DATABASE_IMPLEMENTATION_COMPLETE.md` | `docs/techniques/database_implementation_complete.md` | RENAME |
| `docs/techniques/JOHANN_ADDITIONS_SEARCH_QUERIES.md` | `docs/techniques/johann_additions_search_queries.md` | RENAME |
| `docs/techniques/TECHNIQUE_CLASSIFICATION_SCHEMA_PROPOSAL.md` | `docs/techniques/technique_classification_schema_proposal.md` | RENAME |
| `docs/techniques/TECHNIQUE_DATABASE_UPDATES_SUMMARY.md` | `docs/techniques/technique_database_updates_summary.md` | RENAME |

**Rationale:** Consistent snake_case naming convention throughout project

---

## Section 2: TEST SCRIPTS (4 files) - RECOMMEND DELETE

These were used during initial development/exploration and are no longer needed:

### Test Scripts in `scripts/`

| File | Size | Purpose | Action |
|------|------|---------|--------|
| `test_detail_ajax.py` | 4,446 bytes | Test AJAX endpoint structure | **DELETE** |
| `test_download_button.py` | 2,862 bytes | Test PDF URL extraction | **DELETE** |
| `test_search_operators.py` | 3,816 bytes | Test search operators (+, OR) | **DELETE** |
| `test_shark_references_fields.py` | 5,449 bytes | Test available fields | **DELETE** |

**Rationale:**
- These were exploration/development scripts
- Findings incorporated into main script (`shark_references_complete_download.py`)
- Not needed for production use
- Keep main scripts only

**Impact:** ~16 KB freed, cleaner scripts directory

---

## Section 3: TEST OUTPUTS (1 file) - RECOMMEND DELETE

### Test Output Files in `outputs/`

| File | Size | Purpose | Action |
|------|------|---------|--------|
| `outputs/shark_references_raw/TEST-sampling-cloacal_swab_test_20251017.csv` | 2,247 bytes | Test search result | **DELETE** |

**Rationale:**
- Sample test data from early development
- Superseded by actual bulk download
- No analytical value

**Impact:** Cleaner outputs directory

---

## Section 4: REDUNDANT DOCUMENTATION (1 file) - RECOMMEND ARCHIVE

### Superseded Strategy Document

**Original:** `docs/species/shark_references_bulk_download_strategy.md`
**Corrected Version:** `docs/species/shark_references_bulk_download_strategy_CORRECTED.md`

**History:**
1. Original strategy document had efficiency calculation error
2. User corrected understanding (bulk is 10.7x more efficient)
3. Corrected version created with accurate analysis

**Recommendation:**

| File | Action | Rationale |
|------|--------|-----------|
| `shark_references_bulk_download_strategy.md` | **ARCHIVE** or **DELETE** | Contains incorrect efficiency calculations |
| `shark_references_bulk_download_strategy_CORRECTED.md` | **KEEP** (will be renamed) | Accurate analysis, current reference |

**Option A - Archive:**
- Move to `docs/archive/shark_references_bulk_download_strategy_original.md`
- Preserves history of thought process

**Option B - Delete:**
- Remove entirely to avoid confusion
- Corrected version is the single source of truth

**Recommendation:** DELETE (corrected version documents the correction)

---

## Section 5: MAIN SCRIPTS - KEEP ALL

### Production Scripts in `scripts/` (5 files)

| File | Purpose | Status |
|------|---------|--------|
| `shark_references_complete_download.py` | **PRIMARY** - Bulk download with all fields | ✅ KEEP |
| `shark_references_bulk_download_by_year.py` | Year-by-year download (basic fields only) | ✅ KEEP |
| `shark_references_bulk_download.py` | Simple bulk download | ✅ KEEP |
| `shark_references_search.py` | Single search execution | ✅ KEEP |
| `update_shark_references_species.py` | Species database updates | ✅ KEEP |

**All production scripts are kept - no deletions**

---

## Execution Plan

### Phase 1: Rename Files (8 operations)

```bash
# Documentation files
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
# Test scripts
rm "scripts/test_detail_ajax.py"
rm "scripts/test_download_button.py"
rm "scripts/test_search_operators.py"
rm "scripts/test_shark_references_fields.py"
```

### Phase 3: Delete Test Outputs (1 operation)

```bash
# Test output
rm "outputs/shark_references_raw/TEST-sampling-cloacal_swab_test_20251017.csv"
```

### Phase 4: Delete Redundant Documentation (1 operation)

```bash
# Superseded strategy doc
rm "docs/species/shark_references_bulk_download_strategy.md"
```

---

## Verification Checklist

After cleanup, verify:

- [ ] All renamed files are accessible
- [ ] No broken links in documentation
- [ ] Main scripts still functional
- [ ] Project structure cleaner
- [ ] All production data intact

---

## File Counts Summary

### Before Cleanup

```
Documentation: 39 files (8 with mixed case)
Scripts: 9 files (4 test, 5 main)
Outputs: Many (including 1 test file)
```

### After Cleanup

```
Documentation: 38 files (0 with mixed case, 1 redundant removed)
Scripts: 5 files (all production)
Outputs: Many (test files removed)
```

**Total removed:** 6 files (~20 KB)
**Total renamed:** 8 files

---

## Recommendations by Action Type

### ✅ APPROVED FOR EXECUTION (Recommend)

1. **RENAME** all 8 documentation files → snake_case
2. **DELETE** all 4 test scripts → no longer needed
3. **DELETE** 1 test output file → sample data
4. **DELETE** 1 redundant doc → superseded by corrected version

**Total operations:** 14

### ⚠️ USER DECISION REQUIRED

**None** - All recommendations are straightforward cleanup

---

## Risk Assessment

| Action | Risk Level | Mitigation |
|--------|------------|------------|
| Rename docs | 🟢 LOW | Git tracks renames, easy to revert |
| Delete test scripts | 🟢 LOW | Code incorporated into main scripts |
| Delete test outputs | 🟢 LOW | Sample data, easily regenerated |
| Delete redundant doc | 🟡 MEDIUM | Could archive instead if history valued |

**Overall Risk:** 🟢 LOW - All actions are reversible via git

---

## Benefits

1. **Consistency:** All files follow snake_case convention
2. **Clarity:** No confusion between corrected vs original docs
3. **Maintainability:** Cleaner codebase, easier to navigate
4. **Professionalism:** Production-ready structure

---

## Approval Requested

Please confirm:

- [ ] **APPROVE:** Rename all 8 files to snake_case
- [ ] **APPROVE:** Delete 4 test scripts
- [ ] **APPROVE:** Delete 1 test output
- [ ] **APPROVE:** Delete superseded strategy doc (or ARCHIVE instead?)

**Alternative for redundant doc:**
- [ ] DELETE `shark_references_bulk_download_strategy.md`
- [ ] ARCHIVE to `docs/archive/` (preserves history)

---

**Ready to execute upon approval.**
