# Copied 2026-09-23 from /media/simon/data/Programs/pics/CLAUDEFILES/review_sheet_helper.R
# so this project enforces the same contract. The rules it encodes are in that
# project's CLAUDEFILES/XLSX-REVIEW-GUIDE.md: decision column last, a proposal
# column before it, empty/constant columns hidden, Info tab first, frozen bold
# autofiltered header, and file:// links percent-encoded with
# utils::URLencode(p, reserved = FALSE).
# Shared writer for every review sheet in this project.
# Enforces Simon's layout contract (2026-08-24) so it cannot be forgotten:
#   * his decision column is ALWAYS last
#   * a PROPOSAL column sits immediately before it
#   * columns that are entirely empty are HIDDEN
#   * plus the standing format: frozen top row, bold header, autofilter
suppressMessages(library(openxlsx))

# directory of this helper, so the drawings fixer beside it is always found
HELPER_DIR <- tryCatch(dirname(normalizePath(sys.frame(1)$ofile)), error = function(e) ".")

# Capture the user's VIEW STATE from a workbook before it is replaced, so a
# rebuild does not cost him his place. Simon, 2026-08-26.
capture_view <- function(path, sheet) {
  if (!file.exists(path)) return(NULL)
  tryCatch({
    wb <- openxlsx::loadWorkbook(path)
    if (!sheet %in% names(wb)) return(NULL)
    i <- which(names(wb) == sheet)
    list(widths = wb$colWidths[[i]],
         freeze = wb$freezePane[[i]],
         filter = wb$autoFilter[[i]],
         view   = wb$worksheets[[i]]$sheetViews)
  }, error = function(e) NULL)
}

restore_view <- function(wb, sheet, st) {
  if (is.null(st)) return(invisible(FALSE))
  i <- which(names(wb) == sheet)
  if (!length(i)) return(invisible(FALSE))
  tryCatch({
    if (!is.null(st$widths)) wb$colWidths[[i]] <- st$widths
    if (!is.null(st$freeze)) wb$freezePane[[i]] <- st$freeze
    if (!is.null(st$filter)) wb$autoFilter[[i]] <- st$filter
    # sheetViews carries zoom, the top-left visible cell and the selection
    if (!is.null(st$view)) wb$worksheets[[i]]$sheetViews <- st$view
    message(sprintf("  %s: restored column widths, hidden columns, filter, zoom and scroll position", sheet))
    invisible(TRUE)
  }, error = function(e) invisible(FALSE))
}

review_sheet <- function(wb, sheet, d, proposal_col = "proposal",
                         decision_col = "decision", widths = "auto",
                         restore_from = NULL) {
  if (!decision_col %in% names(d)) d[[decision_col]] <- ""
  if (!proposal_col %in% names(d)) d[[proposal_col]] <- ""
  others <- setdiff(names(d), c(proposal_col, decision_col))
  d <- d[, c(others, proposal_col, decision_col), drop = FALSE]

  # Reordering columns drops openxlsx's "formula" class, which silently turns a
  # working =HYPERLINK into inert text. Restore it for anything that looks like
  # a formula, so the link cannot break again from a column move.
  for (n in names(d)) {
    v <- as.character(d[[n]])
    if (length(v) && any(!is.na(v) & startsWith(trimws(v), "="))) {
      d[[n]] <- v; class(d[[n]]) <- "formula"
    }
  }

  if (!sheet %in% names(wb)) addWorksheet(wb, sheet)
  writeData(wb, sheet, d)
  freezePane(wb, sheet, firstRow = TRUE)
  addStyle(wb, sheet, createStyle(textDecoration = "bold"),
           rows = 1, cols = seq_len(ncol(d)), gridExpand = TRUE)
  addFilter(wb, sheet, rows = 1, cols = seq_len(ncol(d)))
  setColWidths(wb, sheet, seq_len(ncol(d)), widths = widths)

  # Hide any column that carries no information: entirely empty, or the same
  # value on every row. A constant column is a TAB-LEVEL fact sitting in a
  # row-level slot -- it belongs on Info, not beside the data. Simon,
  # 2026-08-31, on the dedupe proposal column ("all entries for this column are
  # the same rendering it obsolete from a database POV"). Never the proposal or
  # decision column, which must stay visible even when uniform.
  blank <- function(x) all(is.na(x) | !nzchar(trimws(as.character(x))))
  const <- function(x) {
    v <- trimws(as.character(x)); v <- v[!is.na(v) & nzchar(v)]
    length(v) > 1 && length(unique(v)) == 1 && length(v) == nrow(d)
  }
  empty <- vapply(d, blank, TRUE)
  flat  <- vapply(d, const, TRUE) & !empty
  dead  <- empty | flat
  dead[c(proposal_col, decision_col)] <- FALSE
  if (any(dead)) {
    setColWidths(wb, sheet, which(dead), widths = 8.43, hidden = TRUE)
    if (any(empty & dead)) message(sprintf("  %s: hid %d empty column(s): %s",
      sheet, sum(empty & dead), paste(names(d)[empty & dead], collapse = ", ")))
    if (any(flat & dead)) message(sprintf("  %s: hid %d constant column(s): %s",
      sheet, sum(flat & dead), paste(names(d)[flat & dead], collapse = ", ")))
  }
  if (!is.null(restore_from)) restore_view(wb, sheet, capture_view(restore_from, sheet))
  invisible(d)
}

# Save a review workbook, then strip the dangling drawing references openxlsx
# writes into every sheet's .rels. openxlsx reads its own output fine, so the
# defect is invisible from R, but openpyxl and other readers fail outright on
# the missing xl/drawings/drawingN.xml. These workbooks are the deliverable,
# so they must open anywhere. Simon, 2026-08-28.
save_review_workbook <- function(wb, path, overwrite = TRUE) {
  openxlsx::saveWorkbook(wb, path, overwrite = overwrite)
  # this project's paths contain spaces, so every argument is quoted
  fixer <- file.path(HELPER_DIR, "fix_xlsx_drawings.py")
  if (file.exists(fixer)) {
    system2("python3", c(shQuote(fixer), shQuote(normalizePath(path))), stdout = NULL)
  }
  invisible(path)
}
