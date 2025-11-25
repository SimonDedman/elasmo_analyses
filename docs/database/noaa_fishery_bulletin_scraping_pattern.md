# NOAA Fishery Bulletin Scraping Pattern

**Discovered:** 2025-11-17
**Papers affected:** 39 NOAA Fishery Bulletin papers with broken direct PDF links

---

## Problem

Direct PDF URLs in shark-references.com database are outdated:
- Example: `https://fisherybulletin.nmfs.noaa.gov/sites/default/files/pdf-content/fish-bull/crow.pdf`
- Now returns HTML page instead of PDF (website restructured)

---

## Solution Pattern

### Archive URL Structure

**Homepage:** https://spo.nmfs.noaa.gov/fb.htm

**Year-based browsing:**
- URL format: `https://spo.nmfs.noaa.gov/fb.htm?tid=All&field_fish_bull_year_value={offset}`
- **Offset calculation:** `offset = 2021 - year`

**Examples:**
| Year | Offset | URL |
|------|--------|-----|
| 2020 | 1 | `https://spo.nmfs.noaa.gov/fb.htm?tid=All&field_fish_bull_year_value=1` |
| 2010 | 11 | `https://spo.nmfs.noaa.gov/fb.htm?tid=All&field_fish_bull_year_value=11` |
| 1881 | 140 | `https://spo.nmfs.noaa.gov/fb.htm?tid=All&field_fish_bull_year_value=140` |

### Search Functionality

Search fields available at top of page:
- Title search
- Author search
- Can be used to locate specific papers when year is known

---

## Implementation Strategy

For each of the 39 failed NOAA Fishery Bulletin papers:

1. **Extract metadata from database:**
   - Paper title
   - Authors
   - Year

2. **Build year archive URL:**
   ```python
   year = paper['year']
   offset = 2021 - year
   url = f"https://spo.nmfs.noaa.gov/fb.htm?tid=All&field_fish_bull_year_value={offset}"
   ```

3. **Scrape year archive page:**
   - Parse HTML to find all papers from that year
   - Match by title or author

4. **Extract PDF link:**
   - Get actual PDF URL from matched paper
   - Download PDF

5. **Alternative - Use search:**
   - If year archive browsing fails
   - Use title/author search fields
   - Parse search results for PDF link

---

## Sample Papers to Test

From `/logs/pdf_download_log.csv`:

| Literature ID | URL | Expected Year |
|---------------|-----|---------------|
| 26125 | .../crow.pdf | Unknown |
| 25111 | .../dapp.pdf | Unknown |
| 25113 | .../dellapa.pdf | Unknown |
| 25112 | .../driggers.pdf | Unknown |
| 25114 | .../hueter.pdf | Unknown |

**Action needed:** Look up these literature IDs in database to get year and title for testing.

---

## Priority

- **Current:** Low (only 39 papers = 0.1% of database)
- **Revisit:** After DOI discovery and higher-priority sources
- **Estimated gain:** 35-39 PDFs (90-100% success rate, all government open access)

---

## Related Files

- Failed downloads log: `/logs/pdf_download_log.csv`
- Implementation script: `scripts/scrape_noaa_fishery_bulletin.py` (to be created)

---

**Status:** Documented, implementation deferred to lower priority
