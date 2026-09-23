#!/usr/bin/env Rscript
# Review workbook for queue rows whose PDF is already in the library.
#
# Input : outputs/queue_rows_already_filed_<date>.csv  (scripts/find_queue_rows_already_filed.py)
#         outputs/mark_reconcile_<date>.csv            (scripts/reconcile_download_marks.py, optional)
# Output: outputs/queue_rows_already_filed_<date>.xlsx
#
# Written through scripts/lib/review_sheet_helper.R, which enforces Simon's
# layout contract (decision column last, proposal column before it, empty and
# constant columns hidden, frozen bold autofiltered header, Info tab first).
# file:// links use utils::URLencode(p, reserved = FALSE), per rule 7 of
# /media/simon/data/Programs/pics/CLAUDEFILES/XLSX-REVIEW-GUIDE.md: reserved =
# TRUE turns the "&" of "Papers & Books" into %26 and the link stops working.
#
# Usage: Rscript scripts/build_already_filed_workbook.R 2026-09-23

suppressMessages(library(openxlsx))

args <- commandArgs(trailingOnly = TRUE)
stamp <- if (length(args)) args[1] else format(Sys.Date(), "%Y-%m-%d")
root <- normalizePath(file.path(dirname(sub("^--file=", "",
        grep("^--file=", commandArgs(), value = TRUE)[1])), ".."))
source(file.path(root, "scripts", "lib", "review_sheet_helper.R"))

src <- file.path(root, "outputs", paste0("queue_rows_already_filed_", stamp, ".csv"))
marks_csv <- file.path(root, "outputs", paste0("mark_reconcile_", stamp, ".csv"))
out <- sub("\\.csv$", ".xlsx", src)

d <- read.csv(src, stringsAsFactors = FALSE)
d$marked_by <- ""
if (file.exists(marks_csv)) {
  m <- read.csv(marks_csv, stringsAsFactors = FALSE)
  j <- match(as.character(d$lid), as.character(m$literature_id))
  d$marked_by <- ifelse(is.na(j), "", m$marked_by[j])
}

needs <- d$verdict != "verified"
d$action_status <- ifelse(needs, "you: open the PDF and decide", "claude: close on your go")
d$why_unconfirmed <- ifelse(!needs, "",
  ifelse(d$title_cov < 0.3,
         "almost no title words on pages 1-2: scan with no text layer, or the title page is not page 1",
  ifelse(!as.logical(d$author_on_page),
         "title matches but the first author's surname is not on pages 1-2",
         "some title words missing on pages 1-2")))
d$proposed_action <- ifelse(needs,
  "check: is the PDF this paper? then same paper / different paper / can't tell",
  "close this queue row: the PDF is filed and verified")
d$your_decision <- ""

# Percent-encode for the link, keep the plain path in its own column for skimming.
d$open_pdf <- sprintf('=HYPERLINK("file://%s","open PDF")',
                      vapply(d$pdf, function(p) utils::URLencode(p, reserved = FALSE), ""))
class(d$open_pdf) <- "formula"

d <- d[order(!needs, -as.numeric(d$title_cov)), c(
  "action_status", "why_unconfirmed", "lid", "title", "authors", "year", "doi",
  "status", "marked_by", "title_cov", "author_on_page", "pdf", "open_pdf",
  "proposed_action", "your_decision")]

n_check <- sum(d$action_status == "you: open the PDF and decide")
n_close <- nrow(d) - n_check

info <- data.frame(`Queue rows whose PDF is already filed` = c(
  paste0("Generated ", format(Sys.time(), "%Y-%m-%d %H:%M %Z"), " from the queue",
         " (docs/papers_data.json) and the library at /media/simon/data/Documents/Si Work/Papers & Books/SharkPapers."),
  "",
  "WHY THIS EXISTS",
  paste0("A queue row is meant to close when its PDF is filed. These ", nrow(d), " rows are still",
         " outstanding, so the download hub keeps offering them to the team, yet a PDF matching them",
         " is already in the library. Found on 2026-09-23 while checking why 89 of Elena's marked",
         " papers never resolved: 83 of hers were already filed and verified."),
  "",
  "WHAT WAS DONE AUTOMATICALLY, BEFORE YOU SAW THIS",
  paste0("1. All 10,082 outstanding rows (conference abstracts excluded) were matched against 21,255",
         " library PDFs on first-author surname, year, and the library filename's title."),
  paste0("2. Every candidate PDF was then OPENED: pages 1-2 had to carry at least 80% of the record's",
         " title words plus the first author's surname, or 95% of the title words alone for old papers",
         " that print no author on page one. A filename match was never trusted on its own."),
  paste0("3. ", n_close, " passed and need nothing from you."),
  paste0("4. ", n_check, " did not. They are the only rows that need you, and they sort to the top."),
  "",
  "WHAT YOU NEED TO DO (the 'rows' tab)",
  paste0("1. Filter action_status to 'you: open the PDF and decide' (", n_check, " rows)."),
  "2. Click open_pdf. Compare what opens against the title and authors columns.",
  "3. Put one of these in your_decision (last column): same paper / different paper / can't tell.",
  "4. Ignore rows marked 'claude: close on your go': they need no decision.",
  "5. Save and tell me, or just say 'go' to close the verified ones without reading these.",
  "",
  "WHAT HAPPENS NEXT",
  paste0("'same paper' and the ", n_close, " verified rows get their queue row closed through",
         " scripts/lib/papers_data_io.py::mutate(). The download hub's remaining count drops by that many."),
  "'different paper' means the library file is misfiled under this record, and it goes to the misfile repair list.",
  "Nothing in the queue or the library has been changed by this workbook.",
  "",
  "COLUMNS",
  "action_status   - who owns the row: you, or me on your go.",
  "why_unconfirmed - why opening the PDF did not confirm it.",
  "title_cov       - share of the record's title words found on pages 1-2 (1.0 is all of them).",
  "author_on_page  - was the first author's surname on pages 1-2.",
  "marked_by       - who clicked Mark for this paper on the download hub, if anyone.",
  "pdf             - the library path, for skimming; open_pdf is the same file as a link.",
  "proposed_action - what I will do unless you say otherwise.",
  "your_decision   - the only column you fill, and only on 'you:' rows.",
  "",
  "PROVENANCE",
  paste0("Source: ", basename(src), ", written by scripts/find_queue_rows_already_filed.py."),
  "Known gap: a row can only be matched when its first author and year are recorded, so the true",
  "number of already-filed rows is at least this many, not exactly this many."),
  check.names = FALSE)

wb <- createWorkbook()
addWorksheet(wb, "Info")
writeData(wb, "Info", info)
addStyle(wb, "Info", createStyle(textDecoration = "bold"), rows = 1, cols = 1)
setColWidths(wb, "Info", cols = 1, widths = 120)

d2 <- review_sheet(wb, "rows", d, proposal_col = "proposed_action",
                   decision_col = "your_decision",
                   widths = c(26, 46, 8, 60, 34, 6, 22, 14, 11, 9, 9, 62, 10, 52, 18),
                   restore_from = if (file.exists(out)) out else NULL)
addStyle(wb, "rows", createStyle(fontColour = "#0563C1", textDecoration = "underline"),
         rows = 2:(nrow(d2) + 1), cols = which(names(d2) == "open_pdf"), gridExpand = TRUE)
addStyle(wb, "rows", createStyle(fgFill = "#FFF3CD"),
         rows = 1 + which(d2$action_status == "you: open the PDF and decide"),
         cols = seq_len(ncol(d2)), gridExpand = TRUE, stack = TRUE)
worksheetOrder(wb) <- c(1, 2)
save_review_workbook(wb, out)
cat("wrote", out, "\n", n_check, "rows for Simon,", n_close, "verified\n")
