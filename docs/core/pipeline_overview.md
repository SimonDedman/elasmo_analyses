# Pipeline Overview (as-built)

**Last updated:** 2026-07-21

A single map of how the project turns a bare citation into an answerable
question, with the current corpus figures and the script that owns each
stage. This is the developer-facing companion to the front-page
[README](../../README.md).

---

## Corpus figures (current)

| Metric | Value | Notes |
|--------|------:|-------|
| Papers catalogued | 30,553 | master DB; enriched parquet has 31,648 rows incl. SR IDs |
| PDFs on disk | 18,364 | library `rglob` counts 20,046 files (incl. supplementary/dupes) |
| Extraction columns | 123 | binary, across 6 schemas |
| Evidence rows | 274,967 | audit trail, 18,202+ papers |
| Unique authors (OpenAlex) | 28,953 | gender 86.9% resolved |
| Techniques in taxonomy | 208 | `database/technique_taxonomy.db` |
| Geographic coverage | ~18.6% | merged `geo_` columns |

Figures grow with each monthly sync. The canonical live numbers are in
project memory; treat this table as a dated snapshot.

---

## The stages

```
acquire → ingest+OCR → extract → enrich → analyse → ask
```

### 1. Acquire — `acquire_cascade.py`

Unified per-paper acquisition. For a given paper it tries each source in
turn until it finds the PDF: open-access resolvers, DOI recovery, the
Biodiversity Heritage Library (`fetch_bhl_archive.py` for pre-1970 /
taxonomy no-DOI work), and Unpaywall. `finalize_acquisitions()` then
chains **ingest → verified-delete → incremental extraction**, mirroring
the monthly sync's Phase 5b, so a newly-found paper flows straight into
the parquet. Books are skipped by default.

> This replaced dozens of per-source download scripts (DownThemAll, Tor,
> Sci-Hub, institutional-access, manual guides). Those are archived under
> [`docs/archive/acquisition/`](../archive/acquisition/). Design spec:
> [`docs/superpowers/specs/2026-07-07-cascade-finalize-ingest-extract-design.md`](../superpowers/specs/2026-07-07-cascade-finalize-ingest-extract-design.md).

**Monthly top-up:** `sync_shark_references.py` (anacron) crawls
Shark-References, diffs against the corpus, downloads new papers,
notifies, and runs incremental extraction. Design:
[`docs/technical/2026-04-06-sr-monthly-sync-design.md`](../technical/2026-04-06-sr-monthly-sync-design.md).

### 2. Ingest + OCR — `ingest_pdfs.py`, `ocr_library.py`

`ingest_pdfs.py` is the generic ingestion entry (5 match strategies,
book/chapter extraction, inline OCR fallback for image-only PDFs).
Scanned/historical PDFs are made text-searchable via the screen → OCR →
verify pipeline so the extractor can read them. Full detail:
[OCR pipeline guide](../database/ocr_processing_guide.md).

### 3. Extract — `extract_schema_columns.py`

Reads each PDF's text (via `pdftotext`; no title/abstract fallback) and
scores it against 123 binary columns in 6 schemas — discipline (`d_`),
ecosystem (`eco_`), pressure (`pr_`), gear (`gear_`), impact (`imp_`),
ocean basin (`b_`) — with section-weighted, frequency-based scoring and
per-column thresholds. Every classification is backed by a quote in
`outputs/schema_extraction_evidence.csv`. Small batches patch the parquet
via `extract_incremental.py`. Logic:
[extraction_logic.md](../schema_proposals/extraction_logic.md);
false-positive patterns:
[extraction_quality_issues.md](../schema_proposals/extraction_quality_issues.md).

### 4. Enrich

| Layer | Script | Source |
|-------|--------|--------|
| Authors + institutions | `enrich_authors_openalex.py` | OpenAlex (batch DOI) |
| Gender / origin / diaspora | `enrich_namsor.py`, `infer_author_gender.py`, `genderize_daily.py` | NamSor, gender-guesser, Genderize.io |
| Citation impact | `enrich_altmetric.py` | Altmetric |
| Journal quality | `lookup_scimago_journals.py` | SCImago |
| Incremental (new papers) | `enrich_new_papers.py` | chains the above for freshly-ingested papers |

### 5. Analyse — `viz_*.R`

The R visualisation suite generates the publication figures, one script
per theme: `viz_A_spatial.R`, `viz_D_bars_E1_sankey.R`,
`viz_H_geography.R` (H1–H5 geographic figures), and siblings. The
[Author Atlas](../network_atlas/) is a deployed interactive collaboration
map, built by `build_author_atlas.R` (React frontend under
`frontend/network_atlas`, deployed to `docs/network_atlas/` via CI).

### 6. Ask — `scripts/rag/`

A local retrieval-augmented-generation prototype: **BGE-small**
embeddings + **FAISS** index + **Ollama** (qwen2.5:3b), all CPU-local and
private. `scripts/rag/{common,build_index,query}.py`. Status:
[rag_prototype_status.md](../LLM/rag_prototype_status.md).

---

## Supporting pipelines

- **PDF library QA / dedup:** `detect_duplicate_pdfs.py`,
  `review_duplicates.py`, and `scripts/dedup/` (ingest-time dedup hook).
  Detects duplicate/preprint/mislabelled PDFs before they double-count.
- **Non-English / non-extractable audit:** `find_non_extractable_pdfs.py`
  + `detect_non_english.py` feed the OCR pipeline.
  `resolve_pdf_language.py` corrects the OCR language label from the
  filename + corpus metadata (better than page-1 OCR guessing), and
  old German routes to a `deu+Fraktur` blackletter model. See the
  [OCR guide](../database/ocr_processing_guide.md).
- **Orphan staging:** `stage_orphan_pdfs.py` files non-SR PDFs with
  Crossref-recovered metadata (ids ≥ 600000).
- **Frontend data refresh:** `regenerate_papers_data.py`,
  `rebuild_viz_data.py` rebuild the RAG-frontend and corpus-lookup data.

---

## Validation

An automated loop scores the rule-based extractor against human-reviewed
("gold") and LLM-oracle ("silver") labels, mines synonym fixes from
evidence quotes, and re-scores each change. First round complete —
[validation & rule-improvement report](../validation_and_rule_improvement_report.md).
Design spec:
[`docs/superpowers/specs/2026-07-03-extraction-validation-loop-design.md`](../superpowers/specs/2026-07-03-extraction-validation-loop-design.md).
