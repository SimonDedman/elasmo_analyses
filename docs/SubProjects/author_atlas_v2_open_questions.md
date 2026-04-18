# Author Atlas v2 — open questions for review

Queued during the autonomous step-5 session (2026-04-17). Best-guess defaults
taken; every one is reversible with a one-liner change. Answer at your leisure.

## 1. Shape-per-attribute — implementation choice

The `shapeBy` dropdown exists but is currently a no-op (renders circles).
Before wiring the IconLayer, three decisions:

### 1a. Which attribute drives shape?

- **Gender only** (3 values: M / F / Unknown → circle / triangle / square).
  **Best-guess default**, since gender has few enough categories for shape
  encoding to stay legible.
- **Origin region** has 11 values; shapes get muddled beyond 4–5.
- **Country** is out of the question (>150 values).

Unless you want a custom grouping (hemisphere? continent?) I'll wire shape-by
for gender only.

### 1b. Shape ↔ category mapping

Default guess:
- M = circle
- F = triangle (pointing up)
- Unknown = square

Any reason to flip that (e.g. "triangle feels gendered")? I can also do
diamond/hexagon if you want less loaded shapes.

### 1c. Size equivalence

Two options, both reasonable:
- **Area-equivalent**: n papers produces the same *visual area* across
  shapes. Requires tuning shape side ratios (triangle side ≈ 1.35 × circle
  diameter; square side ≈ 0.89 × circle diameter). Most faithful to
  "same n = same magnitude".
- **Bounding-box-equivalent**: n papers produces the same *width/height*
  across shapes. Areas differ (triangle looks smaller, square looks
  bigger). Simpler code.

**Best-guess default: area-equivalent.** Matches your original concern that
"the same n looks different as a square than a circle."

## 2. Stamen Terrain comparator

Stamen Terrain via Stadia Maps **requires an API key** for off-localhost use.
Free tier exists (200,000 requests/month), but the key must be issued to a
registered domain.

**Best-guess default: replaced with MapLibre demotiles (Natural Earth)** in
the Base map dropdown. This gives you the "lighter, NE-based" comparator
for free with no signup.

To add real Stamen later:
1. Sign up at <https://stadiamaps.com/> (free).
2. Whitelist `simondedman.github.io` in the Stadia dashboard.
3. Add the API key to `frontend/network_atlas/.env` as `VITE_STADIA_KEY`.
4. Uncomment the Stamen entries in `src/lib/basemaps.js` (I'll leave the
   commented stub when you say go).

## 3. Label density at high zoom

Currently no author labels at any zoom — only hover tooltip. Your v1
feedback said labels should appear as you zoom in. Three knobs:

- **Always-off** (current).
- **Show labels when ≤20 visible authors**. Simple, conservative.
- **Leader-line callouts**: labels placed in whitespace with lines back to
  points. Requires a custom layer (`@deck.gl/react-map-gl-labels` or
  hand-rolled). ~half-day of work.

**Best-guess default: option 2** (show when ≤20 visible) after you confirm.

## 4. Edges at low zoom — cluster-to-cluster lines?

Currently edges hide when you zoom out and their endpoints get clustered
into institution bubbles. Three options:

- **Keep current** (edges disappear at low zoom with their endpoints).
- **Aggregate to cluster-pair edges**: when two authors' edge spans two
  clusters, draw one line between cluster centres weighted by the
  underlying edge count. Visually clearer at continental zoom.
- **Always render all edges**: messy but complete.

**Best-guess default: keep current.** Aggregation is step-7 material.

## 5. Search — scope and behaviour

Currently: searches in `authors` view only, datalist shows top 200 by paper
count, on submit jumps to author + zoom 6 + selects.

Confirm:
- Should search work in institutions view too (jump to institution)?
- Should it respect active country/gender/region filters, or search the
  full author set and bypass filters?
- Should it accept partial matches (currently yes, but only the first hit
  is used)?

**Best-guess default**: author-view only, respects filters, first hit.

## 6. Performance budget for the build

Current: ~1.7 MB JS (gzip 465 KB) + 5.5 MB data. Four gzipped files on
first load. Acceptable for a showcase but not mobile-friendly.

Tolerable? Or should we code-split MapLibre into its own async chunk so
the filter panel can render before the base map finishes loading?

**Best-guess default: leave as-is** until we see it deployed and can judge.

## 7. Deploy flow

Currently `npm run build` writes to `docs/network_atlas/`. To deploy:
1. Rebuild data: `Rscript scripts/build_author_atlas.R`
2. Refresh frontend data: `cd frontend/network_atlas && npm run copy-data`
3. Build: `npm run build`
4. Commit `docs/network_atlas/` and push.

Want me to wrap this in a single `scripts/deploy_atlas.sh` or a make
target?

**Best-guess default: yes, one helper script.** Will add when you confirm.


Misc notes:
- replace hand icon with standard arrow, hand makes it hard to see where you're pointing & overlaps content
- offset floating mouseover content from cursor else cursor covers top left content of box
- Goldbogen is at Hopkins Marine Station in Pacific Grove. Check all Stanford employees for this.
- UCSC researchers e.g. Bograd: many are based at the NOAA office in Pacific Grove/Monterey: check these.

1a. shape per attribute: moot if all authors are under the one with the most publications per institute - everyone is assigned that gender. Return to Issue once position dodging is solved.
1b seems fine.
1c. area equivalent sounds fine

2. maplibre demotiles sucks - it's just green? I thought it had terrain?
Carto voyager is better, unless demotiles can be improved - is it only valid for that area of germany?
I'll setup the stamen API later, I think I already have one. stadia: 0aa446de-fa73-491c-8ffd-c6cd1f0e7e96

3. show labels when ≤20 visible sounds good; can explore leader line callouts based on how the existing implementation looks

4. edges don't noticeably disappear currently (may relate to 1a issue). Can we have the aggregation option as a toggle?

5. could you add an institution search as well? Start with respecting filters but I might change that.

6. Fine as is; are we currently using all data or only the subset? Looks like all. If so, performance is great and <7.5mb is fine.

7. A helper script would be good, but I think we should also add a GitHub Action to automate the deploy on push to main.