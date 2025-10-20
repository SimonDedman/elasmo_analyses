---
editor_options:
  markdown:
    wrap: 72
---

# Project Summary: EEA 2025 Data Panel

## At a Glance

**Project:** Systematic Literature Review of Emerging Technologies in Elasmobranch Research
**Conference:** American Elasmobranch Society (AES) Annual Meeting 2025
**Format:** Data Panel (95 min: 50 min talks + 45 min expert panel)
**Lead:** Simon Dedman
**Status:** Phase 0 - Planning Complete ✅

---

## Quick Navigation

| What do you need? | Go here |
|-------------------|---------|
| **Understand the project** | [README.md](../README.md) |
| **Review overall plan** | [EEA2025_Data_Panel_Comprehensive_Plan.md](EEA2025_Data_Panel_Comprehensive_Plan.md) |
| **Classify a paper** | [Discipline_Structure_Analysis.md](Discipline_Structure_Analysis.md) |
| **Find an expert** | [Expert_Recommendations_Comprehensive.md](Expert_Recommendations_Comprehensive.md) |
| **Set up database** | [Database_Schema_Design.md](Database_Schema_Design.md) |
| **Run automated search** | [Shark_References_Automation_Workflow.md](Shark_References_Automation_Workflow.md) |
| **Python script** | [../scripts/shark_references_search.py](../scripts/shark_references_search.py) |
| **R script** | [../scripts/shark_references_search.R](../scripts/shark_references_search.R) |

---

## Core Objectives

### 1. Systematic Literature Review
- **Scope:** Emerging analytical technologies and approaches in chondrichthyan research
- **Type:** Mixed-method umbrella/scoping/state-of-the-art review (PRISMA-SCR)
- **Primary Database:** Shark-References (>30,000 chondrichthyan-specific papers)
- **Automation:** Python & R scripts for batch searching

### 2. Expert Panel Discussion
- **Disciplines:** 8 refined analytical-methods-focused categories
- **Experts:** 71+ identified, tier-based recruitment strategy
- **Format:** 5-6 minutes per discipline for emerging technology perspectives

### 3. Database Development
- **Schema:** Wide sparse table (~1,652 columns)
- **Format:** DuckDB + Parquet (optimized for sparse boolean data)
- **Columns:** Binary classification for disciplines, species, methods, geography
- **Collaboration:** Git LFS for Parquet version control

---

## 8 Refined Disciplines

1. **Biology, Life History, & Health**
   - Reproduction, growth, aging, stress physiology, disease, telomeres

2. **Behaviour & Sensory Ecology**
   - Vision, electroreception, olfaction, magnetoreception, social behavior, cognition

3. **Trophic & Community Ecology**
   - Stable isotopes, diet analysis, food webs, energy flow, niche partitioning

4. **Genetics, Genomics, & eDNA**
   - Population genetics, genomic sequencing, eDNA, phylogenetics, conservation genetics

5. **Movement, Space Use, & Habitat Modeling**
   - Telemetry (acoustic, satellite), SDMs, home range, migration, MPA design

6. **Fisheries, Stock Assessment, & Management**
   - Stock assessment, CPUE, bycatch, mortality, harvest strategies

7. **Conservation Policy & Human Dimensions**
   - CITES, MPA policy, stakeholder engagement, ecosystem services

8. **Data Science & Integrative Methods**
   - Machine learning, Bayesian modeling, GAMs, ensemble models, data integration

---

## Database Schema Summary

### Core Design Principle
**Multi-label binary classification** to capture cross-cutting research

### Column Categories

| Prefix | Category | Count | Example | Purpose |
|--------|----------|-------|---------|---------|
| - | Core metadata | 20 | `study_id`, `doi`, `year` | Bibliographic data |
| `d_` | Discipline | 8 | `d_genetics_genomics` | Multi-discipline papers |
| `auth_` | Author nation | 197 | `auth_us`, `auth_au` | Research capacity |
| `b_` | Ocean basin | 9 | `b_north_atlantic` | Study biogeography |
| `sb_` | Sub-basin | 66 | `sb_california_current` | Fine-scale regions |
| `so_` | Superorder | 2 | `so_selachimorpha` | Sharks vs rays |
| `sp_` | Species | ~1,200 | `sp_carcharodon_carcharias` | Species-specific trends |
| `a_` | Analysis | ~150 | `a_acoustic_telemetry` | Method trends |

**Total: ~1,652 columns**

### Why This Works
- **Parquet compression:** >90% size reduction for sparse boolean data
- **DuckDB queries:** Columnar engine optimized for wide sparse tables
- **Simple SQL:** No complex JOINs needed for multi-label queries
- **Future-proof:** Add new columns without schema migration

---

## Automation Workflow

### Shark-References Search Strategy

**Database:** https://shark-references.com (>30,000 refs)

**Critical Limitations:**
- 3-letter indexing only (`+tel` matches `telemetry`)
- 2,000 reference maximum per search
- No official API (form-based POST requests)
- Conservative rate limiting required (10-sec delays)

**Search Operators:**
```
+word         Required keyword (AND)
-word         Exclude keyword (NOT, requires + first)
word*         Wildcard prefix matching
"exact"       Exact phrase match
word1 @10 word2   Proximity search (within 10 words)
```

**Example Search Terms:**
```
Movement & Spatial:
  +telemetry +acoustic
  +satellite +tracking
  +habitat +model*

Genetics & Genomics:
  +population +geneti*
  +genom* +sequenc*
  +eDNA +environmental
```

### Implementation
- **Python script:** `scripts/shark_references_search.py`
- **R script:** `scripts/shark_references_search.R`
- **Both include:**
  - Automated batch searching across all disciplines
  - Rate limiting (configurable delays)
  - Database integration (SQLite/DuckDB)
  - Error handling and logging

---

## Expert Recruitment

### Tier System

**Tier 1: Must Recruit** (Established, accessible, key expertise)
- Emily Meese (Trophic Ecology)
- Caroline Sullivan OR Andrew Nosal (Behaviour)
- High priority for discipline coverage

**Tier 2: Strong Candidates** (Active research, good communicators)
- Oliver Shipley (Movement + Trophic)
- Rachel Graham (Conservation + Movement)
- Cross-cutting expertise valued

**Tier 3: Senior/Busy** (High stature, may decline)
- Gregory Skomal (Movement)
- Bradley Wetherbee (Movement)
- Backup if Tier 1/2 unavailable

**Tier 4: Early Career/Assistants** (Fallback)
- Recent PhDs, postdocs
- Use if senior experts unavailable

### Total Experts Identified: 71+
- Sourced from Carrier et al. (2019), AES 2024, web research
- Contact info where available
- Cross-cutting expertise noted

---

## Timeline (5 Weeks Pre-Conference)

### Week 1: Setup & Planning ✅
- [x] Finalize discipline structure (8 refined)
- [x] Create database schema design
- [x] Develop automation scripts (Python & R)
- [x] Identify 71+ expert candidates
- [ ] Generate SQL schema from ISO/FishBase sources
- [ ] Create CSV template with all columns

### Week 2: Recruitment & Trial
- [ ] Send Tier 1 expert recruitment emails
- [ ] Begin trial literature review (n=50 per discipline)
- [ ] Refine search terms based on trial
- [ ] Contact Shark-References for automation permission

### Weeks 2-3: Batch Searching
- [ ] Execute automated searches (all disciplines)
- [ ] Download CSV results
- [ ] Import to DuckDB database

### Weeks 3-4: Processing & QC
- [ ] Parse CSVs, deduplicate
- [ ] Manual QC sample per discipline
- [ ] Identify gaps, run additional searches
- [ ] Generate summary statistics

### Week 4-5: Expert Packages
- [ ] Export discipline-specific reference lists
- [ ] Create expert review packages
- [ ] Send to confirmed panelists
- [ ] Prepare session materials

---

## Key Decisions Made

### ✅ Database Format: DuckDB + Parquet
**Rationale:** Columnar storage optimal for sparse boolean data, R/Python compatible, no server setup

### ✅ Wide Sparse Schema (~1,652 columns)
**Rationale:** Multi-label classification essential, simple queries, Parquet compresses efficiently

### ✅ Geographic Schema: 3-tier
**Rationale:** Separate author affiliation (research capacity) from study location (biogeography)

### ✅ Binarized Species (~1,200 columns)
**Rationale:** Enables species-specific trends, supports taxonomic aggregation

### ❌ Subjective Fields in Main Table
**Rationale:** key_findings/strengths/weaknesses → separate annotations table (optional)

### ✅ Automated Extraction for study_type
**Rationale:** Keywords "meta-analysis", "systematic review" in title/abstract reliably classify

---

## Deliverables

### Documentation ✅
1. Comprehensive plan (session structure, methodology, actionables)
2. Discipline structure analysis (8 refined, boundary definitions)
3. Expert recommendations (71+ experts, tier-based)
4. Database schema design (1,652 columns, DuckDB/Parquet)
5. Automation workflow (Shark-References integration)
6. Project README (complete index and quick start)

### Scripts ✅
1. Python automated search (`shark_references_search.py`)
2. R automated search (`shark_references_search.R`)

### Pending
1. SQL schema generation scripts
2. DuckDB database initialization
3. CSV template with all columns
4. Data entry interface (R Shiny or web form)
5. Automated extraction (study_type, species, methods)

---

## Next Immediate Actions

### 1. Contact Shark-References
**Email:** info@shark-references.com
**Subject:** Request permission for automated literature review
**Content:**
- Explain EEA 2025 Data Panel project scope
- Request guidance on acceptable rate limits
- Ask about bulk export options
- Offer to acknowledge database in publications

### 2. Generate SQL Schema
**Tasks:**
- Extract ISO 3166-1 country codes → `auth_*` columns (197)
- Extract FishBase chondrichthyan species → `sp_*` columns (~1,200)
- Extract NOAA LME regions → `sb_*` columns (66)
- Create SQL files in `sql/` directory

### 3. Create CSV Template
**Tasks:**
- Generate header row with all 1,652 columns
- Include example row with sample data
- Add data dictionary sheet (column definitions)
- Distribute to trial reviewers

### 4. Recruit Tier 1 Experts
**Priority Disciplines:**
- Behaviour: Caroline Sullivan OR Andrew Nosal
- Trophic: Emily Meese
- Genetics: [TBD from recommendations]
- Data Science: [TBD from recommendations]

---

## Technical Stack

### Languages
- **Python 3.x:** Automation scripts, data processing
- **R 4.x:** Database queries (duckplyr), analysis

### Databases
- **DuckDB:** In-process OLAP database
- **Parquet:** Columnar storage format

### R Packages
- `{duckdb}` - DuckDB interface
- `{duckplyr}` - dplyr with DuckDB backend
- `{httr}` - HTTP requests
- `{RSQLite}` - SQLite (fallback)
- `{readr}` - CSV I/O
- `{dplyr}` - Data manipulation

### Python Packages
- `duckdb` - DuckDB interface
- `pandas` - Data manipulation
- `requests` - HTTP requests
- `beautifulsoup4` - HTML parsing
- `sqlite3` - SQLite (fallback)

---

## Risk Mitigation

### Shark-References Blocking
**Mitigation:**
- Contact maintainers first ✅
- Use 10-second delays (conservative)
- Monitor HTTP response codes
- Fallback to manual searches if needed

### Search Results Exceed 2,000
**Mitigation:**
- Refine search terms (add year ranges)
- Split by temporal periods (pre/post 2010)
- Combine results from multiple refined searches

### Wide Schema Performance
**Mitigation:**
- DuckDB columnar engine optimized for this
- Parquet compression reduces storage >90%
- Query only needed columns (don't SELECT *)

### Expert Recruitment Failures
**Mitigation:**
- Tier-based approach (71+ candidates)
- Cross-cutting experts cover multiple disciplines
- Early career researchers as Tier 4 backup

### Database Collaboration Conflicts
**Mitigation:**
- Git LFS for Parquet version control
- Assign reviewers to non-overlapping paper sets
- Regular synchronization schedule (weekly merges)

---

## Success Metrics

### Literature Review Completeness
- **Target:** >5,000 papers identified across all disciplines
- **Coverage:** All major analytical methods represented
- **Temporal:** 2000-2025 emphasis (last 25 years)

### Expert Panel Quality
- **Target:** 6-8 experts confirmed (minimum 1 per discipline)
- **Diversity:** Geographic, career stage, expertise areas
- **Engagement:** Materials reviewed pre-conference

### Database Utility
- **Structure:** All 1,652 columns implemented and documented
- **Usability:** CSV template + DuckDB queries functional
- **Reproducibility:** Scripts run successfully for collaborators

### Session Impact
- **Attendance:** Target 50+ attendees
- **Discussion:** Lively Q&A across disciplines
- **Follow-up:** Post-conference publication planned

---

## Contact & Resources

**Project Lead:** Simon Dedman
**Repository:** [TBD - add GitHub/GitLab URL]

**Key External Resources:**
- Shark-References: https://shark-references.com
- Sharkipedia: https://www.sharkipedia.org/
- DuckDB: https://duckdb.org/
- PRISMA-SCR: http://www.prisma-statement.org/Extensions/ScopingReviews

**Documentation:**
- Main README: [`../README.md`](../README.md)
- All docs in: [`docs/`](./)

---

*Last updated: 2025-10-02*
*Status: Planning Phase Complete ✅ → Moving to Implementation Phase*
