-- ============================================================================
-- EEA 2025 Data Panel: Core Literature Review Table
-- ============================================================================
--
-- Purpose: Create the main literature review table with core metadata fields
--
-- Schema Version: 1.0
-- Created: 2025-10-02
-- Database: DuckDB
--
-- Dependencies: None
--
-- ============================================================================

CREATE TABLE IF NOT EXISTS literature_review (
    -- ========================================================================
    -- Primary Key & Audit Trail
    -- ========================================================================
    study_id INTEGER PRIMARY KEY,
    reviewer VARCHAR(100) NOT NULL,
    review_date DATE NOT NULL DEFAULT CURRENT_DATE,

    -- ========================================================================
    -- Bibliographic Metadata
    -- ========================================================================
    authors TEXT NOT NULL,
    year INTEGER CHECK (year >= 1800 AND year <= 2100),
    title TEXT NOT NULL,
    journal VARCHAR(255),
    volume VARCHAR(50),
    issue VARCHAR(50),
    pages VARCHAR(50),
    doi VARCHAR(100) UNIQUE,
    url TEXT,
    abstract TEXT,
    keywords TEXT,

    -- ========================================================================
    -- Study Classification
    -- ========================================================================
    study_type VARCHAR(20) CHECK (study_type IN ('Primary', 'Systematic Review', 'Meta-analysis')),
    open_access BOOLEAN DEFAULT FALSE,

    -- ========================================================================
    -- External Database References
    -- ========================================================================
    shark_refs_id VARCHAR(100) UNIQUE,
    semantic_scholar_id VARCHAR(100),
    citation_count INTEGER DEFAULT 0,

    -- ========================================================================
    -- Geographic Context (Text - Binary Columns Added Later)
    -- ========================================================================
    study_region_text TEXT,  -- Free text for complex geographic descriptions

    -- ========================================================================
    -- Taxonomic Context (Text - Binary Columns Added Later)
    -- ========================================================================
    species_list_text TEXT,  -- Free text for species mentioned

    -- ========================================================================
    -- Notes & Quality Assessment
    -- ========================================================================
    review_notes TEXT,
    data_quality VARCHAR(20) CHECK (data_quality IN ('High', 'Medium', 'Low', NULL)),

    -- ========================================================================
    -- Timestamps
    -- ========================================================================
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- Indexes for Performance
-- ============================================================================

-- Primary search patterns
CREATE INDEX IF NOT EXISTS idx_year ON literature_review(year);
CREATE INDEX IF NOT EXISTS idx_reviewer ON literature_review(reviewer);
CREATE INDEX IF NOT EXISTS idx_study_type ON literature_review(study_type);

-- External IDs
CREATE INDEX IF NOT EXISTS idx_doi ON literature_review(doi);
CREATE INDEX IF NOT EXISTS idx_shark_refs_id ON literature_review(shark_refs_id);

-- Full-text search preparation (DuckDB FTS extension)
-- Note: Actual FTS indexes created after data population
-- PRAGMA create_fts_index('literature_review', 'study_id', 'title', 'abstract', 'keywords');

-- ============================================================================
-- Triggers for Auto-Update Timestamps
-- ============================================================================

-- DuckDB doesn't support triggers in the same way as PostgreSQL
-- Use application-level logic to update `updated_at` timestamp
-- Or manual UPDATE queries when modifying records

-- ============================================================================
-- Comments & Documentation
-- ============================================================================

COMMENT ON TABLE literature_review IS 'Main literature review table for EEA 2025 Data Panel project. Tracks chondrichthyan research papers with comprehensive metadata, discipline classification, and analytical method categorization.';

-- Column documentation
COMMENT ON COLUMN literature_review.study_id IS 'Unique identifier for each study (auto-incrementing)';
COMMENT ON COLUMN literature_review.reviewer IS 'Name of person who reviewed/entered this study';
COMMENT ON COLUMN literature_review.review_date IS 'Date when this study was reviewed/entered';
COMMENT ON COLUMN literature_review.doi IS 'Digital Object Identifier (unique constraint)';
COMMENT ON COLUMN literature_review.study_type IS 'Classification: Primary research, Systematic Review, or Meta-analysis';
COMMENT ON COLUMN literature_review.shark_refs_id IS 'ID from Shark-References database';
COMMENT ON COLUMN literature_review.study_region_text IS 'Free-text geographic description (binary columns added in separate schema)';
COMMENT ON COLUMN literature_review.species_list_text IS 'Free-text species list (binary columns added in separate schema)';
COMMENT ON COLUMN literature_review.data_quality IS 'Reviewer assessment of data quality/reliability';

-- ============================================================================
-- Usage Examples
-- ============================================================================

/*
-- Insert a new study
INSERT INTO literature_review (
    reviewer, authors, year, title, journal, doi, study_type
) VALUES (
    'Simon Dedman',
    'Dedman S, Officer R, Brophy D, Clarke M, Reid DG',
    2015,
    'Modelling abundance hotspots for data-poor Irish Sea rays',
    'Ecological Modelling',
    '10.1016/j.ecolmodel.2015.06.007',
    'Primary'
);

-- Query recent papers
SELECT year, title, authors
FROM literature_review
WHERE year >= 2020
ORDER BY year DESC;

-- Find papers by reviewer
SELECT COUNT(*) as reviewed_count, reviewer
FROM literature_review
GROUP BY reviewer
ORDER BY reviewed_count DESC;
*/
