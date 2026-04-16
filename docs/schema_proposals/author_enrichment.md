# Data Source: Author Enrichment

**Status:** Complete (OpenAlex 2026-03-12; NamSor 2026-04-13)
**Team leads:** Simon Dedman (OpenAlex), Elena Fernández-Corredor (NamSor gender/origin)

## Purpose

Link each paper's author list to external author identity databases to recover institutional affiliations, career-level proxies, and inferred demographic data (gender, geographic origin, diaspora status). These enrichments support analyses of who is publishing in elasmobranch research: which institutions and countries contribute most, whether female authorship has increased over time, and whether "parachute science" patterns exist across author demographics.

## Data Sources

### OpenAlex

[OpenAlex](https://openalex.org/) is an open scholarly graph maintained by OurResearch. It indexes over 250 million works and provides structured author identity records linked to institutions and disambiguated author IDs.

- **Script:** `scripts/enrich_authors_openalex.py`
- **Method:** Batch DOI lookup (50 DOIs per request). Old-style DOIs containing `(SICI)` or semicolons cause 400 errors in batch mode; the script falls back to individual per-DOI lookups for these.
- **Output files:**
  - `outputs/openalex_paper_authors.csv` — one row per author-paper pairing (71,801 rows)
  - `outputs/openalex_unique_authors.csv` — one row per unique author (28,953 authors)
- **Coverage:** 15,780 papers matched; 87.7 % of author records include institution data

### NamSor

[NamSor](https://namsor.app/) is a gender and origin inference API that uses surname and forename combinations to predict gender, geographic origin (country/region), and diaspora status. The project has 2 M free credits via an institutional grant (see `memory/reference_namsor_api.md`).

- **Script:** `scripts/enrich_namsor.py`
- **Output files:**
  - `outputs/namsor_enrichment.csv` — combined output, all fields (28,922 authors)
  - `outputs/namsor_gender.csv` — gender predictions only
  - `outputs/namsor_origin.csv` — origin country/region predictions
  - `outputs/namsor_diaspora.csv` — diaspora-lifted predictions
- **Coverage:** 28,922 authors enriched as of 2026-04-13 (16,793 M / 9,429 F from NamSor alone)

## Fields

### OpenAlex fields (in `openalex_unique_authors.csv`)

| Field | Type | Description |
|-------|------|-------------|
| `openalex_author_id` | string | Full OpenAlex URL, e.g. `https://openalex.org/A123456789` |
| `display_name` | string | Author's canonical display name in OpenAlex |
| `first_name` | string | Given name(s) parsed from display_name |
| `last_name` | string | Family name parsed from display_name |
| `institution_name` | string | Primary affiliated institution |
| `institution_country` | string | ISO two-letter country code of institution |
| `institution_type` | string | Type of institution (e.g. education, government, company) |
| `gender` | string | Gender label inferred by OpenAlex (where available) |
| `paper_count` | integer | Total works attributed to this author in OpenAlex |
| `most_common_institution` | string | Most frequently recorded institution across the author's career |

### NamSor fields (in `namsor_enrichment.csv`)

| Field | Type | Description |
|-------|------|-------------|
| `namsor_gender` | string | Predicted gender: M or F |
| `namsor_gender_probability` | float | Confidence score for gender prediction (0–1) |
| `namsor_origin_country` | string | Predicted country of geographic origin |
| `namsor_origin_region` | string | World region of origin (e.g. Western Europe) |
| `namsor_origin_subregion` | string | Sub-regional grouping |
| `namsor_ethnicity` | string | Predicted ethnicity label |
| `namsor_diaspora_lifted` | string | Country of diaspora (if applicable) |
| `namsor_diaspora_score` | float | Confidence score for diaspora prediction |
| `namsor_origin_score` | float | Confidence score for origin prediction |

## Gender Resolution Summary

Gender inference draws on three sources applied in priority order: offline gender-guesser library (`scripts/infer_author_gender.py`), the Genderize.io API (100 lookups/day free tier), and NamSor. Combined resolved rate as of 2026-04-13:

| Category | Proportion |
|----------|-----------|
| Male | 55.1 % |
| Female | 30.4 % |
| Unknown | 13.1 % (1.5 % improvement after NamSor) |

**Overall resolved:** 86.9 %

Resolution strategies in `scripts/infer_author_gender.py`: direct forename lookup → accent stripping → initial-skipping → surname+initial matching → Genderize.io API. Full names recovered from OpenAlex author profiles where only initials were available (`scripts/resolve_initials_openalex.py`, 1,420 names recovered; `scripts/resolve_initials_deep.py`, further 300 of 967 initials-only names resolved via OpenAlex + CrossRef).

## Known Issues

1. **Initials-only names:** ~680 authors remain as initials only after all resolution strategies. These stay as unknown gender.
2. **Genderize.io rate limit:** Free tier is 100 names per day (not 1,000). Do not confuse with the batched API rate (10 names per request × 10 requests = 100/day).
3. **NamSor credits:** The institutional grant provides 2 M free credits. Each name lookup consumes credits; see `memory/reference_namsor_api.md` for per-endpoint costs.
4. **Name cleaning:** Pre-NamSor cleaning (`scripts/clean_authors_for_namsor.py`) handles 14 issue types including surname leaks, encoding errors, honorifics, and non-name strings. A review XLSX is generated for spot-checking.
5. **OpenAlex gender field:** OpenAlex's own gender field has sparse coverage; NamSor and gender-guesser are the primary sources.

## Validation

See the extraction review pages linked from `docs/schema_proposals/extraction_review_reference.md` for author-level validation notes. Top NamSor origin countries are GB, ES, IE, IT, PT; top diaspora categories are British, Hispanic, Italian, Portuguese, Chinese.

---
*Draft created: 2026-04-16*
