(function () {
  'use strict';

  /* -----------------------------------------------------------------------
   * submit.js
   * Builds submission JSON from validateUI state, triggers download, and
   * POSTs to a proxy endpoint.
   *
   * Dependencies (must be present on window before this script runs):
   *   window.validateUI   — exposed by validate.js
   *   window.SUBMIT_CONFIG — set by each HTML page, e.g.:
   *     window.SUBMIT_CONFIG = {
   *       PROXY_URL:      'https://example.com/proxy',  // omit/null = download only
   *       DISPATCH_TOKEN: 'ghp_...'
   *     };
   * --------------------------------------------------------------------- */

  /* ------------------------------------------------------------------
   * buildJSON
   * Assembles the submission object from validateUI state.
   *
   * validateUI state shape: { [paperId]: { [prefix]: {...} }, author_corrections: {...} }
   * — i.e. keyed by paperId at the top level (no intermediate `papers` key).
   *
   * A paper counts as "reviewed" if any of its prefixes has a non-empty
   * `rating` (matches validate.js:_isPaperReviewed).
   * ------------------------------------------------------------------ */
  function buildJSON() {
    var state    = window.validateUI.getState();
    var pageData = window.validateUI.getPageData();

    var papers          = {};
    var papersReviewed  = 0;
    var stateKeys       = Object.keys(state || {});

    for (var i = 0; i < stateKeys.length; i++) {
      var pid = stateKeys[i];
      if (pid === 'author_corrections') { continue; }  // not a paper

      var paperState = state[pid];
      if (!paperState || typeof paperState !== 'object') { continue; }

      var paperEntry    = {};
      var paperHasRating = false;
      var sectionKeys    = Object.keys(paperState);

      for (var j = 0; j < sectionKeys.length; j++) {
        var section     = sectionKeys[j];
        var sectionData = paperState[section];

        if (!sectionData || typeof sectionData !== 'object') {
          continue;
        }

        /* Determine whether this section has any real data. */
        var hasRating       = sectionData.rating && sectionData.rating !== '';
        var hasAdded        = Array.isArray(sectionData.added)   && sectionData.added.length   > 0;
        var hasRemoved      = Array.isArray(sectionData.removed) && sectionData.removed.length > 0;
        var hasNotes        = typeof sectionData.notes === 'string' && sectionData.notes.trim() !== '';
        var hasRuleSugg     = sectionData.rule_suggestions &&
                              Object.keys(sectionData.rule_suggestions).length > 0;

        /* Special numeric fields (depth_, count_, etc.) — include if present. */
        var hasNumericField = false;
        var numericKeys     = Object.keys(sectionData);
        for (var k = 0; k < numericKeys.length; k++) {
          var key = numericKeys[k];
          if (key !== 'rating' && key !== 'added' && key !== 'removed' &&
              key !== 'notes'  && key !== 'rule_suggestions') {
            if (sectionData[key] !== null && sectionData[key] !== undefined &&
                sectionData[key] !== '') {
              hasNumericField = true;
              break;
            }
          }
        }

        if (hasRating) { paperHasRating = true; }

        if (hasRating || hasAdded || hasRemoved || hasNotes ||
            hasRuleSugg || hasNumericField) {
          paperEntry[section] = sectionData;
        }
      }

      /* Only include papers that have at least one populated section. */
      if (Object.keys(paperEntry).length > 0) {
        papers[pid] = paperEntry;
      }
      if (paperHasRating) { papersReviewed++; }
    }

    var result = {
      openalex_id:      pageData.openalex_id      || '',
      author_name:      pageData.author_name      || '',
      timestamp:        new Date().toISOString(),
      page_version:     pageData.page_version     || '',
      papers_reviewed:  papersReviewed,
      papers_total:     pageData.papers_total     || 0,
      papers:           papers
    };

    /* Include author_corrections only if non-empty. */
    var ac = state.author_corrections;
    if (ac && typeof ac === 'object' && Object.keys(ac).length > 0) {
      result.author_corrections = ac;
    }

    return result;
  }

  /* ------------------------------------------------------------------
   * downloadJSON
   * Serialises the current state and triggers a browser file download.
   * ------------------------------------------------------------------ */
  function downloadJSON() {
    var json       = buildJSON();
    var jsonString = JSON.stringify(json, null, 2);
    var blob       = new Blob([jsonString], { type: 'application/json' });
    var url        = URL.createObjectURL(blob);
    var filename   = (json.openalex_id || 'validation') + '_validation.json';

    var a      = document.createElement('a');
    a.href     = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  /* ------------------------------------------------------------------
   * submitValidation
   * Validates state, then either POSTs to the proxy or falls back to
   * a local download.
   * ------------------------------------------------------------------ */
  /* Translate helper — falls back to hardcoded English if I18N isn't loaded. */
  function _t(key, vars) {
    if (window.I18N && typeof window.I18N.t === 'function') {
      return window.I18N.t(key, vars);
    }
    return key;  /* safe fallback — key identifies the message */
  }

  function submitValidation() {
    var json = buildJSON();

    if (!json.papers_reviewed || json.papers_reviewed < 1) {
      alert(_t('submit_no_reviews'));
      return;
    }

    var btn = document.getElementById('btn-submit');
    if (btn) {
      btn.disabled     = true;
      btn.textContent  = _t('submitting');
    }

    var config       = window.SUBMIT_CONFIG || {};
    var proxyUrl     = config.PROXY_URL     || null;
    var dispatchToken = config.DISPATCH_TOKEN || '';

    if (!proxyUrl) {
      /* No endpoint configured — use download as the delivery mechanism. */
      alert(_t('submit_no_endpoint'));
      downloadJSON();
      if (btn) {
        btn.disabled    = false;
        btn.textContent = _t('submit_btn');
      }
      return;
    }

    /* POST to proxy. */
    var payload = JSON.stringify({
      token:   dispatchToken,
      payload: json
    });

    var xhr = new XMLHttpRequest();
    xhr.open('POST', proxyUrl, true);
    xhr.setRequestHeader('Content-Type', 'application/json');

    xhr.onload = function () {
      if (xhr.status >= 200 && xhr.status < 300) {
        alert(_t('submit_success'));
        if (btn) {
          btn.disabled    = true;
          btn.textContent = _t('submitted_check');
        }
      } else {
        alert(_t('submit_failed', { status: xhr.status }));
        downloadJSON();
        if (btn) {
          btn.disabled    = false;
          btn.textContent = _t('submit_btn');
        }
      }
    };

    xhr.onerror = function () {
      alert(_t('submit_network_error'));
      downloadJSON();
      if (btn) {
        btn.disabled    = false;
        btn.textContent = _t('submit_btn');
      }
    };

    xhr.send(payload);
  }

  /* ------------------------------------------------------------------
   * Bind buttons on DOM ready.
   * ------------------------------------------------------------------ */
  document.addEventListener('DOMContentLoaded', function () {
    var btnSubmit   = document.getElementById('btn-submit');
    var btnDownload = document.getElementById('btn-download');

    if (btnSubmit) {
      btnSubmit.addEventListener('click', submitValidation);
    }

    if (btnDownload) {
      btnDownload.addEventListener('click', downloadJSON);
    }
  });

}());
