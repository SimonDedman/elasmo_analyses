// DISABLED — no longer imported anywhere (kept for reference/history only).
//
// Co-location dodge for the author point layer.
//
// ROOT CAUSE (see docs/SubProjects/author_atlas_v2_open_questions.md and the
// v2.4 "spiral-offset" attempt in App.jsx): many authors share an
// institution's exact geocoded lat/lon (5,287 authors resolve to only
// ~1,515 unique coordinates — e.g. 149 authors sit on one Paris point).
// Supercluster clusters purely on projected (Web Mercator) distance
// between input coordinates. Identical coordinates project to *zero*
// distance at every zoom, so a mega-cluster built from coincident points
// can never split into smaller sub-clusters no matter how far you zoom —
// it stays one blob until the zoom crosses `maxZoom`, at which point the
// app's hard bypass reveals ALL of them at once with no intermediate
// hierarchy. That abrupt non-gradual reveal is the reported bug.
//
// The previous mitigation (`colocationOffsets` in App.jsx) only nudged
// already-rendered singleton icons in *screen-pixel* space, applied after
// the clustering decision — it never changed what supercluster saw, so it
// could not fix the splitting behaviour, only cosmetically fan out points
// once they were already un-clustered.
//
// Fix: mutate the authors FeatureCollection at data-load time so every
// co-located author gets a small, deterministic, distinct coordinate
// (golden-angle phyllotaxis spiral around the shared point, radius
// growing as sqrt(index)). Supercluster then sees real geographic
// separation and can — and does — split large coincident groups into
// smaller clusters progressively as zoom increases: sparse outer spiral
// members (small index) peel off into their own clusters/singletons at
// higher zoom, while the dense core (large index, tightly packed) keeps
// clustering a little longer. This must run BEFORE the Supercluster index
// is built (i.e. in the data-prep step), not at render time.
//
// SUPERSEDED (2026-07-07): geographic offsets are fixed in DEGREES, so their
// on-screen pixel size grows without bound as you zoom in — co-located
// authors kept visually drifting further apart the more you zoomed, instead
// of settling into a stable fixed layout. Replaced by a fixed-PIXEL
// "spiderfy" fan-out applied at render time (see `colocationOffsets` in
// App.jsx): authors keep their true, identical institution coordinate;
// supercluster merges them into one cluster node below CLUSTER_MAX_ZOOM;
// above it they fan out to phyllotaxis-packed pixel offsets that do NOT
// change with zoom. `scripts/dodge-data.mjs` is now a no-op and this
// function is no longer called from App.jsx.

const GOLDEN_ANGLE = 2.39996323; // radians — avoids any two spiral steps aligning
const BASE_DEG = 0.0003;         // ~33 m/unit — pack an institution tight enough that it
                                 // stays ONE cluster until CLUSTER_MAX_ZOOM, then all its
                                 // authors reveal together via the bypass (no sub-clusters).
                                 // Top author on the true point, others dodged right in.

// Round to 4dp (~11 m at the equator) to catch true float-identical
// geocodes (same institution) without merging genuinely distinct nearby
// addresses that happen to be close.
function coordKey(coordinates) {
  const [lon, lat] = coordinates;
  return `${lon.toFixed(4)},${lat.toFixed(4)}`;
}

/**
 * Mutates `featureCollection.features[*].geometry.coordinates` in place so
 * that co-located points get distinct coordinates, and returns the same
 * FeatureCollection for chaining. Idempotent-ish: running it twice on
 * already-dodged data is harmless (groups will already be near-unique so
 * little further movement occurs), but it should only be called once,
 * right after load.
 */
export function dodgeCoincidentAuthors(featureCollection) {
  const features = featureCollection?.features ?? [];
  const groups = new Map();
  features.forEach(f => {
    const key = coordKey(f.geometry.coordinates);
    const arr = groups.get(key);
    if (arr) arr.push(f); else groups.set(key, [f]);
  });

  groups.forEach(group => {
    if (group.length < 2) return; // no collision — leave untouched
    // Most-prolific author anchors the true coordinate; everyone else
    // spirals outward from it. Deterministic sort (not insertion order)
    // so results are stable across reloads regardless of upstream order.
    group.sort((a, b) => (b.properties.papers ?? 0) - (a.properties.papers ?? 0));
    const [lon0, lat0] = group[0].geometry.coordinates;
    const latRad = (lat0 * Math.PI) / 180;
    // Guard near the poles so longitude offsets don't blow up.
    const lonScale = Math.max(Math.cos(latRad), 0.15);

    group.forEach((f, i) => {
      if (i === 0) return; // top author keeps the true geocode
      const angle = i * GOLDEN_ANGLE;
      const r = BASE_DEG * Math.sqrt(i);
      const dLat = r * Math.sin(angle);
      const dLon = (r * Math.cos(angle)) / lonScale;
      f.geometry.coordinates = [lon0 + dLon, lat0 + dLat];
    });
  });

  return featureCollection;
}
