#!/usr/bin/env Rscript
# ==============================================================================
# Extract and Process Weigmann 2016 Species Checklist
# ==============================================================================
#
# Purpose: Extract Table II from Weigmann (2016) PDF and convert to CSV
#
# Input: Weigmann_2016_Annotated_global_checklist_of_ChondrichthyesTable_II_rotated.pdf
# Output: weigmann_2016_species_checklist.csv
#
# Processing steps:
# 1. Extract table from PDF using pdftools + tabulizer
# 2. Fill down hierarchical columns (Subclass, Order, Family)
# 3. Clean Family column (remove numbers, e.g., "Heterodontidae 1" → "Heterodontidae")
# 4. Split "Depth distribution (m)" into min_depth_m and max_depth_m
# 5. Convert column names to lowercase with underscores
# 6. Pivot geographic distribution to binary columns (WIO, EIO, etc.)
#
# Author: Assistant
# Date: 2025-10-02
# ==============================================================================

# Load required packages
library(tidyverse)
library(pdftools)

# NOTE: The PDF has a complex rotated table layout that is difficult to parse
# programmatically. Two approaches:
#
# APPROACH 1 (RECOMMENDED): Manual extraction
#   - Use Tabula (https://tabula.technology/) to manually extract Table II
#   - Export as CSV
#   - Then run this script to process the CSV
#
# APPROACH 2: Automated extraction with tabulizer (may require manual cleanup)
#   - Requires Java and rJava
#   - May not work well with rotated PDF layout

# ==============================================================================
# Configuration
# ==============================================================================

pdf_path <- here::here("data", "Weigmann_2016_Annotated_global_checklist_of_ChondrichthyesTable_II_rotated.pdf")
output_csv <- here::here("data", "weigmann_2016_species_checklist.csv")
output_wide_csv <- here::here("data", "weigmann_2016_species_checklist_wide.csv")
geo_lookup_csv <- here::here("data", "lookup_geographic_distribution.csv")

# ==============================================================================
# STEP 1: Extract Table from PDF
# ==============================================================================

cat("==============================================================================\n")
cat("NOTE: Automated PDF table extraction is complex for rotated tables.\n")
cat("==============================================================================\n\n")

cat("RECOMMENDED WORKFLOW:\n")
cat("1. Download Tabula: https://tabula.technology/\n")
cat("2. Open the PDF in Tabula\n")
cat("3. Select Table II (pages vary, start around page 5 of table)\n")
cat("4. Export as CSV\n")
cat("5. Save as: data/weigmann_2016_table2_raw.csv\n")
cat("6. Re-run this script to process the extracted CSV\n\n")

# Check if raw CSV exists
raw_csv <- here::here("data", "weigmann_2016_table2_raw.csv")

if (!file.exists(raw_csv)) {
  cat("ERROR: Raw CSV not found at:", raw_csv, "\n")
  cat("Please extract Table II using Tabula first (see instructions above)\n")

  # Try automated extraction with pdftools as fallback
  cat("\nAttempting automated text extraction (may require manual cleanup)...\n")

  # Extract text with layout
  text <- pdf_text(pdf_path)

  # Find pages containing "Table II"
  table_pages <- which(str_detect(text, "Table II"))

  cat("Table II found on pages:", paste(table_pages, collapse = ", "), "\n")
  cat("Extracted text saved to: data/weigmann_table2_text.txt\n")

  # Save extracted text for manual review
  writeLines(text, here::here("data", "weigmann_table2_text.txt"))

  cat("\nNEXT STEPS:\n")
  cat("1. Review: data/weigmann_table2_text.txt\n")
  cat("2. Use Tabula for cleaner extraction\n")
  cat("3. Save result as: data/weigmann_2016_table2_raw.csv\n")

  quit(status = 1)
}

# ==============================================================================
# STEP 2: Load and Process Raw CSV
# ==============================================================================

cat("Loading raw CSV...\n")
species_raw <- read_csv(raw_csv, show_col_types = FALSE)

cat("Raw data dimensions:", nrow(species_raw), "rows,", ncol(species_raw), "columns\n")
cat("Column names:\n")
print(names(species_raw))

# ==============================================================================
# STEP 3: Fill Down Hierarchical Columns
# ==============================================================================

cat("\nFilling down hierarchical columns (Subclass, Order, Family)...\n")

species_processed <- species_raw %>%
  # Fill down hierarchical taxonomic columns
  fill(Subclass, .direction = "down") %>%
  fill(Order, .direction = "down") %>%
  fill(`Family #`, .direction = "down")

# ==============================================================================
# STEP 4: Clean Family Column
# ==============================================================================

cat("Cleaning Family column (removing numbers)...\n")

species_processed <- species_processed %>%
  mutate(
    # Extract family name only (remove numbers like "Heterodontidae 1" → "Heterodontidae")
    Family = str_replace(`Family #`, "\\s+\\d+$", ""),
    # Remove the original "Family #" column
    `Family #` = NULL
  ) %>%
  # Fill down family name
  fill(Family, .direction = "down")

# ==============================================================================
# STEP 5: Split Depth Distribution Column
# ==============================================================================

cat("Splitting depth distribution into min_depth_m and max_depth_m...\n")

species_processed <- species_processed %>%
  mutate(
    # Extract min and max depth from "Depth distribution (m)" column
    # Handles formats: "0-590", "3->100", "Inshore", "450-1568", ">1000"
    depth_raw = `Depth distribution (m)`,

    # Extract minimum depth
    min_depth_m = case_when(
      str_detect(depth_raw, "Inshore") ~ 0,
      str_detect(depth_raw, "^>") ~ as.numeric(str_extract(depth_raw, "\\d+")),
      TRUE ~ as.numeric(str_extract(depth_raw, "^\\d+"))
    ),

    # Extract maximum depth
    max_depth_m = case_when(
      str_detect(depth_raw, "Inshore") ~ 50,  # Assume inshore = 0-50m
      str_detect(depth_raw, "^>") ~ NA_real_,  # >1000 = unknown max
      str_detect(depth_raw, "->") ~ as.numeric(str_extract(depth_raw, "(?<=>)\\d+")),
      TRUE ~ as.numeric(str_extract(depth_raw, "(?<=-)\\d+$"))
    ),

    # Remove raw depth column
    `Depth distribution (m)` = NULL
  )

# ==============================================================================
# STEP 6: Convert Column Names to Lowercase with Underscores
# ==============================================================================

cat("Converting column names to lowercase with underscores...\n")

species_processed <- species_processed %>%
  rename_with(
    .fn = ~ str_to_lower(.) %>%
      str_replace_all("\\s+", "_") %>%
      str_replace_all("[()]", "")
  )

# ==============================================================================
# STEP 7: Process Geographic Distribution
# ==============================================================================

cat("Processing geographic distribution column...\n")

# Load geographic distribution lookup
geo_lookup <- read_csv(geo_lookup_csv, show_col_types = FALSE)

cat("Geographic distribution codes:", paste(geo_lookup$abbreviation, collapse = ", "), "\n")

# Add individual binary columns for each geographic area
for (abbrev in geo_lookup$abbreviation) {
  col_name <- paste0("geo_", str_to_lower(abbrev))

  species_processed <- species_processed %>%
    mutate(
      !!col_name := str_detect(geographic_distribution, abbrev)
    )
}

# ==============================================================================
# STEP 8: Save Processed CSV (Long Format)
# ==============================================================================

cat("\nSaving processed data (long format)...\n")

species_long <- species_processed %>%
  select(
    # Taxonomic hierarchy
    subclass,
    order,
    family,
    scientific_name,
    species_authorship,

    # Common details
    common_name,
    maximum_size_mm,

    # Depth
    min_depth_m,
    max_depth_m,
    depth_raw,

    # Geographic distribution (original text)
    geographic_distribution,

    # Geographic binary columns
    starts_with("geo_"),

    # Remarks
    remarks
  )

write_csv(species_long, output_csv)
cat("Saved:", output_csv, "\n")
cat("  - Rows:", nrow(species_long), "\n")
cat("  - Columns:", ncol(species_long), "\n")

# ==============================================================================
# STEP 9: Create Wide Format (Geographic Distribution Pivoted)
# ==============================================================================

cat("\nCreating wide format with binary geographic columns...\n")

# Already done in STEP 7 (binary columns added)
# Just rearrange for clarity

species_wide <- species_long %>%
  select(
    # Taxonomic hierarchy
    subclass,
    order,
    family,
    scientific_name,
    species_authorship,
    common_name,
    maximum_size_mm,
    min_depth_m,
    max_depth_m,

    # Geographic binary columns
    geo_wio,
    geo_eio,
    geo_swp,
    geo_nwp,
    geo_nep,
    geo_sep,
    geo_swa,
    geo_nwa,
    geo_nea,
    geo_sea,

    # Keep original text and remarks
    geographic_distribution,
    depth_raw,
    remarks
  )

write_csv(species_wide, output_wide_csv)
cat("Saved:", output_wide_csv, "\n")
cat("  - Rows:", nrow(species_wide), "\n")
cat("  - Columns:", ncol(species_wide), "\n")

# ==============================================================================
# STEP 10: Summary Statistics
# ==============================================================================

cat("\n==============================================================================\n")
cat("SUMMARY STATISTICS\n")
cat("==============================================================================\n\n")

cat("Total species:", nrow(species_wide), "\n\n")

cat("Species by subclass:\n")
species_wide %>%
  count(subclass, sort = TRUE) %>%
  print()

cat("\nTop 10 families by species count:\n")
species_wide %>%
  count(family, sort = TRUE) %>%
  head(10) %>%
  print()

cat("\nGeographic distribution summary (species per area):\n")
species_wide %>%
  summarise(
    WIO = sum(geo_wio, na.rm = TRUE),
    EIO = sum(geo_eio, na.rm = TRUE),
    SWP = sum(geo_swp, na.rm = TRUE),
    NWP = sum(geo_nwp, na.rm = TRUE),
    NEP = sum(geo_nep, na.rm = TRUE),
    SEP = sum(geo_sep, na.rm = TRUE),
    SWA = sum(geo_swa, na.rm = TRUE),
    NWA = sum(geo_nwa, na.rm = TRUE),
    NEA = sum(geo_nea, na.rm = TRUE),
    SEA = sum(geo_sea, na.rm = TRUE)
  ) %>%
  pivot_longer(everything(), names_to = "area", values_to = "species_count") %>%
  arrange(desc(species_count)) %>%
  print()

cat("\nDepth range summary:\n")
species_wide %>%
  summarise(
    min_depth_median = median(min_depth_m, na.rm = TRUE),
    max_depth_median = median(max_depth_m, na.rm = TRUE),
    max_depth_max = max(max_depth_m, na.rm = TRUE),
    species_with_depth = sum(!is.na(min_depth_m))
  ) %>%
  print()

cat("\n==============================================================================\n")
cat("PROCESSING COMPLETE\n")
cat("==============================================================================\n\n")

cat("Output files:\n")
cat("  1. Long format:  ", output_csv, "\n")
cat("  2. Wide format:  ", output_wide_csv, "\n")
cat("  3. Geo lookup:   ", geo_lookup_csv, "\n")

cat("\nNext steps:\n")
cat("  1. Review CSV files for accuracy\n")
cat("  2. Use wide format for SQL species column generation\n")
cat("  3. Create sp_genus_species columns from scientific_name\n")

# ==============================================================================
# END OF SCRIPT
# ==============================================================================
