// Cluster icons: vertical bands in the active colour-by palette.
// PRIVACY 2026-10-16: inferred attributes kept local only (outputs/), never published

const CACHE = new Map();
const SIZE = 96;

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
