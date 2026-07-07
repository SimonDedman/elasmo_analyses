## viz_basin_barchart.R
## Reproduces outputs/figures/basin_barchart.png but with x-axis ordered
## DESCENDING (largest -> smallest) instead of ascending.
##
## Note: the original script that generated basin_barchart.png was not
## present in scripts/ or in the elasmo_analyses GitHub repo. This script
## reconstructs the figure from outputs/viz_data.csv (the same data source
## used by viz_A_spatial.R and viz_fixes.R).

suppressPackageStartupMessages({
  library(tidyverse)
  library(scales)
  library(viridis)
})

base_dir <- "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
fig_dir  <- file.path(base_dir, "outputs/figures")
dir.create(fig_dir, showWarnings = FALSE, recursive = TRUE)

df <- read_csv(file.path(base_dir, "outputs/viz_data.csv"),
               show_col_types = FALSE, guess_max = 5000)

b_cols <- names(df)[startsWith(names(df), "b_")]

clean_name <- function(x) {
  x |>
    str_remove("^(eco_|pr_|gear_|imp_|d_|b_|sp_|gear_mit_)") |>
    str_replace_all("_", " ") |>
    str_to_title()
}

basin_counts <- tibble(
  basin = b_cols,
  n     = sapply(b_cols, function(col) sum(df[[col]] == 1, na.rm = TRUE))
) |>
  mutate(label = clean_name(basin))

# DESCENDING order: largest on the left, smallest on the right.
basin_counts <- basin_counts |>
  arrange(desc(n)) |>
  mutate(label = factor(label, levels = label))

cat("Basin counts (descending):\n")
print(basin_counts |> select(label, n))

theme_eea <- theme_minimal(base_size = 13) +
  theme(
    plot.background   = element_rect(fill = "white", colour = NA),
    panel.background  = element_rect(fill = "white", colour = NA),
    panel.grid.major  = element_line(colour = "grey92"),
    panel.grid.minor  = element_blank(),
    plot.title        = element_text(face = "bold", size = 16),
    plot.subtitle     = element_text(colour = "grey40", size = 12),
    axis.text.x       = element_text(angle = 30, hjust = 1),
    axis.title.x      = element_blank(),
    legend.position   = "none"
  )

p <- ggplot(basin_counts, aes(x = label, y = n, fill = n)) +
  geom_col() +
  geom_text(aes(label = comma(n)), vjust = -0.4, size = 3.6) +
  # Smallest = light, largest = dark (matches original mako-style palette)
  scale_fill_viridis_c(option = "mako", direction = -1) +
  scale_y_continuous(labels = comma, expand = expansion(mult = c(0, 0.08))) +
  labs(
    title    = "Elasmobranch research by ocean basin",
    subtitle = "Papers classified per basin (multi-label, papers with PDFs)",
    y        = "Number of papers"
  ) +
  theme_eea

out_png <- file.path(fig_dir, "basin_barchart_desc.png")
out_pdf <- file.path(fig_dir, "basin_barchart_desc.pdf")
ggsave(out_png, p, width = 12, height = 7, dpi = 200, bg = "white")
ggsave(out_pdf, p, width = 12, height = 7, bg = "white")
cat("Saved:", out_png, "\n")
cat("Saved:", out_pdf, "\n")
