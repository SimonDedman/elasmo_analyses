---
editor_options:
  markdown:
    wrap: 72
---

# Weigmann 2016 Species Checklist - Extraction Instructions

## Overview

This document provides instructions for extracting Table II from the Weigmann (2016) PDF and processing it into CSV format for the EEA 2025 Data Panel project.

**Source:** `data/Weigmann_2016_Annotated_global_checklist_of_ChondrichthyesTable_II_rotated.pdf`

**Target Output:** `data/weigmann_2016_species_checklist_wide.csv`

---

## Step 1: Extract Table II from PDF

### Option A: Tabula (RECOMMENDED)

**Tabula** is a free tool specifically designed for extracting tables from PDFs.

1. **Download Tabula:**
   - URL: https://tabula.technology/
   - Available for Windows, Mac, Linux
   - No installation required (standalone JAR file)

2. **Open PDF in Tabula:**
   ```bash
   # Launch Tabula (it will open in your web browser)
   java -jar tabula.jar
   ```

   Then upload: `data/Weigmann_2016_Annotated_global_checklist_of_ChondrichthyesTable_II_rotated.pdf`

3. **Select Table II:**
   - Table II starts around page 5 of the checklist section
   - **Look for header row:** `Subclass | Order | Family # | Scientific name | Species authorship | Common name | Maximum size (mm) | Depth distribution (m) | Geographic distribution | Remarks`
   - Table spans approximately **150-200 pages** (1188 species)

4. **Extract Table:**
   - Click "Preview & Export Extracted Data"
   - **Method:** "Lattice" (for tables with lines) or "Stream" (for tables without lines)
   - Try **Lattice first** - it works better for structured tables
   - If columns merge, switch to **Stream** method

5. **Export as CSV:**
   - Click "Export" → "CSV"
   - Save as: `data/weigmann_2016_table2_raw.csv`

---

### Option B: pdftotext + Manual Cleanup

If Tabula doesn't work well with the rotated layout:

```bash
# Extract text with layout preservation
pdftotext -layout "data/Weigmann_2016_Annotated_global_checklist_of_ChondrichthyesTable_II_rotated.pdf" "data/weigmann_table2_text.txt"

# Then manually parse the text file
# This is tedious but works when PDFs have complex layouts
```

---

### Option C: Manual Entry (LAST RESORT)

For testing/development, manually extract a subset:

- Extract just **Carcharhinidae family** (~50 species) as a test
- Verify processing scripts work
- Then extract full table

---

## Step 2: Process Extracted CSV

Once you have `data/weigmann_2016_table2_raw.csv`, run either:

### R Processing Script:

```r
source("scripts/extract_weigmann_2016_species.R")
```

### Python Processing Script:

```python
python scripts/extract_weigmann_2016_species.py
```

---

## Processing Steps (Automated by Scripts)

The scripts perform the following transformations:

### 1. Fill Down Hierarchical Columns

**Problem:** Subclass, Order, and Family are only listed once per group

**Example:**
```
Subclass     Order            Family #           Scientific name
Elasmobranchii Carcharhiniformes Carcharhinidae 1  Carcharhinus acronotus
                                                   Carcharhinus albimarginatus
                                                   Carcharhinus altimus
```

**Solution:** Fill down blank cells

```r
df <- df %>%
  fill(Subclass, .direction = "down") %>%
  fill(Order, .direction = "down") %>%
  fill(`Family #`, .direction = "down")
```

---

### 2. Clean Family Column

**Problem:** Family column has numbers (e.g., "Heterodontidae 1", "Carcharhinidae 1")

**Solution:** Remove numbers, keep family name only

```r
df$Family <- str_replace(df$`Family #`, "\\s+\\d+$", "")
```

**Before:** `Heterodontidae 1`
**After:** `Heterodontidae`

---

### 3. Split Depth Distribution Column

**Problem:** Depth is a range string (e.g., "0-590", "3->100", ">1000", "Inshore")

**Solution:** Parse into `min_depth_m` and `max_depth_m`

**Examples:**

| Depth distribution (m) | min_depth_m | max_depth_m |
|------------------------|-------------|-------------|
| 0-590                  | 0           | 590         |
| 3->100                 | 3           | 100         |
| >1000                  | 1000        | NA          |
| Inshore                | 0           | 50          |
| 450-1568               | 450         | 1568        |

```r
df <- df %>%
  mutate(
    min_depth_m = case_when(
      str_detect(depth_raw, "Inshore") ~ 0,
      str_detect(depth_raw, "^>") ~ as.numeric(str_extract(depth_raw, "\\d+")),
      TRUE ~ as.numeric(str_extract(depth_raw, "^\\d+"))
    ),
    max_depth_m = case_when(
      str_detect(depth_raw, "Inshore") ~ 50,
      str_detect(depth_raw, "^>") ~ NA_real_,
      str_detect(depth_raw, "->") ~ as.numeric(str_extract(depth_raw, "(?<=>)\\d+")),
      TRUE ~ as.numeric(str_extract(depth_raw, "(?<=-)\\d+$"))
    )
  )
```

---

### 4. Convert Column Names to Lowercase

**Before:**
```
Subclass, Order, Family #, Scientific name, Species authorship, Common name, Maximum size (mm), Depth distribution (m), Geographic distribution, Remarks
```

**After:**
```
subclass, order, family, scientific_name, species_authorship, common_name, maximum_size_mm, min_depth_m, max_depth_m, geographic_distribution, remarks
```

---

### 5. Pivot Geographic Distribution to Binary Columns

**Problem:** Geographic distribution is comma-separated codes (e.g., "WIO, EIO, SWP")

**Solution:** Create binary column for each geographic area

**Geographic codes:**

| Code | Full Name | Ocean Basin |
|------|-----------|-------------|
| WIO  | Western Indian Ocean | Indian Ocean |
| EIO  | Eastern Indian Ocean | Indian Ocean |
| SWP  | South-Western Pacific Ocean | Pacific Ocean |
| NWP  | North-Western Pacific Ocean | Pacific Ocean |
| NEP  | North-Eastern Pacific Ocean | Pacific Ocean |
| SEP  | South-Eastern Pacific Ocean | Pacific Ocean |
| SWA  | South-Western Atlantic Ocean | Atlantic Ocean |
| NWA  | North-Western Atlantic Ocean | Atlantic Ocean |
| NEA  | North-Eastern Atlantic Ocean (incl. Mediterranean & Black Sea) | Atlantic Ocean |
| SEA  | South-Eastern Atlantic Ocean | Atlantic Ocean |

**Example transformation:**

**Before:**
```
Scientific name            Geographic distribution
Carcharodon carcharias    WIO, EIO, SWP, NWP, NEP, SEP, SWA, NWA, NEA, SEA
Prionace glauca           WIO, EIO, SWP, NWP, NEP, SEP
```

**After:**
```
Scientific name         geo_wio  geo_eio  geo_swp  geo_nwp  geo_nep  geo_sep  geo_swa  geo_nwa  geo_nea  geo_sea
Carcharodon carcharias  TRUE     TRUE     TRUE     TRUE     TRUE     TRUE     TRUE     TRUE     TRUE     TRUE
Prionace glauca         TRUE     TRUE     TRUE     TRUE     TRUE     TRUE     FALSE    FALSE    FALSE    FALSE
```

```r
for (abbrev in c("WIO", "EIO", "SWP", "NWP", "NEP", "SEP", "SWA", "NWA", "NEA", "SEA")) {
  col_name <- paste0("geo_", str_to_lower(abbrev))
  df[[col_name]] <- str_detect(df$geographic_distribution, abbrev)
}
```

---

## Expected Output Structure

### Final CSV Schema

**File:** `data/weigmann_2016_species_checklist_wide.csv`

**Columns (23 total):**

1. `subclass` - Taxonomic subclass (Elasmobranchii or Holocephali)
2. `order` - Taxonomic order (Carcharhiniformes, Squaliformes, etc.)
3. `family` - Family name (Carcharhinidae, Lamnidae, etc.)
4. `scientific_name` - Binomial (e.g., Carcharodon carcharias)
5. `species_authorship` - Author citation (e.g., "(Linnaeus 1758)")
6. `common_name` - Common name(s)
7. `maximum_size_mm` - Maximum total length in mm
8. `min_depth_m` - Minimum depth in meters
9. `max_depth_m` - Maximum depth in meters
10. `geo_wio` - Boolean: Western Indian Ocean
11. `geo_eio` - Boolean: Eastern Indian Ocean
12. `geo_swp` - Boolean: South-Western Pacific
13. `geo_nwp` - Boolean: North-Western Pacific
14. `geo_nep` - Boolean: North-Eastern Pacific
15. `geo_sep` - Boolean: South-Eastern Pacific
16. `geo_swa` - Boolean: South-Western Atlantic
17. `geo_nwa` - Boolean: North-Western Atlantic
18. `geo_nea` - Boolean: North-Eastern Atlantic (incl. Med & Black Sea)
19. `geo_sea` - Boolean: South-Eastern Atlantic
20. `geographic_distribution` - Original text (for reference)
21. `depth_raw` - Original depth text (for reference)
22. `remarks` - Taxonomic/distributional remarks
23. *(Optional)* `species_number` - Sequential species number from table

---

## Validation Checks

After processing, verify the following:

### 1. Species Count

**Expected:** 1,188 species total (as of 2015-11-07)

```r
nrow(species_df)  # Should be ~1188
```

**Breakdown by group:**
- **Sharks:** 509 species
- **Batoids (rays/skates):** 630 species
- **Chimaeras:** 49 species

### 2. Subclass Distribution

```r
species_df %>% count(subclass)

# Expected:
# Elasmobranchii: 1139 (509 sharks + 630 batoids)
# Holocephali: 49 (chimaeras)
```

### 3. Top Families

```r
species_df %>% count(family, sort = TRUE) %>% head(10)

# Expected top families:
# 1. Rajidae (skates) - ~150 species
# 2. Carcharhinidae (requiem sharks) - ~50 species
# 3. Dasyatidae (stingrays) - ~80 species
# 4. Scyliorhinidae (catsharks) - ~160 species
```

### 4. Geographic Distribution

```r
species_df %>%
  summarise(across(starts_with("geo_"), sum, na.rm = TRUE))

# Expected high-diversity areas:
# SWP (South-Western Pacific): ~300-400 species
# NWP (North-Western Pacific): ~250-350 species
# WIO (Western Indian Ocean): ~250-350 species
```

### 5. Depth Range

```r
summary(species_df$min_depth_m)
summary(species_df$max_depth_m)

# Expected:
# min_depth_m: 0 (many coastal species)
# max_depth_m: up to 2000+ m (deep-sea species)
```

---

## Integration with SQL Schema

Once the CSV is validated, use it to generate SQL species columns:

```r
library(tidyverse)

species_df <- read_csv("data/weigmann_2016_species_checklist_wide.csv")

# Generate SQL column names
species_df <- species_df %>%
  mutate(
    sql_column = paste0(
      "sp_",
      str_to_lower(scientific_name) %>%
        str_replace_all(" ", "_") %>%
        str_replace_all("-", "_") %>%
        str_replace_all("[^a-z0-9_]", "")
    )
  )

# Generate SQL ALTER TABLE statements
sql_statements <- species_df %>%
  mutate(
    sql = glue::glue(
      "ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS {sql_column} BOOLEAN DEFAULT FALSE; -- {scientific_name} ({common_name})"
    )
  )

# Write to SQL file
writeLines(sql_statements$sql, "sql/06_add_species_columns.sql")

cat(sprintf("Generated %d species columns\n", nrow(species_df)))
```

---

## Troubleshooting

### Issue: Tabula merges columns

**Solution:** Try switching extraction method:
- Lattice → Stream
- Stream → Lattice

Or manually adjust column boundaries in Tabula UI.

---

### Issue: Hierarchical columns not filling down

**Symptom:** Many rows have blank Subclass/Order/Family

**Solution:** Ensure fill_down is applied in correct order:
```r
df %>%
  fill(Subclass, .direction = "down") %>%
  fill(Order, .direction = "down") %>%
  fill(Family, .direction = "down")
```

---

### Issue: Depth parsing fails

**Symptom:** min_depth_m and max_depth_m are all NA

**Cause:** Unexpected depth format

**Solution:** Inspect unique depth values:
```r
unique(df$depth_raw)
```

Add handling for new formats.

---

### Issue: Geographic codes not detected

**Symptom:** All geo_* columns are FALSE

**Cause:** Column name mismatch

**Solution:** Check column name:
```r
names(df)
# Should include "geographic_distribution" (lowercase, underscores)
```

---

## Next Steps

1. ✅ Extract Table II using Tabula → `data/weigmann_2016_table2_raw.csv`
2. ✅ Run processing script → `data/weigmann_2016_species_checklist_wide.csv`
3. ✅ Validate species count (~1,188 species)
4. ✅ Generate SQL species columns → `sql/06_add_species_columns.sql`
5. ✅ Compare with Sharkipedia list (when received from Simon Weigmann)

---

## References

**Weigmann, S. (2016).** Annotated checklist of the living sharks, batoids and chimaeras (Chondrichthyes) of the world, with a focus on biogeographical diversity. *Journal of Fish Biology*, 88(3), 837-1037. DOI: 10.1111/jfb.12874

**Geographic areas based on:** IHO (1953). *Limits of Oceans and Seas*, 3rd edition.

---

*Created: 2025-10-02*
*For: EEA 2025 Data Panel Project*
*Status: Awaiting Table II extraction*
