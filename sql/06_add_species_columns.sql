-- ============================================================================
-- EEA 2025 Data Panel: Species Binary Columns
-- ============================================================================
--
-- Purpose: Add binary columns for each chondrichthyan species
--
-- Schema Version: 1.0
-- Created: 2025-10-02
-- Database: DuckDB
--
-- Dependencies: 01_create_core_table.sql
--
-- Design Rationale:
--   - Track species-specific research focus
--   - Papers often study multiple species (comparative, community ecology)
--   - Binary columns enable multi-species tracking
--   - Prefix 'sp_' identifies species columns
--   - Column names use binomial format: sp_genus_species (lowercase, underscore)
--   - Default FALSE for explicit missing data tracking
--
-- Source: species_common_lookup_cleaned.csv
--   - 1030 unique species
--   - Generated automatically from cleaned lookup table
--   - Primary common name selected alphabetically
--
-- Note: This file generated with 1030 species from cleaned lookup.
--       Expected ~1,208 species per Weigmann 2016.
--       Missing 178 species - will be added when updated list received.
--
-- ============================================================================
-- ============================================================================
-- Add Species Binary Columns
-- ============================================================================

-- Acroteriobatus (8 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_acroteriobatus_annulatus BOOLEAN DEFAULT FALSE; -- Acroteriobatus annulatus (Guitarfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_acroteriobatus_blochii BOOLEAN DEFAULT FALSE; -- Acroteriobatus blochii (Bluntnose fiddlefish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_acroteriobatus_leucospilus BOOLEAN DEFAULT FALSE; -- Acroteriobatus leucospilus (Blue-spotted guitarfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_acroteriobatus_ocellatus BOOLEAN DEFAULT FALSE; -- Acroteriobatus ocellatus (Speckled guitarfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_acroteriobatus_omanensis BOOLEAN DEFAULT FALSE; -- Acroteriobatus omanensis (Oman guitarfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_acroteriobatus_salalah BOOLEAN DEFAULT FALSE; -- Acroteriobatus salalah (Salalah guitarfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_acroteriobatus_variegatus BOOLEAN DEFAULT FALSE; -- Acroteriobatus variegatus (Stripenose guitarfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_acroteriobatus_zanzibarensis BOOLEAN DEFAULT FALSE; -- Acroteriobatus zanzibarensis (Zanzibar guitarfish)

-- Aculeola (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_aculeola_nigra BOOLEAN DEFAULT FALSE; -- Aculeola nigra (Hooktooth dogfish)

-- Aetobatus (5 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_aetobatus_flagellum BOOLEAN DEFAULT FALSE; -- Aetobatus flagellum (Eagle ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_aetobatus_laticeps BOOLEAN DEFAULT FALSE; -- Aetobatus laticeps (Pacific eagle ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_aetobatus_narinari BOOLEAN DEFAULT FALSE; -- Aetobatus narinari (Bishop ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_aetobatus_narutobiei BOOLEAN DEFAULT FALSE; -- Aetobatus narutobiei (Naru eagle ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_aetobatus_ocellatus BOOLEAN DEFAULT FALSE; -- Aetobatus ocellatus (Ocellated eagle ray)

-- Aetomylaeus (5 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_aetomylaeus_caeruleofasciatus BOOLEAN DEFAULT FALSE; -- Aetomylaeus caeruleofasciatus (Blue-banded eagle ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_aetomylaeus_maculatus BOOLEAN DEFAULT FALSE; -- Aetomylaeus maculatus (Bat ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_aetomylaeus_milvus BOOLEAN DEFAULT FALSE; -- Aetomylaeus milvus (Brown eagle-ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_aetomylaeus_nichofii BOOLEAN DEFAULT FALSE; -- Aetomylaeus nichofii (Banded eagle ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_aetomylaeus_vespertilio BOOLEAN DEFAULT FALSE; -- Aetomylaeus vespertilio (Ornate eagle ray)

-- Alopias (3 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_alopias_pelagicus BOOLEAN DEFAULT FALSE; -- Alopias pelagicus (Fox shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_alopias_superciliosus BOOLEAN DEFAULT FALSE; -- Alopias superciliosus (Bigeye thresher shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_alopias_vulpinus BOOLEAN DEFAULT FALSE; -- Alopias vulpinus (Atlantic thresher)

-- Amblyraja (8 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_amblyraja_doellojuradoi BOOLEAN DEFAULT FALSE; -- Amblyraja doellojuradoi (Southern thorny skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_amblyraja_frerichsi BOOLEAN DEFAULT FALSE; -- Amblyraja frerichsi (Thickbody skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_amblyraja_georgiana BOOLEAN DEFAULT FALSE; -- Amblyraja georgiana (Amblyraja georgiana)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_amblyraja_hyperborea BOOLEAN DEFAULT FALSE; -- Amblyraja hyperborea (Arctic skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_amblyraja_jenseni BOOLEAN DEFAULT FALSE; -- Amblyraja jenseni (Jensen's skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_amblyraja_radiata BOOLEAN DEFAULT FALSE; -- Amblyraja radiata (Artic thorny skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_amblyraja_reversa BOOLEAN DEFAULT FALSE; -- Amblyraja reversa (Reversed skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_amblyraja_taaf BOOLEAN DEFAULT FALSE; -- Amblyraja taaf (Thorny skate)

-- Anacanthobatis (2 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_anacanthobatis_donghaiensis BOOLEAN DEFAULT FALSE; -- Anacanthobatis donghaiensis (East China leg skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_anacanthobatis_nanhaiensis BOOLEAN DEFAULT FALSE; -- Anacanthobatis nanhaiensis (South China leg skate)

-- Anoxypristis (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_anoxypristis_cuspidata BOOLEAN DEFAULT FALSE; -- Anoxypristis cuspidata (Knifetooth sawfish)

-- Apristurus (29 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_apristurus_breviventralis BOOLEAN DEFAULT FALSE; -- Apristurus breviventralis (Shortbelly catshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_apristurus_brunneus BOOLEAN DEFAULT FALSE; -- Apristurus brunneus (Brown cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_apristurus_bucephalus BOOLEAN DEFAULT FALSE; -- Apristurus bucephalus (Bighead catshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_apristurus_canutus BOOLEAN DEFAULT FALSE; -- Apristurus canutus (Hoary cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_apristurus_gibbosus BOOLEAN DEFAULT FALSE; -- Apristurus gibbosus (Humpback cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_apristurus_herklotsi BOOLEAN DEFAULT FALSE; -- Apristurus herklotsi (Longfin cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_apristurus_indicus BOOLEAN DEFAULT FALSE; -- Apristurus indicus (Smallbelly cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_apristurus_investigatoris BOOLEAN DEFAULT FALSE; -- Apristurus investigatoris (Broadnose cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_apristurus_japonicus BOOLEAN DEFAULT FALSE; -- Apristurus japonicus (Japanese cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_apristurus_kampae BOOLEAN DEFAULT FALSE; -- Apristurus kampae (Longnose cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_apristurus_laurussonii BOOLEAN DEFAULT FALSE; -- Apristurus laurussonii (Atlantic ghost cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_apristurus_longicephalus BOOLEAN DEFAULT FALSE; -- Apristurus longicephalus (Longhead cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_apristurus_macrorhynchus BOOLEAN DEFAULT FALSE; -- Apristurus macrorhynchus (Flathead cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_apristurus_macrostomus BOOLEAN DEFAULT FALSE; -- Apristurus macrostomus (Broadmouth cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_apristurus_manis BOOLEAN DEFAULT FALSE; -- Apristurus manis (Ghost cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_apristurus_melanoasper BOOLEAN DEFAULT FALSE; -- Apristurus melanoasper (Black roughscale catshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_apristurus_microps BOOLEAN DEFAULT FALSE; -- Apristurus microps (Smalleye cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_apristurus_micropterygeus BOOLEAN DEFAULT FALSE; -- Apristurus micropterygeus (Smalldorsal cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_apristurus_nakayai BOOLEAN DEFAULT FALSE; -- Apristurus nakayai (Milk-eye catshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_apristurus_nasutus BOOLEAN DEFAULT FALSE; -- Apristurus nasutus (Largenose cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_apristurus_parvipinnis BOOLEAN DEFAULT FALSE; -- Apristurus parvipinnis (Smallfin cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_apristurus_platyrhynchus BOOLEAN DEFAULT FALSE; -- Apristurus platyrhynchus (Borneo cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_apristurus_profundorum BOOLEAN DEFAULT FALSE; -- Apristurus profundorum (Deep-water catshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_apristurus_riveri BOOLEAN DEFAULT FALSE; -- Apristurus riveri (Broadgill cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_apristurus_saldanha BOOLEAN DEFAULT FALSE; -- Apristurus saldanha (Saldanha cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_apristurus_sibogae BOOLEAN DEFAULT FALSE; -- Apristurus sibogae (Pale cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_apristurus_sinensis BOOLEAN DEFAULT FALSE; -- Apristurus sinensis (South China cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_apristurus_spongiceps BOOLEAN DEFAULT FALSE; -- Apristurus spongiceps (Spongehead cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_apristurus_stenseni BOOLEAN DEFAULT FALSE; -- Apristurus stenseni (Panama ghost cat shark)

-- Aptychotrema (3 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_aptychotrema_rostrata BOOLEAN DEFAULT FALSE; -- Aptychotrema rostrata (Australian shovelnose ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_aptychotrema_timorensis BOOLEAN DEFAULT FALSE; -- Aptychotrema timorensis (Spotted shovelnose ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_aptychotrema_vincentiana BOOLEAN DEFAULT FALSE; -- Aptychotrema vincentiana (Guitarfish)

-- Arhynchobatis (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_arhynchobatis_asperrimus BOOLEAN DEFAULT FALSE; -- Arhynchobatis asperrimus (Longtail skate)

-- Asymbolus (9 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_asymbolus_analis BOOLEAN DEFAULT FALSE; -- Asymbolus analis (Australian spotted catshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_asymbolus_funebris BOOLEAN DEFAULT FALSE; -- Asymbolus funebris (Blotched catshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_asymbolus_galacticus BOOLEAN DEFAULT FALSE; -- Asymbolus galacticus (Starry catshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_asymbolus_occiduus BOOLEAN DEFAULT FALSE; -- Asymbolus occiduus (Spotted cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_asymbolus_pallidus BOOLEAN DEFAULT FALSE; -- Asymbolus pallidus (Pale spotted catshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_asymbolus_parvus BOOLEAN DEFAULT FALSE; -- Asymbolus parvus (Dwarf catshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_asymbolus_rubiginosus BOOLEAN DEFAULT FALSE; -- Asymbolus rubiginosus (Orange spotted catshrak)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_asymbolus_submaculatus BOOLEAN DEFAULT FALSE; -- Asymbolus submaculatus (Saddled catshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_asymbolus_vincenti BOOLEAN DEFAULT FALSE; -- Asymbolus vincenti (Gulf cat shark)

-- Atelomycterus (6 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_atelomycterus_baliensis BOOLEAN DEFAULT FALSE; -- Atelomycterus baliensis (Bali catshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_atelomycterus_erdmanni BOOLEAN DEFAULT FALSE; -- Atelomycterus erdmanni (Spotted-belly catshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_atelomycterus_fasciatus BOOLEAN DEFAULT FALSE; -- Atelomycterus fasciatus (Banded catshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_atelomycterus_macleayi BOOLEAN DEFAULT FALSE; -- Atelomycterus macleayi (Australian marbled cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_atelomycterus_marmoratus BOOLEAN DEFAULT FALSE; -- Atelomycterus marmoratus (Coral catshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_atelomycterus_marnkalha BOOLEAN DEFAULT FALSE; -- Atelomycterus marnkalha (Eastern banded catshark)

-- Atlantoraja (3 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_atlantoraja_castelnaui BOOLEAN DEFAULT FALSE; -- Atlantoraja castelnaui (Spotback skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_atlantoraja_cyclophora BOOLEAN DEFAULT FALSE; -- Atlantoraja cyclophora (Eyespot skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_atlantoraja_platana BOOLEAN DEFAULT FALSE; -- Atlantoraja platana (La Plata skate)

-- Aulohalaelurus (2 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_aulohalaelurus_kanakorum BOOLEAN DEFAULT FALSE; -- Aulohalaelurus kanakorum (Kanakorum catshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_aulohalaelurus_labiosus BOOLEAN DEFAULT FALSE; -- Aulohalaelurus labiosus (Australian blackspot catshark)

-- Bathyraja (44 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_bathyraja_abyssicola BOOLEAN DEFAULT FALSE; -- Bathyraja abyssicola (Deep-sea skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_bathyraja_aguja BOOLEAN DEFAULT FALSE; -- Bathyraja aguja (Aguja skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_bathyraja_aleutica BOOLEAN DEFAULT FALSE; -- Bathyraja aleutica (Aleutian skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_bathyraja_andriashevi BOOLEAN DEFAULT FALSE; -- Bathyraja andriashevi (Little-eyed skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_bathyraja_bergi BOOLEAN DEFAULT FALSE; -- Bathyraja bergi (Bottom skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_bathyraja_brachyurops BOOLEAN DEFAULT FALSE; -- Bathyraja brachyurops (Broadnose skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_bathyraja_cousseauae BOOLEAN DEFAULT FALSE; -- Bathyraja cousseauae (Joined-fins skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_bathyraja_diplotaenia BOOLEAN DEFAULT FALSE; -- Bathyraja diplotaenia (Dusky-pink skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_bathyraja_eatonii BOOLEAN DEFAULT FALSE; -- Bathyraja eatonii (Eaton's skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_bathyraja_fedorovi BOOLEAN DEFAULT FALSE; -- Bathyraja fedorovi (Cinnamon skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_bathyraja_griseocauda BOOLEAN DEFAULT FALSE; -- Bathyraja griseocauda (Austral ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_bathyraja_hesperafricana BOOLEAN DEFAULT FALSE; -- Bathyraja hesperafricana (West African skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_bathyraja_interrupta BOOLEAN DEFAULT FALSE; -- Bathyraja interrupta (Bering skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_bathyraja_irrasa BOOLEAN DEFAULT FALSE; -- Bathyraja irrasa (Kerguelen sandpaper skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_bathyraja_ishiharai BOOLEAN DEFAULT FALSE; -- Bathyraja ishiharai (Abyssal skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_bathyraja_isotrachys BOOLEAN DEFAULT FALSE; -- Bathyraja isotrachys (Challenger skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_bathyraja_kincaidii BOOLEAN DEFAULT FALSE; -- Bathyraja kincaidii (Sandpaper Skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_bathyraja_leucomelanos BOOLEAN DEFAULT FALSE; -- Bathyraja leucomelanos (Domino skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_bathyraja_lindbergi BOOLEAN DEFAULT FALSE; -- Bathyraja lindbergi (Commander skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_bathyraja_longicauda BOOLEAN DEFAULT FALSE; -- Bathyraja longicauda (Slimtail skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_bathyraja_maccaini BOOLEAN DEFAULT FALSE; -- Bathyraja maccaini (McCain's skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_bathyraja_maculata BOOLEAN DEFAULT FALSE; -- Bathyraja maculata (White-blotched skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_bathyraja_mariposa BOOLEAN DEFAULT FALSE; -- Bathyraja mariposa (Butterfly skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_bathyraja_matsubarai BOOLEAN DEFAULT FALSE; -- Bathyraja matsubarai (Dusky-purple skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_bathyraja_meridionalis BOOLEAN DEFAULT FALSE; -- Bathyraja meridionalis (Dark-belly skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_bathyraja_microtrachys BOOLEAN DEFAULT FALSE; -- Bathyraja microtrachys (Fine-spined skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_bathyraja_minispinosa BOOLEAN DEFAULT FALSE; -- Bathyraja minispinosa (Smallthorn skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_bathyraja_notoroensis BOOLEAN DEFAULT FALSE; -- Bathyraja notoroensis (Notoro skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_bathyraja_pallida BOOLEAN DEFAULT FALSE; -- Bathyraja pallida (Pale ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_bathyraja_panthera BOOLEAN DEFAULT FALSE; -- Bathyraja panthera (Leopard skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_bathyraja_papilionifera BOOLEAN DEFAULT FALSE; -- Bathyraja papilionifera (Butterfly skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_bathyraja_peruana BOOLEAN DEFAULT FALSE; -- Bathyraja peruana (Peruvian skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_bathyraja_richardsoni BOOLEAN DEFAULT FALSE; -- Bathyraja richardsoni (Deepsea skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_bathyraja_scaphiops BOOLEAN DEFAULT FALSE; -- Bathyraja scaphiops (Cuphead skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_bathyraja_schroederi BOOLEAN DEFAULT FALSE; -- Bathyraja schroederi (Whitemouth skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_bathyraja_shuntovi BOOLEAN DEFAULT FALSE; -- Bathyraja shuntovi (Longnose deep-sea skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_bathyraja_smirnovi BOOLEAN DEFAULT FALSE; -- Bathyraja smirnovi (Golden skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_bathyraja_smithii BOOLEAN DEFAULT FALSE; -- Bathyraja smithii (African softnose skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_bathyraja_spinicauda BOOLEAN DEFAULT FALSE; -- Bathyraja spinicauda (Spinetail ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_bathyraja_spinosissima BOOLEAN DEFAULT FALSE; -- Bathyraja spinosissima (Pacific white skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_bathyraja_trachouros BOOLEAN DEFAULT FALSE; -- Bathyraja trachouros (Eremo skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_bathyraja_trachura BOOLEAN DEFAULT FALSE; -- Bathyraja trachura (Black skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_bathyraja_tzinovskii BOOLEAN DEFAULT FALSE; -- Bathyraja tzinovskii (Creamback skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_bathyraja_violacea BOOLEAN DEFAULT FALSE; -- Bathyraja violacea (Okhotsk skate)

-- Benthobatis (3 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_benthobatis_marcida BOOLEAN DEFAULT FALSE; -- Benthobatis marcida (Blind Torpedo)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_benthobatis_moresbyi BOOLEAN DEFAULT FALSE; -- Benthobatis moresbyi (Dark blind ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_benthobatis_yangi BOOLEAN DEFAULT FALSE; -- Benthobatis yangi (Taiwanese blind electric ray)

-- Beringraja (2 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_beringraja_binoculata BOOLEAN DEFAULT FALSE; -- Beringraja binoculata (Big skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_beringraja_pulchra BOOLEAN DEFAULT FALSE; -- Beringraja pulchra (Mottled skate)

-- Brachaelurus (2 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_brachaelurus_colcloughi BOOLEAN DEFAULT FALSE; -- Brachaelurus colcloughi (Blue-gray carpet shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_brachaelurus_waddi BOOLEAN DEFAULT FALSE; -- Brachaelurus waddi (Blind shark)

-- Breviraja (5 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_breviraja_claramaculata BOOLEAN DEFAULT FALSE; -- Breviraja claramaculata (Brightspot skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_breviraja_colesi BOOLEAN DEFAULT FALSE; -- Breviraja colesi (Lightnose Skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_breviraja_mouldi BOOLEAN DEFAULT FALSE; -- Breviraja mouldi (Blacknose skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_breviraja_nigriventralis BOOLEAN DEFAULT FALSE; -- Breviraja nigriventralis (Blackbelly skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_breviraja_spinosa BOOLEAN DEFAULT FALSE; -- Breviraja spinosa (Spinose skate)

-- Brevitrygon (2 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_brevitrygon_heterura BOOLEAN DEFAULT FALSE; -- Brevitrygon heterura (Dwarf whipray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_brevitrygon_javaensis BOOLEAN DEFAULT FALSE; -- Brevitrygon javaensis (Javan whipray)

-- Brochiraja (2 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_brochiraja_asperula BOOLEAN DEFAULT FALSE; -- Brochiraja asperula (Prickly deepsea skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_brochiraja_spinifera BOOLEAN DEFAULT FALSE; -- Brochiraja spinifera (Prickly deep-sea skate)

-- Bythaelurus (13 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_bythaelurus_alcockii BOOLEAN DEFAULT FALSE; -- Bythaelurus alcockii (Arabian cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_bythaelurus_bachi BOOLEAN DEFAULT FALSE; -- Bythaelurus bachi (Bach's catshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_bythaelurus_canescens BOOLEAN DEFAULT FALSE; -- Bythaelurus canescens (Cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_bythaelurus_clevai BOOLEAN DEFAULT FALSE; -- Bythaelurus clevai (Broadhead cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_bythaelurus_dawsoni BOOLEAN DEFAULT FALSE; -- Bythaelurus dawsoni (Dawson's catshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_bythaelurus_giddingsi BOOLEAN DEFAULT FALSE; -- Bythaelurus giddingsi (GalÃ¡pagos catshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_bythaelurus_hispidus BOOLEAN DEFAULT FALSE; -- Bythaelurus hispidus (Bristly cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_bythaelurus_immaculatus BOOLEAN DEFAULT FALSE; -- Bythaelurus immaculatus (Spotless cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_bythaelurus_incanus BOOLEAN DEFAULT FALSE; -- Bythaelurus incanus (Dusky catshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_bythaelurus_lutarius BOOLEAN DEFAULT FALSE; -- Bythaelurus lutarius (Brown catshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_bythaelurus_naylori BOOLEAN DEFAULT FALSE; -- Bythaelurus naylori (Dusky snout catshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_bythaelurus_tenuicephalus BOOLEAN DEFAULT FALSE; -- Bythaelurus tenuicephalus (Narrowhead catshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_bythaelurus_vivaldii BOOLEAN DEFAULT FALSE; -- Bythaelurus vivaldii (Vivaldi's catshark)

-- Callorhinchus (3 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_callorhinchus_callorynchus BOOLEAN DEFAULT FALSE; -- Callorhinchus callorynchus (Elephant fish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_callorhinchus_capensis BOOLEAN DEFAULT FALSE; -- Callorhinchus capensis (Cape elephantfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_callorhinchus_milii BOOLEAN DEFAULT FALSE; -- Callorhinchus milii (Elephant fish)

-- Caranx (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_caranx_latus BOOLEAN DEFAULT FALSE; -- Caranx latus (Horse-eye jack)

-- Carcharhinus (32 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_carcharhinus_acronotus BOOLEAN DEFAULT FALSE; -- Carcharhinus acronotus (Blacknose shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_carcharhinus_albimarginatus BOOLEAN DEFAULT FALSE; -- Carcharhinus albimarginatus (Silver-tip reef shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_carcharhinus_altimus BOOLEAN DEFAULT FALSE; -- Carcharhinus altimus (Bignose Shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_carcharhinus_amblyrhynchoides BOOLEAN DEFAULT FALSE; -- Carcharhinus amblyrhynchoides (Graceful shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_carcharhinus_amblyrhynchos BOOLEAN DEFAULT FALSE; -- Carcharhinus amblyrhynchos (Black-vee whaler)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_carcharhinus_amboinensis BOOLEAN DEFAULT FALSE; -- Carcharhinus amboinensis (Ambon sharpnose puffer)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_carcharhinus_borneensis BOOLEAN DEFAULT FALSE; -- Carcharhinus borneensis (Borneo shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_carcharhinus_brachyurus BOOLEAN DEFAULT FALSE; -- Carcharhinus brachyurus (Black-tipped whaler)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_carcharhinus_brevipinna BOOLEAN DEFAULT FALSE; -- Carcharhinus brevipinna (Blacktipped shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_carcharhinus_cautus BOOLEAN DEFAULT FALSE; -- Carcharhinus cautus (Nervous shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_carcharhinus_cerdale BOOLEAN DEFAULT FALSE; -- Carcharhinus cerdale (Pacific smalltail shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_carcharhinus_dussumieri BOOLEAN DEFAULT FALSE; -- Carcharhinus dussumieri (Coates' shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_carcharhinus_falciformis BOOLEAN DEFAULT FALSE; -- Carcharhinus falciformis (Blackspot shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_carcharhinus_fitzroyensis BOOLEAN DEFAULT FALSE; -- Carcharhinus fitzroyensis (Creek whaler)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_carcharhinus_galapagensis BOOLEAN DEFAULT FALSE; -- Carcharhinus galapagensis (Galapagos shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_carcharhinus_hemiodon BOOLEAN DEFAULT FALSE; -- Carcharhinus hemiodon (Long nosed shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_carcharhinus_humani BOOLEAN DEFAULT FALSE; -- Carcharhinus humani (Human's whaler shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_carcharhinus_isodon BOOLEAN DEFAULT FALSE; -- Carcharhinus isodon (Eventooth shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_carcharhinus_leiodon BOOLEAN DEFAULT FALSE; -- Carcharhinus leiodon (Smooth tooth blacktip shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_carcharhinus_leucas BOOLEAN DEFAULT FALSE; -- Carcharhinus leucas (Bull shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_carcharhinus_limbatus BOOLEAN DEFAULT FALSE; -- Carcharhinus limbatus (Black fin shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_carcharhinus_longimanus BOOLEAN DEFAULT FALSE; -- Carcharhinus longimanus (Brown Milbert's sand bar shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_carcharhinus_macloti BOOLEAN DEFAULT FALSE; -- Carcharhinus macloti (Hardnose shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_carcharhinus_melanopterus BOOLEAN DEFAULT FALSE; -- Carcharhinus melanopterus (Black fin reef shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_carcharhinus_obscurus BOOLEAN DEFAULT FALSE; -- Carcharhinus obscurus (Bay-shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_carcharhinus_perezii BOOLEAN DEFAULT FALSE; -- Carcharhinus perezii (Caribbean reef shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_carcharhinus_plumbeus BOOLEAN DEFAULT FALSE; -- Carcharhinus plumbeus (Brown shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_carcharhinus_porosus BOOLEAN DEFAULT FALSE; -- Carcharhinus porosus (Small-tailed shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_carcharhinus_sealei BOOLEAN DEFAULT FALSE; -- Carcharhinus sealei (Black-spot shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_carcharhinus_signatus BOOLEAN DEFAULT FALSE; -- Carcharhinus signatus (Night shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_carcharhinus_sorrah BOOLEAN DEFAULT FALSE; -- Carcharhinus sorrah (Gray shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_carcharhinus_tilstoni BOOLEAN DEFAULT FALSE; -- Carcharhinus tilstoni (Australian blacktip shark)

-- Carcharias (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_carcharias_taurus BOOLEAN DEFAULT FALSE; -- Carcharias taurus (Blue nurse shark)

-- Carcharodon (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_carcharodon_carcharias BOOLEAN DEFAULT FALSE; -- Carcharodon carcharias (Great white shark)

-- Caretta (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_caretta_caretta BOOLEAN DEFAULT FALSE; -- Caretta caretta (Loggerhead sea turtle)

-- Centrophorus (11 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_centrophorus_atromarginatus BOOLEAN DEFAULT FALSE; -- Centrophorus atromarginatus (Blackfin gulper shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_centrophorus_granulosus BOOLEAN DEFAULT FALSE; -- Centrophorus granulosus (Gulper Shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_centrophorus_harrissoni BOOLEAN DEFAULT FALSE; -- Centrophorus harrissoni (Dogfish endeavor)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_centrophorus_isodon BOOLEAN DEFAULT FALSE; -- Centrophorus isodon (Black gulper shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_centrophorus_lusitanicus BOOLEAN DEFAULT FALSE; -- Centrophorus lusitanicus (Lowfin gulper shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_centrophorus_moluccensis BOOLEAN DEFAULT FALSE; -- Centrophorus moluccensis (Arrowspine dogfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_centrophorus_squamosus BOOLEAN DEFAULT FALSE; -- Centrophorus squamosus (Deepsea spiny dogfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_centrophorus_tessellatus BOOLEAN DEFAULT FALSE; -- Centrophorus tessellatus (Mosaic gulper shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_centrophorus_uyato BOOLEAN DEFAULT FALSE; -- Centrophorus uyato (Endeavor dogfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_centrophorus_westraliensis BOOLEAN DEFAULT FALSE; -- Centrophorus westraliensis (Western gulper shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_centrophorus_zeehaani BOOLEAN DEFAULT FALSE; -- Centrophorus zeehaani (Southern dogfish)

-- Centroscyllium (7 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_centroscyllium_excelsum BOOLEAN DEFAULT FALSE; -- Centroscyllium excelsum (Highfin dogfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_centroscyllium_fabricii BOOLEAN DEFAULT FALSE; -- Centroscyllium fabricii (Black dogfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_centroscyllium_granulatum BOOLEAN DEFAULT FALSE; -- Centroscyllium granulatum (Granular dogfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_centroscyllium_kamoharai BOOLEAN DEFAULT FALSE; -- Centroscyllium kamoharai (Bareskin dogfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_centroscyllium_nigrum BOOLEAN DEFAULT FALSE; -- Centroscyllium nigrum (Combtooth dogfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_centroscyllium_ornatum BOOLEAN DEFAULT FALSE; -- Centroscyllium ornatum (Ornate dogfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_centroscyllium_ritteri BOOLEAN DEFAULT FALSE; -- Centroscyllium ritteri (Whitefin dogfish)

-- Centroscymnus (2 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_centroscymnus_coelolepis BOOLEAN DEFAULT FALSE; -- Centroscymnus coelolepis (Portugese dogfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_centroscymnus_owstonii BOOLEAN DEFAULT FALSE; -- Centroscymnus owstonii (Black shark)

-- Centroselachus (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_centroselachus_crepidater BOOLEAN DEFAULT FALSE; -- Centroselachus crepidater (Black shark)

-- Cephaloscyllium (16 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_cephaloscyllium_albipinnum BOOLEAN DEFAULT FALSE; -- Cephaloscyllium albipinnum (Whitefin swellshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_cephaloscyllium_cooki BOOLEAN DEFAULT FALSE; -- Cephaloscyllium cooki (Cook's swellshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_cephaloscyllium_fasciatum BOOLEAN DEFAULT FALSE; -- Cephaloscyllium fasciatum (Leopard-spotted swellshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_cephaloscyllium_formosanum BOOLEAN DEFAULT FALSE; -- Cephaloscyllium formosanum (Formosa swellshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_cephaloscyllium_hiscosellum BOOLEAN DEFAULT FALSE; -- Cephaloscyllium hiscosellum (Australian reticulate swellshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_cephaloscyllium_laticeps BOOLEAN DEFAULT FALSE; -- Cephaloscyllium laticeps (Australian swell shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_cephaloscyllium_pictum BOOLEAN DEFAULT FALSE; -- Cephaloscyllium pictum (Painted swellshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_cephaloscyllium_signourum BOOLEAN DEFAULT FALSE; -- Cephaloscyllium signourum (Flagtail swellshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_cephaloscyllium_silasi BOOLEAN DEFAULT FALSE; -- Cephaloscyllium silasi (Indian swell shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_cephaloscyllium_speccum BOOLEAN DEFAULT FALSE; -- Cephaloscyllium speccum (Speckled swellshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_cephaloscyllium_stevensi BOOLEAN DEFAULT FALSE; -- Cephaloscyllium stevensi (Steven's swellshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_cephaloscyllium_sufflans BOOLEAN DEFAULT FALSE; -- Cephaloscyllium sufflans (Balloon shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_cephaloscyllium_umbratile BOOLEAN DEFAULT FALSE; -- Cephaloscyllium umbratile (Blotchy swell shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_cephaloscyllium_variegatum BOOLEAN DEFAULT FALSE; -- Cephaloscyllium variegatum (Saddled swellshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_cephaloscyllium_ventriosum BOOLEAN DEFAULT FALSE; -- Cephaloscyllium ventriosum (Swell shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_cephaloscyllium_zebrum BOOLEAN DEFAULT FALSE; -- Cephaloscyllium zebrum (Narrowbar swellshark)

-- Cephalurus (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_cephalurus_cephalus BOOLEAN DEFAULT FALSE; -- Cephalurus cephalus (Lollipop cat shark)

-- Cetorhinus (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_cetorhinus_maximus BOOLEAN DEFAULT FALSE; -- Cetorhinus maximus (Basking shark)

-- Chaenogaleus (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_chaenogaleus_macrostoma BOOLEAN DEFAULT FALSE; -- Chaenogaleus macrostoma (Balfour's shark)

-- Chiloscyllium (7 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_chiloscyllium_arabicum BOOLEAN DEFAULT FALSE; -- Chiloscyllium arabicum (Arabian bamboo shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_chiloscyllium_caeruleopunctatum BOOLEAN DEFAULT FALSE; -- Chiloscyllium caeruleopunctatum (Bluespotted bambooshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_chiloscyllium_griseum BOOLEAN DEFAULT FALSE; -- Chiloscyllium griseum (Banded dogfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_chiloscyllium_hasseltii BOOLEAN DEFAULT FALSE; -- Chiloscyllium hasseltii (Catshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_chiloscyllium_indicum BOOLEAN DEFAULT FALSE; -- Chiloscyllium indicum (Catshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_chiloscyllium_plagiosum BOOLEAN DEFAULT FALSE; -- Chiloscyllium plagiosum (White-spotted bamboo shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_chiloscyllium_punctatum BOOLEAN DEFAULT FALSE; -- Chiloscyllium punctatum (Brown spotted cat shark)

-- Chimaera (13 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_chimaera_argiloba BOOLEAN DEFAULT FALSE; -- Chimaera argiloba (Whitefin chimarea)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_chimaera_bahamaensis BOOLEAN DEFAULT FALSE; -- Chimaera bahamaensis (Bahamas ghost shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_chimaera_carophila BOOLEAN DEFAULT FALSE; -- Chimaera carophila (Brown chimaera)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_chimaera_cubana BOOLEAN DEFAULT FALSE; -- Chimaera cubana (Chimaera)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_chimaera_fulva BOOLEAN DEFAULT FALSE; -- Chimaera fulva (Southern chimaera)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_chimaera_lignaria BOOLEAN DEFAULT FALSE; -- Chimaera lignaria (Carpenter's chimaera)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_chimaera_macrospina BOOLEAN DEFAULT FALSE; -- Chimaera macrospina (Longspine chimaera)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_chimaera_monstrosa BOOLEAN DEFAULT FALSE; -- Chimaera monstrosa (Chimaera)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_chimaera_notafricana BOOLEAN DEFAULT FALSE; -- Chimaera notafricana (Cape chimaera)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_chimaera_obscura BOOLEAN DEFAULT FALSE; -- Chimaera obscura (Shortspine chimaera)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_chimaera_opalescens BOOLEAN DEFAULT FALSE; -- Chimaera opalescens (Opal chimaera)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_chimaera_orientalis BOOLEAN DEFAULT FALSE; -- Chimaera orientalis (Eastern Pacific black chimaera)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_chimaera_phantasma BOOLEAN DEFAULT FALSE; -- Chimaera phantasma (Chimaera)

-- Chlamydoselachus (2 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_chlamydoselachus_africana BOOLEAN DEFAULT FALSE; -- Chlamydoselachus africana (African frilled shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_chlamydoselachus_anguineus BOOLEAN DEFAULT FALSE; -- Chlamydoselachus anguineus (Frill shark)

-- Cirrhigaleus (3 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_cirrhigaleus_asper BOOLEAN DEFAULT FALSE; -- Cirrhigaleus asper (Roughskin dogfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_cirrhigaleus_australis BOOLEAN DEFAULT FALSE; -- Cirrhigaleus australis (Mandarin dogfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_cirrhigaleus_barbifer BOOLEAN DEFAULT FALSE; -- Cirrhigaleus barbifer (Mandarin dogfish)

-- Cirrhoscyllium (3 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_cirrhoscyllium_expolitum BOOLEAN DEFAULT FALSE; -- Cirrhoscyllium expolitum (Barbelthroat carpet shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_cirrhoscyllium_formosanum BOOLEAN DEFAULT FALSE; -- Cirrhoscyllium formosanum (Taiwan saddled carpet shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_cirrhoscyllium_japonicum BOOLEAN DEFAULT FALSE; -- Cirrhoscyllium japonicum (Saddle carpetshark)

-- Crassinarke (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_crassinarke_dormitor BOOLEAN DEFAULT FALSE; -- Crassinarke dormitor (Sleeper torpedo)

-- Cruriraja (8 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_cruriraja_andamanica BOOLEAN DEFAULT FALSE; -- Cruriraja andamanica (Andaman leg skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_cruriraja_atlantis BOOLEAN DEFAULT FALSE; -- Cruriraja atlantis (Atlantic leg skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_cruriraja_cadenati BOOLEAN DEFAULT FALSE; -- Cruriraja cadenati (Broadfoot leg skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_cruriraja_durbanensis BOOLEAN DEFAULT FALSE; -- Cruriraja durbanensis (Smooth nose leg skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_cruriraja_hulleyi BOOLEAN DEFAULT FALSE; -- Cruriraja hulleyi (Roughnose legskate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_cruriraja_parcomaculata BOOLEAN DEFAULT FALSE; -- Cruriraja parcomaculata (Roughnose leg skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_cruriraja_poeyi BOOLEAN DEFAULT FALSE; -- Cruriraja poeyi (Cuban leg skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_cruriraja_rugosa BOOLEAN DEFAULT FALSE; -- Cruriraja rugosa (Rough leg skate)

-- Ctenacis (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_ctenacis_fehlmanni BOOLEAN DEFAULT FALSE; -- Ctenacis fehlmanni (Harlequin cat shark)

-- Dactylobatus (2 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_dactylobatus_armatus BOOLEAN DEFAULT FALSE; -- Dactylobatus armatus (Skilletskate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_dactylobatus_clarkii BOOLEAN DEFAULT FALSE; -- Dactylobatus clarkii (Hookskate)

-- Dalatias (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_dalatias_licha BOOLEAN DEFAULT FALSE; -- Dalatias licha (Black shark)

-- Dasyatis (7 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_dasyatis_chrysonota BOOLEAN DEFAULT FALSE; -- Dasyatis chrysonota (Blue stingray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_dasyatis_gigantea BOOLEAN DEFAULT FALSE; -- Dasyatis gigantea (Giant stumptail stingray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_dasyatis_hastata BOOLEAN DEFAULT FALSE; -- Dasyatis hastata (Whip sting-ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_dasyatis_marmorata BOOLEAN DEFAULT FALSE; -- Dasyatis marmorata (Marbled stingray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_dasyatis_multispinosa BOOLEAN DEFAULT FALSE; -- Dasyatis multispinosa (Multispine giant stingray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_dasyatis_pastinaca BOOLEAN DEFAULT FALSE; -- Dasyatis pastinaca (Blue stingray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_dasyatis_tortonesei BOOLEAN DEFAULT FALSE; -- Dasyatis tortonesei (Tortonese's stingray)

-- Deania (3 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_deania_hystricosa BOOLEAN DEFAULT FALSE; -- Deania hystricosa (Rough longnose dogfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_deania_profundorum BOOLEAN DEFAULT FALSE; -- Deania profundorum (Arrowhead dogfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_deania_quadrispinosa BOOLEAN DEFAULT FALSE; -- Deania quadrispinosa (Longsnout dogfish)

-- Dentiraja (2 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_dentiraja_flindersi BOOLEAN DEFAULT FALSE; -- Dentiraja flindersi (Pygmy thornback skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_dentiraja_lemprieri BOOLEAN DEFAULT FALSE; -- Dentiraja lemprieri (Australian thornback skate)

-- Diplobatis (3 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_diplobatis_colombiensis BOOLEAN DEFAULT FALSE; -- Diplobatis colombiensis (Colombian dwarf numbfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_diplobatis_guamachensis BOOLEAN DEFAULT FALSE; -- Diplobatis guamachensis (Venezuelan dwarf numbfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_diplobatis_ommata BOOLEAN DEFAULT FALSE; -- Diplobatis ommata (Bullseye electric ray)

-- Dipturus (31 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_dipturus_acrobelus BOOLEAN DEFAULT FALSE; -- Dipturus acrobelus (Deepwater skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_dipturus_amphispinus BOOLEAN DEFAULT FALSE; -- Dipturus amphispinus (Ridgeback skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_dipturus_apricus BOOLEAN DEFAULT FALSE; -- Dipturus apricus (Pale tropical skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_dipturus_batis BOOLEAN DEFAULT FALSE; -- Dipturus batis (Blue gray skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_dipturus_bullisi BOOLEAN DEFAULT FALSE; -- Dipturus bullisi (Bullis skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_dipturus_campbelli BOOLEAN DEFAULT FALSE; -- Dipturus campbelli (Blackspot skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_dipturus_canutus BOOLEAN DEFAULT FALSE; -- Dipturus canutus (Gray skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_dipturus_crosnieri BOOLEAN DEFAULT FALSE; -- Dipturus crosnieri (Madagascar skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_dipturus_doutrei BOOLEAN DEFAULT FALSE; -- Dipturus doutrei (Javalin skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_dipturus_ecuadoriensis BOOLEAN DEFAULT FALSE; -- Dipturus ecuadoriensis (Ecuador skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_dipturus_garricki BOOLEAN DEFAULT FALSE; -- Dipturus garricki (San Blas skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_dipturus_gigas BOOLEAN DEFAULT FALSE; -- Dipturus gigas (Giant skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_dipturus_gudgeri BOOLEAN DEFAULT FALSE; -- Dipturus gudgeri (Bight skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_dipturus_innominatus BOOLEAN DEFAULT FALSE; -- Dipturus innominatus (New Zealand smooth skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_dipturus_kwangtungensis BOOLEAN DEFAULT FALSE; -- Dipturus kwangtungensis (Kwangtung skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_dipturus_laevis BOOLEAN DEFAULT FALSE; -- Dipturus laevis (Barn-door skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_dipturus_lanceorostratus BOOLEAN DEFAULT FALSE; -- Dipturus lanceorostratus (Rattail skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_dipturus_macrocauda BOOLEAN DEFAULT FALSE; -- Dipturus macrocauda (Bigtail skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_dipturus_melanospilus BOOLEAN DEFAULT FALSE; -- Dipturus melanospilus (Blacktip skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_dipturus_mennii BOOLEAN DEFAULT FALSE; -- Dipturus mennii (South Brazilian skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_dipturus_nidarosiensis BOOLEAN DEFAULT FALSE; -- Dipturus nidarosiensis (Norwegian skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_dipturus_olseni BOOLEAN DEFAULT FALSE; -- Dipturus olseni (Spreadfin skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_dipturus_oregoni BOOLEAN DEFAULT FALSE; -- Dipturus oregoni (Hooktail skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_dipturus_oxyrinchus BOOLEAN DEFAULT FALSE; -- Dipturus oxyrinchus (Long nosed skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_dipturus_queenslandicus BOOLEAN DEFAULT FALSE; -- Dipturus queenslandicus (Queensland deepwater skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_dipturus_springeri BOOLEAN DEFAULT FALSE; -- Dipturus springeri (Roughbelly skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_dipturus_stenorhynchus BOOLEAN DEFAULT FALSE; -- Dipturus stenorhynchus (Prow-nose skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_dipturus_teevani BOOLEAN DEFAULT FALSE; -- Dipturus teevani (Caribbean skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_dipturus_tengu BOOLEAN DEFAULT FALSE; -- Dipturus tengu (Acutenose skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_dipturus_wengi BOOLEAN DEFAULT FALSE; -- Dipturus wengi (Weng's skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_dipturus_wuhanlingi BOOLEAN DEFAULT FALSE; -- Dipturus wuhanlingi (China skate)

-- Discopyge (2 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_discopyge_castelloi BOOLEAN DEFAULT FALSE; -- Discopyge castelloi (Castello's apron numbfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_discopyge_tschudii BOOLEAN DEFAULT FALSE; -- Discopyge tschudii (Apron ray)

-- Echinorhinus (2 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_echinorhinus_brucus BOOLEAN DEFAULT FALSE; -- Echinorhinus brucus (Bramble shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_echinorhinus_cookei BOOLEAN DEFAULT FALSE; -- Echinorhinus cookei (Cooks bramble shark)

-- Electrolux (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_electrolux_addisoni BOOLEAN DEFAULT FALSE; -- Electrolux addisoni (Ornate sleeper-ray)

-- Epinephelus (2 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_epinephelus_itajara BOOLEAN DEFAULT FALSE; -- Epinephelus itajara (Goliath grouper)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_epinephelus_striatus BOOLEAN DEFAULT FALSE; -- Epinephelus striatus (Nassau grouper)

-- Eridacnis (3 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_eridacnis_barbouri BOOLEAN DEFAULT FALSE; -- Eridacnis barbouri (Cuban ribbontail cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_eridacnis_radcliffei BOOLEAN DEFAULT FALSE; -- Eridacnis radcliffei (Pygmy ribbontail cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_eridacnis_sinuans BOOLEAN DEFAULT FALSE; -- Eridacnis sinuans (African ribbontail cat shark)

-- Etmopterus (39 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_etmopterus_alphus BOOLEAN DEFAULT FALSE; -- Etmopterus alphus (Whitecheek lanternshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_etmopterus_benchleyi BOOLEAN DEFAULT FALSE; -- Etmopterus benchleyi (Ninja lanternshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_etmopterus_bigelowi BOOLEAN DEFAULT FALSE; -- Etmopterus bigelowi (Blurred lantern shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_etmopterus_brachyurus BOOLEAN DEFAULT FALSE; -- Etmopterus brachyurus (Short-tail lantern shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_etmopterus_bullisi BOOLEAN DEFAULT FALSE; -- Etmopterus bullisi (Lined lantern shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_etmopterus_burgessi BOOLEAN DEFAULT FALSE; -- Etmopterus burgessi (Broadnose lanternshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_etmopterus_carteri BOOLEAN DEFAULT FALSE; -- Etmopterus carteri (Cylindrical lantern shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_etmopterus_caudistigmus BOOLEAN DEFAULT FALSE; -- Etmopterus caudistigmus (Tailspot lanternshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_etmopterus_compagnoi BOOLEAN DEFAULT FALSE; -- Etmopterus compagnoi (Brown lantern shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_etmopterus_decacuspidatus BOOLEAN DEFAULT FALSE; -- Etmopterus decacuspidatus (Combtooth lantern shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_etmopterus_dianthus BOOLEAN DEFAULT FALSE; -- Etmopterus dianthus (Pink lanternshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_etmopterus_dislineatus BOOLEAN DEFAULT FALSE; -- Etmopterus dislineatus (Lined lanternshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_etmopterus_evansi BOOLEAN DEFAULT FALSE; -- Etmopterus evansi (Blackmouth lanternshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_etmopterus_fusus BOOLEAN DEFAULT FALSE; -- Etmopterus fusus (Pygmy lanternshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_etmopterus_gracilispinis BOOLEAN DEFAULT FALSE; -- Etmopterus gracilispinis (Broadband dogfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_etmopterus_granulosus BOOLEAN DEFAULT FALSE; -- Etmopterus granulosus (Baxters lantern dogfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_etmopterus_hillianus BOOLEAN DEFAULT FALSE; -- Etmopterus hillianus (Blackbelly Dogfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_etmopterus_joungi BOOLEAN DEFAULT FALSE; -- Etmopterus joungi (Shortfin smooth lanternshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_etmopterus_lailae BOOLEAN DEFAULT FALSE; -- Etmopterus lailae (Laila's lanternshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_etmopterus_litvinovi BOOLEAN DEFAULT FALSE; -- Etmopterus litvinovi (Smalleye lantern shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_etmopterus_lucifer BOOLEAN DEFAULT FALSE; -- Etmopterus lucifer (Blackbelly lanternshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_etmopterus_molleri BOOLEAN DEFAULT FALSE; -- Etmopterus molleri (Blackbelly lanternshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_etmopterus_perryi BOOLEAN DEFAULT FALSE; -- Etmopterus perryi (Dwarf lantern shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_etmopterus_polli BOOLEAN DEFAULT FALSE; -- Etmopterus polli (African lantern shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_etmopterus_princeps BOOLEAN DEFAULT FALSE; -- Etmopterus princeps (Great lanternshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_etmopterus_pseudosqualiolus BOOLEAN DEFAULT FALSE; -- Etmopterus pseudosqualiolus (False lanternshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_etmopterus_pusillus BOOLEAN DEFAULT FALSE; -- Etmopterus pusillus (Slender lantern shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_etmopterus_pycnolepis BOOLEAN DEFAULT FALSE; -- Etmopterus pycnolepis (Dense-scale lantern shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_etmopterus_robinsi BOOLEAN DEFAULT FALSE; -- Etmopterus robinsi (West Indian lanternshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_etmopterus_samadiae BOOLEAN DEFAULT FALSE; -- Etmopterus samadiae (Papuan lanternshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_etmopterus_schultzi BOOLEAN DEFAULT FALSE; -- Etmopterus schultzi (Fringefin lantern shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_etmopterus_sculptus BOOLEAN DEFAULT FALSE; -- Etmopterus sculptus (Sculpted lanternshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_etmopterus_sentosus BOOLEAN DEFAULT FALSE; -- Etmopterus sentosus (Thorny lantern shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_etmopterus_sheikoi BOOLEAN DEFAULT FALSE; -- Etmopterus sheikoi (Rasptooth dogfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_etmopterus_spinax BOOLEAN DEFAULT FALSE; -- Etmopterus spinax (Velvet belly)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_etmopterus_splendidus BOOLEAN DEFAULT FALSE; -- Etmopterus splendidus (Splendid lantern shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_etmopterus_unicolor BOOLEAN DEFAULT FALSE; -- Etmopterus unicolor (Bristled lanternshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_etmopterus_villosus BOOLEAN DEFAULT FALSE; -- Etmopterus villosus (Hawaiian lantern shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_etmopterus_virens BOOLEAN DEFAULT FALSE; -- Etmopterus virens (Green lanternshark)

-- Eucrossorhinus (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_eucrossorhinus_dasypogon BOOLEAN DEFAULT FALSE; -- Eucrossorhinus dasypogon (Bearded wobbegong)

-- Euprotomicroides (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_euprotomicroides_zantedeschia BOOLEAN DEFAULT FALSE; -- Euprotomicroides zantedeschia (Taillight shark)

-- Euprotomicrus (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_euprotomicrus_bispinatus BOOLEAN DEFAULT FALSE; -- Euprotomicrus bispinatus (Pygmy shark)

-- Eusphyra (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_eusphyra_blochii BOOLEAN DEFAULT FALSE; -- Eusphyra blochii (Arrow headed hammerhead)

-- Fenestraja (8 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_fenestraja_atripinna BOOLEAN DEFAULT FALSE; -- Fenestraja atripinna (Blackfin pygmy skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_fenestraja_cubensis BOOLEAN DEFAULT FALSE; -- Fenestraja cubensis (Cuban Pygmy Skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_fenestraja_ishiyamai BOOLEAN DEFAULT FALSE; -- Fenestraja ishiyamai (Plain Pygmy Skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_fenestraja_maceachrani BOOLEAN DEFAULT FALSE; -- Fenestraja maceachrani (Madagascar pygmy skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_fenestraja_mamillidens BOOLEAN DEFAULT FALSE; -- Fenestraja mamillidens (Prickly skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_fenestraja_plutonia BOOLEAN DEFAULT FALSE; -- Fenestraja plutonia (Pluto Skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_fenestraja_sibogae BOOLEAN DEFAULT FALSE; -- Fenestraja sibogae (Siboga pygmy skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_fenestraja_sinusmexicanus BOOLEAN DEFAULT FALSE; -- Fenestraja sinusmexicanus (Gulf Of Mexico Pygmy Skate)

-- Figaro (2 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_figaro_boardmani BOOLEAN DEFAULT FALSE; -- Figaro boardmani (Australian sawtail cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_figaro_striatus BOOLEAN DEFAULT FALSE; -- Figaro striatus (Northern sawtail shark)

-- Furgaleus (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_furgaleus_macki BOOLEAN DEFAULT FALSE; -- Furgaleus macki (Mack's whiskery shark)

-- Galeocerdo (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_galeocerdo_cuvier BOOLEAN DEFAULT FALSE; -- Galeocerdo cuvier (Leopard shark)

-- Galeorhinus (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_galeorhinus_galeus BOOLEAN DEFAULT FALSE; -- Galeorhinus galeus (Eastern school shark)

-- Galeus (15 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_galeus_arae BOOLEAN DEFAULT FALSE; -- Galeus arae (Crested shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_galeus_atlanticus BOOLEAN DEFAULT FALSE; -- Galeus atlanticus (Atlantic sawtail cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_galeus_cadenati BOOLEAN DEFAULT FALSE; -- Galeus cadenati (Longfin sawtail cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_galeus_eastmani BOOLEAN DEFAULT FALSE; -- Galeus eastmani (Gecko cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_galeus_gracilis BOOLEAN DEFAULT FALSE; -- Galeus gracilis (Slender sawtail cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_galeus_longirostris BOOLEAN DEFAULT FALSE; -- Galeus longirostris (Longnose sawtail cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_galeus_melastomus BOOLEAN DEFAULT FALSE; -- Galeus melastomus (Black-mouthed dogfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_galeus_mincaronei BOOLEAN DEFAULT FALSE; -- Galeus mincaronei (Southern sawtail catshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_galeus_murinus BOOLEAN DEFAULT FALSE; -- Galeus murinus (Mouse cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_galeus_nipponensis BOOLEAN DEFAULT FALSE; -- Galeus nipponensis (Broadfin sawtail cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_galeus_piperatus BOOLEAN DEFAULT FALSE; -- Galeus piperatus (Peppered cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_galeus_polli BOOLEAN DEFAULT FALSE; -- Galeus polli (African sawtail cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_galeus_sauteri BOOLEAN DEFAULT FALSE; -- Galeus sauteri (Blacktip sawtail catshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_galeus_schultzi BOOLEAN DEFAULT FALSE; -- Galeus schultzi (Dwarf sawtail cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_galeus_springeri BOOLEAN DEFAULT FALSE; -- Galeus springeri (Springer's sawtail cat shark)

-- Ginglymostoma (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_ginglymostoma_cirratum BOOLEAN DEFAULT FALSE; -- Ginglymostoma cirratum (Carpet shark)

-- Glaucostegus (8 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_glaucostegus_cemiculus BOOLEAN DEFAULT FALSE; -- Glaucostegus cemiculus (Blackchin guitarfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_glaucostegus_granulatus BOOLEAN DEFAULT FALSE; -- Glaucostegus granulatus (Granulated guitarfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_glaucostegus_halavi BOOLEAN DEFAULT FALSE; -- Glaucostegus halavi (Halavi guitarfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_glaucostegus_microphthalmus BOOLEAN DEFAULT FALSE; -- Glaucostegus microphthalmus (Smalleyed guitarfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_glaucostegus_obtusus BOOLEAN DEFAULT FALSE; -- Glaucostegus obtusus (Blunt shovel nose ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_glaucostegus_spinosus BOOLEAN DEFAULT FALSE; -- Glaucostegus spinosus (Spiny guitarfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_glaucostegus_thouin BOOLEAN DEFAULT FALSE; -- Glaucostegus thouin (Clubnose guitarfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_glaucostegus_typus BOOLEAN DEFAULT FALSE; -- Glaucostegus typus (Austalian guitarfish)

-- Glyphis (5 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_glyphis_fowlerae BOOLEAN DEFAULT FALSE; -- Glyphis fowlerae (Borneo river shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_glyphis_gangeticus BOOLEAN DEFAULT FALSE; -- Glyphis gangeticus (Ganges shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_glyphis_garricki BOOLEAN DEFAULT FALSE; -- Glyphis garricki (Northern river shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_glyphis_glyphis BOOLEAN DEFAULT FALSE; -- Glyphis glyphis (Speartooth shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_glyphis_siamensis BOOLEAN DEFAULT FALSE; -- Glyphis siamensis (Irrawaddy river shark)

-- Gogolia (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_gogolia_filewoodi BOOLEAN DEFAULT FALSE; -- Gogolia filewoodi (Sailback hound shark)

-- Gollum (2 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_gollum_attenuatus BOOLEAN DEFAULT FALSE; -- Gollum attenuatus (Slender smooth hound)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_gollum_suluensis BOOLEAN DEFAULT FALSE; -- Gollum suluensis (Sulu Gollumshark)

-- Gurgesiella (3 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_gurgesiella_atlantica BOOLEAN DEFAULT FALSE; -- Gurgesiella atlantica (Atlantic pygmy skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_gurgesiella_dorsalifera BOOLEAN DEFAULT FALSE; -- Gurgesiella dorsalifera (Onefin skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_gurgesiella_furvescens BOOLEAN DEFAULT FALSE; -- Gurgesiella furvescens (Dusky finless skate)

-- Gymnura (12 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_gymnura_altavela BOOLEAN DEFAULT FALSE; -- Gymnura altavela (Butterfly ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_gymnura_australis BOOLEAN DEFAULT FALSE; -- Gymnura australis (Australian butterfly ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_gymnura_bimaculata BOOLEAN DEFAULT FALSE; -- Gymnura bimaculata (Twin-spot butterfly ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_gymnura_crebripunctata BOOLEAN DEFAULT FALSE; -- Gymnura crebripunctata (Butterfly ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_gymnura_hirundo BOOLEAN DEFAULT FALSE; -- Gymnura hirundo (Madeira butterfly ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_gymnura_japonica BOOLEAN DEFAULT FALSE; -- Gymnura japonica (Japanese butterfly ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_gymnura_marmorata BOOLEAN DEFAULT FALSE; -- Gymnura marmorata (California butterfly ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_gymnura_micrura BOOLEAN DEFAULT FALSE; -- Gymnura micrura (Butterfly ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_gymnura_natalensis BOOLEAN DEFAULT FALSE; -- Gymnura natalensis (Backwater butterfly ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_gymnura_poecilura BOOLEAN DEFAULT FALSE; -- Gymnura poecilura (Butterfly ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_gymnura_tentaculata BOOLEAN DEFAULT FALSE; -- Gymnura tentaculata (Tentacled butterfly ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_gymnura_zonura BOOLEAN DEFAULT FALSE; -- Gymnura zonura (Bleeker's butterfly ray)

-- Halaelurus (7 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_halaelurus_boesemani BOOLEAN DEFAULT FALSE; -- Halaelurus boesemani (Shortlip spotted catshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_halaelurus_buergeri BOOLEAN DEFAULT FALSE; -- Halaelurus buergeri (Black-spotted cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_halaelurus_lineatus BOOLEAN DEFAULT FALSE; -- Halaelurus lineatus (Banded catshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_halaelurus_maculosus BOOLEAN DEFAULT FALSE; -- Halaelurus maculosus (Indonesian Speckled Catshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_halaelurus_natalensis BOOLEAN DEFAULT FALSE; -- Halaelurus natalensis (Tiger cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_halaelurus_quagga BOOLEAN DEFAULT FALSE; -- Halaelurus quagga (Quagga cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_halaelurus_sellus BOOLEAN DEFAULT FALSE; -- Halaelurus sellus (Rusty Catshark)

-- Haploblepharus (3 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_haploblepharus_edwardsii BOOLEAN DEFAULT FALSE; -- Haploblepharus edwardsii (Dog fish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_haploblepharus_fuscus BOOLEAN DEFAULT FALSE; -- Haploblepharus fuscus (Brown shy shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_haploblepharus_pictus BOOLEAN DEFAULT FALSE; -- Haploblepharus pictus (Dark shy shark)

-- Harriotta (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_harriotta_raleighana BOOLEAN DEFAULT FALSE; -- Harriotta raleighana (Bent-nose chimaera)

-- Heliotrygon (2 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_heliotrygon_gomesi BOOLEAN DEFAULT FALSE; -- Heliotrygon gomesi (Gomes's round ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_heliotrygon_rosai BOOLEAN DEFAULT FALSE; -- Heliotrygon rosai (Rosa's round ray)

-- Hemigaleus (2 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_hemigaleus_australiensis BOOLEAN DEFAULT FALSE; -- Hemigaleus australiensis (Australian weasel shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_hemigaleus_microstoma BOOLEAN DEFAULT FALSE; -- Hemigaleus microstoma (Sicklefin weasel shark)

-- Hemipristis (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_hemipristis_elongata BOOLEAN DEFAULT FALSE; -- Hemipristis elongata (Elliot's gray shark)

-- Hemiscyllium (9 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_hemiscyllium_freycineti BOOLEAN DEFAULT FALSE; -- Hemiscyllium freycineti (Freycinet's shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_hemiscyllium_galei BOOLEAN DEFAULT FALSE; -- Hemiscyllium galei (Cenderwasih Epaulette shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_hemiscyllium_hallstromi BOOLEAN DEFAULT FALSE; -- Hemiscyllium hallstromi (Papuan epaulette shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_hemiscyllium_halmahera BOOLEAN DEFAULT FALSE; -- Hemiscyllium halmahera (Bamboo shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_hemiscyllium_henryi BOOLEAN DEFAULT FALSE; -- Hemiscyllium henryi (Triton Epaulette shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_hemiscyllium_michaeli BOOLEAN DEFAULT FALSE; -- Hemiscyllium michaeli (Leopard Epaulette shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_hemiscyllium_ocellatum BOOLEAN DEFAULT FALSE; -- Hemiscyllium ocellatum (Blind shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_hemiscyllium_strahani BOOLEAN DEFAULT FALSE; -- Hemiscyllium strahani (Hooded carpet shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_hemiscyllium_trispeculare BOOLEAN DEFAULT FALSE; -- Hemiscyllium trispeculare (Marbled catshark)

-- Hemitriakis (5 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_hemitriakis_abdita BOOLEAN DEFAULT FALSE; -- Hemitriakis abdita (Darksnout houndshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_hemitriakis_falcata BOOLEAN DEFAULT FALSE; -- Hemitriakis falcata (Sicklefin hound shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_hemitriakis_indroyonoi BOOLEAN DEFAULT FALSE; -- Hemitriakis indroyonoi (Indonesian Houndshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_hemitriakis_japanica BOOLEAN DEFAULT FALSE; -- Hemitriakis japanica (Japanese gray shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_hemitriakis_leucoperiptera BOOLEAN DEFAULT FALSE; -- Hemitriakis leucoperiptera (Whitefin tope shark)

-- Hemitrygon (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_hemitrygon_longicauda BOOLEAN DEFAULT FALSE; -- Hemitrygon longicauda (Merauke stingray)

-- Heptranchias (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_heptranchias_perlo BOOLEAN DEFAULT FALSE; -- Heptranchias perlo (7-gilled shark)

-- Heterodontus (9 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_heterodontus_francisci BOOLEAN DEFAULT FALSE; -- Heterodontus francisci (Horn shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_heterodontus_galeatus BOOLEAN DEFAULT FALSE; -- Heterodontus galeatus (Crested bull shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_heterodontus_japonicus BOOLEAN DEFAULT FALSE; -- Heterodontus japonicus (Bull-head shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_heterodontus_mexicanus BOOLEAN DEFAULT FALSE; -- Heterodontus mexicanus (Mexican horn shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_heterodontus_omanensis BOOLEAN DEFAULT FALSE; -- Heterodontus omanensis (Oman bullhead shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_heterodontus_portusjacksoni BOOLEAN DEFAULT FALSE; -- Heterodontus portusjacksoni (Bullhead)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_heterodontus_quoyi BOOLEAN DEFAULT FALSE; -- Heterodontus quoyi (Galapagos bullhead shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_heterodontus_ramalheira BOOLEAN DEFAULT FALSE; -- Heterodontus ramalheira (Heterodontus zebra)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_heterodontus_zebra BOOLEAN DEFAULT FALSE; -- Heterodontus zebra (Barred bull-head shark)

-- Heteronarce (4 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_heteronarce_bentuviai BOOLEAN DEFAULT FALSE; -- Heteronarce bentuviai (Eilat sleeper ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_heteronarce_garmani BOOLEAN DEFAULT FALSE; -- Heteronarce garmani (Natal electric ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_heteronarce_mollis BOOLEAN DEFAULT FALSE; -- Heteronarce mollis (Soft electric ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_heteronarce_prabhui BOOLEAN DEFAULT FALSE; -- Heteronarce prabhui (Quilon electric ray)

-- Heteroscymnoides (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_heteroscymnoides_marleyi BOOLEAN DEFAULT FALSE; -- Heteroscymnoides marleyi (Longnose pygmy shark)

-- Hexanchus (2 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_hexanchus_griseus BOOLEAN DEFAULT FALSE; -- Hexanchus griseus (6-gilled shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_hexanchus_nakamurai BOOLEAN DEFAULT FALSE; -- Hexanchus nakamurai (Bigeye Sixgill Shark)

-- Hexatrygon (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_hexatrygon_bickelli BOOLEAN DEFAULT FALSE; -- Hexatrygon bickelli (Sixgill stingray)

-- Himantura (5 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_himantura_australis BOOLEAN DEFAULT FALSE; -- Himantura australis (Australian whipray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_himantura_leoparda BOOLEAN DEFAULT FALSE; -- Himantura leoparda (Leopard whipray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_himantura_marginata BOOLEAN DEFAULT FALSE; -- Himantura marginata (Black-edge whipray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_himantura_uarnak BOOLEAN DEFAULT FALSE; -- Himantura uarnak (Banded whiptail stingray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_himantura_undulata BOOLEAN DEFAULT FALSE; -- Himantura undulata (Leopard whipray)

-- Holohalaelurus (3 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_holohalaelurus_melanostigma BOOLEAN DEFAULT FALSE; -- Holohalaelurus melanostigma (Crying Izak)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_holohalaelurus_punctatus BOOLEAN DEFAULT FALSE; -- Holohalaelurus punctatus (African spotted catshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_holohalaelurus_regani BOOLEAN DEFAULT FALSE; -- Holohalaelurus regani (Izak)

-- Hydrolagus (17 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_hydrolagus_affinis BOOLEAN DEFAULT FALSE; -- Hydrolagus affinis (Atlantic chimaera)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_hydrolagus_africanus BOOLEAN DEFAULT FALSE; -- Hydrolagus africanus (African chimaera)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_hydrolagus_bemisi BOOLEAN DEFAULT FALSE; -- Hydrolagus bemisi (Pale ghost shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_hydrolagus_colliei BOOLEAN DEFAULT FALSE; -- Hydrolagus colliei (Angel fish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_hydrolagus_deani BOOLEAN DEFAULT FALSE; -- Hydrolagus deani (Philippine chimaera)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_hydrolagus_erithacus BOOLEAN DEFAULT FALSE; -- Hydrolagus erithacus (Robin's ghostshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_hydrolagus_homonycteris BOOLEAN DEFAULT FALSE; -- Hydrolagus homonycteris (Black ghostshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_hydrolagus_macrophthalmus BOOLEAN DEFAULT FALSE; -- Hydrolagus macrophthalmus (Big eye chimaera)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_hydrolagus_matallanasi BOOLEAN DEFAULT FALSE; -- Hydrolagus matallanasi (Striped rabbitfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_hydrolagus_mccoskeri BOOLEAN DEFAULT FALSE; -- Hydrolagus mccoskeri (GalÃ¡pagos Ghost Shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_hydrolagus_melanophasma BOOLEAN DEFAULT FALSE; -- Hydrolagus melanophasma (Eastern Pacific Black Ghostshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_hydrolagus_mirabilis BOOLEAN DEFAULT FALSE; -- Hydrolagus mirabilis (Large-eyed rabbitfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_hydrolagus_mitsukurii BOOLEAN DEFAULT FALSE; -- Hydrolagus mitsukurii (Ghost shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_hydrolagus_novaezealandiae BOOLEAN DEFAULT FALSE; -- Hydrolagus novaezealandiae (Chimaera)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_hydrolagus_pallidus BOOLEAN DEFAULT FALSE; -- Hydrolagus pallidus (Ghost shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_hydrolagus_purpurescens BOOLEAN DEFAULT FALSE; -- Hydrolagus purpurescens (Purple chimaera)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_hydrolagus_trolli BOOLEAN DEFAULT FALSE; -- Hydrolagus trolli (Pointy-nosed blue chimaera)

-- Hypanus (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_hypanus_americanus BOOLEAN DEFAULT FALSE; -- Hypanus americanus (Southern stingray)

-- Hypnos (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_hypnos_monopterygius BOOLEAN DEFAULT FALSE; -- Hypnos monopterygius (Australian numbfish)

-- Hypogaleus (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_hypogaleus_hyugaensis BOOLEAN DEFAULT FALSE; -- Hypogaleus hyugaensis (Blacktip houndshark)

-- Iago (2 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_iago_garricki BOOLEAN DEFAULT FALSE; -- Iago garricki (Longnose hound shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_iago_omanensis BOOLEAN DEFAULT FALSE; -- Iago omanensis (Bigeye hound shark)

-- Insentiraja (2 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_insentiraja_laxipella BOOLEAN DEFAULT FALSE; -- Insentiraja laxipella (Eastern looseskin skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_insentiraja_subtilispinosa BOOLEAN DEFAULT FALSE; -- Insentiraja subtilispinosa (Velvet skate)

-- Irolita (2 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_irolita_waitii BOOLEAN DEFAULT FALSE; -- Irolita waitii (Round ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_irolita_westraliensis BOOLEAN DEFAULT FALSE; -- Irolita westraliensis (Western round skate)

-- Isistius (2 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_isistius_brasiliensis BOOLEAN DEFAULT FALSE; -- Isistius brasiliensis (Cigar shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_isistius_plutodus BOOLEAN DEFAULT FALSE; -- Isistius plutodus (Largetooth cookie-cutter shark)

-- Isogomphodon (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_isogomphodon_oxyrhynchus BOOLEAN DEFAULT FALSE; -- Isogomphodon oxyrhynchus (Daggernose shark)

-- Isurus (2 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_isurus_oxyrinchus BOOLEAN DEFAULT FALSE; -- Isurus oxyrinchus (Atlantic mako)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_isurus_paucus BOOLEAN DEFAULT FALSE; -- Isurus paucus (Long finned mako shark)

-- Lamiopsis (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_lamiopsis_temminckii BOOLEAN DEFAULT FALSE; -- Lamiopsis temminckii (Broadfin shark)

-- Lamna (2 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_lamna_ditropis BOOLEAN DEFAULT FALSE; -- Lamna ditropis (Mackerel shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_lamna_nasus BOOLEAN DEFAULT FALSE; -- Lamna nasus (Beaumaris shark)

-- Leptocharias (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_leptocharias_smithii BOOLEAN DEFAULT FALSE; -- Leptocharias smithii (Barbeled hound shark)

-- Leucoraja (14 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_leucoraja_caribbaea BOOLEAN DEFAULT FALSE; -- Leucoraja caribbaea (Maya skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_leucoraja_circularis BOOLEAN DEFAULT FALSE; -- Leucoraja circularis (Cuckoo ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_leucoraja_compagnoi BOOLEAN DEFAULT FALSE; -- Leucoraja compagnoi (Tigertail skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_leucoraja_fullonica BOOLEAN DEFAULT FALSE; -- Leucoraja fullonica (Dun cow)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_leucoraja_garmani BOOLEAN DEFAULT FALSE; -- Leucoraja garmani (Freckled skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_leucoraja_lentiginosa BOOLEAN DEFAULT FALSE; -- Leucoraja lentiginosa (Freckled skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_leucoraja_leucosticta BOOLEAN DEFAULT FALSE; -- Leucoraja leucosticta (Whitedappled skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_leucoraja_melitensis BOOLEAN DEFAULT FALSE; -- Leucoraja melitensis (Maltese brown ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_leucoraja_naevus BOOLEAN DEFAULT FALSE; -- Leucoraja naevus (Butterfly skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_leucoraja_ocellata BOOLEAN DEFAULT FALSE; -- Leucoraja ocellata (Big skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_leucoraja_pristispina BOOLEAN DEFAULT FALSE; -- Leucoraja pristispina (Sawback skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_leucoraja_virginica BOOLEAN DEFAULT FALSE; -- Leucoraja virginica (Virginia skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_leucoraja_wallacei BOOLEAN DEFAULT FALSE; -- Leucoraja wallacei (Blancmange skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_leucoraja_yucatanensis BOOLEAN DEFAULT FALSE; -- Leucoraja yucatanensis (Yucatan skate)

-- Loxodon (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_loxodon_macrorhinus BOOLEAN DEFAULT FALSE; -- Loxodon macrorhinus (Jordan's blue dogshark)

-- Lutjanus (2 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_lutjanus_analis BOOLEAN DEFAULT FALSE; -- Lutjanus analis (Mutton snapper)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_lutjanus_cyanopterus BOOLEAN DEFAULT FALSE; -- Lutjanus cyanopterus (Cuberra snapper)

-- Maculabatis (3 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_maculabatis_ambigua BOOLEAN DEFAULT FALSE; -- Maculabatis ambigua (Baraka"s whipray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_maculabatis_arabica BOOLEAN DEFAULT FALSE; -- Maculabatis arabica (Arabic whipray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_maculabatis_bineeshi BOOLEAN DEFAULT FALSE; -- Maculabatis bineeshi (Short-tail whipray)

-- Makararaja (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_makararaja_chindwinensis BOOLEAN DEFAULT FALSE; -- Makararaja chindwinensis (Chindwin cowtail ray)

-- Malacoraja (4 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_malacoraja_kreffti BOOLEAN DEFAULT FALSE; -- Malacoraja kreffti (Krefft's ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_malacoraja_obscura BOOLEAN DEFAULT FALSE; -- Malacoraja obscura (Brazilian soft skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_malacoraja_senta BOOLEAN DEFAULT FALSE; -- Malacoraja senta (Prickly skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_malacoraja_spinacidermis BOOLEAN DEFAULT FALSE; -- Malacoraja spinacidermis (Prickled ray)

-- Megachasma (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_megachasma_pelagios BOOLEAN DEFAULT FALSE; -- Megachasma pelagios (Megamouth shark)

-- Mitsukurina (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_mitsukurina_owstoni BOOLEAN DEFAULT FALSE; -- Mitsukurina owstoni (Elfin shark)

-- Mobula (9 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_mobula_eregoodootenkee BOOLEAN DEFAULT FALSE; -- Mobula eregoodootenkee (Devil ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_mobula_hypostoma BOOLEAN DEFAULT FALSE; -- Mobula hypostoma (Atlantic devil ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_mobula_japanica BOOLEAN DEFAULT FALSE; -- Mobula japanica (Devilray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_mobula_kuhlii BOOLEAN DEFAULT FALSE; -- Mobula kuhlii (Kuhl's devilray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_mobula_mobular BOOLEAN DEFAULT FALSE; -- Mobula mobular (Devil fish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_mobula_munkiana BOOLEAN DEFAULT FALSE; -- Mobula munkiana (Munk's devil ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_mobula_rochebrunei BOOLEAN DEFAULT FALSE; -- Mobula rochebrunei (Lesser Guinean devil ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_mobula_tarapacana BOOLEAN DEFAULT FALSE; -- Mobula tarapacana (Chilean devil ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_mobula_thurstoni BOOLEAN DEFAULT FALSE; -- Mobula thurstoni (Bentfin devil ray)

-- Mollisquama (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_mollisquama_parini BOOLEAN DEFAULT FALSE; -- Mollisquama parini (Pocket shark)

-- Mustelus (25 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_mustelus_albipinnis BOOLEAN DEFAULT FALSE; -- Mustelus albipinnis (Whitemargin smoothhound)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_mustelus_antarcticus BOOLEAN DEFAULT FALSE; -- Mustelus antarcticus (Australian smooth hound)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_mustelus_asterias BOOLEAN DEFAULT FALSE; -- Mustelus asterias (Smooth-hound)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_mustelus_californicus BOOLEAN DEFAULT FALSE; -- Mustelus californicus (Gray smooth-hound)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_mustelus_canis BOOLEAN DEFAULT FALSE; -- Mustelus canis (Atlantic smooth dogfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_mustelus_dorsalis BOOLEAN DEFAULT FALSE; -- Mustelus dorsalis (Sharp-tooth smooth hound)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_mustelus_fasciatus BOOLEAN DEFAULT FALSE; -- Mustelus fasciatus (Striped smooth hound)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_mustelus_griseus BOOLEAN DEFAULT FALSE; -- Mustelus griseus (Japanese gray smooth hound)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_mustelus_henlei BOOLEAN DEFAULT FALSE; -- Mustelus henlei (Brown smooth hound)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_mustelus_higmani BOOLEAN DEFAULT FALSE; -- Mustelus higmani (Smalleye smooth hound)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_mustelus_lenticulatus BOOLEAN DEFAULT FALSE; -- Mustelus lenticulatus (Gummy shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_mustelus_lunulatus BOOLEAN DEFAULT FALSE; -- Mustelus lunulatus (Sicklefin smooth hound)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_mustelus_manazo BOOLEAN DEFAULT FALSE; -- Mustelus manazo (Gummy dogfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_mustelus_mento BOOLEAN DEFAULT FALSE; -- Mustelus mento (Smooth hound)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_mustelus_mosis BOOLEAN DEFAULT FALSE; -- Mustelus mosis (Arabian smooth hound)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_mustelus_mustelus BOOLEAN DEFAULT FALSE; -- Mustelus mustelus (Gray mouth dog)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_mustelus_norrisi BOOLEAN DEFAULT FALSE; -- Mustelus norrisi (Florida smooth hound)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_mustelus_palumbes BOOLEAN DEFAULT FALSE; -- Mustelus palumbes (Smoothound)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_mustelus_punctulatus BOOLEAN DEFAULT FALSE; -- Mustelus punctulatus (Black spotted smooth hound)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_mustelus_ravidus BOOLEAN DEFAULT FALSE; -- Mustelus ravidus (Australian gray smooth-hound)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_mustelus_schmitti BOOLEAN DEFAULT FALSE; -- Mustelus schmitti (Narrownose smooth hound)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_mustelus_sinusmexicanus BOOLEAN DEFAULT FALSE; -- Mustelus sinusmexicanus (Gulf smoothhound)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_mustelus_stevensi BOOLEAN DEFAULT FALSE; -- Mustelus stevensi (Western spotted smoothhound)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_mustelus_whitneyi BOOLEAN DEFAULT FALSE; -- Mustelus whitneyi (Humpback smooth hound)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_mustelus_widodoi BOOLEAN DEFAULT FALSE; -- Mustelus widodoi (White-fin smooth-hound)

-- Myliobatis (11 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_myliobatis_aquila BOOLEAN DEFAULT FALSE; -- Myliobatis aquila (Common bull ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_myliobatis_australis BOOLEAN DEFAULT FALSE; -- Myliobatis australis (Australian bull ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_myliobatis_chilensis BOOLEAN DEFAULT FALSE; -- Myliobatis chilensis (Chilean eagle ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_myliobatis_freminvillei BOOLEAN DEFAULT FALSE; -- Myliobatis freminvillei (Blue-nosed ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_myliobatis_goodei BOOLEAN DEFAULT FALSE; -- Myliobatis goodei (Rockfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_myliobatis_hamlyni BOOLEAN DEFAULT FALSE; -- Myliobatis hamlyni (Hamlyn's bull-ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_myliobatis_longirostris BOOLEAN DEFAULT FALSE; -- Myliobatis longirostris (Longnose eagle ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_myliobatis_peruvianus BOOLEAN DEFAULT FALSE; -- Myliobatis peruvianus (Peruvian eagle ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_myliobatis_ridens BOOLEAN DEFAULT FALSE; -- Myliobatis ridens (Shortnose eagle ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_myliobatis_tenuicaudatus BOOLEAN DEFAULT FALSE; -- Myliobatis tenuicaudatus (Eagle ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_myliobatis_tobijei BOOLEAN DEFAULT FALSE; -- Myliobatis tobijei (Cowhead eagle ray)

-- Narcine (15 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_narcine_atzi BOOLEAN DEFAULT FALSE; -- Narcine atzi (Oman numbfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_narcine_baliensis BOOLEAN DEFAULT FALSE; -- Narcine baliensis (Indonesian numbfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_narcine_bancroftii BOOLEAN DEFAULT FALSE; -- Narcine bancroftii (Bancroft's numbfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_narcine_brasiliensis BOOLEAN DEFAULT FALSE; -- Narcine brasiliensis (Brazilian electric ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_narcine_brevilabiata BOOLEAN DEFAULT FALSE; -- Narcine brevilabiata (Shortlip electric ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_narcine_brunnea BOOLEAN DEFAULT FALSE; -- Narcine brunnea (Brown electric ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_narcine_entemedor BOOLEAN DEFAULT FALSE; -- Narcine entemedor (Cortez electric ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_narcine_insolita BOOLEAN DEFAULT FALSE; -- Narcine insolita (Madagascar numbfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_narcine_leoparda BOOLEAN DEFAULT FALSE; -- Narcine leoparda (Leopard numbfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_narcine_lingula BOOLEAN DEFAULT FALSE; -- Narcine lingula (Chinese numbfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_narcine_maculata BOOLEAN DEFAULT FALSE; -- Narcine maculata (Dark-spotted elctric ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_narcine_oculifera BOOLEAN DEFAULT FALSE; -- Narcine oculifera (Bigeye numbfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_narcine_prodorsalis BOOLEAN DEFAULT FALSE; -- Narcine prodorsalis (Tonkin electric ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_narcine_rierai BOOLEAN DEFAULT FALSE; -- Narcine rierai (Mozambique electric ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_narcine_timlei BOOLEAN DEFAULT FALSE; -- Narcine timlei (Black-spotted electric ray)

-- Narke (3 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_narke_capensis BOOLEAN DEFAULT FALSE; -- Narke capensis (Cape numbfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_narke_dipterygia BOOLEAN DEFAULT FALSE; -- Narke dipterygia (Numbray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_narke_japonica BOOLEAN DEFAULT FALSE; -- Narke japonica (Electric numb ray)

-- Nasolamia (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_nasolamia_velox BOOLEAN DEFAULT FALSE; -- Nasolamia velox (Requiem shark)

-- Nebrius (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_nebrius_ferrugineus BOOLEAN DEFAULT FALSE; -- Nebrius ferrugineus (Giant Sleepy -shark)

-- Negaprion (2 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_negaprion_acutidens BOOLEAN DEFAULT FALSE; -- Negaprion acutidens (Broadfin shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_negaprion_brevirostris BOOLEAN DEFAULT FALSE; -- Negaprion brevirostris (Lemon shark)

-- Neoharriotta (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_neoharriotta_pinnata BOOLEAN DEFAULT FALSE; -- Neoharriotta pinnata (Sicklefin chimaera)

-- Neoraja (5 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_neoraja_africana BOOLEAN DEFAULT FALSE; -- Neoraja africana (West African pygmy skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_neoraja_caerulea BOOLEAN DEFAULT FALSE; -- Neoraja caerulea (Blue pygmy skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_neoraja_carolinensis BOOLEAN DEFAULT FALSE; -- Neoraja carolinensis (Carolina pygmy skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_neoraja_iberica BOOLEAN DEFAULT FALSE; -- Neoraja iberica (Iberian pygmy skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_neoraja_stehmanni BOOLEAN DEFAULT FALSE; -- Neoraja stehmanni (African pygmy skate)

-- Neotrygon (7 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_neotrygon_annotata BOOLEAN DEFAULT FALSE; -- Neotrygon annotata (Brown stingray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_neotrygon_australiae BOOLEAN DEFAULT FALSE; -- Neotrygon australiae (Australian bluespotted maskray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_neotrygon_caeruleopunctata BOOLEAN DEFAULT FALSE; -- Neotrygon caeruleopunctata (Bluespotted maskray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_neotrygon_kuhlii BOOLEAN DEFAULT FALSE; -- Neotrygon kuhlii (Ble-spotted stingaree)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_neotrygon_leylandi BOOLEAN DEFAULT FALSE; -- Neotrygon leylandi (Brown-reticulate stingray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_neotrygon_orientalis BOOLEAN DEFAULT FALSE; -- Neotrygon orientalis (Oriental bluespotted maskray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_neotrygon_picta BOOLEAN DEFAULT FALSE; -- Neotrygon picta (Peppered maskray)

-- Notoraja (9 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_notoraja_alisae BOOLEAN DEFAULT FALSE; -- Notoraja alisae (Alis' velvet skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_notoraja_azurea BOOLEAN DEFAULT FALSE; -- Notoraja azurea (Blue skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_notoraja_hirticauda BOOLEAN DEFAULT FALSE; -- Notoraja hirticauda (Ghost skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_notoraja_martinezi BOOLEAN DEFAULT FALSE; -- Notoraja martinezi (Barbedwire-tailed skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_notoraja_ochroderma BOOLEAN DEFAULT FALSE; -- Notoraja ochroderma (Pale skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_notoraja_sapphira BOOLEAN DEFAULT FALSE; -- Notoraja sapphira (Sapphire Skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_notoraja_sereti BOOLEAN DEFAULT FALSE; -- Notoraja sereti (Papuan velvet skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_notoraja_sticta BOOLEAN DEFAULT FALSE; -- Notoraja sticta (Blotched skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_notoraja_tobitukai BOOLEAN DEFAULT FALSE; -- Notoraja tobitukai (Leadhued skate)

-- Notorynchus (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_notorynchus_cepedianus BOOLEAN DEFAULT FALSE; -- Notorynchus cepedianus (Bluntnose sevengill shark)

-- Odontaspis (2 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_odontaspis_ferox BOOLEAN DEFAULT FALSE; -- Odontaspis ferox (Bigeye sandtiger)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_odontaspis_noronhai BOOLEAN DEFAULT FALSE; -- Odontaspis noronhai (Bigeye sand shark)

-- Okamejei (11 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_okamejei_acutispina BOOLEAN DEFAULT FALSE; -- Okamejei acutispina (Sharpspine skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_okamejei_arafurensis BOOLEAN DEFAULT FALSE; -- Okamejei arafurensis (Arafura skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_okamejei_boesemani BOOLEAN DEFAULT FALSE; -- Okamejei boesemani (Black sand skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_okamejei_cairae BOOLEAN DEFAULT FALSE; -- Okamejei cairae (Borneo sand Skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_okamejei_heemstrai BOOLEAN DEFAULT FALSE; -- Okamejei heemstrai (East African skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_okamejei_hollandi BOOLEAN DEFAULT FALSE; -- Okamejei hollandi (Holland skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_okamejei_kenojei BOOLEAN DEFAULT FALSE; -- Okamejei kenojei (Ocellate spot skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_okamejei_leptoura BOOLEAN DEFAULT FALSE; -- Okamejei leptoura (Thintail skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_okamejei_meerdervoortii BOOLEAN DEFAULT FALSE; -- Okamejei meerdervoortii (Bigeye skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_okamejei_ornata BOOLEAN DEFAULT FALSE; -- Okamejei ornata (Ornate skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_okamejei_schmidti BOOLEAN DEFAULT FALSE; -- Okamejei schmidti (Browneye skate)

-- Orectolobus (10 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_orectolobus_floridus BOOLEAN DEFAULT FALSE; -- Orectolobus floridus (Floral banded wobbegong)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_orectolobus_halei BOOLEAN DEFAULT FALSE; -- Orectolobus halei (Banded wobbegong)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_orectolobus_hutchinsi BOOLEAN DEFAULT FALSE; -- Orectolobus hutchinsi (Western wobbegong)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_orectolobus_japonicus BOOLEAN DEFAULT FALSE; -- Orectolobus japonicus (Fringe shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_orectolobus_leptolineatus BOOLEAN DEFAULT FALSE; -- Orectolobus leptolineatus (Indonesian wobbegong)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_orectolobus_maculatus BOOLEAN DEFAULT FALSE; -- Orectolobus maculatus (Carpet shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_orectolobus_ornatus BOOLEAN DEFAULT FALSE; -- Orectolobus ornatus (Banded carpet shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_orectolobus_parvimaculatus BOOLEAN DEFAULT FALSE; -- Orectolobus parvimaculatus (Dwarf spotted wobbegong)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_orectolobus_reticulatus BOOLEAN DEFAULT FALSE; -- Orectolobus reticulatus (Network wobbegong)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_orectolobus_wardi BOOLEAN DEFAULT FALSE; -- Orectolobus wardi (North Australian wobbegong)

-- Oxynotus (5 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_oxynotus_bruniensis BOOLEAN DEFAULT FALSE; -- Oxynotus bruniensis (Pepeke)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_oxynotus_caribbaeus BOOLEAN DEFAULT FALSE; -- Oxynotus caribbaeus (Caribbean roughshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_oxynotus_centrina BOOLEAN DEFAULT FALSE; -- Oxynotus centrina (Angular rough shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_oxynotus_japonicus BOOLEAN DEFAULT FALSE; -- Oxynotus japonicus (Japanese roughshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_oxynotus_paradoxus BOOLEAN DEFAULT FALSE; -- Oxynotus paradoxus (Angular rough shark)

-- Paragaleus (3 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_paragaleus_leucolomatus BOOLEAN DEFAULT FALSE; -- Paragaleus leucolomatus (Whitetip weasel shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_paragaleus_pectoralis BOOLEAN DEFAULT FALSE; -- Paragaleus pectoralis (Atlantic weasel shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_paragaleus_tengi BOOLEAN DEFAULT FALSE; -- Paragaleus tengi (Straight-tooth weasel shark)

-- Parascyllium (5 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_parascyllium_collare BOOLEAN DEFAULT FALSE; -- Parascyllium collare (Collar carpetshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_parascyllium_elongatum BOOLEAN DEFAULT FALSE; -- Parascyllium elongatum (Elongate carpet shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_parascyllium_ferrugineum BOOLEAN DEFAULT FALSE; -- Parascyllium ferrugineum (Rusty carpet shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_parascyllium_sparsimaculatum BOOLEAN DEFAULT FALSE; -- Parascyllium sparsimaculatum (Ginger carpetshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_parascyllium_variolatum BOOLEAN DEFAULT FALSE; -- Parascyllium variolatum (Aried cat shark)

-- Paratrygon (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_paratrygon_aiereba BOOLEAN DEFAULT FALSE; -- Paratrygon aiereba (Discus ray)

-- Parmaturus (9 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_parmaturus_albimarginatus BOOLEAN DEFAULT FALSE; -- Parmaturus albimarginatus (White-tip Catshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_parmaturus_albipenis BOOLEAN DEFAULT FALSE; -- Parmaturus albipenis (White-clasper catshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_parmaturus_bigus BOOLEAN DEFAULT FALSE; -- Parmaturus bigus (Beige catshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_parmaturus_campechiensis BOOLEAN DEFAULT FALSE; -- Parmaturus campechiensis (Campeche cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_parmaturus_lanatus BOOLEAN DEFAULT FALSE; -- Parmaturus lanatus (Velvet catshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_parmaturus_macmillani BOOLEAN DEFAULT FALSE; -- Parmaturus macmillani (McMillan's cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_parmaturus_melanobranchus BOOLEAN DEFAULT FALSE; -- Parmaturus melanobranchus (Blackgill cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_parmaturus_pilosus BOOLEAN DEFAULT FALSE; -- Parmaturus pilosus (Salamander shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_parmaturus_xaniurus BOOLEAN DEFAULT FALSE; -- Parmaturus xaniurus (Filetail cat shark)

-- Pastinachus (4 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_pastinachus_gracilicaudus BOOLEAN DEFAULT FALSE; -- Pastinachus gracilicaudus (Narrowtail stingray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_pastinachus_sephen BOOLEAN DEFAULT FALSE; -- Pastinachus sephen (Banana-tail ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_pastinachus_solocirostris BOOLEAN DEFAULT FALSE; -- Pastinachus solocirostris (Roughnose stingray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_pastinachus_stellurostris BOOLEAN DEFAULT FALSE; -- Pastinachus stellurostris (Starrynose stingray)

-- Pateobatis (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_pateobatis_bleekeri BOOLEAN DEFAULT FALSE; -- Pateobatis bleekeri (Bleeker's whipray)

-- Pavoraja (6 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_pavoraja_alleni BOOLEAN DEFAULT FALSE; -- Pavoraja alleni (Allen's skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_pavoraja_arenaria BOOLEAN DEFAULT FALSE; -- Pavoraja arenaria (Sandy skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_pavoraja_mosaica BOOLEAN DEFAULT FALSE; -- Pavoraja mosaica (Mosaic skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_pavoraja_nitida BOOLEAN DEFAULT FALSE; -- Pavoraja nitida (Graceful skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_pavoraja_pseudonitida BOOLEAN DEFAULT FALSE; -- Pavoraja pseudonitida (False peacock skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_pavoraja_umbrosa BOOLEAN DEFAULT FALSE; -- Pavoraja umbrosa (Dusky skate)

-- Pentanchus (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_pentanchus_profundicolus BOOLEAN DEFAULT FALSE; -- Pentanchus profundicolus (Onefin catshark)

-- Planonasus (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_planonasus_parini BOOLEAN DEFAULT FALSE; -- Planonasus parini (Dwarf False Catshark)

-- Platyrhina (4 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_platyrhina_hyugaensis BOOLEAN DEFAULT FALSE; -- Platyrhina hyugaensis (Hyuga fanray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_platyrhina_psomadakisi BOOLEAN DEFAULT FALSE; -- Platyrhina psomadakisi (Indian fanray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_platyrhina_sinensis BOOLEAN DEFAULT FALSE; -- Platyrhina sinensis (Amoy fanray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_platyrhina_tangi BOOLEAN DEFAULT FALSE; -- Platyrhina tangi (Yellow-spotted fanray)

-- Platyrhinoidis (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_platyrhinoidis_triseriata BOOLEAN DEFAULT FALSE; -- Platyrhinoidis triseriata (Guitarfish)

-- Plesiobatis (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_plesiobatis_daviesi BOOLEAN DEFAULT FALSE; -- Plesiobatis daviesi (Davie's stingray)

-- Plesiotrygon (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_plesiotrygon_iwamae BOOLEAN DEFAULT FALSE; -- Plesiotrygon iwamae (Long-tailed river stingray)

-- Pliotrema (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_pliotrema_warreni BOOLEAN DEFAULT FALSE; -- Pliotrema warreni (Sixgill sawshark)

-- Poroderma (2 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_poroderma_africanum BOOLEAN DEFAULT FALSE; -- Poroderma africanum (Pyjama shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_poroderma_pantherinum BOOLEAN DEFAULT FALSE; -- Poroderma pantherinum (Barbeled catshark)

-- Potamotrygon (15 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_potamotrygon_brachyura BOOLEAN DEFAULT FALSE; -- Potamotrygon brachyura (Short-tailed river stingray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_potamotrygon_constellata BOOLEAN DEFAULT FALSE; -- Potamotrygon constellata (Thorny river stingray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_potamotrygon_falkneri BOOLEAN DEFAULT FALSE; -- Potamotrygon falkneri (Largespot river stingray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_potamotrygon_henlei BOOLEAN DEFAULT FALSE; -- Potamotrygon henlei (Bigtooth river stingray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_potamotrygon_histrix BOOLEAN DEFAULT FALSE; -- Potamotrygon histrix (Freshwater stingray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_potamotrygon_leopoldi BOOLEAN DEFAULT FALSE; -- Potamotrygon leopoldi (White-blotched river stingray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_potamotrygon_magdalenae BOOLEAN DEFAULT FALSE; -- Potamotrygon magdalenae (Magdalena river stingray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_potamotrygon_motoro BOOLEAN DEFAULT FALSE; -- Potamotrygon motoro (Black river stingray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_potamotrygon_ocellata BOOLEAN DEFAULT FALSE; -- Potamotrygon ocellata (Red-blotched river stingray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_potamotrygon_orbignyi BOOLEAN DEFAULT FALSE; -- Potamotrygon orbignyi (Anglespot river stingray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_potamotrygon_rex BOOLEAN DEFAULT FALSE; -- Potamotrygon rex (Great freshwater stingray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_potamotrygon_schroederi BOOLEAN DEFAULT FALSE; -- Potamotrygon schroederi (Rosette river stingray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_potamotrygon_scobina BOOLEAN DEFAULT FALSE; -- Potamotrygon scobina (Raspy river stingray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_potamotrygon_signata BOOLEAN DEFAULT FALSE; -- Potamotrygon signata (Parnaiba river stingray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_potamotrygon_yepezi BOOLEAN DEFAULT FALSE; -- Potamotrygon yepezi (Maracaibo river stingray)

-- Prionace (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_prionace_glauca BOOLEAN DEFAULT FALSE; -- Prionace glauca (Blue dog)

-- Pristiophorus (7 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_pristiophorus_cirratus BOOLEAN DEFAULT FALSE; -- Pristiophorus cirratus (Common sawshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_pristiophorus_delicatus BOOLEAN DEFAULT FALSE; -- Pristiophorus delicatus (Tropical sawshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_pristiophorus_japonicus BOOLEAN DEFAULT FALSE; -- Pristiophorus japonicus (Halberd shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_pristiophorus_lanae BOOLEAN DEFAULT FALSE; -- Pristiophorus lanae (Lana's Sawshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_pristiophorus_nancyae BOOLEAN DEFAULT FALSE; -- Pristiophorus nancyae (African dwarf sawshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_pristiophorus_nudipinnis BOOLEAN DEFAULT FALSE; -- Pristiophorus nudipinnis (Doggies)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_pristiophorus_schroederi BOOLEAN DEFAULT FALSE; -- Pristiophorus schroederi (Bahamas saw shark)

-- Pristis (4 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_pristis_clavata BOOLEAN DEFAULT FALSE; -- Pristis clavata (Dwarf sawfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_pristis_pectinata BOOLEAN DEFAULT FALSE; -- Pristis pectinata (Comb shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_pristis_pristis BOOLEAN DEFAULT FALSE; -- Pristis pristis (Common sawfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_pristis_zijsron BOOLEAN DEFAULT FALSE; -- Pristis zijsron (Dindagubba)

-- Proscyllium (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_proscyllium_habereri BOOLEAN DEFAULT FALSE; -- Proscyllium habereri (Graceful cat shark)

-- Psammobatis (8 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_psammobatis_bergi BOOLEAN DEFAULT FALSE; -- Psammobatis bergi (Blotched sand skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_psammobatis_extenta BOOLEAN DEFAULT FALSE; -- Psammobatis extenta (Zipper sand skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_psammobatis_lentiginosa BOOLEAN DEFAULT FALSE; -- Psammobatis lentiginosa (Freckled sand skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_psammobatis_normani BOOLEAN DEFAULT FALSE; -- Psammobatis normani (Shortfin sand skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_psammobatis_parvacauda BOOLEAN DEFAULT FALSE; -- Psammobatis parvacauda (Smalltail sand skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_psammobatis_rudis BOOLEAN DEFAULT FALSE; -- Psammobatis rudis (Smallthorn sand skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_psammobatis_rutrum BOOLEAN DEFAULT FALSE; -- Psammobatis rutrum (Spade sand skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_psammobatis_scobina BOOLEAN DEFAULT FALSE; -- Psammobatis scobina (Raspthorn sand skate)

-- Pseudocarcharias (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_pseudocarcharias_kamoharai BOOLEAN DEFAULT FALSE; -- Pseudocarcharias kamoharai (Crocodile shark)

-- Pseudoginglymostoma (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_pseudoginglymostoma_brevicaudatum BOOLEAN DEFAULT FALSE; -- Pseudoginglymostoma brevicaudatum (Short-tail nurse shark)

-- Pseudoraja (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_pseudoraja_fischeri BOOLEAN DEFAULT FALSE; -- Pseudoraja fischeri (Fanfin skate)

-- Pseudotriakis (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_pseudotriakis_microdon BOOLEAN DEFAULT FALSE; -- Pseudotriakis microdon (False cat shark)

-- Pteroplatytrygon (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_pteroplatytrygon_violacea BOOLEAN DEFAULT FALSE; -- Pteroplatytrygon violacea (Blue stingray)

-- Raja (19 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_raja_ackleyi BOOLEAN DEFAULT FALSE; -- Raja ackleyi (Ocellate skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_raja_asterias BOOLEAN DEFAULT FALSE; -- Raja asterias (Atlantic starry skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_raja_bahamensis BOOLEAN DEFAULT FALSE; -- Raja bahamensis (Bahama skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_raja_brachyura BOOLEAN DEFAULT FALSE; -- Raja brachyura (Blonde)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_raja_cervigoni BOOLEAN DEFAULT FALSE; -- Raja cervigoni (Finspot ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_raja_clavata BOOLEAN DEFAULT FALSE; -- Raja clavata (Maiden ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_raja_equatorialis BOOLEAN DEFAULT FALSE; -- Raja equatorialis (Ecuatorial ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_raja_herwigi BOOLEAN DEFAULT FALSE; -- Raja herwigi (Cape Verde skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_raja_maderensis BOOLEAN DEFAULT FALSE; -- Raja maderensis (Madeira ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_raja_microocellata BOOLEAN DEFAULT FALSE; -- Raja microocellata (Owl ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_raja_miraletus BOOLEAN DEFAULT FALSE; -- Raja miraletus (Brown ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_raja_montagui BOOLEAN DEFAULT FALSE; -- Raja montagui (Homelyn ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_raja_parva BOOLEAN DEFAULT FALSE; -- Raja parva (African brown skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_raja_polystigma BOOLEAN DEFAULT FALSE; -- Raja polystigma (Speckled ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_raja_radula BOOLEAN DEFAULT FALSE; -- Raja radula (Rough ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_raja_rondeleti BOOLEAN DEFAULT FALSE; -- Raja rondeleti (Rondelet's ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_raja_straeleni BOOLEAN DEFAULT FALSE; -- Raja straeleni (Biscuit skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_raja_texana BOOLEAN DEFAULT FALSE; -- Raja texana (Roundel skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_raja_undulata BOOLEAN DEFAULT FALSE; -- Raja undulata (Painted ray)

-- Rajella (17 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rajella_annandalei BOOLEAN DEFAULT FALSE; -- Rajella annandalei (Annandale's skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rajella_barnardi BOOLEAN DEFAULT FALSE; -- Rajella barnardi (Bigthorn skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rajella_bathyphila BOOLEAN DEFAULT FALSE; -- Rajella bathyphila (Abyssal skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rajella_bigelowi BOOLEAN DEFAULT FALSE; -- Rajella bigelowi (Bigelow's ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rajella_caudaspinosa BOOLEAN DEFAULT FALSE; -- Rajella caudaspinosa (Munchkin skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rajella_challengeri BOOLEAN DEFAULT FALSE; -- Rajella challengeri (Challenger skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rajella_dissimilis BOOLEAN DEFAULT FALSE; -- Rajella dissimilis (Ghost skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rajella_eisenhardti BOOLEAN DEFAULT FALSE; -- Rajella eisenhardti (Galapagos gray skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rajella_fuliginea BOOLEAN DEFAULT FALSE; -- Rajella fuliginea (Sooty skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rajella_fyllae BOOLEAN DEFAULT FALSE; -- Rajella fyllae (Nova Scotia skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rajella_kukujevi BOOLEAN DEFAULT FALSE; -- Rajella kukujevi (Mid-Atlantic skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rajella_lintea BOOLEAN DEFAULT FALSE; -- Rajella lintea (Linen skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rajella_nigerrima BOOLEAN DEFAULT FALSE; -- Rajella nigerrima (Blackish skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rajella_paucispinosa BOOLEAN DEFAULT FALSE; -- Rajella paucispinosa (Sparsely-thorned skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rajella_purpuriventralis BOOLEAN DEFAULT FALSE; -- Rajella purpuriventralis (Purplebelly skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rajella_ravidula BOOLEAN DEFAULT FALSE; -- Rajella ravidula (Smoothback skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rajella_sadowskii BOOLEAN DEFAULT FALSE; -- Rajella sadowskii (Brazilian skate)

-- Remora (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_remora_remora BOOLEAN DEFAULT FALSE; -- Remora remora (Remora)

-- Rhincodon (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rhincodon_typus BOOLEAN DEFAULT FALSE; -- Rhincodon typus (Basking shark)

-- Rhinobatos (16 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rhinobatos_albomaculatus BOOLEAN DEFAULT FALSE; -- Rhinobatos albomaculatus (White-spotted guitarfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rhinobatos_annandalei BOOLEAN DEFAULT FALSE; -- Rhinobatos annandalei (Annandale's guitarfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rhinobatos_borneensis BOOLEAN DEFAULT FALSE; -- Rhinobatos borneensis (Borneo guitarfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rhinobatos_formosensis BOOLEAN DEFAULT FALSE; -- Rhinobatos formosensis (Taiwan guitarfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rhinobatos_holcorhynchus BOOLEAN DEFAULT FALSE; -- Rhinobatos holcorhynchus (Slender guitarfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rhinobatos_hynnicephalus BOOLEAN DEFAULT FALSE; -- Rhinobatos hynnicephalus (Angel fish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rhinobatos_irvinei BOOLEAN DEFAULT FALSE; -- Rhinobatos irvinei (Spineback guitarfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rhinobatos_jimbaranensis BOOLEAN DEFAULT FALSE; -- Rhinobatos jimbaranensis (Jimbaran shovelnose ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rhinobatos_lionotus BOOLEAN DEFAULT FALSE; -- Rhinobatos lionotus (Norman's shovelnose ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rhinobatos_manai BOOLEAN DEFAULT FALSE; -- Rhinobatos manai (Papuan guitarfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rhinobatos_penggali BOOLEAN DEFAULT FALSE; -- Rhinobatos penggali (Indonesian shovelnose ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rhinobatos_punctifer BOOLEAN DEFAULT FALSE; -- Rhinobatos punctifer (Spotted guitarfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rhinobatos_rhinobatos BOOLEAN DEFAULT FALSE; -- Rhinobatos rhinobatos (Common guitarfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rhinobatos_sainsburyi BOOLEAN DEFAULT FALSE; -- Rhinobatos sainsburyi (Goldeneye shovelnose)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rhinobatos_schlegelii BOOLEAN DEFAULT FALSE; -- Rhinobatos schlegelii (Beaked guitar fish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rhinobatos_whitei BOOLEAN DEFAULT FALSE; -- Rhinobatos whitei (Philippine guitarfish)

-- Rhinochimaera (3 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rhinochimaera_africana BOOLEAN DEFAULT FALSE; -- Rhinochimaera africana (Paddlenose chimaera)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rhinochimaera_atlantica BOOLEAN DEFAULT FALSE; -- Rhinochimaera atlantica (Atlantic knife-nose chimaera)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rhinochimaera_pacifica BOOLEAN DEFAULT FALSE; -- Rhinochimaera pacifica (Deep-sea chimaera)

-- Rhinoptera (7 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rhinoptera_bonasus BOOLEAN DEFAULT FALSE; -- Rhinoptera bonasus (American cownose ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rhinoptera_brasiliensis BOOLEAN DEFAULT FALSE; -- Rhinoptera brasiliensis (Brazilian cow-nose ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rhinoptera_javanica BOOLEAN DEFAULT FALSE; -- Rhinoptera javanica (Cownose ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rhinoptera_jayakari BOOLEAN DEFAULT FALSE; -- Rhinoptera jayakari (Oman cownose ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rhinoptera_marginata BOOLEAN DEFAULT FALSE; -- Rhinoptera marginata (Lusitanian cow-nose ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rhinoptera_neglecta BOOLEAN DEFAULT FALSE; -- Rhinoptera neglecta (Australian cow-nose ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rhinoptera_steindachneri BOOLEAN DEFAULT FALSE; -- Rhinoptera steindachneri (Cow-nosed ray)

-- Rhinoraja (3 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rhinoraja_kujiensis BOOLEAN DEFAULT FALSE; -- Rhinoraja kujiensis (Dapple-bellied softnose skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rhinoraja_longicauda BOOLEAN DEFAULT FALSE; -- Rhinoraja longicauda (White-bellied softnose skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rhinoraja_odai BOOLEAN DEFAULT FALSE; -- Rhinoraja odai (Oda's skate)

-- Rhizoprionodon (7 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rhizoprionodon_acutus BOOLEAN DEFAULT FALSE; -- Rhizoprionodon acutus (Fish shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rhizoprionodon_lalandii BOOLEAN DEFAULT FALSE; -- Rhizoprionodon lalandii (Brazilian sharpnose shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rhizoprionodon_longurio BOOLEAN DEFAULT FALSE; -- Rhizoprionodon longurio (Pacific sharp-nosed shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rhizoprionodon_oligolinx BOOLEAN DEFAULT FALSE; -- Rhizoprionodon oligolinx (Gray dog shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rhizoprionodon_porosus BOOLEAN DEFAULT FALSE; -- Rhizoprionodon porosus (Atlantic sharpnose shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rhizoprionodon_taylori BOOLEAN DEFAULT FALSE; -- Rhizoprionodon taylori (Australian sharpnose shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rhizoprionodon_terraenovae BOOLEAN DEFAULT FALSE; -- Rhizoprionodon terraenovae (Atlantic sharp-nosed shark)

-- Rhynchobatus (8 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rhynchobatus_australiae BOOLEAN DEFAULT FALSE; -- Rhynchobatus australiae (Bottlenose wedgefish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rhynchobatus_cooki BOOLEAN DEFAULT FALSE; -- Rhynchobatus cooki (Clown wedgefish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rhynchobatus_djiddensis BOOLEAN DEFAULT FALSE; -- Rhynchobatus djiddensis (Giant guitarfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rhynchobatus_immaculatus BOOLEAN DEFAULT FALSE; -- Rhynchobatus immaculatus (Taiwanese Wedgefish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rhynchobatus_laevis BOOLEAN DEFAULT FALSE; -- Rhynchobatus laevis (Smooth nose wedgefish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rhynchobatus_luebberti BOOLEAN DEFAULT FALSE; -- Rhynchobatus luebberti (African wedgefish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rhynchobatus_palpebratus BOOLEAN DEFAULT FALSE; -- Rhynchobatus palpebratus (Eyebrow wedgefish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rhynchobatus_springeri BOOLEAN DEFAULT FALSE; -- Rhynchobatus springeri (Broadnose wedgefish)

-- Rhynchorhina (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rhynchorhina_mauritaniensis BOOLEAN DEFAULT FALSE; -- Rhynchorhina mauritaniensis (False shark ray)

-- Rioraja (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rioraja_agassizii BOOLEAN DEFAULT FALSE; -- Rioraja agassizii (Rio skate)

-- Rostroraja (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_rostroraja_alba BOOLEAN DEFAULT FALSE; -- Rostroraja alba (Bordered ray)

-- Schroederichthys (5 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_schroederichthys_bivius BOOLEAN DEFAULT FALSE; -- Schroederichthys bivius (Narrowmouth cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_schroederichthys_chilensis BOOLEAN DEFAULT FALSE; -- Schroederichthys chilensis (Red-spotted cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_schroederichthys_maculatus BOOLEAN DEFAULT FALSE; -- Schroederichthys maculatus (Narrowtail cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_schroederichthys_saurisqualus BOOLEAN DEFAULT FALSE; -- Schroederichthys saurisqualus (Lizard catshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_schroederichthys_tenuis BOOLEAN DEFAULT FALSE; -- Schroederichthys tenuis (Narrowmouthed catshark)

-- Scoliodon (2 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_scoliodon_laticaudus BOOLEAN DEFAULT FALSE; -- Scoliodon laticaudus (Dog shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_scoliodon_macrorhynchos BOOLEAN DEFAULT FALSE; -- Scoliodon macrorhynchos (Pacific spadenose shark)

-- Scyliorhinus (14 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_scyliorhinus_besnardi BOOLEAN DEFAULT FALSE; -- Scyliorhinus besnardi (Polka-dot cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_scyliorhinus_boa BOOLEAN DEFAULT FALSE; -- Scyliorhinus boa (Boa cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_scyliorhinus_canicula BOOLEAN DEFAULT FALSE; -- Scyliorhinus canicula (Dogfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_scyliorhinus_capensis BOOLEAN DEFAULT FALSE; -- Scyliorhinus capensis (Yellow-spotted cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_scyliorhinus_cervigoni BOOLEAN DEFAULT FALSE; -- Scyliorhinus cervigoni (Nurse hound)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_scyliorhinus_comoroensis BOOLEAN DEFAULT FALSE; -- Scyliorhinus comoroensis (Comoro cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_scyliorhinus_garmani BOOLEAN DEFAULT FALSE; -- Scyliorhinus garmani (Brown-spotted cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_scyliorhinus_haeckelii BOOLEAN DEFAULT FALSE; -- Scyliorhinus haeckelii (Freckled cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_scyliorhinus_hesperius BOOLEAN DEFAULT FALSE; -- Scyliorhinus hesperius (White-saddled cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_scyliorhinus_meadi BOOLEAN DEFAULT FALSE; -- Scyliorhinus meadi (Blotched cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_scyliorhinus_retifer BOOLEAN DEFAULT FALSE; -- Scyliorhinus retifer (Chain cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_scyliorhinus_stellaris BOOLEAN DEFAULT FALSE; -- Scyliorhinus stellaris (Bull huss)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_scyliorhinus_torazame BOOLEAN DEFAULT FALSE; -- Scyliorhinus torazame (Cloudy cat shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_scyliorhinus_torrei BOOLEAN DEFAULT FALSE; -- Scyliorhinus torrei (Cat shark)

-- Scylliogaleus (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_scylliogaleus_quecketti BOOLEAN DEFAULT FALSE; -- Scylliogaleus quecketti (Flapnose houndshark)

-- Scymnodalatias (4 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_scymnodalatias_albicauda BOOLEAN DEFAULT FALSE; -- Scymnodalatias albicauda (Whitetail dogfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_scymnodalatias_garricki BOOLEAN DEFAULT FALSE; -- Scymnodalatias garricki (Azores dogfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_scymnodalatias_oligodon BOOLEAN DEFAULT FALSE; -- Scymnodalatias oligodon (Sparsetooth dogfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_scymnodalatias_sherwoodi BOOLEAN DEFAULT FALSE; -- Scymnodalatias sherwoodi (Sherwood dogfish)

-- Scymnodon (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_scymnodon_ringens BOOLEAN DEFAULT FALSE; -- Scymnodon ringens (Knifetooth dogfish)

-- Serranidae (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_serranidae_NA BOOLEAN DEFAULT FALSE; -- Serranidae (Grouper)

-- Sinobatis (7 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_sinobatis_andamanensis BOOLEAN DEFAULT FALSE; -- Sinobatis andamanensis (Andaman legskate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_sinobatis_borneensis BOOLEAN DEFAULT FALSE; -- Sinobatis borneensis (Borneo leg skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_sinobatis_brevicauda BOOLEAN DEFAULT FALSE; -- Sinobatis brevicauda (Shorttail legskate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_sinobatis_bulbicauda BOOLEAN DEFAULT FALSE; -- Sinobatis bulbicauda (Western Australian Legskate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_sinobatis_caerulea BOOLEAN DEFAULT FALSE; -- Sinobatis caerulea (Blue Legskate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_sinobatis_filicauda BOOLEAN DEFAULT FALSE; -- Sinobatis filicauda (Eastern Australian legskate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_sinobatis_melanosoma BOOLEAN DEFAULT FALSE; -- Sinobatis melanosoma (Blackbodied leg skate)

-- Somniosus (5 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_somniosus_antarcticus BOOLEAN DEFAULT FALSE; -- Somniosus antarcticus (Greenland shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_somniosus_longus BOOLEAN DEFAULT FALSE; -- Somniosus longus (Frog shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_somniosus_microcephalus BOOLEAN DEFAULT FALSE; -- Somniosus microcephalus (Greenland shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_somniosus_pacificus BOOLEAN DEFAULT FALSE; -- Somniosus pacificus (Pacific Sleeper Shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_somniosus_rostratus BOOLEAN DEFAULT FALSE; -- Somniosus rostratus (Little Sleeper Shark)

-- Sphyraena (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_sphyraena_barracuda BOOLEAN DEFAULT FALSE; -- Sphyraena barracuda (Barracuda)

-- Sphyrna (8 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_sphyrna_corona BOOLEAN DEFAULT FALSE; -- Sphyrna corona (Hammerhead)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_sphyrna_gilberti BOOLEAN DEFAULT FALSE; -- Sphyrna gilberti (Carolina hammerhead)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_sphyrna_lewini BOOLEAN DEFAULT FALSE; -- Sphyrna lewini (Bronze hammerhead shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_sphyrna_media BOOLEAN DEFAULT FALSE; -- Sphyrna media (Scoophead shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_sphyrna_mokarran BOOLEAN DEFAULT FALSE; -- Sphyrna mokarran (Great hammerhead)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_sphyrna_tiburo BOOLEAN DEFAULT FALSE; -- Sphyrna tiburo (Bonnet hammerhead)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_sphyrna_tudes BOOLEAN DEFAULT FALSE; -- Sphyrna tudes (Bonnet)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_sphyrna_zygaena BOOLEAN DEFAULT FALSE; -- Sphyrna zygaena (Common hammerhead)

-- Spiniraja (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_spiniraja_whitleyi BOOLEAN DEFAULT FALSE; -- Spiniraja whitleyi (Great skate)

-- Squaliolus (2 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_squaliolus_aliae BOOLEAN DEFAULT FALSE; -- Squaliolus aliae (Smalleye pigmy shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_squaliolus_laticaudus BOOLEAN DEFAULT FALSE; -- Squaliolus laticaudus (Dwarf shark)

-- Squalus (30 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_squalus_acanthias BOOLEAN DEFAULT FALSE; -- Squalus acanthias (Blue dog)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_squalus_albicaudus BOOLEAN DEFAULT FALSE; -- Squalus albicaudus (Brazilian whitetail dogfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_squalus_albifrons BOOLEAN DEFAULT FALSE; -- Squalus albifrons (Eastern highfin spurdog)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_squalus_altipinnis BOOLEAN DEFAULT FALSE; -- Squalus altipinnis (Western highfin spurdog)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_squalus_bahiensis BOOLEAN DEFAULT FALSE; -- Squalus bahiensis (Northeastern Brazilian dogfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_squalus_blainville BOOLEAN DEFAULT FALSE; -- Squalus blainville (Bigeye dogfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_squalus_brevirostris BOOLEAN DEFAULT FALSE; -- Squalus brevirostris (Shortnose dogfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_squalus_bucephalus BOOLEAN DEFAULT FALSE; -- Squalus bucephalus (Bighead spurdog)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_squalus_chloroculus BOOLEAN DEFAULT FALSE; -- Squalus chloroculus (Greeneye spurdog)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_squalus_crassispinus BOOLEAN DEFAULT FALSE; -- Squalus crassispinus (Fatspine spurdog)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_squalus_cubensis BOOLEAN DEFAULT FALSE; -- Squalus cubensis (Cuban dogfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_squalus_edmundsi BOOLEAN DEFAULT FALSE; -- Squalus edmundsi (Edmund's spurdog)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_squalus_formosus BOOLEAN DEFAULT FALSE; -- Squalus formosus (Taiwan spurdog)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_squalus_grahami BOOLEAN DEFAULT FALSE; -- Squalus grahami (Eastern longnose spurdog)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_squalus_griffini BOOLEAN DEFAULT FALSE; -- Squalus griffini (Green-eyed dogfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_squalus_hemipinnis BOOLEAN DEFAULT FALSE; -- Squalus hemipinnis (Indonesian shortsnout spurdog)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_squalus_japonicus BOOLEAN DEFAULT FALSE; -- Squalus japonicus (Japanese spurdog)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_squalus_lobularis BOOLEAN DEFAULT FALSE; -- Squalus lobularis (Atlantic lobefin dogfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_squalus_mahia BOOLEAN DEFAULT FALSE; -- Squalus mahia (Malagasy skinny spurdog)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_squalus_margaretsmithae BOOLEAN DEFAULT FALSE; -- Squalus margaretsmithae (Smith's dogfish shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_squalus_megalops BOOLEAN DEFAULT FALSE; -- Squalus megalops (Bluntnose spiny dogfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_squalus_melanurus BOOLEAN DEFAULT FALSE; -- Squalus melanurus (Blacktail spurdog)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_squalus_mitsukurii BOOLEAN DEFAULT FALSE; -- Squalus mitsukurii (Blainvilles dogfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_squalus_montalbani BOOLEAN DEFAULT FALSE; -- Squalus montalbani (Indonesian greeneye spurdog)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_squalus_nasutus BOOLEAN DEFAULT FALSE; -- Squalus nasutus (Western longnose spurdog)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_squalus_notocaudatus BOOLEAN DEFAULT FALSE; -- Squalus notocaudatus (Bartail spurdog)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_squalus_quasimodo BOOLEAN DEFAULT FALSE; -- Squalus quasimodo (Humpback Western dogfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_squalus_rancureli BOOLEAN DEFAULT FALSE; -- Squalus rancureli (Cyrano spurdog)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_squalus_raoulensis BOOLEAN DEFAULT FALSE; -- Squalus raoulensis (Kermadec spiny dogfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_squalus_suckleyi BOOLEAN DEFAULT FALSE; -- Squalus suckleyi (Dogfish)

-- Squatina (20 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_squatina_aculeata BOOLEAN DEFAULT FALSE; -- Squatina aculeata (Sawback angel shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_squatina_africana BOOLEAN DEFAULT FALSE; -- Squatina africana (African angel shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_squatina_albipunctata BOOLEAN DEFAULT FALSE; -- Squatina albipunctata (Eastern Angel Shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_squatina_argentina BOOLEAN DEFAULT FALSE; -- Squatina argentina (Argentine Angel shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_squatina_armata BOOLEAN DEFAULT FALSE; -- Squatina armata (Angel shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_squatina_australis BOOLEAN DEFAULT FALSE; -- Squatina australis (Angel shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_squatina_californica BOOLEAN DEFAULT FALSE; -- Squatina californica (Angel shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_squatina_david BOOLEAN DEFAULT FALSE; -- Squatina david (David's Angel Shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_squatina_dumeril BOOLEAN DEFAULT FALSE; -- Squatina dumeril (Angel shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_squatina_formosa BOOLEAN DEFAULT FALSE; -- Squatina formosa (Taiwan angel shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_squatina_guggenheim BOOLEAN DEFAULT FALSE; -- Squatina guggenheim (Angular angel shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_squatina_japonica BOOLEAN DEFAULT FALSE; -- Squatina japonica (Change angel shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_squatina_legnota BOOLEAN DEFAULT FALSE; -- Squatina legnota (Indonesian Angel Shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_squatina_nebulosa BOOLEAN DEFAULT FALSE; -- Squatina nebulosa (Angel ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_squatina_occulta BOOLEAN DEFAULT FALSE; -- Squatina occulta (Argentine angelshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_squatina_oculata BOOLEAN DEFAULT FALSE; -- Squatina oculata (Monk fish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_squatina_pseudocellata BOOLEAN DEFAULT FALSE; -- Squatina pseudocellata (Western Angel Shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_squatina_squatina BOOLEAN DEFAULT FALSE; -- Squatina squatina (Angel)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_squatina_tergocellata BOOLEAN DEFAULT FALSE; -- Squatina tergocellata (Angel shark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_squatina_tergocellatoides BOOLEAN DEFAULT FALSE; -- Squatina tergocellatoides (Ocellated angelshark)

-- Sutorectus (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_sutorectus_tentaculatus BOOLEAN DEFAULT FALSE; -- Sutorectus tentaculatus (Cobbler carpet shark)

-- Sympterygia (4 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_sympterygia_acuta BOOLEAN DEFAULT FALSE; -- Sympterygia acuta (Bignose fanskate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_sympterygia_bonapartii BOOLEAN DEFAULT FALSE; -- Sympterygia bonapartii (Smallnose fanskate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_sympterygia_brevicaudata BOOLEAN DEFAULT FALSE; -- Sympterygia brevicaudata (Pacific skate)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_sympterygia_lima BOOLEAN DEFAULT FALSE; -- Sympterygia lima (Filetail fanskate)

-- Taeniura (2 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_taeniura_lessoni BOOLEAN DEFAULT FALSE; -- Taeniura lessoni (Oceania fantail ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_taeniura_lymma BOOLEAN DEFAULT FALSE; -- Taeniura lymma (Blue spotted lagoon ray)

-- Taeniurops (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_taeniurops_meyeni BOOLEAN DEFAULT FALSE; -- Taeniurops meyeni (Black spotted ray)

-- Telatrygon (2 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_telatrygon_biasa BOOLEAN DEFAULT FALSE; -- Telatrygon biasa (Common ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_telatrygon_crozieri BOOLEAN DEFAULT FALSE; -- Telatrygon crozieri (Indian sharpnose ray)

-- Temera (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_temera_hardwickii BOOLEAN DEFAULT FALSE; -- Temera hardwickii (Electric ray)

-- Tetronarce (2 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_tetronarce_cowleyi BOOLEAN DEFAULT FALSE; -- Tetronarce cowleyi (Cowley's torpedo ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_tetronarce_occidentalis BOOLEAN DEFAULT FALSE; -- Tetronarce occidentalis (Western atlantic torpedo)

-- Torpedo (11 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_torpedo_adenensis BOOLEAN DEFAULT FALSE; -- Torpedo adenensis (Aden torpedo)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_torpedo_alexandrinsis BOOLEAN DEFAULT FALSE; -- Torpedo alexandrinsis (Alexandrine torpedo)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_torpedo_andersoni BOOLEAN DEFAULT FALSE; -- Torpedo andersoni (Caribbean torpedo)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_torpedo_bauchotae BOOLEAN DEFAULT FALSE; -- Torpedo bauchotae (Rosette torpedo)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_torpedo_fuscomaculata BOOLEAN DEFAULT FALSE; -- Torpedo fuscomaculata (Black-spotted torpedo)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_torpedo_mackayana BOOLEAN DEFAULT FALSE; -- Torpedo mackayana (Ringed torpedo)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_torpedo_marmorata BOOLEAN DEFAULT FALSE; -- Torpedo marmorata (Common crampfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_torpedo_panthera BOOLEAN DEFAULT FALSE; -- Torpedo panthera (Leopard torpedo)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_torpedo_sinuspersici BOOLEAN DEFAULT FALSE; -- Torpedo sinuspersici (Gulf torpedo)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_torpedo_suessii BOOLEAN DEFAULT FALSE; -- Torpedo suessii (Red sea torpedo)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_torpedo_torpedo BOOLEAN DEFAULT FALSE; -- Torpedo torpedo (Common torpedo)

-- Triaenodon (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_triaenodon_obesus BOOLEAN DEFAULT FALSE; -- Triaenodon obesus (Blunt-head shark)

-- Triakis (5 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_triakis_acutipinna BOOLEAN DEFAULT FALSE; -- Triakis acutipinna (Sharpfin houndshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_triakis_maculata BOOLEAN DEFAULT FALSE; -- Triakis maculata (Smooth hound)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_triakis_megalopterus BOOLEAN DEFAULT FALSE; -- Triakis megalopterus (Sharptooth houndshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_triakis_scyllium BOOLEAN DEFAULT FALSE; -- Triakis scyllium (Banded houndshark)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_triakis_semifasciata BOOLEAN DEFAULT FALSE; -- Triakis semifasciata (Leopard shark)

-- Trigonognathus (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_trigonognathus_kabeyai BOOLEAN DEFAULT FALSE; -- Trigonognathus kabeyai (Triangle-jaw lantern-shark)

-- Trygonoptera (6 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_trygonoptera_galba BOOLEAN DEFAULT FALSE; -- Trygonoptera galba (Shovelnose stingaree)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_trygonoptera_imitata BOOLEAN DEFAULT FALSE; -- Trygonoptera imitata (Eastern shovelnose stingaree)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_trygonoptera_mucosa BOOLEAN DEFAULT FALSE; -- Trygonoptera mucosa (Bebil)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_trygonoptera_ovalis BOOLEAN DEFAULT FALSE; -- Trygonoptera ovalis (Bight stingaree)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_trygonoptera_personata BOOLEAN DEFAULT FALSE; -- Trygonoptera personata (Masked stingaree)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_trygonoptera_testacea BOOLEAN DEFAULT FALSE; -- Trygonoptera testacea (Common stingaree)

-- Trygonorrhina (2 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_trygonorrhina_dumerilii BOOLEAN DEFAULT FALSE; -- Trygonorrhina dumerilii (Black and white fiddler ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_trygonorrhina_fasciata BOOLEAN DEFAULT FALSE; -- Trygonorrhina fasciata (Banjo shark)

-- Typhlonarke (2 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_typhlonarke_aysoni BOOLEAN DEFAULT FALSE; -- Typhlonarke aysoni (Blind electric ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_typhlonarke_tarakea BOOLEAN DEFAULT FALSE; -- Typhlonarke tarakea (Numbfish)

-- Urobatis (6 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_urobatis_concentricus BOOLEAN DEFAULT FALSE; -- Urobatis concentricus (Bull's-eye stingray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_urobatis_halleri BOOLEAN DEFAULT FALSE; -- Urobatis halleri (Haller's round ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_urobatis_jamaicensis BOOLEAN DEFAULT FALSE; -- Urobatis jamaicensis (Maid)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_urobatis_maculatus BOOLEAN DEFAULT FALSE; -- Urobatis maculatus (Cortez round stingray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_urobatis_marmoratus BOOLEAN DEFAULT FALSE; -- Urobatis marmoratus (Chilean round stingray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_urobatis_tumbesensis BOOLEAN DEFAULT FALSE; -- Urobatis tumbesensis (Tumbes round stingray)

-- Urogymnus (2 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_urogymnus_acanthobothrium BOOLEAN DEFAULT FALSE; -- Urogymnus acanthobothrium (Mumburarr whipray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_urogymnus_asperrimus BOOLEAN DEFAULT FALSE; -- Urogymnus asperrimus (Black spotted ray)

-- Urolophus (18 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_urolophus_aurantiacus BOOLEAN DEFAULT FALSE; -- Urolophus aurantiacus (Sepia stingray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_urolophus_bucculentus BOOLEAN DEFAULT FALSE; -- Urolophus bucculentus (Great stingaree)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_urolophus_circularis BOOLEAN DEFAULT FALSE; -- Urolophus circularis (Banded sting-ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_urolophus_cruciatus BOOLEAN DEFAULT FALSE; -- Urolophus cruciatus (Banded stingaree)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_urolophus_expansus BOOLEAN DEFAULT FALSE; -- Urolophus expansus (Broadbacked stingaree)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_urolophus_flavomosaicus BOOLEAN DEFAULT FALSE; -- Urolophus flavomosaicus (Patchwork stingaree)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_urolophus_gigas BOOLEAN DEFAULT FALSE; -- Urolophus gigas (Sinclair's stingaree)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_urolophus_javanicus BOOLEAN DEFAULT FALSE; -- Urolophus javanicus (Java stingaree)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_urolophus_kaianus BOOLEAN DEFAULT FALSE; -- Urolophus kaianus (Kai stingaree)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_urolophus_kapalensis BOOLEAN DEFAULT FALSE; -- Urolophus kapalensis (Kapala stingaree)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_urolophus_lobatus BOOLEAN DEFAULT FALSE; -- Urolophus lobatus (Lobed stingaree)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_urolophus_mitosis BOOLEAN DEFAULT FALSE; -- Urolophus mitosis (Blotched stingaree)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_urolophus_orarius BOOLEAN DEFAULT FALSE; -- Urolophus orarius (Coastal stingaree)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_urolophus_paucimaculatus BOOLEAN DEFAULT FALSE; -- Urolophus paucimaculatus (Dixon's stingaree)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_urolophus_piperatus BOOLEAN DEFAULT FALSE; -- Urolophus piperatus (Coral sea stingaree)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_urolophus_sufflavus BOOLEAN DEFAULT FALSE; -- Urolophus sufflavus (Yellowback stingaree)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_urolophus_viridis BOOLEAN DEFAULT FALSE; -- Urolophus viridis (Greenback stingaree)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_urolophus_westraliensis BOOLEAN DEFAULT FALSE; -- Urolophus westraliensis (Brown stingaree)

-- Urotrygon (12 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_urotrygon_aspidura BOOLEAN DEFAULT FALSE; -- Urotrygon aspidura (Panamic stingray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_urotrygon_caudispinosus BOOLEAN DEFAULT FALSE; -- Urotrygon caudispinosus (Stingray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_urotrygon_chilensis BOOLEAN DEFAULT FALSE; -- Urotrygon chilensis (Blotched stingray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_urotrygon_microphthalmum BOOLEAN DEFAULT FALSE; -- Urotrygon microphthalmum (Smalleyed round stingray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_urotrygon_munda BOOLEAN DEFAULT FALSE; -- Urotrygon munda (Munda round ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_urotrygon_nana BOOLEAN DEFAULT FALSE; -- Urotrygon nana (Dwarf round ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_urotrygon_peruanus BOOLEAN DEFAULT FALSE; -- Urotrygon peruanus (Peruvian stingray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_urotrygon_reticulata BOOLEAN DEFAULT FALSE; -- Urotrygon reticulata (Reticulate round ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_urotrygon_rogersi BOOLEAN DEFAULT FALSE; -- Urotrygon rogersi (Lined round stingray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_urotrygon_serrula BOOLEAN DEFAULT FALSE; -- Urotrygon serrula (Stingray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_urotrygon_simulatrix BOOLEAN DEFAULT FALSE; -- Urotrygon simulatrix (Fake round ray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_urotrygon_venezuelae BOOLEAN DEFAULT FALSE; -- Urotrygon venezuelae (Venezuela round stingray)

-- Zameus (1 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_zameus_squamulosus BOOLEAN DEFAULT FALSE; -- Zameus squamulosus (Smallmouth knifetooth dogfish)

-- Zanobatus (2 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_zanobatus_maculatus BOOLEAN DEFAULT FALSE; -- Zanobatus maculatus (Maculate panray)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_zanobatus_schoenleinii BOOLEAN DEFAULT FALSE; -- Zanobatus schoenleinii (Striped panray)

-- Zapteryx (3 species)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_zapteryx_brevirostris BOOLEAN DEFAULT FALSE; -- Zapteryx brevirostris (Lesser guitarfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_zapteryx_exasperata BOOLEAN DEFAULT FALSE; -- Zapteryx exasperata (Banded guitarfish)
ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS sp_zapteryx_xyster BOOLEAN DEFAULT FALSE; -- Zapteryx xyster (Witch guitarfish)

-- ============================================================================
-- Indexes for Frequently-Studied Species (Top 50)
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_sp_squalus_acanthias ON literature_review(sp_squalus_acanthias) WHERE sp_squalus_acanthias = TRUE;
CREATE INDEX IF NOT EXISTS idx_sp_aetobatus_narinari ON literature_review(sp_aetobatus_narinari) WHERE sp_aetobatus_narinari = TRUE;
CREATE INDEX IF NOT EXISTS idx_sp_carcharias_taurus ON literature_review(sp_carcharias_taurus) WHERE sp_carcharias_taurus = TRUE;
CREATE INDEX IF NOT EXISTS idx_sp_taeniura_lymma ON literature_review(sp_taeniura_lymma) WHERE sp_taeniura_lymma = TRUE;
CREATE INDEX IF NOT EXISTS idx_sp_isurus_oxyrinchus ON literature_review(sp_isurus_oxyrinchus) WHERE sp_isurus_oxyrinchus = TRUE;
CREATE INDEX IF NOT EXISTS idx_sp_carcharhinus_obscurus ON literature_review(sp_carcharhinus_obscurus) WHERE sp_carcharhinus_obscurus = TRUE;
CREATE INDEX IF NOT EXISTS idx_sp_galeorhinus_galeus ON literature_review(sp_galeorhinus_galeus) WHERE sp_galeorhinus_galeus = TRUE;
CREATE INDEX IF NOT EXISTS idx_sp_himantura_uarnak ON literature_review(sp_himantura_uarnak) WHERE sp_himantura_uarnak = TRUE;
CREATE INDEX IF NOT EXISTS idx_sp_notorynchus_cepedianus ON literature_review(sp_notorynchus_cepedianus) WHERE sp_notorynchus_cepedianus = TRUE;
CREATE INDEX IF NOT EXISTS idx_sp_rhynchobatus_djiddensis ON literature_review(sp_rhynchobatus_djiddensis) WHERE sp_rhynchobatus_djiddensis = TRUE;
CREATE INDEX IF NOT EXISTS idx_sp_squalus_megalops ON literature_review(sp_squalus_megalops) WHERE sp_squalus_megalops = TRUE;
CREATE INDEX IF NOT EXISTS idx_sp_harriotta_raleighana ON literature_review(sp_harriotta_raleighana) WHERE sp_harriotta_raleighana = TRUE;
CREATE INDEX IF NOT EXISTS idx_sp_hexanchus_griseus ON literature_review(sp_hexanchus_griseus) WHERE sp_hexanchus_griseus = TRUE;
CREATE INDEX IF NOT EXISTS idx_sp_carcharhinus_leucas ON literature_review(sp_carcharhinus_leucas) WHERE sp_carcharhinus_leucas = TRUE;
CREATE INDEX IF NOT EXISTS idx_sp_heptranchias_perlo ON literature_review(sp_heptranchias_perlo) WHERE sp_heptranchias_perlo = TRUE;
CREATE INDEX IF NOT EXISTS idx_sp_odontaspis_ferox ON literature_review(sp_odontaspis_ferox) WHERE sp_odontaspis_ferox = TRUE;
CREATE INDEX IF NOT EXISTS idx_sp_pastinachus_sephen ON literature_review(sp_pastinachus_sephen) WHERE sp_pastinachus_sephen = TRUE;
CREATE INDEX IF NOT EXISTS idx_sp_squalus_mitsukurii ON literature_review(sp_squalus_mitsukurii) WHERE sp_squalus_mitsukurii = TRUE;
CREATE INDEX IF NOT EXISTS idx_sp_alopias_vulpinus ON literature_review(sp_alopias_vulpinus) WHERE sp_alopias_vulpinus = TRUE;
CREATE INDEX IF NOT EXISTS idx_sp_carcharhinus_amblyrhynchos ON literature_review(sp_carcharhinus_amblyrhynchos) WHERE sp_carcharhinus_amblyrhynchos = TRUE;
CREATE INDEX IF NOT EXISTS idx_sp_rhizoprionodon_acutus ON literature_review(sp_rhizoprionodon_acutus) WHERE sp_rhizoprionodon_acutus = TRUE;
CREATE INDEX IF NOT EXISTS idx_sp_rhynchobatus_australiae ON literature_review(sp_rhynchobatus_australiae) WHERE sp_rhynchobatus_australiae = TRUE;
CREATE INDEX IF NOT EXISTS idx_sp_taeniurops_meyeni ON literature_review(sp_taeniurops_meyeni) WHERE sp_taeniurops_meyeni = TRUE;
CREATE INDEX IF NOT EXISTS idx_sp_aptychotrema_rostrata ON literature_review(sp_aptychotrema_rostrata) WHERE sp_aptychotrema_rostrata = TRUE;
CREATE INDEX IF NOT EXISTS idx_sp_carcharhinus_brachyurus ON literature_review(sp_carcharhinus_brachyurus) WHERE sp_carcharhinus_brachyurus = TRUE;
CREATE INDEX IF NOT EXISTS idx_sp_rostroraja_alba ON literature_review(sp_rostroraja_alba) WHERE sp_rostroraja_alba = TRUE;
CREATE INDEX IF NOT EXISTS idx_sp_squatina_squatina ON literature_review(sp_squatina_squatina) WHERE sp_squatina_squatina = TRUE;
CREATE INDEX IF NOT EXISTS idx_sp_carcharhinus_falciformis ON literature_review(sp_carcharhinus_falciformis) WHERE sp_carcharhinus_falciformis = TRUE;
CREATE INDEX IF NOT EXISTS idx_sp_carcharhinus_limbatus ON literature_review(sp_carcharhinus_limbatus) WHERE sp_carcharhinus_limbatus = TRUE;
CREATE INDEX IF NOT EXISTS idx_sp_carcharhinus_melanopterus ON literature_review(sp_carcharhinus_melanopterus) WHERE sp_carcharhinus_melanopterus = TRUE;
CREATE INDEX IF NOT EXISTS idx_sp_centroscymnus_owstonii ON literature_review(sp_centroscymnus_owstonii) WHERE sp_centroscymnus_owstonii = TRUE;
CREATE INDEX IF NOT EXISTS idx_sp_cephaloscyllium_laticeps ON literature_review(sp_cephaloscyllium_laticeps) WHERE sp_cephaloscyllium_laticeps = TRUE;
CREATE INDEX IF NOT EXISTS idx_sp_chimaera_monstrosa ON literature_review(sp_chimaera_monstrosa) WHERE sp_chimaera_monstrosa = TRUE;
CREATE INDEX IF NOT EXISTS idx_sp_etmopterus_granulosus ON literature_review(sp_etmopterus_granulosus) WHERE sp_etmopterus_granulosus = TRUE;
CREATE INDEX IF NOT EXISTS idx_sp_neotrygon_kuhlii ON literature_review(sp_neotrygon_kuhlii) WHERE sp_neotrygon_kuhlii = TRUE;
CREATE INDEX IF NOT EXISTS idx_sp_rhinoptera_javanica ON literature_review(sp_rhinoptera_javanica) WHERE sp_rhinoptera_javanica = TRUE;
CREATE INDEX IF NOT EXISTS idx_sp_scyliorhinus_canicula ON literature_review(sp_scyliorhinus_canicula) WHERE sp_scyliorhinus_canicula = TRUE;
CREATE INDEX IF NOT EXISTS idx_sp_scyliorhinus_stellaris ON literature_review(sp_scyliorhinus_stellaris) WHERE sp_scyliorhinus_stellaris = TRUE;
CREATE INDEX IF NOT EXISTS idx_sp_sphyrna_zygaena ON literature_review(sp_sphyrna_zygaena) WHERE sp_sphyrna_zygaena = TRUE;
CREATE INDEX IF NOT EXISTS idx_sp_amblyraja_radiata ON literature_review(sp_amblyraja_radiata) WHERE sp_amblyraja_radiata = TRUE;
CREATE INDEX IF NOT EXISTS idx_sp_callorhinchus_milii ON literature_review(sp_callorhinchus_milii) WHERE sp_callorhinchus_milii = TRUE;
CREATE INDEX IF NOT EXISTS idx_sp_carcharodon_carcharias ON literature_review(sp_carcharodon_carcharias) WHERE sp_carcharodon_carcharias = TRUE;
CREATE INDEX IF NOT EXISTS idx_sp_mobula_eregoodootenkee ON literature_review(sp_mobula_eregoodootenkee) WHERE sp_mobula_eregoodootenkee = TRUE;
CREATE INDEX IF NOT EXISTS idx_sp_mustelus_canis ON literature_review(sp_mustelus_canis) WHERE sp_mustelus_canis = TRUE;
CREATE INDEX IF NOT EXISTS idx_sp_mustelus_manazo ON literature_review(sp_mustelus_manazo) WHERE sp_mustelus_manazo = TRUE;
CREATE INDEX IF NOT EXISTS idx_sp_myliobatis_australis ON literature_review(sp_myliobatis_australis) WHERE sp_myliobatis_australis = TRUE;
CREATE INDEX IF NOT EXISTS idx_sp_prionace_glauca ON literature_review(sp_prionace_glauca) WHERE sp_prionace_glauca = TRUE;
CREATE INDEX IF NOT EXISTS idx_sp_triaenodon_obesus ON literature_review(sp_triaenodon_obesus) WHERE sp_triaenodon_obesus = TRUE;
CREATE INDEX IF NOT EXISTS idx_sp_trygonorrhina_fasciata ON literature_review(sp_trygonorrhina_fasciata) WHERE sp_trygonorrhina_fasciata = TRUE;
CREATE INDEX IF NOT EXISTS idx_sp_carcharhinus_brevipinna ON literature_review(sp_carcharhinus_brevipinna) WHERE sp_carcharhinus_brevipinna = TRUE;

-- ============================================================================
-- Helper Views
-- ============================================================================

-- Species summary (will be populated after data entry)
-- CREATE OR REPLACE VIEW v_species_summary AS ...
-- (Deferred - requires dynamic SQL generation)

-- ============================================================================
-- Column Documentation (Top 20 Species)
-- ============================================================================

COMMENT ON COLUMN literature_review.sp_squalus_acanthias IS 'Species: Squalus acanthias (Blue dog)';
COMMENT ON COLUMN literature_review.sp_aetobatus_narinari IS 'Species: Aetobatus narinari (Bishop ray)';
COMMENT ON COLUMN literature_review.sp_carcharias_taurus IS 'Species: Carcharias taurus (Blue nurse shark)';
COMMENT ON COLUMN literature_review.sp_taeniura_lymma IS 'Species: Taeniura lymma (Blue spotted lagoon ray)';
COMMENT ON COLUMN literature_review.sp_isurus_oxyrinchus IS 'Species: Isurus oxyrinchus (Atlantic mako)';
COMMENT ON COLUMN literature_review.sp_carcharhinus_obscurus IS 'Species: Carcharhinus obscurus (Bay-shark)';
COMMENT ON COLUMN literature_review.sp_galeorhinus_galeus IS 'Species: Galeorhinus galeus (Eastern school shark)';
COMMENT ON COLUMN literature_review.sp_himantura_uarnak IS 'Species: Himantura uarnak (Banded whiptail stingray)';
COMMENT ON COLUMN literature_review.sp_notorynchus_cepedianus IS 'Species: Notorynchus cepedianus (Bluntnose sevengill shark)';
COMMENT ON COLUMN literature_review.sp_rhynchobatus_djiddensis IS 'Species: Rhynchobatus djiddensis (Giant guitarfish)';
COMMENT ON COLUMN literature_review.sp_squalus_megalops IS 'Species: Squalus megalops (Bluntnose spiny dogfish)';
COMMENT ON COLUMN literature_review.sp_harriotta_raleighana IS 'Species: Harriotta raleighana (Bent-nose chimaera)';
COMMENT ON COLUMN literature_review.sp_hexanchus_griseus IS 'Species: Hexanchus griseus (6-gilled shark)';
COMMENT ON COLUMN literature_review.sp_carcharhinus_leucas IS 'Species: Carcharhinus leucas (Bull shark)';
COMMENT ON COLUMN literature_review.sp_heptranchias_perlo IS 'Species: Heptranchias perlo (7-gilled shark)';
COMMENT ON COLUMN literature_review.sp_odontaspis_ferox IS 'Species: Odontaspis ferox (Bigeye sandtiger)';
COMMENT ON COLUMN literature_review.sp_pastinachus_sephen IS 'Species: Pastinachus sephen (Banana-tail ray)';
COMMENT ON COLUMN literature_review.sp_squalus_mitsukurii IS 'Species: Squalus mitsukurii (Blainvilles dogfish)';
COMMENT ON COLUMN literature_review.sp_alopias_vulpinus IS 'Species: Alopias vulpinus (Atlantic thresher)';
COMMENT ON COLUMN literature_review.sp_carcharhinus_amblyrhynchos IS 'Species: Carcharhinus amblyrhynchos (Black-vee whaler)';

-- ============================================================================
-- Usage Examples
-- ============================================================================

/*
-- Mark a paper studying multiple species
UPDATE literature_review
SET
    sp_carcharodon_carcharias = TRUE,
    sp_prionace_glauca = TRUE,
    sp_galeocerdo_cuvier = TRUE
WHERE study_id = 1;

-- Find all White Shark papers
SELECT title, year
FROM literature_review
WHERE sp_carcharodon_carcharias = TRUE;

-- Count papers by species (top 20)
SELECT
    SUM(CASE WHEN sp_carcharodon_carcharias THEN 1 ELSE 0 END) as white_shark,
    SUM(CASE WHEN sp_prionace_glauca THEN 1 ELSE 0 END) as blue_shark,
    SUM(CASE WHEN sp_galeocerdo_cuvier THEN 1 ELSE 0 END) as tiger_shark
FROM literature_review;

-- Find multi-species comparative studies
SELECT title, year,
    (CAST(sp_carcharodon_carcharias AS INTEGER) +
     CAST(sp_prionace_glauca AS INTEGER) +
     CAST(sp_galeocerdo_cuvier AS INTEGER) +
     CAST(sp_isurus_oxyrinchus AS INTEGER)) AS species_count
FROM literature_review
WHERE species_count >= 2
ORDER BY species_count DESC;

-- Find papers on sharks in a specific family (requires family lookup)
-- Example: All Carcharhinidae (requiem sharks)
SELECT title, year
FROM literature_review
WHERE sp_carcharhinus_acronotus = TRUE
   OR sp_carcharhinus_albimarginatus = TRUE
   OR sp_carcharhinus_altimus = TRUE
   -- ... (add all Carcharhinus species)
;
*/

-- ============================================================================
-- END OF FILE
-- ============================================================================
-- Total species columns: 1030
-- Missing species: ~178 (to be added when Weigmann updated list received)
-- ============================================================================
