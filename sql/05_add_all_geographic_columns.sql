-- EEA 2025 Data Panel: Geographic Columns
-- Database: literature_review table

-- This file adds author nationality and geographic location columns
-- Compatible with: DuckDB, SQLite, PostgreSQL

-- Column Summary:
--   Author nations: 249 columns (auth_*)
--   Ocean basins: 9 columns (b_*)
--   Sub-basins (LMEs): 66 columns (sb_*, optional)
--   Total: 324 geographic columns

----------------------------------------

-- ========================================
-- SECTION 1: Author Nationality (249 columns)
-- ========================================

ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_afg BOOLEAN DEFAULT FALSE; -- Afghanistan
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_alb BOOLEAN DEFAULT FALSE; -- Albania
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_dza BOOLEAN DEFAULT FALSE; -- Algeria
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_asm BOOLEAN DEFAULT FALSE; -- American Samoa
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_and BOOLEAN DEFAULT FALSE; -- Andorra
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_ago BOOLEAN DEFAULT FALSE; -- Angola
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_aia BOOLEAN DEFAULT FALSE; -- Anguilla
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_ata BOOLEAN DEFAULT FALSE; -- Antarctica
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_atg BOOLEAN DEFAULT FALSE; -- Antigua and Barbuda
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_arg BOOLEAN DEFAULT FALSE; -- Argentina
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_arm BOOLEAN DEFAULT FALSE; -- Armenia
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_abw BOOLEAN DEFAULT FALSE; -- Aruba
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_aus BOOLEAN DEFAULT FALSE; -- Australia
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_aut BOOLEAN DEFAULT FALSE; -- Austria
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_aze BOOLEAN DEFAULT FALSE; -- Azerbaijan
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_bhs BOOLEAN DEFAULT FALSE; -- Bahamas
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_bhr BOOLEAN DEFAULT FALSE; -- Bahrain
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_bgd BOOLEAN DEFAULT FALSE; -- Bangladesh
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_brb BOOLEAN DEFAULT FALSE; -- Barbados
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_blr BOOLEAN DEFAULT FALSE; -- Belarus
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_bel BOOLEAN DEFAULT FALSE; -- Belgium
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_blz BOOLEAN DEFAULT FALSE; -- Belize
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_ben BOOLEAN DEFAULT FALSE; -- Benin
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_bmu BOOLEAN DEFAULT FALSE; -- Bermuda
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_btn BOOLEAN DEFAULT FALSE; -- Bhutan
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_bol BOOLEAN DEFAULT FALSE; -- Bolivia, Plurinational State of
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_bes BOOLEAN DEFAULT FALSE; -- Bonaire, Sint Eustatius and Saba
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_bih BOOLEAN DEFAULT FALSE; -- Bosnia and Herzegovina
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_bwa BOOLEAN DEFAULT FALSE; -- Botswana
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_bvt BOOLEAN DEFAULT FALSE; -- Bouvet Island
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_bra BOOLEAN DEFAULT FALSE; -- Brazil
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_iot BOOLEAN DEFAULT FALSE; -- British Indian Ocean Territory
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_brn BOOLEAN DEFAULT FALSE; -- Brunei Darussalam
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_bgr BOOLEAN DEFAULT FALSE; -- Bulgaria
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_bfa BOOLEAN DEFAULT FALSE; -- Burkina Faso
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_bdi BOOLEAN DEFAULT FALSE; -- Burundi
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_cpv BOOLEAN DEFAULT FALSE; -- Cabo Verde
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_khm BOOLEAN DEFAULT FALSE; -- Cambodia
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_cmr BOOLEAN DEFAULT FALSE; -- Cameroon
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_can BOOLEAN DEFAULT FALSE; -- Canada
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_cym BOOLEAN DEFAULT FALSE; -- Cayman Islands
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_caf BOOLEAN DEFAULT FALSE; -- Central African Republic
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_tcd BOOLEAN DEFAULT FALSE; -- Chad
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_chl BOOLEAN DEFAULT FALSE; -- Chile
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_chn BOOLEAN DEFAULT FALSE; -- China
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_cxr BOOLEAN DEFAULT FALSE; -- Christmas Island
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_cck BOOLEAN DEFAULT FALSE; -- Cocos (Keeling) Islands
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_col BOOLEAN DEFAULT FALSE; -- Colombia
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_com BOOLEAN DEFAULT FALSE; -- Comoros
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_cog BOOLEAN DEFAULT FALSE; -- Congo
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_cod BOOLEAN DEFAULT FALSE; -- Congo, The Democratic Republic of the
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_cok BOOLEAN DEFAULT FALSE; -- Cook Islands
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_cri BOOLEAN DEFAULT FALSE; -- Costa Rica
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_hrv BOOLEAN DEFAULT FALSE; -- Croatia
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_cub BOOLEAN DEFAULT FALSE; -- Cuba
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_cuw BOOLEAN DEFAULT FALSE; -- Curaçao
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_cyp BOOLEAN DEFAULT FALSE; -- Cyprus
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_cze BOOLEAN DEFAULT FALSE; -- Czechia
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_civ BOOLEAN DEFAULT FALSE; -- Côte d'Ivoire
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_dnk BOOLEAN DEFAULT FALSE; -- Denmark
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_dji BOOLEAN DEFAULT FALSE; -- Djibouti
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_dma BOOLEAN DEFAULT FALSE; -- Dominica
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_dom BOOLEAN DEFAULT FALSE; -- Dominican Republic
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_ecu BOOLEAN DEFAULT FALSE; -- Ecuador
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_egy BOOLEAN DEFAULT FALSE; -- Egypt
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_slv BOOLEAN DEFAULT FALSE; -- El Salvador
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_gnq BOOLEAN DEFAULT FALSE; -- Equatorial Guinea
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_eri BOOLEAN DEFAULT FALSE; -- Eritrea
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_est BOOLEAN DEFAULT FALSE; -- Estonia
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_swz BOOLEAN DEFAULT FALSE; -- Eswatini
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_eth BOOLEAN DEFAULT FALSE; -- Ethiopia
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_flk BOOLEAN DEFAULT FALSE; -- Falkland Islands (Malvinas)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_fro BOOLEAN DEFAULT FALSE; -- Faroe Islands
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_fji BOOLEAN DEFAULT FALSE; -- Fiji
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_fin BOOLEAN DEFAULT FALSE; -- Finland
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_fra BOOLEAN DEFAULT FALSE; -- France
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_guf BOOLEAN DEFAULT FALSE; -- French Guiana
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_pyf BOOLEAN DEFAULT FALSE; -- French Polynesia
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_atf BOOLEAN DEFAULT FALSE; -- French Southern Territories
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_gab BOOLEAN DEFAULT FALSE; -- Gabon
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_gmb BOOLEAN DEFAULT FALSE; -- Gambia
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_geo BOOLEAN DEFAULT FALSE; -- Georgia
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_deu BOOLEAN DEFAULT FALSE; -- Germany
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_gha BOOLEAN DEFAULT FALSE; -- Ghana
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_gib BOOLEAN DEFAULT FALSE; -- Gibraltar
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_grc BOOLEAN DEFAULT FALSE; -- Greece
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_grl BOOLEAN DEFAULT FALSE; -- Greenland
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_grd BOOLEAN DEFAULT FALSE; -- Grenada
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_glp BOOLEAN DEFAULT FALSE; -- Guadeloupe
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_gum BOOLEAN DEFAULT FALSE; -- Guam
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_gtm BOOLEAN DEFAULT FALSE; -- Guatemala
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_ggy BOOLEAN DEFAULT FALSE; -- Guernsey
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_gin BOOLEAN DEFAULT FALSE; -- Guinea
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_gnb BOOLEAN DEFAULT FALSE; -- Guinea-Bissau
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_guy BOOLEAN DEFAULT FALSE; -- Guyana
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_hti BOOLEAN DEFAULT FALSE; -- Haiti
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_hmd BOOLEAN DEFAULT FALSE; -- Heard Island and McDonald Islands
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_vat BOOLEAN DEFAULT FALSE; -- Holy See (Vatican City State)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_hnd BOOLEAN DEFAULT FALSE; -- Honduras
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_hkg BOOLEAN DEFAULT FALSE; -- Hong Kong
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_hun BOOLEAN DEFAULT FALSE; -- Hungary
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_isl BOOLEAN DEFAULT FALSE; -- Iceland
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_ind BOOLEAN DEFAULT FALSE; -- India
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_idn BOOLEAN DEFAULT FALSE; -- Indonesia
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_irn BOOLEAN DEFAULT FALSE; -- Iran, Islamic Republic of
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_irq BOOLEAN DEFAULT FALSE; -- Iraq
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_irl BOOLEAN DEFAULT FALSE; -- Ireland
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_imn BOOLEAN DEFAULT FALSE; -- Isle of Man
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_isr BOOLEAN DEFAULT FALSE; -- Israel
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_ita BOOLEAN DEFAULT FALSE; -- Italy
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_jam BOOLEAN DEFAULT FALSE; -- Jamaica
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_jpn BOOLEAN DEFAULT FALSE; -- Japan
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_jey BOOLEAN DEFAULT FALSE; -- Jersey
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_jor BOOLEAN DEFAULT FALSE; -- Jordan
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_kaz BOOLEAN DEFAULT FALSE; -- Kazakhstan
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_ken BOOLEAN DEFAULT FALSE; -- Kenya
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_kir BOOLEAN DEFAULT FALSE; -- Kiribati
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_prk BOOLEAN DEFAULT FALSE; -- Korea, Democratic People's Republic of
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_kor BOOLEAN DEFAULT FALSE; -- Korea, Republic of
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_kwt BOOLEAN DEFAULT FALSE; -- Kuwait
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_kgz BOOLEAN DEFAULT FALSE; -- Kyrgyzstan
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_lao BOOLEAN DEFAULT FALSE; -- Lao People's Democratic Republic
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_lva BOOLEAN DEFAULT FALSE; -- Latvia
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_lbn BOOLEAN DEFAULT FALSE; -- Lebanon
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_lso BOOLEAN DEFAULT FALSE; -- Lesotho
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_lbr BOOLEAN DEFAULT FALSE; -- Liberia
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_lby BOOLEAN DEFAULT FALSE; -- Libya
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_lie BOOLEAN DEFAULT FALSE; -- Liechtenstein
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_ltu BOOLEAN DEFAULT FALSE; -- Lithuania
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_lux BOOLEAN DEFAULT FALSE; -- Luxembourg
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_mac BOOLEAN DEFAULT FALSE; -- Macao
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_mdg BOOLEAN DEFAULT FALSE; -- Madagascar
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_mwi BOOLEAN DEFAULT FALSE; -- Malawi
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_mys BOOLEAN DEFAULT FALSE; -- Malaysia
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_mdv BOOLEAN DEFAULT FALSE; -- Maldives
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_mli BOOLEAN DEFAULT FALSE; -- Mali
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_mlt BOOLEAN DEFAULT FALSE; -- Malta
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_mhl BOOLEAN DEFAULT FALSE; -- Marshall Islands
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_mtq BOOLEAN DEFAULT FALSE; -- Martinique
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_mrt BOOLEAN DEFAULT FALSE; -- Mauritania
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_mus BOOLEAN DEFAULT FALSE; -- Mauritius
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_myt BOOLEAN DEFAULT FALSE; -- Mayotte
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_mex BOOLEAN DEFAULT FALSE; -- Mexico
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_fsm BOOLEAN DEFAULT FALSE; -- Micronesia, Federated States of
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_mda BOOLEAN DEFAULT FALSE; -- Moldova, Republic of
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_mco BOOLEAN DEFAULT FALSE; -- Monaco
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_mng BOOLEAN DEFAULT FALSE; -- Mongolia
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_mne BOOLEAN DEFAULT FALSE; -- Montenegro
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_msr BOOLEAN DEFAULT FALSE; -- Montserrat
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_mar BOOLEAN DEFAULT FALSE; -- Morocco
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_moz BOOLEAN DEFAULT FALSE; -- Mozambique
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_mmr BOOLEAN DEFAULT FALSE; -- Myanmar
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_nam BOOLEAN DEFAULT FALSE; -- Namibia
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_nru BOOLEAN DEFAULT FALSE; -- Nauru
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_npl BOOLEAN DEFAULT FALSE; -- Nepal
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_nld BOOLEAN DEFAULT FALSE; -- Netherlands
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_ncl BOOLEAN DEFAULT FALSE; -- New Caledonia
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_nzl BOOLEAN DEFAULT FALSE; -- New Zealand
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_nic BOOLEAN DEFAULT FALSE; -- Nicaragua
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_ner BOOLEAN DEFAULT FALSE; -- Niger
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_nga BOOLEAN DEFAULT FALSE; -- Nigeria
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_niu BOOLEAN DEFAULT FALSE; -- Niue
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_nfk BOOLEAN DEFAULT FALSE; -- Norfolk Island
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_mkd BOOLEAN DEFAULT FALSE; -- North Macedonia
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_mnp BOOLEAN DEFAULT FALSE; -- Northern Mariana Islands
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_nor BOOLEAN DEFAULT FALSE; -- Norway
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_omn BOOLEAN DEFAULT FALSE; -- Oman
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_pak BOOLEAN DEFAULT FALSE; -- Pakistan
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_plw BOOLEAN DEFAULT FALSE; -- Palau
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_pse BOOLEAN DEFAULT FALSE; -- Palestine, State of
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_pan BOOLEAN DEFAULT FALSE; -- Panama
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_png BOOLEAN DEFAULT FALSE; -- Papua New Guinea
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_pry BOOLEAN DEFAULT FALSE; -- Paraguay
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_per BOOLEAN DEFAULT FALSE; -- Peru
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_phl BOOLEAN DEFAULT FALSE; -- Philippines
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_pcn BOOLEAN DEFAULT FALSE; -- Pitcairn
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_pol BOOLEAN DEFAULT FALSE; -- Poland
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_prt BOOLEAN DEFAULT FALSE; -- Portugal
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_pri BOOLEAN DEFAULT FALSE; -- Puerto Rico
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_qat BOOLEAN DEFAULT FALSE; -- Qatar
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_rou BOOLEAN DEFAULT FALSE; -- Romania
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_rus BOOLEAN DEFAULT FALSE; -- Russian Federation
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_rwa BOOLEAN DEFAULT FALSE; -- Rwanda
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_reu BOOLEAN DEFAULT FALSE; -- Réunion
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_blm BOOLEAN DEFAULT FALSE; -- Saint Barthélemy
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_shn BOOLEAN DEFAULT FALSE; -- Saint Helena, Ascension and Tristan da Cunha
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_kna BOOLEAN DEFAULT FALSE; -- Saint Kitts and Nevis
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_lca BOOLEAN DEFAULT FALSE; -- Saint Lucia
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_maf BOOLEAN DEFAULT FALSE; -- Saint Martin (French part)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_spm BOOLEAN DEFAULT FALSE; -- Saint Pierre and Miquelon
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_vct BOOLEAN DEFAULT FALSE; -- Saint Vincent and the Grenadines
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_wsm BOOLEAN DEFAULT FALSE; -- Samoa
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_smr BOOLEAN DEFAULT FALSE; -- San Marino
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_stp BOOLEAN DEFAULT FALSE; -- Sao Tome and Principe
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_sau BOOLEAN DEFAULT FALSE; -- Saudi Arabia
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_sen BOOLEAN DEFAULT FALSE; -- Senegal
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_srb BOOLEAN DEFAULT FALSE; -- Serbia
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_syc BOOLEAN DEFAULT FALSE; -- Seychelles
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_sle BOOLEAN DEFAULT FALSE; -- Sierra Leone
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_sgp BOOLEAN DEFAULT FALSE; -- Singapore
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_sxm BOOLEAN DEFAULT FALSE; -- Sint Maarten (Dutch part)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_svk BOOLEAN DEFAULT FALSE; -- Slovakia
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_svn BOOLEAN DEFAULT FALSE; -- Slovenia
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_slb BOOLEAN DEFAULT FALSE; -- Solomon Islands
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_som BOOLEAN DEFAULT FALSE; -- Somalia
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_zaf BOOLEAN DEFAULT FALSE; -- South Africa
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_sgs BOOLEAN DEFAULT FALSE; -- South Georgia and the South Sandwich Islands
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_ssd BOOLEAN DEFAULT FALSE; -- South Sudan
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_esp BOOLEAN DEFAULT FALSE; -- Spain
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_lka BOOLEAN DEFAULT FALSE; -- Sri Lanka
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_sdn BOOLEAN DEFAULT FALSE; -- Sudan
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_sur BOOLEAN DEFAULT FALSE; -- Suriname
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_sjm BOOLEAN DEFAULT FALSE; -- Svalbard and Jan Mayen
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_swe BOOLEAN DEFAULT FALSE; -- Sweden
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_che BOOLEAN DEFAULT FALSE; -- Switzerland
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_syr BOOLEAN DEFAULT FALSE; -- Syrian Arab Republic
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_twn BOOLEAN DEFAULT FALSE; -- Taiwan, Province of China
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_tjk BOOLEAN DEFAULT FALSE; -- Tajikistan
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_tza BOOLEAN DEFAULT FALSE; -- Tanzania, United Republic of
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_tha BOOLEAN DEFAULT FALSE; -- Thailand
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_tls BOOLEAN DEFAULT FALSE; -- Timor-Leste
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_tgo BOOLEAN DEFAULT FALSE; -- Togo
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_tkl BOOLEAN DEFAULT FALSE; -- Tokelau
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_ton BOOLEAN DEFAULT FALSE; -- Tonga
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_tto BOOLEAN DEFAULT FALSE; -- Trinidad and Tobago
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_tun BOOLEAN DEFAULT FALSE; -- Tunisia
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_tkm BOOLEAN DEFAULT FALSE; -- Turkmenistan
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_tca BOOLEAN DEFAULT FALSE; -- Turks and Caicos Islands
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_tuv BOOLEAN DEFAULT FALSE; -- Tuvalu
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_tur BOOLEAN DEFAULT FALSE; -- Türkiye
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_uga BOOLEAN DEFAULT FALSE; -- Uganda
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_ukr BOOLEAN DEFAULT FALSE; -- Ukraine
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_are BOOLEAN DEFAULT FALSE; -- United Arab Emirates
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_gbr BOOLEAN DEFAULT FALSE; -- United Kingdom
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_usa BOOLEAN DEFAULT FALSE; -- United States
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_umi BOOLEAN DEFAULT FALSE; -- United States Minor Outlying Islands
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_ury BOOLEAN DEFAULT FALSE; -- Uruguay
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_uzb BOOLEAN DEFAULT FALSE; -- Uzbekistan
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_vut BOOLEAN DEFAULT FALSE; -- Vanuatu
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_ven BOOLEAN DEFAULT FALSE; -- Venezuela, Bolivarian Republic of
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_vnm BOOLEAN DEFAULT FALSE; -- Viet Nam
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_vgb BOOLEAN DEFAULT FALSE; -- Virgin Islands, British
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_vir BOOLEAN DEFAULT FALSE; -- Virgin Islands, U.S.
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_wlf BOOLEAN DEFAULT FALSE; -- Wallis and Futuna
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_esh BOOLEAN DEFAULT FALSE; -- Western Sahara
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_yem BOOLEAN DEFAULT FALSE; -- Yemen
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_zmb BOOLEAN DEFAULT FALSE; -- Zambia
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_zwe BOOLEAN DEFAULT FALSE; -- Zimbabwe
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS auth_ala BOOLEAN DEFAULT FALSE; -- Åland Islands

-- ========================================
-- SECTION 2: Ocean Basins (9 columns)
-- ========================================

ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS b_arctic BOOLEAN DEFAULT FALSE; -- Arctic Ocean
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS b_caribbean BOOLEAN DEFAULT FALSE; -- Caribbean Sea
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS b_indian BOOLEAN DEFAULT FALSE; -- Indian Ocean
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS b_mediterranean BOOLEAN DEFAULT FALSE; -- Mediterranean Sea
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS b_north_atlantic BOOLEAN DEFAULT FALSE; -- North Atlantic Ocean
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS b_north_pacific BOOLEAN DEFAULT FALSE; -- North Pacific Ocean
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS b_south_atlantic BOOLEAN DEFAULT FALSE; -- South Atlantic Ocean
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS b_south_pacific BOOLEAN DEFAULT FALSE; -- South Pacific Ocean
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS b_southern BOOLEAN DEFAULT FALSE; -- Southern Ocean

-- ========================================
-- SECTION 3: Sub-basins / LMEs (66 columns, OPTIONAL)
-- ========================================
-- Note: Sub-basins provide finer geographic resolution
-- You can skip this section if not needed

ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_east_bering_sea BOOLEAN DEFAULT FALSE; -- LME #1: East Bering Sea
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_gulf_of_alaska BOOLEAN DEFAULT FALSE; -- LME #2: Gulf of Alaska
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_california_current BOOLEAN DEFAULT FALSE; -- LME #3: California Current
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_gulf_of_california BOOLEAN DEFAULT FALSE; -- LME #4: Gulf of California
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_gulf_of_mexico BOOLEAN DEFAULT FALSE; -- LME #5: Gulf of Mexico
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_southeast_u_s_continental_shelf BOOLEAN DEFAULT FALSE; -- LME #6: Southeast U.S. Continental Shelf
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_northeast_u_s_continental_shelf BOOLEAN DEFAULT FALSE; -- LME #7: Northeast U.S. Continental Shelf
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_scotian_shelf BOOLEAN DEFAULT FALSE; -- LME #8: Scotian Shelf
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_newfoundland_labrador_shelf BOOLEAN DEFAULT FALSE; -- LME #9: Newfoundland-Labrador Shelf
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_insular_pacific_hawaiian BOOLEAN DEFAULT FALSE; -- LME #10: Insular Pacific-Hawaiian
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_pacific_central_american_coastal BOOLEAN DEFAULT FALSE; -- LME #11: Pacific Central-American Coastal
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_caribbean_sea BOOLEAN DEFAULT FALSE; -- LME #12: Caribbean Sea
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_humboldt_current BOOLEAN DEFAULT FALSE; -- LME #13: Humboldt Current
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_patagonian_shelf BOOLEAN DEFAULT FALSE; -- LME #14: Patagonian Shelf
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_south_brazil_shelf BOOLEAN DEFAULT FALSE; -- LME #15: South Brazil Shelf
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_east_brazil_shelf BOOLEAN DEFAULT FALSE; -- LME #16: East Brazil Shelf
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_north_brazil_shelf BOOLEAN DEFAULT FALSE; -- LME #17: North Brazil Shelf
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_west_greenland_shelf BOOLEAN DEFAULT FALSE; -- LME #18: West Greenland Shelf
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_east_greenland_shelf BOOLEAN DEFAULT FALSE; -- LME #19: East Greenland Shelf
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_barents_sea BOOLEAN DEFAULT FALSE; -- LME #20: Barents Sea
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_norwegian_sea BOOLEAN DEFAULT FALSE; -- LME #21: Norwegian Sea
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_north_sea BOOLEAN DEFAULT FALSE; -- LME #22: North Sea
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_baltic_sea BOOLEAN DEFAULT FALSE; -- LME #23: Baltic Sea
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_celtic_biscay_shelf BOOLEAN DEFAULT FALSE; -- LME #24: Celtic-Biscay Shelf
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_iberian_coastal BOOLEAN DEFAULT FALSE; -- LME #25: Iberian Coastal
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_mediterranean_sea BOOLEAN DEFAULT FALSE; -- LME #26: Mediterranean Sea
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_canary_current BOOLEAN DEFAULT FALSE; -- LME #27: Canary Current
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_guinea_current BOOLEAN DEFAULT FALSE; -- LME #28: Guinea Current
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_benguela_current BOOLEAN DEFAULT FALSE; -- LME #29: Benguela Current
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_agulhas_current BOOLEAN DEFAULT FALSE; -- LME #30: Agulhas Current
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_somali_coastal_current BOOLEAN DEFAULT FALSE; -- LME #31: Somali Coastal Current
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_arabian_sea BOOLEAN DEFAULT FALSE; -- LME #32: Arabian Sea
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_red_sea BOOLEAN DEFAULT FALSE; -- LME #33: Red Sea
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_bay_of_bengal BOOLEAN DEFAULT FALSE; -- LME #34: Bay of Bengal
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_gulf_of_thailand BOOLEAN DEFAULT FALSE; -- LME #35: Gulf of Thailand
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_south_china_sea BOOLEAN DEFAULT FALSE; -- LME #36: South China Sea
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_sulu_celebes_sea BOOLEAN DEFAULT FALSE; -- LME #37: Sulu-Celebes Sea
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_indonesian_sea BOOLEAN DEFAULT FALSE; -- LME #38: Indonesian Sea
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_north_australian_shelf BOOLEAN DEFAULT FALSE; -- LME #39: North Australian Shelf
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_northeast_australian_shelf BOOLEAN DEFAULT FALSE; -- LME #40: Northeast Australian Shelf
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_east_central_australian_shelf BOOLEAN DEFAULT FALSE; -- LME #41: East Central Australian Shelf
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_southeast_australian_shelf BOOLEAN DEFAULT FALSE; -- LME #42: Southeast Australian Shelf
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_south_west_australian_shelf BOOLEAN DEFAULT FALSE; -- LME #43: South West Australian Shelf
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_west_central_australian_shelf BOOLEAN DEFAULT FALSE; -- LME #44: West Central Australian Shelf
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_northwest_australian_shelf BOOLEAN DEFAULT FALSE; -- LME #45: Northwest Australian Shelf
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_new_zealand_shelf BOOLEAN DEFAULT FALSE; -- LME #46: New Zealand Shelf
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_east_china_sea BOOLEAN DEFAULT FALSE; -- LME #47: East China Sea
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_yellow_sea BOOLEAN DEFAULT FALSE; -- LME #48: Yellow Sea
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_kuroshio_current BOOLEAN DEFAULT FALSE; -- LME #49: Kuroshio Current
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_sea_of_japan BOOLEAN DEFAULT FALSE; -- LME #50: Sea of Japan
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_oyashio_current BOOLEAN DEFAULT FALSE; -- LME #51: Oyashio Current
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_sea_of_okhotsk BOOLEAN DEFAULT FALSE; -- LME #52: Sea of Okhotsk
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_west_bering_sea BOOLEAN DEFAULT FALSE; -- LME #53: West Bering Sea
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_northern_bering_chukchi_seas BOOLEAN DEFAULT FALSE; -- LME #54: Northern Bering - Chukchi Seas
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_beaufort_sea BOOLEAN DEFAULT FALSE; -- LME #55: Beaufort Sea
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_east_siberian_sea BOOLEAN DEFAULT FALSE; -- LME #56: East Siberian Sea
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_laptev_sea BOOLEAN DEFAULT FALSE; -- LME #57: Laptev Sea
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_kara_sea BOOLEAN DEFAULT FALSE; -- LME #58: Kara Sea
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_iceland_shelf_and_sea BOOLEAN DEFAULT FALSE; -- LME #59: Iceland Shelf and Sea
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_faroe_plateau BOOLEAN DEFAULT FALSE; -- LME #60: Faroe Plateau
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_antarctica BOOLEAN DEFAULT FALSE; -- LME #61: Antarctica
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_black_sea BOOLEAN DEFAULT FALSE; -- LME #62: Black Sea
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_hudson_bay_complex BOOLEAN DEFAULT FALSE; -- LME #63: Hudson Bay Complex
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_central_arctic BOOLEAN DEFAULT FALSE; -- LME #64: Central Arctic
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_aleutian_islands BOOLEAN DEFAULT FALSE; -- LME #65: Aleutian Islands
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sb_canadian_high_arctic_north_greenland BOOLEAN DEFAULT FALSE; -- LME #66: Canadian High Arctic - North Greenland
