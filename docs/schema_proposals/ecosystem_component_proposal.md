# Proposed Schema: Ecosystem Component

**Status:** Draft for team discussion
**Column prefix:** `eco_`
**Source:** David Ruiz Garcia's reference paper (Issue #2), adapted for elasmobranch context

## Purpose

Classify each paper by the ecosystem component(s) it studies. This enables filtering like "show all papers studying demersal elasmobranchs in coastal habitats" or "which techniques are used for pelagic vs reef species?"

## Extraction Method

Search terms are matched against the **full text** of each paper (title, abstract, keywords, and body where available), not keywords alone. A term like "seagrass" appearing anywhere in the paper will trigger `eco_seagrass = 1`. For papers without full text, title + abstract + keywords are searched.

LLM-based extraction (Phase 2) will supplement keyword matching to catch implicit habitat references that keywords miss (e.g., a paper studying *Triaenodon obesus* on a reef without using the word "reef").

## Proposed Categories

### Level 1: Realm (broad)

| Column | Label | Search Terms |
|--------|-------|-------------|
| `eco_marine` | Marine | marine, ocean, sea, saltwater |
| `eco_freshwater` | Freshwater | freshwater, river, lake, estuarine\*, brackish |
| `eco_brackish` | Brackish/Estuarine | estuar\*, brackish, lagoon, mangrove |

### Level 2: Zone/Habitat

| Column | Label | Search Terms |
|--------|-------|-------------|
| `eco_pelagic` | Pelagic/Open Ocean | pelagic, open ocean, oceanic, offshore, epipelagic, mesopelagic, bathypelagic |
| `eco_coastal` | Coastal/Neritic | coastal, neritic, inshore, nearshore, continental shelf |
| `eco_demersal` | Demersal/Benthic | demersal, benthic, bottom-dwelling, epibenthic, benthopelagic |
| `eco_reef` | Coral/Rocky Reef | coral reef, reef-associated, rocky reef |
| `eco_deepwater` | Deep-water | deep-sea, deep-water, abyssal, hadal, bathyal, seamount |
| `eco_intertidal` | Intertidal | intertidal, tide pool, littoral |
| `eco_mangrove` | Mangrove | mangrove |
| `eco_seagrass` | Seagrass | seagrass, eelgrass, *Posidonia*, *Zostera*, *Thalassia* |
| `eco_kelp` | Kelp Forest | kelp forest, kelp bed, macroalgal |
| `eco_polar` | Polar/Ice | polar, arctic, antarctic, ice-edge, sea ice |
| `eco_riverine` | Riverine | river shark, freshwater stingray, bull shark river |

### Functional Habitats (cross-cutting)

| Column | Label | Search Terms |
|--------|-------|-------------|
| `eco_nursery` | Nursery Habitat | nursery habitat, nursery ground, nursery area, essential fish habitat, juvenile habitat |
| `eco_pupping` | Pupping Ground | pupping ground, pupping area, parturition site, birthing ground |

### Level 3: Depth Zone (where stated)

| Column | Label | Search Terms |
|--------|-------|-------------|
| `eco_epipelagic` | Epipelagic (0-200m) | epipelagic, surface, photic zone |
| `eco_mesopelagic` | Mesopelagic (200-1000m) | mesopelagic, twilight zone |
| `eco_bathypelagic` | Bathypelagic (1000-4000m) | bathypelagic, deep scattering layer |
| `eco_abyssal` | Abyssal (4000m+) | abyssal, hadal |

### Depth Data Columns (numeric extraction)

| Column | Type | Description |
|--------|------|-------------|
| `depth_range` | text | Stated depth range as text, e.g., "0-200", "150", ">500", "<50" |
| `depth_min_m` | float | Minimum depth in metres (parsed from depth_range) |
| `depth_max_m` | float | Maximum depth in metres (parsed from depth_range) |

## Confidence / Guess Columns

When the extraction process cannot confidently assign an ecosystem level, a guess system is used rather than leaving data blank:

| Column | Type | Description |
|--------|------|-------------|
| `eco_1_guess` | text | Best guess for Level 1 realm if not confidently determined (e.g., "eco_marine") |
| `eco_2_guess` | text | Best guess for Level 2 zone if not confidently determined (e.g., "eco_kelp") |
| `eco_3_guess` | text | Best guess for Level 3 depth zone if not confidently determined |

**Rules:**
- Binary `eco_*` columns are only set to `1` when the extraction is confident.
- If an eco level has no confident match, the relevant binary columns stay `0`, and the `eco_N_guess` column is populated with the best-guess category name.
- This avoids polluting numeric binary columns with non-numeric characters while preserving uncertain classifications for later review.

## Discussion Points

1. **Multiple habitats per paper:** Papers often span habitats (e.g., "movement between reef and pelagic zones"). Binary columns handle this naturally.
2. **Level 3 depth zones vs. numeric depth:** Depth zones provide quick filtering; `depth_range`/`depth_min_m`/`depth_max_m` provide precise data. Both are useful.
3. **"Not stated":** All eco\_ columns default to 0 when habitat is not stated. No guessing into binary columns. Guesses go to `eco_N_guess` text columns only.

## Expected Coverage

Based on typical elasmobranch literature:
- Pelagic + coastal + demersal should cover ~70-80% of papers
- Reef, mangrove, deep-water cover most of the remainder
- Freshwater is a small but distinct subset (~2-3% of papers)
- Nursery/pupping grounds are a cross-cutting functional subset (~5-10% of papers)

---
*Draft created: 2026-03-10 for team review*
