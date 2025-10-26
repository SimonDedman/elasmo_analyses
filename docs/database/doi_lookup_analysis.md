---
editor_options:
  markdown:
    wrap: 72
---

# DOI Lookup Analysis & Recommendations

**Date:** 2025-10-24
**Question:** Should we run DOI lookup for 13,881 papers without DOIs?

---

## Current Status

### Papers Without DOIs: 13,881
**Breakdown by decade:**
- **2020-2029:** 338 papers (2.4%)
- **2010-2019:** 2,952 papers (21.3%)
- **2000-2009:** 4,431 papers (31.9%)
- **1990-1999:** 2,429 papers (17.5%)
- **1980-1989:** 1,554 papers (11.2%)
- **1970-1979:** 1,056 papers (7.6%)
- **Pre-1970:** 1,121 papers (8.1%)

### Papers WITH DOIs Already: 16,642
- These already tried via Sci-Hub
- ~11,000 papers have DOI but no PDF URL

---

## Test Results

### Test 1: Random 10 Papers (2020+)
- **Success rate:** 10% (1/10 DOIs found)
- **Time:** 35 seconds
- **Success per hour:** ~100 DOIs

### Test 2: 50 Recent Papers (2015+)
- **Success rate:** 18% (9/50 DOIs found)
- **Time:** 2 minutes 20 seconds
- **Success per hour:** ~230 DOIs
- **Sources:**
  - CrossRef API: 5 DOIs
  - URL extraction: 4 DOIs

---

## Estimated Full Run Analysis

### Scenario 1: All Papers (13,881)
**Success rate estimates by period:**
- 2020-2029: 15% → ~51 DOIs
- 2010-2019: 18% → ~531 DOIs
- 2000-2009: 10% → ~443 DOIs
- 1990-1999: 5% → ~121 DOIs
- Pre-1990: 1% → ~27 DOIs

**Total expected:** ~1,173 DOIs

**Time required:**
- Average: 2.8 seconds per paper
- Total: 38,866 seconds = **10.8 hours**

**Then Sci-Hub download of new DOIs:**
- Estimated success: 70% of 1,173 = ~821 PDFs
- Time: ~3-5 hours

**Total investment:** ~14-16 hours
**Total gain:** ~821 PDFs

---

### Scenario 2: Recent Papers Only (2010+)
**Target:** 3,290 papers from 2010-2024

**Success rate estimates:**
- 2020-2024: 15% → ~51 DOIs
- 2015-2019: 18% → ~146 DOIs
- 2010-2014: 15% → ~364 DOIs

**Total expected:** ~561 DOIs

**Time required:**
- Total: 9,212 seconds = **2.6 hours**

**Then Sci-Hub download of new DOIs:**
- Estimated success: 70% of 561 = ~393 PDFs
- Time: ~2-3 hours

**Total investment:** ~4.5-5.5 hours
**Total gain:** ~393 PDFs

---

### Scenario 3: High-Value Papers Only (2015+)
**Target:** 1,127 papers from 2015-2024

**Success rate:** 18%
**Total expected:** ~203 DOIs

**Time required:**
- Total: 3,156 seconds = **0.9 hours**

**Then Sci-Hub download of new DOIs:**
- Estimated success: 70% of 203 = ~142 PDFs
- Time: ~1-1.5 hours

**Total investment:** ~2-2.5 hours
**Total gain:** ~142 PDFs

---

## Comparison of Approaches

| Scenario | Papers | DOIs Found | PDFs Gained | Time | Efficiency |
|----------|--------|------------|-------------|------|------------|
| **All papers** | 13,881 | ~1,173 | ~821 | 14-16h | 51 PDFs/hour |
| **2010+** | 3,290 | ~561 | ~393 | 4.5-5.5h | 78 PDFs/hour |
| **2015+** | 1,127 | ~203 | ~142 | 2-2.5h | 62 PDFs/hour |

---

## Recommendation

### ⭐ RECOMMENDED: Scenario 2 (2010+ Papers)

**Rationale:**
1. **Best ROI:** ~78 PDFs per hour
2. **Reasonable time:** 4.5-5.5 hours total (can run overnight)
3. **Focuses on valuable papers:** Recent papers more relevant for panel
4. **Higher success rate:** 2010+ papers more likely to have DOIs

**Gain:** ~393 new PDFs
**New total:** 13,347 + 393 = **13,740 PDFs (45.0% coverage)**

---

### Alternative: Scenario 3 (2015+ Only)

**If time is limited:**
- **Quick win:** Only 2-2.5 hours
- **Still valuable:** Recent papers most important
- **Gain:** ~142 PDFs (44.3% coverage)

---

### Don't Do: Scenario 1 (All Papers)

**Reasons:**
- **Diminishing returns:** Pre-2000 papers rarely have DOIs
- **Time intensive:** 14-16 hours for only ~400 extra PDFs vs Scenario 2
- **Lower priority:** Very old papers less relevant for technique trends

---

## Implementation Plan

### Step 1: Run DOI Hunting (2010+)
```bash
cd "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"

# Run DOI hunting for papers 2010+
./venv/bin/python scripts/hunt_dois.py --min-year 2010

# Expected: ~2.6 hours, find ~561 DOIs
```

### Step 2: Add Found DOIs to Database
```bash
# Merge found DOIs back into main database
# (Script needed - see below)
```

### Step 3: Run Sci-Hub on New DOIs
```bash
# Download PDFs for newly found DOIs
./venv/bin/python scripts/download_via_scihub_tor.py --doi-file outputs/papers_with_found_dois.csv

# Expected: ~2-3 hours, download ~393 PDFs
```

### Total Time: 4.5-5.5 hours (can run overnight)

---

## Scripts Needed

### ✅ Already Have
1. `scripts/prepare_doi_hunting.py` - Extracts papers without DOIs
2. `scripts/hunt_dois.py` - Hunts for DOIs via CrossRef/DataCite
3. `scripts/download_via_scihub_tor.py` - Downloads via Sci-Hub

### 🔄 Need to Create
1. **Merge script:** Add found DOIs back to main CSV
2. **Sci-Hub downloader for specific DOI list:** Modify existing script

---

## Expected Outcomes

### After DOI Hunting + Sci-Hub Download

**New coverage:**
- Current: 13,347 PDFs (43.8%)
- After DOI hunt (2010+): ~13,740 PDFs (45.0%)
- After complete Sci-Hub sweep: ~19,000-20,000 PDFs (62-65%)

**Recommended sequence:**
1. DOI hunt for 2010+ papers → +393 PDFs
2. Complete Sci-Hub sweep of all DOIs → +5,000-7,000 PDFs
3. **Final total:** 19,000-20,000 PDFs (62-65% coverage)

---

## Success Rates by Source

From testing:
- **URL extraction:** 100% confidence (DOIs found in PDF URLs)
- **CrossRef API:** 90% high confidence (≥0.9), 10% medium (0.7-0.9)
- **DataCite API:** Not tested in our runs (rare for these papers)

---

## API Rate Limits

**Current delays:** 1 second between requests
**CrossRef limit:** No official limit, but 1/sec is respectful
**DataCite limit:** No official limit

**Risk of getting blocked:** LOW (using respectful delays + proper User-Agent)

---

## Decision Matrix

| Goal | Action | Time | Gain |
|------|--------|------|------|
| **Quick improvement** | DOI hunt 2015+ only | 2.5h | +142 PDFs |
| **Best efficiency** | DOI hunt 2010+ | 5.5h | +393 PDFs |
| **Maximum coverage** | Full Sci-Hub sweep | 20h | +5,000+ PDFs |
| **Ultimate coverage** | All of above | 26h | +6,000+ PDFs |

---

## Final Recommendation

### OPTION A: Efficient Path (Recommended)
1. ✅ **DOI hunt 2010+** (5.5 hours) → +393 PDFs
2. ✅ **Complete Sci-Hub sweep** (20 hours) → +5,000 PDFs
3. **Final:** 19,000 PDFs (62% coverage)

### OPTION B: Analysis-Ready Path
1. ❌ Skip DOI hunting
2. ✅ **Complete Sci-Hub sweep only** (20 hours) → +5,000 PDFs
3. **Final:** 18,300 PDFs (60% coverage)
4. **Rationale:** 393 PDFs not worth 5.5 hours if you're doing Sci-Hub anyway

### OPTION C: Current is Sufficient
1. ❌ Skip everything
2. **Proceed with:** 13,347 PDFs (43.8% coverage)
3. **Rationale:** Already sufficient for panel analysis

---

## My Recommendation: OPTION B

**Why:**
- The DOI hunting yields only ~393 PDFs for 5.5 hours
- The Sci-Hub sweep yields ~5,000 PDFs for 20 hours
- **Much better ROI to just run Sci-Hub sweep**
- Can run overnight, wake up to 60% coverage

**Skip DOI hunting. Just run complete Sci-Hub sweep.**

---

*DOI hunting is ready to go if you want it, but the numbers suggest Sci-Hub sweep alone is more efficient.*
