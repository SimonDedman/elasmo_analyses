#!/usr/bin/env Rscript
# Build the review workbook for corpus records whose PDF is not the paper
# they name.
#
# Reads outputs/misfiled_records.csv, written by:
#   python3 scripts/check_misfiled_pdfs.py --csv outputs/misfiled_records.csv
# All judgement happens in the Python checker; this only formats.

here <- dirname(sub("--file=", "", grep("--file=", commandArgs(trailingOnly = FALSE),
                                        value = TRUE)[1]))
source(file.path(here, "xlsx_review_helpers.R"))
suppressPackageStartupMessages(library(jsonlite))

proj <- normalizePath(file.path(here, ".."))
out_dir <- file.path(proj, "outputs")
today <- format(Sys.Date(), "%Y-%m-%d")

mis <- read.csv(file.path(out_dir, "misfiled_records.csv"),
                stringsAsFactors = FALSE, check.names = FALSE)
stopifnot(nrow(mis) > 0)

# Totals for the Info tab come from the checker's own verdicts, never
# transcribed, so they cannot go stale against the sheet beside them.
verdicts <- jsonlite::fromJSON(file.path(out_dir, "misfiled_verdicts.json"),
                               simplifyDataFrame = FALSE)
v <- vapply(verdicts, function(x) x$verdict, character(1))
n_tested <- length(v)
n_container <- sum(v == "container")
n_untestable <- sum(startsWith(v, "untestable"))

n_auto <- sum(mis$confidence == "auto")
n_flag <- sum(mis$confidence != "auto")
n_groups <- length(unique(mis$group_id))

mis$open <- ""

# Confident findings first, biggest groups next; the rows flagged as probable
# tool failures sort to the bottom, where the highlight and the confidence
# filter still make them easy to reach.
mis <- mis[order(mis$confidence != "auto", -mis$n_records, mis$year),
           c("group_id", "year", "confidence", "absent_title",
             "pdf_holds_instead", "pdf_starts", "n_records", "size_mb",
             "open", "decision", "notes", "latin_fraction", "n_words",
             "absent_path", "sha256")]
links <- folder_links(mis$absent_path)

info_lines <- c(
  sprintf("Generated %s by scripts/check_misfiled_pdfs.py.", today),
  "",
  "WHY THIS EXISTS",
  "Several papers can legitimately share one PDF: a scanned journal volume backs every",
  "article in it. But a shared PDF can also mean the ingest matcher filed one paper's",
  "file under another paper's name, and the two look identical from the outside.",
  "",
  "Every PDF named by more than one record was text-extracted in full, and each naming",
  "paper's title looked for inside it. A real volume contains all its articles. A",
  sprintf("misfile contains no trace of the paper it is filed as. %d PDFs were tested;",
          n_tested),
  sprintf("%d are genuine containers and are not listed here. %d records across %d PDFs",
          n_container, nrow(mis), n_groups),
  "are absent from the file they name.",
  "",
  "WHY THIS MATTERS BEYOND TIDINESS",
  "Schema extraction ran over whatever PDF was on disk. Every record listed here has",
  "columns in the enriched parquet describing a different paper.",
  "",
  "WHAT HAS ALREADY BEEN DONE AUTOMATICALLY",
  "- The whole library was hashed to find PDFs named by more than one paper.",
  "- Each was text-extracted (cached in outputs/.pdf_text_cache) and every naming",
  "  paper's title searched for inside it.",
  "- Title words are matched by PREFIX, because filenames abbreviate them",
  "  ('Bioturb stingray Ningaloo'). Literal matching produced 44 false accusations",
  "  against correctly-filed papers before this was fixed.",
  "- 'Could not be tested' is kept separate from 'absent' and is NOT listed here:",
  sprintf("  %d PDFs had too little text or too short a title to judge either way.",
          n_untestable),
  "- NOTHING HAS BEEN DELETED OR CHANGED. This workbook is the gate.",
  "",
  "WHAT YOU NEED TO DO",
  "1. Open the 'misfiled' tab. Each row is one record whose PDF is the wrong paper.",
  "2. Read 'absent_title' (what the filename claims) against 'pdf_holds_instead'",
  "   (the paper that IS in the file) and 'pdf_starts' (the document's opening words).",
  "   'open' opens the containing folder.",
  "3. Fill 'decision' on every row. Accepted values:",
  "      MISFILED   confirmed: the filename claims a paper the file does not contain",
  "      CONTAINER  the checker is wrong: the paper IS in there",
  "      UNSURE     needs a closer look",
  "   Use 'notes' for anything worth recording.",
  sprintf("4. %d rows are confidence = auto. %d are flagged and need a real look:", n_auto, n_flag),
  "      check_ocr          the scan is mostly non-Latin script (Japanese society",
  "                         bulletins), so Latin titles cannot be OCRed and 'absent'",
  "                         is probably the tool failing, not a misfile",
  "      check_thin_text    little extractable text, so a miss is weak evidence",
  "      check_none_matched NONE of the naming papers were found, which more often",
  "                         means bad extraction than several simultaneous misfiles",
  "5. Save the workbook and say so.",
  "",
  "WHAT HAPPENS AFTERWARDS (not yet built, and your call)",
  "A confirmed MISFILED row means that filename should go, and the paper it claimed",
  "returns to the needs-a-PDF list. Deleting the file is safe and frees NAS space; the",
  "file is hardlinked to its correctly-named sibling, so removing the wrong name drops",
  "one link and leaves the real paper untouched. The record's extracted schema columns",
  "should also be invalidated, which is the larger piece of work.",
  "",
  "ONE GROUP TO LOOK AT FIRST",
  "Nineteen separate 2021 shark records share a single 0.7 MB PDF which is",
  "'NOMES DE LUGAR: CONFIM', a 2005 article from Revista de Letras, a literature",
  "journal. None of the nineteen is in it.",
  "",
  "PROVENANCE AND KNOWN GAPS",
  "- Source: scripts/check_misfiled_pdfs.py over the SharkPapers library.",
  "- Only papers sharing a BYTE-IDENTICAL PDF are examined. A record pointing at the",
  "  wrong paper's file where no other record shares it is invisible to this method.",
  "- A 12-row hand audit of an earlier pass found 10 genuine misfiles and 2 false",
  "  positives, both Japanese-language bulletins now flagged check_ocr.",
  "- This does not identify the correct PDF for any record; it only establishes that",
  "  the current one is wrong."
)

wb <- createWorkbook()
add_info_sheet(wb, "Misfiled PDF review", info_lines)

addWorksheet(wb, "misfiled")
writeData(wb, "misfiled", mis, keepNA = FALSE)
writeFormula(wb, "misfiled", x = links,
             startCol = which(names(mis) == "open"), startRow = 2)

style_review_sheet(
  wb, "misfiled", mis,
  widths = c(8, 6, 18, 58, 58, 70, 9, 8, 6, 12, 30, 8, 8, 10, 10),
  hide = c("latin_fraction", "n_words", "absent_path", "sha256"))

dataValidation(wb, "misfiled", col = which(names(mis) == "decision"),
               rows = 2:(nrow(mis) + 1), type = "list",
               value = '"MISFILED,CONTAINER,UNSURE"')

flagged <- which(mis$confidence != "auto") + 1
if (length(flagged)) {
  addStyle(wb, "misfiled", createStyle(fgFill = "#FFF2CC"), rows = flagged,
           cols = seq_len(ncol(mis)), gridExpand = TRUE, stack = TRUE)
}

worksheetOrder(wb) <- c(1, 2)
out <- file.path(out_dir, sprintf("misfiled_pdf_review_%s.xlsx", today))
saveWorkbook(wb, out, overwrite = TRUE)
strip_dangling_rels(out)
cat("wrote", out, "\n")
cat(sprintf("  %d records across %d PDFs (%d auto, %d flagged for a closer look)\n",
            nrow(mis), n_groups, n_auto, n_flag))
