# RAG prototype status (2026-07-06, updated 2026-07-07: cross-encoder re-ranker)

First working end-to-end Retrieval-Augmented-Generation prototype over the
SharkPapers PDF corpus: embed → retrieve → cite → generate → rate claim
strength. Built OODA-style — a working demo over a 300-paper sample, not a
production system. See "Next steps to scale" below for the path to the
full ~19-20k corpus and the structured-filter search from GitHub Issue #2.

## Stack chosen (and why)

| Component | Choice | Why |
|---|---|---|
| PDF text extraction | `pdftotext` (poppler-utils), same approach as `extract_schema_columns.py` | Already proven on this corpus; no new dependency |
| Chunking | Word-based sliding window, ~650 words (~850-900 tokens) / 100-word overlap | Simple, fast, no tokenizer dependency; good enough for a first pass |
| Embeddings | `BAAI/bge-small-en-v1.5` (33M params, 384-dim), CPU, via `sentence-transformers` | Retrieval-tuned (asymmetric query/passage training), small enough to embed thousands of chunks on CPU in seconds; the GTX 1080 Ti (Pascal, sm_61) can't run modern CUDA torch wheels, so embedding is CPU-only by design |
| Vector store | **FAISS** `IndexFlatIP` (flat, exact cosine via normalized vectors) | No server, no Docker, pip-installable; exact search is fine at this scale (a few thousand chunks) — Qdrant/HNSW only pays off once the corpus is much bigger (see scaling notes) |
| Re-ranker | **`cross-encoder/ms-marco-MiniLM-L-6-v2`** (~23M params), CPU, via `sentence-transformers.CrossEncoder` | Scores each `(query, chunk_text)` pair directly with cross-attention rather than comparing two independently-embedded vectors, so its scores are calibrated to actual relevance in a way BGE's absolute cosine is not (see "Claim-strength" below and the before/after in Limitations). Small enough to score the FAISS top-20 shortlist per query in ~8-10s on CPU — no GPU needed |
| LLM | **Ollama 0.31.1**, model `qwen2.5:3b-instruct` | Neither Ollama nor Qdrant were pre-installed. Ollama was installed **without sudo**: the release tarball was downloaded and extracted straight into `~/.local/share/ollama-rag/` (binary + model store), and `ollama serve` runs as a plain user process on a non-default port (`127.0.0.1:11435`), so it never touches system paths or systemd. Ollama auto-detected the 1080 Ti and is running its **Vulkan** compute backend (not CUDA — Vulkan compute isn't gated by the sm_61/cu128 cutoff that blocks PyTorch), giving ~3-4s generations for a 3B model instead of a much slower CPU fallback. |
| Interface | CLI (`scripts/rag/query.py`) | Sufficient for a first prototype; Open WebUI (per the roadmap doc) is a follow-on step once the pipeline is proven |

Python environment: the shared `fashion-clip` venv
(`/home/simon/.venvs/fashion-clip/bin/python`) already had `torch`,
`transformers`, `pandas`, `pyarrow`, `numpy` (built with
`--system-site-packages`), so only `sentence-transformers` and `faiss-cpu`
needed installing — done via `pip install` into that venv, no heavy new
downloads beyond the two small wheels. `sentence-transformers` 5.6.0
already ships `CrossEncoder`, so the re-ranker needed no extra package —
only the ~90MB `cross-encoder/ms-marco-MiniLM-L-6-v2` weights, cached under
`~/.cache/huggingface` like the embedding model. **No GPU packages were
installed for embeddings or re-ranking**; both run on CPU as required.

## What works end-to-end

1. **Sampling + matching** (`scripts/rag/build_index.py`): randomly samples
   PDFs from the SharkPapers library (20,046 PDFs total on disk), parses
   the library filename convention (`Surname[.etal].Year.Title
   fragment.pdf`), and matches each to its `literature_id` row in
   `outputs/literature_review_enriched.parquet` by first-author-surname +
   year(±1) + title-word-overlap (score ≥ 0.25). This is read-only against
   the parquet.
2. **Extraction + chunking**: `pdftotext` per matched PDF, chunked into
   ~650-word / 100-word-overlap pieces.
3. **Embedding**: `BAAI/bge-small-en-v1.5` on CPU, batch size 32,
   normalized vectors.
4. **Indexing**: chunks + metadata (`literature_id`, title, authors, year,
   journal, DOI, chunk_id) written to
   `outputs/rag/chunks_meta.jsonl` + `outputs/rag/embeddings.npy`; FAISS
   flat index written to `outputs/rag/index.faiss`.
5. **Retrieval** (`scripts/rag/query.py`): embeds the question with the
   BGE query-instruction prefix, retrieves the top **20** candidate chunks
   (`--retrieve-n`, default 20) by FAISS cosine similarity.
6. **Cross-encoder re-rank** (`scripts/rag/rerank.py`, new 2026-07-07):
   scores each `(question, chunk_text)` pair from those 20 candidates with
   `cross-encoder/ms-marco-MiniLM-L-6-v2` (CPU, ~8-10s for 20 pairs), sorts
   by that score, and keeps the top **8** (`--top-k`) for citation and
   generation. `--no-rerank` disables this stage and falls back to raw
   FAISS cosine order, kept only as an A/B lever to reproduce the old
   over-reporting bug for comparison — not for real use.
7. **Generation**: if Ollama is reachable, builds a citation-constrained
   prompt (every source is presented as `SOURCE [literature_id] Author et
   al. Year — Title`) and asks the model to end every factual sentence
   with its `[literature_id]` citation. If Ollama is not reachable, falls
   back to printing the ranked, cited evidence chunks directly (no
   generation) — retrieval and citation are the part that must never
   silently fail.
8. **Claim-strength rating** (computed **programmatically**, not asserted
   by the LLM — see Limitations): derived from how many *distinct papers*
   in the re-ranked set clear a **cross-encoder relevance** bar (an
   unbounded logit, not a cosine or a probability). Thresholds calibrated
   2026-07-07 against this index using one in-domain query and the
   deliberate out-of-domain probe (numbers below):
   - **well-supported**: ≥3 distinct papers with cross-encoder score ≥ 1.0
   - **limited**: 1-2 such papers, or several papers ≥ 0.0 (the floor) but
     below 1.0
   - **unresolved**: top cross-encoder score < 0.0 — nothing retrieved is
     actually relevant, regardless of how high its cosine similarity was

Build run (this prototype): **300 papers indexed, 47 unmatched (86%
match rate), 0 extraction failures, 4,860 chunks** from the random sample.
Full attempt log: `outputs/rag/pdf_attempt_log.csv`.

## How to run

```bash
# 1. Build (or extend) the index — resumable, safe to re-run with a bigger --sample
/home/simon/.venvs/fashion-clip/bin/python scripts/rag/build_index.py --sample 300

# 2. Make sure the local LLM server is up (user-local, no sudo, no systemd)
export OLLAMA_MODELS=/home/simon/.local/share/ollama-rag/models
export OLLAMA_HOST=127.0.0.1:11435
CUDA_VISIBLE_DEVICES="" nohup /home/simon/.local/share/ollama-rag/bin/ollama serve \
    > /home/simon/.local/share/ollama-rag/serve.log 2>&1 &

# 3. Ask a question
/home/simon/.venvs/fashion-clip/bin/python scripts/rag/query.py \
    "What techniques are used to study diving behaviour in pelagic sharks?"

# Retrieval-only (no LLM call, just ranked cited evidence, still re-ranked):
/home/simon/.venvs/fashion-clip/bin/python scripts/rag/query.py "..." --no-generate

# Machine-readable output:
/home/simon/.venvs/fashion-clip/bin/python scripts/rag/query.py "..." --json

# A/B: disable the cross-encoder to see the old (over-reporting) behaviour
/home/simon/.venvs/fashion-clip/bin/python scripts/rag/query.py "..." --no-rerank
```

## Sample outputs

All ran against the 300-paper / 4,860-chunk index, with the cross-encoder
re-ranker enabled (default). Generations came from `qwen2.5:3b-instruct` on
Ollama in ~3-5s each; the re-rank stage itself adds ~8-10s per query on CPU
(scoring 20 FAISS candidates before keeping the top 8).

**Q: "What techniques are used to study the diving and movement behaviour of
pelagic sharks?"**
> Techniques used to study the diving and movement behavior of pelagic
> sharks include archival tagging, which records depth data frequently over
> long periods... Additionally, accelerometers attached to these tags
> provide information on locomotor activity patterns... [23522] [19519].
>
> **Claim strength: WELL-SUPPORTED** — 4 distinct papers, top cross-encoder
> relevance 5.65. Sources: [23522] Shepard et al. 2006 (cosine 0.80,
> relevance 5.65), [19519] Gleiss et al. 2013 (cosine 0.77, relevance 4.86),
> [32125] Hoyos-Padilla et al. 2023 (cosine 0.73, relevance 2.26).

**Q: "How is age and growth determined in sharks using vertebral analysis?"**
> Age and growth in sharks are determined using vertebral analysis,
> particularly counting annuli or growth bands on vertebrae [4968]... For
> species such as spiny dogfish and white sharks, experts prefer reading
> annuli externally from the second dorsal spine [29568, 29562]...
>
> **Claim strength: WELL-SUPPORTED** — 6 distinct papers, top cross-encoder
> relevance 4.73 (Tanaka et al. 2011, [13271]). All 6 papers score ≥ 1.0
> (range 1.48-4.73), well clear of the 0.0 floor. (Here the LLM used the
> requested inline `[literature_id]` citation format.)

**Q: "How does climate change affect deep-sea shark distributions?"**
> Climate change affects deep-sea shark distributions by potentially
> shifting their geographical ranges due to changes in temperature and
> oceanic conditions such as oxygen minimum zones [30614]... deep-sea sharks
> face increased fishing pressure and may experience a shift in population
> phenology [28492].
>
> **Claim strength: LIMITED** — 1 paper with strong cross-encoder relevance
> (top score 2.92), 4 more above the floor but not strong. (Under the old
> absolute-cosine heuristic this same retrieval was rated WELL-SUPPORTED at
> "4 distinct papers, top similarity 0.80" — a smaller, more honest
> illustration of the same over-reporting problem the CRISPR probe shows
> more starkly below: cosine ~0.80 was common to genuinely strong and only
> loosely-related hits alike.)

**Q: "CRISPR gene editing protocols for shark embryos" (deliberate
out-of-sample probe — no such papers exist in this corpus)**

BEFORE (absolute-cosine heuristic, `--no-rerank`):
> Retrieved shark *genomics/transcriptomics* papers ([13642] shark myelin
> proteins, [26755] zebra bullhead shark transcriptome, [27738]
> chondrichthyan genomics) at cosine similarity 0.76-0.80 — but **none
> actually describe CRISPR protocols**. The heuristic labelled this
> **WELL-SUPPORTED** ("6 distinct papers retrieved with high similarity
> (>= 0.55) to the question, top similarity 0.80"). A real miscalibration.

AFTER (cross-encoder re-ranked, default, `--no-generate`):
> Same shortlist re-scored by the cross-encoder: every single chunk comes
> back **negative** (-1.89 to -4.32), despite cosine on the same chunks
> still reading 0.76-0.80. Top hit [29137] Gervais et al. 2021 (thermal
> physiology, not genomics or CRISPR) scores -1.89.
>
> **Claim strength: UNRESOLVED** — "top cross-encoder relevance score -1.89
> is below the floor (0.0) — nothing retrieved is actually relevant to the
> question, regardless of cosine similarity; the corpus likely has no
> evidence on this topic." This is the fix: the label now correctly reports
> no evidence instead of a false WELL-SUPPORTED.

Retrieval-only mode (`--no-generate`) prints the same ranked, cited,
re-ranked evidence list without calling the LLM, so citation + ranking work
even with no model server running.

## Limitations (be honest about these)

- **300 of ~20,000 PDFs indexed (~1.5%).** Most questions about niche
  topics will correctly come back "unresolved" simply because the sample
  doesn't contain relevant papers yet — that is expected at this stage,
  not a bug in retrieval.
- **Claim-strength over-reporting on absolute cosine — FIXED 2026-07-07
  by adding a cross-encoder re-ranker** (`scripts/rag/rerank.py`,
  `cross-encoder/ms-marco-MiniLM-L-6-v2`). The old heuristic counted how
  many *distinct papers* cleared an *absolute* cosine-similarity bar for
  the *question*; two problems were observed and are now addressed:
  1. **BGE-small ran high absolute cosine, and did not separate on-topic
     from topic-adjacent.** On this corpus genuinely on-topic hits scored
     ~0.77-0.87 cosine, but the out-of-sample "CRISPR gene editing
     protocols for shark embryos" probe still pulled shark-genomics papers
     at ~0.76-0.80 cosine and was labelled WELL-SUPPORTED (see before/after
     above). **Fix applied:** re-rank the FAISS top-20 with a cross-encoder
     that scores `(query, chunk)` pairs directly via cross-attention, and
     derive claim-strength from *that* score instead. On this index the fix
     produces a clean sign flip — genuinely relevant chunks score positive
     (+1.5 to +5.6 observed), the CRISPR probe's best chunk scores -1.89 —
     so a floor of 0.0 cleanly separates the two cases tested. This is
     still only two calibration points (one in-domain question family, one
     out-of-domain probe); it has **not** been validated against a larger
     gold-standard query set (see "Next steps to scale" item 8), so treat
     the exact threshold values as a reasonable first cut, not tuned
     statistics.
  2. **It is still agreement-of-topic, not agreement-of-claim** — this part
     is *not* fixed by the re-ranker. It does not
     check whether the retrieved papers agree with *each other* on a
     specific finding, or whether one contradicts the others — two papers
     with opposite conclusions both count as "support". Fixing this needs
     an NLI/entailment pass between the answer and its sources, or asking
     the LLM to flag cross-source contradictions (its own claim still
     cross-checked, not trusted blindly).

  Until (2) is addressed, treat the label as "how much genuinely relevant
  evidence was retrieved", **not** "how correct the answer is" or "whether
  sources agree on the specific claim". (1) is fixed; (2) remains the next
  thing to harden before the sharkatlas.org-style rating goes in front of
  users.
- **Chunking is naive** (fixed word count, no section/heading awareness).
  Extraction pipeline already has section-aware logic
  (`strip_non_body_sections` in `extract_schema_columns.py`) that RAG
  chunking does not yet reuse — a chunk can straddle e.g. an abstract and
  results section boundary.
- **PDF→literature_id matching is heuristic** (surname + year ± 1 + title
  word overlap ≥ 0.25). At 300-paper scale this measured 86% match rate
  with 0 observed false positives on manual spot-check of the sample, but
  it has not been validated at the full-corpus scale where more
  near-duplicate titles/authors exist.
- **`qwen2.5:3b-instruct` is small.** It follows the citation-per-sentence
  instruction well in testing but is not a strong reasoner; a larger model
  (7B-14B) would likely produce better synthesis if CPU/Vulkan throughput
  allows it — worth trying now that Ollama+Vulkan on the 1080 Ti is
  confirmed working.
- **No deduplication across near-identical chunks** (e.g. a review paper
  quoting another paper's abstract) — could inflate apparent
  "concordance" for claim-strength.
- **No hybrid (keyword+vector) search yet** — pure semantic retrieval can
  miss exact-term queries (species names, gear acronyms) that a BM25/
  keyword pass would catch immediately.

## Next steps to scale

1. **Scale the index to the full corpus.** Re-run `build_index.py` with
   `--sample` raised in batches (it's resumable — already-attempted PDFs
   are skipped via `outputs/rag/pdf_attempt_log.csv`, already-indexed
   papers via literature_id dedup). At ~20-25s per 300-paper batch on CPU
   for embedding alone (excluding I/O), the full ~20k library is roughly
   60-90x this run — budget a few hours of unattended CPU time, batched
   overnight.
2. **Wire the structured-filter search from GitHub Issue #2** — the
   parquet's 166 schema columns (year, geography, discipline, pressure,
   gear, taxon) already exist; add them as FAISS metadata pre-filters
   (filter chunk candidates by year range / `b_*` basin / `d_*` discipline
   columns before the vector search) so users can combine "papers from
   2015-2020 about acoustic telemetry in hammerheads" with the semantic
   question.
3. **Section-aware chunking** — reuse `strip_non_body_sections` /
   section-weighting logic from `extract_schema_columns.py` so
   introduction/methods/results/discussion boundaries aren't split
   mid-chunk, and so reference/acknowledgement sections are excluded (as
   they already are for schema extraction).
4. **Hybrid retrieval** — add a BM25/keyword pass (e.g. `rank_bm25` or
   SQLite FTS5 over the same chunk text) and combine scores with the
   vector search, per the roadmap doc's Boolean/phrase/wildcard search
   requirements.
5. **Move off IndexFlatIP once the corpus grows** — flat search is O(n)
   per query; fine at a few thousand chunks, but the full corpus at
   ~20-30k papers x ~15 chunks/paper could be 300-400k vectors. Switch to
   FAISS `IndexHNSWFlat` or move to Qdrant (as originally scoped) once
   query latency is felt.
6. **Contradiction-aware claim-strength** — the cross-encoder re-ranker
   (done 2026-07-07) fixed absolute-cosine over-reporting on *topic*
   relevance, but claim-strength is still agreement-of-topic, not
   agreement-of-claim. Next: an entailment check between the generated
   answer's citations (do the cited sources actually support the sentence,
   or contradict each other?), closer to the sharkatlas.org UX the lead
   asked to match.
7. **Open WebUI front-end** — once retrieval quality is validated on a
   bigger sample, wire `query.py`'s retrieve+generate logic into Open
   WebUI (already scoped in the roadmap doc) for a chat-style interface,
   or a lightweight Streamlit/Gradio wrapper as an interim step.
8. **Evaluate retrieval quality quantitatively, including the cross-encoder
   thresholds.** Build a small gold-standard question set (reuse the
   Schiffman 22-category comparison or manually curated Q&A pairs) and
   measure precision@k / whether the correct paper appears in top-k, rather
   than relying on spot-checks. The CE_FLOOR=0.0 / CE_STRONG=1.0 cut-offs
   (`scripts/rag/query.py`) are currently calibrated against exactly two
   probes (one in-domain, one deliberately out-of-domain) — solid enough to
   fix the demonstrated bug, but should be re-validated once this
   gold-standard set exists.
