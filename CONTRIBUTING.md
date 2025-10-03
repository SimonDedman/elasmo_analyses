# Contributing to Elasmobranch Analytical Methods Review

Thank you for your interest in contributing to this project! This document provides guidelines for different types of contributions.

---

## Ways to Contribute

### 1. Suggest New Analytical Techniques

If you know of analytical methods not currently captured in our review:

**Via GitHub Issues:**
1. Go to [Issues](../../issues)
2. Click "New Issue"
3. Use the "Suggest Technique" template
4. Provide:
   - Technique name and synonyms
   - Discipline category (1-8)
   - Key papers demonstrating the technique
   - Brief description (1-2 sentences)
   - Why it's important for elasmobranch research

**Via Email:**
Send to panel leaders with subject line "New Technique Suggestion: [Technique Name]"

---

### 2. Report Corrections

Found an error in discipline classifications, expert attributions, or documentation?

**Via GitHub Issues:**
1. Use the "Report Error" template
2. Specify:
   - Location of error (file name, line number if applicable)
   - Current incorrect information
   - Proposed correction
   - Source/reference for correction

**Via Pull Request:**
1. Fork the repository
2. Create a branch: `git checkout -b fix/your-correction`
3. Make changes
4. Commit: `git commit -m "Fix: [brief description]"`
5. Push and create pull request

---

### 3. Contribute to Discipline Reviews

Help expand or update systematic reviews for specific disciplines:

**Requirements:**
- Expertise in the relevant discipline
- Familiarity with PRISMA-SCR guidelines (training provided)
- Time commitment: ~5-10 hours over 2-3 weeks

**Process:**
1. Contact panel leaders expressing interest
2. Receive discipline-specific briefing materials
3. Complete template spreadsheet with technique inventory
4. Participate in expert panel discussion (optional)

**Disciplines currently seeking experts:**
- **Behaviour & Sensory Ecology** (high priority)
- **Trophic & Community Ecology** (high priority)
- All others welcome for assistant roles

---

### 4. Join as Panel Expert

Interested in joining future panel sessions at EEA or AES conferences?

**Eligibility:**
- Active researcher in elasmobranch science
- Established expertise in one of the 8 disciplines
- Available for conference attendance

**How to Apply:**
1. Email panel leaders with:
   - Brief CV or link to Google Scholar/ResearchGate profile
   - Primary discipline of expertise
   - Secondary/cross-cutting expertise (if applicable)
   - Conference attendance plans (EEA 2026, AES 2026, etc.)
   - Phonetic pronunciation of your name (for introductions)

---

## Code of Conduct

### Our Standards

- **Respectful:** Treat all contributors with respect regardless of experience level
- **Collaborative:** Work together to improve elasmobranch science
- **Credit:** Acknowledge contributions appropriately
- **Inclusive:** Welcome diverse perspectives and backgrounds

### Unacceptable Behavior

- Harassment or discrimination of any kind
- Plagiarism or failure to cite sources
- Deliberate misinformation
- Disrespect toward other researchers or methods

### Reporting

If you experience or witness unacceptable behavior, contact panel leaders privately.

---

## Contribution Guidelines

### For Code (R/Python Scripts)

**Style:**
- Follow tidyverse style for R: https://style.tidyverse.org/
- Follow PEP 8 for Python: https://pep8.org/
- Include comments explaining logic
- Add example usage in header

**Testing:**
- Test scripts with sample data before submitting
- Document expected inputs/outputs
- Note any package dependencies

**Pull Request Process:**
1. Create feature branch: `git checkout -b feature/script-name`
2. Add tests if applicable
3. Update documentation (README, inline comments)
4. Submit PR with clear description of changes

---

### For Documentation

**Markdown Style:**
- Use ATX-style headings (`#` not `===`)
- Include table of contents for long documents
- Use code fences with language tags
- Add links to related documents

**Structure:**
- Overview/purpose at top
- Clear section headings
- Examples where helpful
- References/citations at bottom

---

### For Data Contributions

**Species Data:**
- Use scientific names (binomial nomenclature)
- Cross-reference with Sharkipedia/FishBase
- Include common names if known
- Note any taxonomic uncertainties

**Literature Database:**
- Include DOI when available
- Use consistent date formats (YYYY-MM-DD)
- Binary columns: TRUE/FALSE (not 1/0, yes/no)
- Mark uncertainties in notes column

**Geographic Data:**
- Use ISO 3166-1 codes for countries
- Follow NOAA LME boundaries for basins
- Document coordinate systems if applicable

---

## Recognition

### How We Credit Contributors

**Major Contributors (≥10 hours):**
- Listed as co-authors on panel summary papers
- Acknowledged in presentation slides
- Listed in README acknowledgments section

**Minor Contributors (<10 hours):**
- Listed in README acknowledgments section
- Credited in specific files they contributed to
- Thanked in presentations

**Expert Panel Reviewers:**
- Co-authors on discipline-specific publications
- Listed as panelists in conference materials
- Acknowledged as experts in documentation

### Claiming Credit

When contributing, please indicate your preferred attribution:
- Full name (as you'd like it cited)
- Institutional affiliation
- ORCID (optional but recommended)
- Email (if you want to be contactable)

---

## Timeline & Deadlines

### Pre-Conference (Leading up to EEA 2025)

- **5 weeks before:** Expert recruitment closes
- **4 weeks before:** Technique inventories due
- **3 weeks before:** Literature review drafts due
- **2 weeks before:** Final revisions due
- **1 week before:** Presentation materials finalized

### Post-Conference

- **Week 1-2:** Panel insights synthesis
- **Week 3-4:** Database refinement
- **Month 2:** Public release preparation
- **Month 3+:** Ongoing updates accepted

### Rolling Contributions

Non-urgent contributions (typo fixes, documentation improvements) are welcome year-round and will be reviewed within 1-2 weeks.

---

## Questions?

**General Questions:**
- Post in [Discussions](../../discussions)

**Technical Issues:**
- Open an [Issue](../../issues)

**Private Inquiries:**
- Email panel leaders (see README for contact info)

**Expert Recruitment:**
- See [Expert_Recommendations_Comprehensive.md](docs/Expert_Recommendations_Comprehensive.md)

---

## License

By contributing, you agree that your contributions will be licensed under the same terms as the project (CC BY 4.0 for documentation, MIT for code).

---

Thank you for helping advance elasmobranch research!

*Last updated: 2025-10-02*
