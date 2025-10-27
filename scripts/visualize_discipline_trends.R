#!/usr/bin/env Rscript
# ============================================================================
# Discipline Trends Over Time Visualization
# ============================================================================
# Creates time series visualizations showing how shark science disciplines
# have grown from 1950-2025
#
# Input: outputs/analysis/discipline_trends_by_year.csv
# Output: Multiple figures in outputs/figures/
#
# Author: EEA 2025 Data Panel
# Date: 2025-10-26
# ============================================================================

# Load required packages
library(tidyverse)
library(scales)
library(viridis)
library(zoo)

# Set paths
input_file <- "outputs/analysis/discipline_trends_by_year.csv"
output_dir <- "outputs/figures"
dir.create(output_dir, showWarnings = FALSE, recursive = TRUE)

# ============================================================================
# 1. Load Data
# ============================================================================

cat("Loading discipline trends data...\n")
trends <- read_csv(input_file, show_col_types = FALSE)

cat(sprintf("Loaded %d rows spanning %d-%d\n",
    nrow(trends),
    min(trends$year),
    max(trends$year)))

# ============================================================================
# 2. Data Preparation
# ============================================================================

# Discipline metadata
discipline_info <- tibble(
  code = c("GEN", "DATA", "BIO", "FISH", "MOV", "TRO", "CON", "BEH"),
  full_name = c(
    "Genetics & Genomics",
    "Data Science",
    "Biology & Life History",
    "Fisheries & Stock Assessment",
    "Movement & Space Use",
    "Trophic & Community Ecology",
    "Conservation & Policy",
    "Behaviour & Sensory"
  ),
  color = c(
    "#A23B72",  # GEN - purple
    "#2E86AB",  # DATA - deep blue
    "#F18F01",  # BIO - orange
    "#C73E1D",  # FISH - red
    "#6A994E",  # MOV - green
    "#BC4B51",  # TRO - dark red
    "#8B7E74",  # CON - brown
    "#5E548E"   # BEH - purple-grey
  ),
  order = 1:8
)

# Add full names and colors to trends data
trends <- trends %>%
  left_join(discipline_info, by = c("discipline_code" = "code")) %>%
  mutate(full_name = fct_reorder(full_name, -order))

# Summarize by year and discipline (combine assignment types)
trends_summary <- trends %>%
  group_by(year, discipline_code, full_name, color, order) %>%
  summarise(
    papers = sum(paper_count),
    .groups = "drop"
  )

# ============================================================================
# 3. Main Time Series: All Disciplines
# ============================================================================

cat("\nCreating main time series visualization...\n")

p_timeseries <- trends_summary %>%
  ggplot(aes(x = year, y = papers, color = full_name, group = full_name)) +
  geom_line(size = 1.2, alpha = 0.8) +
  geom_point(size = 2, alpha = 0.6) +
  scale_color_manual(
    values = setNames(discipline_info$color, discipline_info$full_name),
    name = "Discipline"
  ) +
  scale_x_continuous(
    breaks = seq(1950, 2025, 10),
    limits = c(1950, 2025)
  ) +
  scale_y_continuous(
    labels = comma,
    expand = expansion(mult = c(0.02, 0.1))
  ) +
  labs(
    title = "Evolution of Shark Science Disciplines (1950-2025)",
    subtitle = "Number of papers by discipline over 75 years",
    x = "Year",
    y = "Number of Papers",
    caption = "Based on 9,503 papers with extracted analytical techniques"
  ) +
  theme_minimal(base_size = 13) +
  theme(
    plot.title = element_text(size = 18, face = "bold", hjust = 0.5),
    plot.subtitle = element_text(size = 12, hjust = 0.5, margin = margin(b = 15)),
    plot.caption = element_text(size = 9, hjust = 0, margin = margin(t = 10)),
    legend.position = "right",
    legend.title = element_text(face = "bold"),
    panel.grid.minor = element_blank(),
    axis.title = element_text(face = "bold"),
    plot.margin = margin(15, 15, 15, 15)
  )

ggsave(
  filename = file.path(output_dir, "discipline_trends_all.png"),
  plot = p_timeseries,
  width = 14,
  height = 8,
  dpi = 300
)

ggsave(
  filename = file.path(output_dir, "discipline_trends_all.pdf"),
  plot = p_timeseries,
  width = 14,
  height = 8
)

cat(sprintf("✅ Saved: %s\n", file.path(output_dir, "discipline_trends_all.png")))

# ============================================================================
# 4. Faceted View: Individual Discipline Trajectories
# ============================================================================

cat("\nCreating faceted discipline trajectories...\n")

p_facets <- trends_summary %>%
  ggplot(aes(x = year, y = papers)) +
  geom_area(aes(fill = full_name), alpha = 0.6) +
  geom_line(aes(color = full_name), size = 1) +
  facet_wrap(~ full_name, scales = "free_y", ncol = 2) +
  scale_fill_manual(
    values = setNames(discipline_info$color, discipline_info$full_name),
    guide = "none"
  ) +
  scale_color_manual(
    values = setNames(discipline_info$color, discipline_info$full_name),
    guide = "none"
  ) +
  scale_x_continuous(
    breaks = c(1960, 1990, 2020),
    limits = c(1950, 2025)
  ) +
  scale_y_continuous(labels = comma) +
  labs(
    title = "Individual Discipline Growth Trajectories (1950-2025)",
    subtitle = "Each panel shows one discipline's publication history",
    x = "Year",
    y = "Papers per Year",
    caption = "Note: Y-axes are independent to show each discipline's shape"
  ) +
  theme_minimal(base_size = 11) +
  theme(
    plot.title = element_text(size = 16, face = "bold", hjust = 0.5),
    plot.subtitle = element_text(size = 11, hjust = 0.5, margin = margin(b = 15)),
    strip.text = element_text(face = "bold", size = 10),
    panel.grid.minor = element_blank(),
    axis.title = element_text(face = "bold"),
    plot.margin = margin(15, 15, 15, 15)
  )

ggsave(
  filename = file.path(output_dir, "discipline_trends_faceted.png"),
  plot = p_facets,
  width = 12,
  height = 14,
  dpi = 300
)

ggsave(
  filename = file.path(output_dir, "discipline_trends_faceted.pdf"),
  plot = p_facets,
  width = 12,
  height = 14
)

cat(sprintf("✅ Saved: %s\n", file.path(output_dir, "discipline_trends_faceted.png")))

# ============================================================================
# 5. Stacked Area Chart: Relative Proportions
# ============================================================================

cat("\nCreating stacked area chart...\n")

p_stacked <- trends_summary %>%
  ggplot(aes(x = year, y = papers, fill = full_name)) +
  geom_area(alpha = 0.8, position = "stack") +
  scale_fill_manual(
    values = setNames(discipline_info$color, discipline_info$full_name),
    name = "Discipline"
  ) +
  scale_x_continuous(
    breaks = seq(1950, 2025, 10),
    limits = c(1950, 2025)
  ) +
  scale_y_continuous(
    labels = comma,
    expand = expansion(mult = c(0, 0.05))
  ) +
  labs(
    title = "Cumulative Growth of Shark Science Disciplines",
    subtitle = "Total papers per year across all disciplines (stacked)",
    x = "Year",
    y = "Total Papers",
    caption = "Note: Papers with multiple disciplines appear in each relevant layer"
  ) +
  theme_minimal(base_size = 13) +
  theme(
    plot.title = element_text(size = 18, face = "bold", hjust = 0.5),
    plot.subtitle = element_text(size = 12, hjust = 0.5, margin = margin(b = 15)),
    plot.caption = element_text(size = 9, hjust = 0, margin = margin(t = 10)),
    legend.position = "right",
    legend.title = element_text(face = "bold"),
    panel.grid.minor = element_blank(),
    axis.title = element_text(face = "bold"),
    plot.margin = margin(15, 15, 15, 15)
  )

ggsave(
  filename = file.path(output_dir, "discipline_trends_stacked.png"),
  plot = p_stacked,
  width = 14,
  height = 8,
  dpi = 300
)

ggsave(
  filename = file.path(output_dir, "discipline_trends_stacked.pdf"),
  plot = p_stacked,
  width = 14,
  height = 8
)

cat(sprintf("✅ Saved: %s\n", file.path(output_dir, "discipline_trends_stacked.png")))

# ============================================================================
# 6. Growth Rate Analysis: Pre-2000 vs Post-2010
# ============================================================================

cat("\nCalculating growth rates...\n")

# Calculate papers by era
era_growth <- trends_summary %>%
  mutate(era = case_when(
    year < 2000 ~ "Pre-2000",
    year >= 2010 ~ "Post-2010",
    TRUE ~ "2000-2009"
  )) %>%
  filter(era != "2000-2009") %>%
  group_by(era, discipline_code, full_name, color) %>%
  summarise(total_papers = sum(papers), .groups = "drop") %>%
  pivot_wider(names_from = era, values_from = total_papers, values_fill = 0) %>%
  mutate(
    growth_multiple = `Post-2010` / pmax(`Pre-2000`, 1),
    growth_percent = (growth_multiple - 1) * 100
  ) %>%
  arrange(desc(growth_multiple))

# Create growth rate comparison chart
p_growth <- era_growth %>%
  ggplot(aes(x = reorder(full_name, growth_multiple), y = growth_multiple, fill = full_name)) +
  geom_col(alpha = 0.8) +
  geom_text(
    aes(label = sprintf("%.1fx", growth_multiple)),
    hjust = -0.1,
    fontface = "bold",
    size = 4
  ) +
  scale_fill_manual(
    values = setNames(discipline_info$color, discipline_info$full_name),
    guide = "none"
  ) +
  scale_y_continuous(
    expand = expansion(mult = c(0, 0.15)),
    breaks = seq(0, 20, 2)
  ) +
  coord_flip() +
  labs(
    title = "Discipline Growth: Pre-2000 vs. Post-2010",
    subtitle = "How many times larger is each discipline in the modern era?",
    x = NULL,
    y = "Growth Multiple (Post-2010 / Pre-2000)",
    caption = "Pre-2000 = 1950-1999 | Post-2010 = 2010-2025"
  ) +
  theme_minimal(base_size = 13) +
  theme(
    plot.title = element_text(size = 18, face = "bold", hjust = 0.5),
    plot.subtitle = element_text(size = 12, hjust = 0.5, margin = margin(b = 15)),
    plot.caption = element_text(size = 9, hjust = 0.5, margin = margin(t = 10)),
    panel.grid.major.y = element_blank(),
    panel.grid.minor = element_blank(),
    axis.text.y = element_text(face = "bold", size = 11),
    axis.title = element_text(face = "bold"),
    plot.margin = margin(15, 15, 15, 15)
  )

ggsave(
  filename = file.path(output_dir, "discipline_growth_comparison.png"),
  plot = p_growth,
  width = 12,
  height = 8,
  dpi = 300
)

ggsave(
  filename = file.path(output_dir, "discipline_growth_comparison.pdf"),
  plot = p_growth,
  width = 12,
  height = 8
)

cat(sprintf("✅ Saved: %s\n", file.path(output_dir, "discipline_growth_comparison.png")))

# ============================================================================
# 7. Recent Trends: Focus on 2000-2025
# ============================================================================

cat("\nCreating recent trends visualization (2000-2025)...\n")

p_recent <- trends_summary %>%
  filter(year >= 2000) %>%
  ggplot(aes(x = year, y = papers, color = full_name, group = full_name)) +
  geom_line(size = 1.5, alpha = 0.8) +
  geom_point(size = 2.5, alpha = 0.7) +
  scale_color_manual(
    values = setNames(discipline_info$color, discipline_info$full_name),
    name = "Discipline"
  ) +
  scale_x_continuous(
    breaks = seq(2000, 2025, 5),
    limits = c(2000, 2025)
  ) +
  scale_y_continuous(
    labels = comma,
    expand = expansion(mult = c(0.02, 0.1))
  ) +
  labs(
    title = "Recent Trends in Shark Science Disciplines (2000-2025)",
    subtitle = "Showing the modern era of shark research",
    x = "Year",
    y = "Number of Papers",
    caption = "Genetics dominates but other disciplines also show steady growth"
  ) +
  theme_minimal(base_size = 13) +
  theme(
    plot.title = element_text(size = 18, face = "bold", hjust = 0.5),
    plot.subtitle = element_text(size = 12, hjust = 0.5, margin = margin(b = 15)),
    plot.caption = element_text(size = 9, hjust = 0, margin = margin(t = 10)),
    legend.position = "right",
    legend.title = element_text(face = "bold"),
    panel.grid.minor = element_blank(),
    axis.title = element_text(face = "bold"),
    plot.margin = margin(15, 15, 15, 15)
  )

ggsave(
  filename = file.path(output_dir, "discipline_trends_recent.png"),
  plot = p_recent,
  width = 14,
  height = 8,
  dpi = 300
)

ggsave(
  filename = file.path(output_dir, "discipline_trends_recent.pdf"),
  plot = p_recent,
  width = 14,
  height = 8
)

cat(sprintf("✅ Saved: %s\n", file.path(output_dir, "discipline_trends_recent.png")))

# ============================================================================
# 8. Anomaly Plot: Discipline-Specific Deviations from Overall Mean
# ============================================================================

cat("\nCreating discipline anomaly plot (faceted)...\n")

# Calculate total papers per year across all disciplines
total_by_year <- trends_summary %>%
  group_by(year) %>%
  summarise(total_papers = sum(papers), .groups = "drop")

# Calculate proportion of each discipline per year
discipline_proportions <- trends_summary %>%
  left_join(total_by_year, by = "year") %>%
  mutate(proportion = papers / total_papers)

# Calculate mean proportion for each discipline across all years
mean_proportions <- discipline_proportions %>%
  group_by(discipline_code, full_name, color) %>%
  summarise(mean_prop = mean(proportion), .groups = "drop")

# Calculate anomaly (deviation from mean proportion)
anomalies <- discipline_proportions %>%
  left_join(mean_proportions, by = c("discipline_code", "full_name", "color")) %>%
  mutate(anomaly = (proportion - mean_prop) * 100)  # Convert to percentage points

# Calculate 5-year rolling average for smoother
anomalies_smooth <- anomalies %>%
  arrange(discipline_code, year) %>%
  group_by(discipline_code, full_name, color) %>%
  mutate(
    anomaly_smooth = zoo::rollmean(anomaly, k = 5, fill = NA, align = "center")
  ) %>%
  ungroup()

# Create faceted anomaly plot
p_anomaly <- anomalies_smooth %>%
  ggplot(aes(x = year, y = anomaly)) +
  geom_hline(yintercept = 0, linetype = "dashed", color = "grey50", size = 0.5) +
  geom_line(aes(color = full_name), size = 1, alpha = 0.4) +
  geom_line(aes(y = anomaly_smooth, color = full_name), size = 0.7, linetype = "11", alpha = 0.9) +
  geom_point(aes(color = full_name), size = 1.5, alpha = 0.6) +
  facet_wrap(~ full_name, scales = "free_y", ncol = 2) +
  scale_color_manual(
    values = setNames(discipline_info$color, discipline_info$full_name),
    guide = "none"
  ) +
  scale_x_continuous(
    breaks = c(1960, 1990, 2020),
    limits = c(1950, 2025)
  ) +
  labs(
    title = "Discipline-Specific Deviations from Overall Research Trends",
    subtitle = "Anomaly = % of papers in discipline minus long-term average (shows relative growth/decline)",
    x = "Year",
    y = "Deviation from Mean (%)",
    caption = "Solid line = annual data | Dashed line = 5-year rolling average\nPositive = growing faster than average | Negative = declining relative to average | Y-axes independent"
  ) +
  theme_minimal(base_size = 11) +
  theme(
    plot.title = element_text(size = 16, face = "bold", hjust = 0.5),
    plot.subtitle = element_text(size = 10, hjust = 0.5, margin = margin(b = 15)),
    plot.caption = element_text(size = 8, hjust = 0.5, margin = margin(t = 10)),
    strip.text = element_text(face = "bold", size = 10),
    panel.grid.minor = element_blank(),
    axis.title = element_text(face = "bold")
  )

ggsave(
  filename = file.path(output_dir, "discipline_trends_anomaly.png"),
  plot = p_anomaly,
  width = 12,
  height = 14,
  dpi = 300
)

ggsave(
  filename = file.path(output_dir, "discipline_trends_anomaly.pdf"),
  plot = p_anomaly,
  width = 12,
  height = 14
)

cat(sprintf("✅ Saved: %s\n", file.path(output_dir, "discipline_trends_anomaly.png")))

# ============================================================================
# 9. Summary Statistics Table
# ============================================================================

cat(paste0("\n", strrep("=", 70), "\n"))
cat("DISCIPLINE TRENDS SUMMARY\n")
cat(paste0(strrep("=", 70), "\n\n"))

# Total papers by discipline (all years)
totals <- trends_summary %>%
  group_by(full_name) %>%
  summarise(total = sum(papers)) %>%
  arrange(desc(total))

cat("Total papers by discipline (1950-2025):\n")
for (i in 1:nrow(totals)) {
  cat(sprintf("  %d. %-35s %6s papers\n",
              i, totals$full_name[i], comma(totals$total[i])))
}

cat("\nGrowth analysis (Pre-2000 vs Post-2010):\n")
for (i in 1:nrow(era_growth)) {
  cat(sprintf("  %-35s  %.1fx growth\n",
              era_growth$full_name[i], era_growth$growth_multiple[i]))
}

# Calculate recent growth (2020-2025 vs 2015-2019)
recent_growth <- trends_summary %>%
  mutate(period = case_when(
    year >= 2020 ~ "2020-2025",
    year >= 2015 ~ "2015-2019",
    TRUE ~ "Earlier"
  )) %>%
  filter(period != "Earlier") %>%
  group_by(period, full_name) %>%
  summarise(avg_papers_per_year = mean(papers), .groups = "drop") %>%
  pivot_wider(names_from = period, values_from = avg_papers_per_year) %>%
  mutate(recent_change_pct = (`2020-2025` - `2015-2019`) / `2015-2019` * 100) %>%
  arrange(desc(recent_change_pct))

cat("\nRecent 5-year trend (2020-2025 vs 2015-2019):\n")
for (i in 1:nrow(recent_growth)) {
  direction <- ifelse(recent_growth$recent_change_pct[i] > 0, "↑", "↓")
  cat(sprintf("  %-35s  %s %+.1f%%\n",
              recent_growth$full_name[i],
              direction,
              recent_growth$recent_change_pct[i]))
}

cat(paste0("\n", strrep("=", 70), "\n"))
cat("All visualizations saved to: outputs/figures/\n")
cat(paste0(strrep("=", 70), "\n"))
