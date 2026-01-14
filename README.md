# Elasmobranch Analytical Methods Review

**A systematic review of analytical techniques across elasmobranch research disciplines**

[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)

---

## Overview

This repository contains materials for the **"New Frontiers in Elasmobranch Data Analysis"** project, initially presented at the European Elasmobranch Association (EEA) Conference 2025 in Rotterdam, Netherlands.

**Project Status:** Post-conference development phase (January 2026)

**Original Session (EEA 2025):**
- **Date:** Thursday, 30 October 2025
- **Format:** 45 minutes of discipline panel reviews + 50 minutes of oral presentations
- **Organizers:** Dr. Simon Dedman & Dr. Guuske Tiktak

---

## Project Goals

### Primary Objectives
1. **Comprehensive Review:** Systematically document current analytical techniques across 8 major elasmobranch research disciplines
2. **Empirical Analysis:** Extract and analyze techniques from ~13,000 shark science PDFs spanning 75+ years (1950-2026)
3. **Expert Evaluation:** Assess strengths, weaknesses, and suitability of different approaches through specialist insight
4. **Temporal Mapping:** Identify historical trends, current methods, declining approaches, and emerging frontiers
5. **Knowledge Transfer:** Create accessible overviews valuable to both practitioners and non-specialists
6. **Network Building:** Connect researchers within and across disciplines

### Long-Term Vision
- Create a **living database** updated annually at EEA and AES conferences
- Develop **automated trend analysis** using the Shark-References database
- Build **conversational AI interface** for querying the knowledge base (see [LLM Integration](#llm-integration))
- Integrate with **Sharkipedia**, **Megamove**, and other elasmobranch databases
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
│   ├── database/                                # Database & extraction documentation
│   │   ├── extraction_progress_report.md        # Peer review document
│   │   ├── extraction_complete_summary.md       # Technical summary
│   │   ├── database_schema_design.md            # Schema documentation
│   │   └── pdf_acquisition_complete_summary.md  # PDF corpus details
│   ├── LLM/                                     # LLM integration (NEW!)
│   │   ├── llm_integration_roadmap.md           # LLM roadmap
│   │   └── notebooklm_alternatives_summary.md   # Platform comparison
│   ├── candidates/                              # Panelist recruitment
│   ├── geographic/                              # Geographic analysis
│   ├── species/                                 # Species database
│   ├── techniques/                              # Technique classification
│   ├── technical/                               # Technical guides
│   └── readme.md                                # Docs index
├── scripts/                                     # Data processing scripts
│   ├── extract_techniques_parallel.py           # Fast parallel extraction
│   ├── build_analysis_tables.py                 # Generate analysis CSVs
│   └── [Additional scripts for PDF acquisition, OCR, etc.]
├── database/                                    # SQLite databases
│   └── technique_taxonomy.db                    # Main extraction database
├── outputs/                                     # Generated outputs
│   ├── analysis/                                # Analysis CSV files
│   │   ├── discipline_trends_by_year.csv        # Discipline trends 1950-2025
│   │   ├── technique_trends_by_year.csv         # Technique adoption over time
│   │   ├── top_techniques.csv                   # 151 techniques ranked
│   │   └── summary_statistics.csv               # Overall stats
│   ├── figures/                                 # Publication-ready visualizations
│   ├── panel_reports/                           # Expert panel materials
│   └── abstract_reviews/                        # Conference abstract reviews
├── data/                                        # Input data files
├── .gitignore                                   # Git ignore rules
├── README.md                                    # This file
└── CONTRIBUTING.md                              # Contribution guidelines
```

---

## Current Status (January 2026)

### Latest Updates

**✅ EEA 2025 Conference Complete** (October 2025)
- Panel session delivered successfully
- Expert feedback incorporated
- Community interest in living database confirmed

**✅ PDF Corpus Expansion Ongoing**
- Current: ~13,000 papers (1950-2026)
- Adding 2026 publications from Shark-References
- Target: Complete coverage through 2026

**🔄 LLM Integration In Progress** (NEW!)
- Evaluating local RAG solutions for conversational interface
- See [docs/LLM/](docs/LLM/) for platform comparison
- Goal: "Talk to" the shark science knowledge base

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
  - 25+ publication-ready visualizations

- [x] **Phase 3: EEA 2025 Conference** (2025-10-30)
  - Panel session delivered
  - Expert reviews collected
  - Community feedback incorporated

### In Progress

- [ ] **Phase 4: Corpus Expansion** (2026 Q1)
  - Adding 2026 publications
  - Expanding metadata (species, ocean basin, habitat)
  - Database integration with Sharkipedia/Megamove

- [ ] **Phase 5: LLM Integration** (2026 Q1-Q2)
  - Build conversational interface
  - Enable natural language queries
  - Add metadata filtering

- [ ] **Phase 6: Manuscript & Public Release** (2026)
  - Methods paper
  - Interactive web dashboard
  - Public database release

---

## Key Results

### PDF Technique Extraction

**Corpus:** 12,381 shark science PDFs (1950-2025)
**Coverage:** 9,503 papers with techniques (76.5%)
**Techniques:** 151 unique methods identified

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
| BEH (Behavior) | 265 | 2.8% |

**Key Findings:**
- **Genetics dominates** - 85% of papers use genetic techniques
- **Data Science pervasive** - 48% use statistical/ML methods
- **Cross-cutting DATA** - 70.5% of DATA papers integrate with other disciplines
- **STRUCTURE software** - Most common tool (7,535 papers, 80%)

---

## LLM Integration

We are developing a conversational AI interface to enable researchers to query the knowledge base naturally:

> "What techniques are used for age determination in deep-sea sharks?"
> "Which countries have published most on acoustic telemetry since 2015?"
> "Show me papers combining eDNA and stable isotope analysis"

### Approach

**Recommended stack for 13,000+ PDFs:**
- **Vector Database:** Qdrant (open-source, scalable)
- **Embeddings:** nomic-embed-text (local, free)
- **LLM:** Ollama with Llama 3.1 or Qwen2.5 (local, private)
- **Interface:** Open WebUI or custom Gradio app

**Why not Google NotebookLM?**
- Limited to 50-300 sources per notebook
- Cannot query across notebooks
- Not suitable for corpus-scale analysis

See [docs/LLM/notebooklm_alternatives_summary.md](docs/LLM/notebooklm_alternatives_summary.md) for full comparison.

---

## Key Documentation

### Project Overview
- **[docs/readme.md](docs/readme.md)** - Documentation index
- **[docs/core/project_status_comprehensive.md](docs/core/project_status_comprehensive.md)** - Complete project summary

### Database & Extraction
- **[docs/database/database_schema_design.md](docs/database/database_schema_design.md)** - Schema documentation
- **[docs/database/extraction_complete_summary.md](docs/database/extraction_complete_summary.md)** - Extraction results

### LLM Integration (NEW!)
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
- David Ruiz Garcia
- Elena Fernández Corredor
- Jürgen Pollerspöck & Nico Straube ([Shark-References](https://shark-references.com/))

---

## Acknowledgments

This project builds upon:
- **~13,000 shark science papers** by thousands of researchers worldwide (1950-2026)
- **Shark-References database** - Comprehensive elasmobranch literature repository
- **EEA and AES conferences** - Decades of community knowledge sharing
- **Panel experts and contributors** - Discipline-specific insights and validation

---

*Last updated: 2026-01-14*
*Version: 2.1 - Post-EEA 2025, LLM integration phase*
