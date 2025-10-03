-- ============================================================================
-- EEA 2025 Data Panel: Analysis Approach Binary Columns
-- ============================================================================
--
-- Purpose: Add ~150 binary columns for analytical method tracking
--
-- Schema Version: 1.0
-- Created: 2025-10-02
-- Database: DuckDB
--
-- Dependencies: 01_create_core_table.sql, 02_add_discipline_columns.sql
--
-- Design Rationale:
--   - Track analytical methods used in each study
--   - Papers often use multiple analytical approaches
--   - Binary columns enable multi-method tracking
--   - Prefix 'a_' identifies analysis approach columns
--   - Column names use lowercase with underscores
--   - Default FALSE for explicit missing data tracking
--
-- Source: Phase 1 literature review (expert-identified methods)
--   - Reviewing panel will identify analytical approaches used across studies
--   - Methods categorized by discipline
--   - Estimated ~150 distinct analytical approaches
--
-- ============================================================================
-- IMPORTANT: This file is a PLACEHOLDER
-- ============================================================================
--
-- BLOCKER: Phase 1 review required to identify analytical approaches
--
-- TO COMPLETE THIS FILE:
-- 1. Complete Phase 1 literature review with expert panel
-- 2. Extract and categorize analytical approaches by discipline
-- 3. Consolidate synonymous methods (e.g., "acoustic telemetry" = "acoustic tracking")
-- 4. Generate ALTER TABLE statements programmatically
-- 5. Create indexes for commonly-used methods
-- 6. Create helper views for method summary statistics
--
-- ESTIMATED COMPLETION: After Phase 1 review (Week 3, Task D1.1)
--
-- ============================================================================

-- ============================================================================
-- Example Analysis Columns by Discipline (Template - DO NOT RUN)
-- ============================================================================

/*
-- Movement, Space Use & Habitat Modeling (examples)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_acoustic_telemetry BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_satellite_tracking BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_archival_tagging BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_mark_recapture BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_photo_id BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_species_distribution_model BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_maxent BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_boosted_regression_tree BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_random_forest BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_generalized_additive_model BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_habitat_suitability_index BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_home_range_analysis BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_kernel_density_estimation BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_movement_path_analysis BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_state_space_model BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_hidden_markov_model BOOLEAN DEFAULT FALSE;

-- Genetics, Genomics & eDNA (examples)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_microsatellite BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_snp_genotyping BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_whole_genome_sequencing BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_rad_seq BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_mitochondrial_dna BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_edna_metabarcoding BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_population_structure_analysis BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_phylogenetic_analysis BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_genetic_diversity_metrics BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_parentage_analysis BOOLEAN DEFAULT FALSE;

-- Trophic & Community Ecology (examples)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_stable_isotope_analysis BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_carbon_isotope BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_nitrogen_isotope BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_stomach_content_analysis BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_diet_breadth_metrics BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_trophic_level_estimation BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_mixing_model BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_food_web_analysis BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_network_analysis BOOLEAN DEFAULT FALSE;

-- Biology, Life History & Health (examples)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_age_growth_analysis BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_von_bertalanffy_growth BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_length_frequency_analysis BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_maturity_analysis BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_fecundity_analysis BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_reproductive_cycle_analysis BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_endocrine_assay BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_stress_biomarker BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_parasite_identification BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_disease_pathology BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_telomere_analysis BOOLEAN DEFAULT FALSE;

-- Fisheries, Stock Assessment & Management (examples)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_catch_per_unit_effort BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_surplus_production_model BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_stock_synthesis BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_integrated_analysis BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_mortality_estimation BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_fishery_observer_data BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_bycatch_estimation BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_discard_mortality BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_selectivity_analysis BOOLEAN DEFAULT FALSE;

-- Behaviour & Sensory Ecology (examples)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_accelerometry BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_video_analysis BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_underwater_observation BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_electroretinography BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_olfactory_assay BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_electroreception_assay BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_magnetoreception_assay BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_social_network_analysis BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_behavioral_experiment BOOLEAN DEFAULT FALSE;

-- Conservation Policy & Human Dimensions (examples)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_iucn_assessment BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_extinction_risk_model BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_stakeholder_interview BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_questionnaire_survey BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_socioeconomic_analysis BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_policy_analysis BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_mpa_effectiveness BOOLEAN DEFAULT FALSE;

-- Data Science & Integrative Methods (examples)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_machine_learning BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_random_forest_ml BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_neural_network BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_deep_learning BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_bayesian_hierarchical_model BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_bayesian_network BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_ensemble_modeling BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_simulation_modeling BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_agent_based_model BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS a_meta_analysis BOOLEAN DEFAULT FALSE;

-- ... (continue for all ~150 analytical approaches)
*/

-- ============================================================================
-- Programmatic Generation Workflow
-- ============================================================================

/*
# Python example for generating SQL from Phase 1 review data

import pandas as pd

# Load Phase 1 review results with extracted analytical approaches
methods_df = pd.read_csv('phase1_analytical_approaches.csv')

# Clean method names for SQL column names
methods_df['column_name'] = (
    'a_' +
    methods_df['method_name']
    .str.lower()
    .str.replace(' ', '_')
    .str.replace('-', '_')
    .str.replace('(', '')
    .str.replace(')', '')
    .str.replace('/', '_')
)

# Remove duplicates and consolidate synonyms
methods_df = methods_df.drop_duplicates(subset=['column_name'])

# Generate ALTER TABLE statements
with open('07_add_analysis_columns.sql', 'w') as f:
    f.write('-- Auto-generated from Phase 1 review\n\n')

    # Group by discipline for organization
    for discipline in methods_df['discipline'].unique():
        discipline_methods = methods_df[methods_df['discipline'] == discipline]

        f.write(f'\n-- {discipline} ({len(discipline_methods)} methods)\n')

        for idx, row in discipline_methods.iterrows():
            f.write(f"ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS "
                    f"{row['column_name']} BOOLEAN DEFAULT FALSE; "
                    f"-- {row['method_name']}\n")

    # Add indexes for top 50 most-used methods
    top_methods = methods_df.nlargest(50, 'paper_count')
    f.write('\n-- Indexes for frequently-used methods\n')
    for idx, row in top_methods.iterrows():
        f.write(f"CREATE INDEX IF NOT EXISTS idx_{row['column_name']} "
                f"ON literature_review({row['column_name']}) "
                f"WHERE {row['column_name']} = TRUE;\n")

print(f"Generated {len(methods_df)} analytical approach columns")
*/

/*
# R equivalent

library(dplyr)
library(stringr)

# Load Phase 1 review results
methods_df <- read.csv('phase1_analytical_approaches.csv')

# Clean method names for SQL column names
methods_df <- methods_df %>%
  mutate(
    column_name = paste0(
      'a_',
      str_to_lower(method_name) %>%
        str_replace_all(' ', '_') %>%
        str_replace_all('-', '_') %>%
        str_replace_all('[()]', '') %>%
        str_replace_all('/', '_')
    )
  ) %>%
  distinct(column_name, .keep_all = TRUE)

# Generate ALTER TABLE statements
sql_lines <- c('-- Auto-generated from Phase 1 review\n')

for (discipline in unique(methods_df$discipline)) {
  discipline_methods <- filter(methods_df, discipline == !!discipline)

  sql_lines <- c(sql_lines,
    sprintf('\n-- %s (%d methods)', discipline, nrow(discipline_methods)))

  for (i in 1:nrow(discipline_methods)) {
    row <- discipline_methods[i, ]
    sql_lines <- c(sql_lines,
      sprintf("ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS %s BOOLEAN DEFAULT FALSE; -- %s",
              row$column_name, row$method_name))
  }
}

# Add indexes for top 50 most-used methods
top_methods <- methods_df %>% arrange(desc(paper_count)) %>% head(50)
sql_lines <- c(sql_lines, '\n-- Indexes for frequently-used methods')

for (i in 1:nrow(top_methods)) {
  row <- top_methods[i, ]
  sql_lines <- c(sql_lines,
    sprintf("CREATE INDEX IF NOT EXISTS idx_%s ON literature_review(%s) WHERE %s = TRUE;",
            row$column_name, row$column_name, row$column_name))
}

writeLines(sql_lines, '07_add_analysis_columns.sql')
cat(sprintf("Generated %d analytical approach columns\n", nrow(methods_df)))
*/

-- ============================================================================
-- Helper Views (TO BE CREATED after analysis columns added)
-- ============================================================================

/*
-- Method summary by discipline
CREATE OR REPLACE VIEW v_method_summary AS
SELECT
    discipline,
    column_name,
    method_name,
    paper_count,
    ROUND(100.0 * paper_count / total_papers, 2) AS percentage
FROM (
    -- To be populated after Phase 1 review
)
ORDER BY discipline, paper_count DESC;

-- Multi-method papers
CREATE OR REPLACE VIEW v_multi_method_papers AS
SELECT
    study_id,
    title,
    year,
    (CAST(a_acoustic_telemetry AS INTEGER) +
     CAST(a_satellite_tracking AS INTEGER) +
     -- ... sum all method columns
    ) AS method_count
FROM literature_review
WHERE method_count > 1
ORDER BY method_count DESC, year DESC;

-- Method co-occurrence matrix (for network analysis)
CREATE OR REPLACE VIEW v_method_cooccurrence AS
SELECT
    m1.method_name AS method_1,
    m2.method_name AS method_2,
    COUNT(*) AS cooccurrence_count
FROM literature_review lr
CROSS JOIN (SELECT column_name, method_name FROM method_lookup) m1
CROSS JOIN (SELECT column_name, method_name FROM method_lookup) m2
WHERE lr.[m1.column_name] = TRUE
  AND lr.[m2.column_name] = TRUE
  AND m1.column_name < m2.column_name  -- Avoid duplicates
GROUP BY m1.method_name, m2.method_name
ORDER BY cooccurrence_count DESC;
*/

-- ============================================================================
-- Comments & Documentation (TO BE CREATED)
-- ============================================================================

/*
COMMENT ON COLUMN literature_review.a_acoustic_telemetry IS 'Method: Acoustic telemetry tracking';
COMMENT ON COLUMN literature_review.a_stable_isotope_analysis IS 'Method: Stable isotope analysis (carbon, nitrogen)';
-- ... (repeat for all methods)
*/

-- ============================================================================
-- Usage Examples (AFTER analysis columns added)
-- ============================================================================

/*
-- Mark a paper using multiple analytical approaches
UPDATE literature_review
SET
    a_acoustic_telemetry = TRUE,
    a_state_space_model = TRUE,
    a_generalized_additive_model = TRUE
WHERE study_id = 1;

-- Find all papers using acoustic telemetry
SELECT title, year
FROM literature_review
WHERE a_acoustic_telemetry = TRUE;

-- Count papers by method (top 20)
SELECT * FROM v_method_summary LIMIT 20;

-- Find multi-method integrative studies
SELECT * FROM v_multi_method_papers LIMIT 10;

-- Identify method trends over time
SELECT
    year,
    SUM(CASE WHEN a_acoustic_telemetry THEN 1 ELSE 0 END) AS acoustic_telemetry,
    SUM(CASE WHEN a_satellite_tracking THEN 1 ELSE 0 END) AS satellite_tracking,
    SUM(CASE WHEN a_species_distribution_model THEN 1 ELSE 0 END) AS sdm
FROM literature_review
WHERE d_movement_spatial = TRUE
  AND year BETWEEN 2000 AND 2025
GROUP BY year
ORDER BY year;

-- Find method co-occurrences (e.g., telemetry + modeling)
SELECT * FROM v_method_cooccurrence
WHERE method_1 LIKE '%telemetry%'
ORDER BY cooccurrence_count DESC
LIMIT 10;
*/

-- ============================================================================
-- END OF PLACEHOLDER FILE
-- ============================================================================
-- To complete: Conduct Phase 1 literature review and extract analytical approaches
-- Timeline: Week 3 (after expert panel completes initial paper review)
-- ============================================================================
