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
  library(arrow)
})

PARQUET <- "outputs/literature_review_enriched.parquet"

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
# Two formats: pre-2026-09-03 logs carry no literature_id on this line, later
# ones do. Both are parsed so historical logs stay analysable.
pat_html_id <- "PDF URL returned HTML \\(likely paywall\\) for ([0-9?]+): (.*)$"
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

hit <- grep(pat_html_id, lines, value = TRUE)
if (length(hit)) {
  m <- regmatches(hit, regexec(pat_html_id, hit))
  ev[[length(ev) + 1]] <- data.frame(
    literature_id = sapply(m, `[`, 2),
    failure_class = "returned_html_paywall",
    detail        = sapply(m, `[`, 3),
    stringsAsFactors = FALSE)
}

hit <- grep(pat_html, lines, value = TRUE)
hit <- hit[!grepl(pat_html_id, hit)]
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
stopifnot(all(c("title", "journal_clean") %in% keep))

# papers_data.json holds 34 duplicated literature_ids (11,877 rows, 11,839
# distinct) with CONFLICTING metadata: id 32101 appears twice with two
# different DOIs for the same title. Merging on a duplicated key silently
# fans out rows, so the failure count inflates and every percentage in this
# workbook is computed against a wrong denominator. Deduplicate first, and
# say how many were dropped rather than doing it quietly.
pmeta <- papers[, keep]
dupes <- sum(duplicated(pmeta$literature_id))
if (dupes) {
  message(sprintf("WARNING: papers_data.json has %d duplicate literature_ids; keeping first of each", dupes))
  pmeta <- pmeta[!duplicated(pmeta$literature_id), ]
}
before <- nrow(fail)
fail <- merge(fail, pmeta, by = "literature_id", all.x = TRUE)
stopifnot(nrow(fail) == before)   # the merge must never change the row count

# --- Recover the events that were logged without a literature_id -------------
# Pre-fix logs recorded the paywall line as URL-only, so ~27% of failure events
# had no id and therefore no title, journal, or publisher. They are not
# unidentifiable: the corpus parquet carries pdf_url per paper, so the logged
# URL identifies the paper directly. The log truncates the URL at 80 characters,
# so match on that prefix rather than the whole string.
if (any(is.na(fail$literature_id)) && file.exists(PARQUET)) {
  options(arrow.skip_nul = TRUE)   # embedded NULs in this parquet
  pqd <- as.data.frame(arrow::read_parquet(
    PARQUET, col_select = c("literature_id", "title", "authors", "year",
                            "journal", "doi", "pdf_url")))
  pqd$literature_id <- sub("\\.0$", "", as.character(pqd$literature_id))
  pqd <- pqd[!is.na(pqd$pdf_url) & nzchar(pqd$pdf_url), ]
  pqd$key <- substr(pqd$pdf_url, 1, 80)
  pqd <- pqd[!duplicated(pqd$key), ]

  need <- is.na(fail$literature_id)
  idx <- match(substr(fail$detail[need], 1, 80), pqd$key)
  rec <- !is.na(idx)
  fail$literature_id[need][rec]  <- pqd$literature_id[idx[rec]]
  fail$title[need][rec]          <- pqd$title[idx[rec]]
  fail$authors[need][rec]        <- pqd$authors[idx[rec]]
  fail$year[need][rec]           <- pqd$year[idx[rec]]
  fail$journal_clean[need][rec]  <- pqd$journal[idx[rec]]
  fail$doi[need][rec]            <- pqd$doi[idx[rec]]
  message(sprintf("recovered %s of %s id-less events by matching the logged URL against parquet pdf_url",
                  format(sum(rec), big.mark = ","),
                  format(sum(need), big.mark = ",")))
}

# Record join coverage rather than letting failed joins pass as blank cells.
# Two separate causes, and they need different responses:
#   no id in the log      -> a worker logging gap (fixed 2026-09-03 forward)
#   id present, no match  -> new papers not yet written to papers_data.json,
#                            which Phase 5 does AFTER Phase 4, so a mid-run
#                            snapshot cannot resolve them. Resolves on re-run.
n_no_id <- sum(is.na(fail$literature_id))
n_unjoined <- sum(!is.na(fail$literature_id) & is.na(fail$title))
message(sprintf("join coverage: %s of %s events carry metadata (%s no id, %s id but no corpus row)",
                format(sum(!is.na(fail$title)), big.mark = ","),
                format(nrow(fail), big.mark = ","),
                format(n_no_id, big.mark = ","),
                format(n_unjoined, big.mark = ",")))

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
dom$pct_of_all <- round(100 * dom$n / nrow(fail), 2)
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
dom$pct_real_of_all <- round(100 * dom$real_failures / nrow(fail), 2)
dom <- dom[order(-dom$real_failures, -dom$n),
           c("domain", "n", "pct_of_all", "deliberate_skips", "real_failures",
             "pct_real_of_all", "with_known_oa", "decision", "proposed_route")]
names(dom)[1] <- "domain"

st <- as.data.frame(table(http_status = fail$http_status), responseName = "n")
st <- st[order(-st$n), ]
st$pct_of_all <- round(100 * st$n / nrow(fail), 1)

by_class$pct_of_all <- round(100 * by_class$n / nrow(fail), 1)

# --- Stratified samples, one tab per dimension -------------------------------
# Sampling grouped by domain only, as the single Sample_for_review tab did,
# hides whichever patterns cut ACROSS domains: every 404 looks like a different
# publisher's problem when it may be one rotted-link problem. So each dimension
# gets its own tab, each stratified on its own categories, and each carries the
# category column first so the grouping is visible rather than implied.
set.seed(20260903)

samp_cols <- c("literature_id", "year", "title", "journal_clean", "publisher",
               "doi", "failure_class", "http_status", "domain", "known_oa_url",
               "actionable", "url")

stratified <- function(df, key, categories, per_cat) {
  out <- do.call(rbind, lapply(categories, function(k) {
    rows <- df[!is.na(df[[key]]) & df[[key]] == k, ]
    if (!nrow(rows)) return(NULL)
    rows[sample(seq_len(nrow(rows)), min(per_cat, nrow(rows))), ]
  }))
  if (is.null(out)) return(NULL)
  cols <- c(key, setdiff(samp_cols[samp_cols %in% names(out)], key))
  out <- out[, cols]
  out$title <- substr(out$title, 1, 150)
  out$url <- substr(out$url, 1, 180)
  out$pattern_noted <- ""
  out$proposed_fix <- ""
  out
}

# Domains: top 25 by REAL failures, 6 each.
samp_domain <- stratified(fail, "domain",
                          head(as.character(dom$domain), 25), 6)
# Statuses and classes are few, so sample more deeply from each.
samp_status <- stratified(fail, "http_status",
                          as.character(st$http_status), 12)
samp_class <- stratified(fail, "failure_class",
                         as.character(by_class$failure_class), 15)

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
  "TABS 4-6: Domain_sample, Status_sample, Class_sample",
  "One sample tab per dimension, each stratified on its OWN categories, with",
  "that category as the first column so the grouping is visible rather than",
  "implied. Sampling only by domain would hide patterns that cut ACROSS",
  "domains: every 404 looks like a different publisher's problem when it may",
  "be one rotted-link problem.",
  sprintf("  Domain_sample: %s rows, 6 per domain, top 25 domains by real failures.",
          if (is.null(samp_domain)) "0" else format(nrow(samp_domain), big.mark = ",")),
  sprintf("  Status_sample: %s rows, up to 12 per HTTP status.",
          if (is.null(samp_status)) "0" else format(nrow(samp_status), big.mark = ",")),
  sprintf("  Class_sample:  %s rows, up to 15 per failure class.",
          if (is.null(samp_class)) "0" else format(nrow(samp_class), big.mark = ",")),
  "  3. Fill 'pattern_noted' and 'proposed_fix' where you spot something.",
  "",
  "PROVENANCE AND KNOWN GAPS",
  "- Failure events come from the sync log, so a failure the worker did not",
  "  log does not appear here. The counts are of EVENTS, and a paper retried",
  "  twice contributes more than one event.",
  sprintf("- Metadata join coverage: %s of %s events (%.0f%%).",
          format(sum(!is.na(fail$title)), big.mark = ","),
          format(nrow(fail), big.mark = ","),
          100 * sum(!is.na(fail$title)) / nrow(fail)),
  sprintf("  %s events carry NO literature_id: logs before 2026-09-03 omitted",
          format(n_no_id, big.mark = ",")),
  "  it on the paywall line, which is ~27% of failures. Fixed going forward.",
  sprintf("  %s have an id but no corpus row: these are new papers, and Phase 5",
          format(n_unjoined, big.mark = ",")),
  "  writes papers_data.json AFTER Phase 4, so a mid-run snapshot cannot",
  "  resolve them. They resolve when this is re-run after the sync completes.",
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

add_tab("By_domain", dom, c(38, 8, 11, 15, 13, 15, 14, 16, 46))
add_tab("By_status", st, c(16, 8, 11))
add_tab("By_class", by_class, c(26, 8, 11))
swid <- function(df) c(26, 12, 6, 52, 26, 20, 24, 20, 11, 26, 40, 16, 50,
                       30, 34)[seq_len(ncol(df))]
if (!is.null(samp_domain)) add_tab("Domain_sample", samp_domain, swid(samp_domain))
if (!is.null(samp_status)) add_tab("Status_sample", samp_status, swid(samp_status))
if (!is.null(samp_class))  add_tab("Class_sample",  samp_class,  swid(samp_class))

worksheetOrder(wb) <- seq_len(length(wb$sheet_names))
out <- sprintf("outputs/download_failures_%s.xlsx", format(Sys.Date(), "%Y-%m-%d"))
saveWorkbook(wb, out, overwrite = TRUE)
source(file.path("scripts", "lib", "repair_xlsx.R"))
repair_xlsx(out)
message(sprintf("wrote %s  (%s failures, %s with a known OA copy)", out,
                format(nrow(fail), big.mark = ","),
                format(n_oa, big.mark = ",")))
if (!finished) message("NOTE: sync still running — these are PARTIAL figures.")
