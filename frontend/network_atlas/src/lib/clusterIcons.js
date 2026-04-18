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

  // Draw three vertical bands, clipped to the circle
  ctx.fillStyle = 'rgb(55, 126, 184)';           // M = blue
  ctx.fillRect(cx - R, cy - R, R + x1,          2 * R);

  if (uFrac > 0) {
    ctx.fillStyle = 'rgb(140, 140, 140)';        // U = grey
    ctx.fillRect(cx + x1, cy - R, x2 - x1,      2 * R);
  }

  ctx.fillStyle = 'rgb(228, 26, 28)';            // F = red/pink
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
