# Documentation Index

**Last updated:** 2026-07-21

Documentation for the **Elasmobranch Analytical Methods Review**. New
here? Read the [front-page README](../README.md) first, then the
[pipeline overview](core/pipeline_overview.md).

Historical and superseded material has been moved under
[`archive/`](archive/) — if you are looking for old download/Sci-Hub/Tor
guides, the EEA-2025 abstract, or dated build logs, they live there.

---

## Start here

- **[../README.md](../README.md)** — what the project is, corpus at a glance, the 8 disciplines.
- **[core/pipeline_overview.md](core/pipeline_overview.md)** — the as-built pipeline (acquire → OCR → extract → enrich → analyse → ask) with current figures and the script owning each stage.
- **[results.html](results.html)** — live links to the Author Atlas, collaboration network, figures, and validation UI.
- **[core/eea2025_data_panel_comprehensive_plan.md](core/eea2025_data_panel_comprehensive_plan.md)** — the master plan / protocol (authoritative, long).

## The analytical design (schema & extraction)

- **[schema_proposals/](schema_proposals/)** — the design core. Per-schema column proposals (`discipline`, `ecosystem`, `pressure`, `gear`, `impact`, `ocean_basin`, plus `species`, `depth`, `analytical_techniques`), the [extraction logic](schema_proposals/extraction_logic.md), and the [false-positive catalogue](schema_proposals/extraction_quality_issues.md).
- **[techniques/](techniques/)** — technique classification schema and the 8-discipline structure.
- **[database/technique_taxonomy_database_design.md](database/technique_taxonomy_database_design.md)** — the 208-technique taxonomy DB.

## Current design specs

- **[superpowers/specs/](superpowers/specs/)** — the up-to-date design specs:
  - `2026-07-07-cascade-finalize-ingest-extract-design.md` — the unified `acquire_cascade.py` acquisition pipeline.
  - `2026-07-11-rag-schema-filters-web-frontend-design.md` — RAG web frontend.
  - `2026-07-03-extraction-validation-loop-design.md` — the validation loop.
  - `2026-07-07-book-chapter-mining-design.md`, `2026-07-07-fable-corpus-extraction-design.md`.

## Data, database & PDFs

- **[database/database_schema_design.md](database/database_schema_design.md)** — schema documentation.
- **[database/ocr_processing_guide.md](database/ocr_processing_guide.md)** — the PDF text-extraction / OCR pipeline.
- **[database/shark_references_to_sql_mapping.md](database/shark_references_to_sql_mapping.md)**, **[database/techniques_snapshot_strategy.md](database/techniques_snapshot_strategy.md)**.
- **[species/](species/)** — species database & Shark-References automation.

## Enrichment & integrations

- **[schema_proposals/author_enrichment.md](schema_proposals/author_enrichment.md)**, **[schema_proposals/altmetric.md](schema_proposals/altmetric.md)**, **[schema_proposals/journal_quality.md](schema_proposals/journal_quality.md)**, **[schema_proposals/open_access.md](schema_proposals/open_access.md)**.
- **[integrations/](integrations/)** — [Sharkipedia](integrations/sharkipedia_integration.md), [MegaMove/GSMP](integrations/megamove_integration.md).

## Validation

- **[validation_and_rule_improvement_report.md](validation_and_rule_improvement_report.md)** — extractor accuracy vs gold/LLM-oracle labels; first rule-improvement round.
- **[technical/2026-04-16-validation-ui-design.md](technical/2026-04-16-validation-ui-design.md)** — community validation UI design.

## Geographic

- **[schema_proposals/geographic_extraction.md](schema_proposals/geographic_extraction.md)** — geographic extraction design.
- **[geographic/DATABASE_QUERY_REFERENCE.md](geographic/DATABASE_QUERY_REFERENCE.md)**, **[geographic/SQL_QUERIES_TEMPORAL_ANALYSIS.md](geographic/SQL_QUERIES_TEMPORAL_ANALYSIS.md)** — reusable query references.

## LLM / RAG

- **[LLM/rag_prototype_status.md](LLM/rag_prototype_status.md)** — the built RAG stack (BGE-small + FAISS + Ollama, CPU-local).

## Other current

- **[no_doi_papers_analysis.md](no_doi_papers_analysis.md)** — profile of no-DOI papers.
- **[team_download_task.md](team_download_task.md)**, **[SETUP_GOOGLE_SHEET.md](SETUP_GOOGLE_SHEET.md)** — crowdsourced acquisition task setup.
- **[technical/external_database_integration_analysis.md](technical/external_database_integration_analysis.md)**.

---

## Archive

[`archive/`](archive/) holds superseded and point-in-time material,
grouped: `acquisition/` (pre-cascade download guides + status snapshots),
`abstract_2025/` (EEA-2025 conference abstract), `geographic_phases/`
(dated build logs), `techniques_population/`, `candidates_preconf/`,
`core_status/`, `schema_snapshots/`, and `llm_planning/`. Kept for
provenance; not current.
