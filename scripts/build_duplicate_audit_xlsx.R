#!/usr/bin/env Rscript
# Build the review workbook for byte-identical PDFs in the SharkPapers library.
#
# Reads the two CSVs emitted by:
#   python3 scripts/dedupe_hardlink.py --scan --review-csvs outputs/
# and formats them.  All classification happens in the Python tool, so the
# sheet and the deletion that follows cannot disagree about which file is the
# redundant one.

here <- dirname(sub("--file=", "", grep("--file=", commandArgs(trailingOnly = FALSE),
                                        value = TRUE)[1]))
source(file.path(here, "xlsx_review_helpers.R"))

proj <- normalizePath(file.path(here, ".."))
out_dir <- file.path(proj, "outputs")

twins <- read.csv(file.path(out_dir, "duplicate_twins.csv"),
                  stringsAsFactors = FALSE, check.names = FALSE)
containers <- read.csv(file.path(out_dir, "shared_containers.csv"),
                       stringsAsFactors = FALSE, check.names = FALSE)

stopifnot(nrow(twins) > 0)

twin_gb <- sum(twins$size_mb) / 1024
cont_gb <- sum(containers$reclaimable_mb) / 1024
today <- format(Sys.Date(), "%Y-%m-%d")

# Short one-click link to the containing folder rather than a full-path column.
# writeFormula supplies the leading "=" itself.
twin_links <- sprintf('HYPERLINK("file://%s","open")',
                      utils::URLencode(dirname(twins$delete_path)))
twins$open <- ""

twins <- twins[, c("group_id", "year", "keep_name", "delete_name",
                   "difference", "confidence", "size_mb", "open",
                   "decision", "notes", "sha256", "keep_path",
                   "delete_path")]
open_col <- which(names(twins) == "open")

info <- data.frame(A = c(
  "Duplicate PDF audit: SharkPapers library",
  "",
  sprintf("Generated %s from a byte-identical (SHA-256) scan of the 20,558 PDFs in", today),
  "/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers",
  "",
  "WHY THIS EXISTS",
  "The library holds 518 groups of byte-identical PDFs: 1,212 files where 517 would do,",
  "wasting 11.15 GiB. They come from two different causes, which need different fixes.",
  "",
  sprintf("1. Redundant names (%d files, %.2f GiB). One paper stored under two filenames that", nrow(twins), twin_gb),
  "   differ only by a trailing full stop, a truncating comma, or an accent. One name is",
  "   leftover from an earlier punctuation-stripping pass. These are safe to delete, and",
  "   deleting them frees space on the NAS as well as locally. THIS IS THE 'twins' TAB.",
  "",
  sprintf("2. Shared containers (%d groups, %.2f GiB). Genuinely different papers whose source", nrow(containers), cont_gb),
  "   PDF is one scanned journal volume or issue. One 1880 volume backs sixteen separate",
  "   Jordan and Garman papers. These cannot be deleted: the corpus has no pdf_path column",
  "   and finds a paper by matching author, year, and title against the filename, so every",
  "   record needs its own name. THIS IS THE 'containers' TAB, for information only.",
  "",
  "WHAT HAS ALREADY BEEN DONE AUTOMATICALLY",
  "- The whole library was hashed and the 518 identical groups identified.",
  "- Each group was split into redundant names and distinct records.",
  "- For every redundant pair, the cleaner filename was chosen to keep, following house",
  "  style: no trailing punctuation, accents preferred over stripped ASCII.",
  "- Every pipeline script that writes a PDF was audited to confirm it writes to a temp",
  "  file and then os.replace()s it, so hardlinking cannot corrupt anything.",
  "- NOTHING HAS BEEN DELETED OR CHANGED. This workbook is the gate.",
  "",
  "WHAT YOU NEED TO DO",
  "1. Open the 'twins' tab. Each row is one file proposed for deletion.",
  "2. Read keep_name against delete_name. The 'difference' column says how they differ,",
  "   and 'open' opens the containing folder.",
  "3. Fill the 'decision' column on every row. Accepted values:",
  "      OK        delete delete_name, keep keep_name (this is the recommendation)",
  "      SWAP      the wrong one was picked: delete keep_name instead",
  "      KEEP BOTH do not delete either",
  "   Leave 'notes' for anything worth recording.",
  sprintf("4. %d of %d rows are marked confidence = auto: the two names differ only by trailing", sum(twins$confidence == "auto"), nrow(twins)),
  sprintf("   punctuation, so OK is almost certainly right. %d row is marked manual and needs a", sum(twins$confidence == "manual")),
  "   real look: the names differ by an accent or special character, where both spellings",
  "   are arguably wrong and the choice is editorial.",
  "5. Save the workbook and say so. Deletions run only on rows marked OK or SWAP.",
  "",
  "WHAT HAPPENS AFTERWARDS",
  "- The files you approved are deleted, and the deletions sync to the NAS.",
  "- Every remaining identical group is then collapsed onto a shared inode with hardlinks,",
  "  reclaiming the rest of the 11.15 GiB locally. All filenames survive; every tool sees",
  "  ordinary files. That saving is local only, because a sync client transfers content",
  "  per path and has no concept of a shared inode.",
  "",
  "PROVENANCE AND KNOWN GAPS",
  "- Source: scripts/dedupe_hardlink.py --scan, SHA-256 over every PDF whose byte size",
  "  collides with another. Exact duplicates only.",
  "- This does NOT find near-duplicates: rescans, re-encodes, or a preprint against its",
  "  published version. Those live in outputs/pdf_library_audit.xlsx, which is a separate",
  "  and still-open piece of work.",
  "- 'Redundant name' means the two filenames reduce to the same author, year, and title",
  "  once punctuation, accents, and case are removed. Two genuinely different papers with",
  "  titles identical bar punctuation would be misfiled here, which is why you review it."
), stringsAsFactors = FALSE)
names(info) <- "Duplicate PDF audit"

wb <- createWorkbook()
hdr <- createStyle(textDecoration = "bold")
wrap_manual <- createStyle(fgFill = "#FFF2CC")

addWorksheet(wb, "Info")
writeData(wb, "Info", info)
setColWidths(wb, "Info", cols = 1, widths = 100)
addStyle(wb, "Info", createStyle(textDecoration = "bold", fontSize = 12),
         rows = 1, cols = 1)

addWorksheet(wb, "twins")
writeData(wb, "twins", twins, keepNA = FALSE)
writeFormula(wb, "twins", x = twin_links, startCol = open_col, startRow = 2)

addWorksheet(wb, "containers")
writeData(wb, "containers", containers, keepNA = FALSE)

# Standing house style: frozen, bold, autofiltered header on every data tab.
for (sh in c("twins", "containers")) {
  n <- if (sh == "twins") ncol(twins) else ncol(containers)
  freezePane(wb, sh, firstRow = TRUE)
  addStyle(wb, sh, hdr, rows = 1, cols = 1:n)
  addFilter(wb, sh, rows = 1, cols = 1:n)
}

# Compact, content-appropriate widths; never setColWidths(..., "auto").
setColWidths(wb, "twins", cols = 1:ncol(twins),
             widths = c(8, 6, 58, 58, 22, 11, 8, 6, 12, 34, 14, 10, 10))
setColWidths(wb, "containers", cols = 1:ncol(containers),
             widths = c(8, 9, 9, 14, 10, 90, 14))

# Hide the long paths and the hash: needed by the deletion step, not by the eye.
setColWidths(wb, "twins",
             cols = which(names(twins) %in% c("sha256", "keep_path", "delete_path")),
             widths = 10, hidden = TRUE)
setColWidths(wb, "containers", cols = which(names(containers) == "sha256"),
             widths = 10, hidden = TRUE)

dataValidation(wb, "twins", col = which(names(twins) == "decision"),
               rows = 2:(nrow(twins) + 1), type = "list",
               value = '"OK,SWAP,KEEP BOTH"')

manual_rows <- which(twins$confidence == "manual") + 1
if (length(manual_rows)) {
  addStyle(wb, "twins", wrap_manual, rows = manual_rows,
           cols = 1:ncol(twins), gridExpand = TRUE, stack = TRUE)
}

worksheetOrder(wb) <- c(1, 2, 3)
out <- file.path(out_dir, sprintf("duplicate_pdf_audit_%s.xlsx", today))
saveWorkbook(wb, out, overwrite = TRUE)
strip_dangling_rels(out)
cat("wrote", out, "\n")
cat(sprintf("  twins: %d rows (%.2f GiB), containers: %d groups (%.2f GiB)\n",
            nrow(twins), twin_gb, nrow(containers), cont_gb))
