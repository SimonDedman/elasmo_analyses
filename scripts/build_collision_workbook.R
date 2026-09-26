#!/usr/bin/env Rscript
# Review workbook for library files still claimed by two or more papers.
#
# Input : outputs/filename_collisions_resolved.csv (scripts/resolve_filename_collisions.py)
# Output: outputs/filename_collisions_<date>.xlsx
#
# Usage: Rscript scripts/build_collision_workbook.R

suppressMessages(library(openxlsx))
root <- normalizePath(file.path(dirname(sub("^--file=", "",
        grep("^--file=", commandArgs(), value = TRUE)[1])), ".."))
source(file.path(root, "scripts", "lib", "review_sheet_helper.R"))

d <- read.csv(file.path(root, "outputs", "filename_collisions_resolved.csv"), stringsAsFactors = FALSE)
d <- d[d$verdict == "unclear", ]
d$file <- basename(d$pdf)
d$open_pdf <- sprintf('=HYPERLINK("file://%s","open PDF")',
                      vapply(d$pdf, function(p) utils::URLencode(p, reserved = FALSE), ""))
class(d$open_pdf) <- "formula"
d$action_status <- "you: open the PDF and say which paper it is"
d$proposed_action <- "name the literature_id the file belongs to, or say it is one paper twice"
d$your_decision <- ""
d <- d[order(d$file, -d$score),
       c("action_status", "file", "literature_id", "title", "year", "score",
         "on_queue", "pdf", "open_pdf", "proposed_action", "your_decision")]
n_files <- length(unique(d$file))

info <- data.frame(`Library files shared by two or more papers` = c(
  paste0("Generated ", format(Sys.time(), "%Y-%m-%d %H:%M %Z"), "."),
  "",
  "WHY THIS EXISTS",
  paste0("A library filename truncates the title at 60 characters, which is exactly where a series says",
         " which part it is. A paper and its Part II generated the same name, so filing the second would",
         " have overwritten the first. 128 files were shared that way, covering 272 records."),
  "",
  "WHAT WAS DONE AUTOMATICALLY, BEFORE YOU SAW THIS",
  paste0("1. The naming rule now keeps the part designator even when the truncation would drop it, and a",
         " second paper that still collides gets an id suffix. One definition, in",
         " scripts/lib/library_naming.py, used by the ingester, the monthly sync, the repair tool and the",
         " id map, so they cannot drift apart again."),
  paste0("2. Every shared file was OPENED and scored against each claiming record, on the words that make",
         " that title different from its rivals, plus the part number printed in the paper itself."),
  "3. 51 files proved to be one paper catalogued twice: those records now carry merged_into = the lowest id.",
  paste0("4. 49 files were resolved outright and renamed to the winner's unambiguous name. 62 papers were",
         " proved NOT held, and 61 of them went back on the download queue."),
  paste0("5. ", n_files, " files could not be called with confidence. They are this workbook."),
  "",
  "WHAT YOU NEED TO DO (the 'rows' tab)",
  "1. Each file is a group of rows, one per claiming record, best guess first.",
  "2. Click open_pdf and see which paper the file actually is.",
  "3. Write 'this one' in your_decision on that row. If the records are one paper twice, write 'same paper'.",
  "4. Anything left blank stays as it is: the file keeps its name and both records keep claiming it.",
  "",
  "WHAT HAPPENS NEXT",
  paste0("The file is renamed to the winning record's name, the losing records go back on the download queue",
         " as papers we do not hold, and the id map is rebuilt so extraction reads the right text."),
  "",
  "COLUMNS",
  "score  - share of that record's distinctive title words found on the first pages, +0.5 when the part",
  "         number printed in the paper matches it, -0.5 when a rival's number matches instead.",
  "on_queue - whether that record is already listed as still to download.",
  "",
  "PROVENANCE",
  "outputs/filename_collisions_resolved.csv, written by scripts/resolve_filename_collisions.py."),
  check.names = FALSE)

wb <- createWorkbook()
addWorksheet(wb, "Info"); writeData(wb, "Info", info)
addStyle(wb, "Info", createStyle(textDecoration = "bold"), rows = 1, cols = 1)
setColWidths(wb, "Info", cols = 1, widths = 120)
d2 <- review_sheet(wb, "rows", d, proposal_col = "proposed_action", decision_col = "your_decision",
                   widths = c(40, 52, 9, 78, 6, 7, 9, 60, 10, 62, 16))
addStyle(wb, "rows", createStyle(fontColour = "#0563C1", textDecoration = "underline"),
         rows = 2:(nrow(d2) + 1), cols = which(names(d2) == "open_pdf"), gridExpand = TRUE)
worksheetOrder(wb) <- c(1, 2)
out <- file.path(root, "outputs", paste0("filename_collisions_", format(Sys.Date(), "%Y-%m-%d"), ".xlsx"))
save_review_workbook(wb, out)
cat("wrote", out, "\n", nrow(d), "rows across", n_files, "files\n")
