# Researcher Database Implementation Plan

**Date:** 2025-10-26
**Status:** Design Phase
**Priority:** HIGH - Solves geographic visualization requirement

---

## Executive Summary

Building a comprehensive researcher database will enable geographic analysis of shark research by linking papers → authors → institutions → countries. This approach is superior to manual geographic coding and provides additional benefits for collaboration network analysis and researcher productivity tracking.

---

## Problem Statement

**Current Situation:**
- Have 4,545 papers with techniques and disciplines classified
- Need geographic visualizations showing disciplines/techniques by location
- No paper-location linkages exist

**Proposed Solution:**
- Extract author information from PDFs and filenames
- Use ORCID API to get institutional affiliations
- Geocode institutions to countries/coordinates
- Link papers → authors → institutions → geographic locations

**Benefits:**
1. ✅ Solves geographic visualization requirement
2. ✅ Enables collaboration network analysis
3. ✅ Tracks researcher productivity over time
4. ✅ Identifies institutional research strengths
5. ✅ Can compare first author vs. corresponding author locations

---

## Data Sources

### 1. PDF Filenames (4,545 papers)
**Format:** `FirstAuthor.etal.YEAR.Title.pdf`

**Examples:**
- `Rao.etal.1950.On a new caligid parasite from the Indian hammerhead shark..pdf`
- `Matthews.etal.1950.Notes on the anatomy and biology of the basking shark.pdf`
- `Samuel.etal.1952.new species coelomic trematode genus Staphylo from Tiger.pdf`

**Extractable:**
- ✅ First author surname
- ✅ Year
- ✅ Title (partial)
- ❌ Full author list (need PDF extraction)
- ❌ Institutions (need ORCID/PDF)

### 2. PDF Metadata
**Extractable fields (via PyPDF2/pdfplumber):**
- `/Author` - Author names (sometimes)
- `/Title` - Full title
- `/Subject` - Keywords/abstract (rare)
- `/Creator` - Software used (not useful)

**First page text extraction needed for:**
- Full author list with affiliations
- Author order (first, corresponding)
- Institution names and addresses
- Email addresses

### 3. ORCID API
**Endpoint:** `https://pub.orcid.org/v3.0/search`

**Query by:** Author name + year + keywords

**Returns:**
- ORCID identifier
- Full name variations
- Employment history (institutions with dates)
- Education history
- Works (publications with DOIs)

**Rate limits:** 24 requests/second (public API)

**Example query:**
```
https://pub.orcid.org/v3.0/search?q=family-name:Matthews+AND+keyword:shark
```

### 4. CrossRef API (Alternative)
**Endpoint:** `https://api.crossref.org/works/{DOI}`

**If we have DOIs:**
- Full author list with ORCIDs
- Affiliations
- References
- Citations

**Challenge:** We don't have DOIs for all papers

### 5. OpenAlex API (Emerging option)
**Endpoint:** `https://api.openalex.org/works`

**Search by:** Title, authors, year

**Returns:**
- Author information
- Institution IDs
- Geographic coordinates of institutions
- Collaboration networks

---

## Database Schema Design

### Tables

#### 1. `researchers`
```sql
CREATE TABLE researchers (
    researcher_id INTEGER PRIMARY KEY AUTOINCREMENT,
    surname TEXT NOT NULL,
    given_names TEXT,
    full_name TEXT,
    orcid TEXT UNIQUE,
    email TEXT,
    first_seen_year INTEGER,
    last_seen_year INTEGER,
    total_papers INTEGER DEFAULT 0,
    h_index INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(surname, given_names)
);

CREATE INDEX idx_researchers_surname ON researchers(surname);
CREATE INDEX idx_researchers_orcid ON researchers(orcid);
```

#### 2. `institutions`
```sql
CREATE TABLE institutions (
    institution_id INTEGER PRIMARY KEY AUTOINCREMENT,
    institution_name TEXT NOT NULL UNIQUE,
    institution_name_normalized TEXT,  -- For deduplication
    country_code CHAR(2),  -- ISO 3166-1 alpha-2
    country_name TEXT,
    city TEXT,
    latitude REAL,
    longitude REAL,
    ror_id TEXT,  -- Research Organization Registry ID
    grid_id TEXT,  -- Global Research Identifier Database
    total_papers INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_institutions_country ON institutions(country_code);
CREATE INDEX idx_institutions_name ON institutions(institution_name_normalized);
```

#### 3. `paper_authors`
```sql
CREATE TABLE paper_authors (
    paper_author_id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id TEXT NOT NULL,  -- Filename
    researcher_id INTEGER NOT NULL,
    author_position INTEGER,  -- 1 = first, 999 = last (corresponding?)
    is_corresponding BOOLEAN DEFAULT 0,
    institution_id INTEGER,
    affiliation_text TEXT,  -- Raw affiliation string
    FOREIGN KEY (researcher_id) REFERENCES researchers(researcher_id),
    FOREIGN KEY (institution_id) REFERENCES institutions(institution_id),
    UNIQUE(paper_id, researcher_id, author_position)
);

CREATE INDEX idx_paper_authors_paper ON paper_authors(paper_id);
CREATE INDEX idx_paper_authors_researcher ON paper_authors(researcher_id);
CREATE INDEX idx_paper_authors_institution ON paper_authors(institution_id);
```

#### 4. `researcher_institutions` (for tracking mobility)
```sql
CREATE TABLE researcher_institutions (
    researcher_institution_id INTEGER PRIMARY KEY AUTOINCREMENT,
    researcher_id INTEGER NOT NULL,
    institution_id INTEGER NOT NULL,
    start_year INTEGER,
    end_year INTEGER,
    is_primary BOOLEAN DEFAULT 1,
    FOREIGN KEY (researcher_id) REFERENCES researchers(researcher_id),
    FOREIGN KEY (institution_id) REFERENCES institutions(institution_id),
    UNIQUE(researcher_id, institution_id, start_year)
);
```

#### 5. `researcher_orcid_cache`
```sql
CREATE TABLE researcher_orcid_cache (
    cache_id INTEGER PRIMARY KEY AUTOINCREMENT,
    search_name TEXT NOT NULL,
    search_year INTEGER,
    orcid TEXT,
    confidence_score REAL,  -- Match confidence
    orcid_data JSON,  -- Full ORCID response
    queried_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(search_name, search_year)
);
```

---

## Implementation Phases

### Phase 1: Filename-Based Author Extraction (Quick Win)
**Effort:** Low (1-2 hours)
**Data:** 4,545 first authors

**Steps:**
1. Parse all PDF filenames
2. Extract first author surname
3. Extract year
4. Create `researchers` table with basic info
5. Create `paper_authors` table (first authors only)

**Output:**
- CSV: `researchers_from_filenames.csv`
- CSV: `paper_first_authors.csv`
- Initial stats on author productivity

**Script:** `scripts/extract_authors_from_filenames.py`

---

### Phase 2: PDF Metadata & First Page Extraction (Medium Effort)
**Effort:** Medium (4-6 hours)
**Data:** Full author lists, affiliations

**Steps:**
1. Extract PDF metadata (`/Author`, `/Title`)
2. Extract first page text from each PDF
3. Use regex/NLP to identify:
   - Author list section
   - Affiliation superscripts/numbers
   - Institution names
   - Email addresses (for corresponding authors)
4. Parse structured author-affiliation mappings
5. Update `paper_authors` with full author lists
6. Populate `institutions` table (raw names)

**Challenges:**
- Varied formatting across journals/years
- OCR'd papers may have extraction errors
- Author-affiliation matching can be ambiguous

**Output:**
- CSV: `paper_authors_full.csv`
- CSV: `institutions_raw.csv`
- Quality report on extraction success rates

**Scripts:**
- `scripts/extract_authors_from_pdfs.py`
- `scripts/parse_affiliations.py`

---

### Phase 3: Institution Normalization & Geocoding (Medium Effort)
**Effort:** Medium (3-5 hours)
**Data:** Deduplicated institutions with coordinates

**Steps:**
1. Normalize institution names:
   - "Univ. of California" → "University of California"
   - "MIT" → "Massachusetts Institute of Technology"
2. Use ROR (Research Organization Registry) API for lookups
3. Geocode using:
   - ROR coordinates (if available)
   - Nominatim/OpenStreetMap API (free)
   - Google Geocoding API (if needed, has free tier)
4. Assign country codes (ISO 3166-1)
5. Update `institutions` table with coordinates

**Output:**
- CSV: `institutions_geocoded.csv`
- Map showing institution locations
- Country distribution summary

**Script:** `scripts/geocode_institutions.py`

---

### Phase 4: ORCID Integration (High Effort, Optional)
**Effort:** High (8-12 hours)
**Benefits:** High-quality institutional affiliation data

**Steps:**
1. For each unique researcher surname + year:
   - Query ORCID API with name + year + "shark" keyword
   - Cache results in `researcher_orcid_cache`
2. Match ORCID records to our researchers:
   - Compare publication years
   - Compare co-authors
   - Use fuzzy matching for names
3. Extract employment history from ORCID
4. Link researchers to institutions with date ranges
5. Update `researcher_institutions` table

**Rate limiting strategy:**
- Batch queries (24/second limit)
- Prioritize recent/prolific authors
- Cache all results for reuse

**Output:**
- CSV: `researchers_with_orcid.csv`
- CSV: `researcher_institution_history.csv`
- Match confidence report

**Script:** `scripts/orcid_integration.py`

---

### Phase 5: Geographic Analysis & Visualization (Low Effort)
**Effort:** Low (2-3 hours) - Once data exists
**Requires:** Phases 1-3 complete

**Analyses:**
1. Papers per country over time
2. Disciplines per country
3. Techniques per country/region
4. Collaboration networks (inter-country)
5. Institutional productivity rankings

**Visualizations:**
1. **Choropleth map** - Papers per country
2. **Bubble map** - Institution sizes by paper count
3. **Flow map** - International collaborations
4. **Regional breakdowns** - Discipline distribution by continent
5. **Time series** - Geographic spread of techniques

**Output:**
- Maps matching colleague's request (guuske map1/map2 style)
- R visualizations using: sf, rnaturalearth, ggplot2
- Interactive maps using: leaflet (optional)

**Scripts:**
- `scripts/analyze_geography.R`
- `scripts/visualize_geography.R`

---

## Technical Implementation Details

### Filename Parsing
```python
import re
from pathlib import Path

def parse_pdf_filename(filename):
    """
    Extract metadata from PDF filename.
    Format: FirstAuthor.etal.YEAR.Title.pdf
    """
    pattern = r'^(?P<first_author>[^.]+)\.(?:etal\.)?(?P<year>\d{4})\.(?P<title>.+)\.pdf$'
    match = re.match(pattern, filename)

    if match:
        return {
            'filename': filename,
            'first_author': match.group('first_author'),
            'year': int(match.group('year')),
            'title': match.group('title').replace('.', ' ')
        }
    return None
```

### PDF First Page Extraction
```python
import pdfplumber

def extract_authors_from_pdf(pdf_path):
    """
    Extract authors and affiliations from first page.
    """
    with pdfplumber.open(pdf_path) as pdf:
        first_page = pdf.pages[0]
        text = first_page.extract_text()

        # Look for author section (varies by journal)
        # Common patterns:
        # - Line before "Abstract"
        # - After title, before email
        # - Superscript numbers linking to affiliations

        authors = extract_author_names(text)
        affiliations = extract_affiliations(text)

        return {
            'authors': authors,
            'affiliations': affiliations
        }
```

### ORCID API Query
```python
import requests

def query_orcid(surname, year=None, keyword="shark"):
    """
    Query ORCID API for researcher.
    """
    base_url = "https://pub.orcid.org/v3.0/search"

    query_parts = [f"family-name:{surname}"]
    if year:
        query_parts.append(f"year:{year}")
    if keyword:
        query_parts.append(f"keyword:{keyword}")

    params = {
        'q': ' AND '.join(query_parts),
        'rows': 10
    }

    headers = {
        'Accept': 'application/json'
    }

    response = requests.get(base_url, params=params, headers=headers)

    if response.status_code == 200:
        return response.json()
    return None
```

### Institution Geocoding
```python
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

def geocode_institution(institution_name):
    """
    Get coordinates for institution.
    """
    geolocator = Nominatim(user_agent="eea_shark_panel")
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)

    location = geocode(institution_name)

    if location:
        return {
            'latitude': location.latitude,
            'longitude': location.longitude,
            'address': location.address,
            'country': extract_country(location.address)
        }
    return None
```

---

## Data Quality & Validation

### Quality Metrics

1. **Filename Parsing Success Rate**
   - Target: >99% (filenames are standardized)
   - Validation: Manual check of 100 random samples

2. **PDF Author Extraction Success Rate**
   - Target: >80% (varies by PDF quality)
   - Validation: Manual check of 100 random samples across decades

3. **Institution Matching Rate**
   - Target: >70% (fuzzy matching needed)
   - Validation: Manual review of top 50 institutions

4. **Geocoding Success Rate**
   - Target: >85% (common institutions should succeed)
   - Validation: Check that top 20 countries represented

5. **ORCID Match Rate** (if implemented)
   - Target: >30% (ORCID adoption varies)
   - Validation: Confidence scores >0.7 considered matches

### Validation Queries

```sql
-- Check for missing data
SELECT
    COUNT(*) as total_papers,
    COUNT(DISTINCT researcher_id) as unique_researchers,
    COUNT(DISTINCT institution_id) as unique_institutions,
    COUNT(DISTINCT country_code) as unique_countries
FROM paper_authors
LEFT JOIN institutions USING (institution_id);

-- Top institutions
SELECT
    institution_name,
    country_name,
    COUNT(*) as paper_count
FROM paper_authors
LEFT JOIN institutions USING (institution_id)
GROUP BY institution_id
ORDER BY paper_count DESC
LIMIT 20;

-- Papers per country
SELECT
    country_name,
    COUNT(DISTINCT paper_id) as paper_count,
    MIN(year) as first_year,
    MAX(year) as last_year
FROM paper_authors
LEFT JOIN institutions USING (institution_id)
GROUP BY country_code
ORDER BY paper_count DESC;
```

---

## Estimated Timeline

| Phase | Effort | Duration | Dependencies |
|-------|--------|----------|--------------|
| Phase 1: Filename extraction | Low | 2-3 hours | None |
| Phase 2: PDF extraction | Medium | 1-2 days | Phase 1 |
| Phase 3: Geocoding | Medium | 1 day | Phase 2 |
| Phase 4: ORCID (optional) | High | 2-3 days | Phases 1-3 |
| Phase 5: Visualization | Low | 4-6 hours | Phase 3 |
| **Total (Phases 1-3, 5)** | - | **3-4 days** | - |
| **Total (All phases)** | - | **5-7 days** | - |

**Recommended approach:** Implement Phases 1-3 and 5 first (3-4 days), defer Phase 4 (ORCID) as enhancement.

---

## Expected Outputs

### CSV Files
```
outputs/researchers/
├── researchers_from_filenames.csv
├── paper_first_authors.csv
├── paper_authors_full.csv
├── institutions_raw.csv
├── institutions_geocoded.csv
├── researchers_with_orcid.csv (if Phase 4)
└── researcher_institution_history.csv (if Phase 4)
```

### Analysis Files
```
outputs/analysis/
├── papers_per_country.csv
├── disciplines_per_country.csv
├── techniques_per_country.csv
├── institution_productivity.csv
└── collaboration_networks.csv
```

### Visualizations
```
outputs/figures/
├── world_map_papers_by_country.png/pdf
├── world_map_disciplines_by_country.png/pdf
├── institution_bubble_map.png/pdf
├── collaboration_network_map.png/pdf
└── geographic_technique_distribution.png/pdf
```

### Database
```
shark_panel.db (updated with new tables)
```

---

## Alternative/Hybrid Approaches

### Approach A: OpenAlex Only (Faster)
- Skip ORCID entirely
- Query OpenAlex API by title/authors
- Get institutions directly with coordinates
- **Pros:** Faster, simpler, includes coordinates
- **Cons:** May not match all papers (especially old ones)

### Approach B: Hybrid (Recommended)
1. Phase 1: Filename extraction (baseline)
2. Phase 2: PDF extraction (full author lists)
3. Phase 3a: OpenAlex lookup (modern papers)
4. Phase 3b: Geocoding (papers not in OpenAlex)
5. Phase 4: ORCID enrichment (optional, for researcher tracking)

This gives best coverage with reasonable effort.

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Poor PDF quality (OCR errors) | Medium | Focus on recent papers first, validate extraction rates |
| Institution name variations | High | Use ROR API for normalization, manual review of top 100 |
| Geocoding failures | Medium | Fallback to country-level if city fails |
| ORCID low match rate | Low | Make Phase 4 optional, use OpenAlex alternative |
| API rate limits | Low | Implement caching, batch processing, delays |
| Ambiguous author-affiliation matches | Medium | Flag low-confidence matches for review |

---

## Success Criteria

**Minimum Viable Product (Phases 1-3, 5):**
- ✅ Extract first author from all 4,545 papers
- ✅ Extract full author lists from >80% of papers
- ✅ Geocode >70% of institutions to country level
- ✅ Create world map showing papers per country
- ✅ Create discipline distribution by country visualization

**Stretch Goals (Phase 4):**
- ✅ ORCID matches for >30% of researchers
- ✅ Researcher mobility tracking
- ✅ Collaboration network analysis

---

## Next Steps

1. **Get approval** to proceed with Phases 1-3, 5
2. **Start with Phase 1** (quick win, 2-3 hours)
3. **Review Phase 1 outputs** with user
4. **Decide** on proceeding to Phases 2-5

Once Phase 1 complete, can immediately:
- Show preliminary author statistics
- Demonstrate feasibility
- Identify any filename parsing issues
- Adjust plan based on findings

---

**Status:** AWAITING USER APPROVAL TO PROCEED
**Recommended:** Start with Phase 1 (low risk, quick results)
