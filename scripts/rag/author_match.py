"""Author-name matching for the RAG author autocomplete.

A faithful Python port of docs/validate/assets/author_search.js (written
2026-09-30 for the validation landing page): accent, dash and case folding,
word-order independence, and prefix matching on tokens, so "Elena Fernán"
finds "Elena Fernández‐Corredor". Keep the two in step; the rules (fold,
tokens, score constants) are deliberately identical.

Ranking: every query token must match a distinct name token (exactly: +10,
as a prefix: +3). A name made of the same words in any order gets +1000, and
a small bonus favours names that the query covers fully. Ties go to the
author with more papers, then to the name alphabetically.
"""

from __future__ import annotations

import re
import unicodedata

import pandas as pd

# Letters that NFD does not decompose to an ASCII base.
SPECIAL = {
    "ı": "i", "ł": "l", "Ł": "l", "ø": "o", "Ø": "o", "ß": "ss",
    "æ": "ae", "Æ": "ae", "œ": "oe", "Œ": "oe", "đ": "d", "Đ": "d",
    "ð": "d", "Ð": "d", "þ": "th", "Þ": "th", "ħ": "h", "Ħ": "h",
    "ŧ": "t", "Ŧ": "t",
}
_SPECIAL_RE = re.compile("[" + "".join(SPECIAL) + "]")
# Every dash-like code point OpenAlex has been seen to use (U+2010 is the common one).
_DASH_RE = re.compile("[‐‑‒–—―−­⁃﹣－]")
_COMBINING_RE = re.compile("[̀-ͯ]")
_SPLIT_RE = re.compile(r"[^a-z0-9]+")

MIN_QUERY_CHARS = 2


def fold(name) -> str:
    """Lower-case, accent-free, dash-normalised form (same as the JS `fold`)."""
    if name is None or (isinstance(name, float) and pd.isna(name)):
        return ""
    s = _DASH_RE.sub("-", str(name))
    s = unicodedata.normalize("NFD", s)
    s = _COMBINING_RE.sub("", s)
    s = _SPECIAL_RE.sub(lambda m: SPECIAL[m.group(0)], s)
    return s.lower()


def tokens(name) -> list[str]:
    return [t for t in _SPLIT_RE.split(fold(name)) if t]


def _score(entry_toks: list[str], qtoks: list[str], qkey: str):
    used = [False] * len(entry_toks)
    score = 0.0
    for q in qtoks:
        best, best_kind = -1, 0
        for i, t in enumerate(entry_toks):
            if used[i]:
                continue
            if t == q:
                best, best_kind = i, 2
                break
            if best_kind < 1 and t.startswith(q):
                best, best_kind = i, 1
        if best < 0:
            return None
        used[best] = True
        score += 10 if best_kind == 2 else 3
    if " ".join(sorted(entry_toks)) == qkey:
        score += 1000
    score += 5 * len(qtoks) / len(entry_toks)
    return score


def add_match_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add `norm` (folded name) and `tokens` (space-joined) columns."""
    df = df.copy()
    df["norm"] = df["display_name"].map(fold)
    df["tokens"] = df["norm"].map(lambda s: " ".join(t for t in _SPLIT_RE.split(s) if t))
    return df


_DERIVED: dict = {}


def _derived(df: pd.DataFrame) -> pd.DataFrame:
    """Cache the derived columns per frame object (old indexes lack them)."""
    key = id(df)
    hit = _DERIVED.get(key)
    if hit is None or hit[0] is not df:
        _DERIVED.clear()
        hit = _DERIVED[key] = (df, add_match_columns(df))
    return hit[1]


def match(query: str, candidates: pd.DataFrame, limit: int = 20) -> list:
    """Return up to `limit` rows (namedtuples) of `candidates`, best first.

    `candidates` is the author_suggest frame. If it lacks the `tokens` column
    (an index built before 2026-10-07) the columns are derived on the fly.
    """
    qtoks = tokens(query)
    if candidates is None or candidates.empty or not qtoks \
            or len("".join(qtoks)) < MIN_QUERY_CHARS:
        return []
    if "tokens" not in candidates.columns:
        candidates = _derived(candidates)
    qkey = " ".join(sorted(qtoks))
    # Cheap vectorised pre-filter: every query token must occur in the name.
    mask = pd.Series(True, index=candidates.index)
    for q in qtoks:
        mask &= candidates["tokens"].str.contains(q, regex=False, na=False)
    sub = candidates[mask]
    hits = []
    for r in sub.itertuples():
        toks = (r.tokens or "").split()
        if not toks:
            continue
        s = _score(toks, qtoks, qkey)
        if s is None:
            continue
        count = int(r.paper_count) if pd.notna(r.paper_count) else 0
        hits.append((-s, -count, str(r.display_name), r))
    hits.sort(key=lambda h: h[:3])
    return [h[3] for h in hits[:limit]]
