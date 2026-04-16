# Proposed Schema: Analytical Techniques

**Status:** Active — extracted from full PDF text since 2026-04-16
**Column prefix:** `a_`
**Team lead:** Guuske Tiktak
**Source:** Technique taxonomy database (`database/technique_taxonomy.db`, techniques table)

## Purpose

Record which analytical techniques are applied in each paper. Enables analyses like "which techniques are used most frequently for movement ecology vs. population assessment?" or "how has adoption of stable isotope analysis changed over time?" One column per technique in the taxonomy — 215 columns in total.

## Column Naming

Columns follow the pattern `a_technique_name` using lowercase with underscores. Examples:

| Column | Technique |
|--------|-----------|
| `a_behavioural_observation` | Behavioural observation |
| `a_accelerometry` | Accelerometry |
| `a_stable_isotope_analysis` | Stable isotope analysis |
| `a_mark_recapture` | Mark–recapture |
| `a_acoustic_telemetry` | Acoustic telemetry |
| `a_generalised_additive_model` | Generalised additive model |

Where a technique name contains a forward slash or special character, those are replaced with underscores and any redundant underscores collapsed.

## Source Taxonomy

Techniques and their synonyms are loaded directly from `database/technique_taxonomy.db` (the `techniques` table). Each technique record includes:

- **Primary name:** the canonical label and the basis for the column name
- **Synonyms:** alternative names and abbreviations (e.g., "GAM" for generalised additive model, "SIA" for stable isotope analysis)
- **Category / discipline mapping:** grouping within the taxonomy hierarchy

The database is the authoritative source for both column names and search terms. Changes to technique names or synonyms in the database will propagate to future extractions.

## Extraction Method

Columns are populated by scanning the **full text** of each PDF for:

1. The primary technique name
2. All synonyms recorded in the database for that technique

Matching is **case-insensitive** with **word-boundary enforcement**. Each hit increments the frequency counter for that technique's column. Both primary name and synonym hits count towards the same column.

### Script

`scripts/extract_species_techniques_from_pdfs.py`

## Storage Format

| Column type | Format | Notes |
|-------------|--------|-------|
| `a_*` (215 columns) | `int16` | Frequency count: number of times the technique name or any synonym appears in the PDF text |

A value of `0` indicates no match found. A value ≥ 1 indicates the technique was used or mentioned; higher values typically reflect more substantive application.

**Previous pipeline (pre-2026-04-16):** columns were stored as `bool` (True/False) and matched only against title + abstract metadata. This frequently missed techniques described in the methods section but not the abstract. All values were re-extracted from full PDF text on 2026-04-16.

## Evidence

Every technique column that fires (count > 0) generates a row in `outputs/schema_extraction_evidence.csv` containing:

| Field | Content |
|-------|---------|
| `literature_id` | Paper identifier |
| `column` | e.g., `a_stable_isotope_analysis` |
| `matched_terms` | List of terms that triggered the match (primary name and/or synonyms) |
| `frequency` | Total match count across full PDF text |
| `context` | First-occurrence sentence from the PDF for manual verification |

## Known Issues and Limitations

1. **Technique name overlap:** Some technique names are substrings of others (e.g., "model" appears in many technique names). Word-boundary matching reduces but does not eliminate this; review the evidence sentences for borderline cases.
2. **Generic methodology terms:** Broad terms such as "analysis", "model", or "survey" are not used as standalone search terms; they appear only as part of longer technique phrases to avoid noise.
3. **Evolving taxonomy:** The technique taxonomy database is actively maintained. Columns added or renamed in the database after 2026-04-16 will require an incremental re-extraction pass.
4. **Pre-2026-04-16 values were metadata-only** and should not be used for technique-level analyses without re-extraction.
5. **Methods vs. cited mentions:** A paper may mention a technique in a literature review without applying it. Frequency and the evidence context sentence should be used to distinguish applied vs. cited techniques.

## Coverage Expectations

Based on the PDF library (18,065 PDFs):

- High-frequency techniques (acoustic telemetry, stable isotope analysis, mark–recapture, statistical modelling) are expected to appear in thousands of papers.
- Emerging or specialised techniques (e.g., environmental DNA, accelerometry, biologging) will have lower coverage but are analytically important for temporal trend analyses.
- Most papers will have between 3 and 10 technique columns ≥ 1.

## Validation

Interactive evidence review pages for technique columns are linked from the extraction review dashboard:

**<https://simondedman.github.io/elasmo_analyses/validate/>**

Each technique page shows matched papers, frequency distributions, context sentences, co-occurring techniques, and flagged potential false positives.

## Discussion Points

1. **Frequency threshold for "applied":** A threshold of ≥ 2 may better distinguish papers that genuinely apply a technique from those that cite it in passing. To be determined after reviewing frequency distributions across the corpus.
2. **Technique hierarchy in analysis:** The taxonomy database groups techniques into families (e.g., telemetry methods, genetic methods, modelling approaches). Analysis scripts should use this grouping for discipline-level summaries rather than treating all 215 columns as flat.
3. **Synonym completeness:** Teams are encouraged to submit additional synonyms for under-matched techniques via the project issue tracker; these feed directly into the database and subsequent extraction runs.

---
*Draft created: 2026-04-16. Pipeline migrated from metadata-only bool to full-PDF int16 frequency extraction.*
