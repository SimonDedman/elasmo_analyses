import Legend from './Legend.jsx';
import { BASEMAPS } from '../lib/basemaps.js';

export default function FilterPanel({
  filters, setFilters,
  colorBy, setColorBy,
  shapeBy, setShapeBy,
  showEdges, setShowEdges,
  showClusters, setShowClusters,
  aggregateEdges, setAggregateEdges,
  viewMode, setViewMode,
  basemap, setBasemap,
  searchQuery, setSearchQuery, onSearchSubmit,
  searchTarget, setSearchTarget,
  institutionNames,
  selectedAuthor, onClearSelection,
  stats, authorCount, totalAuthors, edgeCount,
  institutionCount,
  originRegions, palettes,
  authorNames,
  genderCounts, regionCounts,     // {key: n, …}
  shapeByMatrix,                  // [{attr, n_categories, top}, …]
  zoomLevel,
  version,
}) {
  // Helper for "(123)" suffixes sorted by count desc
  const sortedWithCounts = (obj, keys) =>
    keys
      .map(k => [k, obj[k] ?? 0])
      .sort((a, b) => b[1] - a[1]);
  const update = (k, v) => setFilters(prev => ({ ...prev, [k]: v }));
  const topCountries = Object.entries(stats?.by_country ?? {});

  return (
    <div className="filter-panel">
      <h1>
        Elasmobranch Author Atlas{' '}
        <span className="tag">
          v{version ?? '2'}{zoomLevel != null ? ` · z${zoomLevel.toFixed(1)}` : ''} · wasd to pan
        </span>
      </h1>
      <div className="stats">
        {viewMode === 'authors' ? (
          <>
            <strong>{authorCount.toLocaleString()}</strong> / {totalAuthors.toLocaleString()} authors,{' '}
            <strong>{edgeCount.toLocaleString()}</strong> edges
          </>
        ) : (
          <>
            <strong>{institutionCount.toLocaleString()}</strong> institutions
          </>
        )}
      </div>

      <label>View</label>
      <select value={viewMode} onChange={e => setViewMode(e.target.value)}>
        <option value="authors">Authors (individual)</option>
        <option value="institutions">Institutions (aggregated)</option>
      </select>

      <label>Base map</label>
      <select value={basemap} onChange={e => setBasemap(e.target.value)}>
        {Object.entries(BASEMAPS).map(([key, { label }]) => (
          <option key={key} value={key}>{label}</option>
        ))}
      </select>

      <label>Search {searchTarget === 'author' ? 'author' : 'institution'}</label>
      <div style={{ display: 'flex', gap: 4, marginBottom: 4 }}>
        <select
          value={searchTarget}
          onChange={e => { setSearchTarget(e.target.value); setSearchQuery(''); }}
          style={{ width: '40%' }}
        >
          <option value="author">Author</option>
          <option value="institution">Institution</option>
        </select>
        <input
          type="text"
          list="search-list"
          value={searchQuery}
          placeholder="Start typing…"
          onChange={e => setSearchQuery(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') onSearchSubmit(); }}
          onBlur={onSearchSubmit}
          style={{ flex: 1 }}
        />
      </div>
      <datalist id="search-list">
        {(searchTarget === 'author' ? authorNames : institutionNames)
          .map(n => <option key={n} value={n} />)}
      </datalist>

      {viewMode === 'authors' && (
        <>
          <label>Country</label>
          <select value={filters.country} onChange={e => update('country', e.target.value)}>
            <option value="">All</option>
            {topCountries.map(([c, n]) => (
              <option key={c} value={c}>{c} ({n.toLocaleString()})</option>
            ))}
          </select>

          <label>Gender</label>
          <select value={filters.gender} onChange={e => update('gender', e.target.value)}>
            <option value="">All</option>
            {sortedWithCounts(genderCounts ?? {}, ['M', 'F', 'Unknown'])
              .map(([k, n]) => (
                <option key={k} value={k}>
                  {k === 'M' ? 'Male' : k === 'F' ? 'Female' : k} ({n.toLocaleString()})
                </option>
              ))}
          </select>

          <label>Origin region (NamSor)</label>
          <select value={filters.origin_region} onChange={e => update('origin_region', e.target.value)}>
            <option value="">All</option>
            {sortedWithCounts(regionCounts ?? {}, originRegions).map(([r, n]) => (
              <option key={r} value={r}>{r} ({n.toLocaleString()})</option>
            ))}
          </select>

          <label>
            Min edge weight: <strong>{filters.minEdgeWeight}</strong>
          </label>
          <input
            type="range" min="1" max="20" step="1"
            value={filters.minEdgeWeight}
            onChange={e => update('minEdgeWeight', parseInt(e.target.value, 10))}
          />

          {stats?.year_min != null && stats?.year_max != null && (() => {
            const lo = filters.yearMin ?? stats.year_min;
            const hi = filters.yearMax ?? stats.year_max;
            return (
              <>
                <label>
                  Year range: <strong>{lo}</strong>–<strong>{hi}</strong>
                </label>
                <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                  <input
                    type="range" min={stats.year_min} max={stats.year_max} step="1"
                    value={lo}
                    onChange={e => {
                      const v = parseInt(e.target.value, 10);
                      update('yearMin', Math.min(v, hi));
                    }}
                    style={{ flex: 1 }}
                  />
                  <input
                    type="range" min={stats.year_min} max={stats.year_max} step="1"
                    value={hi}
                    onChange={e => {
                      const v = parseInt(e.target.value, 10);
                      update('yearMax', Math.max(v, lo));
                    }}
                    style={{ flex: 1 }}
                  />
                </div>
              </>
            );
          })()}

          <label>Colour by</label>
          <select value={colorBy} onChange={e => setColorBy(e.target.value)}>
            <option value="gender">Gender</option>
            <option value="country">Country (top 20)</option>
            <option value="origin_region">Origin region</option>
          </select>

          <label>Shape by</label>
          <select value={shapeBy} onChange={e => setShapeBy(e.target.value)}>
            <option value="none">None (all circles)</option>
            <option value="gender">Gender (M=○ F=△ Unknown=□)</option>
          </select>
          {shapeByMatrix && shapeByMatrix.length > 0 && (
            <div className="shape-suggest">
              <span className="muted">Best shape-by attrs in current filter (fewest categories first):</span>
              <ul>
                {shapeByMatrix.map(row => (
                  <li key={row.attr}>
                    <strong>{row.attr}</strong>: {row.n_categories} categories
                    {row.top.length > 0 && <> — top: {row.top.join(', ')}</>}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="toggles">
            <label>
              <input type="checkbox" checked={showEdges}
                     onChange={e => setShowEdges(e.target.checked)} />
              Show edges
            </label>
            <label>
              <input type="checkbox" checked={showClusters}
                     onChange={e => setShowClusters(e.target.checked)} />
              Cluster at low zoom
            </label>
            <label>
              <input type="checkbox" checked={aggregateEdges}
                     onChange={e => setAggregateEdges(e.target.checked)} />
              Group lines per institution
            </label>
          </div>

          <Legend colorBy={colorBy} palettes={palettes} />
        </>
      )}

      {selectedAuthor && (
        <div className="selected-info">
          <div><strong>{selectedAuthor.properties.name}</strong></div>
          <div className="muted">{selectedAuthor.properties.institution ?? '—'}</div>
          <div className="muted">
            {selectedAuthor.properties.papers} papers · {selectedAuthor.properties.gender}
          </div>
          <button className="clear" onClick={onClearSelection}>Clear selection</button>
        </div>
      )}

      <button
        className="reset"
        onClick={() => {
          setFilters({ country: '', gender: '', origin_region: '', minEdgeWeight: 2,
                       yearMin: null, yearMax: null });
          setSearchQuery('');
          onClearSelection();
        }}
      >
        Reset filters
      </button>
    </div>
  );
}
