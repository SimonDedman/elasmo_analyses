# Data Source: Journal Quality (SCImago)

**Status:** Complete
**Team lead:** Elena Fernández-Corredor

## Purpose

Assign each paper a journal-level quality indicator based on citation-weighted rankings. Journal quality metrics allow analyses of whether research on particular taxa, techniques, or regions tends to appear in high- or low-impact outlets, and whether publishing norms have changed over time. They also support validation checks: implausibly high or low counts for a column may reflect coverage bias across journal tiers rather than true patterns.

## Data Source

[SCImago Journal & Country Rank](https://www.scimagojr.com/) (SJR) provides freely downloadable bibliometric indicators for journals indexed in Scopus. SJR scores are calculated analogously to Google PageRank: citations from high-prestige journals carry more weight than citations from low-prestige journals.

- **Script:** `scripts/lookup_scimago_journals.py`
- **Output location:** `data/journal_quality/` — SCImago CSV matched and joined to our journal list
- **Coverage:** 1,558 journals matched; 64.7 % of papers assigned a quality score

## Fields

| Field | Type | Description |
|-------|------|-------------|
| `sjr_score` | float | SCImago Journal Rank score (citation-weighted prestige) |
| `sjr_hindex` | integer | H-index of the journal (all years in Scopus) |
| `sjr_quartile` | string | Journal quartile within its best subject category: Q1, Q2, Q3, or Q4 |
| `sjr_subject_category` | string | Primary Scopus subject category used for quartile assignment |
| `sjr_publisher` | string | Publisher name as recorded in SCImago |
| `sjr_country` | string | Country of the publisher |
| `sjr_open_access` | boolean | True if SCImago classifies the journal as open access |

## Quartile Definitions

Quartile is assigned within the journal's best-fitting subject category. Q1 represents the top 25 % of journals by SJR score; Q4 represents the bottom 25 %.

| Quartile | SJR rank within subject category |
|----------|----------------------------------|
| Q1 | Top 25 % |
| Q2 | 26th–50th percentile |
| Q3 | 51st–75th percentile |
| Q4 | Bottom 25 % |

Note that a journal can appear in multiple subject categories and hold different quartile rankings in each. The `sjr_quartile` field records the best (highest) quartile.

## Known Issues

1. **Unmatched journals:** 35.3 % of papers are in journals not matched in SCImago. This includes non-Scopus-indexed journals, conference proceedings, and book chapters. These records have NULL quality fields.
2. **Interdisciplinary journals:** Broad journals such as *Science* and *Nature* are Q1 in every category; their SJR scores are orders of magnitude higher than specialist fisheries journals. Log-transformation is recommended for regression analyses.
3. **Temporal inconsistency:** SCImago ranks change annually. The snapshot year should be recorded in the output file metadata. Avoid comparing raw SJR scores for papers published in different decades without accounting for the edition used.
4. **H-index all-time:** The H-index field covers all years in Scopus, not a rolling window. It is a stable but slow-moving metric.
5. **SCImago vs Impact Factor:** SJR is not equivalent to the Journal Impact Factor (JIF). Do not conflate the two in reporting.

## Validation

Spot-check ten well-known elasmobranch journals (e.g. *Journal of Fish Biology*, *Marine Ecology Progress Series*, *Endangered Species Research*, *ICES Journal of Marine Science*) against the SCImago website to confirm correct SJR scores and quartile assignments for the edition used.

---
*Draft created: 2026-04-16*
