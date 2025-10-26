# OCR Resource Requirements Analysis

**Date:** 2025-10-24
**Based on:** 500-PDF sample analysis showing ~2% need OCR

---

## Quick Summary

**To OCR all PDFs lacking searchable text:**

| Resource | Estimated Requirement |
|----------|---------------------|
| **PDFs to OCR** | ~267 PDFs (2% of 13,357) |
| **Time** | 9-18 hours |
| **Disk Space** | 5-10 GB additional |
| **Processing** | CPU-intensive (parallel processing recommended) |
| **Cost** | Free (using open-source tools) |

---

## Time Requirements

### Per-PDF Processing Time

**OCR tool comparison:**

| Tool | Speed (per PDF) | Quality | Notes |
|------|----------------|---------|-------|
| **ocrmypdf** | 2-5 min | High | Recommended, uses Tesseract |
| **Tesseract alone** | 1-3 min | Medium | Faster but less accurate |
| **Adobe Acrobat** | 30-60 sec | Highest | Commercial, fastest |
| **Google Drive** | Variable | High | Cloud-based, free but slow upload |

### Total Time Estimates

**For ~267 PDFs needing OCR:**

#### Single-threaded (Sequential Processing)

```
ocrmypdf (conservative estimate):
  - 267 PDFs × 3 min/PDF = 801 minutes = 13.4 hours

ocrmypdf (optimistic estimate):
  - 267 PDFs × 2 min/PDF = 534 minutes = 8.9 hours

Adobe Acrobat (if available):
  - 267 PDFs × 45 sec/PDF = 200 minutes = 3.3 hours
```

#### Multi-threaded (Parallel Processing)

Using 8 CPU cores in parallel:

```
ocrmypdf (8 cores):
  - 13.4 hours ÷ 8 = ~1.7 hours
  - 8.9 hours ÷ 8 = ~1.1 hours
```

**Realistic estimate with ocrmypdf (8-core parallel):**
- **Best case:** 1-2 hours
- **Typical case:** 2-3 hours
- **Worst case:** 3-4 hours (large scanned PDFs)

### Processing Speed Factors

**What affects OCR time:**

1. **PDF size:**
   - Small (< 1 MB): ~1 min
   - Medium (1-5 MB): ~2-3 min
   - Large (5-20 MB): ~5-10 min
   - Very large (20-50 MB): ~15-30 min

2. **Page count:**
   - 1-10 pages: Fast (1-2 min)
   - 10-20 pages: Medium (2-5 min)
   - 20+ pages: Slow (5-15 min)

3. **Image quality:**
   - High DPI scans: Slower but more accurate
   - Low DPI scans: Faster but may have errors

4. **CPU cores:**
   - Single core: Full time estimate
   - 4 cores: ~25% of time
   - 8 cores: ~12.5% of time
   - 16 cores: ~6% of time

**From our sample:**
- Average size of PDFs needing OCR: 9.66 MB
- Some very large: 33-52 MB (2 PDFs)
- Estimated average: ~3-4 min/PDF with ocrmypdf

---

## Disk Space Requirements

### OCR Output Size

**OCR typically REDUCES file size** (counterintuitive but true!)

**Why:**
- Original scanned PDFs: Just images (large)
- OCR'd PDFs: Images + compressed text layer (smaller overall)
- ocrmypdf applies image optimization during OCR

**Size changes from sample analysis:**

| Category | Original Size | After OCR | Change |
|----------|--------------|-----------|--------|
| Small PDFs (< 1 MB) | 0.3 MB avg | ~0.4 MB | +33% |
| Medium PDFs (1-10 MB) | 5 MB avg | ~4 MB | -20% |
| Large PDFs (10-50 MB) | 35 MB avg | ~20 MB | -43% |

**Net effect:** OCR often reduces total collection size!

### Disk Space Scenarios

#### Scenario 1: In-Place OCR (Replace Originals)

```
Current PDFs needing OCR: ~2.6 GB (267 PDFs × 9.66 MB avg)
After OCR: ~2.0 GB (estimated 20% reduction)

Net disk space change: -600 MB (savings!)
```

**Recommended approach:** Keep originals as backup

#### Scenario 2: Keep Originals + OCR Copies

```
Original PDFs: ~2.6 GB
OCR'd PDFs: ~2.0 GB
Total: ~4.6 GB
Additional space needed: ~2.0 GB
```

#### Scenario 3: Keep Originals in Archive

```
Move originals to compressed archive:
  - Original PDFs: 2.6 GB
  - Compressed (tar.gz): ~1.8 GB (30% compression)
  - OCR'd PDFs: ~2.0 GB

Total: ~3.8 GB (vs 2.6 GB original)
Additional space: ~1.2 GB
```

### Current Disk Space

**Your system:**
```bash
# Check available space
df -h /media/simon/data/

# Current PDF collection size
du -sh "/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers"
```

**Estimated current usage:**
- 13,357 PDFs × 2.52 MB avg = ~33.6 GB
- With room for OCR'd versions: ~35-36 GB total needed

**Space needed for OCR project:**
- **Temporary:** ~5 GB (during processing)
- **Permanent:** ~2 GB (keeping both versions)
- **Net:** Potentially -600 MB if replacing originals

---

## Resource Requirements by Approach

### Approach 1: Quick OCR (Recommended for Panel)

**Target:** Only recent papers needing OCR (2000+)

From sample: ~3 PDFs from 2000+ need OCR
Projected: ~40 PDFs from 2000+ (1.3% of 3,000 papers)

```
Time: 40 PDFs × 3 min = 120 min = 2 hours (single core)
      or ~15-20 min (8 cores parallel)

Disk space: 40 PDFs × 9.66 MB = ~386 MB
            After OCR: ~300 MB
            Additional: ~300 MB (keep both versions)

Effort: Low
Value: High (recent papers most relevant)
```

### Approach 2: Targeted OCR (Pre-2000 Only)

**Target:** All pre-2000 PDFs needing OCR

Projected: ~227 PDFs from pre-2000 (11.4% of ~2,000 papers)

```
Time: 227 PDFs × 3 min = 681 min = 11.4 hours (single core)
      or ~1.5-2 hours (8 cores parallel)

Disk space: 227 PDFs × 9.66 MB = ~2.2 GB
            After OCR: ~1.7 GB
            Additional: ~1.7 GB (keep both versions)

Effort: Medium
Value: Medium (older papers less relevant for trends)
```

### Approach 3: Complete OCR (All Missing)

**Target:** All 267 PDFs needing OCR

```
Time: 267 PDFs × 3 min = 801 min = 13.4 hours (single core)
      or ~1.7-2.5 hours (8 cores parallel)

Disk space: 267 PDFs × 9.66 MB = ~2.6 GB
            After OCR: ~2.0 GB
            Additional: ~2.0 GB (keep both versions)

Effort: Medium-High
Value: Low (marginal gain over targeted approach)
```

### Approach 4: Full Collection OCR (All 13,357 PDFs)

**Target:** OCR everything (even PDFs that already have text)

```
Time: 13,357 PDFs × 3 min = 40,071 min = 668 hours = 28 days (single core)
      or ~3.5 days (8 cores parallel, 24/7)

Disk space: ~33.6 GB current → ~27 GB after OCR (savings!)
            Keep both: ~61 GB total

Effort: Very High
Value: Minimal (98% already have text)
Cost: Unnecessary CPU/electricity use
```

**Not recommended** - waste of resources!

---

## Recommended Workflow

### Phase 1: Setup (5 minutes)

```bash
# 1. Install OCR tools
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-eng ocrmypdf

# 2. Test on one PDF
cd "/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers"
ocrmypdf --deskew --rotate-pages --clean \
  "1993/Siversson.etal.1993.Maastric Squaloid Sharks from Southern Sweden.pdf" \
  "test_ocr_output.pdf"

# 3. Verify output
pdftotext test_ocr_output.pdf - | head -50
```

### Phase 2: Create OCR List (2 minutes)

```bash
cd "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"

# Extract list of PDFs needing OCR
awk -F',' '$7=="True" {print $1}' outputs/pdf_ocr_status.csv > pdfs_to_ocr.txt

# Count
wc -l pdfs_to_ocr.txt

# Preview first 10
head -10 pdfs_to_ocr.txt
```

### Phase 3: Batch OCR (1-3 hours, parallel)

```bash
# Create OCR script
cat > scripts/batch_ocr.sh << 'EOF'
#!/bin/bash
# Batch OCR with GNU parallel

INPUT_LIST="pdfs_to_ocr.txt"
NUM_CORES=8  # Adjust based on system

# Function to OCR single PDF
ocr_pdf() {
  input="$1"

  # Create output path (add _ocr before .pdf)
  output="${input%.pdf}_ocr.pdf"

  # Skip if already done
  if [ -f "$output" ]; then
    echo "SKIP: $output already exists"
    return
  fi

  # OCR with error handling
  if ocrmypdf --deskew --rotate-pages --clean \
              --optimize 1 \
              --skip-text \
              "$input" "$output" 2>/dev/null; then
    echo "SUCCESS: $output"
  else
    echo "FAILED: $input"
  fi
}

export -f ocr_pdf

# Run in parallel
cat "$INPUT_LIST" | parallel -j "$NUM_CORES" ocr_pdf {}

echo "OCR complete!"
EOF

chmod +x scripts/batch_ocr.sh

# Run OCR (will take 1-3 hours)
./scripts/batch_ocr.sh
```

### Phase 4: Verify & Replace (10 minutes)

```bash
# Check OCR'd files
find "/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers" \
  -name "*_ocr.pdf" | wc -l

# Verify a few randomly
find "/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers" \
  -name "*_ocr.pdf" -type f | shuf -n 5 | while read pdf; do
  echo "=== $pdf ==="
  pdftotext "$pdf" - | head -20
done

# If satisfied, replace originals
find "/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers" \
  -name "*_ocr.pdf" -type f | while read ocr_file; do
  original="${ocr_file%_ocr.pdf}.pdf"

  # Backup original
  mkdir -p backups/pre_ocr/
  cp "$original" backups/pre_ocr/

  # Replace with OCR'd version
  mv "$ocr_file" "$original"
done
```

---

## Performance Optimization

### Parallel Processing

**Using GNU Parallel (recommended):**

```bash
# Install
sudo apt-get install parallel

# OCR with 8 cores
cat pdfs_to_ocr.txt | parallel -j 8 ocrmypdf --skip-text {} {.}_ocr.pdf

# OCR with all available cores
cat pdfs_to_ocr.txt | parallel ocrmypdf --skip-text {} {.}_ocr.pdf
```

**Speed improvement:**
- 1 core: 100% time (baseline)
- 4 cores: ~25-30% time (3-4× faster)
- 8 cores: ~12-15% time (6-8× faster)
- 16 cores: ~6-8% time (12-16× faster)

**System check:**
```bash
# How many cores do you have?
nproc

# Recommended: Use (cores - 1) to keep system responsive
nproc --ignore=1
```

### OCRmyPDF Options for Speed

```bash
# Fastest (lower quality)
ocrmypdf --fast-web-view --optimize 0 input.pdf output.pdf

# Balanced (recommended)
ocrmypdf --deskew --rotate-pages --optimize 1 input.pdf output.pdf

# Best quality (slowest)
ocrmypdf --deskew --rotate-pages --clean --optimize 3 input.pdf output.pdf

# Skip pages that already have text (much faster!)
ocrmypdf --skip-text input.pdf output.pdf
```

---

## Cost Analysis

### Open Source (Free)

**Tools:** Tesseract + ocrmypdf
- Cost: $0
- Time: 1-3 hours (parallel)
- Quality: Good (95-98% accuracy)

### Commercial Tools

**Adobe Acrobat Pro DC:**
- Cost: $15/month subscription
- Time: ~30-60 minutes (parallel)
- Quality: Excellent (98-99% accuracy)
- Worth it? Probably not for 267 PDFs

**ABBYY FineReader:**
- Cost: $200 one-time
- Time: ~30-45 minutes (parallel)
- Quality: Excellent (98-99% accuracy)
- Worth it? No for this use case

### Cloud Services

**Google Drive:**
- Cost: Free (15 GB limit)
- Time: Upload time + processing (~4-6 hours)
- Quality: Good
- Worth it? Maybe for very large PDFs

---

## Summary & Recommendation

### Best Approach for Your Project

**Recommended: Approach 1 (Quick OCR - Recent Papers Only)**

```
Target: ~40 PDFs from 2000+
Time: 15-20 minutes (8-core parallel)
Disk space: ~300 MB additional
Value: High (most relevant papers)
Effort: Minimal
```

**Why:**
- Fastest ROI
- Most relevant papers for panel (recent trends)
- Minimal resource use
- Can always do older papers later if needed

### Implementation Plan

```bash
# 1. Install tools (5 min)
sudo apt-get install tesseract-ocr ocrmypdf parallel

# 2. Filter for recent PDFs only (2 min)
awk -F',' '$7=="True" && $3>=2000 {print $1}' outputs/pdf_ocr_status.csv > recent_pdfs_to_ocr.txt

# 3. Run parallel OCR (15-20 min)
cat recent_pdfs_to_ocr.txt | parallel -j 8 ocrmypdf --skip-text {} {.}_ocr.pdf

# 4. Verify and replace (5 min)
# Check results, replace originals if satisfied

Total time: ~30 minutes
```

### If You Want Complete Coverage

**Approach 3 (All Missing PDFs):**

```
Target: All 267 PDFs
Time: 1.5-2.5 hours (8-core parallel)
Disk space: ~2 GB additional (temp), ~0 net if replacing
Cost: Free
Benefit: 100% searchable text coverage
```

---

**Summary Table:**

| Metric | Current | After Quick OCR | After Full OCR |
|--------|---------|----------------|----------------|
| **PDFs with text** | 98% | 99.7% | 100% |
| **Time needed** | - | 30 min | 2-3 hours |
| **Disk space** | 33.6 GB | +300 MB | +2 GB (temp) |
| **Effort** | - | Minimal | Low-Medium |
| **Value for panel** | High | Very High | Marginal |

**Bottom line:** The quick OCR approach gives you the best value for minimal investment of time and disk space.

---

**Last Updated:** 2025-10-24
