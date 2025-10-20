# Master Technique Taxonomy Database

**Location:** `/database/technique_taxonomy.db`
**Created:** 2025-10-13
**Purpose:** Central repository for all elasmobranch research techniques for literature review automation

---

## Overview

This database serves as the **master source** for:
1. **Technique taxonomy** - All analytical methods across 8 disciplines
2. **Search term definitions** - Shark-References query strings for each technique
3. **EEA evidence** - Conference presentation frequencies
4. **Literature tracking** - Papers found via automated searches

**Database exists at:** `database/technique_taxonomy.db`

### Database Population Status

✅ **Schema created** - All tables and views defined
⏳ **Needs population** - Disciplines, categories, techniques, search terms
📋 **Alternative approach recommended** - Use CSV-based workflow for panelist review

---

## Recommended Workflow

### Phase 1: CSV-Based Technique List (CURRENT)

Instead of directly populating the database (which locks the structure), we'll use an **editable CSV workflow**:

1. **Create Master CSV** (`master_techniques.csv`) with columns:
   - `discipline_code` (BIO, BEH, TRO, GEN, MOV, FISH, CON, DATA)
   - `category_name`
   - `technique_name`
   - `is_parent` (TRUE/FALSE)
   - `parent_technique` (if sub-technique)
   - `description`
   - `synonyms` (comma-separated)
   - `data_source` (EEA, planned, gap, expert)
   - `search_query` (Shark-References search string)
   - `search_query_2` (alternative search)
   - `search_query_3` (another alternative)
   - `eea_count` (number of EEA presentations)
   - `inclusion_criteria`
   - `exclusion_criteria`
   - `notes_for_panelists`

2. **Panelist Review Spreadsheet** (Excel format for easier editing)
   - Same structure as CSV
   - Conditional formatting to highlight:
     - Techniques with EEA evidence (green)
     - Techniques from gap analysis (yellow)
     - Techniques needing search terms (red)
   - Tabs per discipline for focused review

3. **Import to Database** after panelist approval
   - R script reads approved CSV
   - Populates all tables with validated data
   - Generates search term alternatives
   - Links EEA evidence

### Phase 2: Database Population (AFTER REVIEW)

Once CSV is approved:
- Run `scripts/import_approved_techniques.R`
- Validates all foreign key relationships
- Imports to `technique_taxonomy.db`
- Creates backup of approved CSV

### Phase 3: Literature Search Execution

With populated database:
- Export search terms via `v_search_terms_for_automation` view
- Execute automated Shark-References searches
- Import results to `literature_searches` and `literature_papers` tables

---

## Current Database Structure

### Core Tables

**`disciplines` (8 records)**
- Biology, Life History, & Health
- Behaviour & Sensory Ecology
- Trophic & Community Ecology
- Genetics, Genomics, & eDNA
- Movement, Space Use, & Habitat Modeling
- Fisheries, Stock Assessment, & Management
- Conservation Policy & Human Dimensions
- Data Science & Integrative Methods

**`categories` (~40 records estimated)**
Example categories:
- Biology: Age & Growth Methods, Reproductive Biology, Morphology, Physiology, Disease & Health
- Behaviour: Behavioural Observation, Sensory Biology, Social Behaviour, Cognition
- Trophic: Diet Analysis Methods, Trophic Position, Foraging Ecology
- [See full list in schema.sql comments]

**`techniques` (~120-150 records estimated)**
- 40 from EEA 2025 conference
- 60-80 from planned Shark-References searches
- 20-30 from gap analysis additions
- Additional expert suggestions

**`search_terms` (~200-250 records estimated)**
- Multiple search strategies per technique
- Validated via manual testing
- Ready for automated execution

### Evidence & Results Tables

**`eea_evidence`** - Links techniques to EEA presentation counts
**`literature_searches`** - Log of executed searches
**`literature_papers`** - Individual paper citations
**`paper_techniques`** - Many-to-many: papers use multiple techniques

### Views for Export

**`v_panelist_review_export`** - Complete technique list for review
**`v_search_terms_for_automation`** - Ready-to-execute search queries
**`v_technique_evidence_summary`** - EEA + literature coverage per technique

---

## Technique Count Targets

### By Discipline (Estimated Final Counts)

| Discipline | EEA | Planned | Gap | Target |
|------------|-----|---------|-----|--------|
| Biology | 7 | 10 | 6 | **23** |
| Behaviour | 5 | 6 | 3 | **14** |
| Trophic | 4 | 6 | 2 | **12** |
| Genetics | 6 | 7 | 2 | **15** |
| Movement | 6 | 8 | 3 | **17** |
| Fisheries | 2 | 12 | 3 | **17** |
| Conservation | 6 | 7 | 3 | **16** |
| Data Science | 5 | 8 | 2 | **15** |
| **TOTAL** | **41** | **64** | **24** | **129** |

*Note: Numbers include both parent techniques and important sub-techniques*

### Gap Analysis Summary

**Critical Additions (10 high-priority gaps):**
1. Histology (Biology) - `+histolog* +gonad*`
2. Morphometrics (Biology) - `+morpholog* +morphometric*`
3. Video/Drone Analysis (Behaviour) - `+video +UAV` or `+drone +track*`
4. VPS/Acoustic Sub-techniques (Movement) - `+VPS +positioning`
5. Close-Kin Mark-Recapture (Fisheries) - `+close* +kin +mark*` or `+CKMR`
6. Data-Poor Methods (Fisheries) - `+data* +poor +assess*`
7. Trade & Markets (Conservation) - `+trade +fin* +market`
8. Citizen Science (Conservation) - `+citizen +scien* +monitor*`
9. Meta-Analysis (Data Science) - `+meta* +analysis +systematic`
10. Time Series (Data Science) - `+time +series +temporal`

**"Missing from EEA but Planned" (18 techniques to include):**

*Biology:* Telomere studies, Endocrinology, Metabolic studies, Bomb radiocarbon, NIRS ageing, Ultrasound

*Behaviour:* Electroreception, Olfaction, Magnetoreception, Predation behavior specifics, Animal-borne cameras

*Trophic:* Food web modeling, Energy flow, Niche partitioning, Fatty acid analysis

*Genetics:* SNPs (explicit), Transcriptomics, Conservation genetics, RAD-seq, Ancient DNA

*Movement:* Satellite tracking (PSAT, SPOT), Home range methods (KDE, Brownian bridge), State-space models, Circuit theory

*Fisheries:* Stock assessment (all sub-methods), CPUE standardization, Surplus production models, Integrated models, Mark-recapture (traditional), Close-kin mark-recapture, Ecosystem models (Ecopath, Atlantis), Gear selectivity, Fisher interviews

*Conservation:* Stakeholder engagement, Ecosystem services, MPA policy evaluation, Shark sanctuaries, Bycatch mitigation policy

*Data Science:* Neural networks, Deep learning, GAM (explicit), Ensemble modeling, GAMM, Hierarchical models, INLA, Stan

**Decision:** ALL planned techniques will be included. Conference snapshot should not limit systematic literature review.

---

## Search Term Design Principles

### Shark-References Query Syntax

| Operator | Usage | Example |
|----------|-------|---------|
| `+` | Required term (AND) | `+acoustic +telemetry` |
| `-` | Exclude term (NOT) | `+telemetry -seabird` |
| `*` | Wildcard suffix | `+reproduct*` matches reproduction, reproductive |
| `"..."` | Exact phrase | `+"stable isotope"` |
| `@N` | Proximity search | `+acoustic @10 +array` (within 10 words) |

**Remember:** Shark-References indexes **first 3 letters only**
- `+tel` matches telemetry, television, telephone
- Be specific: `+acoustic +telemetry` (not just `+tel`)

### Search Term Strategies

**Broad Discipline Searches:**
```
+machine +learning
+Bayesian +model*
+stable +isotop*
```

**Specific Technique Searches:**
```
+close* +kin +mark*  (CKMR)
+VPS +position*      (Vemco Positioning System)
+INLA +model*        (Integrated Nested Laplace Approximation)
```

**Alternative Spellings/Terms:**
```
# Behavior vs. Behaviour
+behav* +predation    (catches both)

# Method variations
+microsatellite* OR +SSR  (simple sequence repeats)
```

**Combination Searches:**
```
+acoustic +telemetry +array
+stable +isotop* +trophic
+IUCN +red +list +assessment
```

### Validation Criteria

Before automated execution, each search term must be:
1. ✅ **Tested manually** on Shark-References
2. ✅ **Result count recorded** (must be > 0 and < 2000)
3. ✅ **Relevance checked** (sample 10-20 results for technique match)
4. ✅ **Refined if needed** (if too broad/narrow or irrelevant results)

---

## Next Steps

### Immediate (This Week)

1. ✅ **Database schema created** - `database/technique_taxonomy.db` exists
2. 📝 **Create master CSV** - All techniques from EEA + planned + gaps
3. 📊 **Create panelist Excel** - Formatted for easy review
4. 📧 **Distribute to panelists** - Request additions/corrections/search term suggestions

### Week 2

5. **Panelist review period** - Collect feedback
6. **Incorporate changes** - Update master CSV
7. **Validate search terms** - Manual testing on subset

### Week 3-4

8. **Import approved CSV to database** - Run import script
9. **Validate complete database** - Check all foreign keys
10. **Begin automated searches** - Execute validated search terms

### Week 5+

11. **Literature import** - Parse CSVs, populate papers table
12. **Deduplication** - Remove duplicate papers
13. **Citation enrichment** - Semantic Scholar API
14. **Expert review preparation** - Generate discipline reports

---

## Database Queries

### Check Database Status

```r
library(RSQLite)
conn <- dbConnect(SQLite(), "database/technique_taxonomy.db")

# Count records
dbGetQuery(conn, "SELECT 'disciplines' as table_name, COUNT(*) as count FROM disciplines
           UNION ALL SELECT 'categories', COUNT(*) FROM categories
           UNION ALL SELECT 'techniques', COUNT(*) FROM techniques
           UNION ALL SELECT 'search_terms', COUNT(*) FROM search_terms
           UNION ALL SELECT 'eea_evidence', COUNT(*) FROM eea_evidence")

# View technique hierarchy
techniques_hierarchy <- dbGetQuery(conn, "SELECT * FROM v_technique_hierarchy LIMIT 20")
print(techniques_hierarchy)

dbDisconnect(conn)
```

### Export for Panelist Review

```r
conn <- dbConnect(SQLite(), "database/technique_taxonomy.db")

# Export complete technique list
panelist_export <- dbGetQuery(conn, "SELECT * FROM v_panelist_review_export")
write_csv(panelist_export, "panelist_review_export.csv")

# Create Excel with separate sheets per discipline
library(writexl)
discipline_sheets <- panelist_export %>%
  group_split(discipline_name) %>%
  set_names(unique(panelist_export$discipline_name))
write_xlsx(discipline_sheets, "panelist_review_by_discipline.xlsx")

dbDisconnect(conn)
```

### Import Approved Techniques

```r
# After panelist review
approved_techniques <- read_csv("master_techniques_approved.csv")

conn <- dbConnect(SQLite(), "database/technique_taxonomy.db")

# Import function in scripts/import_approved_techniques.R
source("scripts/import_approved_techniques.R")
import_techniques_from_csv(approved_techniques, conn)

dbDisconnect(conn)
```

---

## Files in This Project

### Database Files
- `database/technique_taxonomy.db` - Main SQLite database ✅ EXISTS
- `database/schema.sql` - Database schema definition ✅ EXISTS

### Scripts
- `scripts/create_and_populate_taxonomy_db.R` - Initial population (INCOMPLETE)
- `scripts/import_approved_techniques.R` - Import from CSV (TO CREATE)
- `scripts/export_for_panelist_review.R` - Generate review spreadsheets (TO CREATE)
- `scripts/validate_search_terms.R` - Test search terms (TO CREATE)
- `scripts/execute_literature_searches.R` - Automated searches (TO CREATE)

### Data Files (TO CREATE)
- `data/master_techniques.csv` - Editable technique list
- `data/master_techniques_approved.csv` - Post-review version
- `data/panelist_review_by_discipline.xlsx` - Excel for review

### Documentation
- `docs/Technique_Taxonomy_Database_Design.md` - Comprehensive design doc ✅ EXISTS
- `docs/TECHNIQUE_DATABASE_README.md` - This file ✅ EXISTS
- `docs/Discipline_Structure_Analysis.md` - Source boundaries ✅ EXISTS
- `docs/Shark_References_Automation_Workflow.md` - Automation guide ✅ EXISTS

---

## Contact & Support

**Database Location:** `/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel/database/technique_taxonomy.db`

**For Questions:**
- Database structure: See `database/schema.sql`
- Technique taxonomy: See `docs/Technique_Taxonomy_Database_Design.md`
- Search automation: See `docs/Shark_References_Automation_Workflow.md`

---

*Last updated: 2025-10-13*
*Status: Database schema created, awaiting CSV-based population workflow*
*Next action: Create master_techniques.csv with all EEA + planned + gap techniques*
