#!/usr/bin/env python3
"""
Retrieval evaluation harness for the SharkOracle query interface (phase 2 of
docs/superpowers/specs/2026-08-06-retrieval-evaluation-design.md).

Runs every question in scripts/rag/eval/questions.jsonl through named
retrieval configurations, IN-PROCESS (it loads the FAISS index, the BGE
embedder and the cross-encoder itself; it never calls the server), dedupes the
ranked chunks to papers, and writes per-category metrics.

    /home/simon/.venvs/fashion-clip/bin/python scripts/rag/eval/run_eval.py \
        --index-dir outputs/rag_test --limit 5          # smoke run
    /home/simon/.venvs/fashion-clip/bin/python scripts/rag/eval/run_eval.py \
        --index-dir outputs/rag --fts-db <path>/fts.sqlite   # baseline

Configs
  vector     FAISS top-20 chunks, cosine order (no rerank).
  vector_ce  FAISS top-30 chunks, cross-encoder rerank, interface shows top-10.
  hybrid_ce  FAISS + BM25 (reciprocal rank fusion, scripts/rag/hybrid.py)
             top-30, cross-encoder rerank, top-10 shown. Only run when
             hybrid.py imports and an fts.sqlite is available.

Paper ranking = the configuration's full ranked chunk list deduplicated to
papers, first occurrence wins. For the CE configs that is all 30 reranked
chunks, so hit@20 is measurable; `hit@shown` is whether a relevant paper
appears among the chunks the interface actually displays (top 10).

Relevance: `relevant_ids` (gain 1) and optional `partial_ids` (gain 0.5, used
only in nDCG). hit/P/R/MRR are strict (relevant_ids only). Questions with no
relevant_ids are excluded from the retrieval metrics and counted as unjudged.

Duplicate-aware scoring: the live index (outputs/rag, Sept 2026) holds
literature_ids whose text is identical to another id's. Duplicates are found
by hashing each id's indexed chunk text (plus ids sharing a source PDF SHA-1
in outputs/validation/fable_texts_manifest.csv); a retrieved duplicate of a
relevant id is credited in the `_dupaware` variant of each metric.

Outputs (in --out-dir, default outputs/rag_eval):
  <date>_<index-name>_<config>.json   per-question rankings + metrics
  <date>_report.md                    tables for every config run that day
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import os
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAG_DIR = HERE.parent
PROJECT_ROOT = RAG_DIR.parents[1]
DEFAULT_QUESTIONS = HERE / "questions.jsonl"
DEFAULT_OUT = PROJECT_ROOT / "outputs" / "rag_eval"
MANIFEST = PROJECT_ROOT / "outputs" / "validation" / "fable_texts_manifest.csv"

KS = (1, 5, 10, 20)
CATEGORIES = ("known_answer", "exact_term", "assessor", "unanswerable")

CONFIGS = {
    "vector":    {"retrieve_n": 20, "rerank": False, "hybrid": False, "shown": 20},
    "vector_ce": {"retrieve_n": 30, "rerank": True,  "hybrid": False, "shown": 10},
    "hybrid_ce": {"retrieve_n": 30, "rerank": True,  "hybrid": True,  "shown": 10},
}
SERVER_TOP_K = 8   # serve.py QueryBody.top_k default: what the badge is computed on


# ---------------------------------------------------------------------------
# Pure helpers (unit-tested in tests/test_rag_eval.py)
# ---------------------------------------------------------------------------

def clean_id(s) -> str:
    s = str(s)
    return s[:-2] if s.endswith(".0") else s


def dedupe_to_papers(hits: list[dict]) -> list[dict]:
    """Ranked chunks -> ranked papers (first occurrence wins), keeping the
    chunk rank and the best scores seen for each paper."""
    out: dict[str, dict] = {}
    for rank, h in enumerate(hits, start=1):
        lid = clean_id(h["literature_id"])
        p = out.get(lid)
        if p is None:
            out[lid] = p = {"literature_id": lid, "first_chunk_rank": rank,
                            "cosine": h.get("score"), "ce": h.get("ce_score"),
                            "n_chunks": 0}
        p["n_chunks"] += 1
        if h.get("score") is not None and (p["cosine"] is None or h["score"] > p["cosine"]):
            p["cosine"] = h["score"]
        if h.get("ce_score") is not None and (p["ce"] is None or h["ce_score"] > p["ce"]):
            p["ce"] = h["ce_score"]
    return list(out.values())


def expand_dups(ids: set[str], dup_groups: dict[str, set[str]] | None) -> set[str]:
    if not dup_groups:
        return set(ids)
    out = set(ids)
    for i in ids:
        out |= dup_groups.get(i, set())
    return out


def question_metrics(ranked: list[str], relevant: set[str],
                     partial: set[str] | None = None,
                     shown: set[str] | None = None) -> dict:
    """Binary-strict hit@k, P@10, R@10, MRR; graded nDCG@10 (partial = 0.5)."""
    partial = (partial or set()) - relevant
    m: dict[str, float] = {}
    for k in KS:
        m[f"hit@{k}"] = float(any(r in relevant for r in ranked[:k]))
    top10 = ranked[:10]
    n_rel10 = sum(1 for r in top10 if r in relevant)
    m["P@10"] = n_rel10 / 10.0
    m["R@10"] = n_rel10 / len(relevant) if relevant else 0.0
    rr = 0.0
    for i, r in enumerate(ranked, start=1):
        if r in relevant:
            rr = 1.0 / i
            break
    m["MRR"] = rr

    def gain(r):
        return 1.0 if r in relevant else (0.5 if r in partial else 0.0)

    dcg = sum(gain(r) / math.log2(i + 1) for i, r in enumerate(top10, start=1))
    ideal = sorted([1.0] * len(relevant) + [0.5] * len(partial), reverse=True)[:10]
    idcg = sum(g / math.log2(i + 1) for i, g in enumerate(ideal, start=1))
    m["nDCG@10"] = dcg / idcg if idcg else 0.0
    if shown is not None:
        m["hit@shown"] = float(bool(relevant & shown))
    return m


METRIC_KEYS = [f"hit@{k}" for k in KS] + ["hit@shown", "P@10", "R@10", "nDCG@10", "MRR"]


def aggregate(rows: list[dict], key: str = "metrics") -> dict:
    vals = defaultdict(list)
    for r in rows:
        for k, v in (r.get(key) or {}).items():
            vals[k].append(v)
    return {k: (sum(v) / len(v) if v else None) for k, v in vals.items()}


def load_dup_groups(manifest: Path = MANIFEST) -> dict[str, set[str]]:
    """literature_id -> other ids whose text came from the same PDF (SHA-1)."""
    by_sha: dict[str, set[str]] = defaultdict(set)
    if not manifest.exists():
        return {}
    with open(manifest, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r.get("sha"):
                by_sha[r["sha"]].add(clean_id(r["lit_id"]))
    out: dict[str, set[str]] = {}
    for ids in by_sha.values():
        if len(ids) > 1:
            for i in ids:
                out[i] = ids - {i}
    return out


def dup_groups_from_text(text_sha: dict[str, str]) -> dict[str, set[str]]:
    """literature_id -> other ids whose indexed text is byte-identical."""
    by_sha: dict[str, set[str]] = defaultdict(set)
    for lid, sha in text_sha.items():
        by_sha[sha].add(lid)
    out: dict[str, set[str]] = {}
    for ids in by_sha.values():
        if len(ids) > 1:
            for i in ids:
                out[i] = ids - {i}
    return out


def merge_groups(*groups: dict[str, set[str]]) -> dict[str, set[str]]:
    out: dict[str, set[str]] = defaultdict(set)
    for g in groups:
        for k, v in g.items():
            out[k] |= v
    return dict(out)


def load_questions(path: Path) -> list[dict]:
    qs = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                qs.append(json.loads(line))
    return qs


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

class Engine:
    """Holds the index, chunks, embedder and (lazily) the cross-encoder."""

    def __init__(self, index_dir: Path, fts_db: Path | None):
        os.environ["RAG_OUT_DIR"] = str(index_dir)
        sys.path.insert(0, str(RAG_DIR))
        import faiss
        from sentence_transformers import SentenceTransformer
        import common
        self.common = common
        t0 = time.time()
        self.index = faiss.read_index(str(index_dir / "index.faiss"))
        keep = ("literature_id", "chunk_index", "title", "year", "journal", "text")
        self.chunks = []
        with open(index_dir / "chunks_meta.jsonl", encoding="utf-8") as f:
            for line in f:
                c = json.loads(line)
                self.chunks.append({k: c.get(k) for k in keep})
        self.meta = {}
        hashers: dict[str, "hashlib._Hash"] = {}
        for c in self.chunks:
            lid = clean_id(c["literature_id"])
            hashers.setdefault(lid, hashlib.sha1()).update((c.get("text") or "").encode("utf-8", "ignore"))
        # literature_id -> sha1 of its indexed text: the index's own duplicate instrument
        self.text_sha = {lid: h.hexdigest() for lid, h in hashers.items()}
        for c in self.chunks:
            self.meta.setdefault(clean_id(c["literature_id"]),
                                 (c.get("title"), c.get("year"), c.get("journal")))
        self.embedder = SentenceTransformer(common.EMBED_MODEL_NAME, device="cpu")
        self.load_seconds = round(time.time() - t0, 1)
        self.fts_db = fts_db if (fts_db and Path(fts_db).exists()) else None
        self.hybrid_ok = False
        if self.fts_db is not None:
            try:
                import hybrid  # noqa: F401
                from retrieval import search_hybrid  # noqa: F401
                self.hybrid_ok = True
            except Exception as e:  # noqa: BLE001
                print(f"[eval] hybrid unavailable: {e}")

    def title_of(self, lid: str):
        return (self.meta.get(lid) or (None,))[0]

    def retrieve(self, question: str, cfg: dict) -> list[dict]:
        from retrieval import search_preloaded
        if cfg["hybrid"]:
            from retrieval import search_hybrid
            return search_hybrid(self.index, self.chunks, self.embedder, question,
                                 cfg["retrieve_n"], None,
                                 self.common.BGE_QUERY_PREFIX, self.fts_db)
        return search_preloaded(self.index, self.chunks, self.embedder, question,
                                cfg["retrieve_n"], None,
                                self.common.BGE_QUERY_PREFIX)


def run_config(engine: Engine, name: str, questions: list[dict],
               dup_groups: dict[str, set[str]], indexed_ids: set[str]) -> dict:
    from rerank import rerank
    import query as q
    cfg = CONFIGS[name]
    per_q = []
    t0 = time.time()
    for qq in questions:
        hits = engine.retrieve(qq["question"], cfg)
        if cfg["rerank"]:
            hits = rerank(qq["question"], hits, len(hits))   # sort all, keep all
            badge = q.claim_strength(hits[:SERVER_TOP_K])
            badge10 = q.claim_strength(hits[:cfg["shown"]])
        else:
            badge = q.claim_strength_legacy(hits[:SERVER_TOP_K])
            badge10 = q.claim_strength_legacy(hits[:cfg["shown"]])
        papers = dedupe_to_papers(hits)
        ranked = [p["literature_id"] for p in papers]
        shown = {clean_id(h["literature_id"]) for h in hits[:cfg["shown"]]}
        rel = {clean_id(x) for x in qq.get("relevant_ids") or []}
        part = {clean_id(x) for x in qq.get("partial_ids") or []}
        row = {
            "id": qq["id"], "category": qq["category"], "question": qq["question"],
            "status": qq.get("status"),
            "n_relevant": len(rel),
            "n_relevant_indexed": len(rel & indexed_ids),
            "badge_top8": badge["label"], "badge_top10": badge10["label"],
            "top_ce": badge.get("top_ce_score"),
            "ranked_papers": [{**p, "title": engine.title_of(p["literature_id"])}
                              for p in papers],
            "metrics": None, "metrics_dupaware": None,
        }
        if rel:
            row["metrics"] = question_metrics(ranked, rel, part, shown)
            rel_d = expand_dups(rel, dup_groups)
            row["metrics_dupaware"] = question_metrics(
                ranked, rel_d, expand_dups(part, dup_groups) - rel_d, shown)
        per_q.append(row)
    secs = time.time() - t0

    by_cat = {}
    for cat in CATEGORIES:
        rows = [r for r in per_q if r["category"] == cat]
        judged = [r for r in rows if r["metrics"] is not None]
        judged_idx = [r for r in judged if r["n_relevant_indexed"] > 0]
        badges = Counter(r["badge_top8"] for r in rows)
        by_cat[cat] = {
            "n_questions": len(rows),
            "n_judged": len(judged),
            "n_judged_with_relevant_indexed": len(judged_idx),
            "metrics": aggregate(judged_idx) if judged_idx else None,
            "metrics_dupaware": aggregate(judged_idx, "metrics_dupaware") if judged_idx else None,
            "badge_top8": dict(badges),
            "frac_unresolved_top8": (badges.get("unresolved", 0) / len(rows)) if rows else None,
            "frac_unresolved_top10": (sum(r["badge_top10"] == "unresolved" for r in rows) / len(rows)) if rows else None,
        }
    return {"config": name, "config_params": cfg, "server_top_k_for_badge": SERVER_TOP_K,
            "seconds": round(secs, 1), "by_category": by_cat, "questions": per_q}


def file_sha(p: Path) -> str | None:
    try:
        return hashlib.sha1(p.read_bytes()).hexdigest()[:12]
    except OSError:
        return None


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _fmt(v):
    return "n/a" if v is None else f"{v:.2f}"


def write_report(out_dir: Path, date: str, results: list[dict], meta: dict) -> Path:
    path = out_dir / f"{date}_report.md"
    L = []
    L.append(f"# Retrieval evaluation report, {date} (SILVER)")
    L.append("")
    L.append("Every relevance label behind these numbers is **silver**: questions and "
             "`relevant_ids` were written by Claude from the papers' abstracts and the "
             "text cache, not yet adjudicated by Simon or a co-author. Treat every figure "
             "as indicative until the adjudication workbook has been applied "
             "(`scripts/rag/eval/apply_adjudication.py`) and this harness re-run.")
    L.append("")
    L.append("## Set-up")
    L.append("")
    L.append(f"- Index: `{meta['index_dir']}` ({meta['index_name']}); build_status: "
             f"{meta['build_status'].get('papers_indexed', '?'):,} papers / "
             f"{meta['build_status'].get('chunks_indexed', '?'):,} chunks, complete="
             f"{meta['build_status'].get('complete')}.")
    if meta.get("duplicate_note"):
        L.append(f"- {meta['duplicate_note']}")
    L.append(f"- Questions: `{meta['questions_path']}` ({meta['n_questions']} run; "
             f"by category {meta['by_category_counts']}); sha1 {meta['questions_sha']}.")
    L.append("- Embedder BAAI/bge-small-en-v1.5 (CPU, query prefix); cross-encoder "
             "cross-encoder/ms-marco-MiniLM-L-6-v2 (CPU).")
    L.append(f"- FTS sidecar for hybrid: `{meta.get('fts_db')}`; hybrid.py sha1 {meta.get('hybrid_sha')}.")
    L.append(f"- Index load {meta['load_seconds']} s. Claim-strength badge computed on the top "
             f"{SERVER_TOP_K} reranked chunks (serve.py default `top_k`), and on the top 10 for comparison.")
    L.append("")
    L.append("| config | retrieve_n | rerank | hybrid | chunks shown | run time (s) |")
    L.append("|---|---|---|---|---|---|")
    for r in results:
        c = r["config_params"]
        L.append(f"| {r['config']} | {c['retrieve_n']} | {c['rerank']} | {c['hybrid']} | {c['shown']} | {r['seconds']} |")
    L.append("")
    L.append("Paper ranking = the config's ranked chunk list deduplicated to papers. "
             "hit@k, P@10, R@10 and MRR are strict (relevant_ids only); nDCG@10 gives partial_ids gain 0.5. "
             "`hit@shown` = a relevant paper is among the chunks the interface displays. "
             "Means are over questions that have at least one relevant paper present in the index.")
    L.append("")
    for cat in ("known_answer", "exact_term"):
        L.append(f"## {cat}")
        L.append("")
        any_r = results[0]["by_category"][cat]
        L.append(f"{any_r['n_questions']} questions, {any_r['n_judged']} with relevant_ids, "
                 f"{any_r['n_judged_with_relevant_indexed']} with a relevant paper in this index.")
        L.append("")
        for variant, label in (("metrics", "strict"), ("metrics_dupaware", "duplicate-aware")):
            L.append(f"**{label}**")
            L.append("")
            L.append("| config | " + " | ".join(METRIC_KEYS) + " |")
            L.append("|---|" + "---|" * len(METRIC_KEYS))
            for r in results:
                m = r["by_category"][cat][variant] or {}
                L.append(f"| {r['config']} | " + " | ".join(_fmt(m.get(k)) for k in METRIC_KEYS) + " |")
            L.append("")
    L.append("## Claim-strength badge by category")
    L.append("")
    L.append("Fraction of questions whose badge is `unresolved` (top-8 / top-10 reranked chunks), and the "
             "top-8 label counts. For unanswerable questions `unresolved` is the correct behaviour; "
             "for the vector config the badge is the legacy cosine heuristic.")
    L.append("")
    L.append("| config | category | n | unresolved top-8 | unresolved top-10 | labels (top-8) |")
    L.append("|---|---|---|---|---|---|")
    for r in results:
        for cat in CATEGORIES:
            b = r["by_category"][cat]
            if not b["n_questions"]:
                continue
            L.append(f"| {r['config']} | {cat} | {b['n_questions']} | {_fmt(b['frac_unresolved_top8'])} | "
                     f"{_fmt(b['frac_unresolved_top10'])} | {b['badge_top8']} |")
    L.append("")
    L.append("## Misses (known_answer / exact_term, strict, relevant paper indexed but not in the ranked list)")
    L.append("")
    for r in results:
        miss = [x for x in r["questions"] if x["metrics"] and x["n_relevant_indexed"]
                and x["metrics"]["hit@20"] == 0]
        L.append(f"- {r['config']}: {len(miss)} — " + (", ".join(x["id"] for x in miss) or "none"))
    L.append("")
    L.append("## Limitations")
    L.append("")
    L.append(meta["limitations"])
    L.append("")
    path.write_text("\n".join(L), encoding="utf-8")
    return path


LIMITATIONS = (
    "The questions were written by the system builder's assistant (Claude), not by "
    "independent assessors, so they are likely to be shaped by what the corpus contains "
    "and by the abstract wording; the spec's independence concern is not yet met. "
    "Known-answer questions have one relevant paper by construction, so P@10 is capped at "
    "0.1 for them and R@10 equals hit@10; other relevant papers in the corpus are "
    "counted as misses until adjudication adds them. Exact-term relevant sets are every "
    "indexed paper whose body text contains the term (capped at 10 per question, total "
    "noted in provenance), which rewards matching the term rather than answering a "
    "question. Assessor and unanswerable questions carry no relevance labels yet, so they "
    "contribute only badge statistics. With 30 and 20 questions per scored category, a "
    "single question moves a hit rate by 3 to 5 percentage points: differences between "
    "configs smaller than about 10 points are not distinguishable from noise. All labels "
    "are silver."
)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--index-dir", default=os.environ.get("RAG_OUT_DIR") or str(PROJECT_ROOT / "outputs" / "rag"))
    ap.add_argument("--questions", default=str(DEFAULT_QUESTIONS))
    ap.add_argument("--configs", default="auto",
                    help="comma list from vector,vector_ce,hybrid_ce; 'auto' = all available")
    ap.add_argument("--fts-db", default=None,
                    help="FTS5 sidecar for hybrid_ce (default <index-dir>/fts.sqlite)")
    ap.add_argument("--limit", type=int, default=None, help="first N questions only (smoke runs)")
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT))
    ap.add_argument("--date", default=dt.date.today().isoformat())
    args = ap.parse_args()

    index_dir = Path(args.index_dir).resolve()
    out_dir = Path(args.out_dir).resolve()
    if index_dir.name == "rag.new":
        sys.exit("refusing to read outputs/rag.new (a rebuild may be in progress)")
    out_dir.mkdir(parents=True, exist_ok=True)

    questions = [q for q in load_questions(Path(args.questions)) if q.get("status") != "dropped"]
    if args.limit:
        questions = questions[:args.limit]
    fts = Path(args.fts_db) if args.fts_db else index_dir / "fts.sqlite"

    print(f"[eval] loading {index_dir} ...", flush=True)
    engine = Engine(index_dir, fts)
    indexed_ids = set(engine.meta)
    print(f"[eval] loaded {len(engine.chunks):,} chunks / {len(indexed_ids):,} papers "
          f"in {engine.load_seconds}s; hybrid available={engine.hybrid_ok}", flush=True)

    if args.configs == "auto":
        names = ["vector", "vector_ce"] + (["hybrid_ce"] if engine.hybrid_ok else [])
    else:
        names = [n.strip() for n in args.configs.split(",") if n.strip()]
        if "hybrid_ce" in names and not engine.hybrid_ok:
            sys.exit("hybrid_ce requested but no usable fts.sqlite / hybrid.py")

    text_groups = dup_groups_from_text(engine.text_sha)
    pdf_groups = load_dup_groups()
    dup_groups = merge_groups(text_groups, pdf_groups)
    n_dup_ids = sum(1 for i in indexed_ids if i in dup_groups)
    n_text_dup = len(text_groups)
    n_text_groups = len({frozenset(v | {k}) for k, v in text_groups.items()})
    bs_path = index_dir / "build_status.json"
    build_status = json.loads(bs_path.read_text()) if bs_path.exists() else {}
    index_name = index_dir.name

    results = []
    for name in names:
        print(f"[eval] running {name} over {len(questions)} questions ...", flush=True)
        res = run_config(engine, name, questions, dup_groups, indexed_ids)
        res.update({"date": args.date, "index_dir": str(index_dir), "index_name": index_name,
                    "build_status": build_status, "label_status": "silver",
                    "questions_path": str(args.questions),
                    "questions_sha": file_sha(Path(args.questions)),
                    "limit": args.limit})
        p = out_dir / f"{args.date}_{index_name}_{name}.json"
        p.write_text(json.dumps(res, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
        print(f"[eval] {name}: {res['seconds']}s -> {p}", flush=True)
        results.append(res)

    meta = {
        "index_dir": str(index_dir), "index_name": index_name, "build_status": build_status,
        "questions_path": str(args.questions), "questions_sha": file_sha(Path(args.questions)),
        "n_questions": len(questions),
        "by_category_counts": dict(Counter(q["category"] for q in questions)),
        "fts_db": str(engine.fts_db) if engine.fts_db else None,
        "hybrid_sha": file_sha(RAG_DIR / "hybrid.py"),
        "load_seconds": engine.load_seconds,
        "duplicate_note": (f"Duplicates: {n_text_dup:,} of the {len(indexed_ids):,} indexed literature_ids "
                           f"have byte-identical indexed text to another id ({n_text_groups:,} groups, measured "
                           f"by hashing chunks_meta.jsonl); {n_dup_ids:,} in all once ids sharing a source PDF "
                           f"in today's fable_texts_manifest.csv are added. Duplicate texts compete for ranks; "
                           f"the duplicate-aware tables credit a retrieved duplicate of a relevant paper."
                           if n_dup_ids else None),
        "limitations": LIMITATIONS,
    }
    rp = write_report(out_dir, args.date, results, meta)
    print(f"[eval] report -> {rp}")


if __name__ == "__main__":
    main()
