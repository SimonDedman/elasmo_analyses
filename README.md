# Elasmobranch Analytical Methods Review

**A systematic review of analytical techniques across elasmobranch research disciplines**

[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)

---

## Overview

This repository contains materials for the **"New Frontiers in Elasmobranch Data Analysis"** panel session at the European Elasmobranch Association (EEA) Conference 2025 in Rotterdam, Netherlands.

**Session Details:**
- **Date:** Thursday, 30 October 2025
- **Time:** 11:15 AM - 12:50 PM
- **Format:** 45 minutes of discipline panel reviews + 50 minutes of oral presentations
- **Organizers:** Dr. Simon Dedman & Dr. Guuske Tiktak

---

## Project Goals

### Primary Objectives
1. **Comprehensive Review:** Systematically document current analytical techniques across 8 major elasmobranch research disciplines
2. **Empirical Analysis:** Extract and analyze techniques from 12,381 shark science PDFs spanning 75 years (1950-2025)
3. **Expert Evaluation:** Assess strengths, weaknesses, and suitability of different approaches through specialist insight
4. **Temporal Mapping:** Identify historical trends, current methods, declining approaches, and emerging frontiers
5. **Knowledge Transfer:** Create accessible overviews valuable to both practitioners and non-specialists
6. **Network Building:** Connect researchers within and across disciplines

### Long-Term Vision
- Create a **living database** updated annually at EEA and AES conferences
- Develop **automated trend analysis** using the Shark-References database
- Build **sustainable infrastructure** for ongoing knowledge curation
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
eea_2025_data_panel/
├── docs/                                        # Documentation
│   ├── database/                                # Database & extraction documentation
│   │   ├── extraction_progress_report.md        # ⭐ PEER REVIEW DOCUMENT
│   │   ├── extraction_guide.md                  # Extraction methodology
│   │   ├── extraction_complete_summary.md       # Technical summary
│   │   ├── database_schema_design.md            # Schema documentation
│   │   └── pdf_acquisition_complete_summary.md  # PDF corpus details
│   ├── candidates/                              # Panelist recruitment
│   ├── species/                                 # Species database
│   ├── techniques/                              # Technique classification
│   ├── technical/                               # Technical guides
│   └── readme.md                                # Docs index
├── scripts/                                     # Data processing scripts
│   ├── extract_techniques_parallel.py           # ⭐ Fast parallel extraction
│   ├── extract_full_parallel.py                 # Full extraction with researchers
│   ├── build_analysis_tables.py                 # ⭐ Generate analysis CSVs
│   └── [Additional scripts for PDF acquisition, OCR, etc.]
├── database/                                    # SQLite databases
│   └── technique_taxonomy.db                    # ⭐ Main extraction database
├── outputs/                                     # Generated outputs
│   └── analysis/                                # ⭐ Analysis CSV files
│       ├── discipline_trends_by_year.csv        # Discipline trends 1950-2025
│       ├── technique_trends_by_year.csv         # Technique adoption over time
│       ├── data_science_segmentation.csv        # DATA cross-cutting analysis
│       ├── top_techniques.csv                   # 151 techniques ranked
│       ├── discipline_cooccurrence_matrix.csv   # Discipline overlap
│       ├── summary_statistics.csv               # Overall stats
│       └── discipline_summary.csv               # Discipline totals
├── data/                                        # Input data files
│   ├── Techniques DB for Panel Review_UPDATED.xlsx  # ⭐ 182 reviewed techniques
│   ├── master_techniques.csv                    # Original 208 techniques
│   └── [Species lookups, geographic data]
├── .gitignore                                   # Git ignore rules
├── README.md                                    # This file
└── CONTRIBUTING.md                              # Contribution guidelines
```

**⭐ = Key files for review and analysis**

---

## Current Status (October 2025)

### ✅ Phase 1: PDF Technique Extraction - COMPLETE (2025-10-26)

**Corpus:** 12,381 shark science PDFs (1950-2025)
**Extracted:** 9,503 papers with techniques (76.5% coverage)
**Techniques found:** 151 unique techniques (83% of 182 searched)
**Total mentions:** 23,307 technique occurrences

**Key Results:**
- **Genetics dominates** - 85% of papers use genetic techniques
- **Data Science pervasive** - 48% of papers use data science techniques
- **Cross-cutting DATA** - 70.5% of DATA papers integrate with other disciplines
- **STRUCTURE software** - Found in 80% of papers (7,535 papers)
- **Average:** 2.5 techniques per paper

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

**For detailed review:** See [`docs/database/extraction_progress_report.md`](docs/database/extraction_progress_report.md)

**Analysis outputs:** See `outputs/analysis/*.csv` (7 files ready for visualization)

---

### ✅ Completed Phases

- [x] **Phase 0: Planning & Documentation** (Complete)
  - [x] 8-discipline framework defined and validated
  - [x] Database schema designed
  - [x] Program timeline finalized

- [x] **Phase 0.5: Conference Materials** (Complete 2025-10-03)
  - [x] Expert recruitment (243 candidates identified)
  - [x] Conference attendance integrated (EEA 2013-2023, AES 2015, SI2022)
  - [x] EEA 2025 attendee list processed (151 unique attendees)
  - [x] Analytical techniques extracted from presentations (46 unique)
  - [x] Panel team recruited (5 confirmed speakers)

- [x] **Phase 1: Technique Database Compilation** (Complete 2025-10-13)
  - [x] Master techniques database created: 208 techniques
  - [x] Literature review expansion completed
  - [x] Database files ready for panelist review
  - [x] All techniques have search queries for Shark-References automation

- [x] **Phase 1.5: PDF Corpus Acquisition** (Complete 2025-10-25)
  - [x] 12,381 PDFs acquired and organized by year
  - [x] 631 duplicates removed
  - [x] OCR processing completed for scanned papers
  - [x] Metadata extraction and organization

- [x] **Phase 2: PDF Technique Extraction** (Complete 2025-10-26)
  - [x] Parallel extraction across 11 CPU cores
  - [x] 9,503 papers successfully processed
  - [x] 151 techniques identified in corpus
  - [x] Cross-cutting DATA discipline logic implemented
  - [x] Analysis tables generated (discipline trends, technique trends)
  - [x] Peer review documentation created

---

### 🔄 In Progress

- [ ] **Phase 2.5: Panelist Review of Extraction Results**
  - [ ] Distribute extraction progress report to colleagues
  - [ ] Validate top techniques for false positives (esp. STRUCTURE)
  - [ ] Review missing techniques (31 not found)
  - [ ] Assess bias and completeness
  - [ ] Approve cross-cutting DATA definition

---

### ⏳ Upcoming

- [ ] **Phase 3: Researcher Network Extraction** (Post-schema fix)
  - [ ] Fix database schema issues
  - [ ] Re-run full extraction for author/collaboration data
  - [ ] Build researcher collaboration networks
  - [ ] Link researchers to techniques and disciplines

- [ ] **Phase 4: Visualization & Analysis**
  - [ ] Create tree graphic showing DATA connections to other disciplines
  - [ ] Generate discipline trend visualizations
  - [ ] Create technique adoption timelines
  - [ ] Build interactive dashboards

- [ ] **Phase 5: EEA 2025 Conference** (30 October 2025)
  - [ ] Present findings to elasmobranch community
  - [ ] Collect feedback and validation
  - [ ] Identify additional techniques and gaps

- [ ] **Phase 6: Public Release** (November 2025)
  - [ ] Finalize database and documentation
  - [ ] Create public-facing visualizations
  - [ ] Publish methodology and findings

---

## Data Extraction Methodology

### Technique Matching
- **Pattern matching:** Case-insensitive regex with word boundaries
- **Search space:** 182 techniques (priority 1 & 2 from reviewed database)
- **Tool:** `pdftotext` for text extraction
- **Context:** 100 characters captured around each mention
- **Performance:** 25-30 PDFs/second using 11 CPU cores

### Cross-Cutting DATA Logic
Papers count for DATA discipline if they use ANY of 128 techniques marked as:
- Primary discipline = DATA (28 techniques)
- statistical_model = TRUE
- analytical_algorithm = TRUE
- inference_framework = TRUE

**Result:** 70.5% of DATA papers are cross-cutting (using data techniques in other disciplines)

### Quality Controls
✅ **Implemented:**
- PDF timeout (10s) to skip corrupted files
- Text length limit (500KB) to skip scanned books
- Duplicate detection and removal
- Resume capability (skip already-processed papers)
- Batch database writes for data integrity

⚠️ **Limitations:**
- Filename-based author extraction only
- No species linkage yet (detected but not analyzed)
- Researcher network incomplete (schema issues to be fixed)

---

## Key Documentation

### For Peer Review
- **[Extraction Progress Report](docs/database/extraction_progress_report.md)** - Comprehensive review document for colleagues
  - Methodology, results, bias assessment
  - Data quality checks and validation suggestions
  - Reviewer checklist and action items

### For Technical Understanding
- **[Extraction Guide](docs/database/extraction_guide.md)** - How to run the extraction scripts
- **[Extraction Complete Summary](docs/database/extraction_complete_summary.md)** - Technical details and metrics
- **[Database Schema Design](docs/database/database_schema_design.md)** - SQLite structure and relationships

### For Analysis
- **Analysis CSVs:** `outputs/analysis/` (7 files ready for visualization)
- **Database:** `database/technique_taxonomy.db` (SQLite, queryable)

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

# View technique trends
head outputs/analysis/technique_trends_by_year.csv

# View DATA segmentation
head outputs/analysis/data_science_segmentation.csv
```

### Run Analysis Builder
```bash
# Regenerate analysis tables
./venv/bin/python scripts/build_analysis_tables.py
```

---

## EEA 2025 Conference Distribution

Analysis of 106 presentations at EEA 2025 by discipline validates our 8-discipline framework.

### Top Techniques by Conference Mentions
- IUCN Red List Assessment: 16 presentations
- Acoustic Telemetry: 11 presentations
- Machine Learning: 9 presentations
- MPA Design: 7 presentations
- Age & Growth, Reproduction: 7 presentations each

### Top Techniques by Literature Corpus
- STRUCTURE (genetic analysis software): 7,535 papers
- Connectivity (population/genetic): 1,068 papers
- Stock Assessment: 984 papers
- Parasitology: 927 papers
- Tourism: 777 papers

---

## How to Contribute

We welcome contributions from the elasmobranch research community!

**Current review needs:**
1. **Validate extraction results** - Check for false positives (esp. STRUCTURE)
2. **Identify missing techniques** - Review 31 techniques not found in corpus
3. **Assess bias** - Evaluate discipline representation and completeness
4. **Suggest improvements** - Alternative technique names, search queries

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

**Panel Leaders:**
- Dr. Simon Dedman - simondedman@gmail.com - [GitHub](https://github.com/SimonDedman)
- Dr. Guuske Tiktak

**External Collaborators:**
- Jürgen Pollerspöck & Nico Straube - [Shark-References Database](https://shark-references.com/)

---

## Acknowledgments

This project builds upon:
- **12,381 shark science papers** by thousands of researchers worldwide (1950-2025)
- **Shark-References database** - Comprehensive elasmobranch literature repository
- **EEA and AES conferences** - Decades of community knowledge sharing
- **Panel experts and contributors** - Discipline-specific insights and validation

---

*Last updated: 2025-10-26*
*Version: 2.0 - PDF Technique Extraction Complete (9,503 papers analyzed)*
