#!/usr/bin/env Rscript
# ============================================================================
# visualize_cross_schema_extra.R
#
# Additional cross-schema combination plots not covered by issue2 script:
#   - Ecosystem x Gear x Pressure (3-way faceted heatmap)
#   - Species x Pressure heatmap
#   - Discipline x Gear heatmap
#
# Author: Simon Dedman / EEA 2025 Data Panel
# Date: 2026-03-15
# ============================================================================

library(tidyverse)
library(scales)
library(viridis)

# ============================================================================
# CONFIGURATION
# ============================================================================

input_dir  <- "outputs/meeting_review"
output_dir <- "outputs/figures"
dir.create(output_dir, showWarnings = FALSE, recursive = TRUE)

theme_xs <- theme_minimal(base_size = 13) +
  theme(
    plot.title       = element_text(face = "bold", size = 15, hjust = 0),
    plot.subtitle    = element_text(colour = "grey40", size = 11, hjust = 0),
    panel.background = element_rect(fill = "white", colour = NA),
    plot.background  = element_rect(fill = "white", colour = NA),
    panel.grid.major = element_line(colour = "grey92"),
    panel.grid.minor = element_blank(),
    legend.position  = "right",
    axis.text        = element_text(colour = "grey30"),
    axis.title       = element_text(colour = "grey20"),
    strip.text       = element_text(face = "bold", size = 10)
  )

save_plot <- function(p, name, w = 12, h = 8) {
  ggsave(file.path(output_dir, paste0(name, ".png")), p, width = w, height = h,
         dpi = 300, bg = "white")
  ggsave(file.path(output_dir, paste0(name, ".pdf")), p, width = w, height = h,
         bg = "white")
  cat(sprintf("  Saved: %s (.png + .pdf)\n", name))
}

pretty_name <- function(x) {
  x |>
    str_remove("^[a-z]+_") |>
    str_replace_all("_", " ") |>
    str_to_title() |>
    str_replace("Iuu", "IUU") |>
    str_replace("Cpue", "CPUE") |>
    str_replace("Brd", "BRD") |>
    str_replace("Mit ", "Mitigation: ")
}

# ============================================================================
# 1. LOAD DATA
# ============================================================================

cat("Loading data...\n")
df <- read_csv(file.path(input_dir, "enriched_schema_for_plots.csv"),
               show_col_types = FALSE)
df_sp <- read_csv(file.path(input_dir, "enriched_with_top30_species.csv"),
                  show_col_types = FALSE)

d_cols    <- names(df)[str_starts(names(df), "d_")]
eco_cols  <- names(df)[str_starts(names(df), "eco_")]
pr_cols   <- names(df)[str_starts(names(df), "pr_")]
gear_cols <- names(df)[str_starts(names(df), "gear_") & names(df) != "gear_target_species"]
sp_cols   <- names(df_sp)[str_starts(names(df_sp), "sp_")]

# ============================================================================
# 2. DISCIPLINE x GEAR HEATMAP
# ============================================================================

cat("\n=== Discipline x Gear heatmap ===\n")

disc_gear_mat <- map_dfr(d_cols, function(d) {
  map_dfr(gear_cols, function(gr) {
    tibble(
      discipline = d,
      gear       = gr,
      n = sum(df[[d]] == 1 & df[[gr]] == 1, na.rm = TRUE)
    )
  })
}) |>
  mutate(
    discipline_label = pretty_name(discipline),
    gear_label       = pretty_name(gear)
  )

disc_order <- disc_gear_mat |>
  group_by(discipline_label) |> summarise(total = sum(n)) |>
  arrange(total) |> pull(discipline_label)

gear_order <- disc_gear_mat |>
  group_by(gear_label) |> summarise(total = sum(n)) |>
  arrange(desc(total)) |> pull(gear_label)

p1 <- disc_gear_mat |>
  mutate(
    discipline_label = factor(discipline_label, levels = disc_order),
    gear_label       = factor(gear_label, levels = gear_order)
  ) |>
  ggplot(aes(x = gear_label, y = discipline_label, fill = n)) +
  geom_tile(colour = "white", linewidth = 0.3) +
  geom_text(aes(label = ifelse(n > 0, comma(n), "")), size = 2.8, colour = "grey20") +
  scale_fill_viridis_c(option = "cividis", direction = -1, name = "Papers",
                       trans = "sqrt") +
  labs(
    title    = "Discipline x Fishing Gear Co-occurrence",
    subtitle = "Which disciplines study which gear types?",
    x = NULL, y = NULL
  ) +
  theme_xs +
  theme(axis.text.x = element_text(angle = 45, hjust = 1, size = 9))
save_plot(p1, "issue2_discipline_gear_heatmap", w = 14, h = 10)

# ============================================================================
# 3. SPECIES x PRESSURE HEATMAP (top 20 species)
# ============================================================================

cat("\n=== Species x Pressure heatmap ===\n")

# Re-read enriched data with species + pressure columns
pr_cols_sp <- names(df_sp)[str_starts(names(df_sp), "pr_") |
                            names(df_sp) %in% names(df)[str_starts(names(df), "pr_")]]
# Actually pr_ columns aren't in the species CSV, need to merge
# Use the schema CSV which has pr_ columns, merge via row index
df_full <- read_csv(file.path(input_dir, "enriched_schema_for_plots.csv"),
                    show_col_types = FALSE)

sp_pr_mat <- map_dfr(sp_cols[1:min(20, length(sp_cols))], function(sp) {
  map_dfr(pr_cols, function(pr) {
    tibble(
      species  = sp,
      pressure = pr,
      n = sum(df_sp[[sp]] == 1 & df_full[[pr]] == 1, na.rm = TRUE)
    )
  })
}) |>
  mutate(
    species_label  = species |>
      str_remove("^sp_") |>
      str_replace_all("_", " ") |>
      str_to_sentence(),
    pressure_label = pretty_name(pressure)
  )

sp_order <- sp_pr_mat |>
  group_by(species_label) |> summarise(total = sum(n)) |>
  arrange(total) |> pull(species_label)

pr_order <- sp_pr_mat |>
  group_by(pressure_label) |> summarise(total = sum(n)) |>
  arrange(desc(total)) |> pull(pressure_label)

p2 <- sp_pr_mat |>
  mutate(
    species_label  = factor(species_label, levels = sp_order),
    pressure_label = factor(pressure_label, levels = pr_order)
  ) |>
  ggplot(aes(x = pressure_label, y = species_label, fill = n)) +
  geom_tile(colour = "white", linewidth = 0.3) +
  geom_text(aes(label = ifelse(n > 0, n, "")), size = 2.5, colour = "grey20") +
  scale_fill_viridis_c(option = "rocket", direction = -1, name = "Papers",
                       trans = "sqrt") +
  labs(
    title    = "Top 20 Species x Pressure Co-occurrence",
    subtitle = "Which species face which studied pressures?",
    x = NULL, y = NULL
  ) +
  theme_xs +
  theme(
    axis.text.x = element_text(angle = 45, hjust = 1, size = 9),
    axis.text.y = element_text(face = "italic", size = 9)
  )
save_plot(p2, "issue2_species_pressure_heatmap", w = 15, h = 10)

# ============================================================================
# 4. ECOSYSTEM x GEAR x PRESSURE (3-way faceted heatmaps)
# ============================================================================

cat("\n=== Ecosystem x Gear x Pressure (3-way) ===\n")

# Focus on top 5 ecosystems, all gears, all pressures (facet by ecosystem)
top5_eco <- c("eco_marine", "eco_coastal", "eco_pelagic", "eco_demersal", "eco_freshwater")

three_way <- map_dfr(top5_eco, function(eco) {
  map_dfr(gear_cols, function(gr) {
    map_dfr(pr_cols, function(pr) {
      n_val <- sum(df[[eco]] == 1 & df[[gr]] == 1 & df[[pr]] == 1, na.rm = TRUE)
      if (n_val > 0) {
        tibble(ecosystem = eco, gear = gr, pressure = pr, n = n_val)
      }
    })
  })
}) |>
  mutate(
    ecosystem_label = pretty_name(ecosystem),
    gear_label      = pretty_name(gear),
    pressure_label  = pretty_name(pressure)
  )

# Order axes by total across all facets
gear_order3 <- three_way |>
  group_by(gear_label) |> summarise(total = sum(n)) |>
  arrange(total) |> pull(gear_label)

pr_order3 <- three_way |>
  group_by(pressure_label) |> summarise(total = sum(n)) |>
  arrange(desc(total)) |> pull(pressure_label)

p3 <- three_way |>
  mutate(
    gear_label     = factor(gear_label, levels = gear_order3),
    pressure_label = factor(pressure_label, levels = pr_order3)
  ) |>
  ggplot(aes(x = pressure_label, y = gear_label, fill = n)) +
  geom_tile(colour = "white", linewidth = 0.2) +
  geom_text(aes(label = ifelse(n > 0, n, "")), size = 1.8, colour = "grey20") +
  facet_wrap(~ ecosystem_label, ncol = 3) +
  scale_fill_viridis_c(option = "inferno", direction = -1, name = "Papers",
                       trans = "sqrt") +
  labs(
    title    = "Gear x Pressure by Ecosystem",
    subtitle = "Three-way co-occurrence: top 5 ecosystems (faceted)",
    x = NULL, y = NULL
  ) +
  theme_xs +
  theme(
    axis.text.x = element_text(angle = 55, hjust = 1, size = 6),
    axis.text.y = element_text(size = 7),
    strip.text  = element_text(face = "bold", size = 10)
  )
save_plot(p3, "issue2_ecosystem_gear_pressure_3way", w = 20, h = 14)

cat("\n============================================================\n")
cat("All extra cross-schema plots generated!\n")
cat("============================================================\n")
