# Issue 7: Remove eco_marine from Ecosystem Schema

## Summary

`eco_marine` should be removed from the ecosystem schema because it's the uninformative default for elasmobranch research. Nearly all papers about sharks, rays, and chimaeras are marine by definition, making this category add no discriminatory power.

## Current State

- `eco_marine` flags 11,794 papers (by far the highest of any ecosystem column)
- The next highest is `eco_pelagic` at 5,506
- Marine encompasses all other ecosystem types except `eco_freshwater` (2,646) and `eco_brackish` (2,521)

## Proposal

1. Remove `eco_marine` from the ecosystem schema (currently 20 columns → 19)
2. Retain all other ecosystem types including:
   - `eco_polar` (919 papers) — already present
   - `eco_deepwater` (1,523) — already present
   - All depth zones (`eco_epipelagic`, `eco_mesopelagic`, `eco_bathypelagic`, `eco_abyssal`)
3. Regenerate all ecosystem-related visualisations without marine
4. Update extraction pipeline to skip marine extraction

## Evidence

Top 20 species × ecosystem co-occurrence matrix shows marine dominates all species uniformly, confirming it adds no information about habitat specialisation.

## Impact

- Reduces noise in ecosystem analysis
- Makes habitat specialisation patterns more visible
- All other ecosystem categories become more informative by comparison

## Status

- [x] Ecosystem plots regenerated without marine (2026-03-19)
- [ ] Extraction pipeline updated
- [ ] Evidence CSV regenerated
- [ ] Main parquet updated
