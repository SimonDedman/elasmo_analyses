#!/usr/bin/env Rscript
# ==============================================================================
# Create Tiered Technique Classification
# ==============================================================================
# Combine title and abstract techniques
# Create technique → subtechnique hierarchy
# Output: analytical_techniques_by_discipline.csv
# ==============================================================================

library(tidyverse)

cat("=== Creating Tiered Technique Classification ===\n\n")

# ==============================================================================
# STEP 1: Load techniques from both sources
# ==============================================================================

# From titles
titles <- read_csv("outputs/techniques_from_titles_summary.csv", show_col_types = FALSE)

# From abstracts
abstracts <- read_csv("outputs/techniques_from_abstracts_summary.csv", show_col_types = FALSE)

cat("Loaded techniques from:\n")
cat("  Titles:", nrow(titles), "unique techniques\n")
cat("  Abstracts:", nrow(abstracts), "unique techniques\n\n")

# ==============================================================================
# STEP 2: Define tiered hierarchy (Technique → Subtechnique)
# ==============================================================================

# Manual mapping of subtechniques to parent techniques
technique_hierarchy <- tribble(
  ~technique_parent, ~technique_child, ~discipline,

  # Biology
  "Age & Growth", "Age & Growth (VBGF)", "Biology",
  "Age & Growth", "Age & Growth (Vertebral Sectioning)", "Biology",
  "Age & Growth", "Age & Growth (Validated)", "Biology",
  "Reproduction", "Reproduction (Maturity Ogive)", "Biology",
  "Reproduction", "Reproduction (Fecundity)", "Biology",
  "Reproduction", "Reproduction (Gestation)", "Biology",

  # Behaviour
  "Behavioural Observation", "Video Analysis", "Behaviour",
  "Behavioural Observation", "Accelerometry", "Behaviour",
  "Behavioural Observation", "Time Budget Analysis", "Behaviour",

  # Trophic
  "Stable Isotope Analysis", "Stable Isotopes (δ13C/δ15N)", "Trophic",
  "Stable Isotope Analysis", "Compound-Specific Isotope Analysis", "Trophic",
  "Diet Analysis", "Stomach Content Analysis", "Trophic",
  "Diet Analysis", "Fatty Acid Analysis", "Trophic",
  "Diet Analysis", "DNA Metabarcoding", "Trophic",

  # Genetics
  "Population Genetics", "Microsatellites", "Genetics",
  "Population Genetics", "SNPs", "Genetics",
  "Population Genetics", "RAD-seq", "Genetics",
  "Genomics", "Whole Genome Sequencing", "Genetics",

  # Movement
  "Telemetry", "Acoustic Telemetry", "Movement",
  "Telemetry", "Satellite Telemetry", "Movement",
  "Movement Modeling", "Hidden Markov Models", "Movement",
  "Movement Modeling", "State-Space Models", "Movement",
  "Movement Modeling", "Brownian Bridge Movement Models", "Movement",
  "Space Use", "Kernel Density Estimation", "Movement",
  "Space Use", "Home Range", "Movement",
  "Species Distribution Models", "SDM (MaxEnt/BRT/RF)", "Movement",
  "Species Distribution Models", "Generalized Additive Models", "Movement",

  # Fisheries
  "Stock Assessment", "Surplus Production Models", "Fisheries",
  "Stock Assessment", "Age-Structured Models", "Fisheries",
  "Stock Assessment", "Data-Poor Stock Assessment", "Fisheries",
  "CPUE Standardization", "Generalized Linear Models", "Fisheries",
  "CPUE Standardization", "Delta-Lognormal Models", "Fisheries",
  "Bycatch Assessment", "Length-Based Indicators", "Fisheries",

  # Conservation
  "IUCN Assessment", "IUCN Red List Assessment", "Conservation",
  "IUCN Assessment", "Extinction Risk Assessment", "Conservation",
  "Participatory Science", "Participatory Monitoring", "Conservation",
  "Participatory Science", "Citizen Science", "Conservation",
  "Human Dimensions", "Questionnaire Surveys", "Conservation",
  "Human Dimensions", "Semi-Structured Interviews", "Conservation",

  # Data Science
  "Machine Learning", "Random Forest", "Data Science",
  "Machine Learning", "Neural Networks", "Data Science",
  "Machine Learning", "Gradient Boosting", "Data Science",
  "Bayesian Methods", "Bayesian Inference", "Data Science",
  "Bayesian Methods", "Bayesian (MCMC/Stan/JAGS)", "Data Science",
  "Multivariate Analysis", "Principal Component Analysis", "Data Science",
  "Multivariate Analysis", "Cluster Analysis", "Data Science"
)

cat("Defined", nrow(technique_hierarchy), "parent-child technique pairs\n\n")

# ==============================================================================
# STEP 3: Combine title and abstract data
# ==============================================================================

# Union of all techniques
all_techniques <- bind_rows(
  titles %>% mutate(source = "title"),
  abstracts %>% mutate(source = "abstract")
) %>%
  group_by(discipline, technique) %>%
  summarise(
    n_total = sum(n),
    n_from_titles = sum(n[source == "title"], na.rm = TRUE),
    n_from_abstracts = sum(n[source == "abstract"], na.rm = TRUE),
    sources = paste(unique(source), collapse = "+"),
    .groups = "drop"
  )

cat("Combined:", nrow(all_techniques), "unique techniques across both sources\n\n")

# ==============================================================================
# STEP 4: Apply hierarchy
# ==============================================================================

# Identify which techniques are subtechniques
techniques_with_tier <- all_techniques %>%
  left_join(
    technique_hierarchy %>%
      select(technique_child, technique_parent),
    by = c("technique" = "technique_child")
  ) %>%
  mutate(
    tier = if_else(is.na(technique_parent), "parent", "child"),
    technique_display = if_else(
      tier == "parent",
      technique,
      paste0("  └─ ", technique)  # Indent subtechniques
    )
  ) %>%
  # Sort by parent technique, then child
  arrange(discipline, coalesce(technique_parent, technique), tier, technique)

cat("=== Tiered Technique Structure ===\n\n")
cat("Parent techniques:", sum(techniques_with_tier$tier == "parent"), "\n")
cat("Child techniques:", sum(techniques_with_tier$tier == "child"), "\n\n")

# ==============================================================================
# STEP 5: Generate discipline summaries
# ==============================================================================

cat("=== Techniques by Discipline (with hierarchy) ===\n\n")

for (disc in unique(techniques_with_tier$discipline)) {
  cat("###", disc, "###\n")

  disc_techniques <- techniques_with_tier %>%
    filter(discipline == disc) %>%
    select(technique_display, n_total, sources)

  print(disc_techniques, n = 100)
  cat("\n")
}

# ==============================================================================
# STEP 6: Save final output
# ==============================================================================

cat("=== Saving final outputs ===\n")

# Full tiered classification
write_csv(
  techniques_with_tier %>%
    select(
      discipline,
      tier,
      technique,
      technique_parent,
      n_total,
      n_from_titles,
      n_from_abstracts,
      sources
    ),
  "outputs/analytical_techniques_by_discipline.csv"
)
cat("✓ Saved: outputs/analytical_techniques_by_discipline.csv\n")

# Simplified parent-only view for quick reference
parent_techniques <- techniques_with_tier %>%
  filter(tier == "parent") %>%
  select(discipline, technique, n_total, sources) %>%
  arrange(discipline, desc(n_total))

write_csv(parent_techniques, "outputs/analytical_techniques_parents_only.csv")
cat("✓ Saved: outputs/analytical_techniques_parents_only.csv\n")

# ==============================================================================
# STEP 7: Coverage statistics
# ==============================================================================

cat("\n=== Coverage Statistics ===\n\n")

discipline_stats <- techniques_with_tier %>%
  group_by(discipline) %>%
  summarise(
    n_parent_techniques = sum(tier == "parent"),
    n_child_techniques = sum(tier == "child"),
    total_mentions = sum(n_total),
    from_titles = sum(n_from_titles),
    from_abstracts = sum(n_from_abstracts),
    .groups = "drop"
  ) %>%
  arrange(desc(total_mentions))

print(discipline_stats)

cat("\n=== Summary ===\n\n")
cat("Total unique techniques:", nrow(all_techniques), "\n")
cat("  Parent techniques:", sum(techniques_with_tier$tier == "parent"), "\n")
cat("  Subtechniques:", sum(techniques_with_tier$tier == "child"), "\n")
cat("Total mentions:", sum(techniques_with_tier$n_total), "\n")
cat("  From titles:", sum(techniques_with_tier$n_from_titles), "\n")
cat("  From abstracts:", sum(techniques_with_tier$n_from_abstracts), "\n")

cat("\n✓ Tiered classification complete\n")
