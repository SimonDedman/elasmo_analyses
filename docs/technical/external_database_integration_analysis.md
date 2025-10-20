---
editor_options:
  markdown:
    wrap: 72
---

# External Database Integration Analysis

## Overview

This document analyzes the roles, content, and integration opportunities
between **Shark-References**, **Sharkipedia**, and the **EEA 2025 Data
Panel Literature Review Database**.

**Purpose:** Identify synergies, avoid duplication, and plan data flow
(pulling from vs pushing to) between systems.

---

## 1. Comparison Table

| Aspect | Shark-References | Sharkipedia | EEA 2025 Lit Review DB |
|--------|------------------|-------------|------------------------|
| **Primary Focus** | Bibliography | Trait data | Analytical methods & technology trends |
| **Scope** | All chondrichthyan literature | Species traits & ecology | Emerging technologies in shark research |
| **Coverage** | >30,000 references (comprehensive) | >1,200 species | ~5,000-10,000 papers (filtered) |
| **Data Type** | Bibliographic metadata (title, authors, journal, year, abstract) | Species-specific traits (length, maturity, diet, habitat, ecological roles) | Paper metadata + disciplines + methods + species + geography |
| **Temporal Range** | Historical to current (all years) | Pooled across studies (current best estimates) | Emphasis on recent (2000-2025) |
| **Primary Users** | Researchers, students, public | Researchers, conservation planners, modelers | Conference attendees, method practitioners |
| **Data Entry** | Curated by maintainers | Community contributions + curated | Project-specific (reviewers + automation) |
| **Access** | Web search + CSV export (limited) | Web UI + CSV download + API (planned?) | DuckDB/Parquet + Git repository |
| **Update Frequency** | Ongoing | Ongoing | One-time (with post-conference updates) |
| **Institution** | Zoologische Staatssammlung München (ZSM) | Florida International University | AES / Project-specific |
| **Maintainers** | Jürgen Pollerspöck & team | Lindsay French, Maurits van Zinnicq Bergmann, et al. | Simon Dedman, Guuske Tiktak, et al. |

---

## 2. Detailed Role Analysis

### 2.1 Shark-References

**What it does:**
- Comprehensive bibliography of all chondrichthyan literature
- Fulltext search across >30,000 papers
- Species-specific reference lists
- Author-specific publication lists
- Geographic and temporal filtering

**What it doesn't do:**
- Extract/synthesize data from papers
- Track analytical methods or technologies
- Provide trait data for species
- Enable multi-label classification of papers

**Strengths:**
- Most comprehensive chondrichthyan bibliography
- Curated by experts
- Free public access
- CSV export for species lists
- Long-standing reputation (trusted source)

**Limitations:**
- No API for programmatic access
- 3-letter indexing (search precision limited)
- 2,000 reference download limit
- No method/technology categorization
- No multi-label paper classification

---

### 2.2 Sharkipedia

**What it does:**
- Species-specific trait database
- Life history (length, maturity, growth)
- Ecology (diet, habitat, depth, migration)
- **Ecological roles** (predation, risk effects, trophic cascades,
  competition, facilitation, nutrient cycling)
- Conservation status (IUCN, threats)
- Community contributions via upload template

**What it doesn't do:**
- Store full bibliographic metadata (only reference IDs)
- Track analytical methods used in studies
- Provide comprehensive literature search
- Multi-paper synthesis (stores best estimates, not all studies)

**Strengths:**
- Trait-focused (enables modeling, conservation planning)
- Community contribution model
- Standardized trait schema
- Ecological role evidence (Effect Size + Strength of Evidence)
- Web UI + planned API

**Limitations:**
- Requires manual trait extraction from papers
- No method/technology categorization
- Limited to species-level data (no multi-species comparisons)
- Reference tracking minimal (DOI or short code)

**Upload Template Schema:**
- `species_superorder`, `species_name`, `marine_province`,
  `location_name`
- `trait_class`, `trait_name`, `standard_name`, `method_name`,
  `model_name`
- `value`, `value_type`, `precision`, `sample_size`
- `resource_doi`, `contributor_id`, `notes`

**Ecological Role Traits:**
- Direct Predation (effect size, strength of evidence)
- Risk Effects
- Trophic Cascade
- Competition
- Facilitation
- Nutrient Cycling (carcass deposition, bioturbation, excretion,
  sharks as food)

---

### 2.3 EEA 2025 Literature Review Database

**What it does:**
- Systematic review of **emerging technologies and analytical
  approaches**
- Multi-label classification:
  - Disciplines (8 categories)
  - Analytical methods (~150 approaches)
  - Species studied (~1,200)
  - Geographic scope (author nations, ocean basins)
- Temporal trends (method adoption over time)
- Method co-occurrence analysis
- Research capacity mapping (author institutions)
- **Potential:** Ecological role evidence extraction (annotations
  table)

**What it doesn't do:**
- Comprehensive bibliography (filtered to analytical methods focus)
- Species trait data (stores which species studied, not trait values)
- Public access initially (conference-focused, then open)

**Strengths:**
- Multi-label classification (papers span multiple disciplines/methods)
- Method-focused (unique niche)
- Temporal trend analysis
- Wide sparse schema optimized for cross-cutting queries
- Potential for ecological role evidence tracking

**Limitations:**
- Narrower scope than Shark-References (method-focused)
- One-time effort (not continuously updated like Shark-Refs)
- Requires manual/semi-automated review (labor-intensive)
- No trait extraction (focus on methods, not results)

---

## 3. Data Flow Analysis

### 3.1 PULLING FROM External Databases

#### From Shark-References → EEA Database

**What we pull:**
- Bibliographic metadata (title, authors, year, journal, DOI, abstract)
- Initial candidate papers via automated searches
- Species-specific reference lists (optional)

**How:**
- Automated form-based POST requests (scripts created)
- CSV download and parsing
- Import to DuckDB database

**Benefits:**
- Leverage comprehensive chondrichthyan-specific bibliography
- Automated batch searching (saves manual effort)
- Chondrichthyan-focused (all papers in-scope for taxa)

**Challenges:**
- No official API (form-based workaround)
- 2,000 reference limit per search (requires refined terms)
- 3-letter indexing (some precision loss)
- Rate limiting required (conservative delays)

**Status:** Scripts ready (Python & R), awaiting permission from
maintainers

---

#### From Sharkipedia → EEA Database

**What we could pull:**
- Species list with taxonomy (genus, species, superorder)
- Common names for species
- **Potential:** Existing ecological role evidence (to avoid
  duplication)

**How:**
- API (if available) or CSV download
- Parse species list → generate `sp_*` columns
- Map taxonomy → auto-populate `so_*` (superorder) columns

**Benefits:**
- Authoritative species list (curated)
- Common names for human-readable reports
- Taxonomic hierarchy for aggregation

**Challenges:**
- API availability unclear (need to confirm with maintainers)
- Ecological role data may not be comprehensive yet

**Status:** Need to contact Sharkipedia team (SD action)

---

### 3.2 PUSHING TO External Databases

#### From EEA Database → Shark-References

**What we could push:**
- None (Shark-References is comprehensive, we're a subset)

**Rationale:**
- Shark-References already indexes all chondrichthyan literature
- Our database is a **filtered view** (method-focused)
- No added value to pushing data back

---

#### From EEA Database → Sharkipedia

**What we could push:**
- **Ecological role evidence** from reviewed papers
- Method metadata (which analytical approaches used for which traits)

**How:**
- Extract from **annotations table** (subjective assessments)
- Map to Sharkipedia trait schema:
  - `trait_class` = "Ecological Role"
  - `trait_name` = "Direct Predation" / "Risk Effects" / etc.
  - `standard_name` = "Effect size" / "Strength of evidence"
  - `value` = "High" / "Medium" / "Low" (or numeric)
  - `resource_doi` = Paper DOI
  - `method_name` = Analytical approach used
- Create Sharkipedia upload template (CSV)
- Submit via manual or automated upload

**Benefits:**
- **Populate Sharkipedia with method metadata** (which analyses used
  for which ecological roles)
- **Expand ecological role evidence base** (more papers reviewed)
- **Benefit community** (accessible via Sharkipedia web UI)
- **Reduce duplication** (one central database for ecological roles)

**Challenges:**
- Requires manual annotation of papers for ecological role evidence
  (labor-intensive)
- Sharkipedia upload process may require manual review
- Need to map our schema to Sharkipedia schema (not 1:1)

**Workflow:**

``` r
# Extract ecological role annotations from EEA database
annotations <- dbGetQuery(conn, "
  SELECT study_id, doi, species_name, annotation_type, annotation_text
  FROM study_annotations
  WHERE annotation_type IN ('effect_size', 'strength_of_evidence')
")

# Map to Sharkipedia template
sharkipedia_upload <- annotations %>%
  mutate(
    resource_doi = doi,
    species_superorder = case_when(
      species_name %in% shark_species ~ "Gaelomorph Sharks",
      species_name %in% ray_species ~ "Batoidea",
      TRUE ~ "Unknown"
    ),
    species_name = species_name,
    trait_class = "Ecological Role",
    trait_name = str_extract(annotation_text, "Direct Predation|Risk Effect|Trophic Cascade|Competition|Facilitation"),
    standard_name = annotation_type,  # "Effect size" or "Strength of evidence"
    value = str_extract(annotation_text, "High|Medium|Low"),
    method_name = # Extract from analysis_approach columns
  )

# Export as CSV
write_csv(sharkipedia_upload, "sharkipedia_upload_eea2025.csv")
```

**Status:** Long-term goal (Phase 8), not critical for conference

---

## 4. Integration Opportunities

### 4.1 Synergies (Mutually Beneficial)

1.  **Species Taxonomy Standardization**

    -   **Pull from:** Sharkipedia species list
    -   **Use in:** EEA database `sp_*` columns
    -   **Benefit:** Consistent nomenclature across projects

2.  **Ecological Role Evidence**

    -   **Pull from:** Sharkipedia (existing evidence)
    -   **Push to:** Sharkipedia (new evidence from our review)
    -   **Benefit:** Central repository, avoid duplication, expand
        coverage

3.  **Method Metadata**

    -   **EEA unique contribution:** Which analytical methods used for
        which ecological role studies
    -   **Push to:** Sharkipedia (enhance method_name field)
    -   **Benefit:** Enable method-based filtering in Sharkipedia

4.  **Geographic Scope**

    -   **Pull from:** Sharkipedia (marine_province schema)
    -   **Use in:** EEA database (sub-basin mapping)
    -   **Benefit:** Consistent biogeographic regions

5.  **Reference Tracking**

    -   **Pull from:** Shark-References (comprehensive DOI list)
    -   **Link in:** Both EEA and Sharkipedia databases
    -   **Benefit:** Shared reference pool, reduce redundant data entry

### 4.2 Complementary Roles (Avoiding Duplication)

| Function | Shark-References | Sharkipedia | EEA Database |
|----------|------------------|-------------|--------------|
| **Comprehensive bibliography** | ✅ Primary | ❌ | ❌ Subset only |
| **Trait data** | ❌ | ✅ Primary | ❌ |
| **Ecological role evidence** | ❌ | ✅ Primary | 🔄 Can contribute |
| **Method categorization** | ❌ | ⚠️ Minimal | ✅ Primary |
| **Temporal trends** | ⚠️ Metadata only | ❌ | ✅ Primary |
| **Multi-label classification** | ❌ | ❌ | ✅ Primary |
| **Research capacity mapping** | ❌ | ❌ | ✅ Primary |

**Key Insight:** Our database fills a **methods/technology niche** not
covered by existing databases.

---

## 5. Potential Concerns & Mitigation

### 5.1 Duplication of Effort

**Concern:** Are we creating redundant infrastructure?

**Mitigation:**

-   **No:** Our focus is **analytical methods**, not traits or
    comprehensive bibliography
-   **Synergy:** We can **contribute ecological role evidence** to
    Sharkipedia (push data)
-   **Niche:** Multi-label classification and method trends are unique
-   **Temporary:** Our database is conference-specific, then archived
    (not ongoing maintenance burden)

### 5.2 Data Quality & Consistency

**Concern:** Multiple databases may have conflicting data

**Mitigation:**

-   **Pull authoritative data:** Use Sharkipedia for species taxonomy,
    Shark-References for bibliography
-   **Clear provenance:** Document data sources in our database
-   **Contribute back:** Push curated data to Sharkipedia (increases
    overall quality)

### 5.3 User Confusion

**Concern:** Community may be confused about which database to use

**Mitigation:**

-   **Clear documentation:** Explain our niche (methods, not traits)
-   **Cross-reference:** Link to Shark-References and Sharkipedia in
    our docs
-   **Complementary messaging:** "Use Shark-References for
    comprehensive bibliography, Sharkipedia for traits, EEA database
    for method trends"

---

## 6. Recommended Integration Plan

### Phase 1: Data Acquisition (Weeks 1-3)

1.  **Contact Sharkipedia team** (SD)
    -   Request species list (API or CSV)
    -   Discuss ecological role evidence overlap
    -   Propose future data contribution
2.  **Contact Shark-References maintainers** (SD)
    -   Request automation permission
    -   Acknowledge in all outputs
    -   Offer to share method categorization back (if useful)
3.  **Pull species taxonomy** from Sharkipedia
    -   Generate `sp_*` columns
    -   Create species → common name lookup
    -   Map superorder taxonomy

### Phase 2: Database Development (Weeks 3-5)

4.  **Pull bibliographic data** from Shark-References
    -   Automated searches
    -   CSV import to DuckDB
    -   Link to Shark-Refs IDs (`shark_refs_id` column)
5.  **Create separate annotations table** for ecological role evidence
    -   Modeled after EROS project structure
    -   Fields: `study_id`, `trait_name`, `effect_size`,
        `strength_of_evidence`, `method_used`
6.  **Enable manual annotation** during review
    -   Reviewers flag papers with ecological role evidence
    -   Capture in annotations table

### Phase 3: Post-Conference Data Sharing (Phase 8)

7.  **Extract ecological role evidence** from annotations
    -   Map to Sharkipedia upload template
    -   Include method metadata (unique contribution)
8.  **Coordinate with Sharkipedia team**
    -   Review data before upload
    -   Bulk upload process (manual or API)
    -   Acknowledge EEA 2025 Data Panel as contributor
9.  **Publish EEA database** with clear documentation
    -   Zenodo/Dryad with DOI
    -   Link to Shark-References and Sharkipedia
    -   Explain complementary roles

---

## 7. Benefits Summary

### To Shark-References

-   **Minimal direct benefit** (they're already comprehensive)
-   **Potential:** Method categorization could be added to their
    database (if they want it)
-   **Acknowledgment:** Increased visibility via our conference
    presentation and publication

### To Sharkipedia

-   ✅ **Expanded ecological role evidence** (more papers reviewed)
-   ✅ **Method metadata** (which analyses used for which ecological
    roles)
-   ✅ **Community engagement** (more contributors aware of upload
    process)
-   ✅ **Cross-validation** (our review may identify gaps in their
    data)

### To EEA Database (Our Project)

-   ✅ **Authoritative species taxonomy** (from Sharkipedia)
-   ✅ **Comprehensive bibliography** (from Shark-References)
-   ✅ **Reduced duplication** (don't re-create species lists or
    bibliographies)
-   ✅ **Credibility** (build on established databases)
-   ✅ **Long-term impact** (contribute back to community resources)

### To Research Community

-   ✅ **Complementary resources** (bibliography + traits + methods)
-   ✅ **Improved data quality** (cross-validation between databases)
-   ✅ **Enhanced discoverability** (linked databases)
-   ✅ **Reduced redundant effort** (shared infrastructure)

---

## 8. Drawbacks & Risks

### Potential Drawbacks

1.  **Dependency risk:** If Shark-References or Sharkipedia change
    access policies, our workflows may break
    -   **Mitigation:** Archive downloaded data, document
        alternatives

2.  **Data quality dependency:** If source databases have errors, we
    inherit them
    -   **Mitigation:** Cross-validate, document provenance, manual
        QC

3.  **Coordination overhead:** Requires communication with multiple
    teams
    -   **Mitigation:** SD has informal relationships, keep
        communication lightweight

4.  **Upload approval delays:** Sharkipedia may review/reject
    contributions
    -   **Mitigation:** Treat as long-term goal (not critical for
        conference)

### Risks If We DON'T Integrate

1.  **Reinventing the wheel:** Create redundant species lists,
    bibliographies
2.  **Lower quality:** Less authoritative than curated sources
3.  **Community fragmentation:** Yet another isolated database
4.  **Missed opportunities:** Don't contribute back to community
    resources

**Conclusion:** Benefits of integration **far outweigh** drawbacks.

---

## 9. Other Relevant Projects?

### Potential Additional Databases

1.  **FishBase** (<https://www.fishbase.org/>)

    -   Comprehensive fish species database
    -   Includes chondrichthyans
    -   Trait data (length, maturity, habitat)
    -   **Overlap with Sharkipedia:** Significant (Sharkipedia more
        shark-specific)
    -   **Relevance:** Could use for species list if Sharkipedia
        unavailable

2.  **IUCN Red List** (<https://www.iucnredlist.org/>)

    -   Conservation status for all species
    -   Threat assessments
    -   **Integration:** Pull conservation status for `sp_*` species
    -   **Relevance:** Useful for conservation-focused analyses

3.  **Catalog of Fishes** (California Academy of Sciences)

    -   Taxonomic authority
    -   Comprehensive species list
    -   **Integration:** Use for taxonomy validation
    -   **Relevance:** Backup for species nomenclature

4.  **GBIF** (Global Biodiversity Information Facility)

    -   Species occurrence data
    -   Geographic distributions
    -   **Integration:** Could map study locations to occurrence
        hotspots
    -   **Relevance:** Low (our focus is methods, not biogeography)

**Recommendation:** Focus on Shark-References and Sharkipedia
(chondrichthyan-specific). Use FishBase or Catalog of Fishes as
fallbacks only.

---

## 10. Decision Matrix

| Integration Action | Effort | Benefit | Priority | Owner | Status |
|--------------------|--------|---------|----------|-------|--------|
| Contact Sharkipedia for species list | Low | High | 🔴 Critical | SD | ⏳ Pending |
| Contact Shark-References for automation | Low | High | 🔴 Critical | SD | ⏳ Pending |
| Pull species taxonomy from Sharkipedia | Medium | High | 🔴 Critical | Assistant | ⏳ Pending (blocked by contact) |
| Pull bibliography from Shark-References | Medium | High | 🔴 Critical | Assistant | ⏳ Ready (awaiting permission) |
| Design annotations table for ecological roles | Low | Medium | 🟡 High | Assistant | ⏳ Pending |
| Extract & push ecological role evidence to Sharkipedia | High | Medium | 🟢 Medium | SD + Assistant | ⏳ Long-term (Phase 8) |
| Cross-reference all databases in publications | Low | High | 🟡 High | SD | ⏳ Post-conference |

---

## 11. Communication Templates

### Email to Sharkipedia Team

**Subject:** EEA 2025 Data Panel - Integration Opportunities

**Body:**

> Hi [Sharkipedia Team],
>
> I'm leading a systematic literature review for the EEA 2025 Data Panel
> on emerging technologies in elasmobranch research. We're building a
> database to track analytical methods, species studied, and geographic
> scope across \~5,000-10,000 papers.
>
> I'd love to discuss integration opportunities:
>
> 1.  **Pull from Sharkipedia:** Could we use your species list
>     (taxonomy, common names) to standardize our species columns?
> 2.  **Push to Sharkipedia:** Our reviewers will annotate papers for
>     ecological role evidence (effect size, strength of evidence). We
>     could contribute this to Sharkipedia via your upload template,
>     including method metadata (which analytical approaches were used).
> 3.  **Avoid duplication:** We want to ensure our efforts complement
>     (not duplicate) Sharkipedia's excellent work.
>
> Could we schedule a brief call to discuss? I'm happy to share our
> database schema and discuss how we can contribute back to the
> community.
>
> Best,\
> Simon Dedman

### Email to Shark-References Team

**Subject:** Request for Automated Search Permission - EEA 2025 Data
Panel

**Body:**

> Dear Shark-References Team,
>
> I'm organizing a Data Panel for the American Elasmobranch Society 2025
> conference on emerging technologies in shark research. We're
> conducting a systematic literature review of \~5,000-10,000 papers
> focused on analytical methods.
>
> **Request:** Permission to run automated searches on your database
> using our Python/R scripts with conservative rate limiting (10-second
> delays between requests).
>
> **Details:**
>
> -   \~50-60 searches across 8 disciplines (e.g., `+telemetry +acoustic`,
>     `+stable +isotop*`)
> -   Conservative delays to avoid server load
> -   CSV download for import to our database
> -   All results will acknowledge Shark-References as the source
>
> **Benefits to Shark-References:**
>
> -   Increased visibility via conference presentation and publication
> -   Potential contribution of method categorization back to your
>     database (if useful)
>
> Could you advise on acceptable rate limits and any restrictions? We're
> happy to adjust our approach to accommodate your preferences.
>
> Thank you for maintaining this invaluable resource!
>
> Best,\
> Simon Dedman\
> [Contact details]

---

## 12. Summary & Recommendations

### Key Findings

1.  **Complementary roles:** Shark-References (bibliography),
    Sharkipedia (traits), EEA Database (methods)
2.  **No significant duplication:** Our method-focused niche is unique
3.  **Synergy opportunities:** Pull taxonomy from Sharkipedia, push
    ecological role evidence back
4.  **Community benefit:** Contribute to shared infrastructure, avoid
    fragmentation

### Recommended Actions

1.  ✅ **Contact Sharkipedia and Shark-References teams** (SD, Week 1)
2.  ✅ **Pull species taxonomy** from Sharkipedia (Assistant, Week 1-2)
3.  ✅ **Pull bibliography** from Shark-References (Assistant, Week
    2-3)
4.  ✅ **Design annotations table** for ecological role evidence
    (Assistant, Week 3)
5.  🔄 **Contribute ecological role evidence** to Sharkipedia (SD +
    Assistant, Post-conference)

### Long-Term Vision

-   **Integrated ecosystem:** Shark-References (discover papers) →
    Sharkipedia (extract traits) → EEA Database (track methods)
-   **Bidirectional data flow:** Pull authoritative data, push curated
    contributions
-   **Community resource:** Open access, cross-referenced, mutually
    reinforcing

---

*Last updated: 2025-10-02*\
*Status: Analysis complete, awaiting SD contact with external teams*
