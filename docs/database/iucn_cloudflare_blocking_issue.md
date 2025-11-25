# IUCN Red List Cloudflare Blocking Issue

**Discovered:** 2025-11-17
**Status:** Blocking automated scraping
**Impact:** Cannot scrape 1,098 IUCN species assessments via Selenium

---

## Problem

The IUCN Red List website (https://www.iucnredlist.org) uses **Cloudflare protection** that blocks automated browsers, even headless Selenium with ChromeDriver.

### Evidence

When accessing any IUCN URL with Selenium, the response is:

```html
<title>Just a moment...</title>
```

This is Cloudflare's challenge page that:
1. Detects automated browsers (Selenium WebDriver signature)
2. Requires JavaScript challenges to prove browser is human
3. Blocks all scrapers that don't solve the challenge

### URLs Tested (All Blocked)

- `https://www.iucnredlist.org/species/carcharodon-carcharias`
- `https://www.iucnredlist.org/species/Carcharodon-carcharias`
- `https://www.iucnredlist.org/search?query=Carcharodon+carcharias`

All return the same Cloudflare challenge page with no actual content.

---

## Technical Details

### Anti-Bot Measures Detected

1. **Cloudflare Bot Management**: Sophisticated detection of automated browsers
2. **JavaScript Challenge**: Requires solving crypto challenge before access
3. **WebDriver Detection**: Identifies Selenium `navigator.webdriver` property
4. **TLS Fingerprinting**: Analyzes TLS handshake to detect automation
5. **Browser Behavior Analysis**: Monitors mouse movement, timing patterns

### What Doesn't Work

- ❌ Standard Selenium (tested with Chrome + ChromeDriver)
- ❌ Headless mode (--headless=new)
- ❌ User-Agent spoofing
- ❌ Simple request delays
- ❌ Standard WebDriver options

---

## Alternative Approaches

### Approach 1: IUCN API (Recommended)

**Method:** Use official IUCN Red List API

**Pros:**
- Legal and official
- Reliable data access
- Structured JSON responses
- Free with registration

**Cons:**
- Does NOT provide direct PDF downloads
- Only provides assessment metadata
- Rate limited (10,000 requests/month)
- Requires API token registration

**Implementation:**
1. Register for API token: https://apiv3.iucnredlist.org/api/v3/token
2. Query species assessment metadata
3. Extract taxon IDs and assessment data
4. **Note:** Cannot download PDFs via API

**Expected Outcome:**
- Access to all 1,098 species metadata
- No PDF downloads
- Would need to manually download PDFs or use alternative source

---

### Approach 2: Undetected ChromeDriver

**Method:** Use `undetected-chromedriver` package to bypass Cloudflare

**Pros:**
- Specifically designed to bypass Cloudflare
- Regular updates to stay ahead of detection
- Works with most Cloudflare-protected sites
- Python package available

**Cons:**
- Constantly in arms race with Cloudflare updates
- May break unexpectedly
- Slower than standard Selenium
- Ethical gray area (bypassing protection)

**Implementation:**
```python
import undetected_chromedriver as uc

driver = uc.Chrome()
driver.get("https://www.iucnredlist.org/species/...")
# Should bypass Cloudflare challenge
```

**Expected Success Rate:** 60-80% (if working, but may break anytime)

---

### Approach 3: Playwright with Stealth Plugin

**Method:** Use Playwright browser automation with stealth mode

**Pros:**
- More modern than Selenium
- Better at avoiding detection
- Built-in stealth features
- Can handle dynamic JavaScript

**Cons:**
- Still detected by advanced Cloudflare
- Requires installing Playwright + browsers
- More complex setup

**Implementation:**
```python
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    stealth_sync(page)
    page.goto("https://www.iucnredlist.org/...")
```

---

### Approach 4: Alternative PDF Sources

**Method:** Find IUCN assessments from alternative sources

**Sources to Try:**

1. **IUCN SSG Publications**
   - URL: https://www.iucnssg.org/publications.html
   - Shark Specialist Group hosts regional reports
   - PDFs directly downloadable (no Cloudflare)
   - Covers ~150 papers from our list

2. **Biodiversity Heritage Library**
   - URL: https://www.biodiversitylibrary.org/
   - Some IUCN assessments archived
   - Full-text search available
   - No Cloudflare protection

3. **Google Scholar**
   - Many IUCN assessments have PDFs hosted elsewhere
   - Can search by species name + "IUCN Red List"
   - Some hosted on university repositories

4. **ResearchGate / Academia.edu**
   - Authors often upload their IUCN assessments
   - No scraping protection
   - Partial coverage

**Expected Outcome:**
- Regional reports: 80-100% success (~150 papers)
- Individual assessments: 20-30% success (~220-330 papers)
- Total: ~370-450 PDFs (versus 680-790 originally expected)

---

### Approach 5: Manual Download + Automation

**Method:** Semi-automated approach with manual intervention

**Process:**
1. Use API to get list of taxon IDs
2. Generate direct URLs for each species page
3. Provide user with clickable list
4. User manually downloads PDFs (browser passes Cloudflare)
5. Script processes downloaded PDFs and renames them

**Pros:**
- Guaranteed to work (human passes Cloudflare)
- Legal and ethical
- One-time effort

**Cons:**
- Very time-consuming (1,098 species)
- Requires manual clicks for each PDF
- Estimated time: 10-15 hours of clicking

---

## Recommended Strategy

Given the constraints, I recommend a **hybrid approach**:

### Phase 1: API for Metadata (Immediate)
1. Register for IUCN API token
2. Query all 1,098 species to get:
   - Taxon IDs
   - Assessment dates
   - Conservation status
   - Direct URLs to species pages
3. Save metadata to CSV

**Outcome:** Complete metadata for all species, no PDFs

### Phase 2: Try Undetected ChromeDriver (This Week)
1. Install `undetected-chromedriver` package
2. Test on 10-20 species
3. If working, run full scraping pipeline
4. Monitor for blocks/failures

**Outcome:** 0-790 PDFs (depending on if bypass works)

### Phase 3: Alternative Sources (This Week)
1. Download regional reports from IUCN SSG website (no Cloudflare)
2. Extract individual assessments from reports
3. Search Google Scholar for missing species

**Outcome:** ~370-450 PDFs

### Phase 4: Manual Fallback (If Needed)
1. Generate prioritized list of high-value species
2. User manually downloads top priority PDFs
3. Focus on recent assessments (2016-2017)

**Outcome:** Variable (depends on effort)

---

## Implementation Timeline

| Phase | Effort | Time | Expected PDFs |
|-------|--------|------|---------------|
| Phase 1: API metadata | Low | 1 hour | 0 (metadata only) |
| Phase 2: Bypass attempt | Medium | 2-3 hours | 0-790 |
| Phase 3: Alternative sources | Medium | 3-4 hours | 370-450 |
| Phase 4: Manual (if needed) | High | 10-15 hours | Variable |

**Total Time (automated only):** 6-8 hours development + runtime
**Expected Automated Yield:** 370-1,240 PDFs

---

## Next Steps

### Immediate (Choose One Path)

**Option A: API-Only Path**
1. Register IUCN API token (5 min)
2. Build API metadata extractor (30 min)
3. Query all 1,098 species (1 hour runtime)
4. Accept no PDFs, just metadata
5. Move on to other download priorities (PeerJ, DOI discovery results)

**Option B: Bypass Attempt**
1. Install `undetected-chromedriver` (5 min)
2. Test on 5 species (30 min)
3. If working: run full pipeline (3-4 hours runtime)
4. If failing: fall back to Option A

**Option C: Alternative Sources**
1. Scrape IUCN SSG website (no Cloudflare)
2. Download regional reports (1-2 hours)
3. Search Google Scholar for remaining species
4. Accept lower coverage (370-450 PDFs)

### Recommendation

**Try Option B first** (undetected-chromedriver)
- Low effort to test (30 min setup + test)
- High payoff if it works (790 PDFs)
- Clear fallback if it fails (API metadata only)
- Can always fall back to Option C for regional reports

---

## Files to Create/Modify

**If API Path:**
- `scripts/download_iucn_via_api.py` - API-based metadata extractor
- `outputs/iucn_species_metadata.csv` - Species data without PDFs

**If Bypass Path:**
- `scripts/download_iucn_undetected.py` - Modified scraper using undetected-chromedriver
- Update `requirements.txt` to include undetected-chromedriver

**If Alternative Sources:**
- `scripts/scrape_iucn_ssg.py` - SSG publications scraper
- `scripts/search_google_scholar_iucn.py` - Scholar search for PDFs

---

## Status

**Current Situation:**
- ✅ 1,098 species identified and cleaned
- ✅ Selenium scraper built (functional code)
- ❌ Cloudflare blocks all automated access
- ⏸️  IUCN scraping paused pending bypass solution

**Awaiting Decision:**
- Which approach to pursue (A, B, or C)
- User's risk tolerance for bypass tools
- Priority level of IUCN PDFs vs other download tasks

**Alternative Priorities:**
- DOI discovery completing soon (~19:00 ETA) → will unlock 650-950 new PDFs via Sci-Hub
- PeerJ downloads (80 OA papers, should be straightforward)
- Semantic Scholar results analysis (potential additional DOIs)

---

**Recommendation:** Pause IUCN scraping for now, focus on DOI discovery results (higher ROI), revisit IUCN with bypass tools if time permits.
