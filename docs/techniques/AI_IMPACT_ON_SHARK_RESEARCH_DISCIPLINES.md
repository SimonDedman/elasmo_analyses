# AI Impact on Shark Research: Discipline-by-Discipline Analysis

## Executive Summary

Artificial Intelligence is rapidly transforming shark research across all eight core disciplines. This report analyzes current AI adoption and projects future impacts for each discipline, based on the EEA 2025 Data Panel analysis of 208 techniques across 4,543 papers.

**Key Finding**: DATA discipline techniques (machine learning, neural networks, deep learning) are penetrating all disciplines, but adoption rates vary significantly by field.

**Date**: 2025-10-26
**Project**: EEA 2025 Data Panel

---

## Table of Contents

1. [Cross-Cutting AI Trends](#cross-cutting-trends)
2. [Behaviour (BEH)](#behaviour-beh)
3. [Biology (BIO)](#biology-bio)
4. [Conservation (CON)](#conservation-con)
5. [Data Science (DATA)](#data-science-data)
6. [Fisheries (FISH)](#fisheries-fish)
7. [Genetics (GEN)](#genetics-gen)
8. [Movement (MOV)](#movement-mov)
9. [Trophic Ecology (TRO)](#trophic-ecology-tro)
10. [Recommendations](#recommendations)

---

## Cross-Cutting AI Trends

### Current State (2025)

**AI Adoption Across Disciplines:**
- **High adoption**: Data Science (native), Genetics, Movement
- **Medium adoption**: Behaviour, Fisheries
- **Low adoption**: Biology, Trophic Ecology, Conservation

**Common AI Applications:**
1. **Image Recognition** - Photo-ID, species classification, behaviour analysis
2. **Pattern Detection** - Acoustic telemetry, movement patterns, habitat use
3. **Predictive Modeling** - Stock assessment, population projections, climate impacts
4. **Natural Language Processing** - Literature mining, database construction, metadata extraction
5. **Automated Data Processing** - Video analysis, acoustic processing, genomic pipelines

### Key Drivers

**Technology:**
- Cloud computing democratizes access to GPU resources
- Pre-trained models (transfer learning) reduce training data needs
- AutoML tools lower technical barriers
- Edge computing enables real-time field deployments

**Data:**
- Growing datasets (biologging, video, genomics)
- Standardization of data formats
- Open science movement
- Citizen science contributions

**Community:**
- Interdisciplinary collaborations
- Code sharing (GitHub, Zenodo)
- Training workshops (Data Carpentry, ML4Conservation)
- Dedicated conferences (e.g., ML for ecology)

### Barriers to Adoption

1. **Technical Skills Gap** - Many biologists lack programming/ML training
2. **Interpretability** - "Black box" models challenge biological understanding
3. **Data Quality** - AI requires large, clean datasets
4. **Computational Resources** - Not all institutions have GPU access
5. **Validation** - Difficult to verify AI outputs in novel scenarios
6. **Funding** - AI development costly, grant systems favor traditional methods

---

## Behaviour (BEH)

### Current Techniques (10 techniques, 290 papers)

**AI-Ready:**
- Video Analysis (108 papers) - **HIGH AI POTENTIAL**
- BORIS (56 papers) - Manual annotation, AI-augmentable
- Social Network Analysis (48 papers) - Graph neural networks

**Traditional:**
- Dominance hierarchy, Operant conditioning, Ethogram development

### Current AI Adoption

**Established (2020-2025):**
1. **Automated Behaviour Recognition**
   - Deep learning for video classification
   - Pose estimation (DeepLabCut, SLEAP)
   - Action recognition networks
   - **Example**: Automated shark feeding behaviour detection

2. **Computer Vision for Ethograms**
   - Object detection (YOLO, Faster R-CNN)
   - Activity classification
   - Interaction detection
   - **Example**: Multi-shark social interaction mapping

3. **Pattern Discovery**
   - Unsupervised learning for novel behaviours
   - Clustering algorithms for behaviour states
   - **Example**: Identifying unknown behavioural repertoires

### Future AI Impacts (2025-2030)

#### High Probability (>75%)

**1. Real-Time Behaviour Classification**
- **Technology**: Edge AI on underwater cameras
- **Impact**: Instant behaviour coding in field studies
- **Timeline**: 2-3 years
- **Barrier**: Power consumption in remote deployments

**2. Predictive Behaviour Models**
- **Technology**: Recurrent neural networks, transformers
- **Impact**: Predict future behaviours from past sequences
- **Timeline**: 3-5 years
- **Barrier**: Requires long-term continuous data

**3. Automated Ethogram Generation**
- **Technology**: Self-supervised learning
- **Impact**: Discover behaviours without human labeling
- **Timeline**: 3-5 years
- **Barrier**: Validation against expert observations

#### Medium Probability (50-75%)

**4. Multi-Modal Behaviour Analysis**
- **Technology**: Fusion models (video + accelerometer + acoustic)
- **Impact**: Comprehensive behaviour understanding
- **Timeline**: 5+ years
- **Barrier**: Synchronized multi-sensor data collection

**5. Social Network Prediction**
- **Technology**: Graph neural networks, temporal networks
- **Impact**: Predict social structure from limited observations
- **Timeline**: 3-5 years
- **Barrier**: Requires individual ID over time

#### Technique Transformations

| Traditional Technique | AI Enhancement | Effort | Impact |
|----------------------|----------------|--------|--------|
| Video Analysis | Automated classification | **HIGH** | 10-100x speedup |
| BORIS | Semi-automated annotation | **MEDIUM** | 5-10x speedup |
| Focal Sampling | Automated focal tracking | **MEDIUM** | Eliminate observer bias |
| Social Network | Automated interaction detection | **HIGH** | Continuous monitoring |
| Ethogram Development | Unsupervised behaviour discovery | **VERY HIGH** | Novel behaviour detection |

### Recommendations for BEH Researchers

**Immediate (2025-2026):**
1. **Adopt pose estimation tools** (DeepLabCut) for video analysis
2. **Pre-label datasets** for future AI training
3. **Standardize video formats** for cross-study comparisons
4. **Learn Python** and basic computer vision

**Medium-term (2026-2028):**
1. **Develop discipline-specific models** for common species/behaviours
2. **Create benchmark datasets** for model validation
3. **Establish best practices** for AI-assisted behaviour coding
4. **Train next generation** in AI+behaviour

**Long-term (2028+):**
1. **Deploy edge AI** for real-time field studies
2. **Integrate multi-modal** sensor networks
3. **Develop interpretable models** that reveal biological insights

---

## Biology (BIO)

### Current Techniques (11 techniques, 2,149 papers)

**AI-Ready:**
- Morphometrics (572 papers) - **HIGH AI POTENTIAL**
- Parasitology (926 papers) - Image classification potential
- Body Measurements (98 papers) - Computer vision

**Traditional:**
- Metabolic Rate, Maturity Ogive, Reproductive observations

### Current AI Adoption

**Established (2020-2025):**
1. **Automated Morphometrics**
   - Image segmentation for landmark detection
   - 3D reconstruction from photos
   - **Example**: FishBase automated measurements

2. **Parasite Detection**
   - Object detection in microscopy images
   - Species classification
   - **Example**: Automated parasite counting

3. **Age Estimation**
   - Vertebral ring reading automation
   - **Example**: Deep learning for otolith aging

### Future AI Impacts (2025-2030)

#### High Probability (>75%)

**1. Automated Specimen Analysis**
- **Technology**: Computer vision, object detection
- **Impact**: Rapid morphometric data collection
- **Timeline**: 2-3 years
- **Barrier**: Standardized imaging protocols needed

**2. Predictive Growth Models**
- **Technology**: Neural ODEs, physics-informed ML
- **Impact**: Better growth predictions with limited data
- **Timeline**: 3-5 years
- **Barrier**: Requires long-term growth datasets

**3. Histology Image Analysis**
- **Technology**: Convolutional neural networks
- **Impact**: Automated tissue classification, maturity staging
- **Timeline**: 2-4 years
- **Barrier**: Expert-labeled training datasets needed

#### Medium Probability (50-75%)

**4. Metabolic Rate Prediction**
- **Technology**: Multi-task learning from multiple traits
- **Impact**: Estimate metabolic rate without experiments
- **Timeline**: 5+ years
- **Barrier**: Mechanistic understanding needed

**5. Health Index Automation**
- **Technology**: Multi-modal learning (images + blood + behavior)
- **Impact**: Rapid health assessment
- **Timeline**: 4-6 years
- **Barrier**: Comprehensive health datasets rare

#### Technique Transformations

| Traditional Technique | AI Enhancement | Effort | Impact |
|----------------------|----------------|--------|--------|
| Morphometrics | Automated measurement | **HIGH** | 100x speedup, eliminate error |
| Parasitology | Automated counting/ID | **MEDIUM** | Consistent quantification |
| Body Measurements | Photo-based estimation | **MEDIUM** | Non-destructive sampling |
| Maturity Ogive | Automated staging | **HIGH** | Remove subjectivity |
| Age Estimation | Automated ring reading | **VERY HIGH** | Eliminate reader bias |

### Recommendations for BIO Researchers

**Immediate (2025-2026):**
1. **Digitize specimens** - High-resolution photos for future analysis
2. **Standardize imaging** - Consistent protocols across studies
3. **Create reference collections** - Expert-labeled training data
4. **Adopt ImageJ/FIJI** with AI plugins

**Medium-term (2026-2028):**
1. **Develop species-specific models** for common measurements
2. **Validate AI outputs** against expert assessments
3. **Integrate AI** into field collection workflows
4. **Share models** via community repositories

**Long-term (2028+):**
1. **Real-time field analysis** using mobile devices
2. **Predictive phenomics** linking genes to traits
3. **Automated health monitoring** in aquaculture/aquaria

---

## Conservation (CON)

### Current Techniques (9 techniques, 1,074 papers)

**AI-Ready:**
- Tourism (775 papers) - Sentiment analysis, predictive modeling
- Vulnerability Assessment (49 papers) - **HIGH AI POTENTIAL**
- MPA Effectiveness (12 papers) - Spatial modeling

**Traditional:**
- IUCN Red List, Stakeholder Engagement, Policy Evaluation

### Current AI Adoption

**Low (2020-2025):**
1. **Species Distribution Models** - GAM/MaxEnt dominate, ML rare
2. **Threat Assessment** - Manual IUCN criteria application
3. **Stakeholder Analysis** - Qualitative methods, minimal AI

**Why Low Adoption?**
- Small sample sizes (rare species)
- Qualitative data (interviews, observations)
- Policy emphasis over prediction
- Funding bias toward traditional conservation

### Future AI Impacts (2025-2030)

#### High Probability (>75%)

**1. Automated Red List Assessments**
- **Technology**: Rule-based AI + expert systems
- **Impact**: Rapid assessment of data-deficient species
- **Timeline**: 2-3 years
- **Barrier**: IUCN criteria formalization

**2. Predictive Threat Modeling**
- **Technology**: Random forests, gradient boosting
- **Impact**: Identify emerging threats before population declines
- **Timeline**: 2-4 years
- **Barrier**: Requires long-term monitoring data

**3. MPA Optimization**
- **Technology**: Spatial optimization algorithms, reinforcement learning
- **Impact**: Design MPAs that maximize conservation outcomes
- **Timeline**: 3-5 years
- **Barrier**: Multiple competing objectives

#### Medium Probability (50-75%)

**4. Sentiment Analysis for Conservation**
- **Technology**: NLP, large language models
- **Impact**: Monitor public attitudes, predict policy success
- **Timeline**: 2-4 years
- **Barrier**: Cultural/linguistic diversity

**5. Human-Wildlife Conflict Prediction**
- **Technology**: Spatiotemporal models, event forecasting
- **Impact**: Prevent conflicts before they occur
- **Timeline**: 4-6 years
- **Barrier**: Incomplete conflict reporting

**6. Policy Impact Prediction**
- **Technology**: Causal inference, counterfactual modeling
- **Impact**: Forecast policy outcomes before implementation
- **Timeline**: 5+ years
- **Barrier**: Few controlled experiments in conservation

#### Technique Transformations

| Traditional Technique | AI Enhancement | Effort | Impact |
|----------------------|----------------|--------|--------|
| IUCN Assessment | Automated criteria application | **MEDIUM** | Assess 1000s of species rapidly |
| Vulnerability Assessment | Predictive threat models | **HIGH** | Proactive conservation |
| MPA Design | Spatial optimization | **HIGH** | Maximize conservation ROI |
| Stakeholder Engagement | Sentiment analysis | **MEDIUM** | Real-time feedback |
| Tourism Impact | Predictive modeling | **MEDIUM** | Sustainable tourism planning |

### Recommendations for CON Researchers

**Immediate (2025-2026):**
1. **Digitize conservation data** - Species observations, threats, policies
2. **Adopt GIS + ML tools** (QGIS, R spatial, GeoPandas)
3. **Collaborate with data scientists** for predictive models
4. **Use LLMs** (ChatGPT, Claude) for literature synthesis

**Medium-term (2026-2028):**
1. **Develop early warning systems** for threats
2. **Create decision support tools** for practitioners
3. **Validate AI predictions** with monitoring programs
4. **Train conservation planners** in AI tools

**Long-term (2028+):**
1. **Real-time conservation dashboards** powered by AI
2. **Automated monitoring** via satellite/drones + AI
3. **AI-assisted policy design** for evidence-based conservation

---

## Data Science (DATA)

### Current Techniques (25 techniques, 2,469 papers)

**Traditional AI:**
- Machine Learning (97 papers)
- Neural Networks (51 papers)
- Random Forest (37 papers)
- Deep Learning (17 papers)
- CNN (3 papers)

**Statistical:**
- GLM, GAM, GAMM, Bayesian Methods, Time Series

### Current AI Adoption

**High (2020-2025):** DATA is the AI discipline, but adoption varies:

**Emerging (2018-2025):**
- Deep Learning (2018+)
- Convolutional Neural Networks (2022+)
- Computer Vision (growing)
- Data Fusion (2022+)

**Established:**
- Random Forest, Neural Networks, SVM, Ensemble Learning

### Future AI Impacts (2025-2030)

#### High Probability (>75%)

**1. Foundation Models for Marine Science**
- **Technology**: Large pre-trained models (CLIP, SAM for underwater imagery)
- **Impact**: Zero-shot species recognition, few-shot learning
- **Timeline**: 1-2 years (already emerging)
- **Barrier**: Curating large marine datasets

**2. Physics-Informed Neural Networks**
- **Technology**: Embedding ecological/physical laws in NNs
- **Impact**: Better predictions with less data, interpretable models
- **Timeline**: 2-4 years
- **Barrier**: Formalizing ecological theory for AI

**3. Automated ML (AutoML)**
- **Technology**: Neural architecture search, hyperparameter optimization
- **Impact**: Non-experts can build custom models
- **Timeline**: 1-3 years (tools exist, adoption lagging)
- **Barrier**: Trust and understanding

#### Medium Probability (50-75%)

**4. Causal Machine Learning**
- **Technology**: Causal forests, double ML, instrumental variables
- **Impact**: Estimate intervention effects from observational data
- **Timeline**: 3-5 years
- **Barrier**: Requires domain expertise + statistics

**5. Multi-Task Learning**
- **Technology**: Shared representations across related tasks
- **Impact**: Better predictions with limited data per task
- **Timeline**: 2-4 years
- **Barrier**: Defining related tasks in ecology

**6. Explainable AI (XAI)**
- **Technology**: SHAP, LIME, attention mechanisms
- **Impact**: Interpretable deep learning models
- **Timeline**: 2-3 years
- **Barrier**: Balancing accuracy vs. interpretability

#### Technique Evolution

**Techniques to Watch:**
1. **Graph Neural Networks** - For spatial/network data
2. **Transformers** - For time series, sequences
3. **Diffusion Models** - For data augmentation, simulation
4. **Federated Learning** - Privacy-preserving multi-institution learning
5. **Active Learning** - Efficient labeling strategies

### Recommendations for DATA Researchers

**Immediate (2025-2026):**
1. **Adopt deep learning frameworks** (PyTorch, JAX)
2. **Use pre-trained models** (transfer learning)
3. **Benchmark new methods** against traditional approaches
4. **Publish reproducible code** with papers

**Medium-term (2026-2028):**
1. **Develop domain-specific benchmarks** for shark research
2. **Create interpretable models** for biological insights
3. **Teach workshops** for other disciplines
4. **Collaborate widely** to apply AI across fields

**Long-term (2028+):**
1. **Build foundation models** for marine ecology
2. **Develop causal frameworks** for conservation interventions
3. **Create AI tools** accessible to non-experts

---

## Fisheries (FISH)

### Current Techniques (31 techniques, 2,286 papers)

**AI-Ready:**
- Stock Assessment (984 papers) - **HIGH AI POTENTIAL**
- CPUE Standardization (21 papers) - ML models
- Bycatch Assessment (23 papers) - Predictive modeling

**Traditional:**
- Yield per Recruit, Virtual Population Analysis, Surplus Production Models

### Current AI Adoption

**Medium (2020-2025):**
1. **ML for Stock Assessment** - Random forests for data-poor scenarios
2. **Image-Based Catch Monitoring** - Species/size classification
3. **Bycatch Prediction** - Spatiotemporal models

**Why Not Higher?**
- Regulatory frameworks require validated models
- Small sample sizes for many stocks
- Conservative management culture

### Future AI Impacts (2025-2030)

#### High Probability (>75%)

**1. Automated Catch Monitoring**
- **Technology**: Computer vision on fishing vessels
- **Impact**: Real-time catch composition, size distribution
- **Timeline**: 2-3 years
- **Barrier**: Implementation on fleets, privacy concerns

**2. Predictive Bycatch Models**
- **Technology**: Ensemble methods, deep learning
- **Impact**: Dynamic closures to minimize bycatch
- **Timeline**: 2-4 years
- **Barrier**: Real-time data streams needed

**3. Data-Poor Stock Assessment**
- **Technology**: Transfer learning from data-rich stocks
- **Impact**: Better management for poorly studied species
- **Timeline**: 3-5 years
- **Barrier**: Cross-species assumptions

#### Medium Probability (50-75%)

**4. Catch Forecasting**
- **Technology**: Recurrent neural networks, transformers
- **Impact**: Predict future catch rates, optimize effort
- **Timeline**: 3-5 years
- **Barrier**: Non-stationary environments (climate change)

**5. Fleet Behavior Modeling**
- **Technology**: Agent-based models + reinforcement learning
- **Impact**: Predict fishing effort under policy scenarios
- **Timeline**: 4-6 years
- **Barrier**: Proprietary vessel data access

**6. Ecosystem-Based Fisheries Management**
- **Technology**: Graph neural networks for food webs
- **Impact**: Multi-species management
- **Timeline**: 5+ years
- **Barrier**: Data requirements, complexity

#### Technique Transformations

| Traditional Technique | AI Enhancement | Effort | Impact |
|----------------------|----------------|--------|--------|
| Stock Assessment | ML-augmented age-structured models | **HIGH** | Handle data gaps |
| CPUE Standardization | Neural networks | **MEDIUM** | Capture non-linearities |
| Bycatch Assessment | Predictive spatiotemporal models | **MEDIUM** | Real-time risk maps |
| Yield per Recruit | RL-optimized harvest strategies | **HIGH** | Adaptive management |
| Fisher Interviews | NLP for qualitative data | **MEDIUM** | Systematic analysis |

### Recommendations for FISH Researchers

**Immediate (2025-2026):**
1. **Adopt ML for CPUE standardization** (random forests, boosted trees)
2. **Digitize catch logs** for future AI applications
3. **Implement electronic monitoring** on vessels
4. **Collaborate with computer vision experts**

**Medium-term (2026-2028):**
1. **Develop AI-augmented stock assessment** frameworks
2. **Validate ML models** against traditional methods
3. **Create bycatch prediction tools** for fishers
4. **Train fishery managers** in AI interpretation

**Long-term (2028+):**
1. **Real-time adaptive management** powered by AI
2. **Ecosystem models** incorporating ML components
3. **Automated compliance monitoring** via AI

---

## Genetics (GEN)

### Current Techniques (23 techniques, 11,163 papers)

**AI-Ready:**
- Genomics (511 papers) - **VERY HIGH AI POTENTIAL**
- DNA Barcoding (448 papers) - Deep learning classification
- eDNA (110 papers) - Sequence classification
- Metabarcoding (86 papers) - ML pipelines

**Traditional:**
- STRUCTURE, Phylogenetics, Population Genetics

### Current AI Adoption

**High (2020-2025):**
1. **Deep Learning for Variant Calling** - CNNs outperform traditional methods
2. **Species Classification** - ML from DNA sequences
3. **Genomic Prediction** - Predict traits from genotypes
4. **eDNA Analysis** - Automated taxonomic assignment

**Why High Adoption?**
- Massive datasets (NGS produces GBs-TBs)
- Discrete data (sequences, SNPs)
- Active bioinformatics community
- Public datasets (NCBI, BOLD)

### Future AI Impacts (2025-2030)

#### High Probability (>75%)

**1. Foundation Models for Genomics**
- **Technology**: DNA language models (like GPT for genomes)
- **Impact**: Zero-shot gene function prediction, variant effects
- **Timeline**: 1-2 years (already emerging: DNABERT, Nucleotide Transformer)
- **Barrier**: Computational cost

**2. Automated eDNA Pipelines**
- **Technology**: End-to-end ML (sequence → species → abundance)
- **Impact**: Rapid biodiversity assessments
- **Timeline**: 2-3 years
- **Barrier**: Reference database completeness

**3. Pangenomics Analysis**
- **Technology**: Graph neural networks for pangenomes
- **Impact**: Understand population-level genomic diversity
- **Timeline**: 2-4 years
- **Barrier**: Computational complexity

#### Medium Probability (50-75%)

**4. Phenotype Prediction**
- **Technology**: Deep learning from genotype to phenotype
- **Impact**: Predict traits without sequencing full genome
- **Timeline**: 3-5 years
- **Barrier**: Genotype-phenotype maps complex

**5. Ancient DNA Reconstruction**
- **Technology**: Generative models for damaged DNA
- **Impact**: Better reconstruction of degraded samples
- **Timeline**: 3-5 years
- **Barrier**: Validation against known genomes

**6. Phylogenomic Inference**
- **Technology**: Neural networks for tree building
- **Impact**: Faster, more accurate phylogenies
- **Timeline**: 2-4 years
- **Barrier**: Interpretability of phylogenetic relationships

#### Technique Transformations

| Traditional Technique | AI Enhancement | Effort | Impact |
|----------------------|----------------|--------|--------|
| DNA Barcoding | Deep learning classification | **MEDIUM** | Higher accuracy, novel species |
| eDNA | Automated taxonomic assignment | **MEDIUM** | Real-time biodiversity |
| Genomics | Variant calling, annotation | **HIGH** | Faster, more accurate |
| Population Genetics | ML-based STRUCTURE | **MEDIUM** | Handle large datasets |
| Metabarcoding | End-to-end ML pipelines | **HIGH** | Eliminate manual steps |

### Recommendations for GEN Researchers

**Immediate (2025-2026):**
1. **Adopt ML for variant calling** (DeepVariant, etc.)
2. **Use pre-trained DNA models** for classification
3. **Automate eDNA pipelines** with ML tools
4. **Contribute to reference databases** for AI training

**Medium-term (2026-2028):**
1. **Develop species-specific genomic models**
2. **Integrate multi-omics** (genomics + transcriptomics + proteomics)
3. **Create interpretable models** linking genes to traits
4. **Validate AI predictions** with wet-lab experiments

**Long-term (2028+):**
1. **Real-time eDNA analysis** in the field
2. **Predictive conservation genomics** for climate adaptation
3. **AI-designed primers** for novel species detection

---

## Movement (MOV)

### Current Techniques (22 techniques, 1,786 papers)

**AI-Ready:**
- Network Analysis (160 papers) - Graph neural networks
- State-Space Models (41 papers) - Deep learning SSMs
- Hidden Markov Models (35 papers) - Neural HMMs
- Species Distribution Model (26 papers) - **HIGH AI POTENTIAL**

**Traditional:**
- Kernel Density, Minimum Convex Polygon, MaxEnt

### Current AI Adoption

**Medium-High (2020-2025):**
1. **Deep Learning SSMs** - RNNs, LSTMs for movement trajectories
2. **Species Distribution Models** - Neural networks augmenting MaxEnt
3. **Automated Acoustic Detection** - CNNs for receiver data
4. **Habitat Prediction** - Random forests, boosted trees

### Future AI Impacts (2025-2030)

#### High Probability (>75%)

**1. Predictive Movement Models**
- **Technology**: Transformers, graph neural networks
- **Impact**: Predict future locations from partial tracks
- **Timeline**: 2-3 years
- **Barrier**: Long-term continuous tracking data

**2. Multi-Individual Tracking**
- **Technology**: Graph neural networks, attention mechanisms
- **Impact**: Jointly model interacting individuals
- **Timeline**: 2-4 years
- **Barrier**: Simultaneous tracking difficult

**3. Real-Time Spatial Predictions**
- **Technology**: Streaming ML, edge computing
- **Impact**: Dynamic MPAs, real-time conservation alerts
- **Timeline**: 3-5 years
- **Barrier**: Data transmission in remote areas

#### Medium Probability (50-75%)

**4. Causal Movement Analysis**
- **Technology**: Causal inference in spatiotemporal data
- **Impact**: Identify drivers of movement (not just correlations)
- **Timeline**: 4-6 years
- **Barrier**: Requires experimental perturbations

**5. Generative Movement Models**
- **Technology**: Diffusion models, GANs for trajectories
- **Impact**: Simulate realistic movement for scenario testing
- **Timeline**: 3-5 years
- **Barrier**: Validation against real movements

**6. Automated Acoustic Array Design**
- **Technology**: Reinforcement learning
- **Impact**: Optimize receiver placement for coverage
- **Timeline**: 3-5 years
- **Barrier**: Deployment costs

#### Technique Transformations

| Traditional Technique | AI Enhancement | Effort | Impact |
|----------------------|----------------|--------|--------|
| State-Space Models | Deep learning SSMs | **HIGH** | Handle irregular sampling, non-linearity |
| Hidden Markov Models | Neural HMMs | **MEDIUM** | More complex behaviors |
| Species Distribution Model | Neural networks, ensemble | **HIGH** | Better predictions, interactions |
| Network Analysis | Graph neural networks | **HIGH** | Dynamic networks |
| Home Range | Automated boundary detection | **MEDIUM** | Objective delineation |

### Recommendations for MOV Researchers

**Immediate (2025-2026):**
1. **Adopt ML for habitat models** (random forests, XGBoost)
2. **Use deep learning SSMs** for irregular tracks
3. **Automate acoustic detection** with CNNs
4. **Learn graph analysis** (networkX, PyG)

**Medium-term (2026-2028):**
1. **Develop predictive movement models** for conservation
2. **Create real-time alert systems** for critical habitats
3. **Validate AI predictions** with independent data
4. **Integrate movement + environment** in unified models

**Long-term (2028+):**
1. **AI-powered dynamic MPAs** adjusting in real-time
2. **Generative models** for scenario testing
3. **Causal models** linking environment to behavior

---

## Trophic Ecology (TRO)

### Current Techniques (17 techniques, 1,550 papers)

**AI-Ready:**
- NMDS (134 papers) - Neural embedding alternatives
- DNA Metabarcoding (44 papers) - **HIGH AI POTENTIAL**
- Food Web Models (80 papers) - Graph neural networks

**Traditional:**
- Stable Isotope Analysis (448 papers)
- Stomach Content Analysis (302 papers)
- Fatty Acid Analysis (56 papers)

### Current AI Adoption

**Low-Medium (2020-2025):**
1. **ML for DNA Metabarcoding** - Taxonomic classification
2. **Food Web Modeling** - Network analysis with ML
3. **Isotope Mixing Models** - Bayesian + ML hybrids

**Why Lower Than Expected?**
- Small sample sizes (expensive isotope analysis)
- Mechanistic models preferred (diet mixing, fractionation)
- Conservative field culture

### Future AI Impacts (2025-2030)

#### High Probability (>75%)

**1. Automated Prey Identification**
- **Technology**: Computer vision for stomach contents
- **Impact**: Rapid diet analysis without expert taxonomists
- **Timeline**: 2-3 years
- **Barrier**: Training datasets with expert IDs

**2. DNA Metabarcoding Pipelines**
- **Technology**: End-to-end ML (sequence → species → diet)
- **Impact**: Comprehensive diet analysis from feces/stomach
- **Timeline**: 2-3 years
- **Barrier**: Reference database gaps

**3. Isotope Prediction**
- **Technology**: ML to predict isotope values from traits/environment
- **Impact**: Supplement expensive isotope sampling
- **Timeline**: 3-5 years
- **Barrier**: Requires large isotope databases

#### Medium Probability (50-75%)

**4. Food Web Reconstruction**
- **Technology**: Graph neural networks, ecological networks
- **Impact**: Infer trophic links from partial data
- **Timeline**: 4-6 years
- **Barrier**: Validation difficult

**5. Trophic Position Estimation**
- **Technology**: Multi-task learning from multiple indicators
- **Impact**: Better estimates with limited data
- **Timeline**: 3-5 years
- **Barrier**: Ground truth difficult to establish

**6. Foraging Behavior Prediction**
- **Technology**: Combining movement + environment + prey
- **Impact**: Predict where sharks feed
- **Timeline**: 4-6 years
- **Barrier**: Linking behavior to actual feeding

#### Technique Transformations

| Traditional Technique | AI Enhancement | Effort | Impact |
|----------------------|----------------|--------|--------|
| Stomach Content Analysis | Computer vision for prey ID | **HIGH** | 10-100x speedup |
| DNA Metabarcoding | Automated taxonomic assignment | **MEDIUM** | Eliminate manual BLAST |
| Stable Isotope Analysis | Predictive models | **MEDIUM** | Reduce sampling costs |
| NMDS | Neural embeddings | **LOW** | Better visualization |
| Food Web Models | Graph neural networks | **HIGH** | Dynamic food webs |

### Recommendations for TRO Researchers

**Immediate (2025-2026):**
1. **Digitize stomach contents** - High-res photos for future AI
2. **Adopt ML for metabarcoding** pipelines
3. **Use ensemble models** for isotope mixing
4. **Compile isotope databases** for AI training

**Medium-term (2026-2028):**
1. **Develop computer vision** for prey identification
2. **Create predictive models** for isotope values
3. **Integrate multiple diet indicators** (isotopes + FA + DNA)
4. **Validate AI outputs** against expert analysis

**Long-term (2028+):**
1. **Real-time diet analysis** from photos in the field
2. **Predictive trophic models** linking diet to ecosystem change
3. **AI-reconstructed food webs** from minimal data

---

## Recommendations

### For Researchers

#### Universal Skills for AI Era

**Technical:**
1. **Programming** - Python (essential), R (helpful)
2. **Machine Learning Basics** - scikit-learn, PyTorch
3. **Data Management** - SQL, pandas, data versioning
4. **Version Control** - Git, GitHub
5. **Cloud Computing** - Google Colab, AWS, HPC basics

**Conceptual:**
1. **When to use AI** vs. traditional methods
2. **Model Validation** - Overfitting, generalization, cross-validation
3. **Interpretability** - Understanding predictions, SHAP values
4. **Ethics** - Bias, fairness, privacy, reproducibility
5. **Communication** - Explaining AI to non-experts

#### Training Resources

**Free Online Courses:**
- Fast.ai - Practical Deep Learning
- Coursera - Machine Learning (Andrew Ng)
- Kaggle Learn - Hands-on tutorials
- Data Carpentry - Data science for biology

**Workshops & Bootcamps:**
- ML4Conservation Summer School
- BIOS2 Training Program
- SORTEE Hackathons
- Discipline-specific workshops at conferences

**Books:**
- "Deep Learning for the Life Sciences" (Ramsundar et al.)
- "Hands-On Machine Learning" (Géron)
- "Applied Predictive Modeling" (Kuhn & Johnson)

### For Funders

**Priority Areas:**
1. **Training Programs** - Workshops, bootcamps, fellowships
2. **Benchmark Datasets** - Curated, expert-labeled data
3. **Computational Resources** - Cloud credits, GPU access
4. **Interdisciplinary Teams** - Ecologists + data scientists
5. **Software Infrastructure** - Maintain critical tools (QIIME, DADA2, etc.)
6. **Validation Studies** - Compare AI to traditional methods
7. **Open Science** - Code/data sharing requirements

**Funding Mechanisms:**
- Seed grants for AI pilot studies
- Postdoc fellowships for AI+ecology
- Infrastructure grants for computational resources
- Collaborative grants (ecologist + CS researcher)

### For Institutions

**Infrastructure:**
1. **HPC Access** - University clusters, cloud partnerships
2. **Data Storage** - Institutional repositories, data management plans
3. **Software Licenses** - MATLAB, ArcGIS, specialized tools
4. **Training** - Workshops, short courses, online resources

**Support:**
1. **Consulting Services** - Statisticians, data scientists
2. **Code Review** - Peer review for methods/code
3. **Reproducibility** - Tools for computational reproducibility
4. **Collaboration** - Cross-department AI+biology partnerships

### For Journals & Publishers

**Requirements:**
1. **Code Availability** - Mandate code sharing
2. **Data Availability** - Public datasets where possible
3. **Reproducibility** - Computational environment specs
4. **Validation** - Independent test sets required
5. **Transparency** - Model architectures, hyperparameters documented

**New Article Types:**
1. **Negative Results** - When AI doesn't work
2. **Benchmarks** - Standardized datasets for comparisons
3. **Software Papers** - Credit for tool development
4. **Replication Studies** - Verify published AI methods

---

## Conclusion

### Key Takeaways

**1. AI is transforming ALL shark research disciplines**
- Even "low-tech" fields (Biology, Trophic Ecology) will see major impacts
- Adoption varies, but trajectory is clear

**2. Greatest impact where data is abundant**
- Genetics, Movement already AI-intensive
- Behaviour, Fisheries accelerating adoption
- Conservation, Biology, Trophic Ecology lagging but catching up

**3. Technical barriers are falling**
- Pre-trained models democratize AI
- AutoML lowers expertise requirements
- Cloud computing removes hardware barriers

**4. Interpretability remains critical**
- "Black box" models not enough for science
- Need AI that reveals biological insights
- XAI (Explainable AI) will be essential

**5. Interdisciplinary collaboration is key**
- Ecologists + data scientists partnerships
- Training programs bridging fields
- Shared tools and datasets

### Timeline Summary

**2025-2026 (Immediate):**
- Adopt existing AI tools (computer vision, ML classification)
- Digitize data for future AI applications
- Learn Python and basic ML

**2026-2028 (Near-term):**
- Develop discipline-specific AI models
- Validate AI against traditional methods
- Integrate AI into standard workflows

**2028+ (Long-term):**
- Real-time AI-powered conservation
- Predictive ecology becomes mainstream
- Foundation models for marine science

### The Bottom Line

**AI will not replace shark researchers** - it will amplify their capabilities. Those who embrace AI early will:
- Analyze 10-100x more data
- Discover patterns humans miss
- Make faster, data-driven conservation decisions
- Collaborate globally via shared models/datasets

**The question is not WHETHER to adopt AI, but HOW and WHEN.**

This report provides a roadmap. The future of shark research is AI-augmented, interdisciplinary, and data-driven. The transition is happening now.

---

**Author**: EEA 2025 Data Panel Analysis
**Date**: 2025-10-26
**Version**: 1.0
**Contact**: [Project contact info]

**Cite as**: EEA 2025 Data Panel (2025). AI Impact on Shark Research: Discipline-by-Discipline Analysis. Technical Report.

---

## Appendix: AI Tools by Discipline

### BEH
- DeepLabCut, SLEAP (pose estimation)
- YOLO, Faster R-CNN (object detection)
- BORIS + AI plugins (behavior annotation)
- igraph, networkX (social networks)

### BIO
- ImageJ + AI plugins (morphometrics)
- Ilastik (image segmentation)
- QuPath (histology analysis)
- FishBase API (species data)

### CON
- MaxEnt, SDM (species distribution)
- Marxan + ML (MPA optimization)
- spaCy, NLTK (sentiment analysis)
- QGIS + ML plugins (spatial analysis)

### DATA
- scikit-learn (general ML)
- PyTorch, TensorFlow (deep learning)
- XGBoost, LightGBM (boosted trees)
- SHAP, LIME (explainability)

### FISH
- TropFishR + ML (stock assessment)
- Keras/TensorFlow (catch monitoring)
- Python + geopandas (spatial models)
- Stan, JAGS (Bayesian models)

### GEN
- DeepVariant (variant calling)
- DNABERT (DNA language model)
- QIIME2 + ML (metabarcoding)
- AlphaFold (protein structure)

### MOV
- moveVis + ML (trajectory analysis)
- PyTorch Geometric (graph NNs)
- TensorFlow Probability (probabilistic SSMs)
- GRASS GIS + R (spatial analysis)

### TRO
- MixSIAR + ML (isotope mixing)
- QIIME2, DADA2 (DNA metabarcoding)
- igraph, networX (food webs)
- Custom CV tools (stomach contents)
