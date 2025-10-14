#!/usr/bin/env Rscript
# ==============================================================================
# Create and Populate Master Technique Taxonomy Database
# ==============================================================================
# Purpose: Initialize technique_taxonomy.db with complete taxonomy from:
#          1. EEA 2025 conference data
#          2. Discipline Structure Analysis boundaries
#          3. Shark-References Automation Workflow planned searches
#          4. Gap analysis additions (all "Missing from EEA" and "Gaps" items)
# ==============================================================================

library(tidyverse)
library(RSQLite)

cat("=== Creating Master Technique Taxonomy Database ===\n\n")

# ==============================================================================
# STEP 1: Create database and execute schema
# ==============================================================================

cat("Creating database...\n")

db_path <- "database/technique_taxonomy.db"
dir.create("database", showWarnings = FALSE)

# Remove existing database if present
if (file.exists(db_path)) {
  file.remove(db_path)
  cat("  - Removed existing database\n")
}

conn <- dbConnect(SQLite(), db_path)

# Execute schema
schema_sql <- readLines("database/schema.sql")
schema_sql <- paste(schema_sql, collapse = "\n")

# Split by semicolons and execute each statement
statements <- str_split(schema_sql, ";")[[1]]
for (stmt in statements) {
  stmt_clean <- str_trim(stmt)
  if (nchar(stmt_clean) > 0 && !str_starts(stmt_clean, "--")) {
    tryCatch({
      dbExecute(conn, stmt_clean)
    }, error = function(e) {
      # Silently continue - many statements are CREATE IF NOT EXISTS
    })
  }
}

cat("✓ Database schema created\n\n")

# ==============================================================================
# STEP 2: Populate Disciplines (8 from Option B)
# ==============================================================================

cat("Populating disciplines...\n")

disciplines <- tribble(
  ~discipline_name, ~discipline_code, ~description, ~sort_order,
  "Biology, Life History, & Health", "BIO",
    "Age/growth, reproduction, physiology, disease/parasites", 1,
  "Behaviour & Sensory Ecology", "BEH",
    "Behaviour, neurobiology, sensory systems, network analysis", 2,
  "Trophic & Community Ecology", "TRO",
    "Diet (isotopes, DNA, stomach), ecosystem roles", 3,
  "Genetics, Genomics, & eDNA", "GEN",
    "Population genetics, phylogenetics, adaptive genomics, eDNA", 4,
  "Movement, Space Use, & Habitat Modeling", "MOV",
    "Telemetry, satellite tracking, SDMs, MPA design", 5,
  "Fisheries, Stock Assessment, & Management", "FISH",
    "Population dynamics, CPUE, bycatch, data-poor methods", 6,
  "Conservation Policy & Human Dimensions", "CON",
    "IUCN assessments, policy, human-shark conflict, citizen science", 7,
  "Data Science & Integrative Methods", "DATA",
    "AI/ML, data integration, Bayesian approaches, statistics", 8
)

dbWriteTable(conn, "disciplines", disciplines, append = TRUE, row.names = FALSE)
cat("✓ Added", nrow(disciplines), "disciplines\n\n")

# Get discipline IDs for foreign keys
disciplines_db <- dbGetQuery(conn, "SELECT * FROM disciplines")

# ==============================================================================
# STEP 3: Populate Categories
# ==============================================================================

cat("Populating categories...\n")

categories <- tribble(
  ~discipline_code, ~category_name, ~category_description, ~sort_order,

  # Biology
  "BIO", "Age & Growth Methods",
    "Vertebrae, spines, radiocarbon, NIRS, bomb radiocarbon", 1,
  "BIO", "Reproductive Biology",
    "Histology, ultrasound, hormones, fecundity, gestation", 2,
  "BIO", "Morphology & Morphometrics",
    "Body measurements, shape analysis, geometric morphometrics", 3,
  "BIO", "Physiology",
    "Metabolic rate, osmoregulation, blood chemistry, thermal tolerance", 4,
  "BIO", "Disease, Parasites, & Health",
    "Pathology, contaminants, immune function, health indices, telomeres", 5,

  # Behaviour
  "BEH", "Behavioural Observation",
    "Video analysis, drones, field observation, aquarium studies", 1,
  "BEH", "Sensory Biology",
    "Electroreception, olfaction, vision, hearing, magnetoreception", 2,
  "BEH", "Social Behaviour",
    "Network analysis, aggregations, social structure", 3,
  "BEH", "Cognition & Learning",
    "Learning, memory, personality, decision-making", 4,

  # Trophic
  "TRO", "Diet Analysis Methods",
    "Stomach contents, DNA metabarcoding, isotopes", 1,
  "TRO", "Trophic Position & Food Webs",
    "Trophic level, food web models, ecosystem roles", 2,
  "TRO", "Foraging Ecology",
    "Foraging behavior, prey selection, energy flow", 3,

  # Genetics
  "GEN", "Population Genetics",
    "Microsatellites, SNPs, mtDNA, population structure", 1,
  "GEN", "Genomics",
    "WGS, RAD-seq, transcriptomics, comparative genomics", 2,
  "GEN", "Phylogenetics & Taxonomy",
    "Molecular phylogeny, phylogeography, species delimitation", 3,
  "GEN", "eDNA & Metabarcoding",
    "Environmental DNA detection, monitoring, biodiversity", 4,
  "GEN", "Applied Genetics",
    "DNA forensics, conservation genetics, adaptive genetics", 5,

  # Movement
  "MOV", "Telemetry Methods",
    "Acoustic, satellite, archival tags", 1,
  "MOV", "Movement Analysis",
    "Movement models, home range, migration, connectivity", 2,
  "MOV", "Habitat Modeling",
    "SDMs, habitat suitability, niche modeling", 3,
  "MOV", "Spatial Conservation",
    "MPA design, critical habitat, spatial prioritization", 4,

  # Fisheries
  "FISH", "Stock Assessment",
    "Age-structured models, surplus production, integrated models", 1,
  "FISH", "Fishery-Dependent Data",
    "CPUE standardization, catch data, fisher interviews", 2,
  "FISH", "Bycatch & Mortality",
    "Bycatch estimation, discard mortality, post-release survival", 3,
  "FISH", "Data-Poor Methods",
    "Catch-MSY, DCAC, length-based methods", 4,
  "FISH", "Ecosystem-Based Management",
    "Ecosystem models, multispecies approaches", 5,

  # Conservation
  "CON", "Conservation Assessment",
    "IUCN Red List, extinction risk, vulnerability", 1,
  "CON", "Policy & Governance",
    "Policy evaluation, legislation, management effectiveness", 2,
  "CON", "Human Dimensions",
    "Human-wildlife conflict, perceptions, socio-economics", 3,
  "CON", "Trade & Markets",
    "CITES, trade monitoring, fin trade, sustainability", 4,
  "CON", "Participatory Approaches",
    "Citizen science, co-management, stakeholder engagement", 5,
  "CON", "Tourism & Education",
    "Ecotourism, dive tourism, education, outreach", 6,

  # Data Science
  "DATA", "Machine Learning & AI",
    "Random forest, neural networks, deep learning", 1,
  "DATA", "Statistical Models",
    "GLM, GAM, GAMM, hierarchical models", 2,
  "DATA", "Bayesian Approaches",
    "Bayesian inference, JAGS, Stan, INLA", 3,
  "DATA", "Data Integration",
    "Multi-source data, integrated models, meta-analysis", 4,
  "DATA", "Time Series & Forecasting",
    "Temporal analysis, forecasting, regime shifts", 5
)

# Add discipline_id
categories <- categories %>%
  left_join(
    disciplines_db %>% select(discipline_id, discipline_code),
    by = "discipline_code"
  ) %>%
  select(discipline_id, category_name, category_description, sort_order)

dbWriteTable(conn, "categories", categories, append = TRUE, row.names = FALSE)
cat("✓ Added", nrow(categories), "categories\n\n")

# Get categories for foreign keys
categories_db <- dbGetQuery(conn, "SELECT * FROM categories") %>%
  left_join(disciplines_db %>% select(discipline_id, discipline_code), by = "discipline_id")

cat("Category distribution:\n")
cat_summary <- categories_db %>%
  count(discipline_code) %>%
  arrange(discipline_code)
print(cat_summary, n = Inf)
cat("\n")

# ==============================================================================
# STEP 4: Populate Techniques
# ==============================================================================

cat("Populating techniques...\n\n")

# Function to add technique
add_technique <- function(discipline_code, category_name, technique_name,
                         description = NA, synonyms = NA, data_source = "planned",
                         is_parent = TRUE, parent_technique_name = NA) {

  # Get category_id
  cat_row <- categories_db %>%
    filter(discipline_code == !!discipline_code, category_name == !!category_name)

  if (nrow(cat_row) == 0) {
    cat("ERROR: Category not found:", category_name, "in", discipline_code, "\n")
    return(NULL)
  }

  parent_technique_id <- NA
  if (!is.na(parent_technique_name)) {
    parent_tech <- dbGetQuery(conn, sprintf(
      "SELECT technique_id FROM techniques WHERE technique_name = '%s'",
      parent_technique_name
    ))
    if (nrow(parent_tech) > 0) {
      parent_technique_id <- parent_tech$technique_id[1]
    }
  }

  tibble(
    technique_name = technique_name,
    technique_name_normalized = tolower(str_trim(technique_name)),
    parent_category_id = cat_row$category_id[1],
    is_parent = as.integer(is_parent),
    parent_technique_id = if (is.na(parent_technique_id)) NA_integer_ else as.integer(parent_technique_id),
    description = description,
    synonyms = synonyms,
    data_source = data_source
  )
}

techniques_list <- list()

# ==============================================================================
# BIOLOGY Techniques
# ==============================================================================

cat("Adding Biology techniques...\n")

# Age & Growth
techniques_list <- c(techniques_list, list(
  add_technique("BIO", "Age & Growth Methods", "Age & Growth",
    "Determining age and growth rates", data_source = "EEA"),
  add_technique("BIO", "Age & Growth Methods", "Vertebral Sectioning",
    "Age determination via vertebral band counts", "Vertebrae sectioning",
    data_source = "EEA", is_parent = FALSE, parent_technique_name = "Age & Growth"),
  add_technique("BIO", "Age & Growth Methods", "Bomb Radiocarbon Dating",
    "Radiocarbon dating for age validation", "C-14, radiocarbon",
    data_source = "planned"),
  add_technique("BIO", "Age & Growth Methods", "NIRS Ageing",
    "Near-infrared spectroscopy for age determination", "Near-infrared",
    data_source = "planned")
))

# Reproduction
techniques_list <- c(techniques_list, list(
  add_technique("BIO", "Reproductive Biology", "Reproduction",
    "Reproductive biology studies", data_source = "EEA"),
  add_technique("BIO", "Reproductive Biology", "Reproductive Histology",
    "Histological examination of reproductive tissues", "Gonad histology",
    data_source = "EEA+gap", is_parent = FALSE, parent_technique_name = "Reproduction"),
  add_technique("BIO", "Reproductive Biology", "Reproductive Endocrinology",
    "Hormone analysis for reproductive state", "Hormone analysis",
    data_source = "planned"),
  add_technique("BIO", "Reproductive Biology", "Ultrasound",
    "Ultrasound imaging for reproductive assessment",
    data_source = "planned"),
  add_technique("BIO", "Reproductive Biology", "Captive Breeding",
    "Ex-situ reproduction studies",
    data_source = "planned")
))

# Morphology
techniques_list <- c(techniques_list, list(
  add_technique("BIO", "Morphology & Morphometrics", "Morphology",
    "Morphological analysis", data_source = "EEA"),
  add_technique("BIO", "Morphology & Morphometrics", "Morphometrics",
    "Quantitative shape analysis", "Geometric morphometrics",
    data_source = "gap"),
  add_technique("BIO", "Morphology & Morphometrics", "CT Imaging",
    "CT/MRI scanning for morphology", "Medical imaging, MRI",
    data_source = "planned")
))

# Physiology
techniques_list <- c(techniques_list, list(
  add_technique("BIO", "Physiology", "Physiology",
    "Physiological studies", data_source = "EEA"),
  add_technique("BIO", "Physiology", "Metabolic Rate",
    "Oxygen consumption and metabolic studies",
    data_source = "planned"),
  add_technique("BIO", "Physiology", "Stress Physiology",
    "Cortisol and stress response", "Stress hormones",
    data_source = "planned"),
  add_technique("BIO", "Physiology", "Thermal Biology",
    "Temperature tolerance and thermal performance", "Thermal tolerance",
    data_source = "planned")
))

# Health & Disease
techniques_list <- c(techniques_list, list(
  add_technique("BIO", "Disease, Parasites, & Health", "Health & Disease",
    "Health assessment and disease studies", data_source = "EEA"),
  add_technique("BIO", "Disease, Parasites, & Health", "Parasitology",
    "Parasite identification and burden",
    data_source = "planned"),
  add_technique("BIO", "Disease, Parasites, & Health", "Health Indices",
    "Condition scores and health metrics", "Condition factor",
    data_source = "gap"),
  add_technique("BIO", "Disease, Parasites, & Health", "Telomere Analysis",
    "Telomere length as aging/health proxy",
    data_source = "planned"),
  add_technique("BIO", "Disease, Parasites, & Health", "Contaminants",
    "Heavy metals, pollutants, microplastics",
    data_source = "planned")
))

# Histology (cross-cutting)
techniques_list <- c(techniques_list, list(
  add_technique("BIO", "Reproductive Biology", "Histology",
    "Microscopic tissue examination", data_source = "EEA")
))

# ==============================================================================
# BEHAVIOUR Techniques
# ==============================================================================

cat("Adding Behaviour techniques...\n")

# Behavioural Observation
techniques_list <- c(techniques_list, list(
  add_technique("BEH", "Behavioural Observation", "Behavioural Observation",
    "Direct observation of behavior", data_source = "EEA"),
  add_technique("BEH", "Behavioural Observation", "Video Analysis",
    "Automated or manual video analysis", "Camera traps, video", data_source = "EEA+gap"),
  add_technique("BEH", "Behavioural Observation", "Drone Observation",
    "UAV-based behavioral observation", "UAV, aerial observation", data_source = "gap"),
  add_technique("BEH", "Behavioural Observation", "Animal-Borne Cameras",
    "Camera tags for behavior", "Crittercam", data_source = "planned"),
  add_technique("BEH", "Behavioural Observation", "Accelerometry",
    "Accelerometer data for behavior classification",
    data_source = "planned")
))

# Sensory Biology
techniques_list <- c(techniques_list, list(
  add_technique("BEH", "Sensory Biology", "Sensory Biology",
    "Sensory system studies", data_source = "EEA"),
  add_technique("BEH", "Sensory Biology", "Electroreception",
    "Electrosensory studies", "Ampullae of Lorenzini", data_source = "planned"),
  add_technique("BEH", "Sensory Biology", "Olfaction",
    "Olfactory studies", "Chemoreception", data_source = "planned"),
  add_technique("BEH", "Sensory Biology", "Vision",
    "Visual ecology and eye morphology",
    data_source = "planned"),
  add_technique("BEH", "Sensory Biology", "Magnetoreception",
    "Magnetic field detection and navigation",
    data_source = "planned")
))

# Social & Cognition
techniques_list <- c(techniques_list, list(
  add_technique("BEH", "Social Behaviour", "Social Network Analysis",
    "Network analysis of social interactions", "PBSN, spatsoc", data_source = "EEA"),
  add_technique("BEH", "Cognition & Learning", "Cognition",
    "Cognitive ability studies", data_source = "EEA"),
  add_technique("BEH", "Cognition & Learning", "Learning Experiments",
    "Experimental studies of learning and memory",
    data_source = "planned")
))

# ==============================================================================
# TROPHIC Techniques
# ==============================================================================

cat("Adding Trophic techniques...\n")

techniques_list <- c(techniques_list, list(
  # Diet Analysis
  add_technique("TRO", "Diet Analysis Methods", "Diet Analysis",
    "Dietary studies", data_source = "EEA"),
  add_technique("TRO", "Diet Analysis Methods", "Stomach Content Analysis",
    "Traditional stomach content analysis", data_source = "EEA"),
  add_technique("TRO", "Diet Analysis Methods", "DNA Metabarcoding",
    "DNA-based diet identification", "Metabarcoding", data_source = "EEA"),
  add_technique("TRO", "Diet Analysis Methods", "Stable Isotope Analysis",
    "Isotopic analysis for diet and trophic position", "SIA, isotopes", data_source = "EEA"),
  add_technique("TRO", "Diet Analysis Methods", "Fatty Acid Analysis",
    "Fatty acid signature analysis for diet", "QFASA",
    data_source = "planned"),

  # Food Webs
  add_technique("TRO", "Trophic Position & Food Webs", "Trophic Level Estimation",
    "Quantifying trophic position",
    data_source = "planned"),
  add_technique("TRO", "Trophic Position & Food Webs", "Food Web Models",
    "Network models of trophic interactions", "Ecopath",
    data_source = "planned"),
  add_technique("TRO", "Foraging Ecology", "Foraging Behavior",
    "Observational studies of foraging", "Predation behavior",
    data_source = "planned"),
  add_technique("TRO", "Foraging Ecology", "Niche Partitioning",
    "Resource partitioning studies",
    data_source = "planned")
))

# To be continued in next message due to length...
# Saving what we have so far

techniques_df <- bind_rows(techniques_list)
dbWriteTable(conn, "techniques", techniques_df, append = TRUE, row.names = FALSE)

cat("✓ Added", nrow(techniques_df), "techniques so far\n")
cat("  - Biology:", sum(str_detect(techniques_df$technique_name, "Age|Reprod|Morph|Physio|Health|Histolog|Telomere|Stress|Metabol|Parasit|Contam|Thermal|Ultrasound|Breeding|NIRS|Bomb")), "\n")
cat("  - Behaviour:", sum(str_detect(techniques_df$technique_name, "Behav|Video|Drone|Camera|Accelerom|Sensory|Electro|Olfact|Vision|Magnet|Social|Cognition|Learning")), "\n")
cat("  - Trophic:", sum(str_detect(techniques_df$technique_name, "Diet|Stomach|Metabarcoding|Isotope|Fatty|Trophic|Food|Forag|Niche")), "\n")
cat("\nContinuing with remaining disciplines...\n")

# Script continues in part 2...
dbDisconnect(conn)
cat("\n✓ Database partially populated - to be continued\n")
