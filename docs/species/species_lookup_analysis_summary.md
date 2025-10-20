---
editor_options:
  markdown:
    wrap: 72
---

# Species Common Name Lookup - Analysis & Cleaning Summary

**Date:** 2025-10-02
**File Analyzed:** `data/species_common_lookup.csv`
**Cleaned Output:** `data/species_common_lookup_cleaned.csv`

---

## Executive Summary

**Status:** ✅ **GOOD DATA QUALITY** - Minor typos fixed, ready to use

- **Current species count:** 1,030 unique species
- **Expected (Weigmann 2016):** 1,208 species
- **Missing:** 178 species (14.7% gap)
- **Data quality:** Excellent structure, minimal typos
- **Common names:** 2,607 unique common names (avg 2.9 per species)

---

## Analysis Results

### ✅ Quality Checks PASSED

All major quality checks passed with flying colors:

| Check | Result | Status |
|-------|--------|--------|
| Numbers in species names | 0 | ✅ Pass |
| Special characters | 0 | ✅ Pass |
| Extra spaces | 0 | ✅ Pass |
| Case inconsistencies | 0 | ✅ Pass |
| Empty common names | 0 | ✅ Pass |
| Leading/trailing spaces | 0 | ✅ Pass |
| Very short species names (<5 chars) | 0 | ✅ Pass |
| Very long species names (>50 chars) | 0 | ✅ Pass |

**Conclusion:** This is a well-maintained dataset!

---

### ⚠️ Issues Found & Fixed

#### 1. Obvious Typos (5 fixed)

| Original | Corrected |
|----------|-----------|
| Grayspottted guitarfish | Grayspotted guitarfish |
| Omn guitarfish | Oman guitarfish |
| Lang spotted eagle ray | Long spotted eagle ray |
| Spotted edgle-ray | Spotted eagle-ray |
| Duckbil ray | Duckbill ray |

---

#### 2. Spelling Variants Standardized

**Gray vs Grey:**
- Original: 139 "gray" variants, 40 "grey" variants
- **Decision:** Standardized to "gray" (American English, more common)
- **Action:** All "grey" → "gray"

**Whipray:**
- Original: 19 "whipray" (one word), 6 "whip ray" (two words)
- **Decision:** Standardized to "whipray" (one word, more common)
- **Action:** All "whip ray" → "whipray"

**Eagle Ray:**
- Original: 47 "eagle ray" (two words), 3 "eagleray" (one word)
- **Decision:** Standardized to "eagle ray" (two words, more common)
- **Action:** All "eagleray" → "eagle ray"

---

#### 3. Duplicate Rows Removed

- **Found:** 22 duplicate rows (exact Species + Common duplicates)
- **Action:** Removed duplicates
- **Result:** 3,027 rows → 3,016 rows (11 duplicates removed)

---

### 🔍 Potential Issues to Investigate

#### 1. Missing Species (178 species)

**Expected:** 1,208 species (Weigmann 2016)
**Found:** 1,030 species
**Missing:** 178 species (14.7%)

**Possible explanations:**
1. Source data is incomplete
2. Taxonomic revisions (species split/merged since 2016)
3. Different taxonomic authority used
4. Data extraction errors

**Recommendation:** Wait for Simon Weigmann's updated list to identify missing species

---

#### 2. Suspicious Similar Species Names (5 pairs)

These species have very similar names (edit distance ≤ 2). Verify they are distinct species:

| Species 1 | Species 2 | Edit Distance | Likely Explanation |
|-----------|-----------|---------------|-------------------|
| Apristurus canutus | Apristurus nasutus | 2 | Different species (canutus vs nasutus) |
| Carcharhinus hemiodon | Carcharhinus leiodon | 2 | Different species (hemiodon vs leiodon) |
| Dipturus tengu | Dipturus wengi | 2 | Different species (tengu vs wengi) |
| Squatina aculeata | Squatina oculata | 2 | Different species (aculeata vs oculata) |
| **Squatina occulta** | **Squatina oculata** | 2 | ⚠️ **VERIFY** - very similar! |

**Action:** Check taxonomic authorities for `Squatina occulta` vs `Squatina oculata`

---

## Common Name Statistics

### Top 10 Species by Common Name Count

| Rank | Species | Common Names | Top Common Name |
|------|---------|--------------|-----------------|
| 1 | Squalus acanthias | 24 | Spiny dogfish |
| 2 | Aetobatus narinari | 23 | Spotted eagle ray |
| 3 | Carcharias taurus | 22 | Sand tiger shark |
| 4 | Taeniura lymma | 21 | Blue-spotted stingray |
| 5 | Isurus oxyrinchus | 19 | Shortfin mako |
| 6 | Carcharhinus obscurus | 18 | Dusky shark |
| 7 | Galeorhinus galeus | 18 | School shark |
| 8 | Himantura uarnak | 18 | Reticulate whipray |
| 9 | Notorynchus cepedianus | 18 | Broadnose sevengill shark |
| 10 | Rhynchobatus djiddensis | 18 | Giant guitarfish |

### Common Name Distribution

| Common Names per Species | Number of Species |
|-------------------------|-------------------|
| 25 | 0 (after cleaning) |
| 24 | 1 |
| 22-23 | 2 |
| 21 | 1 |
| 18-19 | 7 |
| 14-17 | 9 |
| 10-13 | 26 |
| 5-9 | 97 |
| 2-4 | 441 |
| 1 | 446 |

**Average:** 2.9 common names per species
**Median:** 2 common names per species

---

## Files Created

### 1. Analysis Report
**File:** `data/species_lookup_analysis_report.txt`
**Content:** Detailed analysis with full lists of issues

### 2. Cleaned CSV
**File:** `data/species_common_lookup_cleaned.csv`
**Changes:**
- Fixed 5 typos
- Standardized gray/grey, whipray/whip ray, eagleray/eagle ray
- Removed 11 duplicate rows
- **Rows:** 3,016 (down from 3,027)
- **Species:** 1,030 (unchanged)
- **Common names:** 2,607 (down from 2,619)

---

## Scripts Created

### 1. Analysis Script
**File:** `scripts/analyze_species_lookup.R`
**Purpose:** Detect typos, duplicates, inconsistencies
**Usage:**
```r
Rscript scripts/analyze_species_lookup.R
```

### 2. Cleaning Script
**File:** `scripts/clean_species_lookup.R`
**Purpose:** Fix typos and standardize spelling
**Usage:**
```r
Rscript scripts/clean_species_lookup.R
```

---

## Next Steps

### Immediate

1. ✅ **Use cleaned CSV** - `data/species_common_lookup_cleaned.csv` is ready to use
2. ✅ **Generate SQL species columns** - Can proceed with 1,030 species now
3. ⏳ **Wait for Weigmann update** - Fill in 178 missing species when received

### When Weigmann List Received

1. Compare Weigmann 2016 species list with current 1,030 species
2. Identify 178 missing species
3. Add missing species to lookup table
4. Re-run cleaning script
5. Regenerate SQL species columns with full 1,208 species

### Optional Enhancements

1. **Add taxonomic hierarchy** - Subclass, Order, Family for each species
2. **Add authority citations** - Species author & year
3. **Add IUCN status** - Conservation status for each species
4. **Cross-reference Sharkipedia** - Validate species list against Sharkipedia

---

## Usage Examples

### Load Cleaned Data in R

```r
library(tidyverse)

# Load cleaned species lookup
species_lookup <- read_csv("data/species_common_lookup_cleaned.csv")

# Get all common names for a species
species_lookup %>%
  filter(Species == "Carcharodon carcharias") %>%
  pull(Common)

# Get species with most common names
species_lookup %>%
  count(Species, sort = TRUE) %>%
  head(10)

# Find common name for a species (first alphabetically)
get_common_name <- function(species_name) {
  species_lookup %>%
    filter(Species == species_name) %>%
    arrange(Common) %>%
    slice(1) %>%
    pull(Common)
}

get_common_name("Prionace glauca")  # Returns "Blue pointer"
```

### Generate SQL Species Columns

```r
library(tidyverse)

species_lookup <- read_csv("data/species_common_lookup_cleaned.csv")

# Get unique species
unique_species <- species_lookup %>%
  distinct(Species) %>%
  arrange(Species) %>%
  mutate(
    # Generate SQL column name: sp_genus_species
    column_name = paste0(
      "sp_",
      str_to_lower(Species) %>%
        str_replace_all(" ", "_")
    ),
    # Get first common name (alphabetically)
    common_name = map_chr(Species, function(sp) {
      species_lookup %>%
        filter(Species == sp) %>%
        arrange(Common) %>%
        slice(1) %>%
        pull(Common)
    })
  )

# Generate SQL ALTER TABLE statements
sql_statements <- unique_species %>%
  mutate(
    sql = glue::glue(
      "ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS {column_name} BOOLEAN DEFAULT FALSE; -- {Species} ({common_name})"
    )
  )

# Write to file
writeLines(sql_statements$sql, "sql/06_add_species_columns.sql")

cat(sprintf("Generated %d species columns\n", nrow(unique_species)))
```

---

## Conclusion

**The species_common_lookup.csv is high-quality data** with only minor typos and spelling inconsistencies, now fixed in the cleaned version.

**Key Points:**
- ✅ 1,030 species ready to use immediately
- ✅ Clean data structure (no major errors)
- ⏳ 178 species missing (wait for Weigmann update)
- ✅ All infrastructure ready for SQL generation

**Recommendation:** Proceed with generating SQL species columns using 1,030 species, then update when Weigmann's complete list arrives.

---

*Generated: 2025-10-02*
*Analysis by: Assistant*
*Status: Ready for use*
