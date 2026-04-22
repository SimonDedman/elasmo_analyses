# Extraction Logic Review Reference

*For team review of classification schemas and extraction techniques*

*Generated: 2026-04-03*

**Related documents:**
- [extraction_logic.md](extraction_logic.md) — Full technical documentation
- [extraction_quality_issues.md](extraction_quality_issues.md) — False-positive catalogue and fix tracking
- [GitHub #7: Threshold and anchor decisions](https://github.com/SimonDedman/elasmo_analyses/issues/7)
- [GitHub #8: Nationality, Diversity, Ethnicity](https://github.com/SimonDedman/elasmo_analyses/issues/8)
- [GitHub #1: Ground truth vs existing lit reviews](https://github.com/SimonDedman/elasmo_analyses/issues/1)

**Source of truth for all keyword/threshold definitions:** [`scripts/extract_schema_columns.py` lines 92–299](https://github.com/SimonDedman/elasmo_analyses/blob/main/scripts/extract_schema_columns.py#L92-L299)

---

## Part 1: Extraction Techniques Inventory

Every column uses one or more of the following techniques. Codes are referenced in Part 2.

| Code | Technique | Description | Example | Currently used by | Documentation |
|------|-----------|-------------|---------|-------------------|---------------|
| **KM** | Keyword match | Simple presence/absence match for a single known term (threshold=1, no frequency scoring). Term is matched as a whole-word regex (`\bterm\b`). | `sp_carcharodon_carcharias`: matches the binomial name "*Carcharodon carcharias*" once anywhere in the text → binary=1 | 1,308 sp_ columns; 215 a_ columns (with synonyms) | [extraction_logic.md #term-types](extraction_logic.md#term-types) |
| **KFT** | Keyword frequency threshold | Total mentions of all synonyms must reach ≥N for binary=1. Higher thresholds filter passing mentions of generic terms. | `eco_marine` (threshold=3): "marine" ×2 + "ocean" ×1 = 3 → binary=1; "marine" ×1 alone → binary=0 | All 123 schema columns (eco_, pr_, gear_, imp_, d_, b_) | [extraction_logic.md #universal-frequency-based-scoring](extraction_logic.md#universal-frequency-based-scoring) |
| **ANC** | Context anchors | At least one anchor term (e.g. "population", "decline") must co-occur anywhere in the text for binary=1, even if frequency threshold is met. Prevents ambiguous terms scoring without supporting context. | `imp_abundance` (anchors: population, decline, trend): "abundance" ×3 but no anchor → binary=0; "abundance" ×2 + "population decline" → binary=1 | 6 imp_ columns + 3 added imp_ columns = 9 total | [extraction_logic.md #universal-frequency-based-scoring](extraction_logic.md#universal-frequency-based-scoring) |
| **KPC** | Keyword proximity check | Each keyword match only counts if a specified anchor term set (currently: elasmobranch vocabulary — shark, ray, skate, chimaera, plus ~30 common names and higher taxa) appears within ±1 sentence. Matches without a nearby anchor are discarded from the frequency count. Generalisable to other anchor sets. | `imp_abundance`: "abundance" appears in a sentence about invertebrate populations with no elasmobranch term nearby → match discarded | 19 columns (most imp_, most d_, eco_pelagic) | [extraction_quality_issues.md #2-subject-mismatch-sm--implemented](extraction_quality_issues.md#2-subject-mismatch-sm--implemented) |
| **SW** | Section-weighted scoring | PDF text is parsed into labelled sections (Abstract, Introduction, Methods, Results, Results & Discussion, Discussion, Conclusions, Other). Each keyword match is multiplied by a section-specific weight (1.0 / 0.5 / 0.25) that varies by schema. Reduces false positives from background/contextual mentions. | `gear_` schema: Methods=1.0, Abstract/Results=0.5, Introduction/Discussion=0.25; so "longline" ×4 in Methods = 4.0, but "longline" ×4 in Introduction = 1.0 | All 123 schema columns (weights differ by schema prefix) | [extraction_quality_issues.md #6-contextual-mention-cm--implemented](extraction_quality_issues.md#6-contextual-mention-cm--implemented) |
| **AC** | Case-sensitive acronym matching | Specified acronym terms are matched uppercase only, preventing collision with common lowercase words. | "RAMP" matches only uppercase (Reflex Action Mortality Predictor), not "boat ramp" | 25 acronyms across 20 columns | [extraction_quality_issues.md #4-acronym-collision-ac--implemented](extraction_quality_issues.md#4-acronym-collision-ac--implemented) |
| **SS** | Section stripping | Entire sections are removed before any keyword matching: front matter (before Abstract), reference list (after REFERENCES/BIBLIOGRAPHY header), acknowledgements/funding/data availability (last 30% of text). | "Marine Pollution Bulletin" in reference list no longer triggers `pr_pollution_chemical` | All columns processed from PDFs | [extraction_logic.md #section-stripping-false-positive-mitigation](extraction_logic.md#section-stripping-false-positive-mitigation) |
| **WC** | Wildcard matching | Prefix match using `term*` syntax, compiled to `\bterm\w*`. Word-boundary prefix prevents mid-word matches. | `fish*` matches "fishing", "fishery", "fisheries" but not "selfish"; `estuarin*` matches "estuarine", "estuarina" | Many schema columns | [extraction_logic.md #term-types](extraction_logic.md#term-types) |
| **PH** | Phrase matching | Multi-word exact sequence, compiled to `\bword1 word2\b`. | `coral reef`, `post-release mortality`, `deep scattering layer` | Many schema columns | [extraction_logic.md #term-types](extraction_logic.md#term-types) |
| **AND** | AND logic | Both terms must appear anywhere in the text (not necessarily adjacent). | `(acidification AND pH)` — both must be present | 2 terms in `pr_ocean_acidification` | [extraction_logic.md #term-types](extraction_logic.md#term-types) |
| **RX** | Raw regex | Custom regex pattern passed through directly. Case-sensitive by default (to prevent unintended matches). | `Ne\b` for effective population size (N~e~) — case-sensitive to avoid matching "ne" in "determine" | 1 column (`imp_genetic`) |  [extraction_logic.md #term-types](extraction_logic.md#term-types) |
| **RE** | Regex extraction | Custom regex patterns extract free-text values (not binary classification). Captures named groups or specific fields from surrounding text. | `depth_min_m`: regex matches "depths of 150 m to 300 m" → extracts 150 and 300 as floats; `gear_target_species`: regex matches "{word} longline" → extracts "tuna" | depth_ (3 cols), gear_target_species, imp_direction, imp_quantified | [extraction_logic.md #depth-extraction](extraction_logic.md#depth-extraction) |
| **DRV** | Derived / rule-based | Column value is computed from other extracted columns using priority-ordered logic or conditional rules. No direct text matching. | `eco_1_guess`: iterates eco_ binary columns in priority order (marine > freshwater > brackish); picks first =1 as the realm guess | eco_N_guess (3 cols), imp_is_bycatch, imp_confidence | [extraction_logic.md #ecosystem-guesses](extraction_logic.md#ecosystem-guesses) |
| **SA** | Sentiment analysis | Counts positive vs negative cue words near impact terms. Classifies overall direction based on relative frequency of cues. | `imp_direction`: counts "decline", "decrease", "loss" (negative) vs "increase", "recover", "improve" (positive) → returns "negative", "positive", "mixed", or "not stated" | imp_direction (1 col) | [extraction_logic.md #impact-direction-and-quantification](extraction_logic.md#impact-direction-and-quantification) |
| **API** | External API lookup | Queries an external web API using a key column (typically DOI or journal name) and retrieves structured metadata. Results stored in separate CSV files, joined to main database on `literature_id` or `doi`. | OpenAlex: DOI → author names, institutions, countries. Altmetric: DOI → attention score, tweet count. Unpaywall: DOI → OA status, licence. | Author enrichment (OpenAlex), Altmetric scores, Open access (Unpaywall), Journal quality (Scimago) | Scripts: `enrich_authors_openalex.py`, `enrich_altmetric.py`, `lookup_unpaywall_oa.py`, `lookup_scimago_journals.py` |
| **GEO** | Geographic extraction | Institution names parsed from PDF front matter; country and region assigned via lookup tables. Study locations extracted from text. Parachute research flag derived by comparing author country to study country. | First author at "University of Miami" → country=US, region=North America; study mentions "Mozambique Channel" → study_country=Mozambique; author≠study country → parachute_research=True | paper_geography table (23 fields), ob_ columns (9) | [docs/geographic/](../geographic/) |
| **GI** | Gender inference | First name matched against offline gender-guesser library, with fallback to Genderize.io API for unresolved names. Strategies: direct lookup → accent stripping → initial-skipping → API. | "María" → female (gender-guesser); "Xiang" → unknown (gender-guesser) → male (Genderize.io API, p=0.92) | gender column in author CSVs | Script: `infer_author_gender.py` |

### Proposed new techniques (not yet implemented)

| Code | Technique | Description | Rationale |
|------|-----------|-------------|-----------|
| **CS** | Citation stripping | Remove inline parenthetical citations (e.g. "(Pelagic et al., 2026)", "(Smith & Jones, 2024)") from body text before keyword matching. | Author surnames in inline citations can match keywords (e.g. an author named "Pelagic" triggering `eco_pelagic`). Currently only reference *sections* are stripped, not inline citations within body text. |
| **LN** | Length normalisation | Normalise frequency thresholds by paper length (e.g. mentions per 1,000 words). | Raised in [GitHub #7 comment by David R-G](https://github.com/SimonDedman/elasmo_analyses/issues/7#issuecomment-2737002247): "10 mentions in a 1,000-word paper" differs from the same count in a 15,000-word paper. Counter-argument: genuinely relevant papers should meet absolute thresholds regardless of length. |

### Quick-reference legend

KM=Keyword match, KFT=Keyword frequency threshold, ANC=Context anchors, KPC=Keyword proximity check, SW=Section-weighted scoring, AC=Case-sensitive acronym matching, SS=Section stripping, WC=Wildcard matching, PH=Phrase matching, AND=AND logic, RX=Raw regex, RE=Regex extraction, DRV=Derived/rule-based, SA=Sentiment analysis, API=External API lookup, GEO=Geographic extraction, GI=Gender inference.

---

## Part 2: Column Tables

Tables are ordered as columns appear in the database. Each table lists every column with its extraction configuration. **Techniques** column uses codes from Part 1.

**Review process:** An accompanying [review spreadsheet](../review/extraction_review_comments.xlsx) provides one row per content item with columns per reviewer for collaborative comments and proposed edits. Changes are synced via Google Sheets and monitored for updates.

---

### Paper metadata — 14 columns

These columns come from the input database (Shark-References and other sources). Not extracted by our pipeline.

| Column | Label | Description | Source | Notes |
|--------|-------|-------------|--------|-------|
| `year` | Publication year | Year of publication | Input parquet | |
| `title` | Title | Paper title | Input parquet | |
| `authors` | Authors | Author list (string) | Input parquet | |
| `doi` | DOI | Digital object identifier — primary key for API lookups | Input parquet | |
| `abstract` | Abstract | Paper abstract text | Input parquet | |
| `literature_id` | Literature ID | Primary key linking to Shark-References database | Input parquet | |
| `pdf_url` | PDF URL | URL or path to PDF file | Input parquet | |
| `date_added` | Date added | When paper was added to database | Input parquet | |
| `data_source` | Data source | Source of paper record (Shark-References, Web of Science, etc.) | Input parquet | |
| `journal` | Journal | Journal name | Input parquet | |
| `epoch` | Epoch | Temporal grouping | Input parquet | |
| `country` | Country | Study country (from source database, not our extraction) | Input parquet | |
| `superregion` | Superregion | Geographic region classification | Input parquet | |
| `study_type` | Paper type | One of `corrigendum`/`letter`/`review`/`synthesis`/`conceptual`/`empirical` (or `None` for non-PDF papers) | Banner-first classifier on page 1 of PDF | See [`study_type_proposal.md`](study_type_proposal.md) · audit page [`study_type_audit.html`](../study_type_audit.html) |
| `study_type_signal` | Classifier signal | `banner` / `title_kw` / `default_empirical` / `no_pdf` | Classifier | Provenance of the study_type label |
| `study_type_evidence` | Matched snippet | Banner token or title phrase that fired | Classifier | ≤80 chars |

---

### Techniques (`a_`) — 215 columns

Each technique is matched by its name + alternative search query + synonyms, all loaded from the taxonomy Excel file. Compiled to `\bterm\b` whole-word regexes. Binary presence/absence per technique per paper. 215 techniques retained after removing 42 priority-3 entries.

| Column(s) | Label | Keywords / method | Techniques | Notes |
|-----------|-------|-------------------|------------|-------|
| `a_accelerometry` ... `a_x_ray_fluorescence` (215 total) | Research technique names | Technique name + `search_query` + `search_query_alt` + `synonyms` fields from Excel taxonomy. | KM, SS | Technique names, synonyms, and search queries defined in the Excel taxonomy, not in code. |

**Script:** [`scripts/extract_techniques_from_pdfs.py`](https://github.com/SimonDedman/elasmo_analyses/blob/main/scripts/extract_techniques_from_pdfs.py)
**Taxonomy source:** `data/Techniques DB for Panel Review_UPDATED.xlsx` (sheet: Full_List)
**Documentation:**
- [Technique taxonomy database design](../database/technique_taxonomy_database_design.md) — Hierarchical taxonomy structure
- [Master techniques list](../techniques/master_techniques_list_for_population.md) — Full list of 129 core techniques across 8 disciplines
- [Technique classification schema proposal](../techniques/technique_classification_schema_proposal.md) — Schema design rationale
- [Technique expansion list](../techniques/technique_expansion_list.md) — Additional techniques added post-launch

---

### Observation basins (`ob_`) — 9 columns

Geographic study location data extracted via the geographic extraction pipeline (Phase 3–4, Nov 2025). The pipeline works in four phases: (1) extract author names and affiliations from PDF front matter using regex patterns; (2) match institution names to countries via a lookup table of ~5,700 known institutions; (3) extract study location mentions from the paper text and map them to ocean basins; (4) derive parachute research flags by comparing author country to study country. These are **text fields** containing structured location information, predating the binary `b_` keyword-based basin columns added later.

| Column | Label | Techniques | Notes |
|--------|-------|------------|-------|
| `ob_north_atlantic_ocean` | North Atlantic (text) | GEO | |
| `ob_south_atlantic_ocean` | South Atlantic (text) | GEO | |
| `ob_north_pacific_ocean` | North Pacific (text) | GEO | |
| `ob_south_pacific_ocean` | South Pacific (text) | GEO | |
| `ob_indian_ocean` | Indian Ocean (text) | GEO | |
| `ob_southern_ocean` | Southern Ocean (text) | GEO | |
| `ob_arctic_ocean` | Arctic Ocean (text) | GEO | |
| `ob_mediterranean_black_sea` | Mediterranean & Black Sea (text) | GEO | |
| `ob_baltic_sea` | Baltic Sea (text) | GEO | |

**Script:** Geographic extraction pipeline (`scripts/extract_study_locations_phase4*.py`)
**Storage:** Also in `database/technique_taxonomy.db` → `paper_geography` table
**Documentation:**
- [Quick start guide](../geographic/QUICK_START_GEOGRAPHIC_ANALYSIS.md) — Summary statistics and SQL queries
- [Complete geographic analysis](../geographic/GEOGRAPHIC_ANALYSIS_COMPLETE_SUMMARY_2025-11-24.md) — Full methodology and results
- [Phase 4 study location guide](../geographic/PHASE_4_STUDY_LOCATION_GUIDE.md) — Parachute research analysis
- [Database query reference](../geographic/DATABASE_QUERY_REFERENCE.md) — SQL examples for geographic data

---

### Species (`sp_`) — 1,308 columns

Each species is matched by its Latin binomial name as a single whole-word regex (`\bGenus species\b`). Binary presence/absence — unambiguous matches require no evidence table. The full taxonomic hierarchy (Class → Order → Family → Genus → Species) is available in the species database, enabling aggregation at any taxonomic level.

| Column(s) | Label | Keywords / method | Techniques | Notes |
|-----------|-------|-------------------|------------|-------|
| `sp_acroteriobatus_andysabini` ... `sp_zearaja_chilensis` (1,308 total) | Binomial species name | Single `\bGenus species\b` regex per species. | KM, SS | Column name format: `sp_<genus>_<species>`. 1,308 species from Shark-References (2025). |

**Species database:** [`data/shark_species_detailed_complete.csv`](../../data/shark_species_detailed_complete.csv) (2 MB) — includes full taxonomic hierarchy (Class, Order, Family, Genus, Species) and common names in 6+ languages. Also: [`data/shark_references_species_list.csv`](../../data/shark_references_species_list.csv) (162 KB, simplified list)
**Scripts:** `scripts/update_shark_references_species.py` (quarterly updates), `scripts/generate_species_sql.R`
**Documentation:**
- [Species database readme](../species/species_database_readme.md) — Quick reference and status
- [Species extraction methodology](../species/shark_references_species_database_extraction.md) — Full extraction methodology
- [Species update guide](../species/shark_references_update_script_readme.md) — Quarterly update procedure

---

### Ecosystem (`eco_`) — 20 binary columns + 3 derived

**Documentation:**
- [Ecosystem component proposal](ecosystem_component_proposal.md) — Column rationale and term selection
- [Extraction logic](extraction_logic.md) — Technical implementation details

#### Section weight profile

Different schema keywords are likely to occur in different paper sections, e.g. gear is described in the methods section, whereas fisheries impacts are discussed in the results and discussion.

| Schema | Meaning | Example column | Primary (×1.0) | Secondary (×0.5) | Low-value (×0.25) |
|--------|---------|----------------|---------------|-------------------|---------------------|
| `eco_` | Habitat / environment | `eco_reef` | Introduction, Methods | Abstract, Results, R&D, Discussion, Conclusions | Other |
| `pr_` | Threats and stressors | `pr_bycatch` | Introduction, Methods, Discussion, R&D | Abstract, Results, Conclusions | Other |
| `gear_` | Fishing gear and mitigation | `gear_trawl` | Methods | Abstract, Results, R&D | Introduction, Discussion, Conclusions, Other |
| `imp_` | Population / ecological impacts | `imp_abundance` | Results, Discussion, R&D | Abstract, Methods, Conclusions | Introduction, Other |
| `d_` | Research discipline | `d_genetics` | Methods, Results, R&D | Abstract, Introduction, Discussion, Conclusions | Other |
| `b_` | Study geography (ocean basin) | `b_mediterranean` | Introduction, Methods | Abstract, Results, R&D, Discussion, Conclusions | Other |

#### Binary columns

| Column | Label | Keywords | Threshold | Techniques | Known issues / notes |
|--------|-------|----------|-----------|------------|----------------------|
| `eco_marine` | Marine | marine, ocean, sea, saltwater | 3 | KFT, SW | Pre-threshold hit rate 83% → expected ~47% post-threshold. Generic term needs high threshold. |
| `eco_freshwater` | Freshwater | freshwater, freshwater river, river shark, river system, riverine, lake, estuarine, estuarin*, brackish | 3 | KFT, WC, SW | "river" removed (matched author surname "Rivera"). Now uses compounds only. |
| `eco_brackish` | Brackish / estuarine | estuar*, brackish, lagoon, mangrove | 2 | KFT, WC, SW | |
| `eco_pelagic` | Pelagic | pelagic, open ocean, oceanic, epipelagic, mesopelagic, bathypelagic | 2 | KFT, KPC, SW | "offshore" removed (AK: matched "30 m offshore"). Proximity check enabled. |
| `eco_coastal` | Coastal | coastal, neritic, inshore, nearshore, continental shelf | 3 | KFT, PH, SW | |
| `eco_demersal` | Demersal / benthic | demersal, benthic, bottom-dwelling, epibenthic, benthopelagic | 2 | KFT, SW | |
| `eco_reef` | Reef | coral reef, reef-associated, rocky reef | 1 | KFT, PH, SW | Specific terms — low threshold appropriate. |
| `eco_deepwater` | Deep water | deep-sea, deep-water, abyssal, hadal, bathyal, seamount | 2 | KFT, SW | |
| `eco_intertidal` | Intertidal | intertidal, tide pool, littoral | 1 | KFT, PH, SW | |
| `eco_mangrove` | Mangrove | mangrove | 2 | KFT, SW | |
| `eco_seagrass` | Seagrass | seagrass, eelgrass, Posidonia, Zostera, Thalassia | 1 | KFT, SW | Genus names are specific enough for threshold=1. |
| `eco_kelp` | Kelp | kelp forest, kelp bed, macroalgal | 1 | KFT, PH, SW | |
| `eco_polar` | Polar | polar, arctic, antarctic, ice-edge, sea ice | 2 | KFT, PH, SW | |
| `eco_riverine` | Riverine | river shark, freshwater stingray, bull shark river | 1 | KFT, PH, SW | Inherently elasmobranch-specific terms. |
| `eco_nursery` | Nursery habitat | nursery habitat, nursery ground, nursery area, essential fish habitat, juvenile habitat | 1 | KFT, PH, SW | |
| `eco_pupping` | Pupping ground | pupping ground, pupping area, parturition site, birthing ground | 1 | KFT, PH, SW | |
| `eco_epipelagic` | Epipelagic | epipelagic, surface waters, surface layer, photic zone | 2 | KFT, PH, SW | "surface" alone removed (AK: matched "surface area"). |
| `eco_mesopelagic` | Mesopelagic | mesopelagic, twilight zone | 1 | KFT, PH, SW | |
| `eco_bathypelagic` | Bathypelagic | bathypelagic, deep scattering layer | 1 | KFT, PH, SW | |
| `eco_abyssal` | Abyssal | abyssal, hadal | 1 | KFT, SW | |

#### Derived ecosystem columns

These columns pick a single best-guess label from the binary eco_ columns above. The logic iterates through the binary columns in a fixed priority order and selects the **first column with binary=1**. This means a paper flagged as both `eco_marine=1` and `eco_freshwater=1` will get `eco_1_guess = "marine"` because marine has higher priority. The priority ordering reflects how common each category is in the corpus (most common first), so the guess represents the most likely primary ecosystem when multiple apply.

| Column | Label | Techniques | Description | Notes |
|--------|-------|------------|-------------|-------|
| `eco_1_guess` | Realm guess | DRV | Best-guess realm from eco_ binaries. Priority order: marine → freshwater → brackish/estuarine. | |
| `eco_2_guess` | Zone guess | DRV | Best-guess zone from eco_ binaries. Priority order: pelagic → coastal → demersal/benthic → reef → deep-water → intertidal → mangrove → seagrass → kelp → polar → riverine → nursery → pupping. | |
| `eco_3_guess` | Depth zone guess | DRV | Best-guess depth zone from eco_ binaries. Priority order: epipelagic → mesopelagic → bathypelagic → abyssal. | |

---

### Pressure (`pr_`) — 26 columns

**Documentation:** [Pressure proposal](pressure_proposal.md) — Column rationale and term selection

| Column | Label | Keywords | Threshold | Techniques | Known issues / notes |
|--------|-------|----------|-----------|------------|----------------------|
| `pr_fishing_commercial` | Commercial fishing | commercial fish*, industrial fish*, fishing pressure, fishing mortality, exploitation | 3 | KFT, WC, PH, SW | Pre-threshold 29.5% → expected ~8.5% post-threshold. |
| `pr_fishing_artisanal` | Artisanal fishing | artisanal, small-scale fish*, subsistence fish*, traditional fish* | 2 | KFT, WC, PH, SW | |
| `pr_fishing_recreational` | Recreational fishing | recreational fish*, sport fish*, game fish*, catch-and-release, angling, angler, anglers | 2 | KFT, WC, PH, SW | "angl*" replaced with exact matches (AK: matched "angle", "angular"). |
| `pr_fishing_iuu` | IUU fishing | illegal fish*, unreported, unregulated, IUU, poach* | 2 | KFT, WC, AC, SW | IUU case-sensitive. |
| `pr_bycatch` | Bycatch | bycatch, by-catch, incidental capture, non-target, discards | 2 | KFT, PH, SW | |
| `pr_shark_finning` | Shark finning | shark fin*, finning, fin trade | 1 | KFT, WC, PH, SW | Inherently specific. |
| `pr_targeted_fishing` | Targeted shark fishing | targeted shark fish*, directed shark fish*, shark fish* | 2 | KFT, WC, PH, SW | |
| `pr_climate_change` | Climate change | climate change, global warming, ocean warming | 3 | KFT, PH, SW | CM issue: often mentioned as background driver, not study focus. High threshold helps. |
| `pr_ocean_acidification` | Ocean acidification | ocean acidification, (acidification AND pH), (acidification AND pCO2) | 1 | KFT, PH, AND, SW | AND logic: "acidification" alone insufficient; needs "pH" or "pCO2" co-occurrence. |
| `pr_hypoxia` | Hypoxia | hypoxia, deoxygenation, oxygen minimum zone, OMZ | 1 | KFT, PH, AC, SW | OMZ case-sensitive. |
| `pr_pollution_chemical` | Chemical pollution | pollut*, contaminant*, heavy metal*, mercury, PCB, PFAS, pesticide* | 3 | KFT, WC, AC, SW | PCB, PFAS case-sensitive. High threshold — common in reference titles (RB). |
| `pr_pollution_plastic` | Plastic pollution | plastic pollution, microplastic*, macroplastic*, plastic ingestion, plastic debris | 1 | KFT, WC, PH, SW | |
| `pr_pollution_noise` | Noise pollution | noise pollution, anthropogenic noise, shipping noise, sonar, acoustic disturbance | 1 | KFT, PH, SW | "sonar" can match non-pollution contexts (RB: reference about tube-worm mapping). |
| `pr_habitat_loss` | Habitat loss | habitat loss, habitat degradation, coastal development, dredg*, mangrove loss | 2 | KFT, WC, PH, SW | |
| `pr_shipping` | Shipping | ship strike, vessel strike, maritime traffic | 1 | KFT, PH, SW | |
| `pr_tourism` | Tourism | dive tourism, ecotourism, shark tourism, provisioning, shark feed*, cage div* | 1 | KFT, WC, PH, SW | |
| `pr_depredation` | Depredation | depredation, depredating, bait loss, catch damage | 1 | KFT, PH, SW | |
| `pr_aquaculture` | Aquaculture | aquaculture, fish farm*, mariculture | 1 | KFT, WC, SW | |
| `pr_invasive` | Invasive species | invasive species, non-native species, alien species | 1 | KFT, PH, SW | |
| `pr_disease` | Disease | disease, pathogen, parasite, epizootic, infection | 3 | KFT, SW | Parasitology papers correctly trigger this — not a false positive. |
| `pr_light` | Light pollution | light pollution, artificial light, ALAN | 1 | KFT, PH, AC, SW | ALAN case-sensitive. |
| `pr_electromagnetic` | Electromagnetic | electromagnetic field, EMF, submarine cable, electroreception interference | 1 | KFT, PH, AC, SW | EMF case-sensitive. |
| `pr_cumulative` | Cumulative impacts | cumulative impact, multiple stressor*, synergistic, additive effect | 2 | KFT, WC, PH, SW | |
| `pr_discarding` | Discarding | discard*, discarding practice*, high-grading, slipping | 2 | KFT, WC, PH, SW | Added 2026-03-16. |
| `pr_seabed_disturbance` | Seabed disturbance | seabed disturbance, bottom disturbance, benthic disturbance, physical disturbance of the seabed, sediment resuspension, trawl impact on seabed, habitat scraping | 1 | KFT, PH, SW | Added 2026-03-16. |
| `pr_visual_disturbance` | Visual disturbance | visual disturbance, vessel presence, diver disturbance, boat disturbance, swimmer disturbance, shadow effect | 1 | KFT, PH, SW | Added 2026-03-16. |

---

### Gear (`gear_`) — 28 binary columns + 1 extracted

**Documentation:** [Gear proposal](gear_proposal.md) — Column rationale, BMIS mitigation techniques

#### Binary columns

| Column | Label | Keywords | Threshold | Techniques | Known issues / notes |
|--------|-------|----------|-----------|------------|----------------------|
| `gear_longline` | Longline | longline, long-line, pelagic longline, demersal longline, bottom longline | 2 | KFT, PH, SW | CM: "longline" as ghost gear substrate (not study focus). |
| `gear_gillnet` | Gillnet | gillnet, gill net, trammel net, entangling net, drift net, driftnet | 2 | KFT, PH, SW | |
| `gear_trawl` | Trawl | trawl, bottom trawl, demersal trawl, pelagic trawl, otter trawl, beam trawl, shrimp trawl | 2 | KFT, PH, SW | |
| `gear_purse_seine` | Purse seine | purse seine, purse-seine, ring net | 1 | KFT, PH, SW | |
| `gear_seine` | Seine (other) | beach seine, Danish seine, seine net | 1 | KFT, PH, SW | |
| `gear_hook_line` | Hook and line | hook and line, handline, rod and reel, trolling, jigging, pole and line | 2 | KFT, PH, SW | |
| `gear_trap` | Trap / pot | trap, pot, fish trap, drumline, SMART drumline | 2 | KFT, PH, SW | "trap" is generic — threshold=2 helps. |
| `gear_net_other` | Other nets | cast net, lift net, scoop net, fyke net, pound net, weir | 1 | KFT, PH, SW | |
| `gear_harpoon` | Harpoon | harpoon, spearfish*, spear gun | 1 | KFT, WC, PH, SW | |
| `gear_dredge` | Dredge | dredge, towed dredge, scallop dredge, clam dredge, oyster dredge, hydraulic dredge | 1 | KFT, PH, SW | Added 2026-03-16. |
| `gear_trawl_beam` | Beam trawl | beam trawl, beam-trawl | 1 | KFT, PH, SW | Added 2026-03-16. |
| `gear_trawl_otter` | Otter trawl | otter trawl, otter-trawl | 1 | KFT, PH, SW | Added 2026-03-16. |
| `gear_survey` | Survey gear | research vessel, survey trawl, BRUVs, longline survey, fishery-independent survey, drone survey, UAV survey, ROV, submersible, diving survey, diver transect | 2 | KFT, PH, AC, SW | BRUVs, UAV, ROV case-sensitive. |
| `gear_pelagic` | Pelagic gear | pelagic longline, pelagic trawl, midwater trawl | 1 | KFT, PH, SW | |
| `gear_demersal` | Demersal gear | demersal longline, bottom trawl, demersal trawl, bottom longline | 1 | KFT, PH, SW | |
| `gear_artisanal` | Artisanal gear | artisanal, traditional gear, small-scale, hand-operated | 2 | KFT, PH, SW | |
| `gear_mit_circle_hook` | Mitigation: circle hooks | circle hook, non-offset hook | 1 | KFT, PH, SW | |
| `gear_mit_brd` | Mitigation: BRD / TED | bycatch reduction device, BRD, turtle excluder, TED | 1 | KFT, PH, AC, SW | BRD, TED case-sensitive. |
| `gear_mit_deterrent` | Mitigation: deterrents | shark deterrent, SharkGuard, shark guard, electropositive, Rare Earth, EPM, LED deterrent, magnetic deterrent | 1 | KFT, PH, AC, SW | EPM case-sensitive. |
| `gear_mit_time_area` | Mitigation: time-area closure | time-area closure, spatial closure, fishing closure, seasonal closure, MPA | 2 | KFT, PH, AC, SW | MPA case-sensitive. Previously matched institutional addresses. |
| `gear_mit_handling` | Mitigation: handling | safe release, handling practice*, live release, post-release mortality, PRM | 1 | KFT, WC, PH, AC, SW | PRM case-sensitive. |
| `gear_mit_weak_hook` | Mitigation: weak hooks | weak hook, corrodible hook, designed to straighten | 1 | KFT, PH, SW | Added 2026-03-16 (BMIS). |
| `gear_mit_line_weight` | Mitigation: line weighting | line weight*, weighted branchline, leaded swivel, sliding lead, lumo lead, sink rate | 1 | KFT, WC, PH, SW | Added 2026-03-16 (BMIS). |
| `gear_mit_setting` | Mitigation: setting practices | night set*, deep set*, deep-set buoy gear, side-set*, underwater set* | 1 | KFT, WC, PH, SW | Added 2026-03-16 (BMIS). |
| `gear_mit_pinger` | Mitigation: pingers | pinger, acoustic alarm, acoustic deterrent, porpoise alerting device, PAL | 1 | KFT, PH, AC, SW | PAL case-sensitive. Added 2026-03-16 (BMIS). |
| `gear_mit_illumination` | Mitigation: net illumination | illuminat* net, illuminat* gillnet, LED net, net light*, lightstick*, light attract* | 1 | KFT, WC, PH, SW | Added 2026-03-16 (BMIS). |
| `gear_mit_wire_leader` | Mitigation: wire leaders | wire leader, monofilament leader, wire trace, nylon leader | 1 | KFT, PH, SW | Added 2026-03-16 (BMIS). |
| `gear_mit_ghost` | Mitigation: ghost gear | ghost gear, ghost net, ALDFG, abandoned gear, lost gear, derelict gear, derelict fishing | 1 | KFT, PH, AC, SW | ALDFG case-sensitive. Added 2026-03-16 (BMIS). |

#### Extracted gear metadata

| Column | Label | Techniques | Description | Notes |
|--------|-------|------------|-------------|-------|
| `gear_target_species` | Target species | RE | Regex extracts species/group names from gear-related phrases: "{word} fishery", "{word} longline", "{word} trawl", "directed at {word}". Returns comma-separated species names (e.g. "tuna, swordfish") or null. | |

---

### Impact (`imp_`) — 21 binary columns + 4 derived/extracted

**Documentation:** [Impact proposal](impact_proposal.md) — Column rationale, anchor term design, direction/quantification metadata

#### Binary columns

| Column | Label | Keywords | Threshold | Anchors | Techniques | Known issues / notes |
|--------|-------|----------|-----------|---------|------------|----------------------|
| `imp_mortality` | Mortality | mortality, survival rate, lethality, dead on arrival, DOA, at-vessel mortality, AVM | 2 | — | KFT, PH, AC, KPC, SW | DOA, AVM case-sensitive. Proximity check enabled. |
| `imp_post_release` | Post-release mortality | post-release mortality, PRM, delayed mortality, post-capture survival | 1 | — | KFT, PH, AC, KPC, SW | PRM case-sensitive. Proximity check enabled. CM: sometimes mentioned as importance statement only. |
| `imp_abundance` | Abundance | abundance, population size, population decline, population trend | 2 | population, decline, increase, change, trend, status | KFT, PH, ANC, KPC, SW | Classic ambiguous term. Anchors + proximity check both required. CM: "abundance" in invertebrate context. |
| `imp_cpue` | CPUE | CPUE, catch per unit effort, catch rate | 1 | — | KFT, PH, AC, SW | CPUE case-sensitive. |
| `imp_biomass` | Biomass | biomass, standing stock, spawning stock biomass, SSB | 2 | — | KFT, PH, AC, KPC, SW | SSB case-sensitive. Proximity check enabled. CM: "biomass" as predictor variable, not outcome. |
| `imp_distribution` | Distribution shift | distribution shift, range shift, range contraction, habitat shift | 1 | — | KFT, PH, SW | Specific phrases — low threshold appropriate. |
| `imp_behaviour_change` | Behavioural change | behavioural change, behavioral change, avoidance behaviour, flight response, habituation | 2 | change, response | KFT, PH, ANC, KPC, SW | Proximity check enabled. |
| `imp_physiology_stress` | Physiological stress | cortisol, lactate, blood chemistry, acid-base, reflex impairment, RAMP, physiological stress | 1 | — | KFT, PH, AC, SW | RAMP case-sensitive (AC: "boat ramp"). |
| `imp_injury` | Injury | injury, hooking injury, scarring, body condition index, entanglement, entangled, gear interaction, net mark* | 2 | — | KFT, WC, PH, KPC, SW | Proximity check enabled. |
| `imp_reproduction` | Reproductive impact | reproductive output, fecundity change, reproductive failure | 1 | — | KFT, PH, SW | |
| `imp_growth` | Growth | growth rate, von Bertalanffy, growth curve, somatic growth, condition factor, Fulton, length-weight, stunting, growth overfishing | 2 | change, impact, decline, reduce, affect, alter, slow, decrease, increase | KFT, PH, ANC, SW | |
| `imp_genetic` | Genetic impact | genetic diversity, effective population size, Ne\b, bottleneck, inbreeding | 2 | — | KFT, PH, RX, SW | `Ne\b` is raw regex, case-sensitive. |
| `imp_trophic` | Trophic impact | trophic level change, dietary shift, prey depletion, mesopredator release | 1 | — | KFT, PH, SW | |
| `imp_habitat_quality` | Habitat quality | habitat quality, habitat suitability, degradation index | 2 | — | KFT, PH, SW | |
| `imp_contamination` | Contamination | contaminant load, bioaccumulation, biomagnification, tissue concentration | 1 | — | KFT, PH, SW | |
| `imp_economic` | Economic impact | economic value, fishery value, tourism revenue, willingness to pay, WTP | 1 | — | KFT, PH, AC, KPC, SW | WTP case-sensitive. Proximity check enabled. CM: economic value as justification, not study topic. |
| `imp_social` | Social impact | livelihood, food security, human dimension, attitude, perception | 3 | — | KFT, SW | High threshold — generic terms. |
| `imp_community_composition` | Community composition | community composition, assemblage composition, species composition, community structure change, assemblage shift | 2 | change, shift, impact, alter* | KFT, PH, ANC, WC, SW | Added 2026-03-16. |
| `imp_biodiversity` | Biodiversity | biodiversity loss, species richness change, diversity index, Shannon, Simpson, evenness change, species loss | 2 | change, loss, decline, impact | KFT, PH, ANC, SW | Added 2026-03-16. |
| `imp_size_structure` | Size structure | size structure, length frequency, age structure, size composition, size distribution, mean length, maximum length, length at maturity shift, truncated size | 2 | change, shift, impact, decline, truncat* | KFT, PH, ANC, WC, SW | Added 2026-03-16. |
| `imp_productivity` | Productivity | productivity, recruitment, yield per recruit, spawning potential ratio, SPR, surplus production, reproductive output | 2 | change, decline, impact, reduce, increase, affect, fishing, overfishing | KFT, PH, ANC, AC, SW | SPR case-sensitive. Added 2026-03-16. |

#### Derived/extracted impact metadata

| Column | Label | Techniques | Description | Notes |
|--------|-------|------------|-------------|-------|
| `imp_direction` | Impact direction | SA | Sentiment classification from positive/negative cue words. Returns: "negative", "positive", "mixed", or "not stated". | |
| `imp_quantified` | Impact quantified | RE | Boolean: whether paper provides quantitative measures (percentages, p-values, confidence intervals, ± values). | |
| `imp_confidence` | Impact confidence | DRV | JSON object with per-column confidence scores (e.g. `{"imp_abundance": 3}`). | |
| `imp_is_bycatch` | Bycatch inference | DRV | Inferred from `pr_bycatch` + `gear_target_species`: True if bycatch=1 AND target species is non-elasmobranch (e.g. "tuna fishery"); None if ambiguous; False if no bycatch signal. | |

---

### Discipline (`d_`) — 19 columns

| Column | Label | Keywords | Threshold | Techniques | Known issues / notes |
|--------|-------|----------|-----------|------------|----------------------|
| `d_biology` | Life history / biology | life history, age and growth, growth rate, longevity, maturity, length-at-maturity, length-weight, vertebral band | 2 | KFT, PH, KPC, SW | Proximity check enabled. CM: "slow growth, late maturity" boilerplate in introductions. |
| `d_behaviour` | Behaviour | behavio*, behavioral ecology, predator-prey, diel vertical migration, activity pattern, social behavio*, agonistic, refuging | 3 | KFT, WC, PH, KPC, SW | Proximity check enabled. CM: "behavio*" matched skipper behaviour. High threshold. |
| `d_trophic` | Trophic ecology | trophic, diet, feeding ecology, stomach content*, prey composition, stable isotope, fatty acid, food web | 2 | KFT, WC, PH, KPC, SW | Proximity check enabled. |
| `d_genetics` | Genetics / genomics | genetic*, genomic*, eDNA, environmental DNA, microsatellite, mitochondrial, phylogenet*, haplotype, SNP, RADseq, population genetics | 2 | KFT, WC, PH, AC, SW | eDNA, SNP case-sensitive. CM: "phylogenet*" as justification context. |
| `d_movement` | Movement / telemetry | movement, telemetry, satellite tag*, acoustic tag*, archival tag*, home range, migration, habitat use, space use, tracking | 3 | KFT, WC, PH, KPC, SW | Proximity check enabled. CM: "movement" matched embryo movement in egg cases. High threshold. |
| `d_fisheries` | Fisheries science | stock assessment, fisheries management, catch data, fishing mortality, maximum sustainable yield, MSY, fishery-dependent, fishery-independent | 2 | KFT, PH, AC, KPC, SW | MSY case-sensitive. Proximity check enabled. |
| `d_conservation` | Conservation | conservation, endangered, CITES, IUCN, Red List, protected area, marine protected area, recovery plan, conservation status | 3 | KFT, PH, AC, SW | CITES, IUCN case-sensitive. High threshold — "conservation" appears widely. |
| `d_data_science` | Data science / modelling | machine learning, deep learning, neural network, random forest, Bayesian, meta-analysis, systematic review, simulation model | 2 | KFT, PH, KPC, SW | Proximity check enabled. CM: "Bayesian" cited in passing. |
| `d_husbandry` | Husbandry / captive | aquarium, captive, husbandry, captive breeding, ex situ, tank-held, aquaria | 2 | KFT, PH, KPC, SW | Proximity check enabled. Hit rate 4.9% — spot-check flagged. RB: "aquarium" in reference titles. |
| `d_paleontology` | Palaeontology | fossil, paleontol*, palaeontol*, Cretaceous, Jurassic, Miocene, Pliocene, Eocene, Oligocene, Cenozoic, Mesozoic, Devonian, Carboniferous | 1 | KFT, WC, SW | Hit rate 9.6% — spot-check flagged. Geological period names are specific. |
| `d_taxonomy` | Taxonomy | taxonom*, new species, sp. nov., new genus, morphometric*, meristic*, dichotomous key, identification key, redescription, synonymy, type specimen | 1 | KFT, WC, PH, KPC, SW | Proximity check enabled. Hit rate 22.1% — spot-check flagged. CM: "taxonom*" as context in reviews. |
| `d_physiology` | Physiology | physiolog*, metaboli*, oxygen consumption, ventilation rate, blood gas, haematocrit, hematocrit, osmoregulat*, thermoregulat*, bioenergetic* | 2 | KFT, WC, PH, SW | CM: physiological responses cited from bibliography, not measured. |
| `d_reproductive` | Reproductive biology | reproductive biology, fecundity, gestation, embryo*, uterine, ovipar*, vivipar*, mating, parturition, neonat*, litter size, reproductive cycle | 2 | KFT, WC, PH, SW | |
| `d_biomechanics` | Biomechanics | biomechani*, functional morphology, locomot*, kinematics, bite force, jaw mechanics, hydrodynamic*, swimming performance | 1 | KFT, WC, PH, SW | SM: "hydrodynamic*" matched embayment hydrodynamics. |
| `d_sensory` | Sensory biology | electrorecept*, ampullae of Lorenzini, lateral line, mechanosens*, olfact*, chemosens*, visual acuity, magnetorecept* | 1 | KFT, WC, PH, SW | Inherently elasmobranch-specific (ampullae of Lorenzini). No proximity check needed. |
| `d_ecotourism` | Ecotourism | ecotourism, dive tourism, shark tourism, shark watching, whale shark tourism, shark encounter, provisioning | 1 | KFT, PH, SW | |
| `d_human_dimensions` | Human dimensions | human dimension*, social science, stakeholder, perception, attitude*, willingness to pay, WTP, shark bite, shark attack, shark repellent | 2 | KFT, WC, PH, AC, SW | WTP case-sensitive. |
| `d_immunology` | Immunology | immun*, antibod*, complement system, innate immun*, adaptive immun*, leukocyte, lymphocyte | 2 | KFT, WC, PH, SW | |
| `d_toxicology` | Toxicology | toxicolog*, contaminant*, bioaccumulation, biomagnification, heavy metal*, mercury, methylmercury, tissue concentration | 2 | KFT, WC, PH, SW | |

---

### Ocean basin (`b_`) — 9 columns

| Column | Label | Keywords | Threshold | Techniques | Known issues / notes |
|--------|-------|----------|-----------|------------|----------------------|
| `b_north_atlantic` | North Atlantic | North Atlantic, Northwest Atlantic, Northeast Atlantic, NW Atlantic, NE Atlantic, North Sea, Bay of Biscay, Celtic Sea, Norwegian Sea, Barents Sea, Baltic Sea, Gulf of Mexico, Sargasso Sea, Azores | 2 | KFT, PH, SW | RB: geographic terms in reference titles. |
| `b_south_atlantic` | South Atlantic | South Atlantic, Southwest Atlantic, Southeast Atlantic, SW Atlantic, SE Atlantic, Benguela, Patagoni*, South Africa*, Namibia*, Brazilian coast | 2 | KFT, WC, PH, SW | |
| `b_north_pacific` | North Pacific | North Pacific, Northwest Pacific, Northeast Pacific, NW Pacific, NE Pacific, Bering Sea, Sea of Japan, East China Sea, South China Sea, Yellow Sea, California Current, Kuroshio, Sea of Okhotsk, Gulf of Alaska, Hawaiian | 2 | KFT, PH, SW | |
| `b_south_pacific` | South Pacific | South Pacific, Southwest Pacific, Southeast Pacific, SW Pacific, SE Pacific, Coral Sea, Tasman Sea, Great Barrier Reef, New Zealand*, Fiji*, French Polynesia, Humboldt Current | 2 | KFT, WC, PH, SW | |
| `b_indian_ocean` | Indian Ocean | Indian Ocean, Bay of Bengal, Arabian Sea, Mozambique Channel, Red Sea, Persian Gulf, Andaman Sea, Madagascar, Maldives, Seychelles, Western Indian Ocean, Eastern Indian Ocean | 2 | KFT, PH, SW | |
| `b_southern_ocean` | Southern Ocean | Southern Ocean, Antarctic, sub-Antarctic, Kerguelen, South Georgia, Patagonian shelf | 1 | KFT, PH, SW | Lower threshold — specific terms. |
| `b_arctic_ocean` | Arctic Ocean | Arctic Ocean, Arctic, Greenland Sea, Beaufort Sea, Chukchi Sea, Canadian Arctic | 2 | KFT, PH, SW | |
| `b_mediterranean` | Mediterranean | Mediterranean, Adriatic, Aegean, Tyrrhenian, Ionian Sea, Ligurian Sea, Alboran Sea, Strait of Gibraltar, Strait of Sicily | 1 | KFT, PH, SW | Lower threshold — sub-basin names are specific. |
| `b_caribbean` | Caribbean | Caribbean, Gulf of Mexico, Bahamas, Belize, Mesoamerican Reef, Antilles, West Indies | 2 | KFT, PH, SW | Note: Gulf of Mexico appears in both b_north_atlantic and b_caribbean. |

---

### Depth extraction — 3 columns

| Column | Label | Techniques | Description | Notes |
|--------|-------|------------|-------------|-------|
| `depth_range` | Depth range (text) | RE | Text representation of depth range extracted from paper (e.g. "0–200 m", "depths of 150 m to 300 m"). | |
| `depth_min_m` | Depth minimum (m) | RE | Minimum depth in metres (float), parsed from depth range patterns. | |
| `depth_max_m` | Depth maximum (m) | RE | Maximum depth in metres (float), parsed from depth range patterns. | |

**Regex patterns matched:** Range ("0–200 m", "depths of 150 m to 300 m"), single value ("depth of 500 m"), comparative (">200 m", "≥200 m").

---

### Author enrichment (OpenAlex) — [`openalex_paper_authors.csv`](../../outputs/openalex_paper_authors.csv), [`openalex_unique_authors.csv`](../../outputs/openalex_unique_authors.csv)

**Lookup key:** DOI → [OpenAlex API](https://docs.openalex.org/) (batch queries, 50 DOIs per request)
**Script:** [`scripts/enrich_authors_openalex.py`](https://github.com/SimonDedman/elasmo_analyses/blob/main/scripts/enrich_authors_openalex.py)
**Output files:**
- [`outputs/openalex_paper_authors.csv`](../../outputs/openalex_paper_authors.csv) (11 MB, one row per author per paper)
- [`outputs/openalex_unique_authors.csv`](../../outputs/openalex_unique_authors.csv) (3 MB, deduplicated by OpenAlex author ID)
**Gender inference:** [`scripts/infer_author_gender.py`](https://github.com/SimonDedman/elasmo_analyses/blob/main/scripts/infer_author_gender.py) (offline gender-guesser) + [`scripts/genderize_daily.py`](https://github.com/SimonDedman/elasmo_analyses/blob/main/scripts/genderize_daily.py) (daily cron via [Genderize.io](https://genderize.io/) API, 1,000 names/day free tier). Results written back to both author CSVs above.

| Field | Label | Techniques | Description | Notes |
|-------|-------|------------|-------------|-------|
| `author_position` | Author position | API | "first", "middle", "last" | |
| `display_name` | Display name | API | Author name as recorded in OpenAlex | |
| `first_name` | First name | API | Parsed first name (used for gender inference) | |
| `last_name` | Last name | API | Parsed surname | |
| `openalex_author_id` | OpenAlex ID | API | Unique author identifier (e.g. "https://openalex.org/A5023888391") | |
| `institution_name` | Institution | API | Primary institutional affiliation | |
| `institution_country` | Institution country | API | ISO country code | |
| `institution_type` | Institution type | API | "education", "healthcare", "government", etc. | |
| `gender` | Inferred gender | GI | "male", "female", or "unknown". Inferred by [`infer_author_gender.py`](https://github.com/SimonDedman/elasmo_analyses/blob/main/scripts/infer_author_gender.py) using offline gender-guesser library, with daily [Genderize.io](https://genderize.io/) API fallback (1,000 names/day free tier). Results written back to both author CSVs above. | |
| `paper_count` | Paper count | DRV | Number of papers in corpus by this author (unique authors CSV only) | |

---

### Altmetric social attention — [`altmetric_scores.csv`](../../outputs/altmetric_scores.csv)

**Lookup key:** DOI → [Altmetric Details Page API](https://www.altmetric.com/products/altmetric-api/)
**Script:** [`scripts/enrich_altmetric.py`](https://github.com/SimonDedman/elasmo_analyses/blob/main/scripts/enrich_altmetric.py)
**Output:** [`outputs/altmetric_scores.csv`](../../outputs/altmetric_scores.csv) (880 KB, one row per paper; 10,897 papers, 65.5% hit rate)

| Field | Label | Techniques | Description | Notes |
|-------|-------|------------|-------------|-------|
| `altmetric_id` | Altmetric ID | API | Altmetric-assigned identifier | |
| `alt_score` | Attention score | API | Altmetric Attention Score (weighted composite) | |
| `alt_tweeters` | Twitter users | API | Unique Twitter/X users mentioning the paper | |
| `alt_posts` | Twitter posts | API | Total Twitter/X mentions | |
| `alt_fbwalls` | Facebook posts | API | Facebook wall posts | |
| `alt_blogs` | Blog mentions | API | Blog post mentions | |
| `alt_news` | News mentions | API | News outlet mentions | |
| `alt_policy` | Policy citations | API | Policy document citations | |
| `alt_wikipedia` | Wikipedia mentions | API | Wikipedia page citations | |
| `alt_reddit` | Reddit mentions | API | Reddit post/comment mentions | |
| `alt_peer_review` | Peer review mentions | API | Peer review site mentions | |
| `alt_mendeley` | Mendeley readers | API | Mendeley bookmark count | |
| `alt_pct_journal` | Journal percentile | API | Percentile rank within the same journal | |
| `alt_pct_all` | Overall percentile | API | Percentile rank across all research outputs | |
| `alt_pct_similar_age` | Age-cohort percentile | API | Percentile rank among papers of similar age (3-month window) | |

---

### Open access status (Unpaywall) — [`unpaywall_oa_by_doi.csv`](../../outputs/unpaywall_oa_by_doi.csv)

**Lookup key:** DOI → [Unpaywall API](https://unpaywall.org/products/api)
**Script:** [`scripts/lookup_unpaywall_oa.py`](https://github.com/SimonDedman/elasmo_analyses/blob/main/scripts/lookup_unpaywall_oa.py)
**Output:** [`outputs/unpaywall_oa_by_doi.csv`](../../outputs/unpaywall_oa_by_doi.csv) (3.1 MB, one row per paper)

| Field | Label | Techniques | Description | Notes |
|-------|-------|------------|-------------|-------|
| `oa_status` | OA status | API | "gold", "green", "hybrid", "bronze", "closed", "unknown" | |
| `oa_is_oa` | Is open access | API | Boolean: is the paper freely available? | |
| `oa_url` | Best OA URL | API | URL of best available open access copy | |
| `oa_journal_is_oa` | Journal is OA | API | Boolean: is the journal fully open access? | |
| `oa_journal_is_in_doaj` | In DOAJ | API | Boolean: is the journal in the Directory of Open Access Journals? | |
| `oa_host_type` | Host type | API | "publisher" or "repository" | |
| `oa_license` | Licence | API | Creative Commons or other licence (e.g. "cc-by") | |
| `oa_version` | Version | API | "publishedVersion", "acceptedVersion", "submittedVersion" | |

---

### Journal quality (Scimago) — [`scimago_match.csv`](../../data/journal_quality/scimago_match.csv)

**Lookup key:** journal name → [Scimago Journal Rank](https://www.scimagojr.com/) database (fuzzy matching)
**Script:** [`scripts/lookup_scimago_journals.py`](https://github.com/SimonDedman/elasmo_analyses/blob/main/scripts/lookup_scimago_journals.py)
**Output:** [`data/journal_quality/scimago_match.csv`](../../data/journal_quality/scimago_match.csv) + 4 additional CSVs (unmatched, book chapters, theses, grey literature)

| Field | Label | Techniques | Description | Notes |
|-------|-------|------------|-------------|-------|
| `scimago_title` | Scimago title | API | Official Scimago journal title | |
| `sjr_score` | SJR score | API | Scimago Journal Rank impact metric | |
| `quartile` | Quartile | API | Q1/Q2/Q3/Q4 journal ranking | |
| `h_index` | h-index | API | Journal h-index (citation impact) | |
| `subject_areas` | Subject areas | API | Primary research domains | |
| `open_access` | OA (Scimago) | API | "yes"/"no"/"partial" | |
| `match_type` | Match type | DRV | "exact", "alias", "substring", "fuzz" | |
| `match_score` | Match score | DRV | Fuzzy matching confidence (0–1) | |

---

### Geographic extraction — database table

**Source:** Geographic extraction pipeline (Phase 3–4, Nov 2025)
**Scripts:** `scripts/extract_study_locations_phase4*.py` and related
**Storage:** `database/technique_taxonomy.db` → `paper_geography` table (6,183 papers)

| Field | Label | Techniques | Description | Notes |
|-------|-------|------------|-------------|-------|
| `first_author_institution` | Author institution | GEO | Parsed from PDF front matter | |
| `first_author_country` | Author country | GEO | Derived from institution name | |
| `first_author_region` | Author region | GEO | Global North / Global South classification | |
| `study_country` | Study country | GEO | Country where research was conducted | |
| `study_ocean_basin` | Study basin | GEO | Ocean basin of study site | |
| `study_latitude` | Study latitude | GEO | Latitude of study site (float) | |
| `study_longitude` | Study longitude | GEO | Longitude of study site (float) | |
| `study_location_text` | Study location (text) | GEO | Raw extracted location string | |
| `is_parachute_research` | Parachute research | DRV | True when author country ≠ study country (flags potential parachute science) | |

---

## Part 3: Validation Accuracy

*To be populated as validation proceeds. See [GitHub #1](https://github.com/SimonDedman/elasmo_analyses/issues/1) for validation plan.*

### Validation sources

| Source | Status | Coverage | Notes |
|--------|--------|----------|-------|
| 200-paper dry run (pre-threshold) | Complete — hit rates in [extraction_logic.md](extraction_logic.md#initial-validation-results) | All schemas, simple binary (no SW/KPC) | Pre-dates frequency thresholds, SW, KPC fixes |
| Elena F. Corr Mediterranean trophic review | Pending | d_trophic, b_mediterranean | |
| David Schiffman AES coded dataset | Pending — dataset requested | 22 Schiffman categories → d_ columns | |
| Alex McInturf / Sophia Pelletier / Deven Guerrero shark social aggregation review | Pending — expressed interest | d_behaviour, specific social behaviour | |
| Chris Mull species/habitats | Pending — expressed interest | sp_ (species), eco_ (ecosystem/habitat) | |
| David R-G Mediterranean fisheries bibliography | Pending | gear_, pr_, b_mediterranean | |
| Coauthor evidence review (XLSX) | David R-G rows 2–141 complete | 40+ issues identified → fixes implemented | |

### Per-column metrics (template)

Once spot-checks and cross-validation are complete, populate this table:

| Column | N validated | True pos | False pos | False neg | Precision | Recall | F1 | Notes |
|--------|------------|----------|-----------|-----------|-----------|--------|----|-------|
| *example* | *50* | *42* | *3* | *5* | *0.93* | *0.89* | *0.91* | *—* |

### Technique effectiveness analysis

With per-column validation metrics and the technique codes from Part 1, we can regress validation accuracy against which techniques are applied to each column. This would identify which techniques contribute most to precision and recall, and where adding techniques (e.g. extending KPC to more columns, or adding ANC to discipline columns) would yield the greatest improvement.

---

## Discussion Points for Team Review

1. **Citation stripping (proposed CS technique):** Inline citations like "(Pelagic et al., 2026)" are currently scanned by keyword matching. Should we strip these before matching? Risk: low frequency of surname-keyword collisions. Benefit: eliminates an entire class of false positive.

2. **Length normalisation (proposed LN technique):** Should frequency thresholds scale with paper length? [David R-G raised this in #7](https://github.com/SimonDedman/elasmo_analyses/issues/7). Counter-argument: genuinely relevant papers should meet absolute thresholds regardless of length.

3. **Extending keyword proximity check (KPC):** Currently uses elasmobranch vocabulary only. Could be generalised with different anchor sets for different schemas (e.g. fishing vocabulary for gear_ columns).

4. **Extending context anchors (ANC):** Currently only on 9 imp_ columns. Could `d_physiology` benefit from anchors like "measured", "sampled", "experiment"? Could `d_data_science` require "applied", "fitted", "trained"?

5. **Threshold sensitivity:** The evidence table records `total_freq` and `threshold` for every match. A systematic sensitivity analysis (varying thresholds and measuring agreement with manual validation) would inform optimal thresholds.

6. **eco_marine removal:** [GitHub #7 comment](https://github.com/SimonDedman/elasmo_analyses/issues/7) — `eco_marine` is uninformative (83% hit rate in an elasmobranch corpus). Should it be dropped or retained as a sanity check?

7. **Gulf of Mexico duplication:** Appears in both `b_north_atlantic` and `b_caribbean`. Intentional (geographic overlap) or should it be exclusive to one?
