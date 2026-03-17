#!/usr/bin/env Rscript
# ============================================================================
# visualize_issue3_technique_cards.R
#
# Issue #3: Summary linking techniques to key descriptors
# Generates visual "cards" for the top 3 techniques per discipline.
#
# Author: Simon Dedman / EEA 2025 Data Panel
# Date: 2026-03-15
# ============================================================================

library(tidyverse)
library(scales)

# ============================================================================
# CONFIGURATION
# ============================================================================

input_dir  <- "outputs/meeting_review"
output_dir <- "outputs/figures"
dir.create(output_dir, showWarnings = FALSE, recursive = TRUE)

theme_card <- theme_minimal(base_size = 12) +
  theme(
    plot.title       = element_text(face = "bold", size = 14, hjust = 0),
    plot.subtitle    = element_text(colour = "grey40", size = 10, hjust = 0),
    panel.background = element_rect(fill = "white", colour = NA),
    plot.background  = element_rect(fill = "white", colour = NA),
    panel.grid.major = element_line(colour = "grey92"),
    panel.grid.minor = element_blank(),
    axis.text        = element_text(colour = "grey30"),
    axis.title       = element_text(colour = "grey20"),
    strip.text       = element_text(face = "bold", size = 10)
  )

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

cat("Loading technique card data...\n")
cards <- read_csv(file.path(input_dir, "technique_cards_data.csv"),
                  show_col_types = FALSE)

# Discipline colours (consistent across project)
disc_colours <- c(
  BEH = "#e74c3c", BIO = "#3498db", CON = "#2ecc71", DATA = "#9b59b6",
  FISH = "#f39c12", GEN = "#1abc9c", MOV = "#e67e22", TRO = "#34495e"
)

# ============================================================================
# 2. SUMMARY CARD PLOT (all disciplines, one figure)
# ============================================================================

cat("\n=== Building technique summary cards ===\n")

card_data <- cards |>
  mutate(
    technique_label = pretty_name(technique),
    eco_summary = paste0(
      pretty_name(eco_1), " (", eco_1_n, "), ",
      pretty_name(eco_2), " (", eco_2_n, "), ",
      pretty_name(eco_3), " (", eco_3_n, ")"
    ),
    pr_summary = paste0(
      pretty_name(pr_1), " (", pr_1_n, "), ",
      pretty_name(pr_2), " (", pr_2_n, "), ",
      pretty_name(pr_3), " (", pr_3_n, ")"
    ),
    gear_summary = paste0(
      pretty_name(gear_1), " (", gear_1_n, "), ",
      pretty_name(gear_2), " (", gear_2_n, "), ",
      pretty_name(gear_3), " (", gear_3_n, ")"
    ),
    imp_summary = paste0(
      pretty_name(imp_1), " (", imp_1_n, "), ",
      pretty_name(imp_2), " (", imp_2_n, "), ",
      pretty_name(imp_3), " (", imp_3_n, ")"
    ),
    year_span = paste0(first_year, " \u2013 ", last_year),
    card_label = paste0("#", rank, ": ", technique_label, "\n",
                        n_papers, " papers | ", year_span),
    row_id = paste0(discipline_code, "_", rank)
  )

# Horizontal bar chart: papers per technique, faceted by discipline
p_cards <- card_data |>
  mutate(
    discipline_label = factor(discipline_label,
      levels = rev(sort(unique(discipline_label)))),
    technique_label = fct_reorder(technique_label, n_papers, .fun = max)
  ) |>
  ggplot(aes(x = n_papers, y = technique_label, fill = discipline_code)) +
  geom_col(width = 0.7, show.legend = FALSE) +
  geom_text(aes(label = paste0(comma(n_papers), " (", first_year, "\u2013", last_year, ")")),
            hjust = -0.05, size = 3, colour = "grey30") +
  facet_wrap(~ discipline_label, scales = "free_y", ncol = 2) +
  scale_fill_manual(values = disc_colours) +
  scale_x_continuous(expand = expansion(mult = c(0, 0.35)), labels = comma) +
  labs(
    title    = "Top 3 Techniques per Discipline",
    subtitle = "Paper count and year span within each discipline",
    x = "Number of Papers", y = NULL
  ) +
  theme_card +
  theme(
    strip.text = element_text(face = "bold", size = 10),
    axis.text.y = element_text(size = 9)
  )
save_plot(p_cards, "issue3_technique_cards_barplot", w = 16, h = 14)

# ============================================================================
# 3. DETAILED DESCRIPTOR TABLE (text-based cards as a tile plot)
# ============================================================================

cat("\n=== Building descriptor matrix ===\n")

# Build a long-form descriptor table
descriptors <- card_data |>
  select(discipline_code, rank, technique_label, n_papers, year_span,
         eco_summary, pr_summary, gear_summary, imp_summary) |>
  pivot_longer(
    cols = c(eco_summary, pr_summary, gear_summary, imp_summary),
    names_to = "descriptor_type",
    values_to = "value"
  ) |>
  mutate(
    descriptor_label = case_when(
      descriptor_type == "eco_summary"  ~ "Ecosystems",
      descriptor_type == "pr_summary"   ~ "Pressures",
      descriptor_type == "gear_summary" ~ "Gear",
      descriptor_type == "imp_summary"  ~ "Impacts"
    ),
    card_id = paste0(discipline_code, " #", rank, ": ", technique_label)
  )

# Create a tile-based descriptor overview
p_desc <- descriptors |>
  mutate(
    card_id = fct_inorder(card_id),
    descriptor_label = factor(descriptor_label,
      levels = c("Ecosystems", "Pressures", "Gear", "Impacts"))
  ) |>
  ggplot(aes(x = descriptor_label, y = fct_rev(card_id))) +
  geom_tile(fill = "grey97", colour = "grey80") +
  geom_text(aes(label = str_wrap(value, width = 35)), size = 2.3,
            lineheight = 0.9) +
  labs(
    title    = "Technique Descriptor Summary Cards",
    subtitle = "Top 3 techniques per discipline with ecosystem, pressure, gear, and impact context",
    x = NULL, y = NULL
  ) +
  theme_card +
  theme(
    axis.text.y  = element_text(size = 7, hjust = 1),
    axis.text.x  = element_text(size = 10, face = "bold"),
    panel.grid   = element_blank()
  )
save_plot(p_desc, "issue3_technique_descriptor_matrix", w = 18, h = 16)

# ============================================================================
# 4. INDIVIDUAL DISCIPLINE CARDS (one per discipline)
# ============================================================================

cat("\n=== Building per-discipline card plots ===\n")

for (code in unique(card_data$discipline_code)) {
  disc_data <- card_data |> filter(discipline_code == code)
  disc_label <- disc_data$discipline_label[1]

  # Small multiples: one row per technique, bars for each descriptor count
  # Build long-form descriptor data manually
  desc_rows <- list()
  for (r in seq_len(nrow(disc_data))) {
    row <- disc_data[r, ]
    for (cat in c("eco", "pr", "gear", "imp")) {
      for (pos in 1:3) {
        col_val <- row[[paste0(cat, "_", pos)]]
        cnt_val <- row[[paste0(cat, "_", pos, "_n")]]
        if (!is.na(col_val) && col_val != "" && !is.na(cnt_val) && cnt_val > 0) {
          desc_rows <- c(desc_rows, list(tibble(
            technique_label = row$technique_label,
            rank = row$rank,
            category = cat,
            col_name = col_val,
            count = cnt_val
          )))
        }
      }
    }
  }
  desc_long <- bind_rows(desc_rows) |>
    mutate(
      label = pretty_name(col_name),
      category_label = case_when(
        category == "eco"  ~ "Ecosystem",
        category == "pr"   ~ "Pressure",
        category == "gear" ~ "Gear",
        category == "imp"  ~ "Impact"
      ),
      technique_label = fct_reorder(technique_label, -rank)
    )

  p_disc <- desc_long |>
    ggplot(aes(x = count, y = fct_rev(label), fill = category_label)) +
    geom_col(width = 0.6, show.legend = TRUE) +
    facet_grid(rows = vars(technique_label), cols = vars(category_label),
               scales = "free", space = "free_y") +
    geom_text(aes(label = count), hjust = -0.2, size = 2.8) +
    scale_fill_brewer(palette = "Set2", guide = "none") +
    scale_x_continuous(expand = expansion(mult = c(0, 0.3))) +
    labs(
      title    = paste0(disc_label, " (", code, ")"),
      subtitle = "Top 3 techniques: ecosystem, pressure, gear, and impact descriptors",
      x = "Papers", y = NULL
    ) +
    theme_card +
    theme(strip.text = element_text(size = 9))
  save_plot(p_disc, paste0("issue3_card_", code), w = 14, h = 8)
}

cat("\n============================================================\n")
cat("All Issue #3 plots generated!\n")
cat("============================================================\n")
