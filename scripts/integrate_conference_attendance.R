#!/usr/bin/env Rscript
# ==============================================================================
# Integrate Conference Attendance into Candidate Database
# ==============================================================================
# Combines SI2022 + EEA/AES historical attendance
# Updates candidate database with conf_attendance column
# Format: EEA2014;AES2016;SI2022
# ==============================================================================

library(tidyverse)

cat("=== Integrating Conference Attendance ===\n\n")

# ==============================================================================
# STEP 1: Load SI2022 attendance (already extracted)
# ==============================================================================

si2022_path <- "/home/simon/Documents/Si Work/PostDoc Work/SI/2022 Valencia/SI2022_attendance_summary.csv"

si2022_attendance <- read_csv(si2022_path, show_col_types = FALSE) %>%
  mutate(conf_code = "SI2022") %>%
  select(name_first, name_last, conf_code)

cat("Loaded SI2022:", nrow(si2022_attendance), "speakers\n")

# ==============================================================================
# STEP 2: Parse conference text files for names
# ==============================================================================

conf_texts_dir <- "/home/simon/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel/outputs/conference_texts"

# Map text files to conference codes
text_files <- tribble(
  ~conf_code, ~filename,
  "EEA2013", "EEA2013.txt",
  "EEA2017", "EEA2017.txt",
  "EEA2021", "EEA2021.txt",
  "EEA2023", "EEA2023.txt",
  "AES2015", "AES2015_oral.txt",
  "AES2015", "AES2015_poster.txt"
) %>%
  mutate(filepath = file.path(conf_texts_dir, filename))

# Function to extract names from conference program text
extract_names_simple <- function(text, conf_code) {

  # Split by lines
  lines <- str_split(text, "\\n")[[1]]

  # Look for author name patterns
  # Common patterns in conference programs:
  # - "Lastname, Firstname"
  # - "Firstname Lastname"
  # - Names followed by institution/email

  # Extract all potential names using regex
  # Pattern: capitalized word followed by comma and another capitalized word
  pattern_lastname_first <- "([A-Z][a-zA-Z'-]+),\\s*([A-Z][a-zA-Z'-]+)"

  # Pattern: Firstname Lastname (both capitalized)
  pattern_firstname_last <- "\\b([A-Z][a-z]+)\\s+([A-Z][a-zA-Z'-]+)\\b"

  # Extract using both patterns
  names_df <- tibble(line = lines) %>%
    # Filter out very short lines and lines that are clearly not names
    filter(
      nchar(line) > 5,
      !str_detect(line, "^\\d+$"),  # Not just numbers
      !str_detect(line, "^(Abstract|Session|Room|Time|Date|Page)\\b")  # Not headers
    ) %>%
    mutate(
      # Try lastname, firstname pattern
      match_lastname_first = str_extract(line, pattern_lastname_first),
      name_last = str_extract(match_lastname_first, "^[^,]+"),
      name_first = str_extract(match_lastname_first, ",\\s*(.+)") %>% str_remove("^,\\s*"),
      # If that failed, try firstname lastname pattern
      match_firstname_last = str_extract(line, pattern_firstname_last),
      name_first_alt = str_extract(match_firstname_last, "^\\S+"),
      name_last_alt = str_extract(match_firstname_last, "\\S+$"),
      # Combine
      name_first = coalesce(name_first, name_first_alt),
      name_last = coalesce(name_last, name_last_alt)
    ) %>%
    select(-match_lastname_first, -match_firstname_last, -name_first_alt, -name_last_alt) %>%
    filter(!is.na(name_first), !is.na(name_last)) %>%
    # Clean names
    mutate(
      name_first = str_trim(name_first),
      name_last = str_trim(name_last),
      # Remove middle initials
      name_first = str_remove(name_first, "\\s+[A-Z]\\.?$"),
      # Remove common non-name words
      name_last = str_remove(name_last, "(University|Institute|Laboratory).*$")
    ) %>%
    # Filter out obvious non-names
    filter(
      nchar(name_first) >= 2,
      nchar(name_last) >= 2,
      !name_first %in% c("The", "And", "For", "With", "From", "This", "That"),
      !name_last %in% c("The", "And", "For", "With", "From", "This", "That")
    ) %>%
    distinct(name_first, name_last) %>%
    mutate(conf_code = conf_code)

  return(names_df)
}

# Process all text files
cat("\nExtracting names from conference programs:\n")

all_conference_names <- list()

for (i in 1:nrow(text_files)) {
  row <- text_files[i, ]

  if (!file.exists(row$filepath)) {
    cat("⚠️  File not found:", row$filepath, "\n")
    next
  }

  text <- read_file(row$filepath)

  if (nchar(text) < 100) {
    cat("⚠️  File too short:", row$conf_code, "\n")
    next
  }

  names_found <- extract_names_simple(text, row$conf_code)

  cat(row$conf_code, ":", nrow(names_found), "names extracted\n")

  all_conference_names[[i]] <- names_found
}

cat("\n")

# Combine all extracted names
conference_names <- bind_rows(all_conference_names)

# ==============================================================================
# STEP 3: Combine SI2022 with historical conferences
# ==============================================================================

cat("=== Combining all conference attendance ===\n")

all_attendance <- bind_rows(
  si2022_attendance,
  conference_names
)

cat("Total attendance records:", nrow(all_attendance), "\n")
cat("Unique conferences:", n_distinct(all_attendance$conf_code), "\n\n")

# Create summary by person
conf_attendance_summary <- all_attendance %>%
  group_by(name_first, name_last) %>%
  summarise(
    conf_attendance = paste(sort(unique(conf_code)), collapse = ";"),
    n_conferences = n_distinct(conf_code),
    .groups = "drop"
  ) %>%
  arrange(desc(n_conferences))

cat("Unique attendees across all conferences:", nrow(conf_attendance_summary), "\n\n")

# Show top frequent attendees
cat("Top 15 most frequent conference attendees:\n")
print(head(conf_attendance_summary, 15))

# ==============================================================================
# STEP 4: Load and update candidate database
# ==============================================================================

cat("\n=== Updating candidate database ===\n")

candidate_db <- read_csv("outputs/candidate_database_phase1.csv", show_col_types = FALSE)

cat("Current candidate database:", nrow(candidate_db), "candidates\n")

# Rename eea_attendance_history to conf_attendance if it exists
if ("eea_attendance_history" %in% names(candidate_db)) {
  candidate_db <- candidate_db %>%
    rename(conf_attendance_old = eea_attendance_history)
}

# Join conference attendance
candidate_db_updated <- candidate_db %>%
  left_join(
    conf_attendance_summary %>% select(name_first, name_last, conf_attendance),
    by = c("name_first", "name_last")
  ) %>%
  # Keep existing if no new data
  mutate(
    conf_attendance = coalesce(conf_attendance, conf_attendance_old)
  ) %>%
  select(-conf_attendance_old)

# Show stats
cat("Candidates with conference history:", sum(!is.na(candidate_db_updated$conf_attendance)), "\n")

# Show distribution by number of conferences
cat("\nDistribution by number of conferences attended:\n")
candidate_db_updated %>%
  filter(!is.na(conf_attendance)) %>%
  mutate(n_conf = str_count(conf_attendance, ";") + 1) %>%
  count(n_conf) %>%
  print()

# ==============================================================================
# STEP 5: Save updated database
# ==============================================================================

cat("\n=== Saving updated database ===\n")

write_csv(candidate_db_updated, "outputs/candidate_database_phase1.csv")
cat("✓ Saved: outputs/candidate_database_phase1.csv\n")

# Also save the full conference attendance table
write_csv(conf_attendance_summary, "outputs/conference_attendance_summary.csv")
cat("✓ Saved: outputs/conference_attendance_summary.csv\n")

# ==============================================================================
# STEP 6: Sample output
# ==============================================================================

cat("\n=== Sample candidates with conference attendance ===\n")
candidate_db_updated %>%
  filter(!is.na(conf_attendance)) %>%
  select(name_first, name_last, discipline_primary, conf_attendance, eea_2025_status) %>%
  arrange(desc(str_count(conf_attendance, ";"))) %>%
  head(20) %>%
  print()

cat("\n✓ Conference Attendance Integration Complete\n")
