#!/usr/bin/env Rscript
# ==============================================================================
# Convert Oral PPT Analysis Discipline to 8-Discipline Schema and Highlight
# ==============================================================================

library(tidyverse)
library(readxl)
library(openxlsx)

# ==============================================================================
# STEP 1: Load Excel File
# ==============================================================================

excel_path <- here::here("Final Speakers EEA 2025.xlsx")

# Load workbook
wb <- loadWorkbook(excel_path)

# Read Oral PPT sheet
oral_ppt <- read_excel(excel_path, sheet = "Oral PPT")

cat("=== Loading Data ===\n")
cat("Oral PPT rows:", nrow(oral_ppt), "\n\n")

# ==============================================================================
# STEP 2: Define Discipline Mapping (same as used in create_discipline_summary.R)
# ==============================================================================

discipline_mapping <- tribble(
  ~original, ~mapped,
  "Biology", "1. Biology, Life History, & Health",
  "Ecology", "3. Trophic & Community Ecology",
  "Genetics & genomics", "4. Genetics, Genomics, & eDNA",
  "Spatial; SDM", "5. Movement, Space Use, & Habitat Modeling",
  "Spatial; MPA", "5. Movement, Space Use, & Habitat Modeling",
  "Fisheries", "6. Fisheries, Stock Assessment, & Management",
  "Policy", "7. Conservation Policy & Human Dimensions",
  "Citizen science", "7. Conservation Policy & Human Dimensions",
  "Statistics", "8. Data Science & Integrative Methods",
  "Field & gear", "6. Fisheries, Stock Assessment, & Management",
  "Pollution", "1. Biology, Life History, & Health",
  "human shark conflict", "7. Conservation Policy & Human Dimensions"
)

cat("=== Discipline Mapping ===\n")
print(discipline_mapping)
cat("\n")

# ==============================================================================
# STEP 3: Apply Mapping and Track Changes
# ==============================================================================

oral_ppt_updated <- oral_ppt %>%
  left_join(discipline_mapping, by = c("Analysis Discipline" = "original")) %>%
  mutate(
    # Track which rows are being updated
    was_updated = !is.na(`Analysis Discipline`) & !is.na(mapped),
    # Update to new schema
    `Analysis Discipline` = if_else(
      !is.na(mapped),
      mapped,
      `Analysis Discipline`
    )
  )

n_updated <- sum(oral_ppt_updated$was_updated, na.rm = TRUE)
cat("=== Updated Oral PPT ===\n")
cat("Rows updated:", n_updated, "\n")
cat("Rows unchanged:", sum(!oral_ppt_updated$was_updated, na.rm = TRUE), "\n\n")

# Show distribution
cat("=== New Distribution ===\n")
oral_ppt_updated %>%
  count(`Analysis Discipline`) %>%
  arrange(`Analysis Discipline`) %>%
  print(n = Inf)
cat("\n")

# ==============================================================================
# STEP 4: Write Back to Excel with Yellow Highlighting
# ==============================================================================

cat("=== Applying Changes to Excel ===\n")

# Define yellow highlight style
highlight_style <- createStyle(fgFill = "#FFFF00", fontColour = "#000000",
                               textDecoration = NULL)

# Find Analysis Discipline column index
col_idx <- which(names(oral_ppt_updated) == "Analysis Discipline")

# Remove tracking column before writing
oral_ppt_final <- oral_ppt_updated %>% select(-was_updated, -mapped)

# Write updated data to Oral PPT sheet
writeData(wb, sheet = "Oral PPT", x = oral_ppt_final, startRow = 1, colNames = TRUE)

# Highlight updated cells
updated_rows <- which(oral_ppt_updated$was_updated)
if (length(updated_rows) > 0) {
  # Add 1 to account for header row in Excel
  excel_rows <- updated_rows + 1

  for (row in excel_rows) {
    addStyle(wb, sheet = "Oral PPT", style = highlight_style,
             rows = row, cols = col_idx, gridExpand = FALSE, stack = TRUE)
  }

  cat("Highlighted", length(updated_rows), "cells in Oral PPT\n")
}

# ==============================================================================
# STEP 5: Update Data Sheet
# ==============================================================================

cat("\n=== Updating Data Sheet ===\n")

# Read current data sheet
data_sheet <- read_excel(excel_path, sheet = "data")

# Find rows from Oral PPT (format == "oral_ppt")
# Map them with updated disciplines
oral_lookup <- oral_ppt_final %>%
  select(`Name (First)`, `Name (Last)`, `Analysis Discipline`)

data_updated <- data_sheet %>%
  # Remove old Analysis Discipline for oral_ppt entries
  mutate(`Analysis Discipline` = if_else(format == "oral_ppt", NA_character_, `Analysis Discipline`)) %>%
  # Join with updated oral disciplines
  left_join(
    oral_lookup,
    by = c("Name (First)", "Name (Last)"),
    suffix = c("_old", "_new")
  ) %>%
  mutate(
    # Mark which rows are being updated
    was_updated = format == "oral_ppt" & !is.na(`Analysis Discipline_new`),
    # Update Analysis Discipline for oral_ppt entries
    `Analysis Discipline` = if_else(
      format == "oral_ppt",
      `Analysis Discipline_new`,
      `Analysis Discipline_old`
    )
  ) %>%
  select(-`Analysis Discipline_old`, -`Analysis Discipline_new`)

n_updated_data <- sum(data_updated$was_updated, na.rm = TRUE)
cat("Data sheet rows updated:", n_updated_data, "\n")

# Find Analysis Discipline column in data sheet
data_col_idx <- which(names(data_updated) == "Analysis Discipline")

# Remove tracking column
data_final <- data_updated %>% select(-was_updated)

# Write updated data
writeData(wb, sheet = "data", x = data_final, startRow = 1, colNames = TRUE)

# Highlight updated cells in data sheet
data_updated_rows <- which(data_updated$was_updated)
if (length(data_updated_rows) > 0) {
  excel_rows <- data_updated_rows + 1

  for (row in excel_rows) {
    addStyle(wb, sheet = "data", style = highlight_style,
             rows = row, cols = data_col_idx, gridExpand = FALSE, stack = TRUE)
  }

  cat("Highlighted", length(data_updated_rows), "cells in data sheet\n")
}

# ==============================================================================
# STEP 6: Save Workbook
# ==============================================================================

cat("\n=== Saving Workbook ===\n")

# Save
saveWorkbook(wb, excel_path, overwrite = TRUE)
cat("✓ Saved:", excel_path, "\n")

cat("\n=== Summary ===\n")
cat("Total cells highlighted:\n")
cat("  Oral PPT:", length(updated_rows), "\n")
cat("  Data sheet:", length(data_updated_rows), "\n")
cat("  Posters: 21 (from previous run)\n")
cat("  Additional Posters: 18 (from previous run)\n")
cat("\nAll updated cells should now be YELLOW\n")

# ==============================================================================
# COMPLETE
# ==============================================================================
