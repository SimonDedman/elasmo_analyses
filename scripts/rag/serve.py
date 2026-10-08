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
    GET  /api/history?limit= -> the caller's own recent queries
    GET  /api/export?ids=1,2&fmt= -> references (bibtex|ris|csv|json|apa|harvard|vancouver|chicago|mla)
"""

from __future__ import annotations

import sys
import json
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from common import (  # noqa: E402
    BGE_QUERY_PREFIX, CHUNKS_JSONL, EMBED_MODEL_NAME, FAISS_INDEX_PATH, RAG_OUT_DIR,
)
from filter_config import EXCLUDE, FLAG_LABELS, VALUE_LABELS, resolve_families  # noqa: E402
import labels  # noqa: E402
from retrieval import (  # noqa: E402
    build_author_map, build_position_map, positions_for_ids,
    page_papers, resolve_filter_ids, search_preloaded,
)
import history  # noqa: E402
from auth import require_access  # noqa: E402
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


SORT_LABELS = {"freq": "frequency", "az": "A-Z", "geo": "geological time", "best": "best to worst"}


def _count_true(series: pd.Series) -> int:
    return int((pd.to_numeric(series, errors="coerce").fillna(0) > 0).sum())


def _value_label(spec, v: str) -> str:
    if spec.key in VALUE_LABELS:
        return VALUE_LABELS[spec.key].get(v, v)
    if spec.key == "epoch":
        return labels.epoch_label(v)
    if spec.key == "oa_status":
        return v[:1].upper() + v[1:]
    if spec.key in ("study_basin",):
        return labels.title_case(v)
    return v


def _build_filters_payload() -> dict:
    """Precompute the /api/filters response from the sidecar + registry."""
    pf: pd.DataFrame = S["paper_filters"]
    families = []
    for spec in resolve_families(set(pf.columns) | {"author"}):
        entry = {"key": spec.key, "label": spec.label, "kind": spec.kind,
                 "widget": spec.widget, "note": spec.note}
        if spec.sorts:
            entry["sorts"] = [{"id": i, "label": SORT_LABELS[i]} for i in spec.sorts]
            entry["default_sort"] = spec.default_sort
        if spec.kind == "author":
            pass
        elif spec.kind == "bool_prefix":
            cols = sorted(c for c in pf.columns
                          if c.startswith(spec.prefix) and c not in EXCLUDE)
            opts = [{"value": c, "label": labels.label_for(c), "count": _count_true(pf[c])}
                    for c in cols]
            # Drop options that can never match (non-boolean columns such as
            # imp_direction coerce to all-zero).
            entry["options"] = sorted((o for o in opts if o["count"] > 0),
                                      key=lambda o: o["label"].lower())
        elif spec.kind == "bool_cols":
            entry["options"] = [
                {"value": c, "label": FLAG_LABELS.get(c) or labels.label_for(c.replace("geo_", "")),
                 "count": _count_true(pf[c])}
                for c in spec.columns if c in pf.columns
            ]
        elif spec.kind == "categorical":
            col = pf[spec.column].astype(str)
            col = col[~col.map(labels.is_blank)]
            vc = col.value_counts()
            limit = 1200 if spec.widget == "search-multiselect" else 400
            opts = []
            for v, n in vc.head(limit).items():
                o = {"value": v, "label": _value_label(spec, v), "count": int(n)}
                if spec.key == "epoch":
                    o["rank"] = labels.epoch_rank(v)
                elif spec.key == "oa_status":
                    o["rank"] = labels.oa_rank(v)
                opts.append(o)
            entry["options"] = opts
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
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class QueryBody(BaseModel):
    question: str
    filters: dict = {}
    top_k: int = 8
    retrieve_n: int = 30
    generate: bool = True


class PapersBody(BaseModel):
    filters: dict = {}
    page: int = 1
    page_size: int = 50
    sort: str = "year_desc"   # year_desc | year_asc | title


@app.post("/api/papers")
def api_papers(body: PapersBody):
    """Browse without a question: metadata of every paper matching the filters
    (no retrieval, no LLM). 400 when no filter is active."""
    if body.sort not in ("year_desc", "year_asc", "title"):
        raise HTTPException(400, "sort must be year_desc, year_asc or title")
    ids = resolve_filter_ids(body.filters, S["paper_filters"], S["author_map"])
    if ids is None:
        raise HTTPException(400, "choose at least one filter to list papers")
    if "meta" not in S:
        import common
        S["meta"] = common.load_metadata().drop_duplicates("literature_id").set_index(
            "literature_id", drop=False)
    return page_papers(ids, S["meta"], body.sort, body.page, min(max(body.page_size, 1), 200))


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
    from author_match import match
    hit = match(q, sug, limit)
    return {"suggestions": [
        {"display_name": r.display_name, "id": r.openalex_author_id,
         "paper_count": int(r.paper_count) if pd.notna(r.paper_count) else 0}
        for r in hit
    ]}


@app.get("/api/history")
def api_history(limit: int = 20, client: str = Depends(require_access)):
    """The caller's own recent queries (never another client's)."""
    return {"client": client, "queries": history.recent(client, limit)}


@app.post("/api/query")
def run_query(body: QueryBody, client: str = Depends(require_access)):
    t0 = time.perf_counter()
    resp = _run_query(body)
    try:
        data = json.loads(resp.body) if isinstance(resp, JSONResponse) else resp
        history.record(
            client, body.question, body.filters, data.get("retrieval"),
            data.get("mode"), (data.get("claim_strength") or {}).get("label"),
            [h.get("literature_id") for h in data.get("retrieved", [])],
            data.get("answer"), (time.perf_counter() - t0) * 1000)
    except Exception as e:  # noqa: BLE001 - history must never break a query
        print(f"[history] not recorded: {e}")
    return resp


def _why(h: dict, question: str, retrieval_mode: str, fused_rank: dict) -> dict:
    """Per-source explanation: which channel(s) found the chunk, which query
    terms occur in it, the full passage, and the raw scores."""
    from hybrid import matched_terms
    chans = h.get("channels") or ["vector"]
    return {
        "channels": chans,
        "retrieval": retrieval_mode,
        "matched_terms": matched_terms(question, h["text"]),
        "passage": h["text"],
        "chunk_id": h.get("pos"),
        "fts_score": round(h["fts_score"], 3) if h.get("fts_score") is not None else None,
        "fused_score": round(h["fused_score"], 4) if h.get("fused_score") is not None else None,
        "fused_rank": fused_rank.get(h.get("pos")),
    }


EXPORT_COLS = ("literature_id", "title", "authors", "year", "doi", "journal", "volume",
               "issue", "pages", "abstract", "pdf_url")


def _export_meta() -> pd.DataFrame:
    if "export_meta" not in S:
        import pyarrow.parquet as pq
        from common import PARQUET_PATH
        have = set(pq.ParquetFile(PARQUET_PATH).schema.names)
        df = pd.read_parquet(PARQUET_PATH, columns=[c for c in EXPORT_COLS if c in have])
        df["literature_id"] = df["literature_id"].astype(str)
        S["export_meta"] = df.drop_duplicates("literature_id").set_index("literature_id", drop=False)
    return S["export_meta"]


@app.get("/api/export")
def api_export(ids: str = "", fmt: str = "bibtex", client: str = Depends(require_access)):
    """Reference export for the given literature_ids (order kept, unknown ids
    skipped). 400 on empty ids or unknown format, 404 when no id is known."""
    import export_refs as ex
    want = [i.strip() for i in ids.split(",") if i.strip()]
    if not want:
        raise HTTPException(400, "ids is required (comma-separated literature_ids)")
    fmt = fmt.lower()
    if fmt not in ex.FORMATS:
        raise HTTPException(400, f"fmt must be one of {', '.join(ex.FORMATS)}")
    meta = _export_meta()
    seen, rows = set(), []
    for i in want:
        if i in meta.index and i not in seen:
            seen.add(i)
            rows.append(meta.loc[i].to_dict())
    if not rows:
        raise HTTPException(404, "none of the ids are in the corpus")
    mime, ext = ex.MEDIA.get(fmt, ("text/plain", "txt"))
    return Response(ex.render(rows, fmt), media_type=mime + "; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="shark_oracle_references_{fmt}.{ext}"'})


def _run_query(body: QueryBody):
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
    fts_db = RAG_OUT_DIR / "fts.sqlite"
    if fts_db.exists():
        from retrieval import search_hybrid
        retrieval_mode = "hybrid"
        candidates = search_hybrid(
            S["index"], S["chunks"], S["embedder"], body.question,
            retrieve_n, positions, BGE_QUERY_PREFIX, fts_db,
        )
    else:
        retrieval_mode = "vector"
        candidates = search_preloaded(
            S["index"], S["chunks"], S["embedder"], body.question,
            retrieve_n, positions, BGE_QUERY_PREFIX,
        )
    fused_rank = {c.get("pos"): i for i, c in enumerate(candidates, start=1)}
    hits = cross_encode_rerank(body.question, candidates, body.top_k)
    strength = q.claim_strength(hits)

    answer, mode = None, "retrieval-only"
    llm_ok, llm_name = q.llm_backend_status()
    if body.generate and llm_ok:
        answer = q.generate_answer(body.question, hits)
        mode = f"generated ({llm_name})"
    elif body.generate:
        mode = "stub (no LLM reachable)"

    rated = q.rate_answer(answer, hits, strength)

    return {
        "question": body.question,
        "n_papers_matching_filter": n_match,
        "n_papers_matching_indexed": (
            None if positions is None else int(len(set(
                q_.get("literature_id") for q_ in candidates)))),
        "answer": answer,
        "mode": mode,
        "retrieval": retrieval_mode,
        "claim_strength": rated["claim_strength"],
        "claim_strength_topic": rated["claim_strength_topic"],
        "sentences": rated["sentences"],
        "retrieved": [
            {"literature_id": h["literature_id"], "title": h["title"],
             "authors": h["authors"], "year": h["year"], "journal": h.get("journal"),
             "cosine_score": round(h["score"], 3),
             "ce_score": round(h["ce_score"], 3) if h.get("ce_score") is not None else None,
             "text_preview": h["text"][:260].replace("\n", " ") + "...",
             "why": _why(h, body.question, retrieval_mode, fused_rank)}
            for h in hits
        ],
    }
