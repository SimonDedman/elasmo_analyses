# Paper Acquisition Strategy Review & Next Steps

**Date:** 2025-10-23
**Current Status:** 5,414 PDFs acquired (~18% of 30,000 total papers)
**Goal:** Maximize acquisition efficiency to reach 50-70% coverage

---

## Executive Summary

After extensive testing of multiple acquisition strategies, we have achieved **5,414 PDFs** (18% of database). This represents significant progress, but several key opportunities remain untapped. This document analyzes all attempted strategies, their success rates, and provides **actionable next steps prioritized by ROI**.

---

## Current Acquisition Status

### Papers Acquired: 5,414 PDFs

| Source | PDFs | % of Total | Notes |
|--------|------|------------|-------|
| **Sci-Hub (DOI-based)** | ~1,600 | 5.3% | 11,858 attempts, 13.6% success rate |
| **Direct downloads (URL-based)** | ~2,650 | 8.8% | 5,888 attempts, 45.1% success rate |
| **Dropbox library** | 423 | 1.4% | Previously owned papers |
| **Manual downloads** | ~741 | 2.5% | Institutional access, manual effort |
| **Total** | **5,414** | **~18%** | Actual count on disk |

### Database Composition (~30,000 papers)

- **Papers with PDF URLs:** ~6,000 (20%)
- **Papers with DOIs:** ~12,000 (40%)
- **Papers with neither:** ~12,000-15,000 (40-50%)

---

## Strategy Analysis: What We've Tried

### ✅ Strategy 1: Direct URL Downloads
**Script:** `scripts/download_pdfs_from_database.py`

**Results:**
- **Attempts:** 5,888 papers with PDF URLs
- **Successes:** 2,653 (45.1%)
- **Status:** Exhausted - all URL-based papers attempted

**Success Factors:**
- Good success rate on open access journals (PeerJ, PLOS, BMC)
- Recent papers (2020-2025) more available
- Well-maintained publisher sites

**Failure Reasons:**
- **Paywalled (24.9%):** HTML received instead of PDF
- **Forbidden (15.8%):** HTTP 403 errors requiring institutional access
- **Broken links (10.8%):** HTTP 404 errors
- **Timeouts (1.8%):** Server too slow

**Top Failed Domains:**
- Wiley: 337 papers (paywall)
- ScienceDirect: 254 papers (CAPTCHA + paywall)
- Taylor & Francis: 136 papers (paywall)
- NOAA sites: 130 papers (government shutdown - **RETRY OPPORTUNITY**)

**Recommendation:** ✅ Complete - Do not retry except NOAA papers after government operations resume

---

### ⚠️ Strategy 2: Sci-Hub (DOI-based)
**Script:** `scripts/download_via_scihub.py`

**Results:**
- **Attempts:** 11,858 papers with DOIs
- **Successes:** 1,609 (13.6%)
- **Status:** Surprisingly low success rate

**Expected vs Actual:**
- Expected: ~85% success (based on initial tests)
- Actual: 13.6% success
- **Gap indicates technical issue or outdated mirror**

**Status Breakdown:**
- Success: 1,609 (13.6%)
- Error: 10,025 (84.5%)
- Not in Sci-Hub: 224 (1.9%)

**Critical Findings:**
⚠️ **84.5% error rate suggests:**
1. Mirror may be down/blocked (`sci-hub.st`)
2. PDF extraction logic failing
3. Rate limiting/IP blocking
4. Network connectivity issues

**Recommendation:** 🔴 **HIGH PRIORITY - Investigate & Fix**
- Test different Sci-Hub mirrors (`sci-hub.se`, `sci-hub.ru`)
- Verify PDF extraction logic
- Check for IP blocks
- Consider using Tor/proxies
- **Potential gain: +8,000 PDFs if fixed (70% success rate)**

---

### ❌ Strategy 3: Open Access APIs (Multisource)
**Script:** `scripts/retrieve_papers_multisource.py`

**APIs Tested:**
- Unpaywall API
- Semantic Scholar API
- CrossRef API
- DOI resolution

**Results:**
- **Attempts:** 3,064 papers
- **Successes:** 0 (0.0%)
- **Status:** Completely ineffective

**Why it Failed:**
- Most shark biology papers are in paywalled journals
- Recent papers (2024-2025) not yet in open repositories
- Specialized field lacks strong open access policies
- Valid DOIs but papers unavailable as OA

**Recommendation:** ✅ Abandon - 0% success rate, not worth pursuing

---

### ❌ Strategy 4: ResearchGate & Academia.edu
**Script:** `scripts/download_from_researchgate.py`, `scripts/download_from_academia.py`

**Results:**
- **Status:** Authentication blocked
- **Successes:** 0
- **Attempts:** Limited testing only

**Why it Failed:**
- Both platforms have sophisticated anti-bot protection
- Require authentication/login
- Would need browser automation (Selenium/Playwright)

**Recommendation:** ⚠️ **Revisit with browser automation or manual request workflow**
- Could be valuable for papers not found elsewhere
- Manual "request" button clicking for high-priority papers
- **Estimated potential: 500-1,000 PDFs**

---

### ❌ Strategy 5: IUCN Red List Assessments
**Script:** `scripts/download_iucn_assessments.py`

**Results:**
- **Attempts:** 1,104 papers
- **Successes:** 0 (0.0%)
- **Status:** API returns no PDFs

**Why it Failed:**
- IUCN API doesn't provide direct PDF downloads
- Assessments exist but not accessible via API
- Would require web scraping or manual download

**Recommendation:** ⚠️ **Revisit with web scraping approach**
- IUCN assessments are publicly available
- Need to scrape species pages directly
- **Estimated potential: 600-800 PDFs (60-70% of 1,104)**

---

### ✅ Strategy 6: Dropbox Library Integration
**Script:** Custom inline Python

**Results:**
- **Scanned:** 2,727 PDFs in Dropbox
- **Matched:** 423 papers (15.5%)
- **Status:** Complete

**Success Factors:**
- Good metadata in existing PDF collection
- Title-based matching worked well

**Recommendation:** ✅ Complete - Expand to other local folders if available

---

### ⚠️ Strategy 7: Semantic Scholar Search
**Script:** `scripts/search_semantic_scholar.py`

**Results:**
- **Searches:** 13,890 papers
- **Status:** Log created but no download attempts recorded

**Current Status:** Unclear - needs investigation

**Recommendation:** 🟡 **Investigate log file and test effectiveness**
- Check if DOIs were found
- Test download success rate
- **Potential gain: 1,000-2,000 PDFs (10-15% success)**

---

### ⚠️ Strategy 8: Thesis Downloads
**Script:** `scripts/download_theses_multisource.py`

**Results:**
- **Log entries:** 325
- **Status:** Unclear from logs

**Potential Sources:**
- OATD (Open Access Theses & Dissertations)
- ProQuest
- University repositories

**Recommendation:** 🟡 **Test and optimize**
- ~500 thesis papers in database
- Expected 50-70% success rate
- **Potential gain: 250-350 PDFs**

---

### ❌ Strategy 9: Timeout Retries
**Script:** `scripts/retry_failed_downloads.py`

**Results:**
- **Tested:** 2 papers with 60s timeout
- **Successes:** 0 (both still timed out)
- **Status:** Ineffective

**Recommendation:** ✅ Abandon - Not worth the time investment

---

## Papers Never Attempted

Based on logs analysis:

- **Papers attempted:** ~17,000 unique papers
- **Papers never tried:** ~13,000 (43% of database)
- **Papers with DOI never tried:** ~200 (most have been tried)
- **Papers with neither DOI nor URL:** ~12,000-15,000

---

## Recommended Next Steps (Prioritized by ROI)

### 🔴 Priority 1: Fix Sci-Hub Downloads (URGENT)
**Potential Gain:** +8,000 PDFs (70% success from 11,858 attempts)
**Effort:** Medium (2-4 hours debugging)
**ROI:** 🔥 **HIGHEST - Could double our collection**

**Action Items:**
1. Test all Sci-Hub mirrors to find working ones
2. Check PDF extraction logic in `scripts/download_via_scihub.py:154-175`
3. Verify not IP blocked (test from different network)
4. Consider using Tor or proxies if blocked
5. Add better error logging to identify failure points
6. Re-run download with fixed configuration

**Expected Timeline:** 1-2 days to fix and re-run

---

### 🟡 Priority 2: Semantic Scholar DOI Discovery
**Potential Gain:** +2,000-3,000 PDFs (15-20% of papers without DOIs)
**Effort:** Medium (investigation + optimization)
**ROI:** 🔥 **HIGH**

**Action Items:**
1. Investigate `logs/semantic_scholar_log.csv` to see what was found
2. Extract DOIs found by Semantic Scholar
3. Feed new DOIs to (fixed) Sci-Hub downloader
4. Search for papers without DOIs using title/author matching

**Expected Timeline:** 2-3 days

---

### 🟡 Priority 3: Retry NOAA Papers After Government Shutdown
**Potential Gain:** +130 PDFs
**Effort:** Low (automated retry)
**ROI:** 🟢 **HIGH - Easy wins**

**Action Items:**
1. Monitor NOAA sites (fishbull.noaa.gov, spo.nwr.noaa.gov)
2. When back online, retry these specific papers
3. Expected ~90% success rate (government open access)

**Expected Timeline:** Wait for government operations to resume

---

### 🟡 Priority 4: IUCN Assessment Web Scraping
**Potential Gain:** +600-800 PDFs (60-70% of 1,104)
**Effort:** Medium-High (web scraping development)
**ROI:** 🟢 **GOOD**

**Action Items:**
1. Identify IUCN papers in database (search for "Red List", "IUCN" in titles)
2. Extract species names from titles
3. Build scraper to download assessment PDFs from IUCN website
4. Match downloaded PDFs to database

**Expected Timeline:** 3-4 days

---

### 🟡 Priority 5: Optimize Thesis Downloads
**Potential Gain:** +300-400 PDFs
**Effort:** Medium (optimization + expansion)
**ROI:** 🟢 **GOOD**

**Action Items:**
1. Review `logs/thesis_download_log.csv` to understand current status
2. Expand to multiple thesis sources:
   - OATD API
   - ProQuest (if institutional access available)
   - Google Scholar thesis search
3. Improve title/author matching

**Expected Timeline:** 2-3 days

---

### 🟢 Priority 6: ResearchGate/Academia.edu with Browser Automation
**Potential Gain:** +500-1,000 PDFs
**Effort:** High (browser automation setup)
**ROI:** 🟡 **MEDIUM**

**Action Items:**
1. Set up Selenium or Playwright
2. Automate login and PDF download
3. Handle CAPTCHAs and rate limiting
4. Focus on high-priority papers first

**Expected Timeline:** 5-7 days

---

### 🟢 Priority 7: Conference Proceedings Scraping
**Potential Gain:** +400-600 PDFs (30-50% of 1,200 conference papers)
**Effort:** High (manual website identification + scraping)
**ROI:** 🟡 **MEDIUM**

**Action Items:**
1. Identify major conferences:
   - American Elasmobranch Society (448 papers)
   - Shark International (174 papers)
   - World Congress of Herpetology (143 papers)
2. Find conference proceeding archives
3. Download proceedings PDFs
4. Extract individual abstracts
5. Match to database

**Expected Timeline:** 1-2 weeks

---

### 🟢 Priority 8: Google Scholar Scraping (Careful!)
**Potential Gain:** +1,000-2,000 PDFs (10-20% of remaining papers)
**Effort:** High (anti-bot evasion)
**ROI:** 🟡 **MEDIUM**

**Action Items:**
1. Use `scholarly` Python library or similar
2. Implement strict rate limiting (2-3 seconds between requests)
3. Use rotating User-Agents
4. Handle CAPTCHAs gracefully
5. Search for papers without DOIs first

**Expected Timeline:** 1-2 weeks (must be done slowly to avoid blocks)

---

### 🔵 Priority 9: Manual Institutional Access Downloads
**Potential Gain:** +1,000-2,000 PDFs
**Effort:** Very High (manual effort)
**ROI:** 🟡 **MEDIUM - But necessary for high-priority papers**

**Action Items:**
1. Focus on high-value paywalled domains:
   - Wiley (337 papers)
   - ScienceDirect (254 papers)
   - Taylor & Francis (136 papers)
2. Use Firefox cache extraction workflow
3. Spread downloads over time to avoid rate limiting
4. Prioritize recent papers (2020-2025)

**Expected Timeline:** Ongoing, 2-4 weeks part-time

---

### 🔵 Priority 10: DOI Hunting for Papers Without DOIs
**Potential Gain:** +2,000-3,000 PDFs (via Sci-Hub after finding DOIs)
**Effort:** Very High (automated + manual)
**ROI:** 🟡 **MEDIUM-LONG TERM**

**Action Items:**
1. For papers without DOIs (~12,000-15,000):
   - Query CrossRef API by title/author
   - Scrape journal websites
   - Check Google Scholar for citations with DOIs
2. Feed discovered DOIs to Sci-Hub
3. Focus on high-priority journals first

**Expected Timeline:** 2-4 weeks for automated approach, months for manual

---

## Projected Outcomes by Priority

### If We Complete Priorities 1-5 (2-3 weeks effort)

| Current | + Sci-Hub Fix | + Semantic DOIs | + NOAA | + IUCN | + Theses | **TOTAL** |
|---------|---------------|-----------------|--------|--------|----------|-----------|
| 5,414 | +8,000 | +2,500 | +130 | +700 | +350 | **17,094** |

**Final Coverage:** ~57% of 30,000 papers

---

### If We Complete All Priorities (2-3 months effort)

| After P1-5 | + ResearchGate | + Conferences | + Google Scholar | + Manual | + DOI Hunt | **TOTAL** |
|------------|----------------|---------------|------------------|----------|------------|-----------|
| 17,094 | +750 | +500 | +1,500 | +1,500 | +2,500 | **23,844** |

**Final Coverage:** ~79% of 30,000 papers

---

## Critical Issue: Sci-Hub 13.6% Success Rate

### Why This Matters

Our Sci-Hub download achieved only **13.6% success** vs. expected **70-85%**. This represents a **missed opportunity of ~8,000 PDFs**.

### Likely Causes

1. **Wrong/blocked mirror:** `sci-hub.st` may be blocked or outdated
2. **PDF extraction failure:** BeautifulSoup logic may not be finding PDFs correctly
3. **IP blocking:** Too many requests may have triggered blocks
4. **Network issues:** Connection problems during batch run

### How to Fix

```python
# Test each mirror individually
mirrors = ["https://sci-hub.st", "https://sci-hub.se", "https://sci-hub.ru",
           "https://sci-hub.ee", "https://sci-hub.cat"]

# Add robust logging
logging.info(f"Response status: {response.status_code}")
logging.info(f"Content-Type: {response.headers.get('Content-Type')}")
logging.debug(f"First 500 chars: {response.text[:500]}")

# Test with known-good DOIs first
test_dois = ["10.1371/journal.pone.0000000", ...]  # Papers known to be in Sci-Hub

# Consider using Tor for anonymity
# Consider adding random delays 3-10 seconds
```

---

## Recommended Action Plan

### Week 1: Quick Wins
- [ ] Fix and re-run Sci-Hub downloads (Priority 1)
- [ ] Investigate Semantic Scholar logs (Priority 2)
- [ ] Set up NOAA monitoring (Priority 3)

**Expected gain:** +8,000-10,000 PDFs

### Week 2-3: Medium Effort, High Yield
- [ ] Build IUCN scraper (Priority 4)
- [ ] Optimize thesis downloads (Priority 5)
- [ ] Begin DOI hunting for high-priority papers (Priority 10)

**Expected gain:** +1,000-1,500 PDFs

### Month 2-3: Long-term Strategies
- [ ] Set up browser automation for ResearchGate (Priority 6)
- [ ] Scrape conference proceedings (Priority 7)
- [ ] Careful Google Scholar scraping (Priority 8)
- [ ] Ongoing manual downloads (Priority 9)

**Expected gain:** +3,000-5,000 PDFs

---

## Success Metrics

### Short-term (1 month)
- **Target:** 15,000-17,000 PDFs (50-57% coverage)
- **Primary driver:** Fixed Sci-Hub + Semantic Scholar DOIs

### Medium-term (3 months)
- **Target:** 20,000-24,000 PDFs (67-80% coverage)
- **Primary drivers:** IUCN + Theses + ResearchGate + Conferences

### Long-term (6 months)
- **Target:** 24,000-27,000 PDFs (80-90% coverage)
- **Primary drivers:** Systematic DOI hunting + Manual acquisition + Author outreach

---

## Key Takeaways

1. **🔴 CRITICAL:** Sci-Hub only achieved 13.6% success - fixing this could double our collection
2. **🟢 GOOD NEWS:** We have 5,414 PDFs (18%) with relatively low effort
3. **📊 REALISTIC GOAL:** 50-60% coverage achievable in 1 month with Priority 1-5
4. **🎯 AMBITIOUS GOAL:** 70-80% coverage achievable in 3 months with all priorities
5. **⚠️ DIMINISHING RETURNS:** Last 10-20% will require disproportionate effort (author emails, ILL)

---

## Files Referenced

**Scripts:**
- `scripts/download_via_scihub.py` - Sci-Hub downloader (NEEDS FIX)
- `scripts/download_pdfs_from_database.py` - Direct URL downloads (COMPLETE)
- `scripts/retrieve_papers_multisource.py` - OA APIs (INEFFECTIVE)
- `scripts/search_semantic_scholar.py` - Semantic Scholar (INVESTIGATE)
- `scripts/download_theses_multisource.py` - Thesis downloads (OPTIMIZE)

**Logs:**
- `logs/scihub_download_log.csv` - 11,858 attempts, 13.6% success
- `logs/pdf_download_log.csv` - 5,888 attempts, 45.1% success
- `logs/semantic_scholar_log.csv` - 13,890 searches (INVESTIGATE)
- `logs/multisource_retrieval_log.csv` - 3,064 attempts, 0% success
- `logs/dropbox_matches.csv` - 423 matches

**Documentation:**
- `docs/database/pdf_acquisition_complete_summary.md` - Previous summary
- `docs/database/pending_downloads_summary.md` - What's left
- `docs/database/grey_literature_acquisition_strategy.md` - Grey lit strategy

---

**Next Immediate Action:** Investigate and fix Sci-Hub download issue (Priority 1)

**Expected Impact:** +8,000 PDFs within 1-2 days

**Status:** Ready to proceed
