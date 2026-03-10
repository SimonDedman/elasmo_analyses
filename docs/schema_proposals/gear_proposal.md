# Proposed Schema: Fishing Gear Type

**Status:** Draft for team discussion
**Column prefix:** `gear_`
**Source:** David Ruiz Garcia's reference paper (Issue #2), FAO gear classification, ICES terminology

## Purpose

Classify papers mentioning specific fishing gear types. Enables analyses like "which gear types are most studied in bycatch research?" or "are there geographic biases in gear-type research?"

## Proposed Categories

### Level 1: Gear Family

| Column | Label | Search Terms |
|--------|-------|-------------|
| `gear_longline` | Longline | longline, long-line, pelagic longline, demersal longline, bottom longline |
| `gear_gillnet` | Gillnet/Entanglement | gillnet, gill net, trammel net, entangling net, drift net, driftnet |
| `gear_trawl` | Trawl | trawl, bottom trawl, demersal trawl, pelagic trawl, otter trawl, beam trawl, shrimp trawl |
| `gear_purse_seine` | Purse Seine | purse seine, purse-seine, ring net |
| `gear_seine` | Beach/Danish Seine | beach seine, Danish seine, seine net |
| `gear_hook_line` | Hook and Line (non-longline) | hook and line, handline, rod and reel, trolling, jigging, pole and line |
| `gear_trap` | Trap/Pot | trap, pot, fish trap, drumline, SMART drumline |
| `gear_net_other` | Other Nets | cast net, lift net, scoop net, fyke net, pound net, weir |
| `gear_harpoon` | Harpoon/Spear | harpoon, spearfish\*, spear gun |
| `gear_survey` | Scientific Survey Gear | research vessel, survey trawl, BRUVs, longline survey, fishery-independent survey, drone survey, UAV survey, ROV, submersible |

### Level 2: Gear Modifiers (optional, where stated)

| Column | Label | Search Terms |
|--------|-------|-------------|
| `gear_pelagic` | Pelagic Gear | pelagic longline, pelagic trawl, midwater trawl |
| `gear_demersal` | Demersal Gear | demersal longline, bottom trawl, demersal trawl, bottom longline |
| `gear_artisanal` | Artisanal/Traditional | artisanal, traditional gear, small-scale, hand-operated |

### Target Species (text column, not binary)

| Column | Type | Description |
|--------|------|-------------|
| `gear_target_species` | text | Target species group of the fishery, e.g., "tuna", "swordfish", "shrimp", "shark", "mixed demersal". Free text extracted from paper; standardised during analysis. |

### Mitigation Devices (relevant to bycatch research)

| Column | Label | Search Terms |
|--------|-------|-------------|
| `gear_mit_circle_hook` | Circle Hooks | circle hook, non-offset hook |
| `gear_mit_brd` | Bycatch Reduction Device | bycatch reduction device, BRD, turtle excluder, TED |
| `gear_mit_deterrent` | Shark Deterrent | shark deterrent, SharkGuard, shark guard, electropositive, Rare Earth, EPM, LED deterrent, magnetic deterrent |
| `gear_mit_time_area` | Time-Area Closure | time-area closure, spatial closure, fishing closure, seasonal closure, MPA |
| `gear_mit_handling` | Handling/Release | safe release, handling practice\*, live release, post-release mortality, PRM |

**Note:** Shark deterrents (previously split across `gear_mit_brd` and `gear_mit_led`) are consolidated under `gear_mit_deterrent`. Deterrents are a subset of bycatch reduction approaches but are distinct enough in the literature to warrant their own column. BRDs retain the physical device meaning (TEDs, grids, escape panels).

## Resolved Discussion Points

1. **Level 2 vs separate columns:** Keep separate. Pelagic/demersal modifiers add gear-specific context that eco\_ columns don't capture (a paper might study pelagic habitat but discuss demersal gear).
2. **Mitigation as sub-category:** Keep here under gear. They are gear modifications.
3. **Survey gear vs techniques:** Keep separate schema. See Gear-Technique Comparison table (below) for where they overlap and diverge.
4. **Target species:** Added as free text column `gear_target_species` rather than splitting gear into fishery-specific buckets. Allows "tuna longline" to be captured as gear=longline + target=tuna.
5. **Coverage:** Gear type is mainly relevant for FISH and CON disciplines. ~40-50% of papers won't mention gear at all.
6. **Drones in survey:** Added drone survey, UAV survey, ROV, submersible to `gear_survey`.

## Gear vs. Technique Overlap Comparison

Some items appear in both the gear schema and the technique taxonomy. This is intentional — they serve different analytical purposes.

| Item | In Gear Schema | In Technique Taxonomy | Rationale for Both |
|------|---------------|----------------------|-------------------|
| BRUVs | `gear_survey` | `a_bruvs` (MOV) | Gear: what equipment was deployed. Technique: the analytical method used. |
| Longline survey | `gear_survey` | `a_longline_survey` (FISH) | Gear: the physical gear. Technique: the standardised sampling design. |
| Acoustic telemetry | No | `a_acoustic_telemetry` (MOV) | Technique only — not a fishing gear. |
| Satellite telemetry | No | `a_satellite_telemetry` (MOV) | Technique only — not a fishing gear. |
| Trawl | `gear_trawl` | `a_trawl_survey` (FISH) | Gear: commercial/survey trawl. Technique: when used as standardised survey method. |
| Drone | `gear_survey` | `a_drone_survey` (BEH) | Gear: the survey platform. Technique: the observation/analysis method. |
| Circle hooks | `gear_mit_circle_hook` | No | Gear only — a gear modification, not an analytical technique. |
| Stable isotopes | No | `a_stable_isotopes` (TRO) | Technique only — not a gear type. |
| Mark-recapture | No | `a_mark_recapture` (BIO) | Technique only — the tagging gear is incidental. |
| Genetics/eDNA | No | `a_edna` (GEN) | Technique only — sampling gear is incidental. |

**Principle:** Gear describes *what physical equipment was used in the water*. Technique describes *what analytical method was applied to the data*. A paper can use longline gear and apply CPUE standardisation technique to the resulting data.

---
*Draft created: 2026-03-10, revised with team feedback*
