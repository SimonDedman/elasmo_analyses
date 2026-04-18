// Fetch helpers. Path resolves against Vite BASE_URL so dev and the deployed
// GH-Pages build both work without patching call sites.
const DATA_BASE = `${import.meta.env.BASE_URL}data`;

export async function loadJSON(path) {
  const res = await fetch(`${DATA_BASE}/${path}`);
  if (!res.ok) throw new Error(`${path}: ${res.status} ${res.statusText}`);
  return res.json();
}

export const loadAuthors      = () => loadJSON('authors.geojson');
export const loadInstitutions = () => loadJSON('institutions.geojson');
export const loadEdges        = () => loadJSON('edges.json');
export const loadStats        = () => loadJSON('stats.json');
