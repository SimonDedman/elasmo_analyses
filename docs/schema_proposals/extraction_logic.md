# Schema Extraction Logic

*Technical documentation for `scripts/extract_schema_columns.py`*

*Last updated: 2026-04-21*

---

## Synthetic-section pollution fix (added 2026-04-21)

The 2026-04-20 TITLE/KEYWORDS injection (see below) had a subtle defect. After prepending `TITLE\n<title>\n\n` and `KEYWORDS\n<block>\n\n`, `_label_sections()` scans line-by-line for section-header matches. Every line between the injected header and the *next* recognised header stays attached to the injected label. For papers whose body text does not hit a detected header promptly (e.g. where Abstract is not on a line by itself, so `_ABSTRACT_RE` fails), TITLE ended up absorbing all of the author and affiliation text at weight 2.0. Paper 27537 (McInturf 2019) fired `d_conservation` with weighted score 6.0 purely from the phrase "Department of Wildlife, Fish and Conservation Biology" in the author-affiliation footnote.

Three coordinated changes close this hole:

1. **OTHER terminator injection.** TITLE and KEYWORDS injections now write `TITLE\n<title>\nOTHER\n\n` and `KEYWORDS\n<block>\nOTHER\n\n`. A new `("OTHER", ^OTHER\s*$)` entry sits at the bottom of `_SECTION_PATTERNS` so the terminator line is recognised as a header boundary. Both synthetic sections are now strictly one chunk wide.
2. **OTHER weighted to zero.** `_SECTION_WEIGHTS` entries for `OTHER` were `0.25` across all seven schemas. They are now `0.0`. Text the labeller cannot attribute to a named section contributes no score — front matter, author affiliations, and any lines between detected section headers that don't form part of a labelled section.
3. **Springer-affiliation paragraph removal.** `strip_non_body_sections()` gained a `_strip_affiliation_blocks()` pass (step 1b) that removes affiliation footnotes appearing after the Abstract. A line at the start of a paragraph matching `(?:[A-Z]\.\s*){1,3}[A-Z][a-z]{2,}(?::|·|&|;)(?:[A-Z]\.\s*){1,3}[A-Z][a-z]{2,}` (two-or-more author-initials-runs joined by `:`, `·`, `&`, or `;` — but NOT comma, to avoid matching mid-sentence citations) is treated as a candidate block start; if the block (extended to the next blank line) contains an institution keyword (`Department|Institute|School|Laboratory|Faculty|College|Aquarium|Museum|Foundation|Consultants|Centro|Istituto|Universit...`), it is removed. Verified on 27537: conservation-term occurrences drop from 4 → 1 (only the legitimate IUCN citation remains).

The affiliation-block heuristic is pattern-specific to Springer-style layouts. Future layouts (Elsevier, Wiley, IEEE) may need additional patterns; extend `_SPRINGER_AFFIL_START_RE` or add layout-specific rules.

---

## Study-type classification (added 2026-04-21)

The parquet column `study_type` was previously a hardcoded `"empirical"` default set by `shark_references_to_sql.py`. It now carries a classification into one of six mutually-exclusive labels determined at extraction time from TITLE and KEYWORDS only:

| Label | Triggers (examples) |
|---|---|
| `corrigendum` | "corrigendum", "erratum", "correction to", "publisher's note", "retraction notice" |
| `letter` | "letter to the editor", "reply to", "response to", "commentary on", "brief communication", "rebuttal" |
| `review` | "systematic review", "narrative review", "literature review", "review paper/article", "comprehensive review", "mini-review", "scoping review", "meta-analysis", "umbrella review" |
| `synthesis` | "research synthesis", "a synthesis", "synthesis of", "synthesising" |
| `conceptual` | "conceptual framework", "methodological framework", "theoretical framework", "perspective(s) on", "opinion piece", "viewpoint" |
| `empirical` | default if no other label matches |

Priority order is most-specific-first: a corrigendum of a review still classifies as `corrigendum`; a meta-analysis that mentions "synthesis" still classifies as `review`.

Body text is NOT examined because reviews are routinely cited inside empirical papers, which would trigger false-positive review classifications. Only TITLE and KEYWORDS (author-intent signals) drive the classification.

Downstream analyses that want primary-data-only queries should filter `study_type == "empirical"`. Alex McInturf's 2026-04-21 feedback flagged the current (hardcoded) behaviour as a false-negative source: catch-data and review papers were inheriting every schema tag from their case-study examples. The new classification gives a single filter to exclude reviews and non-primary-data papers from trend analyses.

Accuracy needs manual cross-check against known-correct labels after re-extraction.

---

## Depth extraction (rewritten 2026-04-21)

The previous depth regex `[><~≈]?\s*(\d{1,5}(?:\.\d+)?)\s*m` had an empty-matchable prefix: the `[><~≈]?\s*` alternative allowed any number followed by `m` to match, so body-measurement values (e.g. `5–8 m` for basking shark total length) were captured as depth values.

The new implementation requires a bathymetric-context word within ~60 characters before the number. `_DEPTH_CONTEXT` covers `depth(s)?`, `bathym(etric|etry)?`, `benthic`, `demersal zone`, `water column`, `sea floor`, `below (the) surface`, plus deployment/capture verbs (`caught at|in`, `captured at|in`, `collected at|in|from`, `sampled at|in|from`, `tagged at|in`, `set at|to`, `fished at|in`, `deployed at|to|in`, `hooked at`, `longline at|to`, `trawl(ed) at|between|from`, `dive(d|s) to`, `CTD`, `vertical profile`, `descended to`, `lowered to`, `down to`, `recorded at|to|from`).

Two patterns:

- `_DEPTH_RANGE_RE` — `<CONTEXT> ... (\d+)(-|–|—|to)(\d+) m` — depth ranges like "caught between 200 and 400 m".
- `_DEPTH_SINGLE_RE` — `<CONTEXT> ... (\d+) m` — single values like "deployed at 50 m depth". Only tried if no range match fired, to avoid double-counting range endpoints as singles.

`extract_depth()` now returns an `_evidence` key: a list of evidence-row dicts with `matched_terms`, `section`, and a 160-char `context` snippet in which the matched numeric span is bracketed (`...descended to [350 m] in the channel...`). These rows are appended to `schema_extraction_evidence.csv` during `_match_paper()` so reviewers see the same per-match evidence UI for depth as for other schemas. Previously depth emitted zero evidence rows (evidence CSV had 0 `depth_*` rows of ~260K total).

Smoke-test (2026-04-21):

- "Basking sharks reaching 5 to 8 m in total length" → **no depth extracted** (body measurement correctly rejected)
- "CTD casts deployed at depths of 50-200 m" → **50–200 m** (context word `depth` + deployment verb both present)
- "7 m basking shark diving to a maximum depth of 350 m" → **350 m** (the 7 m body size is rejected, the 350 m depth is captured)

---

## TITLE and KEYWORDS sections (added 2026-04-20)

Two synthetic sections are injected at extraction time:

- **TITLE** — the paper's full title from the bibliographic record (`literature_review.parquet:title`), prepended in `_match_paper()` as `TITLE\n<title>\n\n` before section labelling.
- **KEYWORDS** — the author-supplied keyword block parsed from the raw PDF text BEFORE `strip_non_body_sections()` removes the front matter. `_extract_keywords_block()` finds the line matching `^\s*Key[- ]?words?\s*[:.]` and re-injects the keyword list as `KEYWORDS\n<terms>\n\n` at the top of the body text.

Both receive **weight 2.0** for every schema that uses section weighting (eco_, pr_, gear_, imp_, d_, b_, sb_) — the highest weighting in the system — because they encode author intent rather than incidental mention. A single keyword-block hit (2.0 × 1) plus one body mention is enough to pass any column's threshold of 2.

The `_SECTION_PATTERNS` list places the TITLE and KEYWORDS patterns BEFORE the existing section patterns so they match first. The `_SECTION_WEIGHTS` dict for every supported prefix carries `"TITLE": 2.0, "KEYWORDS": 2.0`.

The validation UI's section-weights table (driven by `rules.json` → `_section_weights`) shows TITLE and KEYWORDS as the leftmost columns rendered in dark green (`w-max` CSS class).

**Schemas without section weighting** (`ob_`, `sp_`, `a_`, `depth_`) do not benefit from TITLE/KEYWORDS injection. `ob_` is fed from a separate geographic pipeline; `sp_` and `a_` are integer counts not binary classifications; `depth_` is regex-extracted numeric metadata. Whether to extend section weighting to `sp_` and `a_` is an open question for the validation meeting.

---

## Acronym disambiguation via prerequisite_terms (added 2026-04-20)

`BinaryColumn` now supports a `prerequisite_terms` mapping of `{term: [list of prerequisite terms]}`. The keyed term's matches only contribute to `total_freq` if at least one of its prerequisites also fires somewhere in the document.

**Use case:** acronym disambiguation. `d_biology` includes `GSI` and `HSI` (case-sensitive) with `prerequisite_terms={"GSI": ["gonadosomatic index"], "HSI": ["hepatosomatic index"]}` — so the acronyms only contribute when their full forms also appear, eliminating acronym-collision false positives without requiring the spelled-out forms to fire alone.

The filter runs after term matching and before threshold comparison. Other terms in the column are unaffected.

---

## Overview

Single-pass extraction pipeline that processes ~30,500 elasmobranch papers, extracting ecosystem, pressure, gear, impact, discipline, and ocean basin metadata using frequency-based keyword matching with per-column thresholds. Produces binary columns (0/1) plus a separate evidence table for team validation.

**Key principle:** Every classification decision is traceable. The evidence table records which terms matched, which anchors fired, and a context snippet — so the team can audit and refine without re-running the full pipeline.

---

## Architecture

```
literature_review.parquet          SharkPapers/YYYY/*.pdf
        │                                    │
        ▼                                    ▼
   ┌─────────┐                        ┌──────────────┐
   │ Paper    │───── author+year ────▶│ PDF Index     │
   │ metadata │      lookup           │ (normalised)  │
   └─────────┘                        └──────────────┘
        │                                    │
        ▼                                    ▼
   ┌──────────────────────────────────────────────┐
   │              process_paper()                  │
   │  1. Resolve PDF → extract text (pdftotext)   │
   │  2. Strip non-body sections                   │
   │  3. Match all 4 schemas simultaneously        │
   │  4. Extract depth, target species, direction  │
   │  5. Record evidence for every match           │
   └──────────────────────────────────────────────┘
        │                    │
        ▼                    ▼
  literature_review     schema_extraction
  _enriched.parquet     _evidence.csv
  (~120 new columns)    (~350K rows)
```

### Files

| File | Purpose |
|------|---------|
| `outputs/literature_review.parquet` | Input: ~30,500 papers × 1,546 columns |
| `outputs/literature_review_enriched.parquet` | Output: original + ~140 new columns (123 binary + metadata) |
| `outputs/schema_extraction_evidence.csv` | Evidence: one row per (paper, column) match |
| `outputs/.schema_extraction_progress.json` | Checkpoint for resume capability |

---

## PDF Matching Strategy

### Primary: Author-year lookup

1. Build index from `SharkPapers/YYYY/*.pdf` directory structure
2. Extract first author surname from parquet `authors` field
3. **Normalise names** — critical for matching across inconsistent transliterations:
   - NFD decomposition strips accents: "Araújo" → "araujo"
   - Remove hyphens: "Abd-Elhameed" → "abdelhameed"
   - Remove apostrophes: "O'Brien" → "obrien"
   - Lowercase, strip spaces
4. Look up `(normalised_surname, year_int)` in index

### Collision disambiguation

~13.7% of (author, year) keys map to multiple PDFs. Resolved by **title-word matching**:

- Extract content words from the parquet title (stop words removed)
- Extract content words from each candidate PDF filename
- Pick the candidate with the most overlapping words
- Fall back to first candidate if no title available

### Match rates (validated on 200-paper sample, 2015–2022)

| Source | Count | Percentage |
|--------|-------|------------|
| PDF + title/abstract | 161 | 80.5% |
| Title/abstract only | 39 | 19.5% |

The 80.5% rate reflects actual PDF availability for these years. Overall PDF coverage across the full corpus is 48.7% (14,876/30,553).

### Planned: DOI-based lookup

99.9% of papers have DOIs. A DOI-primary lookup will be added to match against legacy `{literature_id}.0_{DOI_escaped}.pdf` filenames, which should push match rates close to the 48.7% ceiling for all years.

---

## Text Extraction & Cleaning

### PDF to text

- `pdftotext` subprocess with 10-second timeout
- 500 KB text cap (truncates very large documents)
- Falls back to title + abstract if PDF extraction fails

### Section stripping (false-positive mitigation)

**This is the single most important quality step.** Without it, author names in headers, journal titles in references, and institution names in affiliations all inflate false-positive rates significantly.

**Sections removed:**

| Section | What it catches | Detection |
|---------|----------------|-----------|
| **Front matter** (before Abstract) | Author names ("Rivera" → eco_freshwater), journal metadata, editor names, affiliations | First line matching `ABSTRACT`, `Abstract`, `INTRODUCTION`, `Introduction`, `SUMMARY`, `Summary` |
| **References** (and everything after) | Journal titles ("Marine Pollution Bulletin" → pr_pollution_chemical), geographic places in cited titles, author surnames | Standalone line: `REFERENCES`, `Bibliography`, `LITERATURE CITED`, `WORKS CITED` |
| **Acknowledgements block** | Funder names ("Marine Conservation Society" → eco_marine), institution names | Standalone line: `ACKNOWLEDGEMENTS`, `FUNDING`, `AUTHOR CONTRIBUTIONS`, `DATA AVAILABILITY`, `CONFLICT OF INTEREST` — only if in last 30% of text |

**Measured impact** (200-paper sample, before → after stripping):

- `pr_pollution_chemical`: 3–8 percentage point reduction
- `eco_freshwater`: ~4 pp reduction (author name "Rivera" eliminated)
- Most columns: 2–5 pp reduction in false positives
- No meaningful reduction in true positives (body text unaffected)

---

## Keyword Matching Engine

### Term types

| Type | Syntax | Example | Compiles to |
|------|--------|---------|-------------|
| Plain keyword | `marine` | Whole-word match | `\bmarine\b` |
| Wildcard | `fish*` | Prefix match | `\bfish\w*` |
| Phrase | `coral reef` | Adjacent words | `\bcoral\ reef\b` |
| AND logic | `(acidification AND pH)` | Both present anywhere | Two separate regex checks |
| Raw regex | `Ne\b` | Pass-through | `Ne\b` (effective population size) |

### Schema categories

| Category | Prefix | Columns | Matching mode | Description |
|----------|--------|---------|---------------|-------------|
| Ecosystem | `eco_` | 20 | Frequency-based | Habitat/environment classification |
| Pressure | `pr_` | 26 | Frequency-based | Threats and stressors |
| Gear | `gear_` | 28 | Frequency-based | Fishing gear, survey methods, and mitigation |
| Impact | `imp_` | 21 | Frequency + anchors | Population/ecological impacts |
| Discipline | `d_` | 19 | Frequency-based | Research area classification |
| Ocean basin | `b_` | 9 | Frequency-based | Study geography |

All categories now use **universal frequency-based scoring** with per-column configurable thresholds (see below).

### Universal frequency-based scoring

All schema categories use `findall()` frequency counting rather than simple presence/absence. Each column has a configurable **threshold** — the minimum total mention count (summed across all matching terms) required for binary=1.

**Rationale:** A single mention of "marine" in a freshwater stingray paper should not trigger `eco_marine=1`. Generic terms (marine, fishing, behaviour) get higher thresholds (3+); specific terms (depredation, coral reef, ampullae of Lorenzini) get threshold=1.

**Decision rules:**

| Condition | Binary | Rationale |
|-----------|--------|-----------|
| total_freq < threshold | 0 | Insufficient mentions — likely passing reference |
| total_freq ≥ threshold, no anchors defined | 1 | Confident: enough co-occurring mentions |
| total_freq ≥ threshold, anchors defined, none fire | 0 | Ambiguous term without supporting context |
| total_freq ≥ threshold, anchors defined, ≥1 fires | 1 | Confident: frequency + context confirmed |

**Evidence table records** `total_freq`, `term_count`, and `threshold` for every match, enabling sensitivity analysis to tune thresholds after the initial run.

**Worked example — `eco_marine` (threshold=3):**

| Scenario | Mentions | Binary | Rationale |
|----------|----------|--------|-----------|
| "marine" appears once in intro context | 1 | 0 | Below threshold |
| "marine" ×2 + "ocean" ×1 | 3 | 1 | Meets threshold |
| "marine" ×5 + "sea" ×3 + "ocean" ×2 | 10 | 1 | Central topic |

**Worked example — `imp_abundance` (threshold=2, with anchors):**

- **Terms:** "abundance", "population size", "population decline", "population trend"
- **Anchors:** "population", "decline", "increase", "change", "trend", "status"

| Scenario | total_freq | Anchors fired | Binary | Rationale |
|----------|-----------|---------------|--------|-----------|
| "abundance" ×1 | 1 | 0 | 0 | Below threshold + no anchors |
| "abundance" ×3 | 3 | 0 | 0 | Meets threshold but no anchor context |
| "abundance" ×2 + "population" + "decline" | 2 | 2 | 1 | Meets threshold + anchors confirm |

In all cases, the evidence table records the matched terms and anchors, enabling review of borderline (score=1) cases.

---

## False-Positive Mitigations

| Problem identified | Root cause | Solution applied |
|--------------------|-----------|-----------------|
| Author "Rivera" → `eco_freshwater` | Standalone "river" matched surnames | Removed "river"; use compounds: "river shark", "river system", "riverine" |
| "surface area" → `eco_epipelagic` | Standalone "surface" too broad | Changed to "surface waters", "surface layer" |
| "Marine Pollution Bulletin" in refs → `pr_pollution_chemical` | Journal titles in reference lists | Section stripping removes references before matching |
| "abundance" in any ecology context → `imp_abundance` | Common ecological term | Require anchor co-occurrence ("population", "decline", "trend") |
| Parasitology papers → `pr_disease` | "parasite", "infection" are disease terms | **No change needed** — parasitology IS disease/health research |
| "MPA" in address → `gear_mit_time_area` | Institutional abbreviations | Section stripping removes front matter/affiliations |
| "marine" once in freshwater paper → `eco_marine` | Single mention sufficient under old binary matching | Universal frequency thresholds: `eco_marine` requires ≥3 mentions |
| `Ne\b` matching "determine" → `imp_genetic` | Raw regex compiled case-insensitive | Raw regex terms (containing `\b`) now compiled case-sensitive |
| Inline "Abstract:" not stripped (MDPI, Frontiers) | Regex required standalone line | Updated regex accepts inline `Abstract:` / `ABSTRACT.` formats |

---

## Evidence Table

### Purpose

Enables team validation of extraction results without doubling the column count in the main database. Each row records *why* a paper matched a particular column, providing an audit trail for every classification decision.

### Structure

| Column | Type | Description |
|--------|------|-------------|
| `literature_id` | string | Links to main database (DOI or `orphan_<idx>` for orphan rows) |
| `title` | string | Paper title (first 200 chars) for quick identification |
| `column` | string | Schema column name (e.g., `eco_marine`, `imp_abundance`) |
| `binary` | int | Final 0/1 classification |
| `total_freq` | int | Total mention count across all matching terms |
| `term_count` | int | Number of distinct terms that fired |
| `threshold` | int | Column's configured threshold for binary=1 |
| `matched_terms` | string | Semicolon-separated, with frequency: `"marine(5); ocean(18)"` |
| `matched_anchors` | string | Semicolon-separated list of anchor terms that fired (impact only) |
| `context` | string | ~160-character text snippet around first match |

### Which columns need evidence

- **eco_, pr_, gear_, imp_** — all produce evidence (ambiguous terms, potential false positives)
- **Species columns (sp_)** — do NOT need evidence (unambiguous binomial name matches)
- **Discipline columns (d_)** — produce evidence (same frequency-based scoring)
- **Ocean basin columns (b_)** — produce evidence (geographic terms can appear in references)

### Scale

- ~8 evidence rows per paper on average
- ~250,000 rows at full corpus scale
- Manageable in R/dplyr, Excel, or any data tool

### Validation workflow

1. Load evidence CSV into R or Excel
2. Filter to a specific column (e.g., `pr_pollution_chemical`)
3. Review `context` snippets — quickly spot false positives
4. Sort by `score` to find borderline cases (score=1, binary=0)
5. Discuss with team; adjust terms, thresholds, or anchors in schema definitions
6. Re-run extraction (`--resume` skips unchanged papers)

---

## Additional Extracted Metadata

### Depth extraction

Regex-based extraction of depth ranges mentioned in the text:

- **Range patterns:** "0–200 m", "depths of 150 m to 300 m"
- **Single values:** "depth of 500 m", ">200 m"
- **Output:** `depth_range` (text), `depth_min_m` (float), `depth_max_m` (float)

### Ecosystem guesses

Hierarchical best-guess columns derived from binary results:

| Column | Level | Values |
|--------|-------|--------|
| `eco_1_guess` | Realm | marine, freshwater, brackish/estuarine |
| `eco_2_guess` | Zone | pelagic, coastal, demersal/benthic, reef, deep-water, intertidal, mangrove, seagrass, kelp, polar, riverine, nursery, pupping |
| `eco_3_guess` | Depth zone | epipelagic, mesopelagic, bathypelagic, abyssal |

### Gear target species

Regex extraction of target species/groups from gear context (e.g., "tuna longline" → "tuna").

### Impact direction and quantification

| Column | Type | Description |
|--------|------|-------------|
| `imp_direction` | text | Sentiment of negative vs positive cues: "negative", "positive", "mixed", "not stated" |
| `imp_quantified` | boolean | Whether paper provides quantitative measures (%, p-values, CIs) |
| `imp_confidence` | JSON | Per-column scores for transparency (e.g., `{"imp_abundance": 3}`) |

---

## Runtime & Performance

### Processing model

- **Single-pass:** each paper's PDF extracted once, all 6 schemas matched simultaneously
- **Multiprocessing:** `Pool` with `imap_unordered` for parallel paper processing
- **Checkpointing:** progress saved every 500 papers (configurable) for resume capability

### Benchmarks

| Configuration | Time | Rate |
|---------------|------|------|
| 200 papers, 1 worker | 52 seconds | 3.8 papers/sec |
| 30,500 papers, 11 workers (est.) | 25–40 minutes | ~15 papers/sec |

**Bottleneck:** PDF text extraction (pdftotext I/O), not regex matching.

---

## Usage

```bash
# Dry run: process 200 papers, print results, write nothing
python3 scripts/extract_schema_columns.py --dry-run 200

# Custom input file (e.g., test sample)
python3 scripts/extract_schema_columns.py --input /tmp/test_sample.parquet --dry-run 200

# Full run with 11 workers
python3 scripts/extract_schema_columns.py --workers 11

# Resume interrupted run
python3 scripts/extract_schema_columns.py --workers 11 --resume
```

---

## Initial Validation Results

*200-paper dry run, 2015–2022 sample (pre-frequency-threshold, simple binary matching)*

**Note:** These rates predate the switch to frequency-based scoring. Expected reductions with thresholds: eco_marine 83%→~47%, pr_fishing_commercial 29.5%→~8.5%. Full updated rates pending next extraction run.

### Hit rates

**Ecosystem (eco_):**

| Column | Hits | Rate | Assessment |
|--------|------|------|------------|
| eco_marine | 166 | 83.0% | Expected — elasmobranch papers |
| eco_coastal | 102 | 51.0% | Reasonable — many nearshore studies |
| eco_pelagic | 81 | 40.5% | Open-ocean species well-represented |
| eco_freshwater | 56 | 28.0% | Includes estuarine (post cleanup) |
| eco_demersal | 58 | 29.0% | Benthic species common |
| eco_deepwater | 24 | 12.0% | Deep-sea elasmobranchs |
| eco_nursery | 18 | 9.0% | Nursery habitat studies |
| eco_polar | 16 | 8.0% | Arctic/Antarctic studies |

**Pressure (pr_):**

| Column | Hits | Rate | Assessment |
|--------|------|------|------------|
| pr_fishing_commercial | 59 | 29.5% | Major threat — expected |
| pr_bycatch | 57 | 28.5% | Major threat — expected |
| pr_fishing_recreational | 44 | 22.0% | Game fishing well-studied |
| pr_disease | 29 | 14.5% | Parasitology + health studies |
| pr_pollution_chemical | 22 | 11.0% | Contaminant studies |
| pr_climate_change | 19 | 9.5% | Growing field |

**Gear (gear_):**

| Column | Hits | Rate | Assessment |
|--------|------|------|------------|
| gear_trawl | 30 | 15.0% | Common survey/fishery gear |
| gear_longline | 25 | 12.5% | Major pelagic gear |
| gear_artisanal | 25 | 12.5% | Small-scale fisheries |
| gear_gillnet | 18 | 9.0% | Common coastal gear |
| gear_survey | 18 | 9.0% | Research vessels, BRUVs, ROV |

**Impact (imp_):**

| Column | Hits | Rate | Assessment |
|--------|------|------|------------|
| imp_abundance | 75 | 37.5% | Score-based, requires anchors |
| imp_genetic | 14 | 7.0% | Population genetics studies |
| imp_cpue | 6 | 3.0% | Fisheries-focused papers |
| imp_mortality | 5 | 2.5% | Direct mortality studies |

### Evidence quality

- **1,621 evidence rows** across 184/200 papers and 74 columns
- Context snippets manually validated — genuine matches confirmed
- Borderline cases (binary=0, terms matched) appropriately conservative

---

## Design Decisions Log

| Decision | Rationale | Date |
|----------|-----------|------|
| Separate evidence CSV (not extra parquet columns) | Keeps main database clean; ~250K rows manageable separately | 2026-03-10 |
| Score threshold ≥ 2 for impact columns | Single-term matches too noisy; two co-occurring signals provide reasonable confidence | 2026-03-10 |
| Section stripping before matching | Reduces false positives 2–8 pp across all schemas | 2026-03-10 |
| 30% threshold for acknowledgements stripping | Prevents stripping body paragraphs that merely mention "acknowledgement" | 2026-03-10 |
| Author-year PDF matching with normalisation | Handles accent/hyphen variation across transliteration conventions | 2026-03-10 |
| Title-word disambiguation for collisions | 13.7% of (author, year) keys have multiple PDFs | 2026-03-10 |
| No evidence for species columns | Binomial name matches are unambiguous | 2026-03-10 |
| Wildcards expand with `\b` prefix | Prevents "fish*" matching "selfish" or "starfish" | 2026-03-10 |
| Universal frequency-based scoring for all schemas | Single-mention false positives (e.g. "marine" once in freshwater paper); per-column thresholds tuneable | 2026-03-12 |
| PDF-only extraction (no title/abstract fallback) | Title/abstract too short for reliable frequency scoring; papers without PDFs get all zeros | 2026-03-12 |
| Raw regex case-sensitive compilation | `Ne\b` was matching "ne" in "determine" with IGNORECASE | 2026-03-12 |
| Inline Abstract regex fix | MDPI/Frontiers use `Abstract:` inline, not standalone line; improved coverage 53%→74% | 2026-03-12 |
| Discipline columns (d_) added | 19 research area columns, enabling Schiffman et al. 2020 comparison and cross-validation | 2026-03-12 |
| Ocean basin columns (b_) added | 9 basins, complements existing geographic extraction pipeline (author country, study location) | 2026-03-12 |
