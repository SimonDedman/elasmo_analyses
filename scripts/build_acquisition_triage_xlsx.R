#!/usr/bin/env Rscript
# Build outputs/acquisition_triage_<date>.xlsx — the manual-review half of the
# acquisition-backlog retriage.
#
# Two jobs the machine should NOT decide on its own:
#   1. Which "conference-shaped" journal strings are genuinely conference
#      abstract series (-> migrate to the conference-abstracts project) and
#      which are peer-reviewed journals that merely have "Proceedings" in the
#      title. Getting this wrong either loses real papers or pollutes the
#      abstracts DB.
#   2. Journal fields that are visibly damaged ("SMITH", "Programme Booklet of
#      The"), which defeat every title-based DOI lookup until repaired.
#
# Usage:  Rscript scripts/build_acquisition_triage_xlsx.R

suppressPackageStartupMessages({
  library(jsonlite)
  library(openxlsx)
})

root <- normalizePath(file.path(dirname(sub("^--file=", "", grep("^--file=",
        commandArgs(trailingOnly = FALSE), value = TRUE)[1])), ".."))
setwd(root)

papers <- fromJSON("docs/papers_data.json", simplifyDataFrame = TRUE)
papers$journal_use <- ifelse(nzchar(trimws(papers$journal_clean)),
                             trimws(papers$journal_clean),
                             trimws(papers$journal))
papers$year_num <- suppressWarnings(as.integer(papers$year))
papers$has_doi <- nzchar(trimws(papers$doi))

message(sprintf("outstanding rows: %s", format(nrow(papers), big.mark = ",")))

# --- 1. Conference-shaped strings ------------------------------------------
conf_pat <- paste0("abstract|programm|program\\b|proceedings|résumés|",
                   "resumenes|resúmenes|congress|symposium|conference|meeting|",
                   "libro de|book of|workshop|booklet|encuentro|colloque|",
                   "jornadas|reunião|reunion")
# Titles that contain "Proceedings"/"Transactions" but are established
# peer-reviewed serials, not abstract books.
journal_pat <- paste0("^(proceedings|transactions|papers and proceedings)\\b.*",
                      "\\b(society|academy|museum|institute|association of|",
                      "national academy|royal society|linnean)\\b")
strong_conf_pat <- paste0("abstract|programm|program\\b|book of|libro de|",
                          "résumés|resúmenes|resumenes|encuentro|colloque|",
                          "booklet|congress|symposium|workshop|jornadas")

is_conf_shaped <- grepl(conf_pat, papers$journal_use, ignore.case = TRUE,
                        perl = TRUE)
conf <- papers[is_conf_shaped, ]

agg <- aggregate(
  cbind(n = rep(1, nrow(conf))) ~ journal_use, data = conf, FUN = sum)
yr <- aggregate(year_num ~ journal_use, data = conf,
                FUN = function(z) c(min(z, na.rm = TRUE), max(z, na.rm = TRUE)))
agg$year_min <- yr$year_num[, 1][match(agg$journal_use, yr$journal_use)]
agg$year_max <- yr$year_num[, 2][match(agg$journal_use, yr$journal_use)]
agg$year_span <- agg$year_max - agg$year_min

agg$suggested_class <- ifelse(
  grepl(strong_conf_pat, agg$journal_use, ignore.case = TRUE, perl = TRUE),
  "CONFERENCE_SERIES",
  ifelse(grepl(journal_pat, agg$journal_use, ignore.case = TRUE, perl = TRUE),
         "PEER_REVIEWED_JOURNAL", "UNCLEAR"))

# Already tracked by the conference-abstracts coverage matrix (5 series).
known_pat <- paste0("european elasmobranch|\\bEEA\\b|shark international|\\bSI\\b|",
                    "american elasmobranch|\\bAES\\b|oceania|\\bOCS\\b|",
                    "ASIH|JMIH|joint meeting of ichthyologists")
# Flag a tracked series regardless of suggested_class: "Proceedings of the
# European Elasmobranch Association" classifies as UNCLEAR on wording alone,
# but it is unambiguously the EEA series the matrix already follows, and
# hiding that would invite a duplicate series being created for it.
agg$in_coverage_matrix <- ifelse(
  grepl(known_pat, agg$journal_use, ignore.case = TRUE, perl = TRUE),
  "yes (tracked)", "NO - candidate to add")
agg$in_coverage_matrix[agg$suggested_class == "PEER_REVIEWED_JOURNAL" &
                       agg$in_coverage_matrix == "NO - candidate to add"] <- ""

agg$decision <- ""            # MIGRATE / KEEP_AS_PAPER / SPLIT / UNSURE
agg$series_name <- ""         # name for the coverage matrix, if migrating
agg$notes <- ""

agg <- agg[order(-agg$n), c("journal_use", "n", "year_min", "year_max",
                            "year_span", "suggested_class",
                            "in_coverage_matrix", "decision", "series_name",
                            "notes")]
names(agg)[1] <- "journal_string"

message(sprintf("conference-shaped strings: %d (%s rows)",
                nrow(agg), format(sum(agg$n), big.mark = ",")))

# --- 2. Damaged journal fields ---------------------------------------------
j <- papers$journal_use

# A bare surname in the journal field ("SMITH", "Fowler") is the signature of a
# scrape that put the author where the journal belongs. Test it by asking
# whether the journal string IS this row's own first-author surname, rather
# than by string length: "Ambio" and "Copeia" are 5- and 6-character real
# journals, and a length rule condemns them alongside "SMITH".
first_surname <- toupper(trimws(sub("[,&(].*$", "", papers$authors)))
journal_is_surname <- nchar(j) > 0 &
  !grepl("\\s", trimws(j)) &
  toupper(trimws(j)) == first_surname

# The journal field holding the paper's own title is the other common damage.
journal_is_title <- nchar(j) > 40 &
  substr(tolower(j), 1, 40) == substr(tolower(trimws(papers$title)), 1, 40)

damaged <- (nchar(j) < 4) |
  journal_is_surname |
  journal_is_title |
  grepl("\\b(of|for|and|the|in|at|on)\\s+(the)?\\s*$", j, ignore.case = TRUE) |
  grepl("\\.\\.\\.$|,\\s*$|^\\W+$", j) |
  grepl("^(unknown|anon|n/?a|none|null)$", j, ignore.case = TRUE)

dmg <- papers[damaged & !is_conf_shaped, ]
dmg_out <- data.frame(
  literature_id = dmg$literature_id,
  year          = dmg$year,
  authors       = substr(dmg$authors, 1, 120),
  title         = substr(dmg$title, 1, 200),
  journal_as_recorded = dmg$journal_use,
  doi           = dmg$doi,
  corrected_journal = "",
  corrected_doi     = "",
  decision      = "",
  notes         = "",
  stringsAsFactors = FALSE
)
dmg_out <- dmg_out[order(dmg_out$journal_as_recorded, -as.integer(dmg_out$year)), ]
message(sprintf("damaged journal fields: %s rows, %d distinct strings",
                format(nrow(dmg_out), big.mark = ","),
                length(unique(dmg_out$journal_as_recorded))))

# --- Info tab ---------------------------------------------------------------
info <- data.frame(c(
  "ACQUISITION BACKLOG — MANUAL TRIAGE",
  sprintf("Generated %s from docs/papers_data.json (%s outstanding papers).",
          format(Sys.time(), "%Y-%m-%d %H:%M %Z"),
          format(nrow(papers), big.mark = ",")),
  "",
  "WHY THIS EXISTS",
  "The acquisition todo list is being re-cut into tracks so the headline",
  "acquisition % stops being dragged down by rows no subscription can ever",
  "reach. Two of those decisions are judgement calls a script must not make",
  "alone, so they are here for you.",
  "",
  "WHAT WAS ALREADY DONE AUTOMATICALLY",
  sprintf("- Classified all %s outstanding rows by DOI presence and publisher.",
          format(nrow(papers), big.mark = ",")),
  "- Flagged every journal string that looks like a conference abstract book.",
  "- Pre-classified those into CONFERENCE_SERIES / PEER_REVIEWED_JOURNAL /",
  "  UNCLEAR, and checked each against the 5 series already tracked in",
  "  outputs/conference_coverage_matrix.xlsx (ASIH/JMIH, AES, EEA, OCS, SI).",
  "- Flagged journal fields that look truncated or corrupted.",
  "- NOTHING has been moved, deleted, or migrated. This sheet is the gate.",
  "",
  "TAB 1: Conference_series",
  sprintf("%d distinct journal strings covering %s outstanding rows.",
          nrow(agg), format(sum(agg$n), big.mark = ",")),
  "The pre-classification is a suggestion and it is wrong in both directions:",
  "'Proceedings of the Biological Society of Washington' is a real journal,",
  "while 'Programme Booklet of The' is a truncated abstract book.",
  "",
  "  1. Read 'suggested_class', then fill 'decision' with one of:",
  "       MIGRATE       - a conference abstract series; move to the",
  "                       conference-abstracts project, out of acquisition.",
  "       KEEP_AS_PAPER - a peer-reviewed journal; leave in the download queue.",
  "       SPLIT         - the string covers both; explain in 'notes'.",
  "       UNSURE        - leave for Carylanne or a second pass.",
  "  2. For every MIGRATE row, put the canonical series name in 'series_name'",
  "     (e.g. 'Encuentro Colombiano sobre Condrictios'). Rows marked",
  "     'NO - candidate to add' in 'in_coverage_matrix' become NEW series in",
  "     the coverage matrix, so the name you give is the one that sticks.",
  "  3. Leave 'decision' blank for anything you want left alone.",
  "",
  "TAB 2: Damaged_journals",
  sprintf("%s rows whose journal field is truncated, blank, or a bare surname.",
          format(nrow(dmg_out), big.mark = ",")),
  "These defeat title-based DOI lookup until repaired, so they block the",
  "DOI-recovery pass that would otherwise make them assignable.",
  "",
  "  4. Fill 'corrected_journal' where you can identify the real journal.",
  "  5. Fill 'corrected_doi' if you happen to know or find it.",
  "  6. Set 'decision' to REPAIRED, DROP (not a paper), or UNSURE.",
  "",
  "WHAT HAPPENS NEXT",
  "Send the file back and the decisions are applied in one pass: MIGRATE rows",
  "leave the acquisition denominator and enter the abstracts coverage matrix;",
  "REPAIRED rows re-enter the DOI-recovery queue.",
  "",
  "PROVENANCE AND KNOWN GAPS",
  "- Source: docs/papers_data.json, the live outstanding-papers list.",
  "- A shark-references sync was running when this was generated, so counts",
  "  will grow once it lands; the decisions here stay valid regardless.",
  "- The conference/journal regex is recall-biased: it over-catches on",
  "  'Proceedings', which is exactly why tab 1 needs a human."
), stringsAsFactors = FALSE)
names(info) <- "Acquisition backlog — manual triage"

# --- Write ------------------------------------------------------------------
wb <- createWorkbook()
hdr <- createStyle(textDecoration = "bold")

addWorksheet(wb, "Info")
writeData(wb, "Info", info)
setColWidths(wb, "Info", 1, 92)
addStyle(wb, "Info", createStyle(textDecoration = "bold", fontSize = 12),
         rows = 1, cols = 1)

addWorksheet(wb, "Conference_series")
writeData(wb, "Conference_series", agg, headerStyle = hdr)
freezePane(wb, "Conference_series", firstRow = TRUE)
addFilter(wb, "Conference_series", rows = 1, cols = seq_len(ncol(agg)))
setColWidths(wb, "Conference_series", seq_len(ncol(agg)),
             c(58, 6, 9, 9, 10, 22, 22, 16, 30, 34))

addWorksheet(wb, "Damaged_journals")
writeData(wb, "Damaged_journals", dmg_out, headerStyle = hdr)
freezePane(wb, "Damaged_journals", firstRow = TRUE)
addFilter(wb, "Damaged_journals", rows = 1, cols = seq_len(ncol(dmg_out)))
setColWidths(wb, "Damaged_journals", seq_len(ncol(dmg_out)),
             c(12, 6, 34, 60, 26, 24, 30, 24, 14, 30))

worksheetOrder(wb) <- c(1, 2, 3)
out <- sprintf("outputs/acquisition_triage_%s.xlsx", format(Sys.Date(), "%Y-%m-%d"))
saveWorkbook(wb, out, overwrite = TRUE)
source(file.path("scripts", "lib", "repair_xlsx.R"))
repair_xlsx(out)
message(sprintf("wrote %s", out))
