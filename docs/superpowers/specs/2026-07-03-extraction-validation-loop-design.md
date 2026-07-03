# Extraction Validation Loop — Design Spec

**Date:** 2026-07-03
**Author:** Simon Dedman (+ Claude)
**Status:** Design approved, spec under review
**Deadline context:** Coding pause at COP Tue 7 July 2026 (conference presentation Wed 8 July). This is the **foreground anchor** subproject; download acquisition, the Researcher Atlas, and SLM/RAG run as parallel background/worktree threads.

---

## 1. Purpose

The 123-column rule-based extractor (`scripts/extract_schema_columns.py`) has **never had its accuracy measured against human labels**. Every "fixed" claim to date rests on firing-count deltas and single-paper spot-checks. There is currently no number that can be put on a slide.

This subproject delivers:

1. **A measured accuracy figure** for the rule-based extractor (precision / recall / F1 per column) against human ground truth and an LLM-adjudicated silver set.
2. **A rule-improvement loop** that proposes and *auto-tests* concrete rule changes, showing accuracy before → after (the "watch it improve" narrative).
3. **An A/B viability verdict on LLM extraction** — Fable-vs-human accuracy, tokens/paper, and an extrapolated cost/time for a max 40,000-PDF corpus — piggybacked on the oracle pass at no extra extraction cost.

Primary output is a **conference slide / dashboard** (credibility slide); secondary output is an improved, branch-isolated rule set.

## 2. Key decisions (locked)

| Decision | Choice | Rationale |
|---|---|---|
| LLM's end-state role | **Rule-improvement engine** (keep the fast/free/auditable regex extractor); Fable acts as oracle + critic. Plus an **LLM-extraction A/B** run alongside. | Matches "iterate the rules"; preserves determinism/auditability; the A/B answers "should we switch?" with data. |
| Test set | **Gold + silver bridge.** 15 human-labelled papers = gold; ~300 stratified Fable-labelled = silver; Fable-human concordance on the 15 licenses Fable as the silver oracle. | Defensible headline (rules-vs-human) AND usable N for per-column stats. |
| Silver sample size | **300 papers** | Tighter per-column CIs incl. rare columns; Fable is cheap/fast enough. |
| Build scope for Tuesday | **Full loop (components 1–7)**, including auto-test improvement loop. | User wants both the number and the improvement narrative. |

## 3. Ground truth available (as surveyed)

- **~190 column-level human corrections** across **15 papers / 3 reviewers** on `origin/validation/A50*` branches, as JSON (`added[]`→value 1, `removed[]`→value 0), loadable as `(literature_id, column, human_value)` triples. Plus 140 schema-group ratings (coarse signal).
  - David Ruiz-García `A5009396914` (6 papers), Alex McInturf `A5078322786` (8), Elena Fernández-Corredor `A5027778174` (1).
- **David's 27 rule-change proposals** in `docs/schema_proposals/ruiz_garcia_validation_master.xlsx` (sheet `Validation_Rules`) — prose rule feedback, not per-column labels.
- `extraction_review_comments.xlsx` is a **blank template** — not a correction source.
- Known FP/FN patterns already catalogued in `docs/schema_proposals/extraction_quality_issues.md` and `2026-04-20_validation_synthesis.md`.

## 4. Components

Each is a focused unit with a defined input/output, independently runnable.

### 4.1 Ground-truth loader
- **In:** the 3 JSONs on `validation/A50*` branches (via `git show <branch>:<path>` or fetch), `ruiz_garcia_validation_master.xlsx`.
- **Out:** `outputs/validation/gold_labels.csv` (`literature_id, column, human_value, reviewer, group_rating`), `outputs/validation/rule_backlog.csv` (David's 27 + provenance).
- Idempotent; re-runnable as more validation PRs land.

### 4.2 Sample selector
- **In:** `outputs/literature_review_enriched.parquet`, `schema_extraction_evidence.csv`, gold list.
- Stratified across disciplines **and** the 123 columns (ensure low-prevalence columns are represented); deliberately mixes fired vs not-fired papers to expose false negatives. Deterministic seed. Includes the 15 gold papers.
- **Out:** `outputs/validation/validation_sample.csv` (~300 + 15 gold, flagged `tier=gold|silver`).

### 4.3 Fable oracle extractor
- **In:** each sample PDF's extracted text + section map (reuse `extract_schema_columns.py` text/section pipeline), schema column definitions (name + description + current rule terms).
- Structured output per column: `present` (bool), `evidence_quote` (str), `confidence` (0–1).
- Cached by PDF SHA-1 (mirror the OCR cache pattern); per-call token counts logged.
- **Out:** `outputs/validation/fable_labels.parquet`, `outputs/validation/fable_token_log.csv`.

### 4.4 Scorer
- **Bridge:** Fable-vs-human on gold 15 → agreement %, per-column where labels exist.
- **Headline:** rules-vs-human on gold 15.
- **At scale:** rules-vs-Fable on silver 300 → per-column precision / recall / F1, FP & FN rates.
- **A/B:** per column, rules vs Fable vs human accuracy + Fable tokens; 40k-corpus cost/time extrapolation caveated by OCR share and PDF-length distribution.
- **Out:** `outputs/validation/metrics.parquet`, `outputs/validation/ab_viability.md`.

### 4.5 Diagnosis + proposal engine (Fable)
- For each column where rules disagree with Fable/human, feed the offending papers' evidence + current rule (`docs/validate/assets/rules.json`) to Fable → specific proposed change (add/remove terms, threshold, anchor, section-weight) + rationale.
- Merge with David's 27 proposals → single ranked backlog.
- **Out:** `outputs/validation/rule_proposals.csv` (ranked; `column, change_type, detail, rationale, source=fable|david, predicted_impact`).

### 4.6 Auto-test loop
- For each proposal: apply to a **copy** of the rule set, re-run the extractor on the **sample only** (incremental/fast path), re-score, keep if F1 improves without regressing other columns past a guard threshold, else reject.
- **Gold-15 rules-vs-human score reported alongside as the un-gameable overfit check.**
- Log every change + accuracy delta.
- **Out:** `outputs/validation/improved_rules/` (branch-isolated), `outputs/validation/improvement_log.csv`.
- Orchestration: a `Workflow` (propose → test → keep/reject per rule, in parallel) is the natural fit if the sequential loop is too slow.

### 4.7 Dashboard / figures
- Per-column P/R bars (worst→best); before/after improvement; rules-vs-LLM-vs-human A/B + cost box; top FP/FN patterns with example quotes.
- Built to the `dataviz` skill. R/ggplot figures for the pptx **plus** an HTML version.
- **Out:** `outputs/validation/figures/*.png`, `outputs/validation/dashboard.html`.

## 5. Data flow

```
gold JSONs + David xlsx ─┐
                         ├─► sample selector ─► Fable oracle (cached, token-logged)
stratified corpus ───────┘                              │
                                                        ▼
                          scorer (rules vs Fable vs human) ─► metrics + A/B/cost
                                                        ▼
                    diagnosis (Fable) + David backlog ─► ranked rule proposals
                                                        ▼
             auto-test loop (apply→re-extract sample→re-score→keep/reject)
                                                        ▼
                              dashboard / ggplot figures ─► slide
```

## 6. Rigor / guards

- Fable output cached by PDF hash → cheap, repeatable, near-deterministic reruns.
- Accepted rule changes stay on a **branch**; the production extractor is not overwritten until the batch is user-approved.
- Silver overfitting guarded by reporting the gold-15 rules-vs-human score alongside every loop iteration.
- Token cost logged exactly; 40k extrapolation explicitly caveated (OCR %, length distribution, model/pricing snapshot).
- Language/tooling: **R for the figures/dashboard**; Python for the Fable/extraction automation (per project convention).

## 7. Out of scope (explicit)

- Re-labelling the full parquet from corrections (merge-back pipeline) — future work.
- Expanding human ground truth via more coauthor review before Tuesday (slow; the silver bridge removes the dependency). May run as a parallel team-delegation thread but is not on the critical path.
- Switching the production pipeline to LLM extraction — the A/B **informs** that decision; it does not execute it.

## 8. Success criteria

1. A defensible headline accuracy figure (rules-vs-human on gold, contextualised by rules-vs-silver at N=300).
2. Per-column precision/recall/F1 table for all columns with silver coverage.
3. `ab_viability.md`: Fable accuracy vs rules, tokens/paper, 40k-corpus cost/time verdict.
4. `improvement_log.csv` showing ≥ the first accepted rule changes with measured before→after deltas.
5. Conference-ready figures (pptx) + HTML dashboard.
