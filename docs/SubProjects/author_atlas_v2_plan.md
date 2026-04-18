# Author Atlas v2 — Design Plan

**Status:** proposal, not yet started.
**Date:** 2026-04-17.
**Author:** Simon Dedman + Claude.

## 1. Why v2

The current build (`scripts/build_author_network.R` → `docs/network/index.html`) is
a vis-network widget bent into doing two jobs it was not designed for: a
geographic atlas AND a force-directed collaboration graph. The geographic mode
keeps hitting the same walls — label collision, cluster expansion, map rendering
at multiple zooms, dateline wrap, density-aware border drawing. Each fix unlocks
the next bug.

v2 splits the product in two:

- **Author Atlas** — map-first, showcase quality. A geographic view of where
  elasmobranch researchers are and who they work with, clickable and legible
  from world view to street view.
- **Collaboration Graph** — network-first. The existing vis-network widget,
  kept as-is for force-directed analysis (cluster detection, community
  structure). Iterate separately on that track.

This document concerns the Atlas. The Graph stays.

## 2. Collated design preferences (from the iteration so far)

### Reading/interaction

- Labels must stay **readable from min to max zoom** without manual zoom tuning
  by the user.
- Labels must **not overlap** at any zoom level.
- **Clickable at every zoom** — no dead zones where dense clusters swallow
  clicks.
- Selection isolation: clicking an author hides edges not incident to them and
  reveals labels only on that author and their coauthors.
- Default view shows edges with ≥2 shared papers; slider controls threshold.
- Counter-zoom: node sizes and labels hold **constant screen pixels**, never
  scale with the canvas.

### Geographic rendering

- **Institution-level clustering**: authors at the same lab stack tightly;
  the cluster expands as you zoom in, not earlier.
- Within a cluster, order **most-prolific first** (top of column, leftmost,
  or central — tbd).
- Map layers must stay **visually coherent across zoom**: no chunky low-res
  country silhouette showing through higher-res state borders.
- **Density-aware boundaries**: country borders always visible; sub-country
  boundaries appear only when they cover enough screen area (huge US state
  shows early, small UK county shows late).
- **Stronger country/state distinction**: the boundary between France and
  Spain must read more strongly than the boundary between départements.
- **Dateline**: Aleutians and Pacific islands must not streak horizontally.

### Edges

- Thinner but **darker** — individual edges visible, mesh does not flood
  large regions when many are present.
- Log-scaled by shared-paper count.
- Fade (not hide) when a slider threshold is active.

### Data quality (non-negotiable for showcase)

- **Author duplicates must be merged** (multiple OpenAlex IDs for the same
  person → one canonical node). Existing: Taylor K. Chapple ×3, Barbara A.
  Block ×4, Patrick Rex ×2, Katherine R. Kumli ×2.
- **Institution corrections** via an override CSV, user-editable. Known
  wrong in OpenAlex: Hopkins Marine mislabelled as Pacific University,
  Global Fishing Watch mislabelled as "World Water Watch".
- **Moves tracked**: when a researcher changes institution, override updates
  their node without touching OpenAlex. e.g. Emily Spurgeon (CSULB → FIU).

### Visual language

- Data-source attribution (NamSor etc.) visible in the legend or subtitle.
- Per-author validation page linked from each node.
- **Italicise species names** everywhere they appear (project-wide rule).
- **British English** in all copy.

### Performance

- A `--bbox` subset mode must exist, for sub-second iteration during
  development. The full 28K-author build must not be the only option.

## 3. Proposed v2 architecture

### Layer 1: base map — MapLibre GL

[MapLibre GL JS](https://maplibre.org/) is the open-source fork of Mapbox GL.
Vector tiles, no API key, commercial-friendly licence. It gives us:

- Tile-based rendering (handles all zoom levels natively).
- Label collision detection built-in.
- Density-aware feature visibility via style expressions.
- Sharp vector rendering at any zoom (no chunky polygon problem).
- Pan/zoom/rotate controls.

Base style can be built from:
- [OpenStreetMap tiles](https://www.openstreetmap.org/) (free, community).
- [Natural Earth tiles](https://www.naturalearthdata.com/) (public domain,
  we already use this package in R).
- [Carto Voyager](https://carto.com/attribution/) (free, muted palette that
  matches the existing `#e8efdb` / `#4a6b4a` look).

Recommend Carto Voyager or a hand-built Natural Earth + OSM hybrid for
publication-quality visuals.

### Layer 2: author overlay — deck.gl

[deck.gl](https://deck.gl/) sits on top of MapLibre. It is the Uber-built,
GPU-accelerated visualisation layer that owns the multi-zoom-point-cloud
problem. Specifically:

- **`ScatterplotLayer`** for author bubbles (size = log papers).
- **`TextLayer`** with `getCollisionFilter` — labels cull automatically when
  they would overlap.
- **`IconLayer`** if we want shape-per-attribute (e.g. circle / triangle /
  square for gender / origin / ethnicity).
- **`ArcLayer` or `LineLayer`** for collaboration edges — darker at high zoom,
  fade at low zoom.
- **Clustering**: supercluster integrates natively; at world zoom Stanford's
  42 authors show as one bubble labelled "42", expands to individuals at
  city zoom.

### Layer 3: interaction — React + zustand (or vanilla)

State management for filters, search, selection:

- Filter panel: country, gender, origin, ethnicity, edge-weight slider.
- Search with autocomplete.
- Click-to-select with edge isolation.
- Zoom-tier label policy (cluster → count → name → full card).

React is overkill if we keep vanilla JS — but deck.gl ships React bindings
and most examples are React. For a showcase product, React + vite makes
the whole thing a ~20 MB static site that drops into `docs/network_atlas/`.

### Layer 4: data — precomputed GeoJSON / Parquet

Build step (R or Python) produces:

- `authors.geojson` — one feature per author, properties include name,
  institution, country, gender, origin, ethnicity, paper_count, coauthor_ids.
- `edges.arrow` or `.parquet` — binary edges table, loaded via Apache Arrow.
  28K × 28K is sparse; ~200K edges at ~30 bytes each = 6 MB. Cheap.
- `institutions.geojson` — precomputed cluster centroids with author counts.

Data lives in `outputs/author_atlas/` (per the folder convention we agreed).
Deploy step copies to `docs/network_atlas/` for GitHub Pages.

## 4. Label/cluster strategy (the hard part)

This is where v1 fails and v2 must win.

| Zoom | What shows |
|------|------------|
| 0–3 (continent) | Institution bubbles, size = log(N authors). Numbers inside bubble. Labels only on hover. |
| 3–6 (country) | Institutions still clustered. Top-3-author labels per institution, collision-filtered. |
| 6–10 (region) | Clusters start expanding. Individual bubbles for authors with ≥10 papers. |
| 10+ (city) | All individual bubbles. Labels for all, leader-lined into whitespace. |
| All | Selected author + coauthors always labelled, regardless of zoom. |

Leader-line placement: deck.gl does not ship this out of the box, but
[d3-label-placement](https://github.com/tinker10/d3-label-placement) or
[labella.js](https://twitter.github.io/labella.js/) plug into a custom layer.

## 5. Migration plan (rough)

1. **Keep v1 live.** Force-directed network stays at `docs/network/`.
2. **New build lives at `outputs/author_atlas/`** (canonical) + `docs/network_atlas/` (deploy mirror).
3. **Data layer first** — write the Atlas GeoJSON builder in R, reusing
   `outputs/analysis/author_network_nodes.csv` and the overrides+aliases
   pipelines. No visual work in step 1.
4. **MapLibre prototype** — drop a basic base map, plot authors as static
   scatterplot. Verify base rendering quality, confirm Carto vs NE-hybrid
   look.
5. **Clustering + LOD** — wire supercluster, test at all zoom levels using
   `--bbox` subset.
6. **Edges** — add LineLayer, confirm density behaves.
7. **Interactions** — filters, search, selection isolation.
8. **Polish** — legend, attribution, validation links, British English copy,
   italics on species names.

Estimated scope: ~2-3 days of focused work for a functional showcase, plus
another day or two of visual polish.

## 6. Decisions (2026-04-17)

- **Base map**: start with **Carto Voyager**; keep **Stamen Terrain** (via
  Stadia Maps) as a visual comparator before finalising.
- **Frontend stack**: **React** + deck.gl + MapLibre GL.
- **Shapes-per-attribute**: prepare the functionality (circle / triangle /
  square keyed to gender or origin). Keep the caveat that n-equivalent
  shapes look different — the viewer infers size/quantity slightly
  differently across shape types. Area-normalise the shape sizes so
  identical paper counts produce perceptually equivalent markers.
- **LOD/clustering**: use core deck.gl / MapLibre / supercluster
  primitives. Do not hand-roll collision detection or leader lines in
  step one — iterate after the core works.

## 7. Step 3 — DONE (2026-04-17)

Data builder: `scripts/build_author_atlas.R`. Reuses alias + override
pipelines from build_author_network.R.

Outputs (in `outputs/author_atlas/`):

| File                    | Rows   | Size    | Purpose                        |
|-------------------------|--------|---------|--------------------------------|
| `authors.geojson`       | 5,230  | 1.7 MB  | Point per author, full props   |
| `institutions.geojson`  | 1,593  | 533 KB  | Clustered by institution       |
| `edges.json`            | 63,845 | 3.3 MB  | Coauthor edges                 |
| `stats.json`            | —      | 535 B   | Build summary for UI           |

Figures match the v1 network (MIN_PAPERS=3), minus 80 authors without
institution coordinates. 98.5% of the focal network is mappable.

Each author feature carries: id, name, institution, city, region, country,
papers, gender, origin_country, origin_region, ethnicity — everything the UI
needs for filters, tooltips, and the colour/shape scales.

Institution clusters are keyed by rounded (lon, lat) to 3 decimals (~110 m
tolerance) so SOEST-vs-Honolulu-HQ authors don't accidentally merge.

## 8. Step 4 — next

Minimum React + MapLibre + deck.gl prototype:

1. `docs/network_atlas/` — Vite-built static site.
2. Load `authors.geojson` into a `ScatterplotLayer`.
3. Carto Voyager base.
4. No filters yet, no clustering, no edges — confirm the map renders
   and the 5,230 points land in the right places.

Ask for green-light before committing scaffolding.
