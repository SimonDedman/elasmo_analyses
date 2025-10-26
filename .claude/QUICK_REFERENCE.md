# Claude Code Quick Reference Card

## Project Quick Facts
- **Working Directory:** `/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel/`
- **Main Databases:**
  - `shark_references.db` - Bibliographic (SQLite)
  - `database/technique_taxonomy.db` - 208 techniques (SQLite)
  - `outputs/literature_review.duckdb` - Analytical (DuckDB)
- **Virtual Environment:** `./venv/bin/` (Python 3.13)

## Column Prefixes (Database Schema)
| Prefix | Purpose | Example | Count |
|--------|---------|---------|-------|
| `d_` | Disciplines | `d_genetics_genomics` | 8 |
| `sp_` | Species | `sp_carcharodon_carcharias` | ~1,200 |
| `auth_` | Author nations | `auth_us`, `auth_au` | 197 |
| `b_` | Ocean basins | `b_north_atlantic` | 9 |
| `sb_` | Sub-basins | `sb_california_current` | 66 |
| `so_` | Superorders | `so_selachimorpha` | 3 |
| `a_` | Analysis methods | `a_acoustic_telemetry` | ~150 |

## The 8 Disciplines (with shortcuts)
1. **BIO** - Biology, Life History, & Health (28 techniques)
2. **BEH** - Behaviour & Sensory Ecology (20 techniques)
3. **TRO** - Trophic & Community Ecology (20 techniques)
4. **GEN** - Genetics, Genomics, & eDNA (24 techniques)
5. **MOV** - Movement, Space Use, & Habitat Modeling (31 techniques)
6. **FISH** - Fisheries, Stock Assessment, & Management (34 techniques)
7. **CON** - Conservation Policy & Human Dimensions (19 techniques)
8. **DATA** - Data Science & Integrative Methods (32 techniques)

## Shark-References Search Operators
```
+word              Required keyword (AND)
-word              Exclude (NOT, requires + first)
word*              Wildcard prefix
"exact phrase"     Exact match
word1 @10 word2    Proximity (within 10 words)
```
⚠️ **Rate Limit:** 10-second delays between requests
⚠️ **Max Results:** 2,000 per search
⚠️ **Indexing:** 3+ letters only (`+tel` matches `telemetry`)
✅ **Note:** No permission needed for automated searches

## Quick Commands

### Check Download Progress
```bash
tail -20 logs/oa_download_log.csv
find "Papers/" -type f -name "*.pdf" | wc -l
```

### Query Databases
```bash
# Technique count
sqlite3 database/technique_taxonomy.db "SELECT COUNT(*) FROM techniques"

# Species count
sqlite3 shark_references.db "SELECT COUNT(DISTINCT species) FROM species"
```

### R Database Connection
```r
library(duckdb)
con <- dbConnect(duckdb::duckdb(), "outputs/literature_review.duckdb")
```

### Python Virtual Environment
```bash
source venv/bin/activate           # Activate
./venv/bin/pip install package     # Install
```

## Key Files & Locations

### Data Files
- `data/master_techniques.csv` - 208 techniques
- `data/species_common_lookup_cleaned.csv` - Species names
- `data/Techniques DB for Panel Review.xlsx` - For panelist edits

### Documentation
- `docs/readme.md` - Documentation index
- `docs/core/project_summary.md` - Project overview
- `docs/database/database_schema_design.md` - Schema details

### Scripts (Most Used)
- `scripts/download_pdfs_from_database.py` - Main downloader
- `scripts/shark_references_search.py` - Automated searches
- `scripts/update_shark_references_species.py` - Species updates
- `scripts/organize_unmatched_pdfs.py` - PDF organization

### Output Directories
- `outputs/` - Generated files (gitignored)
- `Papers/` - Downloaded PDFs (gitignored)
- `logs/` - Download logs

## Common Requests Shortcuts

Instead of asking: "Can you check the download progress and tell me how many papers we have?"
Just ask: "Download status?"
→ Claude knows to check logs and count PDFs

Instead of: "Please query the technique database and show me counts by discipline in both SQL and R"
Just ask: "Technique breakdown?"
→ Claude provides both query formats

Instead of: "What's the proper column name format for white sharks in the database?"
Just ask: "Species column for white shark?"
→ Claude knows: `sp_carcharodon_carcharias`

## Project Status (Current)
✅ **Completed:** Database schema, 208 techniques compiled, 243 candidates identified
🔄 **In Progress:** PDF acquisition, panelist reviews
⏳ **Upcoming:** Bulk Shark-References automation (awaiting permission), EEA conference (Oct 30)

## Remember
1. ✅ **R for analysis, Python for automation** - don't create both unless asked
2. ✅ Use **absolute paths** for file operations
3. ✅ Never `SELECT *` from wide sparse tables (specify columns)
4. ✅ **10-second delays** for web scraping
5. ✅ Use **snake_case** for new .md files in docs/
6. ✅ **Don't over-create** - keep docs focused and concise
7. ✅ YAML frontmatter for R Markdown compatibility

## External Resources
- **Shark-References:** https://shark-references.com (30,000+ papers)
- **Sharkipedia:** https://www.sharkipedia.org/
- **DuckDB:** https://duckdb.org/docs/

## Help
- Full configuration: `.claude/claude.md`
- Configuration guide: `docs/core/claude_md_configuration_summary.md`
- Project README: `README.md`

---
*Keep this handy for quick reference during Claude Code sessions*
