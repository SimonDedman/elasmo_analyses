#!/usr/bin/env Rscript
# ==============================================================================
# Classify Unclassified Presentations and Highlight Changes
# ==============================================================================

library(tidyverse)
library(readxl)
library(openxlsx)

# ==============================================================================
# STEP 1: Load Current Data
# ==============================================================================

excel_path <- here::here("Final Speakers EEA 2025.xlsx")

# Read all sheets
oral_ppt <- read_excel(excel_path, sheet = "Oral PPT")
posters <- read_excel(excel_path, sheet = "Posters")
add_posters <- read_excel(excel_path, sheet = "Additional Posters")

cat("=== Loading Data ===\n")
cat("Oral PPT:", nrow(oral_ppt), "rows\n")
cat("Posters:", nrow(posters), "rows\n")
cat("Additional Posters:", nrow(add_posters), "rows\n\n")

# ==============================================================================
# STEP 2: Define Classifications
# ==============================================================================

# Based on manual review of titles and topics
classifications <- tribble(
  ~first_name, ~last_name, ~discipline,
  # Oral presentations
  "Simon", "Dedman", NA_character_,  # Not speaking

  # Posters
  "Harriet", "Allen", "7. Conservation Policy & Human Dimensions",  # Citizen science
  "Sarai", "Burman", "7. Conservation Policy & Human Dimensions",  # Education/citizen science
  "Aitor", "Campos Sosa", "6. Fisheries, Stock Assessment, & Management",  # Bycatch rehabilitation
  "Maite", "Erauskin-Extramiana", "5. Movement, Space Use, & Habitat Modeling",  # Habitat significance
  "Maisie", "Evans", "6. Fisheries, Stock Assessment, & Management",  # Fisheries management
  "Elena", "Fernández Corredor", "3. Trophic & Community Ecology",  # Trophic niche (poster #1)
  "Cat", "Gordon", "7. Conservation Policy & Human Dimensions",  # Human-wildlife coexistence
  "Anouk", "Langerak", "4. Genetics, Genomics, & eDNA",  # Genomics/eDNA
  "Guido", "Leurs", "5. Movement, Space Use, & Habitat Modeling",  # Space use/habitat
  "Benjamin", "Marsaly", "2. Behaviour & Sensory Ecology",  # Behavioral ecology
  "Claudia", "Meneses", "8. Data Science & Integrative Methods",  # Data management tool
  "Roxani", "Naasan Aga Spyridopoulou", "7. Conservation Policy & Human Dimensions",  # Species protection
  "Mark", "Packer", "7. Conservation Policy & Human Dimensions",  # Collaboration/outreach
  "David", "Ruiz-García", "6. Fisheries, Stock Assessment, & Management",  # Bycatch mortality
  "Nikoletta", "Sidiropoulou", "7. Conservation Policy & Human Dimensions",  # Habitat restoration (poster)
  "Sebastian", "Uhlmann", "6. Fisheries, Stock Assessment, & Management",  # Bycatch mitigation
  "Carla", "Valdés", "1. Biology, Life History, & Health",  # Health/injury assessment
  "Erwin", "Winter", "5. Movement, Space Use, & Habitat Modeling",  # Movement/connectivity
  "Lucas", "Zaccagnini", "5. Movement, Space Use, & Habitat Modeling",  # Spatial ecology/telemetry
  "Peter", "Gausmann", "1. Biology, Life History, & Health",  # Life history/ecology
  "Yaara", "Grossmark", "7. Conservation Policy & Human Dimensions",  # Human-wildlife interactions

  # Additional Posters
  "Hettie", "Brown", "7. Conservation Policy & Human Dimensions",  # Conservation/monitoring
  "Kirsti", "Burnett", "4. Genetics, Genomics, & eDNA",  # Genomics
  "Juliette Elisa", "Debarge", "2. Behaviour & Sensory Ecology",  # Social behavior
  "Joanna", "Desmidt", "6. Fisheries, Stock Assessment, & Management",  # Evidence-based management
  "Roel", "Fiselier", "6. Fisheries, Stock Assessment, & Management",  # Fisheries catch composition
  "Emina", "Karalic", "1. Biology, Life History, & Health",  # Nursery/life history
  "Carlotta", "Mazzoldi", "5. Movement, Space Use, & Habitat Modeling",  # Tracking/movement
  "Gustavo", "Montero Hernández", NA_character_,  # No title - cannot classify
  "Mišo", "Pavičić", "6. Fisheries, Stock Assessment, & Management",  # Fisheries
  "Jaime", "Penadés-Suay", "5. Movement, Space Use, & Habitat Modeling",  # Distribution/biogeography
  "Kidé", "Saïkou Oumar", "1. Biology, Life History, & Health",  # Reproduction/life history
  "Manoah", "Touzot", "1. Biology, Life History, & Health",  # Health/pollution (microplastics)
  "Jaquelino", "Varela", NA_character_,  # No title - cannot classify
  "Francesca Maria", "Veneziano", "5. Movement, Space Use, & Habitat Modeling",  # Distribution/biogeography
  "Andrea", "Vera Espinosa", "5. Movement, Space Use, & Habitat Modeling",  # Spatiotemporal distribution
  "Nicolas", "Ziani", "1. Biology, Life History, & Health",  # Reproduction/life history
  "Eleonora", "Zuccollo", NA_character_,  # No title - cannot classify
  "Manuel", "Seixas", "4. Genetics, Genomics, & eDNA",  # Genomics/immunology
  "Junge", "Claudia", NA_character_  # No title - cannot classify
)

# Note: Harriet Allen appears twice (poster + add_poster), handled separately
# Note: Elena Fernández Corredor appears twice with different topics
classifications_elena_add <- "6. Fisheries, Stock Assessment, & Management"  # For add_poster (fishing/conservation)
classifications_nikoletta_add <- "1. Biology, Life History, & Health"  # For add_poster (nursery area)

cat("=== Classifications Defined ===\n")
cat("Total classifications:", nrow(classifications), "\n")
cat("NA classifications:", sum(is.na(classifications$discipline)), "\n\n")

# ==============================================================================
# STEP 3: Apply Classifications to Each Sheet
# ==============================================================================

apply_classifications <- function(df, sheet_name) {
  # Check if Analysis Discipline column exists, if not create it
  if (!"Analysis Discipline" %in% names(df)) {
    df <- df %>% mutate(`Analysis Discipline` = NA_character_)
  }

  df_updated <- df %>%
    left_join(
      classifications,
      by = c("Name (First)" = "first_name", "Name (Last)" = "last_name")
    ) %>%
    mutate(
      # Mark rows that will be updated
      was_updated = is.na(`Analysis Discipline`) & !is.na(discipline),
      # Update Analysis Discipline
      `Analysis Discipline` = if_else(
        is.na(`Analysis Discipline`) & !is.na(discipline),
        discipline,
        `Analysis Discipline`
      )
    ) %>%
    select(-discipline)

  # Special handling for duplicates
  if (sheet_name == "Additional Posters") {
    # Elena Fernández Corredor - add_poster gets different classification
    df_updated <- df_updated %>%
      mutate(
        `Analysis Discipline` = if_else(
          `Name (First)` == "Elena" & `Name (Last)` == "Fernández Corredor" & was_updated,
          classifications_elena_add,
          `Analysis Discipline`
        )
      )

    # Nikoletta Sidiropoulou - add_poster gets nursery classification
    df_updated <- df_updated %>%
      mutate(
        `Analysis Discipline` = if_else(
          `Name (First)` == "Nikoletta" & `Name (Last)` == "Sidiropoulou" & was_updated,
          classifications_nikoletta_add,
          `Analysis Discipline`
        )
      )
  }

  n_updated <- sum(df_updated$was_updated, na.rm = TRUE)
  cat("Sheet:", sheet_name, "- Updated", n_updated, "rows\n")

  return(df_updated)
}

oral_ppt_updated <- apply_classifications(oral_ppt, "Oral PPT")
posters_updated <- apply_classifications(posters, "Posters")
add_posters_updated <- apply_classifications(add_posters, "Additional Posters")

cat("\n")

# ==============================================================================
# STEP 4: Create Workbook with Highlighting
# ==============================================================================

cat("=== Creating Workbook with Highlighting ===\n")

# Create workbook
wb <- loadWorkbook(excel_path)

# Define yellow highlight style
highlight_style <- createStyle(fgFill = "#FFFF00", fontColour = "#000000")

# Function to highlight updated cells
highlight_updates <- function(wb, sheet_name, df_updated) {
  # Find Analysis Discipline column
  col_idx <- which(names(df_updated) == "Analysis Discipline")

  if (length(col_idx) == 0) {
    cat("Warning: No 'Analysis Discipline' column found in", sheet_name, "\n")
    return(wb)
  }

  # Find rows that were updated
  updated_rows <- which(df_updated$was_updated)

  if (length(updated_rows) > 0) {
    # Add 1 to row numbers to account for header row in Excel
    excel_rows <- updated_rows + 1

    # Apply highlighting
    for (row in excel_rows) {
      addStyle(wb, sheet = sheet_name, style = highlight_style,
               rows = row, cols = col_idx, gridExpand = FALSE, stack = TRUE)
    }

    cat("Highlighted", length(updated_rows), "cells in", sheet_name, "\n")
  } else {
    cat("No updates to highlight in", sheet_name, "\n")
  }

  return(wb)
}

# Remove was_updated column before writing
oral_ppt_final <- oral_ppt_updated %>% select(-was_updated)
posters_final <- posters_updated %>% select(-was_updated)
add_posters_final <- add_posters_updated %>% select(-was_updated)

# Write updated data
writeData(wb, sheet = "Oral PPT", x = oral_ppt_final, startRow = 1, startCol = 1)
writeData(wb, sheet = "Posters", x = posters_final, startRow = 1, startCol = 1)
writeData(wb, sheet = "Additional Posters", x = add_posters_final, startRow = 1, startCol = 1)

# Apply highlighting
wb <- highlight_updates(wb, "Oral PPT", oral_ppt_updated)
wb <- highlight_updates(wb, "Posters", posters_updated)
wb <- highlight_updates(wb, "Additional Posters", add_posters_updated)

# ==============================================================================
# STEP 5: Save Updated Workbook
# ==============================================================================

# Create backup of original file
backup_path <- str_replace(excel_path, "\\.xlsx$", "_BKUP.xlsx")
if (!file.exists(backup_path)) {
  file.copy(excel_path, backup_path)
  cat("\n✓ Backup saved to:", backup_path, "\n")
}

# Save updated file
saveWorkbook(wb, excel_path, overwrite = TRUE)
cat("✓ Updated file saved to:", excel_path, "\n")

# ==============================================================================
# STEP 6: Show Summary
# ==============================================================================

cat("\n=== Summary ===\n")
cat("Total presentations updated:",
    sum(oral_ppt_updated$was_updated, na.rm = TRUE) +
    sum(posters_updated$was_updated, na.rm = TRUE) +
    sum(add_posters_updated$was_updated, na.rm = TRUE), "\n")

cat("\nUpdated cells are highlighted in YELLOW\n")
cat("\nNext step: Re-run create_discipline_summary.R to update outputs\n")

# ==============================================================================
# COMPLETE
# ==============================================================================
