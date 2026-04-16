# Proposed Schema: Impact / Response Variables

**Status:** Draft for team discussion
**Team lead:** David Ruiz-Garcia (DRG)
**Column prefix:** `imp_`
**Source:** David Ruiz Garcia's reference paper (Issue #2), common fisheries/conservation impact metrics

## Validation

Extracted classifications for this schema can be reviewed at <https://simondedman.github.io/elasmo_analyses/validate/>. Validators are encouraged to check papers associated with their own work and submit corrections via their OpenAlex author page.

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

## Columns Added 2026-03-16

Gap analysis against Beukhof et al. (2026) identified four impact/response categories used in their framework that were missing or insufficiently distinct in our schema.

| Column | Label | Search Terms | Anchor/Context Required | Threshold | Notes |
|--------|-------|-------------|------------------------|-----------|-------|
| `imp_community_composition` | Community Composition | community composition, assemblage composition, species composition, community structure change, assemblage shift | Require co-occurrence with: change, shift, impact, alter\* | 2 | Measures changes in multi-species assemblage structure. Distinct from `imp_abundance` (single-population focus) and `imp_trophic` (food web focus). |
| `imp_biodiversity` | Biodiversity | biodiversity loss, species richness change, diversity index, Shannon, Simpson, evenness change, species loss | Require co-occurrence with: change, loss, decline, impact | 2 | Diversity metrics (richness, evenness, indices). Complements `imp_community_composition` — biodiversity quantifies diversity per se, while community composition captures shifts in relative species abundance. |
| `imp_size_structure` | Size Structure | size structure, length frequency, age structure, size composition, size distribution, mean length, maximum length, length at maturity shift, truncated size | Require co-occurrence with: change, shift, impact, decline, truncat\* | 2 | Changes in population size/age structure from fishing pressure. Distinct from `imp_growth` (individual growth rates) — this column targets population-level structural shifts such as truncation of large size classes. |
| `imp_productivity` | Productivity | primary productivity change, secondary productivity, production decline, yield change, recruitment change, recruitment failure | Require co-occurrence with: change, decline, impact | 2 | Rate of biomass production at population or ecosystem level. Beukhof et al. (2026) define this as the rate of production of biomass, covering papers examining how fishing affects production/productivity of populations or ecosystems (20 papers in their review). Distinct from `imp_biomass` (standing stock) and `imp_reproduction` (reproductive output). |

### Updated Existing Columns

- **`imp_injury`**: Now also includes entanglement keywords (entangle\*, entanglement injury, net entanglement) to capture injury from gear interaction beyond hooking.
- **`imp_growth`**: Now also includes size/age structure keywords (growth-related size change, age-at-maturity shift) where they pertain to individual growth impacts rather than population-level size structure (see `imp_size_structure` for the latter).

**Rationale:** Beukhof et al. (2026) use community composition, biodiversity, size structure, and productivity as distinct response variable categories. Adding these ensures our schema can cross-reference with their classification. These columns also address a gap where population-level and ecosystem-level impacts were previously captured only through proxies (abundance, biomass, CPUE) without distinguishing the specific ecological dimension being measured.

## Derived Field: `imp_is_bycatch`

**Type:** Derived boolean (not a binary extraction column — computed from other fields)

**Purpose:** Infer whether elasmobranchs are bycatch in a non-elasmobranch fishery. Since the corpus is elasmobranch-focused, if a paper mentions bycatch AND identifies a non-elasmobranch target species (e.g. "tuna fishery", "prawn trawl"), the elasmobranchs are likely bycatch.

**Logic:**
1. If `pr_bycatch = 0` → `imp_is_bycatch = False` (no bycatch signal)
2. If `pr_bycatch = 1` AND `gear_target_species` contains a non-elasmobranch term (e.g. tuna, cod, shrimp) → `imp_is_bycatch = True`
3. If `pr_bycatch = 1` AND `gear_target_species` is null or contains only elasmobranch terms → `imp_is_bycatch = None` (ambiguous)

**Inputs:**
- `pr_bycatch` — binary column from pressure schema
- `gear_target_species` — free-text field extracted from patterns like "[X] fishery", "[X] longline", "[X] trawl", "directed at [X]"

**Elasmobranch target species list:** ~40+ common names and group terms including shark, ray, skate, elasmobranch, chondrichthyan, batoid, hammerhead, mako, thresher, manta, mobula, stingray, guitarfish, sawfish, chimaera, etc. Maintained as `_ELASMOBRANCH_TARGETS` in `extract_schema_columns.py`.

**Interpretation:**

| Value | Meaning | Example |
|-------|---------|---------|
| `True` | Elasmobranchs are likely bycatch | Paper about "tuna longline fishery" mentions shark bycatch |
| `False` | No bycatch signal | Paper is about shark biology with no bycatch context |
| `None` | Ambiguous | Paper mentions bycatch but target species is elasmobranch (bycatch may refer to other taxa), or no target species could be extracted |

**Limitations:**
- Depends on `gear_target_species` regex extraction quality — if the target species isn't captured, result is `None`
- Does not distinguish between "studying bycatch" and "mentioning bycatch in passing"
- A paper about a "shark fishery" mentioning bycatch of turtles would get `None`, not `False`

---
*Draft created: 2026-03-10, revised with team feedback*
*Updated: 2026-03-16, added 4 columns from Beukhof et al. comparison; updated imp_injury and imp_growth; added imp_is_bycatch derived field*
