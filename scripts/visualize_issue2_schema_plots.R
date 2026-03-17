#!/usr/bin/env Rscript
# ============================================================================
# visualize_issue2_schema_plots.R
#
# Issue #2: Searches -> map & lineplot outputs
# Generates cross-tabulation and temporal plots from enriched schema columns.
#
# Inputs:
#   - outputs/meeting_review/enriched_schema_for_plots.csv
#   - outputs/meeting_review/enriched_with_top30_techniques.csv
#   - outputs/meeting_review/enriched_with_top30_species.csv
#
# Outputs:
#   - outputs/figures/issue2_*.png and .pdf
#
# Style: ggplot2, theme_minimal, white background, clean titles
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

# Consistent theme for all plots
theme_issue2 <- theme_minimal(base_size = 13) +
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
    strip.text       = element_text(face = "bold", size = 11)
  )

save_plot <- function(p, name, w = 12, h = 8) {
  ggsave(file.path(output_dir, paste0(name, ".png")), p, width = w, height = h,
         dpi = 300, bg = "white")
  ggsave(file.path(output_dir, paste0(name, ".pdf")), p, width = w, height = h,
         bg = "white")
  cat(sprintf("  Saved: %s (.png + .pdf)\n", name))
}

# Pretty-print column names: remove prefix, replace _ with space, title case
pretty_name <- function(x) {
  x |>
    str_remove("^[a-z]+_") |>
    str_replace_all("_", " ") |>
    str_to_title() |>
    str_replace("Iuu", "IUU") |>
    str_replace("Cpue", "CPUE") |>
    str_replace("Brd", "BRD") |>
    str_replace("Mpa", "MPA") |>
    str_replace("Iucn", "IUCN") |>
    str_replace("Edna", "eDNA") |>
    str_replace("Mit ", "Mitigation: ")
}

# ============================================================================
# 1. LOAD DATA
# ============================================================================

cat("Loading data...\n")
df <- read_csv(file.path(input_dir, "enriched_schema_for_plots.csv"),
               show_col_types = FALSE)
df_tech <- read_csv(file.path(input_dir, "enriched_with_top30_techniques.csv"),
                    show_col_types = FALSE)
df_sp <- read_csv(file.path(input_dir, "enriched_with_top30_species.csv"),
                  show_col_types = FALSE)
cat(sprintf("  Loaded %d papers, year range %d-%d\n",
            nrow(df), min(df$year, na.rm = TRUE), max(df$year, na.rm = TRUE)))

# Define column groups
d_cols    <- names(df)[str_starts(names(df), "d_")]
eco_cols  <- names(df)[str_starts(names(df), "eco_")]
pr_cols   <- names(df)[str_starts(names(df), "pr_")]
gear_cols <- names(df)[str_starts(names(df), "gear_") & names(df) != "gear_target_species"]
imp_cols  <- names(df)[str_starts(names(df), "imp_") & !names(df) %in% c("imp_growth")]
b_cols    <- names(df)[str_starts(names(df), "b_")]
a_cols    <- names(df_tech)[str_starts(names(df_tech), "a_")]

# ============================================================================
# 2. ECOSYSTEM COMPOSITION OVER TIME (stacked area)
# ============================================================================

cat("\n=== Plot 2: Ecosystem composition over time ===\n")

eco_by_year <- df |>
  filter(!is.na(year), year >= 1970) |>
  group_by(year) |>
  summarise(across(all_of(eco_cols), ~ sum(.x == 1, na.rm = TRUE)), .groups = "drop") |>
  pivot_longer(cols = all_of(eco_cols), names_to = "ecosystem", values_to = "n") |>
  mutate(ecosystem_label = pretty_name(ecosystem))

# Top 10 ecosystems for readability
top_eco <- eco_by_year |>
  group_by(ecosystem) |>
  summarise(total = sum(n)) |>
  slice_max(total, n = 10) |>
  pull(ecosystem)

p2 <- eco_by_year |>
  filter(ecosystem %in% top_eco) |>
  mutate(ecosystem_label = fct_reorder(ecosystem_label, -n, .fun = sum)) |>
  ggplot(aes(x = year, y = n, fill = ecosystem_label)) +
  geom_area(alpha = 0.85, colour = "white", linewidth = 0.3) +
  scale_fill_viridis_d(option = "turbo", name = "Ecosystem") +
  scale_x_continuous(breaks = seq(1970, 2025, 5)) +
  labs(
    title    = "Ecosystem Focus in Elasmobranch Research Over Time",
    subtitle = "Top 10 ecosystem types by paper count (papers may tag multiple ecosystems)",
    x = "Year", y = "Number of Papers"
  ) +
  theme_issue2
save_plot(p2, "issue2_ecosystem_over_time", w = 14, h = 8)

# ============================================================================
# 3. PRESSURE EVOLUTION OVER TIME (line plots)
# ============================================================================

cat("\n=== Plot 3: Pressure focus evolution ===\n")

pr_by_year <- df |>
  filter(!is.na(year), year >= 1980) |>
  group_by(year) |>
  summarise(across(all_of(pr_cols), ~ sum(.x == 1, na.rm = TRUE)), .groups = "drop") |>
  pivot_longer(cols = all_of(pr_cols), names_to = "pressure", values_to = "n") |>
  mutate(pressure_label = pretty_name(pressure))

# Top 12 pressures
top_pr <- pr_by_year |>
  group_by(pressure) |>
  summarise(total = sum(n)) |>
  slice_max(total, n = 12) |>
  pull(pressure)

p3 <- pr_by_year |>
  filter(pressure %in% top_pr) |>
  mutate(pressure_label = fct_reorder(pressure_label, -n, .fun = sum)) |>
  ggplot(aes(x = year, y = n, colour = pressure_label)) +
  geom_line(linewidth = 1, alpha = 0.8) +
  geom_point(size = 0.8, alpha = 0.5) +
  scale_colour_viridis_d(option = "turbo", name = "Pressure") +
  scale_x_continuous(breaks = seq(1980, 2025, 5)) +
  labs(
    title    = "Evolution of Research on Pressures and Threats",
    subtitle = "Top 12 pressure categories, annual paper counts",
    x = "Year", y = "Number of Papers"
  ) +
  theme_issue2
save_plot(p3, "issue2_pressure_evolution", w = 14, h = 8)

# Also faceted version for clarity
p3b <- pr_by_year |>
  filter(pressure %in% top_pr) |>
  mutate(pressure_label = fct_reorder(pressure_label, -n, .fun = sum)) |>
  ggplot(aes(x = year, y = n)) +
  geom_line(colour = "#e74c3c", linewidth = 0.7) +
  geom_smooth(method = "loess", se = FALSE, colour = "#2c3e50", linewidth = 0.5,
              linetype = "dashed", span = 0.4) +
  facet_wrap(~ pressure_label, scales = "free_y", ncol = 4) +
  scale_x_continuous(breaks = seq(1980, 2025, 15)) +
  labs(
    title    = "Research Trends per Pressure Type",
    subtitle = "Dashed line = LOESS trend; free y-axis per panel",
    x = "Year", y = "Papers"
  ) +
  theme_issue2 +
  theme(strip.text = element_text(size = 9))
save_plot(p3b, "issue2_pressure_evolution_faceted", w = 14, h = 10)

# ============================================================================
# 4. IMPACT MEASUREMENT TRENDS OVER TIME
# ============================================================================

cat("\n=== Plot 4: Impact measurement trends ===\n")

imp_by_year <- df |>
  filter(!is.na(year), year >= 1980) |>
  group_by(year) |>
  summarise(across(all_of(imp_cols), ~ sum(.x == 1, na.rm = TRUE)), .groups = "drop") |>
  pivot_longer(cols = all_of(imp_cols), names_to = "impact", values_to = "n") |>
  mutate(impact_label = pretty_name(impact))

top_imp <- imp_by_year |>
  group_by(impact) |>
  summarise(total = sum(n)) |>
  filter(total > 50) |>
  slice_max(total, n = 12) |>
  pull(impact)

p4 <- imp_by_year |>
  filter(impact %in% top_imp) |>
  mutate(impact_label = fct_reorder(impact_label, -n, .fun = sum)) |>
  ggplot(aes(x = year, y = n)) +
  geom_line(colour = "#3498db", linewidth = 0.7) +
  geom_smooth(method = "loess", se = FALSE, colour = "#2c3e50", linewidth = 0.5,
              linetype = "dashed", span = 0.4) +
  facet_wrap(~ impact_label, scales = "free_y", ncol = 4) +
  scale_x_continuous(breaks = seq(1980, 2025, 15)) +
  labs(
    title    = "Trends in Impact/Response Variables Measured",
    subtitle = "How has the focus on different response metrics changed over time?",
    x = "Year", y = "Papers"
  ) +
  theme_issue2 +
  theme(strip.text = element_text(size = 9))
save_plot(p4, "issue2_impact_trends_faceted", w = 14, h = 10)

# ============================================================================
# 5. TECHNIQUE x ECOSYSTEM HEATMAP
# ============================================================================

cat("\n=== Plot 5: Technique x Ecosystem heatmap ===\n")

top_a <- a_cols[1:min(25, length(a_cols))]  # top 25 techniques (pre-sorted)

# Build co-occurrence matrix
tech_eco_mat <- map_dfr(top_a, function(tech) {
  map_dfr(eco_cols, function(eco) {
    tibble(
      technique = tech,
      ecosystem = eco,
      n = sum(df_tech[[tech]] == 1 & df[[eco]] == 1, na.rm = TRUE)
    )
  })
}) |>
  mutate(
    technique_label = pretty_name(technique),
    ecosystem_label = pretty_name(ecosystem)
  )

# Order by total count
tech_order <- tech_eco_mat |>
  group_by(technique_label) |>
  summarise(total = sum(n)) |>
  arrange(total) |>
  pull(technique_label)

eco_order <- tech_eco_mat |>
  group_by(ecosystem_label) |>
  summarise(total = sum(n)) |>
  arrange(desc(total)) |>
  pull(ecosystem_label)

p5 <- tech_eco_mat |>
  mutate(
    technique_label = factor(technique_label, levels = tech_order),
    ecosystem_label = factor(ecosystem_label, levels = eco_order)
  ) |>
  ggplot(aes(x = ecosystem_label, y = technique_label, fill = n)) +
  geom_tile(colour = "white", linewidth = 0.3) +
  geom_text(aes(label = ifelse(n > 0, n, "")), size = 2.5, colour = "grey20") +
  scale_fill_viridis_c(option = "mako", direction = -1, name = "Papers",
                       trans = "sqrt") +
  labs(
    title    = "Technique x Ecosystem Co-occurrence",
    subtitle = "Top 25 techniques; count of papers tagging both",
    x = NULL, y = NULL
  ) +
  theme_issue2 +
  theme(
    axis.text.x = element_text(angle = 45, hjust = 1, size = 9),
    axis.text.y = element_text(size = 8)
  )
save_plot(p5, "issue2_technique_ecosystem_heatmap", w = 16, h = 12)

# ============================================================================
# 6. TECHNIQUE x PRESSURE HEATMAP
# ============================================================================

cat("\n=== Plot 6: Technique x Pressure heatmap ===\n")

tech_pr_mat <- map_dfr(top_a, function(tech) {
  map_dfr(pr_cols, function(pr) {
    tibble(
      technique = tech,
      pressure  = pr,
      n = sum(df_tech[[tech]] == 1 & df[[pr]] == 1, na.rm = TRUE)
    )
  })
}) |>
  mutate(
    technique_label = pretty_name(technique),
    pressure_label  = pretty_name(pressure)
  )

tech_order_pr <- tech_pr_mat |>
  group_by(technique_label) |> summarise(total = sum(n)) |>
  arrange(total) |> pull(technique_label)

pr_order <- tech_pr_mat |>
  group_by(pressure_label) |> summarise(total = sum(n)) |>
  arrange(desc(total)) |> pull(pressure_label)

p6 <- tech_pr_mat |>
  mutate(
    technique_label = factor(technique_label, levels = tech_order_pr),
    pressure_label  = factor(pressure_label, levels = pr_order)
  ) |>
  ggplot(aes(x = pressure_label, y = technique_label, fill = n)) +
  geom_tile(colour = "white", linewidth = 0.3) +
  geom_text(aes(label = ifelse(n > 0, n, "")), size = 2.5, colour = "grey20") +
  scale_fill_viridis_c(option = "rocket", direction = -1, name = "Papers",
                       trans = "sqrt") +
  labs(
    title    = "Technique x Pressure Co-occurrence",
    subtitle = "Top 25 techniques vs. all pressure categories",
    x = NULL, y = NULL
  ) +
  theme_issue2 +
  theme(
    axis.text.x = element_text(angle = 45, hjust = 1, size = 9),
    axis.text.y = element_text(size = 8)
  )
save_plot(p6, "issue2_technique_pressure_heatmap", w = 16, h = 12)

# ============================================================================
# 7. TECHNIQUE x GEAR HEATMAP
# ============================================================================

cat("\n=== Plot 7: Technique x Gear heatmap ===\n")

tech_gear_mat <- map_dfr(top_a, function(tech) {
  map_dfr(gear_cols, function(gr) {
    tibble(
      technique = tech,
      gear      = gr,
      n = sum(df_tech[[tech]] == 1 & df[[gr]] == 1, na.rm = TRUE)
    )
  })
}) |>
  mutate(
    technique_label = pretty_name(technique),
    gear_label      = pretty_name(gear)
  )

tech_order_gear <- tech_gear_mat |>
  group_by(technique_label) |> summarise(total = sum(n)) |>
  arrange(total) |> pull(technique_label)

gear_order <- tech_gear_mat |>
  group_by(gear_label) |> summarise(total = sum(n)) |>
  arrange(desc(total)) |> pull(gear_label)

p7 <- tech_gear_mat |>
  mutate(
    technique_label = factor(technique_label, levels = tech_order_gear),
    gear_label      = factor(gear_label, levels = gear_order)
  ) |>
  ggplot(aes(x = gear_label, y = technique_label, fill = n)) +
  geom_tile(colour = "white", linewidth = 0.3) +
  geom_text(aes(label = ifelse(n > 0, n, "")), size = 2.8, colour = "grey20") +
  scale_fill_viridis_c(option = "cividis", direction = -1, name = "Papers",
                       trans = "sqrt") +
  labs(
    title    = "Technique x Fishing Gear Co-occurrence",
    subtitle = "Top 25 techniques vs. gear types (excl. target_species)",
    x = NULL, y = NULL
  ) +
  theme_issue2 +
  theme(
    axis.text.x = element_text(angle = 45, hjust = 1, size = 9),
    axis.text.y = element_text(size = 8)
  )
save_plot(p7, "issue2_technique_gear_heatmap", w = 14, h = 12)

# ============================================================================
# 8. GEAR x PRESSURE CO-OCCURRENCE HEATMAP
# ============================================================================

cat("\n=== Plot 8: Gear x Pressure co-occurrence ===\n")

gear_pr_mat <- map_dfr(gear_cols, function(gr) {
  map_dfr(pr_cols, function(pr) {
    tibble(
      gear     = gr,
      pressure = pr,
      n = sum(df[[gr]] == 1 & df[[pr]] == 1, na.rm = TRUE)
    )
  })
}) |>
  mutate(
    gear_label     = pretty_name(gear),
    pressure_label = pretty_name(pressure)
  )

gear_order2 <- gear_pr_mat |>
  group_by(gear_label) |> summarise(total = sum(n)) |>
  arrange(total) |> pull(gear_label)

pr_order2 <- gear_pr_mat |>
  group_by(pressure_label) |> summarise(total = sum(n)) |>
  arrange(desc(total)) |> pull(pressure_label)

p8 <- gear_pr_mat |>
  mutate(
    gear_label     = factor(gear_label, levels = gear_order2),
    pressure_label = factor(pressure_label, levels = pr_order2)
  ) |>
  ggplot(aes(x = pressure_label, y = gear_label, fill = n)) +
  geom_tile(colour = "white", linewidth = 0.5) +
  geom_text(aes(label = ifelse(n > 0, n, "")), size = 3, colour = "grey20") +
  scale_fill_viridis_c(option = "inferno", direction = -1, name = "Papers",
                       trans = "sqrt") +
  labs(
    title    = "Fishing Gear x Pressure Co-occurrence",
    subtitle = "How often do gear types co-occur with different pressures?",
    x = NULL, y = NULL
  ) +
  theme_issue2 +
  theme(
    axis.text.x = element_text(angle = 45, hjust = 1, size = 10),
    axis.text.y = element_text(size = 10)
  )
save_plot(p8, "issue2_gear_pressure_heatmap", w = 14, h = 9)

# ============================================================================
# 9. OCEAN BASIN x DISCIPLINE HEATMAP
# ============================================================================

cat("\n=== Plot 9: Ocean basin x Discipline heatmap ===\n")

basin_disc_mat <- map_dfr(b_cols, function(b) {
  map_dfr(d_cols, function(d) {
    tibble(
      basin      = b,
      discipline = d,
      n = sum(df[[b]] == 1 & df[[d]] == 1, na.rm = TRUE)
    )
  })
}) |>
  mutate(
    basin_label      = pretty_name(basin),
    discipline_label = pretty_name(discipline)
  )

basin_order <- basin_disc_mat |>
  group_by(basin_label) |> summarise(total = sum(n)) |>
  arrange(desc(total)) |> pull(basin_label)

disc_order <- basin_disc_mat |>
  group_by(discipline_label) |> summarise(total = sum(n)) |>
  arrange(total) |> pull(discipline_label)

p9 <- basin_disc_mat |>
  mutate(
    basin_label      = factor(basin_label, levels = basin_order),
    discipline_label = factor(discipline_label, levels = disc_order)
  ) |>
  ggplot(aes(x = basin_label, y = discipline_label, fill = n)) +
  geom_tile(colour = "white", linewidth = 0.5) +
  geom_text(aes(label = comma(n)), size = 3.2, colour = "grey20") +
  scale_fill_viridis_c(option = "mako", direction = -1, name = "Papers") +
  labs(
    title    = "Research by Ocean Basin and Discipline",
    subtitle = "Co-occurrence counts (papers may span multiple basins and disciplines)",
    x = NULL, y = NULL
  ) +
  theme_issue2 +
  theme(axis.text.x = element_text(angle = 30, hjust = 1, size = 11))
save_plot(p9, "issue2_basin_discipline_heatmap", w = 12, h = 10)

# ============================================================================
# 10. PRESSURE x IMPACT CO-OCCURRENCE MATRIX
# ============================================================================

cat("\n=== Plot 10: Pressure x Impact co-occurrence ===\n")

pr_imp_mat <- map_dfr(pr_cols, function(pr) {
  map_dfr(imp_cols, function(imp) {
    tibble(
      pressure = pr,
      impact   = imp,
      n = sum(df[[pr]] == 1 & df[[imp]] == 1, na.rm = TRUE)
    )
  })
}) |>
  mutate(
    pressure_label = pretty_name(pressure),
    impact_label   = pretty_name(impact)
  )

pr_order3 <- pr_imp_mat |>
  group_by(pressure_label) |> summarise(total = sum(n)) |>
  arrange(total) |> pull(pressure_label)

imp_order <- pr_imp_mat |>
  group_by(impact_label) |> summarise(total = sum(n)) |>
  arrange(desc(total)) |> pull(impact_label)

p10 <- pr_imp_mat |>
  mutate(
    pressure_label = factor(pressure_label, levels = pr_order3),
    impact_label   = factor(impact_label, levels = imp_order)
  ) |>
  ggplot(aes(x = impact_label, y = pressure_label, fill = n)) +
  geom_tile(colour = "white", linewidth = 0.3) +
  geom_text(aes(label = ifelse(n > 0, n, "")), size = 2.5, colour = "grey20") +
  scale_fill_viridis_c(option = "rocket", direction = -1, name = "Papers",
                       trans = "sqrt") +
  labs(
    title    = "Pressure x Impact Co-occurrence",
    subtitle = "Which pressures are studied with which response variables?",
    x = NULL, y = NULL
  ) +
  theme_issue2 +
  theme(
    axis.text.x = element_text(angle = 45, hjust = 1, size = 9),
    axis.text.y = element_text(size = 9)
  )
save_plot(p10, "issue2_pressure_impact_heatmap", w = 14, h = 12)

# ============================================================================
# 11. DISCIPLINE x ECOSYSTEM HEATMAP
# ============================================================================

cat("\n=== Plot 11: Discipline x Ecosystem heatmap ===\n")

disc_eco_mat <- map_dfr(d_cols, function(d) {
  map_dfr(eco_cols, function(eco) {
    tibble(
      discipline = d,
      ecosystem  = eco,
      n = sum(df[[d]] == 1 & df[[eco]] == 1, na.rm = TRUE)
    )
  })
}) |>
  mutate(
    discipline_label = pretty_name(discipline),
    ecosystem_label  = pretty_name(ecosystem)
  )

disc_order2 <- disc_eco_mat |>
  group_by(discipline_label) |> summarise(total = sum(n)) |>
  arrange(total) |> pull(discipline_label)

eco_order2 <- disc_eco_mat |>
  group_by(ecosystem_label) |> summarise(total = sum(n)) |>
  arrange(desc(total)) |> pull(ecosystem_label)

p11 <- disc_eco_mat |>
  mutate(
    discipline_label = factor(discipline_label, levels = disc_order2),
    ecosystem_label  = factor(ecosystem_label, levels = eco_order2)
  ) |>
  ggplot(aes(x = ecosystem_label, y = discipline_label, fill = n)) +
  geom_tile(colour = "white", linewidth = 0.3) +
  geom_text(aes(label = ifelse(n > 0, comma(n), "")), size = 2.5, colour = "grey20") +
  scale_fill_viridis_c(option = "mako", direction = -1, name = "Papers",
                       trans = "sqrt") +
  labs(
    title    = "Discipline x Ecosystem Co-occurrence",
    subtitle = "Research effort by discipline and habitat type",
    x = NULL, y = NULL
  ) +
  theme_issue2 +
  theme(
    axis.text.x = element_text(angle = 45, hjust = 1, size = 9),
    axis.text.y = element_text(size = 9)
  )
save_plot(p11, "issue2_discipline_ecosystem_heatmap", w = 15, h = 10)

# ============================================================================
# 12. GEAR x IMPACT HEATMAP
# ============================================================================

cat("\n=== Plot 12: Gear x Impact heatmap ===\n")

gear_imp_mat <- map_dfr(gear_cols, function(gr) {
  map_dfr(imp_cols, function(imp) {
    tibble(
      gear   = gr,
      impact = imp,
      n = sum(df[[gr]] == 1 & df[[imp]] == 1, na.rm = TRUE)
    )
  })
}) |>
  mutate(
    gear_label   = pretty_name(gear),
    impact_label = pretty_name(impact)
  )

gear_order3 <- gear_imp_mat |>
  group_by(gear_label) |> summarise(total = sum(n)) |>
  arrange(total) |> pull(gear_label)

imp_order2 <- gear_imp_mat |>
  group_by(impact_label) |> summarise(total = sum(n)) |>
  arrange(desc(total)) |> pull(impact_label)

p12 <- gear_imp_mat |>
  mutate(
    gear_label   = factor(gear_label, levels = gear_order3),
    impact_label = factor(impact_label, levels = imp_order2)
  ) |>
  ggplot(aes(x = impact_label, y = gear_label, fill = n)) +
  geom_tile(colour = "white", linewidth = 0.5) +
  geom_text(aes(label = ifelse(n > 0, n, "")), size = 3, colour = "grey20") +
  scale_fill_viridis_c(option = "cividis", direction = -1, name = "Papers",
                       trans = "sqrt") +
  labs(
    title    = "Fishing Gear x Impact Response Co-occurrence",
    subtitle = "Which gear studies measure which response variables?",
    x = NULL, y = NULL
  ) +
  theme_issue2 +
  theme(
    axis.text.x = element_text(angle = 45, hjust = 1, size = 10),
    axis.text.y = element_text(size = 10)
  )
save_plot(p12, "issue2_gear_impact_heatmap", w = 14, h = 9)

# ============================================================================
# 13. SPECIES x ECOSYSTEM (top 20 species)
# ============================================================================

cat("\n=== Plot 13: Species x Ecosystem ===\n")

sp_cols <- names(df_sp)[str_starts(names(df_sp), "sp_")]
eco_cols_sp <- names(df_sp)[str_starts(names(df_sp), "eco_")]

sp_eco_mat <- map_dfr(sp_cols[1:min(20, length(sp_cols))], function(sp) {
  map_dfr(eco_cols_sp, function(eco) {
    tibble(
      species   = sp,
      ecosystem = eco,
      n = sum(df_sp[[sp]] == 1 & df_sp[[eco]] == 1, na.rm = TRUE)
    )
  })
}) |>
  mutate(
    species_label = species |>
      str_remove("^sp_") |>
      str_replace_all("_", " ") |>
      str_to_sentence(),
    ecosystem_label = pretty_name(ecosystem)
  )

sp_order <- sp_eco_mat |>
  group_by(species_label) |> summarise(total = sum(n)) |>
  arrange(total) |> pull(species_label)

eco_order3 <- sp_eco_mat |>
  group_by(ecosystem_label) |> summarise(total = sum(n)) |>
  arrange(desc(total)) |> pull(ecosystem_label)

p13 <- sp_eco_mat |>
  mutate(
    species_label   = factor(species_label, levels = sp_order),
    ecosystem_label = factor(ecosystem_label, levels = eco_order3)
  ) |>
  ggplot(aes(x = ecosystem_label, y = species_label, fill = n)) +
  geom_tile(colour = "white", linewidth = 0.3) +
  geom_text(aes(label = ifelse(n > 0, n, "")), size = 2.5, colour = "grey20") +
  scale_fill_viridis_c(option = "turbo", direction = -1, name = "Papers",
                       trans = "sqrt") +
  labs(
    title    = "Top 20 Species x Ecosystem Co-occurrence",
    subtitle = "Which species are studied in which habitats?",
    x = NULL, y = NULL
  ) +
  theme_issue2 +
  theme(
    axis.text.x = element_text(angle = 45, hjust = 1, size = 9),
    axis.text.y = element_text(face = "italic", size = 9)
  )
save_plot(p13, "issue2_species_ecosystem_heatmap", w = 15, h = 10)

# ============================================================================
# 14. TEMPORAL EMERGENCE: When did each schema column first appear?
# ============================================================================

cat("\n=== Plot 14: Temporal emergence of schema columns ===\n")

# For each column, find first year with >= 1 paper and total count
all_schema_cols <- c(eco_cols, pr_cols, gear_cols, imp_cols)
emergence <- map_dfr(all_schema_cols, function(col) {
  hits <- df |> filter(!is.na(year), .data[[col]] == 1)
  if (nrow(hits) == 0) return(NULL)
  tibble(
    column      = col,
    prefix      = str_extract(col, "^[a-z]+"),
    first_year  = min(hits$year, na.rm = TRUE),
    total       = nrow(hits),
    label       = pretty_name(col)
  )
})

prefix_labels <- c(
  eco  = "Ecosystem",
  pr   = "Pressure",
  gear = "Gear",
  imp  = "Impact"
)

p14 <- emergence |>
  mutate(
    category = prefix_labels[prefix],
    label    = fct_reorder(label, first_year)
  ) |>
  ggplot(aes(x = first_year, y = label, size = total, colour = category)) +
  geom_point(alpha = 0.7) +
  scale_size_continuous(range = c(2, 10), name = "Total Papers",
                        labels = comma) +
  scale_colour_brewer(palette = "Set1", name = "Category") +
  scale_x_continuous(breaks = seq(1950, 2025, 10)) +
  labs(
    title    = "First Appearance of Schema Categories in Literature",
    subtitle = "Point size = total paper count; x = earliest paper year",
    x = "First Year Detected", y = NULL
  ) +
  theme_issue2 +
  theme(axis.text.y = element_text(size = 7))
save_plot(p14, "issue2_schema_emergence_timeline", w = 14, h = 14)

# ============================================================================
# 15. ECOSYSTEM PROPORTIONS OVER TIME (normalised stacked area)
# ============================================================================

cat("\n=== Plot 15: Ecosystem proportions over time ===\n")

# 5-year bins for smoother visualisation
eco_prop <- df |>
  filter(!is.na(year), year >= 1970) |>
  mutate(decade = floor(year / 5) * 5) |>
  group_by(decade) |>
  summarise(across(all_of(eco_cols), ~ sum(.x == 1, na.rm = TRUE)), .groups = "drop") |>
  pivot_longer(cols = all_of(eco_cols), names_to = "ecosystem", values_to = "n") |>
  filter(ecosystem %in% top_eco) |>
  group_by(decade) |>
  mutate(pct = n / sum(n) * 100) |>
  ungroup() |>
  mutate(ecosystem_label = pretty_name(ecosystem))

p15 <- eco_prop |>
  mutate(ecosystem_label = fct_reorder(ecosystem_label, -pct, .fun = mean)) |>
  ggplot(aes(x = decade, y = pct, fill = ecosystem_label)) +
  geom_area(alpha = 0.85, colour = "white", linewidth = 0.3) +
  scale_fill_viridis_d(option = "turbo", name = "Ecosystem") +
  scale_x_continuous(breaks = seq(1970, 2025, 5)) +
  labs(
    title    = "Proportional Ecosystem Focus Over Time",
    subtitle = "Top 10 ecosystems, 5-year bins, normalised to 100%",
    x = "5-Year Period", y = "% of Ecosystem Tags"
  ) +
  theme_issue2
save_plot(p15, "issue2_ecosystem_proportions_over_time", w = 14, h = 8)

# ============================================================================
# 16. GEAR TYPES OVER TIME (stacked area)
# ============================================================================

cat("\n=== Plot 16: Gear types over time ===\n")

gear_by_year <- df |>
  filter(!is.na(year), year >= 1980) |>
  group_by(year) |>
  summarise(across(all_of(gear_cols), ~ sum(.x == 1, na.rm = TRUE)), .groups = "drop") |>
  pivot_longer(cols = all_of(gear_cols), names_to = "gear", values_to = "n") |>
  mutate(gear_label = pretty_name(gear))

p16 <- gear_by_year |>
  mutate(gear_label = fct_reorder(gear_label, -n, .fun = sum)) |>
  ggplot(aes(x = year, y = n, fill = gear_label)) +
  geom_area(alpha = 0.85, colour = "white", linewidth = 0.3) +
  scale_fill_viridis_d(option = "turbo", name = "Gear Type") +
  scale_x_continuous(breaks = seq(1980, 2025, 5)) +
  labs(
    title    = "Fishing Gear Research Over Time",
    subtitle = "All gear types (excl. target_species), stacked by year",
    x = "Year", y = "Number of Papers"
  ) +
  theme_issue2
save_plot(p16, "issue2_gear_over_time", w = 14, h = 8)

# ============================================================================
# 17. DISCIPLINE x PRESSURE HEATMAP
# ============================================================================

cat("\n=== Plot 17: Discipline x Pressure heatmap ===\n")

disc_pr_mat <- map_dfr(d_cols, function(d) {
  map_dfr(pr_cols, function(pr) {
    tibble(
      discipline = d,
      pressure   = pr,
      n = sum(df[[d]] == 1 & df[[pr]] == 1, na.rm = TRUE)
    )
  })
}) |>
  mutate(
    discipline_label = pretty_name(discipline),
    pressure_label   = pretty_name(pressure)
  )

disc_order3 <- disc_pr_mat |>
  group_by(discipline_label) |> summarise(total = sum(n)) |>
  arrange(total) |> pull(discipline_label)

pr_order4 <- disc_pr_mat |>
  group_by(pressure_label) |> summarise(total = sum(n)) |>
  arrange(desc(total)) |> pull(pressure_label)

p17 <- disc_pr_mat |>
  mutate(
    discipline_label = factor(discipline_label, levels = disc_order3),
    pressure_label   = factor(pressure_label, levels = pr_order4)
  ) |>
  ggplot(aes(x = pressure_label, y = discipline_label, fill = n)) +
  geom_tile(colour = "white", linewidth = 0.3) +
  geom_text(aes(label = ifelse(n > 0, comma(n), "")), size = 2.8, colour = "grey20") +
  scale_fill_viridis_c(option = "rocket", direction = -1, name = "Papers",
                       trans = "sqrt") +
  labs(
    title    = "Discipline x Pressure Co-occurrence",
    subtitle = "Which disciplines address which pressures?",
    x = NULL, y = NULL
  ) +
  theme_issue2 +
  theme(
    axis.text.x = element_text(angle = 45, hjust = 1, size = 9),
    axis.text.y = element_text(size = 10)
  )
save_plot(p17, "issue2_discipline_pressure_heatmap", w = 15, h = 10)

# ============================================================================
# 18. OCEAN BASIN RESEARCH OVER TIME (line plot)
# ============================================================================

cat("\n=== Plot 18: Ocean basin research over time ===\n")

basin_by_year <- df |>
  filter(!is.na(year), year >= 1980) |>
  group_by(year) |>
  summarise(across(all_of(b_cols), ~ sum(.x == 1, na.rm = TRUE)), .groups = "drop") |>
  pivot_longer(cols = all_of(b_cols), names_to = "basin", values_to = "n") |>
  mutate(basin_label = pretty_name(basin))

p18 <- basin_by_year |>
  mutate(basin_label = fct_reorder(basin_label, -n, .fun = sum)) |>
  ggplot(aes(x = year, y = n, colour = basin_label)) +
  geom_line(linewidth = 1, alpha = 0.8) +
  scale_colour_brewer(palette = "Set2", name = "Ocean Basin") +
  scale_x_continuous(breaks = seq(1980, 2025, 5)) +
  labs(
    title    = "Elasmobranch Research by Ocean Basin Over Time",
    subtitle = "Annual paper counts per basin",
    x = "Year", y = "Number of Papers"
  ) +
  theme_issue2
save_plot(p18, "issue2_basin_over_time", w = 14, h = 8)

# ============================================================================
# DONE
# ============================================================================

cat("\n============================================================\n")
cat("All Issue #2 plots generated successfully!\n")
cat("============================================================\n")
