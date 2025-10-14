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
2. **Expert Evaluation:** Assess strengths, weaknesses, and suitability of different approaches through specialist insight
3. **Temporal Mapping:** Identify historical trends, current methods, declining approaches, and emerging frontiers
4. **Knowledge Transfer:** Create accessible overviews valuable to both practitioners and non-specialists
5. **Network Building:** Connect researchers within and across disciplines

### Long-Term Vision
- Create a **living database** updated annually at EEA and AES conferences
- Develop **automated trend analysis** using the Shark-References database
- Build **sustainable infrastructure** for ongoing knowledge curation
- Establish **community-driven** annual updates

---

## The 8 Disciplines

1. **Biology, Life History, & Health** - Age/growth, reproduction, physiology, anatomy, disease, health indices
2. **Behaviour & Sensory Ecology** - Behavioral observation, social structure, sensory biology, network analysis
3. **Trophic & Community Ecology** - Diet analysis, trophic position, food webs, ecosystem roles
4. **Genetics, Genomics, & eDNA** - Population genetics, phylogenetics, genomics, environmental DNA
5. **Movement, Space Use, & Habitat Modeling** - Telemetry, movement models, species distribution models, MPAs
6. **Fisheries, Stock Assessment, & Management** - Stock assessment, CPUE standardization, bycatch, data-poor methods
7. **Conservation Policy & Human Dimensions** - IUCN assessments, policy evaluation, human-wildlife conflict, citizen science
8. **Data Science & Integrative Methods** - Statistical frameworks, machine learning, data integration, reproducibility

---

## Repository Structure

```
elasmo_analyses/
├── docs/                                    # Documentation
│   ├── Candidate_Search_Protocol.md         # Web search methodology
│   ├── Candidate_Database_Phase1_Report.md  # Phase 1 summary
│   ├── EEA2025_Data_Panel_Comprehensive_Plan.md
│   ├── Expert_Recommendations_Comprehensive.md
│   └── Species_Lookup_Analysis_Summary.md
├── scripts/                                 # Data processing scripts
│   ├── create_candidate_database_phase1.R   # Initial database creation
│   ├── integrate_all_candidates.R           # Multi-source integration
│   ├── integrate_conference_attendance.R    # Conference history
│   ├── extract_conference_attendance_simple.sh  # PDF text extraction
│   ├── extract_si2022_attendance.R          # SI2022 video parsing
│   ├── search_abstracts_simple.sh           # Abstract name search
│   ├── update_attendee_list_missing_names.R # Attendee list updates
│   ├── classify_unclassified.R              # Discipline assignment
│   ├── extract_techniques_from_titles.R     # Title technique extraction
│   ├── extract_techniques_from_abstracts.sh # Abstract technique extraction
│   ├── parse_techniques_from_abstracts.R    # Structure abstract data
│   ├── create_tiered_technique_classification.R  # 3-tier method hierarchy
│   ├── add_presentation_status_to_attendees.R  # Cross-reference status
│   └── consolidate_attendee_duplicates.R    # Deduplicate attendees
├── sql/                                     # Database schema SQL files
│   ├── 01_create_core_table.sql
│   ├── 02_add_discipline_columns.sql
│   ├── 03_add_country_columns.sql
│   ├── 04_add_basin_columns.sql
│   ├── 05_add_superorder_columns.sql
│   └── 06_add_species_columns.sql
├── data/                                    # Data files (see .gitignore)
│   ├── species_common_lookup_cleaned.csv
│   └── lookup_geographic_distribution.csv
├── outputs/                                 # Generated outputs (.gitignored)
│   ├── candidate_database_phase1.csv        # Main candidate database (243 candidates)
│   ├── attendee_list_consolidated.csv       # Consolidated attendee list (151 unique)
│   ├── conference_attendance_summary.csv    # Historical attendance
│   ├── analytical_techniques_by_discipline.csv  # Technique compilation (46 unique)
│   ├── method_hierarchy_table.csv           # 3-tier method classification
│   ├── abstracts_technique_counts.csv       # Unique techniques per presentation
│   ├── analytical_techniques_report.md      # Technique extraction findings
│   └── attendee_presentation_status_report.md  # Presentation status report
├── .gitignore                               # Git ignore rules
├── README.md                                # This file
└── CONTRIBUTING.md                          # Contribution guidelines
```

---

## Current Status (October 2025)

### Completed ✅
- [x] **Phase 0: Planning & Documentation** (Complete)
  - [x] 8-discipline framework defined and validated
  - [x] Database schema designed (3-tier method classification, 3 superorders, ~1,625 columns)
  - [x] Program timeline finalized
  - [x] Documentation structure created

- [x] **Phase 0.5: Conference Materials** (Complete 2025-10-03)
  - [x] Expert recruitment strategy developed (243 candidates identified across 8 disciplines)
  - [x] Candidate database created (Phase 1: 243 candidates)
  - [x] Conference attendance integrated (EEA 2013-2023, AES 2015, SI2022)
  - [x] EEA 2025 attendee list processed and integrated (151 unique attendees)
  - [x] Missing attendee names resolved via abstract search (75% success rate)
  - [x] Presentation status added to attendee list (48 presenting, 19 poster, 12 panel, 2 organiser)
  - [x] Duplicate attendees consolidated (155 → 151)
  - [x] **Analytical techniques extracted from presentations**:
    - 93 techniques from 63 presentation titles (77.8% coverage)
    - 53 techniques from 112 full abstracts (37.5% coverage)
    - 46 unique techniques compiled (33 parent + 13 subtechniques)
    - 3-tier method hierarchy created (method_families → parent_techniques → subtechniques)
  - [x] Panel team recruited (5 confirmed speakers)

- [x] **Phase 1: Technique Database Compilation** (Complete 2025-10-13)
  - [x] **Master techniques database created: 208 techniques** across 8 disciplines
  - [x] Initial compilation from EEA 2025 abstracts (40 techniques)
  - [x] Gap analysis and planned techniques added (79 techniques)
  - [x] **Literature review expansion** (+79 techniques via systematic review)
    - Web searches for SDM methods, stock assessment, home range analysis
    - Domain knowledge integration (textbooks, R packages, FAO manuals)
    - Hierarchical expansion of parent techniques
  - [x] **Database files ready for panelist review**:
    - `data/master_techniques.csv` (208 techniques, 12 fields)
    - `data/Techniques DB for Panel Review.xlsx` (3 sheets, ready to edit)
    - Complete documentation suite (5 markdown files)
  - [x] All techniques have search queries for Shark-References automation
  - [x] 40 techniques validated by EEA 2025 conference presentations

- [x] **Database Design Updates** (2025-10-03)
  - [x] Added `n_studies` column for review/meta-analysis papers
  - [x] Updated superorders to include Holocephali (chimaeras) - 3 total
  - [x] Created 3-tier method classification structure
  - [x] Added `paper_id` column for multi-discipline papers
  - [x] Documented multi-discipline paper handling (duplicate row approach)
  - [x] Species lookup table cleaned (1,030 species; 178 pending from Weigmann)

### In Progress 🔄
- [ ] **Phase 2: Panelist Review** (Week 1-2)
  - [ ] Distribute technique database to 8 discipline leads
  - [ ] Collect reviewed files with edits
  - [ ] Validate search queries on Shark-References (sample testing)

- [ ] **Phase 3: Database Finalization** (Week 3-4)
  - [ ] Consolidate edits from all discipline leads
  - [ ] Resolve flagged issues and conflicts
  - [ ] Create final approved version
  - [ ] Import to SQLite database

- [ ] **Phase 4: Infrastructure Setup**
  - [ ] Database schema implementation (SQL generation)
  - [ ] Species list completion (awaiting Weigmann complete list: 178 missing)
  - [ ] Shark-References automation permission request

### Upcoming ⏳
- [ ] Complete Weigmann species list integration (178 species pending) - **BLOCKING I1.3**
- [ ] Shark-References batch literature searches (post-approval)
- [ ] Systematic literature review execution
- [ ] Web-based candidate search for discipline gaps
- [ ] EEA 2025 panel session (30 October 2025)
- [ ] Post-conference database refinement
- [ ] Public release of initial review (November 2025)

---

## EEA 2025 Conference Distribution

Analysis of 106 presentations at EEA 2025 by discipline:

| Discipline | Presentations | Posters | Panel Talk |
|------------|--------------|---------|------------|
| **1. Biology, Life History, & Health** | 15 | 3 | ✓ 10 min |
| **2. Behaviour & Sensory Ecology** | 0 | 0 | - |
| **3. Trophic & Community Ecology** | 2 | 0 | - |
| **4. Genetics, Genomics, & eDNA** | 11 | 0 | ✓ 10 min |
| **5. Movement, Space Use, & Habitat Modeling** | 31 | 2 | ✓ 10 min |
| **6. Fisheries, Stock Assessment, & Management** | 17 | 6 | - |
| **7. Conservation Policy & Human Dimensions** | 12 | 3 | ✓ 10 min |
| **8. Data Science & Integrative Methods** | 3 | 2 | ✓ 10 min |

This distribution validates our 8-discipline framework and informs panel time allocation.

### Analytical Techniques Database

**Current Status: 208 Techniques Ready for Panelist Review**

**Compilation Sources**:
- EEA 2025 conference presentations: 40 techniques with empirical validation
- Shark-References planned searches: 79 techniques from literature boundaries
- Gap analysis: 8 critical additions (histology, morphometrics, video, CKMR, etc.)
- Literature review expansion (2025-10-13): +79 techniques via systematic review
  - Web searches: SDM methods, stock assessment, home range analysis
  - Domain knowledge: Standard textbook methods, R packages, FAO manuals
  - Hierarchical expansion: Sub-techniques added to parent methods

**Total Unique Techniques**: 208 (64 parent techniques + 144 sub-techniques)

**By Discipline (Updated 2025-10-13)**:
- **Fisheries** (FISH): 34 techniques - Stock assessment (11), data-poor methods (7), CPUE (4), bycatch (4), ecosystem-based (3)
- **Data Science** (DATA): 32 techniques - Machine learning (9), Bayesian (7), statistical (7), integration (7), time series (2)
- **Movement** (MOV): 31 techniques - Habitat modeling/SDM (8), telemetry (5), movement analysis (13), spatial conservation (5)
- **Biology** (BIO): 28 techniques - Age & growth (6), reproduction (7), morphology (4), physiology (6), health (5)
- **Genetics** (GEN): 24 techniques - Population genetics (9), genomics (6), eDNA (4), phylogenetics (2), applied (3)
- **Behaviour** (BEH): 20 techniques - Observation (10), sensory biology (5), social (1), cognition (4)
- **Trophic** (TRO): 20 techniques - Diet analysis (7), food webs/community (7), foraging/energetics (6)
- **Conservation** (CON): 19 techniques - Assessment (4), policy (4), human dimensions (6), trade/participatory (3), tourism (2)

**Top Techniques by EEA 2025 Mentions**:
- IUCN Red List Assessment: 16 presentations
- Acoustic Telemetry: 11 presentations
- Machine Learning: 9 presentations
- MPA Design: 7 presentations
- Age & Growth, Reproduction: 7 presentations each

**Database Files**:
- `data/master_techniques.csv` - Main CSV file (208 rows, 12 columns)
- `data/Techniques DB for Panel Review.xlsx` - Excel file for panelist editing
- `docs/README_FOR_PANELISTS.md` - Instructions for panelist review
- `docs/MASTER_TECHNIQUES_CSV_README.md` - Complete CSV documentation
- `docs/Expansion_Summary_Report.md` - Details of literature review expansion

See documentation for complete hierarchies and search queries.

### Candidate Database Status

**Total Candidates**: 243 (as of 2025-10-03)

**Data Sources Integrated**:
- Final Speakers EEA 2025: 99 candidates
- Panel team roster: 8 candidates
- Expert recommendations: 63 candidates
- EEA 2025 attendee list: 155 candidates
- Conference history: 22 candidates with attendance data

**Completeness**:
- With disciplines: 95 (39%)
- With institutions: 217 (90%)
- With emails: 169 (70%)
- Attending EEA 2025: 187 (77%)
- With conference history: 22 (9%)

---

## Quick Start

### View the Program Timeline
See [`docs/EEA2025_Data_Panel_Program_Timeline_Personnel.md`](docs/EEA2025_Data_Panel_Program_Timeline_Personnel.md) for complete session schedule and team roster.

### Review the Comprehensive Plan
See [`docs/EEA2025_Data_Panel_Comprehensive_Plan.md`](docs/EEA2025_Data_Panel_Comprehensive_Plan.md) for complete methodology and timeline.

### Explore the Database Schema
SQL files in [`sql/`](sql/) directory contain the complete literature review database schema.

---

## How to Contribute

We welcome contributions from the elasmobranch research community! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:

- Suggesting new analytical techniques
- Reporting corrections or updates
- Contributing to discipline reviews
- Joining as a panel expert for future conferences

---

## Data Sources

### Primary Data
- **Shark-References Database** - Comprehensive elasmobranch literature database with fulltext search
- **Expert Contributions** - Discipline-specific systematic reviews from panel experts
- **EEA 2025 Conference Data** - 106 presentations analyzed for discipline distribution

### Reference Materials
- Carrier et al. (2019) *Shark Research: Emerging Technologies and Applications*
- AES 2024 (JMIH Pittsburgh) conference proceedings
- Weigmann (2016) Annotated Checklist of Chondrichthyes

---

## Citation

If you use materials from this project, please cite:

```
Dedman, S., Tiktak, G., et al. (2025). Elasmobranch Analytical Methods Review.
European Elasmobranch Association Conference 2025, Rotterdam, Netherlands.
https://github.com/SimonDedman/elasmo_analyses
```

---

## License

This work is licensed under a [Creative Commons Attribution 4.0 International License](https://creativecommons.org/licenses/by/4.0/).

You are free to:
- **Share** - copy and redistribute the material in any medium or format
- **Adapt** - remix, transform, and build upon the material for any purpose

Under the following terms:
- **Attribution** - You must give appropriate credit and indicate if changes were made

---

## Contact

**Panel Leaders:**
- Dr. Simon Dedman - [GitHub](https://github.com/SimonDedman)
- Dr. Guuske Tiktak

**External Collaborators:**
- Jürgen Pollerspöck & Nico Straube - [Shark-References Database](https://shark-references.com/)

---

## Acknowledgments

This project builds upon decades of elasmobranch research by thousands of scientists worldwide. We are grateful to:

- All panel experts and contributors
- EEA and AES conference organizers
- Shark-References database curators
- The global elasmobranch research community

---

*Last updated: 2025-10-13*
*Version: 1.3 - Technique Database Expansion Complete (208 techniques)*
