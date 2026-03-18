## viz_F_altmetric.R
## Comprehensive Altmetric visualisations for EEA 2025 Data Panel
## Outputs: outputs/figures/F_alt_*.png and *.pdf

library(tidyverse)

base_dir <- "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
fig_dir  <- file.path(base_dir, "outputs/figures")
dir.create(fig_dir, showWarnings = FALSE, recursive = TRUE)

df <- read_csv(file.path(base_dir, "outputs/viz_data.csv"),
               show_col_types = FALSE, guess_max = 5000)
df <- df |> filter(!is.na(year), year >= 1950, year <= 2025)

d_main <- c("d_biology","d_behaviour","d_trophic","d_genetics",
            "d_movement","d_fisheries","d_conservation","d_data_science")
d_main <- d_main[d_main %in% names(df)]

alt_metrics <- c("alt_score","alt_tweeters","alt_posts","alt_fbwalls",
                 "alt_blogs","alt_news","alt_policy","alt_wikipedia",
                 "alt_reddit","alt_mendeley")
alt_labels <- c(
  alt_score    = "Attention Score",
  alt_tweeters = "Twitter/X",
  alt_posts    = "Total Posts",
  alt_fbwalls  = "Facebook",
  alt_blogs    = "Blogs",
  alt_news     = "News",
  alt_policy   = "Policy Docs",
  alt_wikipedia = "Wikipedia",
  alt_reddit   = "Reddit",
  alt_mendeley = "Mendeley Readers"
)

clean_name <- function(x) {
  x |> str_remove("^(eco_|pr_|gear_|imp_|d_|b_|sp_|gear_mit_|alt_)") |>
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

## ── Papers with Altmetric data ─────────────────────────────────────────────
df_alt <- df |> filter(!is.na(alt_score))
n_alt  <- nrow(df_alt)
cat("Papers with alt_score:", n_alt, "\n")

## ── F1: Distribution of Altmetric Attention Scores ────────────────────────
med_score  <- median(df_alt$alt_score, na.rm = TRUE)
mean_score <- mean(df_alt$alt_score,   na.rm = TRUE)

p1 <- ggplot(df_alt, aes(x = alt_score)) +
  geom_histogram(bins = 60, fill = "#2C3E50", colour = "white", linewidth = 0.2) +
  geom_vline(aes(xintercept = med_score,  colour = "Median"), linewidth = 1, linetype = "dashed") +
  geom_vline(aes(xintercept = mean_score, colour = "Mean"),   linewidth = 1, linetype = "solid") +
  scale_x_log10(labels = scales::comma) +
  scale_colour_manual(name = NULL,
                      values = c(Median = "#E74C3C", Mean = "#F39C12")) +
  labs(
    title    = "Distribution of Altmetric Attention Scores",
    subtitle = sprintf("n = %s papers | Median = %.1f | Mean = %.1f",
                       scales::comma(n_alt), med_score, mean_score),
    x = "Altmetric Attention Score (log\u2081\u2080 scale)",
    y = "Number of papers"
  ) +
  theme_eea

save_plot(p1, "F_alt_score_distribution")

## ── F2: % of papers with >= 1 mention per metric ──────────────────────────
pct_data <- tibble(
  metric = alt_metrics,
  label  = alt_labels[alt_metrics],
  pct    = map_dbl(alt_metrics, function(m) {
    if (!m %in% names(df_alt)) return(NA_real_)
    mean(!is.na(df_alt[[m]]) & df_alt[[m]] >= 1, na.rm = TRUE) * 100
  })
) |>
  filter(!is.na(pct)) |>
  arrange(pct) |>
  mutate(label = factor(label, levels = label))

p2 <- ggplot(pct_data, aes(x = pct, y = label)) +
  geom_col(fill = "#2980B9") +
  geom_text(aes(label = sprintf("%.0f%%", pct)), hjust = -0.1, size = 3.5) +
  scale_x_continuous(limits = c(0, 110), labels = function(x) paste0(x, "%")) +
  labs(
    title    = "Altmetric coverage: % of papers with \u2265 1 mention",
    subtitle = sprintf("Among %s papers with Altmetric data", scales::comma(n_alt)),
    x = "% of papers",
    y = NULL
  ) +
  theme_eea +
  theme(axis.text.x = element_text(angle = 0, hjust = 0.5))

save_plot(p2, "F_alt_metrics_overview", w = 12, h = 7)

## ── F3: Grouped column plot by discipline ─────────────────────────────────
disc5_metrics <- c("alt_tweeters","alt_news","alt_policy","alt_wikipedia","alt_mendeley")
disc5_colours <- c(
  alt_tweeters  = "#1DA1F2",
  alt_news      = "#E74C3C",
  alt_policy    = "#8E44AD",
  alt_wikipedia = "#95A5A6",
  alt_mendeley  = "#F39C12"
)
disc5_labels <- alt_labels[disc5_metrics]

disc_long <- df_alt |>
  select(all_of(c(d_main, disc5_metrics))) |>
  pivot_longer(cols = all_of(d_main), names_to = "discipline", values_to = "disc_val") |>
  filter(disc_val == 1) |>
  pivot_longer(cols = all_of(disc5_metrics), names_to = "metric", values_to = "value") |>
  group_by(discipline, metric) |>
  summarise(med_val = median(value, na.rm = TRUE), .groups = "drop") |>
  mutate(
    disc_label   = clean_name(discipline),
    metric_label = disc5_labels[metric],
    metric_label = factor(metric_label, levels = disc5_labels)
  )

p3 <- ggplot(disc_long, aes(x = disc_label, y = med_val,
                             fill = metric_label, group = metric_label)) +
  geom_col(position = position_dodge(width = 0.85), colour = "white", linewidth = 0.2) +
  scale_fill_manual(name = "Metric", values = setNames(disc5_colours, disc5_labels)) +
  scale_y_continuous(labels = scales::comma) +
  labs(
    title    = "Median Altmetric engagement by discipline",
    subtitle = "Papers assigned to each discipline (binary flag = 1); five key metrics",
    x = NULL,
    y = "Median value"
  ) +
  theme_eea +
  theme(legend.position = "top")

save_plot(p3, "F_alt_discipline_grouped", w = 16, h = 9)

## ── F4: Discipline × metric heatmap (column-scaled medians) ───────────────
heat_long <- df_alt |>
  select(all_of(c(d_main, alt_metrics))) |>
  pivot_longer(cols = all_of(d_main), names_to = "discipline", values_to = "disc_val") |>
  filter(disc_val == 1) |>
  pivot_longer(cols = all_of(alt_metrics), names_to = "metric", values_to = "value") |>
  group_by(discipline, metric) |>
  summarise(med_val = median(value, na.rm = TRUE), .groups = "drop") |>
  group_by(metric) |>
  mutate(scaled = (med_val - min(med_val)) / (max(med_val) - min(med_val) + 1e-9)) |>
  ungroup() |>
  mutate(
    disc_label   = clean_name(discipline),
    metric_label = alt_labels[metric],
    metric_label = factor(metric_label, levels = alt_labels)
  )

p4 <- ggplot(heat_long, aes(x = metric_label, y = disc_label, fill = scaled)) +
  geom_tile(colour = "white", linewidth = 0.5) +
  geom_text(aes(label = sprintf("%.1f", med_val)), size = 2.8, colour = "white") +
  scale_fill_viridis_c(option = "plasma", name = "Scaled\nmedian") +
  labs(
    title    = "Altmetric engagement by discipline (scaled medians)",
    subtitle = "Each column scaled 0\u20131 independently so magnitudes are comparable; cell text = raw median",
    x = NULL,
    y = NULL
  ) +
  theme_eea +
  theme(axis.text.x = element_text(angle = 45, hjust = 1))

save_plot(p4, "F_alt_discipline_heatmap", w = 14, h = 7)

## ── F5: Median alt_score per year with IQR ribbon ─────────────────────────
timeline_score <- df_alt |>
  filter(!is.na(year)) |>
  group_by(year) |>
  summarise(
    n      = n(),
    med    = median(alt_score, na.rm = TRUE),
    q25    = quantile(alt_score, 0.25, na.rm = TRUE),
    q75    = quantile(alt_score, 0.75, na.rm = TRUE),
    .groups = "drop"
  ) |>
  filter(n >= 20)

p5 <- ggplot(timeline_score, aes(x = year)) +
  geom_ribbon(aes(ymin = q25, ymax = q75), fill = "#2980B9", alpha = 0.25) +
  geom_line(aes(y = med), colour = "#2980B9", linewidth = 1.2) +
  geom_point(aes(y = med, size = n), colour = "#2980B9") +
  scale_y_log10(labels = scales::comma) +
  scale_size_continuous(name = "Papers", range = c(1, 5)) +
  labs(
    title    = "Altmetric Attention Score over time",
    subtitle = "Median (line), IQR ribbon; years with \u2265 20 papers with scores only",
    x = "Year",
    y = "Median Altmetric Score (log\u2081\u2080)"
  ) +
  theme_eea +
  theme(axis.text.x = element_text(angle = 45, hjust = 1))

save_plot(p5, "F_alt_timeline_score", w = 14, h = 7)

## ── F6: Faceted timeline of key metrics ───────────────────────────────────
facet_metrics <- c("alt_tweeters","alt_news","alt_policy",
                   "alt_wikipedia","alt_mendeley","alt_blogs")
facet_labels  <- alt_labels[facet_metrics]

timeline_long <- df_alt |>
  filter(year >= 2010) |>
  select(year, all_of(facet_metrics)) |>
  pivot_longer(cols = all_of(facet_metrics), names_to = "metric", values_to = "value") |>
  group_by(year, metric) |>
  summarise(med = median(value, na.rm = TRUE), n = n(), .groups = "drop") |>
  filter(n >= 5) |>
  mutate(metric_label = factor(facet_labels[metric], levels = facet_labels))

p6 <- ggplot(timeline_long, aes(x = year, y = med)) +
  geom_line(colour = "#2C3E50", linewidth = 0.9) +
  geom_point(colour = "#2C3E50", size = 1.5) +
  facet_wrap(~ metric_label, scales = "free_y", ncol = 3) +
  labs(
    title    = "Altmetric engagement trends by metric",
    subtitle = "Median value per year; papers from 2010 onwards",
    x = "Year",
    y = "Median value"
  ) +
  theme_eea +
  theme(axis.text.x = element_text(angle = 45, hjust = 1))

save_plot(p6, "F_alt_timeline_metrics", w = 16, h = 10)

## ── F7: Top 20 papers by alt_score ────────────────────────────────────────
make_label <- function(authors, year, title, max_title = 55) {
  first_author <- str_extract(as.character(authors), "^[^,;]+") |>
    str_trim() |> str_trunc(20)
  yr   <- suppressWarnings(as.integer(year))
  ttl  <- str_trunc(as.character(title), max_title)
  sprintf("%s (%s) — %s", first_author, yr, ttl)
}

top20_score <- df_alt |>
  arrange(desc(alt_score)) |>
  slice_head(n = 20) |>
  mutate(paper_label = make_label(authors, year, title)) |>
  arrange(alt_score) |>
  mutate(paper_label = factor(paper_label, levels = paper_label))

p7 <- ggplot(top20_score, aes(x = alt_score, y = paper_label, fill = alt_score)) +
  geom_col() +
  scale_fill_viridis_c(option = "inferno", direction = -1, name = "Score") +
  scale_x_continuous(labels = scales::comma) +
  labs(
    title    = "Most-discussed elasmobranch papers (Altmetric score)",
    subtitle = "Top 20 papers by Altmetric Attention Score",
    x = "Altmetric Attention Score",
    y = NULL
  ) +
  theme_eea +
  theme(axis.text.x = element_text(angle = 0, hjust = 0.5),
        axis.text.y = element_text(size = 8))

save_plot(p7, "F_alt_top_papers", w = 16, h = 10)

## ── F8: World map — median alt_score by author country ────────────────────
if ("institution_country_first" %in% names(df_alt)) {
  has_sf  <- requireNamespace("sf",             quietly = TRUE)
  has_rne <- requireNamespace("rnaturalearth",  quietly = TRUE)
  has_rne_data <- requireNamespace("rnaturalearthdata", quietly = TRUE)

  if (has_sf && has_rne && has_rne_data) {
    library(sf)
    library(rnaturalearth)

    country_med <- df_alt |>
      filter(!is.na(institution_country_first)) |>
      group_by(iso_a2 = institution_country_first) |>
      summarise(med_score = median(alt_score, na.rm = TRUE),
                n = n(), .groups = "drop") |>
      filter(n >= 5)

    world <- ne_countries(scale = "medium", returnclass = "sf")

    world_data <- world |>
      left_join(country_med, by = "iso_a2")

    p8 <- ggplot(world_data) +
      geom_sf(aes(fill = med_score), colour = "grey60", linewidth = 0.15) +
      scale_fill_viridis_c(
        option    = "plasma",
        name      = "Median\nAltmetric\nScore",
        na.value  = "grey85",
        trans     = "log10",
        labels    = scales::comma
      ) +
      coord_sf(crs = "+proj=robin") +
      labs(
        title    = "Median Altmetric score by author country",
        subtitle = sprintf("Countries with \u2265 5 papers (n = %d countries shown)",
                           sum(!is.na(world_data$med_score)))
      ) +
      theme_eea +
      theme(
        axis.text.x  = element_blank(),
        axis.text.y  = element_blank(),
        axis.ticks   = element_blank(),
        panel.grid   = element_blank()
      )

    save_plot(p8, "F_alt_country_map", w = 16, h = 9)
  } else {
    cat("Skipping F8 (country map): sf / rnaturalearth not available\n")
  }
} else {
  cat("Skipping F8 (country map): institution_country_first column not found\n")
}

## ── F9: alt_score by open access status ───────────────────────────────────
oa_col <- intersect(c("oa_status","oa_type","open_access_status"), names(df_alt))
if (length(oa_col) > 0) {
  oa_col <- oa_col[1]
  oa_data <- df_alt |>
    filter(!is.na(.data[[oa_col]])) |>
    rename(oa = all_of(oa_col)) |>
    mutate(oa = str_to_title(as.character(oa))) |>
    group_by(oa) |>
    filter(n() >= 20) |>
    ungroup()

  oa_counts <- oa_data |> count(oa, name = "n_papers")

  oa_palette <- c(
    Gold   = "#F1C40F", Green  = "#27AE60", Hybrid = "#8E44AD",
    Bronze = "#E67E22", Closed = "#7F8C8D", Diamond = "#1ABC9C"
  )
  oa_fill <- oa_palette[oa_data$oa]
  oa_fill[is.na(oa_fill)] <- "#BDC3C7"

  p9 <- ggplot(oa_data, aes(x = oa, y = alt_score)) +
    geom_violin(aes(fill = oa), alpha = 0.6, colour = "grey40", trim = TRUE) +
    geom_boxplot(width = 0.2, outlier.size = 0.5, outlier.alpha = 0.3,
                 colour = "grey30", fill = "white") +
    geom_text(data = oa_counts, aes(x = oa, y = 0.5, label = paste0("n=", scales::comma(n_papers))),
              size = 3, colour = "grey40", inherit.aes = FALSE) +
    scale_y_log10(labels = scales::comma) +
    scale_fill_manual(values = oa_palette, na.value = "#BDC3C7") +
    guides(fill = "none") +
    labs(
      title    = "Altmetric score by open access status",
      subtitle = "Log\u2081\u2080 scale; only OA categories with \u2265 20 papers",
      x = "Open Access status",
      y = "Altmetric Attention Score"
    ) +
    theme_eea +
    theme(axis.text.x = element_text(angle = 0, hjust = 0.5))

  save_plot(p9, "F_alt_oa_comparison", w = 12, h = 8)
} else {
  cat("Skipping F9 (OA comparison): no oa_status column found\n")
}

## ── F10: Top 20 papers by alt_policy ──────────────────────────────────────
if ("alt_policy" %in% names(df_alt)) {
  top20_policy <- df_alt |>
    filter(!is.na(alt_policy), alt_policy >= 1) |>
    arrange(desc(alt_policy)) |>
    slice_head(n = 20) |>
    mutate(paper_label = make_label(authors, year, title)) |>
    arrange(alt_policy) |>
    mutate(paper_label = factor(paper_label, levels = paper_label))

  if (nrow(top20_policy) > 0) {
    p10 <- ggplot(top20_policy,
                  aes(x = alt_policy, y = paper_label, fill = alt_policy)) +
      geom_col() +
      scale_fill_viridis_c(option = "magma", direction = -1, name = "Policy\nmentions") +
      scale_x_continuous(labels = scales::comma) +
      labs(
        title    = "Elasmobranch papers cited in policy documents",
        subtitle = "Top 20 papers by number of policy document mentions (Altmetric)",
        x = "Number of policy document mentions",
        y = NULL
      ) +
      theme_eea +
      theme(axis.text.x = element_text(angle = 0, hjust = 0.5),
            axis.text.y = element_text(size = 8))

    save_plot(p10, "F_alt_policy_papers", w = 16, h = 10)
  } else {
    cat("Skipping F10: no papers with alt_policy >= 1\n")
  }
} else {
  cat("Skipping F10: alt_policy column not found\n")
}

cat("\nAll Altmetric figures complete.\n")
