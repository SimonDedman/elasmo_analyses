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

## Columns Added 2026-03-16

New gear types from ISSCFG classification and mitigation devices from BMIS (Bycatch Management Information System) review.

### Additional Gear Types

| Column | Label | Search Terms | Threshold | Notes |
|--------|-------|-------------|-----------|-------|
| `gear_dredge` | Dredge | dredge, towed dredge, scallop dredge, clam dredge, oyster dredge, hydraulic dredge | 1 | ISSCFG code 04. Previously absent; relevant for benthic elasmobranch bycatch studies. |
| `gear_trawl_beam` | Beam Trawl | beam trawl, beam-trawl | 1 | Subtype of `gear_trawl`. Separated because beam trawl bycatch composition differs substantially from otter trawl. |
| `gear_trawl_otter` | Otter Trawl | otter trawl, otter-trawl | 1 | Subtype of `gear_trawl`. Most common demersal trawl type in elasmobranch bycatch literature. |

### Additional Mitigation Devices (from BMIS)

| Column | Label | Search Terms | Threshold | Notes |
|--------|-------|-------------|-----------|-------|
| `gear_mit_weak_hook` | Weak Hook | weak hook, corrodible hook, designed to straighten | 1 | Hook designed to release large non-target species (sharks, rays) while retaining target species. From BMIS. |
| `gear_mit_line_weight` | Line Weighting | line weight\*, weighted branchline, leaded swivel, sliding lead, lumo lead, sink rate | 1 | Branchline weighting to increase sink rate, reducing seabird and shark interactions. From BMIS. |
| `gear_mit_setting` | Setting Practice | night set\*, deep set\*, deep-set buoy gear, side-set\*, underwater set\* | 1 | Operational modifications to when/how gear is deployed. From BMIS. |
| `gear_mit_pinger` | Pinger/Acoustic Alarm | pinger, acoustic alarm, acoustic deterrent, porpoise alerting device, PAL | 1 | Acoustic devices attached to nets to deter marine mammals and elasmobranchs. From BMIS. |
| `gear_mit_illumination` | Net Illumination | illuminat\* net, illuminat\* gillnet, LED net, net light\*, lightstick\*, light attract\* | 1 | Visual deterrents or attractants on nets. Distinct from `gear_mit_deterrent` (which covers shark-specific electronic/magnetic devices). From BMIS. |
| `gear_mit_wire_leader` | Wire/Mono Leader | wire leader, monofilament leader, wire trace, nylon leader | 1 | Leader material affects shark catch and bite-off rates. From BMIS. |
| `gear_mit_ghost` | Ghost Gear | ghost gear, ghost net, ALDFG, abandoned gear, lost gear, derelict gear, derelict fishing | 1 | Abandoned, lost, or otherwise discarded fishing gear. From BMIS. |

### Updated Existing Column

- **`gear_survey`**: Now also includes "diving survey" and "diver transect" as search terms, covering in-water visual survey methods alongside drone, ROV, and vessel-based surveys.

**Rationale:** Dredge and trawl subtypes fill gaps in gear resolution identified via ISSCFG cross-referencing. The seven new mitigation columns cover the most commonly studied bycatch mitigation approaches catalogued in BMIS that were not already captured by `gear_mit_circle_hook`, `gear_mit_brd`, `gear_mit_deterrent`, `gear_mit_time_area`, or `gear_mit_handling`.

---
*Draft created: 2026-03-10, revised with team feedback*
*Updated: 2026-03-16, added 10 columns from ISSCFG and BMIS review*
