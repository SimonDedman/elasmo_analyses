# Publisher Direct Access Guide for Shark Paper Acquisition

**Created:** November 21, 2025
**Purpose:** Publisher-specific strategies for institutional access and bulk downloading
**Scope:** Top 10 publishers covering 67.9% of Priority 1 papers (6,116 papers)

---

## Publisher Distribution - Priority 1 Papers

**Total Priority 1 papers (2015+):** 9,003

| Publisher | Papers | % of Total | Access File |
|-----------|--------|------------|-------------|
| **Elsevier** | 1,604 | 17.8% | `outputs/by_publisher/priority1_elsevier.csv` |
| **Wiley** | 1,542 | 17.1% | `outputs/by_publisher/priority1_wiley.csv` |
| **Springer Nature** | 1,248 | 13.9% | `outputs/by_publisher/priority1_springer_nature.csv` |
| **Frontiers** | 343 | 3.8% | `outputs/by_publisher/priority1_frontiers.csv` |
| **Taylor & Francis** | 331 | 3.7% | `outputs/by_publisher/priority1_taylor_&_francis.csv` |
| **Inter-Research** | 303 | 3.4% | `outputs/by_publisher/priority1_inter-research.csv` |
| **Oxford University Press** | 236 | 2.6% | `outputs/by_publisher/priority1_oxford_university_press.csv` |
| **PLOS** | 217 | 2.4% | `outputs/by_publisher/priority1_plos.csv` |
| **Cambridge University Press** | 165 | 1.8% | `outputs/by_publisher/priority1_cambridge_university_press.csv` |
| **PeerJ** | 81 | 0.9% | `outputs/by_publisher/priority1_peerj.csv` |
| **Other** | 2,887 | 32.1% | `outputs/by_publisher/priority1_other.csv` |

---

## Publisher-Specific Strategies

### 1. Elsevier (ScienceDirect) - 1,604 papers (17.8%)

#### Key Journals
- Fisheries Research
- Deep Sea Research Part I & II
- Journal of Experimental Marine Biology and Ecology
- Progress in Oceanography
- Estuarine, Coastal and Shelf Science

#### Institutional Access
**URL:** https://www.sciencedirect.com/
**Login:** Institution selection → Find your institution → Shibboleth/OpenAthens login

**Proxy URL format:**
```
https://www.sciencedirect.com.ezproxy.[institution].edu/
```

#### Bulk Download Strategy
1. **Via DOI redirect** (recommended):
   ```python
   import requests
   doi = "10.1016/j.fishres.2024.107001"
   url = f"https://doi.org/{doi}"
   # Access via institutional proxy
   response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
   ```

2. **Via ScienceDirect API** (if available):
   - Request API key from library
   - Documentation: https://dev.elsevier.com/
   - Rate limit: 20,000 requests/week

3. **Direct download URLs**:
   Format: `https://www.sciencedirect.com/science/article/pii/[PII]/pdfft`
   - PII can be extracted from DOI or article page

#### Rate Limits
- **Interactive browsing:** No strict limit
- **Bulk download:** 100-200 papers/hour recommended
- **Download manager:** Allowed with delays (5-10 seconds between requests)

#### Tips
- ✅ Use "Export to PDF" button on article page
- ✅ Check for "Open access" badge (free to download)
- ✅ Many recent papers have OA versions
- ⚠️ Some older papers require separate permissions

---

### 2. Wiley Online Library - 1,542 papers (17.1%)

#### Key Journals
- **Journal of Fish Biology** (major source)
- Fish and Fisheries
- Journal of Applied Ichthyology
- Ecology of Freshwater Fish
- Marine Mammal Science

#### Institutional Access
**URL:** https://onlinelibrary.wiley.com/
**Login:** Institution selection → Shibboleth/OpenAthens

**Proxy URL format:**
```
https://onlinelibrary-wiley-com.ezproxy.[institution].edu/
```

#### Bulk Download Strategy
1. **Via DOI**:
   ```
   https://doi.org/10.1111/jfb.15234
   ```
   Redirects to full article with PDF download link

2. **Direct PDF URL**:
   Format: `https://onlinelibrary.wiley.com/doi/pdfdirect/[DOI]`
   Example: `https://onlinelibrary.wiley.com/doi/pdfdirect/10.1111/jfb.15234`

3. **Wiley Open Access**:
   - Many papers are hybrid OA
   - Check for "Open Access" label
   - No login required for OA papers

#### Rate Limits
- **Browsing:** No limit
- **Bulk download:** 100-150 papers/hour recommended
- **API access:** Limited (contact library)

#### Tips
- ✅ Journal of Fish Biology has many OA papers
- ✅ Use "Download PDF" button (not "View PDF" in browser)
- ✅ Export citation to verify correct paper
- ⚠️ Some early view papers may not have final DOI

---

### 3. Springer Nature - 1,248 papers (13.9%)

#### Key Journals
- Marine Biology
- Environmental Biology of Fishes
- Hydrobiologia
- Marine Ecology
- Coral Reefs

#### Institutional Access
**URL:** https://link.springer.com/
**Login:** Institution selection or Shibboleth

**Proxy URL format:**
```
https://link-springer-com.ezproxy.[institution].edu/
```

#### Bulk Download Strategy
1. **Via DOI**:
   ```
   https://doi.org/10.1007/s00227-024-12345
   ```

2. **Direct PDF URL**:
   Format: `https://link.springer.com/content/pdf/[DOI].pdf`
   Example: `https://link.springer.com/content/pdf/10.1007/s00227-024-12345.pdf`

3. **Springer Nature Open Access**:
   - Check for "Open access" badge
   - Many recent papers are OA
   - SharedIt links provide read-only access (not downloadable)

#### Rate Limits
- **Browsing:** No limit
- **Bulk download:** 100 papers/day recommended
- **API:** Springer Nature API available (request key)

#### Tips
- ✅ Many BMC journals are full OA
- ✅ SharedIt links allow reading but not downloading
- ✅ Check institutional access vs. open access
- ⚠️ Nature journals require special permissions

---

### 4. Frontiers - 343 papers (3.8%)

#### Key Journals
- Frontiers in Marine Science
- Frontiers in Ecology and Evolution
- Frontiers in Conservation Science

#### Institutional Access
**URL:** https://www.frontiersin.org/
**Login:** Not required - **All Frontiers journals are fully Open Access!**

#### Bulk Download Strategy
1. **Direct download** (no login needed):
   ```
   https://doi.org/10.3389/fmars.2024.12345
   ```

2. **PDF URL format**:
   Format: `https://www.frontiersin.org/articles/[DOI]/pdf`
   Example: `https://www.frontiersin.org/articles/10.3389/fmars.2024.12345/pdf`

#### Rate Limits
- **No authentication required**
- **Bulk download:** Be respectful (10-20 seconds delay)
- **100-200 papers/hour** recommended

#### Tips
- ✅ **ALL PAPERS ARE FREE** - No institutional access needed
- ✅ High-quality PDFs available
- ✅ XML and other formats also available
- ✅ Great source for recent shark research

---

### 5. Taylor & Francis - 331 papers (3.7%)

#### Key Journals
- Marine and Freshwater Research
- Journal of Natural History
- Marine Biology Research
- African Journal of Marine Science

#### Institutional Access
**URL:** https://www.tandfonline.com/
**Login:** Institution selection → Shibboleth/OpenAthens

**Proxy URL format:**
```
https://www-tandfonline-com.ezproxy.[institution].edu/
```

#### Bulk Download Strategy
1. **Via DOI**:
   ```
   https://doi.org/10.1080/12345678.2024.123456
   ```

2. **Direct PDF URL**:
   Format: `https://www.tandfonline.com/doi/pdf/[DOI]`
   Example: `https://www.tandfonline.com/doi/pdf/10.1080/12345678.2024.123456`

#### Rate Limits
- **Browsing:** No limit
- **Bulk download:** 50-100 papers/hour
- **Moderate rate limits** - use delays

#### Tips
- ✅ Many papers have green OA versions in repositories
- ⚠️ Some older papers require special permissions
- ⚠️ Download limits are stricter than other publishers

---

### 6. Inter-Research - 303 papers (3.4%)

#### Key Journals
- Marine Ecology Progress Series (MEPS)
- Aquatic Biology
- Endangered Species Research

#### Institutional Access
**URL:** https://www.int-res.com/
**Login:** IP-based (automatic if on campus network)

#### Bulk Download Strategy
1. **Via DOI**:
   ```
   https://doi.org/10.3354/meps12345
   ```

2. **Direct PDF access**:
   - Usually requires IP-based access
   - Check if institution subscribes

3. **Open Access**:
   - Some papers are OA (check article page)
   - Theme sections often OA

#### Rate Limits
- **IP-based access:** No explicit limits
- **Bulk download:** 50 papers/hour recommended
- **Small publisher** - be respectful

#### Tips
- ✅ MEPS is a major source of shark research
- ✅ Check for OA papers (free to all)
- ⚠️ Older papers may be harder to access
- ⚠️ Small publisher - download slowly

---

### 7. Oxford University Press - 236 papers (2.6%)

#### Key Journals
- ICES Journal of Marine Science
- Conservation Biology
- Integrative and Comparative Biology

#### Institutional Access
**URL:** https://academic.oup.com/
**Login:** Institution selection → Shibboleth/OpenAthens

**Proxy URL format:**
```
https://academic-oup-com.ezproxy.[institution].edu/
```

#### Bulk Download Strategy
1. **Via DOI**:
   ```
   https://doi.org/10.1093/icesjms/fsab123
   ```

2. **Direct PDF URL**:
   Format: `https://academic.oup.com/[journal]/article-pdf/[DOI]/[hash].pdf`
   - Hash is auto-generated, use DOI redirect instead

#### Rate Limits
- **Browsing:** No limit
- **Bulk download:** 100 papers/hour
- **API access:** Available with key

#### Tips
- ✅ Many papers have "Advance Access" versions
- ✅ Check for OA papers (clearly marked)
- ✅ Good institutional access coverage
- ⚠️ Some archives require special permissions

---

### 8. PLOS (Public Library of Science) - 217 papers (2.4%)

#### Key Journals
- PLOS ONE
- PLOS Biology

#### Institutional Access
**URL:** https://journals.plos.org/
**Login:** Not required - **All PLOS journals are fully Open Access!**

#### Bulk Download Strategy
1. **Direct download** (no login needed):
   ```
   https://doi.org/10.1371/journal.pone.0123456
   ```

2. **PDF URL format**:
   Format: `https://journals.plos.org/plosone/article/file?id=[DOI]&type=printable`
   Example: `https://journals.plos.org/plosone/article/file?id=10.1371/journal.pone.0123456&type=printable`

#### Rate Limits
- **No authentication required**
- **Bulk download:** Be respectful (5-10 seconds delay)
- **100-200 papers/hour** recommended

#### Tips
- ✅ **ALL PAPERS ARE FREE**
- ✅ XML format available for text mining
- ✅ CC-BY license (very permissive)
- ✅ Supplementary materials also downloadable

---

### 9. Cambridge University Press - 165 papers (1.8%)

#### Key Journals
- Journal of the Marine Biological Association of the UK
- Marine Biodiversity Records

#### Institutional Access
**URL:** https://www.cambridge.org/core/
**Login:** Institution selection → Shibboleth/OpenAthens

**Proxy URL format:**
```
https://www-cambridge-org.ezproxy.[institution].edu/
```

#### Bulk Download Strategy
1. **Via DOI**:
   ```
   https://doi.org/10.1017/S0025315423000123
   ```

2. **Direct PDF URL**:
   - Use DOI redirect to article page
   - Click "PDF" button for download

#### Rate Limits
- **Browsing:** No limit
- **Bulk download:** 50-100 papers/hour
- **Moderate restrictions**

#### Tips
- ✅ Some older papers are now OA
- ✅ Register for free account for better access
- ⚠️ Download manager may be blocked

---

### 10. PeerJ - 81 papers (0.9%)

#### Key Journals
- PeerJ (main journal)
- PeerJ PrePrints

#### Institutional Access
**URL:** https://peerj.com/
**Login:** Not required - **PeerJ is fully Open Access!**

#### Bulk Download Strategy
1. **Direct download** (no login needed):
   ```
   https://doi.org/10.7717/peerj.12345
   ```

2. **PDF URL format**:
   Format: `https://peerj.com/articles/[id].pdf`
   Example: `https://peerj.com/articles/12345.pdf`

#### Rate Limits
- **No authentication required**
- **Bulk download:** Be respectful (5-10 seconds delay)
- **100 papers/hour** recommended

#### Tips
- ✅ **ALL PAPERS ARE FREE**
- ✅ High-quality peer review
- ✅ XML and RDF formats available
- ⚠️ We already downloaded 38 PeerJ papers (see logs)

---

## Automated Download Script

### Python Script for Institutional Access

```python
import pandas as pd
import requests
import time
from pathlib import Path

def download_papers_by_publisher(csv_file, publisher_name, output_dir, delay=10):
    """
    Download papers from a specific publisher using institutional proxy

    Args:
        csv_file: Path to CSV with papers (must have 'doi_clean' column)
        publisher_name: Name of publisher (for logging)
        output_dir: Directory to save PDFs
        delay: Seconds to wait between downloads (default: 10)
    """

    # Load papers
    df = pd.read_csv(csv_file)
    print(f"Loaded {len(df)} papers from {publisher_name}")

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Download each paper
    success_count = 0
    fail_count = 0

    for idx, row in df.iterrows():
        doi = row['doi_clean']
        lit_id = row['literature_id']
        year = row['year']

        try:
            # Construct URL (via DOI redirect)
            url = f"https://doi.org/{doi}"

            # Add headers to mimic browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            # Request PDF (via institutional proxy if configured)
            response = requests.get(url, headers=headers, allow_redirects=True, timeout=30)

            if response.status_code == 200 and 'application/pdf' in response.headers.get('Content-Type', ''):
                # Save PDF
                filename = output_path / f"{lit_id}_{doi.replace('/', '_')}.pdf"
                with open(filename, 'wb') as f:
                    f.write(response.content)

                print(f"✓ Downloaded {lit_id}: {doi}")
                success_count += 1
            else:
                print(f"✗ Failed {lit_id}: {doi} (status: {response.status_code})")
                fail_count += 1

        except Exception as e:
            print(f"✗ Error {lit_id}: {doi} - {e}")
            fail_count += 1

        # Respectful delay
        time.sleep(delay)

    print(f"\n{'='*60}")
    print(f"Download complete for {publisher_name}")
    print(f"Success: {success_count} papers")
    print(f"Failed: {fail_count} papers")
    print(f"{'='*60}")

# Example usage
if __name__ == "__main__":
    # Download Frontiers papers (all OA, no login needed)
    download_papers_by_publisher(
        csv_file='outputs/by_publisher/priority1_frontiers.csv',
        publisher_name='Frontiers',
        output_dir='outputs/SharkPapers',
        delay=15  # 15 seconds between downloads
    )
```

---

## Quick Start Workflow

### Phase 1: Open Access Publishers (No Login Required)
**Estimated time:** 2-3 hours
**Expected downloads:** 600-700 papers

1. **Frontiers** (343 papers) - 100% OA
2. **PLOS** (217 papers) - 100% OA
3. **PeerJ** (81 papers) - 100% OA (but 38 already downloaded)

**Action:**
```bash
python scripts/download_oa_publishers.py
```

---

### Phase 2: Major Publishers (Institutional Access)
**Estimated time:** 10-15 hours
**Expected downloads:** 2,000-3,000 papers

1. **Elsevier** (1,604 papers) - Set up proxy, download in batches
2. **Wiley** (1,542 papers) - Many OA papers available
3. **Springer Nature** (1,248 papers) - Good institutional coverage

**Action:**
1. Configure institutional proxy in browser
2. Test access with 5-10 papers manually
3. Run automated script with delays
4. Monitor for any IP blocks or CAPTCHAs

---

### Phase 3: Remaining Publishers
**Estimated time:** 5-10 hours
**Expected downloads:** 800-1,200 papers

1. **Taylor & Francis** (331 papers)
2. **Inter-Research** (303 papers)
3. **Oxford** (236 papers)
4. **Cambridge** (165 papers)

---

### Phase 4: Other Publishers + ILL
**Estimated time:** Ongoing
**Expected downloads:** 1,000-2,000 papers

- Submit ILL requests for papers not accessible
- Use author requests for recent papers
- Manual downloads for high-priority gaps

---

## Troubleshooting

### Problem: "Access Denied" or "403 Forbidden"

**Solutions:**
1. Verify institutional access is active (try manually in browser)
2. Check if on campus network or VPN is connected
3. Clear cookies and try again
4. Contact library if subscription lapsed

### Problem: "Rate limit exceeded" or "Too many requests"

**Solutions:**
1. Increase delay between downloads (15-30 seconds)
2. Download in smaller batches (50 papers at a time)
3. Wait 1-2 hours before resuming
4. Check if IP was temporarily blocked

### Problem: PDF download is actually HTML page

**Solutions:**
1. Check if you're logged in properly
2. Some publishers redirect to HTML first - follow redirect
3. Look for "Download PDF" button in HTML
4. Verify content-type header before saving

### Problem: "Subscription required" for supposedly OA paper

**Solutions:**
1. Check if paper is hybrid OA (requires specific link)
2. Search for paper in open repositories (Unpaywall, BASE)
3. Request from author if recently published
4. Submit ILL request

---

## Legal & Ethical Reminder

### ✅ Allowed
- Downloading via institutional subscriptions
- Downloading open access papers
- Saving for personal research use
- Organizing into personal library

### ⚠️ Check Terms
- Bulk downloading (follow publisher terms)
- Using download managers
- Sharing within research team

### ❌ Not Allowed
- Circumventing paywalls
- Sharing publicly online
- Commercial use
- Exceeding institutional license terms

**Always review your institution's library policies before bulk downloading.**

---

## Support & Resources

### Technical Issues
- **Proxy problems:** Contact library IT
- **Access issues:** Contact e-resources librarian
- **Download script issues:** Check Python dependencies

### Publisher Support
- **Elsevier:** https://service.elsevier.com/
- **Wiley:** https://onlinelibrary.wiley.com/help
- **Springer Nature:** https://support.springernature.com/
- **Contact publisher support if systematic download issues occur**

---

## File References

- Publisher-specific paper lists: `outputs/by_publisher/`
- Download script: `scripts/download_institutional_access.py` (to be created)
- Tracking template: `templates/acquisition_tracking_template.xlsx`

---

**Document Version:** 1.0
**Last Updated:** November 21, 2025
**Coverage:** Top 10 publishers (67.9% of Priority 1 papers)
