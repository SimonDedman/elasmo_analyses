#!/usr/bin/env Rscript
# ============================================================================
# AUTHOR ATLAS — v2 data builder
# ============================================================================
# Produces canonical GeoJSON + JSON files for the MapLibre + deck.gl atlas.
# No visual layer here — this is the data step only. Visual layer is a
# separate React app that consumes these files.
#
# Reuses the same pipeline as build_author_network.R:
#   - author aliases (outputs/author_aliases.csv)
#   - location overrides (outputs/author_location_overrides.csv)
#   - last-known institutions (outputs/openalex_authors_last_institution.csv)
#
# Outputs (outputs/author_atlas/):
#   - authors.geojson      — one Point feature per author with full metadata
#   - institutions.geojson — one Point per institution cluster (author counts,
#                            top-N authors, aggregate paper counts)
#   - edges.json           — coauthor edges (weight = shared papers)
#   - stats.json           — summary counts for the UI (total authors etc.)
#
# Deploy step will copy outputs/author_atlas/ to docs/network_atlas/.
# ============================================================================

suppressPackageStartupMessages({
  library(tidyverse)
  library(jsonlite)
  library(arrow)
})

local_root <- "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
if (dir.exists(local_root)) {
  setwd(local_root)
}
# Otherwise assume we are already at the repo root (e.g. GitHub Actions
# runner), where relative paths like outputs/... resolve correctly.
`%||%` <- function(a, b) if (is.null(a)) b else a
OUT_DIR <- Sys.getenv("ATLAS_OUT_DIR", "outputs/author_atlas")  # override for test builds
dir.create(OUT_DIR, recursive = TRUE, showWarnings = FALSE)

cat("Loading source data...\n")
authors       <- read_csv("outputs/openalex_unique_authors.csv", show_col_types = FALSE)

# Apply name corrections from the reviewed XLSX (if present)
corr_path <- "outputs/author_name_corrections.csv"
if (file.exists(corr_path)) {
  corrections <- read_csv(corr_path, show_col_types = FALSE) |>
    select(openalex_author_id, corrected_first_name, corrected_last_name)
  authors <- authors |>
    mutate(oa_id = str_remove(openalex_author_id, "https://openalex.org/")) |>
    left_join(corrections, by = c("oa_id" = "openalex_author_id")) |>
    mutate(
      first_name = coalesce(corrected_first_name, first_name),
      last_name  = coalesce(corrected_last_name,  last_name),
      display_name = coalesce(
        ifelse(!is.na(corrected_first_name),
               trimws(paste(corrected_first_name, corrected_last_name)),
               NA_character_),
        display_name
      )
    ) |>
    select(-oa_id, -corrected_first_name, -corrected_last_name)
  cat(sprintf("  Applied %d name corrections\n",
              sum(!is.na(corrections$corrected_first_name))))
}
paper_authors <- read_csv("outputs/openalex_paper_authors.csv",  show_col_types = FALSE)
namsor        <- read_csv("outputs/namsor_enrichment.csv",       show_col_types = FALSE)

last_inst_path <- if (file.exists("outputs/openalex_authors_last_institution.openalex_api.csv")) {
  "outputs/openalex_authors_last_institution.openalex_api.csv"
} else {
  "outputs/openalex_authors_last_institution.csv"
}
last_inst <- if (file.exists(last_inst_path)) {
  x <- read_csv(last_inst_path, show_col_types = FALSE) |>
    mutate(openalex_author_id = str_remove(openalex_author_id, "https://openalex.org/"))

  # Precise-geocode corrections for institutions OpenAlex placed at a
  # generic city centroid (see scripts/geocode_institutions.py). Applied
  # BEFORE the per-author manual overrides below, so a manual override
  # (reviewed by a human) always wins over an automated re-geocode.
  geo_path <- "outputs/institution_geocode_corrections.csv"
  if (file.exists(geo_path)) {
    geo <- read_csv(geo_path, show_col_types = FALSE) |>
      filter(status == "geocoded") |>
      select(last_institution_id = institution_id, geo_lat = new_lat, geo_lon = new_lon)
    x <- x |>
      left_join(geo, by = "last_institution_id") |>
      mutate(
        last_institution_lat = coalesce(geo_lat, last_institution_lat),
        last_institution_lon = coalesce(geo_lon, last_institution_lon)
      ) |>
      select(-geo_lat, -geo_lon)
    cat(sprintf("  Applied %d precise-geocode institution corrections\n", nrow(geo)))
  }

  ov_path <- "outputs/author_location_overrides.csv"
  if (file.exists(ov_path)) {
    ov <- read_csv(ov_path, show_col_types = FALSE) |>
      mutate(openalex_author_id = str_remove(openalex_author_id, "https://openalex.org/"))
    x <- x |>
      left_join(ov |> select(-any_of("notes")),
                by = "openalex_author_id", suffix = c("", ".ov")) |>
      mutate(
        last_institution_name    = coalesce(last_institution_name.ov,    last_institution_name),
        last_institution_city    = coalesce(last_institution_city.ov,    last_institution_city),
        last_institution_region  = coalesce(last_institution_region.ov,  last_institution_region),
        last_institution_country = coalesce(last_institution_country.ov, last_institution_country),
        last_institution_lat     = coalesce(last_institution_lat.ov,     last_institution_lat),
        last_institution_lon     = coalesce(last_institution_lon.ov,     last_institution_lon)
      ) |>
      select(-ends_with(".ov"))
    cat(sprintf("  Applied %d location overrides\n", nrow(ov)))
  }
  x
} else NULL

# --- Author meta with enrichment -------------------------------------------
namsor_clean <- namsor |>
  mutate(openalex_author_id = str_remove(id, "https://openalex.org/")) |>
  select(openalex_author_id, namsor_gender, namsor_origin_country,
         namsor_origin_region, namsor_origin_subregion, namsor_ethnicity)

ns_ov_path <- "outputs/namsor_overrides.csv"
if (file.exists(ns_ov_path)) {
  ns_ov <- read_csv(ns_ov_path, show_col_types = FALSE,
                    col_types = cols(.default = col_character())) |>
    select(openalex_author_id, any_of(c("namsor_gender", "namsor_origin_country", "namsor_ethnicity")))
  namsor_clean <- namsor_clean |>
    left_join(ns_ov, by = "openalex_author_id", suffix = c("", ".ov")) |>
    mutate(
      namsor_gender         = coalesce(na_if(namsor_gender.ov, ""),         namsor_gender),
      namsor_origin_country = coalesce(na_if(namsor_origin_country.ov, ""), namsor_origin_country),
      namsor_ethnicity      = coalesce(na_if(namsor_ethnicity.ov, ""),      namsor_ethnicity)
    ) |>
    select(-ends_with(".ov"))
  cat(sprintf("  Applied %d NamSor overrides\n", nrow(ns_ov)))
}

# Genderize was retired; its `gender` column is no longer in openalex_unique_authors.csv.
# NamSor gender comes first in the case_when below, so an absent fallback is harmless.
if (!"gender" %in% names(authors)) authors$gender <- NA_character_

# Last-resort gender: the Genderize/gender-guesser cache, keyed on the exact first_name string
# ("Demian D.", "M. B."), which recovers names gender_guesser alone cannot parse.
gz_path <- "outputs/.genderize_cache.json"
gz <- if (file.exists(gz_path)) {
  raw <- jsonlite::fromJSON(gz_path, simplifyVector = FALSE)
  tibble(first_name = names(raw),
         gz_gender = vapply(raw, function(v) if (is.list(v)) (v$gender %||% NA_character_) else as.character(v %||% NA), character(1)))
} else tibble(first_name = character(), gz_gender = character())

author_meta <- authors |>
  mutate(openalex_author_id = str_remove(openalex_author_id, "https://openalex.org/")) |>
  left_join(namsor_clean, by = "openalex_author_id") |>
  left_join(gz, by = "first_name") |>
  mutate(gender_final = case_when(
    namsor_gender %in% c("M", "male")   ~ "M",
    namsor_gender %in% c("F", "female") ~ "F",
    gender %in% c("male")               ~ "M",
    gender %in% c("female")             ~ "F",
    gz_gender %in% c("male")            ~ "M",
    gz_gender %in% c("female")          ~ "F",
    TRUE                                 ~ "Unknown"
  )) |>
  select(-gz_gender)

if (!is.null(last_inst)) {
  author_meta <- author_meta |>
    left_join(last_inst, by = "openalex_author_id") |>
    mutate(
      institution_final = coalesce(last_institution_name, most_common_institution),
      country_final     = coalesce(last_institution_country, institution_country),
      inst_city         = last_institution_city,
      inst_region       = last_institution_region,
      inst_lat          = last_institution_lat,
      inst_lon          = last_institution_lon
    )
} else {
  author_meta <- author_meta |>
    mutate(
      institution_final = most_common_institution,
      country_final     = institution_country,
      inst_city = NA_character_, inst_region = NA_character_,
      inst_lat = NA_real_, inst_lon = NA_real_
    )
}

# --- Alias merge (drop duplicate profiles) --------------------------------
aliases_path <- "outputs/author_aliases.csv"
if (file.exists(aliases_path)) {
  aliases <- read_csv(aliases_path, show_col_types = FALSE) |>
    select(alias_openalex_id, canonical_openalex_id, canonical_name_override = canonical_name)
  cat(sprintf("  Loaded %d author aliases\n", nrow(aliases)))

  remap_ids <- function(ids) {
    hits <- aliases$canonical_openalex_id[match(ids, aliases$alias_openalex_id)]
    coalesce(hits, ids)
  }

  paper_authors <- paper_authors |>
    mutate(openalex_author_id = str_remove(openalex_author_id, "https://openalex.org/"),
           openalex_author_id = remap_ids(openalex_author_id))

  # Pick up expanded canonical_name for canonicals touched by an expansion-merge.
  # .keep_all = TRUE pins each canonical_openalex_id to a SINGLE alias row
  # (the first one, by CSV order) so conflicting alias canonical_name values
  # can't re-fan-out one author into multiple map points.
  canonical_name_map <- aliases |>
    distinct(canonical_openalex_id, .keep_all = TRUE)

  author_meta <- author_meta |>
    filter(!openalex_author_id %in% aliases$alias_openalex_id) |>
    left_join(canonical_name_map,
              by = c("openalex_author_id" = "canonical_openalex_id")) |>
    mutate(display_name = coalesce(canonical_name_override, display_name)) |>
    select(-canonical_name_override)

  new_counts <- paper_authors |>
    filter(!is.na(literature_id), !is.na(openalex_author_id)) |>
    distinct(literature_id, openalex_author_id) |>
    count(openalex_author_id, name = "new_paper_count")

  author_meta <- author_meta |>
    left_join(new_counts, by = "openalex_author_id") |>
    mutate(paper_count = coalesce(new_paper_count, paper_count)) |>
    select(-new_paper_count)
  cat(sprintf("  After alias merge: %d authors\n", nrow(author_meta)))
}

# --- Coauthor edges --------------------------------------------------------
cat("Building coauthor edges...\n")
paper_author_clean <- paper_authors |>
  filter(!is.na(literature_id), !is.na(openalex_author_id)) |>
  select(literature_id, openalex_author_id) |>
  distinct()

coauthor_edges <- paper_author_clean |>
  group_by(literature_id) |>
  filter(n() > 1) |>
  summarise(
    pairs = list(combn(sort(openalex_author_id), 2, simplify = FALSE)),
    .groups = "drop"
  ) |>
  unnest(pairs) |>
  mutate(from = sapply(pairs, `[`, 1),
         to   = sapply(pairs, `[`, 2)) |>
  select(from, to) |>
  count(from, to, name = "weight")

# --- Focal network: authors with >=3 papers, edges weight >=1 -------------
# ATLAS_MIN_PAPERS / ATLAS_REQUIRE_COAUTHOR let a test build include everyone with a location
# (e.g. ATLAS_MIN_PAPERS=1 ATLAS_REQUIRE_COAUTHOR=0); the published map uses 3 and TRUE.
MIN_PAPERS <- as.integer(Sys.getenv("ATLAS_MIN_PAPERS", "3"))
REQUIRE_COAUTHOR <- Sys.getenv("ATLAS_REQUIRE_COAUTHOR", "1") != "0"
focal_authors <- author_meta |> filter(paper_count >= MIN_PAPERS)
focal_ids <- focal_authors$openalex_author_id
edges_focal <- coauthor_edges |>
  filter(from %in% focal_ids & to %in% focal_ids)

connected_ids <- unique(c(edges_focal$from, edges_focal$to))
nodes_focal <- if (REQUIRE_COAUTHOR) focal_authors |> filter(openalex_author_id %in% connected_ids) else focal_authors

cat(sprintf("Focal network: %d authors, %d edges\n",
            nrow(nodes_focal), nrow(edges_focal)))

# --- Per-author year range from local parquet ----------------------------
cat("Computing per-author year ranges...\n")
year_ranges <- tryCatch({
  papers_yr <- read_parquet("outputs/literature_review_enriched.parquet") |>
    select(literature_id, year) |>
    filter(!is.na(year), year >= 1900, year <= 2030) |>
    mutate(literature_id = as.character(literature_id))
  paper_authors |>
    mutate(literature_id = as.character(literature_id)) |>
    inner_join(papers_yr, by = "literature_id") |>
    group_by(openalex_author_id) |>
    summarise(year_min = min(year, na.rm = TRUE),
              year_max = max(year, na.rm = TRUE),
              .groups = "drop")
}, error = function(e) {
  cat("  parquet unavailable — skipping year enrichment\n")
  tibble(openalex_author_id = character(),
         year_min = integer(), year_max = integer())
})
cat(sprintf("  Year ranges for %d authors\n", nrow(year_ranges)))

# --- Per-author research profiles ------------------------------------------
# Joins author -> paper (alias-merged paper_authors) -> binary classification columns of the
# enriched parquet. Present = value > 0 (NA = 0). Counts are papers, not mentions.
cat("Computing per-author research profiles...\n")
suppressPackageStartupMessages(library(Matrix))

humanise <- function(core) {
  w <- strsplit(core, "_")[[1]]
  paste(c(toupper(substring(w[1], 1, 1)) |> paste0(substring(w[1], 2)), w[-1]), collapse = " ")
}
ACR <- c("AKDE","CPUE","BRUV","BRUVS","eDNA","GLM","GAM","GLMM","BRT","SDM","MaxEnt","PIT","DNA","RNA",
         "SNP","mtDNA","PCR","ROV","AUV","UAV","DIDSON","MPA","IUCN","CITES","FAO","EEZ","SST","ENSO",
         "PSAT","SPOT","VHF","UV","IUU","BRD")
EXP <- c(akde="autocorrelated kernel density estimation", cpue="catch per unit effort",
         bruv="baited remote underwater video", bruvs="baited remote underwater video system",
         sdm="species distribution model", glm="generalised linear model",
         gam="generalised additive model", glmm="generalised linear mixed model",
         brt="boosted regression trees", psat="pop-up satellite archival tag",
         edna="environmental DNA", pit="passive integrated transponder",
         rov="remotely operated vehicle", auv="autonomous underwater vehicle",
         uav="unmanned aerial vehicle", snp="single-nucleotide polymorphism",
         mpa="marine protected area", eez="exclusive economic zone", sst="sea surface temperature",
         iuu="illegal, unreported and unregulated", brd="bycatch reduction device")
decorate <- function(label) {
  k <- tolower(trimws(label)); acr <- ACR[match(k, tolower(ACR))]
  if (!is.na(acr)) { e <- EXP[k]; return(if (!is.na(e)) sprintf("%s (%s)", acr, e) else acr) }
  w <- strsplit(label, " ")[[1]]; a <- ACR[match(tolower(w), tolower(ACR))]
  paste(ifelse(is.na(a), w, a), collapse = " ")
}
# Same mapping as scripts/rag/labels.py::label_for for a_ columns
slug <- function(n) paste0("a_", gsub("^_+|_+$", "", gsub("[^a-z0-9&/]+", "_", tolower(n))))
tech_names <- read_csv("data/master_techniques.csv", show_col_types = FALSE) |>
  filter(!is.na(technique_name)) |> mutate(col = slug(technique_name))
tech_label <- function(cols) vapply(cols, function(cn) {
  nm <- tech_names$technique_name[match(cn, tech_names$col)]
  decorate(if (is.na(nm)) humanise(sub("^a_", "", cn)) else trimws(nm))
}, character(1))
title_case <- function(x) vapply(strsplit(gsub("_", " ", x), " "), function(w)
  paste(ifelse(seq_along(w) > 1 & w %in% c("of","the","and","in"), w,
               paste0(toupper(substring(w, 1, 1)), substring(w, 2))), collapse = " "), character(1))
sp_label <- function(cols) vapply(strsplit(sub("^sp_", "", cols), "_"), function(w)
  paste(c(paste0(toupper(substring(w[1], 1, 1)), substring(w[1], 2)), w[-1]), collapse = " "), character(1))

pq <- read_parquet("outputs/literature_review_enriched.parquet")
pq$literature_id <- as.character(pq$literature_id)
pq <- pq[!duplicated(pq$literature_id), ]
bin <- function(prefix) {
  cols <- grep(paste0("^", prefix), names(pq), value = TRUE)
  m <- as.matrix(as.data.frame(lapply(pq[cols], function(v) { v <- as.numeric(v); v[is.na(v)] <- 0; v > 0 })))
  storage.mode(m) <- "numeric"; colnames(m) <- cols; Matrix(m, sparse = TRUE)
}
# Species are mention COUNTS. Most papers name a species in passing (1,773 of the 2,629 papers
# mentioning white shark do so once), so "any mention" made the Species filter match 41% of
# authors. A species counts as a paper's FOCUS when it is mentioned >= 3 times and >= 25% as often
# as that paper's most-mentioned species, or is the paper's top species with >= 2 mentions.
sp_focus <- function() {
  cols <- grep("^sp_", names(pq), value = TRUE)
  m <- as.matrix(as.data.frame(lapply(pq[cols], function(v) { v <- as.numeric(v); v[is.na(v)] <- 0; v })))
  top <- apply(m, 1, max)
  f <- (m >= 3 & m >= 0.25 * top) | (m == top & m >= 2)
  storage.mode(f) <- "numeric"; colnames(f) <- cols; Matrix(f, sparse = TRUE)
}
FAM <- list(
  disc = list(M = bin("d_"),  lab = function(c) title_case(sub("^d_", "", c))),
  tech = list(M = bin("a_"),  lab = tech_label),
  sp   = list(M = sp_focus(), lab = sp_label),
  ob   = list(M = bin("ob_"), lab = function(c) title_case(sub("^ob_", "", c)))
)
# study country as one-hot
ctry <- pq$geo_study_country; ctry[is.na(ctry) | ctry == ""] <- NA
cl <- sort(unique(na.omit(ctry)))
CM <- sparseMatrix(i = which(!is.na(ctry)), j = match(ctry[!is.na(ctry)], cl), x = 1,
                   dims = c(nrow(pq), length(cl)), dimnames = list(NULL, cl))
dec <- floor(suppressWarnings(as.numeric(pq$year)) / 10) * 10
dl <- sort(unique(na.omit(dec[dec >= 1900 & dec <= 2020])))
DM <- sparseMatrix(i = which(!is.na(dec) & dec %in% dl), j = match(dec[!is.na(dec) & dec %in% dl], dl), x = 1,
                   dims = c(nrow(pq), length(dl)), dimnames = list(NULL, as.character(dl)))

ap <- paper_authors |>
  mutate(literature_id = as.character(literature_id)) |>
  filter(!is.na(literature_id), !is.na(openalex_author_id), literature_id %in% pq$literature_id)
ap_pos <- ap |> group_by(openalex_author_id, literature_id) |>
  summarise(first = any(author_position == "first"), last = any(author_position == "last"), .groups = "drop")
prof_ids <- unique(nodes_focal$openalex_author_id)
ap_pos <- ap_pos |> filter(openalex_author_id %in% prof_ids)
ai <- match(ap_pos$openalex_author_id, prof_ids); pi_ <- match(ap_pos$literature_id, pq$literature_id)
AP <- sparseMatrix(i = ai, j = pi_, x = 1, dims = c(length(prof_ids), nrow(pq)))
n_prof_papers <- as.numeric(rowSums(AP))
share <- function(flag) { s <- sparseMatrix(i = ai[flag], j = seq_along(ai)[flag], x = 1, dims = c(length(prof_ids), length(ai)))
  as.numeric(rowSums(s)) }
first_n <- tabulate(ai[ap_pos$first], length(prof_ids)); last_n <- tabulate(ai[ap_pos$last], length(prof_ids))

top_pairs <- function(CNT, labels, k) {   # CNT: authors x features (sparse); returns list of list(list(label,n),...)
  CNT <- as(CNT, "RsparseMatrix")
  lapply(seq_len(nrow(CNT)), function(r) {
    st <- CNT@p[r] + 1; en <- CNT@p[r + 1]
    if (en < st) return(list())
    j <- CNT@j[st:en] + 1; x <- CNT@x[st:en]
    o <- order(-x, labels[j])[seq_len(min(k, length(j)))]
    lapply(o, function(q) list(labels[j[q]], as.integer(x[q])))
  })
}
paper_cnt <- colSums(FAM$disc$M)
disc_lab <- FAM$disc$lab(colnames(FAM$disc$M))
CD <- AP %*% FAM$disc$M
disc_main <- vapply(seq_len(nrow(CD)), function(r) {
  v <- CD[r, ]; if (all(v == 0)) return("Unclassified")
  cand <- which(v == max(v)); disc_lab[cand[which.max(paper_cnt[cand])]]
}, character(1))
profile <- tibble(
  openalex_author_id = prof_ids,
  disc_main = disc_main,
  dt = top_pairs(CD, disc_lab, 3),
  tt = top_pairs(AP %*% FAM$tech$M, FAM$tech$lab(colnames(FAM$tech$M)), 5),
  st = top_pairs(AP %*% FAM$sp$M,   FAM$sp$lab(colnames(FAM$sp$M)), 5),
  bs = top_pairs(AP %*% FAM$ob$M,   FAM$ob$lab(colnames(FAM$ob$M)), 9),
  sc = top_pairs(AP %*% CM, cl, 5),
  dc = top_pairs(AP %*% DM, as.character(dl), 12),
  fs = round(first_n / pmax(n_prof_papers, 1), 3),
  ls = round(last_n  / pmax(n_prof_papers, 1), 3)
)
# Within-author lists are sorted by count; decades chronologically
profile$dc <- lapply(profile$dc, function(l) l[order(vapply(l, function(z) z[[1]], ""))])
nco <- bind_rows(coauthor_edges |> transmute(id = from, o = to), coauthor_edges |> transmute(id = to, o = from)) |>
  count(id, name = "nc")
profile <- profile |> left_join(nco, by = c("openalex_author_id" = "id")) |> mutate(nc = coalesce(nc, 0L))

# Vocabulary (author counts, over mapped authors) for the front-end filters; called after authors_geo exists
# Full (not top-N) membership as 0-based indices into the vocab arrays, so the filters match
# "any of the author's papers carries X" rather than only the displayed top few.
# Species also need to RECUR for an author (>= 2 focus papers, or >= 20% of their papers), so one
# co-authored paper on a species does not file a prolific author under it.
sp_member <- function(M) { C <- AP %*% M; (C >= 2) | (C >= 0.2 * pmax(n_prof_papers, 1) & C > 0) }
idx_lists <- function(fam_M, member = function(M) AP %*% M > 0) {
  R <- as(member(fam_M), "RsparseMatrix")
  lapply(seq_len(nrow(R)), function(r) { st <- R@p[r] + 1; en <- R@p[r + 1]
    if (en < st) I(integer(0)) else I(as.integer(R@j[st:en])) })   # I(): keep length-1 as a JSON array
}
profile$dx <- idx_lists(FAM$disc$M)
profile$tx <- idx_lists(FAM$tech$M)
profile$sx <- idx_lists(FAM$sp$M, sp_member)
# Vocabulary in fixed column order (array position = the index above); `authors` counts the mapped
# authors only, so the front end can hide zero-count entries and sort by count.
make_vocab <- function(mask) {
  vocab_of <- function(fam_M, labs)
    tibble(label = labs, authors = as.integer(colSums((AP[mask, , drop = FALSE] %*% fam_M) > 0)))
  list(disciplines = vocab_of(FAM$disc$M, FAM$disc$lab(colnames(FAM$disc$M))),
       techniques  = vocab_of(FAM$tech$M, FAM$tech$lab(colnames(FAM$tech$M))),
       species     = tibble(label = FAM$sp$lab(colnames(FAM$sp$M)),
                            authors = as.integer(colSums(sp_member(FAM$sp$M)[mask, , drop = FALSE]))),
       basins      = vocab_of(FAM$ob$M,   FAM$ob$lab(colnames(FAM$ob$M))))
}
cat(sprintf("  Profiles for %d authors\n", nrow(profile)))

# --- GeoJSON: authors -----------------------------------------------------
# One Point feature per author with coordinates. Drop authors without
# institution coordinates (they have no place on a map).
authors_geo <- nodes_focal |>
  filter(!is.na(inst_lon), !is.na(inst_lat)) |>
  left_join(year_ranges, by = "openalex_author_id") |>
  left_join(profile, by = "openalex_author_id") |>
  transmute(
    id = openalex_author_id,
    name = display_name,
    institution = institution_final,
    city = inst_city,
    region = inst_region,
    country = country_final,
    papers = paper_count,
    gender = gender_final,
    origin_country = namsor_origin_country,
    origin_region  = namsor_origin_region,
    ethnicity      = namsor_ethnicity,
    year_min = year_min,
    year_max = year_max,
    disc_main, dt, tt, st, bs, sc, dc, fs, ls, nc, dx, tx, sx,
    lon = inst_lon,
    lat = inst_lat
  )

cat(sprintf("Authors on map: %d (%.1f%% of focal)\n",
            nrow(authors_geo), 100 * nrow(authors_geo) / nrow(nodes_focal)))

# Build feature list without allocating 30K individual lists (manual geojson)
build_feature_collection <- function(df, lon_col = "lon", lat_col = "lat") {
  feats <- vector("list", nrow(df))
  lon <- df[[lon_col]]; lat <- df[[lat_col]]
  prop_df <- df |> select(-all_of(c(lon_col, lat_col)))
  for (i in seq_len(nrow(df))) {
    feats[[i]] <- list(
      type = "Feature",
      geometry = list(type = "Point", coordinates = c(lon[i], lat[i])),
      properties = {
        p <- as.list(prop_df[i, ])
        for (k in names(p)) if (is.list(p[[k]])) p[[k]] <- p[[k]][[1]]   # unwrap list-columns
        p
      }
    )
  }
  list(type = "FeatureCollection", features = feats)
}

authors_fc <- build_feature_collection(authors_geo)
write(toJSON(authors_fc, auto_unbox = TRUE, digits = 5, na = "null"),
      file = file.path(OUT_DIR, "authors.geojson"))
cat(sprintf("Wrote %s/authors.geojson\n", OUT_DIR))

# --- GeoJSON: institutions (aggregated clusters) --------------------------
institutions <- authors_geo |>
  mutate(lon_rnd = round(lon, 3), lat_rnd = round(lat, 3)) |>
  group_by(lon_rnd, lat_rnd, institution) |>
  summarise(
    lon = mean(lon), lat = mean(lat),
    city = first(city), region = first(region), country = first(country),
    author_count = n(),
    total_papers = sum(papers),
    author_ids = list(id),
    top_authors = paste(head(name[order(-papers)], 5), collapse = " · "),
    .groups = "drop"
  ) |>
  arrange(desc(author_count))

# Flatten author_ids into a comma-joined string for GeoJSON props (JSON
# doesn't support nested arrays in a CSV-y way, but strings are safe).
institutions <- institutions |>
  mutate(author_ids = sapply(author_ids, function(ids) paste(ids, collapse = ",")))

inst_fc <- build_feature_collection(institutions |>
                                    select(-lon_rnd, -lat_rnd))
write(toJSON(inst_fc, auto_unbox = TRUE, digits = 5, na = "null"),
      file = file.path(OUT_DIR, "institutions.geojson"))
cat(sprintf("Wrote %s/institutions.geojson (%d clusters)\n",
            OUT_DIR, nrow(institutions)))

# --- Edges JSON -----------------------------------------------------------
# Keep only edges between authors that made it onto the map.
mapped_ids <- authors_geo$id
edges_out <- edges_focal |>
  filter(from %in% mapped_ids & to %in% mapped_ids) |>
  rename(weight = weight)

write(toJSON(edges_out, auto_unbox = TRUE, na = "null"),
      file = file.path(OUT_DIR, "edges.json"))
cat(sprintf("Wrote %s/edges.json (%d edges)\n", OUT_DIR, nrow(edges_out)))

vocab <- make_vocab(prof_ids %in% authors_geo$id)
write(toJSON(lapply(vocab, function(d) lapply(seq_len(nrow(d)), function(i) list(d$label[i], d$authors[i]))),
             auto_unbox = TRUE), file = file.path(OUT_DIR, "vocab.json"))
cat(sprintf("Wrote %s/vocab.json\n", OUT_DIR))

# --- Summary stats --------------------------------------------------------
stats <- list(
  build_timestamp  = format(Sys.time(), "%Y-%m-%d %H:%M:%S %Z"),
  total_authors    = nrow(authors_geo),
  total_institutions = nrow(institutions),
  total_edges      = nrow(edges_out),
  by_country = as.list(authors_geo |> count(country, sort = TRUE) |>
                       head(20) |> deframe()),
  by_gender  = as.list(authors_geo |> count(gender) |> deframe()),
  min_papers = MIN_PAPERS,
  year_min = if (any(!is.na(authors_geo$year_min)))
    min(authors_geo$year_min, na.rm = TRUE) else NA,
  year_max = if (any(!is.na(authors_geo$year_max)))
    max(authors_geo$year_max, na.rm = TRUE) else NA
)
write(toJSON(stats, auto_unbox = TRUE, pretty = TRUE, na = "null"),
      file = file.path(OUT_DIR, "stats.json"))
cat(sprintf("Wrote %s/stats.json\n", OUT_DIR))

cat("\nDone.\n")
