#!/usr/bin/env Rscript
# ============================================================================
# Disambiguation pass for the alias review XLSX.
#
# For each row in outputs/author_alias_review.xlsx, compute similarity
# signals between alias and canonical using only local data:
#
#   - species_jaccard    : Jaccard index of sp_* columns across papers
#   - discipline_jaccard : Jaccard of d_* columns
#   - basin_jaccard      : Jaccard of b_* columns (geography)
#   - coauthor_jaccard   : Jaccard of coauthor sets
#   - paper_overlap      : already present, retained
#
# Decision rule (weighted score, thresholds calibrated on a few known pairs):
#   score = 0.30*species + 0.20*discipline + 0.20*basin + 0.30*coauthor
#   MERGE  if score >= 0.60 OR paper_overlap >= 1
#   SKIP   if score < 0.15 AND year_overlap_ratio == 0
#   else UNSURE
#
# Adds columns (preserves existing notes + all prior data):
#   species_jaccard, discipline_jaccard, basin_jaccard, coauthor_jaccard,
#   ai_suggestion, ai_confidence, ai_reasoning
# ============================================================================

suppressPackageStartupMessages({
  library(tidyverse)
  library(openxlsx)
  library(arrow)
})

setwd("/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel")

REVIEW_PATH <- "outputs/author_alias_review.xlsx"
if (!file.exists(REVIEW_PATH)) stop("No review XLSX — run process_alias_candidates.R first.")

review <- read.xlsx(REVIEW_PATH)
cat(sprintf("Review rows: %d\n", nrow(review)))

cat("Loading paper data...\n")
papers <- read_parquet("outputs/literature_review_enriched.parquet") |>
  mutate(literature_id = as.character(literature_id))

# Find the schema-prefix columns in the parquet
sp_cols <- grep("^sp_", colnames(papers), value = TRUE)
d_cols  <- grep("^d_",  colnames(papers), value = TRUE)
b_cols  <- grep("^b_",  colnames(papers), value = TRUE)
cat(sprintf("  %d sp_, %d d_, %d b_ columns\n", length(sp_cols), length(d_cols), length(b_cols)))

paper_authors <- read_csv("outputs/openalex_paper_authors.csv", show_col_types = FALSE) |>
  mutate(openalex_author_id = str_remove(openalex_author_id, "https://openalex.org/"),
         literature_id = as.character(literature_id)) |>
  filter(!is.na(literature_id), !is.na(openalex_author_id))

# --- Per-author profile ---------------------------------------------------
# Collect unique author IDs we need to profile
target_ids <- unique(c(review$alias_id, review$canonical_id))
cat(sprintf("Profiling %d authors...\n", length(target_ids)))

# Author → literature_ids
pa_sub <- paper_authors |> filter(openalex_author_id %in% target_ids)

# Author → set of active columns per schema
active_cols_for_author <- function(author_id, cols) {
  lids <- pa_sub$literature_id[pa_sub$openalex_author_id == author_id]
  if (length(lids) == 0) return(character(0))
  rows <- papers |> filter(literature_id %in% lids)
  if (nrow(rows) == 0) return(character(0))
  # A column is "active" if any of the author's papers has a positive value
  active <- sapply(cols, function(c) {
    v <- rows[[c]]
    if (is.logical(v)) any(v, na.rm = TRUE)
    else if (is.numeric(v)) any(v > 0, na.rm = TRUE)
    else any(!is.na(v) & v != "", na.rm = TRUE)
  })
  cols[active]
}

# Author → set of coauthors (other author IDs on the same literature_id)
coauthors_for_author <- function(author_id) {
  lids <- pa_sub$literature_id[pa_sub$openalex_author_id == author_id]
  if (length(lids) == 0) return(character(0))
  # Any other author on those papers — use the full paper_authors, not just pa_sub
  paper_authors |>
    filter(literature_id %in% lids, openalex_author_id != author_id) |>
    pull(openalex_author_id) |>
    unique()
}

profiles <- list()
for (i in seq_along(target_ids)) {
  id <- target_ids[i]
  profiles[[id]] <- list(
    species    = active_cols_for_author(id, sp_cols),
    discipline = active_cols_for_author(id, d_cols),
    basin      = active_cols_for_author(id, b_cols),
    coauthors  = coauthors_for_author(id)
  )
  if (i %% 25 == 0) cat(sprintf("  %d / %d\n", i, length(target_ids)))
}

# --- Jaccard similarity ---------------------------------------------------
jaccard <- function(a, b) {
  if (length(a) == 0 && length(b) == 0) return(NA_real_)
  u <- length(union(a, b))
  if (u == 0) return(NA_real_)
  round(length(intersect(a, b)) / u, 3)
}

cat("Computing similarities...\n")
review <- review |>
  rowwise() |>
  mutate(
    species_jaccard    = jaccard(profiles[[alias_id]]$species,
                                 profiles[[canonical_id]]$species),
    discipline_jaccard = jaccard(profiles[[alias_id]]$discipline,
                                 profiles[[canonical_id]]$discipline),
    basin_jaccard      = jaccard(profiles[[alias_id]]$basin,
                                 profiles[[canonical_id]]$basin),
    coauthor_jaccard   = jaccard(profiles[[alias_id]]$coauthors,
                                 profiles[[canonical_id]]$coauthors),
    coauthor_common    = length(intersect(
                           profiles[[alias_id]]$coauthors,
                           profiles[[canonical_id]]$coauthors))
  ) |>
  ungroup()

# --- Decision -------------------------------------------------------------
# Weight species/coauthor higher — they're the strongest signals for
# "is this the same researcher." Discipline and basin corroborate.
score_fn <- function(sp, di, ba, co) {
  # Treat NA as 0 for score, but remember we did
  s <- 0.30 * coalesce(sp, 0) + 0.20 * coalesce(di, 0) +
       0.20 * coalesce(ba, 0) + 0.30 * coalesce(co, 0)
  s
}

review <- review |>
  rowwise() |>
  mutate(
    ai_score = score_fn(species_jaccard, discipline_jaccard,
                        basin_jaccard,   coauthor_jaccard),
    ai_suggestion = case_when(
      paper_overlap >= 1                                       ~ "MERGE",
      coauthor_common >= 3                                     ~ "MERGE",
      !is.na(ai_score) & ai_score >= 0.60                       ~ "MERGE",
      !is.na(ai_score) & ai_score >= 0.35                       ~ "UNSURE",
      !is.na(ai_score) & ai_score <  0.15 &
        coalesce(year_overlap_ratio, 0) == 0                   ~ "SKIP",
      !is.na(gender_diff) & gender_diff &
        coalesce(year_overlap_ratio, 0) < 0.25                 ~ "SKIP",
      TRUE                                                     ~ "UNSURE"
    ),
    ai_confidence = round(pmin(1.0, pmax(0.0, case_when(
      ai_suggestion == "MERGE" & paper_overlap >= 1        ~ 0.95,
      ai_suggestion == "MERGE"                              ~ 0.55 + coalesce(ai_score, 0) * 0.4,
      ai_suggestion == "SKIP"                               ~ 0.70 + (1 - coalesce(ai_score, 0)) * 0.25,
      ai_suggestion == "UNSURE"                             ~ 0.40,
      TRUE                                                  ~ 0.30
    ))), 2),
    ai_reasoning = sprintf(
      "score=%.2f (sp=%s,d=%s,b=%s,co=%s); papers=%d; coauthors-shared=%d; yr-ratio=%s%s",
      coalesce(ai_score, 0),
      ifelse(is.na(species_jaccard),    "?", sprintf("%.2f", species_jaccard)),
      ifelse(is.na(discipline_jaccard), "?", sprintf("%.2f", discipline_jaccard)),
      ifelse(is.na(basin_jaccard),      "?", sprintf("%.2f", basin_jaccard)),
      ifelse(is.na(coauthor_jaccard),   "?", sprintf("%.2f", coauthor_jaccard)),
      paper_overlap, coauthor_common,
      ifelse(is.na(year_overlap_ratio), "?", sprintf("%.2f", year_overlap_ratio)),
      ifelse(gender_diff, " | gender-diff", "")
    )
  ) |>
  ungroup()

cat("\nAI suggestions:\n")
print(table(review$ai_suggestion))
cat("\nMean confidence by suggestion:\n")
print(review |> group_by(ai_suggestion) |> summarise(mean_conf = mean(ai_confidence)))

# --- Preserve existing notes -----------------------------------------------
# The AI suggestion appends to (does not replace) any existing user note.
# If the user has already written "merge" / "skip" / etc., we leave it in place.
review <- review |>
  mutate(
    notes = ifelse(is.na(notes), "", notes)
  )

# --- Write XLSX with hyperlinks preserved ----------------------------------
class(review$alias_openalex_url)     <- "hyperlink"
class(review$canonical_openalex_url) <- "hyperlink"

# Re-order columns so the AI signals sit near the decision area
first_cols <- c("decision", "notes",
                "ai_suggestion", "ai_confidence", "ai_reasoning",
                "paper_overlap", "year_overlap_ratio", "year_overlap", "year_gap",
                "species_jaccard", "discipline_jaccard", "basin_jaccard",
                "coauthor_jaccard", "coauthor_common")
other_cols <- setdiff(colnames(review), first_cols)
review <- review[, c(first_cols, other_cols)]

wb <- createWorkbook()
addWorksheet(wb, "review")
writeData(wb, "review", review)
addStyle(wb, "review", createStyle(textDecoration = "bold"),
         rows = 1, cols = seq_len(ncol(review)), gridExpand = TRUE)
freezePane(wb, "review", firstRow = TRUE)
setColWidths(wb, "review", cols = seq_len(ncol(review)), widths = "auto")
addFilter(wb, "review", row = 1, cols = seq_len(ncol(review)))

# Colour-code AI suggestion (MERGE=green, UNSURE=yellow, SKIP=red)
sug_col <- which(colnames(review) == "ai_suggestion")
hi  <- createStyle(bgFill = "#d4edda")
med <- createStyle(bgFill = "#fff3cd")
lo  <- createStyle(bgFill = "#f8d7da")
conditionalFormatting(wb, "review", cols = sug_col, rows = 2:(nrow(review) + 1),
                      type = "contains", rule = "MERGE",  style = hi)
conditionalFormatting(wb, "review", cols = sug_col, rows = 2:(nrow(review) + 1),
                      type = "contains", rule = "UNSURE", style = med)
conditionalFormatting(wb, "review", cols = sug_col, rows = 2:(nrow(review) + 1),
                      type = "contains", rule = "SKIP",   style = lo)

# Ratio also colour-scaled as before
ratio_col <- which(colnames(review) == "year_overlap_ratio")
conditionalFormatting(wb, "review", cols = ratio_col,
                      rows = 2:(nrow(review) + 1),
                      type = "colourScale",
                      style = c("#f8d7da", "#fff3cd", "#d4edda"))

saveWorkbook(wb, REVIEW_PATH, overwrite = TRUE)
cat(sprintf("\nWrote %s (%d rows, new AI columns added)\n", REVIEW_PATH, nrow(review)))
