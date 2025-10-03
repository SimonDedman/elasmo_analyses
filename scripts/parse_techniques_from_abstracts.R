#!/usr/bin/env Rscript
# ==============================================================================
# Parse and Structure Techniques from Abstracts
# ==============================================================================
# Input: techniques_from_abstracts_raw.txt (filename|pattern|context)
# Output: Structured CSV with discipline mapping
# ==============================================================================

library(tidyverse)

cat("=== Parsing Abstract Techniques ===\n\n")

# ==============================================================================
# STEP 1: Load raw extraction
# ==============================================================================

abstracts_raw <- read_delim(
  "outputs/techniques_from_abstracts_raw.txt",
  delim = "|",
  col_names = c("filename", "pattern", "context"),
  col_types = "ccc",
  show_col_types = FALSE
)

cat("Loaded", nrow(abstracts_raw), "technique matches from abstracts\n\n")

# ==============================================================================
# STEP 2: Map patterns to technique names and disciplines
# ==============================================================================

# Technique mapping (pattern → clean name + discipline)
technique_mapping <- tribble(
  ~pattern, ~technique, ~discipline,

  # Biology
  "age.*growth", "Age & Growth", "Biology",
  "von.*bertalanffy", "Age & Growth (VBGF)", "Biology",
  "vertebra.*section", "Age & Growth (Vertebral Sectioning)", "Biology",
  "validated.*age", "Age & Growth (Validated)", "Biology",
  "histolog", "Histology", "Biology",
  "reproduct.*cycle", "Reproduction", "Biology",
  "maturity.*ogive", "Reproduction (Maturity Ogive)", "Biology",
  "fecundity", "Reproduction (Fecundity)", "Biology",
  "gestation", "Reproduction (Gestation)", "Biology",

  # Behaviour
  "acceleromet", "Accelerometry", "Behaviour",
  "video.*analysis", "Video Analysis", "Behaviour",
  "behavioural.*observation", "Behavioural Observation", "Behaviour",
  "time.*budget", "Time Budget Analysis", "Behaviour",
  "social.*network", "Social Network Analysis", "Behaviour",

  # Trophic Ecology
  "stable.*isotope", "Stable Isotope Analysis", "Trophic",
  "δ13c|δ15n|d13c|d15n", "Stable Isotopes (δ13C/δ15N)", "Trophic",
  "fatty.*acid", "Fatty Acid Analysis", "Trophic",
  "stomach.*content", "Stomach Content Analysis", "Trophic",
  "metabarcod", "DNA Metabarcoding", "Trophic",
  "compound.*specific.*isotope", "Compound-Specific Isotope Analysis", "Trophic",

  # Genetics
  "microsatellite", "Microsatellites", "Genetics",
  "single.*nucleotide.*polymorphism|snp", "SNPs", "Genetics",
  "whole.*genome.*sequenc", "Whole Genome Sequencing", "Genetics",
  "rad.*seq|ddrad", "RAD-seq", "Genetics",
  "environmental.*dna|edna", "eDNA", "Genetics",
  "population.*genetic.*structure", "Population Genetics", "Genetics",

  # Movement
  "acoustic.*telemetry", "Acoustic Telemetry", "Movement",
  "satellite.*tag|psat", "Satellite Telemetry", "Movement",
  "hidden.*markov.*model|hmm", "Hidden Markov Models", "Movement",
  "state.*space.*model|ssm", "State-Space Models", "Movement",
  "kernel.*density", "Kernel Density Estimation", "Movement",
  "brownian.*bridge", "Brownian Bridge Movement Models", "Movement",
  "species.*distribution.*model|sdm", "Species Distribution Models", "Movement",
  "maxent|boosted.*regression.*tree|random.*forest", "SDM (MaxEnt/BRT/RF)", "Movement",
  "generalized.*additive.*model|gam", "Generalized Additive Models", "Movement",

  # Fisheries
  "surplus.*production", "Surplus Production Models", "Fisheries",
  "catch.*per.*unit.*effort|cpue", "CPUE Standardization", "Fisheries",
  "generalized.*linear.*model|glm", "Generalized Linear Models", "Fisheries",
  "delta.*lognormal", "Delta-Lognormal Models", "Fisheries",
  "age.*structured.*model", "Age-Structured Models", "Fisheries",
  "length.*based.*indicator|lbi", "Length-Based Indicators", "Fisheries",
  "data.*poor.*stock.*assessment|dbsra", "Data-Poor Stock Assessment", "Fisheries",

  # Conservation
  "iucn.*red.*list", "IUCN Red List Assessment", "Conservation",
  "extinction.*risk.*assessment", "Extinction Risk Assessment", "Conservation",
  "participatory.*monitoring", "Participatory Monitoring", "Conservation",
  "questionnaire.*survey", "Questionnaire Surveys", "Conservation",
  "semi.*structured.*interview", "Semi-Structured Interviews", "Conservation",

  # Data Science
  "machine.*learning", "Machine Learning", "Data Science",
  "neural.*network", "Neural Networks", "Data Science",
  "bayesian.*inference", "Bayesian Inference", "Data Science",
  "mcmc|stan|jags", "Bayesian (MCMC/Stan/JAGS)", "Data Science",
  "random.*forest", "Random Forest", "Data Science",
  "gradient.*boosting", "Gradient Boosting", "Data Science",
  "principal.*component.*analysis|pca", "Principal Component Analysis", "Data Science",
  "cluster.*analysis", "Cluster Analysis", "Data Science",
  "meta.*analysis", "Meta-Analysis", "Data Science"
)

# Join with mapping
abstracts_structured <- abstracts_raw %>%
  left_join(technique_mapping, by = "pattern") %>%
  filter(!is.na(technique)) %>%  # Remove unmapped patterns
  # Clean context (remove extra whitespace)
  mutate(
    context = str_squish(context),
    # Extract presentation number from filename
    presentation_id = str_extract(filename, "^[OP]_?\\d+")
  )

cat("Mapped", nrow(abstracts_structured), "techniques to disciplines\n\n")

# ==============================================================================
# STEP 3: Create summary tables
# ==============================================================================

# By technique
technique_summary <- abstracts_structured %>%
  count(discipline, technique, sort = TRUE)

cat("=== Technique Distribution ===\n\n")
print(technique_summary)

# By discipline
discipline_summary <- abstracts_structured %>%
  count(discipline, name = "n_techniques", sort = TRUE)

cat("\n=== Techniques by Discipline ===\n\n")
print(discipline_summary)

# By presentation
presentation_summary <- abstracts_structured %>%
  count(presentation_id, filename, sort = TRUE)

cat("\n=== Presentations with Most Techniques ===\n\n")
print(head(presentation_summary, 15))

# ==============================================================================
# STEP 4: Save outputs
# ==============================================================================

cat("\n=== Saving structured outputs ===\n")

# Full structured data
write_csv(abstracts_structured, "outputs/techniques_from_abstracts_structured.csv")
cat("✓ Saved: outputs/techniques_from_abstracts_structured.csv\n")

# Technique summary
write_csv(technique_summary, "outputs/techniques_from_abstracts_summary.csv")
cat("✓ Saved: outputs/techniques_from_abstracts_summary.csv\n")

# Presentation summary
write_csv(presentation_summary, "outputs/abstracts_technique_counts.csv")
cat("✓ Saved: outputs/abstracts_technique_counts.csv\n")

cat("\n✓ Abstract parsing complete\n")
