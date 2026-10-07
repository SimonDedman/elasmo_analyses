# RAG prototype (scripts/rag/)

First working Retrieval-Augmented-Generation prototype over the SharkPapers
PDF corpus. Full write-up, stack rationale, sample outputs, limitations and
scaling plan: **`docs/LLM/rag_prototype_status.md`**.

## Files

| File | Purpose |
|---|---|
| `common.py` | Shared config (`RAG_OUT_DIR`, text-cache paths), boundary-aware chunking, metadata. Read-only w.r.t. the parquet. |
| `build_from_cache.py` | Embeds the text cache into FAISS; `--fresh` for a rebuild; skips records whose PDF is already indexed under another record (`dedupe_skipped.csv`). |
| `sync_index.sh` / `progress.py` | Prepass → embed → sidecars → swap, and its one-screen monitor. |
| `build_index.py` | Sample PDFs → match to parquet → extract → chunk → embed (CPU) → FAISS index. Resumable via `outputs/rag/pdf_attempt_log.csv`. |
| `entailment.py` | Sentence-level NLI check of a generated answer (`cross-encoder/nli-deberta-v3-xsmall`, 70.8M parameters, about 270 MB, CPU; fallback `cross-encoder/nli-MiniLM2-L6-H768`). Each answer sentence is tested against the chunks it cites (and the other top hits, for contradiction). Drives the claim-strength badge when an answer exists: `well-supported` / `contested` / `limited` / `unresolved`. Tests: `tests/test_rag_entail.py`. |
| `rerank.py` | Cross-encoder (`cross-encoder/ms-marco-MiniLM-L-6-v2`, CPU) re-ranking of the FAISS top-N shortlist by direct `(query, chunk)` relevance. Fixes absolute-cosine over-reporting — see `docs/LLM/rag_prototype_status.md`. |
| `query.py` | Question → embed → FAISS retrieve top-N → cross-encoder re-rank to top-k → cited answer (Ollama) + programmatic claim-strength rating (now derived from cross-encoder scores, not raw cosine). `--no-rerank` disables the re-rank stage for A/B comparison only. |

## Interpreter

Use the shared **fashion-clip** venv (has torch/transformers/pandas/
sentence-transformers/faiss):

```bash
FCLIP=/home/simon/.venvs/fashion-clip/bin/python
```

## Keeping the index in step with the library (2026-10-07)

The text cache the index is built from (`outputs/validation/.fable_texts/`) now comes
from `outputs/pdf_id_map.csv` only (one PDF per record, hash-deduplicated), and
`scripts/refresh_pdf_map_and_extract.sh` ends by calling `scripts/rag/sync_index.sh`,
so a filing batch reaches the index without a manual step.

```bash
sh scripts/rag/sync_index.sh            # incremental: new texts embedded onto outputs/rag
sh scripts/rag/sync_index.sh --rebuild  # full rebuild in outputs/rag.new, swapped in when done
watch -n 60 -t -c 'cd "<project dir>" && python3 scripts/rag/progress.py'
```

`RAG_OUT_DIR` points every script at another index directory (`outputs/rag_test`
holds a 200-paper index for tests). Chunks are paragraph/sentence-bounded
(`common.chunk_text`); the July sliding window is kept as `chunk_text_words`.

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

## Run for other people

Three seams make the server safe to share. All default to the single-user behaviour.

| Variable | Values | Default | Effect |
|---|---|---|---|
| `RAG_LLM_BACKEND` | `ollama`, `anthropic`, `none` | `ollama` | Answer generator (`llm_backend.py`). `none` gives retrieval-only. |
| `RAG_LLM_MODEL` | any Claude model id | `claude-haiku-4-5` | Anthropic backend only. Temperature 0, `max_tokens` 600. |
| `ANTHROPIC_API_KEY` | key | unset | Anthropic backend only. Read from the environment, never from a file, never logged. Startup of a query fails with a clear message if it is absent. |
| `RAG_AUTH_MODE` | `open`, `token` | `open` | `token` requires a valid token on `/api/query` and `/api/history`. |
| `RAG_AUTH_TOKENS` | `name:secret,name:secret` | unset | Tokens, merged with `outputs/rag_state/auth_tokens.json`. |

Query history is always on: `outputs/rag_state/history.sqlite` (WAL). `GET /api/history?limit=` returns the caller's own rows only (every open-mode caller is `anonymous`). A write failure is logged and never affects the answer.

Launch (named unit that expires on its own, with a memory cap):

```
systemd-run --user --unit=claude-rag-serve -p RuntimeMaxSec=12h -p MemoryMax=8G \
  --setenv=RAG_AUTH_MODE=token --setenv=RAG_LLM_BACKEND=ollama \
  --working-directory="<project root>" \
  /home/simon/.venvs/fashion-clip/bin/python -m uvicorn serve:app --app-dir scripts/rag --host 0.0.0.0 --port 8000
systemctl --user stop claude-rag-serve    # stop early
```

Caveats for `--host 0.0.0.0`:
- Traffic is plain HTTP, so tokens cross the network in clear text. Use it on a trusted LAN or behind a TLS proxy or tunnel; never leave `RAG_AUTH_MODE=open` on a reachable address.
- There is no rate limit. With `RAG_LLM_BACKEND=anthropic` every query spends money, so anyone holding a token can run up the bill. A single local Ollama on the 1080 Ti serves one answer at a time.
- `/api/filters`, `/api/authors`, `/api/status` and `/` stay open by design (they expose no answers).

Mint a token (kept in `outputs/`, which is git-ignored):

```
python3 -c "import secrets,json,pathlib; p=pathlib.Path('outputs/rag_state/auth_tokens.json'); d=json.loads(p.read_text()) if p.exists() else {}; d['alice']=secrets.token_urlsafe(24); p.write_text(json.dumps(d,indent=1)); print(d['alice'])"
```

Give the person the printed secret. The browser page asks for it once on a 401 and keeps it in `localStorage`. From a script: `curl -H "Authorization: Bearer <secret>" ...` (or `X-SharkOracle-Token`). Revoke by deleting the entry; the file is re-read on every request.
