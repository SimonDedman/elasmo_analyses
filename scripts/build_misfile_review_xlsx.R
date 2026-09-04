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

# read.csv types an entirely-empty column as logical, so a run with no
# cross-check hits would hand file_links() a vector of NA and stop the build.
for (col in c("correct_copy_path", "correct_copy_elsewhere", "decision",
              "notes", "pdf_holds_instead", "pdf_starts", "absent_title",
              "why", "how_sure")) {
  if (!is.null(mis[[col]])) {
    mis[[col]] <- as.character(mis[[col]])
    mis[[col]][is.na(mis[[col]])] <- ""
  }
}

# Carry forward decisions already made, keyed on the file itself so a
# renumbered group or a reordered sheet cannot lose them.
prior_path <- Sys.getenv("PRIOR_REVIEW", "")
n_carried <- 0
if (nzchar(prior_path) && file.exists(prior_path)) {
  prior <- read_review_sheet(prior_path, "misfiled")
  keep <- prior[nzchar(trimws(ifelse(is.na(prior$decision), "", prior$decision))) |
                  nzchar(trimws(ifelse(is.na(prior$notes), "", prior$notes))), ]
  m <- match(mis$absent_path, keep$absent_path)
  mis$decision <- ifelse(is.na(m), "", keep$decision[m])
  mis$notes <- ifelse(is.na(m), "", keep$notes[m])
  mis$decision[is.na(mis$decision)] <- ""
  mis$notes[is.na(mis$notes)] <- ""
  n_carried <- sum(nzchar(mis$decision))
  cat(sprintf("  carried %d decisions forward from %s\n",
              n_carried, basename(prior_path)))
}

# Totals for the Info tab come from the checker's own verdicts, never
# transcribed, so they cannot go stale against the sheet beside them.
verdicts <- fromJSON(file.path(out_dir, "misfiled_verdicts.json"),
                     simplifyDataFrame = FALSE)
v <- vapply(verdicts, function(x) x$verdict, character(1))
n_tested <- length(v)
n_container <- sum(v == "container")
n_untestable <- sum(startsWith(v, "untestable"))

n_strong <- sum(mis$how_sure == "strong")
n_short <- sum(mis$how_sure == "short title")
n_check <- sum(mis$how_sure == "check the scan")
n_groups <- length(unique(mis$group_id))

# One legible evidence cell instead of two raw counts.
mis$title_words_found <- sprintf("%d of %d", mis$words_found, mis$words_sought)

# Confident findings first, then the biggest groups; rows flagged as probable
# checker failures sort to the bottom, still reachable by the filter.
mis <- mis[order(mis$how_sure != "strong", -mis$n_records, mis$record_year), ]
links <- file_links(mis$absent_path)
mis$open_pdf <- ""
n_correct <- sum(nzchar(mis$correct_copy_elsewhere))

# English glosses for the non-English titles and document openings. Hand
# translated into data/lookup_title_translations.csv rather than guessed at runtime,
# so they are reviewable and versioned.
gloss_file <- file.path(proj, "data", "lookup_title_translations.csv")
mis$english_gloss <- ""
if (file.exists(gloss_file)) {
  gl <- read.csv(gloss_file, stringsAsFactors = FALSE)
  for (k in seq_len(nrow(gl))) {
    hit <- grepl(gl$original[k], mis$absent_title, fixed = TRUE) |
           grepl(gl$original[k], mis$pdf_holds_instead, fixed = TRUE) |
           grepl(gl$original[k], mis$pdf_starts, fixed = TRUE)
    mis$english_gloss[hit] <- ifelse(
      nzchar(mis$english_gloss[hit]),
      paste(mis$english_gloss[hit], gl$english[k], sep = " | "),
      sprintf("[%s] %s", gl$language[k], gl$english[k]))
  }
  cat(sprintf("  glossed %d rows from %d translations\n",
              sum(nzchar(mis$english_gloss)), nrow(gl)))
}

mis$open_correct <- ""
correct_links <- ifelse(nzchar(mis$correct_copy_path),
                        file_links(mis$correct_copy_path, "open"), "")

mis <- mis[, c("group_id", "how_sure", "record_year", "absent_title",
               "pdf_year", "pdf_holds_instead", "correct_copy_elsewhere",
               "open_correct", "pdf_starts", "english_gloss",
               "title_words_found", "open_pdf",
               "decision", "notes", "why", "n_records", "size_mb",
               "words_found", "words_sought", "latin_fraction", "n_words",
               "absent_path", "correct_copy_path", "sha256")]

info_lines <- c(
  sprintf("Generated %s by scripts/check_misfiled_pdfs.py.", today),
  "",
  "WHY THIS EXISTS",
  "Several papers can legitimately share one PDF: a scanned journal volume backs every",
  "article in it. But a shared PDF can also mean the ingest matcher filed one paper's",
  "file under another paper's name, and from outside the file the two look identical.",
  "",
  "So every PDF named by more than one record was text-extracted in full, and each",
  "naming paper's title looked for inside it. A real volume contains all its articles.",
  sprintf("A misfile contains no trace of the paper it is filed as. %d PDFs were tested;",
          n_tested),
  sprintf("%d are genuine containers and are not listed here. %d records across %d PDFs",
          n_container, nrow(mis), n_groups),
  "are absent from the file they name.",
  "",
  "WHY THIS MATTERS BEYOND TIDINESS",
  "Schema extraction ran over whatever PDF was on disk. Every record listed here has",
  "columns in the enriched parquet describing a different paper.",
  "",
  "HOW TO JUDGE A ROW (this is the whole job)",
  "The question is only ever: is the paper named in 'absent_title' inside this PDF?",
  "",
  "1. Read 'absent_title' — what the filename claims the file is.",
  "2. Read 'pdf_starts' — the first 160 words of the actual document, usually the",
  "   journal line and title. In most rows that alone settles it.",
  "3. Read 'pdf_holds_instead' — the paper that IS in the file, named by another",
  "   record. Where it says '(none of the naming papers)', no record naming this PDF",
  "   was found in it, which is the strongest case of all.",
  sprintf("4. Read 'correct_copy_elsewhere'. On %d rows the paper the filename claims is", n_correct),
  "   ALREADY filed correctly under another name, verified to be in that file, and",
  "   'open_correct' opens it. Those rows are the easy ones: the misfiled name is a",
  "   spurious extra, and deleting it loses no paper. A blank means only that this",
  "   method did not find a home, not that none exists.",
  "5. Where a title or document opening is not in English, 'english_gloss' carries a",
  "   translation. These are hand-translated in data/lookup_title_translations.csv, not",
  "   machine output, so check them if a decision turns on one.",
  "6. If still unsure, click 'open_pdf'. It opens THAT ROW'S file directly.",
  "7. Put a value in 'decision':",
  "      MISFILED   confirmed, the file is not the paper the filename claims",
  "      CONTAINER  the checker is wrong, the paper IS in there",
  "      UNSURE     needs a closer look than this sheet supports",
  "",
  "A WORKED ROW",
  "  absent_title      Birth of guitarfish, Zapteryx brevirostris ...",
  "  record_year       2004",
  "  pdf_starts        Bolm Inst. oceanogr., S Paulo, 27(2):95-152, 1978 AN ANNOTATED",
  "                    BIBLIOGRAPHY OF PARASITIC ISOPODA (CRUSTACEA) OF CHONDRICHTHYES",
  "  pdf_holds_instead An annotated bibliography of parasitic Isopoda (Crustacea)",
  "  title_words_found 0 of 7",
  "The file is a 1978 parasitic-isopod bibliography. It is not a 2004 guitarfish birth",
  "note. Decision: MISFILED.",
  "",
  "WHY THERE ARE TWO YEAR COLUMNS",
  "'record_year' is the year of the paper the filename claims, and the year folder the",
  "file sits in. 'pdf_year' is the year of the paper actually in the document. They",
  "differ on most rows here, which is itself part of the evidence.",
  "",
  "HOW FAR TO TRUST EACH ROW",
  "The 'how_sure' column is about the quality of the EVIDENCE, never about how bad the",
  "verdict sounds. The 'why' column spells out the basis for that row. Rows that are",
  "not 'strong' are highlighted and sorted to the bottom.",
  "",
  sprintf("  strong          %d rows. Plenty of clean text, and enough testable title", n_strong),
  "                  words, so a title that is not found is genuinely not there.",
  sprintf("  short title     %d rows. The filename is abbreviated so hard that only three", n_short),
  "                  or four words remain to test, which cannot settle it either way.",
  "                  '3D mov hab select jGWS NY Bight' is the same paper as",
  "                  'Three-Dimensional Movements and Habitat Selection of Young White",
  "                  Sharks', and no word-matching rule can see that.",
  sprintf("  check the scan  %d rows. Either the PDF is mostly non-Latin script (Japanese", n_check),
  "                  society bulletins, whose Latin titles cannot be OCRed) or too",
  "                  little text came out. On these, 'absent' is more likely the",
  "                  checker failing than a misfile.",
  "",
  "WHAT HAS ALREADY BEEN DONE AUTOMATICALLY",
  "- The whole library was hashed to find PDFs named by more than one paper.",
  "- Each was text-extracted (cached in outputs/.pdf_text_cache) and every naming",
  "  paper's title searched for inside it.",
  "- Title words are matched by PREFIX, because filenames abbreviate them",
  "  ('Bioturb stingray Ningaloo'). Literal matching produced 44 false accusations",
  "  against correctly-filed papers before this was fixed.",
  "- A leading or trailing 'i' is also tried stripped: BibTeX italic markup loses its",
  "  angle brackets upstream, so '<i>Tursiops aduncus</i>' reaches the filename as",
  "  'iTursiops aduncusi' and looked absent from a document that plainly held it.",
  "- A record whose title nearly matches one that IS in the document is treated as a",
  "  duplicate filename, not a misfile, and is excluded from this sheet.",
  sprintf("- 'Could not be tested' is kept separate from 'absent' and is NOT listed here: %d",
          n_untestable),
  "  PDFs had too little text or too short a title to judge either way.",
  "- NOTHING HAS BEEN DELETED OR CHANGED. This workbook is the gate.",
  "",
  "ONE GROUP TO LOOK AT FIRST",
  "Nineteen separate 2021 shark records share a single 0.7 MB PDF which is",
  "'NOMES DE LUGAR: CONFIM', a 2005 article from Revista de Letras, a literature",
  "journal. None of the nineteen is in it, and the text came out clean (3,982 words,",
  "96% Latin script), so this is not an extraction failure.",
  "",
  "WHAT HAPPENS AFTERWARDS (not yet built, and your call)",
  "A confirmed MISFILED row means that filename should go, and the paper it claimed",
  "returns to the needs-a-PDF list. Deleting the file is safe and frees NAS space; it",
  "is hardlinked to its correctly-named sibling, so removing the wrong name drops one",
  "link and leaves the real paper untouched. The record's extracted schema columns",
  "should also be invalidated, which is the larger piece of work.",
  "",
  "PROVENANCE AND KNOWN GAPS",
  "- Source: scripts/check_misfiled_pdfs.py over the SharkPapers library.",
  "- Only papers sharing a BYTE-IDENTICAL PDF are examined. A record pointing at the",
  "  wrong paper's file where no other record shares it is invisible to this method.",
  "- A 12-row hand audit of an earlier pass found 10 genuine misfiles and 2 false",
  "  positives, both Japanese-language bulletins, now flagged 'check the scan'.",
  "- This does not identify the correct PDF for any record; it only establishes that",
  "  the current one is wrong."
)

wb <- createWorkbook()
add_info_sheet(wb, "Misfiled PDF review", info_lines)

addWorksheet(wb, "misfiled")
writeData(wb, "misfiled", mis, keepNA = FALSE)
writeFormula(wb, "misfiled", x = links,
             startCol = which(names(mis) == "open_pdf"), startRow = 2)
has_correct <- which(nzchar(correct_links))
for (i in has_correct) {
  writeFormula(wb, "misfiled", x = correct_links[i],
               startCol = which(names(mis) == "open_correct"), startRow = i + 1)
}

style_review_sheet(
  wb, "misfiled", mis,
  widths = c(8, 15, 8, 54, 8, 48, 48, 8, 70, 60, 14, 8, 12, 28, 60,
             9, 8, 8, 8, 8, 8, 10, 10, 10),
  hide = c("words_found", "words_sought", "latin_fraction", "n_words",
           "absent_path", "correct_copy_path", "sha256"))

dataValidation(wb, "misfiled", col = which(names(mis) == "decision"),
               rows = 2:(nrow(mis) + 1), type = "list",
               value = '"MISFILED,CONTAINER,UNSURE"')

flagged <- which(mis$how_sure != "strong") + 1
if (length(flagged)) {
  addStyle(wb, "misfiled", createStyle(fgFill = "#FFF2CC"), rows = flagged,
           cols = seq_len(ncol(mis)), gridExpand = TRUE, stack = TRUE)
}

worksheetOrder(wb) <- c(1, 2)
out <- file.path(out_dir, sprintf("misfiled_pdf_review_%s.xlsx", today))
saveWorkbook(wb, out, overwrite = TRUE)
strip_dangling_rels(out)
cat("wrote", out, "\n")
cat(sprintf("  %d records across %d PDFs (%d strong, %d short title, %d check the scan)\n",
            nrow(mis), n_groups, n_strong, n_short, n_check))
