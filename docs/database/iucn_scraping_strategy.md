# IUCN Red List Assessment Scraping Strategy

**Created:** 2025-11-17
**Target:** 1,133 IUCN-related papers without DOIs
**Expected Success:** 600-800 PDFs (60-70%)

---

## Overview

IUCN Red List assessments are publicly available conservation status evaluations for species. Most shark/ray species have been assessed, and these assessments are available as PDFs through various channels.

---

## Paper Categories Identified

From our database of 1,133 IUCN-related papers:

1. **Individual Species Assessments** (~900 papers)
   - Title format: Just the species name (e.g., "Carcharodon carcharias", "Planonasus parini")
   - Year: Mostly 2016-2017 (mass reassessment period)
   - Source: IUCN Red List website

2. **Regional Assessment Reports** (~150 papers)
   - Examples:
     - "Conservation Status of Sharks, Rays, and Chimaeras in the Arabian Sea and Adjacent Waters"
     - "Conservation status of New Zealand chondrichthyans (chimaeras, sharks and rays), 2016"
   - Source: IUCN publications, regional reports

3. **Conservation Status Guides** (~50 papers)
   - Example: "Illustrated Guide To Protected Elasmobranchs In Indian Waters - With WPAA, IUCN, CITES & NDF Status"
   - Source: Government/NGO publications

4. **Research Using IUCN Data** (~33 papers)
   - Example: "Using DNA Barcoding to Investigate Patterns of Species Utilisation in UK Shark Products Reveals Threatened Species on Sale"
   - Source: Journal articles (may have DOIs but not in our database)

---

## Access Methods

### Method 1: IUCN Red List API (Recommended for Metadata)

**Endpoint:** `https://apiv3.iucnredlist.org/api/v3/`

**Requirements:**
- Free API token (register at https://apiv3.iucnredlist.org/api/v3/token)
- Rate limit: 10,000 requests/month (sufficient for our needs)

**Available Endpoints:**
```
/species/page/{species-name}        # Get species page info
/species/{id}                       # Get full species data
/species/narrative/{id}             # Get assessment narrative
/species/cite/{id}                  # Get citation info
/species/region/{id}/region/{region} # Regional assessments
```

**Limitations:**
- API does NOT provide direct PDF downloads
- PDF links may be embedded in returned HTML/JSON
- Assessment text available but not formatted PDFs

**Strategy:**
1. Query API for species metadata
2. Extract PDF URLs from response if available
3. Download PDFs directly from returned URLs

### Method 2: Direct Website Scraping

**URL Pattern:**
```
https://www.iucnredlist.org/species/{taxonid}/{assessmentid}
Example: https://www.iucnredlist.org/species/161796/5489267
```

**Challenges:**
- Website uses JavaScript rendering
- Returns 403 for automated requests
- Need browser automation (Selenium/Playwright)

**Strategy:**
1. Use Selenium with headless Chrome/Firefox
2. Navigate to species page
3. Look for "Download PDF" or "Assessment" links
4. Extract and download PDF

**Required Tools:**
- Selenium WebDriver
- ChromeDriver or GeckoDriver (Firefox)
- BeautifulSoup for HTML parsing

### Method 3: Alternative Sources

Many IUCN assessments are also available through:

1. **Species Pages PDF Archive**
   - Some assessments downloadable directly
   - URL pattern may be: `/pdf/{taxonid}_{assessmentid}.pdf`

2. **IUCN Publications Database**
   - https://portals.iucn.org/library/
   - Search by species name
   - Some full reports available

3. **Regional Assessment Reports**
   - Often published as standalone PDFs
   - Available on IUCN SSC (Species Survival Commission) pages
   - Example: https://www.iucnssg.org/publications.html (Shark Specialist Group)

---

## Implementation Plan

### Phase 1: API-Based Discovery (Lowest Effort)

**Goal:** Extract species IDs and check for direct PDF links

```python
import requests

API_TOKEN = "YOUR_TOKEN"
BASE_URL = "https://apiv3.iucnredlist.org/api/v3"

def get_species_info(genus, species):
    url = f"{BASE_URL}/species/page/{genus}-{species}"
    params = {"token": API_TOKEN}
    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()
        # Extract taxon_id, assessment_id
        # Look for PDF URLs in response
        return data

    return None
```

**Expected Success:** 20-30% (API may not provide PDF links)

### Phase 2: Selenium-Based Scraping (Higher Success)

**Goal:** Automate browser to access species pages and download PDFs

```python
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def scrape_species_pdf(genus, species):
    driver = webdriver.Chrome()  # or Firefox

    # Try multiple URL patterns
    urls_to_try = [
        f"https://www.iucnredlist.org/species/{genus}-{species}",
        f"https://www.iucnredlist.org/search?query={genus}%20{species}",
    ]

    for url in urls_to_try:
        driver.get(url)

        # Wait for page load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        # Look for PDF links
        pdf_links = driver.find_elements(By.XPATH, "//a[contains(@href, '.pdf')]")

        if pdf_links:
            pdf_url = pdf_links[0].get_attribute('href')
            # Download PDF
            return pdf_url

    driver.quit()
    return None
```

**Expected Success:** 60-70% (most recent assessments have PDFs)

### Phase 3: SSC Website Scraping (Specialist Group)

**Goal:** Access Shark Specialist Group publications

**URL:** https://www.iucnssg.org/publications.html

**Strategy:**
1. Scrape SSG publications page
2. Match publications to our database by title/species
3. Download regional assessment reports
4. Extract individual species assessments from reports

**Expected Success:** 10-20% (covers regional reports)

---

## Species Name Extraction

For papers with just species names as titles, we need to:

1. **Parse species name from title:**
   ```python
   import re

   def extract_species_name(title):
       # Pattern: Genus species (two words, first capitalized)
       match = re.search(r'([A-Z][a-z]+)\s+([a-z]+)', title)
       if match:
           return match.group(1), match.group(2)  # genus, species
       return None, None
   ```

2. **Validate species name:**
   - Check against known shark/ray species list
   - Use `species_list.csv` from database
   - Cross-reference with WoRMS (World Register of Marine Species)

3. **Handle variations:**
   - Some titles may have subspecies: "Genus species subspecies"
   - Some may have author/year: "Genus species (Author, Year)"
   - Clean before querying IUCN

---

## URL Construction Patterns

Based on IUCN website structure:

**Species Page:**
```
Pattern 1: /species/{taxon_id}/{assessment_id}
Pattern 2: /species/page/{genus}-{species}
Pattern 3: /species/{genus}-{species}
```

**PDF Direct Access (if exists):**
```
Pattern 1: /pdf/{taxon_id}_{assessment_id}.pdf
Pattern 2: /assessment/{assessment_id}/document
Pattern 3: /sites/default/files/assessment/{taxon_id}.pdf
```

**Search:**
```
https://www.iucnredlist.org/search?query={genus}+{species}
```

---

## Rate Limiting & Ethics

**API Rate Limits:**
- 10,000 requests/month = ~330 requests/day
- For 1,133 papers: ~3.5 days if doing API only

**Web Scraping Rate Limits:**
- Use 2-3 second delays between requests
- Rotate User-Agents
- Use sessions to maintain cookies
- Respect robots.txt

**Best Practices:**
- Run during off-peak hours
- Cache results to avoid re-scraping
- Download PDFs only once (check if already exists)
- Credit IUCN appropriately in publications

---

## Expected Outcomes

| Method | Papers Attempted | Expected Success | PDFs Downloaded |
|--------|------------------|------------------|-----------------|
| API-based | 900 | 20-30% | 180-270 |
| Selenium scraping | 900 | 60-70% | 540-630 |
| SSC publications | 233 | 10-20% | 23-47 |
| **TOTAL** | **1,133** | **60-70%** | **680-790** |

---

## Implementation Priority

### High Priority (Immediate)
1. **Register for IUCN API token**
2. **Extract clean species names** from titles
3. **Test API access** with 10-20 species

### Medium Priority (This Week)
4. **Set up Selenium** with Chrome/Firefox driver
5. **Test browser automation** on sample species
6. **Build scraping pipeline** with rate limiting

### Low Priority (Next Week)
7. **Scrape SSC publications**
8. **Match regional reports** to database
9. **Manual downloads** for high-priority missing papers

---

## Next Steps

1. **Immediate action:** Extract and clean species names from 1,133 papers
2. **Register for API token:** https://apiv3.iucnredlist.org/api/v3/token
3. **Test access methods:** Try API and Selenium on 5-10 sample species
4. **Choose best method:** Based on success rate of tests
5. **Build production scraper:** Implement chosen method at scale

---

## Files to Create

1. `scripts/extract_species_names_iucn.py` - Clean species names
2. `scripts/download_iucn_via_api.py` - API-based downloader
3. `scripts/download_iucn_via_selenium.py` - Browser automation
4. `scripts/scrape_iucn_ssg.py` - SSG publications scraper
5. `outputs/iucn_species_cleaned.csv` - Species names extracted
6. `logs/iucn_download_log.csv` - Download progress tracking

---

**Status:** Strategy designed, ready for implementation
**Estimated Development Time:** 2-3 days
**Estimated Runtime:** 1-2 days (with rate limiting)
**Expected Yield:** 680-790 PDFs
