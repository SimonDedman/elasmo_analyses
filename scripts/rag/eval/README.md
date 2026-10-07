# Retrieval evaluation (scripts/rag/eval/)

Phases 1 and 2 of `docs/superpowers/specs/2026-08-06-retrieval-evaluation-design.md`:
a question set with relevance labels, and a harness that measures how well the
query interface's retrieval finds the right papers. **Every label here is silver**
(written by Claude, 2026-10-07) until Simon or a co-author adjudicates it.

## Files

| File | Purpose |
|---|---|
| `questions.jsonl` | The question set (versioned). One JSON object per line: `id`, `category` (known_answer / exact_term / assessor / unanswerable), `question`, `relevant_ids` (literature_ids), `provenance`, `status` (silver / needs_judgement / adjudicated / dropped). Optional: `partial_ids`, `judgements`, `term`, `expected_behaviour`, `previous_wording`. |
| `run_eval.py` | Loads an index in-process (never the server), runs every question through the configs, writes `outputs/rag_eval/<date>_<index>_<config>.json` and `<date>_report.md`. |
| `build_adjudication.py` | Pools each config's top-10 papers per question into `outputs/rag_eval/<date>_question_adjudication.xlsx` (Info tab, one `judgements` tab, a `questions` tab). Already-judged pairs are never served again. |
| `apply_adjudication.py` | Reads the workbook's decisions back into `questions.jsonl`. |
| `count_term_docs.py` | Lists papers whose body text contains a term verbatim (for writing exact_term questions). |
| `tests/test_rag_eval.py` | Metric, pooling and round-trip tests, plus a run against `outputs/rag_test`. |

## The question set (85)

- **known_answer (30)**: one paper each, by construction: the 15 human-gold papers and 15
  silver-tier papers (seed 20261007) from `outputs/validation/validation_sample.csv`. Each
  question was written from the abstract without the title's distinctive words; the
  abstract sentence it rests on is in `provenance`.
- **exact_term (20)**: a rare species binomial, place, gear, or method name. `relevant_ids` =
  every indexed paper whose text contains the term verbatim (all have 4 to 10, so the sets
  are complete for the live index; totals are in `provenance`).
- **assessor (20)**: what a Red List assessor or fisheries manager would type. No labels yet.
- **unanswerable (15)**: in-domain vocabulary, believed outside the corpus (the spec's CRISPR
  probe and similar). Expected behaviour: the badge says `unresolved`. Not verified exhaustively.

## Running

```bash
cd "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
PY=/home/simon/.venvs/fashion-clip/bin/python
# smoke run (200-paper test index, a few seconds)
$PY scripts/rag/eval/run_eval.py --index-dir outputs/rag_test --limit 6 --out-dir /tmp/eval_smoke
# full run on the live index (~3 GB RAM; about 10 minutes, mostly the cross-encoder)
systemd-run --user --scope -p MemoryMax=7G $PY scripts/rag/eval/run_eval.py --index-dir outputs/rag \
    --fts-db <an fts.sqlite built from that index's chunks_meta.jsonl>
python3 scripts/rag/eval/build_adjudication.py --date <run date> --index-name rag
```

Configs: `vector` (FAISS top-20, cosine order), `vector_ce` (FAISS top-30, cross-encoder
rerank, 10 shown), `hybrid_ce` (FAISS + BM25 fused by `hybrid.py`, top-30, rerank, 10 shown;
runs only when an `fts.sqlite` is available, by default `<index-dir>/fts.sqlite`). A rebuilt
index that ships its own `fts.sqlite` needs no `--fts-db`. `--configs vector,vector_ce`
restricts the run. The badge is computed with `query.claim_strength` on the top 8 reranked
chunks (the server's `top_k` default) and on the top 10.

Metrics per category: hit@1/5/10/20, hit@shown, P@10, R@10, nDCG@10 (partial = gain 0.5), MRR,
each strict and duplicate-aware (a retrieved id sharing a source PDF SHA-1 with a relevant id,
per `outputs/validation/fable_texts_manifest.csv`, counts). Unanswerable and assessor questions
contribute badge statistics only until they carry labels.

## Adjudication loop

1. Open `outputs/rag_eval/<date>_question_adjudication.xlsx`, follow the Info tab: `relevant` =
   Y / N / partial for each (question, paper) row; optionally reword or drop questions.
2. `python3 scripts/rag/eval/apply_adjudication.py <workbook> --judge SD` (`--dry-run` first to
   see the counts). Y adds to `relevant_ids`, partial to `partial_ids`, N removes; every
   decision is kept in the question's `judgements`. A copy of the old file goes to
   `questions.jsonl.bak`.
3. Re-run `run_eval.py`, then `build_adjudication.py` again: only unjudged pairs (new
   candidates from changed configs, reworded questions) appear.

## Honest limits

- The questions are author-written (by the builder's assistant), so they are shaped by what
  the corpus holds and by abstract wording. The spec's independence concern stands until
  outside assessors contribute questions.
- Known-answer questions have one relevant paper, so P@10 is at most 0.1 and R@10 equals hit@10;
  other papers that answer them count as misses until adjudicated.
- Exact-term relevance is "contains the term", which rewards term matching rather than
  answering, and misses spelling or case variants (e.g. LiDAR).
- 30 and 20 questions per scored category: one question moves a rate by 3 to 5 points.
- The live index (Sept 2026 build) holds 4,971 literature_ids whose indexed text is identical to
  another id's (1,953 groups, measured 2026-10-07 by hashing chunks_meta.jsonl); use the
  duplicate-aware tables for it, and re-run on the deduplicated rebuild.
