---
description: Generate comprehensive project status dashboard
---

Generate a comprehensive project status dashboard with the following sections:

## 1. Database Status
Check and report:
- Record count in `shark_references.db` (papers table)
- Technique count in `database/technique_taxonomy.db`
- Size and record count of `outputs/literature_review.duckdb`
- Status: Display as table with ✅ if operational, ❌ if missing/error

## 2. PDF Acquisition Progress
Check and report:
- Total PDFs in `Papers/` directory (recursive count)
- Last 5 entries from `logs/oa_download_log.csv` if exists
- Success/failure counts from log
- Breakdown by source if available (Open Access, Sci-Hub, Institutional)
- Status indicator: ✅ >1000 PDFs, 🔄 100-1000, ⏳ <100, ❌ none

## 3. Technique Database
Query `database/technique_taxonomy.db` and report:
- Total techniques (should be 208)
- Breakdown by discipline (BIO/BEH/TRO/GEN/MOV/FISH/CON/DATA)
- Count with search queries defined
- Count validated by EEA 2025 presentations
- Status: ✅ if 208 techniques, 🔄 if different

## 4. Documentation Status
Check `docs/` directory:
- Total markdown files (excluding README)
- Files by category (core/database/techniques/species/candidates/technical)
- Most recently modified files (top 3 with dates)
- Check if `docs/readme.md` is up to date
- Status: ✅ if >40 docs, 🔄 if 20-40, ⏳ if <20

## 5. Expert Candidates
Check `outputs/candidate_database_phase1.csv` if exists:
- Total candidates
- Breakdown by tier (Tier 1/2/3/4)
- Candidates with emails vs without
- Discipline coverage gaps (disciplines with <5 candidates)
- Status: ✅ if >200, 🔄 if 100-200, ⏳ if <100

## 6. Species Database
Check species-related files:
- Count in `data/species_common_lookup_cleaned.csv`
- Note: Weigmann complete list pending (178 species)
- Status: 🔄 awaiting Weigmann complete list

## 7. Recent Activity
- Last 3 git commits (date, message)
- Most recently modified scripts in `scripts/`
- Any running background processes (check for Python/R processes)

## Output Format
Present as a structured markdown report with:
- Section headers
- Tables where appropriate
- Status indicators (✅/🔄/⏳/❌)
- Summary at the top
- Recommendations at the bottom

## Recommendations Section
Based on status, suggest:
- Immediate actions needed (if any ❌ status)
- Next priority tasks (if any 🔄 status)
- Maintenance tasks (backups, updates)

---

This command provides a comprehensive overview perfect for starting a work session or checking progress.
