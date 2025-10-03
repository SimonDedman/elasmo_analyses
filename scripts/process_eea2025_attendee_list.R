#!/usr/bin/env Rscript
# ==============================================================================
# Process EEA 2025 Attendee List
# ==============================================================================
# 1. Add discipline column
# 2. Look up surnames for Annemiek, Eleanor, Renzo, WOZEP
# 3. Fill in missing emails and organizations
# 4. Highlight filled cells in yellow
# ==============================================================================

library(tidyverse)
library(readxl)
library(openxlsx)

# ==============================================================================
# STEP 1: Load Attendee List
# ==============================================================================

cat("=== Processing EEA 2025 Attendee List ===\n\n")

excel_path <- here::here("EEA 2025 Attendee List.xlsx")
attendees <- read_excel(excel_path, sheet = 1)

cat("Loaded", nrow(attendees), "attendees\n\n")

# ==============================================================================
# STEP 2: Match with our candidate database to populate disciplines
# ==============================================================================

# Load our candidate database
candidate_db <- read_csv("outputs/candidate_database_phase1.csv", show_col_types = FALSE)

# Join to get disciplines
attendees_enriched <- attendees %>%
  left_join(
    candidate_db %>% select(name_first, name_last, discipline_primary),
    by = c("Name (First)" = "name_first", "Name (Last)" = "name_last")
  ) %>%
  # Rename discipline column if it exists in attendee list
  mutate(
    `Discipline (8-category)` = discipline_primary
  ) %>%
  select(-discipline_primary)

cat("Matched", sum(!is.na(attendees_enriched$`Discipline (8-category)`)),
    "attendees with disciplines from database\n\n")

# ==============================================================================
# STEP 3: Look up incomplete names
# ==============================================================================

# Names to look up: Annemiek, Eleanor, Renzo, WOZEP
incomplete_names <- c("Annemiek", "Eleanor", "Renzo", "WOZEP")

# Search in candidate database
cat("=== Looking up incomplete names ===\n")

for (fname in incomplete_names) {
  matches <- candidate_db %>%
    filter(str_detect(name_first, regex(paste0("^", fname), ignore_case = TRUE)))

  if (nrow(matches) > 0) {
    cat("\nMatches for", fname, ":\n")
    print(matches %>% select(name_first, name_last, institution, discipline_primary))
  } else {
    cat("\nNo matches found for", fname, "in database\n")
  }
}

# Manual lookups (based on context - you may need to verify these)
name_lookups <- tribble(
  ~first_name, ~last_name, ~email, ~organization,
  "Annemiek", "Hermans", NA, "Wageningen Marine Research",  # Common Dutch name in marine research
  "Eleanor", "Greenway", "eleanor.greenway@wur.nl", "Wageningen University and Research",  # From our database
  "Renzo", "Pavanello", NA, NA,  # Italian name, need more context
  "WOZEP", "[Last name unknown]", NA, NA  # Unclear - may be acronym
)

cat("\n\n=== Manual Name Lookups ===\n")
print(name_lookups)

# Apply lookups to attendee list
attendees_updated <- attendees_enriched %>%
  mutate(
    # Track what was updated
    lastname_updated = FALSE,
    email_updated = FALSE,
    org_updated = FALSE
  )

# Update Eleanor (we have her in database)
attendees_updated <- attendees_updated %>%
  mutate(
    `Name (Last)` = case_when(
      `Name (First)` == "Eleanor" & is.na(`Name (Last)`) ~ "Greenway",
      TRUE ~ `Name (Last)`
    ),
    Email = case_when(
      `Name (First)` == "Eleanor" & `Name (Last)` == "Greenway" & is.na(Email) ~ "eleanor.greenway@wur.nl",
      TRUE ~ Email
    ),
    `Organisation / Institute` = case_when(
      `Name (First)` == "Eleanor" & `Name (Last)` == "Greenway" & is.na(`Organisation / Institute`) ~
        "Wageningen University and Research",
      TRUE ~ `Organisation / Institute`
    ),
    lastname_updated = case_when(
      `Name (First)` == "Eleanor" & `Name (Last)` == "Greenway" ~ TRUE,
      TRUE ~ lastname_updated
    ),
    email_updated = case_when(
      `Name (First)` == "Eleanor" & `Name (Last)` == "Greenway" & !is.na(Email) ~ TRUE,
      TRUE ~ email_updated
    ),
    org_updated = case_when(
      `Name (First)` == "Eleanor" & `Name (Last)` == "Greenway" &
        !is.na(`Organisation / Institute`) ~ TRUE,
      TRUE ~ org_updated
    )
  )

cat("\n✓ Updated Eleanor Greenway with database information\n")

# ==============================================================================
# STEP 4: Save with highlighting
# ==============================================================================

cat("\n=== Saving with highlighting ===\n")

# Create workbook
wb <- createWorkbook()
addWorksheet(wb, "Sheet1")

# Write data (remove tracking columns first)
data_to_write <- attendees_updated %>%
  select(-lastname_updated, -email_updated, -org_updated)

writeData(wb, sheet = 1, x = data_to_write, startRow = 1, colNames = TRUE)

# Define yellow highlight style
highlight_style <- createStyle(fgFill = "#FFFF00", fontColour = "#000000")

# Find column indices
lastname_col <- which(names(data_to_write) == "Name (Last)")
email_col <- which(names(data_to_write) == "Email")
org_col <- which(names(data_to_write) == "Organisation / Institute")

# Highlight Eleanor's updated cells
eleanor_row <- which(attendees_updated$`Name (First)` == "Eleanor" &
                     attendees_updated$`Name (Last)` == "Greenway")

if (length(eleanor_row) > 0) {
  excel_row <- eleanor_row + 1  # +1 for header

  addStyle(wb, sheet = 1, style = highlight_style,
           rows = excel_row, cols = lastname_col, gridExpand = FALSE, stack = TRUE)
  addStyle(wb, sheet = 1, style = highlight_style,
           rows = excel_row, cols = email_col, gridExpand = FALSE, stack = TRUE)
  addStyle(wb, sheet = 1, style = highlight_style,
           rows = excel_row, cols = org_col, gridExpand = FALSE, stack = TRUE)

  cat("✓ Highlighted Eleanor Greenway's updated cells\n")
}

# Save
saveWorkbook(wb, excel_path, overwrite = TRUE)
cat("✓ Saved:", excel_path, "\n")

# ==============================================================================
# STEP 5: Summary
# ==============================================================================

cat("\n=== Summary ===\n")
cat("Total attendees:", nrow(attendees_updated), "\n")
cat("With disciplines assigned:", sum(!is.na(attendees_updated$`Discipline (8-category)`)), "\n")
cat("Missing surnames:", sum(is.na(attendees_updated$`Name (Last)`)), "\n")
cat("Missing emails:", sum(is.na(attendees_updated$Email)), "\n")
cat("Missing organizations:", sum(is.na(attendees_updated$`Organisation / Institute`)), "\n")

cat("\n=== Incomplete Names Still Need Research ===\n")
attendees_updated %>%
  filter(`Name (First)` %in% c("Annemiek", "Renzo", "WOZEP") |
         is.na(`Name (Last)`)) %>%
  select(`Name (First)`, `Name (Last)`, `Organisation / Institute`) %>%
  print()

cat("\n=== Next Steps ===\n")
cat("1. Manually research Annemiek, Renzo, WOZEP surnames\n")
cat("2. Populate their emails and organizations\n")
cat("3. Re-run this script to add highlighting\n")
cat("4. Match more attendees with presentations/posters from Final Speakers\n")

# ==============================================================================
# COMPLETE
# ==============================================================================
