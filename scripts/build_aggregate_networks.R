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
  library(countrycode)
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
country_nodes_f <- country_nodes |>
  filter(country %in% connected) |>
  mutate(
    continent = countrycode(country, origin = "iso2c", destination = "continent",
                            warn = FALSE),
    continent = coalesce(continent, "Other")
  )

# Geographic layout: use country centroids from natural earth
# Robust iso_a2: prefer iso_a2_eh when iso_a2 isn't a standard 2-char code
ne_centroids <- world |>
  mutate(
    iso_a2_fixed = if_else(
      is.na(iso_a2) | iso_a2 == "-99" | nchar(iso_a2) != 2,
      iso_a2_eh, iso_a2
    )
  ) |>
  filter(!is.na(iso_a2_fixed), nchar(iso_a2_fixed) == 2) |>
  st_make_valid() |>
  mutate(
    centroid = st_point_on_surface(geometry),
    lon = sapply(centroid, function(p) if (is.null(p)) NA_real_ else sf::st_coordinates(p)[1]),
    lat = sapply(centroid, function(p) if (is.null(p)) NA_real_ else sf::st_coordinates(p)[2])
  ) |>
  st_drop_geometry() |>
  select(iso_a2 = iso_a2_fixed, lon, lat) |>
  distinct(iso_a2, .keep_all = TRUE)

# Map French overseas territories to FR
country_nodes_f <- country_nodes_f |>
  mutate(country_for_layout = case_when(
    country %in% c("GP", "MQ", "RE", "GF", "YT", "NC", "PF") ~ "FR",
    TRUE ~ country
  )) |>
  left_join(ne_centroids, by = c("country_for_layout" = "iso_a2"))

# Drop any still-missing
missing_cc <- country_nodes_f |> filter(is.na(lon)) |> pull(country)
if (length(missing_cc) > 0) {
  cat("  Dropping unmappable countries:", paste(missing_cc, collapse = ", "), "\n")
  country_nodes_f <- country_nodes_f |> filter(!is.na(lon))
  country_edges_f <- country_edges_f |>
    filter(from %in% country_nodes_f$country & to %in% country_nodes_f$country)
}

layout_mat <- country_nodes_f |> select(lon, lat) |> as.matrix()
g_country <- graph_from_data_frame(country_edges_f, vertices = country_nodes_f, directed = FALSE)

library(ggraph)
p_country <- ggraph(as_tbl_graph(g_country), layout = layout_mat) +
  geom_edge_link(aes(width = weight, alpha = weight), colour = "#081E3F") +
  geom_node_point(aes(size = papers, colour = continent), alpha = 0.88) +
  geom_node_text(aes(label = name), repel = TRUE, size = 3,
                 max.overlaps = 80, family = "sans",
                 bg.colour = "white", bg.r = 0.1) +
  scale_edge_width(range = c(0.15, 2.5), name = "Shared papers") +
  scale_edge_alpha(range = c(0.12, 0.7), guide = "none") +
  scale_size_continuous(range = c(1.5, 12), name = "Papers", labels = comma) +
  scale_colour_manual(
    name = "Continent",
    values = c(
      "Africa"   = "#d9534f",
      "Americas" = "#5bc0de",
      "Asia"     = "#f0ad4e",
      "Europe"   = "#5cb85c",
      "Oceania"  = "#9b59b6",
      "Other"    = "#868e96"
    )
  ) +
  coord_fixed() +
  theme_graph(base_family = "sans") +
  labs(
    title = "Elasmobranch research: country collaboration network",
    subtitle = sprintf("%d countries connected by ≥3 shared papers; geographic layout (Mercator-ish)",
                       nrow(country_nodes_f)),
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

# Discipline groupings
disc_groups <- tribble(
  ~discipline,       ~group,
  "fisheries",       "Fisheries & management",
  "ecotourism",      "Fisheries & management",
  "conservation",    "Fisheries & management",
  "husbandry",       "Fisheries & management",
  "human_dimensions","Fisheries & management",
  "movement",        "Movement & behaviour",
  "behaviour",       "Movement & behaviour",
  "trophic",         "Movement & behaviour",
  "immunology",      "Health",
  "toxicology",      "Health",
  "physiology",      "Organismal biology",
  "biology",         "Organismal biology",
  "biomechanics",    "Organismal biology",
  "sensory",         "Organismal biology",
  "reproductive",    "Organismal biology",
  "data_science",    "Methods & evolution",
  "genetics",        "Methods & evolution",
  "paleontology",    "Methods & evolution",
  "taxonomy",        "Methods & evolution"
)

disc_nodes <- pq_disc |>
  count(discipline, name = "papers") |>
  filter(discipline %in% unique(c(disc_edges$from, disc_edges$to))) |>
  left_join(disc_groups, by = "discipline") |>
  mutate(
    group = factor(group, levels = c(
      "Fisheries & management", "Movement & behaviour", "Organismal biology",
      "Health", "Methods & evolution"
    ))
  )

cat(sprintf("  Disciplines: %d, edges: %d\n", nrow(disc_nodes), nrow(disc_edges)))

g_disc <- graph_from_data_frame(disc_edges, vertices = disc_nodes, directed = FALSE)

# Circular layout, ordered by group so thematic clusters are adjacent
disc_nodes_ordered <- disc_nodes |>
  arrange(group, desc(papers))

# Build circular layout coordinates manually
n_disc <- nrow(disc_nodes_ordered)
angles <- seq(pi/2, pi/2 - 2*pi, length.out = n_disc + 1)[-(n_disc + 1)]
disc_nodes_ordered <- disc_nodes_ordered |>
  mutate(
    x = cos(angles),
    y = sin(angles)
  )

layout_disc <- disc_nodes_ordered |> select(x, y) |> as.matrix()

# Rebuild graph with ordered vertices
g_disc <- graph_from_data_frame(disc_edges, vertices = disc_nodes_ordered, directed = FALSE)
g_tbl <- as_tbl_graph(g_disc)

disc_palette <- c(
  "Fisheries & management" = "#0088cc",
  "Movement & behaviour"   = "#33aa55",
  "Organismal biology"     = "#cc3333",
  "Health"                 = "#f0ad4e",
  "Methods & evolution"    = "#8844aa"
)

p_disc <- ggraph(g_tbl, layout = layout_disc) +
  geom_edge_link(aes(width = weight, alpha = weight), colour = "#444") +
  geom_node_point(aes(size = papers, colour = group), alpha = 0.92) +
  geom_node_text(aes(label = name, colour = group),
                 size = 3.8, family = "sans", fontface = "bold",
                 nudge_x = disc_nodes_ordered$x * 0.18,
                 nudge_y = disc_nodes_ordered$y * 0.18,
                 bg.colour = "white", bg.r = 0.15) +
  scale_edge_width(range = c(0.3, 3), name = "Shared papers",
                   labels = comma) +
  scale_edge_alpha(range = c(0.2, 0.75), guide = "none") +
  scale_size_continuous(range = c(3, 16), name = "Papers", labels = comma) +
  scale_colour_manual(name = "Group", values = disc_palette) +
  coord_fixed(clip = "off") +
  theme_graph(base_family = "sans") +
  theme(plot.margin = margin(20, 100, 20, 100)) +
  labs(
    title = "Elasmobranch research: discipline co-occurrence network",
    subtitle = sprintf("%d disciplines clustered by theme; edge weight = papers in both",
                       nrow(disc_nodes_ordered)),
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

# Fix broken iso_a2 codes (FR, NO, TW, XK, etc. use iso_a2_eh)
world <- world |>
  mutate(iso_a2_fixed = if_else(
    is.na(iso_a2) | iso_a2 == "-99" | nchar(iso_a2) != 2,
    iso_a2_eh, iso_a2
  ))

map_data <- world |>
  left_join(author_by_country, by = c("iso_a2_fixed" = "institution_country"))

# Compute visual centroids (point on surface, avoiding water)
# st_point_on_surface gives a point guaranteed to be inside the polygon
map_valid <- map_data |>
  filter(!is.na(authors)) |>
  st_make_valid()

# Use point_on_surface for mainland; this avoids centroids falling in lakes/seas
centroids <- map_valid |>
  mutate(centroid = st_point_on_surface(geometry)) |>
  st_drop_geometry() |>
  mutate(
    lon = sapply(centroid, function(p) if (is.null(p)) NA_real_ else sf::st_coordinates(p)[1]),
    lat = sapply(centroid, function(p) if (is.null(p)) NA_real_ else sf::st_coordinates(p)[2]),
    # Contrast-aware: log10(authors) > 2 → dark fill → white text
    label_colour = if_else(log10(authors) > 2, "white", "black")
  ) |>
  filter(!is.na(lon), !is.na(lat))

centroids_sf <- centroids |>
  st_as_sf(coords = c("lon", "lat"), crs = 4326)

make_map <- function(bbox = NULL, subtitle_suffix = "") {
  p <- ggplot(map_data) +
    geom_sf(aes(fill = authors), colour = "white", linewidth = 0.15) +
    geom_sf_text(data = centroids_sf, aes(label = authors, colour = label_colour),
                 size = 2.6, family = "sans", fontface = "plain") +
    scale_fill_gradient(
      low = "#fef3c7", high = "#081E3F",
      na.value = "#e2e8f0",
      name = "Authors",
      labels = comma,
      trans = "log10",
      breaks = c(1, 10, 100, 1000, 5000)
    ) +
    scale_colour_identity() +
    theme_void(base_family = "sans") +
    theme(
      plot.title = element_text(size = 14, face = "bold", margin = margin(b = 5)),
      plot.subtitle = element_text(size = 10, colour = "#4a5568", margin = margin(b = 10)),
      legend.position = "bottom",
      legend.key.width = unit(1.8, "cm")
    ) +
    labs(
      title = "Elasmobranch research: authors by country",
      subtitle = sprintf("%s authors across %s countries (log scale)%s",
                         comma(sum(author_by_country$authors)),
                         nrow(author_by_country),
                         subtitle_suffix),
      caption = sprintf("Data: OpenAlex, %s", format(Sys.Date(), "%Y-%m-%d"))
    )

  if (is.null(bbox)) {
    p + coord_sf(crs = "+proj=robin")
  } else {
    # Use ETRS89 / Lambert Azimuthal for Europe
    p + coord_sf(crs = "+proj=laea +lat_0=52 +lon_0=10",
                 xlim = bbox$xlim, ylim = bbox$ylim)
  }
}

p_map <- make_map()
ggsave("outputs/figures/author_country_map.png", p_map,
       width = 14, height = 8, dpi = 150, bg = "white")
cat("  Wrote author_country_map.png\n")

# Europe-zoomed version — extended to include Greenland, Russia, N. Africa, Iran
p_map_eu <- make_map(
  bbox = list(
    xlim = c(-4.5e6, 5.5e6),
    ylim = c(-4.0e6, 4.0e6)
  ),
  subtitle_suffix = " — Europe & surrounds"
)
ggsave("outputs/figures/author_country_map_europe.png", p_map_eu,
       width = 12, height = 10, dpi = 150, bg = "white")
cat("  Wrote author_country_map_europe.png\n")

cat("\nDone.\n")
