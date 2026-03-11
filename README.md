# Elasmobranch Analytical Methods Review

**A systematic review of analytical techniques across elasmobranch research disciplines**

[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)

---

## Overview

This repository contains materials for the **"New Frontiers in Elasmobranch Data Analysis"** project, initially presented at the European Elasmobranch Association (EEA) Conference 2025 in Rotterdam, Netherlands.

**Project Status:** Post-conference development phase (March 2026) — External integrations & schema design

**Original Session (EEA 2025):**
- **Date:** Thursday, 30 October 2025
- **Format:** 45 minutes of discipline panel reviews + 50 minutes of oral presentations
- **Organizers:** Dr. Simon Dedman & Dr. Guuske Tiktak

**Current Scale:** ~30,500 papers | ~14,940 PDFs acquired | 2,559 remaining | 151 techniques | 8 disciplines

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

```
elasmo_analyses/
├── docs/                                        # Documentation
│   ├── core/                                    # Project status & planning
│   ├── database/                                # Database & extraction documentation
│   ├── integrations/                            # External database integration analyses
│   │   ├── sharkipedia_integration.md           # Sharkipedia API & data overlap
│   │   ├── megamove_integration.md              # MegaMove/GSMP tracking data
│   │   ├── altmetric_integration.md             # Altmetric scoring & social impact
│   │   └── altmetric_grants_datasets.md         # Dimensions grants & datasets
│   ├── schema_proposals/                        # Proposed new column categories
│   │   ├── ecosystem_component_proposal.md      # eco_* columns (habitat, depth, realm)
│   │   ├── pressure_proposal.md                 # pr_* columns (fishing, climate, pollution)
│   │   ├── gear_proposal.md                     # gear_* columns (gear type, mitigation)
│   │   └── impact_proposal.md                   # imp_* columns (mortality, abundance, etc.)
│   ├── LLM/                                     # LLM integration
│   ├── candidates/                              # Panelist recruitment
│   ├── geographic/                              # Geographic analysis
│   ├── species/                                 # Species database
│   ├── techniques/                              # Technique classification
│   └── technical/                               # Technical guides
├── scripts/                                     # Data processing scripts
├── database/                                    # SQLite/DuckDB databases
│   └── technique_taxonomy.db                    # Technique extraction database
├── outputs/                                     # Generated outputs
│   ├── analysis/                                # Analysis CSV files
│   ├── figures/                                 # Publication-ready visualisations
│   ├── literature_review.duckdb                 # Main analytical database
│   └── remaining_downloads_for_web.csv          # Papers still needed
├── data/                                        # Input & integration data
│   ├── sharkipedia/                             # Sharkipedia API & Zenodo data
│   └── journal_quality/                         # SCImago journal matching
├── .gitignore                                   # Git ignore rules
├── README.md                                    # This file
└── CONTRIBUTING.md                              # Contribution guidelines
```

---

## Current Status (March 2026)

### Latest Updates

**✅ External Integrations Assessed** (March 2026)
- Sharkipedia: 90% species overlap, API pull complete (1,288 species, 8,494 trait measurements)
- MegaMove: Assessed as closed; GSMP GitHub repos and Movebank API as alternatives
- Altmetric/Dimensions: SRAD application submitted (awaiting approval)

**✅ Schema Extraction Pipeline Built** (March 2026)
- 4 new column categories: [Ecosystem](docs/schema_proposals/ecosystem_component_proposal.md), [Pressure](docs/schema_proposals/pressure_proposal.md), [Gear](docs/schema_proposals/gear_proposal.md), [Impact](docs/schema_proposals/impact_proposal.md)
- Automated extraction from PDFs with score-based matching and false-positive mitigation
- Evidence table for team validation (matched terms, anchors, context snippets)
- Full pipeline documentation: [Extraction Logic](docs/schema_proposals/extraction_logic.md)

**✅ Journal Quality Matching** (March 2026)
- SCImago journal data matched: 1,558 journals covering 64.7% of papers
- Theses, book chapters, and grey literature identified and categorised separately

### Completed Phases

- [x] **Phase 1: PDF Technique Extraction** (2025-10-26)
  - 12,381 PDFs processed
  - 9,503 papers with techniques (76.5% coverage)
  - 151 unique techniques identified
  - 23,307 technique mentions

- [x] **Phase 2: Analysis & Conference Materials** (2025-10-26)
  - Collaboration networks (18,633 authors)
  - Geographic analysis (73 countries)
  - AI impact assessment
  - 25+ publication-ready visualisations

- [x] **Phase 3: EEA 2025 Conference** (2025-10-30)
  - Panel session delivered
  - Expert reviews collected
  - Community feedback incorporated

### In Progress

- [ ] **Phase 4: Corpus Expansion** (2026 Q1)
  - [**Remaining Papers to Download**](https://simondedman.github.io/elasmo_analyses/remaining_downloads.html) — 2,559 papers remaining
  - PDF deduplication complete (removed 4,780 duplicates, freed ~13.5 GB)
  - Awaiting Shark-References NAS upload from Jürgen
  - ~14,940 unique PDFs acquired to date

- [ ] **Phase 5: LLM Integration** (2026 Q1-Q2)
  - Stack: Qdrant + nomic-embed-text + Ollama
  - Build conversational interface for querying corpus
  - Quality control: predatory publishers, paper mills, species misidentification

- [ ] **Phase 6: External Integrations & Schema** (2026 Q1-Q2)
  - Sharkipedia species/trait/trend data integration
  - Altmetric/Dimensions social impact and grant data (pending SRAD approval)
  - New metadata columns: ecosystem, pressure, gear, impact ([schema proposals](docs/schema_proposals/))

- [ ] **Phase 7: Manuscript & Public Release** (2026)
  - Methods paper
  - Interactive web dashboard
  - Public database release

---

## Key Results

### Database Scale

| Metric | Value |
|--------|-------|
| Papers in database | ~30,500 |
| PDFs acquired | ~14,940 unique |
| Remaining to acquire | 2,559 |
| Techniques identified | 151 |
| Disciplines | 8 |
| Species columns | 1,308 |

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
- **Status:** SRAD application submitted (March 2026, 30 business day review)
- **Value:** Social impact scores, grant linkage, dataset discovery for ~30,500 DOIs
- See [docs/integrations/altmetric_integration.md](docs/integrations/altmetric_integration.md)

---

## Schema Proposals

Four new column categories have been proposed to enrich the database beyond techniques and species. Each uses binary columns with keyword + context matching, and includes false-positive mitigation strategies.

| Category | Prefix | Columns | Proposal |
|----------|--------|---------|----------|
| Ecosystem Component | `eco_` | Realm, zone/habitat, depth | [ecosystem_component_proposal.md](docs/schema_proposals/ecosystem_component_proposal.md) |
| Pressure / Threat | `pr_` | Fishing types, climate, pollution | [pressure_proposal.md](docs/schema_proposals/pressure_proposal.md) |
| Fishing Gear | `gear_` | Gear families, modifiers, mitigation | [gear_proposal.md](docs/schema_proposals/gear_proposal.md) |
| Impact / Response | `imp_` | Mortality, abundance, stress, etc. | [impact_proposal.md](docs/schema_proposals/impact_proposal.md) |
| **Extraction Logic** | — | Pipeline documentation, validation, evidence table | [extraction_logic.md](docs/schema_proposals/extraction_logic.md) |

Automated extraction pipeline running against full corpus — see [Issue #2](https://github.com/SimonDedman/elasmo_analyses/issues/2) for the ongoing column design conversation and validation updates.

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
1. **Validate extraction results** - Check for false positives
2. **Identify missing techniques** - Review 31 techniques not found
3. **Suggest improvements** - Alternative technique names, search queries
4. **Test LLM prototypes** - Help evaluate conversational interfaces

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

*Last updated: 2026-03-10*
*Version: 3.0 — External integrations & schema design phase*
