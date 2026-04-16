# Extraction Pipeline Upgrade Plan

**Goal:** Upgrade species, analytical technique, and depth extraction to scan full PDF text with frequency counting and evidence trails, then regenerate validation pages.

**Current state:**
- Species: binary (present/absent) from title+abstract+described_species metadata only. 1,308 species. Misses species mentioned only in PDF body.
- Analytical techniques: binary from title+abstract metadata only. 215 techniques. Same gap.
- Depth: regex from PDF text, produces numeric range. No evidence trail (no surrounding sentence context stored).
- Tier 1 schemas (eco, pr, gear, imp, d, b): full PDF text with frequency counting and evidence trail. Working correctly.

**Changes needed:**

## 1. Species extraction from full PDF text with frequency

Create `scripts/extract_species_from_pdfs.py`:
- Read species list from existing parquet column names (1,308 binomials + common names from species DB)
- For each PDF: extract text, search for each species binomial and common name
- Store frequency count (not just boolean) per species per paper
- Store matched context sentences in evidence CSV
- Output: update sp_ columns in parquet from bool to int16 (frequency), append to evidence CSV

Approach: reuse the PDF text extraction from `extract_schema_columns.py` (pdftotext subprocess), iterate species patterns with `re.findall()` for counting.

Estimated run time: ~30-60 min for 18,065 PDFs (species matching is faster than full schema extraction since it's just string matching, no anchors/thresholds).

## 2. Analytical technique extraction from full PDF text with frequency

Same script or sibling: `scripts/extract_techniques_from_pdfs.py`
- Read technique list from existing parquet column names (215 techniques)
- For each PDF: search for technique name and alternative queries
- Store frequency count per technique per paper
- Store matched context in evidence CSV
- Output: update a_ columns from bool to int16

Estimated run time: ~20-40 min (fewer patterns than species).

## 3. Depth evidence trail

Modify `extract_schema_columns.py` depth extraction to also store:
- The matched sentence/context for each depth value found
- Output: append depth evidence rows to evidence CSV

This is a smaller change — add evidence logging to the existing `extract_depth()` function.

## 4. Rule palette in validation pages

- Extract all BinaryColumn rules from extract_schema_columns.py as JSON (done: `outputs/extraction_rules.json`, 23 KB)
- Embed as shared file `docs/validate/assets/rules.json`
- Update validate.js to display rules per category: show all terms, threshold, anchors, case-sensitive terms, highlighting which rule fired for each paper

## 5. Regenerate validation pages

After extraction re-run: regenerate all 28,952 pages with new data.

## 6. Submission batching

Modify Cloudflare Worker to batch submissions:
- On POST: write to Cloudflare KV store with timestamp key
- Scheduled CRON trigger (daily): read all KV entries, create single PR with all day's submissions
- Reduces GitHub Actions from potentially thousands of runs to 1/day

## 7. Auto-merge for valid submissions

Add GitHub Action that:
- On PR creation by Validation Bot: validate JSON schema, check for conflicts with existing validations
- If clean: auto-approve and merge
- If conflicts: label PR for manual review
