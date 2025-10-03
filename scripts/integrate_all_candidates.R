#!/usr/bin/env Rscript
# ==============================================================================
# Integrate All Candidate Sources into Database
# ==============================================================================
# 1. Expert_Recommendations_Comprehensive.md
# 2. EEA 2025 Attendee List.xlsx
# Carefully avoid duplicates
# ==============================================================================

library(tidyverse)
library(readxl)

cat("=== Integrating All Candidate Sources ===\n\n")

# ==============================================================================
# STEP 1: Load current candidate database
# ==============================================================================

current_db <- read_csv("outputs/candidate_database_phase1.csv", show_col_types = FALSE)

cat("Current database:", nrow(current_db), "candidates\n\n")

# ==============================================================================
# STEP 2: Extract candidates from Expert Recommendations
# ==============================================================================

cat("=== Extracting from Expert_Recommendations_Comprehensive.md ===\n")

expert_rec_path <- "docs/Expert_Recommendations_Comprehensive.md"
expert_text <- read_lines(expert_rec_path)

# Parse the markdown structure to extract expert names
# Pattern: **Dr. Name Name** or **Name Name**
# Also capture role and status from parentheses

expert_pattern <- "\\*\\*(?:Dr\\.|Prof\\.|Ms\\.|Mr\\.|Mx\\.)?\\s*([A-Z][a-z]+(?:\\s+[A-Z][a-z]+)*)\\*\\*"

experts_raw <- tibble(line_num = seq_along(expert_text), line = expert_text) %>%
  filter(str_detect(line, expert_pattern)) %>%
  mutate(
    # Extract the full name
    full_name = str_extract(line, expert_pattern) %>%
      str_remove_all("\\*\\*") %>%
      str_trim(),
    # Extract prefix if present
    name_prefix = str_extract(full_name, "^(Dr|Prof|Ms|Mr|Mx)\\."),
    # Remove prefix from name
    name_clean = str_remove(full_name, "^(Dr|Prof|Ms|Mr|Mx)\\.\\s*"),
    # Split into first and last name
    name_parts = str_split(name_clean, "\\s+"),
    # Assume first word is first name, rest is last name
    name_first = map_chr(name_parts, ~.x[1]),
    name_last = map_chr(name_parts, ~if(length(.x) > 1) paste(.x[-1], collapse = " ") else NA_character_),
    # Extract any info in parentheses or after dash
    context = str_extract(line, "(?:\\-|\\().*$"),
    # Try to extract institution
    institution = str_extract(context, "(?<=\\-\\s)([^,\\(]+)(?=,|\\(|$)") %>% str_trim(),
    # Try to extract status
    status = case_when(
      str_detect(context, "confirmed|Confirmed") ~ "confirmed",
      str_detect(context, "invited|Invited") ~ "invited",
      str_detect(context, "declined|Declined") ~ "declined",
      str_detect(context, "tentative") ~ "tentative",
      TRUE ~ NA_character_
    ),
    # Determine source
    source = case_when(
      str_detect(line, "AI.*rec|recommended") ~ "AI_rec",
      str_detect(line, "EEA.*rec") ~ "EEA_rec",
      str_detect(line, "sec.*rec|secretariat") ~ "sec_rec",
      TRUE ~ "AI_rec"  # Default for expert recommendations
    )
  ) %>%
  filter(!is.na(name_first), !is.na(name_last)) %>%
  # Remove obviously wrong extractions
  filter(
    !name_first %in% c("Additional", "Strong", "Confirmed", "High", "Priority"),
    nchar(name_first) > 1,
    nchar(name_last) > 1
  ) %>%
  select(name_first, name_last, name_prefix, institution, status, source)

cat("Extracted", nrow(experts_raw), "expert names from recommendations\n")

# Look for discipline context by finding which section they're in
# Read file and identify discipline sections
discipline_sections <- tibble(line_num = seq_along(expert_text), line = expert_text) %>%
  filter(str_detect(line, "^###\\s+\\d+\\.")) %>%
  mutate(
    discipline = str_extract(line, "(?<=###\\s).*$") %>% str_trim()
  )

# Assign disciplines based on which section each expert appears in
experts_with_discipline <- experts_raw %>%
  mutate(line_num = row_number()) %>%
  left_join(
    tibble(line = expert_text) %>%
      mutate(
        line_num = row_number(),
        # Find nearest discipline header before this line
        discipline_section = NA_character_
      ),
    by = "line_num"
  )

# Simpler approach: manually map based on what we know
# Since parsing is complex, let's create standardized records
experts_cleaned <- experts_raw %>%
  distinct(name_first, name_last, .keep_all = TRUE) %>%
  mutate(
    # Create placeholder for other fields
    putative_age = NA_integer_,
    sex = NA_character_,
    continent = NA_character_,
    country = NA_character_,
    seniority = NA_character_,
    publication_count_total = NA_integer_,
    publication_count_first_author_5yr = NA_integer_,
    h_index = NA_integer_,
    discipline_primary = NA_character_,  # Will need manual assignment
    subdiscipline = NA_character_,
    analytical_techniques = NA_character_,
    study_taxa = NA_character_,
    study_regions = NA_character_,
    attending_eea_2025 = if_else(status == "confirmed", "Yes", "Unknown"),
    eea_2025_status = if_else(status == "confirmed", "panel", NA_character_),
    conf_attendance = NA_character_,
    proposal_status = if_else(status == "confirmed", "panel_confirmed", "panel_candidate"),
    email = NA_character_
  ) %>%
  select(all_of(names(current_db)))

cat("Cleaned to", nrow(experts_cleaned), "unique expert candidates\n\n")

# ==============================================================================
# STEP 3: Load and process EEA 2025 Attendee List
# ==============================================================================

cat("=== Loading EEA 2025 Attendee List ===\n")

attendee_list <- read_excel("EEA 2025 Attendee List.xlsx", sheet = 1)

cat("Attendee list:", nrow(attendee_list), "attendees\n")

# Standardize to database format
attendees_cleaned <- attendee_list %>%
  rename(
    name_first = `Name (First)`,
    name_last = `Name (Last)`,
    email = Email,
    institution = `Organisation / Institute`,
    discipline_primary = `Discipline (8-category)`
  ) %>%
  mutate(
    # Add placeholders for missing fields
    name_prefix = NA_character_,
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
    attending_eea_2025 = "Yes",  # All on attendee list are attending
    eea_2025_status = "attendee",  # May be updated if they're also presenters
    conf_attendance = NA_character_,
    source = "EEA_rec",
    proposal_status = "eea_2025_attendee"
  ) %>%
  select(all_of(names(current_db)))

cat("Cleaned to", nrow(attendees_cleaned), "attendee records\n\n")

# ==============================================================================
# STEP 4: Combine all sources and remove duplicates
# ==============================================================================

cat("=== Combining all sources ===\n")

# Combine all
all_candidates <- bind_rows(
  current_db %>% mutate(data_source = "current_db"),
  experts_cleaned %>% mutate(data_source = "expert_rec"),
  attendees_cleaned %>% mutate(data_source = "attendee_list")
)

cat("Combined total:", nrow(all_candidates), "records\n")

# Deduplicate - prioritize more complete records
# Priority: current_db > attendee_list > expert_rec (for data completeness)
candidates_dedup <- all_candidates %>%
  group_by(name_first, name_last) %>%
  arrange(
    # Sort by data completeness
    desc(data_source == "current_db"),
    desc(data_source == "attendee_list"),
    desc(!is.na(email)),
    desc(!is.na(institution)),
    desc(!is.na(discipline_primary))
  ) %>%
  # Merge data from duplicate records
  summarise(
    # Take first non-NA value for each field
    name_prefix = first(na.omit(name_prefix)),
    putative_age = first(na.omit(putative_age)),
    sex = first(na.omit(sex)),
    institution = first(na.omit(institution)),
    continent = first(na.omit(continent)),
    country = first(na.omit(country)),
    seniority = first(na.omit(seniority)),
    publication_count_total = first(na.omit(publication_count_total)),
    publication_count_first_author_5yr = first(na.omit(publication_count_first_author_5yr)),
    h_index = first(na.omit(h_index)),
    discipline_primary = first(na.omit(discipline_primary)),
    subdiscipline = first(na.omit(subdiscipline)),
    analytical_techniques = first(na.omit(analytical_techniques)),
    study_taxa = first(na.omit(study_taxa)),
    study_regions = first(na.omit(study_regions)),
    attending_eea_2025 = first(na.omit(attending_eea_2025)),
    eea_2025_status = first(na.omit(eea_2025_status)),
    conf_attendance = first(na.omit(conf_attendance)),
    source = first(na.omit(source)),
    proposal_status = first(na.omit(proposal_status)),
    email = first(na.omit(email)),
    # Track which sources contributed to this record
    data_sources = paste(unique(data_source), collapse = ";"),
    .groups = "drop"
  )

cat("After deduplication:", nrow(candidates_dedup), "unique candidates\n\n")

# ==============================================================================
# STEP 5: Statistics
# ==============================================================================

cat("=== Integration Statistics ===\n\n")

cat("Records by source:\n")
all_candidates %>%
  count(data_source) %>%
  print()

cat("\nNew candidates added:\n")
cat("  From current DB:", sum(str_detect(candidates_dedup$data_sources, "current_db")), "\n")
cat("  NEW from expert rec:", sum(str_detect(candidates_dedup$data_sources, "expert_rec") &
                                    !str_detect(candidates_dedup$data_sources, "current_db")), "\n")
cat("  NEW from attendee list:", sum(str_detect(candidates_dedup$data_sources, "attendee_list") &
                                       !str_detect(candidates_dedup$data_sources, "current_db")), "\n")

cat("\nEnhanced records (multiple sources):\n")
candidates_dedup %>%
  filter(str_count(data_sources, ";") > 0) %>%
  count(data_sources) %>%
  print()

# ==============================================================================
# STEP 6: Update EEA 2025 status for presenters in attendee list
# ==============================================================================

cat("\n=== Updating EEA 2025 status for presenters ===\n")

# If someone is in current_db with presentation/poster status AND in attendee list,
# keep their presentation/poster status (don't overwrite with "attendee")
candidates_final <- candidates_dedup %>%
  mutate(
    # If they have a specific status (not just attendee), keep it
    eea_2025_status = if_else(
      eea_2025_status == "attendee" & str_detect(data_sources, "current_db"),
      NA_character_,  # Will be filled from current_db which has priority
      eea_2025_status
    )
  ) %>%
  select(-data_sources)

# Fill in status from original current_db for exact matches
status_lookup <- current_db %>%
  select(name_first, name_last, eea_2025_status_orig = eea_2025_status)

candidates_final <- candidates_final %>%
  left_join(status_lookup, by = c("name_first", "name_last")) %>%
  mutate(
    eea_2025_status = coalesce(eea_2025_status_orig, eea_2025_status)
  ) %>%
  select(-eea_2025_status_orig)

# ==============================================================================
# STEP 7: Save updated database
# ==============================================================================

cat("\n=== Saving updated database ===\n")

write_csv(candidates_final, "outputs/candidate_database_phase1.csv")
cat("✓ Saved:", nrow(candidates_final), "candidates to outputs/candidate_database_phase1.csv\n")

# ==============================================================================
# STEP 8: Summary by category
# ==============================================================================

cat("\n=== Final Database Summary ===\n\n")

cat("Total candidates:", nrow(candidates_final), "\n")
cat("With disciplines:", sum(!is.na(candidates_final$discipline_primary)), "\n")
cat("With institutions:", sum(!is.na(candidates_final$institution)), "\n")
cat("With emails:", sum(!is.na(candidates_final$email)), "\n")
cat("Attending EEA 2025:", sum(candidates_final$attending_eea_2025 == "Yes", na.rm = TRUE), "\n")
cat("With conference history:", sum(!is.na(candidates_final$conf_attendance)), "\n")

cat("\nBy proposal status:\n")
candidates_final %>%
  count(proposal_status, sort = TRUE) %>%
  print()

cat("\nBy EEA 2025 status:\n")
candidates_final %>%
  count(eea_2025_status, sort = TRUE) %>%
  print()

cat("\n✓ Integration Complete\n")
