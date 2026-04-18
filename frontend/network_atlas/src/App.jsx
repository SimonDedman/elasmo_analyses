import { useEffect, useMemo, useState } from 'react';
import { Map as MapLibreMap } from 'react-map-gl/maplibre';
import DeckGL from '@deck.gl/react';
import { ScatterplotLayer, LineLayer, TextLayer, IconLayer } from '@deck.gl/layers';
import { CollisionFilterExtension } from '@deck.gl/extensions';
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

const INITIAL_VIEW_STATE = {
  longitude: -30, latitude: 30, zoom: 1.6, pitch: 0, bearing: 0,
};

const CLUSTER_RADIUS_PX  = 50;
const CLUSTER_MAX_ZOOM   = 8;
const CLUSTER_MIN_POINTS = 3;

// Zoom used when pan-to-author via search.
const SEARCH_ZOOM = 6;

export default function App() {
  const [authorsFC, setAuthorsFC]         = useState(null);
  const [institutionsFC, setInstitutionsFC] = useState(null);
  const [edgesList, setEdgesList]         = useState(null);
  const [stats, setStats]                 = useState(null);
  const [error, setError]                 = useState(null);

  const [viewState, setViewState] = useState(INITIAL_VIEW_STATE);
  const [filters, setFilters] = useState({
    country: '', gender: '', origin_region: '', minEdgeWeight: 2,
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

  useEffect(() => {
    Promise.all([loadAuthors(), loadEdges(), loadStats(), loadInstitutions()])
      .then(([a, e, s, i]) => {
        setAuthorsFC(a); setEdgesList(e); setStats(s); setInstitutionsFC(i);
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
    return true;
  }), [authors, filters.country, filters.gender, filters.origin_region]);

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
    const clusterResult = clusterIndex
      ? clusterIndex.getClusters([-180, -85, 180, 85], Math.floor(viewState.zoom))
      : authorsToCluster;
    // Append always-visible (selection-related) authors as individuals
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
      const dimAlpha  = selectedRelated ? 8   : (isAggregated ? 140 : 90);
      const liveAlpha = selectedRelated ? 220 : (isAggregated ? 140 : 90);
      layers.push(new LineLayer({
        id: 'edges',
        data: edgeData,
        getSourcePosition: e => isAggregated ? e.fromPos : (positionById.get(e.from) ?? [0, 0]),
        getTargetPosition: e => isAggregated ? e.toPos   : (positionById.get(e.to)   ?? [0, 0]),
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
        updateTriggers: { getColor: [selectedId, aggregateEdges] },
        pickable: false,
      }));
    }
  }

  // Split singletons into "ordinary" (rendered under clusters) and
  // "selection-related" (rendered above clusters so they stay visible
  // even when they'd otherwise be covered by a cluster bubble).
  const singletonsBelow = selectedRelated
    ? singletons.filter(f => !selectedRelated.has(f.properties.id))
    : singletons;
  const singletonsAbove = selectedRelated
    ? singletons.filter(f => selectedRelated.has(f.properties.id))
    : [];

  // Individual authors — ScatterplotLayer (circles) OR IconLayer (shapes)
  if (viewMode === 'authors') {
    if (shapeBy === 'none') {
      layers.push(new ScatterplotLayer({
        id: 'authors',
        data: singletonsBelow,
        pickable: true,
        opacity: 0.85,
        stroked: true,
        filled: true,
        radiusMinPixels: 3,
        radiusMaxPixels: 18,
        lineWidthMinPixels: 0.5,
        getPosition: f => f.geometry.coordinates,
        getRadius: f => 30000 * Math.log2((f.properties.papers ?? 1) + 1),
        getFillColor: f => {
          const base = pickColour(f.properties, colorBy, palettes);
          if (selectedRelated && !selectedRelated.has(f.properties.id)) {
            return [base[0], base[1], base[2], 40];
          }
          return base;
        },
        getLineColor: f =>
          (selectedId && f.properties.id === selectedId)
            ? [182, 134, 44, 255]
            : [40, 40, 40, 180],
        getLineWidth: f => (selectedId && f.properties.id === selectedId) ? 2.5 : 0.5,
        lineWidthUnits: 'pixels',
        onClick: info => { if (info.object) setSelectedId(info.object.properties.id); },
        updateTriggers: {
          getFillColor: [colorBy, selectedId, palettes],
          getLineColor: [selectedId],
          getLineWidth: [selectedId],
        },
      }));
    } else {
      // IconLayer path — procedural shape atlas, area-equivalent across
      // circle / triangle / square. See src/lib/shapes.js.
      layers.push(new IconLayer({
        id: 'authors-shaped',
        data: singletonsBelow,
        pickable: true,
        iconAtlas: getIconAtlas(),
        iconMapping: ICON_MAPPING,
        sizeUnits: 'pixels',
        sizeMinPixels: 8,
        sizeMaxPixels: 48,
        getPosition: f => f.geometry.coordinates,
        getIcon: f => pickShape(f.properties, shapeBy),
        getSize: f => 6 + Math.log2((f.properties.papers ?? 1) + 1) * 4,
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
        },
      }));
    }

    if (clusterPoints.length > 0 && clusterIndex) {
      // Per-cluster gender tally via supercluster.getLeaves.
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
        getSize:     d => 28 + Math.sqrt(d.cluster.properties.point_count) * 4,
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
        updateTriggers: { getIcon: [clusterStats.length] },
      }));

      layers.push(new TextLayer({
        id: 'cluster-labels',
        data: clusterStats,
        pickable: false,
        getPosition: d => d.cluster.geometry.coordinates,
        getText: d => String(
          d.cluster.properties.point_count_abbreviated ?? d.cluster.properties.point_count
        ),
        getSize: 16,
        getColor: [255, 255, 255, 255],
        getTextAnchor: 'middle',
        getAlignmentBaseline: 'center',
        outlineWidth: 4,
        outlineColor: [30, 30, 30, 230],
        fontSettings: { sdf: true, radius: 16 },
        fontWeight: 700,
      }));
    }

    // Selection-related singletons rendered ABOVE the cluster bubbles so
    // you (Simon) stay visible even when sitting on top of a cluster.
    if (singletonsAbove.length > 0) {
      layers.push(new ScatterplotLayer({
        id: 'authors-above',
        data: singletonsAbove,
        pickable: true,
        opacity: 1,
        stroked: true,
        filled: true,
        radiusMinPixels: 5,
        radiusMaxPixels: 22,
        lineWidthMinPixels: 1,
        getPosition: f => f.geometry.coordinates,
        getRadius: f => 30000 * Math.log2((f.properties.papers ?? 1) + 1),
        getFillColor: f => pickColour(f.properties, colorBy, palettes),
        getLineColor: f => (selectedId && f.properties.id === selectedId)
          ? [182, 134, 44, 255] : [30, 30, 30, 220],
        getLineWidth: f => (selectedId && f.properties.id === selectedId) ? 3 : 1,
        lineWidthUnits: 'pixels',
        onClick: info => { if (info.object) setSelectedId(info.object.properties.id); },
        updateTriggers: {
          getFillColor: [colorBy, palettes],
          getLineColor: [selectedId],
          getLineWidth: [selectedId],
        },
      }));
    }
  }

  // Author-name labels. Show only when the visible singletons are
  // few enough to read (≤20 by default) OR when a selection is active,
  // in which case we label the selected author + their coauthors.
  //
  // Stacking policy:
  //   - Authors at the same lat/lon (same institution) get stacked
  //     VERTICALLY: most-prolific on top (below the dot), then each
  //     successive name on the next row down, 18px apart.
  //   - Authors at different positions still use CollisionFilter —
  //     when two groups' labels overlap, the higher-priority group's
  //     wins. Inside a group, ALL members show (stacked) regardless.
  if (viewMode === 'authors') {
    let labelled = [];
    if (selectedRelated) {
      labelled = singletons.filter(f => selectedRelated.has(f.properties.id));
    } else if (singletons.length > 0 && singletons.length <= 20) {
      labelled = singletons;
    }
    if (labelled.length > 0) {
      // Group by rounded coordinates (same institution = same row stack)
      const rowIndex = new Map();
      const groupMax = new Map();
      const groupKey = (f) =>
        `${f.geometry.coordinates[0].toFixed(3)},${f.geometry.coordinates[1].toFixed(3)}`;
      const byGroup = new Map();
      labelled.forEach(f => {
        const k = groupKey(f);
        const arr = byGroup.get(k) ?? [];
        arr.push(f);
        byGroup.set(k, arr);
      });
      byGroup.forEach((group, k) => {
        group.sort((a, b) => (b.properties.papers ?? 0) - (a.properties.papers ?? 0));
        const maxPapers = group[0].properties.papers ?? 1;
        group.forEach((f, i) => {
          rowIndex.set(f.properties.id, i);
          groupMax.set(f.properties.id, maxPapers);
        });
      });

      layers.push(new TextLayer({
        id: 'author-labels',
        data: labelled,
        pickable: false,
        getPosition: f => f.geometry.coordinates,
        getText: f => f.properties.name ?? '',
        getSize: 16,
        getColor: [15, 15, 15, 255],
        getPixelOffset: f => [0, 22 + (rowIndex.get(f.properties.id) ?? 0) * 18],
        getTextAnchor: 'middle',
        getAlignmentBaseline: 'top',
        outlineWidth: 6,
        outlineColor: [255, 255, 255, 250],
        fontSettings: { sdf: true, radius: 20 },
        background: false,
        // Cross-group collision: higher-paper-count group wins when two
        // groups' columns overlap. Members of the same group all carry
        // the same priority (their institution's top author's papers)
        // so they travel together.
        extensions: [new CollisionFilterExtension()],
        collisionEnabled: true,
        collisionGroup: 'author-labels',
        getCollisionPriority: f =>
          Math.log2((groupMax.get(f.properties.id) ?? 1) + 1),
      }));
    }
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
    if (object.properties?.cluster) {
      return {
        text: `${object.properties.point_count_abbreviated ?? object.properties.point_count} authors · click to zoom in`,
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
        />
      )}
    </div>
  );
}
