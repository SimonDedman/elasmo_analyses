# Interactive Validation UI — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build static HTML validation pages (one per author) hosted on GitHub Pages, with structured review controls and a submission pipeline that creates GitHub PRs.

**Architecture:** A Python generation script reads the parquet, evidence CSV, and OpenAlex author CSVs, then produces ~28,952 static HTML files under `docs/validate/`. Each page embeds that author's paper data as JSON and uses shared JS/CSS for interactivity. Submission POSTs to a Cloudflare Worker proxy that forwards to a GitHub Action via `repository_dispatch`.

**Tech Stack:** Python (pyarrow, jinja2), vanilla JS, Tom Select (autocomplete), GitHub Actions, Cloudflare Workers

**Spec:** [docs/technical/2026-04-16-validation-ui-design.md](../2026-04-16-validation-ui-design.md)

---

## File Structure

```
scripts/
  generate_validation_pages.py         # Main generation script
  templates/
    validate_page.html.j2              # Jinja2 template for per-author pages
    validate_index.html.j2             # Landing page template
    validate_404.html.j2               # 404 page template
    validate_redirect.html.j2          # Redirect page for merged secondary IDs
docs/
  404.html                             # Generated 404
  validate/
    index.html                         # Generated landing page
    assets/
      style.css                        # Shared CSS
      validate.js                      # Validation UI logic (localStorage, ratings, checkboxes)
      submit.js                        # Submission logic (JSON build, POST to proxy)
      tom-select.min.js                # Tom Select library (~15KB)
      tom-select.min.css               # Tom Select styles
    {openalex_id}.html                 # One per author (28,952 files)
.github/
  workflows/
    receive-validation.yml             # GitHub Action: receive dispatch, create PR
validations/                           # Empty dir, populated by PRs
```

---

### Task 1: Shared CSS (`docs/validate/assets/style.css`)

**Files:**
- Create: `docs/validate/assets/style.css`

- [ ] **Step 1: Create the assets directory**

```bash
mkdir -p "docs/validate/assets"
```

- [ ] **Step 2: Write the CSS file**

Create `docs/validate/assets/style.css` with these sections:

```css
/* === Reset & Base === */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  line-height: 1.5;
  color: #1a1a1a;
  background: #f8f9fa;
  padding: 1rem;
  max-width: 1400px;
  margin: 0 auto;
}

/* === Header === */
.page-header {
  background: #081E3F;
  color: white;
  padding: 1.5rem 2rem;
  border-radius: 8px;
  margin-bottom: 1.5rem;
}
.page-header h1 { font-size: 1.5rem; margin-bottom: 0.25rem; }
.page-header .meta { font-size: 0.85rem; opacity: 0.8; }
.page-header .merge-note {
  background: rgba(255,255,255,0.1);
  padding: 0.5rem;
  border-radius: 4px;
  margin-top: 0.5rem;
  font-size: 0.85rem;
}

/* === Paper Block === */
.paper-block {
  background: white;
  border: 1px solid #dee2e6;
  border-radius: 6px;
  margin-bottom: 0.75rem;
}
.paper-summary {
  padding: 0.75rem 1rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.95rem;
  user-select: none;
}
.paper-summary:hover { background: #f1f3f5; }
.paper-summary .chevron {
  transition: transform 0.15s;
  font-size: 0.7rem;
  color: #868e96;
}
.paper-block[open] .chevron { transform: rotate(90deg); }
.paper-summary .year { font-weight: 700; min-width: 3rem; }
.paper-summary .authors { color: #495057; }
.paper-summary .title { color: #1a1a1a; font-style: italic; flex: 1; }
.paper-summary .journal { color: #868e96; font-size: 0.85rem; }
.paper-summary .review-status {
  font-size: 0.75rem;
  padding: 0.15rem 0.5rem;
  border-radius: 10px;
  background: #e9ecef;
  color: #495057;
}
.paper-summary .review-status.reviewed {
  background: #d3f9d8;
  color: #2b8a3e;
}

/* === Metadata Row === */
.metadata-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  background: #f8f9fa;
  border-bottom: 1px solid #dee2e6;
  font-size: 0.8rem;
}
.metadata-row .meta-item {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
}
.metadata-row .meta-label { color: #868e96; }
.metadata-row .meta-value { font-weight: 500; }
.metadata-row a { color: #1971c2; text-decoration: none; }

/* === Category Section === */
.category-section {
  padding: 0.75rem 1rem;
  border-bottom: 1px solid #f1f3f5;
}
.category-section:last-child { border-bottom: none; }
.category-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}
.category-name {
  font-weight: 600;
  font-size: 0.9rem;
  color: #495057;
}

/* === Checkbox Grid === */
.checkbox-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
}
.cb-item {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  font-size: 0.8rem;
  border: 1px solid #dee2e6;
  background: white;
  cursor: pointer;
  transition: all 0.1s;
}
.cb-item:hover { border-color: #adb5bd; }
.cb-item.checked {
  background: #d3f9d8;
  border-color: #69db7c;
}
.cb-item.checked.original {
  background: #d0ebff;
  border-color: #74c0fc;
}
.cb-item.changed {
  outline: 2px solid #ffd43b;
  outline-offset: -1px;
}
.cb-item input[type="checkbox"] { margin: 0; }
.cb-item .cb-label {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 200px;
}

/* === Evidence Detail (expandable within a checkbox) === */
.evidence-detail {
  display: none;
  background: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 4px;
  padding: 0.5rem;
  margin: 0.35rem 0;
  font-size: 0.75rem;
  width: 100%;
}
.evidence-detail.open { display: block; }
.evidence-detail .ev-row { display: flex; gap: 0.5rem; margin-bottom: 0.2rem; }
.evidence-detail .ev-label { color: #868e96; min-width: 5rem; }
.evidence-detail .ev-value { color: #1a1a1a; }
.evidence-detail .context-snippet {
  font-style: italic;
  color: #495057;
  border-left: 2px solid #dee2e6;
  padding-left: 0.5rem;
  margin-top: 0.25rem;
}

/* === Rating Controls === */
.rating-controls {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-top: 0.5rem;
  font-size: 0.8rem;
}
.rating-controls label {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  cursor: pointer;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  border: 1px solid transparent;
}
.rating-controls input[type="radio"] { margin: 0; }
.rating-controls label:has(input:checked) {
  font-weight: 600;
}
.rating-correct:has(input:checked) { background: #d3f9d8; border-color: #69db7c; }
.rating-partial:has(input:checked) { background: #fff3bf; border-color: #ffd43b; }
.rating-incorrect:has(input:checked) { background: #ffe3e3; border-color: #ff8787; }

/* === Notes & Rule Feedback === */
.notes-field {
  width: 100%;
  padding: 0.4rem;
  border: 1px solid #dee2e6;
  border-radius: 4px;
  font-size: 0.8rem;
  resize: vertical;
  min-height: 2rem;
  margin-top: 0.35rem;
}
.rule-feedback {
  background: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 4px;
  padding: 0.5rem;
  margin-top: 0.5rem;
  font-size: 0.8rem;
}
.rule-feedback summary { cursor: pointer; color: #868e96; }
.rule-feedback .rf-row { display: flex; align-items: center; gap: 0.5rem; margin-top: 0.35rem; }
.rule-feedback input[type="number"] { width: 4rem; padding: 0.2rem; }
.rule-feedback input[type="text"] { flex: 1; padding: 0.2rem 0.4rem; }

/* === Tag-style items (species, techniques) === */
.tag-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  margin-bottom: 0.5rem;
}
.tag-item {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.15rem 0.5rem;
  border-radius: 12px;
  font-size: 0.78rem;
  background: #d0ebff;
  border: 1px solid #74c0fc;
  cursor: pointer;
}
.tag-item.removed {
  background: #ffe3e3;
  border-color: #ff8787;
  text-decoration: line-through;
}
.tag-item .remove-btn {
  font-size: 0.7rem;
  color: #868e96;
  cursor: pointer;
  margin-left: 0.15rem;
}
.autocomplete-wrapper { margin-top: 0.35rem; max-width: 400px; }

/* === Footer === */
.page-footer {
  position: sticky;
  bottom: 0;
  background: white;
  border-top: 2px solid #081E3F;
  padding: 0.75rem 1rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  z-index: 100;
  margin-top: 1rem;
}
.progress-bar {
  flex: 1;
  height: 0.5rem;
  background: #e9ecef;
  border-radius: 4px;
  overflow: hidden;
}
.progress-bar .fill {
  height: 100%;
  background: #081E3F;
  transition: width 0.3s;
}
.progress-text { font-size: 0.8rem; color: #495057; min-width: 8rem; text-align: right; }
.save-indicator { font-size: 0.75rem; color: #868e96; min-width: 10rem; }
.btn {
  padding: 0.5rem 1.25rem;
  border-radius: 6px;
  border: none;
  font-size: 0.85rem;
  cursor: pointer;
  font-weight: 500;
}
.btn-primary { background: #081E3F; color: white; }
.btn-primary:hover { background: #0c2d5e; }
.btn-secondary { background: #e9ecef; color: #495057; }
.btn-secondary:hover { background: #dee2e6; }

/* === Landing Page === */
.landing-container { max-width: 700px; margin: 3rem auto; text-align: center; }
.landing-container h1 { font-size: 2rem; color: #081E3F; margin-bottom: 0.5rem; }
.landing-container .subtitle { color: #495057; margin-bottom: 2rem; }
.search-box {
  width: 100%;
  padding: 0.75rem 1rem;
  font-size: 1.1rem;
  border: 2px solid #081E3F;
  border-radius: 8px;
  outline: none;
}
.search-box:focus { border-color: #B6862C; box-shadow: 0 0 0 3px rgba(182,134,44,0.2); }
.search-results {
  text-align: left;
  margin-top: 1rem;
}
.search-result {
  display: block;
  padding: 0.75rem 1rem;
  border: 1px solid #dee2e6;
  border-radius: 6px;
  margin-bottom: 0.5rem;
  text-decoration: none;
  color: inherit;
  transition: border-color 0.1s;
}
.search-result:hover { border-color: #081E3F; background: #f8f9fa; }
.search-result .sr-name { font-weight: 600; }
.search-result .sr-inst { color: #495057; font-size: 0.85rem; }
.search-result .sr-meta { color: #868e96; font-size: 0.8rem; }

/* === 404 Page === */
.four-oh-four { max-width: 600px; margin: 5rem auto; text-align: center; }
.four-oh-four h1 { font-size: 3rem; color: #081E3F; }
.four-oh-four p { color: #495057; margin-top: 1rem; font-size: 1.1rem; }
.four-oh-four a { color: #1971c2; }

/* === Depth override fields === */
.depth-display { display: flex; gap: 1rem; align-items: center; font-size: 0.85rem; }
.depth-display input[type="number"] { width: 5rem; padding: 0.2rem 0.4rem; border: 1px solid #dee2e6; border-radius: 4px; }
```

- [ ] **Step 3: Commit**

```bash
git add docs/validate/assets/style.css
git commit -m "feat(validate): add shared CSS for validation pages"
```

---

### Task 2: Validation UI JavaScript (`docs/validate/assets/validate.js`)

**Files:**
- Create: `docs/validate/assets/validate.js`

This file handles: reading embedded page data, rendering category sections, checkbox state management, rating controls, localStorage auto-save, and progress tracking. The page data is embedded in each HTML page as `window.PAGE_DATA` (set by the Jinja2 template).

- [ ] **Step 1: Write the validation JS**

Create `docs/validate/assets/validate.js`:

```javascript
// validate.js — Validation UI logic
// Expects window.PAGE_DATA to be set by the HTML page before this script loads.
// PAGE_DATA shape: { openalex_id, author_name, institution, merged_ids, papers: { [lit_id]: { meta, categories } } }

(function () {
  'use strict';

  const STORAGE_KEY = 'validate_' + window.PAGE_DATA.openalex_id;
  let state = loadState();

  // --- State Management ---

  function loadState() {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      return saved ? JSON.parse(saved) : {};
    } catch (e) {
      return {};
    }
  }

  function saveState() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
      updateSaveIndicator();
    } catch (e) {
      console.error('Failed to save state:', e);
    }
  }

  function updateSaveIndicator() {
    const el = document.getElementById('save-indicator');
    if (el) {
      const now = new Date();
      el.textContent = 'Last saved: ' + now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
  }

  function getPaperState(litId) {
    if (!state[litId]) state[litId] = {};
    return state[litId];
  }

  function getCategoryState(litId, prefix) {
    const ps = getPaperState(litId);
    if (!ps[prefix]) ps[prefix] = {};
    return ps[prefix];
  }

  // --- Progress Tracking ---

  function updateProgress() {
    const papers = Object.keys(window.PAGE_DATA.papers);
    const reviewed = papers.filter(id => {
      const ps = state[id];
      if (!ps) return false;
      return Object.values(ps).some(cat => cat.rating);
    }).length;
    const total = papers.length;

    const fill = document.querySelector('.progress-bar .fill');
    const text = document.getElementById('progress-text');
    if (fill) fill.style.width = (total > 0 ? (reviewed / total * 100) : 0) + '%';
    if (text) text.textContent = reviewed + ' of ' + total + ' reviewed';

    // Update per-paper badges
    papers.forEach(id => {
      const badge = document.querySelector('[data-paper="' + id + '"] .review-status');
      if (badge) {
        const ps = state[id];
        const done = ps && Object.values(ps).some(cat => cat.rating);
        badge.textContent = done ? 'reviewed' : 'not reviewed';
        badge.classList.toggle('reviewed', done);
      }
    });
  }

  // --- Rendering ---

  function renderPaperBlock(litId, paperData) {
    const details = document.createElement('details');
    details.className = 'paper-block';
    details.setAttribute('data-paper', litId);

    // Summary line
    const summary = document.createElement('summary');
    summary.className = 'paper-summary';
    const m = paperData.meta;
    const authorShort = m.authors ? m.authors.split(',')[0].trim() + (m.authors.includes(',') ? ' et al.' : '') : 'Unknown';
    const titleShort = m.title && m.title.length > 80 ? m.title.substring(0, 77) + '...' : (m.title || 'Untitled');
    summary.innerHTML =
      '<span class="chevron">&#9654;</span>' +
      '<span class="year">' + (m.year || '?') + '</span>' +
      '<span class="authors">' + escapeHtml(authorShort) + '</span> &mdash; ' +
      '<span class="title">"' + escapeHtml(titleShort) + '"</span>' +
      '<span class="journal">' + escapeHtml(m.journal || '') + '</span>' +
      '<span class="review-status">not reviewed</span>';
    details.appendChild(summary);

    // Content wrapper
    const content = document.createElement('div');

    // Metadata row
    content.appendChild(renderMetadataRow(m));

    // Category sections — Tier 1 (rule-based, with evidence) first, then Tier 2
    const tier1Prefixes = ['b_', 'd_', 'eco_', 'pr_', 'imp_', 'gear_'];
    const tier2Prefixes = ['sp_', 'a_', 'ob_', 'depth_'];

    tier1Prefixes.forEach(function (prefix) {
      const catData = paperData.categories[prefix];
      if (catData) content.appendChild(renderCategorySection(litId, prefix, catData, true));
    });
    tier2Prefixes.forEach(function (prefix) {
      const catData = paperData.categories[prefix];
      if (catData) content.appendChild(renderCategorySection(litId, prefix, catData, false));
    });

    // Any other prefixes discovered dynamically
    Object.keys(paperData.categories).forEach(function (prefix) {
      if (tier1Prefixes.indexOf(prefix) === -1 && tier2Prefixes.indexOf(prefix) === -1) {
        const catData = paperData.categories[prefix];
        content.appendChild(renderCategorySection(litId, prefix, catData, false));
      }
    });

    details.appendChild(content);
    return details;
  }

  function renderMetadataRow(meta) {
    const row = document.createElement('div');
    row.className = 'metadata-row';
    const items = [
      { label: 'Year', value: meta.year },
      { label: 'Journal', value: meta.journal },
      { label: 'DOI', value: meta.doi, link: meta.doi ? 'https://doi.org/' + meta.doi : null },
      { label: 'Study type', value: meta.study_type },
      { label: 'Country', value: meta.country },
      { label: 'Superregion', value: meta.superregion },
      { label: 'Epoch', value: meta.epoch },
      { label: 'Altmetric', value: meta.alt_score },
    ];
    items.forEach(function (item) {
      if (!item.value) return;
      const span = document.createElement('span');
      span.className = 'meta-item';
      if (item.link) {
        span.innerHTML = '<span class="meta-label">' + item.label + ':</span> <a href="' + escapeHtml(item.link) + '" target="_blank">' + escapeHtml(String(item.value)) + '</a>';
      } else {
        span.innerHTML = '<span class="meta-label">' + item.label + ':</span> <span class="meta-value">' + escapeHtml(String(item.value)) + '</span>';
      }
      row.appendChild(span);
    });
    return row;
  }

  var CATEGORY_LABELS = {
    'b_': 'Ocean Basin (extraction)',
    'd_': 'Discipline',
    'eco_': 'Ecosystem',
    'pr_': 'Pressure / Threat',
    'imp_': 'Impact / Response',
    'gear_': 'Fishing Gear',
    'sp_': 'Species',
    'a_': 'Analytical Techniques',
    'ob_': 'Ocean Basin (geographic)',
    'depth_': 'Depth',
  };

  function renderCategorySection(litId, prefix, catData, hasEvidence) {
    var section = document.createElement('div');
    section.className = 'category-section';

    var header = document.createElement('div');
    header.className = 'category-header';
    header.innerHTML = '<span class="category-name">' + (CATEGORY_LABELS[prefix] || prefix) + '</span>';
    section.appendChild(header);

    var savedCat = getCategoryState(litId, prefix);

    // Depth is a special case: read-only display with override fields
    if (prefix === 'depth_') {
      section.appendChild(renderDepthSection(litId, catData, savedCat));
      return section;
    }

    // Species and Techniques: tag-style with autocomplete
    if (prefix === 'sp_' || prefix === 'a_') {
      section.appendChild(renderTagSection(litId, prefix, catData, savedCat));
    } else {
      // Checkbox grid for all other categories
      section.appendChild(renderCheckboxGrid(litId, prefix, catData, hasEvidence, savedCat));
    }

    // Rating controls (all categories except depth)
    if (prefix !== 'depth_') {
      section.appendChild(renderRatingControls(litId, prefix, savedCat));
    }

    // Notes field
    var notes = document.createElement('textarea');
    notes.className = 'notes-field';
    notes.placeholder = 'Notes (optional)';
    notes.value = savedCat.notes || '';
    notes.addEventListener('input', function () {
      getCategoryState(litId, prefix).notes = notes.value;
      saveState();
    });
    section.appendChild(notes);

    // Rule feedback (only for Tier 1 categories with evidence)
    if (hasEvidence) {
      section.appendChild(renderRuleFeedback(litId, prefix, catData, savedCat));
    }

    return section;
  }

  function renderCheckboxGrid(litId, prefix, catData, hasEvidence, savedCat) {
    var grid = document.createElement('div');
    grid.className = 'checkbox-grid';

    // catData.columns: [{name, triggered, evidence}]
    var added = savedCat.added || [];
    var removed = savedCat.removed || [];

    catData.columns.forEach(function (col) {
      var originallyTriggered = col.triggered;
      var isAdded = added.indexOf(col.name) !== -1;
      var isRemoved = removed.indexOf(col.name) !== -1;
      var currentlyChecked = (originallyTriggered && !isRemoved) || isAdded;

      var item = document.createElement('label');
      item.className = 'cb-item';
      if (currentlyChecked) item.classList.add('checked');
      if (originallyTriggered && currentlyChecked) item.classList.add('original');
      if (isAdded || isRemoved) item.classList.add('changed');

      var cb = document.createElement('input');
      cb.type = 'checkbox';
      cb.checked = currentlyChecked;

      var label = document.createElement('span');
      label.className = 'cb-label';
      // Strip prefix for display: "b_north_atlantic" -> "north atlantic"
      label.textContent = col.name.replace(prefix, '').replace(/_/g, ' ');
      label.title = col.name;

      cb.addEventListener('change', function () {
        var cs = getCategoryState(litId, prefix);
        if (!cs.added) cs.added = [];
        if (!cs.removed) cs.removed = [];

        if (cb.checked && !originallyTriggered) {
          // Adding a new one
          if (cs.added.indexOf(col.name) === -1) cs.added.push(col.name);
          cs.removed = cs.removed.filter(function (n) { return n !== col.name; });
        } else if (!cb.checked && originallyTriggered) {
          // Removing an original
          if (cs.removed.indexOf(col.name) === -1) cs.removed.push(col.name);
          cs.added = cs.added.filter(function (n) { return n !== col.name; });
        } else {
          // Reverting a change
          cs.added = cs.added.filter(function (n) { return n !== col.name; });
          cs.removed = cs.removed.filter(function (n) { return n !== col.name; });
        }

        item.classList.toggle('checked', cb.checked);
        item.classList.toggle('changed', cs.added.indexOf(col.name) !== -1 || cs.removed.indexOf(col.name) !== -1);
        saveState();
        updateProgress();
      });

      item.appendChild(cb);
      item.appendChild(label);

      // Evidence detail toggle (only for triggered items with evidence)
      if (hasEvidence && col.evidence && col.evidence.length > 0) {
        var infoBtn = document.createElement('span');
        infoBtn.textContent = ' \u24D8';
        infoBtn.style.cursor = 'pointer';
        infoBtn.style.fontSize = '0.7rem';
        infoBtn.title = 'Show evidence';
        item.appendChild(infoBtn);

        var evDetail = document.createElement('div');
        evDetail.className = 'evidence-detail';
        col.evidence.forEach(function (ev) {
          var row = document.createElement('div');
          row.className = 'ev-row';
          row.innerHTML =
            '<span class="ev-label">Terms:</span><span class="ev-value">' + escapeHtml(ev.matched_terms || '') + '</span>';
          evDetail.appendChild(row);
          if (ev.section) {
            var srow = document.createElement('div');
            srow.className = 'ev-row';
            srow.innerHTML =
              '<span class="ev-label">Section:</span><span class="ev-value">' + escapeHtml(ev.section) + '</span>' +
              ' &middot; <span class="ev-label">Freq:</span><span class="ev-value">' + ev.total_freq + '/' + ev.threshold + '</span>';
            evDetail.appendChild(srow);
          }
          if (ev.context) {
            var ctx = document.createElement('div');
            ctx.className = 'context-snippet';
            ctx.textContent = ev.context.length > 200 ? ev.context.substring(0, 197) + '...' : ev.context;
            evDetail.appendChild(ctx);
          }
        });

        infoBtn.addEventListener('click', function (e) {
          e.preventDefault();
          e.stopPropagation();
          evDetail.classList.toggle('open');
        });

        grid.appendChild(item);
        grid.appendChild(evDetail);
      } else {
        grid.appendChild(item);
      }
    });

    return grid;
  }

  function renderTagSection(litId, prefix, catData, savedCat) {
    var wrapper = document.createElement('div');

    // Show triggered items as tags
    var tagGrid = document.createElement('div');
    tagGrid.className = 'tag-grid';

    var removed = savedCat.removed || [];

    catData.triggered.forEach(function (name) {
      var tag = document.createElement('span');
      tag.className = 'tag-item';
      if (removed.indexOf(name) !== -1) tag.classList.add('removed');
      var displayName = name.replace(prefix, '').replace(/_/g, ' ');
      tag.innerHTML = escapeHtml(displayName) + ' <span class="remove-btn">&times;</span>';
      tag.querySelector('.remove-btn').addEventListener('click', function () {
        var cs = getCategoryState(litId, prefix);
        if (!cs.removed) cs.removed = [];
        if (cs.removed.indexOf(name) !== -1) {
          cs.removed = cs.removed.filter(function (n) { return n !== name; });
          tag.classList.remove('removed');
        } else {
          cs.removed.push(name);
          tag.classList.add('removed');
        }
        saveState();
      });
      tagGrid.appendChild(tag);
    });

    // Show added items
    (savedCat.added || []).forEach(function (name) {
      var tag = document.createElement('span');
      tag.className = 'tag-item changed';
      var displayName = name.replace(prefix, '').replace(/_/g, ' ');
      tag.innerHTML = escapeHtml(displayName) + ' <span class="remove-btn">&times;</span>';
      tag.querySelector('.remove-btn').addEventListener('click', function () {
        var cs = getCategoryState(litId, prefix);
        cs.added = (cs.added || []).filter(function (n) { return n !== name; });
        tag.remove();
        saveState();
      });
      tagGrid.appendChild(tag);
    });

    wrapper.appendChild(tagGrid);

    // Autocomplete input for adding new items
    var acWrapper = document.createElement('div');
    acWrapper.className = 'autocomplete-wrapper';
    var select = document.createElement('select');
    select.id = 'ac-' + prefix + '-' + litId;
    select.setAttribute('placeholder', 'Add ' + (CATEGORY_LABELS[prefix] || prefix).toLowerCase() + '...');

    // Will be initialised by Tom Select after DOM insertion
    acWrapper.appendChild(select);
    wrapper.appendChild(acWrapper);

    // Defer Tom Select init
    requestAnimationFrame(function () {
      if (typeof TomSelect === 'undefined') return;
      var ts = new TomSelect(select, {
        options: catData.all_options.map(function (name) {
          return { value: name, text: name.replace(prefix, '').replace(/_/g, ' ') };
        }),
        maxOptions: 50,
        create: false,
        onChange: function (value) {
          if (!value) return;
          var cs = getCategoryState(litId, prefix);
          if (!cs.added) cs.added = [];
          if (cs.added.indexOf(value) === -1 && catData.triggered.indexOf(value) === -1) {
            cs.added.push(value);
            // Add tag to grid
            var tag = document.createElement('span');
            tag.className = 'tag-item changed';
            var displayName = value.replace(prefix, '').replace(/_/g, ' ');
            tag.innerHTML = escapeHtml(displayName) + ' <span class="remove-btn">&times;</span>';
            tag.querySelector('.remove-btn').addEventListener('click', function () {
              cs.added = cs.added.filter(function (n) { return n !== value; });
              tag.remove();
              saveState();
            });
            tagGrid.appendChild(tag);
            saveState();
          }
          ts.clear(true);
        }
      });
    });

    return wrapper;
  }

  function renderDepthSection(litId, catData, savedCat) {
    var wrapper = document.createElement('div');
    wrapper.className = 'depth-display';

    wrapper.innerHTML =
      '<span class="meta-label">Range:</span> <span class="meta-value">' + escapeHtml(catData.depth_range || 'N/A') + '</span>' +
      ' &middot; <span class="meta-label">Min (m):</span> <input type="number" value="' + (savedCat.depth_min || catData.depth_min_m || '') + '" data-field="depth_min">' +
      ' &middot; <span class="meta-label">Max (m):</span> <input type="number" value="' + (savedCat.depth_max || catData.depth_max_m || '') + '" data-field="depth_max">';

    wrapper.querySelectorAll('input').forEach(function (inp) {
      inp.addEventListener('change', function () {
        var cs = getCategoryState(litId, 'depth_');
        cs[inp.dataset.field] = inp.value ? parseFloat(inp.value) : null;
        saveState();
      });
    });

    return wrapper;
  }

  function renderRatingControls(litId, prefix, savedCat) {
    var controls = document.createElement('div');
    controls.className = 'rating-controls';
    var name = 'rating-' + litId + '-' + prefix;

    [
      { value: 'correct', label: 'Correct', cls: 'rating-correct' },
      { value: 'partially_correct', label: 'Partially correct', cls: 'rating-partial' },
      { value: 'incorrect', label: 'Incorrect', cls: 'rating-incorrect' },
    ].forEach(function (opt) {
      var label = document.createElement('label');
      label.className = opt.cls;
      var radio = document.createElement('input');
      radio.type = 'radio';
      radio.name = name;
      radio.value = opt.value;
      if (savedCat.rating === opt.value) radio.checked = true;
      radio.addEventListener('change', function () {
        getCategoryState(litId, prefix).rating = opt.value;
        saveState();
        updateProgress();
      });
      label.appendChild(radio);
      label.appendChild(document.createTextNode(' ' + opt.label));
      controls.appendChild(label);
    });

    return controls;
  }

  function renderRuleFeedback(litId, prefix, catData, savedCat) {
    var details = document.createElement('details');
    details.className = 'rule-feedback';
    var summary = document.createElement('summary');
    summary.textContent = 'Suggest rule changes...';
    details.appendChild(summary);

    var inner = document.createElement('div');

    // Threshold adjustment
    if (catData.threshold !== undefined) {
      var thRow = document.createElement('div');
      thRow.className = 'rf-row';
      thRow.innerHTML =
        '<span>Threshold (current: ' + catData.threshold + '):</span>' +
        '<input type="number" value="' + (savedCat.rule_threshold || catData.threshold) + '" min="1" max="50">';
      thRow.querySelector('input').addEventListener('change', function (e) {
        var cs = getCategoryState(litId, prefix);
        if (!cs.rule_suggestions) cs.rule_suggestions = {};
        cs.rule_suggestions.threshold_change = parseInt(e.target.value);
        saveState();
      });
      inner.appendChild(thRow);
    }

    // Add term
    var addRow = document.createElement('div');
    addRow.className = 'rf-row';
    addRow.innerHTML = '<span>Add term:</span><input type="text" placeholder="e.g. incidental take">';
    addRow.querySelector('input').addEventListener('change', function (e) {
      if (!e.target.value.trim()) return;
      var cs = getCategoryState(litId, prefix);
      if (!cs.rule_suggestions) cs.rule_suggestions = {};
      if (!cs.rule_suggestions.add_terms) cs.rule_suggestions.add_terms = [];
      cs.rule_suggestions.add_terms.push(e.target.value.trim());
      e.target.value = '';
      saveState();
    });
    inner.appendChild(addRow);

    // Remove term (dropdown of current terms)
    if (catData.current_terms && catData.current_terms.length > 0) {
      var rmRow = document.createElement('div');
      rmRow.className = 'rf-row';
      var sel = '<span>Remove term:</span><select><option value="">--</option>';
      catData.current_terms.forEach(function (t) {
        sel += '<option value="' + escapeHtml(t) + '">' + escapeHtml(t) + '</option>';
      });
      sel += '</select>';
      rmRow.innerHTML = sel;
      rmRow.querySelector('select').addEventListener('change', function (e) {
        if (!e.target.value) return;
        var cs = getCategoryState(litId, prefix);
        if (!cs.rule_suggestions) cs.rule_suggestions = {};
        if (!cs.rule_suggestions.remove_terms) cs.rule_suggestions.remove_terms = [];
        cs.rule_suggestions.remove_terms.push(e.target.value);
        saveState();
      });
      inner.appendChild(rmRow);
    }

    details.appendChild(inner);
    return details;
  }

  // --- Utilities ---

  function escapeHtml(str) {
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  // --- Init ---

  function init() {
    var container = document.getElementById('papers-container');
    if (!container) return;

    // Sort papers by year descending
    var paperIds = Object.keys(window.PAGE_DATA.papers);
    paperIds.sort(function (a, b) {
      var ya = window.PAGE_DATA.papers[a].meta.year || 0;
      var yb = window.PAGE_DATA.papers[b].meta.year || 0;
      return yb - ya;
    });

    paperIds.forEach(function (litId) {
      container.appendChild(renderPaperBlock(litId, window.PAGE_DATA.papers[litId]));
    });

    updateProgress();
    updateSaveIndicator();
  }

  // Expose for submit.js
  window.validateUI = {
    getState: function () { return state; },
    getPageData: function () { return window.PAGE_DATA; },
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
```

- [ ] **Step 2: Commit**

```bash
git add docs/validate/assets/validate.js
git commit -m "feat(validate): add validation UI JavaScript (state, rendering, localStorage)"
```

---

### Task 3: Submission JavaScript (`docs/validate/assets/submit.js`)

**Files:**
- Create: `docs/validate/assets/submit.js`

- [ ] **Step 1: Write the submission JS**

Create `docs/validate/assets/submit.js`:

```javascript
// submit.js — Build submission JSON and POST to proxy
(function () {
  'use strict';

  // PROXY_URL and DISPATCH_TOKEN are set in each HTML page's inline script
  // before this file loads. They come from the generation script's config.
  var PROXY_URL = window.SUBMIT_CONFIG ? window.SUBMIT_CONFIG.proxy_url : '';
  var DISPATCH_TOKEN = window.SUBMIT_CONFIG ? window.SUBMIT_CONFIG.dispatch_token : '';

  function buildSubmissionJSON() {
    var ui = window.validateUI;
    var pageData = ui.getPageData();
    var state = ui.getState();

    var papers = {};
    var papersReviewed = 0;

    Object.keys(state).forEach(function (litId) {
      var paperState = state[litId];
      var hasRating = Object.values(paperState).some(function (cat) { return cat && cat.rating; });
      if (hasRating) papersReviewed++;

      var paperOut = {};
      var hasChanges = false;

      Object.keys(paperState).forEach(function (prefix) {
        var cat = paperState[prefix];
        if (!cat) return;
        var entry = {};
        if (cat.rating) entry.rating = cat.rating;
        if (cat.added && cat.added.length > 0) entry.added = cat.added;
        if (cat.removed && cat.removed.length > 0) entry.removed = cat.removed;
        if (cat.notes && cat.notes.trim()) entry.notes = cat.notes.trim();
        if (cat.rule_suggestions && Object.keys(cat.rule_suggestions).length > 0) {
          entry.rule_suggestions = cat.rule_suggestions;
        }
        if (cat.depth_min !== undefined) entry.depth_min = cat.depth_min;
        if (cat.depth_max !== undefined) entry.depth_max = cat.depth_max;
        if (Object.keys(entry).length > 0) {
          paperOut[prefix] = entry;
          hasChanges = true;
        }
      });

      if (hasChanges) papers[litId] = paperOut;
    });

    return {
      openalex_id: pageData.openalex_id,
      author_name: pageData.author_name,
      timestamp: new Date().toISOString(),
      page_version: pageData.page_version || '2026-04-16',
      papers_reviewed: papersReviewed,
      papers_total: Object.keys(pageData.papers).length,
      papers: papers,
    };
  }

  function downloadJSON() {
    var json = buildSubmissionJSON();
    var blob = new Blob([JSON.stringify(json, null, 2)], { type: 'application/json' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = json.openalex_id + '_validation.json';
    a.click();
    URL.revokeObjectURL(url);
  }

  function submitValidation() {
    var json = buildSubmissionJSON();

    if (json.papers_reviewed === 0) {
      alert('Please review at least one paper before submitting.');
      return;
    }

    var submitBtn = document.getElementById('btn-submit');
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = 'Submitting...';
    }

    // If no proxy URL configured, fall back to download
    if (!PROXY_URL) {
      alert('Submission endpoint not configured. Downloading JSON file instead — please email it to simondedman@gmail.com');
      downloadJSON();
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Submit validation';
      }
      return;
    }

    fetch(PROXY_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        token: DISPATCH_TOKEN,
        payload: json,
      }),
    })
      .then(function (res) {
        if (!res.ok) throw new Error('Server returned ' + res.status);
        return res.json();
      })
      .then(function () {
        alert('Validation submitted successfully! A pull request will be created shortly. Thank you for your contribution.');
        if (submitBtn) {
          submitBtn.textContent = 'Submitted ✓';
        }
      })
      .catch(function (err) {
        console.error('Submission failed:', err);
        alert('Submission failed (' + err.message + '). Downloading JSON as backup — please email it to simondedman@gmail.com');
        downloadJSON();
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = 'Submit validation';
        }
      });
  }

  // Bind buttons
  document.addEventListener('DOMContentLoaded', function () {
    var submitBtn = document.getElementById('btn-submit');
    if (submitBtn) submitBtn.addEventListener('click', submitValidation);

    var downloadBtn = document.getElementById('btn-download');
    if (downloadBtn) downloadBtn.addEventListener('click', downloadJSON);
  });
})();
```

- [ ] **Step 2: Commit**

```bash
git add docs/validate/assets/submit.js
git commit -m "feat(validate): add submission JS (JSON build, proxy POST, download fallback)"
```

---

### Task 4: Tom Select vendor files

**Files:**
- Create: `docs/validate/assets/tom-select.min.js`
- Create: `docs/validate/assets/tom-select.min.css`

- [ ] **Step 1: Download Tom Select**

```bash
cd "docs/validate/assets"
curl -sL "https://cdn.jsdelivr.net/npm/tom-select@2.4.3/dist/js/tom-select.complete.min.js" -o tom-select.min.js
curl -sL "https://cdn.jsdelivr.net/npm/tom-select@2.4.3/dist/css/tom-select.min.css" -o tom-select.min.css
```

- [ ] **Step 2: Verify files exist and are non-empty**

```bash
ls -la docs/validate/assets/tom-select.*
```

Expected: two files, each 10-50 KB.

- [ ] **Step 3: Commit**

```bash
git add docs/validate/assets/tom-select.min.js docs/validate/assets/tom-select.min.css
git commit -m "feat(validate): add Tom Select vendor files for autocomplete"
```

---

### Task 5: Jinja2 Templates

**Files:**
- Create: `scripts/templates/validate_page.html.j2`
- Create: `scripts/templates/validate_index.html.j2`
- Create: `scripts/templates/validate_404.html.j2`
- Create: `scripts/templates/validate_redirect.html.j2`

- [ ] **Step 1: Create templates directory**

```bash
mkdir -p scripts/templates
```

- [ ] **Step 2: Write the per-author page template**

Create `scripts/templates/validate_page.html.j2`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Validate: {{ author_name }}</title>
  <link rel="stylesheet" href="assets/tom-select.min.css">
  <link rel="stylesheet" href="assets/style.css">
</head>
<body>
  <div class="page-header">
    <h1>{{ author_name }}</h1>
    <div class="meta">
      {{ institution }} &middot; OpenAlex: {{ openalex_id }} &middot; {{ paper_count }} paper{{ 's' if paper_count != 1 else '' }} in database
    </div>
    {% if merged_ids %}
    <div class="merge-note">
      This page includes papers from merged OpenAlex profiles: {{ merged_ids | join(', ') }}
    </div>
    {% endif %}
  </div>

  <div id="papers-container"></div>

  <div class="page-footer">
    <span id="save-indicator" class="save-indicator">Not yet saved</span>
    <div class="progress-bar"><div class="fill" style="width: 0%"></div></div>
    <span id="progress-text" class="progress-text">0 of {{ paper_count }} reviewed</span>
    <button id="btn-download" class="btn btn-secondary">Download JSON</button>
    <button id="btn-submit" class="btn btn-primary">Submit validation</button>
  </div>

  <script>
    window.PAGE_DATA = {{ page_data_json }};
    window.SUBMIT_CONFIG = {
      proxy_url: '{{ proxy_url }}',
      dispatch_token: '{{ dispatch_token }}',
    };
  </script>
  <script src="assets/tom-select.min.js"></script>
  <script src="assets/validate.js"></script>
  <script src="assets/submit.js"></script>
</body>
</html>
```

- [ ] **Step 3: Write the landing page template**

Create `scripts/templates/validate_index.html.j2`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Elasmobranch Analytical Methods Review — Validation</title>
  <link rel="stylesheet" href="assets/style.css">
</head>
<body>
  <div class="landing-container">
    <h1>Elasmobranch Analytical Methods Review</h1>
    <p class="subtitle">Validate the automated extractions for your papers</p>

    <input type="text" class="search-box" id="author-search"
           placeholder="Search by name (e.g. Jane Smith)..."
           autocomplete="off">

    <div id="search-results" class="search-results"></div>

    <p style="margin-top: 2rem; font-size: 0.85rem; color: #868e96;">
      Can't find your page? Your OpenAlex ID is the number after <code>author.id:</code> in any
      <a href="https://openalex.org" target="_blank">openalex.org</a> author URL.
      If you are not in our database, please share your papers with
      <a href="https://shark-references.com" target="_blank">Shark References</a>.
    </p>
  </div>

  <script>
    (function() {
      var input = document.getElementById('author-search');
      var results = document.getElementById('search-results');
      var debounceTimer;
      // Set of known author IDs (generated at build time)
      var KNOWN_IDS = new Set({{ known_ids_json }});
      var BASE_URL = '{{ base_url }}';

      input.addEventListener('input', function() {
        clearTimeout(debounceTimer);
        var query = input.value.trim();
        if (query.length < 3) { results.innerHTML = ''; return; }
        debounceTimer = setTimeout(function() { searchAuthors(query); }, 300);
      });

      function searchAuthors(query) {
        results.innerHTML = '<p style="color:#868e96">Searching...</p>';
        fetch('https://api.openalex.org/authors?search=' + encodeURIComponent(query) + '&per_page=10')
          .then(function(r) { return r.json(); })
          .then(function(data) {
            results.innerHTML = '';
            if (!data.results || data.results.length === 0) {
              results.innerHTML = '<p style="color:#868e96">No authors found.</p>';
              return;
            }
            data.results.forEach(function(author) {
              var id = author.id.replace('https://openalex.org/', '');
              var inDB = KNOWN_IDS.has(id);
              var a = document.createElement('a');
              a.className = 'search-result';
              a.href = inDB ? (BASE_URL + id + '.html') : '#';
              if (!inDB) a.style.opacity = '0.5';
              a.innerHTML =
                '<div class="sr-name">' + escapeHtml(author.display_name) + '</div>' +
                '<div class="sr-inst">' + escapeHtml((author.last_known_institutions && author.last_known_institutions[0] ? author.last_known_institutions[0].display_name : '') || 'Unknown institution') + '</div>' +
                '<div class="sr-meta">' + (author.works_count || 0) + ' works &middot; ' + id +
                (inDB ? '' : ' &middot; <em>not in our database</em>') + '</div>';
              if (!inDB) {
                a.addEventListener('click', function(e) {
                  e.preventDefault();
                  alert('This author is not in our database. Please share papers with Shark References (shark-references.com).');
                });
              }
              results.appendChild(a);
            });
          })
          .catch(function() {
            results.innerHTML = '<p style="color:#868e96">Search failed. Please try again.</p>';
          });
      }

      function escapeHtml(str) {
        var d = document.createElement('div');
        d.textContent = str || '';
        return d.innerHTML;
      }
    })();
  </script>
</body>
</html>
```

- [ ] **Step 4: Write the 404 page template**

Create `scripts/templates/validate_404.html.j2`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Page Not Found</title>
  <link rel="stylesheet" href="{{ assets_prefix }}validate/assets/style.css">
</head>
<body>
  <div class="four-oh-four">
    <h1>404</h1>
    <div id="message"></div>
  </div>
  <script>
    (function() {
      var path = window.location.pathname;
      var msg = document.getElementById('message');
      if (path.indexOf('/validate/') !== -1) {
        msg.innerHTML = '<p>We don\'t have papers linked to this OpenAlex ID in our database.</p>' +
          '<p>If your elasmobranch research is missing, please share your papers with ' +
          '<a href="https://shark-references.com">Shark References</a> &mdash; they\'ll be ' +
          'included in our next monthly sync and extraction run.</p>' +
          '<p><a href="{{ base_url }}validate/index.html">Search for your author page &rarr;</a></p>';
      } else {
        msg.innerHTML = '<p>The page you requested was not found.</p>' +
          '<p><a href="{{ base_url }}validate/index.html">Go to the validation landing page &rarr;</a></p>';
      }
    })();
  </script>
</body>
</html>
```

- [ ] **Step 5: Write the redirect template for merged secondary IDs**

Create `scripts/templates/validate_redirect.html.j2`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="refresh" content="0; url={{ primary_url }}">
  <title>Redirecting...</title>
</head>
<body>
  <p>Redirecting to <a href="{{ primary_url }}">{{ primary_id }}</a>...</p>
</body>
</html>
```

- [ ] **Step 6: Commit**

```bash
git add scripts/templates/
git commit -m "feat(validate): add Jinja2 templates for validation pages"
```

---

### Task 6: Generation Script (`scripts/generate_validation_pages.py`)

**Files:**
- Create: `scripts/generate_validation_pages.py`

This is the main script. It reads all four data sources, merges fragmented authors, builds the per-author data structures, and renders HTML via Jinja2.

- [ ] **Step 1: Write the generation script**

Create `scripts/generate_validation_pages.py`:

```python
#!/usr/bin/env python3
"""Generate static HTML validation pages for each author.

Usage:
    python scripts/generate_validation_pages.py                  # generate all
    python scripts/generate_validation_pages.py --author a5086753224  # single author
    python scripts/generate_validation_pages.py --limit 100      # first 100 authors
"""

import argparse
import csv
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import pyarrow.parquet as pq
from jinja2 import Environment, FileSystemLoader

# --- Paths ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PARQUET_PATH = PROJECT_ROOT / "outputs" / "literature_review_enriched.parquet"
EVIDENCE_PATH = PROJECT_ROOT / "outputs" / "schema_extraction_evidence.csv"
PAPER_AUTHORS_PATH = PROJECT_ROOT / "outputs" / "openalex_paper_authors.csv"
UNIQUE_AUTHORS_PATH = PROJECT_ROOT / "outputs" / "openalex_unique_authors.csv"
ALTMETRIC_PATH = PROJECT_ROOT / "outputs" / "altmetric_scores.csv"
TEMPLATE_DIR = PROJECT_ROOT / "scripts" / "templates"
OUTPUT_DIR = PROJECT_ROOT / "docs" / "validate"
FOUR_OH_FOUR_PATH = PROJECT_ROOT / "docs" / "404.html"

# Prefixes that have evidence in the evidence CSV (Tier 1)
TIER1_PREFIXES = {"b_", "d_", "eco_", "pr_", "imp_", "gear_"}
# Tier 2 prefixes (automated extraction, no evidence trail)
TIER2_PREFIXES = {"sp_", "a_", "ob_", "depth_"}

# Proxy config — update these when Cloudflare Worker is deployed
PROXY_URL = ""  # e.g. "https://elasmo-validate.your-worker.workers.dev/submit"
DISPATCH_TOKEN = ""  # shared secret token
BASE_URL = "/elasmo_analyses/"

METADATA_COLUMNS = [
    "year", "title", "authors", "doi", "journal",
    "study_type", "country", "superregion", "epoch", "literature_id",
]


def parse_args():
    parser = argparse.ArgumentParser(description="Generate validation pages")
    parser.add_argument("--author", help="Generate for a single OpenAlex author ID")
    parser.add_argument("--limit", type=int, help="Limit number of authors to generate")
    parser.add_argument("--proxy-url", default=PROXY_URL, help="Submission proxy URL")
    parser.add_argument("--dispatch-token", default=DISPATCH_TOKEN, help="Dispatch token")
    return parser.parse_args()


def load_parquet():
    """Load parquet and return (metadata dict by lit_id, column_data dict by lit_id)."""
    print("Loading parquet...")
    schema = pq.read_schema(PARQUET_PATH)
    all_cols = schema.names

    # Identify binary columns by prefix
    binary_prefixes = set()
    for col in all_cols:
        parts = col.split("_", 1)
        if len(parts) == 2 and len(parts[0]) <= 5:
            prefix = parts[0] + "_"
            if prefix in TIER1_PREFIXES or prefix in TIER2_PREFIXES:
                binary_prefixes.add(prefix)

    # Read metadata columns
    meta_cols = [c for c in METADATA_COLUMNS if c in all_cols]
    table = pq.read_table(PARQUET_PATH, columns=meta_cols)
    metadata = {}
    for i in range(table.num_rows):
        row = {col: table.column(col)[i].as_py() for col in meta_cols}
        lit_id = str(int(row["literature_id"])) if row.get("literature_id") else None
        if not lit_id:
            continue
        row["literature_id"] = lit_id
        if row.get("year"):
            row["year"] = int(row["year"])
        metadata[lit_id] = row

    # Read binary columns — identify which are triggered per paper
    print(f"  Reading binary columns for {len(binary_prefixes)} prefixes...")
    columns_by_prefix = defaultdict(list)
    for col in all_cols:
        for prefix in binary_prefixes:
            if col.startswith(prefix):
                columns_by_prefix[prefix].append(col)
                break

    # For each paper, record which columns are triggered (value > 0)
    paper_columns = defaultdict(lambda: defaultdict(dict))
    # paper_columns[lit_id][prefix] = {"triggered": [col_names], "all_options": [col_names]}

    for prefix, cols in columns_by_prefix.items():
        # Read in batches to manage memory
        batch_table = pq.read_table(PARQUET_PATH, columns=["literature_id"] + cols)
        lit_ids = batch_table.column("literature_id")
        for i in range(batch_table.num_rows):
            lid_raw = lit_ids[i].as_py()
            if not lid_raw:
                continue
            lit_id = str(int(lid_raw))
            triggered = []
            for col in cols:
                val = batch_table.column(col)[i].as_py()
                if val and val > 0:
                    triggered.append(col)
            if triggered or prefix in TIER1_PREFIXES:
                paper_columns[lit_id][prefix] = {
                    "triggered": triggered,
                    "all_options": cols,
                }

    # Depth columns are special (numeric, not binary)
    if "depth_range" in all_cols:
        depth_table = pq.read_table(
            PARQUET_PATH, columns=["literature_id", "depth_range", "depth_min_m", "depth_max_m"]
        )
        for i in range(depth_table.num_rows):
            lid_raw = depth_table.column("literature_id")[i].as_py()
            if not lid_raw:
                continue
            lit_id = str(int(lid_raw))
            dr = depth_table.column("depth_range")[i].as_py()
            dmin = depth_table.column("depth_min_m")[i].as_py()
            dmax = depth_table.column("depth_max_m")[i].as_py()
            if dr or dmin or dmax:
                paper_columns[lit_id]["depth_"] = {
                    "depth_range": dr,
                    "depth_min_m": dmin,
                    "depth_max_m": dmax,
                }

    print(f"  Loaded {len(metadata)} papers, columns for {len(paper_columns)} papers")
    return metadata, paper_columns, columns_by_prefix


def load_evidence():
    """Load evidence CSV into dict: evidence[lit_id][column] = [rows]."""
    print("Loading evidence CSV...")
    evidence = defaultdict(lambda: defaultdict(list))
    with open(EVIDENCE_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            lit_id = str(row["literature_id"])
            col = row["column"]
            evidence[lit_id][col].append({
                "matched_terms": row.get("matched_terms", ""),
                "section": row.get("section", ""),
                "total_freq": row.get("total_freq", ""),
                "threshold": row.get("threshold", ""),
                "context": row.get("context", ""),
            })
    print(f"  Loaded evidence for {len(evidence)} papers")
    return evidence


def load_altmetric():
    """Load altmetric scores into dict: altmetric[lit_id] = score."""
    print("Loading altmetric scores...")
    altmetric = {}
    if not ALTMETRIC_PATH.exists():
        print("  No altmetric file found, skipping")
        return altmetric
    with open(ALTMETRIC_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            lit_id = str(row.get("literature_id", ""))
            score = row.get("alt_score", "")
            if lit_id and score:
                altmetric[lit_id] = score
    print(f"  Loaded altmetric for {len(altmetric)} papers")
    return altmetric


def load_authors():
    """Load author data and build merge groups.

    Returns:
        author_papers: dict[openalex_id] -> list of literature_ids
        author_info: dict[openalex_id] -> {display_name, institution, country, ...}
        merge_groups: dict[primary_id] -> list of secondary_ids
        redirects: dict[secondary_id] -> primary_id
    """
    print("Loading author data...")

    # Load unique authors
    authors = {}
    with open(UNIQUE_AUTHORS_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            aid = row["openalex_author_id"].replace("https://openalex.org/", "")
            authors[aid] = {
                "display_name": row["display_name"],
                "institution": row["most_common_institution"],
                "country": row["institution_country"],
                "paper_count": int(row["paper_count"]) if row["paper_count"] else 0,
            }

    # Load paper-author mapping
    author_papers = defaultdict(list)
    with open(PAPER_AUTHORS_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            aid = row["openalex_author_id"].replace("https://openalex.org/", "")
            lit_id = str(row["literature_id"])
            if aid and lit_id:
                author_papers[aid].append(lit_id)

    # Build merge groups: same (display_name, institution) -> group
    name_inst_groups = defaultdict(list)
    for aid, info in authors.items():
        key = (info["display_name"].strip().lower(), info["institution"].strip().lower())
        name_inst_groups[key].append(aid)

    merge_groups = {}
    redirects = {}
    for key, ids in name_inst_groups.items():
        if len(ids) < 2:
            continue
        # Primary = highest paper count
        ids_sorted = sorted(ids, key=lambda x: -authors[x]["paper_count"])
        primary = ids_sorted[0]
        secondaries = ids_sorted[1:]
        merge_groups[primary] = secondaries
        for sec in secondaries:
            redirects[sec] = primary
            # Merge papers onto primary
            author_papers[primary].extend(author_papers.get(sec, []))

    # Deduplicate paper lists
    for aid in author_papers:
        author_papers[aid] = list(dict.fromkeys(author_papers[aid]))

    print(f"  Loaded {len(authors)} authors, {len(merge_groups)} merge groups, {len(redirects)} redirects")
    return author_papers, authors, merge_groups, redirects


def build_page_data(
    author_id, author_info, paper_ids, metadata, paper_columns,
    evidence, altmetric, columns_by_prefix, merged_ids=None,
):
    """Build the PAGE_DATA JSON object for one author."""
    papers = {}
    for lit_id in paper_ids:
        meta = metadata.get(lit_id)
        if not meta:
            continue

        # Add altmetric score to metadata
        paper_meta = dict(meta)
        paper_meta["alt_score"] = altmetric.get(lit_id, "")

        categories = {}
        pc = paper_columns.get(lit_id, {})

        # Always show Tier 1 and ob_ even if nothing triggered
        always_show = TIER1_PREFIXES | {"ob_"}
        for prefix in list(TIER1_PREFIXES) + list(TIER2_PREFIXES):
            cat_data = pc.get(prefix)
            if not cat_data:
                if prefix in always_show:
                    all_opts = columns_by_prefix.get(prefix, [])
                    categories[prefix] = {
                        "columns": [
                            {"name": col, "triggered": False, "evidence": []}
                            for col in all_opts
                        ],
                    }
                continue

            if prefix == "depth_":
                categories["depth_"] = cat_data
                continue

            if prefix in ("sp_", "a_"):
                categories[prefix] = {
                    "triggered": cat_data["triggered"],
                    "all_options": cat_data["all_options"],
                }
                continue

            # Standard checkbox categories
            columns = []
            paper_evidence = evidence.get(lit_id, {})
            for col in cat_data.get("all_options", columns_by_prefix.get(prefix, [])):
                triggered = col in cat_data.get("triggered", [])
                ev = paper_evidence.get(col, [])
                columns.append({
                    "name": col,
                    "triggered": triggered,
                    "evidence": ev if triggered else [],
                })
            categories[prefix] = {"columns": columns}

        papers[lit_id] = {"meta": paper_meta, "categories": categories}

    return {
        "openalex_id": author_id,
        "author_name": author_info.get("display_name", "Unknown"),
        "institution": author_info.get("institution", ""),
        "page_version": "2026-04-16",
        "merged_ids": merged_ids or [],
        "papers": papers,
    }


def generate_pages(args):
    """Main generation function."""
    metadata, paper_columns, columns_by_prefix = load_parquet()
    evidence = load_evidence()
    altmetric = load_altmetric()
    author_papers, authors, merge_groups, redirects = load_authors()

    # Set up Jinja2
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=False)
    page_template = env.get_template("validate_page.html.j2")
    index_template = env.get_template("validate_index.html.j2")
    four04_template = env.get_template("validate_404.html.j2")
    redirect_template = env.get_template("validate_redirect.html.j2")

    # Ensure output directories exist
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Determine which authors to generate
    if args.author:
        author_ids = [args.author]
    else:
        # All authors except those that redirect
        author_ids = [aid for aid in authors if aid not in redirects]
        if args.limit:
            author_ids = author_ids[: args.limit]

    print(f"\nGenerating {len(author_ids)} author pages...")

    # Generate per-author pages
    for i, author_id in enumerate(author_ids):
        if (i + 1) % 1000 == 0 or i == 0:
            print(f"  {i + 1}/{len(author_ids)}...")

        info = authors.get(author_id, {"display_name": "Unknown", "institution": "", "paper_count": 0})
        paper_ids = author_papers.get(author_id, [])
        merged_ids = merge_groups.get(author_id, [])

        page_data = build_page_data(
            author_id, info, paper_ids, metadata, paper_columns,
            evidence, altmetric, columns_by_prefix, merged_ids,
        )

        html = page_template.render(
            author_name=info["display_name"],
            institution=info.get("institution", ""),
            openalex_id=author_id,
            paper_count=len(page_data["papers"]),
            merged_ids=merged_ids,
            page_data_json=json.dumps(page_data, ensure_ascii=False),
            proxy_url=args.proxy_url,
            dispatch_token=args.dispatch_token,
        )

        out_path = OUTPUT_DIR / f"{author_id}.html"
        out_path.write_text(html, encoding="utf-8")

    # Generate redirect pages for secondary IDs
    print(f"Generating {len(redirects)} redirect pages...")
    for sec_id, primary_id in redirects.items():
        html = redirect_template.render(
            primary_url=f"{primary_id}.html",
            primary_id=primary_id,
        )
        out_path = OUTPUT_DIR / f"{sec_id}.html"
        out_path.write_text(html, encoding="utf-8")

    # Generate landing page
    print("Generating landing page...")
    known_ids = [aid for aid in authors if aid not in redirects]
    html = index_template.render(
        known_ids_json=json.dumps(known_ids),
        base_url=BASE_URL + "validate/",
    )
    (OUTPUT_DIR / "index.html").write_text(html, encoding="utf-8")

    # Generate 404 page
    print("Generating 404 page...")
    html = four04_template.render(
        assets_prefix=BASE_URL,
        base_url=BASE_URL,
    )
    FOUR_OH_FOUR_PATH.write_text(html, encoding="utf-8")

    total_files = len(author_ids) + len(redirects) + 2  # +2 for index and 404
    print(f"\nDone! Generated {total_files} files in {OUTPUT_DIR}")


if __name__ == "__main__":
    args = parse_args()
    generate_pages(args)
```

- [ ] **Step 2: Test with a single author**

```bash
python scripts/generate_validation_pages.py --author a5086753224 --limit 1
```

Expected: creates `docs/validate/a5086753224.html`, `docs/validate/index.html`, `docs/404.html`. Open `docs/validate/a5086753224.html` in a browser to verify layout.

- [ ] **Step 3: Fix any issues found during browser testing**

Open the generated page in Firefox/Chrome. Verify:
- Header shows author name, institution, paper count
- Paper blocks expand/collapse
- Metadata row shows year, journal, DOI link
- Checkbox grids render for all 6 Tier 1 categories
- Evidence details expand when clicking the info icon
- Species/technique tags display with autocomplete
- Rating radio buttons work
- localStorage saves on interaction (check DevTools > Application > Local Storage)
- Progress bar updates when ratings are set
- Download JSON button produces valid JSON

- [ ] **Step 4: Commit**

```bash
git add scripts/generate_validation_pages.py
git commit -m "feat(validate): add main generation script for validation pages"
```

---

### Task 7: GitHub Action for receiving validations

**Files:**
- Create: `.github/workflows/receive-validation.yml`
- Create: `validations/.gitkeep`

- [ ] **Step 1: Create the workflow**

```bash
mkdir -p .github/workflows
mkdir -p validations
touch validations/.gitkeep
```

Create `.github/workflows/receive-validation.yml`:

```yaml
name: Receive Validation

on:
  repository_dispatch:
    types: [validation-submitted]

jobs:
  create-pr:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Extract submission data
        id: extract
        run: |
          # The payload is in the client_payload from repository_dispatch
          echo '${{ toJSON(github.event.client_payload) }}' > /tmp/payload.json

          # Extract fields
          OPENALEX_ID=$(jq -r '.openalex_id' /tmp/payload.json)
          AUTHOR_NAME=$(jq -r '.author_name' /tmp/payload.json)
          PAPERS_REVIEWED=$(jq -r '.papers_reviewed' /tmp/payload.json)
          TIMESTAMP=$(date +%Y%m%d-%H%M%S)

          echo "openalex_id=$OPENALEX_ID" >> $GITHUB_OUTPUT
          echo "author_name=$AUTHOR_NAME" >> $GITHUB_OUTPUT
          echo "papers_reviewed=$PAPERS_REVIEWED" >> $GITHUB_OUTPUT
          echo "timestamp=$TIMESTAMP" >> $GITHUB_OUTPUT
          echo "filename=validations/${OPENALEX_ID}_${TIMESTAMP}.json" >> $GITHUB_OUTPUT
          echo "branch=validation/${OPENALEX_ID}/${TIMESTAMP}" >> $GITHUB_OUTPUT

      - name: Create branch and commit validation
        run: |
          git config user.name "Validation Bot"
          git config user.email "noreply@github.com"
          git checkout -b "${{ steps.extract.outputs.branch }}"

          # Write the full payload as the validation file
          echo '${{ toJSON(github.event.client_payload) }}' | jq '.' > "${{ steps.extract.outputs.filename }}"

          git add "${{ steps.extract.outputs.filename }}"
          git commit -m "validation: ${{ steps.extract.outputs.author_name }} (${{ steps.extract.outputs.papers_reviewed }} papers)"

          git push origin "${{ steps.extract.outputs.branch }}"

      - name: Generate PR summary
        id: summary
        run: |
          # Build a human-readable summary from the JSON
          python3 -c "
          import json, sys

          with open('${{ steps.extract.outputs.filename }}') as f:
              data = json.load(f)

          lines = ['## Validation Summary\n']
          lines.append(f\"**Author:** {data['author_name']} ({data['openalex_id']})\")
          lines.append(f\"**Papers reviewed:** {data['papers_reviewed']} / {data['papers_total']}\")
          lines.append(f\"**Submitted:** {data['timestamp']}\n\")

          for lit_id, paper in data.get('papers', {}).items():
              lines.append(f\"### Paper {lit_id}\")
              for prefix, cat in paper.items():
                  changes = []
                  if cat.get('rating'):
                      changes.append(f\"Rating: {cat['rating']}\")
                  if cat.get('added'):
                      changes.append(f\"Added: {', '.join(cat['added'])}\")
                  if cat.get('removed'):
                      changes.append(f\"Removed: {', '.join(cat['removed'])}\")
                  if cat.get('notes'):
                      changes.append(f\"Note: {cat['notes']}\")
                  if cat.get('rule_suggestions'):
                      changes.append(f\"Rule changes: {json.dumps(cat['rule_suggestions'])}\")
                  if changes:
                      lines.append(f\"- **{prefix}**: {' | '.join(changes)}\")
              lines.append('')

          summary = '\n'.join(lines)
          # Write to file for the PR body
          with open('/tmp/pr_body.md', 'w') as f:
              f.write(summary)
          "

      - name: Create Pull Request
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          gh pr create \
            --title "Validation: ${{ steps.extract.outputs.author_name }} (${{ steps.extract.outputs.papers_reviewed }} papers)" \
            --body-file /tmp/pr_body.md \
            --base main \
            --head "${{ steps.extract.outputs.branch }}"
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/receive-validation.yml validations/.gitkeep
git commit -m "feat(validate): add GitHub Action for receiving validation submissions"
```

---

### Task 8: Generate all pages and deploy

**Files:**
- Modify: `scripts/generate_validation_pages.py` (if any fixes from Task 6 testing)
- Generate: `docs/validate/*.html` (28,952 files)
- Generate: `docs/404.html`

- [ ] **Step 1: Run full generation**

```bash
python scripts/generate_validation_pages.py 2>&1 | tee /tmp/generate_validation.log
```

Expected: ~28,952 author pages + ~187 redirect pages + index + 404. Monitor memory usage — the parquet is large. If memory is an issue, process in batches by modifying the script to read parquet columns per-prefix instead of all at once.

- [ ] **Step 2: Check output size**

```bash
du -sh docs/validate/
ls docs/validate/*.html | wc -l
```

Expected: ~580 MB total, ~29,100+ HTML files.

- [ ] **Step 3: Spot-check a few pages in browser**

Open 3-5 pages for authors with varying paper counts:
- A prolific author (50+ papers)
- A single-paper author
- A merged-profile author
- A redirect page (should auto-redirect)

- [ ] **Step 4: Enable GitHub Pages**

Go to `github.com/SimonDedman/elasmo_analyses/settings/pages`:
- Source: Deploy from a branch
- Branch: `main`
- Folder: `/docs`
- Save

- [ ] **Step 5: Add docs/validate/ to .gitignore (generated files)**

The generated HTML files are build artefacts. They should be committed for GitHub Pages deployment but not pollute diffs. Add to `.gitignore`:

```
# Don't track individual validation page diffs (too many files)
# They are committed for GitHub Pages but excluded from normal diffs
```

Note: Actually, since GitHub Pages requires these files to be committed, they cannot be in `.gitignore`. Instead, just commit them in a single dedicated commit.

- [ ] **Step 6: Commit all generated pages**

```bash
git add docs/validate/ docs/404.html
git commit -m "feat(validate): generate all 28,952 validation pages for GitHub Pages"
```

- [ ] **Step 7: Push**

```bash
git push
```

- [ ] **Step 8: Verify GitHub Pages deployment**

After push, wait a few minutes for GitHub Pages to build. Then verify:
- `https://simondedman.github.io/elasmo_analyses/validate/index.html` loads
- Name search returns results from OpenAlex API
- Clicking a result loads the author's validation page
- A non-existent ID shows the 404 page
- A merged secondary ID redirects to the primary

---

### Task 9: Cloudflare Worker proxy (submission endpoint)

**Files:**
- Create: `scripts/cloudflare-worker/worker.js` (reference, deployed via Cloudflare dashboard)

This task sets up the proxy that accepts unauthenticated POSTs from validators' browsers and forwards them to the GitHub `repository_dispatch` endpoint.

- [ ] **Step 1: Write the worker script**

Create `scripts/cloudflare-worker/worker.js`:

```javascript
// Cloudflare Worker: proxy validation submissions to GitHub repository_dispatch
// Deploy via Cloudflare Dashboard > Workers > Create Worker
// Environment variables (set in Cloudflare dashboard):
//   GITHUB_PAT: fine-grained PAT with actions:write on SimonDedman/elasmo_analyses
//   DISPATCH_TOKEN: shared secret that validators include in their POST body

export default {
  async fetch(request, env) {
    // CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'POST, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type',
        },
      });
    }

    if (request.method !== 'POST') {
      return new Response('Method not allowed', { status: 405 });
    }

    try {
      const body = await request.json();

      // Validate shared token
      if (body.token !== env.DISPATCH_TOKEN) {
        return new Response('Unauthorized', { status: 401 });
      }

      // Forward to GitHub repository_dispatch
      const response = await fetch(
        'https://api.github.com/repos/SimonDedman/elasmo_analyses/dispatches',
        {
          method: 'POST',
          headers: {
            'Accept': 'application/vnd.github+json',
            'Authorization': 'Bearer ' + env.GITHUB_PAT,
            'X-GitHub-Api-Version': '2022-11-28',
            'Content-Type': 'application/json',
            'User-Agent': 'elasmo-validation-proxy',
          },
          body: JSON.stringify({
            event_type: 'validation-submitted',
            client_payload: body.payload,
          }),
        }
      );

      if (!response.ok) {
        const errText = await response.text();
        return new Response('GitHub API error: ' + errText, {
          status: 502,
          headers: { 'Access-Control-Allow-Origin': '*' },
        });
      }

      return new Response(JSON.stringify({ ok: true }), {
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*',
        },
      });
    } catch (err) {
      return new Response('Bad request: ' + err.message, {
        status: 400,
        headers: { 'Access-Control-Allow-Origin': '*' },
      });
    }
  },
};
```

- [ ] **Step 2: Deploy the worker**

1. Go to `dash.cloudflare.com` > Workers & Pages > Create Worker
2. Paste the worker code
3. Set environment variables:
   - `GITHUB_PAT`: create a fine-grained PAT at `github.com/settings/tokens?type=beta` with `actions:write` permission on `SimonDedman/elasmo_analyses`
   - `DISPATCH_TOKEN`: generate a random string (e.g. `openssl rand -hex 32`)
4. Deploy and note the worker URL (e.g. `https://elasmo-validate.simondedman.workers.dev`)

- [ ] **Step 3: Update generation script config**

Edit `scripts/generate_validation_pages.py` and set:

```python
PROXY_URL = "https://elasmo-validate.simondedman.workers.dev"
DISPATCH_TOKEN = "<the token from step 2>"
```

- [ ] **Step 4: Regenerate pages with proxy config**

```bash
python scripts/generate_validation_pages.py
```

- [ ] **Step 5: Test end-to-end**

1. Open a validation page in browser
2. Rate one category as "correct"
3. Click "Submit validation"
4. Check the repository for a new PR created by the Action

- [ ] **Step 6: Commit**

```bash
git add scripts/cloudflare-worker/worker.js scripts/generate_validation_pages.py
git commit -m "feat(validate): add Cloudflare Worker proxy and wire up submission"
```

---

## Task Dependency Summary

```
Task 1 (CSS) ─────────────┐
Task 2 (validate.js) ─────┤
Task 3 (submit.js) ───────┤── Task 6 (generation script) ── Task 8 (generate all + deploy)
Task 4 (Tom Select) ──────┤                                         │
Task 5 (templates) ────────┘                                         │
                                                                      │
Task 7 (GitHub Action) ───── Task 9 (Cloudflare Worker) ──────────────┘
```

Tasks 1-5 and Task 7 can be done in parallel. Task 6 depends on 1-5. Task 8 depends on 6+7. Task 9 depends on 7+8.
