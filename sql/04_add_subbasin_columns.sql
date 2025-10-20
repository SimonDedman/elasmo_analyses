-- Large Marine Ecosystem Sub-basin Columns (66 LMEs)
-- NOAA Large Marine Ecosystems
-- Note: These are OPTIONAL columns for finer geographic resolution

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
