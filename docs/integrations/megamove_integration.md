# MegaMove Integration Analysis

## Overview

[MegaMove](https://megamove.org/) (Marine Megafauna Movement Analytical Program) is the largest collaborative tracking initiative for marine megafauna, directed by **Ana M.M. Sequeira** at the Australian National University. UN-endorsed under the Decade of Ocean Science (2021-2030).

**Key reference:** Sequeira et al. (2025). Global tracking of marine megafauna space use reveals how to achieve conservation targets. *Science* 388(6751). DOI: [10.1126/science.adl0239](https://www.science.org/doi/10.1126/science.adl0239)

## Data Contents

| Metric                     | Value                    |
|----------------------------|--------------------------|
| Total geopositions         | \~11 million             |
| Individual animals tracked | 15,845                   |
| Curated individual tracks  | 12,794                   |
| Species                    | 121 (111 after curation) |
| Temporal span              | 1985-2018                |
| Ocean coverage             | 71.7% of global ocean    |
| Taxonomic groups           | 8                        |

### Taxonomic Groups

1.  **Fishes (mainly sharks)** — blue, tiger, whale, oceanic whitetip, mako, great white, hammerhead, silky, bull sharks
2.  Cetaceans (whales/dolphins)
3.  Pinnipeds (seals/sea lions)
4.  Sea turtles
5.  Seabirds (flying)
6.  Penguins
7.  Sirenians (dugongs, manatees)
8.  Polar bears

### Data Types

-   Satellite telemetry tracking (primary)
-   Geopositions (lat/lon time-series)
-   Regularised daily location time-series
-   Behavioural state classifications (residency vs. migration)
-   Important Marine Megafauna Areas (IMMegAs) derived layers
-   Threat overlap analyses (fishing, shipping, pollution, temperature)

## Data Access

### Current Status: CLOSED

-   **No public API** exists
-   **Data portal** (megamove.org/data-portal/) says "coming soon" — has been for several years
-   **Access requires membership** in the MegaMove network (expression of interest submission)
-   Data will eventually be deposited in Movebank under CC-BY licence, but not yet enacted

### Alternative Access Routes

1.  **Global Shark Movement Project (GSMP) GitHub repos** — actual downloadable data for published analyses
    -   [github.com/GlobalSharkMovement](https://github.com/GlobalSharkMovement) (6 repos)
    -   GlobalSpatialRisk, CollisionRisk, BlueSharkOMZ, WhaleSharkHabitats, etc.
2.  **Movebank public API** ([movebank.org](https://www.movebank.org)) — individual studies shared by contributing researchers
    -   API docs: [github.com/movebank/movebank-api-doc](https://github.com/movebank/movebank-api-doc)
3.  **Apply for MegaMove membership** — requires contributing tracking data or expertise

## Related Projects

### Global Shark Movement Project (GSMP)

-   Coordinated from Marine Biological Association, Plymouth, UK
-   \~1,800+ shark tracks from 20+ species
-   Directly feeds shark data into MegaMove
-   [globalsharkmovement.org](https://www.globalsharkmovement.org/)

### Movebank

-   Free, open archive of animal tracking data (Max Planck Institute)
-   7,500+ studies
-   **Has a public REST API** — most accessible route for shark tracking data
-   MegaMove will eventually deposit here

### OCEARCH

-   Public real-time shark tracker ([ocearch.org/tracker](https://www.ocearch.org/tracker/))
-   Independent of MegaMove/GSMP

## Integration Value for EEA Project

### What MegaMove/GSMP could add to us:

1.  **Movement ecology context** — which species have been tracked, where, with what methods
2.  **Spatial overlap analysis** — threat overlap layers relevant to our MOV and CON disciplines
3.  **Method validation** — real tracking data to contextualise papers about telemetry techniques

### Practical Assessment

-   **Low immediate integration potential** due to closed data access
-   **Medium-term**: Contact Ana Sequeira about collaboration; apply for membership
-   **Best current route**: Use GSMP GitHub repos for published shark tracking datasets and Movebank API for broader marine tracking data
-   **Our contribution**: Our literature database could help MegaMove identify tracking studies they may have missed

### Join Keys

-   **Species name** — maps to our `sp_*` columns
-   **DOI** — GSMP publications and Movebank studies have DOIs
-   **Geographic overlap** — our ocean basin and sub-basin columns vs. their tracking coverage

------------------------------------------------------------------------

*Created: 2026-03-09*
