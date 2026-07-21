# Thesis & Dissertation Download Guide

**Script:** `scripts/download_theses_multisource.py`
**Created:** 2025-10-22
**Target:** 325 thesis/dissertation papers from papers without DOIs

---

## Overview

This script searches for and downloads thesis and dissertation PDFs using multiple online sources. Since OATD (Open Access Theses and Dissertations) doesn't provide a public API, the script uses:

1. **Google Scholar** (primary) - Best coverage, but strict rate limiting
2. **OATD web scraping** (secondary) - No API, may block requests
3. **Institutional repository downloads** - Direct PDF extraction

---

## Thesis Identification

The script identifies thesis papers using keyword matching in title or journal fields:

**Keywords:**
- thesis, dissertation
- phd, ph.d, ph d
- master, msc, m.sc
- bachelor, bsc, b.sc
- doctoral, doctorate
- graduate thesis, undergraduate thesis, honours thesis

**Results:** 325 papers identified from 13,890 papers without DOIs

---

## Usage

### Test Mode (Recommended First)

Test with 10 papers to verify functionality:

```bash
cd "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
./venv/bin/python3 scripts/download_theses_multisource.py --test
```

**Expected Results:**
- ~40% found online (4/10)
- ~20% successfully downloaded (2/10)

### Full Download

Process all 325 thesis papers:

```bash
cd "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
nohup ./venv/bin/python3 scripts/download_theses_multisource.py > logs/thesis_full_download.log 2>&1 &
```

**Estimated Time:** ~27 minutes (325 papers × 5 second delay)

### Skip Google Scholar (If Blocked)

If you get blocked by Google Scholar, skip it:

```bash
./venv/bin/python3 scripts/download_theses_multisource.py --skip-google
```

### Skip OATD (If Blocked)

OATD often blocks scraping attempts (403 error):

```bash
./venv/bin/python3 scripts/download_theses_multisource.py --skip-oatd
```

**Note:** OATD blocked during testing, so using `--skip-oatd` is recommended.

### Process Limited Number

Process first 50 papers only:

```bash
./venv/bin/python3 scripts/download_theses_multisource.py --max-papers 50
```

---

## How It Works

### 1. Google Scholar Search

**Rate Limit:** 5 seconds between requests
**Success Rate:** ~40% (finds paper online)
**Download Rate:** ~20% (successfully downloads PDF)

**Process:**
1. Search Google Scholar by title + first author
2. Look for `[PDF]` links in results
3. Match title similarity (≥50% word overlap)
4. Extract PDF URL from institutional repository

**Example Results:**
- ✅ UFRRJ (Brazil) - `https://rima.ufrrj.br/jspui/bitstream/...`
- ✅ UEvora (Portugal) - `https://dspace.uevora.pt/rdpc/bitstream/...`
- ❌ UPSE (Ecuador) - PDF found but download error

### 2. OATD Web Scraping

**Rate Limit:** 2 seconds between requests
**Status:** Usually blocked (403)

**Note:** OATD blocked requests during testing. This source is included for future attempts but is not reliable.

### 3. Institutional Repository Download

Once a repository URL is found, the script:

1. Checks if URL is direct PDF (ends with `.pdf`)
2. If not, parses landing page for PDF download link
3. Looks for keywords: "download", "pdf", "fulltext"
4. Verifies PDF header (`%PDF`)
5. Saves to output directory by year

**Common Repository Types:**
- DSpace (most universities)
- RIMA (Brazilian institutions)
- ePrints
- Custom systems

---

## Output

### Directory Structure

```
outputs/SharkPapers/
├── 2019/
│   └── Flores_Estudio_poblacional_2019.pdf
├── 2022/
│   ├── Chero_Taxonomia_de_2022.pdf
│   └── Costa_Fishes_from_the_2022.pdf
└── unknown_year/
    └── ...
```

### Log File

**Location:** `logs/thesis_download_log.csv`

**Fields:**
- `literature_id` - Database ID
- `title` - Paper title
- `authors` - Authors
- `year` - Publication year
- `journal` - Source (e.g., "PhD Thesis", "Master Thesis")
- `source` - Where found ("google_scholar", "oatd", "none")
- `pdf_status` - Download status ("success", "error", "not_found", "no_pdf_found")
- `file_size` - PDF file size in bytes
- `matched_title` - Title from search result
- `match_score` - Title similarity (0-1)
- `pdf_url` - Direct PDF URL
- `timestamp` - When processed

---

## Expected Results

Based on test results (10 papers):

| Metric | Count | Percentage |
|--------|-------|------------|
| **Total thesis papers** | 325 | 100% |
| **Found online** | ~130 | ~40% |
| **PDFs downloaded** | ~65 | ~20% |

**Projected Downloads:** ~65 thesis PDFs

---

## Rate Limiting & Blocking

### Google Scholar

**Strict Rate Limiting** - May block if too many requests

**Symptoms:**
- "unusual traffic" message
- CAPTCHA required
- HTTP 429 or 403 errors

**Solutions:**
- Use 5-second delays (implemented)
- Run in small batches (`--max-papers 50`)
- Wait 24 hours if blocked
- Use `--skip-google` flag

### OATD

**Often Blocks Scraping** - 403 Forbidden

**Solution:**
- Use `--skip-oatd` flag (recommended)
- Focus on Google Scholar only
- Consider manual searches for critical theses

---

## Monitoring Progress

See `docs/database/monitoring_commands.md` for detailed monitoring commands.

**Quick Check:**
```bash
cd "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
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

## Troubleshooting

### Google Scholar Blocked

**Error:** "unusual traffic" or CAPTCHA

**Solution:**
```bash
# Run with --skip-google
./venv/bin/python3 scripts/download_theses_multisource.py --skip-google
# Or wait 24 hours and retry
```

### OATD 403 Error

**Error:** `⚠️ OATD blocked request (403)`

**Solution:**
```bash
# OATD blocks by default, use --skip-oatd
./venv/bin/python3 scripts/download_theses_multisource.py --skip-oatd
```

### No PDFs Found

**Issue:** Papers found online but PDFs not downloadable

**Reasons:**
- Institutional repository requires login
- PDF behind paywall
- Broken/moved links
- Repository uses complex access system

**Manual Follow-up:**
Check `logs/thesis_download_log.csv` for:
- `pdf_status == 'no_pdf_found'` - Repository URL in log, manually visit
- `pdf_status == 'error'` - Check error details

### Low Success Rate

**Expected:** ~20% download rate for theses is normal

**Reasons:**
- Many theses aren't digitized
- Older theses (pre-2000) rarely available
- Some universities don't publish online
- Access restrictions

---

## Best Practices

1. **Start with Test Mode**
   ```bash
   ./venv/bin/python3 scripts/download_theses_multisource.py --test
   ```

2. **Skip OATD** (they block scraping)
   ```bash
   ./venv/bin/python3 scripts/download_theses_multisource.py --skip-oatd
   ```

3. **Run in Batches** (avoid Google Scholar blocks)
   ```bash
   ./venv/bin/python3 scripts/download_theses_multisource.py --max-papers 50
   # Wait 1 hour
   # Process next batch by modifying script to skip processed papers
   ```

4. **Monitor Progress**
   ```bash
   tail -f logs/thesis_full_download.log
   ```

5. **Check for Blocks**
   - If Google Scholar blocks, wait 24 hours
   - Consider VPN or different IP

---

## Integration with Other Downloads

This is part of the grey literature acquisition strategy:

| Source | Papers | Success Rate | PDFs |
|--------|--------|--------------|------|
| **Sci-Hub** | 11,858 | 85% | ~10,080 |
| **Semantic Scholar** | 13,890 | 10-15% | ~1,500 |
| **IUCN Red List** | 1,082 | 60-70% | ~700 |
| **Theses** | 325 | 20% | ~65 |

**Total Expected:** ~12,300-12,500 PDFs

---

## Future Improvements

1. **Add more institutional repositories**
   - Identify common thesis repositories
   - Build repository-specific scrapers

2. **ProQuest Integration**
   - If institutional access available
   - Much better coverage than OATD

3. **ResearchGate/Academia.edu**
   - Many researchers upload their theses
   - Requires login and browser automation

4. **Email Authors**
   - For critical missing theses
   - Many authors happy to share

---

## See Also

- `docs/database/grey_literature_acquisition_strategy.md` - Overall strategy
- `docs/database/monitoring_commands.md` - Progress tracking
- `scripts/search_semantic_scholar.py` - Alternative grey literature source
- `scripts/download_iucn_assessments.py` - IUCN assessment downloader
