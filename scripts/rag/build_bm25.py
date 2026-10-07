#!/usr/bin/env python3
"""
Build the SQLite FTS5 keyword index that sits beside the FAISS vectors.

    RAG_OUT_DIR=outputs/rag_test python scripts/rag/build_bm25.py

Reads <RAG_OUT_DIR>/chunks_meta.jsonl and writes <RAG_OUT_DIR>/fts.sqlite
(rebuilt fully each run, atomically) plus fts_status.json.

Design: a contentless FTS5 table (the text is not stored twice; chunks_meta
stays the source of the text), with rowid = pos = line position in
chunks_meta = FAISS vector position. A small `meta` table maps pos ->
literature_id. Tokenizer: porter unicode61 remove_diacritics 2.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CHUNKS_JSONL, RAG_OUT_DIR  # noqa: E402

FTS_DB = RAG_OUT_DIR / "fts.sqlite"
FTS_STATUS = RAG_OUT_DIR / "fts_status.json"


def build(chunks_path: Path = CHUNKS_JSONL, db_path: Path = FTS_DB) -> int:
    tmp = db_path.with_name(db_path.name + ".tmp")
    for p in (tmp, Path(str(tmp) + "-journal")):
        if p.exists():
            p.unlink()
    con = sqlite3.connect(tmp)
    con.execute("PRAGMA journal_mode=OFF")
    con.execute("PRAGMA synchronous=OFF")
    con.execute("CREATE VIRTUAL TABLE fts USING fts5("
                "text, content='', contentless_delete=0, "
                "tokenize='porter unicode61 remove_diacritics 2')")
    con.execute("CREATE TABLE meta(pos INTEGER PRIMARY KEY, literature_id TEXT)")
    n = 0
    batch_f, batch_m = [], []
    with open(chunks_path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            c = json.loads(line)
            lid = str(c["literature_id"])
            lid = lid[:-2] if lid.endswith(".0") else lid
            batch_f.append((n, c.get("text") or ""))
            batch_m.append((n, lid))
            n += 1
            if len(batch_f) >= 5000:
                con.executemany("INSERT INTO fts(rowid, text) VALUES (?, ?)", batch_f)
                con.executemany("INSERT INTO meta VALUES (?, ?)", batch_m)
                batch_f, batch_m = [], []
    if batch_f:
        con.executemany("INSERT INTO fts(rowid, text) VALUES (?, ?)", batch_f)
        con.executemany("INSERT INTO meta VALUES (?, ?)", batch_m)
    con.execute("INSERT INTO fts(fts) VALUES('optimize')")
    con.commit()
    con.close()
    os.replace(tmp, db_path)
    return n


def main() -> None:
    if not CHUNKS_JSONL.exists():
        sys.exit(f"missing {CHUNKS_JSONL}")
    t0 = time.time()
    n = build()
    status = {"rows": n, "built_epoch": time.time(),
              "seconds": round(time.time() - t0, 1),
              "db_bytes": FTS_DB.stat().st_size}
    tmp = FTS_STATUS.with_name(FTS_STATUS.name + ".tmp")
    tmp.write_text(json.dumps(status))
    os.replace(tmp, FTS_STATUS)
    print(f"fts.sqlite: {n:,} rows, {status['db_bytes']/1e6:.1f} MB, "
          f"{status['seconds']}s -> {FTS_DB}")


if __name__ == "__main__":
    main()
