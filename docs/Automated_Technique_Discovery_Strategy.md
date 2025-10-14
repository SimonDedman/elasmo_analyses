# Automated Technique Discovery Strategy

**Date:** 2025-10-13
**Goal:** Maximize technique database population before panelist review
**Target:** Find 30-50 additional techniques across 8 disciplines

---

## Problem Statement

Current database has **129 techniques**, but domain knowledge suggests gaps:
- **Example:** Species Distribution Models should include Random Forest, BRT, MaxEnt, GAMs, etc.
- **Issue:** Relying solely on panelists increases their workload
- **Solution:** Automated discovery of techniques from review literature

---

## Multi-Pronged Discovery Strategy

### Approach 1: Shark-References Review Paper Search 🔍

**Target:** Find recent review papers covering analytical techniques

**Method:**
```
Search Shark-References with:
- "+review +method*"
- "+review +technique*"
- "+analyt* +approach*"
- Filtered by recent years (2020-2025)
```

**Workflow:**
1. Download titles/abstracts of review papers
2. Extract technique mentions using NLP
3. Cross-reference with current list
4. Identify missing techniques

**Expected yield:** 20-30 techniques

---

### Approach 2: Exploit Existing Shark-Ref Searches ⚡

**Target:** Use planned search queries to find what we're missing

**Method:**
```r
# For each current technique, run its search query
# Extract METHOD sections from top 20 papers
# Look for technique variations mentioned

Example:
- Search: "+telemetry +acoustic"
- Papers mention: "VPS", "VRAP", "receiver arrays", "detection range"
- Add these as sub-techniques
```

**Workflow:**
1. Run each of 129 search queries (limit 20 results each)
2. Parse paper abstracts/methods for technique keywords
3. Build co-occurrence matrix (techniques mentioned together)
4. Identify missing techniques in clusters

**Expected yield:** 15-25 techniques

---

### Approach 3: Domain-Specific Review Mining 🎓

**Target:** Known authoritative review papers in each discipline

**Sources to mine:**

#### BIO - Biology
- "Methods in elasmobranch age determination" reviews
- "Reproductive biology techniques" reviews
- PubMed search: `("elasmobranch" OR "shark" OR "ray") AND "review" AND ("age" OR "growth" OR "reproduction")`

#### BEH - Behaviour
- "Behavioural observation methods" reviews
- "Animal-borne sensors" reviews
- "Accelerometry classification" technique papers

#### TRO - Trophic
- "Stable isotope analysis in marine ecology" (standard methods)
- "Diet analysis techniques" reviews
- "Mixing models" (SIAR, MixSIAR, IsotopeR)

#### GEN - Genetics
- "Population genomics of elasmobranchs" reviews
- "eDNA methods" reviews
- "Close-kin mark-recapture" (recent advancement)

#### MOV - Movement
- "Telemetry data analysis" reviews
- "Home range estimators" (KDE, MCP, Brownian bridge, etc.)
- "Hidden Markov Models for movement"

#### FISH - Fisheries
- "Stock assessment methods" (FAO manuals)
- "Data-poor methods" reviews
- "CPUE standardization approaches" (GLM, GAM, RF, etc.)

#### CON - Conservation
- "IUCN Red List methodology"
- "Marine spatial planning" reviews
- "Stakeholder engagement methods"

#### DATA - Data Science
- **SDM methods:** RF, BRT, MaxEnt, GAM, GLM, Neural Networks, Ensemble
- **Bayesian methods:** INLA, Stan, JAGS
- **Machine learning:** CNN, SVM, XGBoost
- "Machine learning in ecology" reviews

**Workflow:**
1. Search for authoritative reviews (Google Scholar, PubMed)
2. Extract methods sections
3. Build technique lists by discipline
4. Cross-check with our database

**Expected yield:** 25-40 techniques

---

### Approach 4: Methodological Hierarchy Expansion 📊

**Target:** Fill out sub-technique hierarchies systematically

**Method:** For each parent technique, identify standard sub-methods

**Examples:**

#### Current: Species Distribution Models (parent only)
**Add sub-techniques:**
- Random Forest
- Boosted Regression Trees (BRT)
- MaxEnt
- Generalized Additive Models (GAMs)
- Generalized Linear Models (GLMs)
- Ensemble Models
- Neural Network SDMs

#### Current: Home Range Analysis (parent only)
**Add sub-techniques:**
- Kernel Density Estimation (KDE)
- Minimum Convex Polygon (MCP)
- Brownian Bridge Movement Models
- Utilization Distributions
- Dynamic Brownian Bridge

#### Current: Stock Assessment (parent only)
**Add sub-techniques:**
- Age-Structured Models
- Length-Based Models
- Surplus Production Models
- Statistical Catch-at-Age (SCA)
- Virtual Population Analysis (VPA)
- Integrated Stock Assessment

#### Current: Stable Isotope Analysis (parent only)
**Add sub-techniques:**
- Bulk SIA
- Compound-Specific SIA (CSIA)
- Amino Acid SIA
- Mixing Models (SIAR, MixSIAR, IsoSpace)

**Workflow:**
1. Identify all parent techniques with missing obvious sub-techniques
2. Use textbook/manual knowledge to list standard methods
3. Validate via Google Scholar searches
4. Add to database with `data_source = "method_expansion"`

**Expected yield:** 30-50 techniques

---

### Approach 5: Cross-Disciplinary Technique Transfer 🔄

**Target:** Techniques used in one discipline but applicable to others

**Examples:**
- **Machine Learning:** Currently mostly in DATA, but used across MOV, FISH, BEH
- **Bayesian Methods:** Used in FISH, MOV, TRO, BIO
- **Accelerometry:** In BEH, but also used in MOV and TRO (energy expenditure)
- **Video Analysis:** In BEH, but also used in TRO (feeding), CON (tourism impact)

**Workflow:**
1. Identify cross-cutting techniques
2. Check which disciplines currently have them
3. Add to disciplines where they're commonly used but missing
4. Mark with `data_source = "cross_discipline"`

**Expected yield:** 10-20 techniques

---

## Automated Web Scraping Strategy

### Step 1: Google Scholar API / Scraping

```python
# Pseudo-code for review paper discovery
search_terms = [
    "elasmobranch analytical methods review",
    "shark research techniques review",
    "marine fish stock assessment methods",
    "telemetry data analysis methods",
    "species distribution modeling review",
    # ... for each discipline
]

for term in search_terms:
    papers = scholar.search(term, year_low=2020, year_high=2025)
    for paper in papers[:20]:  # Top 20 results
        extract_methods(paper.abstract)
        extract_methods(paper.pdf) if available
```

### Step 2: Shark-References Targeted Mining

```r
# R script to mine Shark-References
library(rvest)
library(httr)

# For each discipline, search for methodology papers
disciplines <- c("age determination", "telemetry", "stable isotope",
                 "stock assessment", "IUCN assessment", etc.)

for (disc in disciplines) {
    query <- paste0("+", disc, " +method*")
    # Run search on Shark-References
    # Parse results
    # Extract technique keywords from abstracts
}
```

### Step 3: PubMed / Scopus API Queries

```python
# Systematic literature search
from Bio import Entrez

search_queries = {
    "BIO": "elasmobranch[All] AND (age[Title] OR growth[Title]) AND method[Title]",
    "MOV": "shark[All] AND telemetry[Title] AND (analysis[Title] OR method[Title])",
    "FISH": "elasmobranch[All] AND stock assessment[Title] AND method[Title]",
    # ... etc.
}

for discipline, query in search_queries.items():
    results = Entrez.esearch(db="pubmed", term=query, retmax=100)
    # Extract abstracts
    # Parse for technique mentions
```

---

## NLP-Based Technique Extraction

### Method Keywords to Detect

```python
method_indicators = [
    "we used", "we applied", "using", "via", "through",
    "analysis was conducted", "estimated using", "calculated with",
    "implemented in", "performed using"
]

technique_patterns = [
    r"(\w+\s)?(?:random forest|RF|boosted regression|BRT)",
    r"(?:generalized )?(?:linear|additive) model(?:s)?\s?\(?(?:GLM|GAM|GAMM)?\)?",
    r"kernel density estimation|KDE",
    r"maximum entropy|MaxEnt|Maxent",
    # ... hundreds more patterns
]
```

### Workflow:
1. Download paper abstracts/methods sections
2. Identify sentences containing method indicators
3. Extract technique names using regex patterns
4. Validate extracted terms (remove false positives)
5. Cross-reference with current database
6. Add missing techniques

---

## Specific Gaps to Target

Based on domain knowledge, prioritize finding:

### MOV - Movement & Habitat (HIGH PRIORITY)
- [ ] Random Forest (for SDM)
- [ ] Boosted Regression Trees
- [ ] MaxEnt
- [ ] GAMs (if not already general)
- [ ] Kernel Density Estimation
- [ ] Minimum Convex Polygon
- [ ] Brownian Bridge Models
- [ ] Hidden Markov Models
- [ ] State-Space Models (movement)
- [ ] Resource Selection Functions
- [ ] Step Selection Functions

### FISH - Fisheries
- [ ] Virtual Population Analysis (VPA)
- [ ] Spawning Stock Biomass per Recruit
- [ ] Yield per Recruit
- [ ] Leslie-DeLury models
- [ ] Catch Curve Analysis
- [ ] Mortality estimators (Hoenig, Pauly, etc.)
- [ ] LIME (Length-based Integrated Mixed Effects)
- [ ] SS3 (Stock Synthesis)

### TRO - Trophic
- [ ] SIAR (Stable Isotope Analysis in R)
- [ ] MixSIAR
- [ ] IsoSpace
- [ ] Trophic position calculation
- [ ] Rayleigh test (for diet preference)
- [ ] PERMANOVA (for diet comparisons)

### DATA - Data Science
- [ ] XGBoost
- [ ] Gradient Boosting Machines
- [ ] Support Vector Machines (SVM)
- [ ] Convolutional Neural Networks (CNN)
- [ ] INLA (Integrated Nested Laplace Approximation)
- [ ] Stan (Bayesian)
- [ ] JAGS (Bayesian)
- [ ] Ensemble modeling
- [ ] Cross-validation methods

### BEH - Behaviour
- [ ] Hidden Markov Models (behavioural states)
- [ ] Ethogram development
- [ ] Focal sampling
- [ ] Scan sampling
- [ ] BORIS (video analysis software)
- [ ] DeepLabCut (pose estimation)

### GEN - Genetics
- [ ] STRUCTURE (population structure)
- [ ] ADMIXTURE
- [ ] PCA (genetic)
- [ ] DAPC (Discriminant Analysis of Principal Components)
- [ ] FST calculations
- [ ] Tajima's D
- [ ] Nucleotide diversity (π)

---

## Implementation Plan

### Phase 1: Quick Wins (Hours 1-4)
1. **Hierarchical expansion** - Add obvious sub-techniques to parents
   - Target: 30-40 techniques
   - Method: Domain knowledge + quick Wikipedia/Google checks

2. **Cross-discipline transfer** - Add ML/Bayesian methods to relevant disciplines
   - Target: 10-15 techniques

### Phase 2: Literature Mining (Hours 5-12)
3. **Google Scholar search** - Find 5-10 key review papers per discipline
   - Target: 20-30 techniques

4. **Shark-References mining** - Run targeted searches for methodology papers
   - Target: 15-20 techniques

### Phase 3: Systematic Search (Hours 13-24)
5. **PubMed/Scopus API** - Systematic literature search
   - Target: 20-30 techniques

6. **NLP extraction** - Parse abstracts for technique mentions
   - Target: 10-20 techniques

### Phase 4: Validation (Hours 25-30)
7. **Deduplicate** - Remove overlaps
8. **Validate** - Ensure techniques are legitimate and commonly used
9. **Add to database** - Populate all 3 files (MD, CSV, XLSX)

---

## Success Metrics

**Goal:** Add 50-80 techniques before panelist review

**Current:** 129 techniques
**Target:** 180-210 techniques (40-60% increase)

**Quality criteria:**
- ✅ Each technique has clear description
- ✅ Search query defined (can be refined later)
- ✅ Properly categorized by discipline
- ✅ Parent/child relationships correct
- ✅ Commonly used in field (not obscure)

---

## Tools & Resources

### Automated Tools:
1. **Shark-References** - Primary literature source
2. **Google Scholar** - Review paper discovery
3. **PubMed API** - Biomedical literature
4. **Scopus API** - Citation database
5. **Web scraping** - For non-API sources

### Manual Resources:
1. **Textbooks** - Standard methods references
2. **FAO manuals** - Fisheries stock assessment
3. **IUCN guidelines** - Conservation assessment
4. **R packages** - Method documentation (e.g., `move`, `adehabitatHR`, `TMB`)

### NLP Tools:
1. **SpaCy** - Named entity recognition
2. **NLTK** - Text processing
3. **Regex patterns** - Technique name extraction

---

## Next Steps

**Immediate action items:**

1. ✅ Start with **hierarchical expansion** (fastest, highest yield)
   - Focus on MOV (SDM methods), FISH (stock assessment), DATA (ML/Bayes)

2. ✅ Quick Google Scholar search for 2-3 key reviews per discipline

3. ✅ Build initial list of 30-50 techniques to add

4. ✅ Validate and add to master CSV

5. ✅ Regenerate XLSX and update MD documentation

---

*Strategy developed: 2025-10-13*
*Ready for implementation*
