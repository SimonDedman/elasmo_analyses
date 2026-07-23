# PDF Storage Analysis for SharkPapers Download

**Date:** 2025-10-21
**Purpose:** Estimate storage requirements for downloading ~10,050 PDFs from shark-references database

---

## Executive Summary

**Recommendation:** ✅ **PROCEED WITH DOWNLOAD**

- **Estimated storage required:** 20-25 GB for 10,050 papers
- **Available space at target:** 301 GB
- **Safety margin:** 12-15x available capacity
- **Risk:** 🟢 LOW - Ample storage available

---

## Existing Library Analysis

### Source Data
- **Location:** `/home/simon/Dropbox/Galway/Papers/`
- **Sample size:** 2,727 PDFs
- **Total size:** 6.72 GB

### Statistics

| Metric | Value | Notes |
|--------|-------|-------|
| **Total PDFs** | 2,727 | Existing collection |
| **Total size** | 6.72 GB | ~6,877 MB |
| **Average size** | 2.52 MB | Mean (affected by outliers) |
| **Median size** | 1.02 MB | Typical paper size |

**Key observation:** Median (1.02 MB) is much lower than mean (2.52 MB), indicating a right-skewed distribution with some large outliers pulling the average up.

---

## Size Distribution

### Overall Distribution
```
Median:    1.02 MB  ←  50% of papers
Average:   2.52 MB  ←  includes outlier effect
```

### Outliers Identified

#### Very Large Files (>50 MB)
6 files found:

| Size | File |
|------|------|
| 84.69 MB | Zuur.2009.Zero Truncated Inflated Models Count Data.pdf |
| 81.14 MB | Dedman.2003.Elasmobranches of the East Solent.pdf |
| 77.20 MB | ICES WGCSE Report 2014.pdf |
| 71.18 MB | NOAA.2006.HMSFMP.pdf |
| 65.21 MB | Carrier.etal.2019.Emerg tech app field laboratory.pdf |
| 57.56 MB | ICESWGEF.2020.Fullreport.pdf |

**Analysis:** These are primarily technical reports, regulatory documents, and comprehensive textbooks - not typical research papers.

#### Size Brackets

| Range | Count | % of Total |
|-------|-------|------------|
| **<100 KB** | 45 | 1.6% |
| **100 KB - 5 MB** | 2,408 | 88.3% ← **MAJORITY** |
| **5-10 MB** | 191 | 7.0% |
| **10-20 MB** | 79 | 2.9% |
| **20-50 MB** | 38 | 1.4% |
| **>50 MB** | 6 | 0.2% |

**Key finding:** 88.3% of papers fall in the typical research paper range (100 KB - 5 MB).

---

## Storage Projections for 10,050 Papers

### Scenario Analysis

| Estimate Type | Calculation | Total Storage |
|---------------|-------------|---------------|
| **Optimistic** (median) | 10,050 × 1.02 MB | **10.0 GB** |
| **Conservative** (mean) | 10,050 × 2.52 MB | **24.7 GB** |
| **Recommended** (adjusted) | 10,050 × 2.0 MB | **~20 GB** |

### Recommended Estimate: 20 GB

**Rationale:**
- Shark-references papers are primarily research articles (not reports/books)
- Expected distribution similar to existing library
- Some large papers (multi-figure, supplementary materials)
- Account for ~10% overhead
- **Formula:** 10,050 papers × 2.0 MB/paper = 20,100 MB ≈ 20 GB

---

## Target Storage Capacity

### Destination
- **Path:** `/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers/`
- **Volume:** `/media/simon/data/`

### Available Space
- **Total capacity:** 1.7 TB
- **Currently used:** 82% (1.4 TB)
- **Available:** 301 GB

### Capacity Analysis

| Item | Size | % of Available |
|------|------|----------------|
| **Required (recommended)** | 20 GB | 6.6% |
| **Required (conservative)** | 25 GB | 8.3% |
| **Available** | 301 GB | 100% |
| **Remaining after download** | 276-281 GB | 91-93% |

✅ **Verdict:** Ample storage available (12-15x required capacity)

---

## Outlier Mitigation Strategy

### Expected Outliers in Shark-References

**Potential large files:**
- Species identification guides (illustrated)
- Taxonomic revisions (high-resolution plates)
- Atlas documents (maps, distribution charts)
- Review papers (extensive figures/tables)

**Expected rate:** ~5-10% of papers >5 MB (similar to current library)

### Handling Strategy

**Option 1: Download All (Recommended)**
- Download all 10,050 PDFs without filtering
- Monitor download progress for failures
- Re-attempt failed downloads separately
- **Storage impact:** Minimal (well within capacity)

**Option 2: Size Filtering (Not Recommended)**
- Skip PDFs >50 MB during download
- Review and selectively download large files
- **Downside:** May miss important review papers/atlases

**Recommendation:** Option 1 - storage is not a constraint

---

## Download Estimates

### Based on shark-references_complete CSV

From analysis of `shark_references_complete_2025_to_1950_20251021.csv`:
- **Total papers:** 30,523
- **Papers with PDF links:** ~10,050 (estimated from `pdf_url` field)
- **Papers without PDFs:** ~20,473 (older papers, paywalled, etc.)

### Download Timeline Estimates

**Assumptions:**
- Average download speed: 5 Mbps (moderate connection)
- Average PDF size: 2 MB
- Total data: 20 GB

| Scenario | Speed | Time for 20 GB |
|----------|-------|----------------|
| **Fast connection** | 50 Mbps | ~53 minutes |
| **Moderate connection** | 10 Mbps | ~4.4 hours |
| **Slow connection** | 5 Mbps | ~8.9 hours |

**Additional factors:**
- Rate limiting (polite scraping: 1-2 requests/second)
- Failed downloads / retries
- Server response time

**Realistic estimate:** 6-12 hours for complete download (including rate limiting, retries)

---

## Comparison with Existing Library

### Growth Projection

| Metric | Current | After Download | Growth |
|--------|---------|----------------|--------|
| **PDF count** | 2,727 | 12,777 | +368% |
| **Storage** | 6.72 GB | ~27 GB | +302% |
| **Average size** | 2.52 MB | ~2.1 MB | -16% |

**Note:** Expected average size slightly lower because shark-references papers are research articles (not regulatory reports/textbooks).

---

## Risk Assessment

### Storage Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Insufficient space** | 🟢 Very Low | High | 301 GB available vs 20 GB needed |
| **Larger than expected** | 🟡 Low | Low | Even at 50 GB, still ample space |
| **Download failures** | 🟡 Medium | Low | Retry mechanism + logging |
| **Corrupted files** | 🟡 Medium | Low | Verify file sizes, re-download if needed |

**Overall risk:** 🟢 **LOW** - No significant storage or capacity concerns

---

## Recommendations

### 1. Pre-Download Setup

```bash
# Create target directory
mkdir -p "/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers"

# Create subdirectories for organization
mkdir -p "/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers/by_year"
mkdir -p "/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers/failed_downloads"
mkdir -p "/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers/logs"
```

### 2. Download Strategy

**Recommended approach:**
- Process papers year-by-year (similar to bulk CSV download)
- Save PDFs with unique identifiers: `{literature_id}_{year}_{first_author}.pdf`
- Log successful downloads
- Track failed downloads for retry
- Generate download summary report

### 3. Quality Control

**Post-download verification:**
- Verify file count matches expected
- Check for 0-byte files (failed downloads)
- Spot-check random PDFs for corruption
- Generate size distribution histogram

### 4. Monitoring

**Track during download:**
- Progress: papers downloaded / total
- Success rate: successful / attempted
- Storage used: running total
- Estimated time remaining
- Failed downloads list

---

## Storage Allocation Plan

### Breakdown by Component

| Component | Estimated Size | Notes |
|-----------|----------------|-------|
| **PDF files** | 20 GB | 10,050 papers × 2 MB average |
| **Download logs** | 10 MB | CSV tracking success/failure |
| **Failed retries** | 1 GB | ~5% retry buffer |
| **Metadata cache** | 50 MB | JSON/CSV metadata |
| **Total** | **~21 GB** | |
| **Available** | **301 GB** | |
| **Remaining** | **280 GB** | 93% free after download |

---

## Next Steps

### Immediate Actions

1. ✅ **Storage analysis complete** - 20 GB required, 301 GB available
2. ⏳ **Create download script** - `scripts/download_shark_references_pdfs.py`
3. ⏳ **Set up directory structure** - Target location + subdirectories
4. ⏳ **Implement download queue** - Year-by-year processing
5. ⏳ **Add retry mechanism** - Handle failed downloads
6. ⏳ **Generate download report** - Success rate, storage used, failed list

### Integration with Extraction Pipeline

**Parallel workflows:**
- **Workflow A (NOW):** Extract metadata from CSV → populate SQL database (TIER 1-3 fields)
- **Workflow B (CONCURRENT):** Download PDFs → save to SharkPapers directory
- **Workflow C (LATER):** Extract full-text from PDFs → populate TIER 4 fields (author affiliations, subtechniques)

**Benefits:**
- Can start metadata extraction immediately
- PDF download runs in background (6-12 hours)
- Full-text extraction added after PDF download completes

---

## Summary Statistics

### Existing Library
```
Location:  /home/simon/Dropbox/Galway/Papers/
PDFs:      2,727 files
Size:      6.72 GB
Average:   2.52 MB (mean) / 1.02 MB (median)
Outliers:  6 files >50 MB, 117 files >10 MB
```

### Projection for Download
```
Target:    /media/simon/data/.../SharkPapers/
PDFs:      10,050 files
Size:      ~20 GB (recommended estimate)
Range:     10-25 GB (optimistic-conservative)
Available: 301 GB (15x required capacity)
```

### Verdict
✅ **APPROVED FOR DOWNLOAD**
- Storage: ample capacity
- Timeline: 6-12 hours
- Risk: low

---

**Analysis completed:** 2025-10-21
**Recommendation:** Proceed with PDF download alongside metadata extraction
**Storage constraint:** None (301 GB available vs 20 GB required)
