# viz_fixes.R
# Regenerates 5 plots (B4, D1, D2, D3, D4) with specific fixes applied.

suppressPackageStartupMessages(library(tidyverse))

base_dir <- "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
fig_dir  <- file.path(base_dir, "outputs/figures")
dir.create(fig_dir, showWarnings = FALSE, recursive = TRUE)

df <- read_csv(file.path(base_dir, "outputs/viz_data.csv"),
               show_col_types = FALSE, guess_max = 5000)
df <- df |> filter(!is.na(year), year >= 1950, year <= 2025)

n_papers <- nrow(df)
cat("Papers loaded:", n_papers, "\n")

# CRITICAL: filter columns to only actual binary (0/1 integer) schema columns
# Excludes non-binary columns like imp_direction, imp_quantified, imp_confidence, gear_target_species
is_binary_col <- function(col_name) {
  x <- df[[col_name]]
  is.numeric(x) && all(x %in% c(0, 1, NA))
}

imp_cols  <- names(df)[startsWith(names(df), "imp_")]
imp_cols  <- imp_cols[sapply(imp_cols, is_binary_col)]

pr_cols   <- names(df)[startsWith(names(df), "pr_")]
pr_cols   <- pr_cols[sapply(pr_cols, is_binary_col)]

eco_cols  <- names(df)[startsWith(names(df), "eco_")]
eco_cols  <- eco_cols[sapply(eco_cols, is_binary_col)]

gear_cols <- names(df)[startsWith(names(df), "gear_") & !startsWith(names(df), "gear_target")]
gear_cols <- gear_cols[sapply(gear_cols, is_binary_col)]

d_cols    <- names(df)[startsWith(names(df), "d_")]
d_cols    <- d_cols[sapply(d_cols, is_binary_col)]

b_cols    <- names(df)[startsWith(names(df), "b_")]
b_cols    <- b_cols[sapply(b_cols, is_binary_col)]

mit_cols      <- gear_cols[startsWith(gear_cols, "gear_mit_")]
gear_type_cols <- setdiff(gear_cols, mit_cols)

d_main <- c("d_biology", "d_behaviour", "d_trophic", "d_genetics",
            "d_movement", "d_fisheries", "d_conservation", "d_data_science")
d_main <- d_main[d_main %in% d_cols]

clean_name <- function(x) {
  x |>
    str_remove("^(eco_|pr_|gear_|imp_|d_|b_|sp_|gear_mit_)") |>
    str_replace_all("_", " ") |>
    str_to_title()
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

# ── B4. temporal_impact_evolution ─────────────────────────────────────────────
# Fix: use ONLY validated binary imp_cols (excludes imp_direction, imp_quantified,
# imp_confidence). Group by 5-year bins, count papers per bin per impact type,
# facet_wrap with free_y.
cat("\n--- B4: Temporal impact evolution ---\n")
cat("Binary imp_cols:", paste(imp_cols, collapse = ", "), "\n")

b4_long <- df |>
  mutate(bin = floor(year / 5) * 5) |>
  select(bin, all_of(imp_cols)) |>
  pivot_longer(cols = all_of(imp_cols), names_to = "impact", values_to = "val") |>
  filter(!is.na(val)) |>
  group_by(bin, impact) |>
  summarise(n = sum(val, na.rm = TRUE), .groups = "drop") |>
  mutate(label = clean_name(impact))

p_b4 <- ggplot(b4_long, aes(x = bin, y = n, colour = label, group = label)) +
  geom_line(linewidth = 0.8) +
  geom_point(size = 1.5) +
  facet_wrap(~label, scales = "free_y", ncol = 4) +
  labs(
    title    = "Temporal evolution of impact types in elasmobranch research",
    subtitle = "Papers per 5-year bin for each binary impact column",
    x = "5-year bin", y = "Number of papers"
  ) +
  theme_eea +
  theme(
    legend.position = "none",
    axis.text.x     = element_text(angle = 45, hjust = 1, size = 8)
  )

save_plot(p_b4, "B4_temporal_impact_evolution", w = 18, h = 14)

# ── D1. bars_schema_dashboard ─────────────────────────────────────────────────
# Fix: use ONLY validated binary columns from is_binary_col filter above.
# Include mit_cols as a separate schema panel. ncol = 3.
cat("\n--- D1: Schema dashboard ---\n")

schema_colours <- c(
  "Ecosystem"  = "#1b7837",
  "Pressure"   = "#d6604d",
  "Gear type"  = "#4393c3",
  "Mitigation" = "#2166ac",
  "Impact"     = "#9970ab",
  "Discipline" = "#d6b418",
  "Ocean basin" = "#74add1"
)

schema_prevalence <- function(data, cols, label) {
  data |>
    select(all_of(cols)) |>
    summarise(across(everything(), \(x) sum(x, na.rm = TRUE))) |>
    pivot_longer(everything(), names_to = "col", values_to = "n") |>
    mutate(
      pct    = 100 * n / n_papers,
      label  = clean_name(col),
      schema = label
    )
}

prev_all <- bind_rows(
  schema_prevalence(df, eco_cols,       "Ecosystem"),
  schema_prevalence(df, pr_cols,        "Pressure"),
  schema_prevalence(df, gear_type_cols, "Gear type"),
  schema_prevalence(df, mit_cols,       "Mitigation"),
  schema_prevalence(df, imp_cols,       "Impact"),
  schema_prevalence(df, d_cols,         "Discipline"),
  schema_prevalence(df, b_cols,         "Ocean basin")
) |>
  group_by(schema) |>
  mutate(label = fct_reorder(label, pct)) |>
  ungroup() |>
  mutate(schema = factor(schema, levels = names(schema_colours)))

p_d1 <- ggplot(prev_all, aes(x = label, y = pct, fill = schema)) +
  geom_col(show.legend = FALSE) +
  coord_flip() +
  scale_fill_manual(values = schema_colours) +
  facet_wrap(~schema, scales = "free_y", ncol = 3) +
  labs(
    title    = "Schema column prevalence across the corpus",
    subtitle = paste0("Percentage of ", format(n_papers, big.mark = ","),
                      " papers in which each binary column = 1"),
    x = NULL, y = "% of papers"
  ) +
  theme_eea +
  theme(axis.text.x = element_text(angle = 0, hjust = 0.5))

save_plot(p_d1, "D1_bars_schema_dashboard", w = 18, h = 16)

# ── D2. bars_discipline_comparison ────────────────────────────────────────────
# Fix: use ONLY validated binary columns; apply clean_name to avoid duplicates.
# Top 3 (not 5) per group per discipline; heatmap with geom_tile.
cat("\n--- D2: Discipline comparison heatmap ---\n")

top_n_cols <- function(data, cols, n = 3) {
  data |>
    select(all_of(cols)) |>
    summarise(across(everything(), \(x) sum(x, na.rm = TRUE))) |>
    pivot_longer(everything(), names_to = "col", values_to = "n") |>
    slice_max(n, n = n, with_ties = FALSE) |>
    pull(col)
}

top_pr   <- top_n_cols(df, pr_cols,        3)
top_gear <- top_n_cols(df, gear_type_cols, 3)
top_imp  <- top_n_cols(df, imp_cols,       3)
other_cols <- c(top_pr, top_gear, top_imp)

# Apply clean_name and ensure uniqueness by using original column names as keys
other_labels <- setNames(clean_name(other_cols), other_cols)

d2_long <- map_dfr(d_main, function(dcol) {
  d_bin <- df[[dcol]]
  map_dfr(other_cols, function(ocol) {
    o_bin <- df[[ocol]]
    tibble(
      discipline = clean_name(dcol),
      other      = other_labels[[ocol]],
      group      = case_when(
        ocol %in% top_pr   ~ "Pressure",
        ocol %in% top_gear ~ "Gear",
        TRUE               ~ "Impact"
      ),
      count = sum(d_bin == 1 & o_bin == 1, na.rm = TRUE)
    )
  })
}) |>
  mutate(
    discipline = fct_reorder(discipline, -count, sum),
    other      = fct_reorder(other, count, sum),
    group      = factor(group, levels = c("Pressure", "Gear", "Impact"))
  )

p_d2 <- ggplot(d2_long, aes(x = other, y = discipline, fill = count)) +
  geom_tile(colour = "white", linewidth = 0.4) +
  geom_text(aes(label = count), size = 3, colour = "white") +
  scale_fill_distiller(palette = "YlOrRd", direction = 1,
                       name = "Co-occurrence\n(papers)") +
  facet_wrap(~group, scales = "free_x", nrow = 1) +
  labs(
    title    = "Top pressures, gears, and impacts by discipline",
    subtitle = "Cell = papers where both discipline and other column = 1 (top 3 per group)",
    x = NULL, y = NULL
  ) +
  theme_eea +
  theme(axis.text.x = element_text(angle = 45, hjust = 1))

save_plot(p_d2, "D2_bars_discipline_comparison", w = 18, h = 8)

# ── D3. bars_bycatch_targets ──────────────────────────────────────────────────
# Fix: imp_is_bycatch is character "True"/"False", not numeric or logical.
# Filter using == "True" (string comparison). Split gear_target_species by comma.
cat("\n--- D3: Bycatch targets ---\n")

cat("imp_is_bycatch TRUE:", sum(df$imp_is_bycatch == TRUE, na.rm = TRUE), "\n")

bycatch_papers <- df |>
  filter(imp_is_bycatch == TRUE)

cat("Bycatch papers:", nrow(bycatch_papers), "\n")

if (nrow(bycatch_papers) == 0) {
  cat("  Skipping D3: no bycatch papers found.\n")
} else {
  target_counts <- bycatch_papers |>
    filter(!is.na(gear_target_species), gear_target_species != "") |>
    pull(gear_target_species) |>
    str_split(",") |>
    unlist() |>
    str_trim() |>
    str_to_lower() |>
    (\(x) x[x != ""])() |>
    tibble(species = _) |>
    count(species, name = "n", sort = TRUE) |>
    slice_max(n, n = 15, with_ties = FALSE) |>
    mutate(species = fct_reorder(species, n))

  cat("Top target species rows:", nrow(target_counts), "\n")

  if (nrow(target_counts) == 0) {
    cat("  Skipping D3: no target species data in bycatch papers.\n")
  } else {
    p_d3 <- ggplot(target_counts, aes(x = species, y = n)) +
      geom_col(fill = "#e08214") +
      coord_flip() +
      labs(
        title    = "Top fisheries where elasmobranchs are bycatch",
        subtitle = paste0("Top 15 target species/fishery terms from ",
                          nrow(bycatch_papers), " bycatch papers"),
        x = NULL, y = "Number of papers"
      ) +
      theme_eea +
      theme(axis.text.x = element_text(angle = 0, hjust = 0.5))

    save_plot(p_d3, "D3_bars_bycatch_targets", w = 12, h = 8)
  }
}

# ── D4. bars_mitigation_gaps ──────────────────────────────────────────────────
# Fix: order Y axis by grouping similar gears together using explicit factor levels.
cat("\n--- D4: Mitigation gaps ---\n")

gear_order <- c(
  "gear_trawl", "gear_trawl_beam", "gear_trawl_otter",
  "gear_demersal", "gear_pelagic",
  "gear_longline", "gear_hook_line",
  "gear_gillnet",
  "gear_purse_seine", "gear_seine",
  "gear_trap", "gear_dredge",
  "gear_net_other", "gear_harpoon",
  "gear_artisanal", "gear_survey"
)

# Keep only those that exist in validated gear_type_cols
gear_focus <- gear_order[gear_order %in% gear_type_cols]
cat("Gear types used:", paste(gear_focus, collapse = ", "), "\n")

d4_data <- map_dfr(gear_focus, function(gcol) {
  g_bin   <- df[[gcol]]
  mit_any <- df |>
    select(all_of(mit_cols)) |>
    rowSums(na.rm = TRUE)
  tibble(
    gear_col = gcol,
    gear     = clean_name(gcol),
    total    = sum(g_bin == 1, na.rm = TRUE),
    with_mit = sum(g_bin == 1 & mit_any >= 1, na.rm = TRUE)
  )
}) |>
  filter(total > 0) |>
  mutate(pct_mit = 100 * with_mit / total)

# Enforce the specified gear order using factor levels.
# gear_focus is already in the desired order; those with total == 0 were dropped.
# Reverse for coord_flip so the first item in gear_order appears at the top.
ordered_gear_labels <- rev(clean_name(gear_focus[gear_focus %in% d4_data$gear_col]))
d4_data <- d4_data |>
  mutate(gear = factor(gear, levels = ordered_gear_labels))

p_d4 <- d4_data |>
  pivot_longer(c(total, with_mit), names_to = "type", values_to = "count") |>
  mutate(type = recode(type,
                       total    = "All papers mentioning gear",
                       with_mit = "Papers with mitigation research")) |>
  ggplot(aes(x = gear, y = count, fill = type)) +
  geom_col(position = "identity", alpha = 0.85) +
  scale_fill_manual(values = c(
    "All papers mentioning gear"      = "#92c5de",
    "Papers with mitigation research" = "#0571b0"
  ), name = NULL) +
  geom_text(
    data = d4_data,
    aes(x = gear, y = total + max(total) * 0.015,
        label = paste0(round(pct_mit, 1), "%")),
    inherit.aes = FALSE, size = 3.2, hjust = 0
  ) +
  coord_flip() +
  labs(
    title    = "Mitigation research coverage by gear type",
    subtitle = "Blue bars = papers also including any gear_mit_* column; % = proportion with mitigation",
    x = NULL, y = "Number of papers"
  ) +
  theme_eea +
  theme(
    axis.text.x     = element_text(angle = 0, hjust = 0.5),
    legend.position = "bottom"
  )

save_plot(p_d4, "D4_bars_mitigation_gaps", w = 12, h = 8)

cat("\nAll 5 fixes complete.\n")
