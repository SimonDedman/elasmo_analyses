# Sharkipedia Integration Analysis

## Overview

[Sharkipedia](https://www.sharkipedia.org/) is a curated, open-access database for elasmobranch biological traits and population trends, maintained by Chris Mull and collaborators.

**Key reference:** Mull CG et al. (2022). Sharkipedia: a curated open access database of shark and ray life history traits and abundance time-series. *Scientific Data* 9:559. DOI: [10.1038/s41597-022-01655-1](https://www.nature.com/articles/s41597-022-01655-1)

## Data Contents

### Traits Database
- **4,247+ measurements** across **59 traits** for **178 species**
- **39 families** (65% of chondrichthyan family diversity)
- **12 orders** (85% of chondrichthyan order diversity)
- ~14% of total chondrichthyan species diversity (~1,200 known species globally)

### Trait Classes (6 classes, 59 traits)

| Class | # Traits | Examples |
|-------|----------|---------|
| **Length** | 9 | Lmat50, Lmax-observed, Lbirth |
| **Age** | 8 | Amat50, Amax-observed |
| **Growth** | 12 | Von Bertalanffy k, Linf, L0, t0; Gompertz |
| **Reproduction** | 19 | Fecundity, gestation, breeding interval, offspring mass |
| **Demography** | 5 | Natural mortality (M), total mortality (Z), fishing mortality (F), rmax, lambda |
| **Allometric Relationships** | 5 | Length-length, length-weight conversion coefficients |

### Trends Database
- **871 population time-series** from **202 species**
- Includes abundance indices, CPUE, biomass estimates
- Each trend: year-value pairs, observation type, spatial/gear/time units, analysis model

### Supporting Data
- Taxonomic backbone (Weigmann 2016), IUCN codes, CITES status, CMS status
- Geographic data: lat/lon, Longhurst provinces, FAO areas, EEZs, marine ecoregions
- Bibliographic references with DOIs

## Data Access Methods

| Method | Format | Auth Required | Scope | Currency |
|--------|--------|---------------|-------|----------|
| **Zenodo download** | CSV + XLSX | None | Full snapshot | June 2022 |
| **Website data export** | CSV/Excel | Free account | Filtered | Live |
| **REST API (v1)** | JSON:API | Bearer token (free) | Paginated, spatial | Live |
| **GitHub clone** | Source code | None | Schema + seeds | Sept 2024 |

### Zenodo Files (DOI: 10.5281/zenodo.6656525)

| File | Format | Size |
|------|--------|------|
| Sharkipedia-Taxonomy-v1.0-22-01-25.csv | CSV | 121.6 kB |
| Sharkipedia-Traits-v1.0-22-01-25.csv | CSV | 812.5 kB |
| Sharkipedia-Trends-v1.2-22-06-17.csv | CSV | 702.7 kB |
| Sharkipedia-References-v1.2-22-06-17.xlsx | Excel | 54.2 kB |

**Note:** Zenodo snapshot is from mid-2022. The live website has grown since.

### API Details

- Base URL: `https://www.sharkipedia.org/api/v1/`
- Auth: HTTP Bearer Token (free registration)
- Format: JSON:API specification
- Read-only API

**Key endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/species` | List all species (paginated) |
| GET | `/api/v1/species/:id` | Single species with traits/trends |
| POST | `/api/v1/species/query` | Geospatial query (GeoJSON, oceans, EEZ) |
| GET | `/api/v1/boundaries` | Boundary types (Ocean, EEZ) |

Includable relationships: `observations`, `observations.measurements`, `measurements`, `trends`, `trends.trend_observations`

### Account Credentials

- Username: simondedman@gmail.com
- Password: rpf0gat@jae*JBW*egh

## GitHub Repository

[sharkipedia/sharkipedia](https://github.com/sharkipedia/sharkipedia) — Ruby on Rails + PostgreSQL + PostGIS

## Database Schema (key tables)

| Table | Key Columns | Purpose |
|-------|-------------|---------|
| species | name, scientific_name, iucn_code, cites_status, cms_status | Taxonomic reference |
| species_superorders | name | Selachimorpha, Batoidea, Holocephali |
| observations | access, hidden, contributor_id, depth | Groups measurements by population/study |
| measurements | value, value_type_id, precision, sample_size, validated | Individual data points |
| traits | name, description, trait_class_id | e.g. Lmat50, k, litter_size |
| trait_classes | name | Length, Age, Growth, Reproduction, Demography, Relationships |
| trends | no_years, time_min, start_year, end_year | Population time-series metadata |
| trend_observations | year, value | Individual year-value data points |
| references | name, doi, year, title, journal | Bibliographic sources |
| locations | name, lat, lon | Spatial reference (PostGIS) |

## Integration Value for EEA Project

### What Sharkipedia adds to us:
1. **Life history trait data** per species — enriches our species columns with biological parameters
2. **Population trend time-series** — context for whether species studied are increasing/declining
3. **IUCN/CITES/CMS status** — conservation status layer
4. **Trait-method linkage** — which analytical methods were used to derive each trait measurement

### What we add to Sharkipedia:
1. **Method classification** — our 151-technique taxonomy mapped to their trait measurements
2. **Literature coverage** — our 30,500 papers vs. their ~264 source references
3. **Discipline context** — which disciplines use which trait types

### Join Keys
- **Species name** (scientific binomial) — maps to our `sp_*` columns
- **DOI** — direct paper-level linkage between databases
- **Reference** — Sharkipedia references table has DOIs matchable to our DOI column

---

*Created: 2026-03-09*
