#!/usr/bin/env Rscript
# ==============================================================================
# Populate Poster Metadata from Additional Posters Tab
# ==============================================================================
# Purpose: Fill in NA titles and presenter names for poster presentations
#          using data from "Additional Posters" tab in Excel
# Input:   outputs/techniques_from_titles_abstracts.csv
#          Final Speakers EEA 2025.xlsx (Additional Posters tab)
# Output:  outputs/techniques_from_titles_abstracts.csv (overwritten)
# ==============================================================================

library(tidyverse)
library(readxl)

cat("=== Populating Poster Metadata ===\n\n")

# ==============================================================================
# STEP 1: Load data
# ==============================================================================

cat("Loading data...\n")

techniques <- read_csv(
  "outputs/techniques_from_titles_abstracts.csv",
  show_col_types = FALSE
)

additional_posters <- read_excel(
  "Final Speakers EEA 2025.xlsx",
  sheet = "Additional Posters"
)

cat("✓ Loaded", nrow(techniques), "technique rows\n")
cat("✓ Loaded", nrow(additional_posters), "additional poster records\n\n")

# ==============================================================================
# STEP 2: Normalize presentation IDs in Additional Posters
# ==============================================================================

cat("Normalizing presentation IDs...\n")

# Create lookup table with normalized IDs
# The techniques dataset has IDs like "P02", "P03" (no underscore)
# The Additional Posters has IDs like "P_01", "P_02" (with underscore)
# We need to handle both formats

poster_lookup <- additional_posters %>%
  select(
    nr,
    title_poster = Title,
    first_poster = `Name (First)`,
    last_poster = `Name (Last)`
  ) %>%
  mutate(
    # Create normalized ID without underscore for matching
    presentation_id_norm = str_replace(nr, "P_", "P")
  )

cat("✓ Created lookup table with", nrow(poster_lookup), "poster records\n")
cat("  Sample IDs from Additional Posters:",
    paste(head(poster_lookup$nr, 5), collapse = ", "), "\n\n")

# ==============================================================================
# STEP 3: Count rows that need updating
# ==============================================================================

cat("Analyzing rows that need metadata...\n")

rows_with_na <- techniques %>%
  filter(is.na(title) | is.na(presenter_first) | is.na(presenter_last))

cat("Total rows with NA values:", nrow(rows_with_na), "\n")
cat("  - NA title:", sum(is.na(techniques$title)), "\n")
cat("  - NA presenter_first:", sum(is.na(techniques$presenter_first)), "\n")
cat("  - NA presenter_last:", sum(is.na(techniques$presenter_last)), "\n\n")

# Check which have poster-like IDs
poster_pattern_ids <- rows_with_na %>%
  filter(str_detect(presentation_id, "^P\\d{2,}") | str_detect(presentation_id, "^P_\\d{2,}")) %>%
  distinct(presentation_id) %>%
  arrange(presentation_id)

cat("Rows with poster-pattern IDs (P02, P03, etc.):\n")
print(poster_pattern_ids, n = Inf)

# ==============================================================================
# STEP 4: Populate metadata via lookup
# ==============================================================================

cat("\n\nPopulating metadata from Additional Posters tab...\n")

# First, normalize the presentation_id in techniques for matching
techniques_updated <- techniques %>%
  mutate(
    # Create normalized ID for matching (remove underscore if present)
    presentation_id_norm = case_when(
      str_starts(presentation_id, "P_") ~ str_replace(presentation_id, "P_", "P"),
      str_detect(presentation_id, "^P\\d{2,}") ~ presentation_id,
      TRUE ~ NA_character_
    )
  ) %>%
  # Join with poster lookup using both original nr and normalized ID
  left_join(
    poster_lookup,
    by = c("presentation_id_norm"),
    relationship = "many-to-one"
  ) %>%
  # Populate NA fields with values from Additional Posters
  mutate(
    title = if_else(
      is.na(title) & !is.na(title_poster),
      title_poster,
      title
    ),
    presenter_first = if_else(
      is.na(presenter_first) & !is.na(first_poster),
      first_poster,
      presenter_first
    ),
    presenter_last = if_else(
      is.na(presenter_last) & !is.na(last_poster),
      last_poster,
      presenter_last
    )
  ) %>%
  # Remove temporary columns
  select(-presentation_id_norm, -nr, -title_poster, -first_poster, -last_poster)

# ==============================================================================
# STEP 5: Report results
# ==============================================================================

cat("\n=== Results ===\n\n")

# Count how many were filled
titles_filled <- sum(is.na(techniques$title)) - sum(is.na(techniques_updated$title))
first_filled <- sum(is.na(techniques$presenter_first)) - sum(is.na(techniques_updated$presenter_first))
last_filled <- sum(is.na(techniques$presenter_last)) - sum(is.na(techniques_updated$presenter_last))

cat("Metadata populated:\n")
cat("  - Titles filled:", titles_filled, "\n")
cat("  - First names filled:", first_filled, "\n")
cat("  - Last names filled:", last_filled, "\n\n")

# Show remaining NA counts
cat("Remaining NA values:\n")
cat("  - NA title:", sum(is.na(techniques_updated$title)), "\n")
cat("  - NA presenter_first:", sum(is.na(techniques_updated$presenter_first)), "\n")
cat("  - NA presenter_last:", sum(is.na(techniques_updated$presenter_last)), "\n\n")

# Show sample of updated rows
cat("Sample of updated poster rows:\n")
updated_posters <- techniques_updated %>%
  filter(
    str_detect(presentation_id, "^P\\d{2,}") | str_detect(presentation_id, "^P_\\d{2,}")
  ) %>%
  distinct(presentation_id, title, presenter_first, presenter_last) %>%
  arrange(presentation_id) %>%
  head(10)

print(updated_posters, n = 10)

# ==============================================================================
# STEP 6: Save updated data
# ==============================================================================

cat("\n\n=== Saving updated data ===\n")

output_file <- "outputs/techniques_from_titles_abstracts.csv"
write_csv(techniques_updated, output_file)

cat("✓ Saved:", output_file, "\n")
cat("  -", nrow(techniques_updated), "rows\n")
cat("  -", n_distinct(techniques_updated$presentation_id), "unique presentations\n")

cat("\n✓ Metadata population complete\n")
