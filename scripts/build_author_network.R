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

# --- Focal network: filter to authors with >= 3 papers and edges with weight >= 2 ---
MIN_PAPERS <- 3
MIN_EDGE_WEIGHT <- 2

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
  select(openalex_author_id, display_name, institution = most_common_institution,
         country = institution_country, papers = paper_count, gender = gender_final,
         origin_country = namsor_origin_country,
         origin_region = namsor_origin_region,
         ethnicity = namsor_ethnicity)
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
    title = sprintf(
      "<b>%s</b><br><i>%s</i><br>%s<br>%d papers<br>Gender: %s<br>Origin: %s (%s)<br>Ethnicity: %s",
      display_name,
      coalesce(institution, ""),
      coalesce(country, ""),
      papers,
      gender,
      coalesce(origin_country, "—"),
      coalesce(origin_region, "—"),
      coalesce(ethnicity, "—")
    ),
    value = pmin(papers, 50),
    group = coalesce(country, "Unknown"),
    # Short display label for dropdown
    labelDropdown = sprintf("%s (%d)", display_name, papers)
  ) |>
  select(id, label, title, value, group, labelDropdown,
         papers, gender, country, ethnicity, origin_region, origin_country, institution)

vis_edges <- edges_focal |>
  rename(value = weight) |>
  mutate(title = sprintf("%d shared papers", value))

# Build widget with multiple filter dimensions
vn <- visNetwork(vis_nodes, vis_edges,
                 height = "100vh", width = "100%",
                 main = sprintf("Elasmobranch Author Collaboration Atlas (%d authors, %d edges)",
                                nrow(vis_nodes), nrow(vis_edges)),
                 submain = "(lots of data: may take a while to load)") |>
  visNodes(
    shape = "dot",
    scaling = list(min = 4, max = 40),
    font = list(size = 0, face = "sans", strokeWidth = 3, strokeColor = "#ffffff")
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
    tooltipDelay = 100
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
    beforeDrawing = "function() {
      if (!window.fpNetwork) {
        window.fpNetwork = this;
      }
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

# Embed nodes data as JSON for client-side filtering
nodes_json <- jsonlite::toJSON(
  vis_nodes |> select(id, gender, country, ethnicity, origin_region),
  auto_unbox = FALSE
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
/* Tighten visNetwork header spacing */
h2.main { font-size: 1rem; margin: 0.2rem 0 0.1rem 0; }
h3.submain { font-size: 0.8rem; margin: 0 0 0.2rem 0; color: #718096; font-weight: normal; font-style: italic; }
/* Hide the default selectedBy/nodesIdSelection dropdowns, we replace them */
.vis-configuration-wrapper { display: none !important; }
</style>'

# Build filter panel HTML
panel_html <- paste0('<div class="filter-panel" id="filter-panel">
<h3>Elasmobranch Author Atlas</h3>
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
</div>
<script>
window.fpNodesMeta = ', nodes_json, ';
window.fpReset = function() {
  document.getElementById("fp-country").value = "";
  document.getElementById("fp-gender").value = "";
  document.getElementById("fp-region").value = "";
  document.getElementById("fp-ethnicity").value = "";
  document.getElementById("fp-author").value = "";
  window.fpApply();
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
  // Dynamic label sizing: show labels only when <=150 visible, scale by count
  var n = keep.size;
  var labelSize = n === allIds.length ? 0
                : n <= 20 ? 24
                : n <= 50 ? 18
                : n <= 150 ? 14
                : 0;
  var updates = allIds.map(function(id) {
    var visible = keep.has(id);
    return {
      id: id,
      hidden: !visible,
      font: { size: visible ? labelSize : 0, strokeWidth: 4, strokeColor: "#ffffff" }
    };
  });
  nodesDS.update(updates);
  document.getElementById("fp-stats").textContent =
    "Showing " + n + " / " + allIds.length + " authors" +
    (labelSize ? " (labels visible)" : " (filter down to ≤150 to see labels)");
  console.log("fpApply: showing", n, "/", allIds.length);
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
  // Apply any retained filter values from browser autofill/reload
  var hasSearch = document.getElementById("fp-author").value.trim();
  if (hasSearch) {
    window.fpAuthorJump();
  } else {
    window.fpApply();
  }
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
  }
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
