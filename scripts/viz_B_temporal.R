library(tidyverse)
library(ggrepel)

base_dir <- "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
fig_dir <- file.path(base_dir, "outputs/figures")
df <- read_csv(file.path(base_dir, "outputs/viz_data.csv"), show_col_types = FALSE, guess_max = 5000)
df <- df |> filter(!is.na(year), year >= 1950, year <= 2025)

d_cols  <- names(df)[startsWith(names(df), "d_")]
pr_cols <- names(df)[startsWith(names(df), "pr_")]
imp_cols <- names(df)[startsWith(names(df), "imp_") & !names(df) %in% c("imp_direction","imp_quantified","imp_is_bycatch","imp_confidence")]
mit_cols <- names(df)[startsWith(names(df), "gear_mit_")]

# Main 8 disciplines only
d_main <- c("d_biology","d_behaviour","d_trophic","d_genetics","d_movement","d_fisheries","d_conservation","d_data_science")
d_main <- d_main[d_main %in% d_cols]

clean_name <- function(x) {
  x |> str_remove("^(eco_|pr_|gear_|imp_|d_|b_|sp_|gear_mit_)") |>
    str_replace_all("_", " ") |> str_to_title()
}

theme_eea <- theme_minimal(base_size = 12) +
  theme(plot.background = element_rect(fill = "white", colour = NA),
        panel.background = element_rect(fill = "white", colour = NA),
        legend.background = element_rect(fill = "white", colour = NA),
        plot.title = element_text(face = "bold", size = 14),
        plot.subtitle = element_text(colour = "grey40"),
        axis.text.x = element_text(angle = 45, hjust = 1))

save_plot <- function(p, name, w = 14, h = 9) {
  ggsave(file.path(fig_dir, paste0(name, ".png")), p, width = w, height = h, dpi = 300, bg = "white")
  ggsave(file.path(fig_dir, paste0(name, ".pdf")), p, width = w, height = h, bg = "white")
  cat("Saved:", name, "\n")
}

# ── Palette ────────────────────────────────────────────────────────────────────
palette_8 <- c(
  "#2166AC", "#4DAF4A", "#FF7F00", "#984EA3",
  "#E41A1C", "#A65628", "#F781BF", "#999999"
)

# ── B1. Column chart: papers per year stacked by 8 main disciplines ────────────
cat("Building B1...\n")

b1_long <- df |>
  select(year, all_of(d_main)) |>
  pivot_longer(cols = all_of(d_main), names_to = "discipline", values_to = "flag") |>
  filter(flag == 1) |>
  count(year, discipline)

disc_labels <- setNames(clean_name(d_main), d_main)

p_b1 <- b1_long |>
  mutate(discipline = factor(discipline, levels = d_main)) |>
  ggplot(aes(x = year, y = n, fill = discipline)) +
  geom_col(width = 0.8, position = "stack") +
  scale_fill_manual(values = setNames(palette_8, d_main), labels = disc_labels) +
  scale_x_continuous(breaks = seq(1950, 2025, by = 5)) +
  labs(
    title = "Annual elasmobranch publications by discipline",
    subtitle = "Papers may appear in multiple discipline categories",
    x = "Year", y = "Count", fill = "Discipline"
  ) +
  theme_eea

save_plot(p_b1, "B1_temporal_papers_year_discipline")

# ── B2. Bubble chart: pressure emergence ──────────────────────────────────────
cat("Building B2...\n")

recent_cutoff <- max(df$year, na.rm = TRUE) - 4  # last 5 years

b2_stats <- map_dfr(pr_cols, function(col) {
  vals <- df[[col]]
  years <- df$year
  first_yr <- if (any(vals == 1, na.rm = TRUE)) min(years[!is.na(vals) & vals == 1], na.rm = TRUE) else NA_real_
  recent_mask <- years >= recent_cutoff & !is.na(years) & !is.na(vals)
  recent_rate <- if (sum(recent_mask) > 0) mean(vals[recent_mask], na.rm = TRUE) * sum(recent_mask) / 5 else 0
  total_papers <- sum(vals == 1, na.rm = TRUE)
  tibble(column = col, first_year = first_yr, current_rate = recent_rate, total_papers = total_papers)
}) |>
  filter(!is.na(first_year), total_papers >= 5) |>
  mutate(label = clean_name(column))

p_b2 <- b2_stats |>
  ggplot(aes(x = first_year, y = current_rate, size = total_papers, label = label)) +
  geom_point(aes(colour = label), alpha = 0.7, show.legend = FALSE) +
  geom_text_repel(size = 3, max.overlaps = 20, seed = 42) +
  scale_size_continuous(range = c(3, 18), name = "Total papers") +
  scale_x_continuous(breaks = seq(1950, 2025, by = 5)) +
  labs(
    title = "When did each pressure type first appear in elasmobranch research?",
    subtitle = "Bubble size = total papers; y-axis = recent annual rate (last 5 years)",
    x = "First year recorded", y = "Recent papers / year"
  ) +
  theme_eea

save_plot(p_b2, "B2_temporal_pressure_emergence")

# ── B3. Mitigation adoption: loess lines faceted ──────────────────────────────
cat("Building B3...\n")

b3_long <- map_dfr(mit_cols, function(col) {
  df |>
    select(year, val = all_of(col)) |>
    filter(!is.na(val)) |>
    count(year, val) |>
    filter(val == 1) |>
    mutate(technique = col) |>
    select(year, n, technique)
})

if (nrow(b3_long) > 0) {
  p_b3 <- b3_long |>
    mutate(technique = factor(technique, levels = mit_cols,
                              labels = clean_name(mit_cols))) |>
    ggplot(aes(x = year, y = n)) +
    geom_point(colour = "#2166AC", alpha = 0.5, size = 1.2) +
    geom_smooth(method = "loess", colour = "#E41A1C", fill = "#FDDBC7",
                se = TRUE, span = 0.6, linewidth = 0.8) +
    facet_wrap(~technique, scales = "free_y", ncol = 4) +
    labs(
      title = "Adoption of mitigation techniques in elasmobranch research",
      subtitle = "Points = annual counts; red line = LOESS smoother",
      x = "Year", y = "Papers per year"
    ) +
    theme_eea +
    theme(strip.text = element_text(face = "bold", size = 9))

  save_plot(p_b3, "B3_temporal_mitigation_adoption", w = 16, h = 10)
} else {
  cat("  Skipping B3: no mitigation data\n")
}

# ── B4. Impact evolution: 5-year bins faceted ─────────────────────────────────
cat("Building B4...\n")

imp_cols_clean <- imp_cols[imp_cols %in% names(df)]

b4_long <- map_dfr(imp_cols_clean, function(col) {
  df |>
    select(year, val = all_of(col)) |>
    filter(!is.na(val)) |>
    mutate(bin = floor(year / 5) * 5) |>
    group_by(bin) |>
    summarise(n = sum(val == 1, na.rm = TRUE), .groups = "drop") |>
    mutate(impact = col)
})

if (nrow(b4_long) > 0) {
  p_b4 <- b4_long |>
    mutate(impact = factor(impact, levels = imp_cols_clean,
                           labels = clean_name(imp_cols_clean))) |>
    ggplot(aes(x = bin, y = n)) +
    geom_line(colour = "#2166AC", linewidth = 0.8) +
    geom_point(colour = "#2166AC", size = 1.5) +
    facet_wrap(~impact, scales = "free_y", ncol = 4) +
    labs(
      title = "Evolution of impact metrics in elasmobranch research",
      subtitle = "Papers per 5-year bin recording each impact type",
      x = "5-year period", y = "Papers"
    ) +
    theme_eea +
    theme(strip.text = element_text(face = "bold", size = 9))

  save_plot(p_b4, "B4_temporal_impact_evolution", w = 16, h = 12)
} else {
  cat("  Skipping B4: no impact data\n")
}

# ── B5. Bycatch vs targeted fishing ───────────────────────────────────────────
cat("Building B5...\n")

b5_series <- list()

if ("pr_bycatch" %in% names(df)) {
  b5_series[["Bycatch (pressure)"]] <- df |>
    filter(!is.na(pr_bycatch)) |>
    group_by(year) |>
    summarise(n = sum(pr_bycatch == 1, na.rm = TRUE), .groups = "drop") |>
    mutate(series = "Bycatch (pressure)")
}

if ("pr_targeted_fishing" %in% names(df)) {
  b5_series[["Targeted fishing"]] <- df |>
    filter(!is.na(pr_targeted_fishing)) |>
    group_by(year) |>
    summarise(n = sum(pr_targeted_fishing == 1, na.rm = TRUE), .groups = "drop") |>
    mutate(series = "Targeted fishing")
}

if ("imp_is_bycatch" %in% names(df)) {
  b5_series[["Bycatch study (impact)"]] <- df |>
    filter(!is.na(imp_is_bycatch)) |>
    group_by(year) |>
    summarise(n = sum(imp_is_bycatch == TRUE, na.rm = TRUE), .groups = "drop") |>
    mutate(series = "Bycatch study (impact)")
}

if (length(b5_series) > 0) {
  b5_long <- bind_rows(b5_series)
  series_colours <- c(
    "Bycatch (pressure)"    = "#E41A1C",
    "Targeted fishing"      = "#2166AC",
    "Bycatch study (impact)"= "#FF7F00"
  )
  present_colours <- series_colours[names(series_colours) %in% unique(b5_long$series)]

  p_b5 <- b5_long |>
    ggplot(aes(x = year, y = n, colour = series)) +
    geom_line(linewidth = 1.0) +
    geom_point(size = 1.5, alpha = 0.6) +
    scale_colour_manual(values = present_colours) +
    scale_x_continuous(breaks = seq(1950, 2025, by = 5)) +
    labs(
      title = "Bycatch vs targeted fishing research attention",
      subtitle = "Annual paper counts",
      x = "Year", y = "Papers per year", colour = NULL
    ) +
    theme_eea

  save_plot(p_b5, "B5_temporal_bycatch_vs_targeted")
} else {
  cat("  Skipping B5: no bycatch/targeted columns found\n")
}

# ── B6. Discipline proportions: 100% stacked area ────────────────────────────
cat("Building B6...\n")

b6_long <- df |>
  select(year, all_of(d_main)) |>
  mutate(bin = floor(year / 5) * 5) |>
  pivot_longer(cols = all_of(d_main), names_to = "discipline", values_to = "flag") |>
  filter(!is.na(flag)) |>
  group_by(bin, discipline) |>
  summarise(n = sum(flag == 1, na.rm = TRUE), .groups = "drop") |>
  group_by(bin) |>
  mutate(prop = n / sum(n)) |>
  ungroup()

p_b6 <- b6_long |>
  mutate(discipline = factor(discipline, levels = rev(d_main))) |>
  ggplot(aes(x = bin, y = prop, fill = discipline)) +
  geom_area(position = "stack", colour = "white", linewidth = 0.2) +
  scale_fill_manual(values = setNames(rev(palette_8), rev(d_main)),
                    labels = function(x) clean_name(x)) +
  scale_x_continuous(breaks = seq(1950, 2025, by = 5)) +
  scale_y_continuous(labels = scales::percent_format()) +
  labs(
    title = "Proportional attention across disciplines in elasmobranch research",
    subtitle = "100% stacked area by 5-year periods",
    x = "5-year period", y = "Proportion of papers", fill = "Discipline"
  ) +
  theme_eea

save_plot(p_b6, "B6_temporal_discipline_proportions")

# ── B7. Validation: newly added schema columns ────────────────────────────────
cat("Building B7...\n")

new_cols_wanted <- c(
  "pr_discarding", "pr_seabed_disturbance", "pr_visual_disturbance",
  "gear_dredge", "gear_trawl_beam", "gear_trawl_otter",
  "gear_mit_weak_hook", "gear_mit_line_weight", "gear_mit_setting",
  "gear_mit_pinger", "gear_mit_illumination", "gear_mit_wire_leader",
  "gear_mit_ghost",
  "imp_community_composition", "imp_biodiversity",
  "imp_size_structure", "imp_productivity"
)

new_cols_present <- new_cols_wanted[new_cols_wanted %in% names(df)]
cat("  New cols present:", length(new_cols_present), "of", length(new_cols_wanted), "\n")

if (length(new_cols_present) > 0) {
  b7_long <- map_dfr(new_cols_present, function(col) {
    df |>
      select(year, val = all_of(col)) |>
      filter(!is.na(val)) |>
      group_by(year) |>
      summarise(n = sum(val == 1, na.rm = TRUE), .groups = "drop") |>
      mutate(column = col)
  })

  p_b7 <- b7_long |>
    mutate(column = factor(column, levels = new_cols_present,
                           labels = clean_name(new_cols_present))) |>
    ggplot(aes(x = year, y = n)) +
    geom_col(fill = "#4DAF4A", width = 0.8, alpha = 0.85) +
    facet_wrap(~column, scales = "free_y", ncol = 4) +
    labs(
      title = "Validation: newly added schema columns over time",
      subtitle = "Annual paper counts for new columns; verify patterns look plausible",
      x = "Year", y = "Papers"
    ) +
    theme_eea +
    theme(strip.text = element_text(face = "bold", size = 9))

  save_plot(p_b7, "B7_temporal_new_columns", w = 16, h = 12)
} else {
  cat("  Skipping B7: none of the target columns found in data\n")
}

cat("All temporal plots complete.\n")
