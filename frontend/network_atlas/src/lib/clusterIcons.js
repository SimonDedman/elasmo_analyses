// Per-cluster icon generator: a circle split horizontally into three
// proportional bands — blue (M) on the left, grey (U) in the middle,
// red (F) on the right. Cached by (M_bucket, F_bucket) so we don't
// regenerate canvas images for every re-render.

const CACHE = new Map();
const SIZE = 96;

function makeIcon(mFrac, uFrac, fFrac) {
  const canvas = document.createElement('canvas');
  canvas.width = SIZE;
  canvas.height = SIZE;
  const ctx = canvas.getContext('2d');
  const R = SIZE / 2 - 3;
  const cx = SIZE / 2, cy = SIZE / 2;

  // Clip to circle
  ctx.save();
  ctx.beginPath();
  ctx.arc(cx, cy, R, 0, 2 * Math.PI);
  ctx.clip();

  // Horizontal band positions (in local -R..+R coords)
  const x1 = -R + 2 * R * mFrac;                 // M | U boundary
  const x2 = x1 + 2 * R * uFrac;                 // U | F boundary

  // Draw three vertical bands, clipped to the circle. Colours match
  // GENDER_PALETTE in palettes.js — Pantone 284 C baby-blue for M,
  // Pantone 183 C baby-pink for F.
  ctx.fillStyle = 'rgb(130, 181, 220)';          // M = baby blue
  ctx.fillRect(cx - R, cy - R, R + x1,          2 * R);

  if (uFrac > 0) {
    ctx.fillStyle = 'rgb(140, 140, 140)';        // U = grey
    ctx.fillRect(cx + x1, cy - R, x2 - x1,      2 * R);
  }

  ctx.fillStyle = 'rgb(242, 143, 176)';          // F = baby pink
  ctx.fillRect(cx + x2, cy - R, R - x2,         2 * R);

  ctx.restore();

  // Circle outline (not clipped)
  ctx.beginPath();
  ctx.arc(cx, cy, R, 0, 2 * Math.PI);
  ctx.strokeStyle = 'rgba(255,255,255,0.95)';
  ctx.lineWidth = 2;
  ctx.stroke();

  return canvas.toDataURL('image/png');
}

export function getClusterIcon(m, u, f) {
  const total = m + u + f || 1;
  // Bucket fractions to 5% to bound the cache.
  const mb = Math.round((m / total) * 20);
  const ub = Math.round((u / total) * 20);
  const fb = 20 - mb - ub;
  const key = `${mb}-${ub}-${fb}`;
  let url = CACHE.get(key);
  if (!url) {
    url = makeIcon(mb / 20, ub / 20, fb / 20);
    CACHE.set(key, url);
  }
  return { url, width: SIZE, height: SIZE, anchorX: SIZE / 2, anchorY: SIZE / 2 };
}

// Generic cluster icon for any colour-by mode: vertical bands, largest share
// first, each in its palette colour (grey for values without one).
// `parts` = [[rgbArray, count], ...]. Cached on 5 % buckets.
export function getCategoryClusterIcon(parts) {
  // Parts that share a colour are one category on screen (all greyed-out disciplines, or
  // Unclassified + missing values), so merge them into a single band. Every real category
  // keeps its own band (no grey "rest" lump that reads as unknown); greys go last.
  const merged = new Map();
  parts.forEach(([c, n]) => { if (n > 0) { const k = c.slice(0, 3).join('.'); const e = merged.get(k);
    if (e) e[1] += n; else merged.set(k, [c, n]); } });
  const isGrey = c => c[0] === c[1] && c[1] === c[2];
  const sorted = [...merged.values()].sort((a, b) => (isGrey(a[0]) - isGrey(b[0])) || (b[1] - a[1]));
  const total = sorted.reduce((a, [, n]) => a + n, 0) || 1;
  const bands = sorted.map(([c, n]) => [c, Math.max(1, Math.round((n / total) * 20))]);
  const key = 'cat:' + bands.map(([c, b]) => c.slice(0, 3).join('.') + 'x' + b).join('|');
  let url = CACHE.get(key);
  if (!url) {
    const canvas = document.createElement('canvas'); canvas.width = SIZE; canvas.height = SIZE;
    const ctx = canvas.getContext('2d'); const R = SIZE / 2 - 3, cx = SIZE / 2, cy = SIZE / 2;
    ctx.save(); ctx.beginPath(); ctx.arc(cx, cy, R, 0, 2 * Math.PI); ctx.clip();
    const sum = bands.reduce((a, [, b]) => a + b, 0); let x = cx - R;
    bands.forEach(([c, b]) => { const w = 2 * R * b / sum; ctx.fillStyle = `rgb(${c[0]},${c[1]},${c[2]})`; ctx.fillRect(x, cy - R, w + 0.5, 2 * R); x += w; });
    ctx.restore(); ctx.beginPath(); ctx.arc(cx, cy, R, 0, 2 * Math.PI);
    ctx.strokeStyle = 'rgba(255,255,255,0.95)'; ctx.lineWidth = 2; ctx.stroke();
    url = canvas.toDataURL('image/png'); CACHE.set(key, url);
  }
  return { url, width: SIZE, height: SIZE, anchorX: SIZE / 2, anchorY: SIZE / 2 };
}
