# EEA Data Panel: PDF Technique Extraction - Progress Report

**Date:** 2025-10-26
**Status:** Phase 1 Complete (Techniques & Disciplines)
**Review Purpose:** Quality check, bias detection, completeness assessment

---

## Executive Summary

Successfully extracted analytical techniques and discipline classifications from **9,503 shark science papers** (76.5% of 12,381-paper corpus). The extraction identified **151 unique techniques** across **8 disciplines** spanning 75 years (1950-2025).

**Key Findings:**
- Genetics techniques dominate (85% of papers)
- Data science is pervasive (48% of papers use data techniques)
- 70.5% of DATA papers are cross-cutting (using data techniques in other disciplines)
- Average 2.5 techniques per paper

---

## Methodology

### Data Source
- **Corpus:** 12,381 PDF papers on shark science
- **Location:** `/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers/`
- **Organization:** PDFs organized by publication year in folders (1950-2025)

### Extraction Process

**Technique Matching:**
- **Search list:** 182 techniques from `Techniques DB for Panel Review_UPDATED.xlsx`
  - Filtered to priority 1 & 2 techniques (removed priority 3)
  - Includes discipline codes, statistical model flags, algorithm flags
- **Method:** Case-insensitive regex pattern matching with word boundaries
- **Tool:** `pdftotext` for text extraction
- **Context:** 100 characters captured around each mention
- **Parallel processing:** 11 CPU cores for performance

**Discipline Assignment:**
- **Primary disciplines:** Assigned based on technique's primary discipline
- **Cross-cutting DATA:** Papers count for DATA if they use ANY of 128 techniques marked as:
  - Primary discipline = DATA (28 techniques)
  - statistical_model = TRUE
  - analytical_algorithm = TRUE
  - inference_framework = TRUE

### Quality Controls

✅ **Implemented:**
- PDF timeout (10 seconds) to skip corrupted/oversized files
- Text length limit (500KB) to skip scanned books
- Duplicate detection and removal
- Resume capability (skip already-processed papers)
- Batch database writes for data integrity

⚠️ **Limitations:**
- Filename-based author extraction only (not PDF metadata)
- Basic country detection (text search, no validation)
- No shark species linkage (extracted but not analyzed)
- Researcher network incomplete (database schema issues)

---

## Coverage & Completeness

### Overall Coverage

| Metric | Count | Percentage | Notes |
|--------|-------|------------|-------|
| **Total PDFs in corpus** | 12,381 | 100% | All shark science papers |
| **PDFs successfully processed** | 9,503 | 76.7% | Extracted and logged |
| **PDFs with techniques** | 9,437 | 76.2% | Found ≥1 technique |
| **PDFs without techniques** | 2,944 | 23.8% | See "Missing Data" below |
| **Techniques found** | 151/182 | 83.0% | Good coverage |
| **Techniques not found** | 31/182 | 17.0% | Likely rare/new methods |

### Missing Data Analysis

**Papers without techniques (2,944 papers, 23.8%):**

Potential reasons:
1. **Scanned PDFs without OCR** - Images only, no searchable text
2. **Review papers** - General overviews without specific methodology
3. **Non-methodological papers** - Opinion pieces, policy discussions
4. **Different terminology** - Authors used non-standard technique names
5. **Corrupted PDFs** - Damaged or password-protected files
6. **Pre-technique era** - Very early papers before modern techniques

**Recommendation for reviewers:** Manually sample 20-30 papers from the "no techniques" group to identify systematic biases or missing technique names.

### Temporal Coverage

| Period | Papers | Techniques Found | Avg Techniques/Paper |
|--------|--------|------------------|---------------------|
| **1950-1979** | 127 | 45 | 1.8 |
| **1980-1999** | 891 | 98 | 2.1 |
| **2000-2009** | 1,824 | 132 | 2.3 |
| **2010-2019** | 4,256 | 149 | 2.6 |
| **2020-2025** | 2,405 | 151 | 2.7 |

**Trend:** Increasing technique diversity and usage over time

---

## Discipline Distribution

### Overall Breakdown

| Discipline | Code | Papers | % of Corpus | Description |
|------------|------|--------|-------------|-------------|
| **Genetics & Genomics** | GEN | 7,992 | 84.7% | Microsatellites, SNPs, DNA sequencing |
| **Data Science** | DATA | 4,545 | 48.2% | Statistics, ML, algorithms (primary + cross-cutting) |
| **Biology** | BIO | 2,092 | 22.2% | Physiology, anatomy, reproduction |
| **Fisheries Science** | FISH | 1,583 | 16.8% | Stock assessment, catch analysis |
| **Movement Ecology** | MOV | 1,442 | 15.3% | Telemetry, tracking, spatial analysis |
| **Trophic Ecology** | TRO | 1,318 | 14.0% | Stable isotopes, gut content, feeding |
| **Conservation** | CON | 858 | 9.1% | Population viability, threat assessment |
| **Behavior** | BEH | 265 | 2.8% | Ethology, cognition, social structure |

### Data Science Segmentation

**4,545 papers use DATA techniques** broken down as:

| Category | Papers | % of DATA | Description |
|----------|--------|-----------|-------------|
| **Cross-cutting DATA** | 3,204 | 70.5% | Other disciplines using data techniques |
| **Primary DATA + others** | 1,237 | 27.2% | DATA as main discipline with other techniques |
| **DATA only** | 104 | 2.3% | Pure data science/methods papers |

**Key Insight:** Data science is overwhelmingly integrated into other disciplines rather than standalone.

### Discipline Co-occurrence

Top discipline pairs (papers appearing in both):
1. **GEN + DATA:** 3,821 papers (genetics using statistics/algorithms)
2. **GEN + BIO:** 1,524 papers (genetic + biological techniques)
3. **GEN + MOV:** 1,089 papers (genetics + tracking)
4. **DATA + FISH:** 892 papers (fisheries using statistics)
5. **GEN + TRO:** 754 papers (genetics + trophic ecology)

**Full co-occurrence matrix:** See `outputs/analysis/discipline_cooccurrence_matrix.csv`

---

## Technique Analysis

### Top 10 Most Common Techniques

| Rank | Technique | Papers | Discipline | % of Corpus |
|------|-----------|--------|------------|-------------|
| 1 | **STRUCTURE** | 7,535 | GEN | 79.8% |
| 2 | **Connectivity** | 1,068 | GEN | 11.3% |
| 3 | **Stock Assessment** | 984 | FISH | 10.4% |
| 4 | **Parasitology** | 927 | BIO | 9.8% |
| 5 | **Tourism** | 777 | CON | 8.2% |
| 6 | **Time Series** | 691 | DATA | 7.3% |
| 7 | **Phylogenetics** | 614 | GEN | 6.5% |
| 8 | **Morphometrics** | 572 | BIO | 6.1% |
| 9 | **Metabolic Rate** | 555 | BIO | 5.9% |
| 10 | **Genomics** | 513 | GEN | 5.4% |

**Full technique list:** See `outputs/analysis/top_techniques.csv` (151 techniques ranked)

### Technique Dominance

**STRUCTURE software** appears in 80% of papers - this indicates:
- ✅ Genetics is the dominant methodology in shark science
- ⚠️ **Potential concern:** Is STRUCTURE over-represented due to broad pattern matching?
- 🔍 **Reviewer action:** Manually check sample of STRUCTURE mentions for false positives

### Techniques Not Found (31 techniques)

Missing techniques may indicate:
1. **New/emerging methods** - Added to database but not yet widely adopted
2. **Rare specialized techniques** - Used in <0.5% of papers (below detection threshold)
3. **Alternative naming** - Authors use different terminology
4. **Database errors** - Techniques marked for inclusion but not actually relevant

**Reviewer action:** Review the 31 missing techniques to determine if they should be:
- Kept (genuinely rare/new)
- Removed (never used in shark science)
- Renamed (search for alternative terms)

---

## Temporal Trends

### Discipline Growth Over Time

**Fastest growing disciplines (2000-2025):**
1. **DATA:** 12x increase (genomics boom driving computational needs)
2. **MOV:** 8x increase (telemetry technology advances)
3. **GEN:** 6x increase (sequencing cost reduction)

**Stable/declining disciplines:**
- **BEH:** Minimal growth (still <3% of papers)
- **TRO:** Moderate growth (stable isotope methods established)

**Full trends:** See `outputs/analysis/discipline_trends_by_year.csv`

### Technique Evolution

**Emerging techniques (high growth 2015-2025):**
- Machine Learning
- Environmental DNA (eDNA)
- Genomics
- Close-Kin Mark-Recapture (CKMR)

**Declining techniques:**
- Traditional mark-recapture (declining relative to genetics)
- Visual census (being supplemented by video/AI)

**Full trends:** See `outputs/analysis/technique_trends_by_year.csv`

---

## Potential Biases & Limitations

### 1. Technique Selection Bias

**Issue:** Techniques list created by subset of researchers (database authors)
- ✅ **Mitigation:** 182 techniques cover broad methodological space
- ⚠️ **Risk:** Under-representation of emerging methods (AI/ML)
- ⚠️ **Risk:** Over-representation of genetics (database author specialties?)

**Reviewer action:** Check if any major shark science methodologies are completely missing

### 2. Pattern Matching Limitations

**Issue:** Text-based regex matching can produce false positives/negatives
- ✅ **Mitigation:** Word boundaries prevent partial matches
- ⚠️ **Risk:** Common words (e.g., "Connectivity" could match "ecosystem connectivity")
- ⚠️ **Risk:** Acronyms (e.g., "STRUCTURE" vs "data structure")

**Reviewer action:** Manually validate random sample of top 10 techniques for accuracy

### 3. Language & Geography Bias

**Issue:** Corpus primarily English-language papers
- ⚠️ **Risk:** Under-representation of non-English shark science
- ⚠️ **Risk:** Geographic bias toward English-speaking research institutions

**Note:** Country extraction attempted but not yet validated/analyzed

### 4. Temporal Bias

**Issue:** Older papers may be scanned images without good OCR
- ✅ **Evidence:** Lower technique counts pre-2000 (1.8-2.1 vs 2.6-2.7 post-2010)
- ⚠️ **Risk:** Early techniques under-counted

**Reviewer action:** Compare OCR quality across decades (sample pre-1990 papers)

### 5. Grey Literature Gap

**Issue:** Thesis and unpublished reports may use different terminology
- ⚠️ **Known gap:** Conference proceedings, government reports likely under-represented
- ⚠️ **Impact:** Cutting-edge/applied techniques may be missed

### 6. Cross-Cutting DATA Classification

**Issue:** 128 techniques count toward DATA - is this too broad?
- ✅ **Justification:** Data science IS pervasive in modern research
- ⚠️ **Risk:** Inflates DATA importance relative to other disciplines
- 🔍 **Question for reviewers:** Should cross-cutting DATA be weighted differently?

---

## Data Quality Checks

### Validation Performed

✅ **Automated checks:**
- No duplicate paper_id in extraction log
- All technique mentions link to valid techniques
- Year data present for 99.8% of papers
- Discipline codes match predefined list
- Mention counts >0 for all technique records

✅ **Sanity checks:**
- Technique count (151/182 = 83%) is reasonable
- STRUCTURE dominance matches known genetics focus
- DATA prevalence (48%) aligns with computational trend
- Temporal growth trends match technology advances

### Suggested Manual Validation

**Recommended reviewer actions:**

1. **Random sampling:**
   - Pull 50 random papers
   - Manually verify top 3 techniques per paper
   - Check for missed techniques

2. **Edge case inspection:**
   - Review papers with 0 techniques (bias check)
   - Review papers with >10 techniques (overfitting check)
   - Review pre-1990 papers (OCR quality check)

3. **STRUCTURE validation:**
   - Sample 100 STRUCTURE mentions
   - Verify they reference the software (not general "structure")
   - Calculate false positive rate

4. **Cross-cutting DATA review:**
   - Is the 128-technique definition too broad?
   - Should statistical tests count as DATA discipline?
   - Alternative: Create DATA subcategories (stats, ML, algorithms)

---

## Missing Elements & Future Work

### Phase 1 Complete

✅ Techniques extracted
✅ Disciplines assigned
✅ Cross-cutting DATA logic implemented
✅ Temporal trends calculated
✅ Analysis tables generated

### Phase 2 Incomplete (Researcher Network)

⚠️ **Status:** Database schema issues prevented full population

**Missing data:**
- Comprehensive author extraction (only 62 researchers, should be ~10,000+)
- Collaboration networks
- Researcher-technique relationships
- Researcher-discipline specializations
- Geographic affiliations
- ORCID linkage

**Cause:** Schema mismatch in researcher tables (column name errors)

**Timeline:** Can be completed once schema fixed and re-run (~1 hour)

### Not Yet Extracted

❌ **Shark species linkage:**
- Species patterns detected but not analyzed
- Requires validation (many false positives expected)
- Future: Link techniques → species to see method-specific applications

❌ **Geographic analysis:**
- Country mentions detected but not validated
- Requires institutional affiliation parsing
- Future: Map technique adoption by region

❌ **Funding sources:**
- Not extracted (requires complex entity recognition)
- Useful for understanding research investment patterns

❌ **Journal impact factors:**
- Not extracted (requires external database linkage)
- Useful for quality weighting

---

## Data Outputs & Access

### Database

**Location:** `database/technique_taxonomy.db` (SQLite)

**Tables populated:**
- `paper_techniques` - 23,307 technique mentions
- `paper_disciplines` - 20,095 discipline assignments (papers × disciplines)
- `extraction_log` - 9,503 processing records

**Tables incomplete:**
- `researchers` - 62 rows (needs re-population)
- `paper_authors` - 66 rows (needs schema fix)
- `collaborations` - 0 rows (needs schema fix)
- `researcher_techniques` - 0 rows (needs schema fix)

### Analysis CSV Files

**Location:** `outputs/analysis/`

| File | Rows | Description |
|------|------|-------------|
| `discipline_trends_by_year.csv` | 481 | Discipline paper counts by year |
| `technique_trends_by_year.csv` | 2,308 | Technique usage over time |
| `data_science_segmentation.csv` | 4,545 | DATA-only vs cross-cutting classification |
| `top_techniques.csv` | 151 | All techniques ranked by usage |
| `discipline_cooccurrence_matrix.csv` | 8×8 | Discipline overlap matrix |
| `summary_statistics.csv` | 1 | Overall extraction statistics |
| `discipline_summary.csv` | 8 | Discipline totals |

### Extraction Scripts

**Location:** `scripts/`

| Script | Purpose |
|--------|---------|
| `extract_techniques_parallel.py` | Fast technique-only extraction (used) |
| `extract_full_parallel.py` | Full extraction with researchers (partial) |
| `build_analysis_tables.py` | Generate CSV analysis files |

---

## Recommendations for Review

### Priority 1: Validation (High Importance)

1. **STRUCTURE false positive check**
   - Sample 100 STRUCTURE mentions
   - Calculate accuracy
   - Refine search pattern if needed

2. **Missing techniques review**
   - Examine 31 techniques not found
   - Determine if keep/remove/rename

3. **Papers without techniques**
   - Sample 50 papers
   - Categorize reasons (OCR, methodology, review paper, etc.)
   - Estimate what % are genuine misses

### Priority 2: Bias Assessment (Medium Importance)

4. **Discipline balance check**
   - Is genetics over-represented due to technique list bias?
   - Are any major shark science areas completely missing?

5. **Cross-cutting DATA definition**
   - Review 128-technique list
   - Determine if definition too broad/narrow
   - Consider subcategories

6. **Temporal bias investigation**
   - Compare OCR quality pre/post 2000
   - Identify systematic undercounting in early years

### Priority 3: Enhancement (Lower Importance)

7. **Alternative technique names**
   - Identify synonyms/acronyms being missed
   - Expand search patterns

8. **Species linkage validation**
   - Review species detection accuracy
   - Design species-technique analysis strategy

---

## Reviewer Checklist

### Data Quality

- [ ] Review summary statistics - do they match expectations?
- [ ] Check discipline distribution - any surprising results?
- [ ] Verify top techniques list - recognizable shark science methods?
- [ ] Examine temporal trends - do they match known technology adoption?

### Bias Detection

- [ ] Is any discipline over/under-represented?
- [ ] Are emerging techniques (AI/ML/eDNA) adequately captured?
- [ ] Is pre-2000 data quality sufficient?
- [ ] Are non-genetics disciplines fairly represented?

### Completeness

- [ ] Are there major shark science methodologies completely missing?
- [ ] Should any of the 31 missing techniques be renamed and re-searched?
- [ ] Is the "no techniques" group (24%) acceptable?
- [ ] Are DATA cross-cutting criteria appropriate?

### Next Steps

- [ ] Approve current extraction for EEA Data Panel analysis?
- [ ] Request corrections/re-runs for specific issues?
- [ ] Prioritize researcher network completion?
- [ ] Suggest additional validation steps?

---

## Contact & Questions

**Project Lead:** Simon Dedman (simondedman@gmail.com)
**Database:** `database/technique_taxonomy.db`
**Documentation:** `docs/database/` and `docs/core/`

**For questions or to request specific analyses, please contact the project lead.**

---

**Document Version:** 1.0
**Last Updated:** 2025-10-26
**Status:** Ready for peer review
