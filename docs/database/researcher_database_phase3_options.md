# Researcher Database - Phase 3 Options

## Overview
Phase 2 successfully extracted 73 countries with 5,483 geocoded affiliations. Phase 3 would enhance data quality and enable advanced analyses.

## Completed Phases

### ✅ Phase 1: Filename Extraction
- 2,486 unique first authors from 4,517 PDFs (99.4% success)
- See: `outputs/researchers/filename_parsing_report.txt`

### ✅ Phase 2: PDF Affiliation Extraction
- 18,851 unique authors, 12,105 institutions
- 73 countries identified (expanded from initial 25)
- 2,612 papers with geographic data
- See: `outputs/researchers/phase2_extraction_report.txt`

## Phase 3 Enhancement Options

### Option A: Institution Normalization (Recommended)
**Purpose**: Consolidate variant institution names

**Examples of variants**:
- "University of X" vs "Univ. of X" vs "X University"
- "CSIRO" vs "Commonwealth Scientific and Industrial Research Organisation"

**Approach**:
```python
# Fuzzy matching + manual curation
institution_variants = {
    "University of Queensland": [
        "Univ. Queensland",
        "UQ",
        "Queensland Univ."
    ]
}
```

**Benefits**:
- More accurate institution counts
- Better collaboration network analysis
- Cleaner country assignment

**Effort**: Medium (1-2 days for top 100 institutions)

---

### Option B: ORCID Integration
**Purpose**: Disambiguate authors, get accurate affiliations

**Process**:
1. Query ORCID API for author names
2. Match to known affiliations/publication years
3. Extract verified institutional history

**Benefits**:
- Resolve author name variants (J. Smith vs Jane Smith)
- Track researcher mobility
- Find additional affiliations

**Challenges**:
- Not all researchers have ORCIDs
- API rate limits
- Manual verification needed

**Effort**: High (3-5 days)

---

### Option C: Enhanced Country Extraction
**Purpose**: Catch missed countries using NLP

**Current**: Simple string matching (~73 countries found)

**Enhancement**:
- Use spaCy NER for location extraction
- Add city → country mapping
- Handle multilingual affiliations

**Example**:
```
"Laboratoire de Biologie, Marseille" → France (via city lookup)
```

**Benefits**:
- Increase geocoding coverage beyond current 45%
- Find researchers from smaller countries

**Effort**: Low-Medium (1-2 days)

---

### Option D: Collaboration Network Analysis
**Purpose**: Map research networks

**Metrics**:
- Co-authorship networks
- Institution collaborations
- Cross-country partnerships
- Temporal evolution of networks

**Visualizations**:
- Network graphs (NetworkX/igraph)
- Geographic collaboration flows
- Clustered research communities

**Dependencies**: Requires clean institution data (Option A recommended first)

**Effort**: Medium (2-3 days)

---

## Recommended Priority

1. **Option C** (Enhanced Country Extraction) - Quick wins, high impact
2. **Option A** (Institution Normalization) - Foundation for other analyses
3. **Option D** (Collaboration Networks) - After A is complete
4. **Option B** (ORCID) - Optional, if author disambiguation needed

## Scripts Ready to Run

Current researcher database scripts:
- ✅ `scripts/extract_authors_phase1_parallel.py`
- ✅ `scripts/extract_authors_phase2_parallel.py`
- 🔄 Phase 3 scripts: To be created based on selected option

## Data Files Available

### Input:
- `outputs/researchers/paper_authors_full.csv` (57,914 records)
- `outputs/researchers/institutions_raw.csv` (12,105 institutions)
- `outputs/researchers/author_cache.json` (18,851 authors)

### Output:
- `outputs/analysis/papers_per_country.csv` (71 countries)
- `outputs/analysis/disciplines_per_country.csv`
- `outputs/analysis/papers_by_region.csv` (6 regions)

## Next Steps

To implement any option:
1. Review this document
2. Select desired option(s)
3. Create corresponding Phase 3 script
4. Run analysis
5. Generate visualizations

---

*Last Updated: 2025-10-26*
*Current Status: Phase 2 Complete, Phase 3 Optional*
