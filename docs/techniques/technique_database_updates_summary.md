# Technique Database Updates Summary

**Date:** 2025-10-21
**Session:** Classification schema proposal + database restructuring

---

## Overview

This document summarizes all updates made to the techniques database in response to panelist feedback and data completeness issues.

---

## 1. Bulk Download Completed ✅

### Shark-References Database Download

**Status:** COMPLETE (Downloaded overnight 2025-10-20 to 2025-10-21)

**Results:**
- **Total papers:** 30,523 (across 76 years: 1950-2025)
- **File size:** 46 MB
- **Download time:** ~15 hours (with faster delays: 3s/1.5s)
- **Fields captured:** 14 including abstracts, keywords, PDFs, taxa
- **Output:** `outputs/shark_references_bulk/shark_references_complete_2025_to_1950_20251021.csv`

**Papers per Year Distribution:**
```
Peak year: 2014 (1,241 papers)
Recent average: 900-1,200 papers/year (2009-2024)
Early years: 50-150 papers/year (1950s-1970s)
Growth pattern: Exponential increase from 2000 onwards
```

**Visualization:** Created bar plot showing distribution across years
- File: `outputs/papers_per_year.png`
- Shows clear research explosion in 2000s

---

## 2. Classification Schema Proposal 📋

### Problem Identified

Two panelists independently identified the same core issue:

**Anouk (Genetics):**
> "Blurred distinction between theoretical concepts, methods, tools and analyses"

**Ed Lavender (Movement):**
> "Mixing: (a) technologies, (b) descriptive/heuristic methods, (c) statistical models, (d) fitting methods, (e) software"

### Examples of the Mixing

| Technique | Currently Listed As | Reality |
|-----------|-------------------|---------|
| Satellite Tracking | Technique | = Hardware (data collection technology) |
| GAM SDM | Technique | = Statistical model class |
| Marxan | Technique | = Software (implements algorithms) |
| Kernel Density | Technique | = Algorithm (computational method) |
| Hidden Markov Models | Technique | = Statistical model + inference framework |
| Population Genetics | Technique | = Conceptual field (contains many methods) |

### Proposed Solution: 6-Dimensional Binary Classification

**Add 6 new columns to spreadsheet:**

1. **is_data_collection_technology** 🔬
   - Physical instruments, lab techniques for generating data
   - Examples: Satellite Tracking, Acoustic Telemetry, RAD-seq, eDNA

2. **is_statistical_model** 📊
   - Formal mathematical/statistical model families
   - Examples: GLM, GAM, Hidden Markov Models, State-Space Models

3. **is_analytical_algorithm** 🔢
   - Computational procedures/algorithms for transforming data
   - Examples: Kernel Density, Random Forest, FST, PCA, MCP

4. **is_inference_framework** 🎯
   - Methods for fitting models to data
   - Examples: Bayesian inference, Maximum Likelihood, Kalman Filter

5. **is_software** 💻
   - Named software packages/programs
   - Examples: Marxan, STRUCTURE, Stan, R-INLA

6. **is_conceptual_field** 🌐
   - Broad research areas encompassing multiple methods
   - Examples: Population Genetics, Habitat Modeling, SDM

### Why Binary (Not Categorical)?

**Multiple techniques legitimately span categories:**

| Technique | Multiple Classifications |
|-----------|------------------------|
| MaxEnt | 🔢 ALGORITHM + 💻 SOFTWARE |
| Bayesian State-Space Models | 📊 STATISTICAL_MODEL + 🎯 INFERENCE_FRAMEWORK |
| qPCR eDNA | 🔬 TECHNOLOGY + 🔢 ALGORITHM |

**Benefits:**
- ✅ Accurate representation of multi-type entries
- ✅ Easy filtering ("show all SOFTWARE")
- ✅ Future-proof (can add dimensions)
- ✅ Makes mixing explicit, not hidden

### Pilot Classification: Movement Discipline

**32 Movement techniques classified:**

```
Distribution:
🔬 TECH:   4 techniques (12.5%) - Satellite, Acoustic, Archival Tags, VPS
📊 STAT:   4 techniques (12.5%) - GLM, GAM, HMM, SSM
🔢 ALGO:  13 techniques (40.6%) - KDE, MCP, Random Forest, etc.
🎯 INFER:  0 techniques ( 0.0%) - None explicitly listed
💻 SOFT:   2 techniques ( 6.2%) - Marxan, MaxEnt
🌐 FIELD:  9 techniques (28.1%) - Habitat Modeling, SDM, etc.

Multi-type: 1 (MaxEnt = ALGO + SOFT)
```

**Detailed classification:** See `outputs/movement_pilot_classification.csv`

### Documentation Created

1. **Full Proposal:** `docs/techniques/TECHNIQUE_CLASSIFICATION_SCHEMA_PROPOSAL.md`
   - Rationale and definitions
   - Integration of both panelists' frameworks
   - Implementation guidelines
   - Example classifications

2. **Visual Summary:** `docs/techniques/CLASSIFICATION_SCHEMA_VISUAL_SUMMARY.md`
   - Quick reference guide
   - Decision trees
   - Real-world examples
   - Use case scenarios

**Status:** ⏳ Ready for review by Anouk and Ed

---

## 3. Johann's Additions - Search Queries 🔍

### Missing Search Queries Identified

**4 yellow-highlighted rows (Johann's additions):**

| Discipline | Technique | search_query | search_query_alt |
|------------|-----------|--------------|------------------|
| BIO | Reproductive observations | ❌ Missing | ❌ Missing |
| GEN | Genetic relatedness | ❌ Missing | ❌ Missing |
| MOV | Joint Species Distribution Model | ❌ Missing | ❌ Missing |
| ??? | *(4th entry has queries)* | ✅ Present | ✅ Present |

### Proposed Search Queries Created

#### 1. Reproductive Observations (BIO)

**search_query:**
```
reproduction OR reproductive OR pregnancy OR pregnant OR gestation OR clasper OR "mating scar" OR "bite mark" OR "mating behavior" OR parturition OR embryo
```

**search_query_alt:**
```
maturity OR "sexual maturity" OR "reproductive maturity" OR gravid OR "litter size" OR fecundity OR ovary OR testis OR oviduct
```

**Rationale:** Captures both direct reproductive observations (bite marks, claspers, pregnancy) and maturity/biology terms

---

#### 2. Genetic Relatedness (GEN)

**search_query:**
```
relatedness OR kinship OR parentage OR pedigree OR "parent-offspring" OR "full-sib" OR "half-sib" OR "sibship"
```

**search_query_alt:**
```
"genetic relatedness" OR "relatedness coefficient" OR "parentage analysis" OR "parentage assignment" OR "pedigree reconstruction" OR "kinship analysis" OR paternity OR maternity
```

**Rationale:** Standard terminology in relatedness studies, includes both technical and descriptive terms

---

#### 3. Joint Species Distribution Model (MOV)

**search_query:**
```
"joint species distribution" OR "JSDM" OR "multi-species distribution" OR "multi-species model" OR "species co-occurrence"
```

**search_query_alt:**
```
"joint distribution model" OR "multivariate species distribution" OR "community distribution model" OR "species correlation" OR "multi-species SDM" OR "hierarchical model of species communities" OR "HMSC"
```

**Rationale:** Recent specialized methodology; exact phrases important; includes HMSC framework

---

### Documentation Created

**File:** `docs/techniques/JOHANN_ADDITIONS_SEARCH_QUERIES.md`
- Proposed queries with rationale
- Testing recommendations
- Classification suggestions for new entries

**Status:** ⏳ Needs Johann's review and testing on bulk database

---

## 4. Database Restructure: Deep Learning ✅

### Change Request (Maria)

> "Add Deep Learning as a category under DATA discipline and add CNN, ANN, computer vision (move these from under Machine Learning & AI)"

### Changes Made

**BEFORE:**
```
Machine Learning & AI (9 techniques):
  • Machine Learning [PARENT]
    ├─ Boosted Regression Trees
    ├─ Computer Vision
    ├─ Convolutional Neural Networks (CNN)
    ├─ Deep Learning
    ├─ Ensemble Learning
    ├─ Neural Networks (ANN)
    ├─ Random Forest
    └─ Support Vector Machines
```

**AFTER:**
```
Machine Learning & AI (5 techniques):
  • Machine Learning [PARENT]
    ├─ Boosted Regression Trees
    ├─ Ensemble Learning
    ├─ Random Forest
    └─ Support Vector Machines

Deep Learning (4 techniques):
  • Deep Learning [PARENT]
    ├─ Computer Vision
    ├─ Convolutional Neural Networks (CNN)
    └─ Neural Networks (ANN)
```

### Implementation Details

**4 techniques updated:**

1. **Deep Learning** (Row 87)
   - category_name: 'Machine Learning & AI' → 'Deep Learning'
   - is_parent: FALSE → TRUE
   - parent_technique: 'Machine Learning' → [empty]

2. **Computer Vision** (Row 85)
   - category_name: 'Machine Learning & AI' → 'Deep Learning'
   - parent_technique: 'Machine Learning' → 'Deep Learning'

3. **Convolutional Neural Networks** (Row 86)
   - category_name: 'Machine Learning & AI' → 'Deep Learning'
   - parent_technique: 'Machine Learning' → 'Deep Learning'

4. **Neural Networks** (Row 89)
   - category_name: 'Machine Learning & AI' → 'Deep Learning'
   - parent_technique: 'Machine Learning' → 'Deep Learning'

**Status:** ✅ COMPLETE - Changes saved to Excel file

---

## 5. Updated DATA Discipline Structure ✅

### Complete Category Breakdown

**Total DATA techniques: 30 (across 6 categories)**

#### 1. Bayesian Approaches (5 techniques)
- Bayesian Methods [PARENT]
  - Approximate Bayesian Computation
  - Bayesian Network Analysis
  - INLA
  - Markov Chain Monte Carlo

#### 2. Data Integration (6 techniques)
- Data Integration [PARENT]
  - Meta-Analysis
  - Cross-Validation
  - Data Fusion
  - Multi-Species Models
  - N-Mixture Models

#### 3. **Deep Learning** (4 techniques) **← NEW CATEGORY**
- Deep Learning [PARENT]
  - Computer Vision
  - Convolutional Neural Networks
  - Neural Networks

#### 4. Machine Learning & AI (5 techniques) **← REDUCED**
- Machine Learning [PARENT]
  - Boosted Regression Trees
  - Ensemble Learning
  - Random Forest
  - Support Vector Machines

#### 5. Statistical Models (6 techniques)
- GLM/GAM [PARENT]
  - GAMM
  - Generalized Estimating Equations
- Hierarchical Models [PARENT]
  - Structural Equation Modeling
  - ARIMA Models

#### 6. Time Series & Forecasting (4 techniques)
- Time Series [PARENT]
  - ARIMA
  - Forecasting
  - SARIMA

---

## Next Steps

### Immediate Actions Required

1. **Classification Schema Review**
   - [ ] Send proposal to Anouk (Genetics)
   - [ ] Send proposal to Ed (Movement)
   - [ ] Collect feedback on 6-dimension schema
   - [ ] Validate Movement discipline pilot classification

2. **Johann's Search Queries**
   - [ ] Johann reviews proposed queries
   - [ ] Test queries on bulk database:
     ```python
     import pandas as pd
     df = pd.read_csv('outputs/shark_references_bulk/shark_references_complete_2025_to_1950_20251021.csv')
     # Test each query
     ```
   - [ ] Refine based on results (expect: Reproductive 500-1500, Relatedness 100-500, JSDM 10-50)
   - [ ] Update Excel spreadsheet with final queries

3. **Database Updates**
   - [x] ✅ Deep Learning restructure (COMPLETE)
   - [ ] Add classification columns (after schema approval)
   - [ ] Populate Johann's search queries (after testing)

### Medium-Term Actions

4. **Complete Classification Schema**
   - [ ] Classify all 218 techniques using 6-dimension schema
   - [ ] Create decision tree/flowchart for classification
   - [ ] Quality check: verify FIELD entries have children, SOFTWARE has methods, etc.

5. **Literature Search**
   - [ ] Use bulk database for technique-specific searches
   - [ ] Filter and create technique CSVs
   - [ ] Distribute to panelists

6. **Database Maintenance**
   - [ ] Update in 6 months (download only 2025-2026)
   - [ ] Continuous refinement of search queries based on results

---

## Files Created/Modified

### Documentation Created

| File | Description | Status |
|------|-------------|--------|
| `docs/techniques/TECHNIQUE_CLASSIFICATION_SCHEMA_PROPOSAL.md` | Full schema proposal (comprehensive) | ✅ Complete |
| `docs/techniques/CLASSIFICATION_SCHEMA_VISUAL_SUMMARY.md` | Visual reference guide | ✅ Complete |
| `docs/techniques/JOHANN_ADDITIONS_SEARCH_QUERIES.md` | Search queries for 3 new techniques | ✅ Complete |
| `docs/techniques/TECHNIQUE_DATABASE_UPDATES_SUMMARY.md` | This document | ✅ Complete |

### Data Files

| File | Description | Size |
|------|-------------|------|
| `outputs/shark_references_bulk/shark_references_complete_2025_to_1950_20251021.csv` | Complete bulk download | 46 MB |
| `outputs/papers_per_year.png` | Visualization of papers/year | Image |
| `outputs/movement_pilot_classification.csv` | Pilot classification (32 MOV techniques) | Small |
| `outputs/johann_additions_missing_queries.csv` | Johann's entries needing queries | Small |
| `outputs/techniques_for_classification_review.csv` | All techniques for review | Small |

### Modified Files

| File | Changes | Status |
|------|---------|--------|
| `data/Techniques DB for Panel Review.xlsx` | Deep Learning restructure (4 techniques) | ✅ Saved |

---

## Statistics Summary

### Bulk Download
- **Papers:** 30,523
- **Years:** 1950-2025 (76 years)
- **Fields:** 14 per paper
- **PDFs:** ~30% have open access links

### Database Structure
- **Total techniques:** 218
- **Disciplines:** 8 (BEH, BIO, CON, DATA, FISH, GEN, MOV, TRO)
- **DATA discipline:** 30 techniques across 6 categories
- **Movement discipline:** 32 techniques (pilot for classification)

### Classification Schema
- **Dimensions:** 6 binary columns
- **Types identified:** TECH, STAT, ALGO, INFER, SOFT, FIELD
- **Multi-type entries:** Expected ~5-10% of techniques

---

## Questions for Team Review

1. **Classification Schema:**
   - Do the 6 dimensions adequately capture Anouk's and Ed's concerns?
   - Are the definitions clear and actionable?
   - Should we pilot with additional disciplines beyond Movement?

2. **Search Queries:**
   - Do Johann's proposed queries capture the right papers?
   - Should we test on bulk database before finalizing?
   - Are there missing synonyms or alternative terms?

3. **Deep Learning Restructure:**
   - Does the new category structure make sense?
   - Should any other techniques be moved or reclassified?

4. **Next Priorities:**
   - Complete classification schema first, or populate search queries?
   - Which discipline should be classified next after Movement?
   - When to start distributing technique CSVs to panelists?

---

## Contact & Review

**For classification schema questions:**
- Anouk (Genetics perspective)
- Ed Lavender (Movement perspective)

**For search queries:**
- Johann (yellow highlighted entries)

**For database structure:**
- Maria (Deep Learning restructure)

---

**Document Status:** Ready for team review
**Last Updated:** 2025-10-21
