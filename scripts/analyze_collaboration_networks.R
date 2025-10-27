#!/usr/bin/env Rscript
# ============================================================================
# COLLABORATION NETWORK ANALYSIS
# ============================================================================
# Purpose: Analyze co-authorship, institution, and country collaboration
#          networks in shark research
#
# Analyses:
#   1) Co-authorship network (author-author connections)
#   2) Institution collaboration network
#   3) Cross-country partnerships
#   4) Network metrics and statistics
#
# Author: EEA 2025 Data Panel
# Date: 2025-10-26
# ============================================================================

library(tidyverse)
library(igraph)
library(scales)

cat("\n")
cat(paste0(strrep("=", 80), "\n"))
cat("COLLABORATION NETWORK ANALYSIS\n")
cat(paste0(strrep("=", 80), "\n\n"))

# ============================================================================
# LOAD DATA
# ============================================================================

cat("=== LOADING DATA ===\n")

# Load author data
authors <- read_csv(
  "outputs/researchers/paper_authors_full.csv",
  show_col_types = FALSE
)

# Load country data
papers_per_country <- read_csv(
  "outputs/analysis/papers_per_country.csv",
  show_col_types = FALSE
)

cat(sprintf("Loaded %s paper-author records\n", comma(nrow(authors))))
cat(sprintf("Loaded %s countries with data\n", nrow(papers_per_country)))

# ============================================================================
# DATA CLEANING
# ============================================================================

cat("\n=== CLEANING DATA ===\n")

# Filter out obvious non-author entries
# Remove single-word entries that are likely location names or artifacts
authors_clean <- authors %>%
  filter(
    !is.na(author_name),
    author_name != "",
    # Remove common artifacts (dates, locations, keywords)
    !author_name %in% c(
      "School", "University", "Department", "Laboratory", "Institute",
      "College", "Hospital", "Center", "Centre", "Research", "Marine",
      "Biological", "Science", "Sciences", "Biology", "USA", "UK",
      "Australia", "Canada", "However", "Therefore", "Massachusetts",
      "California", "Florida", "Maryland", "Texas", "Queensland",
      "Baltimore", "Sydney", "Melbourne", "London", "Paris", "Berlin",
      # Date artifacts
      "Received", "Accepted", "Published", "January", "February", "March",
      "April", "May", "June", "July", "August", "September", "October",
      "November", "December", "Box", "Figure", "Table", "Abstract",
      "Introduction", "Methods", "Results", "Discussion", "References"
    ),
    # Keep entries that look like names (have reasonable length)
    nchar(author_name) >= 3,
    nchar(author_name) <= 50
  )

cat(sprintf("Cleaned data: %s records → %s records\n",
           comma(nrow(authors)),
           comma(nrow(authors_clean))))

# ============================================================================
# PART 1: CO-AUTHORSHIP NETWORK
# ============================================================================

cat("\n")
cat(paste0(strrep("=", 80), "\n"))
cat("PART 1: CO-AUTHORSHIP NETWORK\n")
cat(paste0(strrep("=", 80), "\n\n"))

# Build edge list: all pairs of authors on same paper
cat("Building co-authorship network...\n")

# Get papers with multiple authors
multi_author_papers <- authors_clean %>%
  group_by(paper_id) %>%
  filter(n() >= 2) %>%
  ungroup()

# Create all pairwise combinations of authors per paper
coauthor_edges <- multi_author_papers %>%
  group_by(paper_id) %>%
  summarize(
    authors = list(unique(author_name)),
    n_authors = n_distinct(author_name),
    .groups = "drop"
  ) %>%
  filter(n_authors >= 2) %>%
  rowwise() %>%
  mutate(
    pairs = list(combn(authors, 2, simplify = FALSE))
  ) %>%
  unnest(pairs) %>%
  mutate(
    author1 = map_chr(pairs, 1),
    author2 = map_chr(pairs, 2)
  ) %>%
  select(paper_id, author1, author2)

# Count collaborations
coauthor_network <- coauthor_edges %>%
  group_by(author1, author2) %>%
  summarize(
    n_papers = n(),
    .groups = "drop"
  )

cat(sprintf("Co-authorship network: %s unique edges\n",
           comma(nrow(coauthor_network))))
cat(sprintf("  %s total collaborations\n",
           comma(sum(coauthor_network$n_papers))))

# Build igraph network
g_coauthor <- graph_from_data_frame(
  coauthor_network,
  directed = FALSE
)

# Add edge weights
E(g_coauthor)$weight <- coauthor_network$n_papers

# Calculate network metrics
cat("\nCalculating network metrics...\n")

# Basic metrics
n_nodes <- vcount(g_coauthor)
n_edges <- ecount(g_coauthor)
density <- edge_density(g_coauthor)
components <- components(g_coauthor)
largest_component_size <- max(components$csize)

cat(sprintf("  Nodes (authors): %s\n", comma(n_nodes)))
cat(sprintf("  Edges (collaborations): %s\n", comma(n_edges)))
cat(sprintf("  Network density: %.4f\n", density))
cat(sprintf("  Connected components: %s\n", comma(components$no)))
cat(sprintf("  Largest component size: %s\n", comma(largest_component_size)))

# Degree distribution
degrees <- degree(g_coauthor)
degree_summary <- data.frame(
  author = V(g_coauthor)$name,
  degree = degrees
) %>%
  arrange(desc(degree))

cat(sprintf("\nTop 10 most collaborative authors:\n"))
print(head(degree_summary, 10), row.names = FALSE)

# Save network metrics
write_csv(
  degree_summary,
  "outputs/analysis/coauthor_network_degrees.csv"
)

cat("\n✓ Saved: coauthor_network_degrees.csv\n")

# ============================================================================
# PART 2: INSTITUTION COLLABORATION NETWORK
# ============================================================================

cat("\n")
cat(paste0(strrep("=", 80), "\n"))
cat("PART 2: INSTITUTION COLLABORATION NETWORK\n")
cat(paste0(strrep("=", 80), "\n\n"))

# Extract country from affiliation for network analysis
# This is a simplified approach - Phase 3 Option A would improve this
extract_country_simple <- function(affiliation) {
  if (is.na(affiliation) || affiliation == "") return(NA_character_)

  # Common country patterns
  countries <- c(
    "USA", "United States", "Australia", "UK", "United Kingdom",
    "Canada", "Germany", "France", "Italy", "Spain", "Portugal",
    "Japan", "China", "South Africa", "Brazil", "Mexico",
    "New Zealand", "Norway", "Sweden", "Netherlands", "Belgium"
  )

  for (country in countries) {
    if (grepl(country, affiliation, ignore.case = TRUE)) {
      # Standardize
      if (country %in% c("USA", "United States")) return("USA")
      if (country %in% c("UK", "United Kingdom")) return("UK")
      return(country)
    }
  }

  return(NA_character_)
}

# Use affiliation data directly from authors table
institution_papers <- authors_clean %>%
  filter(!is.na(affiliation), affiliation != "") %>%
  # Simplify institution names (take first 50 chars for matching)
  mutate(
    institution = str_sub(affiliation, 1, 50),
    country = map_chr(affiliation, extract_country_simple)
  )

cat(sprintf("Papers with affiliation data: %s records\n", comma(nrow(institution_papers))))

# Get papers with multiple institutions
multi_inst_papers <- institution_papers %>%
  group_by(paper_id) %>%
  filter(n_distinct(institution) >= 2) %>%
  ungroup()

cat(sprintf("Papers with multi-institution collaboration: %s\n",
           comma(n_distinct(multi_inst_papers$paper_id))))

# Create institution pairs
inst_edges <- multi_inst_papers %>%
  group_by(paper_id) %>%
  summarize(
    institutions = list(unique(institution)),
    n_inst = n_distinct(institution),
    .groups = "drop"
  ) %>%
  filter(n_inst >= 2) %>%
  rowwise() %>%
  mutate(
    pairs = list(combn(institutions, 2, simplify = FALSE))
  ) %>%
  unnest(pairs) %>%
  mutate(
    inst1 = map_chr(pairs, 1),
    inst2 = map_chr(pairs, 2)
  ) %>%
  select(paper_id, inst1, inst2)

# Count collaborations
inst_network <- inst_edges %>%
  group_by(inst1, inst2) %>%
  summarize(
    n_papers = n(),
    .groups = "drop"
  ) %>%
  arrange(desc(n_papers))

cat(sprintf("Institution collaboration network: %s unique edges\n",
           comma(nrow(inst_network))))

# Top collaborations
cat("\nTop 10 institution collaborations:\n")
print(head(inst_network, 10), row.names = FALSE)

# Save
write_csv(
  inst_network,
  "outputs/analysis/institution_collaboration_network.csv"
)

cat("\n✓ Saved: institution_collaboration_network.csv\n")

# ============================================================================
# PART 3: CROSS-COUNTRY PARTNERSHIPS
# ============================================================================

cat("\n")
cat(paste0(strrep("=", 80), "\n"))
cat("PART 3: CROSS-COUNTRY PARTNERSHIPS\n")
cat(paste0(strrep("=", 80), "\n\n"))

# Build country collaboration network using affiliation data
country_papers <- institution_papers %>%
  filter(!is.na(country)) %>%
  select(paper_id, country) %>%
  distinct()

# Papers with multiple countries
multi_country_papers <- country_papers %>%
  group_by(paper_id) %>%
  filter(n_distinct(country) >= 2) %>%
  ungroup()

cat(sprintf("Papers with international collaboration: %s\n",
           comma(n_distinct(multi_country_papers$paper_id))))

# Create country pairs
country_edges <- multi_country_papers %>%
  group_by(paper_id) %>%
  summarize(
    countries = list(unique(country)),
    n_countries = n_distinct(country),
    .groups = "drop"
  ) %>%
  filter(n_countries >= 2) %>%
  rowwise() %>%
  mutate(
    pairs = list(combn(countries, 2, simplify = FALSE))
  ) %>%
  unnest(pairs) %>%
  mutate(
    country1 = map_chr(pairs, 1),
    country2 = map_chr(pairs, 2)
  ) %>%
  select(paper_id, country1, country2)

# Count collaborations
country_network <- country_edges %>%
  group_by(country1, country2) %>%
  summarize(
    n_papers = n(),
    .groups = "drop"
  ) %>%
  arrange(desc(n_papers))

cat(sprintf("Country collaboration network: %s unique edges\n",
           comma(nrow(country_network))))

# Top collaborations
cat("\nTop 20 country partnerships:\n")
print(head(country_network, 20), row.names = FALSE)

# Build igraph network
g_country <- graph_from_data_frame(
  country_network,
  directed = FALSE
)

E(g_country)$weight <- country_network$n_papers

# Calculate metrics
country_degrees <- data.frame(
  country = V(g_country)$name,
  degree = degree(g_country),
  weighted_degree = strength(g_country)
) %>%
  arrange(desc(weighted_degree))

cat("\nMost internationally collaborative countries:\n")
print(head(country_degrees, 15), row.names = FALSE)

# Save
write_csv(
  country_network,
  "outputs/analysis/country_collaboration_network.csv"
)

write_csv(
  country_degrees,
  "outputs/analysis/country_collaboration_metrics.csv"
)

cat("\n✓ Saved: country_collaboration_network.csv\n")
cat("✓ Saved: country_collaboration_metrics.csv\n")

# ============================================================================
# SUMMARY REPORT
# ============================================================================

cat("\n")
cat(paste0(strrep("=", 80), "\n"))
cat("COLLABORATION NETWORK ANALYSIS COMPLETE\n")
cat(paste0(strrep("=", 80), "\n\n"))

cat("OUTPUTS CREATED:\n")
cat("  1. coauthor_network_degrees.csv - Author collaboration metrics\n")
cat("  2. institution_collaboration_network.csv - Institution partnerships\n")
cat("  3. country_collaboration_network.csv - Country partnerships\n")
cat("  4. country_collaboration_metrics.csv - Country network metrics\n")

cat("\nKEY FINDINGS:\n")
cat(sprintf("  • %s unique authors in collaboration network\n", comma(n_nodes)))
cat(sprintf("  • %s co-authorship connections\n", comma(n_edges)))
cat(sprintf("  • %s papers with multi-institution collaboration\n",
           comma(n_distinct(multi_inst_papers$paper_id))))
cat(sprintf("  • %s papers with international collaboration\n",
           comma(n_distinct(multi_country_papers$paper_id))))
cat(sprintf("  • %s unique country partnerships\n", comma(nrow(country_network))))

cat("\n")
cat(paste0(strrep("=", 80), "\n"))
