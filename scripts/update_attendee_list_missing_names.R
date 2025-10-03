#!/usr/bin/env Rscript
# ==============================================================================
# Update Attendee List with Missing Names
# ==============================================================================
# Based on abstract search findings:
# - Renzo = Lorenzo Elias (co-author on Greenway abstract)
# - ?? (Shark Trust #1) = Hettie Brown (from abstracts O_08, P02)
# - ?? (Shark Trust #2) = Still unknown (possibly Paul Cox from O_28?)
# - WOZEP = Still unknown
# ==============================================================================

library(tidyverse)
library(readxl)
library(openxlsx)

cat("=== Updating Attendee List with Found Names ===\n\n")

# ==============================================================================
# STEP 1: Load attendee list
# ==============================================================================

attendees <- read_excel("EEA 2025 Attendee List.xlsx", sheet = 1)

cat("Original attendee list:\", nrow(attendees), \"attendees\n\n")

# Show incomplete entries
incomplete <- attendees %>%
  filter(is.na(`Name (Last)`) | `Name (Last)` %in% c("??", "WOZEP", ""))

cat("Incomplete entries:\n")
print(incomplete %>% select(1:4))
cat("\n")

# ==============================================================================
# STEP 2: Update known names
# ==============================================================================

cat("=== Findings from abstract search ===\n\n")

cat("✓ Renzo = Lorenzo Elias\n")
cat("  - Co-author on Eleanor Greenway's abstract (O_30)\n")
cat("  - Abstract: Age determination in Raja species\n")
cat("  - Institution: Wageningen University and Research\n\n")

cat("✓ ?? (Shark Trust) = Hettie Brown\n")
cat("  - Author on abstracts O_08 and P02\n")
cat("  - Email: hettie@sharktrust.org\n")
cat("  - Topics: Guitarfish fisheries, Angel sharks\n\n")

cat("? ?? (Shark Trust #2) = Possibly Paul B. Cox\n")
cat("  - Co-author on Cat Gordon's abstract (O_28)\n")
cat("  - Institution: The Shark Trust\n")
cat("  - OR could be another Shark Trust co-author from abstracts\n\n")

cat("? WOZEP = Unknown\n")
cat("  - No matches found in abstracts\n")
cat("  - May need manual lookup or could be abbreviation/nickname\n\n")

# ==============================================================================
# STEP 3: Create updated attendee list
# ==============================================================================

attendees_updated <- attendees %>%
  mutate(
    # Update Renzo -> Lorenzo Elias
    `Name (First)` = if_else(`Name (First)` == "Renzo", "Lorenzo", `Name (First)`),
    `Name (Last)` = if_else(row_number() == which(`Name (First)` == "Lorenzo")[1],
                            "Elias", `Name (Last)`),
    `Organisation / Institute` = if_else(
      row_number() == which(`Name (First)` == "Lorenzo")[1],
      "Wageningen University and Research",
      `Organisation / Institute`
    )
  )

# Update first Shark Trust ?? to Hettie Brown
shark_trust_unknown_rows <- which(attendees_updated$`Name (First)` == "??" &
                                  !is.na(attendees_updated$`Organisation / Institute`) &
                                  str_detect(attendees_updated$`Organisation / Institute`, "Shark Trust"))

if (length(shark_trust_unknown_rows) >= 1) {
  # First unknown = Hettie Brown
  attendees_updated$`Name (First)`[shark_trust_unknown_rows[1]] <- "Hettie"
  attendees_updated$`Name (Last)`[shark_trust_unknown_rows[1]] <- "Brown"
  attendees_updated$Email[shark_trust_unknown_rows[1]] <- "hettie@sharktrust.org"
}

if (length(shark_trust_unknown_rows) >= 2) {
  # Second unknown = tentatively Paul Cox (needs confirmation)
  attendees_updated$`Name (First)`[shark_trust_unknown_rows[2]] <- "Paul"
  attendees_updated$`Name (Last)`[shark_trust_unknown_rows[2]] <- "Cox"
  # Leave email blank as we don't have it confirmed
}

# ==============================================================================
# STEP 4: Save with highlighting
# ==============================================================================

cat("=== Saving updated attendee list ===\n\n")

# Create workbook
wb <- loadWorkbook("EEA 2025 Attendee List.xlsx")

# Define yellow fill style
yellow_style <- createStyle(fgFill = "#FFFF00")

# Get row numbers for updated entries
renzo_row <- which(attendees_updated$`Name (First)` == "Lorenzo" &
                   attendees_updated$`Name (Last)` == "Elias") + 1  # +1 for header

hettie_row <- which(attendees_updated$`Name (First)` == "Hettie" &
                    attendees_updated$`Name (Last)` == "Brown") + 1

paul_row <- which(attendees_updated$`Name (First)` == "Paul" &
                  attendees_updated$`Name (Last)` == "Cox") + 1

# Write updated data
writeData(wb, sheet = 1, attendees_updated, startRow = 1, colNames = TRUE)

# Apply yellow highlighting to updated cells
if (length(renzo_row) > 0) {
  addStyle(wb, sheet = 1, yellow_style, rows = renzo_row, cols = 1:4, gridExpand = FALSE, stack = TRUE)
  cat("✓ Highlighted Lorenzo Elias (row", renzo_row, ")\n")
}

if (length(hettie_row) > 0) {
  addStyle(wb, sheet = 1, yellow_style, rows = hettie_row, cols = 1:4, gridExpand = FALSE, stack = TRUE)
  cat("✓ Highlighted Hettie Brown (row", hettie_row, ")\n")
}

if (length(paul_row) > 0) {
  addStyle(wb, sheet = 1, yellow_style, rows = paul_row, cols = 1:3, gridExpand = FALSE, stack = TRUE)
  cat("✓ Highlighted Paul Cox (row", paul_row, ") - tentative\n")
}

saveWorkbook(wb, "EEA 2025 Attendee List.xlsx", overwrite = TRUE)

cat("\n✓ Saved: EEA 2025 Attendee List.xlsx\n")

# ==============================================================================
# STEP 5: Summary
# ==============================================================================

cat("\n=== Summary ===\n\n")

cat("Updated:\n")
cat("  ✓ Renzo → Lorenzo Elias (Wageningen University)\n")
cat("  ✓ ?? (Shark Trust #1) → Hettie Brown (hettie@sharktrust.org)\n")
cat("  ~ ?? (Shark Trust #2) → Paul Cox (TENTATIVE - needs confirmation)\n\n")

cat("Still unknown:\n")
cat("  ✗ WOZEP - no matches found in abstracts\n\n")

cat("Recommendation:\n")
cat("  - Contact Shark Trust directly to confirm Paul Cox attendance\n")
cat("  - Ask event organizers about 'WOZEP' entry\n")
cat("  - May be misspelling, nickname, or organization abbreviation\n\n")

cat("✓ Update complete\n")
