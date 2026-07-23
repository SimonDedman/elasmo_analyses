# Pending Downloads Summary

**Generated:** 2025-10-22 00:34:34

---

## Overview

**Total papers in database:** 30,523

**Papers with PDFs:** 2,750 (9.0%)
- Direct downloads: 2,653
- From Dropbox library: 97

**Papers still pending:** 3,138 (10.3%)

---

## Pending Breakdown by Status

| Status | Count | Notes |
|--------|-------|-------|
| error | 1,464 | HTML returned instead of PDF (mostly paywalls) |
| forbidden | 933 | HTTP 403 - Requires institutional access |
| not_found | 637 | HTTP 404 - Broken links |
| timeout | 104 | Download timeout (need retry with 60s timeout) |

---

## Pending Downloads by Domain

Top domains requiring manual download or institutional access:

| Domain | Papers | Priority |
|--------|--------|----------|
| onlinelibrary.wiley.com | 337 | Medium |
| www.sciencedirect.com | 254 | High (paywall) |
| www.sharksinternational.org | 174 | Medium |
| www.tandfonline.com | 136 | Medium |
| jeb.biologists.org | 128 | Medium |
| peerj.com | 80 | Medium (open access) |
| fishbull.noaa.gov | 69 | Medium (open access) |
| www.ncbi.nlm.nih.gov | 69 | Medium (open access) |
| academic.oup.com | 64 | Medium |
| www.journalofparasitology.org | 64 | Medium |
| spo.nwr.noaa.gov | 61 | Medium (open access) |
| www.scielo.br | 46 | Medium |
| www.revbiolmar.cl | 39 | Low (broken/hijacked) |
| www.bio.gc.ca | 38 | Medium |
| sfi.mnhn.fr | 36 | Medium |
| www.mnhn.fr | 36 | Medium |
| conbio.onlinelibrary.wiley.com | 34 | Medium |
| www.aiep.pl | 31 | Medium |
| www.labomar.ufc.br | 31 | Low (broken) |
| www.publish.csiro.au | 29 | Medium |


---

## Papers Without PDF URLs

**Total without URLs:** 20,503  
**Still need PDFs (not in Dropbox):** 20,503

These papers require:
1. Manual search on publisher websites
2. DOI lookup
3. Alternative sources (ResearchGate, author websites, etc.)

---

## Known Domain Issues

### Broken/Hijacked Domains

**revbiolmar.cl** (39 papers)
- Status: Domain hijacked - redirects to casino site
- Recommendation: Search for papers on institutional repositories

**www.labomar.ufc.br** (31 papers)
- Status: All links broken
- Recommendation: Report to shark-references.com

### Temporarily Down

**NOAA sites** (~130 papers)
- Status: Down due to government shutdown
- Domains: fishbull.noaa.gov, spo.nwr.noaa.gov
- Recommendation: Retry after shutdown ends

### Access Restricted

**Journal of Parasitology** (64 papers)
- Status: Limited institutional access
- Recommendation: Try alternative sources or ILL

---

## Next Steps

### Immediate Actions

1. **Retry timeout failures** (104 papers)
   - Use 60-second timeout
   - Command: `python3 scripts/retry_failed_downloads.py --status timeout --timeout 60`

2. **Manual downloads** (1,367 papers with known URLs)
   - Priority 1: PeerJ (remaining papers)
   - Priority 2: NOAA sites (after shutdown)
   - Priority 3: ScienceDirect (with rate limiting)
   - See: `docs/database/MANUAL_DOWNLOAD_GUIDE.md`

3. **Papers without URLs** (20,503 papers)
   - Search by DOI
   - Search by title on publisher sites
   - Check ResearchGate, Academia.edu

### Long-term Strategy

1. Report domain issues to shark-references.com
2. Set up automated retry for NOAA sites
3. Continue manual downloads in batches
4. Cross-reference with other library sources

---

**Files:**
- Detailed pending list: `outputs/pending_downloads_updated.csv`
- Download log: `logs/pdf_download_log.csv`
- Domain issues: `docs/database/DOMAIN_ISSUES_LOG.md`
