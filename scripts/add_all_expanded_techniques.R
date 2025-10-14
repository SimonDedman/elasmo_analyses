#!/usr/bin/env Rscript
# Add All 84 Expanded Techniques to Master Techniques CSV
# Date: 2025-10-13
# Purpose: Add all techniques from Technique_Expansion_List.md to master_techniques.csv
# Input: data/master_techniques.csv (129 techniques)
# Output: data/master_techniques.csv (213 techniques)
# Backup: data/master_techniques_BEFORE_EXPANSION.csv

library(tidyverse)

# Set working directory to project root
setwd("/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel")

# 1. LOAD CURRENT DATA --------------------------------------------------------
cat("Loading current master_techniques.csv...\n")
master_techniques <- read_csv("data/master_techniques.csv", show_col_types = FALSE)
cat(sprintf("Current techniques: %d\n\n", nrow(master_techniques)))

# 2. CREATE BACKUP ------------------------------------------------------------
backup_file <- "data/master_techniques_BEFORE_EXPANSION.csv"
cat(sprintf("Creating backup: %s\n", backup_file))
write_csv(master_techniques, backup_file)
cat("Backup created successfully.\n\n")

# 3. DEFINE ALL 84 NEW TECHNIQUES ---------------------------------------------
cat("Creating 84 new technique entries...\n\n")

new_techniques <- tribble(
  ~discipline_code, ~category_name, ~technique_name, ~is_parent, ~parent_technique, ~description, ~synonyms, ~data_source, ~search_query, ~search_query_alt, ~eea_count, ~notes,

  # === MOV - Movement (15 techniques) ===

  # SDM Sub-techniques
  "MOV", "Habitat Modeling", "Random Forest SDM", FALSE, "Species Distribution Model", "Machine learning ensemble method for SDM", "RF", "method_expansion", "+species +distribution +random +forest", NA, 0, NA,
  "MOV", "Habitat Modeling", "Boosted Regression Trees SDM", FALSE, "Species Distribution Model", "Gradient boosting for SDM", "BRT, GBM, Gradient Boosted Models", "method_expansion", "+BRT +species +distribution", "+boosted +regression +tree*", 0, NA,
  "MOV", "Habitat Modeling", "GAM SDM", FALSE, "Species Distribution Model", "GAMs for non-linear species-environment relationships", "GAM, GAMM", "method_expansion", "+GAM +species +distribution", "+additive +model* +habitat", 0, NA,
  "MOV", "Habitat Modeling", "GLM SDM", FALSE, "Species Distribution Model", "GLMs for species distribution", "GLM, logistic regression", "method_expansion", "+GLM +species +distribution", "+generalized +linear +model* +habitat", 0, NA,
  "MOV", "Habitat Modeling", "Neural Network SDM", FALSE, "Species Distribution Model", "Deep learning for species distribution", "CNN for SDM, deep SDM", "method_expansion", "+neural +network +species +distribution", "+deep +learning +SDM", 0, NA,

  # Home Range Sub-techniques
  "MOV", "Movement Analysis", "Kernel Density Estimation", FALSE, "Home Range Analysis", "Probabilistic home range estimation", "KDE, utilization distribution, UD", "method_expansion", "+kernel +density +home +range", "+KDE +utilization +distribution", 0, NA,
  "MOV", "Movement Analysis", "Minimum Convex Polygon", FALSE, "Home Range Analysis", "Smallest polygon enclosing all relocations", "MCP, convex hull", "method_expansion", "+MCP +home +range", "+minimum +convex +polygon", 0, NA,
  "MOV", "Movement Analysis", "Brownian Bridge Movement Model", FALSE, "Home Range Analysis", "Path-based home range estimation accounting for movement between fixes", "BBMM, dynamic Brownian bridge", "method_expansion", "+brownian +bridge +home +range", "+BBMM +movement", 0, NA,
  "MOV", "Movement Analysis", "AKDE", FALSE, "Home Range Analysis", "KDE accounting for temporal autocorrelation", "Autocorrelated Kernel Density Estimator", "method_expansion", "+AKDE +home +range", "+autocorrelat* +kernel +density", 0, NA,

  # Movement Modeling Sub-techniques
  "MOV", "Movement Analysis", "Hidden Markov Models", FALSE, "Movement Modeling", "State-space models for behavioral state estimation", "HMM, behavioral state models", "method_expansion", "+hidden +markov +movement", "+HMM +behav* +state", 0, NA,
  "MOV", "Movement Analysis", "State-Space Models", FALSE, "Movement Modeling", "Filtering location error and estimating movement parameters", "SSM, Kalman filter", "method_expansion", "+state +space +model* +movement", "+SSM +telemetry", 0, NA,
  "MOV", "Movement Analysis", "Step Selection Functions", FALSE, "Movement Modeling", "Resource selection at movement step scale", "SSF, integrated step selection", "method_expansion", "+step +selection +function*", "+SSF +movement", 0, NA,
  "MOV", "Movement Analysis", "Resource Selection Functions", FALSE, "Movement Modeling", "Habitat selection analysis", "RSF, resource utilization functions", "method_expansion", "+resource +selection +function*", "+RSF +habitat +selection", 0, NA,

  # Spatial Conservation
  "MOV", "Spatial Conservation", "Network Analysis Spatial", FALSE, "Spatial Prioritization", "Graph theory for connectivity and MPA networks", "Graph theory, circuit theory", "method_expansion", "+network +analysis +connectivity +spatial", "+graph +theory +conservation", 0, NA,
  "MOV", "Spatial Conservation", "Marxan", FALSE, "Spatial Prioritization", "Spatial prioritization software", "Zonation, systematic conservation planning", "method_expansion", "+marxan +conservation +planning", "+zonation +prioritization", 0, NA,

  # === FISH - Fisheries (18 techniques) ===

  # Stock Assessment Sub-techniques
  "FISH", "Stock Assessment", "Statistical Catch-at-Age", FALSE, "Stock Assessment", "Age-structured assessment using catch composition", "SCA, catch-at-age analysis", "method_expansion", "+statistical +catch +age", "+SCA +stock +assessment", 0, NA,
  "FISH", "Stock Assessment", "Stock Synthesis", FALSE, "Stock Assessment", "Integrated age-structured assessment framework (NOAA)", "SS3, Stock Synthesis 3", "method_expansion", "+stock +synthesis +SS3", "+stock +synthesis +assessment", 0, NA,
  "FISH", "Stock Assessment", "Virtual Population Analysis", FALSE, "Stock Assessment", "Cohort analysis for estimating fishing mortality", "VPA, cohort analysis", "method_expansion", "+VPA +virtual +population", "+cohort +analysis +fisheries", 0, NA,
  "FISH", "Stock Assessment", "Spawning Stock Biomass per Recruit", FALSE, "Stock Assessment", "Per-recruit analysis for reference points", "SSB/R, spawning potential ratio, SPR", "method_expansion", "+spawning +biomass +recruit", "+SPR +fisheries", 0, NA,
  "FISH", "Stock Assessment", "Yield per Recruit", FALSE, "Stock Assessment", "Per-recruit models for yield optimization", "Y/R, yield-per-recruit analysis", "method_expansion", "+yield +per +recruit", "+YPR +fisheries", 0, NA,
  "FISH", "Stock Assessment", "Delay-Difference Models", FALSE, "Stock Assessment", "Population models incorporating somatic growth", "Deriso-Schnute model", "method_expansion", "+delay +difference +model* +stock", "+Deriso +Schnute", 0, NA,
  "FISH", "Stock Assessment", "Catch Curve Analysis", FALSE, "Stock Assessment", "Mortality estimation from age/length composition", "Catch curve, age-based mortality", "method_expansion", "+catch +curve +mortality", "+catch +curve +analysis", 0, NA,

  # Data-Poor Methods
  "FISH", "Data-Poor Methods", "LIME", FALSE, "Data-Poor Assessment", "Length-based assessment with recruitment variability", "Length-based integrated assessment", "method_expansion", "+LIME +length +based +assessment", "+length +integrated +mixed +effects", 0, NA,
  "FISH", "Data-Poor Methods", "LBSPR", FALSE, "Data-Poor Assessment", "SPR estimation from length composition", "Length-based SPR", "method_expansion", "+LBSPR +spawning +potential", "+length +based +SPR", 0, NA,
  "FISH", "Data-Poor Methods", "Catch-MSY", FALSE, "Data-Poor Assessment", "Data-limited method using catch and priors", "CMSY", "method_expansion", "+catch +MSY +data +poor", "+CMSY +stock +assessment", 0, NA,
  "FISH", "Data-Poor Methods", "Depletion Methods", FALSE, "Data-Poor Assessment", "Abundance estimation from catch and effort decline", "Leslie-DeLury, depletion estimators", "method_expansion", "+depletion +method* +abundance", "+Leslie +DeLury", 0, NA,
  "FISH", "Data-Poor Methods", "Life History Invariant Methods", FALSE, "Data-Poor Assessment", "Natural mortality estimators (Hoenig, Pauly, etc.)", "M estimators, empirical mortality", "method_expansion", "+natural +mortality +Hoenig", "+natural +mortality +Pauly", 0, NA,

  # CPUE & Abundance
  "FISH", "Fishery-Dependent Data", "GLM CPUE Standardization", FALSE, "CPUE Standardization", "Generalized linear models for CPUE", "GLM standardization", "method_expansion", "+GLM +CPUE +standardization", NA, 0, NA,
  "FISH", "Fishery-Dependent Data", "GAM CPUE Standardization", FALSE, "CPUE Standardization", "Generalized additive models for CPUE", "GAM standardization, non-linear CPUE", "method_expansion", "+GAM +CPUE +standardization", NA, 0, NA,
  "FISH", "Fishery-Dependent Data", "Random Forest CPUE", FALSE, "CPUE Standardization", "Machine learning for CPUE standardization", "RF CPUE", "method_expansion", "+random +forest +CPUE", "+machine +learning +CPUE +standardization", 0, NA,
  "FISH", "Fishery-Dependent Data", "Distance Sampling", FALSE, "Catch Data Analysis", "Abundance estimation accounting for detection probability", "Line transect, strip transect", "method_expansion", "+distance +sampling +abundance", "+line +transect +fish*", 0, NA,

  # Bycatch
  "FISH", "Bycatch & Mortality", "Post-Release Mortality", FALSE, "Bycatch Assessment", "Survival estimation after release", "Release mortality, discard survival", "method_expansion", "+post +release +mortality", "+discard +survival", 0, NA,
  "FISH", "Bycatch & Mortality", "Observer Coverage Analysis", FALSE, "Bycatch Assessment", "Extrapolating bycatch from observer data", "Observer program analysis", "method_expansion", "+observer +coverage +bycatch", "+observer +data +extrapolation", 0, NA,

  # === DATA - Data Science (20 techniques) ===

  # Machine Learning
  "DATA", "Machine Learning & AI", "Boosted Regression Trees", FALSE, "Machine Learning", "Gradient boosting machine learning", "BRT, GBM, XGBoost, gradient boosting", "method_expansion", "+boosted +regression +tree*", "+GBM +XGBoost", 0, NA,
  "DATA", "Machine Learning & AI", "Support Vector Machines", FALSE, "Machine Learning", "Classification and regression ML method", "SVM, support vector regression", "method_expansion", "+support +vector +machine*", "+SVM +classification", 0, NA,
  "DATA", "Machine Learning & AI", "Convolutional Neural Networks", FALSE, "Machine Learning", "Deep learning for image/spatial data", "CNN, ConvNet", "method_expansion", "+convolutional +neural +network*", "+CNN +deep +learning", 0, NA,
  "DATA", "Machine Learning & AI", "Ensemble Learning", FALSE, "Machine Learning", "Combining multiple models", "Model averaging, stacking", "method_expansion", "+ensemble +learning +model*", "+model +averaging", 0, NA,
  "DATA", "Machine Learning & AI", "Computer Vision", FALSE, "Machine Learning", "Image/video analysis with ML", "Image recognition, object detection", "method_expansion", "+computer +vision", "+image +recognition +fish*", 0, NA,

  # Statistical Models
  "DATA", "Statistical Models", "GAMM", FALSE, "GLM/GAM", "GAMs with random effects", "Generalized additive mixed models", "method_expansion", "+GAMM +generalized +additive +mixed", "+GAMM +model*", 0, NA,
  "DATA", "Statistical Models", "Generalized Estimating Equations", FALSE, "GLM/GAM", "Marginal models for correlated data", "GEE", "method_expansion", "+generalized +estimating +equation*", "+GEE +correlated +data", 0, NA,
  "DATA", "Statistical Models", "Hierarchical Models", FALSE, "Hierarchical Models", "Multi-level statistical models", "Multilevel models, nested models", "method_expansion", "+hierarchical +model* +statistical", "+multilevel +model*", 0, NA,
  "DATA", "Statistical Models", "ARIMA Models", FALSE, "Time Series", "Autoregressive integrated moving average", "Time series forecasting, Box-Jenkins", "method_expansion", "+ARIMA +time +series", "+autoregressive +model*", 0, NA,
  "DATA", "Statistical Models", "Structural Equation Modeling", FALSE, "Hierarchical Models", "Multivariate causal modeling", "SEM, path analysis", "method_expansion", "+structural +equation +model*", "+SEM +causal +analysis", 0, NA,

  # Bayesian Methods
  "DATA", "Bayesian Approaches", "INLA", FALSE, "Bayesian Methods", "Integrated Nested Laplace Approximation for spatial models", "R-INLA", "method_expansion", "+INLA +bayesian +spatial", "+integrated +nested +laplace", 0, NA,
  "DATA", "Bayesian Approaches", "Stan", FALSE, "Bayesian Methods", "Probabilistic programming language for Bayesian inference", "RStan, PyStan", "method_expansion", "+Stan +bayesian +inference", "+RStan +model*", 0, NA,
  "DATA", "Bayesian Approaches", "JAGS", FALSE, "Bayesian Methods", "Just Another Gibbs Sampler for Bayesian models", "rjags", "method_expansion", "+JAGS +bayesian +model*", "+gibbs +sampl*", 0, NA,
  "DATA", "Bayesian Approaches", "Approximate Bayesian Computation", FALSE, "Bayesian Methods", "Likelihood-free Bayesian inference", "ABC, simulation-based inference", "method_expansion", "+approximate +bayesian +computation", "+ABC +likelihood +free", 0, NA,
  "DATA", "Bayesian Approaches", "Bayesian Network Analysis", FALSE, "Bayesian Methods", "Probabilistic graphical models", "Belief networks, Bayes nets", "method_expansion", "+bayesian +network +analysis", "+belief +network*", 0, NA,

  # Data Integration
  "DATA", "Data Integration", "Occupancy Modeling", FALSE, "Data Integration", "Estimating occurrence accounting for detection", "Occupancy models, presence-absence", "method_expansion", "+occupancy +model* +detection", "+presence +absence +detection +probability", 0, NA,
  "DATA", "Data Integration", "N-Mixture Models", FALSE, "Data Integration", "Abundance from repeated counts", "Binomial mixture models", "method_expansion", "+N +mixture +model*", "+binomial +mixture +abundance", 0, NA,
  "DATA", "Data Integration", "Multi-Species Models", FALSE, "Data Integration", "Joint modeling of multiple species", "Community models, joint SDM", "method_expansion", "+multi +species +model*", "+joint +species +distribution", 0, NA,
  "DATA", "Data Integration", "Data Fusion", FALSE, "Data Integration", "Combining disparate data sources", "Data integration, multi-source analysis", "method_expansion", "+data +fusion +integration", "+multi +source +data", 0, NA,
  "DATA", "Data Integration", "Cross-Validation", FALSE, "Data Integration", "Model validation and selection", "k-fold CV, LOOCV", "method_expansion", "+cross +validation +model +selection", "+k +fold +validation", 0, NA,

  # === TRO - Trophic Ecology (8 techniques) ===

  # Diet Analysis
  "TRO", "Diet Analysis Methods", "SIAR", FALSE, "Stable Isotope Analysis", "Bayesian mixing models for isotope data", "MixSIAR, stable isotope mixing models", "method_expansion", "+SIAR +isotope +mixing", "+MixSIAR +diet", 0, NA,
  "TRO", "Diet Analysis Methods", "IsoSpace", FALSE, "Stable Isotope Analysis", "Bayesian niche space estimation from isotopes", "Isotopic niche", "method_expansion", "+IsoSpace +isotope +niche", "+isotopic +niche +space", 0, NA,
  "TRO", "Diet Analysis Methods", "Trophic Position Calculation", FALSE, "Stable Isotope Analysis", "Estimating trophic level from isotopes", "Trophic level, TP calculation", "method_expansion", "+trophic +position +isotope*", "+trophic +level +calculation", 0, NA,

  # Food Webs & Community
  "TRO", "Trophic Position & Food Webs", "Network Analysis Food Web", FALSE, "Food Web Models", "Graph theory for food web structure", "Food web networks, trophic networks", "method_expansion", "+network +analysis +food +web", "+trophic +network*", 0, NA,
  "TRO", "Trophic Position & Food Webs", "PERMANOVA", FALSE, "Food Web Models", "Permutational multivariate analysis of variance", "Permutational ANOVA, non-parametric MANOVA", "method_expansion", "+PERMANOVA +community +analysis", "+permutation* +ANOVA", 0, NA,
  "TRO", "Trophic Position & Food Webs", "NMDS", FALSE, "Food Web Models", "Non-metric multidimensional scaling for community composition", "Non-metric MDS, ordination", "method_expansion", "+NMDS +community +composition", "+non +metric +multidimensional +scaling", 0, NA,

  # Foraging & Energetics
  "TRO", "Foraging Ecology", "Optimal Foraging Theory", FALSE, "Foraging Behavior", "Modeling foraging decisions", "OFT, foraging models", "method_expansion", "+optimal +foraging +theory", "+OFT +foraging +behav*", 0, NA,
  "TRO", "Foraging Ecology", "Dynamic Energy Budget", FALSE, "Foraging Behavior", "Physiological energetics modeling", "DEB theory, DEB models", "method_expansion", "+dynamic +energy +budget", "+DEB +theory +model*", 0, NA,

  # === BEH - Behaviour (6 techniques) ===

  # Behavioural Observation
  "BEH", "Behavioural Observation", "Ethogram Development", FALSE, "Behavioural Observation", "Standardized behavioral catalog", "Behavioral repertoire", "method_expansion", "+ethogram +behav* +catalog", "+behav* +repertoire", 0, NA,
  "BEH", "Behavioural Observation", "Focal Sampling", FALSE, "Behavioural Observation", "Continuous observation of individual", "Focal animal sampling", "method_expansion", "+focal +sampling +behav*", "+focal +animal +observation", 0, NA,
  "BEH", "Behavioural Observation", "Scan Sampling", FALSE, "Behavioural Observation", "Instantaneous group behavior recording", "Instantaneous sampling", "method_expansion", "+scan +sampling +behav*", "+instantaneous +sampling", 0, NA,
  "BEH", "Behavioural Observation", "BORIS", FALSE, "Video Analysis", "Behavioral observation software", "Behavioral Observation Research Interactive Software", "method_expansion", "+BORIS +behav* +observation +software", NA, 0, NA,

  # Cognition
  "BEH", "Cognition & Learning", "Operant Conditioning", FALSE, "Learning Experiments", "Experimental learning paradigms", "Conditioning experiments", "method_expansion", "+operant +condition* +learning", "+reinforcement +learning +fish*", 0, NA,
  "BEH", "Cognition & Learning", "Cognitive Testing", FALSE, "Cognition", "Problem-solving and memory tests", "Cognitive performance, cognitive ability", "method_expansion", "+cognitive +test* +problem +solving", "+cognitive +performance +fish*", 0, NA,

  # === GEN - Genetics (9 techniques) ===

  # Population Genetics
  "GEN", "Population Genetics", "STRUCTURE", FALSE, "Population Genetics", "Bayesian clustering for population structure", "Structure analysis", "method_expansion", "+STRUCTURE +population +genetics +software", "+bayesian +clustering +population", 0, NA,
  "GEN", "Population Genetics", "ADMIXTURE", FALSE, "Population Genetics", "Maximum likelihood population structure", "Admixture analysis", "method_expansion", "+ADMIXTURE +population +structure", "+admixture +analysis +genetics", 0, NA,
  "GEN", "Population Genetics", "FST Analysis", FALSE, "Population Genetics", "Population differentiation metrics", "F-statistics, genetic differentiation", "method_expansion", "+FST +population +differentiation", "+F +statistic* +genetics", 0, NA,
  "GEN", "Population Genetics", "PCA Genetics", FALSE, "Population Genetics", "PCA for genetic data visualization", "Genetic PCA, PC analysis", "method_expansion", "+PCA +population +genetics", "+principal +component* +genetic*", 0, NA,
  "GEN", "Population Genetics", "DAPC", FALSE, "Population Genetics", "Discriminant analysis of principal components", "Discriminant PCA", "method_expansion", "+DAPC +population +genetics", "+discriminant +analysis +principal +components", 0, NA,

  # Genomics
  "GEN", "Genomics", "Genome Assembly", FALSE, "Genomics", "De novo genome reconstruction", "De novo assembly", "method_expansion", "+genome +assembly +de +novo", "+genome +sequencing +assembly", 0, NA,
  "GEN", "Genomics", "RNA-seq", FALSE, "Genomics", "Transcriptome sequencing and analysis", "RNA sequencing", "method_expansion", "+RNA +seq +transcriptom*", "+RNA +sequencing", 0, NA,

  # eDNA
  "GEN", "eDNA & Metabarcoding", "qPCR eDNA", FALSE, "eDNA", "Quantitative PCR for species detection", "Quantitative PCR, real-time PCR", "method_expansion", "+qPCR +eDNA +detection", "+quantitative +PCR +environmental +DNA", 0, NA,
  "GEN", "eDNA & Metabarcoding", "ddPCR eDNA", FALSE, "eDNA", "Droplet digital PCR for precise quantification", "Digital PCR", "method_expansion", "+ddPCR +eDNA", "+droplet +digital +PCR +environmental", 0, NA,

  # === BIO - Biology (5 techniques) ===

  # Age & Growth
  "BIO", "Age & Growth Methods", "Growth Curve Modeling", FALSE, "Age & Growth", "von Bertalanffy, Gompertz, logistic growth models", "von Bertalanffy, VBGF, growth modeling", "method_expansion", "+von +Bertalanffy +growth", "+growth +curve +model*", 0, NA,
  "BIO", "Age & Growth Methods", "Length-Frequency Analysis", FALSE, "Age & Growth", "Age/cohort estimation from length distributions", "Modal progression analysis, ELEFAN", "method_expansion", "+length +frequency +analysis +age", "+modal +progression +analysis", 0, NA,

  # Physiology
  "BIO", "Physiology", "Respirometry", FALSE, "Physiology", "Oxygen consumption measurement", "Metabolic measurement, oxygen consumption", "method_expansion", "+respirometry +metabol*", "+oxygen +consumption +measurement", 0, NA,

  # Reproductive Biology
  "BIO", "Reproductive Biology", "Maturity Ogive", FALSE, "Reproduction", "Age/length at maturity estimation", "Maturity curve, L50/A50", "method_expansion", "+maturity +ogive", "+length +maturity +L50", 0, NA,

  # Disease & Health
  "BIO", "Disease, Parasites, & Health", "Blood Chemistry", FALSE, "Health & Disease", "Hematology and plasma chemistry", "Hematology, clinical chemistry", "method_expansion", "+blood +chemistry +fish*", "+hematology +health", 0, NA,

  # === CON - Conservation (3 techniques) ===

  # Conservation Assessment
  "CON", "Conservation Assessment", "IUCN Criteria Application", FALSE, "IUCN Red List Assessment", "Specific Red List criteria (A-E)", "Red List criteria, IUCN categories", "method_expansion", "+IUCN +criteria +red +list", "+IUCN +categor* +assessment", 0, NA,

  # Policy & Governance
  "CON", "Policy & Governance", "Policy Impact Evaluation", FALSE, "Policy Evaluation", "Evaluating conservation policy outcomes", "Policy effectiveness, impact assessment", "method_expansion", "+policy +impact +evaluation +conservation", "+policy +effectiveness +assessment", 0, NA,

  # Human Dimensions
  "CON", "Human Dimensions", "Contingent Valuation", FALSE, "Human Dimensions", "Economic valuation of ecosystem services", "Willingness to pay, WTP", "method_expansion", "+contingent +valuation +conservation", "+willingness +pay +ecosystem", 0, NA
)

cat(sprintf("Created %d new technique entries\n\n", nrow(new_techniques)))

# 4. VERIFY NEW TECHNIQUES STRUCTURE ------------------------------------------
cat("Verifying new techniques structure...\n")
cat(sprintf("  Columns match: %s\n", identical(names(new_techniques), names(master_techniques))))
cat(sprintf("  All eea_count = 0: %s\n", all(new_techniques$eea_count == 0)))
cat(sprintf("  All data_source = 'method_expansion': %s\n", all(new_techniques$data_source == "method_expansion")))

# Count by discipline
discipline_counts <- new_techniques %>%
  count(discipline_code) %>%
  arrange(desc(n))

cat("\nNew techniques by discipline:\n")
print(discipline_counts, n = Inf)

# 5. COMBINE AND SAVE ---------------------------------------------------------
cat("\nCombining existing and new techniques...\n")
combined_techniques <- bind_rows(master_techniques, new_techniques)
cat(sprintf("Total techniques: %d (original: %d + new: %d)\n",
            nrow(combined_techniques), nrow(master_techniques), nrow(new_techniques)))

# Sort by discipline, category, parent/child structure
combined_techniques <- combined_techniques %>%
  arrange(discipline_code, category_name, desc(is_parent), parent_technique, technique_name)

# Save updated master file
output_file <- "data/master_techniques.csv"
cat(sprintf("\nSaving updated file: %s\n", output_file))
write_csv(combined_techniques, output_file)

# 6. GENERATE SUMMARY STATISTICS ----------------------------------------------
cat("\n", strrep("=", 70), "\n", sep = "")
cat("EXPANSION SUMMARY\n")
cat(strrep("=", 70), "\n\n", sep = "")

cat(sprintf("Original techniques:     %3d\n", nrow(master_techniques)))
cat(sprintf("New techniques added:    %3d\n", nrow(new_techniques)))
cat(sprintf("Total techniques:        %3d\n", nrow(combined_techniques)))
cat(sprintf("Increase:                %3.1f%%\n\n", (nrow(new_techniques) / nrow(master_techniques)) * 100))

# Summary by discipline (combined)
cat("TECHNIQUES BY DISCIPLINE (After Expansion):\n")
cat(strrep("-", 70), "\n", sep = "")

discipline_summary <- combined_techniques %>%
  group_by(discipline_code) %>%
  summarise(
    total = n(),
    parent = sum(is_parent),
    child = sum(!is_parent),
    from_expansion = sum(data_source == "method_expansion"),
    .groups = "drop"
  ) %>%
  arrange(desc(total))

print(discipline_summary, n = Inf)

cat("\n", strrep("-", 70), "\n", sep = "")
cat(sprintf("TOTAL: %d techniques (%d parent, %d child, %d from expansion)\n\n",
            sum(discipline_summary$total),
            sum(discipline_summary$parent),
            sum(discipline_summary$child),
            sum(discipline_summary$from_expansion)))

# Category summary
cat("TOP 10 CATEGORIES BY TECHNIQUE COUNT:\n")
cat(strrep("-", 70), "\n", sep = "")

category_summary <- combined_techniques %>%
  count(discipline_code, category_name) %>%
  arrange(desc(n)) %>%
  head(10)

print(category_summary, n = Inf)

cat("\n", strrep("=", 70), "\n", sep = "")
cat("EXPANSION COMPLETE\n")
cat(strrep("=", 70), "\n\n", sep = "")

cat("Files created:\n")
cat(sprintf("  - %s (backup)\n", backup_file))
cat(sprintf("  - %s (updated with 84 new techniques)\n", output_file))
cat("\n")
