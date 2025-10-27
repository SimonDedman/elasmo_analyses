# Geographic Data Investigation Summary

## Date: 2025-10-26

## Purpose
Investigation to determine availability of geographic/country-level data for creating map visualizations as requested by colleague (reference: guuske map1.png, guuske map2.png).

---

## Investigation Results

### Geographic Reference Data Available
✅ **Found the following geographic lookup tables:**

1. **`data/lookup_geographic_distribution.csv`** (11 rows)
   - Ocean basin regions (WIO, EIO, SWP, NWP, NEP, SEP, SWA, NWA, NEA, SEA)
   - Based on major ocean basins (Indian, Pacific, Atlantic)

2. **`data/geographic_regions_hierarchy.csv`** (77 rows)
   - Comprehensive hierarchy of marine regions
   - Includes: Ocean basins, sub-basins, Large Marine Ecosystems (LMEs)
   - Contains LME IDs (1-66) for standardized marine regions
   - Examples: East Bering Sea, Gulf of Alaska, California Current, Gulf of Mexico, etc.

3. **`data/iso_3166_countries.csv`**
   - ISO country codes for mapping

4. **`data/iho_ocean_basins.csv`**
   - International Hydrographic Organization ocean basin definitions

5. **`data/noaa_lme_regions.csv`**
   - NOAA Large Marine Ecosystem classifications

### Paper-Level Geographic Data Status
❌ **NOT AVAILABLE** - The current analysis datasets do not contain geographic information

**Checked files:**
- `outputs/analysis/data_science_segmentation.csv`
  - Columns: paper_id, year, category, num_disciplines, disciplines, data_assignment_type
  - ❌ No geographic fields

- `outputs/analysis/technique_trends_by_year.csv`
  - Columns: technique_name, year, paper_count, total_mentions, primary_discipline
  - ❌ No geographic fields

- Database: `shark_panel.db`
  - Status: Empty (no tables populated)
  - ❌ No geographic linkages available

---

## Implications for Map Visualizations

### Requested Visualizations (from colleague)
The colleague requested maps similar to:
1. **guuske map1.png** - Choropleth map showing number of disciplines per country with pie chart overlays
2. **guuske map2.png** - World map with regional pie charts showing technique breakdowns

### Current Capability: ❌ CANNOT CREATE

**Reason:** No linkage between papers/techniques and geographic locations

**Missing data:**
- No country-level information for each paper
- No region-level information for each paper
- No way to aggregate disciplines/techniques by location

---

## Recommendations

### Option 1: Manual Geographic Coding (High Effort)
If geographic visualizations are critical:
1. Extract study locations from PDF titles/abstracts
2. Manually code papers to countries/regions
3. Link papers to LME regions or countries
4. Then create visualizations

**Estimated effort:** High (requires processing 4,545 papers)

### Option 2: Species Distribution Proxy (Medium Effort)
Use shark species distribution data:
1. Link papers to shark species (if available)
2. Use species geographic range as proxy for paper location
3. Aggregate disciplines/techniques by species ranges

**Data needed:**
- Paper-species linkages
- Species geographic distribution (may exist in `data/shark_species_detailed_complete.csv`)

### Option 3: Defer Geographic Analysis (Low Effort)
- Focus on completed visualizations (discipline networks, temporal trends, technique stacked bars)
- Defer geographic analysis until paper-location data becomes available

---

## Current Project Status

### ✅ Completed Deliverables

**Phase 1: Technique Analysis (1a-1d)**
- [x] 1a) Breakdown of techniques per discipline
- [x] 1b) Breakdown of techniques per discipline per year
- [x] 1c) Emerging/new/declining technique classification
- [x] 1d) Reference lists of emerging techniques per discipline

**Phase 2: Stacked Bar Visualizations**
- [x] 8 stacked bar plots (one per discipline, Tiktak style)
- [x] Shows technique distribution over time (1950-2025)
- [x] Files: BEH/BIO/CON/DATA/FISH/GEN/MOV/TRO_techniques_stacked.png + .pdf

**Additional Visualizations (from previous session)**
- [x] All-disciplines network visualizations (5 types)
- [x] Interdisciplinary connection analysis

### ⏸️ Pending (Awaiting Data)

**Phase 3: Geographic Visualizations**
- [ ] Cannot proceed without paper-location linkages
- [ ] Awaiting decision on data acquisition strategy

---

## Files Generated This Session

### Analysis Files (Phase 1)
```
outputs/analysis/
├── techniques_per_discipline.csv
├── discipline_technique_summary.csv
├── techniques_per_discipline_per_year.csv
├── technique_trends_analysis.csv
├── technique_trends_summary.csv
├── all_emerging_techniques.csv
├── emerging_techniques_BEH.csv/.txt
├── emerging_techniques_BIO.csv/.txt
├── emerging_techniques_CON.csv/.txt
├── emerging_techniques_DATA.csv/.txt
├── emerging_techniques_FISH.csv/.txt
├── emerging_techniques_GEN.csv/.txt
├── emerging_techniques_MOV.csv/.txt
└── emerging_techniques_TRO.csv/.txt
```

### Visualization Files (Phase 2)
```
outputs/figures/
├── BEH_techniques_stacked.png + .pdf
├── BIO_techniques_stacked.png + .pdf
├── CON_techniques_stacked.png + .pdf
├── DATA_techniques_stacked.png + .pdf
├── FISH_techniques_stacked.png + .pdf
├── GEN_techniques_stacked.png + .pdf
├── MOV_techniques_stacked.png + .pdf
└── TRO_techniques_stacked.png + .pdf
```

### Scripts Created
```
scripts/
├── analyze_techniques_per_discipline.R
└── visualize_techniques_stacked_bars.R
```

---

## Summary Statistics

**From Phase 1 Analysis:**
- Total Techniques Analyzed: 151
- Total Papers: 23,286
- Year Range: 1950 - 2025

**Technique Classifications:**
- STABLE: 83 techniques
- EMERGING: 42 techniques
- RARE: 25 techniques
- NEW: 1 technique

**Top 3 Disciplines by Paper Count:**
1. Genetics: 11,163 papers across 23 techniques
2. Data Science: 2,469 papers across 25 techniques
3. Fisheries: 2,286 papers across 31 techniques

---

## Next Steps

**Immediate recommendation:** Consult with colleague about geographic data availability/requirements:

1. Is geographic visualization critical or optional?
2. Is there existing paper-location data we haven't discovered?
3. Should we pursue Option 1, 2, or 3 above?

**If geographic data becomes available:**
- Can quickly create the requested visualizations
- Have reference images (guuske map1.png, guuske map2.png) to match style
- R packages available: sf, rnaturalearth, ggplot2, maps

---

**Investigation Status:** ✅ COMPLETE
**Geographic Data Status:** ❌ NOT AVAILABLE
**Recommendation:** Consult with colleague before proceeding
