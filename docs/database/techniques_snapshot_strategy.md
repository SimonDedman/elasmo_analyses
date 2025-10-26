# Techniques Database Snapshot Strategy

**Date:** 2025-10-21
**Purpose:** Version control for techniques database during panelist updates

---

## Current Snapshot

**File:** `data/techniques_snapshot_v20251021.csv`
**Version:** v20251021 (October 21, 2025)
**Techniques:** 216
**Status:** ✅ Complete (all search queries populated, all classified)

---

## Snapshot Contents

### Fields Included (14 columns)

| Field | Purpose | Completeness |
|-------|---------|--------------|
| `discipline` | Discipline assignment | 100% |
| `category_name` | Category within discipline | 100% |
| `technique_name` | Technique name | 100% |
| `is_parent` | Parent/child hierarchy flag | 100% |
| `parent_technique` | Parent technique name | As applicable |
| `description` | Technique description | ~95% |
| `synonyms` | Alternative names | ~60% |
| `search_query` | Primary search query | 100% ✅ |
| `search_query_alt` | Alternative search query | 87.5% |
| `data_collection_technology` | Classification type | 20% |
| `statistical_model` | Classification type | 12% |
| `analytical_algorithm` | Classification type | 44% |
| `inference_framework` | Classification type | 2% |
| `software` | Classification type | 6% |
| `conceptual_field` | Classification type | 26% |

---

## Extraction Pipeline Use

### Phase 1: Initial Extraction (NOW)

```python
# Use snapshot for extraction
techniques = pd.read_csv('data/techniques_snapshot_v20251021.csv')

# Extract techniques from papers
for idx, tech in techniques.iterrows():
    extract_technique(papers, tech['search_query'], tech['technique_name'])

# Populate 216 technique columns in SQL database
```

**Benefits:**
- ✅ Stable baseline (won't change during extraction)
- ✅ Reproducible results
- ✅ Can re-run with same version

---

### Phase 2: Detecting Updates (LATER)

When panelists add new techniques, compare versions:

```python
import pandas as pd

# Load snapshots
current = pd.read_csv('data/techniques_snapshot_v20251021.csv')
updated = pd.read_excel('data/Techniques DB for Panel Review.xlsx', sheet_name='Full_List')
updated = updated[updated['technique_name'].notna()]

# Find new techniques
new_techniques = updated[~updated['technique_name'].isin(current['technique_name'])]

print(f"New techniques added: {len(new_techniques)}")
for idx, tech in new_techniques.iterrows():
    print(f"  • [{tech['discipline']}] {tech['technique_name']}")
```

**Output example:**
```
New techniques added: 5
  • [GEN] CRISPR Analysis
  • [MOV] Drone Tracking
  • [DATA] Graph Neural Networks
  • [BIO] Proteomics
  • [FISH] Electronic Monitoring
```

---

### Phase 3: Incremental Update (WHEN NEEDED)

```python
# Add new technique columns to existing database
for idx, tech in new_techniques.iterrows():
    # Add new column
    col_name = f"a_{tech['technique_name'].lower().replace(' ', '_')}"
    df_sql[col_name] = False

    # Re-search all 30k papers for this new technique
    df_sql[col_name] = df_sql.apply(
        lambda row: search_for_technique(row, tech['search_query']),
        axis=1
    )

# Export updated database
df_sql.to_parquet('outputs/literature_review_updated.parquet')
```

**Benefits:**
- ✅ No need to re-extract everything
- ✅ Just search for new techniques
- ✅ Maintains data integrity
- ✅ Fast (minutes, not hours)

---

## Snapshot Versioning Convention

**Format:** `techniques_snapshot_vYYYYMMDD.csv`

**Examples:**
- `techniques_snapshot_v20251021.csv` (initial, 216 techniques)
- `techniques_snapshot_v20251115.csv` (after panelist updates, 225 techniques)
- `techniques_snapshot_v20260115.csv` (final version, 240 techniques)

**When to create new snapshot:**
1. Before major extraction run
2. After significant panelist updates (10+ new techniques)
3. Before distributing database to stakeholders

---

## Diff Strategy

### Compare Two Snapshots

```python
def compare_snapshots(old_file, new_file):
    """
    Compare two technique snapshots and report changes
    """
    old = pd.read_csv(old_file)
    new = pd.read_csv(new_file)

    # New techniques
    added = new[~new['technique_name'].isin(old['technique_name'])]

    # Removed techniques (rare, but possible if consolidating)
    removed = old[~old['technique_name'].isin(new['technique_name'])]

    # Modified search queries
    merged = old.merge(
        new,
        on='technique_name',
        suffixes=('_old', '_new'),
        how='inner'
    )
    modified = merged[
        merged['search_query_old'] != merged['search_query_new']
    ]

    print(f"Added: {len(added)}")
    print(f"Removed: {len(removed)}")
    print(f"Modified search queries: {len(modified)}")

    return {
        'added': added,
        'removed': removed,
        'modified': modified
    }

# Usage
changes = compare_snapshots(
    'data/techniques_snapshot_v20251021.csv',
    'data/techniques_snapshot_v20251115.csv'
)
```

---

## Handling Different Types of Changes

### 1. New Techniques Added

**Action:** Incremental extraction (add columns, search papers)
**Timeline:** ~10 minutes per new technique
**Impact:** Low (only affects new columns)

---

### 2. Search Queries Modified

**Example:** Panelist improves search query for better accuracy

**Action:** Re-extract affected technique column
```python
# Re-extract "Acoustic Telemetry" with new query
df_sql['a_acoustic_telemetry'] = df_sql.apply(
    lambda row: search_for_technique(row, new_search_query),
    axis=1
)
```

**Timeline:** ~10 minutes per modified technique
**Impact:** Medium (may change paper assignments)

---

### 3. Techniques Removed/Consolidated

**Example:** "GPS Tracking" and "Satellite Tracking" consolidated into one

**Action:**
1. Mark old columns as deprecated
2. Migrate data to consolidated column
3. Document in changelog

**Timeline:** ~30 minutes
**Impact:** High (requires careful data migration)

---

## Quality Control

### Before Creating Snapshot

**Checklist:**
- [ ] All techniques have `search_query` populated
- [ ] All techniques have `technique_name` populated
- [ ] No duplicate technique names
- [ ] All classifications validated
- [ ] Descriptions reviewed

**Validation Script:**
```python
def validate_techniques(df):
    """
    Validate techniques database before snapshot
    """
    issues = []

    # Check for missing search queries
    missing_query = df[df['search_query'].isna()]
    if len(missing_query) > 0:
        issues.append(f"Missing search_query: {len(missing_query)} techniques")

    # Check for duplicate names
    duplicates = df[df.duplicated('technique_name', keep=False)]
    if len(duplicates) > 0:
        issues.append(f"Duplicate names: {len(duplicates)} techniques")

    # Check for unclassified techniques
    class_cols = ['data_collection_technology', 'statistical_model',
                  'analytical_algorithm', 'inference_framework',
                  'software', 'conceptual_field']
    unclassified = df[df[class_cols].sum(axis=1) == 0]
    if len(unclassified) > 0:
        issues.append(f"Unclassified: {len(unclassified)} techniques")

    if len(issues) == 0:
        print("✓ All validation checks passed")
        return True
    else:
        print("⚠️  Validation issues found:")
        for issue in issues:
            print(f"  • {issue}")
        return False
```

---

## Current Snapshot Summary (v20251021)

### Statistics

```
Total techniques: 216
Disciplines: 8
  • BEH (Behaviour & Sensory): 21
  • BIO (Biology & Health): 30
  • CON (Conservation & Policy): 19
  • DATA (Data Science): 28
  • FISH (Fisheries Management): 34
  • GEN (Genetics & Genomics): 32
  • MOV (Movement & Spatial): 32
  • TRO (Trophic Ecology): 20

Search queries: 100% complete
Classifications: 100% complete
Ready for extraction: ✅ YES
```

### Extraction Readiness

| Component | Status | Notes |
|-----------|--------|-------|
| Search queries | ✅ Ready | All 216 have primary query |
| Alternative queries | ✅ Ready | 189/216 (87.5%) have alt query |
| Classifications | ✅ Ready | All 216 classified (0 unclassified) |
| Descriptions | ✅ Ready | Most have descriptions |
| Snapshot created | ✅ Ready | v20251021 saved |

---

## Recommended Workflow

### Week 1: Initial Extraction
```
1. Use techniques_snapshot_v20251021.csv (216 techniques)
2. Extract from 30,523 papers
3. Populate 216 technique columns
4. Generate quality report
```

### Week 4: Check for Updates
```
1. Compare current Excel vs snapshot
2. If <5 new techniques: note for next cycle
3. If 5-10 new techniques: incremental update
4. If >10 new techniques: create new snapshot + full re-extraction
```

### Month 3: Final Snapshot
```
1. Panelists finalize techniques list
2. Create techniques_snapshot_vFINAL.csv
3. Run final extraction
4. Lock database for analysis
```

---

## Benefits of Snapshot Strategy

### ✅ Reproducibility
- Exact version used for extraction is documented
- Can re-run extraction with same inputs
- Results are comparable across runs

### ✅ Flexibility
- Easy to add new techniques without re-doing everything
- Can test different search queries without affecting production
- Rollback to previous version if needed

### ✅ Collaboration
- Panelists can continue updating Excel file
- Extraction uses stable snapshot
- Merge updates when ready

### ✅ Quality Control
- Validation before snapshot creation
- Clear audit trail of changes
- Easy to identify when techniques were added

---

## Next Steps

1. ✅ **Snapshot created** (v20251021, 216 techniques)
2. ⏳ **Build extraction script** using snapshot
3. ⏳ **Extract techniques** from 30k papers
4. ⏳ **Generate quality report** (precision/recall)
5. ⏳ **Wait for panelist updates** (weeks/months)
6. ⏳ **Create new snapshot** when updates substantial
7. ⏳ **Incremental re-extraction** for new techniques only

---

## File Locations

```
data/
├── Techniques DB for Panel Review.xlsx       (LIVE - panelists editing)
├── techniques_snapshot_v20251021.csv         (SNAPSHOT - for extraction)
└── techniques_snapshot_v20251115.csv         (FUTURE - after updates)

outputs/
├── literature_review.parquet                 (EXTRACTED - from v20251021)
└── literature_review_updated.parquet         (UPDATED - with new techniques)

scripts/
└── shark_references_to_sql.py                (USES snapshot, not live Excel)
```

---

**Strategy approved:** Use versioned snapshots for stable extraction, easy updates, and clear audit trail.

**Current status:** Ready to proceed with extraction using v20251021 (216 techniques)
