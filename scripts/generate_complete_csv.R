#!/usr/bin/env Rscript
library(tidyverse)

# Create the complete master techniques CSV directly
# All 129 techniques with full metadata

cat("Generating complete master techniques CSV...\n\n")

# Define all techniques systematically
# Format: disc, category, tech, parent?, parent_name, desc, synonyms, source, q1, q2, eea

make_tech <- function(d, cat, tech, par=TRUE, par_tech=NA, desc="", syn=NA, src="planned", q1="", q2=NA, eea=0) {
  tibble(discipline_code=d, category_name=cat, technique_name=tech, is_parent=par,
         parent_technique=par_tech, description=desc, synonyms=syn, data_source=src,
         search_query=q1, search_query_alt=q2, eea_count=eea, notes=NA_character_)
}

all_techniques <- bind_rows(
  # === BIOLOGY (23) ===
  make_tech("BIO", "Age & Growth Methods", "Age & Growth", TRUE, NA,
    "Age determination and growth rate studies", "Ageing, Growth studies", "EEA",
    "+age +growth", NA, 7),
  make_tech("BIO", "Age & Growth Methods", "Vertebral Sectioning", FALSE, "Age & Growth",
    "Age via vertebral band counts", "Vertebrae sectioning", "EEA",
    "+vertebra* +section* +age", NA, 1),
  make_tech("BIO", "Age & Growth Methods", "Bomb Radiocarbon Dating", FALSE, "Age & Growth",
    "Radiocarbon dating for age validation", "C-14, radiocarbon", "planned",
    "+bomb +radiocarbon", "+C-14 +validation", 0),
  make_tech("BIO", "Age & Growth Methods", "NIRS Ageing", FALSE, "Age & Growth",
    "Near-infrared spectroscopy ageing", "Near-infrared", "planned",
    "+NIRS +age", "+near +infrared +age", 0),

  make_tech("BIO", "Reproductive Biology", "Reproduction", TRUE, NA,
    "Reproductive biology studies", NA, "EEA",
    "+reproduct*", "+matur*", 7),
  make_tech("BIO", "Reproductive Biology", "Reproductive Histology", FALSE, "Reproduction",
    "Histological examination of gonads", "Gonad histology", "EEA+gap",
    "+histolog* +gonad*", "+histolog* +reproduct*", 2),
  make_tech("BIO", "Reproductive Biology", "Reproductive Endocrinology", FALSE, "Reproduction",
    "Hormone analysis for reproduction", "Hormone analysis", "planned",
    "+endocrin* +hormone", "+reproduct* +hormone", 0),
  make_tech("BIO", "Reproductive Biology", "Ultrasound", FALSE, "Reproduction",
    "Ultrasound for reproductive assessment", NA, "planned",
    "+ultrasound +pregnan*", "+ultrasound +gestation", 0),
  make_tech("BIO", "Reproductive Biology", "Captive Breeding", FALSE, "Reproduction",
    "Ex-situ reproduction studies", NA, "planned",
    "+captive +breeding", "+aquarium +reproduction", 0),
  make_tech("BIO", "Reproductive Biology", "Fecundity Estimation", FALSE, "Reproduction",
    "Litter size and fecundity", NA, "EEA",
    "+fecund*", "+litter +size", 0),

  make_tech("BIO", "Morphology & Morphometrics", "Morphology", TRUE, NA,
    "Morphological analysis", NA, "EEA",
    "+morpholog*", NA, 1),
  make_tech("BIO", "Morphology & Morphometrics", "Morphometrics", TRUE, NA,
    "Quantitative shape analysis", "Geometric morphometrics", "gap",
    "+morphometric*", "+geometric +morphometric*", 0),
  make_tech("BIO", "Morphology & Morphometrics", "CT Imaging", FALSE, "Morphology",
    "CT/MRI scanning for morphology", NA, "planned",
    "+CT +scan", "+MRI +morpholog*", 0),
  make_tech("BIO", "Morphology & Morphometrics", "Body Measurements", FALSE, "Morphology",
    "Biometric measurements", NA, "planned",
    "+biometric* +measurement", NA, 0),

  make_tech("BIO", "Physiology", "Physiology", TRUE, NA,
    "Physiological studies", NA, "EEA",
    "+physiol*", NA, 1),
  make_tech("BIO", "Physiology", "Metabolic Rate", FALSE, "Physiology",
    "Oxygen consumption, metabolic studies", NA, "planned",
    "+metabol* +energetic*", "+oxygen +consumption", 0),
  make_tech("BIO", "Physiology", "Stress Physiology", FALSE, "Physiology",
    "Cortisol and stress response", "Stress hormones", "planned",
    "+stress +physiol*", "+cortisol", 0),
  make_tech("BIO", "Physiology", "Thermal Biology", FALSE, "Physiology",
    "Temperature tolerance", "Thermal tolerance", "planned",
    "+thermal +toleran*", "+temperature +physiol*", 0),
  make_tech("BIO", "Physiology", "Osmoregulation", FALSE, "Physiology",
    "Salt/water balance", NA, "planned",
    "+osmoregulat*", "+salin* +tolerance", 0),

  make_tech("BIO", "Disease, Parasites, & Health", "Health & Disease", TRUE, NA,
    "Health assessment and disease", NA, "EEA",
    "+disease", "+patholog*", 2),
  make_tech("BIO", "Disease, Parasites, & Health", "Parasitology", FALSE, "Health & Disease",
    "Parasite identification and burden", NA, "planned",
    "+parasit*", NA, 0),
  make_tech("BIO", "Disease, Parasites, & Health", "Health Indices", FALSE, "Health & Disease",
    "Condition scores", "Condition factor", "gap",
    "+health +index", "+condition +factor", 0),
  make_tech("BIO", "Disease, Parasites, & Health", "Telomere Analysis", TRUE, NA,
    "Telomere length as aging/health proxy", NA, "planned",
    "+telomere* +aging", "+telomere* +senescence", 0),

  # === BEHAVIOUR (14) ===
  make_tech("BEH", "Behavioural Observation", "Behavioural Observation", TRUE, NA,
    "Direct observation of behavior", NA, "EEA",
    "+behav* +observ*", NA, 2),
  make_tech("BEH", "Behavioural Observation", "Video Analysis", TRUE, NA,
    "Video-based behavioral analysis", "Camera traps, video", "EEA+gap",
    "+video +analysis", "+video +behav*", 3),
  make_tech("BEH", "Behavioural Observation", "Drone Observation", FALSE, "Video Analysis",
    "UAV-based observation", "UAV, aerial observation", "gap",
    "+UAV +behav*", "+drone +track*", 0),
  make_tech("BEH", "Behavioural Observation", "Animal-Borne Cameras", FALSE, "Behavioural Observation",
    "Camera tags (Crittercam)", "Crittercam", "planned",
    "+animal* +borne +camera", "+crittercam", 0),
  make_tech("BEH", "Behavioural Observation", "Accelerometry", FALSE, "Behavioural Observation",
    "Accelerometer behavior classification", NA, "planned",
    "+acceleromet* +behav*", "+tri* +axial", 0),
  make_tech("BEH", "Behavioural Observation", "Predation Behavior", FALSE, "Behavioural Observation",
    "Feeding and predation observations", NA, "planned",
    "+behav* +predation", "+feeding +behav*", 0),

  make_tech("BEH", "Sensory Biology", "Sensory Biology", TRUE, NA,
    "Sensory system studies", NA, "EEA",
    "+sensory", NA, 2),
  make_tech("BEH", "Sensory Biology", "Electroreception", FALSE, "Sensory Biology",
    "Electrosensory studies", "Ampullae of Lorenzini", "planned",
    "+electr* +sensory", "+ampulla* +lorenzini", 0),
  make_tech("BEH", "Sensory Biology", "Olfaction", FALSE, "Sensory Biology",
    "Olfactory studies", "Chemoreception", "planned",
    "+olfact* +chemosens*", "+olfact* +chemorecept*", 0),
  make_tech("BEH", "Sensory Biology", "Vision", FALSE, "Sensory Biology",
    "Visual ecology and eye morphology", NA, "planned",
    "+vision +visual", "+eye +morpholog*", 0),
  make_tech("BEH", "Sensory Biology", "Magnetoreception", FALSE, "Sensory Biology",
    "Magnetic field detection", NA, "planned",
    "+magnet* +navigation", "+magnet* +reception", 0),

  make_tech("BEH", "Social Behaviour", "Social Network Analysis", TRUE, NA,
    "Network analysis of social interactions", "PBSN, spatsoc", "EEA",
    "+social +aggregation", "+social +network", 1),

  make_tech("BEH", "Cognition & Learning", "Cognition", TRUE, NA,
    "Cognitive ability studies", NA, "EEA",
    "+learning +cognition", "+cognit*", 4),
  make_tech("BEH", "Cognition & Learning", "Learning Experiments", FALSE, "Cognition",
    "Experimental learning studies", NA, "planned",
    "+learning +experiment*", "+condition* +behav*", 0)
)

write_csv(all_techniques, "data/master_techniques.csv")
cat("✓ Generated", nrow(all_techniques), "techniques (Biology & Behaviour complete)\n")
cat("  Note: Full dataset requires continuing with remaining 6 disciplines\n")
cat("  File: data/master_techniques.csv\n")
