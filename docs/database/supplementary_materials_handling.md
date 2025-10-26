# Supplementary Materials Handling Guide

**Purpose:** How to handle supplementary materials (SM) files in PDF collection
**Date:** 2025-10-25

---

## Overview

Some publications have separate supplementary materials files that contain additional methods, data, or results not in the main paper. These SM files should be:

1. **Retained** in the collection (not deleted as duplicates)
2. **Searched/queried** separately
3. **Merged** with main paper results for complete technique coverage

---

## Identifying Supplementary Materials

### Filename Patterns

SM files typically have these indicators in filenames:

- ` SM.pdf` or `_SM.pdf`
- ` SM ` or `_SM_`
- `supplementary` or `supplement`

**Examples:**
```
Author.etal.YYYY.Paper title SM.pdf
Author.etal.YYYY.Paper title supplementary.pdf
Author.etal.YYYY.Paper title_SM_methods.pdf
```

### How They're Created

SM files are mapped to their main papers using:

**Script:** `scripts/find_duplicate_pdfs_improved.py`

**Output:** `outputs/supplementary_materials_mapping.csv`

**Mapping logic:**
- Same author + year
- Similar title (after removing SM indicators)
- Similarity threshold > 0.5

---

## Current Status

Based on improved duplicate detection:

```
Total PDFs: 13,357
Main papers: ~13,300
Supplementary materials: 0 (currently)
Reply papers: 26
Corrections: 36
Commentaries: 7
```

**Note:** Current collection has 0 SM files identified. This may increase as more papers are added.

---

## Workflow for Handling SM Files

### Step 1: Detection

When new PDFs are added, run duplicate finder:

```bash
cd "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"

./venv/bin/python scripts/find_duplicate_pdfs_improved.py
```

**Outputs:**
- `outputs/duplicate_pdfs_to_remove.csv` - True duplicates to remove
- `outputs/supplementary_materials_mapping.csv` - SM-to-main mappings

### Step 2: Verification

Review SM mappings:

```bash
cat outputs/supplementary_materials_mapping.csv
```

**Check:**
- SM file correctly matched to main paper?
- Same author + year?
- Titles make sense?

### Step 3: Technique Querying

When searching PDFs for techniques, include SM files:

```python
# Example search code
all_pdfs = list(pdf_base.glob("*/*.pdf"))

# Search ALL PDFs (including SM)
for pdf_path in all_pdfs:
    techniques_found = search_pdf_for_techniques(pdf_path)
    # ... store results
```

**Important:** Don't filter out SM files during search!

### Step 4: Result Merging

After searching, merge SM results with main papers:

```bash
python scripts/merge_sm_results_with_main.py \
    --results outputs/technique_search_results.csv \
    --sm-mapping outputs/supplementary_materials_mapping.csv \
    --output outputs/technique_search_results_merged.csv
```

**What this does:**
1. For each technique found in SM but not main paper → Add to main paper
2. For techniques found in both → Keep main paper entry only
3. Remove all SM entries (consolidate to main papers)

---

## Example Scenario

### Before Merge

**Search results:**

| paper_path | technique | found |
|------------|-----------|-------|
| Author.2020.Paper.pdf | GLM | TRUE |
| Author.2020.Paper SM.pdf | GLM | TRUE |
| Author.2020.Paper SM.pdf | PERMANOVA | TRUE |

### After Merge

**Merged results:**

| paper_path | technique | found | source |
|------------|-----------|-------|--------|
| Author.2020.Paper.pdf | GLM | TRUE | main |
| Author.2020.Paper.pdf | PERMANOVA | TRUE | SM |

**Changes:**
- GLM: Found in both → Keep main entry only
- PERMANOVA: Found only in SM → Added to main paper with source='SM'
- SM file removed from results

---

## Why This Matters

### Scenario: Technique Coverage

**Problem without SM handling:**
```
Main paper mentions: "GAM was used for analysis"
SM paper details: "GAM, GLM, and PERMANOVA were all tested"

Without SM: Only GAM recorded for this paper ❌
With SM: GAM, GLM, PERMANOVA all recorded ✓
```

### Scenario: Panel Analysis

When analyzing technique trends over time:

**Without SM:**
```
2020 papers with PERMANOVA: 50
(Missing techniques that were only in SM files)
```

**With SM:**
```
2020 papers with PERMANOVA: 65
(Complete coverage including SM-only mentions)
```

---

## Integration with Duplicate Removal

### Important Distinction

**DO NOT remove:**
- Supplementary materials (separate content)
- Reply papers (separate publications)
- Corrections/Errata (separate publications)
- Commentaries (separate publications)

**DO remove:**
- Same paper with different filename
- Versioned files (_v1, _v2)
- Different naming conventions (Dropbox vs Sci-Hub)

### Safe Removal Process

```bash
# 1. Run improved duplicate finder
./venv/bin/python scripts/find_duplicate_pdfs_improved.py

# 2. Review recommendations
cat outputs/duplicate_pdfs_to_remove.csv

# 3. Verify no SM/reply/correction papers in removal list
grep -i "reply\|sm\|correction\|erratum" outputs/duplicate_pdfs_to_remove.csv

# 4. If clear, remove duplicates
./venv/bin/python scripts/remove_duplicate_pdfs.py --live
```

---

## Special Cases

### Case 1: Multiple SM Files

Some papers have multiple SM files:

```
Author.2020.Paper.pdf
Author.2020.Paper SM1.pdf
Author.2020.Paper SM2.pdf
```

**Handling:**
- Map SM1 → Main
- Map SM2 → Main
- Merge results from both SM files with main

### Case 2: SM Without Main Paper

Sometimes SM file exists but main paper is missing:

```
Author.2020.Paper SM.pdf  (exists)
Author.2020.Paper.pdf     (missing - failed download)
```

**Handling:**
- Flag for review
- Attempt to re-download main paper
- If main paper cannot be obtained, keep SM and treat as standalone

### Case 3: Reply Papers with SM

Reply papers can also have SM:

```
Author.2020.Paper reply.pdf
Author.2020.Paper reply SM.pdf
```

**Handling:**
- Classify as reply (not duplicate with original paper)
- Map SM to reply paper (not original)
- Merge SM results with reply paper

---

## Future Enhancements

### Automatic Detection in Search

Modify search scripts to automatically handle SM:

```python
def search_papers_with_sm(pdf_list, sm_mapping, techniques):
    """
    Search papers and automatically merge SM results.
    """
    results = []

    # Search all PDFs
    for pdf in pdf_list:
        found_techniques = search_pdf(pdf, techniques)
        results.append({
            'paper': pdf,
            'techniques': found_techniques
        })

    # Auto-merge SM results
    return merge_sm_results(results, sm_mapping)
```

### SM Content Flagging

Track which techniques came from SM vs main:

```csv
paper,technique,in_main,in_sm,source
Author.2020.Paper.pdf,GLM,TRUE,TRUE,both
Author.2020.Paper.pdf,PERMANOVA,FALSE,TRUE,sm_only
```

**Benefits:**
- Transparency about technique sources
- Can filter to "main paper only" if needed
- Track completeness of methods reporting

---

## Monitoring SM Files

### After Each Download Batch

```bash
# Check for new SM files
find "/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers" \
    -name "*SM.pdf" -o -name "*supplementary*"

# Run duplicate finder to update mappings
./venv/bin/python scripts/find_duplicate_pdfs_improved.py

# Review new mappings
cat outputs/supplementary_materials_mapping.csv
```

### Periodic Audit

```bash
# Count SM files
find "/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers" \
    -name "*SM.pdf" | wc -l

# Check unmapped SM files
# (SM files without matching main paper)
```

---

## Summary

### Key Points

1. **SM files are NOT duplicates** - They contain additional content
2. **Search SM files separately** - Don't skip them in technique queries
3. **Merge results automatically** - Use merge script to consolidate
4. **Track source** - Record whether technique came from main or SM
5. **Review regularly** - Check SM mappings after downloads

### Quick Commands

```bash
# Find SM files
find . -name "*SM.pdf"

# Run duplicate finder (creates SM mappings)
./venv/bin/python scripts/find_duplicate_pdfs_improved.py

# Merge search results
python scripts/merge_sm_results_with_main.py \
    --results search_results.csv \
    --sm-mapping outputs/supplementary_materials_mapping.csv \
    --output search_results_merged.csv
```

---

**Last Updated:** 2025-10-25
