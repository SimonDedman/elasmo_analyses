# RAG prototype (scripts/rag/)

First working Retrieval-Augmented-Generation prototype over the SharkPapers
PDF corpus. Full write-up, stack rationale, sample outputs, limitations and
scaling plan: **`docs/LLM/rag_prototype_status.md`**.

## Files

| File | Purpose |
|---|---|
| `common.py` | Shared config + PDF→literature_id matching + `pdftotext` extraction + chunking. Read-only w.r.t. the parquet. |
| `build_index.py` | Sample PDFs → match to parquet → extract → chunk → embed (CPU) → FAISS index. Resumable via `outputs/rag/pdf_attempt_log.csv`. |
| `rerank.py` | Cross-encoder (`cross-encoder/ms-marco-MiniLM-L-6-v2`, CPU) re-ranking of the FAISS top-N shortlist by direct `(query, chunk)` relevance. Fixes absolute-cosine over-reporting — see `docs/LLM/rag_prototype_status.md`. |
| `query.py` | Question → embed → FAISS retrieve top-N → cross-encoder re-rank to top-k → cited answer (Ollama) + programmatic claim-strength rating (now derived from cross-encoder scores, not raw cosine). `--no-rerank` disables the re-rank stage for A/B comparison only. |

## Interpreter

Use the shared **fashion-clip** venv (has torch/transformers/pandas/
sentence-transformers/faiss):

```bash
FCLIP=/home/simon/.venvs/fashion-clip/bin/python
```

## Run

```bash
# Build / extend the index (resumable; re-run with a larger --sample to grow)
$FCLIP scripts/rag/build_index.py --sample 300

# Start the local LLM server (user-local, no sudo, no systemd)
export OLLAMA_MODELS=/home/simon/.local/share/ollama-rag/models
export OLLAMA_HOST=127.0.0.1:11435
nohup /home/simon/.local/share/ollama-rag/bin/ollama serve \
    > /home/simon/.local/share/ollama-rag/serve.log 2>&1 &

# Ask
$FCLIP scripts/rag/query.py "How is age determined in sharks from vertebrae?"
$FCLIP scripts/rag/query.py "..." --no-generate     # ranked cited evidence, no LLM
$FCLIP scripts/rag/query.py "..." --json            # machine-readable
$FCLIP scripts/rag/query.py "..." --top-k 8 --retrieve-n 20  # defaults shown
$FCLIP scripts/rag/query.py "..." --no-rerank       # A/B: old absolute-cosine behaviour
```

## Artifacts (all under `outputs/rag/`, git-ignored)

`index.faiss`, `embeddings.npy`, `chunks_meta.jsonl`, `pdf_attempt_log.csv`.
