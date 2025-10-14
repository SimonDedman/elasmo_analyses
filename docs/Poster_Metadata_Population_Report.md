# Poster Metadata Population Report

**Date:** 2025-10-13
**Script:** `scripts/populate_poster_metadata.R`
**Status:** ✅ Complete

---

## Overview

Successfully populated titles and presenter names for poster presentations (P_XX format) from the "Additional Posters" tab in `Final Speakers EEA 2025.xlsx`.

---

## Objectives

1. Identify poster presentation IDs with NA titles and presenter names
2. Match these to the "Additional Posters" tab using the `nr` column
3. Populate `title`, `presenter_first`, and `presenter_last` fields
4. Maintain data integrity for all other records

---

## Data Sources

### Input
- **Techniques dataset:** `outputs/techniques_from_titles_abstracts.csv` (135 rows)
- **Additional Posters tab:** `Final Speakers EEA 2025.xlsx` sheet "Additional Posters" (22 records)

### Matching Strategy
- Additional Posters tab has IDs in format: `P_01`, `P_02`, `P_03`, etc.
- Techniques dataset has IDs in format: `P02`, `P03`, `P04`, etc. (no underscore)
- Normalized both formats by removing underscores for matching

---

## Processing Steps

### 1. Data Loading
- Loaded 135 technique extraction rows
- Loaded 22 additional poster records from Excel

### 2. ID Normalization
Created normalized presentation IDs for matching:
- `P_01` → `P01`
- `P_02` → `P02`
- `P_03` → `P03`
- etc.

### 3. Lookup and Matching
Performed left join between techniques dataset and additional posters lookup:
- Join key: `presentation_id_norm`
- Relationship: many-to-one (multiple techniques per presentation)

### 4. Conditional Population
Used conditional logic to populate NA fields:
```r
title = if_else(
  is.na(title) & !is.na(title_poster),
  title_poster,
  title
)
```

Applied same logic for `presenter_first` and `presenter_last`.

---

## Results

### Metadata Populated

| Field | Count Filled |
|-------|--------------|
| `title` | 10 |
| `presenter_first` | 10 |
| `presenter_last` | 10 |

### Posters Successfully Updated

| Presentation ID | Title | Presenter |
|----------------|-------|-----------|
| P02 | Angel Sharks in the Eastern and Central Mediterranean: Three Years On | Hettie Brown |
| P03 | The first reference genome of the blackchin guitarfish (Glaucostegus cemiculus)... | Kirsti Burnett |
| P04 | Linking space use and sociality in reef manta rays on a remote Pacific island... | Juliette Elisa Debarge |
| P07 | Too Late or Just in Time? Rediscovery and first nursery evidence of the critically endangered Spiny butterfly ray... | Emina Karalic |
| P13 | Possible nursery area for nursehound shark Scyliorhinus stellaris in Lemnos island, Greece | Nikoletta Sidiropoulou |
| P14 | First investigation of the presence of microplastics in the stomach of the thornback ray... | Manoah Touzot |
| P16 | Solving the puzzle on Dasyatis marmorata's distribution: first record of the species in the Spanish coast | Francesca Maria Veneziano |
| P18 | Insights of reproduction and foraging behaviour of the white shark (Carcharodon carcharias) off France... | Nicolas Ziani |

**Note:** Some poster IDs have multiple technique extractions, resulting in 10 metadata fills across 8 unique poster presentation IDs.

---

## Remaining NA Values

### Summary
- **Total rows with NA title:** 20 (down from 30)
- **Percentage complete:** 85.2% (115 of 135 rows have titles)

### Breakdown of Remaining NAs

All 20 remaining rows with NA values are **oral presentations (O_XX format)**, not posters:

| Presentation ID | Note |
|----------------|------|
| O_07 | Abstract-only extraction, no title in abstract file |
| O_08 | Abstract-only extraction, no title in abstract file |
| O_10 | Abstract-only extraction, no title in abstract file |
| O_17 | Abstract-only extraction, no title in abstract file |
| O_24 | Abstract-only extraction, no title in abstract file |
| O_32 | Abstract-only extraction, no title in abstract file |
| O_35 | Abstract-only extraction, no title in abstract file |
| O_36 | Abstract-only extraction, no title in abstract file |
| O_38 | Abstract-only extraction, no title in abstract file |
| O_44 | Abstract-only extraction, no title in abstract file |
| O_57 | Abstract-only extraction, no title in abstract file |
| O_61 | Abstract-only extraction, no title in abstract file |
| O_62 | Abstract-only extraction, no title in abstract file |
| O_67 | Abstract-only extraction, no title in abstract file |
| O_74 | Abstract-only extraction, no title in abstract file |

**Reason for remaining NAs:** These are oral presentations extracted from abstract files that did not contain title or presenter metadata within the abstract text itself. These could potentially be filled from the main "Final Speakers EEA 2025.xlsx" data tab if needed.

---

## Data Quality Metrics

### Before Update
- Rows with title: 105 / 135 (77.8%)
- Rows with presenter_first: 105 / 135 (77.8%)
- Rows with presenter_last: 105 / 135 (77.8%)

### After Update
- Rows with title: 115 / 135 (85.2%)
- Rows with presenter_first: 115 / 135 (85.2%)
- Rows with presenter_last: 115 / 135 (85.2%)

### Improvement
- **+10 rows** with complete metadata (7.4% improvement)
- **All poster presentations** now have complete metadata
- Remaining 20 NAs are oral presentations that require different lookup source

---

## Technical Details

### Script Location
`scripts/populate_poster_metadata.R`

### Key Functions
1. **ID Normalization:** `str_replace(nr, "P_", "P")`
2. **Pattern Detection:** `str_detect(presentation_id, "^P\\d{2,}")`
3. **Conditional Population:** `if_else(is.na(title) & !is.na(title_poster), title_poster, title)`
4. **Left Join:** Preserved all original rows while adding lookup data

### Execution Time
< 30 seconds

---

## File Changes

### Modified Files
- `outputs/techniques_from_titles_abstracts.csv` - Updated with poster metadata (overwritten)

### New Scripts
- `scripts/populate_poster_metadata.R` - Poster metadata population script

### New Documentation
- `docs/Poster_Metadata_Population_Report.md` - This report

---

## Validation

### Verification Checks
✅ All 8 unique poster IDs (P02-P18) now have titles
✅ All 8 unique poster IDs now have presenter names
✅ No existing data was overwritten (only NA values filled)
✅ Total row count unchanged (135 rows)
✅ Unique presentation count unchanged (68 presentations)

### Sample Verification
Selected P04 for detailed check:
- **Presentation ID:** P04
- **Title:** "Linking space use and sociality in reef manta rays on a remote Pacific island in Micronesia"
- **Presenter:** Juliette Elisa Debarge
- **Techniques:** Social Network Analysis, Acoustic Telemetry
- **Match source:** Additional Posters tab, nr = P_04

✅ Verified correct match

---

## Recommendations

### Optional: Populate Remaining Oral Presentation NAs

The 15 oral presentations with NA titles could be populated from the main "Final Speakers EEA 2025.xlsx" data tab using a similar lookup approach:

1. Load main data tab (already used in `clean_amalgamated_techniques.R`)
2. Match on `presentation_id` using the `nr` column
3. Populate NA titles and presenter names

**Benefit:** Would achieve 100% metadata completeness
**Consideration:** These abstract-only extractions don't have presenter info in the abstract file, suggesting they might be less reliable or need validation

### Alternative: Manual Review

Given only 15 remaining NAs (11% of dataset), a manual review might be appropriate to:
1. Verify these are legitimate technique extractions
2. Confirm the abstract files are properly formatted
3. Decide whether to keep or remove these rows

---

## Summary

Successfully populated metadata for all poster presentations in the techniques dataset. The operation:

✅ **Filled 10 metadata instances** (title, first name, last name) across 8 poster presentations
✅ **Improved completeness from 77.8% to 85.2%**
✅ **Maintained data integrity** - no overwrites of existing data
✅ **Used official identifiers** from Additional Posters tab
✅ **Preserved all technique extractions** - row count unchanged

**All poster presentations (P_XX) now have complete metadata.**

Remaining NAs are oral presentations (O_XX) extracted from abstract files without embedded metadata. These can be addressed separately if 100% completeness is desired.

---

## Reproducibility

To reproduce this update:

```bash
cd "/path/to/Data Panel"
Rscript scripts/populate_poster_metadata.R
```

**Prerequisites:**
- R (version 4.x+)
- tidyverse package
- readxl package

**Inputs:**
- `outputs/techniques_from_titles_abstracts.csv` (from data cleaning)
- `Final Speakers EEA 2025.xlsx` (Additional Posters tab)

**Output:**
- `outputs/techniques_from_titles_abstracts.csv` (updated, overwritten)

---

*Report prepared: 2025-10-13*
*Script version: 1.0*
*Status: ✅ Complete*
