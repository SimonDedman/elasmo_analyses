# Search Queries for Johann's Additions

**Date:** 2025-10-21
**Missing search queries:** 3 techniques

---

## Summary of Johann's Additions

| Discipline | Technique | Has search_query? |
|------------|-----------|-------------------|
| BIO | Reproductive observations | ❌ NO |
| GEN | Genetic relatedness | ❌ NO |
| MOV | Joint Species Distribution Model | ❌ NO |
| ??? | *(4th entry has search_query)* | ✅ YES |

---

## Proposed Search Queries

### 1. Reproductive Observations (BIO)

**Description:** "Observation of bite marks, clasper length or pregnancy"

**Context:** Biological/reproductive ecology. Papers will mention:
- Mating behavior indicators (bite marks)
- Sexual maturity markers (clasper measurements)
- Pregnancy/gestation observations

**Proposed search_query:**
```
reproduction OR reproductive OR pregnancy OR pregnant OR gestation OR clasper OR "mating scar" OR "bite mark" OR "mating behavior" OR parturition OR embryo
```

**Proposed search_query_alt:**
```
maturity OR "sexual maturity" OR "reproductive maturity" OR gravid OR "litter size" OR fecundity OR ovary OR testis OR oviduct
```

**Rationale:**
- Primary terms focus on direct reproductive observations
- Alternative terms capture maturity/reproductive biology papers
- Includes both male (clasper, testis) and female (pregnancy, ovary) indicators
- Broad enough to catch various reproductive assessment methods

---

### 2. Genetic Relatedness (GEN)

**Description:** "Genetic relatedness and parentage analyses"

**Context:** Population genetics. Papers will mention:
- Relatedness coefficients
- Parentage assignment
- Kinship analysis
- Pedigree reconstruction

**Proposed search_query:**
```
relatedness OR kinship OR parentage OR pedigree OR "parent-offspring" OR "full-sib" OR "half-sib" OR "sibship"
```

**Proposed search_query_alt:**
```
"genetic relatedness" OR "relatedness coefficient" OR "parentage analysis" OR "parentage assignment" OR "pedigree reconstruction" OR "kinship analysis" OR paternity OR maternity
```

**Rationale:**
- Primary terms are standard terminology in relatedness studies
- Includes both human-readable (kinship) and technical (relatedness coefficient) terms
- Captures both parentage (parent-offspring) and sibling relationships
- Alternative query adds more specific multi-word phrases

**Related software/methods to consider:**
- COLONY (parentage/sibship software)
- CERVUS (parentage assignment)
- ML-Relate (relatedness estimation)
- These could be in search_query_alt if we want implementation-specific papers

---

### 3. Joint Species Distribution Model (MOV)

**Description:** "Predict species range and abundance from various environmental factors and species correlations"

**Context:** Species distribution modeling with multi-species interactions. Papers will mention:
- Joint SDMs (JSDM)
- Multi-species modeling
- Species correlations/co-occurrence
- Community-level SDMs

**Proposed search_query:**
```
"joint species distribution" OR "JSDM" OR "multi-species distribution" OR "multi-species model" OR "species co-occurrence"
```

**Proposed search_query_alt:**
```
"joint distribution model" OR "multivariate species distribution" OR "community distribution model" OR "species correlation" OR "multi-species SDM" OR "hierarchical model of species communities" OR "HMSC"
```

**Rationale:**
- Primary query focuses on the specific term "joint species distribution model" and its abbreviation
- Includes multi-species variants that might be used instead
- Alternative includes:
  - Multivariate approaches
  - Community-level terminology
  - HMSC (Hierarchical Modelling of Species Communities - major framework)
- Species co-occurrence captures the biological concept

**Note:** This is a relatively recent and specific methodology, so exact phrases are important.

---

## Implementation Instructions

### Add to Spreadsheet

For each technique, update the Excel file with:

1. **Reproductive observations**
   - Column `search_query`: `reproduction OR reproductive OR pregnancy OR pregnant OR gestation OR clasper OR "mating scar" OR "bite mark" OR "mating behavior" OR parturition OR embryo`
   - Column `search_query_alt`: `maturity OR "sexual maturity" OR "reproductive maturity" OR gravid OR "litter size" OR fecundity OR ovary OR testis OR oviduct`

2. **Genetic relatedness**
   - Column `search_query`: `relatedness OR kinship OR parentage OR pedigree OR "parent-offspring" OR "full-sib" OR "half-sib" OR "sibship"`
   - Column `search_query_alt`: `"genetic relatedness" OR "relatedness coefficient" OR "parentage analysis" OR "parentage assignment" OR "pedigree reconstruction" OR "kinship analysis" OR paternity OR maternity`

3. **Joint Species Distribution Model**
   - Column `search_query`: `"joint species distribution" OR "JSDM" OR "multi-species distribution" OR "multi-species model" OR "species co-occurrence"`
   - Column `search_query_alt`: `"joint distribution model" OR "multivariate species distribution" OR "community distribution model" OR "species correlation" OR "multi-species SDM" OR "hierarchical model of species communities" OR "HMSC"`

---

## Testing Recommendations

### Test on Shark-References Database

Before finalizing, test each search query on the shark-references bulk download:

```python
import pandas as pd

# Load complete database
df = pd.read_csv('outputs/shark_references_bulk/shark_references_complete_2025_to_1950_20251021.csv')

# Test search queries
test_queries = {
    'Reproductive observations': 'reproduction|reproductive|pregnancy|pregnant|gestation|clasper|mating scar|bite mark|mating behavior|parturition|embryo',
    'Genetic relatedness': 'relatedness|kinship|parentage|pedigree|parent-offspring|full-sib|half-sib|sibship',
    'Joint Species Distribution Model': 'joint species distribution|JSDM|multi-species distribution|multi-species model|species co-occurrence'
}

for technique, query in test_queries.items():
    # Search in full_text or abstract
    results = df[df['full_text'].str.contains(query, case=False, na=False, regex=True)]
    print(f"{technique}: {len(results)} papers found")
```

**Expected results:**
- Reproductive observations: 500-1500 papers (common topic)
- Genetic relatedness: 100-500 papers (specialized)
- Joint Species Distribution Model: 10-50 papers (recent, specialized)

**If counts are:**
- Too high (>2000): Query is too broad, add more specific terms
- Too low (<10): Query is too narrow, add synonyms
- Just right (50-500): Good balance of precision and recall

---

## Additional Notes

### Why Two Search Queries?

**search_query** = Primary, most specific terms
- Used for targeted searches
- Higher precision, lower recall

**search_query_alt** = Broader synonyms and related terms
- Used when primary search yields too few results
- Higher recall, lower precision

### Combining Queries

For comprehensive literature search, use:
```
(search_query) OR (search_query_alt)
```

This captures:
- Papers using exact terminology (search_query)
- Papers using alternative phrasing (search_query_alt)

---

## Quality Check Criteria

Each search query should:

✅ **Be specific enough** to not return irrelevant papers
✅ **Be broad enough** to catch variant terminology
✅ **Include standard abbreviations** (JSDM, HMSC, etc.)
✅ **Use OR operators** for synonyms
✅ **Use quotes** for multi-word exact phrases
✅ **Cover both technical and colloquial** terms

---

## Next Steps

1. ✅ **Review** these proposed queries with Johann
2. ⏳ **Test** on shark-references bulk download
3. ⏳ **Refine** based on test results
4. ⏳ **Update** Excel spreadsheet
5. ⏳ **Run** searches to populate papers for these techniques

---

## Classification Schema Note

While we're updating Johann's additions, we should also classify them:

| Technique | Proposed Classification |
|-----------|------------------------|
| **Reproductive observations** | 🔢 ANALYTICAL_ALGORITHM (observational method) |
| **Genetic relatedness** | 🔢 ANALYTICAL_ALGORITHM (computational analysis of genetic data) |
| **Joint Species Distribution Model** | 📊 STATISTICAL_MODEL (formal model class) |

See `TECHNIQUE_CLASSIFICATION_SCHEMA_PROPOSAL.md` for details.
