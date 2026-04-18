#!/usr/bin/env Rscript
# ============================================================================
# Alias-candidate processor with OpenAlex enrichment.
#
# Pipeline:
#   1. Build candidate pairs from openalex_unique_authors.csv (surname +
#      first-letter match with an initials-only alias).
#   2. Enrich each author ID from the OpenAlex API (cached) so every row
#      carries affiliation, year range (counts_by_year), cited-by counts.
#   3. Classify: auto-merge rules (exact / prefix / extend / paper-overlap),
#      plus finer review categories based on gender-diff + year-overlap +
#      institution-match.
#   4. Read user decisions from existing outputs/author_alias_review.xlsx
#      'decision' column:
#        M / merge         → add to author_aliases.csv
#        S / skip          → add to author_alias_skipped.csv (never re-flag)
#        R / review / ""   → keep in the review sheet
#   5. Write:
#      - outputs/author_aliases.csv  + .xlsx (formatted)
#      - outputs/author_alias_skipped.csv (permanent skip list)
#      - outputs/author_alias_review.xlsx (remaining candidates, enriched)
# ============================================================================

suppressPackageStartupMessages({
  library(tidyverse)
  library(openxlsx)
  library(arrow)
})

setwd("/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel")

SKIP_PATH   <- "outputs/author_alias_skipped.csv"
REVIEW_PATH <- "outputs/author_alias_review.xlsx"
ALIAS_PATH  <- "outputs/author_aliases.csv"
# Prefer the richer API-variant institution file if present.
INST_PATH <- if (file.exists("outputs/openalex_authors_last_institution.openalex_api.csv")) {
  "outputs/openalex_authors_last_institution.openalex_api.csv"
} else {
  "outputs/openalex_authors_last_institution.csv"
}

# --- Load source data ------------------------------------------------------
authors <- read_csv("outputs/openalex_unique_authors.csv", show_col_types = FALSE) |>
  mutate(openalex_author_id = str_remove(openalex_author_id, "https://openalex.org/"))

paper_authors <- read_csv("outputs/openalex_paper_authors.csv", show_col_types = FALSE) |>
  mutate(openalex_author_id = str_remove(openalex_author_id, "https://openalex.org/")) |>
  filter(!is.na(literature_id), !is.na(openalex_author_id)) |>
  distinct(literature_id, openalex_author_id)

existing <- read_csv(ALIAS_PATH, show_col_types = FALSE)
is_manual <- !grepl("^auto-", existing$notes %||% "")
manual_aliases <- existing[is_manual, ]
cat(sprintf("Manual aliases preserved: %d\n", nrow(manual_aliases)))

skip_list <- if (file.exists(SKIP_PATH)) {
  read_csv(SKIP_PATH, show_col_types = FALSE,
           col_types = cols(.default = "c"))
} else {
  tibble(alias_id = character(), canonical_id = character(),
         decided_on = character(), note = character())
}
cat(sprintf("Skip list entries: %d\n", nrow(skip_list)))

# --- Apply user decisions from previous review XLSX -----------------------
applied_merges <- tibble(alias_openalex_id = character(),
                         canonical_openalex_id = character(),
                         canonical_name = character(),
                         notes = character())
new_skips <- tibble(alias_id = character(), canonical_id = character(),
                    decided_on = character(), note = character())

# Read user decisions from the NOTES column of the prior review XLSX.
# Keywords (case-insensitive, substring match):
#   merge / same / yes / confirm   → auto-merge into aliases.csv
#   skip / different / no / keep   → permanent skip
#   review / unsure / ?            → keep in review
#   empty or unrecognised          → keep in review
if (file.exists(REVIEW_PATH)) {
  prev_review <- read.xlsx(REVIEW_PATH)
  if ("notes" %in% colnames(prev_review)) {
    # Final-pass policy: anything without an explicit "merge" keyword is SKIP.
    # (User directive: blank / distinct / skip all = skip.) Rows where the
    # user wants more time can be excluded by typing "review" or "unsure".
    classify_note <- function(n) {
      n <- tolower(trimws(n %||% ""))
      if (grepl("\\b(merge|same|confirm|is the same|yes)\\b", n)) return("MERGE")
      if (grepl("\\b(review|unsure|defer|\\?+)\\b", n)) return("NONE")
      "SKIP"
    }
    prev_review$decision_code <- vapply(prev_review$notes, classify_note, character(1))
    n_merge <- sum(prev_review$decision_code == "MERGE")
    n_skip  <- sum(prev_review$decision_code == "SKIP")
    cat(sprintf("User notes decisions — merge: %d, skip: %d, pending: %d\n",
                n_merge, n_skip,
                sum(prev_review$decision_code == "NONE")))

    merges <- prev_review |> filter(decision_code == "MERGE")
    skips  <- prev_review |> filter(decision_code == "SKIP")

    if (nrow(merges) > 0) {
      applied_merges <- merges |>
        transmute(
          alias_openalex_id     = alias_id,
          canonical_openalex_id = canonical_id,
          canonical_name        = canonical_name,
          notes = sprintf("user-confirm: %s = %s | %s",
                          alias_name, canonical_name, notes)
        )
    }
    if (nrow(skips) > 0) {
      new_skips <- skips |>
        transmute(alias_id = alias_id,
                  canonical_id = canonical_id,
                  decided_on = as.character(Sys.Date()),
                  note = sprintf("user-skip: %s | %s", alias_name, notes))
    }
  }
}

skip_list <- bind_rows(skip_list, new_skips) |> distinct(alias_id, canonical_id, .keep_all = TRUE)
write_csv(skip_list, SKIP_PATH)

# --- Helpers ---------------------------------------------------------------
get_initials <- function(name) {
  if (length(name) != 1 || is.na(name)) return("")
  name <- trimws(as.character(name))
  if (nchar(name) == 0) return("")
  parts <- strsplit(name, "\\s+")[[1]]
  if (length(parts) <= 1) return("")
  givens <- parts[-length(parts)]
  inits <- vapply(givens, function(tok) {
    lo <- gsub("[^A-Za-z]", "", tok)
    if (nchar(lo) == 0) return("")
    if (lo == toupper(lo) && nchar(lo) <= 4) toupper(lo)
    else toupper(substr(lo, 1, 1))
  }, character(1))
  paste0(inits, collapse = "")
}

expand_canonical <- function(cn, an) {
  ci <- get_initials(cn); ai <- get_initials(an)
  if (nchar(ai) <= nchar(ci)) return(cn)
  extra <- substr(ai, nchar(ci) + 1, nchar(ai))
  parts <- strsplit(trimws(cn), "\\s+")[[1]]
  surname <- parts[length(parts)]
  givens  <- parts[-length(parts)]
  paste(c(givens, paste0(strsplit(extra, "")[[1]], "."), surname), collapse = " ")
}

is_pure_initials_token <- function(fn) {
  if (is.na(fn)) return(FALSE)
  compact <- gsub("[\\s.]", "", fn, perl = TRUE)
  nchar(compact) > 0 && nchar(compact) <= 4 && compact == toupper(compact) &&
    grepl("^[A-Z]+$", compact)
}

# --- Richer institution data (API variant if available) ------------------
inst_richer <- read_csv(INST_PATH, show_col_types = FALSE) |>
  mutate(openalex_author_id = str_remove(openalex_author_id, "https://openalex.org/")) |>
  transmute(
    id = openalex_author_id,
    last_inst    = last_institution_name,
    last_country = last_institution_country
  )
cat(sprintf("Richer institution rows: %d (from %s)\n",
            sum(!is.na(inst_richer$last_inst)), INST_PATH))

# --- Per-author year ranges from local paper data -------------------------
# Join paper_authors × literature_review_enriched.year → min/max per author.
cat("Computing per-author year ranges from local parquet...\n")
papers <- tryCatch(
  read_parquet("outputs/literature_review_enriched.parquet") |>
    select(literature_id, year) |>
    filter(!is.na(year), year >= 1900, year <= 2030) |>
    mutate(literature_id = as.character(literature_id)),
  error = function(e) { cat("  parquet unavailable\n"); NULL }
)

year_ranges <- if (!is.null(papers)) {
  paper_authors |>
    mutate(literature_id = as.character(literature_id)) |>
    inner_join(papers, by = "literature_id") |>
    group_by(openalex_author_id) |>
    summarise(
      year_min = min(year, na.rm = TRUE),
      year_max = max(year, na.rm = TRUE),
      works_count = n(),
      .groups = "drop"
    ) |>
    rename(id = openalex_author_id)
} else {
  tibble(id = character(), year_min = integer(),
         year_max = integer(), works_count = integer())
}
cat(sprintf("  Year ranges computed for %d authors\n", nrow(year_ranges)))

# --- Build candidate set ---------------------------------------------------
cat("\nBuilding candidate pairs...\n")
authors$surname_lc   <- vapply(authors$last_name,  function(s) {
  if (is.na(s)) "" else tolower(trimws(strsplit(s, "\\s+")[[1]][1]))
}, character(1))
authors$is_init_only <- vapply(authors$first_name, is_pure_initials_token, logical(1))
authors$first_letter <- toupper(substr(trimws(authors$first_name), 1, 1))

by_surname <- split(authors, authors$surname_lc)
cand_list <- list()
for (nm in names(by_surname)) {
  grp <- by_surname[[nm]]
  if (nchar(nm) == 0) next
  full  <- grp[!grp$is_init_only, , drop = FALSE]
  inits <- grp[ grp$is_init_only, , drop = FALSE]
  if (nrow(full) == 0 || nrow(inits) == 0) next
  for (fl in unique(full$first_letter)) {
    anchors <- full[full$first_letter == fl, , drop = FALSE]
    if (nrow(anchors) == 0) next
    anchor <- anchors[which.max(anchors$paper_count), , drop = FALSE]
    matching <- inits[inits$first_letter == fl, , drop = FALSE]
    if (nrow(matching) == 0) next
    for (i in seq_len(nrow(matching))) {
      a <- matching[i, ]
      cand_list[[length(cand_list) + 1]] <- tibble(
        alias_id              = a$openalex_author_id,
        alias_name            = paste(a$first_name, a$last_name),
        alias_papers          = a$paper_count,
        alias_institution     = a$most_common_institution,
        alias_country         = a$institution_country,
        alias_gender          = a$gender,
        canonical_id          = anchor$openalex_author_id,
        canonical_name        = paste(anchor$first_name, anchor$last_name),
        canonical_papers      = anchor$paper_count,
        canonical_institution = anchor$most_common_institution,
        canonical_country     = anchor$institution_country,
        canonical_gender      = anchor$gender
      )
    }
  }
}
cand <- bind_rows(cand_list)
cat(sprintf("Raw candidate pairs: %d\n", nrow(cand)))

# Drop user-skipped pairs
cand <- cand |>
  anti_join(skip_list, by = c("alias_id", "canonical_id"))
cat(sprintf("After skip-list filter: %d\n", nrow(cand)))

# Drop aliases already resolved (manual or user-confirmed merges)
already <- c(manual_aliases$alias_openalex_id, applied_merges$alias_openalex_id)
cand <- cand |> filter(!alias_id %in% already)
cat(sprintf("After already-merged filter: %d\n", nrow(cand)))

# --- Enrich candidates with richer institution + year ranges --------------
prof_df <- inst_richer |>
  full_join(year_ranges, by = "id")

cand <- cand |>
  left_join(prof_df |> rename_with(~ paste0("alias_", .), -id),
            by = c("alias_id" = "id")) |>
  left_join(prof_df |> rename_with(~ paste0("canonical_", .), -id),
            by = c("canonical_id" = "id"))

# Use richer institution file when the unique_authors file has NA
cand <- cand |>
  mutate(
    alias_institution     = coalesce(alias_institution, alias_last_inst),
    alias_country         = coalesce(alias_country, alias_last_country),
    canonical_institution = coalesce(canonical_institution, canonical_last_inst),
    canonical_country     = coalesce(canonical_country, canonical_last_country)
  )

# --- Paper overlap --------------------------------------------------------
cat("Computing paper overlap...\n")
all_ids <- unique(c(cand$alias_id, cand$canonical_id))
pa_sub <- paper_authors |> filter(openalex_author_id %in% all_ids)
overlap_fn <- function(id1, id2) {
  p1 <- pa_sub$literature_id[pa_sub$openalex_author_id == id1]
  p2 <- pa_sub$literature_id[pa_sub$openalex_author_id == id2]
  length(intersect(p1, p2))
}
cand$paper_overlap <- mapply(overlap_fn, cand$alias_id, cand$canonical_id)

# --- Year overlap ---------------------------------------------------------
cand <- cand |>
  mutate(
    year_span_alias     = ifelse(!is.na(alias_year_min) & !is.na(alias_year_max),
                                 alias_year_max - alias_year_min + 1, NA_integer_),
    year_span_canonical = ifelse(!is.na(canonical_year_min) & !is.na(canonical_year_max),
                                 canonical_year_max - canonical_year_min + 1, NA_integer_),
    year_overlap = pmax(0, pmin(alias_year_max, canonical_year_max) -
                             pmax(alias_year_min, canonical_year_min) + 1),
    year_overlap = ifelse(is.na(alias_year_min) | is.na(canonical_year_min),
                          NA_integer_, year_overlap),
    # Proportional overlap: how much of the ALIAS's active years fall
    # within the canonical's range. A 1-paper alias (span=1) that sits
    # inside canonical's range gives ratio=1.0 — strong same-person signal.
    # Many papers (span>>1) with tiny overlap → distinct people.
    year_overlap_ratio = ifelse(is.na(year_overlap) | year_span_alias == 0,
                                NA_real_,
                                round(year_overlap / year_span_alias, 2)),
    # gap = years between the two active ranges (0 if they overlap)
    year_gap = pmax(0, pmax(alias_year_min, canonical_year_min) -
                       pmin(alias_year_max, canonical_year_max) - 1),
    year_gap = ifelse(is.na(year_overlap), NA_integer_, year_gap)
  )

# --- Classify -------------------------------------------------------------
cand <- cand |>
  mutate(
    alias_inits     = vapply(alias_name,     get_initials, character(1)),
    canonical_inits = vapply(canonical_name, get_initials, character(1)),
    same_inst       = !is.na(alias_institution) & !is.na(canonical_institution) &
                      alias_institution == canonical_institution,
    gender_diff     = !is.na(alias_gender) & !is.na(canonical_gender) &
                      alias_gender != canonical_gender & alias_gender != "" &
                      canonical_gender != "",
    inits_exact     = alias_inits == canonical_inits & nchar(alias_inits) > 0,
    inits_prefix    = nchar(alias_inits) < nchar(canonical_inits) &
                      startsWith(canonical_inits, alias_inits) & nchar(alias_inits) > 0,
    inits_extend    = nchar(alias_inits) > nchar(canonical_inits) &
                      startsWith(alias_inits, canonical_inits),
    middle_diff     = nchar(alias_inits) > 0 & nchar(canonical_inits) > 0 &
                      substr(alias_inits, 1, 1) == substr(canonical_inits, 1, 1) &
                      !inits_exact & !inits_prefix & !inits_extend,
    years_overlap   = !is.na(year_overlap) & year_overlap > 0,
    years_gap_big   = !is.na(year_gap) & year_gap >= 10,
    decision = case_when(
      paper_overlap >= 2                              ~ "merge: paper-overlap",
      inits_exact                                     ~ "merge: exact",
      inits_prefix                                    ~ "merge: prefix",
      inits_extend                                    ~ "merge: extend",
      gender_diff & same_inst                         ~ "review: same-inst diff-gender",
      gender_diff & !same_inst                        ~ "review: diff-inst diff-gender",
      middle_diff & same_inst & years_overlap         ~ "review: same-inst likely-dupe",
      middle_diff & same_inst & years_gap_big         ~ "review: same-inst year-gap ≥10",
      middle_diff & same_inst                         ~ "review: same-inst",
      middle_diff & !same_inst & years_overlap        ~ "review: diff-inst maybe-moved",
      middle_diff & !same_inst & years_gap_big        ~ "review: diff-inst year-gap ≥10",
      middle_diff & !same_inst                        ~ "review: diff-inst",
      TRUE                                            ~ "skip: other"
    )
  )

dec_counts <- cand |> count(decision, sort = TRUE)
cat("\nDecisions:\n"); print(dec_counts)

# --- Build alias rows for merges ------------------------------------------
build_rows <- function(df, label) {
  if (nrow(df) == 0) return(tibble())
  df |>
    rowwise() |>
    mutate(new_canonical = if (label == "merge: extend")
      expand_canonical(canonical_name, alias_name) else canonical_name) |>
    ungroup() |>
    transmute(
      alias_openalex_id     = alias_id,
      canonical_openalex_id = canonical_id,
      canonical_name        = new_canonical,
      notes = sprintf("auto-%s: %s (%dp) = %s (%dp) @ %s (overlap=%d, yrs %s↔%s)",
                      sub("^merge: ", "", label),
                      alias_name, alias_papers,
                      canonical_name, canonical_papers,
                      substr(coalesce(canonical_institution, "?"), 1, 40),
                      paper_overlap,
                      ifelse(is.na(alias_year_min), "?",
                             paste0(alias_year_min, "-", alias_year_max)),
                      ifelse(is.na(canonical_year_min), "?",
                             paste0(canonical_year_min, "-", canonical_year_max)))
    )
}
new_exact   <- build_rows(cand |> filter(decision == "merge: exact"),  "merge: exact")
new_prefix  <- build_rows(cand |> filter(decision == "merge: prefix"), "merge: prefix")
new_extend  <- build_rows(cand |> filter(decision == "merge: extend"), "merge: extend")
new_overlap <- build_rows(cand |> filter(decision == "merge: paper-overlap"),
                          "merge: paper-overlap")
new_auto <- bind_rows(new_exact, new_prefix, new_extend, new_overlap) |>
  distinct(alias_openalex_id, .keep_all = TRUE)

# Propagate expanded canonical name to manual entries (if any)
if (nrow(new_extend) > 0) {
  rename_map <- new_extend |> distinct(canonical_openalex_id, canonical_name)
  manual_aliases <- manual_aliases |>
    left_join(rename_map, by = "canonical_openalex_id", suffix = c("", ".new")) |>
    mutate(canonical_name = coalesce(canonical_name.new, canonical_name)) |>
    select(-canonical_name.new)
}

# Applied merges from user go in too
alias_final <- bind_rows(manual_aliases, applied_merges, new_auto) |>
  distinct(alias_openalex_id, .keep_all = TRUE) |>
  arrange(canonical_name, alias_openalex_id)

write_csv(alias_final, ALIAS_PATH)
cat(sprintf("\nWrote %s — %d aliases total\n", ALIAS_PATH, nrow(alias_final)))

# --- XLSX helper -----------------------------------------------------------
write_formatted_xlsx <- function(df, path, sheet = "Sheet1") {
  wb <- createWorkbook()
  addWorksheet(wb, sheet)
  writeData(wb, sheet, df)
  addStyle(wb, sheet, createStyle(textDecoration = "bold"),
           rows = 1, cols = seq_len(ncol(df)), gridExpand = TRUE)
  freezePane(wb, sheet, firstRow = TRUE)
  setColWidths(wb, sheet, cols = seq_len(ncol(df)), widths = "auto")
  addFilter(wb, sheet, row = 1, cols = seq_len(ncol(df)))
  saveWorkbook(wb, path, overwrite = TRUE)
  cat(sprintf("Wrote %s\n", path))
}

write_formatted_xlsx(alias_final, "outputs/author_aliases.xlsx", sheet = "aliases")

# --- Review XLSX (enriched) -----------------------------------------------
# Preserve any existing 'decision' / 'notes' that AREN'T auto-classifications
prev_notes <- tibble(alias_id = character(), prev_note = character())
if (file.exists(REVIEW_PATH)) {
  pr <- read.xlsx(REVIEW_PATH)
  if ("notes" %in% colnames(pr)) {
    prev_notes <- pr |>
      select(alias_id, prev_note = notes) |>
      filter(!is.na(prev_note), nchar(trimws(prev_note)) > 0)
  }
}

review <- cand |>
  filter(grepl("^review:|^skip: other", decision)) |>
  left_join(prev_notes, by = "alias_id") |>
  mutate(notes = coalesce(prev_note, "")) |>
  select(
    decision,                                       # auto-classified
    notes,                                          # user enters M/S/free text
    paper_overlap, year_overlap, year_overlap_ratio, year_gap,
    alias_id, alias_name, alias_papers, alias_inits,
    alias_institution, alias_country, alias_gender,
    alias_year_min, alias_year_max, alias_works_count,
    canonical_id, canonical_name, canonical_papers, canonical_inits,
    canonical_institution, canonical_country, canonical_gender,
    canonical_year_min, canonical_year_max, canonical_works_count,
    same_inst, gender_diff
  ) |>
  mutate(
    alias_openalex_url     = sprintf("https://openalex.org/%s", alias_id),
    canonical_openalex_url = sprintf("https://openalex.org/%s", canonical_id)
  ) |>
  arrange(decision, desc(paper_overlap), desc(year_overlap_ratio),
          desc(canonical_papers))

# --- Write review XLSX with hyperlinked URL columns -----------------------
wb <- createWorkbook()
addWorksheet(wb, "review")
# Mark the two URL columns as hyperlinks BEFORE writeData (openxlsx quirk)
class(review$alias_openalex_url)     <- "hyperlink"
class(review$canonical_openalex_url) <- "hyperlink"
writeData(wb, "review", review)
addStyle(wb, "review", createStyle(textDecoration = "bold"),
         rows = 1, cols = seq_len(ncol(review)), gridExpand = TRUE)
freezePane(wb, "review", firstRow = TRUE)
setColWidths(wb, "review", cols = seq_len(ncol(review)), widths = "auto")
addFilter(wb, "review", row = 1, cols = seq_len(ncol(review)))
# Colour-code by year_overlap_ratio — strong same-person signal = green
ratio_col <- which(colnames(review) == "year_overlap_ratio")
conditionalFormatting(wb, "review", cols = ratio_col,
                      rows = 2:(nrow(review) + 1),
                      type = "colourScale",
                      style = c("#f8d7da", "#fff3cd", "#d4edda"))
saveWorkbook(wb, REVIEW_PATH, overwrite = TRUE)
cat(sprintf("Wrote %s — %d review rows\n", REVIEW_PATH, nrow(review)))

# Remove stale outputs if any
if (file.exists("outputs/author_alias_candidates.csv"))
  file.remove("outputs/author_alias_candidates.csv")
if (file.exists("outputs/author_alias_candidates.xlsx"))
  file.remove("outputs/author_alias_candidates.xlsx")

cat("\nDone.\n")
