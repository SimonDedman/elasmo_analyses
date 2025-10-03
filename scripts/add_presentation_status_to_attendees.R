#!/usr/bin/env Rscript
# ==============================================================================
# Add Presentation Status Columns to Attendee List
# ==============================================================================
# Add logical columns: presenting, poster, panel, organiser
# Cross-reference with Final Speakers and candidate database
# ==============================================================================

library(tidyverse)
library(readxl)
library(openxlsx)

cat("=== Adding Presentation Status to Attendee List ===\n\n")

# ==============================================================================
# STEP 1: Load data sources
# ==============================================================================

# Attendee list
attendees <- read_excel("EEA 2025 Attendee List.xlsx", sheet = 1)
cat("Loaded attendee list:", nrow(attendees), "attendees\n")

# Final Speakers
speakers <- read_excel("Final Speakers EEA 2025.xlsx", sheet = 1)
cat("Loaded speakers list:", nrow(speakers), "speakers\n")

# Candidate database
candidates <- read_csv("outputs/candidate_database_phase1.csv", show_col_types = FALSE)
cat("Loaded candidate database:", nrow(candidates), "candidates\n\n")

# ==============================================================================
# STEP 2: Extract status from speakers list
# ==============================================================================

cat("=== Extracting status from speakers list ===\n\n")

# Extract presentation status
speakers_status <- speakers %>%
  select(
    name_first = `Name (First)`,
    name_last = `Name (Last)`,
    decision = `Decision - oral presentation, poster, presentation or panel/breakout session, reject`,
    panel_prez = PanelPrez,
    format = format
  ) %>%
  mutate(
    # Parse decision column
    is_oral = str_detect(decision, regex("oral|presentation", ignore_case = TRUE)) &
              !str_detect(decision, regex("reject", ignore_case = TRUE)),
    is_poster = str_detect(decision, regex("poster", ignore_case = TRUE)),
    is_panel = str_detect(decision, regex("panel|breakout", ignore_case = TRUE)) |
               !is.na(panel_prez),
    # Also check format column
    is_oral = is_oral | str_detect(coalesce(format, ""), regex("oral|O_", ignore_case = TRUE)),
    is_poster = is_poster | str_detect(coalesce(format, ""), regex("poster|P_", ignore_case = TRUE))
  )

cat("Speakers with oral presentations:", sum(speakers_status$is_oral, na.rm = TRUE), "\n")
cat("Speakers with posters:", sum(speakers_status$is_poster, na.rm = TRUE), "\n")
cat("Speakers on panels:", sum(speakers_status$is_panel, na.rm = TRUE), "\n\n")

# ==============================================================================
# STEP 3: Extract status from candidate database
# ==============================================================================

cat("=== Extracting status from candidate database ===\n\n")

# Map eea_2025_status to logical columns
candidates_status <- candidates %>%
  select(
    name_first,
    name_last,
    eea_2025_status
  ) %>%
  mutate(
    # Parse eea_2025_status
    is_oral_db = str_detect(coalesce(eea_2025_status, ""), regex("presentation|oral", ignore_case = TRUE)),
    is_poster_db = str_detect(coalesce(eea_2025_status, ""), regex("poster", ignore_case = TRUE)),
    is_panel_db = str_detect(coalesce(eea_2025_status, ""), regex("panel", ignore_case = TRUE)),
    is_organiser_db = str_detect(coalesce(eea_2025_status, ""), regex("organis|organiz", ignore_case = TRUE))
  )

cat("Candidates with oral (DB):", sum(candidates_status$is_oral_db, na.rm = TRUE), "\n")
cat("Candidates with poster (DB):", sum(candidates_status$is_poster_db, na.rm = TRUE), "\n")
cat("Candidates with panel (DB):", sum(candidates_status$is_panel_db, na.rm = TRUE), "\n")
cat("Candidates as organisers (DB):", sum(candidates_status$is_organiser_db, na.rm = TRUE), "\n\n")

# ==============================================================================
# STEP 4: Identify organisers
# ==============================================================================

# Panel organisers (from project knowledge)
organisers <- tribble(
  ~name_first, ~name_last,
  "Simon", "Dedman",
  "Guuske", "Tiktak"
)

cat("Known organisers:", nrow(organisers), "\n\n")

# ==============================================================================
# STEP 5: Merge status into attendee list
# ==============================================================================

cat("=== Merging status into attendee list ===\n\n")

# Join with speakers
attendees_updated <- attendees %>%
  left_join(
    speakers_status %>% select(name_first, name_last, is_oral, is_poster, is_panel),
    by = c("Name (First)" = "name_first", "Name (Last)" = "name_last")
  ) %>%
  # Join with candidate database
  left_join(
    candidates_status %>% select(name_first, name_last, is_oral_db, is_poster_db, is_panel_db, is_organiser_db),
    by = c("Name (First)" = "name_first", "Name (Last)" = "name_last")
  ) %>%
  # Join with organisers
  left_join(
    organisers %>% mutate(is_organiser_list = TRUE),
    by = c("Name (First)" = "name_first", "Name (Last)" = "name_last")
  ) %>%
  # Combine sources (TRUE from any source = TRUE)
  mutate(
    presenting = coalesce(is_oral, FALSE) | coalesce(is_oral_db, FALSE),
    poster = coalesce(is_poster, FALSE) | coalesce(is_poster_db, FALSE),
    panel = coalesce(is_panel, FALSE) | coalesce(is_panel_db, FALSE),
    organiser = coalesce(is_organiser_list, FALSE) | coalesce(is_organiser_db, FALSE)
  ) %>%
  # Remove intermediate columns
  select(-is_oral, -is_poster, -is_panel, -is_oral_db, -is_poster_db, -is_panel_db,
         -is_organiser_db, -is_organiser_list)

# ==============================================================================
# STEP 6: Summary statistics
# ==============================================================================

cat("=== Summary Statistics ===\n\n")

cat("Total attendees:", nrow(attendees_updated), "\n")
cat("With oral presentations:", sum(attendees_updated$presenting), "\n")
cat("With posters:", sum(attendees_updated$poster), "\n")
cat("On panel:", sum(attendees_updated$panel), "\n")
cat("Organisers:", sum(attendees_updated$organiser), "\n")

cat("\nAttendees with multiple roles:\n")
cat("  Presenting + Poster:", sum(attendees_updated$presenting & attendees_updated$poster), "\n")
cat("  Presenting + Panel:", sum(attendees_updated$presenting & attendees_updated$panel), "\n")
cat("  Poster + Panel:", sum(attendees_updated$poster & attendees_updated$panel), "\n")
cat("  Organiser + Presenting:", sum(attendees_updated$organiser & attendees_updated$presenting), "\n")

cat("\nAttendees not presenting:", sum(!attendees_updated$presenting & !attendees_updated$poster & !attendees_updated$panel), "\n\n")

# ==============================================================================
# STEP 7: Show examples
# ==============================================================================

cat("=== Examples ===\n\n")

cat("Presenters:\n")
attendees_updated %>%
  filter(presenting) %>%
  select(`Name (First)`, `Name (Last)`, presenting, poster, panel, organiser) %>%
  head(10) %>%
  print()

cat("\nPoster presenters:\n")
attendees_updated %>%
  filter(poster) %>%
  select(`Name (First)`, `Name (Last)`, presenting, poster, panel, organiser) %>%
  head(10) %>%
  print()

cat("\nPanel members:\n")
attendees_updated %>%
  filter(panel) %>%
  select(`Name (First)`, `Name (Last)`, presenting, poster, panel, organiser) %>%
  print()

cat("\nOrganisers:\n")
attendees_updated %>%
  filter(organiser) %>%
  select(`Name (First)`, `Name (Last)`, presenting, poster, panel, organiser) %>%
  print()

# ==============================================================================
# STEP 8: Save updated attendee list
# ==============================================================================

cat("\n=== Saving updated attendee list ===\n")

# Load existing workbook to preserve formatting
wb <- loadWorkbook("EEA 2025 Attendee List.xlsx")

# Get existing data dimensions
existing_cols <- ncol(attendees)

# Write the new columns
writeData(wb, sheet = 1, attendees_updated, startRow = 1, colNames = TRUE)

# Add header formatting for new columns
header_style <- createStyle(
  textDecoration = "bold",
  fgFill = "#4F81BD",
  fontColour = "#FFFFFF",
  border = "TopBottomLeftRight"
)

new_col_start <- existing_cols + 1
new_col_end <- ncol(attendees_updated)

for (col in new_col_start:new_col_end) {
  addStyle(wb, sheet = 1, header_style, rows = 1, cols = col, gridExpand = FALSE, stack = TRUE)
}

# Highlight TRUE values in green
true_style <- createStyle(fgFill = "#C6EFCE", fontColour = "#006100")

for (col in new_col_start:new_col_end) {
  # Find rows where value is TRUE
  true_rows <- which(attendees_updated[[col]]) + 1  # +1 for header

  if (length(true_rows) > 0) {
    for (row in true_rows) {
      addStyle(wb, sheet = 1, true_style, rows = row, cols = col, gridExpand = FALSE, stack = TRUE)
    }
  }
}

# Save
saveWorkbook(wb, "EEA 2025 Attendee List.xlsx", overwrite = TRUE)

cat("✓ Saved: EEA 2025 Attendee List.xlsx\n")
cat("  Added columns: presenting, poster, panel, organiser\n")
cat("  TRUE values highlighted in green\n")

cat("\n✓ Update complete\n")
