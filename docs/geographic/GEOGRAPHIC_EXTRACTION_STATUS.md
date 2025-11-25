# Geographic Extraction Status - November 24, 2025

## Current Situation

**Question**: Why do only 28% of papers have country metadata?

**Answer**: The geographic extraction pipeline hasn't been re-run on the full 12,240-paper corpus yet. It was last run on October 26th when we had fewer papers analyzed.

---

## What We Have Now

### ✅ Complete (Ready for Abstract)

1. **Technique/Discipline Analysis** - UPDATED TODAY
   - All 12,240 papers analyzed for techniques
   - 151 unique techniques found
   - 9,537 papers with techniques (77.9%)
   - All discipline statistics current
   - **Files regenerated**: `outputs/analysis/*.csv`

2. **Author Names from Filenames** - COMPLETED TODAY
   - Phase 1 extraction complete
   - 12,183 papers processed (99.5% success)
   - 5,471 unique first authors identified
   - **Files created**:
     - `outputs/researchers/researchers_from_filenames_ALL.csv`
     - `outputs/researchers/paper_first_authors_ALL.csv`

### ⚠️ Partial (From October 26th)

3. **Geographic Data** - OLD (28% coverage)
   - **3,426 papers** have country metadata (from October extraction)
   - **8,814 papers** don't have country metadata yet (72%)
   - This is the data currently used for abstract statistics:
     - USA: 774 papers (22.6%)
     - Australia: 644 papers (18.8%)
     - UK: 298 papers (8.7%)
     - Global North: 82.2%, Global South: 17.8%
   - **Files** (not updated):
     - `outputs/analysis/papers_per_country.csv`
     - `outputs/analysis/papers_by_region.csv`
     - `outputs/analysis/*collaboration*.csv`

---

## What's Needed to Get 90%+ Country Coverage

### Pipeline Overview

```
Phase 1: Extract authors from filenames ✅ DONE (today)
    ↓
Phase 2: Extract affiliations from PDFs ⏳ IN PROGRESS (2-3 hours)
    ↓
Phase 3: Map institutions → countries 🔜 PENDING
    ↓
Phase 4: Run R analysis scripts 🔜 PENDING
    ↓
Result: papers_per_country.csv with 90%+ coverage
```

### Phase 2: Extract Affiliations from PDFs

**Status**: Currently running (started 14:14, ~10 minutes ago)

**What it does**:
- Opens first page of each PDF
- Extracts author names and institutional affiliations
- Parses "Department of X, University of Y, Country Z" patterns
- Saves to `outputs/researchers/paper_authors_full.csv`

**Time estimate**:
- Processing ~12,000 PDFs
- Using pdfplumber (Python library)
- 11 CPU cores in parallel
- **Estimated time: 2-3 hours** (some PDFs are slow to open)

**Current progress**:
```bash
# Check progress:
tail -20 logs/phase2_extraction.log
```

**Known issues**:
- Some PDFs have malformed color specifications (warnings in log)
- These are non-fatal and can be ignored
- Success rate likely 85-95% (some PDFs don't have clear affiliation formatting)

### Phase 3: Map Institutions to Countries

**Status**: Not yet implemented

**What's needed**:
- Read institutional affiliations from Phase 2 output
- Extract country names from affiliation strings
- Use geocoding/country-name-matching library
- Possible approaches:
  1. **Simple regex matching**: Look for country names in affiliation text
  2. **geocoder library**: Use Python `geopy` or `pycountry`
  3. **Manual mapping table**: Create institution → country lookup table
  4. **Google Maps API**: Geocode full addresses (requires API key)

**Recommended approach**:
Simple regex + manual fallback for most common institutions

**Estimated time**: 30-60 minutes to write + 10 minutes to run

### Phase 4: Run R Analysis Scripts

**Status**: Ready to run (scripts exist)

**Scripts to run**:
```R
# Generate country statistics
Rscript scripts/analyze_collaboration_networks.R
Rscript scripts/visualize_geography.R
```

**Output files updated**:
- `outputs/analysis/papers_per_country.csv`
- `outputs/analysis/papers_by_region.csv`
- `outputs/analysis/country_collaboration_network.csv`
- `outputs/analysis/country_collaboration_metrics.csv`

**Estimated time**: 5-10 minutes

---

## Timeline Options

### Option 1: Complete Before Abstract Submission (Nov 30)

**Pros**:
- Get 90%+ country coverage for abstract
- More robust geographic statistics
- Better for reviewer confidence

**Cons**:
- Phase 2 takes 2-3 hours (must babysit)
- Phase 3 needs to be written (30-60 minutes)
- Risk of bugs/delays close to deadline

**Timeline**:
- Today (Nov 24): Phase 2 completes (~17:00)
- Nov 25: Write Phase 3 script, run pipeline
- Nov 26: Regenerate abstract with updated numbers
- Nov 27-30: Buffer for revisions

### Option 2: Use Current Data for Abstract, Update for Presentation (May 2025)

**Pros**:
- Abstract uses proven, stable data (3,426 papers, 28%)
- No risk of last-minute bugs
- Can still make strong equity arguments (82% Global North)
- More time to validate Phase 2/3 pipeline

**Cons**:
- Lower coverage percentage in abstract (28% vs 90%)
- Must frame as "preliminary" findings

**Timeline**:
- Today (Nov 24): Document current status (this file)
- Nov 25-28: Finalize abstract with existing data
- Nov 30: Submit abstract
- Dec-Apr: Complete geographic pipeline at leisure
- May 2025: Present with full 90%+ coverage

---

## Recommendation

**Use Option 2: Current data for abstract, full pipeline for May presentation**

### Rationale:

1. **28% coverage is sufficient for preliminary findings**
   - N=3,426 is statistically robust
   - Clear pattern (82% Global North)
   - Can acknowledge as preliminary

2. **Risk management**
   - 6 days until deadline (Nov 30)
   - Phase 2 running now (finish today)
   - Phase 3 not yet written (unknown unknowns)
   - Better to use stable, tested data

3. **Scientific integrity**
   - Transparent about coverage ("preliminary analysis of 3,426 papers...")
   - Honest about ongoing work ("full extraction by May 2025")
   - Shows rigorous methodology (not hiding limitations)

4. **Time allocation**
   - Focus remaining days on Methods/Discussion expansion
   - Find species richness data
   - Final review with GT

### Abstract Phrasing:

**Current (accurate) phrasing**:
> "Preliminary geographic analysis of 3,426 papers (28% of analyzed corpus) shows that 22.6% were led by institutions in the USA (n = 774), 18.8% in Australia (n = 644), and 8.7% in the UK (n = 298). Regional analysis reveals that 82.2% of studies were led by institutions in the Global North (high-income countries in North America, Europe, and Australia/New Zealand), while only 17.8% originated from the Global South."

**Why this works**:
- ✅ Transparent about coverage
- ✅ Sample size sufficient for strong conclusions
- ✅ Sets up May 2025 presentation ("expanded analysis will...")
- ✅ Uses tested, validated data
- ✅ No risk of last-minute pipeline failures

---

## If You Choose Option 1 (Complete Now)

### Steps to Complete:

1. **Wait for Phase 2** (check logs periodically)
   ```bash
   tail -f logs/phase2_extraction.log
   ```
   - Will take 2-3 hours
   - Look for "PHASE 2 COMPLETE" message

2. **Write Phase 3 script** (institution → country mapping)
   - Create `scripts/map_institutions_to_countries.py`
   - Read `outputs/researchers/paper_authors_full.csv`
   - Extract country from affiliation strings
   - Update `researchers` table in database
   - Example code provided below

3. **Run R analysis scripts**
   ```bash
   Rscript scripts/analyze_collaboration_networks.R
   Rscript scripts/visualize_geography.R
   ```

4. **Verify new country coverage**
   ```bash
   wc -l outputs/analysis/papers_per_country.csv
   # Should show ~11,000+ papers (up from 3,426)
   ```

5. **Update abstract** with new percentages

### Phase 3 Script Template:

```python
#!/usr/bin/env python3
"""
PHASE 3: Map Institutions to Countries
"""
import pandas as pd
import sqlite3
import re
from pathlib import Path

# Load affiliations from Phase 2
affiliations = pd.read_csv('outputs/researchers/paper_authors_full.csv')

# Simple country extraction (regex-based)
COUNTRIES = {
    'USA': ['USA', 'United States', 'U.S.A.', 'California', 'Florida', 'Maryland'],
    'Australia': ['Australia', 'Queensland', 'New South Wales', 'Victoria'],
    'UK': ['UK', 'United Kingdom', 'England', 'Scotland', 'Wales'],
    # ... add more countries
}

def extract_country(affiliation_text):
    """Extract country from affiliation string."""
    if not affiliation_text or pd.isna(affiliation_text):
        return None

    text_lower = affiliation_text.lower()
    for country, keywords in COUNTRIES.items():
        if any(kw.lower() in text_lower for kw in keywords):
            return country

    return None

# Apply country extraction
affiliations['country'] = affiliations['affiliation'].apply(extract_country)

# Update database
conn = sqlite3.connect('database/technique_taxonomy.db')
cursor = conn.cursor()

for _, row in affiliations.iterrows():
    if row['country']:
        cursor.execute(
            "UPDATE researchers SET country = ? WHERE researcher_id = ?",
            (row['country'], row['researcher_id'])
        )

conn.commit()
conn.close()

print("✓ Phase 3 complete!")
```

---

## Current File Locations

### Ready for Abstract (Updated Today):
- `outputs/analysis/discipline_trends_by_year.csv` ✅
- `outputs/analysis/technique_trends_by_year.csv` ✅
- `outputs/analysis/top_techniques.csv` ✅
- `outputs/analysis/discipline_summary.csv` ✅
- `outputs/analysis/summary_statistics.csv` ✅

### Geographic Data (From October 26):
- `outputs/analysis/papers_per_country.csv` ⚠️ (OLD, 28%)
- `outputs/analysis/papers_by_region.csv` ⚠️ (OLD)
- `outputs/analysis/*collaboration*.csv` ⚠️ (OLD)

### Logs:
- `logs/phase2_extraction.log` (currently running)

---

## Summary

**For abstract submission (Nov 30)**:
- ✅ Use current geographic data (3,426 papers, 28% coverage)
- ✅ Phrase as "preliminary" with transparent limitations
- ✅ Focus on strong findings (82% Global North, clear inequity)

**For presentation (May 2025)**:
- 🔜 Complete Phase 2/3/4 pipeline at leisure
- 🔜 Achieve 90%+ country coverage
- 🔜 Present with full, validated dataset

**Bottom line**: We have everything needed for a strong abstract. Geographic expansion can wait until after submission.

---

**Generated**: 2025-11-24 14:16
**Phase 2 status**: Running (started 14:14, ~10 min elapsed)
**Recommendation**: Use existing 28% data for abstract, complete pipeline for May 2025
