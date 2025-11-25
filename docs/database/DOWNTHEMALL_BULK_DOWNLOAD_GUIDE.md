# DownThemAll Bulk Download Strategy for Shark Papers

**Created:** November 21, 2025
**Purpose:** Maximize download efficiency using DownThemAll Firefox extension with multi-tab strategy
**Tool:** DownThemAll (DTA) - Firefox Extension

---

## Overview

DownThemAll can scan **all open tabs** in a Firefox window and batch download PDFs. This enables:
- **100-500 papers per batch** (limited by browser memory, not DTA)
- **Automated filtering** (only PDFs)
- **Queue management** with pause/resume
- **Rate limiting** to avoid publisher blocks
- **Parallel downloads** (5-20 simultaneous)

**Key advantage:** Open hundreds of DOI tabs → DTA scans all → Download all PDFs in one click

---

## Setup & Configuration

### 1. Install DownThemAll
**Firefox Add-on:** https://www.downthemall.net/

**Installation:**
1. Open Firefox
2. Go to Add-ons (Ctrl+Shift+A)
3. Search "DownThemAll"
4. Click "Add to Firefox"
5. Grant necessary permissions

### 2. Configure DownThemAll Settings

**Recommended settings for bulk academic paper downloads:**

#### A. General Settings
```
Max concurrent downloads: 10-15
  (Higher = faster, but more likely to trigger rate limits)

Segments per download: 1
  (PDFs don't benefit from multi-segment downloads)

Download directory: /home/simon/Documents/Si Work/Papers & Books/SharkPapers/{YEAR}/
  (Use DTA's directory selection per batch)
```

#### B. Network Settings
```
Connection timeout: 60 seconds
  (Academic sites can be slow)

Retry failed downloads: 3 attempts
  (Publishers sometimes have transient errors)

Delay between downloads: 2-5 seconds
  (Critical for avoiding rate limits!)
```

#### C. Filter Settings
```
File type filter: *.pdf
Fast filter mode: Enabled
Include linked files: Enabled
Max depth: 1
  (Don't follow links beyond the current page)
```

---

## Strategy 1: DOI Redirect Multi-Tab (RECOMMENDED)

### Concept
Open 100-300 tabs with DOI URLs → Each redirects to publisher → DTA scans all tabs → Downloads all PDFs

### Step-by-Step Process

#### Phase 1: Generate Tab URLs
**Create a file with DOI URLs for bulk opening:**

```bash
./venv/bin/python3 << 'PYEOF'
import pandas as pd

# Load priority list
df = pd.read_csv('outputs/by_publisher/priority1_frontiers.csv')

# Generate DOI URLs (first 100 papers)
batch = df.head(100)
urls = [f"https://doi.org/{doi}" for doi in batch['doi_clean']]

# Save as HTML file that opens all tabs
html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Batch Open Papers - Frontiers</title>
    <script>
        function openAllTabs() {
            const urls = """ + str(urls).replace("'", '"') + """;

            // Confirm before opening many tabs
            if (confirm('Open ' + urls.length + ' tabs? This may take 30-60 seconds.')) {
                urls.forEach((url, index) => {
                    setTimeout(() => {
                        window.open(url, '_blank');
                    }, index * 100); // 100ms delay between each tab
                });
            }
        }
    </script>
</head>
<body>
    <h1>Batch Paper Downloader</h1>
    <p>This will open """ + str(len(urls)) + """ tabs with paper DOI links.</p>
    <button onclick="openAllTabs()" style="font-size: 20px; padding: 15px 30px;">
        Open All Tabs (""" + str(len(urls)) + """ papers)
    </button>

    <h2>Publisher: Frontiers (Open Access)</h2>
    <p>Expected download size: ~""" + str(len(urls) * 2) + """ MB</p>
    <p>Estimated time: 5-10 minutes</p>
</body>
</html>
"""

with open('outputs/batch_download_frontiers_100.html', 'w') as f:
    f.write(html_content)

print(f"✓ Created batch file: outputs/batch_download_frontiers_100.html")
print(f"  Papers: {len(urls)}")
print(f"  Open in Firefox and click button to open all tabs")
PYEOF
```

#### Phase 2: Open Tabs in Firefox
1. **Open dedicated Firefox window** (Ctrl+N for new window)
2. **Open the HTML file:** `outputs/batch_download_frontiers_100.html`
3. **Click "Open All Tabs" button**
4. **Wait 30-60 seconds** for all tabs to load
5. **Firefox will redirect each DOI to publisher page**

**Tips:**
- Close other Firefox windows to preserve memory
- Use a machine with 8GB+ RAM (100 tabs ≈ 2-4GB RAM)
- Don't interact with tabs while they load

#### Phase 3: Use DownThemAll
1. **Right-click anywhere** → **DownThemAll!** → **All Tabs**
2. **DTA scans all open tabs** for PDF links
3. **Filter results:**
   - Check "Fast filter" → Enter: `*.pdf`
   - Uncheck non-PDF files
4. **Select download directory:**
   - Example: `/home/simon/Documents/Si Work/Papers & Books/SharkPapers/2024/`
5. **Configure filename mask:**
   - Use: `*name*` (keeps original filename)
   - Or: `{num3}_{name}` (adds sequence number)
6. **Click "Download"**
7. **Monitor progress** in DTA window

#### Phase 4: Cleanup
1. **After downloads complete:** Close all tabs (Ctrl+W, keep pressing)
2. **Verify downloads:** Check folder for PDF count
3. **Move/rename** PDFs with literature IDs if needed
4. **Mark as complete** in tracking spreadsheet

---

## Strategy 2: Publisher-Specific Multi-Tab

### For Publishers with Direct PDF URLs

Some publishers allow direct PDF links (bypassing article page):

#### Elsevier ScienceDirect
```python
# Generate direct PDF URLs
doi = "10.1016/j.fishres.2024.107001"
pii = extract_pii_from_doi(doi)  # Extract PII
url = f"https://www.sciencedirect.com/science/article/pii/{pii}/pdfft"
```

#### Springer Nature
```python
doi = "10.1007/s00227-024-12345"
url = f"https://link.springer.com/content/pdf/{doi}.pdf"
```

#### Wiley
```python
doi = "10.1111/jfb.15234"
url = f"https://onlinelibrary.wiley.com/doi/pdfdirect/{doi}"
```

**Advantage:** Opens directly to PDF, faster than DOI redirect

**Script to generate publisher-specific URLs:**

```bash
./venv/bin/python3 << 'PYEOF'
import pandas as pd
import re

def generate_pdf_url(row):
    """Generate direct PDF URL based on publisher"""
    doi = row['doi_clean']
    publisher = row['publisher']

    if publisher == 'Springer Nature':
        return f"https://link.springer.com/content/pdf/{doi}.pdf"
    elif publisher == 'Wiley':
        return f"https://onlinelibrary.wiley.com/doi/pdfdirect/{doi}"
    elif publisher == 'Frontiers':
        return f"https://www.frontiersin.org/articles/{doi}/pdf"
    elif publisher == 'PLOS':
        return f"https://journals.plos.org/plosone/article/file?id={doi}&type=printable"
    elif publisher == 'PeerJ':
        # Extract ID from DOI (e.g., 10.7717/peerj.12345 → 12345)
        peerj_id = doi.split('.')[-1]
        return f"https://peerj.com/articles/{peerj_id}.pdf"
    else:
        # Default to DOI redirect
        return f"https://doi.org/{doi}"

# Load publisher-specific file
df = pd.read_csv('outputs/by_publisher/priority1_springer_nature.csv')
df['pdf_url'] = df.apply(generate_pdf_url, axis=1)

# Save URLs for batch opening
urls = df['pdf_url'].head(100).tolist()

# Generate HTML opener
html = f"""<!DOCTYPE html>
<html><head><title>Springer Nature Batch (100 papers)</title>
<script>
function openAll() {{
    const urls = {str(urls).replace("'", '"')};
    if (confirm('Open ' + urls.length + ' PDF tabs?')) {{
        urls.forEach((url, i) => setTimeout(() => window.open(url, '_blank'), i * 150));
    }}
}}
</script></head>
<body>
<h1>Springer Nature - Direct PDF Links</h1>
<button onclick="openAll()" style="font-size:20px;padding:15px;">Open {len(urls)} PDFs</button>
</body></html>"""

with open('outputs/batch_springer_direct_100.html', 'w') as f:
    f.write(html)

print(f"✓ Created: outputs/batch_springer_direct_100.html")
PYEOF
```

---

## Strategy 3: Institutional Proxy Multi-Tab

### For Papers Requiring Institutional Access

**If your institution uses EZProxy or similar:**

```python
# Add proxy prefix to URLs
proxy_prefix = "https://doi-org.ezproxy.yourinstitution.edu/"
doi = "10.1016/j.fishres.2024.107001"
url = f"{proxy_prefix}{doi}"
```

**Benefits:**
- Automatic authentication via proxy
- No manual login needed
- Works with DTA multi-tab scanning

**Setup:**
1. Get proxy URL from your library website
2. Modify URL generator script to add proxy prefix
3. Open tabs → DTA scans → Downloads with institutional access

---

## Batch Size Optimization

### Browser Memory Limits

**Firefox memory usage per tab:**
- Empty tab: ~10-20 MB
- Article page: ~30-50 MB
- PDF page: ~50-100 MB (if PDF renders in browser)

**Recommended batch sizes:**

| RAM Available | Recommended Batch | Max Batch |
|---------------|-------------------|-----------|
| 4 GB | 50 tabs | 75 tabs |
| 8 GB | 100 tabs | 150 tabs |
| 16 GB | 200 tabs | 300 tabs |
| 32 GB | 300 tabs | 500 tabs |

**Signs you've opened too many tabs:**
- Browser becomes unresponsive
- Tabs take >2 minutes to load
- System swap usage increases
- Mouse cursor lags

**Solution:** Close half the tabs and try again with smaller batch

---

## Download Speed & Rate Limits

### Publisher-Specific Limits

**Open Access (No limits):**
- Frontiers: 20-50 PDFs/minute ✅
- PLOS: 20-50 PDFs/minute ✅
- PeerJ: 20-50 PDFs/minute ✅

**Major Publishers (Moderate limits):**
- Elsevier: 10-20 PDFs/minute (use 3-5 sec delay)
- Wiley: 10-20 PDFs/minute (use 3-5 sec delay)
- Springer Nature: 10-15 PDFs/minute (use 4-6 sec delay)

**Conservative Publishers (Strict limits):**
- Taylor & Francis: 5-10 PDFs/minute (use 6-10 sec delay)
- Oxford: 10-15 PDFs/minute (use 4-6 sec delay)

### DTA Configuration by Publisher

**For Open Access (Fast):**
```
Max concurrent: 20
Delay: 1-2 seconds
```

**For Major Publishers (Moderate):**
```
Max concurrent: 10
Delay: 3-5 seconds
```

**For Conservative Publishers (Slow):**
```
Max concurrent: 5
Delay: 6-10 seconds
```

---

## Automated Batch Script

### Complete workflow automation:

```bash
./venv/bin/python3 << 'PYEOF'
import pandas as pd
import json

def create_batch_html(csv_file, publisher_name, batch_size, start_idx=0):
    """
    Create HTML file that opens N tabs for DownThemAll batch downloading

    Args:
        csv_file: Path to CSV with papers
        publisher_name: Name of publisher (for title)
        batch_size: Number of papers per batch
        start_idx: Starting index (for multiple batches)
    """

    # Load papers
    df = pd.read_csv(csv_file)
    batch = df.iloc[start_idx:start_idx + batch_size]

    # Generate URLs (DOI redirect for simplicity)
    urls = [f"https://doi.org/{doi}" for doi in batch['doi_clean'] if pd.notna(doi)]

    # Create HTML
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{publisher_name} Batch {start_idx//batch_size + 1}</title>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }}
        button {{ font-size: 20px; padding: 15px 30px; background: #4CAF50; color: white; border: none; cursor: pointer; }}
        button:hover {{ background: #45a049; }}
        .info {{ background: #f0f0f0; padding: 15px; margin: 20px 0; border-radius: 5px; }}
        .warning {{ background: #fff3cd; padding: 15px; margin: 20px 0; border-radius: 5px; }}
    </style>
    <script>
        function openAllTabs() {{
            const urls = {json.dumps(urls)};

            if (urls.length === 0) {{
                alert('No URLs to open!');
                return;
            }}

            if (!confirm('Open ' + urls.length + ' tabs?\\n\\nThis will take 30-60 seconds.\\nDo not close this window until all tabs are open.')) {{
                return;
            }}

            document.getElementById('status').innerHTML = 'Opening tabs: 0/' + urls.length;
            document.getElementById('openBtn').disabled = true;

            let opened = 0;
            urls.forEach((url, index) => {{
                setTimeout(() => {{
                    window.open(url, '_blank');
                    opened++;
                    document.getElementById('status').innerHTML = 'Opening tabs: ' + opened + '/' + urls.length;

                    if (opened === urls.length) {{
                        document.getElementById('status').innerHTML = '✅ All ' + urls.length + ' tabs opened!<br><br>Now use DownThemAll: Right-click → DownThemAll! → All Tabs';
                    }}
                }}, index * 100); // 100ms delay between tabs
            }});
        }}
    </script>
</head>
<body>
    <h1>📥 Batch Paper Downloader</h1>

    <div class="info">
        <strong>Publisher:</strong> {publisher_name}<br>
        <strong>Papers in batch:</strong> {len(urls)}<br>
        <strong>Batch number:</strong> {start_idx//batch_size + 1}<br>
        <strong>Estimated download size:</strong> ~{len(urls) * 2} MB<br>
        <strong>Estimated time:</strong> 5-15 minutes
    </div>

    <div class="warning">
        <strong>⚠️ Before starting:</strong>
        <ul>
            <li>Close other Firefox windows (save memory)</li>
            <li>Ensure you have enough disk space</li>
            <li>Configure DownThemAll download directory</li>
            <li>Set DownThemAll delay to 3-5 seconds</li>
        </ul>
    </div>

    <button id="openBtn" onclick="openAllTabs()">
        📂 Open All {len(urls)} Tabs
    </button>

    <div id="status" style="margin-top: 20px; font-size: 18px;"></div>

    <div style="margin-top: 40px; border-top: 1px solid #ccc; padding-top: 20px;">
        <h2>📋 Next Steps</h2>
        <ol>
            <li><strong>Click button above</strong> to open all tabs</li>
            <li><strong>Wait 30-60 seconds</strong> for tabs to load and redirect to publishers</li>
            <li><strong>Right-click anywhere</strong> → <strong>DownThemAll!</strong> → <strong>All Tabs</strong></li>
            <li><strong>Filter for PDFs:</strong> Enter <code>*.pdf</code> in filter box</li>
            <li><strong>Select download directory</strong></li>
            <li><strong>Click "Download"</strong></li>
            <li><strong>Monitor progress</strong> in DownThemAll window</li>
            <li><strong>Close all tabs</strong> when done (Ctrl+W repeatedly)</li>
        </ol>
    </div>

    <div style="margin-top: 40px; background: #e7f3fe; padding: 15px; border-left: 4px solid #2196F3;">
        <strong>💡 Tip:</strong> If browser becomes slow, you opened too many tabs.
        Close half and try again with smaller batch size.
    </div>
</body>
</html>"""

    # Save file
    output_file = f"outputs/batch_download_{publisher_name.lower().replace(' ', '_')}_batch{start_idx//batch_size + 1}.html"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"✓ Created: {output_file}")
    print(f"  Papers: {len(urls)}")
    print(f"  Publisher: {publisher_name}")
    return output_file

# Example: Create batches for Frontiers (Open Access)
print("="*80)
print("CREATING DOWNTHEMALL BATCH FILES")
print("="*80)

# Frontiers (343 papers total, create 4 batches of 100)
for i in range(0, 400, 100):
    create_batch_html(
        'outputs/by_publisher/priority1_frontiers.csv',
        'Frontiers',
        batch_size=100,
        start_idx=i
    )

print("\n" + "="*80)
print("Files created! Open in Firefox to start batch downloading.")
print("="*80)
PYEOF
```

---

## Troubleshooting

### Problem: "Too many tabs, browser frozen"
**Solution:**
- Force close Firefox (Ctrl+Alt+Delete → Kill process)
- Restart with smaller batch size (50 instead of 100)
- Close other applications to free RAM

### Problem: "DTA not finding PDFs"
**Solution:**
- Wait longer for tabs to fully load (some publishers slow)
- Check if institutional login required (use proxy URLs)
- Try "All Links" instead of "All Tabs" in DTA
- Some publishers use JavaScript - PDFs may not be detectable

### Problem: "Downloads failing / incomplete PDFs"
**Solution:**
- Increase timeout in DTA settings (60 → 120 seconds)
- Reduce concurrent downloads (20 → 5)
- Increase delay between downloads (2 → 5 seconds)
- Check if IP was rate-limited (wait 1 hour)

### Problem: "Downloaded HTMLpages instead of PDFs"
**Solution:**
- Institutional login required but not provided
- Use proxy URLs or VPN
- Publisher may block direct PDF downloads
- Try DOI redirect instead of direct PDF URLs

---

## Performance Benchmarks

### Expected Throughput

**Open Access (Optimal conditions):**
- Batch size: 100 papers
- Time to open tabs: 1 minute
- Time for DTA scan: 30 seconds
- Download time: 5-10 minutes
- **Total: 6-11 minutes for 100 papers** (9-16 papers/minute)

**Institutional Access (Moderate conditions):**
- Batch size: 50-75 papers
- Time to open tabs: 1 minute
- Time for DTA scan: 30 seconds
- Download time: 10-15 minutes (with delays)
- **Total: 11-16 minutes for 50 papers** (3-4.5 papers/minute)

### Comparison to Manual Download

**Manual (one at a time):**
- Find paper → Click download → Save → Repeat
- Time per paper: 20-60 seconds
- **Rate: 1-3 papers/minute**

**DownThemAll Multi-Tab:**
- Open all tabs → Scan → Download all
- **Rate: 3-16 papers/minute** (3-16x faster)

**Time savings for 9,003 papers:**
- Manual: 50-150 hours
- DTA Multi-Tab: 10-30 hours
- **Savings: 20-140 hours** ⏰

---

## Recommended Workflow

### Session 1: Open Access Blitz (2-3 hours)
1. **Frontiers** (343 papers)
   - 4 batches × 100 papers
   - ~10 min per batch = 40 minutes

2. **PLOS** (217 papers)
   - 3 batches × 75 papers
   - ~8 min per batch = 24 minutes

3. **PeerJ** (81 papers)
   - 1 batch × 81 papers
   - ~8 minutes

**Total: 550-600 papers in 2-3 hours** 🚀

### Session 2-5: Major Publishers (10-15 hours)
- Wiley: 1,542 papers (15 batches × 100)
- Elsevier: 1,604 papers (16 batches × 100)
- Springer: 1,248 papers (12 batches × 100)

---

## File References

**Batch generators:**
- Script above creates HTML batch files
- Save in `outputs/` directory
- Open in dedicated Firefox window

**Priority lists:**
- `outputs/by_publisher/priority1_*.csv` (10 publishers)
- Each can be batched with script above

---

**Ready to start? Run the batch script and open your first HTML file in Firefox!**
