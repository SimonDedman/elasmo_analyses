#!/usr/bin/env Rscript
# ==============================================================================
# Create Combined Data Sheet and Discipline Summary
# ==============================================================================

library(tidyverse)
library(readxl)
library(writexl)

# ==============================================================================
# STEP 1: Read Excel Sheets
# ==============================================================================

excel_path <- here::here("Final Speakers EEA 2025.xlsx")
sheet_names <- excel_sheets(excel_path)

oral_ppt <- read_excel(excel_path, sheet = sheet_names[1])
poster <- read_excel(excel_path, sheet = sheet_names[2])
add_poster <- read_excel(excel_path, sheet = sheet_names[3])

cat("=== Loading Data ===\n")
cat("Oral presentations:", nrow(oral_ppt), "\n")
cat("Posters:", nrow(poster), "\n")
cat("Additional posters:", nrow(add_poster), "\n\n")

# ==============================================================================
# STEP 2: Add Format Column
# ==============================================================================

oral_ppt$format <- "oral_ppt"
poster$format <- "poster"
add_poster$format <- "add_poster"

# ==============================================================================
# STEP 3: Harmonize Column Names
# ==============================================================================

# Rename nr/NR to standardize
if ("NR" %in% names(poster)) {
  poster <- poster %>% rename(nr = NR)
}

if ("NR" %in% names(add_poster)) {
  add_poster <- add_poster %>% rename(nr = NR)
}

# ==============================================================================
# STEP 4: Combine All Sheets
# ==============================================================================

combined <- bind_rows(
  oral_ppt %>% mutate(source_sheet = "Oral PPT"),
  poster %>% mutate(source_sheet = "Posters"),
  add_poster %>% mutate(source_sheet = "Additional Posters")
)

cat("=== Combined Data ===\n")
cat("Total rows:", nrow(combined), "\n")
cat("Total columns:", ncol(combined), "\n\n")

# ==============================================================================
# STEP 5: Create Discipline Column Using 8-Discipline Schema
# ==============================================================================

# Define discipline mapping based on Analysis Discipline and Topic
combined <- combined %>%
  mutate(
    discipline = case_when(
      # Use existing Analysis Discipline if available
      !is.na(`Analysis Discipline`) ~ `Analysis Discipline`,

      # Otherwise map from Topic
      str_detect(tolower(Topic), "ecology|life history") ~ "1. Biology, Life History, & Health",
      str_detect(tolower(Topic), "behav|sensory") ~ "2. Behaviour & Sensory Ecology",
      str_detect(tolower(Topic), "trophic|diet|food") ~ "3. Trophic & Community Ecology",
      str_detect(tolower(Topic), "genet|genomic|edna") ~ "4. Genetics, Genomics, & eDNA",
      str_detect(tolower(Topic), "tagging|telemetry|spatial|movement") ~ "5. Movement, Space Use, & Habitat Modeling",
      str_detect(tolower(Topic), "fisheries|stock") ~ "6. Fisheries, Stock Assessment, & Management",
      str_detect(tolower(Topic), "conservation|management|policy") ~ "7. Conservation Policy & Human Dimensions",
      str_detect(tolower(Topic), "big data|methods|statistic") ~ "8. Data Science & Integrative Methods",

      # Default
      TRUE ~ "Unclassified"
    )
  )

# Show discipline distribution
cat("=== Discipline Distribution ===\n")
discipline_counts <- combined %>%
  count(discipline, format) %>%
  pivot_wider(names_from = format, values_from = n, values_fill = 0) %>%
  mutate(total = oral_ppt + poster + add_poster)

print(discipline_counts)

# ==============================================================================
# STEP 6: Save Updated Excel with Data Sheet
# ==============================================================================

sheets_list <- list(
  "Oral PPT" = oral_ppt,
  "Posters" = poster,
  "Additional Posters" = add_poster,
  "data" = combined
)

write_xlsx(sheets_list, excel_path)
cat("\n✓ Added 'data' sheet to Excel file\n")

# ==============================================================================
# STEP 7: Create Summary CSV for Outputs
# ==============================================================================

# Create discipline summary table
discipline_summary <- combined %>%
  group_by(discipline) %>%
  summarise(
    oral_presentations = sum(format == "oral_ppt", na.rm = TRUE),
    posters = sum(format == "poster", na.rm = TRUE),
    additional_posters = sum(format == "add_poster", na.rm = TRUE),
    total_presentations = n(),
    has_panel_review = any(!is.na(PanelPrez) & PanelPrez == TRUE, na.rm = TRUE),
    .groups = "drop"
  ) %>%
  arrange(discipline)

# Save to outputs folder
dir.create("outputs", showWarnings = FALSE)
write_csv(discipline_summary, "outputs/discipline_summary.csv")

cat("\n=== Discipline Summary ===\n")
print(discipline_summary)

cat("\n✓ Saved outputs/discipline_summary.csv\n")

# ==============================================================================
# STEP 8: Show Sample Data
# ==============================================================================

cat("\n=== Sample Combined Data ===\n")
combined %>%
  select(`Name (First)`, `Name (Last)`, Title, format, discipline, PanelPrez) %>%
  head(10) %>%
  print()

cat("\n==============================================================================\n")
cat("COMPLETE\n")
cat("==============================================================================\n")
