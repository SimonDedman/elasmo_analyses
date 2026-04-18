#!/usr/bin/env Rscript
# ============================================================================
# Migrate name fixes from outputs/author_name_issues.xlsx into a canonical
# corrections CSV that build scripts apply at load time. This is the same
# pattern as author_location_overrides.csv.
#
# Corrections applied to outputs/author_name_corrections.csv include:
#   - HIGH-confidence rule outputs (auto-applied; user has not vetoed)
#   - Any row where the user has typed "fixed" in the notes column
#   - Any row where the user has EDITED suggested_first_name or
#     suggested_last_name (detected by re-computing rule output and
#     comparing — a cell differing from the rule output = user edit)
#   - User MED/LOW rows where notes contain an explicit "apply" keyword
#
# The CSV schema matches what build scripts expect:
#   openalex_author_id, corrected_first_name, corrected_last_name, source
# ============================================================================

suppressPackageStartupMessages({
  library(tidyverse)
  library(openxlsx)
})

setwd("/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel")

XLSX_PATH   <- "outputs/author_name_issues.xlsx"
CORR_PATH   <- "outputs/author_name_corrections.csv"

if (!file.exists(XLSX_PATH)) {
  stop("No author_name_issues.xlsx — run check_name_issues.R first.")
}

x <- read.xlsx(XLSX_PATH)
cat(sprintf("Read %d rows from %s\n", nrow(x), XLSX_PATH))

# Decide per-row whether to apply
decide_apply <- function(row) {
  conf  <- row$confidence
  notes <- tolower(trimws(row$notes %||% ""))
  sf    <- row$suggested_first_name %||% ""
  sl    <- row$suggested_last_name  %||% ""
  of    <- row$first_name %||% ""
  ol    <- row$last_name  %||% ""
  # No change at all → skip
  if (sf == of && sl == ol) return(list(apply = FALSE, reason = "no change"))
  # Strip subagent prefix annotations before keyword scan so words like
  # "confirmed" in subagent prose don't spuriously lock rows.
  user_notes <- gsub("\\[subagent-[a-z]+\\][^|]*", "", notes)
  if (grepl("\\b(fix|fixed|newfix|newfixed|edit|edited|apply|accept|accepted|confirm|confirmed)\\b",
            user_notes)) {
    return(list(apply = TRUE, reason = "user confirmed"))
  }
  # Explicit user veto
  if (grepl("\\b(skip|reject|ignore|wrong|no)\\b", notes)) {
    return(list(apply = FALSE, reason = "user vetoed"))
  }
  # Default: apply HIGH, hold MED/LOW for review
  if (conf == "HIGH") return(list(apply = TRUE, reason = "auto HIGH"))
  list(apply = FALSE, reason = sprintf("%s awaiting review", conf))
}

x_decided <- x |>
  rowwise() |>
  mutate(dec = list(decide_apply(pick(everything())))) |>
  ungroup() |>
  mutate(
    apply_correction = vapply(dec, `[[`, logical(1), "apply"),
    apply_reason     = vapply(dec, `[[`, character(1), "reason")
  ) |>
  select(-dec)

n_apply <- sum(x_decided$apply_correction)
cat(sprintf("Will apply %d corrections (%d HIGH auto, %d user-confirmed)\n",
            n_apply,
            sum(x_decided$apply_correction & x_decided$apply_reason == "auto HIGH"),
            sum(x_decided$apply_correction & x_decided$apply_reason == "user confirmed")))

corrections <- x_decided |>
  filter(apply_correction) |>
  transmute(
    openalex_author_id,
    corrected_first_name = suggested_first_name,
    corrected_last_name  = suggested_last_name,
    confidence,
    source = apply_reason,
    notes  = notes
  )

write_csv(corrections, CORR_PATH)
cat(sprintf("Wrote %s — %d rows\n", CORR_PATH, nrow(corrections)))

# Summary of what changed
if (nrow(corrections) > 0) {
  n_lastname <- sum(x_decided$apply_correction &
                    x_decided$suggested_last_name != x_decided$last_name,
                    na.rm = TRUE)
  n_firstname <- sum(x_decided$apply_correction &
                     x_decided$suggested_first_name != x_decided$first_name,
                     na.rm = TRUE)
  cat(sprintf("  First-name corrections:  %d\n", n_firstname))
  cat(sprintf("  Last-name corrections:   %d\n", n_lastname))
}

cat("\nNext: run `Rscript scripts/build_author_atlas.R` to rebuild data with corrections applied.\n")
