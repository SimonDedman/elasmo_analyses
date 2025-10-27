#!/usr/bin/env Rscript
# ============================================================================
# GEOGRAPHIC VISUALIZATIONS WITH DISCIPLINE PIE CHARTS
# ============================================================================
# Purpose: Create world and European maps with pie charts showing
#          discipline breakdown by region/country
#
# Reference: guuske map2.png
#
# Outputs:
#   1) World map with regional pie charts
#   2) European map with country pie charts
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
library(scatterpie)

# ============================================================================
# LOAD DATA
# ============================================================================

cat("\n=== LOADING DATA ===\n")

# Load paper-region discipline data
papers_by_region_discipline <- read_csv(
  "outputs/analysis/papers_by_region_discipline.csv",
  show_col_types = FALSE
)

papers_by_region <- read_csv(
  "outputs/analysis/papers_by_region.csv",
  show_col_types = FALSE
)

# Load country-discipline data
disciplines_per_country <- read_csv(
  "outputs/analysis/disciplines_per_country.csv",
  show_col_types = FALSE
)

papers_per_country <- read_csv(
  "outputs/analysis/papers_per_country.csv",
  show_col_types = FALSE
)

cat(sprintf("Loaded %d regions with discipline data\n", nrow(papers_by_region)))
cat(sprintf("Loaded %d countries with data\n", nrow(papers_per_country)))

# ============================================================================
# PREPARE PIE CHART DATA
# ============================================================================

# Discipline metadata
discipline_names <- tribble(
  ~code, ~name, ~color,
  "BEH", "Behaviour", "#E41A1C",
  "BIO", "Biology", "#377EB8",
  "CON", "Conservation", "#4DAF4A",
  "DATA", "Data Science", "#984EA3",
  "FISH", "Fisheries", "#FF7F00",
  "GEN", "Genetics", "#FFFF33",
  "MOV", "Movement", "#A65628",
  "TRO", "Trophic Ecology", "#F781BF"
)

disciplines <- discipline_names$code

# ============================================================================
# PART 1: WORLD MAP WITH REGIONAL PIE CHARTS
# ============================================================================

cat("\n=== CREATING WORLD MAP WITH REGIONAL PIE CHARTS ===\n")

# Prepare regional data in wide format for scatterpie
regional_data_wide <- papers_by_region_discipline %>%
  pivot_wider(
    names_from = disciplines,
    values_from = count,
    values_fill = 0
  ) %>%
  left_join(papers_by_region, by = "region")

# Define regional centroids (approximate lon, lat for pie placement)
regional_positions <- tribble(
  ~region, ~lon, ~lat, ~radius,
  "N. America", -100, 45, 15,
  "S. America", -60, -20, 8,
  "Europe", 15, 52, 12,
  "Africa", 20, 0, 8,
  "Asia", 100, 35, 12,
  "Oceania", 135, -25, 10
)

regional_data_wide <- regional_data_wide %>%
  left_join(regional_positions, by = "region") %>%
  mutate(label = sprintf("%s\n(n=%s)", region, comma(total_papers)))

cat(sprintf("Regional pie charts: %d regions\n", nrow(regional_data_wide)))

# Get world map
world <- ne_countries(scale = "medium", returnclass = "sf")

# Join country data for choropleth
country_mapping <- tribble(
  ~our_name, ~map_name,
  "USA", "United States of America",
  "UK", "United Kingdom"
)

papers_per_country_mapped <- papers_per_country %>%
  left_join(country_mapping, by = c("country" = "our_name")) %>%
  mutate(country_mapped = coalesce(map_name, country))

world_data <- world %>%
  left_join(papers_per_country_mapped, by = c("name" = "country_mapped"))

# Create world map with regional pie charts
# Note: Using simple grey base map to avoid fill scale conflicts with pie charts
p_world_pies <- ggplot() +
  # Base map (simple grey, no choropleth to avoid scale conflicts)
  geom_sf(
    data = world,
    fill = "grey95",
    color = "white",
    size = 0.1
  ) +
  # Add pie charts for regions
  geom_scatterpie(
    data = regional_data_wide,
    aes(x = lon, y = lat, r = radius),
    cols = disciplines,
    color = "black",
    linewidth = 0.5,
    alpha = 0.9
  ) +
  # Add regional labels
  geom_text(
    data = regional_data_wide,
    aes(x = lon, y = lat + radius + 5, label = label),
    size = 3.5,
    fontface = "bold",
    color = "black"
  ) +
  # Pie chart legend
  scale_fill_manual(
    values = setNames(discipline_names$color, discipline_names$code),
    labels = setNames(discipline_names$name, discipline_names$code),
    name = "Discipline"
  ) +
  coord_sf(xlim = c(-180, 180), ylim = c(-60, 80)) +
  labs(
    title = "Global Distribution of Shark Research by Discipline",
    subtitle = sprintf("Pie charts show discipline breakdown by region (n=%s papers total)",
                      comma(sum(papers_by_region$total_papers))),
    caption = "EEA 2025 Data Panel | Pie chart size proportional to regional paper count"
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
  "outputs/figures/world_map_with_regional_discipline_pies.png",
  plot = p_world_pies,
  width = 16,
  height = 10,
  dpi = 300,
  bg = "white"
)

ggsave(
  "outputs/figures/world_map_with_regional_discipline_pies.pdf",
  plot = p_world_pies,
  width = 16,
  height = 10,
  bg = "white"
)

cat("✓ Saved: world_map_with_regional_discipline_pies.png + .pdf\n")

# ============================================================================
# PART 2: EUROPEAN MAP WITH COUNTRY PIE CHARTS
# ============================================================================

cat("\n=== CREATING EUROPEAN MAP WITH COUNTRY PIE CHARTS ===\n")

# Get European countries with sufficient data (≥10 papers)
european_countries <- c(
  "UK", "France", "Germany", "Italy", "Spain", "Portugal",
  "Norway", "Ireland", "Greece", "Sweden", "Netherlands",
  "Turkey", "Austria", "Switzerland", "Belgium", "Denmark"
)

european_data <- disciplines_per_country %>%
  filter(country %in% european_countries) %>%
  pivot_wider(
    names_from = disciplines,
    values_from = count,
    values_fill = 0
  ) %>%
  left_join(papers_per_country, by = "country")

# Get country centroids from naturalearth
world_europe <- world %>%
  filter(name %in% c(
    "United Kingdom", "France", "Germany", "Italy", "Spain", "Portugal",
    "Norway", "Ireland", "Greece", "Sweden", "Netherlands",
    "Turkey", "Austria", "Switzerland", "Belgium", "Denmark"
  ))

# Calculate centroids
europe_centroids <- world_europe %>%
  st_centroid() %>%
  st_coordinates() %>%
  as_tibble() %>%
  bind_cols(world_europe %>% st_drop_geometry() %>% select(name))

# Join with data
european_data <- european_data %>%
  left_join(country_mapping, by = c("country" = "our_name")) %>%
  mutate(country_mapped = coalesce(map_name, country)) %>%
  left_join(europe_centroids, by = c("country_mapped" = "name")) %>%
  filter(!is.na(X), !is.na(Y)) %>%
  mutate(
    radius = sqrt(paper_count) * 0.15,  # Reduced from 0.5 to prevent overlap
    label = sprintf("%s\n(n=%s)", country, comma(paper_count))
  )

cat(sprintf("European country pie charts: %d countries\n", nrow(european_data)))

# Create European map
p_europe_pies <- ggplot() +
  # Base map
  geom_sf(
    data = world_europe,
    fill = "grey95",
    color = "white",
    size = 0.2
  ) +
  # Add pie charts for countries
  geom_scatterpie(
    data = european_data,
    aes(x = X, y = Y, r = radius),
    cols = disciplines,
    color = "black",
    linewidth = 0.3,
    alpha = 0.9
  ) +
  # Add country labels (offset to avoid overlap with pies)
  geom_text(
    data = european_data,
    aes(x = X, y = Y + radius + 0.5, label = country),
    size = 2.5,
    fontface = "bold",
    color = "black"
  ) +
  scale_fill_manual(
    values = setNames(discipline_names$color, discipline_names$code),
    labels = setNames(discipline_names$name, discipline_names$code),
    name = "Discipline"
  ) +
  coord_sf(xlim = c(-12, 45), ylim = c(35, 72)) +
  labs(
    title = "European Shark Research by Discipline",
    subtitle = sprintf("%d countries with ≥10 papers shown", nrow(european_data)),
    caption = "EEA 2025 Data Panel | Pie chart size proportional to country paper count"
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
  "outputs/figures/europe_map_with_country_discipline_pies.png",
  plot = p_europe_pies,
  width = 14,
  height = 10,
  dpi = 300,
  bg = "white"
)

ggsave(
  "outputs/figures/europe_map_with_country_discipline_pies.pdf",
  plot = p_europe_pies,
  width = 14,
  height = 10,
  bg = "white"
)

cat("✓ Saved: europe_map_with_country_discipline_pies.png + .pdf\n")

# ============================================================================
# SUMMARY
# ============================================================================

cat("\n")
cat(paste0(strrep("=", 80), "\n"))
cat("MAPS WITH DISCIPLINE PIE CHARTS COMPLETE\n")
cat(paste0(strrep("=", 80), "\n\n"))

cat("VISUALIZATIONS CREATED:\n")
cat("  1. world_map_with_regional_discipline_pies.png + .pdf\n")
cat("  2. europe_map_with_country_discipline_pies.png + .pdf\n")

cat("\nREGIONAL PIE CHARTS:\n")
for (i in 1:nrow(regional_data_wide)) {
  cat(sprintf("  %s: %s papers\n",
             regional_data_wide$region[i],
             comma(regional_data_wide$total_papers[i])))
}

cat(sprintf("\nEUROPEAN COUNTRY PIE CHARTS: %d countries\n", nrow(european_data)))

cat("\n")
cat(paste0(strrep("=", 80), "\n"))
