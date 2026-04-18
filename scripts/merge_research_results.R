#!/usr/bin/env Rscript
# ============================================================================
# Merge subagent research results back into the name-issues XLSX.
#
# For each row where the agent returned HIGH confidence AND a non-empty
# verified first/last, push to outputs/author_name_corrections.csv and
# drop the row from the XLSX (it's resolved).
#
# MED confidence → update suggested_first_name / suggested_last_name in the
# XLSX but keep the row there for human review. Agent reasoning goes into
# the notes column (appended, not replacing).
#
# LOW confidence / blank verified → no change to suggestions, but append
# agent reasoning to notes.
# ============================================================================

suppressPackageStartupMessages({
  library(tidyverse)
  library(openxlsx)
})

setwd("/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel")

# Load all 5 result CSVs (agents wrote them with varying quality)
res_files <- list.files("outputs", pattern = "\\.research_results_[1-5]\\.csv",
                        full.names = TRUE, all.files = TRUE)
cat(sprintf("Loading %d result files: %s\n", length(res_files),
            paste(basename(res_files), collapse = ", ")))

all_res <- res_files |>
  map_dfr(~ read_csv(.x, show_col_types = FALSE, col_types = cols(.default = "c"))) |>
  mutate(
    verified_first = ifelse(is.na(verified_first) | verified_first == "", NA_character_, verified_first),
    verified_last  = ifelse(is.na(verified_last)  | verified_last  == "", NA_character_, verified_last)
  ) |>
  distinct(openalex_author_id, .keep_all = TRUE)

cat(sprintf("Total results: %d\n", nrow(all_res)))
cat("By confidence:\n"); print(table(all_res$confidence, useNA = "always"))
cat(sprintf("  with verified name: %d\n",
            sum(!is.na(all_res$verified_first) | !is.na(all_res$verified_last))))

# --- Load current XLSX -----------------------------------------------------
xlsx_path <- "outputs/author_name_issues.xlsx"
xlsx      <- read.xlsx(xlsx_path)

# Back it up first
BACKUP_DIR <- "outputs/.backups"
dir.create(BACKUP_DIR, showWarnings = FALSE, recursive = TRUE)
stamp <- format(Sys.time(), "%Y%m%d_%H%M%S")
dest <- file.path(BACKUP_DIR,
                  sprintf("author_name_issues_before_research_merge_%s.xlsx", stamp))
file.copy(xlsx_path, dest, overwrite = FALSE)
cat(sprintf("Backed up XLSX to %s\n", dest))

# --- Extract HIGH-confidence merges → corrections --------------------------
high <- all_res |>
  filter(confidence == "HIGH",
         !is.na(verified_first) | !is.na(verified_last))
cat(sprintf("HIGH-confidence rows to push to corrections: %d\n", nrow(high)))

if (nrow(high) > 0) {
  new_corr <- high |>
    transmute(
      openalex_author_id,
      corrected_first_name = verified_first,
      corrected_last_name  = verified_last,
      confidence = "HIGH",
      source = sprintf("subagent: %s", source),
      notes = reasoning
    )

  corr_path <- "outputs/author_name_corrections.csv"
  existing <- if (file.exists(corr_path)) {
    read_csv(corr_path, show_col_types = FALSE)
  } else tibble()
  merged <- bind_rows(existing, new_corr) |>
    distinct(openalex_author_id, .keep_all = TRUE)
  write_csv(merged, corr_path)
  cat(sprintf("  Total corrections in %s: %d\n", corr_path, nrow(merged)))

  # Remove resolved rows from the XLSX
  xlsx <- xlsx |> filter(!openalex_author_id %in% high$openalex_author_id)
}

# --- Apply MED updates to remaining XLSX rows ------------------------------
med <- all_res |>
  filter(confidence == "MED",
         !is.na(verified_first) | !is.na(verified_last))
cat(sprintf("MED-confidence rows to update in XLSX: %d\n", nrow(med)))

xlsx <- xlsx |>
  left_join(all_res |> select(openalex_author_id,
                              v_first = verified_first,
                              v_last  = verified_last,
                              v_conf  = confidence,
                              v_src   = source,
                              v_rsn   = reasoning),
            by = "openalex_author_id") |>
  mutate(
    suggested_first_name = case_when(
      v_conf == "MED" & !is.na(v_first) ~ v_first,
      TRUE                               ~ suggested_first_name
    ),
    suggested_last_name  = case_when(
      v_conf == "MED" & !is.na(v_last)  ~ v_last,
      TRUE                               ~ suggested_last_name
    ),
    notes = case_when(
      !is.na(v_rsn) & (notes == "" | is.na(notes)) ~
        sprintf("[subagent-%s] %s (%s)", tolower(v_conf %||% "?"),
                v_rsn, v_src %||% ""),
      !is.na(v_rsn) ~
        sprintf("%s | [subagent-%s] %s (%s)", notes,
                tolower(v_conf %||% "?"), v_rsn, v_src %||% ""),
      TRUE ~ notes
    )
  ) |>
  select(-v_first, -v_last, -v_conf, -v_src, -v_rsn)

cat(sprintf("XLSX rows remaining: %d\n", nrow(xlsx)))

# --- Rewrite XLSX with hyperlinks preserved --------------------------------
wb <- createWorkbook()
addWorksheet(wb, "name_issues")
if ("openalex_url" %in% colnames(xlsx)) {
  class(xlsx$openalex_url) <- "hyperlink"
}
writeData(wb, "name_issues", xlsx)
addStyle(wb, "name_issues", createStyle(textDecoration = "bold"),
         rows = 1, cols = seq_len(ncol(xlsx)), gridExpand = TRUE)
freezePane(wb, "name_issues", firstRow = TRUE)
setColWidths(wb, "name_issues", cols = seq_len(ncol(xlsx)), widths = "auto")
addFilter(wb, "name_issues", row = 1, cols = seq_len(ncol(xlsx)))
# Colour-code confidence
hi  <- createStyle(bgFill = "#d4edda")
med_sty <- createStyle(bgFill = "#fff3cd")
lo  <- createStyle(bgFill = "#f8d7da")
cc  <- which(colnames(xlsx) == "confidence")
if (length(cc) && nrow(xlsx) > 0) {
  conditionalFormatting(wb, "name_issues", cols = cc, rows = 2:(nrow(xlsx)+1),
                        type = "contains", rule = "HIGH", style = hi)
  conditionalFormatting(wb, "name_issues", cols = cc, rows = 2:(nrow(xlsx)+1),
                        type = "contains", rule = "MED",  style = med_sty)
  conditionalFormatting(wb, "name_issues", cols = cc, rows = 2:(nrow(xlsx)+1),
                        type = "contains", rule = "LOW",  style = lo)
}
saveWorkbook(wb, xlsx_path, overwrite = TRUE)
cat(sprintf("\nWrote %s\n", xlsx_path))
cat("Done.\n")
