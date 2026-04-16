# Proposed Schema: Ocean Basin

**Status:** Draft for team discussion
**Column prefixes:** `b_` (PDF keyword extraction), `ob_` (geographic pipeline)
**Team lead:** Simon Dedman

## Purpose

Classify each paper by the ocean basin(s) in which it was conducted. Two parallel schemas exist, derived from different data sources, with complementary strengths. Both are retained in the enriched parquet to allow cross-validation and combined analyses.

---

## Schema 1: `b_` — PDF Keyword Extraction

**9 binary columns.** Extracted from full PDF text using the same frequency-threshold keyword system as all other Tier 1 schemas (ecology, pressure, gear, impact, discipline).

### Method

Terms are matched against the full text of each PDF. A column is set to `1` when the cumulative term frequency meets or exceeds the column threshold. Higher thresholds guard against papers that mention a basin only in a biogeographic context (e.g., a discussion section comparing findings to North Atlantic studies).

### Columns

| Column | Label | Threshold | Terms |
|--------|-------|-----------|-------|
| `b_north_atlantic` | North Atlantic | 2 | North Atlantic, Northwest Atlantic, Northeast Atlantic, NW Atlantic, NE Atlantic, North Sea, Bay of Biscay, Celtic Sea, Norwegian Sea, Barents Sea, Baltic Sea, Gulf of Mexico, Sargasso Sea, Azores |
| `b_south_atlantic` | South Atlantic | 2 | South Atlantic, Southwest Atlantic, Southeast Atlantic, SW Atlantic, SE Atlantic, Benguela, Patagoni\*, South Africa\*, Namibia\*, Brazilian coast |
| `b_north_pacific` | North Pacific | 2 | North Pacific, Northwest Pacific, Northeast Pacific, NW Pacific, NE Pacific, Bering Sea, Sea of Japan, East China Sea, South China Sea, Yellow Sea, California Current, Kuroshio, Sea of Okhotsk, Gulf of Alaska, Hawaiian |
| `b_south_pacific` | South Pacific | 2 | South Pacific, Southwest Pacific, Southeast Pacific, SW Pacific, SE Pacific, Coral Sea, Tasman Sea, Great Barrier Reef, New Zealand\*, Fiji\*, French Polynesia, Humboldt Current |
| `b_indian_ocean` | Indian Ocean | 2 | Indian Ocean, Bay of Bengal, Arabian Sea, Mozambique Channel, Red Sea, Persian Gulf, Andaman Sea, Madagascar, Maldives, Seychelles, Western Indian Ocean, Eastern Indian Ocean |
| `b_southern_ocean` | Southern Ocean | 1 | Southern Ocean, Antarctic, sub-Antarctic, Kerguelen, South Georgia, Patagonian shelf |
| `b_arctic_ocean` | Arctic Ocean | 2 | Arctic Ocean, Arctic, Greenland Sea, Beaufort Sea, Chukchi Sea, Canadian Arctic |
| `b_mediterranean` | Mediterranean Sea | 1 | Mediterranean, Adriatic, Aegean, Tyrrhenian, Ionian Sea, Ligurian Sea, Alboran Sea, Strait of Gibraltar, Strait of Sicily |
| `b_caribbean` | Caribbean | 2 | Caribbean, Gulf of Mexico, Bahamas, Belize, Mesoamerican Reef, Antilles, West Indies |

### Notes on Specific Columns

**`b_mediterranean` and `b_southern_ocean`** — Threshold of 1: sea/ocean names within these regions are sufficiently distinctive that a single confirmed mention is reliable. Sub-sea names such as "Adriatic" or "Tyrrhenian" are unambiguous.

**`b_north_atlantic`** — Includes Gulf of Mexico and Baltic Sea for completeness of North Atlantic region coverage. Note that `b_caribbean` also includes Gulf of Mexico terms; a paper focused on the Gulf may flag both columns. This is intentional and reflects the genuine biogeographic overlap of the region.

**`b_arctic_ocean`** — Threshold of 2 because "Arctic" appears in biogeographic discussions of species with broad ranges (e.g., Greenland shark, *Somniosus microcephalus*) without the study itself being Arctic-based.

---

## Schema 2: `ob_` — Geographic Pipeline

**9 binary columns.** Derived from the separate geographic extraction pipeline (see `docs/geographic/` for full documentation), which assigns ocean basins based on study location coordinates, place names extracted from methods sections, and author institutional affiliations.

### Method

The geographic pipeline processes each paper through four phases:
1. **PDF affiliation extraction** — author institutions mapped to countries via the `institutions` table in `database/technique_taxonomy.db`.
2. **Study location extraction** — geographic coordinates and place names extracted from methods sections.
3. **Country → basin mapping** — country codes and coordinates mapped to ocean basins using a standardised regional scheme.
4. **Parachute research flagging** — identifies mismatches between author institution country and study country.

Results are stored in the `paper_geography` table (`study_ocean_basin` column) in `database/technique_taxonomy.db` and will be merged into the main enriched parquet during the geographic pipeline integration step.

### Columns

| Column | Label | Notes |
|--------|-------|-------|
| `ob_arctic_ocean` | Arctic Ocean | |
| `ob_north_atlantic_ocean` | North Atlantic Ocean | |
| `ob_south_atlantic_ocean` | South Atlantic Ocean | |
| `ob_indian_ocean` | Indian Ocean | |
| `ob_north_pacific_ocean` | North Pacific Ocean | |
| `ob_south_pacific_ocean` | South Pacific Ocean | |
| `ob_southern_ocean` | Southern Ocean | |
| `ob_mediterranean_black_sea` | Mediterranean & Black Sea | Grouped as a single analytical unit |
| `ob_baltic_sea` | Baltic Sea | Separated from North Atlantic in this schema |

---

## Why Two Schemas?

| Aspect | `b_` (PDF keywords) | `ob_` (geographic pipeline) |
|--------|--------------------|-----------------------------|
| **Source** | Full PDF text | Institutional affiliations + study coordinates |
| **Coverage** | All papers with PDFs (~18,000) | ~6,000–18,000 depending on pipeline run |
| **Strengths** | Catches explicit geographic discussion regardless of study location | Reflects where the study was actually conducted, not just discussed |
| **Weaknesses** | Can flag a basin mentioned only in the discussion or introduction | Requires extractable PDF text and institution-matching |
| **Typical use** | First-pass geographic filtering; temporal trend analysis | Parachute research analysis; author-country vs study-country comparisons |

Cross-validation between the two schemas is recommended before publication. Papers where `b_` and `ob_` disagree (e.g., a paper flagged `b_north_atlantic` but with `ob_south_atlantic_ocean = 1`) are candidates for manual review.

---

## Validation

Individual paper classifications can be reviewed at:

```
https://simondedman.github.io/elasmo_analyses/validate/{openalex_id}.html
```

Replace `{openalex_id}` with the paper's OpenAlex identifier (e.g., `W2164874137`). The validation page shows the extracted evidence — matched terms, their frequencies, and the document section — for all `b_` columns. Geographic pipeline (`ob_`) assignments are shown separately.

## Known Issues

1. **Gulf of Mexico overlap:** Terms appear in both `b_north_atlantic` and `b_caribbean`. Papers focused on the Gulf will typically flag both. Analysts studying Caribbean-specific questions should filter on `b_caribbean = 1` rather than excluding `b_north_atlantic = 1`.

2. **Southern Ocean / South Atlantic overlap:** "Patagonian shelf" appears in both `b_south_atlantic` and `b_southern_ocean` term lists. Papers on Patagonian elasmobranch populations may flag both columns depending on the geographic framing used.

3. **`b_arctic_ocean` false positives:** *Somniosus microcephalus* (Greenland shark) literature regularly discusses Arctic distribution even when study sites are sub-Arctic or subarctic. Threshold of 2 mitigates but does not eliminate this.

4. **`ob_` pipeline coverage:** As of 2026-04-16, the geographic pipeline has been run on approximately 6,000–18,000 papers. Coverage will improve as the pipeline is re-run on the complete corpus. See `docs/geographic/GEOGRAPHIC_EXTRACTION_STATUS.md` for current status.

---
*Draft created: 2026-04-16*
