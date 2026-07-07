// Fetch helpers. Path resolves against Vite BASE_URL so dev and the deployed
// GH-Pages build both work without patching call sites.
const DATA_BASE = `${import.meta.env.BASE_URL}data`;

// Cache-buster: GitHub Pages / CDN caches the (non-hashed) .geojson data files,
// so a data-only redeploy can keep serving stale coordinates to browsers even on
// a hard refresh. Bump DATA_VERSION whenever the data files change to force a
// fresh fetch from a new URL. (2026-07-07: bumped for the baked geoDodge coords.)
const DATA_VERSION = 'dodge-20260707';

export async function loadJSON(path) {
  const res = await fetch(`${DATA_BASE}/${path}?v=${DATA_VERSION}`, { cache: 'no-cache' });
  if (!res.ok) throw new Error(`${path}: ${res.status} ${res.statusText}`);
  return res.json();
}

export const loadAuthors      = () => loadJSON('authors.geojson');
export const loadInstitutions = () => loadJSON('institutions.geojson');
export const loadEdges        = () => loadJSON('edges.json');
export const loadStats        = () => loadJSON('stats.json');
