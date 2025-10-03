-- ============================================================================
-- EEA 2025 Data Panel: Superorder Columns
-- ============================================================================
--
-- Purpose: Add 2 binary superorder columns for high-level taxonomic classification
--
-- Schema Version: 1.0
-- Created: 2025-10-02
-- Database: DuckDB
--
-- Dependencies: 01_create_core_table.sql
--
-- Design Rationale:
--   - High-level taxonomic filtering (sharks vs rays/skates)
--   - Papers often focus on one superorder or both
--   - Binary columns enable multi-superorder tracking
--   - Prefix 'so_' identifies superorder columns
--   - Default FALSE for explicit missing data tracking
--
-- Taxonomy:
--   - Selachimorpha: True sharks (~500 species)
--   - Batoidea: Rays, skates, sawfish (~650 species)
--   - Note: Chimaeras (Holocephali) are a separate subclass, not included here
--
-- ============================================================================

-- ============================================================================
-- Add Superorder Binary Columns
-- ============================================================================

ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS so_selachimorpha BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS so_batoidea BOOLEAN DEFAULT FALSE;

-- ============================================================================
-- Indexes for Taxonomic Queries
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_so_selachimorpha ON literature_review(so_selachimorpha) WHERE so_selachimorpha = TRUE;
CREATE INDEX IF NOT EXISTS idx_so_batoidea ON literature_review(so_batoidea) WHERE so_batoidea = TRUE;

-- ============================================================================
-- Helper View: Superorder Summary
-- ============================================================================

CREATE OR REPLACE VIEW v_superorder_summary AS
SELECT
    'Selachimorpha (Sharks)' AS superorder,
    'so_selachimorpha' AS column_name,
    SUM(CASE WHEN so_selachimorpha THEN 1 ELSE 0 END) AS paper_count,
    ROUND(100.0 * SUM(CASE WHEN so_selachimorpha THEN 1 ELSE 0 END) / COUNT(*), 2) AS percentage
FROM literature_review
UNION ALL
SELECT
    'Batoidea (Rays/Skates)',
    'so_batoidea',
    SUM(CASE WHEN so_batoidea THEN 1 ELSE 0 END),
    ROUND(100.0 * SUM(CASE WHEN so_batoidea THEN 1 ELSE 0 END) / COUNT(*), 2)
FROM literature_review
ORDER BY paper_count DESC;

-- ============================================================================
-- Helper View: Multi-Superorder Papers
-- ============================================================================

CREATE OR REPLACE VIEW v_multi_superorder_papers AS
SELECT
    study_id,
    title,
    year,
    authors,
    so_selachimorpha,
    so_batoidea
FROM literature_review
WHERE so_selachimorpha = TRUE AND so_batoidea = TRUE
ORDER BY year DESC;

-- ============================================================================
-- Comments & Documentation
-- ============================================================================

COMMENT ON COLUMN literature_review.so_selachimorpha IS 'Superorder: Selachimorpha (true sharks, ~500 species)';
COMMENT ON COLUMN literature_review.so_batoidea IS 'Superorder: Batoidea (rays, skates, sawfish, ~650 species)';

-- ============================================================================
-- Usage Examples
-- ============================================================================

/*
-- Mark a paper as focusing on sharks
UPDATE literature_review
SET so_selachimorpha = TRUE
WHERE study_id = 1;

-- Mark a comparative paper (sharks + rays)
UPDATE literature_review
SET
    so_selachimorpha = TRUE,
    so_batoidea = TRUE
WHERE study_id = 2;

-- Find all shark-only papers
SELECT title, year
FROM literature_review
WHERE so_selachimorpha = TRUE
  AND so_batoidea = FALSE;

-- Find all ray-only papers
SELECT title, year
FROM literature_review
WHERE so_batoidea = TRUE
  AND so_selachimorpha = FALSE;

-- Find comparative papers (both superorders)
SELECT * FROM v_multi_superorder_papers;

-- Count papers by superorder
SELECT * FROM v_superorder_summary;

-- Compare discipline focus between sharks and rays
SELECT
    CASE
        WHEN so_selachimorpha AND NOT so_batoidea THEN 'Sharks only'
        WHEN so_batoidea AND NOT so_selachimorpha THEN 'Rays only'
        WHEN so_selachimorpha AND so_batoidea THEN 'Both'
        ELSE 'Neither'
    END AS taxon_group,
    SUM(CASE WHEN d_movement_spatial THEN 1 ELSE 0 END) AS movement_papers,
    SUM(CASE WHEN d_genetics_genomics THEN 1 ELSE 0 END) AS genetics_papers,
    SUM(CASE WHEN d_fisheries_management THEN 1 ELSE 0 END) AS fisheries_papers
FROM literature_review
GROUP BY taxon_group;
*/
