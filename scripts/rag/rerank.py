#!/usr/bin/env python3
"""
Cross-encoder re-ranking stage for the RAG prototype.

Why: BGE-small cosine similarity (used for the initial FAISS retrieval) runs
high in absolute terms and does not cleanly separate on-topic passages from
merely topic-adjacent ones — the "CRISPR gene editing for shark embryos"
probe pulled shark-genomics papers at cosine ~0.78-0.80 and got labelled
WELL-SUPPORTED even though none of them describe CRISPR (see
docs/LLM/rag_prototype_status.md, "Limitations"). A cross-encoder scores the
(query, passage) pair directly with full cross-attention between the two
texts, rather than comparing two independently-computed vectors, which makes
its scores far better calibrated to actual relevance — at the cost of being
much slower per pair, so it is only run over the FAISS top-N shortlist, not
the whole index.

Model: cross-encoder/ms-marco-MiniLM-L-6-v2 (~23M params, CPU-fast, trained
on MS MARCO passage relevance ranking). Raw output is an UNBOUNDED LOGIT
(observed roughly -11 to +8 on this corpus), not a 0-1 probability — the
claim-strength thresholds in query.py are tuned against these logits.
"""

from __future__ import annotations

CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import CrossEncoder
        _model = CrossEncoder(CROSS_ENCODER_MODEL, device="cpu")
    return _model


def rerank(question: str, hits: list[dict], top_k: int) -> list[dict]:
    """Score each hit's chunk text against the question with the cross-encoder,
    sort descending by that score, and keep the top_k.

    Adds a `ce_score` key (float, unbounded logit) to every hit in-place.
    The original FAISS cosine similarity is left under `score` for reference/
    display — it is no longer what claim-strength is computed from.
    """
    if not hits:
        return hits
    model = _get_model()
    pairs = [(question, h["text"]) for h in hits]
    scores = model.predict(pairs)
    for h, s in zip(hits, scores):
        h["ce_score"] = float(s)
    return sorted(hits, key=lambda h: h["ce_score"], reverse=True)[:top_k]
