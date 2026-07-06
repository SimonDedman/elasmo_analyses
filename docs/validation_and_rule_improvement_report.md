# Validation and rule-improvement report: extraction pipeline accuracy

**Date:** 2026-07-04
**Author:** Simon Dedman (+ Claude)
**Audience:** EEA elasmobranch research team

---

## 1. Executive summary

The 123-column rule-based extractor that classifies every paper in the database (habitats, threats, gear, impacts, disciplines, ocean basins) had never had its accuracy measured against human judgement — every "it works" claim to date rested on firing counts, not ground truth. We built a validation loop that scores the rules against 15 human-reviewed papers ("gold") and against a Claude ("Fable") oracle run across 291 papers spanning 166 schema columns ("silver"), and found the rules agree with humans on only 43% of contested calls (macro-F1), while Fable agrees with humans on 80%. Diagnosis showed this gap is *not* a logic problem: the rules are precise (68%) but under-detect (49% recall) because their keyword lists are too narrow, missing legitimate synonyms and phrasings. Using Fable's own evidence quotes as a synonym-mining source, we ran a self-verifying auto-test loop that added terms to the ten worst-scoring columns, re-ran the rules, and re-scored automatically — 9 of 10 changes were kept because they measurably improved F1 (macro-F1 over those columns rose from 0.16 to 0.43), and the one change that made things worse was automatically rejected. The core deliverable is not just an accuracy number but a repeatable, cheap method for using an LLM to make the deterministic rule-based extractor better, so that production extraction across the full ~40,000-PDF corpus never needs to call an LLM at all.

---

## 2. Method

### 2.1 The gold + silver bridge

Human review of extraction output is slow (three reviewers — David Ruiz-García, Alex McInturf, Elena Fernández-Corredor — produced 190 column-level corrections across 15 papers). That is a solid but small sample. To get usable statistics on rare columns, we added a "silver" layer: Fable (Claude) was run as an extraction oracle across a stratified sample of 300 papers plus the 15 gold papers (315 sampled; 291 successfully processed — 24 had no extractable PDF text and were skipped), covering 166 schema columns.

The bridge that licenses this substitution is simple: on the 15 gold papers, **Fable agrees with the human reviewers 80% of the time** (macro-F1 0.796). That is high enough to treat Fable's labels as a usable, non-gold "silver" reference for the other 276 papers where no human review exists, while still reporting every headline number against the true gold set as well.

### 2.2 Fable as oracle and critic

For each paper, Fable was given the full extracted text and every schema column's name + definition, and asked (via a forced structured tool call) to return `present` (bool), an `evidence` quote, and a `confidence` score per column — independently of what the regex rules had already fired. This is the same role an expert coder plays in a manual coding exercise, run automatically and cached by PDF SHA-1 so repeat runs are near-free.

Where the rules and Fable/human disagreed on a column, Fable was asked a second question: given the offending papers' evidence quotes and the column's current rule (keyword list, threshold, section-weighting), *what specific change would fix it?* This produced a ranked list of proposed rule edits (`outputs/validation/rule_proposals.csv`) — mostly `add_terms` changes listing new synonyms mined directly from real evidence text.

### 2.3 The self-verifying auto-test loop

The critical design choice is that no proposed rule change is trusted on Fable's say-so. Each proposal is applied to an isolated copy of the rule set, the regex extractor is re-run on the sample, and the column's precision/recall/F1 is re-scored against the same reference labels used before the change. A change is **kept only if it measurably improves F1**; otherwise it is discarded. This turns "the LLM thinks this rule is better" into "we measured that this rule is better," which is the whole point of using an LLM to improve a deterministic system rather than replace it — the rules stay auditable, fast, and free, and every change to them is backed by a before/after number, not a plausible-sounding suggestion.

---

## 3. Results

### 3.1 Headline accuracy

| Comparison | Papers | Columns scored | Macro-F1 |
|---|---|---|---|
| Fable vs human (gold, the licensing bridge) | 15 | 55 | **0.796** |
| Rules vs human (gold — the real headline) | 15 | 55 | **0.429** |
| Rules vs Fable (silver, at scale) | 291 | 166 | **0.533** |

Averaged across the 166 silver columns, the rules run at **precision 0.68 / recall 0.49** — they are more often right than wrong when they *do* fire, but they miss roughly half of the true positives.

### 3.2 The diagnosis: under-detection, not over-detection

That precision/recall split is the key diagnostic finding: **the rules under-detect.** They are not raising a flood of false positives (which would point to a logic problem — rules firing on the wrong context) — they are staying silent on cases a human or Fable would call positive, because the keyword list simply does not contain the words the paper actually used. This is a vocabulary problem, and vocabulary problems are exactly what an LLM is good at fixing.

The worst-performing columns illustrate this starkly — high precision, near-zero recall, dominated by false negatives:

| Column | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|
| `gear_survey` | 4 | 1 | **40** | 0.80 | 0.09 | 0.16 |
| `gear_hook_line` | 4 | 0 | **30** | 1.00 | 0.12 | 0.21 |
| `imp_size_structure` | 2 | 2 | 17 | 0.50 | 0.11 | 0.17 |
| `imp_behaviour_change` | 1 | 0 | **17** | 1.00 | 0.06 | 0.11 |
| `imp_economic` | 1 | 1 | 15 | 0.50 | 0.06 | 0.11 |
| `imp_trophic` | 1 | 1 | 11 | 0.50 | 0.08 | 0.14 |
| `eco_pupping` | 1 | 0 | 11 | 1.00 | 0.08 | 0.15 |
| `imp_injury` | 2 | 5 | 11 | 0.29 | 0.15 | 0.20 |
| `gear_mit_circle_hook` | 1 | 0 | 8 | 1.00 | 0.11 | 0.20 |
| `imp_post_release` | 1 | 2 | 8 | 0.33 | 0.11 | 0.17 |

`gear_survey` missed BRUV/aerial-survey papers because its terms only covered a couple of phrasings; `gear_hook_line` missed dropline, angling and hand-line studies; `imp_behaviour_change` missed papers describing "behavioural shift" or "altered behaviour" rather than the exact terms the rule was looking for.

### 3.3 Round 1 of rule improvement: before → after

Fable's evidence quotes for these ten worst columns were mined for the synonyms the rules were missing, each proposed as an `add_terms` change, and auto-tested:

| Column | Terms added (excerpt) | F1 before | F1 after | Result |
|---|---|---|---|---|
| `gear_mit_circle_hook` | circular hook, circle hooks, Mustad circle, non-offset… | 0.20 | **0.80** | ACCEPT |
| `gear_hook_line` | dropline, angling, baited hook, hand line, rod and line… | 0.21 | **0.52** | ACCEPT |
| `gear_survey` | BRUV, baited remote underwater video, aerial survey… | 0.16 | **0.52** | ACCEPT |
| `imp_trophic` | trophic cascade, cascade effect, ontogenetic dietary shift… | 0.14 | **0.50** | ACCEPT |
| `eco_pupping` | parturition, parturition season, pupping site, spawning site… | 0.15 | **0.45** | ACCEPT |
| `imp_injury` | abrasion, lesion, laceration, amputation, bite mark… | 0.20 | **0.42** | ACCEPT |
| `imp_size_structure` | length-frequency, size class, catch size distribution… | 0.17 | **0.41** | ACCEPT |
| `imp_economic` | revenue, price per kg, market trend, economic profit… | 0.11 | **0.38** | ACCEPT |
| `imp_behaviour_change` | behavioural shift, behavioral shift, altered behaviour… | 0.11 | **0.19** | ACCEPT |
| `imp_post_release` | post-release survival, post-release survivorship… | 0.17 | 0.14 | **reject** |

**9 of 10 proposed changes were accepted; macro-F1 across these ten columns rose from 0.163 to 0.433** (all figures per `outputs/validation/improvement_log.csv` and `autotest_full.log`). The single rejection — `imp_post_release`, where the new terms actually *lowered* F1 from 0.17 to 0.14 — is not a failure of the method; it is proof the guardrail works: a plausible-looking, LLM-proposed change was tested, found to make things worse (probably by introducing false positives elsewhere), and discarded automatically without a human having to notice.

### 3.4 Model choice: is Fable overkill?

As a side experiment, we re-ran the oracle role on the 15 gold papers using cheaper models (Claude Sonnet and Claude Haiku, same forced structured extraction) to see whether a lighter model could serve as the oracle. Scored the same way against the 15 gold papers, using both the per-column macro-F1 and the pooled micro-F1 (more stable on a small sample):

| Model | Macro-F1 vs human | Micro-F1 vs human (tp/fp/fn) |
|---|---|---|
| Fable | 0.80 | **0.60** (34 / 8 / 38) |
| Sonnet | 0.73 | **0.60** (34 / 8 / 38) |
| Haiku | 0.62 | 0.38 (20 / 13 / 52) |

The key point: **Fable and Sonnet are statistically indistinguishable on this gold set** — pooled, they produce the *identical* true-positive/false-positive/false-negative counts, so the small "0.80 vs 0.73" macro gap is per-column averaging noise on only 15 papers, not a real quality difference. **Haiku is genuinely lossier** (recall 0.28 vs 0.47 — it misses far more). So the honest ordering is Fable ≈ Sonnet ≫ Haiku. For this project we use **Fable** for extraction (quality is the priority, and where two models are indistinguishable there is nothing to lose by choosing the stronger one); Haiku is not trustworthy enough to adjudicate rule quality.

### 3.5 Cost of the oracle at scale

Fable used a mean of ~8,305 input / ~400 output tokens per paper. Extrapolated to the full ~40,000-PDF corpus at $1.00/$5.00 per 1M in/out tokens, that is **~$412** (excludes OCR and retries) — cheap enough to run the whole diagnostic loop repeatedly, but this is precisely why the plan is to use the LLM to *improve the free rules* rather than to run it on every paper in production.

---

## 4. Generalisable lessons

These are the transferable takeaways, not specific to this schema:

1. **Rule-based extractors typically fail by under-detection, not over-detection.** High precision/low recall is the signature of a vocabulary gap, not a broken matching logic — check precision and recall separately, not just an aggregate accuracy figure, or the fix will be aimed at the wrong problem (tightening rules that are already too tight).
2. **LLM evidence quotes are a synonym-mining goldmine.** Asking an oracle model to point at the *exact phrase* it used to justify a label turns "the rule is missing something" into a concrete, minimal, testable diff (a term list to add), rather than a vague prompt to "improve accuracy."
3. **Always auto-test, and keep only measured improvements.** An LLM's proposed rule change is a hypothesis, not a fact. The one rejected change in round 1 is the whole argument for this discipline: it looked reasonable and made things worse. A change accepted on the LLM's authority alone, without re-scoring, would have silently regressed the pipeline.
4. **A gold set built only from corrections is a pessimistic lower bound, not the true score.** Our 190 gold labels are *corrections* to what the rules originally produced — reviewers only logged where the rules were wrong, not every column they confirmed as right. That means the true rules-vs-human agreement is very likely higher than 0.429 in practice; treat that number as a floor to improve from, not a ceiling of how bad the system is.
5. **Model choice is a dial, not a binary.** The cheapest model (Haiku) was noticeably lossier as an oracle; the mid-tier model (Sonnet) tracked the top-tier model (Fable) closely. When designing any LLM-as-oracle or LLM-as-critic loop, it is worth costing out whether a cheaper model gets you 90% of the signal at a fraction of the price before defaulting to the most expensive option.
6. **The endpoint is a rule set that no longer needs an LLM.** The goal of this entire exercise is not to justify switching production extraction to Fable — it's the opposite: use the LLM offline, once, as a critic and synonym-generator, to close the gap until the free deterministic rules are good enough that nobody needs to call an LLM to extract the next 40,000 papers.

---

## 5. How to continue the loop

The loop is designed to be re-run indefinitely, each time picking off the next tranche of weak columns:

1. **Re-score** the current rule set against the silver set (`scripts/validation/score.py`) to get fresh per-column F1s — the ten columns fixed in round 1 will have moved off the "worst" list, revealing the next ten.
2. **Propose** — feed the new worst columns' evidence quotes and current rules back to Fable (`scripts/validation/propose_rules.py`) for a fresh batch of `add_terms` / threshold / section-weighting proposals.
3. **Auto-test** each proposal (`scripts/validation/autotest_rules.py`): apply → re-run the sample → re-score → keep only if F1 improves, exactly as in round 1.
4. **Report the gold-15 rules-vs-human score alongside every round** as the un-gameable overfitting check — silver-set gains that do not show up (or that regress) on the untouched gold set are a warning sign the rules are overfitting to Fable's idiosyncrasies rather than genuinely improving.
5. Repeat until the marginal round stops moving the needle, or until rules-vs-human on gold closes most of the way to Fable-vs-human on gold (0.796) — at that point the rule-based extractor is doing almost as well as the LLM oracle, and production extraction across the full corpus can continue to run on the free deterministic rules with confidence, with no LLM call required at inference time.

Every accepted change stays on an isolated branch (`outputs/validation/improved_rules/`) until a human approves merging it into the production rule set — the auto-test loop earns trust for a candidate change, it does not by itself deploy it.

---

## 6. Limitations and caveats

- **The gold set is small.** 15 papers, 3 reviewers, 190 corrections. Per-column statistics on gold are noisy, especially for rare columns (many gold columns have only 1-6 supporting rows — see the 52-column coverage gap noted in `ab_viability.md`). Treat the gold headline (0.429) as directionally right, not precise to the third decimal.
- **Gold labels are corrections-only.** Reviewers logged where the rules were wrong, not a full independent re-labelling of every column for every paper. This structurally depresses the rules-vs-human number relative to the true agreement rate (see lesson 4 above) — it is a defensible pessimistic bound, not a ceiling.
- **The silver set is LLM-adjudicated, not human-verified.** The 291-paper, 166-column scale figures (rules-vs-Fable, 0.533) inherit whatever blind spots Fable itself has. The gold bridge (0.796 Fable-vs-human) is the only check on Fable's own reliability, and it is itself built on only 15 papers.
- **24 of 315 sampled papers had no extractable text** and were dropped from the silver set entirely (291 processed of 315 sampled), which may under-represent scanned/older PDFs relative to the full corpus.
- **The model comparison rests on a small sample.** It scored all 15 gold papers but only ~105 human-labelled (paper × column) pairs, so the exact F1 values are noisy — treat the ordering (Fable ≈ Sonnet ≫ Haiku, with Fable and Sonnet indistinguishable at the pooled level) as more reliable than the precise numbers, and re-run on a larger human-labelled set before quoting single figures.
- **Cost extrapolation is a snapshot.** The $412/40k-PDF Fable estimate uses a fixed pricing snapshot, excludes OCR and retry overhead, and assumes the sampled papers' token/length distribution is representative of the full corpus.
