# repair_xlsx.R — strip dangling drawing relationships from an openxlsx file.
#
# openxlsx writes a <Relationship ... Type=".../drawing" Target="../drawings/
# drawing1.xml"> into every sheet's .rels, but only emits xl/drawings/*.xml when
# the sheet actually carries an image or chart. On a plain data sheet the target
# is absent, so the workbook is structurally invalid: Excel and LibreOffice are
# tolerant enough to open it, but strict readers are not. openpyxl raises
#   KeyError: "There is no item named 'xl/drawings/drawing1.xml' in the archive"
# which breaks any programmatic round-trip of a review sheet we send out and get
# back.
#
# Usage:
#   source("scripts/lib/repair_xlsx.R")
#   saveWorkbook(wb, path, overwrite = TRUE)
#   repair_xlsx(path)

repair_xlsx <- function(path) {
  stopifnot(file.exists(path))
  path <- normalizePath(path)
  tmp <- file.path(tempdir(), paste0("repair_", basename(tempfile())))
  dir.create(tmp, recursive = TRUE, showWarnings = FALSE)
  on.exit(unlink(tmp, recursive = TRUE), add = TRUE)

  files <- utils::unzip(path, exdir = tmp)
  present <- sub(paste0("^", tools::file_path_sans_ext(tmp), "[^/]*/"), "",
                 sub(paste0("^", tmp, "/"), "", files))

  rels <- files[grepl("worksheets/_rels/.*\\.rels$", files)]
  changed <- 0L
  for (rf in rels) {
    xml <- readLines(rf, warn = FALSE)
    xml1 <- paste(xml, collapse = "")
    # Each <Relationship .../> is self-closing; drop whole tags whose Target
    # does not exist in the archive.
    tags <- regmatches(xml1, gregexpr("<Relationship\\b[^>]*/>", xml1))[[1]]
    drop <- character(0)
    for (tg in tags) {
      tgt <- sub('.*Target="([^"]+)".*', "\\1", tg)
      if (!grepl("^\\.\\./", tgt)) next
      resolved <- file.path("xl", sub("^\\.\\./", "", tgt))
      if (!(resolved %in% present)) drop <- c(drop, tg)
    }
    if (length(drop)) {
      for (tg in drop) xml1 <- sub(tg, "", xml1, fixed = TRUE)
      writeLines(xml1, rf)
      changed <- changed + length(drop)
    }
  }

  if (changed == 0L) return(invisible(FALSE))

  owd <- setwd(tmp); on.exit(setwd(owd), add = TRUE)
  inner <- list.files(".", recursive = TRUE, all.files = TRUE, no.. = TRUE)
  rebuilt <- file.path(tempdir(), basename(path))
  if (file.exists(rebuilt)) unlink(rebuilt)
  utils::zip(rebuilt, inner, flags = "-qX9")
  setwd(owd)
  file.copy(rebuilt, path, overwrite = TRUE)
  message(sprintf("repair_xlsx: dropped %d dangling relationship(s) from %s",
                  changed, basename(path)))
  invisible(TRUE)
}
