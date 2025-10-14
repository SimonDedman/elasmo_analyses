# Technique Taxonomy Database Design for Literature Review Automation

**Date:** 2025-10-13
**Purpose:** Design hierarchical technique taxonomy database for automated Shark-References literature searches
**Target:** Form-based POST requests for systematic literature review

---

## Executive Summary

This document synthesizes three data sources to create a comprehensive, hierarchical database of analytical techniques in elasmobranch research:

1. **EEA 2025 Conference Data** (`techniques_from_titles_abstracts.csv`) - 135 technique applications from 68 presentations
2. **Discipline Structure Analysis** (Option B: 8 disciplines with inclusion/exclusion boundaries)
3. **Shark-References Automation Workflow** (Search term requirements and POST request structure)

**Deliverable:** SQLite database schema + populated taxonomy for automated literature search generation.

---

## Current State Analysis

### Data Sources Comparison

#### Source 1: EEA 2025 Conference Techniques (Empirical)
**Coverage:** 40 unique techniques across 8 disciplines
**Strengths:**
- Real-world technique usage by active researchers
- Validated by conference acceptance
- Shows current methodological trends (2025)

**Limitations:**
- Limited sample size (68 presentations)
- Biased toward European researchers
- May underrepresent emerging/rare techniques
- Focus on presentation-worthy methods (publication bias)

#### Source 2: Discipline Structure Analysis (Literature-Based)
**Coverage:** Comprehensive INCLUDE/EXCLUDE lists per discipline
**Strengths:**
- Based on multi-year conference analysis (EEA, AES, SI)
- References Carrier et al. (2019) textbook
- Expert-validated boundaries
- Includes methodological context

**Limitations:**
- Text-based (not structured database)
- Mixed granularity (some specific, some broad)
- Not explicitly linked to search terms

#### Source 3: Shark-References Search Terms (Implementation)
**Coverage:** Example search queries per discipline
**Strengths:**
- Directly usable for automation
- Includes operator syntax (+, *, quotes)
- Tested search term patterns

**Limitations:**
- Limited coverage (8-10 terms per discipline)
- No hierarchical structure
- Missing many techniques from EEA data

---

## Gap Analysis: EEA Techniques vs. Planned Searches

### 1. Biology, Life History, & Health

#### EEA Techniques (7 unique)
- Age & Growth (7 presentations)
- Reproduction (7 presentations)
- Histology (2)
- Health & Disease (2)
- Physiology (1)
- Morphology (1)

#### Planned Searches (from Workflow doc)
```
+reproduct* +matur*
+growth +age
+telomere* +aging
+stress +physiol*
+parasit* +disease
+endocrin* +hormone
+metabol* +energetic*
```

**✅ Well Covered:**
- Reproduction (broad term covers fecundity, gestation)
- Age & growth (including vertebral sectioning methods)
- Physiology, disease

**⚠️ Gaps in Planned Searches:**
- Histology (specific technique, should add: `+histolog* +gonad*`)
- Morphology/morphometrics (add: `+morpholog* +morphometric*`)
- Health indices (add: `+health +index` or `+condition +score`)

**⚠️ Missing from EEA but in Planned:**
- Telomere studies (emerging, may appear in literature)
- Endocrinology (not captured in EEA titles/abstracts)
- Metabolic studies

**Recommendation:** Add 3-4 search terms; EEA data confirms core techniques.

---

### 2. Behaviour & Sensory Ecology

#### EEA Techniques (5 unique)
- Cognition (4 presentations)
- Video Analysis (3)
- Behavioural Observation (2)
- Sensory Biology (2)
- Social Network Analysis (1)

#### Planned Searches
```
+behav* +predation
+vision +visual
+electr* +sensory
+olfact* +chemosens*
+magnet* +navigation
+social +aggregation
+learning +cognition
```

**✅ Well Covered:**
- Social behavior, cognition, sensory biology

**⚠️ Gaps in Planned Searches:**
- Video analysis (add: `+video +analysis` or `+UAV +drone`)
- Network analysis (already covered by "+social")

**⚠️ Missing from EEA but in Planned:**
- Specific sensory modalities (electro, olfaction, magnetoreception)
- Predation behavior

**Recommendation:** Add video/drone search term; maintain sensory specifics.

---

### 3. Trophic & Community Ecology

#### EEA Techniques (4 unique)
- Stable Isotope Analysis (4 presentations)
- DNA Metabarcoding (3)
- Diet Analysis (3)
- Stomach Content Analysis (3)

#### Planned Searches
```
+stable +isotop*
+diet +prey
+trophic +level
+food +web
+stomach +content
+energy +flow
+niche +partition*
```

**✅ Excellent Coverage:**
- All EEA techniques directly represented
- Good hierarchical organization (diet → stomach/DNA/isotopes)

**⚠️ Missing from EEA but in Planned:**
- Food web modeling, energy flow (theoretical, less common in conference)
- Niche partitioning

**Recommendation:** Maintain current search terms; strong alignment.

---

### 4. Genetics, Genomics, & eDNA

#### EEA Techniques (6 unique)
- Genomics (3 presentations)
- Population Genetics (2)
- eDNA (2)
- Microsatellites (1)
- Phylogenetics (1)
- Whole Genome Sequencing (1)

#### Planned Searches
```
+population +geneti*
+genom* +sequenc*
+eDNA +environmental
+phylogeny +molecular
+microsatellite +SNP
+transcriptom* +gene
+conservation +genetic*
```

**✅ Excellent Coverage:**
- All major EEA techniques represented
- Good technique granularity (WGS, RAD-seq, etc.)

**⚠️ Missing from EEA but in Planned:**
- SNPs (likely present but not captured in extraction)
- Transcriptomics
- Conservation genetics (as distinct category)

**Recommendation:** Maintain comprehensive list; add `+RAD* +seq*` for RAD-seq.

---

### 5. Movement, Space Use, & Habitat Modeling

#### EEA Techniques (6 unique)
- Acoustic Telemetry (11 presentations) ⚠️ DOMINANT
- MPA Design (7)
- Habitat Modeling (3)
- Movement Modeling (3)
- Connectivity (2)
- Species Distribution Model (1)

#### Planned Searches
```
+telemetry +acoustic
+satellite +tracking
+habitat +model*
+home +range
+SDM +distribution
+spatial +ecology
+migration +movement
+circuit* +connectivity
```

**✅ Excellent Coverage:**
- All EEA techniques represented
- Good balance of empirical (telemetry) and analytical (SDM, circuit theory)

**⚠️ Acoustic Telemetry Dominance:**
- 11/27 movement techniques (41%) are acoustic telemetry
- Suggests need for broad acoustic telemetry literature search
- May warrant sub-searches: `+acoustic +array`, `+VPS +positioning`, `+residence +time`

**⚠️ Missing from EEA but in Planned:**
- Satellite tracking (PSAT, SPOT tags)
- Home range estimation (KDE, Brownian bridge)

**Recommendation:** Add sub-techniques for acoustic telemetry; maintain others.

---

### 6. Fisheries, Stock Assessment, & Management

#### EEA Techniques (2 unique) ⚠️ UNDERREPRESENTED
- Bycatch Assessment (4 presentations)
- Mark-Recapture (1)

#### Planned Searches
```
+stock +assessment
+fishery +CPUE
+bycatch +discard*
+mortality +fishing
+catch +per +unit
+surplus +production
+harvest +strategy
```

**⚠️ Major Gap in EEA Data:**
- Stock assessment techniques largely absent from conference
- Possible reasons:
  1. Fisheries-focused researchers attend different conferences
  2. EEA focus on conservation/ecology over fisheries
  3. Stock assessment methods well-established (not presentation-worthy)

**✅ Bycatch Well Represented:**
- 4 presentations on bycatch (aligns with conservation focus)

**Recommendation:**
- Literature search CANNOT rely on EEA data for this discipline
- Use planned searches as-is
- Consider adding: `+close* +kin` (CKMR), `+data* +poor` (data-poor methods)

---

### 7. Conservation Policy & Human Dimensions

#### EEA Techniques (6 unique)
- IUCN Red List Assessment (16 presentations) ⚠️ DOMINANT
- Human Dimensions (7)
- Trade & Markets (6)
- Citizen Science (2)
- Policy Evaluation (2)
- Tourism (2)

#### Planned Searches
```
+conservation +status
+CITES +protection
+MPA +marine +protected
+policy +management
+stakeholder +community
+ecosystem +service*
+human +dimension*
```

**✅ Strong EEA Representation:**
- IUCN assessments dominate (16/35 = 46% of conservation techniques)
- Human dimensions well-covered

**⚠️ Gaps in Planned Searches:**
- Trade & markets (add: `+trade +CITES` or `+shark +fin +trade`)
- Citizen science (add: `+citizen +scien*`)
- Tourism impacts (add: `+tourism +ecotourism`)

**⚠️ Missing from EEA but in Planned:**
- MPA policy (vs. MPA spatial design in Movement)
- Stakeholder engagement
- Ecosystem services

**Recommendation:** Add 3 search terms for trade, citizen science, tourism.

---

### 8. Data Science & Integrative Methods

#### EEA Techniques (5 unique)
- Machine Learning (9 presentations) - including Random Forest
- Bayesian Methods (1)
- Data Integration (1)
- Meta-Analysis (1)
- Time Series (1)

#### Planned Searches
```
+machine +learning
+random +forest
+neural +network
+Bayesian +model*
+AI +artificial
+ensemble +model*
+data +integration
+GAM +generalized
```

**✅ Good Coverage:**
- Machine learning dominant in both EEA and planned searches
- Bayesian methods represented

**⚠️ Gaps in Planned Searches:**
- Meta-analysis (add: `+meta* +analysis`)
- Time series analysis (add: `+time +series` or `+ARIMA`)

**⚠️ Missing from EEA but in Planned:**
- Neural networks (likely too cutting-edge for 2025 conference)
- GAM (common but perhaps not highlighted in titles/abstracts)
- Ensemble modeling

**Recommendation:** Add meta-analysis and time series; maintain AI/ML breadth.

---

## Summary of Gaps and Recommendations

### Critical Additions Needed (High Priority)

| Discipline | Missing Techniques | Recommended Search Terms |
|------------|-------------------|--------------------------|
| Biology | Histology | `+histolog* +gonad*` |
| Biology | Morphometrics | `+morpholog* +morphometric*` |
| Behaviour | Video/Drone Analysis | `+video +UAV` or `+drone +track*` |
| Movement | Acoustic Telemetry Sub-techniques | `+VPS +positioning`, `+residence +detection` |
| Fisheries | Close-Kin Mark-Recapture | `+close* +kin +mark*` or `+CKMR` |
| Fisheries | Data-Poor Methods | `+data* +poor +assess*` |
| Conservation | Trade & Markets | `+trade +fin* +market` |
| Conservation | Citizen Science | `+citizen +scien* +monitor*` |
| Data Science | Meta-Analysis | `+meta* +analysis +systematic` |
| Data Science | Time Series | `+time +series +temporal` |

### Techniques in EEA but Not in Planned Searches (11 techniques)

These are validated by conference presentations and should be considered:

1. **Histology** (Biology) - 2 presentations
2. **Morphology** (Biology) - 1 presentation
3. **Video Analysis** (Behaviour) - 3 presentations
4. **Social Network Analysis** (Behaviour) - 1 presentation (covered by "+social")
5. **DNA Metabarcoding** (Trophic) - 3 presentations (covered by "+diet +DNA")
6. **Stomach Content Analysis** (Trophic) - 3 presentations (explicitly listed)
7. **Microsatellites** (Genetics) - 1 presentation (explicitly listed)
8. **Whole Genome Sequencing** (Genetics) - 1 presentation (covered by "+genom*")
9. **MPA Design** (Movement) - 7 presentations (in Conservation Policy searches)
10. **Meta-Analysis** (Data Science) - 1 presentation
11. **Time Series** (Data Science) - 1 presentation

**Action Items:**
- Add explicit search terms for: Histology, Morphology, Video Analysis, Meta-Analysis, Time Series
- Verify others are captured by existing wildcards

### Techniques in Planned Searches but Not in EEA (18 techniques)

These may be important for literature but weren't conference topics:

**Biology:** Telomere studies, Endocrinology, Metabolic studies
**Behaviour:** Electroreception, Olfaction, Magnetoreception, Predation behavior specifics
**Trophic:** Food web modeling, Energy flow, Niche partitioning
**Genetics:** SNPs (specific), Transcriptomics, Conservation genetics (as category)
**Movement:** Satellite tracking, Home range estimation methods
**Fisheries:** Stock assessment (all sub-methods), CPUE standardization, Surplus production
**Conservation:** Stakeholder engagement, Ecosystem services
**Data Science:** Neural networks, GAM, Ensemble modeling

**Decision:**
- **KEEP ALL** - These represent established or emerging methods in literature
- Literature review should be more comprehensive than conference snapshot
- Conference bias (toward novel/presentation-worthy) should not limit systematic review

---

## Proposed Database Schema

### Design Principles

1. **Hierarchical Structure:** Disciplines → Categories → Techniques → Sub-techniques
2. **Search Term Mapping:** Each technique maps to 1+ search terms
3. **Metadata:** Track source (EEA, literature, expert), usage frequency, temporal trends
4. **Flexibility:** Allow many-to-many relationships (techniques can span categories)
5. **Automation-Ready:** Direct export to POST request parameters

### Entity-Relationship Model

```
┌─────────────┐
│ Disciplines │ (8 records: Biology, Behaviour, Trophic, etc.)
└──────┬──────┘
       │ 1:N
       │
┌──────▼──────────┐
│ Categories      │ (Technique groups within disciplines)
│                 │ Examples: "Telemetry Methods", "Genetic Markers"
└────────┬────────┘
         │ 1:N
         │
┌────────▼────────────┐
│ Techniques          │ (Parent techniques)
│                     │ Examples: "Acoustic Telemetry", "Population Genetics"
└─────────┬───────────┘
          │ 1:N
          │
┌─────────▼────────────┐
│ Sub-Techniques       │ (Specific methods)
│                      │ Examples: "VPS Positioning", "Microsatellites"
└──────────────────────┘

┌────────────────────┐
│ Search Terms       │ (Shark-References query strings)
│                    │ Linked to: Techniques, Sub-Techniques, Categories
└────────────────────┘

┌────────────────────┐
│ EEA Evidence       │ (Conference usage frequency)
│                    │ Linked to: Techniques
└────────────────────┘

┌────────────────────┐
│ Literature Counts  │ (Shark-Ref search results - populated later)
│                    │ Linked to: Search Terms
└────────────────────┘
```

### SQL Schema (SQLite)

```sql
-- ==============================================================================
-- Core Taxonomy Tables
-- ==============================================================================

CREATE TABLE disciplines (
    discipline_id INTEGER PRIMARY KEY AUTOINCREMENT,
    discipline_name VARCHAR(100) NOT NULL UNIQUE,
    discipline_code VARCHAR(20) NOT NULL UNIQUE, -- e.g., "BIO", "MOV", "CON"
    description TEXT,
    sort_order INTEGER, -- For panel presentation order
    expert_lead VARCHAR(100), -- Assigned expert name
    expert_email VARCHAR(100),
    created_date DATE DEFAULT CURRENT_DATE,
    modified_date DATE DEFAULT CURRENT_DATE
);

CREATE TABLE categories (
    category_id INTEGER PRIMARY KEY AUTOINCREMENT,
    discipline_id INTEGER NOT NULL,
    category_name VARCHAR(150) NOT NULL,
    category_description TEXT,
    is_cross_cutting BOOLEAN DEFAULT 0, -- e.g., Climate Change
    sort_order INTEGER,
    FOREIGN KEY (discipline_id) REFERENCES disciplines(discipline_id),
    UNIQUE (discipline_id, category_name)
);

CREATE TABLE techniques (
    technique_id INTEGER PRIMARY KEY AUTOINCREMENT,
    technique_name VARCHAR(200) NOT NULL,
    technique_name_normalized VARCHAR(200), -- Lowercase, trimmed for matching
    parent_category_id INTEGER, -- Primary category (may have multiple)
    is_parent BOOLEAN DEFAULT 1, -- TRUE if parent, FALSE if sub-technique
    parent_technique_id INTEGER, -- NULL if parent, FK if sub-technique
    description TEXT,
    synonyms TEXT, -- Comma-separated alternative names
    first_elasmobranch_paper TEXT, -- Citation of first use in elasmos
    methodological_notes TEXT,
    inclusion_criteria TEXT, -- From Discipline_Structure_Analysis.md
    exclusion_criteria TEXT,
    boundary_cases TEXT,
    created_date DATE DEFAULT CURRENT_DATE,
    modified_date DATE DEFAULT CURRENT_DATE,
    FOREIGN KEY (parent_category_id) REFERENCES categories(category_id),
    FOREIGN KEY (parent_technique_id) REFERENCES techniques(technique_id)
);

-- Many-to-many: Techniques can belong to multiple categories
CREATE TABLE technique_categories (
    technique_id INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    is_primary BOOLEAN DEFAULT 0, -- Mark primary category
    notes TEXT,
    PRIMARY KEY (technique_id, category_id),
    FOREIGN KEY (technique_id) REFERENCES techniques(technique_id),
    FOREIGN KEY (category_id) REFERENCES categories(category_id)
);

-- ==============================================================================
-- Search Term Management
-- ==============================================================================

CREATE TABLE search_terms (
    search_term_id INTEGER PRIMARY KEY AUTOINCREMENT,
    search_query VARCHAR(500) NOT NULL, -- Actual query string with operators
    query_description TEXT, -- Human-readable description
    target_level VARCHAR(20), -- "discipline", "category", "technique", "sub-technique"
    target_id INTEGER, -- FK to relevant table (flexible - use with target_level)
    technique_id INTEGER, -- Optional link to specific technique
    category_id INTEGER, -- Optional link to category
    discipline_id INTEGER, -- Optional link to discipline
    operator_type VARCHAR(20), -- "AND" (+), "OR" (default), "PHRASE" (quotes), "PROXIMITY" (@)
    expected_specificity VARCHAR(20), -- "broad", "moderate", "narrow"
    notes TEXT,
    is_validated BOOLEAN DEFAULT 0, -- Set TRUE after manual testing
    validation_date DATE,
    validation_result_count INTEGER, -- Results from test search
    created_date DATE DEFAULT CURRENT_DATE,
    FOREIGN KEY (technique_id) REFERENCES techniques(technique_id),
    FOREIGN KEY (category_id) REFERENCES categories(category_id),
    FOREIGN KEY (discipline_id) REFERENCES disciplines(discipline_id)
);

-- Examples of search term variations for same technique
CREATE TABLE search_term_alternatives (
    alternative_id INTEGER PRIMARY KEY AUTOINCREMENT,
    primary_search_term_id INTEGER NOT NULL,
    alternative_query VARCHAR(500) NOT NULL,
    reason VARCHAR(50), -- "spelling_variant", "abbreviation", "broader", "narrower"
    notes TEXT,
    FOREIGN KEY (primary_search_term_id) REFERENCES search_terms(search_term_id)
);

-- ==============================================================================
-- Evidence Tables
-- ==============================================================================

-- EEA 2025 Conference Usage
CREATE TABLE eea_evidence (
    evidence_id INTEGER PRIMARY KEY AUTOINCREMENT,
    technique_id INTEGER NOT NULL,
    discipline_name VARCHAR(100), -- From EEA data
    presentation_count INTEGER DEFAULT 1,
    source VARCHAR(50), -- "title", "abstract", "title+abstract"
    presentation_ids TEXT, -- Comma-separated list of presentation IDs
    example_presentation_title TEXT,
    notes TEXT,
    FOREIGN KEY (technique_id) REFERENCES techniques(technique_id)
);

-- Literature Search Results (populated by automation)
CREATE TABLE literature_searches (
    search_id INTEGER PRIMARY KEY AUTOINCREMENT,
    search_term_id INTEGER NOT NULL,
    search_date DATE DEFAULT CURRENT_DATE,
    result_count INTEGER,
    year_from INTEGER,
    year_to INTEGER,
    csv_filename VARCHAR(255), -- Downloaded CSV path
    search_duration_seconds REAL,
    status VARCHAR(50), -- "success", "error", "timeout", "rate_limited"
    error_message TEXT,
    FOREIGN KEY (search_term_id) REFERENCES search_terms(search_term_id)
);

-- Individual papers from literature searches
CREATE TABLE literature_papers (
    paper_id INTEGER PRIMARY KEY AUTOINCREMENT,
    search_id INTEGER NOT NULL,
    shark_ref_id VARCHAR(100), -- Original Shark-References ID
    authors TEXT,
    year INTEGER,
    title TEXT,
    journal VARCHAR(255),
    volume VARCHAR(50),
    issue VARCHAR(50),
    pages VARCHAR(50),
    doi VARCHAR(100),
    abstract TEXT,
    keywords TEXT,
    citation_count INTEGER, -- From Semantic Scholar API
    scholar_url VARCHAR(500),
    is_duplicate BOOLEAN DEFAULT 0,
    duplicate_of_paper_id INTEGER,
    date_retrieved DATE DEFAULT CURRENT_DATE,
    FOREIGN KEY (search_id) REFERENCES literature_searches(search_id),
    FOREIGN KEY (duplicate_of_paper_id) REFERENCES literature_papers(paper_id)
);

-- Link papers to multiple techniques (papers can use multiple methods)
CREATE TABLE paper_techniques (
    paper_id INTEGER NOT NULL,
    technique_id INTEGER NOT NULL,
    confidence VARCHAR(20), -- "high", "medium", "low" - technique relevance
    context TEXT, -- Where/how technique mentioned
    PRIMARY KEY (paper_id, technique_id),
    FOREIGN KEY (paper_id) REFERENCES literature_papers(paper_id),
    FOREIGN KEY (technique_id) REFERENCES techniques(technique_id)
);

-- ==============================================================================
-- Temporal Trends
-- ==============================================================================

CREATE TABLE technique_trends (
    trend_id INTEGER PRIMARY KEY AUTOINCREMENT,
    technique_id INTEGER NOT NULL,
    year INTEGER NOT NULL,
    paper_count INTEGER DEFAULT 0,
    citation_sum INTEGER DEFAULT 0,
    trend_category VARCHAR(50), -- "emerging", "established", "declining", "stable"
    notes TEXT,
    FOREIGN KEY (technique_id) REFERENCES techniques(technique_id),
    UNIQUE (technique_id, year)
);

-- ==============================================================================
-- Expert Annotations
-- ==============================================================================

CREATE TABLE expert_reviews (
    review_id INTEGER PRIMARY KEY AUTOINCREMENT,
    technique_id INTEGER,
    paper_id INTEGER,
    expert_name VARCHAR(100) NOT NULL,
    review_date DATE DEFAULT CURRENT_DATE,
    relevance_rating INTEGER CHECK (relevance_rating BETWEEN 1 AND 5),
    methodological_quality INTEGER CHECK (methodological_quality BETWEEN 1 AND 5),
    innovation_score INTEGER CHECK (innovation_score BETWEEN 1 AND 5),
    comments TEXT,
    is_recommended_reading BOOLEAN DEFAULT 0,
    is_seminal_paper BOOLEAN DEFAULT 0,
    FOREIGN KEY (technique_id) REFERENCES techniques(technique_id),
    FOREIGN KEY (paper_id) REFERENCES literature_papers(paper_id)
);

-- ==============================================================================
-- Indexes for Performance
-- ==============================================================================

CREATE INDEX idx_techniques_parent ON techniques(parent_technique_id);
CREATE INDEX idx_techniques_category ON techniques(parent_category_id);
CREATE INDEX idx_techniques_normalized ON techniques(technique_name_normalized);
CREATE INDEX idx_search_terms_technique ON search_terms(technique_id);
CREATE INDEX idx_search_terms_discipline ON search_terms(discipline_id);
CREATE INDEX idx_literature_papers_doi ON literature_papers(doi);
CREATE INDEX idx_literature_papers_year ON literature_papers(year);
CREATE INDEX idx_literature_papers_sharkref ON literature_papers(shark_ref_id);
CREATE INDEX idx_eea_evidence_technique ON eea_evidence(technique_id);
CREATE INDEX idx_paper_techniques_paper ON paper_techniques(paper_id);
CREATE INDEX idx_paper_techniques_technique ON paper_techniques(technique_id);
CREATE INDEX idx_technique_trends_technique_year ON technique_trends(technique_id, year);

-- ==============================================================================
-- Views for Common Queries
-- ==============================================================================

-- Complete technique hierarchy with discipline context
CREATE VIEW v_technique_hierarchy AS
SELECT
    d.discipline_name,
    d.discipline_code,
    c.category_name,
    t.technique_name,
    t.technique_id,
    t.is_parent,
    pt.technique_name AS parent_technique_name,
    t.description,
    t.synonyms
FROM techniques t
JOIN categories c ON t.parent_category_id = c.category_id
JOIN disciplines d ON c.discipline_id = d.discipline_id
LEFT JOIN techniques pt ON t.parent_technique_id = pt.technique_id
ORDER BY d.sort_order, c.sort_order, t.is_parent DESC, t.technique_name;

-- EEA evidence summary with search coverage
CREATE VIEW v_technique_evidence_summary AS
SELECT
    t.technique_name,
    d.discipline_name,
    c.category_name,
    COALESCE(e.presentation_count, 0) AS eea_presentations,
    e.source AS eea_source,
    COUNT(DISTINCT st.search_term_id) AS search_terms_defined,
    COUNT(DISTINCT ls.search_id) AS literature_searches_run,
    SUM(COALESCE(ls.result_count, 0)) AS total_papers_found
FROM techniques t
JOIN categories c ON t.parent_category_id = c.category_id
JOIN disciplines d ON c.discipline_id = d.discipline_id
LEFT JOIN eea_evidence e ON t.technique_id = e.technique_id
LEFT JOIN search_terms st ON t.technique_id = st.technique_id
LEFT JOIN literature_searches ls ON st.search_term_id = ls.search_term_id
GROUP BY t.technique_id, t.technique_name, d.discipline_name, c.category_name, e.presentation_count, e.source
ORDER BY d.discipline_name, eea_presentations DESC;

-- Search terms ready for automation
CREATE VIEW v_search_terms_for_automation AS
SELECT
    st.search_term_id,
    st.search_query,
    st.query_description,
    d.discipline_name,
    d.discipline_code,
    c.category_name,
    t.technique_name,
    st.operator_type,
    st.expected_specificity,
    st.is_validated,
    st.validation_result_count,
    -- Generate filename for CSV output
    REPLACE(LOWER(st.search_query), ' ', '_') || '_' || strftime('%Y%m%d', 'now') || '.csv' AS suggested_filename
FROM search_terms st
LEFT JOIN techniques t ON st.technique_id = t.technique_id
LEFT JOIN categories c ON st.category_id = c.category_id
LEFT JOIN disciplines d ON st.discipline_id = d.discipline_id
WHERE st.is_validated = 1 OR st.is_validated IS NULL -- Include unvalidated for initial run
ORDER BY d.sort_order, c.sort_order, t.technique_name;
```

---

## Population Strategy

### Phase 1: Core Taxonomy (Week 1)

#### 1.1 Disciplines (8 records)
**Source:** Discipline_Structure_Analysis.md Option B

```sql
INSERT INTO disciplines (discipline_name, discipline_code, description, sort_order) VALUES
('Biology, Life History, & Health', 'BIO', 'Age/growth, reproduction, physiology, disease/parasites', 1),
('Behaviour & Sensory Ecology', 'BEH', 'Behaviour, neurobiology, sensory systems, network analysis', 2),
('Trophic & Community Ecology', 'TRO', 'Diet (isotopes, DNA, stomach), ecosystem roles', 3),
('Genetics, Genomics, & eDNA', 'GEN', 'Population genetics, phylogenetics, adaptive genomics, eDNA', 4),
('Movement, Space Use, & Habitat Modeling', 'MOV', 'Telemetry, satellite tracking, SDMs, MPA design', 5),
('Fisheries, Stock Assessment, & Management', 'FISH', 'Population dynamics, CPUE, bycatch, data-poor methods', 6),
('Conservation Policy & Human Dimensions', 'CON', 'IUCN assessments, policy, human-shark conflict, citizen science', 7),
('Data Science & Integrative Methods', 'DATA', 'AI/ML, data integration, Bayesian approaches, statistics', 8);
```

#### 1.2 Categories (~30-40 records)
**Source:** Synthesize from Discipline boundaries + EEA technique clusters

Example for Biology:
```sql
INSERT INTO categories (discipline_id, category_name, category_description, sort_order) VALUES
(1, 'Age & Growth Methods', 'Vertebrae, spines, radiocarbon, NIRS, bomb radiocarbon', 1),
(1, 'Reproductive Biology', 'Histology, ultrasound, hormones, fecundity, gestation', 2),
(1, 'Morphology & Morphometrics', 'Body measurements, shape analysis, geometric morphometrics', 3),
(1, 'Physiology', 'Metabolic rate, osmoregulation, blood chemistry, thermal tolerance', 4),
(1, 'Disease & Health', 'Pathology, contaminants, immune function, health indices, telomeres', 5);
```

#### 1.3 Techniques (~80-120 records)
**Sources:**
1. EEA data (40 validated techniques) - PRIORITY
2. Discipline_Structure_Analysis.md INCLUDE lists
3. Shark_References_Automation_Workflow.md example terms

**Method:**
1. Start with 40 EEA techniques (mark as `is_parent = TRUE` unless explicitly sub-technique)
2. Add missing techniques from Discipline boundaries (mark as `is_parent = TRUE`)
3. Create parent-child relationships where clear (e.g., Acoustic Telemetry → VPS, Residence Time)

#### 1.4 Search Terms (~150-200 records initially)
**Sources:**
1. Shark_References_Automation_Workflow.md (56 example terms across 8 disciplines)
2. Additional terms from Gap Analysis (10 critical additions)
3. EEA-specific terms (techniques not in original workflow)

**Linking Strategy:**
- **Broad searches** → Link to discipline_id
- **Moderate searches** → Link to category_id
- **Specific searches** → Link to technique_id
- **Very specific** → Link to sub-technique technique_id

### Phase 2: EEA Evidence (Week 1)

**Source:** `outputs/techniques_from_titles_abstracts.csv` (135 records)

**Process:**
1. Load CSV into temporary table
2. Match technique names to `techniques` table (normalize for matching)
3. Aggregate by technique: COUNT presentations, COLLECT presentation_ids
4. INSERT into `eea_evidence` table

**R Script:**
```r
library(tidyverse)
library(RSQLite)

# Load data
eea_data <- read_csv("outputs/techniques_from_titles_abstracts.csv")
conn <- dbConnect(SQLite(), "technique_taxonomy.db")

# Normalize and aggregate
eea_aggregated <- eea_data %>%
  mutate(technique_normalized = tolower(str_trim(technique))) %>%
  group_by(technique_normalized, discipline) %>%
  summarise(
    presentation_count = n(),
    presentation_ids = paste(unique(presentation_id), collapse = ","),
    example_title = first(title),
    sources = case_when(
      all(!is.na(pattern)) ~ "abstract",
      all(is.na(pattern)) ~ "title",
      TRUE ~ "title+abstract"
    ),
    .groups = "drop"
  )

# Match to techniques table
techniques_db <- dbGetQuery(conn, "SELECT technique_id, technique_name_normalized FROM techniques")

eea_matched <- eea_aggregated %>%
  left_join(
    techniques_db,
    by = c("technique_normalized" = "technique_name_normalized")
  )

# Insert matched records
eea_matched %>%
  filter(!is.na(technique_id)) %>%
  select(
    technique_id,
    discipline_name = discipline,
    presentation_count,
    source = sources,
    presentation_ids,
    example_presentation_title = example_title
  ) %>%
  dbWriteTable(conn, "eea_evidence", ., append = TRUE, row.names = FALSE)

# Report unmatched
unmatched <- eea_matched %>% filter(is.na(technique_id))
cat("Unmatched techniques:", nrow(unmatched), "\n")
print(unmatched %>% select(technique_normalized, discipline, presentation_count))
```

### Phase 3: Search Term Validation (Week 2)

**Manual Process:**
1. Export search terms from database
2. For each term, manually execute on Shark-References
3. Record result count
4. Update `is_validated = TRUE`, `validation_result_count = N`
5. If count > 2000, flag for refinement

**Automated Validation Script:**
```python
import sqlite3
import requests
import time
from datetime import datetime

def validate_search_term(search_query):
    """
    Test search term on Shark-References and return result count

    NOTE: This requires parsing HTML response or inspecting result page
    Implementation details depend on Shark-Ref page structure
    """
    url = "https://shark-references.com/search"
    data = {
        "query_fulltext": search_query,
        "clicked_button": "search"  # Not export, just count
    }

    response = requests.post(url, data=data)

    # Parse response to extract result count
    # (Implementation detail - may need BeautifulSoup)
    result_count = parse_result_count(response.text)

    return result_count

# Connect to database
conn = sqlite3.connect("technique_taxonomy.db")
cursor = conn.cursor()

# Get unvalidated search terms
cursor.execute("""
    SELECT search_term_id, search_query
    FROM search_terms
    WHERE is_validated = 0 OR is_validated IS NULL
    ORDER BY search_term_id
""")

search_terms = cursor.fetchall()

print(f"Validating {len(search_terms)} search terms...")

for search_term_id, search_query in search_terms:
    print(f"Testing: {search_query}")

    try:
        result_count = validate_search_term(search_query)

        # Update database
        cursor.execute("""
            UPDATE search_terms
            SET is_validated = 1,
                validation_date = ?,
                validation_result_count = ?
            WHERE search_term_id = ?
        """, (datetime.now().date(), result_count, search_term_id))

        conn.commit()

        print(f"  → {result_count} results")

        if result_count > 2000:
            print(f"  ⚠️ EXCEEDS LIMIT - needs refinement")

    except Exception as e:
        print(f"  ✗ ERROR: {e}")

    # Rate limiting: 10 seconds between requests
    time.sleep(10)

conn.close()
print("Validation complete")
```

### Phase 4: Literature Search Execution (Week 3-4)

**Automated Batch Search:**
```python
import sqlite3
import requests
import time
from datetime import datetime

def execute_shark_ref_search(search_query, output_dir="./literature_searches"):
    """
    Execute search on Shark-References and download CSV
    """
    url = "https://shark-references.com/search"
    data = {
        "query_fulltext": search_query,
        "opts[]": "download",
        "clicked_button": "export"
    }

    start_time = time.time()
    response = requests.post(url, data=data)
    duration = time.time() - start_time

    # Generate filename
    safe_query = search_query.replace("+", "").replace(" ", "_")[:50]
    filename = f"{output_dir}/sharkrefs_{safe_query}_{datetime.now().strftime('%Y%m%d')}.csv"

    # Save CSV
    with open(filename, 'wb') as f:
        f.write(response.content)

    # Parse result count from CSV (count rows - 1 for header)
    result_count = len(response.text.split('\n')) - 1

    return {
        'filename': filename,
        'result_count': result_count,
        'duration': duration,
        'status': 'success'
    }

# Main batch search loop
conn = sqlite3.connect("technique_taxonomy.db")
cursor = conn.cursor()

# Get validated search terms
cursor.execute("""
    SELECT search_term_id, search_query
    FROM search_terms
    WHERE is_validated = 1
    AND validation_result_count > 0
    AND validation_result_count <= 2000
    ORDER BY discipline_id, search_term_id
""")

search_terms = cursor.fetchall()

print(f"Executing {len(search_terms)} literature searches...")

for search_term_id, search_query in search_terms:
    print(f"\n[{datetime.now()}] Searching: {search_query}")

    try:
        result = execute_shark_ref_search(search_query)

        # Log search
        cursor.execute("""
            INSERT INTO literature_searches
            (search_term_id, search_date, result_count, csv_filename,
             search_duration_seconds, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            search_term_id,
            datetime.now().date(),
            result['result_count'],
            result['filename'],
            result['duration'],
            result['status']
        ))

        conn.commit()

        print(f"  ✓ Downloaded {result['result_count']} references")
        print(f"  → {result['filename']}")

    except Exception as e:
        # Log error
        cursor.execute("""
            INSERT INTO literature_searches
            (search_term_id, search_date, status, error_message)
            VALUES (?, ?, ?, ?)
        """, (
            search_term_id,
            datetime.now().date(),
            'error',
            str(e)
        ))
        conn.commit()

        print(f"  ✗ ERROR: {e}")

    # Conservative rate limiting: 10 seconds between searches
    time.sleep(10)

conn.close()
print("\n✓ Batch search execution complete")
```

### Phase 5: CSV Import to Database (Week 4)

**Process:**
1. Parse each downloaded CSV
2. Extract citation fields
3. Insert into `literature_papers` table
4. Link to originating `search_id`
5. Deduplicate based on DOI or title

---

## Deliverables

### Immediate (End of Week 1)
1. ✅ **SQLite Database File:** `technique_taxonomy.db` with schema implemented
2. ✅ **Populated Core Tables:**
   - 8 disciplines
   - ~35 categories
   - ~100 techniques (40 from EEA + 60 from literature)
   - ~150 search terms (initial set)
3. ✅ **EEA Evidence Table:** 40 technique records with presentation counts
4. 📄 **Population Scripts:**
   - `R/populate_taxonomy.R` - Insert disciplines, categories, techniques
   - `R/import_eea_evidence.R` - Load EEA conference data
   - `python/validate_search_terms.py` - Test search terms

### Week 2
5. ✅ **Validated Search Terms:** All search terms tested with result counts
6. 📊 **Validation Report:** Markdown document with:
   - Terms exceeding 2000 results (need refinement)
   - Terms with 0 results (need revision)
   - Recommended additions/modifications

### Week 3-4
7. 📦 **Literature Search Results:** CSV files for all validated searches
8. 💾 **Populated Literature Tables:**
   - `literature_searches` - Log of all executed searches
   - `literature_papers` - Individual paper citations (initial import)
9. 📈 **Summary Statistics:**
   - Papers per technique
   - Papers per discipline
   - Temporal trends (papers per year)

### Week 5
10. 📊 **Expert Review Packages:** Export discipline-specific reference lists
11. 📄 **Methodology Documentation:** Complete workflow documentation
12. 🔗 **API Integration Guide:** Instructions for Semantic Scholar enrichment

---

## Next Steps

### Immediate Actions (This Week)

1. **Create Database:**
   ```bash
   cd "/path/to/Data Panel"
   sqlite3 technique_taxonomy.db < schema.sql
   ```

2. **Population Script Development:**
   - Create `scripts/populate_taxonomy_database.R`
   - Implement discipline/category/technique insertion
   - Import EEA evidence

3. **Gap Filling:**
   - Review EEA techniques vs. Discipline boundaries
   - Add missing techniques to database
   - Create hierarchical relationships

4. **Search Term Compilation:**
   - Extract all search terms from Workflow document
   - Add new terms from Gap Analysis
   - Link to appropriate taxonomy level

### Week 2 Actions

5. **Validation Testing:**
   - Manual test sample of search terms
   - Develop automated validation script
   - Refine terms exceeding limits

6. **Expert Consultation:**
   - Send draft taxonomy to discipline leads
   - Request additions/corrections
   - Incorporate feedback

### Week 3-4 Actions

7. **Automated Literature Search:**
   - Execute validated search terms
   - Download and store CSVs
   - Log all searches

8. **Database Population:**
   - Parse CSVs
   - Import paper citations
   - Deduplicate

### Week 5+ Actions

9. **Citation Enrichment:**
   - Semantic Scholar API integration
   - Citation count retrieval
   - Influential paper identification

10. **Expert Review Preparation:**
    - Generate discipline-specific reports
    - Export reference lists
    - Create summary visualizations

---

## Success Criteria

✅ **Complete** when:
1. Database contains ≥100 techniques across 8 disciplines
2. Each technique linked to ≥1 validated search term
3. All EEA techniques represented with evidence counts
4. Search terms tested and validated (or flagged for refinement)
5. Documentation complete for reproducibility

📊 **Metrics:**
- Technique coverage: 100% of EEA techniques + ≥60 literature techniques
- Search term validation rate: ≥80% successfully tested
- Database completeness: All required foreign keys populated
- Expert approval: ≥6 of 8 discipline leads approve taxonomy

---

*Document prepared: 2025-10-13*
*Status: Design Phase - Ready for Implementation*
*Next Action: Create database schema and begin population*
