#!/usr/bin/env python3
"""
FastAPI server for the RAG front-end: schema-filtered semantic search over the
SharkPapers corpus with cited, claim-strength-rated answers.

Models and indexes load ONCE at startup (not per request). The FAISS index is
hot-reloaded when it changes on disk, so the server serves a *growing* index
while build_from_cache.py is still embedding.

Run with the fashion-clip venv:
    /home/simon/.venvs/fashion-clip/bin/python -m uvicorn serve:app \
        --app-dir scripts/rag --host 127.0.0.1 --port 8000

Endpoints:
    GET  /                -> single-page app
    GET  /api/status      -> build progress + live index size
    GET  /api/filters     -> filter families, options, counts, ranges
    GET  /api/authors?q=  -> author autocomplete suggestions
    POST /api/query       -> {question, filters, top_k, retrieve_n, generate}
"""

from __future__ import annotations

import sys
import json
import threading
from contextlib import asynccontextmanager
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from common import (  # noqa: E402
    BGE_QUERY_PREFIX, CHUNKS_JSONL, EMBED_MODEL_NAME, FAISS_INDEX_PATH, RAG_OUT_DIR,
)
from filter_config import EXCLUDE, resolve_families  # noqa: E402
from retrieval import (  # noqa: E402
    build_author_map, build_position_map, positions_for_ids,
    resolve_filter_ids, search_preloaded,
)
import query as q  # noqa: E402  (reuse claim_strength, generate_answer, etc.)
from rerank import rerank as cross_encode_rerank, _get_model as _get_ce  # noqa: E402

PAPER_FILTERS = RAG_OUT_DIR / "paper_filters.parquet"
AUTHOR_INDEX = RAG_OUT_DIR / "author_index.parquet"
AUTHOR_SUGGEST = RAG_OUT_DIR / "author_suggest.parquet"
BUILD_STATUS_JSON = RAG_OUT_DIR / "build_status.json"
STATIC_DIR = HERE / "static"

S: dict = {}          # server state
_LOCK = threading.Lock()


def _load_chunks() -> list[dict]:
    with open(CHUNKS_JSONL, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _reload_index_if_stale() -> None:
    """Hot-reload the FAISS index + chunk metadata if the index file changed."""
    import faiss
    mtime = FAISS_INDEX_PATH.stat().st_mtime
    if S.get("index_mtime") == mtime:
        return
    with _LOCK:
        if S.get("index_mtime") == mtime:
            return
        index = faiss.read_index(str(FAISS_INDEX_PATH))
        chunks = _load_chunks()
        S["index"] = index
        S["chunks"] = chunks
        S["position_map"] = build_position_map(chunks)
        S["index_mtime"] = mtime
        S["n_papers"] = len(S["position_map"])
        S["n_chunks"] = len(chunks)


def _build_filters_payload() -> dict:
    """Precompute the /api/filters response from the sidecar + registry."""
    pf: pd.DataFrame = S["paper_filters"]
    families = []
    for spec in resolve_families(set(pf.columns) | {"author"}):
        entry = {"key": spec.key, "label": spec.label, "kind": spec.kind,
                 "widget": spec.widget, "note": spec.note}
        if spec.kind == "author":
            pass
        elif spec.kind == "bool_prefix":
            cols = sorted(c for c in pf.columns
                          if c.startswith(spec.prefix) and c not in EXCLUDE)
            entry["options"] = [
                {"value": c, "label": c[len(spec.prefix):].replace("_", " ").capitalize(),
                 "count": int((pd.to_numeric(pf[c], errors="coerce").fillna(0) > 0).sum())}
                for c in cols
            ]
        elif spec.kind == "bool_cols":
            entry["options"] = [
                {"value": c, "label": c.replace("geo_", "").replace("_", " ").capitalize(),
                 "count": int((pd.to_numeric(pf[c], errors="coerce").fillna(0) > 0).sum())}
                for c in spec.columns if c in pf.columns
            ]
        elif spec.kind == "categorical":
            vc = pf[spec.column].astype(str).replace({"nan": None}).dropna().value_counts()
            limit = 1200 if spec.widget == "search-multiselect" else 400
            entry["options"] = [{"value": v, "label": v, "count": int(n)}
                                for v, n in vc.head(limit).items()]
        elif spec.kind == "range":
            vals = pd.to_numeric(pf[spec.column], errors="coerce")
            entry["min"] = None if vals.min() != vals.min() else float(vals.min())
            entry["max"] = None if vals.max() != vals.max() else float(vals.max())
        families.append(entry)
    return {"families": families}


@asynccontextmanager
async def lifespan(app: FastAPI):
    from sentence_transformers import SentenceTransformer
    print("[startup] loading embedding model ...")
    S["embedder"] = SentenceTransformer(EMBED_MODEL_NAME, device="cpu")
    print("[startup] warming cross-encoder ...")
    _get_ce()
    print("[startup] loading filter sidecar + author index ...")
    pf = pd.read_parquet(PAPER_FILTERS)
    pf["literature_id"] = pf["literature_id"].astype(str)
    S["paper_filters"] = pf.set_index("literature_id")
    S["author_map"] = (build_author_map(pd.read_parquet(AUTHOR_INDEX))
                       if AUTHOR_INDEX.exists() else {})
    S["author_suggest"] = (pd.read_parquet(AUTHOR_SUGGEST)
                           if AUTHOR_SUGGEST.exists() else pd.DataFrame())
    S["filters_payload"] = _build_filters_payload()
    print("[startup] loading FAISS index ...")
    _reload_index_if_stale()
    print(f"[startup] ready — {S['n_papers']:,} papers / {S['n_chunks']:,} chunks")
    yield


app = FastAPI(title="SharkPapers RAG", lifespan=lifespan)


class QueryBody(BaseModel):
    question: str
    filters: dict = {}
    top_k: int = 8
    retrieve_n: int = 30
    generate: bool = True


@app.get("/")
def root():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/status")
def status():
    _reload_index_if_stale()
    build = {}
    if BUILD_STATUS_JSON.exists():
        try:
            build = json.loads(BUILD_STATUS_JSON.read_text())
        except (OSError, json.JSONDecodeError):
            build = {}
    return {"index_papers": S.get("n_papers", 0),
            "index_chunks": S.get("n_chunks", 0),
            "build": build}


@app.get("/api/filters")
def filters():
    return S["filters_payload"]


@app.get("/api/authors")
def authors(q: str = "", limit: int = 20):
    sug: pd.DataFrame = S["author_suggest"]
    if sug.empty or not q.strip():
        return {"suggestions": []}
    from retrieval import norm_name
    needle = norm_name(q)
    hit = sug[sug["norm"].str.contains(needle, regex=False, na=False)].head(limit)
    return {"suggestions": [
        {"display_name": r.display_name, "id": r.openalex_author_id,
         "paper_count": int(r.paper_count) if pd.notna(r.paper_count) else 0}
        for r in hit.itertuples()
    ]}


@app.post("/api/query")
def run_query(body: QueryBody):
    _reload_index_if_stale()
    pf = S["paper_filters"]
    allowed_ids = resolve_filter_ids(body.filters, pf, S["author_map"])
    n_match = None if allowed_ids is None else len(allowed_ids)

    positions = positions_for_ids(allowed_ids, S["position_map"])
    if positions is not None and positions.size == 0:
        return JSONResponse({
            "question": body.question,
            "n_papers_matching_filter": n_match,
            "n_papers_matching_indexed": 0,
            "answer": None, "mode": "no-match",
            "claim_strength": {"label": "unresolved",
                               "reason": "no indexed papers match the selected filters"},
            "retrieved": [],
        })

    retrieve_n = max(body.retrieve_n, body.top_k)
    candidates = search_preloaded(
        S["index"], S["chunks"], S["embedder"], body.question,
        retrieve_n, positions, BGE_QUERY_PREFIX,
    )
    hits = cross_encode_rerank(body.question, candidates, body.top_k)
    strength = q.claim_strength(hits)

    answer, mode = None, "retrieval-only"
    if body.generate and q.ollama_available():
        answer = q.generate_answer(body.question, hits)
        mode = f"generated ({q.OLLAMA_MODEL})"
    elif body.generate:
        mode = "stub (no LLM reachable)"

    return {
        "question": body.question,
        "n_papers_matching_filter": n_match,
        "n_papers_matching_indexed": (
            None if positions is None else int(len(set(
                q_.get("literature_id") for q_ in candidates)))),
        "answer": answer,
        "mode": mode,
        "claim_strength": strength,
        "retrieved": [
            {"literature_id": h["literature_id"], "title": h["title"],
             "authors": h["authors"], "year": h["year"], "journal": h.get("journal"),
             "cosine_score": round(h["score"], 3),
             "ce_score": round(h["ce_score"], 3) if h.get("ce_score") is not None else None,
             "text_preview": h["text"][:260].replace("\n", " ") + "..."}
            for h in hits
        ],
    }
