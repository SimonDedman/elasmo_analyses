#!/usr/bin/env Rscript
# ============================================================================
# SCHEMA-SLICED NETWORKS
# ============================================================================
# For each schema category (discipline, pressure, gear, impact, basin),
# produce a country collaboration network and country author map filtered
# to papers matching that schema column.
#
# Outputs to outputs/figures/slices/{schema}/{column}_{type}.png
#
# Author: Simon Dedman + Claude
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

# Which schemas to slice by
SCHEMAS <- list(
  discipline = list(prefix = "d_", label = "Discipline"),
  pressure   = list(prefix = "pr_", label = "Pressure"),
  gear       = list(prefix = "gear_", label = "Gear"),
  impact     = list(prefix = "imp_", label = "Impact"),
  basin      = list(prefix = "b_", label = "Ocean basin"),
  ecosystem  = list(prefix = "eco_", label = "Ecosystem")
)

# Minimum paper count for a slice to be generated
MIN_PAPERS <- 30

cat("Loading data...\n")
authors <- read_csv("outputs/openalex_unique_authors.csv", show_col_types = FALSE) |>
  mutate(openalex_author_id = str_remove(openalex_author_id, "https://openalex.org/"))
paper_authors <- read_csv("outputs/openalex_paper_authors.csv", show_col_types = FALSE) |>
  mutate(openalex_author_id = str_remove(openalex_author_id, "https://openalex.org/"))

# Load all binary columns we need
pq_cols <- c("literature_id", unlist(lapply(SCHEMAS, function(s) {
  schema_full <- arrow::read_parquet("outputs/literature_review_enriched.parquet",
                                      as_data_frame = FALSE)
  cols_in_parquet <- names(schema_full)
  grep(paste0("^", s$prefix), cols_in_parquet, value = TRUE)
})))
pq <- arrow::read_parquet("outputs/literature_review_enriched.parquet",
                          col_select = unique(pq_cols)) |>
  mutate(literature_id = as.character(literature_id))

# Natural earth data (fixed iso_a2)
world <- ne_countries(scale = "medium", returnclass = "sf") |>
  mutate(iso_a2_fixed = if_else(
    is.na(iso_a2) | iso_a2 == "-99" | nchar(iso_a2) != 2,
    iso_a2_eh, iso_a2
  ))

# Country centroids for geographic layout
ne_centroids <- world |>
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

# =============================================================================
# Helper: build country network for a subset of papers
# =============================================================================

build_country_network <- function(paper_ids, slice_label, n_papers, out_path) {
  subset_pa <- paper_authors |>
    filter(as.character(literature_id) %in% paper_ids,
           !is.na(institution_country)) |>
    select(literature_id, country = institution_country) |>
    distinct()

  if (nrow(subset_pa) == 0) return(invisible(NULL))

  c_edges <- subset_pa |>
    group_by(literature_id) |>
    filter(n_distinct(country) > 1) |>
    summarise(pairs = list(combn(sort(unique(country)), 2, simplify = FALSE)),
              .groups = "drop") |>
    unnest(pairs) |>
    mutate(from = sapply(pairs, `[`, 1), to = sapply(pairs, `[`, 2)) |>
    count(from, to, name = "weight")

  # For slices, use a weight threshold proportional to total papers
  min_w <- max(2, ceiling(n_papers / 500))
  c_edges <- c_edges |> filter(weight >= min_w)

  if (nrow(c_edges) == 0) return(invisible(NULL))

  c_nodes <- subset_pa |> distinct(literature_id, country) |>
    count(country, name = "papers") |>
    filter(country %in% unique(c(c_edges$from, c_edges$to))) |>
    mutate(
      continent = coalesce(
        countrycode(country, "iso2c", "continent", warn = FALSE),
        "Other"
      ),
      country_for_layout = case_when(
        country %in% c("GP", "MQ", "RE", "GF", "YT", "NC", "PF") ~ "FR",
        TRUE ~ country
      )
    ) |>
    left_join(ne_centroids, by = c("country_for_layout" = "iso_a2")) |>
    filter(!is.na(lon))

  c_edges <- c_edges |> filter(from %in% c_nodes$country & to %in% c_nodes$country)

  if (nrow(c_nodes) < 2 || nrow(c_edges) == 0) return(invisible(NULL))

  layout_mat <- c_nodes |> select(lon, lat) |> as.matrix()
  g <- graph_from_data_frame(c_edges, vertices = c_nodes, directed = FALSE)

  p <- ggraph(as_tbl_graph(g), layout = layout_mat) +
    geom_edge_link(aes(width = weight, alpha = weight), colour = "#081E3F") +
    geom_node_point(aes(size = papers, colour = continent), alpha = 0.88) +
    geom_node_text(aes(label = name), repel = TRUE, size = 3,
                   max.overlaps = 80, family = "sans",
                   bg.colour = "white", bg.r = 0.1) +
    scale_edge_width(range = c(0.15, 2.5), name = "Shared papers") +
    scale_edge_alpha(range = c(0.12, 0.7), guide = "none") +
    scale_size_continuous(range = c(1.5, 12), name = "Papers", labels = comma) +
    scale_colour_manual(values = c(
      "Africa" = "#d9534f", "Americas" = "#5bc0de", "Asia" = "#f0ad4e",
      "Europe" = "#5cb85c", "Oceania" = "#9b59b6", "Other" = "#868e96"
    ), name = "Continent") +
    coord_fixed() +
    theme_graph(base_family = "sans") +
    labs(
      title = paste0("Country collaboration: ", slice_label),
      subtitle = sprintf("%d papers, %d countries, %d edges (weight ≥%d)",
                         n_papers, nrow(c_nodes), nrow(c_edges), min_w),
      caption = sprintf("Data: OpenAlex + PDF-based extraction, %s",
                        format(Sys.Date(), "%Y-%m-%d"))
    )

  ggsave(out_path, p, width = 14, height = 10, dpi = 120, bg = "white")
}

# =============================================================================
# Helper: build country map (world) for a subset of papers
# =============================================================================

build_country_map <- function(paper_ids, slice_label, n_papers, out_path) {
  subset_authors <- paper_authors |>
    filter(as.character(literature_id) %in% paper_ids,
           !is.na(institution_country)) |>
    distinct(openalex_author_id, institution_country) |>
    count(institution_country, name = "authors")

  if (nrow(subset_authors) == 0) return(invisible(NULL))

  md <- world |>
    left_join(subset_authors, by = c("iso_a2_fixed" = "institution_country"))

  md_valid <- md |>
    filter(!is.na(authors)) |>
    st_make_valid()

  centroids <- md_valid |>
    mutate(centroid = st_point_on_surface(geometry)) |>
    st_drop_geometry() |>
    mutate(
      lon = sapply(centroid, function(p) if (is.null(p)) NA_real_ else sf::st_coordinates(p)[1]),
      lat = sapply(centroid, function(p) if (is.null(p)) NA_real_ else sf::st_coordinates(p)[2]),
      label_colour = if_else(log10(authors) > 1.5, "white", "black")
    ) |>
    filter(!is.na(lon), !is.na(lat)) |>
    st_as_sf(coords = c("lon", "lat"), crs = 4326)

  p <- ggplot(md) +
    geom_sf(aes(fill = authors), colour = "white", linewidth = 0.15) +
    geom_sf_text(data = centroids, aes(label = authors, colour = label_colour),
                 size = 2.5, family = "sans") +
    scale_fill_gradient(low = "#fef3c7", high = "#081E3F", na.value = "#e2e8f0",
                        name = "Authors", labels = comma, trans = "log10") +
    scale_colour_identity() +
    coord_sf(crs = "+proj=robin") +
    theme_void(base_family = "sans") +
    theme(plot.title = element_text(size = 14, face = "bold", margin = margin(b = 5)),
          plot.subtitle = element_text(size = 10, colour = "#4a5568", margin = margin(b = 10)),
          legend.position = "bottom", legend.key.width = unit(1.8, "cm")) +
    labs(
      title = paste0("Authors by country: ", slice_label),
      subtitle = sprintf("%d papers, %s authors across %d countries",
                         n_papers, comma(sum(subset_authors$authors)),
                         nrow(subset_authors))
    )

  ggsave(out_path, p, width = 14, height = 8, dpi = 120, bg = "white")
}

# =============================================================================
# Main loop
# =============================================================================

for (schema_name in names(SCHEMAS)) {
  schema <- SCHEMAS[[schema_name]]
  prefix <- schema$prefix
  out_dir <- file.path("outputs/figures/slices", schema_name)
  dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)

  cols <- grep(paste0("^", prefix), names(pq), value = TRUE)
  cat(sprintf("\n=== Slicing by %s (%d columns) ===\n", schema_name, length(cols)))

  for (col in cols) {
    # Get papers where this column is triggered
    triggered <- pq |>
      filter(.data[[col]] > 0) |>
      pull(literature_id)
    n <- length(triggered)
    if (n < MIN_PAPERS) {
      cat(sprintf("  %s: only %d papers, skipping\n", col, n))
      next
    }
    label <- paste0(schema$label, ": ", str_replace_all(str_remove(col, prefix), "_", " "))
    cat(sprintf("  %s: %d papers\n", col, n))

    # Country network
    build_country_network(
      paper_ids = triggered, slice_label = label, n_papers = n,
      out_path = file.path(out_dir, paste0(str_remove(col, prefix), "_network.png"))
    )
    # Country map
    build_country_map(
      paper_ids = triggered, slice_label = label, n_papers = n,
      out_path = file.path(out_dir, paste0(str_remove(col, prefix), "_map.png"))
    )
  }
}

cat("\nDone.\n")
