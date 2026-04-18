#!/usr/bin/env Rscript
# ============================================================================
# AUTHOR ATLAS — v2 data builder
# ============================================================================
# Produces canonical GeoJSON + JSON files for the MapLibre + deck.gl atlas.
# No visual layer here — this is the data step only. Visual layer is a
# separate React app that consumes these files.
#
# Reuses the same pipeline as build_author_network.R:
#   - author aliases (outputs/author_aliases.csv)
#   - location overrides (outputs/author_location_overrides.csv)
#   - last-known institutions (outputs/openalex_authors_last_institution.csv)
#
# Outputs (outputs/author_atlas/):
#   - authors.geojson      — one Point feature per author with full metadata
#   - institutions.geojson — one Point per institution cluster (author counts,
#                            top-N authors, aggregate paper counts)
#   - edges.json           — coauthor edges (weight = shared papers)
#   - stats.json           — summary counts for the UI (total authors etc.)
#
# Deploy step will copy outputs/author_atlas/ to docs/network_atlas/.
# ============================================================================

suppressPackageStartupMessages({
  library(tidyverse)
  library(jsonlite)
})

setwd("/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel")
OUT_DIR <- "outputs/author_atlas"
dir.create(OUT_DIR, recursive = TRUE, showWarnings = FALSE)

cat("Loading source data...\n")
authors       <- read_csv("outputs/openalex_unique_authors.csv", show_col_types = FALSE)

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
paper_authors <- read_csv("outputs/openalex_paper_authors.csv",  show_col_types = FALSE)
namsor        <- read_csv("outputs/namsor_enrichment.csv",       show_col_types = FALSE)

last_inst_path <- if (file.exists("outputs/openalex_authors_last_institution.openalex_api.csv")) {
  "outputs/openalex_authors_last_institution.openalex_api.csv"
} else {
  "outputs/openalex_authors_last_institution.csv"
}
last_inst <- if (file.exists(last_inst_path)) {
  x <- read_csv(last_inst_path, show_col_types = FALSE) |>
    mutate(openalex_author_id = str_remove(openalex_author_id, "https://openalex.org/"))
  ov_path <- "outputs/author_location_overrides.csv"
  if (file.exists(ov_path)) {
    ov <- read_csv(ov_path, show_col_types = FALSE) |>
      mutate(openalex_author_id = str_remove(openalex_author_id, "https://openalex.org/"))
    x <- x |>
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
    cat(sprintf("  Applied %d location overrides\n", nrow(ov)))
  }
  x
} else NULL

# --- Author meta with enrichment -------------------------------------------
namsor_clean <- namsor |>
  mutate(openalex_author_id = str_remove(id, "https://openalex.org/")) |>
  select(openalex_author_id, namsor_gender, namsor_origin_country,
         namsor_origin_region, namsor_origin_subregion, namsor_ethnicity)

author_meta <- authors |>
  mutate(openalex_author_id = str_remove(openalex_author_id, "https://openalex.org/")) |>
  left_join(namsor_clean, by = "openalex_author_id") |>
  mutate(gender_final = case_when(
    namsor_gender %in% c("M", "male")   ~ "M",
    namsor_gender %in% c("F", "female") ~ "F",
    gender %in% c("male")               ~ "M",
    gender %in% c("female")             ~ "F",
    TRUE                                 ~ "Unknown"
  ))

if (!is.null(last_inst)) {
  author_meta <- author_meta |>
    left_join(last_inst, by = "openalex_author_id") |>
    mutate(
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
      inst_city = NA_character_, inst_region = NA_character_,
      inst_lat = NA_real_, inst_lon = NA_real_
    )
}

# --- Alias merge (drop duplicate profiles) --------------------------------
aliases_path <- "outputs/author_aliases.csv"
if (file.exists(aliases_path)) {
  aliases <- read_csv(aliases_path, show_col_types = FALSE) |>
    select(alias_openalex_id, canonical_openalex_id, canonical_name_override = canonical_name)
  cat(sprintf("  Loaded %d author aliases\n", nrow(aliases)))

  remap_ids <- function(ids) {
    hits <- aliases$canonical_openalex_id[match(ids, aliases$alias_openalex_id)]
    coalesce(hits, ids)
  }

  paper_authors <- paper_authors |>
    mutate(openalex_author_id = str_remove(openalex_author_id, "https://openalex.org/"),
           openalex_author_id = remap_ids(openalex_author_id))

  # Pick up expanded canonical_name for canonicals touched by an expansion-merge
  canonical_name_map <- aliases |>
    distinct(canonical_openalex_id, canonical_name_override)

  author_meta <- author_meta |>
    filter(!openalex_author_id %in% aliases$alias_openalex_id) |>
    left_join(canonical_name_map,
              by = c("openalex_author_id" = "canonical_openalex_id")) |>
    mutate(display_name = coalesce(canonical_name_override, display_name)) |>
    select(-canonical_name_override)

  new_counts <- paper_authors |>
    filter(!is.na(literature_id), !is.na(openalex_author_id)) |>
    distinct(literature_id, openalex_author_id) |>
    count(openalex_author_id, name = "new_paper_count")

  author_meta <- author_meta |>
    left_join(new_counts, by = "openalex_author_id") |>
    mutate(paper_count = coalesce(new_paper_count, paper_count)) |>
    select(-new_paper_count)
  cat(sprintf("  After alias merge: %d authors\n", nrow(author_meta)))
}

# --- Coauthor edges --------------------------------------------------------
cat("Building coauthor edges...\n")
paper_author_clean <- paper_authors |>
  filter(!is.na(literature_id), !is.na(openalex_author_id)) |>
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
  mutate(from = sapply(pairs, `[`, 1),
         to   = sapply(pairs, `[`, 2)) |>
  select(from, to) |>
  count(from, to, name = "weight")

# --- Focal network: authors with >=3 papers, edges weight >=1 -------------
MIN_PAPERS <- 3
focal_authors <- author_meta |> filter(paper_count >= MIN_PAPERS)
focal_ids <- focal_authors$openalex_author_id
edges_focal <- coauthor_edges |>
  filter(from %in% focal_ids & to %in% focal_ids)

connected_ids <- unique(c(edges_focal$from, edges_focal$to))
nodes_focal <- focal_authors |> filter(openalex_author_id %in% connected_ids)

cat(sprintf("Focal network: %d authors, %d edges\n",
            nrow(nodes_focal), nrow(edges_focal)))

# --- GeoJSON: authors -----------------------------------------------------
# One Point feature per author with coordinates. Drop authors without
# institution coordinates (they have no place on a map).
authors_geo <- nodes_focal |>
  filter(!is.na(inst_lon), !is.na(inst_lat)) |>
  transmute(
    id = openalex_author_id,
    name = display_name,
    institution = institution_final,
    city = inst_city,
    region = inst_region,
    country = country_final,
    papers = paper_count,
    gender = gender_final,
    origin_country = namsor_origin_country,
    origin_region  = namsor_origin_region,
    ethnicity      = namsor_ethnicity,
    lon = inst_lon,
    lat = inst_lat
  )

cat(sprintf("Authors on map: %d (%.1f%% of focal)\n",
            nrow(authors_geo), 100 * nrow(authors_geo) / nrow(nodes_focal)))

# Build feature list without allocating 30K individual lists (manual geojson)
build_feature_collection <- function(df, lon_col = "lon", lat_col = "lat") {
  feats <- vector("list", nrow(df))
  lon <- df[[lon_col]]; lat <- df[[lat_col]]
  prop_df <- df |> select(-all_of(c(lon_col, lat_col)))
  for (i in seq_len(nrow(df))) {
    feats[[i]] <- list(
      type = "Feature",
      geometry = list(type = "Point", coordinates = c(lon[i], lat[i])),
      properties = as.list(prop_df[i, ])
    )
  }
  list(type = "FeatureCollection", features = feats)
}

authors_fc <- build_feature_collection(authors_geo)
write(toJSON(authors_fc, auto_unbox = TRUE, digits = 5, na = "null"),
      file = file.path(OUT_DIR, "authors.geojson"))
cat(sprintf("Wrote %s/authors.geojson\n", OUT_DIR))

# --- GeoJSON: institutions (aggregated clusters) --------------------------
institutions <- authors_geo |>
  mutate(lon_rnd = round(lon, 3), lat_rnd = round(lat, 3)) |>
  group_by(lon_rnd, lat_rnd, institution) |>
  summarise(
    lon = mean(lon), lat = mean(lat),
    city = first(city), region = first(region), country = first(country),
    author_count = n(),
    total_papers = sum(papers),
    author_ids = list(id),
    top_authors = paste(head(name[order(-papers)], 5), collapse = " · "),
    .groups = "drop"
  ) |>
  arrange(desc(author_count))

# Flatten author_ids into a comma-joined string for GeoJSON props (JSON
# doesn't support nested arrays in a CSV-y way, but strings are safe).
institutions <- institutions |>
  mutate(author_ids = sapply(author_ids, function(ids) paste(ids, collapse = ",")))

inst_fc <- build_feature_collection(institutions |>
                                    select(-lon_rnd, -lat_rnd))
write(toJSON(inst_fc, auto_unbox = TRUE, digits = 5, na = "null"),
      file = file.path(OUT_DIR, "institutions.geojson"))
cat(sprintf("Wrote %s/institutions.geojson (%d clusters)\n",
            OUT_DIR, nrow(institutions)))

# --- Edges JSON -----------------------------------------------------------
# Keep only edges between authors that made it onto the map.
mapped_ids <- authors_geo$id
edges_out <- edges_focal |>
  filter(from %in% mapped_ids & to %in% mapped_ids) |>
  rename(weight = weight)

write(toJSON(edges_out, auto_unbox = TRUE, na = "null"),
      file = file.path(OUT_DIR, "edges.json"))
cat(sprintf("Wrote %s/edges.json (%d edges)\n", OUT_DIR, nrow(edges_out)))

# --- Summary stats --------------------------------------------------------
stats <- list(
  build_timestamp  = format(Sys.time(), "%Y-%m-%d %H:%M:%S %Z"),
  total_authors    = nrow(authors_geo),
  total_institutions = nrow(institutions),
  total_edges      = nrow(edges_out),
  by_country = as.list(authors_geo |> count(country, sort = TRUE) |>
                       head(20) |> deframe()),
  by_gender  = as.list(authors_geo |> count(gender) |> deframe()),
  min_papers = MIN_PAPERS
)
write(toJSON(stats, auto_unbox = TRUE, pretty = TRUE, na = "null"),
      file = file.path(OUT_DIR, "stats.json"))
cat(sprintf("Wrote %s/stats.json\n", OUT_DIR))

cat("\nDone.\n")
