# Data Source: Geographic Extraction

**Status:** Complete (Phase 4, 2025-11-24)
**Team lead:** Simon Dedman

## Purpose

Assign each paper spatial context at three levels: the country of the lead author's institution (author country), the geographic area where fieldwork or data collection took place (study country and ocean basin), and a flag for "parachute science" where the study location and the lead author's institution are in different Global-North/South categories. Geographic extraction enables analyses of research effort distribution across ocean basins, identification of data-poor regions, and investigation of equity in who studies where.

## Data Source

Geographic data are extracted from the SQLite database `database/technique_taxonomy.db`, populated during Phases 3 and 4 of the geographic extraction pipeline. Full documentation is in `docs/geographic/`.

Key references:
- `docs/geographic/QUICK_START_GEOGRAPHIC_ANALYSIS.md` — querying the geographic tables
- `docs/geographic/PHASE_4_FINAL_RESULTS.md` — extraction results and coverage summary
- `docs/geographic/PARACHUTE_RESEARCH_ANALYSIS_SUMMARY.md` — parachute science analysis methodology and results

## Database Tables

### `paper_geography` (6,183 papers)

One row per paper with geographic data. Contains study location, author country, ocean basin assignments, and parachute research flag.

### `institutions` (5,689 records)

Disambiguated institution records linked to countries, used to resolve author country from institutional affiliation strings.

## Fields

### Author geography

| Field | Type | Description |
|-------|------|-------------|
| `auth_country` | string | ISO two-letter country code of the lead author's institution |
| `auth_region` | string | World region of lead author institution |
| `auth_global_north` | boolean | True if institution is in the Global North |

### Study geography

| Field | Type | Description |
|-------|------|-------------|
| `study_country` | string | ISO two-letter country code(s) of study location |
| `study_region` | string | World region of study location |
| `study_global_north` | boolean | True if study location is in the Global North |

### Ocean basin columns (`ob_` prefix)

Binary columns (0/1) indicating which ocean basin(s) a study covers. Nine basins are represented:

| Column | Basin |
|--------|-------|
| `ob_north_atlantic` | North Atlantic |
| `ob_south_atlantic` | South Atlantic |
| `ob_north_pacific` | North Pacific |
| `ob_south_pacific` | South Pacific |
| `ob_indian` | Indian Ocean |
| `ob_southern` | Southern Ocean |
| `ob_arctic` | Arctic Ocean |
| `ob_mediterranean` | Mediterranean Sea |
| `ob_global` | Global / multi-basin / meta-analysis |

### Sub-basin columns (`sb_` prefix)

66 sub-basin binary columns for finer-grained regional filtering (e.g. `sb_gulf_of_mexico`, `sb_north_sea`, `sb_coral_triangle`). See `docs/geographic/PHASE_4_FINAL_RESULTS.md` for the full list.

### Parachute science

| Field | Type | Description |
|-------|------|-------------|
| `parachute_flag` | boolean | True if lead author institution is Global North and study location is Global South |
| `parachute_score` | float | Continuous measure of North–South authorship–location mismatch (0–1) |

## Known Issues

1. **Coverage gap:** 6,183 of ~18,200 papers with extracted data (34 %) have geographic records. Papers extracted via PDF but without institutional data or clear study location references are not covered.
2. **Multi-country studies:** Papers spanning several countries receive multiple `study_country` values as a semicolon-delimited string; parse carefully before aggregating.
3. **Institutional ambiguity:** Authors at institutions with campuses in multiple countries (e.g. international research stations) may be assigned the headquarters country rather than the campus country.
4. **Historical boundary changes:** Country ISO codes reflect current boundaries. Papers from before 1993 citing "Czechoslovakia" or "USSR" are mapped to successor states where possible.
5. **Parachute science definition:** The binary `parachute_flag` uses a strict Global North/South split. The continuous `parachute_score` is preferred for nuanced analyses. See `docs/geographic/PARACHUTE_RESEARCH_ANALYSIS_SUMMARY.md` for methodology.

## Validation

- `docs/geographic/PHASE_4_FINAL_RESULTS.md` contains validation checks run at completion of Phase 4.
- Cross-tabulate `ob_*` columns against `study_country` for a sanity check (e.g. papers with `study_country = AU` should predominantly have `ob_south_pacific = 1` or `ob_indian = 1`).
- Spot-check parachute flagging by manually reviewing 10–15 papers where `parachute_flag = TRUE` to confirm institutional country and study country assignments.

---
*Draft created: 2026-04-16*
