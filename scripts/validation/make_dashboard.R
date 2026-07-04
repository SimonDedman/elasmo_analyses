#!/usr/bin/env Rscript
# Per-column precision/recall bars (worst-first) + before/after improvement.
#
# Inputs (outputs/validation/):
#   metrics.parquet       -- written by scripts/validation/score.py::run();
#                            columns: column, tp, fp, fn, tn, precision,
#                            recall, f1, set (set in
#                            {silver_rules_vs_fable, gold_rules_vs_human}).
#   improvement_log.csv   -- written by scripts/validation/autotest_rules.py;
#                            columns include column, change_type,
#                            silver_f1_before, silver_f1_after,
#                            gold_f1_after, accepted.
#
# Outputs (outputs/validation/figures/):
#   per_column_pr.png     -- precision/recall per column, worst (lowest
#                            mean precision+recall) at the top after
#                            coord_flip().
#   improvement.png       -- before -> after macro-F1 per column touched by
#                            the rule-improvement loop; if the log is empty
#                            (no changes proposed/accepted yet), fall back
#                            to copying per_column_pr.png so the dashboard
#                            still has two images.
suppressMessages({
  library(arrow)
  library(ggplot2)
  library(dplyr)
  library(tidyr)
})

out <- "outputs/validation"
dir.create(file.path(out, "figures"), showWarnings = FALSE, recursive = TRUE)

m <- read_parquet(file.path(out, "metrics.parquet")) |>
  filter(set == "silver_rules_vs_fable")

pr <- m |>
  select(column, precision, recall) |>
  pivot_longer(-column) |>
  filter(!is.na(value)) |>
  group_by(column) |>
  mutate(ord = mean(value)) |>
  ungroup()

ggplot(pr, aes(reorder(column, ord), value, fill = name)) +
  geom_col(position = "dodge") +
  coord_flip() +
  scale_fill_manual(values = c(precision = "#2166AC", recall = "#B2182B")) +
  labs(
    x = NULL, y = NULL, fill = NULL,
    title = "Rule extractor: precision & recall per column (vs Fable silver)"
  ) +
  theme_minimal(base_size = 9)
ggsave(file.path(out, "figures/per_column_pr.png"), width = 8, height = 11, dpi = 150)

imp <- read.csv(file.path(out, "improvement_log.csv"))
if (nrow(imp) > 0) {
  impl <- imp |>
    select(column, silver_f1_before, silver_f1_after) |>
    pivot_longer(-column, names_to = "stage", values_to = "f1")

  ggplot(impl, aes(reorder(column, f1), f1, colour = stage, group = column)) +
    geom_line(colour = "grey70") +
    geom_point(size = 2) +
    coord_flip() +
    scale_colour_manual(values = c(
      silver_f1_before = "grey50",
      silver_f1_after = "#1B7837"
    )) +
    labs(
      x = NULL, y = "macro F1", colour = NULL,
      title = "Rule improvement: before -> after"
    ) +
    theme_minimal(base_size = 9)
  ggsave(file.path(out, "figures/improvement.png"), width = 8, height = 6, dpi = 150)
} else {
  file.copy(
    file.path(out, "figures/per_column_pr.png"),
    file.path(out, "figures/improvement.png"),
    overwrite = TRUE
  )
}

cat("figures written\n")
