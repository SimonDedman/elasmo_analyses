#!/usr/bin/env Rscript
# ============================================================================
# AUTHOR COLLABORATION NETWORK (modernised)
# ============================================================================
# Builds co-authorship network using OpenAlex + NamSor data.
# Outputs:
#   - outputs/analysis/author_network_nodes.csv
#   - outputs/analysis/author_network_edges.csv
#   - outputs/figures/author_network_static.png (ggraph)
#   - docs/network/index.html (visNetwork interactive)
#
# Author: Simon Dedman + Claude
# Date: 2026-04-16
# ============================================================================

library(tidyverse)
library(igraph)
library(ggraph)
library(tidygraph)
library(visNetwork)
library(htmlwidgets)

setwd("/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel")
dir.create("docs/network", recursive = TRUE, showWarnings = FALSE)

# --- Optional subset mode: --bbox=west,south,east,north ------------------------
# Filters authors by inst_lon/inst_lat for faster iteration on a smaller set.
# When set, output goes to docs/network/index_subset.html.
cli_args <- commandArgs(trailingOnly = TRUE)
bbox_arg <- cli_args[grep("^--bbox=", cli_args)]
SUBSET_BBOX <- NULL
OUTPUT_HTML <- "docs/network/index.html"
if (length(bbox_arg) > 0) {
  vals <- as.numeric(strsplit(sub("^--bbox=", "", bbox_arg[1]), ",")[[1]])
  if (length(vals) == 4 && all(!is.na(vals))) {
    SUBSET_BBOX <- list(west = vals[1], south = vals[2],
                        east = vals[3], north = vals[4])
    OUTPUT_HTML <- "docs/network/index_subset.html"
    cat(sprintf("Subset mode: bbox=[W %.1f, S %.1f, E %.1f, N %.1f] → %s\n",
                vals[1], vals[2], vals[3], vals[4], OUTPUT_HTML))
  } else {
    stop("--bbox requires 4 comma-separated numbers: west,south,east,north")
  }
}

cat("Loading data...\n")
authors <- read_csv("outputs/openalex_unique_authors.csv", show_col_types = FALSE)

# Apply name corrections from the reviewed XLSX (if present)
corr_path <- "outputs/author_name_corrections.csv"
if (file.exists(corr_path)) {
  corrections <- read_csv(corr_path, show_col_types = FALSE) |>
    select(openalex_author_id, corrected_first_name, corrected_last_name)
  authors <- authors |>
    mutate(oa_id = str_remove(openalex_author_id, "https://openalex.org/")) |>
    left_join(corrections, by = c("oa_id" = "openalex_author_id")) |>
    mutate(
      first_name = coalesce(corrected_first_name, first_name),
      last_name  = coalesce(corrected_last_name,  last_name),
      display_name = coalesce(
        ifelse(!is.na(corrected_first_name),
               trimws(paste(corrected_first_name, corrected_last_name)),
               NA_character_),
        display_name
      )
    ) |>
    select(-oa_id, -corrected_first_name, -corrected_last_name)
  cat(sprintf("  Applied %d name corrections\n",
              sum(!is.na(corrections$corrected_first_name))))
}
paper_authors <- read_csv("outputs/openalex_paper_authors.csv", show_col_types = FALSE)
namsor <- read_csv("outputs/namsor_enrichment.csv", show_col_types = FALSE)

# Optional enrichment files (from scripts/enrich_author_last_institutions.py)
last_inst_path <- if (file.exists("outputs/openalex_authors_last_institution.openalex_api.csv")) {
  "outputs/openalex_authors_last_institution.openalex_api.csv"
} else {
  "outputs/openalex_authors_last_institution.csv"
}
if (file.exists(last_inst_path)) {
  last_inst <- read_csv(last_inst_path, show_col_types = FALSE) |>
    mutate(openalex_author_id = str_remove(openalex_author_id, "https://openalex.org/"))
  cat(sprintf("  Loaded last_known_institutions for %d authors\n", nrow(last_inst)))

  # Apply manual overrides from outputs/author_location_overrides.csv if present.
  # Any non-empty field in the overrides replaces the corresponding column.
  ov_path <- "outputs/author_location_overrides.csv"
  if (file.exists(ov_path)) {
    ov <- read_csv(ov_path, show_col_types = FALSE) |>
      mutate(openalex_author_id = str_remove(openalex_author_id, "https://openalex.org/"))
    last_inst <- last_inst |>
      left_join(ov |> select(-any_of("notes")),
                by = "openalex_author_id", suffix = c("", ".ov")) |>
      mutate(
        last_institution_name    = coalesce(last_institution_name.ov,    last_institution_name),
        last_institution_city    = coalesce(last_institution_city.ov,    last_institution_city),
        last_institution_region  = coalesce(last_institution_region.ov,  last_institution_region),
        last_institution_country = coalesce(last_institution_country.ov, last_institution_country),
        last_institution_lat     = coalesce(last_institution_lat.ov,     last_institution_lat),
        last_institution_lon     = coalesce(last_institution_lon.ov,     last_institution_lon)
      ) |>
      select(-ends_with(".ov"))
    cat(sprintf("  Applied %d manual overrides from %s\n", nrow(ov), ov_path))
  }
} else {
  last_inst <- NULL
  cat("  No last_known_institutions file yet — using modal institution\n")
}

# Author metadata with enrichment
namsor_clean <- namsor |>
  mutate(openalex_author_id = str_remove(id, "https://openalex.org/")) |>
  select(openalex_author_id, namsor_gender, namsor_origin_country,
         namsor_origin_region, namsor_origin_subregion, namsor_ethnicity)

ns_ov_path <- "outputs/namsor_overrides.csv"
if (file.exists(ns_ov_path)) {
  ns_ov <- read_csv(ns_ov_path, show_col_types = FALSE,
                    col_types = cols(.default = col_character())) |>
    select(openalex_author_id, any_of(c("namsor_gender", "namsor_origin_country", "namsor_ethnicity")))
  namsor_clean <- namsor_clean |>
    left_join(ns_ov, by = "openalex_author_id", suffix = c("", ".ov")) |>
    mutate(
      namsor_gender         = coalesce(na_if(namsor_gender.ov, ""),         namsor_gender),
      namsor_origin_country = coalesce(na_if(namsor_origin_country.ov, ""), namsor_origin_country),
      namsor_ethnicity      = coalesce(na_if(namsor_ethnicity.ov, ""),      namsor_ethnicity)
    ) |>
    select(-ends_with(".ov"))
  cat(sprintf("  Applied %d NamSor overrides\n", nrow(ns_ov)))
}

author_meta <- authors |>
  mutate(openalex_author_id = str_remove(openalex_author_id, "https://openalex.org/")) |>
  left_join(namsor_clean, by = "openalex_author_id") |>
  mutate(
    gender_final = case_when(
      namsor_gender %in% c("M", "male")   ~ "M",
      namsor_gender %in% c("F", "female") ~ "F",
      gender %in% c("male")               ~ "M",
      gender %in% c("female")             ~ "F",
      TRUE                                 ~ "Unknown"
    )
  )

# If enrichment available: prefer last_known_institution over modal
if (!is.null(last_inst)) {
  author_meta <- author_meta |>
    left_join(last_inst, by = "openalex_author_id") |>
    mutate(
      # Use last_known if present, else fall back to modal
      institution_final = coalesce(last_institution_name, most_common_institution),
      country_final     = coalesce(last_institution_country, institution_country),
      inst_city         = last_institution_city,
      inst_region       = last_institution_region,
      inst_lat          = last_institution_lat,
      inst_lon          = last_institution_lon
    )
} else {
  author_meta <- author_meta |>
    mutate(
      institution_final = most_common_institution,
      country_final     = institution_country,
      inst_city         = NA_character_,
      inst_region       = NA_character_,
      inst_lat          = NA_real_,
      inst_lon          = NA_real_
    )
}

# --- Merge author aliases (duplicate OpenAlex profiles → canonical) ---
aliases_path <- "outputs/author_aliases.csv"
if (file.exists(aliases_path)) {
  aliases <- read_csv(aliases_path, show_col_types = FALSE) |>
    select(alias_openalex_id, canonical_openalex_id)
  cat(sprintf("  Loaded %d author aliases\n", nrow(aliases)))

  remap_ids <- function(ids) {
    hits <- aliases$canonical_openalex_id[match(ids, aliases$alias_openalex_id)]
    coalesce(hits, ids)
  }

  paper_authors <- paper_authors |>
    mutate(openalex_author_id = str_remove(openalex_author_id, "https://openalex.org/"),
           openalex_author_id = remap_ids(openalex_author_id))

  author_meta <- author_meta |>
    filter(!openalex_author_id %in% aliases$alias_openalex_id)

  new_counts <- paper_authors |>
    filter(!is.na(literature_id), !is.na(openalex_author_id)) |>
    distinct(literature_id, openalex_author_id) |>
    count(openalex_author_id, name = "new_paper_count")

  before_n <- nrow(author_meta)
  author_meta <- author_meta |>
    left_join(new_counts, by = "openalex_author_id") |>
    mutate(paper_count = coalesce(new_paper_count, paper_count)) |>
    select(-new_paper_count)
  cat(sprintf("  After alias merge: %d authors (paper counts recomputed)\n", before_n))
}

# Build coauthor edges
cat("Building coauthor edges...\n")
paper_author_clean <- paper_authors |>
  filter(!is.na(literature_id), !is.na(openalex_author_id)) |>
  mutate(openalex_author_id = str_remove(openalex_author_id, "https://openalex.org/")) |>
  select(literature_id, openalex_author_id) |>
  distinct()

coauthor_edges <- paper_author_clean |>
  group_by(literature_id) |>
  filter(n() > 1) |>
  summarise(
    pairs = list(combn(sort(openalex_author_id), 2, simplify = FALSE)),
    .groups = "drop"
  ) |>
  unnest(pairs) |>
  mutate(
    from = sapply(pairs, `[`, 1),
    to   = sapply(pairs, `[`, 2)
  ) |>
  select(from, to) |>
  count(from, to, name = "weight")

cat(sprintf("Coauthor edges: %d (weight >=3: %d)\n",
            nrow(coauthor_edges),
            sum(coauthor_edges$weight >= 3)))

# --- Focal network: filter to authors with >= 3 papers, include ALL edges (weight >= 1) ---
# Client-side slider controls visible edge weight threshold
MIN_PAPERS <- 3
MIN_EDGE_WEIGHT <- 1

focal_authors <- author_meta |> filter(paper_count >= MIN_PAPERS)

# Apply bbox filter if subset mode on — drops authors without coords AND
# those whose institution falls outside the window.
if (!is.null(SUBSET_BBOX)) {
  before_n <- nrow(focal_authors)
  focal_authors <- focal_authors |>
    filter(!is.na(inst_lon), !is.na(inst_lat),
           inst_lon >= SUBSET_BBOX$west,  inst_lon <= SUBSET_BBOX$east,
           inst_lat >= SUBSET_BBOX$south, inst_lat <= SUBSET_BBOX$north)
  cat(sprintf("Subset bbox: %d → %d authors\n", before_n, nrow(focal_authors)))
}

focal_ids <- focal_authors$openalex_author_id

edges_focal <- coauthor_edges |>
  filter(from %in% focal_ids & to %in% focal_ids) |>
  filter(weight >= MIN_EDGE_WEIGHT)

cat(sprintf("Focal network: %d authors, %d edges\n",
            nrow(focal_authors), nrow(edges_focal)))

# Keep only authors present in the edge list (remove isolates)
connected_ids <- unique(c(edges_focal$from, edges_focal$to))
nodes_focal <- focal_authors |> filter(openalex_author_id %in% connected_ids)

cat(sprintf("After removing isolates: %d authors\n", nrow(nodes_focal)))

# --- Export node + edge CSVs ---
dir.create("outputs/analysis", showWarnings = FALSE, recursive = TRUE)
nodes_out <- nodes_focal |>
  select(openalex_author_id, display_name, institution = institution_final,
         country = country_final, papers = paper_count, gender = gender_final,
         origin_country = namsor_origin_country,
         origin_region = namsor_origin_region,
         ethnicity = namsor_ethnicity,
         inst_city, inst_region, inst_lat, inst_lon)
write_csv(nodes_out, "outputs/analysis/author_network_nodes.csv")
write_csv(edges_focal, "outputs/analysis/author_network_edges.csv")
cat("Wrote node/edge CSVs\n")

# --- Build igraph ---
g <- graph_from_data_frame(edges_focal, vertices = nodes_out, directed = FALSE)
cat(sprintf("Graph: %d vertices, %d edges\n", vcount(g), ecount(g)))

# Compute degree for node size
V(g)$degree <- degree(g)

# --- Static figure via ggraph ---
cat("Rendering static figure...\n")
tg <- as_tbl_graph(g)
p <- ggraph(tg, layout = "fr") +
  geom_edge_link(aes(alpha = weight), colour = "#081E3F", width = 0.3) +
  geom_node_point(aes(size = degree, colour = country), alpha = 0.85) +
  scale_edge_alpha(range = c(0.1, 0.6)) +
  scale_size_continuous(range = c(0.8, 6)) +
  theme_graph(base_family = "sans") +
  theme(legend.position = "none") +
  labs(title = sprintf("Elasmobranch Author Collaboration Network (%d authors, %d edges)",
                       vcount(g), ecount(g)),
       subtitle = sprintf("Nodes: authors with ≥%d papers; edges: ≥%d shared papers",
                          MIN_PAPERS, MIN_EDGE_WEIGHT))

dir.create("outputs/figures", showWarnings = FALSE, recursive = TRUE)
ggsave("outputs/figures/author_network_static.png", p,
       width = 14, height = 10, dpi = 150, bg = "white")
cat("Wrote outputs/figures/author_network_static.png\n")

# --- Interactive visNetwork HTML ---
cat("Rendering interactive visNetwork...\n")

# Build visNetwork node/edge data
# group = country (categorical, drives colour)
vis_nodes <- nodes_out |>
  mutate(
    id = openalex_author_id,
    label = display_name,
    loc_str = dplyr::case_when(
      !is.na(inst_city) & !is.na(inst_region) ~ paste0(inst_city, ", ", inst_region, ", ", country),
      !is.na(inst_city)                       ~ paste0(inst_city, ", ", country),
      TRUE                                     ~ coalesce(country, "")
    ),
    title = sprintf(
      "<b>%s</b><br><i>%s</i><br>%s<br>%d papers<br>Gender: %s<br>Origin: %s (%s)<br>Ethnicity: %s",
      display_name,
      coalesce(institution, ""),
      loc_str,
      papers,
      gender,
      coalesce(origin_country, "—"),
      coalesce(origin_region, "—"),
      coalesce(ethnicity, "—")
    ),
    # Direct pixel size (3-20 range) - no value/scaling interaction
    size = pmin(20, pmax(3, log2(papers + 1) * 2.4)),
    labelDropdown = sprintf("%s (%d)", display_name, papers)
  ) |>
  select(id, label, title, size, labelDropdown,
         papers, gender, country, ethnicity, origin_region, origin_country,
         institution, inst_city, inst_region, inst_lat, inst_lon)

# Build a fixed palette for the top-N most-populous countries so a meaningful
# legend can be drawn. Others fall back to a muted grey.
top_countries <- vis_nodes |>
  count(country, sort = TRUE) |>
  filter(!is.na(country)) |>
  head(20)
COUNTRY_PALETTE <- c(
  "#E41A1C", "#377EB8", "#4DAF4A", "#984EA3", "#FF7F00",
  "#FFD700", "#A65628", "#F781BF", "#17becf", "#66C2A5",
  "#FC8D62", "#8DA0CB", "#E78AC3", "#A6D854", "#6A3D9A",
  "#E5C494", "#8c564b", "#1B9E77", "#D95F02", "#7570B3"
)
country_colors <- setNames(COUNTRY_PALETTE[seq_len(nrow(top_countries))],
                          top_countries$country)
country_color_lookup <- function(c) {
  ifelse(is.na(c) | !(c %in% names(country_colors)),
         "#cccccc",
         unname(country_colors[c]))
}
# Attach initial color (country mode) to each node
vis_nodes <- vis_nodes |>
  mutate(color = country_color_lookup(country))
# JSON for legend + JS colour lookups
country_color_json <- jsonlite::toJSON(as.list(country_colors), auto_unbox = TRUE)

vis_edges <- edges_focal |>
  rename(value = weight) |>
  mutate(
    title = sprintf("%d shared papers", value),
    # Log-scaled width — thinner overall so mesh doesn't obscure the map
    width = log2(value + 1) * 0.5
  )

# Build widget with multiple filter dimensions
vn <- visNetwork(vis_nodes, vis_edges,
                 height = "100vh", width = "100%",
                 main = sprintf("Elasmobranch Author Collaboration Atlas — %d authors, %d edges",
                                nrow(vis_nodes), nrow(vis_edges)),
                 submain = paste0(
                   "Gender, origin & ethnicity inferred from name via ",
                   "<a href=\"https://namsor.app\" target=\"_blank\" rel=\"noopener\">NamSor</a>",
                   " — corrections welcome via each author's ",
                   "<a href=\"https://simondedman.github.io/elasmo_analyses/validate/\" target=\"_blank\" rel=\"noopener\">validation page</a>",
                   "<br><span style='font-size:0.75rem;color:#868e96'>(lots of data; default view: edges &#8805;2 shared papers. Use slider to adjust)</span>"
                 )) |>
  visNodes(
    shape = "dot",
    font = list(size = 0, face = "sans", strokeWidth = 2, strokeColor = "#ffffff"),
    labelHighlightBold = FALSE,
    borderWidth = 0.5
  ) |>
  visEdges(
    smooth = FALSE,
    # Darker ink, lower alpha — individual lines stay visible, mesh doesn't flood.
    color = list(color = "rgba(60,80,105,0.35)", highlight = "#B6862C"),
    scaling = list(min = 0.15, max = 1.2)
  ) |>
  visPhysics(
    solver = "forceAtlas2Based",
    forceAtlas2Based = list(gravitationalConstant = -50, springLength = 100),
    stabilization = list(
      enabled = TRUE,
      iterations = 300,
      fit = TRUE
    ),
    # Freeze after stabilisation so clicks are easier
    timestep = 0.3,
    adaptiveTimestep = TRUE
  ) |>
  visInteraction(
    navigationButtons = TRUE,
    hover = TRUE,
    tooltipDelay = 100,
    zoomView = TRUE,
    dragView = TRUE,
    keyboard = list(enabled = TRUE, bindToWindow = FALSE)
  ) |>
  visOptions(
    highlightNearest = list(enabled = TRUE, degree = 1, hover = TRUE, labelOnly = FALSE),
    selectedBy = list(
      variable = "country",
      main = "Filter by country",
      multiple = TRUE
    ),
    nodesIdSelection = list(
      enabled = TRUE,
      useLabels = TRUE,
      main = "Select author"
    )
  ) |>
  # Freeze physics and expose network instance globally for filter controls
  visEvents(
    stabilizationIterationsDone = "function() {
      this.setOptions({ physics: false });
      window.fpNetwork = this;
      if (window.fpOnReady) window.fpOnReady();
    }",
    beforeDrawing = "function(ctx) {
      if (!window.fpNetwork) { window.fpNetwork = this; }
      if (document.body.classList.contains('geo-layout') && window.fpDrawMap) {
        try { window.fpDrawMap(ctx); } catch (e) { console.error('fpDrawMap error', e); }
      }
    }",
    zoom = "function(params) {
      // Counter-zoom: vis-network draws in a scaled canvas so font.size and node radii
      // are multiplied by zoom on screen. Divide by scale to hold constant screen pixels.
      var scale = params.scale || 1;
      if (window.fpLastZoomApply && Math.abs((window.fpLastZoomApply - scale) / scale) < 0.05) return;
      window.fpLastZoomApply = scale;
      window.fpApplyFont(scale);
      // Enforce min zoom once fit-to-view has happened (see fpMinScale)
      if (window.fpMinScale && scale < window.fpMinScale) {
        this.moveTo({ scale: window.fpMinScale });
      }
    }",
    selectNode = "function(params) {
      if (window.fpSelectNode) window.fpSelectNode(params.nodes[0]);
    }",
    deselectNode = "function() {
      if (window.fpDeselect) window.fpDeselect();
    }",
    click = "function(params) {
      if (params.nodes.length === 0 && params.edges.length === 0) {
        if (window.fpDeselect) window.fpDeselect();
      }
    }"
  )

saveWidget(vn, OUTPUT_HTML, selfcontained = TRUE,
           title = "Elasmobranch Author Collaboration Atlas")

# Post-process: inject CSS + custom filter sidebar
html <- readLines(OUTPUT_HTML)

# Build filter options from the data
gender_opts <- sort(unique(vis_nodes$gender))
region_opts <- sort(unique(vis_nodes$origin_region[!is.na(vis_nodes$origin_region)]))
ethnicity_opts <- sort(unique(vis_nodes$ethnicity[!is.na(vis_nodes$ethnicity)]))
country_opts <- sort(unique(vis_nodes$country[!is.na(vis_nodes$country)]))

# Country centroids for geographic layout option
country_coords <- nodes_out |>
  distinct(country) |>
  filter(!is.na(country)) |>
  left_join(
    tibble::tribble(
      ~country, ~lon, ~lat,
      # Fill with ISO2 -> centroid
      # We'll compute these from rnaturalearth at runtime
    ),
    by = "country"
  )

# Build a simple ISO2 -> lon/lat lookup from rnaturalearth
library(sf)
library(rnaturalearth)
world_for_layout <- ne_countries(scale = "medium", returnclass = "sf") |>
  mutate(iso = if_else(is.na(iso_a2) | iso_a2 == "-99" | nchar(iso_a2) != 2,
                       iso_a2_eh, iso_a2)) |>
  filter(!is.na(iso), nchar(iso) == 2)

iso_coords <- world_for_layout |>
  st_make_valid() |>
  mutate(
    centroid = st_point_on_surface(geometry),
    lon = sapply(centroid, function(p) if (is.null(p)) NA_real_ else sf::st_coordinates(p)[1]),
    lat = sapply(centroid, function(p) if (is.null(p)) NA_real_ else sf::st_coordinates(p)[2])
  ) |>
  st_drop_geometry() |>
  select(iso, lon, lat) |>
  distinct(iso, .keep_all = TRUE)

# Add manual overrides
iso_coords <- dplyr::bind_rows(
  iso_coords,
  tibble::tribble(
    ~iso, ~lon, ~lat,
    "GP",  -61.55,  16.25, "MQ", -61.00, 14.67, "RE", 55.53, -21.12,
    "GF",  -53.13,   3.93, "YT",  45.17,-12.83, "GL",-42.00,  72.00,
    "HK",  114.17,  22.32, "SG", 103.82,  1.35
  ) |> anti_join(iso_coords, by = "iso")
)

# Embed node data for geographic layout.
# Prefer institution lat/lon (inst_lat/inst_lon) when available; fall back to country centroid.
vis_nodes_enriched <- vis_nodes |>
  left_join(iso_coords |> rename(country = iso, country_lon = lon, country_lat = lat),
            by = "country") |>
  mutate(
    lon = coalesce(inst_lon, country_lon),
    lat = coalesce(inst_lat, country_lat),
    lon_src = if_else(!is.na(inst_lon), "institution", "country")
  )

cat(sprintf("Institution-level coords: %d / %d authors (%.1f%%)\n",
            sum(vis_nodes_enriched$lon_src == "institution", na.rm = TRUE),
            nrow(vis_nodes_enriched),
            100 * mean(vis_nodes_enriched$lon_src == "institution", na.rm = TRUE)))

nodes_json <- jsonlite::toJSON(
  vis_nodes_enriched |> select(id, gender, country, ethnicity, origin_region,
                                origin_country, papers, institution,
                                inst_city, inst_region, lon, lat, lon_src),
  auto_unbox = FALSE
)

# Full iso2 -> centroid lookup (for origin country layout)
iso_coords_json <- jsonlite::toJSON(
  iso_coords |> rowwise() |>
    mutate(entry = list(list(lon = lon, lat = lat))) |>
    ungroup() |>
    select(iso, entry) |>
    { \(d) setNames(d$entry, d$iso) }(),
  auto_unbox = TRUE
)

# ---- Map layers: country + state borders, label centroids ----
cat("Building map layers (country/state polygons, labels)...\n")
sf_to_rings <- function(sf_data, dp = 2, with_extents = FALSE) {
  all_rings <- list()
  all_extents <- numeric()
  add_seg <- function(seg) {
    if (nrow(seg) < 3) return(invisible())
    pts <- round(as.matrix(seg), dp)
    all_rings[[length(all_rings) + 1]] <<- unname(pts)
    if (with_extents) {
      ext <- max(diff(range(seg$X)), diff(range(seg$Y)))
      all_extents[length(all_extents) + 1] <<- round(ext, 3)
    }
  }
  geoms <- sf::st_geometry(sf_data)
  for (i in seq_along(geoms)) {
    g <- geoms[[i]]
    if (sf::st_is_empty(g)) next
    coords <- sf::st_coordinates(g)
    if (is.null(coords) || nrow(coords) == 0) next
    grp_cols <- intersect(c("L3", "L2", "L1"), colnames(coords))
    if (length(grp_cols) == 0) next
    grp <- do.call(paste, c(lapply(grp_cols, function(cc) coords[, cc]), sep = "_"))
    by_grp <- split(as.data.frame(coords[, c("X", "Y")]), grp)
    for (ring in by_grp) {
      if (nrow(ring) < 3) next
      # Split rings at the antimeridian (|Δlon| > 180) to avoid horizontal streaks
      lons <- ring$X
      breaks <- which(abs(diff(lons)) > 180)
      if (length(breaks) == 0) {
        add_seg(ring)
      } else {
        starts <- c(1, breaks + 1)
        ends   <- c(breaks, nrow(ring))
        for (k in seq_along(starts)) add_seg(ring[starts[k]:ends[k], , drop = FALSE])
      }
    }
  }
  if (with_extents) list(rings = all_rings, extents = all_extents) else all_rings
}

countries_sf <- ne_countries(scale = 50, returnclass = "sf") |>
  st_make_valid() |>
  st_simplify(dTolerance = 0.2, preserveTopology = TRUE)
country_rings <- sf_to_rings(countries_sf, dp = 2)
country_labels_df <- countries_sf |>
  st_point_on_surface() |>
  mutate(
    lon = sapply(geometry, function(p) if (is.null(p)) NA_real_ else sf::st_coordinates(p)[1]),
    lat = sapply(geometry, function(p) if (is.null(p)) NA_real_ else sf::st_coordinates(p)[2])
  ) |>
  st_drop_geometry() |>
  filter(!is.na(lon), !is.na(lat), !is.na(name_long), nchar(name_long) > 0) |>
  # Skip Antarctica (labels look weird)
  filter(name_long != "Antarctica") |>
  transmute(name = name_long,
            lon = round(lon, 2),
            lat = round(lat, 2))

# State/province borders for a selection of larger nations
states_sf <- tryCatch(
  ne_states(country = c(
    "United States of America", "Canada", "Mexico", "Brazil", "Argentina",
    "Australia", "New Zealand", "India", "China", "Russia", "South Africa",
    "Indonesia", "France", "Germany", "Italy", "Spain", "United Kingdom",
    "Chile", "Colombia", "Peru", "Japan"
  ), returnclass = "sf"),
  error = function(e) NULL
)
if (!is.null(states_sf)) {
  states_sf <- states_sf |>
    st_make_valid() |>
    st_simplify(dTolerance = 0.1, preserveTopology = TRUE)
  state_tmp <- sf_to_rings(states_sf, dp = 2, with_extents = TRUE)
  state_rings <- state_tmp$rings
  state_ring_extents <- state_tmp$extents
  # Per-feature bbox extent (degrees) for filtering small regions at low zoom
  state_feature_ext <- vapply(seq_along(st_geometry(states_sf)), function(i) {
    bb <- sf::st_bbox(states_sf[i, ])
    max(bb$xmax - bb$xmin, bb$ymax - bb$ymin)
  }, numeric(1))
  state_labels_df <- states_sf |>
    mutate(.row_ext = state_feature_ext) |>
    st_point_on_surface() |>
    mutate(
      lon = sapply(geometry, function(p) if (is.null(p)) NA_real_ else sf::st_coordinates(p)[1]),
      lat = sapply(geometry, function(p) if (is.null(p)) NA_real_ else sf::st_coordinates(p)[2])
    ) |>
    st_drop_geometry() |>
    { \(d) {
      nm_col <- intersect(c("name", "name_en", "gn_name", "woe_name"), colnames(d))[1]
      if (is.na(nm_col)) nm_col <- "name"
      d$label <- d[[nm_col]]
      d
    } }() |>
    filter(!is.na(lon), !is.na(lat), !is.na(label), nchar(label) > 0) |>
    transmute(name = label, lon = round(lon, 2), lat = round(lat, 2),
              ext = round(.row_ext, 3))
} else {
  state_rings <- list()
  state_ring_extents <- numeric()
  state_labels_df <- tibble::tibble(name = character(), lon = numeric(),
                                    lat = numeric(), ext = numeric())
}

country_rings_json <- jsonlite::toJSON(country_rings, auto_unbox = FALSE, digits = 3)
state_rings_json   <- jsonlite::toJSON(state_rings,   auto_unbox = FALSE, digits = 3)
state_ring_ext_json <- jsonlite::toJSON(state_ring_extents, auto_unbox = FALSE)
country_labels_json <- jsonlite::toJSON(country_labels_df, dataframe = "rows", auto_unbox = FALSE)
state_labels_json   <- jsonlite::toJSON(state_labels_df,   dataframe = "rows", auto_unbox = FALSE)

cat(sprintf("  Country rings: %d, state rings: %d\n",
            length(country_rings), length(state_rings)))
cat(sprintf("  Country labels: %d, state labels: %d\n",
            nrow(country_labels_df), nrow(state_labels_df)))

make_opts <- function(values) {
  paste0('<option value="', values, '">', values, '</option>', collapse = "\n")
}

inject_style <- '<style>
html, body { margin: 0; padding: 0; height: 100%; overflow: hidden; font-family: -apple-system, system-ui, sans-serif; }
.html-widget { width: 100vw !important; height: 100vh !important; }
#htmlwidget_container { width: 100vw !important; height: 100vh !important; }
div.vis-network { width: 100vw !important; height: 100vh !important; }

#fp-debug-top {
  position: fixed;
  top: 10px;
  right: 10px;
  z-index: 2000;
  background: #081E3F;
  color: #FFCC00;
  font-family: "Courier New", monospace;
  font-size: 0.9rem;
  padding: 0.35rem 0.6rem;
  border-radius: 4px;
  box-shadow: 0 2px 6px rgba(0,0,0,0.25);
}

.filter-panel {
  position: fixed;
  top: 10px;
  left: 10px;
  z-index: 1000;
  background: rgba(255,255,255,0.95);
  border: 1px solid #c8d0dc;
  border-radius: 6px;
  padding: 0.6rem 0.8rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  font-size: 0.85rem;
  max-width: 260px;
  max-height: calc(100vh - 30px);
  overflow-y: auto;
}
.filter-panel h3 {
  margin: 0 0 0.5rem 0;
  font-size: 0.9rem;
  color: #081E3F;
  border-bottom: 2px solid #B6862C;
  padding-bottom: 0.2rem;
}
.filter-panel label {
  display: block;
  margin-top: 0.4rem;
  font-weight: 500;
  color: #4a5568;
  font-size: 0.75rem;
}
.filter-panel select, .filter-panel input {
  width: 100%;
  padding: 0.2rem;
  border: 1px solid #c8d0dc;
  border-radius: 3px;
  font-size: 0.8rem;
  box-sizing: border-box;
  overflow: hidden;
  text-overflow: ellipsis;
}
.filter-panel input[type="range"] {
  padding: 0;
}
.filter-panel .stats {
  margin-top: 0.5rem;
  font-size: 0.75rem;
  color: #718096;
}
.filter-panel button.reset {
  margin-top: 0.4rem;
  padding: 0.2rem 0.6rem;
  background: #081E3F;
  color: white;
  border: none;
  border-radius: 3px;
  cursor: pointer;
  font-size: 0.75rem;
}
.filter-panel .legend {
  margin-top: 0.7rem;
  padding-top: 0.5rem;
  border-top: 1px solid #c8d0dc;
  font-size: 0.72rem;
  color: #4a5568;
}
.filter-panel .legend h4 {
  margin: 0 0 0.3rem 0;
  font-size: 0.78rem;
  color: #081E3F;
}
.filter-panel .legend div {
  margin-bottom: 0.15rem;
}
/* Tighten visNetwork header spacing */
h2.main { font-size: 1rem; margin: 0.2rem 0 0.1rem 0; }
h3.submain { font-size: 0.8rem; margin: 0 0 0.2rem 0; color: #718096; font-weight: normal; font-style: italic; }
/* Hide the default selectedBy/nodesIdSelection dropdowns, we replace them */
.vis-configuration-wrapper { display: none !important; }
</style>'

build_ts <- format(Sys.time(), "%Y-%m-%d %H:%M")
# Build filter panel HTML
panel_html <- paste0('<div id="fp-debug-top">build ', build_ts, ' · zoom — · label —px</div>
<div class="filter-panel" id="filter-panel">
<h3>Elasmobranch Author Atlas</h3>

<label>Layout</label>
<select id="fp-layout" style="width:100%">
<option value="physics">Force-directed (default)</option>
<option value="geo-inst">Geographic: institution country</option>
<option value="geo-origin">Geographic: NamSor origin country</option>
</select>

<label>Colour by</label>
<select id="fp-colour" style="width:100%">
<option value="country">Institution country (default)</option>
<option value="gender">Gender</option>
<option value="origin_region">Origin region</option>
<option value="ethnicity">Ethnicity</option>
</select>

<label>Min edge weight (shared papers) <span id="fp-min-edge-val">2</span></label>
<input type="range" id="fp-min-edge" min="1" max="20" step="1" value="2" style="width:100%">
<div style="font-size:0.65rem;color:#868e96;margin-top:-0.2rem;display:flex;justify-content:space-between"><span>1</span><span>20</span></div>
<button class="reset" onclick="window.fpFit()" style="margin-top:0.3rem;background:#4a5568">Fit to view</button>

<label>Search author</label>
<input type="text" id="fp-author" list="fp-author-list" placeholder="Type name...">
<datalist id="fp-author-list">',
paste0('<option value="', vis_nodes$label, '" data-id="', vis_nodes$id, '">',
       collapse = "\n"),
'</datalist>
<label>Country</label>
<select id="fp-country"><option value="">(all)</option>',
make_opts(country_opts), '</select>
<label>Gender</label>
<select id="fp-gender"><option value="">(all)</option>',
make_opts(gender_opts), '</select>
<label>Origin region</label>
<select id="fp-region"><option value="">(all)</option>',
make_opts(region_opts), '</select>
<label>Ethnicity</label>
<select id="fp-ethnicity"><option value="">(all)</option>',
make_opts(ethnicity_opts), '</select>
<button class="reset" onclick="window.fpReset()">Reset filters</button>
<div class="stats" id="fp-stats">Showing ', nrow(vis_nodes), ' / ', nrow(vis_nodes), ' authors</div>

<div class="legend">
  <h4>Legend</h4>
  <div><strong>Node size</strong>: papers (log scale)</div>
  <div><strong>Edge width / alpha</strong>: shared papers (log)</div>
  <div id="fp-legend-colors" style="margin-top:0.5rem;font-size:0.7rem"></div>
</div>
</div>
<script>
window.fpNodesMeta = ', nodes_json, ';
window.fpIsoCoords = ', iso_coords_json, ';
window.fpCountryRings  = ', country_rings_json, ';
window.fpStateRings    = ', state_rings_json, ';
window.fpStateRingExt  = ', state_ring_ext_json, ';
window.fpCountryLabels = ', country_labels_json, ';
window.fpStateLabels   = ', state_labels_json, ';
window.fpCountryPalette = ', country_color_json, ';
// Draw map with zoom-tier borders + labels. scale=60 (px per lon/lat degree).
window.fpDrawMap = function(ctx) {
  var nw = window.fpNetwork;
  var s  = nw && nw.getScale ? nw.getScale() : 1;
  var worldScale = 60;
  ctx.save();
  // Ocean
  ctx.fillStyle = "#d8e3ec";
  ctx.fillRect(-180*worldScale, -90*worldScale, 360*worldScale, 180*worldScale);
  // Draw country polygons (filled + stroked).
  // extents[] is optional — when given, skip rings whose on-screen extent
  // (degrees * worldScale * scale) is below minScreenPx. This is how we
  // hide tiny UK counties at low zoom while keeping huge US states visible.
  var drawRings = function(rings, extents, fill, stroke, lw, minScreenPx) {
    ctx.lineWidth = lw;
    if (fill)   ctx.fillStyle   = fill;
    if (stroke) ctx.strokeStyle = stroke;
    for (var r = 0; r < rings.length; r++) {
      if (extents && minScreenPx && (extents[r] * worldScale * s) < minScreenPx) continue;
      var ring = rings[r];
      if (!ring || ring.length < 3) continue;
      ctx.beginPath();
      for (var i = 0; i < ring.length; i++) {
        var x =  ring[i][0] * worldScale;
        var y = -ring[i][1] * worldScale;
        if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      }
      ctx.closePath();
      if (fill)   ctx.fill();
      if (stroke) ctx.stroke();
    }
  };
  // Country: fill only — stroke is drawn AFTER state polygons so it stays
  // on top and is not subsumed by state-polygon fills.
  drawRings(window.fpCountryRings || [], null, "#e8efdb", null, 0, 0);
  // State polygons: per-feature density filter — needs ≥30 screen px of extent
  // to draw. So California (11° wide) shows from scale≈0.05, but a UK county
  // (0.3° wide) only appears once scale > 1.7.
  drawRings(window.fpStateRings || [], window.fpStateRingExt,
            "#e8efdb", "#9fb39f", 0.4 / s, 30);
  // Country stroke on TOP: thicker + darker, reads as a stronger boundary
  // than the state borders inside it even after state fills paint the land.
  drawRings(window.fpCountryRings || [], null, null, "#4a6b4a", 1.8 / s, 0);
  // Country labels — always; size counter-zooms to stay at target screen px
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillStyle = "rgba(40,55,40,0.85)";
  ctx.font = "600 " + (12 / s) + "px sans-serif";
  (window.fpCountryLabels || []).forEach(function(l) {
    ctx.fillText(l.name, l.lon * worldScale, -l.lat * worldScale);
  });
  // State labels — same per-feature extent filter. Threshold slightly larger
  // than the border (50 px) so labels appear after the border, not before.
  ctx.fillStyle = "rgba(90,110,90,0.7)";
  ctx.font = (9 / s) + "px sans-serif";
  (window.fpStateLabels || []).forEach(function(l) {
    if (l.ext && (l.ext * worldScale * s) < 50) return;
    ctx.fillText(l.name, l.lon * worldScale, -l.lat * worldScale);
  });
  ctx.restore();
};
window.fpReset = function() {
  document.getElementById("fp-country").value = "";
  document.getElementById("fp-gender").value = "";
  document.getElementById("fp-region").value = "";
  document.getElementById("fp-ethnicity").value = "";
  document.getElementById("fp-author").value = "";
  document.getElementById("fp-layout").value = "physics";
  document.getElementById("fp-colour").value = "country";
  document.getElementById("fp-min-edge").value = "2";
  document.getElementById("fp-min-edge-val").textContent = "2";
  window.fpSetColour("country");
  window.fpSetLayout("physics");
  window.fpApplyEdgeWeight();
  window.fpApply();
};
window.fpFit = function() {
  if (window.fpNetwork) window.fpNetwork.fit({ animation: true });
};
window.fpApplyEdgeWeight = function() {
  var nw = window.fpNetwork;
  if (!nw || !nw.body || !nw.body.data) return;
  var minW = parseInt(document.getElementById("fp-min-edge").value, 10);
  var edgesDS = nw.body.data.edges;
  var updates = [];
  edgesDS.forEach(function(e) {
    updates.push({ id: e.id, hidden: e.value < minW });
  });
  edgesDS.update(updates);
};
window.fpSetLayout = function(mode) {
  console.log("fpSetLayout called with mode:", mode);
  var nw = window.fpNetwork;
  if (!nw || !nw.body) { console.warn("fpSetLayout: network not ready"); return; }
  // Release min-zoom floor so fit() can drop the scale for a wider world map
  window.fpMinScale = 0;
  if (mode === "geo-inst" || mode === "geo-origin") {
    document.body.classList.add("geo-layout");
  } else {
    document.body.classList.remove("geo-layout");
  }
  if (nw.redraw) nw.redraw();
  var nodesDS = nw.body.data.nodes;
  var meta = window.fpNodesMeta || [];
  var refreshMinScale = function(delay) {
    setTimeout(function() {
      if (nw.getScale) window.fpMinScale = nw.getScale() * 0.95;
      console.log("fpSetLayout: fpMinScale now", window.fpMinScale);
    }, delay);
  };
  if (mode === "physics") {
    // Seed from geography where available — simulation will relax from there,
    // but residual geographic structure persists (Europe clusters top-right,
    // Americas top-left, etc.) so the first view is intuitive.
    var worldScale = 60;
    var updates = meta.map(function(n) {
      var x, y;
      if (n.lon != null && n.lat != null) {
        x =  n.lon * worldScale;
        y = -n.lat * worldScale;
      } else {
        x = (Math.random() - 0.5) * 800;
        y = (Math.random() - 0.5) * 800;
      }
      return { id: n.id, x: x, y: y, fixed: { x: false, y: false } };
    });
    nodesDS.update(updates);
    // Lower gravity + fewer iterations preserves the geographic seed while still
    // letting edges pull coauthors together.
    nw.setOptions({
      physics: {
        enabled: true,
        solver: "forceAtlas2Based",
        forceAtlas2Based: { gravitationalConstant: -30, springLength: 120 },
        stabilization: { enabled: true, iterations: 150, fit: true }
      }
    });
    setTimeout(function() {
      nw.setOptions({ physics: false });
      nw.fit({ animation: true });
      refreshMinScale(1500);
    }, 2500);
    return;
  }
  // Geographic layouts
  nw.setOptions({ physics: false });
  var positions;
  try {
    positions = window.fpComputePositions(meta, mode);
    console.log("fpComputePositions returned", Object.keys(positions).length, "positions");
  } catch (e) {
    console.error("fpComputePositions error:", e);
    positions = {};
  }
  var updates = meta.map(function(n) {
    var p = positions[n.id];
    if (!p) return { id: n.id, hidden: true };
    return { id: n.id, x: p.x, y: p.y, fixed: { x: true, y: true }, hidden: false };
  });
  nodesDS.update(updates);
  var hiddenCount = updates.filter(function(u) { return u.hidden; }).length;
  console.log("fpSetLayout geo: updated", updates.length, "nodes,", hiddenCount, "hidden (no coords)");
  setTimeout(function() {
    nw.fit({ animation: true });
    refreshMinScale(1500);
  }, 200);
};
// Deterministic 32-bit hash of a string
window.fpHash = function(s) {
  var h = 0;
  for (var i = 0; i < s.length; i++) { h = ((h << 5) - h) + s.charCodeAt(i); h |= 0; }
  return h;
};
// Geographic positions with institution-based clustering.
// Authors at same institution are stacked in a VERTICAL COLUMN at the institution
// point, ordered most-papers → fewest from top. At low zoom the column compresses
// into a single bubble; at high zoom it fans out as a readable, non-overlapping list.
window.fpComputePositions = function(meta, mode) {
  var positions = {};
  var scale = 60;
  var instJitter = 15;       // fallback when only country-level coords available (~25 km)

  // Group by (lon, lat) rounded to 3 decimals — effectively by institution
  var groups = {};
  meta.forEach(function(n) {
    var lon, lat, srcKind;
    if (mode === "geo-origin") {
      var oc = n.origin_country;
      if (oc && window.fpIsoCoords && window.fpIsoCoords[oc]) {
        lon = window.fpIsoCoords[oc].lon;
        lat = window.fpIsoCoords[oc].lat;
        srcKind = "country";
      }
    } else {
      lon = n.lon;
      lat = n.lat;
      srcKind = n.lon_src || "country";
    }
    if (lon == null || lat == null) return;
    var key = lon.toFixed(3) + "," + lat.toFixed(3);
    if (!groups[key]) groups[key] = { lon: lon, lat: lat, srcKind: srcKind, members: [] };
    groups[key].members.push(n);
  });

  // Place members of each group in a spiral / concentric rings
  Object.keys(groups).forEach(function(key) {
    var g = groups[key];
    var members = g.members;
    var count = members.length;
    var cx = g.lon * scale;
    var cy = -g.lat * scale;

    // If source is country-level, add institution-hash offset first
    if (g.srcKind !== "institution") {
      var instKey = members[0].institution || members[0].country || "";
      var hi = window.fpHash(instKey);
      cx += ((hi & 0xFFFF) / 0xFFFF - 0.5) * 2 * instJitter;
      cy += (((hi >> 16) & 0xFFFF) / 0xFFFF - 0.5) * 2 * instJitter;
    }

    // Sort most-prolific first so the top of the column gets the big names
    members.sort(function(a, b) { return b.papers - a.papers; });

    if (count === 1) {
      positions[members[0].id] = { x: cx, y: cy };
      return;
    }

    // Vertical column: stride ~6 world units ≈ 10 km vertically. Canvas y is
    // flipped (north is -y), so decreasing y walks up the screen. Topmost row
    // sits at the institution point; subsequent authors stack downward.
    var colStride = 6;
    for (var i = 0; i < count; i++) {
      positions[members[i].id] = { x: cx, y: cy + i * colStride };
    }
  });

  return positions;
};
// Colour by attribute — assign per-node colour from a palette
window.fpGenderPalette = { M: "#377EB8", F: "#E41A1C", Unknown: "#cccccc" };
window.fpRegionPalette = {
  "Europe": "#377EB8", "North America": "#E41A1C", "South America": "#FF7F00",
  "Africa": "#4DAF4A", "East Asia": "#984EA3", "South Asia": "#8DA0CB",
  "South-East Asia": "#A6D854", "Muslim": "#66C2A5", "Central Asia": "#F781BF",
  "Oceania": "#FFD700", "Unknown": "#cccccc"
};
window.fpSetColour = function(attr) {
  var nw = window.fpNetwork;
  if (!nw || !nw.body) return;
  var nodesDS = nw.body.data.nodes;
  var meta = window.fpNodesMeta || [];
  var palette;
  if (attr === "country")      palette = window.fpCountryPalette;
  else if (attr === "gender")  palette = window.fpGenderPalette;
  else if (attr === "origin_region") palette = window.fpRegionPalette;
  else palette = null;

  var nextHue = 0;
  var dynamicCache = {};
  var pickColour = function(key) {
    if (!key) return "#cccccc";
    if (palette && palette[key]) return palette[key];
    if (dynamicCache[key]) return dynamicCache[key];
    // Stable hashing for ethnicity or other unknown attributes
    var hue = (nextHue * 47) % 360;
    dynamicCache[key] = "hsl(" + hue + ",55%,55%)";
    nextHue++;
    return dynamicCache[key];
  };
  var updates = meta.map(function(n) {
    return { id: n.id, color: pickColour(n[attr]) };
  });
  nodesDS.update(updates);
  // Refresh the legend swatches
  if (window.fpBuildLegend) window.fpBuildLegend(attr);
};
window.fpBuildLegend = function(attr) {
  var container = document.getElementById("fp-legend-colors");
  if (!container) return;
  var palette;
  if (attr === "country") palette = window.fpCountryPalette;
  else if (attr === "gender") palette = window.fpGenderPalette;
  else if (attr === "origin_region") palette = window.fpRegionPalette;
  else palette = null;
  container.innerHTML = "";
  if (!palette) {
    container.innerHTML = "<em>palette auto-generated</em>";
    return;
  }
  Object.keys(palette).forEach(function(key) {
    var div = document.createElement("div");
    div.style.display = "flex";
    div.style.alignItems = "center";
    div.style.marginBottom = "2px";
    div.innerHTML = "<span style=\\"display:inline-block;width:10px;height:10px;background:" +
      palette[key] + ";border-radius:50%;margin-right:6px\\"></span>" + key;
    container.appendChild(div);
  });
  var others = document.createElement("div");
  others.style.color = "#777";
  others.style.marginTop = "3px";
  others.innerHTML = "<span style=\\"display:inline-block;width:10px;height:10px;background:#cccccc;border-radius:50%;margin-right:6px\\"></span>other";
  container.appendChild(others);
};
// Single source of truth: counter-zoom by updating EVERY node explicitly.
// screen_px = world_px * scale, so set world = target_screen_px / scale.
// setOptions on scaling was unreliable — per-node `size` + `font.size` wins.
window.fpApplyFont = function(scale) {
  var nw = window.fpNetwork;
  if (!nw || !nw.body || !nw.body.data || !nw.body.data.nodes) return;
  scale = scale || (nw.getScale ? nw.getScale() : 1);
  var nodesDS = nw.body.data.nodes;
  var meta = window.fpNodesMeta || [];

  var visibleCount = 0, totalCount = 0;
  nodesDS.forEach(function(n) { totalCount++; if (!n.hidden) visibleCount++; });

  // Default label-visibility policy by how many are shown + zoom level (+2pt)
  var screenFontPx = visibleCount >= totalCount ? 0
                   : visibleCount <= 20 ? 15
                   : visibleCount <= 60 ? 13
                   : visibleCount <= 200 ? 11
                   : 0;
  if (visibleCount >= totalCount && scale > 1.5) screenFontPx = 11;
  if (visibleCount >= totalCount && scale > 3)   screenFontPx = 13;
  if (visibleCount >= totalCount && scale > 5)   screenFontPx = 15;
  var worldFont = screenFontPx > 0 ? screenFontPx / scale : 0;

  // Selection mode overrides: only labels for selected + neighbours
  var selSet = window.fpSelectedSet;
  var useSelection = !!(selSet && selSet.size > 0);

  var updates = meta.map(function(n) {
    var papers = n.papers || 1;
    var targetRadius = Math.min(20, Math.max(3, Math.log(papers + 1) / Math.LN2 * 2.4));
    var showLabel;
    var labelPx;
    if (useSelection) {
      showLabel = selSet.has(n.id);
      labelPx = showLabel ? 15 / scale : 0;
    } else {
      showLabel = worldFont > 0;
      labelPx = worldFont;
    }
    return {
      id: n.id,
      size: targetRadius / scale,
      font: { size: labelPx,
              strokeWidth: Math.max(1, 2 / scale),
              strokeColor: "#ffffff",
              face: "sans" }
    };
  });
  nodesDS.update(updates);
  window.fpCurrentScale = scale;
  var dbg = document.getElementById("fp-debug-top");
  if (dbg) dbg.textContent = "zoom " + scale.toFixed(2) + " · label " + screenFontPx + "px · " + updates.length + " nodes" + (useSelection ? " · SEL" : "");
};
// Selection: hide non-connected edges, light up connected author labels.
window.fpSelectNode = function(nodeId) {
  var nw = window.fpNetwork;
  if (!nw || !nw.body || !nodeId) return;
  var connectedNodes = nw.getConnectedNodes(nodeId) || [];
  var selSet = new Set();
  selSet.add(nodeId);
  connectedNodes.forEach(function(nid) { selSet.add(nid); });
  window.fpSelectedSet = selSet;
  var connEdges = new Set((nw.getConnectedEdges(nodeId) || []));
  var edgesDS = nw.body.data.edges;
  var minW = parseInt(document.getElementById("fp-min-edge").value, 10) || 1;
  var updates = [];
  edgesDS.forEach(function(e) {
    var keepBase = e.value >= minW;  // respect the slider
    var keep = keepBase && connEdges.has(e.id);
    updates.push({ id: e.id, hidden: !keep });
  });
  edgesDS.update(updates);
  window.fpApplyFont();
};
window.fpDeselect = function() {
  window.fpSelectedSet = null;
  window.fpApplyEdgeWeight();  // restore edges per current slider
  window.fpApplyFont();
};
window.fpApply = function() {
  var c = document.getElementById("fp-country").value;
  var g = document.getElementById("fp-gender").value;
  var r = document.getElementById("fp-region").value;
  var e = document.getElementById("fp-ethnicity").value;
  var nw = window.fpNetwork;
  if (!nw || !nw.body || !nw.body.data || !nw.body.data.nodes) {
    console.warn("fpApply: network not ready, retrying in 500ms");
    setTimeout(window.fpApply, 500);
    return;
  }
  var nodesDS = nw.body.data.nodes;
  var keep = new Set();
  window.fpNodesMeta.forEach(function(n) {
    if (c && n.country !== c) return;
    if (g && n.gender !== g) return;
    if (r && n.origin_region !== r) return;
    if (e && n.ethnicity !== e) return;
    keep.add(n.id);
  });
  var allIds = nodesDS.getIds();
  var updates = allIds.map(function(id) {
    return { id: id, hidden: !keep.has(id) };
  });
  nodesDS.update(updates);
  window.fpApplyFont();
  document.getElementById("fp-stats").textContent =
    "Showing " + keep.size + " / " + allIds.length + " authors";
  console.log("fpApply: showing", keep.size, "/", allIds.length);
};
window.fpAuthorJump = function() {
  var val = document.getElementById("fp-author").value.trim();
  var nw = window.fpNetwork;
  if (!nw || !nw.body) return;
  if (!val) {
    // Clear search: show all per other filters
    window.fpApply();
    return;
  }
  var nodesDS = nw.body.data.nodes;
  var allIds = nodesDS.getIds();
  var matched = [];
  nodesDS.forEach(function(n) {
    if (n.label === val) matched.push(n.id);
  });
  if (matched.length === 0) {
    // Try substring match as fallback
    var lval = val.toLowerCase();
    nodesDS.forEach(function(n) {
      if (n.label.toLowerCase().indexOf(lval) !== -1) matched.push(n.id);
    });
  }
  if (matched.length === 0) {
    document.getElementById("fp-stats").textContent = "No match for " + val;
    return;
  }
  // Hide all non-matches and their non-neighbours; keep matches + 1-degree neighbours
  var show = new Set(matched);
  matched.forEach(function(id) {
    (nw.getConnectedNodes(id) || []).forEach(function(nid) { show.add(nid); });
  });
  var updates = allIds.map(function(id) {
    return {
      id: id,
      hidden: !show.has(id),
      font: { size: show.has(id) ? 18 : 0, strokeWidth: 4, strokeColor: "#ffffff" }
    };
  });
  nodesDS.update(updates);
  nw.selectNodes(matched);
  if (matched.length === 1) {
    nw.focus(matched[0], { scale: 2, animation: true });
  } else {
    nw.fit({ nodes: Array.from(show), animation: true });
  }
  document.getElementById("fp-stats").textContent =
    matched.length + " match(es) for " + val + " (showing " + show.size + " nodes with neighbours)";
};
// Wire up filter listeners immediately (they check fpNetwork at call time)
window.fpOnReady = function() {
  console.log("Network instance captured:", !!window.fpNetwork);
  document.getElementById("fp-country").value = "";
  document.getElementById("fp-gender").value = "";
  document.getElementById("fp-region").value = "";
  document.getElementById("fp-ethnicity").value = "";
  document.getElementById("fp-author").value = "";
  document.getElementById("fp-layout").value = "physics";
  document.getElementById("fp-colour").value = "country";
  document.getElementById("fp-min-edge").value = "2";
  document.getElementById("fp-min-edge-val").textContent = "2";
  window.fpApplyEdgeWeight();
  window.fpApply();
  window.fpBuildLegend("country");
  window.fpNetwork.fit({ animation: true });
  // Record the fit scale and use it as the minimum zoom
  setTimeout(function() {
    var s = window.fpNetwork.getScale ? window.fpNetwork.getScale() : 1;
    window.fpMinScale = s * 0.95;  // allow 5% margin for padding
  }, 600);
};
document.addEventListener("DOMContentLoaded", function() {
  console.log("[fp] DOMContentLoaded — wiring filter listeners");
  ["fp-country","fp-gender","fp-region","fp-ethnicity"].forEach(function(id) {
    var el = document.getElementById(id);
    if (el) el.addEventListener("change", window.fpApply);
  });
  var au = document.getElementById("fp-author");
  if (au) {
    au.addEventListener("change", window.fpAuthorJump);
    au.addEventListener("keydown", function(ev) {
      if (ev.key === "Enter") window.fpAuthorJump();
    });
    // Fire on datalist selection (click) — input event + exact-match check
    var authorLabels = new Set();
    var dl = document.getElementById("fp-author-list");
    if (dl) {
      for (var i = 0; i < dl.options.length; i++) authorLabels.add(dl.options[i].value);
    }
    au.addEventListener("input", function() {
      if (authorLabels.has(au.value)) {
        window.fpAuthorJump();
      }
    });
  }
  var lay = document.getElementById("fp-layout");
  if (lay) lay.addEventListener("change", function() {
    window.fpSetLayout(lay.value);
  });
  var col = document.getElementById("fp-colour");
  if (col) col.addEventListener("change", function() {
    window.fpSetColour(col.value);
  });
  var me = document.getElementById("fp-min-edge");
  if (me) me.addEventListener("input", function() {
    document.getElementById("fp-min-edge-val").textContent = me.value;
    window.fpApplyEdgeWeight();
  });
});
</script>')

idx <- grep("</head>", html, fixed = TRUE)[1]
html <- append(html, inject_style, after = idx - 1)
# Inject panel after <body>
idx <- grep("<body", html, fixed = TRUE)[1]
html <- append(html, panel_html, after = idx)
writeLines(html, OUTPUT_HTML)

cat(sprintf("Wrote %s\n", OUTPUT_HTML))

cat("\nDone.\n")
