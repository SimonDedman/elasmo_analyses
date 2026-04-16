#!/usr/bin/env Rscript
# ============================================================================
# AGGREGATE COLLABORATION NETWORKS
# ============================================================================
# Regenerate the three static aggregate figures using current OpenAlex data:
#   1. country_collaboration_network.png  — country-country collaborations
#   2. all_disciplines_network.png        — discipline co-occurrence network
#   3. author_country_map.png             — world map of author counts
#
# Data: OpenAlex authors + parquet disciplines
# Date: 2026-04-16
# ============================================================================

suppressMessages({
  library(tidyverse)
  library(igraph)
  library(ggraph)
  library(tidygraph)
  library(scales)
  library(sf)
  library(rnaturalearth)
  library(arrow)
})

setwd("/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel")

cat("Loading data...\n")
authors <- read_csv("outputs/openalex_unique_authors.csv", show_col_types = FALSE) |>
  mutate(openalex_author_id = str_remove(openalex_author_id, "https://openalex.org/"))
paper_authors <- read_csv("outputs/openalex_paper_authors.csv", show_col_types = FALSE) |>
  mutate(openalex_author_id = str_remove(openalex_author_id, "https://openalex.org/"))

# =============================================================================
# 1. COUNTRY COLLABORATION NETWORK
# =============================================================================
cat("\n=== 1. Country collaboration network ===\n")

# Assign each paper's authors to a country (use institution_country)
paper_countries <- paper_authors |>
  filter(!is.na(literature_id), !is.na(institution_country)) |>
  mutate(literature_id = as.character(literature_id)) |>
  select(literature_id, country = institution_country) |>
  distinct()

# Country pairs on multi-country papers
country_edges <- paper_countries |>
  group_by(literature_id) |>
  filter(n_distinct(country) > 1) |>
  summarise(
    pairs = list(combn(sort(unique(country)), 2, simplify = FALSE)),
    .groups = "drop"
  ) |>
  unnest(pairs) |>
  mutate(
    from = sapply(pairs, `[`, 1),
    to   = sapply(pairs, `[`, 2)
  ) |>
  count(from, to, name = "weight")

country_nodes <- paper_countries |>
  distinct(literature_id, country) |>
  count(country, name = "papers") |>
  filter(country %in% unique(c(country_edges$from, country_edges$to)))

cat(sprintf("  Countries: %d, edges: %d\n", nrow(country_nodes), nrow(country_edges)))

# Filter to edges with weight >= 3 to reduce clutter
country_edges_f <- country_edges |> filter(weight >= 3)
connected <- unique(c(country_edges_f$from, country_edges_f$to))
country_nodes_f <- country_nodes |> filter(country %in% connected)

g_country <- graph_from_data_frame(country_edges_f, vertices = country_nodes_f, directed = FALSE)

library(ggraph)
p_country <- ggraph(as_tbl_graph(g_country), layout = "fr") +
  geom_edge_link(aes(width = weight, alpha = weight), colour = "#081E3F") +
  geom_node_point(aes(size = papers), colour = "#B6862C", alpha = 0.85) +
  geom_node_text(aes(label = name), repel = TRUE, size = 3,
                 max.overlaps = 40, family = "sans") +
  scale_edge_width(range = c(0.2, 2.5), name = "Shared papers") +
  scale_edge_alpha(range = c(0.15, 0.7), guide = "none") +
  scale_size_continuous(range = c(1.5, 12), name = "Papers", labels = comma) +
  theme_graph(base_family = "sans") +
  labs(
    title = "Elasmobranch research: country collaboration network",
    subtitle = sprintf("%d countries connected by ≥3 shared papers (out of %d total)",
                       nrow(country_nodes_f), nrow(country_nodes)),
    caption = sprintf("Data: OpenAlex, %s", format(Sys.Date(), "%Y-%m-%d"))
  )

ggsave("outputs/figures/country_collaboration_network.png", p_country,
       width = 14, height = 10, dpi = 150, bg = "white")
cat("  Wrote country_collaboration_network.png\n")

# =============================================================================
# 2. DISCIPLINE CO-OCCURRENCE NETWORK
# =============================================================================
cat("\n=== 2. Discipline co-occurrence network ===\n")

pq <- arrow::read_parquet("outputs/literature_review_enriched.parquet")
d_cols <- grep("^d_", names(pq), value = TRUE)
cat(sprintf("  Discipline columns: %d\n", length(d_cols)))

# Long format: paper × discipline (where triggered)
pq_disc <- pq |>
  select(literature_id, all_of(d_cols)) |>
  pivot_longer(cols = all_of(d_cols), names_to = "discipline", values_to = "triggered") |>
  filter(triggered > 0) |>
  mutate(discipline = str_remove(discipline, "^d_")) |>
  select(literature_id, discipline) |>
  distinct()

# Discipline pairs per paper (only papers with 2+ disciplines)
disc_edges <- pq_disc |>
  group_by(literature_id) |>
  filter(n_distinct(discipline) >= 2) |>
  summarise(
    pairs = list(combn(sort(unique(discipline)), 2, simplify = FALSE)),
    .groups = "drop"
  ) |>
  unnest(pairs) |>
  mutate(
    from = sapply(pairs, `[`, 1),
    to   = sapply(pairs, `[`, 2)
  ) |>
  count(from, to, name = "weight")

disc_nodes <- pq_disc |>
  count(discipline, name = "papers") |>
  filter(discipline %in% unique(c(disc_edges$from, disc_edges$to)))

cat(sprintf("  Disciplines: %d, edges: %d\n", nrow(disc_nodes), nrow(disc_edges)))

g_disc <- graph_from_data_frame(disc_edges, vertices = disc_nodes, directed = FALSE)

p_disc <- ggraph(as_tbl_graph(g_disc), layout = "circle") +
  geom_edge_link(aes(width = weight, alpha = weight), colour = "#081E3F") +
  geom_node_point(aes(size = papers), colour = "#B6862C", alpha = 0.85) +
  geom_node_text(aes(label = name), repel = TRUE, size = 3.5,
                 family = "sans") +
  scale_edge_width(range = c(0.3, 3), name = "Shared papers",
                   labels = comma) +
  scale_edge_alpha(range = c(0.2, 0.75), guide = "none") +
  scale_size_continuous(range = c(3, 15), name = "Papers", labels = comma) +
  theme_graph(base_family = "sans") +
  labs(
    title = "Elasmobranch research: discipline co-occurrence network",
    subtitle = sprintf("%d disciplines; edge weight = papers in both",
                       nrow(disc_nodes)),
    caption = sprintf("Data: PDF-based extraction, %s papers, %s",
                      comma(n_distinct(pq_disc$literature_id)),
                      format(Sys.Date(), "%Y-%m-%d"))
  )

ggsave("outputs/figures/all_disciplines_network.png", p_disc,
       width = 12, height = 10, dpi = 150, bg = "white")
cat("  Wrote all_disciplines_network.png\n")

# =============================================================================
# 3. AUTHOR COUNTRY MAP (choropleth)
# =============================================================================
cat("\n=== 3. Author country map ===\n")

author_by_country <- authors |>
  filter(!is.na(institution_country)) |>
  count(institution_country, name = "authors")

cat(sprintf("  Countries with authors: %d\n", nrow(author_by_country)))

world <- ne_countries(scale = "medium", returnclass = "sf")

# OpenAlex uses ISO 2-letter codes; rnaturalearth has iso_a2
map_data <- world |>
  left_join(author_by_country, by = c("iso_a2" = "institution_country"))

p_map <- ggplot(map_data) +
  geom_sf(aes(fill = authors), colour = "white", linewidth = 0.15) +
  scale_fill_gradient(
    low = "#fef3c7", high = "#081E3F",
    na.value = "#e2e8f0",
    name = "Authors",
    labels = comma,
    trans = "log10",
    breaks = c(1, 10, 100, 1000, 5000)
  ) +
  coord_sf(crs = "+proj=robin") +
  theme_void(base_family = "sans") +
  theme(
    plot.title = element_text(size = 14, face = "bold", margin = margin(b = 5)),
    plot.subtitle = element_text(size = 10, colour = "#4a5568", margin = margin(b = 10)),
    legend.position = "bottom",
    legend.key.width = unit(1.8, "cm")
  ) +
  labs(
    title = "Elasmobranch research: authors by country",
    subtitle = sprintf("%s authors across %s countries (log scale)",
                       comma(sum(author_by_country$authors)),
                       nrow(author_by_country)),
    caption = sprintf("Data: OpenAlex, %s", format(Sys.Date(), "%Y-%m-%d"))
  )

ggsave("outputs/figures/author_country_map.png", p_map,
       width = 14, height = 8, dpi = 150, bg = "white")
cat("  Wrote author_country_map.png\n")

cat("\nDone.\n")
