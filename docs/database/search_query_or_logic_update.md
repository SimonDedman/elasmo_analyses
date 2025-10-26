---
editor_options:
  markdown:
    wrap: 72
---

# Search Query Update: OR Logic for Synonyms

## Summary

Updated `search_query_new` column in Techniques DB to use proper OR logic
for synonyms instead of problematic AND logic.

**Date:** 2025-10-24
**Files Updated:** `data/Techniques DB for Panel Review_updated.xlsx`
**Scripts:** `scripts/update_search_queries_with_or_logic.py` (Python),
`scripts/update_search_queries_with_or_logic.R` (R)

## Problem

Original `search_query` and `search_query_alt` columns used AND logic
(+) which excluded relevant papers:

**Example Issue:**
- Technique: Boosted Regression Trees
- Synonyms: BRT, GBM, XGBoost, gradient boosting
- Old query: `+GBM +XGBoost`
- **Problem:** Excludes papers mentioning only "BRT" or "gradient boosting"

## Solution

Since we're downloading **ALL papers** from Shark-References (not
filtering during search), queries should catch ANY paper mentioning the
technique or its synonyms.

**New approach:** OR all terms together

- New query: `BRT OR GBM OR XGBoost OR "gradient boosting" OR "boosted regression"`
- **Result:** Captures ANY paper using the technique under any name

## Implementation Details

### Quoting Rules

- **Multi-word terms:** Use quotes (e.g., `"gradient boosting"`)
- **Single words:** No quotes (e.g., `BRT`, `GBM`)
- **Special characters (/, -, &):** Use quotes (e.g., `"SSB/R"`)

### Examples

| Technique | Synonyms | New Query |
|-----------|----------|-----------|
| Boosted Regression Trees | BRT, GBM, XGBoost, gradient boosting | `BRT OR GBM OR XGBoost OR "gradient boosting"` |
| Video Analysis | Camera traps, video, Bruvs | `"Video Analysis" OR "Camera traps" OR video OR Bruvs` |
| BORIS | Behavioral Observation Research Interactive Software | `BORIS OR "Behavioral Observation Research Interactive Software"` |
| Growth Curve Modeling | von Bertalanffy, VBGF, growth modeling | `"von Bertalanffy" OR VBGF OR "growth modeling"` |

## Statistics

- **Total techniques:** 220
- **With synonyms:** 117 (53%)
- **Without synonyms:** 103 (47%)

### Distribution of OR Terms

| OR Count | Techniques |
|----------|------------|
| 1 term | 103 |
| 2 terms | 47 |
| 3 terms | 62 |
| 4 terms | 6 |
| 5 terms | 1 |
| 8 terms | 1 |

### Techniques with Most Variations

1. **Markov Chain Monte Carlo** (8 terms): MCMC, rjags, Rstan, PyStan, JAGS, Gibbs sampling, NIMBLE
2. **Boosted Regression Trees** (5 terms): BRT, GBM, XGBoost, gradient boosting
3. **Video Analysis** (4 terms): Camera traps, video, Bruvs
4. **Growth Curve Modeling** (4 terms): von Bertalanffy, VBGF, growth modeling

## Usage

### Python

```bash
python scripts/update_search_queries_with_or_logic.py
```

### R

```bash
Rscript scripts/update_search_queries_with_or_logic.R
```

Both scripts:
1. Read `data/Techniques DB for Panel Review.xlsx`
2. Update `search_query_new` column with OR logic
3. Save to `data/Techniques DB for Panel Review_updated.xlsx`
4. Print examples and statistics

## Next Steps

1. **Review** generated queries in Excel
2. **Manual corrections** for edge cases if needed
3. **Replace** original file once approved
4. **Deprecate** old `search_query` and `search_query_alt` columns

## Notes

- Old columns (`search_query`, `search_query_alt`) retained for reference
- Can be removed once new queries validated
- Search queries only used for local paper categorization (not for
  Shark-References API calls)

---

*Last updated: 2025-10-24*
