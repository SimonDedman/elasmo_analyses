#!/usr/bin/env python3
"""
Sentence-level entailment check for generated SharkOracle answers.

The old claim-strength badge (query.claim_strength) counts distinct papers whose
chunks clear a cross-encoder RELEVANCE bar: agreement of topic. Two papers with
opposite conclusions both count. This module scores agreement of claim: each
answer sentence is tested (NLI, premise = retrieved chunk, hypothesis = the
sentence) against the chunks it cites, and against the other top hits to catch
contradiction.

Model: cross-encoder/nli-deberta-v3-xsmall (70.8M parameters incl. embeddings,
~270 MB on disk, CPU). Label order is read from the model config (for this
model: 0 contradiction, 1 entailment, 2 neutral). Fallback if it cannot be
loaded: cross-encoder/nli-MiniLM2-L6-H768. `MODEL_USED` records which loaded.

Known weakness (MEASURED 2026-10-07 on hand pairs): the xsmall model can call a
completely unrelated premise a "contradiction" with p~0.99. A contradiction
therefore only counts when the chunk is topically relevant to the sentence:
its cross-encoder relevance score (`ce_score`, when present) must be >= CE_FLOOR
of query.py, and p(contradiction) must reach P_CONTRA.
"""

from __future__ import annotations

import re

MODEL_PRIMARY = "cross-encoder/nli-deberta-v3-xsmall"
MODEL_FALLBACK = "cross-encoder/nli-MiniLM2-L6-H768"
MODEL_USED: str | None = None

MAX_SENTENCES = 8
MAX_CHUNKS = 8
MAX_CHUNK_CHARS = 1500
P_ENTAIL = 0.5      # INFERRED: p(entailment) at or above this counts as entailed
P_CONTRA = 0.95     # INFERRED: strict, xsmall over-calls contradiction (0.81-0.83 false hits on the Q1 probe; 0.948 on a 'growth bands' sentence vs a chunk describing the same banding, full index, 2026-10-07)
MIN_SHARED_TOKENS = 3  # INFERRED: a contradicting chunk must share this many content words with the sentence
CE_FLOOR = 0.0      # same relevance floor as query.CE_FLOOR
MIN_PAPERS_WELL = 3

_model = None
_labels: dict[str, int] = {}

_CITE = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")


def _get_model():
    global _model, MODEL_USED, _labels
    if _model is None:
        from sentence_transformers import CrossEncoder
        last = None
        for name in (MODEL_PRIMARY, MODEL_FALLBACK):
            try:
                _model = CrossEncoder(name, device="cpu")
                MODEL_USED = name
                break
            except Exception as e:  # noqa: BLE001 (offline, missing, etc.)
                last = e
        if _model is None:
            raise RuntimeError(f"no NLI model loadable: {last}")
        id2label = {int(k): v.lower() for k, v in _model.model.config.id2label.items()}
        _labels = {v: k for k, v in id2label.items()}
    return _model


_AUTHOR_YEAR = re.compile(
    r"\b([A-Z][\w'\-]+)(?:\s+et\s+al\.?|\s+(?:and|&)\s+[A-Z][\w'\-]+)?,?\s+\(?((?:1[6-9]|20)\d\d)[a-z]?\)?"
)


def _first_surname(authors) -> str:
    first = re.split(r"[;,]| and | & ", str(authors or ""))[0]
    toks = re.findall(r"[A-Za-z][\w'\-]+", first)
    return toks[0].lower() if toks else ""


def normalise_citations(answer: str, hits: list[dict]) -> str:
    """Small local models cite "Casey et al., 1985" instead of the [id] the
    system prompt asks for. When such a mention names exactly one retrieved
    paper (first-author surname + year), append its [id] so the citation is
    machine-checkable; otherwise leave the text alone."""
    by_key: dict[tuple[str, int], set[str]] = {}
    for h in hits:
        try:
            yr = int(float(h.get("year")))
        except (TypeError, ValueError):
            continue
        by_key.setdefault((_first_surname(h.get("authors")), yr), set()).add(str(h["literature_id"]))

    def repl(m):
        ids = by_key.get((m.group(1).lower(), int(m.group(2))))
        if ids and len(ids) == 1:
            lid = next(iter(ids))
            tail = answer[m.end():m.end() + 12]
            if f"[{lid}" in tail:
                return m.group(0)
            return f"{m.group(0)} [{lid}]"
        return m.group(0)

    return _AUTHOR_YEAR.sub(repl, answer) if hits else answer


def split_sentences(answer: str) -> list[dict]:
    """Split an answer into sentences, each with its [id] / [id, id] citations.

    A sentence ends at . ! ? followed by whitespace, or after a citation block
    that follows the full stop ("... sharks. [12]" stays with its sentence).
    Returns [{"text", "citations": [int, ...]}]; text keeps its citations.
    """
    if not answer:
        return []
    out = []
    for para in re.split(r"\n+", answer):
        para = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s+", "", para).strip()
        if not para:
            continue
        # protect "et al." and "e.g." style abbreviations from the sentence break
        prot = re.sub(r"\b(et al|e\.g|i\.e|vs|approx|ca|spp|sp|cf)\.",
                      lambda m: m.group(1) + "\u0000", para)
        # a sentence ends at . ! ? plus any citation block that follows it
        pieces, pos = [], 0
        for m in re.finditer(r"[.!?](?:\s*\[[\d\s,]+\])*(?=\s|$)", prot):
            pieces.append(prot[pos:m.end()])
            pos = m.end()
        if prot[pos:].strip():
            pieces.append(prot[pos:])
        for p in pieces:
            text = p.replace("\u0000", ".").strip()
            if not text:
                continue
            ids = []
            for m in _CITE.finditer(text):
                for i in re.split(r"\s*,\s*", m.group(1)):
                    if int(i) not in ids:
                        ids.append(int(i))
            out.append({"text": text, "citations": ids})
    return out


def _bare(text: str) -> str:
    """Sentence text without its citation markers, for use as the hypothesis."""
    return re.sub(r"\s*\[[\d\s,]+\]", "", text).strip()


_STOP = frozenset("the a an of in on to and or is are was were be by for with as at from that this these those it its their which can may not no than then also such into more most used use using".split())


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z]{3,}", text.lower()) if t not in _STOP}


def _nli(pairs: list[tuple[str, str]]):
    """Softmax probabilities per pair as dicts {contradiction, entailment, neutral}."""
    model = _get_model()
    probs = model.predict(pairs, apply_softmax=True, batch_size=16, show_progress_bar=False)
    return [{lab: float(p[idx]) for lab, idx in _labels.items()} for p in probs]


def score_sentences(sentences: list[dict], hits: list[dict]) -> list[dict]:
    """Add NLI judgement to each sentence (at most MAX_SENTENCES x MAX_CHUNKS pairs).

    Per sentence: support in {entailed, neutral, contradicted, uncited},
    best_support_id, contradicted_by (ids), and `pairs` with the raw
    probabilities per (chunk) tested. Sentences without citations are
    `uncited`, but are still checked against the other hits for contradiction,
    which overrides to `contradicted`.
    """
    hits = hits[:MAX_CHUNKS]
    sents = sentences[:MAX_SENTENCES]
    jobs, meta = [], []
    for si, s in enumerate(sents):
        hyp = _bare(s["text"])
        for h in hits:
            jobs.append((h["text"][:MAX_CHUNK_CHARS], hyp))
            meta.append((si, h))
    probs = _nli(jobs) if jobs else []

    per = [[] for _ in sents]
    for (si, h), p, (prem, hyp) in zip(meta, probs, jobs):
        shared = len(_tokens(prem) & _tokens(hyp))
        per[si].append({"literature_id": h["literature_id"], "shared_tokens": shared,
                        "cited": h["literature_id"] in set(sents[si]["citations"]),
                        "relevant": h.get("ce_score") is None or h["ce_score"] >= CE_FLOOR,
                        **{k: round(v, 4) for k, v in p.items()}})

    results = []
    for s, plist in zip(sents, per):
        cited = [p for p in plist if p["cited"]]
        ent = [p for p in cited if p.get("entailment", 0) >= P_ENTAIL]
        best = max(cited, key=lambda p: p.get("entailment", 0), default=None)
        contra = sorted({p["literature_id"] for p in plist
                         if p["relevant"] and p["shared_tokens"] >= MIN_SHARED_TOKENS
                         and p.get("contradiction", 0) >= P_CONTRA
                         and p.get("entailment", 0) < P_ENTAIL})
        # entailing paper ids from ANY retrieved chunk (corroboration beyond citations)
        entail_ids = sorted({p["literature_id"] for p in plist
                             if p.get("entailment", 0) >= P_ENTAIL})
        attributed = False
        # "contested" means two retrieved sources disagree about the claim: one must
        # entail the sentence as well. A contradiction with no support anywhere is a
        # sentence the corpus does not back, which is "neutral", not a dispute.
        if contra and not entail_ids:
            contra = []
        if contra:
            support = "contradicted"
        elif ent:
            support = "entailed"
        elif entail_ids:
            # no cited chunk entails it (or it carries no citation), but a
            # retrieved chunk does: the claim is grounded, the citation is not
            support, attributed = "entailed", True
            best = max(plist, key=lambda p: p.get("entailment", 0))
        elif not s["citations"]:
            support = "uncited"
        else:
            support = "neutral"
        results.append({
            "text": s["text"], "citations": s["citations"], "support": support,
            "attributed": attributed,
            "best_support_id": best["literature_id"] if best and best.get("entailment", 0) >= P_ENTAIL else None,
            "contradicted_by": contra,
            "entailed_by": entail_ids,
            "pairs": plist,
        })
    for s in sentences[MAX_SENTENCES:]:
        results.append({"text": s["text"], "citations": s["citations"],
                        "support": "uncited" if not s["citations"] else "neutral",
                        "best_support_id": None, "contradicted_by": [],
                        "entailed_by": [], "pairs": [], "not_scored": True})
    return results


def claim_strength_entailment(sentence_scores: list[dict], hits: list[dict]) -> dict:
    """Claim-level rating from per-sentence NLI results.

    contested       any sentence is contradicted by a relevant retrieved chunk
    well-supported  >= 3 distinct papers entail at least one sentence, no contradiction
    limited         at least one entailed sentence, otherwise
    unresolved      no entailed sentence
    """
    scored = [s for s in sentence_scores if not s.get("not_scored")]
    cited = [s for s in scored if s["citations"]]
    entailed_cited = [s for s in cited if s["support"] == "entailed"]
    groundedness = round(len(entailed_cited) / len(cited), 3) if cited else 0.0
    papers = sorted({i for s in scored if s["support"] in ("entailed", "contradicted")
                     for i in s["entailed_by"]})
    contested = [s for s in scored if s["support"] == "contradicted"]

    base = {"groundedness": groundedness, "n_entailing_papers": len(papers),
            "entailing_papers": papers, "n_sentences": len(scored),
            "n_cited_sentences": len(cited),
            "nli_model": MODEL_USED, "basis": "entailment"}
    if contested:
        sides = [{"sentence": s["text"], "supported_by": s["entailed_by"],
                  "contradicted_by": s["contradicted_by"]} for s in contested]
        first = contested[0]
        reason = (f"{len(contested)} answer sentence(s) contradicted by retrieved text: "
                  f"papers {', '.join(map(str, first['contradicted_by']))} contradict a claim "
                  f"that {', '.join(map(str, first['entailed_by'])) or 'the answer'} "
                  f"{'supports' if first['entailed_by'] else 'makes'}")
        return {"label": "contested", "reason": reason, "contested": sides, **base}
    if not papers:
        return {"label": "unresolved",
                "reason": ("no retrieved chunk entails any sentence of the answer "
                           f"({len(cited)} cited sentence(s) checked)"), **base}
    if len(papers) >= MIN_PAPERS_WELL:
        return {"label": "well-supported",
                "reason": (f"{len(papers)} distinct papers each entail an answer sentence; "
                           f"{len(entailed_cited)}/{len(cited)} cited sentences entailed; "
                           "no contradiction"), **base}
    return {"label": "limited",
            "reason": (f"{len(papers)} paper(s) entail an answer sentence; "
                       f"{len(entailed_cited)}/{len(cited)} cited sentences entailed"), **base}


def assess(answer: str, hits: list[dict]) -> tuple[list[dict], dict]:
    """Convenience: split, score, rate. Returns (sentences, claim_strength)."""
    scores = score_sentences(split_sentences(normalise_citations(answer, hits)), hits)
    return scores, claim_strength_entailment(scores, hits)


def rate_answer(answer: str | None, hits: list[dict], topic_strength: dict) -> dict:
    """Shared by query.py and serve.py. Returns the three result fields:
    claim_strength (entailment-based, or the topic rating when no usable answer),
    claim_strength_topic (the old cross-encoder rating, unchanged), sentences.
    """
    topic = dict(topic_strength)
    if not answer or answer.startswith("[generation error"):
        fb = dict(topic)
        fb["basis"] = "topic"
        fb["reason"] = ("no generated answer, so this is the topic rating "
                        "(papers retrieved on topic), not claim agreement: "
                        + str(topic.get("reason", "")))
        return {"claim_strength": fb, "claim_strength_topic": topic, "sentences": []}
    try:
        sentences, strength = assess(answer, hits)
    except Exception as err:  # noqa: BLE001 (model unavailable: degrade, say so)
        fb = dict(topic)
        fb["basis"] = "topic"
        fb["reason"] = f"entailment check failed ({err}); topic rating shown: " + str(topic.get("reason", ""))
        return {"claim_strength": fb, "claim_strength_topic": topic, "sentences": []}
    slim = [{k: v for k, v in s.items() if k != "pairs"}
            | {"probs": [{"id": p["literature_id"], "e": p["entailment"], "c": p["contradiction"]}
                         for p in s["pairs"] if p["cited"] or p["literature_id"] in s["contradicted_by"]]}
            for s in sentences]
    return {"claim_strength": strength, "claim_strength_topic": topic, "sentences": slim}
