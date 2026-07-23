# Candidate Database - Phase 1 Report

**Date:** 2025-10-03
**Status:** Phase 1 Complete - Local Data Extraction

---

## Summary

**Total Unique Candidates:** 106

### By Source
- **EEA 2025 Attendees:** 99 people
- **Panel Team (confirmed):** 5 people
- **Panel Candidates:** 2 people

### By Discipline

| Discipline | Candidate Count | % of Total |
|------------|-----------------|------------|
| 5. Movement, Space Use, & Habitat Modeling | 34 | 32.1% |
| 6. Fisheries, Stock Assessment, & Management | 16 | 15.1% |
| 7. Conservation Policy & Human Dimensions | 14 | 13.2% |
| 1. Biology, Life History, & Health | 13 | 12.3% |
| 4. Genetics, Genomics, & eDNA | 11 | 10.4% |
| 3. Trophic & Community Ecology | 3 | 2.8% |
| 2. Behaviour & Sensory Ecology | 2 | 1.9% |
| 8. Data Science & Integrative Methods | 2 | 1.9% |
| *Unassigned* | 11 | 10.4% |

---

## Underrepresented Disciplines

**Target:** 5+ candidates per discipline

### Critical Gaps
1. **2. Behaviour & Sensory Ecology** - Only 2 candidates
2. **8. Data Science & Integrative Methods** - Only 2 candidates
3. **3. Trophic & Community Ecology** - Only 3 candidates

These three disciplines need additional candidates from web search (Phase 3).

---

## Data Completeness

### Available Data
- ✅ **Names:** 106/106 (100%)
- ✅ **Institutions:** 97/106 (91.5%)
- ✅ **Disciplines:** 95/106 (89.6%)
- ✅ **EEA 2025 Status:** 104/106 (98.1%)
- ✅ **Study Taxa:** 76/106 (71.7%)
- ✅ **Study Regions:** 89/106 (84.0%)

### Missing Data (to be collected)
- ❌ **Age/Career Stage:** 0/106 (0%)
- ❌ **Sex/Gender:** 0/106 (0%)
- ❌ **Country/Continent:** 0/106 (0%)
- ❌ **Seniority:** 0/106 (0%)
- ❌ **Publication Counts:** 0/106 (0%)
- ❌ **Subdisciplines:** 0/106 (0%)
- ❌ **Analytical Techniques:** 0/106 (0%)
- ❌ **Conference History:** 0/106 (0%)

---

## Candidates by EEA 2025 Status

| Status | Count | Notes |
|--------|-------|-------|
| Presentation | 63 | Oral presenters |
| Poster | 36 | Poster presenters |
| Panel | 5 | Panel team members |
| Panel-Presentation | 0 | To be added manually |
| Unknown | 2 | Panel candidates (not yet confirmed) |

**Note:** Need to identify which panel members are also giving presentations (e.g., Amy Jeffries, Charlotte Nuyt, Edward Lavender, Nicholas Dulvy, Maria Dolores Riesgo should be "panel-presentation")

---

## Next Steps

### Phase 2: Analytical Techniques Compilation
**Goal:** Extract techniques from existing candidate presentations

**Method:**
1. Review presentation titles from EEA 2025 data
2. Extract specific analytical methods mentioned
3. Group techniques by discipline
4. Identify 2-3 cutting-edge techniques per discipline
5. Create `outputs/analytical_techniques_by_discipline.csv`

**Questions to Answer:**
- Which techniques are well-represented at EEA 2025?
- Which techniques are missing or underrepresented?
- Should we compile techniques first, or use candidate expertise to define techniques?

### Phase 3: Web Search (if needed)
**Target:** 5 additional candidates per underrepresented discipline

**Priority Disciplines:**
1. Behaviour & Sensory Ecology (need 3+ more)
2. Data Science & Integrative Methods (need 3+ more)
3. Trophic & Community Ecology (need 2+ more)

**Total Web Search Target:** ~15-20 new candidates

---

## Files Generated

### Primary Outputs
- ✅ `outputs/candidate_database_phase1.csv` (106 candidates, 24 columns)
- ✅ `outputs/candidates_by_discipline_phase1.csv` (discipline summary)
- ✅ `outputs/candidate_search_log.csv` (search provenance)

### Documentation
- ✅ `docs/Candidate_Search_Protocol.md` (complete protocol)
- ✅ `docs/Candidate_Database_Phase1_Report.md` (this report)

---

## Database Schema

**24 columns:**
1. name_first, name_last, name_prefix
2. putative_age, sex
3. institution, continent, country
4. seniority
5. publication_count_total, publication_count_first_author_5yr, h_index
6. discipline_primary, subdiscipline, analytical_techniques
7. study_taxa, study_regions
8. attending_eea_2025, eea_attendance_history, aes_attendance_history, si_attendance_history
9. eea_2025_status, source, proposal_status
10. email

---

## Recommendations

### Immediate Actions
1. **Review Phase 1 database** - Check for accuracy and completeness
2. **Decide on Phase 2 approach:**
   - Option A: Extract techniques from titles first, then use to guide web search
   - Option B: Skip technique extraction, proceed directly to web search for gap disciplines
3. **Manual corrections:**
   - Update panel members with presentation status (panel-presentation)
   - Fill in missing institutions for 9 candidates
   - Assign disciplines to 11 unassigned candidates

### Optional Enhancements
- Add email addresses for panel candidates (if available from documentation)
- Extract institution affiliations for panel team from web searches
- Cross-reference with Shark-References database for publication metrics

---

**Status:** ✅ Ready for Phase 2 review and decision
