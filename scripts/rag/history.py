"""Query history (spec 'history seam'): SQLite at <RAG_OUT_DIR>/history.sqlite, WAL.

record() never raises; failures are logged and swallowed so a history problem
cannot break a query response.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

log = logging.getLogger("rag.history")

SCHEMA = """
CREATE TABLE IF NOT EXISTS queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL, client TEXT NOT NULL, question TEXT NOT NULL,
    filters_json TEXT, retrieval TEXT, mode TEXT, badge TEXT,
    retrieved_ids TEXT, answer TEXT, latency_ms INTEGER
);
CREATE INDEX IF NOT EXISTS queries_client_ts ON queries(client, ts DESC);
"""


def _db_path() -> Path:
    return common.RAG_STATE_DIR / "history.sqlite"


def _connect() -> sqlite3.Connection:
    con = sqlite3.connect(_db_path(), timeout=5)
    con.execute("PRAGMA journal_mode=WAL")
    con.executescript(SCHEMA)
    return con


def record(client: str, question: str, filters: dict | None, retrieval: str | None,
           mode: str | None, badge: str | None, retrieved_ids: list | None,
           answer: str | None, latency_ms: int | float | None) -> None:
    try:
        con = _connect()
        try:
            with con:
                con.execute(
                    "INSERT INTO queries(ts, client, question, filters_json, retrieval, mode,"
                    " badge, retrieved_ids, answer, latency_ms) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (time.time(), client, question, json.dumps(filters or {}, default=str),
                     retrieval, mode, badge,
                     json.dumps([str(i) for i in (retrieved_ids or [])]),
                     answer, None if latency_ms is None else int(latency_ms)))
        finally:
            con.close()
    except Exception as e:  # noqa: BLE001 - must never reach the response path
        log.warning("history.record failed: %s", e)


def recent(client: str, limit: int = 20) -> list[dict]:
    limit = max(1, min(int(limit), 200))
    try:
        con = _connect()
        try:
            rows = con.execute(
                "SELECT ts, question, filters_json, retrieval, mode, badge, retrieved_ids,"
                " answer, latency_ms FROM queries WHERE client=? ORDER BY ts DESC, id DESC LIMIT ?",
                (client, limit)).fetchall()
        finally:
            con.close()
    except Exception as e:  # noqa: BLE001
        log.warning("history.recent failed: %s", e)
        return []
    keys = ("ts", "question", "filters", "retrieval", "mode", "badge",
            "retrieved_ids", "answer", "latency_ms")
    out = []
    for r in rows:
        d = dict(zip(keys, r))
        d["filters"] = json.loads(d["filters"] or "{}")
        d["retrieved_ids"] = json.loads(d["retrieved_ids"] or "[]")
        out.append(d)
    return out
