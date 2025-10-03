#!/usr/bin/env Rscript
# ==============================================================================
# Create Discipline Summary from EEA 2025 Data
# ==============================================================================

library(tidyverse)
library(readxl)

# ==============================================================================
# STEP 1: Load Data Sheet
# ==============================================================================

excel_path <- here::here("Final Speakers EEA 2025.xlsx")

# Check if data sheet exists, if not create it first
if (!"data" %in% excel_sheets(excel_path)) {
  cat("ERROR: 'data' sheet not found. Run create_data_sheet.R first.\n")
  quit(status = 1)
}

combined <- read_excel(excel_path, sheet = "data")

cat("=== Loading Data ===\n")
cat("Total rows:", nrow(combined), "\n\n")

# ==============================================================================
# STEP 2: Define 8-Discipline Schema
# ==============================================================================

# From EEA2025_Data_Panel_Program_Timeline_Personnel.md
discipline_schema <- c(
  "1. Biology, Life History, & Health",
  "2. Behaviour & Sensory Ecology",
  "3. Trophic & Community Ecology",
  "4. Genetics, Genomics, & eDNA",
  "5. Movement, Space Use, & Habitat Modeling",
  "6. Fisheries, Stock Assessment, & Management",
  "7. Conservation Policy & Human Dimensions",
  "8. Data Science & Integrative Methods"
)

# Disciplines with 10-minute oral presentations
disciplines_with_talks <- c(
  "1. Biology, Life History, & Health",           # Amy Jeffries
  "4. Genetics, Genomics, & eDNA",                # Charlotte Nuyt
  "5. Movement, Space Use, & Habitat Modeling",   # Edward Lavender
  "7. Conservation Policy & Human Dimensions",    # Nicholas Dulvy
  "8. Data Science & Integrative Methods"         # Maria Dolores Riesgo
)

# ==============================================================================
# STEP 3: Map Existing Analysis Discipline to 8-Discipline Schema
# ==============================================================================

# Create mapping from existing categories to 8-discipline schema
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

# Topic-based mapping for posters (case-insensitive)
topic_mapping <- tribble(
  ~topic_pattern, ~discipline,
  "ecology.*life history", "1. Biology, Life History, & Health",
  "genetics", "4. Genetics, Genomics, & eDNA",
  "tagging.*telemetry", "5. Movement, Space Use, & Habitat Modeling",
  "fisheries", "6. Fisheries, Stock Assessment, & Management",
  "conservation.*management", "7. Conservation Policy & Human Dimensions",
  "citizen science", "7. Conservation Policy & Human Dimensions",
  "big data.*methods", "8. Data Science & Integrative Methods"
)

# Apply mapping
combined <- combined %>%
  left_join(discipline_mapping, by = c("Analysis Discipline" = "original")) %>%
  mutate(
    # First try Analysis Discipline mapping
    discipline = case_when(
      !is.na(mapped) ~ mapped,
      !is.na(`Analysis Discipline`) & str_detect(`Analysis Discipline`, "^[1-8]\\.") ~ `Analysis Discipline`,
      TRUE ~ NA_character_
    )
  )

# For rows still unclassified, try Topic mapping
for (i in 1:nrow(topic_mapping)) {
  pattern <- topic_mapping$topic_pattern[i]
  disc <- topic_mapping$discipline[i]

  combined <- combined %>%
    mutate(
      discipline = if_else(
        is.na(discipline) & str_detect(tolower(coalesce(Topic, "")), pattern),
        disc,
        discipline
      )
    )
}

# Final fallback to Unclassified
combined <- combined %>%
  mutate(discipline = coalesce(discipline, "Unclassified"))

cat("=== Discipline Mapping Applied ===\n")
cat("Mapped rows:", sum(!is.na(combined$mapped)), "\n")
cat("Unclassified rows:", sum(combined$discipline == "Unclassified"), "\n\n")

# ==============================================================================
# STEP 4: Create Discipline Summary
# ==============================================================================

# Create complete discipline list including those with 0 presentations
discipline_summary <- tibble(discipline = discipline_schema) %>%
  left_join(
    combined %>%
      group_by(discipline) %>%
      summarise(
        oral_presentations = sum(format == "oral_ppt", na.rm = TRUE),
        posters = sum(format == "poster", na.rm = TRUE),
        additional_posters = sum(format == "add_poster", na.rm = TRUE),
        total_presentations = n(),
        .groups = "drop"
      ),
    by = "discipline"
  ) %>%
  # Replace NA with 0 for disciplines with no presentations
  mutate(
    oral_presentations = replace_na(oral_presentations, 0),
    posters = replace_na(posters, 0),
    additional_posters = replace_na(additional_posters, 0),
    total_presentations = replace_na(total_presentations, 0)
  ) %>%
  # Add panel_oral column
  mutate(
    panel_oral = discipline %in% disciplines_with_talks
  ) %>%
  # Arrange alphabetically
  arrange(discipline)

cat("=== Discipline Summary (8 Disciplines) ===\n")
print(discipline_summary)

# ==============================================================================
# STEP 5: Show Unclassified Items
# ==============================================================================

unclassified <- combined %>%
  filter(discipline == "Unclassified") %>%
  select(`Name (First)`, `Name (Last)`, Title, Topic, `Analysis Discipline`, format)

if (nrow(unclassified) > 0) {
  cat("\n=== Unclassified Items (need manual review) ===\n")
  cat("Count:", nrow(unclassified), "\n")
  print(unclassified)
}

# ==============================================================================
# STEP 6: Save Outputs
# ==============================================================================

dir.create("outputs", showWarnings = FALSE)
write_csv(discipline_summary, "outputs/discipline_summary.csv")

cat("\n✓ Saved outputs/discipline_summary.csv\n")

# ==============================================================================
# STEP 7: Update Timeline Document Section
# ==============================================================================

# Create formatted text for timeline document
timeline_text <- discipline_summary %>%
  mutate(
    has_talk = if_else(panel_oral, " (10 min talk)", ""),
    presentation_text = case_when(
      total_presentations == 1 ~ "1 presentation",
      total_presentations > 1 ~ paste0(total_presentations, " presentations"),
      TRUE ~ "0 presentations"
    ),
    poster_text = case_when(
      posters == 0 ~ "",
      posters == 1 ~ ", 1 poster",
      TRUE ~ paste0(", ", posters, " posters")
    ),
    line = paste0("- **", discipline, "**", has_talk, ": ", presentation_text, poster_text)
  ) %>%
  pull(line)

cat("\n=== Text for Timeline Document ===\n")
cat("Copy this to EEA2025_Data_Panel_Program_Timeline_Personnel.md:\n\n")
cat("**Dominant topics at EEA 2025:**\n\n")
cat(paste(timeline_text, collapse = "\n"))
cat("\n\n")

# ==============================================================================
# COMPLETE
# ==============================================================================

cat("\n==============================================================================\n")
cat("COMPLETE\n")
cat("==============================================================================\n")
cat("\nNext steps:\n")
cat("1. Review unclassified items above\n")
cat("2. Manually classify remaining items if needed\n")
cat("3. Update EEA2025_Data_Panel_Program_Timeline_Personnel.md with text above\n")
