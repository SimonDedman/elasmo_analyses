#!/usr/bin/env Rscript
# ==============================================================================
# Apply Yellow Highlighting to ALL Updated Analysis Discipline Cells
# ==============================================================================

library(tidyverse)
library(readxl)
library(openxlsx)

# ==============================================================================
# STEP 1: Load Excel File
# ==============================================================================

excel_path <- here::here("Final Speakers EEA 2025.xlsx")
wb <- loadWorkbook(excel_path)

cat("=== Applying Complete Highlighting ===\n\n")

# ==============================================================================
# STEP 2: Define Yellow Highlight Style
# ==============================================================================

highlight_style <- createStyle(fgFill = "#FFFF00", fontColour = "#000000")

# ==============================================================================
# STEP 3: Highlight Oral PPT Sheet
# ==============================================================================

oral_ppt <- read_excel(excel_path, sheet = "Oral PPT")

# Find Analysis Discipline column
oral_col_idx <- which(names(oral_ppt) == "Analysis Discipline")

# All rows with non-NA Analysis Discipline should be highlighted (except Simon Dedman)
oral_highlight_rows <- which(!is.na(oral_ppt$`Analysis Discipline`))

if (length(oral_highlight_rows) > 0 && length(oral_col_idx) > 0) {
  excel_rows <- oral_highlight_rows + 1  # +1 for header

  for (row in excel_rows) {
    addStyle(wb, sheet = "Oral PPT", style = highlight_style,
             rows = row, cols = oral_col_idx, gridExpand = FALSE, stack = TRUE)
  }

  cat("✓ Oral PPT:", length(oral_highlight_rows), "cells highlighted\n")
}

# ==============================================================================
# STEP 4: Highlight Posters Sheet
# ==============================================================================

posters <- read_excel(excel_path, sheet = "Posters")

# Find Analysis Discipline column
poster_col_idx <- which(names(posters) == "Analysis Discipline")

# All rows with non-NA Analysis Discipline should be highlighted
poster_highlight_rows <- which(!is.na(posters$`Analysis Discipline`))

if (length(poster_highlight_rows) > 0 && length(poster_col_idx) > 0) {
  excel_rows <- poster_highlight_rows + 1

  for (row in excel_rows) {
    addStyle(wb, sheet = "Posters", style = highlight_style,
             rows = row, cols = poster_col_idx, gridExpand = FALSE, stack = TRUE)
  }

  cat("✓ Posters:", length(poster_highlight_rows), "cells highlighted\n")
}

# ==============================================================================
# STEP 5: Highlight Additional Posters Sheet
# ==============================================================================

add_posters <- read_excel(excel_path, sheet = "Additional Posters")

# Find Analysis Discipline column
add_poster_col_idx <- which(names(add_posters) == "Analysis Discipline")

# All rows with non-NA Analysis Discipline should be highlighted
add_poster_highlight_rows <- which(!is.na(add_posters$`Analysis Discipline`))

if (length(add_poster_highlight_rows) > 0 && length(add_poster_col_idx) > 0) {
  excel_rows <- add_poster_highlight_rows + 1

  for (row in excel_rows) {
    addStyle(wb, sheet = "Additional Posters", style = highlight_style,
             rows = row, cols = add_poster_col_idx, gridExpand = FALSE, stack = TRUE)
  }

  cat("✓ Additional Posters:", length(add_poster_highlight_rows), "cells highlighted\n")
}

# ==============================================================================
# STEP 6: Highlight Data Sheet
# ==============================================================================

data_sheet <- read_excel(excel_path, sheet = "data")

# Find Analysis Discipline column
data_col_idx <- which(names(data_sheet) == "Analysis Discipline")

# Highlight all rows with disciplines in 8-discipline schema format (starts with digit)
data_highlight_rows <- which(str_detect(data_sheet$`Analysis Discipline`, "^[1-8]\\."))

if (length(data_highlight_rows) > 0 && length(data_col_idx) > 0) {
  excel_rows <- data_highlight_rows + 1

  for (row in excel_rows) {
    addStyle(wb, sheet = "data", style = highlight_style,
             rows = row, cols = data_col_idx, gridExpand = FALSE, stack = TRUE)
  }

  cat("✓ Data sheet:", length(data_highlight_rows), "cells highlighted\n")
}

# ==============================================================================
# STEP 7: Save Workbook
# ==============================================================================

saveWorkbook(wb, excel_path, overwrite = TRUE)

cat("\n✓ Saved:", excel_path, "\n")
cat("\nAll Analysis Discipline cells using the 8-discipline schema are now YELLOW\n")

# ==============================================================================
# COMPLETE
# ==============================================================================
