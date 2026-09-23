#!/usr/bin/env Rscript
# Review workbook for queue rows whose PDF is already in the library.
#
# Input : outputs/queue_rows_already_filed_<date>.csv  (scripts/find_queue_rows_already_filed.py)
#         outputs/mark_reconcile_<date>.csv            (scripts/reconcile_download_marks.py, optional)
# Output: outputs/queue_rows_already_filed_<date>.xlsx — Info tab first, one data tab,
#         status as a COLUMN so it can be filtered and sorted.
#
# Usage: Rscript scripts/build_already_filed_workbook.R 2026-09-23

library(openxlsx)

args <- commandArgs(trailingOnly = TRUE)
stamp <- if (length(args)) args[1] else format(Sys.Date(), "%Y-%m-%d")
root <- normalizePath(file.path(dirname(sub("^--file=", "", grep("^--file=", commandArgs(), value = TRUE)[1])), ".."))
src <- file.path(root, "outputs", paste0("queue_rows_already_filed_", stamp, ".csv"))
marks_csv <- file.path(root, "outputs", paste0("mark_reconcile_", stamp, ".csv"))
out <- sub("\\.csv$", ".xlsx", src)

d <- read.csv(src, stringsAsFactors = FALSE)
marked_by <- rep("", nrow(d))
if (file.exists(marks_csv)) {
  m <- read.csv(marks_csv, stringsAsFactors = FALSE)
  marked_by <- m$marked_by[match(as.character(d$lid), as.character(m$literature_id))]
  marked_by[is.na(marked_by)] <- ""
}

d$action_status <- ifelse(d$verdict == "verified",
                          "claude: close on your go", "you: open the PDF and decide")
d$marked_by <- marked_by
d$why_unconfirmed <- ifelse(
  d$verdict == "verified", "",
  ifelse(d$title_cov < 0.3, "almost no title words on pages 1-2: scan with no text layer, or a title page that isn't page 1",
  ifelse(!as.logical(d$author_on_page), "title matches but the author's surname is not on pages 1-2",
         "some title words missing on pages 1-2")))
d$your_decision <- ""            # same paper / different paper / can't tell
d$your_notes <- ""

d$open_pdf <- paste0('=HYPERLINK("file://', gsub(" ", "%20", d$pdf), '","open PDF")')
class(d$open_pdf) <- "formula"

ord <- order(d$verdict != "needs_eyes", -as.numeric(d$title_cov))
cols <- c("action_status", "your_decision", "your_notes", "why_unconfirmed", "open_pdf",
          "lid", "title", "authors", "year", "doi", "status", "marked_by",
          "title_cov", "author_on_page", "pdf")
d <- d[ord, cols]

n_check <- sum(d$action_status == "you: open the PDF and decide")
n_close <- nrow(d) - n_check

info <- data.frame(`Queue rows whose PDF is already filed` = c(
  paste0("Generated ", format(Sys.time(), "%Y-%m-%d %H:%M %Z"),
         " from the queue (docs/papers_data.json) and the library at",
         " /media/simon/data/Documents/Si Work/Papers & Books/SharkPapers."),
  "",
  "WHY THIS EXISTS",
  paste0("A queue row is supposed to close when its PDF is filed. These ", nrow(d),
         " rows are still outstanding, so the download hub keeps offering them to the team,",
         " but a PDF that matches them is already in the library. Found on 2026-09-23 while",
         " checking why 89 of Elena's marked papers never resolved: 83 of hers were already filed."),
  "",
  "WHAT WAS DONE AUTOMATICALLY, BEFORE YOU SEE THIS",
  paste0("1. Every outstanding row (10,082, conference abstracts excluded) was matched against",
         " 21,255 library PDFs on first-author surname, year, and the library filename's title."),
  paste0("2. Each candidate PDF was then OPENED: pages 1-2 must carry at least 80% of the record's",
         " title words plus the first author's surname (or 95% of the title words alone, for old",
         " papers that print no author on page one). A filename match alone was never trusted."),
  paste0("3. ", n_close, " passed that check and need nothing from you."),
  paste0("4. ", n_check, " did not, and are the only rows you need to look at."),
  "",
  "WHAT YOU NEED TO DO",
  paste0("1. Open the 'rows' tab and filter action_status to 'you: open the PDF and decide' (",
         n_check, " rows, sorted worst first)."),
  "2. Click the open_pdf link in the row. Compare what opens with the title and authors columns.",
  "3. Put one of these in your_decision: same paper / different paper / can't tell.",
  "4. Leave the rest alone: rows marked 'claude: close on your go' need no decision.",
  "5. Send the file back, or just say 'go' and I close the verified ones.",
  "",
  "WHAT HAPPENS NEXT",
  paste0("'same paper' and the ", n_close, " verified rows get their queue row closed through",
         " scripts/lib/papers_data_io.py::mutate(), which drops the hub's remaining count by that much."),
  "'different paper' means the library file is misfiled under this record: it goes on the misfile repair list.",
  "Nothing in the queue or the library has been changed by this workbook.",
  "",
  "COLUMNS",
  "action_status  - who owns the row: you, or me on your go.",
  "your_decision  - the only column you must fill, and only on 'you:' rows.",
  "why_unconfirmed- why opening the PDF did not confirm it.",
  "open_pdf       - clickable link to the library file.",
  "title_cov      - share of the record's title words found on pages 1-2 (1.0 is all of them).",
  "author_on_page - was the first author's surname on pages 1-2.",
  "marked_by      - who clicked Mark for this paper on the download hub, if anyone.",
  "",
  "PROVENANCE",
  paste0("Source: ", basename(src), ", written by scripts/find_queue_rows_already_filed.py."),
  "Known gap: only rows whose first author and year are recorded can be matched at all, so the",
  "true number of already-filed rows is at least this many, not exactly this many."),
  check.names = FALSE)

wb <- createWorkbook()
addWorksheet(wb, "Info"); addWorksheet(wb, "rows")
writeData(wb, "Info", info)
writeData(wb, "rows", d)
hdr <- createStyle(textDecoration = "bold")
addStyle(wb, "Info", hdr, rows = 1, cols = 1)
addStyle(wb, "rows", hdr, rows = 1, cols = seq_along(d))
freezePane(wb, "rows", firstRow = TRUE)
addFilter(wb, "rows", rows = 1, cols = seq_along(d))
setColWidths(wb, "Info", cols = 1, widths = 120)
setColWidths(wb, "rows", cols = seq_along(d),
             widths = c(26, 16, 26, 44, 10, 8, 60, 34, 6, 22, 14, 11, 9, 9, 70))
# the check rows first, tinted so they are obvious before any filtering
addStyle(wb, "rows", createStyle(fgFill = "#FFF3CD"),
         rows = 1 + which(d$action_status == "you: open the PDF and decide"),
         cols = seq_along(d), gridExpand = TRUE, stack = TRUE)
worksheetOrder(wb) <- c(1, 2)
saveWorkbook(wb, out, overwrite = TRUE)
cat("wrote", out, "\n", n_check, "rows for Simon,", n_close, "verified\n")
