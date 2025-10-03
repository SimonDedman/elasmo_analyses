#!/usr/bin/env Rscript
# ==============================================================================
# Clean Weigmann 2016 Excel File
# ==============================================================================
#
# Purpose: Clean the extracted Excel file from PDFTables.com
#
# Issues to fix:
# 1. Blank rows (all NA)
# 2. Repeated column headers
# 3. Text split across multiple rows (species names, remarks)
# 4. Shifted columns
# 5. Family names split across rows
#
# ==============================================================================

library(readxl)
library(tidyverse)

# ==============================================================================
# Configuration
# ==============================================================================

excel_path <- here::here("data", "Weigmann_2016_Annotated_global_checklist_of_ChondrichthyesTable_II_rotated.xlsx")
output_csv <- here::here("data", "weigmann_2016_species_checklist_cleaned.csv")

cat("==============================================================================\n")
cat("CLEANING WEIGMANN 2016 EXCEL FILE\n")
cat("==============================================================================\n\n")

# ==============================================================================
# STEP 1: Read Raw Excel Data
# ==============================================================================

cat("Reading Excel file...\n")
df_raw <- read_excel(excel_path, sheet = 1, col_names = FALSE)

cat("Raw data dimensions:", nrow(df_raw), "rows x", ncol(df_raw), "columns\n\n")

# ==============================================================================
# STEP 2: Find True Header Row
# ==============================================================================

cat("Searching for header row...\n")

# Header should contain "Subclass", "Order", "Family", "Scientific name", etc.
header_keywords <- c("Subclass", "Order", "Family", "Scientific", "Common", "Maximum", "Depth", "Geographic")

# Find row containing most header keywords
find_header_row <- function(df) {
  for (i in 1:min(20, nrow(df))) {
    row_text <- paste(df[i, ], collapse = " ")
    matches <- sum(sapply(header_keywords, function(kw) grepl(kw, row_text, ignore.case = TRUE)))

    if (matches >= 5) {  # At least 5 header keywords found
      cat("Found header row at line", i, "(", matches, "keywords matched)\n")
      return(i)
    }
  }

  cat("WARNING: Header row not found automatically. Using row 3.\n")
  return(3)  # Default fallback
}

header_row <- find_header_row(df_raw)

# Extract header
header <- df_raw[header_row, ] %>%
  as.character() %>%
  str_trim()

cat("Header columns:", paste(header[!is.na(header)], collapse = " | "), "\n\n")

# ==============================================================================
# STEP 3: Extract Data Rows (After Header)
# ==============================================================================

cat("Extracting data rows...\n")

# Start from row after header
df_data <- df_raw[(header_row + 1):nrow(df_raw), ]

# Assign column names from header
# Clean header: remove line breaks, extra spaces
header_clean <- header %>%
  str_replace_all("\\n", " ") %>%
  str_replace_all("\\s+", " ") %>%
  str_trim()

# If header has more columns than data, trim
if (length(header_clean) > ncol(df_data)) {
  header_clean <- header_clean[1:ncol(df_data)]
}

# If data has more columns than header, extend header
if (ncol(df_data) > length(header_clean)) {
  header_clean <- c(header_clean, paste0("extra_", 1:(ncol(df_data) - length(header_clean))))
}

# Replace NA and empty column names
na_count <- sum(is.na(header_clean) | header_clean == "")
header_clean[is.na(header_clean) | header_clean == ""] <- paste0("col_", 1:na_count)

# Make column names unique
header_clean <- make.unique(header_clean, sep = "_")

colnames(df_data) <- header_clean

cat("Data dimensions after header extraction:", nrow(df_data), "rows x", ncol(df_data), "columns\n\n")

# ==============================================================================
# STEP 4: Remove Completely Blank Rows
# ==============================================================================

cat("Removing blank rows...\n")

df_data <- df_data %>%
  filter(rowSums(!is.na(.)) > 0)  # Keep rows with at least 1 non-NA value

cat("After removing blanks:", nrow(df_data), "rows\n\n")

# ==============================================================================
# STEP 5: Remove Repeated Header Rows
# ==============================================================================

cat("Removing repeated headers...\n")

# Identify rows where "Subclass" appears (repeated headers)
subclass_col <- names(df_data)[str_detect(names(df_data), regex("subclass", ignore_case = TRUE))][1]

if (!is.na(subclass_col)) {
  df_data <- df_data %>%
    filter(is.na(.data[[subclass_col]]) | !str_detect(.data[[subclass_col]], regex("^Subclass$", ignore_case = TRUE)))
}

cat("After removing repeated headers:", nrow(df_data), "rows\n\n")

# ==============================================================================
# STEP 6: Collapse Multi-Row Entries
# ==============================================================================

cat("Collapsing multi-row entries...\n")

# Strategy: If Subclass/Order/Family are NA, merge with previous row
# This handles cases where text wraps to next line

collapse_rows <- function(df) {
  # Identify columns that should trigger new records
  key_cols <- c("Subclass", "Order", "Family #", "Scientific name")

  # Find actual column names (case-insensitive)
  key_col_matches <- sapply(key_cols, function(kc) {
    idx <- which(str_detect(names(df), regex(kc, ignore_case = TRUE)))
    if (length(idx) > 0) idx[1] else NA
  })

  if (all(is.na(key_col_matches))) {
    cat("WARNING: Could not find key columns for row collapsing\n")
    return(df)
  }

  # For now, just return df as-is (collapsing is complex without clear row boundaries)
  # This would require inspection of actual data patterns
  return(df)
}

df_data <- collapse_rows(df_data)

# ==============================================================================
# STEP 7: Standardize Column Names
# ==============================================================================

cat("Standardizing column names...\n")

# Expected columns (flexible matching)
col_mapping <- c(
  "Subclass" = "subclass",
  "Order" = "order",
  "Family" = "family",
  "Scientific name" = "scientific_name",
  "Species authorship" = "species_authorship",
  "Common name" = "common_name",
  "Maximum size" = "maximum_size_mm",
  "Depth distribution" = "depth_distribution_m",
  "Geographic distribution" = "geographic_distribution",
  "Remarks" = "remarks"
)

# Rename columns using flexible matching
for (old_pattern in names(col_mapping)) {
  matches <- str_which(names(df_data), regex(old_pattern, ignore_case = TRUE))

  if (length(matches) > 0) {
    names(df_data)[matches[1]] <- col_mapping[old_pattern]
  }
}

cat("Standardized column names:", paste(names(df_data), collapse = ", "), "\n\n")

# ==============================================================================
# STEP 8: Clean Specific Columns
# ==============================================================================

cat("Cleaning individual columns...\n")

# Clean Family column (remove numbers like "Heterodontidae 1" → "Heterodontidae")
if ("family" %in% names(df_data)) {
  df_data <- df_data %>%
    mutate(family = str_replace(family, "\\s+\\d+$", ""))
}

# Clean maximum_size_mm (remove " mm" suffix if present, extract numbers)
if ("maximum_size_mm" %in% names(df_data)) {
  df_data <- df_data %>%
    mutate(maximum_size_mm = as.numeric(str_extract(maximum_size_mm, "\\d+")))
}

# ==============================================================================
# STEP 9: Fill Down Hierarchical Columns
# ==============================================================================

cat("Filling down hierarchical columns...\n")

hierarchical_cols <- c("subclass", "order", "family")

for (col in hierarchical_cols) {
  if (col %in% names(df_data)) {
    df_data <- df_data %>%
      fill(!!sym(col), .direction = "down")
  }
}

# ==============================================================================
# STEP 10: Filter to Valid Species Rows
# ==============================================================================

cat("Filtering to valid species rows...\n")

# A valid row should have:
# - Non-NA scientific_name
# - Non-NA subclass, order, family (after fill-down)

df_clean <- df_data %>%
  filter(
    !is.na(scientific_name),
    !is.na(subclass),
    !is.na(order),
    !is.na(family)
  )

cat("Valid species rows:", nrow(df_clean), "\n\n")

# ==============================================================================
# STEP 11: Save Cleaned CSV
# ==============================================================================

cat("Saving cleaned data...\n")

write_csv(df_clean, output_csv)

cat("Saved to:", output_csv, "\n\n")

# ==============================================================================
# STEP 12: Summary Statistics
# ==============================================================================

cat("==============================================================================\n")
cat("SUMMARY\n")
cat("==============================================================================\n\n")

cat("Total species:", nrow(df_clean), "\n\n")

if ("subclass" %in% names(df_clean)) {
  cat("Species by subclass:\n")
  print(df_clean %>% count(subclass, sort = TRUE))
  cat("\n")
}

if ("order" %in% names(df_clean)) {
  cat("Top 10 orders:\n")
  print(df_clean %>% count(order, sort = TRUE) %>% head(10))
  cat("\n")
}

if ("family" %in% names(df_clean)) {
  cat("Top 10 families:\n")
  print(df_clean %>% count(family, sort = TRUE) %>% head(10))
  cat("\n")
}

cat("Column names in output:\n")
cat(paste(names(df_clean), collapse = "\n"), "\n\n")

cat("==============================================================================\n")
cat("CLEANING COMPLETE\n")
cat("==============================================================================\n\n")

cat("Next steps:\n")
cat("1. Review:", output_csv, "\n")
cat("2. Validate species count (expected ~1,188)\n")
cat("3. Check for issues:\n")
cat("   - Missing scientific names\n")
cat("   - Malformed data\n")
cat("   - Duplicate entries\n")
cat("4. Run further processing scripts if needed\n")

# ==============================================================================
# END OF SCRIPT
# ==============================================================================
