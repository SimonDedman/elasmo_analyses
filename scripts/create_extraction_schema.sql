-- Database Schema for PDF Technique Extraction with Researcher Scaffolding
-- Creates tables in database/technique_taxonomy.db

-- ============================================================================
-- RESEARCHER TABLES
-- ============================================================================

-- Core researcher information
CREATE TABLE IF NOT EXISTS researchers (
    researcher_id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT,
    surname TEXT NOT NULL,
    initials TEXT,
    name_variants TEXT,  -- JSON array of name variations
    institution_current TEXT,
    country TEXT,
    orcid TEXT UNIQUE,
    first_paper_year INTEGER,
    last_paper_year INTEGER,
    total_papers INTEGER DEFAULT 0,
    lead_author_papers INTEGER DEFAULT 0,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_researchers_surname ON researchers(surname);
CREATE INDEX IF NOT EXISTS idx_researchers_orcid ON researchers(orcid);

-- ============================================================================
-- PAPER-AUTHOR RELATIONSHIPS
-- ============================================================================

-- Links papers to researchers
CREATE TABLE IF NOT EXISTS paper_authors (
    paper_author_id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id TEXT NOT NULL,
    researcher_id INTEGER NOT NULL,
    author_position INTEGER,  -- 1=first author, 2=second, etc.
    is_corresponding BOOLEAN DEFAULT 0,
    affiliation TEXT,
    year INTEGER,
    FOREIGN KEY (researcher_id) REFERENCES researchers(researcher_id),
    UNIQUE(paper_id, researcher_id)
);

CREATE INDEX IF NOT EXISTS idx_paper_authors_paper ON paper_authors(paper_id);
CREATE INDEX IF NOT EXISTS idx_paper_authors_researcher ON paper_authors(researcher_id);
CREATE INDEX IF NOT EXISTS idx_paper_authors_year ON paper_authors(year);
CREATE INDEX IF NOT EXISTS idx_paper_authors_position ON paper_authors(author_position);

-- ============================================================================
-- RESEARCHER-TECHNIQUE RELATIONSHIPS
-- ============================================================================

-- Tracks which techniques each researcher has used
CREATE TABLE IF NOT EXISTS researcher_techniques (
    researcher_technique_id INTEGER PRIMARY KEY AUTOINCREMENT,
    researcher_id INTEGER NOT NULL,
    technique_id INTEGER NOT NULL,
    paper_count INTEGER DEFAULT 0,
    first_used_year INTEGER,
    last_used_year INTEGER,
    FOREIGN KEY (researcher_id) REFERENCES researchers(researcher_id),
    FOREIGN KEY (technique_id) REFERENCES techniques(technique_id),
    UNIQUE(researcher_id, technique_id)
);

CREATE INDEX IF NOT EXISTS idx_researcher_techniques_researcher ON researcher_techniques(researcher_id);
CREATE INDEX IF NOT EXISTS idx_researcher_techniques_technique ON researcher_techniques(technique_id);

-- ============================================================================
-- RESEARCHER-DISCIPLINE RELATIONSHIPS
-- ============================================================================

-- Tracks which disciplines each researcher works in
CREATE TABLE IF NOT EXISTS researcher_disciplines (
    researcher_discipline_id INTEGER PRIMARY KEY AUTOINCREMENT,
    researcher_id INTEGER NOT NULL,
    discipline_code TEXT NOT NULL,
    discipline_name TEXT,
    paper_count INTEGER DEFAULT 0,
    is_primary_discipline BOOLEAN DEFAULT 0,
    FOREIGN KEY (researcher_id) REFERENCES researchers(researcher_id),
    FOREIGN KEY (discipline_code) REFERENCES disciplines(discipline_code),
    UNIQUE(researcher_id, discipline_code)
);

CREATE INDEX IF NOT EXISTS idx_researcher_disciplines_researcher ON researcher_disciplines(researcher_id);
CREATE INDEX IF NOT EXISTS idx_researcher_disciplines_discipline ON researcher_disciplines(discipline_code);

-- ============================================================================
-- COLLABORATION NETWORK
-- ============================================================================

-- Tracks co-authorship relationships
CREATE TABLE IF NOT EXISTS collaborations (
    collaboration_id INTEGER PRIMARY KEY AUTOINCREMENT,
    researcher_1_id INTEGER NOT NULL,
    researcher_2_id INTEGER NOT NULL,
    collaboration_count INTEGER DEFAULT 0,
    first_collaboration_year INTEGER,
    last_collaboration_year INTEGER,
    FOREIGN KEY (researcher_1_id) REFERENCES researchers(researcher_id),
    FOREIGN KEY (researcher_2_id) REFERENCES researchers(researcher_id),
    UNIQUE(researcher_1_id, researcher_2_id),
    CHECK(researcher_1_id < researcher_2_id)  -- Prevent duplicates (A-B vs B-A)
);

CREATE INDEX IF NOT EXISTS idx_collaborations_r1 ON collaborations(researcher_1_id);
CREATE INDEX IF NOT EXISTS idx_collaborations_r2 ON collaborations(researcher_2_id);

-- ============================================================================
-- INSTITUTIONS (for future use)
-- ============================================================================

CREATE TABLE IF NOT EXISTS institutions (
    institution_id INTEGER PRIMARY KEY AUTOINCREMENT,
    institution_name TEXT NOT NULL UNIQUE,
    institution_name_normalized TEXT,
    country TEXT,
    city TEXT,
    latitude REAL,
    longitude REAL,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_institutions_country ON institutions(country);
CREATE INDEX IF NOT EXISTS idx_institutions_name_norm ON institutions(institution_name_normalized);

-- ============================================================================
-- PAPER-DISCIPLINE RELATIONSHIPS
-- ============================================================================

-- Tracks which disciplines each paper belongs to (including cross-cutting)
CREATE TABLE IF NOT EXISTS paper_disciplines (
    paper_discipline_id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id TEXT NOT NULL,
    year INTEGER,
    discipline_code TEXT NOT NULL,
    discipline_name TEXT,
    assignment_type TEXT,  -- 'primary', 'cross_cutting', 'mixed'
    technique_count INTEGER DEFAULT 0,
    is_primary_only BOOLEAN DEFAULT 0,
    is_data_only BOOLEAN DEFAULT 0,
    FOREIGN KEY (discipline_code) REFERENCES disciplines(discipline_code),
    UNIQUE(paper_id, discipline_code)
);

CREATE INDEX IF NOT EXISTS idx_paper_disciplines_paper ON paper_disciplines(paper_id);
CREATE INDEX IF NOT EXISTS idx_paper_disciplines_discipline ON paper_disciplines(discipline_code);
CREATE INDEX IF NOT EXISTS idx_paper_disciplines_year ON paper_disciplines(year);
CREATE INDEX IF NOT EXISTS idx_paper_disciplines_type ON paper_disciplines(assignment_type);

-- ============================================================================
-- EXTRACTION LOG
-- ============================================================================

-- Tracks processing status for each PDF
CREATE TABLE IF NOT EXISTS extraction_log (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id TEXT NOT NULL UNIQUE,
    paper_path TEXT,
    status TEXT,  -- 'success', 'failed', 'partial'
    techniques_found INTEGER DEFAULT 0,
    text_extracted_length INTEGER,
    processing_time_sec REAL,
    error_message TEXT,
    extraction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_extraction_log_status ON extraction_log(status);
CREATE INDEX IF NOT EXISTS idx_extraction_log_date ON extraction_log(extraction_date);

-- ============================================================================
-- RESEARCHER METRICS (calculated/cached)
-- ============================================================================

-- Pre-calculated metrics for common time windows
CREATE TABLE IF NOT EXISTS researcher_metrics (
    metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
    researcher_id INTEGER NOT NULL,
    metric_year INTEGER,  -- Current year for the metric calculation
    papers_1y INTEGER DEFAULT 0,
    papers_3y INTEGER DEFAULT 0,
    papers_5y INTEGER DEFAULT 0,
    papers_10y INTEGER DEFAULT 0,
    papers_all_time INTEGER DEFAULT 0,
    lead_author_1y INTEGER DEFAULT 0,
    lead_author_3y INTEGER DEFAULT 0,
    lead_author_5y INTEGER DEFAULT 0,
    lead_author_10y INTEGER DEFAULT 0,
    lead_author_all_time INTEGER DEFAULT 0,
    unique_collaborators INTEGER DEFAULT 0,
    unique_techniques INTEGER DEFAULT 0,
    technique_diversity_score REAL,  -- Shannon diversity or similar
    primary_discipline TEXT,
    h_index_estimate INTEGER DEFAULT 0,
    calculated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (researcher_id) REFERENCES researchers(researcher_id),
    UNIQUE(researcher_id, metric_year)
);

CREATE INDEX IF NOT EXISTS idx_researcher_metrics_researcher ON researcher_metrics(researcher_id);
CREATE INDEX IF NOT EXISTS idx_researcher_metrics_year ON researcher_metrics(metric_year);
