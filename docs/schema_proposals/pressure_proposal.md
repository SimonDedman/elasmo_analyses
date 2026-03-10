# Proposed Schema: Pressure / Threat Type

**Status:** Draft for team discussion
**Column prefix:** `pr_`
**Source:** David Ruiz Garcia's reference paper (Issue #2), IUCN threat classification, adapted for elasmobranch context

## Purpose

Classify each paper by the pressure/threat type(s) it addresses. Enables analyses like "which techniques are used to study bycatch?" or "how has climate change research grown relative to fisheries pressure research?"

## Proposed Categories

### Level 1: Pressure Type

| Column | Label | Search Terms | Notes |
|--------|-------|-------------|-------|
| `pr_fishing_commercial` | Commercial Fishing | commercial fish\*, industrial fish\*, fishing pressure, fishing mortality, exploitation | |
| `pr_fishing_artisanal` | Artisanal/Small-scale Fishing | artisanal, small-scale fish\*, subsistence fish\*, traditional fish\* | |
| `pr_fishing_recreational` | Recreational Fishing | recreational fish\*, sport fish\*, game fish\*, catch-and-release, angl\* | |
| `pr_fishing_iuu` | IUU Fishing | illegal fish\*, unreported, unregulated, IUU, poach\* | |
| `pr_bycatch` | Bycatch | bycatch, by-catch, incidental capture, non-target, discards | |
| `pr_shark_finning` | Shark Finning | shark fin\*, finning, fin trade | Finning only; removed "targeted" — see note below |
| `pr_targeted_fishing` | Targeted Shark Fishing | targeted shark fish\*, directed shark fish\*, shark fish\* | Separate from finning; covers meat, liver oil, etc. |
| `pr_climate_change` | Climate Change | climate change, global warming, ocean warming | SST/sea surface temperature removed — too many false positives from distribution/ecology papers |
| `pr_ocean_acidification` | Ocean Acidification | ocean acidification, acidification AND pH, acidification AND pCO2 | Require "acidification" as anchor term to avoid false positives |
| `pr_hypoxia` | Hypoxia/Deoxygenation | hypoxia, deoxygenation, oxygen minimum zone, OMZ | Removed "dissolved oxygen" — too common in basic ecology |
| `pr_pollution_chemical` | Chemical Pollution | pollut\*, contaminant\*, heavy metal\*, mercury, PCB, PFAS, pesticide\* | Removed microplastic (now in pr_pollution_plastic) |
| `pr_pollution_plastic` | Plastic Pollution | plastic pollution, microplastic\*, macroplastic\*, plastic ingestion, plastic debris | Tightened: require "plastic" as anchor, not just "debris" |
| `pr_pollution_noise` | Noise Pollution | noise pollution, anthropogenic noise, shipping noise, sonar, acoustic disturbance | |
| `pr_habitat_loss` | Habitat Loss/Degradation | habitat loss, habitat degradation, coastal development, dredg\*, mangrove loss | |
| `pr_shipping` | Shipping/Vessel Strike | ship strike, vessel strike, maritime traffic | Removed generic "shipping" and "boat" — too many false positives |
| `pr_tourism` | Tourism/Ecotourism Impact | dive tourism, ecotourism, shark tourism, provisioning, shark feed\*, cage div\* | |
| `pr_depredation` | Depredation | depredation, depredating, bait loss, catch damage | Separate from tourism and fishing; a shark-initiated behaviour in response to fishing |
| `pr_aquaculture` | Aquaculture | aquaculture, fish farm\*, mariculture | |
| `pr_invasive` | Invasive Species | invasive species, non-native species, alien species | Removed "range expansion" — too generic |
| `pr_disease` | Disease/Parasites | disease, pathogen, parasite, epizootic, infection | |
| `pr_light` | Light Pollution | light pollution, artificial light, ALAN | |
| `pr_electromagnetic` | Electromagnetic | electromagnetic field, EMF, submarine cable, electroreception interference | |

### Compound/Cross-cutting

| Column | Label | Search Terms |
|--------|-------|-------------|
| `pr_cumulative` | Cumulative/Multiple Pressures | cumulative impact, multiple stressor\*, synergistic, additive effect |

## Resolved Discussion Points

1. **Granularity:** Level 1 is sufficient. Gear sub-types (trawl, longline, gillnet) are covered in the separate Gear proposal.
2. **"No pressure" papers:** Leave all pr\_ columns as 0 rather than marking explicitly.
3. **Emerging threats:** Include electromagnetic, noise, light — even if rare now, they are growing and the columns cost nothing.
4. **Finning vs targeted:** Split into `pr_shark_finning` (finning specifically) and `pr_targeted_fishing` (directed shark fisheries for meat, liver oil, etc.). Finning can occur in both targeted and bycatch contexts.
5. **Depredation:** Added as separate category (`pr_depredation`). Not a human pressure per se but a human-induced shark behaviour. Relevant to recreational fishing, commercial fishing, and tourism/provisioning contexts. Keeping it separate avoids forcing it into an ill-fitting category.
6. **False-positive-prone terms:** SST, dissolved oxygen, pH, "debris", "shipping", "boat", "range expansion" removed or tightened with anchor terms to reduce false positives.

---
*Draft created: 2026-03-10, revised with team feedback*
