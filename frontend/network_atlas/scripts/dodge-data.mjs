// Build step: previously applied a GEOGRAPHIC coordinate dodge (see
// src/lib/geoDodge.js) to co-located authors so supercluster would split
// them apart. That mechanism is now DISABLED — the geographic offsets grew
// with zoom (they were degrees, not pixels), so co-located authors kept
// visually spreading further apart the more you zoomed in, which is not the
// desired behaviour. Fan-out of co-located authors is now done entirely in
// screen-pixel space at render time (see `colocationOffsets` / the
// spiderfy fan in App.jsx), which is zoom-independent by construction.
//
// This script is kept as a no-op passthrough (rather than deleted) so the
// `copy-data` npm script and CI history stay stable, and so the intent is
// documented for whoever next touches co-location handling. It intentionally
// does NOT call dodgeCoincidentAuthors() and does NOT mutate coordinates —
// public/data/authors.geojson keeps the TRUE institution geocode for every
// author, including co-located ones.
import fs from 'fs';

const path = 'public/data/authors.geojson';
const d = JSON.parse(fs.readFileSync(path, 'utf8'));
const uniqueCoords = new Set(d.features.map(f => f.geometry.coordinates.join(','))).size;
console.log(
  `dodge-data: DISABLED (no-op) — ${path} keeps true coords: ` +
  `${d.features.length} authors, ${uniqueCoords} unique coordinates.`
);
