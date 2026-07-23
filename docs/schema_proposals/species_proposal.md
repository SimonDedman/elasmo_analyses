# Proposed Schema: Species

**Status:** Active — extracted from full PDF text since 2026-04-16
**Column prefix:** `sp_`
**Team lead:** Chris Mull
**Source:** Shark References species database (all described elasmobranch taxa)

## Purpose

Record which elasmobranch species (or broader taxa) are mentioned in each paper. Enables analyses like "which species are most studied, and by which disciplines?" or "are there geographic biases in species-level research effort?" One column per species binomial from the Shark References database — 1,308 columns in total.

## Column Naming

Columns follow the pattern `sp_genus_species` using lowercase with underscores. Examples:

| Column | Species |
|--------|---------|
| `sp_carcharodon_carcharias` | *Carcharodon carcharias* |
| `sp_sphyrna_lewini` | *Sphyrna lewini* |
| `sp_alopias_superciliosus` | *Alopias superciliosus* |
| `sp_rhincodon_typus` | *Rhincodon typus* |
| `sp_torpedo_torpedo` | *Torpedo torpedo* |

For subspecies or author-year variants, only the binomial portion is used.

## Extraction Method

Columns are populated by scanning the **full text** of each PDF for:

1. The species binomial (e.g., *Carcharodon carcharias*)
2. The primary common name, where one is recorded in the Shark References database (e.g., "white shark", "great white shark")

Matching is **case-insensitive** with **word-boundary enforcement** to avoid partial matches (e.g., "carcharias" won't match "epicarcharias"). Both Latin binomial and common name hits contribute to the frequency count for the same column.

### Script

`scripts/extract_species_techniques_from_pdfs.py`

## Storage Format

| Column type | Format | Notes |
|-------------|--------|-------|
| `sp_*` (1,308 columns) | `int16` | Frequency count: number of times the species name (binomial or common name) appears in the PDF text |

A value of `0` indicates no match found. A value ≥ 1 indicates the species was mentioned; higher values reflect greater frequency of mention.

**Previous pipeline (pre-2026-04-16):** columns were stored as `bool` (True/False) and matched only against title + abstract metadata. This frequently missed species mentioned only in the PDF body. All values were re-extracted from full PDF text on 2026-04-16.

## Evidence

Every species column that fires (count > 0) generates a row in `outputs/schema_extraction_evidence.csv` containing:

| Field | Content |
|-------|---------|
| `literature_id` | Paper identifier |
| `column` | e.g., `sp_carcharodon_carcharias` |
| `matched_terms` | List of terms that triggered the match (binomial and/or common name) |
| `frequency` | Total match count across full PDF text |
| `context` | First-occurrence sentence from the PDF for manual verification |

## Known Issues and Limitations

1. **Common name ambiguity:** Common names such as "hammerhead" or "shark" aren't used as matching terms because they resolve to multiple species. Only unambiguous common names from the Shark References database are used.
2. **Genus-level papers:** Papers studying *Sphyrna* spp. without naming a specific species will score 0 on all `sp_sphyrna_*` columns. Genus-level coverage is handled by a separate grouping step at analysis time, not at extraction.
3. **Spelling variants and hyphens:** The extractor normalises whitespace and hyphens but doesn't currently handle OCR-introduced errors in older scanned PDFs.
4. **Non-elasmobranch species mentions:** If a prey species' name happens to match an elasmobranch binomial, a false positive can result. Frequency thresholds and the evidence context sentence help identify these cases.
5. **Pre-2026-04-16 values were metadata-only** and should not be used for any species-level analyses. The full-text re-extraction supersedes all prior values.

## Coverage Expectations

Based on the PDF library (18,065 PDFs):

- The most-studied species (*Carcharodon carcharias*, *Sphyrna lewini*, *Rhincodon typus*, *Carcharhinus limbatus*, *Prionace glauca*) are expected to appear in hundreds to low thousands of papers.
- The long tail: the majority of the 1,308 species will appear in fewer than 10 papers.
- Papers studying multiple species simultaneously will have multiple `sp_*` columns ≥ 1.

## Validation

Interactive evidence review pages for species columns are linked from the extraction review dashboard:

**<https://simondedman.github.io/elasmo_analyses/validate/>**

Each species column page shows matched papers, frequency distributions, context sentences, and flagged potential false positives.

## Discussion Points

1. **Frequency threshold for "present":** Currently any frequency ≥ 1 counts as a mention. Should a minimum threshold (e.g., ≥ 2) be applied to reduce single-word noise? To be decided after reviewing frequency distributions.
2. **Synonyms and nomenclature changes:** Some species have been renamed since older papers were published. The Shark References database includes synonym lists; these should be incorporated into the matching terms where available.
3. **Genus and family roll-ups:** Analysis scripts should aggregate `sp_*` columns to genus (`sp_sphyrna_*`) and family level for coarser-grained analyses. This aggregation happens post-extraction, not in the column schema.

---
*Draft created: 2026-04-16. Pipeline migrated from metadata-only bool to full-PDF int16 frequency extraction.*
