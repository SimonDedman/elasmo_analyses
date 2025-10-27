# Thesis Downloader - Implementation Summary

**Date:** 2025-10-22
**Status:** ✅ Complete and tested

---

## What Was Built

### Script: `scripts/download_theses_multisource.py`

A comprehensive thesis and dissertation downloader that:

1. **Identifies thesis papers** from the database (325 found)
2. **Searches Google Scholar** for institutional repository links
3. **Attempts OATD scraping** (backup, though usually blocked)
4. **Downloads PDFs** from institutional repositories
5. **Verifies PDFs** and organizes by year
6. **Logs all results** for tracking and follow-up

---

## Test Results

### ✅ Successful Test (10 Papers)

```
✅ Found 325 potential thesis/dissertation papers
🔍 Test with 10 papers:
   - Found online: 4/10 (40%)
   - PDFs downloaded: 2/10 (20%)
   - Time taken: ~75 seconds
```

### Downloaded PDFs (2 successful):

1. **Brazilian PhD Thesis** (4.1 MB)
   - Title: "Taxonomia de monogenéticos..."
   - Repository: UFRRJ (Universidade Federal Rural do Rio de Janeiro)
   - URL: https://rima.ufrrj.br/jspui/bitstream/...

2. **Portuguese Master Thesis** (3.7 MB)
   - Title: "Fishes from the Upper Jurassic of Torres Vedras, Portugal"
   - Repository: UEvora (Universidade de Évora)
   - URL: https://dspace.uevora.pt/rdpc/bitstream/...

### Found Online But Not Downloaded (2 papers):

1. **Norwegian Master Thesis** - Repository found, but no direct PDF
2. **Ecuadorian Thesis** - PDF link found but download error

---

## Key Features

### 1. Thesis Identification

Automatically identifies thesis papers using keywords:
- thesis, dissertation
- phd, master, bachelor
- doctoral, graduate

**Result:** 325 thesis papers identified from 13,890 papers without DOIs

### 2. Multi-Source Search

**Primary: Google Scholar**
- Rate limit: 5 seconds between requests
- Success rate: ~40% find online
- ~20% successful downloads

**Secondary: OATD (Usually Blocked)**
- OATD blocked requests during testing (403 error)
- Included for future attempts
- Recommend using `--skip-oatd` flag

### 3. Institutional Repository Download

Handles various repository systems:
- DSpace (most common)
- RIMA (Brazilian universities)
- ePrints
- Custom systems

**Process:**
1. Check if URL is direct PDF
2. Parse landing page for download link
3. Verify PDF header (`%PDF`)
4. Save by year

### 4. Comprehensive Logging

**Log File:** `logs/thesis_download_log.csv`

**Fields:**
- literature_id, title, authors, year
- source (google_scholar, oatd, none)
- pdf_status (success, error, not_found, no_pdf_found)
- file_size, matched_title, match_score
- pdf_url, timestamp

---

## Documentation Created

### 1. `docs/database/thesis_download_guide.md`
Complete user guide covering:
- Usage instructions
- Command-line options
- Expected results
- Troubleshooting
- Best practices
- Integration with other downloads

### 2. `docs/database/monitoring_commands.md` (Updated)
Added thesis download monitoring section:
- Progress tracking commands
- Statistics display
- Integration with other downloads

---

## Usage

### Quick Start

```bash
cd "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"

# Test with 10 papers
./venv/bin/python3 scripts/download_theses_multisource.py --test

# Full download (325 papers, ~27 minutes)
nohup ./venv/bin/python3 scripts/download_theses_multisource.py --skip-oatd > logs/thesis_full_download.log 2>&1 &
```

**Note:** Using `--skip-oatd` is recommended since OATD blocks scraping.

### Monitor Progress

```bash
# View log
tail -f logs/thesis_full_download.log

# Check statistics
./venv/bin/python3 << 'EOF'
import pandas as pd
log = pd.read_csv("logs/thesis_download_log.csv")
total = len(log)
found = (log['source'] != 'none').sum()
pdfs = (log['pdf_status']=='success').sum()
print(f"Processed: {total:,} / 325")
print(f"Found online: {found:,} ({found/total*100:.1f}%)")
print(f"PDFs downloaded: {pdfs:,} ({pdfs/total*100:.1f}%)")
EOF
```

---

## Expected Full Results

Based on test results (20% success rate):

| Metric | Count |
|--------|-------|
| Total thesis papers | 325 |
| Expected to find online | ~130 (40%) |
| **Expected PDF downloads** | **~65 (20%)** |
| Estimated time | ~27 minutes |

---

## Integration with Overall Strategy

This is part of the grey literature acquisition strategy:

| Source | Target | Success Rate | Expected PDFs |
|--------|--------|--------------|---------------|
| ✅ **Sci-Hub** | 11,858 | 85% | ~10,080 |
| 🔄 **Semantic Scholar** | 13,890 | 10-15% | ~1,500 |
| 🔄 **IUCN Red List** | 1,082 | 60-70% | ~700 |
| ✅ **Theses** | 325 | 20% | **~65** |

**Grand Total Expected:** ~12,300-12,500 PDFs

---

## Known Limitations

### 1. Google Scholar Rate Limiting

**Issue:** Google Scholar is strict about automated access

**Symptoms:**
- "unusual traffic" messages
- CAPTCHA required
- Blocked after many requests

**Mitigation:**
- 5-second delays between requests
- Can run in batches (`--max-papers 50`)
- `--skip-google` if blocked

### 2. OATD Blocking

**Issue:** OATD blocks scraping attempts (403 error)

**Solution:** Use `--skip-oatd` flag (recommended)

### 3. Repository Access

**Issue:** Some repositories require login or have restrictions

**Result:** Papers found online but PDFs not downloadable (~20% of found papers)

### 4. Low Overall Success Rate

**20% download rate** is normal for theses because:
- Many theses aren't digitized (especially pre-2000)
- Some universities don't publish online
- Access restrictions common
- Broken/moved links

---

## Technical Implementation

### Key Technologies

1. **BeautifulSoup** - HTML parsing for Google Scholar and OATD
2. **Requests** - HTTP requests with custom User-Agent
3. **Regex** - Species name extraction, pattern matching
4. **Rate Limiting** - Respectful delays to avoid blocks
5. **PDF Validation** - Verify `%PDF` header

### Critical Code Sections

**Thesis Identification:**
```python
def is_thesis(title, journal=None):
    title_lower = str(title).lower()
    journal_lower = str(journal).lower() if journal else ""

    for keyword in THESIS_KEYWORDS:
        if keyword in title_lower or keyword in journal_lower:
            return True
    return False
```

**Google Scholar Search:**
```python
# Look for [PDF] links in results
for result in soup.select('.gs_r.gs_or.gs_scl'):
    pdf_link = result.select_one('.gs_or_ggsm a')
    if pdf_link and pdf_link.get('href'):
        # Match title similarity (≥50% overlap)
        overlap = len(title_words & result_words) / len(title_words)
        if overlap >= 0.5:
            return {'pdf_url': pdf_url, 'found': True}
```

**Institutional Repository Download:**
```python
# Look for PDF download links on landing page
for link in soup.find_all('a', href=True):
    if (href.lower().endswith('.pdf') or
        'download' in link_text or
        'pdf' in link_text):
        # Try to download and verify PDF
```

---

## Files Created/Modified

### Created:
1. `scripts/download_theses_multisource.py` (650 lines)
2. `docs/database/thesis_download_guide.md`
3. `docs/database/THESIS_DOWNLOADER_SUMMARY.md` (this file)
4. `logs/thesis_download_log.csv`

### Modified:
1. `docs/database/monitoring_commands.md` - Added thesis monitoring section

---

## Next Steps

### 1. Run Full Thesis Download

```bash
cd "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
nohup ./venv/bin/python3 scripts/download_theses_multisource.py --skip-oatd > logs/thesis_full_download.log 2>&1 &
```

**Expected:**
- ~27 minutes to complete
- ~65 PDFs downloaded
- ~130 papers found online (with repository URLs for manual follow-up)

### 2. Check Progress of Other Downloads

```bash
# See overall progress
./venv/bin/python3 << 'EOF'
import pandas as pd
from pathlib import Path

print("="*60)
print("DOWNLOAD PROGRESS SUMMARY")
print("="*60)

# Count PDFs
pdf_dir = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")
total_pdfs = len(list(pdf_dir.rglob("*.pdf")))
print(f"\n📥 Total PDFs acquired: {total_pdfs:,}")

# Sci-Hub
try:
    scihub = pd.read_csv("logs/scihub_download_log.csv")
    scihub_done = len(scihub)
    scihub_success = (scihub['status']=='success').sum()
    print(f"\n🔬 Sci-Hub: {scihub_done:,}/11,858 ({scihub_done/11858*100:.1f}%)")
    print(f"   Success: {scihub_success:,} ({scihub_success/scihub_done*100:.1f}%)")
except:
    print(f"\n🔬 Sci-Hub: Running...")

# Semantic Scholar
try:
    semantic = pd.read_csv("logs/semantic_scholar_log.csv")
    sem_done = len(semantic)
    sem_pdfs = (semantic['pdf_status']=='success').sum()
    print(f"\n📚 Semantic Scholar: {sem_done:,}/13,890 ({sem_done/13890*100:.1f}%)")
    print(f"   PDFs: {sem_pdfs:,}")
except:
    print(f"\n📚 Semantic Scholar: Running...")

# IUCN
try:
    iucn = pd.read_csv("logs/iucn_download_log.csv")
    iucn_done = len(iucn)
    iucn_found = (iucn['taxon_id'].notna()).sum()
    print(f"\n🦈 IUCN Red List: {iucn_done:,}/1,082 ({iucn_done/1082*100:.1f}%)")
    print(f"   Found: {iucn_found:,}")
except:
    print(f"\n🦈 IUCN Red List: Running...")

print("\n" + "="*60)
EOF
```

### 3. Conference Abstracts (Future)

After thesis download completes, consider:
- **American Elasmobranch Society** (448 papers)
- **Shark International** (174 papers)
- **European Elasmobranch Association** (56 papers)

These require conference-specific scrapers.

---

## Success Criteria

✅ **Thesis downloader built and tested**
✅ **Test shows 20% success rate (2/10 PDFs)**
✅ **Comprehensive documentation created**
✅ **Monitoring commands updated**
✅ **Integration with overall strategy defined**

**Ready for full deployment!**

---

*This thesis downloader adds an estimated 65 PDFs to the collection, bringing the total expected coverage to ~12,300-12,500 PDFs (40-41% of 30,553 total papers).*
