#!/usr/bin/env python3
"""
Crawl Shark-References bibliography (A-Z) for papers with PDF download links.
Cross-reference against our remaining papers list to find available PDFs.

Rate limiting: 10-second delays between requests as per project rules.

HTML Structure:
<div class="list-entry">
  <div class="list-images">
    <img data-ajax="/literature/detailAjax/{lit_id}" src="/images/information.png"/>
    <a href="{pdf_url}"><img src="/images/download.png"/></a>  <!-- optional -->
  </div>
  <div class="list-text">
    <span class="lit-authors">Author (Year)</span>
    Title text...
    <span class="lit-findspot">Journal info</span>
    DOI: <a href="...">10.xxxx/...</a>
  </div>
</div>
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
from pathlib import Path
from datetime import datetime

# Project paths
PROJECT_ROOT = Path("/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel")
REMAINING_CSV = PROJECT_ROOT / "outputs/remaining_downloads_for_web.csv"
OUTPUT_DIR = PROJECT_ROOT / "outputs"

# Shark-References base URL
BASE_URL = "https://shark-references.com/literature/listAll/{letter}"

# Headers to mimic browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}


def fetch_letter_page(letter: str) -> str:
    """Fetch a single letter page from Shark-References."""
    url = BASE_URL.format(letter=letter)
    response = requests.get(url, headers=HEADERS, timeout=60)
    response.raise_for_status()
    return response.text


def extract_papers_with_pdfs(html: str) -> list[dict]:
    """
    Parse HTML to extract papers that have download links.
    Returns list of dicts with: literature_id, authors, year, title, doi, pdf_url
    """
    soup = BeautifulSoup(html, 'html.parser')
    papers_with_pdfs = []

    # Find all list entries
    entries = soup.find_all('div', class_='list-entry')

    for entry in entries:
        # Check if this entry has a download link
        images_div = entry.find('div', class_='list-images')
        if not images_div:
            continue

        download_link = images_div.find('a', href=True)
        download_img = None
        if download_link:
            download_img = download_link.find('img', src=lambda x: x and 'download' in x.lower() if x else False)

        if not download_img:
            continue  # No download available for this entry

        pdf_url = download_link.get('href', '')

        # Get literature_id from the info image's data-ajax attribute
        info_img = images_div.find('img', attrs={'data-ajax': True})
        lit_id = None
        if info_img:
            ajax_url = info_img.get('data-ajax', '')
            lit_id_match = re.search(r'/literature/detailAjax/(\d+)', ajax_url)
            if lit_id_match:
                lit_id = int(lit_id_match.group(1))

        # Get text content
        text_div = entry.find('div', class_='list-text')
        if not text_div:
            continue

        # Extract authors and year
        authors_span = text_div.find('span', class_='lit-authors')
        authors = None
        year = None
        if authors_span:
            authors_text = authors_span.get_text(strip=True)
            authors = authors_text
            year_match = re.search(r'\((\d{4})\)', authors_text)
            if year_match:
                year = int(year_match.group(1))

        # Extract DOI
        full_text = text_div.get_text(' ', strip=True)
        doi_match = re.search(r'10\.\d{4,}/[^\s<>"]+', full_text)
        doi = doi_match.group(0).rstrip('.,;)') if doi_match else None

        # Get title (text between authors and journal info)
        title = None
        findspot = text_div.find('span', class_='lit-findspot')
        if authors_span and findspot:
            # Get all text content and try to extract title
            all_text = text_div.get_text(' ', strip=True)
            # Title is typically between the authors line and the findspot
            title = all_text

        papers_with_pdfs.append({
            'literature_id': lit_id,
            'authors': authors,
            'year': year,
            'doi': doi,
            'pdf_url': pdf_url,
        })

    return papers_with_pdfs


def crawl_all_letters(delay: int = 10) -> list[dict]:
    """Crawl all letters A-Z with rate limiting."""
    all_papers = []
    letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

    for i, letter in enumerate(letters):
        print(f"[{i+1}/26] Processing letter {letter}...", end=' ', flush=True)

        try:
            html = fetch_letter_page(letter)
            papers = extract_papers_with_pdfs(html)
            print(f"Found {len(papers)} papers with PDFs")
            all_papers.extend(papers)

            # Save intermediate results
            if all_papers:
                interim_df = pd.DataFrame(all_papers)
                interim_df.to_csv(OUTPUT_DIR / "shark_refs_pdfs_interim.csv", index=False)

        except Exception as e:
            print(f"ERROR: {e}")

        # Rate limiting (skip delay after last letter)
        if i < len(letters) - 1:
            time.sleep(delay)

    return all_papers


def cross_reference_remaining(shark_refs_pdfs: list[dict], remaining_df: pd.DataFrame) -> pd.DataFrame:
    """
    Cross-reference Shark-References PDFs against our remaining papers.
    Match by: literature_id first, then DOI.
    """
    sr_df = pd.DataFrame(shark_refs_pdfs)

    if sr_df.empty:
        return pd.DataFrame()

    matches = []

    for _, row in remaining_df.iterrows():
        match = None
        match_type = None
        pdf_url = None

        # Try matching by literature_id first
        our_lit_id = row.get('literature_id')
        if pd.notna(our_lit_id):
            lit_match = sr_df[sr_df['literature_id'] == int(our_lit_id)]
            if len(lit_match) > 0:
                match = lit_match.iloc[0]
                match_type = 'literature_id'
                pdf_url = match['pdf_url']

        # Try matching by DOI if no lit_id match
        if match is None:
            our_doi = row.get('doi')
            if pd.notna(our_doi) and our_doi:
                doi_clean = str(our_doi).lower().strip()
                sr_df['doi_clean'] = sr_df['doi'].fillna('').astype(str).str.lower().str.strip()
                doi_matches = sr_df[sr_df['doi_clean'] == doi_clean]
                if len(doi_matches) > 0:
                    match = doi_matches.iloc[0]
                    match_type = 'doi'
                    pdf_url = match['pdf_url']

        if match is not None:
            matches.append({
                'our_id': row.get('id'),
                'literature_id': row.get('literature_id'),
                'doi': row.get('doi'),
                'title': row.get('title'),
                'authors': row.get('authors'),
                'year': row.get('year'),
                'journal': row.get('journal'),
                'pdf_url': pdf_url,
                'match_type': match_type
            })

    return pd.DataFrame(matches)


def main():
    print("=" * 70)
    print("Shark-References PDF Crawler")
    print("=" * 70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Load remaining papers
    print("Loading remaining papers list...")
    remaining_df = pd.read_csv(REMAINING_CSV)
    print(f"  {len(remaining_df):,} papers remaining to acquire")
    print()

    # Crawl Shark-References
    print("Crawling Shark-References (A-Z)...")
    print("  With 10-second delays, this takes ~4-5 minutes.")
    print()

    shark_refs_pdfs = crawl_all_letters(delay=10)

    print()
    print(f"Total papers with PDFs found on Shark-References: {len(shark_refs_pdfs):,}")

    # Save all found PDFs
    if shark_refs_pdfs:
        sr_df = pd.DataFrame(shark_refs_pdfs)
        sr_output = OUTPUT_DIR / "shark_refs_all_pdfs.csv"
        sr_df.to_csv(sr_output, index=False)
        print(f"Saved to: {sr_output}")

    # Cross-reference
    print()
    print("Cross-referencing against remaining papers...")
    matches_df = cross_reference_remaining(shark_refs_pdfs, remaining_df)

    if len(matches_df) > 0:
        print(f"  ✓ Found {len(matches_df):,} of our remaining papers available on Shark-References!")

        # Save matches
        matches_output = OUTPUT_DIR / "remaining_available_on_shark_refs.csv"
        matches_df.to_csv(matches_output, index=False)
        print(f"  Saved to: {matches_output}")

        # Summary by match type
        print()
        print("  Match breakdown:")
        for mtype, count in matches_df['match_type'].value_counts().items():
            print(f"    {mtype}: {count:,}")

        # Show sample
        print()
        print("  Sample matches (first 5):")
        for _, row in matches_df.head(5).iterrows():
            doi = row['doi'] if pd.notna(row['doi']) else 'no DOI'
            print(f"    - {row['year']}: {doi}")
            print(f"      PDF: {row['pdf_url'][:60]}...")
    else:
        print("  No matches found.")

    print()
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)


if __name__ == "__main__":
    main()
