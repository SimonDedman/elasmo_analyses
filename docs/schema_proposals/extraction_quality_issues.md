# Extraction Quality Issues Framework

Catalogue of known false-positive patterns and proposed fixes for `extract_schema_columns.py`, based on coauthor review of `schema_extraction_evidence_by_coauthor`.

GitHub issue: [#7 Threshold and anchor decisions](https://github.com/SimonDedman/elasmo_analyses/issues/7)
Schema definitions: [`scripts/extract_schema_columns.py` lines 92-292](https://github.com/SimonDedman/elasmo_analyses/blob/main/scripts/extract_schema_columns.py#L92-L292)

## Issue class codes

| Code | Name | Description | Fix complexity |
|------|------|-------------|----------------|
| **PDF** | PDF Mismatch | Wrong PDF assigned to literature_id | FIXED |
| **SM** | Subject Mismatch | Keyword pertains to non-elasmobranch subject | IMPLEMENTED |
| **AK** | Ambiguous Keyword | Keyword stem matches unrelated word | IMPLEMENTED |
| **AC** | Acronym Collision | Case-insensitive match hits different word | IMPLEMENTED |
| **RB** | Reference Bleed | Keywords matched in unstripped references | IMPLEMENTED |
| **CM/SW** | Contextual Mention / Section Weighting | Keyword is about elasmobranchs but paper doesn't study that topic | IMPLEMENTED |

---

## 1. PDF Mismatch (FIXED)

**Source:** David R-G review, rows 18-40 (lit_id 31532 got text from lit_id 31729)

**Root cause:** `_title_words()` called `_normalise_name()` on the full title, which strips spaces and concatenates all words into a single string. Disambiguation always returned 0 overlap, falling back to the first file alphabetically.

**Fix:** Changed `_title_words()` to use `title.lower()` instead of `_normalise_name(title)` so word boundaries are preserved. (Line 650)

**Impact:** Any pair of papers sharing the same first-author surname and year could have been swapped. Requires re-extraction.

---

## 2. Subject Mismatch (SM) — PROPOSED

Keyword appears in the paper but describes something other than a shark, ray, or chimaera.

**Examples:**
| Row | Column | Keyword | Actual subject |
|-----|--------|---------|----------------|
| R4 | `d_biomechanics` | hydrodynamic* | the embayment |
| R13 | `imp_abundance` | abundance | invertebrates |
| R42 | `d_behaviour` | behavio* | skipper behaviour |
| R113 | `imp_abundance` | abundance | plastics |
| R115 | `imp_biomass` | biomass | mixed catch, not elasmobranch-specific |
| R103 | `d_taxonomy` | taxonom* | invertebrate taxonomy |

**Proposed fix — elasmobranch proximity check:**
For each keyword hit, check whether an elasmobranch reference (species name, common name, or higher taxon) appears within the same sentence or +/-1 sentence. If absent, downweight or flag the match. Build the term set from existing species columns + common names (shark, ray, skate, chimaera, dogfish, guitarfish, sawfish, etc.) + higher taxa (Chondrichthyes, Elasmobranchii, Batoidea, Selachii).

Opt-in per column: apply for generic terms (`imp_abundance`, `d_behaviour`, `d_biomechanics`); skip for inherently elasmobranch-specific columns.

---

## 3. Ambiguous Keyword (AK) — PROPOSED

Keyword stem matches a completely different concept.

**Examples:**
| Row | Column | Keyword | Intended | Actual in context |
|-----|--------|---------|----------|-------------------|
| R12 | `eco_pelagic` | offshore | pelagic habitat | distance from shore ("30 m offshore") |
| R38,61,121 | `pr_fishing_recreational` | angl* | angling | geometric angle ("slope angle") |
| R110 | `eco_pelagic` | pelagic | pelagic habitat | "pelagic longlines" as ghost gear substrate |

**`eco_pelagic` keywords** (threshold=2): `pelagic`, `open ocean`, `oceanic`, `offshore`, `epipelagic`, `mesopelagic`, `bathypelagic`

**Proposed fixes:**
- Remove `offshore` from `eco_pelagic` or require co-occurrence with pelagic-specific terms
- Replace `angl*` with exact matches: `angling`, `angler`, `anglers`
- Audit all wildcard keywords for unintended stem matches: `behavio*`, `physiolog*`, `metaboli*`, `pollut*`, `contaminant*`, `taxonom*`, `phylogenet*`

---

## 4. Acronym Collision (AC) — PROPOSED

Case-insensitive matching hits a common lowercase word.

**Example:**
| Row | Column | Keyword | Intended | Actual in context |
|-----|--------|---------|----------|-------------------|
| R15 | `imp_physiology_stress` | RAMP | Reflex Action Mortality Predictor | boat ramp |

**All acronym keywords in schemas:**

| Acronym | Column | Definition |
|---------|--------|------------|
| IUU | `pr_fishing_iuu` | Illegal, Unreported, and Unregulated (fishing) |
| OMZ | `pr_hypoxia` | Oxygen Minimum Zone |
| PCB | `pr_pollution_chemical` | Polychlorinated Biphenyl |
| PFAS | `pr_pollution_chemical` | Per- and Polyfluoroalkyl Substances |
| ALAN | `pr_light` | Artificial Light At Night |
| EMF | `pr_electromagnetic` | Electromagnetic Field |
| BRUVs | `gear_survey` | Baited Remote Underwater Video stations |
| UAV | `gear_survey` | Unmanned Aerial Vehicle |
| ROV | `gear_survey` | Remotely Operated Vehicle |
| BRD | `gear_mit_brd` | Bycatch Reduction Device |
| TED | `gear_mit_brd` | Turtle Excluder Device |
| EPM | `gear_mit_deterrent` | Electropositive Metal |
| MPA | `gear_mit_time_area` | Marine Protected Area |
| PRM | `gear_mit_handling` | Post-Release Mortality |
| ALDFG | `gear_mit_ghost` | Abandoned, Lost, and Derelict Fishing Gear |
| PAL | `gear_mit_pinger` | Porpoise Alerting device |
| DOA | `imp_mortality` | Dead on Arrival |
| AVM | `imp_mortality` | At-Vessel Mortality |
| CPUE | `imp_cpue` | Catch Per Unit Effort |
| SSB | `imp_biomass` | Spawning Stock Biomass |
| RAMP | `imp_physiology_stress` | Reflex Action Mortality Predictor |
| WTP | `imp_economic` | Willingness To Pay |
| SPR | `imp_productivity` | Spawning Potential Ratio |
| eDNA | `d_genetics` | Environmental DNA |
| SNP | `d_genetics` | Single Nucleotide Polymorphism |
| MSY | `d_fisheries` | Maximum Sustainable Yield |
| CITES | `d_conservation` | Convention on International Trade in Endangered Species |
| IUCN | `d_conservation` | International Union for Conservation of Nature |

**Proposed rules:**
1. Tag acronym keywords with `case_sensitive=True`; match only uppercase occurrences
2. Optionally verify the expanded form appears nearby (e.g. "catch per unit effort (CPUE)")

---

## 5. Reference Bleed (RB) — PROPOSED

Reference sections not fully stripped; keywords match in reference titles, author affiliations, or journal names.

**Examples (lit_id 32709, Carrasco-Puig et al. 2024, heavy metals paper):**
| Row | Column | Keyword | False match source |
|-----|--------|---------|-------------------|
| R66 | `b_north_atlantic` | North Atlantic, etc. | Reference titles from other papers |
| R68 | `d_behaviour` | behavio* | Reference about porbeagle diving |
| R73 | `d_husbandry` | aquarium, captive | Reference about CA elasmobranch necropsies |
| R74 | `d_movement` | movement, archival tag | Reference about porbeagle movement |
| R75 | `d_physiology` | physiolog* | Reference about stress indicators |
| R83-87 | `gear_*` | artisanal, longline, circle hook | References and funding acknowledgements |
| R91-92 | `imp_mortality/post_release` | mortality, post-release | Reference titles |
| R97 | `b_north_pacific` | North Pacific | Reference title (catshark paper) |
| R104 | `d_toxicology` | contaminant, heavy metal | References |
| R118 | `imp_mortality` | mortality | References |
| R124 | `pr_pollution_noise` | sonar | Reference about tube-worm mapping |

David notes several references don't even belong to the paper — possibly PDF concatenation or a different Carrasco-Puig paper's references leaking in.

**Proposed fixes:**
- Audit and improve `_REF_HEADER_RE` regex for more formatting variants
- Fallback heuristic: if >60% of hits come from a single contiguous block near the end, flag as reference bleed
- For known problem papers, verify PDF contents match the expected paper

---

## 6. Contextual Mention (CM) — PROPOSED

Keyword correctly describes elasmobranchs but appears only in introductory/background context, not as a research focus.

**Examples:**
| Row | Column | Keyword(freq) | Context | Threshold |
|-----|--------|---------------|---------|-----------|
| R3 | `d_biology` | maturity(1) | boilerplate intro: "slow growth, late maturity, low fecundity" | 2 |
| R43 | `d_biology` | life history(1), longevity(2), maturity(4) | vulnerability context in bycatch paper | 2 |
| R45 | `d_physiology` | physiolog*(2), metaboli*(3), thermoregulat*(1) | explains temperature effects but doesn't study physiology | 2 |
| R55 | `imp_economic` | economic value(1) | justifies fisheries patterns, not study topic | 1 |
| R57 | `imp_post_release` | post-capture survival(1) | highlights importance but doesn't study it | 1 |
| R59 | `pr_climate_change` | climate change(2), ocean warming(1) | mentioned as driver, not the study goal | 3 |
| R101 | `d_movement` | movement(1), tracking(2) | embryo movement in egg case, not animal tracking | 3 |
| R111 | `gear_longline` | longline(3) | longlines as ghost gear substrate for eggs | 2 |
| R135 | `d_data_science` | Bayesian(1) | Bayesian model cited in review, paper doesn't analyse data | 2 |
| R141 | `d_taxonomy` | taxonom*(5) | used as context in a review | 1 |
| R209 | `d_biology` | maturity(7) | maturity as predictor variable, not study goal | 2 |
| R213 | `d_genetics` | phylogenet*(2) | phylogenetic traits as justification, not genetics | 2 |
| R214 | `d_physiology` | physiolog*(5), metaboli*(7) | physiological responses cited from bibliography, not measured | 2 |
| R224 | `imp_biomass` | biomass(9) | total biomass as predictor, not the outcome | 2 |

**Implemented solution — Section-weighted scoring (SW fix):**

Corpus survey of 208 papers (1970s–2020s) achieved 99.8% section header detection coverage. PDF text is parsed into labelled sections (Abstract, Introduction, Methods, Results, Results and Discussion, Discussion, Conclusions, Other). Each keyword match is multiplied by a section weight specific to the schema prefix:

| Schema | Primary (1.0) | Secondary (0.5) | Low-value (0.25) |
|--------|--------------|-----------------|-------------------|
| `eco_` | Introduction, Methods | Abstract, Results, R&D, Discussion, Conclusions | Other |
| `pr_` | Introduction, Methods, Discussion | Abstract, Results, Conclusions | Other |
| `gear_` | Methods | Abstract, Results, R&D | Introduction, Discussion, Conclusions, Other |
| `imp_` | Results, Discussion | Abstract, Methods, Conclusions | Introduction, Other |
| `d_` | Methods, Results | Abstract, Introduction, Discussion, Conclusions | Other |
| `b_` | Introduction, Methods | Abstract, Results, R&D, Discussion, Conclusions | Other |

Combined "Results and Discussion" sections receive the maximum of Results and Discussion weights (greedy). Papers without detectable section headers fall back to full-text scoring.

Evidence output now includes `raw_freq` (unweighted count for audit) and `section` (label of the primary match).

Processing order: RB (strip references) → SM (proximity check) → SW (section weighting) → AC (case-sensitive acronyms).

**Future refinements** (deferred pending re-extraction and review):
- Raise thresholds for columns prone to contextual mention
- Require anchor co-occurrence for borderline cases: e.g. `d_physiology` could require "measured", "sampled", "experiment", "assay"

---

## Review tracking

| Reviewer | Sheet | Rows reviewed | Issues found | Date |
|----------|-------|---------------|--------------|------|
| David Ruiz-Garcia | David Ruiz-Garcia | R2-R141 | 40+ | 2026-03-18 |
| Elena F. Corr | — | — | — | — |
| Guuske Tiktak | — | — | — | — |
| Simon Dedman | — | — | — | — |
| David Shiffman | — | — | — | — |

---

*Created: 2026-03-18. Update as more coauthor reviews are received.*
