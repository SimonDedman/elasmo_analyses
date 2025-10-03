#!/usr/bin/env Rscript
# ==============================================================================
# Clean Species Common Name Lookup Table
# ==============================================================================
#
# Purpose: Fix typos and standardize spelling in species_common_lookup.csv
#
# ==============================================================================

library(tidyverse)

# ==============================================================================
# Configuration
# ==============================================================================

input_csv <- here::here("data", "species_common_lookup.csv")
output_csv <- here::here("data", "species_common_lookup_cleaned.csv")

cat("==============================================================================\n")
cat("CLEANING SPECIES LOOKUP TABLE\n")
cat("==============================================================================\n\n")

# ==============================================================================
# STEP 1: Load Data
# ==============================================================================

cat("Loading data...\n")
df <- read_csv(input_csv, show_col_types = FALSE)

cat("Original data:", nrow(df), "rows,", n_distinct(df$Species), "unique species\n\n")

# ==============================================================================
# STEP 2: Fix Obvious Typos
# ==============================================================================

cat("Fixing obvious typos in common names...\n")

df_cleaned <- df %>%
  mutate(
    Common = case_when(
      # Fix known typos identified in analysis
      Common == "Grayspottted guitarfish" ~ "Grayspotted guitarfish",
      Common == "Omn guitarfish" ~ "Oman guitarfish",
      Common == "Lang spotted eagle ray" ~ "Long spotted eagle ray",
      Common == "Spotted edgle-ray" ~ "Spotted eagle-ray",
      Common == "Duckbil ray" ~ "Duckbill ray",

      # Keep as-is (these may be intentional)
      # "McCain's skate", "McMillan's cat shark", "Rog", "Rig"

      # Default: keep original
      TRUE ~ Common
    )
  )

cat("  Fixed 5 obvious typos\n\n")

# ==============================================================================
# STEP 3: Standardize Spelling Variants
# ==============================================================================

cat("Standardizing spelling variants...\n")

df_cleaned <- df_cleaned %>%
  mutate(
    Common = Common %>%
      # Standardize gray/grey to "gray" (American English, more common in dataset)
      str_replace_all("([Gg])rey", "\\1ray") %>%

      # Standardize to "whipray" (one word, more common in dataset)
      str_replace_all("whip ray", "whipray") %>%
      str_replace_all("Whip ray", "Whipray") %>%

      # Standardize to "eagle ray" (two words, more common in dataset)
      str_replace_all("eagleray", "eagle ray") %>%
      str_replace_all("Eagleray", "Eagle ray")
  )

cat("  Standardized 'grey' → 'gray'\n")
cat("  Standardized 'whip ray' → 'whipray'\n")
cat("  Standardized 'eagleray' → 'eagle ray'\n\n")

# ==============================================================================
# STEP 4: Remove Duplicates (if any)
# ==============================================================================

cat("Checking for duplicates...\n")

duplicates <- df_cleaned %>%
  group_by(Species, Common) %>%
  filter(n() > 1) %>%
  ungroup()

if (nrow(duplicates) > 0) {
  cat("  Found", nrow(duplicates), "duplicate rows\n")
  cat("  Removing duplicates...\n")

  df_cleaned <- df_cleaned %>%
    distinct(Species, Common, .keep_all = TRUE)

  cat("  Duplicates removed\n\n")
} else {
  cat("  No duplicates found\n\n")
}

# ==============================================================================
# STEP 5: Sort and Save
# ==============================================================================

cat("Sorting and saving...\n")

df_cleaned <- df_cleaned %>%
  arrange(Species, Common)

write_csv(df_cleaned, output_csv)

cat("Saved to:", output_csv, "\n\n")

# ==============================================================================
# STEP 6: Summary
# ==============================================================================

cat("==============================================================================\n")
cat("SUMMARY\n")
cat("==============================================================================\n\n")

cat("Original data:\n")
cat("  Rows:", nrow(df), "\n")
cat("  Unique species:", n_distinct(df$Species), "\n")
cat("  Unique common names:", n_distinct(df$Common), "\n\n")

cat("Cleaned data:\n")
cat("  Rows:", nrow(df_cleaned), "\n")
cat("  Unique species:", n_distinct(df_cleaned$Species), "\n")
cat("  Unique common names:", n_distinct(df_cleaned$Common), "\n\n")

cat("Changes:\n")
cat("  Rows removed:", nrow(df) - nrow(df_cleaned), "\n")
cat("  Common names affected:", n_distinct(df$Common) - n_distinct(df_cleaned$Common), "\n\n")

# Top species by common name count
cat("Top 10 species by common name count:\n")
df_cleaned %>%
  count(Species, sort = TRUE) %>%
  head(10) %>%
  print()

cat("\n==============================================================================\n")
cat("CLEANING COMPLETE\n")
cat("==============================================================================\n\n")

cat("Next steps:\n")
cat("1. Review cleaned CSV\n")
cat("2. Investigate 178 missing species (expected 1,208, have", n_distinct(df_cleaned$Species), ")\n")
cat("3. Consider merging with Weigmann 2016 list when received\n")

# ==============================================================================
# END OF SCRIPT
# ==============================================================================
