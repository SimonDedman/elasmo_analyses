# EEA 2025 Data Panel Project - Claude Code Configuration

## Project Overview

This is a systematic literature review project for the European Elasmobranch Association (EEA) 2025 conference panel session on analytical techniques in elasmobranch research across 8 disciplines.

**Key Facts:**
- **Primary database:** Shark-References (https://shark-references.com) - 30,000+ chondrichthyan papers
- **Database format:** DuckDB (optimized for wide sparse schema with columnar storage)
- **Main databases:**
  - `shark_references.db` - Main bibliographic database (SQLite)
  - `database/technique_taxonomy.db` - Technique classification (208 techniques, SQLite)
  - `outputs/literature_review.duckdb` - DuckDB analytical database
- **Species count:** ~1,200 chondrichthyan species
- **Schema:** ~1,652 columns (wide sparse binary classification)

## The 8 Disciplines

1. **Biology, Life History, & Health** (BIO) - 28 techniques
2. **Behaviour & Sensory Ecology** (BEH) - 20 techniques
3. **Trophic & Community Ecology** (TRO) - 20 techniques
4. **Genetics, Genomics, & eDNA** (GEN) - 24 techniques
5. **Movement, Space Use, & Habitat Modeling** (MOV) - 31 techniques
6. **Fisheries, Stock Assessment, & Management** (FISH) - 34 techniques
7. **Conservation Policy & Human Dimensions** (CON) - 19 techniques
8. **Data Science & Integrative Methods** (DATA) - 32 techniques

## Important Project Constraints

### R vs Python Code
- R is the primary language for the research community
- Provide R code when the task is analytical or statistical in nature
- Python is fine for automation, web scraping, and data processing tasks
- Don't automatically create both versions unless specifically requested
- Prefer R packages for analysis: `{duckdb}`, `{duckplyr}`, `{tidyverse}`, `{data.table}`

### Database Schema Conventions
- **Discipline columns:** Prefix `d_` (e.g., `d_genetics_genomics`)
- **Author nations:** Prefix `auth_` (e.g., `auth_us`, `auth_au`)
- **Ocean basins:** Prefix `b_` (e.g., `b_north_atlantic`)
- **Sub-basins:** Prefix `sb_` (e.g., `sb_california_current`)
- **Superorders:** Prefix `so_` (e.g., `so_selachimorpha`, `so_batoidea`, `so_holocephali`)
- **Species:** Prefix `sp_` (e.g., `sp_carcharodon_carcharias`)
- **Analysis methods:** Prefix `a_` (e.g., `a_acoustic_telemetry`)

### Shark-References Automation Rules
- **Rate limiting:** Use 10-second delays between requests (conservative)
- **Search operators:**
  - `+word` = Required keyword (AND)
  - `-word` = Exclude keyword (NOT, requires + first)
  - `word*` = Wildcard prefix matching
  - `"exact"` = Exact phrase match
  - `word1 @10 word2` = Proximity search (within 10 words)
- **Limitation:** 3-letter minimum indexing (e.g., `+tel` matches `telemetry`)
- **Maximum results:** 2,000 references per search

## Common High-Priority Requests

### 1. PDF Acquisition & Organization
**Context:** Large-scale paper acquisition from multiple sources with complex download workflows.

**Common tasks:**
- Monitor download progress from logs (`logs/oa_download_log.csv`)
- Check Sci-Hub/institutional access status
- Organize downloaded PDFs by priority/status
- Track failed downloads and retry strategies
- Extract metadata from PDFs for database matching

**Key scripts:**
- `scripts/download_pdfs_from_database.py` - Main download orchestrator
- `scripts/download_via_scihub_tor.py` - Tor-based Sci-Hub downloads
- `scripts/retry_failed_downloads.py` - Retry failed acquisitions
- `scripts/organize_unmatched_pdfs.py` - Match PDFs to database entries
- `scripts/monitor_firefox_pdfs.py` - Track manual downloads

**Default actions:**
```bash
# Check download progress
if [ -f logs/oa_download_log.csv ]; then
  tail -20 logs/oa_download_log.csv
fi

# Count PDFs by source
find "Papers/" -type f -name "*.pdf" | wc -l
```

### 2. Database Queries & Analysis
**Context:** Querying the wide sparse schema for trends, gaps, and summaries.

**Common queries:**
- Count papers by discipline/technique/year
- Identify gaps in coverage (species, regions, methods)
- Generate temporal trends (technique adoption over time)
- Cross-tabulate disciplines vs techniques
- Extract papers for specific panelist review

**Always use:** DuckDB with columnar queries (don't SELECT *)

**Example pattern:**
```r
library(duckdb)
con <- dbConnect(duckdb::duckdb(), "outputs/literature_review.duckdb")

# Count papers by discipline
dbGetQuery(con, "
  SELECT
    SUM(d_genetics_genomics) as genetics,
    SUM(d_movement_spatial) as movement,
    SUM(d_fisheries) as fisheries
  FROM papers
")
```

### 3. Technique Database Updates
**Context:** The master techniques database requires regular updates from panelist reviews.

**Database location:** `database/technique_taxonomy.db`
**CSV version:** `data/master_techniques.csv` (208 techniques)
**Excel for review:** `data/Techniques DB for Panel Review.xlsx`

**Common updates:**
- Add new techniques from literature review
- Update search queries for Shark-References automation
- Reclassify techniques across disciplines
- Add subtechniques to parent methods
- Validate EEA presentation counts

**Fields to maintain:**
- `technique_id`, `technique_name`, `discipline`, `parent_technique`
- `search_query`, `eea_2025_count`, `priority`, `notes`

### 4. Species Database Operations
**Context:** ~1,200 chondrichthyan species require standardization and lookup.

**Key files:**
- `data/species_common_lookup_cleaned.csv` - Common name to scientific name
- Reference: Weigmann (2016) Annotated Checklist (178 species pending)
- Integration with Shark-References species database

**Common tasks:**
- Update species list from Shark-References
- Standardize scientific names (genus_species format)
- Map common names to scientific names
- Generate `sp_*` columns for database schema
- Extract species distributions for `sb_*` columns

**Script:** `scripts/update_shark_references_species.py`

### 5. Shark-References Search Automation
**Context:** Batch searching Shark-References for systematic literature review.

**Scripts:**
- `scripts/shark_references_search.py` (Python version)
- `scripts/shark_references_bulk_download.py` (CSV downloads)
- `scripts/shark_references_to_sql.py` (Database import)

**Process:**
1. Generate search queries from technique database
2. Execute searches with rate limiting (10-sec delays)
3. Download CSV results
4. Parse and import to database
5. Deduplicate and QC

### 6. Literature Review Data Entry Support
**Context:** Collaborative data entry requires validation and helper tools.

**Common needs:**
- Generate CSV templates with all 1,652 columns
- Create data validation rules (species lists, discipline options)
- Build lookup helpers (basin → sub-basin auto-population)
- Implement duplicate detection
- Extract metadata from DOIs/titles

**Validation priorities:**
- `study_type` auto-classification (keywords: "meta-analysis", "systematic review")
- Species name standardization
- Geographic region hierarchies (basin → sub-basin)
- Superorder auto-population from species

### 7. Candidate/Panelist Database
**Context:** 243 expert candidates across 8 disciplines with recruitment tiers.

**Database:** `outputs/candidate_database_phase1.csv`
**Documentation:** `docs/candidates/`

**Common queries:**
- Filter by discipline and tier (Tier 1 = high priority)
- Add conference attendance history (EEA, AES, SI)
- Update contact information and status
- Generate discipline-specific candidate lists
- Track recruitment status (invited, confirmed, declined)

**Tier definitions:**
- **Tier 1:** Must recruit (established, accessible)
- **Tier 2:** Strong candidates (active research)
- **Tier 3:** Senior/busy (may decline)
- **Tier 4:** Early career (fallback)

### 8. Visualization Requests
**Context:** Conference presentation graphics and temporal trend visualization.

**Common visualizations:**
- Branching timeline with technique adoption (thickness = paper count)
- Discipline distribution heatmaps
- Geographic distribution maps
- Temporal trends by discipline
- Network diagrams (technique relationships)

**Preferred tools:**
- R: `{ggplot2}`, `{plotly}`, `{visNetwork}`, `{ggraph}`
- Output: SVG/PNG for presentations, HTML for interactive

**Deployment:** GitHub Pages (github.io) for interactive visualizations

### 9. Git Operations & Documentation
**Context:** Collaborative project with extensive documentation structure.

**Documentation structure:**
- `docs/core/` - Project overview and planning
- `docs/database/` - Schema and acquisition
- `docs/techniques/` - Technique classification
- `docs/species/` - Species database
- `docs/candidates/` - Expert recruitment
- `docs/technical/` - Scripts and workflows

**When creating documentation:**
- Use `.md` files in appropriate `docs/` subfolders
- Use `snake_case` for filenames
- **Don't over-create:** Avoid huge files for simple queries/summaries
- Keep documentation focused and concise
- Include cross-references to related docs
- Add to `docs/readme.md` index only if substantial
- Update `README.md` only for major milestones
- Use YAML frontmatter for R Markdown compatibility

**Git commit style:** Descriptive, focused on "why" not "what"
- ✅ "Expand technique database to cover data-poor stock assessment methods"
- ❌ "Update master_techniques.csv"

### 10. Environment & Dependencies
**Context:** Python virtual environment with specific package versions.

**Virtual environment:** `venv/` (Python 3.13)
**Key packages:** duckdb, pandas, requests, beautifulsoup4, sqlite3

**R packages:** duckdb, duckplyr, tidyverse, data.table, httr

**When updating dependencies:**
- Always use the virtual environment: `./venv/bin/pip install`
- Document new requirements
- Test compatibility with existing scripts

## Project Status Quick Reference

**Completed:**
- ✅ 8-discipline framework defined
- ✅ Database schema designed (1,652 columns)
- ✅ 208 techniques compiled and documented
- ✅ 243 expert candidates identified
- ✅ Shark-References integration scripts created
- ✅ PDF acquisition infrastructure built

**In Progress:**
- 🔄 Panelist technique database review
- 🔄 Large-scale PDF acquisition (monitoring needed)
- 🔄 Species list completion (178 pending from Weigmann)

**Upcoming:**
- ⏳ Shark-References bulk automation (awaiting permission)
- ⏳ Systematic literature review execution
- ⏳ EEA 2025 conference (30 October 2025)

## Key External Resources

- **Shark-References:** https://shark-references.com (30,000+ papers)
- **Sharkipedia:** https://www.sharkipedia.org/ (species data)
- **DuckDB docs:** https://duckdb.org/docs/ (for query optimization)
- **Weigmann 2016:** Annotated Checklist of Chondrichthyes (species authority)
- **Carrier et al. 2019:** Shark Research: Emerging Technologies (technique reference)

## File Path Conventions

**Always use absolute paths starting with:**
- `/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel/`
- OR `/home/simon/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel/`

**Additional working directory:** `/home/simon/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel`

## Frequent Gotchas & Reminders

1. **Wide schema queries:** Always specify columns in SELECT, never use `SELECT *`
2. **DuckDB columnar storage:** Optimized for sparse boolean data, storage is not an issue
3. **Multi-label classification:** Papers can have multiple disciplines/techniques/species
4. **Search operator limitation:** Shark-References only indexes 3+ letter terms
5. **Rate limiting:** Always use conservative delays (10+ seconds) for web scraping
6. **R for analysis, Python for automation:** Use R for statistical work, Python for web scraping/processing
7. **Documentation style:** Use snake_case .md files in docs/ subfolders; avoid over-creating huge files
8. **Virtual environment:** Always use `./venv/bin/pip` not global pip
9. **Species format:** Use lowercase `genus_species` format for `sp_*` columns
10. **Geographic hierarchy:** Sub-basins auto-populate parent basin columns

## Quick Commands for Common Tasks

```bash
# Check PDF download progress
tail -20 logs/oa_download_log.csv

# Count PDFs acquired
find "Papers/" -type f -name "*.pdf" | wc -l

# Query technique database
sqlite3 database/technique_taxonomy.db "SELECT COUNT(*) FROM techniques"

# Activate Python environment
source venv/bin/activate

# Check DuckDB database size
ls -lh outputs/literature_review.duckdb
```

## Documentation Style Guide

When creating new documentation:

1. **Use clear hierarchical structure:**
   - Overview section at top
   - Table of contents for long docs
   - Section numbering where appropriate

2. **Include practical examples:**
   - Complete, runnable code snippets
   - Both Python AND R versions
   - Expected inputs and outputs

3. **Cross-reference related docs:**
   - Link to related documentation
   - Reference script locations
   - Point to data files

4. **Troubleshooting sections:**
   - Common errors and solutions
   - Rate limiting workarounds
   - Fallback strategies

5. **Maintain YAML frontmatter** (for R Markdown compatibility):
   ```yaml
   ---
   editor_options:
     markdown:
       wrap: 72
   ---
   ```

---

*Last updated: 2025-10-24*
*This file helps Claude Code provide faster, more accurate assistance by front-loading common context.*
