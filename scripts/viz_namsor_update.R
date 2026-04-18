# viz_namsor_update.R
# 1. Replot D6 (gender summary), A5 (gender map), C5 (gender × discipline)
#    with improved NamSor-enriched gender data
# 2. New plots: origin country, origin region, ethnicity trends over time

suppressPackageStartupMessages({
  library(tidyverse)
  library(patchwork)
  library(sf)
  library(rnaturalearth)
})

base_dir <- "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
fig_dir  <- file.path(base_dir, "outputs/figures")
dir.create(fig_dir, showWarnings = FALSE, recursive = TRUE)

df <- read_csv(file.path(base_dir, "outputs/viz_data.csv"),
               show_col_types = FALSE, guess_max = 5000)
df <- df |> filter(!is.na(year), year >= 1950, year <= 2025)
n_papers <- nrow(df)

# NamSor columns already merged into viz_data.csv by Python:
#   origin_country_first, origin_region_first, origin_subregion_first,
#   ethnicity_first, ethnicity_alt_first, gender_probability_first

d_cols <- names(df)[startsWith(names(df), "d_")]

clean_name <- function(x) {
  x |> str_remove("^(eco_|pr_|gear_|imp_|d_|b_|sp_|gear_mit_)") |>
    str_replace_all("_", " ") |> str_to_title()
}

theme_eea <- theme_minimal(base_size = 12) +
  theme(
    plot.background  = element_rect(fill = "white", colour = NA),
    panel.background = element_rect(fill = "white", colour = NA),
    legend.background = element_rect(fill = "white", colour = NA),
    plot.title    = element_text(face = "bold", size = 14),
    plot.subtitle = element_text(colour = "grey40"),
    axis.text.x   = element_text(angle = 45, hjust = 1)
  )

save_plot <- function(p, name, w = 14, h = 9) {
  ggsave(file.path(fig_dir, paste0(name, ".png")), p,
         width = w, height = h, dpi = 300, bg = "white")
  ggsave(file.path(fig_dir, paste0(name, ".pdf")), p,
         width = w, height = h, bg = "white")
  cat("Saved:", name, "\n")
}

# ==========================================================================
# REPLOT 1: D6 — Gender summary (bar + trend)
# ==========================================================================
cat("\n--- D6: Gender summary (updated) ---\n")

gender_df <- df |>
  filter(!is.na(gender_first_author),
         gender_first_author %in% c("Male", "Female", "Unknown", "male", "female", "unknown")) |>
  mutate(
    gender = case_when(
      tolower(gender_first_author) == "male"   ~ "Male",
      tolower(gender_first_author) == "female" ~ "Female",
      TRUE ~ "Unknown"
    ),
    year_bin = floor(year / 5) * 5
  )

cat("Gender papers:", nrow(gender_df), "\n")
cat("  Male:", sum(gender_df$gender == "Male"), "\n")
cat("  Female:", sum(gender_df$gender == "Female"), "\n")
cat("  Unknown:", sum(gender_df$gender == "Unknown"), "\n")

overall <- gender_df |> count(gender) |> mutate(gender = fct_reorder(gender, -n))
gender_cols <- c(Male = "#4393c3", Female = "#e91e8d", Unknown = "#aaaaaa")

trend <- gender_df |>
  count(year_bin, gender) |>
  group_by(year_bin) |>
  mutate(total = sum(n), pct = 100 * n / total) |>
  ungroup()

avg <- gender_df |>
  count(gender) |>
  mutate(pct = 100 * n / sum(n))

p_d6a <- ggplot(overall, aes(x = gender, y = n, fill = gender)) +
  geom_col(show.legend = FALSE) +
  geom_text(aes(label = scales::comma(n)), vjust = -0.5, size = 3.5) +
  scale_fill_manual(values = gender_cols) +
  scale_y_continuous(expand = expansion(mult = c(0, 0.1))) +
  labs(title = "Gender counts", x = NULL, y = "Number of papers") +
  theme_eea +
  theme(axis.text.x = element_text(angle = 0, hjust = 0.5))

# Latest year bin label data (Male and Female only)
latest_bin <- max(trend$year_bin)
latest_labels <- trend |>
  filter(year_bin == latest_bin, gender %in% c("Male", "Female"))

p_d6b <- ggplot(trend, aes(x = year_bin, y = pct, colour = gender, group = gender)) +
  geom_hline(data = avg, aes(yintercept = pct, colour = gender),
             linetype = "dashed", linewidth = 0.7, show.legend = FALSE) +
  geom_line(linewidth = 1.2) +
  geom_point(aes(size = n)) +
  geom_text(data = latest_labels,
            aes(label = sprintf("%.1f%%", pct)),
            hjust = -0.2, vjust = 0.5, size = 3.5, fontface = "bold",
            show.legend = FALSE) +
  scale_colour_manual(values = gender_cols) +
  scale_size_continuous(range = c(1.5, 5), name = "Papers") +
  scale_x_continuous(breaks = seq(1950, 2030, 10), limits = c(NA, 2030)) +
  scale_y_continuous(labels = scales::percent_format(scale = 1)) +
  labs(title = "Trend over time", x = "Year (5-year bins)",
       y = "% first author") +
  theme_eea +
  guides(colour = guide_legend(title = "Gender"))

p_d6 <- (p_d6a | p_d6b) +
  plot_annotation(
    title    = "First author gender in elasmobranch research",
    subtitle = "Left: total counts | Right: % by 5-year period (NamSor-enriched)"
  ) +
  plot_layout(widths = c(1, 2))
save_plot(p_d6, "D6_bars_gender_summary", w = 14, h = 6)


# ==========================================================================
# REPLOT 2: A5 — Gender map
# ==========================================================================
cat("\n--- A5: Gender map (updated) ---\n")

country_col <- intersect(c("institution_country_first", "institution_country"), names(df))
if (length(country_col) > 0) {
  country_col <- country_col[1]

  gender_summary <- df |>
    select(country = all_of(country_col),
           gender = gender_first_author) |>
    filter(!is.na(country), country != "",
           tolower(gender) %in% c("female", "male")) |>
    mutate(gender = tolower(gender)) |>
    count(country, gender) |>
    pivot_wider(names_from = gender, values_from = n, values_fill = 0) |>
    mutate(total      = female + male,
           pct_female = female / total * 100) |>
    filter(total >= 5)

  world <- ne_countries(scale = "medium", returnclass = "sf")
  robinson <- "+proj=robin +lon_0=0 +x_0=0 +y_0=0 +datum=WGS84"

  # Join on ISO2 code (institution_country_first is ISO2)
  world_gender <- world |>
    left_join(gender_summary, by = c("iso_a2" = "country"))

  # Compute centroids for label placement
  world_label <- world_gender |>
    filter(!is.na(pct_female)) |>
    st_transform(robinson)
  centroids_label <- st_centroid(world_label, of_largest_polygon = TRUE)

  p_a5 <- ggplot() +
    geom_sf(data = world_gender, aes(fill = pct_female),
            colour = "grey60", linewidth = 0.15) +
    geom_sf_text(data = centroids_label,
                 aes(label = sprintf("%.0f", pct_female)),
                 size = 1.8, colour = "black", fontface = "plain") +
    scale_fill_gradient2(low = "#d73027", mid = "#ffffbf", high = "#4575b4",
                         midpoint = 50, name = "% Female\nFirst Author",
                         na.value = "grey85") +
    coord_sf(crs = robinson) +
    labs(title = "Female first authorship rate by country",
         subtitle = "Countries with >= 5 papers shown; grey = no data (NamSor-enriched). Numbers = % female.") +
    theme_eea +
    theme(axis.text  = element_blank(),
          axis.ticks = element_blank(),
          panel.background = element_rect(fill = "#E8F4FD", colour = NA),
          panel.grid = element_line(colour = "grey90", linewidth = 0.2))

  save_plot(p_a5, "A5_spatial_gender_map", w = 14, h = 8)

  # A5b: Recent years only (last 6 years, 2020-2025)
  cat("  A5b: Gender map (2020-2025 only)...\n")

  gender_summary_recent <- df |>
    filter(year >= 2020) |>
    select(country = all_of(country_col),
           gender = gender_first_author) |>
    filter(!is.na(country), country != "",
           tolower(gender) %in% c("female", "male")) |>
    mutate(gender = tolower(gender)) |>
    count(country, gender) |>
    pivot_wider(names_from = gender, values_from = n, values_fill = 0) |>
    mutate(total      = female + male,
           pct_female = female / total * 100) |>
    filter(total >= 5)

  world_gender_recent <- world |>
    left_join(gender_summary_recent, by = c("iso_a2" = "country"))

  centroids_recent <- world_gender_recent |>
    filter(!is.na(pct_female)) |>
    st_transform(robinson)
  centroids_recent <- st_centroid(centroids_recent, of_largest_polygon = TRUE)

  p_a5b <- ggplot() +
    geom_sf(data = world_gender_recent, aes(fill = pct_female),
            colour = "grey60", linewidth = 0.15) +
    geom_sf_text(data = centroids_recent,
                 aes(label = sprintf("%.0f", pct_female)),
                 size = 1.8, colour = "black", fontface = "plain") +
    scale_fill_gradient2(low = "#d73027", mid = "#ffffbf", high = "#4575b4",
                         midpoint = 50, name = "% Female\nFirst Author",
                         na.value = "grey85") +
    coord_sf(crs = robinson) +
    labs(title = "Female first authorship rate by country (2020-2025)",
         subtitle = "Countries with >= 5 papers shown; grey = no data. Numbers = % female.") +
    theme_eea +
    theme(axis.text  = element_blank(),
          axis.ticks = element_blank(),
          panel.background = element_rect(fill = "#E8F4FD", colour = NA),
          panel.grid = element_line(colour = "grey90", linewidth = 0.2))

  save_plot(p_a5b, "A5b_spatial_gender_map_recent", w = 14, h = 8)

} else {
  cat("  Skipped: no country column found\n")
}


# ==========================================================================
# REPLOT 3: C5 — Gender × discipline
# ==========================================================================
cat("\n--- C5: Gender × discipline (updated) ---\n")

disc_all <- d_cols

gender_disc <- map_dfr(disc_all, function(col) {
  sub_df <- df |>
    filter(.data[[col]] == 1, !is.na(gender_first_author),
           tolower(gender_first_author) %in% c("male", "female"))
  if (nrow(sub_df) < 10) return(NULL)
  tibble(
    discipline  = col,
    n_total     = nrow(sub_df),
    n_female    = sum(tolower(sub_df$gender_first_author) == "female", na.rm = TRUE),
    pct_female  = 100 * n_female / n_total
  )
}) |>
  arrange(pct_female) |>
  mutate(disc_label = factor(clean_name(discipline), levels = clean_name(discipline)))

overall_pct <- df |>
  filter(!is.na(gender_first_author),
         tolower(gender_first_author) %in% c("male", "female")) |>
  summarise(pct = 100 * mean(tolower(gender_first_author) == "female")) |>
  pull(pct)

p_c5 <- ggplot(gender_disc, aes(x = pct_female, y = disc_label, size = n_total)) +
  geom_vline(xintercept = overall_pct, linetype = "dashed", colour = "grey50") +
  geom_point(colour = "#d6604d", alpha = 0.85) +
  scale_size_continuous(name = "Papers", range = c(3, 12)) +
  annotate("text", x = overall_pct + 0.5, y = 1.3,
           label = sprintf("Overall: %.1f%%", overall_pct),
           hjust = 0, colour = "grey40", size = 3.5) +
  scale_x_continuous(limits = c(0, NA), labels = function(x) paste0(x, "%")) +
  labs(
    title    = "Female first authorship by discipline",
    subtitle = paste0("Disciplines with >= 10 papers where gender is known (NamSor-enriched). ",
                      "Dashed line = overall average."),
    x = "% female first author", y = NULL
  ) +
  theme_eea +
  theme(axis.text.x = element_text(angle = 0, hjust = 0.5),
        axis.text.y = element_text(angle = 0, hjust = 1))

save_plot(p_c5, "C5_corr_gender_discipline", w = 12, h = 8)


# ==========================================================================
# NEW PLOTS: Origin, region, ethnicity trends over time
# ==========================================================================
cat("\n--- New: NamSor origin/ethnicity trends ---\n")

# Work with papers that have NamSor enrichment
df_enriched <- df |>
  filter(!is.na(origin_country_first) | !is.na(ethnicity_first))

cat("Papers with NamSor first-author enrichment:", nrow(df_enriched), "\n")

# --------------------------------------------------------------------------
# N1. Top origin countries over time (annual, stacked area)
# --------------------------------------------------------------------------
cat("  N1: Origin country trends...\n")

# Find top 10 origin countries
top_origins <- df_enriched |>
  filter(!is.na(origin_country_first), origin_country_first != "") |>
  count(origin_country_first, sort = TRUE) |>
  head(10) |>
  pull(origin_country_first)

origin_annual <- df_enriched |>
  filter(!is.na(origin_country_first), origin_country_first != "") |>
  mutate(origin_group = if_else(origin_country_first %in% top_origins,
                                origin_country_first, "Other")) |>
  count(year, origin_group) |>
  # Ensure "Other" is last in legend
  mutate(origin_group = factor(origin_group,
                               levels = c(top_origins, "Other")))

# Colours: use a qualitative palette + grey for Other
origin_pal <- c(setNames(scales::hue_pal()(10), top_origins), Other = "grey70")

p_n1 <- ggplot(origin_annual, aes(x = year, y = n, fill = origin_group)) +
  geom_area(alpha = 0.85, colour = "white", linewidth = 0.2) +
  scale_fill_manual(values = origin_pal, name = "Name origin\ncountry") +
  scale_x_continuous(breaks = seq(1950, 2025, 10)) +
  labs(
    title    = "First author name-origin country over time",
    subtitle = "Top 10 countries by NamSor name-origin inference (all others grouped)",
    x = "Year", y = "Papers per year"
  ) +
  theme_eea +
  theme(axis.text.x = element_text(angle = 0, hjust = 0.5))

save_plot(p_n1, "N1_origin_country_trends", w = 16, h = 9)


# --------------------------------------------------------------------------
# N2. Origin subregion over time (annual proportional area)
# --------------------------------------------------------------------------
cat("  N2: Origin subregion trends...\n")

# Top 8 subregions + Other
top_subregions <- df_enriched |>
  filter(!is.na(origin_subregion_first), origin_subregion_first != "") |>
  count(origin_subregion_first, sort = TRUE) |>
  head(8) |>
  pull(origin_subregion_first)

region_annual <- df_enriched |>
  filter(!is.na(origin_subregion_first), origin_subregion_first != "") |>
  mutate(subregion = if_else(origin_subregion_first %in% top_subregions,
                             origin_subregion_first, "Other")) |>
  count(year, subregion) |>
  mutate(subregion = factor(subregion, levels = c(top_subregions, "Other")))

subregion_pal <- c(setNames(
  c("#1b9e77", "#d95f02", "#7570b3", "#e7298a",
    "#66a61e", "#e6ab02", "#a6761d", "#666666"),
  top_subregions
), Other = "grey75")

p_n2 <- ggplot(region_annual, aes(x = year, y = n, fill = subregion)) +
  geom_area(position = "fill", alpha = 0.85, colour = "white", linewidth = 0.2) +
  scale_fill_manual(values = subregion_pal, name = "Name-origin\nsubregion") +
  scale_x_continuous(breaks = seq(1950, 2025, 10)) +
  scale_y_continuous(labels = scales::percent_format(), expand = c(0, 0)) +
  labs(
    title    = "First author name-origin subregion over time",
    subtitle = "Proportion by subregion (NamSor inference -- reflects name etymology, not nationality)",
    x = "Year", y = "% of papers"
  ) +
  theme_eea +
  theme(axis.text.x = element_text(angle = 0, hjust = 0.5))

save_plot(p_n2, "N2_origin_subregion_trends", w = 16, h = 9)


# --------------------------------------------------------------------------
# N3. Top ethnicities over time (annual lines)
# --------------------------------------------------------------------------
cat("  N3: Ethnicity trends...\n")

top_ethnicities <- df_enriched |>
  filter(!is.na(ethnicity_first), ethnicity_first != "") |>
  count(ethnicity_first, sort = TRUE) |>
  head(12) |>
  pull(ethnicity_first)

ethnicity_annual <- df_enriched |>
  filter(ethnicity_first %in% top_ethnicities) |>
  count(year, ethnicity_first) |>
  mutate(ethnicity_first = factor(ethnicity_first, levels = top_ethnicities))

p_n3 <- ggplot(ethnicity_annual, aes(x = year, y = n,
                                      colour = ethnicity_first,
                                      group = ethnicity_first)) +
  geom_line(linewidth = 0.9, alpha = 0.85) +
  scale_colour_manual(values = setNames(
    c(scales::hue_pal()(12)),
    top_ethnicities
  ), name = "Ethnicity") +
  scale_x_continuous(breaks = seq(1950, 2025, 10)) +
  labs(
    title    = "First author ethnicity over time",
    subtitle = "Top 12 ethnicities by NamSor diaspora inference (annual counts)",
    x = "Year", y = "Papers per year"
  ) +
  theme_eea +
  theme(axis.text.x = element_text(angle = 0, hjust = 0.5))

save_plot(p_n3, "N3_ethnicity_trends", w = 16, h = 9)


# --------------------------------------------------------------------------
# N4. Ethnicity diversity index over time
# --------------------------------------------------------------------------
cat("  N4: Ethnicity diversity over time...\n")

# Shannon diversity index per year
diversity_annual <- df_enriched |>
  filter(!is.na(ethnicity_first), ethnicity_first != "") |>
  count(year, ethnicity_first) |>
  group_by(year) |>
  mutate(p = n / sum(n)) |>
  summarise(
    shannon = -sum(p * log(p)),
    n_ethnicities = n_distinct(ethnicity_first),
    total_papers = sum(n),
    .groups = "drop"
  ) |>
  filter(total_papers >= 10)  # minimum papers per year

p_n4 <- ggplot(diversity_annual, aes(x = year, y = shannon)) +
  geom_point(aes(size = total_papers), colour = "#4393c3", alpha = 0.6) +
  geom_smooth(method = "loess", span = 0.3, colour = "#d73027",
              linewidth = 1.2, se = TRUE, fill = "#d73027", alpha = 0.15) +
  scale_size_continuous(range = c(1, 6), name = "Papers") +
  scale_x_continuous(breaks = seq(1950, 2025, 10)) +
  labs(
    title    = "Ethnic diversity of first authors over time",
    subtitle = "Shannon diversity index of NamSor ethnicity classifications (LOESS trend)",
    x = "Year", y = "Shannon diversity index"
  ) +
  theme_eea +
  theme(axis.text.x = element_text(angle = 0, hjust = 0.5))

save_plot(p_n4, "N4_ethnicity_diversity", w = 14, h = 8)


# --------------------------------------------------------------------------
# N5. Origin country vs institution country (mismatch / mobility)
# --------------------------------------------------------------------------
cat("  N5: Name-origin vs institution country...\n")

if ("institution_country_first" %in% names(df)) {
  mobility <- df_enriched |>
    filter(!is.na(origin_country_first), origin_country_first != "",
           !is.na(institution_country_first), institution_country_first != "") |>
    mutate(
      # Use ISO2 codes from institution_country_first
      match = origin_country_first == institution_country_first,
      year_bin = floor(year / 5) * 5
    )

  mobility_trend <- mobility |>
    count(year_bin, match) |>
    group_by(year_bin) |>
    mutate(pct = 100 * n / sum(n)) |>
    ungroup() |>
    filter(!match)  # keep only mismatch %

  p_n5 <- ggplot(mobility_trend, aes(x = year_bin, y = pct)) +
    geom_col(fill = "#d6604d", alpha = 0.85, width = 4) +
    geom_smooth(method = "loess", span = 0.5, colour = "#4393c3",
                linewidth = 1.2, se = FALSE) +
    scale_x_continuous(breaks = seq(1950, 2025, 10)) +
    scale_y_continuous(labels = function(x) paste0(x, "%")) +
    labs(
      title    = "Researcher mobility: name-origin vs institution country",
      subtitle = "% of first authors whose NamSor name-origin differs from their institution country (5-year bins)",
      x = "Year (5-year bins)", y = "% mismatch"
    ) +
    theme_eea +
    theme(axis.text.x = element_text(angle = 0, hjust = 0.5))

  save_plot(p_n5, "N5_origin_institution_mismatch", w = 14, h = 8)
} else {
  cat("  Skipped N5: institution_country_first not found\n")
}

cat("\nAll NamSor visualisations complete.\n")
