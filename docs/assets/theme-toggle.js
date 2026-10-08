/* Shark Oracle light/dark/auto toggle. One shared script; load it in <head>, not deferred.
   Optional: <script src="..." data-theme-toggle-offset="120"></script> shifts the button left by that many px.
   A page that is dark by design and ships its own [data-theme=light] palette sets <html data-so-native-dark> (no inversion in dark).
   State lives in localStorage key "so-theme" (auto | light | dark). */
(function () {
  'use strict';
  if (window.__soThemeToggle) return;
  window.__soThemeToggle = true;
  var KEY = 'so-theme', root = document.documentElement;
  var me = document.currentScript;
  var offset = me && parseInt(me.getAttribute('data-theme-toggle-offset') || '0', 10) || 0;
  var seen = [];      // [{rule, orig, kind}]
  var known = new Set();
  var hasDark = false;
  var mode = 'auto';
  try { var s = localStorage.getItem(KEY); if (s === 'light' || s === 'dark' || s === 'auto') mode = s; } catch (e) {}

  function walk(rules) {
    var n; try { n = rules.length; } catch (e) { return; }
    for (var i = 0; i < n; i++) {
      var r = rules[i];
      try {
        if (r.media && r.cssRules && r.media.mediaText !== undefined && r.type === 4) {
          var t = r.media.mediaText;
          if (/prefers-color-scheme\s*:\s*dark/.test(t) && !/print/.test(t)) {
            hasDark = true;
            if (!known.has(r)) { known.add(r); seen.push({ rule: r, orig: t, kind: 'dark' }); }
          } else if (/prefers-color-scheme\s*:\s*light/.test(t) && !/print/.test(t)) {
            if (!known.has(r)) { known.add(r); seen.push({ rule: r, orig: t, kind: 'light' }); }
          }
          walk(r.cssRules);
        } else if (r.styleSheet) { walk(r.styleSheet.cssRules);
        } else if (r.cssRules) { walk(r.cssRules);
        } else if (r.selectorText && /data-theme\s*=\s*["']?dark/.test(r.selectorText)) { hasDark = true; }
      } catch (e) {}
    }
  }
  function scan() {
    var sh = document.styleSheets;
    for (var i = 0; i < sh.length; i++) { try { walk(sh[i].cssRules); } catch (e) {} }
  }
  function setMedia(item, text) { try { if (item.rule.media.mediaText !== text) item.rule.media.mediaText = text; } catch (e) {} }
  var INV = 'html[data-so-invert]{filter:invert(.92) hue-rotate(180deg);background:#fff}' +
    'html[data-so-invert] img,html[data-so-invert] video,html[data-so-invert] canvas,html[data-so-invert] svg image,html[data-so-invert] [data-no-invert]{filter:invert(1) hue-rotate(180deg)}';
  function apply() {
    scan();
    root.dataset.theme = mode;
    for (var i = 0; i < seen.length; i++) {
      var it = seen[i];
      if (mode === 'auto') setMedia(it, it.orig);
      else if (mode === 'dark') setMedia(it, it.kind === 'dark' ? 'all' : 'not all');
      else setMedia(it, it.kind === 'dark' ? 'not all' : 'all');
    }
    var invert = !hasDark && !root.hasAttribute('data-so-native-dark') && mode === 'dark';
    var st = document.getElementById('so-theme-invert');
    if (invert) {
      if (!st) { st = document.createElement('style'); st.id = 'so-theme-invert'; st.textContent = INV; (document.head || root).appendChild(st); }
      root.setAttribute('data-so-invert', '');
    } else { root.removeAttribute('data-so-invert'); }
    if (hasDark && mode !== 'auto') root.style.colorScheme = mode; else root.style.removeProperty('color-scheme');
    paint();
  }
  var btn;
  var GLYPH = { auto: '◐', light: '☀', dark: '☾' };
  var NEXT = { auto: 'light', light: 'dark', dark: 'auto' };
  function paint() {
    if (!btn) return;
    btn.textContent = GLYPH[mode];
    var l = 'Theme: ' + mode + (mode === 'auto' ? ' (follows system)' : '') + '. Click for ' + NEXT[mode] + '.';
    btn.setAttribute('aria-label', l); btn.title = l;
  }
  function mount() {
    if (btn || !document.body) return;
    var st = document.createElement('style');
    st.textContent = '#so-theme-btn{position:fixed;top:8px;right:calc(8px + var(--so-theme-toggle-right,' + offset + 'px));width:32px;height:32px;' +
      'padding:0;margin:0;border-radius:50%;border:1px solid rgba(128,128,128,.55);background:rgba(255,255,255,.85);color:#222;' +
      'font:16px/30px system-ui,sans-serif;text-align:center;cursor:pointer;z-index:2147483000;opacity:.6;box-shadow:0 1px 3px rgba(0,0,0,.2)}' +
      '#so-theme-btn:hover,#so-theme-btn:focus-visible{opacity:1}@media print{#so-theme-btn{display:none}}';
    document.head.appendChild(st);
    btn = document.createElement('button');
    btn.id = 'so-theme-btn'; btn.type = 'button'; btn.setAttribute('data-no-print', '');
    btn.addEventListener('click', function () {
      mode = NEXT[mode];
      try { localStorage.setItem(KEY, mode); } catch (e) {}
      apply();
    });
    document.body.appendChild(btn);
    paint();
  }
  window.soTheme = { get: function () { return mode; }, set: function (m) { mode = m; try { localStorage.setItem(KEY, m); } catch (e) {} apply(); } };
  apply();
  try {
    var mo = new MutationObserver(function (ms) {
      for (var i = 0; i < ms.length; i++) for (var j = 0; j < ms[i].addedNodes.length; j++) {
        var t = ms[i].addedNodes[j].tagName;
        if (t === 'STYLE' || t === 'LINK') { apply(); return; }
      }
    });
    mo.observe(root, { childList: true });
    if (document.head) mo.observe(document.head, { childList: true });
    else document.addEventListener('DOMContentLoaded', function () { mo.observe(document.head, { childList: true }); });
  } catch (e) {}
  document.addEventListener('load', function (e) { if (e.target && e.target.tagName === 'LINK') apply(); }, true);
  document.addEventListener('DOMContentLoaded', function () { mount(); apply(); });
  window.addEventListener('load', function () { mount(); apply(); });
})();
