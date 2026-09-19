# Topic review pages: experts judge a concept's paper list, the rules are fitted to their judgement

**Date:** 2026-09-19
**Status:** DRAFT for Simon's review. Written overnight at his request ("plan this, make a
mockup of a review page/pages for the fisheries topic, propose questions to me... mock up
multiple scenarios"). The mock-ups are built and run on the real corpus; nothing in the
production extraction, the validation pipeline, or the Cloudflare Worker has been touched.
**Branch:** `pdf-dedupe-hardlinks`.
**Origin:** Simon's discussion with David Ruiz-García (notes pasted 2026-09-18), and David's
keyword workbook `docs/2026-09-10_FisheriesApproach_keywords_DRG.xlsx`.
**Open the mock-ups:** `docs/topic_review/index.html` (scenario cards at the top).

## Problem

The per-author validation pages ask each author whether their own papers are coded correctly.
That gives depth on a few papers and nothing on a concept as a whole: nobody has looked at
"every paper flagged `d_fisheries`" and said which are right. Rule changes are therefore argued
from anecdotes, each change needs a corpus re-run to see its effect, and the people best placed
to judge a concept (its subject experts) have no surface to do it on.

Simon's idea: order every paper that mentions a concept's keywords from most to least
qualifying. Somewhere down that list is the threshold line. The top is almost certainly
correctly IN and the bottom almost certainly correctly OUT, so the expert's time belongs on the
papers near the line. Give them fast bulk selection, tie each judgement to the expert, and the
resulting list becomes a gold standard against which rules can be fitted by search instead of
tuned by hand.

## Measured before designing (2026-09-19, regenerate with the scripts below, do not hand-edit)

Sources: `outputs/topic_review/fisheries/{coverage.json, control.txt, measured_2026-09-19.txt}`.
Topic vocabulary: 40 live columns (`d_fisheries`, eight fishing `pr_` columns, all 28 `gear_`,
`imp_cpue`, `imp_post_release`, `imp_mortality`) plus David's 66 proposed subcategories: 671
distinct keywords and anchors.

- **Coverage of the count pass.** 31,772 corpus rows in scope; 21,959 with readable PDF text;
  9,791 with no PDF resolved; 22 with a PDF but no text. 26 minutes on 10 cores, and the
  section-labelled text is now cached (394 MB), so new vocabulary is a re-count, not a re-read.
- **Positive control.** Re-scoring the 40 live columns from the stored counts reproduces the
  production evidence table on 55,256 of 55,288 paper-column decisions (99.94%); the weakest
  column is `gear_trawl_beam` at 99.45% (181 compared), `d_fisheries` is 99.95% (5,623). The
  browser's scoring matches the Python builder's exactly on all eight featured rules
  (`review.html?selftest=1`). Papers with text here but no production evidence rows: 1,335, of
  which 346 have PDFs filed in the last 60 days (INFERRED cause for the rest: no English keyword
  in any column; not checked).
- **`d_fisheries`, suspect-text rows excluded.** 7,781 papers mention a keyword; 2,581 qualify.
  2,893 of the 7,781 score below 0.5 despite mentioning a keyword, because no mention sits near
  a shark or ray term or all mentions fall in text the section labeller could not place (weight 0).
- **The margin is wide.** 1,905 papers lie within 0.5 of the line, 3,326 within 1.0, 6,425 within
  1.5. Scores move in steps of 0.5 and the threshold is 2, so most of the list is "near".
- **Against Fable's silver labels** (1,602 papers Fable read, suspects excluded; Fable was told to
  flag a column only if "the study itself did/used/covered it"): precision 73.7%, recall 54.4%,
  F1 62.6% (tp 278, fp 99, fn 233, tn 992). 44 Fable-IN papers contain none of the 13 keywords.
- **The premise is half right.** Share of Fable-read papers that Fable calls fisheries, by rule
  score: under 0.5, 37%; 0.5 to 1.49, 40%; 1.5 to 2.49, 50%; 2.5 to 4.49, 73%; 4.5 to 9.99, 87%;
  10 and over, 96%. The top of the ladder can be assumed IN. The bottom cannot be assumed OUT:
  the live score orders the low end poorly. This is why scenario C spot-checks both ends, and why
  "all below is OUT" stores `assumed` labels that the fitting never uses.
- **Per-keyword damage is visible.** `retention` is the deciding keyword for 256 qualifying
  papers (urea retention, sperm retention, chromatographic retention time); of the 23 Fable read,
  21 are not fisheries. `bycatch` decides 730 (72 IN / 44 out among Fable-read); `discard*` 298
  (15 / 17); `fisheries management` 167 (31 / 9).
- **Independent check.** A fresh-context agent recomputed these figures from the raw files with
  its own code. It confirmed the Fable comparison, the 44 unreachable papers, and the counts of
  mentioning papers; it corrected the `retention` split above (I had omitted the confidence
  filter: 5 / 18 became 2 / 21). Its three other disagreements traced to its own error: it added
  the keyword `discards`, which belongs to `pr_bycatch`, into the `d_fisheries` score. Checked on
  its example paper (34527): the feature table scores 1.0, production says 1, OUT in both.
- **The optimiser, on the same silver labels** (869 labelled papers with a keyword hit, 467 IN,
  plus 45 unreachable): live rule F1 62.5%; proposed rule 76.3% fitted, **73.8% on five held-out
  folds**. Proposed changes: threshold 2 to 1; proximity off; methods and results weights 1 to
  0.5; unplaced-text weight 0 to 1; drop `discard*`; drop `retention`. 46 ms in the browser. Best
  single changes: proximity off +6.0 points, unplaced-text weight 0 to 1 +4.5, threshold 2 to 1
  +4.1. Silver labels: the mechanism is demonstrated, the size of the gain is indicative.
- **Rounding.** `round()` is half-to-even, so 1.5 passes a threshold of 2 while 2.5 fails a
  threshold of 3. Across the 40 live columns, 1,146 of 27,599 qualifying decisions would differ
  under ordinary half-up rounding (`imp_cpue` 165, `gear_demersal` 148).
- **Workload.** Summed margins (within 0.5 of the line) are in the hub table. With the earlier
  1.5 band: live columns 43,609 paper-judgements, 17 of 40 columns over 1,000 each; proposed
  rules 29,338, 35 of 66 under 100 each. David's broadest rule, "Spatial overlap: Distribution"
  (`distribution, occurrence, presence...` with anchors `habitat, area, region...`), is
  mentioned by 14,042 papers and 8,236 qualify: too generic to discriminate as written.
- **Existing expert labels are almost nil:** 18 gold labels across the topic's columns from
  four author validations. Everything above rests on Fable silver until a champion labels.
- **Page weight:** about 20 MB of static data for the topic (counts 6.5 MB, paper metadata 4.2 MB,
  snippets for eight featured rules 9 MB). Acceptable for an expert tool; snippets for all 106
  rules would need lazy per-paper loading.

## The model everything rests on

`extract_schema_columns.py::_match_column` decides a column like this:

    score  = round( sum over keywords t, sections s of  n[t, s] x W[s] )      (Python round: half to even)
    n[t,s] = mentions of t in section s, counted only if a shark or ray term sits within
             one sentence either side (for the 19 columns in PROXIMITY_CHECK_COLUMNS)
    IN     = score >= threshold  AND  (the rule has no anchors OR any anchor occurs anywhere)

The evidence table keeps only the totals, which is why a rule change has needed a re-run. The
design stores `n[t, s]` instead (both the proximity-filtered and the raw count) for a
**superset vocabulary**: every keyword and anchor of every live column in the topic plus every
keyword and anchor the champion has proposed. With that table:

- threshold, section weights, per-keyword weights, keyword on/off, the proximity switch, the
  anchor gate, and the rounding rule are all re-scored in the browser, instantly;
- a proposed rule that has never been run (David's 66 subcategories) can be scored on the whole
  corpus the moment it is written, from the same table;
- accepting a rule change for a column means recomputing that column from the table, which
  takes seconds. The feature table becomes the extraction for these columns.

The one thing the table cannot answer is a keyword nobody counted. `build_topic_features.py`
therefore also writes a section-labelled text cache (`outputs/topic_review/text_cache.sqlite`),
so a re-count for new vocabulary reads cached text and never re-runs `pdftotext`.

## Components

| Unit | What it does | Depends on |
|---|---|---|
| `data/topic_review/<topic>.json` | Topic definition: live columns in scope, proposed rules (keywords, anchors, threshold), featured rules, champion. | hand-edited, or generated from a champion's workbook |
| `scripts/build_topic_features.py` | One corpus pass: per paper, per vocabulary term, per section, raw and proximity-filtered counts. Reuses the extractor's own PDF resolution, text extraction, section labelling, term compiler, and elasmobranch pattern. Writes `features.jsonl`, `vocab.json`, `coverage.json`, and the text cache. `--control` re-scores every live column from the stored counts and compares with the production evidence table. | `extract_schema_columns.py` |
| `scripts/build_topic_review_pages.py` | Turns the feature table into static data files: `meta.js`, `papers.js`, `counts.js`, `seed_labels.js`, and per-rule snippet files read from the text cache. Computes the per-rule workload table. | the feature pass, corpus parquet, Fable cache, `gold_labels.csv`, suspects list |
| `docs/topic_review/review.html` | The review application (one file, no dependencies, works from `file://`). Ladder view, margin-queue view, rule lab, impact panel, optimiser, export and import. `?topic=&rule=&view=&mode=&blind=&who=`. | the data files |
| `docs/topic_review/index.html` | Topic hub: scenario links, instrument check, every rule with its workload, champion and checker columns. | `meta.js` |
| (build phase) Worker + Action route | `topic-review-submitted` event, stored as `validations/topic/<topic>/<rule>/<reviewer>_<timestamp>.json` on `main`. | existing `elasmo-validate` Worker and `receive-validation.yml` |
| (build phase) `scripts/validation/load_topic_labels.py` | Flattens submitted topic labels into the same `(literature_id, column, human_value, reviewer, how)` table the validation loop already scores against. | `scripts/validation/score.py` |

## The scenarios mocked up

All eight open from the hub and share one data set, so they can be compared directly.

- **A. Ladder with the rule lab.** The list Simon described: score order, the threshold drawn
  as a bar inside the list, margin band tinted, the page opening at the line. Click, shift-click,
  ctrl-click, drag, arrow keys, space; `I` / `O` / `U` / `X`; "all above is IN" (`A`), "all below
  is OUT" (`B`); undo for any action of any size. The Rule tab edits the rule and the line moves
  as you type; "moved by my rule edits" filters to exactly the papers that crossed.
- **B. Judge-only ladder.** Same list, rule lab hidden (`mode=judge`). The expert judges; we fit.
- **C. Margin queue.** One paper per card, closest to the line first, keys `I` / `O` / `U`.
  Every fifth card is a random paper from well above or well below the line, and the header
  keeps a running tally of those spot checks. "The top is surely IN" becomes a measured claim
  with a stopping rule instead of an assumption.
- **C2. Blind margin queue.** As C with the score, the stratum, and the Fable verdict hidden.
- **D. Optimiser.** Coordinate-descent search over threshold, section weights, keyword on/off
  (optionally keyword weights, proximity, rounding), a small penalty per change so proposals stay
  close to the current rule, five-fold held-out accuracy reported beside the fitted accuracy, and
  a single-change leaderboard ("drop `retention`: +x F1"). "Load into the editor" draws the
  proposed line on the ladder.
- **E. A rule edit and what it moves.** A worked example of the instant-update requirement.
- **F. A proposed rule that has never been run** (David's "Capture: CPUE").
- **G. Second reviewer.** Export, switch reviewer, import, filter to "reviewers disagree".

### Decisions built into the mock-ups (each is reversible; the questions below ask about them)

1. **Two kinds of label.** A label made on one paper, or on a selection of 25 or fewer, is stored
   as `inspected`. "All above / all below" and any larger selection is stored as `assumed` and
   drawn with a dashed pill. Accuracy is reported for inspected labels alone and for both. An
   assumed label is a statement about the list, never evidence about the paper, and the optimiser
   should not be allowed to congratulate itself on labels that were derived from its own score.
2. **Bulk actions fill, they do not overwrite**, unless "overwrite" is ticked.
3. **The list includes every paper with at least one keyword mention**, below the line as well as
   above it, as David's notes asked.
4. **Suspect-text papers are hidden by default.** The extractor's borrowed-PDF bug
   (`project_extraction_borrowed_pdf_bug`) means 1,471 rows carry text from a different paper by
   the same first author and year; an expert shown that title beside that evidence would be
   judging nonsense. They are flagged, excluded from accuracy and from the optimiser, and can be
   shown with a tick box.
5. **Fable's corpus reads are shown as silver labels** and named as such everywhere. They are the
   only label source that covers papers with no keyword hit, which makes them the only current
   handle on recall.
6. **The ladder opens at the line**, not at the top.

## What the reviewer is judging

The unit of judgement is the **concept**, written down, not the rule. Before anyone labels, the
champion writes two or three lines per concept: what counts, what does not, and two example
papers each way. The page shows that text above the list at all times. Without it, two reviewers
will disagree about "fisheries" for reasons that have nothing to do with the papers, and labels
collected before the definition changes are wasted.

## Workflow

1. Simon and the champion agree the topic's scope and split: which live columns, which proposed
   rules, and which of those are worth a gold list at all (see the workload table on the hub).
2. The champion writes the concept definitions. `build_topic_features.py` runs once for the
   topic's vocabulary (about 20 minutes unattended for the whole corpus; seconds thereafter).
3. Primary reviewer works the margin (scenario A or C), with spot checks above and below.
4. Checker reviews the primary's `unsure` papers plus a random sample of the rest; conflicts are
   resolved in the "reviewers disagree" view. (Alternative: two independent full passes. Costs
   double, gives an agreement statistic. Question 7.)
5. We run the optimiser on the inspected labels, review the proposed diff, and accept or reject.
   Accepted rules are written to `extract_schema_columns.py`, the column is recomputed from the
   feature table, and the headline figures are regenerated per `feedback_corpus_figures_sync`.
6. The labels join `gold_labels.csv` and the validation dashboard's per-column accuracy.

## Submission and storage (build phase, not built)

Reuse the per-author route: browser to `elasmo-validate` Worker to `repository_dispatch` to an
Action that commits JSON to `main` (the July fix: no pull request). Two constraints found while
reading it:

- GitHub caps a `repository_dispatch` payload at about 64 KB. A topic list is thousands of
  labels; at roughly eight bytes per label a full `d_fisheries` list fits, but only just, so the
  page submits in chunks of 3,000 labels and the Action appends.
- The Action's file naming expects an OpenAlex author id. Topic submissions need their own event
  type and path so the two never collide.

Until that exists the mock-ups keep labels in the browser (`localStorage`) with Export / Import
as JSON, which is also the fallback if the Worker is down.

## Error handling and honesty rules

- "Not read" is never "OUT". Papers with no PDF or no text are counted on the hub and absent
  from the lists; they are not negatives.
- Every accuracy figure names its label source and its n. Silver is never called gold.
- Accuracy from labels made only on keyword-hit papers is blind to missed papers. The page says
  so beside the table, and reports the count of labelled-IN papers no keyword reaches.
- The optimiser's headline is the held-out figure. The fitted figure is shown beside it so the
  gap is visible.
- The hub shows the positive control (page scoring against production extraction) on every build.

## Testing

- `build_topic_features.py --control`: re-scored live columns against the evidence table.
- `review.html?selftest=1`: the browser's scoring against the Python builder's, per featured rule.
- Build-phase unit tests: label chunking, the Action's append, `load_topic_labels.py` on a
  fixture, and a test that an `assumed` label can never enter the inspected-only accuracy.

## Questions for Simon

Each has my recommendation, so "agree" is a complete answer.

1. **Is the goal a gold sample or a corrected list?** A sample (a few hundred stratified,
   inspected labels per concept) is enough to fit and measure a rule, and costs about two hours.
   A corrected list (every margin paper read, expert label overrides the rule for that paper) is
   1,905 papers for `d_fisheries` alone. *Recommend:* sample by default; corrected list only for
   the handful of concepts a sub-paper depends on. Expert labels always override the rule for the
   papers they cover.
2. **Which page do reviewers get?** *Recommend:* C2 (blind margin queue) for the labels that
   count, because A's ordering and Fable flags steer the judge towards the machine's opinion;
   A (ladder with rule lab) for champions and for us, to explore and to sanity-check proposals.
   B adds little over A.
3. **May assumed (bulk) labels enter the gold standard?** *Recommend:* no. Keep the buttons,
   since they are useful for clearing a list, but fit and score on inspected labels only, and let
   the random spot checks carry the evidence about the top and bottom.
4. **How do we measure recall?** Keywords cannot find what they miss, and neither can labels made
   on keyword hits. Options: (a) a random sample of 50 zero-hit papers per concept in the queue;
   (b) Fable reads of the rest of the corpus (about 18,000 more papers of your Max allowance);
   (c) accept unknown recall. *Recommend:* (a) now, (b) only where it is already on disk.
5. **What may the search change?** Threshold, section weights, and dropping keywords are on by
   default. Per-keyword weights, the proximity switch, and rounding are off. Section weights are
   currently shared by every column with the same prefix, so a per-column weight is an extractor
   change. *Recommend:* allow per-column overrides only when the held-out gain is at least three
   points of F1 on expert labels, to keep rules explainable.
6. **Replace half-to-even rounding?** 1,146 decisions hinge on it and nobody chose it.
   *Recommend:* compare the unrounded score with the threshold, decided per schema when its
   columns are next re-fitted, never as a silent global change.
7. **Two independent reviewers, or primary plus checker?** *Recommend:* primary plus checker
   (the checker sees the primary's `unsure` papers and a 10% random sample), with two independent
   passes only for the two or three headline concepts, where an agreement statistic is worth
   quoting.
8. **Who champions fisheries, and how is it split?** 106 lists is too many. *Recommend:* David
   champions; start with `d_fisheries`, `pr_bycatch`, `imp_cpue` against his "Capture: CPUE",
   `imp_post_release` against his PRM group, and `gear_longline`; decide the rest from the hub's
   workload table after one concept has been timed for real.
9. **What happens to David's 66 subcategories?** New schema (say `fx_`), or merged into existing
   columns where they overlap (his CPUE vs `imp_cpue`, his PRM vs `imp_post_release`)?
   *Recommend:* merge where the coverage workbook says CLOSE or PARTIAL, new columns only for
   ABSENT concepts, and restructure the generic ones (question 10) before anyone labels them.
10. **Generic keywords with generic anchors** ("distribution" anchored by "area") qualify a quarter
    of the corpus. An anchor anywhere in the paper is a weak test. *Recommend:* count keyword
    mentions that have an anchor in the same or adjacent sentence, as the elasmobranch proximity
    filter already does. That is one more count per term in the feature pass; say yes and I add it.
11. **Are David's acronyms case-sensitive** (CPUE, BPUE, PRM, AVM, CK, LDH, AST, ALT, LED, TAC*)?
    I assumed yes; "led" and "alt" would otherwise match everywhere. Needs David's confirmation.
12. **Reviewer names on a public site and in a public repo?** The per-author pages already do
    this. *Recommend:* display names as on the download hub, no emails, and say so on the page.
13. **Fix the borrowed-PDF bug first?** 1,456 papers in these lists carry another paper's text.
    They are hidden, but they are also 1,456 papers no expert can judge. *Recommend:* yes, fix
    before champions start; it has been waiting for your go-ahead since 18 Sep.
14. **Should the ladder order by the live score or by the best available score?** The live score
    orders the bottom of the list poorly. *Recommend:* once a concept has 200 inspected labels,
    re-order by the fitted rule's score so the margin tightens as labelling proceeds.
15. **Is 20 MB of generated data per topic acceptable in `docs/`**, or should the data files live
    on a separate branch or release asset? *Recommend:* commit for fisheries now, revisit at the
    third topic.

## Out of scope

Fixing the borrowed-PDF bug (separate, awaiting approval); non-binary columns (species,
techniques, depth, geography); LLM judging beyond reusing the Fable reads already on disk;
any change to the per-author pages.
