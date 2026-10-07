"""Hybrid (FTS5 BM25 + FAISS) retrieval, against the outputs/rag_test index."""
import json
import os
import re
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
TEST_DIR = ROOT / "outputs" / "rag_test"
os.environ["RAG_OUT_DIR"] = str(TEST_DIR)
sys.path.insert(0, str(ROOT / "scripts" / "rag"))

from common import BGE_QUERY_PREFIX, CHUNKS_JSONL, EMBED_MODEL_NAME, FAISS_INDEX_PATH  # noqa: E402
import build_bm25  # noqa: E402
import hybrid  # noqa: E402
from retrieval import build_position_map, positions_for_ids, search_hybrid, search_preloaded  # noqa: E402

BINOMIAL = "Squalus americanus"


@pytest.fixture(scope="module")
def env():
    if not CHUNKS_JSONL.exists():
        pytest.skip("outputs/rag_test not built")
    import faiss
    from sentence_transformers import SentenceTransformer
    build_bm25.main()
    chunks = [json.loads(l) for l in open(CHUNKS_JSONL, encoding="utf-8")]
    return {"chunks": chunks, "index": faiss.read_index(str(FAISS_INDEX_PATH)),
            "model": SentenceTransformer(EMBED_MODEL_NAME, device="cpu"),
            "db": build_bm25.FTS_DB}


def papers(hits, k=5):
    out = []
    for h in hits:
        if h["literature_id"] not in out:
            out.append(h["literature_id"])
    return out[:k]


def test_db_rows_match_chunks(env):
    import sqlite3
    con = sqlite3.connect(f"file:{env['db']}?mode=ro", uri=True)
    assert con.execute("SELECT count(*) FROM meta").fetchone()[0] == len(env["chunks"])
    st = json.loads(build_bm25.FTS_STATUS.read_text())
    assert st["rows"] == len(env["chunks"]) and st["built_epoch"] > 0


def test_binomial_found_in_top5_hybrid(env):
    rel = {c["literature_id"] for c in env["chunks"] if BINOMIAL in c["text"]}
    assert rel, "test binomial no longer in rag_test texts"
    args = (env["index"], env["chunks"], env["model"], BINOMIAL, 30, None, BGE_QUERY_PREFIX)
    vec = papers(search_preloaded(*args))
    hyb = papers(search_hybrid(*args, env["db"]))
    print(f"vector-only found {BINOMIAL!r} in top 5: {bool(rel & set(vec))}")
    assert rel & set(hyb)
    h = search_hybrid(*args, env["db"])[0]
    assert {"score", "fts_score", "fused_score", "channels"} <= set(h)


def test_filter_positions_honoured(env):
    pm = build_position_map(env["chunks"])
    lids = list(pm)[:5]
    allowed = positions_for_ids(set(lids), pm)
    hits = search_hybrid(env["index"], env["chunks"], env["model"], "shark movement",
                         20, allowed, BGE_QUERY_PREFIX, env["db"])
    assert hits and {h["pos"] for h in hits} <= set(allowed.tolist())
    # large allowed set goes through the temp-table path
    big = np.arange(0, len(env["chunks"]) // 2, dtype="int64")
    assert big.size > 500
    res = hybrid.fts_search(env["db"], "shark", 20, big)
    assert res and all(p in set(big.tolist()) for p, _ in res)
    assert hybrid.fts_search(env["db"], "shark", 5, np.array([], dtype="int64")) == []


@pytest.mark.parametrize("q", ['say "unterminated phrase', "title: foo OR (bar", 'a"b:c*', "NEAR(", "", "***", "'; DROP TABLE fts;--"])
def test_hostile_queries_do_not_raise(env, q):
    hybrid.fts_query_from_question(q)
    assert isinstance(hybrid.fts_search(env["db"], q, 5), list)


def test_query_builder_shapes():
    f = hybrid.fts_query_from_question
    assert '"gill net"' in f('effects of "gill net" use')
    assert '"longline"*' in f("longline* bycatch")
    assert '"Squalus americanus"' in f("Squalus americanus diet")
    assert '"the"' not in f("the shark")


def test_rrf_fuse_channels():
    out = hybrid.rrf_fuse([(1, .9), (2, .8)], [(2, 5.0), (3, 4.0)], k=60, n=10)
    assert out[0][0] == 2 and out[0][2] == ["vector", "fts"]
    assert {p for p, _, _ in out} == {1, 2, 3}
