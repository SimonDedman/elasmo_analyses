#!/usr/bin/env python3
"""
Filter resolution + FAISS pre-filtered retrieval for the RAG server.

Kept separate from query.py (the CLI) so the server can hold preloaded models
and indexes in memory and call these stateless helpers. Filter semantics:
OR within a family (any selected value matches), AND across families (every
touched family must match) — standard faceted search.
"""

from __future__ import annotations

import sys
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from filter_config import FAMILY_SPECS  # noqa: E402

_SPEC_BY_KEY = {s.key: s for s in FAMILY_SPECS}


def clean_id(s) -> str:
    s = str(s)
    return s[:-2] if s.endswith(".0") else s


def norm_name(s: str) -> str:
    s = "".join(c for c in unicodedata.normalize("NFKD", str(s))
                if not unicodedata.combining(c))
    return s.lower().strip()


def build_position_map(chunks: list[dict]) -> dict[str, list[int]]:
    """literature_id -> list of chunk vector positions (chunks_meta order)."""
    pos: dict[str, list[int]] = {}
    for i, c in enumerate(chunks):
        pos.setdefault(clean_id(c["literature_id"]), []).append(i)
    return pos


def build_author_map(author_index: pd.DataFrame) -> dict[str, set[str]]:
    """openalex_author_id -> set of literature_ids."""
    out: dict[str, set[str]] = {}
    for aid, lid in zip(author_index["openalex_author_id"],
                        author_index["literature_id"]):
        out.setdefault(aid, set()).add(clean_id(lid))
    return out


def resolve_filter_ids(
    filters: dict,
    pf: pd.DataFrame,
    author_map: dict[str, set[str]],
) -> set[str] | None:
    """Return the set of literature_ids matching all active filters, or None
    (meaning no active filter -> search the whole corpus).

    `pf` must be the paper_filters frame indexed by literature_id.
    `filters` maps family_key -> selection (list for multiselect/categorical/
    author, {"min":..,"max":..} for range).
    """
    if not filters:
        return None

    result: set[str] | None = None

    def intersect(ids: set[str]) -> None:
        nonlocal result
        result = ids if result is None else (result & ids)

    for key, sel in filters.items():
        spec = _SPEC_BY_KEY.get(key)
        if spec is None or sel in (None, [], "", {}):
            continue

        if spec.kind in ("bool_prefix", "bool_cols"):
            cols = [c for c in sel if c in pf.columns]
            if not cols:
                intersect(set())
                continue
            mask = pd.Series(False, index=pf.index)
            for c in cols:
                mask = mask | (pd.to_numeric(pf[c], errors="coerce").fillna(0) > 0)
            intersect(set(pf.index[mask]))

        elif spec.kind == "categorical":
            col = spec.column
            if col not in pf.columns:
                intersect(set())
                continue
            wanted = {str(v) for v in sel}
            mask = pf[col].astype(str).isin(wanted)
            intersect(set(pf.index[mask]))

        elif spec.kind == "range":
            col = spec.column
            if col not in pf.columns:
                intersect(set())
                continue
            vals = pd.to_numeric(pf[col], errors="coerce")
            mask = vals.notna()
            lo, hi = sel.get("min"), sel.get("max")
            if lo is not None:
                mask &= vals >= float(lo)
            if hi is not None:
                mask &= vals <= float(hi)
            intersect(set(pf.index[mask]))

        elif spec.kind == "author":
            ids: set[str] = set()
            for aid in sel:
                ids |= author_map.get(aid, set())
            intersect(ids)

    return result if result is not None else None


def positions_for_ids(
    allowed_ids: set[str] | None, position_map: dict[str, list[int]]
) -> np.ndarray | None:
    """Map allowed literature_ids to a sorted int64 array of chunk positions.
    Returns None when there is no filter (search everything). An empty array
    means the filter matched nothing indexed."""
    if allowed_ids is None:
        return None
    positions: list[int] = []
    for lid in allowed_ids:
        positions.extend(position_map.get(lid, ()))
    return np.array(sorted(positions), dtype="int64")


def search_preloaded(
    index, chunks: list[dict], model, question: str,
    retrieve_n: int, allowed_positions: np.ndarray | None,
    query_prefix: str,
) -> list[dict]:
    """FAISS cosine retrieval with an optional IDSelectorBatch pre-filter,
    using preloaded index/model/chunks."""
    import faiss

    qvec = model.encode(
        [query_prefix + question], normalize_embeddings=True,
        convert_to_numpy=True,
    ).astype("float32")

    if allowed_positions is not None:
        if allowed_positions.size == 0:
            return []
        sel = faiss.IDSelectorBatch(allowed_positions)
        params = faiss.SearchParameters(sel=sel)
        scores, idxs = index.search(qvec, retrieve_n, params=params)
    else:
        scores, idxs = index.search(qvec, retrieve_n)

    hits = []
    for score, idx in zip(scores[0], idxs[0]):
        if idx < 0:
            continue
        c = dict(chunks[idx])
        c["score"] = float(score)
        hits.append(c)
    return hits
