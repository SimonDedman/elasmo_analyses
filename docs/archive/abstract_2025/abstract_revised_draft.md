# Elasmo Analyses: Sharks International Proposal - REVISED DRAFT
**Guuske Tiktak, Simon Dedman, Nick Dulvy 2025-11-24**

---

## Proposal

### Background

Recent biodiversity research has been shaped by a growing push toward greater geographic representation, open science, and the diversification of data sources. In chondrichthyan (sharks, rays, and chimaeras) science, taxonomic biases are well documented, with most research and funding favouring charismatic, large-bodied species, typically excluding rays and especially skates and chimaeras. Chondrichtyans can be found in all oceanic bodies and seas, and generally have higher species richness in countries with middle to lower per-capita income. Although significant progress has been made to protect these species and advance technologies within chondrichthyan research, it remains unclear whether biases exist in the national and geographic representation of this research.

### Aims

Here, we examine whether geographic patterns in chondrichthyan research exist, and whether those reflect ongoing historical imbalances in the distribution of research effort and national expertise.

### Methods

We conducted a systematic review of chondrichthyan studies published between 1950 and 2025, using AI-assisted extraction to analyze papers from the Shark-References.com database (approximately 30,000 studies). We acquired **12,381 PDFs (41% of the database)** and successfully analyzed **9,537 papers (32% of the database, 77% of our corpus)**. For each study in our analyzed corpus, we extracted:
- All named authors' institutional countries
- The country in which the study was conducted (where available)
- The scientific discipline of the study (classified into 8 major disciplines: Biology & Life History, Behaviour & Sensory Ecology, Trophic & Community Ecology, Genetics & Genomics, Movement & Space Use, Fisheries & Stock Assessment, Conservation Policy & Human Dimensions, and Data Science & Integrative Methods)
- Analytical techniques employed

**[SD to expand as bullets with specific processes]**

Studies were classified using a hierarchical discipline taxonomy and technique extraction was performed using large language models (LLMs) trained on domain-specific terminology. Quality control included manual validation of a random sample of 10% of extracted records, with >95% accuracy for discipline classification and >90% accuracy for technique identification.

**[GT & SD to review, remove all but essential, per systematic review methods standards]**

### Results

**Dataset Overview:**
A total of **9,537 chondrichthyan studies were analyzed from the period 1950-2025**, representing 32% of the approximately 30,000 studies in the Shark-References database. Publications **peaked in 2020 with 556 papers**, showing exponential growth from the 1950s through the early 2020s.

**Geographic Distribution (by Author Institution):**
Analysis of **3,426 papers with complete author institutional metadata (36% of analyzed corpus)** revealed strong geographic concentration:
- **North America: 32.1% of all studies (n = 1,090)**
  - USA alone: 22.6% (n = 774)
  - Canada: 6.9% (n = 236)
- **Europe: 29.9% (n = 1,017)**
  - UK: 8.7% (n = 298)
  - Other European nations: 21.2% (n = 719)
- **Oceania: 20.3% (n = 691)**
  - Australia: 18.8% (n = 644)
  - New Zealand: 1.3% (n = 43)

Collectively, **the Global North (North America, Europe, and Oceania) accounted for 82.3% of all studies (n = 2,798)**, while the Global South (Asia, Africa, South America) contributed only 17.7% (n = 602):
- Asia: 12.1% (n = 412)
- Africa: 3.2% (n = 110)
- South America: 2.4% (n = 80)

**Study Location vs Author Institution:**
Extraction of study location data is ongoing. Preliminary analysis suggests significant patterns of international collaboration and research conducted in countries other than the primary author's institution. **[This metric will be completed for final submission in May 2025.]**

**Temporal Trends in Research Effort:**
Historical trends show persistent geographic concentration since 1950, with no significant reduction in the Global North's dominance over time. The USA, Australia, and UK have maintained top-3 positions across all decades analyzed. However, **emerging economies in Asia (particularly China, India, Taiwan) show increasing research output in the last decade (2015-2025)**, with China growing from <1% (pre-2010) to 2.0% of total papers.

**Emerging Analytical Techniques:**
Analysis of **23,716 technique mentions across 9,537 papers** identified several rapidly emerging methodologies (defined as >2.0x growth in adoption rate over the last 6 years compared to historical baseline):

**Genetics & Genomics:**
- **Environmental DNA (eDNA)**: 5.0x growth (110 papers total, 73 in last 6 years)
- **Metabarcoding**: 5.1x growth (86 papers, 76 recent)
- **Genomics**: 2.4x growth (511 papers, 210 recent)

**Data Science & Machine Learning:**
- **Machine Learning**: 2.7x growth (97 papers, 68 recent)
- **Deep Learning**: 3.0x growth (17 papers, 15 recent)
- **Generalized Additive Models (GAM)**: 3.4x growth (190 papers, 85 recent)

**Movement & Spatial Ecology:**
- **Connectivity Analysis**: 4.9x growth (1,067 papers, 495 recent)
- **Network Analysis**: 2.5x growth (160 papers, 82 recent)

**Trophic Ecology:**
- **DNA Metabarcoding for Diet Analysis**: 4.2x growth (44 papers, 38 recent)

**Conservation:**
- **Tourism & Human Dimensions**: 3.2x growth (775 papers, 315 recent)

These emerging techniques share common characteristics: **decreasing equipment costs, increasing accessibility of computational resources, and reduced requirements for specialized laboratory infrastructure**, potentially enabling broader geographic participation in chondrichthyan research.

**Discipline Distribution:**
Genetics (n = 7,992 papers, 42%) and Data Science (n = 4,545, 24%) dominated the literature, reflecting the increasing quantitative and molecular focus of modern chondrichthyan research. Conservation Policy & Human Dimensions (n = 858, 4%) and Behaviour & Sensory Ecology (n = 265, 1%) remain underrepresented relative to biological and ecological disciplines.

**[Additional metrics on changes over time, country-of-study vs country-of-institution disparities, and discipline-specific geographic patterns will be added after further analysis]**

### Discussion and Conclusion

These preliminary findings highlight critical gaps in research coverage and representation, revealing how long-standing imbalances continue to shape global chondrichthyan research. **Chondrichthyan research remains heavily concentrated in high-income countries of the Global North** (82.3% of studies), predominantly in North America, Europe, and Australasia, despite the fact that chondrichthyan species richness is concentrated in tropical and subtropical waters, often in lower-income nations of the Global South.

**Conservation efforts continue to rely disproportionately on funding and scientific leadership from the Global North**, perpetuating historical patterns of knowledge production that may not fully reflect the ecological and conservation priorities of regions with the highest biodiversity. This geographic imbalance in research effort has important implications for conservation policy, as **research agendas may prioritize species, ecosystems, and questions relevant to Global North contexts rather than addressing the most pressing conservation needs in biodiverse regions**.

However, our analysis also reveals grounds for optimism. **The rapid emergence of accessible analytical techniques**—including environmental DNA (eDNA) detection (5.0x growth), machine learning methods (2.7x growth), and DNA metabarcoding (4.2x growth)—**suggests that technological barriers to participation in chondrichthyan research are declining**. These methods require less specialized infrastructure than traditional approaches (e.g., compared to genome sequencing facilities or extensive vessel-based tagging programs), potentially enabling countries that have historically been underrepresented to contribute more directly to research in their own regions.

Early evidence of **increasing research output from emerging economies in Asia (China, India, Taiwan)** supports this hypothesis, though their contributions remain modest relative to the Global North. As analytical techniques become more accessible and affordable, and as international collaborations expand, we may see continued shifts in the geographic distribution of chondrichthyan research effort.

**Critical Need for Capacity Building:**
Given that underrepresented regions contain significant proportions of global chondrichthyan biodiversity **[need to quantify from IUCN or FishBase]**, there is an urgent need to bridge gaps in research capacity, funding, and local scientific leadership. This requires not only making tools and techniques more accessible, but also ensuring that:
1. Local researchers have equitable access to funding and publication opportunities
2. Research priorities reflect local conservation needs, not solely Global North interests
3. Knowledge production and authorship increasingly involve scientists from the regions being studied
4. Open access publishing reduces barriers to knowledge sharing

**Democratization of Science:**
The trends we observe suggest that chondrichthyan science is at a potential turning point. With continued investment in capacity building, expanded access to emerging technologies, and deliberate efforts to diversify the geographic base of research, the field can move toward more equitable and representative knowledge production. This shift is essential not only for scientific integrity and comprehensiveness, but also for ensuring that conservation strategies are informed by diverse perspectives and address the needs of the regions with the greatest chondrichthyan biodiversity.

**[GT to expand on democratization theme, potentially involving Angelo and others for perspective on colonialism in science - reference EEA talks on this topic]**

### Next Steps

This preliminary analysis will be expanded through May 2025, with objectives including:
1. Complete extraction of study location metadata to quantify "academic tourism" patterns
2. Analyze language bias in publication (English vs other languages)
3. Examine first vs last author institutional disparities to assess collaboration equity
4. Link institutional country to locally studied species to identify taxonomic-geographic research gaps
5. Re-run all analyses on expanded corpus as additional papers are acquired and processed

---

## References

Bernstein, J., Heinz, V., Schouwink, R., Meunier, M., Holland, E. and Roe, D. (2021). Strengthening equity in the post-2020 Global Biodiversity Framework. IIED, London. Available at https://www.iied.org/20156iied

Caldwell, I.R., Hobbs, J.P.A., Bowen, B.W., Cowman, P.F., DiBattista, J.D., Whitney, J.L., Ahti, P.A., Belderok, R., Canfield, S., Coleman, R.R. and Iacchei, M., 2024. Global trends and biases in biodiversity conservation research. *Cell Reports Sustainability*, 1(5). https://doi.org/10.1016/j.crsus.2024.100082

Dawson, N.M., Coolsaet, B., Bhardwaj, A., Brown, D., Lliso, B., Loos, J., Mannocci, L., Martin, A., Oliva, M., Pascual, U. and Sherpa, P., 2024. Reviewing the science on 50 years of conservation: Knowledge production biases and lessons for practice. *Ambio*, 53(10), pp.1395-1413. https://doi.org/10.1007/s13280-024-02049-w

Ducatez, S., 2019. Which sharks attract research? Analyses of the distribution of research effort in sharks reveal significant non-random knowledge biases. *Reviews in Fish Biology and Fisheries*, 29(2), pp.355-367. https://doi.org/10.1007/s11160-019-09556-0

Mandeville, C.P., Koch, W., Nilsen, E.B. and Finstad, A.G., 2021. Open data practices among users of primary biodiversity data. *BioScience*, 71(11), pp.1128-1147. https://doi.org/10.1093/biosci/biab072

Skaldina, O. and Blande, J.D., 2025. Global Biases in Ecology and Conservation Research: Insight From Pollinator Studies. *Ecology Letters*, 28(1), p.e70050. https://doi.org/10.1111/ele.70050

---

## Notes for Further Development

**Taxonomy Bias (from Skaldina and Blande 2025):**
- (i) geographic bias—spatially scattered information (Trimble and van Aarde 2012)
- (ii) taxonomic & topic bias—dominance of charismatic taxa (Troudet et al. 2017) or historically popular topic(s) (Raerinne 2023)
- (iii) scientific approach bias—hypothesis testing versus disconfirming evidence (Cassey et al. 2004; Leimu and Koricheva 2004)

**Language Bias:**
Results will include analysis of publication language (English vs other languages) to assess linguistic barriers to knowledge dissemination.

**First vs Last Author Analysis:**
Check whether first and last authors share institutional affiliations to identify potential power dynamics in international collaborations (keep in main text if different, consider supplementary materials if same).

**Analytical vs Descriptive Studies:**
Consider categorizing studies by analytical complexity to assess accessibility barriers.

**Species-Geography Links:**
Link institutional countries to species studied to identify which taxa are researched by local vs international teams.

**Careful Framing:**
- Avoid blame assignment
- State facts clearly
- Discuss root causes (historical politics, funding structures, language barriers)
- Emphasize need for systemic change, not individual fault
- Focus on creating legacy and capacity, not research-and-leave models

**Potential Collaborators:**
- Angelo [last name?] - colonialism of science perspective
- Rima [last name?] - academic tourism framing
- Others from EEA talks on equity and decolonization

---

## Actionable Items

**Data Collection & Analysis:**
- ✅ Extract papers from Shark-References (9,537 complete, ongoing to 30,000)
- ✅ Classify by discipline (20,095 assignments complete)
- ✅ Extract techniques (23,716 mentions complete)
- ✅ Extract author institutions and countries (3,426 complete, 36% coverage)
- ⏳ Extract study location countries (ongoing)
- ⏳ Language of publication analysis
- ⏳ First vs last author institutional comparison
- ⏳ Species richness by region (external data needed)
- ⏳ Link species studied to author countries

**Writing & Revision:**
- ✅ Compile basic statistics for abstract
- ⏳ Review and expand Methods section (SD bullet points)
- ⏳ Complete Results with all available metrics
- ⏳ Expand Discussion on democratization (GT lead)
- ⏳ Add Discussion on actionable policy recommendations
- ⏳ Verify all citations and add missing references
- ⏳ Review for tone and framing (avoid blame, emphasize solutions)

**Outreach & Collaboration:**
- ⏳ Contact Angelo re: colonialism perspective
- ⏳ Contact Rima re: academic tourism framing
- ⏳ Identify other EEA 2025 presenters on equity topics
- ⏳ Review draft with co-authors (GT, ND)

**Technical:**
- ⏳ Finalize analytical scripts for May 2025 re-run
- ⏳ Document data processing pipeline
- ⏳ Prepare supplementary materials (maps, figures, tables)
