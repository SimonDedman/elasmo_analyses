/**
 * validate.js — Validation UI main logic
 *
 * Expects window.PAGE_DATA to be set before this script loads.
 * Exposes window.validateUI = { getState(), getPageData() } for submit.js.
 *
 * No ES6 modules; IIFE; var for broad compatibility.
 */
(function () {
  'use strict';

  // ---------------------------------------------------------------------------
  // Constants
  // ---------------------------------------------------------------------------

  var TIER1_PREFIXES = ['b_', 'd_', 'eco_', 'pr_', 'imp_', 'gear_', 'ob_'];
  var TIER1_CHECKBOX = ['b_', 'd_', 'eco_', 'pr_', 'imp_', 'gear_'];  // ob_ also checkbox but listed separately
  var TAG_PREFIXES   = ['sp_', 'a_'];
  var PREFIX_ORDER   = ['b_', 'd_', 'eco_', 'pr_', 'imp_', 'gear_', 'sp_', 'a_', 'ob_', 'depth_'];

  var PREFIX_LABELS = {
    'b_':     'Ocean Basin',
    'd_':     'Discipline',
    'eco_':   'Ecosystem',
    'pr_':    'Pressure',
    'imp_':   'Impact',
    'gear_':  'Gear',
    'sp_':    'Species',
    'a_':     'Author Affiliation',
    'ob_':    'Observation Method',
    'depth_': 'Depth'
  };

  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------

  var _state   = {};   // { [paperId]: { [prefix]: { rating, added, removed, notes, rule_suggestions, depth_min_m, depth_max_m } } }
  var _pageData = window.PAGE_DATA || {};
  var _storageKey = 'validate_' + (_pageData.openalex_id || 'unknown');
  var _sharedOptions = {};  // loaded from assets/options.json: { sp_: [...], a_: [...] }

  function _loadState() {
    try {
      var raw = localStorage.getItem(_storageKey);
      if (raw) { _state = JSON.parse(raw); }
    } catch (e) {
      console.warn('validate.js: could not load state from localStorage', e);
    }
  }

  function _saveState() {
    try {
      localStorage.setItem(_storageKey, JSON.stringify(_state));
    } catch (e) {
      console.warn('validate.js: could not save state to localStorage', e);
    }
  }

  function _ensureState(paperId, prefix) {
    if (!_state[paperId]) { _state[paperId] = {}; }
    if (!_state[paperId][prefix]) {
      _state[paperId][prefix] = {
        rating:           null,
        added:            [],
        removed:          [],
        notes:            '',
        rule_suggestions: { threshold: null, add_terms: [], remove_terms: [] },
        depth_min_m:      null,
        depth_max_m:      null
      };
    }
    return _state[paperId][prefix];
  }

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  function escapeHtml(text) {
    var d = document.createElement('div');
    d.textContent = String(text == null ? '' : text);
    return d.innerHTML;
  }

  function _shortAuthor(authorsStr) {
    if (!authorsStr) { return ''; }
    var parts = authorsStr.split(',');
    var first = parts[0].trim();
    // "Smith, J." → surname only
    var surname = first.split(' ')[0].replace(/[,;]$/, '');
    return parts.length > 1 ? surname + ' et al.' : surname;
  }

  function _truncate(str, max) {
    if (!str) { return ''; }
    return str.length > max ? str.slice(0, max - 1) + '\u2026' : str;
  }

  function _isPaperReviewed(paperId) {
    var paperState = _state[paperId];
    if (!paperState) { return false; }
    var prefixes = Object.keys(paperState);
    for (var i = 0; i < prefixes.length; i++) {
      if (paperState[prefixes[i]].rating) { return true; }
    }
    return false;
  }

  function _prefixFor(colName) {
    for (var i = 0; i < PREFIX_ORDER.length; i++) {
      if (colName.indexOf(PREFIX_ORDER[i]) === 0) { return PREFIX_ORDER[i]; }
    }
    return null;
  }

  // Sort prefixes: known order first, then alphabetically for unknowns
  function _sortPrefixes(prefixes) {
    return prefixes.slice().sort(function (a, b) {
      var ai = PREFIX_ORDER.indexOf(a);
      var bi = PREFIX_ORDER.indexOf(b);
      if (ai === -1 && bi === -1) { return a < b ? -1 : 1; }
      if (ai === -1) { return 1; }
      if (bi === -1) { return -1; }
      return ai - bi;
    });
  }

  // ---------------------------------------------------------------------------
  // Progress bar
  // ---------------------------------------------------------------------------

  function _updateProgress() {
    var papers  = _pageData.papers || {};
    var ids     = Object.keys(papers);
    var total   = ids.length;
    var reviewed = 0;
    for (var i = 0; i < ids.length; i++) {
      if (_isPaperReviewed(ids[i])) { reviewed++; }
    }
    var pct = total > 0 ? Math.round((reviewed / total) * 100) : 0;
    var bar  = document.getElementById('progress-bar-fill');
    var txt  = document.getElementById('progress-text');
    if (bar) { bar.style.width = pct + '%'; }
    if (txt) { txt.textContent = reviewed + ' of ' + total + ' reviewed'; }
  }

  // ---------------------------------------------------------------------------
  // Evidence popover rendering
  // ---------------------------------------------------------------------------

  function _renderEvidence(evidenceArr) {
    if (!evidenceArr || evidenceArr.length === 0) {
      return '<span class="evidence-empty">No evidence recorded.</span>';
    }
    var html = '<ul class="evidence-list">';
    for (var i = 0; i < evidenceArr.length; i++) {
      var ev = evidenceArr[i];
      html += '<li>';
      html += '<span class="ev-terms">' + escapeHtml(ev.matched_terms || '') + '</span>';
      if (ev.section) {
        html += ' <span class="ev-section">[' + escapeHtml(ev.section) + ']</span>';
      }
      if (ev.total_freq != null) {
        html += ' <span class="ev-freq">freq:' + escapeHtml(ev.total_freq) + '</span>';
      }
      if (ev.threshold != null) {
        html += ' <span class="ev-thresh">thr:' + escapeHtml(ev.threshold) + '</span>';
      }
      if (ev.context) {
        html += '<blockquote class="ev-context">&hellip;' + escapeHtml(ev.context) + '&hellip;</blockquote>';
      }
      html += '</li>';
    }
    html += '</ul>';
    return html;
  }

  // ---------------------------------------------------------------------------
  // Rating + notes + rule feedback HTML (shared across category types)
  // ---------------------------------------------------------------------------

  function _renderRatingRow(paperId, prefix, isTier1) {
    var s      = _ensureState(paperId, prefix);
    var nameBase = 'rating_' + paperId + '_' + prefix;
    var ratings  = ['correct', 'partially_correct', 'incorrect'];
    var labels   = ['Correct', 'Partially correct', 'Incorrect'];

    var html = '<div class="rating-row">';
    html += '<span class="rating-label">Rating:</span>';
    for (var i = 0; i < ratings.length; i++) {
      var checked = s.rating === ratings[i] ? ' checked' : '';
      html += '<label class="rating-option">';
      html += '<input type="radio" name="' + escapeHtml(nameBase) + '"';
      html += ' value="' + ratings[i] + '"' + checked;
      html += ' data-paper="' + escapeHtml(paperId) + '"';
      html += ' data-prefix="' + escapeHtml(prefix) + '"';
      html += ' class="rating-radio">';
      html += ' ' + labels[i];
      html += '</label>';
    }
    html += '</div>';

    // Notes
    html += '<div class="notes-row">';
    html += '<label class="notes-label">Notes:</label>';
    html += '<textarea class="notes-area"';
    html += ' data-paper="' + escapeHtml(paperId) + '"';
    html += ' data-prefix="' + escapeHtml(prefix) + '"';
    html += ' rows="2">' + escapeHtml(s.notes || '') + '</textarea>';
    html += '</div>';

    // Rule feedback only for Tier 1 checkbox categories (not sp_, a_, ob_, depth_)
    if (isTier1 && TIER1_CHECKBOX.indexOf(prefix) !== -1) {
      var rs = s.rule_suggestions;
      html += '<div class="rule-feedback">';
      html += '<span class="rule-label">Rule feedback:</span>';
      html += '<label class="rule-item">Threshold: ';
      html += '<input type="number" class="threshold-input"';
      html += ' data-paper="' + escapeHtml(paperId) + '"';
      html += ' data-prefix="' + escapeHtml(prefix) + '"';
      html += ' min="0" step="1" placeholder="current"';
      html += ' value="' + escapeHtml(rs.threshold != null ? rs.threshold : '') + '">';
      html += '</label>';
      html += '<label class="rule-item">Add term: ';
      html += '<input type="text" class="add-term-input"';
      html += ' data-paper="' + escapeHtml(paperId) + '"';
      html += ' data-prefix="' + escapeHtml(prefix) + '"';
      html += ' placeholder="e.g. demersal">';
      html += '<button class="btn-add-term"';
      html += ' data-paper="' + escapeHtml(paperId) + '"';
      html += ' data-prefix="' + escapeHtml(prefix) + '"';
      html += '>+</button>';
      var addTermsList = rs.add_terms && rs.add_terms.length
        ? '<span class="term-tags">' + rs.add_terms.map(function (t) {
            return '<span class="term-tag add-tag">' + escapeHtml(t)
              + '<button class="btn-remove-added-term" data-paper="' + escapeHtml(paperId) + '"'
              + ' data-prefix="' + escapeHtml(prefix) + '"'
              + ' data-term="' + escapeHtml(t) + '">&times;</button></span>';
          }).join('') + '</span>'
        : '';
      html += addTermsList;
      html += '</label>';
      html += '<label class="rule-item">Remove term: ';
      html += '<input type="text" class="remove-term-input"';
      html += ' data-paper="' + escapeHtml(paperId) + '"';
      html += ' data-prefix="' + escapeHtml(prefix) + '"';
      html += ' placeholder="e.g. pelagic">';
      html += '<button class="btn-remove-term"';
      html += ' data-paper="' + escapeHtml(paperId) + '"';
      html += ' data-prefix="' + escapeHtml(prefix) + '"';
      html += '>+</button>';
      var removeTermsList = rs.remove_terms && rs.remove_terms.length
        ? '<span class="term-tags">' + rs.remove_terms.map(function (t) {
            return '<span class="term-tag remove-tag">' + escapeHtml(t)
              + '<button class="btn-delete-removed-term" data-paper="' + escapeHtml(paperId) + '"'
              + ' data-prefix="' + escapeHtml(prefix) + '"'
              + ' data-term="' + escapeHtml(t) + '">&times;</button></span>';
          }).join('') + '</span>'
        : '';
      html += removeTermsList;
      html += '</label>';
      html += '</div>';
    }

    return html;
  }

  // ---------------------------------------------------------------------------
  // Checkbox category (Tier1 + ob_)
  // ---------------------------------------------------------------------------

  function _renderCheckboxCategory(paperId, prefix, catData, isTier1) {
    var s       = _ensureState(paperId, prefix);
    var columns = catData.columns || [];
    var html    = '';

    html += '<div class="checkbox-grid">';
    for (var i = 0; i < columns.length; i++) {
      var col        = columns[i];
      var colName    = col.name || '';
      var triggered  = !!col.triggered;
      var isAdded    = s.added.indexOf(colName) !== -1;
      var isRemoved  = s.removed.indexOf(colName) !== -1;

      // Effective checked state: originally triggered + added − removed
      var effectiveChecked = (triggered && !isRemoved) || isAdded;
      var originalClass    = triggered ? ' original' : '';
      var addedClass       = isAdded   ? ' manually-added' : '';
      var removedClass     = isRemoved ? ' manually-removed' : '';

      var colId    = 'chk_' + paperId + '_' + colName;
      var label    = colName.replace(prefix, '').replace(/_/g, ' ');
      var evidence = col.evidence || [];

      html += '<div class="checkbox-item' + originalClass + addedClass + removedClass + '">';
      html += '<label>';
      html += '<input type="checkbox" id="' + escapeHtml(colId) + '"';
      html += ' data-paper="' + escapeHtml(paperId) + '"';
      html += ' data-prefix="' + escapeHtml(prefix) + '"';
      html += ' data-col="' + escapeHtml(colName) + '"';
      html += ' data-original="' + (triggered ? '1' : '0') + '"';
      html += ' class="col-checkbox"';
      if (effectiveChecked) { html += ' checked'; }
      html += '>';
      html += ' ' + escapeHtml(label);
      html += '</label>';

      if (evidence.length > 0) {
        html += ' <button class="btn-evidence" aria-label="Show evidence"';
        html += ' data-paper="' + escapeHtml(paperId) + '"';
        html += ' data-col="' + escapeHtml(colName) + '"';
        html += '>&#9432;</button>';
        html += '<div class="evidence-panel" id="ev_' + escapeHtml(paperId) + '_' + escapeHtml(colName) + '" hidden>';
        html += _renderEvidence(evidence);
        html += '</div>';
      }

      html += '</div>'; // .checkbox-item
    }
    html += '</div>'; // .checkbox-grid

    html += _renderRatingRow(paperId, prefix, isTier1);
    return html;
  }

  // ---------------------------------------------------------------------------
  // Tag category (sp_, a_)
  // ---------------------------------------------------------------------------

  function _renderTagCategory(paperId, prefix, catData) {
    var s          = _ensureState(paperId, prefix);
    var triggered  = catData.triggered  || [];
    var allOptions = _sharedOptions[prefix] || [];

    // Effective tags: triggered minus removed plus added
    var effective = [];
    var i;
    for (i = 0; i < triggered.length; i++) {
      if (s.removed.indexOf(triggered[i]) === -1) {
        effective.push({ val: triggered[i], original: true });
      }
    }
    for (i = 0; i < s.added.length; i++) {
      if (triggered.indexOf(s.added[i]) === -1) {
        effective.push({ val: s.added[i], original: false });
      }
    }

    var html = '<div class="tag-section">';

    // Existing tags
    html += '<div class="tag-list" id="tags_' + escapeHtml(paperId) + '_' + escapeHtml(prefix) + '">';
    for (i = 0; i < effective.length; i++) {
      var tag = effective[i];
      var tagLabel = tag.val.replace(prefix, '').replace(/_/g, ' ');
      var tagClass = tag.original ? 'tag original-tag' : 'tag added-tag';
      html += '<span class="' + tagClass + '">';
      html += escapeHtml(tagLabel);
      html += '<button class="btn-remove-tag"';
      html += ' data-paper="' + escapeHtml(paperId) + '"';
      html += ' data-prefix="' + escapeHtml(prefix) + '"';
      html += ' data-val="' + escapeHtml(tag.val) + '"';
      html += ' aria-label="Remove ' + escapeHtml(tagLabel) + '">&times;</button>';
      html += '</span>';
    }
    html += '</div>'; // .tag-list

    // Autocomplete select for adding new tags
    var selectId = 'ts_' + paperId + '_' + prefix.replace('_', '');
    html += '<select id="' + escapeHtml(selectId) + '"';
    html += ' class="tag-select"';
    html += ' data-paper="' + escapeHtml(paperId) + '"';
    html += ' data-prefix="' + escapeHtml(prefix) + '"';
    html += '>';
    html += '<option value="">Add ' + escapeHtml(PREFIX_LABELS[prefix] || prefix) + '&hellip;</option>';

    // Options: all_options not already in effective
    var effectiveVals = effective.map(function (t) { return t.val; });
    for (i = 0; i < allOptions.length; i++) {
      var opt = allOptions[i];
      if (effectiveVals.indexOf(opt) === -1) {
        var optLabel = opt.replace(prefix, '').replace(/_/g, ' ');
        html += '<option value="' + escapeHtml(opt) + '">' + escapeHtml(optLabel) + '</option>';
      }
    }
    html += '</select>';

    html += '</div>'; // .tag-section

    html += _renderRatingRow(paperId, prefix, false);
    return html;
  }

  // ---------------------------------------------------------------------------
  // Depth category
  // ---------------------------------------------------------------------------

  function _renderDepthCategory(paperId, catData) {
    var prefix = 'depth_';
    var s      = _ensureState(paperId, prefix);
    var range  = catData.depth_range  || '';
    var minVal = s.depth_min_m != null ? s.depth_min_m : (catData.depth_min_m != null ? catData.depth_min_m : '');
    var maxVal = s.depth_max_m != null ? s.depth_max_m : (catData.depth_max_m != null ? catData.depth_max_m : '');

    var html = '<div class="depth-section">';
    html += '<p class="depth-range-display">Extracted range: <strong>' + escapeHtml(range || 'not extracted') + '</strong></p>';
    html += '<div class="depth-inputs">';
    html += '<label>Min (m): <input type="number" class="depth-input depth-min"';
    html += ' data-paper="' + escapeHtml(paperId) + '" data-field="depth_min_m"';
    html += ' value="' + escapeHtml(String(minVal)) + '" step="1" min="0">';
    html += '</label>';
    html += '<label>Max (m): <input type="number" class="depth-input depth-max"';
    html += ' data-paper="' + escapeHtml(paperId) + '" data-field="depth_max_m"';
    html += ' value="' + escapeHtml(String(maxVal)) + '" step="1" min="0">';
    html += '</label>';
    html += '</div>';
    html += '</div>'; // .depth-section
    // No rating row for depth
    return html;
  }

  // ---------------------------------------------------------------------------
  // Paper block rendering
  // ---------------------------------------------------------------------------

  function _renderPaperBlock(paperId, paperData) {
    var meta       = paperData.meta       || {};
    var categories = paperData.categories || {};

    var year       = meta.year      || '';
    var title      = meta.title     || '(no title)';
    var authors    = meta.authors   || '';
    var journal    = meta.journal   || '';
    var doi        = meta.doi       || '';
    var studyType  = meta.study_type  || '';
    var country    = meta.country     || '';
    var superregion = meta.superregion || '';
    var epoch      = meta.epoch       || '';
    var altScore   = meta.alt_score   || '';

    var shortAuth  = _shortAuthor(authors);
    var shortTitle = _truncate(title, 80);
    var reviewed   = _isPaperReviewed(paperId);
    var badgeClass = reviewed ? 'badge badge-reviewed' : 'badge badge-pending';
    var badgeText  = reviewed ? 'Reviewed' : 'Pending';

    // Gather and sort category prefixes
    var catPrefixes = Object.keys(categories);
    catPrefixes = _sortPrefixes(catPrefixes);

    // Separate known and dynamic prefixes
    var knownSet = {};
    PREFIX_ORDER.forEach(function (p) { knownSet[p] = true; });
    var dynamicPrefixes = catPrefixes.filter(function (p) { return !knownSet[p]; });

    var html = '<details class="paper-block" id="paper_' + escapeHtml(paperId) + '">';

    // Summary line
    html += '<summary class="paper-summary">';
    html += '<span class="chevron">&#9654;</span>';
    html += '<span class="paper-year">' + escapeHtml(String(year)) + '</span>';
    html += '<span class="paper-short-author">' + escapeHtml(shortAuth) + '</span>';
    html += '<span class="paper-title-short" title="' + escapeHtml(title) + '">' + escapeHtml(shortTitle) + '</span>';
    html += '<span class="paper-journal">' + escapeHtml(journal) + '</span>';
    html += '<span class="' + badgeClass + '" id="badge_' + escapeHtml(paperId) + '">' + badgeText + '</span>';
    html += '</summary>';

    // Paper body
    html += '<div class="paper-body">';

    // Metadata row
    html += '<div class="meta-row">';
    html += '<span class="meta-item"><strong>Year:</strong> ' + escapeHtml(String(year)) + '</span>';
    html += '<span class="meta-item"><strong>Journal:</strong> ' + escapeHtml(journal) + '</span>';
    if (doi) {
      html += '<span class="meta-item"><strong>DOI:</strong> <a href="https://doi.org/' + escapeHtml(doi) + '" target="_blank" rel="noopener">' + escapeHtml(doi) + '</a></span>';
    }
    if (studyType)   { html += '<span class="meta-item"><strong>Type:</strong> '        + escapeHtml(studyType)   + '</span>'; }
    if (country)     { html += '<span class="meta-item"><strong>Country:</strong> '     + escapeHtml(country)     + '</span>'; }
    if (superregion) { html += '<span class="meta-item"><strong>Superregion:</strong> ' + escapeHtml(superregion) + '</span>'; }
    if (epoch)       { html += '<span class="meta-item"><strong>Epoch:</strong> '       + escapeHtml(epoch)       + '</span>'; }
    if (altScore)    { html += '<span class="meta-item"><strong>Altmetric:</strong> '   + escapeHtml(altScore)    + '</span>'; }
    html += '<span class="meta-item meta-id"><strong>ID:</strong> ' + escapeHtml(String(paperId)) + '</span>';
    html += '</div>'; // .meta-row

    // Full authors
    if (authors) {
      html += '<div class="authors-row"><strong>Authors:</strong> ' + escapeHtml(authors) + '</div>';
    }

    // Categories: Tier 1 ordered, then Tier 2 ordered, then dynamic
    var orderedToRender = PREFIX_ORDER.concat(dynamicPrefixes);
    for (var i = 0; i < orderedToRender.length; i++) {
      var prefix = orderedToRender[i];
      var catData = categories[prefix];
      if (!catData) { continue; }

      var isCheckbox = TIER1_CHECKBOX.indexOf(prefix) !== -1 || prefix === 'ob_';
      var isTag      = TAG_PREFIXES.indexOf(prefix) !== -1;
      var isDepth    = prefix === 'depth_';
      var isTier1    = TIER1_CHECKBOX.indexOf(prefix) !== -1;

      var catLabel = PREFIX_LABELS[prefix] || prefix;

      html += '<section class="cat-section" data-prefix="' + escapeHtml(prefix) + '">';
      html += '<h3 class="cat-title">' + escapeHtml(catLabel) + '</h3>';
      html += '<div class="cat-body">';

      if (isDepth) {
        html += _renderDepthCategory(paperId, catData);
      } else if (isTag) {
        html += _renderTagCategory(paperId, prefix, catData);
      } else if (isCheckbox) {
        html += _renderCheckboxCategory(paperId, prefix, catData, isTier1);
      } else {
        // Unknown/dynamic prefix with columns array — treat as checkbox
        if (catData.columns) {
          html += _renderCheckboxCategory(paperId, prefix, catData, false);
        } else if (catData.triggered) {
          html += _renderTagCategory(paperId, prefix, catData);
        }
      }

      html += '</div>'; // .cat-body
      html += '</section>';
    }

    html += '</div>'; // .paper-body
    html += '</details>';

    return html;
  }

  // ---------------------------------------------------------------------------
  // Render all papers
  // ---------------------------------------------------------------------------

  function _renderAll() {
    var container = document.getElementById('papers-container');
    if (!container) {
      console.error('validate.js: #papers-container not found');
      return;
    }

    var papers = _pageData.papers || {};
    var ids    = Object.keys(papers);

    // Sort by year descending, then id descending
    ids.sort(function (a, b) {
      var ya = parseInt((papers[a].meta || {}).year, 10) || 0;
      var yb = parseInt((papers[b].meta || {}).year, 10) || 0;
      if (yb !== ya) { return yb - ya; }
      return String(b).localeCompare(String(a));
    });

    var fragments = [];
    for (var i = 0; i < ids.length; i++) {
      fragments.push(_renderPaperBlock(ids[i], papers[ids[i]]));
    }
    container.innerHTML = fragments.join('');

    // Attach event handlers after DOM is ready
    _attachHandlers(container);

    // Init Tom Select for tag sections (deferred)
    requestAnimationFrame(function () {
      _initTomSelects(container);
    });

    _updateProgress();
  }

  // ---------------------------------------------------------------------------
  // Tom Select initialisation
  // ---------------------------------------------------------------------------

  function _initTomSelects(container) {
    if (typeof TomSelect === 'undefined') { return; }
    var selects = container.querySelectorAll('select.tag-select');
    for (var i = 0; i < selects.length; i++) {
      (function (sel) {
        new TomSelect(sel, {
          create:      false,
          placeholder: sel.options[0] ? sel.options[0].text : 'Add…',
          onItemAdd:   function (value) {
            var paperId = sel.dataset.paper;
            var prefix  = sel.dataset.prefix;
            _handleTagAdd(paperId, prefix, value);
            // Reset select
            this.clear();
            this.clearOptions();
            // Reload options minus newly added
            var s       = _ensureState(paperId, prefix);
            var catData = ((_pageData.papers[paperId] || {}).categories || {})[prefix] || {};
            var allOptions = _sharedOptions[prefix] || [];
            var triggered  = catData.triggered  || [];
            var effective  = triggered.filter(function (v) { return s.removed.indexOf(v) === -1; }).concat(s.added);
            var self       = this;
            allOptions.forEach(function (opt) {
              if (effective.indexOf(opt) === -1) {
                self.addOption({ value: opt, text: opt.replace(prefix, '').replace(/_/g, ' ') });
              }
            });
            self.refreshOptions(false);
          }
        });
      })(selects[i]);
    }
  }

  // ---------------------------------------------------------------------------
  // Event delegation
  // ---------------------------------------------------------------------------

  function _attachHandlers(container) {

    // Checkbox toggle
    container.addEventListener('change', function (e) {
      var el = e.target;

      // Rating radio
      if (el.classList.contains('rating-radio')) {
        var paperId = el.dataset.paper;
        var prefix  = el.dataset.prefix;
        var s       = _ensureState(paperId, prefix);
        s.rating    = el.value;
        _saveState();
        _updateBadge(paperId);
        _updateProgress();
        return;
      }

      // Column checkbox
      if (el.classList.contains('col-checkbox')) {
        var paperId  = el.dataset.paper;
        var prefix   = el.dataset.prefix;
        var colName  = el.dataset.col;
        var original = el.dataset.original === '1';
        var s        = _ensureState(paperId, prefix);

        if (el.checked) {
          // User is checking: remove from removed list; add to added if not original
          var ri = s.removed.indexOf(colName);
          if (ri !== -1) { s.removed.splice(ri, 1); }
          if (!original && s.added.indexOf(colName) === -1) {
            s.added.push(colName);
          }
          el.parentElement.parentElement.classList.remove('manually-removed');
          if (!original) { el.parentElement.parentElement.classList.add('manually-added'); }
        } else {
          // User is unchecking: add to removed; remove from added if not original
          if (s.removed.indexOf(colName) === -1) { s.removed.push(colName); }
          if (!original) {
            var ai = s.added.indexOf(colName);
            if (ai !== -1) { s.added.splice(ai, 1); }
          }
          el.parentElement.parentElement.classList.add('manually-removed');
          el.parentElement.parentElement.classList.remove('manually-added');
        }
        _saveState();
        return;
      }

      // Notes textarea
      if (el.classList.contains('notes-area')) {
        var paperId = el.dataset.paper;
        var prefix  = el.dataset.prefix;
        var s       = _ensureState(paperId, prefix);
        s.notes     = el.value;
        _saveState();
        return;
      }

      // Threshold input
      if (el.classList.contains('threshold-input')) {
        var paperId = el.dataset.paper;
        var prefix  = el.dataset.prefix;
        var s       = _ensureState(paperId, prefix);
        s.rule_suggestions.threshold = el.value !== '' ? parseFloat(el.value) : null;
        _saveState();
        return;
      }

      // Depth inputs
      if (el.classList.contains('depth-input')) {
        var paperId = el.dataset.paper;
        var field   = el.dataset.field;
        var s       = _ensureState(paperId, 'depth_');
        s[field]    = el.value !== '' ? parseFloat(el.value) : null;
        _saveState();
        return;
      }
    });

    // Also listen for input event (notes textarea live save, threshold)
    container.addEventListener('input', function (e) {
      var el = e.target;
      if (el.classList.contains('notes-area')) {
        var paperId = el.dataset.paper;
        var prefix  = el.dataset.prefix;
        var s       = _ensureState(paperId, prefix);
        s.notes     = el.value;
        _saveState();
      }
      if (el.classList.contains('threshold-input')) {
        var paperId = el.dataset.paper;
        var prefix  = el.dataset.prefix;
        var s       = _ensureState(paperId, prefix);
        s.rule_suggestions.threshold = el.value !== '' ? parseFloat(el.value) : null;
        _saveState();
      }
      if (el.classList.contains('depth-input')) {
        var paperId = el.dataset.paper;
        var field   = el.dataset.field;
        var s       = _ensureState(paperId, 'depth_');
        s[field]    = el.value !== '' ? parseFloat(el.value) : null;
        _saveState();
      }
    });

    // Click delegation
    container.addEventListener('click', function (e) {
      var el = e.target;

      // Evidence toggle
      if (el.classList.contains('btn-evidence')) {
        var paperId = el.dataset.paper;
        var col     = el.dataset.col;
        var panel   = document.getElementById('ev_' + paperId + '_' + col);
        if (panel) {
          panel.hidden = !panel.hidden;
        }
        return;
      }

      // Remove tag
      if (el.classList.contains('btn-remove-tag')) {
        var paperId = el.dataset.paper;
        var prefix  = el.dataset.prefix;
        var val     = el.dataset.val;
        _handleTagRemove(paperId, prefix, val);
        return;
      }

      // Add term button (rule feedback)
      if (el.classList.contains('btn-add-term')) {
        var paperId  = el.dataset.paper;
        var prefix   = el.dataset.prefix;
        var inputSel = '.add-term-input[data-paper="' + paperId + '"][data-prefix="' + prefix + '"]';
        var input    = container.querySelector(inputSel);
        if (input && input.value.trim()) {
          var term = input.value.trim();
          var s    = _ensureState(paperId, prefix);
          if (s.rule_suggestions.add_terms.indexOf(term) === -1) {
            s.rule_suggestions.add_terms.push(term);
            _saveState();
            // Re-render rule feedback section inline
            _refreshRuleFeedback(container, paperId, prefix);
          }
          input.value = '';
        }
        return;
      }

      // Remove added term tag
      if (el.classList.contains('btn-remove-added-term')) {
        var paperId = el.dataset.paper;
        var prefix  = el.dataset.prefix;
        var term    = el.dataset.term;
        var s       = _ensureState(paperId, prefix);
        var idx     = s.rule_suggestions.add_terms.indexOf(term);
        if (idx !== -1) { s.rule_suggestions.add_terms.splice(idx, 1); }
        _saveState();
        _refreshRuleFeedback(container, paperId, prefix);
        return;
      }

      // Remove term button (rule feedback)
      if (el.classList.contains('btn-remove-term')) {
        var paperId  = el.dataset.paper;
        var prefix   = el.dataset.prefix;
        var inputSel = '.remove-term-input[data-paper="' + paperId + '"][data-prefix="' + prefix + '"]';
        var input    = container.querySelector(inputSel);
        if (input && input.value.trim()) {
          var term = input.value.trim();
          var s    = _ensureState(paperId, prefix);
          if (s.rule_suggestions.remove_terms.indexOf(term) === -1) {
            s.rule_suggestions.remove_terms.push(term);
            _saveState();
            _refreshRuleFeedback(container, paperId, prefix);
          }
          input.value = '';
        }
        return;
      }

      // Delete removed term tag
      if (el.classList.contains('btn-delete-removed-term')) {
        var paperId = el.dataset.paper;
        var prefix  = el.dataset.prefix;
        var term    = el.dataset.term;
        var s       = _ensureState(paperId, prefix);
        var idx     = s.rule_suggestions.remove_terms.indexOf(term);
        if (idx !== -1) { s.rule_suggestions.remove_terms.splice(idx, 1); }
        _saveState();
        _refreshRuleFeedback(container, paperId, prefix);
        return;
      }
    });

    // details toggle: update chevron
    container.addEventListener('toggle', function (e) {
      var details = e.target;
      if (details.tagName !== 'DETAILS') { return; }
      var chevron = details.querySelector('.chevron');
      if (chevron) {
        chevron.innerHTML = details.open ? '&#9660;' : '&#9654;';
      }
    }, true);
  }

  // ---------------------------------------------------------------------------
  // Tag helpers
  // ---------------------------------------------------------------------------

  function _handleTagAdd(paperId, prefix, value) {
    if (!value) { return; }
    var s = _ensureState(paperId, prefix);
    // If it was removed, un-remove it
    var ri = s.removed.indexOf(value);
    if (ri !== -1) { s.removed.splice(ri, 1); }
    // Add to added if not already in triggered or added
    var catData  = ((_pageData.papers[paperId] || {}).categories || {})[prefix] || {};
    var triggered = catData.triggered || [];
    if (triggered.indexOf(value) === -1 && s.added.indexOf(value) === -1) {
      s.added.push(value);
    }
    _saveState();
    _refreshTagSection(paperId, prefix);
  }

  function _handleTagRemove(paperId, prefix, value) {
    var s = _ensureState(paperId, prefix);
    var catData  = ((_pageData.papers[paperId] || {}).categories || {})[prefix] || {};
    var triggered = catData.triggered || [];

    if (triggered.indexOf(value) !== -1) {
      // Originally triggered: mark as removed
      if (s.removed.indexOf(value) === -1) { s.removed.push(value); }
    } else {
      // Manually added: remove from added
      var ai = s.added.indexOf(value);
      if (ai !== -1) { s.added.splice(ai, 1); }
    }
    _saveState();
    _refreshTagSection(paperId, prefix);
  }

  // Re-render just the tag list within a tag section (avoids full re-render)
  function _refreshTagSection(paperId, prefix) {
    var tagListEl = document.getElementById('tags_' + paperId + '_' + prefix);
    if (!tagListEl) { return; }

    var s         = _ensureState(paperId, prefix);
    var catData   = ((_pageData.papers[paperId] || {}).categories || {})[prefix] || {};
    var triggered = catData.triggered || [];

    var effective = [];
    var i;
    for (i = 0; i < triggered.length; i++) {
      if (s.removed.indexOf(triggered[i]) === -1) {
        effective.push({ val: triggered[i], original: true });
      }
    }
    for (i = 0; i < s.added.length; i++) {
      if (triggered.indexOf(s.added[i]) === -1) {
        effective.push({ val: s.added[i], original: false });
      }
    }

    var html = '';
    for (i = 0; i < effective.length; i++) {
      var tag      = effective[i];
      var tagLabel = tag.val.replace(prefix, '').replace(/_/g, ' ');
      var tagClass = tag.original ? 'tag original-tag' : 'tag added-tag';
      html += '<span class="' + tagClass + '">';
      html += escapeHtml(tagLabel);
      html += '<button class="btn-remove-tag"';
      html += ' data-paper="' + escapeHtml(paperId) + '"';
      html += ' data-prefix="' + escapeHtml(prefix) + '"';
      html += ' data-val="' + escapeHtml(tag.val) + '"';
      html += ' aria-label="Remove ' + escapeHtml(tagLabel) + '">&times;</button>';
      html += '</span>';
    }
    tagListEl.innerHTML = html;
  }

  // ---------------------------------------------------------------------------
  // Rule feedback re-render helper (replaces just the .rule-feedback div)
  // ---------------------------------------------------------------------------

  function _refreshRuleFeedback(container, paperId, prefix) {
    var s  = _ensureState(paperId, prefix);
    var rs = s.rule_suggestions;

    // Rebuild just the term tag lists within the rule-feedback block
    // Add terms list
    var addSel  = '.add-term-input[data-paper="' + paperId + '"][data-prefix="' + prefix + '"]';
    var addInput = container.querySelector(addSel);
    if (addInput) {
      var addTagContainer = addInput.parentElement.querySelector('.term-tags');
      if (!addTagContainer) {
        addTagContainer = document.createElement('span');
        addTagContainer.className = 'term-tags';
        addInput.parentElement.appendChild(addTagContainer);
      }
      addTagContainer.innerHTML = rs.add_terms.map(function (t) {
        return '<span class="term-tag add-tag">' + escapeHtml(t)
          + '<button class="btn-remove-added-term" data-paper="' + escapeHtml(paperId) + '"'
          + ' data-prefix="' + escapeHtml(prefix) + '"'
          + ' data-term="' + escapeHtml(t) + '">&times;</button></span>';
      }).join('');
    }

    // Remove terms list
    var removeSel   = '.remove-term-input[data-paper="' + paperId + '"][data-prefix="' + prefix + '"]';
    var removeInput = container.querySelector(removeSel);
    if (removeInput) {
      var removeTagContainer = removeInput.parentElement.querySelector('.term-tags');
      if (!removeTagContainer) {
        removeTagContainer = document.createElement('span');
        removeTagContainer.className = 'term-tags';
        removeInput.parentElement.appendChild(removeTagContainer);
      }
      removeTagContainer.innerHTML = rs.remove_terms.map(function (t) {
        return '<span class="term-tag remove-tag">' + escapeHtml(t)
          + '<button class="btn-delete-removed-term" data-paper="' + escapeHtml(paperId) + '"'
          + ' data-prefix="' + escapeHtml(prefix) + '"'
          + ' data-term="' + escapeHtml(t) + '">&times;</button></span>';
      }).join('');
    }
  }

  // ---------------------------------------------------------------------------
  // Badge update
  // ---------------------------------------------------------------------------

  function _updateBadge(paperId) {
    var badge = document.getElementById('badge_' + paperId);
    if (!badge) { return; }
    var reviewed = _isPaperReviewed(paperId);
    badge.textContent  = reviewed ? 'Reviewed' : 'Pending';
    badge.className    = reviewed ? 'badge badge-reviewed' : 'badge badge-pending';
  }

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------

  window.validateUI = {
    getState:    function () { return _state; },
    getPageData: function () { return _pageData; }
  };

  // ---------------------------------------------------------------------------
  // Boot
  // ---------------------------------------------------------------------------

  document.addEventListener('DOMContentLoaded', function () {
    _loadState();
    // Load shared options (sp_, a_ column lists) then render
    fetch('assets/options.json')
      .then(function (r) { return r.ok ? r.json() : {}; })
      .then(function (data) { _sharedOptions = data; })
      .catch(function () { _sharedOptions = {}; })
      .then(function () { _renderAll(); });
  });

})();
