#!/usr/bin/env python3
"""
Create DownThemAll batch HTML files for multi-tab PDF downloading

This script generates HTML files that open multiple paper DOI URLs in tabs,
which can then be batch-downloaded using the DownThemAll Firefox extension.

Usage:
    python create_downthemall_batches.py --publisher frontiers --batch-size 100
    python create_downthemall_batches.py --input custom_list.csv --name "Custom Batch"
"""

import pandas as pd
import json
import argparse
from pathlib import Path


def create_batch_html(df, publisher_name, batch_size, start_idx, output_dir):
    """
    Create HTML file that opens N tabs for DownThemAll batch downloading

    Args:
        df: DataFrame with papers (must have 'doi_clean' column)
        publisher_name: Name of publisher (for title)
        batch_size: Number of papers per batch
        start_idx: Starting index (for multiple batches)
        output_dir: Directory to save HTML files
    """

    # Get batch of papers
    batch = df.iloc[start_idx:start_idx + batch_size]

    if len(batch) == 0:
        return None

    # Generate URLs (DOI redirect)
    urls = [f"https://doi.org/{doi}" for doi in batch['doi_clean'] if pd.notna(doi)]

    if len(urls) == 0:
        print(f"  ⚠️  No valid DOIs in batch {start_idx//batch_size + 1}, skipping")
        return None

    batch_num = start_idx // batch_size + 1

    # Create HTML
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{publisher_name} Batch {batch_num}</title>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 900px;
            margin: 50px auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{ color: #333; }}
        button {{
            font-size: 20px;
            padding: 15px 30px;
            background: #4CAF50;
            color: white;
            border: none;
            cursor: pointer;
            border-radius: 5px;
            font-weight: bold;
        }}
        button:hover {{ background: #45a049; }}
        button:disabled {{ background: #cccccc; cursor: not-allowed; }}
        .info {{
            background: #e7f3fe;
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
            border-left: 4px solid #2196F3;
        }}
        .warning {{
            background: #fff3cd;
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
            border-left: 4px solid #ff9800;
        }}
        .success {{
            background: #d4edda;
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
            border-left: 4px solid #28a745;
        }}
        #status {{
            margin-top: 20px;
            font-size: 18px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 5px;
            min-height: 30px;
        }}
        ol {{ line-height: 1.8; }}
        code {{
            background: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: monospace;
        }}
        .next-steps {{
            margin-top: 40px;
            border-top: 2px solid #eee;
            padding-top: 20px;
        }}
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

            const statusDiv = document.getElementById('status');
            const openBtn = document.getElementById('openBtn');

            statusDiv.innerHTML = '<strong>Opening tabs:</strong> 0/' + urls.length + ' <em>(please wait...)</em>';
            openBtn.disabled = true;

            let opened = 0;
            urls.forEach((url, index) => {{
                setTimeout(() => {{
                    try {{
                        window.open(url, '_blank');
                        opened++;
                        statusDiv.innerHTML = '<strong>Opening tabs:</strong> ' + opened + '/' + urls.length;

                        if (opened === urls.length) {{
                            statusDiv.innerHTML = '<div class="success"><strong>✅ All ' + urls.length + ' tabs opened!</strong><br><br>' +
                                'Now use DownThemAll:<br>' +
                                '1. Right-click anywhere → <strong>DownThemAll!</strong> → <strong>All Tabs</strong><br>' +
                                '2. Filter for PDFs: Enter <code>*.pdf</code> in filter box<br>' +
                                '3. Select download directory<br>' +
                                '4. Click "Download"</div>';
                        }}
                    }} catch (e) {{
                        console.error('Failed to open tab:', url, e);
                    }}
                }}, index * 100); // 100ms delay between tabs
            }});
        }}
    </script>
</head>
<body>
    <div class="container">
        <h1>📥 DownThemAll Batch Downloader</h1>

        <div class="info">
            <strong>Publisher:</strong> {publisher_name}<br>
            <strong>Papers in batch:</strong> {len(urls)}<br>
            <strong>Batch number:</strong> {batch_num}<br>
            <strong>Estimated download size:</strong> ~{len(urls) * 2} MB<br>
            <strong>Estimated time:</strong> 5-15 minutes
        </div>

        <div class="warning">
            <strong>⚠️ Before starting:</strong>
            <ul>
                <li><strong>Install DownThemAll:</strong> <a href="https://www.downthemall.net/" target="_blank">www.downthemall.net</a></li>
                <li>Close other Firefox windows to save memory</li>
                <li>Ensure you have enough disk space (~{len(urls) * 2} MB)</li>
                <li>Configure DownThemAll download directory first</li>
                <li>Set DownThemAll delay to 3-5 seconds (for rate limiting)</li>
            </ul>
        </div>

        <button id="openBtn" onclick="openAllTabs()">
            📂 Open All {len(urls)} Tabs
        </button>

        <div id="status"></div>

        <div class="next-steps">
            <h2>📋 Step-by-Step Instructions</h2>
            <ol>
                <li><strong>Click button above</strong> to open all {len(urls)} tabs</li>
                <li><strong>Wait 30-60 seconds</strong> for tabs to load and redirect to publisher sites</li>
                <li><strong>Right-click anywhere</strong> in Firefox → <strong>DownThemAll!</strong> → <strong>All Tabs</strong></li>
                <li><strong>Filter for PDFs:</strong> Enter <code>*.pdf</code> in the filter box</li>
                <li><strong>Review list:</strong> Uncheck any non-PDF files</li>
                <li><strong>Select download directory:</strong> Choose where to save PDFs</li>
                <li><strong>Configure settings:</strong>
                    <ul>
                        <li>Max concurrent downloads: 10-15</li>
                        <li>Delay between downloads: 3-5 seconds</li>
                    </ul>
                </li>
                <li><strong>Click "Download"</strong> to start batch download</li>
                <li><strong>Monitor progress</strong> in DownThemAll window</li>
                <li><strong>Close all tabs</strong> when done (Ctrl+W repeatedly, or close window)</li>
            </ol>
        </div>

        <div class="warning">
            <strong>💡 Tips:</strong>
            <ul>
                <li>If browser becomes slow, you opened too many tabs. Close half and try smaller batch.</li>
                <li>Some publishers require institutional login - use VPN if needed</li>
                <li>If downloads fail, check DTA settings (timeout, retry attempts)</li>
                <li>PDFs will be named by publisher - you can rename later using literature IDs</li>
            </ul>
        </div>

        <div class="info">
            <strong>🔧 Troubleshooting:</strong><br>
            <strong>PDFs not found?</strong> Wait longer for tabs to load, or try DOI resolver<br>
            <strong>Downloads failing?</strong> Increase timeout in DTA settings (60→120 sec)<br>
            <strong>HTML pages instead of PDFs?</strong> Check institutional access/VPN<br>
            <strong>Rate limited?</strong> Increase delay between downloads (3→10 sec)
        </div>
    </div>
</body>
</html>"""

    # Save file
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    filename = f"batch_{publisher_name.lower().replace(' ', '_')}_batch{batch_num}_{len(urls)}papers.html"
    output_file = output_path / filename

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"  ✓ Batch {batch_num}: {len(urls)} papers → {output_file}")
    return str(output_file)


def generate_batches_for_publisher(publisher_csv, publisher_name, batch_size, output_dir, max_batches=None):
    """Generate multiple batch HTML files for a publisher"""

    print(f"\n{'='*80}")
    print(f"Creating batches for: {publisher_name}")
    print(f"{'='*80}")

    # Load papers
    df = pd.read_csv(publisher_csv)
    total_papers = len(df)
    print(f"Total papers: {total_papers}")
    print(f"Batch size: {batch_size}")

    # Calculate number of batches
    num_batches = (total_papers + batch_size - 1) // batch_size
    if max_batches:
        num_batches = min(num_batches, max_batches)
    print(f"Creating {num_batches} batches...\n")

    # Create batches
    created_files = []
    for i in range(num_batches):
        start_idx = i * batch_size
        output_file = create_batch_html(df, publisher_name, batch_size, start_idx, output_dir)
        if output_file:
            created_files.append(output_file)

    print(f"\n✅ Created {len(created_files)} batch files for {publisher_name}")
    return created_files


def main():
    parser = argparse.ArgumentParser(
        description='Create DownThemAll batch HTML files for PDF downloading'
    )
    parser.add_argument(
        '--publisher',
        choices=['frontiers', 'plos', 'peerj', 'elsevier', 'wiley', 'springer',
                 'taylor', 'inter-research', 'oxford', 'cambridge', 'all'],
        help='Publisher to create batches for (or "all" for predefined list)'
    )
    parser.add_argument(
        '--input',
        help='Custom CSV file (must have doi_clean column)'
    )
    parser.add_argument(
        '--name',
        help='Name for custom batch (used if --input provided)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=100,
        help='Number of papers per batch (default: 100)'
    )
    parser.add_argument(
        '--max-batches',
        type=int,
        help='Maximum number of batches to create (useful for testing)'
    )
    parser.add_argument(
        '--output-dir',
        default='outputs/downthemall_batches',
        help='Directory to save HTML files (default: outputs/downthemall_batches)'
    )

    args = parser.parse_args()

    # Publisher mappings
    publisher_files = {
        'frontiers': ('outputs/by_publisher/priority1_frontiers.csv', 'Frontiers'),
        'plos': ('outputs/by_publisher/priority1_plos.csv', 'PLOS'),
        'peerj': ('outputs/by_publisher/priority1_peerj.csv', 'PeerJ'),
        'elsevier': ('outputs/by_publisher/priority1_elsevier.csv', 'Elsevier'),
        'wiley': ('outputs/by_publisher/priority1_wiley.csv', 'Wiley'),
        'springer': ('outputs/by_publisher/priority1_springer_nature.csv', 'Springer Nature'),
        'taylor': ('outputs/by_publisher/priority1_taylor_&_francis.csv', 'Taylor & Francis'),
        'inter-research': ('outputs/by_publisher/priority1_inter-research.csv', 'Inter-Research'),
        'oxford': ('outputs/by_publisher/priority1_oxford_university_press.csv', 'Oxford University Press'),
        'cambridge': ('outputs/by_publisher/priority1_cambridge_university_press.csv', 'Cambridge University Press'),
    }

    all_files = []

    if args.input:
        # Custom input file
        if not args.name:
            args.name = Path(args.input).stem
        all_files = generate_batches_for_publisher(
            args.input, args.name, args.batch_size, args.output_dir, args.max_batches
        )

    elif args.publisher == 'all':
        # Generate for all predefined publishers
        print("\n" + "="*80)
        print("CREATING BATCHES FOR ALL PUBLISHERS")
        print("="*80)

        for pub_key, (csv_file, pub_name) in publisher_files.items():
            if Path(csv_file).exists():
                files = generate_batches_for_publisher(
                    csv_file, pub_name, args.batch_size, args.output_dir, args.max_batches
                )
                all_files.extend(files)
            else:
                print(f"\n⚠️  File not found: {csv_file}, skipping {pub_name}")

    elif args.publisher:
        # Single publisher
        csv_file, pub_name = publisher_files[args.publisher]
        if Path(csv_file).exists():
            all_files = generate_batches_for_publisher(
                csv_file, pub_name, args.batch_size, args.output_dir, args.max_batches
            )
        else:
            print(f"❌ Error: File not found: {csv_file}")
            return 1

    else:
        parser.print_help()
        return 1

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Total batch files created: {len(all_files)}")
    print(f"Output directory: {args.output_dir}")
    print(f"\nNext steps:")
    print(f"1. Open any HTML file in Firefox")
    print(f"2. Click 'Open All Tabs' button")
    print(f"3. Use DownThemAll to batch download PDFs")
    print("="*80)

    return 0


if __name__ == '__main__':
    exit(main())
