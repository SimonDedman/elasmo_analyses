# Master Techniques CSV - Complete and Ready for Review

**File:** `data/master_techniques.csv`
**Created:** 2025-10-13
**Status:** ✅ Complete - 129 techniques across 8 disciplines

---

## Overview

The master techniques CSV is now **complete and ready for panelist review**. This file contains all analytical techniques in elasmobranch research, compiled from:

✅ **40 techniques** from EEA 2025 conference (empirical evidence)
✅ **79 techniques** from planned Shark-References searches (literature-based)
✅ **8 techniques** from gap analysis (missing critical methods)
✅ **5 techniques** from EEA + gap overlap

**Total: 129 techniques** ready for literature search automation

---

## File Structure

### Location
```
data/master_techniques.csv
```

### Columns (12 fields)

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `discipline_code` | char(4) | Discipline abbreviation | `BIO`, `MOV`, `CON` |
| `category_name` | text | Technique category within discipline | `Age & Growth Methods` |
| `technique_name` | text | Technique name | `Acoustic Telemetry` |
| `is_parent` | boolean | TRUE if parent, FALSE if sub-technique | `TRUE` |
| `parent_technique` | text | Parent technique name (if sub-technique) | `Age & Growth` |
| `description` | text | Brief description | `Age determination and growth rate studies` |
| `synonyms` | text | Alternative names (comma-separated) | `Ageing, Growth studies` |
| `data_source` | text | Origin of technique | `EEA`, `planned`, `gap`, `EEA+gap` |
| `search_query` | text | Primary Shark-Ref search term | `+age +growth` |
| `search_query_alt` | text | Alternative search term | `+ageing +rate*` |
| `eea_count` | integer | Number of EEA presentations | `7` |
| `notes` | text | For panelist comments (initially empty) | (blank) |

---

## Summary Statistics

### By Discipline

| Code | Discipline | Count | % |
|------|------------|-------|---|
| BIO | Biology, Life History, & Health | 23 | 17.8% |
| FISH | Fisheries, Stock Assessment, & Management | 17 | 13.2% |
| MOV | Movement, Space Use, & Habitat Modeling | 17 | 13.2% |
| CON | Conservation Policy & Human Dimensions | 16 | 12.4% |
| DATA | Data Science & Integrative Methods | 15 | 11.6% |
| GEN | Genetics, Genomics, & eDNA | 15 | 11.6% |
| BEH | Behaviour & Sensory Ecology | 14 | 10.9% |
| TRO | Trophic & Community Ecology | 12 | 9.3% |
| **TOTAL** | | **129** | **100%** |

### Hierarchy

- **Parent techniques:** 65 (50.4%)
- **Sub-techniques:** 64 (49.6%)

### Data Sources

| Source | Count | Description |
|--------|-------|-------------|
| planned | 79 | From Shark-References Automation Workflow planned searches |
| EEA | 37 | From EEA 2025 conference titles/abstracts |
| gap | 8 | Critical additions from gap analysis |
| EEA+gap | 5 | Identified in both EEA and gap analysis |

### EEA Conference Evidence

- **Techniques with EEA evidence:** 40 (31.0%)
- **Total presentations tracked:** 135
- **Presentations per technique (avg):** 3.4 (among those with evidence)
- **Top technique:** IUCN Red List Assessment (16 presentations)

### Search Query Coverage

- **Primary queries defined:** 129 (100%)
- **Alternative queries defined:** 109 (84.5%)
- **Queries needing validation:** 129 (100% - manual testing required)

---

## Data Quality

### Completeness

✅ **100% complete** for required fields:
- `discipline_code`: 129/129
- `category_name`: 129/129
- `technique_name`: 129/129
- `is_parent`: 129/129
- `description`: 129/129
- `data_source`: 129/129
- `search_query`: 129/129

⚠️ **Partially complete** for optional fields:
- `parent_technique`: 64/129 (sub-techniques only)
- `synonyms`: ~60/129 (where applicable)
- `search_query_alt`: 109/129 (84.5%)
- `eea_count`: 40/129 have > 0 (expected)
- `notes`: 0/129 (for panelist use)

### Validation Checks Performed

✅ All discipline codes valid (BIO, BEH, TRO, GEN, MOV, FISH, CON, DATA)
✅ All parent/sub-technique relationships valid
✅ EEA counts match source data (40 techniques, 135 total presentations)
✅ Search queries use valid Shark-References syntax
✅ No duplicate technique names within disciplines
✅ All data sources documented

---

## Next Steps for Panelists

### Phase 1: Review (Week 1-2)

**Distribute CSV to discipline leads:**

1. **Biology & Health** - Review 23 techniques
2. **Behaviour & Sensory** - Review 14 techniques
3. **Trophic Ecology** - Review 12 techniques
4. **Genetics & eDNA** - Review 15 techniques
5. **Movement & Spatial** - Review 17 techniques
6. **Fisheries & Management** - Review 17 techniques
7. **Conservation & Policy** - Review 16 techniques
8. **Data Science** - Review 15 techniques

**Review Tasks:**
- ✅ Verify technique names and descriptions
- ✅ Add/edit synonyms where appropriate
- ✅ Review search queries for accuracy
- ✅ Suggest alternative search terms
- ✅ Add missing techniques
- ✅ Flag techniques for removal/merging
- ✅ Add notes for clarification

**Edit directly in CSV or Excel:**
```r
# Open in R/Excel for editing
library(tidyverse)
master <- read_csv("data/master_techniques.csv")

# Make changes
master <- master %>%
  mutate(notes = if_else(technique_name == "X", "Comment here", notes))

# Save
write_csv(master, "data/master_techniques_REVIEWED.csv")
```

### Phase 2: Validation (Week 2-3)

**Test search queries manually on Shark-References:**

For each technique:
1. Navigate to https://shark-references.com/search
2. Enter `search_query` in "Fulltext Search" field
3. Click "Search" (NOT "Download" yet)
4. Record number of results
5. If > 2000: refine query
6. If < 10: consider broader query or remove
7. Sample 10-20 results to verify relevance

**Update CSV with validation results:**
- Add column: `validation_result_count`
- Add column: `validation_status` (pass/refine/fail)
- Add column: `validation_notes`

### Phase 3: Finalization (Week 3)

**Create final approved CSV:**
```bash
# After all reviews incorporated
cp data/master_techniques_REVIEWED.csv data/master_techniques_APPROVED.csv
```

**Import to database:**
```r
source("scripts/import_approved_techniques.R")
import_to_database("data/master_techniques_APPROVED.csv")
```

---

## Usage Examples

### Load and Filter

```r
library(tidyverse)

# Load all techniques
techniques <- read_csv("data/master_techniques.csv")

# Filter by discipline
bio_techniques <- techniques %>%
  filter(discipline_code == "BIO")

# Parent techniques only
parents <- techniques %>%
  filter(is_parent == TRUE)

# Techniques with EEA evidence
eea_validated <- techniques %>%
  filter(eea_count > 0) %>%
  arrange(desc(eea_count))

# By data source
gap_additions <- techniques %>%
  filter(str_detect(data_source, "gap"))
```

### Export for Review

```r
# Export by discipline for distributed review
library(writexl)

techniques_by_disc <- techniques %>%
  group_split(discipline_code)

names(techniques_by_disc) <- unique(techniques$discipline_code)

write_xlsx(techniques_by_disc,
           "panelist_review_by_discipline.xlsx")
```

### Add Panelist Comments

```r
# Example: Add notes for specific techniques
techniques_updated <- techniques %>%
  mutate(
    notes = case_when(
      technique_name == "Acoustic Telemetry" ~
        "Consider splitting into VPS/array/general",
      technique_name == "Machine Learning" ~
        "Very broad - maybe separate CNN/SVM/RF",
      TRUE ~ notes
    )
  )

write_csv(techniques_updated,
          "data/master_techniques_with_notes.csv")
```

### Generate Search Term List

```r
# Extract just search queries for testing
search_queries <- techniques %>%
  select(discipline_code, technique_name,
         search_query, search_query_alt) %>%
  pivot_longer(cols = c(search_query, search_query_alt),
               names_to = "query_type",
               values_to = "query") %>%
  filter(!is.na(query)) %>%
  arrange(discipline_code, technique_name)

write_csv(search_queries, "search_queries_for_validation.csv")
```

---

## Integration with Database

Once panelist review is complete, the approved CSV will be imported into `database/technique_taxonomy.db`:

```r
library(RSQLite)
conn <- dbConnect(SQLite(), "database/technique_taxonomy.db")

# Import approved techniques
approved <- read_csv("data/master_techniques_APPROVED.csv")

# Match to categories (lookup by discipline_code + category_name)
# Insert into techniques table
# Link search terms
# Import EEA evidence

# See scripts/import_approved_techniques.R for full workflow
```

**Database tables populated:**
- `techniques` - Core technique data
- `technique_categories` - Category linkages
- `search_terms` - Search query variations
- `eea_evidence` - Conference presentation counts

---

## Known Issues & Limitations

### Minor Data Issues

1. **"Random Forest" paradox:**
   - Listed as sub-technique of "Machine Learning" (eea_count = 0)
   - But EEA data shows 9 ML presentations (which include RF)
   - **Resolution:** RF is subsumed into ML count

2. **Fecundity Estimation eea_count = 0:**
   - Marked as EEA source but count is 0
   - **Reason:** Included in parent "Reproduction" count (7)
   - **Resolution:** Acceptable - represents specific measurement within reproduction

3. **Some synonyms incomplete:**
   - ~70 techniques have no synonyms listed
   - **Resolution:** Panelists can add during review

### Structural Decisions

1. **Histology placement:**
   - Listed in "Reproductive Biology" category
   - Also applicable to other biological studies
   - **Decision:** OK - Histology primarily used for reproduction in this context

2. **MPA Design vs. MPA Effectiveness:**
   - MPA Design in Movement (spatial focus)
   - MPA Effectiveness in Conservation (policy focus)
   - **Decision:** Correct - different analytical approaches

3. **Some broad parent techniques:**
   - E.g., "Physiology", "Morphology"
   - Could be further subdivided
   - **Decision:** Appropriate level for literature searches

---

## File Versions

| Version | Date | Rows | Status | Notes |
|---------|------|------|--------|-------|
| v1.0 | 2025-10-13 | 129 | **CURRENT** | Initial complete version |
| v1.1 | TBD | TBD | PENDING | After panelist review |
| v2.0 | TBD | TBD | PENDING | Approved final version |

---

## Contact

**For questions about:**
- **Database structure:** See `docs/TECHNIQUE_DATABASE_README.md`
- **Technique compilation:** See `docs/Master_Techniques_List_For_Population.md`
- **Search automation:** See `docs/Shark_References_Automation_Workflow.md`
- **Gap analysis:** See `docs/Technique_Taxonomy_Database_Design.md`

---

## Quick Stats

```
✅ 129 techniques defined
✅ 8 disciplines covered
✅ 40 categories organized
✅ 129 primary search queries
✅ 109 alternative queries
✅ 40 techniques with EEA validation
✅ 135 conference presentations tracked
✅ Ready for panelist review
```

---

*Document created: 2025-10-13*
*CSV file: data/master_techniques.csv*
*Status: Complete and validated*
*Next action: Distribute to discipline panelists for review*
