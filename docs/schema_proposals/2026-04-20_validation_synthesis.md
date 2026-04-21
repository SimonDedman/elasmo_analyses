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

## 2. David's 27 proposed rule changes — by change type

Each rule can invoke multiple mechanisms; totals sum to > 27.

| Change type | # rules | Implementation cost | Database/processing impact |
|---|---|---|---|
| **KEYWORDS** — add/remove terms | 14 | **Low** — edit term lists in `extract_schema_columns.py` | Minimal; re-extract affected schemas |
| **SECTION priority** — require hits in Methods/Results, not Intro/Discussion | 9 | **Medium** — section detection already exists (99.8% coverage per MEMORY, corpus-trained). Need to wire per-column section weights | Re-extract: ~18K PDFs × 123 columns. ~6–10 h on current machine. |
| **ANCHORS** — require term + co-occurrence (e.g. "trawl" + "bottom") | 7 | **Medium** — new co-occurrence logic; would extend evidence schema | Re-extract; evidence CSV grows modestly |
| **THRESHOLD** — raise/lower existing per-column thresholds | 5 | **Trivial** | Re-extract only |
| **CONTEXT** — ignore background/comparison mentions | 3 | **Medium-high** — needs sentence-level context classification | Moderate processing overhead |
| **CORRELATION** — cross-column rules (e.g. if `trawl` strong and `bottom` near → `gear_trawl_otter`) | 2 | **Medium** — new post-processing pass | Small |
| **STRUCTURE** — merge categories (Injury + Physiological stress → "Health assessment") | 1 | **High** — schema-breaking. Affects all existing analyses | Parquet column changes; extraction_review_reference regen |
| **DEFINITION** — narrow "coastal" to nearshore-process focus | 1 | **Medium** — requires new sub-rule | Small |
| **SPECIES LIST** — add missing taxa (e.g. *Aetomylaeus bovinus*) | 1 | **Low** — species DB additions | Trivial |
| **DYNAMIC THRESHOLD** — scale by document length for short-format papers | 1 | **Medium** — new extraction feature | Small; requires word-count per PDF |
| **CONDITIONAL DEPENDENCY** — only derive direction/confidence if pressure/threat detected | 1 | **Low-medium** — post-processing gate | Small |

**Breakdown of effort:**
- **Low-cost batch (18 rules, ~45 min dev + 1 re-extract):** all KEYWORDS and THRESHOLD rules, plus SPECIES LIST addition → could be applied immediately
- **Medium-cost batch (19 rules with overlap, ~1–2 days dev):** SECTION priority, ANCHORS, CORRELATION, DYNAMIC THRESHOLD, DEFINITION, CONDITIONAL DEPENDENCY — requires one coordinated pipeline update
- **High-cost batch (1 rule):** STRUCTURE merge — needs team decision before implementation

---

## 3. David's 27 rules — key individual items

Priority ordering for meeting discussion. Full text in `/home/simon/Downloads/ruiz_garcia_validation_master.xlsx` (Validation_Rules sheet).

### Likely-adopt (low cost, clear fix)

1. **`b_` threshold consistency** (xlsx row 2) — `b_mediterranean` and `b_southern_ocean` use threshold=1 while others use 2. David asks whether this is deliberate. *(Per `ocean_basin_proposal.md` it IS deliberate: these sub-sea names are unambiguous single-mention signals. Document this in the meeting notes and retain.)*
2. **`eco_deepwater` keywords** (row 8) — add "deepwater" and "deep water" as variants alongside "deep-water"
3. **`d_fisheries` keywords** (row 6) — expand to include "bycatch", "discard", "retention", "non-target species"
4. **`sp_` species list** (row 23) — add *Aetomylaeus bovinus* (and likely other Mediterranean taxa missing from the dictionary)
5. **`imp_biomass` anchor** (row 11) — require biomass co-occurrence with response-variable language, not predictor
6. **`mit_ghost` reclassification** (row 19) — ghost gear currently under mitigation; David argues it's gear- or pressure-related

### Needs discussion (medium cost, design choice)

7. **Mediterranean sub-basin scheme** (row 3, plus Meta_Notes) — David proposes GFCM-aligned groupings: Western / Central / Adriatic / Eastern / Black Sea. Current scheme uses individual sea names (Alboran, Ligurian, Tyrrhenian…). Proposal is to use GFCM groups as the columns while keeping the current sea-names as keywords. **Question for team:** adopt GFCM grouping as the primary axis, or retain current granularity as a supplementary set?
8. **Section-weighted disciplines** (rows 4, 7) — `d_biology`, `d_physiology` over-fire when methodological terms appear only in literature-review context. Proposal: require Methods+Results co-presence. *(Section weighting is already trained per MEMORY; this is a matter of extending it to these columns.)*
9. **Dynamic thresholds for short-format papers** (rows 9, 25) — brief communications fail to meet threshold=2. Proposal: scale threshold by word count.
10. **Impact summary conditional dependency** (row 26) — don't populate `imp_direction`, `imp_quantified`, `imp_confidence` unless at least one pressure/threat or impact was detected. Simple post-processing rule.

### Needs design work

11. **"Coastal" definition** (row 14) — current keyword-frequency approach mis-classifies deep-sea papers that mention continental shelf. David proposes a process-focus definition (nearshore dynamics). Design question: is `eco_coastal` a location label or an ecosystem-type label? The answer drives the implementation.
12. **`pr_aquaculture` anchor + threshold** (row 15) — single-mention "aquaculture" as context currently triggers. Raise threshold and/or require co-term.
13. **`pollution_chemical`** (row 16) — broad "pollut*" root too aggressive. Needs specific-compound or context requirements.
14. **Analytical techniques transparency** (row 20) — David asks for the full keyword/synonym list per technique to be documented publicly. *(Action: export `a_` keyword dictionary from pipeline code to `docs/schema_proposals/analytical_techniques_keywords.md`.)*

### Defer / investigate

15. **`imp_structure` schema merge** (row 10) — proposal to collapse Injury + Physiological stress into "Health assessment". Schema-breaking; affects existing analyses. Defer to post-review-cycle restructure.

---

## 4. Alex's submission — highlights

- **Per-paper:** discipline and analytical-technique schemas dominate her "incorrect" ratings (Alex's papers span movement ecology / telemetry / behaviour). Suggests `a_` dictionary coverage is weak for newer tracking methods.
- **Notes:** one question on taxonomy — "Does behaviour change = behavioral response?" for `imp_behaviour_change`. Action: document the intended distinction (or merge if there isn't one).
- **Author corrections** (new data path — silently dropped by the old workflow):
  - `gender`: blank → F
  - `origin_country`: **RU** → **USA** (NamSor mis-classified her; fix upstream)
  - `ethnicity`: British → United States (conflation issue — see §5)

---

## 5. Upstream data-quality issue surfaced by Alex

NamSor returned `origin_country=RU` for Alexandra G. McInturf with 72% probability (alt GR). This appears to be a **rare-surname failure mode**: "McInturf" is a low-frequency Scots-Irish surname with weak surname prior in NamSor, so the model over-weights the first name "Alexandra" (strongly Russian-signalling).

**Actions:**
- Add her correction to `outputs/author_location_overrides.csv` once PR #11 merges
- Audit NamSor output for other rare-surname authors — identify systematic Russian-mis-classification pattern
- The `ethnicity: British → United States` correction suggests the UI presents "ethnicity" and "origin country" as interchangeable, which is a UX issue worth revisiting (ethnicity ≈ heritage; origin country ≈ nation of birth/residence — they should be separately labelled)

---

## 6. Meeting agenda suggestions

**Tuesday** (if narrower focus):
- Adopt the low-cost batch (§3 items 1–6) as immediate pipeline fixes — apply and re-extract
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

References to "§3 item N" below match the numbered list above.

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
- **Action item:** review the species-lookup build script (`scripts/clean_species_lookup.R`) and rerun against current Shark References + Sharkipedia + IUCN species lists to catch any other taxonomic-revision misses. The `species_match_sharkipedia_only` file is the audit trail — 133 species are in Sharkipedia but absent from EEA, suggesting the gap is wider than this one species.

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

**Trade-offs to discuss:**
1. **Lossy aggregation:** the current 8 sub-basin columns let analysts ask basin-specific questions (e.g. "Tyrrhenian-only papers"). Collapsing to 5 GFCM groups loses this. **Recommendation:** keep both — add the 5 GFCM columns alongside the 8 individual seas (5 new columns; minor cost). The GFCM columns become the analytical default; individual seas remain available for fine-grained queries. David's xlsx Meta_Notes already proposes "retaining current sea names as keywords" which is consistent with this approach.
2. **Black Sea:** GFCM does not include Black Sea as a Mediterranean sub-basin (it's a separate FAO statistical area). Keep `sb_black_sea` as its own column rather than rolling into `sb_eastern_mediterranean`.
3. **Sea of Marmara:** Mediterranean ↔ Black Sea transition. Currently its own column; GFCM treats it as part of Black Sea statistical area. Roll into `sb_black_sea`?

## Item 8 — SECTION priority + keyword expansion

David proposes adding "effect" and "affect" as anchors/discriminators. Both are useful (often the response-variable language we lack for `imp_biomass`).

**Additional analytical/measurement keywords proposed (for d_biology, item 4 in xlsx):**

Currently `d_biology` terms are: *life history, age and growth, growth rate, longevity, maturity, length-at-maturity, length-weight, vertebral band* (8 terms). Add:
- `analyzed`, `analysed`, `assessed`, `examined`, `investigated`, `determined`, `calculated`, `estimated`, `measured`, `quantified` — generic *measurement-action* anchors. Better as anchors than terms (would over-fire as raw terms).
- Concrete biological measurements not currently captured: `vertebral counts`, `band pair`, `gonadosomatic index`, `GSI`, `hepatosomatic index`, `HSI`, `Le Cren`, `Fulton's K`, `morphometric analysis`, `total length`, `precaudal length`, `disc width`

**Additional measurement-based keywords for d_physiology (item 7 in xlsx):**

Currently: *physiolog\*, metaboli\*, oxygen consumption, ventilation rate, blood gas, haematocrit, hematocrit, osmoregulat\*, thermoregulat\*, bioenergetic\** (10 terms). Add:
- `SMR`, `RMR`, `MMR` (case-sensitive — standard, routine, max metabolic rate)
- `aerobic scope`, `Ucrit`, `critical swimming speed`
- `heart rate`, `cardiac output`, `blood pressure`, `plasma osmolality`, `plasma cortisol`, `plasma lactate`
- `urea`, `TMAO`, `trimethylamine N-oxide`, `enzyme activity`, `Q10`, `Q\u2081\u2080`, `metabolic rate`

These keep the discipline narrow (measurement-based) per David's intent, rather than firing on a single Introduction reference to "physiology".

## Item 9 — TITLE and KEYWORDS sections (key gap)

**Confirmed gap:** the section detector in `extract_schema_columns.py` (lines 563-583) recognises ABSTRACT, INTRODUCTION, METHODS, RESULTS, RESULTS_AND_DISCUSSION, DISCUSSION, CONCLUSIONS — and bins everything else as OTHER (weight 0.25). It does **not** have explicit patterns for **TITLE** or the author-supplied **KEYWORDS** block. Both are currently swept into OTHER (the lowest-weight bucket).

**Why this matters:**
- Author-supplied keywords are the strongest possible "author intent" signal. If a paper lists "Mediterranean" or "discard mortality" as a keyword, the topic is unambiguously central — yet our pipeline treats it the same as a footer reference.
- Titles are similarly high-signal: the title is the author's chosen one-line summary.

**Proposed (avoids dynamic thresholds — Simon's preference):**
1. Add a **TITLE** virtual section that wraps `parquet.title` text and gets weight **2.0** for ALL schemas (highest possible).
2. Add a **KEYWORDS** section pattern matching the typical PDF block (`r"^\s*Key\s*[\- ]?words\s*[:.\-]"`) and weight **2.0** as well.
3. Update `_SECTION_WEIGHTS` to include these two new section types for every prefix.
4. Keep existing thresholds. The added weight should be enough that a single keyword-block hit + one body mention = passes threshold=2 for most columns.

**Estimated effort:** ~1 hour code, ~6 h re-extract on full corpus.

**This likely subsumes the dynamic-threshold proposal (item 9):** brief communications often have keyword sections and abstract-style titles; promoting these to weight 2.0 will let short-format papers reach threshold without introducing length-dependent logic.

## Item 10 — Conditional dependency (`imp_direction`/`quantified`/`confidence`)

These three columns are NOT in the IMP main block (the 21 columns listed below). They appear to be derived/summary columns produced post-extraction. Confirmation needed: where are they computed, and against what definition of "pressure/threat detected"?

**Possible definitions for "pressure/threat detected" (for meeting):**
- Any `pr_*` column = 1 (broad — fires on background mentions of "climate change")
- Any `pr_*` column = 1 AND scored above 1.5× threshold (strong signal)
- At least 2 `pr_*` columns = 1 (multi-stressor confirmation)
- Any `pr_*` column = 1 AND any `imp_*` column = 1 (both detected)

David's proposal of "any pressure OR any impact detected" is the simplest gate. Trivial post-processing: `if (any pr_* > 0 or any imp_* > 0) then keep imp_direction/quantified/confidence else null`.

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

**Recommended:** raise threshold from 1 to 2. Keep current keyword set. (Or: keep threshold 1 but require an anchor like `impact|effect|threat|interaction|surrounding|near|adjacent` — more precise but requires anchor-co-occurrence which is the medium-cost work item.)

## Item 13 — `pr_pollution_chemical`: rules already in place

**Current rule:** terms = `pollut*`, `contaminant*`, `heavy metal*`, `mercury`, `PCB`, `PFAS`, `pesticide*` (case-sensitive: PCB, PFAS); threshold = **3**.

**Analysis:** "pollut*" is one of seven terms. Threshold 3 means three TOTAL mentions across any combination. So a paper could fire purely from `pollut*` × 3 (e.g. "marine pollution" appears 3 times) — Simon is correct that the wildcard root IS contributing as a near-standalone trigger.

**David's complaint** is that "pollution" appears in passing (e.g. "global threats include climate change, pollution, and overfishing") and fires the column. Threshold 3 mitigates but doesn't eliminate this when the paper happens to use "pollution" as a keyword more than once.

**Options for meeting:**
- Replace `pollut*` with `chemical pollut*` (much narrower)
- Keep `pollut*` but require a specific compound anchor: `anchors=["heavy metal*", "mercury", "PCB", "PFAS", "pesticide*", "contaminant*"]`. Then "pollution" alone won't fire; needs co-occurrence with a specific compound term.
- Raise threshold to 5 (cosmetic; doesn't fix the root issue)

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

**Mockup HTML:** delivered separately as `docs/schema_proposals/2026-04-20_validation_ui_mockup.html` (single-page proof-of-concept showing the proposed disclosure pattern on a sample paper). Pending request — want me to build it now or after meeting input?

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

# Alex's notes (item §4)

Easy-review surface: yes — they live inside her validation JSON's per-paper `notes` fields. I extracted them; here are the substantive ones (rather than empty strings):

- **Paper 27537 / `imp_`:** "Does behaviour change = behavioral response?" — terminology question on `imp_behaviour_change`
- (Alex's other 7 papers had ratings without text notes — suggests low-friction UX, but limited qualitative feedback)

Plus the **author_corrections** block (silently dropped by old workflow until today's fix):
- gender: blank → F
- origin_country: RU → USA (NamSor mis-classification; see §5 below)
- ethnicity: British → United States

**Posting to issue #7:** willing to post a comment summarising Alex's substantive feedback + author_corrections to https://github.com/SimonDedman/elasmo_analyses/issues/7 — but holding off until you confirm. Comment text drafted in the next section (so you can review/amend before I post).

### Draft comment for issue #7

```
Validation submission received from Alexandra McInturf (2026-04-20, PR #11).

**Per-paper feedback (8 papers reviewed):**
- Mostly partially_correct/incorrect ratings on imp_, a_, ob_, and gear_ schemas.
- Sole substantive note: "Does behaviour change = behavioral response?" on
  imp_behaviour_change (paper literature_id 27537). Suggests we should clarify
  the distinction (or merge if there isn't one) in extraction_review_reference.md.

**Author-self-corrections** (newly captured by the validation pipeline):
- origin_country: RU → USA (NamSor's name-only origin model misclassified
  "Alexandra G. McInturf" as Russian — surname is rare Scots-Irish, model
  over-weighted "Alexandra" as Russian-signalling).
- ethnicity: British → United States (NamSor diaspora endpoint returned
  "British" with 33% probability — likely a heritage-vs-residence taxonomy
  conflation; flagging as a UX issue for the validation UI).
- gender: blank → F.

Action: add Alex's overrides to `outputs/author_location_overrides.csv`
once PR #11 merges, and audit other rare-surname authors for similar
NamSor mis-classifications.
```

# Item §5 — NamSor source: name-only or name+context?

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

