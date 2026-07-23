# Validation Feedback Synthesis — 2026-04-20

**Source:**
- Alexandra G. McInturf — 8 papers reviewed, JSON submitted via UI (PR #11)
- David Ruiz-García — 6 papers reviewed (JSON, PR #12) + 27-rule master sheet: [`ruiz_garcia_validation_master.md`](./ruiz_garcia_validation_master.md) (converted from `ruiz_garcia_validation_master.xlsx`, stored alongside)

**Purpose:** Collate both validators' feedback ahead of the Tuesday / Wednesday review meetings. Decisions to reach: which rule changes to adopt, which need more input, which are out of scope.

---

## 1. Rating distribution across schemas

Combined picture of where the extraction pipeline is working well vs. struggling, from the two validators' submissions.

| Schema | Alex (n=8 papers) | David (n=6 papers) | Combined read |
|---|---|---|---|
| `pr_` Pressure / Threat | 5 correct, 1 partial | 4 correct, 1 partial, 1 incorrect | **Working well** |
| `sp_` Species | 3 correct, 2 partial, 1 incorrect | 4 correct, 1 incorrect | **Working well** |
| `gear_` Fishing Gear | 3 correct, 1 partial, 3 incorrect | 3 correct, 1 partial, 2 incorrect | Acceptable; gear-type subtypes weak |
| `b_` Ocean Basin (keyword) | 1 correct, 3 partial, 4 incorrect | 4 correct, 2 incorrect | Mixed — hits fail on papers without explicit basin name |
| `d_` Discipline | 1 correct, 7 partial | 1 correct, 3 partial, 2 incorrect | **Needs work** — over-triggered by background mentions |
| `eco_` Ecosystem | 2 correct, 5 partial | 1 correct, 4 partial, 1 incorrect | **Needs work** — keyword coverage gaps (deepwater / demersal) |
| `sb_` Ocean Sub-basin | 4 correct, 2 partial, 2 incorrect | 1 correct, 5 incorrect | **Needs work** (David: Mediterranean scheme too granular) |
| `imp_` Impact / Response | 6 partial, 2 incorrect | 3 partial, 3 incorrect | **Needs work** — false positives from predictor-variable mentions |
| `ob_` Ocean Basin (geographic) | 1 correct, 2 partial, 4 incorrect | 5 correct, 1 incorrect | **Diverges** between validators — check pipeline coverage for Alex's papers |
| `a_` Analytical Techniques | 1 correct, 6 incorrect | 2 correct, 2 partial, 1 incorrect | **Diverges** — Alex's papers likely use newer / rarer methods |

**Take-home:** `pr_` and `sp_` are fine. `d_`, `eco_`, `sb_`, `imp_` need the most attention. `ob_` and `a_` need investigation of why the two validators see different outcomes.

---

## 2. David's 27 rules — key individual items

Priority ordering for meeting discussion. Full sheet at [`ruiz_garcia_validation_master.md`](./ruiz_garcia_validation_master.md).

### Likely-adopt (low cost, clear fix)

1. **`b_` threshold consistency** (xlsx row 2) — `b_mediterranean` and `b_southern_ocean` use threshold=1 while others use 2. David asks whether this is deliberate. *(Per `ocean_basin_proposal.md` it IS deliberate: these sub-sea names are unambiguous single-mention signals. Document this in the meeting notes and retain.)* **TO REVIEW** at meeting (decision: keep current thresholds, document rationale).
2. **`eco_deepwater` keywords** (row 8) — add "deepwater" and "deep water" as variants alongside "deep-water". **FIXED** (extract_schema_columns.py + rules.json updated 2026-04-20).
3. **`d_fisheries` keywords** (row 6) — expand to include "bycatch", "discard", "retention", "non-target species". **FIXED** (extract_schema_columns.py + rules.json updated 2026-04-20).
4. **`sp_` species list** (row 23) — add *Aetomylaeus bovinus* (and likely other Mediterranean taxa missing from the dictionary). **FIXED** for *bovinus* (added to species_common_lookup_cleaned.csv + options.json as `sp_aetomylaeus_bovinus` 2026-04-20). Wider audit **TO REVIEW** at meeting.
5. **`imp_biomass` anchor** (row 11) — require biomass co-occurrence with response-variable language, not predictor. **FIXED** (added document-level anchors: change/decline/decrease/increase/shift/trend/loss/recovery/fluctuat\*/depletion/rebuild\*; biomass-only mentions no longer fire without one of these).
6. **`mit_ghost` reclassification** (row 19) — ghost gear currently under mitigation; David argues it's gear- or pressure-related. **FIXED** (renamed `gear_mit_ghost` → `gear_ghost`, no longer in the mitigation cluster; "ghost fishing" added as keyword variant).

### Needs discussion (medium cost, design choice)

7. **Mediterranean sub-basin scheme** (row 3, plus Meta_Notes) — David proposes GFCM-aligned groupings: Western / Central / Adriatic / Eastern / Black Sea. Current scheme uses individual sea names (Alboran, Ligurian, Tyrrhenian…). **TO REVIEW** at meeting (resolved trade-offs below: keep both schemas in parallel; keep `sb_black_sea` as own column; roll Sea of Marmara into `sb_black_sea`).
8. **Section-weighted disciplines** (rows 4, 7) — `d_biology`, `d_physiology` over-fire when methodological terms appear only in literature-review context. **PARTIALLY FIXED**: keyword expansion done (see §item-8 below for the resolved keyword set including measurement-action anchors, GSI/HSI spelled-out forms, "Le Cren", "Fulton's K", Ucrit + variants, TMAO/Q10 case-sensitive). Section-weighted refinement **TO REVIEW**.
9. **Dynamic thresholds for short-format papers** (rows 9, 25) — brief communications fail to meet threshold=2. **SUPERSEDED by item §9 below** — TITLE and KEYWORDS sections now ingested with weight 2.0, which lifts brief communications above threshold without length-dependent logic. Dynamic thresholds avoided as Simon preferred.
10. **Impact summary conditional dependency** (row 26) — don't populate `imp_direction`, `imp_quantified`, `imp_confidence` unless at least one pressure/threat or impact was detected. Simple post-processing rule. **TO REVIEW** at meeting (need to define "pressure/threat detected").

### Needs design work

11. **"Coastal" definition** (row 14) — current keyword-frequency approach mis-classifies deep-sea papers that mention continental shelf. David proposes a process-focus definition (nearshore dynamics). Design question: is `eco_coastal` a location label or an ecosystem-type label? The answer drives the implementation.
12. **`pr_aquaculture` anchor + threshold** (row 15) — single-mention "aquaculture" as context currently triggers. Raise threshold and/or require co-term.
13. **`pollution_chemical`** (row 16) — broad "pollut*" root too aggressive. Needs specific-compound or context requirements.
14. **Analytical techniques transparency** (row 20) — David asks for the full keyword/synonym list per technique to be documented publicly. *(Action: export `a_` keyword dictionary from pipeline code to `docs/schema_proposals/analytical_techniques_keywords.md`.)*

### Defer / investigate

15. **`imp_structure` schema merge** (row 10) — proposal to collapse Injury + Physiological stress into "Health assessment". Schema-breaking; affects existing analyses. Defer to post-review-cycle restructure.

---

## 3. Alex's submission — highlights

- **Per-paper:** discipline and analytical-technique schemas dominate her "incorrect" ratings (Alex's papers span movement ecology / telemetry / behaviour). Suggests `a_` dictionary coverage is weak for newer tracking methods.
- **Notes:** one question on taxonomy — "Does behaviour change = behavioral response?" for `imp_behaviour_change`. Action: document the intended distinction (or merge if there isn't one).
- **Author corrections** (new data path — silently dropped by the old workflow):
  - `gender`: blank → F
  - `origin_country`: **RU** → **USA** (NamSor mis-classified her; fix upstream)
  - `ethnicity`: British → United States (conflation issue — see §4)

---

## 4. Upstream data-quality issue surfaced by Alex

NamSor returned `origin_country=RU` for Alexandra G. McInturf with 72% probability (alt GR). This appears to be a **rare-surname failure mode**: "McInturf" is a low-frequency Scots-Irish surname with weak surname prior in NamSor, so the model over-weights the first name "Alexandra" (strongly Russian-signalling).

**Actions:**
- Add her correction to `outputs/author_location_overrides.csv` once PR #11 merges
- Audit NamSor output for other rare-surname authors — identify systematic Russian-mis-classification pattern
- The `ethnicity: British → United States` correction suggests the UI presents "ethnicity" and "origin country" as interchangeable, which is a UX issue worth revisiting (ethnicity ≈ heritage; origin country ≈ nation of birth/residence — they should be separately labelled)

---

## 5. Meeting agenda suggestions

**Tuesday** (if narrower focus):
- Adopt the low-cost batch (§2 items 1–6) as immediate pipeline fixes — apply and re-extract
- Decide on Mediterranean sub-basin scheme (item 7) — needs full group

**Wednesday** (broader strategy):
- Section-weighted disciplines (item 8) — commit to rollout timeline
- Dynamic thresholds (item 9) — agree on formula (linear? stepped?)
- Coastal definition (item 11) — resolve ecosystem-vs-location question
- Analytical techniques transparency (item 14) — assign owner
- Structural `imp_` merge (item 15) — defer or schedule?

**Post-meeting actions:**
- Merge PRs #11 and #12 with curator tags summarising adopted changes
- Update `extraction_review_reference.md` with agreed rule changes
- Push worker/workflow fixes (pending `main` commit)

---

# Investigation results — Simon's review questions (2026-04-20)

References to "§2 item N" below match the numbered list above.

## Implemented in this commit

- **Item 2** — `eco_deepwater`: added "deepwater" and "deep water" hyphen-variant keywords
- **Item 3** — `d_fisheries`: added "bycatch", "discard*", "retention", "non-target species", "non-target catch"
- **Item 6** — Ghost gear reclassified: `gear_mit_ghost` → `gear_ghost` (no longer in the mitigation cluster). Also added "ghost fishing" as a keyword variant. Updated in both `scripts/extract_schema_columns.py` and `docs/validate/assets/rules.json`. Existing extraction evidence rows under the old name are historical; will be overwritten on next extraction run.
- **Item 4 (partial)** — *Aetomylaeus bovinus* added to `data/species_common_lookup_cleaned.csv` (3 rows: bull ray, duckbill ray, Pteromylaeus bovinus synonym) AND to `docs/validate/assets/options.json` as `sp_aetomylaeus_bovinus`. See investigation note below for the upstream source-of-truth question.

## Item 4 — *Aetomylaeus bovinus* absence: investigation

- `sp_` master list (1,308 columns in options.json) included 7 *Aetomylaeus* species but NOT *bovinus*.
- `data/species_common_lookup_cleaned.csv` (3,016 rows) had no entry under *Aetomylaeus bovinus* OR its historical name *Pteromylaeus bovinus*. The only "bull ray" record was *Myliobatis aquila* (different genus).
- However, `data/sharkipedia/species_match_sharkipedia_only.csv` DOES contain `Aetomylaeus bovinus` (1 trend record). This means the species exists in Sharkipedia but failed to make it into our species lookup pipeline.
- **Likely root cause:** the `sp_` list was built from an older taxonomic snapshot when the species was still classified as *Pteromylaeus bovinus*. The 2016 revision moved it to *Aetomylaeus*; our lookup CSV did not capture this transition.

**Terminology clarification — "EEA" in this context:**
The comparison was:
- **"EEA list" = the `sp_*` columns in `outputs/literature_review.duckdb`** (1,308 columns, now 1,309 with bovinus). This set was originally built from the Shark References master species list; that's the de-facto EEA master.
- **"Sharkipedia list" = `data/sharkipedia/Sharkipedia-Taxonomy-v1.0-22-01-25.csv`** (1,282 species, dated **2022-01-25** — 3+ years old).
- `scripts/match_species_sharkipedia.py` diffs these two. Outputs land in `data/sharkipedia/species_match_{both,eea_only,sharkipedia_only}.csv`.

So the figure is:
- **1,177** species appear in both lists
- **131** species in our `sp_` columns but not in Sharkipedia's 2022 snapshot (mostly newly-described taxa: *Acroteriobatus andysabini* named 2019, etc.)
- **133** species in Sharkipedia's 2022 snapshot but not in our `sp_` columns (taxonomic-revision misses like *Aetomylaeus bovinus*, plus multi-species combined entries like "Alopias superciliosus,vulpinus")

The 133 is against a 3-year-old Sharkipedia snapshot — a fresh pull would likely find a different figure. The real audit should be against **Shark References** (our upstream source) AND current Sharkipedia/IUCN, not against a frozen 2022 CSV.

- **Action item:** run a species-list refresh against current Shark References + fresh Sharkipedia API pull + IUCN Red List species list; identify genus-revision misses and populate `sp_` accordingly.

## Item 5 — `imp_biomass`: section eligibility & co-occurrence linkage

**Current rule:** terms = `biomass`, `standing stock`, `spawning stock biomass`, `SSB` (case-sensitive); threshold = 2; **no anchors**.

**Section weights for `imp_` schema** (already implemented per SW fix):
- ABSTRACT 0.5, INTRODUCTION 0.25, METHODS 0.5, **RESULTS 1.0**, **RESULTS_AND_DISCUSSION 1.0**, **DISCUSSION 1.0**, CONCLUSIONS 0.5, OTHER 0.25
- So Results/Discussion already carry 4× the weight of Introduction. David's "require beyond Methods" intent is partially met, but a Methods-only mention can still trigger if there are 4+ occurrences in Methods (4 × 0.5 = 2.0 ≥ threshold).

**For "require linkage to response variable" (David's anchor proposal):**
- The current `BinaryColumn` class supports an `anchors` field (used by `imp_abundance`, `imp_growth`, `imp_community_composition` etc.). Anchors are **document-level**: "at least one anchor must fire anywhere in the doc" + the term threshold is met.
- We do NOT currently have **sentence-level** or **window-level** co-occurrence (i.e. "biomass within ±N sentences of a change-language verb"). Adding this requires a new matching pass over labelled sections and sliding-window scans.
- **Proposed implementation cost:** moderate (~half-day dev). Add `anchor_window` int field to `BinaryColumn`; if set, score = number of `term`-anchor co-occurrences within ±window words, not raw frequency.
- **Quick-win alternative for now:** add document-level anchors to `imp_biomass` matching the pattern used elsewhere: `anchors=["change", "decline", "decrease", "increase", "shift", "trend", "loss", "recovery", "fluctuat*"]`. This would catch papers that discuss biomass changes (response use) but not papers that mention biomass only as a covariate.

## Item 7 — Mediterranean coverage: current vs. David's proposed scheme

### Current state

| Schema | Mediterranean entries |
|---|---|
| `b_` (keyword extraction) | 1 column: `b_mediterranean` (terms: Mediterranean, Adriatic, Aegean, Tyrrhenian, Ionian Sea, Ligurian Sea, Alboran Sea, Strait of Gibraltar, Strait of Sicily; threshold 1) |
| `sb_` (sub-basin keyword) | **8 columns**: `sb_alboran_sea`, `sb_ligurian_sea`, `sb_tyrrhenian_sea`, `sb_adriatic_sea`, `sb_ionian_sea`, `sb_aegean_sea`, `sb_black_sea`, `sb_sea_of_marmara` |
| `ob_` (geographic pipeline) | 1 column: `ob_mediterranean_black_sea` (groups Mediterranean and Black Sea as a single analytical unit) |

### David's proposed GFCM-aligned scheme (5 groups + Black Sea)

Augmented with sub-area names found in the literature but missing from David's list (filled by Simon-Claude):

| Proposed column | Sub-areas / keywords (combined) |
|---|---|
| `sb_western_mediterranean` | **Alboran Sea**, **Balearic Sea**, **Sardinian Sea**, **Ligurian Sea**, **Tyrrhenian Sea**, Gulf of Lions, Catalan Sea |
| `sb_central_mediterranean` | Strait of Sicily, **Sicilian Channel**, **Ionian Sea**, **Libyan Sea**, Gulf of Sirte, Gulf of Gabès, Maltese Channel |
| `sb_adriatic_sea` | **Adriatic Sea** (existing) — Northern, Central, Southern Adriatic + **Strait of Otranto** |
| `sb_eastern_mediterranean` | **Aegean Sea**, **Sea of Crete**, **Levantine Sea**, **Cilician Sea**, Cyprus, Iskenderun Bay |
| `sb_black_sea` | **Black Sea** (existing) + **Sea of Marmara** + Sea of Azov + Bosphorus |

**Trade-offs — RESOLVED (Simon's call 2026-04-20):**
1. **Lossy aggregation:** the current 8 sub-basin columns let analysts ask basin-specific questions (e.g. "Tyrrhenian-only papers"). **DECISION: keep both** — add the 5 GFCM columns alongside the 8 individual seas. GFCM columns become the analytical default; individual seas remain available for fine-grained queries. David's xlsx Meta_Notes already proposes "retaining current sea names as keywords" which is consistent.
2. **Black Sea:** GFCM does not include Black Sea as a Mediterranean sub-basin (separate FAO statistical area). **DECISION: keep `sb_black_sea` as its own column** rather than rolling into `sb_eastern_mediterranean`.
3. **Sea of Marmara:** Mediterranean ↔ Black Sea transition. **DECISION: roll into `sb_black_sea`** (drop `sb_sea_of_marmara` as standalone; "Sea of Marmara" / "Marmara" / "Bosphorus" become keywords for `sb_black_sea`).

**Implementation pending** — needs the 5 new GFCM column definitions added to `extract_schema_columns.py:SUB_BASIN`, the Marmara merge applied, and rules.json mirrored. Will commit as a separate change after meeting confirmation.

## Item 8 — SECTION priority + keyword expansion

David proposes adding "effect" and "affect" as anchors/discriminators. Both are useful (often the response-variable language we lack for `imp_biomass`).

**`d_biology` keyword expansion — IMPLEMENTED 2026-04-20:**

Was 8 terms. Now 18:
- Original: *life history, age and growth, growth rate, longevity, maturity, length-at-maturity, length-weight, vertebral band*
- Added measurement terms: `vertebral count*`, `band pair*`, `gonadosomatic index`, `hepatosomatic index`, `Le Cren`, `Fulton's K`, `morphometric analysis`, `total length`, `precaudal length`, `disc width`

**Design decisions** (per Simon 2026-04-20, revised):
- **GSI / HSI INCLUDED** as case-sensitive terms with prerequisite-term gating. New `prerequisite_terms` field on `BinaryColumn` lets the matcher revoke the acronym's contribution unless the spelled-out form also fires. Implemented as a post-match filter that runs before threshold comparison; other terms in the column are unaffected. Smoke-tested against four scenarios (acronym alone / acronym + spelled-out / spelled-out alone / many bio terms + lone acronym) and behaves as expected. Documented in `extraction_logic.md`.
- **"Le Cren" and "Fulton's K"** are passed as plain string terms; the matcher treats them as exact-phrase matches (apostrophe and space included). No regex escaping needed in the term list.
- **Measurement-action anchors** (`analyzed`/`assessed`/`examined`/etc.) **not added** — they would over-fire as raw terms across ANY analytical discipline. Better as a future per-column `anchors` field if we want to require co-occurrence with measurement-action language; deferred.

**`d_physiology` keyword expansion — IMPLEMENTED 2026-04-20:**

Was 10 terms. Now 28:
- Original: *physiolog\*, metaboli\*, oxygen consumption, ventilation rate, blood gas, haematocrit, hematocrit, osmoregulat\*, thermoregulat\*, bioenergetic\**
- Added (case-sensitive): `SMR`, `RMR`, `MMR`, `Ucrit`, `TMAO`, `Q10`
- Added (case-insensitive): `aerobic scope`, `U crit`, `U-crit`, `critical swimming speed`, `heart rate`, `cardiac output`, `blood pressure`, `plasma osmolality`, `plasma cortisol`, `plasma lactate`, `urea`, `trimethylamine N-oxide`, `enzyme activity`, `metabolic rate`

**Design decisions** (per Simon 2026-04-20):
- **Ucrit superscript:** `pdftotext` flattens superscripts and subscripts to inline ASCII (no special character is preserved). "Ucrit" in a PDF rendered with subscript-`crit` extracts as plain "Ucrit" — so the literal-string match works. Added two extra variants (`U crit`, `U-crit`) to catch inconsistent typesetting where the layer break inserts a space or hyphen.
- **TMAO:** added to `case_sensitive_terms` so it doesn't match accidental capitalisation in body text.
- **Q10 / Q₁₀:** the unicode subscript form (Q₁₀, U+2081 U+2080) is essentially never preserved by PDF text extraction — papers using subscript styling extract as plain "Q10". So we search ASCII "Q10" case-sensitive only. Confident this catches the literature; the unicode form is dropped.

## Item 9 — TITLE and KEYWORDS sections — IMPLEMENTED 2026-04-20

**The gap:** the section detector recognised ABSTRACT, INTRODUCTION, METHODS, RESULTS, RESULTS_AND_DISCUSSION, DISCUSSION, CONCLUSIONS — and binned everything else as OTHER (weight 0.25). TITLE and KEYWORDS were both falling into OTHER, despite being the strongest possible author-intent signals.

**What changed (this commit):**

1. **`extract_schema_columns.py`:**
   - New `_extract_keywords_block()` helper extracts the author-supplied keyword block from raw PDF text BEFORE `strip_non_body_sections` removes the front matter
   - `extract_text_from_pdf()` re-injects the keyword block as a synthetic `KEYWORDS\n…\n\n` section at the top of the body text
   - `_match_paper()` now prepends `TITLE\n<title>\n\n` from the parquet's `title` column before section labelling
   - `_SECTION_PATTERNS` gets two new patterns: `^TITLE$` and `^KEYWORDS$` (placed at the top so they match before any other patterns)
   - `_SECTION_WEIGHTS` now includes `"TITLE": 2.0, "KEYWORDS": 2.0` for all 7 prefixes (eco_, pr_, gear_, imp_, d_, b_, sb_)

2. **`docs/validate/assets/rules.json`:** mirror of the new section weights so the validation UI reflects them.

3. **`docs/validate/assets/validate.js`:** `_renderRulesPalette` now includes TITLE and KEYWORDS columns in the section-weights table; new `w-max` class for ≥2.0 (highlighted green) renders them visually as the strongest weight.

4. **`docs/validate/assets/style.css`:** `.section-weights-table td.w-max` style added.

**Effect:** a single keyword-block hit (weighted 2.0) plus ONE body mention (weighted 0.25-1.0) clears threshold=2 for any column. Brief communications no longer fall below threshold; this **supersedes the dynamic-threshold proposal (item 9 in §2 list above).**

**Re-extraction needed.** All ~18,000 PDFs need to be re-processed for the new sections to take effect. Measured runtime: **~1h 23m** for the full corpus (from `run_id 20260421T050413_5ca94a22d`, 30,558 papers wall-clock between `rules_snapshot.json` and `binary_classifications.parquet`).

**Documentation update needed.** `docs/schema_proposals/extraction_logic.md` and the per-schema proposal docs (`ecosystem_component_proposal.md`, etc.) should mention TITLE and KEYWORDS as the highest-weighted sections. Proposed addendum text:

> Two synthetic sections are injected at extraction time: **TITLE** (the paper's full title from the bibliographic record) and **KEYWORDS** (the author-supplied keyword block parsed from the PDF after the abstract). Both receive weight **2.0** for every schema — the highest weighting in the system — because they encode author intent rather than incidental mention. A single keyword-block hit plus one body mention is sufficient to pass any column's threshold.

## Item 10 — Conditional dependency (`imp_direction`/`quantified`/`confidence`)

These three columns are NOT in the IMP main block (the 21 columns listed below). They appear to be derived/summary columns produced post-extraction. Confirmation needed: where are they computed, and against what definition of "pressure/threat detected"?

**Possible definitions for "pressure/threat detected" (for meeting):**
- Any `pr_*` column = 1 (broad — fires on background mentions of "climate change")
- Any `pr_*` column = 1 AND scored above 1.5× threshold (strong signal)
- At least 2 `pr_*` columns = 1 (multi-stressor confirmation)
- Any `pr_*` column = 1 AND any `imp_*` column = 1 (both detected)

David's proposal of "any pressure OR any impact detected" is the simplest gate. Trivial post-processing: `if (any pr_* > 0 or any imp_* > 0) then keep imp_direction/quantified/confidence else null`.

## Items shipped 2026-04-21 (post-this-doc, covering Alex's feedback)

**Status:** in working tree pending commit after re-extraction completes.

- **A1** — TITLE/KEYWORDS synthetic-section pollution fix. Three changes:
  1. Injections now terminate with `\nOTHER\n\n` so TITLE and KEYWORDS are strictly one chunk each.
  2. `OTHER` weight zeroed across all 7 weighted schemas (was 0.25). Content the labeller can't attribute to a named section contributes no score.
  3. New `_strip_affiliation_blocks()` pass in `strip_non_body_sections()` removes Springer-style author-affiliation paragraphs (e.g. "A. G. McInturf (*) : A. E. Steel : ... Department of Wildlife, Fish and Conservation Biology, University of California, Davis, CA, USA  e-mail: amcinturf@ucdavis.edu"). Pattern-specific to Springer; other journal layouts may need additional patterns as encountered.

  Verified on 27537: conservation-term hits in stripped text drop 4 → 1 (only the legitimate IUCN citation remains). Closes the `d_conservation` false positive flagged in the 2026-04-21 regen commit.

- **C** — `study_type` classifier. Replaces the hardcoded `"empirical"` default in `shark_references_to_sql.py`. Priority-ordered signals from TITLE + KEYWORDS only yield one of: `corrigendum`, `letter`, `review`, `synthesis`, `conceptual`, `empirical`. Addresses Alex's review-paper concern — downstream analyses can filter `study_type == 'empirical'` for primary-data-only queries.

- **D** — Depth regex tightened. Previously the `[><~≈]?\s*` prefix was empty-matchable, so any "NNN m" was captured (Alex's basking-shark body lengths misread as depths). Now requires a bathymetric-context word (`depth|bathym*|benthic|water column|sea floor|deployed at|captured at|CTD|...`) within ~60 chars before the number. Depth evidence rows now land in `schema_extraction_evidence.csv` with ±context snippets (previously 0 depth rows of 260K).

- **Elena E1/E2/E3** — `imp_community_composition` and `imp_biodiversity` anchors widened to wildcards so verb tenses fire; `extinction*` added to `imp_biodiversity` as both term and anchor; `pr_ocean_acidification` threshold 1 → 2.

- **Gender normaliser** in `generate_validation_pages.py:load_namsor()` — NamSor's `male`/`female` → dropdown codes `M`/`F` before page rendering so validators don't submit phantom gender "corrections".

---

## Item 11 — `eco_coastal` definition

**Current rule:** terms = `coastal, neritic, inshore, nearshore, continental shelf`; threshold = 3.

**Simon's framing:** ecosystem categories are mutually-informative (a coastal study is NOT pelagic), so "coastal" should fire on sampling-location evidence, not just process-focus mentions. **This reads as: keep current behaviour; the design intent is location-as-ecosystem.**

**For meeting:** propose two options for explicit framing:
- **Option A (status quo, Simon's preference):** `eco_*` = where the study took place. Keep current rules. Define in proposal doc.
- **Option B (David's reading):** `eco_*` = process-focus ecosystems. Tighter, more publishable, but requires ecosystem-process language anchors.

If A is adopted, also discuss whether `eco_` should attempt to be **mutually exclusive** (every paper assigned ≥1 ecosystem), which would inform what the "default" / fallback is.

## Item 12 — `pr_aquaculture`: current keywords + sections

**Current rule:** terms = `aquaculture`, `fish farm*`, `mariculture`; threshold = **1**; section weights for `pr_` schema:
- ABSTRACT 0.5, INTRODUCTION 1.0, METHODS 1.0, RESULTS 0.5, R&D 1.0, DISCUSSION 1.0, CONCLUSIONS 0.5, OTHER 0.25

So pressures fire most readily from Introduction/Methods/Discussion. A single mention in Introduction = 1.0 weighted score ≥ threshold 1.0 → passes. This is what David flagged: the threshold is too low.

**David's keywords to add:** (from xlsx row 15) — David lists `aquaculture`, `fish farm`, `mariculture` as the trigger terms (same as ours). His proposal is structural (raise threshold ≥2, require co-term), not new keywords.

**IMPLEMENTED 2026-04-20:** threshold raised 1 → 2. Combined with the new TITLE/KEYWORDS sections (item 9, also live this commit): a paper that lists "aquaculture" as a keyword (weight 2.0) plus has any body mention will now reach threshold without needing pure body-text repetition. Conversely, a paper that mentions "aquaculture" once in passing in the introduction (weight 1.0) will NOT fire — Simon's expected accuracy improvement should be substantial.

## Item 13 — `pr_pollution_chemical`: rules already in place

**Current rule:** terms = `pollut*`, `contaminant*`, `heavy metal*`, `mercury`, `PCB`, `PFAS`, `pesticide*` (case-sensitive: PCB, PFAS); threshold = **3**.

**Analysis:** "pollut*" is one of seven terms. Threshold 3 means three TOTAL mentions across any combination. So a paper could fire purely from `pollut*` × 3 (e.g. "marine pollution" appears 3 times) — Simon is correct that the wildcard root IS contributing as a near-standalone trigger.

**David's complaint** is that "pollution" appears in passing (e.g. "global threats include climate change, pollution, and overfishing") and fires the column. Threshold 3 mitigates but doesn't eliminate this when the paper happens to use "pollution" as a keyword more than once.

**Section weighting — yes, in use.** All `pr_*` columns share the `pr_` schema's section weights (Abstract 0.5, Intro 1.0, Methods 1.0, Results 0.5, Results+Discussion 1.0, Discussion 1.0, Conclusions 0.5, Other 0.25). With this commit's additions, TITLE and KEYWORDS get weight 2.0 too.

**Will TITLE+KEYWORDS inclusion help?** Yes, considerably. Chemical-pollution papers almost always list a specific compound class ("heavy metals", "PCBs", "microplastics", "mercury", etc.) as a keyword AND in the title. With weight 2.0 each, a true chemical-pollution paper will easily clear threshold 3 from title+keywords alone. False-positive papers that mention "pollution" only in passing won't have it as a title or keyword and so won't accumulate the high-weight credit.

**Recommendation:** wait and re-evaluate after the next extraction run with TITLE+KEYWORDS active. If pollut\*-only false positives persist, then add the specific-compound anchor:

```python
anchors=["heavy metal*", "mercury", "PCB", "PFAS", "pesticide*", "contaminant*", "microplastic*"]
```

**TO REVIEW** at meeting after re-extraction.

## Item 14 — Validation page mockup (rules transparency)

**Goal:** every validator should see, per column, the keywords that triggered the match, the section in which they appeared, the threshold, and any anchors / co-occurrence rules.

**Current state:** validate.js already has `_renderEvidence(evidenceArr)` (line 547) which surfaces matched terms + frequencies + sections per column — this is the existing evidence panel under each rating row. What's missing is the *underlying rule* (the term list, threshold, anchors) that the column WOULD have used had no match fired, OR for transparency on what the matcher was looking for.

**Recommended approach (low cost):**
1. **Augment `rules.json`** (already has 884 column entries) — confirmed it carries `terms`, `threshold`, `anchors`, `case_sensitive_terms`, plus per-prefix `_description` and `_criteria`.
2. **Add an inline "rule" disclosure** in the existing UI row: a small `[?]` icon next to each column name that pops a tooltip / accordion showing:
   - Threshold required (e.g. "≥ 2 weighted mentions")
   - Section weights for this prefix
   - Full keyword list (with case-sensitive flagged)
   - Anchors (if present)
   - Link to the relevant `docs/schema_proposals/<schema>.md`
3. Also add a **"current matches" panel** showing what the matcher actually fired on (this is the existing evidence panel — already present).
4. For columns that did NOT fire on this paper but the validator wants to know what the rule looks like, the `[?]` is the answer.

**Implemented directly in the production validation pages (2026-04-20):**

Two layers of rule transparency now live in production:

1. **Schema-level palette** (committed in `0ca2a672e`): the existing "Extraction rules" collapsible now shows, per schema, a colour-coded section-weights table (green ≥ 1.0, yellow ≥ 0.5, grey ≤ 0.25) and a 📄 _Full schema proposal_ link. After this commit's TITLE/KEYWORDS work, the table also includes the new TITLE and KEYWORDS columns at weight 2.0 (highlighted darker green via the `w-max` class).
   - Data sources: `_section_weights` and `_proposal_url` injected into `docs/validate/assets/rules.json`; rendered in `validate.js`'s `_renderRulesPalette`.
   - Visible on every validation page including Simon's: https://simondedman.github.io/elasmo_analyses/validate/A5086753224.html

2. **Per-column [?] inline disclosure — design preview, not yet wired into production:**
   - Mockup file: [`2026-04-20_validation_ui_mockup.html`](./2026-04-20_validation_ui_mockup.html). Open in a browser; click any [?] in the right pane to see what the popover would look like.
   - **Layout (post-Simon-feedback 2026-04-20):** popover widened to 960 px (was 640) to accommodate the section-weights matrix. The matrix has three rows:
     - **Section weighting** — the static per-section weights from the schema definition
     - **This paper** — the actual terms that fired in each section (e.g. "mercury ×2" under METHODS)
     - **Total score** — the weighted score per section AND the grand total in the rightmost column, colour-coded green when ≥ threshold (FIRED) or grey when below (did not fire)
   - Design rationale: the schema-level palette requires the validator to scroll to find rule details; the per-column [?] icon answers "what does this column actually look for, and what did it find on this paper?" without leaving the rating row.
   - Implementation cost: ~50 lines JS + ~60 lines CSS. No new data plumbing — same `rules.json` already feeds it. Per-paper hits per section are already computed by the extractor and would need to be exposed in the per-paper data file.
   - **TO REVIEW** at meeting; if endorsed, will be wired into `_renderPaperRow()` in a follow-up commit.

## Item 15 — IMP categories (full list, for review)

**21 main `imp_*` columns:**

| Column | Notes |
|---|---|
| `imp_mortality` | mortality, survival rate, AVM, DOA |
| `imp_post_release` | PRM, post-capture survival |
| `imp_abundance` | uses anchors |
| `imp_cpue` | catch per unit effort |
| `imp_biomass` | NO anchors (gap David flagged) |
| `imp_distribution` | range/habitat shifts |
| `imp_behaviour_change` | uses anchors |
| `imp_physiology_stress` | cortisol, lactate, RAMP |
| `imp_injury` | hooking injury, scarring |
| `imp_reproduction` | fecundity change |
| `imp_growth` | uses anchors |
| `imp_genetic` | diversity, Ne |
| `imp_trophic` | dietary shift, mesopredator release |
| `imp_habitat_quality` | David's xlsx row 18 — false negatives |
| `imp_contamination` | bioaccumulation |
| `imp_economic` | tourism revenue, WTP |
| `imp_social` | livelihood, attitude |
| `imp_community_composition` | uses anchors |
| `imp_biodiversity` | uses anchors |
| `imp_size_structure` | uses anchors |
| `imp_productivity` | uses anchors |

**Derived summary columns (referenced in xlsx row 26):**
- `imp_direction` — direction of impact (positive/negative/none)
- `imp_quantified` — whether impact was numerically quantified
- `imp_confidence` — overall confidence rating

These are computed post-extraction from the 21 binary columns + per-paper context. Action: locate the derivation logic; document the rule for the meeting.

**David's STRUCTURE merge (xlsx row 10):** propose `imp_injury` + `imp_physiology_stress` → `imp_health_assessment`. Schema-breaking; defer per Simon's note "Existing analyses are all moot and will be re-run before the presentation. Note that we'll review this point at the meeting." — so it's open, but the full impact-schema is on the table.

---

# Alex's notes (item §3)

Easy-review surface: yes — they live inside her validation JSON's per-paper `notes` fields. I extracted them; here are the substantive ones (rather than empty strings):

- **Paper 27537 / `imp_`:** "Does behaviour change = behavioral response?" — terminology question on `imp_behaviour_change`
- (Alex's other 7 papers had ratings without text notes — suggests low-friction UX, but limited qualitative feedback)

Plus the **author_corrections** block (silently dropped by old workflow until today's fix):
- gender: blank → F
- origin_country: RU → USA (NamSor mis-classification; see §4 below)
- ethnicity: British → United States

# Item §4 — NamSor source: name-only or name+context?

Verified from `scripts/enrich_namsor.py`:

| Field | NamSor endpoint | Inputs sent |
|---|---|---|
| `gender` | `genderGeoBatch` (if institution country known) or `genderBatch` | first + last name (+ country if available) |
| `origin_country` | `originBatch` | **first + last name ONLY** |
| `ethnicity` / `diaspora` | `diasporaBatch` | first + last name + country of residence (institution country) |

So:
- **Gender:** name (with country boost when we have it)
- **Origin country:** **name only** — this is why Alex's "Alexandra G. McInturf" → RU. Origin model has no idea where she was born/works; it predicts heritage from name patterns alone.
- **Ethnicity / diaspora:** name + country of residence. Predicts heritage GIVEN where the person lives. This is why Alex's diaspora answer was "British" (Scots-Irish heritage common in the US population).

The NamSor `originBatch` endpoint is unavoidably weak for low-frequency surnames in any context, and is especially weak for US-immigration-shaped name distributions (Scots-Irish, Italian-American, etc.). Audit suggestion: any author with `namsor_origin_score < 5` AND a US institution country is a high-likelihood mis-classification candidate.

