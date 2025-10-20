---
editor_options:
  markdown:
    wrap: 72
---

# Database Schema Design for Systematic Literature Review

## Overview

This document analyzes the database requirements for the EEA 2025 Data
Panel systematic literature review, evaluates the proposed wide-sparse
schema design, and recommends optimal database format and structure.

**Key Challenge:** Balancing comprehensive categorical coverage (many
binary columns) against database performance and maintainability for a
sparse, distributed collaborative project.

------------------------------------------------------------------------

## 1. Column Schema Analysis

### Current Template Structure

From `Example of Spreadsheet for Review.xlsx`:

| Column | Type | Purpose | Proposed Change |
|----|----|----|----|
| study_id | Index | Unique row identifier | ✅ Keep as-is (PRIMARY KEY) |
| reviewer | Text | Data entry accountability | ✅ Keep as-is |
| discipline | Category | Single discipline assignment | ⚠️ **PIVOT TO BINARY** |
| author | Text | Author names | ✅ Keep as-is |
| year | Integer | Publication year | ✅ Keep as-is |
| journal | Text | Journal name | ✅ Keep as-is |
| doi | Text | Digital object identifier | ✅ Keep as-is (UNIQUE) |
| study_type | Category | Primary/Review/Meta-analysis | ✅ Keep as-is (ENUM) |
| n_studies | Integer | Count of studies in review/meta-analysis | ✅ Add for review papers |
| region | Category | Geographic location | ⚠️ **SPLIT INTO 3 SCHEMAS** |
| superorder | Category | Taxonomic grouping | ⚠️ **BINARIZE** |
| species | Category | Species studied | ⚠️ **BINARIZE WIDE** |
| analysis_approach | Category | Analytical methods | ⚠️ **BINARIZE WIDE** |
| key_findings | Text | Subjective summary | ❌ **REMOVE FROM DBASE** |
| strengths | Text | Subjective assessment | ❌ **REMOVE FROM DBASE** |
| weaknesses | Text | Subjective assessment | ❌ **REMOVE FROM DBASE** |
| shark_refs_pdf | Text/Int | SharkReferences database ID | ✅ Keep as-is |

------------------------------------------------------------------------

## 2. Sequential Column Design Decisions

### 2.1 study_id (Index)

**Decision:** ✅ **APPROVED**

**Rationale:**

-   Essential for relational integrity
-   Auto-incrementing integer primary key
-   Enables efficient JOINs and lookups

**Schema:**

``` sql
study_id INTEGER PRIMARY KEY AUTOINCREMENT
```

### 2.2 reviewer

**Decision:** ✅ **APPROVED WITH ENHANCEMENT**

**Rationale:**

-   Accountability for data entry and QAQC
-   Essential for distributed collaborative work
-   Should include timestamp for audit trail

**Enhanced Schema:**

``` sql
reviewer VARCHAR(100) NOT NULL
review_date DATE NOT NULL DEFAULT CURRENT_DATE
last_modified_by VARCHAR(100)
last_modified_date TIMESTAMP
```

### 2.3 discipline

**Decision:** ⚠️ **PIVOT TO BINARY COLUMNS**

**Rationale:**

-   Papers frequently span multiple disciplines (e.g., genetics +
    conservation)
-   Single-category assignment loses cross-cutting information
-   Binary columns enable multi-label classification
-   Supports future discipline additions without schema migration

**Original Schema:**

``` sql
discipline VARCHAR(50)  -- Genetics, Movement, Fisheries, etc.
```

**Recommended Schema:**

``` sql
-- Prefix: d_ for "discipline"
d_biology_health BOOLEAN DEFAULT FALSE
d_behaviour_sensory BOOLEAN DEFAULT FALSE
d_trophic_ecology BOOLEAN DEFAULT FALSE
d_genetics_genomics BOOLEAN DEFAULT FALSE
d_movement_spatial BOOLEAN DEFAULT FALSE
d_fisheries_management BOOLEAN DEFAULT FALSE
d_conservation_policy BOOLEAN DEFAULT FALSE
d_data_science BOOLEAN DEFAULT FALSE
```

**Advantages:**

-   Multi-label support: paper can be
    `{d_genetics: TRUE, d_conservation: TRUE}`
-   Easy aggregation: `SELECT COUNT(*) WHERE d_genetics = TRUE`
-   Future-proof: add new `d_*` columns without breaking existing data
-   Query efficiency: indexed boolean columns fast for filtering

**Alternatives Considered:**

1.  **Normalized table:**
    `discipline_assignments(study_id, discipline_id)`
    -   ❌ More complex queries (requires JOINs)
    -   ❌ Less intuitive for reviewers
    -   ✅ Slightly more storage-efficient
    -   **Verdict:** Overkill for 8 disciplines
2.  **JSON array:** `disciplines JSON ['genetics', 'conservation']`
    -   ✅ Flexible schema
    -   ❌ Poor query performance (no indexing)
    -   ❌ Database-dependent syntax
    -   **Verdict:** Not recommended for analysis-heavy use case

### 2.4 study_type

**Decision:** ✅ **APPROVED AS ENUMERATED TYPE**

**Rationale:**

-   Three well-defined categories
-   Systematic reviews and meta-analyses typically self-identify in
    title/abstract
-   Can be extracted via text scraping (keywords: "systematic review",
    "meta-analysis")
-   Important for PRISMA compliance (exclude secondary studies from
    primary analysis)

**Schema:**

``` sql
study_type VARCHAR(20) CHECK (study_type IN ('Primary', 'Systematic Review', 'Meta-analysis'))
n_studies INTEGER  -- For review/meta-analysis papers: count of studies reviewed/analysed
```

**Usage:**

- `n_studies = NULL` for primary research papers
- `n_studies = <count>` for systematic reviews and meta-analyses
- Extract from abstract text patterns: "reviewed X studies", "meta-analysis of Y papers", "included Z publications"

**Automated Extraction Logic:**

``` python
def classify_study_type(title, abstract):
    """
    Classify study type from title/abstract text

    Returns: 'Meta-analysis', 'Systematic Review', or 'Primary'
    """
    text = (title + " " + abstract).lower()

    # Meta-analysis keywords (check first, as they're specific)
    if any(term in text for term in ['meta-analysis', 'meta analysis', 'metaanalysis']):
        return 'Meta-analysis'

    # Systematic review keywords
    if any(term in text for term in [
        'systematic review', 'literature review', 'scoping review',
        'umbrella review', 'review of', 'state-of-the-art review'
    ]):
        return 'Systematic Review'

    # Default to primary research
    return 'Primary'
```

### 2.5 region

**Decision:** ⚠️ **SPLIT INTO 3 HIERARCHICAL SCHEMAS**

**Rationale:**

-   Geographic information serves two purposes:
    1.  **Author affiliation** → Research capacity mapping
    2.  **Study location** → Biogeographic patterns
-   Conflating these loses important information
-   Multi-national collaborations and multi-basin studies are common

**Recommended 3-Schema Approach:**

#### Schema A: Author Institution Nations

**Prefix:** `auth_` for "author institution"

-   One binary column per UN-recognized nation (\~197 countries)
-   Captures multi-national collaborations
-   Enables research capacity analysis

``` sql
-- Examples (all BOOLEAN DEFAULT FALSE)
auth_usa BOOLEAN
auth_australia BOOLEAN
auth_united_kingdom BOOLEAN
auth_south_africa BOOLEAN
-- ... (197 total)
```

**Data Source:**

-   **ISO 3166-1 alpha-2 country codes** (official UN list)
-   Available at: <https://www.iso.org/obp/ui/#search/code/>
-   Alternative: R package `{countrycode}` or Python `pycountry`
-   Updated regularly by ISO (supports future edits)

**Automated Extraction:**

``` python
import pycountry

# Extract from author affiliations
def extract_author_countries(affiliation_text):
    """
    Parse affiliation text for country names

    Returns: set of ISO alpha-2 codes
    """
    countries = set()
    for country in pycountry.countries:
        if country.name.lower() in affiliation_text.lower():
            countries.add(country.alpha_2)
    return countries
```

#### Schema B: Major Ocean Basins

**Prefix:** `b_` for "basin"

-   Well-defined marine biogeographic regions
-   Papers can cover multiple basins (e.g., global meta-analysis)

``` sql
-- Major ocean basins (BOOLEAN DEFAULT FALSE)
b_north_atlantic BOOLEAN
b_south_atlantic BOOLEAN
b_north_pacific BOOLEAN
b_south_pacific BOOLEAN
b_indian_ocean BOOLEAN
b_southern_ocean BOOLEAN
b_arctic_ocean BOOLEAN
b_mediterranean_sea BOOLEAN
b_caribbean_sea BOOLEAN
```

**Data Source:**

-   **IHO Sea Areas** (International Hydrographic Organization)
-   Available via VLIZ Marine Regions: <https://www.marineregions.org/>
-   Standardized geographic boundaries

#### Schema C: Sub-Basins (Optional)

**Prefix:** `sb_` for "sub-basin"

-   Finer-scale biogeographic resolution
-   Large Ecosystems (LMEs) classification

``` sql
-- Examples (BOOLEAN DEFAULT FALSE)
sb_california_current BOOLEAN
sb_gulf_of_mexico BOOLEAN
sb_benguela_current BOOLEAN
sb_great_barrier_reef BOOLEAN
-- ... (~66 LMEs globally)
```

**Data Source:**

-   **Large Marine Ecosystems of the World** (NOAA/LME Program)
-   Available at: <https://www.lme.noaa.gov/>
-   66 well-defined LME regions

**Auto-Population Logic:**

``` sql
-- Trigger: Auto-populate major basin from sub-basin
-- Example: sb_california_current = TRUE → b_north_pacific = TRUE
CREATE TRIGGER populate_basin_from_subbasin
AFTER UPDATE ON literature_review
FOR EACH ROW
BEGIN
    -- California Current → North Pacific
    UPDATE literature_review
    SET b_north_pacific = TRUE
    WHERE study_id = NEW.study_id
      AND sb_california_current = TRUE;

    -- Gulf of Mexico → North Atlantic
    UPDATE literature_review
    SET b_north_atlantic = TRUE
    WHERE study_id = NEW.study_id
      AND sb_gulf_of_mexico = TRUE;

    -- [Additional mappings...]
END;
```

**Advantages of 3-Schema Approach:**

1.  **Analytical flexibility:** Separate author networks from study
    biogeography
2.  **Hierarchical aggregation:** Sub-basin → basin queries
3.  **Trend analysis:** Track research capacity growth by nation
4.  **Gap identification:** Identify under-studied regions vs
    under-represented countries

### 2.6 superorder

**Decision:** ⚠️ **BINARIZE WITH AUTO-POPULATION**

**Rationale:**

-   Chondrichthyes has 3 superorders: **Selachimorpha** (sharks), **Batoidea** (rays/skates), and **Holocephali** (chimaeras)
-   Papers may study multiple superorders (e.g., comparative phylogenetics)
-   Can auto-populate from species list using lookup table

**Schema:**

``` sql
so_selachimorpha BOOLEAN DEFAULT FALSE  -- Sharks
so_batoidea BOOLEAN DEFAULT FALSE       -- Rays & skates
so_holocephali BOOLEAN DEFAULT FALSE    -- Chimaeras
```

**Auto-Population Logic:**

``` sql
-- Lookup table: species → superorder
CREATE TABLE species_taxonomy (
    species_binomial VARCHAR(100) PRIMARY KEY,
    superorder VARCHAR(50),
    order_name VARCHAR(50),
    family VARCHAR(50)
);

-- Auto-populate superorder from species
UPDATE literature_review lr
SET so_selachimorpha = TRUE
WHERE EXISTS (
    SELECT 1 FROM species_taxonomy st
    WHERE st.superorder = 'Selachimorpha'
    AND (
        -- Check all sp_* columns for matches
        lr.sp_carcharodon_carcharias = TRUE
        OR lr.sp_prionace_glauca = TRUE
        -- ... (expand for all shark species)
    )
);
```

**Data Source for Taxonomy:**

-   **Sharkipedia** (<https://www.sharkipedia.org/>)
-   **FishBase** (<https://www.fishbase.org/>)
-   **Catalog of Fishes** (California Academy of Sciences)

### 2.7 species

**Decision:** ⚠️ **BINARIZE WIDE WITH STANDARDIZED NOMENCLATURE**

**Rationale:**

-   \~1,200+ chondrichthyan species (sharks, rays, skates, chimaeras)
-   Papers commonly study multiple species
-   Enables species-specific trend analysis
-   Supports taxonomic aggregation (genus, family, order)

**Schema:**

``` sql
-- Prefix: sp_ for "species"
-- Format: sp_{genus}_{species} (lowercase, underscores)
sp_carcharodon_carcharias BOOLEAN DEFAULT FALSE  -- White shark
sp_prionace_glauca BOOLEAN DEFAULT FALSE         -- Blue shark
sp_rhincodon_typus BOOLEAN DEFAULT FALSE         -- Whale shark
sp_carcharhinus_leucas BOOLEAN DEFAULT FALSE     -- Bull shark
-- ... (~1,200+ species)
```

**Column Naming Convention:**

-   Binomial nomenclature (genus + species)
-   All lowercase
-   Underscores replace spaces
-   No special characters (accents, hyphens)

**Data Source:**

-   **Primary:** Sharkipedia API (if available)
-   **Alternative:** FishBase species list
-   **Validation:** ITIS (Integrated Taxonomic Information System)

**Automated Species Extraction:**

``` python
import re

def extract_species_binomials(text):
    """
    Extract scientific names from text

    Pattern: Capitalized Genus + lowercase species
    Returns: set of binomials
    """
    # Pattern: Genus species (e.g., "Carcharodon carcharias")
    pattern = r'\b([A-Z][a-z]+)\s+([a-z]+)\b'
    matches = re.findall(pattern, text)

    # Validate against known species list
    valid_species = set()
    for genus, species in matches:
        binomial = f"{genus.lower()}_{species.lower()}"
        if binomial in KNOWN_SPECIES_LIST:  # Pre-loaded from Sharkipedia
            valid_species.add(binomial)

    return valid_species
```

**Storage Consideration:**

-   1,200 boolean columns ≈ 1,200 bits = 150 bytes per row (sparse)
-   For 10,000 studies: 150 bytes \* 10,000 = 1.5 MB (trivial)
-   Modern databases optimize sparse boolean columns efficiently

### 2.8 method_families & analysis_approach

**Decision:** ⚠️ **3-TIER HIERARCHICAL METHOD CLASSIFICATION**

**Rationale:**

-   Papers use multiple analytical methods across different conceptual levels
-   Method discovery is core objective of Phase 1 review
-   Enables method trend analysis over time
-   Supports discipline-method cross-tabulation
-   **3-tier structure:** method_families → parent_techniques → subtechniques

**Column Order:** `method_families` columns appear **before** `analysis_approach` columns in schema

**Schema:**

``` sql
-- TIER 1: Method Families (Prefix: mf_)
-- Broad methodological categories
mf_behavioural_observation BOOLEAN DEFAULT FALSE
mf_telemetry BOOLEAN DEFAULT FALSE
mf_genomics BOOLEAN DEFAULT FALSE
mf_diet_analysis BOOLEAN DEFAULT FALSE
mf_stable_isotopes BOOLEAN DEFAULT FALSE
mf_machine_learning BOOLEAN DEFAULT FALSE
mf_habitat_modeling BOOLEAN DEFAULT FALSE
mf_iucn_assessment BOOLEAN DEFAULT FALSE
-- ... (to be determined from Phase 2 review)

-- TIER 2: Analysis Approach / Parent Techniques (Prefix: a_)
-- Specific analytical methods
a_acoustic_telemetry BOOLEAN DEFAULT FALSE
a_satellite_tracking BOOLEAN DEFAULT FALSE
a_genetic_metabarcoding BOOLEAN DEFAULT FALSE
a_stable_isotope_analysis BOOLEAN DEFAULT FALSE
a_random_forest BOOLEAN DEFAULT FALSE
a_bayesian_modeling BOOLEAN DEFAULT FALSE
a_species_distribution_model BOOLEAN DEFAULT FALSE
a_red_list_assessment BOOLEAN DEFAULT FALSE
-- ... (to be determined from Phase 2 review)

-- TIER 3: Subtechniques (Prefix: st_)
-- Implementation-level details
st_video_analysis BOOLEAN DEFAULT FALSE
st_vertebral_sectioning BOOLEAN DEFAULT FALSE
st_dna_metabarcoding BOOLEAN DEFAULT FALSE
st_stomach_content_analysis BOOLEAN DEFAULT FALSE
st_whole_genome_sequencing BOOLEAN DEFAULT FALSE
st_microsatellites BOOLEAN DEFAULT FALSE
-- ... (to be determined from Phase 2 review)
```

**Hierarchical Method Categorization:**

Based on `outputs/method_hierarchy_table.csv`, methods are organized as:

```
discipline → method_family → parent_technique → subtechnique
```

**Examples:**
- Movement → Telemetry → Acoustic Telemetry → (specific tag types)
- Trophic → Diet Analysis → DNA Metabarcoding → (specific primers)
- Data Science → Machine Learning → Random Forest → (specific implementations)

**Note on Data Science Methods:**

Data science methods (e.g., Machine Learning, Bayesian Methods, Time Series) are cross-cutting and underpin analyses across all disciplines. These will be reviewed and potentially restructured after initial classification to reflect their foundational nature.

**Method Discovery Workflow:**

1.  **Phase 1** (Exploratory review, n=50-100 per discipline):
    -   Manually extract methods from papers
    -   Create initial method vocabulary
    -   Standardize naming conventions
2.  **Phase 2** (Main review):
    -   Use Phase 1 vocabulary as binary columns
    -   Add new methods as discovered
    -   Code searches in Shark-References for method keywords
3.  **Post-Review**:
    -   Consolidate synonymous methods
    -   Create hierarchical groupings
    -   Generate method trend analyses

### 2.9 Multi-Discipline, Multi-Technique Papers

**Challenge:** How to represent papers that span multiple disciplines with different techniques for each discipline?

**Example Problem:**
- Paper uses eDNA (genetics discipline) AND SDM (movement discipline)
- If we mark both `d_genetics_genomics = TRUE` and `d_movement_spatial = TRUE`, and also mark both `a_edna = TRUE` and `a_species_distribution_model = TRUE`, we lose the linkage of which technique pertains to which discipline

**Option A: Duplicate Rows**

Create multiple rows for the same paper, with distinct discipline-technique combinations:

```csv
study_id,paper_id,authors,year,d_genetics,d_movement,a_edna,a_sdm
1,PAPER_001,Smith et al,2023,TRUE,FALSE,TRUE,FALSE
2,PAPER_001,Smith et al,2023,FALSE,TRUE,FALSE,TRUE
```

**Pros:**
- ✅ Maintains discipline-technique linkage
- ✅ Simple to query: "genetics papers using eDNA"
- ✅ Standard SQL operations work

**Cons:**
- ❌ Loses "one row = one paper" conceptual model
- ❌ Inflates row count (need to COUNT DISTINCT paper_id for paper counts)
- ❌ Duplicate metadata (authors, year, title repeated)

**Option B: Sub-Tables Per Paper**

Create a separate relational table for discipline-technique pairs:

```sql
-- Main table (one row per paper)
CREATE TABLE literature_review (
    paper_id INTEGER PRIMARY KEY,
    authors TEXT,
    year INTEGER,
    ...
);

-- Discipline-technique pairs (many-to-one with papers)
CREATE TABLE paper_disciplines_techniques (
    id INTEGER PRIMARY KEY,
    paper_id INTEGER REFERENCES literature_review(paper_id),
    discipline VARCHAR(50),
    technique VARCHAR(100)
);
```

**Pros:**
- ✅ Maintains "one row = one paper" in main table
- ✅ No duplicate metadata
- ✅ Normalized database design

**Cons:**
- ❌ Requires JOINs for most queries (slower, more complex)
- ❌ Loses simplicity of binary column model
- ❌ More complex for reviewers to populate

**Recommendation:**

Start with **Option A (duplicate rows)** for Phase 1 review because:
1. Most papers (\~80%) likely use single discipline
2. Simpler for reviewers to understand and populate
3. Can migrate to Option B later if multi-discipline papers common
4. Query complexity remains low for most analyses

Add `paper_id` column to track unique papers:
```sql
paper_id VARCHAR(50) NOT NULL  -- Groups duplicate rows for same paper
study_id INTEGER PRIMARY KEY   -- Unique row identifier
```

**Query pattern for paper counts:**
```sql
-- Count unique papers (not rows)
SELECT COUNT(DISTINCT paper_id) FROM literature_review;

-- Count discipline-technique combinations
SELECT COUNT(*) FROM literature_review;
```

### 2.10 key_findings, strengths, weaknesses

**Decision:** ❌ **REMOVE FROM PRIMARY DATABASE**

**Rationale:**

-   **Subjective** → Not suitable for quantitative analysis
-   **Free text** → Difficult to query and aggregate
-   **Reviewer-dependent** → Inter-rater variability high
-   **Storage inefficient** → Large text fields in wide sparse table

**Alternative Approach:**

Store subjective assessments in separate **annotations table** with
many-to-one relationship:

``` sql
CREATE TABLE study_annotations (
    annotation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    study_id INTEGER REFERENCES literature_review(study_id),
    reviewer VARCHAR(100),
    annotation_type VARCHAR(50),  -- 'key_finding', 'strength', 'weakness'
    annotation_text TEXT,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Advantages:**

-   Multiple reviewers can annotate same study
-   Annotations optional (no sparse NULL fields in main table)
-   Easy to filter by annotation type or reviewer
-   Can add structured tags later (e.g., sentiment analysis)

### 2.11 shark_refs_pdf

**Decision:** ✅ **APPROVED AS FOREIGN KEY**

**Rationale:**

-   Links to Shark-References database
-   Enables cross-database queries
-   Supports automated PDF retrieval (if API available)

**Schema:**

``` sql
shark_refs_id VARCHAR(100) UNIQUE  -- SharkReferences unique identifier
```

**Usage:**

``` sql
-- Query SharkReferences for full citation
SELECT * FROM shark_references_external
WHERE shark_ref_id = 'SR12345';
```

------------------------------------------------------------------------

## 3. Complete Recommended Schema

### 3.1 Core Metadata Table

``` sql
CREATE TABLE literature_review (
    -- Primary key
    study_id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Audit trail
    reviewer VARCHAR(100) NOT NULL,
    review_date DATE NOT NULL DEFAULT CURRENT_DATE,
    last_modified_by VARCHAR(100),
    last_modified_date TIMESTAMP,

    -- Bibliographic metadata
    authors TEXT NOT NULL,
    year INTEGER,
    title TEXT NOT NULL,
    journal VARCHAR(255),
    doi VARCHAR(100) UNIQUE,
    abstract TEXT,
    keywords TEXT,

    -- Study classification
    study_type VARCHAR(20) CHECK (study_type IN ('Primary', 'Systematic Review', 'Meta-analysis')),
    n_studies INTEGER,  -- For reviews/meta-analyses: count of studies reviewed/analysed

    -- External references
    shark_refs_id VARCHAR(100) UNIQUE,
    citation_count INTEGER,
    scholar_url TEXT,

    -- Timestamps
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3.2 Discipline Columns (8 binary)

``` sql
ALTER TABLE literature_review ADD COLUMN d_biology_health BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN d_behaviour_sensory BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN d_trophic_ecology BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN d_genetics_genomics BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN d_movement_spatial BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN d_fisheries_management BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN d_conservation_policy BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN d_data_science BOOLEAN DEFAULT FALSE;
```

### 3.3 Author Institution Nations (\~197 binary)

``` sql
-- Generated from ISO 3166-1 alpha-2 codes
ALTER TABLE literature_review ADD COLUMN auth_us BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN auth_au BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN auth_gb BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN auth_za BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN auth_ca BOOLEAN DEFAULT FALSE;
-- ... (192 more)
```

### 3.4 Ocean Basins (9 binary)

``` sql
ALTER TABLE literature_review ADD COLUMN b_north_atlantic BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN b_south_atlantic BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN b_north_pacific BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN b_south_pacific BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN b_indian_ocean BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN b_southern_ocean BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN b_arctic_ocean BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN b_mediterranean_sea BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN b_caribbean_sea BOOLEAN DEFAULT FALSE;
```

### 3.5 Sub-Basins (\~66 binary, optional)

``` sql
ALTER TABLE literature_review ADD COLUMN sb_california_current BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN sb_gulf_of_mexico BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN sb_benguela_current BOOLEAN DEFAULT FALSE;
-- ... (63 more)
```

### 3.6 Superorders (3 binary)

``` sql
ALTER TABLE literature_review ADD COLUMN so_selachimorpha BOOLEAN DEFAULT FALSE;  -- Sharks
ALTER TABLE literature_review ADD COLUMN so_batoidea BOOLEAN DEFAULT FALSE;       -- Rays & skates
ALTER TABLE literature_review ADD COLUMN so_holocephali BOOLEAN DEFAULT FALSE;    -- Chimaeras
```

### 3.7 Species (\~1,200 binary)

``` sql
ALTER TABLE literature_review ADD COLUMN sp_carcharodon_carcharias BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN sp_prionace_glauca BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN sp_rhincodon_typus BOOLEAN DEFAULT FALSE;
-- ... (~1,197 more)
```

### 3.8 Method Families (\~30-40 binary, from Phase 2)

``` sql
-- TIER 1: Method Families (mf_ prefix)
ALTER TABLE literature_review ADD COLUMN mf_behavioural_observation BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN mf_telemetry BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN mf_genomics BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN mf_diet_analysis BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN mf_stable_isotopes BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN mf_machine_learning BOOLEAN DEFAULT FALSE;
-- ... (~30-40 method families total)
```

### 3.9 Analysis Approaches / Parent Techniques (\~50-70 binary, from Phase 2)

``` sql
-- TIER 2: Analysis Approach (a_ prefix)
ALTER TABLE literature_review ADD COLUMN a_acoustic_telemetry BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN a_satellite_tracking BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN a_stable_isotope_analysis BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN a_genetic_metabarcoding BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN a_random_forest BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN a_species_distribution_model BOOLEAN DEFAULT FALSE;
-- ... (~50-70 parent techniques total)
```

### 3.10 Subtechniques (\~20-30 binary, from Phase 2)

``` sql
-- TIER 3: Subtechniques (st_ prefix)
ALTER TABLE literature_review ADD COLUMN st_video_analysis BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN st_vertebral_sectioning BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN st_dna_metabarcoding BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN st_stomach_content_analysis BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN st_whole_genome_sequencing BOOLEAN DEFAULT FALSE;
-- ... (~20-30 subtechniques total)
```

### 3.11 Summary Statistics

**Total Columns:**

-   Core metadata: \~22 columns (includes n_studies, paper_id)
-   Disciplines: 8 columns
-   Author nations: 197 columns
-   Ocean basins: 9 columns
-   Sub-basins: 66 columns (optional)
-   Superorders: 3 columns (includes Holocephali for chimaeras)
-   Species: 1,200 columns
-   Method families: 35 columns (estimated from Phase 2)
-   Analysis approaches (parent techniques): 60 columns (estimated from Phase 2)
-   Subtechniques: 25 columns (estimated from Phase 2)

**TOTAL: \~1,625 columns** (or \~1,559 without sub-basins)

**Method Hierarchy Reference:** See `outputs/method_hierarchy_table.csv` for current 3-tier classification

**Technique Count Documentation:** `outputs/abstracts_technique_counts.csv` counts the number of unique techniques mentioned per presentation (paper), not the total mentions across all papers

------------------------------------------------------------------------

## 4. Wide Sparse Database Considerations

### 4.1 Is This A Problem?

**Short Answer:** Not for modern columnar databases like DuckDB or
Parquet.

**Long Answer:**

#### Traditional Row-Oriented Databases (MySQL, PostgreSQL, SQLite)

-   ❌ **Performance issues** with \>1,000 columns
-   ❌ **Storage inefficiency** for sparse boolean data
-   ❌ **Query complexity** (SELECT \* returns massive rows)
-   ❌ **Schema migration difficulties** (adding columns requires table
    locks)

**Example Storage Calculation (PostgreSQL):**

-   1,652 columns \* 1 byte per boolean = 1,652 bytes per row
-   10,000 studies = 16.52 MB (small, but inefficient)
-   NULL storage overhead: \~1 bit per column = 207 bytes per row
-   **Total: \~18.6 MB** for 10,000 rows (acceptable, but suboptimal)

#### Columnar Databases (DuckDB, Parquet, Arrow)

-   ✅ **Optimized for sparse data** (run-length encoding)
-   ✅ **Fast analytical queries** (scan only needed columns)
-   ✅ **Compression-friendly** (sparse boolean columns compress \>90%)
-   ✅ **Schema-flexible** (easy to add columns)

**Example Storage Calculation (Parquet):**

-   Sparse boolean columns compress to \~0.1 bits per value (via
    run-length encoding)
-   1,652 columns \* 0.1 bits \* 10,000 rows = 2.065 MB
-   **Total: \~2 MB** for 10,000 rows (83% reduction vs PostgreSQL)

### 4.2 Database Format Recommendation

**Recommended:** **DuckDB + Parquet**

**Rationale:**

1.  **DuckDB:**
    -   In-process SQL database (no server setup)
    -   Native Parquet support
    -   R integration via `{duckdb}` and `{duckplyr}`
    -   Python integration via `duckdb` package
    -   OLAP-optimized (analytics, not transactions)
    -   Zero configuration for collaborators
2.  **Parquet:**
    -   Columnar storage format
    -   Excellent compression for sparse data
    -   Cross-platform (R, Python, Julia, etc.)
    -   Can be queried directly (no import needed)
    -   Cloud-friendly (AWS, GCP, Azure native support)

**Alternative:** **Arrow IPC (Feather v2)**

-   Even faster than Parquet for local workflows
-   Same compression benefits
-   DuckDB supports Arrow natively
-   **Recommendation:** Use Arrow for active development, Parquet for
    archival

### 4.3 Workflow Recommendation

#### Phase 1: Initial Development (CSV)

-   Start with CSV for simplicity and universal compatibility
-   Easy for reviewers to edit in Excel/LibreOffice
-   Version control with git (track changes)

``` r
# R workflow
library(readr)
df <- read_csv("literature_review.csv")
```

#### Phase 2: Scale-Up (DuckDB + Parquet)

-   Import CSV to DuckDB
-   Export to Parquet for storage/sharing
-   Query Parquet directly with DuckDB (no import needed)

``` r
# R workflow
library(duckdb)
library(dplyr)
library(duckplyr)

# Connect to DuckDB
con <- dbConnect(duckdb::duckdb(), dbdir = "literature_review.duckdb")

# Import CSV
dbExecute(con, "
  CREATE TABLE literature_review AS
  SELECT * FROM read_csv_auto('literature_review.csv')
")

# Export to Parquet (compressed, portable)
dbExecute(con, "
  COPY literature_review TO 'literature_review.parquet' (FORMAT PARQUET)
")

# Query Parquet directly (no import!)
df <- tbl(con, "read_parquet('literature_review.parquet')") %>%
  filter(d_genetics_genomics == TRUE) %>%
  select(study_id, authors, year, title) %>%
  collect()
```

**Python equivalent:**

``` python
import duckdb

# Query Parquet directly
df = duckdb.query("""
    SELECT study_id, authors, year, title
    FROM read_parquet('literature_review.parquet')
    WHERE d_genetics_genomics = TRUE
""").to_df()
```

#### Phase 3: Distributed Collaboration (Parquet + Git LFS)

-   Store Parquet files in Git LFS (large file storage)
-   Collaborators pull latest Parquet
-   Each reviewer edits CSV subset, merged to master Parquet

``` bash
# Enable Git LFS for Parquet files
git lfs track "*.parquet"
git add .gitattributes
git commit -m "Track Parquet files with LFS"

# Add and commit Parquet
git add literature_review.parquet
git commit -m "Update literature review database"
git push
```

#### Phase 4: Analysis & Reporting (duckplyr)

-   Use `{duckplyr}` for dplyr-compatible DuckDB queries
-   Automatic query optimization
-   Works seamlessly with existing dplyr code

``` r
library(duckplyr)

# Read Parquet as dplyr-compatible tibble
df <- duckplyr_df_from_parquet("literature_review.parquet")

# Standard dplyr syntax, DuckDB execution
result <- df %>%
  filter(year >= 2020) %>%
  group_by(year) %>%
  summarise(
    total_studies = n(),
    genetics = sum(d_genetics_genomics, na.rm = TRUE),
    movement = sum(d_movement_spatial, na.rm = TRUE)
  ) %>%
  collect()
```

------------------------------------------------------------------------

## 5. Schema Implementation Scripts

### 5.1 Generate Country Columns (R)

``` r
library(dplyr)
library(stringr)

# Get ISO country codes
countries <- ISOcodes::ISO_3166_1 %>%
  select(Alpha_2, Name) %>%
  mutate(column_name = paste0("auth_", str_to_lower(Alpha_2)))

# Generate SQL ALTER statements
country_sql <- countries %>%
  mutate(sql = sprintf(
    "ALTER TABLE literature_review ADD COLUMN %s BOOLEAN DEFAULT FALSE;",
    column_name
  )) %>%
  pull(sql)

# Write to file
writeLines(country_sql, "sql/add_country_columns.sql")
```

### 5.2 Generate Species Columns (R)

``` r
library(rfishbase)

# Get all chondrichthyan species
sharks <- species_list(Class = "Elasmobranchii")

# Format as column names
species_cols <- sharks %>%
  mutate(
    genus_species = paste(str_to_lower(Genus), str_to_lower(Species), sep = "_"),
    column_name = paste0("sp_", genus_species),
    sql = sprintf(
      "ALTER TABLE literature_review ADD COLUMN %s BOOLEAN DEFAULT FALSE;",
      column_name
    )
  )

# Write to file
writeLines(species_cols$sql, "sql/add_species_columns.sql")
```

### 5.3 Create DuckDB Database with Full Schema (R)

``` r
library(duckdb)

# Connect to DuckDB
con <- dbConnect(duckdb::duckdb(), dbdir = "literature_review.duckdb")

# Execute schema creation scripts
dbExecute(con, readr::read_file("sql/create_core_table.sql"))
dbExecute(con, readr::read_file("sql/add_discipline_columns.sql"))
dbExecute(con, readr::read_file("sql/add_country_columns.sql"))
dbExecute(con, readr::read_file("sql/add_basin_columns.sql"))
dbExecute(con, readr::read_file("sql/add_species_columns.sql"))
dbExecute(con, readr::read_file("sql/add_analysis_columns.sql"))

# Create indexes for common queries
dbExecute(con, "CREATE INDEX idx_year ON literature_review(year)")
dbExecute(con, "CREATE INDEX idx_doi ON literature_review(doi)")
dbExecute(con, "CREATE INDEX idx_study_type ON literature_review(study_type)")

# Disconnect
dbDisconnect(con, shutdown = TRUE)
```

------------------------------------------------------------------------

## 6. Query Examples

### 6.1 Multi-Discipline Papers

``` sql
-- Papers spanning Genetics + Conservation
SELECT study_id, authors, year, title
FROM literature_review
WHERE d_genetics_genomics = TRUE
  AND d_conservation_policy = TRUE;
```

### 6.2 Geographic Trends

``` sql
-- US-led research in the Caribbean
SELECT COUNT(*) as study_count
FROM literature_review
WHERE auth_us = TRUE
  AND b_caribbean_sea = TRUE;
```

### 6.3 Method Co-Occurrence

``` sql
-- Papers using both telemetry and isotopes
SELECT study_id, authors, year, title
FROM literature_review
WHERE a_acoustic_telemetry = TRUE
  AND a_stable_isotopes = TRUE;
```

### 6.4 Species-Specific Method Trends

``` sql
-- White shark studies using satellite tracking over time
SELECT year, COUNT(*) as papers
FROM literature_review
WHERE sp_carcharodon_carcharias = TRUE
  AND a_satellite_tracking = TRUE
GROUP BY year
ORDER BY year;
```

### 6.5 Multi-National Collaborations

``` sql
-- Count co-authorship patterns (3+ countries)
SELECT study_id, authors, year,
       (auth_us::int + auth_au::int + auth_gb::int + auth_za::int +
        auth_ca::int + auth_nz::int + auth_br::int + auth_mx::int) as num_countries
FROM literature_review
HAVING num_countries >= 3
ORDER BY num_countries DESC;
```

------------------------------------------------------------------------

## 7. Summary & Recommendations

### ✅ Approved Schema Design

1.  **Wide sparse table** with binary columns for multi-label
    classification
2.  **Hierarchical geographic schema:** Author nations + basins +
    sub-basins
3.  **Binarized species and methods** for flexible querying
4.  **Separate annotations table** for subjective assessments

### ✅ Recommended Database Stack

-   **Format:** Parquet (storage) + DuckDB (queries)
-   **R workflow:** `{duckdb}` + `{duckplyr}`
-   **Python workflow:** `duckdb` package
-   **Collaboration:** Git LFS for Parquet version control

### ✅ Implementation Approach

1.  **Phase 1:** Start with CSV template for reviewers
2.  **Phase 2:** Import to DuckDB, export to Parquet
3.  **Phase 3:** Distribute Parquet via Git LFS
4.  **Phase 4:** Analyze with duckplyr/duckdb

### 🎯 Key Advantages

-   ✅ **Future-proof:** Easy to add columns without migration
-   ✅ **Query-friendly:** Standard SQL for all analyses
-   ✅ **Storage-efficient:** Parquet compresses sparse data \>90%
-   ✅ **Collaborative:** CSV editing, Parquet sharing
-   ✅ **Cross-platform:** Works in R, Python, Julia, etc.
-   ✅ **Scalable:** Handles 10K+ studies efficiently

### ⚠️ Trade-Offs Accepted

-   ❌ Wide schema (\~1,652 columns) less human-readable
-   ❌ Normalized design would be more "elegant" (but less practical)
-   ❌ Requires DuckDB installation (but it's simple)

------------------------------------------------------------------------

## 8. Next Steps

1.  **Generate full SQL schema** from ISO/FishBase/LME sources
2.  **Create template CSV** with all columns
3.  **Build import/export scripts** (CSV ↔ Parquet ↔ DuckDB)
4.  **Develop data entry interface** (R Shiny or web form?)
5.  **Implement automated extraction** for study_type, species, methods
6.  **Set up Git LFS repository** for collaborative Parquet storage
7.  **Create analysis templates** in duckplyr/duckdb

------------------------------------------------------------------------

## References

-   **ISO 3166-1:** <https://www.iso.org/iso-3166-country-codes.html>
-   **Marine Regions:** <https://www.marineregions.org/>
-   **Large Marine Ecosystems:** <https://www.lme.noaa.gov/>
-   **Sharkipedia:** <https://www.sharkipedia.org/>
-   **FishBase:** <https://www.fishbase.org/>
-   **DuckDB:** <https://duckdb.org/>
-   **Parquet:** <https://parquet.apache.org/>
-   **duckplyr:** <https://duckdblabs.github.io/duckplyr/>
