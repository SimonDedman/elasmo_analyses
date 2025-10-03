#!/usr/bin/env Rscript
# ==============================================================================
# Extract Conference Attendance from Historical Programs
# ==============================================================================
# Extract presenter names from EEA and AES conference programs
# Create conf_attendance column format: EEA2014;AES2016;SI2022
# ==============================================================================

library(tidyverse)
library(pdftools)
library(readtext)

# ==============================================================================
# STEP 1: Define conference files
# ==============================================================================

cat("=== Extracting Conference Attendance ===\n\n")

conf_history_path <- "/home/simon/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel/EEA History"

# Map files to conferences
conference_files <- tribble(
  ~conference, ~year, ~filepath,
  "EEA", 2013, file.path(conf_history_path, "EEA 2013 Plymouth/2013.11.01 EEA 17 Plymouth Abstract Book.pdf"),
  "EEA", 2014, file.path(conf_history_path, "Programme EEA2014_FINAL.docx"),
  "AES", 2015, file.path(conf_history_path, "AES 2015 Reno/Oral Presentations_5 June 2015.pdf"),
  "AES", 2015, file.path(conf_history_path, "AES 2015 Reno/Poster Presentations_5 June 2015.pdf"),
  "EEA", 2017, file.path(conf_history_path, "EEA2017_program_provisional.pdf"),
  "EEA", 2021, file.path(conf_history_path, "EEA2021-program.pdf"),
  "EEA", 2023, file.path(conf_history_path, "eea2023programme.pdf"),
  "AES", 2024, file.path(conf_history_path, "AES2024 Pittsburgh.docx")
) %>%
  mutate(
    conf_code = paste0(conference, year),
    exists = file.exists(filepath)
  )

cat("Conference files identified:\n")
print(conference_files %>% select(conf_code, exists))
cat("\n")

# ==============================================================================
# STEP 2: Extract text from PDFs
# ==============================================================================

extract_pdf_text <- function(filepath) {
  tryCatch({
    text <- pdf_text(filepath)
    paste(text, collapse = "\n")
  }, error = function(e) {
    cat("Error reading PDF:", filepath, "\n", e$message, "\n")
    return(NA_character_)
  })
}

# ==============================================================================
# STEP 3: Extract text from DOCX
# ==============================================================================

extract_docx_text <- function(filepath) {
  tryCatch({
    # Use readtext package
    doc <- readtext(filepath)
    doc$text
  }, error = function(e) {
    cat("Error reading DOCX:", filepath, "\n", e$message, "\n")
    return(NA_character_)
  })
}

# ==============================================================================
# STEP 4: Extract presenter names from text
# ==============================================================================

# Function to extract names from conference program text
extract_names_from_program <- function(text, conf_code) {

  # Different conferences have different formats
  # Common patterns:
  # - "Author, A., Author, B." (author list format)
  # - "Firstname Lastname" (presentation list)
  # - "LASTNAME, Firstname" (some programs)

  # Strategy: Look for patterns that indicate presenter/author names
  # Split by lines first
  lines <- str_split(text, "\n")[[1]]

  # Filter lines that likely contain names
  # Look for lines with typical name patterns
  name_lines <- lines %>%
    # Remove very short lines
    .[nchar(.) > 10] %>%
    # Look for lines with capital letters (names)
    .[str_detect(., "[A-Z][a-z]+")]

  # Extract names using regex patterns
  # Pattern 1: Lastname, Firstname format
  pattern1 <- "([A-Z][a-zA-Z-]+),\\s*([A-Z][a-z]+)"
  # Pattern 2: Firstname Lastname format
  pattern2 <- "\\b([A-Z][a-z]+)\\s+([A-Z][a-zA-Z-]+)\\b"

  names_extracted <- tibble(
    conf_code = conf_code,
    raw_line = name_lines
  ) %>%
    mutate(
      # Try pattern 1 first
      name_last = str_extract(raw_line, pattern1) %>% str_extract("^[^,]+"),
      name_first = str_extract(raw_line, pattern1) %>% str_extract("(?<=,\\s).*"),
      # If pattern 1 failed, try pattern 2
      name_first = if_else(is.na(name_first),
                           str_extract(raw_line, pattern2) %>% str_extract("^\\S+"),
                           name_first),
      name_last = if_else(is.na(name_last),
                          str_extract(raw_line, pattern2) %>% str_extract("\\S+$"),
                          name_last)
    ) %>%
    filter(!is.na(name_first), !is.na(name_last)) %>%
    # Clean up names
    mutate(
      name_first = str_trim(name_first),
      name_last = str_trim(name_last),
      # Remove middle initials
      name_first = str_remove(name_first, "\\s+[A-Z]\\.?$")
    ) %>%
    distinct(name_first, name_last, .keep_all = TRUE)

  return(names_extracted)
}

# ==============================================================================
# STEP 5: Process each conference file
# ==============================================================================

cat("Extracting attendance from conference programs...\n\n")

all_attendance <- list()

for (i in 1:nrow(conference_files)) {
  row <- conference_files[i, ]

  if (!row$exists) {
    cat("⚠️  File not found:", row$conf_code, "\n")
    next
  }

  cat("Processing:", row$conf_code, "-", basename(row$filepath), "\n")

  # Extract text based on file type
  if (str_ends(row$filepath, ".pdf")) {
    text <- extract_pdf_text(row$filepath)
  } else if (str_ends(row$filepath, ".docx")) {
    text <- extract_docx_text(row$filepath)
  } else {
    cat("  Unknown file type, skipping\n")
    next
  }

  if (is.na(text) || nchar(text) < 100) {
    cat("  Failed to extract text or file too short\n")
    next
  }

  # Extract names
  names_found <- extract_names_from_program(text, row$conf_code)

  cat("  Found", nrow(names_found), "potential names\n")

  all_attendance[[i]] <- names_found
}

cat("\n")

# ==============================================================================
# STEP 6: Combine all attendance
# ==============================================================================

cat("=== Combining attendance records ===\n")

attendance_combined <- bind_rows(all_attendance)

cat("Total attendance records:", nrow(attendance_combined), "\n")
cat("Unique conferences:", n_distinct(attendance_combined$conf_code), "\n")

# Show sample
cat("\nSample records:\n")
print(head(attendance_combined %>% select(conf_code, name_first, name_last), 20))

# ==============================================================================
# STEP 7: Create conf_attendance strings
# ==============================================================================

cat("\n=== Creating conf_attendance strings ===\n")

# Group by person and create semicolon-separated list
conf_attendance_summary <- attendance_combined %>%
  group_by(name_first, name_last) %>%
  summarise(
    conf_attendance = paste(sort(unique(conf_code)), collapse = ";"),
    n_conferences = n_distinct(conf_code),
    .groups = "drop"
  ) %>%
  arrange(desc(n_conferences))

cat("Unique attendees:", nrow(conf_attendance_summary), "\n")

cat("\nTop 10 most frequent attendees:\n")
print(head(conf_attendance_summary, 10))

# ==============================================================================
# STEP 8: Save outputs
# ==============================================================================

cat("\n=== Saving outputs ===\n")

output_dir <- "/home/simon/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel/outputs"
dir.create(output_dir, showWarnings = FALSE)

# Save full attendance records
write_csv(attendance_combined, file.path(output_dir, "conference_attendance_full.csv"))
cat("✓ Saved:", file.path(output_dir, "conference_attendance_full.csv"), "\n")

# Save summary
write_csv(conf_attendance_summary, file.path(output_dir, "conference_attendance_summary.csv"))
cat("✓ Saved:", file.path(output_dir, "conference_attendance_summary.csv"), "\n")

# ==============================================================================
# STEP 9: Statistics
# ==============================================================================

cat("\n=== Statistics by Conference ===\n")
attendance_combined %>%
  count(conf_code, name = "attendees") %>%
  arrange(conf_code) %>%
  print()

cat("\n✓ Conference Attendance Extraction Complete\n")
cat("\nNext step: Integrate into candidate database\n")
