# Retrieval evaluation for the database query interface

**Created:** 2026-08-06
**Status:** design, not started
**Owner:** unassigned (see "How vital is a specialist?" below)
**Relates to:** [`docs/LLM/rag_prototype_status.md`](../../LLM/rag_prototype_status.md)
("Next steps to scale", item 8), the extraction validation loop
([`2026-07-03-extraction-validation-loop-design.md`](2026-07-03-extraction-validation-loop-design.md)),
and the web front-end
([`2026-07-11-rag-schema-filters-web-frontend-design.md`](2026-07-11-rag-schema-filters-web-frontend-design.md)).

---

## Why this document exists

The extraction side of the project is measured. There is a human gold set, an
LLM-adjudicated silver set, macro-F1 reported per column, a bridge between the
two, and a rule-improvement loop that automatically rejects changes which do not
improve F1. Anyone can ask "how good is the extractor?" and get a number with a
stated method behind it.

The database query interface has none of that. It is built, it runs over the
full corpus (papers and chunks per the canonical figures in
[`docs/core/pipeline_overview.md`](../../core/pipeline_overview.md)), it has a
web front-end with schema pre-filters, and it produces a claim-strength badge
that users will read as a quality signal. **Nothing about its retrieval or
answer quality has been measured.** The two threshold constants that drive the
badge, `CE_FLOOR = 0.0` and `CE_STRONG = 1.0` in `scripts/rag/query.py`, are
calibrated against exactly two probes: one in-domain question family, and one
deliberately out-of-domain probe ("CRISPR gene editing protocols for shark
embryos").

This was already known and written down, as item 8 of "Next steps to scale" in
the RAG status doc, alongside an honest limitations section. What it lacked was
a place on the project's actual to-do list and a worked plan. This document is
that plan. The gap is a backlog item that was never scheduled, not a blind spot.

**Why it matters more now than it did in July.** Two things changed. The
interface moved from a 300-paper prototype to the full corpus with a web
front-end, which means it is close to being put in front of other people; an
unmeasured badge that says "well-supported" to a Red List assessor is a
different object from the same badge in a local prototype. And the project is
being written into grant proposals where the query interface is a headline
deliverable, so any number quoted about it has to exist.

---

## What is actually missing

Six things, roughly in order of how much they matter.

**1. A gold-standard question set.** There is no set of questions with known
correct answers or known relevant papers. Without it, none of the rest can be
computed. This is the blocking dependency and the most labour-intensive item,
because it needs domain experts, not engineering.

**2. Retrieval metrics.** Standard and uncontroversial once (1) exists:
precision@k and recall@k, nDCG@10, MRR, and "does the known-relevant paper
appear in the top k at all". These answer "is the right evidence being found?"

**3. Threshold calibration.** With a labelled question set, `CE_FLOOR` and
`CE_STRONG` become fitted quantities with a stated operating point (e.g. chosen
to hold false "well-supported" labels under some rate), rather than two points
on a line. The `CE_MIN_CONCORDANT_PAPERS = 3` rule needs the same treatment.

**4. Answer-level (generation) evaluation.** Distinct from retrieval, and
currently entirely unmeasured: does each generated sentence actually follow from
the chunk it cites (groundedness/faithfulness), are the citations attached to
the right sentences, and what is the rate of unsupported statements? The
`sharkoracle_context.md` persona already demands citation-per-sentence, which
makes this measurable sentence by sentence.

**5. Ablations.** Does the cross-encoder rerank actually help, and by how much?
Does hybrid BM25-plus-vector beat pure vector on exact-term queries (species
binomials, gear acronyms)? Does section-aware chunking help? Each of these is
currently a plausible improvement on the roadmap with no evidence attached.
Running them without a metric is guesswork.

**6. Out-of-domain and negative handling.** The CRISPR probe was the right
instinct applied once. It needs to become a held-out set of questions the corpus
genuinely cannot answer, so "unresolved" can be scored as a correct behaviour
rather than assumed.

**Not in scope, but worth naming:** claim-strength is agreement-of-topic, not
agreement-of-claim. Two papers with opposite conclusions both count as support.
Fixing that needs an entailment pass and is tracked separately as item 6 of the
RAG next-steps. Evaluation and that fix are independent; do evaluation first, so
the fix can be shown to help.

---

## Proposed approach

### Phase 1: build the question set (the hard part)

Target 80–120 questions, which is small by IR standards but adequate for a
domain corpus and realistic for expert time. Compose it deliberately rather than
by convenience sampling:

- **Known-answer questions** derived from papers already in the human gold set,
  where the relevant paper is known by construction.
- **Assessor-shaped questions**, written by the people who would actually use
  this: what a Red List assessor or a fisheries manager types in. These carry
  the most weight for broader-impact claims and are the ones most likely to
  expose retrieval failures the team would not think to test.
- **Exact-term questions** (species binomials, gear acronyms, technique names)
  which are the predicted weak point of pure semantic retrieval and the
  motivating case for hybrid search.
- **Held-out unanswerable questions**, in-domain in vocabulary but outside what
  the corpus covers, to score the "unresolved" path.

Relevance judgements come from the same route the extraction gold set used:
domain co-authors adjudicate. Pool candidates from several retrieval
configurations before judging, so the judgements are not biased toward whichever
system produced them.

### Phase 2: harness and baseline

A script that runs the question set through the retrieval stack, computes the
metrics, and writes a dated report, mirroring the extraction validation loop's
structure so results are comparable across rounds. Report the baseline honestly,
including the cases it fails.

### Phase 3: calibrate, ablate, iterate

Refit the thresholds on the labelled set. Run the ablations. Adopt changes only
where the metric improves, reusing the extraction loop's accept/reject
guardrail, which is the pattern that has already proved itself here.

---

## How vital is hiring a specialist?

Direct answer: **not vital to do the work, valuable for independence and speed,
and worth the most as external credibility in a CISE-led grant competition.**

**The case that it is not vital.** The evidence is what has already been built
solo. The extraction validation framework is exactly this problem in a different
domain, and it was done properly: a stratified sample with a deterministic seed,
a human gold set and an LLM silver set with a bridge between them, macro-F1
rather than accuracy on imbalanced binary columns, precision and recall reported
separately so the failure mode (under-detection) could be diagnosed, and an
automatic guardrail that rejected a proposed change which degraded its column.
That is competent evaluation methodology. Retrieval evaluation is the same
shape with different metrics, and the metrics themselves are standard and well
documented. The claim "nobody on the team can do this" is not true and should
not be written into a proposal.

Further, the one existing quality bug in the query interface was found
in-house, by running an out-of-domain probe on the suspicion that high cosine
similarity was over-reporting. That is the instinct the whole evaluation
workpackage systematises.

**The case for bringing someone in anyway.** Three arguments, in descending
strength.

- **Time, not capability.** Phases 1–3 are weeks of work, and phase 1 is
  unavoidably slow because it depends on expert adjudication. It competes
  directly with extraction, acquisition, and the grey-literature pipeline for
  the same single pair of hands. This is the strongest argument and it is an
  argument for funded time, not necessarily for seniority.
- **Independence.** Evaluating your own system is a known weak position: the
  question set tends to be shaped, unconsciously, by what the system already
  does well. An outside evaluator writes questions the builder would not think
  to ask. This is a real methodological gain, not just optics.
- **Reviewer credibility.** A CISE-led panel will contain people who do
  information retrieval for a living, and they will look for exactly these
  metrics. Having a named person whose track record is benchmark design answers
  that before it is asked.

**Recommendation.** Budget an IR-literate postdoc or PhD student as the primary
route, working to a protocol rather than inventing one, with domain co-authors
supplying relevance judgements and the technical lead building the harness.
That covers time and most of independence at a fraction of a co-PI's cost.
Recruit a named co-PI only if someone appears who genuinely brings a benchmark
or evaluation track record, and if so give them a real workpackage to own.
Do not recruit a figurehead: a co-PI with nothing to do is visible to a panel
and costs budget that the actual work needs.

**Sequencing.** This work should start before the proposal is written, not
after it is funded. Even a partial result, a question set built and a baseline
measured, converts the single largest unquotable claim in the bid into a
reported number, and turns the workpackage from "we will evaluate" into "we
have begun evaluating and here is round one". That is the same move that made
the extraction section of the proposal strong.

---

## To-do

- [ ] Draft the question set specification (categories, target counts, judging protocol)
- [ ] Recruit adjudicators from existing gold-set reviewers
- [ ] Build 80–120 questions with pooled relevance judgements
- [ ] Write the evaluation harness and produce a dated baseline report
- [ ] Refit `CE_FLOOR`, `CE_STRONG`, `CE_MIN_CONCORDANT_PAPERS` against the set
- [ ] Ablate: cross-encoder rerank on/off, hybrid BM25, section-aware chunking
- [ ] Add groundedness and citation-correctness scoring for generated answers
- [ ] Feed results back into the grant narrative
