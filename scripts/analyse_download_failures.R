#!/usr/bin/env Rscript
# Build outputs/download_failures_<date>.xlsx — a structural review of why
# Phase 4 PDF downloads fail, so patterns can be attacked in classes rather
# than one paper at a time.
#
# Runs against a partial log while the sync is still going, so the taxonomy can
# be validated early; re-run at completion for the real figures. The Info tab
# always states which it is.
#
# The lever this is really looking for: SR gives us ONE url per paper, and when
# that url is the publisher's paywalled landing page the download fails even
# though a free copy exists elsewhere. Cross-referencing failures against the
# Unpaywall cache turns "403 Forbidden" into "we already know where this is".
#
# Usage:  Rscript scripts/analyse_download_failures.R [path/to/sr_sync_YYYYMMDD.log]

suppressPackageStartupMessages({
  library(jsonlite)
  library(openxlsx)
})

args <- commandArgs(trailingOnly = TRUE)
root <- normalizePath(file.path(dirname(sub("^--file=", "", grep("^--file=",
        commandArgs(trailingOnly = FALSE), value = TRUE)[1])), ".."))
setwd(root)

log_path <- if (length(args)) args[1] else {
  lg <- list.files("logs", pattern = "^sr_sync_2.*\\.log$", full.names = TRUE)
  lg[which.max(file.mtime(lg))]
}
stopifnot(file.exists(log_path))
message(sprintf("reading %s", log_path))
lines <- readLines(log_path, warn = FALSE)

# Is the run finished? Determines whether these are final numbers.
finished <- any(grepl("Sync complete|Phase 6", lines, fixed = FALSE))

# --- Extract one row per failure event --------------------------------------
# Three distinct failure shapes, kept separate because they need different
# fixes. Collapsing them would hide that "returned HTML" is a paywall while
# "blocked domain" is our own deliberate skip.
pat_http <- "Download failed for ([0-9]+): (.*)$"
pat_html <- "PDF URL returned HTML \\(likely paywall\\): (.*)$"
pat_block <- "Skipping blocked domain \\(([^)]+)\\): ([0-9]+)"

ev <- list()

hit <- grep(pat_http, lines, value = TRUE)
if (length(hit)) {
  m <- regmatches(hit, regexec(pat_http, hit))
  ev[[length(ev) + 1]] <- data.frame(
    literature_id = sapply(m, `[`, 2),
    failure_class = "http_error",
    detail        = sapply(m, `[`, 3),
    stringsAsFactors = FALSE)
}

hit <- grep(pat_html, lines, value = TRUE)
if (length(hit)) {
  m <- regmatches(hit, regexec(pat_html, hit))
  ev[[length(ev) + 1]] <- data.frame(
    literature_id = NA_character_,
    failure_class = "returned_html_paywall",
    detail        = sapply(m, `[`, 2),
    stringsAsFactors = FALSE)
}

hit <- grep(pat_block, lines, value = TRUE)
if (length(hit)) {
  m <- regmatches(hit, regexec(pat_block, hit))
  ev[[length(ev) + 1]] <- data.frame(
    literature_id = sapply(m, `[`, 3),
    failure_class = "blocked_domain_skipped",
    detail        = sapply(m, `[`, 2),
    stringsAsFactors = FALSE)
}

fail <- do.call(rbind, ev)
if (is.null(fail) || !nrow(fail)) stop("no failure events found in the log")
message(sprintf("failure events: %s", format(nrow(fail), big.mark = ",")))

# --- Derive structure from the detail string --------------------------------
fail$http_status <- sub(".*?([0-9]{3}) Client Error.*", "\\1", fail$detail)
fail$http_status[!grepl("^[0-9]{3}$", fail$http_status)] <- ""
srv <- grepl("Server Error", fail$detail)
fail$http_status[srv] <- sub(".*?([0-9]{3}) Server Error.*", "\\1",
                             fail$detail[srv])

url <- sub(".*for url: ", "", fail$detail)
url[!grepl("^https?://", url)] <- ifelse(
  grepl("^https?://", fail$detail[!grepl("^https?://", url)]),
  fail$detail[!grepl("^https?://", url)], NA_character_)
fail$url <- url
fail$domain <- sub("^https?://(www\\.)?([^/]+).*", "\\2", fail$url)
fail$domain[is.na(fail$url)] <- fail$detail[is.na(fail$url)]

# Timeouts, connection resets and the like carry no status code.
fail$http_status[fail$http_status == "" & grepl("Timeout|timed out",
                 fail$detail, ignore.case = TRUE)] <- "timeout"
fail$http_status[fail$http_status == "" &
                 fail$failure_class == "http_error"] <- "other"

# --- Join corpus metadata ----------------------------------------------------
papers <- fromJSON("docs/papers_data.json", simplifyDataFrame = TRUE)
papers$literature_id <- sub("\\.0$", "", as.character(papers$literature_id))
keep <- c("literature_id", "year", "authors", "title", "journal_clean",
          "doi", "publisher", "oa_status", "oa_url")
keep <- keep[keep %in% names(papers)]
fail <- merge(fail, papers[, keep], by = "literature_id", all.x = TRUE)

# --- The lever: does a free copy already exist? ------------------------------
# A failure whose DOI has a known OA location is not a lost paper, it is a
# wrong URL. Counting these separates "cannot get" from "asked the wrong place".
oa_known <- rep(NA_character_, nrow(fail))
oa_file <- "outputs/unpaywall_oa_by_doi.csv"
if (file.exists(oa_file)) {
  oa <- read.csv(oa_file, stringsAsFactors = FALSE)
  oa$doi_n <- tolower(trimws(oa$doi))
  idx <- match(tolower(trimws(fail$doi)), oa$doi_n)
  oa_known <- ifelse(!is.na(idx) & !is.na(oa$oa_url[idx]) &
                     nzchar(oa$oa_url[idx]), oa$oa_url[idx], NA_character_)
  message(sprintf("Unpaywall cache: %s DOIs", format(nrow(oa), big.mark = ",")))
}
fail$known_oa_url <- oa_known
fail$actionable <- ifelse(!is.na(fail$known_oa_url), "OA COPY KNOWN",
                   ifelse(fail$failure_class == "blocked_domain_skipped",
                          "deliberate skip", "needs a route"))

# --- Summaries ---------------------------------------------------------------
by_class <- as.data.frame(table(failure_class = fail$failure_class,
                                dnn = "failure_class"),
                          responseName = "n")
by_class <- by_class[order(-by_class$n), ]

dom <- as.data.frame(table(domain = fail$domain), responseName = "n")
dom <- dom[order(-dom$n), ]
dom$pct <- round(100 * dom$n / nrow(fail), 1)
# Split our own deliberate skips out of the failure count. Without this,
# biodiversitylibrary.org tops the table at 37% of all "failures" when not one
# of them was ever attempted: it is in SKIP_DOMAINS and has its own harvester
# in fetch_bhl_archive.py. Reading that as a download problem would send effort
# at a route that is already covered.
dom$deliberate_skips <- sapply(as.character(dom$domain), function(d)
  sum(fail$domain == d & fail$failure_class == "blocked_domain_skipped"))
dom$real_failures <- dom$n - dom$deliberate_skips
# How many of each domain's real failures already have a known free copy?
dom$with_known_oa <- sapply(as.character(dom$domain), function(d)
  sum(fail$domain == d & !is.na(fail$known_oa_url)))
dom$decision <- ""
dom$proposed_route <- ""
dom <- dom[order(-dom$real_failures, -dom$n),
           c("domain", "n", "deliberate_skips", "real_failures", "pct",
             "with_known_oa", "decision", "proposed_route")]
names(dom)[1] <- "domain"

st <- as.data.frame(table(http_status = fail$http_status), responseName = "n")
st <- st[order(-st$n), ]

# Stratified sample for manual inspection: up to 6 per domain across the top
# domains, so the review covers patterns rather than whatever sorted first.
set.seed(20260903)
top_domains <- head(as.character(dom$domain), 25)
samp <- do.call(rbind, lapply(top_domains, function(d) {
  rows <- fail[fail$domain == d, ]
  rows[sample(seq_len(nrow(rows)), min(6, nrow(rows))), ]
}))
samp_cols <- c("literature_id", "year", "title", "journal_clean", "publisher",
               "doi", "failure_class", "http_status", "domain", "known_oa_url",
               "actionable", "url")
samp_cols <- samp_cols[samp_cols %in% names(samp)]
samp <- samp[, samp_cols]
samp$title <- substr(samp$title, 1, 150)
samp$url <- substr(samp$url, 1, 180)
samp$pattern_noted <- ""
samp$proposed_fix <- ""

n_oa <- sum(!is.na(fail$known_oa_url))

# --- Info --------------------------------------------------------------------
info <- data.frame(c(
  "PHASE 4 DOWNLOAD FAILURES — STRUCTURAL REVIEW",
  sprintf("Generated %s from %s", format(Sys.time(), "%Y-%m-%d %H:%M %Z"),
          basename(log_path)),
  if (finished) "Run status: COMPLETE. These are final figures."
  else paste0("Run status: *** SYNC STILL RUNNING *** These are PARTIAL ",
              "figures from a log still being written. Re-run this script ",
              "when the sync finishes."),
  "",
  "WHY THIS EXISTS",
  "Shark-References gives us one URL per paper. When that URL is a publisher's",
  "paywalled landing page the fetch fails, even where a free copy exists",
  "elsewhere. The aim is to attack failures in CLASSES, by domain and status,",
  "rather than one paper at a time.",
  "",
  "HEADLINE",
  sprintf("- %s failure events across %d distinct domains.",
          format(nrow(fail), big.mark = ","), length(unique(fail$domain))),
  sprintf("- %s of those were never attempted: they are OUR deliberate skips",
          format(sum(fail$failure_class == "blocked_domain_skipped"),
                 big.mark = ",")),
  "  (biodiversitylibrary.org, elasmo.org), which have their own harvester in",
  "  fetch_bhl_archive.py. Sort By_domain on 'real_failures', not 'n'.",
  sprintf("- Genuine failures: %s.",
          format(sum(fail$failure_class != "blocked_domain_skipped"),
                 big.mark = ",")),
  sprintf("- %s of them (%.1f%%) have a KNOWN free copy in the Unpaywall cache.",
          format(n_oa, big.mark = ","), 100 * n_oa / nrow(fail)),
  "  Those are not lost papers, they are wrong URLs, and they are the cheapest",
  "  win available: retarget the fetcher at the known OA url.",
  "",
  "WHAT WAS ALREADY DONE AUTOMATICALLY",
  "- Split failures into three classes that need different fixes:",
  "    http_error             - the server refused (403/404/5xx/timeout)",
  "    returned_html_paywall  - we got a landing page, not a PDF",
  "    blocked_domain_skipped - our own deliberate skip (BHL, elasmo.org)",
  "- Extracted HTTP status and domain from each event.",
  "- Cross-referenced every failure's DOI against the Unpaywall cache.",
  "- Sampled up to 6 per domain across the top 25 domains, so the review sees",
  "  patterns rather than whatever happened to sort first.",
  "",
  "TAB 1: By_domain",
  "Every domain, its failure count, and how many already have a known free",
  "copy. This is the tab to work top-down.",
  "  1. For each domain worth attacking, set 'decision':",
  "       RETARGET_OA   - use the known OA url instead of SR's",
  "       NEEDS_LOGIN   - a team member's institutional access should get it",
  "       NEEDS_SCRAPER - the publisher needs specific handling",
  "       BLOCKED       - accept as unreachable, route to ILL",
  "       IGNORE        - not worth effort",
  "  2. Put the specific approach in 'proposed_route'.",
  "",
  "TAB 2: By_status and TAB 3: By_class",
  "Supporting cuts. A wall of 403s means authentication; a wall of 404s means",
  "SR's links have rotted and need re-resolving from the DOI.",
  "",
  "TAB 4: Sample_for_review",
  sprintf("%d rows, stratified across domains, with the real URL so a pattern",
          nrow(samp)),
  "can be confirmed by opening a few.",
  "  3. Fill 'pattern_noted' and 'proposed_fix' where you spot something.",
  "",
  "PROVENANCE AND KNOWN GAPS",
  "- Failure events come from the sync log, so a failure the worker did not",
  "  log does not appear here. The counts are of EVENTS, and a paper retried",
  "  twice contributes more than one event.",
  "- 'returned_html_paywall' events carry no literature_id in the log, so they",
  "  cannot be joined to corpus metadata and show blank title/journal.",
  "- The Unpaywall cache is a snapshot; a paper may have gone OA since."
), stringsAsFactors = FALSE)
names(info) <- "Phase 4 download failures"

# --- Write -------------------------------------------------------------------
wb <- createWorkbook()
hdr <- createStyle(textDecoration = "bold")
add_tab <- function(name, df, widths) {
  addWorksheet(wb, name)
  writeData(wb, name, df, headerStyle = hdr)
  freezePane(wb, name, firstRow = TRUE)
  addFilter(wb, name, rows = 1, cols = seq_len(ncol(df)))
  setColWidths(wb, name, seq_len(ncol(df)), widths)
}

addWorksheet(wb, "Info")
writeData(wb, "Info", info)
setColWidths(wb, "Info", 1, 92)
addStyle(wb, "Info", createStyle(textDecoration = "bold", fontSize = 12),
         rows = 1, cols = 1)

add_tab("By_domain", dom, c(38, 8, 15, 14, 7, 15, 16, 46))
add_tab("By_status", st, c(16, 10))
add_tab("By_class", by_class, c(26, 10))
add_tab("Sample_for_review", samp,
        c(12, 6, 52, 26, 20, 24, 20, 11, 26, 40, 16, 50, 30, 34)[seq_len(ncol(samp))])

worksheetOrder(wb) <- seq_len(length(wb$sheet_names))
out <- sprintf("outputs/download_failures_%s.xlsx", format(Sys.Date(), "%Y-%m-%d"))
saveWorkbook(wb, out, overwrite = TRUE)
source(file.path("scripts", "lib", "repair_xlsx.R"))
repair_xlsx(out)
message(sprintf("wrote %s  (%s failures, %s with a known OA copy)", out,
                format(nrow(fail), big.mark = ","),
                format(n_oa, big.mark = ",")))
if (!finished) message("NOTE: sync still running — these are PARTIAL figures.")
