#!/usr/bin/env Rscript
# ==============================================================================
# Consolidate Duplicate Entries in Attendee List
# ==============================================================================
# Merge duplicate attendees, keeping most complete information
# ==============================================================================

library(tidyverse)
library(readxl)
library(openxlsx)

cat("=== Consolidating Duplicate Attendees ===\n\n")

# ==============================================================================
# STEP 1: Load attendee list
# ==============================================================================

attendees <- read_excel("EEA 2025 Attendee List.xlsx", sheet = 1)

cat("Original attendee list:", nrow(attendees), "rows\n\n")

# ==============================================================================
# STEP 2: Identify duplicates
# ==============================================================================

cat("=== Identifying duplicates ===\n\n")

duplicates <- attendees %>%
  group_by(`Name (First)`, `Name (Last)`) %>%
  filter(n() > 1) %>%
  arrange(`Name (First)`, `Name (Last)`)

cat("Found", nrow(duplicates), "duplicate rows (",
    n_distinct(duplicates[c("Name (First)", "Name (Last)")]), "unique people)\n\n")

if (nrow(duplicates) > 0) {
  cat("Duplicates:\n")
  print(duplicates %>%
    select(`Name (First)`, `Name (Last)`, Email, `Organisation / Institute`,
           presenting, poster, panel, organiser))
  cat("\n")
}

# ==============================================================================
# STEP 3: Consolidate duplicates
# ==============================================================================

cat("=== Consolidating duplicates ===\n\n")

# Separate duplicates from unique attendees
unique_attendees <- attendees %>%
  anti_join(duplicates, by = c("Name (First)", "Name (Last)"))

# Consolidate duplicates using summarise
if (nrow(duplicates) > 0) {
  consolidated_duplicates <- duplicates %>%
    group_by(`Name (First)`, `Name (Last)`) %>%
    summarise(
      Email = first(na.omit(Email)),
      `Organisation / Institute` = first(na.omit(`Organisation / Institute`)),
      `Discipline (GT Review)` = first(na.omit(`Discipline (GT Review)`)),
      `Discipline (8-category)` = first(na.omit(`Discipline (8-category)`)),
      # Logical columns: TRUE if any row is TRUE
      presenting = any(presenting, na.rm = TRUE),
      poster = any(poster, na.rm = TRUE),
      panel = any(panel, na.rm = TRUE),
      organiser = any(organiser, na.rm = TRUE),
      .groups = "drop"
    )

  cat("Consolidated", n_distinct(duplicates[c("Name (First)", "Name (Last)")]),
      "duplicate people into single entries\n\n")

  # Show what was consolidated
  cat("Consolidated entries:\n")
  print(consolidated_duplicates %>%
    select(`Name (First)`, `Name (Last)`, Email, `Organisation / Institute`,
           presenting, poster, panel, organiser))
  cat("\n")

  # Combine unique and consolidated
  attendees_dedup <- bind_rows(unique_attendees, consolidated_duplicates) %>%
    arrange(`Name (Last)`, `Name (First)`)
} else {
  attendees_dedup <- attendees
}

# ==============================================================================
# STEP 4: Summary
# ==============================================================================

cat("=== Summary ===\n\n")

cat("Original rows:", nrow(attendees), "\n")
cat("Unique attendees:", nrow(unique_attendees), "\n")
if (nrow(duplicates) > 0) {
  cat("Duplicate rows removed:", nrow(duplicates) - nrow(consolidated_duplicates), "\n")
  cat("Consolidated rows:", nrow(consolidated_duplicates), "\n")
}
cat("Final rows:", nrow(attendees_dedup), "\n\n")

# Check for any remaining duplicates
remaining_dupes <- attendees_dedup %>%
  group_by(`Name (First)`, `Name (Last)`) %>%
  filter(n() > 1)

if (nrow(remaining_dupes) > 0) {
  cat("⚠️  WARNING: Remaining duplicates found:\n")
  print(remaining_dupes)
} else {
  cat("✓ No remaining duplicates\n")
}

# ==============================================================================
# STEP 5: Save consolidated list
# ==============================================================================

cat("\n=== Saving consolidated list ===\n")

# Create new workbook
wb <- createWorkbook()
addWorksheet(wb, "Attendees")

# Write data
writeData(wb, sheet = 1, attendees_dedup, startRow = 1, colNames = TRUE)

# Format header
header_style <- createStyle(
  textDecoration = "bold",
  fgFill = "#4F81BD",
  fontColour = "#FFFFFF",
  border = "TopBottomLeftRight"
)

addStyle(wb, sheet = 1, header_style, rows = 1, cols = 1:ncol(attendees_dedup),
         gridExpand = TRUE, stack = TRUE)

# Highlight TRUE values in logical columns
true_style <- createStyle(fgFill = "#C6EFCE", fontColour = "#006100")
logical_cols <- which(sapply(attendees_dedup, is.logical))

for (col in logical_cols) {
  true_rows <- which(attendees_dedup[[col]]) + 1  # +1 for header

  if (length(true_rows) > 0) {
    for (row in true_rows) {
      addStyle(wb, sheet = 1, true_style, rows = row, cols = col,
               gridExpand = FALSE, stack = TRUE)
    }
  }
}

# Set column widths
setColWidths(wb, sheet = 1, cols = 1:ncol(attendees_dedup), widths = "auto")

# Save
saveWorkbook(wb, "EEA 2025 Attendee List.xlsx", overwrite = TRUE)

cat("✓ Saved: EEA 2025 Attendee List.xlsx\n")
cat("  Removed", nrow(attendees) - nrow(attendees_dedup), "duplicate rows\n")

# Also save a CSV backup
write_csv(attendees_dedup, "outputs/attendee_list_consolidated.csv")
cat("✓ Saved backup: outputs/attendee_list_consolidated.csv\n")

cat("\n✓ Consolidation complete\n")
