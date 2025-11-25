# Institutional Access Workflow for Shark Paper Acquisition

**Created:** November 21, 2025
**Purpose:** Systematic process for acquiring paywalled papers through institutional and library resources
**Coverage:** Optimized strategy for obtaining the remaining 18,142 papers (59.5% of collection)

---

## Executive Summary

After automated scraping reached diminishing returns (40.5% coverage), institutional access provides the most effective path to completing the collection. This workflow prioritizes papers by research value and acquisition feasibility.

### Current Status
- **Total papers:** 30,523
- **PDFs acquired:** 12,381 (40.5%)
- **Papers needed:** 18,142
- **Papers with DOIs:** 16,642 (91.7% of needed papers)
- **Recent papers (2015+):** 9,003 with DOIs (highest priority)

### Acquisition Priorities
1. **Priority 1:** 9,003 recent papers (2015+) with DOIs
2. **Priority 2:** 5,035 papers (2000-2014) with DOIs
3. **Priority 3:** 3,038 papers from top shark journals
4. **Priority 4:** 65 papers without DOI but complete metadata

---

## Acquisition Methods (Ranked by Efficiency)

### Method 1: Institutional Library Access ⭐⭐⭐⭐⭐
**Best for:** Recent papers from major publishers
**Success rate:** 80-95%
**Cost:** Free (included in institutional subscription)
**Time:** Instant access

#### Access Channels
1. **Library website proxy/VPN**
   - Log in through institutional portal
   - Access subscribed journals directly
   - Download PDFs immediately

2. **Discovery services** (Primo, Summon, WorldCat)
   - Search by DOI or title
   - System checks institutional holdings
   - Direct link to full text if available

3. **Publisher platforms** (via institutional login)
   - Elsevier ScienceDirect
   - Springer Nature
   - Wiley Online Library
   - Taylor & Francis Online
   - Oxford Academic
   - Cambridge Core

#### Workflow
```
1. Open Priority 1 list (recent papers with DOIs)
2. Sort by publisher (batch similar journals together)
3. For each publisher group:
   - Log in via institutional access
   - Search by DOI or title
   - Download PDF if available
   - Mark paper as "downloaded" in tracking sheet
   - If not available → Move to ILL queue
```

---

### Method 2: Interlibrary Loan (ILL) ⭐⭐⭐⭐
**Best for:** Papers not in institutional subscriptions
**Success rate:** 90-98%
**Cost:** Usually free, sometimes £1-5 per article
**Time:** 2-7 days per article

#### ILL Services
Most academic institutions use one of:
- **ILLiad** (most common)
- **OCLC WorldShare ILL**
- **RapidILL**
- **BL Document Supply (UK)**

#### Batch Submission Strategy
1. **Prepare batch files** (25-50 papers per batch)
   - Export DOIs from priority lists
   - Include: Title, Authors, Journal, Year, Volume, Pages, DOI
   - Use ILL import format (usually tab-delimited or CSV)

2. **Submit in priority order**
   - Batch 1: Priority 1 papers (2024-2025, highest impact)
   - Batch 2: Priority 1 papers (2021-2023)
   - Batch 3: Priority 1 papers (2015-2020)
   - Then move to Priority 2 and 3

3. **Track progress**
   - Most ILL systems send email notifications
   - Download PDFs as they arrive
   - Record success/failure in tracking sheet

#### ILL Request Template
See `ILL_BATCH_REQUEST_TEMPLATE.csv` for importable format.

---

### Method 3: Open Access Repositories ⭐⭐⭐
**Best for:** Papers with preprints or green OA versions
**Success rate:** 20-40%
**Cost:** Free
**Time:** 5-10 minutes per paper

#### Repository Sources (Already Attempted)
- ✅ Unpaywall (158 papers acquired)
- ✅ Semantic Scholar (limited success)
- ⏳ **Not yet tried:**
  - BASE (Bielefeld Academic Search Engine)
  - CORE (COnnecting REpositories)
  - PubMed Central (for biomedical papers)
  - EuroPMC (European papers)
  - arXiv/bioRxiv (preprints)

#### Workflow
1. Search repository by DOI or title
2. Check for full-text PDF
3. Download if available
4. Validate paper matches (check authors, year)
5. Move to `SharkPapers/{year}/` directory

---

### Method 4: Author Requests ⭐⭐
**Best for:** Recent papers (last 5 years) when other methods fail
**Success rate:** 40-60% (varies by author responsiveness)
**Cost:** Free
**Time:** 1-14 days (many never respond)

#### Process
1. Find corresponding author email (usually in paper or institutional page)
2. Use ResearchGate "Request full-text" feature (if available)
3. Send polite email request:

```
Subject: Request for PDF: [Paper Title]

Dear Dr. [Author],

I am conducting a comprehensive literature review on shark research
and would greatly appreciate access to your paper:

[Full Citation]
DOI: [DOI]

I have been unable to access it through my institutional library.
Would you be willing to share a PDF copy for research purposes?

Thank you for your time and consideration.

Best regards,
[Your Name]
[Your Institution]
```

4. Track requests in spreadsheet (date sent, response received, PDF obtained)
5. **DO NOT mass-email** - send in small batches (10-20 per week)

---

### Method 5: Direct Purchase ⭐
**Best for:** Critical papers unavailable through other methods
**Success rate:** 99%
**Cost:** £20-40 per paper
**Time:** Instant

#### When to Use
- Paper is critical to research
- All other methods failed
- Paper is very recent (< 2 years old)
- Budget allows individual purchases

#### Purchase Options
1. Publisher website (one-time access)
2. Copyright Clearance Center
3. Individual journal purchase

⚠️ **Warning:** Only use for <10 high-priority papers. Cost adds up quickly.

---

## Recommended Workflow (Step-by-Step)

### Phase 1: Institutional Access (Weeks 1-2)
**Goal:** Acquire 2,000-4,000 papers

1. **Download Priority 1 list** (`acquisition_priority_1_recent_with_doi.csv`)
2. **Group by publisher** (use Excel/LibreOffice sort function)
3. **Set up institutional access**
   - Configure VPN/proxy
   - Bookmark publisher sites
   - Test access to 5-10 papers
4. **Daily downloads** (target: 100-200 papers/day)
   - 2 hours focused downloading
   - Use download manager for bulk operations
   - Organize into year folders immediately
5. **Track progress** in `acquisition_tracking.xlsx`

### Phase 2: ILL Requests (Weeks 2-4)
**Goal:** Request 1,000-2,000 papers, acquire 900-1,800

1. **Compile ILL batch** from papers not found in Phase 1
2. **Submit first batch** (50 papers)
3. **Monitor arrivals** (usually 2-7 days)
4. **Download and organize** as they arrive
5. **Submit subsequent batches** weekly
6. **Follow up on failures** after 2 weeks

### Phase 3: Repository Search (Weeks 3-5)
**Goal:** Acquire 500-1,000 papers from open repositories

1. **Search BASE** for papers not yet found
2. **Search CORE** for institutional repositories
3. **Check PubMed Central** for biomedical papers
4. **Download and validate** all finds
5. **Update tracking sheet**

### Phase 4: Author Requests (Weeks 4-8)
**Goal:** Acquire 200-400 papers from authors

1. **Identify papers** still missing after Phases 1-3
2. **Prioritize recent papers** (2020+) with responsive authors
3. **Send requests** in batches (10-20 per week)
4. **Follow up** after 1 week if no response
5. **Thank authors** who provide papers

### Phase 5: Manual Review & Purchase (Weeks 6-10)
**Goal:** Acquire remaining critical papers

1. **Review remaining gaps** (~5,000-10,000 papers)
2. **Assess criticality** - which papers are essential?
3. **Purchase** 5-10 most critical papers
4. **Document gaps** for future reference
5. **Accept coverage limits** - aim for 70-80% total coverage

---

## Tracking System

### Spreadsheet Structure
Create `acquisition_tracking.xlsx` with columns:

| Column | Description | Example |
|--------|-------------|---------|
| literature_id | Paper ID | 12345 |
| doi | Paper DOI | 10.1234/journal.2024.001 |
| title | Paper title | "Shark migration patterns..." |
| year | Publication year | 2024 |
| journal | Journal name | Journal of Fish Biology |
| priority | Priority tier (1-4) | 1 |
| method_attempted | Acquisition methods tried | Institutional, ILL |
| status | Current status | Downloaded, ILL Pending, Failed |
| date_acquired | Date PDF obtained | 2025-11-21 |
| notes | Any additional info | Received via ILL |

### Status Values
- **Downloaded** - PDF successfully acquired
- **Institutional Access** - Available through library
- **ILL Pending** - Interlibrary loan requested
- **ILL Received** - ILL fulfilled
- **Repository Found** - Found in open repository
- **Author Requested** - Email sent to author
- **Author Provided** - Author sent PDF
- **Purchase Required** - Needs direct purchase
- **Failed** - Unable to acquire through any method
- **Low Priority** - Deferred to future work

---

## Batch Processing Templates

### ILL Batch Request (CSV Format)
See separate file: `templates/ILL_BATCH_REQUEST_TEMPLATE.csv`

Required fields:
- ArticleTitle
- ArticleAuthor
- ArticleDate (Year)
- JournalTitle
- JournalVolume
- JournalIssue
- JournalPages
- DOI
- Notes

### Publisher Batch Download Script
For papers with institutional access, use provided Python script:

```bash
python scripts/download_institutional_access.py \
    --input outputs/acquisition_priority_1_recent_with_doi.csv \
    --publisher "Elsevier" \
    --proxy "http://ezproxy.yourinstitution.edu"
```

---

## Publisher-Specific Notes

### Elsevier (ScienceDirect)
- **Journals:** Fisheries Research, Deep Sea Research, Journal of Experimental Marine Biology
- **Access:** Institutional login or proxy
- **Bulk download:** Allowed via institutional access
- **API:** Available with API key (request from library)

### Springer Nature
- **Journals:** Marine Biology, Environmental Biology of Fishes
- **Access:** Institutional login or Shibboleth
- **Bulk download:** Allowed (rate limit: 100/day)
- **SharedIt links:** Sometimes provide free-to-read versions

### Wiley
- **Journals:** Journal of Fish Biology, Fish and Fisheries
- **Access:** Institutional login
- **Bulk download:** Allowed via institutional access
- **Open access hybrid:** Many papers have OA versions

### Taylor & Francis
- **Journals:** Marine and Freshwater Research, Journal of Natural History
- **Access:** Institutional login
- **Bulk download:** Moderate rate limits
- **Green OA:** Check for accepted manuscripts in repositories

### Oxford Academic
- **Journals:** ICES Journal of Marine Science
- **Access:** Institutional login
- **Bulk download:** Allowed
- **Advance Access:** Preprints often available

### Cambridge Core
- **Journals:** Journal of the Marine Biological Association
- **Access:** Institutional login
- **Bulk download:** Allowed with registration
- **Legacy content:** Older papers often OA

---

## Success Metrics & Estimates

### Conservative Estimates (6 months of work)
- **Institutional access:** 3,000 papers (33% of Priority 1)
- **ILL requests:** 1,500 papers (100 papers × 15 batches)
- **Open repositories:** 500 papers
- **Author requests:** 200 papers
- **Total:** 5,200 papers → **57.5% coverage** (12,381 + 5,200 = 17,581 / 30,523)

### Optimistic Estimates (6 months of intensive work)
- **Institutional access:** 6,000 papers (67% of Priority 1)
- **ILL requests:** 3,000 papers (150 papers × 20 batches)
- **Open repositories:** 1,000 papers
- **Author requests:** 500 papers
- **Total:** 10,500 papers → **74.9% coverage** (12,381 + 10,500 = 22,881 / 30,523)

### Realistic Target
- **Goal:** **70% coverage** (21,366 papers)
- **Additional papers needed:** 8,985
- **Timeline:** 4-6 months
- **Effort:** 10-15 hours per week

---

## Cost Estimates

### Free Methods (90% of papers)
- Institutional access: Free
- ILL (UK institutions): Usually free
- Open repositories: Free
- Author requests: Free (just time)

### Paid Methods (10% of papers)
- ILL fees (if charged): £2-5 per paper × 500 papers = £1,000-2,500
- Direct purchases: £30 per paper × 20 papers = £600
- **Total estimated cost:** £1,600-3,100

---

## Legal & Ethical Considerations

### ✅ ALLOWED
- Downloading papers via institutional access
- Requesting papers through ILL
- Downloading from open repositories
- Requesting papers from authors
- Purchasing papers for research use
- Storing papers for personal research

### ⚠️ GRAY AREA
- Using Sci-Hub for unavailable papers
- Sharing papers with colleagues
- Keeping papers after leaving institution

### ❌ NOT ALLOWED
- Mass downloading beyond institutional terms
- Sharing papers publicly
- Using papers for commercial purposes
- Circumventing paywalls without permission
- Violating publisher terms of service

**Recommendation:** Stay in the "ALLOWED" category. Methods in this guide are all legal and ethical.

---

## Tools & Resources

### Download Managers
- **Zotero** - Citation management + PDF storage
- **Mendeley** - Similar to Zotero
- **JDownloader** - Batch downloading tool
- **wget/curl** - Command-line downloading

### Organization Tools
- **Folder structure:** `SharkPapers/{year}/{lit_id}_{title}.pdf`
- **Naming convention:** `{literature_id}_{doi_or_year}_{short_title}.pdf`
- **Backup:** Regular backups to external drive + cloud

### Library Tools
- **LibKey Nomad** - Browser extension showing institutional access
- **Unpaywall** - Browser extension showing OA versions
- **Kopernio** - Browser extension with library integration

---

## Next Steps

1. **Review Priority 1 list** - Familiarize yourself with highest-priority papers
2. **Set up institutional access** - Configure VPN/proxy and test
3. **Create tracking spreadsheet** - Set up `acquisition_tracking.xlsx`
4. **Start Phase 1** - Begin institutional downloads (target: 100/day)
5. **Prepare ILL batches** - Compile first batch (50 papers)
6. **Schedule regular sessions** - Block 2 hours/day for paper acquisition

---

## Questions & Support

For questions about:
- **Institutional access:** Contact your library's e-resources team
- **ILL services:** Contact your library's ILL department
- **Publisher terms:** Check library website or ask liaison librarian
- **Technical issues:** Contact library IT support

---

## File References

- `outputs/acquisition_priority_1_recent_with_doi.csv` - 9,003 recent papers
- `outputs/acquisition_priority_2_2000s_with_doi.csv` - 5,035 papers from 2000s
- `outputs/acquisition_priority_3_key_journals.csv` - 3,038 papers from key journals
- `outputs/acquisition_priority_4_no_doi_complete_metadata.csv` - 65 papers for manual search
- `acquisition_tracking.xlsx` - Master tracking spreadsheet (create this)

---

**Document Version:** 1.0
**Last Updated:** November 21, 2025
**Status:** Active workflow, ready for implementation
