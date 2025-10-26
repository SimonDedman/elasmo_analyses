# PDF Technique Extraction Guide

## Overview

Extracts techniques from 12,381 shark science PDFs and builds researcher collaboration database.

**Created:** 2025-10-26
**Script:** `scripts/extract_techniques_from_pdfs.py`
**Database:** `database/technique_taxonomy.db`

---

## What Gets Extracted

### From each PDF:
1. **182 techniques** (priority 1 & 2 from Excel)
2. **Author names** (from filename)
3. **Year** (from folder structure)
4. **Technique mentions** (count + context)
5. **Disciplines** (primary + cross-cutting DATA)

### Cross-Cutting DATA Logic:
Papers count for DATA discipline if they use ANY technique where:
- `discipline = 'DATA'` (28 primary DATA techniques), OR
- `statistical_model = TRUE` OR `analytical_algorithm = TRUE` OR `inference_framework = TRUE`

**Result:** 128 total techniques count for DATA (28 primary + 100 cross-cutting)

---

## Usage

### Test Run (10 PDFs, no database writes):
```bash
./venv/bin/python scripts/extract_techniques_from_pdfs.py --dry-run --limit 10
```

### Full Extraction (12,381 PDFs):
```bash
nohup ./venv/bin/python scripts/extract_techniques_from_pdfs.py > logs/extraction_full.log 2>&1 &
```

### Resume After Interruption:
```bash
# Automatically resumes - skips already processed PDFs
./venv/bin/python scripts/extract_techniques_from_pdfs.py
```

### Start Fresh (ignore previous progress):
```bash
./venv/bin/python scripts/extract_techniques_from_pdfs.py --no-resume
```

---

## Output

### Database Tables Populated:
- `paper_techniques` - Which techniques appear in which papers
- `paper_disciplines` - Which disciplines each paper belongs to
- `paper_authors` - Author-paper relationships
- `researchers` - Unique researcher records
- `collaborations` - Co-authorship network
- `researcher_techniques` - Who uses what techniques
- `researcher_disciplines` - Who works in what fields
- `extraction_log` - Processing status for each PDF

### CSV Exports (created during run):
```
outputs/technique_extraction/
├── extraction_progress.json    # Live progress updates
└── extraction_stats.json       # Final summary statistics
```

---

## Performance

- **Speed:** ~5-15 PDFs/second (varies by PDF size and technique matches)
- **Estimated time:** 15-45 minutes for 12,381 PDFs
- **Resume:** Saves progress every 100 PDFs
- **Memory:** ~500MB RAM

---

## Database Schema

### Core Relationships:
```
papers 1→∞ paper_techniques ∞→1 techniques
papers 1→∞ paper_disciplines ∞→1 disciplines
papers 1→∞ paper_authors ∞→1 researchers
researchers ∞→∞ collaborations ∞→∞ researchers
researchers 1→∞ researcher_techniques ∞→1 techniques
researchers 1→∞ researcher_disciplines ∞→1 disciplines
```

### Key Fields:

**paper_techniques:**
- paper_id, technique_name, discipline, mention_count, context_sample

**paper_disciplines:**
- paper_id, discipline_code, assignment_type (primary/cross_cutting/mixed)
- is_data_only, is_primary_only

**researchers:**
- researcher_id, surname, first_paper_year, last_paper_year
- total_papers, lead_author_papers

**collaborations:**
- researcher_1_id, researcher_2_id, collaboration_count
- first_collaboration_year, last_collaboration_year

---

## Downstream Analysis

After extraction completes, build analysis tables:

```bash
./venv/bin/python scripts/build_analysis_tables.py
```

This creates:
- `discipline_trends_by_year.csv` - Discipline trends over time
- `technique_trends_by_year.csv` - Individual technique trends
- `data_science_segmentation.csv` - DATA-only vs cross-cutting breakdown
- `researcher_metrics.csv` - Publication metrics by researcher

---

## Troubleshooting

### Extraction Stalls
- Check `logs/extraction.log` for errors
- Resume with `--no-dry-run` (continues where it left off)

### Low Technique Matches
- Normal - many PDFs won't mention specific techniques
- Average: 8-40 techniques per paper (estimated)

### Author Name Issues
- Simple extraction from filename only (for now)
- Will be enhanced with ORCID integration later
- Name variants handled in post-processing

### Database Locked
- Only run one extraction process at a time
- If stuck, check for zombie processes: `ps aux | grep extract_techniques`

---

## Next Steps

1. ✅ **Run extraction** across all 12,381 PDFs
2. **Build analysis tables** for EEA Data Panel
3. **Calculate researcher metrics** (flexible time windows)
4. **Create visualizations** (discipline trends, researcher networks)
5. **ORCID integration** (enhance researcher data)
6. **Conference attendance** (manual import when available)

---

## Data Science Visualization

The cross-cutting DATA discipline structure enables:

**Tree Graphic:** Shows how Data Science techniques connect to other disciplines
- 28 primary DATA techniques (pure data science)
- 100 cross-cutting techniques from other disciplines
- Papers can be filtered: DATA-only, DATA cross-cutting, or both

This will be visualized in the planned tree graphic showing DATA connections across all 8 disciplines.
