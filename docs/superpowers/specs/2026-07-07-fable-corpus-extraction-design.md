# Corpus-wide Fable extraction (overnight token burn, resumable to 12 Jul)

**Date:** 2026-07-07
**Status:** Approved (design A), implementing
**Author:** Simon Dedman (with Claude Code)

## Problem / opportunity

The 166-column regex extractor (`extract_schema_columns.py`) agrees with human
labels at macro-F1 **0.43** (gold set). The validation loop's A/B showed Fable
(`claude-fable-5`) reaching **0.80** on the same columns — nearly double. Fable
access expires **12 Jul 2026**; the interactive session can be switched to Fable
and the token budget spent to relabel the whole corpus at the higher quality
before access lapses.

**Goal:** run Fable structured extraction over **all resolvable PDFs**
(~15–18k; 30,546 rows have author+year+title metadata, fewer resolve to a PDF on
disk), producing a corpus-wide high-quality label set that supersedes the regex
output — **resumable across nights** until access expires.

## What Fable extracts

- The **166 binary schema columns** already defined in `ALL_SCHEMAS`
  (`eco_` 20, `pr_` 26, `gear_` 28, `imp_` 21, `d_` 19, `b_` 9, `sb_` 43) —
  ocean basins and sub-basins are already covered.
- **NEW geography:** `study_country` (list) and `study_region` (free text) — the
  actual place the study was conducted. The schema has **no** study-country
  field today, and the geo-pipeline's `geo_study_latitude/longitude` are known
  broken (hemisphere sign lost; see project memory). Fable extracts study
  location reliably, so this is the highest-value addition and the answer to
  "geography columns, if not already included".

## Billing / execution path

**No `ANTHROPIC_API_KEY` exists on this machine** (checked env, `.env`,
dotfiles, `~/.anthropic`, claude settings). Fable is available only as a **model
inside Claude Code**. Therefore the burn cannot use the standalone
`fable_extract.py` (which calls `anthropic.Anthropic()`); the Fable inference
must come from **Claude Code subagents** running under a Fable session. A
Claude Code **Workflow** launched from a Fable-model session fans out subagents
that inherit Fable — each subagent's forced structured output is one Fable call,
billed to the Claude Code Fable allowance.

## Architecture — three stages (only the middle burns Fable)

### 1. Pre-pass (local, no Fable) — `scripts/validation/fable_corpus_prepass.py`

Reuses the resolution helpers in `fable_extract.py` /
`extract_schema_columns.py` (`_first_surname`, PDF index, `_pick_best_pdf`,
`extract_text_from_pdf`). For every `literature_id` in the enriched parquet:

1. Resolve first-author surname + year + title → best PDF on disk.
2. `sha1(pdf.bytes)`. If `<corpus_cache>/<sha>.txt` already exists → **skip**
   (already extracted; enables resume).
3. Else `pdftotext` → write `outputs/validation/.fable_texts/<lit_id>.txt`.
4. Append `{lit_id, text_path, sha}` to the worklist.

Outputs (all under `outputs/validation/`, which is git-ignored):
- `.fable_texts/<lit_id>.txt` — materialised paper text (cap 120k chars, matching
  the validated prompt).
- `fable_corpus_worklist.json` — `[{lit_id, text_path, sha}, ...]` still to do.
- `fable_corpus_columns.json` — `[{name, description}, ...]` for the 166 cols.

Prints **resolvable / unresolvable / already-done** counts so the true N is known
before committing the burn. Idempotent: re-running only adds newly-resolvable or
un-cached papers.

### 2. Burn (Fable, via chained Workflows) — `scripts/validation/fable_corpus_burn.mjs`

Workflow's hard cap is **1000 agents per workflow run**, so the worklist is
**sharded into ≤900-paper chunks**; each shard is one Workflow invocation, passed
its slice as `args`. Within a shard, `parallel()` runs **one subagent per paper**
(concurrency auto-caps at `min(16, cores-2)` = 10 here). Each subagent:

1. `Read` its `text_path` (full paper text).
2. Decide, for the 166 columns, which the paper's **own study** (not
   references/background) supports; extract `study_country` / `study_region`.
3. `Write` a **present-only** cache file `<corpus_cache>/<sha>.txt` (line-based,
   see format) — listing only present columns. Absent = false by omission.
4. Return only `"OK <lit_id>"`.

**Why the subagent writes to disk (not returns data):** returning 166×900 label
values per shard would flood the orchestrator's context (megabytes/shard). The
subagent persists its own result; the Workflow returns only counts. The
line-based present-only format minimises both output tokens and JSON-escaping
fragility.

**Cache format** `<corpus_cache>/<sha>.txt`:
```
LIT: 12345
COUNTRY: Australia; New Zealand
REGION: Great Barrier Reef
gear_longline|0.90|caught on demersal longlines
d_trophic|0.85|stomach-content analysis of 40 individuals
...
```
Pipe-delimited `name|confidence|evidence`; evidence ≤80 chars, no pipes/newlines.

**Chaining:** the orchestrator (Fable session) launches shard 0; on completion
launches shard 1; etc. (~20 shards for 18k). If a night runs out, the next night
re-runs the pre-pass (skips done SHAs) and continues. Cache = single source of
resume truth.

### 3. Post-pass (local, no Fable) — `scripts/validation/fable_corpus_merge.py`

1. **Validate + purge:** parse every `<corpus_cache>/*.txt`; delete malformed
   ones (they become cache-misses and get retried next shard/night). Log purged.
2. Map `sha → lit_id` via the worklist; expand present-only → full 166 columns
   (absent = 0); attach `study_country` / `study_region`.
3. Write **`outputs/literature_review_fable.parquet`** — a NEW file with
   `literature_id`, the 166 Fable columns, geography, and a `fable_extracted`
   provenance flag. **Never overwrites** `literature_review_enriched.parquet`.
4. Emit `outputs/validation/fable_vs_rules_diff.csv` — per-column agreement /
   flip counts (Fable vs the regex columns) for review.

## Safety / resumability

- New-file writes only; the regex parquet and the validation-loop `.fable_cache`
  are untouched (corpus burn uses its own `.fable_corpus_cache/`).
- Cache keyed by PDF SHA-1 → fully idempotent and resumable; interruption loses
  at most the in-flight papers.
- Merge validates cache before trusting it; malformed entries self-heal by
  re-running.
- Pre-pass and merge are local (no Fable), safe to run any time.

## Out of scope

- Overwriting or merging into the rules parquet (kept separate until reviewed).
- Free-text species (`sp_*`) and other derived fields — user chose 166 + study
  geography only.
- A managed multi-night scheduler — chaining is orchestrated by the session; the
  cache makes manual restart cheap and safe.

## Runbook (see chat for exact go-command)

1. Pre-pass runs now (local) → worklist + text materialised.
2. User switches session model to Fable, says "go".
3. Orchestrator launches burn shards 0..N sequentially.
4. Each night until 12 Jul: re-run pre-pass (skips done) + continue shards.
5. When done (or on 12 Jul): run merge → `literature_review_fable.parquet` + diff.
