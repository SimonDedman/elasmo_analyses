# RAG schema filters + web front-end — design

**Date:** 2026-07-11
**Status:** Draft for review
**Author:** Simon Dedman (with Claude Code)
**Related:** `memory/project_rag_prototype.md`, `docs/LLM/rag_prototype_status.md`,
`scripts/rag/{common,build_index,query,rerank}.py`

## Purpose

Add two of the RAG prototype's "next to scale" items:

1. **Wire the parquet schema columns as FAISS metadata pre-filters** so a user can
   restrict a semantic query to, e.g., "genetics papers on pelagic sharks in the NE
   Atlantic since 2015 by author Simpfendorfer".
2. **A web front-end** (custom FastAPI + single-page HTML) that exposes the query
   pipeline (retrieval → cross-encoder rerank → claim-strength → local LLM answer)
   with the filters, inline citations, and the claim-strength badge.

Both are **decoupled from embedding**: neither requires rebuilding the ~10-hour
FAISS embedding index. This is the central design constraint.

## Non-goals (this iteration)

- Real authentication, rate-limiting logic, or multi-user session state.
- A database or persistent multi-user query history.
- Re-embedding the corpus, or changing the retrieval / rerank / claim-strength logic.
- Hosting/deployment itself (Docker images, TLS, a public URL).

These are **future** requirements the user has stated (shareable, served online,
multi-user, some auth to prevent abuse, query-history persistence). The design
therefore builds *seams* for each so they can be added later without a rewrite, but
doesn't implement them. Everything runs locally for solo testing to begin with.

## Central idea: decouple filtering from embedding

The 10-hour embedding index (`outputs/rag/index.faiss` + `embeddings.npy` +
`chunks_meta.jsonl`) never needs rebuilding to add or change filters.

- A **filter registry** auto-discovers filterable column families from the parquet
  schema.
- A small **`paper_filters.parquet` sidecar** (seconds to build) holds just those
  columns keyed by `literature_id`.
- At query time, active filters resolve to a set of allowed `literature_id`s → allowed
  chunk row-positions → a FAISS `IDSelectorBatch` pre-filter.

Adding a new family later = adjust the registry's discovery rules (or exclusion list)
and rerun the sidecar builder. No re-embedding.

**FAISS pre-filter verified working** on the installed build (faiss 1.14.3,
`IndexFlatIP`):

```python
sel = faiss.IDSelectorBatch(allowed_ids)          # int64 vector positions
params = faiss.SearchParameters(sel=sel)
D, I = index.search(qvec, k, params=params)        # returns only allowed positions
```

## Components

### 1. Config — `scripts/rag/config.py`

Centralises everything machine-specific so the server is portable (not locked to
Simon's paths/GPU). Reads from environment variables with local-sensible defaults:

| Setting | Env var | Local default |
|---|---|---|
| Project root | `RAG_PROJECT_ROOT` | derived from file location |
| Parquet path | `RAG_PARQUET` | `outputs/literature_review_enriched.parquet` |
| RAG output dir | `RAG_OUT_DIR` | `outputs/rag` |
| PDF library dir | `RAG_PDF_DIR` | current hardcoded `SharkPapers` path |
| Ollama host | `RAG_OLLAMA_HOST` | `http://127.0.0.1:11435` |
| Ollama model | `RAG_OLLAMA_MODEL` | `qwen2.5:3b-instruct` |
| LLM backend | `RAG_LLM_BACKEND` | `ollama` |
| Auth mode | `RAG_AUTH_MODE` | `open` |

Existing constants in `common.py` are re-exported from `config.py` (or `common.py`
imports from `config.py`) so nothing else breaks. **No absolute machine paths in the
server code** — all via config.

### 2. Filter registry — `scripts/rag/filter_config.py`

Auto-discovers families from the parquet schema so "include everything we can" is the
default. Discovery rules:

- **Boolean prefix families** — every column matching a known prefix becomes an option
  within that family: `eco_`, `pr_`, `gear_`, `imp_`, `d_`, `b_`, `sb_`, `a_`, and the
  boolean subset of `geo_`. Family display labels are curated (e.g. `d_` → "Discipline",
  `a_` → "Technique"); options derive their labels from the column name (strip prefix,
  title-case, expand `&`).
- **Scalar/categorical families** — curated list: `year` (range), `country`,
  `superregion`, `epoch`, `journal`, `data_source` (multiselect over distinct values).
- **Range families** — `year`, and `geo_study_latitude` / `geo_study_longitude`
  (numeric min/max; see caveat below).
- **Author family** — special `author-autocomplete` type (see component 4).
- **Exclusion list** — identifiers/free-text never offered as filters: `title`,
  `abstract`, `doi`, `pdf_url`, `date_added`, chunk/embedding internals. (`authors` is
  **not** excluded — it's served via the author-autocomplete family instead of the raw
  free-text column.)

Each family entry: `key`, `label`, `type`
(`multiselect | search-multiselect | range | author-autocomplete`), and either a column
`prefix`, an explicit `column`, or (for author) a resolver reference. Big families
(`a_` ~208, `sb_` 43) use `search-multiselect` and render collapsed by default so the UI
stays usable. This one module drives the sidecar builder, the API, and the frontend —
the UI is fully data-driven, so new families appear automatically.

**Registry is validated against the parquet schema at build/startup**: any configured
column absent from the parquet is skipped with a logged warning (never a crash).

### 3. Sidecar builder — `scripts/rag/build_filters.py`

Reads the parquet, keeps `literature_id` + every registry-named column, writes
`outputs/rag/paper_filters.parquet`. Boolean columns stored as bool; scalar columns as
their native type. Independent of the embedding pipeline; rebuildable in seconds.
Re-run whenever the registry changes or the parquet is refreshed.

Also builds the **author index** (`outputs/rag/author_index.parquet` +
`author_suggest.parquet`) from `openalex_paper_authors.csv` (author→`literature_id`) and
`openalex_unique_authors.csv` (canonical `display_name` + `paper_count` for ranking).

### 4. Filter resolution — extend `scripts/rag/query.py`

- New `load_filters()` (cached): loads `paper_filters.parquet` and the author index.
- New `resolve_filter_ids(filters) -> set[str]`: applies active filters with
  **OR within a family, AND across families**; returns the matching `literature_id` set
  (or `None` meaning "no filter → all papers"). Author selections resolve via the author
  index; range filters (year, lat, lon) apply min/max bounds.
- Extend `retrieve(question, retrieve_n, allowed_ids=None)`: when `allowed_ids` is set,
  map to chunk vector positions (precomputed `literature_id → [positions]` from
  `chunks_meta` order) and pass `SearchParameters(sel=IDSelectorBatch(positions))` into
  `index.search`.
- Everything downstream (cross-encoder rerank, `claim_strength`, Ollama generate) is
  unchanged. Backward compatible: no filters → today's behaviour. The CLI gains an
  optional `--filters '<json>'` flag for parity/testing.
- **Empty/tiny filter result** is detected before retrieval and surfaced (see error
  handling).

**Author autocomplete resolver**: substring match on accent-folded `display_name`,
ranked by `paper_count` desc, capped (e.g. top 20). 29,930 authors fit in memory.

### 5. LLM backend abstraction — `scripts/rag/llm_backend.py`

A minimal `generate(prompt) -> str` interface with an `OllamaBackend` implementation
(the current `generate_answer` logic, moved here) selected by `RAG_LLM_BACKEND`.
Generation is the real scaling bottleneck (one local Ollama on a GTX 1080 Ti won't
serve many concurrent users); this seam lets a hosted API or larger shared model drop in
later without touching the pipeline. Only `ollama` is implemented now.

### 6. FastAPI backend — `scripts/rag/serve.py`

Runs user-local via `uvicorn` (no Docker, no sudo). **Models and indexes load once at
startup** into app state via the lifespan handler — BGE embedder, cross-encoder, FAISS
index, chunk metadata, filter sidecar, author index. (Today `query.py` reloads the
embedding model on every call; that's fine for CLI but fatal for a server — this is the
single most important multi-user change.)

Endpoints:

- `GET /api/filters` → the registry: families, their options (with per-option paper
  counts from the sidecar), value ranges for range families. Drives the UI.
- `GET /api/authors?q=<str>` → ranked author suggestions `[{display_name, id,
  paper_count}]`.
- `POST /api/query` → body `{question, filters, top_k, retrieve_n, generate}` → runs the
  pipeline (with pre-filter) and returns the JSON `query.py` already produces (`answer`,
  `claim_strength`, `retrieved` sources, `mode`) **plus** `n_papers_matching_filter`.
- `GET /` → serves the static single-page app.

**Auth seam**: a FastAPI dependency `require_access` gated by `RAG_AUTH_MODE`. In `open`
(local default) it's a no-op. It's the single place to later add an API key or
per-key rate-limit. No auth logic implemented now.

**History seam**: `record_query(question, filters, result_summary)` with a local JSONL
implementation writing to `outputs/rag/query_history.jsonl` (gives history for free
now); swappable to a DB later. Wrapped so a write failure never breaks a query.

### 7. Front-end — `scripts/rag/static/index.html`

Self-contained vanilla HTML/CSS/JS (no build step; matches the project's existing
custom-HTML GitHub-Pages dashboards). On load, `GET /api/filters` builds the filter
panel dynamically:

- Multiselect families → checkbox groups (large ones collapsed).
- `search-multiselect` (`a_`, `sb_`) → a filter-as-you-type box over the option labels.
- `range` families (year, lat, lon) → dual numeric min/max entry boxes.
- Author → a debounced autocomplete box hitting `/api/authors`.

Results area: the generated answer with clickable `[literature_id]` citations, a
colour-coded claim-strength badge (well-supported / limited / unresolved), the
`n_papers_matching_filter` count, and an expandable ranked source list (title, authors,
year, cosine + cross-encoder relevance).

## Data flow

```
question + filters
  → POST /api/query
  → resolve_filter_ids  → allowed literature_ids  → allowed chunk positions
  → embed query (BGE, loaded once)
  → FAISS pre-filtered retrieval (IDSelectorBatch)
  → cross-encoder rerank
  → top-k
  → claim_strength (cross-encoder scores)
  → LLM backend generate (cited answer)
  → JSON  → render (answer + citations + badge + sources)
```

## Error handling

- **Ollama / LLM down** → retrieval-only mode (already handled in `query.py`), surfaced
  as `mode` in the response; the UI shows ranked evidence instead of a generated answer.
- **Empty filter result** (0 papers match) → detected before retrieval; response carries
  `n_papers_matching_filter: 0`, generation skipped, UI shows "0 papers match these
  filters".
- **Index / sidecar missing** → `503` with a clear message.
- **Registry column absent from parquet** → skipped with a startup warning.
- **History write failure** → logged, never breaks the query.

## Known data caveat: geo study coordinates

`geo_study_latitude` / `geo_study_longitude` are included as range filters per explicit
user request, but the stored values are unreliable: across all 967 non-null rows there
are **zero negative values** (lat 0.0–89.3, lon 0.0–176.5), despite the corpus containing
many Southern-/Western-hemisphere studies (a known-wrong example: a South Africa paper
stored as lat 65.2 / lon 69.3). The hemisphere sign appears lost **in the data**, not
merely in a past plot. Consequences documented in the UI and here:

- A lat/lon range filter treats every study as Northern/Eastern hemisphere.
- Requesting a Southern/Western range will match nothing.

The filter is wired so that a corrected/signed coordinate source (re-extraction) is a
drop-in replacement for the column with no other changes.

**Decision (2026-07-11): include the geo range filter now, caveated.** Separately,
**an upstream fix is required**: the coordinate extraction that populates
`geo_study_latitude` / `geo_study_longitude` must be corrected to preserve the
hemisphere sign (S negative latitude, W negative longitude). Tracked as a follow-up
action outside this spec's scope; once fixed and the parquet re-merged, the geo range
filter becomes correct with no code change (rebuild the sidecar only).

## Author-filter coverage caveat

Author filtering reaches only papers with OpenAlex author records
(`openalex_paper_authors.csv`, 74,153 author-paper rows over ~half the corpus — OpenAlex
DOI-matched ~15,780 of 30,553 papers). Papers without OpenAlex records won't match an
author selection. Surfaced in the UI near the author box.

## Testing

- **Unit** — `resolve_filter_ids` for known filter combinations (OR-within/AND-across),
  including author, year range, and lat/lon range; `IDSelectorBatch` correctness (every
  returned chunk belongs to an allowed paper); registry auto-discovery against a small
  fixture schema; author autocomplete ranking.
- **Integration** — `/api/filters` shape; `/api/authors` ranking; `/api/query` with and
  without filters; the empty-filter case; the Ollama-down path.
- **Manual** — load the page, run a filtered query, confirm citations render, badge
  colour matches `claim_strength.label`, and `n_papers_matching_filter` is correct.

## New dependencies

`fastapi` + `uvicorn` installed into the shared `fashion-clip` venv
(`/home/simon/.venvs/fashion-clip/bin/python`). No system packages, no Docker, no sudo.

## Files

New: `scripts/rag/config.py`, `filter_config.py`, `build_filters.py`,
`llm_backend.py`, `serve.py`, `static/index.html`, plus tests under
`scripts/rag/tests/`.
Modified: `scripts/rag/query.py` (filter resolution, pre-filter retrieval, `--filters`),
`scripts/rag/common.py` (import paths/config from `config.py`).
Generated (git-ignored, under `outputs/rag/`): `paper_filters.parquet`,
`author_index.parquet`, `author_suggest.parquet`, `query_history.jsonl`.

## Deployment note (future, not this iteration)

The retrieval stack (FAISS + BGE + cross-encoder) is portable and cheap to serve. The
LLM generation is the machine-specific bottleneck (local Ollama on a single GPU). When
this is served online for multiple users, the likely path is: keep retrieval local/on a
small box, swap the LLM backend to a hosted API or a shared inference server, turn on the
auth seam (API keys + rate-limit), and move history to a DB. The seams above are placed
so each of these is a localised change.
