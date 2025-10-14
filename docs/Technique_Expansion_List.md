# Technique Expansion List - To Add Before Panelist Review

**Date:** 2025-10-13
**Goal:** Add 50-80 techniques based on literature review and domain knowledge
**Status:** Draft for validation

---

## Summary

Based on web searches and domain knowledge, the following techniques should be added to maximize database completeness before panelist review.

**Rationale:** These are commonly used, well-established methods that appear in recent reviews and are standard in their respective fields.

---

## MOV - Movement, Space Use, & Habitat Modeling (ADD: 15 techniques)

### Category: Habitat Modeling - Species Distribution Models
**Current:** Species Distribution Model (parent), MaxEnt, Ensemble Models

**ADD Sub-techniques:**
1. **Random Forest** (for SDM)
   - Description: Machine learning ensemble method for SDM
   - Synonyms: RF
   - Search query: `+species +distribution +random +forest`
   - Source: Web search - widely used in SDM literature

2. **Boosted Regression Trees**
   - Description: Gradient boosting for SDM
   - Synonyms: BRT, GBM, Gradient Boosted Models
   - Search query: `+BRT +species +distribution` OR `+boosted +regression +tree*`
   - Source: Web search - top-performing SDM method

3. **Generalized Additive Models** (for SDM)
   - Description: GAMs for non-linear species-environment relationships
   - Synonyms: GAM, GAMM
   - Search query: `+GAM +species +distribution` OR `+additive +model* +habitat`
   - Source: Web search - standard SDM approach

4. **Generalized Linear Models** (for SDM)
   - Description: GLMs for species distribution
   - Synonyms: GLM, logistic regression
   - Search query: `+GLM +species +distribution` OR `+generalized +linear +model* +habitat`
   - Source: Domain knowledge

5. **Neural Network SDMs**
   - Description: Deep learning for species distribution
   - Synonyms: CNN for SDM, deep SDM
   - Search query: `+neural +network +species +distribution` OR `+deep +learning +SDM`
   - Source: Web search - emerging method

### Category: Movement Analysis - Home Range
**Current:** Home Range Analysis (parent), Residency Analysis

**ADD Sub-techniques:**
6. **Kernel Density Estimation**
   - Description: Probabilistic home range estimation
   - Synonyms: KDE, utilization distribution, UD
   - Search query: `+kernel +density +home +range` OR `+KDE +utilization +distribution`
   - Source: Web search - standard method

7. **Minimum Convex Polygon**
   - Description: Smallest polygon enclosing all relocations
   - Synonyms: MCP, convex hull
   - Search query: `+MCP +home +range` OR `+minimum +convex +polygon`
   - Source: Web search - most widely used baseline

8. **Brownian Bridge Movement Model**
   - Description: Path-based home range estimation accounting for movement between fixes
   - Synonyms: BBMM, dynamic Brownian bridge
   - Search query: `+brownian +bridge +home +range` OR `+BBMM +movement`
   - Source: Web search - modern approach

9. **Autocorrelated Kernel Density Estimator**
   - Description: KDE accounting for temporal autocorrelation
   - Synonyms: AKDE
   - Search query: `+AKDE +home +range` OR `+autocorrelat* +kernel +density`
   - Source: Domain knowledge

### Category: Movement Analysis - Movement Modeling
**Current:** Movement Modeling (parent), Migration Studies

**ADD Sub-techniques:**
10. **Hidden Markov Models** (movement)
    - Description: State-space models for behavioral state estimation
    - Synonyms: HMM, behavioral state models
    - Search query: `+hidden +markov +movement` OR `+HMM +behav* +state`
    - Source: Domain knowledge - widely used

11. **State-Space Models** (movement)
    - Description: Filtering location error and estimating movement parameters
    - Synonyms: SSM, Kalman filter
    - Search query: `+state +space +model* +movement` OR `+SSM +telemetry`
    - Source: Domain knowledge

12. **Step Selection Functions**
    - Description: Resource selection at movement step scale
    - Synonyms: SSF, integrated step selection
    - Search query: `+step +selection +function*` OR `+SSF +movement`
    - Source: Domain knowledge

13. **Resource Selection Functions**
    - Description: Habitat selection analysis
    - Synonyms: RSF, resource utilization functions
    - Search query: `+resource +selection +function*` OR `+RSF +habitat +selection`
    - Source: Domain knowledge

### Category: Spatial Conservation
**Current:** Critical Habitat Identification, Connectivity Analysis, MPA Design

**ADD Sub-techniques:**
14. **Network Analysis** (spatial)
    - Description: Graph theory for connectivity and MPA networks
    - Synonyms: Graph theory, circuit theory
    - Search query: `+network +analysis +connectivity +spatial` OR `+graph +theory +conservation`
    - Source: Domain knowledge

15. **Marxan / Zonation**
    - Description: Spatial prioritization software
    - Synonyms: Systematic conservation planning
    - Search query: `+marxan +conservation +planning` OR `+zonation +prioritization`
    - Source: Domain knowledge

---

## FISH - Fisheries, Stock Assessment, & Management (ADD: 18 techniques)

### Category: Stock Assessment
**Current:** Stock Assessment (parent), Age-Structured Models, Surplus Production Models, Integrated Models

**ADD Sub-techniques:**
1. **Statistical Catch-at-Age**
   - Description: Age-structured assessment using catch composition
   - Synonyms: SCA, catch-at-age analysis
   - Search query: `+statistical +catch +age` OR `+SCA +stock +assessment`
   - Source: Domain knowledge - standard method

2. **Stock Synthesis**
   - Description: Integrated age-structured assessment framework (NOAA)
   - Synonyms: SS3, Stock Synthesis 3
   - Search query: `+stock +synthesis +SS3` OR `+stock +synthesis +assessment`
   - Source: Web search - widely used

3. **Virtual Population Analysis**
   - Description: Cohort analysis for estimating fishing mortality
   - Synonyms: VPA, cohort analysis
   - Search query: `+VPA +virtual +population` OR `+cohort +analysis +fisheries`
   - Source: Domain knowledge

4. **Spawning Stock Biomass per Recruit**
   - Description: Per-recruit analysis for reference points
   - Synonyms: SSB/R, spawning potential ratio, SPR
   - Search query: `+spawning +biomass +recruit` OR `+SPR +fisheries`
   - Source: Domain knowledge

5. **Yield per Recruit**
   - Description: Per-recruit models for yield optimization
   - Synonyms: Y/R, yield-per-recruit analysis
   - Search query: `+yield +per +recruit` OR `+YPR +fisheries`
   - Source: Domain knowledge

6. **Delay-Difference Models**
   - Description: Population models incorporating somatic growth
   - Synonyms: Deriso-Schnute model
   - Search query: `+delay +difference +model* +stock` OR `+Deriso +Schnute`
   - Source: Domain knowledge

7. **Catch Curve Analysis**
   - Description: Mortality estimation from age/length composition
   - Synonyms: Catch curve, age-based mortality
   - Search query: `+catch +curve +mortality` OR `+catch +curve +analysis`
   - Source: Domain knowledge

### Category: Data-Poor Methods
**Current:** Data-Poor Methods (parent), Length-Based Assessment, Productivity-Susceptibility Analysis

**ADD Sub-techniques:**
8. **LIME** (Length-based Integrated Mixed Effects)
   - Description: Length-based assessment with recruitment variability
   - Synonyms: Length-based integrated assessment
   - Search query: `+LIME +length +based +assessment` OR `+length +integrated +mixed +effects`
   - Source: Web search - modern data-poor method

9. **LBSPR** (Length-Based Spawning Potential Ratio)
   - Description: SPR estimation from length composition
   - Synonyms: Length-based SPR
   - Search query: `+LBSPR +spawning +potential` OR `+length +based +SPR`
   - Source: Domain knowledge

10. **Catch-MSY**
    - Description: Data-limited method using catch and priors
    - Synonyms: CMSY
    - Search query: `+catch +MSY +data +poor` OR `+CMSY +stock +assessment`
    - Source: Domain knowledge

11. **Depletion Methods**
    - Description: Abundance estimation from catch and effort decline
    - Synonyms: Leslie-DeLury, depletion estimators
    - Search query: `+depletion +method* +abundance` OR `+Leslie +DeLury`
    - Source: Domain knowledge

12. **Life History Invariant Methods**
    - Description: Natural mortality estimators (Hoenig, Pauly, etc.)
    - Synonyms: M estimators, empirical mortality
    - Search query: `+natural +mortality +Hoenig` OR `+natural +mortality +Pauly`
    - Source: Domain knowledge

### Category: CPUE & Abundance
**Current:** CPUE Standardization (parent), Mark-Recapture, N-Mixture Models

**ADD Sub-techniques:**
13. **GLM CPUE Standardization**
    - Description: Generalized linear models for CPUE
    - Synonyms: GLM standardization
    - Search query: `+GLM +CPUE +standardization`
    - Source: Domain knowledge

14. **GAM CPUE Standardization**
    - Description: Generalized additive models for CPUE
    - Synonyms: GAM standardization, non-linear CPUE
    - Search query: `+GAM +CPUE +standardization`
    - Source: Domain knowledge

15. **Random Forest CPUE**
    - Description: Machine learning for CPUE standardization
    - Synonyms: RF CPUE
    - Search query: `+random +forest +CPUE` OR `+machine +learning +CPUE +standardization`
    - Source: Domain knowledge - emerging

16. **Distance Sampling**
    - Description: Abundance estimation accounting for detection probability
    - Synonyms: Line transect, strip transect
    - Search query: `+distance +sampling +abundance` OR `+line +transect +fish*`
    - Source: Domain knowledge

### Category: Bycatch & Interactions
**Current:** Bycatch Assessment, Bycatch Mitigation, Discard Mortality, Depredation Studies

**ADD Sub-techniques:**
17. **Post-Release Mortality**
    - Description: Survival estimation after release
    - Synonyms: Release mortality, discard survival
    - Search query: `+post +release +mortality` OR `+discard +survival`
    - Source: Domain knowledge

18. **Observer Coverage Analysis**
    - Description: Extrapolating bycatch from observer data
    - Synonyms: Observer program analysis
    - Search query: `+observer +coverage +bycatch` OR `+observer +data +extrapolation`
    - Source: Domain knowledge

---

## DATA - Data Science & Integrative Methods (ADD: 20 techniques)

### Category: Machine Learning & AI
**Current:** Machine Learning (parent), Random Forest, Neural Networks, Deep Learning

**ADD Sub-techniques:**
1. **Boosted Regression Trees** (general ML)
   - Description: Gradient boosting machine learning
   - Synonyms: BRT, GBM, XGBoost, gradient boosting
   - Search query: `+boosted +regression +tree*` OR `+GBM +XGBoost`
   - Source: Domain knowledge

2. **Support Vector Machines**
   - Description: Classification and regression ML method
   - Synonyms: SVM, support vector regression
   - Search query: `+support +vector +machine*` OR `+SVM +classification`
   - Source: Domain knowledge

3. **Convolutional Neural Networks**
   - Description: Deep learning for image/spatial data
   - Synonyms: CNN, ConvNet
   - Search query: `+convolutional +neural +network*` OR `+CNN +deep +learning`
   - Source: Domain knowledge

4. **Ensemble Learning**
   - Description: Combining multiple models
   - Synonyms: Model averaging, stacking
   - Search query: `+ensemble +learning +model*` OR `+model +averaging`
   - Source: Domain knowledge

5. **Computer Vision**
   - Description: Image/video analysis with ML
   - Synonyms: Image recognition, object detection
   - Search query: `+computer +vision` OR `+image +recognition +fish*`
   - Source: Domain knowledge - growing field

### Category: Statistical Models
**Current:** Generalized Linear Models (parent), GAMs, Mixed Effects Models, Time Series Analysis

**ADD Sub-techniques:**
6. **Generalized Additive Mixed Models**
   - Description: GAMs with random effects
   - Synonyms: GAMM
   - Search query: `+GAMM +generalized +additive +mixed` OR `+GAMM +model*`
   - Source: Domain knowledge

7. **Generalized Estimating Equations**
   - Description: Marginal models for correlated data
   - Synonyms: GEE
   - Search query: `+generalized +estimating +equation*` OR `+GEE +correlated +data`
   - Source: Domain knowledge

8. **Hierarchical Models**
   - Description: Multi-level statistical models
   - Synonyms: Multilevel models, nested models
   - Search query: `+hierarchical +model* +statistical` OR `+multilevel +model*`
   - Source: Domain knowledge

9. **ARIMA Models**
   - Description: Autoregressive integrated moving average
   - Synonyms: Time series forecasting, Box-Jenkins
   - Search query: `+ARIMA +time +series` OR `+autoregressive +model*`
   - Source: Domain knowledge

10. **Structural Equation Modeling**
    - Description: Multivariate causal modeling
    - Synonyms: SEM, path analysis
    - Search query: `+structural +equation +model*` OR `+SEM +causal +analysis`
    - Source: Domain knowledge

### Category: Bayesian Methods
**Current:** Bayesian Inference (parent), MCMC Methods, State-Space Models

**ADD Sub-techniques:**
11. **INLA**
    - Description: Integrated Nested Laplace Approximation for spatial models
    - Synonyms: R-INLA
    - Search query: `+INLA +bayesian +spatial` OR `+integrated +nested +laplace`
    - Source: Domain knowledge - widely used

12. **Stan**
    - Description: Probabilistic programming language for Bayesian inference
    - Synonyms: RStan, PyStan
    - Search query: `+Stan +bayesian +inference` OR `+RStan +model*`
    - Source: Domain knowledge

13. **JAGS**
    - Description: Just Another Gibbs Sampler for Bayesian models
    - Synonyms: rjags
    - Search query: `+JAGS +bayesian +model*` OR `+gibbs +sampl*`
    - Source: Domain knowledge

14. **Approximate Bayesian Computation**
    - Description: Likelihood-free Bayesian inference
    - Synonyms: ABC, simulation-based inference
    - Search query: `+approximate +bayesian +computation` OR `+ABC +likelihood +free`
    - Source: Domain knowledge

15. **Bayesian Network Analysis**
    - Description: Probabilistic graphical models
    - Synonyms: Belief networks, Bayes nets
    - Search query: `+bayesian +network +analysis` OR `+belief +network*`
    - Source: Domain knowledge

### Category: Data Integration
**Current:** Integrated Population Models (parent), Data Integration (parent), Meta-Analysis, Systematic Review

**ADD Sub-techniques:**
16. **Occupancy Modeling**
    - Description: Estimating occurrence accounting for detection
    - Synonyms: Occupancy models, presence-absence
    - Search query: `+occupancy +model* +detection` OR `+presence +absence +detection +probability`
    - Source: Domain knowledge

17. **N-Mixture Models**
    - Description: Abundance from repeated counts
    - Synonyms: Binomial mixture models
    - Search query: `+N +mixture +model*` OR `+binomial +mixture +abundance`
    - Source: Domain knowledge

18. **Multi-Species Models**
    - Description: Joint modeling of multiple species
    - Synonyms: Community models, joint SDM
    - Search query: `+multi +species +model*` OR `+joint +species +distribution`
    - Source: Domain knowledge

19. **Data Fusion**
    - Description: Combining disparate data sources
    - Synonyms: Data integration, multi-source analysis
    - Search query: `+data +fusion +integration` OR `+multi +source +data`
    - Source: Domain knowledge

20. **Cross-Validation**
    - Description: Model validation and selection
    - Synonyms: k-fold CV, LOOCV
    - Search query: `+cross +validation +model +selection` OR `+k +fold +validation`
    - Source: Domain knowledge

---

## TRO - Trophic & Community Ecology (ADD: 8 techniques)

### Category: Diet Analysis
**Current:** Stable Isotope Analysis (parent), Stomach Content Analysis, Fatty Acid Analysis, DNA Metabarcoding, Compound-Specific Isotopes, Amino Acid Isotopes

**ADD Sub-techniques:**
1. **SIAR / MixSIAR**
   - Description: Bayesian mixing models for isotope data
   - Synonyms: Stable isotope mixing models
   - Search query: `+SIAR +isotope +mixing` OR `+MixSIAR +diet`
   - Source: Domain knowledge - standard software

2. **IsoSpace**
   - Description: Bayesian niche space estimation from isotopes
   - Synonyms: Isotopic niche
   - Search query: `+IsoSpace +isotope +niche` OR `+isotopic +niche +space`
   - Source: Domain knowledge

3. **Trophic Position Calculation**
   - Description: Estimating trophic level from isotopes
   - Synonyms: Trophic level, TP calculation
   - Search query: `+trophic +position +isotope*` OR `+trophic +level +calculation`
   - Source: Domain knowledge

### Category: Food Webs & Community
**Current:** Food Web Analysis (parent), Community Ecology (parent), Ecopath/Ecosim, Species Interactions

**ADD Sub-techniques:**
4. **Network Analysis** (food web)
   - Description: Graph theory for food web structure
   - Synonyms: Food web networks, trophic networks
   - Search query: `+network +analysis +food +web` OR `+trophic +network*`
   - Source: Domain knowledge

5. **PERMANOVA**
   - Description: Permutational multivariate analysis of variance
   - Synonyms: Permutational ANOVA, non-parametric MANOVA
   - Search query: `+PERMANOVA +community +analysis` OR `+permutation* +ANOVA`
   - Source: Domain knowledge - widely used

6. **nMDS / NMDS**
   - Description: Non-metric multidimensional scaling for community composition
   - Synonyms: Non-metric MDS, ordination
   - Search query: `+NMDS +community +composition` OR `+non +metric +multidimensional +scaling`
   - Source: Domain knowledge

### Category: Foraging & Energetics
**Current:** Foraging Ecology (parent), Bioenergetics Modeling

**ADD Sub-techniques:**
7. **Optimal Foraging Theory**
   - Description: Modeling foraging decisions
   - Synonyms: OFT, foraging models
   - Search query: `+optimal +foraging +theory` OR `+OFT +foraging +behav*`
   - Source: Domain knowledge

8. **Dynamic Energy Budget**
   - Description: Physiological energetics modeling
   - Synonyms: DEB theory, DEB models
   - Search query: `+dynamic +energy +budget` OR `+DEB +theory +model*`
   - Source: Domain knowledge

---

## BEH - Behaviour & Sensory Ecology (ADD: 6 techniques)

### Category: Behavioural Observation
**Current:** Behavioural Observation (parent), Video Analysis (parent), Drone Observation, Animal-Borne Cameras, Accelerometry, Predation Behavior

**ADD Sub-techniques:**
1. **Ethogram Development**
   - Description: Standardized behavioral catalog
   - Synonyms: Behavioral repertoire
   - Search query: `+ethogram +behav* +catalog` OR `+behav* +repertoire`
   - Source: Domain knowledge

2. **Focal Sampling**
   - Description: Continuous observation of individual
   - Synonyms: Focal animal sampling
   - Search query: `+focal +sampling +behav*` OR `+focal +animal +observation`
   - Source: Domain knowledge

3. **Scan Sampling**
   - Description: Instantaneous group behavior recording
   - Synonyms: Instantaneous sampling
   - Search query: `+scan +sampling +behav*` OR `+instantaneous +sampling`
   - Source: Domain knowledge

4. **BORIS**
   - Description: Behavioral observation software
   - Synonyms: Behavioral Observation Research Interactive Software
   - Search query: `+BORIS +behav* +observation +software`
   - Source: Domain knowledge

### Category: Cognition & Learning
**Current:** Cognition (parent), Learning Experiments

**ADD Sub-techniques:**
5. **Operant Conditioning**
   - Description: Experimental learning paradigms
   - Synonyms: Conditioning experiments
   - Search query: `+operant +condition* +learning` OR `+reinforcement +learning +fish*`
   - Source: Domain knowledge

6. **Cognitive Testing**
   - Description: Problem-solving and memory tests
   - Synonyms: Cognitive performance, cognitive ability
   - Search query: `+cognitive +test* +problem +solving` OR `+cognitive +performance +fish*`
   - Source: Domain knowledge

---

## GEN - Genetics, Genomics, & eDNA (ADD: 9 techniques)

### Category: Population Genetics
**Current:** Population Genetics (parent), Microsatellites, Mitochondrial DNA, SNPs, Phylogenetics

**ADD Sub-techniques:**
1. **STRUCTURE**
   - Description: Bayesian clustering for population structure
   - Synonyms: Structure analysis
   - Search query: `+STRUCTURE +population +genetics +software` OR `+bayesian +clustering +population`
   - Source: Domain knowledge - widely used

2. **ADMIXTURE**
   - Description: Maximum likelihood population structure
   - Synonyms: Admixture analysis
   - Search query: `+ADMIXTURE +population +structure` OR `+admixture +analysis +genetics`
   - Source: Domain knowledge

3. **FST Analysis**
   - Description: Population differentiation metrics
   - Synonyms: F-statistics, genetic differentiation
   - Search query: `+FST +population +differentiation` OR `+F +statistic* +genetics`
   - Source: Domain knowledge

4. **Principal Component Analysis** (genetic)
   - Description: PCA for genetic data visualization
   - Synonyms: Genetic PCA, PC analysis
   - Search query: `+PCA +population +genetics` OR `+principal +component* +genetic*`
   - Source: Domain knowledge

5. **DAPC**
   - Description: Discriminant analysis of principal components
   - Synonyms: Discriminant PCA
   - Search query: `+DAPC +population +genetics` OR `+discriminant +analysis +principal +components`
   - Source: Domain knowledge

### Category: Genomics
**Current:** Whole Genome Sequencing (parent), RAD-seq, Transcriptomics, Epigenetics

**ADD Sub-techniques:**
6. **Genome Assembly**
   - Description: De novo genome reconstruction
   - Synonyms: De novo assembly
   - Search query: `+genome +assembly +de +novo` OR `+genome +sequencing +assembly`
   - Source: Domain knowledge

7. **RNA-seq**
   - Description: Transcriptome sequencing and analysis
   - Synonyms: RNA sequencing
   - Search query: `+RNA +seq +transcriptom*` OR `+RNA +sequencing`
   - Source: Domain knowledge

### Category: eDNA
**Current:** Environmental DNA (parent), eDNA Metabarcoding, eDNA Surveys

**ADD Sub-techniques:**
8. **qPCR** (eDNA)
   - Description: Quantitative PCR for species detection
   - Synonyms: Quantitative PCR, real-time PCR
   - Search query: `+qPCR +eDNA +detection` OR `+quantitative +PCR +environmental +DNA`
   - Source: Domain knowledge

9. **ddPCR** (eDNA)
   - Description: Droplet digital PCR for precise quantification
   - Synonyms: Digital PCR
   - Search query: `+ddPCR +eDNA` OR `+droplet +digital +PCR +environmental`
   - Source: Domain knowledge

---

## BIO - Biology, Life History, & Health (ADD: 5 techniques)

### Category: Age & Growth Methods
**Current:** Age & Growth (parent), Vertebral Sectioning, Bomb Radiocarbon Dating, NIRS Ageing

**ADD Sub-techniques:**
1. **Growth Curve Modeling**
   - Description: von Bertalanffy, Gompertz, logistic growth models
   - Synonyms: von Bertalanffy, VBGF, growth modeling
   - Search query: `+von +Bertalanffy +growth` OR `+growth +curve +model*`
   - Source: Domain knowledge

2. **Length-Frequency Analysis**
   - Description: Age/cohort estimation from length distributions
   - Synonyms: Modal progression analysis, ELEFAN
   - Search query: `+length +frequency +analysis +age` OR `+modal +progression +analysis`
   - Source: Domain knowledge

### Category: Physiology
**Current:** Physiology (parent), Metabolic Rate, Stress Physiology, Thermal Biology, Osmoregulation

**ADD Sub-techniques:**
3. **Respirometry**
   - Description: Oxygen consumption measurement
   - Synonyms: Metabolic measurement, oxygen consumption
   - Search query: `+respirometry +metabol*` OR `+oxygen +consumption +measurement`
   - Source: Domain knowledge

### Category: Reproductive Biology
**Current:** Reproduction (parent), Reproductive Histology, Reproductive Endocrinology, Ultrasound, Captive Breeding, Fecundity Estimation

**ADD Sub-techniques:**
4. **Maturity Ogive**
   - Description: Age/length at maturity estimation
   - Synonyms: Maturity curve, L50/A50
   - Search query: `+maturity +ogive` OR `+length +maturity +L50`
   - Source: Domain knowledge

### Category: Disease, Parasites, & Health
**Current:** Health & Disease (parent), Parasitology, Health Indices, Telomere Analysis

**ADD Sub-techniques:**
5. **Blood Chemistry**
   - Description: Hematology and plasma chemistry
   - Synonyms: Hematology, clinical chemistry
   - Search query: `+blood +chemistry +fish*` OR `+hematology +health`
   - Source: Domain knowledge

---

## CON - Conservation Policy & Human Dimensions (ADD: 3 techniques)

### Category: Conservation Assessment
**Current:** IUCN Red List Assessment (parent), Extinction Risk Assessment, Population Viability Analysis, Conservation Prioritization

**ADD Sub-techniques:**
1. **IUCN Criteria Application**
   - Description: Specific Red List criteria (A-E)
   - Synonyms: Red List criteria, IUCN categories
   - Search query: `+IUCN +criteria +red +list` OR `+IUCN +categor* +assessment`
   - Source: Domain knowledge

### Category: Policy & Governance
**Current:** Policy Analysis (parent), MPA Effectiveness, Compliance & Enforcement, Legal Framework Analysis

**ADD Sub-techniques:**
2. **Policy Impact Evaluation**
   - Description: Evaluating conservation policy outcomes
   - Synonyms: Policy effectiveness, impact assessment
   - Search query: `+policy +impact +evaluation +conservation` OR `+policy +effectiveness +assessment`
   - Source: Domain knowledge

### Category: Human Dimensions
**Current:** Socioeconomic Analysis (parent), Stakeholder Analysis, Fisher Knowledge, Market Analysis, Tourism & Recreation

**ADD Sub-techniques:**
3. **Contingent Valuation**
   - Description: Economic valuation of ecosystem services
   - Synonyms: Willingness to pay, WTP
   - Search query: `+contingent +valuation +conservation` OR `+willingness +pay +ecosystem`
   - Source: Domain knowledge

---

## Summary Statistics

**Total techniques to ADD:** 84

By discipline:
- MOV: 15 (largest expansion - SDM and home range methods)
- FISH: 18 (stock assessment and data-poor methods)
- DATA: 20 (ML, Bayesian, statistical methods)
- TRO: 8 (mixing models, community analysis)
- BEH: 6 (observation methods, cognition)
- GEN: 9 (population structure software, eDNA methods)
- BIO: 5 (growth, physiology, reproduction)
- CON: 3 (IUCN, policy, economics)

**New total:** 129 + 84 = **213 techniques**

**Increase:** 65% expansion before panelist review

---

## Data Quality Notes

All additions are:
- ✅ Commonly used in the field (not obscure)
- ✅ Have established literature presence
- ✅ Can be searched on Shark-References
- ✅ Properly categorized hierarchically
- ✅ Include description, synonyms, search queries

**Source documentation:**
- Web search validation: SDM methods, stock assessment, home range
- Domain knowledge: Standard textbook methods
- Software-specific: Named tools widely used (STRUCTURE, SIAR, SS3, etc.)

---

*Expansion list compiled: 2025-10-13*
*Ready for implementation*
