# Claude.md Configuration Summary

## Overview

I've created a comprehensive `.claude/claude.md` configuration file to significantly reduce context window usage and avoid repetitive questions in future Claude Code sessions. This file front-loads common project context, conventions, and frequently requested operations.

**Location:** `/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel/.claude/claude.md`

## What's Included

### 1. Project Overview & Quick Facts
- Database locations and formats (DuckDB, SQLite, Parquet)
- Key metrics (1,200 species, 1,652 columns, 208 techniques)
- The 8 discipline framework with technique counts
- Primary data source (Shark-References database)

### 2. Important Project Constraints
- **R preference reminder:** Always provide R alternatives to Python code
- **Database schema conventions:** All column prefixes (`d_`, `sp_`, `auth_`, `b_`, etc.)
- **Shark-References automation rules:** Rate limiting, search operators, permission requirements

### 3. 10 Common High-Priority Request Categories

Each includes:
- **Context** explaining why this request is common
- **Common tasks** that you typically ask for
- **Key scripts** and file locations
- **Example patterns** or code snippets
- **Default actions** to take proactively

#### The 10 Categories:
1. **PDF Acquisition & Organization** - Monitoring downloads, tracking failures, organizing files
2. **Database Queries & Analysis** - Querying wide sparse schema, temporal trends, gap analysis
3. **Technique Database Updates** - Adding techniques, updating search queries, validation
4. **Species Database Operations** - Species list updates, name standardization, distribution mapping
5. **Shark-References Search Automation** - Batch searching, rate limiting, CSV import
6. **Literature Review Data Entry Support** - Templates, validation rules, lookup helpers
7. **Candidate/Panelist Database** - Expert recruitment, tier filtering, status tracking
8. **Visualization Requests** - Temporal trends, branching timelines, network diagrams
9. **Git Operations & Documentation** - Doc structure, commit style, markdown conventions
10. **Environment & Dependencies** - Virtual environment usage, package management

### 4. Project Status Quick Reference
- Checkboxes for completed, in-progress, and upcoming work
- Allows Claude to understand project phase without asking

### 5. Key External Resources
- Shark-References, Sharkipedia, DuckDB docs
- Important papers (Weigmann 2016, Carrier et al. 2019)

### 6. File Path Conventions
- Both working directory paths documented
- Absolute path requirements specified

### 7. Frequent Gotchas & Reminders
- 10 common pitfalls to avoid
- Specific technical limitations (3-letter indexing, rate limits)
- Workflow conventions (R preference, documentation updates)

### 8. Quick Commands Reference
- Bash one-liners for common checks
- Ready-to-use commands for monitoring progress

### 9. Documentation Style Guide
- Structure requirements for new docs
- Cross-referencing conventions
- YAML frontmatter template

## Benefits You'll Experience

### 1. Reduced Context Window Usage
**Before:** Each session required reading multiple docs to understand project structure
**After:** Claude has immediate access to all conventions and common patterns

**Estimated savings:** 10,000-20,000 tokens per session

### 2. Fewer Clarifying Questions
**Before:**
- "Do you want Python or R?"
- "What's the rate limiting policy for Shark-References?"
- "What prefix should I use for species columns?"

**After:** Claude knows these conventions automatically

### 3. Proactive Default Actions
**Before:** You'd ask "check the download progress"
**After:** Claude can proactively run the monitoring commands when relevant

### 4. Consistent Documentation
Claude will now automatically follow your project's documentation conventions without needing to be told each time.

### 5. Faster Onboarding in New Sessions
New chat sessions will have the critical context immediately, reducing back-and-forth.

## How Claude Will Use This File

When you start a new session, Claude Code automatically loads `.claude/claude.md` as context. This means:

1. **First message advantage:** Claude already knows your project structure
2. **Smart defaults:** Claude can make informed decisions about R vs Python, column naming, etc.
3. **Proactive assistance:** Claude can suggest next steps based on project status
4. **Context-aware responses:** Answers are tailored to your specific workflow

## Recommended Additional Enhancements

### 1. Create Slash Commands for Common Workflows

Create `.claude/commands/` directory with these suggested commands:

#### `.claude/commands/check-downloads.md`
```markdown
Check the status of PDF downloads:
1. Show last 20 lines of logs/oa_download_log.csv if it exists
2. Count total PDFs in Papers/ directory
3. Show breakdown by source (Open Access, Sci-Hub, institutional)
4. Identify any errors in recent downloads
5. Summarize success rate
```

#### `.claude/commands/query-techniques.md`
```markdown
Query the technique taxonomy database:
1. Connect to database/technique_taxonomy.db
2. Show total techniques by discipline
3. List techniques with search queries still pending
4. Show techniques validated by EEA 2025 presentations
5. Provide both SQL and duckdb/R versions of queries
```

#### `.claude/commands/update-species.md`
```markdown
Update the species database:
1. Run scripts/update_shark_references_species.py
2. Compare old vs new species counts
3. Identify newly added species
4. Update data/species_common_lookup_cleaned.csv
5. Regenerate sp_* column list for database schema
```

#### `.claude/commands/doc-index.md`
```markdown
Update the documentation index:
1. Scan docs/ directory for new markdown files
2. Update docs/readme.md with new entries
3. Check for broken internal links
4. Suggest updates to main README.md if needed
5. Verify all docs have proper YAML frontmatter
```

### 2. Create MCP Server for Shark-References

If you frequently interact with Shark-References, consider creating a Model Context Protocol (MCP) server for it. This would provide:

- Structured search function with automatic rate limiting
- CSV parsing and database import
- Search query validation
- Automatic retry logic

Benefits:
- Safer than ad-hoc web scraping
- Built-in rate limiting
- Reusable across projects
- Better error handling

### 3. Add Project-Specific Templates

Create `.claude/templates/` with:

#### `new-technique.md` - Template for adding techniques
```markdown
## New Technique Checklist
- [ ] Technique name (clear, concise)
- [ ] Discipline classification (BIO/BEH/TRO/GEN/MOV/FISH/CON/DATA)
- [ ] Parent technique (if subtechnique)
- [ ] Search query for Shark-References
- [ ] Priority (1-4)
- [ ] Notes (references, common uses)
- [ ] Add to database/technique_taxonomy.db
- [ ] Add to data/master_techniques.csv
- [ ] Update docs/techniques/ documentation
```

#### `new-documentation.md` - Template for documentation
```markdown
---
editor_options:
  markdown:
    wrap: 72
---

# [Document Title]

## Overview

[Brief description of purpose]

## Prerequisites

[Required knowledge, tools, or data]

## [Main Sections]

...

## Troubleshooting

[Common issues and solutions]

## Related Resources

[Cross-references to other docs]

---

*Last updated: YYYY-MM-DD*
*Status: [Draft/Complete/Archived]*
```

### 4. Add Database Query Cookbook

Create `docs/database/query_cookbook.md` with common query patterns:

```markdown
# Database Query Cookbook

## Common Queries for Literature Review Database

### Count papers by discipline
\`\`\`sql
SELECT
  SUM(d_biology_health) as biology,
  SUM(d_behaviour_sensory) as behaviour,
  SUM(d_trophic_ecology) as trophic,
  -- ... etc
FROM papers;
\`\`\`

### Temporal trends for specific technique
\`\`\`r
library(duckdb)
library(dplyr)

con <- dbConnect(duckdb::duckdb(), "outputs/literature_review.duckdb")

tbl(con, "papers") %>%
  filter(a_acoustic_telemetry == 1) %>%
  count(year) %>%
  arrange(year) %>%
  collect()
\`\`\`

[... more examples ...]
```

This could be referenced from claude.md and save even more explanation time.

### 5. Add Workflow Diagrams

Create ASCII or Mermaid diagrams for complex workflows:

**In claude.md, add section:**
```markdown
## Key Workflows

### PDF Acquisition Workflow
\`\`\`mermaid
graph TD
    A[Search Shark-References] --> B[Extract DOIs]
    B --> C{DOI exists?}
    C -->|Yes| D[Try Open Access]
    C -->|No| E[Manual download list]
    D --> F{Success?}
    F -->|No| G[Try Sci-Hub/Tor]
    F -->|Yes| H[Organize by source]
    G --> H
    H --> I[Match to database]
\`\`\`

[Include for other major workflows]
```

### 6. Create Progress Dashboard Command

Create `.claude/commands/project-status.md`:
```markdown
Generate a comprehensive project status dashboard:

1. **Database Status**
   - Count records in shark_references.db
   - Count techniques in technique_taxonomy.db
   - Size of literature_review.duckdb

2. **PDF Acquisition**
   - Total PDFs downloaded
   - Success/failure rates by source
   - Pending downloads count

3. **Technique Database**
   - Techniques by discipline
   - Techniques with/without search queries
   - EEA validation status

4. **Documentation**
   - Count files in docs/
   - Last updated dates
   - Missing documentation (check TODOs)

5. **Expert Candidates**
   - Total candidates by tier
   - Recruitment status counts
   - Discipline coverage gaps

Format as markdown table with status indicators (✅/🔄/❌/⏳)
```

### 7. Add Data Validation Rules Document

Create `docs/database/validation_rules.md`:
```markdown
# Data Validation Rules

## Automated Validations

### study_type
- **Valid values:** Primary, Review, Meta-analysis
- **Auto-classify:** Scan title/abstract for keywords
  - "systematic review" → Review
  - "meta-analysis" → Meta-analysis
  - Default → Primary

### Species columns (sp_*)
- **Format:** lowercase genus_species
- **Validation:** Check against species_common_lookup_cleaned.csv
- **Auto-complete:** Genus → populate all sp_* for that genus

[... etc for all major fields ...]
```

## Implementation Notes

### Current Configuration Location
```
/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel/.claude/
├── claude.md                      # Main configuration (created)
└── settings.local.json            # Settings (existing)
```

### Recommended Directory Structure
```
.claude/
├── claude.md                      # Main configuration ✅
├── settings.local.json            # Settings ✅
├── commands/                      # Slash commands (suggested)
│   ├── check-downloads.md
│   ├── query-techniques.md
│   ├── update-species.md
│   ├── doc-index.md
│   └── project-status.md
└── templates/                     # Document templates (suggested)
    ├── new-technique.md
    └── new-documentation.md
```

## Testing the Configuration

### Test in a New Session

1. **Start fresh Claude Code session**
2. **Ask a previously repetitive question:**
   - "What column prefix should I use for species?"
   - "Should I provide Python or R code?"
   - "What's the rate limiting policy?"

3. **Check if Claude:**
   - Answers without asking clarifications
   - Uses correct conventions automatically
   - References the claude.md content

### Test Proactive Behavior

1. **Ask about download progress**
   - Claude should automatically run: `tail -20 logs/oa_download_log.csv`
   - Claude should count PDFs without being asked

2. **Ask about technique database**
   - Claude should know the location and structure
   - Claude should offer both SQL and R query options

### Test Documentation Creation

1. **Ask Claude to create a new doc**
   - Should use YAML frontmatter
   - Should follow existing structure
   - Should offer to update docs/readme.md

## Maintenance Recommendations

### When to Update claude.md

1. **Major project milestones** - Update "Project Status Quick Reference"
2. **New common patterns** - Add to "Common High-Priority Requests"
3. **Changed conventions** - Update relevant sections
4. **New external resources** - Add to "Key External Resources"
5. **New gotchas discovered** - Add to "Frequent Gotchas & Reminders"

### Version Control

The `.claude/claude.md` file is tracked in git, so:
- Changes are versioned
- Collaborators get the same context
- You can revert if needed

Consider adding a version number and last-updated date at the bottom (already included).

## Estimated Impact

### Token Savings Per Session
- **Documentation reads:** ~10,000 tokens saved
- **Clarifying questions:** ~2,000 tokens saved
- **Convention explanations:** ~3,000 tokens saved
- **Status updates:** ~2,000 tokens saved

**Total estimated savings: 15,000-20,000 tokens per session**

### Time Savings Per Session
- **Fewer back-and-forth questions:** ~5-10 messages saved
- **Faster code generation:** Claude makes correct assumptions
- **Reduced manual correction:** Follows conventions first time

**Estimated time savings: 5-10 minutes per session**

### Consistency Improvements
- **Naming conventions:** Automatically consistent
- **Documentation structure:** Follows project style
- **Code patterns:** Uses established approaches
- **R/Python balance:** Always provides both when relevant

## Future Considerations

### If Project Grows Significantly

Consider splitting claude.md into multiple files:
```
.claude/
├── claude.md                      # Main config (overview + includes)
├── conventions.md                 # All naming/style conventions
├── workflows.md                   # Common request patterns
└── resources.md                   # External resources + gotchas
```

Then use includes/references in main claude.md.

### If Collaborators Join

Brief collaborators on:
1. The `.claude/` directory exists and its purpose
2. Update `claude.md` when they discover new patterns
3. Add their common questions to reduce friction

### Integration with Other Tools

The conventions in claude.md could also inform:
- **Pre-commit hooks** - Validate column naming
- **CI/CD checks** - Verify documentation updates
- **IDE snippets** - Code templates matching conventions
- **Shell aliases** - Quick commands from "Quick Commands" section

## Conclusion

The new `.claude/claude.md` configuration file provides:

✅ **Immediate context** for new sessions
✅ **Reduced token usage** through front-loaded information
✅ **Fewer repetitive questions** via established conventions
✅ **Proactive assistance** with default actions
✅ **Consistent outputs** following project patterns
✅ **Faster development** through smart defaults

This should significantly improve your Claude Code experience for this project!

---

*Created: 2025-10-24*
*Purpose: Document the claude.md configuration and suggest enhancements*
