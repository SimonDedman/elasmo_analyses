# Validation Feedback Synthesis — 2026-04-20

**Source:**
- Alexandra G. McInturf — 8 papers reviewed, JSON submitted via UI (PR #11)
- David Ruiz-García — 6 papers reviewed (JSON, PR #12) + 27-rule master xlsx (`ruiz_garcia_validation_master.xlsx`)

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
