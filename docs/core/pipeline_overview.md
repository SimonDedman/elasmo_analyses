# Pipeline Overview (as-built)

**Last updated:** 2026-07-21

A single map of how the project turns a bare citation into an answerable
question, with the current corpus figures and the script that owns each
stage. This is the developer-facing companion to the front-page
[README](../../README.md).

---

## Corpus figures (current)

**These figures are generated, not typed.** Run
`python3 scripts/report_corpus_stats.py`, which derives every value from the
artifacts themselves and writes `outputs/corpus_stats.json` (machine-readable)
plus `outputs/corpus_stats.md` (this table). Paste the regenerated table here
rather than editing a number in place.

<!-- BEGIN corpus_stats: paste from outputs/corpus_stats.md -->

*Generated 2026-08-06.*

| Metric | Value | Notes |
|--------|------:|-------|
| Papers catalogued | 31,653 | rows in the enriched parquet |
| Parquet columns | 1,744 | all families plus metadata |
| PDF files on disk | 20,404 | raw count; over-counts supplements and duplicates |
| Evidence rows | 293,107 | audit trail across 19,945 papers |
| Unique authors (OpenAlex) | 29,929 | `outputs/openalex_unique_authors.csv` |
| Techniques in taxonomy | 215 | `data/master_techniques.csv` |
| Species columns | 1,308 | `sp_` prefix |
| RAG index | 19,885 papers / 204,508 chunks | `outputs/rag/build_status.json` |
| Conference abstracts | 9,792 | 3,174 chondrichthyan, 54 meetings |
| Geographic coverage | ~18.6% | merged `geo_` columns (not yet generated) |

Column families in the parquet:

| Prefix | Meaning | Columns |
|--------|---------|--------:|
| `sp_` | species | 1,308 |
| `a_` | analytical technique | 215 |
| `sb_` | sub-basin | 43 |
| `gear_` | fishing gear | 29 |
| `pr_` | pressure / threat | 26 |
| `imp_` | impact / response | 25 |
| `eco_` | ecosystem | 23 |
| `d_` | discipline | 19 |
| `geo_` | geography | 19 |
| `b_` | ocean basin (text-mined) | 9 |
| `ob_` | ocean basin (geo pipeline) | 9 |
| `depth_` | depth | 3 |

<!-- END corpus_stats -->

### Reading the numbers correctly

- **"123 extraction columns" is retired.** It counted the original six binary
  schemas before sub-basins landed. The six-schema binary set is now **127**
  (`d_` 19 + `eco_` 23 + `pr_` 26 + `gear_` 29 + `imp_` 21 real binary + `b_` 9);
  adding `sb_` gives **170**, which is what older docs call "166". Say which set
  you mean, or quote the family table above.
- **Techniques live in `data/master_techniques.csv` (215), not in
  `database/technique_taxonomy.db`.** That database's `techniques` table is
  **empty**; the "208 techniques in the taxonomy DB" claim repeated across the
  docs is wrong in both the number and the location. The "151" figure some docs
  quote is the count of distinct `technique_name` values in the DB's
  `paper_techniques` table, which is a usage count, not the taxonomy.
- **There is no master paper database.** `shark_references.db`, `shark_panel.db`
  and their siblings are all 0 bytes. The enriched parquet is the corpus of
  record; the "30,553 papers in the master DB" figure has no backing artifact.
- **`sp_` and `a_` columns are frequency counts**, not binaries, so "papers with
  a hit" and "column count" are different questions.

### Where these numbers appear

They are hard-coded in several surfaces. **When any figure changes, re-run the
generator and update all of these in the same commit**, otherwise they drift
apart, which is how the author count came to be published as 28,334, 28,953,
and 29,929 simultaneously.

| Surface | What it holds |
|---|---|
| `docs/core/pipeline_overview.md` (this table) | canonical, all figures |
| `README.md` corpus table | rounded values plus a pointer here |
| `docs/results.html` stat tiles | papers, PDFs, authors, columns |
| `docs/slides/index.html` stat tiles | papers, columns |
| `scripts/viz_pipeline_diagram.R` | four figures baked into a published figure |
| `~/.claude/projects/<project>/memory/MEMORY.md` | quick-reference table |
| `.claude/QUICK_REFERENCE.md`, `.claude/claude.md`, `.claude/commands/project-status.md` | technique count and DB path |

Dated logs (`memory/project_session_*.md`, `outputs/extraction_runs/*`,
historical `docs/species/*` narratives) record what was true at the time and
should **not** be resynced.

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

**The query interface (stage 6) has no equivalent.** Nothing about its
retrieval or answer quality has been measured, so no number about it can
be quoted. Scoped 2026-08-06 in
[`docs/superpowers/specs/2026-08-06-retrieval-evaluation-design.md`](../superpowers/specs/2026-08-06-retrieval-evaluation-design.md);
see the open gaps below.

---

## Open gaps (scheduled work, not known-unknowns)

Kept here so they stay visible rather than living only in the specs that
describe them.

1. **Retrieval evaluation for the database query interface** — no
   gold-standard question set, no precision@k / recall@k / nDCG, no
   groundedness or citation-correctness scoring. `CE_FLOOR` / `CE_STRONG`
   in `scripts/rag/query.py` are fitted to two probes. Do this before the
   interface goes in front of external users.
   [Design](../superpowers/specs/2026-08-06-retrieval-evaluation-design.md).
2. **`geo_study_latitude` / `geo_study_longitude` are unusable** — all
   values positive *and* magnitudes unrelated to true positions, so it is
   not a recoverable sign flip. Fix is unwritten; the producer scripts
   (`extract_study_locations_phase4*.py`, `merge_geography.py`) contain no
   hemisphere handling. Only the H2 figure is worked around, via
   `geo_study_country` polygon centroids. Use `geo_study_country` for all
   location work meanwhile.
3. **Contradiction-aware claim strength** — the badge currently measures
   agreement-of-topic, not agreement-of-claim; two papers with opposite
   conclusions both count as support. Needs an entailment pass
   (RAG next-steps item 6).
4. **Corpus-wide LLM relabelling stalled at ~8%** of the 19,882-paper
   worklist, blocked on funded inference access, not on compute cost.
5. **Public inferred-attribute exposure** — per-author gender, origin, and
   ethnicity are algorithmically inferred and publicly surfaced; the
   mitigation plan is written but unimplemented.
