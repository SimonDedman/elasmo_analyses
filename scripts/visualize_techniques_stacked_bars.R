#!/usr/bin/env Rscript
# ============================================================================
# STACKED BAR PLOTS: TECHNIQUES PER DISCIPLINE PER YEAR
# ============================================================================
# Purpose: Create 8 stacked bar plots (one per discipline) showing technique
#          usage over time, following Tiktak et al. 2020 style
#
# Reference: guuske barplot.png
#   - Vertical stacked bars
#   - X-axis: Years
#   - Y-axis: Number of studies/papers
#   - Stacked segments: Different techniques (color-coded)
#
# Outputs: 8 PNG + 8 PDF files (one pair per discipline)
#
# Author: EEA 2025 Data Panel
# Date: 2025-10-26
# ============================================================================

library(tidyverse)
library(scales)
library(viridis)
library(RColorBrewer)

# ============================================================================
# LOAD DATA
# ============================================================================

cat("\n=== LOADING DATA ===\n")

# Load technique data by discipline and year
technique_data <- read_csv(
  "outputs/analysis/techniques_per_discipline_per_year.csv",
  show_col_types = FALSE
)

cat(sprintf("Loaded %s technique-year records\n", comma(nrow(technique_data))))
cat(sprintf("Disciplines: %s\n", paste(unique(technique_data$primary_discipline), collapse = ", ")))

# Load trend analysis to get classification info
trend_analysis <- read_csv(
  "outputs/analysis/technique_trends_analysis.csv",
  show_col_types = FALSE
)

# ============================================================================
# DATA PREPARATION
# ============================================================================

cat("\n=== PREPARING DATA ===\n")

# Add classification to technique data
technique_data <- technique_data %>%
  left_join(
    trend_analysis %>% select(primary_discipline, technique_name, classification),
    by = c("primary_discipline", "technique_name")
  )

# For each discipline, identify top techniques to display
# (to avoid too many legend items, we'll show top 15-20 techniques and group rest as "Other")

MAX_TECHNIQUES_SHOWN <- 15

# Function to prepare data for one discipline
prepare_discipline_data <- function(disc_code, disc_name) {

  disc_data <- technique_data %>%
    filter(primary_discipline == disc_code)

  # Get top techniques by total paper count
  top_techniques <- disc_data %>%
    group_by(technique_name) %>%
    summarise(total_papers = sum(paper_count), .groups = "drop") %>%
    arrange(desc(total_papers)) %>%
    slice_head(n = MAX_TECHNIQUES_SHOWN) %>%
    pull(technique_name)

  # Group others
  disc_data_grouped <- disc_data %>%
    mutate(
      technique_display = ifelse(
        technique_name %in% top_techniques,
        technique_name,
        "Other techniques"
      )
    ) %>%
    group_by(primary_discipline, full_name, year, technique_display) %>%
    summarise(
      paper_count = sum(paper_count),
      .groups = "drop"
    )

  return(disc_data_grouped)
}

# ============================================================================
# CREATE STACKED BAR PLOTS
# ============================================================================

cat("\n=== CREATING STACKED BAR PLOTS ===\n")

# Discipline info
disciplines <- tribble(
  ~code, ~name,
  "BEH", "Behaviour",
  "BIO", "Biology",
  "CON", "Conservation",
  "DATA", "Data Science",
  "FISH", "Fisheries",
  "GEN", "Genetics",
  "MOV", "Movement",
  "TRO", "Trophic Ecology"
)

# Create plot for each discipline
for (i in 1:nrow(disciplines)) {
  disc_code <- disciplines$code[i]
  disc_name <- disciplines$name[i]

  cat(sprintf("\nProcessing: %s (%s)\n", disc_name, disc_code))

  # Prepare data
  plot_data <- prepare_discipline_data(disc_code, disc_name)

  # Get year range
  year_min <- min(plot_data$year)
  year_max <- max(plot_data$year)

  # Count techniques shown
  n_techniques <- n_distinct(plot_data$technique_display)

  cat(sprintf("  Years: %d - %d\n", year_min, year_max))
  cat(sprintf("  Techniques shown: %d\n", n_techniques))
  cat(sprintf("  Total records: %d\n", nrow(plot_data)))

  # Create color palette
  # Use a combination of Set2, Set3, and Paired for better distinction
  if (n_techniques <= 8) {
    colors <- brewer.pal(max(3, n_techniques), "Set2")
  } else if (n_techniques <= 12) {
    colors <- brewer.pal(max(3, n_techniques), "Set3")
  } else {
    colors <- c(
      brewer.pal(8, "Set2"),
      brewer.pal(8, "Set3"),
      brewer.pal(min(8, n_techniques - 16), "Paired")
    )[1:n_techniques]
  }

  # Make "Other techniques" grey if present
  technique_levels <- plot_data %>%
    group_by(technique_display) %>%
    summarise(total = sum(paper_count), .groups = "drop") %>%
    arrange(desc(total)) %>%
    pull(technique_display)

  if ("Other techniques" %in% technique_levels) {
    other_idx <- which(technique_levels == "Other techniques")
    colors[other_idx] <- "grey80"
  }

  # Create plot
  p <- ggplot(plot_data, aes(x = year, y = paper_count, fill = factor(technique_display, levels = technique_levels))) +
    geom_col(width = 0.8, color = NA) +
    scale_fill_manual(
      values = colors,
      name = "Technique"
    ) +
    scale_x_continuous(
      breaks = seq(
        ceiling(year_min / 5) * 5,
        floor(year_max / 5) * 5,
        by = 5
      ),
      expand = c(0.01, 0)
    ) +
    scale_y_continuous(
      expand = c(0, 0),
      labels = comma
    ) +
    labs(
      title = sprintf("%s: Techniques Over Time", disc_name),
      subtitle = sprintf("Stacked bar plot showing top %d techniques by paper count (%d-%d)",
                        min(MAX_TECHNIQUES_SHOWN, n_techniques - 1), year_min, year_max),
      x = "Year",
      y = "Number of Papers",
      caption = sprintf("EEA 2025 Data Panel | N = %s papers across %d techniques",
                       comma(sum(plot_data$paper_count)), n_techniques)
    ) +
    theme_minimal(base_size = 12) +
    theme(
      plot.background = element_rect(fill = "white", color = NA),
      panel.background = element_rect(fill = "white", color = NA),
      panel.grid.major.x = element_blank(),
      panel.grid.minor = element_blank(),
      panel.grid.major.y = element_line(color = "grey90", linewidth = 0.3),
      axis.text = element_text(size = 10),
      axis.title = element_text(size = 12, face = "bold"),
      plot.title = element_text(size = 16, face = "bold", hjust = 0.5, margin = margin(b = 5)),
      plot.subtitle = element_text(size = 10, hjust = 0.5, color = "grey40", margin = margin(b = 15)),
      plot.caption = element_text(size = 9, color = "grey50", margin = margin(t = 15)),
      legend.position = "right",
      legend.title = element_text(size = 11, face = "bold"),
      legend.text = element_text(size = 9),
      legend.key.size = unit(0.4, "cm"),
      plot.margin = margin(t = 10, r = 10, b = 10, l = 10)
    ) +
    guides(fill = guide_legend(ncol = 1))

  # Save PNG
  png_file <- sprintf("outputs/figures/%s_techniques_stacked.png", disc_code)
  ggsave(
    png_file,
    plot = p,
    width = 12,
    height = 8,
    dpi = 300,
    bg = "white"
  )

  # Save PDF
  pdf_file <- sprintf("outputs/figures/%s_techniques_stacked.pdf", disc_code)
  ggsave(
    pdf_file,
    plot = p,
    width = 12,
    height = 8,
    bg = "white"
  )

  cat(sprintf("  ✓ Saved: %s (%.1f KB)\n", basename(png_file), file.size(png_file) / 1024))
  cat(sprintf("  ✓ Saved: %s (%.1f KB)\n", basename(pdf_file), file.size(pdf_file) / 1024))
}

# ============================================================================
# SUMMARY
# ============================================================================

cat("\n")
cat(paste0(strrep("=", 80), "\n"))
cat("STACKED BAR PLOTS COMPLETE\n")
cat(paste0(strrep("=", 80), "\n\n"))

cat("FILES CREATED:\n")
for (i in 1:nrow(disciplines)) {
  disc_code <- disciplines$code[i]
  disc_name <- disciplines$name[i]
  cat(sprintf("  %s: %s_techniques_stacked.png + .pdf\n", disc_name, disc_code))
}

cat("\nTotal: 16 files (8 PNG + 8 PDF)\n")
cat("\n")
cat(paste0(strrep("=", 80), "\n"))
cat("Ready for Phase 3: Geographic Visualizations\n")
cat(paste0(strrep("=", 80), "\n"))
