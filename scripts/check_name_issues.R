#!/usr/bin/env Rscript
# ============================================================================
# Author-name quality scanner + rule-based corrector with confidence scores.
#
# Rules (ordered; later rules see the output of earlier ones):
#
#   R0  Strip literal "undefined" prefix and trailing whitespace.
#   R1  Strip leading punctuation (-, ., ,) from either field.
#   R2  Surname-first comma reorder: "LAST, First" → "First Last".
#   R3  Split compact "X.SURNAME" tokens into "X." + "SURNAME" so later
#       rules can dedupe the surname from the first-name list.
#   R4  Title-case all-caps tokens (≥3 letters AND ≥1 vowel). Tokens
#       with 0 vowels stay (likely initials: LJV, RRMKP, SFJ).
#   R5  Capitalise the letter immediately after any hyphen variant
#       (ASCII + Unicode hyphens). Rest of token stays as is.
#   R6  Strip any first/middle token whose normalised form matches the
#       surname (accent-folded, punct-stripped, hyphen-tolerant).
#   R7  Collapse adjacent duplicate tokens in first name.
#   R8  Flag: single-letter surname (might be lost data).
#   R9  Flag: Unicode replacement character. Dictionary lookup suggests
#       the likely correction where possible (José, König, Rodríguez …).
#
# Rows with the user note "fixed" (or starting with it) are dropped from
# the review list — the user has already reconciled the XLSX manually.
# ============================================================================

suppressPackageStartupMessages({
  library(tidyverse)
  library(openxlsx)
})

setwd("/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel")

authors <- read_csv("outputs/openalex_unique_authors.csv", show_col_types = FALSE) |>
  mutate(openalex_author_id = str_remove(openalex_author_id, "https://openalex.org/"))

# --- Author exclusions ----------------------------------------------------
# Bogus authors get written to outputs/author_excluded.csv and skipped from
# the issues XLSX and the build pipeline.
#   * collective-article   : OpenAlex editorials labelled as one author
#   * multi-author-entry   : first_name contains a comma-separated author list
#                            (3+ commas → almost always multiple people
#                            stuffed into a single record)
#   * mojibake             : first_name has the tell-tale "Ð"/"Ñ" byte pairs
#                            from UTF-8 mis-decoded as Latin-1 — unrecoverable
#                            without the source document
count_char <- function(s, ch) {
  if (is.na(s)) return(0L)
  lengths(regmatches(s, gregexpr(ch, s, fixed = TRUE)))
}

is_multi_author <- function(first) {
  if (is.na(first)) return(FALSE)
  n_comma <- count_char(first, ",")
  has_and <- grepl("\\band\\b", first)
  # Split on either a comma or the word "and"; count distinct name-chunks
  n_chunks <- length(strsplit(first, "(,|\\band\\b)", perl = TRUE)[[1]])
  (n_comma >= 3) ||
    (has_and && n_comma >= 1) ||
    (n_chunks >= 3)
}
is_mojibake <- function(s) {
  if (is.na(s)) return(FALSE)
  # Latin-1-interpreted UTF-8 Cyrillic produces long runs of Ð/Ñ/Ò/Ó chars.
  count_char(s, "\u00D0") + count_char(s, "\u00D1") >= 3
}

excluded <- authors |>
  mutate(
    reason = case_when(
      grepl("^COLLECTIVE ARTICLE", display_name) |
      grepl("^Collective Article", display_name) ~ "collective-article",
      vapply(first_name, is_multi_author, logical(1)) ~ "multi-author-entry",
      vapply(first_name, is_mojibake, logical(1))    ~ "mojibake",
      vapply(last_name,  is_mojibake, logical(1))    ~ "mojibake",
      TRUE ~ NA_character_
    )
  ) |>
  filter(!is.na(reason)) |>
  transmute(openalex_author_id, display_name, reason)

write_csv(excluded, "outputs/author_excluded.csv")
cat(sprintf("Excluded %d bogus authors:\n", nrow(excluded)))
print(table(excluded$reason))
authors <- authors |> filter(!openalex_author_id %in% excluded$openalex_author_id)

# Clean stale corrections for authors now in the excluded list (prevents
# bogus multi-author entries from showing as corrections like
# "P Ramu Sridhar And S Chandrasekaran R | Ramesh").
corr_path <- "outputs/author_name_corrections.csv"
if (file.exists(corr_path) && nrow(excluded) > 0) {
  cc <- read_csv(corr_path, show_col_types = FALSE)
  stale <- cc |> filter(openalex_author_id %in% excluded$openalex_author_id)
  if (nrow(stale) > 0) {
    cc <- cc |> filter(!openalex_author_id %in% excluded$openalex_author_id)
    write_csv(cc, corr_path)
    cat(sprintf("  Removed %d stale corrections for excluded authors\n", nrow(stale)))
  }
}

# Skip rows where first OR last name is NA or empty — these can't be corrected
# via rules and just clutter the review XLSX as "NA ESA"-style garbage.
authors_with_na <- authors |> filter(is.na(first_name) | is.na(last_name) |
                                     !nzchar(trimws(first_name)) |
                                     !nzchar(trimws(last_name)))
cat(sprintf("  %d rows with missing first/last name — not reviewable via rules, skipping\n",
            nrow(authors_with_na)))
authors <- authors |> filter(!is.na(first_name), !is.na(last_name),
                             nzchar(trimws(first_name)), nzchar(trimws(last_name)))

# Skip rows already resolved in author_name_corrections.csv so we don't
# re-flag them every run against the un-fixed source data.
already_fixed <- tibble(openalex_author_id = character())
if (file.exists("outputs/author_name_corrections.csv")) {
  already_fixed <- read_csv("outputs/author_name_corrections.csv",
                            show_col_types = FALSE) |>
    select(openalex_author_id)
}
cat(sprintf("  %d rows already in corrections — skipping\n", nrow(already_fixed)))
authors <- authors |> filter(!openalex_author_id %in% already_fixed$openalex_author_id)

# Preserve user edits from the prior XLSX: notes AND any manual overrides
# in suggested_first_name / suggested_last_name cells.
existing <- tibble(openalex_author_id = character(),
                   notes = character(),
                   prev_suggested_first = character(),
                   prev_suggested_last  = character())
if (file.exists("outputs/author_name_issues.xlsx")) {
  prev <- read.xlsx("outputs/author_name_issues.xlsx")
  need_cols <- c("openalex_author_id", "notes",
                 "suggested_first_name", "suggested_last_name")
  if (all(need_cols %in% colnames(prev))) {
    existing <- prev |>
      select(openalex_author_id,
             notes,
             prev_suggested_first = suggested_first_name,
             prev_suggested_last  = suggested_last_name) |>
      mutate(notes = ifelse(is.na(notes), "", notes))
  }
}

# User confirmation keywords in notes: fixed / newfixed / edited / apply.
# DO NOT drop these rows — they must stay visible so the user can audit
# which fixes they have made, and their values must flow through to the
# upstream corrections CSV. The migration script picks them up.
FIXED_KEYWORDS <- "\\b(fix|fixed|newfix|newfixed|edit|edited|apply|accept|accepted|confirm|confirmed)\\b"
# Strip subagent prefix annotations before scanning for lock keywords —
# otherwise words like "confirmed" inside a subagent's prose spuriously
# lock the row.
strip_subagent <- function(s) gsub("\\[subagent-[a-z]+\\][^|]*", "", s %||% "")
fixed_ids <- existing |>
  filter(grepl(FIXED_KEYWORDS, strip_subagent(notes), ignore.case = TRUE)) |>
  pull(openalex_author_id)
cat(sprintf("User-confirmed rows (kept in XLSX): %d\n", length(fixed_ids)))

# Unicode replacement dictionary. `\uFFFD` is the standard replacement char
# that appears when the original encoded byte couldn't be decoded as valid
# UTF-8. Multiple appearances in one token (e.g. Th\uFFFDr\uFFFDse) each
# stand for one lost character.
#
# Matching is literal substring (fixed=TRUE). For single-byte \uFFFD the
# pattern must include one replacement char per missing char. Spread
# across languages: Spanish/Portuguese/French/Italian/German/Nordic/
# Turkish/Catalan — country column used as tie-break when ambiguous.
UNICODE_DICT <- list(
  # Spanish / Portuguese / Catalan
  "Rodr\uFFFDguez"  = "Rodríguez",   "Gonz\uFFFDlez"   = "González",
  "L\uFFFDpez"      = "López",        "Mart\uFFFDnez"   = "Martínez",
  "P\uFFFDrez"      = "Pérez",        "Gim\uFFFDnez"    = "Giménez",
  "Hern\uFFFDndez"  = "Hernández",    "Fern\uFFFDndez"  = "Fernández",
  "Jim\uFFFDnez"    = "Jiménez",      "Ram\uFFFDrez"    = "Ramírez",
  "Mu\uFFFDoz"      = "Muñoz",        "Pe\uFFFDa"       = "Peña",
  "Garc\uFFFDa"     = "García",       "C\uFFFDrdenas"   = "Cárdenas",
  "Jos\uFFFD"       = "José",         "Ord\uFFFD\uFFFDez" = "Ordóñez",
  "S\uFFFDnchez"    = "Sánchez",      "Ram\uFFFDn"      = "Ramón",
  "Anad\uFFFDn"     = "Anadón",       "M\uFFFDndez"     = "Méndez",
  "Gij\uFFFDn"      = "Gijón",        "G\uFFFDmez"      = "Gómez",
  "Merc\uFFFD"      = "Mercè",        "Soler-Gij\uFFFDn" = "Soler-Gijón",

  # Portuguese
  "Sim\uFFFDes"     = "Simões",       "Jo\uFFFDo"       = "João",
  "Ant\uFFFDnio"    = "António",      "Guerra\uFFFD"    = "Guerrão",
  "Concei\uFFFD\uFFFDo" = "Conceição", "Sa\uFFFDo"       = "São",

  # French
  "Gis\uFFFDle"     = "Gisèle",       "Th\uFFFDr\uFFFDse" = "Thérèse",
  "J\uFFFDgou"      = "Jégou",        "Fran\uFFFDois"   = "François",
  "Herv\uFFFD"      = "Hervé",        "Genevi\uFFFDve"  = "Geneviève",
  "Aim\uFFFD"       = "Aimé",         "Isra\uFFFDl"     = "Israël",
  "Andr\uFFFD"      = "André",        "C\uFFFDdric"     = "Cédric",

  # German
  "J\uFFFDrgen"     = "Jürgen",       "G\uFFFDgelein"   = "Gägelein",
  "R\uFFFDdeberg"   = "Rödeberg",     "K\uFFFDnig"      = "König",
  "M\uFFFDller"     = "Müller",       "Schr\uFFFDder"   = "Schröder",
  "B\uFFFDhmer"     = "Böhmer",       "Gr\uFFFDnewald"  = "Grünewald",

  # Italian
  "Niccol\uFFFD"    = "Niccolò",      "Nicol\uFFFD"     = "Nicolò",

  # Nordic (Swedish, Norwegian, Danish, Finnish, Icelandic)
  "Bj\uFFFDrn"      = "Björn",        "Bj\uFFFDrklund"  = "Björklund",
  "J\uFFFDnsson"    = "Jönsson",      "J\uFFFDrgensen"  = "Jørgensen",
  "M\uFFFDrup"      = "Mørup",        "F\uFFFDnge"      = "Fänge",
  "M\uFFFDkel\uFFFD" = "Mäkelä",      "M\uFFFDkel"      = "Mäkel",
  "L\uFFFDfgren"    = "Löfgren",
  "F\uFFFDgares"    = "Fogares",
  "S\uFFFDren"      = "Søren",        "\uFFFDrsted"     = "Ørsted",
  "\uFFFDke"        = "Åke",          "P\uFFFDter"      = "Pöter",

  # Turkish
  "Karam\uFFFDrsel" = "Karamürsel",   "\uFFFDzg\uFFFDr"  = "Özgür",
  "\uFFFDelik"      = "Çelik",        "Da\uFFFDli"      = "Dağlı",
  "Dem\uFFFDr"      = "Demir",

  # Heuristic fallbacks for surnames that lost a vowel (no replacement
  # char but ASCII-stripped form is distinctive — rare but seen in data)
  "Bjrklund"        = "Björklund"
)

PARTICLES <- c("da","das","de","del","della","di","do","dos","du",
               "la","le","el","al","van","von","der","den","ter","ten",
               "bin","ibn","mac","mc","st","st.",
               "abu","ibn","bin","binti","ben")

is_particle <- function(tok) {
  if (is.na(tok) || !nzchar(tok)) return(FALSE)
  tolower(gsub("[.,]", "", tok)) %in% PARTICLES
}

# --- Helpers --------------------------------------------------------------

# Fold accents for comparison purposes (not for display).
strip_accents <- function(s) {
  if (is.na(s)) return(NA_character_)
  iconv(s, from = "UTF-8", to = "ASCII//TRANSLIT")
}

# Normalise a token for surname comparison: lowercase, no accents, no punct,
# no whitespace. "San-Martín" → "sanmartin".
norm_for_match <- function(s) {
  if (is.na(s) || !nzchar(s)) return("")
  s <- strip_accents(s)
  s <- tolower(s)
  gsub("[^a-z0-9]", "", s)
}

vowel_count <- function(letters) {
  nchar(gsub("[^AEIOUaeiou]", "", letters))
}

# R4: title-case one token if it looks like a shouted name (all caps, has vowels).
# Preserves vowel-sparse blocks (likely initials) and short init tokens with dots.
title_tok <- function(tok) {
  if (is.na(tok) || !nzchar(tok)) return(tok)
  letters_only <- gsub("[^A-Za-zÀ-ÿ]", "", tok)
  n <- nchar(letters_only)
  if (n <= 1) return(tok)
  # NEW: fully lowercase tokens should be title-cased ("mercy" → "Mercy").
  # Mixed case (e.g. "McDonald") left alone.
  is_all_upper <- letters_only == toupper(letters_only) && nzchar(letters_only)
  is_all_lower <- letters_only == tolower(letters_only) && nzchar(letters_only)
  if (!is_all_upper && !is_all_lower) return(tok)  # mixed case kept
  if (is_all_upper) {
    if (n == 2) return(tok)                         # "AB", "BJ" initials kept
    if (grepl("\\.", tok) && n <= 4) return(tok)
    if (!(tolower(letters_only) %in% PARTICLES)) {
      vc <- vowel_count(letters_only)
      if (n <= 4 && vc < 2) return(tok)            # short vowel-sparse = initials
      if (vc == 0) return(tok)
    }
  }
  # is_all_lower or is_all_upper-but-needs-title-case → fall through and
  # title-case.
  chars <- strsplit(tok, "", fixed = TRUE)[[1]]
  out <- character(length(chars))
  seen_letter <- FALSE
  for (i in seq_along(chars)) {
    ch <- chars[i]
    if (grepl("[A-Za-zÀ-ÿ]", ch)) {
      if (!seen_letter) { out[i] <- toupper(ch); seen_letter <- TRUE }
      else              { out[i] <- tolower(ch) }
    } else { out[i] <- ch }
  }
  paste(out, collapse = "")
}

# R10: mid-token case fix. After the first letter, any uppercase character
# (including Unicode: Ğ, İ, Č, Ć, Ñ, …) becomes its lowercase equivalent,
# UNLESS it immediately follows a hyphen or apostrophe. Catches patterns like:
#   "DaĞli"        → "Dağli"
#   "Demİr"        → "Demir"
#   "DragiČeviĆ"  → "Dragičević"
#   "McDONALD"     → "McDonald"  (already handled by R4 all-caps path; this is defensive)
is_upper_char <- function(ch) {
  # Character is upper if lowercasing it produces a different character.
  # This is Unicode-aware via R's locale.
  ch != tolower(ch)
}

is_lower_char <- function(ch) ch != toupper(ch)

# R11: Initials-block recovery. "M.a.s." → "M.A.S." when a token is a string
# of letter-plus-dot pairs of any casing. Fixes values where a prior buggy
# run lowercased legitimate initials.
fix_initials_block <- function(tok) {
  if (is.na(tok) || !nzchar(tok)) return(tok)
  if (grepl("^([A-Za-zÀ-ÿ]\\.){2,}$", tok)) return(toupper(tok))
  tok
}

# Lowercase any uppercase letter at position 2+ UNLESS:
#   - the previous character is a separator (. - ' ‐ ‑ ‒ – —)
#   - the entire token looks like an initials block (all-upper letters,
#     ≤4 chars, possibly with dots). Protects "BA", "LJV", "M.A.S." etc.
# Catches: ĆEtković → Ćetković, DaĞli → Dağli, Demİr → Demir, DragiČeviĆ → Dragičević.
normalise_midtoken_case <- function(tok) {
  if (is.na(tok) || nchar(tok) <= 1) return(tok)
  letters_only <- gsub("[^A-Za-zÀ-ÿ]", "", tok)
  # Short all-upper token = initials block; leave it alone.
  if (nchar(letters_only) <= 4 &&
      nzchar(letters_only) &&
      letters_only == toupper(letters_only)) return(tok)
  chars <- strsplit(tok, "", fixed = TRUE)[[1]]
  out <- character(length(chars))
  out[1] <- chars[1]
  sep_pat <- "[-'.\u2010\u2011\u2012\u2013\u2014]"
  for (i in 2:length(chars)) {
    ch   <- chars[i]
    prev <- chars[i - 1]
    if (is_upper_char(ch) && !grepl(sep_pat, prev)) {
      out[i] <- tolower(ch)
    } else {
      out[i] <- ch
    }
  }
  paste(out, collapse = "")
}

# R5: capitalise the letter immediately after any hyphen variant.
capitalise_hyphens <- function(s) {
  if (is.na(s) || !nzchar(s)) return(s)
  pat <- "([\\-\u2010\u2011\u2012\u2013\u2014])([a-z\u00e0-\u00ff])"
  result <- s
  repeat {
    m <- regexpr(pat, result, perl = TRUE)
    if (m == -1) break
    start <- as.integer(m)
    len   <- attr(m, "match.length")
    hy <- substr(result, start, start)
    ltr <- substr(result, start + 1, start + 1)
    result <- paste0(
      substr(result, 1, start - 1),
      hy, toupper(ltr),
      substr(result, start + len, nchar(result))
    )
  }
  result
}

# R3: split "X.SURNAME" compound tokens like "A.GOPALAKRISHNAN" into "A." + "SURNAME"
split_compound_initials <- function(tokens) {
  out <- character(0)
  for (tok in tokens) {
    # Pattern: single uppercase letter + dot + uppercase word of ≥3 letters
    m <- regexpr("^([A-Z]\\.)([A-Z][A-Z]{2,})(.*)$", tok, perl = TRUE)
    if (m != -1) {
      matched <- regmatches(tok, m)
      initial_part <- sub("^([A-Z]\\.)([A-Z][A-Z]{2,})(.*)$", "\\1", matched, perl = TRUE)
      surname_part <- sub("^([A-Z]\\.)([A-Z][A-Z]{2,})(.*)$", "\\2", matched, perl = TRUE)
      tail         <- sub("^([A-Z]\\.)([A-Z][A-Z]{2,})(.*)$", "\\3", matched, perl = TRUE)
      out <- c(out, initial_part, surname_part)
      if (nchar(tail) > 0) out <- c(out, tail)
    } else {
      out <- c(out, tok)
    }
  }
  out
}

# Apply the full rule-pipeline to (first, last). Returns list: new_first,
# new_last, confidence, rules applied, flags.
apply_rules <- function(first, last, issue_type) {
  rules <- character(0)
  confidence <- "HIGH"
  flags <- character(0)

  first <- if (is.na(first)) "" else trimws(first)
  last  <- if (is.na(last))  "" else trimws(last)

  # R0: strip "undefined" prefix
  if (grepl("^undefined\\b", first, ignore.case = TRUE)) {
    first <- trimws(sub("^undefined\\s*", "", first, ignore.case = TRUE))
    rules <- c(rules, "R0-strip-undefined")
  }
  if (grepl("^undefined\\b", last, ignore.case = TRUE)) {
    last  <- trimws(sub("^undefined\\s*", "", last, ignore.case = TRUE))
    rules <- c(rules, "R0-strip-undefined")
  }

  # R15: strip honorific titles (Dr., Prof., Mr., Mrs., Ms., PhD, MD)
  # at either end of first_name. "Walther Baumann, Dr." → "Walther Baumann".
  honorific_pat <- "(^|[,;\\s])(Dr\\.?|Prof\\.?|Mr\\.?|Mrs\\.?|Ms\\.?|PhD|Ph\\.D\\.?|MD|M\\.D\\.?)(\\s|$|,|;|\\.)"
  if (grepl(honorific_pat, first, ignore.case = TRUE, perl = TRUE)) {
    first <- trimws(gsub(honorific_pat, " ", first, ignore.case = TRUE, perl = TRUE))
    first <- trimws(gsub(",\\s*$|^,\\s*|\\s*,\\s*,", "", first, perl = TRUE))
    rules <- c(rules, "R15-strip-honorific")
  }

  # R16: strip trailing parenthetical identifiers like "(699617)"
  if (grepl("\\s*\\(\\d+\\)\\s*$", first)) {
    first <- trimws(sub("\\s*\\(\\d+\\)\\s*$", "", first))
    rules <- c(rules, "R16-strip-paren-id")
  }

  # R17: strip year-range prefix/suffix like ", 1858-1947." or "(1858-1947)"
  if (grepl("[,;\\s\\(]\\s*\\d{4}\\s*[-–—]\\s*\\d{4}\\s*[.\\)]?", first, perl = TRUE)) {
    first <- trimws(sub("[,;\\s\\(]\\s*\\d{4}\\s*[-–—]\\s*\\d{4}\\s*[.\\)]?", "", first, perl = TRUE))
    first <- trimws(gsub("\\s+", " ", first))
    first <- trimws(gsub("[,;]\\s*$", "", first))
    rules <- c(rules, "R17-strip-year-range")
  }

  # R1: leading punctuation
  if (grepl("^[[:punct:]]", first)) {
    first <- trimws(sub("^[[:punct:]]+\\s*", "", first))
    rules <- c(rules, "R1-strip-leading-punct")
  }
  if (grepl("^[[:punct:]]", last)) {
    last <- trimws(sub("^[[:punct:]]+\\s*", "", last))
    rules <- c(rules, "R1-strip-leading-punct")
  }

  # R2: surname-first comma reorder. Only applies when there is a comma.
  #   "LAST, First Middle" → "First Middle Last"
  if (grepl(",", first) || grepl(",", last)) {
    combined <- trimws(paste(first, last))
    if (grepl(",", combined)) {
      parts <- strsplit(combined, ",", fixed = TRUE)[[1]]
      if (length(parts) == 2) {
        new_combined <- paste(trimws(parts[2]), trimws(parts[1]))
        toks <- strsplit(new_combined, "\\s+")[[1]]
        if (length(toks) >= 2) {
          first <- paste(toks[seq_len(length(toks) - 1)], collapse = " ")
          last  <- toks[length(toks)]
        }
      }
      rules <- c(rules, "R2-comma-reorder")
      confidence <- min_conf(confidence, "LOW")
    }
  }

  # Tokenise
  first_tokens <- if (nchar(first) > 0) strsplit(first, "\\s+")[[1]] else character(0)
  last_tokens  <- if (nchar(last)  > 0) strsplit(last,  "\\s+")[[1]] else character(0)

  # R3: split "A.SURNAME" compounds in first-name tokens
  split_result <- split_compound_initials(first_tokens)
  if (!identical(split_result, first_tokens)) {
    first_tokens <- split_result
    rules <- c(rules, "R3-split-compound")
  }

  # R4: title-case all-caps tokens
  new_first <- vapply(first_tokens, title_tok, character(1))
  new_last  <- vapply(last_tokens,  title_tok, character(1))
  if (!identical(new_first, first_tokens)) rules <- c(rules, "R4-titlecase-first")
  if (!identical(new_last,  last_tokens))  rules <- c(rules, "R4-titlecase-last")
  first_tokens <- new_first
  last_tokens  <- new_last

  # R10: normalise mid-token case (Unicode-aware). Runs BEFORE hyphen-cap
  # so any lowercase letter freed by R10 gets re-upped if it's after a hyphen.
  pre_first <- first_tokens; pre_last <- last_tokens
  first_tokens <- vapply(first_tokens, normalise_midtoken_case, character(1))
  last_tokens  <- vapply(last_tokens,  normalise_midtoken_case, character(1))
  if (!identical(first_tokens, pre_first) || !identical(last_tokens, pre_last)) {
    rules <- c(rules, "R10-midtoken-case")
  }

  # R5: hyphen capitalisation
  hyphen_pre <- any(grepl("[\\-\u2010\u2011\u2012\u2013\u2014][a-z\u00e0-\u00ff]",
                          c(first_tokens, last_tokens), perl = TRUE))
  first_tokens <- vapply(first_tokens, capitalise_hyphens, character(1))
  last_tokens  <- vapply(last_tokens,  capitalise_hyphens, character(1))
  if (hyphen_pre) rules <- c(rules, "R5-hyphen-cap")

  # R6: surname duplicated as middle — strip (accent/punct/hyphen tolerant).
  # Strips tokens matching the FULL surname or any single surname-token,
  # including 2-char tokens like "BA" when the surname is "Bâ".
  if (length(first_tokens) > 0 && length(last_tokens) > 0) {
    surname_norm <- norm_for_match(paste(last_tokens, collapse = ""))
    last_any <- vapply(last_tokens, norm_for_match, character(1))
    keep <- vapply(first_tokens, function(tok) {
      norm <- norm_for_match(tok)
      if (nchar(norm) == 0) return(TRUE)
      norm != surname_norm && !(norm %in% last_any)
    }, logical(1))
    if (any(!keep)) {
      first_tokens <- first_tokens[keep]
      rules <- c(rules, "R6-strip-dup-surname")
      confidence <- min_conf(confidence, "MED")
    }
  }

  # R7: collapse adjacent duplicates in first_tokens
  if (length(first_tokens) >= 2) {
    norm_seq <- vapply(first_tokens, norm_for_match, character(1))
    keep <- c(TRUE, norm_seq[-1] != norm_seq[-length(norm_seq)])
    if (any(!keep)) {
      first_tokens <- first_tokens[keep]
      rules <- c(rules, "R7-dedup-adjacent")
      confidence <- min_conf(confidence, "MED")
    }
  }

  # R13: Single-letter-surname reorder. Pattern-aware:
  #   "M. S. A. Khan" / "."   → initials-then-surname  → last = "Khan"
  #   "Simmons John E." / "." → surname-then-given      → last = "Simmons"
  #   neither                → keep current ordering (flag single-letter)
  is_initial_tok <- function(t) {
    grepl("^[A-Za-zÀ-ÿ]{1,2}\\.?$", t, perl = TRUE)
  }
  last_letters <- gsub("[^A-Za-zÀ-ÿ]", "",
                       paste(last_tokens, collapse = ""))
  if (nchar(last_letters) <= 1 && length(first_tokens) >= 2) {
    init_flags <- vapply(first_tokens, is_initial_tok, logical(1))
    # initials-then-surname: first token(s) are initials, and a later
    # non-initials token exists → that token is the surname
    if (init_flags[1] && any(!init_flags)) {
      split_at <- which(!init_flags)[length(which(!init_flags))]  # last non-init
      new_last  <- first_tokens[split_at]
      new_first <- first_tokens[-split_at]
      if (nchar(last_letters) > 0) new_first <- c(new_first, last_tokens)
      first_tokens <- new_first
      last_tokens  <- new_last
      rules <- c(rules, "R13-reorder-initials-then-surname")
      confidence <- min_conf(confidence, "MED")
    } else if (init_flags[length(init_flags)] && !init_flags[1]) {
      # surname-then-given (Simmons John E.): surname = first token
      new_last  <- first_tokens[1]
      new_first <- c(first_tokens[-1], last_tokens)
      first_tokens <- new_first
      last_tokens  <- new_last
      rules <- c(rules, "R13-reorder-surname-first")
      confidence <- min_conf(confidence, "MED")
    }
    # Else: ambiguous — leave order alone, R8 will flag single-letter-surname
  }

  # R12: particle migration. Scan first_tokens LEFT-TO-RIGHT; the first
  # particle (da / de / du / van / von / la / el / …) and EVERYTHING
  # AFTER IT belong to the surname. Catches:
  #   "Vanessa Paes Da | Cruz"                      → "Vanessa Paes | Da Cruz"
  #   "M.J. Biscoglio De Jimenez | Bonino"          → "M.J. Biscoglio | De Jimenez Bonino"
  #   "Jean de la | Fontaine"                       → "Jean | de la Fontaine"
  if (length(first_tokens) > 0) {
    part_idx <- which(vapply(first_tokens, is_particle, logical(1)))
    if (length(part_idx) > 0) {
      split_at <- part_idx[1]
      moved <- first_tokens[split_at:length(first_tokens)]
      # Title-case all migrated tokens (title_tok skips 2-char all-caps like
      # "DA", so handle those explicitly here).
      moved <- vapply(moved, function(t) {
        if (nchar(t) == 0) return(t)
        paste0(toupper(substr(t, 1, 1)),
               tolower(substr(t, 2, nchar(t))))
      }, character(1))
      first_tokens <- first_tokens[seq_len(split_at - 1)]
      last_tokens  <- c(moved, last_tokens)
      rules <- c(rules, "R12-migrate-particle")
      confidence <- min_conf(confidence, "MED")
    }
  }

  # R8: flag single-letter surname
  if (length(last_tokens) >= 1) {
    last_letters <- gsub("[^A-Za-zÀ-ÿ]", "", paste(last_tokens, collapse = ""))
    if (nchar(last_letters) <= 1) {
      flags <- c(flags, "single-letter-surname")
      confidence <- min_conf(confidence, "LOW")
    }
  }

  # R9: Unicode replacement → dictionary suggestion
  combined_for_unicode <- paste(first_tokens, collapse = " ") |>
    paste(paste(last_tokens, collapse = " "))
  if (grepl("\uFFFD", combined_for_unicode, fixed = TRUE)) {
    flags <- c(flags, "unicode-replacement")
    confidence <- min_conf(confidence, "LOW")
    for (key in names(UNICODE_DICT)) {
      if (grepl(key, paste(first_tokens, collapse = " "), fixed = TRUE)) {
        first_tokens <- sapply(first_tokens, function(t)
          gsub(key, UNICODE_DICT[[key]], t, fixed = TRUE))
        rules <- c(rules, "R9-unicode-dict")
      }
      if (grepl(key, paste(last_tokens, collapse = " "), fixed = TRUE)) {
        last_tokens <- sapply(last_tokens, function(t)
          gsub(key, UNICODE_DICT[[key]], t, fixed = TRUE))
        rules <- c(rules, "R9-unicode-dict")
      }
    }
    # Special: "X.YYYY" where YYYY has a replacement char AND starts with an
    # uppercase letter with no intervening lowercase — probably "X. Yyyy"
    # pattern. Flag but do not auto-correct.
  }

  list(
    new_first  = paste(first_tokens, collapse = " "),
    new_last   = paste(last_tokens,  collapse = " "),
    confidence = confidence,
    rules      = paste(rules, collapse = ","),
    flags      = paste(flags, collapse = ",")
  )
}

min_conf <- function(a, b) {
  order <- c(HIGH = 3, MED = 2, LOW = 1)
  if (order[b] < order[a]) b else a
}

# --- Detect issues --------------------------------------------------------
has_replacement   <- function(s) grepl("\uFFFD", s %||% "", fixed = TRUE)
has_digit         <- function(s) grepl("[0-9]", s %||% "")
has_leading_punct <- function(s) grepl("^[[:punct:]]", s %||% "")
has_comma         <- function(s) grepl(",", s %||% "")
has_undefined     <- function(s) grepl("^undefined\\b", s %||% "", ignore.case = TRUE)

has_hyphen_lc <- function(s) {
  if (is.na(s)) return(FALSE)
  grepl("[\\-\u2010\u2011\u2012\u2013\u2014][a-z\u00e0-\u00ff]", s, perl = TRUE)
}

has_allcaps_long <- function(s) {
  if (is.na(s)) return(FALSE)
  parts <- strsplit(s, "\\s+")[[1]]
  any(vapply(parts, function(tok) {
    lo <- gsub("[^A-Za-zÀ-ÿ]", "", tok)
    if (nchar(lo) < 3) return(FALSE)
    if (lo != toupper(lo)) return(FALSE)
    vowel_count(lo) >= 1
  }, logical(1)))
}

has_surname_in_middle <- function(first, last) {
  if (is.na(first) || is.na(last) || !nchar(first) || !nchar(last)) return(FALSE)
  ss <- norm_for_match(last)
  first_toks <- strsplit(first, "\\s+")[[1]]
  any(vapply(first_toks, function(t) norm_for_match(t) == ss && nchar(ss) > 0,
             logical(1)))
}

has_single_letter_surname <- function(last) {
  if (is.na(last) || !nzchar(last)) return(FALSE)
  letters <- gsub("[^A-Za-zÀ-ÿ]", "", last)
  nchar(letters) <= 1
}

flagged <- authors |>
  mutate(
    full_name     = paste(first_name, last_name),
    fn_rep        = vapply(first_name, has_replacement,        logical(1)),
    ln_rep        = vapply(last_name,  has_replacement,        logical(1)),
    fn_caps       = vapply(first_name, has_allcaps_long,       logical(1)),
    ln_caps       = vapply(last_name,  has_allcaps_long,       logical(1)),
    hy_fn         = vapply(first_name, has_hyphen_lc,          logical(1)),
    hy_ln         = vapply(last_name,  has_hyphen_lc,          logical(1)),
    dup_surname   = mapply(has_surname_in_middle, first_name, last_name),
    comma         = vapply(full_name,  has_comma,              logical(1)),
    digit         = vapply(full_name,  has_digit,              logical(1)),
    leading_punct = vapply(full_name,  has_leading_punct,      logical(1)),
    undef_prefix  = vapply(first_name, has_undefined,          logical(1)) |
                    vapply(last_name,  has_undefined,          logical(1)),
    single_ln     = vapply(last_name,  has_single_letter_surname, logical(1))
  ) |>
  filter(
    fn_rep | ln_rep | fn_caps | ln_caps | hy_fn | hy_ln |
    dup_surname | comma | digit | leading_punct |
    undef_prefix | single_ln |
    # Keep any row the user has touched — even if the ORIGINAL name no
    # longer trips our rules, their corrections must still flow through.
    openalex_author_id %in% fixed_ids |
    openalex_author_id %in% existing$openalex_author_id
  )

cat(sprintf("Flagged: %d authors\n", nrow(flagged)))

# Apply rules
fixed <- flagged |>
  rowwise() |>
  mutate(rule_out = list(apply_rules(first_name, last_name, "auto"))) |>
  ungroup() |>
  mutate(
    rule_first  = vapply(rule_out, `[[`, character(1), "new_first"),
    rule_last   = vapply(rule_out, `[[`, character(1), "new_last"),
    confidence  = vapply(rule_out, `[[`, character(1), "confidence"),
    rules_applied = vapply(rule_out, `[[`, character(1), "rules"),
    extra_flags   = vapply(rule_out, `[[`, character(1), "flags")
  ) |>
  select(-rule_out) |>
  # Preserve user edits from the previous XLSX, BUT chain R10 + hyphen-cap
  # on top of them so partial fixes like "DaĞli" still get cleaned up to
  # "Dağli". If the note says "fixed"/"newfixed", lock the value exactly.
  left_join(existing |> select(openalex_author_id,
                               prev_suggested_first,
                               prev_suggested_last,
                               prev_notes = notes),
            by = "openalex_author_id") |>
  rowwise() |>
  mutate(
    user_edited_first = !is.na(prev_suggested_first) &
                        prev_suggested_first != rule_first &
                        nchar(trimws(prev_suggested_first)) > 0,
    user_edited_last  = !is.na(prev_suggested_last) &
                        prev_suggested_last != rule_last &
                        nchar(trimws(prev_suggested_last)) > 0,
    # Only user notes lock a row — strip any subagent-added annotations
    # like "[subagent-low] Org confirmed but ..." before keyword scan,
    # otherwise the word "confirmed" in the subagent's prose spuriously
    # locks rows the user never touched.
    locked_by_note = grepl(FIXED_KEYWORDS,
                           gsub("\\[subagent-[a-z]+\\][^|]*", "",
                                prev_notes %||% ""),
                           ignore.case = TRUE),
    # Build the suggested values. Chain: start from user's value (if any),
    # then apply R10 + hyphen-cap (so mid-token upper-case like Ğ gets fixed).
    # Exception: when note says "fixed", lock the user's value exactly.
    # Policy:
    #   locked_by_note (fix/fixed/newfix/edited/apply)  → user's edit wins,
    #                                                     verbatim.
    #   no such note                                   → rules win. Any
    #                                                     incomplete user
    #                                                     edit is overwritten
    #                                                     by the freshly-
    #                                                     computed rule output.
    suggested_first_name = ifelse(user_edited_first & locked_by_note,
                                  prev_suggested_first, rule_first),
    suggested_last_name  = ifelse(user_edited_last  & locked_by_note,
                                  prev_suggested_last,  rule_last)
  ) |>
  ungroup() |>
  mutate(
    rules_applied = case_when(
      user_edited_first & user_edited_last ~ paste(rules_applied, "user-edit-both", sep = ","),
      user_edited_first                    ~ paste(rules_applied, "user-edit-first", sep = ","),
      user_edited_last                     ~ paste(rules_applied, "user-edit-last",  sep = ","),
      TRUE                                 ~ rules_applied
    ),
    confidence = ifelse(user_edited_first | user_edited_last, "HIGH", confidence)
  ) |>
  select(-rule_first, -rule_last,
         -prev_suggested_first, -prev_suggested_last, -prev_notes,
         -user_edited_first, -user_edited_last, -locked_by_note)

# Compose the issue_type breakdown — finer than before
fixed <- fixed |>
  rowwise() |>
  mutate(issue_type = paste(c(
    if (fn_rep || ln_rep)         "unicode-replacement",
    if (fn_caps && !ln_caps)      "allcaps-first",
    if (!fn_caps && ln_caps)      "allcaps-last",
    if (fn_caps && ln_caps)       "allcaps-both",
    if (hy_fn || hy_ln)           "hyphen-lowercase",
    if (dup_surname)              "surname-duplicated-in-middle",
    if (comma)                    "surname-first-comma",
    if (digit)                    "digit-in-name",
    if (leading_punct)            "leading-punct",
    if (undef_prefix)             "undefined-prefix",
    if (single_ln)                "single-letter-surname"
  ), collapse = "; ")) |>
  ungroup()

# Restore user notes from prior XLSX
fixed <- fixed |>
  left_join(existing |> select(openalex_author_id, notes),
            by = "openalex_author_id") |>
  mutate(notes = ifelse(is.na(notes), "", notes))

out <- fixed |>
  mutate(openalex_url = sprintf("https://openalex.org/%s", openalex_author_id)) |>
  arrange(last_name, first_name) |>
  select(openalex_author_id, openalex_url, full_name,
         first_name, last_name,
         suggested_first_name, suggested_last_name,
         confidence, rules_applied, extra_flags, issue_type, notes,
         paper_count, most_common_institution, institution_country, gender)

cat("\nConfidence:\n"); print(table(out$confidence))
cat("\nIssue types (top 10):\n")
print(sort(table(out$issue_type), decreasing = TRUE) |> head(10))

# --- XLSX ------------------------------------------------------------------
write_formatted_xlsx <- function(df, path, sheet = "Sheet1") {
  wb <- createWorkbook()
  addWorksheet(wb, sheet)
  # Mark URL column as clickable hyperlink
  if ("openalex_url" %in% colnames(df)) {
    class(df$openalex_url) <- "hyperlink"
  }
  writeData(wb, sheet, df)
  addStyle(wb, sheet, createStyle(textDecoration = "bold"),
           rows = 1, cols = seq_len(ncol(df)), gridExpand = TRUE)
  freezePane(wb, sheet, firstRow = TRUE)
  setColWidths(wb, sheet, cols = seq_len(ncol(df)), widths = "auto")
  addFilter(wb, sheet, row = 1, cols = seq_len(ncol(df)))
  hi  <- createStyle(bgFill = "#d4edda")
  med <- createStyle(bgFill = "#fff3cd")
  lo  <- createStyle(bgFill = "#f8d7da")
  cc <- which(colnames(df) == "confidence")
  conditionalFormatting(wb, sheet, cols = cc, rows = 2:(nrow(df)+1),
                        type = "contains", rule = "HIGH", style = hi)
  conditionalFormatting(wb, sheet, cols = cc, rows = 2:(nrow(df)+1),
                        type = "contains", rule = "MED",  style = med)
  conditionalFormatting(wb, sheet, cols = cc, rows = 2:(nrow(df)+1),
                        type = "contains", rule = "LOW",  style = lo)
  saveWorkbook(wb, path, overwrite = TRUE)
  cat(sprintf("Wrote %s\n", path))
}

# --- Category-done: push an entire issue_type to corrections + drop it -----
# When a category is listed here, every row with that EXACT issue_type gets
# appended to outputs/author_name_corrections.csv and removed from the XLSX.
# User clears the allcaps-both category, we move to allcaps-first next, etc.
DONE_CATEGORIES <- c("allcaps-both", "allcaps-first", "allcaps-last",
                     "surname-duplicated-in-middle",
                     "hyphen-lowercase",
                     "single-letter-surname",
                     "surname-first-comma",
                     "surname-duplicated-in-middle; surname-first-comma",
                     "allcaps-first; surname-duplicated-in-middle",
                     "allcaps-first; single-letter-surname",
                     "surname-first-comma; single-letter-surname",
                     "allcaps-first; surname-duplicated-in-middle; surname-first-comma",
                     "allcaps-first; surname-first-comma",
                     "allcaps-first; single-letter-surname; surname-duplicated-in-middle",
                     "hyphen-lowercase; surname-duplicated-in-middle",
                     "hyphen-lowercase; surname-duplicated-in-middle; surname-first-comma",
                     "surname-duplicated-in-middle; digit-in-name",
                     "surname-duplicated-in-middle; leading-punct",
                     "surname-first-comma; digit-in-name",
                     "allcaps-both; undefined-prefix",
                     "allcaps-last; undefined-prefix",
                     "allcaps-first; digit-in-name",
                     "allcaps-first; surname-duplicated-in-middle; leading-punct",
                     "leading-punct")
# For unicode-replacement rows: push upstream ONLY when the suggested names
# no longer contain the U+FFFD replacement character (i.e., the rule or
# dictionary resolved them).
UNICODE_CATEGORY <- "unicode-replacement"
CORR_PATH <- "outputs/author_name_corrections.csv"

if (length(DONE_CATEGORIES) > 0) {
  # Unicode rows pushable ONLY when the suggested fields no longer contain �
  unicode_clean <- out |>
    filter(grepl(UNICODE_CATEGORY, issue_type),
           !grepl("\uFFFD", suggested_first_name, fixed = TRUE),
           !grepl("\uFFFD", suggested_last_name,  fixed = TRUE))
  to_apply <- bind_rows(
    out |> filter(issue_type %in% DONE_CATEGORIES),
    unicode_clean
  ) |> distinct(openalex_author_id, .keep_all = TRUE)

  cat(sprintf("\nCategory-done: pushing %d rows (incl %d unicode-clean) → %s\n",
              nrow(to_apply), nrow(unicode_clean), CORR_PATH))

  if (nrow(to_apply) > 0) {
    new_corr <- to_apply |>
      transmute(openalex_author_id,
                corrected_first_name = suggested_first_name,
                corrected_last_name  = suggested_last_name,
                confidence,
                source = sprintf("category-done: %s", issue_type),
                notes)
    existing_corr <- if (file.exists(CORR_PATH)) {
      read_csv(CORR_PATH, show_col_types = FALSE)
    } else tibble()
    merged <- bind_rows(existing_corr, new_corr) |>
      distinct(openalex_author_id, .keep_all = TRUE)
    write_csv(merged, CORR_PATH)
    cat(sprintf("  Wrote %d total corrections to %s\n", nrow(merged), CORR_PATH))
    out <- out |> filter(!openalex_author_id %in% to_apply$openalex_author_id)
  }
}

# Auto-backup before overwriting — so we never silently lose user notes again.
BACKUP_DIR <- "outputs/.backups"
dir.create(BACKUP_DIR, showWarnings = FALSE, recursive = TRUE)
src <- "outputs/author_name_issues.xlsx"
if (file.exists(src)) {
  stamp <- format(Sys.time(), "%Y%m%d_%H%M%S")
  dest <- file.path(BACKUP_DIR, sprintf("author_name_issues_%s.xlsx", stamp))
  file.copy(src, dest, overwrite = FALSE)
  cat(sprintf("Backed up previous XLSX to %s\n", dest))
}

write_formatted_xlsx(out, "outputs/author_name_issues.xlsx", sheet = "name_issues")
cat(sprintf("\nXLSX now has %d rows remaining.\n", nrow(out)))
cat("Done.\n")
