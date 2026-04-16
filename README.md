# Elasmobranch Analytical Methods Review

**A systematic review of analytical techniques across elasmobranch research disciplines**

[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)

---

## Overview

This repository contains materials for the **"New Frontiers in Elasmobranch Data Analysis"** project, initially presented at the European Elasmobranch Association (EEA) Conference 2025 in Rotterdam, Netherlands.

**Project Status:** Analysis & validation phase (April 2026) — Extraction complete, author enrichment done, building interactive validation UI

**Original Session (EEA 2025):**
- **Date:** Thursday, 30 October 2025
- **Format:** 45 minutes of discipline panel reviews + 50 minutes of oral presentations
- **Organizers:** Dr. Simon Dedman & Dr. Guuske Tiktak

**Current Scale:** 30,553 papers | 18,065 PDFs acquired | 123 extraction columns (6 schemas) | 28,953 unique authors | 1,308 species columns

---

## Project Goals

### Primary Objectives
1. **Comprehensive Review:** Systematically document current analytical techniques across 8 major elasmobranch research disciplines
2. **Empirical Analysis:** Extract and analyse techniques from ~30,500 elasmobranch papers spanning 75+ years (1950-2026)
3. **Expert Evaluation:** Assess strengths, weaknesses, and suitability of different approaches through specialist insight
4. **Temporal Mapping:** Identify historical trends, current methods, declining approaches, and emerging frontiers
5. **Knowledge Transfer:** Create accessible overviews valuable to both practitioners and non-specialists
6. **Network Building:** Connect researchers within and across disciplines

### Long-Term Vision
- Create a **living database** updated annually at EEA and AES conferences
- Develop **automated trend analysis** using the Shark-References database
- Build **conversational AI interface** for querying the knowledge base (see [LLM Integration](#llm-integration))
- Integrate with **Sharkipedia**, **MegaMove**, **Altmetric/Dimensions**, and other elasmobranch databases
- Add **ecosystem, pressure, gear, and impact** metadata columns for rich cross-cutting analyses
- Establish **community-driven** annual updates

---

## The 8 Disciplines

1. **Biology, Life History, & Health (BIO)** - Age/growth, reproduction, physiology, anatomy, disease, health indices
2. **Behaviour & Sensory Ecology (BEH)** - Behavioral observation, social structure, sensory biology, network analysis
3. **Trophic & Community Ecology (TRO)** - Diet analysis, trophic position, food webs, ecosystem roles
4. **Genetics, Genomics, & eDNA (GEN)** - Population genetics, phylogenetics, genomics, environmental DNA
5. **Movement, Space Use, & Habitat Modeling (MOV)** - Telemetry, movement models, species distribution models, MPAs
6. **Fisheries, Stock Assessment, & Management (FISH)** - Stock assessment, CPUE standardization, bycatch, data-poor methods
7. **Conservation Policy & Human Dimensions (CON)** - IUCN assessments, policy evaluation, human-wildlife conflict, citizen science
8. **Data Science & Integrative Methods (DATA)** - Statistical frameworks, machine learning, data integration, reproducibility

---

## Repository Structure

- **[docs/](docs/)** — Documentation
  - **[core/](docs/core/)** — Project status & planning
    - [eea2025_data_panel_comprehensive_plan.md](docs/core/eea2025_data_panel_comprehensive_plan.md) — Master plan
    - [eea2025_data_panel_program_timeline_personnel.md](docs/core/eea2025_data_panel_program_timeline_personnel.md) — Programme timeline & personnel
    - [project_status_comprehensive.md](docs/core/project_status_comprehensive.md) — Current project status
    - [project_cleanup_plan.md](docs/core/project_cleanup_plan.md) — Cleanup plan
    - [project_cleanup_review.md](docs/core/project_cleanup_review.md) — Cleanup review
    - [project_completion_summary.md](docs/core/project_completion_summary.md) — Completion summary
    - [project_organization_complete.md](docs/core/project_organization_complete.md) — Organisation complete
    - [visualization_summary.md](docs/core/visualization_summary.md) — Visualisation summary
  - **[database/](docs/database/)** — Database schema, extraction, acquisition (53 files)
    - [database_schema_design.md](docs/database/database_schema_design.md) — Schema documentation
    - [extraction_complete_summary.md](docs/database/extraction_complete_summary.md) — Extraction results
    - [technique_taxonomy_database_design.md](docs/database/technique_taxonomy_database_design.md) — Technique taxonomy design
    - [paper_acquisition_status.md](docs/database/paper_acquisition_status.md) — Paper acquisition status
    - [pdf_acquisition_complete_summary.md](docs/database/pdf_acquisition_complete_summary.md) — PDF acquisition summary
    - [ocr_processing_guide.md](docs/database/ocr_processing_guide.md) — OCR processing guide
    - [duplicate_removal_final_guide.md](docs/database/duplicate_removal_final_guide.md) — Duplicate removal guide
    - ... and 46 more guides (download tools, institutional access, thesis handling, etc.)
  - **[schema_proposals/](docs/schema_proposals/)** — Extraction column categories & logic
    - [ecosystem_component_proposal.md](docs/schema_proposals/ecosystem_component_proposal.md) — `eco_*` columns (20)
    - [pressure_proposal.md](docs/schema_proposals/pressure_proposal.md) — `pr_*` columns (26)
    - [gear_proposal.md](docs/schema_proposals/gear_proposal.md) — `gear_*` columns (28)
    - [impact_proposal.md](docs/schema_proposals/impact_proposal.md) — `imp_*` columns (21)
    - [extraction_logic.md](docs/schema_proposals/extraction_logic.md) — Pipeline documentation
    - [extraction_quality_issues.md](docs/schema_proposals/extraction_quality_issues.md) — False-positive catalogue
    - [extraction_review_reference.md](docs/schema_proposals/extraction_review_reference.md) — Review reference
    - [schiffman_comparison.md](docs/schema_proposals/schiffman_comparison.md) — Schiffman et al. 2020 comparison
    - [issue7_ecosystem_marine_removal.md](docs/schema_proposals/issue7_ecosystem_marine_removal.md) — eco_marine removal
  - **[integrations/](docs/integrations/)** — External database integrations
    - [sharkipedia_integration.md](docs/integrations/sharkipedia_integration.md) — Sharkipedia API & data overlap
    - [megamove_integration.md](docs/integrations/megamove_integration.md) — MegaMove/GSMP tracking data
    - [altmetric_integration.md](docs/integrations/altmetric_integration.md) — Altmetric scoring & social impact
    - [altmetric_grants_datasets.md](docs/integrations/altmetric_grants_datasets.md) — Dimensions grants & datasets
  - **[technical/](docs/technical/)** — Technical specs & design docs
    - [2026-04-16-validation-ui-design.md](docs/technical/2026-04-16-validation-ui-design.md) — Interactive validation UI design
    - [2026-04-06-sr-monthly-sync-design.md](docs/technical/2026-04-06-sr-monthly-sync-design.md) — Shark-References monthly sync design
    - [visualization_strategy.md](docs/technical/visualization_strategy.md) — Visualisation strategy
    - [external_database_integration_analysis.md](docs/technical/external_database_integration_analysis.md) — External DB integration analysis
    - [final_data_cleaning_report.md](docs/technical/final_data_cleaning_report.md) — Data cleaning report
    - [shark_references_search_script_guide.md](docs/technical/shark_references_search_script_guide.md) — SR search script guide
  - **[geographic/](docs/geographic/)** — Geographic extraction & analysis (14 files)
    - [QUICK_START_GEOGRAPHIC_ANALYSIS.md](docs/geographic/QUICK_START_GEOGRAPHIC_ANALYSIS.md) — Quick start guide
    - [PHASE_4_FINAL_RESULTS.md](docs/geographic/PHASE_4_FINAL_RESULTS.md) — Phase 4 final results
    - [PARACHUTE_RESEARCH_ANALYSIS_SUMMARY.md](docs/geographic/PARACHUTE_RESEARCH_ANALYSIS_SUMMARY.md) — Parachute research analysis
    - [DATABASE_QUERY_REFERENCE.md](docs/geographic/DATABASE_QUERY_REFERENCE.md) — Query reference
    - ... and 10 more (phase 3-4 docs, temporal analysis, etc.)
  - **[species/](docs/species/)** — Species database & SR automation (8 files)
    - [species_database_readme.md](docs/species/species_database_readme.md) — Species database readme
    - [shark_references_automation_workflow.md](docs/species/shark_references_automation_workflow.md) — SR automation workflow
    - [shark_species_extraction_summary.md](docs/species/shark_species_extraction_summary.md) — Species extraction summary
    - ... and 5 more
  - **[techniques/](docs/techniques/)** — Technique taxonomy & classification (11 files)
    - [technique_classification_schema_proposal.md](docs/techniques/technique_classification_schema_proposal.md) — Classification schema
    - [discipline_structure_analysis.md](docs/techniques/discipline_structure_analysis.md) — Discipline structure
    - [ai_impact_on_shark_research_disciplines.md](docs/techniques/ai_impact_on_shark_research_disciplines.md) — AI impact assessment
    - ... and 8 more
  - **[LLM/](docs/LLM/)** — LLM integration
    - [llm_integration_roadmap.md](docs/LLM/llm_integration_roadmap.md) — LLM roadmap
    - [notebooklm_alternatives_summary.md](docs/LLM/notebooklm_alternatives_summary.md) — Platform comparison
  - **[candidates/](docs/candidates/)** — Panellist recruitment (6 files)
    - [candidate_search_protocol.md](docs/candidates/candidate_search_protocol.md) — Search protocol
    - [expert_recommendations_comprehensive.md](docs/candidates/expert_recommendations_comprehensive.md) — Expert recommendations
    - ... and 4 more
  - **[abstract/](docs/abstract/)** — Conference abstract materials (9 files)
  - **[archive/](docs/archive/)** — Historical documents (31 files)
- **scripts/** — Data processing & extraction scripts
- **database/** — SQLite databases
- **outputs/** — Generated outputs (analysis CSVs, figures, validation XLSX)
- **data/** — Input & integration data (Sharkipedia, SCImago)
- [CONTRIBUTING.md](CONTRIBUTING.md) — Contribution guidelines

---

## Current Status (April 2026)

### Latest Updates

**✅ Author Enrichment Complete** (April 2026)
- OpenAlex: 28,953 unique authors, 71,801 author-paper records, 87.7% with institution data
- NamSor: gender (16,793 M / 9,429 F), origin, and diaspora enrichment for 28,922 authors
- Gender resolved: 86.9% (13.1% unknown, daily genderize.io batch running)

**✅ Altmetric Integration Complete** (March 2026)
- 10,897 papers enriched with social attention scores (65.5% hit rate)

**✅ Schema Extraction Pipeline Complete** (March 2026)
- 6 schemas, 123 binary columns: [Ecosystem](docs/schema_proposals/ecosystem_component_proposal.md) (20), [Pressure](docs/schema_proposals/pressure_proposal.md) (26), [Gear](docs/schema_proposals/gear_proposal.md) (28), [Impact](docs/schema_proposals/impact_proposal.md) (21), Discipline (19), Ocean basin (9)
- 247,131 evidence rows across 18,202 papers
- Section-weighted scoring with corpus-trained section detection
- Full pipeline documentation: [Extraction Logic](docs/schema_proposals/extraction_logic.md)

**✅ Corpus Expansion Largely Complete** (April 2026)
- 18,065 PDFs on disk (up from ~12,400 at conference)
- Ingested batches from Jürgen (1,361), David (89), Elena (316), Guuske (19)
- Automated monthly Shark-References sync via anacron

**🔨 Interactive Validation UI** (April 2026, in progress)
- Static HTML pages on GitHub Pages, one per author (28,952 pages)
- Structured validation inputs replacing free-text XLSX approach
- Submission via GitHub Actions → PRs
- Design spec: [Validation UI design](docs/technical/2026-04-16-validation-ui-design.md)

### Completed Phases

- [x] **Phase 1: PDF Technique Extraction** (2025-10-26)
  - 12,381 PDFs processed, 9,503 papers with techniques (76.5% coverage)
  - 151 unique techniques identified, 23,307 technique mentions

- [x] **Phase 2: Analysis & Conference Materials** (2025-10-26)
  - Collaboration networks (18,633 authors), geographic analysis (73 countries)
  - AI impact assessment, 25+ publication-ready visualisations

- [x] **Phase 3: EEA 2025 Conference** (2025-10-30)
  - Panel session delivered, expert reviews collected

- [x] **Phase 4: Corpus Expansion & Schema Extraction** (2026 Q1)
  - 18,065 PDFs acquired, 123 extraction columns across 6 schemas
  - Author enrichment (OpenAlex + NamSor), Altmetric integration
  - Automated monthly Shark-References sync

### In Progress

- [ ] **Phase 5: Validation & Analysis** (2026 Q2)
  - Interactive validation UI for community-scale review
  - Temporal trend lineplots, co-occurrence heatmaps, geographic dashboards
  - Cross-validation against Schiffman et al. 2020

- [ ] **Phase 6: LLM Integration** (2026 Q2)
  - Stack: Qdrant + nomic-embed-text + Ollama
  - Conversational interface for querying corpus

- [ ] **Phase 7: Manuscript & Public Release** (2026)
  - Methods paper, interactive web dashboard, public database release

---

## Key Results

### Database Scale

| Metric | Value |
|--------|-------|
| Papers in database | 30,553 |
| PDFs acquired | 18,065 |
| Extraction columns | 123 (6 schemas) |
| Evidence rows | 247,131 |
| Papers with evidence | 18,202 |
| Unique authors (OpenAlex) | 28,953 |
| Species columns | 1,308 |
| Analytical technique columns | 215 |

### PDF Technique Extraction (from initial 12,381 PDFs)

**Coverage:** 9,503 papers with techniques (76.5%)

**Discipline Distribution:**
| Discipline | Papers | % of Corpus |
|------------|--------|-------------|
| GEN (Genetics) | 7,992 | 84.7% |
| DATA (Data Science) | 4,545 | 48.2% |
| BIO (Biology) | 2,092 | 22.2% |
| FISH (Fisheries) | 1,583 | 16.8% |
| MOV (Movement) | 1,442 | 15.3% |
| TRO (Trophic) | 1,318 | 14.0% |
| CON (Conservation) | 858 | 9.1% |
| BEH (Behaviour) | 265 | 2.8% |

### External Integration Overlap

| Source | Overlap with our DB |
|--------|-------------------|
| Sharkipedia species | 1,177/1,308 (90%) |
| Sharkipedia DOIs | 201/273 (74%) |
| Sharkipedia traits | 163 species with data |
| SCImago journals | 1,558 matched (64.7% of papers) |

---

## External Integrations

### Sharkipedia
- **Status:** API pull complete (1,288 species, 8,494 trait measurements, 828 trends)
- **Species overlap:** 90% (1,177 of our 1,308 species found in Sharkipedia)
- **Value:** Trait data (length, age, litter size) enriches our literature database
- See [docs/integrations/sharkipedia_integration.md](docs/integrations/sharkipedia_integration.md)

### MegaMove / GSMP
- **Status:** Assessed — data portal closed, no public API
- **Alternative:** GSMP GitHub repos and Movebank REST API for shark tracking data
- See [docs/integrations/megamove_integration.md](docs/integrations/megamove_integration.md)

### Altmetric / Dimensions
- **Status:** Complete — 10,897 papers enriched (65.5% hit rate)
- **Value:** Social impact scores for ~30,500 DOIs; grant/dataset integration via Dimensions
- See [docs/integrations/altmetric_integration.md](docs/integrations/altmetric_integration.md)

---

## Schema Proposals

Six schema categories extract binary classifications from PDFs using keyword + context matching with section-weighted scoring. Fully implemented and run across all 18,065 PDFs.

| Category | Prefix | Columns | Proposal |
|----------|--------|---------|----------|
| Ecosystem | `eco_` | 20 (habitat, depth, realm) | [ecosystem_component_proposal.md](docs/schema_proposals/ecosystem_component_proposal.md) |
| Pressure / Threat | `pr_` | 26 (fishing, climate, pollution) | [pressure_proposal.md](docs/schema_proposals/pressure_proposal.md) |
| Fishing Gear | `gear_` | 28 (gear type, mitigation) | [gear_proposal.md](docs/schema_proposals/gear_proposal.md) |
| Impact / Response | `imp_` | 21 (mortality, abundance, etc.) | [impact_proposal.md](docs/schema_proposals/impact_proposal.md) |
| Discipline | `d_` | 19 (research area) | — |
| Ocean Basin | `b_` | 9 (study geography) | — |
| **Extraction Logic** | — | Pipeline docs, evidence table | [extraction_logic.md](docs/schema_proposals/extraction_logic.md) |
| **Quality Issues** | — | False-positive catalogue | [extraction_quality_issues.md](docs/schema_proposals/extraction_quality_issues.md) |

See [Issue #2](https://github.com/SimonDedman/elasmo_analyses/issues/2) for column design discussion. Extraction review reference: [extraction_review_reference.md](docs/schema_proposals/extraction_review_reference.md).

---

## LLM Integration

We are developing a conversational AI interface to enable researchers to query the knowledge base naturally:

> "What techniques are used for age determination in deep-sea sharks?"
> "Which countries have published most on acoustic telemetry since 2015?"
> "Show me papers combining eDNA and stable isotope analysis"

### Approach

**Stack for 30,500+ papers:**
- **Vector Database:** Qdrant (open-source, scalable)
- **Embeddings:** nomic-embed-text (local, free)
- **LLM:** Ollama with Llama 3.1 or Qwen2.5 (local, private)
- **Interface:** Open WebUI or custom Gradio app

See [docs/LLM/notebooklm_alternatives_summary.md](docs/LLM/notebooklm_alternatives_summary.md) for platform comparison.

---

## Key Documentation

### Project Overview
- **[docs/readme.md](docs/readme.md)** - Documentation index
- **[docs/core/project_status_comprehensive.md](docs/core/project_status_comprehensive.md)** - Complete project summary

### Database & Extraction
- **[docs/database/database_schema_design.md](docs/database/database_schema_design.md)** - Schema documentation
- **[docs/database/extraction_complete_summary.md](docs/database/extraction_complete_summary.md)** - Extraction results

### External Integrations
- **[docs/integrations/sharkipedia_integration.md](docs/integrations/sharkipedia_integration.md)** - Sharkipedia API & data overlap
- **[docs/integrations/megamove_integration.md](docs/integrations/megamove_integration.md)** - MegaMove/GSMP tracking data
- **[docs/integrations/altmetric_integration.md](docs/integrations/altmetric_integration.md)** - Altmetric & Dimensions

### Schema Proposals
- **[docs/schema_proposals/](docs/schema_proposals/)** - Ecosystem, pressure, gear, impact column proposals

### LLM Integration
- **[docs/LLM/llm_integration_roadmap.md](docs/LLM/llm_integration_roadmap.md)** - LLM roadmap
- **[docs/LLM/notebooklm_alternatives_summary.md](docs/LLM/notebooklm_alternatives_summary.md)** - Platform comparison

### Conference Materials
- **[outputs/panel_reports/](outputs/panel_reports/)** - Expert panel materials
- **[outputs/abstract_reviews/](outputs/abstract_reviews/)** - 109 presentation reviews

### Analysis & Visualizations
- **[outputs/analysis/](outputs/analysis/)** - CSV analysis files
- **[outputs/figures/](outputs/figures/)** - Publication-ready figures

---

## Quick Start

### View Extraction Results
```bash
# Open the main database
sqlite3 database/technique_taxonomy.db

# Query top techniques
SELECT technique_name, COUNT(DISTINCT paper_id) as papers
FROM paper_techniques
GROUP BY technique_name
ORDER BY papers DESC
LIMIT 10;
```

### Load Analysis Tables
```bash
# View discipline trends
head outputs/analysis/discipline_trends_by_year.csv

# View technique rankings
head outputs/analysis/top_techniques.csv
```

---

## How to Contribute

We welcome contributions from the elasmobranch research community!

**Current needs:**
1. **Validate extraction results** — interactive validation pages coming soon (see [Validation UI design](docs/technical/2026-04-16-validation-ui-design.md))
2. **Review schema columns** — check false positives/negatives, suggest rule changes
3. **Share missing papers** — contribute PDFs via [Shark References](https://shark-references.com/)
4. **Test LLM prototypes** — help evaluate conversational interfaces

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

---

## Citation

If you use materials from this project, please cite:

```
Dedman, S., Tiktak, G., et al. (2025). Elasmobranch Analytical Methods Review:
A systematic extraction of techniques from 9,503 shark science papers (1950-2025).
European Elasmobranch Association Conference 2025, Rotterdam, Netherlands.
https://github.com/SimonDedman/elasmo_analyses
```

---

## License

This work is licensed under a [Creative Commons Attribution 4.0 International License](https://creativecommons.org/licenses/by/4.0/).

---

## Contact

**Project Leads:**
- Dr. Simon Dedman - simondedman@gmail.com - [GitHub](https://github.com/SimonDedman)
- Dr. Guuske Tiktak

**Collaborators:**
- David Ruiz Garcia — Mediterranean fisheries; schema proposals ([Issue #2](https://github.com/SimonDedman/elasmo_analyses/issues/2))
- David Schiffman — Citation/social media analysis; Altmetric integration
- Elena Fernández Corredor — Mediterranean trophic literature review
- Jürgen Pollerspöck & Nico Straube ([Shark-References](https://shark-references.com/))

---

## Acknowledgments

This project builds upon:
- **~30,500 elasmobranch papers** by thousands of researchers worldwide (1950-2026)
- **[Shark-References](https://shark-references.com/)** — Comprehensive elasmobranch literature repository
- **[Sharkipedia](https://sharkipedia.org/)** — Trait and trend data for elasmobranch species
- **EEA and AES conferences** — Decades of community knowledge sharing
- **Panel experts and contributors** — Discipline-specific insights and validation

---

*Last updated: 2026-04-16*
*Version: 4.0 — Validation & analysis phase*
