import { useEffect, useMemo, useState } from 'react';
import { Map as MapLibreMap } from 'react-map-gl/maplibre';
import DeckGL from '@deck.gl/react';
import { LineLayer, TextLayer, IconLayer, ScatterplotLayer } from '@deck.gl/layers';
import { WebMercatorViewport } from '@deck.gl/core';
import { getIconAtlas, ICON_MAPPING, pickShape } from './lib/shapes.js';
import { getClusterIcon } from './lib/clusterIcons.js';
import Supercluster from 'supercluster';
import 'maplibre-gl/dist/maplibre-gl.css';

import FilterPanel from './components/FilterPanel.jsx';
import {
  GENDER_PALETTE, REGION_PALETTE,
  buildCountryPalette, pickColour,
} from './lib/palettes.js';
import {
  loadAuthors, loadEdges, loadStats, loadInstitutions,
} from './lib/dataLoaders.js';
import { BASEMAPS, DEFAULT_BASEMAP } from './lib/basemaps.js';
import './App.css';

// Bump on each push so the header shows a fresh build number and the
// user can confirm they're looking at the latest code (cache bust aid).
const VERSION = '2.7';

const INITIAL_VIEW_STATE = {
  longitude: -30, latitude: 30, zoom: 1.6, pitch: 0, bearing: 0,
};

const CLUSTER_RADIUS_PX  = 40;
// Authors now carry their TRUE institution coordinate (co-located authors
// are pixel-identical). Supercluster clusters purely on projected distance,
// so identical coordinates cluster into exactly ONE node per institution at
// any zoom <= CLUSTER_MAX_ZOOM — that's the "one blob per institution"
// behaviour we want at low/medium zoom. Above CLUSTER_MAX_ZOOM the app
// bypasses supercluster entirely and reveals individuals, which are then
// spiderfied apart in fixed screen-pixel space (see `colocationOffsets`)
// rather than geographically, so they stop drifting apart on further zoom.
const CLUSTER_MAX_ZOOM   = 10;   // above this, ALL authors show individually (bypass),
                                 // then get pixel-fanned by colocationOffsets
// MUST be 2, not supercluster's example default of 3+: many institutions
// have exactly TWO co-located authors (283 of 1,900 coordinate groups in
// the current dataset — e.g. Kenneth J. Goldman + L. B. Hulbert, both
// "Alaska Department of Fish and Game", identical coords). With
// minPoints=3, supercluster refuses to merge a 2-point group into a
// cluster at all — it returns them as two ordinary (non-cluster) points at
// EVERY zoom, including far-zoomed-out world view. Those bypass the "one
// blob per institution" bucket entirely and instead go straight through
// colocationOffsets' fixed-PIXEL fan-out — which is fine at high zoom but
// catastrophic at low zoom, where a ~28px pixel offset unprojects to many
// degrees of longitude/latitude (verified: at z2.3 Hulbert's fanned
// position lands at [-138.49, 56.29], ~4 degrees into the open Pacific,
// vs her true coordinate at Juneau [-134.42, 58.30]). minPoints=2 (the
// supercluster default) lets any 2+ co-located group merge into a single
// cluster bubble below CLUSTER_MAX_ZOOM, matching the comment above and
// eliminating the drift.
const CLUSTER_MIN_POINTS = 2;

// Zoom used when pan-to-author via search.
const SEARCH_ZOOM = 6;

// Decluttered institution-name labels (replaces the old >=50%-purity
// cluster-name label — see the greedy-placement block near the layers
// section). Visible from this zoom onward; more labels appear as you zoom
// in further and screen space frees up.
const INSTITUTION_LABEL_MIN_ZOOM = 4;
const INSTITUTION_LABEL_FONT_SIZE = 15;   // bumped per restyle (bold, see the TextLayer)
const INSTITUTION_LABEL_GAP_PX = 8;       // gap between the dot and the label's bottom edge
// Hard cap on how many institutions even enter the greedy-placement pass
// (after sorting by author_count desc and filtering to the viewport) — keeps
// the O(candidates x placed) overlap scan cheap even when thousands of
// institutions are on screen at once (e.g. zoomed out over a dense region).
const INSTITUTION_LABEL_MAX_CANDIDATES = 600;

// Author name-label sizing/cap — used both to pick which authors are even
// candidates for a label (viewport-window + paper-count cap, see
// authorLabelCandidates) and to size each candidate's approximate glyph box
// for the greedy declutter pass (see placedAuthorLabels).
const MAX_AUTO_LABELS = 160;
const AUTHOR_LABEL_FONT_SIZE = 13;
const AUTHOR_LABEL_GAP_PX = 8;   // gap between the icon's bottom edge and the label's top

// Author icon diameter in pixels — area grows with sqrt(papers) so it reads
// as area-proportional, clamped to the IconLayer's own min/max. Shared by
// the IconLayer itself and by the fan-out spacing/label-offset maths below
// so they never disagree about how big a node actually is on screen.
const AUTHOR_SIZE_MIN = 6;
const AUTHOR_SIZE_MAX = 44;
function authorIconDiameter(papers) {
  const d = 3 + Math.sqrt(papers ?? 1) * 4.5;
  return Math.min(AUTHOR_SIZE_MAX, Math.max(AUTHOR_SIZE_MIN, d));
}

// Cluster gender-pie bubble diameter in pixels — MUST mirror the 'clusters'
// IconLayer's own getSize/sizeMinPixels/sizeMaxPixels below exactly, since
// this is also used to keep institution labels off the bubbles (see
// clusterBubbleBoxes).
const CLUSTER_ICON_SIZE_MIN = 30;
const CLUSTER_ICON_SIZE_MAX = 92;
function clusterBubbleDiameter(pointCount) {
  const d = 28 + Math.sqrt(pointCount) * 4;
  return Math.min(CLUSTER_ICON_SIZE_MAX, Math.max(CLUSTER_ICON_SIZE_MIN, d));
}

// Fixed-pixel phyllotaxis fan-out constants (golden-angle "sunflower"
// spiral). Zoom-independent because these are screen pixels, applied via
// deck.gl's getPixelOffset AFTER projection — unlike the old geoDodge.js
// degrees-based offsets, they never grow or shrink as you zoom.
const GOLDEN_ANGLE = 2.39996323; // radians
const FAN_PADDING_PX = 16;       // gap between the largest node's edge and its neighbour ring

// NOTE on CollisionFilterExtension: an earlier version of this file used
// @deck.gl/extensions' CollisionFilterExtension to declutter the author
// name labels. In-browser testing (headless Chrome + swiftshader, see
// verification notes) showed that turning `collisionEnabled: true` on
// makes the ENTIRE label layer invisible — 0 of 137 labels rendered, even
// though the exact same data with `collisionEnabled: false` rendered
// immediately. This reproduced with both a fresh extension instance per
// render and a stable module-level singleton, and also after aligning
// @deck.gl/core to the same 9.3.1 version as @deck.gl/extensions — so it
// is not a stale-instance or version-skew issue, it's the extension itself
// failing closed in this stack. Labels are decluttered manually in JS
// instead (viewport windowing + a paper-count cap), which is simpler and
// verified working.

export default function App() {
  const [authorsFC, setAuthorsFC]         = useState(null);
  const [institutionsFC, setInstitutionsFC] = useState(null);
  const [edgesList, setEdgesList]         = useState(null);
  const [stats, setStats]                 = useState(null);
  const [error, setError]                 = useState(null);

  const [viewState, setViewState] = useState(INITIAL_VIEW_STATE);
  const [filters, setFilters] = useState({
    country: '', gender: '', origin_region: '', minEdgeWeight: 2,
    yearMin: null, yearMax: null,   // null = no filter (uses dataset range)
  });
  const [colorBy, setColorBy]           = useState('gender');
  const [shapeBy, setShapeBy]           = useState('none');
  const [showEdges, setShowEdges]       = useState(true);
  const [showClusters, setShowClusters] = useState(true);
  const [selectedId, setSelectedId]     = useState(null);
  const [viewMode, setViewMode]         = useState('authors');
  const [basemap, setBasemap]           = useState(DEFAULT_BASEMAP);
  const [searchQuery, setSearchQuery]   = useState('');
  const [aggregateEdges, setAggregateEdges] = useState(true);
  const [searchTarget, setSearchTarget] = useState('author');  // 'author' | 'institution'

  // Real on-screen canvas size, for the institution-label greedy-placement
  // viewport projection below (the DeckGL canvas is a `position: fixed;
  // inset: 0` div — see App.css — so it always exactly fills the window;
  // the floating filter-panel overlays it rather than shrinking it).
  const [canvasSize, setCanvasSize] = useState({
    width: window.innerWidth, height: window.innerHeight,
  });
  useEffect(() => {
    const onResize = () => setCanvasSize({ width: window.innerWidth, height: window.innerHeight });
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  // DEV-only debug hooks for headless-browser verification (puppeteer).
  // Never included in production builds.
  useEffect(() => {
    if (!import.meta.env.DEV) return;
    window.__setViewState = (v) => setViewState(prev => ({ ...prev, ...v }));
    window.__getViewState = () => viewState;
    // Exposes the greedily-placed author label boxes so a headless script
    // can check pairwise overlap programmatically instead of eyeballing —
    // see the `box` field added to each placedAuthorLabels entry below.
    window.__debugPlacedAuthorLabels = placedAuthorLabels;
  });

  useEffect(() => {
    Promise.all([loadAuthors(), loadEdges(), loadStats(), loadInstitutions()])
      .then(([a, e, s, i]) => {
        // Authors keep their TRUE institution coordinate — co-located
        // authors share the exact same point. Supercluster clusters them
        // into one node per institution below CLUSTER_MAX_ZOOM; above it,
        // individuals are spiderfied apart in fixed screen-pixel space
        // (see `colocationOffsets`), not geographically. See geoDodge.js
        // for why the old geographic-offset approach was replaced.
        setAuthorsFC(a);
        setEdgesList(e); setStats(s); setInstitutionsFC(i);
      })
      .catch(err => setError(err.message));
  }, []);

  // WASD panning — skip when typing in the filter panel inputs
  useEffect(() => {
    const handler = (ev) => {
      const tag = ev.target?.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
      const key = ev.key.toLowerCase();
      if (!'wasd'.includes(key)) return;
      ev.preventDefault();
      setViewState(prev => {
        const step = 20 / Math.pow(2, prev.zoom);   // bigger step when zoomed out
        const dx = key === 'a' ? -step : key === 'd' ? step : 0;
        const dy = key === 'w' ?  step : key === 's' ? -step : 0;
        return { ...prev, longitude: prev.longitude + dx, latitude: prev.latitude + dy };
      });
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  const authors      = authorsFC?.features ?? [];
  const institutions = institutionsFC?.features ?? [];

  const countryPalette = useMemo(() => {
    if (!stats?.by_country) return {};
    return buildCountryPalette(Object.keys(stats.by_country));
  }, [stats]);

  const palettes = useMemo(() => ({
    gender:        GENDER_PALETTE,
    origin_region: REGION_PALETTE,
    country:       countryPalette,
  }), [countryPalette]);

  const originRegions = useMemo(() => {
    const s = new Set();
    authors.forEach(f => { if (f.properties.origin_region) s.add(f.properties.origin_region); });
    return Array.from(s).sort();
  }, [authors]);

  // Counts for dropdown labels (post-filter so (N) reflects the remaining set)
  const filterSample = authors.filter(f => {
    const p = f.properties;
    if (filters.country       && p.country       !== filters.country) return false;
    if (filters.gender        && p.gender        !== filters.gender) return false;
    if (filters.origin_region && p.origin_region !== filters.origin_region) return false;
    return true;
  });
  const genderCounts = useMemo(() => {
    const c = { M: 0, F: 0, Unknown: 0 };
    filterSample.forEach(f => {
      const g = f.properties.gender ?? 'Unknown';
      c[g] = (c[g] ?? 0) + 1;
    });
    return c;
  }, [filterSample]);
  const regionCounts = useMemo(() => {
    const c = {};
    filterSample.forEach(f => {
      const r = f.properties.origin_region ?? 'Unknown';
      c[r] = (c[r] ?? 0) + 1;
    });
    return c;
  }, [filterSample]);

  // Shape-by matrix: count distinct categories for each attribute within
  // the current filter. Fewer categories → better candidate for shape-by
  // (currently only 'gender' is actually wired in shapes.js, but we show
  // the matrix so the user can see which attribute would map cleanly).
  const shapeByMatrix = useMemo(() => {
    if (filterSample.length === 0) return [];
    const attrs = ['gender', 'origin_region', 'country'];
    return attrs.map(attr => {
      const counts = {};
      filterSample.forEach(f => {
        const v = f.properties[attr] ?? '?';
        counts[v] = (counts[v] ?? 0) + 1;
      });
      const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1]);
      return {
        attr,
        n_categories: sorted.length,
        top: sorted.slice(0, 3).map(([k, n]) => `${k}(${n})`),
      };
    }).sort((a, b) => a.n_categories - b.n_categories);
  }, [filterSample]);

  // Sorted author-name list for the datalist autocomplete (unique, by papers).
  const authorNames = useMemo(() => {
    if (!authors.length) return [];
    return [...authors]
      .sort((a, b) => (b.properties.papers ?? 0) - (a.properties.papers ?? 0))
      .map(f => f.properties.name)
      .filter(Boolean);
  }, [authors]);

  // Institution-name list for autocomplete, sorted by author count
  const institutionNames = useMemo(() => {
    if (!institutions.length) return [];
    return [...institutions]
      .sort((a, b) => (b.properties.author_count ?? 0) - (a.properties.author_count ?? 0))
      .map(f => f.properties.institution)
      .filter(Boolean);
  }, [institutions]);

  // --- Filter authors ------------------------------------------------------
  const filteredAuthors = useMemo(() => authors.filter(f => {
    const p = f.properties;
    if (filters.country       && p.country       !== filters.country) return false;
    if (filters.gender        && p.gender        !== filters.gender) return false;
    if (filters.origin_region && p.origin_region !== filters.origin_region) return false;
    // Year filter: keep if the author's active range overlaps the slider
    // window. (author.year_max >= filter.yearMin AND author.year_min <= filter.yearMax)
    if (filters.yearMin != null && p.year_max != null && p.year_max < filters.yearMin) return false;
    if (filters.yearMax != null && p.year_min != null && p.year_min > filters.yearMax) return false;
    return true;
  }), [authors, filters.country, filters.gender, filters.origin_region,
       filters.yearMin, filters.yearMax]);

  const filteredIdSet = useMemo(
    () => new Set(filteredAuthors.map(f => f.properties.id)),
    [filteredAuthors]
  );

  const positionById = useMemo(() => {
    const m = new Map();
    authors.forEach(f => m.set(f.properties.id, f.geometry.coordinates));
    return m;
  }, [authors]);

  const filteredEdges = useMemo(() => {
    if (!edgesList) return [];
    return edgesList.filter(e =>
      e.weight >= filters.minEdgeWeight &&
      filteredIdSet.has(e.from) && filteredIdSet.has(e.to)
    );
  }, [edgesList, filters.minEdgeWeight, filteredIdSet]);

  // --- Selection ----------------------------------------------------------
  const selectedAuthor = useMemo(
    () => (selectedId ? authors.find(f => f.properties.id === selectedId) : null),
    [authors, selectedId]
  );

  const selectedRelated = useMemo(() => {
    if (!selectedId) return null;
    const ids = new Set([selectedId]);
    filteredEdges.forEach(e => {
      if (e.from === selectedId) ids.add(e.to);
      if (e.to   === selectedId) ids.add(e.from);
    });
    return ids;
  }, [selectedId, filteredEdges]);

  // --- Search — author or institution depending on searchTarget -----------
  const onSearchSubmit = () => {
    if (!searchQuery.trim()) return;
    const q = searchQuery.trim().toLowerCase();
    if (searchTarget === 'institution') {
      const match =
        institutions.find(f => f.properties.institution?.toLowerCase() === q) ||
        institutions.find(f => f.properties.institution?.toLowerCase().includes(q));
      if (!match) return;
      setViewState(prev => ({
        ...prev,
        longitude: match.geometry.coordinates[0],
        latitude:  match.geometry.coordinates[1],
        zoom: Math.max(prev.zoom, SEARCH_ZOOM),
        transitionDuration: 600,
      }));
      return;
    }
    const match =
      authors.find(f => f.properties.name?.toLowerCase() === q) ||
      authors.find(f => f.properties.name?.toLowerCase().includes(q));
    if (!match) return;
    setSelectedId(match.properties.id);
    setViewState(prev => ({
      ...prev,
      longitude: match.geometry.coordinates[0],
      latitude:  match.geometry.coordinates[1],
      zoom: Math.max(prev.zoom, SEARCH_ZOOM),
      transitionDuration: 600,
    }));
  };

  // --- Clustering ---------------------------------------------------------
  // Exclude the selected author and their coauthors from the cluster
  // index — they stay as individual dots even when zoomed out so the
  // user can follow international connections without losing the people
  // they care about.
  const authorsToCluster = useMemo(() => {
    if (!selectedRelated) return filteredAuthors;
    return filteredAuthors.filter(f => !selectedRelated.has(f.properties.id));
  }, [filteredAuthors, selectedRelated]);
  const alwaysVisible = useMemo(() => {
    if (!selectedRelated) return [];
    return filteredAuthors.filter(f => selectedRelated.has(f.properties.id));
  }, [filteredAuthors, selectedRelated]);

  const clusterIndex = useMemo(() => {
    if (viewMode !== 'authors' || !showClusters || !authorsToCluster.length) return null;
    const idx = new Supercluster({
      radius: CLUSTER_RADIUS_PX,
      maxZoom: CLUSTER_MAX_ZOOM,
      minPoints: CLUSTER_MIN_POINTS,
    });
    idx.load(authorsToCluster);
    return idx;
  }, [authorsToCluster, showClusters, viewMode]);

  const currentPoints = useMemo(() => {
    if (viewMode !== 'authors') return [];
    // Safety net: above maxZoom, bypass supercluster entirely (it would
    // clamp internally anyway, but this avoids relying on that). With
    // maxZoom=16 this essentially never triggers in normal use.
    if (viewState.zoom > CLUSTER_MAX_ZOOM) {
      return [...authorsToCluster, ...alwaysVisible];
    }
    const clusterResult = clusterIndex
      ? clusterIndex.getClusters([-180, -85, 180, 85], Math.floor(viewState.zoom))
      : authorsToCluster;
    return [...clusterResult, ...alwaysVisible];
  }, [clusterIndex, viewState.zoom, authorsToCluster, alwaysVisible, viewMode]);

  const singletons = useMemo(
    () => currentPoints.filter(c => !c.properties?.cluster),
    [currentPoints]
  );
  const clusterPoints = useMemo(
    () => currentPoints.filter(c => c.properties?.cluster),
    [currentPoints]
  );

  // --- Cluster edges (aggregated to cluster-pair) -------------------------
  // When clustering is active AND aggregateEdges is on, bundle edges
  // whose endpoints share a cluster into one cluster-to-cluster line
  // weighted by the sum. Makes the mesh readable at continental zoom.
  const clusterMembership = useMemo(() => {
    if (!aggregateEdges || !clusterIndex || clusterPoints.length === 0) return null;
    const map = new Map();
    clusterPoints.forEach(c => {
      // getLeaves gives the original points under this cluster
      const leaves = clusterIndex.getLeaves(c.properties.cluster_id ?? c.id, Infinity);
      leaves.forEach(l => { map.set(l.properties.id, c); });
    });
    return map;
  }, [aggregateEdges, clusterIndex, clusterPoints]);

  const aggregatedEdges = useMemo(() => {
    if (!clusterMembership) return filteredEdges;
    const bins = new Map();  // key: "minId|maxId" where id is cluster id or author id
    filteredEdges.forEach(e => {
      const cFrom = clusterMembership.get(e.from);
      const cTo   = clusterMembership.get(e.to);
      const fromKey = cFrom ? `c:${cFrom.id}` : `a:${e.from}`;
      const toKey   = cTo   ? `c:${cTo.id}`   : `a:${e.to}`;
      if (fromKey === toKey) return;  // intra-cluster — skip
      const [a, b] = fromKey < toKey ? [fromKey, toKey] : [toKey, fromKey];
      const key = `${a}|${b}`;
      const agg = bins.get(key);
      if (agg) { agg.weight += e.weight; agg.count += 1; }
      else bins.set(key, {
        fromKey: a, toKey: b,
        fromPos: cFrom ? cFrom.geometry.coordinates : positionById.get(e.from),
        toPos:   cTo   ? cTo.geometry.coordinates   : positionById.get(e.to),
        weight: e.weight, count: 1,
      });
    });
    return Array.from(bins.values());
  }, [clusterMembership, filteredEdges, positionById]);

  // Split singletons into "ordinary" (rendered under clusters) and
  // "selection-related" (rendered above clusters so they stay visible
  // even when they'd otherwise be covered by a cluster bubble).
  const singletonsBelow = selectedRelated
    ? singletons.filter(f => !selectedRelated.has(f.properties.id))
    : singletons;
  const singletonsAbove = selectedRelated
    ? singletons.filter(f => selectedRelated.has(f.properties.id))
    : [];

  // Fixed-pixel "spiderfy" fan-out for co-located authors (same institution
  // geocode — now identical, true coordinates; see geoDodge.js history
  // note). Below CLUSTER_MAX_ZOOM these are merged into one cluster node by
  // supercluster (identical coordinates cluster with zero distance at every
  // zoom); above it they show individually here, and THIS map is what fans
  // them apart. Offsets are pure screen pixels applied post-projection via
  // getPixelOffset, so — unlike the old geographic dodge — they are
  // completely zoom-independent: the same two co-located authors sit the
  // same number of pixels apart whether you're at z15 or z18.
  //
  // Layout: most-prolific author anchors dead centre [0, 0]; everyone else
  // is packed on a golden-angle phyllotaxis spiral (r = SPACING*sqrt(i),
  // angle = i*GOLDEN_ANGLE) — the classic "sunflower" arrangement, which
  // gives near-uniform nearest-neighbour spacing for any i. SPACING is
  // derived per-group from the largest node diameter in that group so
  // neighbours never overlap regardless of how many papers they have.
  const colocationOffsets = useMemo(() => {
    const groups = new Map();
    singletons.forEach(f => {
      const k = `${f.geometry.coordinates[0].toFixed(4)},${f.geometry.coordinates[1].toFixed(4)}`;
      const arr = groups.get(k) ?? [];
      arr.push(f);
      groups.set(k, arr);
    });
    const map = new Map();
    groups.forEach(group => {
      if (group.length === 1) { map.set(group[0].properties.id, [0, 0]); return; }
      group.sort((a, b) => (b.properties.papers ?? 0) - (a.properties.papers ?? 0));
      const maxDiameter = Math.max(...group.map(f => authorIconDiameter(f.properties.papers)));
      // Plain icon-packing spacing (as before)...
      const packingSpacing = maxDiameter + FAN_PADDING_PX;
      // ...but the anchor (i=0, biggest icon, offset [0,0]) always gets its
      // own name label rendered directly below it — see placedAuthorLabels,
      // dy = radius + AUTHOR_LABEL_GAP_PX. That label is a wide rectangle
      // (author names run 60-150px+) sitting right where the closest fanned
      // neighbour (i=1) lands if spacing is too tight: i=1 is always placed
      // at GOLDEN_ANGLE (~137.5°) and r=spacing (sqrt(1)=1), so a spacing
      // that's merely "big enough to not overlap icons" can still drop that
      // neighbour's dot squarely inside the anchor's label box, rendering
      // it invisible underneath the text (verified: Kenneth J. Goldman /
      // L. B. Hulbert, Alaska Dept of Fish & Game — Hulbert's dot landed
      // fully inside Goldman's label rectangle at the old spacing). Bump
      // spacing so the i=1 neighbour's vertical position alone (r*sin,
      // ignoring any horizontal clearance) clears the anchor's label
      // bottom edge, with the same max-diameter radius as a safety margin
      // for the neighbour's own icon on the far side.
      const anchorLabelBottom =
        maxDiameter / 2 + AUTHOR_LABEL_GAP_PX + AUTHOR_LABEL_FONT_SIZE * 1.2;
      const labelClearSpacing = (anchorLabelBottom + maxDiameter / 2) / Math.sin(GOLDEN_ANGLE);
      const spacing = Math.max(packingSpacing, labelClearSpacing);
      group.forEach((f, i) => {
        if (i === 0) { map.set(f.properties.id, [0, 0]); return; }
        const angle = i * GOLDEN_ANGLE;
        const r = spacing * Math.sqrt(i);
        map.set(f.properties.id, [r * Math.cos(angle), r * Math.sin(angle)]);
      });
    });
    return map;
  }, [singletons]);

  // Geo-space equivalent of colocationOffsets, for layers that can't take a
  // screen-pixel offset directly (LineLayer has no getPixelOffset). Only
  // computed for the (usually small) set of fanned authors with a non-zero
  // offset, by projecting the true coordinate to screen space, adding the
  // pixel offset, and unprojecting back — so edges visually land on the
  // same fanned position as the icon/label, at every zoom.
  const fannedGeoPositionById = useMemo(() => {
    const map = new Map();
    let viewport;
    try {
      viewport = new WebMercatorViewport({
        width: 800, height: 600,   // arbitrary — offset math is centre-independent
        longitude: viewState.longitude, latitude: viewState.latitude,
        zoom: viewState.zoom, pitch: viewState.pitch, bearing: viewState.bearing,
      });
    } catch {
      return map;
    }
    singletons.forEach(f => {
      const off = colocationOffsets.get(f.properties.id);
      if (!off || (off[0] === 0 && off[1] === 0)) return;
      const screen = viewport.project(f.geometry.coordinates);
      const shifted = viewport.unproject([screen[0] + off[0], screen[1] + off[1]]);
      map.set(f.properties.id, shifted);
    });
    return map;
  }, [singletons, colocationOffsets, viewState.longitude, viewState.latitude,
      viewState.zoom, viewState.pitch, viewState.bearing]);

  // Resolve an author id to its final ON-SCREEN geo position: the fanned
  // pixel-offset position if it has one, else its true coordinate.
  const finalPositionById = (id) => fannedGeoPositionById.get(id) ?? positionById.get(id) ?? [0, 0];

  // --- Cluster-bubble screen boxes (obstacle for institution labels) ------
  // Same size formula as the 'clusters' IconLayer's getSize below (28 +
  // sqrt(point_count)*4, clamped to that layer's own sizeMinPixels/
  // sizeMaxPixels), projected with the same WebMercatorViewport pattern used
  // for institutionScreenCandidates just below. Consumed by the greedy
  // institution-label placement so labels (a) offset above their OWN
  // bubble's top edge rather than just the raw dot, and (b) get rejected
  // outright if they'd overlap ANY bubble on screen — see placedInstitutionLabels.
  const clusterBubbleBoxes = useMemo(() => {
    if (!clusterPoints.length) return [];
    let viewport;
    try {
      viewport = new WebMercatorViewport({
        width: canvasSize.width, height: canvasSize.height,
        longitude: viewState.longitude, latitude: viewState.latitude,
        zoom: viewState.zoom, pitch: viewState.pitch, bearing: viewState.bearing,
      });
    } catch {
      return [];
    }
    return clusterPoints.map(c => {
      const [x, y] = viewport.project(c.geometry.coordinates);
      const r = clusterBubbleDiameter(c.properties.point_count) / 2;
      return { x, y, r, left: x - r, right: x + r, top: y - r, bottom: y + r };
    });
  }, [clusterPoints, canvasSize.width, canvasSize.height, viewState.zoom,
      viewState.longitude, viewState.latitude, viewState.pitch, viewState.bearing]);

  // --- Decluttered institution labels --------------------------------------
  // Replaces the old >=50%-purity "cluster dominant institution" label,
  // which left plenty of institutions unlabelled even where there was
  // visible free space (and only ever applied to still-clustered nodes).
  // This version works straight off institutions.geojson — independent of
  // the author cluster index — and greedily places labels for the biggest
  // institutions first, skipping any candidate whose label box would
  // overlap one already placed. Guarantees zero overlaps at any zoom.
  //
  // Step 1: project every institution to real screen pixels (same
  // WebMercatorViewport pattern as fannedGeoPositionById above, but here
  // using the actual canvas size since we need true on-screen bounds, not
  // just centre-independent offset maths) and drop anything off-screen.
  const institutionScreenCandidates = useMemo(() => {
    if (viewState.zoom < INSTITUTION_LABEL_MIN_ZOOM || !institutions.length) return [];
    let viewport;
    try {
      viewport = new WebMercatorViewport({
        width: canvasSize.width, height: canvasSize.height,
        longitude: viewState.longitude, latitude: viewState.latitude,
        zoom: viewState.zoom, pitch: viewState.pitch, bearing: viewState.bearing,
      });
    } catch {
      return [];
    }
    const margin = 150; // px — keep candidates whose dot is just off-screen too
    const out = [];
    for (const f of institutions) {
      const [x, y] = viewport.project(f.geometry.coordinates);
      if (x < -margin || x > canvasSize.width + margin ||
          y < -margin || y > canvasSize.height + margin) continue;
      out.push({ feature: f, x, y });
    }
    // Priority order: biggest institutions (by author_count) get first pick
    // of screen space, so they're the ones guaranteed a label.
    out.sort((a, b) => (b.feature.properties.author_count ?? 0) - (a.feature.properties.author_count ?? 0));
    return out.slice(0, INSTITUTION_LABEL_MAX_CANDIDATES);
  }, [institutions, canvasSize.width, canvasSize.height, viewState.zoom,
      viewState.longitude, viewState.latitude, viewState.pitch, viewState.bearing]);

  // Step 2: greedy placement — walk candidates in priority order, place a
  // label only if its approximate bounding box doesn't overlap any box
  // already placed this pass OR any on-screen cluster bubble. Recomputed on
  // every viewState/candidate change, so more labels appear as zooming in
  // frees up screen space.
  //
  // Each entry is { feature, offsetY } — offsetY is the per-label vertical
  // pixel offset (negative = up) fed straight to the TextLayer's
  // getPixelOffset below. It defaults to the standard gap above the
  // institution's own dot, but when that institution anchors an on-screen
  // cluster bubble (true institution coordinates mean the bubble's centroid
  // sits exactly on the dot — see the coordinate-sharing note near
  // colocationOffsets above) the label is pushed further up to clear the
  // bubble's top edge + the same gap, so it never sits over the bubble or
  // its count.
  const placedInstitutionLabels = useMemo(() => {
    const placed = [];
    // Seed the obstacle list with every on-screen cluster bubble's bounding
    // box (screen centre +/- its radius) BEFORE placing any label, so a
    // label candidate is rejected if it overlaps ANY bubble — not just its
    // own — using the exact same box-overlap test as label-vs-label.
    const placedBoxes = clusterBubbleBoxes.map(b => ({
      left: b.left, right: b.right, top: b.top, bottom: b.bottom,
    }));
    for (const cand of institutionScreenCandidates) {
      const name = cand.feature.properties.institution;
      if (!name) continue;
      // Approximate glyph metrics: width scales with string length and
      // font size, height is a fixed multiple of font size. Anchored
      // text-anchor 'middle' / baseline 'bottom' just above the dot (or
      // above the bubble, when this institution has one — see ownBubble).
      const textWidth  = name.length * INSTITUTION_LABEL_FONT_SIZE * 0.55;
      const textHeight = INSTITUTION_LABEL_FONT_SIZE * 1.2;
      const ownBubble = clusterBubbleBoxes.find(
        b => Math.abs(b.x - cand.x) < 1 && Math.abs(b.y - cand.y) < 1
      );
      const gapAboveDot = ownBubble ? (ownBubble.r + INSTITUTION_LABEL_GAP_PX) : INSTITUTION_LABEL_GAP_PX;
      const bottom = cand.y - gapAboveDot;
      const top    = bottom - textHeight;
      const left   = cand.x - textWidth / 2;
      const right  = cand.x + textWidth / 2;
      const overlaps = placedBoxes.some(b =>
        left < b.right && right > b.left && top < b.bottom && bottom > b.top
      );
      if (overlaps) continue;
      placedBoxes.push({ left, right, top, bottom });
      placed.push({ feature: cand.feature, offsetY: -gapAboveDot });
    }
    return placed;
  }, [institutionScreenCandidates, clusterBubbleBoxes]);

  // --- Decluttered author-name labels --------------------------------------
  // Candidate selection: label coauthors of the current selection, or (once
  // zoomed in enough that individuals are showing, see CLUSTER_MAX_ZOOM) every
  // singleton in the viewport, capped by paper count when there are too many.
  // This is the same selection this layer always used — split out into its
  // own memo so the greedy placement pass below can run over a stable list.
  const authorLabelCandidates = useMemo(() => {
    if (viewMode !== 'authors') return [];
    if (selectedRelated) {
      return singletons.filter(f => selectedRelated.has(f.properties.id));
    }
    if (viewState.zoom >= CLUSTER_MAX_ZOOM) {
      const halfLat = 220 / Math.pow(2, viewState.zoom);
      const halfLon = (halfLat * 2.2) / Math.max(Math.cos((viewState.latitude * Math.PI) / 180), 0.2);
      let labelled = singletons.filter(f => {
        const [lo, la] = f.geometry.coordinates;
        return Math.abs(la - viewState.latitude) < halfLat &&
               Math.abs(lo - viewState.longitude) < halfLon;
      });
      if (labelled.length > MAX_AUTO_LABELS) {
        labelled = [...labelled]
          .sort((a, b) => (b.properties.papers ?? 0) - (a.properties.papers ?? 0))
          .slice(0, MAX_AUTO_LABELS);
      }
      return labelled;
    }
    return [];
  }, [viewMode, selectedRelated, singletons, viewState.zoom, viewState.latitude, viewState.longitude]);

  // Greedy placement — same box-overlap pattern as placedInstitutionLabels
  // above, but for author name labels. Each candidate's screen box is its
  // true coordinate projected to screen space, PLUS its fixed-pixel fan
  // offset from colocationOffsets (the same "spiderfy" used for the dots
  // themselves), PLUS the downward nudge that sits the label under its own
  // icon (radius + AUTHOR_LABEL_GAP_PX — mirrors the old inline
  // getPixelOffset). Priority order is paper_count desc, same principle as
  // institution labels: the most-published (usually most-relevant) authors
  // get first pick of screen space and are guaranteed a label; a name that
  // would overlap one already placed is skipped outright rather than
  // relabelled or shrunk. Obstacles are seeded with on-screen cluster
  // bubbles and already-placed institution labels too (bonus ask) so author
  // names don't sit on top of either — author-vs-author is still checked
  // first since it's placed in the same pass as the seed.
  const placedAuthorLabels = useMemo(() => {
    if (!authorLabelCandidates.length) return [];
    let viewport;
    try {
      viewport = new WebMercatorViewport({
        width: canvasSize.width, height: canvasSize.height,
        longitude: viewState.longitude, latitude: viewState.latitude,
        zoom: viewState.zoom, pitch: viewState.pitch, bearing: viewState.bearing,
      });
    } catch {
      return [];
    }
    const ordered = [...authorLabelCandidates].sort(
      (a, b) => (b.properties.papers ?? 0) - (a.properties.papers ?? 0)
    );
    const placedBoxes = [
      ...clusterBubbleBoxes.map(b => ({ left: b.left, right: b.right, top: b.top, bottom: b.bottom })),
      ...placedInstitutionLabels.map(d => {
        const [x, y] = viewport.project(d.feature.geometry.coordinates);
        const name = d.feature.properties.institution ?? '';
        const w = name.length * INSTITUTION_LABEL_FONT_SIZE * 0.55;
        const h = INSTITUTION_LABEL_FONT_SIZE * 1.2;
        const bottom = y + d.offsetY;
        const top = bottom - h;
        return { left: x - w / 2, right: x + w / 2, top, bottom };
      }),
    ];
    const placed = [];
    for (const f of ordered) {
      const name = f.properties.name ?? '';
      if (!name) continue;
      const [fanDx, fanDy] = colocationOffsets.get(f.properties.id) ?? [0, 0];
      const radius = authorIconDiameter(f.properties.papers) / 2;
      const dx = fanDx;
      const dy = fanDy + radius + AUTHOR_LABEL_GAP_PX;
      const [px, py] = viewport.project(f.geometry.coordinates);
      const x = px + dx;
      const y = py + dy;
      // Approximate glyph metrics — same formula as institution labels.
      // getTextAnchor 'middle' / getAlignmentBaseline 'top': (x,y) is the
      // top-centre of the text, so the box extends down from y.
      const textWidth  = name.length * AUTHOR_LABEL_FONT_SIZE * 0.55;
      const textHeight = AUTHOR_LABEL_FONT_SIZE * 1.2;
      const left = x - textWidth / 2;
      const right = x + textWidth / 2;
      const top = y;
      const bottom = y + textHeight;
      const overlaps = placedBoxes.some(b =>
        left < b.right && right > b.left && top < b.bottom && bottom > b.top
      );
      if (overlaps) continue;
      placedBoxes.push({ left, right, top, bottom });
      // `box` is carried along purely for headless-verification (see the
      // window.__debugPlacedAuthorLabels DEV hook above) — the TextLayer
      // below only reads .feature/.pixelOffset off each entry, so this
      // extra field is inert for rendering.
      placed.push({ feature: f, pixelOffset: [dx, dy], box: { left, right, top, bottom } });
    }
    return placed;
  }, [authorLabelCandidates, clusterBubbleBoxes, placedInstitutionLabels, colocationOffsets,
      canvasSize.width, canvasSize.height, viewState.zoom, viewState.longitude, viewState.latitude,
      viewState.pitch, viewState.bearing]);

  // --- Layers -------------------------------------------------------------
  const layers = [];

  // Edges (authors view only). Aggregated or per-author depending on toggle.
  if (viewMode === 'authors' && showEdges) {
    const edgeData = aggregateEdges && clusterMembership
      ? aggregatedEdges
      : filteredEdges;
    if (edgeData.length > 0) {
      const isAggregated = aggregateEdges && clusterMembership;
      // When a selection is active, dim non-incident edges HARD to 8/255
      // alpha so the selected author's connections read clearly through
      // the mesh, even with aggregation on.
      const dimAlpha  = selectedRelated ? 8   : (isAggregated ? 52 : 30);
      const liveAlpha = selectedRelated ? 220 : (isAggregated ? 52 : 30);
      layers.push(new LineLayer({
        id: 'edges',
        data: edgeData,
        // Aggregated (cluster-to-cluster) edges terminate on the cluster's
        // true coordinate — clusters aren't fanned, only individuals are.
        // Per-author edges use the fanned position so a line visibly lands
        // on the same spiderfied dot the user sees, not the shared
        // institution point underneath it.
        getSourcePosition: e => isAggregated ? e.fromPos : finalPositionById(e.from),
        getTargetPosition: e => isAggregated ? e.toPos   : finalPositionById(e.to),
        getWidth: e => Math.log2(e.weight + 1) * 0.5,
        widthMinPixels: 0.4,
        widthMaxPixels: isAggregated ? 4 : 2,
        getColor: e => {
          if (selectedRelated) {
            // Determine incidence: aggregated edges store fromKey/toKey
            // like "a:ID" or "c:clusterID"; check whether the selection's
            // cluster (or the author itself) is at either end.
            let incident = false;
            if (isAggregated) {
              const aKey = `a:${selectedId}`;
              // Also treat a cluster containing the selected author as incident
              const selClusterId = clusterMembership?.get(selectedId)?.id;
              const cKey = selClusterId != null ? `c:${selClusterId}` : null;
              incident = (e.fromKey === aKey || e.toKey === aKey ||
                          (cKey && (e.fromKey === cKey || e.toKey === cKey)));
            } else {
              incident = e.from === selectedId || e.to === selectedId;
            }
            return incident ? [60, 80, 105, liveAlpha]
                            : [140, 155, 180, dimAlpha];
          }
          return [60, 80, 105, liveAlpha];
        },
        updateTriggers: {
          getColor: [selectedId, aggregateEdges],
          getSourcePosition: [fannedGeoPositionById, aggregateEdges],
          getTargetPosition: [fannedGeoPositionById, aggregateEdges],
        },
        pickable: false,
      }));
    }
  }

  // Individual authors — unified IconLayer (circle when shapeBy='none',
  // other shapes otherwise). IconLayer is used even for the plain-circle
  // case so we get getPixelOffset for co-location spiraling, which
  // ScatterplotLayer cannot provide.
  if (viewMode === 'authors') {
    layers.push(new IconLayer({
      id: 'authors',
      data: singletonsBelow,
      pickable: true,
      iconAtlas: getIconAtlas(),
      iconMapping: ICON_MAPPING,
      sizeUnits: 'pixels',
      sizeMinPixels: AUTHOR_SIZE_MIN,
      sizeMaxPixels: AUTHOR_SIZE_MAX,
      getPosition: f => f.geometry.coordinates,
      getIcon: f => pickShape(f.properties, shapeBy),
      getSize: f => authorIconDiameter(f.properties.papers),   // area ∝ papers
      getPixelOffset: f => colocationOffsets.get(f.properties.id) ?? [0, 0],
      getColor: f => {
        const base = pickColour(f.properties, colorBy, palettes);
        if (selectedRelated && !selectedRelated.has(f.properties.id)) {
          return [base[0], base[1], base[2], 40];
        }
        return base;
      },
      onClick: info => { if (info.object) setSelectedId(info.object.properties.id); },
      updateTriggers: {
        getColor: [colorBy, selectedId, palettes],
        getIcon: [shapeBy],
        getPixelOffset: [colocationOffsets],
      },
    }));

    if (clusterPoints.length > 0 && clusterIndex) {
      // Per-cluster gender tally, via supercluster.getLeaves — used for the
      // M/U/F icon. (This used to also tally a dominant institution name for
      // a purity-gated label; that's been replaced by the standalone
      // decluttered institution-label layer below, built straight off
      // institutions.geojson instead of cluster membership.)
      const clusterStats = clusterPoints.map(c => {
        const leaves = clusterIndex.getLeaves(c.id, Infinity);
        let m = 0, f = 0, u = 0;
        leaves.forEach(l => {
          const g = l.properties.gender;
          if (g === 'M') m++;
          else if (g === 'F') f++;
          else u++;
        });
        return { cluster: c, m, f, u };
      });

      // Signature of filter state — changes any time the cluster input
      // set could have shifted. Used as an updateTriggers value so deck.gl
      // re-runs icon / size / text accessors when filters change, even if
      // the cluster count stays the same (e.g. same 3 blobs, different
      // M/F/U composition).
      const filterSig = `${filters.country}|${filters.gender}|${filters.origin_region}|${filters.yearMin}|${filters.yearMax}`;

      // Single IconLayer. Each icon is a canvas-rendered circle with
      // horizontal M | U | F bands proportional to count. Cached by
      // bucketed ratio so the canvas work happens once per unique split.
      layers.push(new IconLayer({
        id: 'clusters',
        data: clusterStats,
        pickable: true,
        sizeUnits: 'pixels',
        sizeMinPixels: 30,
        sizeMaxPixels: 92,
        getPosition: d => d.cluster.geometry.coordinates,
        getIcon:     d => getClusterIcon(d.m, d.u, d.f),
        getSize:     d => clusterBubbleDiameter(d.cluster.properties.point_count),
        onClick: info => {
          if (!info.object || !clusterIndex) return;
          const z = clusterIndex.getClusterExpansionZoom(info.object.cluster.id);
          setViewState(prev => ({
            ...prev,
            longitude: info.object.cluster.geometry.coordinates[0],
            latitude:  info.object.cluster.geometry.coordinates[1],
            zoom: z + 0.5,
            transitionDuration: 500,
          }));
        },
        updateTriggers: {
          getIcon: [filterSig],
          getSize: [filterSig],
          getPosition: [filterSig],
        },
      }));

      layers.push(new TextLayer({
        id: 'cluster-labels',
        data: clusterStats,
        pickable: false,
        getPosition: d => d.cluster.geometry.coordinates,
        getText: d => String(
          d.cluster.properties.point_count_abbreviated ?? d.cluster.properties.point_count
        ),
        getSize: 17,
        getColor: [0, 0, 0, 255],
        getTextAnchor: 'middle',
        getAlignmentBaseline: 'center',
        // Plain crisp black numerals in a clean sans-serif (deck.gl's default is
        // Monaco monospace — the source of the clunky look). No chip, no halo.
        // Non-SDF: no outline is used here either, and SDF's smoothstep blur
        // made the small numerals look soft (verified in headless crops).
        fontFamily: '"Helvetica Neue", Helvetica, Arial, sans-serif',
        fontSettings: { sdf: false },
        fontWeight: 700,
        updateTriggers: {
          getText: [filterSig],
          getPosition: [filterSig],
        },
      }));

    }

    // Selection-related singletons rendered ABOVE the cluster bubbles so
    // you (Simon) stay visible even when sitting on top of a cluster.
    if (singletonsAbove.length > 0) {
      layers.push(new IconLayer({
        id: 'authors-above',
        data: singletonsAbove,
        pickable: true,
        iconAtlas: getIconAtlas(),
        iconMapping: ICON_MAPPING,
        sizeUnits: 'pixels',
        sizeMinPixels: 8,
        sizeMaxPixels: 52,
        getPosition: f => f.geometry.coordinates,
        getIcon: f => pickShape(f.properties, shapeBy),
        getSize: f => 3 + Math.sqrt(f.properties.papers ?? 1) * 4.5,   // area ∝ papers
        getPixelOffset: f => colocationOffsets.get(f.properties.id) ?? [0, 0],
        getColor: f => pickColour(f.properties, colorBy, palettes),
        onClick: info => { if (info.object) setSelectedId(info.object.properties.id); },
        updateTriggers: {
          getColor: [colorBy, palettes],
          getIcon: [shapeBy],
          getPixelOffset: [colocationOffsets],
        },
      }));
    }
  }

  // Author-name labels — AUTO-displayed (no hover/click needed) once authors
  // are fanned out to individuals. Candidate selection (viewport window +
  // paper-count cap, or coauthors of a selection) lives in
  // authorLabelCandidates; the greedy overlap-free placement lives in
  // placedAuthorLabels — same box-overlap pattern as placedInstitutionLabels
  // above, so no two author name labels ever overlap each other (and they
  // also skip cluster bubbles / institution labels as obstacles).
  //
  // Positioning: each label rides its own author's fixed-pixel fan offset
  // (colocationOffsets) plus a small downward nudge sized to that author's
  // own icon radius, so the label sits just under ITS dot — not stacked in
  // a shared column. That pixelOffset was already computed once during
  // placement (placedAuthorLabels), so it's just read back here rather than
  // recomputed.
  //
  // No GPU collision filter: CollisionFilterExtension was found (via
  // in-browser testing) to hide 100% of labels in this stack regardless of
  // config — see the NOTE near the top of this file. Decluttering here is
  // done in plain JS instead (see placedAuthorLabels).
  if (viewMode === 'authors' && placedAuthorLabels.length > 0) {
    layers.push(new TextLayer({
      id: 'author-labels',
      data: placedAuthorLabels,
      pickable: false,
      getPosition: d => d.feature.geometry.coordinates,
      getText: d => d.feature.properties.name ?? '',
      getSize: AUTHOR_LABEL_FONT_SIZE,
      getColor: [15, 15, 15, 255],
      getPixelOffset: d => d.pixelOffset,
      getTextAnchor: 'middle',
      getAlignmentBaseline: 'top',
      // Switched to non-SDF (matches institution-labels/cluster-labels) —
      // re-verified via headless before/after crops at z13-z16 and this
      // reads noticeably crisper than even the bumped-resolution SDF atlas
      // (fontSize 128/radius 32) tried previously: SDF's smoothstep blur
      // softened every glyph edge, most visible on curves ("G", "d", "o")
      // and it never fully caught up to native canvas-text sharpness. The
      // white halo went with it (outline only renders via SDF), so
      // legibility over the busy edge-mesh background now leans on the
      // plain dark fill (getColor) plus generous label decluttering
      // (placedAuthorLabels) rather than a halo — verified still legible
      // in the same before/after crops; no case where dropping the halo
      // made a name unreadable against the mesh.
      // fontFamily fixed the earlier silent fallback to deck.gl's default
      // Monaco monospace font. fontWeight stays 700 (bold).
      fontFamily: '"Helvetica Neue", Helvetica, Arial, sans-serif',
      fontWeight: 700,
      fontSettings: { sdf: false },
      characterSet: 'auto',   // accented author names (José, Sébastien, …)
      background: false,
      updateTriggers: {
        getPosition: [placedAuthorLabels],
        getPixelOffset: [placedAuthorLabels],
      },
    }));
  }

  // Decluttered institution-name labels — see the greedy-placement memos
  // above (institutionScreenCandidates / placedInstitutionLabels). Built
  // straight from institutions.geojson, so it applies in both viewModes:
  // labelling the dominant institutions over the author clusters/blobs, and
  // labelling the institution dots themselves in 'institutions' view. Kicks
  // in from INSTITUTION_LABEL_MIN_ZOOM (4) — well below CLUSTER_MAX_ZOOM —
  // and more labels appear as zooming in frees up screen space. Plain black,
  // no outline (see restyle note above the constants).
  if (placedInstitutionLabels.length > 0) {
    layers.push(new TextLayer({
      id: 'institution-labels',
      data: placedInstitutionLabels,
      pickable: false,
      getPosition: d => d.feature.geometry.coordinates,
      getText: d => d.feature.properties.institution,
      getSize: INSTITUTION_LABEL_FONT_SIZE,
      getColor: [0, 0, 0, 255],
      getTextAnchor: 'middle',
      getAlignmentBaseline: 'bottom',
      // Per-label vertical offset — clears this institution's own bubble
      // (if it has one) in addition to the standard gap. See the offsetY
      // computation in placedInstitutionLabels above.
      getPixelOffset: d => [0, d.offsetY],
      fontFamily: '"Helvetica Neue", Helvetica, Arial, sans-serif',
      // Plain black fill, no outline — SDF bought nothing here and its
      // smoothstep blur made small text look soft/choppy (verified in
      // headless before/after crops). Non-SDF renders the glyph atlas at
      // native alpha-tested resolution instead, which is crisper at these
      // small (13-17px) on-screen sizes.
      fontSettings: { sdf: false },
      fontWeight: 700,
      characterSet: 'auto',   // include accented glyphs (é, ñ, ü…) — default set drops them
      background: false,
      maxWidth: 1400,
      wordBreak: 'break-word',
      updateTriggers: {
        getPixelOffset: [placedInstitutionLabels],
      },
    }));
  }

  // Institutions view
  if (viewMode === 'institutions' && institutions.length > 0) {
    layers.push(new ScatterplotLayer({
      id: 'institutions',
      data: institutions,
      pickable: true,
      opacity: 0.88,
      stroked: true, filled: true,
      radiusMinPixels: 5, radiusMaxPixels: 38,
      lineWidthMinPixels: 0.8,
      getPosition: f => f.geometry.coordinates,
      getRadius: f => 25000 * Math.log2(f.properties.author_count + 1),
      getFillColor: [182, 134, 44, 220],    // FIU gold
      getLineColor: [40, 40, 40, 200],
    }));
  }

  // --- Tooltip -------------------------------------------------------------
  // Offset from cursor (-12, 24) so the pointer isn't sitting on the
  // top-left corner of the card and covering its content.
  const tipOffset = { marginLeft: '14px', marginTop: '14px' };
  const tipBase = {
    background: '#081E3F', color: '#fff', fontSize: '0.8em',
    padding: '6px 9px', borderRadius: '4px',
    ...tipOffset,
  };
  const getTooltip = ({ object }) => {
    if (!object) return null;
    // ROOT CAUSE of the "megacluster never splits" bug: the 'clusters'
    // IconLayer's data items are { cluster, m, f, u } wrapper objects (see
    // clusterStats above), NOT bare GeoJSON features — there is no
    // object.properties on them at all. This branch used to check
    // `object.properties?.cluster`, which was always undefined for a
    // hovered cluster, so it fell through to the final `p.name` access
    // below with p===undefined and threw. That throw happens INSIDE
    // deck.gl's own per-frame render/pick callback (Deck._onRenderFrame),
    // and because the cursor typically sits on the very cluster the user
    // is zooming into, it re-threw on every subsequent animation frame —
    // permanently halting layerManager.updateLayers() for the rest of the
    // session. React state (viewState.zoom, clusterPoints) kept updating
    // fine, which is why the header zoom read correctly while the GPU-
    // rendered layers stayed frozen at whatever they were the instant
    // before the crash (a single big cluster that then "never split").
    if (object.cluster) {
      const cp = object.cluster.properties;
      return {
        text: `${cp.point_count_abbreviated ?? cp.point_count} authors · click to zoom in`,
        style: tipBase,
      };
    }
    if (object.properties?.author_count) {
      const p = object.properties;
      return {
        html:
          `<strong>${p.institution}</strong><br/>` +
          `${[p.city, p.region, p.country].filter(Boolean).join(', ')}<br/>` +
          `<em>${p.author_count} authors · ${p.total_papers} papers</em><br/>` +
          `Top: ${p.top_authors}`,
        style: { ...tipBase, maxWidth: '320px' },
      };
    }
    const p = object.properties;
    // Defensive fallback: never let an unrecognised/stale picked object
    // (e.g. a transient picking-buffer/data race on any other layer)
    // throw inside deck.gl's render loop — that would silently and
    // permanently freeze all GPU-rendered layers, exactly as above.
    if (!p) return null;
    return {
      html:
        `<strong>${p.name}</strong><br/>` +
        `${p.institution ?? '—'}<br/>` +
        `${[p.city, p.region, p.country].filter(Boolean).join(', ')}<br/>` +
        `<em>${p.papers} papers</em> · ${p.gender}${
          p.origin_region ? ` · origin ${p.origin_region}` : ''
        }`,
      style: { ...tipBase, maxWidth: '280px' },
    };
  };

  // Cursor: default arrow everywhere, pointer on a hoverable feature.
  // (deck.gl's default was 'grab'/'grabbing' hand, which hid the point
  // the user was aiming at.)
  const getCursor = ({ isDragging, isHovering }) => {
    if (isDragging) return 'grabbing';
    if (isHovering) return 'pointer';
    return 'default';
  };

  // DEV-only debug surface for headless-browser verification (puppeteer).
  // Exposes just enough internal state to measure fan-out spacing and node
  // sizes from outside React without needing a UI affordance. Never
  // included in production builds.
  useEffect(() => {
    if (!import.meta.env.DEV) return;
    window.__debug = {
      viewState,
      singletons,
      clusterPoints,
      colocationOffsets,
      fannedGeoPositionById,
      authorIconDiameter,
      institutionScreenCandidates,
      placedInstitutionLabels,
      clusterBubbleBoxes,
      findAuthorByName: (name) => authors.find(f => f.properties.name === name),
      projectToScreen: (lon, lat, offsetPx = [0, 0]) => {
        try {
          const vp = new WebMercatorViewport({
            width: 800, height: 600,
            longitude: viewState.longitude, latitude: viewState.latitude,
            zoom: viewState.zoom, pitch: viewState.pitch, bearing: viewState.bearing,
          });
          const [x, y] = vp.project([lon, lat]);
          return [x + offsetPx[0], y + offsetPx[1]];
        } catch {
          return null;
        }
      },
    };
  });

  return (
    <div style={{ position: 'fixed', inset: 0 }}>
      <DeckGL
        viewState={viewState}
        onViewStateChange={e => setViewState(e.viewState)}
        controller={true}
        layers={layers}
        onClick={info => { if (!info.object) setSelectedId(null); }}
        getTooltip={getTooltip}
        getCursor={getCursor}
      >
        <MapLibreMap reuseMaps mapStyle={BASEMAPS[basemap].url} />
      </DeckGL>

      {!authorsFC && !error && (
        <div className="overlay">Loading authors…</div>
      )}
      {error && <div className="overlay error">Error: {error}</div>}

      {authorsFC && (
        <FilterPanel
          filters={filters} setFilters={setFilters}
          colorBy={colorBy} setColorBy={setColorBy}
          shapeBy={shapeBy} setShapeBy={setShapeBy}
          showEdges={showEdges} setShowEdges={setShowEdges}
          showClusters={showClusters} setShowClusters={setShowClusters}
          aggregateEdges={aggregateEdges} setAggregateEdges={setAggregateEdges}
          viewMode={viewMode} setViewMode={setViewMode}
          basemap={basemap} setBasemap={setBasemap}
          searchQuery={searchQuery} setSearchQuery={setSearchQuery}
          searchTarget={searchTarget} setSearchTarget={setSearchTarget}
          institutionNames={institutionNames}
          onSearchSubmit={onSearchSubmit}
          selectedAuthor={selectedAuthor}
          onClearSelection={() => setSelectedId(null)}
          stats={stats}
          authorCount={filteredAuthors.length}
          totalAuthors={authors.length}
          edgeCount={filteredEdges.length}
          institutionCount={institutions.length}
          originRegions={originRegions}
          palettes={palettes}
          authorNames={authorNames}
          genderCounts={genderCounts}
          regionCounts={regionCounts}
          shapeByMatrix={shapeByMatrix}
          zoomLevel={viewState.zoom}
          version={VERSION}
        />
      )}
    </div>
  );
}
