#!/usr/bin/env Rscript
# ==============================================================================
# Find Missing Names in Abstracts
# ==============================================================================
# Search abstracts for:
# - Renzo (missing surname)
# - WOZEP (missing full name)
# - ?? (x2) from Shark Trust (missing full names)
# ==============================================================================

library(tidyverse)
library(officer)  # For reading DOCX files

cat("=== Searching Abstracts for Missing Names ===\n\n")

# ==============================================================================
# STEP 1: Get list of abstract files
# ==============================================================================

abstracts_dir <- "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel/abstracts"

docx_files <- list.files(abstracts_dir, pattern = "\\.docx$", full.names = TRUE)

cat("Found", length(docx_files), "DOCX files\n\n")

# ==============================================================================
# STEP 2: Function to extract text from DOCX
# ==============================================================================

extract_docx_text <- function(filepath) {
  tryCatch({
    doc <- read_docx(filepath)
    text <- docx_summary(doc)
    # Get all text content
    text_content <- text %>%
      filter(content_type == "paragraph") %>%
      pull(text) %>%
      paste(collapse = " ")
    return(text_content)
  }, error = function(e) {
    cat("⚠️  Error reading:", basename(filepath), "-", e$message, "\n")
    return(NA_character_)
  })
}

# ==============================================================================
# STEP 3: Search for target names
# ==============================================================================

cat("Searching for target names...\n\n")

search_results <- tibble(
  filepath = docx_files,
  filename = basename(docx_files)
) %>%
  mutate(
    text = map_chr(filepath, extract_docx_text),
    # Search for Renzo
    has_renzo = str_detect(text, regex("\\brenzo\\b", ignore_case = TRUE)),
    # Search for WOZEP
    has_wozep = str_detect(text, regex("wozep", ignore_case = TRUE)),
    # Search for Shark Trust
    has_shark_trust = str_detect(text, regex("shark\\s+trust", ignore_case = TRUE))
  )

# ==============================================================================
# STEP 4: Show matches
# ==============================================================================

cat("=== Files mentioning 'Renzo' ===\n")
renzo_files <- search_results %>%
  filter(has_renzo) %>%
  select(filename, text)

if (nrow(renzo_files) > 0) {
  for (i in 1:nrow(renzo_files)) {
    cat("\nFile:", renzo_files$filename[i], "\n")
    # Extract context around "Renzo"
    text_snippet <- str_extract(renzo_files$text[i],
                                "(?i).{0,100}renzo.{0,100}")
    cat("Context:", text_snippet, "\n")
  }
} else {
  cat("No files found mentioning 'Renzo'\n")
}

cat("\n\n=== Files mentioning 'WOZEP' ===\n")
wozep_files <- search_results %>%
  filter(has_wozep) %>%
  select(filename, text)

if (nrow(wozep_files) > 0) {
  for (i in 1:nrow(wozep_files)) {
    cat("\nFile:", wozep_files$filename[i], "\n")
    # Extract context around "WOZEP"
    text_snippet <- str_extract(wozep_files$text[i],
                                "(?i).{0,100}wozep.{0,100}")
    cat("Context:", text_snippet, "\n")
  }
} else {
  cat("No files found mentioning 'WOZEP'\n")
}

cat("\n\n=== Files mentioning 'Shark Trust' ===\n")
shark_trust_files <- search_results %>%
  filter(has_shark_trust) %>%
  select(filename, text)

if (nrow(shark_trust_files) > 0) {
  for (i in 1:nrow(shark_trust_files)) {
    cat("\nFile:", shark_trust_files$filename[i], "\n")
    # Extract context around "Shark Trust"
    text_snippet <- str_extract(shark_trust_files$text[i],
                                "(?i).{0,150}shark\\s+trust.{0,150}")
    cat("Context:", text_snippet, "\n")

    # Try to extract author names from this file
    # Look for common author patterns
    author_pattern <- "([A-Z][a-z]+\\s+[A-Z][a-z]+(?:\\s+[A-Z][a-z]+)?)"
    authors <- str_extract_all(shark_trust_files$text[i], author_pattern)[[1]] %>%
      unique()
    cat("Potential authors:", paste(head(authors, 10), collapse = ", "), "\n")
  }
} else {
  cat("No files found mentioning 'Shark Trust'\n")
}

# ==============================================================================
# STEP 5: Check filename O_28 (Cat Gordon Shark Trust)
# ==============================================================================

cat("\n\n=== Checking O_28 (Cat Gordon Shark Trust) ===\n")

cat_gordon_file <- docx_files[str_detect(docx_files, "O_28")]

if (length(cat_gordon_file) > 0) {
  cat("Found:", basename(cat_gordon_file), "\n")
  text <- extract_docx_text(cat_gordon_file)

  # Look for co-authors
  cat("\nFull text excerpt (first 500 chars):\n")
  cat(str_sub(text, 1, 500), "\n")

  # Extract all capitalized names
  names_found <- str_extract_all(text, "\\b([A-Z][a-z]+(?:\\s+[A-Z][a-z]+)+)\\b")[[1]] %>%
    unique()

  cat("\n\nPotential names found:\n")
  print(names_found)
}

# ==============================================================================
# STEP 6: Save results
# ==============================================================================

cat("\n\n=== Saving search results ===\n")

search_summary <- search_results %>%
  filter(has_renzo | has_wozep | has_shark_trust) %>%
  select(filename, has_renzo, has_wozep, has_shark_trust)

write_csv(search_summary, "outputs/missing_names_search_results.csv")
cat("✓ Saved: outputs/missing_names_search_results.csv\n")

cat("\n✓ Search Complete\n")
