#!/usr/bin/env Rscript
# ============================================================================
# GEOGRAPHIC VISUALIZATIONS - RESEARCHER DATABASE
# ============================================================================
# Purpose: Create world maps showing research distribution by country
#          Based on researcher affiliations extracted from PDFs
#
# Reference: guuske map1.png, guuske map2.png
#
# Outputs:
#   1) World map: Papers per country (choropleth)
#   2) World map: Disciplines per country (with overlays)
#   3) Bar chart: Top 20 countries by paper count
#   4) Regional breakdown: Discipline distribution
#
# Author: EEA 2025 Data Panel
# Date: 2025-10-26
# ============================================================================

library(tidyverse)
library(scales)
library(rnaturalearth)
library(rnaturalearthdata)
library(sf)
library(viridis)

# ============================================================================
# LOAD DATA
# ============================================================================

cat("\n=== LOADING DATA ===\n")

# Load institutions with countries
institutions <- read_csv(
  "outputs/researchers/institutions_raw.csv",
  show_col_types = FALSE
)

# Load paper-author linkages
paper_authors <- read_csv(
  "outputs/researchers/paper_authors_full.csv",
  show_col_types = FALSE
)

# Load discipline data
discipline_data <- read_csv(
  "outputs/analysis/data_science_segmentation.csv",
  show_col_types = FALSE
) %>%
  select(paper_id, year, disciplines, num_disciplines)

cat(sprintf("Loaded %s institutions\n", comma(nrow(institutions))))
cat(sprintf("Loaded %s paper-author linkages\n", comma(nrow(paper_authors))))
cat(sprintf("Loaded %s papers with discipline data\n", comma(nrow(discipline_data))))

# ============================================================================
# DATA PREPARATION
# ============================================================================

cat("\n=== PREPARING GEOGRAPHIC DATA ===\n")

# Filter institutions with country information
institutions_with_country <- institutions %>%
  filter(!is.na(country), country != "")

cat(sprintf("Institutions with country: %s (%.1f%%)\n",
            comma(nrow(institutions_with_country)),
            100 * nrow(institutions_with_country) / nrow(institutions)))

# Link papers to countries through authors
paper_countries <- paper_authors %>%
  inner_join(institutions, by = c("affiliation" = "institution_name")) %>%
  filter(!is.na(country), country != "") %>%
  select(paper_id, author_name, country) %>%
  distinct()

cat(sprintf("Paper-country linkages: %s\n", comma(nrow(paper_countries))))

# Standardize country names BEFORE aggregation
paper_countries <- paper_countries %>%
  mutate(country = case_when(
    country == "United States" ~ "USA",
    country == "United Kingdom" ~ "UK",
    TRUE ~ country
  ))

# Aggregate: Papers per country
papers_per_country <- paper_countries %>%
  group_by(country) %>%
  summarise(
    paper_count = n_distinct(paper_id),
    author_count = n_distinct(author_name),
    .groups = "drop"
  ) %>%
  arrange(desc(paper_count))

cat(sprintf("Countries represented: %d\n", nrow(papers_per_country)))

# Link with disciplines
paper_countries_disciplines <- paper_countries %>%
  inner_join(discipline_data, by = "paper_id") %>%
  select(paper_id, country, disciplines, year) %>%
  distinct()

# Expand disciplines (they're comma-separated)
paper_countries_disciplines_expanded <- paper_countries_disciplines %>%
  separate_rows(disciplines, sep = ",") %>%
  mutate(disciplines = str_trim(disciplines))

# Count disciplines per country
disciplines_per_country <- paper_countries_disciplines_expanded %>%
  group_by(country, disciplines) %>%
  summarise(count = n(), .groups = "drop") %>%
  group_by(country) %>%
  mutate(
    total_in_country = sum(count),
    proportion = count / total_in_country
  ) %>%
  ungroup()

# Get world map data
world <- ne_countries(scale = "medium", returnclass = "sf")

# Standardize country names
country_mapping <- tribble(
  ~our_name, ~map_name,
  "USA", "United States of America",
  "UK", "United Kingdom",
  "United States", "United States of America",
  "United Kingdom", "United Kingdom"
)

# Apply mapping
papers_per_country <- papers_per_country %>%
  left_join(country_mapping, by = c("country" = "our_name")) %>%
  mutate(country_mapped = coalesce(map_name, country)) %>%
  select(-map_name)

# Join with world map
world_data <- world %>%
  left_join(papers_per_country, by = c("name" = "country_mapped"))

# ============================================================================
# VISUALIZATION 1: WORLD MAP - PAPERS PER COUNTRY (CHOROPLETH)
# ============================================================================

cat("\n=== CREATING VISUALIZATION 1: World Map (Papers per Country) ===\n")

# Calculate centroids for country labels (only for countries with data)
world_data_with_papers <- world_data %>%
  filter(!is.na(paper_count))

# Get point-on-surface (better than centroid for irregular shapes)
# This ensures the label point is actually inside the country
world_label_points <- world_data_with_papers %>%
  st_point_on_surface() %>%
  mutate(
    label = sprintf("%s\n(n=%s)", name, comma(paper_count))
  )

# Determine which countries to label (all countries with ≥10 papers OR specific small countries)
world_centroids_labeled <- world_label_points %>%
  filter(paper_count >= 10 | name %in% c("Chile", "Argentina"))

# Extract coordinates for custom nudging
label_coords <- world_centroids_labeled %>%
  st_coordinates() %>%
  as_tibble() %>%
  bind_cols(world_centroids_labeled %>% st_drop_geometry())

# Add custom nudging for specific countries
label_coords <- label_coords %>%
  mutate(
    nudge_x = case_when(
      name == "Chile" ~ -8,          # Move Chile label left (off country, into Pacific)
      name == "Argentina" ~ 8,       # Move Argentina label right (off country, into Atlantic)
      name == "Portugal" ~ -2,       # Move Portugal slightly left
      name == "France" ~ 0,          # Keep France centered
      name == "Germany" ~ 1,         # Move Germany slightly right
      TRUE ~ 0
    ),
    nudge_y = case_when(
      name == "France" ~ 1,          # Move France slightly up to avoid overlap
      name == "Portugal" ~ -1,       # Move Portugal slightly down
      TRUE ~ 0
    )
  )

cat(sprintf("Labeling %d countries (≥10 papers or specially selected)\n", nrow(label_coords)))

p1 <- ggplot(world_data) +
  geom_sf(aes(fill = paper_count), color = "white", size = 0.1) +
  geom_text(
    data = label_coords,
    aes(x = X + nudge_x, y = Y + nudge_y, label = label),
    size = 2.5,
    color = "black",
    fontface = "bold"
  ) +
  scale_fill_viridis(
    option = "plasma",
    name = "Papers",
    labels = comma,
    trans = "log10",
    breaks = c(1, 10, 100, 1000),
    na.value = "grey90"
  ) +
  labs(
    title = "Global Distribution of Shark Research",
    subtitle = sprintf("Based on %s author affiliations across %d countries",
                      comma(nrow(paper_countries)), nrow(papers_per_country)),
    caption = "EEA 2025 Data Panel | Log scale | Countries with ≥10 papers labeled"
  ) +
  theme_minimal(base_size = 12) +
  theme(
    plot.background = element_rect(fill = "white", color = NA),
    panel.background = element_rect(fill = "white", color = NA),
    panel.grid = element_line(color = "grey95"),
    axis.text = element_blank(),
    axis.title = element_blank(),
    plot.title = element_text(size = 16, face = "bold", hjust = 0.5),
    plot.subtitle = element_text(size = 11, hjust = 0.5, color = "grey40"),
    plot.caption = element_text(size = 9, color = "grey50", margin = margin(t = 10)),
    legend.position = "right",
    plot.margin = margin(t = 10, r = 10, b = 10, l = 10)
  )

ggsave(
  "outputs/figures/world_map_papers_by_country.png",
  plot = p1,
  width = 14,
  height = 8,
  dpi = 300,
  bg = "white"
)

ggsave(
  "outputs/figures/world_map_papers_by_country.pdf",
  plot = p1,
  width = 14,
  height = 8,
  bg = "white"
)

cat("✓ Saved: world_map_papers_by_country.png + .pdf\n")

# ============================================================================
# VISUALIZATION 1B: EUROPEAN ZOOMED MAP
# ============================================================================

cat("\n=== CREATING VISUALIZATION 1B: European Zoomed Map ===\n")

# Filter for European countries
european_countries <- c(
  "United Kingdom", "France", "Germany", "Italy", "Spain", "Portugal",
  "Netherlands", "Belgium", "Switzerland", "Austria", "Denmark", "Sweden",
  "Norway", "Finland", "Poland", "Czech Republic", "Greece", "Ireland",
  "Iceland", "Romania", "Bulgaria", "Hungary", "Croatia", "Serbia",
  "Slovakia", "Slovenia", "Estonia", "Latvia", "Lithuania", "Albania",
  "Bosnia and Herzegovina", "North Macedonia", "Montenegro", "Moldova",
  "Ukraine", "Belarus"
)

# Filter world data for Europe
europe_data <- world_data %>%
  filter(name %in% european_countries)

# Filter label data for European countries with papers
europe_label_coords <- label_coords %>%
  filter(name %in% european_countries)

cat(sprintf("European countries with data: %d\n", nrow(europe_label_coords)))

# Create European map with tighter zoom
p1b <- ggplot(europe_data) +
  geom_sf(aes(fill = paper_count), color = "white", size = 0.2) +
  geom_text(
    data = europe_label_coords,
    aes(x = X + nudge_x, y = Y + nudge_y, label = label),
    size = 3,
    color = "black",
    fontface = "bold"
  ) +
  scale_fill_viridis(
    option = "plasma",
    name = "Papers",
    labels = comma,
    trans = "log10",
    breaks = c(1, 10, 100, 1000),
    na.value = "grey90"
  ) +
  coord_sf(xlim = c(-12, 30), ylim = c(35, 72)) +  # Zoom to Europe
  labs(
    title = "European Distribution of Shark Research",
    subtitle = sprintf("European countries with geographic data (n=%d)",
                      nrow(europe_label_coords)),
    caption = "EEA 2025 Data Panel | Log scale"
  ) +
  theme_minimal(base_size = 12) +
  theme(
    plot.background = element_rect(fill = "white", color = NA),
    panel.background = element_rect(fill = "white", color = NA),
    panel.grid = element_line(color = "grey95"),
    axis.text = element_blank(),
    axis.title = element_blank(),
    plot.title = element_text(size = 16, face = "bold", hjust = 0.5),
    plot.subtitle = element_text(size = 11, hjust = 0.5, color = "grey40"),
    plot.caption = element_text(size = 9, color = "grey50", margin = margin(t = 10)),
    legend.position = "right",
    plot.margin = margin(t = 10, r = 10, b = 10, l = 10)
  )

ggsave(
  "outputs/figures/europe_map_papers_by_country.png",
  plot = p1b,
  width = 14,
  height = 10,
  dpi = 300,
  bg = "white"
)

ggsave(
  "outputs/figures/europe_map_papers_by_country.pdf",
  plot = p1b,
  width = 14,
  height = 10,
  bg = "white"
)

cat("✓ Saved: europe_map_papers_by_country.png + .pdf\n")

# ============================================================================
# VISUALIZATION 2: TOP 20 COUNTRIES BAR CHART
# ============================================================================

cat("\n=== CREATING VISUALIZATION 2: Top 20 Countries ===\n")

top20_countries <- papers_per_country %>%
  arrange(desc(paper_count)) %>%
  head(20) %>%
  mutate(country = fct_reorder(country, paper_count))

p2 <- ggplot(top20_countries, aes(x = paper_count, y = country)) +
  geom_col(fill = "#440154", alpha = 0.8) +
  geom_text(aes(label = comma(paper_count)),
           hjust = -0.2, size = 3, color = "grey20") +
  scale_x_continuous(
    expand = expansion(mult = c(0, 0.15)),
    labels = comma
  ) +
  labs(
    title = "Top 20 Countries in Shark Research",
    subtitle = "Based on author institutional affiliations",
    x = "Number of Papers",
    y = NULL,
    caption = "EEA 2025 Data Panel"
  ) +
  theme_minimal(base_size = 12) +
  theme(
    plot.background = element_rect(fill = "white", color = NA),
    panel.background = element_rect(fill = "white", color = NA),
    panel.grid.major.x = element_line(color = "grey90"),
    panel.grid.major.y = element_blank(),
    panel.grid.minor = element_blank(),
    axis.text.y = element_text(size = 11),
    plot.title = element_text(size = 16, face = "bold", hjust = 0.5),
    plot.subtitle = element_text(size = 11, hjust = 0.5, color = "grey40"),
    plot.caption = element_text(size = 9, color = "grey50", margin = margin(t = 15)),
    plot.margin = margin(t = 10, r = 20, b = 10, l = 10)
  )

ggsave(
  "outputs/figures/top20_countries_bar_chart.png",
  plot = p2,
  width = 10,
  height = 8,
  dpi = 300,
  bg = "white"
)

ggsave(
  "outputs/figures/top20_countries_bar_chart.pdf",
  plot = p2,
  width = 10,
  height = 8,
  bg = "white"
)

cat("✓ Saved: top20_countries_bar_chart.png + .pdf\n")

# ============================================================================
# VISUALIZATION 3: DISCIPLINE DISTRIBUTION BY TOP 10 COUNTRIES
# ============================================================================

cat("\n=== CREATING VISUALIZATION 3: Disciplines by Country ===\n")

# Get top 10 countries
top10_countries <- papers_per_country %>%
  arrange(desc(paper_count)) %>%
  head(10) %>%
  pull(country)

# Filter discipline data for top 10
disciplines_top10 <- disciplines_per_country %>%
  filter(country %in% top10_countries) %>%
  group_by(country) %>%
  mutate(
    country_total = sum(count),
    country_label = sprintf("%s (n=%s)", country, comma(country_total))
  ) %>%
  ungroup() %>%
  mutate(country_label = fct_reorder(country_label, country_total, .desc = TRUE))

# Discipline names
discipline_names <- tribble(
  ~code, ~name,
  "BEH", "Behaviour",
  "BIO", "Biology",
  "CON", "Conservation",
  "DATA", "Data Science",
  "FISH", "Fisheries",
  "GEN", "Genetics",
  "MOV", "Movement",
  "TRO", "Trophic Ecology"
)

disciplines_top10 <- disciplines_top10 %>%
  left_join(discipline_names, by = c("disciplines" = "code")) %>%
  mutate(discipline_name = coalesce(name, disciplines))

p3 <- ggplot(disciplines_top10, aes(x = country_label, y = count, fill = discipline_name)) +
  geom_col(position = "fill") +
  scale_y_continuous(labels = percent) +
  scale_fill_brewer(
    palette = "Set2",
    name = "Discipline"
  ) +
  labs(
    title = "Discipline Distribution by Country",
    subtitle = "Top 10 countries in shark research",
    x = NULL,
    y = "Proportion of Papers",
    caption = "EEA 2025 Data Panel"
  ) +
  theme_minimal(base_size = 12) +
  theme(
    plot.background = element_rect(fill = "white", color = NA),
    panel.background = element_rect(fill = "white", color = NA),
    panel.grid.major.x = element_blank(),
    panel.grid.minor = element_blank(),
    axis.text.x = element_text(angle = 45, hjust = 1, size = 10),
    plot.title = element_text(size = 16, face = "bold", hjust = 0.5),
    plot.subtitle = element_text(size = 11, hjust = 0.5, color = "grey40"),
    plot.caption = element_text(size = 9, color = "grey50", margin = margin(t = 15)),
    legend.position = "right",
    plot.margin = margin(t = 10, r = 10, b = 10, l = 10)
  )

ggsave(
  "outputs/figures/disciplines_by_country_top10.png",
  plot = p3,
  width = 12,
  height = 8,
  dpi = 300,
  bg = "white"
)

ggsave(
  "outputs/figures/disciplines_by_country_top10.pdf",
  plot = p3,
  width = 12,
  height = 8,
  bg = "white"
)

cat("✓ Saved: disciplines_by_country_top10.png + .pdf\n")

# ============================================================================
# DATA EXPORT: GEOGRAPHIC SUMMARIES
# ============================================================================

cat("\n=== EXPORTING GEOGRAPHIC DATA ===\n")

# Papers per country
write_csv(
  papers_per_country,
  "outputs/analysis/papers_per_country.csv"
)
cat("✓ Saved: papers_per_country.csv\n")

# Disciplines per country
write_csv(
  disciplines_per_country,
  "outputs/analysis/disciplines_per_country.csv"
)
cat("✓ Saved: disciplines_per_country.csv\n")

# ============================================================================
# SUMMARY REPORT
# ============================================================================

cat("\n")
cat(paste0(strrep("=", 80), "\n"))
cat("GEOGRAPHIC VISUALIZATIONS COMPLETE\n")
cat(paste0(strrep("=", 80), "\n\n"))

cat("VISUALIZATIONS CREATED:\n")
cat("  1. world_map_papers_by_country.png + .pdf\n")
cat("  1b. europe_map_papers_by_country.png + .pdf\n")
cat("  2. top20_countries_bar_chart.png + .pdf\n")
cat("  3. disciplines_by_country_top10.png + .pdf\n")

cat("\nDATA FILES CREATED:\n")
cat("  - papers_per_country.csv\n")
cat("  - disciplines_per_country.csv\n")

cat("\nKEY STATISTICS:\n")
cat(sprintf("  Countries represented: %d\n", nrow(papers_per_country)))
cat(sprintf("  Papers with geographic data: %s\n",
           comma(n_distinct(paper_countries$paper_id))))
cat(sprintf("  Total paper-country linkages: %s\n",
           comma(nrow(paper_countries))))

cat("\n  TOP 5 COUNTRIES:\n")
for (i in 1:min(5, nrow(papers_per_country))) {
  cat(sprintf("    %d. %s: %s papers\n",
             i,
             papers_per_country$country[i],
             comma(papers_per_country$paper_count[i])))
}

cat("\n")
cat(paste0(strrep("=", 80), "\n"))
cat("All colleague requests now complete!\n")
cat(paste0(strrep("=", 80), "\n"))
