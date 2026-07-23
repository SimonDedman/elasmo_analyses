# Institutional Access Setup - Complete Summary

**Date:** November 21, 2025
**Session:** Post-crash recovery and Option 2 implementation
**Status:** ✅ Complete - Ready for implementation

---

## What Was Completed

### 1. Collection Gap Analysis ✅
**Identified:**
- **Total papers:** 30,523
- **Papers with PDFs:** 12,381 (40.5%)
- **Papers needed:** 18,142 (59.5%)
- **Papers with DOIs:** 16,642 (91.7% of needed papers)

**Key Finding:** The automated scraping phase has reached diminishing returns. Institutional access is now the most efficient strategy.

---

### 2. Prioritized Acquisition Lists ✅
Created **four priority tiers** based on research value and acquisition feasibility:

#### Priority 1: Recent papers with DOIs (2015+)
- **Count:** 9,003 papers
- **File:** `outputs/acquisition_priority_1_recent_with_doi.csv`
- **Strategy:** Start here - highest research value, easiest to acquire
- **Success rate:** 70-85% via institutional/ILL

#### Priority 2: Medium-age papers with DOIs (2000-2014)
- **Count:** 5,035 papers
- **File:** `outputs/acquisition_priority_2_2000s_with_doi.csv`
- **Strategy:** Second wave after Priority 1
- **Success rate:** 60-75% via institutional/ILL

#### Priority 3: Key journal papers (any year)
- **Count:** 3,038 papers
- **File:** `outputs/acquisition_priority_3_key_journals.csv`
- **Journals:** Top 10 shark research journals
- **Strategy:** Systematic journal-by-journal acquisition
- **Success rate:** 80-90% via institutional/ILL

#### Priority 4: Papers without DOI but complete metadata
- **Count:** 65 papers
- **File:** `outputs/acquisition_priority_4_no_doi_complete_metadata.csv`
- **Strategy:** Manual library searches or ILL
- **Success rate:** 50-70% (requires more effort)

---

### 3. Publisher-Specific Analysis ✅
**Analyzed Priority 1 papers by publisher:**

| Publisher | Papers | % | Access Type |
|-----------|--------|---|-------------|
| Elsevier | 1,604 | 17.8% | Institutional |
| Wiley | 1,542 | 17.1% | Institutional |
| Springer Nature | 1,248 | 13.9% | Institutional |
| Frontiers | 343 | 3.8% | **Open Access** |
| Taylor & Francis | 331 | 3.7% | Institutional |
| Inter-Research | 303 | 3.4% | Institutional |
| Oxford | 236 | 2.6% | Institutional |
| PLOS | 217 | 2.4% | **Open Access** |
| Cambridge | 165 | 1.8% | Institutional |
| PeerJ | 81 | 0.9% | **Open Access** |
| Other | 2,887 | 32.1% | Mixed |

**Created publisher-specific lists:**
- Location: `outputs/by_publisher/`
- 10 separate CSV files for targeted downloading
- Enables batch processing by publisher

---

### 4. Comprehensive Documentation ✅

#### A. Institutional Access Workflow
**File:** `docs/database/INSTITUTIONAL_ACCESS_WORKFLOW.md`

**Contents:**
- Step-by-step acquisition process
- 5 acquisition methods ranked by efficiency
- 5-phase implementation plan (10-week timeline)
- Tracking system setup
- Success metrics and cost estimates
- Legal and ethical guidelines

**Key Features:**
- Conservative estimate: 5,200 papers → 57.5% coverage
- Optimistic estimate: 10,500 papers → 74.9% coverage
- Realistic target: **70% coverage** (21,366 papers)

---

#### B. Publisher Access Guide
**File:** `docs/database/PUBLISHER_ACCESS_GUIDE.md`

**Contents:**
- Detailed guides for top 10 publishers
- Institutional login instructions
- Bulk download strategies
- Rate limits and best practices
- Troubleshooting section
- Python download script template

**Highlights:**
- **641 papers** (7.1%) are from fully OA publishers (Frontiers, PLOS, PeerJ)
- **5,475 papers** (60.8%) from major publishers with good institutional access
- Automated download possible with proper proxy configuration

---

### 5. ILL Batch Templates ✅

#### Created Templates:
1. **Main ILL template:** `templates/ILL_BATCH_REQUEST_TEMPLATE.csv`
   - Standard ILLiad-compatible format
   - 50 sample papers included
   - Ready for import to ILL system

2. **Pre-grouped batches:**
   - `templates/ILL_batch_1_most_recent.csv` (2024-2025)
   - `templates/ILL_batch_2_recent.csv` (2021-2023)
   - `templates/ILL_batch_3_2018_2020.csv` (2018-2020)
   - Each contains 50 papers ready for submission

3. **Tracking template:** `templates/acquisition_tracking_template.xlsx`
   - Columns: literature_id, doi, title, year, journal, priority, method, status, date, notes
   - Example rows included
   - Ready for progress tracking

---

## Files Created (Complete List)

### Priority Lists (4 files)
```
outputs/acquisition_priority_1_recent_with_doi.csv          (9,003 papers)
outputs/acquisition_priority_2_2000s_with_doi.csv           (5,035 papers)
outputs/acquisition_priority_3_key_journals.csv             (3,038 papers)
outputs/acquisition_priority_4_no_doi_complete_metadata.csv (65 papers)
```

### Publisher Lists (10 files)
```
outputs/by_publisher/priority1_elsevier.csv                 (1,604 papers)
outputs/by_publisher/priority1_wiley.csv                    (1,542 papers)
outputs/by_publisher/priority1_springer_nature.csv          (1,248 papers)
outputs/by_publisher/priority1_frontiers.csv                (343 papers)
outputs/by_publisher/priority1_taylor_&_francis.csv         (331 papers)
outputs/by_publisher/priority1_inter-research.csv           (303 papers)
outputs/by_publisher/priority1_oxford_university_press.csv  (236 papers)
outputs/by_publisher/priority1_plos.csv                     (217 papers)
outputs/by_publisher/priority1_cambridge_university_press.csv (165 papers)
outputs/by_publisher/priority1_peerj.csv                    (81 papers)
```

### Templates (5 files)
```
templates/ILL_BATCH_REQUEST_TEMPLATE.csv                    (50 papers)
templates/ILL_batch_1_most_recent.csv                       (50 papers)
templates/ILL_batch_2_recent.csv                            (50 papers)
templates/ILL_batch_3_2018_2020.csv                         (50 papers)
templates/acquisition_tracking_template.xlsx                (template with examples)
```

### Documentation (3 files)
```
docs/database/INSTITUTIONAL_ACCESS_WORKFLOW.md              (6,000+ words)
docs/database/PUBLISHER_ACCESS_GUIDE.md                     (5,000+ words)
docs/database/INSTITUTIONAL_ACCESS_SETUP_SUMMARY.md         (this file)
```

**Total files created:** 22

---

## Quick Start Guide

### Immediate Actions (This Week)

#### 1. Set Up Institutional Access (30 minutes)
- [ ] Configure VPN/proxy for your institution
- [ ] Test access to 5 publishers (Elsevier, Wiley, Springer, Frontiers, PLOS)
- [ ] Verify you can download at least 1 PDF from each
- [ ] Bookmark publisher login pages

#### 2. Download Open Access Papers (2-3 hours)
**No institutional access needed!**
- [ ] Frontiers: 343 papers (use `outputs/by_publisher/priority1_frontiers.csv`)
- [ ] PLOS: 217 papers (use `outputs/by_publisher/priority1_plos.csv`)
- [ ] PeerJ: 81 papers (43 remaining after previous downloads)

**Expected yield:** 550-600 PDFs immediately

#### 3. Set Up Tracking Spreadsheet (15 minutes)
- [ ] Open `templates/acquisition_tracking_template.xlsx`
- [ ] Save as `acquisition_tracking_working.xlsx`
- [ ] Import Priority 1 papers or start with Batch 1

---

### Phase 1 Plan (Weeks 1-2)

#### Week 1: Institutional Downloads
**Target:** 500-1,000 papers

**Day 1-2:** Elsevier papers (1,604 available)
- Focus on recent papers (2020+)
- Download 200-300 papers
- Track progress in spreadsheet

**Day 3-4:** Wiley papers (1,542 available)
- Many are open access - download those first
- Target 200-300 papers
- Note which papers are paywalled for ILL

**Day 5:** Springer Nature (1,248 available)
- Download 100-200 papers
- Check for SharedIt free-to-read versions

**Weekend:** Process and organize downloads
- Sort PDFs into year folders
- Update tracking spreadsheet
- Prepare ILL batch for Week 2

#### Week 2: ILL Submission + Continued Downloads
**Target:** Submit 150 ILL requests, download 300 more papers

**Day 1:** Submit first ILL batch
- Use `templates/ILL_batch_1_most_recent.csv` (50 papers)
- Monitor ILL system for confirmations

**Day 2-4:** Continue institutional downloads
- Taylor & Francis: 331 papers
- Oxford: 236 papers
- Cambridge: 165 papers

**Day 5:** Submit second ILL batch
- Use `templates/ILL_batch_2_recent.csv` (50 papers)

**Weekend:** Review progress
- Total PDFs acquired
- ILL request status
- Plan Week 3

---

### Success Metrics

#### Short-term (2 weeks)
- **Downloads:** 1,000-1,500 papers
- **ILL submitted:** 100-150 requests
- **Coverage:** 42-44% (from current 40.5%)

#### Medium-term (6 weeks)
- **Downloads:** 3,000-4,000 papers
- **ILL submitted:** 500-750 requests
- **ILL received:** 400-600 papers
- **Coverage:** 50-55%

#### Long-term (4-6 months)
- **Total acquired:** 8,000-10,000 papers
- **Final coverage:** 65-75%
- **Status:** Ready for comprehensive analysis

---

## Cost Estimate

### Free Methods (90-95% of papers)
- Institutional access: **Free**
- Open access papers: **Free**
- ILL (most UK institutions): **Free or £1-2 per paper**
- Author requests: **Free**

### Potential Costs
- ILL fees (if charged): £500-1,500 (500 papers × £1-3)
- Direct purchases (10-20 critical papers): £300-600
- **Total estimated: £800-2,100**

Most institutions cover ILL costs for research, so actual out-of-pocket may be **£0-300**.

---

## Timeline Estimate

### Optimistic (Intensive Work)
- **4 months** to reach 70% coverage
- **10-15 hours per week**
- Focused downloading sessions
- Regular ILL batch submissions

### Realistic (Steady Progress)
- **6 months** to reach 70% coverage
- **5-10 hours per week**
- Balanced with other research
- Periodic download sessions

### Conservative (Part-time)
- **9-12 months** to reach 65% coverage
- **2-5 hours per week**
- Opportunistic downloading
- Slower ILL processing

---

## Technical Requirements

### Software Needed
- ✅ Python 3 (already installed)
- ✅ Pandas (already installed)
- ✅ Requests library (already installed)
- ⚠️ Institutional VPN/proxy (check with IT)
- ⚠️ Browser with bookmark manager
- ⚠️ Excel/LibreOffice (for tracking)

### Optional Tools
- Zotero or Mendeley (citation management)
- JDownloader (download manager)
- Browser extensions: LibKey Nomad, Unpaywall

---

## Support Resources

### Internal Documentation
- 📄 `INSTITUTIONAL_ACCESS_WORKFLOW.md` - Complete process guide
- 📄 `PUBLISHER_ACCESS_GUIDE.md` - Publisher-specific instructions
- 📄 `DOWNLOAD_TOOLS_GUIDE.md` - Existing download automation docs

### Institutional Support
- **Library e-resources team:** VPN/proxy setup, access issues
- **ILL department:** Batch submissions, request status
- **IT support:** Technical problems, network issues

### External Resources
- Unpaywall browser extension: https://unpaywall.org/
- LibKey Nomad: https://www.thirdiron.com/libkey-nomad/
- Your institution's library guides

---

## Known Issues & Solutions

### Issue 1: PDF Directory Mismatch
**Problem:** Main PDF collection is in `/home/simon/Documents/Si Work/Papers & Books/SharkPapers` but scripts save to `outputs/SharkPapers`

**Solution:** Decide on single location and update all scripts. Recommend:
```bash
# Symlink to consolidate
ln -s "/home/simon/Documents/Si Work/Papers & Books/SharkPapers" outputs/SharkPapers
```

### Issue 2: DOI Cleaning Inconsistencies
**Problem:** Some DOIs have trailing periods, "DOI:" prefixes, or URLs

**Solution:** All priority lists have `doi_clean` column with standardized DOIs

### Issue 3: Automated Scraping Hit Limits
**Problem:** Recent retry session only recovered 19/271 papers (7% vs. expected 40%)

**Solution:** Shift strategy to institutional/ILL (this plan addresses this)

---

## Next Steps Summary

### Immediate (Today)
1. ✅ Review this summary and all documentation
2. ⏳ Test institutional access to 5 publishers
3. ⏳ Download first 50 OA papers (Frontiers/PLOS) as test

### This Week
1. ⏳ Set up tracking spreadsheet
2. ⏳ Download 500-700 OA papers (Frontiers, PLOS, PeerJ)
3. ⏳ Begin Elsevier/Wiley institutional downloads (200-300 papers)

### Next 2 Weeks
1. ⏳ Submit first ILL batch (50 papers)
2. ⏳ Continue institutional downloads (target: 1,000 papers)
3. ⏳ Monitor ILL arrivals and organize

### Month 1
1. ⏳ Reach 1,500-2,000 papers acquired
2. ⏳ Submit 150-200 ILL requests
3. ⏳ Establish sustainable weekly routine

---

## Questions?

**About this setup:**
- All documentation is in `docs/database/`
- All data files are in `outputs/`
- All templates are in `templates/`

**Need help with:**
- **Technical issues:** Check `PUBLISHER_ACCESS_GUIDE.md` troubleshooting section
- **Process questions:** Review `INSTITUTIONAL_ACCESS_WORKFLOW.md`
- **ILL questions:** Contact your library's ILL department
- **Access issues:** Contact library e-resources team

---

## Success Criteria

### Setup Phase (Complete ✅)
- ✅ Gap analysis completed
- ✅ Priority lists created
- ✅ Publisher analysis completed
- ✅ Documentation written
- ✅ Templates prepared

### Implementation Phase (Ready to Start)
- ⏳ Institutional access configured
- ⏳ First 500 papers downloaded
- ⏳ ILL system tested
- ⏳ Tracking system operational

### Achievement Phase (Goals)
- ⏳ 70% coverage reached (21,366 papers)
- ⏳ All Priority 1 papers attempted
- ⏳ Documentation of remaining gaps
- ⏳ Ready for comprehensive analysis

---

**Document Version:** 1.0
**Created:** November 21, 2025
**Status:** Setup complete, ready for implementation
**Next Action:** Test institutional access and download first batch of OA papers

---

## Archive Note

This setup replaces the automated scraping strategy which reached diminishing returns at 40.5% coverage after attempting:
- DOI discovery (3.3% success)
- Sci-Hub (0% success)
- Unpaywall (55.8% success of OA papers)
- PeerJ browser automation (43% success)
- Google Scholar/Academia/ResearchGate (blocked)

The institutional access strategy is expected to achieve 65-75% coverage in 4-6 months with significantly higher success rates and full legal/ethical compliance.
