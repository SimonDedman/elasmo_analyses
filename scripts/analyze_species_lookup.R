#!/usr/bin/env Rscript
# ==============================================================================
# Analyze Species Common Name Lookup Table
# ==============================================================================
#
# Purpose: Analyze species_common_lookup.csv for duplicates, errors, patterns
#
# Expected: ~1,208 unique species (per Weigmann 2016)
#
# ==============================================================================

library(tidyverse)

# ==============================================================================
# Configuration
# ==============================================================================

csv_path <- here::here("data", "species_common_lookup.csv")
output_report <- here::here("data", "species_lookup_analysis_report.txt")

cat("==============================================================================\n")
cat("SPECIES LOOKUP TABLE ANALYSIS\n")
cat("==============================================================================\n\n")

# ==============================================================================
# STEP 1: Load and Basic Stats
# ==============================================================================

cat("Loading CSV...\n")
df <- read_csv(csv_path, show_col_types = FALSE)

cat("Total rows:", nrow(df), "\n")
cat("Columns:", paste(names(df), collapse = ", "), "\n\n")

# ==============================================================================
# STEP 2: Count Unique Species
# ==============================================================================

cat("Unique species count:\n")
unique_species <- df %>%
  distinct(Species) %>%
  arrange(Species)

cat("  Unique species:", nrow(unique_species), "\n")
cat("  Expected (Weigmann 2016):", 1208, "\n")
cat("  Difference:", 1208 - nrow(unique_species), "species missing\n\n")

# ==============================================================================
# STEP 3: Species Name Quality Check
# ==============================================================================

cat("Species name quality checks:\n")

# Check for issues
issues <- df %>%
  distinct(Species) %>%
  mutate(
    has_numbers = str_detect(Species, "\\d"),
    has_special_chars = str_detect(Species, "[^A-Za-z\\s\\-]"),
    too_short = nchar(Species) < 5,
    too_long = nchar(Species) > 50,
    multiple_spaces = str_detect(Species, "\\s{2,}"),
    leading_trailing_space = str_detect(Species, "^\\s|\\s$"),
    mixed_case_issues = str_detect(Species, "[A-Z].*[A-Z]") & !str_detect(Species, "^[A-Z][a-z]+\\s+[a-z]+$")
  )

cat("  Species with numbers:", sum(issues$has_numbers), "\n")
cat("  Species with special characters:", sum(issues$has_special_chars), "\n")
cat("  Species too short (<5 chars):", sum(issues$too_short), "\n")
cat("  Species too long (>50 chars):", sum(issues$too_long), "\n")
cat("  Species with multiple spaces:", sum(issues$multiple_spaces), "\n")
cat("  Species with leading/trailing spaces:", sum(issues$leading_trailing_space), "\n")
cat("  Species with mixed case issues:", sum(issues$mixed_case_issues), "\n\n")

if (sum(issues$has_numbers) > 0) {
  cat("Species with numbers:\n")
  issues %>% filter(has_numbers) %>% pull(Species) %>% head(10) %>% cat(sep = "\n")
  cat("\n\n")
}

# ==============================================================================
# STEP 4: Common Name Quality Check
# ==============================================================================

cat("Common name quality checks:\n")

common_issues <- df %>%
  mutate(
    common_empty = is.na(Common) | Common == "",
    common_too_long = nchar(Common) > 100,
    common_has_typo_indicators = str_detect(Common, "(?i)(unkn|unid|sp\\.|spp\\.|cf\\.|aff\\.)")
  )

cat("  Empty/NA common names:", sum(common_issues$common_empty), "\n")
cat("  Common names too long (>100 chars):", sum(common_issues$common_too_long), "\n")
cat("  Common names with uncertain identifiers:", sum(common_issues$common_has_typo_indicators), "\n\n")

# ==============================================================================
# STEP 5: Detect Potential Duplicates
# ==============================================================================

cat("Analyzing potential duplicate species...\n\n")

# Pattern 1: Exact duplicates (case-insensitive)
duplicates_case <- df %>%
  mutate(Species_lower = str_to_lower(Species)) %>%
  group_by(Species_lower) %>%
  filter(n_distinct(Species) > 1) %>%
  arrange(Species_lower, Species) %>%
  ungroup()

if (nrow(duplicates_case) > 0) {
  cat("Pattern 1: Case-insensitive duplicates:\n")
  cat("  Count:", nrow(duplicates_case), "rows\n")
  cat("  Unique species affected:", n_distinct(duplicates_case$Species), "\n")
  cat("\nExamples:\n")
  duplicates_case %>%
    select(Species) %>%
    distinct() %>%
    head(10) %>%
    print()
  cat("\n")
}

# Pattern 2: Extra/missing spaces
duplicates_space <- df %>%
  mutate(
    Species_normalized = str_squish(Species),  # Remove extra spaces
    Species_nospace = str_replace_all(Species, "\\s+", "")  # Remove all spaces
  ) %>%
  group_by(Species_nospace) %>%
  filter(n_distinct(Species) > 1) %>%
  arrange(Species_nospace, Species) %>%
  ungroup()

if (nrow(duplicates_space) > 0) {
  cat("Pattern 2: Space-related duplicates:\n")
  cat("  Count:", nrow(duplicates_space), "rows\n")
  cat("  Unique species affected:", n_distinct(duplicates_space$Species), "\n")
  cat("\nExamples:\n")
  duplicates_space %>%
    select(Species) %>%
    distinct() %>%
    head(10) %>%
    print()
  cat("\n")
}

# Pattern 3: Hyphen vs no hyphen
duplicates_hyphen <- df %>%
  mutate(
    Species_no_hyphen = str_replace_all(Species, "-", " "),
    Species_with_hyphen = str_replace_all(Species, "\\s+", "-")
  ) %>%
  group_by(Species_no_hyphen) %>%
  filter(n_distinct(Species) > 1) %>%
  arrange(Species_no_hyphen, Species) %>%
  ungroup()

if (nrow(duplicates_hyphen) > 0) {
  cat("Pattern 3: Hyphen-related duplicates:\n")
  cat("  Count:", nrow(duplicates_hyphen), "rows\n")
  cat("  Unique species affected:", n_distinct(duplicates_hyphen$Species), "\n")
  cat("\nExamples:\n")
  duplicates_hyphen %>%
    select(Species) %>%
    distinct() %>%
    head(10) %>%
    print()
  cat("\n")
}

# Pattern 4: Similar strings (Levenshtein distance)
# Find species with very similar names (distance <= 2)
cat("Pattern 4: Similar species names (edit distance <= 2):\n")

species_vec <- unique_species$Species
similar_pairs <- tibble()

for (i in 1:(length(species_vec)-1)) {
  for (j in (i+1):length(species_vec)) {
    dist <- adist(species_vec[i], species_vec[j])[1,1]
    if (dist <= 2 && dist > 0) {
      similar_pairs <- bind_rows(
        similar_pairs,
        tibble(
          Species1 = species_vec[i],
          Species2 = species_vec[j],
          Distance = dist
        )
      )
    }
  }

  # Progress indicator every 100 species
  if (i %% 100 == 0) {
    cat("  Checked", i, "of", length(species_vec), "species...\n")
  }
}

if (nrow(similar_pairs) > 0) {
  cat("\n  Found", nrow(similar_pairs), "similar pairs\n")
  cat("\nExamples (edit distance 1-2):\n")
  similar_pairs %>%
    arrange(Distance) %>%
    head(20) %>%
    print()
  cat("\n")
} else {
  cat("  No similar pairs found (distance <= 2)\n\n")
}

# ==============================================================================
# STEP 6: Common Name Analysis
# ==============================================================================

cat("Common name analysis:\n\n")

# Count common names per species
common_per_species <- df %>%
  group_by(Species) %>%
  summarise(
    common_name_count = n(),
    common_names = paste(Common, collapse = "; ")
  ) %>%
  arrange(desc(common_name_count))

cat("Species with most common names:\n")
common_per_species %>%
  head(10) %>%
  print()
cat("\n")

cat("Common name count distribution:\n")
common_per_species %>%
  count(common_name_count) %>%
  arrange(desc(common_name_count)) %>%
  print()
cat("\n")

# ==============================================================================
# STEP 7: Common Name Typo Detection
# ==============================================================================

cat("Common name typo patterns:\n\n")

# Pattern 1: Spelling variations (e.g., "grey" vs "gray", "whip ray" vs "whipray")
typo_patterns <- df %>%
  mutate(
    Common_normalized = str_to_lower(Common),
    has_grey = str_detect(Common_normalized, "grey"),
    has_gray = str_detect(Common_normalized, "gray"),
    has_whipray = str_detect(Common_normalized, "whipray\\b"),
    has_whip_ray = str_detect(Common_normalized, "whip ray"),
    has_eagleray = str_detect(Common_normalized, "eagleray\\b"),
    has_eagle_ray = str_detect(Common_normalized, "eagle ray"),
    has_duckbill = str_detect(Common_normalized, "duckbill\\b"),
    has_duckbil = str_detect(Common_normalized, "duckbil\\b") & !str_detect(Common_normalized, "duckbill")
  )

cat("Spelling variation patterns:\n")
cat("  'grey' variant:", sum(typo_patterns$has_grey), "\n")
cat("  'gray' variant:", sum(typo_patterns$has_gray), "\n")
cat("  'whipray' (one word):", sum(typo_patterns$has_whipray), "\n")
cat("  'whip ray' (two words):", sum(typo_patterns$has_whip_ray), "\n")
cat("  'eagleray' (one word):", sum(typo_patterns$has_eagleray), "\n")
cat("  'eagle ray' (two words):", sum(typo_patterns$has_eagle_ray), "\n")
cat("  'duckbil' (typo):", sum(typo_patterns$has_duckbil), "\n")
cat("  'duckbill' (correct):", sum(typo_patterns$has_duckbill), "\n\n")

# Find obvious typos (very short common names, missing spaces, etc.)
obvious_typos <- df %>%
  filter(
    str_detect(Common, "(?i)(omn|edgle|grayspottted|lang spotted)") |  # Known typos from preview
    nchar(Common) < 4 |  # Too short
    str_detect(Common, "[a-z][A-Z]")  # Mixed case without space
  )

if (nrow(obvious_typos) > 0) {
  cat("Obvious typos detected:\n")
  obvious_typos %>%
    select(Species, Common) %>%
    distinct() %>%
    arrange(Species) %>%
    head(20) %>%
    print()
  cat("\n")
}

# ==============================================================================
# STEP 8: Generate Cleaning Recommendations
# ==============================================================================

cat("==============================================================================\n")
cat("CLEANING RECOMMENDATIONS\n")
cat("==============================================================================\n\n")

recommendations <- list()

# Recommendation 1: Fix case inconsistencies
if (nrow(duplicates_case) > 0) {
  recommendations <- c(recommendations,
    "1. Standardize species name capitalization (binomial: Genus species)")
}

# Recommendation 2: Fix spacing
if (nrow(duplicates_space) > 0) {
  recommendations <- c(recommendations,
    "2. Remove extra spaces and normalize whitespace")
}

# Recommendation 3: Fix hyphens
if (nrow(duplicates_hyphen) > 0) {
  recommendations <- c(recommendations,
    "3. Standardize hyphen usage (check taxonomic authorities)")
}

# Recommendation 4: Fix typos
if (nrow(obvious_typos) > 0) {
  recommendations <- c(recommendations,
    "4. Fix obvious typos in common names")
}

# Recommendation 5: Standardize spelling variants
recommendations <- c(recommendations,
  "5. Standardize spelling variants:",
  "   - Choose 'gray' OR 'grey' (not both)",
  "   - Choose 'whipray' OR 'whip ray' (not both)",
  "   - Choose 'eagleray' OR 'eagle ray' (not both)")

# Recommendation 6: Validate species count
recommendations <- c(recommendations,
  sprintf("6. Investigate missing species (%d expected, %d found = %d missing)",
          1208, nrow(unique_species), 1208 - nrow(unique_species)))

cat(paste(recommendations, collapse = "\n"))
cat("\n\n")

# ==============================================================================
# STEP 9: Save Report
# ==============================================================================

cat("Saving detailed report to:", output_report, "\n")

sink(output_report)
cat("SPECIES LOOKUP TABLE ANALYSIS REPORT\n")
cat("Generated:", format(Sys.time()), "\n")
cat("==============================================================================\n\n")

cat("SUMMARY STATISTICS\n")
cat("------------------\n")
cat("Total rows:", nrow(df), "\n")
cat("Unique species:", nrow(unique_species), "\n")
cat("Expected species (Weigmann 2016):", 1208, "\n")
cat("Missing species:", 1208 - nrow(unique_species), "\n\n")

cat("QUALITY ISSUES FOUND\n")
cat("--------------------\n")
cat("Case-insensitive duplicates:", nrow(duplicates_case), "rows\n")
cat("Space-related duplicates:", nrow(duplicates_space), "rows\n")
cat("Hyphen-related duplicates:", nrow(duplicates_hyphen), "rows\n")
cat("Similar species names (edit distance <= 2):", nrow(similar_pairs), "pairs\n")
cat("Obvious typos in common names:", nrow(obvious_typos), "\n\n")

cat("CLEANING RECOMMENDATIONS\n")
cat("------------------------\n")
cat(paste(recommendations, collapse = "\n"))
cat("\n\n")

cat("DETAILED LISTS\n")
cat("--------------\n\n")

if (nrow(duplicates_case) > 0) {
  cat("Case-insensitive duplicates:\n")
  print(duplicates_case %>% select(Species, Common) %>% arrange(Species))
  cat("\n\n")
}

if (nrow(similar_pairs) > 0) {
  cat("Similar species pairs:\n")
  print(similar_pairs)
  cat("\n\n")
}

if (nrow(obvious_typos) > 0) {
  cat("Obvious typos:\n")
  print(obvious_typos %>% select(Species, Common) %>% arrange(Species))
  cat("\n\n")
}

sink()

cat("\n==============================================================================\n")
cat("ANALYSIS COMPLETE\n")
cat("==============================================================================\n\n")
cat("Report saved to:", output_report, "\n")
cat("\nNext steps:\n")
cat("1. Review report\n")
cat("2. Create cleaned CSV with corrections\n")
cat("3. Validate against Weigmann 2016 species list\n")

# ==============================================================================
# END OF SCRIPT
# ==============================================================================
