#!/usr/bin/env python3
"""
Query the RAG prototype index built by build_index.py.

Run with the fashion-clip venv (has sentence-transformers/faiss):

    /home/simon/.venvs/fashion-clip/bin/python scripts/rag/query.py \
        "What techniques are used for age determination in deep-sea sharks?"

Flags:
    --top-k N        number of chunks to retrieve (default 8)
    --no-generate    skip the LLM call, print the ranked cited context only
    --json           print machine-readable JSON instead of formatted text

Pipeline: embed question (BGE query prefix) -> FAISS cosine retrieval over
outputs/rag/index.faiss -> build a cited context block -> (if Ollama is
reachable) generate an answer instructed to cite [literature_id] inline ->
compute a claim-strength rating from retrieval agreement, independent of
whatever the LLM says (LLMs are not a trustworthy source of their own
confidence, so this is scored programmatically from the retrieved evidence).
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

# Claim-strength thresholds on cosine similarity (BGE-small, normalized
# embeddings -> inner product == cosine, range roughly 0.3-0.9 in practice
# for this corpus). These are heuristic cut-offs calibrated by eyeballing
# retrieval scores during prototyping, not a validated statistical model —
# see docs/LLM/rag_prototype_status.md "Limitations".
SIM_CONCORDANT = 0.55   # a hit this strong "counts" as real supporting evidence
SIM_WEAK = 0.40         # below this, a hit is noise, not evidence


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


def retrieve(question: str, top_k: int) -> list[dict]:
    index, chunks = load_index()
    qvec = embed_query(question)
    scores, idxs = index.search(qvec, top_k)
    hits = []
    for score, idx in zip(scores[0], idxs[0]):
        if idx < 0:
            continue
        c = dict(chunks[idx])
        c["score"] = float(score)
        hits.append(c)
    return hits


def claim_strength(hits: list[dict]) -> dict:
    """Derive a claim-strength label from retrieval agreement.

    Heuristic, not a semantic-agreement/contradiction detector: it only
    measures how much of the retrieved evidence, across how many distinct
    papers, sits above a similarity bar — a proxy for "multiple independent
    sources say something relevant to this question", not for "multiple
    sources agree on the same claim". See docs for caveats.
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
        lines.append(
            f"SOURCE {format_citation(h)} (similarity={h['score']:.2f})\n{snippet}\n"
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
    ap.add_argument("--top-k", type=int, default=8)
    ap.add_argument("--no-generate", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not FAISS_INDEX_PATH.exists():
        sys.exit("No index found — run build_index.py first "
                  "(outputs/rag/index.faiss missing).")

    hits = retrieve(args.question, args.top_k)
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
        "answer": answer,
        "claim_strength": strength,
        "retrieved": [
            {
                "literature_id": h["literature_id"],
                "title": h["title"],
                "authors": h["authors"],
                "year": h["year"],
                "score": round(h["score"], 3),
                "chunk_index": h["chunk_index"],
                "text_preview": h["text"][:220].replace("\n", " ") + "...",
            }
            for h in hits
        ],
    }

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    print(f"\nQ: {args.question}")
    print(f"   [answer mode: {mode}]\n")
    if answer:
        print(answer)
    else:
        print("(No local LLM reachable — showing ranked cited evidence instead of a generated answer.)")
        for h in hits:
            print(f"  - {format_citation(h)}  (sim={h['score']:.2f})")

    print(f"\nClaim strength: {strength['label'].upper()}  — {strength['reason']}")
    print(f"  distinct papers retrieved: {strength['n_distinct_papers_retrieved']}, "
          f"concordant (sim>={SIM_CONCORDANT}): {strength['n_concordant_papers']}, "
          f"top similarity: {strength['top_similarity']}")

    print("\nTop sources:")
    for h in hits[:min(args.top_k, 6)]:
        print(f"  {format_citation(h)}  (sim={h['score']:.2f})")


if __name__ == "__main__":
    main()
