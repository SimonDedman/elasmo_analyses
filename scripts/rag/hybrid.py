#!/usr/bin/env python3
"""
Keyword (FTS5 / BM25) retrieval and rank fusion for the hybrid RAG search.

Vector search misses exact terms (binomials, gear acronyms, place names).
`fts_search` queries the sidecar built by build_bm25.py; `rrf_fuse` merges its
ranking with the FAISS ranking by reciprocal rank fusion.
"""

from __future__ import annotations

import re
import sqlite3
import threading
from pathlib import Path

import numpy as np

STOPWORDS = frozenset("""
a about above after again against all also am an and any are as at be because
been before being below between both but by can could did do does doing down
during each few for from further had has have having he her here hers him his
how i if in into is it its just me more most my no nor not of off on once only
or other our out over own same she should so some such than that the their
them then there these they this those through to too under until up us very
was we were what when where which while who whom why will with would you your
""".split())

_PHRASE = re.compile(r'"([^"]*)"')
_WORD = re.compile(r"\w+", re.UNICODE)
_WILD = re.compile(r"(\w+)\*")
_BINOMIAL = re.compile(r"\b([A-Z][a-z]{2,})\s+([a-z]{3,})\b")


def _q(term: str) -> str:
    """One safely quoted FTS5 string."""
    return '"' + term.replace('"', '""') + '"'


def fts_query_from_question(q: str) -> str:
    """Build a MATCH expression. User-quoted phrases stay phrases, `word*`
    stays a prefix query, Genus-species pairs also become phrases, and every
    other content word is OR-ed. Returns '' when nothing usable remains."""
    parts: list[str] = []
    seen: set[str] = set()

    def add(expr: str) -> None:
        if expr not in seen:
            seen.add(expr)
            parts.append(expr)

    for m in _PHRASE.finditer(q):
        words = _WORD.findall(m.group(1))
        if len(words) == 1:
            add(_q(words[0]))
        elif words:
            add(_q(" ".join(words)))
    rest = _PHRASE.sub(" ", q)
    rest = rest.replace('"', " ")
    for m in _BINOMIAL.finditer(rest):
        if m.group(1).lower() not in STOPWORDS:
            add(_q(f"{m.group(1)} {m.group(2)}"))
    for m in _WILD.finditer(rest):
        add(_q(m.group(1)) + "*")
    rest = _WILD.sub(" ", rest)
    for w in _WORD.findall(rest):
        if w.lower() in STOPWORDS or (len(w) < 2 and not w.isdigit()):
            continue
        add(_q(w))
    return " OR ".join(parts)


_CONN: dict = {}
_LOCK = threading.Lock()


def _connect(db: Path) -> sqlite3.Connection:
    """Read-only connection, reopened when the file's mtime changes."""
    db = Path(db)
    mtime = db.stat().st_mtime_ns
    ent = _CONN.get(str(db))
    if ent and ent[0] == mtime:
        return ent[1]
    if ent:
        try:
            ent[1].close()
        except sqlite3.Error:
            pass
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True, check_same_thread=False)
    _CONN[str(db)] = (mtime, con)
    return con


def fts_search(db, q: str, n: int,
               allowed_positions: np.ndarray | None = None
               ) -> list[tuple[int, float]]:
    """Top-n (pos, score) by BM25, best first. Score is positive, higher is
    better (negated SQLite bm25). allowed_positions restricts the search; an
    empty array returns []."""
    if allowed_positions is not None and allowed_positions.size == 0:
        return []
    expr = fts_query_from_question(q)
    if not expr:
        return []
    with _LOCK:
        con = _connect(Path(db))
        try:
            if allowed_positions is None:
                rows = con.execute(
                    "SELECT rowid, bm25(fts) AS s FROM fts WHERE fts MATCH ? "
                    "ORDER BY s LIMIT ?", (expr, n)).fetchall()
            elif allowed_positions.size <= 500:
                ph = ",".join("?" * allowed_positions.size)
                rows = con.execute(
                    f"SELECT rowid, bm25(fts) AS s FROM fts WHERE fts MATCH ? "
                    f"AND rowid IN ({ph}) ORDER BY s LIMIT ?",
                    (expr, *[int(p) for p in allowed_positions], n)).fetchall()
            else:
                con.execute("CREATE TEMP TABLE IF NOT EXISTS allowed(pos INTEGER PRIMARY KEY)")
                con.execute("DELETE FROM allowed")
                con.executemany("INSERT OR IGNORE INTO allowed VALUES (?)",
                                ((int(p),) for p in allowed_positions))
                rows = con.execute(
                    "SELECT f.rowid, bm25(fts) AS s FROM fts f "
                    "JOIN allowed a ON a.pos = f.rowid WHERE fts MATCH ? "
                    "ORDER BY s LIMIT ?", (expr, n)).fetchall()
        except sqlite3.OperationalError:
            return []   # unparseable expression: degrade to vector-only
    return [(int(r), -float(s)) for r, s in rows]


def rrf_fuse(vector_hits: list[tuple[int, float]],
             fts_hits: list[tuple[int, float]],
             k: int = 60, n: int = 30
             ) -> list[tuple[int, float, list[str]]]:
    """Reciprocal rank fusion over two ranked lists of (pos, score).
    Returns [(pos, fused_score, channels)] best first, channels a subset of
    ['vector', 'fts']."""
    fused: dict[int, float] = {}
    chans: dict[int, list[str]] = {}
    for name, hits in (("vector", vector_hits), ("fts", fts_hits)):
        for rank, (pos, _s) in enumerate(hits, start=1):
            fused[pos] = fused.get(pos, 0.0) + 1.0 / (k + rank)
            chans.setdefault(pos, []).append(name)
    order = sorted(fused, key=lambda p: (-fused[p], p))[:n]
    return [(p, fused[p], chans[p]) for p in order]


_QTERM = re.compile(r'"((?:[^"]|"")*)"(\*?)')


def _stem(w: str) -> str:
    """Crude stem approximating FTS5's porter tokenizer, for display only."""
    w = w.lower()
    for suf in ("ing", "ed", "es", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[: -len(suf)]
    return w


def matched_terms(question: str, text: str) -> list[str]:
    """Query terms from the FTS expression that occur in `text` (case- and
    accent-insensitive, stem-tolerant like the porter tokenizer). Returns the
    query-side terms, e.g. ['bull shark', 'Chennai']. Display helper only; it
    never affects ranking."""
    import unicodedata

    def fold(s: str) -> str:
        return "".join(c for c in unicodedata.normalize("NFKD", s)
                       if not unicodedata.combining(c)).lower()

    expr = fts_query_from_question(question)
    body = fold(text or "")
    found: list[str] = []
    for m in _QTERM.finditer(expr):
        term = m.group(1).replace('""', '"')
        words = [fold(w) for w in _WORD.findall(term)]
        if not words:
            continue
        parts = [r"\b" + re.escape(_stem(w)) + r"\w*"
                 for i, w in enumerate(words)]
        if re.search(r"\W+".join(parts), body) and term not in found:
            found.append(term)
    return found
