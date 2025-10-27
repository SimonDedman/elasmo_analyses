# Technique Classification Schema - Visual Summary

**Quick Reference Guide**

---

## The Problem in One Image

### Current Database (Mixed Types)

```
┌─────────────────────────────────────────────────────────────┐
│  ALL LISTED AS "TECHNIQUES"                                 │
├─────────────────────────────────────────────────────────────┤
│  ❌ Satellite Tracking        (= Hardware)                  │
│  ❌ GAM                        (= Statistical model)         │
│  ❌ Marxan                     (= Software)                  │
│  ❌ Kernel Density             (= Algorithm)                 │
│  ❌ Bayesian inference         (= Fitting method)            │
│  ❌ Population Genetics        (= Research field)            │
└─────────────────────────────────────────────────────────────┘
       ↓
   CONFUSION: What are we actually searching for?
```

### Proposed Solution (Typed Entities)

```
┌──────────────────────────────────────────────────────────────┐
│  TYPED TECHNIQUES WITH CLEAR CLASSIFICATIONS                 │
├──────────────────────────────────────────────────────────────┤
│  ✓ Satellite Tracking        [TECH]                          │
│  ✓ GAM                        [STAT]                          │
│  ✓ Marxan                     [SOFT]                          │
│  ✓ Kernel Density             [ALGO]                          │
│  ✓ Bayesian inference         [INFER]                         │
│  ✓ Population Genetics        [FIELD]                         │
│  ✓ MaxEnt                     [ALGO + SOFT] (multi-type!)     │
└──────────────────────────────────────────────────────────────┘
       ↓
   CLARITY: We know what each entry represents
```

---

## Six Classification Types

### Quick Decision Tree

```
                    Is this entry a...?
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
    Physical          Mathematical       Conceptual
    Entity            Entity              Entity
        │                  │                  │
        ▼                  ▼                  ▼
  ┌──────────┐      ┌──────────┐      ┌──────────┐
  │   TECH   │      │   STAT   │      │   FIELD  │
  │   ALGO   │      │   INFER  │      │          │
  │   SOFT   │      │          │      │          │
  └──────────┘      └──────────┘      └──────────┘
```

### Type Definitions

| Type | Icon | Definition | Example |
|------|------|------------|---------|
| **DATA_COLLECTION_TECHNOLOGY** | 🔬 | Physical instruments/lab techniques for generating data | Satellite tags, eDNA sampling, RAD-seq |
| **STATISTICAL_MODEL** | 📊 | Formal mathematical model families | GLM, GAM, Hidden Markov Models |
| **ANALYTICAL_ALGORITHM** | 🔢 | Computational procedures for transforming data | Kernel Density, Random Forest, FST |
| **INFERENCE_FRAMEWORK** | 🎯 | Methods for fitting models to data | Bayesian, Maximum Likelihood, Kalman Filter |
| **SOFTWARE** | 💻 | Named software packages | Marxan, STRUCTURE, Stan |
| **CONCEPTUAL_FIELD** | 🌐 | Broad research areas | Population Genetics, Habitat Modeling |

---

## Classification Matrix - Movement Discipline Pilot

### Legend
- 🔬 = TECH (Data Collection Technology)
- 📊 = STAT (Statistical Model)
- 🔢 = ALGO (Analytical Algorithm)
- 🎯 = INFER (Inference Framework)
- 💻 = SOFT (Software)
- 🌐 = FIELD (Conceptual Field)

### Full Classification (32 Movement Techniques)

| # | Technique Name | Classifications |
|---|----------------|-----------------|
| 1 | Habitat Modeling | 🌐 |
| 2 | Species Distribution Model | 🌐 |
| 3 | Boosted Regression Trees SDM | 🔢 |
| 4 | Ensemble Models | 🔢 |
| 5 | GAM SDM | 📊 |
| 6 | GLM SDM | 📊 |
| 7 | **MaxEnt** | 🔢 + 💻 *(multi-type!)* |
| 8 | Neural Network SDM | 🔢 |
| 9 | Random Forest SDM | 🔢 |
| 10 | Joint Species Distribution Model | 🌐 |
| 11 | Connectivity | 🌐 |
| 12 | Home Range Analysis | 🌐 |
| 13 | Movement Modeling | 🌐 |
| 14 | AKDE | 🔢 |
| 15 | Brownian Bridge | 🔢 |
| 16 | Brownian Bridge Movement Model | 🔢 |
| 17 | Kernel Density Estimation | 🔢 |
| 18 | Minimum Convex Polygon | 🔢 |
| 19 | Hidden Markov Models | 📊 |
| 20 | Resource Selection Functions | 🔢 |
| 21 | State-Space Models | 📊 |
| 22 | Step Selection Functions | 🔢 |
| 23 | Network Analysis Spatial | 🔢 |
| 24 | Critical Habitat | 🌐 |
| 25 | MPA Design | 🌐 |
| 26 | Spatial Prioritization | 🌐 |
| 27 | Marxan | 💻 |
| 28 | Acoustic Telemetry | 🔬 |
| 29 | Archival Tags | 🔬 |
| 30 | Satellite Tracking | 🔬 |
| 31 | Residence Time Analysis | *[needs classification]* |
| 32 | VPS Positioning | 🔬 |

### Statistics

```
Distribution of Types (32 Movement techniques):

🔬 TECH:   4 techniques (12.5%) │████░░░░░░░░░░░░░░░░
📊 STAT:   4 techniques (12.5%) │████░░░░░░░░░░░░░░░░
🔢 ALGO:  13 techniques (40.6%) │████████████████░░░░
🎯 INFER:  0 techniques ( 0.0%) │░░░░░░░░░░░░░░░░░░░░
💻 SOFT:   2 techniques ( 6.2%) │██░░░░░░░░░░░░░░░░░░
🌐 FIELD:  9 techniques (28.1%) │███████████░░░░░░░░░

Multi-type entries: 1 (MaxEnt = ALGO + SOFT)
```

---

## Real-World Examples Showing the Difference

### Example 1: Hidden Markov Models (HMMs)

| Aspect | Classification | Notes |
|--------|----------------|-------|
| **The concept** | 📊 STATISTICAL_MODEL | Formal stochastic process model |
| **How it's fit** | 🎯 INFERENCE_FRAMEWORK | Could be MLE, Bayesian, etc. |
| **Implementation** | 💻 SOFTWARE | R package 'moveHMM', Python 'hmmlearn' |
| **Application domain** | 🌐 CONCEPTUAL_FIELD | Movement ecology, behavioral states |

**Current database:** "Hidden Markov Models" (ambiguous - which aspect?)
**With schema:** Tagged as 📊 STAT (the model itself)

---

### Example 2: Acoustic Telemetry Workflow

```
Study Design: "We used acoustic telemetry"
                        ↓
┌───────────────────────────────────────────────────────────┐
│  Step 1: DATA COLLECTION                                  │
│  → Acoustic Telemetry  [🔬 TECH]                          │
│     (physical receivers and tags)                         │
├───────────────────────────────────────────────────────────┤
│  Step 2: SPATIAL ANALYSIS                                 │
│  → Kernel Density Estimation  [🔢 ALGO]                   │
│     (smooth detection data into space use)                │
├───────────────────────────────────────────────────────────┤
│  Step 3: STATISTICAL MODELING                             │
│  → GAM  [📊 STAT]                                         │
│     (model space use ~ environmental covariates)          │
├───────────────────────────────────────────────────────────┤
│  Step 4: INFERENCE                                        │
│  → Bayesian inference  [🎯 INFER]                         │
│     (fit GAM with priors)                                 │
├───────────────────────────────────────────────────────────┤
│  Step 5: SOFTWARE                                         │
│  → R-INLA  [💻 SOFT]                                      │
│     (software for Bayesian GAM)                           │
└───────────────────────────────────────────────────────────┘
```

**Benefit of schema:** Each component is correctly classified. Literature search can target any level.

---

### Example 3: Population Structure Analysis

```
Research Question: "What's the genetic structure of this population?"
                              ↓
┌────────────────────────────────────────────────────────────┐
│  BROAD FIELD: Population Genetics  [🌐 FIELD]             │
│  (umbrella term for literature search)                     │
│                                                             │
│  SPECIFIC APPROACHES:                                       │
│  ├─ FST Analysis  [🔢 ALGO]                                │
│  │   (metric calculation)                                  │
│  │                                                          │
│  ├─ STRUCTURE  [💻 SOFT]                                   │
│  │   (Bayesian clustering software)                        │
│  │   └─ Uses: Bayesian inference  [🎯 INFER]              │
│  │                                                          │
│  └─ PCA  [🔢 ALGO]                                         │
│      (dimensionality reduction)                            │
│                                                             │
│  DATA SOURCE: Microsatellites  [🔬 TECH]                   │
│               (molecular markers)                           │
└────────────────────────────────────────────────────────────┘
```

**Current problem:** All listed together as "techniques"
**With schema:** Clear hierarchy and relationships

---

## Implementation in Spreadsheet

### Add 6 Binary Columns

```
Current columns:
┌──────────────────────────────────────────────────────┐
│ discipline | category | technique_name | description │
└──────────────────────────────────────────────────────┘

Add these columns:
┌─────────────────────────────────────────────────────────────────────┐
│ is_data_collection_technology  (TRUE/FALSE)                         │
│ is_statistical_model           (TRUE/FALSE)                         │
│ is_analytical_algorithm        (TRUE/FALSE)                         │
│ is_inference_framework         (TRUE/FALSE)                         │
│ is_software                    (TRUE/FALSE)                         │
│ is_conceptual_field            (TRUE/FALSE)                         │
└─────────────────────────────────────────────────────────────────────┘

Result:
┌────────────────────┬──────┬──────┬──────┬───────┬──────┬───────┐
│ technique_name     │ TECH │ STAT │ ALGO │ INFER │ SOFT │ FIELD │
├────────────────────┼──────┼──────┼──────┼───────┼──────┼───────┤
│ Satellite Tracking │  ✓   │      │      │       │      │       │
│ GAM SDM            │      │  ✓   │      │       │      │       │
│ MaxEnt             │      │      │  ✓   │       │  ✓   │       │
│ Population Genetics│      │      │      │       │      │   ✓   │
└────────────────────┴──────┴──────┴──────┴───────┴──────┴───────┘
```

---

## Use Cases After Implementation

### Use Case 1: Literature Search Strategy

**Query:** "Papers about shark movement using satellite tracking and GAMs"

```
Search components:
1. "shark" (species)
2. "movement" OR "tracking" (domain)
3. TECH entries: "Satellite Tracking" [🔬]
4. STAT entries: "GAM" [📊]

Benefit: Know we're searching for TECHNOLOGY + STATISTICAL MODEL
         (not confusing with software names or field terms)
```

---

### Use Case 2: Panelist Assignment

**Scenario:** New paper found mentioning "Marxan for critical habitat identification"

```
Technique: Marxan
Classifications: [💻 SOFT]

Action: Route to panelist who uses Marxan software
        (not just anyone who does spatial analysis)

Alternative: If it was "Network Analysis" [🔢 ALGO]
             Route to spatial analyst (method expertise)
```

---

### Use Case 3: Avoiding Redundancy

**Problem:** Multiple panelists reviewing same concept at different levels

```
Current (ambiguous):
- Panelist 1 reviews: "Species Distribution Model"
- Panelist 2 reviews: "GAM SDM"
- Panelist 3 reviews: "MaxEnt"

Are these the same? Different? Overlapping?

With schema (clear hierarchy):
- "Species Distribution Model" [🌐 FIELD] → General domain
- "GAM SDM" [📊 STAT] → Statistical approach within SDM
- "MaxEnt" [🔢 ALGO + 💻 SOFT] → Specific algorithm/software

Panelists now understand relationships and can avoid duplication
```

---

## Quality Checks After Classification

### Check 1: Disciplines should have different type distributions

```
Expected patterns:

Movement (MOV):
  High: ALGO (spatial analysis), TECH (tracking devices)
  Low: (depends on statistical sophistication)

Genetics (GEN):
  High: TECH (sequencing, markers), ALGO (structure analysis)
  Low: STAT (fewer formal statistical models)

Data Science (DATA):
  High: ALGO (ML methods), STAT (statistical models)
  Low: TECH (fewer physical tools)
```

### Check 2: CONCEPTUAL_FIELD entries should have children

```
Rule: If tagged as FIELD, should have specific methods as children

Example:
Population Genetics [🌐 FIELD]
  ├─ FST Analysis [🔢 ALGO] (child)
  ├─ STRUCTURE [💻 SOFT] (child)
  ├─ Microsatellites [🔬 TECH] (child)
  └─ ...

If FIELD has no children → might not be conceptual field
```

### Check 3: SOFTWARE should have corresponding method

```
Rule: Software implements methods/models

Marxan [💻 SOFT]
  → implements Spatial Prioritization [🌐 FIELD]
  → uses specific algorithms [🔢 ALGO]

STRUCTURE [💻 SOFT]
  → implements Bayesian clustering [🎯 INFER + 📊 STAT]

If SOFTWARE has no corresponding method → document what it does
```

---

## Frequently Asked Questions

### Q1: Can a technique have multiple types?
**A: Yes!** That's why we use binary columns. Example: MaxEnt is both ALGO and SOFT.

### Q2: What if I'm unsure about classification?
**A: Use the notes column** to document uncertainty. Team can review together.

### Q3: Do all 6 types need to be filled?
**A: No.** Most techniques will have 1-2 types. Having zero means needs review.

### Q4: What about techniques that could be two types?
**A: Tag both!** If something is legitimately both STAT and ALGO, mark both TRUE.

### Q5: How do we handle parent-child relationships?
**A: Separately.** Type classification is orthogonal to hierarchical structure.
   - is_parent / parent_technique → structural hierarchy
   - is_* columns → type classification

### Q6: What if new types emerge?
**A: Add new column.** Schema is extensible. Binary columns make this easy.

---

## Next Steps

1. ✅ **Review proposal** with Anouk and Ed
2. ⏳ **Pilot classification** complete for Movement (32 techniques)
3. ⏳ **Validate** pilot with Ed
4. ⏳ **Refine** definitions based on feedback
5. ⏳ **Implement** in full spreadsheet (218 techniques)
6. ⏳ **Distribute** to all panelists with guidance

---

## Summary: Before vs After

### Before (Current State)
```
❌ Mixed types unlabeled
❌ Unclear what each entry represents
❌ Hard to query precisely
❌ Panelists confused about level of detail
❌ Difficult to avoid redundancy
```

### After (With Schema)
```
✅ Explicit type classification
✅ Clear meaning of each entry
✅ Precise filtering possible
✅ Panelists understand context
✅ Hierarchical relationships visible
```

---

**Proposal Status:** Ready for review by Anouk (GEN) and Ed (MOV)

**Key Question:** Does this schema adequately address the classification concerns?
