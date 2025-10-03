-- ============================================================================
-- EEA 2025 Data Panel: Author Institution Nation Columns
-- ============================================================================
--
-- Purpose: Add 197 binary columns for author institutional affiliations by country
--
-- Schema Version: 1.0
-- Created: 2025-10-02
-- Database: DuckDB
--
-- Dependencies: 01_create_core_table.sql
--
-- Design Rationale:
--   - Track geographic distribution of research efforts
--   - Papers often have authors from multiple countries (international collaborations)
--   - Binary columns enable multi-country tracking
--   - Prefix 'auth_' identifies author nation columns
--   - ISO 3166-1 alpha-2 codes used (lowercase for SQL compatibility)
--   - Default FALSE for explicit missing data tracking
--
-- Source: ISO 3166-1 standard (197 UN member states + observer states)
--
-- ============================================================================

-- ============================================================================
-- Add Author Nation Binary Columns (ISO 3166-1 Alpha-2)
-- ============================================================================

-- Africa (54 countries)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_dz BOOLEAN DEFAULT FALSE; -- Algeria
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_ao BOOLEAN DEFAULT FALSE; -- Angola
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_bj BOOLEAN DEFAULT FALSE; -- Benin
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_bw BOOLEAN DEFAULT FALSE; -- Botswana
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_bf BOOLEAN DEFAULT FALSE; -- Burkina Faso
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_bi BOOLEAN DEFAULT FALSE; -- Burundi
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_cv BOOLEAN DEFAULT FALSE; -- Cabo Verde
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_cm BOOLEAN DEFAULT FALSE; -- Cameroon
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_cf BOOLEAN DEFAULT FALSE; -- Central African Republic
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_td BOOLEAN DEFAULT FALSE; -- Chad
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_km BOOLEAN DEFAULT FALSE; -- Comoros
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_cg BOOLEAN DEFAULT FALSE; -- Congo (Republic)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_cd BOOLEAN DEFAULT FALSE; -- Congo (DRC)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_ci BOOLEAN DEFAULT FALSE; -- Côte d'Ivoire
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_dj BOOLEAN DEFAULT FALSE; -- Djibouti
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_eg BOOLEAN DEFAULT FALSE; -- Egypt
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_gq BOOLEAN DEFAULT FALSE; -- Equatorial Guinea
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_er BOOLEAN DEFAULT FALSE; -- Eritrea
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_sz BOOLEAN DEFAULT FALSE; -- Eswatini
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_et BOOLEAN DEFAULT FALSE; -- Ethiopia
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_ga BOOLEAN DEFAULT FALSE; -- Gabon
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_gm BOOLEAN DEFAULT FALSE; -- Gambia
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_gh BOOLEAN DEFAULT FALSE; -- Ghana
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_gn BOOLEAN DEFAULT FALSE; -- Guinea
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_gw BOOLEAN DEFAULT FALSE; -- Guinea-Bissau
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_ke BOOLEAN DEFAULT FALSE; -- Kenya
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_ls BOOLEAN DEFAULT FALSE; -- Lesotho
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_lr BOOLEAN DEFAULT FALSE; -- Liberia
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_ly BOOLEAN DEFAULT FALSE; -- Libya
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_mg BOOLEAN DEFAULT FALSE; -- Madagascar
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_mw BOOLEAN DEFAULT FALSE; -- Malawi
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_ml BOOLEAN DEFAULT FALSE; -- Mali
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_mr BOOLEAN DEFAULT FALSE; -- Mauritania
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_mu BOOLEAN DEFAULT FALSE; -- Mauritius
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_ma BOOLEAN DEFAULT FALSE; -- Morocco
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_mz BOOLEAN DEFAULT FALSE; -- Mozambique
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_na BOOLEAN DEFAULT FALSE; -- Namibia
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_ne BOOLEAN DEFAULT FALSE; -- Niger
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_ng BOOLEAN DEFAULT FALSE; -- Nigeria
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_rw BOOLEAN DEFAULT FALSE; -- Rwanda
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_st BOOLEAN DEFAULT FALSE; -- São Tomé and Príncipe
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_sn BOOLEAN DEFAULT FALSE; -- Senegal
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_sc BOOLEAN DEFAULT FALSE; -- Seychelles
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_sl BOOLEAN DEFAULT FALSE; -- Sierra Leone
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_so BOOLEAN DEFAULT FALSE; -- Somalia
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_za BOOLEAN DEFAULT FALSE; -- South Africa
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_ss BOOLEAN DEFAULT FALSE; -- South Sudan
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_sd BOOLEAN DEFAULT FALSE; -- Sudan
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_tz BOOLEAN DEFAULT FALSE; -- Tanzania
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_tg BOOLEAN DEFAULT FALSE; -- Togo
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_tn BOOLEAN DEFAULT FALSE; -- Tunisia
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_ug BOOLEAN DEFAULT FALSE; -- Uganda
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_zm BOOLEAN DEFAULT FALSE; -- Zambia
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_zw BOOLEAN DEFAULT FALSE; -- Zimbabwe

-- Americas (35 countries)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_ag BOOLEAN DEFAULT FALSE; -- Antigua and Barbuda
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_ar BOOLEAN DEFAULT FALSE; -- Argentina
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_bs BOOLEAN DEFAULT FALSE; -- Bahamas
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_bb BOOLEAN DEFAULT FALSE; -- Barbados
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_bz BOOLEAN DEFAULT FALSE; -- Belize
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_bo BOOLEAN DEFAULT FALSE; -- Bolivia
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_br BOOLEAN DEFAULT FALSE; -- Brazil
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_ca BOOLEAN DEFAULT FALSE; -- Canada
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_cl BOOLEAN DEFAULT FALSE; -- Chile
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_co BOOLEAN DEFAULT FALSE; -- Colombia
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_cr BOOLEAN DEFAULT FALSE; -- Costa Rica
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_cu BOOLEAN DEFAULT FALSE; -- Cuba
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_dm BOOLEAN DEFAULT FALSE; -- Dominica
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_do BOOLEAN DEFAULT FALSE; -- Dominican Republic
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_ec BOOLEAN DEFAULT FALSE; -- Ecuador
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_sv BOOLEAN DEFAULT FALSE; -- El Salvador
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_gd BOOLEAN DEFAULT FALSE; -- Grenada
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_gt BOOLEAN DEFAULT FALSE; -- Guatemala
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_gy BOOLEAN DEFAULT FALSE; -- Guyana
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_ht BOOLEAN DEFAULT FALSE; -- Haiti
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_hn BOOLEAN DEFAULT FALSE; -- Honduras
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_jm BOOLEAN DEFAULT FALSE; -- Jamaica
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_mx BOOLEAN DEFAULT FALSE; -- Mexico
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_ni BOOLEAN DEFAULT FALSE; -- Nicaragua
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_pa BOOLEAN DEFAULT FALSE; -- Panama
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_py BOOLEAN DEFAULT FALSE; -- Paraguay
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_pe BOOLEAN DEFAULT FALSE; -- Peru
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_kn BOOLEAN DEFAULT FALSE; -- Saint Kitts and Nevis
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_lc BOOLEAN DEFAULT FALSE; -- Saint Lucia
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_vc BOOLEAN DEFAULT FALSE; -- Saint Vincent and the Grenadines
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_sr BOOLEAN DEFAULT FALSE; -- Suriname
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_tt BOOLEAN DEFAULT FALSE; -- Trinidad and Tobago
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_us BOOLEAN DEFAULT FALSE; -- United States
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_uy BOOLEAN DEFAULT FALSE; -- Uruguay
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_ve BOOLEAN DEFAULT FALSE; -- Venezuela

-- Asia (49 countries)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_af BOOLEAN DEFAULT FALSE; -- Afghanistan
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_am BOOLEAN DEFAULT FALSE; -- Armenia
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_az BOOLEAN DEFAULT FALSE; -- Azerbaijan
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_bh BOOLEAN DEFAULT FALSE; -- Bahrain
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_bd BOOLEAN DEFAULT FALSE; -- Bangladesh
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_bt BOOLEAN DEFAULT FALSE; -- Bhutan
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_bn BOOLEAN DEFAULT FALSE; -- Brunei
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_kh BOOLEAN DEFAULT FALSE; -- Cambodia
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_cn BOOLEAN DEFAULT FALSE; -- China
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_cy BOOLEAN DEFAULT FALSE; -- Cyprus
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_ge BOOLEAN DEFAULT FALSE; -- Georgia
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_in BOOLEAN DEFAULT FALSE; -- India
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_id BOOLEAN DEFAULT FALSE; -- Indonesia
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_ir BOOLEAN DEFAULT FALSE; -- Iran
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_iq BOOLEAN DEFAULT FALSE; -- Iraq
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_il BOOLEAN DEFAULT FALSE; -- Israel
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_jp BOOLEAN DEFAULT FALSE; -- Japan
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_jo BOOLEAN DEFAULT FALSE; -- Jordan
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_kz BOOLEAN DEFAULT FALSE; -- Kazakhstan
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_kw BOOLEAN DEFAULT FALSE; -- Kuwait
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_kg BOOLEAN DEFAULT FALSE; -- Kyrgyzstan
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_la BOOLEAN DEFAULT FALSE; -- Laos
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_lb BOOLEAN DEFAULT FALSE; -- Lebanon
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_my BOOLEAN DEFAULT FALSE; -- Malaysia
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_mv BOOLEAN DEFAULT FALSE; -- Maldives
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_mn BOOLEAN DEFAULT FALSE; -- Mongolia
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_mm BOOLEAN DEFAULT FALSE; -- Myanmar
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_np BOOLEAN DEFAULT FALSE; -- Nepal
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_kp BOOLEAN DEFAULT FALSE; -- North Korea
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_om BOOLEAN DEFAULT FALSE; -- Oman
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_pk BOOLEAN DEFAULT FALSE; -- Pakistan
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_ps BOOLEAN DEFAULT FALSE; -- Palestine
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_ph BOOLEAN DEFAULT FALSE; -- Philippines
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_qa BOOLEAN DEFAULT FALSE; -- Qatar
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_sa BOOLEAN DEFAULT FALSE; -- Saudi Arabia
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_sg BOOLEAN DEFAULT FALSE; -- Singapore
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_kr BOOLEAN DEFAULT FALSE; -- South Korea
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_lk BOOLEAN DEFAULT FALSE; -- Sri Lanka
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_sy BOOLEAN DEFAULT FALSE; -- Syria
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_tj BOOLEAN DEFAULT FALSE; -- Tajikistan
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_th BOOLEAN DEFAULT FALSE; -- Thailand
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_tl BOOLEAN DEFAULT FALSE; -- Timor-Leste
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_tr BOOLEAN DEFAULT FALSE; -- Turkey
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_tm BOOLEAN DEFAULT FALSE; -- Turkmenistan
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_ae BOOLEAN DEFAULT FALSE; -- United Arab Emirates
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_uz BOOLEAN DEFAULT FALSE; -- Uzbekistan
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_vn BOOLEAN DEFAULT FALSE; -- Vietnam
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_ye BOOLEAN DEFAULT FALSE; -- Yemen

-- Europe (44 countries)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_al BOOLEAN DEFAULT FALSE; -- Albania
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_ad BOOLEAN DEFAULT FALSE; -- Andorra
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_at BOOLEAN DEFAULT FALSE; -- Austria
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_by BOOLEAN DEFAULT FALSE; -- Belarus
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_be BOOLEAN DEFAULT FALSE; -- Belgium
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_ba BOOLEAN DEFAULT FALSE; -- Bosnia and Herzegovina
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_bg BOOLEAN DEFAULT FALSE; -- Bulgaria
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_hr BOOLEAN DEFAULT FALSE; -- Croatia
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_cz BOOLEAN DEFAULT FALSE; -- Czechia
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_dk BOOLEAN DEFAULT FALSE; -- Denmark
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_ee BOOLEAN DEFAULT FALSE; -- Estonia
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_fi BOOLEAN DEFAULT FALSE; -- Finland
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_fr BOOLEAN DEFAULT FALSE; -- France
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_de BOOLEAN DEFAULT FALSE; -- Germany
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_gr BOOLEAN DEFAULT FALSE; -- Greece
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_va BOOLEAN DEFAULT FALSE; -- Holy See (Vatican)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_hu BOOLEAN DEFAULT FALSE; -- Hungary
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_is BOOLEAN DEFAULT FALSE; -- Iceland
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_ie BOOLEAN DEFAULT FALSE; -- Ireland
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_it BOOLEAN DEFAULT FALSE; -- Italy
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_xk BOOLEAN DEFAULT FALSE; -- Kosovo
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_lv BOOLEAN DEFAULT FALSE; -- Latvia
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_li BOOLEAN DEFAULT FALSE; -- Liechtenstein
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_lt BOOLEAN DEFAULT FALSE; -- Lithuania
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_lu BOOLEAN DEFAULT FALSE; -- Luxembourg
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_mk BOOLEAN DEFAULT FALSE; -- North Macedonia
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_mt BOOLEAN DEFAULT FALSE; -- Malta
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_md BOOLEAN DEFAULT FALSE; -- Moldova
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_mc BOOLEAN DEFAULT FALSE; -- Monaco
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_me BOOLEAN DEFAULT FALSE; -- Montenegro
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_nl BOOLEAN DEFAULT FALSE; -- Netherlands
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_no BOOLEAN DEFAULT FALSE; -- Norway
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_pl BOOLEAN DEFAULT FALSE; -- Poland
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_pt BOOLEAN DEFAULT FALSE; -- Portugal
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_ro BOOLEAN DEFAULT FALSE; -- Romania
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_ru BOOLEAN DEFAULT FALSE; -- Russia
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_sm BOOLEAN DEFAULT FALSE; -- San Marino
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_rs BOOLEAN DEFAULT FALSE; -- Serbia
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_sk BOOLEAN DEFAULT FALSE; -- Slovakia
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_si BOOLEAN DEFAULT FALSE; -- Slovenia
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_es BOOLEAN DEFAULT FALSE; -- Spain
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_se BOOLEAN DEFAULT FALSE; -- Sweden
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_ch BOOLEAN DEFAULT FALSE; -- Switzerland
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_ua BOOLEAN DEFAULT FALSE; -- Ukraine
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_gb BOOLEAN DEFAULT FALSE; -- United Kingdom

-- Oceania (15 countries)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_au BOOLEAN DEFAULT FALSE; -- Australia
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_fj BOOLEAN DEFAULT FALSE; -- Fiji
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_ki BOOLEAN DEFAULT FALSE; -- Kiribati
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_mh BOOLEAN DEFAULT FALSE; -- Marshall Islands
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_fm BOOLEAN DEFAULT FALSE; -- Micronesia
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_nr BOOLEAN DEFAULT FALSE; -- Nauru
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_nz BOOLEAN DEFAULT FALSE; -- New Zealand
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_pw BOOLEAN DEFAULT FALSE; -- Palau
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_pg BOOLEAN DEFAULT FALSE; -- Papua New Guinea
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_ws BOOLEAN DEFAULT FALSE; -- Samoa
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_sb BOOLEAN DEFAULT FALSE; -- Solomon Islands
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_to BOOLEAN DEFAULT FALSE; -- Tonga
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_tv BOOLEAN DEFAULT FALSE; -- Tuvalu
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_vu BOOLEAN DEFAULT FALSE; -- Vanuatu

-- Total: 197 country columns

-- ============================================================================
-- Indexes for Geographic Analysis
-- ============================================================================

-- Index high-research-output countries (partial indexes for performance)
CREATE INDEX IF NOT EXISTS idx_auth_us ON literature_review(auth_us) WHERE auth_us = TRUE;
CREATE INDEX IF NOT EXISTS idx_auth_au ON literature_review(auth_au) WHERE auth_au = TRUE;
CREATE INDEX IF NOT EXISTS idx_auth_gb ON literature_review(auth_gb) WHERE auth_gb = TRUE;
CREATE INDEX IF NOT EXISTS idx_auth_ca ON literature_review(auth_ca) WHERE auth_ca = TRUE;
CREATE INDEX IF NOT EXISTS idx_auth_de ON literature_review(auth_de) WHERE auth_de = TRUE;
CREATE INDEX IF NOT EXISTS idx_auth_fr ON literature_review(auth_fr) WHERE auth_fr = TRUE;
CREATE INDEX IF NOT EXISTS idx_auth_es ON literature_review(auth_es) WHERE auth_es = TRUE;
CREATE INDEX IF NOT EXISTS idx_auth_jp ON literature_review(auth_jp) WHERE auth_jp = TRUE;
CREATE INDEX IF NOT EXISTS idx_auth_cn ON literature_review(auth_cn) WHERE auth_cn = TRUE;
CREATE INDEX IF NOT EXISTS idx_auth_br ON literature_review(auth_br) WHERE auth_br = TRUE;
CREATE INDEX IF NOT EXISTS idx_auth_za ON literature_review(auth_za) WHERE auth_za = TRUE;
CREATE INDEX IF NOT EXISTS idx_auth_mx ON literature_review(auth_mx) WHERE auth_mx = TRUE;

-- ============================================================================
-- Helper View: Country Summary
-- ============================================================================

-- Note: This view will be populated after data is entered
-- Full view creation deferred to avoid extremely long SQL

-- ============================================================================
-- Comments & Documentation
-- ============================================================================

COMMENT ON COLUMN literature_review.auth_us IS 'Author affiliation: United States';
COMMENT ON COLUMN literature_review.auth_au IS 'Author affiliation: Australia';
COMMENT ON COLUMN literature_review.auth_gb IS 'Author affiliation: United Kingdom';
COMMENT ON COLUMN literature_review.auth_ca IS 'Author affiliation: Canada';
COMMENT ON COLUMN literature_review.auth_de IS 'Author affiliation: Germany';
-- (Additional comments omitted for brevity - add as needed)

-- ============================================================================
-- Usage Examples
-- ============================================================================

/*
-- Mark a paper with international collaboration
UPDATE literature_review
SET
    auth_us = TRUE,
    auth_au = TRUE,
    auth_gb = TRUE
WHERE study_id = 1;

-- Find all papers with US authors
SELECT title, year
FROM literature_review
WHERE auth_us = TRUE;

-- Count papers by country (example for top 10)
SELECT
    'United States' AS country,
    SUM(CASE WHEN auth_us THEN 1 ELSE 0 END) AS paper_count
FROM literature_review
UNION ALL
SELECT 'Australia', SUM(CASE WHEN auth_au THEN 1 ELSE 0 END)
FROM literature_review
UNION ALL
SELECT 'United Kingdom', SUM(CASE WHEN auth_gb THEN 1 ELSE 0 END)
FROM literature_review
ORDER BY paper_count DESC;

-- Find international collaborations (2+ countries)
SELECT title, year
FROM literature_review
WHERE (CAST(auth_us AS INTEGER) + CAST(auth_au AS INTEGER) + CAST(auth_gb AS INTEGER) +
       CAST(auth_ca AS INTEGER) + CAST(auth_de AS INTEGER) + CAST(auth_fr AS INTEGER)) >= 2;
*/
