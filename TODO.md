# EEA 2025 Data Panel - Master TODO List

**Last Updated:** 2025-10-03
**Project Status:** Phase 0 Complete → Phase 2 Analytical Techniques Complete → Implementation Phase

---

## Legend

**Owner Codes:**
- **SD** = Simon Dedman (Project Lead)
- **GT** = Guuske Tiktak (Co-lead/Reviewer)
- **Assistant** = Claude Code / Automated systems
- **Panelist** = Expert panel members (TBD)
- **Community** = Open contribution / Collaborative

**Status:**
- ⏳ Pending
- 🔄 In Progress
- ✅ Complete
- ❌ Blocked
- ⚠️ Needs Review

**Priority:**
- 🔴 Critical (blocks other tasks)
- 🟡 High (needed soon)
- 🟢 Medium (important but not urgent)
- 🔵 Low (nice to have)

---

## Phase 0: Planning & Documentation ✅ COMPLETE

| ID | Task | Owner | Status | Priority | Dependencies | Notes |
|----|------|-------|--------|----------|--------------|-------|
| P0.1 | Finalize 8-discipline structure | SD | ✅ | 🔴 | - | Complete |
| P0.2 | Create comprehensive plan document | SD + Assistant | ✅ | 🔴 | P0.1 | Complete |
| P0.3 | Identify 71+ expert candidates | SD + Assistant | ✅ | 🟡 | P0.1 | Complete: 243 candidates |
| P0.4 | Design database schema | SD + Assistant | ✅ | 🔴 | P0.1 | Complete: Updated 2025-10-03 |
| P0.5 | Develop automation scripts (Python & R) | Assistant | ✅ | 🟡 | - | Complete |
| P0.6 | Create project documentation structure | Assistant | ✅ | 🟡 | P0.4 | Complete |

## Phase 0.5: Conference Materials ✅ COMPLETE

| ID | Task | Owner | Status | Priority | Dependencies | Notes |
|----|------|-------|--------|----------|--------------|-------|
| P0.7 | Extract conference attendance data | Assistant | ✅ | 🟡 | P0.3 | 243 candidates across 8 disciplines |
| P0.8 | Resolve missing attendee names | Assistant | ✅ | 🟡 | P0.7 | 17 missing names resolved |
| P0.9 | Compile analytical techniques from presentations | Assistant | ✅ | 🔴 | - | 46 unique techniques (33 parent + 13 sub) |
| P0.10 | Add presentation status to attendee list | Assistant | ✅ | 🟡 | - | 48 presenting, 19 poster, 12 panel |
| P0.11 | Consolidate duplicate attendees | Assistant | ✅ | 🟡 | P0.10 | 155 → 151 attendees |
| P0.12 | Create method hierarchy table | Assistant | ✅ | 🔴 | P0.9 | 3-tier classification |

---

## Phase 1: Infrastructure Setup (Week 1)

### 1.1 Database Schema Implementation

| ID | Task | Owner | Status | Priority | Dependencies | Notes |
|----|------|-------|--------|----------|--------------|-------|
| I1.1 | Verify Sharkipedia species list accessibility | SD | ⏳ | 🔴 | - | Need API or download access |
| I1.2 | Extract ISO 3166-1 country codes (197) | Assistant | ⏳ | 🔴 | - | For `auth_*` columns |
| I1.3 | Extract FishBase/Sharkipedia species (~1,200) | Assistant | 🔄 | 🔴 | I1.1 | Awaiting Weigmann complete list (178 missing) |
| I1.4 | Extract NOAA LME regions (66 sub-basins) | Assistant | ⏳ | 🟡 | - | For `sb_*` columns |
| I1.5 | Extract IHO ocean basins (9 major basins) | Assistant | ⏳ | 🟡 | - | For `b_*` columns |
| I1.6 | Generate SQL schema files (all tables) | Assistant | ⏳ | 🔴 | I1.2-I1.5 | 6 SQL files in sql/ |
| I1.7 | Create species → common name lookup table | Assistant | ⏳ | 🟡 | I1.3 | Embedded in docs or separate CSV |
| I1.8 | Create country code → name lookup table | Assistant | ⏳ | 🟡 | I1.2 | Embedded in docs or separate CSV |
| I1.9 | Create basin/sub-basin lookup table | Assistant | ⏳ | 🟡 | I1.4, I1.5 | With hierarchical mapping |
| I1.10 | Initialize DuckDB database | Assistant | ⏳ | 🔴 | I1.6 | Run all SQL schema files |
| I1.11 | Create CSV template with all ~1,625 columns | Assistant | ⏳ | 🔴 | I1.6 | Updated count: 3-tier methods + 3 superorders |
| I1.12 | Evaluate Arrow vs Parquet format | SD + Assistant | ⏳ | 🟡 | - | See comparison analysis |
| I1.13 | Set up Git LFS for database files | SD | ⏳ | 🟡 | I1.10 | Track .parquet/.arrow files |

### 1.2 External Database Integration

| ID | Task | Owner | Status | Priority | Dependencies | Notes |
|----|------|-------|--------|----------|--------------|-------|
| I2.1 | Contact Shark-References maintainers | SD | ⏳ | 🔴 | - | Email: info@shark-references.com |
| I2.2 | Request Shark-References automation permission | SD | ⏳ | 🔴 | I2.1 | Include project scope, rate limits |
| I2.3 | Contact Sharkipedia team (informal) | SD | ⏳ | 🟡 | - | Discuss integration opportunities |
| I2.4 | Review Shark-Refs/Sharkipedia roles & overlap | SD + Assistant | ⏳ | 🟡 | I2.1, I2.3 | Create comparison table |
| I2.5 | Explore Sharkipedia API for species data | SD + Assistant | ⏳ | 🟡 | I2.3 | Alternative to manual extraction |
| I2.6 | Design Sharkipedia upload workflow | SD + Assistant | ⏳ | 🟢 | I2.3 | For ecological role evidence |

### 1.3 Search Term Refinement

| ID | Task | Owner | Status | Priority | Dependencies | Notes |
|----|------|-------|--------|----------|--------------|-------|
| I3.1 | Create search term matrix (8 disciplines) | SD + GT | ⏳ | 🔴 | P0.1 | Expand from examples in docs |
| I3.2 | Test search terms on Shark-References | SD | ⏳ | 🔴 | I2.1, I3.1 | Verify result counts < 2,000 |
| I3.3 | Refine terms based on trial results | SD + GT | ⏳ | 🟡 | I3.2 | Add year ranges if needed |
| I3.4 | Document final search term vocabulary | SD + Assistant | ⏳ | 🟡 | I3.3 | Update workflow docs |

---

## Phase 2: Expert Recruitment & Trial Review (Week 2)

### 2.1 Expert Recruitment

| ID | Task | Owner | Status | Priority | Dependencies | Notes |
|----|------|-------|--------|----------|--------------|-------|
| R1.1 | Draft Tier 1 recruitment email template | SD | ⏳ | 🔴 | P0.3 | Include project scope, timeline |
| R1.2 | Customize emails by discipline | SD | ⏳ | 🔴 | R1.1 | 8 discipline-specific versions |
| R1.3 | Send to Tier 1 experts (8-12 candidates) | SD | ⏳ | 🔴 | R1.2 | Priority: Behavior, Trophic leads |
| R1.4 | Track responses and confirmations | SD | ⏳ | 🔴 | R1.3 | Spreadsheet or database |
| R1.5 | Follow up with Tier 2 if needed | SD | ⏳ | 🟡 | R1.4 | If Tier 1 declines |
| R1.6 | Confirm 6-8 experts (min 1 per discipline) | SD | ⏳ | 🔴 | R1.5 | Success metric |

### 2.2 Trial Literature Review (Phase 1 Discovery)

| ID | Task | Owner | Status | Priority | Dependencies | Notes |
|----|------|-------|--------|----------|--------------|-------|
| R2.1 | Assign trial reviewers to disciplines | SD + GT | ⏳ | 🟡 | I1.11 | n=50 papers per discipline |
| R2.2 | Conduct trial review (discover methods) | GT + Community | ⏳ | 🔴 | R2.1, I1.11 | Extract analysis_approach vocab |
| R2.3 | Compile initial method vocabulary | GT | ⏳ | 🔴 | R2.2 | ~100-150 unique methods |
| R2.4 | Standardize method naming conventions | SD + GT | ⏳ | 🔴 | R2.3 | Create `a_*` column names |
| R2.5 | Generate SQL for analysis columns | Assistant | ⏳ | 🔴 | R2.4 | Add to schema |
| R2.6 | Identify search term gaps | SD + GT | ⏳ | 🟡 | R2.2 | Missing disciplines/methods |
| R2.7 | QC trial data for consistency | GT | ⏳ | 🟡 | R2.2 | Inter-rater reliability check |

---

## Phase 3: Automated Literature Search (Weeks 2-3)

### 3.1 Shark-References Batch Searching

| ID | Task | Owner | Status | Priority | Dependencies | Notes |
|----|------|-------|--------|----------|--------------|-------|
| S1.1 | Confirm Shark-Refs automation approval | SD | ⏳ | 🔴 | I2.2 | BLOCKER - must have permission |
| S1.2 | Configure search scripts with final terms | Assistant | ⏳ | 🔴 | I3.4, R2.4 | Update SEARCH_TERMS dict |
| S1.3 | Execute batch searches (all disciplines) | Assistant | ⏳ | 🔴 | S1.1, S1.2 | Conservative 10-sec delays |
| S1.4 | Download CSV results | Assistant | ⏳ | 🔴 | S1.3 | Save to data/shark_refs_data/ |
| S1.5 | Log all searches (terms, counts, status) | Assistant | ⏳ | 🔴 | S1.3 | Populate search_log table |
| S1.6 | Monitor for errors/blocks | SD + Assistant | ⏳ | 🔴 | S1.3 | Pause if HTTP errors occur |
| S1.7 | Handle searches exceeding 2,000 results | SD + Assistant | ⏳ | 🟡 | S1.3 | Refine with year ranges |

### 3.2 Supplementary Searches (Optional)

| ID | Task | Owner | Status | Priority | Dependencies | Notes |
|----|------|-------|--------|----------|--------------|-------|
| S2.1 | Identify gaps in Shark-Refs coverage | SD + GT | ⏳ | 🟢 | S1.4 | Compare to known key papers |
| S2.2 | Execute targeted Google Scholar searches | SD | ⏳ | 🟢 | S2.1 | Manual or semi-automated |
| S2.3 | Add supplementary papers to database | GT | ⏳ | 🟢 | S2.2 | Via CSV template |

---

## Phase 4: Data Processing & QC (Weeks 3-4)

### 4.1 CSV Processing & Import

| ID | Task | Owner | Status | Priority | Dependencies | Notes |
|----|------|-------|--------|----------|--------------|-------|
| D1.1 | Parse all downloaded CSVs | Assistant | ⏳ | 🔴 | S1.4 | Extract bibliographic data |
| D1.2 | Map CSV fields to database schema | Assistant | ⏳ | 🔴 | D1.1 | Handle field name variations |
| D1.3 | Import to DuckDB database | Assistant | ⏳ | 🔴 | D1.2, I1.10 | Use import scripts |
| D1.4 | Deduplicate based on DOI/title | Assistant | ⏳ | 🔴 | D1.3 | Keep first occurrence |
| D1.5 | Export to Parquet/Arrow format | Assistant | ⏳ | 🔴 | D1.4, I1.12 | Compressed storage |
| D1.6 | Generate summary statistics | Assistant | ⏳ | 🟡 | D1.4 | Total refs, by discipline, by year |

### 4.2 Quality Control

| ID | Task | Owner | Status | Priority | Dependencies | Notes |
|----|------|-------|--------|----------|--------------|-------|
| D2.1 | Manual QC sample per discipline | GT + Community | ⏳ | 🔴 | D1.4 | n=50 random papers |
| D2.2 | Verify automated study_type extraction | GT | ⏳ | 🟡 | D1.4 | Check Primary/Review/Meta |
| D2.3 | Verify species extraction (if automated) | GT | ⏳ | 🟡 | D1.4 | Check sp_* columns |
| D2.4 | Identify false positives/negatives | GT | ⏳ | 🟡 | D2.1-D2.3 | Document error rates |
| D2.5 | Refine extraction algorithms | Assistant | ⏳ | 🟡 | D2.4 | Improve accuracy |

### 4.3 Gap Analysis

| ID | Task | Owner | Status | Priority | Dependencies | Notes |
|----|------|-------|--------|----------|--------------|-------|
| D3.1 | Compare results to expert-known papers | Panelist | ⏳ | 🟡 | D1.4, R1.6 | Each expert reviews their discipline |
| D3.2 | Identify missing key papers | Panelist + GT | ⏳ | 🟡 | D3.1 | Create list for manual addition |
| D3.3 | Execute targeted searches for gaps | SD + Assistant | ⏳ | 🟡 | D3.2 | Refine search terms |
| D3.4 | Update database with gap-filling papers | GT | ⏳ | 🟡 | D3.3 | Final additions |

---

## Phase 5: Analysis & Expert Packages (Week 4-5)

### 5.1 Database Analysis

| ID | Task | Owner | Status | Priority | Dependencies | Notes |
|----|------|-------|--------|----------|--------------|-------|
| A1.1 | Generate discipline-specific statistics | Assistant | ⏳ | 🔴 | D1.6 | Papers, methods, temporal trends |
| A1.2 | Create method co-occurrence matrices | Assistant | ⏳ | 🟡 | D1.6 | Which methods used together? |
| A1.3 | Analyze geographic trends | Assistant | ⏳ | 🟡 | D1.6 | Author nations, study basins |
| A1.4 | Identify emerging technologies | SD + Panelist | ⏳ | 🔴 | A1.1 | Recent methods (2020+) |
| A1.5 | Create branching timeline visualizations | Assistant | ⏳ | 🔴 | A1.1 | Plotly with variable line thickness |
| A1.6 | Generate method co-occurrence networks | Assistant | ⏳ | 🟡 | A1.2 | Interactive networkD3 |
| A1.7 | Create geographic heatmaps | Assistant | ⏳ | 🟡 | A1.3 | Author nations, study basins |
| A1.8 | Export high-res graphics for Canva | Assistant | ⏳ | 🟡 | A1.5-A1.7 | PNG/SVG transparent background |
| A1.9 | Set up GitHub Pages for interactive viz | Assistant | ⏳ | 🟡 | A1.5-A1.7 | Host HTML visualizations |
| A1.10 | Design polish in Canva | SD + GT | ⏳ | 🟡 | A1.8 | Import R graphics, add branding |

### 5.2 Expert Review Packages

| ID | Task | Owner | Status | Priority | Dependencies | Notes |
|----|------|-------|--------|----------|--------------|-------|
| A2.1 | Export discipline-specific reference lists | Assistant | ⏳ | 🔴 | D1.6 | CSV or Parquet subsets |
| A2.2 | Create summary reports per discipline | Assistant | ⏳ | 🔴 | A1.1 | Top papers, method trends |
| A2.3 | Compile panel questions based on findings | SD | ⏳ | 🔴 | A1.4 | Discussion prompts |
| A2.4 | Send materials to confirmed panelists | SD | ⏳ | 🔴 | A2.1-A2.3, R1.6 | 2 weeks before conference |
| A2.5 | Collect panelist feedback | SD | ⏳ | 🟡 | A2.4 | Additional papers, insights |

---

## Phase 6: Session Preparation (Week 5)

### 6.1 Session Materials

| ID | Task | Owner | Status | Priority | Dependencies | Notes |
|----|------|-------|--------|----------|--------------|-------|
| P1.1 | Create session handouts | SD + Assistant | ⏳ | 🟡 | A1.5 | Key findings, visualizations |
| P1.2 | Prepare panel discussion framework | SD | ⏳ | 🔴 | A2.3 | 5-6 min per discipline |
| P1.3 | Coordinate with session co-chairs | SD | ⏳ | 🔴 | - | Logistics, AV needs |
| P1.4 | Test presentation technology | SD | ⏳ | 🟡 | P1.1 | Ensure compatibility |
| P1.5 | Brief panelists on session format | SD | ⏳ | 🔴 | R1.6 | Timeline, expectations |

---

## Phase 7: Conference Execution

### 7.1 Session Delivery

| ID | Task | Owner | Status | Priority | Dependencies | Notes |
|----|------|-------|--------|----------|--------------|-------|
| C1.1 | Deliver 5 oral presentations (50 min) | Presenters | ⏳ | 🔴 | - | FIXED component |
| C1.2 | Facilitate panel discussion (45 min) | SD + Panelist | ⏳ | 🔴 | C1.1 | FLEXIBLE component |
| C1.3 | Manage audience Q&A | SD | ⏳ | 🔴 | C1.2 | Integrated throughout |
| C1.4 | Record key insights | SD + GT | ⏳ | 🟡 | C1.2 | For post-conference synthesis |

---

## Phase 8: Post-Conference (Ongoing)

### 8.1 Data Finalization

| ID | Task | Owner | Status | Priority | Dependencies | Notes |
|----|------|-------|--------|----------|--------------|-------|
| F1.1 | Synthesize panel insights | SD + GT | ⏳ | 🔴 | C1.4 | Key themes, recommendations |
| F1.2 | Finalize literature database | GT | ⏳ | 🔴 | D3.4 | All QC complete |
| F1.3 | Create metadata documentation | SD + Assistant | ⏳ | 🔴 | F1.2 | Data dictionary, provenance |
| F1.4 | Publish dataset (Zenodo/Dryad) | SD | ⏳ | 🟡 | F1.3 | With DOI |
| F1.5 | Create data paper manuscript | SD + GT + Panelist | ⏳ | 🟡 | F1.1, F1.4 | Target journal TBD |

### 8.2 Sharkipedia Integration (Long-term)

| ID | Task | Owner | Status | Priority | Dependencies | Notes |
|----|------|-------|--------|----------|--------------|-------|
| F2.1 | Extract ecological role evidence | Assistant | ⏳ | 🟢 | F1.2 | From annotations table |
| F2.2 | Map to Sharkipedia trait schema | SD + Assistant | ⏳ | 🟢 | F2.1, I2.6 | Match trait_class, trait_name |
| F2.3 | Create Sharkipedia upload templates | Assistant | ⏳ | 🟢 | F2.2 | CSV format |
| F2.4 | Develop automated upload workflow | Assistant | ⏳ | 🔵 | F2.3 | Manual trigger initially |
| F2.5 | Coordinate with Sharkipedia team | SD | ⏳ | 🟢 | F2.3 | Bulk upload process |

### 8.3 Community Engagement

| ID | Task | Owner | Status | Priority | Dependencies | Notes |
|----|------|-------|--------|----------|--------------|-------|
| F3.1 | Share database with AES community | SD | ⏳ | 🟡 | F1.4 | Mailing list, social media |
| F3.2 | Create GitHub repository (public) | SD | ⏳ | 🟡 | F1.4 | Scripts, docs, schema |
| F3.3 | Solicit community contributions | Community | ⏳ | 🟢 | F3.2 | Ongoing updates |
| F3.4 | Present at future conferences | SD + GT | ⏳ | 🟢 | F1.5 | Disseminate findings |

---

## Technical Debt / Future Enhancements

| ID | Task | Owner | Status | Priority | Dependencies | Notes |
|----|------|-------|--------|----------|--------------|-------|
| T1.1 | Build R Shiny data entry interface | Assistant | ⏳ | 🔵 | I1.11 | For collaborative editing |
| T1.2 | Implement automated species extraction | Assistant | ⏳ | 🟢 | I1.7 | NER or regex-based |
| T1.3 | Implement automated method extraction | Assistant | ⏳ | 🟢 | R2.4 | NLP or keyword-based |
| T1.4 | Create data validation rules | Assistant | ⏳ | 🟢 | I1.10 | Prevent invalid entries |
| T1.5 | Develop citation enrichment pipeline | Assistant | ⏳ | 🔵 | D1.4 | Semantic Scholar API |
| T1.6 | Create interactive data explorer | Assistant | ⏳ | 🔵 | F1.4 | Web dashboard |

---

## Critical Path (MUST COMPLETE)

**Week 1:**
1. I1.1: Verify Sharkipedia species list ← **SD ACTION**
2. I2.1-I2.2: Contact Shark-References ← **SD ACTION**
3. I1.2-I1.6: Generate SQL schema ← **Assistant ACTION**
4. I1.11: Create CSV template ← **Assistant ACTION**

**Week 2:**
5. R1.1-R1.3: Recruit Tier 1 experts ← **SD ACTION**
6. R2.1-R2.2: Conduct trial review ← **GT + Community ACTION**
7. I3.1-I3.3: Refine search terms ← **SD + GT ACTION**
8. S1.1: Confirm automation approval ← **SD ACTION (BLOCKER)**

**Weeks 2-3:**
9. S1.2-S1.4: Execute batch searches ← **Assistant ACTION**
10. R2.3-R2.5: Compile method vocabulary ← **GT + Assistant ACTION**

**Weeks 3-4:**
11. D1.1-D1.6: Process CSVs & QC ← **Assistant + GT ACTION**
12. D3.1-D3.2: Expert gap analysis ← **Panelist + GT ACTION**

**Week 4-5:**
13. A1.1-A1.4: Analysis & visualizations ← **Assistant + SD ACTION**
14. A2.1-A2.4: Create & send expert packages ← **Assistant + SD ACTION**
15. P1.1-P1.5: Session preparation ← **SD ACTION**

---

## Blocking Issues

| ID | Issue | Blocked Tasks | Owner | Action Required |
|----|-------|---------------|-------|-----------------|
| B1 | Sharkipedia species list access unknown | I1.3, I1.7, D2.3 | SD | Verify API or download availability |
| B2 | Shark-References automation not approved | S1.1-S1.7 | SD | Email info@shark-references.com |
| B3 | Arrow vs Parquet decision pending | I1.12, D1.5 | SD + Assistant | Complete comparison analysis |
| B4 | Tier 1 experts not yet contacted | All Phase 2-5 | SD | Draft and send recruitment emails |

---

## Notes & Decisions Log

**2025-10-03:**
- Completed Phase 0.5 (Conference Materials): attendee list, analytical techniques, method hierarchy
- Updated database schema to include 3-tier method classification (method_families → parent_techniques → subtechniques)
- Updated database schema to include 3 superorders (added Holocephali for chimaeras)
- Added `n_studies` column for review/meta-analysis papers
- Added `paper_id` column for multi-discipline papers (duplicate row approach)
- Created `outputs/method_hierarchy_table.csv` with 3-tier classification
- Updated Shark_References_Automation_Workflow.md with algorithmic CSV naming
- Database column count: ~1,625 (revised from 1,652)
- Outstanding: 178 missing species (awaiting Weigmann complete list)

**2025-10-02:**
- Completed Phase 0 documentation
- Identified EROS ecological role evidence structure as model for annotations
- Need to compare Arrow vs Parquet for final format decision
- Need to create Shark-Refs/Sharkipedia comparison table
- Lookup tables should be separate CSVs (too large to embed in docs)

---

## Contact for Task Ownership

- **SD (Simon Dedman):** [email]
- **GT (Guuske Tiktak):** [email]
- **Assistant (Claude Code):** Available via this session
- **Panelists:** TBD based on recruitment (Week 2)
- **Community:** Open call after public repository creation

---

*This TODO list is a living document. Update status, add tasks, and note blockers as the project progresses.*
