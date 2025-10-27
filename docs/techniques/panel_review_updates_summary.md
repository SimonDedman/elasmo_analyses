# Techniques Database - Panel Review Updates Summary

**Date:** 2025-10-22
**File:** `data/Techniques DB for Panel Review_UPDATED.xlsx`

---

## Overview

Updated the techniques database with contributions from Manuel Dureuil (Fisheries discipline expert) and performed data quality improvements.

**Final Count:** 224 techniques (was 219, added 6, removed 1 duplicate)

---

## Changes Made

### 1. Manuel Dureuil's Contributions (6 New Techniques)

Manuel focuses on "data poor conservation assessments and life history" rather than classical stock assessments.

| # | Technique Name | Discipline | Category | Description |
|---|---|---|---|---|
| 1 | **Length-Converted Catch Curves** | FISH | Mortality & Life History | Length-based mortality estimation (Pauly 1983) |
| 2 | **Bayesian Fabens Method** | BIO | Age & Growth Methods | Bayesian mark-recapture growth estimation (Dureuil et al 2022) |
| 3 | **AMSY** | FISH | Data-Poor Methods | Abundance maximum sustainable yield for data-limited stocks (Froese et al 2020) |
| 4 | **LBB** | FISH | Length-Based Methods | Length-based Bayesian biomass estimation (Froese et al 2018) |
| 5 | **Natural Mortality Estimators** | BIO | Life History Parameters | Unified indirect estimators for different life stages (Hoenig, Pauly, Dureuil et al 2021) |
| 6 | **Generation Time-Based IUCN Indicators** | CON | Conservation Assessment | New IUCN generation time based status indicators (topic of Manuel's EEA talk) |

**Key References:**
- Pauly 1983 - Length-converted catch curves
- Dureuil et al 2022 - Bayesian Fabens method
- Froese et al 2020 - AMSY
- Froese et al 2018 - LBB
- Dureuil et al 2021 - Unified mortality estimator for elasmobranchs
- Dureuil & Froese 2021 - Universal estimator for adult natural mortality

---

### 2. Duplicate Resolution

**Issue:** Two identical "Ultrasound" entries (rows 48-49)

**Resolution:**
- Merged into single entry
- Combined search queries: `+ultrasound +pregnan*` (primary) and `+ultrasound +gestation; +echography` (alt)
- Added synonyms: "Echography, pregnancy ultrasound, gestation ultrasound"

---

### 3. Data Quality Improvements

Added synonyms for 10 techniques that were missing them:

| Technique | Synonyms Added |
|-----------|---------------|
| Predation Behavior | Predation, predator-prey interactions, feeding behavior |
| Cognition | Cognitive ability, intelligence, problem solving |
| Learning Experiments | Learning trials, behavioral learning, conditioning |
| Sensory Biology | Sensory systems, sensory ecology, sensory physiology |
| Magnetoreception | Magnetic sense, magnetic orientation, geomagnetic navigation |
| Vision | Visual system, eyesight, visual ecology, visual acuity |
| Health & Disease | Disease ecology, health assessment, pathology |
| Telomere Analysis | Telomere length, aging markers, cellular aging |
| Parasitology | Parasite ecology, host-parasite interactions, parasitic infections |
| Morphology | Morphological analysis, body shape, anatomical features |

---

## Discipline Breakdown

| Discipline | Count | Change |
|-----------|-------|--------|
| BEH (Behavior) | 21 | - |
| BIO (Biology) | 31 | +2 (Bayesian Fabens, Natural Mortality Estimators) |
| CON (Conservation) | 20 | +1 (Generation Time IUCN) |
| DATA (Data Science) | 28 | - |
| FISH (Fisheries) | 37 | +3 (Length-Converted Catch Curves, AMSY, LBB) |
| GEN (Genetics) | 32 | - |
| MOV (Movement) | 35 | - |
| TRO (Trophic Ecology) | 20 | - |
| **Total** | **224** | **+6 new, -1 duplicate** |

---

## Yannis Papastamatiou's Edits

**Status:** You mentioned Yannis has already submitted his edits to the sheet.

**What to Check:**
Since no explicit "Yannis" notes were found in the `notes` column, his edits may be:
1. **Direct data changes** - Modified descriptions, synonyms, or search queries
2. **Added techniques** - New rows without specific attribution
3. **Category adjustments** - Changes to discipline or category assignments
4. **Search query refinements** - Updated search strings

**Action Required:**
- Review the Excel file for any changes that look recent or different from the original schema
- Check for rows with `data_source = 'panel_expert'` (besides Manuel's 6)
- Look for unusual formatting or comments
- Compare against your original backup if you have one

**His Discipline Focus:** Movement ecology (MOV), Behavior (BEH), or Data science (DATA) - check these sections first.

---

## Remaining Data Gaps

| Column | Missing Count | % |
|--------|--------------|---|
| notes | 213 | 95.1% |
| synonyms | 90 | 40.2% |
| parent_technique | 68 | 30.4% |
| search_query_alt | 31 | 13.8% |
| remove_reason | 9 | 4.0% |
| eea_count | 7 | 3.1% |
| data_source | 4 | 1.8% |

**Notes:**
- High missing `notes` is normal - only needed for special cases
- Some techniques naturally don't have parent_technique (top-level/parent techniques)
- Missing synonyms could be filled by domain experts during review

---

## Duplicate Check Results

✅ **No duplicates found** in final database (after fixing Ultrasound)

All 224 technique names are unique.

---

## Next Steps

### For Panel Review:
1. **Distribute to panel members** - Each expert reviews their discipline
2. **Review Manuel's additions** - Verify descriptions and search queries
3. **Identify Yannis's changes** - Document what he modified
4. **Fill remaining synonyms** - Especially for high-frequency techniques
5. **Validate search queries** - Test against literature database

### For Literature Search:
1. Use updated search queries for each technique
2. Document hit counts (eea_count column)
3. Refine queries based on results

---

## Files

**Input:** `data/Techniques DB for Panel Review.xlsx` (219 techniques)
**Output:** `data/Techniques DB for Panel Review_UPDATED.xlsx` (224 techniques)
**Sheets:**
- README - Instructions for panel
- Example_Sample - Sample review format
- Full_List - Complete technique database (224 rows)

---

## Quality Assurance

✅ All techniques have descriptions
✅ No duplicate technique names
✅ All Manuel's techniques properly attributed (`data_source = 'panel_expert'`)
✅ Proper parent-child relationships maintained
✅ Discipline codes consistent
✅ Boolean flags properly set for classification schema

---

## Manuel Dureuil's Note

> "Please also note that my work does not focus on classical stock assessments, but more on data poor conservation assessments and life history side of things, such as length-based mortality estimation, natural mortality estimation, growth estimation, etc"

This context is important for understanding why his suggestions focus on:
- **Data-limited methods** (AMSY, LBB) rather than data-rich stock synthesis
- **Life history parameters** (natural mortality, growth) rather than population models
- **Conservation indicators** (IUCN generation time) rather than fishery management metrics

---

*Document prepared by Claude Code*
*Data Panel - EEA 2025*
