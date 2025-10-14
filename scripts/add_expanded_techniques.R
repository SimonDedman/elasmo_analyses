#!/usr/bin/env Rscript
# ==============================================================================
# Add Expanded Techniques to Master CSV
# ==============================================================================
# Adds 84 new techniques based on literature review and domain knowledge
# ==============================================================================

library(tidyverse)

cat("=== Adding Expanded Techniques to Master CSV ===\n\n")

# Load current master
master <- read_csv("data/master_techniques.csv", show_col_types = FALSE)
cat("Current techniques:", nrow(master), "\n")

# Helper function to create technique rows
make_tech <- function(d, cat, tech, par=TRUE, par_tech=NA, desc="", syn=NA, src="method_expansion", q1="", q2=NA, eea=0) {
  tibble(discipline_code=d, category_name=cat, technique_name=tech, is_parent=par,
         parent_technique=par_tech, description=desc, synonyms=syn, data_source=src,
         search_query=q1, search_query_alt=q2, eea_count=eea, notes=NA_character_)
}

# ==============================================================================
# MOV - Movement (15 new techniques)
# ==============================================================================

mov_new <- bind_rows(
  # Species Distribution Models (5)
  make_tech("MOV", "Habitat Modeling", "Random Forest", FALSE, "Species Distribution Model",
    "Machine learning ensemble method for SDM", "RF for SDM",
    "method_expansion", "+species +distribution +random +forest", "+SDM +RF", 0),

  make_tech("MOV", "Habitat Modeling", "Boosted Regression Trees", FALSE, "Species Distribution Model",
    "Gradient boosting for SDM", "BRT, GBM, Gradient Boosted Models",
    "method_expansion", "+BRT +species +distribution", "+boosted +regression +tree* +SDM", 0),

  make_tech("MOV", "Habitat Modeling", "Generalized Additive Models", FALSE, "Species Distribution Model",
    "GAMs for non-linear species-environment relationships", "GAM, GAMM for SDM",
    "method_expansion", "+GAM +species +distribution", "+additive +model* +habitat", 0),

  make_tech("MOV", "Habitat Modeling", "Generalized Linear Models", FALSE, "Species Distribution Model",
    "GLMs for species distribution", "GLM, logistic regression for SDM",
    "method_expansion", "+GLM +species +distribution", "+generalized +linear +model* +habitat", 0),

  make_tech("MOV", "Habitat Modeling", "Neural Network SDMs", FALSE, "Species Distribution Model",
    "Deep learning for species distribution", "CNN for SDM, deep SDM",
    "method_expansion", "+neural +network +species +distribution", "+deep +learning +SDM", 0),

  # Home Range (4)
  make_tech("MOV", "Movement Analysis", "Kernel Density Estimation", FALSE, "Home Range Analysis",
    "Probabilistic home range estimation", "KDE, utilization distribution, UD",
    "method_expansion", "+kernel +density +home +range", "+KDE +utilization +distribution", 0),

  make_tech("MOV", "Movement Analysis", "Minimum Convex Polygon", FALSE, "Home Range Analysis",
    "Smallest polygon enclosing all relocations", "MCP, convex hull",
    "method_expansion", "+MCP +home +range", "+minimum +convex +polygon", 0),

  make_tech("MOV", "Movement Analysis", "Brownian Bridge Movement Model", FALSE, "Home Range Analysis",
    "Path-based home range accounting for movement between fixes", "BBMM, dynamic Brownian bridge",
    "method_expansion", "+brownian +bridge +home +range", "+BBMM +movement", 0),

  make_tech("MOV", "Movement Analysis", "Autocorrelated Kernel Density", FALSE, "Home Range Analysis",
    "KDE accounting for temporal autocorrelation", "AKDE",
    "method_expansion", "+AKDE +home +range", "+autocorrelat* +kernel +density", 0),

  # Movement Modeling (3)
  make_tech("MOV", "Movement Analysis", "Hidden Markov Models", FALSE, "Movement Modeling",
    "State-space models for behavioral state estimation", "HMM, behavioral state models",
    "method_expansion", "+hidden +markov +movement", "+HMM +behav* +state", 0),

  make_tech("MOV", "Movement Analysis", "State-Space Models", FALSE, "Movement Modeling",
    "Filtering location error and estimating movement parameters", "SSM, Kalman filter",
    "method_expansion", "+state +space +model* +movement", "+SSM +telemetry", 0),

  make_tech("MOV", "Movement Analysis", "Step Selection Functions", FALSE, "Movement Modeling",
    "Resource selection at movement step scale", "SSF, integrated step selection",
    "method_expansion", "+step +selection +function*", "+SSF +movement", 0),

  make_tech("MOV", "Movement Analysis", "Resource Selection Functions", TRUE, NA,
    "Habitat selection analysis", "RSF, resource utilization functions",
    "method_expansion", "+resource +selection +function*", "+RSF +habitat +selection", 0),

  # Spatial Conservation (2)
  make_tech("MOV", "Spatial Conservation", "Network Analysis", TRUE, NA,
    "Graph theory for connectivity and MPA networks", "Graph theory, circuit theory",
    "method_expansion", "+network +analysis +connectivity +spatial", "+graph +theory +conservation", 0),

  make_tech("MOV", "Spatial Conservation", "Marxan", TRUE, NA,
    "Spatial prioritization software", "Zonation, systematic conservation planning",
    "method_expansion", "+marxan +conservation +planning", "+zonation +prioritization", 0)
)

cat("MOV: Adding", nrow(mov_new), "techniques\n")

# ==============================================================================
# FISH - Fisheries (18 new techniques)
# ==============================================================================

fish_new <- bind_rows(
  # Stock Assessment (7)
  make_tech("FISH", "Stock Assessment", "Statistical Catch-at-Age", FALSE, "Stock Assessment",
    "Age-structured assessment using catch composition", "SCA, catch-at-age analysis",
    "method_expansion", "+statistical +catch +age", "+SCA +stock +assessment", 0),

  make_tech("FISH", "Stock Assessment", "Stock Synthesis", FALSE, "Stock Assessment",
    "Integrated age-structured assessment framework (NOAA)", "SS3, Stock Synthesis 3",
    "method_expansion", "+stock +synthesis +SS3", "+stock +synthesis +assessment", 0),

  make_tech("FISH", "Stock Assessment", "Virtual Population Analysis", FALSE, "Stock Assessment",
    "Cohort analysis for estimating fishing mortality", "VPA, cohort analysis",
    "method_expansion", "+VPA +virtual +population", "+cohort +analysis +fisheries", 0),

  make_tech("FISH", "Stock Assessment", "Spawning Stock Biomass per Recruit", FALSE, "Stock Assessment",
    "Per-recruit analysis for reference points", "SSB/R, spawning potential ratio, SPR",
    "method_expansion", "+spawning +biomass +recruit", "+SPR +fisheries", 0),

  make_tech("FISH", "Stock Assessment", "Yield per Recruit", FALSE, "Stock Assessment",
    "Per-recruit models for yield optimization", "Y/R, yield-per-recruit analysis",
    "method_expansion", "+yield +per +recruit", "+YPR +fisheries", 0),

  make_tech("FISH", "Stock Assessment", "Delay-Difference Models", FALSE, "Stock Assessment",
    "Population models incorporating somatic growth", "Deriso-Schnute model",
    "method_expansion", "+delay +difference +model* +stock", "+Deriso +Schnute", 0),

  make_tech("FISH", "Stock Assessment", "Catch Curve Analysis", FALSE, "Stock Assessment",
    "Mortality estimation from age/length composition", "Catch curve, age-based mortality",
    "method_expansion", "+catch +curve +mortality", "+catch +curve +analysis", 0),

  # Data-Poor Methods (5)
  make_tech("FISH", "Data-Poor Methods", "LIME", FALSE, "Data-Poor Methods",
    "Length-based Integrated Mixed Effects assessment", "Length-based integrated assessment",
    "method_expansion", "+LIME +length +based +assessment", "+length +integrated +mixed +effects", 0),

  make_tech("FISH", "Data-Poor Methods", "LBSPR", FALSE, "Data-Poor Methods",
    "Length-Based Spawning Potential Ratio estimation", "Length-based SPR",
    "method_expansion", "+LBSPR +spawning +potential", "+length +based +SPR", 0),

  make_tech("FISH", "Data-Poor Methods", "Catch-MSY", FALSE, "Data-Poor Methods",
    "Data-limited method using catch and priors", "CMSY",
    "method_expansion", "+catch +MSY +data +poor", "+CMSY +stock +assessment", 0),

  make_tech("FISH", "Data-Poor Methods", "Depletion Methods", FALSE, "Data-Poor Methods",
    "Abundance estimation from catch and effort decline", "Leslie-DeLury, depletion estimators",
    "method_expansion", "+depletion +method* +abundance", "+Leslie +DeLury", 0),

  make_tech("FISH", "Data-Poor Methods", "Life History Invariant Methods", FALSE, "Data-Poor Methods",
    "Natural mortality estimators (Hoenig, Pauly, etc.)", "M estimators, empirical mortality",
    "method_expansion", "+natural +mortality +Hoenig", "+natural +mortality +Pauly", 0),

  # CPUE (4)
  make_tech("FISH", "CPUE & Abundance", "GLM CPUE Standardization", FALSE, "CPUE Standardization",
    "Generalized linear models for CPUE", "GLM standardization",
    "method_expansion", "+GLM +CPUE +standardization", NA, 0),

  make_tech("FISH", "CPUE & Abundance", "GAM CPUE Standardization", FALSE, "CPUE Standardization",
    "Generalized additive models for CPUE", "GAM standardization, non-linear CPUE",
    "method_expansion", "+GAM +CPUE +standardization", NA, 0),

  make_tech("FISH", "CPUE & Abundance", "Random Forest CPUE", FALSE, "CPUE Standardization",
    "Machine learning for CPUE standardization", "RF CPUE",
    "method_expansion", "+random +forest +CPUE", "+machine +learning +CPUE +standardization", 0),

  make_tech("FISH", "CPUE & Abundance", "Distance Sampling", TRUE, NA,
    "Abundance estimation accounting for detection probability", "Line transect, strip transect",
    "method_expansion", "+distance +sampling +abundance", "+line +transect +fish*", 0),

  # Bycatch (2)
  make_tech("FISH", "Bycatch & Interactions", "Post-Release Mortality", FALSE, "Discard Mortality",
    "Survival estimation after release", "Release mortality, discard survival",
    "method_expansion", "+post +release +mortality", "+discard +survival", 0),

  make_tech("FISH", "Bycatch & Interactions", "Observer Coverage Analysis", TRUE, NA,
    "Extrapolating bycatch from observer data", "Observer program analysis",
    "method_expansion", "+observer +coverage +bycatch", "+observer +data +extrapolation", 0)
)

cat("FISH: Adding", nrow(fish_new), "techniques\n")

# ==============================================================================
# DATA - Data Science (20 new techniques)
# ==============================================================================

data_new <- bind_rows(
  # Machine Learning (5)
  make_tech("DATA", "Machine Learning & AI", "Boosted Regression Trees", FALSE, "Machine Learning",
    "Gradient boosting machine learning", "BRT, GBM, XGBoost, gradient boosting",
    "method_expansion", "+boosted +regression +tree*", "+GBM +XGBoost", 0),

  make_tech("DATA", "Machine Learning & AI", "Support Vector Machines", FALSE, "Machine Learning",
    "Classification and regression ML method", "SVM, support vector regression",
    "method_expansion", "+support +vector +machine*", "+SVM +classification", 0),

  make_tech("DATA", "Machine Learning & AI", "Convolutional Neural Networks", FALSE, "Neural Networks",
    "Deep learning for image/spatial data", "CNN, ConvNet",
    "method_expansion", "+convolutional +neural +network*", "+CNN +deep +learning", 0),

  make_tech("DATA", "Machine Learning & AI", "Ensemble Learning", TRUE, NA,
    "Combining multiple models", "Model averaging, stacking",
    "method_expansion", "+ensemble +learning +model*", "+model +averaging", 0),

  make_tech("DATA", "Machine Learning & AI", "Computer Vision", TRUE, NA,
    "Image/video analysis with ML", "Image recognition, object detection",
    "method_expansion", "+computer +vision", "+image +recognition +fish*", 0),

  # Statistical Models (5)
  make_tech("DATA", "Statistical Models", "Generalized Additive Mixed Models", FALSE, "GAMs",
    "GAMs with random effects", "GAMM",
    "method_expansion", "+GAMM +generalized +additive +mixed", "+GAMM +model*", 0),

  make_tech("DATA", "Statistical Models", "Generalized Estimating Equations", TRUE, NA,
    "Marginal models for correlated data", "GEE",
    "method_expansion", "+generalized +estimating +equation*", "+GEE +correlated +data", 0),

  make_tech("DATA", "Statistical Models", "Hierarchical Models", TRUE, NA,
    "Multi-level statistical models", "Multilevel models, nested models",
    "method_expansion", "+hierarchical +model* +statistical", "+multilevel +model*", 0),

  make_tech("DATA", "Statistical Models", "ARIMA Models", FALSE, "Time Series Analysis",
    "Autoregressive integrated moving average", "Time series forecasting, Box-Jenkins",
    "method_expansion", "+ARIMA +time +series", "+autoregressive +model*", 0),

  make_tech("DATA", "Statistical Models", "Structural Equation Modeling", TRUE, NA,
    "Multivariate causal modeling", "SEM, path analysis",
    "method_expansion", "+structural +equation +model*", "+SEM +causal +analysis", 0),

  # Bayesian (5)
  make_tech("DATA", "Bayesian Methods", "INLA", TRUE, NA,
    "Integrated Nested Laplace Approximation for spatial models", "R-INLA",
    "method_expansion", "+INLA +bayesian +spatial", "+integrated +nested +laplace", 0),

  make_tech("DATA", "Bayesian Methods", "Stan", TRUE, NA,
    "Probabilistic programming language for Bayesian inference", "RStan, PyStan",
    "method_expansion", "+Stan +bayesian +inference", "+RStan +model*", 0),

  make_tech("DATA", "Bayesian Methods", "JAGS", TRUE, NA,
    "Just Another Gibbs Sampler for Bayesian models", "rjags",
    "method_expansion", "+JAGS +bayesian +model*", "+gibbs +sampl*", 0),

  make_tech("DATA", "Bayesian Methods", "Approximate Bayesian Computation", TRUE, NA,
    "Likelihood-free Bayesian inference", "ABC, simulation-based inference",
    "method_expansion", "+approximate +bayesian +computation", "+ABC +likelihood +free", 0),

  make_tech("DATA", "Bayesian Methods", "Bayesian Network Analysis", TRUE, NA,
    "Probabilistic graphical models", "Belief networks, Bayes nets",
    "method_expansion", "+bayesian +network +analysis", "+belief +network*", 0),

  # Data Integration (5)
  make_tech("DATA", "Data Integration", "Occupancy Modeling", TRUE, NA,
    "Estimating occurrence accounting for detection", "Occupancy models, presence-absence",
    "method_expansion", "+occupancy +model* +detection", "+presence +absence +detection +probability", 0),

  make_tech("DATA", "Data Integration", "N-Mixture Models", TRUE, NA,
    "Abundance from repeated counts", "Binomial mixture models",
    "method_expansion", "+N +mixture +model*", "+binomial +mixture +abundance", 0),

  make_tech("DATA", "Data Integration", "Multi-Species Models", TRUE, NA,
    "Joint modeling of multiple species", "Community models, joint SDM",
    "method_expansion", "+multi +species +model*", "+joint +species +distribution", 0),

  make_tech("DATA", "Data Integration", "Data Fusion", TRUE, NA,
    "Combining disparate data sources", "Data integration, multi-source analysis",
    "method_expansion", "+data +fusion +integration", "+multi +source +data", 0),

  make_tech("DATA", "Data Integration", "Cross-Validation", TRUE, NA,
    "Model validation and selection", "k-fold CV, LOOCV",
    "method_expansion", "+cross +validation +model +selection", "+k +fold +validation", 0)
)

cat("DATA: Adding", nrow(data_new), "techniques\n")

# ==============================================================================
# Continue with remaining disciplines...
# (TRO, BEH, GEN, BIO, CON)
# ==============================================================================

# Save for continuation
cat("\nFirst batch ready (MOV, FISH, DATA):", nrow(mov_new) + nrow(fish_new) + nrow(data_new), "techniques\n")
cat("Continuing with remaining disciplines in next chunk...\n")
