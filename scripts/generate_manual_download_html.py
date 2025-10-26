#!/usr/bin/env python3
"""
generate_manual_download_html.py

Generate HTML files with clickable links for manual PDF downloads.
Groups failures by domain for sequential clicking.

Usage:
    python3 scripts/generate_manual_download_html.py

Output:
    - outputs/manual_downloads_sciencedirect.html
    - outputs/manual_downloads_wiley.html
    - outputs/manual_downloads_peerj.html
    - etc.

Author: Simon Dedman
Date: 2025-10-21
Version: 1.0
"""

import pandas as pd
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).parent.parent
LOG_FILE = BASE_DIR / "logs/pdf_download_log.csv"
DATABASE_PARQUET = BASE_DIR / "outputs/literature_review.parquet"
OUTPUT_DIR = BASE_DIR / "outputs/manual_downloads"

# ============================================================================
# HTML GENERATION
# ============================================================================

def generate_html_for_domain(domain, papers_df, output_file):
    """
    Generate HTML file with clickable links for manual download.

    Args:
        domain: Domain name (e.g., 'sciencedirect.com')
        papers_df: DataFrame with columns: literature_id, url, title, authors, year
        output_file: Path to output HTML file
    """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Manual PDF Downloads - {domain}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        .stats {{
            background: #fff;
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .paper {{
            background: white;
            padding: 15px;
            margin: 10px 0;
            border-radius: 8px;
            border-left: 4px solid #3498db;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .paper:hover {{
            transform: translateX(5px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }}
        .paper-number {{
            display: inline-block;
            background: #3498db;
            color: white;
            padding: 4px 12px;
            border-radius: 4px;
            font-weight: bold;
            margin-right: 10px;
        }}
        .paper-id {{
            color: #7f8c8d;
            font-size: 0.9em;
            margin-left: 10px;
        }}
        .title {{
            font-weight: bold;
            color: #2c3e50;
            margin: 8px 0;
        }}
        .authors {{
            color: #34495e;
            font-size: 0.95em;
            margin: 5px 0;
        }}
        .year {{
            color: #7f8c8d;
            font-size: 0.9em;
        }}
        .url-link {{
            display: inline-block;
            background: #27ae60;
            color: white;
            padding: 8px 16px;
            text-decoration: none;
            border-radius: 4px;
            margin-top: 10px;
            font-weight: bold;
            transition: background 0.2s;
        }}
        .url-link:hover {{
            background: #229954;
        }}
        .instructions {{
            background: #fff3cd;
            border: 1px solid #ffc107;
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0;
        }}
        .instructions h3 {{
            margin-top: 0;
            color: #856404;
        }}
        .instructions ol {{
            margin: 10px 0;
            padding-left: 25px;
        }}
        .instructions li {{
            margin: 5px 0;
        }}
        .progress {{
            margin: 20px 0;
            font-weight: bold;
            color: #27ae60;
        }}
    </style>
</head>
<body>
    <h1>📄 Manual PDF Downloads: {domain}</h1>

    <div class="stats">
        <strong>Total papers:</strong> {len(papers_df)}<br>
        <strong>Domain:</strong> {domain}<br>
        <strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    </div>

    <div class="instructions">
        <h3>📋 Instructions</h3>
        <ol>
            <li><strong>Make sure you're logged in</strong> to your institutional access (VPN or library portal)</li>
            <li><strong>Open the monitoring script</strong> in a terminal:
                <pre>python3 scripts/monitor_firefox_pdfs.py</pre>
            </li>
            <li><strong>Click each "Download PDF" link below</strong> - the PDF should open in Firefox</li>
            <li><strong>Wait ~2 seconds</strong> for each PDF to fully load (you'll see the PDF content)</li>
            <li><strong>Close the tab</strong> (Ctrl+W) and move to the next link</li>
            <li>The monitoring script will automatically extract and rename the PDFs</li>
            <li>Every 25 papers, take a short break to let the cache settle</li>
        </ol>
        <p><strong>💡 Tip:</strong> Middle-click (or Ctrl+click) to open in a new tab, then close when loaded.</p>
    </div>

    <div class="progress" id="progress">
        Progress: <span id="count">0</span> / {len(papers_df)} papers clicked
    </div>

    <div id="papers">
"""

    # Add each paper
    for idx, row in papers_df.iterrows():
        html += f"""
    <div class="paper" id="paper-{row['literature_id']}">
        <span class="paper-number">{idx + 1}</span>
        <span class="paper-id">ID: {row['literature_id']}</span>
        <div class="title">{row['title']}</div>
        <div class="authors">{row['authors']}</div>
        <div class="year">Year: {row['year']}</div>
        <a href="{row['url']}" class="url-link" target="_blank" onclick="markClicked({row['literature_id']})">
            📥 Download PDF
        </a>
    </div>
"""

    html += """
    </div>

    <script>
        let clickedCount = 0;
        let clicked = new Set();

        // Load progress from localStorage
        if (localStorage.getItem('clicked')) {
            clicked = new Set(JSON.parse(localStorage.getItem('clicked')));
            clickedCount = clicked.size;
            document.getElementById('count').textContent = clickedCount;

            // Mark already clicked papers
            clicked.forEach(id => {
                const paper = document.getElementById('paper-' + id);
                if (paper) {
                    paper.style.opacity = '0.5';
                    paper.style.borderLeftColor = '#95a5a6';
                }
            });
        }

        function markClicked(id) {
            if (!clicked.has(id)) {
                clicked.add(id);
                clickedCount++;
                document.getElementById('count').textContent = clickedCount;

                // Save to localStorage
                localStorage.setItem('clicked', JSON.stringify([...clicked]));

                // Visual feedback
                const paper = document.getElementById('paper-' + id);
                paper.style.opacity = '0.5';
                paper.style.borderLeftColor = '#95a5a6';
            }
        }

        // Reset button (optional)
        document.addEventListener('keydown', function(e) {
            if (e.ctrlKey && e.key === 'r') {
                if (confirm('Reset progress?')) {
                    localStorage.removeItem('clicked');
                    location.reload();
                }
            }
        });
    </script>
</body>
</html>
"""

    # Write file
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"✅ Generated: {output_file.name} ({len(papers_df)} papers)")

def main():
    """Generate HTML files for manual downloads, grouped by domain."""

    print("=" * 80)
    print("MANUAL DOWNLOAD HTML GENERATOR")
    print("=" * 80)

    # Load download log
    if not LOG_FILE.exists():
        print(f"❌ Download log not found: {LOG_FILE}")
        return

    log_df = pd.read_csv(LOG_FILE)
    print(f"\n📂 Loaded download log: {len(log_df)} entries")

    # Filter to error status (HTML instead of PDF)
    error_df = log_df[log_df['status'] == 'error'].copy()
    print(f"📋 Papers with 'error' status: {len(error_df)}")

    # Load database for metadata
    db_df = pd.read_parquet(DATABASE_PARQUET)

    # Merge to get full metadata
    error_df['literature_id'] = pd.to_numeric(error_df['literature_id'], errors='coerce').astype('Int64')
    db_df['literature_id'] = pd.to_numeric(db_df['literature_id'], errors='coerce').astype('Int64')

    # Drop any existing metadata columns from log to avoid conflicts
    cols_to_drop = [col for col in ['authors', 'title', 'year', 'pdf_url'] if col in error_df.columns]
    if cols_to_drop:
        error_df = error_df.drop(columns=cols_to_drop)

    merged_df = error_df.merge(
        db_df[['literature_id', 'authors', 'title', 'year', 'pdf_url']],
        on='literature_id',
        how='left'
    )

    # Extract domain from URL
    merged_df['domain'] = merged_df['url'].apply(
        lambda x: urlparse(x).netloc if pd.notna(x) else 'unknown'
    )

    # Group by domain
    domains = merged_df['domain'].value_counts()

    print(f"\n📊 Failures by domain:")
    for domain, count in domains.head(10).items():
        print(f"   • {domain}: {count} papers")

    # Generate HTML for top domains
    print(f"\n📝 Generating HTML files...")

    for domain in domains.head(10).index:
        domain_df = merged_df[merged_df['domain'] == domain].copy()

        # Sort by year (newest first) then by ID
        domain_df = domain_df.sort_values(['year', 'literature_id'], ascending=[False, True])

        # Clean domain name for filename
        safe_domain = domain.replace('.', '_').replace('www_', '')
        output_file = OUTPUT_DIR / f"manual_downloads_{safe_domain}.html"

        # Select relevant columns
        papers_for_html = domain_df[['literature_id', 'url', 'title', 'authors', 'year']].copy()

        generate_html_for_domain(domain, papers_for_html, output_file)

    print(f"\n✅ HTML files generated in: {OUTPUT_DIR}")
    print(f"\n📋 Next steps:")
    print(f"1. Open the monitoring script:")
    print(f"   python3 scripts/monitor_firefox_pdfs.py")
    print(f"2. Open an HTML file in Firefox:")
    print(f"   firefox {OUTPUT_DIR}/manual_downloads_sciencedirect_com.html")
    print(f"3. Click through the links!")
    print("=" * 80)

if __name__ == "__main__":
    main()
