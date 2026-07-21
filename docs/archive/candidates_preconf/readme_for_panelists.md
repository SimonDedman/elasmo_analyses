# Master Techniques Database - Panelist Review Guide

**Date:** 2025-10-13
**Status:** Ready for review
**Total Techniques:** 208
**Your task:** Review and validate technique list for your discipline

---

## Quick Start

### Option 1: Excel/LibreOffice (Easiest)
1. Open: `data/Techniques DB for Panel Review.xlsx`
2. Review the "Full_List" sheet (all 208 techniques)
3. Make your edits
4. Save as: `Techniques_DB_REVIEWED_[YOURNAME].xlsx`

### Option 2: CSV in Excel
1. Open: `data/master_techniques.csv` in Excel
2. Filter to your discipline code (column A)
3. Make your edits
4. Save as: `master_techniques_REVIEWED_[YOURNAME].csv` (UTF-8)

### Option 3: R/tidyverse
```r
library(tidyverse)
master <- read_csv("data/master_techniques.csv")
my_section <- master %>% filter(discipline_code == "BIO")  # Your code
# ... make edits ...
write_csv(my_section, "master_techniques_REVIEWED_BIO.csv")
```

---

## Your Discipline Assignment

Find your section by discipline code:

| Code | Discipline | Techniques | Lead |
|------|-----------|-----------|------|
| **BIO** | Biology, Life History, & Health | 28 | TBD |
| **BEH** | Behaviour & Sensory Ecology | 20 | TBD |
| **TRO** | Trophic & Community Ecology | 20 | TBD |
| **GEN** | Genetics, Genomics, & eDNA | 24 | TBD |
| **MOV** | Movement, Space Use, & Habitat | 31 | TBD |
| **FISH** | Fisheries, Stock Assessment, & Mgmt | 34 | TBD |
| **CON** | Conservation Policy & Human Dim. | 19 | TBD |
| **DATA** | Data Science & Integrative | 32 | TBD |

------------------------------------------------------------------------

## What to Review

### 1. Technique Names (Column C)

-   ✅ Are names accurate and standard?
-   ✅ Should any be split into multiple techniques?
-   ✅ Should any be merged?

**Example:** "Machine Learning" might be too broad - consider separate techniques for Random Forest, Neural Networks, etc.

### 2. Descriptions (Column F)

-   ✅ Are descriptions clear?
-   ✅ Add more detail if needed

### 3. Synonyms (Column G)

-   ✅ Add alternative names researchers might use
-   ✅ Include abbreviations (e.g., "SIA" for Stable Isotope Analysis)
-   ✅ Format: comma-separated

**Example:** - Before: `NA` - After: `Acoustic tracking, hydrophone monitoring, receiver arrays`

### 4. Search Queries (Columns I-J)

-   ✅ Will these find relevant papers on Shark-References?
-   ✅ Are they too broad (\>2000 results)?
-   ✅ Are they too narrow (\<10 results)?
-   ✅ Syntax: Use `+word`, `word*`, `"exact phrase"`

**Example:** - Primary: `+telemetry +acoustic` - Alternative: `+acoustic +tag* +track*`

### 5. Missing Techniques

-   ✅ Add any major techniques we've missed
-   ✅ Copy a similar row and modify
-   ✅ Flag with "NEW:" in notes column

### 6. Notes Column (Column L)

Use this to flag issues:

| Flag | Meaning | Example |
|-------------------|---------------------------|---------------------------|
| `REVIEW:` | Needs discussion | `REVIEW: May overlap with Satellite Telemetry` |
| `REMOVE:` | Should be deleted | `REMOVE: Too general, subsume into parent` |
| `SPLIT:` | Should be multiple | `SPLIT: Separate CNN, RF, SVM` |
| `MERGE:` | Combine with another | `MERGE: with Movement Modeling` |
| `NEW:` | You added this | `NEW: Missing critical technique` |
| `OK:` | Verified correct | `OK: Checked and validated` |

------------------------------------------------------------------------

## Column Reference

| Col | Name               | Description          | Edit?                       |
|---------------|---------------|---------------------------|---------------|
| A   | `discipline_code`  | Your discipline      | ⚠️ Usually no               |
| B   | `category_name`    | Sub-category         | ⚠️ Rarely                   |
| C   | `technique_name`   | Technique name       | ✅ Yes                      |
| D   | `is_parent`        | TRUE/FALSE hierarchy | ⚠️ Rarely                   |
| E   | `parent_technique` | Parent (if sub)      | ⚠️ Rarely                   |
| F   | `description`      | Brief description    | ✅ Yes                      |
| G   | `synonyms`         | Alt names            | ✅ **YES - ADD MORE**       |
| H   | `data_source`      | EEA/planned/gap      | ℹ️ Info only                |
| I   | `search_query`     | Primary search       | ✅ **YES - VALIDATE**       |
| J   | `search_query_alt` | Alternative search   | ✅ **YES - ADD IF MISSING** |
| K   | `eea_count`        | EEA presentations    | ℹ️ Info only                |
| L   | `notes`            | Your comments        | ✅ **YES - USE THIS**       |

------------------------------------------------------------------------

## Example Edits

### Before Review:

``` csv
BIO,Reproductive Biology,Reproduction,TRUE,NA,Reproductive biology studies,NA,EEA,+reproduct*,+matur*,7,NA
```

### After Review:

``` csv
BIO,Reproductive Biology,Reproduction,TRUE,NA,Reproductive biology and maturity studies,"Maturity, sexual maturity, fecundity, breeding",EEA,+reproduct*,"+matur* +sexual",7,OK: Verified - good coverage
```

**Changes made:** - ✅ Enhanced description - ✅ Added synonyms - ✅ Improved alternative query - ✅ Added validation note

------------------------------------------------------------------------

## Testing Search Queries (Optional but Recommended)

If you have time, test a few queries on Shark-References:

1.  Go to: <https://shark-references.com/search>
2.  Enter query in "Fulltext Search" field (e.g., `+age +growth`)
3.  Click "Search" (NOT "Download")
4.  Check results:
    -   **\>2000 results:** Too broad - add more specific terms
    -   **10-2000 results:** Good range ✅
    -   **\<10 results:** Too narrow - use broader terms or wildcards
5.  Sample 5-10 results - are they relevant?

**Record in notes:**

```         
Tested query: ~350 results, high relevance
```

------------------------------------------------------------------------

## Common Issues to Watch For

### 1. Overly Broad Parent Techniques

❌ Problem: "Physiology" covers too much\
✅ Solution: Add specific sub-techniques or flag for discussion

### 2. Missing Modern Methods

❌ Problem: New techniques from last 5 years not included\
✅ Solution: Add with `NEW:` flag in notes

### 3. Overlapping Techniques

❌ Problem: "Habitat Modeling" vs "Species Distribution Models"\
✅ Solution: Clarify parent/child or flag for discussion

### 4. Field-Specific Jargon

❌ Problem: Query uses term only your subfield uses\
✅ Solution: Add synonyms or broader alternative query

### 5. Incomplete Synonyms

❌ Problem: Missing common abbreviations\
✅ Solution: Add all variants (SIA, CNH, PIT tag, etc.)

------------------------------------------------------------------------

## Timeline

-   **Week 1-2:** Your review and edits
-   **Week 3:** Team discussion of flagged issues
-   **Week 4:** Finalize approved version
-   **Week 5+:** Begin automated searches

------------------------------------------------------------------------

## Questions?

**Documentation:** - Full technique list: `docs/Master_Techniques_List_For_Population.md` - CSV usage guide: `docs/MASTER_TECHNIQUES_CSV_README.md` - Database design: `docs/Technique_Taxonomy_Database_Design.md` - This completion report: `TECHNIQUE_DATABASE_COMPLETION_REPORT.md`

**Contact:** [Project coordinator details]

------------------------------------------------------------------------

## Quick Stats

```         
✅ 129 techniques across 8 disciplines
✅ 40 techniques validated by EEA 2025 conference
✅ 100% have primary search queries
✅ 85% have alternative queries
✅ Ready for your expert review
```

------------------------------------------------------------------------

**Thank you for your contribution to this systematic review!**

Your domain expertise is essential for ensuring comprehensive literature coverage across all elasmobranch research techniques.

------------------------------------------------------------------------

*Document created: 2025-10-13*\
*Files ready: master_techniques.csv, Example of Spreadsheet for Review.xlsx*
