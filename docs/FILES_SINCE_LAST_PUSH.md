# Files Created Since Last Git Push

**Date**: 2025-10-03
**Last Push Commit**: a8cfcce (Initial commit)

---

## Scripts (All Recommended for Push)

### Candidate Database Management
1. `scripts/create_candidate_database_phase1.R` - Initial database creation from speaker list
2. `scripts/integrate_all_candidates.R` - Merge expert recommendations + attendee list
3. `scripts/integrate_newly_identified_attendees.R` - Add Lorenzo Elias & Paul Cox
4. `scripts/classify_unclassified.R` - Classify candidates by discipline
5. `scripts/apply_all_highlighting.R` - Apply Excel highlighting to updated cells

### Attendee List Processing
6. `scripts/process_eea2025_attendee_list.R` - Process attendee list, web search for Annemiek
7. `scripts/update_attendee_list_missing_names.R` - Update with Lorenzo, Hettie, Paul
8. `scripts/find_missing_names_in_abstracts.R` - R-based abstract search (unused - officer pkg unavailable)
9. `scripts/search_abstracts_simple.sh` - **WORKING** bash script to search abstracts

### Conference Attendance Extraction
10. `scripts/extract_si2022_attendance.R` - Parse SI2022 video filenames (47 speakers)
11. `scripts/extract_conference_attendance.R` - Extract from PDFs using pdftools (abandoned - timeout)
12. `scripts/extract_conference_attendance_simple.sh` - **WORKING** pdftotext-based extraction
13. `scripts/integrate_conference_attendance.R` - Integrate all conference data into database

### Discipline Assignment
14. `scripts/convert_oral_ppt_disciplines.R` - Convert presentation disciplines to 8-category schema

---

## Documentation (Recommended for Review)

### Progress Reports
15. `docs/Candidate_Database_Phase1_Report.md` - Phase 1 database creation report
16. `docs/Candidate_Search_Protocol.md` - Web search protocol for candidate identification
17. `docs/Task_Progress_Report_2025-10-03.md` - Daily progress report
18. `outputs/missing_names_search_report.md` - Abstract search findings (Renzo, WOZEP, etc.)

### Data Files (Consider for .gitignore)
19. `data/cleaning_log.txt` - Species lookup cleaning log
20. `data/species_lookup_analysis_report.txt` - Species lookup analysis
21. `data/Weigmann_2016_Annotated_global_checklist_of_ChondrichthyesTable_II_rotated.pdf` - Reference PDF (6.4MB)

---

## Output Files (Should Stay .gitignored)

### Primary Outputs (outputs/)
22. `outputs/candidate_database_phase1.csv` - **MAIN DATABASE** (41KB, 243 candidates)
23. `outputs/conference_attendance_summary.csv` - Conference history (52KB, 2043 attendees)
24. `outputs/candidates_by_discipline_phase1.csv` - Discipline distribution summary
25. `outputs/candidate_search_log.csv` - Search attempt log
26. `outputs/discipline_summary.csv` - EEA 2025 presentation distribution
27. `outputs/conference_texts/` - Extracted text from conference PDFs (6 files)

---

## Large Data Directories (Should Stay .gitignored)

### Conference Materials
28. `EEA History/` - Historical conference programs (48 files, mixed PDF/DOC/ODT)
   - EEA 2013, 2015, 2017, 2021, 2023
   - AES 2015, 2016, 2017, 2019, 2021
   - **Size**: ~50MB total

### Abstracts
29. `abstracts/` - EEA 2025 submitted abstracts (112 files)
   - 89 DOCX files
   - 23 PDF files
   - **Size**: ~15MB total

---

## Temporary/Review Files (gitignore Candidates)

30. `PROJECT_STRUCTURE.txt` - Directory tree snapshot
31. `README_OLD.md` - Backup of previous README
32. `TODO.md` - Outdated TODO list (superseded by docs)
33. `Example of Spreadsheet for Review.xlsx` - Template example

---

## Recommendation Summary

### ✅ Push These (Scripts + Key Docs)
- All 14 scripts in `scripts/` (essential workflow)
- `docs/Candidate_Search_Protocol.md` (methodology)
- `docs/Candidate_Database_Phase1_Report.md` (phase 1 summary)
- `outputs/missing_names_search_report.md` (findings)

### 📋 Review Before Push (Docs)
- `docs/Task_Progress_Report_2025-10-03.md` (contains sensitive info?)

### 🚫 Keep .gitignored (Data/Outputs)
- All `outputs/*.csv` files (generated data)
- All `data/*.pdf` files (large references)
- `data/*_log.txt` and `data/*_report.txt` (ephemeral logs)
- `EEA History/` directory (48 large files, ~50MB)
- `abstracts/` directory (112 files, ~15MB, potentially sensitive)

### 🗑️ Delete or .gitignore (Temporary)
- `PROJECT_STRUCTURE.txt` (one-time snapshot)
- `README_OLD.md` (backup not needed)
- `TODO.md` (outdated)
- `Example of Spreadsheet for Review.xlsx` (reference only)

---

## Updated .gitignore Additions Needed

```gitignore
# Conference materials (large)
EEA History/

# Abstracts (potentially sensitive)
abstracts/

# Data logs and reports (ephemeral)
data/*_log.txt
data/*_report.txt

# Temporary files
PROJECT_STRUCTURE.txt
README_OLD.md
TODO.md
```

---

## Summary Statistics

**Scripts created**: 14
**Documentation created**: 4
**Output files generated**: 8 (+ 6 in subdirectory)
**Large data directories**: 2 (EEA History: ~50MB, abstracts: ~15MB)
**Temporary files**: 4

**Recommended for push**: 18 files (~200KB scripts + docs)
**Recommended to .gitignore**: 172+ files (~65MB data)

---

## Notes

1. **Scripts are clean**: All R and bash scripts contain no sensitive data and document the workflow
2. **Outputs are gitignored**: As per existing .gitignore (outputs/* except .gitkeep)
3. **Large data should stay local**: Conference PDFs and abstracts are too large and potentially sensitive
4. **Documentation is selective**: Only push methodology and findings, not daily progress with potential sensitive details

The main workflow is fully reproducible from the scripts once the user provides:
- `Final Speakers EEA 2025.xlsx`
- `EEA 2025 Attendee List.xlsx`
- `docs/Expert_Recommendations_Comprehensive.md`
