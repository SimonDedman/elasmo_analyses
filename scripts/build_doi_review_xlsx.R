#!/usr/bin/env Rscript
# Format the C1 DOI-recovery near-misses as a review workbook.
#
# Input : outputs/doi_recovery_review_<date>.csv  (recover_missing_dois.py)
# Output: outputs/doi_recovery_review_<date>.xlsx
#
# Ordered EASY FIRST. Two thirds of these are quick rejects with an obvious
# tell; the genuine judgement calls come last.
#
# Usage:  Rscript scripts/build_doi_review_xlsx.R [path/to/csv]

suppressPackageStartupMessages(library(openxlsx))

args <- commandArgs(trailingOnly = TRUE)
root <- normalizePath(file.path(dirname(sub("^--file=", "", grep("^--file=",
        commandArgs(trailingOnly = FALSE), value = TRUE)[1])), ".."))
setwd(root)

csv_path <- if (length(args)) args[1] else {
  f <- list.files("outputs", pattern = "^doi_recovery_review_.*\\.csv$",
                  full.names = TRUE)
  f[which.max(file.mtime(f))]
}
stopifnot(file.exists(csv_path))
d <- read.csv(csv_path, stringsAsFactors = FALSE, colClasses = "character")
message(sprintf("read %s (%d rows)", basename(csv_path), nrow(d)))

tokens <- function(x) {
  stop_w <- c("the", "and", "for", "with", "from", "that", "this", "were",
              "was", "are", "its", "into", "new", "some", "their")
  lapply(strsplit(tolower(gsub("[^a-z ]", " ", tolower(x))), "\\s+"),
         function(v) unique(v[nchar(v) >= 4 & !v %in% stop_w]))
}
ta <- tokens(d$title); tb <- tokens(d$candidate_title)
d$our_tokens  <- lengths(ta)
d$cand_tokens <- lengths(tb)
d$two_sided <- round(mapply(function(a, b)
  if (!length(a) || !length(b)) 0 else length(intersect(a, b)) / max(length(a), length(b)),
  ta, tb), 2)

d$title_sim    <- suppressWarnings(as.numeric(d$title_sim))
d$author_match <- tolower(d$author_match) %in% c("true", "1", "yes")

# --- Triage, easiest first ---------------------------------------------------
d$assessment <- ifelse(
  pmin(d$our_tokens, d$cand_tokens) < 4,
  "1 REJECT - candidate title too short to mean anything",
  ifelse(d$author_match & d$two_sided >= 0.50,
         "2 LIKELY CORRECT - author matches, titles broadly agree",
         ifelse(!d$author_match & d$two_sided < 0.40,
                "3 LIKELY WRONG - no author match, titles barely overlap",
                "4 JUDGEMENT - genuinely ambiguous")))
d$rank <- as.integer(substr(d$assessment, 1, 1))
d$decision <- ""
d$notes <- ""

d <- d[order(d$rank, -d$two_sided), ]
cols <- c("assessment", "literature_id", "year", "authors", "title",
          "candidate_doi", "candidate_title", "candidate_year",
          "title_sim", "two_sided", "author_match", "our_tokens",
          "cand_tokens", "decision", "notes")
d <- d[, cols[cols %in% names(d)]]

summ <- as.data.frame(table(assessment = d$assessment), responseName = "rows")
summ$pct <- round(100 * summ$rows / nrow(d), 1)

info <- data.frame(c(
  "C1 DOI RECOVERY — NEAR-MISSES HELD FOR REVIEW",
  sprintf("Generated %s from %s.", format(Sys.time(), "%Y-%m-%d %H:%M %Z"),
          basename(csv_path)),
  "",
  "WHY THIS EXISTS",
  "The DOI-recovery pass queried Crossref for every outstanding paper lacking a",
  "DOI. Confident matches were applied. These are the ones that ALMOST passed:",
  "held back rather than discarded, because a wrong DOI is worse than a blank",
  "one — the download helper links straight to it, which is how the 2026-04",
  "off-by-one corruption sent people to the wrong paper for three months.",
  "",
  "WHAT WAS ALREADY DONE AUTOMATICALLY",
  "- Queried Crossref with title plus the venue string, 7,878 papers, 0 errors.",
  "- Applied 799 matches that passed BOTH a one-sided and a two-sided title",
  "  test plus a year check; 92% of those also matched on author surname.",
  "- Held these back and pre-assessed each one.",
  "",
  "THE TRAP THIS SHEET EXISTS TO AVOID",
  "The similarity score divides token overlap by the SHORTER title, so a",
  "two-word Crossref record scores a perfect 1.00 against any longer title",
  "containing those words. 'CHIMAERAS' scored 1.00 against 'Field Guide to",
  "Sharks, Rays & Chimaeras of Europe and the Mediterranean'. Read 'two_sided'",
  "(overlap over the LONGER title) rather than 'title_sim'.",
  "",
  "HOW THIS SHEET IS ORDERED — easiest first",
  sprintf("  1 REJECT, too short      %4d rows - candidate is an index entry.",
          sum(d$assessment == "1 REJECT - candidate title too short to mean anything")),
  "                                   Skim and reject in bulk.",
  sprintf("  2 LIKELY CORRECT         %4d rows - author matches and titles agree.",
          sum(d$assessment == "2 LIKELY CORRECT - author matches, titles broadly agree")),
  "                                   Skim and accept in bulk.",
  sprintf("  3 LIKELY WRONG           %4d rows - no author, titles barely overlap.",
          sum(d$assessment == "3 LIKELY WRONG - no author match, titles barely overlap")),
  sprintf("  4 JUDGEMENT              %4d rows - genuinely ambiguous. Read these.",
          sum(d$assessment == "4 JUDGEMENT - genuinely ambiguous")),
  "",
  "WHAT TO DO",
  "  1. Fill 'decision' per row with one of:",
  "       ACCEPT  - the DOI is right; it will be written to papers_data.json",
  "       REJECT  - not this paper; the row keeps a blank DOI",
  "       UNSURE  - leave for a second pass",
  "  2. 'notes' is free text.",
  "  3. Send the sheet back; ACCEPTs are applied in one pass and then put",
  "     through the sync's Phase 3b Crossref verification as an independent",
  "     second check before the download helper links to any of them.",
  "",
  "PROVENANCE AND KNOWN GAPS",
  "- candidate_title is truncated to 140 characters in the cache, so a long",
  "  title may look shorter than it is; 'cand_tokens' counts the truncation.",
  "- A blank DOI is an honest state. Rejecting costs nothing but the chance of",
  "  a later recovery; accepting a wrong one costs a person's time and trust."
), stringsAsFactors = FALSE)
names(info) <- "C1 DOI recovery — review"

wb <- createWorkbook()
hdr <- createStyle(textDecoration = "bold")

addWorksheet(wb, "Info")
writeData(wb, "Info", info)
setColWidths(wb, "Info", 1, 92)
addStyle(wb, "Info", createStyle(textDecoration = "bold", fontSize = 12),
         rows = 1, cols = 1)

addWorksheet(wb, "Near_misses")
writeData(wb, "Near_misses", d, headerStyle = hdr)
freezePane(wb, "Near_misses", firstRow = TRUE)
addFilter(wb, "Near_misses", rows = 1, cols = seq_len(ncol(d)))
setColWidths(wb, "Near_misses", seq_len(ncol(d)),
             c(52, 13, 6, 34, 56, 30, 56, 9, 10, 10, 12, 12, 14, 30)[seq_len(ncol(d))])

addWorksheet(wb, "Summary")
writeData(wb, "Summary", summ, headerStyle = hdr)
setColWidths(wb, "Summary", 1:3, c(56, 8, 8))

worksheetOrder(wb) <- c(1, 2, 3)
out <- sub("\\.csv$", ".xlsx", csv_path)
saveWorkbook(wb, out, overwrite = TRUE)
source(file.path("scripts", "lib", "repair_xlsx.R"))
repair_xlsx(out)
message(sprintf("wrote %s  (%d rows)", out, nrow(d)))
