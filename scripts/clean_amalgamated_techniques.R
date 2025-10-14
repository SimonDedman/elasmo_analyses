#!/usr/bin/env Rscript
# ==============================================================================
# Clean Amalgamated Techniques Data
# ==============================================================================
# Tasks:
# 1. Combine "IUCN Assessment" into "IUCN Red List Assessment"
# 2. Combine related technique variants
# 3. Fix incorrect filenames (Cemal Turan) to NA
# 4. Populate presentation_ids via lookup from speakers
# ==============================================================================

library(tidyverse)
library(readxl)

cat("=== Cleaning Amalgamated Techniques Data ===\n\n")

# ==============================================================================
# STEP 1: Load data
# ==============================================================================

cat("Loading data...\n")

techniques <- read_csv(
  "outputs/techniques_from_titles_abstracts.csv",
  show_col_types = FALSE
)

speakers <- read_excel("Final Speakers EEA 2025.xlsx", sheet = 1)

cat("✓ Loaded", nrow(techniques), "technique rows\n")
cat("✓ Loaded", nrow(speakers), "speaker records\n\n")

# ==============================================================================
# STEP 2: Combine technique variants
# ==============================================================================

cat("=== Technique Amalgamations ===\n\n")

# Show current counts before amalgamation
before_counts <- techniques %>% count(technique, discipline, sort = TRUE)

# Define technique mappings
technique_mappings <- tribble(
  ~old_technique, ~new_technique, ~reason,

  # Primary request: IUCN Assessment → IUCN Red List Assessment
  "IUCN Assessment", "IUCN Red List Assessment", "Same concept",

  # Reproduction variants → Reproduction
  "Reproduction (Fecundity)", "Reproduction", "Specific aspect of reproduction",
  "Reproduction (Gestation)", "Reproduction", "Specific aspect of reproduction",

  # Age & Growth variants → Age & Growth
  "Age & Growth (Vertebral Sectioning)", "Age & Growth", "Specific method within age/growth",

  # Random Forest is a type of Machine Learning
  "Random Forest", "Machine Learning", "RF is a ML algorithm",

  # Extinction Risk Assessment is part of IUCN Red List Assessment
  "Extinction Risk Assessment", "IUCN Red List Assessment", "Core component of IUCN RL"
)

cat("Proposed amalgamations:\n")
print(technique_mappings)

# Apply mappings
techniques_clean <- techniques %>%
  left_join(
    technique_mappings %>% select(old_technique, new_technique),
    by = c("technique" = "old_technique")
  ) %>%
  mutate(
    technique = if_else(!is.na(new_technique), new_technique, technique)
  ) %>%
  select(-new_technique)

# Report changes
n_changed <- nrow(techniques) - nrow(techniques_clean %>% distinct())
cat("\n✓ Applied", nrow(technique_mappings), "technique amalgamations\n")

after_counts <- techniques_clean %>% count(technique, discipline, sort = TRUE)

cat("\nTechnique counts after amalgamation:\n")
print(after_counts %>% head(15))

# ==============================================================================
# STEP 3: Fix incorrect filenames
# ==============================================================================

cat("\n\n=== Fixing Incorrect Filenames ===\n\n")

# Count rows with the Cemal Turan filename
cemal_count <- sum(
  !is.na(techniques_clean$filename) &
  str_detect(techniques_clean$filename, "Cemal Turan")
)

cat("Found", cemal_count, "rows with 'Cemal Turan' filename\n")

# Set these filenames to NA
techniques_clean <- techniques_clean %>%
  mutate(
    filename = if_else(
      str_detect(filename, "Cemal Turan"),
      NA_character_,
      filename
    )
  )

cat("✓ Set", cemal_count, "filenames to NA\n")

# ==============================================================================
# STEP 4: Populate presentation_ids via lookup
# ==============================================================================

cat("\n=== Populating Missing Presentation IDs ===\n\n")

# Count NA presentation_ids
na_count_before <- sum(is.na(techniques_clean$presentation_id))
cat("Rows without presentation_id:", na_count_before, "\n")

# Create lookup from speakers: title + presenter -> presentation_id
# Use the existing 'nr' column which contains the actual presentation IDs
speakers_lookup <- speakers %>%
  select(
    presentation_id_lookup = nr,  # Use existing presentation ID
    title_spk = Title,
    first_spk = `Name (First)`,
    last_spk = `Name (Last)`
  ) %>%
  # Normalize for matching
  mutate(
    title_norm = tolower(str_trim(title_spk)),
    first_norm = tolower(str_trim(first_spk)),
    last_norm = tolower(str_trim(last_spk))
  )

# For techniques without presentation_id, try to match
techniques_clean <- techniques_clean %>%
  mutate(
    title_norm = tolower(str_trim(title)),
    first_norm = tolower(str_trim(presenter_first)),
    last_norm = tolower(str_trim(presenter_last))
  ) %>%
  left_join(
    speakers_lookup,
    by = c("title_norm", "first_norm", "last_norm"),
    relationship = "many-to-one"
  ) %>%
  mutate(
    # Fill in presentation_id if it was NA and we found a match
    presentation_id = if_else(
      is.na(presentation_id) & !is.na(presentation_id_lookup),
      presentation_id_lookup,
      presentation_id
    )
  ) %>%
  select(-title_norm, -first_norm, -last_norm,
         -presentation_id_lookup, -title_spk, -first_spk, -last_spk)

na_count_after <- sum(is.na(techniques_clean$presentation_id))
filled <- na_count_before - na_count_after

cat("✓ Filled", filled, "presentation IDs via exact match\n")
cat("Remaining without presentation_id:", na_count_after, "\n")

# Try fuzzy matching for remaining NA presentation_ids
if (na_count_after > 0) {
  cat("\nAttempting fuzzy matching for remaining", na_count_after, "rows...\n")

  # For remaining NAs, try matching on last name only
  techniques_still_na <- techniques_clean %>%
    filter(is.na(presentation_id))

  if (nrow(techniques_still_na) > 0) {
    # Try last name + first letter of first name
    techniques_clean <- techniques_clean %>%
      mutate(
        last_norm = tolower(str_trim(presenter_last)),
        first_initial = tolower(str_sub(presenter_first, 1, 1))
      ) %>%
      left_join(
        speakers_lookup %>%
          mutate(
            last_norm_spk = tolower(str_trim(last_spk)),
            first_initial_spk = tolower(str_sub(first_spk, 1, 1))
          ) %>%
          select(presentation_id_lookup2 = presentation_id_lookup,
                 last_norm_spk, first_initial_spk),
        by = c("last_norm" = "last_norm_spk", "first_initial" = "first_initial_spk"),
        relationship = "many-to-one"
      ) %>%
      mutate(
        presentation_id = if_else(
          is.na(presentation_id) & !is.na(presentation_id_lookup2),
          presentation_id_lookup2,
          presentation_id
        )
      ) %>%
      select(-last_norm, -first_initial, -presentation_id_lookup2)

    na_count_final <- sum(is.na(techniques_clean$presentation_id))
    filled_fuzzy <- na_count_after - na_count_final

    cat("✓ Filled", filled_fuzzy, "additional presentation IDs via fuzzy match\n")
    cat("Final remaining without presentation_id:", na_count_final, "\n")
  }
}

# ==============================================================================
# STEP 5: Remove any duplicates created by amalgamation
# ==============================================================================

cat("\n=== Removing Duplicates After Amalgamation ===\n\n")

before_dedup <- nrow(techniques_clean)

# Remove duplicates: same presentation_id + technique + discipline
techniques_final <- techniques_clean %>%
  filter(!is.na(presentation_id)) %>%
  distinct(presentation_id, technique, discipline, .keep_all = TRUE) %>%
  bind_rows(
    techniques_clean %>% filter(is.na(presentation_id))
  ) %>%
  arrange(presentation_id, discipline, technique)

duplicates_removed <- before_dedup - nrow(techniques_final)

cat("Removed", duplicates_removed, "duplicates created by amalgamation\n")
cat("Final row count:", nrow(techniques_final), "\n")

# ==============================================================================
# STEP 6: Summary statistics
# ==============================================================================

cat("\n=== Final Summary ===\n\n")

cat("Technique counts:\n")
final_counts <- techniques_final %>%
  count(technique, discipline, sort = TRUE) %>%
  head(15)
print(final_counts)

cat("\n\nDiscipline distribution:\n")
discipline_counts <- techniques_final %>%
  count(discipline, sort = TRUE)
print(discipline_counts)

cat("\n\nPresentation ID coverage:\n")
cat("With presentation_id:", sum(!is.na(techniques_final$presentation_id)), "\n")
cat("Without presentation_id:", sum(is.na(techniques_final$presentation_id)), "\n")
cat("Total unique presentation_ids:",
    n_distinct(techniques_final$presentation_id[!is.na(techniques_final$presentation_id)]), "\n")

# ==============================================================================
# STEP 7: Save cleaned data
# ==============================================================================

cat("\n=== Saving Cleaned Data ===\n\n")

output_file <- "outputs/techniques_from_titles_abstracts.csv"
write_csv(techniques_final, output_file)

cat("✓ Saved:", output_file, "\n")
cat("  -", nrow(techniques_final), "rows\n")
cat("  -", n_distinct(techniques_final$technique), "unique techniques\n")
cat("  -", n_distinct(techniques_final$discipline), "unique disciplines\n")

cat("\n✓ Cleaning complete\n")
