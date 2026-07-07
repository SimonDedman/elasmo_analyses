#!/usr/bin/env python3
"""
Query the RAG prototype index built by build_index.py.

Run with the fashion-clip venv (has sentence-transformers/faiss):

    /home/simon/.venvs/fashion-clip/bin/python scripts/rag/query.py \
        "What techniques are used for age determination in deep-sea sharks?"

Flags:
    --top-k N        number of chunks to keep after re-ranking (default 8)
    --retrieve-n N   number of FAISS candidates to pull before re-ranking
                     (default 20; must be >= --top-k)
    --no-rerank      skip the cross-encoder stage, use raw FAISS cosine order
                     and the old absolute-cosine claim-strength (for A/B
                     comparison only — this reintroduces the over-reporting
                     bug, see docs/LLM/rag_prototype_status.md)
    --no-generate    skip the LLM call, print the ranked cited context only
    --json           print machine-readable JSON instead of formatted text

Pipeline: embed question (BGE query prefix) -> FAISS cosine retrieval of the
top --retrieve-n candidates over outputs/rag/index.faiss -> CROSS-ENCODER
RE-RANK those candidates by directly scoring (question, chunk_text) pairs
(scripts/rag/rerank.py) -> keep top --top-k -> build a cited context block ->
(if Ollama is reachable) generate an answer instructed to cite
[literature_id] inline -> compute a claim-strength rating from the
cross-encoder scores, independent of whatever the LLM says (LLMs are not a
trustworthy source of their own confidence, so this is scored
programmatically from the retrieved evidence).

Why the cross-encoder stage exists: BGE cosine similarity runs high in
absolute terms and cannot separate on-topic from merely topic-adjacent
passages (an out-of-sample probe, "CRISPR gene editing protocols for shark
embryos" — no such papers in the corpus — still scored ~0.80 cosine on
shark-genomics papers and was labelled WELL-SUPPORTED). The cross-encoder
scores the full (query, passage) pair with cross-attention rather than
comparing two independently-embedded vectors, so its scores are much better
calibrated to actual relevance — see rerank.py and
docs/LLM/rag_prototype_status.md for detail and the before/after numbers.
"""

from __future__ import annotations

import argparse
import json
import sys
import textwrap
from collections import defaultdict
from pathlib import Path

import numpy as np
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (  # noqa: E402
    BGE_QUERY_PREFIX, CHUNKS_JSONL, EMBED_MODEL_NAME, EMBEDDINGS_NPY,
    FAISS_INDEX_PATH, OLLAMA_HOST, OLLAMA_MODEL,
)
from rerank import rerank as cross_encode_rerank  # noqa: E402

# --- Legacy (pre-rerank) claim-strength thresholds on absolute cosine ------
# Kept only for --no-rerank A/B comparison; this is the miscalibrated
# heuristic documented as over-reporting in docs/LLM/rag_prototype_status.md.
SIM_CONCORDANT = 0.55
SIM_WEAK = 0.40

# --- Cross-encoder claim-strength thresholds -------------------------------
# cross-encoder/ms-marco-MiniLM-L-6-v2 outputs an UNBOUNDED LOGIT, not a
# 0-1 probability. Calibrated empirically against this corpus/index (2026-07)
# by running the actual queries and reading off scores:
#   - in-domain probe ("How is age and growth determined in sharks using
#     vertebral analysis?"): 6 distinct papers in the top-8, ce_score range
#     +1.48 to +4.73 — ALL positive.
#   - out-of-domain probe ("CRISPR gene editing protocols for shark
#     embryos" — no such papers in the corpus): top ce_score -1.89, every
#     retrieved chunk negative (-1.89 to -4.32) even though FAISS cosine on
#     the same chunks was still ~0.76-0.80.
# There is a clean sign flip between the two cases at this corpus size, so
# the floor sits at 0.0 (comfortably inside the gap, not at either extreme)
# and CE_STRONG is set low enough (1.0) to count all 6 of the genuinely
# on-topic papers above, not just the single best chunk.
CE_FLOOR = 0.0      # below this, top hit is not meaningfully relevant -> unresolved
CE_STRONG = 1.0      # a hit this strong "counts" as real supporting evidence
CE_MIN_CONCORDANT_PAPERS = 3   # distinct papers >= CE_STRONG for well-supported


def load_index():
    import faiss
    index = faiss.read_index(str(FAISS_INDEX_PATH))
    with open(CHUNKS_JSONL, encoding="utf-8") as f:
        chunks = [json.loads(line) for line in f]
    return index, chunks


def embed_query(question: str) -> np.ndarray:
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(EMBED_MODEL_NAME, device="cpu")
    vec = model.encode(
        [BGE_QUERY_PREFIX + question], normalize_embeddings=True,
        convert_to_numpy=True,
    ).astype("float32")
    return vec


def retrieve(question: str, retrieve_n: int) -> list[dict]:
    """FAISS cosine retrieval of the top retrieve_n candidates (pre-rerank)."""
    index, chunks = load_index()
    qvec = embed_query(question)
    scores, idxs = index.search(qvec, retrieve_n)
    hits = []
    for score, idx in zip(scores[0], idxs[0]):
        if idx < 0:
            continue
        c = dict(chunks[idx])
        c["score"] = float(score)
        hits.append(c)
    return hits


def claim_strength_legacy(hits: list[dict]) -> dict:
    """Old absolute-cosine heuristic — kept only for --no-rerank A/B
    comparison. Documented as over-reporting; do not use for real output.
    """
    by_paper = defaultdict(list)
    for h in hits:
        by_paper[h["literature_id"]].append(h["score"])

    concordant_papers = [
        lit_id for lit_id, scores in by_paper.items()
        if max(scores) >= SIM_CONCORDANT
    ]
    weak_or_better_papers = [
        lit_id for lit_id, scores in by_paper.items()
        if max(scores) >= SIM_WEAK
    ]
    top_score = max((h["score"] for h in hits), default=0.0)

    if len(concordant_papers) >= 3:
        label = "well-supported"
        reason = (f"{len(concordant_papers)} distinct papers retrieved with "
                   f"high similarity (>= {SIM_CONCORDANT}) to the question")
    elif len(concordant_papers) >= 1 or len(weak_or_better_papers) >= 2:
        label = "limited"
        reason = (f"{len(concordant_papers)} strong + "
                   f"{len(weak_or_better_papers) - len(concordant_papers)} "
                   f"moderate independent sources — some relevant evidence "
                   f"but not broad corroboration")
    else:
        label = "unresolved"
        reason = (f"top similarity {top_score:.2f} is below the moderate "
                   f"threshold ({SIM_WEAK}) — the indexed sample likely "
                   f"doesn't cover this question well")

    return {
        "label": label,
        "reason": reason,
        "n_distinct_papers_retrieved": len(by_paper),
        "n_concordant_papers": len(concordant_papers),
        "n_weak_or_better_papers": len(weak_or_better_papers),
        "top_similarity": round(top_score, 3),
    }


def claim_strength(hits: list[dict]) -> dict:
    """Derive a claim-strength label from cross-encoder relevance scores.

    Unlike absolute BGE cosine (which runs high even for topic-adjacent,
    off-topic passages — see docs "Limitations"), the cross-encoder scores
    each (question, chunk) pair directly, so its top score is a much more
    honest signal of whether the corpus actually contains relevant evidence.
    Still a heuristic, not a semantic-agreement/contradiction detector: it
    measures how much retrieved evidence, across how many distinct papers,
    clears a relevance bar — a proxy for "the corpus has on-topic material",
    not for "independent sources agree on the same specific claim".
    """
    if not hits or hits[0].get("ce_score") is None:
        # No cross-encoder scores available (e.g. --no-rerank) — caller
        # should use claim_strength_legacy instead; guard defensively.
        return claim_strength_legacy(hits)

    by_paper = defaultdict(list)
    for h in hits:
        by_paper[h["literature_id"]].append(h["ce_score"])

    concordant_papers = [
        lit_id for lit_id, scores in by_paper.items()
        if max(scores) >= CE_STRONG
    ]
    above_floor_papers = [
        lit_id for lit_id, scores in by_paper.items()
        if max(scores) >= CE_FLOOR
    ]
    top_score = max((h["ce_score"] for h in hits), default=-999.0)

    if top_score < CE_FLOOR:
        label = "unresolved"
        reason = (f"top cross-encoder relevance score {top_score:.2f} is "
                   f"below the floor ({CE_FLOOR}) — nothing retrieved is "
                   f"actually relevant to the question, regardless of "
                   f"cosine similarity; the corpus likely has no evidence "
                   f"on this topic")
    elif len(concordant_papers) >= CE_MIN_CONCORDANT_PAPERS:
        label = "well-supported"
        reason = (f"{len(concordant_papers)} distinct papers with strong "
                   f"cross-encoder relevance (>= {CE_STRONG}) to the "
                   f"question")
    else:
        label = "limited"
        reason = (f"{len(concordant_papers)} strong + "
                   f"{len(above_floor_papers) - len(concordant_papers)} "
                   f"above-floor-but-not-strong independent sources — some "
                   f"relevant evidence but not broad corroboration")

    return {
        "label": label,
        "reason": reason,
        "n_distinct_papers_retrieved": len(by_paper),
        "n_concordant_papers": len(concordant_papers),
        "n_above_floor_papers": len(above_floor_papers),
        "top_ce_score": round(top_score, 3),
    }


def format_citation(hit: dict) -> str:
    authors = (hit.get("authors") or "").split("&")[0].strip().rstrip(",")
    year = hit.get("year")
    try:
        year = int(float(year))
    except (TypeError, ValueError):
        pass
    return f"[{hit['literature_id']}] {authors} et al. {year} — {hit['title']}"


def build_context_block(hits: list[dict], max_chars_per_chunk: int = 900) -> str:
    lines = []
    for h in hits:
        snippet = h["text"][:max_chars_per_chunk]
        score_bit = f"cosine={h['score']:.2f}"
        if h.get("ce_score") is not None:
            score_bit += f", relevance={h['ce_score']:.2f}"
        lines.append(
            f"SOURCE {format_citation(h)} ({score_bit})\n{snippet}\n"
        )
    return "\n---\n".join(lines)


def ollama_available() -> bool:
    try:
        r = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=2)
        return r.status_code == 200
    except requests.RequestException:
        return False


def generate_answer(question: str, hits: list[dict]) -> str:
    context = build_context_block(hits)
    prompt = textwrap.dedent(f"""\
        You are a research assistant answering questions about elasmobranch
        (shark/ray) science using ONLY the sources below. Every factual
        sentence you write must end with the bracketed literature_id
        citation(s) it is based on, e.g. [23522]. Do not cite a source you
        did not use. If the sources do not answer the question, say so
        plainly instead of guessing. Do not invent a confidence/strength
        rating yourself — that is computed separately.

        QUESTION: {question}

        SOURCES:
        {context}

        Write a concise, well-cited answer (3-6 sentences):
        """)
    try:
        r = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=120,
        )
        r.raise_for_status()
        return r.json()["response"].strip()
    except requests.RequestException as e:
        return f"[generation error: {e}]"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("--top-k", type=int, default=8,
                    help="chunks to keep after re-ranking (default 8)")
    ap.add_argument("--retrieve-n", type=int, default=20,
                    help="FAISS candidates pulled before re-ranking (default 20)")
    ap.add_argument("--no-rerank", action="store_true",
                    help="skip the cross-encoder stage (A/B comparison only; "
                         "reinstates the over-reporting absolute-cosine bug)")
    ap.add_argument("--no-generate", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not FAISS_INDEX_PATH.exists():
        sys.exit("No index found — run build_index.py first "
                  "(outputs/rag/index.faiss missing).")

    retrieve_n = max(args.retrieve_n, args.top_k)
    candidates = retrieve(args.question, retrieve_n)

    if args.no_rerank:
        hits = candidates[:args.top_k]
        strength = claim_strength_legacy(hits)
    else:
        hits = cross_encode_rerank(args.question, candidates, args.top_k)
        strength = claim_strength(hits)

    have_llm = (not args.no_generate) and ollama_available()
    if have_llm:
        answer = generate_answer(args.question, hits)
        mode = f"generated (Ollama: {OLLAMA_MODEL})"
    else:
        answer = None
        mode = "stub (no LLM reachable)" if not args.no_generate else "retrieval-only (--no-generate)"

    result = {
        "question": args.question,
        "mode": mode,
        "reranked": not args.no_rerank,
        "answer": answer,
        "claim_strength": strength,
        "retrieved": [
            {
                "literature_id": h["literature_id"],
                "title": h["title"],
                "authors": h["authors"],
                "year": h["year"],
                "cosine_score": round(h["score"], 3),
                "ce_score": round(h["ce_score"], 3) if h.get("ce_score") is not None else None,
                "chunk_index": h["chunk_index"],
                "text_preview": h["text"][:220].replace("\n", " ") + "...",
            }
            for h in hits
        ],
    }

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    def _score_str(h: dict) -> str:
        s = f"cosine={h['score']:.2f}"
        if h.get("ce_score") is not None:
            s += f" relevance={h['ce_score']:.2f}"
        return s

    print(f"\nQ: {args.question}")
    print(f"   [answer mode: {mode}; "
          f"{'cross-encoder re-ranked' if not args.no_rerank else 'NO RERANK (raw cosine order)'}]\n")
    if answer:
        print(answer)
    else:
        print("(No local LLM reachable — showing ranked cited evidence instead of a generated answer.)")
        for h in hits:
            print(f"  - {format_citation(h)}  ({_score_str(h)})")

    print(f"\nClaim strength: {strength['label'].upper()}  — {strength['reason']}")
    if not args.no_rerank:
        print(f"  distinct papers retrieved: {strength['n_distinct_papers_retrieved']}, "
              f"strong (relevance>={CE_STRONG}): {strength['n_concordant_papers']}, "
              f"top relevance score: {strength['top_ce_score']}")
    else:
        print(f"  distinct papers retrieved: {strength['n_distinct_papers_retrieved']}, "
              f"concordant (sim>={SIM_CONCORDANT}): {strength['n_concordant_papers']}, "
              f"top similarity: {strength['top_similarity']}")

    print("\nTop sources:")
    for h in hits[:min(args.top_k, 6)]:
        print(f"  {format_citation(h)}  ({_score_str(h)})")


if __name__ == "__main__":
    main()
