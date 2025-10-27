#!/usr/bin/env Rscript
# ============================================================================
# GENERATE PANEL REPORTS
# ============================================================================
# Purpose: Create comprehensive MD reports for expert panel review
#          Including technique analysis, trends, and discussion prompts
#
# Author: EEA 2025 Data Panel
# Date: 2025-10-26
# ============================================================================

library(tidyverse)
library(scales)

cat("\n")
cat(paste0(strrep("=", 80), "\n"))
cat("GENERATING PANEL REPORTS\n")
cat(paste0(strrep("=", 80), "\n\n"))

# ============================================================================
# LOAD DATA
# ============================================================================

cat("=== LOADING DATA ===\n")

# Load technique counts
technique_counts <- read_csv(
  "outputs/analysis/technique_counts_per_discipline.csv",
  show_col_types = FALSE
)

# Load all discipline summaries
disciplines <- c("BEH", "BIO", "CON", "DATA", "FISH", "GEN", "MOV", "TRO")

discipline_data <- list()
for (disc in disciplines) {
  file_path <- sprintf("outputs/analysis/technique_summary_%s.txt", disc)
  if (file.exists(file_path)) {
    discipline_data[[disc]] <- read_lines(file_path)
  }
}

cat(sprintf("Loaded %d techniques across %d disciplines\n",
           nrow(technique_counts), length(disciplines)))

# ============================================================================
# ANALYZE CROSS-DISCIPLINE PATTERNS
# ============================================================================

cat("\n=== ANALYZING CROSS-DISCIPLINE PATTERNS ===\n")

# Reshape to wide format for cross-discipline analysis
technique_wide <- technique_counts %>%
  pivot_wider(
    names_from = disciplines,
    values_from = count,
    values_fill = 0
  )

# Identify techniques used in multiple disciplines
technique_wide <- technique_wide %>%
  mutate(
    n_disciplines = rowSums(select(., all_of(disciplines)) > 0),
    total_usage = rowSums(select(., all_of(disciplines)))
  )

# Cross-discipline techniques (used in 2+ disciplines)
cross_discipline <- technique_wide %>%
  filter(n_disciplines >= 2) %>%
  arrange(desc(n_disciplines), desc(total_usage))

cat(sprintf("Techniques used in multiple disciplines: %d\n", nrow(cross_discipline)))
cat(sprintf("  Used in 2 disciplines: %d\n", sum(cross_discipline$n_disciplines == 2)))
cat(sprintf("  Used in 3+ disciplines: %d\n", sum(cross_discipline$n_disciplines >= 3)))
cat(sprintf("  Used in 5+ disciplines: %d\n", sum(cross_discipline$n_disciplines >= 5)))

# Identify DATA discipline techniques and their adoption in other fields
data_techniques <- technique_wide %>%
  filter(DATA > 0) %>%
  arrange(desc(n_disciplines))

cat(sprintf("\nDATA discipline techniques: %d\n", nrow(data_techniques)))
cat(sprintf("  Also used in other disciplines: %d\n", sum(data_techniques$n_disciplines > 1)))

# ============================================================================
# GENERATE CROSS-DISCIPLINE INSIGHTS
# ============================================================================

cat("\n=== GENERATING CROSS-DISCIPLINE INSIGHTS ===\n")

# Save cross-discipline analysis
write_csv(
  cross_discipline,
  "outputs/analysis/cross_discipline_techniques.csv"
)

write_csv(
  data_techniques,
  "outputs/analysis/data_discipline_adoption.csv"
)

cat("✓ Saved: cross_discipline_techniques.csv\n")
cat("✓ Saved: data_discipline_adoption.csv\n")

# ============================================================================
# IDENTIFY EMERGING/NEW TECHNIQUES
# ============================================================================

# Identify techniques with low usage (candidates for expert curation)
low_usage <- technique_wide %>%
  filter(total_usage <= 5, total_usage > 0) %>%
  arrange(desc(n_disciplines))

# Identify single-discipline specialists
specialists <- technique_wide %>%
  filter(n_disciplines == 1, total_usage >= 10) %>%
  arrange(desc(total_usage))

write_csv(low_usage, "outputs/analysis/low_usage_techniques.csv")
write_csv(specialists, "outputs/analysis/specialist_techniques.csv")

cat(sprintf("\nLow usage techniques (≤5 papers): %d\n", nrow(low_usage)))
cat(sprintf("Specialist techniques (1 discipline, ≥10 papers): %d\n", nrow(specialists)))

cat("\n✓ Analysis complete\n")

# ============================================================================
# SUMMARY STATISTICS
# ============================================================================

cat("\n")
cat(paste0(strrep("=", 80), "\n"))
cat("ANALYSIS SUMMARY\n")
cat(paste0(strrep("=", 80), "\n\n"))

cat("OUTPUTS CREATED:\n")
cat("  1. cross_discipline_techniques.csv - Techniques used in 2+ disciplines\n")
cat("  2. data_discipline_adoption.csv - DATA techniques and adoption\n")
cat("  3. low_usage_techniques.csv - Emerging/rare techniques\n")
cat("  4. specialist_techniques.csv - Single-discipline specialists\n")

cat("\nKEY STATISTICS:\n")
cat(sprintf("  Total techniques: %d\n", nrow(technique_wide)))
cat(sprintf("  Cross-discipline techniques: %d (%.1f%%)\n",
           nrow(cross_discipline),
           nrow(cross_discipline)/nrow(technique_wide)*100))
cat(sprintf("  DATA discipline techniques: %d\n", nrow(data_techniques)))
cat(sprintf("  Low usage candidates: %d\n", nrow(low_usage)))

cat("\n")
cat(paste0(strrep("=", 80), "\n"))
