# Institutional Access for PDF Downloads

## Overview

Many PDFs (965 forbidden + 761 HTML errors = **1,726 papers, ~29%**) require institutional authentication. With your institutional login, these can be recovered.

---

## Method 1: Export Browser Cookies (Recommended)

### For Chrome:
1. Install "Get cookies.txt" extension
2. Log into your institutional portal (Elsevier, Wiley, Springer, etc.)
3. Click extension icon → "Export" → Save as `cookies.txt`

### For Firefox:
1. Install "cookies.txt" extension
2. Log into institutional portals
3. Export cookies

### Run Download with Cookies:
```bash
python3 scripts/retry_failed_downloads.py \
    --status forbidden error \
    --cookies cookies.txt
```

---

## Method 2: VPN + Proxy (Alternative)

If your institution uses IP-based authentication:

```bash
# Connect to institutional VPN first
# Then run normal download
python3 scripts/retry_failed_downloads.py --status forbidden error
```

---

## Expected Recovery

**With institutional access:**
- **Forbidden (965)**: 80-90% recovery expected
- **HTML errors (761)**: 60-70% recovery (many are ScienceDirect paywalls)
- **Total potential recovery**: ~1,400 additional PDFs

---

## Failure Report

**Created:** `/docs/database/pdf_download_failures.csv`

**Contains:**
- literature_id, filename, year, url
- status, message, download_date

**Send to shark-references** to report broken/incorrect URLs.

---

**Key Findings:**
- HTTP 441: 114 papers from sharksinternational.org (same URL - requires special access)
- HTTP 400: 82 papers (malformed URLs - report to shark-references)
- Timeouts: 104 papers (retrying now with 60s timeout)
