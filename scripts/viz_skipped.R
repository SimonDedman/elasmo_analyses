library(tidyverse)
library(sf)
library(rnaturalearth)

base_dir <- "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
fig_dir  <- file.path(base_dir, "outputs/figures")
dir.create(fig_dir, showWarnings = FALSE, recursive = TRUE)

df <- read_csv(file.path(base_dir, "outputs/viz_data.csv"),
               show_col_types = FALSE, guess_max = 5000)
df <- df |> filter(!is.na(year), year >= 1950, year <= 2025)

b_cols <- names(df)[startsWith(names(df), "b_")]
d_cols <- names(df)[startsWith(names(df), "d_")]
d_main <- c("d_biology","d_behaviour","d_trophic","d_genetics",
             "d_movement","d_fisheries","d_conservation","d_data_science")
d_main <- d_main[d_main %in% d_cols]

clean_name <- function(x) {
  x |>
    str_remove("^(eco_|pr_|gear_|imp_|d_|b_|sp_|gear_mit_)") |>
    str_replace_all("_", " ") |>
    str_to_title()
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

# ---------------------------------------------------------------------------
# A4. spatial_parachute_science
# Author country (ISO-2) × study basin dot plot
# ---------------------------------------------------------------------------
cat("Building A4: spatial_parachute_science ...\n")

parachute_df <- df |>
  filter(!is.na(institution_country_first)) |>
  select(institution_country_first, all_of(b_cols))

# Convert basin flags to long format, keep only papers with >=1 basin flagged
parachute_long <- parachute_df |>
  pivot_longer(cols = all_of(b_cols), names_to = "basin", values_to = "flag") |>
  filter(!is.na(flag), flag == 1) |>
  count(institution_country_first, basin, name = "n_papers")

# Keep top 20 author countries by total papers
top_countries <- parachute_long |>
  group_by(institution_country_first) |>
  summarise(total = sum(n_papers), .groups = "drop") |>
  slice_max(total, n = 20) |>
  pull(institution_country_first)

parachute_plot_df <- parachute_long |>
  filter(institution_country_first %in% top_countries) |>
  mutate(
    basin_label   = clean_name(basin),
    country_label = institution_country_first
  )

p_a4 <- ggplot(parachute_plot_df,
               aes(x = basin_label, y = country_label, size = n_papers, colour = n_papers)) +
  geom_point(alpha = 0.8) +
  scale_size_continuous(range = c(2, 16), name = "Papers") +
  scale_colour_viridis_c(option = "plasma", name = "Papers") +
  labs(
    title    = "Where researchers are based vs where they study",
    subtitle = "Author country (ISO-2) vs study basin - top 20 author countries",
    x = "Study basin", y = "First-author country"
  ) +
  theme_eea +
  theme(axis.text.x = element_text(angle = 45, hjust = 1))

save_plot(p_a4, "A4_spatial_parachute_science", w = 14, h = 10)

# ---------------------------------------------------------------------------
# A5. spatial_gender_map — % female first authorship by country
# ---------------------------------------------------------------------------
cat("Building A5: spatial_gender_map ...\n")

gender_country <- df |>
  filter(!is.na(institution_country_first),
         gender_first_author %in% c("male", "female")) |>
  group_by(institution_country_first) |>
  summarise(
    n_total  = n(),
    n_female = sum(gender_first_author == "female"),
    pct_female = n_female / n_total * 100,
    .groups = "drop"
  ) |>
  filter(n_total >= 5)

# World map — ISO-2 join
world <- ne_countries(scale = "medium", returnclass = "sf") |>
  select(iso_a2, name, geometry)

world_gender <- world |>
  left_join(gender_country, by = c("iso_a2" = "institution_country_first"))

p_a5 <- ggplot(world_gender) +
  geom_sf(aes(fill = pct_female), colour = "grey60", linewidth = 0.1) +
  scale_fill_viridis_c(
    option    = "magma",
    name      = "% female\nfirst author",
    na.value  = "grey90",
    limits    = c(0, 100)
  ) +
  coord_sf(crs = "+proj=robin") +
  labs(
    title    = "Female first authorship rate by country",
    subtitle = "Countries with >= 5 papers shown; grey = no data"
  ) +
  theme_minimal(base_size = 12) +
  theme(
    plot.background  = element_rect(fill = "white", colour = NA),
    panel.background = element_rect(fill = "white", colour = NA),
    legend.background = element_rect(fill = "white", colour = NA),
    plot.title    = element_text(face = "bold", size = 14),
    plot.subtitle = element_text(colour = "grey40"),
    axis.text     = element_blank(),
    axis.title    = element_blank(),
    panel.grid    = element_blank()
  )

save_plot(p_a5, "A5_spatial_gender_map", w = 16, h = 9)

# ---------------------------------------------------------------------------
# C5. corr_gender_discipline — % female by discipline
# ---------------------------------------------------------------------------
cat("Building C5: corr_gender_discipline ...\n")

overall_pct_female <- df |>
  filter(gender_first_author %in% c("male", "female")) |>
  summarise(pct = mean(gender_first_author == "female") * 100) |>
  pull(pct)

gender_disc <- map_dfr(d_main, function(col) {
  df |>
    filter(.data[[col]] == 1, gender_first_author %in% c("male", "female")) |>
    summarise(
      discipline  = col,
      n_total     = n(),
      n_female    = sum(gender_first_author == "female"),
      pct_female  = n_female / n_total * 100,
      .groups     = "drop"
    )
}) |>
  filter(n_total >= 10) |>
  mutate(disc_label = clean_name(discipline)) |>
  arrange(pct_female) |>
  mutate(disc_label = fct_inorder(disc_label))

p_c5 <- ggplot(gender_disc, aes(x = pct_female, y = disc_label, size = n_total)) +
  geom_vline(xintercept = overall_pct_female, linetype = "dashed",
             colour = "grey50", linewidth = 0.8) +
  geom_point(colour = "#7B2D8B", alpha = 0.85) +
  annotate("text", x = overall_pct_female + 0.5, y = 0.5,
           label = sprintf("Overall: %.1f%%", overall_pct_female),
           hjust = 0, vjust = 0, colour = "grey40", size = 3.5) +
  scale_size_continuous(range = c(3, 14), name = "Papers") +
  scale_x_continuous(labels = scales::label_percent(scale = 1), limits = c(0, NA)) +
  labs(
    title    = "Female first authorship by discipline",
    subtitle = "Disciplines with >= 10 papers where gender is known",
    x = "% female first author", y = NULL
  ) +
  theme_eea +
  theme(axis.text.x = element_text(angle = 0, hjust = 0.5))

save_plot(p_c5, "C5_corr_gender_discipline", w = 12, h = 7)

# ---------------------------------------------------------------------------
# D3. bars_bycatch_targets — top fisheries where elasmobranchs are bycatch
# ---------------------------------------------------------------------------
cat("Building D3: bars_bycatch_targets ...\n")

bycatch_df <- df |>
  filter(imp_is_bycatch == "True", !is.na(gear_target_species)) |>
  select(gear_target_species)

# gear_target_species may be comma-separated; split and tally
bycatch_species <- bycatch_df |>
  mutate(species_list = str_split(gear_target_species, ",\\s*")) |>
  unnest(species_list) |>
  mutate(species_list = str_trim(species_list)) |>
  filter(species_list != "", !is.na(species_list)) |>
  count(species_list, name = "n_papers", sort = TRUE) |>
  slice_max(n_papers, n = 15, with_ties = FALSE) |>
  mutate(species_label = str_to_title(species_list),
         species_label = fct_reorder(species_label, n_papers))

p_d3 <- ggplot(bycatch_species, aes(x = n_papers, y = species_label)) +
  geom_col(fill = "#C0392B", alpha = 0.85) +
  geom_text(aes(label = n_papers), hjust = -0.2, size = 3.5) +
  scale_x_continuous(expand = expansion(mult = c(0, 0.12))) +
  labs(
    title    = "Top fisheries where elasmobranchs are bycatch",
    subtitle = "Papers classified as bycatch (imp_is_bycatch = True)",
    x = "Number of papers", y = NULL
  ) +
  theme_eea +
  theme(axis.text.x = element_text(angle = 0, hjust = 0.5))

save_plot(p_d3, "D3_bars_bycatch_targets", w = 12, h = 8)

# ---------------------------------------------------------------------------
# D6. bars_gender_summary — gender counts + % female over time
# ---------------------------------------------------------------------------
cat("Building D6: bars_gender_summary ...\n")

# Panel 1: overall gender counts
gender_counts <- df |>
  filter(!is.na(gender_first_author)) |>
  count(gender_first_author) |>
  mutate(
    gender_label = str_to_title(gender_first_author),
    gender_label = factor(gender_label, levels = c("Male", "Female", "Unknown"))
  )

gender_colours <- c("Male" = "#2980B9", "Female" = "#E91E8C", "Unknown" = "grey65")

p_d6_left <- ggplot(gender_counts, aes(x = gender_label, y = n, fill = gender_label)) +
  geom_col(alpha = 0.9, width = 0.6) +
  geom_text(aes(label = scales::comma(n)), vjust = -0.4, size = 3.8) +
  scale_fill_manual(values = gender_colours, guide = "none") +
  scale_y_continuous(labels = scales::comma, expand = expansion(mult = c(0, 0.12))) +
  labs(x = NULL, y = "Number of papers", title = "Gender counts") +
  theme_eea +
  theme(axis.text.x = element_text(angle = 0, hjust = 0.5))

# Panel 2: % female by 5-year bin
gender_time <- df |>
  filter(gender_first_author %in% c("male", "female"), year >= 1975) |>
  mutate(year_bin = floor(year / 5) * 5) |>
  group_by(year_bin) |>
  summarise(
    n_total  = n(),
    n_female = sum(gender_first_author == "female"),
    pct_female = n_female / n_total * 100,
    .groups = "drop"
  ) |>
  filter(n_total >= 10)

p_d6_right <- ggplot(gender_time, aes(x = year_bin, y = pct_female)) +
  geom_line(colour = "#E91E8C", linewidth = 1.1) +
  geom_point(aes(size = n_total), colour = "#E91E8C", alpha = 0.85) +
  geom_hline(yintercept = overall_pct_female, linetype = "dashed",
             colour = "grey50", linewidth = 0.8) +
  scale_size_continuous(range = c(2, 8), name = "Papers") +
  scale_y_continuous(labels = scales::label_percent(scale = 1), limits = c(0, NA)) +
  scale_x_continuous(breaks = seq(1975, 2025, 10)) +
  labs(
    x = "Year (5-year bins)", y = "% female first author",
    title = "Trend over time"
  ) +
  theme_eea +
  theme(axis.text.x = element_text(angle = 45, hjust = 1))

# Combine with patchwork if available, else cowplot, else save separately
combined_ok <- FALSE
if (requireNamespace("patchwork", quietly = TRUE)) {
  library(patchwork)
  p_d6_combined <- (p_d6_left | p_d6_right) +
    plot_annotation(
      title    = "First author gender in elasmobranch research",
      subtitle = "Left: total counts  |  Right: % female by 5-year period",
      theme = theme(
        plot.background = element_rect(fill = "white", colour = NA),
        plot.title      = element_text(face = "bold", size = 14)
      )
    )
  save_plot(p_d6_combined, "D6_bars_gender_summary", w = 16, h = 8)
  combined_ok <- TRUE
} else if (requireNamespace("cowplot", quietly = TRUE)) {
  library(cowplot)
  p_d6_combined <- plot_grid(p_d6_left, p_d6_right, ncol = 2,
                              labels = c("A", "B"), label_size = 12)
  # Add title via cowplot
  title_grob <- cowplot::ggdraw() +
    cowplot::draw_label("First author gender in elasmobranch research",
                        fontface = "bold", size = 14)
  p_d6_final <- plot_grid(title_grob, p_d6_combined, ncol = 1,
                           rel_heights = c(0.08, 1))
  save_plot(p_d6_final, "D6_bars_gender_summary", w = 16, h = 8)
  combined_ok <- TRUE
}

if (!combined_ok) {
  save_plot(p_d6_left,  "D6a_bars_gender_counts",  w = 8, h = 7)
  save_plot(p_d6_right, "D6b_bars_gender_trend",   w = 10, h = 7)
  cat("Note: patchwork/cowplot not available — saved as two separate files\n")
}

cat("\nAll skipped visualizations complete.\n")
