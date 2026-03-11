# Schema Extraction Logic

*Technical documentation for `scripts/extract_schema_columns.py`*

*Last updated: 2026-03-10*

---

## Overview

Single-pass extraction pipeline that processes ~30,500 elasmobranch papers, extracting ecosystem, pressure, gear, and impact metadata using keyword matching with context-aware scoring. Produces binary columns (0/1) plus a separate evidence table for team validation.

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
  (~85 new columns)     (~250K rows)
```

### Files

| File | Purpose |
|------|---------|
| `outputs/literature_review.parquet` | Input: ~30,500 papers × 1,546 columns |
| `outputs/literature_review_enriched.parquet` | Output: original + ~85 new columns |
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
| Ecosystem | `eco_` | 20 | Simple binary | Any term match → 1 |
| Pressure | `pr_` | 23 | Simple binary | Any term match → 1 |
| Gear | `gear_` | 18 | Simple binary | Any term match → 1 |
| Impact | `imp_` | 17 | Score-based + anchors | Requires confidence threshold |

### Score-based matching (impact columns)

Impact terms are often ambiguous in isolation ("abundance" appears in many non-impact contexts). The scoring system requires co-occurrence of multiple signals:

1. Count matching **terms** (e.g., "abundance", "population size")
2. Count matching **anchors** (e.g., "population", "decline", "trend")
3. **Score** = terms fired + anchors fired

**Decision rules:**

| Condition | Binary | Rationale |
|-----------|--------|-----------|
| Anchors defined, none fire | 0 | Ambiguous term without supporting context |
| Score ≥ 2 | 1 | Confident: multiple co-occurring signals |
| Score = 1 | 0 | Insufficient evidence (recorded for review) |

**Worked example — `imp_abundance`:**

- **Terms:** "abundance", "population size", "population decline", "population trend"
- **Anchors:** "population", "decline", "increase", "change", "trend", "status"

| Scenario | Terms fired | Anchors fired | Score | Binary |
|----------|-------------|---------------|-------|--------|
| Paper mentions only "abundance" | 1 | 0 | 1 | 0 |
| Paper mentions "abundance" + "population" + "decline" | 1 | 2 | 3 | 1 |
| Paper mentions "population decline" + "population trend" | 2 | 3 | 5 | 1 |

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

---

## Evidence Table

### Purpose

Enables team validation of extraction results without doubling the column count in the main database. Each row records *why* a paper matched a particular column, providing an audit trail for every classification decision.

### Structure

| Column | Type | Description |
|--------|------|-------------|
| `literature_id` | string | Links to main database |
| `column` | string | Schema column name (e.g., `eco_marine`, `imp_abundance`) |
| `binary` | int | Final 0/1 classification |
| `score` | int | Term + anchor count |
| `matched_terms` | string | Semicolon-separated list of search terms that fired |
| `matched_anchors` | string | Semicolon-separated list of anchor terms that fired (impact only) |
| `context` | string | ~160-character text snippet around first match |

### Which columns need evidence

- **eco_, pr_, gear_, imp_** — all produce evidence (ambiguous terms, potential false positives)
- **Species columns (sp_)** — do NOT need evidence (unambiguous binomial name matches)
- **Discipline columns (d_)** — already exist, not extracted here

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

- **Single-pass:** each paper's PDF extracted once, all 4 schemas matched simultaneously
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

*200-paper dry run, 2015–2022 sample*

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
