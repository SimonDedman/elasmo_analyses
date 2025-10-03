-- ============================================================================
-- EEA 2025 Data Panel: Ocean Basin Columns
-- ============================================================================
--
-- Purpose: Add 9 major ocean basin + 66 sub-basin binary columns
--
-- Schema Version: 1.0
-- Created: 2025-10-02
-- Database: DuckDB
--
-- Dependencies: 01_create_core_table.sql
--
-- Design Rationale:
--   - Track geographic distribution of study locations
--   - Papers often cover multiple basins (comparative studies, migratory species)
--   - Binary columns enable multi-basin tracking
--   - Prefix 'b_' identifies major ocean basins
--   - Prefix 'sb_' identifies sub-basins (Large Marine Ecosystems)
--   - Hierarchical relationship: sub-basins belong to major basins
--   - Default FALSE for explicit missing data tracking
--
-- Sources:
--   - IHO (International Hydrographic Organization) Sea Areas for major basins
--   - NOAA Large Marine Ecosystems (LME) for sub-basins
--
-- ============================================================================

-- ============================================================================
-- Add Major Ocean Basin Binary Columns (9 basins)
-- ============================================================================

ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS b_north_atlantic BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS b_south_atlantic BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS b_north_pacific BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS b_south_pacific BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS b_indian_ocean BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS b_arctic_ocean BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS b_southern_ocean BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS b_mediterranean_sea BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS b_caribbean_sea BOOLEAN DEFAULT FALSE;

-- ============================================================================
-- Add Sub-Basin Binary Columns (66 Large Marine Ecosystems)
-- ============================================================================

-- North Atlantic LMEs (13)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_east_greenland_shelf BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_iceland_shelf BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_faroe_plateau BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_norwegian_shelf BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_north_sea BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_baltic_sea BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_celtic_biscay_shelf BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_iberian_coastal BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_newfoundland_labrador BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_scotian_shelf BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_northeast_us_shelf BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_southeast_us_shelf BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_gulf_of_mexico BOOLEAN DEFAULT FALSE;

-- South Atlantic LMEs (5)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_canary_current BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_guinea_current BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_benguela_current BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_patagonian_shelf BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_brazil_current BOOLEAN DEFAULT FALSE;

-- North Pacific LMEs (8)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_east_bering_sea BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_gulf_of_alaska BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_california_current BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_gulf_of_california BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_sea_of_japan BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_yellow_sea BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_east_china_sea BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_kuroshio_current BOOLEAN DEFAULT FALSE;

-- South Pacific LMEs (7)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_humboldt_current BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_east_australian_shelf BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_great_barrier_reef BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_new_zealand_shelf BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_west_central_pacific BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_pacific_coral_coast BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_south_china_sea BOOLEAN DEFAULT FALSE;

-- Indian Ocean LMEs (10)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_red_sea BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_arabian_sea BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_bay_of_bengal BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_gulf_of_thailand BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_sunda_shelf BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_west_australian_shelf BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_northwest_australian_shelf BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_agulhas_current BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_somali_coastal_current BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_seychelles_mauritius BOOLEAN DEFAULT FALSE;

-- Arctic Ocean LMEs (7)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_barents_sea BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_kara_sea BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_laptev_sea BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_east_siberian_sea BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_chukchi_sea BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_beaufort_sea BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_canadian_arctic BOOLEAN DEFAULT FALSE;

-- Southern Ocean LMEs (3)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_antarctic_peninsula BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_weddell_sea BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_ross_sea BOOLEAN DEFAULT FALSE;

-- Mediterranean Sea LMEs (5)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_western_mediterranean BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_adriatic_sea BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_aegean_sea BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_levantine_sea BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_black_sea BOOLEAN DEFAULT FALSE;

-- Caribbean Sea LMEs (8)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_gulf_of_panama BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_caribbean_central BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_caribbean_northeast BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_caribbean_southwest BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_bahamas BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_florida_keys BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_bermuda BOOLEAN DEFAULT FALSE;
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_azores BOOLEAN DEFAULT FALSE;

-- Total: 9 major basins + 66 sub-basins = 75 columns

-- ============================================================================
-- Indexes for Geographic Analysis
-- ============================================================================

-- Index major basins
CREATE INDEX IF NOT EXISTS idx_b_north_atlantic ON literature_review(b_north_atlantic) WHERE b_north_atlantic = TRUE;
CREATE INDEX IF NOT EXISTS idx_b_north_pacific ON literature_review(b_north_pacific) WHERE b_north_pacific = TRUE;
CREATE INDEX IF NOT EXISTS idx_b_indian_ocean ON literature_review(b_indian_ocean) WHERE b_indian_ocean = TRUE;
CREATE INDEX IF NOT EXISTS idx_b_mediterranean_sea ON literature_review(b_mediterranean_sea) WHERE b_mediterranean_sea = TRUE;
CREATE INDEX IF NOT EXISTS idx_b_caribbean_sea ON literature_review(b_caribbean_sea) WHERE b_caribbean_sea = TRUE;

-- Index frequently-studied sub-basins
CREATE INDEX IF NOT EXISTS idx_sb_gulf_of_mexico ON literature_review(sb_gulf_of_mexico) WHERE sb_gulf_of_mexico = TRUE;
CREATE INDEX IF NOT EXISTS idx_sb_california_current ON literature_review(sb_california_current) WHERE sb_california_current = TRUE;
CREATE INDEX IF NOT EXISTS idx_sb_great_barrier_reef ON literature_review(sb_great_barrier_reef) WHERE sb_great_barrier_reef = TRUE;
CREATE INDEX IF NOT EXISTS idx_sb_north_sea ON literature_review(sb_north_sea) WHERE sb_north_sea = TRUE;
CREATE INDEX IF NOT EXISTS idx_sb_south_china_sea ON literature_review(sb_south_china_sea) WHERE sb_south_china_sea = TRUE;

-- ============================================================================
-- Helper View: Basin Hierarchy Mapping
-- ============================================================================

CREATE OR REPLACE VIEW v_basin_hierarchy AS
SELECT 'North Atlantic' AS major_basin, 'East Greenland Shelf' AS sub_basin, 'sb_east_greenland_shelf' AS column_name
UNION ALL SELECT 'North Atlantic', 'Iceland Shelf', 'sb_iceland_shelf'
UNION ALL SELECT 'North Atlantic', 'Faroe Plateau', 'sb_faroe_plateau'
UNION ALL SELECT 'North Atlantic', 'Norwegian Shelf', 'sb_norwegian_shelf'
UNION ALL SELECT 'North Atlantic', 'North Sea', 'sb_north_sea'
UNION ALL SELECT 'North Atlantic', 'Baltic Sea', 'sb_baltic_sea'
UNION ALL SELECT 'North Atlantic', 'Celtic-Biscay Shelf', 'sb_celtic_biscay_shelf'
UNION ALL SELECT 'North Atlantic', 'Iberian Coastal', 'sb_iberian_coastal'
UNION ALL SELECT 'North Atlantic', 'Newfoundland-Labrador', 'sb_newfoundland_labrador'
UNION ALL SELECT 'North Atlantic', 'Scotian Shelf', 'sb_scotian_shelf'
UNION ALL SELECT 'North Atlantic', 'Northeast US Shelf', 'sb_northeast_us_shelf'
UNION ALL SELECT 'North Atlantic', 'Southeast US Shelf', 'sb_southeast_us_shelf'
UNION ALL SELECT 'North Atlantic', 'Gulf of Mexico', 'sb_gulf_of_mexico'
UNION ALL SELECT 'South Atlantic', 'Canary Current', 'sb_canary_current'
UNION ALL SELECT 'South Atlantic', 'Guinea Current', 'sb_guinea_current'
UNION ALL SELECT 'South Atlantic', 'Benguela Current', 'sb_benguela_current'
UNION ALL SELECT 'South Atlantic', 'Patagonian Shelf', 'sb_patagonian_shelf'
UNION ALL SELECT 'South Atlantic', 'Brazil Current', 'sb_brazil_current'
UNION ALL SELECT 'North Pacific', 'East Bering Sea', 'sb_east_bering_sea'
UNION ALL SELECT 'North Pacific', 'Gulf of Alaska', 'sb_gulf_of_alaska'
UNION ALL SELECT 'North Pacific', 'California Current', 'sb_california_current'
UNION ALL SELECT 'North Pacific', 'Gulf of California', 'sb_gulf_of_california'
UNION ALL SELECT 'North Pacific', 'Sea of Japan', 'sb_sea_of_japan'
UNION ALL SELECT 'North Pacific', 'Yellow Sea', 'sb_yellow_sea'
UNION ALL SELECT 'North Pacific', 'East China Sea', 'sb_east_china_sea'
UNION ALL SELECT 'North Pacific', 'Kuroshio Current', 'sb_kuroshio_current'
UNION ALL SELECT 'South Pacific', 'Humboldt Current', 'sb_humboldt_current'
UNION ALL SELECT 'South Pacific', 'East Australian Shelf', 'sb_east_australian_shelf'
UNION ALL SELECT 'South Pacific', 'Great Barrier Reef', 'sb_great_barrier_reef'
UNION ALL SELECT 'South Pacific', 'New Zealand Shelf', 'sb_new_zealand_shelf'
UNION ALL SELECT 'South Pacific', 'West Central Pacific', 'sb_west_central_pacific'
UNION ALL SELECT 'South Pacific', 'Pacific Coral Coast', 'sb_pacific_coral_coast'
UNION ALL SELECT 'South Pacific', 'South China Sea', 'sb_south_china_sea'
UNION ALL SELECT 'Indian Ocean', 'Red Sea', 'sb_red_sea'
UNION ALL SELECT 'Indian Ocean', 'Arabian Sea', 'sb_arabian_sea'
UNION ALL SELECT 'Indian Ocean', 'Bay of Bengal', 'sb_bay_of_bengal'
UNION ALL SELECT 'Indian Ocean', 'Gulf of Thailand', 'sb_gulf_of_thailand'
UNION ALL SELECT 'Indian Ocean', 'Sunda Shelf', 'sb_sunda_shelf'
UNION ALL SELECT 'Indian Ocean', 'West Australian Shelf', 'sb_west_australian_shelf'
UNION ALL SELECT 'Indian Ocean', 'Northwest Australian Shelf', 'sb_northwest_australian_shelf'
UNION ALL SELECT 'Indian Ocean', 'Agulhas Current', 'sb_agulhas_current'
UNION ALL SELECT 'Indian Ocean', 'Somali Coastal Current', 'sb_somali_coastal_current'
UNION ALL SELECT 'Indian Ocean', 'Seychelles-Mauritius', 'sb_seychelles_mauritius'
UNION ALL SELECT 'Arctic Ocean', 'Barents Sea', 'sb_barents_sea'
UNION ALL SELECT 'Arctic Ocean', 'Kara Sea', 'sb_kara_sea'
UNION ALL SELECT 'Arctic Ocean', 'Laptev Sea', 'sb_laptev_sea'
UNION ALL SELECT 'Arctic Ocean', 'East Siberian Sea', 'sb_east_siberian_sea'
UNION ALL SELECT 'Arctic Ocean', 'Chukchi Sea', 'sb_chukchi_sea'
UNION ALL SELECT 'Arctic Ocean', 'Beaufort Sea', 'sb_beaufort_sea'
UNION ALL SELECT 'Arctic Ocean', 'Canadian Arctic', 'sb_canadian_arctic'
UNION ALL SELECT 'Southern Ocean', 'Antarctic Peninsula', 'sb_antarctic_peninsula'
UNION ALL SELECT 'Southern Ocean', 'Weddell Sea', 'sb_weddell_sea'
UNION ALL SELECT 'Southern Ocean', 'Ross Sea', 'sb_ross_sea'
UNION ALL SELECT 'Mediterranean Sea', 'Western Mediterranean', 'sb_western_mediterranean'
UNION ALL SELECT 'Mediterranean Sea', 'Adriatic Sea', 'sb_adriatic_sea'
UNION ALL SELECT 'Mediterranean Sea', 'Aegean Sea', 'sb_aegean_sea'
UNION ALL SELECT 'Mediterranean Sea', 'Levantine Sea', 'sb_levantine_sea'
UNION ALL SELECT 'Mediterranean Sea', 'Black Sea', 'sb_black_sea'
UNION ALL SELECT 'Caribbean Sea', 'Gulf of Panama', 'sb_gulf_of_panama'
UNION ALL SELECT 'Caribbean Sea', 'Caribbean Central', 'sb_caribbean_central'
UNION ALL SELECT 'Caribbean Sea', 'Caribbean Northeast', 'sb_caribbean_northeast'
UNION ALL SELECT 'Caribbean Sea', 'Caribbean Southwest', 'sb_caribbean_southwest'
UNION ALL SELECT 'Caribbean Sea', 'Bahamas', 'sb_bahamas'
UNION ALL SELECT 'Caribbean Sea', 'Florida Keys', 'sb_florida_keys'
UNION ALL SELECT 'Caribbean Sea', 'Bermuda', 'sb_bermuda'
UNION ALL SELECT 'Caribbean Sea', 'Azores', 'sb_azores';

-- ============================================================================
-- Helper View: Basin Summary
-- ============================================================================

CREATE OR REPLACE VIEW v_basin_summary AS
SELECT
    'North Atlantic' AS basin,
    SUM(CASE WHEN b_north_atlantic THEN 1 ELSE 0 END) AS paper_count,
    ROUND(100.0 * SUM(CASE WHEN b_north_atlantic THEN 1 ELSE 0 END) / COUNT(*), 2) AS percentage
FROM literature_review
UNION ALL
SELECT 'South Atlantic',
    SUM(CASE WHEN b_south_atlantic THEN 1 ELSE 0 END),
    ROUND(100.0 * SUM(CASE WHEN b_south_atlantic THEN 1 ELSE 0 END) / COUNT(*), 2)
FROM literature_review
UNION ALL
SELECT 'North Pacific',
    SUM(CASE WHEN b_north_pacific THEN 1 ELSE 0 END),
    ROUND(100.0 * SUM(CASE WHEN b_north_pacific THEN 1 ELSE 0 END) / COUNT(*), 2)
FROM literature_review
UNION ALL
SELECT 'South Pacific',
    SUM(CASE WHEN b_south_pacific THEN 1 ELSE 0 END),
    ROUND(100.0 * SUM(CASE WHEN b_south_pacific THEN 1 ELSE 0 END) / COUNT(*), 2)
FROM literature_review
UNION ALL
SELECT 'Indian Ocean',
    SUM(CASE WHEN b_indian_ocean THEN 1 ELSE 0 END),
    ROUND(100.0 * SUM(CASE WHEN b_indian_ocean THEN 1 ELSE 0 END) / COUNT(*), 2)
FROM literature_review
UNION ALL
SELECT 'Arctic Ocean',
    SUM(CASE WHEN b_arctic_ocean THEN 1 ELSE 0 END),
    ROUND(100.0 * SUM(CASE WHEN b_arctic_ocean THEN 1 ELSE 0 END) / COUNT(*), 2)
FROM literature_review
UNION ALL
SELECT 'Southern Ocean',
    SUM(CASE WHEN b_southern_ocean THEN 1 ELSE 0 END),
    ROUND(100.0 * SUM(CASE WHEN b_southern_ocean THEN 1 ELSE 0 END) / COUNT(*), 2)
FROM literature_review
UNION ALL
SELECT 'Mediterranean Sea',
    SUM(CASE WHEN b_mediterranean_sea THEN 1 ELSE 0 END),
    ROUND(100.0 * SUM(CASE WHEN b_mediterranean_sea THEN 1 ELSE 0 END) / COUNT(*), 2)
FROM literature_review
UNION ALL
SELECT 'Caribbean Sea',
    SUM(CASE WHEN b_caribbean_sea THEN 1 ELSE 0 END),
    ROUND(100.0 * SUM(CASE WHEN b_caribbean_sea THEN 1 ELSE 0 END) / COUNT(*), 2)
FROM literature_review
ORDER BY paper_count DESC;

-- ============================================================================
-- Comments & Documentation
-- ============================================================================

COMMENT ON COLUMN literature_review.b_north_atlantic IS 'Major basin: North Atlantic Ocean';
COMMENT ON COLUMN literature_review.b_south_atlantic IS 'Major basin: South Atlantic Ocean';
COMMENT ON COLUMN literature_review.b_north_pacific IS 'Major basin: North Pacific Ocean';
COMMENT ON COLUMN literature_review.b_south_pacific IS 'Major basin: South Pacific Ocean';
COMMENT ON COLUMN literature_review.b_indian_ocean IS 'Major basin: Indian Ocean';
COMMENT ON COLUMN literature_review.b_arctic_ocean IS 'Major basin: Arctic Ocean';
COMMENT ON COLUMN literature_review.b_southern_ocean IS 'Major basin: Southern Ocean (Antarctic)';
COMMENT ON COLUMN literature_review.b_mediterranean_sea IS 'Major basin: Mediterranean Sea';
COMMENT ON COLUMN literature_review.b_caribbean_sea IS 'Major basin: Caribbean Sea';

-- Sub-basin comments (selected examples)
COMMENT ON COLUMN literature_review.sb_gulf_of_mexico IS 'Sub-basin (LME): Gulf of Mexico';
COMMENT ON COLUMN literature_review.sb_california_current IS 'Sub-basin (LME): California Current';
COMMENT ON COLUMN literature_review.sb_great_barrier_reef IS 'Sub-basin (LME): Great Barrier Reef';

-- ============================================================================
-- Usage Examples
-- ============================================================================

/*
-- Mark a paper covering multiple basins and sub-basins
UPDATE literature_review
SET
    b_north_atlantic = TRUE,
    sb_gulf_of_mexico = TRUE,
    sb_caribbean_central = TRUE
WHERE study_id = 1;

-- Find all Gulf of Mexico papers
SELECT title, year
FROM literature_review
WHERE sb_gulf_of_mexico = TRUE;

-- Count papers by major basin
SELECT * FROM v_basin_summary;

-- Find papers covering multiple major basins
SELECT title, year,
    (CAST(b_north_atlantic AS INTEGER) + CAST(b_north_pacific AS INTEGER) +
     CAST(b_indian_ocean AS INTEGER) + CAST(b_caribbean_sea AS INTEGER)) AS basin_count
FROM literature_review
WHERE (CAST(b_north_atlantic AS INTEGER) + CAST(b_north_pacific AS INTEGER) +
       CAST(b_indian_ocean AS INTEGER) + CAST(b_caribbean_sea AS INTEGER)) >= 2
ORDER BY basin_count DESC;

-- Lookup sub-basin to major basin mapping
SELECT * FROM v_basin_hierarchy WHERE major_basin = 'North Atlantic';
*/
