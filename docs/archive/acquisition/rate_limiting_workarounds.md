# Rate Limiting Workarounds

## Problem

Publishers (especially ScienceDirect, Wiley, Springer) implement rate limiting to prevent automated downloads. You'll see:
- "Too many requests" messages
- Temporary IP blocks (15-60 minutes)
- CAPTCHA requirements

---

## Solutions

### Option 1: Slow Down Click Speed (Recommended)

**For ScienceDirect:**
- Wait **10-15 seconds** between each click
- Do batches of **10-20 papers** then take a **5-minute break**
- Spread downloads over several days

**Updated workflow:**
1. Click a paper
2. Let PDF load fully (~3 seconds)
3. Close tab
4. **WAIT 10-15 seconds** before next click
5. After 10-20 papers, take 5-minute coffee break

### Option 2: Try Different Domains

Switch to domains with less strict rate limiting:

**Less strict (try these first):**
```bash
# PeerJ (81 papers) - Open access friendly
firefox "outputs/manual_downloads/manual_downloads_peerj_com.html"

# NCBI/PubMed Central (69 papers) - Government site, more lenient
firefox "outputs/manual_downloads/manual_downloads_ncbi_nlm_nih_gov.html"

# NOAA Fish Bulletin (69 papers) - Government, no limits
firefox "outputs/manual_downloads/manual_downloads_fishbull_noaa_gov.html"
```

**More strict (save for later):**
- ScienceDirect (262 papers) ⚠️ Very strict
- Wiley - Moderate limits
- Springer - Moderate limits

### Option 3: Wait for Block to Expire

**ScienceDirect typical block duration: 30-60 minutes**

While waiting:
1. Work on other domains (PeerJ, NCBI, NOAA)
2. Come back to ScienceDirect in 1 hour
3. Use slower clicking speed (10-15 sec delays)

### Option 4: Use Different Network

**Change your IP address:**
- Switch to mobile hotspot
- Use institutional VPN (different endpoint)
- Work from different location/network

Then resume ScienceDirect downloads.

### Option 5: Spread Over Multiple Days

**Best practice for large batches:**

**Day 1:**
- ScienceDirect: 50 papers (slow pace, 15-sec delays)
- PeerJ: All 81 papers (faster, open access)

**Day 2:**
- ScienceDirect: 50 more papers
- NCBI: All 69 papers
- NOAA: All 69 papers

**Day 3:**
- ScienceDirect: Remaining ~160 papers
- Other domains

### Option 6: Try Different Times of Day

**Less traffic = fewer rate limits:**
- Early morning (6-8 AM)
- Late evening (9-11 PM)
- Weekends

---

## Priority Order

Based on success likelihood and value:

### Tier 1: Do These First (Easy, No Limits)
1. **NOAA Fish Bulletin** (69 papers) - Government, no restrictions
2. **NCBI/PubMed Central** (69 papers) - Government, lenient
3. **PeerJ** (81 papers) - Open access, friendly

**Total:** 219 papers (~30-45 minutes)

### Tier 2: Moderate Effort (Some Limits)
4. **Journal of Parasitology** (64 papers) - Moderate pace
5. **SciELO Brazil** (43 papers) - Open access regional
6. **Other small domains** (100 papers combined)

**Total:** 207 papers (~45-60 minutes)

### Tier 3: Save for Last (Strict Limits)
7. **ScienceDirect** (262 papers) - ⚠️ Very strict, needs 10-15 sec delays
8. **Sharks International** (174 papers) - May have restrictions

**Total:** 436 papers (2-4 hours with breaks)

---

## Commands to Switch Domains

### Start with Easy Ones:

```bash
# NOAA Fish Bulletin (easy)
firefox "outputs/manual_downloads/manual_downloads_fishbull_noaa_gov.html"

# NCBI PubMed Central (easy)
firefox "outputs/manual_downloads/manual_downloads_ncbi_nlm_nih_gov.html"

# PeerJ (easy, open access)
firefox "outputs/manual_downloads/manual_downloads_peerj_com.html"
```

### Moderate Difficulty:

```bash
# Journal of Parasitology
firefox "outputs/manual_downloads/manual_downloads_journalofparasitology_org.html"

# SciELO Brazil
firefox "outputs/manual_downloads/manual_downloads_scielo_br.html"
```

### Return to ScienceDirect Later:

```bash
# Wait 1 hour, then retry with 15-second delays
firefox "outputs/manual_downloads/manual_downloads_sciencedirect_com.html"
```

---

## Monitoring Tip

The monitoring script (`monitor_firefox_pdfs.py`) is still running, so you can switch between HTML files and it will continue extracting PDFs automatically!

---

## Expected Timeline

**Realistic schedule with rate limits:**

**Week 1:**
- Day 1: Easy domains (219 papers, ~1 hour)
- Day 2: Moderate domains (207 papers, ~1.5 hours)
- Day 3: ScienceDirect batch 1 (50 papers, 15-min delays, ~15 minutes)
- Day 4: ScienceDirect batch 2 (50 papers)
- Day 5: ScienceDirect batch 3 (50 papers)

**Week 2:**
- Day 6-8: ScienceDirect remaining (~110 papers)
- Day 9: Sharks International (174 papers)
- Day 10: Buffer for any failures

**Total time:** ~6-10 hours spread over 2 weeks

---

## Current Status

✅ **Completed:** ~5 ScienceDirect papers
⏸️ **Blocked:** ScienceDirect (wait 30-60 min)
🎯 **Next:** Switch to PeerJ, NCBI, or NOAA (no rate limits)

---

## Recommendation NOW

**Switch to easy domains while waiting for ScienceDirect block to expire:**

1. Keep monitoring script running
2. Open PeerJ HTML file
3. Click through all 81 PeerJ papers (faster, no limits)
4. Then do NCBI (69 papers)
5. Then NOAA (69 papers)
6. By then (~1 hour), ScienceDirect block should be lifted
7. Resume ScienceDirect with 10-15 second delays

This way you're productive while waiting!
