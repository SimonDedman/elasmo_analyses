/* Local author matcher for the validation landing page.
 *
 * Why this exists (2026-09-30): the page used to send every keystroke pause to
 * OpenAlex's `/authors?search=` list endpoint. That endpoint does stemmed
 * whole-word matching only (no prefix matching, so "Elena Fernández-Co" returns
 * nothing) and each call costs 10 credits of the 1,000-credit free daily budget
 * that OpenAlex shares between every machine behind one IP address. A whole
 * institute on one NAT address exhausts it by mid-morning and every later search
 * gets a 429. So the names we actually hold are matched here, in the browser,
 * with accent folding, hyphen folding, and word-order independence; OpenAlex is
 * only consulted for people who are not in our database.
 *
 * Works as a browser global (`AuthorSearch`) and as a CommonJS module (tests).
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.AuthorSearch = factory();
}(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  // Letters that NFD does not decompose to an ASCII base.
  const SPECIAL = {
    'ı': 'i',  // dotless i (Başçınar)
    'ł': 'l', 'Ł': 'l',   // ł
    'ø': 'o', 'Ø': 'o',   // ø
    'ß': 'ss',                 // ß
    'æ': 'ae', 'Æ': 'ae', // æ
    'œ': 'oe', 'Œ': 'oe', // œ
    'đ': 'd', 'Đ': 'd',   // đ
    'ð': 'd', 'Ð': 'd',   // ð
    'þ': 'th', 'Þ': 'th', // þ
    'ħ': 'h', 'Ħ': 'h',   // ħ
    'ŧ': 't', 'Ŧ': 't',   // ŧ
  };
  const SPECIAL_RE = new RegExp('[' + Object.keys(SPECIAL).join('') + ']', 'g');
  // Every dash-like code point OpenAlex has been seen to use (U+2010 is the common one).
  const DASH_RE = /[‐‑‒–—―−­⁃﹣－]/g;

  function fold(s) {
    return String(s || '')
      .replace(DASH_RE, '-')
      .normalize('NFD')
      .replace(/[̀-ͯ]/g, '')
      .replace(SPECIAL_RE, ch => SPECIAL[ch])
      .toLowerCase();
  }

  function tokens(s) {
    return fold(s).split(/[^a-z0-9]+/).filter(Boolean);
  }

  /** rows: [[id, name, institution, paperCount], ...] as written by
   *  scripts/generate_validation_pages.py into assets/authors_index.json. */
  function buildIndex(rows) {
    return rows.map(r => {
      const t = tokens(r[1]);
      return { id: r[0], name: r[1], institution: r[2] || '', count: r[3] || 0, tokens: t, key: t.slice().sort().join(' ') };
    });
  }

  function scoreEntry(entry, qtoks, qkey) {
    const used = new Array(entry.tokens.length).fill(false);
    let score = 0;
    for (const q of qtoks) {
      let best = -1, bestKind = 0;
      for (let i = 0; i < entry.tokens.length; i++) {
        if (used[i]) continue;
        const t = entry.tokens[i];
        if (t === q) { best = i; bestKind = 2; break; }
        if (bestKind < 1 && t.startsWith(q)) { best = i; bestKind = 1; }
      }
      if (best < 0) return -1;            // every query token must match somewhere
      used[best] = true;
      score += bestKind === 2 ? 10 : 3;
    }
    if (entry.key === qkey) score += 1000; // same words, any order
    score += 5 * qtoks.length / entry.tokens.length; // fully covered short names first
    return score;
  }

  function searchLocal(index, query, limit) {
    limit = limit || 10;
    const qtoks = tokens(query);
    if (qtoks.length === 0 || qtoks.join('').length < 2) return [];
    const qkey = qtoks.slice().sort().join(' ');
    const hits = [];
    for (const e of index) {
      const s = scoreEntry(e, qtoks, qkey);
      if (s >= 0) hits.push({ entry: e, score: s });
    }
    hits.sort((a, b) => (b.score - a.score) || (b.entry.count - a.entry.count) || a.entry.name.localeCompare(b.entry.name));
    return hits.slice(0, limit).map(h => h.entry);
  }

  return { fold, tokens, buildIndex, searchLocal };
}));
