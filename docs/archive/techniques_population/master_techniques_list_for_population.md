# Master Techniques List for Database Population

**Purpose:** Complete consolidated list of all techniques to populate `technique_taxonomy.db`
**Sources:** EEA 2025 data + Planned searches + Gap analysis additions
**Date:** 2025-10-13

---

## Summary

This document provides the **complete list of 129 techniques** across 8 disciplines that should be included in the master technique database. This list incorporates:

✅ All 40 techniques from EEA 2025 conference
✅ All 64 techniques from planned Shark-References searches
✅ All 24 techniques from gap analysis (missing from EEA + gaps in planned)
✅ Additional sub-techniques for hierarchical organization

---

## How to Use This Document

### For Manual CSV Creation:
Copy technique lists into `data/master_techniques.csv` with columns:
- `discipline_code`, `category_name`, `technique_name`, `is_parent`, `parent_technique`
- `description`, `synonyms`, `data_source`, `search_query`, `eea_count`

### For Database Population:
Use lists below to populate `techniques` table, linking to appropriate `category_id` values

### For Panelist Review:
Export this as formatted Excel with discipline tabs for expert feedback

---

## BIOLOGY, LIFE HISTORY, & HEALTH (23 techniques)

### Category: Age & Growth Methods (4 techniques)

| Technique | Parent | Description | Source | Search Query | EEA Count |
|-----------|--------|-------------|--------|--------------|-----------|
| **Age & Growth** | — | Age determination and growth rate studies | EEA | `+age +growth` | 7 |
| Vertebral Sectioning | Age & Growth | Age via vertebral band counts | EEA | `+vertebra* +section* +age` | 1 |
| Bomb Radiocarbon Dating | Age & Growth | Radiocarbon dating for age validation | planned | `+bomb +radiocarbon` OR `+C-14 +validation` | 0 |
| NIRS Ageing | Age & Growth | Near-infrared spectroscopy ageing | planned | `+NIRS +age` OR `+near +infrared +age` | 0 |

### Category: Reproductive Biology (6 techniques)

| Technique | Parent | Description | Source | Search Query | EEA Count |
|-----------|--------|-------------|--------|--------------|-----------|
| **Reproduction** | — | Reproductive biology studies | EEA | `+reproduct*` OR `+matur*` | 7 |
| Reproductive Histology | Reproduction | Histological examination of gonads | EEA+gap | `+histolog* +gonad*` OR `+histolog* +reproduct*` | 2 |
| Reproductive Endocrinology | Reproduction | Hormone analysis for reproduction | planned | `+endocrin* +hormone` OR `+reproduct* +hormone` | 0 |
| Ultrasound | Reproduction | Ultrasound for reproductive assessment | planned | `+ultrasound +pregnan*` OR `+ultrasound +gestation` | 0 |
| Captive Breeding | Reproduction | Ex-situ reproduction studies | planned | `+captive +breeding` OR `+aquarium +reproduction` | 0 |
| Fecundity Estimation | Reproduction | Litter size and fecundity | EEA | `+fecund*` OR `+litter +size` | (in Reproduction) |

### Category: Morphology & Morphometrics (4 techniques)

| Technique | Parent | Description | Source | Search Query | EEA Count |
|-----------|--------|-------------|--------|--------------|-----------|
| **Morphology** | — | Morphological analysis | EEA | `+morpholog*` | 1 |
| **Morphometrics** | — | Quantitative shape analysis | gap | `+morphometric*` OR `+geometric +morphometric*` | 0 |
| CT Imaging | Morphology | CT/MRI scanning for morphology | planned | `+CT +scan` OR `+MRI +morpholog*` | 0 |
| Body Measurements | Morphology | Biometric measurements | planned | `+biometric* +measurement` | 0 |

### Category: Physiology (5 techniques)

| Technique | Parent | Description | Source | Search Query | EEA Count |
|-----------|--------|-------------|--------|--------------|-----------|
| **Physiology** | — | Physiological studies | EEA | `+physiol*` | 1 |
| Metabolic Rate | Physiology | Oxygen consumption, metabolic studies | planned | `+metabol* +energetic*` OR `+oxygen +consumption` | 0 |
| Stress Physiology | Physiology | Cortisol and stress response | planned | `+stress +physiol*` OR `+cortisol` | 0 |
| Thermal Biology | Physiology | Temperature tolerance | planned | `+thermal +toleran*` OR `+temperature +physiol*` | 0 |
| Osmoregulation | Physiology | Salt/water balance | planned | `+osmoregulat*` OR `+salin* +tolerance` | 0 |

### Category: Disease, Parasites, & Health (4 techniques)

| Technique | Parent | Description | Source | Search Query | EEA Count |
|-----------|--------|-------------|--------|--------------|-----------|
| **Health & Disease** | — | Health assessment and disease | EEA | `+disease` OR `+patholog*` | 2 |
| Parasitology | Health & Disease | Parasite identification and burden | planned | `+parasit*` | 0 |
| Health Indices | Health & Disease | Condition scores | gap | `+health +index` OR `+condition +factor` | 0 |
| Telomere Analysis | — | Telomere length as aging/health proxy | planned | `+telomere* +aging` OR `+telomere* +senescence` | 0 |

---

## BEHAVIOUR & SENSORY ECOLOGY (14 techniques)

### Category: Behavioural Observation (6 techniques)

| Technique | Parent | Description | Source | Search Query | EEA Count |
|-----------|--------|-------------|--------|--------------|-----------|
| **Behavioural Observation** | — | Direct observation of behavior | EEA | `+behav* +observ*` | 2 |
| **Video Analysis** | — | Video-based behavioral analysis | EEA+gap | `+video +analysis` OR `+video +behav*` | 3 |
| Drone Observation | Video Analysis | UAV-based observation | gap | `+UAV +behav*` OR `+drone +track*` OR `+aerial +observ*` | 0 |
| Animal-Borne Cameras | Behavioural Observation | Camera tags (Crittercam) | planned | `+animal* +borne +camera` OR `+crittercam` | 0 |
| Accelerometry | Behavioural Observation | Accelerometer behavior classification | planned | `+acceleromet* +behav*` OR `+tri* +axial` | 0 |
| Predation Behavior | Behavioural Observation | Feeding and predation observations | planned | `+behav* +predation` OR `+feeding +behav*` | 0 |

### Category: Sensory Biology (5 techniques)

| Technique | Parent | Description | Source | Search Query | EEA Count |
|-----------|--------|-------------|--------|--------------|-----------|
| **Sensory Biology** | — | Sensory system studies | EEA | `+sensory` | 2 |
| Electroreception | Sensory Biology | Electrosensory studies | planned | `+electr* +sensory` OR `+ampulla* +lorenzini` | 0 |
| Olfaction | Sensory Biology | Olfactory studies | planned | `+olfact* +chemosens*` OR `+olfact* +chemorecept*` | 0 |
| Vision | Sensory Biology | Visual ecology and eye morphology | planned | `+vision +visual` OR `+eye +morpholog*` | 0 |
| Magnetoreception | Sensory Biology | Magnetic field detection | planned | `+magnet* +navigation` OR `+magnet* +reception` | 0 |

### Category: Social Behaviour (1 technique)

| Technique | Parent | Description | Source | Search Query | EEA Count |
|-----------|--------|-------------|--------|--------------|-----------|
| **Social Network Analysis** | — | Network analysis of social interactions | EEA | `+social +aggregation` OR `+social +network` OR `+PBSN` | 1 |

### Category: Cognition & Learning (2 techniques)

| Technique | Parent | Description | Source | Search Query | EEA Count |
|-----------|--------|-------------|--------|--------------|-----------|
| **Cognition** | — | Cognitive ability studies | EEA | `+learning +cognition` OR `+cognit*` | 4 |
| Learning Experiments | Cognition | Experimental learning studies | planned | `+learning +experiment*` OR `+condition* +behav*` | 0 |

---

## TROPHIC & COMMUNITY ECOLOGY (12 techniques)

### Category: Diet Analysis Methods (5 techniques)

| Technique | Parent | Description | Source | Search Query | EEA Count |
|-----------|--------|-------------|--------|--------------|-----------|
| **Diet Analysis** | — | Dietary studies | EEA | `+diet +prey` | 3 |
| **Stomach Content Analysis** | Diet Analysis | Traditional stomach contents | EEA | `+stomach +content` | 3 |
| **DNA Metabarcoding** | Diet Analysis | DNA-based diet identification | EEA | `+DNA +metabarcoding` OR `+diet +DNA` | 3 |
| **Stable Isotope Analysis** | — | Isotopic analysis for diet/trophic position | EEA | `+stable +isotop*` | 4 |
| Fatty Acid Analysis | Diet Analysis | Fatty acid signature analysis (QFASA) | planned | `+fatty +acid` OR `+QFASA` | 0 |

### Category: Trophic Position & Food Webs (4 techniques)

| Technique | Parent | Description | Source | Search Query | EEA Count |
|-----------|--------|-------------|--------|--------------|-----------|
| Trophic Level Estimation | — | Quantifying trophic position | planned | `+trophic +level` OR `+trophic +position` | 0 |
| Food Web Models | — | Network models of trophic interactions | planned | `+food +web` OR `+trophic +network` | 0 |
| Ecosystem Roles | — | Top-down effects, trophic cascades | planned | `+ecosystem +role` OR `+trophic +cascade` | 0 |
| Energy Flow | — | Energetics and productivity | planned | `+energy +flow` OR `+product* +trophic` | 0 |

### Category: Foraging Ecology (3 techniques)

| Technique | Parent | Description | Source | Search Query | EEA Count |
|-----------|--------|-------------|--------|--------------|-----------|
| Foraging Behavior | — | Observational foraging studies | planned | `+forag* +behav*` OR `+prey +selection` | 0 |
| Niche Partitioning | — | Resource partitioning studies | planned | `+niche +partition*` OR `+resource +partition*` | 0 |
| Prey Selection | Foraging Behavior | Selectivity and preference studies | planned | `+prey +select*` OR `+diet +select*` | 0 |

---

## GENETICS, GENOMICS, & eDNA (15 techniques)

### Category: Population Genetics (4 techniques)

| Technique | Parent | Description | Source | Search Query | EEA Count |
|-----------|--------|-------------|--------|--------------|-----------|
| **Population Genetics** | — | Population genetic structure | EEA | `+population +geneti*` | 2 |
| Microsatellites | Population Genetics | SSR markers | EEA | `+microsatellite* +SNP` OR `+SSR` | 1 |
| SNPs | Population Genetics | Single nucleotide polymorphisms | planned | `+SNP` OR `+single +nucleotide` | 0 |
| mtDNA | Population Genetics | Mitochondrial DNA analysis | planned | `+mtDNA` OR `+mitochondrial +DNA` | 0 |

### Category: Genomics (5 techniques)

| Technique | Parent | Description | Source | Search Query | EEA Count |
|-----------|--------|-------------|--------|--------------|-----------|
| **Genomics** | — | Whole genome approaches | EEA | `+genom* +sequenc*` | 3 |
| Whole Genome Sequencing | Genomics | Complete genome sequencing | EEA | `+whole +genome +sequenc*` OR `+WGS` | 1 |
| RAD-seq | Genomics | Restriction-site associated DNA sequencing | planned | `+RAD* +seq` OR `+ddRAD` | 0 |
| Transcriptomics | Genomics | RNA sequencing and gene expression | planned | `+transcriptom* +gene` OR `+RNA* +seq` | 0 |
| Comparative Genomics | Genomics | Cross-species genome comparisons | planned | `+comparative +genom*` | 0 |

### Category: Phylogenetics & Taxonomy (2 techniques)

| Technique | Parent | Description | Source | Search Query | EEA Count |
|-----------|--------|-------------|--------|--------------|-----------|
| **Phylogenetics** | — | Molecular phylogeny and phylogeography | EEA | `+phylogeny +molecular` OR `+phylogeograph*` | 1 |
| Ancient DNA | Phylogenetics | Historical DNA from museum specimens | planned | `+ancient +DNA` OR `+museum +specimen +DNA` | 0 |

### Category: eDNA & Metabarcoding (2 techniques)

| Technique | Parent | Description | Source | Search Query | EEA Count |
|-----------|--------|-------------|--------|--------------|-----------|
| **eDNA** | — | Environmental DNA detection | EEA | `+eDNA +environmental` OR `+environmental +DNA` | 2 |
| eDNA Metabarcoding | eDNA | Metabarcoding for biodiversity | planned | `+eDNA +metabarcode*` OR `+environmental +metabarcode*` | 0 |

### Category: Applied Genetics (2 techniques)

| Technique | Parent | Description | Source | Search Query | EEA Count |
|-----------|--------|-------------|--------|--------------|-----------|
| DNA Forensics | — | Species ID and trade monitoring | planned | `+DNA +forensic*` OR `+species +identification +DNA` | 0 |
| Conservation Genetics | — | Genetic diversity for conservation | planned | `+conservation +genetic*` | 0 |

---

---

## MOVEMENT, SPACE USE, & HABITAT MODELING (17 techniques)

### Category: Telemetry Methods (5 techniques)

| Technique | Parent | Description | Source | Search Query | EEA Count |
|-----------|--------|-------------|--------|--------------|-----------|
| **Acoustic Telemetry** | — | Acoustic tracking and monitoring | EEA | `+telemetry +acoustic` OR `+acoustic +tag*` | 11 |
| VPS Positioning | Acoustic Telemetry | Vemco Positioning System | gap | `+VPS +position*` OR `+vemco +position*` | 0 |
| Residence Time Analysis | Acoustic Telemetry | Detection and residence patterns | gap | `+residence +time` OR `+detection +acoustic` | 0 |
| **Satellite Tracking** | — | Satellite tagging (PSAT, SPOT) | planned | `+satellite +tracking` OR `+PSAT` OR `+SPOT +tag` | 0 |
| Archival Tags | — | Data-logging tags | planned | `+archival +tag*` OR `+data* +log* +tag` | 0 |

### Category: Movement Analysis (5 techniques)

| Technique | Parent | Description | Source | Search Query | EEA Count |
|-----------|--------|-------------|--------|--------------|-----------|
| **Movement Modeling** | — | Movement pattern analysis | EEA | `+migration +movement` OR `+movement +model*` | 3 |
| State-Space Models | Movement Modeling | SSM for animal movement | planned | `+state* +space +model*` OR `+SSM +movement` | 0 |
| Home Range Analysis | — | Home range estimation | planned | `+home +range` OR `+KDE +utilization` | 0 |
| Brownian Bridge | Home Range Analysis | Brownian bridge movement models | planned | `+brownian +bridge` OR `+BBMM` | 0 |
| **Connectivity** | — | Movement connectivity analysis | EEA | `+circuit* +connectivity` OR `+connect* +movement` | 2 |

### Category: Habitat Modeling (4 techniques)

| Technique | Parent | Description | Source | Search Query | EEA Count |
|-----------|--------|-------------|--------|--------------|-----------|
| **Habitat Modeling** | — | Habitat suitability modeling | EEA | `+habitat +model*` | 3 |
| **Species Distribution Model** | — | SDM/ENM approaches | EEA | `+SDM +distribution` OR `+species +distribution +model*` | 1 |
| MaxEnt | Species Distribution Model | Maximum entropy modeling | planned | `+MaxEnt` OR `+maximum +entropy +model*` | 0 |
| Ensemble Models | Species Distribution Model | Multi-model ensemble approaches | planned | `+ensemble +model* +SDM` OR `+ensemble +species +distribution` | 0 |

### Category: Spatial Conservation (3 techniques)

| Technique | Parent | Description | Source | Search Query | EEA Count |
|-----------|--------|-------------|--------|--------------|-----------|
| **MPA Design** | — | Marine protected area design | EEA | `+MPA +marine +protected` OR `+marine +reserve +design` | 7 |
| Critical Habitat | — | Critical habitat identification | planned | `+critical +habitat` OR `+essential +habitat` | 0 |
| Spatial Prioritization | — | Systematic conservation planning | planned | `+spatial +priorit*` OR `+conservation +planning +spatial` | 0 |

---

## FISHERIES, STOCK ASSESSMENT, & MANAGEMENT (17 techniques)

### Category: Stock Assessment (6 techniques)

| Technique | Parent | Description | Source | Search Query | EEA Count |
|-----------|--------|-------------|--------|--------------|-----------|
| **Stock Assessment** | — | Population assessment methods | planned | `+stock +assessment` | 0 |
| Age-Structured Models | Stock Assessment | Age-based stock assessment | planned | `+age* +structured +model*` OR `+stock +assessment +age` | 0 |
| Surplus Production Models | Stock Assessment | Biomass dynamic models | planned | `+surplus +production` OR `+biomass +dynamic*` | 0 |
| Integrated Models | Stock Assessment | Integrated stock assessment | planned | `+integrated +model* +stock` OR `+stock +synthesis` | 0 |
| Close-Kin Mark-Recapture | — | CKMR for abundance estimation | gap | `+close* +kin +mark*` OR `+CKMR` | 0 |
| Photo-ID | — | Photo-identification for abundance | planned | `+photo* +identif*` OR `+photo* +ID` | 0 |

### Category: Fishery-Dependent Data (3 techniques)

| Technique | Parent | Description | Source | Search Query | EEA Count |
|-----------|--------|-------------|--------|--------------|-----------|
| CPUE Standardization | — | Catch per unit effort analysis | planned | `+fishery +CPUE` OR `+CPUE +standardiz*` | 0 |
| Catch Data Analysis | — | Landings and catch analysis | planned | `+catch +per +unit` OR `+landings +data` | 0 |
| Fisher Interviews | — | Fisher knowledge and interviews | planned | `+fisher* +interview*` OR `+fisher* +knowledge` | 0 |

### Category: Bycatch & Mortality (3 techniques)

| Technique | Parent | Description | Source | Search Query | EEA Count |
|-----------|--------|-------------|--------|--------------|-----------|
| **Bycatch Assessment** | — | Bycatch estimation methods | EEA | `+bycatch +discard*` | 4 |
| Discard Mortality | Bycatch Assessment | Post-capture mortality | planned | `+mortality +fishing` OR `+discard +mortality` | 0 |
| Post-Release Survival | Bycatch Assessment | Survival after release | planned | `+post* +release +survival` OR `+release +mortality` | 0 |

### Category: Data-Poor Methods (3 techniques)

| Technique | Parent | Description | Source | Search Query | EEA Count |
|-----------|--------|-------------|--------|--------------|-----------|
| Data-Poor Assessment | — | Methods for data-limited stocks | gap | `+data* +poor +assess*` OR `+data* +limited` | 0 |
| Catch-MSY | Data-Poor Assessment | Catch-only MSY estimation | planned | `+catch* +MSY` OR `+CMSY` | 0 |
| Length-Based Methods | Data-Poor Assessment | Length-based assessment | planned | `+length* +based +assess*` OR `+LBB` | 0 |

### Category: Ecosystem-Based Management (2 techniques)

| Technique | Parent | Description | Source | Search Query | EEA Count |
|-----------|--------|-------------|--------|--------------|-----------|
| Ecosystem Models | — | Ecopath, Atlantis, EwE | planned | `+harvest +strategy` OR `+ecosystem +model*` | 0 |
| Multispecies Models | — | Multi-species interactions | planned | `+multispecies +model*` OR `+multi* +species +fishery` | 0 |

---

## CONSERVATION POLICY & HUMAN DIMENSIONS (16 techniques)

### Category: Conservation Assessment (3 techniques)

| Technique | Parent | Description | Source | Search Query | EEA Count |
|-----------|--------|-------------|--------|--------------|-----------|
| **IUCN Red List Assessment** | — | IUCN extinction risk assessment | EEA | `+conservation +status` OR `+IUCN +red +list` | 16 |
| Extinction Risk Models | IUCN Red List Assessment | Quantitative extinction risk | planned | `+extinction +risk` OR `+population +viability` | 0 |
| Vulnerability Assessment | — | Climate/threat vulnerability | planned | `+vulnerability +assessment` OR `+climate +vulnerab*` | 0 |

### Category: Policy & Governance (3 techniques)

| Technique | Parent | Description | Source | Search Query | EEA Count |
|-----------|--------|-------------|--------|--------------|-----------|
| **Policy Evaluation** | — | Policy effectiveness assessment | EEA | `+policy +management` OR `+policy +effectiveness` | 2 |
| Legislation Analysis | Policy Evaluation | Legal framework analysis | planned | `+legislation +effectiveness` OR `+legal +framework` | 0 |
| MPA Effectiveness | — | MPA performance evaluation | planned | `+MPA +effectiveness` OR `+marine +protected +effectiveness` | 0 |

### Category: Human Dimensions (2 techniques)

| Technique | Parent | Description | Source | Search Query | EEA Count |
|-----------|--------|-------------|--------|--------------|-----------|
| **Human Dimensions** | — | Human-wildlife interactions | EEA | `+human +dimension*` OR `+human* +shark +conflict` | 7 |
| Socioeconomic Analysis | Human Dimensions | Economic and social factors | planned | `+stakeholder +community` OR `+socio* +economic*` | 0 |

### Category: Trade & Markets (2 techniques)

| Technique | Parent | Description | Source | Search Query | EEA Count |
|-----------|--------|-------------|--------|--------------|-----------|
| **Trade & Markets** | — | Trade analysis and monitoring | EEA | `+CITES +protection` OR `+trade +monitoring` | 6 |
| Fin Trade Analysis | Trade & Markets | Shark fin trade specifics | gap | `+trade +fin* +market` OR `+shark +fin +trade` | 0 |

### Category: Participatory Approaches (3 techniques)

| Technique | Parent | Description | Source | Search Query | EEA Count |
|-----------|--------|-------------|--------|--------------|-----------|
| **Citizen Science** | — | Citizen science methods | EEA+gap | `+citizen +scien*` OR `+citizen +scien* +monitor*` | 2 |
| Co-Management | — | Participatory management | planned | `+co* +management` OR `+participatory +management` | 0 |
| Stakeholder Engagement | — | Stakeholder consultation processes | planned | `+stakeholder +engag*` OR `+participatory +process*` | 0 |

### Category: Tourism & Education (3 techniques)

| Technique | Parent | Description | Source | Search Query | EEA Count |
|-----------|--------|-------------|--------|--------------|-----------|
| **Tourism** | — | Ecotourism and dive tourism | EEA | `+ecosystem +service*` OR `+ecotourism` | 2 |
| Tourism Impact Assessment | Tourism | Tourism effects on populations | planned | `+tourism +impact*` OR `+dive +tourism +impact` | 0 |
| Education & Outreach | — | Conservation education effectiveness | planned | `+education +outreach` OR `+conservation +education` | 0 |

---

## DATA SCIENCE & INTEGRATIVE METHODS (15 techniques)

### Category: Machine Learning & AI (4 techniques)

| Technique | Parent | Description | Source | Search Query | EEA Count |
|-----------|--------|-------------|--------|--------------|-----------|
| **Machine Learning** | — | ML approaches (general) | EEA | `+machine +learning` OR `+random +forest` | 9 |
| Random Forest | Machine Learning | RF algorithm applications | EEA | `+random +forest` | (included in ML) |
| Neural Networks | Machine Learning | Artificial neural networks | planned | `+neural +network` OR `+ANN` | 0 |
| Deep Learning | Machine Learning | Deep learning approaches | planned | `+AI +artificial` OR `+deep +learning` | 0 |

### Category: Statistical Models (3 techniques)

| Technique | Parent | Description | Source | Search Query | EEA Count |
|-----------|--------|-------------|--------|--------------|-----------|
| GLM/GAM | — | Generalized linear/additive models | planned | `+GAM +generalized` OR `+GLM +model*` | 0 |
| GAMM | GLM/GAM | Generalized additive mixed models | planned | `+GAMM` OR `+generalized +additive +mixed` | 0 |
| Hierarchical Models | — | Multi-level/nested models | planned | `+hierarchical +model*` OR `+mixed +effect* +model*` | 0 |

### Category: Bayesian Approaches (3 techniques)

| Technique | Parent | Description | Source | Search Query | EEA Count |
|-----------|--------|-------------|--------|--------------|-----------|
| **Bayesian Methods** | — | Bayesian inference | EEA | `+Bayesian +model*` | 1 |
| JAGS/Stan | Bayesian Methods | MCMC software implementations | planned | `+JAGS` OR `+Stan +Bayesian` | 0 |
| INLA | Bayesian Methods | Integrated Nested Laplace Approximation | planned | `+INLA` OR `+integrated +nested +Laplace` | 0 |

### Category: Data Integration (2 techniques)

| Technique | Parent | Description | Source | Search Query | EEA Count |
|-----------|--------|-------------|--------|--------------|-----------|
| **Data Integration** | — | Multi-source data synthesis | EEA | `+data +integration` OR `+integrated +data` | 1 |
| **Meta-Analysis** | — | Systematic review and meta-analysis | EEA+gap | `+meta* +analysis` OR `+meta* +analysis +systematic` | 1 |

### Category: Time Series & Forecasting (3 techniques)

| Technique | Parent | Description | Source | Search Query | EEA Count |
|-----------|--------|-------------|--------|--------------|-----------|
| **Time Series** | — | Temporal analysis | EEA+gap | `+time +series +temporal` OR `+time +series` | 1 |
| ARIMA | Time Series | Autoregressive integrated moving average | planned | `+ARIMA` OR `+autoregressive +time +series` | 0 |
| Forecasting | Time Series | Predictive modeling | planned | `+forecast*` OR `+prediction +model*` | 0 |

---

## Summary Statistics

### Final Technique Count by Discipline

| Discipline | Parent Techniques | Sub-Techniques | Total | EEA Evidence |
|------------|-------------------|----------------|-------|--------------|
| Biology, Life History, & Health | 10 | 13 | 23 | 7 parent + 3 sub |
| Behaviour & Sensory Ecology | 8 | 6 | 14 | 4 parent + 0 sub |
| Trophic & Community Ecology | 9 | 3 | 12 | 4 parent + 0 sub |
| Genetics, Genomics, & eDNA | 12 | 3 | 15 | 5 parent + 1 sub |
| Movement, Space Use, & Habitat Modeling | 12 | 5 | 17 | 6 parent + 0 sub |
| Fisheries, Stock Assessment, & Management | 14 | 3 | 17 | 1 parent + 1 sub |
| Conservation Policy & Human Dimensions | 13 | 3 | 16 | 6 parent + 0 sub |
| Data Science & Integrative Methods | 11 | 4 | 15 | 4 parent + 1 sub |
| **TOTAL** | **89** | **40** | **129** | **37 parent + 6 sub** |

### Data Source Distribution

| Source | Count | Percentage |
|--------|-------|------------|
| EEA (Conference evidence) | 40 | 31.0% |
| Planned (Workflow doc) | 65 | 50.4% |
| Gap (Analysis additions) | 24 | 18.6% |
| **TOTAL** | **129** | **100%** |

### Search Query Coverage

- **Techniques with search queries:** 129 (100%)
- **Techniques with alternative queries:** ~80 (62%)
- **Techniques needing validation:** 129 (100% - none tested yet)
- **Expected result range:** 10-2000 papers per search

---

## Next Steps for CSV Creation

This markdown document should now be converted to CSV format with the following structure:

```csv
discipline_code,category_name,technique_name,is_parent,parent_technique,description,synonyms,data_source,search_query,search_query_alt,eea_count,notes
```

**Conversion Process:**
1. Extract all technique rows from tables above
2. Normalize formatting (remove markdown bold, special characters)
3. Add `is_parent` column (TRUE/FALSE based on "Parent" column)
4. Split multiple search queries into `search_query` and `search_query_alt` columns
5. Add `notes` column for panelist comments (blank initially)
6. Save as `data/master_techniques.csv`

---

*Document completed: 2025-10-13*
*Total techniques documented: 129 across 8 disciplines*
*Status: Ready for CSV conversion*
