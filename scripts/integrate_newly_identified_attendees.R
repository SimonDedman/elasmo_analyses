#!/usr/bin/env Rscript
# ==============================================================================
# Integrate Newly Identified Attendees into Candidate Database
# ==============================================================================
# Add Lorenzo Elias, Hettie Brown, and Paul Cox (tentative)
# ==============================================================================

library(tidyverse)
library(readxl)

cat("=== Integrating Newly Identified Attendees ===\n\n")

# ==============================================================================
# STEP 1: Load current candidate database
# ==============================================================================

candidate_db <- read_csv("outputs/candidate_database_phase1.csv", show_col_types = FALSE)

cat("Current database:\", nrow(candidate_db), \"candidates\n\n")

# ==============================================================================
# STEP 2: Load updated attendee list
# ==============================================================================

attendees <- read_excel("EEA 2025 Attendee List.xlsx", sheet = 1)

cat("Attendee list:\", nrow(attendees), \"attendees\n\n")

# ==============================================================================
# STEP 3: Check if new people are already in database
# ==============================================================================

cat("=== Checking for duplicates ===\n\n")

new_people <- tribble(
  ~name_first, ~name_last,
  "Lorenzo", "Elias",
  "Hettie", "Brown",
  "Paul", "Cox"
)

for (i in 1:nrow(new_people)) {
  person <- new_people[i, ]

  already_exists <- candidate_db %>%
    filter(name_first == person$name_first, name_last == person$name_last) %>%
    nrow() > 0

  if (already_exists) {
    cat("✓", person$name_first, person$name_last, "- already in database\n")
  } else {
    cat("✗", person$name_first, person$name_last, "- NOT in database, will add\n")
  }
}

cat("\n")

# ==============================================================================
# STEP 4: Get data from attendee list for new people
# ==============================================================================

cat("=== Extracting data from attendee list ===\n\n")

new_attendee_data <- attendees %>%
  filter(
    (`Name (First)` == "Lorenzo" & `Name (Last)` == "Elias") |
    (`Name (First)` == "Hettie" & `Name (Last)` == "Brown") |
    (`Name (First)` == "Paul" & `Name (Last)` == "Cox")
  ) %>%
  rename(
    name_first = `Name (First)`,
    name_last = `Name (Last)`,
    email = Email,
    institution = `Organisation / Institute`,
    discipline_primary = `Discipline (8-category)`
  ) %>%
  mutate(
    # Add standard fields
    name_prefix = NA_character_,
    putative_age = NA_integer_,
    sex = NA_character_,
    continent = NA_character_,
    country = case_when(
      name_first == "Lorenzo" ~ "Netherlands",  # Wageningen
      name_first %in% c("Hettie", "Paul") ~ "United Kingdom",  # Shark Trust
      TRUE ~ NA_character_
    ),
    seniority = NA_character_,
    publication_count_total = NA_integer_,
    publication_count_first_author_5yr = NA_integer_,
    h_index = NA_integer_,
    subdiscipline = NA_character_,
    analytical_techniques = NA_character_,
    study_taxa = NA_character_,
    study_regions = NA_character_,
    attending_eea_2025 = "Yes",
    eea_2025_status = "attendee",
    conf_attendance = NA_character_,
    source = "attendee_abstract_search",
    proposal_status = "eea_2025_attendee"
  )

cat("Found", nrow(new_attendee_data), "new attendees to add:\n")
print(new_attendee_data %>% select(name_first, name_last, institution, email))
cat("\n")

# ==============================================================================
# STEP 5: Integrate into candidate database
# ==============================================================================

cat("=== Integrating into candidate database ===\n\n")

# Ensure column order matches
new_attendee_data <- new_attendee_data %>%
  select(all_of(names(candidate_db)))

# Add only those not already in database
already_in_db <- candidate_db %>%
  inner_join(new_attendee_data, by = c("name_first", "name_last")) %>%
  select(name_first, name_last)

candidates_to_add <- new_attendee_data %>%
  anti_join(already_in_db, by = c("name_first", "name_last"))

cat("Adding", nrow(candidates_to_add), "new candidates:\n")
print(candidates_to_add %>% select(name_first, name_last, institution))
cat("\n")

# Combine
candidate_db_updated <- bind_rows(candidate_db, candidates_to_add)

cat("Updated database:\", nrow(candidate_db_updated), \"candidates\n")
cat("  (was", nrow(candidate_db), ")\n\n")

# ==============================================================================
# STEP 6: Save updated database
# ==============================================================================

cat("=== Saving updated database ===\n")

write_csv(candidate_db_updated, "outputs/candidate_database_phase1.csv")

cat("✓ Saved: outputs/candidate_database_phase1.csv\n")

cat("\n✓ Integration complete\n")
