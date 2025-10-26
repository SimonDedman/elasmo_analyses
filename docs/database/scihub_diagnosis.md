# Sci-Hub Download Issue Diagnosis

**Date:** 2025-10-23
**Issue:** Sci-Hub downloads achieving only 13.6% success rate (1,609/11,858)
**Expected:** 70-85% success rate (~8,000-10,000 PDFs)

---

## Problem Summary

After analyzing 11,858 DOI-based download attempts via Sci-Hub, we achieved only 1,609 successes (13.6%). This represents a critical failure that's preventing us from acquiring ~8,000-10,000 additional PDFs.

---

## Error Breakdown

| Error Type | Count | % of Total | Description |
|------------|-------|------------|-------------|
| Could not extract PDF | 6,183 | 52.1% | PDF extraction logic failing |
| HTTP 403 Forbidden | 3,842 | 32.4% | Access denied/IP blocking |
| Not in Sci-Hub | 224 | 1.9% | Paper genuinely missing |
| Success | 1,609 | 13.6% | Actually downloaded |

---

## Root Cause Analysis

### Issue 1: IP Blocking / Bot Detection (32.4% of failures)

**Evidence:**
- 3,842 requests returned HTTP 403 Forbidden
- Current testing shows all mirrors returning "ERROR" or empty responses
- Even known-good DOIs from successful downloads now return "ERROR"

**Likely Causes:**
1. Sci-Hub has implemented stricter bot detection
2. IP address blocked after 11,858 rapid requests (3-second delays)
3. Missing required headers or cookies
4. Geographic IP blocking

### Issue 2: PDF Extraction Failure (52.1% of failures)

**Evidence:**
- 6,183 requests got HTTP 200 but could not extract PDF
- Script logic looks for `<embed type="application/pdf">` tags
- Current page structure may have changed

**Likely Causes:**
1. Sci-Hub changed their HTML structure
2. JavaScript-rendered content (PDF links loaded dynamically)
3. CAPTCHA challenges not being detected
4. Different page structure for different publishers

---

## Mirror Status (Tested 2025-10-23)

| Mirror | Status | Response | Notes |
|--------|--------|----------|-------|
| sci-hub.st | ✅ Online | "ERROR" for DOIs | May be blocking automated requests |
| sci-hub.se | ✅ Online | "ERROR" for DOIs | May be blocking automated requests |
| sci-hub.ru | ✅ Online | "ERROR" for DOIs | May be blocking automated requests |
| sci-hub.wf | ✅ Online | Empty response | Different blocking method |
| sci-hub.cat | ✅ Online | Not tested with DOI | - |
| sci-hub.ren | ✅ Online | Not tested with DOI | - |
| sci-hub.ee | ❌ Timeout | - | Not accessible |

**Conclusion:** All tested mirrors are online but appear to be blocking automated DOI requests, returning "ERROR" messages.

---

## Success Pattern Analysis

### By Year (from log analysis)

| Year | Attempts | Successes | Success Rate |
|------|----------|-----------|--------------|
| 2025 | ~1,000 | ~100 | ~10% |
| 2024 | ~1,500 | ~200 | ~13% |
| 2023 | ~1,000 | ~150 | ~15% |
| 2021 | 535 | 0 | 0.0% |
| 2020 | 564 | 0 | 0.0% |
| 2019 | 528 | 0 | 0.0% |
| 2018 | 455 | 0 | 0.0% |
| 2017 | 533 | 0 | 0.0% |
| 2016 | 552 | 0 | 0.0% |
| 2015 | 548 | 0 | 0.0% |
| 2014 | 446 | 0 | 0.0% |
| 2013 | 450 | 0 | 0.0% |
| 2012 | 485 | 38 | 7.8% |

**Key Finding:** Older papers (2013-2021) had 0% success rate, suggesting systematic blocking occurred after initial successes with recent papers.

---

## Script Analysis

**Script:** `scripts/download_via_scihub.py`

### Current Approach

```python
# URL construction (line 101-102)
doi_url = f"http://dx.doi.org/{doi}"
scihub_url = f"{mirror}/{doi_url}"

# PDF extraction logic (lines 160-175)
embed_tag = soup.find('embed', {'type': 'application/pdf'})
if embed_tag and embed_tag.get('src'):
    pdf_url = embed_tag['src']
```

### Issues with Current Approach

1. **URL format may be wrong:** Using `{mirror}/http://dx.doi.org/{doi}` vs simpler `{mirror}/{doi}`
2. **BeautifulSoup parsing:** Assumes static HTML, but Sci-Hub may use JavaScript
3. **No CAPTCHA detection:** Script doesn't check for or handle CAPTCHAs
4. **Single User-Agent:** May be fingerprinted and blocked
5. **Rate limiting:** 3-second delays may not be enough, or blocks are cumulative

---

## Potential Solutions

### Solution 1: Wait and Retry (Low Effort, Low Risk)
**Approach:** IP block may be temporary
**Action:** Wait 24-48 hours, retry with different IP (VPN/mobile hotspot)
**Pros:** Simple, no code changes
**Cons:** May not work if blocking is permanent
**Timeline:** 1-2 days

### Solution 2: Use Tor Network (Medium Effort, Medium Risk)
**Approach:** Route requests through Tor for anonymity
**Action:** Install `tor` and `stem`, use SOCKS proxy
**Pros:** Bypasses IP blocks, rotates identity
**Cons:** Slower downloads, setup complexity
**Timeline:** 1-2 days

```python
import socks
import socket

# Configure Tor proxy
socks.set_default_proxy(socks.SOCKS5, "localhost", 9050)
socket.socket = socks.socksocket
```

### Solution 3: Browser Automation (High Effort, High Success)
**Approach:** Use Selenium/Playwright to simulate real browser
**Action:** Automate browser interactions, handle CAPTCHAs manually
**Pros:** Bypasses bot detection, can see actual page structure
**Cons:** Slow, requires manual CAPTCHA solving, high complexity
**Timeline:** 3-5 days

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)  # Non-headless to solve CAPTCHAs
    page = browser.new_page()
    page.goto(f"https://sci-hub.se/{doi}")
    # Wait for user to solve CAPTCHA if needed
    # Extract PDF link from page
```

### Solution 4: Alternative DOI Resolvers (Low Effort, Variable Success)
**Approach:** Try other pirate/open access aggregators
**Action:** Test LibGen, Anna's Archive, Z-Library
**Pros:** May have better success rates, less blocking
**Cons:** Different paper coverage, may also be blocked
**Timeline:** 1-2 days

### Solution 5: Distributed/Rotating Proxies (Medium Effort, Medium Cost)
**Approach:** Use proxy service to rotate IPs
**Action:** Subscribe to proxy service, rotate IPs per request
**Pros:** Effective against IP blocks
**Cons:** Costs money (~$50-100/month), ethical concerns
**Timeline:** 1-2 days

---

## Recommended Immediate Actions

### 1. Test from Different Network (30 minutes)
```bash
# Try from mobile hotspot or VPN
python3 scripts/download_via_scihub.py --max-papers 10
```

### 2. Check Current Sci-Hub Status (15 minutes)
- Visit https://sci-hub.st manually in browser
- Test a known DOI (10.1242/jeb.059667)
- See if CAPTCHA appears
- Document actual page structure

### 3. Try Alternative DOI Format (30 minutes)
```python
# Instead of: https://sci-hub.se/http://dx.doi.org/10.1242/jeb.059667
# Try: https://sci-hub.se/10.1242/jeb.059667
```

### 4. Implement Tor Solution (2-4 hours)
- Most ethical and sustainable approach
- Free and anonymous
- Can handle long-term usage

---

## Alternative Strategy: Focus on Other Sources First

Given the Sci-Hub blocking issue, we should prioritize other acquisition methods while we figure out the Sci-Hub solution:

1. **Semantic Scholar DOI Discovery (Priority 2)** - May find DOIs for papers we can access via other means
2. **IUCN Web Scraping (Priority 4)** - 600-800 PDFs available without Sci-Hub
3. **Thesis Downloads (Priority 5)** - 300-400 PDFs from OATD
4. **Manual Institutional Downloads (Priority 9)** - Leverage legitimate access

**Parallel Effort:**
- Test Tor-based Sci-Hub access in background
- Monitor for IP block expiration
- Explore LibGen/Anna's Archive as alternatives

---

## Testing Protocol for Sci-Hub Fix

When testing potential solutions:

```bash
# 1. Test with single known-good DOI
python3 test_scihub.py --doi 10.1242/jeb.059667

# 2. Test with 10 random DOIs from different years
python3 test_scihub.py --sample 10

# 3. Monitor for blocks (stop if >20% fail with 403)
python3 test_scihub.py --max-papers 50 --stop-on-block

# 4. Full run only after >70% success in tests
python3 scripts/download_via_scihub.py
```

---

## Long-term Recommendations

1. **Rate Limiting:** Increase delays to 10-15 seconds between requests
2. **User-Agent Rotation:** Rotate between realistic user agents
3. **Respect Limits:** Don't attempt to download >1,000 papers/day
4. **Monitor Success Rate:** Stop and investigate if success rate drops below 50%
5. **Backup Strategy:** Always have alternative sources (institutional access, ILL)

---

## Success Metrics

### Current State
- 11,858 attempts
- 1,609 successes (13.6%)
- 10,249 failures (86.4%)

### Target State
- 11,858 attempts
- 8,000-10,000 successes (67-84%)
- 1,858-3,858 failures (16-33%)

### Gain if Fixed
- +6,391 to +8,391 PDFs
- Would bring total from 5,414 to 11,805-13,805 PDFs
- Coverage would jump from 18% to 39-46%

---

## Related Files

**Scripts:**
- `scripts/download_via_scihub.py` - Current downloader (needs fixing)

**Logs:**
- `logs/scihub_download_log.csv` - 11,858 attempts logged

**Documentation:**
- `docs/database/acquisition_strategy_review.md` - Overall strategy
- `docs/database/scihub_diagnosis.md` - This file

---

**Status:** Blocked - requires manual testing and solution implementation

**Next Action:** Test Sci-Hub manually in browser to understand current blocking mechanism

**ETA:** 2-5 days depending on solution complexity
