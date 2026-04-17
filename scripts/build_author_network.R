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

cat("Loading data...\n")
authors <- read_csv("outputs/openalex_unique_authors.csv", show_col_types = FALSE)
paper_authors <- read_csv("outputs/openalex_paper_authors.csv", show_col_types = FALSE)
namsor <- read_csv("outputs/namsor_enrichment.csv", show_col_types = FALSE)

# Optional enrichment files (from scripts/enrich_author_last_institutions.py)
last_inst_path <- "outputs/openalex_authors_last_institution.csv"
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
    # Log-scale size: log2(papers+1) * 3 gives range ~3-24 for 0-240 papers
    value = log2(papers + 1) * 3,
    group = coalesce(country, "Unknown"),
    labelDropdown = sprintf("%s (%d)", display_name, papers)
  ) |>
  select(id, label, title, value, group, labelDropdown,
         papers, gender, country, ethnicity, origin_region, origin_country,
         institution, inst_city, inst_region, inst_lat, inst_lon)

vis_edges <- edges_focal |>
  rename(value = weight) |>
  mutate(
    title = sprintf("%d shared papers", value),
    # Log-scaled width for visual clarity (many edges = thick line drowns out the rest)
    width = log2(value + 1) * 0.8
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
    scaling = list(
      min = 4, max = 60,
      label = list(enabled = FALSE)
    ),
    # size here is in absolute pixels, not affected by zoom
    font = list(size = 0, face = "sans", strokeWidth = 3, strokeColor = "#ffffff"),
    labelHighlightBold = FALSE
  ) |>
  visEdges(
    smooth = FALSE,
    color = list(color = "#c8d0dc", highlight = "#B6862C"),
    scaling = list(min = 0.5, max = 4)
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
      if (!window.fpNetwork) {
        window.fpNetwork = this;
      }
      // Draw equirectangular world map as background in geographic layout mode
      if (window.fpMapImage && window.fpMapImage.complete &&
          document.body.classList.contains('geo-layout')) {
        var scale = 60;
        // World spans lon -180..180, lat -90..90, with our x=lon*scale, y=-lat*scale
        var left = -180 * scale;
        var top  = -90 * scale;
        var width  = 360 * scale;
        var height = 180 * scale;
        ctx.save();
        ctx.globalAlpha = 0.35;
        ctx.drawImage(window.fpMapImage, left, top, width, height);
        ctx.restore();
      }
    }",
    zoom = "function(params) {
      // Counter-zoom: vis-network draws in a scaled canvas so font.size and node radii
      // are multiplied by zoom on screen. Divide by scale to hold constant screen pixels.
      var scale = params.scale || 1;
      if (window.fpLastZoomApply && Math.abs((window.fpLastZoomApply - scale) / scale) < 0.05) return;
      window.fpLastZoomApply = scale;
      window.fpApplyFont(scale);
    }"
  )

saveWidget(vn, "docs/network/index.html", selfcontained = TRUE,
           title = "Elasmobranch Author Collaboration Atlas")

# Post-process: inject CSS + custom filter sidebar
html <- readLines("docs/network/index.html")

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

make_opts <- function(values) {
  paste0('<option value="', values, '">', values, '</option>', collapse = "\n")
}

inject_style <- '<style>
html, body { margin: 0; padding: 0; height: 100%; overflow: hidden; font-family: -apple-system, system-ui, sans-serif; }
.html-widget { width: 100vw !important; height: 100vh !important; }
#htmlwidget_container { width: 100vw !important; height: 100vh !important; }
div.vis-network { width: 100vw !important; height: 100vh !important; }

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

# Build filter panel HTML
panel_html <- paste0('<div class="filter-panel" id="filter-panel">
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
  <div><strong>Node colour</strong>: institution country (hover for details)</div>
  <div><strong>Edge width</strong>: shared papers (log scale)</div>
  <div><strong>Edge alpha</strong>: same</div>
</div>
</div>
<script>
window.fpNodesMeta = ', nodes_json, ';
window.fpIsoCoords = ', iso_coords_json, ';
// Preload world map image for geographic layout background
window.fpMapImage = new Image();
window.fpMapImage.src = "assets/world_equirect.png";
window.fpMapImage.onload = function() {
  if (window.fpNetwork) window.fpNetwork.redraw();
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
  var nw = window.fpNetwork;
  if (!nw || !nw.body) return;
  // Toggle class so beforeDrawing knows whether to render the map
  if (mode === "geo-inst" || mode === "geo-origin") {
    document.body.classList.add("geo-layout");
  } else {
    document.body.classList.remove("geo-layout");
  }
  // Trigger a redraw to paint (or clear) the map background
  if (nw.redraw) nw.redraw();
  var nodesDS = nw.body.data.nodes;
  var meta = window.fpNodesMeta;
  if (mode === "physics") {
    // Seed with random positions in a bounded area so nodes do not stay
    // stuck in geographic grid; then re-enable physics to converge.
    var updates = meta.map(function(n) {
      return {
        id: n.id,
        x: (Math.random() - 0.5) * 800,
        y: (Math.random() - 0.5) * 800,
        fixed: { x: false, y: false }
      };
    });
    nodesDS.update(updates);
    nw.setOptions({
      physics: {
        enabled: true,
        solver: "forceAtlas2Based",
        forceAtlas2Based: { gravitationalConstant: -50, springLength: 100 },
        stabilization: { enabled: true, iterations: 300, fit: true }
      }
    });
    setTimeout(function() {
      nw.setOptions({ physics: false });
      nw.fit({ animation: true });
    }, 3000);
    return;
  }
  // Geographic layouts: compute positions with institution-level jitter
  nw.setOptions({ physics: false });
  var positions = window.fpComputePositions(meta, mode);
  var updates = meta.map(function(n) {
    var p = positions[n.id];
    if (!p) return { id: n.id, hidden: true };
    return { id: n.id, x: p.x, y: p.y, fixed: { x: true, y: true }, hidden: false };
  });
  nodesDS.update(updates);
  setTimeout(function() { nw.fit({ animation: true }); }, 200);
};
// Deterministic 32-bit hash of a string
window.fpHash = function(s) {
  var h = 0;
  for (var i = 0; i < s.length; i++) { h = ((h << 5) - h) + s.charCodeAt(i); h |= 0; }
  return h;
};
// Geographic positions with institution-based clustering.
// Authors at same institution are placed in a spiral around the institution point
// (radius scales with count) to avoid stacking.
window.fpComputePositions = function(meta, mode) {
  var positions = {};
  var scale = 60;
  var instJitter = 180;       // fallback when only country-level coords available

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

    // Place members on concentric rings. Nodes sized log2(papers+1)*3,
    // so radius ~10-16px per node. Stride rings every ~14px.
    members.sort(function(a, b) { return b.papers - a.papers; });

    if (count === 1) {
      positions[members[0].id] = { x: cx, y: cy };
      return;
    }

    // Spiral placement — node slots sized for max node radius ~30px + 15px gap = 45px
    // Ring stride 50 units; ring 1 at 55 gives a ~25-unit gap around the centre node.
    var placed = 0;
    var ring = 0;
    var slot = 50;
    while (placed < count) {
      var ringRadius = ring === 0 ? 0 : slot * ring + 5;
      var ringCapacity = ring === 0 ? 1 : Math.max(6, Math.floor(2 * Math.PI * ringRadius / slot));
      var toPlace = Math.min(ringCapacity, count - placed);
      for (var i = 0; i < toPlace; i++) {
        var angle = (2 * Math.PI * i) / toPlace + (ring * 0.5);
        var x = cx + ringRadius * Math.cos(angle);
        var y = cy + ringRadius * Math.sin(angle);
        positions[members[placed].id] = { x: x, y: y };
        placed++;
      }
      ring++;
    }
  });

  return positions;
};
// Colour by attribute — change node group on the fly
window.fpSetColour = function(attr) {
  var nw = window.fpNetwork;
  if (!nw || !nw.body) return;
  var nodesDS = nw.body.data.nodes;
  var meta = window.fpNodesMeta;
  var updates = meta.map(function(n) {
    return { id: n.id, group: (n[attr] || "Unknown") };
  });
  nodesDS.update(updates);
};
// Single source of truth for font size and node radii: counter-zoom via setOptions.
// screen_px = world_size * scale, so set world = target_px / scale.
window.fpApplyFont = function(scale) {
  var nw = window.fpNetwork;
  if (!nw) return;
  scale = scale || (nw.getScale ? nw.getScale() : 1);
  // How many nodes currently visible determines label pixel size
  var visibleCount = 0;
  var totalCount = 0;
  if (nw.body && nw.body.data && nw.body.data.nodes) {
    nw.body.data.nodes.forEach(function(n) {
      totalCount++;
      if (!n.hidden) visibleCount++;
    });
  }
  // Target SCREEN pixel size (kept constant regardless of zoom)
  var screenFontPx = visibleCount >= totalCount ? 0
                   : visibleCount <= 20 ? 13
                   : visibleCount <= 60 ? 11
                   : visibleCount <= 200 ? 9
                   : 0;
  // If all are shown, show labels only if the user has zoomed in enough
  if (visibleCount >= totalCount && scale > 2.2) screenFontPx = 9;
  if (visibleCount >= totalCount && scale > 4)   screenFontPx = 11;
  if (visibleCount >= totalCount && scale > 7)   screenFontPx = 13;

  nw.setOptions({
    nodes: {
      font: {
        size: screenFontPx / scale,
        strokeWidth: Math.max(1.5, 3 / scale),
        strokeColor: "#ffffff",
        face: "sans"
      },
      scaling: {
        min: 4 / scale,
        max: 18 / scale,
        label: { enabled: false }
      }
    }
  });
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
  // Reset UI control values to defaults, but do NOT re-seed node positions
  // (visNetwork has already stabilised its own good layout).
  document.getElementById("fp-country").value = "";
  document.getElementById("fp-gender").value = "";
  document.getElementById("fp-region").value = "";
  document.getElementById("fp-ethnicity").value = "";
  document.getElementById("fp-author").value = "";
  document.getElementById("fp-layout").value = "physics";
  document.getElementById("fp-colour").value = "country";
  document.getElementById("fp-min-edge").value = "2";
  document.getElementById("fp-min-edge-val").textContent = "2";
  // Apply default edge filter (hide weight<2)
  window.fpApplyEdgeWeight();
  window.fpApply();
  window.fpNetwork.fit({ animation: true });
};
document.addEventListener("DOMContentLoaded", function() {
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
writeLines(html, "docs/network/index.html")

cat("Wrote docs/network/index.html\n")

cat("\nDone.\n")
