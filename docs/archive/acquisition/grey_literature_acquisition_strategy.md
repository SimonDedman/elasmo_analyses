# Grey Literature Acquisition Strategy

**Created:** 2025-10-22

This document outlines strategies for acquiring the ~13,890 papers without DOIs, which are predominantly grey literature.

---

## Category Breakdown

Based on analysis of papers without DOIs (2000+):

| Category | Count | Strategy |
|----------|-------|----------|
| IUCN Red List | 1,082 | Direct download from IUCN API |
| Conference Abstracts | ~1,200 | Scrape conference websites |
| Society Reports | ~300 | Society website scraping |
| Theses/Dissertations | ~500 | Institutional repositories |
| Books/Chapters | ~300 | Google Books, publisher sites |
| Local Journals | ~500 | Direct journal website access |
| Remaining | ~10,000 | Google Scholar, manual |

---

## 1. IUCN Red List Assessments (1,082 papers)

### Status: High Priority - Freely Available

**Source:** https://www.iucnredlist.org/

**API:** Yes - IUCN Red List API
- Endpoint: `https://apiv3.iucnredlist.org/api/v3/`
- Requires API key (free for non-commercial)
- Rate limit: 10,000 requests/month

**Download Strategy:**
```python
# Extract species names from titles
# Query IUCN API for assessment PDFs
# Many assessments available as downloadable PDFs
```

**Success Rate:** Expected 60-80% (older assessments may not have PDFs)

**Implementation:**
- Create `scripts/download_iucn_assessments.py`
- Extract species names from paper titles
- Query IUCN API for assessment documents
- Download available PDFs

---

## 2. Conference Abstracts (~1,200 papers)

### Major Conferences

**American Elasmobranch Society (AES)** - 448 papers
- Website: https://elasmo.org/
- Abstracts often available in proceedings PDFs
- Strategy: Scrape proceedings by year

**Shark International** - 174 papers
- Abstracts in program books
- Often available as downloadable PDFs
- Strategy: Direct PDF download from conference archives

**World Congress of Herpetology** - 143 papers
- Abstract books sometimes available
- Strategy: Contact organizers or check archives

**European Elasmobranch Association** - 56 papers
- Website may have proceedings
- Strategy: Check annual meeting archives

### Implementation Strategy

```python
# For each conference:
# 1. Identify conference website/archive
# 2. Find proceedings PDFs by year
# 3. Extract individual abstracts (OCR if needed)
# 4. Match to database by title/author/year
```

**Success Rate:** Expected 30-50% (many older conferences don't have digital archives)

---

## 3. Society Reports & Newsletters (~300 papers)

### Target Societies

**Report of Japanese Society for Elasmobranch Studies** - 105 papers
- May have archive on society website
- Strategy: Contact society or scrape archive

**CSIRO Marine and Atmospheric Research** - 63 papers
- Australia's CSIRO often publishes reports online
- URL: https://www.csiro.au/
- Strategy: Search CSIRO publications database

**Marine Fisheries Information Service** - 75 papers
- Indian marine fisheries reports
- Strategy: Check CMFRI website (Central Marine Fisheries Research Institute)

### Implementation

```python
# 1. Build list of society websites
# 2. Check for publications/reports sections
# 3. Match titles to database
# 4. Download PDFs where available
```

**Success Rate:** Expected 40-60%

---

## 4. Theses and Dissertations (~500 papers)

### Strategy: Institutional Repositories

**ProQuest Dissertations & Theses**
- Large database of theses
- Many available for download
- URL: https://www.proquest.com/

**OATD (Open Access Theses and Dissertations)**
- URL: https://oatd.org/
- Free access to global theses
- API available

**Google Scholar**
- Often links to institutional repositories
- Can find thesis PDFs

### Implementation

```python
# 1. Identify thesis papers (look for keywords: "thesis", "dissertation", "MSc", "PhD")
# 2. Search OATD by title/author
# 3. Search ProQuest (may require institutional access)
# 4. Fallback to Google Scholar
```

**Success Rate:** Expected 50-70% (many recent theses are online)

---

## 5. Peer-Reviewed Journals Without DOIs (~500 papers)

### High-Value Targets

**Zootaxa** - 94 papers (SHOULD have DOIs - investigate further)
**Cybium** - 143 papers (some may have DOIs)
**Fishery Bulletin** - 139 papers
**Biologia Marina Mediterranea** - 69 papers

### Strategy

1. **Check if DOIs exist** - Shark-References may have incomplete data
2. **Direct journal website** - Many provide free PDFs
3. **BioOne/JSTOR** - Check aggregator platforms
4. **CrossRef search** - May find DOIs we missed

---

## 6. Google Scholar Scraping

### Why Google Scholar?

- Indexes everything (including grey literature)
- Often links to free PDFs (institutional repos, ResearchGate, Academia.edu)
- Can find papers without DOIs

### Implementation

```python
# Using scholarly library
# 1. Search by title + author
# 2. Get PDF link if available
# 3. Download from institutional repository
# 4. Respect rate limits (1-2 seconds between requests)
```

**Challenges:**
- Rate limiting (need to be careful)
- CAPTCHAs (may need rotating IPs or manual intervention)
- No official API

**Success Rate:** Expected 20-40% for papers not found elsewhere

---

## 7. Semantic Scholar API

### Alternative to Google Scholar

**URL:** https://www.semanticscholar.org/product/api
- Free API with generous limits
- Good coverage of academic papers
- Returns PDF URLs when available

```python
import requests

def search_semantic_scholar(title, authors):
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        'query': title,
        'fields': 'title,authors,year,openAccessPdf'
    }
    response = requests.get(url, params=params)
    # Returns PDF URL if available
```

**Success Rate:** Expected 15-30% for grey literature

---

## Implementation Priority

### Phase 1: High-Yield, Structured Sources (Week 1)
1. **IUCN Red List** - 1,082 papers, ~70% success = **~750 PDFs**
2. **CSIRO Reports** - 63 papers, ~80% success = **~50 PDFs**
3. **Conference Proceedings PDFs** - 500 papers, ~40% success = **~200 PDFs**

**Expected Yield: ~1,000 PDFs**

### Phase 2: Institutional Repositories (Week 2)
1. **OATD Theses** - 500 papers, ~60% success = **~300 PDFs**
2. **ProQuest** - If institutional access available
3. **University Repositories** - Direct scraping

**Expected Yield: ~300 PDFs**

### Phase 3: Academic APIs (Week 3)
1. **Semantic Scholar** - All remaining papers
2. **Google Scholar** - Carefully, with rate limiting
3. **BASE (Bielefeld Academic Search Engine)** - https://www.base-search.net/

**Expected Yield: ~500 PDFs**

### Phase 4: Manual Outreach (Ongoing)
1. **ResearchGate requests** - Message authors
2. **Email authors directly** - For critical papers
3. **Library ILL** - Inter-library loan for key papers

---

## Expected Total Coverage

| Source | Papers | Success Rate | PDFs |
|--------|--------|--------------|------|
| **Current (Sci-Hub)** | 11,858 | 85% | 10,080 |
| **Dropbox** | - | - | 423 |
| **Previous** | - | - | 3,268 |
| **IUCN** | 1,082 | 70% | 750 |
| **Conferences** | 1,200 | 40% | 480 |
| **Theses** | 500 | 60% | 300 |
| **Societies** | 300 | 50% | 150 |
| **Semantic Scholar** | 5,000 | 20% | 1,000 |
| **Google Scholar** | 5,000 | 20% | 1,000 |
| **Manual** | - | - | 200 |

**Projected Total: ~17,600 PDFs (58% of 30,553)**

---

## Tools to Build

1. `scripts/download_iucn_assessments.py` - IUCN Red List scraper
2. `scripts/download_conference_abstracts.py` - Conference proceedings downloader
3. `scripts/search_semantic_scholar.py` - Semantic Scholar API integration
4. `scripts/search_google_scholar.py` - Google Scholar scraper (careful with rate limits)
5. `scripts/download_theses.py` - OATD and ProQuest integration
6. `scripts/master_grey_literature_downloader.py` - Orchestrator for all sources

---

## Rate Limiting & Ethics

- **IUCN API**: 10,000 requests/month (plenty)
- **Semantic Scholar**: 100 requests/second (generous)
- **Google Scholar**: **1-2 seconds between requests** (strict - avoid blocks)
- **Conference Sites**: 2-3 seconds (be respectful)

**Golden Rule:** Always add delays, identify our bot properly in User-Agent, and respect robots.txt

---

## Next Steps

1. ✅ **Complete Sci-Hub download** (running now)
2. **Implement IUCN downloader** (highest priority)
3. **Test Semantic Scholar API**
4. **Identify conference archives**
5. **Build grey literature orchestrator**

---

*This strategy could realistically bring us from 45% to 58% coverage, acquiring an additional ~3,500-4,500 PDFs from grey literature sources.*
