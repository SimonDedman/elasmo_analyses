// Keyless MapLibre styles + Stadia Stamen variants.
// Stadia API key via env var VITE_STADIA_KEY (registered to the site's
// domain — localhost works without, deployment needs the key attached).

const STADIA_KEY = import.meta.env.VITE_STADIA_KEY || '';
const stadia = (style) =>
  `https://tiles.stadiamaps.com/styles/${style}.json${STADIA_KEY ? `?api_key=${STADIA_KEY}` : ''}`;

export const BASEMAPS = {
  voyager: {
    label: 'Carto Voyager',
    url:   'https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json',
  },
  positron: {
    label: 'Carto Positron (light)',
    url:   'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
  },
  darkmatter: {
    label: 'Carto Dark Matter',
    url:   'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
  },
  stamenTerrain: {
    label: 'Stamen Terrain (Stadia)',
    url:   stadia('stamen_terrain'),
  },
  stamenToner: {
    label: 'Stamen Toner Lite (Stadia)',
    url:   stadia('stamen_toner_lite'),
  },
  alidade: {
    label: 'Stadia Alidade Smooth',
    url:   stadia('alidade_smooth'),
  },
};

export const DEFAULT_BASEMAP = 'voyager';
