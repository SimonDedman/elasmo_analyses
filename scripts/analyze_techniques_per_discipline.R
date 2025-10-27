#!/usr/bin/env Rscript
# ============================================================================
# TECHNIQUE ANALYSIS PER DISCIPLINE
# ============================================================================
# Purpose: Comprehensive analysis of techniques within each discipline
# Uses existing CSV exports from previous analysis
#
# Outputs:
#   1a) Technique breakdown per discipline
#   1b) Technique breakdown per discipline per year
#   1c) Emerging/new/declining technique analysis
#   1d) Reference lists for emerging techniques
#
# Author: EEA 2025 Data Panel
# Date: 2025-10-26
# ============================================================================

library(tidyverse)
library(scales)

# ============================================================================
# LOAD DATA
# ============================================================================

cat("\n=== LOADING EXISTING DATA ===\n")

# Load technique trends by year (already has discipline and year breakdowns)
technique_trends <- read_csv(
  "outputs/analysis/technique_trends_by_year.csv",
  show_col_types = FALSE
)

cat(sprintf("Loaded %s technique-year records\n", comma(nrow(technique_trends))))
cat(sprintf("Unique techniques: %d\n", n_distinct(technique_trends$technique_name)))
cat(sprintf("Disciplines: %s\n", paste(unique(technique_trends$primary_discipline), collapse = ", ")))
cat(sprintf("Year range: %d - %d\n",
            min(technique_trends$year), max(technique_trends$year)))

# Discipline names mapping
discipline_names <- tribble(
  ~discipline_code, ~full_name,
  "BEH", "Behaviour",
  "BIO", "Biology",
  "CON", "Conservation",
  "DATA", "Data Science",
  "FISH", "Fisheries",
  "GEN", "Genetics",
  "MOV", "Movement",
  "TRO", "Trophic Ecology"
)

# ============================================================================
# 1a) TECHNIQUE BREAKDOWN PER DISCIPLINE
# ============================================================================

cat("\n=== 1a) GENERATING TECHNIQUE BREAKDOWN PER DISCIPLINE ===\n")

technique_counts_by_discipline <- technique_trends %>%
  group_by(primary_discipline, technique_name) %>%
  summarise(
    paper_count = sum(paper_count),
    total_mentions = sum(total_mentions),
    years_active = n_distinct(year),
    first_year = min(year),
    last_year = max(year),
    .groups = "drop"
  ) %>%
  arrange(primary_discipline, desc(paper_count))

# Add discipline full names
technique_counts_by_discipline <- technique_counts_by_discipline %>%
  left_join(discipline_names, by = c("primary_discipline" = "discipline_code"))

# Summary statistics per discipline
discipline_summary <- technique_counts_by_discipline %>%
  group_by(primary_discipline, full_name) %>%
  summarise(
    total_techniques = n(),
    total_papers = sum(paper_count),
    avg_papers_per_technique = mean(paper_count),
    median_papers_per_technique = median(paper_count),
    top_technique = technique_name[which.max(paper_count)],
    top_technique_count = max(paper_count),
    .groups = "drop"
  ) %>%
  arrange(desc(total_papers))

# Save outputs
write_csv(
  technique_counts_by_discipline,
  "outputs/analysis/techniques_per_discipline.csv"
)

write_csv(
  discipline_summary,
  "outputs/analysis/discipline_technique_summary.csv"
)

cat("\n✓ Saved: techniques_per_discipline.csv\n")
cat("✓ Saved: discipline_technique_summary.csv\n")

# Print summary
cat("\n--- DISCIPLINE TECHNIQUE SUMMARY ---\n")
print(discipline_summary, n = Inf)

# ============================================================================
# 1b) TECHNIQUE BREAKDOWN PER DISCIPLINE PER YEAR
# ============================================================================

cat("\n=== 1b) TECHNIQUE BREAKDOWN BY YEAR (Already Exists) ===\n")

# The source data already has this - just add full names and save
technique_counts_by_year <- technique_trends %>%
  left_join(discipline_names, by = c("primary_discipline" = "discipline_code")) %>%
  select(primary_discipline, full_name, technique_name, year, paper_count, total_mentions) %>%
  arrange(primary_discipline, technique_name, year)

write_csv(
  technique_counts_by_year,
  "outputs/analysis/techniques_per_discipline_per_year.csv"
)

cat("✓ Saved: techniques_per_discipline_per_year.csv\n")
cat(sprintf("Time series data: %s records\n", comma(nrow(technique_counts_by_year))))

# ============================================================================
# 1c) EMERGING, NEW, AND DECLINING TECHNIQUES
# ============================================================================

cat("\n=== 1c) ANALYZING TECHNIQUE TRENDS ===\n")

current_year <- max(technique_trends$year)
cat(sprintf("Analysis reference year: %d\n", current_year))

# Calculate trends for each technique
technique_analysis <- technique_counts_by_discipline %>%
  select(primary_discipline, technique_name, paper_count, first_year, last_year, years_active)

# Get recent activity (last 5 years)
recent_activity <- technique_trends %>%
  filter(year >= current_year - 5) %>%
  group_by(primary_discipline, technique_name) %>%
  summarise(
    recent_papers = sum(paper_count),
    recent_years = n_distinct(year),
    .groups = "drop"
  )

# Get historical activity (more than 5 years ago)
historical_activity <- technique_trends %>%
  filter(year < current_year - 5) %>%
  group_by(primary_discipline, technique_name) %>%
  summarise(
    historical_papers = sum(paper_count),
    historical_years = n_distinct(year),
    .groups = "drop"
  )

# Combine for trend analysis
trend_analysis <- technique_analysis %>%
  left_join(recent_activity, by = c("primary_discipline", "technique_name")) %>%
  left_join(historical_activity, by = c("primary_discipline", "technique_name")) %>%
  replace_na(list(
    recent_papers = 0,
    recent_years = 0,
    historical_papers = 0,
    historical_years = 0
  )) %>%
  mutate(
    # Calculate averages
    recent_avg_per_year = ifelse(recent_years > 0, recent_papers / recent_years, 0),
    historical_avg_per_year = ifelse(historical_years > 0, historical_papers / historical_years, 0),

    # Growth ratio
    growth_ratio = ifelse(historical_avg_per_year > 0,
                         recent_avg_per_year / historical_avg_per_year,
                         ifelse(recent_avg_per_year > 0, 999, 0)),

    # Classify techniques
    classification = case_when(
      # New techniques (appeared in last 1-2 years)
      first_year >= current_year - 2 ~ "NEW",

      # Emerging techniques (significant growth in last 5 years)
      recent_papers >= 5 & growth_ratio > 2 ~ "EMERGING",

      # Declining techniques (were popular but less so recently)
      historical_papers > 10 & last_year < current_year - 2 &
        growth_ratio < 0.5 ~ "DECLINING",

      # Stable techniques
      paper_count >= 5 ~ "STABLE",

      # Rare techniques
      TRUE ~ "RARE"
    )
  )

# Add discipline names
trend_analysis <- trend_analysis %>%
  left_join(discipline_names, by = c("primary_discipline" = "discipline_code"))

# Save full analysis
write_csv(
  trend_analysis,
  "outputs/analysis/technique_trends_analysis.csv"
)

cat("✓ Saved: technique_trends_analysis.csv\n")

# Create summary by discipline and classification
trend_summary <- trend_analysis %>%
  group_by(primary_discipline, full_name, classification) %>%
  summarise(
    technique_count = n(),
    total_papers = sum(paper_count),
    .groups = "drop"
  ) %>%
  arrange(primary_discipline, classification)

write_csv(
  trend_summary,
  "outputs/analysis/technique_trends_summary.csv"
)

cat("✓ Saved: technique_trends_summary.csv\n")

# Print classification summary
cat("\n--- TECHNIQUE CLASSIFICATION SUMMARY ---\n")
classification_counts <- trend_analysis %>%
  count(classification) %>%
  arrange(desc(n))
print(classification_counts)

cat("\n--- TRENDS BY DISCIPLINE ---\n")
print(trend_summary, n = 50)

# ============================================================================
# 1d) REFERENCE LISTS FOR EMERGING TECHNIQUES
# ============================================================================

cat("\n=== 1d) CREATING REFERENCE LISTS ===\n")

# Get emerging and new techniques
emerging_new <- trend_analysis %>%
  filter(classification %in% c("EMERGING", "NEW")) %>%
  arrange(primary_discipline, desc(recent_papers))

cat(sprintf("\nIdentified %d emerging/new techniques:\n", nrow(emerging_new)))
cat(sprintf("  NEW: %d\n", sum(emerging_new$classification == "NEW")))
cat(sprintf("  EMERGING: %d\n", sum(emerging_new$classification == "EMERGING")))

# Create summary lists by discipline
for (disc_code in unique(emerging_new$primary_discipline)) {
  disc_name <- discipline_names$full_name[discipline_names$discipline_code == disc_code]

  disc_techs <- emerging_new %>%
    filter(primary_discipline == disc_code) %>%
    select(technique_name, classification, recent_papers, paper_count, first_year, last_year)

  if (nrow(disc_techs) > 0) {
    filename <- sprintf("outputs/analysis/emerging_techniques_%s.csv", disc_code)
    write_csv(disc_techs, filename)

    # Also create formatted text output
    txt_filename <- sprintf("outputs/analysis/emerging_techniques_%s.txt", disc_code)
    sink(txt_filename)
    cat(paste0(strrep("=", 80), "\n"))
    cat(sprintf("%s - EMERGING & NEW TECHNIQUES\n", disc_name))
    cat(paste0(strrep("=", 80), "\n\n"))

    cat(sprintf("Total: %d techniques\n", nrow(disc_techs)))
    cat(sprintf("  NEW (first appeared %d-%d): %d\n",
               current_year - 2, current_year,
               sum(disc_techs$classification == "NEW")))
    cat(sprintf("  EMERGING (rapid growth last 5 years): %d\n\n",
               sum(disc_techs$classification == "EMERGING")))

    # New techniques
    new_techs <- disc_techs %>% filter(classification == "NEW")
    if (nrow(new_techs) > 0) {
      cat("\n## NEW TECHNIQUES ##\n\n")
      for (i in 1:nrow(new_techs)) {
        cat(sprintf("%d. %s\n", i, new_techs$technique_name[i]))
        cat(sprintf("   First appeared: %d\n", new_techs$first_year[i]))
        cat(sprintf("   Papers (last 5 years): %d\n", new_techs$recent_papers[i]))
        cat(sprintf("   Total papers: %d\n\n", new_techs$paper_count[i]))
      }
    }

    # Emerging techniques
    emerging_techs <- disc_techs %>% filter(classification == "EMERGING")
    if (nrow(emerging_techs) > 0) {
      cat("\n## EMERGING TECHNIQUES ##\n\n")
      for (i in 1:nrow(emerging_techs)) {
        cat(sprintf("%d. %s\n", i, emerging_techs$technique_name[i]))
        cat(sprintf("   Active since: %d\n", emerging_techs$first_year[i]))
        cat(sprintf("   Papers (last 5 years): %d\n", emerging_techs$recent_papers[i]))
        cat(sprintf("   Total papers: %d\n\n", emerging_techs$paper_count[i]))
      }
    }

    sink()

    cat(sprintf("✓ Created: emerging_techniques_%s.csv\n", disc_code))
    cat(sprintf("✓ Created: emerging_techniques_%s.txt\n", disc_code))
  }
}

# Create overall summary
write_csv(
  emerging_new,
  "outputs/analysis/all_emerging_techniques.csv"
)
cat("\n✓ Saved: all_emerging_techniques.csv\n")

# ============================================================================
# SUMMARY REPORT
# ============================================================================

cat("\n")
cat(paste0(strrep("=", 80), "\n"))
cat("TECHNIQUE ANALYSIS COMPLETE - SUMMARY\n")
cat(paste0(strrep("=", 80), "\n\n"))

cat("FILES CREATED:\n")
cat("  1a) techniques_per_discipline.csv - Complete technique counts by discipline\n")
cat("  1a) discipline_technique_summary.csv - Summary statistics per discipline\n")
cat("  1b) techniques_per_discipline_per_year.csv - Time series data\n")
cat("  1c) technique_trends_analysis.csv - Full trend analysis with classifications\n")
cat("  1c) technique_trends_summary.csv - Summary of trends by discipline\n")
cat("  1d) all_emerging_techniques.csv - All emerging/new techniques\n")
cat("  1d) emerging_techniques_[DISC].csv/.txt - Per-discipline lists (8 files each)\n")

cat("\n\nKEY FINDINGS:\n")

cat(sprintf("\nTotal Techniques Analyzed: %d\n", n_distinct(technique_trends$technique_name)))
cat(sprintf("Total Papers: %s\n", comma(sum(discipline_summary$total_papers))))
cat(sprintf("Year Range: %d - %d\n",
           min(technique_trends$year),
           max(technique_trends$year)))

cat("\nTechniques by Classification:\n")
for (i in 1:nrow(classification_counts)) {
  cat(sprintf("  %s: %d techniques\n",
             classification_counts$classification[i],
             classification_counts$n[i]))
}

cat("\nTop 3 Disciplines by Paper Count:\n")
top3 <- head(discipline_summary, 3)
for (i in 1:nrow(top3)) {
  cat(sprintf("  %d. %s: %s papers across %d techniques\n",
             i,
             top3$full_name[i],
             comma(top3$total_papers[i]),
             top3$total_techniques[i]))
}

cat("\n")
cat(paste0(strrep("=", 80), "\n"))
cat("Ready for Phase 2: Stacked Bar Plot Visualizations\n")
cat(paste0(strrep("=", 80), "\n"))
