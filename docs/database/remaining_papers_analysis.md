---
editor_options:
  markdown:
    wrap: 72
---

# Remaining 56.2% Papers - What's Been Tried & What's Left

**Date:** 2025-10-24
**Current Status:** 13,347 PDFs acquired (43.8%), 17,176 papers remaining (56.2%)

---

## Executive Summary

### What We Have
- **13,347 PDFs** successfully downloaded and organized
- **43.8% coverage** of the 30,523 papers in database
- Storage location: `/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers/`

### What We're Missing
- **17,176 papers** (56.2%) still without PDFs
- Breakdown of why they're missing documented below

---

## Download Methods Already Tried

### Method 1: Sci-Hub (MAJOR SUCCESS)
**Attempts:** 11,859 papers
**Estimated Success:** ~10,000-11,000 PDFs (most of our current collection)
**Success Rate:** ~85-90%

**What was tried:**
- Regular Sci-Hub downloads
- Tor-enabled Sci-Hub (to avoid rate limiting/blocking)
- Multiple mirrors tested

**Why this was so successful:**
- Sci-Hub bypasses paywalls
- Has massive coverage of pre-2020 literature
- Works for most major publishers (Elsevier, Wiley, Springer, etc.)

**What remains:**
- Papers Sci-Hub doesn't have (~10-15% of what we tried)
- Papers we haven't tried yet via Sci-Hub

---

### Method 2: Direct Publisher Downloads (MODERATE SUCCESS)
**Attempts:** 5,890 papers
**Valid PDFs:** ~600-1,000
**Success Rate:** 10-17%

**What was tried:**
- Direct HTTP requests to URLs from shark-references.com
- 30-60 second timeouts
- Rate limiting with delays

**Major failures:**
- **Paywalls (1,464 papers):** HTML login pages instead of PDFs
- **HTTP 403 Forbidden (933 papers):** Institutional access required
- **HTTP 404 Not Found (637 papers):** Broken/dead links
- **Timeouts (104 papers):** Too slow to download

**Key domains with failures:**
- Wiley Online Library: 337 papers (paywalled)
- ScienceDirect: 254 papers (CAPTCHA blocked)
- Sharks International: 174 papers (site dead)
- Taylor & Francis: 136 papers (restricted)
- NOAA sites: ~130 papers (government shutdown)

---

### Method 3: Open Access APIs (COMPLETE FAILURE)
**Attempts:** 50 papers (test run)
**Success:** 0 papers (0%)
**Time Spent:** ~330 seconds

**APIs tested:**
1. Unpaywall API
2. Semantic Scholar API
3. CrossRef API
4. Direct DOI resolution

**Why it failed:**
- Shark biology journals have poor OA policies
- Most papers published 2000-2020 are paywalled
- Recent papers (2020+) not yet in OA repositories
- Valid DOIs but papers simply aren't open access

**Decision:** Do not continue - would take ~5.5 hours with 0% success

---

### Method 4: Dropbox Personal Library (SMALL SUCCESS)
**Matched:** 423 papers from personal library
**New PDFs:** 97 (others were duplicates)
**Success Rate:** 100% (already had the files)

**One-time success** - can't be repeated unless you have more personal PDFs

---

### Method 5: Manual Downloads with Institutional Access (SMALL SUCCESS)
**Downloaded:** 192 PDFs manually
**Properly Matched:** 44 PDFs
**Pending Organization:** 148 PDFs (in unknown_year/)

**Sources used:**
- NCBI/PubMed Central (73 PDFs)
- PeerJ (81 PDFs - open access)
- SciELO (38 PDFs)

**Challenges:**
- Time-consuming (manual clicking)
- Poor PDF metadata (hard to match to database)
- Limited institutional access

---

### Method 6: Grey Literature / Theses (SMALL SUCCESS)
**Source:** OATD.org (Open Access Theses & Dissertations)
**Status:** Some downloaded (exact count unclear from logs)

**Challenges:**
- Most shark theses aren't in OATD
- Institutional repositories often restricted
- Lower priority (dissertations vs peer-reviewed papers)

---

## Papers NOT Yet Attempted

### Category 1: Papers with DOIs but No Sci-Hub Attempt
**Estimate:** ~5,000-10,000 papers

These papers have DOIs in the database but may not have been attempted via Sci-Hub yet, or were attempted early before Tor setup.

**Opportunity:** HIGH - Could yield 4,000-8,000 additional PDFs

---

### Category 2: Papers Without URLs (THE BIG ONE)
**Count:** 24,635 papers (80.7% of database!)

These papers have metadata (title, authors, journal, year) but NO PDF URL in shark-references.com database.

**Why they lack URLs:**
- Older papers (pre-2000) not digitized
- Not in any accessible repository
- Publisher never provided open access
- Grey literature (conference papers, reports)
- Local/regional journals

**What could be done:**
- DOI lookup (if DOI exists in metadata)
- Google Scholar searches (automated)
- ResearchGate/Academia.edu scraping
- Direct author contact
- Inter-library loan requests

**Opportunity:** MODERATE - Maybe 20-30% could be found (~5,000-7,000 PDFs)

---

### Category 3: Known Problematic Domains (Retry Opportunities)
**Count:** ~600-1,000 papers

**Temporarily down domains (could retry):**
- **NOAA sites** (~130 papers) - Down due to government shutdown
  - fishbull.noaa.gov (69 papers)
  - spo.nwr.noaa.gov (61 papers)
  - **Action:** Retry when shutdown ends

**Hijacked/broken domains (need alternatives):**
- **revbiolmar.cl** (39 papers) - Domain hijacked by casino
  - **Action:** Search institutional repos or contact authors
- **labomar.ufc.br** (31 papers) - All links broken
  - **Action:** Report to shark-references.com

**Blocked by CAPTCHA:**
- **ScienceDirect** (254 papers) - CAPTCHA blocks access
  - **Action:** Try institutional VPN or wait for fix

**Opportunity:** LOW-MODERATE - Maybe 200-400 could be recovered

---

## Opportunities to Increase Coverage

### 🔥 Option 1: Complete Sci-Hub Coverage (HIGHEST PRIORITY)
**Target:** All papers with DOIs not yet tried via Sci-Hub
**Potential Gain:** +4,000-8,000 PDFs
**Time Required:** 20-40 hours (can run overnight)
**Success Rate:** 70-85%

**Action:**
1. Query database for all papers with DOIs
2. Cross-reference against existing download logs
3. Run comprehensive Sci-Hub download (Tor-enabled)
4. Use conservative rate limiting (10-15 sec delays)

**Estimated final coverage:** 55-65% of database

---

### 🔥 Option 2: DOI Lookup for Papers Without URLs (HIGH PRIORITY)
**Target:** 24,635 papers with metadata but no URL
**Potential Gain:** +5,000-7,000 PDFs
**Time Required:** Varies (could be 50+ hours)
**Success Rate:** 20-30%

**Approach:**
1. Check if papers have DOIs in shark-references metadata
2. For papers with DOIs → try Sci-Hub
3. For papers without DOIs → skip or use Google Scholar

**Challenges:**
- Many older papers (pre-2000) lack DOIs
- Time-intensive if doing Google Scholar searches
- May duplicate effort with Option 1

**Estimated final coverage:** 60-70% of database (combined with Option 1)

---

### ⚠️ Option 3: Institutional Access (MEDIUM PRIORITY)
**Target:** Paywalled papers from major publishers
**Potential Gain:** +1,000-3,000 PDFs
**Time Required:** Depends on access level
**Success Rate:** 30-50%

**Requirements:**
- University VPN or institutional proxy
- Active library subscription
- Possibly manual clicking (if batch download blocked)

**Best targets:**
- Wiley (337 papers)
- Taylor & Francis (136 papers)
- Oxford University Press (64 papers)

**Estimated final coverage:** +3-10% additional

---

### ⚠️ Option 4: ResearchGate/Academia.edu Scraping (MEDIUM PRIORITY)
**Target:** Papers shared by authors on academic social networks
**Potential Gain:** +2,000-4,000 PDFs
**Time Required:** 30-50 hours
**Success Rate:** 20-40%

**Approach:**
1. Search ResearchGate for each paper title
2. Download if available (many authors post their papers)
3. Academia.edu similar approach

**Challenges:**
- Rate limiting on these platforms
- May require account/login
- Legal grey area (ToS violations)
- Author-uploaded versions may differ from published

**Estimated final coverage:** +5-15% additional

---

### 🔄 Option 5: Retry Temporary Failures (LOW PRIORITY)
**Target:** Papers from domains that were down/broken
**Potential Gain:** +200-400 PDFs
**Time Required:** 2-5 hours
**Success Rate:** 30-60%

**Specific targets:**
- NOAA sites (130 papers) - Retry post-shutdown
- Broken domain alternatives (70 papers)
- ScienceDirect via institutional access (254 papers)

**Estimated final coverage:** +1-2% additional

---

### ❌ Option 6: Author Contact (TIME-INTENSIVE, LOW PRIORITY)
**Target:** High-priority papers that can't be found elsewhere
**Potential Gain:** +500-2,000 PDFs (if you contact ~3,000-10,000 authors)
**Time Required:** Massive (100+ hours)
**Success Rate:** 15-30% response rate with PDFs

**Approach:**
1. Identify high-priority missing papers
2. Find author contact info
3. Send polite email requests
4. Wait for responses

**Only worthwhile for:**
- Key papers for your panel analysis
- Papers by specific panelists
- Recent high-impact work

---

## Recommended Strategy

### Phase 1: Quick Wins (Highest ROI)
1. ✅ **Consolidate folders** (DONE - just completed)
2. **Run complete Sci-Hub sweep** for all papers with DOIs
   - Target: Papers not in current download logs
   - Use Tor-enabled script
   - Run overnight
   - **Expected gain:** +4,000-8,000 PDFs

**Outcome:** 55-65% coverage with minimal effort

---

### Phase 2: If You Need More Coverage
3. **DOI lookup for papers without URLs**
   - Check shark-references for DOI fields
   - Try Sci-Hub for papers with DOIs
   - **Expected gain:** +3,000-5,000 PDFs

**Outcome:** 65-75% coverage

---

### Phase 3: Institutional Resources (If Available)
4. **Use institutional access** for major publishers
   - Wiley, Taylor & Francis, OUP
   - Requires university VPN/proxy
   - **Expected gain:** +1,000-3,000 PDFs

**Outcome:** 70-80% coverage

---

### Phase 4: Alternative Sources (Diminishing Returns)
5. **ResearchGate/Academia.edu** for author-posted papers
6. **Retry temporary failures** (NOAA, broken domains)
7. **Author contact** for high-priority gaps only

**Outcome:** Approaching 80-85% coverage (but time-intensive)

---

## What's Realistically Achievable

### With Minimal Effort (Just Sci-Hub)
- **Current:** 43.8% (13,347 PDFs)
- **After complete Sci-Hub sweep:** 60-65% (18,000-20,000 PDFs)
- **Time:** 20-40 hours automated
- **Recommendation:** **DO THIS**

### With Moderate Effort (Sci-Hub + DOI Lookup)
- **Coverage:** 65-75% (20,000-23,000 PDFs)
- **Time:** 50-100 hours (mostly automated)
- **Recommendation:** **Consider if you need better coverage**

### With High Effort (All Methods)
- **Coverage:** 75-85% (23,000-26,000 PDFs)
- **Time:** 150+ hours (lots of manual work)
- **Recommendation:** **Only for comprehensive systematic reviews**

### Theoretical Maximum
- **Coverage:** ~85-90% (26,000-27,000 PDFs)
- **Time:** 300+ hours (including author contact)
- **Recommendation:** **Not worth it for panel purposes**

---

## My Recommendation

### For Your EEA 2025 Panel

**Do:**
1. ✅ Keep the 13,347 PDFs you have (43.8%) - **SUFFICIENT** for panel
2. ✅ Organize and begin text extraction/classification
3. 🔄 **Optionally:** Run one final Sci-Hub sweep to get to 60-65%
   - Can run overnight
   - Minimal effort
   - Big payoff

**Don't:**
- Spend hundreds of hours chasing the last 20-30%
- Do manual Google Scholar searches for 20,000+ papers
- Contact thousands of authors
- You have enough for robust sampling across all disciplines/years

### The 43.8% You Have Is Actually Great Because:
1. **Representative sampling** across 75 years (1950-2025)
2. **Strong recent coverage** (2020-2025: 2,000+ PDFs)
3. **Decent historical coverage** (1970s-2010s: well-sampled)
4. **Sufficient for technique classification** across 8 disciplines
5. **Can identify gaps** after initial analysis, then target specific papers

---

## Final Numbers Summary

**Current State:**
- Have: 13,347 PDFs (43.8%)
- Missing: 17,176 papers (56.2%)

**After Recommended Quick Win (Sci-Hub Sweep):**
- Would have: ~19,000-20,000 PDFs (62-65%)
- Still missing: ~10,500-11,500 papers (35-38%)

**Remaining missing papers would be:**
- Genuinely unavailable (very old, not digitized)
- Behind strict paywalls Sci-Hub doesn't have
- Not worth the effort for panel purposes

---

*Next step: Decide if current 43.8% is sufficient, or run one final Sci-Hub sweep*
