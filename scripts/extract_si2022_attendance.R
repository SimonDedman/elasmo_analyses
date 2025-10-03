#!/usr/bin/env Rscript
# ==============================================================================
# Extract SI2022 Attendance from Video Files
# ==============================================================================

library(tidyverse)

# ==============================================================================
# STEP 1: Get all video files
# ==============================================================================

cat("=== Extracting SI2022 Attendance ===\n\n")

si_video_path <- "/home/simon/Documents/Si Work/PostDoc Work/FIU/Meeting Files/2022-10-20 SI2022/SI2022 Videos"

# Get all video files recursively
video_files <- list.files(
  path = si_video_path,
  pattern = "\\.(mp4|mov|avi|MP4|MOV|AVI)$",
  recursive = TRUE,
  full.names = TRUE
)

cat("Found", length(video_files), "video files\n\n")

# ==============================================================================
# STEP 2: Parse filenames
# ==============================================================================

# Filename format: SI2022-10-21_64_Carlo-Zampieri_Eval-bioas-describ-ecosystem-roles-elasmos-foodweb-models.mp4
# Components:
# - Date: SI2022-10-21
# - Number: 64
# - Speaker(s): Carlo-Zampieri (can be multiple with underscores)
# - Title: Eval-bioas-describ-ecosystem-roles-elasmos-foodweb-models

si_attendance <- tibble(filepath = video_files) %>%
  mutate(
    filename = basename(filepath),
    folder = dirname(filepath),
    # Extract date
    date = str_extract(filename, "SI2022-\\d{2}-\\d{2}"),
    # Extract talk number
    talk_number = str_extract(filename, "(?<=_)\\d+(?=_)"),
    # Extract session from folder structure
    session_folder = basename(folder),
    # Extract everything after date and number
    rest = str_remove(filename, "SI2022-\\d{2}-\\d{2}_\\d+_"),
    # Remove file extension
    rest = str_remove(rest, "\\.(mp4|mov|avi|MP4|MOV|AVI)$"),
    # Split by underscore to separate speakers from title
    # First part(s) before multiple words = speakers
    # Assume speakers have format Name-Surname or Name_Name-Surname
    speakers_raw = str_extract(rest, "^[A-Za-z-]+(?:_[A-Za-z-]+)*(?=_[A-Z])"),
    # If no clear speaker pattern, take first 2-3 underscore segments
    speakers_raw = if_else(
      is.na(speakers_raw),
      str_extract(rest, "^[^_]+(?:_[^_]+){0,2}"),
      speakers_raw
    ),
    # Title is everything after speakers
    title_raw = str_remove(rest, paste0("^", str_replace_all(speakers_raw, fixed("("), "\\("), "_?")),
    # Clean up title
    title_partial = str_replace_all(title_raw, "-", " "),
    title_partial = str_to_sentence(title_partial)
  ) %>%
  # Remove rows where parsing failed
  filter(!is.na(speakers_raw))

cat("Parsed", nrow(si_attendance), "presentations\n\n")

# ==============================================================================
# STEP 3: Extract individual speakers
# ==============================================================================

# Split multiple speakers (separated by underscores)
si_speakers <- si_attendance %>%
  separate_rows(speakers_raw, sep = "_") %>%
  mutate(
    # Convert Name-Surname format to Name, Surname
    name_parts = str_split(speakers_raw, "-"),
    name_first = map_chr(name_parts, ~.x[1]),
    name_last = map_chr(name_parts, ~if(length(.x) > 1) .x[2] else NA_character_),
    # Handle cases with more than 2 parts (e.g., multiple surnames)
    name_last = map2_chr(name_parts, name_last, ~if(length(.x) > 2) paste(.x[-1], collapse = " ") else .y)
  ) %>%
  select(
    date, talk_number, session_folder,
    name_first, name_last,
    title_partial
  ) %>%
  # Remove invalid entries
  filter(!is.na(name_first), nchar(name_first) > 1)

cat("Extracted", nrow(si_speakers), "speaker records\n")
cat("Unique speakers:", n_distinct(si_speakers$name_first, si_speakers$name_last), "\n\n")

# ==============================================================================
# STEP 4: Map sessions to 8-discipline framework
# ==============================================================================

# Session mapping based on folder names
session_discipline_mapping <- tribble(
  ~session_pattern, ~discipline_primary, ~session_name,
  "Applied Elasmo Science", "1. Biology, Life History, & Health", "Applied Elasmobranch Science",
  "Threatened Species", "7. Conservation Policy & Human Dimensions", "Threatened Species & Threats",
  "Mediterranean Species", "6. Fisheries, Stock Assessment, & Management", "Mediterranean Species & Fisheries",
  "COP19", "7. Conservation Policy & Human Dimensions", "COP19 & Special Sessions",
  "Human Dimensions", "7. Conservation Policy & Human Dimensions", "Human Dimensions & Communications",
  "Keynote", NA_character_, "Keynote",
  "Movement", "5. Movement, Space Use, & Habitat Modeling", "Movement & Behavior",
  "Spatial", "5. Movement, Space Use, & Habitat Modeling", "Spatial Ecology",
  "Genetics", "4. Genetics, Genomics, & eDNA", "Genetics & Genomics",
  "Diet|Trophic|Feeding", "3. Trophic & Community Ecology", "Trophic Ecology",
  "Fisheries|Stock", "6. Fisheries, Stock Assessment, & Management", "Fisheries & Management",
  "Data|Methods|Analysis", "8. Data Science & Integrative Methods", "Data Science & Methods",
  "Behavior|Sensory", "2. Behaviour & Sensory Ecology", "Behaviour & Sensory Ecology"
)

# Map sessions to disciplines
si_speakers_mapped <- si_speakers %>%
  mutate(
    discipline_primary = NA_character_,
    session_name = session_folder
  )

# Apply mapping
for (i in 1:nrow(session_discipline_mapping)) {
  pattern <- session_discipline_mapping$session_pattern[i]
  disc <- session_discipline_mapping$discipline_primary[i]
  sess_name <- session_discipline_mapping$session_name[i]

  si_speakers_mapped <- si_speakers_mapped %>%
    mutate(
      discipline_primary = if_else(
        str_detect(session_folder, regex(pattern, ignore_case = TRUE)) & is.na(discipline_primary),
        disc,
        discipline_primary
      ),
      session_name = if_else(
        str_detect(session_folder, regex(pattern, ignore_case = TRUE)),
        sess_name,
        session_name
      )
    )
}

# ==============================================================================
# STEP 5: Create summary table
# ==============================================================================

si2022_summary <- si_speakers_mapped %>%
  distinct(name_first, name_last, .keep_all = TRUE) %>%
  select(
    name_first,
    name_last,
    discipline_primary,
    session_name,
    title_partial
  ) %>%
  arrange(name_last, name_first)

cat("=== SI2022 Attendance Summary ===\n")
cat("Total unique speakers:", nrow(si2022_summary), "\n\n")

cat("Speakers by Discipline (estimated):\n")
si2022_summary %>%
  count(discipline_primary, sort = TRUE) %>%
  print(n = Inf)

# ==============================================================================
# STEP 6: Save outputs
# ==============================================================================

cat("\n=== Saving Outputs ===\n")

output_dir <- "/home/simon/Documents/Si Work/PostDoc Work/SI/2022 Valencia"
dir.create(output_dir, showWarnings = FALSE, recursive = TRUE)

# Save full dataset
write_csv(si_speakers_mapped, file.path(output_dir, "SI2022_attendance_full.csv"))
cat("✓ Saved:", file.path(output_dir, "SI2022_attendance_full.csv"), "\n")

# Save summary
write_csv(si2022_summary, file.path(output_dir, "SI2022_attendance_summary.csv"))
cat("✓ Saved:", file.path(output_dir, "SI2022_attendance_summary.csv"), "\n")

# ==============================================================================
# STEP 7: Sample output
# ==============================================================================

cat("\n=== Sample Speakers (first 20) ===\n")
si2022_summary %>%
  head(20) %>%
  print()

cat("\n✓ SI2022 Attendance Extraction Complete\n")
