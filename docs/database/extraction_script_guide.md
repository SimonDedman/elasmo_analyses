# Shark References to SQL Extraction Script Guide

**Script:** `scripts/shark_references_to_sql.py`
**Version:** 1.0
**Date:** 2025-10-21

---

## Overview

This script extracts data from the shark-references bulk download CSV and populates a SQL-compatible database according to the schema defined in `database_schema_design.md`.

**Input files:**
- `outputs/shark_references_bulk/shark_references_complete_2025_to_1950_20251021.csv` (30,523 papers)
- `data/techniques_snapshot_v20251021.csv` (216 techniques)

**Output files:**
- `outputs/literature_review.parquet` - Primary output (columnar, compressed)
- `outputs/literature_review.duckdb` - DuckDB database
- `outputs/literature_review_sample.csv` - First 100 rows for inspection
- `outputs/extraction_quality_report.md` - Detailed quality metrics

---

## Features

### TIER 1: Direct Copy (100% accuracy)
- `year` - Publication year
- `title` - Paper title
- `authors` - Author list
- `doi` - Digital Object Identifier
- `abstract` - Paper abstract
- `literature_id` - Unique shark-references ID
- `date_added` - Date added to database
- `data_source` - Source identifier

### TIER 2: Simple Parsing (85-95% accuracy)
- `journal` - Extracted from citation field
- `keywords` - Combined from keyword_time and keyword_place
- `study_type` - Basic classification (default: 'empirical')

### TIER 3: Advanced Extraction (60-80% accuracy)

#### Species Detection
- Extracts species binomials from title + abstract + described_species fields
- Pattern matching: `Genus species` format
- Creates binary columns: `sp_genus_species`
- Filters to species mentioned in ≥5 papers (reduces noise)

#### Technique Detection
- Uses search queries from techniques snapshot
- Searches title + abstract for technique keywords
- Supports Boolean operators: `+` (required), `OR` (alternative), `*` (wildcard)
- Creates binary columns: `a_technique_name`
- Includes both primary and alternative search queries

#### Ocean Basin Detection
- Searches for 9 major ocean basins in title + abstract + keyword_place
- Creates binary columns: `ob_basin_name`
- Basins: Arctic, N Atlantic, S Atlantic, Indian, N Pacific, S Pacific, Southern, Mediterranean, Baltic

---

## Installation

### Prerequisites

```bash
# Python 3.8+
python3 --version

# Install required packages
pip install pandas numpy duckdb pyarrow
```

### Package Details

- `pandas` - Data manipulation
- `numpy` - Numerical operations
- `duckdb` - SQL database
- `pyarrow` - Parquet file support

---

## Usage

### Basic Execution

```bash
cd "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"

# Run extraction
python3 scripts/shark_references_to_sql.py
```

### Expected Runtime

**Estimated time:** 15-30 minutes for 30,523 papers

Breakdown:
- TIER 1 (Direct copy): 1-2 minutes
- TIER 2 (Parsing): 2-3 minutes
- TIER 3a (Species): 5-10 minutes (pattern matching across all text)
- TIER 3b (Techniques): 8-15 minutes (216 techniques × 30k papers)
- TIER 3c (Basins): 1-2 minutes
- Export: 1-2 minutes

**Progress indicators:** Script prints progress every 5,000 papers (species) or 20 techniques

---

## Output Files

### 1. Parquet File (Primary)

**File:** `outputs/literature_review.parquet`
**Format:** Apache Parquet (columnar storage)
**Compression:** Snappy

**Benefits:**
- Fast queries on individual columns
- Excellent compression (sparse binary data)
- Compatible with Pandas, DuckDB, Spark, R

**Usage:**
```python
import pandas as pd
df = pd.read_parquet('outputs/literature_review.parquet')
```

**Expected size:** 15-30 MB (compressed from ~300 MB in-memory)

---

### 2. DuckDB Database

**File:** `outputs/literature_review.duckdb`
**Format:** DuckDB SQL database
**Table:** `literature_review`

**Benefits:**
- SQL queries
- Joins with other tables
- Analytical functions
- No server required

**Usage:**
```python
import duckdb
con = duckdb.connect('outputs/literature_review.duckdb')
result = con.execute("""
    SELECT year, COUNT(*) as papers
    FROM literature_review
    WHERE a_acoustic_telemetry = TRUE
    GROUP BY year
    ORDER BY year DESC
""").fetchdf()
```

**Expected size:** 30-50 MB

---

### 3. Sample CSV

**File:** `outputs/literature_review_sample.csv`
**Rows:** First 100 papers
**Purpose:** Quick inspection in Excel/LibreOffice

**Usage:** Open in spreadsheet software to verify structure

---

### 4. Quality Report

**File:** `outputs/extraction_quality_report.md`
**Format:** Markdown

**Contents:**
- Extraction statistics (papers processed, year range)
- Completeness by tier (% with abstracts, DOIs, etc.)
- Top 10 species by paper count
- Top 10 techniques by paper count
- Basin coverage statistics
- Data quality assessment
- Papers requiring manual review
- Next steps for Phase 2-4

---

## Output Schema

### Total Columns

**Current implementation:**
- Core metadata: 8 fields
- Journal/keywords: 3 fields
- Species: ~50-200 fields (depends on how many species found in ≥5 papers)
- Techniques: 216 fields (from snapshot)
- Ocean basins: 9 fields

**Total: ~286-436 columns**

### Column Naming Convention

| Type | Prefix | Example |
|------|--------|---------|
| Core metadata | none | `year`, `title`, `doi` |
| Species | `sp_` | `sp_carcharodon_carcharias` |
| Techniques | `a_` | `a_acoustic_telemetry` |
| Ocean basins | `ob_` | `ob_north_atlantic_ocean` |

---

## Data Quality

### Expected Accuracy

| Tier | Accuracy | Validation Method |
|------|----------|-------------------|
| TIER 1 | 100% | Direct copy (verified by source) |
| TIER 2 | 85-95% | Manual spot-checking |
| TIER 3a (Species) | 70-80% | Validation against known species list (Phase 2) |
| TIER 3b (Techniques) | 70-80% | Panelist review (Phase 4) |
| TIER 3c (Basins) | 60-70% | Geographic keyword matching |

### Known Limitations

**Species extraction:**
- May miss abbreviated binomials (e.g., "C. carcharias")
- May include false positives (non-chondrichthyan species)
- Synonyms not yet handled
- Requires validation against FishBase/Sharkipedia (Phase 2)

**Technique extraction:**
- Limited to title + abstract (no full text)
- Boolean query parsing may miss complex cases
- Some techniques may be mentioned but not actually used
- Requires panelist validation (Phase 4)

**Basin extraction:**
- Simple keyword matching (no geographic parsing)
- May miss implied locations (e.g., "Bering Sea" → North Pacific)
- Sub-basins not yet extracted (TIER 4)

---

## Troubleshooting

### Error: File Not Found

```
ERROR: Shark references CSV not found
```

**Solution:** Check that bulk download is complete:
```bash
ls -lh "outputs/shark_references_bulk/shark_references_complete_2025_to_1950_20251021.csv"
```

---

### Error: Techniques Snapshot Not Found

```
ERROR: Techniques snapshot not found
```

**Solution:** Ensure snapshot is created:
```bash
ls -lh "data/techniques_snapshot_v20251021.csv"
```

If missing, create from Excel:
```python
import pandas as pd
df = pd.read_excel('data/Techniques DB for Panel Review.xlsx', sheet_name='Full_List')
df = df[df['technique_name'].notna()]
df.to_csv('data/techniques_snapshot_v20251021.csv', index=False)
```

---

### Memory Error

```
MemoryError: Unable to allocate array
```

**Solution:** Process in chunks (modify script):
```python
# In main(), change:
df_shark = pd.read_csv(SHARK_REFS_CSV, low_memory=False)

# To:
chunksize = 5000
for chunk in pd.read_csv(SHARK_REFS_CSV, chunksize=chunksize):
    # Process chunk...
```

**Note:** Script is designed for 30k papers and should work on systems with ≥8 GB RAM

---

### Slow Performance

**Expected runtime:** 15-30 minutes

**If significantly slower:**
1. Check CPU usage (should be high during extraction)
2. Close other applications
3. Disable antivirus scanning temporarily
4. Run on SSD (not HDD) if possible

---

## Quality Checks

### Post-Extraction Validation

```python
import pandas as pd

# Load output
df = pd.read_parquet('outputs/literature_review.parquet')

# Check basic stats
print(f"Total papers: {len(df):,}")
print(f"Year range: {df['year'].min()}-{df['year'].max()}")
print(f"Columns: {len(df.columns)}")

# Check completeness
print(f"\nCompleteness:")
print(f"  Abstracts: {(df['abstract'] != '').sum()/len(df)*100:.1f}%")
print(f"  DOIs: {(df['doi'] != '').sum()/len(df)*100:.1f}%")

# Check species
species_cols = [col for col in df.columns if col.startswith('sp_')]
print(f"\nSpecies columns: {len(species_cols)}")
print(f"Papers with ≥1 species: {(df[species_cols].sum(axis=1) > 0).sum()/len(df)*100:.1f}%")

# Check techniques
tech_cols = [col for col in df.columns if col.startswith('a_')]
print(f"\nTechnique columns: {len(tech_cols)}")
print(f"Papers with ≥1 technique: {(df[tech_cols].sum(axis=1) > 0).sum()/len(df)*100:.1f}%")

# Check basins
basin_cols = [col for col in df.columns if col.startswith('ob_')]
print(f"\nBasin columns: {len(basin_cols)}")
print(f"Papers with ≥1 basin: {(df[basin_cols].sum(axis=1) > 0).sum()/len(df)*100:.1f}%")
```

---

## Next Steps After Extraction

### Phase 2: Immediate Enhancements

1. **Species validation**
   - Load known chondrichthyan species from FishBase
   - Cross-reference extracted species
   - Remove false positives
   - Add missing species

2. **Sub-basin extraction**
   - Try searching 66 sub-basin names in abstracts
   - Create binary columns: `sb_subbasin_name`

3. **Technique → Discipline mapping**
   - Map 216 techniques to 8 disciplines
   - Populate discipline binary columns
   - Paper has discipline if ≥1 technique in that discipline

4. **Technique → Method family mapping**
   - Map techniques to 35 method families
   - Populate method_family columns

### Phase 3: Full-Text Extraction

1. **Download PDFs** (~20 GB, 6-12 hours)
2. **Extract full text** (PyPDF2/pdfplumber)
3. **Author affiliations** → Author nations (197 columns)
4. **Subtechniques** → Search full text (25 columns)

### Phase 4: Validation & Refinement

1. **Manual review** by panelists
2. **Precision/recall** calculation on sample
3. **Query refinement** based on false positives/negatives
4. **Re-extraction** with improved queries

---

## Query Examples

### Example 1: Papers by Technique and Year

```python
import duckdb
con = duckdb.connect('outputs/literature_review.duckdb')

result = con.execute("""
    SELECT
        year,
        COUNT(*) as total_papers,
        SUM(CAST(a_acoustic_telemetry AS INT)) as acoustic_telemetry,
        SUM(CAST(a_satellite_tracking AS INT)) as satellite_tracking
    FROM literature_review
    WHERE year >= 2010
    GROUP BY year
    ORDER BY year DESC
""").fetchdf()

print(result)
```

### Example 2: Multi-Technique Papers

```python
import pandas as pd
df = pd.read_parquet('outputs/literature_review.parquet')

# Get technique columns
tech_cols = [col for col in df.columns if col.startswith('a_')]

# Count techniques per paper
df['technique_count'] = df[tech_cols].sum(axis=1)

# Papers using 5+ techniques
multi_tech = df[df['technique_count'] >= 5].sort_values('technique_count', ascending=False)

print(f"Papers using ≥5 techniques: {len(multi_tech)}")
print("\nTop 5:")
for idx, row in multi_tech.head().iterrows():
    print(f"\n{row['year']} - {row['title'][:80]}...")
    print(f"  Techniques: {row['technique_count']}")
```

### Example 3: Species by Basin

```python
import pandas as pd
df = pd.read_parquet('outputs/literature_review.parquet')

# Filter to papers with great white shark and Atlantic Ocean
mask = (
    (df['sp_carcharodon_carcharias'] == True) &
    ((df['ob_north_atlantic_ocean'] == True) | (df['ob_south_atlantic_ocean'] == True))
)

atlantic_white_sharks = df[mask]
print(f"Papers on C. carcharias in Atlantic: {len(atlantic_white_sharks)}")
print(f"Year range: {atlantic_white_sharks['year'].min()}-{atlantic_white_sharks['year'].max()}")
```

---

## Script Modification Guide

### Adding Custom Species List

Modify `create_species_columns()` function:

```python
def create_species_columns(df, known_species_file=None):
    """
    If known_species_file provided, validate against it
    """
    if known_species_file:
        known_species = pd.read_csv(known_species_file)
        known_binomials = set(
            known_species['genus'].str.lower() + '_' +
            known_species['species'].str.lower()
        )
        # Filter extracted species to known list
        # ...
```

### Adjusting Species Threshold

Change minimum paper count for species inclusion:

```python
# Line ~285
# Current: species mentioned in ≥5 papers
significant_species = {sp: count for sp, count in all_species.items() if count >= 5}

# Change to ≥10 papers (more conservative)
significant_species = {sp: count for sp, count in all_species.items() if count >= 10}

# Or ≥3 papers (more inclusive)
significant_species = {sp: count for sp, count in all_species.items() if count >= 3}
```

### Processing Subset of Papers (Testing)

For testing, process only recent papers:

```python
# In main(), after loading data
df_shark = df_shark[df_shark['year'] >= 2020]  # Only 2020-2025
print(f"  Testing mode: {len(df_shark)} papers (2020-2025)")
```

---

## Performance Optimization

### Parallel Processing

For large datasets, parallelize technique extraction:

```python
from multiprocessing import Pool

def process_technique(tech_row):
    """Process single technique"""
    # ... extraction logic
    return results

# In create_technique_columns()
with Pool(4) as pool:  # 4 CPU cores
    results = pool.map(process_technique, techniques_df.iterrows())
```

### Batch Processing

Process papers in batches to reduce memory:

```python
batch_size = 5000
num_batches = len(df_shark) // batch_size + 1

for i in range(num_batches):
    start_idx = i * batch_size
    end_idx = min((i + 1) * batch_size, len(df_shark))
    batch = df_shark.iloc[start_idx:end_idx]
    # Process batch...
```

---

## Version History

### v1.0 (2025-10-21)
- Initial release
- TIER 1-3 extraction
- 216 techniques from snapshot v20251021
- Species extraction with ≥5 paper threshold
- 9 ocean basins
- Parquet, DuckDB, CSV outputs
- Quality report generation

### Planned (v1.1)
- Species validation against FishBase
- Sub-basin extraction (66 sub-basins)
- Discipline mapping (8 disciplines)
- Method family mapping (35 families)

---

## Support & Contact

**Issues:** Report extraction errors, unexpected results, or feature requests

**Documentation:**
- `docs/database/database_schema_design.md` - Full schema specification
- `docs/database/shark_references_to_sql_mapping.md` - Field mapping details
- `docs/database/techniques_snapshot_strategy.md` - Snapshot versioning

---

**Script created:** 2025-10-21
**Last updated:** 2025-10-21
**Status:** Production-ready for TIER 1-3 extraction
