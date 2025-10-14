#!/usr/bin/env Rscript
# ==============================================================================
# Amalgamate Techniques from Titles and Abstracts
# ==============================================================================
# Purpose: Combine techniques extracted from titles and abstracts,
#          removing duplicates where the same presentation has the same
#          technique extracted from both sources.
# Output: techniques_from_titles_abstracts.csv with fields:
#         presentation_id, filename, title, presenter_first, presenter_last,
#         pattern, technique, discipline
# ==============================================================================

library(tidyverse)
library(readxl)

cat("=== Amalgamating Techniques from Titles and Abstracts ===\n\n")

# ==============================================================================
# STEP 1: Load the data sources
# ==============================================================================

cat("Loading data sources...\n")

# Load presentation metadata from Excel
speakers <- read_excel("Final Speakers EEA 2025.xlsx", sheet = 1)

# Load techniques from titles
techniques_titles <- read_csv(
  "outputs/techniques_from_titles.csv",
  show_col_types = FALSE
)

# Load techniques from abstracts
techniques_abstracts <- read_csv(
  "outputs/techniques_from_abstracts_structured.csv",
  show_col_types = FALSE
)

cat("✓ Loaded", nrow(speakers), "presentations\n")
cat("✓ Loaded", nrow(techniques_titles), "techniques from titles\n")
cat("✓ Loaded", nrow(techniques_abstracts), "techniques from abstracts\n\n")

# ==============================================================================
# STEP 2: Create master lookup from abstracts (already have presentation_id)
# ==============================================================================

cat("Creating presentation ID lookup...\n")

# Abstracts already have presentation_id in filename, extract metadata
abstracts_meta <- techniques_abstracts %>%
  select(presentation_id, filename) %>%
  distinct() %>%
  # Join with speakers to get full metadata
  left_join(
    speakers %>%
      select(
        title = Title,
        presenter_first = `Name (First)`,
        presenter_last = `Name (Last)`,
        format
      ),
    by = character()  # Will manually match below
  )

# Better approach: use the abstracts presentation_id as the authoritative source
# and match titles to it via presenter name + title
abstracts_with_presenter <- techniques_abstracts %>%
  # For each unique presentation_id, we need to find the matching speaker
  left_join(
    speakers %>%
      mutate(
        # Create a lookup key from first and last name
        name_match = tolower(paste(`Name (First)`, `Name (Last)`))
      ) %>%
      select(
        title = Title,
        presenter_first_spk = `Name (First)`,
        presenter_last_spk = `Name (Last)`,
        name_match
      ),
    by = character(),
    relationship = "many-to-many"
  ) %>%
  # Match based on filename containing last name
  mutate(
    filename_lower = tolower(filename),
    name_in_file = str_detect(filename_lower, tolower(presenter_last_spk))
  ) %>%
  # Keep matches, but also keep unmatched abstracts
  group_by(presentation_id, filename, pattern, technique, discipline) %>%
  arrange(desc(name_in_file)) %>%  # Prioritize matches
  slice(1) %>%
  ungroup() %>%
  mutate(
    title = if_else(name_in_file, title, NA_character_),
    presenter_first = if_else(name_in_file, presenter_first_spk, NA_character_),
    presenter_last = if_else(name_in_file, presenter_last_spk, NA_character_)
  ) %>%
  select(
    presentation_id,
    filename,
    title,
    presenter_first,
    presenter_last,
    pattern,
    technique,
    discipline
  ) %>%
  mutate(source = "abstract")

cat("✓ Processed", n_distinct(abstracts_with_presenter$presentation_id),
    "unique presentation IDs from abstracts\n")
cat("  -", sum(!is.na(abstracts_with_presenter$title)), "matched to speaker metadata\n")
cat("  -", sum(is.na(abstracts_with_presenter$title)), "without speaker match (kept anyway)\n")

# ==============================================================================
# STEP 3: Match titles to presentation_id via presenter + title
# ==============================================================================

cat("Matching title-based techniques to presentations...\n")

# Create a lookup: presenter + title -> presentation_id
presentation_lookup <- abstracts_with_presenter %>%
  select(presentation_id, title, presenter_first, presenter_last) %>%
  distinct()

# Match titles to this lookup
titles_with_id <- techniques_titles %>%
  left_join(
    presentation_lookup,
    by = c("title", "presenter_first", "presenter_last")
  ) %>%
  # Get filename from abstracts for matched presentations
  left_join(
    abstracts_with_presenter %>%
      select(presentation_id, filename) %>%
      distinct(),
    by = "presentation_id"
  ) %>%
  mutate(
    pattern = NA_character_,  # No pattern for title-based extraction
    source = "title"
  ) %>%
  select(
    presentation_id,
    filename,
    title,
    presenter_first,
    presenter_last,
    pattern,
    technique,
    discipline,
    source
  )

cat("✓ Matched", sum(!is.na(titles_with_id$presentation_id)), "of",
    nrow(titles_with_id), "title techniques to presentation IDs\n\n")

# ==============================================================================
# STEP 4: Combine and remove duplicates
# ==============================================================================

cat("Combining datasets and removing duplicates...\n")

# Combine both sources
combined <- bind_rows(
  titles_with_id,
  abstracts_with_presenter
)

cat("Combined total:", nrow(combined), "technique extractions\n")

# Separate into matched and unmatched
matched <- combined %>%
  filter(!is.na(presentation_id))

unmatched <- combined %>%
  filter(is.na(presentation_id))

cat("  -", nrow(matched), "with valid presentation_id (can check for duplicates)\n")
cat("  -", nrow(unmatched), "without presentation_id (kept as-is)\n")

# Remove duplicates ONLY from matched presentations
# Only remove when same presentation_id AND same technique
deduplicated_matched <- matched %>%
  # Normalize technique names for better matching
  mutate(
    technique_clean = str_trim(technique),
    discipline_clean = str_trim(discipline)
  ) %>%
  # Group by presentation and technique
  group_by(presentation_id, technique_clean, discipline_clean) %>%
  # Keep first occurrence (titles come first in bind_rows)
  slice(1) %>%
  ungroup() %>%
  # Restore original names
  select(-technique_clean, -discipline_clean)

n_removed <- nrow(matched) - nrow(deduplicated_matched)
cat("Removed", n_removed, "duplicates from matched presentations\n")

# Recombine: deduplicated matched + all unmatched
deduplicated <- bind_rows(
  deduplicated_matched,
  unmatched
) %>%
  # Sort for consistent output
  arrange(presentation_id, discipline, technique)

cat("Final dataset:", nrow(deduplicated), "unique technique extractions\n")
cat("  -", nrow(deduplicated_matched), "from matched presentations\n")
cat("  -", nrow(unmatched), "from unmatched presentations (kept all)\n\n")

# ==============================================================================
# STEP 5: Create final output without 'source' column
# ==============================================================================

cat("Creating final output...\n")

final_output <- deduplicated %>%
  select(
    presentation_id,
    filename,
    title,
    presenter_first,
    presenter_last,
    pattern,
    technique,
    discipline
  )

# ==============================================================================
# STEP 6: Generate summary statistics
# ==============================================================================

cat("\n=== Summary Statistics ===\n\n")

# Techniques per presentation
tech_per_prez <- final_output %>%
  count(presentation_id, name = "n_techniques") %>%
  summarise(
    min = min(n_techniques),
    median = median(n_techniques),
    mean = round(mean(n_techniques), 1),
    max = max(n_techniques),
    total_presentations = n()
  )

cat("Techniques per presentation:\n")
print(tech_per_prez)

# Techniques per discipline
tech_per_disc <- final_output %>%
  count(discipline, sort = TRUE)

cat("\n\nTechniques by discipline:\n")
print(tech_per_disc)

# Most common techniques overall
top_techniques <- final_output %>%
  count(technique, discipline, sort = TRUE) %>%
  head(10)

cat("\n\nTop 10 most common techniques:\n")
print(top_techniques)

# Source contribution (from the deduplicated data with source)
source_stats <- deduplicated %>%
  count(source) %>%
  mutate(percentage = round(100 * n / sum(n), 1))

cat("\n\nContribution by source:\n")
print(source_stats)

# Overlap analysis (techniques found in both)
overlap <- combined %>%
  filter(!is.na(presentation_id)) %>%
  group_by(presentation_id, technique) %>%
  summarise(
    n_sources = n_distinct(source),
    sources = paste(sort(unique(source)), collapse = " + "),
    .groups = "drop"
  ) %>%
  count(sources, name = "n_techniques")

cat("\n\nTechnique overlap between sources:\n")
print(overlap)

# ==============================================================================
# STEP 7: Save output
# ==============================================================================

cat("\n=== Saving output ===\n")

output_file <- "outputs/techniques_from_titles_abstracts.csv"
write_csv(final_output, output_file)

cat("✓ Saved:", output_file, "\n")
cat("  -", nrow(final_output), "rows\n")
cat("  -", n_distinct(final_output$presentation_id), "unique presentations\n")
cat("  -", n_distinct(final_output$technique), "unique techniques\n")
cat("  -", n_distinct(final_output$discipline), "unique disciplines\n")

cat("\n✓ Amalgamation complete\n")
