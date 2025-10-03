#!/usr/bin/env Rscript
# ==============================================================================
# Extract Analytical Techniques from Presentation Titles
# ==============================================================================
# Approach: Pattern matching for known analytical method keywords
# Output: Broad technique categories from titles
# ==============================================================================

library(tidyverse)
library(readxl)

cat("=== Extracting Analytical Techniques from Titles ===\n\n")

# ==============================================================================
# STEP 1: Load presentation data
# ==============================================================================

speakers <- read_excel("Final Speakers EEA 2025.xlsx", sheet = 1)

cat("Loaded", nrow(speakers), "presentations\n\n")

# ==============================================================================
# STEP 2: Define technique keyword patterns by discipline
# ==============================================================================

# Technique patterns (broad categories)
technique_patterns <- tribble(
  ~technique, ~pattern, ~discipline,

  # Biology, Life History & Health
  "Age & Growth", "age|growth|otolith|vertebra|validated|aging|ageing|von bertalanffy|vbgf", "Biology",
  "Reproduction", "reproduct|matur|fecund|gestat|pregnan|pup|litter", "Biology",
  "Morphology", "morpholog|morphometr|measur|length|weight|size", "Biology",
  "Physiology", "physiolog|metabol|respir|osmoreg|stress|hormone", "Biology",
  "Histology", "histolog|microscop|tissue|cellular|biopsy", "Biology",
  "Health & Disease", "health|disease|parasit|pathogen|condition|wellness", "Biology",

  # Behaviour & Sensory Ecology
  "Behavioural Observation", "behavio|observation|dive|swim|feed|social", "Behaviour",
  "Sensory Biology", "sensor|vision|visual|olfact|smell|electro|magnetic", "Behaviour",
  "Cognition", "cognit|learn|memory|decision", "Behaviour",
  "Video Analysis", "video|camera|footage|recording|underwater", "Behaviour",

  # Trophic & Community Ecology
  "Diet Analysis", "diet|stomach|gut content|prey|feeding", "Trophic",
  "Stable Isotopes", "isotope|δ13c|δ15n|d13c|d15n|carbon|nitrogen", "Trophic",
  "Fatty Acids", "fatty acid|lipid|siar|simm", "Trophic",
  "Trophic Position", "trophic|food web|ecosystem role|predator", "Trophic",
  "DNA Metabarcoding", "metabarcod|edna diet|diet dna|molecular diet", "Trophic",

  # Genetics, Genomics & eDNA
  "Population Genetics", "population genetic|microsatellite|snp|aflp|genetic structure", "Genetics",
  "Phylogenetics", "phylogen|phylogeo|molecular|evolution|tree", "Genetics",
  "Genomics", "genom|transcriptom|proteom|sequenc", "Genetics",
  "eDNA", "edna|environmental dna", "Genetics",
  "Parentage", "parentage|paternity|kinship|pedigree", "Genetics",

  # Movement, Space Use & Habitat Modeling
  "Acoustic Telemetry", "acoustic|telemetry|tag|receiver|detect|vps|vemco", "Movement",
  "Satellite Telemetry", "satellite|psat|argos|spot tag|geolocation", "Movement",
  "Movement Modeling", "movement model|hidden markov|hmm|state-space|ssm|crawl", "Movement",
  "Home Range", "home range|kernel|utilization|space use|mcp", "Movement",
  "Habitat Modeling", "habitat model|distribution|niche|maxent|ensemble", "Movement",
  "Species Distribution Model", "sdm|species distribution|boosted regression|brt|random forest|gam", "Movement",
  "Connectivity", "connectivity|network|corridor|migration|dispersal", "Movement",
  "MPA Design", "mpa|marine protected|spatial planning|conservation area", "Movement",

  # Fisheries & Stock Assessment
  "Stock Assessment", "stock assess|surplus production|age-structured|delay-difference", "Fisheries",
  "CPUE Standardization", "cpue|catch per unit|standardiz|glm|gam|delta", "Fisheries",
  "Bycatch Assessment", "bycatch|incidental|observer|discard", "Fisheries",
  "Fishery-Independent Survey", "survey|trawl|longline survey|abundance index", "Fisheries",
  "Data-Poor Methods", "data-poor|dbsra|lbi|length-based|psa", "Fisheries",
  "Mark-Recapture", "mark-recapture|tagging|tag-return|ckmr", "Fisheries",

  # Conservation Policy & Human Dimensions
  "IUCN Assessment", "iucn|red list|threatened|endangered|assessment", "Conservation",
  "Policy Evaluation", "policy|regulation|management|legislation|compliance", "Conservation",
  "Citizen Science", "citizen science|participatory|community|engagement", "Conservation",
  "Human Dimensions", "human|fisher|stakeholder|perception|conflict|coexist", "Conservation",
  "Trade & Markets", "trade|market|fin|consumption|demand", "Conservation",
  "Tourism", "tourism|ecotourism|shark diving|recreation", "Conservation",

  # Data Science & Integrative Methods
  "Machine Learning", "machine learn|neural network|deep learning|ai|random forest", "Data Science",
  "Bayesian Methods", "bayesian|mcmc|jags|stan|posterior", "Data Science",
  "Time Series", "time series|trend|arima|breakpoint|changepoint", "Data Science",
  "Multivariate Analysis", "multivariate|pca|nmds|cluster|ordination", "Data Science",
  "Meta-Analysis", "meta-analysis|systematic review|effect size", "Data Science",
  "Data Integration", "integrat|synthesis|multi-source|data fusion", "Data Science"
)

cat("Defined", nrow(technique_patterns), "technique patterns\n\n")

# ==============================================================================
# STEP 3: Extract techniques from titles
# ==============================================================================

cat("=== Searching titles for techniques ===\n\n")

# Create results table
title_techniques <- speakers %>%
  select(
    format = format,
    title = Title,
    presenter_first = `Name (First)`,
    presenter_last = `Name (Last)`,
    prez_discipline = `Analysis Discipline`
  ) %>%
  # Search for each technique pattern
  crossing(technique_patterns) %>%
  mutate(
    # Check if pattern matches title
    matches = str_detect(title, regex(pattern, ignore_case = TRUE))
  ) %>%
  filter(matches) %>%
  # Use technique's discipline, not presentation's discipline
  select(-pattern, -matches, -prez_discipline) %>%
  distinct()

cat("Found", nrow(title_techniques), "technique mentions in titles\n\n")

# ==============================================================================
# STEP 4: Summary by discipline and technique
# ==============================================================================

cat("=== Technique distribution ===\n\n")

technique_summary <- title_techniques %>%
  count(discipline, technique, sort = TRUE)

print(technique_summary)

# ==============================================================================
# STEP 5: Identify most common techniques per discipline
# ==============================================================================

cat("\n=== Top 3 techniques per discipline ===\n\n")

top_techniques <- technique_summary %>%
  group_by(discipline) %>%
  slice_max(n, n = 3, with_ties = FALSE) %>%
  ungroup()

print(top_techniques)

# ==============================================================================
# STEP 6: Save outputs
# ==============================================================================

cat("\n=== Saving outputs ===\n")

# Full extraction
write_csv(title_techniques, "outputs/techniques_from_titles.csv")
cat("✓ Saved: outputs/techniques_from_titles.csv\n")

# Summary
write_csv(technique_summary, "outputs/techniques_from_titles_summary.csv")
cat("✓ Saved: outputs/techniques_from_titles_summary.csv\n")

# Top techniques
write_csv(top_techniques, "outputs/techniques_from_titles_top3.csv")
cat("✓ Saved: outputs/techniques_from_titles_top3.csv\n")

# ==============================================================================
# STEP 7: Coverage statistics
# ==============================================================================

cat("\n=== Coverage Statistics ===\n\n")

total_presentations <- nrow(speakers)
with_techniques <- n_distinct(title_techniques$title)
coverage_pct <- round(100 * with_techniques / total_presentations, 1)

cat("Total presentations:", total_presentations, "\n")
cat("With identified techniques:", with_techniques, "\n")
cat("Coverage:", coverage_pct, "%\n")

cat("\nPresentations by discipline:\n")
speakers %>% count(discipline = `Analysis Discipline`) %>% print()

cat("\nTechniques identified by discipline:\n")
title_techniques %>%
  count(discipline) %>%
  arrange(desc(n)) %>%
  print()

cat("\n✓ Title extraction complete\n")
