#!/usr/bin/env Rscript
# Format the duplicate-literature_id adjudication as a review workbook.
#
# Input : outputs/duplicate_literature_ids_<date>.csv
#         (written by scripts/resolve_duplicate_literature_ids.py)
# Output: outputs/duplicate_literature_ids_<date>.xlsx
#
# Ordered EASY FIRST, so the mechanical two thirds can be cleared in one pass
# and the genuine judgement calls are met last, when the shape of the problem
# is already familiar. Group members stay adjacent: a row means nothing without
# the other rows sharing its id.
#
# Usage:  Rscript scripts/build_duplicate_ids_xlsx.R [path/to/csv]

suppressPackageStartupMessages({
  library(openxlsx)
})

args <- commandArgs(trailingOnly = TRUE)
root <- normalizePath(file.path(dirname(sub("^--file=", "", grep("^--file=",
        commandArgs(trailingOnly = FALSE), value = TRUE)[1])), ".."))
setwd(root)

csv_path <- if (length(args)) args[1] else {
  f <- list.files("outputs", pattern = "^duplicate_literature_ids_.*\\.csv$",
                  full.names = TRUE)
  f[which.max(file.mtime(f))]
}
stopifnot(file.exists(csv_path))
d <- read.csv(csv_path, stringsAsFactors = FALSE, colClasses = "character")
message(sprintf("read %s (%d rows)", basename(csv_path), nrow(d)))

# --- Difficulty ordering -----------------------------------------------------
# Rank reflects how much thought a group needs, not how many rows it has.
# SAFE_DEDUPE is a keystroke; YEAR_CONFLICT means deciding whether two years of
# the same title are two editions or one typo, which needs the book in hand.
rank_of <- function(action) {
  dplyr_case <- c(
    "SAFE_DEDUPE"       = 1,
    "CHECK_TITLES"      = 2,
    "ASSIGN_ORPHAN_ID"  = 3,
    "SEPARATE_RECORD"   = 4,
    "DOI_WRONG"         = 5,
    "YEAR_CONFLICT"     = 6
  )
  key <- sub(" .*$", "", action)          # strip the parenthetical explanation
  out <- unname(dplyr_case[key])
  out[is.na(out)] <- 9
  out
}
d$difficulty_rank <- rank_of(d$suggested_action)
d$difficulty <- c("1 easy", "2 easy", "3 mechanical", "4 clear action",
                  "5 needs a lookup", "6 needs judgement",
                  rep("9 unclassified", 3))[d$difficulty_rank]

grp_n <- table(d$literature_id)
d$rows_in_group <- as.integer(grp_n[d$literature_id])

d <- d[order(d$difficulty_rank, d$literature_id, d$year), ]

cols <- c("difficulty", "suggested_action", "literature_id", "rows_in_group",
          "group_kind", "year", "title", "journal", "doi", "verdict",
          "crossref_title", "crossref_year", "crossref_journal", "detail",
          "decision", "notes")
cols <- cols[cols %in% names(d)]
d <- d[, cols]

n_groups <- length(unique(d$literature_id))
by_action <- as.data.frame(table(suggested_action = d$suggested_action),
                           responseName = "rows")
by_action$ids <- sapply(as.character(by_action$suggested_action), function(a)
  length(unique(d$literature_id[d$suggested_action == a])))
by_action <- by_action[order(rank_of(as.character(by_action$suggested_action))), ]

# --- Info --------------------------------------------------------------------
info <- data.frame(c(
  "DUPLICATE LITERATURE_IDs — ADJUDICATION",
  sprintf("Generated %s from %s.", format(Sys.time(), "%Y-%m-%d %H:%M %Z"),
          basename(csv_path)),
  "",
  "WHY THIS EXISTS",
  "docs/papers_data.json holds rows that share a literature_id but disagree",
  "about the paper: different DOIs, different years, or different titles. A",
  "shared id means the download helper can link to the wrong paper, which is",
  "exactly what the 2026-04 off-by-one corruption did for three months.",
  "",
  "WHAT WAS ALREADY DONE AUTOMATICALLY",
  sprintf("- Found %d groups sharing an id, plus rows carrying no id at all.",
          n_groups),
  "- Fetched the Crossref record for EVERY DOI in every group and compared",
  "  its title AND year against the row's own. A DOI is endorsed only when",
  "  Crossref agrees on both; a title match alone is not enough.",
  "- Kept 'could not check' separate from 'DOI is wrong', so a network failure",
  "  never condemns a good DOI.",
  "- Suggested an action per group. NOTHING HAS BEEN CHANGED.",
  "",
  "WHAT THE CHECK OVERTURNED",
  "The first read was 'where there are two DOIs, one must be wrong'. Not so.",
  "For id 32101 Crossref confirms BOTH: the second is the CORRIGENDUM to the",
  "first. Deduplicating that pair would have destroyed a real record. Only ONE",
  "group holds a genuinely wrong DOI (3365, below).",
  "",
  "HOW THIS SHEET IS ORDERED",
  "Easy first. The mechanical two thirds clear in one pass, and the judgement",
  "calls come last when the shape of the problem is familiar. Rows sharing an",
  "id are kept adjacent: a single row means nothing without its group.",
  "",
  "TAB 'Duplicates' — work top to bottom",
  "  1. Read 'difficulty' and 'suggested_action', then fill 'decision':",
  "       KEEP        - keep this row",
  "       DELETE      - remove this row",
  "       NEW_ID      - this row is a distinct record and needs its own id",
  "       BLANK_DOI   - the DOI is wrong; clear it rather than guess",
  "       UNSURE      - leave it for a second pass",
  "  2. Fill exactly one decision per ROW, not per group: a group of two is",
  "     usually one KEEP and one DELETE.",
  "  3. 'notes' is free text; say why if the reason is not obvious.",
  "",
  "THE GROUPS, EASIEST FIRST",
  "  1 SAFE_DEDUPE       same title, same year, no conflicting DOI. One KEEP,",
  "                      one DELETE, no thought required.",
  "  2 CHECK_TITLES      title variants only: 'regimes'/'regions', accents,",
  "                      capitalisation. Glance, then dedupe.",
  "  3 ASSIGN_ORPHAN_ID  rows with NO literature_id at all (book chapters",
  "                      keyed 'In Kimura et al.', 'In M. Gomon', 'In FISCHER',",
  "                      and a Murmansk report). They cannot be joined,",
  "                      tracked, or acquired until they get ids in the",
  "                      600000+ orphan range.",
  "  4 SEPARATE_RECORD   id 32101: the paper AND its corrigendum. Both are",
  "                      real. The corrigendum needs its own id.",
  "  5 DOI_WRONG         id 3365, 'Sharks and Rays of Australia'. Both rows",
  "                      carry the SAME DOI at title similarity 1.00, but",
  "                      Crossref dates it 2011 while the rows say 1994 and",
  "                      2009: it points at a REVIEW of the book, not either",
  "                      edition. The year check caught what a title check",
  "                      alone would have passed.",
  "  6 YEAR_CONFLICT     same title, two different years. Two editions, or one",
  "                      typo? This is the genuine judgement call and the",
  "                      largest group.",
  "",
  "PROVENANCE AND KNOWN GAPS",
  sprintf("- Only %d of %d rows carry a DOI at all, so Crossref settles very",
          sum(nzchar(d$doi)), nrow(d)),
  "  little here; most of the work is title and year judgement.",
  "- Source is docs/papers_data.json, the live outstanding-papers list. A",
  "  shark-references sync was running when this was generated, so new",
  "  duplicates may appear; re-run the adjudicator after it lands.",
  "- Nothing here is applied. Send the sheet back and the decisions go in as",
  "  one pass."
), stringsAsFactors = FALSE)
names(info) <- "Duplicate literature_ids"

# --- Write -------------------------------------------------------------------
wb <- createWorkbook()
hdr <- createStyle(textDecoration = "bold")

addWorksheet(wb, "Info")
writeData(wb, "Info", info)
setColWidths(wb, "Info", 1, 92)
addStyle(wb, "Info", createStyle(textDecoration = "bold", fontSize = 12),
         rows = 1, cols = 1)

addWorksheet(wb, "Duplicates")
writeData(wb, "Duplicates", d, headerStyle = hdr)
freezePane(wb, "Duplicates", firstRow = TRUE)
addFilter(wb, "Duplicates", rows = 1, cols = seq_len(ncol(d)))
setColWidths(wb, "Duplicates", seq_len(ncol(d)),
             c(18, 30, 14, 8, 26, 6, 60, 28, 30, 22, 60, 8, 26, 18, 14,
               30)[seq_len(ncol(d))])
# Shade alternate GROUPS so a group reads as a block rather than loose rows.
ids <- d$literature_id
band <- cumsum(c(TRUE, ids[-1] != ids[-length(ids)])) %% 2 == 0
shade <- createStyle(fgFill = "#F2F2F2")
if (any(band)) {
  addStyle(wb, "Duplicates", shade, rows = which(band) + 1,
           cols = seq_len(ncol(d)), gridExpand = TRUE, stack = TRUE)
}

addWorksheet(wb, "Summary")
writeData(wb, "Summary", by_action, headerStyle = hdr)
freezePane(wb, "Summary", firstRow = TRUE)
setColWidths(wb, "Summary", 1:3, c(48, 8, 8))

worksheetOrder(wb) <- c(1, 2, 3)
out <- sub("\\.csv$", ".xlsx", csv_path)
saveWorkbook(wb, out, overwrite = TRUE)
source(file.path("scripts", "lib", "repair_xlsx.R"))
repair_xlsx(out)
message(sprintf("wrote %s  (%d rows, %d groups)", out, nrow(d), n_groups))
