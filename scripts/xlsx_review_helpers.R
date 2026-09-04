# Shared formatting for review workbooks, so every sheet the user works
# through obeys the same house style and the rules live in one place.
#
#   source(file.path(dirname(this_file), "xlsx_review_helpers.R"))

suppressPackageStartupMessages(library(openxlsx))

# openxlsx declares a drawing and a vmlDrawing relationship on every sheet but
# only writes those parts when the sheet has one.  Excel and LibreOffice
# tolerate the dangling reference; openpyxl raises KeyError on it, and the
# scripts that apply a reviewed workbook read it back with openpyxl.  So strip
# the references that point at nothing.
strip_dangling_rels <- function(xlsx) {
  tmp <- file.path(tempdir(), paste0("xlsxfix_", basename(xlsx)))
  unlink(tmp, recursive = TRUE)
  dir.create(tmp, recursive = TRUE)
  utils::unzip(xlsx, exdir = tmp)
  present <- basename(list.files(file.path(tmp, "xl", "drawings")))
  for (rels in list.files(file.path(tmp, "xl", "worksheets", "_rels"),
                          full.names = TRUE)) {
    xml <- readLines(rels, warn = FALSE)
    parts <- regmatches(xml, gregexpr("<Relationship [^>]*/>", xml))[[1]]
    drop <- parts[grepl("drawings/", parts, fixed = TRUE) &
                    !basename(sub('.*Target="([^"]*)".*', "\\1", parts)) %in% present]
    for (d in drop) xml <- sub(d, "", xml, fixed = TRUE)
    writeLines(xml, rels)
  }
  files <- list.files(tmp, recursive = TRUE, all.files = TRUE, no.. = TRUE)
  owd <- setwd(tmp); on.exit(setwd(owd), add = TRUE)
  unlink(xlsx)
  utils::zip(xlsx, files, flags = "-qX")
}

# Standing house style: frozen top row, bold header, autofilter across the
# header, compact explicit widths (never "auto", which produces giant
# columns), and info-low columns hidden so the sheet fits one screen.
style_review_sheet <- function(wb, sheet, data, widths, hide = character()) {
  n <- ncol(data)
  freezePane(wb, sheet, firstRow = TRUE)
  addStyle(wb, sheet, createStyle(textDecoration = "bold"),
           rows = 1, cols = seq_len(n))
  addFilter(wb, sheet, rows = 1, cols = seq_len(n))
  setColWidths(wb, sheet, cols = seq_len(n), widths = widths)
  hidden <- which(names(data) %in% hide)
  if (length(hidden)) {
    setColWidths(wb, sheet, cols = hidden, widths = 10, hidden = TRUE)
  }
  invisible(wb)
}

# Short one-click link rather than a full-URL column.  writeFormula supplies
# the leading "=" itself, and escapes the "&" in "Papers & Books".
folder_links <- function(paths) {
  sprintf('HYPERLINK("file://%s","open")', utils::URLencode(dirname(paths)))
}

# Link straight at the file. A folder link makes the reader hunt for the row's
# PDF among everything filed that year, and the year folder is often not the
# one they expect, because a misfiled paper sits under ITS year, not the
# document's.
file_links <- function(paths, label = "open") {
  sprintf('HYPERLINK("file://%s","%s")', utils::URLencode(paths), label)
}

# openxlsx::read.xlsx returns cell text still XML-escaped, so a path through
# "Papers & Books" comes back as "Papers &amp; Books" and matches nothing.
# The written file is correct; only the reader is at fault. A workbook that
# has been through Excel or LibreOffice comes back unescaped, which is why
# this only bites on openxlsx-written files.
unescape_xml <- function(x) {
  if (!is.character(x)) return(x)
  x <- gsub("&lt;", "<", x, fixed = TRUE)
  x <- gsub("&gt;", ">", x, fixed = TRUE)
  x <- gsub("&quot;", '"', x, fixed = TRUE)
  x <- gsub("&apos;", "'", x, fixed = TRUE)
  gsub("&amp;", "&", x, fixed = TRUE)     # last, or the others double-unescape
}

read_review_sheet <- function(path, sheet) {
  df <- openxlsx::read.xlsx(path, sheet = sheet)
  df[] <- lapply(df, unescape_xml)
  df
}

add_info_sheet <- function(wb, title, lines) {
  # The column name becomes the header row, so it carries the title; the body
  # must not repeat it.
  info <- data.frame(x = lines, stringsAsFactors = FALSE)
  names(info) <- title
  addWorksheet(wb, "Info")
  writeData(wb, "Info", info)
  setColWidths(wb, "Info", cols = 1, widths = 100)
  addStyle(wb, "Info", createStyle(textDecoration = "bold", fontSize = 12),
           rows = 1, cols = 1)
  invisible(wb)
}
