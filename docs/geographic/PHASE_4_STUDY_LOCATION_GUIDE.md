# Phase 4: Study Location Extraction - Guide

**Date**: 2025-11-24
**Status**: 🔧 **Script Ready - Not Yet Executed**
**Purpose**: Extract WHERE research was conducted (study location) vs WHERE authors are based (author institution)

---

## Overview

Phase 4 completes the geographic analysis pipeline by extracting **study locations** from Methods/Materials sections of papers. This enables the critical "parachute research" analysis comparing author countries vs study countries.

### What is "Parachute Research"?

**Parachute research** (also called "helicopter research" or "safari science") occurs when researchers from high-income countries conduct fieldwork in low-income countries without meaningful local collaboration or capacity building.

**Definition**: Papers where **author institution country ≠ study location country**

**Example**:
- **Author affiliation**: University of California, USA
- **Study location**: Great Barrier Reef, Australia
- **Classification**: Parachute research (USA author studying Australian ecosystem)

---

## Script: `extract_study_locations_phase4.py`

### What It Does

1. **Extracts Methods sections** from PDFs (first 10 pages)
2. **Identifies study locations** using:
   - Country name patterns (60+ countries)
   - Ocean basin keywords (7 major basins)
   - Latitude/longitude coordinates
   - Location descriptions
3. **Compares** author country vs study country
4. **Flags parachute research** (author country ≠ study country)
5. **Updates database** with study location data

### Input Data

**Source**: Database (`paper_geography` table)
- Papers with author country data: 6,183
- Papers to process: 6,183

### Output Fields

Updates `paper_geography` table with:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `study_country` | TEXT | Country where fieldwork conducted | "Australia" |
| `study_ocean_basin` | TEXT | Ocean basin of study site | "South Pacific" |
| `study_latitude` | REAL | Latitude coordinate | -23.45 |
| `study_longitude` | REAL | Longitude coordinate | 151.92 |
| `study_location_text` | TEXT | Extracted location description | "Sampling conducted in Moreton Bay, Queensland..." |
| `has_study_location` | BOOLEAN | 1 if study location extracted | 1 |
| `is_parachute_research` | BOOLEAN | 1 if author country ≠ study country | 1 |

---

## Geographic Detection Patterns

### Country Patterns (60+ countries)

Script includes comprehensive patterns for major shark research countries:

**Examples**:
- **USA**: 'united states', 'california', 'florida', 'gulf of mexico', 'hawaii'
- **Australia**: 'australia', 'queensland', 'great barrier reef', 'tasmania'
- **Mexico**: 'mexico', 'baja', 'gulf of california', 'sea of cortez'
- **Ecuador**: 'ecuador', 'galapagos'
- **South Africa**: 'south africa'
- **UK**: 'united kingdom', 'england', 'scotland', 'north sea'

### Ocean Basins (7 major basins)

- **North Atlantic**: 'north atlantic', 'gulf of mexico', 'caribbean', 'mediterranean'
- **South Atlantic**: 'south atlantic'
- **North Pacific**: 'north pacific', 'bering sea', 'california current'
- **South Pacific**: 'south pacific', 'coral sea', 'tasman sea'
- **Indian Ocean**: 'indian ocean', 'arabian sea', 'bay of bengal', 'red sea'
- **Arctic**: 'arctic ocean', 'beaufort sea'
- **Southern Ocean**: 'southern ocean', 'antarctic'

### Coordinate Extraction

**Pattern**: `(\d+[\.,]\d+)[°º]?\s*[NS]?\s*[,;]?\s*(\d+[\.,]\d+)[°º]?\s*[EW]?`

**Examples detected**:
- "23.5°N, 151.9°E"
- "23.5N 151.9E"
- "23.5, 151.9"
- "23,5°N; 151,9°E" (European format)

**Validation**: Latitude -90 to 90, Longitude -180 to 180

---

## Execution

### Command

```bash
./venv/bin/python3 scripts/extract_study_locations_phase4.py
```

### Expected Runtime

- **Papers to process**: 6,183
- **Workers**: 11 CPU cores (parallel processing)
- **Estimated time**: ~2-3 hours (depends on PDF parsing speed)
- **Progress reporting**: Every 500 papers

### Expected Output

```
================================================================================
PHASE 4: EXTRACT STUDY LOCATIONS FROM METHODS SECTIONS
================================================================================

Goal: Identify WHERE research was conducted vs WHERE authors are based
Enables: 'Parachute research' analysis (author country ≠ study country)

Papers to process: 6,183

Workers: 11

  Progress: 500/6,183 (success: 450, methods_not_found: 30, pdf_not_found: 20)
  Progress: 1,000/6,183 (success: 920, methods_not_found: 55, pdf_not_found: 25)
  ...

✓ Extraction complete!
  Successfully extracted: 5,500 (89.0%)
  Methods not found: 600
  PDFs not found: 83

=== Study Location Data Extracted ===
  Papers with study country: 4,200 (76.4% of successful)
  Papers with ocean basin: 3,800 (69.1%)
  Papers with coordinates: 1,500 (27.3%)
  Parachute research detected: 1,200 (21.8%)

=== Updating database ===
  Updated 5,500 records in paper_geography table
  Parachute research flagged: 1,200

=== Parachute Research Examples ===
  Smith.etal.2015.Shark movements in tropical waters.pdf
    Author country: USA
    Study country:  Ecuador
    Location: Sampling conducted in the Galapagos Marine Reserve...

  Jones.etal.2018.White shark behavior.pdf
    Author country: UK
    Study country:  South Africa
    Location: Field work was carried out in Gansbaai, South Africa...

================================================================================
PHASE 4 COMPLETE
================================================================================

Study location data extracted for 5,500 papers
Parachute research identified: 1,200 papers

Database updated: paper_geography table

Next: Analyze author country vs study country patterns
```

---

## Expected Results (Estimates)

Based on manual sampling of shark research papers:

| Metric | Expected Count | Expected % |
|--------|----------------|------------|
| **Papers processed** | 6,183 | 100% |
| **Methods sections found** | ~5,500 | ~89% |
| **Study country extracted** | ~4,200 | ~68% |
| **Ocean basin extracted** | ~3,800 | ~61% |
| **Coordinates extracted** | ~1,500 | ~24% |
| **Parachute research cases** | ~1,200 | ~19-22% |

### Why Not 100% Coverage?

**Methods sections not found** (~11%):
- Review papers (no fieldwork)
- Theoretical/modeling studies
- Lab-only studies
- Poor PDF quality/scanned images

**Study location not extracted** (~20-30% of papers with Methods):
- Vague location descriptions ("coastal waters")
- Museum specimens (no field site mentioned)
- Multi-country studies (ambiguous)
- Non-standard terminology

---

## Parachute Research Patterns (Predicted)

### Expected Patterns

**High parachute research rates expected**:
1. **USA/UK → Latin America** (Galapagos, Baja California, Caribbean)
2. **USA/Australia → Pacific Islands** (Palau, Fiji, French Polynesia)
3. **Australia/USA → Southeast Asia** (Indonesia, Malaysia, Philippines)
4. **Global North → African coast** (Madagascar, Mozambique, Tanzania)

**Low parachute research rates expected**:
1. **Domestic studies** (USA studying USA, Australia studying Australia)
2. **Regional collaboration** (UK/France/Spain Mediterranean studies)
3. **South-South collaboration** (Brazil/Argentina South Atlantic)

---

## Analysis Queries (After Phase 4)

### 1. Parachute Research by Author Country

```sql
SELECT first_author_country, COUNT(*) as parachute_papers
FROM paper_geography
WHERE is_parachute_research = 1
GROUP BY first_author_country
ORDER BY parachute_papers DESC;
```

**Expected top countries** (by number of parachute papers):
1. USA (~500)
2. Australia (~200)
3. UK (~150)
4. Canada (~80)
5. Germany (~60)

### 2. Most "Studied" Countries (by Foreign Researchers)

```sql
SELECT study_country, COUNT(*) as foreign_studies
FROM paper_geography
WHERE is_parachute_research = 1
GROUP BY study_country
ORDER BY foreign_studies DESC;
```

**Expected top "destination" countries**:
1. Mexico (Guadalupe, Baja) - ~250 papers
2. Ecuador (Galapagos) - ~180 papers
3. South Africa (cage diving sites) - ~150 papers
4. Palau - ~120 papers
5. Bahamas - ~100 papers

### 3. Parachute Research Rate by Region

```sql
SELECT p.first_author_region,
       COUNT(*) as total_papers,
       SUM(CASE WHEN is_parachute_research = 1 THEN 1 ELSE 0 END) as parachute_count,
       ROUND(SUM(CASE WHEN is_parachute_research = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as parachute_pct
FROM paper_geography p
WHERE has_study_location = 1
GROUP BY p.first_author_region;
```

**Expected results**:
- **Global North**: 22-25% parachute research rate
- **Global South**: 5-8% parachute research rate

### 4. North-South Parachute Research (Most Critical Pattern)

```sql
SELECT p.first_author_country, p.study_country, COUNT(*) as papers
FROM paper_geography p
WHERE p.is_parachute_research = 1
  AND p.first_author_region = 'Global North'
  AND p.study_country IN (
      SELECT DISTINCT first_author_country FROM paper_geography WHERE first_author_region = 'Global South'
  )
GROUP BY p.first_author_country, p.study_country
HAVING COUNT(*) >= 10
ORDER BY papers DESC;
```

**Expected patterns**:
- USA → Mexico: ~200 papers
- USA → Ecuador: ~80 papers
- Australia → Indonesia: ~60 papers
- USA → South Africa: ~50 papers
- UK → South Africa: ~40 papers

---

## Limitations and Considerations

### 1. Multi-Country Studies

**Issue**: Some studies span multiple countries
**Solution**: Script extracts FIRST country mentioned in Methods
**Impact**: May undercount collaborative international studies

### 2. Museum Specimens

**Issue**: Specimens may be from different country than study institution
**Solution**: Script looks for explicit "sampling" or "field work" language
**Impact**: May miss some historical specimen studies

### 3. Collaborative Research

**Issue**: Not all foreign-led studies are "parachute" - some have local co-authors
**Solution**: Phase 4 only detects geographic mismatch, not collaboration depth
**Future work**: Analyze co-author affiliations to identify true collaborative vs parachute

### 4. Ocean-Only Studies

**Issue**: Pelagic studies (open ocean) may not have a study "country"
**Solution**: Ocean basin field captures these (e.g., "North Pacific")
**Impact**: Parachute research metric only valid for coastal/territorial studies

---

## Validation Plan

### Before Full Execution

**Test on sample** (100 papers):
```bash
# Modify script to limit to 100 papers for testing
./venv/bin/python3 scripts/extract_study_locations_phase4.py --test --limit 100
```

**Manual validation**:
1. Select 20 random papers flagged as parachute research
2. Read Methods sections manually
3. Verify country extraction accuracy
4. Check for false positives (e.g., "Australia" in author name vs location)

**Acceptance criteria**:
- >85% accuracy on country extraction
- >90% accuracy on parachute research flagging
- <5% false positive rate

### After Full Execution

**Sanity checks**:
```sql
-- Should be >0 (we know USA has some domestic studies)
SELECT COUNT(*) FROM paper_geography WHERE first_author_country = 'USA' AND study_country = 'USA';

-- Should be >0 (we know some USA researchers study Mexico)
SELECT COUNT(*) FROM paper_geography WHERE first_author_country = 'USA' AND study_country = 'Mexico';

-- Should be reasonable (<50% overall)
SELECT ROUND(AVG(CASE WHEN is_parachute_research = 1 THEN 100.0 ELSE 0.0 END), 1) as parachute_pct
FROM paper_geography WHERE has_study_location = 1;
```

---

## Next Steps After Phase 4

### For Abstract (November 30 Deadline)

**Recommended approach**: Run Phase 4 AFTER abstract submission

**Reason**: Phase 4 is not essential for November 30 abstract. Current data (author countries, Global North/South) is sufficient.

### For Presentation (May 2025)

**Critical analyses enabled by Phase 4**:

1. **Parachute research quantification**
   - % of Global North papers studying Global South locations
   - Top source-destination country pairs
   - Trends over time (has it decreased?)

2. **Regional equity analysis**
   - Which ecosystems are studied by local vs foreign researchers?
   - Are hotspots (Galapagos, GBR, etc.) dominated by foreign research?

3. **Collaboration patterns**
   - Phase 4 + author affiliation co-analysis
   - Identify papers with local co-authors vs truly parachute

4. **Conservation implications**
   - Are Global South countries building local shark research capacity?
   - Which countries have "research sovereignty" (mostly local-led)?

---

## Files

### Scripts
- **`scripts/extract_study_locations_phase4.py`**: Main extraction script (READY)

### Documentation
- **`docs/PHASE_4_STUDY_LOCATION_GUIDE.md`**: This file (COMPLETE)

### Database Schema
- **`database/technique_taxonomy.db`**: Ready with study location fields in `paper_geography` table

---

## Estimated Timeline

| Task | Time | Status |
|------|------|--------|
| Script development | 1 hour | ✅ COMPLETE |
| Documentation | 30 min | ✅ COMPLETE |
| Test run (100 papers) | 5 min | ⏸️ PENDING |
| Manual validation | 1 hour | ⏸️ PENDING |
| Full execution (6,183 papers) | 2-3 hours | ⏸️ PENDING |
| Database update | 5 min | ⏸️ PENDING |
| Analysis queries | 1 hour | ⏸️ PENDING |
| **TOTAL** | **~5-6 hours** | ⏸️ READY TO EXECUTE |

---

## Decision Point

**Question**: Run Phase 4 now (before Nov 30 abstract) or later (for May 2025 presentation)?

### Option A: Run Now (Before Abstract)
**Pros**:
- Complete dataset for abstract
- Parachute research stats available
- More impressive abstract

**Cons**:
- 5-6 hour time investment
- Risk of finding issues that delay abstract
- Abstract already strong without it

### Option B: Run Later (After Abstract, Before Presentation)
**Pros**:
- Focus on abstract deadline first
- More time for validation
- Can refine script based on initial results

**Cons**:
- Parachute research not in abstract
- Two-phase data presentation (abstract vs presentation)

---

**Recommendation**: **Option B - Run after abstract submission**

**Rationale**:
1. Current data (6,183 papers with author countries) is already strong
2. Phase 4 adds complexity that could introduce errors before deadline
3. Parachute research analysis is better suited for full presentation (May 2025)
4. Allows time to validate and refine before public presentation

---

**Generated**: 2025-11-24 18:15
**Script Status**: ✅ Ready to execute
**Documentation Status**: ✅ Complete
**Recommended Execution**: After November 30 abstract submission
