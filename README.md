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

- [x] **Database Design Updates** (2025-10-03)
  - [x] Added `n_studies` column for review/meta-analysis papers
  - [x] Updated superorders to include Holocephali (chimaeras) - 3 total
  - [x] Created 3-tier method classification structure
  - [x] Added `paper_id` column for multi-discipline papers
  - [x] Documented multi-discipline paper handling (duplicate row approach)
  - [x] Species lookup table cleaned (1,030 species; 178 pending from Weigmann)

### In Progress 🔄
- [ ] **Phase 1: Infrastructure Setup**
  - [ ] Database schema implementation (SQL generation)
  - [ ] Species list completion (awaiting Weigmann complete list: 178 missing)
  - [ ] Shark-References automation permission request

- [ ] **Phase 2: Expert Recruitment & Materials**
  - [ ] Panel presentation materials preparation
  - [ ] Expert discipline assignments refinement
  - [ ] Web-based expert search using technique keywords

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

### Analytical Techniques Identified

**3-Tier Method Classification** (from EEA 2025 presentations):

**Total Unique Techniques**: 46 (33 parent techniques + 13 subtechniques)

**By Discipline**:
- **Behaviour**: 4 techniques (Behavioural Observation, Cognition, Sensory Biology, Social Networks)
- **Biology**: 7 techniques (Age & Growth, Health, Histology, Morphology, Physiology, Reproduction)
- **Conservation**: 7 techniques (Human Dimensions, IUCN Assessment, Participatory Science, Policy, Tourism, Trade)
- **Data Science**: 6 techniques (Bayesian Methods, Data Integration, Machine Learning, Meta-Analysis, Time Series)
- **Fisheries**: 2 techniques (Bycatch Assessment, Mark-Recapture)
- **Genetics**: 4 techniques (Genomics, Phylogenetics, Population Genetics, eDNA)
- **Movement**: 5 techniques (Connectivity, Habitat Modeling, MPA Design, Movement Modeling, Telemetry)
- **Trophic**: 2 techniques (Diet Analysis, Stable Isotopes)

**Most Mentioned**:
- Acoustic Telemetry: 13 mentions
- IUCN Red List Assessment: 10 mentions (7 abstracts, 10 titles)
- MPA Design: 7 mentions
- Machine Learning: 7 mentions

**Data Sources**:
- Titles: 63 presentations, 93 technique mentions (77.8% coverage)
- Abstracts: 112 files, 53 technique mentions (37.5% coverage)
- Combined: 46 unique techniques

See `outputs/method_hierarchy_table.csv` for complete 3-tier classification.

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

*Last updated: 2025-10-03*
*Version: 1.2 - Phase 1 Complete + Analytical Techniques Compiled*
