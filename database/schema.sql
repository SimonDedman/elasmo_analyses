-- ==============================================================================
-- Elasmobranch Research Technique Taxonomy Database Schema
-- ==============================================================================
-- Purpose: Master database for literature review automation via Shark-References
-- Created: 2025-10-13
-- Database: technique_taxonomy.db
-- ==============================================================================

-- ==============================================================================
-- Core Taxonomy Tables
-- ==============================================================================

CREATE TABLE IF NOT EXISTS disciplines (
    discipline_id INTEGER PRIMARY KEY AUTOINCREMENT,
    discipline_name VARCHAR(100) NOT NULL UNIQUE,
    discipline_code VARCHAR(20) NOT NULL UNIQUE,
    description TEXT,
    sort_order INTEGER,
    expert_lead VARCHAR(100),
    expert_email VARCHAR(100),
    created_date DATE DEFAULT CURRENT_DATE,
    modified_date DATE DEFAULT CURRENT_DATE
);

CREATE TABLE IF NOT EXISTS categories (
    category_id INTEGER PRIMARY KEY AUTOINCREMENT,
    discipline_id INTEGER NOT NULL,
    category_name VARCHAR(150) NOT NULL,
    category_description TEXT,
    is_cross_cutting BOOLEAN DEFAULT 0,
    sort_order INTEGER,
    FOREIGN KEY (discipline_id) REFERENCES disciplines(discipline_id),
    UNIQUE (discipline_id, category_name)
);

CREATE TABLE IF NOT EXISTS techniques (
    technique_id INTEGER PRIMARY KEY AUTOINCREMENT,
    technique_name VARCHAR(200) NOT NULL,
    technique_name_normalized VARCHAR(200),
    parent_category_id INTEGER,
    is_parent BOOLEAN DEFAULT 1,
    parent_technique_id INTEGER,
    description TEXT,
    synonyms TEXT,
    first_elasmobranch_paper TEXT,
    methodological_notes TEXT,
    inclusion_criteria TEXT,
    exclusion_criteria TEXT,
    boundary_cases TEXT,
    data_source VARCHAR(50), -- 'EEA', 'literature', 'expert', 'planned'
    created_date DATE DEFAULT CURRENT_DATE,
    modified_date DATE DEFAULT CURRENT_DATE,
    FOREIGN KEY (parent_category_id) REFERENCES categories(category_id),
    FOREIGN KEY (parent_technique_id) REFERENCES techniques(technique_id)
);

CREATE TABLE IF NOT EXISTS technique_categories (
    technique_id INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    is_primary BOOLEAN DEFAULT 0,
    notes TEXT,
    PRIMARY KEY (technique_id, category_id),
    FOREIGN KEY (technique_id) REFERENCES techniques(technique_id),
    FOREIGN KEY (category_id) REFERENCES categories(category_id)
);

-- ==============================================================================
-- Search Term Management
-- ==============================================================================

CREATE TABLE IF NOT EXISTS search_terms (
    search_term_id INTEGER PRIMARY KEY AUTOINCREMENT,
    search_query VARCHAR(500) NOT NULL,
    query_description TEXT,
    target_level VARCHAR(20),
    technique_id INTEGER,
    category_id INTEGER,
    discipline_id INTEGER,
    operator_type VARCHAR(20),
    expected_specificity VARCHAR(20),
    notes TEXT,
    is_validated BOOLEAN DEFAULT 0,
    validation_date DATE,
    validation_result_count INTEGER,
    created_date DATE DEFAULT CURRENT_DATE,
    FOREIGN KEY (technique_id) REFERENCES techniques(technique_id),
    FOREIGN KEY (category_id) REFERENCES categories(category_id),
    FOREIGN KEY (discipline_id) REFERENCES disciplines(discipline_id)
);

CREATE TABLE IF NOT EXISTS search_term_alternatives (
    alternative_id INTEGER PRIMARY KEY AUTOINCREMENT,
    primary_search_term_id INTEGER NOT NULL,
    alternative_query VARCHAR(500) NOT NULL,
    reason VARCHAR(50),
    notes TEXT,
    FOREIGN KEY (primary_search_term_id) REFERENCES search_terms(search_term_id)
);

-- ==============================================================================
-- Evidence Tables
-- ==============================================================================

CREATE TABLE IF NOT EXISTS eea_evidence (
    evidence_id INTEGER PRIMARY KEY AUTOINCREMENT,
    technique_id INTEGER NOT NULL,
    discipline_name VARCHAR(100),
    presentation_count INTEGER DEFAULT 1,
    source VARCHAR(50),
    presentation_ids TEXT,
    example_presentation_title TEXT,
    notes TEXT,
    FOREIGN KEY (technique_id) REFERENCES techniques(technique_id)
);

CREATE TABLE IF NOT EXISTS literature_searches (
    search_id INTEGER PRIMARY KEY AUTOINCREMENT,
    search_term_id INTEGER NOT NULL,
    search_date DATE DEFAULT CURRENT_DATE,
    result_count INTEGER,
    year_from INTEGER,
    year_to INTEGER,
    csv_filename VARCHAR(255),
    search_duration_seconds REAL,
    status VARCHAR(50),
    error_message TEXT,
    FOREIGN KEY (search_term_id) REFERENCES search_terms(search_term_id)
);

CREATE TABLE IF NOT EXISTS literature_papers (
    paper_id INTEGER PRIMARY KEY AUTOINCREMENT,
    search_id INTEGER NOT NULL,
    shark_ref_id VARCHAR(100),
    authors TEXT,
    year INTEGER,
    title TEXT,
    journal VARCHAR(255),
    volume VARCHAR(50),
    issue VARCHAR(50),
    pages VARCHAR(50),
    doi VARCHAR(100),
    abstract TEXT,
    keywords TEXT,
    citation_count INTEGER,
    scholar_url VARCHAR(500),
    is_duplicate BOOLEAN DEFAULT 0,
    duplicate_of_paper_id INTEGER,
    date_retrieved DATE DEFAULT CURRENT_DATE,
    FOREIGN KEY (search_id) REFERENCES literature_searches(search_id),
    FOREIGN KEY (duplicate_of_paper_id) REFERENCES literature_papers(paper_id)
);

CREATE TABLE IF NOT EXISTS paper_techniques (
    paper_id INTEGER NOT NULL,
    technique_id INTEGER NOT NULL,
    confidence VARCHAR(20),
    context TEXT,
    PRIMARY KEY (paper_id, technique_id),
    FOREIGN KEY (paper_id) REFERENCES literature_papers(paper_id),
    FOREIGN KEY (technique_id) REFERENCES techniques(technique_id)
);

-- ==============================================================================
-- Temporal Trends
-- ==============================================================================

CREATE TABLE IF NOT EXISTS technique_trends (
    trend_id INTEGER PRIMARY KEY AUTOINCREMENT,
    technique_id INTEGER NOT NULL,
    year INTEGER NOT NULL,
    paper_count INTEGER DEFAULT 0,
    citation_sum INTEGER DEFAULT 0,
    trend_category VARCHAR(50),
    notes TEXT,
    FOREIGN KEY (technique_id) REFERENCES techniques(technique_id),
    UNIQUE (technique_id, year)
);

-- ==============================================================================
-- Expert Annotations
-- ==============================================================================

CREATE TABLE IF NOT EXISTS expert_reviews (
    review_id INTEGER PRIMARY KEY AUTOINCREMENT,
    technique_id INTEGER,
    paper_id INTEGER,
    expert_name VARCHAR(100) NOT NULL,
    review_date DATE DEFAULT CURRENT_DATE,
    relevance_rating INTEGER CHECK (relevance_rating BETWEEN 1 AND 5),
    methodological_quality INTEGER CHECK (methodological_quality BETWEEN 1 AND 5),
    innovation_score INTEGER CHECK (innovation_score BETWEEN 1 AND 5),
    comments TEXT,
    is_recommended_reading BOOLEAN DEFAULT 0,
    is_seminal_paper BOOLEAN DEFAULT 0,
    FOREIGN KEY (technique_id) REFERENCES techniques(technique_id),
    FOREIGN KEY (paper_id) REFERENCES literature_papers(paper_id)
);

-- ==============================================================================
-- Indexes for Performance
-- ==============================================================================

CREATE INDEX IF NOT EXISTS idx_techniques_parent ON techniques(parent_technique_id);
CREATE INDEX IF NOT EXISTS idx_techniques_category ON techniques(parent_category_id);
CREATE INDEX IF NOT EXISTS idx_techniques_normalized ON techniques(technique_name_normalized);
CREATE INDEX IF NOT EXISTS idx_search_terms_technique ON search_terms(technique_id);
CREATE INDEX IF NOT EXISTS idx_search_terms_discipline ON search_terms(discipline_id);
CREATE INDEX IF NOT EXISTS idx_literature_papers_doi ON literature_papers(doi);
CREATE INDEX IF NOT EXISTS idx_literature_papers_year ON literature_papers(year);
CREATE INDEX IF NOT EXISTS idx_literature_papers_sharkref ON literature_papers(shark_ref_id);
CREATE INDEX IF NOT EXISTS idx_eea_evidence_technique ON eea_evidence(technique_id);
CREATE INDEX IF NOT EXISTS idx_paper_techniques_paper ON paper_techniques(paper_id);
CREATE INDEX IF NOT EXISTS idx_paper_techniques_technique ON paper_techniques(technique_id);
CREATE INDEX IF NOT EXISTS idx_technique_trends_technique_year ON technique_trends(technique_id, year);

-- ==============================================================================
-- Views for Common Queries
-- ==============================================================================

CREATE VIEW IF NOT EXISTS v_technique_hierarchy AS
SELECT
    d.discipline_name,
    d.discipline_code,
    c.category_name,
    t.technique_name,
    t.technique_id,
    t.is_parent,
    pt.technique_name AS parent_technique_name,
    t.description,
    t.synonyms,
    t.data_source
FROM techniques t
JOIN categories c ON t.parent_category_id = c.category_id
JOIN disciplines d ON c.discipline_id = d.discipline_id
LEFT JOIN techniques pt ON t.parent_technique_id = pt.technique_id
ORDER BY d.sort_order, c.sort_order, t.is_parent DESC, t.technique_name;

CREATE VIEW IF NOT EXISTS v_technique_evidence_summary AS
SELECT
    t.technique_name,
    t.data_source,
    d.discipline_name,
    c.category_name,
    COALESCE(e.presentation_count, 0) AS eea_presentations,
    e.source AS eea_source,
    COUNT(DISTINCT st.search_term_id) AS search_terms_defined,
    COUNT(DISTINCT ls.search_id) AS literature_searches_run,
    SUM(COALESCE(ls.result_count, 0)) AS total_papers_found
FROM techniques t
JOIN categories c ON t.parent_category_id = c.category_id
JOIN disciplines d ON c.discipline_id = d.discipline_id
LEFT JOIN eea_evidence e ON t.technique_id = e.technique_id
LEFT JOIN search_terms st ON t.technique_id = st.technique_id
LEFT JOIN literature_searches ls ON st.search_term_id = ls.search_term_id
GROUP BY t.technique_id, t.technique_name, t.data_source, d.discipline_name, c.category_name, e.presentation_count, e.source
ORDER BY d.discipline_name, eea_presentations DESC;

CREATE VIEW IF NOT EXISTS v_search_terms_for_automation AS
SELECT
    st.search_term_id,
    st.search_query,
    st.query_description,
    d.discipline_name,
    d.discipline_code,
    c.category_name,
    t.technique_name,
    st.operator_type,
    st.expected_specificity,
    st.is_validated,
    st.validation_result_count,
    REPLACE(REPLACE(LOWER(st.search_query), ' ', '_'), '+', '') || '_' || strftime('%Y%m%d', 'now') || '.csv' AS suggested_filename
FROM search_terms st
LEFT JOIN techniques t ON st.technique_id = t.technique_id
LEFT JOIN categories c ON st.category_id = c.category_id
LEFT JOIN disciplines d ON st.discipline_id = d.discipline_id
WHERE st.is_validated = 1 OR st.is_validated IS NULL
ORDER BY d.sort_order, c.sort_order, t.technique_name;

CREATE VIEW IF NOT EXISTS v_panelist_review_export AS
SELECT
    d.discipline_name,
    d.discipline_code,
    c.category_name,
    t.technique_name,
    t.is_parent,
    pt.technique_name AS parent_technique,
    t.description,
    t.synonyms,
    t.data_source,
    COALESCE(e.presentation_count, 0) AS eea_count,
    GROUP_CONCAT(DISTINCT st.search_query, '; ') AS search_terms,
    t.inclusion_criteria,
    t.exclusion_criteria,
    t.boundary_cases,
    t.technique_id
FROM techniques t
JOIN categories c ON t.parent_category_id = c.category_id
JOIN disciplines d ON c.discipline_id = d.discipline_id
LEFT JOIN techniques pt ON t.parent_technique_id = pt.technique_id
LEFT JOIN eea_evidence e ON t.technique_id = e.technique_id
LEFT JOIN search_terms st ON t.technique_id = st.technique_id
GROUP BY t.technique_id
ORDER BY d.sort_order, c.sort_order, t.is_parent DESC, t.technique_name;
