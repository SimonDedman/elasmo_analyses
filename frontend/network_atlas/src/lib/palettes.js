// Palettes for colour-by modes. Each palette maps a categorical value to
// an RGBA colour array. Keys missing from a palette fall through to grey.

export const GENDER_PALETTE = {
  M: [55, 126, 184, 220],
  F: [228, 26, 28, 220],
  Unknown: [150, 150, 150, 180],
};

export const REGION_PALETTE = {
  'Europe':           [55, 126, 184, 220],
  'North America':    [228, 26, 28, 220],
  'South America':    [255, 127, 0, 220],
  'Africa':           [77, 175, 74, 220],
  'East Asia':        [152, 78, 163, 220],
  'South Asia':       [141, 160, 203, 220],
  'South-East Asia':  [166, 216, 84, 220],
  'Muslim':           [102, 194, 165, 220],
  'Central Asia':     [247, 129, 191, 220],
  'Oceania':          [255, 215, 0, 220],
  'Unknown':          [150, 150, 150, 180],
};

// 20-colour country palette; applied to top-N by author count, rest grey.
export const COUNTRY_PALETTE_COLOURS = [
  [228, 26, 28], [55, 126, 184], [77, 175, 74], [152, 78, 163], [255, 127, 0],
  [255, 215, 0], [166, 86, 40], [247, 129, 191], [23, 190, 207], [102, 194, 165],
  [252, 141, 98], [141, 160, 203], [231, 138, 195], [166, 216, 84], [106, 61, 154],
  [229, 196, 148], [140, 86, 75], [27, 158, 119], [217, 95, 2], [117, 112, 179],
];

export function buildCountryPalette(topCountries) {
  const pal = {};
  topCountries.slice(0, 20).forEach((c, i) => {
    pal[c] = [...COUNTRY_PALETTE_COLOURS[i], 220];
  });
  return pal;
}

export function pickColour(props, colorBy, palettes) {
  const key = props[colorBy];
  if (!key) return [150, 150, 150, 180];
  const pal = palettes[colorBy];
  if (pal && pal[key]) return pal[key];
  return [150, 150, 150, 180];
}
