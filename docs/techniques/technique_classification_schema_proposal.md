# Technique Classification Schema Proposal

**Authors:** Analysis integrating feedback from Anouk (Genetics) and Ed Lavender (Movement)
**Date:** 2025-10-21
**Status:** PROPOSAL for review

---

## Executive Summary

Both panelists identified the same fundamental issue: **the current technique list conflates different types of scientific entities**. This document proposes a 6-dimensional classification schema that resolves this issue while maintaining the practical utility of the database.

**Proposed Solution:** Add 6 binary classification columns that allow each technique to be tagged with its type(s).

---

## The Problem

### Anouk's Observation (Genetics)
> "There is a blurred distinction between theoretical concepts, methods, tools and analyses"

### Ed's Observation (Movement)
> "You are mixing: (a) technologies, (b) descriptive/heuristic methods, (c) statistical models, (d) fitting methods, (e) software"

### Examples of the Mixing

| Technique | Current Status | Reality |
|-----------|---------------|---------|
| **Satellite Tracking** | Listed as technique | = Technology (data collection hardware) |
| **GAM SDM** | Listed as technique | = Statistical model class + Application domain |
| **Marxan** | Listed as technique | = Software (implements algorithms) |
| **Kernel Density Estimation** | Listed as technique | = Algorithm (can be implemented in many ways) |
| **Hidden Markov Models** | Listed as technique | = Statistical model class + Inference framework |
| **Population Genetics** | Listed as technique | = Conceptual field (contains many methods) |
| **FST Analysis** | Listed as technique | = Metric/measure + Analytical approach |

**The core issue:** These are fundamentally different types of things that happen to all appear in Methods sections of papers.

---

## Proposed Classification Schema

### Six Binary Dimensions

Each technique can be tagged with **one or more** of the following types:

#### 1. **DATA_COLLECTION_TECHNOLOGY** (Ed's "technologies")
**Definition:** Physical instruments, devices, or laboratory techniques used to generate raw data

**Rationale:** These are the "how we get data" entries. They require specific equipment, expertise, and infrastructure.

**Examples:**
- ✓ Satellite Tracking (requires satellite tags, receivers)
- ✓ Acoustic Telemetry (requires acoustic tags, hydrophone arrays)
- ✓ RAD-seq (requires restriction enzymes, sequencing platform)
- ✓ Whole Genome Sequencing (requires sequencers, library prep)
- ✓ eDNA sampling (requires water filtration, DNA extraction)

**Not examples:**
- ✗ GLMs (no physical instrument)
- ✗ Kernel Density Estimation (computational method)
- ✗ Marxan (software)

**Anouk's equivalent:** "Tools"

---

#### 2. **STATISTICAL_MODEL** (Ed's "statistical models")
**Definition:** Formal mathematical/statistical model families used for inference

**Rationale:** These entries represent specific probability distributions, likelihood structures, or statistical frameworks. They have mathematical definitions.

**Examples:**
- ✓ GLM (generalized linear models - formal statistical framework)
- ✓ GAM (generalized additive models - specific model class)
- ✓ Hidden Markov Models (formal stochastic process model)
- ✓ State-Space Models (formal time series model)
- ✓ GAMLSS (specific model family)

**Not examples:**
- ✗ Kernel Density Estimation (algorithm, not statistical model)
- ✗ Marxan (software)
- ✗ Satellite Tracking (data collection)

**Anouk's equivalent:** Part of "Methods"

---

#### 3. **ANALYTICAL_ALGORITHM** (Ed's "descriptive/heuristic methods")
**Definition:** Computational procedures, algorithms, or analytical approaches that transform data without formal statistical inference

**Rationale:** These are "recipes" for calculation that may not have an underlying statistical model. They can be deterministic or heuristic.

**Examples:**
- ✓ Kernel Density Estimation (algorithm for smoothing spatial data)
- ✓ Minimum Convex Polygon (geometric algorithm)
- ✓ Random Forest (machine learning algorithm)
- ✓ Principal Component Analysis (dimensionality reduction algorithm)
- ✓ ADMIXTURE (population clustering algorithm)
- ✓ FST calculation (population differentiation metric)

**Not examples:**
- ✗ GLM (statistical model)
- ✗ Acoustic Telemetry (data collection)

**Anouk's equivalent:** "Analyses"

---

#### 4. **INFERENCE_FRAMEWORK** (Ed's "ways of fitting models")
**Definition:** Mathematical/computational frameworks for parameter estimation and uncertainty quantification

**Rationale:** These describe **how** statistical models are fit to data, not **which** models are used.

**Examples:**
- ✓ Bayesian inference (framework for incorporating priors)
- ✓ Maximum Likelihood (optimization-based inference)
- ✓ Kalman Filtering (recursive estimation for state-space models)
- ✓ Markov Chain Monte Carlo (MCMC) (computational inference method)
- ✓ Hamiltonian Monte Carlo (HMC/NUTS) (specific MCMC variant)

**Not examples:**
- ✗ Hidden Markov Models (this is the MODEL, not the inference method)
- ✗ Stan (this is SOFTWARE that implements HMC)

**Anouk's equivalent:** Part of "Methods"

**Note:** Many current entries don't explicitly specify inference framework but could benefit from it.

---

#### 5. **SOFTWARE** (Ed's "software")
**Definition:** Named software packages, programs, or platforms that implement methods

**Rationale:** Software is distinct from the methods it implements. The same method might be implemented in multiple software packages.

**Examples:**
- ✓ Marxan (spatial prioritization software)
- ✓ STRUCTURE (Bayesian clustering software)
- ✓ Stan (probabilistic programming language)
- ✓ R-INLA (Bayesian inference via INLA)
- ✓ MaxEnt (software for SDMs - also an algorithm!)

**Not examples:**
- ✗ Hidden Markov Models (method, not software)
- ✗ Bayesian inference (framework, not software)

**Anouk's equivalent:** "Tools"

**Important distinction:** MaxEnt is BOTH an algorithm AND software (would be tagged with both)

---

#### 6. **CONCEPTUAL_FIELD** (Anouk's "theoretical concepts")
**Definition:** Broad research areas, conceptual frameworks, or domains of study that encompass multiple specific techniques

**Rationale:** These are "umbrella terms" that organize related methods. They're useful for literature search but aren't specific techniques.

**Examples:**
- ✓ Population Genetics (broad field containing FST, STRUCTURE, microsatellites, etc.)
- ✓ Conservation Genetics (applied field)
- ✓ Habitat Modeling (general approach)
- ✓ Home Range Analysis (research area)
- ✓ Species Distribution Modeling (SDM) (domain)
- ✓ Stress Physiology (research field)

**Not examples:**
- ✗ GLM SDM (specific method within SDM field)
- ✗ Acoustic Telemetry (specific technology)

**Anouk's equivalent:** "Theoretical concepts"

**Usage note:** These entries are valuable for search queries (cast wide net) but should be tagged so analysts know they're broad.

---

## Mapping to Panelists' Frameworks

### Integration Table

| This Proposal | Ed's Categories | Anouk's Categories |
|---------------|----------------|-------------------|
| DATA_COLLECTION_TECHNOLOGY | (a) Technologies | Tools |
| STATISTICAL_MODEL | (c) Statistical models | Methods |
| ANALYTICAL_ALGORITHM | (b) Descriptive/heuristic methods | Analyses |
| INFERENCE_FRAMEWORK | (d) Ways of fitting models | Methods |
| SOFTWARE | (e) Software | Tools |
| CONCEPTUAL_FIELD | *(not explicit in Ed's list)* | Theoretical concepts |

**Note:** Ed's framework is more methodological; Anouk's is more epistemological. Both are valid and complementary.

---

## Why Six Binary Columns Instead of One Categorical?

### Rationale for Binary (Multiple Tags Allowed)

**Many entries legitimately span multiple categories:**

| Technique | Multiple Classifications |
|-----------|------------------------|
| **MaxEnt** | SOFTWARE + ANALYTICAL_ALGORITHM |
| **Bayesian State-Space Models** | STATISTICAL_MODEL + INFERENCE_FRAMEWORK |
| **qPCR eDNA** | DATA_COLLECTION_TECHNOLOGY + (implicitly ANALYTICAL_ALGORITHM for quantification) |
| **Random Forest SDM** | ANALYTICAL_ALGORITHM + (applied to) CONCEPTUAL_FIELD |

**Benefits of binary columns:**
1. **Flexibility:** Techniques can have multiple types (accurate representation)
2. **Queryable:** Easy to filter "show me all SOFTWARE" or "all STATISTICAL_MODELs"
3. **Future-proof:** Can add new dimensions without restructuring
4. **Transparent:** Makes the mixing explicit rather than hidden

**Alternative considered and rejected:** Single categorical column with values like "Technology", "Statistical Model", etc.
- **Problem:** Doesn't handle multi-type entries (would require complex encoding like "Technology;Algorithm")
- **Problem:** Forces false choices (is MaxEnt software or algorithm? It's both!)

---

## Implementation Plan

### Phase 1: Add Classification Columns

Add 6 new binary columns to the spreadsheet:

```
is_data_collection_technology    (TRUE/FALSE)
is_statistical_model             (TRUE/FALSE)
is_analytical_algorithm          (TRUE/FALSE)
is_inference_framework           (TRUE/FALSE)
is_software                      (TRUE/FALSE)
is_conceptual_field              (TRUE/FALSE)
```

### Phase 2: Classification Guidelines

**For each technique, ask:**

1. **DATA_COLLECTION_TECHNOLOGY:** Does this require physical equipment or lab protocols to generate raw data?
   - Satellite tags? → TRUE
   - GLM? → FALSE

2. **STATISTICAL_MODEL:** Is this a formal statistical model family with mathematical definition?
   - GAM? → TRUE
   - Kernel Density? → FALSE (it's an algorithm)

3. **ANALYTICAL_ALGORITHM:** Is this a computational procedure/algorithm for transforming data?
   - Random Forest? → TRUE
   - Acoustic Telemetry? → FALSE

4. **INFERENCE_FRAMEWORK:** Is this a method for fitting models or estimating parameters?
   - Bayesian inference? → TRUE
   - Hidden Markov Model? → FALSE (that's the MODEL, not the fitting method)

5. **SOFTWARE:** Is this a named software package?
   - Marxan? → TRUE
   - GLM? → FALSE (GLMs are implemented in many software)

6. **CONCEPTUAL_FIELD:** Is this a broad research area containing multiple specific methods?
   - Habitat Modeling? → TRUE
   - Kernel Density Estimation? → FALSE (specific method)

### Phase 3: Example Classifications

| technique_name | TECH | STAT | ALGO | INFER | SOFT | FIELD |
|----------------|------|------|------|-------|------|-------|
| Satellite Tracking | ✓ | | | | | |
| Acoustic Telemetry | ✓ | | | | | |
| GLM SDM | | ✓ | | | | |
| GAM SDM | | ✓ | | | | |
| Hidden Markov Models | | ✓ | | | | |
| Kernel Density Estimation | | | ✓ | | | |
| Minimum Convex Polygon | | | ✓ | | | |
| Random Forest SDM | | | ✓ | | | |
| Bayesian inference | | | | ✓ | | |
| Kalman Filter | | | | ✓ | | |
| Marxan | | | | | ✓ | |
| STRUCTURE | | | | | ✓ | |
| MaxEnt | | | ✓ | | ✓ | |
| Population Genetics | | | | | | ✓ |
| Habitat Modeling | | | | | | ✓ |
| Species Distribution Model | | | | | | ✓ |
| Stress Physiology | | | | | | ✓ |
| Bayesian State-Space Models | | ✓ | | ✓ | | |
| qPCR eDNA | ✓ | | | | | |
| FST Analysis | | | ✓ | | | |
| PCA Genetics | | | ✓ | | | |

**Legend:**
- TECH = is_data_collection_technology
- STAT = is_statistical_model
- ALGO = is_analytical_algorithm
- INFER = is_inference_framework
- SOFT = is_software
- FIELD = is_conceptual_field

---

## Benefits of This Schema

### For Literature Search
- **Broad searches:** Use CONCEPTUAL_FIELD entries (e.g., "population genetics")
- **Specific searches:** Use STATISTICAL_MODEL or ANALYTICAL_ALGORITHM (e.g., "FST")
- **Technology searches:** Use DATA_COLLECTION_TECHNOLOGY (e.g., "eDNA")
- **Software-specific:** Use SOFTWARE to find implementation-specific papers

### For Panelists
- **Clear expectations:** Panelists know what type of thing they're reviewing
- **Appropriate expertise:** Can route SOFTWARE questions to users of that software
- **Hierarchical review:** Can review CONCEPTUAL_FIELDs at high level, then drill into specific methods

### For Database Integrity
- **Explicit mixing:** Makes the multi-type nature of entries transparent
- **Queryable:** Easy to filter and analyze by type
- **Documentation:** Future users understand what each entry represents

### For Future Expansion
- **New dimensions:** Can add new classification types if needed
- **Refinement:** Can split categories if they become too broad
- **Analysis:** Can analyze distribution of types across disciplines

---

## Potential Concerns and Responses

### Concern 1: "This adds complexity"
**Response:** The complexity already exists (that's the problem!). This schema makes it **explicit and manageable** rather than hidden and confusing.

### Concern 2: "How do we classify edge cases?"
**Response:** Binary columns allow multiple tags. If something is genuinely both SOFTWARE and ANALYTICAL_ALGORITHM (like MaxEnt), tag it as both. If unsure, document in notes column.

### Concern 3: "Will panelists fill this out correctly?"
**Response:**
1. We can pre-populate based on clear cases (e.g., all *-Tracking, *-Telemetry → DATA_COLLECTION_TECHNOLOGY)
2. Provide decision tree / flowchart for classification
3. Review classifications as team for consistency

### Concern 4: "Do we need all 6 dimensions?"
**Response:** We could start with 4-5 (maybe defer INFERENCE_FRAMEWORK if not many entries use it), but all 6 address real issues in the current list.

---

## Next Steps

1. **Review this proposal** with Anouk and Ed
   - Does this address their concerns?
   - Are the definitions clear?
   - Any missing dimensions?

2. **Pilot classification** with one discipline (e.g., Movement - Ed can validate)
   - Classify all 32 MOV techniques
   - Check for ambiguities or unclear cases
   - Refine definitions if needed

3. **Create decision tree** for classification
   - Visual flowchart to help with edge cases
   - Examples for each category

4. **Implement in spreadsheet**
   - Add 6 binary columns
   - Pre-populate obvious cases
   - Add data validation (TRUE/FALSE only)

5. **Distribute to panelists** with guidance
   - Brief explanation of schema
   - Request: review and flag disagreements
   - Collect feedback for refinement

---

## Alternative Approaches Considered

### Alternative 1: Single categorical column
**Rejected because:** Can't handle multi-type entries (MaxEnt, Bayesian SSMs, etc.)

### Alternative 2: Hierarchical parent-child relationships
**Rejected because:** Already exists in current schema (is_parent, parent_technique). This is orthogonal to type classification.

### Alternative 3: Free-text "type" field
**Rejected because:** Not queryable, inconsistent terminology, doesn't solve the problem

### Alternative 4: Separate the database into 6 sub-databases
**Rejected because:** Over-complicates, loses connections, makes literature search harder

---

## Conclusion

**The proposed 6-dimensional binary classification schema:**
1. ✅ Resolves both Anouk's and Ed's concerns
2. ✅ Makes existing mixing explicit and manageable
3. ✅ Maintains practical utility for literature search
4. ✅ Enables precise querying and filtering
5. ✅ Future-proof and extensible

**Recommendation:** Implement this schema and pilot with Movement discipline for validation.

---

## Appendix: Full Movement Discipline Example Classification

*[This would include the full 32 MOV techniques with proposed classifications - can generate if proposal is approved]*

---

**Questions for Review:**
1. Do these 6 dimensions adequately capture the classification issues?
2. Are the definitions clear and actionable?
3. Should we add/remove/merge any dimensions?
4. Are there specific techniques that don't fit this schema?
5. Should we pilot this before full implementation?
