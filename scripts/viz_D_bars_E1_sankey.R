# viz_D_bars_E1_sankey.R
# Generates D1-D6 bar charts and E1 Sankey diagram
# for the EEA 2025 Data Panel systematic review project.

suppressPackageStartupMessages({
  library(tidyverse)
  library(patchwork)
  library(ggalluvial)
})

# ── Common setup ──────────────────────────────────────────────────────────────
base_dir <- "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
fig_dir  <- file.path(base_dir, "outputs/figures")
dir.create(fig_dir, showWarnings = FALSE, recursive = TRUE)

df <- read_csv(file.path(base_dir, "outputs/viz_data.csv"),
               show_col_types = FALSE, guess_max = 5000)
df <- df |> filter(!is.na(year), year >= 1950, year <= 2025)
n_papers <- nrow(df)
cat("Papers loaded:", n_papers, "\n")

# Schema column groups
eco_cols  <- names(df)[startsWith(names(df), "eco_") &
                         !names(df) %in% c("eco_1_guess", "eco_2_guess", "eco_3_guess")]
pr_cols   <- names(df)[startsWith(names(df), "pr_")]
gear_cols <- names(df)[startsWith(names(df), "gear_") &
                         !names(df) %in% c("gear_target_species")]
imp_cols  <- names(df)[startsWith(names(df), "imp_") &
                         !names(df) %in% c("imp_direction", "imp_quantified",
                                           "imp_is_bycatch", "imp_confidence")]
d_cols    <- names(df)[startsWith(names(df), "d_")]
b_cols    <- names(df)[startsWith(names(df), "b_")]
mit_cols      <- names(df)[startsWith(names(df), "gear_mit_")]
gear_type_cols <- setdiff(gear_cols, mit_cols)

d_main <- c("d_biology", "d_behaviour", "d_trophic", "d_genetics",
            "d_movement", "d_fisheries", "d_conservation", "d_data_science")
d_main <- d_main[d_main %in% d_cols]

clean_name <- function(x) {
  x |>
    str_remove("^(eco_|pr_|gear_mit_|gear_|imp_|d_|b_|sp_)") |>
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

# Helper: coerce a schema column to numeric 0/1
to_bin <- function(x) suppressWarnings(as.numeric(as.character(x)))

# Helper: compute prevalence long tibble for a set of columns
schema_prevalence <- function(data, cols, label) {
  data |>
    select(all_of(cols)) |>
    mutate(across(everything(), to_bin)) |>
    summarise(across(everything(), \(x) sum(x, na.rm = TRUE))) |>
    pivot_longer(everything(), names_to = "col", values_to = "n") |>
    mutate(
      pct    = 100 * n / n_papers,
      label  = clean_name(col),
      schema = label
    )
}

# ── D1. bars_schema_dashboard ─────────────────────────────────────────────────
cat("\n--- D1: Schema dashboard ---\n")

schema_colours <- c(
  "Ecosystem"  = "#1b7837",
  "Pressure"   = "#d6604d",
  "Gear type"  = "#4393c3",
  "Impact"     = "#9970ab",
  "Discipline" = "#d6b418",
  "Ocean basin"= "#74add1"
)

prev_all <- bind_rows(
  schema_prevalence(df, eco_cols,       "Ecosystem"),
  schema_prevalence(df, pr_cols,        "Pressure"),
  schema_prevalence(df, gear_type_cols, "Gear type"),
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
    title    = paste0("Schema column prevalence across ", format(n_papers, big.mark = ","), " papers"),
    subtitle = "Percentage of papers in which each column = 1",
    x = NULL, y = "% of papers"
  ) +
  theme_eea +
  theme(axis.text.x = element_text(angle = 0, hjust = 0.5))

save_plot(p_d1, "D1_bars_schema_dashboard", w = 18, h = 14)

# ── D2. bars_discipline_comparison (heatmap) ──────────────────────────────────
cat("\n--- D2: Discipline comparison heatmap ---\n")

top_n_cols <- function(data, cols, n = 5) {
  data |>
    select(all_of(cols)) |>
    mutate(across(everything(), to_bin)) |>
    summarise(across(everything(), \(x) sum(x, na.rm = TRUE))) |>
    pivot_longer(everything(), names_to = "col", values_to = "n") |>
    slice_max(n, n = n) |>
    pull(col)
}

top_pr   <- top_n_cols(df, pr_cols,        5)
top_gear <- top_n_cols(df, gear_type_cols, 5)
top_imp  <- top_n_cols(df, imp_cols,       5)
other_cols <- c(top_pr, top_gear, top_imp)

d2_long <- map_dfr(d_main, function(dcol) {
  d_bin <- to_bin(df[[dcol]])
  map_dfr(other_cols, function(ocol) {
    o_bin <- to_bin(df[[ocol]])
    tibble(
      discipline = clean_name(dcol),
      other      = clean_name(ocol),
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
    subtitle = "Cell = papers where both discipline and other column = 1",
    x = NULL, y = NULL
  ) +
  theme_eea +
  theme(axis.text.x = element_text(angle = 45, hjust = 1))

save_plot(p_d2, "D2_bars_discipline_comparison", w = 18, h = 8)

# ── D3. bars_bycatch_targets ──────────────────────────────────────────────────
cat("\n--- D3: Bycatch targets ---\n")

has_bycatch <- "imp_is_bycatch" %in% names(df)
has_target  <- "gear_target_species" %in% names(df)

if (!has_bycatch) {
  cat("  Skipping D3: imp_is_bycatch column not found in data.\n")
} else if (!has_target) {
  cat("  Skipping D3: gear_target_species column not found in data.\n")
} else {
  bycatch_df <- df |>
    filter(to_bin(imp_is_bycatch) == 1 | gear_target_species != "" |
             tolower(as.character(imp_is_bycatch)) == "true") |>
    filter(!is.na(gear_target_species), gear_target_species != "") |>
    count(gear_target_species, name = "n") |>
    slice_max(n, n = 15) |>
    mutate(gear_target_species = fct_reorder(gear_target_species, n))

  if (nrow(bycatch_df) == 0) {
    cat("  Skipping D3: no bycatch papers with target species labels found.\n")
  } else {
    p_d3 <- ggplot(bycatch_df, aes(x = gear_target_species, y = n)) +
      geom_col(fill = "#e08214") +
      coord_flip() +
      labs(
        title    = "Top fisheries where elasmobranchs are bycatch",
        subtitle = "Papers where imp_is_bycatch = 1, by target species/fishery",
        x = NULL, y = "Number of papers"
      ) +
      theme_eea +
      theme(axis.text.x = element_text(angle = 0, hjust = 0.5))
    save_plot(p_d3, "D3_bars_bycatch_targets", w = 12, h = 8)
  }
}

# ── D4. bars_mitigation_gaps ──────────────────────────────────────────────────
cat("\n--- D4: Mitigation gaps ---\n")

gear_focus <- intersect(
  c("gear_longline", "gear_gillnet", "gear_trawl", "gear_purse_seine",
    "gear_hook_line", "gear_trap", "gear_seine", "gear_dredge"),
  gear_type_cols
)

d4_data <- map_dfr(gear_focus, function(gcol) {
  g_bin   <- to_bin(df[[gcol]])
  mit_any <- df |>
    select(all_of(mit_cols)) |>
    mutate(across(everything(), to_bin)) |>
    rowSums(na.rm = TRUE)
  tibble(
    gear          = clean_name(gcol),
    total         = sum(g_bin == 1, na.rm = TRUE),
    with_mit      = sum(g_bin == 1 & mit_any >= 1, na.rm = TRUE)
  )
}) |>
  filter(total > 0) |>
  mutate(
    pct_mit = 100 * with_mit / total,
    gear    = fct_reorder(gear, pct_mit)
  )

p_d4 <- d4_data |>
  pivot_longer(c(total, with_mit), names_to = "type", values_to = "count") |>
  mutate(type = recode(type,
                       total    = "All papers mentioning gear",
                       with_mit = "Papers with mitigation research")) |>
  ggplot(aes(x = gear, y = count, fill = type)) +
  geom_col(position = "identity", alpha = 0.85) +
  scale_fill_manual(values = c(
    "All papers mentioning gear"    = "#92c5de",
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
    subtitle = "Blue bars = papers also including any gear_mit_* column; % label = proportion with mitigation",
    x = NULL, y = "Number of papers"
  ) +
  theme_eea +
  theme(
    axis.text.x   = element_text(angle = 0, hjust = 0.5),
    legend.position = "bottom"
  )

save_plot(p_d4, "D4_bars_mitigation_gaps", w = 12, h = 8)

# ── D5. bars_basin_discipline_balance ─────────────────────────────────────────
cat("\n--- D5: Basin-discipline balance ---\n")

d5_long <- map_dfr(b_cols, function(bcol) {
  b_bin <- to_bin(df[[bcol]])
  map_dfr(d_main, function(dcol) {
    d_bin <- to_bin(df[[dcol]])
    tibble(
      basin      = clean_name(bcol),
      discipline = clean_name(dcol),
      count      = sum(b_bin == 1 & d_bin == 1, na.rm = TRUE)
    )
  })
}) |>
  group_by(basin) |>
  mutate(
    basin_total = sum(count),
    pct         = 100 * count / pmax(basin_total, 1)
  ) |>
  ungroup() |>
  mutate(
    basin      = fct_reorder(basin, basin_total, .desc = TRUE),
    discipline = fct_reorder(discipline, count, sum)
  )

pal_disc <- c(
  "#1b7837", "#4dac26", "#a6d96a", "#d9ef8b",
  "#fee08b", "#fdae61", "#f46d43", "#d73027"
)[seq_along(d_main)]
names(pal_disc) <- sort(unique(d5_long$discipline))

p_d5 <- ggplot(d5_long, aes(x = discipline, y = pct, fill = discipline)) +
  geom_col(show.legend = FALSE) +
  coord_flip() +
  facet_wrap(~basin, scales = "free_x", ncol = 3) +
  scale_fill_manual(values = pal_disc) +
  labs(
    title    = "Research discipline balance by ocean basin",
    subtitle = "% of basin papers (papers can appear in multiple basins/disciplines)",
    x = NULL, y = "% of basin papers"
  ) +
  theme_eea +
  theme(axis.text.x = element_text(angle = 0, hjust = 0.5))

save_plot(p_d5, "D5_bars_basin_discipline_balance", w = 16, h = 12)

# ── D6. bars_gender_summary ───────────────────────────────────────────────────
cat("\n--- D6: Gender summary ---\n")

gender_col <- intersect(c("gender_first_author", "first_author_gender",
                          "author_gender"), names(df))

if (length(gender_col) == 0) {
  cat("  Skipping D6: no gender_first_author column found in viz_data.csv.\n")
  cat("  (Gender data lives in outputs/openalex_unique_authors.csv — not yet merged into viz_data.)\n")
} else {
  gc <- gender_col[1]
  gender_df <- df |>
    filter(!is.na(.data[[gc]])) |>
    mutate(
      gender = tolower(as.character(.data[[gc]])),
      gender = case_when(
        gender %in% c("male", "m")    ~ "Male",
        gender %in% c("female", "f")  ~ "Female",
        TRUE                           ~ "Unknown"
      ),
      year_bin = floor(year / 5) * 5
    )

  # Overall bar
  overall <- gender_df |> count(gender) |> mutate(gender = fct_reorder(gender, -n))

  gender_cols <- c(Male = "#4393c3", Female = "#e91e8d", Unknown = "#aaaaaa")

  # % of each gender per 5-year bin
  trend <- gender_df |>
    count(year_bin, gender) |>
    group_by(year_bin) |>
    mutate(total = sum(n), pct = 100 * n / total) |>
    ungroup()

  # Overall averages for horizontal reference lines
  avg <- gender_df |>
    count(gender) |>
    mutate(pct = 100 * n / sum(n))

  p_d6a <- ggplot(overall, aes(x = gender, y = n, fill = gender)) +
    geom_col(show.legend = FALSE) +
    geom_text(aes(label = scales::comma(n)), vjust = -0.5, size = 3.5) +
    scale_fill_manual(values = gender_cols) +
    scale_y_continuous(expand = expansion(mult = c(0, 0.1))) +
    labs(title = "Gender counts", x = NULL, y = "Number of papers") +
    theme_eea +
    theme(axis.text.x = element_text(angle = 0, hjust = 0.5))

  p_d6b <- ggplot(trend, aes(x = year_bin, y = pct, colour = gender, group = gender)) +
    geom_hline(data = avg, aes(yintercept = pct, colour = gender),
               linetype = "dashed", linewidth = 0.7, show.legend = FALSE) +
    geom_line(linewidth = 1.2) +
    geom_point(aes(size = n)) +
    scale_colour_manual(values = gender_cols) +
    scale_size_continuous(range = c(1.5, 5), name = "Papers") +
    scale_y_continuous(labels = scales::percent_format(scale = 1)) +
    labs(title = "Trend over time", x = "Year (5-year bins)",
         y = "% first author") +
    theme_eea +
    guides(colour = guide_legend(title = "Gender"))

  p_d6 <- (p_d6a | p_d6b) +
    plot_annotation(
      title    = "First author gender in elasmobranch research",
      subtitle = "Left: total counts | Right: % by 5-year period"
    ) +
    plot_layout(widths = c(1, 2))
  save_plot(p_d6, "D6_bars_gender_summary", w = 14, h = 6)
}

# ── E1. sankey_fishery_flow ────────────────────────────────────────────────────
cat("\n--- E1: Sankey gear → pressure → impact ---\n")

top5_gear <- top_n_cols(df, gear_type_cols, 5)
top5_pr   <- top_n_cols(df, pr_cols,        5)
top5_imp  <- top_n_cols(df, imp_cols,       5)

# Build per-paper long form for each axis
gear_long <- df |>
  mutate(row_id = row_number()) |>
  select(row_id, all_of(top5_gear)) |>
  mutate(across(-row_id, to_bin)) |>
  pivot_longer(-row_id, names_to = "gear_col", values_to = "g") |>
  filter(g == 1)

pr_long <- df |>
  mutate(row_id = row_number()) |>
  select(row_id, all_of(top5_pr)) |>
  mutate(across(-row_id, to_bin)) |>
  pivot_longer(-row_id, names_to = "pr_col", values_to = "p") |>
  filter(p == 1)

imp_long <- df |>
  mutate(row_id = row_number()) |>
  select(row_id, all_of(top5_imp)) |>
  mutate(across(-row_id, to_bin)) |>
  pivot_longer(-row_id, names_to = "imp_col", values_to = "i") |>
  filter(i == 1)

# All gear × pressure × impact combinations per paper, then aggregate
sankey_df <- gear_long |>
  inner_join(pr_long,  by = "row_id", relationship = "many-to-many") |>
  inner_join(imp_long, by = "row_id", relationship = "many-to-many") |>
  count(gear_col, pr_col, imp_col, name = "freq") |>
  mutate(
    Gear     = clean_name(gear_col),
    Pressure = clean_name(pr_col),
    Impact   = clean_name(imp_col)
  ) |>
  select(Gear, Pressure, Impact, freq) |>
  filter(freq >= 5)   # drop very sparse combinations for readability

cat("  Sankey rows after filtering:", nrow(sankey_df), "\n")

if (nrow(sankey_df) == 0) {
  cat("  Skipping E1: no combinations with freq >= 5 found.\n")
} else {
  alluv_df <- sankey_df |>
    to_lodes_form(axes = 1:3, key = "axis", value = "stratum", id = "alluvium") |>
    mutate(axis_label = recode(axis,
                               "1" = "Gear type",
                               "2" = "Pressure",
                               "3" = "Impact"))

  n_strata <- length(unique(alluv_df$stratum))
  pal_sankey <- scales::hue_pal()(n_strata)

  p_e1 <- ggplot(alluv_df,
                 aes(x = axis_label, stratum = stratum, alluvium = alluvium,
                     y = freq, fill = stratum, label = stratum)) +
    geom_alluvium(alpha = 0.55, width = 1/4) +
    geom_stratum(width = 1/4, colour = "white") +
    geom_text(stat = "stratum", size = 3, fontface = "bold") +
    scale_fill_manual(values = setNames(pal_sankey, unique(alluv_df$stratum))) +
    scale_x_discrete(expand = c(0.05, 0.05)) +
    labs(
      title    = "Research flow: Gear -> Pressure -> Impact",
      subtitle = "Each flow = papers with that gear x pressure x impact combination (top 5 per axis, freq >= 5)",
      x = NULL, y = "Number of papers"
    ) +
    guides(fill = "none") +
    theme_eea +
    theme(axis.text.x = element_text(angle = 0, hjust = 0.5, size = 13, face = "bold"))

  save_plot(p_e1, "E1_sankey_fishery_flow", w = 16, h = 11)
}

cat("\nAll visualisations complete.\n")
