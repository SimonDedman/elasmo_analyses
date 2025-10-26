#!/usr/bin/env python3
"""
organize_by_sequential_position.py

Match PDFs by sequential position in manual download HTML lists.
scielo_document1.pdf = position 1 in HTML, scielo_document2.pdf = position 2, etc.

Usage:
    python3 scripts/organize_by_sequential_position.py

Author: Simon Dedman
Date: 2025-10-22
"""

import pandas as pd
import re
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
import shutil

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path("/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel")
DATABASE_PARQUET = BASE_DIR / "outputs/literature_review.parquet"
OUTPUT_DIR = Path("/home/simon/Documents/Si Work/Papers & Books/SharkPapers")
MANUAL_DOWNLOADS_DIR = BASE_DIR / "outputs/manual_downloads"

HTML_FILES = {
    'scielo': MANUAL_DOWNLOADS_DIR / "manual_downloads_scielo_br.html",
    'ncbi': MANUAL_DOWNLOADS_DIR / "manual_downloads_ncbi_nlm_nih_gov.html",
    'peerj': MANUAL_DOWNLOADS_DIR / "manual_downloads_peerj_com.html"
}

LOG_FILE = BASE_DIR / "logs/sequential_organization_log.csv"

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def safe_filename(text, max_length=100):
    """Convert text to safe filename."""
    safe = re.sub(r'[<>:"/\\|?*]', '', text)
    safe = re.sub(r'\s+', '.', safe.strip())
    safe = re.sub(r'\.+', '.', safe)

    if len(safe) > max_length:
        safe = safe[:max_length]

    return safe


def extract_first_author(authors_str):
    """Extract first author surname from authors string."""
    if pd.isna(authors_str) or not authors_str:
        return "Unknown"

    first_author = authors_str.split('&')[0].split(';')[0].strip()
    parts = re.split(r'[,\(]', first_author)
    surname = parts[0].strip()

    return safe_filename(surname, max_length=20)


def parse_html_papers(html_path):
    """Parse manual download HTML and return ordered list of papers."""
    with open(html_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')

    papers = []
    paper_divs = soup.find_all('div', class_='paper')

    for paper_div in paper_divs:
        # Extract literature_id from id attribute
        paper_id = paper_div.get('id', '')
        lit_id = paper_id.replace('paper-', '') if paper_id else None

        # Extract metadata
        title_elem = paper_div.find('div', class_='title')
        authors_elem = paper_div.find('div', class_='authors')
        year_elem = paper_div.find('div', class_='year')
        doi_elem = paper_div.find('div', class_='doi')
        pdf_elem = paper_div.find('a', class_='pdf-link')

        paper = {
            'literature_id': str(lit_id) if lit_id else None,
            'title': title_elem.text.strip() if title_elem else None,
            'authors': authors_elem.text.strip() if authors_elem else None,
            'year': int(year_elem.text.strip().replace('Year:', '').strip()) if year_elem and year_elem.text.strip() else None,
            'doi': doi_elem.text.strip() if doi_elem else None,
            'pdf_url': pdf_elem.get('href', '') if pdf_elem else None
        }

        papers.append(paper)

    return papers


def get_pdf_position_number(filename, source):
    """Extract position number from PDF filename."""
    if source == 'scielo':
        # scielo_document1.pdf -> 1
        match = re.search(r'scielo_document(\d+)\.pdf', filename, re.IGNORECASE)
        if match:
            return int(match.group(1))

    elif source == 'ncbi':
        # Various NCBI patterns - need to identify
        # For now, check if filename contains ncbi
        if 'ncbi' in filename.lower():
            # Try to extract number from various patterns
            match = re.search(r'_(\d+)\.pdf$', filename)
            if match:
                return int(match.group(1))

    elif source == 'peerj':
        # PeerJ_peerj-2041.pdf or similar
        if 'peerj' in filename.lower():
            match = re.search(r'peerj-(\d+)', filename, re.IGNORECASE)
            if match:
                return int(match.group(1))

    return None


def create_proper_filename(authors, year, title):
    """Create proper filename format."""
    first_author = extract_first_author(authors)
    safe_title = safe_filename(title, max_length=80)

    if not year or pd.isna(year):
        year = "unknown"

    filename = f"{first_author}.etal.{year}.{safe_title}.pdf"
    return filename


def organize_pdf(pdf_path, paper_metadata, output_dir, dry_run=False):
    """Organize PDF to proper location with proper name."""
    try:
        # Create filename
        filename = create_proper_filename(
            paper_metadata['authors'],
            paper_metadata['year'],
            paper_metadata['title']
        )

        # Determine year folder
        year = paper_metadata['year']
        if not year or pd.isna(year):
            year_dir = output_dir / "unknown_year"
        else:
            year_dir = output_dir / str(int(year))

        new_path = year_dir / filename

        # Check if already exists
        if new_path.exists():
            return (False, new_path, "Already exists")

        if not dry_run:
            # Create directory
            year_dir.mkdir(parents=True, exist_ok=True)

            # Move file
            shutil.move(str(pdf_path), str(new_path))

        return (True, new_path, "Moved successfully")

    except Exception as e:
        return (False, None, f"Error: {e}")


# ============================================================================
# MAIN SCRIPT
# ============================================================================

def main():
    print("=" * 80)
    print("SEQUENTIAL POSITION PDF ORGANIZER")
    print("=" * 80)

    # Load database
    print("\n📖 Loading database...")
    db = pd.read_parquet(DATABASE_PARQUET)
    print(f"✅ Loaded {len(db):,} papers")

    # Track results
    results = []
    total_organized = 0

    # Process each source
    for source_name, html_path in HTML_FILES.items():
        print(f"\n{'='*80}")
        print(f"Processing {source_name.upper()} PDFs")
        print(f"{'='*80}")

        # Parse HTML to get ordered list
        print(f"📄 Parsing {html_path.name}...")
        papers = parse_html_papers(html_path)
        print(f"✅ Found {len(papers)} papers in HTML list")

        # Find matching PDFs in unknown_year folder
        unknown_dir = OUTPUT_DIR / "unknown_year"
        if not unknown_dir.exists():
            print(f"⚠️  Directory not found: {unknown_dir}")
            continue

        # Get PDFs for this source
        all_pdfs = list(unknown_dir.glob("*.pdf"))
        source_pdfs = []

        for pdf_path in all_pdfs:
            if source_name == 'scielo' and 'scielo_document' in pdf_path.name.lower():
                source_pdfs.append(pdf_path)
            elif source_name == 'ncbi' and 'ncbi' in pdf_path.name.lower():
                source_pdfs.append(pdf_path)
            elif source_name == 'peerj' and 'peerj' in pdf_path.name.lower():
                source_pdfs.append(pdf_path)

        print(f"📁 Found {len(source_pdfs)} {source_name} PDFs")

        # Match each PDF by position
        for pdf_path in source_pdfs:
            position = get_pdf_position_number(pdf_path.name, source_name)

            if position is None:
                print(f"⚠️  Could not extract position from: {pdf_path.name}")
                results.append({
                    'original_path': str(pdf_path),
                    'source': source_name,
                    'position': None,
                    'status': 'failed',
                    'message': 'Could not extract position number',
                    'timestamp': datetime.now().isoformat()
                })
                continue

            # Get paper at this position (1-indexed)
            if position < 1 or position > len(papers):
                print(f"⚠️  Position {position} out of range for {pdf_path.name}")
                results.append({
                    'original_path': str(pdf_path),
                    'source': source_name,
                    'position': position,
                    'status': 'failed',
                    'message': f'Position {position} out of range (max {len(papers)})',
                    'timestamp': datetime.now().isoformat()
                })
                continue

            paper_metadata = papers[position - 1]  # Convert to 0-indexed

            # Update database with year information if needed
            lit_id = paper_metadata['literature_id']
            if lit_id:
                db_match = db[db['literature_id'] == lit_id]
                if len(db_match) > 0 and pd.isna(db_match.iloc[0]['year']):
                    db.loc[db_match.index[0], 'year'] = paper_metadata['year']

            # Organize PDF
            success, new_path, message = organize_pdf(
                pdf_path,
                paper_metadata,
                OUTPUT_DIR,
                dry_run=False
            )

            if success:
                total_organized += 1
                print(f"✅ {pdf_path.name} → {new_path.parent.name}/{new_path.name}")
            else:
                print(f"❌ {pdf_path.name}: {message}")

            results.append({
                'original_path': str(pdf_path),
                'new_path': str(new_path) if new_path else None,
                'source': source_name,
                'position': position,
                'literature_id': paper_metadata['literature_id'],
                'title': paper_metadata['title'],
                'authors': paper_metadata['authors'],
                'year': paper_metadata['year'],
                'status': 'organized' if success else 'failed',
                'message': message,
                'timestamp': datetime.now().isoformat()
            })

    # Save updated database
    print(f"\n💾 Saving updated database...")
    db.to_parquet(DATABASE_PARQUET, index=False)
    print(f"✅ Database updated")

    # Save log
    results_df = pd.DataFrame(results)
    results_df.to_csv(LOG_FILE, index=False)
    print(f"✅ Log saved: {LOG_FILE}")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"✅ Total PDFs organized: {total_organized}/{len(results)}")
    print(f"📊 By source:")
    for source in ['scielo', 'ncbi', 'peerj']:
        source_results = results_df[results_df['source'] == source]
        organized = len(source_results[source_results['status'] == 'organized'])
        print(f"   • {source}: {organized}/{len(source_results)}")
    print("=" * 80)


if __name__ == "__main__":
    main()
