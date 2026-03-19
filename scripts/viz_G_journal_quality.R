## viz_G_journal_quality.R
## Journal quality visualisations for EEA 2025 Data Panel
## Outputs: outputs/figures/G_journal_*.png and *.pdf

library(tidyverse)

base_dir <- "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
fig_dir  <- file.path(base_dir, "outputs/figures")
dir.create(fig_dir, showWarnings = FALSE, recursive = TRUE)

df <- read_csv(file.path(base_dir, "outputs/viz_data.csv"),
               show_col_types = FALSE, guess_max = 5000)
df <- df |> filter(!is.na(year), year >= 1950, year <= 2025)

jq <- read_csv(file.path(base_dir, "data/journal_quality/scimago_match.csv"),
               show_col_types = FALSE)

# Join on normalised journal name
df <- df |> mutate(journal_lower = str_to_lower(str_trim(journal)))
jq <- jq |> mutate(journal_lower = str_to_lower(str_trim(our_journal_name)))

dfj <- df |> left_join(jq |> select(journal_lower, sjr_score, quartile, h_index, open_access),
                        by = "journal_lower")

# Discipline palette (from visualize_discipline_trends.R — EEA 2025 standard)
disc_palette <- c(
  "d_biology"      = "#F18F01",
  "d_behaviour"    = "#5E548E",
  "d_trophic"      = "#BC4B51",
  "d_genetics"     = "#A23B72",
  "d_movement"     = "#6A994E",
  "d_fisheries"    = "#C73E1D",
  "d_conservation" = "#8B7E74",
  "d_data_science" = "#2E86AB"
)

d_main <- names(disc_palette)[names(disc_palette) %in% names(dfj)]

clean_name <- function(x) {
  x |> str_remove("^(eco_|pr_|gear_|imp_|d_|b_|sp_|gear_mit_|alt_)") |>
    str_replace_all("_", " ") |> str_to_title()
}

disc_palette_clean <- setNames(disc_palette, clean_name(names(disc_palette)))

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

## ── G1: Quartile distribution donut (continuous palette) ────────────────────
q_data <- dfj |>
  filter(!is.na(quartile), quartile != "-") |>
  mutate(q_num = as.integer(str_extract(quartile, "\\d"))) |>
  count(quartile, q_num) |>
  mutate(pct = n / sum(n) * 100,
         label = paste0(quartile, "\n", format(n, big.mark = ","), "\n(", round(pct, 1), "%)"))

p1 <- ggplot(q_data, aes(x = 2, y = n, fill = q_num)) +
  geom_col(width = 1, colour = "white", linewidth = 0.5) +
  coord_polar(theta = "y") +
  xlim(0.5, 2.5) +
  scale_fill_viridis_c(option = "viridis", direction = -1, breaks = 1:4, labels = paste0("Q", 1:4)) +
  geom_text(aes(label = label), position = position_stack(vjust = 0.5), size = 3.5) +
  labs(title = "Journal Quartile Distribution",
       subtitle = paste0("SCImago quartiles for ", format(sum(q_data$n), big.mark = ","),
                         " papers (", round(sum(q_data$n)/nrow(dfj)*100, 1), "% of database)"),
       fill = "Quartile") +
  theme_void(base_size = 12) +
  theme(plot.background = element_rect(fill = "white", colour = NA),
        plot.title = element_text(face = "bold", size = 14),
        plot.subtitle = element_text(colour = "grey40"))

save_plot(p1, "G_journal_quartile_donut", w = 10, h = 8)

## ── G2: Top 20 journals bar chart (continuous quartile fill) ────────────────
top_j <- dfj |>
  filter(!is.na(quartile), quartile != "-") |>
  mutate(q_num = as.integer(str_extract(quartile, "\\d"))) |>
  count(journal, quartile, q_num, sort = TRUE) |>
  slice_head(n = 20) |>
  mutate(journal = fct_reorder(journal, n))

p2 <- ggplot(top_j, aes(x = n, y = journal, fill = q_num)) +
  geom_col(colour = "white", linewidth = 0.3) +
  geom_text(aes(label = n), hjust = -0.1, size = 3.5) +
  scale_fill_viridis_c(option = "viridis", direction = -1, breaks = 1:4, labels = paste0("Q", 1:4)) +
  scale_x_continuous(expand = expansion(mult = c(0, 0.15))) +
  labs(title = "Top 20 Journals in Elasmobranch Research",
       subtitle = "Ranked by paper count, coloured by SCImago quartile",
       x = "Number of Papers", y = NULL, fill = "Quartile") +
  theme_eea +
  theme(axis.text.x = element_text(angle = 0, hjust = 0.5))

save_plot(p2, "G_journal_top20", w = 14, h = 9)

## ── G3: Quartile over time (continuous palette) ────────────────────────────
q_time <- dfj |>
  filter(!is.na(quartile), quartile != "-", year >= 1970) |>
  mutate(q_num = as.integer(str_extract(quartile, "\\d"))) |>
  count(year, quartile, q_num) |>
  group_by(year) |>
  mutate(pct = n / sum(n) * 100)

p3 <- ggplot(q_time, aes(x = year, y = pct, fill = q_num)) +
  geom_area(alpha = 0.85) +
  scale_fill_viridis_c(option = "viridis", direction = -1, breaks = 1:4, labels = paste0("Q", 1:4)) +
  labs(title = "Journal Quality Trends Over Time",
       subtitle = "Proportion of elasmobranch papers by SCImago quartile",
       x = "Year", y = "Percentage of Papers (%)", fill = "Quartile") +
  theme_eea

save_plot(p3, "G_journal_quartile_over_time", w = 14, h = 8)

## ── G4: SJR by discipline (cropped, coloured by discipline) ─────────────────
disc_sjr <- dfj |>
  filter(!is.na(sjr_score)) |>
  select(all_of(d_main), sjr_score) |>
  pivot_longer(all_of(d_main), names_to = "discipline", values_to = "flag") |>
  filter(flag == 1) |>
  mutate(discipline = clean_name(discipline))

p4 <- ggplot(disc_sjr, aes(x = reorder(discipline, sjr_score, FUN = median), y = sjr_score,
                            fill = discipline)) +
  geom_violin(alpha = 0.3) +
  geom_boxplot(width = 0.15, fill = "white", outlier.alpha = 0.1) +
  coord_flip(ylim = c(0, 7.5)) +
  scale_fill_manual(values = disc_palette_clean) +
  labs(title = "Journal Quality by Research Discipline",
       subtitle = "SJR score distribution (cropped to 7.5; higher = more influential)",
       x = NULL, y = "SCImago Journal Rank (SJR)") +
  theme_eea +
  theme(axis.text.x = element_text(angle = 0, hjust = 0.5),
        legend.position = "none")

save_plot(p4, "G_journal_sjr_by_discipline", w = 12, h = 8)

## ── G5: Top journals heatmap (adaptive text contrast) ───────────────────────
top15_j <- dfj |> filter(!is.na(quartile)) |> count(journal, sort = TRUE) |> slice_head(n = 15) |> pull(journal)

jd_heat <- dfj |>
  filter(journal %in% top15_j) |>
  select(journal, all_of(d_main)) |>
  pivot_longer(all_of(d_main), names_to = "discipline", values_to = "flag") |>
  filter(flag == 1) |>
  count(journal, discipline) |>
  mutate(discipline = clean_name(discipline),
         text_col = ifelse(n > max(n) * 0.4, "white", "grey20"))

p5 <- ggplot(jd_heat, aes(x = discipline, y = fct_reorder(journal, n, .fun = sum), fill = n)) +
  geom_tile(colour = "white", linewidth = 0.5) +
  geom_text(aes(label = n, colour = text_col), size = 3, show.legend = FALSE) +
  scale_fill_viridis_c(option = "mako", direction = -1) +
  scale_colour_identity() +
  labs(title = "Top 15 Journals x Research Discipline",
       subtitle = "Number of papers per journal-discipline combination",
       x = NULL, y = NULL, fill = "Papers") +
  theme_eea +
  theme(axis.text.x = element_text(angle = 45, hjust = 1))

save_plot(p5, "G_journal_discipline_heatmap", w = 14, h = 10)

## ── G6: Mean SJR by year by discipline ──────────────────────────────────────
sjr_year <- dfj |>
  filter(!is.na(sjr_score), year >= 1970) |>
  select(year, all_of(d_main), sjr_score) |>
  pivot_longer(all_of(d_main), names_to = "discipline", values_to = "flag") |>
  filter(flag == 1) |>
  mutate(discipline = clean_name(discipline)) |>
  summarise(.by = c(year, discipline), mean_sjr = mean(sjr_score, na.rm = TRUE))

p6 <- ggplot(sjr_year, aes(x = year, y = mean_sjr, colour = discipline)) +
  geom_line(linewidth = 0.8, alpha = 0.8) +
  geom_smooth(se = FALSE, method = "loess", span = 0.3, linewidth = 1.2, alpha = 0.6, linetype = "dashed") +
  scale_colour_manual(values = disc_palette_clean) +
  labs(title = "Mean Journal Quality Over Time by Discipline",
       subtitle = "Mean SJR score per year (lines + LOESS trend)",
       x = "Year", y = "Mean SJR Score", colour = "Discipline") +
  theme_eea +
  theme(axis.text.x = element_text(angle = 0, hjust = 0.5))

save_plot(p6, "G_journal_sjr_by_year_discipline", w = 14, h = 8)

cat("\nAll journal figures complete!\n")
