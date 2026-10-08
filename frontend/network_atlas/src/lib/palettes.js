// Palettes for colour-by modes. Each palette maps a categorical value to
// an RGBA colour array. Keys missing from a palette fall through to grey.

// Classic nursery-boy / nursery-girl pantones, saturated enough to read
// on a light basemap:
//   M — Pantone 284 C "Baby Blue"   ≈ #82B5DC  rgb(130, 181, 220)
//   F — Pantone 183 C "Baby Pink"   ≈ #F28FB0  rgb(242, 143, 176)
export const GENDER_PALETTE = {
  M: [130, 181, 220, 230],
  F: [242, 143, 176, 230],
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

// 19 research disciplines + Unclassified. Distinct hues (Tableau-20 style) so adjacent
// bubbles in a cluster remain separable; 'Unclassified' is neutral grey.
export const DISCIPLINE_COLOURS = {
  'Conservation':     [44, 160, 44],
  'Biology':          [31, 119, 180],
  'Genetics':         [148, 103, 189],
  'Paleontology':     [140, 86, 75],
  'Taxonomy':         [188, 189, 34],
  'Physiology':       [214, 39, 40],
  'Immunology':       [227, 119, 194],
  'Reproductive':     [255, 152, 150],
  'Movement':         [23, 190, 207],
  'Trophic':          [255, 127, 14],
  'Behaviour':        [174, 199, 232],
  'Fisheries':        [0, 90, 120],
  'Sensory':          [197, 176, 213],
  'Toxicology':       [127, 127, 0],
  'Biomechanics':     [152, 223, 138],
  'Husbandry':        [196, 156, 148],
  'Ecotourism':       [255, 215, 0],
  'Human Dimensions': [100, 60, 160],
  'Data Science':     [60, 60, 60],
};

// Palette limited to the disciplines present, most common first.
export function buildDisciplinePalette(counts) {
  const pal = {};
  Object.entries(counts).sort((a, b) => b[1] - a[1]).forEach(([k]) => {
    if (k === 'Unclassified') return;
    pal[k] = [...(DISCIPLINE_COLOURS[k] ?? [120, 120, 120]), 225];
  });
  if (counts.Unclassified) pal.Unclassified = [150, 150, 150, 180];
  return pal;
}
