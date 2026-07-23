# Book-chapter mining: surface shark papers hidden in scanned volumes

**Date:** 2026-07-07
**Status:** Design (implement post-conference)
**Author:** Simon Dedman (with Claude Code)

## Problem / opportunity

The BHL/archive.org fetch (`fetch_bhl_archive.py`) downloads whole scanned
volumes (e.g. *Records of the Australian Museum*, *Studies in Ichthyology*)
because **one** target chapter matched a corpus paper. These volumes (105 in the
current staging, ~6.8 GB, each >200 pp) contain **many** articles — and some are
shark/elasmo papers that were never in SharkRefs. Today they're neither filed
nor mined: the cascade's `--skip-books` guard correctly leaves them untouched
(filing a volume whole under one `literature_id` would bury the other chapters).

**Goal:** mine each scanned volume for its constituent articles, identify the
shark-relevant ones **not already in the corpus**, and surface them as candidate
new papers for review and addition.

## What already exists (reuse, don't rebuild)

- `ingest_pdfs.detect_book()` — flags volumes (>200 pp / ISBN).
- `ingest_pdfs.extract_toc_entries()` — OCR-parses front matter (pp 2–30) into
  `(title, start_page, end_page)` across several TOC formats.
- `ingest_pdfs.handle_book()` — splits a volume by TOC and matches each chapter
  against the corpus, filing the ones that match.
- `ingest_pdfs.match_pdf()` — 5-strategy DOI/author/title matching.
- `extract_schema_columns.py` — the elasmobranch-proximity relevance logic
  (section-weighted keyword scoring) used across the corpus.
- `stage_orphan_pdfs.py` — new-id convention (id ≥ 600000) + `stage_pdfs()`.

The novel work is small: **score the *unmatched* chapters for shark relevance and
route the fresh ones to a review queue**, plus an accept-to-corpus step.

## Pipeline (TOC-driven)

```
for each volume (detected book) in staging/library:
  1. OCR front matter -> extract_toc_entries() -> [(title, start, end), ...]
     - no parseable TOC -> route WHOLE volume to manual queue (flag: 'no-TOC')
  2. for each TOC entry:
       a. split page range -> chapter PDF (pikepdf/qpdf)
       b. OCR chapter text (ensure_text_extractable)
       c. relevance = elasmo_score(chapter_text)   # reuse extraction logic
       d. if relevance below threshold -> DROP (not shark-relevant)
       e. match = match_pdf(chapter)               # DOI/title/author vs corpus
       f. classify:
            - matched & in corpus      -> already have it (optionally file if PDF missing)
            - matched but PDF missing   -> file chapter under existing id
            - NO match, shark-relevant  -> CANDIDATE NEW PAPER  <-- the payload
  3. write review queue (see below)
```

### Relevance scoring

Reuse the corpus's elasmobranch-proximity scorer from
`extract_schema_columns.py` (section-weighted keyword hits, elasmo-term
proximity). A chapter passes if it clears the same threshold used for corpus
inclusion. Record the score and the top matched terms for the reviewer.

### Corpus matching

`match_pdf(chapter)` against `viz_data.csv` / `papers_data.json`. "Not in
corpus" = no DOI hit, no author+year hit, and best title overlap below the
ingest threshold. Store the best near-miss (title + score) so the reviewer can
sanity-check false "new" flags.

## Output: review queue (xlsx)

`outputs/book_mining_candidates_<date>.xlsx` — formatted per house style
(frozen bold header row, autofilter). One row per candidate-new shark chapter:

| Column | Meaning |
|---|---|
| volume_id | staging id of the source volume |
| volume_title | parsed volume/journal title |
| chapter_title | TOC title of the article |
| chapter_authors | parsed author(s) |
| page_range | start–end in the volume |
| relevance_score | elasmo score + top terms |
| best_corpus_match | nearest existing paper + match score (or 'none') |
| chapter_pdf | path to the split chapter PDF (for inspection) |
| **decision** | reviewer fills: accept / reject / duplicate |
| notes | reviewer notes |

Rejected/duplicate rows are dropped. Accepted rows feed the accept step.

## Accept-to-corpus

For each `decision == accept`:
1. Assign a new `literature_id` (≥ 600000, orphan convention).
2. Add a minimal record to `papers_data.json` / the tracking DB (title, authors,
   year parsed from TOC/volume, source = 'book-mining:<volume_id>').
3. Ingest the split chapter PDF via `ingest_pdfs.ingest_source()` (files it into
   SharkPapers under the new id).
4. Run `extract_incremental.py --ids <new_ids>` to classify it into the parquet.

Once every relevant chapter of a volume is either filed or reviewer-rejected,
the volume itself may be retired from staging (or archived) — but only after the
review queue for that volume is fully dispositioned. **Never auto-delete a
volume that still has undispositioned chapters.**

## Components (single-purpose units)

- `mine_book_chapters.py` — orchestrator: volumes -> TOC -> chapters -> score ->
  match -> classify -> review xlsx. Read-only w.r.t. the corpus (produces the
  queue only).
- `accept_book_candidates.py` — consumes the reviewed xlsx; performs id
  assignment + ingest + extract for accepted rows. The only writer.

Splitting discovery/scoring (read-only) from acceptance (writes) keeps the
destructive step small, reviewable, and gated behind a human decision — mirrors
the finalize design's dry-run/verify separation.

## Risks / open questions

- **OCR quality on old scans** drives TOC parse + relevance. Budget for a
  meaningful `no-TOC` / low-confidence manual bucket; don't assume clean TOCs.
- **Page-range accuracy**: TOC page numbers (printed) vs PDF page indices
  (scan offset). `handle_book` already handles some offset; verify per volume.
- **Relevance threshold calibration**: run against a few known volumes where the
  shark chapters are known, tune before a full sweep.
- **Duplicate new-ids**: a chapter may be a paper already in the corpus under a
  different scan; the best_corpus_match column + reviewer catch this.

## Out of scope

- Non-TOC volumes beyond flagging them for manual handling (boundary-detection
  segmentation was considered and deferred).
- Re-downloading volumes; works only on what is already staged/local.

## Relationship to the cascade

This subproject is what makes `--include-books` safe to enable. Until it exists,
`finalize_acquisitions(skip_books=True)` (the default) leaves volumes untouched
in staging. See `2026-07-07-cascade-finalize-ingest-extract-design.md`.
