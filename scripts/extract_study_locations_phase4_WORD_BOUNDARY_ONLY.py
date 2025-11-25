#!/usr/bin/env python3
"""
Phase 4: Extract Study Locations - Word Boundary Matching ONLY

This version uses ONLY word boundary matching to prevent false positives
(like "incubated" matching "cuba"), but does NOT require context validation.

Context validation was TOO STRICT and filtered out 96% of valid matches.

FIX APPLIED: Word boundary matching using \b regex anchors
NO CONTEXT VALIDATION (too restrictive)

Author: Claude Code
Date: 2025-11-24
"""

import re
import csv
import sqlite3
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import pdfplumber
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime

# Paths
DB_PATH = Path("database/technique_taxonomy.db")
PDF_BASE = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")
NUM_WORKERS = 11

# Ocean basins for classification
OCEAN_BASINS = {
    'North Atlantic': ['north atlantic', 'northwest atlantic', 'northeast atlantic',
                       'atlantic ocean', 'gulf of mexico', 'caribbean', 'mediterranean'],
    'South Atlantic': ['south atlantic', 'southeast atlantic', 'southwest atlantic'],
    'North Pacific': ['north pacific', 'northwest pacific', 'northeast pacific',
                      'bering sea', 'gulf of alaska', 'california current'],
    'South Pacific': ['south pacific', 'southwest pacific', 'southeast pacific',
                      'coral sea', 'tasman sea'],
    'Indian Ocean': ['indian ocean', 'arabian sea', 'bay of bengal', 'red sea'],
    'Arctic': ['arctic', 'arctic ocean', 'beaufort sea', 'chukchi sea'],
    'Southern Ocean': ['southern ocean', 'antarctic'],
}

# Country patterns (comprehensive list)
COUNTRIES = {
    'USA': ['united states of america', 'united states', 'u.s.a', 'usa', 'u.s.',
            'california', 'florida', 'hawaii', 'gulf of mexico', 'chesapeake',
            'mississippi', 'texas', 'alaska', 'georgia', 'carolina', 'virginia', 'delaware'],
    'Australia': ['australia', 'queensland', 'new south wales', 'victoria',
                  'western australia', 'tasmania', 'great barrier reef'],
    'UK': ['united kingdom', 'england', 'scotland', 'wales', 'britain',
           'british isles', 'north sea'],
    'Canada': ['canada', 'canadian', 'british columbia', 'newfoundland',
               'nova scotia', 'labrador'],
    'Mexico': ['mexico', 'mexican', 'baja california', 'baja', 'gulf of california', 'sea of cortez'],
    'Brazil': ['brazil', 'brazilian'],
    'South Africa': ['south africa', 'south african'],
    'New Zealand': ['new zealand'],
    'Japan': ['japan', 'japanese'],
    'China': ['china', 'chinese'],
    'India': ['india', 'indian'],
    'Indonesia': ['indonesia', 'indonesian'],
    'Philippines': ['philippines', 'philippine'],
    'Thailand': ['thailand', 'thai'],
    'Malaysia': ['malaysia', 'malaysian'],
    'Taiwan': ['taiwan', 'taiwanese'],
    'South Korea': ['south korea', 'republic of korea'],
    'Spain': ['spain', 'spanish', 'canary islands', 'balearic'],
    'Portugal': ['portugal', 'portuguese', 'azores', 'madeira'],
    'Italy': ['italy', 'italian', 'adriatic'],
    'France': ['france', 'french'],
    'Germany': ['germany', 'german'],
    'Norway': ['norway', 'norwegian'],
    'Sweden': ['sweden', 'swedish'],
    'Denmark': ['denmark', 'danish'],
    'Netherlands': ['netherlands', 'dutch'],
    'Greece': ['greece', 'greek'],
    'Turkey': ['turkey', 'turkish'],
    'Egypt': ['egypt', 'egyptian'],
    'Israel': ['israel', 'israeli'],
    'Saudi Arabia': ['saudi arabia', 'saudi'],
    'United Arab Emirates': ['united arab emirates', 'uae', 'emirates'],
    'Oman': ['oman', 'omani'],
    'Iran': ['iran', 'iranian'],
    'Pakistan': ['pakistan', 'pakistani'],
    'Bangladesh': ['bangladesh'],
    'Sri Lanka': ['sri lanka'],
    'Maldives': ['maldives'],
    'Seychelles': ['seychelles'],
    'Madagascar': ['madagascar'],
    'Mozambique': ['mozambique'],
    'Kenya': ['kenya', 'kenyan'],
    'Tanzania': ['tanzania'],
    'Chile': ['chile', 'chilean'],
    'Argentina': ['argentina', 'argentinian', 'argentine'],
    'Peru': ['peru', 'peruvian'],
    'Ecuador': ['ecuador', 'ecuadorian', 'galapagos'],
    'Colombia': ['colombia', 'colombian'],
    'Venezuela': ['venezuela', 'venezuelan'],
    'Costa Rica': ['costa rica'],
    'Panama': ['panama', 'panamanian'],
    'Belize': ['belize'],
    'Bahamas': ['bahamas'],
    'Cuba': ['cuba', 'cuban'],
    'Jamaica': ['jamaica'],
    'Fiji': ['fiji'],
    'Papua New Guinea': ['papua new guinea', 'png'],
    'Palau': ['palau'],
    'Micronesia': ['micronesia'],
    'Samoa': ['samoa'],
    'New Caledonia': ['new caledonia'],
}

# Methods section indicators
METHODS_KEYWORDS = [
    'methods', 'materials and methods', 'methodology', 'study area',
    'study site', 'sampling', 'field work', 'data collection',
    'study location', 'study region', 'study period', 'site description'
]

# Coordinate patterns (latitude/longitude)
LAT_LONG_PATTERN = re.compile(
    r'(\d+[\.,]\d+)[°º]?\s*[NS]?\s*[,;]?\s*(\d+[\.,]\d+)[°º]?\s*[EW]?',
    re.IGNORECASE
)

def find_pdf_path(paper_id: str) -> Optional[Path]:
    """Find PDF file with year subdirectory."""
    year_match = re.search(r'\.(\d{4})\.', paper_id)
    year = year_match.group(1) if year_match else None

    # Try direct
    pdf_path = PDF_BASE / paper_id
    if pdf_path.exists():
        return pdf_path

    # Try with year subdir
    if year:
        pdf_path = PDF_BASE / year / paper_id
        if pdf_path.exists():
            return pdf_path

        pdf_path = PDF_BASE / f"{year}.0" / paper_id
        if pdf_path.exists():
            return pdf_path

    return None

def extract_methods_section(pdf_path: Path) -> Optional[str]:
    """Extract Methods/Materials section from PDF."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            full_text = ""

            # Extract first 10 pages (Methods usually in first few pages)
            for page_num, page in enumerate(pdf.pages[:10]):
                text = page.extract_text()
                if text:
                    full_text += text + "\n"

            if not full_text:
                return None

            # Find Methods section
            methods_text = ""
            lines = full_text.split('\n')
            in_methods = False

            for i, line in enumerate(lines):
                line_lower = line.lower().strip()

                # Check if we're entering Methods section
                if any(kw in line_lower for kw in METHODS_KEYWORDS):
                    in_methods = True
                    continue

                # Stop if we hit Results or Discussion
                if in_methods and any(kw in line_lower for kw in ['results', 'discussion', 'conclusions']):
                    break

                if in_methods:
                    methods_text += line + "\n"

                    # Limit to ~500 lines
                    if len(methods_text.split('\n')) > 500:
                        break

            return methods_text if methods_text else None

    except Exception as e:
        return None

def extract_country(text: str) -> Optional[str]:
    """
    Extract country name from text using WORD BOUNDARY matching ONLY.

    Returns country if country name appears as a complete word (not substring).
    NO CONTEXT VALIDATION - word boundaries are sufficient.
    """
    if not text:
        return None

    text_lower = text.lower()

    # Sort countries by pattern length (longest first) to avoid substring issues
    # e.g., "New South Wales" should match before "Wales"
    all_patterns = []
    for country, patterns in COUNTRIES.items():
        for pattern in patterns:
            all_patterns.append((country, pattern))

    # Sort by pattern length (longest first)
    all_patterns.sort(key=lambda x: len(x[1]), reverse=True)

    # Check each pattern with WORD BOUNDARIES
    for country, pattern in all_patterns:
        # Create regex with word boundaries
        # \b matches word boundary (space, punctuation, start/end of string)
        pattern_regex = re.compile(r'\b' + re.escape(pattern) + r'\b', re.IGNORECASE)

        if pattern_regex.search(text_lower):
            return country  # Return first match (longest pattern priority)

    return None

def extract_ocean_basin(text: str) -> Optional[str]:
    """Extract ocean basin from text."""
    if not text:
        return None

    text_lower = text.lower()

    # Check each ocean basin
    for basin, patterns in OCEAN_BASINS.items():
        for pattern in patterns:
            if pattern in text_lower:
                return basin

    return None

def extract_coordinates(text: str) -> Optional[Tuple[float, float]]:
    """Extract latitude/longitude coordinates from text."""
    if not text:
        return None

    # Find all coordinate patterns
    matches = LAT_LONG_PATTERN.findall(text)

    if matches:
        # Return first coordinate pair found
        try:
            lat_str, lon_str = matches[0]
            lat = float(lat_str.replace(',', '.'))
            lon = float(lon_str.replace(',', '.'))

            # Sanity check (latitude -90 to 90, longitude -180 to 180)
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return (lat, lon)
        except:
            pass

    return None

def extract_study_location_snippet(text: str) -> Optional[str]:
    """Extract a representative snippet describing study location."""
    if not text:
        return None

    # Look for sentences containing location keywords
    location_keywords = ['study', 'sampling', 'collection', 'site', 'area', 'region',
                         'location', 'conducted', 'carried out', 'performed']

    sentences = text.split('.')

    for sentence in sentences[:50]:  # First 50 sentences
        sentence_lower = sentence.lower()

        # If sentence contains location keyword AND country/ocean
        if any(kw in sentence_lower for kw in location_keywords):
            # Check if it mentions a country or ocean
            if extract_country(sentence) or extract_ocean_basin(sentence):
                # Return cleaned snippet (max 200 chars)
                snippet = sentence.strip()
                if len(snippet) > 200:
                    snippet = snippet[:197] + "..."
                return snippet

    return None

def process_paper(paper_info: Tuple[str, str, str]) -> Dict:
    """Process one paper to extract study location."""
    paper_id, author_country, author_institution = paper_info

    # Find PDF
    pdf_path = find_pdf_path(paper_id)
    if not pdf_path:
        return {
            'paper_id': paper_id,
            'status': 'pdf_not_found',
            'author_country': author_country,
        }

    # Extract Methods section
    methods_text = extract_methods_section(pdf_path)
    if not methods_text:
        return {
            'paper_id': paper_id,
            'status': 'methods_not_found',
            'author_country': author_country,
        }

    # Extract geographic information
    study_country = extract_country(methods_text)
    ocean_basin = extract_ocean_basin(methods_text)
    coordinates = extract_coordinates(methods_text)
    location_snippet = extract_study_location_snippet(methods_text)

    # Determine if this is parachute research
    is_parachute = False
    if author_country and study_country and author_country != study_country:
        is_parachute = True

    lat, lon = coordinates if coordinates else (None, None)

    return {
        'paper_id': paper_id,
        'status': 'success',
        'author_country': author_country,
        'study_country': study_country,
        'ocean_basin': ocean_basin,
        'latitude': lat,
        'longitude': lon,
        'location_text': location_snippet,
        'is_parachute': is_parachute,
    }

def update_database(results: List[Dict]):
    """Update database with study location data."""

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    updated_count = 0
    parachute_count = 0

    for result in results:
        if result['status'] != 'success':
            continue

        cursor.execute("""
            UPDATE paper_geography
            SET study_country = ?,
                study_ocean_basin = ?,
                study_latitude = ?,
                study_longitude = ?,
                study_location_text = ?,
                has_study_location = ?,
                is_parachute_research = ?,
                updated_date = ?
            WHERE paper_id = ?
        """, (
            result['study_country'],
            result['ocean_basin'],
            result['latitude'],
            result['longitude'],
            result['location_text'],
            1 if result['study_country'] or result['ocean_basin'] else 0,
            1 if result['is_parachute'] else 0,
            datetime.now().isoformat(),
            result['paper_id']
        ))

        updated_count += 1
        if result['is_parachute']:
            parachute_count += 1

    conn.commit()
    conn.close()

    return updated_count, parachute_count

def main():
    """Main execution function."""

    print("\n" + "="*80)
    print("PHASE 4: EXTRACT STUDY LOCATIONS (WORD BOUNDARY MATCHING ONLY)")
    print("="*80 + "\n")

    print("FIX: Word boundary matching prevents 'incubated' → 'cuba' false positives")
    print("NO CONTEXT VALIDATION (too strict - filtered out 96% of valid matches)")
    print()

    # Get papers with author country data from database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT paper_id, first_author_country, first_author_institution
        FROM paper_geography
        WHERE has_author_country = 1
    """)

    papers = cursor.fetchall()
    conn.close()

    print(f"Papers to process: {len(papers):,}\n")
    print(f"Workers: {NUM_WORKERS}\n")

    # Process in parallel
    all_results = []
    success_count = 0
    methods_not_found = 0
    pdf_not_found = 0

    with ProcessPoolExecutor(max_workers=NUM_WORKERS) as executor:
        futures = {executor.submit(process_paper, paper): paper for paper in papers}

        for i, future in enumerate(as_completed(futures), 1):
            result = future.result()
            all_results.append(result)

            if result['status'] == 'success':
                success_count += 1
            elif result['status'] == 'methods_not_found':
                methods_not_found += 1
            elif result['status'] == 'pdf_not_found':
                pdf_not_found += 1

            if i % 500 == 0:
                print(f"  Progress: {i:,}/{len(papers):,} (success: {success_count:,}, "
                      f"methods_not_found: {methods_not_found}, pdf_not_found: {pdf_not_found})")

    print(f"\n✓ Extraction complete!")
    print(f"  Successfully extracted: {success_count:,} ({success_count/len(papers)*100:.1f}%)")
    print(f"  Methods not found: {methods_not_found}")
    print(f"  PDFs not found: {pdf_not_found}")

    # Count successful extractions
    with_country = sum(1 for r in all_results if r['status'] == 'success' and r.get('study_country'))
    with_ocean = sum(1 for r in all_results if r['status'] == 'success' and r.get('ocean_basin'))
    with_coords = sum(1 for r in all_results if r['status'] == 'success' and r.get('latitude'))
    parachute = sum(1 for r in all_results if r['status'] == 'success' and r.get('is_parachute'))

    print(f"\n=== Study Location Data Extracted ===")
    print(f"  Papers with study country: {with_country:,} ({with_country/success_count*100:.1f}% of successful)")
    print(f"  Papers with ocean basin: {with_ocean:,} ({with_ocean/success_count*100:.1f}%)")
    print(f"  Papers with coordinates: {with_coords:,} ({with_coords/success_count*100:.1f}%)")
    print(f"  Parachute research detected: {parachute:,} ({parachute/success_count*100:.1f}%)")

    # Update database
    print(f"\n=== Updating database ===")
    updated, parachute_db = update_database(all_results)
    print(f"  Updated {updated:,} records in paper_geography table")
    print(f"  Parachute research flagged: {parachute_db:,}")

    # Generate summary statistics
    print(f"\n=== Parachute Research Examples (First 10) ===")
    parachute_examples = [r for r in all_results if r['status'] == 'success' and r.get('is_parachute')][:10]

    for ex in parachute_examples:
        print(f"  {ex['paper_id']}")
        print(f"    Author country: {ex['author_country']}")
        print(f"    Study country:  {ex['study_country']}")
        if ex.get('location_text'):
            print(f"    Location: {ex['location_text'][:100]}...")
        print()

    print("="*80)
    print("PHASE 4 COMPLETE (WORD BOUNDARY ONLY)")
    print("="*80 + "\n")

    print(f"Study location data extracted for {success_count:,} papers")
    print(f"Parachute research identified: {parachute:,} papers")
    print(f"\nDatabase updated: paper_geography table")
    print(f"\nNext: Analyze author country vs study country patterns")

if __name__ == "__main__":
    main()
