# PDF Download Report

**Date:** 2025-10-21 21:11:36
**Source:** Literature Review Database
**Output:** /media/simon/data/Documents/Si Work/Papers & Books/SharkPapers

---

## Summary

**Total papers in database:** 5,888
**Papers attempted:** 5,888

### Download Results

| Status | Count | Percentage |
|--------|-------|------------|
| success | 2,697 | 45.8% |
| error | 1,485 | 25.2% |
| forbidden | 965 | 16.4% |
| not_found | 637 | 10.8% |
| timeout | 104 | 1.8% |

### Storage

- **Total downloaded:** 15.23 GB
- **Average PDF size:** 5.78 MB
- **Output directory:** `/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers`

---

## Common Issues

**Top 10 error types:**

- Access forbidden (paywall/authentication): 965 papers
- PDF not found (404): 637 papers
- Not a valid PDF (got text/html; charset=utf-8): 442 papers
- Not a valid PDF (got text/html): 319 papers
- HTTP 441: 114 papers
- Timeout after 30s: 104 papers
- HTTP 400: 82 papers
- Request error: HTTPSConnectionPool(host='spo.nwr.noaa.gov', port=443): Max retries exceeded with url: /tr90opt.pdf : 34 papers
- Request error: HTTPSConnectionPool(host='www.labomar.ufc.br', port=443): Max retries exceeded with url: /images/sto: 31 papers
- Request error: HTTPSConnectionPool(host='www.springerlink.com', port=443): Max retries exceeded with url: /content/: 24 papers


---

## Next Steps

### Successful Downloads (2,697 PDFs)
- Ready for full text extraction
- Can extract author affiliations
- Can search for subtechniques

### Failed Downloads (3,191 papers)
- **Paywalls:** 965 papers - require institutional access
- **Not Found:** 637 papers - broken links
- **Timeouts:** 104 papers - retry later
- **Other Errors:** 1,485 papers - check log for details

### Recommendations

1. **Re-run for timeouts:** Some papers may succeed on retry
2. **Institutional access:** Use VPN/proxy for paywalled papers
3. **Manual download:** For critical papers, download manually
4. **Alternative sources:** Check ResearchGate, author websites, etc.

---

**Log file:** `/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel/logs/pdf_download_log.csv`
**Report generated:** 2025-10-21 21:11:36
