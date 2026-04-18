# Elasmobranch Author Atlas — v2 prototype

Interactive map of elasmobranch researchers using MapLibre GL + deck.gl + React.
Consumes the canonical Atlas data files produced by
`scripts/build_author_atlas.R`.

## Quick start

```bash
# Build the data first (from repo root):
Rscript scripts/build_author_atlas.R

# Install frontend deps:
cd frontend/network_atlas
npm install

# Copy data into the Vite public dir:
npm run copy-data

# Dev server (localhost:5173):
npm run dev

# Production build (writes to ../../docs/network_atlas/):
npm run copy-data && npm run build
```

## Stack

- **MapLibre GL JS** — vector tile renderer, Carto Voyager style.
- **deck.gl** — GPU-accelerated point/line overlay.
- **React** via `react-map-gl/maplibre` — declarative integration.
- **Vite** — dev server + bundler.

## Current scope (step 4 of v2 plan)

- Base map (Carto Voyager).
- `ScatterplotLayer` plotting every author from `authors.geojson`.
- Radius scales with `log2(papers + 1)`.
- Colour encodes gender (blue M, red F, grey unknown).
- Hover tooltip showing name / institution / papers.

## Not yet (next steps)

- Filters (country, gender, origin, ethnicity).
- Marker clustering (supercluster) for low zoom.
- Edge layer for coauthor links.
- Selection isolation + author search.
- Shape-per-attribute (triangle/square), area-normalised.
- Leader-line label placement at high zoom.

## File layout

```
frontend/network_atlas/
├── package.json
├── vite.config.js
├── index.html
├── src/
│   ├── main.jsx
│   ├── App.jsx
│   └── App.css
└── public/
    └── data/        ← populated by npm run copy-data
        ├── authors.geojson
        ├── institutions.geojson
        ├── edges.json
        └── stats.json
```

Production output lands in `docs/network_atlas/` for GitHub Pages to serve.
