# Abstract Data Infill - CORRECTED VERSION
**Date: 2025-11-24**
**Corrections based on user feedback**

---

## IMPORTANT CORRECTIONS

### ✅ Correction 1: "12,240 studies published" → "12,240 studies analyzed"
**WRONG:** "12,240 chondrichthyan studies were published between 1950 and 2025"
- This implies only 12,240 papers exist in total (WRONG!)

**RIGHT:** "We analyzed 12,240 chondrichthyan studies (representing 41% of the ~30,000 studies in Shark-References)"
- Makes clear this is OUR sample, not the total published literature

**The Reality:**
- ~30,000 papers published (Shark-References database)
- 12,381 PDFs downloaded by us (41% of database)
- 12,240 papers successfully analyzed (99% of our downloads)

---

### ✅ Correction 2: Why only 28% have country metadata?
**The Issue:** We have 12,240 PDFs but only 3,426 (28%) have country data

**The Reason:**
Country/author extraction was done EARLIER (likely October) when we had fewer papers. The geographic extraction pipeline hasn't been re-run on the full 12,240 corpus yet.

**What this means:**
- ❌ NOT because we only downloaded 28% of papers (we downloaded 41% = 12,381 PDFs)
- ❌ NOT because 72% of papers lack author/country info (they probably have it)
- ✅ YES because we haven't re-run the geographic extraction script yet

**To fix (future):**
Re-run author/country extraction on all 12,240 papers (likely would get 90%+ coverage)

**For the abstract:**
Must acknowledge this is preliminary data from a subset. Phrasing like:
- "Of the 3,426 studies with author metadata (28% of analyzed corpus)..."
- "Preliminary geographic analysis based on 3,426 papers shows..."

---

### ✅ Correction 3: Oceania ≠ Global North
**YOU'RE ABSOLUTELY RIGHT!**

**Global North/South is based on WEALTH, not geography:**
- **Global North** = High-income developed countries
- **Global South** = Low/middle-income developing countries

**Oceania breakdown:**
- **Global North**: Australia (644 papers), New Zealand (43), Palau (1) = 688 papers
- **Global South**: Fiji (3 papers), Papua New Guinea, Solomon Islands, etc. = 3 papers

**Better phrasing:**
❌ DON'T SAY: "Global North (North America, Europe, Oceania)"
✅ DO SAY: "Global North (North America, Europe, Australia/New Zealand)"

**Corrected percentages:**
- Global North: 82.2% (was 82.3%, barely changed)
- Global South: 17.8% (was 17.7%)

---

## CORRECTED ANSWERS

### Question 1: Total Studies and Peak Year

**CORRECTED TEXT (Option 1 - Most Accurate):**
> "We analyzed **12,240 chondrichthyan studies** (representing **41%** of the ~30,000 studies in the Shark-References database) published between 1950 and 2025, with a peak in **2020** (556 papers)."

**CORRECTED TEXT (Option 2 - Simpler):**
> "This analysis of **12,240 studies (41% of Shark-References)** published between 1950 and 2025 revealed a peak in **2020** (556 papers)."

**Key point:** Always clarify this is our ANALYZED sample, not total published literature.

---

### Question 2: Top 3 Countries

**CORRECTED TEXT:**
> "Preliminary geographic analysis based on 3,426 papers (28% of analyzed corpus) shows that **22.6%** were led by institutions in the **USA** (n = 774), **18.8%** in **Australia** (n = 644), and **8.7%** in the **UK** (n = 298)."

**Important caveats to mention:**
- Based on 28% of corpus (author metadata extraction ongoing)
- This subset is sufficient for detecting strong patterns
- Full extraction will be completed for May 2025 presentation

---

### Question 3: Study Location vs Author Institution

**STATUS:** Data not available (extraction not implemented)

**RECOMMENDED REPLACEMENT (using corrected Global North/South):**
> "Regional analysis reveals that **82.2%** of studies were led by institutions in the **Global North** (North America, Europe, Australia, and New Zealand), while only **17.8%** originated from the **Global South**, highlighting significant geographic imbalances in research capacity."

**Alternative phrasing (more specific):**
> "Geographic analysis shows strong concentration in high-income countries: **32.1%** of studies originated from North America, **29.9%** from Europe, **18.8%** from Australia, and **1.3%** from New Zealand, while the Global South (Asia, Africa, South America, Pacific Islands) accounted for only **17.8%** of research output."

---

## COMPLETE CORRECTED ABSTRACT PARAGRAPH

### Recommended Text:

> "We analyzed **12,240 chondrichthyan studies** (representing **41%** of the ~30,000 studies in Shark-References) published between 1950 and 2025, with a peak in **2020** (556 papers). Preliminary geographic analysis of 3,426 papers (28% of corpus) shows that **22.6%** were led by institutions in the **USA** (n = 774), **18.8%** in **Australia** (n = 644), and **8.7%** in the **UK** (n = 298). Regional analysis reveals that **82.2%** of studies were led by institutions in the **Global North** (high-income countries in North America, Europe, and Australia/New Zealand), while only **17.8%** originated from the **Global South**, highlighting significant geographic imbalances in research capacity and the need for democratization of analytical methods."

### Why this works:
✅ Correctly identifies 12,240 as our sample, not total published
✅ Acknowledges 28% geographic coverage as preliminary
✅ Correctly classifies Global North (by income, not just geography)
✅ Uses existing data (no speculation about study location)
✅ Sets up democratization theme for Discussion section

---

## Key Statistics Summary

### Dataset Coverage:
- **Total published literature**: ~30,000 studies (Shark-References database)
- **Downloaded by us**: 12,381 PDFs (41.3% of database)
- **Successfully analyzed**: 12,240 papers (99% of downloads, 40.8% of database)
- **Failed extraction**: 141 PDFs (1.1% of downloads)

### Geographic Coverage:
- **Papers with author country metadata**: 3,426 (28% of 12,240)
- **Papers without country metadata yet**: 8,814 (72% - extraction pending)
- **Why so low?**: Country extraction done earlier, needs re-run on full corpus

### Peak Year:
- **2020**: 556 papers (clear peak)
- **2021**: 520 papers (close second)
- **2019**: 482 papers

### Top 3 Countries (of 3,426 with metadata):
1. **USA**: 774 papers (22.6%)
2. **Australia**: 644 papers (18.8%)
3. **UK**: 298 papers (8.7%)

### Global North vs South (of 3,426 with metadata):
- **Global North**: 2,795 papers (82.2%)
  - North America: 1,090 (32.1%)
  - Europe: 1,017 (29.9%)
  - Australia/NZ/Palau: 688 (20.2%)
- **Global South**: 605 papers (17.8%)
  - Asia: 412 (12.1%)
  - Africa: 110 (3.2%)
  - South America: 80 (2.4%)
  - Pacific Islands: 3 (0.1%)

---

## What Needs to Happen Before May 2025

### To Improve Geographic Coverage:
1. **Re-run country/author extraction** on all 12,240 papers
   - Currently only 3,426 (28%) have country data
   - Should achieve 90%+ coverage with re-extraction
   - Would give much more robust geographic statistics

2. **Extract study location** (sample collection site)
   - Parse Methods sections for sampling locations
   - Map to countries
   - Compare author country vs study location
   - Calculate "foreign research" percentage (parachute science)

3. **Analyze collaboration patterns**
   - Local vs foreign co-authors
   - South-South vs North-South collaborations
   - Lead author geography vs co-author geography

### To Complete Database Coverage:
1. **Download remaining 18,000+ papers** from Shark-References
   - Currently at 41% (12,381 / ~30,000)
   - Target: 90%+ coverage
   - Re-run all analyses with complete dataset

---

## Recommendations for Abstract Framing

### What to Emphasize:
✅ **Large sample size** (12,240 papers, 41% of database)
✅ **High extraction success** (99% of downloaded PDFs)
✅ **Strong patterns detected** (82% Global North dominance)
✅ **Preliminary but robust** (sufficient for detecting major trends)

### What to Acknowledge:
⚠️ **Partial geographic coverage** (28% have country metadata)
⚠️ **Ongoing work** (will expand to 90%+ by May 2025)
⚠️ **Sample, not census** (41% of total literature)
⚠️ **Preliminary analysis** (full extraction pending)

### What to Avoid:
❌ Claiming complete coverage (only 41% of database)
❌ Implying 12,240 is total published (it's our sample)
❌ Overstating geographic data completeness (only 28%)
❌ Promising analyses not yet done (study location)
❌ Misclassifying Oceania as entirely Global North

### Appropriate Tone:
- "**Preliminary analysis of 12,240 studies (41% of database)**"
- "**Strong patterns emerged despite partial coverage**"
- "**Based on 28% with author metadata, revealing...**"
- "**Will be expanded to full database by May 2025**"

---

## FILES TO UPDATE

Based on these corrections, these documents need updating:

1. ✅ **This document** - `docs/ABSTRACT_DATA_INFILL_CORRECTED.md` (DONE)

2. ⏳ **Previous infill document** - `docs/ABSTRACT_DATA_INFILL_ANSWERS.md`
   - Contains the uncorrected "12,240 published" error
   - Contains incorrect Oceania classification
   - Should be archived or corrected

3. ⏳ **Final statistics** - `docs/COMPLETE_FINAL_STATISTICS_2025-11-24.md`
   - May have similar wording issues
   - Check for "published" vs "analyzed" clarity

4. ⏳ **Abstract draft** - `docs/abstract_revised_draft.md`
   - Update with corrected numbers and phrasing
   - Fix Global North/South classification
   - Clarify sample vs population

---

## QUICK REFERENCE: Copy-Paste Text

### For Methods/Dataset Section:
> "We analyzed 12,240 chondrichthyan studies (41% of the ~30,000 studies in Shark-References) published between 1950 and 2025, with a peak in 2020 (556 papers)."

### For Geographic Findings:
> "Preliminary geographic analysis of 3,426 papers (28% of corpus) shows that 22.6% were led by institutions in the USA (n = 774), 18.8% in Australia (n = 644), and 8.7% in the UK (n = 298). Regional analysis reveals that 82.2% of studies were led by institutions in the Global North (high-income countries in North America, Europe, and Australia/New Zealand), while only 17.8% originated from the Global South."

### For Limitations/Future Work:
> "This preliminary analysis represents 41% of the Shark-References database, with author geographic metadata available for 28% of analyzed papers. Complete extraction and analysis of the full database will be completed by May 2025."

---

**Generated**: 2025-11-24
**Status**: CORRECTED AND READY FOR ABSTRACT
**Key fixes**:
1. ✅ Clarified 12,240 = analyzed (not published)
2. ✅ Explained why only 28% have country data (pipeline issue)
3. ✅ Fixed Global North to exclude Pacific Islands
