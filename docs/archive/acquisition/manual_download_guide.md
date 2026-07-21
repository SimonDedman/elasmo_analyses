# Manual PDF Download System - Quick Start Guide

## Overview

This system allows you to manually download paywalled PDFs through your institutional browser access, while automatically extracting and organizing them.

**Total paywalled papers:** 1,485 (25.2%)

**Top domains:**
- ScienceDirect: 262 papers
- Sharks International: 174 papers
- PeerJ: 81 papers
- NCBI: 69 papers
- Fish Bulletin NOAA: 69 papers

---

## How It Works

1. **You click links** in Firefox (with institutional access logged in)
2. **Firefox caches the PDFs** when you view them
3. **Monitoring script watches the cache** and automatically extracts PDFs
4. **PDFs are saved** with timestamps and metadata

---

## Step-by-Step Instructions

### 1. Start the Monitoring Script

Open a terminal and run:

```bash
cd "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
python3 scripts/monitor_firefox_pdfs.py
```

**Leave this terminal open!** It will display each PDF as it's extracted.

### 2. Open HTML Click-Through List

In Firefox, open one of the generated HTML files:

**Start with ScienceDirect (262 papers):**
```bash
firefox "outputs/manual_downloads/manual_downloads_sciencedirect_com.html"
```

**Or other domains:**
```bash
# PeerJ (81 papers)
firefox "outputs/manual_downloads/manual_downloads_peerj_com.html"

# Sharks International (174 papers)
firefox "outputs/manual_downloads/manual_downloads_sharksinternational_org.html"
```

### 3. Click Through Links

**Important:** Make sure you're logged into your institutional access first!

For each paper:
1. Click the "📥 Download PDF" button
2. Wait ~2-3 seconds for the PDF to fully load
3. You should see the PDF content in Firefox
4. Close the tab (Ctrl+W)
5. Move to next paper

**Progress tracking:**
- The HTML page tracks which papers you've clicked (saved in browser)
- The monitoring script shows real-time extraction status
- Clicked papers fade out so you know what's done

### 4. Monitor Progress

In the monitoring terminal, you'll see:
```
✅ PDF #1 extracted:
   📄 Title: Effects of climate change on sharks
   👤 Author: Smith et al.
   💾 Size: 2.45 MB
   📁 Saved: 20251021_235530_0001_Effects_of_climate_change.pdf
```

### 5. Take Breaks

- Every 25-50 papers, take a short break
- Let the Firefox cache settle
- Check that PDFs are being extracted properly

---

## Output

**PDFs are saved to:**
```
outputs/SharkPapers/YYYYMMDD_HHMMSS_####_Title.pdf
```

**Extraction log:**
```
logs/firefox_cache_monitor.csv
```

Contains: timestamp, cache_file, output_file, file_size, title, author

---

## Tips for Success

### ✅ DO:
- **Log into institutional access FIRST**
- Let each PDF fully load before closing
- Keep monitoring script running
- Take breaks every 25-50 papers
- Check the monitoring terminal for errors

### ❌ DON'T:
- Close the monitoring script while clicking
- Click too fast (PDFs need time to cache)
- Close Firefox tabs before PDF loads
- Try to do multiple domains at once

---

## Troubleshooting

### PDFs Not Being Extracted

**Problem:** Monitoring script shows no new PDFs

**Solutions:**
1. Make sure PDF fully loads in browser (you see the content)
2. Wait 3-5 seconds after PDF displays
3. Check Firefox cache location is correct
4. Try restarting monitoring script

### Access Denied / Login Required

**Problem:** PDFs show login page instead of content

**Solutions:**
1. Log into your institutional portal
2. Access a test article to verify authentication
3. Try using institutional VPN if available
4. Some publishers require specific login method

### Duplicate PDFs

**Problem:** Same PDF extracted multiple times

**Solutions:**
- This is normal if you re-click a link
- Monitoring script timestamps each extraction
- You can manually deduplicate later

---

## Estimated Time

**Rate:** ~5-10 seconds per paper (with loading time)

**Totals:**
- ScienceDirect (262 papers): ~20-45 minutes
- PeerJ (81 papers): ~7-15 minutes
- All domains (1,485 papers): ~2-4 hours

**Recommendation:** Do in batches of 50-100 papers per session

---

## After Completion

Once you've clicked through all papers:

1. Stop the monitoring script (Ctrl+C)
2. Check the output directory for extracted PDFs
3. Review the extraction log for any issues
4. Rename PDFs using proper format:
   ```bash
   python3 scripts/rename_firefox_pdfs.py
   ```

---

## Alternative: Automated Cookie Method

If institutional access uses simple cookies (not Shibboleth), you can try:

```bash
# Extract cookies while logged in
python3 scripts/extract_firefox_cookies.py --domains sciencedirect.com

# Retry downloads with cookies
python3 scripts/retry_failed_downloads.py --status error --cookies cookies.txt
```

Note: This often doesn't work for paywalls, manual clicking is more reliable.

---

## Files Generated

**HTML click-through lists:**
```
outputs/manual_downloads/manual_downloads_sciencedirect_com.html (262 papers)
outputs/manual_downloads/manual_downloads_peerj_com.html (81 papers)
outputs/manual_downloads/manual_downloads_sharksinternational_org.html (174 papers)
... and 7 more domains
```

**Scripts:**
```
scripts/monitor_firefox_pdfs.py         - Cache monitoring
scripts/generate_manual_download_html.py - HTML generation
scripts/extract_firefox_cookies.py      - Cookie extraction (alternative)
```

**Documentation:**
```
docs/database/MANUAL_DOWNLOAD_GUIDE.md           - This guide
docs/database/institutional_access_guide.md      - Cookie method guide
docs/database/firefox_cookie_export_guide.md     - Firefox cookie export
```

---

**Ready to start?**

1. `python3 scripts/monitor_firefox_pdfs.py` in terminal
2. Open `outputs/manual_downloads/manual_downloads_sciencedirect_com.html` in Firefox
3. Start clicking!

Good luck! 🦈📄
