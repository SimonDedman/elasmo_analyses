# Institutional Access Setup - Quick Reference

**Date:** November 21, 2025
**Status:** ✅ Complete and ready to use

---

## What You Have

### 📊 Priority Lists (Ready to Use)
- **Priority 1:** 9,003 recent papers (2015+) with DOIs → `outputs/acquisition_priority_1_recent_with_doi.csv`
- **Priority 2:** 5,035 papers (2000-2014) with DOIs → `outputs/acquisition_priority_2_2000s_with_doi.csv`
- **Priority 3:** 3,038 papers from key journals → `outputs/acquisition_priority_3_key_journals.csv`
- **Priority 4:** 65 papers with complete metadata → `outputs/acquisition_priority_4_no_doi_complete_metadata.csv`

### 📚 Publisher Lists (By Publisher)
- 10 separate CSV files in `outputs/by_publisher/`
- Top publishers: Elsevier (1,604), Wiley (1,542), Springer Nature (1,248)
- Open access: Frontiers (343), PLOS (217), PeerJ (81)

### 📝 Templates (Ready to Use)
- ILL batch template → `templates/ILL_BATCH_REQUEST_TEMPLATE.csv`
- 3 pre-made ILL batches (50 papers each) → `templates/ILL_batch_*.csv`
- Tracking template → `templates/acquisition_tracking_template.xlsx`

### 📖 Documentation (Complete Guides)
- **Main workflow:** `docs/database/INSTITUTIONAL_ACCESS_WORKFLOW.md` (6,000+ words)
- **Publisher guide:** `docs/database/PUBLISHER_ACCESS_GUIDE.md` (5,000+ words)
- **Setup summary:** `docs/database/INSTITUTIONAL_ACCESS_SETUP_SUMMARY.md` (this file's full version)

---

## Quick Start (3 Steps)

### Step 1: Download Open Access Papers (2-3 hours)
**No institutional access needed!**

```bash
# Frontiers (343 papers) - ALL FREE
# PLOS (217 papers) - ALL FREE  
# PeerJ (81 papers) - ALL FREE

# Use the CSV files in outputs/by_publisher/
# Expected: 550-600 PDFs immediately
```

### Step 2: Set Up Institutional Access (30 minutes)
1. Configure institutional VPN/proxy
2. Test access to Elsevier, Wiley, Springer
3. Verify you can download 1-2 PDFs manually

### Step 3: Start Institutional Downloads (ongoing)
1. Use Priority 1 list: `outputs/acquisition_priority_1_recent_with_doi.csv`
2. Sort by publisher
3. Download in batches (100-200 per session)
4. Track progress in spreadsheet

---

## Expected Results

### Conservative (4-6 months, 5-10 hours/week)
- **Additional papers:** 5,200
- **Final coverage:** 57.5% (17,581 / 30,523)

### Optimistic (4-6 months, 10-15 hours/week)
- **Additional papers:** 10,500
- **Final coverage:** 74.9% (22,881 / 30,523)

### Realistic Target
- **Goal:** 70% coverage (21,366 papers)
- **Additional papers needed:** 8,985
- **Timeline:** 4-6 months

---

## File Locations

```
outputs/
├── acquisition_priority_1_recent_with_doi.csv       ← START HERE
├── acquisition_priority_2_2000s_with_doi.csv
├── acquisition_priority_3_key_journals.csv
├── acquisition_priority_4_no_doi_complete_metadata.csv
└── by_publisher/
    ├── priority1_frontiers.csv                      ← START HERE (FREE!)
    ├── priority1_plos.csv                           ← START HERE (FREE!)
    ├── priority1_elsevier.csv
    ├── priority1_wiley.csv
    └── ... (7 more publishers)

templates/
├── ILL_BATCH_REQUEST_TEMPLATE.csv
├── ILL_batch_1_most_recent.csv
├── ILL_batch_2_recent.csv
├── ILL_batch_3_2018_2020.csv
└── acquisition_tracking_template.xlsx

docs/database/
├── INSTITUTIONAL_ACCESS_WORKFLOW.md                 ← Read this first
├── PUBLISHER_ACCESS_GUIDE.md                        ← Read this second
└── INSTITUTIONAL_ACCESS_SETUP_SUMMARY.md            ← Complete details
```

---

## Current Status

### Collection Coverage
- **Total papers:** 30,523
- **Papers with PDFs:** 12,381 (40.5%)
- **Papers needed:** 18,142 (59.5%)

### What Was Tried (Automated)
- ✅ Unpaywall: 158 papers acquired
- ✅ PeerJ: 38 papers acquired
- ✅ Sci-Hub: 0 papers (none available)
- ❌ Google Scholar: Blocked
- ❌ Academia/ResearchGate: Blocked

### What's Next (Manual/Institutional)
- ⭐ Institutional access (best option)
- ⭐ ILL requests (high success rate)
- ⭐ Open repositories (ongoing)
- ⭐ Author requests (for recent papers)

---

## Need Help?

**Read the full guides:**
- `docs/database/INSTITUTIONAL_ACCESS_WORKFLOW.md` - Complete process
- `docs/database/PUBLISHER_ACCESS_GUIDE.md` - Publisher-specific help

**Contact support:**
- Institutional access issues → Library e-resources team
- ILL questions → Library ILL department  
- Technical problems → Library IT support

---

**Ready to start? Open `docs/database/INSTITUTIONAL_ACCESS_WORKFLOW.md` and follow Phase 1!**
