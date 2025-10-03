# Candidate Database Search Protocol

**Version:** 1.0
**Date:** 2025-10-03
**Purpose:** Comprehensive search protocol for identifying panel candidates across 8 elasmobranch analytical disciplines

---

## Search Phases

### Phase 1: Extract Existing Data (Local Files - No Web Search)

**Sources:**
1. `Final Speakers EEA 2025.xlsx` - data tab (99 unique people)
2. `docs/Expert_Recommendations_Comprehensive.md` (~40-50 recommended experts)
3. `docs/EEA2025_Data_Panel_Program_Timeline_Personnel.md` (panel team roster)

**Data to Extract:**
- Name, email, institution
- Discipline assignment & subdiscipline
- EEA_2025_status (presentation, poster, panel, or combinations)
- Source (EEA_rec, AI_rec, sec_rec, invited, confirmed, declined)
- Proposal_status (existing_EEA_2025, panel_candidate, panel_confirmed)

---

### Phase 2: Analytical Techniques Compilation

**Strategy:** Extract techniques from existing experts' work, then use to guide future searches

**Method:**
1. Review presentation titles from EEA 2025 data
2. Extract specific analytical methods mentioned
3. Group by discipline
4. Identify 2-3 cutting-edge techniques per discipline
5. Use technique list to guide web searches for additional experts

**Output:** `outputs/analytical_techniques_by_discipline.csv`

---

### Phase 3: Web Search Strategy

#### Search Prioritization

**Priority 1: Underrepresented Disciplines**
- 2. Behaviour & Sensory Ecology (2 presentations)
- 8. Data Science & Integrative Methods (2 presentations)
- 3. Trophic & Community Ecology (3 presentations)

**Priority 2: All Disciplines**
- Target: 5 new candidates per discipline = 40 total
- Focus on cutting-edge techniques identified in Phase 2

**Priority 3: Diversity Goals**
- Geographic: Africa, South America, Asia representation
- Career stage: Early career researchers (PhD, postdoc)
- Gender: Balanced representation

#### Search Queries by Discipline

**Time Range:** 2009-2025 (all queries)

**1. Biology, Life History, & Health:**
- "elasmobranch age growth radiocarbon 2009-2025"
- "shark ray reproductive biology hormones 2009-2025"
- "elasmobranch disease parasites health 2009-2025"

**2. Behaviour & Sensory Ecology:**
- "shark sensory ecology electrosensory olfaction 2009-2025"
- "elasmobranch behavior acoustic telemetry 2009-2025"
- "shark social behavior aggregation 2009-2025"

**3. Trophic & Community Ecology:**
- "shark trophic ecology stable isotopes food web 2009-2025"
- "elasmobranch community ecology predator prey 2009-2025"
- "shark dietary analysis metabarcoding 2009-2025"

**4. Genetics, Genomics, & eDNA:**
- "elasmobranch population genomics conservation 2009-2025"
- "shark eDNA environmental DNA detection 2009-2025"
- "elasmobranch phylogenomics evolution 2009-2025"

**5. Movement, Space Use, & Habitat Modeling:**
- "shark satellite telemetry migration 2009-2025"
- "elasmobranch habitat modeling SDM MaxEnt 2009-2025"
- "shark acoustic telemetry network connectivity 2009-2025"

**6. Fisheries, Stock Assessment, & Management:**
- "elasmobranch stock assessment population dynamics 2009-2025"
- "shark bycatch mitigation fisheries 2009-2025"
- "ray fishery management sustainability 2009-2025"

**7. Conservation Policy & Human Dimensions:**
- "shark conservation policy CITES regulations 2009-2025"
- "elasmobranch human dimensions social science 2009-2025"
- "shark marine protected area MPA effectiveness 2009-2025"

**8. Data Science & Integrative Methods:**
- "elasmobranch machine learning AI classification 2009-2025"
- "shark citizen science data integration 2009-2025"
- "elasmobranch database synthesis meta-analysis 2009-2025"

#### Information to Extract per Candidate

**1. Demographics:**
- Name (First, Last, Prefix)
- Putative age (estimated from CV/career stage)
- Sex/gender (from pronouns/bio when available)
- Institution
- Country
- Continent

**2. Academic Profile:**
- Seniority: professor, associate professor, assistant professor, postdoc, PhD, masters, other
- Total publication count (from Google Scholar if available)
- First-author publications in last 5 years (2020-2025)
- h-index (if easily accessible)

**3. Expertise:**
- Primary discipline (one of 8)
- Subdiscipline (specific area within discipline)
- Analytical techniques (specific methods/tools)
- Study taxa (species/families)
- Study regions

**4. Conference History:** *(Lower priority - only if easily found)*
- EEA attendance history (search "EEA conference" + name)
- AES attendance history (search "AES meeting" + name)
- SI attendance history (search "Sharks International" + name)

**5. Status:**
- Attending EEA 2025? (Yes/No/Unknown)
- EEA_2025_status (panel, presentation, poster, or combinations with "-"; blank if not attending)
- Source (EEA_rec, AI_rec, sec_rec, invited, confirmed, declined, web_search)
- Proposal_status (existing_EEA_2025, panel_candidate, panel_confirmed, new_candidate)

#### Data Verification Strategy

- **Accuracy:** Cross-reference names with institution websites
- **Metrics:** Use Google Scholar for publication counts when available
- **Uncertainty:** Flag uncertain data with "[estimated]" or "[unclear]" tags
- **Missing data:** Leave cells blank rather than guessing
- **Privacy:** Avoid scraping email addresses from public sources

#### Search Limits

- **Target:** 5 new candidates per discipline = 40 total
- **Focus:** Recent publications (last 5 years preferred)
- **Geographic diversity:** Aim for 2-3 candidates per underrepresented region
- **Career diversity:** Include early-career researchers (PhD/postdoc)
- **Quality over quantity:** Prioritize well-documented candidates over incomplete profiles

---

## Output Files

### Primary Output
`outputs/candidate_database_comprehensive.csv`

**Column Structure:**
1. name_first
2. name_last
3. name_prefix
4. putative_age
5. sex
6. institution
7. continent
8. country
9. seniority
10. publication_count_total
11. publication_count_first_author_5yr
12. h_index
13. discipline_primary
14. subdiscipline
15. analytical_techniques
16. study_taxa
17. study_regions
18. attending_eea_2025
19. eea_attendance_history
20. aes_attendance_history
21. si_attendance_history
22. eea_2025_status
23. source
24. proposal_status
25. email *(only for existing EEA 2025 attendees)*

### Secondary Outputs
- `outputs/analytical_techniques_by_discipline.csv` - Technique compilation
- `outputs/candidate_search_log.txt` - Search queries used and results found
- `outputs/candidates_by_discipline_summary.csv` - Count summary

---

## Implementation Notes

**Phase 1 (Local Data):**
- Start with EEA 2025 attendees (most complete data)
- Add panel candidates from documentation
- This forms the "existing" candidate pool

**Phase 2 (Techniques):**
- Extract from presentation titles and abstracts
- Group by discipline
- Identify gaps in techniques coverage

**Phase 3 (Web Search):**
- Execute after reviewing Phase 1 results
- May adjust target numbers based on existing pool size
- Time investment TBD based on needs

---

**Status:** Phase 1 ready to execute
**Next Review:** After Phase 1 completion, before Phase 2
