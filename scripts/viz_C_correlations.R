library(tidyverse)
library(corrplot)

base_dir <- "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
fig_dir <- file.path(base_dir, "outputs/figures")
df <- read_csv(file.path(base_dir, "outputs/viz_data.csv"), show_col_types = FALSE, guess_max = 5000)
df <- df |> filter(!is.na(year), year >= 1950, year <= 2025)

d_cols <- names(df)[startsWith(names(df), "d_") & !grepl("\\.\\.\\.", names(df))]
pr_cols <- names(df)[startsWith(names(df), "pr_") & !grepl("\\.\\.\\.", names(df))]

# Exclude non-binary imp_ columns and duplicate-renamed columns (contain "...")
imp_candidate <- names(df)[
  startsWith(names(df), "imp_") &
  !grepl("\\.\\.\\.", names(df)) &
  !names(df) %in% c("imp_direction", "imp_quantified", "imp_is_bycatch", "imp_confidence")
]
imp_cols <- imp_candidate[
  sapply(imp_candidate, function(col) {
    v <- df[[col]]
    is.numeric(v) && all(v %in% c(0, 1, NA))
  })
]

mit_cols <- names(df)[startsWith(names(df), "gear_mit_") & !grepl("\\.\\.\\.", names(df))]
gear_type_cols <- names(df)[
  startsWith(names(df), "gear_") &
  !grepl("\\.\\.\\.", names(df)) &
  !names(df) %in% c("gear_target_species") &
  !startsWith(names(df), "gear_mit_")
]

clean_name <- function(x) {
  x |> str_remove("^(eco_|pr_|gear_|imp_|d_|b_|sp_|gear_mit_)") |>
    str_replace_all("_", " ") |> str_to_title()
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
  ggsave(file.path(fig_dir, paste0(name, ".png")), p, width = w, height = h, dpi = 300, bg = "white")
  ggsave(file.path(fig_dir, paste0(name, ".pdf")), p, width = w, height = h, bg = "white")
  cat("Saved:", name, "\n")
}

# Phi coefficient helper
phi_coef <- function(x, y) {
  tab <- table(factor(x, levels = c(0, 1)), factor(y, levels = c(0, 1)))
  n <- sum(tab)
  if (n == 0) return(0)
  # Cast all cells to numeric before multiplication to prevent integer overflow
  a <- as.numeric(tab[1, 1]); b <- as.numeric(tab[1, 2])
  cc <- as.numeric(tab[2, 1]); d <- as.numeric(tab[2, 2])
  denom <- sqrt((d + b) * (d + cc) * (a + b) * (a + cc))
  if (!is.finite(denom) || denom == 0) return(0)
  (d * a - b * cc) / denom
}

# ── C1 ──────────────────────────────────────────────────────────────────────
cat("C1 skipped: GDP data not yet integrated\n")

# ── C2. Discipline co-occurrence (phi coefficient) ───────────────────────────
cat("Building C2: discipline co-occurrence heatmap...\n")

disc8 <- c("d_biology", "d_behaviour", "d_trophic", "d_genetics",
           "d_movement", "d_fisheries", "d_conservation", "d_data_science")
disc8 <- disc8[disc8 %in% names(df)]

disc_mat <- df |> select(all_of(disc8)) |> as.matrix()
disc_mat[is.na(disc_mat)] <- 0

n_d <- length(disc8)
phi_d <- matrix(0, nrow = n_d, ncol = n_d,
                dimnames = list(disc8, disc8))
for (i in seq_len(n_d)) {
  for (j in seq_len(n_d)) {
    val <- phi_coef(disc_mat[, i], disc_mat[, j])
    phi_d[i, j] <- if (!is.finite(val)) 0 else val
  }
}

phi_d_long <- as.data.frame(phi_d) |>
  rownames_to_column("row_var") |>
  pivot_longer(-row_var, names_to = "col_var", values_to = "phi") |>
  mutate(
    row_label = clean_name(row_var),
    col_label = clean_name(col_var),
    row_label = factor(row_label, levels = clean_name(disc8)),
    col_label = factor(col_label, levels = clean_name(disc8))
  )

p_c2 <- ggplot(phi_d_long, aes(x = col_label, y = row_label, fill = phi)) +
  geom_tile(colour = "white", linewidth = 0.5) +
  geom_text(aes(label = sprintf("%.2f", phi)), size = 3.2, colour = "black") +
  scale_fill_gradient2(
    low = "#2166ac", mid = "white", high = "#d6604d",
    midpoint = 0, limits = c(-1, 1),
    name = "Phi"
  ) +
  labs(
    title = "Discipline co-occurrence (phi coefficient)",
    subtitle = "Phi correlation between pairs of discipline binary flags",
    x = NULL, y = NULL
  ) +
  theme_eea +
  theme(axis.text.y = element_text(angle = 0, hjust = 1))

save_plot(p_c2, "C2_corr_discipline_cooccurrence", w = 10, h = 9)

# ── C3. Pressure × impact correlation ───────────────────────────────────────
cat("Building C3: pressure × impact heatmap...\n")

# Filter to variables with >50 positive papers
pr_keep  <- pr_cols[colSums(df[pr_cols],  na.rm = TRUE) > 50]
imp_keep <- imp_cols[colSums(df[imp_cols], na.rm = TRUE) > 50]

pr_mat  <- df |> select(all_of(pr_keep))  |> as.matrix()
imp_mat <- df |> select(all_of(imp_keep)) |> as.matrix()
pr_mat[is.na(pr_mat)]   <- 0
imp_mat[is.na(imp_mat)] <- 0

phi_pi <- matrix(0, nrow = length(pr_keep), ncol = length(imp_keep),
                 dimnames = list(pr_keep, imp_keep))
for (i in seq_along(pr_keep)) {
  for (j in seq_along(imp_keep)) {
    val <- phi_coef(pr_mat[, i], imp_mat[, j])
    phi_pi[i, j] <- if (!is.finite(val)) 0 else val
  }
}

phi_pi_long <- as.data.frame(phi_pi) |>
  rownames_to_column("pressure") |>
  pivot_longer(-pressure, names_to = "impact", values_to = "phi") |>
  mutate(
    pr_label  = factor(clean_name(pressure), levels = clean_name(pr_keep)),
    imp_label = factor(clean_name(impact),   levels = clean_name(imp_keep))
  )

p_c3 <- ggplot(phi_pi_long, aes(x = imp_label, y = pr_label, fill = phi)) +
  geom_tile(colour = "white", linewidth = 0.3) +
  scale_fill_gradient2(
    low = "#2166ac", mid = "white", high = "#d6604d",
    midpoint = 0, limits = c(-1, 1),
    name = "Phi"
  ) +
  labs(
    title    = "Pressure \u00d7 impact correlation",
    subtitle = "Phi coefficient; variables with >50 papers shown",
    x = "Impact", y = "Pressure"
  ) +
  theme_eea +
  theme(axis.text.y = element_text(angle = 0, hjust = 1))

save_plot(p_c3, "C3_corr_pressure_impact", w = 16, h = 12)

# ── C4. Gear type × mitigation measure correlation ───────────────────────────
cat("Building C4: gear type × mitigation heatmap...\n")

gear7 <- c("gear_longline", "gear_gillnet", "gear_trawl",
           "gear_purse_seine", "gear_hook_line", "gear_trap", "gear_seine")
gear7 <- gear7[gear7 %in% names(df)]

g_mat   <- df |> select(all_of(gear7))   |> as.matrix()
mit_mat <- df |> select(all_of(mit_cols)) |> as.matrix()
g_mat[is.na(g_mat)]     <- 0
mit_mat[is.na(mit_mat)] <- 0

phi_gm <- matrix(0, nrow = length(gear7), ncol = length(mit_cols),
                 dimnames = list(gear7, mit_cols))
for (i in seq_along(gear7)) {
  for (j in seq_along(mit_cols)) {
    val <- phi_coef(g_mat[, i], mit_mat[, j])
    phi_gm[i, j] <- if (!is.finite(val)) 0 else val
  }
}

phi_gm_long <- as.data.frame(phi_gm) |>
  rownames_to_column("gear") |>
  pivot_longer(-gear, names_to = "mitigation", values_to = "phi") |>
  mutate(
    gear_label = factor(clean_name(gear),       levels = clean_name(gear7)),
    mit_label  = factor(clean_name(mitigation), levels = clean_name(mit_cols))
  )

p_c4 <- ggplot(phi_gm_long, aes(x = mit_label, y = gear_label, fill = phi)) +
  geom_tile(colour = "white", linewidth = 0.5) +
  geom_text(aes(label = sprintf("%.2f", phi)), size = 3, colour = "black") +
  scale_fill_gradient2(
    low = "#2166ac", mid = "white", high = "#d6604d",
    midpoint = 0, limits = c(-1, 1),
    name = "Phi"
  ) +
  labs(
    title    = "Gear type \u00d7 mitigation measure correlation",
    subtitle = "Phi coefficient between gear type and mitigation measure binary flags",
    x = "Mitigation measure", y = "Gear type"
  ) +
  theme_eea +
  theme(axis.text.y = element_text(angle = 0, hjust = 1))

save_plot(p_c4, "C4_corr_gear_mitigation", w = 14, h = 7)

# ── C5. Female first authorship by discipline ────────────────────────────────
if ("gender_first_author" %in% names(df)) {
  cat("Building C5: female first authorship by discipline...\n")

  disc_all <- d_cols

  gender_disc <- map_dfr(disc_all, function(col) {
    sub_df <- df |>
      filter(.data[[col]] == 1, !is.na(gender_first_author))
    if (nrow(sub_df) < 10) return(NULL)
    tibble(
      discipline  = col,
      n_total     = nrow(sub_df),
      n_female    = sum(str_detect(sub_df$gender_first_author, regex("female", ignore_case = TRUE)), na.rm = TRUE),
      pct_female  = 100 * n_female / n_total
    )
  }) |>
    arrange(pct_female) |>
    mutate(disc_label = factor(clean_name(discipline), levels = clean_name(discipline)))

  overall_pct <- 100 * mean(
    str_detect(df$gender_first_author[!is.na(df$gender_first_author)],
               regex("female", ignore_case = TRUE))
  )

  p_c5 <- ggplot(gender_disc, aes(x = pct_female, y = disc_label, size = n_total)) +
    geom_vline(xintercept = overall_pct, linetype = "dashed", colour = "grey50") +
    geom_point(colour = "#d6604d", alpha = 0.85) +
    scale_size_continuous(name = "Papers", range = c(3, 12)) +
    annotate("text", x = overall_pct + 0.5, y = 1.3,
             label = sprintf("Overall: %.1f%%", overall_pct),
             hjust = 0, colour = "grey40", size = 3.5) +
    scale_x_continuous(limits = c(0, NA), labels = function(x) paste0(x, "%")) +
    labs(
      title    = "Female first authorship by discipline",
      subtitle = "Proportion of papers with female first author; dot size = total papers. Dashed line = overall average.",
      x = "% female first author", y = NULL
    ) +
    theme_eea +
    theme(axis.text.x = element_text(angle = 0, hjust = 0.5),
          axis.text.y = element_text(angle = 0, hjust = 1))

  save_plot(p_c5, "C5_corr_gender_discipline", w = 12, h = 8)
} else {
  cat("C5 skipped: gender_first_author column not found in viz_data.csv\n")
}

cat("viz_C_correlations.R complete.\n")
