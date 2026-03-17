## viz_A_spatial.R
## Spatial map visualisations for EEA 2025 Data Panel
## A1: basin choropleth (centroid points + ggrepel labels)
## A2: basin × discipline faceted (centroid points)
## A3: pressure hotspot (dominant pressure per basin)
## A4: parachute science (skips if col absent)
## A5: gender map (skips if col absent)

library(tidyverse)
library(sf)
library(rnaturalearth)
library(ggrepel)

base_dir <- "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
fig_dir  <- file.path(base_dir, "outputs/figures")
dir.create(fig_dir, showWarnings = FALSE, recursive = TRUE)

df <- read_csv(file.path(base_dir, "outputs/viz_data.csv"),
               show_col_types = FALSE, guess_max = 5000)
df <- df |> filter(!is.na(year), year >= 1950, year <= 2025)

# Column groups
b_cols  <- names(df)[startsWith(names(df), "b_")]
d_cols  <- names(df)[startsWith(names(df), "d_")]
pr_cols <- names(df)[startsWith(names(df), "pr_")]

clean_name <- function(x) {
  x |> str_remove("^(eco_|pr_|gear_|imp_|d_|b_|sp_|gear_mit_)") |>
    str_replace_all("_", " ") |> str_to_title()
}

theme_eea <- theme_minimal(base_size = 12) +
  theme(
    plot.background  = element_rect(fill = "white", colour = NA),
    panel.background = element_rect(fill = "#E8F4FD", colour = NA),
    legend.background = element_rect(fill = "white", colour = NA),
    plot.title    = element_text(face = "bold", size = 14),
    plot.subtitle = element_text(colour = "grey40")
  )

save_plot <- function(p, name, w = 14, h = 9) {
  ggsave(file.path(fig_dir, paste0(name, ".png")), p,
         width = w, height = h, dpi = 300, bg = "white")
  ggsave(file.path(fig_dir, paste0(name, ".pdf")), p,
         width = w, height = h, bg = "white")
  cat("Saved:", name, "\n")
}

# ---------------------------------------------------------------------------
# Basin centroids (ocean midpoints, manually curated)
# ---------------------------------------------------------------------------
basin_centroids <- tribble(
  ~basin,              ~lon,  ~lat,
  "b_north_atlantic",   -40,   35,
  "b_south_atlantic",   -15,  -25,
  "b_north_pacific",   -170,   30,
  "b_south_pacific",   -150,  -25,
  "b_indian_ocean",      75,  -15,
  "b_southern_ocean",     0,  -70,
  "b_arctic_ocean",       0,   80,
  "b_mediterranean",     18,   38,
  "b_caribbean",        -75,   18
)

# World map (land = light grey)
world <- ne_countries(scale = "medium", returnclass = "sf")
robinson <- "+proj=robin +lon_0=0 +x_0=0 +y_0=0 +datum=WGS84"

# Reproject centroids to Robinson for geom_sf overlay
centroids_sf <- basin_centroids |>
  st_as_sf(coords = c("lon", "lat"), crs = 4326) |>
  st_transform(robinson)

# ---------------------------------------------------------------------------
# A1. spatial_basin_choropleth
# ---------------------------------------------------------------------------
cat("Building A1: basin choropleth...\n")

basin_counts <- tibble(basin = b_cols,
                       n = sapply(b_cols, function(col) sum(df[[col]], na.rm = TRUE))) |>
  mutate(label = paste0(clean_name(basin), "\n(", scales::comma(n), ")"))

# Join counts to projected centroids
pts_a1 <- centroids_sf |>
  left_join(basin_counts, by = "basin")

p_a1 <- ggplot() +
  geom_sf(data = world, fill = "grey80", colour = "grey60", linewidth = 0.25) +
  geom_sf(data = pts_a1, aes(size = n, colour = n), alpha = 0.85) +
  geom_label_repel(
    data = pts_a1,
    aes(label = label, geometry = geometry),
    stat = "sf_coordinates",
    size = 3,
    box.padding = 0.4,
    point.padding = 0.3,
    min.segment.length = 0.2,
    fill = "white",
    colour = "grey20",
    label.size = 0.2,
    max.overlaps = 20
  ) +
  scale_size_continuous(range = c(4, 18), name = "Papers", labels = scales::comma) +
  scale_colour_viridis_c(option = "plasma", name = "Papers", labels = scales::comma) +
  coord_sf(crs = robinson) +
  guides(size = guide_legend(override.aes = list(alpha = 0.85))) +
  labs(title = "Elasmobranch Research by Ocean Basin",
       subtitle = "Circle size and colour show total papers per basin (1950-2025)") +
  theme_eea +
  theme(axis.text  = element_blank(),
        axis.ticks = element_blank(),
        panel.grid = element_line(colour = "grey90", linewidth = 0.2))

save_plot(p_a1, "spatial_basin_choropleth", w = 14, h = 8)

# ---------------------------------------------------------------------------
# A2. spatial_basin_discipline_faceted
# ---------------------------------------------------------------------------
cat("Building A2: basin x discipline faceted maps...\n")

main_d_cols <- c("d_biology", "d_behaviour", "d_trophic", "d_genetics",
                 "d_movement", "d_fisheries", "d_conservation", "d_data_science")

disc_basin_counts <- expand.grid(discipline = main_d_cols,
                                 basin = b_cols,
                                 stringsAsFactors = FALSE) |>
  as_tibble() |>
  rowwise() |>
  mutate(n = sum(df[[discipline]] == 1 & df[[basin]] == 1, na.rm = TRUE)) |>
  ungroup() |>
  mutate(disc_label = clean_name(discipline))

# Join to projected centroids
pts_a2 <- centroids_sf |>
  right_join(disc_basin_counts, by = "basin") |>
  st_as_sf()

p_a2 <- ggplot() +
  geom_sf(data = world, fill = "grey80", colour = "grey60", linewidth = 0.15) +
  geom_sf(data = pts_a2, aes(size = n, colour = n), alpha = 0.8) +
  scale_size_continuous(range = c(1, 10), name = "Papers", labels = scales::comma) +
  scale_colour_viridis_c(option = "viridis", name = "Papers", labels = scales::comma) +
  facet_wrap(~ disc_label, nrow = 2) +
  coord_sf(crs = robinson) +
  labs(title = "Elasmobranch Research by Discipline and Ocean Basin",
       subtitle = "Papers per basin for each major discipline (1950-2025)") +
  theme_eea +
  theme(axis.text  = element_blank(),
        axis.ticks = element_blank(),
        panel.grid = element_line(colour = "grey92", linewidth = 0.15),
        strip.text = element_text(face = "bold", size = 10))

save_plot(p_a2, "spatial_basin_discipline_faceted", w = 20, h = 10)

# ---------------------------------------------------------------------------
# A3. spatial_pressure_hotspot
# ---------------------------------------------------------------------------
cat("Building A3: pressure hotspot map...\n")

# For each basin, find dominant pressure (pr_ column with highest count)
pressure_by_basin <- lapply(b_cols, function(bcol) {
  sub <- df |> filter(.data[[bcol]] == 1)
  if (nrow(sub) == 0) {
    return(tibble(basin = bcol, dominant_pressure = NA_character_,
                  pressure_label = NA_character_, n_total = 0L))
  }
  pr_sums <- sapply(pr_cols, function(p) sum(sub[[p]], na.rm = TRUE))
  dom <- names(which.max(pr_sums))
  tibble(
    basin = bcol,
    dominant_pressure = dom,
    pressure_label = clean_name(dom),
    n_total = as.integer(sum(sub[[bcol]], na.rm = TRUE))
  )
}) |> bind_rows()

# Join to projected centroids
pts_a3 <- centroids_sf |>
  left_join(pressure_by_basin, by = "basin") |>
  mutate(basin_label = clean_name(basin))

# Point label: basin name + dominant pressure
pts_a3 <- pts_a3 |>
  mutate(pt_label = ifelse(!is.na(pressure_label),
                           paste0(basin_label, "\n", pressure_label),
                           basin_label))

n_pressures <- length(unique(na.omit(pts_a3$pressure_label)))
pressure_palette <- setNames(
  scales::hue_pal()(n_pressures),
  sort(unique(na.omit(pts_a3$pressure_label)))
)

p_a3 <- ggplot() +
  geom_sf(data = world, fill = "grey80", colour = "grey60", linewidth = 0.25) +
  geom_sf(data = pts_a3, aes(size = n_total, colour = pressure_label), alpha = 0.85) +
  geom_label_repel(
    data = pts_a3,
    aes(label = pt_label, geometry = geometry, colour = pressure_label),
    stat = "sf_coordinates",
    size = 2.8,
    box.padding = 0.4,
    point.padding = 0.3,
    min.segment.length = 0.2,
    fill = "white",
    label.size = 0.2,
    max.overlaps = 20,
    show.legend = FALSE
  ) +
  scale_size_continuous(range = c(5, 18), name = "Total Papers", labels = scales::comma) +
  scale_colour_manual(values = pressure_palette, name = "Dominant Pressure",
                      na.value = "grey70") +
  coord_sf(crs = robinson) +
  labs(title = "Dominant Pressure Type by Ocean Basin",
       subtitle = "Pressure category with the highest paper count per basin (1950-2025)") +
  theme_eea +
  theme(axis.text  = element_blank(),
        axis.ticks = element_blank(),
        panel.grid = element_line(colour = "grey90", linewidth = 0.2))

save_plot(p_a3, "spatial_pressure_hotspot", w = 14, h = 8)

# ---------------------------------------------------------------------------
# A4. spatial_parachute_science
# ---------------------------------------------------------------------------
cat("Building A4: parachute science...\n")

if (!("institution_country" %in% names(df))) {
  message("A4 skipped: 'institution_country' column not found in viz_data.csv")
} else {
  parachute <- df |>
    select(all_of(c(b_cols, "institution_country"))) |>
    pivot_longer(all_of(b_cols), names_to = "basin", values_to = "flag") |>
    filter(flag == 1, !is.na(institution_country)) |>
    mutate(basin_label = clean_name(basin)) |>
    count(basin_label, institution_country, name = "n") |>
    slice_max(n, n = 20)

  p_a4 <- ggplot(parachute, aes(x = reorder(institution_country, n),
                                 y = n, fill = basin_label)) +
    geom_col() +
    coord_flip() +
    scale_fill_brewer(palette = "Set2", name = "Basin") +
    labs(title = "Top Study Basin x Author Country Combinations",
         subtitle = "Parachute science: author country vs study basin (top 20)",
         x = NULL, y = "Papers") +
    theme_eea

  save_plot(p_a4, "A4_spatial_parachute_science", w = 12, h = 8)
}

# ---------------------------------------------------------------------------
# A5. spatial_gender_map
# ---------------------------------------------------------------------------
cat("Building A5: gender map...\n")

gender_col  <- intersect(c("gender_first_author", "gender"), names(df))
country_col <- intersect(c("institution_country", "author_country"), names(df))

if (length(gender_col) == 0 || length(country_col) == 0) {
  message("A5 skipped: 'gender_first_author' and/or country column not found in viz_data.csv")
} else {
  gender_col  <- gender_col[1]
  country_col <- country_col[1]

  gender_summary <- df |>
    select(country = all_of(country_col), gender = all_of(gender_col)) |>
    filter(!is.na(country), gender %in% c("female", "male")) |>
    count(country, gender) |>
    pivot_wider(names_from = gender, values_from = n, values_fill = 0) |>
    mutate(total      = female + male,
           pct_female = female / total * 100) |>
    filter(total >= 5)

  world_gender <- world |>
    left_join(gender_summary, by = c("name_long" = "country"))

  p_a5 <- ggplot(world_gender) +
    geom_sf(aes(fill = pct_female), colour = "grey60", linewidth = 0.15) +
    scale_fill_gradient2(low = "#d73027", mid = "#ffffbf", high = "#4575b4",
                         midpoint = 50, name = "% Female\nFirst Author",
                         na.value = "grey85") +
    coord_sf(crs = robinson) +
    labs(title = "Female First Authorship by Country",
         subtitle = "Percentage of papers with female first author (min 5 papers per country)") +
    theme_eea +
    theme(axis.text  = element_blank(),
          axis.ticks = element_blank(),
          panel.grid = element_line(colour = "grey90", linewidth = 0.2))

  save_plot(p_a5, "A5_spatial_gender_map", w = 14, h = 8)
}

cat("Done. All spatial plots saved to", fig_dir, "\n")
