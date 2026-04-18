// Procedural shape atlas for IconLayer. Shapes are area-equivalent:
// a square with side s_s, a triangle with side s_t, and a circle with
// diameter d_c all enclose the same pixel-area within their atlas cells.
//
// Relationships (for same area A):
//   circle diameter d_c  = 2 * sqrt(A / pi)
//   square side     s_s  = d_c * sqrt(pi) / 2   ≈ 0.886 * d_c
//   triangle side   s_t  = d_c * sqrt(pi/sqrt(3)) ≈ 1.347 * d_c
//
// Atlas cell is 160px wide so the triangle (~128px side) fits without
// clipping. Circle diameter 95 gives visual parity with the triangle's
// footprint; all three look "the same size" at equal iconSize.
//
// All shapes drawn in white with `mask: true` in iconMapping, so the
// IconLayer's per-feature getColor tints them at render time.

const CELL    = 160;
const CIRCLE_D = 95;                                   // diameter
const SQUARE_S = CIRCLE_D * Math.sqrt(Math.PI) / 2;    // ≈ 84
const TRIANGLE_S = CIRCLE_D * Math.sqrt(Math.PI / Math.sqrt(3)); // ≈ 128

export const ICON_ATLAS_SIZE = [CELL * 3, CELL];

export const ICON_MAPPING = {
  circle:   { x: 0,          y: 0, width: CELL, height: CELL,
              anchorX: CELL / 2, anchorY: CELL / 2, mask: true },
  triangle: { x: CELL,       y: 0, width: CELL, height: CELL,
              anchorX: CELL / 2, anchorY: CELL / 2, mask: true },
  square:   { x: CELL * 2,   y: 0, width: CELL, height: CELL,
              anchorX: CELL / 2, anchorY: CELL / 2, mask: true },
};

// Generate a PNG data URL at module-load time. Runs once per tab.
function buildAtlas() {
  const canvas = document.createElement('canvas');
  canvas.width  = ICON_ATLAS_SIZE[0];
  canvas.height = ICON_ATLAS_SIZE[1];
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = '#ffffff';

  // Circle (cell 0)
  const cx0 = CELL / 2, cy = CELL / 2;
  ctx.beginPath();
  ctx.arc(cx0, cy, CIRCLE_D / 2, 0, Math.PI * 2);
  ctx.fill();

  // Triangle (cell 1) — equilateral, base down
  const cx1 = CELL * 1.5;
  const h = (TRIANGLE_S * Math.sqrt(3)) / 2;
  ctx.beginPath();
  ctx.moveTo(cx1,                  cy - h / 2);
  ctx.lineTo(cx1 - TRIANGLE_S / 2, cy + h / 2);
  ctx.lineTo(cx1 + TRIANGLE_S / 2, cy + h / 2);
  ctx.closePath();
  ctx.fill();

  // Square (cell 2)
  const cx2 = CELL * 2.5;
  ctx.fillRect(cx2 - SQUARE_S / 2, cy - SQUARE_S / 2, SQUARE_S, SQUARE_S);

  return canvas.toDataURL('image/png');
}

// Lazy singleton — avoids running in SSR/Node environments that lack DOM.
let _atlas = null;
export function getIconAtlas() {
  if (typeof document === 'undefined') return null;
  if (_atlas === null) _atlas = buildAtlas();
  return _atlas;
}

// Shape mapping per attribute. Only `gender` is wired for now — see
// docs/SubProjects/author_atlas_v2_open_questions.md for rationale.
export const SHAPE_BY_GENDER = {
  M: 'circle',
  F: 'triangle',
  Unknown: 'square',
};

export function pickShape(props, shapeBy) {
  if (shapeBy === 'none') return 'circle';
  if (shapeBy === 'gender') return SHAPE_BY_GENDER[props.gender] ?? 'square';
  // origin_region: stub — would need an 11-way shape palette
  return 'circle';
}
