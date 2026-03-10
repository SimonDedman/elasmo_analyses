# Proposed Schema: Impact / Response Variables

**Status:** Draft for team discussion
**Column prefix:** `imp_`
**Source:** David Ruiz Garcia's reference paper (Issue #2), common fisheries/conservation impact metrics

## Purpose

Classify papers by the type of impact or response variable they measure. This is the hardest category to parse automatically, but potentially the most analytically valuable. Enables questions like "what proportion of papers actually quantify mortality?" or "are survival estimates increasing over time?"

## False Positive Mitigation

Many impact terms are common in general scientific writing (e.g., "abundance", "density", "stress", "recruitment"). To reduce false positives, the extraction strategy uses a **score-based probability system**:

1. **Single mention** of a term (e.g., "abundance" once in the abstract) = low confidence, flagged for review
2. **Multiple mentions** + co-occurring terms (e.g., "abundance" + "decline" + "population") = high confidence
3. **Context anchor terms** required for ambiguous keywords: e.g., `imp_abundance` requires "abundance" AND one of: "population", "decline", "increase", "change", "trend", "status"
4. **Whole-word matching** for short terms: "Ne" matches only as a whole word (effective population size), not as part of "nearshore"

## Proposed Categories

### Level 1: Impact Type

| Column | Label | Search Terms | Anchor/Context Required |
|--------|-------|-------------|------------------------|
| `imp_mortality` | Mortality/Survival | mortality, survival rate, lethality, dead on arrival, DOA, at-vessel mortality, AVM | None — distinctive terms |
| `imp_post_release` | Post-release Mortality | post-release mortality, PRM, delayed mortality, post-capture survival | None — distinctive compound terms |
| `imp_abundance` | Abundance Change | abundance, population size, population decline, population trend | Require co-occurrence with: population, decline, increase, change, trend, status |
| `imp_cpue` | CPUE/Catch Rate | CPUE, catch per unit effort, catch rate | None — distinctive terms. Removed "landing", "yield" (too generic) |
| `imp_biomass` | Biomass Change | biomass, standing stock, spawning stock biomass, SSB | None — distinctive terms |
| `imp_distribution` | Distribution Shift | distribution shift, range shift, range contraction, habitat shift | None — distinctive compound terms |
| `imp_behaviour_change` | Behavioural Change | behavioural change, behavioral change, avoidance behaviour, flight response, habituation | Require "change" or "response" as anchor |
| `imp_physiology_stress` | Physiological Stress | cortisol, lactate, blood chemistry, acid-base, reflex impairment, RAMP, physiological stress | Removed standalone "stress" — too generic |
| `imp_injury` | Injury/Condition | injury, hooking injury, scarring, body condition index | Removed standalone "wound", "hook" — too generic |
| `imp_reproduction` | Reproductive Impact | reproductive output, fecundity change, reproductive failure | Removed standalone "recruitment" — too generic |
| `imp_growth` | Growth Impact | growth rate change, stunting, condition factor change | Require "change" or "impact" as anchor with growth terms |
| `imp_genetic` | Genetic Impact | genetic diversity, effective population size, \bNe\b, bottleneck, inbreeding | Ne as whole word only |
| `imp_trophic` | Trophic/Dietary Impact | trophic level change, dietary shift, prey depletion, mesopredator release | None — distinctive compound terms |
| `imp_habitat_quality` | Habitat Quality | habitat quality, habitat suitability, degradation index | None |
| `imp_contamination` | Contamination Level | contaminant load, bioaccumulation, biomagnification, tissue concentration | None — distinctive terms |
| `imp_economic` | Economic Impact | economic value, fishery value, tourism revenue, willingness to pay, WTP | None |
| `imp_social` | Social/Human Impact | livelihood, food security, human dimension, attitude, perception | None |

### Direction & Magnitude (metadata columns, not binary)

| Column | Type | Description |
|--------|------|-------------|
| `imp_direction` | text | "negative", "positive", "mixed", "neutral", "not stated" |
| `imp_quantified` | boolean | Does the paper provide a quantitative measure of impact? |

## Extraction Strategy

Given the difficulty, a phased approach with score-based validation:

**Phase 1 (keyword + scoring):** Extract using keyword matching with the anchor/context rules above. Each match gets a confidence score:
- 3+ co-occurring terms = high confidence (auto-accept)
- 2 co-occurring terms = medium confidence (accept with flag)
- 1 mention only = low confidence (populate `imp_N_guess` column, not binary)

**Phase 2 (LLM):** For papers with PDFs, use LLM to classify: "Does this paper measure/quantify any of the following impact types?" Returns structured output supporting (not replacing) keyword extraction. This adds coverage for papers where impact is implicit.

**Phase 3 (validation):** Cross-reference with discipline to catch obvious misclassifications:
- FISH papers → likely imp_cpue, imp_mortality
- CON papers → likely imp_abundance, imp_economic
- BIO papers → likely imp_physiology_stress, imp_growth
- GEN papers → likely imp_genetic

Papers assigned an impact type inconsistent with their discipline are flagged for review.

## Discussion Points

1. **Overlap with pressure:** "Bycatch mortality" spans both pressure (bycatch) and impact (mortality). This is fine — they're orthogonal categorisations.
2. **Quantified vs mentioned:** The `imp_quantified` flag and confidence scoring together distinguish a paper that estimates mortality rate = 0.37 from one mentioning "mortality" in passing.
3. **Direction column:** Single text column. If a paper measures both positive and negative impacts, use "mixed".

---
*Draft created: 2026-03-10, revised with team feedback*
