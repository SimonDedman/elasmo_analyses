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
│   ├── EEA2025_Data_Panel_Comprehensive_Plan.md
│   ├── EEA2025_Data_Panel_Program_Timeline_Personnel.md
│   ├── Expert_Recommendations_Comprehensive.md
│   ├── Species_Lookup_Analysis_Summary.md
│   └── Database_Format_Decision.md
├── scripts/                                 # R scripts for data processing
│   ├── analyze_species_lookup.R
│   ├── clean_species_lookup.R
│   ├── generate_species_sql.R
│   ├── create_data_sheet.R
│   └── create_discipline_summary.R
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
├── outputs/                                 # Analysis outputs
│   └── discipline_summary.csv
├── .gitignore                               # Git ignore rules
├── README.md                                # This file
└── CONTRIBUTING.md                          # Contribution guidelines
```

---

## Current Status (October 2025)

### Completed ✅
- [x] 8-discipline framework defined and validated
- [x] Expert recruitment strategy developed (70+ candidates identified)
- [x] Database schema designed (DuckDB + Arrow format)
- [x] Species lookup table cleaned (1,030 species)
- [x] SQL schema files generated (1-6 of 7)
- [x] Program timeline finalized
- [x] Panel team recruited (5 confirmed speakers, 8 discipline leads)

### In Progress 🔄
- [ ] Expert recruitment for Behaviour & Trophic Ecology disciplines
- [ ] Systematic literature review execution (Weeks 2-4)
- [ ] Panel presentation materials preparation

### Upcoming ⏳
- [ ] EEA 2025 panel session (30 October 2025)
- [ ] Post-conference database refinement
- [ ] Public release of initial review (November 2025)
- [ ] Automated Shark-References integration (Q1 2026)

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

*Last updated: 2025-10-02*
*Version: 1.0*
