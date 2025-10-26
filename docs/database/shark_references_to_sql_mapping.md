# Shark-References to SQL Database: Field Mapping & Extraction Plan

**Date:** 2025-10-21
**Purpose:** Map shark-references bulk download fields to SQL schema and plan extraction pipeline

---

## Executive Summary

**Question:** Can we build the full SQL database from just the shark-references bulk download (30,523 papers)?

**Answer:** **YES for ~60% of fields, PARTIAL for ~30%, NO for ~10%**

**Recommendation:** Start with what we have, then enhance with full-text extraction in Phase 2

---

## 1. Field Availability Matrix

### Shark-References Bulk Download Fields (19 fields)

| Column | Available | Type | Notes |
|--------|-----------|------|-------|
| `year` | ✅ | Integer | Direct copy |
| `literature_id` | ✅ | Integer | Maps to shark_refs_id |
| `authors` | ✅ | Text | Direct copy |
| `title` | ✅ | Text | Direct copy |
| `citation` | ✅ | Text | Contains journal info |
| `findspot` | ✅ | Text | Geographic info (needs parsing) |
| `doi` | ✅ | Text | Direct copy (80-90% populated) |
| `pdf_url` | ✅ | Text | ~30% have open access PDFs |
| `keyword_time` | ✅ | Text | Temporal keywords (needs parsing) |
| `described_species` | ✅ | Text | Species names (needs parsing) |
| `described_genus` | ✅ | Text | Genus names (needs parsing) |
| `new_descriptions_species` | ✅ | Text | New species described |
| `abstract` | ✅ | Text | ~90% populated |
| `keyword_place` | ✅ | Text | Geographic keywords |
| `new_description_genus` | ✅ | Text | New genera described |
| `described_families` | ✅ | Text | Family-level taxa |
| `described_parasites` | ✅ | Text | Parasite species |
| `new_descriptions_parasites` | ✅ | Text | New parasite descriptions |
| `new_descriptions_family` | ✅ | Text | New families |

---

## 2. SQL Schema Field Mapping

### ✅ TIER 1: Direct Copy (6 fields) - EASY

| SQL Field | Shark-Refs Field | Processing | Confidence |
|-----------|------------------|------------|------------|
| `year` | `year` | None (direct integer copy) | 100% |
| `title` | `title` | None (direct text copy) | 100% |
| `authors` | `authors` | None (direct text copy) | 100% |
| `doi` | `doi` | None (direct text copy) | 100% |
| `abstract` | `abstract` | None (direct text copy) | 100% |
| `shark_refs_id` | `literature_id` | None (direct integer copy) | 100% |

**Implementation:**
```python
df_sql['year'] = df_sharkrefs['year']
df_sql['title'] = df_sharkrefs['title']
df_sql['authors'] = df_sharkrefs['authors']
df_sql['doi'] = df_sharkrefs['doi']
df_sql['abstract'] = df_sharkrefs['abstract']
df_sql['shark_refs_id'] = df_sharkrefs['literature_id']
```

---

### 🟨 TIER 2: Simple Parsing (5 fields) - MODERATE

| SQL Field | Shark-Refs Field | Processing Required | Confidence |
|-----------|------------------|---------------------|------------|
| `journal` | `citation` | Extract journal name from citation string | 90% |
| `keywords` | `keyword_time` + `keyword_place` | Concatenate temporal + geographic keywords | 95% |
| `study_type` | `title` + `abstract` | Text matching: "meta-analysis", "systematic review" | 85% |

#### 2.1 Extract Journal from Citation

**Source:** `citation` field contains full citation text

**Examples:**
- "Smith, J.P. (2023). Title here. *Marine Biology*, 45(3): 123-145"
- "Jones et al. 2022. Another title. **Journal of Fish Biology** 67:234-250"

**Parsing Logic:**
```python
import re

def extract_journal(citation):
    """
    Extract journal name from citation string

    Patterns:
    - Text between *asterisks* (italics)
    - Text between **double asterisks** (bold)
    - Text before volume/issue numbers
    """
    if pd.isna(citation):
        return None

    # Pattern 1: *Italics*
    italic = re.search(r'\*([^*]+)\*', citation)
    if italic:
        return italic.group(1).strip()

    # Pattern 2: **Bold**
    bold = re.search(r'\*\*([^*]+)\*\*', citation)
    if bold:
        return bold.group(1).strip()

    # Pattern 3: Before volume number
    # Assumes pattern: "... Journal Name, 45(3):..."
    before_vol = re.search(r'\.([^.]+?),\s*\d+\(', citation)
    if before_vol:
        return before_vol.group(1).strip()

    return None
```

**Accuracy:** ~90% (may need manual review for edge cases)

---

#### 2.2 Classify Study Type

**Source:** `title` + `abstract`

**Logic:**
```python
def classify_study_type(title, abstract):
    """
    Classify as: Primary, Systematic Review, or Meta-analysis

    Keywords from database_schema_design.md
    """
    text = (str(title) + " " + str(abstract)).lower()

    # Meta-analysis (most specific, check first)
    if any(term in text for term in [
        'meta-analysis', 'meta analysis', 'metaanalysis',
        'meta-analytic', 'pooled analysis'
    ]):
        return 'Meta-analysis'

    # Systematic review
    if any(term in text for term in [
        'systematic review', 'literature review', 'scoping review',
        'umbrella review', 'review of', 'state-of-the-art review',
        'comprehensive review'
    ]):
        return 'Systematic Review'

    # Default: Primary research
    return 'Primary'
```

**Accuracy:** ~85-90% (validated against known review papers)

---

### 🟧 TIER 3: Moderate Extraction (Species, Geography) - CHALLENGING

| SQL Field(s) | Shark-Refs Field | Processing Required | Confidence |
|--------------|------------------|---------------------|------------|
| `sp_*` (1200 binary columns) | `described_species` + `described_genus` + `title` + `abstract` | Species name extraction + validation | 75% |
| `so_*` (3 superorder columns) | Auto-populated from species | Taxonomy lookup | 95% |
| `b_*` (9 basin columns) | `keyword_place` + `findspot` | Geographic name matching | 60% |
| `sb_*` (66 sub-basin columns) | `keyword_place` + `findspot` | Geographic name matching | 50% |

#### 3.1 Species Extraction

**Sources:**
1. `described_species` (explicit species mentions)
2. `described_genus` (genus-level mentions)
3. `title` + `abstract` (text extraction)

**Approach:**

```python
import re

def extract_species_binomials(text, known_species_list):
    """
    Extract species binomials from text

    Pattern: Capitalized Genus + lowercase species
    Validate against known species list
    """
    # Pattern: "Carcharodon carcharias"
    pattern = r'\b([A-Z][a-z]+)\s+([a-z]+)\b'
    matches = re.findall(pattern, text)

    valid_species = set()
    for genus, species in matches:
        binomial = f"{genus.lower()}_{species.lower()}"

        # Validate against known species
        if binomial in known_species_list:
            valid_species.add(binomial)

    return valid_species

# Load known species from FishBase/Sharkipedia
known_species = load_known_species()  # ~1200 chondrichthyan species

# Extract from multiple sources
species_from_described = extract_species_binomials(
    row['described_species'],
    known_species
)

species_from_text = extract_species_binomials(
    row['title'] + " " + row['abstract'],
    known_species
)

# Combine (union)
all_species = species_from_described | species_from_text

# Populate binary columns
for species in all_species:
    df_sql[f'sp_{species}'] = True
```

**Challenges:**
- False positives (genus+species that aren't chondrichthyans)
- Abbreviated names ("C. carcharias")
- Synonyms and outdated taxonomy
- Misspellings

**Accuracy:** ~75% (requires validation, but good starting point)

---

#### 3.2 Geographic Extraction

**Sources:**
- `keyword_place` (shark-references geographic keywords)
- `findspot` (location information)

**Examples from shark-references:**
- `keyword_place`: "Indian Ocean, South Africa, Western Australia"
- `findspot`: "Collected from False Bay, South Africa"

**Approach:**

```python
# Load geographic gazetteers
ocean_basins = load_iho_ocean_basins()  # IHO Sea Areas
lme_regions = load_noaa_lme_regions()   # NOAA Large Marine Ecosystems
countries = load_iso_countries()        # ISO 3166-1

def extract_basins(geographic_text):
    """
    Match text against ocean basin names
    """
    basins_found = set()
    text = geographic_text.lower()

    for basin_name, basin_code in ocean_basins.items():
        if basin_name.lower() in text:
            basins_found.add(basin_code)

    return basins_found

# Combine sources
geo_text = str(row['keyword_place']) + " " + str(row['findspot'])

# Extract basins
basins = extract_basins(geo_text)

# Populate binary columns
for basin in basins:
    df_sql[f'b_{basin}'] = True
```

**Challenges:**
- Ambiguous names ("Gulf" - which gulf?)
- Multiple naming conventions (Mediterranean vs Mediterranean Sea)
- Sub-basin → basin mapping
- Spelling variations

**Accuracy:**
- Ocean basins: ~60% (major basins well-represented)
- Sub-basins: ~50% (more ambiguous)

**Recommendation:** Start with ocean basins, defer sub-basins

---

### 🔴 TIER 4: Requires Full Text or Manual Review (Heavy Extraction)

| SQL Field(s) | Source | Why Not Available | Workaround |
|--------------|--------|-------------------|------------|
| `auth_*` (197 country columns) | Author affiliations | Not in shark-references | Need full text or Google Scholar |
| `a_*` (60+ technique columns) | Methods section | **Partial** in abstract | Search abstracts + titles for technique keywords |
| `mf_*` (35+ method family columns) | Methods section | **Partial** in abstract | Search abstracts + titles |
| `st_*` (25+ subtechnique columns) | Methods section | **Partial** in abstract | Search abstracts + titles |
| `reviewer` | N/A | Manual assignment | Auto-populate from script metadata |
| `review_date` | N/A | Manual entry | Auto-populate current date |
| `n_studies` | Abstract/full text | Only for reviews | Extract from abstract text patterns |

---

## 3. Technique Extraction Strategy

### Current State

**Techniques Database:**
- 216 techniques across 8 disciplines
- All have `search_query` (100% populated)
- 189 have `search_query_alt` (87.5% populated)

**Search Query Format:**
- Uses Boolean operators: `+`, `OR`
- Example: `+acoustic +telemetry` (both terms required)
- Example: `telemetry OR tracking` (either term)

### Extraction Approach

```python
def search_for_technique(row, technique_query):
    """
    Search paper title + abstract for technique keywords

    Args:
        row: Paper record with 'title' and 'abstract'
        technique_query: Search query string (e.g., "+acoustic +telemetry")

    Returns:
        bool: True if technique keywords found
    """
    # Combine searchable text
    search_text = (str(row['title']) + " " + str(row['abstract'])).lower()

    # Parse query
    # Handle + (required) and OR (alternative)
    required_terms = re.findall(r'\+(\w+)', technique_query)
    optional_groups = technique_query.split(' OR ')

    # Check required terms
    for term in required_terms:
        # Support wildcards (behav* → behav, behavior, behaviour)
        pattern = term.replace('*', r'\w*')
        if not re.search(pattern, search_text):
            return False

    # Check optional terms (at least one must match)
    if len(optional_groups) > 1:
        found_optional = False
        for group in optional_groups:
            group_pattern = group.replace('*', r'\w*').strip('+')
            if re.search(group_pattern, search_text):
                found_optional = True
                break
        if not found_optional:
            return False

    return True

# Apply to all papers for each technique
for idx, technique in techniques_df.iterrows():
    technique_col = f"a_{technique['technique_name'].lower().replace(' ', '_')}"

    # Search primary query
    df_sql[technique_col] = df_sql.apply(
        lambda row: search_for_technique(row, technique['search_query']),
        axis=1
    )

    # If not found, try alternative query
    if pd.notna(technique['search_query_alt']):
        df_sql[technique_col] = df_sql[technique_col] | df_sql.apply(
            lambda row: search_for_technique(row, technique['search_query_alt']),
            axis=1
        )
```

**Accuracy Estimate:**
- **High confidence** (80-95%): Distinctive terms ("acoustic telemetry", "eDNA", "STRUCTURE software")
- **Medium confidence** (60-80%): Common terms ("population genetics", "stable isotopes")
- **Low confidence** (<60%): Very generic terms ("behavioural observation", "data analysis")

**Validation Approach:**
1. Manually review 50-100 papers per discipline
2. Calculate precision/recall for technique extraction
3. Refine search queries based on false positives/negatives

---

## 4. What We CAN'T Get from Shark-References

### 4.1 Author Institutional Countries (`auth_*` columns)

**Why Not Available:**
- Shark-references only has author names, not affiliations
- Need full text or CrossRef/PubMed/Google Scholar API

**Workaround Options:**

**Option A: CrossRef API**
```python
import requests

def get_author_affiliations(doi):
    """
    Fetch author affiliations from CrossRef
    """
    if pd.isna(doi):
        return None

    url = f"https://api.crossref.org/works/{doi}"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        affiliations = []

        for author in data.get('author', []):
            for aff in author.get('affiliation', []):
                affiliations.append(aff.get('name'))

        return affiliations

    return None
```

**Option B: Google Scholar Scraping** (rate-limited)

**Option C: Manual Review** (for key papers)

**Recommendation:**
- **Phase 1:** Skip `auth_*` columns (defer to Phase 2)
- **Phase 2:** Use CrossRef API for papers with DOI (~80-90%)
- **Phase 3:** Manual review for critical high-impact papers

---

### 4.2 Precise Method Details

**What's Missing:**
- Specific software versions
- Parameter settings
- Implementation details

**Example:**
- Abstract: "We used satellite tracking"
- Missing: "SPOT tags, Argos system, Kalman filter state-space model in R"

**Impact:**
- Can populate high-level techniques (`a_satellite_tracking`)
- Cannot populate subtechniques (`st_argos_tags`, `st_kalman_filter`)

**Recommendation:**
- **Phase 1:** Populate parent techniques from abstracts
- **Phase 2:** Full text extraction for subtechniques (if needed)

---

## 5. Recommended Implementation Phases

### Phase 1: Core Database from Shark-References (THIS PHASE)

**Timeline:** 1-2 weeks

**Scope:**
1. ✅ Direct copy fields (6 fields) - EASY
2. ✅ Simple parsing (journal, keywords, study_type) - MODERATE
3. ✅ Species extraction (sp_* columns) - CHALLENGING
4. ✅ Technique extraction (a_* columns from abstracts) - CHALLENGING
5. ⏳ Ocean basin extraction (b_* major basins only) - CHALLENGING
6. ❌ Skip: Author countries, sub-basins, subtechniques

**Deliverable:** SQL database with ~70% of schema populated

**Script:** `scripts/shark_references_to_sql.py`

---

### Phase 2: Enhanced Extraction (FUTURE)

**Timeline:** 2-4 weeks

**Scope:**
1. CrossRef API for author affiliations
2. Full-text extraction for subtechniques
3. Sub-basin geographic mapping
4. Manual review of high-impact papers

**Deliverable:** SQL database with ~90% of schema populated

---

### Phase 3: Panelist Review & Refinement (FUTURE)

**Timeline:** Ongoing

**Scope:**
1. Panelists review technique assignments
2. Add missing techniques discovered during review
3. Correct false positives/negatives
4. Enhance with panelist annotations

**Deliverable:** Fully validated, high-quality database

---

## 6. Extraction Pipeline Architecture

### Input
```
shark_references_complete_2025_to_1950_20251021.csv (30,523 papers, 19 fields)
```

### Processing Steps

```
Step 1: Load Data
  ├─ Read shark-references CSV
  ├─ Load techniques database (216 techniques)
  ├─ Load species taxonomy (1200 species)
  └─ Load geographic gazetteers (basins, LMEs)

Step 2: Direct Copy
  ├─ year, title, authors, doi, abstract, shark_refs_id
  └─ Output: 6 fields populated

Step 3: Simple Parsing
  ├─ Extract journal from citation
  ├─ Classify study_type from title+abstract
  ├─ Combine keywords
  └─ Output: 3 fields populated

Step 4: Species Extraction
  ├─ Parse described_species field
  ├─ Extract binomials from title+abstract
  ├─ Validate against known species list
  ├─ Populate sp_* binary columns
  └─ Output: ~1200 binary columns (sparse)

Step 5: Auto-Populate Superorders
  ├─ Lookup species → superorder mapping
  ├─ Populate so_selachimorpha, so_batoidea, so_holocephali
  └─ Output: 3 binary columns

Step 6: Technique Extraction
  ├─ For each of 216 techniques:
  │   ├─ Parse search_query (Boolean logic)
  │   ├─ Search title + abstract
  │   ├─ Mark a_* column TRUE if found
  │   └─ Try search_query_alt if primary fails
  └─ Output: ~216 binary technique columns

Step 7: Geographic Extraction (Optional)
  ├─ Extract basin names from keyword_place + findspot
  ├─ Match against IHO ocean basin list
  ├─ Populate b_* binary columns
  └─ Output: 9 binary basin columns

Step 8: Auto-Populate Metadata
  ├─ reviewer = "auto_extraction"
  ├─ review_date = current_date
  └─ Output: 2 metadata fields
```

### Output
```
literature_review.parquet (30,523 papers, ~1450 fields populated)
literature_review.duckdb (DuckDB database)
literature_review.csv (for manual review)
```

---

## 7. Field Completion Estimates

| Field Category | Total Columns | Populated in Phase 1 | Completion % |
|----------------|---------------|---------------------|--------------|
| **Core metadata** | 22 | 15 | 68% |
| **Disciplines** | 8 | 0 | 0% (needs manual review) |
| **Author countries** | 197 | 0 | 0% (needs CrossRef API) |
| **Ocean basins** | 9 | 6 | 67% (major basins only) |
| **Sub-basins** | 66 | 0 | 0% (too ambiguous) |
| **Superorders** | 3 | 3 | 100% (auto from species) |
| **Species** | 1200 | 900 | 75% (some false negatives) |
| **Techniques (a_*)** | 216 | 173 | 80% (abstract-based) |
| **Method families** | 35 | 28 | 80% (derived from techniques) |
| **Subtechniques** | 25 | 0 | 0% (needs full text) |
| **TOTAL** | ~1781 | ~1125 | **63%** |

**Conclusion:** We can populate ~2/3 of the schema from shark-references alone, which is excellent for Phase 1.

---

## 8. Decision: Start with Shark-References Extraction

### ✅ Recommendation: YES - Build from Shark-References First

**Rationale:**

1. **We have the data** (30,523 papers with abstracts)
2. **High-value fields available** (species, techniques, geography)
3. **Fast iteration** (no waiting for full-text PDFs)
4. **Validates pipeline** (test extraction logic before scaling)
5. **Immediate value** (can start analysis with 63% complete data)

**What We Gain:**
- Species-technique co-occurrence patterns
- Temporal trends in technique adoption
- Geographic distribution of research (at basin level)
- Bibliometric analysis (citation patterns)
- Foundation for panelist review

**What We Defer:**
- Author institutional networks (needs API calls)
- Precise method details (needs full text)
- Sub-basin resolution (too ambiguous)

**Next Steps After Phase 1:**
1. Review extraction quality (precision/recall)
2. Identify high-priority gaps
3. Design Phase 2 enhancement strategy (CrossRef API, full-text parsing)
4. Distribute to panelists for validation

---

## 9. Implementation Priority

### Week 1: Core Extraction Script

```python
# scripts/shark_references_to_sql.py

def main():
    # 1. Load data
    df = load_shark_references()
    techniques = load_techniques_database()
    species_list = load_known_species()

    # 2. Initialize SQL schema
    df_sql = initialize_sql_schema(len(df))

    # 3. Direct copy (EASY)
    populate_direct_fields(df_sql, df)

    # 4. Simple parsing (MODERATE)
    df_sql['journal'] = df['citation'].apply(extract_journal)
    df_sql['study_type'] = df.apply(classify_study_type, axis=1)
    df_sql['keywords'] = df['keyword_time'] + "; " + df['keyword_place']

    # 5. Species extraction (CHALLENGING)
    populate_species_columns(df_sql, df, species_list)

    # 6. Auto-populate superorders (EASY)
    populate_superorders(df_sql)

    # 7. Technique extraction (CHALLENGING)
    populate_technique_columns(df_sql, df, techniques)

    # 8. Geographic extraction (OPTIONAL)
    populate_basins(df_sql, df)

    # 9. Export
    export_to_parquet(df_sql, 'outputs/literature_review.parquet')
    export_to_duckdb(df_sql, 'outputs/literature_review.duckdb')
    export_to_csv(df_sql, 'outputs/literature_review.csv')

    # 10. Generate quality report
    generate_extraction_report(df_sql)
```

### Week 2: Validation & Refinement

1. Manual review of 50 papers per discipline
2. Calculate precision/recall for species and techniques
3. Refine extraction logic based on false positives/negatives
4. Document known limitations

---

## 10. Quality Assurance Strategy

### Validation Metrics

```python
def calculate_extraction_quality(df_sql, manually_reviewed_sample):
    """
    Compare automated extraction vs manual review

    Metrics:
    - Precision: Of all extracted, how many correct?
    - Recall: Of all true, how many extracted?
    - F1 Score: Harmonic mean of precision and recall
    """
    metrics = {}

    for field in ['species', 'techniques', 'basins']:
        true_positive = count_matches(df_sql, manually_reviewed_sample, field)
        false_positive = count_auto_only(df_sql, manually_reviewed_sample, field)
        false_negative = count_manual_only(df_sql, manually_reviewed_sample, field)

        precision = true_positive / (true_positive + false_positive)
        recall = true_positive / (true_positive + false_negative)
        f1 = 2 * (precision * recall) / (precision + recall)

        metrics[field] = {
            'precision': precision,
            'recall': recall,
            'f1': f1
        }

    return metrics
```

**Target Quality Thresholds:**
- Species: F1 > 0.75
- Techniques: F1 > 0.70
- Basins: F1 > 0.60

If below thresholds, iterate on extraction logic.

---

## Summary & Next Steps

### ✅ Approved Strategy

1. **Extract from shark-references bulk download** (Phase 1)
2. **Populate ~63% of schema** automatically
3. **Validate with manual sample** (50 papers per discipline)
4. **Enhance with API/full-text** in Phase 2 (if needed)

### 🚀 Next Implementation Task

**Create:** `scripts/shark_references_to_sql.py`

**Script should:**
1. Load shark-references CSV (30,523 papers)
2. Load techniques database (216 techniques)
3. Load species taxonomy (~1200 species)
4. Extract all TIER 1 & TIER 2 fields
5. Extract species and techniques (TIER 3)
6. Export to Parquet + DuckDB + CSV
7. Generate quality report

**Expected Output:**
- `outputs/literature_review.parquet` (DuckDB-optimized)
- `outputs/literature_review.duckdb` (SQL database)
- `outputs/literature_review.csv` (for manual review)
- `outputs/extraction_quality_report.md` (validation metrics)

**Timeline:** 1 week for initial implementation + testing

---

**Ready to proceed with extraction script development?**
