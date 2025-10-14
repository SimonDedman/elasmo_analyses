# Panelist Distribution Checklist

**Date:** 2025-10-13
**Ready to distribute:** ✅ Yes
**Total techniques for review:** 208

---

## Files to Send to Panelists

### 1. Primary Review File ⭐
**File:** `data/Techniques DB for Panel Review.xlsx`
- **Sheet 1 (README):** Quick instructions
- **Sheet 2 (Example_Sample):** 16 examples showing what to review
- **Sheet 3 (Full_List):** All 208 techniques - **THIS IS WHAT THEY EDIT**

### 2. Instructions (Required Reading)
**File:** `docs/README_FOR_PANELISTS.md`
- Quick start guide (3 options: Excel, CSV, or R)
- Discipline assignments
- What to review (6 key areas)
- Column reference guide
- Example edits
- Notes column flags (REVIEW:, REMOVE:, SPLIT:, etc.)

### 3. Background Documentation (Optional)
**File:** `docs/MASTER_TECHNIQUES_CSV_README.md`
- Complete CSV usage guide
- Summary statistics
- File structure details
- Integration workflow

---

## Recommended Distribution Email Template

```
Subject: EEA Panel Review - Elasmobranch Research Techniques Database (208 techniques)

Dear [Discipline Lead],

We're finalizing a comprehensive database of analytical techniques for automated
literature review on Shark-References. We've compiled 208 techniques across 8
disciplines and need your expert validation before proceeding.

YOUR DISCIPLINE: [BIO/BEH/TRO/GEN/MOV/FISH/CON/DATA]
YOUR TECHNIQUES TO REVIEW: [23/20/20/24/31/34/19/32]

ATTACHED FILES:
1. data/Techniques DB for Panel Review.xlsx - EDIT THIS FILE
2. docs/README_FOR_PANELISTS.md - START HERE (5 min read)
3. docs/MASTER_TECHNIQUES_CSV_README.md - Optional background

WHAT WE NEED:
✓ Verify technique names are standard in your field
✓ Add/edit synonyms (abbreviations, alternative names)
✓ Validate search queries will find relevant papers
✓ Flag any issues using notes column (REVIEW:, REMOVE:, SPLIT:, etc.)
✓ Add any missing techniques

HOW TO EDIT:
Option 1 (Easiest): Open Excel file → Filter to your discipline → Make edits
Option 2: Export to CSV → Edit in R/Python → Save as CSV
Option 3: Use Google Sheets (if needed)

TIMELINE:
Week 1-2: Your review and edits
Week 3: Team discussion of flagged issues
Week 4: Finalize approved version

SAVE YOUR EDITS AS:
Techniques_DB_REVIEWED_[YourName].xlsx (or .csv)

WHAT'S NEW:
• 208 total techniques (was 129)
• 84 new techniques added via literature review (marked "method_expansion")
• Focus on validating these new additions

Please see README_FOR_PANELISTS.md for complete instructions.

Questions? Contact [coordinator]

Thank you for your expertise!

Best regards,
[Your name]
```

---

## Pre-Distribution Checklist

Before sending to panelists, verify:

- [x] **Main file renamed:** ~~Example of Spreadsheet for Review.xlsx~~ → `Techniques DB for Panel Review.xlsx` ✅
- [x] **File location correct:** `data/Techniques DB for Panel Review.xlsx`
- [x] **README exists:** `docs/README_FOR_PANELISTS.md` ✅
- [x] **Optional doc exists:** `docs/MASTER_TECHNIQUES_CSV_README.md`
- [x] **CSV backup exists:** `data/master_techniques.csv` (unchanged)
- [x] **All 208 techniques present** in Excel file
- [x] **Three sheets in Excel:** README, Example_Sample, Full_List
- [ ] **Discipline leads identified:** Need names/emails for 8 leads
- [ ] **Coordinator contact:** Update in email template

---

## Discipline Assignment Reference

| Code | Discipline | Techniques | Lead Name | Email |
|------|-----------|-----------|-----------|-------|
| **BIO** | Biology, Life History, & Health | 28 | TBD | |
| **BEH** | Behaviour & Sensory Ecology | 20 | TBD | |
| **TRO** | Trophic & Community Ecology | 20 | TBD | |
| **GEN** | Genetics, Genomics, & eDNA | 24 | TBD | |
| **MOV** | Movement, Space Use, & Habitat | 31 | TBD | |
| **FISH** | Fisheries, Stock Assessment, & Mgmt | 34 | TBD | |
| **CON** | Conservation Policy & Human Dim. | 19 | TBD | |
| **DATA** | Data Science & Integrative | 32 | TBD | |

**Total: 208 techniques**

---

## Expected Panelist Workflow

### Step 1: Read Instructions (10 min)
- Open `README_FOR_PANELISTS.md`
- Skim sections: Quick Start, What to Review, Column Reference

### Step 2: Open Excel File (2 min)
- Open `Techniques DB for Panel Review.xlsx`
- Read "README" sheet
- Look at "Example_Sample" sheet to see format

### Step 3: Filter to Your Discipline (1 min)
- Go to "Full_List" sheet
- Apply filter to Column A (discipline_code)
- Select your code (e.g., "MOV" for Movement)

### Step 4: Review and Edit (1-3 hours)
For each technique in your discipline:
- ✓ Check if name is standard
- ✓ Add synonyms in Column G
- ✓ Verify search queries (Columns I-J)
- ✓ Add notes in Column L if issues
- ✓ Add missing techniques (copy row, modify)

### Step 5: Save Edits (1 min)
- Save As: `Techniques_DB_REVIEWED_[YourName].xlsx`
- Send back to coordinator

### Step 6: Optional - Test Queries (30 min - 2 hours)
- Pick 5-10 techniques
- Test search queries on https://shark-references.com/search
- Record result counts in notes

**Total time estimate:** 2-5 hours per discipline lead

---

## What Panelists Should Focus On

### High Priority ⭐
1. **Verify technique names** - Are they standard terminology?
2. **Add synonyms** - What alternative names do researchers use?
3. **Flag problems** - Use REVIEW:, REMOVE:, SPLIT: in notes

### Medium Priority
4. **Check search queries** - Will they find relevant papers?
5. **Add missing techniques** - Any major methods we missed?

### Low Priority (Optional)
6. **Test queries on Shark-References** - Record result counts
7. **Improve descriptions** - Make them clearer

---

## Common Questions & Answers

**Q: Can I edit in Google Sheets instead of Excel?**
A: Yes! Upload to Google Sheets, make edits, download as .xlsx or .csv

**Q: What if I don't know all the techniques in my discipline?**
A: That's fine! Just review what you know. Flag uncertainties with "REVIEW: Not familiar with this method"

**Q: Should I test every search query on Shark-References?**
A: Optional. If you have time, test 5-10 of the most important ones.

**Q: What if a technique overlaps with another discipline?**
A: Note it! Add "OVERLAP: Also used in [DISCIPLINE]" in notes column.

**Q: Can I suggest moving a technique to a different category?**
A: Yes! Add "MOVE: Should be in [CATEGORY]" in notes column.

**Q: What about very new methods (last 1-2 years)?**
A: Add them! Mark as "NEW: Emerging method, verify importance"

**Q: How specific should sub-techniques be?**
A: Balance specificity with searchability. If it's commonly used and searchable, include it.

**Q: What about commercial software vs. open methods?**
A: Include both if widely used (e.g., MaxEnt, Marxan are commercial but standard)

---

## After Panelist Review

### Week 3: Consolidation
- Collect all reviewed files
- Merge edits from 8 discipline leads
- Discuss flagged issues (REVIEW:, REMOVE:, SPLIT:)
- Resolve conflicts

### Week 3-4: Validation
- Test controversial search queries
- Verify added techniques are searchable
- Finalize technique list

### Week 4: Finalization
- Create `master_techniques_APPROVED.csv`
- Import to database: `database/technique_taxonomy.db`
- Begin automated Shark-References searches

---

## File Versions Tracking

| Version | Date | Techniques | Status | Notes |
|---------|------|-----------|--------|-------|
| v1.0 | 2025-10-13 | 129 | ✅ Complete | Initial compilation |
| v1.5 | 2025-10-13 | 208 | ✅ Expanded | +79 via literature review |
| v2.0 | TBD | ~210-230? | 📋 In Review | After panelist edits |
| v3.0 | TBD | TBD | 🎯 Final | Approved for automation |

---

## Success Metrics

**Distribution success if:**
- ✅ All 8 discipline leads receive files
- ✅ All leads acknowledge receipt
- ✅ Instructions are clear (no major confusion)

**Review success if:**
- ✅ >75% techniques reviewed by discipline leads
- ✅ Synonyms added to >80% of techniques
- ✅ <10% techniques flagged for removal
- ✅ <20 major missing techniques identified

**Timeline success if:**
- ✅ Week 1-2: Edits received from all leads
- ✅ Week 3: Issues resolved
- ✅ Week 4: Final approved version ready

---

## Quick Reference: Key Files

```
Project Root/
├── data/
│   ├── Techniques DB for Panel Review.xlsx  ⭐ EDIT THIS
│   ├── master_techniques.csv                (backup/alternative)
│   └── master_techniques_BEFORE_EXPANSION.csv  (original 129)
├── docs/
│   ├── README_FOR_PANELISTS.md              ⭐ START HERE
│   ├── MASTER_TECHNIQUES_CSV_README.md      (optional background)
│   ├── Panelist_Distribution_Checklist.md   (for coordinator)
│   ├── Expansion_Summary_Report.md          (what was added)
│   └── Technique_Expansion_List.md          (detailed additions)
└── scripts/
    └── add_all_expanded_techniques.R        (how expansion was done)
```

---

## Contact Information

**Project Coordinator:** [Name]
**Email:** [Email]
**Timeline Questions:** [Contact]
**Technical Issues:** [Contact]

---

## Final Checklist Before Send

- [ ] All 3 files attached (Excel, README, optional CSV README)
- [ ] Discipline leads identified and assigned
- [ ] Email customized with lead names and technique counts
- [ ] Timeline confirmed (2 weeks for review)
- [ ] Coordinator contact info updated
- [ ] Response mechanism established (email? shared folder?)
- [ ] Backup plan if lead unavailable (alternate reviewer?)

---

**Status:** ✅ Ready to distribute
**Next Action:** Send to discipline leads
**Expected Return:** Week 1-2 (by [DATE])

---

*Checklist created: 2025-10-13*
*Files ready: 208 techniques across 8 disciplines*
*Expansion complete: +79 techniques via literature review*
