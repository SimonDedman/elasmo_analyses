#!/usr/bin/env Rscript
# ============================================================================
# visualize_issue4_open_access.R
#
# Issue #4: Open source / Open access metric
# Visualises OA rates over time, by journal, and by OA type.
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

output_dir <- "outputs/figures"
dir.create(output_dir, showWarnings = FALSE, recursive = TRUE)

theme_oa <- theme_minimal(base_size = 13) +
  theme(
    plot.title       = element_text(face = "bold", size = 15, hjust = 0),
    plot.subtitle    = element_text(colour = "grey40", size = 11, hjust = 0),
    panel.background = element_rect(fill = "white", colour = NA),
    plot.background  = element_rect(fill = "white", colour = NA),
    panel.grid.major = element_line(colour = "grey92"),
    panel.grid.minor = element_blank(),
    legend.position  = "right",
    axis.text        = element_text(colour = "grey30"),
    axis.title       = element_text(colour = "grey20")
  )

save_plot <- function(p, name, w = 12, h = 8) {
  ggsave(file.path(output_dir, paste0(name, ".png")), p, width = w, height = h,
         dpi = 300, bg = "white")
  ggsave(file.path(output_dir, paste0(name, ".pdf")), p, width = w, height = h,
         bg = "white")
  cat(sprintf("  Saved: %s (.png + .pdf)\n", name))
}

# ============================================================================
# 1. LOAD DATA
# ============================================================================

cat("Loading OA data...\n")
oa_year <- read_csv("outputs/analysis/oa_by_year.csv", show_col_types = FALSE)
oa_summary <- read_csv("outputs/analysis/oa_summary_statistics.csv",
                        show_col_types = FALSE)

# Also load the Unpaywall per-DOI data for type breakdown
oa_doi <- read_csv("outputs/unpaywall_oa_by_doi.csv", show_col_types = FALSE)
cat(sprintf("  OA by year: %d rows\n  OA by DOI: %d rows\n",
            nrow(oa_year), nrow(oa_doi)))

# ============================================================================
# 2. OA RATE OVER TIME (dual axis: count + percentage)
# ============================================================================

cat("\n=== Plot 1: OA rate over time ===\n")

oa_time <- oa_year |>
  filter(year >= 1990, year <= 2025)

p1 <- ggplot(oa_time, aes(x = year)) +
  geom_col(aes(y = total), fill = "grey80", width = 0.8) +
  geom_col(aes(y = oa_count), fill = "#27ae60", alpha = 0.8, width = 0.8) +
  geom_line(aes(y = oa_pct * max(total) / 100), colour = "#e74c3c",
            linewidth = 1.2) +
  geom_point(aes(y = oa_pct * max(total) / 100), colour = "#e74c3c", size = 1.5) +
  scale_y_continuous(
    name = "Number of Papers",
    labels = comma,
    sec.axis = sec_axis(~ . / max(oa_time$total) * 100,
                        name = "Open Access Rate (%)",
                        labels = function(x) paste0(round(x), "%"))
  ) +
  scale_x_continuous(breaks = seq(1990, 2025, 5)) +
  labs(
    title    = "Open Access in Elasmobranch Research",
    subtitle = "Grey = total papers; green = open access; red line = OA percentage",
    x = "Year"
  ) +
  theme_oa +
  theme(axis.title.y.right = element_text(colour = "#e74c3c"))
save_plot(p1, "issue4_oa_rate_over_time", w = 14, h = 8)

# ============================================================================
# 3. OA TYPE BREAKDOWN (stacked bar)
# ============================================================================

cat("\n=== Plot 2: OA type breakdown ===\n")

# Extract OA type from Unpaywall data
if ("oa_status" %in% names(oa_doi)) {
  oa_type_col <- "oa_status"
} else if ("oa_color" %in% names(oa_doi)) {
  oa_type_col <- "oa_color"
} else {
  # Find the right column
  cat("  Available columns: ", paste(names(oa_doi), collapse = ", "), "\n")
  oa_type_col <- NULL
}

if (!is.null(oa_type_col)) {
  # The unpaywall CSV already has year and oa_status columns
  oa_typed <- oa_doi |>
    filter(!is.na(year), year >= 1990, year <= 2025) |>
    mutate(oa_type = .data[[oa_type_col]])

  oa_type_colours <- c(
    gold   = "#f1c40f",
    green  = "#27ae60",
    hybrid = "#3498db",
    bronze = "#e67e22",
    closed = "#95a5a6"
  )

  oa_type_year <- oa_typed |>
    count(year, oa_type) |>
    mutate(oa_type = factor(oa_type,
      levels = c("gold", "hybrid", "green", "bronze", "closed")))

  p2 <- oa_type_year |>
    ggplot(aes(x = year, y = n, fill = oa_type)) +
    geom_area(alpha = 0.85, colour = "white", linewidth = 0.3) +
    scale_fill_manual(values = oa_type_colours, name = "OA Type",
                      labels = str_to_title) +
    scale_x_continuous(breaks = seq(1990, 2025, 5)) +
    labs(
      title    = "Open Access Types Over Time",
      subtitle = "Stacked area by Unpaywall OA classification",
      x = "Year", y = "Number of Papers"
    ) +
    theme_oa
  save_plot(p2, "issue4_oa_type_stacked", w = 14, h = 8)

  # Proportional version
  p2b <- oa_type_year |>
    group_by(year) |>
    mutate(pct = n / sum(n) * 100) |>
    ggplot(aes(x = year, y = pct, fill = oa_type)) +
    geom_area(alpha = 0.85, colour = "white", linewidth = 0.3) +
    scale_fill_manual(values = oa_type_colours, name = "OA Type",
                      labels = str_to_title) +
    scale_x_continuous(breaks = seq(1990, 2025, 5)) +
    scale_y_continuous(labels = function(x) paste0(x, "%")) +
    labs(
      title    = "Proportional Open Access Types Over Time",
      subtitle = "Share of each OA type among papers with DOIs",
      x = "Year", y = "% of Papers"
    ) +
    theme_oa
  save_plot(p2b, "issue4_oa_type_proportional", w = 14, h = 8)

  # Donut chart: overall OA type split
  oa_totals <- oa_typed |>
    count(oa_type) |>
    mutate(
      pct    = n / sum(n) * 100,
      label  = paste0(str_to_title(oa_type), "\n", comma(n), " (", round(pct, 1), "%)"),
      oa_type = factor(oa_type, levels = c("gold", "hybrid", "green", "bronze", "closed"))
    )

  p2c <- oa_totals |>
    ggplot(aes(x = 2, y = n, fill = oa_type)) +
    geom_col(width = 1, colour = "white") +
    coord_polar(theta = "y") +
    xlim(0.5, 2.5) +
    scale_fill_manual(values = oa_type_colours, name = "OA Type") +
    geom_text(aes(label = label), position = position_stack(vjust = 0.5),
              size = 3.5) +
    labs(
      title    = "Overall Open Access Breakdown",
      subtitle = sprintf("From %s papers with DOIs checked via Unpaywall",
                         comma(nrow(oa_typed)))
    ) +
    theme_void(base_size = 13) +
    theme(
      plot.title    = element_text(face = "bold", size = 15, hjust = 0.5),
      plot.subtitle = element_text(colour = "grey40", size = 11, hjust = 0.5),
      plot.background = element_rect(fill = "white", colour = NA)
    )
  save_plot(p2c, "issue4_oa_donut", w = 10, h = 10)
} else {
  cat("  Skipping OA type plots (no oa_status column found)\n")
}

# ============================================================================
# 4. OA SUMMARY STATISTICS BAR
# ============================================================================

cat("\n=== Plot 3: OA summary stats ===\n")

key_stats <- tibble(
  metric = c("Total Papers", "Papers with DOI", "OA (with DOI)",
             "Gold OA", "Green OA", "Hybrid OA", "Bronze OA", "Closed"),
  value = c(30523, 16642, 6407, 3170, 869, 937, 1431, 9949),
  category = c("total", "total", "oa", "gold", "green", "hybrid", "bronze", "closed")
)

stat_colours <- c(
  total = "grey70", oa = "#27ae60", gold = "#f1c40f",
  green = "#27ae60", hybrid = "#3498db", bronze = "#e67e22", closed = "#95a5a6"
)

p3 <- key_stats |>
  mutate(metric = fct_inorder(metric)) |>
  ggplot(aes(x = fct_rev(metric), y = value, fill = category)) +
  geom_col(width = 0.7, show.legend = FALSE) +
  geom_text(aes(label = comma(value)), hjust = -0.1, size = 4) +
  coord_flip() +
  scale_fill_manual(values = stat_colours) +
  scale_y_continuous(labels = comma, expand = expansion(mult = c(0, 0.2))) +
  labs(
    title    = "Open Access Summary Statistics",
    subtitle = "Elasmobranch literature corpus: 30,523 papers",
    x = NULL, y = "Number of Papers"
  ) +
  theme_oa
save_plot(p3, "issue4_oa_summary_stats", w = 12, h = 7)

# ============================================================================
# 5. GOLD OA GROWTH OVER TIME
# ============================================================================

cat("\n=== Plot 4: Gold OA growth ===\n")

p4 <- oa_year |>
  filter(year >= 1990, year <= 2025) |>
  ggplot(aes(x = year)) +
  geom_col(aes(y = gold_count), fill = "#f1c40f", alpha = 0.8, width = 0.8) +
  geom_col(aes(y = oa_count - gold_count), fill = "#27ae60", alpha = 0.6, width = 0.8) +
  scale_x_continuous(breaks = seq(1990, 2025, 5)) +
  scale_y_continuous(labels = comma) +
  labs(
    title    = "Gold vs Other Open Access Over Time",
    subtitle = "Yellow = Gold OA (full journal OA); Green = other OA routes",
    x = "Year", y = "Number of OA Papers"
  ) +
  theme_oa
save_plot(p4, "issue4_gold_oa_growth", w = 14, h = 8)

cat("\n============================================================\n")
cat("All Issue #4 plots generated!\n")
cat("============================================================\n")
