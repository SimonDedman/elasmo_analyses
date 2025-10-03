#!/usr/bin/env Rscript
# ==============================================================================
# Create Candidate Database - Phase 1: Local Data Extraction
# ==============================================================================
# Extract candidate information from:
# 1. Final Speakers EEA 2025.xlsx (data tab)
# 2. Expert recommendations from documentation
# 3. Panel team roster
# ==============================================================================

library(tidyverse)
library(readxl)

# ==============================================================================
# STEP 1: Extract EEA 2025 Attendees
# ==============================================================================

cat("=== Phase 1: Local Data Extraction ===\n\n")

excel_path <- here::here("Final Speakers EEA 2025.xlsx")
eea_data <- read_excel(excel_path, sheet = "data")

cat("Step 1: Extracting EEA 2025 attendees\n")
cat("Total rows:", nrow(eea_data), "\n")

# Create candidate database from EEA 2025 data
candidates_eea <- eea_data %>%
  # Get unique people
  distinct(`Name (First)`, `Name (Last)`, .keep_all = TRUE) %>%
  # Determine EEA 2025 status
  group_by(`Name (First)`, `Name (Last)`) %>%
  summarise(
    name_first = first(`Name (First)`),
    name_last = first(`Name (Last)`),
    name_prefix = first(`Name (Prefix)`),
    email = first(Email),
    institution = first(`Institute / organization`),
    discipline_primary = first(`Analysis Discipline`),
    # Determine combined status (presentation, poster, or presentation-poster)
    eea_2025_status = case_when(
      any(format == "oral_ppt") & any(format %in% c("poster", "add_poster")) ~ "presentation-poster",
      any(format == "oral_ppt") ~ "presentation",
      any(format %in% c("poster", "add_poster")) ~ "poster",
      TRUE ~ NA_character_
    ),
    .groups = "drop"
  ) %>%
  mutate(
    # Initialize empty columns for data to be filled later
    putative_age = NA_integer_,
    sex = NA_character_,
    continent = NA_character_,
    country = NA_character_,
    seniority = NA_character_,
    publication_count_total = NA_integer_,
    publication_count_first_author_5yr = NA_integer_,
    h_index = NA_integer_,
    subdiscipline = NA_character_,
    analytical_techniques = NA_character_,
    study_taxa = NA_character_,
    study_regions = NA_character_,
    attending_eea_2025 = "Yes",
    eea_attendance_history = NA_character_,
    aes_attendance_history = NA_character_,
    si_attendance_history = NA_character_,
    source = "EEA_rec",
    proposal_status = "existing_EEA_2025"
  ) %>%
  # Reorder columns to match schema
  select(
    name_first, name_last, name_prefix, putative_age, sex,
    institution, continent, country, seniority,
    publication_count_total, publication_count_first_author_5yr, h_index,
    discipline_primary, subdiscipline, analytical_techniques,
    study_taxa, study_regions,
    attending_eea_2025, eea_attendance_history, aes_attendance_history, si_attendance_history,
    eea_2025_status, source, proposal_status, email
  )

cat("EEA 2025 candidates extracted:", nrow(candidates_eea), "\n\n")

# ==============================================================================
# STEP 2: Extract Panel Team from Timeline Document
# ==============================================================================

cat("Step 2: Extracting panel team from timeline document\n")

# Read timeline document
timeline_path <- here::here("docs/EEA2025_Data_Panel_Program_Timeline_Personnel.md")
timeline_text <- read_lines(timeline_path)

# Extract panel team names (this is a simplified extraction - may need manual review)
# Looking for patterns like: **Dr. Name Name** (role, status)

panel_team <- tribble(
  ~name_first, ~name_last, ~name_prefix, ~source, ~proposal_status, ~eea_2025_status,
  "Simon", "Dedman", "Dr.", "AI_rec", "panel_confirmed", "panel",
  "Guuske", "Tiktak", "Dr.", "AI_rec", "panel_confirmed", "panel",
  "Irene", "Kingma", NA, "sec_rec", "panel_confirmed", "panel",
  "Paddy", "Walker", NA, "sec_rec", "panel_confirmed", "panel",
  "Jürgen", "Pollerspöck", NA, "AI_rec", "panel_confirmed", "panel",
  "Nico", "Straube", NA, "AI_rec", "panel_confirmed", "panel",
  "Amy", "Jeffries", NA, "AI_rec", "panel_confirmed", "panel-presentation",
  "Charlotte", "Nuyt", NA, "AI_rec", "panel_confirmed", "panel-presentation",
  "Edward", "Lavender", NA, "AI_rec", "panel_confirmed", "panel-presentation",
  "Nicholas", "Dulvy", "Dr.", "EEA_rec", "panel_confirmed", "panel-presentation",
  "Maria Dolores", "Riesgo", NA, "AI_rec", "panel_confirmed", "panel-presentation",
  "David", "Jiménez Alvarado", "Dr.", "AI_rec", "panel_confirmed", "panel",
  "Chris", "Mull", "Dr.", "AI_rec", "panel_candidate", NA,
  "Ryan", "McMullen", NA, "AI_rec", "panel_candidate", NA
) %>%
  mutate(
    # Initialize empty columns
    putative_age = NA_integer_,
    sex = NA_character_,
    institution = NA_character_,
    continent = NA_character_,
    country = NA_character_,
    seniority = NA_character_,
    publication_count_total = NA_integer_,
    publication_count_first_author_5yr = NA_integer_,
    h_index = NA_integer_,
    discipline_primary = NA_character_,
    subdiscipline = NA_character_,
    analytical_techniques = NA_character_,
    study_taxa = NA_character_,
    study_regions = NA_character_,
    attending_eea_2025 = if_else(!is.na(eea_2025_status), "Yes", "Unknown"),
    eea_attendance_history = NA_character_,
    aes_attendance_history = NA_character_,
    si_attendance_history = NA_character_,
    email = NA_character_
  ) %>%
  select(
    name_first, name_last, name_prefix, putative_age, sex,
    institution, continent, country, seniority,
    publication_count_total, publication_count_first_author_5yr, h_index,
    discipline_primary, subdiscipline, analytical_techniques,
    study_taxa, study_regions,
    attending_eea_2025, eea_attendance_history, aes_attendance_history, si_attendance_history,
    eea_2025_status, source, proposal_status, email
  )

cat("Panel team candidates extracted:", nrow(panel_team), "\n\n")

# ==============================================================================
# STEP 3: Combine and Deduplicate
# ==============================================================================

cat("Step 3: Combining and deduplicating\n")

# Combine datasets
candidates_all <- bind_rows(candidates_eea, panel_team)

# Deduplicate - prioritize more complete records
candidates_dedup <- candidates_all %>%
  group_by(name_first, name_last) %>%
  arrange(desc(!is.na(discipline_primary)), desc(!is.na(institution))) %>%
  slice(1) %>%
  ungroup()

cat("Total unique candidates:", nrow(candidates_dedup), "\n")
cat("  From EEA 2025:", sum(candidates_dedup$proposal_status == "existing_EEA_2025"), "\n")
cat("  Panel confirmed:", sum(candidates_dedup$proposal_status == "panel_confirmed"), "\n")
cat("  Panel candidates:", sum(candidates_dedup$proposal_status == "panel_candidate"), "\n\n")

# ==============================================================================
# STEP 4: Extract Study Taxa and Regions from EEA Data
# ==============================================================================

cat("Step 4: Enriching with species and area data from EEA 2025\n")

# Create lookup for species and areas
eea_enrichment <- eea_data %>%
  group_by(`Name (First)`, `Name (Last)`) %>%
  summarise(
    study_taxa = paste(unique(na.omit(Species)), collapse = "; "),
    study_regions = paste(unique(na.omit(Area)), collapse = "; "),
    .groups = "drop"
  ) %>%
  mutate(
    study_taxa = if_else(study_taxa == "", NA_character_, study_taxa),
    study_regions = if_else(study_regions == "", NA_character_, study_regions)
  )

# Join enrichment data
candidates_enriched <- candidates_dedup %>%
  left_join(
    eea_enrichment,
    by = c("name_first" = "Name (First)", "name_last" = "Name (Last)")
  ) %>%
  mutate(
    study_taxa = coalesce(study_taxa.y, study_taxa.x),
    study_regions = coalesce(study_regions.y, study_regions.x)
  ) %>%
  select(-study_taxa.x, -study_taxa.y, -study_regions.x, -study_regions.y)

cat("Enriched candidates with species/area data\n\n")

# ==============================================================================
# STEP 5: Summary Statistics
# ==============================================================================

cat("=== Phase 1 Summary ===\n\n")

cat("Candidates by Discipline:\n")
candidates_enriched %>%
  count(discipline_primary, sort = TRUE) %>%
  print(n = Inf)

cat("\nCandidates by Proposal Status:\n")
candidates_enriched %>%
  count(proposal_status, sort = TRUE) %>%
  print(n = Inf)

cat("\nCandidates by EEA 2025 Status:\n")
candidates_enriched %>%
  count(eea_2025_status, sort = TRUE) %>%
  print(n = Inf)

cat("\nCandidates with Institution Data:\n")
cat("  With institution:", sum(!is.na(candidates_enriched$institution)), "\n")
cat("  Without institution:", sum(is.na(candidates_enriched$institution)), "\n")

# ==============================================================================
# STEP 6: Save Outputs
# ==============================================================================

cat("\n=== Saving Outputs ===\n")

dir.create("outputs", showWarnings = FALSE)

# Save main database
write_csv(candidates_enriched, "outputs/candidate_database_phase1.csv")
cat("✓ Saved: outputs/candidate_database_phase1.csv\n")

# Save summary by discipline
discipline_summary <- candidates_enriched %>%
  filter(!is.na(discipline_primary)) %>%
  count(discipline_primary, name = "candidate_count") %>%
  arrange(discipline_primary)

write_csv(discipline_summary, "outputs/candidates_by_discipline_phase1.csv")
cat("✓ Saved: outputs/candidates_by_discipline_phase1.csv\n")

# Create search log
search_log <- tibble(
  phase = "Phase 1",
  date = Sys.Date(),
  source = c("Final Speakers EEA 2025.xlsx", "Panel team roster"),
  candidates_found = c(nrow(candidates_eea), nrow(panel_team)),
  notes = c("EEA 2025 conference attendees", "Panel team from timeline document")
)

write_csv(search_log, "outputs/candidate_search_log.csv")
cat("✓ Saved: outputs/candidate_search_log.csv\n")

# ==============================================================================
# STEP 7: Identify Gaps for Phase 2
# ==============================================================================

cat("\n=== Gaps Analysis for Phase 2 ===\n\n")

# Disciplines with few candidates
cat("Underrepresented Disciplines (target: 5+ candidates each):\n")
discipline_summary %>%
  filter(candidate_count < 5) %>%
  print(n = Inf)

cat("\nNext Steps:\n")
cat("1. Review outputs/candidate_database_phase1.csv\n")
cat("2. Extract analytical techniques from presentation titles\n")
cat("3. Decide whether to proceed with web search (Phase 3)\n")
cat("4. Fill in missing demographic data for key candidates\n")

# ==============================================================================
# COMPLETE
# ==============================================================================

cat("\n✓ Phase 1 Complete\n")
