# Firefox Cookie Export Guide

## Method 1: cookies.txt Extension (Recommended)

Try this specific extension:
- **Name**: "cookies.txt"
- **Developer**: Lennon Hill
- **URL**: https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/

After installing:
1. Visit ScienceDirect (any page while logged in)
2. Click the extension icon (should appear in toolbar)
3. Click "Current Site" or "All Cookies"
4. Cookies will be copied to clipboard in Netscape format
5. Paste into a text file and save as `cookies.txt`

## Method 2: Export Cookies Extension

Alternative extension:
- **Name**: "Export Cookies"
- **URL**: https://addons.mozilla.org/en-US/firefox/addon/export-cookies-txt/

## Method 3: Python Script to Extract from Firefox Database

Firefox stores cookies in a SQLite database. We can extract them:

```python
#!/usr/bin/env python3
"""
extract_firefox_cookies.py
Extract cookies from Firefox profile and save in Netscape format
"""

import sqlite3
import os
from pathlib import Path

# Find Firefox profile directory
firefox_dir = Path.home() / ".mozilla/firefox"
profiles = list(firefox_dir.glob("*.default-release"))

if not profiles:
    profiles = list(firefox_dir.glob("*.default"))

if not profiles:
    print("Firefox profile not found!")
    exit(1)

profile = profiles[0]
cookies_db = profile / "cookies.sqlite"

if not cookies_db.exists():
    print(f"Cookies database not found: {cookies_db}")
    exit(1)

# Copy database (Firefox locks it while running)
import shutil
temp_db = "/tmp/firefox_cookies_temp.sqlite"
shutil.copy2(cookies_db, temp_db)

# Extract cookies
conn = sqlite3.connect(temp_db)
cursor = conn.cursor()

# Get cookies for key domains
domains = ['sciencedirect.com', 'elsevier.com', 'wiley.com', 'peerj.com']

with open('cookies.txt', 'w') as f:
    f.write("# Netscape HTTP Cookie File\n")

    for domain in domains:
        cursor.execute("""
            SELECT host,
                   CASE WHEN host LIKE '.%' THEN 'TRUE' ELSE 'FALSE' END,
                   path,
                   CASE WHEN isSecure = 1 THEN 'TRUE' ELSE 'FALSE' END,
                   expiry,
                   name,
                   value
            FROM moz_cookies
            WHERE host LIKE ?
        """, (f'%{domain}%',))

        for row in cursor.fetchall():
            f.write('\t'.join(str(x) for x in row) + '\n')

conn.close()
os.remove(temp_db)

print("✅ Cookies exported to cookies.txt")
print("Run: python3 scripts/retry_failed_downloads.py --status error --domain sciencedirect --cookies cookies.txt")
```

Save this as `scripts/extract_firefox_cookies.py` and run:
```bash
python3 scripts/extract_firefox_cookies.py
```

**Note**: Firefox must be closed when running this script, or you'll need to close and reopen it first.

## Method 4: Manual Cookie Entry

For testing, you can manually create a cookies.txt file with just the authentication cookie:

1. Open Firefox Developer Tools (F12)
2. Go to Storage tab → Cookies
3. Find ScienceDirect cookies (especially session cookies)
4. Create `cookies.txt` with format:
```
# Netscape HTTP Cookie File
.sciencedirect.com	TRUE	/	TRUE	0	COOKIE_NAME	COOKIE_VALUE
```

## Testing

After exporting cookies, test with a small sample:
```bash
python3 scripts/retry_failed_downloads.py \
    --status error \
    --domain sciencedirect \
    --cookies cookies.txt \
    --max-papers 5
```

If successful (downloads PDFs instead of HTML), run full retry:
```bash
python3 scripts/retry_failed_downloads.py \
    --status error \
    --domain sciencedirect \
    --cookies cookies.txt
```
