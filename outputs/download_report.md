# Shark Papers Download Report

**Generated:** 2026-01-09
**Database:** literature_review.parquet
**PDF Library:** /media/simon/data/Documents/Si Work/Papers & Books/SharkPapers

---

## Executive Summary

| Metric | Value |
|--------|-------|
| Total papers in database | 30,553 |
| Papers with DOI | 30,523 |
| Total PDFs downloaded | 19,070 |
| Overall coverage | 62.4% |
| **Remaining gap** | **11,483 papers** |
| Already queried (no PDF available) | 3,931 |
| Not yet queried via Unpaywall | 7,552 |

---

## Coverage by Decade

| Decade | PDFs | In Database | Coverage | Gap |
|--------|------|-------------|----------|-----|
| 1950s | 106 | 495 | 21.4% | 389 |
| 1960s | 281 | 942 | 29.8% | 661 |
| 1970s | 593 | 1,571 | 37.7% | 978 |
| 1980s | 845 | 2,294 | 36.8% | 1,449 |
| 1990s | 1,149 | 3,462 | 33.2% | 2,313 |
| 2000s | 2,877 | 6,797 | 42.3% | 3,920 |
| 2010s | 7,187 | 9,241 | 77.8% | 2,054 |
| 2020s | 4,390 | 5,739 | 76.5% | 1,349 |
| **TOTAL** | **17,428** | **30,541** | **57.1%** | **13,113** |

### Recent Years Detail

| Year | PDFs | In Database | Coverage |
|------|------|-------------|----------|
| 2015 | 779 | 933 | 83.5% |
| 2016 | 787 | 886 | 88.8% |
| 2017 | 820 | 906 | 90.5% |
| 2018 | 810 | 809 | 100.1% |
| 2019 | 875 | 862 | 101.5% |
| 2020 | 1,010 | 956 | 105.6% |
| 2021 | 1,016 | 991 | 102.5% |
| 2022 | 879 | 918 | 95.8% |
| 2023 | 506 | 915 | 55.3% |
| 2024 | 545 | 1,153 | 47.3% |
| 2025 | 434 | 806 | 53.8% |

> Note: Coverage >100% indicates PDFs exist that may not be in the current database version.

---

## Download Sources & Results

### 1. Unpaywall API

The primary source for open access papers.

| Status | Count | Percentage |
|--------|-------|------------|
| Not Open Access | 2,293 | 51.0% |
| Failed to download | 1,638 | 36.4% |
| **Successfully downloaded** | **552** | **12.3%** |
| Already exists | 9 | 0.2% |
| OA but no PDF URL | 6 | 0.1% |
| **Total queried** | **4,498** | 100% |

**Open Access Status:**
- OA papers found: 2,205 (49.0%)
- Not Open Access: 2,293 (51.0%)

### 2. Sci-Hub (via Tor)

Attempted for papers not available via Unpaywall.

| Status | Count | Percentage |
|--------|-------|------------|
| Error | 229 | 63.8% |
| Forbidden | 116 | 32.3% |
| Not found | 14 | 3.9% |
| **Total attempted** | **359** | 100% |

> Note: 0% success rate. Sci-Hub appears to have limited coverage for recent papers (2019+) or connection issues.

### 3. Custom Repository Scrapers

| Repository | Attempted | Success | Rate |
|------------|-----------|---------|------|
| Archimer (IFREMER) | 7 | 7 | 100% |
| Scientia Marina | 22 | 22 | 100% |
| Handle.net redirects | 45 | 7 | 16% |
| Inter-Research | 57 | 0 | 0% (auth required) |
| **Total** | **131** | **36** | **27%** |

---

## Failure Analysis

### Unpaywall Download Failures (1,638 total)

| Category | Count | % | Recoverable? |
|----------|-------|---|--------------|
| DOI redirect (landing page) | 501 | 30.6% | Partial - needs scraping |
| Wiley (auth required) | 331 | 20.2% | No - subscription needed |
| Other | 307 | 18.7% | Varies |
| Archimer | 174 | 10.6% | Yes - scraped (7 unique) |
| Inter-Research (auth) | 57 | 3.5% | No - returns 401 |
| Taylor & Francis (auth) | 57 | 3.5% | No - subscription needed |
| Oxford UP (auth) | 52 | 3.2% | No - subscription needed |
| Handle.net | 45 | 2.7% | Partial - scraped 7/45 |
| PubMed Central | 31 | 1.9% | Should work - may need retry |
| Scientia Marina | 22 | 1.3% | Yes - scraped all 22 |
| Elsevier (auth) | 18 | 1.1% | No - subscription needed |
| Zenodo | 16 | 1.0% | Should work - may need retry |
| Figshare | 7 | 0.4% | Should work - may need retry |
| Springer (auth) | 7 | 0.4% | No - subscription needed |
| PeerJ | 5 | 0.3% | Should work - may need retry |
| Science | 5 | 0.3% | No - subscription needed |
| Nature | 2 | 0.1% | No - subscription needed |
| PLOS | 1 | 0.1% | Should work - check URL |

### Summary by Recoverability

| Category | Count | Notes |
|----------|-------|-------|
| **Auth required** | 522 | Wiley, T&F, OUP, Springer, Elsevier, Inter-Research |
| **Already scraped** | 241 | Archimer, Handle.net, Scientia Marina |
| **DOI redirects** | 501 | Would need per-publisher scrapers |
| **Other/Various** | 374 | Mix of issues |

---

## Remaining Gaps

### Gap Breakdown

| Category | Count |
|----------|-------|
| **Total papers without PDF** | **11,483** |
| Already queried via Unpaywall, no PDF available | 3,931 |
| **Not yet queried via Unpaywall** | **7,552** |

### Expected Yield from Querying Remaining DOIs

| Step | Estimate |
|------|----------|
| DOIs to query | 7,552 |
| OA papers found (~49% rate) | ~3,700 |
| Successful downloads (~25% of OA) | **~930 new PDFs** |

> The 25% download success rate reflects that many "OA" links fail (auth required, landing pages, broken URLs).

### Handle.net Failures Detail

The Handle.net scraper had issues with:
- **CSIC (digital.csic.es)**: 15+ papers - server returning 500 errors
- **Timeouts**: 3 repositories not responding
- **No PDF found**: Landing pages without discoverable PDF links
- **403 Forbidden**: Some repos require authentication

---

## Recommendations

### High Priority

1. **Query remaining 7,552 DOIs via Unpaywall**
   - These are papers in the gap that haven't been checked yet
   - Expected yield: ~930 new PDFs (based on 49% OA rate × 25% download success)

2. **Retry PubMed Central failures (31 papers)**
   - These should be freely available
   - May need different URL handling

3. **Retry Zenodo/Figshare (23 papers)**
   - Open repositories, should be accessible
   - Check for rate limiting issues

### Medium Priority

4. **Create DOI redirect scrapers**
   - 501 papers redirect to publisher landing pages
   - Would need per-publisher logic

5. **Retry CSIC later**
   - 15+ papers failed due to server errors
   - May work when their system is stable

### Low Priority / Not Recoverable

6. **Publisher subscriptions (522 papers)**
   - Wiley: 331
   - Taylor & Francis: 57
   - Oxford UP: 52
   - Requires institutional access

---

## Scripts Created

| Script | Purpose |
|--------|---------|
| `download_unpaywall.py` | Query Unpaywall API for OA URLs |
| `download_via_scihub_tor.py` | Download via Sci-Hub over Tor |
| `download_archimer.py` | Scrape Archimer repository |
| `download_scientia_marina.py` | Download from Scientia Marina |
| `download_handle_net.py` | Follow Handle.net redirects |

---

## Log Files

All download attempts are logged in the `logs/` directory:

- `unpaywall_download_log.csv` - Unpaywall API results
- `scihub_tor_download_log.csv` - Sci-Hub attempts
- `archimer_download.log` - Archimer scraper log
- `scientia_marina_download.log` - Scientia Marina log
- `handle_net_download.log` - Handle.net scraper log

---

*Report generated by Claude Code*
