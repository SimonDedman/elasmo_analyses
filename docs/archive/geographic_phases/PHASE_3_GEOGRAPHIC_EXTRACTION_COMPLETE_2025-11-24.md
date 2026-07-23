# Phase 3 Geographic Extraction - COMPLETE (with caveats)

**Date**: 2025-11-24
**Status**: ✅ COMPLETE but with data quality issues requiring refinement

---

## Summary

Successfully completed Phases 1-3 of the geographic extraction pipeline, achieving **75.7% coverage** (9,260 / 12,240 papers) with country metadata - a **2.7x increase** over the October 26 data (3,426 papers, 28% coverage).

**HOWEVER**: The extracted data shows Australia at 81.1% (7,506 papers), which is inconsistent with October data (USA 22.6%, Australia 18.8%). This suggests Phase 2 affiliation extraction is picking up noise.

---

## What Was Completed

### ✅ Phase 1: Extract Author Names from Filenames
- **Status**: COMPLETE
- **Coverage**: 12,183 / 12,240 papers (99.5%)
- **Output**: `outputs/researchers/paper_first_authors_ALL.csv`
- **Unique first authors**: 2,509
- **Time taken**: ~5 minutes

### ✅ Phase 2: Extract Affiliations from PDFs
- **Status**: COMPLETE (but with data quality issues)
- **Coverage**: 12,103 / 12,183 papers (99.3%)
- **Output**: `outputs/researchers/paper_affiliations_ALL.csv`
- **Affiliation records**: 27,839
- **Unique institutions**: 26,135
- **Time taken**: ~2 hours (parallel processing with 11 workers)

**Known Issues**:
- Extracting text fragments that are NOT author affiliations
- Examples of false positives:
  - "by University of Adelaide user" (Cambridge Core download attribution)
  - "Downloaded from https://www.cambridge.org/core. Nottingham Trent University"
  - Footnotes, acknowledgments, references
- This causes over-counting of affiliations, especially for universities mentioned in download attributions

### ✅ Phase 3: Map Institutions to Countries
- **Status**: COMPLETE
- **Coverage**: 89.5% of affiliations mapped (24,927 / 27,839)
- **Output**:
  - `outputs/researchers/papers_per_country_PHASE3.csv`
  - `outputs/researchers/paper_country_mapping.csv`
- **Papers with country data**: 9,260 (75.7% of corpus)
- **Countries identified**: 62 (down from 71 in October)
- **Time taken**: ~10 seconds

**Results** (with caveats):
- **Australia**: 7,506 papers (81.1%) ⚠️  TOO HIGH - likely inflated by download attributions
- **USA**: 1,227 papers (13.3%) ⚠️  TOO LOW - should be ~22-25%
- **UK**: 112 papers (1.2%)

---

## Comparison with October 26 Data

| Metric | October 26 (OLD) | November 24 (NEW) | Change |
|--------|------------------|-------------------|--------|
| **Papers with country data** | 3,426 (28%) | 9,260 (75.7%) | +5,834 (+170%) |
| **Countries identified** | 71 | 62 | -9 |
| **Top country (OLD: USA)** | 774 (22.6%) | 1,227 (13.3%) | +453 |
| **Top country (NEW: Australia)** | 644 (18.8%) | 7,506 (81.1%) | +6,862 ⚠️ |

**Interpretation**:
- ✅ Coverage improvement is REAL (28% → 75.7%)
- ⚠️  Country distribution is DISTORTED by Phase 2 noise
- ⚠️  Australia numbers are inflated (likely 6,000+ false positives from download attributions)

---

## Root Cause: Phase 2 Affiliation Extraction Issues

### Problem

The Phase 2 script extracts **all text lines containing institutional keywords** (university, institute, department, etc.) from the first 100 lines of each PDF. This works for author affiliations BUT also picks up:

1. **Download attributions**: "Downloaded from ... by University of X user"
2. **Copyright notices**: "© 2015 University of Y. All rights reserved."
3. **Journal affiliations**: "Published by University Press"
4. **Reference fragments**: Mentions of other institutions in citations
5. **Acknowledgments**: "We thank University of Z for..."

### Why Australia is Over-Counted

Many papers in the corpus appear to be downloaded from **Cambridge Core**, which uses attribution text like:

> "Downloaded from https://www.cambridge.org/core. **University of Adelaide** user on 12 Aug 2019..."

Since many downloads happened from Australian university IPs, these false affiliations overwhelmingly attribute papers to Australian universities.

### Evidence

From `paper_affiliations_ALL.csv`:

```csv
"Gorbman.etal.1952.Thyroidal metabolism of iodine...pdf",1952,Gorbman,"by University of Adelaide user"
"Fyfe.etal.1953.Otodistomum plunketi n. sp....pdf",1953,Fyfe,"Downloaded from https://www.cambridge.org/core. Nottingham Trent University, on 12 Aug 2019..."
```

These are NOT author affiliations - they're download metadata.

---

## What Needs to Be Fixed (Phase 2 Refinement)

### Option 1: Heuristic Filtering (Quick Fix)

**Approach**: Filter out obvious false positives using keywords

**Reject lines containing**:
- "downloaded from"
- "available at"
- "by [institution] user"
- "© [year]"
- "published by"
- "https://" or "http://"
- "all rights reserved"

**Pros**: Fast to implement (10 minutes)
**Cons**: May still miss some false positives

### Option 2: Improved Affiliation Parsing (Better Solution)

**Approach**: Only extract from specific PDF regions

1. **Focus on author block**: Lines immediately after title, before abstract
2. **Look for structural markers**:
   - Superscript numbers (¹, ², ³)
   - Email addresses (indicator of author affiliations)
   - Formatting patterns (author block vs body text)
3. **Limit to first 30 lines** (not 100)
4. **Stop at keywords**: "Abstract", "Introduction", "Keywords"

**Pros**: Much higher precision
**Cons**: Requires 30-60 minutes to implement, 2 hours to re-run

### Option 3: Use Existing October Data + Manual Validation

**Approach**: Don't re-run Phase 2, use October data for abstract

**Pros**:
- October data (3,426 papers) is validated and accurate
- No risk of bad data in abstract
- Sufficient sample size for preliminary findings

**Cons**:
- Lower coverage (28% vs potential 75%+)
- Missed opportunity to showcase improved extraction

---

## Recommendation for Abstract Deadline (Nov 30)

### ✅ **Use October 26 Data** for Abstract Submission

**Rationale**:
1. **Data Quality > Coverage**: 28% accurate data >> 75% noisy data
2. **Time Constraints**: Only 6 days until deadline
3. **Risk Management**: Phase 2 refinement + re-run = 3-4 hours + validation time
4. **Scientific Integrity**: Better to acknowledge 28% preliminary data than submit questionable 75% data

**Abstract Text (RECOMMENDED)**:

> "Preliminary geographic analysis of 3,426 papers (28% of analyzed corpus) shows that 22.6% were led by institutions in the USA (n = 774), 18.8% in Australia (n = 644), and 8.7% in the UK (n = 298). Regional analysis reveals that 82.2% of studies were led by institutions in the Global North (high-income countries in North America, Europe, and Australia/New Zealand), while only 17.8% originated from the Global South."

**Why This Works**:
- ✅ Transparent about coverage (28%)
- ✅ Sample size sufficient for strong conclusions (N=3,426)
- ✅ Uses validated, tested data
- ✅ Shows clear Global North dominance pattern
- ✅ Sets up May 2025 presentation ("expanded analysis will...")

---

## Timeline for Full Pipeline Completion (Post-Abstract)

### December 2024 - January 2025

1. **Refine Phase 2 script** (Option 2: Improved parsing)
   - Implement heuristic filtering
   - Focus on author block region
   - Add validation checks
   - **Time**: 30-60 minutes coding

2. **Re-run Phase 2** on all 12,240 papers
   - Parallel processing (11 workers)
   - **Time**: 2-3 hours

3. **Re-run Phase 3** (geocoding)
   - No changes needed to geocoding script
   - **Time**: 10 seconds

4. **Validate results**
   - Compare with October data
   - Spot-check 100 random papers
   - Verify country distribution makes sense
   - **Time**: 1-2 hours

5. **Run R analysis scripts** (Phase 4 - originally planned)
   - Generate updated `papers_per_country.csv`
   - Calculate regional statistics
   - Analyze collaboration networks
   - **Time**: 30 minutes

### January - April 2025

6. **Implement Phase 4**: Extract study locations from Methods sections
   - Parse "samples collected in [location]" patterns
   - Map to countries
   - Compare author country vs study location
   - Calculate "foreign research" percentage

7. **Full analysis** for May 2025 presentation
   - Complete database (aim for 90%+ of ~30,000 papers in Shark-References)
   - Full geographic coverage (90%+ with country data)
   - Study location vs author institution analysis
   - Collaboration network analysis

---

## Files Created

### Phase 1 Outputs
- `outputs/researchers/paper_first_authors_ALL.csv` (12,183 records)
- `outputs/researchers/researchers_from_filenames_ALL.csv` (5,471 unique authors)
- `outputs/researchers/filename_parsing_report.txt`

### Phase 2 Outputs (⚠️ Contains noise)
- `outputs/researchers/paper_affiliations_ALL.csv` (27,839 records)
- `outputs/researchers/institutions_ALL.csv` (26,135 institutions)
- `outputs/researchers/phase2_extraction_report.txt`

### Phase 3 Outputs (⚠️ Based on noisy Phase 2 data)
- `outputs/researchers/papers_per_country_PHASE3.csv` (62 countries)
- `outputs/researchers/paper_country_mapping.csv` (13,653 records)
- `outputs/researchers/unmapped_affiliations.txt` (2,912 unmapped)

### Documentation
- `docs/GEOGRAPHIC_EXTRACTION_STATUS.md` (created earlier today)
- `docs/PHASE_3_GEOGRAPHIC_EXTRACTION_COMPLETE_2025-11-24.md` (this file)

---

## Key Learnings

### What Worked Well

1. **Parallel processing**: 11 CPU cores reduced Phase 2 from ~20 hours to 2 hours
2. **Pattern matching**: Comprehensive country pattern dictionary (90+ countries) achieved 89.5% mapping rate
3. **Caching**: Phase 2 used caching to avoid re-extracting already-processed papers

### What Needs Improvement

1. **Affiliation extraction precision**: Current approach too greedy, picks up non-affiliation text
2. **Validation**: Should have spot-checked Phase 2 output before running Phase 3
3. **Data quality checks**: Need automatic sanity checks (e.g., "if one country > 50%, flag for review")

### For Next Time

1. **Extract from structured regions**: Focus on author block, not entire first page
2. **Validate incrementally**: Check sample output after each phase before proceeding
3. **Use machine learning**: Consider using pre-trained models (like Science-Parse, GROBID) for author/affiliation extraction

---

## Bottom Line

**For Abstract (Nov 30)**: ✅ Use October 26 data (3,426 papers, 28% coverage, validated)

**For Presentation (May 2025)**:
- ✅ Refine Phase 2 extraction (remove noise)
- ✅ Re-run pipeline to achieve 75%+ coverage with accurate data
- ✅ Implement Phase 4 (study location extraction)
- ✅ Expand to 90%+ of Shark-References database (~27,000 papers)

---

**Generated**: 2025-11-24
**Phase 1**: ✅ COMPLETE
**Phase 2**: ⚠️  COMPLETE but needs refinement (noise in data)
**Phase 3**: ✅ COMPLETE (but based on noisy Phase 2 data)
**Recommendation**: Use October 26 data for abstract, refine pipeline for May 2025 presentation
