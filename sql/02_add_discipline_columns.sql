-- ============================================================================
-- EEA 2025 Data Panel: Discipline Classification Columns
-- ============================================================================
--
-- Purpose: Add 8 binary discipline columns for multi-label classification
--
-- Schema Version: 1.0
-- Created: 2025-10-02
-- Database: DuckDB
--
-- Dependencies: 01_create_core_table.sql
--
-- Design Rationale:
--   - Papers often span multiple disciplines (e.g., movement + genetics)
--   - Binary columns enable multi-label classification
--   - Prefix 'd_' identifies discipline columns
--   - Default FALSE for explicit missing data tracking
--
-- ============================================================================

-- ============================================================================
-- Add Discipline Binary Columns
-- ============================================================================

ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS d_biology_health BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS d_behaviour_sensory BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS d_trophic_ecology BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS d_genetics_genomics BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS d_movement_spatial BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS d_fisheries_management BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS d_conservation_policy BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS d_data_science BOOLEAN DEFAULT FALSE;

-- ============================================================================
-- Indexes for Discipline Queries
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_d_biology_health ON literature_review(d_biology_health) WHERE d_biology_health = TRUE;
CREATE INDEX IF NOT EXISTS idx_d_behaviour_sensory ON literature_review(d_behaviour_sensory) WHERE d_behaviour_sensory = TRUE;
CREATE INDEX IF NOT EXISTS idx_d_trophic_ecology ON literature_review(d_trophic_ecology) WHERE d_trophic_ecology = TRUE;
CREATE INDEX IF NOT EXISTS idx_d_genetics_genomics ON literature_review(d_genetics_genomics) WHERE d_genetics_genomics = TRUE;
CREATE INDEX IF NOT EXISTS idx_d_movement_spatial ON literature_review(d_movement_spatial) WHERE d_movement_spatial = TRUE;
CREATE INDEX IF NOT EXISTS idx_d_fisheries_management ON literature_review(d_fisheries_management) WHERE d_fisheries_management = TRUE;
CREATE INDEX IF NOT EXISTS idx_d_conservation_policy ON literature_review(d_conservation_policy) WHERE d_conservation_policy = TRUE;
CREATE INDEX IF NOT EXISTS idx_d_data_science ON literature_review(d_data_science) WHERE d_data_science = TRUE;

-- ============================================================================
-- Helper View: Discipline Summary
-- ============================================================================

CREATE OR REPLACE VIEW v_discipline_summary AS
SELECT
    'Biology, Life History & Health' AS discipline,
    'd_biology_health' AS column_name,
    SUM(CASE WHEN d_biology_health THEN 1 ELSE 0 END) AS paper_count,
    ROUND(100.0 * SUM(CASE WHEN d_biology_health THEN 1 ELSE 0 END) / COUNT(*), 2) AS percentage
FROM literature_review
UNION ALL
SELECT
    'Behaviour & Sensory Ecology',
    'd_behaviour_sensory',
    SUM(CASE WHEN d_behaviour_sensory THEN 1 ELSE 0 END),
    ROUND(100.0 * SUM(CASE WHEN d_behaviour_sensory THEN 1 ELSE 0 END) / COUNT(*), 2)
FROM literature_review
UNION ALL
SELECT
    'Trophic & Community Ecology',
    'd_trophic_ecology',
    SUM(CASE WHEN d_trophic_ecology THEN 1 ELSE 0 END),
    ROUND(100.0 * SUM(CASE WHEN d_trophic_ecology THEN 1 ELSE 0 END) / COUNT(*), 2)
FROM literature_review
UNION ALL
SELECT
    'Genetics, Genomics & eDNA',
    'd_genetics_genomics',
    SUM(CASE WHEN d_genetics_genomics THEN 1 ELSE 0 END),
    ROUND(100.0 * SUM(CASE WHEN d_genetics_genomics THEN 1 ELSE 0 END) / COUNT(*), 2)
FROM literature_review
UNION ALL
SELECT
    'Movement, Space Use & Habitat Modeling',
    'd_movement_spatial',
    SUM(CASE WHEN d_movement_spatial THEN 1 ELSE 0 END),
    ROUND(100.0 * SUM(CASE WHEN d_movement_spatial THEN 1 ELSE 0 END) / COUNT(*), 2)
FROM literature_review
UNION ALL
SELECT
    'Fisheries, Stock Assessment & Management',
    'd_fisheries_management',
    SUM(CASE WHEN d_fisheries_management THEN 1 ELSE 0 END),
    ROUND(100.0 * SUM(CASE WHEN d_fisheries_management THEN 1 ELSE 0 END) / COUNT(*), 2)
FROM literature_review
UNION ALL
SELECT
    'Conservation Policy & Human Dimensions',
    'd_conservation_policy',
    SUM(CASE WHEN d_conservation_policy THEN 1 ELSE 0 END),
    ROUND(100.0 * SUM(CASE WHEN d_conservation_policy THEN 1 ELSE 0 END) / COUNT(*), 2)
FROM literature_review
UNION ALL
SELECT
    'Data Science & Integrative Methods',
    'd_data_science',
    SUM(CASE WHEN d_data_science THEN 1 ELSE 0 END),
    ROUND(100.0 * SUM(CASE WHEN d_data_science THEN 1 ELSE 0 END) / COUNT(*), 2)
FROM literature_review
ORDER BY paper_count DESC;

-- ============================================================================
-- Helper View: Multi-Discipline Papers
-- ============================================================================

CREATE OR REPLACE VIEW v_multidisciplinary_papers AS
SELECT
    study_id,
    title,
    year,
    authors,
    (CAST(d_biology_health AS INTEGER) +
     CAST(d_behaviour_sensory AS INTEGER) +
     CAST(d_trophic_ecology AS INTEGER) +
     CAST(d_genetics_genomics AS INTEGER) +
     CAST(d_movement_spatial AS INTEGER) +
     CAST(d_fisheries_management AS INTEGER) +
     CAST(d_conservation_policy AS INTEGER) +
     CAST(d_data_science AS INTEGER)) AS discipline_count,
    d_biology_health,
    d_behaviour_sensory,
    d_trophic_ecology,
    d_genetics_genomics,
    d_movement_spatial,
    d_fisheries_management,
    d_conservation_policy,
    d_data_science
FROM literature_review
WHERE (CAST(d_biology_health AS INTEGER) +
       CAST(d_behaviour_sensory AS INTEGER) +
       CAST(d_trophic_ecology AS INTEGER) +
       CAST(d_genetics_genomics AS INTEGER) +
       CAST(d_movement_spatial AS INTEGER) +
       CAST(d_fisheries_management AS INTEGER) +
       CAST(d_conservation_policy AS INTEGER) +
       CAST(d_data_science AS INTEGER)) > 1
ORDER BY discipline_count DESC, year DESC;

-- ============================================================================
-- Comments & Documentation
-- ============================================================================

COMMENT ON COLUMN literature_review.d_biology_health IS 'Biology, Life History & Health: reproduction, growth, aging, stress, disease, endocrinology, physiology';
COMMENT ON COLUMN literature_review.d_behaviour_sensory IS 'Behaviour & Sensory Ecology: predation, vision, electroreception, olfaction, magnetoreception, social behavior, cognition';
COMMENT ON COLUMN literature_review.d_trophic_ecology IS 'Trophic & Community Ecology: stable isotopes, diet, food webs, trophic levels, energy flow, niche partitioning';
COMMENT ON COLUMN literature_review.d_genetics_genomics IS 'Genetics, Genomics & eDNA: population genetics, genomics, eDNA, phylogenetics, molecular ecology, conservation genetics';
COMMENT ON COLUMN literature_review.d_movement_spatial IS 'Movement, Space Use & Habitat Modeling: telemetry, satellite tracking, home range, SDMs, spatial ecology, migration, connectivity';
COMMENT ON COLUMN literature_review.d_fisheries_management IS 'Fisheries, Stock Assessment & Management: stock assessment, CPUE, bycatch, fishing mortality, harvest strategies';
COMMENT ON COLUMN literature_review.d_conservation_policy IS 'Conservation Policy & Human Dimensions: IUCN status, CITES, MPAs, policy, stakeholder engagement, ecosystem services';
COMMENT ON COLUMN literature_review.d_data_science IS 'Data Science & Integrative Methods: machine learning, Bayesian models, random forests, neural networks, AI, ensemble methods, GAMs';

-- ============================================================================
-- Usage Examples
-- ============================================================================

/*
-- Update a paper to classify it across multiple disciplines
UPDATE literature_review
SET
    d_movement_spatial = TRUE,
    d_genetics_genomics = TRUE,
    d_data_science = TRUE
WHERE study_id = 1;

-- Find all movement ecology papers
SELECT title, year, authors
FROM literature_review
WHERE d_movement_spatial = TRUE
ORDER BY year DESC;

-- Count papers by discipline
SELECT * FROM v_discipline_summary;

-- Find interdisciplinary papers (2+ disciplines)
SELECT * FROM v_multidisciplinary_papers LIMIT 10;

-- Find papers that combine movement + genetics
SELECT title, year
FROM literature_review
WHERE d_movement_spatial = TRUE
  AND d_genetics_genomics = TRUE;
*/
