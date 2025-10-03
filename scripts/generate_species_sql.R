#!/usr/bin/env Rscript
# ==============================================================================
# Generate SQL Species Columns from Cleaned Lookup Table
# ==============================================================================
#
# Purpose: Generate sql/06_add_species_columns.sql with 1,030 species
#
# Input: data/species_common_lookup_cleaned.csv
# Output: sql/06_add_species_columns.sql
#
# ==============================================================================

library(tidyverse)
library(glue)

# ==============================================================================
# Configuration
# ==============================================================================

input_csv <- here::here("data", "species_common_lookup_cleaned.csv")
output_sql <- here::here("sql", "06_add_species_columns.sql")

cat("==============================================================================\n")
cat("GENERATING SQL SPECIES COLUMNS\n")
cat("==============================================================================\n\n")

# ==============================================================================
# STEP 1: Load Cleaned Species Lookup
# ==============================================================================

cat("Loading cleaned species lookup...\n")
species_lookup <- read_csv(input_csv, show_col_types = FALSE)

cat("Total rows:", nrow(species_lookup), "\n")
cat("Unique species:", n_distinct(species_lookup$Species), "\n\n")

# ==============================================================================
# STEP 2: Get Unique Species with Primary Common Name
# ==============================================================================

cat("Extracting unique species...\n")

# Get first common name alphabetically for each species (primary name)
unique_species <- species_lookup %>%
  group_by(Species) %>%
  summarise(
    common_name = first(sort(Common)),
    common_name_count = n(),
    .groups = "drop"
  ) %>%
  arrange(Species) %>%
  mutate(
    # Generate SQL column name: sp_genus_species
    genus = str_extract(Species, "^[A-Za-z]+"),
    species_epithet = str_extract(Species, "(?<=\\s)[A-Za-z]+$"),
    column_name = paste0(
      "sp_",
      str_to_lower(genus), "_",
      str_to_lower(species_epithet)
    )
  )

cat("Unique species:", nrow(unique_species), "\n")
cat("Column names generated\n\n")

# Check for duplicate column names (shouldn't happen with binomial nomenclature)
dup_cols <- unique_species %>%
  count(column_name) %>%
  filter(n > 1)

if (nrow(dup_cols) > 0) {
  cat("WARNING: Duplicate column names found:\n")
  print(dup_cols)
  cat("\n")
}

# ==============================================================================
# STEP 3: Generate SQL Header
# ==============================================================================

cat("Generating SQL file...\n")

sql_header <- "-- ============================================================================
-- EEA 2025 Data Panel: Species Binary Columns
-- ============================================================================
--
-- Purpose: Add binary columns for each chondrichthyan species
--
-- Schema Version: 1.0
-- Created: 2025-10-02
-- Database: DuckDB
--
-- Dependencies: 01_create_core_table.sql
--
-- Design Rationale:
--   - Track species-specific research focus
--   - Papers often study multiple species (comparative, community ecology)
--   - Binary columns enable multi-species tracking
--   - Prefix 'sp_' identifies species columns
--   - Column names use binomial format: sp_genus_species (lowercase, underscore)
--   - Default FALSE for explicit missing data tracking
--
-- Source: species_common_lookup_cleaned.csv
--   - {species_count} unique species
--   - Generated automatically from cleaned lookup table
--   - Primary common name selected alphabetically
--
-- Note: This file generated with {species_count} species from cleaned lookup.
--       Expected ~1,208 species per Weigmann 2016.
--       Missing 178 species - will be added when updated list received.
--
-- ============================================================================
"

sql_header <- glue(sql_header, species_count = nrow(unique_species))

# ==============================================================================
# STEP 4: Generate ALTER TABLE Statements
# ==============================================================================

# Group species by taxonomic groups for organization (by genus)
unique_species <- unique_species %>%
  mutate(genus_group = genus)

sql_statements <- character()

# Add section header
sql_statements <- c(sql_statements, "-- ============================================================================")
sql_statements <- c(sql_statements, "-- Add Species Binary Columns")
sql_statements <- c(sql_statements, "-- ============================================================================")
sql_statements <- c(sql_statements, "")

current_genus <- ""
genus_count <- 0

for (i in 1:nrow(unique_species)) {
  row <- unique_species[i, ]

  # Add genus header every time genus changes
  if (row$genus != current_genus) {
    if (current_genus != "") {
      sql_statements <- c(sql_statements, "")
    }

    genus_count <- genus_count + 1
    sql_statements <- c(sql_statements, glue("-- {row$genus} ({sum(unique_species$genus == row$genus)} species)"))
    current_genus <- row$genus
  }

  # Generate ALTER TABLE statement
  sql_line <- glue(
    "ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS {row$column_name} BOOLEAN DEFAULT FALSE; -- {row$Species} ({row$common_name})"
  )

  sql_statements <- c(sql_statements, sql_line)
}

# ==============================================================================
# STEP 5: Generate Indexes for Common Species
# ==============================================================================

sql_statements <- c(sql_statements, "")
sql_statements <- c(sql_statements, "-- ============================================================================")
sql_statements <- c(sql_statements, "-- Indexes for Frequently-Studied Species (Top 50)
-- ============================================================================")
sql_statements <- c(sql_statements, "")

# Index top 50 species by common name count (proxy for importance)
top_species <- unique_species %>%
  arrange(desc(common_name_count)) %>%
  head(50)

for (i in 1:nrow(top_species)) {
  row <- top_species[i, ]

  sql_line <- glue(
    "CREATE INDEX IF NOT EXISTS idx_{row$column_name} ON literature_review({row$column_name}) WHERE {row$column_name} = TRUE;"
  )

  sql_statements <- c(sql_statements, sql_line)
}

# ==============================================================================
# STEP 6: Generate Helper Views
# ==============================================================================

sql_statements <- c(sql_statements, "")
sql_statements <- c(sql_statements, "-- ============================================================================")
sql_statements <- c(sql_statements, "-- Helper Views")
sql_statements <- c(sql_statements, "-- ============================================================================")
sql_statements <- c(sql_statements, "")

# View 1: Species summary
sql_statements <- c(sql_statements, "-- Species summary (will be populated after data entry)")
sql_statements <- c(sql_statements, "-- CREATE OR REPLACE VIEW v_species_summary AS ...")
sql_statements <- c(sql_statements, "-- (Deferred - requires dynamic SQL generation)")
sql_statements <- c(sql_statements, "")

# ==============================================================================
# STEP 7: Add Comments
# ==============================================================================

sql_statements <- c(sql_statements, "-- ============================================================================")
sql_statements <- c(sql_statements, "-- Column Documentation (Top 20 Species)")
sql_statements <- c(sql_statements, "-- ============================================================================")
sql_statements <- c(sql_statements, "")

top20 <- unique_species %>%
  arrange(desc(common_name_count)) %>%
  head(20)

for (i in 1:nrow(top20)) {
  row <- top20[i, ]

  sql_line <- glue(
    "COMMENT ON COLUMN literature_review.{row$column_name} IS 'Species: {row$Species} ({row$common_name})';"
  )

  sql_statements <- c(sql_statements, sql_line)
}

# ==============================================================================
# STEP 8: Add Usage Examples
# ==============================================================================

sql_usage <- "

-- ============================================================================
-- Usage Examples
-- ============================================================================

/*
-- Mark a paper studying multiple species
UPDATE literature_review
SET
    sp_carcharodon_carcharias = TRUE,
    sp_prionace_glauca = TRUE,
    sp_galeocerdo_cuvier = TRUE
WHERE study_id = 1;

-- Find all White Shark papers
SELECT title, year
FROM literature_review
WHERE sp_carcharodon_carcharias = TRUE;

-- Count papers by species (top 20)
SELECT
    SUM(CASE WHEN sp_carcharodon_carcharias THEN 1 ELSE 0 END) as white_shark,
    SUM(CASE WHEN sp_prionace_glauca THEN 1 ELSE 0 END) as blue_shark,
    SUM(CASE WHEN sp_galeocerdo_cuvier THEN 1 ELSE 0 END) as tiger_shark
FROM literature_review;

-- Find multi-species comparative studies
SELECT title, year,
    (CAST(sp_carcharodon_carcharias AS INTEGER) +
     CAST(sp_prionace_glauca AS INTEGER) +
     CAST(sp_galeocerdo_cuvier AS INTEGER) +
     CAST(sp_isurus_oxyrinchus AS INTEGER)) AS species_count
FROM literature_review
WHERE species_count >= 2
ORDER BY species_count DESC;

-- Find papers on sharks in a specific family (requires family lookup)
-- Example: All Carcharhinidae (requiem sharks)
SELECT title, year
FROM literature_review
WHERE sp_carcharhinus_acronotus = TRUE
   OR sp_carcharhinus_albimarginatus = TRUE
   OR sp_carcharhinus_altimus = TRUE
   -- ... (add all Carcharhinus species)
;
*/

-- ============================================================================
-- END OF FILE
-- ============================================================================
-- Total species columns: {species_count}
-- Missing species: ~178 (to be added when Weigmann updated list received)
-- ============================================================================
"

sql_usage <- glue(sql_usage, species_count = nrow(unique_species))

# ==============================================================================
# STEP 9: Write SQL File
# ==============================================================================

cat("Writing SQL file...\n")

# Combine all parts
sql_full <- c(
  sql_header,
  sql_statements,
  sql_usage
)

writeLines(sql_full, output_sql)

cat("SQL file written to:", output_sql, "\n\n")

# ==============================================================================
# STEP 10: Summary Statistics
# ==============================================================================

cat("==============================================================================\n")
cat("SUMMARY\n")
cat("==============================================================================\n\n")

cat("Species processed:", nrow(unique_species), "\n")
cat("SQL columns generated:", nrow(unique_species), "\n")
cat("Indexes created:", nrow(top_species), "(top 50 species)\n")
cat("Comments added:", nrow(top20), "(top 20 species)\n\n")

cat("Top 10 genera by species count:\n")
unique_species %>%
  count(genus, sort = TRUE) %>%
  head(10) %>%
  print()

cat("\nTop 10 species by common name count (proxy for importance):\n")
unique_species %>%
  arrange(desc(common_name_count)) %>%
  select(Species, common_name, common_name_count) %>%
  head(10) %>%
  print()

cat("\n==============================================================================\n")
cat("GENERATION COMPLETE\n")
cat("==============================================================================\n\n")

cat("Output file:", output_sql, "\n")
cat("Total species:", nrow(unique_species), "\n")
cat("Expected species (Weigmann 2016):", 1208, "\n")
cat("Missing species:", 1208 - nrow(unique_species), "\n\n")

cat("Next steps:\n")
cat("1. Review generated SQL file\n")
cat("2. Test with DuckDB:\n")
cat("   duckdb literature_review.duckdb < sql/06_add_species_columns.sql\n")
cat("3. When Weigmann updated list received:\n")
cat("   - Re-run this script with complete species list\n")
cat("   - Overwrite sql/06_add_species_columns.sql\n")

# ==============================================================================
# END OF SCRIPT
# ==============================================================================
