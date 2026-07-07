# RAG prototype status (2026-07-06)

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
| LLM | **Ollama 0.31.1**, model `qwen2.5:3b-instruct` | Neither Ollama nor Qdrant were pre-installed. Ollama was installed **without sudo**: the release tarball was downloaded and extracted straight into `~/.local/share/ollama-rag/` (binary + model store), and `ollama serve` runs as a plain user process on a non-default port (`127.0.0.1:11435`), so it never touches system paths or systemd. Ollama auto-detected the 1080 Ti and is running its **Vulkan** compute backend (not CUDA — Vulkan compute isn't gated by the sm_61/cu128 cutoff that blocks PyTorch), giving ~3-4s generations for a 3B model instead of a much slower CPU fallback. |
| Interface | CLI (`scripts/rag/query.py`) | Sufficient for a first prototype; Open WebUI (per the roadmap doc) is a follow-on step once the pipeline is proven |

Python environment: the shared `fashion-clip` venv
(`/home/simon/.venvs/fashion-clip/bin/python`) already had `torch`,
`transformers`, `pandas`, `pyarrow`, `numpy` (built with
`--system-site-packages`), so only `sentence-transformers` and `faiss-cpu`
needed installing — done via `pip install` into that venv, no heavy new
downloads beyond the two small wheels. **No GPU packages were installed
for embeddings**; embeddings run on CPU as required.

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
   BGE query-instruction prefix, retrieves top-k chunks by cosine
   similarity.
6. **Generation**: if Ollama is reachable, builds a citation-constrained
   prompt (every source is presented as `SOURCE [literature_id] Author et
   al. Year — Title`) and asks the model to end every factual sentence
   with its `[literature_id]` citation. If Ollama is not reachable, falls
   back to printing the ranked, cited evidence chunks directly (no
   generation) — retrieval and citation are the part that must never
   silently fail.
7. **Claim-strength rating** (computed **programmatically**, not asserted
   by the LLM — see Limitations): derived from how many *distinct papers*
   in the retrieved set clear a cosine-similarity bar.
   - **well-supported**: ≥3 distinct papers retrieved with similarity ≥ 0.55
   - **limited**: 1-2 such papers, or several papers ≥ 0.40
   - **unresolved**: nothing clears 0.40 — the indexed sample doesn't
     cover the question

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

# Retrieval-only (no LLM call, just ranked cited evidence):
/home/simon/.venvs/fashion-clip/bin/python scripts/rag/query.py "..." --no-generate

# Machine-readable output:
/home/simon/.venvs/fashion-clip/bin/python scripts/rag/query.py "..." --json
```

## Sample outputs

All four ran against the 300-paper / 4,860-chunk index. Generations came
from `qwen2.5:3b-instruct` on Ollama in ~3-5s each.

**Q: "What techniques are used to study the diving and movement behaviour of
pelagic sharks?"**
> Techniques such as archival tagging with data loggers that record
> acceleration and depth are used to study diving and movement behavior of
> pelagic sharks... accelerometer-based devices for identifying straight
> versus area-restricted search behaviors... (Gleiss et al., 2013; Shepard
> et al., 2010).
>
> **Claim strength: WELL-SUPPORTED** — 3 distinct papers, top similarity
> 0.80. Sources: [23522] Shepard et al. 2006 (0.80), [19519] Gleiss et al.
> 2013 (0.77), [23002] Meekan et al. 2015 (0.76).

**Q: "How is age and growth determined in sharks using vertebral analysis?"**
> Age and growth in sharks are determined using vertebral analysis,
> particularly counting annuli or growth bands on vertebrae [4968]... For
> species such as spiny dogfish and white sharks, experts prefer reading
> annuli externally from the second dorsal spine [29568, 29562]...
>
> **Claim strength: WELL-SUPPORTED** — 6 distinct papers, top similarity
> 0.87. (Here the LLM used the requested inline `[literature_id]` citation
> format.)

**Q: "How does climate change affect deep-sea shark distributions?"**
> Climate change affects deep-sea shark distributions by potentially
> shifting their geographical ranges due to changes in temperature and
> oceanic conditions such as oxygen minimum zones [30614]... deep-sea sharks
> face increased fishing pressure and may experience a shift in population
> phenology [28492].
>
> **Claim strength: WELL-SUPPORTED** — 4 distinct papers, top similarity
> 0.80.

**Q: "CRISPR gene editing protocols for shark embryos" (deliberate
out-of-sample probe, `--no-generate`)**
> Retrieved shark *genomics/transcriptomics* papers ([26755] zebra bullhead
> shark transcriptome, [30083] reef shark mitogenome, [27738]
> chondrichthyan genomics) at similarity ~0.78-0.80 — but **none actually
> describe CRISPR protocols**. The heuristic still labelled this
> WELL-SUPPORTED. This is a real miscalibration, discussed under
> Limitations — it is why claim-strength must not be read as
> "the answer is correct".

Retrieval-only mode (`--no-generate`) prints the same ranked, cited
evidence list without calling the LLM, so citation + ranking work even with
no model server running.

## Limitations (be honest about these)

- **300 of ~20,000 PDFs indexed (~1.5%).** Most questions about niche
  topics will correctly come back "unresolved" simply because the sample
  doesn't contain relevant papers yet — that is expected at this stage,
  not a bug in retrieval.
- **Claim-strength over-reports "well-supported" — confirmed in testing,
  do not trust it yet.** It counts how many *distinct papers* clear an
  *absolute* cosine-similarity bar for the *question*. Two problems, both
  observed:
  1. **BGE-small runs high absolute cosine.** On this corpus genuinely
     on-topic hits scored ~0.77-0.87, but a deliberately out-of-sample
     probe ("CRISPR gene editing protocols for shark embryos" — no such
     papers in the sample) still pulled shark-genomics papers at ~0.78-0.80
     and was labelled WELL-SUPPORTED. Absolute similarity from this model
     does **not** cleanly separate "on-topic" from "topic-adjacent", so
     raising the threshold alone won't fix it — the on-topic and
     off-topic scores overlap. The real fixes are (a) a cross-encoder
     re-ranker over the top-k, (b) a relative-gap test (is the top hit
     much closer than the k-th?), and/or (c) grounding claim-strength on
     whether the *generated answer* is actually entailed by its cited
     chunks rather than on question↔chunk similarity.
  2. **It is agreement-of-topic, not agreement-of-claim.** It does not
     check whether the retrieved papers agree with *each other* on a
     specific finding, or whether one contradicts the others — two papers
     with opposite conclusions both count as "support". Fixing this needs
     an NLI/entailment pass between the answer and its sources, or asking
     the LLM to flag cross-source contradictions (its own claim still
     cross-checked, not trusted blindly).

  Until (1) and (2) are addressed, treat the label as "how much
  topically-relevant evidence was retrieved", **not** "how correct the
  answer is". This is the single most important thing to harden before the
  sharkatlas.org-style rating goes in front of users.
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
6. **Contradiction-aware claim-strength** — replace/augment the
   similarity-count heuristic with an entailment check between the
   generated answer's citations (do the cited sources actually support the
   sentence, or contradict each other?), closer to the sharkatlas.org UX
   the lead asked to match.
7. **Open WebUI front-end** — once retrieval quality is validated on a
   bigger sample, wire `query.py`'s retrieve+generate logic into Open
   WebUI (already scoped in the roadmap doc) for a chat-style interface,
   or a lightweight Streamlit/Gradio wrapper as an interim step.
8. **Evaluate retrieval quality quantitatively** — build a small
   gold-standard question set (reuse the Schiffman 22-category comparison
   or manually curated Q&A pairs) and measure precision@k / whether the
   correct paper appears in top-k, rather than relying on spot-checks.
