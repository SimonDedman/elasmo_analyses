#!/usr/bin/env Rscript
# ============================================================================
# Technique Adoption Timeline Visualization
# ============================================================================
# Creates visualizations showing when techniques emerged and how they've
# been adopted over time in shark science
#
# Input: outputs/analysis/technique_trends_by_year.csv
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
input_file <- "outputs/analysis/technique_trends_by_year.csv"
top_techniques_file <- "outputs/analysis/top_techniques.csv"
output_dir <- "outputs/figures"
dir.create(output_dir, showWarnings = FALSE, recursive = TRUE)

# ============================================================================
# 1. Load Data
# ============================================================================

cat("Loading technique trends data...\n")
trends <- read_csv(input_file, show_col_types = FALSE)
top_tech <- read_csv(top_techniques_file, show_col_types = FALSE)

cat(sprintf("Loaded %d technique-year combinations\n", nrow(trends)))
cat(sprintf("Loaded %d unique techniques\n", nrow(top_tech)))

# ============================================================================
# 2. Discipline Metadata
# ============================================================================

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
  )
)

# Add colors to trends
trends <- trends %>%
  left_join(discipline_info, by = c("primary_discipline" = "code"))

# ============================================================================
# 3. Top 20 Techniques Over Time
# ============================================================================

cat("\nCreating Top 20 techniques timeline...\n")

# Get top 20 techniques by total papers
top_20 <- top_tech %>%
  arrange(desc(paper_count)) %>%
  head(20)

# Filter trends to top 20
trends_top20 <- trends %>%
  filter(technique_name %in% top_20$technique_name)

# Create line chart
p_top20 <- trends_top20 %>%
  ggplot(aes(x = year, y = paper_count, color = primary_discipline, group = technique_name)) +
  geom_line(size = 0.8, alpha = 0.7) +
  scale_color_manual(
    values = setNames(discipline_info$color, discipline_info$code),
    name = "Discipline",
    labels = setNames(discipline_info$full_name, discipline_info$code)
  ) +
  scale_x_continuous(
    breaks = seq(1950, 2025, 10),
    limits = c(1950, 2025)
  ) +
  scale_y_continuous(labels = comma) +
  facet_wrap(~ technique_name, scales = "free_y", ncol = 4) +
  labs(
    title = "Top 20 Techniques: Adoption Over Time",
    subtitle = "How the most popular shark science techniques emerged and grew (1950-2025)",
    x = "Year",
    y = "Papers per Year",
    caption = "Y-axes are independent to show each technique's trajectory | Color = primary discipline"
  ) +
  theme_minimal(base_size = 9) +
  theme(
    plot.title = element_text(size = 16, face = "bold", hjust = 0.5),
    plot.subtitle = element_text(size = 11, hjust = 0.5, margin = margin(b = 15)),
    plot.caption = element_text(size = 8, hjust = 0.5, margin = margin(t = 10)),
    strip.text = element_text(face = "bold", size = 8),
    legend.position = "bottom",
    legend.title = element_text(face = "bold", size = 9),
    legend.text = element_text(size = 8),
    panel.grid.minor = element_blank(),
    axis.title = element_text(face = "bold", size = 10),
    axis.text = element_text(size = 7)
  )

ggsave(
  filename = file.path(output_dir, "technique_top20_timelines.png"),
  plot = p_top20,
  width = 16,
  height = 12,
  dpi = 300
)

ggsave(
  filename = file.path(output_dir, "technique_top20_timelines.pdf"),
  plot = p_top20,
  width = 16,
  height = 12
)

cat(sprintf("✅ Saved: %s\n", file.path(output_dir, "technique_top20_timelines.png")))

# ============================================================================
# 3b. Top 20 Techniques - Anomaly Plot (Scaled by Total Papers)
# ============================================================================

cat("\nCreating Top 20 techniques anomaly plot...\n")

# Calculate total papers per year (all techniques combined)
total_papers_by_year <- trends %>%
  group_by(year) %>%
  summarise(total_papers = sum(paper_count), .groups = "drop")

# For top 20, calculate proportion of papers using each technique
technique_proportions <- trends_top20 %>%
  left_join(total_papers_by_year, by = "year") %>%
  mutate(proportion = paper_count / total_papers)

# Calculate mean proportion for each technique across all years
mean_tech_proportions <- technique_proportions %>%
  group_by(technique_name, primary_discipline) %>%
  summarise(mean_prop = mean(proportion), .groups = "drop")

# Calculate anomaly (deviation from mean)
tech_anomalies <- technique_proportions %>%
  left_join(mean_tech_proportions, by = c("technique_name", "primary_discipline")) %>%
  mutate(anomaly = (proportion - mean_prop) * 100)  # Percentage points

# Calculate 5-year rolling average for smoother
tech_anomalies_smooth <- tech_anomalies %>%
  arrange(technique_name, year) %>%
  group_by(technique_name, primary_discipline) %>%
  mutate(
    anomaly_smooth = zoo::rollmean(anomaly, k = 5, fill = NA, align = "center")
  ) %>%
  ungroup()

# Create anomaly plot
p_tech_anomaly <- tech_anomalies_smooth %>%
  ggplot(aes(x = year, y = anomaly)) +
  geom_hline(yintercept = 0, linetype = "dashed", color = "grey50", size = 0.5) +
  geom_line(aes(color = primary_discipline), size = 0.8, alpha = 0.4) +
  geom_line(aes(y = anomaly_smooth, color = primary_discipline), size = 0.6, linetype = "11", alpha = 0.9) +
  geom_point(aes(color = primary_discipline), size = 1, alpha = 0.5) +
  facet_wrap(~ technique_name, scales = "free_y", ncol = 4) +
  scale_color_manual(
    values = setNames(discipline_info$color, discipline_info$code),
    name = "Discipline",
    labels = setNames(discipline_info$full_name, discipline_info$code)
  ) +
  scale_x_continuous(
    breaks = c(1960, 1990, 2020),
    limits = c(1950, 2025)
  ) +
  labs(
    title = "Top 20 Techniques: Deviations from Long-Term Average Usage",
    subtitle = "Anomaly = % of papers using technique minus long-term average (scaled by total papers)",
    x = "Year",
    y = "Deviation from Mean (%)",
    caption = "Solid line = annual data | Dashed line = 5-year rolling average\nPositive = growing faster than average | Negative = declining relative to average | Y-axes independent | Color = primary discipline"
  ) +
  theme_minimal(base_size = 9) +
  theme(
    plot.title = element_text(size = 16, face = "bold", hjust = 0.5),
    plot.subtitle = element_text(size = 10, hjust = 0.5, margin = margin(b = 15)),
    plot.caption = element_text(size = 8, hjust = 0.5, margin = margin(t = 10)),
    strip.text = element_text(face = "bold", size = 8),
    legend.position = "bottom",
    legend.title = element_text(face = "bold", size = 9),
    legend.text = element_text(size = 8),
    panel.grid.minor = element_blank(),
    axis.title = element_text(face = "bold", size = 10),
    axis.text = element_text(size = 7)
  )

ggsave(
  filename = file.path(output_dir, "technique_top20_anomaly.png"),
  plot = p_tech_anomaly,
  width = 16,
  height = 12,
  dpi = 300
)

ggsave(
  filename = file.path(output_dir, "technique_top20_anomaly.pdf"),
  plot = p_tech_anomaly,
  width = 16,
  height = 12
)

cat(sprintf("✅ Saved: %s\n", file.path(output_dir, "technique_top20_anomaly.png")))

# ============================================================================
# 4. Technique Emergence Timeline (When did techniques first appear?)
# ============================================================================

cat("\nCalculating technique emergence years...\n")

# Find first year each technique appeared
emergence <- trends %>%
  group_by(technique_name, primary_discipline) %>%
  summarise(
    first_year = min(year),
    total_papers = sum(paper_count),
    .groups = "drop"
  ) %>%
  left_join(discipline_info, by = c("primary_discipline" = "code"))

# Get top 30 by total papers for clearer visualization
top_30_emergence <- emergence %>%
  arrange(desc(total_papers)) %>%
  head(30)

# Create emergence timeline
p_emergence <- top_30_emergence %>%
  ggplot(aes(x = first_year, y = reorder(technique_name, first_year), color = primary_discipline)) +
  geom_point(aes(size = total_papers), alpha = 0.7) +
  geom_segment(
    aes(x = 1950, xend = first_year, yend = reorder(technique_name, first_year)),
    alpha = 0.3,
    size = 0.5
  ) +
  scale_color_manual(
    values = setNames(discipline_info$color, discipline_info$code),
    name = "Discipline",
    labels = setNames(discipline_info$full_name, discipline_info$code)
  ) +
  scale_size_continuous(
    name = "Total Papers",
    range = c(2, 10),
    labels = comma
  ) +
  scale_x_continuous(
    breaks = seq(1950, 2025, 10),
    limits = c(1950, 2030)
  ) +
  labs(
    title = "When Did Techniques Emerge in Shark Science?",
    subtitle = "Top 30 techniques by first year of appearance (point size = total papers)",
    x = "Year of First Appearance",
    y = NULL,
    caption = "Lines show timeline from 1950 to emergence | Larger points = more popular techniques"
  ) +
  theme_minimal(base_size = 11) +
  theme(
    plot.title = element_text(size = 16, face = "bold", hjust = 0.5),
    plot.subtitle = element_text(size = 11, hjust = 0.5, margin = margin(b = 15)),
    plot.caption = element_text(size = 9, hjust = 0.5, margin = margin(t = 10)),
    legend.position = "right",
    panel.grid.minor = element_blank(),
    axis.text.y = element_text(size = 9),
    axis.title = element_text(face = "bold")
  )

ggsave(
  filename = file.path(output_dir, "technique_emergence_timeline.png"),
  plot = p_emergence,
  width = 14,
  height = 11,
  dpi = 300
)

ggsave(
  filename = file.path(output_dir, "technique_emergence_timeline.pdf"),
  plot = p_emergence,
  width = 14,
  height = 11
)

cat(sprintf("✅ Saved: %s\n", file.path(output_dir, "technique_emergence_timeline.png")))

# ============================================================================
# 5. Emerging vs. Declining Techniques (Recent Trends)
# ============================================================================

cat("\nIdentifying emerging and declining techniques...\n")

# Calculate growth rate 2015-2019 vs 2020-2025
growth_analysis <- trends %>%
  filter(year >= 2015) %>%
  mutate(period = if_else(year >= 2020, "2020-2025", "2015-2019")) %>%
  group_by(technique_name, primary_discipline, period) %>%
  summarise(avg_papers = mean(paper_count), .groups = "drop") %>%
  pivot_wider(names_from = period, values_from = avg_papers, values_fill = 0) %>%
  mutate(
    change = `2020-2025` - `2015-2019`,
    pct_change = if_else(`2015-2019` > 0,
                         (change / `2015-2019`) * 100,
                         NA_real_),
    total_recent = `2015-2019` + `2020-2025`,
    category = case_when(
      pct_change >= 50 ~ "Emerging (>50% growth)",
      pct_change <= -25 ~ "Declining (>25% decline)",
      TRUE ~ "Stable"
    )
  ) %>%
  filter(total_recent >= 10)  # Only techniques with at least 10 papers in recent period

# Get top emerging and declining
top_emerging <- growth_analysis %>%
  filter(category == "Emerging (>50% growth)") %>%
  arrange(desc(pct_change)) %>%
  head(15)

top_declining <- growth_analysis %>%
  filter(category == "Declining (>25% decline)") %>%
  arrange(pct_change) %>%
  head(15)

# Combine for visualization
emerging_declining <- bind_rows(
  top_emerging %>% mutate(type = "Emerging"),
  top_declining %>% mutate(type = "Declining")
) %>%
  left_join(discipline_info, by = c("primary_discipline" = "code"))

# Create visualization
p_growth <- emerging_declining %>%
  ggplot(aes(x = pct_change, y = reorder(technique_name, pct_change), fill = primary_discipline)) +
  geom_col(alpha = 0.8) +
  geom_vline(xintercept = 0, linetype = "dashed", color = "grey40") +
  scale_fill_manual(
    values = setNames(discipline_info$color, discipline_info$code),
    name = "Discipline",
    labels = setNames(discipline_info$full_name, discipline_info$code)
  ) +
  scale_x_continuous(labels = function(x) paste0(x, "%")) +
  labs(
    title = "Emerging vs. Declining Techniques (2015-2025)",
    subtitle = "Percent change in usage: 2020-2025 compared to 2015-2019",
    x = "% Change in Papers per Year",
    y = NULL,
    caption = "Only techniques with ≥10 papers in recent period | Emerging = >50% growth | Declining = >25% decline"
  ) +
  theme_minimal(base_size = 11) +
  theme(
    plot.title = element_text(size = 16, face = "bold", hjust = 0.5),
    plot.subtitle = element_text(size = 11, hjust = 0.5, margin = margin(b = 15)),
    plot.caption = element_text(size = 8, hjust = 0.5, margin = margin(t = 10)),
    legend.position = "right",
    panel.grid.minor = element_blank(),
    panel.grid.major.y = element_blank(),
    axis.text.y = element_text(size = 9),
    axis.title = element_text(face = "bold")
  )

ggsave(
  filename = file.path(output_dir, "technique_emerging_declining.png"),
  plot = p_growth,
  width = 14,
  height = 10,
  dpi = 300
)

ggsave(
  filename = file.path(output_dir, "technique_emerging_declining.pdf"),
  plot = p_growth,
  width = 14,
  height = 10
)

cat(sprintf("✅ Saved: %s\n", file.path(output_dir, "technique_emerging_declining.png")))

# ============================================================================
# 6. Technique Diversity Over Time
# ============================================================================

cat("\nCalculating technique diversity over time...\n")

# Count unique techniques per year
diversity <- trends %>%
  group_by(year) %>%
  summarise(
    unique_techniques = n_distinct(technique_name),
    total_papers = sum(paper_count),
    .groups = "drop"
  ) %>%
  mutate(techniques_per_paper = unique_techniques / total_papers)

# Create diversity plot
p_diversity <- diversity %>%
  ggplot(aes(x = year)) +
  geom_line(aes(y = unique_techniques), color = "#2E86AB", size = 1.5, alpha = 0.8) +
  geom_point(aes(y = unique_techniques), color = "#2E86AB", size = 2, alpha = 0.6) +
  scale_x_continuous(
    breaks = seq(1950, 2025, 10),
    limits = c(1950, 2025)
  ) +
  scale_y_continuous(
    limits = c(0, NA),
    expand = expansion(mult = c(0, 0.1))
  ) +
  labs(
    title = "Growth in Technique Diversity (1950-2025)",
    subtitle = "Number of unique analytical techniques used each year in shark science",
    x = "Year",
    y = "Number of Unique Techniques",
    caption = "Shows increasing methodological sophistication over time"
  ) +
  theme_minimal(base_size = 13) +
  theme(
    plot.title = element_text(size = 16, face = "bold", hjust = 0.5),
    plot.subtitle = element_text(size = 11, hjust = 0.5, margin = margin(b = 15)),
    plot.caption = element_text(size = 9, hjust = 0.5, margin = margin(t = 10)),
    panel.grid.minor = element_blank(),
    axis.title = element_text(face = "bold")
  )

ggsave(
  filename = file.path(output_dir, "technique_diversity_over_time.png"),
  plot = p_diversity,
  width = 12,
  height = 7,
  dpi = 300
)

ggsave(
  filename = file.path(output_dir, "technique_diversity_over_time.pdf"),
  plot = p_diversity,
  width = 12,
  height = 7
)

cat(sprintf("✅ Saved: %s\n", file.path(output_dir, "technique_diversity_over_time.png")))

# ============================================================================
# 7. Recent Innovations: Techniques that emerged after 2010
# ============================================================================

cat("\nIdentifying recent innovations (post-2010)...\n")

recent_innovations <- emergence %>%
  filter(first_year >= 2010) %>%
  arrange(desc(total_papers)) %>%
  head(20)

p_innovations <- recent_innovations %>%
  ggplot(aes(x = total_papers, y = reorder(technique_name, total_papers), fill = primary_discipline)) +
  geom_col(alpha = 0.8) +
  geom_text(
    aes(label = paste0("Since ", first_year)),
    hjust = -0.1,
    size = 3,
    fontface = "italic"
  ) +
  scale_fill_manual(
    values = setNames(discipline_info$color, discipline_info$code),
    name = "Discipline",
    labels = setNames(discipline_info$full_name, discipline_info$code)
  ) +
  scale_x_continuous(
    labels = comma,
    expand = expansion(mult = c(0, 0.2))
  ) +
  labs(
    title = "Recent Innovations: Techniques Emerging Since 2010",
    subtitle = "Top 20 newest techniques by total papers",
    x = "Total Papers",
    y = NULL,
    caption = "Shows which cutting-edge methods are gaining traction in shark science"
  ) +
  theme_minimal(base_size = 11) +
  theme(
    plot.title = element_text(size = 16, face = "bold", hjust = 0.5),
    plot.subtitle = element_text(size = 11, hjust = 0.5, margin = margin(b = 15)),
    plot.caption = element_text(size = 9, hjust = 0.5, margin = margin(t = 10)),
    legend.position = "right",
    panel.grid.minor = element_blank(),
    panel.grid.major.y = element_blank(),
    axis.text.y = element_text(size = 9, face = "bold"),
    axis.title = element_text(face = "bold")
  )

ggsave(
  filename = file.path(output_dir, "technique_recent_innovations.png"),
  plot = p_innovations,
  width = 14,
  height = 10,
  dpi = 300
)

ggsave(
  filename = file.path(output_dir, "technique_recent_innovations.pdf"),
  plot = p_innovations,
  width = 14,
  height = 10
)

cat(sprintf("✅ Saved: %s\n", file.path(output_dir, "technique_recent_innovations.png")))

# ============================================================================
# 8. Summary Statistics
# ============================================================================

cat(paste0("\n", strrep("=", 70), "\n"))
cat("TECHNIQUE TRENDS SUMMARY\n")
cat(paste0(strrep("=", 70), "\n\n"))

cat(sprintf("Total unique techniques: %d\n", n_distinct(trends$technique_name)))
cat(sprintf("Year range: %d-%d\n", min(trends$year), max(trends$year)))

cat("\nTechnique diversity growth:\n")
cat(sprintf("  1950s: %d techniques\n", diversity$unique_techniques[diversity$year == 1950]))
cat(sprintf("  2000s: %d techniques\n", diversity$unique_techniques[diversity$year == 2000]))
cat(sprintf("  2025:  %d techniques\n", diversity$unique_techniques[diversity$year == 2025]))

cat("\nTop 5 emerging techniques (2020-2025 vs 2015-2019):\n")
for (i in 1:min(5, nrow(top_emerging))) {
  cat(sprintf("  %d. %-40s  +%.0f%%\n",
              i, top_emerging$technique_name[i], top_emerging$pct_change[i]))
}

cat("\nTop 5 declining techniques (2020-2025 vs 2015-2019):\n")
for (i in 1:min(5, nrow(top_declining))) {
  cat(sprintf("  %d. %-40s  %.0f%%\n",
              i, top_declining$technique_name[i], top_declining$pct_change[i]))
}

cat("\nRecent innovations (techniques since 2010):\n")
cat(sprintf("  Total: %d new techniques\n", sum(emergence$first_year >= 2010)))
cat(sprintf("  Top 3:\n"))
for (i in 1:3) {
  cat(sprintf("    %d. %-40s  %d papers (since %d)\n",
              i,
              recent_innovations$technique_name[i],
              recent_innovations$total_papers[i],
              recent_innovations$first_year[i]))
}

cat(paste0("\n", strrep("=", 70), "\n"))
cat("All visualizations saved to: outputs/figures/\n")
cat(paste0(strrep("=", 70), "\n"))
