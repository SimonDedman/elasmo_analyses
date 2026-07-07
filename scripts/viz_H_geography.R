## viz_H_geography.R
## Geography figures (H1-H5) for the EEA 2025 Data Panel, built on the newly
## merged geo_ columns in outputs/literature_review_enriched.parquet.
## Coverage is sparse (~18.6% of papers, ~5,885) — every figure drops NA rows
## for its own fields and reports n in the subtitle/caption.
##
##   H1  spatial_study_location_choropleth  - where research was DONE (geo_study_country)
##   H2  spatial_study_site_density         - country-level study-effort bubble map
##                                             (geo_study_country centroids; geo_study_latitude/
##                                             longitude are corrupt - see H2 section below - and
##                                             are never used for plotting)
##   H3  parachute_science_top_countries    - top study countries by % foreign-first-author
##   H4  author_to_study_country_flow       - alluvial: author country -> study country
##   H5  study_basin_geo_vs_textmined       - geo_study_ocean_basin vs text-mined b_ columns
##
## Style cloned (not edited) from:
##   viz_A_spatial.R                 -> map theme, Natural Earth basemap, Robinson proj
##   viz_basin_barchart_per_coastline.R -> bar theme
##   viz_D_bars_E1_sankey.R          -> bar/sankey theme, ggalluvial usage, save_plot()
##
## Reads outputs/literature_review_enriched.parquet fresh each run (read-only;
## a background enrichment job may still be appending geo_ matches).

suppressPackageStartupMessages({
  library(tidyverse)
  library(sf)
  library(rnaturalearth)
  library(ggrepel)
  library(ggalluvial)
  library(arrow)
  library(scales)
})

base_dir <- "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
fig_dir  <- file.path(base_dir, "outputs/figures")
dir.create(fig_dir, showWarnings = FALSE, recursive = TRUE)

# ---------------------------------------------------------------------------
# Data (read-only; literature_id coerced to character per project convention)
# ---------------------------------------------------------------------------
options(arrow.skip_nul = TRUE)  # some evidence/text fields carry embedded NUL bytes
pq_path <- file.path(base_dir, "outputs/literature_review_enriched.parquet")
df <- read_parquet(pq_path) |>
  mutate(literature_id = as.character(literature_id)) |>
  filter(!is.na(year), year >= 1950, year <= 2025)

n_total <- nrow(df)
cat("Papers loaded:", comma(n_total), "\n")
cat("  geo_first_author_country :", sum(!is.na(df$geo_first_author_country)), "\n")
cat("  geo_study_country        :", sum(!is.na(df$geo_study_country)), "\n")
cat("  geo_study_latitude       :", sum(!is.na(df$geo_study_latitude)), "\n")
cat("  geo_is_parachute_research:", sum(!is.na(df$geo_is_parachute_research)), "\n")
cat("  geo_study_ocean_basin    :", sum(!is.na(df$geo_study_ocean_basin)), "\n")

# ---------------------------------------------------------------------------
# Shared themes + helpers (cloned verbatim from the template scripts)
# ---------------------------------------------------------------------------
# Map theme (pale-blue "ocean" panel) - from viz_A_spatial.R
theme_eea_map <- theme_minimal(base_size = 12) +
  theme(
    plot.background   = element_rect(fill = "white", colour = NA),
    panel.background  = element_rect(fill = "#E8F4FD", colour = NA),
    legend.background = element_rect(fill = "white", colour = NA),
    plot.title        = element_text(face = "bold", size = 14),
    plot.subtitle     = element_text(colour = "grey40"),
    plot.caption      = element_text(colour = "grey45", size = 8.5, hjust = 0),
    axis.text         = element_blank(),
    axis.ticks        = element_blank(),
    panel.grid        = element_line(colour = "grey90", linewidth = 0.2)
  )

# Bar/sankey theme (plain white panel) - from viz_D_bars_E1_sankey.R
theme_eea <- theme_minimal(base_size = 12) +
  theme(
    plot.background   = element_rect(fill = "white", colour = NA),
    panel.background  = element_rect(fill = "white", colour = NA),
    legend.background = element_rect(fill = "white", colour = NA),
    plot.title        = element_text(face = "bold", size = 14),
    plot.subtitle     = element_text(colour = "grey40"),
    plot.caption      = element_text(colour = "grey45", size = 8.5, hjust = 0)
  )

save_plot <- function(p, name, w = 14, h = 9) {
  ggsave(file.path(fig_dir, paste0(name, ".png")), p,
         width = w, height = h, dpi = 300, bg = "white")
  ggsave(file.path(fig_dir, paste0(name, ".pdf")), p,
         width = w, height = h, bg = "white")
  cat("Saved:", name, "\n")
}

# World basemap (Natural Earth, Robinson projection) - matches viz_A_spatial.R
world    <- ne_countries(scale = "medium", returnclass = "sf")
robinson <- "+proj=robin +lon_0=0 +x_0=0 +y_0=0 +datum=WGS84"

# The geo_ country strings match Natural Earth's name/name_long/admin/
# sovereignt fields directly for every country EXCEPT these two shorthands
# (checked against the full unique set of geo_first_author_country /
# geo_study_country values).
fix_country <- function(x) case_when(
  x == "USA" ~ "United States of America",
  x == "UK"  ~ "United Kingdom",
  TRUE ~ x
)

# Join key: adm0_a3 (NOT iso_a3 - Natural Earth records iso_a3 = "-99" for
# France and Norway, a known upstream quirk; adm0_a3 is complete and unique).
world_lookup <- st_drop_geometry(world) |>
  select(adm0_a3, name, name_long, admin) |>
  pivot_longer(-adm0_a3, values_to = "key") |>
  distinct(adm0_a3, key)

match_adm0 <- function(country_vec) {
  tibble(country = country_vec, key = fix_country(country_vec)) |>
    left_join(world_lookup, by = "key") |>
    pull(adm0_a3)
}

# ---------------------------------------------------------------------------
# H1. Study-location choropleth — WHERE THE RESEARCH WAS DONE
# ---------------------------------------------------------------------------
cat("\nBuilding H1: study-location choropleth...\n")

study_counts <- df |>
  filter(!is.na(geo_study_country)) |>
  count(geo_study_country, name = "n") |>
  mutate(adm0_a3 = match_adm0(geo_study_country))

if (any(is.na(study_counts$adm0_a3))) {
  warning("H1: unmatched countries -> ",
          paste(study_counts$geo_study_country[is.na(study_counts$adm0_a3)], collapse = ", "))
}
n_h1 <- sum(study_counts$n)

world_h1 <- world |> left_join(study_counts |> select(adm0_a3, n), by = "adm0_a3")

p_h1 <- ggplot(world_h1) +
  geom_sf(aes(fill = n), colour = "grey60", linewidth = 0.15) +
  scale_fill_viridis_c(option = "plasma", name = "Papers", labels = comma, na.value = "grey85") +
  coord_sf(crs = robinson) +
  labs(
    title    = "Where elasmobranch research is actually done",
    subtitle = paste0(
      "Papers by STUDY-SITE country (geo_study_country) - not author affiliation. n = ",
      comma(n_h1), " papers with a known study country (",
      round(100 * n_h1 / n_total, 1), "% of ", comma(n_total), ")"
    ),
    caption  = "Contrasts with author-location geography: study location often differs from where authors are based (see H3/H4)."
  ) +
  theme_eea_map

save_plot(p_h1, "H1_spatial_study_location_choropleth", w = 14, h = 8)

# ---------------------------------------------------------------------------
# H2. Study-effort hotspot map — proportional-symbol (bubble) map by country
# ---------------------------------------------------------------------------
# DATA-QUALITY NOTE (verified 2026-07-06): geo_study_latitude / geo_study_longitude
# are CORRUPT and must NEVER be used for plotting. All 914 non-NA values are
# positive (lat range 0-89, lon range 0-176) with arbitrary magnitudes - e.g.
# Australia is recorded at lat 13/lon 30, Brazil at lat 15/lon 16. This is not
# a salvageable sign-flip (Southern Hemisphere countries just need lat*-1):
# the magnitudes themselves bear no relation to the true location, so every
# "study site" collapses into the +lat/+lon quadrant regardless of the
# country's real hemisphere. H2 is therefore built from geo_study_country
# instead (reliable, n ~ 3,650 - the same field H1 uses), geocoded to each
# country's polygon centroid and sized proportionally to paper count.
cat("\nBuilding H2: study-effort hotspot bubble map (by geo_study_country)...\n")

# Reuses study_counts / adm0_a3 matching already computed for H1 above.
n_h2 <- n_h1

centroids_h2 <- suppressWarnings(
  world |>
    inner_join(study_counts |> select(adm0_a3, n), by = "adm0_a3") |>
    st_centroid()
)

p_h2 <- ggplot() +
  geom_sf(data = world, fill = "grey85", colour = "grey65", linewidth = 0.15) +
  geom_sf(data = centroids_h2, aes(size = n), shape = 21, fill = "#d6604d",
          colour = "grey15", alpha = 0.75, stroke = 0.3) +
  scale_size_area(max_size = 18, name = "Papers", labels = comma) +
  coord_sf(crs = robinson) +
  labs(
    title    = "Study-effort hotspots: papers per study-site country",
    subtitle = paste0(
      "Bubble area = papers by STUDY-SITE country (geo_study_country), plotted at each country's ",
      "polygon centroid - not exact site coordinates. n = ", comma(n_h2),
      " papers with a known study country (",
      round(100 * n_h2 / n_total, 1), "% of ", comma(n_total), ")"
    ),
    caption  = str_wrap(paste0(
      "Country-level hotspot map (bubbles at country centroids, not true study-site points). ",
      "Raw extracted study-site coordinates (geo_study_latitude/geo_study_longitude) are a known ",
      "text-extraction artefact - all values positive with arbitrary magnitude (e.g. Australia at ",
      "lat 13/lon 30) - and are not usable; this figure uses geo_study_country instead. See H1 for ",
      "the equivalent choropleth."
    ), width = 150)
  ) +
  theme_eea_map

save_plot(p_h2, "H2_spatial_study_site_density", w = 14, h = 9)

# ---------------------------------------------------------------------------
# H3. Parachute science — top study countries by % foreign-first-author
# ---------------------------------------------------------------------------
cat("\nBuilding H3: parachute science bar...\n")

parachute_country <- df |>
  filter(!is.na(geo_study_country), !is.na(geo_is_parachute_research)) |>
  group_by(geo_study_country) |>
  summarise(n = n(), n_parachute = sum(geo_is_parachute_research == 1), .groups = "drop") |>
  mutate(pct_parachute = 100 * n_parachute / n) |>
  filter(n >= 5) |>
  slice_max(pct_parachute, n = 20, with_ties = FALSE) |>
  mutate(geo_study_country = fct_reorder(geo_study_country, pct_parachute))

n_h3 <- sum(parachute_country$n)

p_h3 <- ggplot(parachute_country, aes(x = geo_study_country, y = pct_parachute)) +
  geom_col(fill = "#d6604d") +
  geom_text(aes(label = paste0(round(pct_parachute), "% (", n_parachute, "/", n, ")")),
            hjust = -0.05, size = 3.2, colour = "grey20") +
  coord_flip(clip = "off") +
  scale_y_continuous(limits = c(0, 112), expand = c(0, 0)) +
  labs(
    title    = "\"Parachute science\": foreign-first-author share by study country",
    subtitle = paste0(
      "Top 20 study countries with >=5 geo-tagged papers, ranked by % where the first ",
      "author's country != the study country (n = ", comma(n_h3), " papers)"
    ),
    x = NULL, y = "% of geo-tagged papers that are parachute research"
  ) +
  theme_eea +
  theme(axis.text.x = element_text(angle = 0, hjust = 0.5),
        plot.margin = margin(5.5, 45, 5.5, 5.5))

save_plot(p_h3, "H3_parachute_science_top_countries", w = 12, h = 9)

# ---------------------------------------------------------------------------
# H4. Author -> study-country flow (alluvial): cross-border ("parachute-style")
# flows only. Same-country pairs are self-loops (most research is done locally
# - not interesting) and are dropped; the traditional first-world research
# hubs are dropped from the RIGHT (study-country) side only, so the figure
# highlights who is doing foreign-led research, not who receives it.
# ---------------------------------------------------------------------------
cat("\nBuilding H4: author -> study country flow (cross-border only)...\n")

# Country strings as they appear in geo_study_country. Both "USA"/"United
# States" and "UK"/"United Kingdom" spellings are matched for robustness, but
# the corpus currently uses "USA"/"UK". Edit this vector to change which
# destinations are excluded from the RIGHT axis; these countries are still
# allowed on the LEFT (author) axis.
h4_excluded_destinations <- c("USA", "United States", "Australia",
                               "UK", "United Kingdom", "Canada", "Japan")
h4_excluded_display <- c("USA", "Australia", "UK", "Canada", "Japan")  # for the caption, deduped

norm_country <- function(x) str_squish(str_to_lower(x))
h4_excluded_norm <- norm_country(h4_excluded_destinations)

flow_raw <- df |>
  filter(!is.na(geo_first_author_country), !is.na(geo_study_country)) |>
  mutate(
    author_norm = norm_country(geo_first_author_country),
    study_norm  = norm_country(geo_study_country)
  ) |>
  filter(author_norm != study_norm) |>                       # drop same-country self-loops
  filter(!study_norm %in% h4_excluded_norm) |>                # drop major-hub destinations
  count(geo_first_author_country, geo_study_country, name = "freq")

n_h4_pairs <- sum(flow_raw$freq)
n_h4_unique_pairs <- nrow(flow_raw)

# Every ribbon must land on a NAMED author country and a NAMED study country -
# no "Other" catch-all bucket. We keep every cross-border flow at or above a
# minimum paper count, tuned to keep the figure legible (~25-40 named flows).
# Raise this threshold if the alluvial gets too dense; do not re-introduce
# an "Other" node.
h4_min_flow <- 6

flow_df <- flow_raw |>
  filter(freq >= h4_min_flow) |>
  transmute(Author = geo_first_author_country, Study = geo_study_country, freq)

n_h4 <- sum(flow_df$freq)
cat("  H4 named cross-border flows (freq >=", h4_min_flow, "):", nrow(flow_df),
    "| papers covered:", n_h4, "of", comma(n_h4_pairs), "cross-border pairs |",
    n_distinct(flow_df$Author), "author x", n_distinct(flow_df$Study), "study countries\n")

alluv_df <- flow_df |>
  to_lodes_form(axes = 1:2, key = "axis", value = "stratum", id = "alluvium") |>
  mutate(axis_label = recode(axis, "1" = "First-author country", "2" = "Study country"))

strata <- sort(unique(alluv_df$stratum))
pal_h4 <- setNames(scales::hue_pal()(length(strata)), strata)

p_h4 <- ggplot(alluv_df,
               aes(x = axis_label, stratum = stratum, alluvium = alluvium,
                   y = freq, fill = stratum, label = stratum)) +
  geom_alluvium(alpha = 0.6, width = 1/4) +
  geom_stratum(width = 1/4, colour = "white") +
  geom_text(stat = "stratum", size = 3, fontface = "bold") +
  scale_fill_manual(values = pal_h4) +
  scale_x_discrete(expand = c(0.08, 0.08)) +
  labs(
    title    = "Parachute science: cross-border first-author -> study-country flows",
    subtitle = paste0(
      "Same-country (locally-led) pairs excluded; major-hub destinations (",
      paste(h4_excluded_display, collapse = ", "), ") excluded from the study-country axis.\n",
      "Every named country pair with >=", h4_min_flow, " papers shown (", nrow(flow_df),
      " flows, no \"Other\" bucket); n = ", comma(n_h4), " cross-border, non-hub-destination papers"
    ),
    x = NULL, y = "Number of papers"
  ) +
  guides(fill = "none") +
  theme_eea +
  theme(axis.text.x = element_text(angle = 0, hjust = 0.5, size = 13, face = "bold"))

save_plot(p_h4, "H4_author_to_study_country_flow", w = 14, h = 11)

# ---------------------------------------------------------------------------
# H5. Study ocean basin — structured geo-tag vs text-mined b_ columns
# ---------------------------------------------------------------------------
cat("\nBuilding H5: study ocean-basin bar (geo vs text-mined)...\n")

clean_basin <- function(x) x |> str_remove("^b_") |> str_replace_all("_", " ") |> str_to_title()

# Structured geo tag (single-label, sparse)
geo_basin <- df |>
  filter(!is.na(geo_study_ocean_basin)) |>
  count(geo_study_ocean_basin, name = "n") |>
  mutate(
    basin = recode(geo_study_ocean_basin, "Arctic" = "Arctic Ocean"),
    pct   = 100 * n / sum(n),
    source = "Geo-tagged (structured, single-label)"
  )
n_h5_geo <- sum(geo_basin$n)

# Text-mined b_ columns (multi-label, full corpus)
b_cols <- names(df)[startsWith(names(df), "b_")]
textmined_basin <- tibble(
  basin = clean_basin(b_cols),
  n     = sapply(b_cols, function(col) sum(df[[col]] == 1, na.rm = TRUE))
) |>
  mutate(pct = 100 * n / sum(n), source = "Text-mined (b_ columns, multi-label)")
n_h5_text_papers <- sum(rowSums(df[b_cols] == 1, na.rm = TRUE) >= 1)

basin_compare <- bind_rows(
  geo_basin |> select(basin, n, pct, source),
  textmined_basin |> select(basin, n, pct, source)
)
basin_order <- basin_compare |> group_by(basin) |> summarise(tot = sum(n), .groups = "drop") |>
  arrange(desc(tot)) |> pull(basin)
basin_compare <- basin_compare |> mutate(basin = factor(basin, levels = basin_order))

p_h5 <- ggplot(basin_compare, aes(x = basin, y = pct, fill = source)) +
  geom_col(position = position_dodge(width = 0.75), width = 0.68) +
  geom_text(aes(label = paste0(round(pct, 1), "%")),
            position = position_dodge(width = 0.75), vjust = -0.4, size = 3) +
  scale_fill_manual(values = c(
    "Geo-tagged (structured, single-label)" = "#4393c3",
    "Text-mined (b_ columns, multi-label)"  = "#d6604d"
  ), name = NULL) +
  scale_y_continuous(expand = expansion(mult = c(0, 0.14))) +
  labs(
    title    = "Study ocean basin: structured geo-tag vs text-mined validation",
    subtitle = str_wrap(paste0(
      "Bars show % share WITHIN each source (not directly comparable in absolute n). Geo-tagged: n = ",
      comma(n_h5_geo), " papers with geo_study_ocean_basin. Text-mined: n = ",
      comma(n_h5_text_papers), " papers with >=1 b_ basin flag (", comma(n_total), " corpus total)."
    ), width = 105),
    x = NULL, y = "% of respective total"
  ) +
  theme_eea +
  theme(axis.text.x = element_text(angle = 20, hjust = 1), legend.position = "bottom")

save_plot(p_h5, "H5_study_basin_geo_vs_textmined", w = 12, h = 7)

cat("\nAll H1-H5 geography visualisations complete. Saved to", fig_dir, "\n")
