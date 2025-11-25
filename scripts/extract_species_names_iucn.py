#!/usr/bin/env python3
"""
extract_species_names_iucn.py

Extract and clean species names from IUCN-related papers for scraping.

This script:
1. Loads IUCN papers from database
2. Extracts species names (Genus species) from titles
3. Validates against known shark/ray species
4. Categorizes papers by type (individual assessment vs regional report)
5. Saves cleaned dataset for download scripts

Author: Simon Dedman / Claude
Date: 2025-11-17
"""

import pandas as pd
import re
from pathlib import Path
import logging

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).parent.parent
INPUT_FILE = BASE_DIR / "outputs/iucn_papers.csv"
SPECIES_LIST = BASE_DIR / "data/shark_references_species_list.csv"
OUTPUT_FILE = BASE_DIR / "outputs/iucn_species_cleaned.csv"
OUTPUT_REGIONAL = BASE_DIR / "outputs/iucn_regional_reports.csv"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# ============================================================================
# SPECIES NAME EXTRACTION
# ============================================================================

def extract_species_name(title: str) -> tuple:
    """
    Extract genus and species from title.

    Returns (genus, species, confidence)
    confidence: 'high', 'medium', 'low'
    """
    if not title:
        return None, None, 'none'

    title = title.strip()

    # Pattern 1: Title is JUST a species name (high confidence)
    # Examples: "Carcharodon carcharias", "Planonasus parini"
    match = re.match(r'^([A-Z][a-z]+)\s+([a-z]+)\.?$', title)
    if match:
        return match.group(1), match.group(2), 'high'

    # Pattern 2: Species name at start of title
    # Example: "Carcharodon carcharias population assessment"
    match = re.match(r'^([A-Z][a-z]+)\s+([a-z]+)\s', title)
    if match:
        return match.group(1), match.group(2), 'medium'

    # Pattern 3: Species name anywhere in title (lower confidence)
    match = re.search(r'\b([A-Z][a-z]+)\s+([a-z]{4,})\b', title)
    if match:
        genus = match.group(1)
        species = match.group(2)

        # Filter out common non-species words
        exclude_words = {'species', 'conservation', 'status', 'assessment', 'using',
                        'based', 'analysis', 'review', 'guide', 'sharks', 'rays'}

        if species.lower() not in exclude_words:
            return genus, species, 'low'

    return None, None, 'none'


def classify_paper_type(title: str, journal: str) -> str:
    """
    Classify paper as:
    - 'individual_assessment': Single species assessment
    - 'regional_report': Multi-species regional report
    - 'conservation_guide': Conservation status guide/manual
    - 'research_paper': Research using IUCN data
    """
    title_lower = title.lower()
    journal_lower = str(journal).lower() if pd.notna(journal) else ''

    # Individual assessment: title is just species name
    if re.match(r'^[A-Z][a-z]+\s+[a-z]+\.?$', title):
        return 'individual_assessment'

    # Regional report indicators
    regional_keywords = ['regional', 'arabian sea', 'mediterranean', 'new zealand',
                        'atlantic', 'pacific', 'indian ocean', 'caribbean']
    if any(keyword in title_lower for keyword in regional_keywords):
        return 'regional_report'

    # Conservation guide indicators
    guide_keywords = ['guide', 'illustrated', 'field guide', 'identification',
                     'status', 'protected', 'wpaa', 'cites']
    if any(keyword in title_lower for keyword in guide_keywords):
        return 'conservation_guide'

    # Research paper indicators
    research_keywords = ['dna barcoding', 'utilisation', 'patterns', 'inventory',
                        'analysis', 'phylogen', 'molecular']
    if any(keyword in title_lower for keyword in research_keywords):
        return 'research_paper'

    return 'unknown'


# ============================================================================
# VALIDATION
# ============================================================================

def load_known_species():
    """Load known shark/ray species from database."""
    try:
        df = pd.read_csv(SPECIES_LIST)
        # Extract genus and species from species names
        species_set = set()

        for col in df.columns:
            if col.startswith('sp_'):
                # Column name format: sp_genus_species
                parts = col.replace('sp_', '').split('_')
                if len(parts) >= 2:
                    genus = parts[0].capitalize()
                    species = parts[1].lower()
                    species_set.add((genus, species))

        logging.info(f"Loaded {len(species_set)} known species from database")
        return species_set

    except FileNotFoundError:
        logging.warning(f"Species list not found: {SPECIES_LIST}")
        logging.warning("Skipping validation against known species")
        return set()


def validate_species(genus: str, species: str, known_species: set) -> bool:
    """Check if species is in our known species list."""
    if not known_species:
        return None  # Unknown (can't validate)

    return (genus, species) in known_species


# ============================================================================
# MAIN PROCESSING
# ============================================================================

def main():
    print("="*80)
    print("IUCN SPECIES NAME EXTRACTION")
    print("="*80)

    # Load IUCN papers
    if not INPUT_FILE.exists():
        logging.error(f"Input file not found: {INPUT_FILE}")
        logging.error("Please run the IUCN paper identification script first")
        return

    df = pd.read_csv(INPUT_FILE)
    logging.info(f"Loaded {len(df)} IUCN-related papers")

    # Load known species for validation
    known_species = load_known_species()

    # Extract species names
    results = []
    for idx, row in df.iterrows():
        genus, species, confidence = extract_species_name(row['title'])
        paper_type = classify_paper_type(row['title'], row.get('journal', ''))

        is_known = None
        if genus and species and known_species:
            is_known = validate_species(genus, species, known_species)

        results.append({
            'literature_id': row['literature_id'],
            'year': row['year'],
            'title': row['title'],
            'journal': row.get('journal', ''),
            'authors': row.get('authors', ''),
            'genus': genus,
            'species': species,
            'species_name': f"{genus} {species}" if genus and species else None,
            'extraction_confidence': confidence,
            'paper_type': paper_type,
            'is_known_species': is_known
        })

    results_df = pd.DataFrame(results)

    # Separate by type
    individual_assessments = results_df[results_df['paper_type'] == 'individual_assessment']
    regional_reports = results_df[results_df['paper_type'] == 'regional_report']
    conservation_guides = results_df[results_df['paper_type'] == 'conservation_guide']
    research_papers = results_df[results_df['paper_type'] == 'research_paper']

    # Print statistics
    print("\n" + "="*80)
    print("EXTRACTION RESULTS")
    print("="*80)

    print(f"\nTotal papers processed: {len(results_df)}")
    print(f"\nBy paper type:")
    print(f"  Individual assessments: {len(individual_assessments)}")
    print(f"  Regional reports: {len(regional_reports)}")
    print(f"  Conservation guides: {len(conservation_guides)}")
    print(f"  Research papers: {len(research_papers)}")
    print(f"  Unknown type: {len(results_df[results_df['paper_type'] == 'unknown'])}")

    print(f"\nSpecies extraction:")
    with_species = results_df[results_df['species_name'].notna()]
    print(f"  Papers with species names extracted: {len(with_species)}")

    if known_species:
        validated = with_species[with_species['is_known_species'] == True]
        print(f"  Validated against known species: {len(validated)}")
        print(f"  Validation rate: {len(validated)/len(with_species)*100:.1f}%")

    print(f"\nExtraction confidence:")
    print(results_df['extraction_confidence'].value_counts())

    # Sample output
    print(f"\n" + "="*80)
    print("SAMPLE OF EXTRACTED SPECIES")
    print("="*80)
    sample = with_species[with_species['extraction_confidence'] == 'high'].head(10)
    print(sample[['year', 'species_name', 'paper_type']].to_string(index=False))

    # Save outputs
    # Individual assessments (ready for scraping)
    individual_for_download = individual_assessments[
        individual_assessments['species_name'].notna()
    ].copy()

    individual_for_download.to_csv(OUTPUT_FILE, index=False)
    print(f"\n✅ Saved {len(individual_for_download)} individual assessments to:")
    print(f"   {OUTPUT_FILE}")

    # Regional reports (require different strategy)
    regional_reports.to_csv(OUTPUT_REGIONAL, index=False)
    print(f"✅ Saved {len(regional_reports)} regional reports to:")
    print(f"   {OUTPUT_REGIONAL}")

    print("\n" + "="*80)
    print("NEXT STEPS")
    print("="*80)
    print("\n1. Register for IUCN API token:")
    print("   https://apiv3.iucnredlist.org/api/v3/token")
    print("\n2. Test API access with sample species:")
    print("   ./venv/bin/python scripts/download_iucn_via_api.py --test")
    print("\n3. Build Selenium scraper for species without API PDFs")
    print("\n4. Download regional reports separately (SSG website)")
    print("="*80)


if __name__ == "__main__":
    main()
