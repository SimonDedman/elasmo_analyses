# EEA 2025 Data Panel: PDF Technique Extraction - Results Overview

**Last Updated:** 2025-10-26
**Status:** Phase 2 Complete - Ready for Review

---

## Quick Navigation

### 📊 For Review & Analysis
- **[Extraction Progress Report](docs/database/extraction_progress_report.md)** - ⭐ Complete peer review document
- **[Project Completion Summary](docs/project_completion_summary.md)** - Deliverables and status
- **[README](README.md)** - Main project overview

### 📈 Analysis Data (CSV Files)
All files in [`outputs/analysis/`](outputs/analysis/):
1. **[discipline_trends_by_year.csv](outputs/analysis/discipline_trends_by_year.csv)** - Discipline paper counts 1950-2025 (481 rows)
2. **[technique_trends_by_year.csv](outputs/analysis/technique_trends_by_year.csv)** - Technique adoption over time (2,308 rows)
3. **[data_science_segmentation.csv](outputs/analysis/data_science_segmentation.csv)** - DATA cross-cutting analysis (4,545 papers)
4. **[top_techniques.csv](outputs/analysis/top_techniques.csv)** - All 151 techniques ranked by usage
5. **[discipline_cooccurrence_matrix.csv](outputs/analysis/discipline_cooccurrence_matrix.csv)** - 8×8 discipline overlap matrix
6. **[summary_statistics.csv](outputs/analysis/summary_statistics.csv)** - Overall extraction metrics
7. **[discipline_summary.csv](outputs/analysis/discipline_summary.csv)** - Discipline totals

### 🗄️ Database
- **SQLite Database:** `database/technique_taxonomy.db` (23,307 technique mentions across 9,503 papers)
- **[Database Schema](docs/database/database_schema_design.md)** - Table structures and relationships

### 🔧 Technical Documentation
- **[Extraction Guide](docs/database/extraction_guide.md)** - How to run the extraction scripts
- **[Extraction Complete Summary](docs/database/extraction_complete_summary.md)** - Technical details and metrics

---

## Executive Summary

Successfully extracted analytical techniques from **9,503 shark science papers** (76.5% of 12,381-paper corpus) spanning **75 years (1950-2025)**. The extraction identified **151 unique techniques** across **8 disciplines**.

### Key Findings

#### Discipline Distribution
| Discipline | Papers | % of Corpus |
|------------|--------|-------------|
| **GEN** (Genetics & Genomics) | 7,992 | 84.7% |
| **DATA** (Data Science) | 4,545 | 48.2% |
| **BIO** (Biology & Life History) | 2,092 | 22.2% |
| **FISH** (Fisheries & Stock Assessment) | 1,583 | 16.8% |
| **MOV** (Movement & Space Use) | 1,442 | 15.3% |
| **TRO** (Trophic & Community Ecology) | 1,318 | 14.0% |
| **CON** (Conservation & Policy) | 858 | 9.1% |
| **BEH** (Behaviour & Sensory) | 265 | 2.8% |

**Key Insights:**
- **Genetics dominates** shark science (85% of papers)
- **Data science is pervasive** (48% of papers), mostly cross-cutting with other disciplines
- **Behavior is underrepresented** (2.8% of papers)

#### Data Science Cross-Cutting Analysis

Of 4,545 papers using DATA techniques:
- **70.5%** (3,204 papers) are cross-cutting - using data techniques in other disciplines
- **27.2%** (1,237 papers) have DATA as primary discipline with other techniques
- **2.3%** (104 papers) are pure DATA/methods papers

**Conclusion:** Data science is overwhelmingly integrated into other disciplines rather than standalone.

#### Top 10 Techniques by Paper Count

| Rank | Technique | Papers | % of Corpus | Discipline |
|------|-----------|--------|-------------|------------|
| 1 | STRUCTURE | 7,535 | 79.8% | GEN |
| 2 | Connectivity | 1,068 | 11.3% | GEN |
| 3 | Stock Assessment | 984 | 10.4% | FISH |
| 4 | Parasitology | 927 | 9.8% | BIO |
| 5 | Tourism | 777 | 8.2% | CON |
| 6 | Time Series | 691 | 7.3% | DATA |
| 7 | Phylogenetics | 614 | 6.5% | GEN |
| 8 | Morphometrics | 572 | 6.1% | BIO |
| 9 | Metabolic Rate | 555 | 5.9% | BIO |
| 10 | Genomics | 513 | 5.4% | GEN |

⚠️ **Note:** STRUCTURE appears in 80% of papers - requires manual validation for potential false positives.

---

## Extraction Methodology

### Corpus
- **Total PDFs:** 12,381 shark science papers (1950-2025)
- **Successfully processed:** 9,503 papers (76.5%)
- **Papers with techniques:** 9,437 papers (76.2%)
- **Papers without techniques:** 2,944 papers (23.8% - likely scanned PDFs, review papers, or no methodology)

### Technique Matching
- **Search list:** 182 techniques (priority 1 & 2 from expert-reviewed database)
- **Techniques found:** 151 (83% coverage)
- **Techniques not found:** 31 (likely rare/emerging methods)
- **Total mentions:** 23,307 technique occurrences
- **Average per paper:** 2.5 techniques

### Processing Details
- **Method:** Case-insensitive regex pattern matching with word boundaries
- **Tool:** `pdftotext` for text extraction
- **Performance:** 25-30 PDFs/second using 11 CPU cores
- **Context:** 100 characters captured around each mention
- **Quality controls:** PDF timeout, text length limits, duplicate removal, resume capability

### Cross-Cutting DATA Logic

Papers count for DATA discipline if they use ANY of **128 techniques** marked as:
- Primary discipline = DATA (28 techniques), OR
- `statistical_model = TRUE`, OR
- `analytical_algorithm = TRUE`, OR
- `inference_framework = TRUE`

This enables analysis of pure data science vs. data science integrated into other disciplines.

---

## For Peer Reviewers

### Review Priorities

#### 1. Validate Top Techniques (High Priority)
- **STRUCTURE false positives** - Sample 100 mentions, verify they reference the software (not general "structure")
- **Calculate accuracy** - Determine false positive rate
- **Refine if needed** - Adjust search pattern if >10% false positives

#### 2. Missing Techniques Review (High Priority)
- **31 techniques not found** in corpus
- **Determine if:** Keep (genuinely rare), Remove (not relevant to sharks), or Rename (alternative terms)
- **See:** `docs/database/extraction_progress_report.md` for full list

#### 3. Papers Without Techniques (Medium Priority)
- **2,944 papers** (23.8%) with no technique matches
- **Sample 50 papers** to categorize reasons:
  - Scanned PDFs without OCR
  - Review/opinion papers
  - Different terminology
  - Corrupted files
- **Estimate** what % are genuine misses vs. expected non-methodology papers

#### 4. Bias Assessment (Medium Priority)
- **Discipline balance** - Is genetics over-represented due to technique list bias?
- **Cross-cutting DATA definition** - Are 128 techniques too broad/narrow?
- **Temporal bias** - Compare OCR quality pre-2000 vs. post-2010
- **Language bias** - English-only corpus (acceptable for shark science?)

#### 5. Completeness Check (Lower Priority)
- **Major methodologies missing?** - Any shark science approaches completely absent?
- **Alternative technique names** - Identify synonyms/acronyms being missed
- **Species linkage validation** - Review species detection accuracy (if time permits)

### Reviewer Checklist

**Data Quality:**
- [ ] Review summary statistics - match expectations?
- [ ] Check discipline distribution - any surprising results?
- [ ] Verify top techniques list - recognizable shark science methods?
- [ ] Examine temporal trends - match known technology adoption?

**Bias Detection:**
- [ ] Any discipline over/under-represented?
- [ ] Emerging techniques (AI/ML/eDNA) adequately captured?
- [ ] Pre-2000 data quality sufficient?
- [ ] Non-genetics disciplines fairly represented?

**Completeness:**
- [ ] Major shark science methodologies completely missing?
- [ ] Should any of 31 missing techniques be renamed and re-searched?
- [ ] Is "no techniques" group (24%) acceptable?
- [ ] Are DATA cross-cutting criteria appropriate?

**Next Steps:**
- [ ] Approve current extraction for EEA Data Panel analysis?
- [ ] Request corrections/re-runs for specific issues?
- [ ] Prioritize researcher network completion?
- [ ] Suggest additional validation steps?

---

## Data Outputs

### Analysis CSV Files

All files ready for visualization in R, Python, Excel, Tableau, etc.

**Location:** [`outputs/analysis/`](outputs/analysis/)

#### Discipline Trends by Year
**File:** `discipline_trends_by_year.csv` (481 rows)

Columns: `year`, `discipline_code`, `paper_count`, `total_techniques`, `assignment_type`

**Use for:**
- Line charts showing discipline growth over time
- Identifying emerging vs. declining disciplines
- Temporal trend analysis (1950-2025)

#### Technique Trends by Year
**File:** `technique_trends_by_year.csv` (2,308 rows)

Columns: `year`, `technique_name`, `primary_discipline`, `paper_count`, `total_mentions`, `avg_mentions_per_paper`

**Use for:**
- Individual technique adoption timelines
- Identifying emerging techniques (high recent growth)
- Identifying declining techniques
- Technique popularity rankings by decade

#### Data Science Segmentation
**File:** `data_science_segmentation.csv` (4,545 rows)

Columns: `paper_id`, `year`, `category`, `num_disciplines`, `disciplines`, `data_assignment_type`

Categories:
- `DATA_only` - Pure data science papers (104 papers, 2.3%)
- `DATA_primary_with_others` - DATA as main discipline (1,237 papers, 27.2%)
- `DATA_cross_cutting` - Other disciplines using data techniques (3,204 papers, 70.5%)

**Use for:**
- Understanding data science integration in shark research
- Visualizing cross-cutting vs. pure data science
- Tree graphic showing DATA connections to other disciplines

#### Top Techniques
**File:** `top_techniques.csv` (151 rows)

Columns: `technique_name`, `primary_discipline`, `paper_count`, `total_mentions`, `avg_mentions_per_paper`, `max_mentions`

**Use for:**
- Bar charts of most popular techniques
- Comparing technique usage across disciplines
- Identifying highly-mentioned techniques (intensive use)

#### Discipline Co-occurrence Matrix
**File:** `discipline_cooccurrence_matrix.csv` (8×8 matrix)

Rows/Columns: BEH, BIO, CON, DATA, FISH, GEN, MOV, TRO

Diagonal = single-discipline papers
Off-diagonal = multi-discipline papers

**Use for:**
- Heatmaps showing discipline overlap
- Network diagrams of discipline relationships
- Understanding multi-disciplinary research patterns

#### Summary Statistics
**File:** `summary_statistics.csv` (1 row)

Overall extraction metrics: total papers, techniques found, averages, year range

**Use for:**
- Quick summary statistics
- Reporting key numbers
- Validation checks

#### Discipline Summary
**File:** `discipline_summary.csv` (8 rows)

Columns: `discipline_code`, `paper_count`

**Use for:**
- Simple bar chart of discipline distribution
- Quick discipline comparisons

### SQLite Database

**File:** `database/technique_taxonomy.db`

**Tables:**
- `paper_techniques` (23,307 rows) - Which techniques appear in which papers
- `paper_disciplines` (20,095 rows) - Discipline assignments (papers × disciplines)
- `extraction_log` (9,503 rows) - Processing status for each PDF

**Query examples:**

```sql
-- Top 10 techniques
SELECT technique_name, COUNT(DISTINCT paper_id) as papers
FROM paper_techniques
GROUP BY technique_name
ORDER BY papers DESC
LIMIT 10;

-- Papers by discipline and year
SELECT year, discipline_code, COUNT(DISTINCT paper_id) as papers
FROM paper_disciplines
WHERE year >= 2000
GROUP BY year, discipline_code
ORDER BY year, discipline_code;

-- Cross-cutting DATA papers
SELECT DISTINCT p1.paper_id, p1.year
FROM paper_disciplines p1
JOIN paper_disciplines p2 ON p1.paper_id = p2.paper_id
WHERE p1.discipline_code = 'DATA'
  AND p2.discipline_code != 'DATA';
```

---

## Temporal Trends

### Discipline Growth (2000-2025)

**Fastest growing:**
1. **DATA** - 12x increase (genomics boom driving computational needs)
2. **MOV** - 8x increase (telemetry technology advances)
3. **GEN** - 6x increase (sequencing cost reduction)

**Stable/declining:**
- **BEH** - Minimal growth (still <3% of papers)
- **TRO** - Moderate growth (stable isotope methods established)

### Technique Evolution

**Emerging techniques (high growth 2015-2025):**
- Machine Learning
- Environmental DNA (eDNA)
- Genomics
- Close-Kin Mark-Recapture (CKMR)

**Declining techniques:**
- Traditional mark-recapture (relative to genetics)
- Visual census (being supplemented by video/AI)

### Era Breakdown

| Period | Papers | Techniques | Avg Tech/Paper |
|--------|--------|------------|----------------|
| 1950-1979 | 127 | 45 | 1.8 |
| 1980-1999 | 891 | 98 | 2.1 |
| 2000-2009 | 1,824 | 132 | 2.3 |
| 2010-2019 | 4,256 | 149 | 2.6 |
| 2020-2025 | 2,405 | 151 | 2.7 |

**Trend:** Increasing technique diversity and usage over time

---

## Known Limitations

### Extraction Limitations
- **Filename-based author extraction** - Only surnames from filenames (not PDF metadata)
- **No species linkage** - Species detected but not yet analyzed
- **Researcher network incomplete** - Database schema issues (to be fixed)

### Potential Biases
- **Technique selection bias** - 182 techniques chosen by database authors (may favor certain areas)
- **Pattern matching limitations** - Regex can produce false positives/negatives
- **Language bias** - English-language papers only (acceptable for shark science field)
- **Temporal bias** - Older papers may have poorer OCR quality
- **Grey literature gap** - Theses/reports may use different terminology

### Data Quality Concerns
- **STRUCTURE over-representation?** - 80% of papers seems high, requires validation
- **Cross-cutting DATA definition** - 128 techniques may be too broad (reviewer feedback needed)
- **Missing techniques** - 31 not found (are they genuinely rare or poorly named?)

---

## Next Steps

### Immediate (This Week)
1. ✅ Generate analysis tables
2. ✅ Create peer review documentation
3. ✅ Update project README
4. 🔄 **Distribute to colleagues for review**
5. ⏳ Fix researcher network schema
6. ⏳ Re-run full extraction with researcher data

### Short-Term (Next 2 Weeks)
7. Manual validation sampling (STRUCTURE, missing techniques, no-technique papers)
8. Incorporate peer review feedback
9. Create visualizations (discipline trends, technique timelines, DATA tree)
10. Build researcher collaboration networks

### Before EEA 2025 (30 October 2025)
11. Finalize visualizations for conference
12. Prepare presentation materials
13. Test interactive dashboards (if created)

### Post-Conference
14. Incorporate community feedback
15. Add missing techniques identified
16. Public release (November 2025)

---

## How to Use This Data

### For Visualization
1. Load CSV files into R, Python, or visualization software
2. See [`docs/database/extraction_progress_report.md`](docs/database/extraction_progress_report.md) for analysis ideas
3. Create discipline trend line charts, technique adoption timelines, heatmaps, networks

### For Database Queries
1. Open `database/technique_taxonomy.db` with SQLite
2. Query `paper_techniques`, `paper_disciplines`, or `extraction_log` tables
3. Join tables for complex analyses

### For Validation
1. Review [`docs/database/extraction_progress_report.md`](docs/database/extraction_progress_report.md)
2. Check reviewer checklist and validation procedures
3. Provide feedback on methodology, bias, completeness

---

## Citation

If you use data or findings from this extraction, please cite:

```
Dedman, S., Tiktak, G., et al. (2025). Elasmobranch Analytical Methods Review:
A systematic extraction of techniques from 9,503 shark science papers (1950-2025).
European Elasmobranch Association Conference 2025, Rotterdam, Netherlands.
https://github.com/SimonDedman/eea_2025_data_panel
```

---

## Contact

**Project Lead:** Dr. Simon Dedman (simondedman@gmail.com)

**For questions:**
- Peer review: See extraction progress report
- Technical: See extraction guide
- Data: Query SQLite database or CSV files

---

## License

This work is licensed under a [Creative Commons Attribution 4.0 International License](https://creativecommons.org/licenses/by/4.0/).

---

*Document Version: 1.0*
*Last Updated: 2025-10-26*
*Status: Ready for Peer Review*
