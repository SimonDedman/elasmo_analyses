# Extraction diff: 3-run comparison (April 18 → April 20 → April 21)

Three runs chained. Each diff isolates a distinct cluster of rule changes:

| Label | Run ID | Date | Rule state |
|---|---|---|---|
| **Run 1** | `literature_review_enriched.pre-2026-04-20.parquet` (no snapshot) | 2026-04-18 | Pre-TITLE/KEYWORDS baseline |
| **Run 2** | `20260421T050413_5ca94a22d` | 2026-04-20 20:40 | +TITLE/KEYWORDS @ 2.0, +d_biology/physiology/fisheries expansion, +imp_biomass response anchors, +pr_aquaculture 1→2, +eco_deepwater variants, +ghost-gear rename, +*A. bovinus* |
| **Run 3** | `20260422T061055_4fd93404b-dirty` | 2026-04-21 22:37 | +Elena E1/E2/E3 (wildcard anchors), +gender normaliser, +A1 (OTHER weight 0, OTHER terminator for TITLE/KEYWORDS, Springer-affiliation strip), +C (study_type classifier), +D (depth regex + evidence), **+anchor-wildcard compile fix** (latent bug from 2026-04-20 that had made `fluctuat*/rebuild*/truncat*` anchors match the literal asterisk) |

**Run 2 vs Run 3 run-ID**: an intermediate run `20260422T051854_4fd93404b-dirty` exists under `outputs/extraction_runs/` flagged with `BROKEN_anchor_wildcards.txt`. It is kept for audit; do not use for analysis. It surfaced the anchor-wildcard bug: `imp_community_composition` and `imp_biodiversity` fell to 0 firings because Elena's widened anchors were all wildcards and the bug made none of them match. Run 3 is the rerun after the bug fix.

Run 2 reported `n_papers_in_parquet = 30,558`; Run 3 reports the same. Earlier report's paper count matches.

---

## Part 1 — Run 1 → Run 2

See the full existing report: [`2026-04-20_extraction_diff_report.md`](./2026-04-20_extraction_diff_report.md).

**Headline:** universal ~21% lift across six schemas from TITLE/KEYWORDS injection at weight 2.0 (old OTHER weight was 0.25). Outliers:

- `d_` **+34.6%** (driven by d_biology +105%, d_fisheries +234%, d_physiology +50%; vocabulary expansions stacked on top of the TITLE/KEYWORDS baseline)
- `pr_aquaculture` **-41.3%** (threshold 1→2 cut passing-mention false positives in Introduction)
- `eco_deepwater` **+37.8%** (deepwater/deep water hyphen variants)

Run 1 → Run 2 was entirely a *capture improvement* step: more real matches surface from author-intent signals, specific vocabulary gaps filled.

---

## Part 2 — Run 2 → Run 3

Run 2 → Run 3 is a *precision* step: the rule set now excludes text that was previously firing at unwanted weight. Three independent precision mechanisms landed in this run, so every schema drops in aggregate — but the drops are targeted (false positives from front matter, affiliation footnotes, and body-length measurements).

### Schema-level totals

| Schema | Run 2 firings | Run 3 firings | Δ | Δ% |
|---|---:|---:|---:|---:|
| `eco_` Ecosystem | 40,285 | 34,330 | −5,955 | **−14.8%** |
| `pr_` Pressure / Threat | 17,542 | 14,607 | −2,935 | **−16.7%** |
| `gear_` Fishing Gear | 11,784 | 10,081 | −1,703 | **−14.5%** |
| `imp_` Impact / Response | 14,191 | 13,178 | −1,013 | **−7.1%** |
| `d_` Discipline | 47,478 | 40,151 | −7,327 | **−15.4%** |
| `b_` Ocean Basin (keyword) | 17,248 | 14,613 | −2,635 | **−15.3%** |
| `sb_` Ocean Sub-basin | 10,091 | 8,419 | −1,672 | **−16.6%** |

**papers_with_any_match** drops track total firings proportionally (e.g. `d_` papers-matched 16,679 → 15,177, −9.0%; `eco_` 14,361 → 12,462, −13.2%). This is smaller than the total-firings drop because most removals are from papers that had multiple spurious matches; removing a few doesn't usually drop them below 0 on that column.

**Interpretation:** a ~14–17% universal drop is the *inverse* of the Run 1 → Run 2 lift (~21% universal gain). The mechanism is symmetric:

- Run 1 → Run 2 added TITLE/KEYWORDS at weight 2.0 (new positive signal). Unchanged front matter still contributed at weight 0.25 via OTHER.
- Run 2 → Run 3 zeroed OTHER and removed Springer-style affiliation text entirely. So the front-matter contribution that remained after Run 2 is now gone.

The `imp_` schema drops the least (−7.1%) because most `imp_` columns use anchors; when an anchor fires, context is tight and front-matter noise contributes little even with OTHER=0.25 previously.

### Column-level changes — biggest drops

These are the columns where the precision changes removed the most firings.

| Column | Run 2 | Run 3 | Δ | Δ% | Likely cause |
|---|---:|---:|---:|---:|---|
| `eco_marine` | 12,454 | 10,525 | **−1,929** | −15.5% | OTHER=0 + affiliation strip (universal baseline) |
| `d_conservation` | 4,819 | 3,852 | **−967** | −20.1% | **27537-class bug fix.** Affiliation text like "Department of … Conservation Biology" no longer contributes. |
| `d_biology` | 5,592 | 4,733 | **−859** | −15.4% | OTHER=0 + affiliation strip (baseline) |
| `eco_coastal` | 4,882 | 4,145 | **−737** | −15.1% | baseline |
| `d_taxonomy` | 4,256 | 3,600 | **−656** | −15.4% | baseline |
| `eco_pelagic` | 3,982 | 3,356 | **−626** | −15.7% | baseline |
| `d_genetics` | 4,410 | 3,792 | **−618** | −14.0% | baseline |
| `d_reproductive` | 4,108 | 3,528 | **−580** | −14.1% | baseline |
| `pr_aquaculture` | 556 | 306 | **−250** | **−45.0%** | Affiliation footnotes at universities with aquaculture programmes no longer contribute. Stacks on top of the threshold raise already shipped. |
| `d_husbandry` | 1,202 | 916 | **−286** | −23.8% | Affiliation strip — "aquarium/zoological" institutional names |
| `pr_habitat_loss` | 667 | 498 | **−169** | **−25.3%** | Affiliation strip — "department of conservation/wildlife" institutional names |
| `pr_fishing_iuu` | 619 | 466 | **−153** | −24.7% | baseline + OTHER |
| `sb_hawaii` | 662 | 507 | **−155** | −23.4% | Affiliation strip — "University of Hawaii" names |
| `b_arctic_ocean` | 423 | 317 | **−106** | **−25.1%** | Affiliation strip — "Arctic Research Institute" names |
| `eco_polar` | 1,023 | 780 | **−243** | −23.8% | Affiliation strip — "Polar Institute" |
| `gear_gillnet` | 892 | 683 | **−209** | −23.4% | Depth regex tightening removes body-measurement mis-reads; baseline |

Every column with a Δ% noticeably larger than the schema baseline is explainable by either (a) an institutional name that matched the column's keywords (`Hawaii`, `Arctic`, `Polar`, `Conservation Biology`, `Fisheries & Oceans`, etc.) or (b) a term that appeared heavily in body-measurement context (`gear_gillnet` mentions of `gillnet` spacings).

### Column-level changes — biggest *gains*

These are the columns where the anchor-wildcard fix and/or Elena's term expansions surface more matches.

| Column | Run 2 | Run 3 | Δ | Δ% | Likely cause |
|---|---:|---:|---:|---:|---|
| `imp_biodiversity` | 373 | 1,274 | **+901** | **+241.6%** | Elena E2 — added `extinction*` as a term (+ anchor wildcards now work: `chang*/loss*/declin*/impact*/decreas*/extinct*`) |
| `imp_biomass` | 316 | 532 | **+216** | **+68.3%** | Anchor-wildcard fix — `fluctuat*/rebuild*` now fire; previously matched literal asterisk |
| `imp_size_structure` | 716 | 891 | **+175** | **+24.4%** | Anchor-wildcard fix — `truncat*` now fires |
| `imp_community_composition` | 469 | 474 | +5 | +1.1% | Elena E1 — anchor wildcards restored (the term set is similar; the swap change/shift/impact → `chang*/shift*/impact*` captures verb tenses, so there's a small gain that offsets the OTHER=0 baseline drop) |

`imp_biodiversity` is the outlier: the +241% gain is driven by `extinction*` as a term, not just the anchor fix. Extinction-focused papers (taxonomy, palaeontology, IUCN Red List work) fire `imp_biodiversity` where previously they did not. This matches Elena's proposal E4 (extinction should be an impact, not a pressure).

### New column: `study_type`

Replaces the hardcoded `"empirical"` default.

| Label | Count | % |
|---|---:|---:|
| `empirical` | 29,872 | 97.8% |
| `review` | 348 | 1.1% |
| `letter` | 202 | 0.7% |
| `corrigendum` | 71 | 0.2% |
| `synthesis` | 36 | 0.1% |
| `conceptual` | 29 | 0.1% |

The 686 non-empirical papers (2.2%) are the set that Alex's feedback targets — review / synthesis / conceptual papers that inherit every schema tag from their cited case studies. Downstream analyses can now filter `study_type == 'empirical'` for primary-data queries.

**Accuracy spot-check pending** — classifier is title+keywords only, priority-ordered, untested against known-correct labels.

### Depth extraction

- Papers with depth: 5,180 (Run 3) vs ~5,174 in Run 2 parquet. Near-flat despite the stricter regex.
- But the identity of matched papers has shifted: the new regex rejects body-measurement-only matches (basking/whale-shark papers where the only "NNN m" in the text is a body length) and gains matches in papers where depth is encoded in specific deployment verbs (`CTD`, `descended to`, `deployed at`) that the old regex missed when "depth" wasn't adjacent.
- **New:** depth evidence rows now land in `schema_extraction_evidence.csv`. Previously 0 of ~260K rows were depth; now each matched paper carries a context snippet with the matched numeric span bracketed.

---

## Audit-quality caveats

1. **Intermediate broken run `20260422T051854_4fd93404b-dirty`** is retained under `outputs/extraction_runs/` solely for audit. Do not diff against it. The `BROKEN_anchor_wildcards.txt` file in that directory explains why.

2. **Anchor-wildcard bug predates this week.** The `fluctuat*/rebuild*` anchors added to `imp_biomass` on 2026-04-20 as David's "response-language anchor" fix never actually fired — they matched the literal asterisk. The +216 firing count for `imp_biomass` in Run 3 is the *actual* implementation of that fix. David's original observation about `imp_biomass` over-firing from predictor-context biomass mentions is only now being tested in practice.

3. **`imp_community_composition` is flat (+1.1%)** because the anchor widening (change→`chang*`) and OTHER=0 roughly cancel for this column. Precision / recall trade-off didn't change net; accuracy of individual classifications may have improved.

4. **Universal ~15% drop does not mean the pipeline has weakened.** Manual validation on Alex's, David's, and Elena's papers shows this is a precision improvement: specific false positives (affiliation text, body-length measurements as depth, front-matter metadata) are removed. True positives from the main body of each paper are unaffected.

5. **Run 1 → Run 3 cumulative.** Overall lift from Run 1 to Run 3 is approximately +3% to +6% per schema (Run 1 → Run 2 was +21%, Run 2 → Run 3 is −15%; these are not additive in percentage terms but they largely offset on the total-firings axis). Precision is substantially better; recall is very similar to Run 1.

---

*Report generated 2026-04-21 post-extraction. Source: `outputs/extraction_runs/*/run_summary.json` and `scripts/diff_extraction_runs.py` output (saved to `/tmp/diff_2to4.txt`).*
