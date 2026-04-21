# Systematic per-schema review — for 2026-04-21 / 22 meetings

_Generated 2026-04-20 from `scripts/extract_schema_columns.py` after the TITLE+KEYWORDS commit. Use this document to walk through schemas systematically — what is captured, what isn't, where TITLE/KEYWORDS now apply, and what design decisions remain open._

## TL;DR — TITLE & KEYWORDS coverage by schema

| Schema | TITLE | KEYWORDS | Notes |
|---|---|---|---|
| `eco_` Ecosystem | 2.0 | 2.0 | active in this commit |
| `pr_` Pressure / Threat | 2.0 | 2.0 | active in this commit |
| `gear_` Fishing Gear | 2.0 | 2.0 | active in this commit |
| `imp_` Impact / Response | 2.0 | 2.0 | active in this commit |
| `d_` Discipline | 2.0 | 2.0 | active in this commit |
| `b_` Ocean Basin (keyword) | 2.0 | 2.0 | active in this commit |
| `sb_` Ocean Sub-basin | 2.0 | 2.0 | active in this commit |
| `ob_` Ocean Basin (geographic pipeline) | n/a | n/a | not text-extracted; comes from study coordinates + institution country. Section weighting irrelevant. |
| `sp_` Species | n/a | n/a | integer count column (1,309 cols); no section weighting applied. **TO REVIEW:** worth applying TITLE+KEYWORDS multipliers? Authors typically list focal species in title/keywords. |
| `a_` Analytical Techniques | n/a | n/a | integer count column (215 cols); no section weighting. **TO REVIEW:** TITLE+KEYWORDS would help capture the headline technique even when it's only mentioned a few times in body. |
| `depth_` Depth | n/a | n/a | numeric extraction (regex on `<num> m`); section weighting not applicable. |

**Decision points for the meeting:**
- Should `sp_` and `a_` adopt section weighting (with TITLE/KEYWORDS at 2.0)? Currently they use raw frequency counts; promoting title/keyword mentions could improve precision for focal-species and primary-technique identification.
- `ob_` is fed from a separate geographic pipeline and bypasses the keyword extractor entirely. Cross-validation with `b_` (keyword) is the recommended audit; see ocean_basin_proposal.md.

---

## `eco_` — Ecosystem

**Schema proposal:** [`ecosystem_component_proposal.md`](ecosystem_component_proposal.md)  
**Number of columns:** 20  
**Section weights:** Title: **2.0** / Keywords: **2.0** / Abstract: **0.5** / Introduction: **1.0** / Methods: **1.0** / Results: **0.5** / Results And Discussion: **0.5** / Discussion: **0.5** / Conclusions: **0.5** / Other: **0.25**

| Column | Threshold | Anchors | Case-sensitive | Prereq | Terms |
|---|---|---|---|---|---|
| **eco_marine** | 3 | — | — | — | <small>`marine`, `ocean`, `sea`, `saltwater`</small> |
| **eco_freshwater** | 3 | — | — | — | <small>`freshwater`, `freshwater river`, `river shark`, `river system`, `riverine`, `lake`, `estuarine`, `estuarin*`, `brackish`</small> |
| **eco_brackish** | 2 | — | — | — | <small>`estuar*`, `brackish`, `lagoon`, `mangrove`</small> |
| **eco_pelagic** | 2 | — | — | — | <small>`pelagic`, `open ocean`, `oceanic`, `epipelagic`, `mesopelagic`, `bathypelagic`</small> |
| **eco_coastal** | 3 | — | — | — | <small>`coastal`, `neritic`, `inshore`, `nearshore`, `continental shelf`</small> |
| **eco_demersal** | 2 | — | — | — | <small>`demersal`, `benthic`, `bottom-dwelling`, `epibenthic`, `benthopelagic`</small> |
| **eco_reef** | 1 | — | — | — | <small>`coral reef`, `reef-associated`, `rocky reef`</small> |
| **eco_deepwater** | 2 | — | — | — | <small>`deep-sea`, `deep-water`, `deepwater`, `deep water`, `abyssal`, `hadal`, `bathyal`, `seamount`</small> |
| **eco_intertidal** | 1 | — | — | — | <small>`intertidal`, `tide pool`, `littoral`</small> |
| **eco_mangrove** | 2 | — | — | — | <small>`mangrove`</small> |
| **eco_seagrass** | 1 | — | — | — | <small>`seagrass`, `eelgrass`, `Posidonia`, `Zostera`, `Thalassia`</small> |
| **eco_kelp** | 1 | — | — | — | <small>`kelp forest`, `kelp bed`, `macroalgal`</small> |
| **eco_polar** | 2 | — | — | — | <small>`polar`, `arctic`, `antarctic`, `ice-edge`, `sea ice`</small> |
| **eco_riverine** | 1 | — | — | — | <small>`river shark`, `freshwater stingray`, `bull shark river`</small> |
| **eco_nursery** | 1 | — | — | — | <small>`nursery habitat`, `nursery ground`, `nursery area`, `essential fish habitat`, `juvenile habitat`</small> |
| **eco_pupping** | 1 | — | — | — | <small>`pupping ground`, `pupping area`, `parturition site`, `birthing ground`</small> |
| **eco_epipelagic** | 2 | — | — | — | <small>`epipelagic`, `surface waters`, `surface layer`, `photic zone`</small> |
| **eco_mesopelagic** | 1 | — | — | — | <small>`mesopelagic`, `twilight zone`</small> |
| **eco_bathypelagic** | 1 | — | — | — | <small>`bathypelagic`, `deep scattering layer`</small> |
| **eco_abyssal** | 1 | — | — | — | <small>`abyssal`, `hadal`</small> |

---

## `pr_` — Pressure / Threat

**Schema proposal:** [`pressure_proposal.md`](pressure_proposal.md)  
**Number of columns:** 26  
**Section weights:** Title: **2.0** / Keywords: **2.0** / Abstract: **0.5** / Introduction: **1.0** / Methods: **1.0** / Results: **0.5** / Results And Discussion: **1.0** / Discussion: **1.0** / Conclusions: **0.5** / Other: **0.25**

| Column | Threshold | Anchors | Case-sensitive | Prereq | Terms |
|---|---|---|---|---|---|
| **pr_fishing_commercial** | 3 | — | — | — | <small>`commercial fish*`, `industrial fish*`, `fishing pressure`, `fishing mortality`, `exploitation`</small> |
| **pr_fishing_artisanal** | 2 | — | — | — | <small>`artisanal`, `small-scale fish*`, `subsistence fish*`, `traditional fish*`</small> |
| **pr_fishing_recreational** | 2 | — | — | — | <small>`recreational fish*`, `sport fish*`, `game fish*`, `catch-and-release`, `angling`, `angler`, `anglers`</small> |
| **pr_fishing_iuu** | 2 | — | IUU | — | <small>`illegal fish*`, `unreported`, `unregulated`, `IUU`, `poach*`</small> |
| **pr_bycatch** | 2 | — | — | — | <small>`bycatch`, `by-catch`, `incidental capture`, `non-target`, `discards`</small> |
| **pr_shark_finning** | 1 | — | — | — | <small>`shark fin*`, `finning`, `fin trade`</small> |
| **pr_targeted_fishing** | 2 | — | — | — | <small>`targeted shark fish*`, `directed shark fish*`, `shark fish*`</small> |
| **pr_climate_change** | 3 | — | — | — | <small>`climate change`, `global warming`, `ocean warming`</small> |
| **pr_ocean_acidification** | 1 | — | — | — | <small>`ocean acidification`, `(acidification AND pH)`, `(acidification AND pCO2)`</small> |
| **pr_hypoxia** | 1 | — | OMZ | — | <small>`hypoxia`, `deoxygenation`, `oxygen minimum zone`, `OMZ`</small> |
| **pr_pollution_chemical** | 3 | — | PCB, PFAS | — | <small>`pollut*`, `contaminant*`, `heavy metal*`, `mercury`, `PCB`, `PFAS`, `pesticide*`</small> |
| **pr_pollution_plastic** | 1 | — | — | — | <small>`plastic pollution`, `microplastic*`, `macroplastic*`, `plastic ingestion`, `plastic debris`</small> |
| **pr_pollution_noise** | 1 | — | — | — | <small>`noise pollution`, `anthropogenic noise`, `shipping noise`, `sonar`, `acoustic disturbance`</small> |
| **pr_habitat_loss** | 2 | — | — | — | <small>`habitat loss`, `habitat degradation`, `coastal development`, `dredg*`, `mangrove loss`</small> |
| **pr_shipping** | 1 | — | — | — | <small>`ship strike`, `vessel strike`, `maritime traffic`</small> |
| **pr_tourism** | 2 | — | — | — | <small>`dive tourism`, `ecotourism`, `shark tourism`, `provisioning`, `shark feed*`, `cage div*`</small> |
| **pr_depredation** | 1 | — | — | — | <small>`depredation`, `depredating`, `bait loss`, `catch damage`</small> |
| **pr_aquaculture** | 2 | — | — | — | <small>`aquaculture`, `fish farm*`, `mariculture`</small> |
| **pr_invasive** | 1 | — | — | — | <small>`invasive species`, `non-native species`, `alien species`</small> |
| **pr_disease** | 3 | — | — | — | <small>`disease`, `pathogen`, `parasite`, `epizootic`, `infection`</small> |
| **pr_light** | 1 | — | ALAN | — | <small>`light pollution`, `artificial light`, `ALAN`</small> |
| **pr_electromagnetic** | 1 | — | EMF | — | <small>`electromagnetic field`, `EMF`, `submarine cable`, `electroreception interference`</small> |
| **pr_cumulative** | 2 | — | — | — | <small>`cumulative impact`, `multiple stressor*`, `synergistic`, `additive effect`</small> |
| **pr_discarding** | 2 | — | — | — | <small>`discard*`, `discarding practice*`, `high-grading`, `slipping`</small> |
| **pr_seabed_disturbance** | 1 | — | — | — | <small>`seabed disturbance`, `bottom disturbance`, `benthic disturbance`, `physical disturbance of the seabed`, `sediment resuspension`, `trawl impact on seabed`, `habitat scraping`</small> |
| **pr_visual_disturbance** | 1 | — | — | — | <small>`visual disturbance`, `vessel presence`, `diver disturbance`, `boat disturbance`, `swimmer disturbance`, `shadow effect`</small> |

---

## `gear_` — Fishing Gear

**Schema proposal:** [`gear_proposal.md`](gear_proposal.md)  
**Number of columns:** 28  
**Section weights:** Title: **2.0** / Keywords: **2.0** / Abstract: **0.5** / Introduction: **0.25** / Methods: **1.0** / Results: **0.5** / Results And Discussion: **0.5** / Discussion: **0.25** / Conclusions: **0.25** / Other: **0.25**

| Column | Threshold | Anchors | Case-sensitive | Prereq | Terms |
|---|---|---|---|---|---|
| **gear_longline** | 2 | — | — | — | <small>`longline`, `long-line`, `pelagic longline`, `demersal longline`, `bottom longline`</small> |
| **gear_gillnet** | 2 | — | — | — | <small>`gillnet`, `gill net`, `trammel net`, `entangling net`, `drift net`, `driftnet`</small> |
| **gear_trawl** | 2 | — | — | — | <small>`trawl`, `bottom trawl`, `demersal trawl`, `pelagic trawl`, `otter trawl`, `beam trawl`, `shrimp trawl`</small> |
| **gear_purse_seine** | 1 | — | — | — | <small>`purse seine`, `purse-seine`, `ring net`</small> |
| **gear_seine** | 1 | — | — | — | <small>`beach seine`, `Danish seine`, `seine net`</small> |
| **gear_hook_line** | 2 | — | — | — | <small>`hook and line`, `handline`, `rod and reel`, `trolling`, `jigging`, `pole and line`</small> |
| **gear_trap** | 2 | — | — | — | <small>`trap`, `pot`, `fish trap`, `drumline`, `SMART drumline`</small> |
| **gear_net_other** | 1 | — | weir | — | <small>`cast net`, `lift net`, `scoop net`, `fyke net`, `pound net`, `weir`</small> |
| **gear_harpoon** | 1 | — | — | — | <small>`harpoon`, `spearfish*`, `spear gun`</small> |
| **gear_dredge** | 1 | — | — | — | <small>`dredge`, `towed dredge`, `scallop dredge`, `clam dredge`, `oyster dredge`, `hydraulic dredge`</small> |
| **gear_trawl_beam** | 1 | — | — | — | <small>`beam trawl`, `beam-trawl`</small> |
| **gear_trawl_otter** | 1 | — | — | — | <small>`otter trawl`, `otter-trawl`</small> |
| **gear_survey** | 2 | — | BRUVs, ROV, UAV | — | <small>`research vessel`, `survey trawl`, `BRUVs`, `longline survey`, `fishery-independent survey`, `drone survey`, `UAV survey`, `ROV`, `submersible`, `diving survey`, `diver transect`</small> |
| **gear_pelagic** | 1 | — | — | — | <small>`pelagic longline`, `pelagic trawl`, `midwater trawl`</small> |
| **gear_demersal** | 1 | — | — | — | <small>`demersal longline`, `bottom trawl`, `demersal trawl`, `bottom longline`</small> |
| **gear_artisanal** | 2 | — | — | — | <small>`artisanal`, `traditional gear`, `small-scale`, `hand-operated`</small> |
| **gear_mit_circle_hook** | 1 | — | — | — | <small>`circle hook`, `non-offset hook`</small> |
| **gear_mit_brd** | 1 | — | BRD, TED | — | <small>`bycatch reduction device`, `BRD`, `turtle excluder`, `TED`</small> |
| **gear_mit_deterrent** | 1 | — | EPM | — | <small>`shark deterrent`, `SharkGuard`, `shark guard`, `electropositive`, `Rare Earth`, `EPM`, `LED deterrent`, `magnetic deterrent`</small> |
| **gear_mit_time_area** | 2 | — | MPA | — | <small>`time-area closure`, `spatial closure`, `fishing closure`, `seasonal closure`, `MPA`</small> |
| **gear_mit_handling** | 1 | — | PRM | — | <small>`safe release`, `handling practice*`, `live release`, `post-release mortality`, `PRM`</small> |
| **gear_mit_weak_hook** | 1 | — | — | — | <small>`weak hook`, `corrodible hook`, `designed to straighten`</small> |
| **gear_mit_line_weight** | 1 | — | — | — | <small>`line weight*`, `weighted branchline`, `leaded swivel`, `sliding lead`, `lumo lead`, `sink rate`</small> |
| **gear_mit_setting** | 1 | — | — | — | <small>`night set*`, `deep set*`, `deep-set buoy gear`, `side-set*`, `underwater set*`</small> |
| **gear_mit_pinger** | 1 | — | PAL | — | <small>`pinger`, `acoustic alarm`, `acoustic deterrent`, `porpoise alerting device`, `PAL`</small> |
| **gear_mit_illumination** | 1 | — | — | — | <small>`illuminat* net`, `illuminat* gillnet`, `LED net`, `net light*`, `lightstick*`, `light attract*`</small> |
| **gear_mit_wire_leader** | 1 | — | — | — | <small>`wire leader`, `monofilament leader`, `wire trace`, `nylon leader`</small> |
| **gear_ghost** | 1 | — | ALDFG | — | <small>`ghost gear`, `ghost net`, `ghost fishing`, `ALDFG`, `abandoned gear`, `lost gear`, `derelict gear`, `derelict fishing`</small> |

---

## `imp_` — Impact / Response

**Schema proposal:** [`impact_proposal.md`](impact_proposal.md)  
**Number of columns:** 21  
**Section weights:** Title: **2.0** / Keywords: **2.0** / Abstract: **0.5** / Introduction: **0.25** / Methods: **0.5** / Results: **1.0** / Results And Discussion: **1.0** / Discussion: **1.0** / Conclusions: **0.5** / Other: **0.25**

| Column | Threshold | Anchors | Case-sensitive | Prereq | Terms |
|---|---|---|---|---|---|
| **imp_mortality** | 2 | — | AVM, DOA | — | <small>`mortality`, `survival rate`, `lethality`, `dead on arrival`, `DOA`, `at-vessel mortality`, `AVM`</small> |
| **imp_post_release** | 1 | — | PRM | — | <small>`post-release mortality`, `PRM`, `delayed mortality`, `post-capture survival`</small> |
| **imp_abundance** | 2 | population, decline, increase, change, trend, status | — | — | <small>`abundance`, `population size`, `population decline`, `population trend`</small> |
| **imp_cpue** | 1 | — | CPUE | — | <small>`CPUE`, `catch per unit effort`, `catch rate`</small> |
| **imp_biomass** | 2 | change, decline, decrease, increase, shift, trend, loss, recovery, fluctuat*, depletion, rebuild* | SSB | — | <small>`biomass`, `standing stock`, `spawning stock biomass`, `SSB`</small> |
| **imp_distribution** | 1 | — | — | — | <small>`distribution shift`, `range shift`, `range contraction`, `habitat shift`</small> |
| **imp_behaviour_change** | 2 | change, response | — | — | <small>`behavioural change`, `behavioral change`, `avoidance behaviour`, `flight response`, `habituation`</small> |
| **imp_physiology_stress** | 1 | — | RAMP | — | <small>`cortisol`, `lactate`, `blood chemistry`, `acid-base`, `reflex impairment`, `RAMP`, `physiological stress`</small> |
| **imp_injury** | 2 | — | — | — | <small>`injury`, `hooking injury`, `scarring`, `body condition index`, `entanglement`, `entangled`, `gear interaction`, `net mark*`</small> |
| **imp_reproduction** | 1 | — | — | — | <small>`reproductive output`, `fecundity change`, `reproductive failure`</small> |
| **imp_growth** | 2 | change, impact, decline, reduce, affect, alter, slow, decrease, increase | — | — | <small>`growth rate`, `von Bertalanffy`, `growth curve`, `somatic growth`, `condition factor`, `Fulton`, `length-weight`, `stunting`, `growth overfishing`</small> |
| **imp_genetic** | 2 | — | — | — | <small>`genetic diversity`, `effective population size`, `bottleneck`, `inbreeding`</small> |
| **imp_trophic** | 1 | — | — | — | <small>`trophic level change`, `dietary shift`, `prey depletion`, `mesopredator release`</small> |
| **imp_habitat_quality** | 2 | — | — | — | <small>`habitat quality`, `habitat suitability`, `degradation index`</small> |
| **imp_contamination** | 1 | — | — | — | <small>`contaminant load`, `bioaccumulation`, `biomagnification`, `tissue concentration`</small> |
| **imp_economic** | 1 | — | WTP | — | <small>`economic value`, `fishery value`, `tourism revenue`, `willingness to pay`, `WTP`</small> |
| **imp_social** | 3 | — | — | — | <small>`livelihood`, `food security`, `human dimension`, `attitude`, `perception`</small> |
| **imp_community_composition** | 2 | change, shift, impact, alter* | — | — | <small>`community composition`, `assemblage composition`, `species composition`, `community structure change`, `assemblage shift`</small> |
| **imp_biodiversity** | 2 | change, loss, decline, impact | — | — | <small>`biodiversity loss`, `species richness change`, `diversity index`, `Shannon`, `Simpson`, `evenness change`, `species loss`</small> |
| **imp_size_structure** | 2 | change, shift, impact, decline, truncat* | — | — | <small>`size structure`, `length frequency`, `age structure`, `size composition`, `size distribution`, `mean length`, `maximum length`, `length at maturity shift`, `truncated size`</small> |
| **imp_productivity** | 2 | change, decline, impact, reduce, increase, affect, fishing, overfishing | SPR | — | <small>`productivity`, `recruitment`, `yield per recruit`, `spawning potential ratio`, `SPR`, `surplus production`, `reproductive output`</small> |

---

## `d_` — Discipline

**Schema proposal:** [`discipline_proposal.md`](discipline_proposal.md)  
**Number of columns:** 19  
**Section weights:** Title: **2.0** / Keywords: **2.0** / Abstract: **0.5** / Introduction: **0.5** / Methods: **1.0** / Results: **1.0** / Results And Discussion: **1.0** / Discussion: **0.5** / Conclusions: **0.5** / Other: **0.25**

| Column | Threshold | Anchors | Case-sensitive | Prereq | Terms |
|---|---|---|---|---|---|
| **d_biology** | 2 | — | GSI, HSI | GSI→gonadosomatic index; HSI→hepatosomatic index | <small>`life history`, `age and growth`, `growth rate`, `longevity`, `maturity`, `length-at-maturity`, `length-weight`, `vertebral band`, `vertebral count*`, `band pair*`, `gonadosomatic index`, `hepatosomatic index`, `GSI`, `HSI`, `Le Cren`, `Fulton's K`, `morphometric analysis`, `total length`, `precaudal length`, `disc width`</small> |
| **d_behaviour** | 3 | — | — | — | <small>`behavio*`, `behavioral ecology`, `predator-prey`, `diel vertical migration`, `activity pattern`, `social behavio*`, `agonistic`, `refuging`</small> |
| **d_trophic** | 2 | — | — | — | <small>`trophic`, `diet`, `feeding ecology`, `stomach content*`, `prey composition`, `stable isotope`, `fatty acid`, `food web`</small> |
| **d_genetics** | 2 | — | SNP, eDNA | — | <small>`genetic*`, `genomic*`, `eDNA`, `environmental DNA`, `microsatellite`, `mitochondrial`, `phylogenet*`, `haplotype`, `SNP`, `RADseq`, `population genetics`</small> |
| **d_movement** | 3 | — | — | — | <small>`movement`, `telemetry`, `satellite tag*`, `acoustic tag*`, `archival tag*`, `home range`, `migration`, `habitat use`, `space use`, `tracking`</small> |
| **d_fisheries** | 2 | — | MSY | — | <small>`stock assessment`, `fisheries management`, `catch data`, `fishing mortality`, `maximum sustainable yield`, `MSY`, `fishery-dependent`, `fishery-independent`, `bycatch`, `discard*`, `retention`, `non-target species`, `non-target catch`</small> |
| **d_conservation** | 3 | — | CITES, IUCN | — | <small>`conservation`, `endangered`, `CITES`, `IUCN`, `Red List`, `protected area`, `marine protected area`, `recovery plan`, `conservation status`</small> |
| **d_data_science** | 2 | — | — | — | <small>`machine learning`, `deep learning`, `neural network`, `random forest`, `Bayesian`, `meta-analysis`, `systematic review`, `simulation model`</small> |
| **d_husbandry** | 2 | — | — | — | <small>`aquarium`, `captive`, `husbandry`, `captive breeding`, `ex situ`, `tank-held`, `aquaria`</small> |
| **d_paleontology** | 1 | — | — | — | <small>`fossil`, `paleontol*`, `palaeontol*`, `Cretaceous`, `Jurassic`, `Miocene`, `Pliocene`, `Eocene`, `Oligocene`, `Cenozoic`, `Mesozoic`, `Devonian`, `Carboniferous`</small> |
| **d_taxonomy** | 1 | — | — | — | <small>`taxonom*`, `new species`, `sp. nov.`, `new genus`, `morphometric*`, `meristic*`, `dichotomous key`, `identification key`, `redescription`, `synonymy`, `type specimen`</small> |
| **d_physiology** | 2 | — | MMR, Q10, RMR, SMR, TMAO, Ucrit | — | <small>`physiolog*`, `metaboli*`, `oxygen consumption`, `ventilation rate`, `blood gas`, `haematocrit`, `hematocrit`, `osmoregulat*`, `thermoregulat*`, `bioenergetic*`, `SMR`, `RMR`, `MMR`, `aerobic scope`, `Ucrit`, `U crit`, `U-crit`, `critical swimming speed`, `heart rate`, `cardiac output`, `blood pressure`, `plasma osmolality`, `plasma cortisol`, `plasma lactate`, `urea`, `TMAO`, `trimethylamine N-oxide`, `enzyme activity`, `Q10`, `metabolic rate`</small> |
| **d_reproductive** | 2 | — | — | — | <small>`reproductive biology`, `fecundity`, `gestation`, `embryo*`, `uterine`, `ovipar*`, `vivipar*`, `mating`, `parturition`, `neonat*`, `litter size`, `reproductive cycle`</small> |
| **d_biomechanics** | 1 | — | — | — | <small>`biomechani*`, `functional morphology`, `locomot*`, `kinematics`, `bite force`, `jaw mechanics`, `hydrodynamic*`, `swimming performance`</small> |
| **d_sensory** | 1 | — | — | — | <small>`electrorecept*`, `ampullae of Lorenzini`, `lateral line`, `mechanosens*`, `olfact*`, `chemosens*`, `visual acuity`, `magnetorecept*`</small> |
| **d_ecotourism** | 1 | — | — | — | <small>`ecotourism`, `dive tourism`, `shark tourism`, `shark watching`, `whale shark tourism`, `shark encounter`, `provisioning`</small> |
| **d_human_dimensions** | 2 | — | — | — | <small>`human dimension*`, `social science`, `stakeholder`, `perception`, `attitude*`, `willingness to pay`, `WTP`, `shark bite`, `shark attack`, `shark repellent`</small> |
| **d_immunology** | 2 | — | — | — | <small>`immun*`, `antibod*`, `complement system`, `innate immun*`, `adaptive immun*`, `leukocyte`, `lymphocyte`</small> |
| **d_toxicology** | 2 | — | — | — | <small>`toxicolog*`, `contaminant*`, `bioaccumulation`, `biomagnification`, `heavy metal*`, `mercury`, `methylmercury`, `tissue concentration`</small> |

---

## `b_` — Ocean Basin (keyword)

**Schema proposal:** [`ocean_basin_proposal.md`](ocean_basin_proposal.md)  
**Number of columns:** 9  
**Section weights:** Title: **2.0** / Keywords: **2.0** / Abstract: **0.5** / Introduction: **1.0** / Methods: **1.0** / Results: **0.5** / Results And Discussion: **0.5** / Discussion: **0.5** / Conclusions: **0.5** / Other: **0.25**

| Column | Threshold | Anchors | Case-sensitive | Prereq | Terms |
|---|---|---|---|---|---|
| **b_north_atlantic** | 2 | — | — | — | <small>`North Atlantic`, `Northwest Atlantic`, `Northeast Atlantic`, `NW Atlantic`, `NE Atlantic`, `North Sea`, `Bay of Biscay`, `Celtic Sea`, `Norwegian Sea`, `Barents Sea`, `Baltic Sea`, `Gulf of Mexico`, `Sargasso Sea`, `Azores`</small> |
| **b_south_atlantic** | 2 | — | — | — | <small>`South Atlantic`, `Southwest Atlantic`, `Southeast Atlantic`, `SW Atlantic`, `SE Atlantic`, `Benguela`, `Patagoni*`, `South Africa*`, `Namibia*`, `Brazilian coast`</small> |
| **b_north_pacific** | 2 | — | — | — | <small>`North Pacific`, `Northwest Pacific`, `Northeast Pacific`, `NW Pacific`, `NE Pacific`, `Bering Sea`, `Sea of Japan`, `East China Sea`, `South China Sea`, `Yellow Sea`, `California Current`, `Kuroshio`, `Sea of Okhotsk`, `Gulf of Alaska`, `Hawaiian`</small> |
| **b_south_pacific** | 2 | — | — | — | <small>`South Pacific`, `Southwest Pacific`, `Southeast Pacific`, `SW Pacific`, `SE Pacific`, `Coral Sea`, `Tasman Sea`, `Great Barrier Reef`, `New Zealand*`, `Fiji*`, `French Polynesia`, `Humboldt Current`</small> |
| **b_indian_ocean** | 2 | — | — | — | <small>`Indian Ocean`, `Bay of Bengal`, `Arabian Sea`, `Mozambique Channel`, `Red Sea`, `Persian Gulf`, `Andaman Sea`, `Madagascar`, `Maldives`, `Seychelles`, `Western Indian Ocean`, `Eastern Indian Ocean`</small> |
| **b_southern_ocean** | 1 | — | — | — | <small>`Southern Ocean`, `Antarctic`, `sub-Antarctic`, `Kerguelen`, `South Georgia`, `Patagonian shelf`</small> |
| **b_arctic_ocean** | 2 | — | — | — | <small>`Arctic Ocean`, `Arctic`, `Greenland Sea`, `Beaufort Sea`, `Chukchi Sea`, `Canadian Arctic`</small> |
| **b_mediterranean** | 1 | — | — | — | <small>`Mediterranean`, `Adriatic`, `Aegean`, `Tyrrhenian`, `Ionian Sea`, `Ligurian Sea`, `Alboran Sea`, `Strait of Gibraltar`, `Strait of Sicily`</small> |
| **b_caribbean** | 2 | — | — | — | <small>`Caribbean`, `Gulf of Mexico`, `Bahamas`, `Belize`, `Mesoamerican Reef`, `Antilles`, `West Indies`</small> |

---

## `sb_` — Ocean Sub-basin

**Schema proposal:** [`ocean_basin_proposal.md`](ocean_basin_proposal.md)  
**Number of columns:** 43  
**Section weights:** Title: **2.0** / Keywords: **2.0** / Abstract: **0.5** / Introduction: **1.0** / Methods: **1.0** / Results: **0.5** / Results And Discussion: **0.5** / Discussion: **0.5** / Conclusions: **0.5** / Other: **0.25**

| Column | Threshold | Anchors | Case-sensitive | Prereq | Terms |
|---|---|---|---|---|---|
| **sb_north_sea** | 2 | — | — | — | <small>`North Sea`</small> |
| **sb_norwegian_sea** | 2 | — | — | — | <small>`Norwegian Sea`</small> |
| **sb_barents_sea** | 2 | — | — | — | <small>`Barents Sea`</small> |
| **sb_baltic_sea** | 2 | — | — | — | <small>`Baltic Sea`</small> |
| **sb_celtic_sea** | 2 | — | — | — | <small>`Celtic Sea`</small> |
| **sb_irish_sea** | 2 | — | — | — | <small>`Irish Sea`</small> |
| **sb_english_channel** | 2 | — | — | — | <small>`English Channel`, `La Manche`</small> |
| **sb_bay_of_biscay** | 2 | — | — | — | <small>`Bay of Biscay`, `Biscay`</small> |
| **sb_azores** | 2 | — | — | — | <small>`Azores`</small> |
| **sb_gulf_of_maine** | 2 | — | — | — | <small>`Gulf of Maine`</small> |
| **sb_gulf_of_mexico** | 2 | — | GOM | — | <small>`Gulf of Mexico`, `GoMex`, `GOM`</small> |
| **sb_caribbean_sea** | 2 | — | — | — | <small>`Caribbean Sea`, `Caribbean`, `Antilles`, `West Indies`</small> |
| **sb_bahamas** | 2 | — | — | — | <small>`Bahamas`, `Bahamian`</small> |
| **sb_sargasso_sea** | 2 | — | — | — | <small>`Sargasso Sea`</small> |
| **sb_gulf_of_guinea** | 2 | — | — | — | <small>`Gulf of Guinea`</small> |
| **sb_benguela** | 2 | — | — | — | <small>`Benguela`, `Benguela Current`</small> |
| **sb_alboran_sea** | 2 | — | — | — | <small>`Alboran Sea`, `Alboran`</small> |
| **sb_ligurian_sea** | 2 | — | — | — | <small>`Ligurian Sea`</small> |
| **sb_tyrrhenian_sea** | 2 | — | — | — | <small>`Tyrrhenian Sea`, `Tyrrhenian`</small> |
| **sb_adriatic_sea** | 2 | — | — | — | <small>`Adriatic Sea`, `Adriatic`</small> |
| **sb_ionian_sea** | 2 | — | — | — | <small>`Ionian Sea`, `Ionian`</small> |
| **sb_aegean_sea** | 2 | — | — | — | <small>`Aegean Sea`, `Aegean`</small> |
| **sb_black_sea** | 2 | — | — | — | <small>`Black Sea`</small> |
| **sb_sea_of_marmara** | 2 | — | — | — | <small>`Sea of Marmara`, `Marmara`</small> |
| **sb_red_sea** | 2 | — | — | — | <small>`Red Sea`</small> |
| **sb_arabian_sea** | 2 | — | — | — | <small>`Arabian Sea`</small> |
| **sb_persian_gulf** | 2 | — | — | — | <small>`Persian Gulf`, `Arabian Gulf`</small> |
| **sb_bay_of_bengal** | 2 | — | — | — | <small>`Bay of Bengal`</small> |
| **sb_andaman_sea** | 2 | — | — | — | <small>`Andaman Sea`</small> |
| **sb_mozambique_channel** | 2 | — | — | — | <small>`Mozambique Channel`</small> |
| **sb_gulf_of_california** | 2 | — | — | — | <small>`Gulf of California`, `Sea of Cortez`, `Sea of Cortés`, `GoCali`</small> |
| **sb_gulf_of_alaska** | 2 | — | — | — | <small>`Gulf of Alaska`</small> |
| **sb_bering_sea** | 2 | — | — | — | <small>`Bering Sea`</small> |
| **sb_sea_of_okhotsk** | 2 | — | — | — | <small>`Sea of Okhotsk`</small> |
| **sb_sea_of_japan** | 2 | — | — | — | <small>`Sea of Japan`, `East Sea`</small> |
| **sb_east_china_sea** | 2 | — | — | — | <small>`East China Sea`</small> |
| **sb_south_china_sea** | 2 | — | — | — | <small>`South China Sea`</small> |
| **sb_yellow_sea** | 2 | — | — | — | <small>`Yellow Sea`</small> |
| **sb_philippine_sea** | 2 | — | — | — | <small>`Philippine Sea`, `Philippines`</small> |
| **sb_coral_sea** | 2 | — | — | — | <small>`Coral Sea`</small> |
| **sb_tasman_sea** | 2 | — | — | — | <small>`Tasman Sea`</small> |
| **sb_hawaii** | 2 | — | — | — | <small>`Hawaii`, `Hawaiian Island*`, `Hawaiian archipelago`</small> |
| **sb_california_current** | 2 | — | — | — | <small>`California Current`</small> |

---
