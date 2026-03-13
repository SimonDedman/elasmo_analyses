# Comparison: Schiffman et al. 2020 vs EEA Data Panel Classification

*Internal project document. Last updated: 2026-03-12.*

---

## Purpose

This document maps two classification systems for elasmobranch research against each other: the manual coding scheme in Schiffman et al. (2020, *Copeia* 108(1):122-131) and our automated multi-label extraction pipeline. The goal is threefold: identify where the two systems align, clarify structural differences that prevent direct comparison, and evaluate whether the Schiffman coded dataset can serve as a validation benchmark for our classifier.

---

## System Summaries

### Schiffman et al. 2020

| Property | Detail |
|----------|--------|
| Corpus | 2,701 AES conference abstracts, 1985-2016 |
| Source text | Abstracts (~250 words each) |
| Classification | 22 research area categories |
| Assignment | Single primary category per abstract (48 dual exceptions) |
| Method | Manual coding by one person (DSS), scheme developed by all coauthors |
| Additional metadata | Study species, author gender, institution type, geographic scope |
| Paper location | `docs/schema_proposals/Schiffman_paper/` |

### EEA 2025 Data Panel

| Property | Detail |
|----------|--------|
| Corpus | ~30,500 peer-reviewed papers |
| Source text | Full PDF body text (references/acknowledgements stripped) |
| Classification | 106 binary columns across 6 schemas |
| Assignment | Multi-label: a paper triggers as many columns as its content warrants |
| Method | Automated frequency-based keyword matching with per-column score thresholds |
| Additional metadata | ~1,308 species columns, ~215 analytical techniques, depth extraction, impact direction |
| Technical docs | `docs/schema_proposals/extraction_logic.md` |

---

## Category Mapping

The table below maps each of the 22 Schiffman categories to the closest EEA column(s). Where our system distributes a single Schiffman category across multiple orthogonal schemas, all relevant columns are listed.

| Schiffman category | EEA column(s) | Notes |
|--------------------|---------------|-------|
| Age and Growth / Life History | `d_biology` | Our broadest discipline bucket; covers maturity, longevity, growth parameters |
| Behavior / Behavioral Ecology | `d_behaviour` | Direct match |
| Bioenergetics and Metabolism | `d_physiology` | Subsumed under physiology; no separate bioenergetics column |
| Biogeography / Distribution | `d_movement` + `eco_*` columns | Distribution work triggers movement and relevant ecosystem columns (e.g. `eco_pelagic`, `eco_reef`) |
| Biomechanics / Functional Morphology | `d_biomechanics` | Direct match |
| Conservation | `d_conservation` + `pr_*` + `gear_mit_*` | Our system decomposes conservation into discipline, pressures faced, and mitigation gear used |
| Diet / Feeding Ecology | `d_trophic` | Direct match |
| Ecosystem Role | `d_trophic` | Partial overlap; ecosystem-level trophic work (mesopredator release, trophic cascades) falls here |
| Ecotourism | `d_ecotourism` | Direct match |
| Fisheries Management | `d_fisheries` + `gear_*` columns | Gear schema captures fleet-level detail absent in Schiffman |
| Husbandry | `d_husbandry` | Direct match |
| Immunology | `d_immunology` | Direct match |
| Movement / Telemetry | `d_movement` | Direct match |
| Paleontology | `d_paleontology` | Direct match |
| Parasitology | `pr_disease` | Reframed as a pressure; no standalone parasitology discipline column |
| Physiology | `d_physiology` | Direct match |
| Population | `imp_abundance`, `imp_mortality`, `imp_cpue` | Population dynamics decomposed into measurable impact columns |
| Population Genetics | `d_genetics` + `imp_genetic` | Discipline plus impact on genetic diversity |
| Reproductive Biology | `d_reproductive` | Direct match |
| Sensory Biology and Physiology | `d_sensory` | Direct match |
| Shark Bites / Shark Repellent | `d_human_dimensions` | Partial; `pr_human_wildlife_conflict` proposed but not yet implemented |
| Social Science / Human Dimensions | `d_human_dimensions` | Direct match |
| Taxonomy | `d_taxonomy` | Direct match |
| Toxicology | `d_toxicology` | Direct match |

Of 22 Schiffman categories, 14 map directly to a single `d_*` discipline column. The remaining 8 either split across schemas (Conservation, Fisheries Management, Population Genetics), map to non-discipline columns (Population, Parasitology), or lose granularity by merging into a broader column (Bioenergetics into Physiology, Biogeography into Movement, Ecosystem Role into Trophic).

---

## Structural Differences

### 1. Exclusive vs multi-label assignment

Schiffman assigns one primary category per abstract. Our system fires every column whose threshold is met. A paper on bycatch mortality of reef sharks in a longline fishery could trigger `d_fisheries`, `d_conservation`, `eco_reef`, `pr_bycatch`, `gear_longline`, and `imp_mortality` simultaneously. This makes direct accuracy comparison against Schiffman codes non-trivial: a "correct" EEA classification must include the Schiffman label among potentially many active columns, not match it exclusively.

### 2. Manual vs automated

One trained coder reading 250-word abstracts will achieve high precision for well-defined categories. Our pipeline processes full-text PDFs at scale but relies on keyword frequency and anchor-term co-occurrence, which introduces false positives (a methods paper citing "longline" in its literature review) and false negatives (novel terminology absent from the dictionary). The tradeoff is precision at small scale vs coverage at large scale.

### 3. Orthogonal decomposition

Schiffman's 22 categories mix disciplinary framing with study context. "Conservation" conflates the research question (is this a conservation study?) with the pressures studied and the management tools discussed. Our system separates these into independent schemas: discipline (`d_conservation`), pressure (`pr_fishing`, `pr_habitat_loss`), and mitigation gear (`gear_mit_circle_hook`, `gear_mit_brd`). This decomposition avoids the ambiguity of a paper that studies fisheries bycatch in a conservation context.

### 4. Schemas without Schiffman equivalents

Three of our six schemas have no counterpart in Schiffman:

- **Ecosystem (`eco_`)**: 20 habitat/environment columns. Schiffman recorded geographic scope (ocean basin) but not habitat type.
- **Pressure (`pr_`)**: 23 threat columns. No equivalent.
- **Gear (`gear_`)**: 18 fishing gear and mitigation device columns. No equivalent.

These schemas were designed to answer questions Schiffman's system was not built for: which habitats are understudied, which pressures dominate the literature, and which gear types receive the most research attention.

### 5. Metadata differences

Schiffman coded author gender and institution type (academic, government, NGO, private). We did not initially capture these but are now adding them via OpenAlex institutional data and gender-guesser for first-name inference. Their geographic scope variable (ocean basin) maps to our `b_*` columns.

### 6. Source text quality

Abstracts are dense, self-contained summaries written to communicate the paper's core contribution. Full-text PDFs contain the same information plus noise: literature reviews discussing other topics, methods sections naming techniques used in cited studies, and taxonomic lists in supplementary material. Our section-stripping pipeline (removing references, acknowledgements, and front matter) mitigates this, but the signal-to-noise ratio remains lower than abstract-only classification.

---

## Validation Potential

The 2,701 coded abstracts represent a ready-made gold standard for the discipline dimension of our classifier, subject to three caveats.

**What would work well.** For the 14 categories that map cleanly to a single `d_*` column, we can test recall directly: of the abstracts Schiffman labelled "Behavior/Behavioral Ecology", what fraction does our pipeline flag as `d_behaviour = 1`? This gives a per-category recall estimate. Precision is harder to measure because our system is multi-label, but we can compute a "primary label accuracy" by checking whether the Schiffman label appears among the active columns.

**What would require care.** The 8 categories that split across schemas need manual mapping rules before comparison. "Conservation" abstracts, for instance, should probably count as correct if any of `d_conservation`, `pr_*`, or `gear_mit_*` fires. "Population" abstracts should count as correct if any of `imp_abundance`, `imp_mortality`, or `imp_cpue` fires. These mapping rules need to be agreed by the team before running validation.

**What would not transfer.** Schiffman coded conference abstracts; our pipeline processes journal papers. The populations differ: AES conference abstracts skew North American, younger-career, and shorter. Journal papers are global, peer-reviewed, and full-length. Performance on Schiffman's corpus may not generalise to the broader literature. Still, it is the best available labelled dataset for this domain.

---

## Practical Next Steps

1. **Obtain the coded dataset.** We have asked David Schiffman for the spreadsheet of 2,701 abstracts with category codes. Without the raw data, validation cannot proceed.
2. **Match abstracts to our corpus.** Cross-reference by DOI where available, otherwise by author-year-title fuzzy matching. Many AES abstracts may not have corresponding journal publications.
3. **Define mapping rules.** For the 8 split categories, write explicit rules specifying which combination of EEA columns constitutes a match. Document these in a validation protocol.
4. **Run per-category recall analysis.** For matched papers, compute recall and "primary label hit rate" for each of the 22 categories.
5. **Consider adding `pr_human_wildlife_conflict`.** The Shark Bites / Shark Repellent category currently has no precise EEA counterpart. If validation reveals a gap, this column should be implemented.
6. **Evaluate Parasitology treatment.** Schiffman treats it as a discipline; we frame it as a pressure (`pr_disease`). If parasitology papers are common enough, a dedicated `d_parasitology` column may be warranted.

---

## References

- Schiffman, D.S., Frazier, B.S., Daly-Engel, T.S., Kassam, K. & Pacoureau, N. (2020). Trends in chondrichthyan research: an analysis of three decades of conference abstracts from the American Elasmobranch Society. *Copeia*, 108(1), 122-131. PDF: `docs/schema_proposals/Schiffman_paper/`
- EEA extraction pipeline: `docs/schema_proposals/extraction_logic.md`
- Schema proposals: `docs/schema_proposals/{ecosystem_component,pressure,gear,impact}_proposal.md`
