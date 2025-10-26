# Paper Acquisition Status Report

**Generated:** 2025-10-22
**Database:** 30,553 papers total

---

## Overview

This document tracks the progress of acquiring PDFs for all papers in the Shark-References database.

## Current Status

### Papers Acquired

| Source | Count | Percentage |
|--------|-------|------------|
| Previous downloads (Shark-References) | 3,268 | 10.7% |
| Dropbox collection | 423 | 1.4% |
| **Current Total** | **~3,720** | **~12.2%** |

### In Progress

| Task | Papers | Status | ETA |
|------|--------|--------|-----|
| Sci-Hub download | 11,858 | 3% complete (351/11,858) | ~10.5 hours |
| Expected success | ~10,080 | 85% success rate | - |

### Remaining After Sci-Hub

- **Papers without DOI:** 13,890
- **Papers not in Sci-Hub:** ~1,778 (15% of 11,858)

---

## Download Methods

### 1. Sci-Hub Download (ACTIVE)

**Status:** Running in background
**Target:** 11,858 papers with DOIs
**Progress:** 351/11,858 (3%)
**Success Rate:** 85%
**Expected Results:** ~10,080 successful downloads

**Configuration:**
- Mirror: https://sci-hub.st
- Rate limit: 3 seconds per request
- Output: `/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers/`
- Log: `logs/scihub_download_log.csv`

**Status Breakdown (from first 20 papers):**
- Success: 17 (85%)
- Not in Sci-Hub: 3 (15%)

### 2. Extracted DOI Papers

**Status:** Completed
**Papers:** 21 (found DOIs in pdf_url field)
**Success Rate:** 4.8% (1/21)

**Low Success Reasons:**
- Many IUCN Red List entries (not in Sci-Hub)
- PeerJ preprints (not in Sci-Hub)
- Malformed DOIs (e.g., `10.1111/j.1748-7692.2011.00542.x/pdf`)

**Log:** `logs/extracted_doi_download_log.csv`

### 3. Dropbox Collection

**Status:** Completed
**Papers:** 423 matched to database
**Match Rate:** 15.5% (423/2,727 PDFs scanned)

**Method:** PDF metadata extraction using `pdfinfo`
**Log:** `logs/dropbox_matches.csv`

### 4. ResearchGate & Academia.edu (FAILED)

**Status:** Authentication blocked
**Issue:** Anti-bot protection on both platforms
**Alternative:** Would require browser automation (Selenium/Playwright)

### 5. Open Access APIs (FAILED)

**Status:** Tested, not pursued
**Test Results:** 0/500 papers (0% success)
**Reason:** 91.6% had no OA sources, 8.4% returned 403 Forbidden

---

## Next Steps

### Immediate (After Sci-Hub Completes)

1. **Verify Sci-Hub results:** ~10,080 papers expected
2. **Count remaining:** Should have ~13,773 papers without PDFs

### Short-term

1. **DOI hunting for 13,890 papers without DOIs:**
   - Scrape journal websites for DOIs added after publication
   - Many papers may now have DOIs that weren't available initially
   - Once DOIs found, retry Sci-Hub download

2. **Retry failed Sci-Hub papers:**
   - ~1,778 papers marked "not_in_scihub"
   - Some may become available later
   - Consider trying different Sci-Hub mirrors

### Long-term

1. **Manual acquisition for remaining papers:**
   - Library requests
   - Author contact
   - University access
   - ResearchGate requests (manual)

---

## File Organization

### Output Directory Structure

```
/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers/
├── 2025/
│   ├── author_year_title_shortcode.pdf
│   └── ...
├── 2024/
├── 2023/
└── unknown_year/
```

### Logs

- `logs/scihub_download_log.csv` - Main Sci-Hub download progress
- `logs/scihub_full_download.log` - Terminal output with progress bar
- `logs/extracted_doi_download_log.csv` - Results from 21 extracted DOI papers
- `logs/dropbox_matches.csv` - Matched PDFs from Dropbox collection

### Data Files

- `outputs/papers_without_doi.csv` - 13,890 papers needing DOI hunting
- `outputs/papers_with_extracted_dois.csv` - 21 papers with DOIs found in pdf_url

---

## Technical Notes

### Sci-Hub PDF Extraction

The script uses BeautifulSoup to extract PDF links from Sci-Hub HTML responses:

```python
# Look for embed tag with PDF
embed_tag = soup.find('embed', {'type': 'application/pdf'})
if embed_tag and embed_tag.get('src'):
    pdf_url = embed_tag['src']

# Handle protocol-relative URLs
if pdf_url.startswith('//'):
    pdf_url = f"https:{pdf_url}"
```

**Critical Fix:** Original regex-based extraction failed (0% success). Switching to BeautifulSoup achieved 85% success rate.

### Russian Language Detection

Sci-Hub returns Russian text when papers are missing:
**"Статья отсутствует в базе"** = "The article is missing from the database"

### Rate Limiting

All downloads use 3-second delays between requests to be respectful to servers and avoid IP blocks.

---

## Success Metrics

### Current Achievement

- **Total papers:** 30,553
- **Papers acquired:** ~3,720 (12.2%)
- **In progress:** 11,858 (expected +10,080)
- **Projected total after Sci-Hub:** ~13,800 (45.2%)

### Expected Final Coverage

| Scenario | Papers | Percentage |
|----------|--------|------------|
| Best case (find all DOIs) | ~27,000 | ~88% |
| Realistic (70% DOI success) | ~23,000 | ~75% |
| Minimum (current + Sci-Hub only) | ~13,800 | ~45% |

---

## Monitoring Commands

### Check Sci-Hub progress
```bash
tail -30 logs/scihub_full_download.log
```

### View success rate
```bash
python3 << 'EOF'
import pandas as pd
log = pd.read_csv("logs/scihub_download_log.csv")
print(f"Processed: {len(log):,}")
print(f"Success: {(log['status']=='success').sum():,}")
print(f"Rate: {(log['status']=='success').sum()/len(log)*100:.1f}%")
EOF
```

### Count acquired PDFs
```bash
find "/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers/" -name "*.pdf" | wc -l
```

---

## Legal Notice

All downloads via Sci-Hub are for **educational and research purposes only**. Users must comply with local copyright laws and institutional policies.

---

*Last updated: 2025-10-22 (Sci-Hub download in progress)*
