#!/usr/bin/env Rscript
# Update search_query_new column in Techniques DB with corrected OR logic for synonyms
#
# Key principle: Since we're downloading ALL papers from Shark-References, we just need
# to search for ANY mention of the technique or its synonyms. Use OR logic to combine
# all relevant terms.
#
# Example:
# - Technique: "Boosted Regression Trees"
# - Synonyms: "BRT, GBM, XGBoost, gradient boosting"
# - Query: BRT OR GBM OR XGBoost OR "gradient boosting" OR "boosted regression"
#
# Usage:
#   Rscript scripts/update_search_queries_with_or_logic.R

library(readxl)
library(writexl)
library(dplyr)
library(stringr)

# File paths
excel_path <- "data/Techniques DB for Panel Review.xlsx"
output_path <- "data/Techniques DB for Panel Review_updated.xlsx"


#' Parse synonyms field into a list of clean terms
parse_synonyms <- function(syn_text) {
  if (is.na(syn_text) || syn_text == "" || syn_text == "NaN") {
    return(character(0))
  }

  # Split on commas or semicolons, trim whitespace
  terms <- str_split(syn_text, "[,;]")[[1]]
  terms <- str_trim(terms)
  terms <- terms[nzchar(terms)]  # Remove empty strings

  return(terms)
}


#' Determine if a term needs quotes
should_quote <- function(term) {
  # Skip if already quoted
  if (str_starts(term, '"') && str_ends(term, '"')) {
    return(FALSE)
  }

  # Quote if contains spaces (multi-word term)
  if (str_detect(term, " ")) {
    return(TRUE)
  }

  # Quote if contains special characters that need exact matching
  if (str_detect(term, "[/\\-&]")) {
    return(TRUE)
  }

  return(FALSE)
}


#' Format a search term with quotes if needed
format_term <- function(term) {
  if (should_quote(term)) {
    # Remove existing quotes if any
    clean <- str_remove_all(term, '"')
    return(paste0('"', clean, '"'))
  }
  return(term)
}


#' Generate corrected search query using OR logic
generate_search_query_new <- function(technique, synonyms_raw) {
  # Parse synonyms
  synonyms <- parse_synonyms(synonyms_raw)

  # Start with all terms
  all_terms <- c(technique, synonyms)

  # Remove duplicates (case-insensitive)
  all_terms_lower <- tolower(all_terms)
  unique_idx <- !duplicated(all_terms_lower)
  unique_terms <- all_terms[unique_idx]

  # Format each term (add quotes if needed)
  formatted_terms <- sapply(unique_terms, format_term, USE.NAMES = FALSE)

  # Join with OR
  query <- paste(formatted_terms, collapse = " OR ")

  return(query)
}


# Main script
cat("Reading:", excel_path, "\n")

# Get all sheet names
sheet_names <- excel_sheets(excel_path)
cat("Sheets found:", paste(sheet_names, collapse = ", "), "\n")

# Read the Full_List sheet
df <- read_excel(excel_path, sheet = "Full_List")
cat("\nProcessing", nrow(df), "techniques from 'Full_List' sheet...\n")

# Generate new search queries
df <- df %>%
  rowwise() %>%
  mutate(search_query_new = generate_search_query_new(technique_name, synonyms)) %>%
  ungroup()

# Read all sheets into a list
all_sheets <- lapply(sheet_names, function(sheet) {
  if (sheet == "Full_List") {
    return(df)
  } else {
    return(read_excel(excel_path, sheet = sheet))
  }
})
names(all_sheets) <- sheet_names

# Write all sheets to new Excel file
write_xlsx(all_sheets, output_path)
cat("\nSaved to:", output_path, "\n")

# Show examples
cat("\n", strrep("=", 80), "\n")
cat("EXAMPLE SEARCH QUERIES:\n")
cat(strrep("=", 80), "\n")

examples <- c(
  "Boosted Regression Trees",
  "Video Analysis",
  "Acoustic Telemetry",
  "Social Network Analysis",
  "Growth Curve Modeling",
  "IUCN Red List Assessment",
  "eDNA",
  "MaxEnt",
  "BORIS"
)

for (tech in examples) {
  row <- df %>% filter(technique_name == tech)
  if (nrow(row) > 0) {
    row <- row[1, ]
    cat("\n", tech, "\n", sep = "")
    if (!is.na(row$synonyms) && row$synonyms != "NaN") {
      cat("  Synonyms:", row$synonyms, "\n")
    }
    cat("  Old:", row$search_query, "\n")
    cat("  NEW:", row$search_query_new, "\n")
  }
}

# Summary statistics
cat("\n", strrep("=", 80), "\n")
cat("SUMMARY:\n")
cat(strrep("=", 80), "\n")
cat("Total techniques processed:", nrow(df), "\n")

# Count techniques with/without synonyms
has_synonyms <- sum(sapply(df$synonyms, function(x) length(parse_synonyms(x)) > 0))
cat("With synonyms:", has_synonyms, "\n")
cat("Without synonyms:", nrow(df) - has_synonyms, "\n")

# Count OR terms
df <- df %>%
  mutate(or_count = str_count(search_query_new, " OR ") + 1)

cat("\nDistribution of OR terms:\n")
or_dist <- table(df$or_count)
print(or_dist)

# Show techniques with most OR terms
cat("\nTechniques with most synonym variations (top 15):\n")
top_or <- df %>%
  arrange(desc(or_count)) %>%
  head(15) %>%
  select(technique_name, or_count, search_query_new)

for (i in 1:nrow(top_or)) {
  row <- top_or[i, ]
  cat("\n", row$technique_name, " (", row$or_count, " terms)\n", sep = "")
  cat("  ", row$search_query_new, "\n", sep = "")
}

cat("\n", strrep("=", 80), "\n")
cat("Done! Updated file saved to:", output_path, "\n")
cat(strrep("=", 80), "\n")
