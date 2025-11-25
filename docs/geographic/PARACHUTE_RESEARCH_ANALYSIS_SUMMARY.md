# Parachute Research Analysis - Summary

**Last Updated**: 2025-11-24 16:53
**Status**: 🔄 **Phase 4 FIXED Running** (v2 - corrected word boundary matching)

---

## Overview

**Parachute research** (also called "helicopter research" or "safari science") occurs when researchers from one country conduct fieldwork in a different country, potentially without meaningful local collaboration.

**Definition**: Papers where **author institution country ≠ study location country**

**Example**:
- Author affiliation: University of California, USA
- Study location: Galapagos Islands, Ecuador
- Classification: Parachute research (USA → Ecuador)

---

## Phase 4 Execution History

### Run 1: Original Phase 4 (Contains False Positives)
**Executed**: 2025-11-24 ~14:00
**Status**: ✅ Complete (but contains false positives)

**Results**:
- Papers processed: 5,457 (88.3% of 6,183)
- Study country extracted: 4,496 (82.4%)
- Parachute research cases: 2,609 (47.8%)
- **CRITICAL BUG**: Substring matching caused false positives

**False Positive Example**:
- Cuba: 120 papers (ALL false positives from "in**CUBA**ted")
- Pattern: `if 'cuba' in text_lower` matched "incubated with occasional shaking"

**Other Suspected False Positives**:
- "iran" matching "Med**IRAN**ean" (likely many false positives)
- "india" matching "f**IN**dings", "b**IN**ding"
- "china" matching "ma**CHINA**ry"

### Run 2: Phase 4 FIXED v1 (Path Bug)
**Executed**: 2025-11-24 ~16:30
**Status**: ❌ Failed (0 PDFs found due to path bug)

**Bug**: Double-escaped backslashes in regex
```python
# WRONG:
year_match = re.search(r'\\.(\d{4})\\.', paper_id)

# CORRECT:
year_match = re.search(r'\.(\d{4})\.', paper_id)
```

**Result**: Script couldn't find any PDFs (0 success, 6,183 pdf_not_found)

### Run 3: Phase 4 FIXED v2 (Current Run)
**Executed**: 2025-11-24 16:51
**Status**: 🔄 **Running** (expected completion ~18:51-19:51)

**Fixes Applied**:
1. ✅ Word boundary matching using `\b` regex anchors
2. ✅ Context validation (country must appear near study keywords)
3. ✅ Longest pattern first sorting
4. ✅ Path finding bug corrected

**Script**: `scripts/extract_study_locations_phase4_FIXED.py`
**Log**: `logs/phase4_study_locations_FIXED_v2.log`
**Workers**: 11 CPU cores (parallel processing)

---

## Technical Fixes Implemented

### 1. Word Boundary Matching

**Before** (substring matching):
```python
def extract_country(text: str) -> Optional[str]:
    text_lower = text.lower()
    for country, patterns in COUNTRIES.items():
        for pattern in patterns:
            if pattern in text_lower:  # BUG: substring matching!
                return country
```

**After** (word boundary matching):
```python
def extract_country_with_context(text: str) -> Optional[str]:
    text_lower = text.lower()

    # Sort patterns by length (longest first)
    all_patterns = []
    for country, patterns in COUNTRIES.items():
        for pattern in patterns:
            all_patterns.append((country, pattern))
    all_patterns.sort(key=lambda x: len(x[1]), reverse=True)

    # Check each pattern with WORD BOUNDARIES
    for country, pattern in all_patterns:
        pattern_regex = re.compile(r'\b' + re.escape(pattern) + r'\b', re.IGNORECASE)
        matches = list(pattern_regex.finditer(text_lower))

        if matches:
            # Context validation (see below)...
```

### 2. Context Validation

**Requirement**: Country name must appear within 100 characters of study location keywords

**Study location keywords**:
```python
STUDY_LOCATION_KEYWORDS = [
    'study site', 'study area', 'study location', 'study region', 'study system',
    'sampling site', 'sampling area', 'sampling location', 'sampling region',
    'field site', 'field work', 'field study', 'fieldwork',
    'survey site', 'survey area', 'survey location', 'survey region',
    'research site', 'research area', 'research location',
    'collection site', 'collection area', 'collection location',
    'conducted in', 'carried out in', 'performed in',
    'located in', 'situated in', 'based in',
    'specimens collected', 'sharks collected', 'individuals collected',
    'tagging occurred', 'capture occurred', 'sampling occurred',
]
```

**Context check**:
```python
for match in matches:
    match_pos = match.start()

    # Get context window (100 chars before and after)
    context_start = max(0, match_pos - 100)
    context_end = min(len(text_lower), match_pos + len(pattern) + 100)
    context = text_lower[context_start:context_end]

    # Check if context contains study location keywords
    if any(kw in context for kw in STUDY_LOCATION_KEYWORDS):
        return country  # Valid match!
```

### 3. Longest Pattern First

**Problem**: "Wales" could match before "New South Wales"
**Solution**: Sort patterns by length (longest first)

```python
all_patterns.sort(key=lambda x: len(x[1]), reverse=True)
```

---

## Expected Results (After FIXED Run Completes)

### Comparison to Original Run

| Metric | Original (with bugs) | Expected FIXED | Change |
|--------|----------------------|----------------|--------|
| Papers processed | 5,457 (88.3%) | ~5,450-5,460 (88%) | Similar |
| Study country extracted | 4,496 (82.4%) | ~4,350-4,400 (80%) | -2-3% (stricter matching) |
| Parachute research cases | 2,609 (47.8%) | ~2,480-2,520 (45-46%) | -100-130 cases (false positives removed) |

### Expected Cuba Count

| Run | Cuba Papers | Notes |
|-----|-------------|-------|
| Original | 120 | ALL false positives ("incubated") |
| FIXED | 0-5 | Only actual Cuba field studies |

### Expected Mediterranean Pattern

| Run | Iran Papers | Notes |
|-----|-------------|-------|
| Original | ~15-20 (estimated) | Many false positives ("Mediterranean") |
| FIXED | ~2-5 | Only actual Iran field studies |

---

## Parachute Research Metrics

### SINK Countries
**Definition**: Countries studied disproportionately more than they produce researchers

**Sink Score Formula**: `(papers_studied - papers_authored) / papers_authored`
**High sink score** = Research destination without local research capacity

**Top SINKS** (from original run - will be recalculated):

| Country | Papers Authored | Papers Studied | Sink Score | Classification |
|---------|-----------------|----------------|------------|----------------|
| Cuba | 0 | 120 | ∞ | ❌ FALSE POSITIVE |
| Oman | 8 | 50 | 5.25 | MAJOR SINK |
| Bahamas | 0 | 13 | ∞ | MAJOR SINK |
| Mexico | 15 | 37 | 1.47 | SINK |
| Peru | 5 | 15 | 2.00 | SINK |

**Expected after FIXED**:
- Cuba will drop to ~0-5 papers (or disappear entirely)
- Oman, Bahamas, Mexico will likely remain top SINKS
- New countries may emerge as sinks

### SOURCE Countries
**Definition**: Countries producing researchers who predominantly study abroad

**Source Score Formula**: `(papers_authored - papers_studied) / papers_studied`
**High source score** = Researchers studying foreign ecosystems

**Top SOURCES** (from original run):

| Country | Papers Authored | Papers Studied | Source Score | Classification |
|---------|-----------------|----------------|--------------|----------------|
| Russia | 80 | 0 | ∞ | MAJOR SOURCE |
| Netherlands | 38 | 1 | 37.00 | MAJOR SOURCE |
| Switzerland | 34 | 0 | ∞ | MAJOR SOURCE |
| Ireland | 28 | 0 | ∞ | MAJOR SOURCE |
| Austria | 26 | 0 | ∞ | MAJOR SOURCE |
| Belgium | 26 | 0 | ∞ | MAJOR SOURCE |

**Expected after FIXED**:
- Source countries less likely to have false positives (author country is from Phase 3, which is reliable)
- Source scores will be stable

---

## Temporal Analysis (After FIXED Run Completes)

### Global North/South Parachute Research Trends

**SQL Query** (ready to run):
```sql
SELECT e.year,
       p.first_author_region,
       COUNT(*) as total_papers,
       SUM(CASE WHEN p.is_parachute_research = 1 THEN 1 ELSE 0 END) as parachute_papers,
       ROUND(100.0 * SUM(CASE WHEN p.is_parachute_research = 1 THEN 1 ELSE 0 END) / COUNT(*), 1) as parachute_pct
FROM extraction_log e
JOIN paper_geography p ON e.paper_id = p.paper_id
WHERE p.has_study_location = 1
  AND e.year >= 1990
GROUP BY e.year, p.first_author_region
ORDER BY e.year, p.first_author_region;
```

**Expected patterns**:
- Parachute research rate may have DECREASED over time (more local capacity building)
- Global North parachute rate likely higher than Global South
- Recent years (2015-2023) may show more collaborative patterns

### Country-Specific Trends

**SQL Query**:
```sql
-- Top 10 parachute research source countries over time
SELECT e.year,
       p.first_author_country,
       COUNT(*) as parachute_papers
FROM extraction_log e
JOIN paper_geography p ON e.paper_id = p.paper_id
WHERE p.is_parachute_research = 1
  AND e.year >= 1990
  AND p.first_author_country IN (
      'USA', 'Australia', 'UK', 'Canada', 'Germany',
      'Japan', 'France', 'Spain', 'Italy', 'Netherlands'
  )
GROUP BY e.year, p.first_author_country
ORDER BY e.year, p.first_author_country;
```

### North → South Parachute Research Patterns

**SQL Query**:
```sql
-- Global North authors studying Global South locations
SELECT p.first_author_country,
       p.study_country,
       COUNT(*) as papers,
       ROUND(AVG(e.year), 1) as avg_year
FROM paper_geography p
JOIN extraction_log e ON p.paper_id = e.paper_id
WHERE p.is_parachute_research = 1
  AND p.first_author_region = 'Global North'
  AND p.study_country IN (
      -- Global South countries with shark research
      SELECT DISTINCT first_author_country
      FROM paper_geography
      WHERE first_author_region = 'Global South'
  )
GROUP BY p.first_author_country, p.study_country
HAVING COUNT(*) >= 5
ORDER BY papers DESC;
```

**Expected patterns**:
- USA → Mexico/Ecuador/Bahamas (high counts)
- Australia → Indonesia/Papua New Guinea (high counts)
- UK/Europe → African coast (moderate counts)

---

## Next Steps

### 1. Wait for FIXED Phase 4 Completion
**Status**: Running (started 16:51)
**Expected completion**: ~18:51-19:51 (2-3 hours)
**Command**: Running in background with timeout 10800s (3 hours)

### 2. Validate FIXED Results
**Actions**:
- [ ] Check Cuba count (should be ~0-5, not 120)
- [ ] Verify total parachute research count (~2,480-2,520)
- [ ] Compare study country extraction rate (~80% vs 82% original)
- [ ] Spot-check 20 random parachute research cases for accuracy

### 3. Re-run Parachute Research Analysis
**Script to create**: Generate updated `outputs/parachute_research_analysis_FIXED.csv`

**SQL Query**:
```sql
SELECT first_author_country,
       COUNT(DISTINCT CASE WHEN is_parachute_research = 0 THEN paper_id END) as papers_authored,
       COUNT(DISTINCT paper_id) as papers_total,
       -- Calculate sink/source scores...
FROM paper_geography
WHERE has_study_location = 1
GROUP BY first_author_country
ORDER BY papers_total DESC;
```

### 4. Prepare Abstract Text (November 30 Deadline)

**Current text** (from author country data):
> "Geographic analysis of 6,183 papers (50.5% of analyzed corpus) shows that 34.6% were led by institutions in the USA (n = 2,137), 13.7% in Australia (n = 849), and 11.5% in the UK (n = 708). Regional analysis reveals that 88.7% of studies were led by institutions in the Global North (high-income countries in North America, Europe, and Australia/New Zealand), while only 11.3% originated from the Global South."

**Add parachute research paragraph** (after FIXED results):
> "Analysis of study locations (n = ~4,400 papers with extractable field sites) identified parachute research patterns in approximately 45-46% of papers (n = ~2,500), where author institution country differed from study location country. Major 'sink' countries (study locations with disproportionately low local research capacity) include [TOP 3 FROM FIXED], while major 'source' countries (researchers predominantly studying abroad) include [TOP 3 FROM FIXED]."

### 5. Temporal Analysis for Presentation (May 2025)

**Actions**:
- [ ] Run temporal SQL queries on FIXED data
- [ ] Generate time series plots:
  - Parachute research rate over time (Global North vs South)
  - Top source countries over time
  - Top sink countries over time
  - North → South flow patterns over time
- [ ] Create visualizations for presentation

---

## Documentation Files

### Scripts
- **`scripts/extract_study_locations_phase4.py`**: Original Phase 4 (contains false positives)
- **`scripts/extract_study_locations_phase4_FIXED.py`**: Corrected Phase 4 (word boundary + context validation)

### Logs
- **`logs/phase4_study_locations.log`**: Original Phase 4 output (complete, 5,457 papers)
- **`logs/phase4_study_locations_FIXED_v2.log`**: Current FIXED run (in progress)

### Data Files
- **`outputs/parachute_research_analysis.csv`**: Original analysis (contains false positives)
- **`outputs/parachute_research_analysis_FIXED.csv`**: To be generated after FIXED run completes

### Documentation
- **`docs/PHASE_4_STUDY_LOCATION_GUIDE.md`**: Comprehensive Phase 4 guide
- **`docs/PARACHUTE_RESEARCH_ANALYSIS_SUMMARY.md`**: This file (analysis summary)
- **`QUICK_START_GEOGRAPHIC_ANALYSIS.md`**: Quick reference for abstract deadline

---

## Database Schema

### `paper_geography` Table (Updated by Phase 4)

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `paper_id` | TEXT | Paper identifier | "Smith.etal.2015.pdf" |
| `first_author_country` | TEXT | Author institution country | "USA" |
| `first_author_region` | TEXT | Global North/South | "Global North" |
| `study_country` | TEXT | **Study location country** | "Ecuador" |
| `study_ocean_basin` | TEXT | Ocean basin | "South Pacific" |
| `study_latitude` | REAL | Study site latitude | -0.75 |
| `study_longitude` | REAL | Study site longitude | -90.30 |
| `study_location_text` | TEXT | Location snippet | "Sampling conducted in..." |
| `has_study_location` | BOOLEAN | 1 if study location extracted | 1 |
| `is_parachute_research` | BOOLEAN | **1 if author ≠ study country** | 1 |

---

## Known Limitations

### 1. Multi-Country Studies
**Issue**: Some studies span multiple countries
**Solution**: Script extracts FIRST country mentioned
**Impact**: May undercount collaborative international studies

### 2. Ocean-Only Studies
**Issue**: Pelagic studies (open ocean) have no study "country"
**Solution**: Ocean basin field captures these
**Impact**: Parachute research metric only valid for coastal/territorial studies

### 3. Collaborative Research
**Issue**: Not all foreign-led studies are "parachute" - some have local co-authors
**Solution**: Phase 4 only detects geographic mismatch, not collaboration depth
**Future work**: Analyze co-author affiliations to distinguish true collaborative vs parachute

### 4. Methods Section Not Found
**Issue**: ~11-12% of papers don't have extractable Methods sections
**Reasons**:
- Review papers (no fieldwork)
- Theoretical/modeling studies
- Lab-only studies
- Poor PDF quality

---

## Validation Plan

### Before Presenting Results

**Manual validation** (20 random papers):
1. Select 20 papers flagged as parachute research
2. Read Methods sections manually
3. Verify country extraction accuracy
4. Check for false positives

**Acceptance criteria**:
- >85% accuracy on country extraction
- >90% accuracy on parachute research flagging
- <5% false positive rate

**Sanity checks** (SQL):
```sql
-- Should be >0 (we know USA has some domestic studies)
SELECT COUNT(*) FROM paper_geography
WHERE first_author_country = 'USA' AND study_country = 'USA';

-- Should be >0 (we know some USA researchers study Mexico)
SELECT COUNT(*) FROM paper_geography
WHERE first_author_country = 'USA' AND study_country = 'Mexico';

-- Should be reasonable (<50% overall)
SELECT ROUND(AVG(CASE WHEN is_parachute_research = 1 THEN 100.0 ELSE 0.0 END), 1) as parachute_pct
FROM paper_geography WHERE has_study_location = 1;
```

---

## Timeline

| Task | Time | Status |
|------|------|--------|
| Original Phase 4 execution | 2-3 hours | ✅ COMPLETE (Nov 24 ~14:00) |
| False positive investigation | 30 min | ✅ COMPLETE (Nov 24 ~15:30) |
| FIXED script development | 1 hour | ✅ COMPLETE (Nov 24 ~16:30) |
| Path bug fix | 15 min | ✅ COMPLETE (Nov 24 ~16:50) |
| **FIXED Phase 4 execution** | **2-3 hours** | **🔄 RUNNING** (started 16:51) |
| Results validation | 1 hour | ⏸️ PENDING |
| Re-run analysis | 30 min | ⏸️ PENDING |
| Update abstract text | 30 min | ⏸️ PENDING |
| **TOTAL** | **~8 hours** | **~70% COMPLETE** |

---

**Generated**: 2025-11-24 16:53
**Script Status**: 🔄 Phase 4 FIXED running
**Expected Completion**: 18:51-19:51
**Next Milestone**: Validate results and update abstract (November 30 deadline)
