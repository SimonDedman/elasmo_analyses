#!/usr/bin/env python3
"""
Incremental update script for Shark-References species database

This script checks for new species or updates to existing species since the last scrape.
It compares the current online species list with the local database and only extracts
new or modified species.

Usage:
    python3 scripts/update_shark_references_species.py [--full]

Options:
    --full          Force full re-scrape (ignore existing data)
    --delay SECS    Delay between requests in seconds (default: 3)
    --help          Show this help message

Output:
    - data/shark_references_species_list.csv (updated species list)
    - data/shark_species_detailed_complete.csv (updated detailed data)
    - data/shark_species_update_report.txt (summary of changes)

Author: Auto-generated for EEA 2025 Data Panel Project
Date: 2025-10-13
"""

import sys
import os
import argparse
import requests
from bs4 import BeautifulSoup
import csv
import time
import re
from datetime import datetime
from pathlib import Path

# Configuration
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'data'
SPECIES_LIST_FILE = DATA_DIR / 'shark_references_species_list.csv'
SPECIES_DETAILS_FILE = DATA_DIR / 'shark_species_detailed_complete.csv'
UPDATE_REPORT_FILE = DATA_DIR / 'shark_species_update_report.txt'


def load_existing_species():
    """Load existing species from local database"""
    if not SPECIES_LIST_FILE.exists():
        print('No existing species list found. Will perform full extraction.')
        return set(), {}

    existing_binomials = set()
    existing_data = {}

    with open(SPECIES_LIST_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            binomial = row['binomial']
            existing_binomials.add(binomial)
            existing_data[binomial] = row

    print(f'Loaded {len(existing_binomials)} existing species from local database')
    return existing_binomials, existing_data


def get_online_species_list(delay=3):
    """Fetch current species list from Shark-References website"""
    print('Fetching current species list from Shark-References...')

    all_species = []
    letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

    for letter in letters:
        url = f'https://shark-references.com/species/listValidRecent/{letter}'
        print(f'  Fetching letter {letter}... ', end='', flush=True)

        try:
            response = requests.get(url, timeout=30)

            if response.status_code != 200:
                print(f'ERROR (HTTP {response.status_code})')
                continue

            soup = BeautifulSoup(response.content, 'html.parser')

            # Find all species view links
            species_links = soup.find_all('a', href=lambda x: x and '/species/view/' in x)

            letter_count = 0
            seen = set()

            for link in species_links:
                href = link.get('href', '')
                if not href.startswith('/species/view/'):
                    continue

                if href in seen:
                    continue
                seen.add(href)

                # Extract binomial from URL
                binomial_url = href.replace('/species/view/', '')

                if '-' in binomial_url:
                    parts = binomial_url.split('-', 1)
                    genus = parts[0]
                    species = parts[1]
                    proper_binomial = f'{genus} {species}'

                    all_species.append({
                        'binomial': proper_binomial,
                        'binomial_url': binomial_url,
                        'genus': genus,
                        'species': species,
                        'url': f'https://shark-references.com{href}',
                        'letter': letter,
                        'date_checked': datetime.now().strftime('%Y-%m-%d')
                    })
                    letter_count += 1

            print(f'{letter_count} species')
            time.sleep(delay)

        except Exception as e:
            print(f'ERROR: {str(e)}')
            continue

    print(f'Total online species: {len(all_species)}')
    return all_species


def compare_species_lists(online_species, existing_binomials):
    """Compare online and local species lists to find changes"""
    online_binomials = {sp['binomial'] for sp in online_species}

    new_species = online_binomials - existing_binomials
    removed_species = existing_binomials - online_binomials
    unchanged_species = online_binomials & existing_binomials

    return new_species, removed_species, unchanged_species


def extract_species_details(species_info, delay=3):
    """Extract detailed information for a single species"""
    binomial = species_info['binomial']
    url = species_info['url']

    try:
        response = requests.get(url, timeout=30)

        if response.status_code != 200:
            return None, f'HTTP {response.status_code}'

        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract all available fields
        details = {
            'binomial': binomial,
            'binomial_url': species_info['binomial_url'],
            'genus': species_info['genus'],
            'species_epithet': species_info['species'],
            'url': url,
            'letter': species_info['letter'],
            'date_extracted': datetime.now().strftime('%Y-%m-%d')
        }

        # Taxonomy
        taxonomy = extract_taxonomy(soup)
        details.update(taxonomy)

        # Common names
        common_names = extract_common_names(soup)
        if common_names:
            details['common_names_json'] = str(common_names)
            english_names = [cn['name'] for cn in common_names if cn['language'].lower() in ['eng', 'english']]
            if english_names:
                details['common_name_primary'] = english_names[0]

        # Other fields
        details['distribution'] = extract_text_after_label(soup, 'Distribution')
        details['habitat'] = extract_text_after_label(soup, 'Habitat')
        details['size_weight_age'] = extract_text_after_label(soup, 'Size.*Weight.*Age')
        details['biology'] = extract_text_after_label(soup, 'Biology')
        details['short_description'] = extract_text_after_label(soup, 'Short Description')
        details['human_uses'] = extract_text_after_label(soup, 'Human uses')
        details['remarks'] = extract_text_after_label(soup, 'Remarks')

        time.sleep(delay)
        return details, None

    except Exception as e:
        time.sleep(delay)
        return None, str(e)


def extract_text_after_label(soup, label_text):
    """Extract text content after a label span"""
    label = soup.find('span', class_='label', string=re.compile(label_text, re.IGNORECASE))
    if not label:
        return None

    parent = label.find_parent('div')
    if parent:
        label_copy = label.extract()
        text = parent.get_text(separator=' ', strip=True)
        return text if text else None
    return None


def extract_common_names(soup):
    """Extract common names with language info"""
    label = soup.find('span', class_='label', string=re.compile('Common names', re.IGNORECASE))
    if not label:
        return []

    parent = label.find_parent('div')
    if not parent:
        return []

    common_names = []
    flags = parent.find_all('img', src=lambda x: x and '/images/flags/' in x)

    for flag in flags:
        lang_code = flag.get('alt', '').split()[0] if flag.get('alt') else 'unknown'

        name_text = ''
        for sibling in flag.next_siblings:
            if hasattr(sibling, 'name') and sibling.name == 'img' and '/images/flags/' in sibling.get('src', ''):
                break
            if isinstance(sibling, str):
                name_text += sibling

        name_text = name_text.strip(' ,\n\t')

        if name_text:
            common_names.append({
                'language': lang_code,
                'name': name_text
            })

    return common_names


def extract_taxonomy(soup):
    """Extract taxonomic classification"""
    label = soup.find('span', class_='label', string=re.compile('Classification:', re.IGNORECASE))
    if not label:
        return {}

    parent = label.find_parent('div')
    if not parent:
        return {}

    taxonomy = {}
    text = parent.get_text(separator='\n', strip=True)
    lines = text.split('\n')

    for line in lines:
        if ':' in line:
            parts = line.split(':', 1)
            if len(parts) == 2:
                rank = parts[0].strip().lower()
                name = parts[1].strip()
                if rank in ['class', 'subclass', 'superorder', 'order', 'family', 'genus']:
                    taxonomy[rank] = name

    return taxonomy


def generate_update_report(new_species, removed_species, unchanged_species, errors, output_file):
    """Generate a human-readable update report"""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('='*80 + '\n')
        f.write('Shark-References Species Database Update Report\n')
        f.write('='*80 + '\n')
        f.write(f'Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
        f.write('\n')

        f.write('SUMMARY\n')
        f.write('-'*80 + '\n')
        f.write(f'New species found:        {len(new_species)}\n')
        f.write(f'Removed species:          {len(removed_species)}\n')
        f.write(f'Unchanged species:        {len(unchanged_species)}\n')
        f.write(f'Errors during extraction: {len(errors)}\n')
        f.write(f'Total species now:        {len(new_species) + len(unchanged_species)}\n')
        f.write('\n')

        if new_species:
            f.write('NEW SPECIES\n')
            f.write('-'*80 + '\n')
            for binomial in sorted(new_species):
                f.write(f'  + {binomial}\n')
            f.write('\n')

        if removed_species:
            f.write('REMOVED SPECIES (no longer in online database)\n')
            f.write('-'*80 + '\n')
            for binomial in sorted(removed_species):
                f.write(f'  - {binomial}\n')
            f.write('\n')

        if errors:
            f.write('ERRORS\n')
            f.write('-'*80 + '\n')
            for error in errors:
                f.write(f'  ! {error["binomial"]}: {error["error"]}\n')
            f.write('\n')

        f.write('='*80 + '\n')


def main():
    parser = argparse.ArgumentParser(
        description='Incremental update for Shark-References species database'
    )
    parser.add_argument(
        '--full',
        action='store_true',
        help='Force full re-scrape (ignore existing data)'
    )
    parser.add_argument(
        '--delay',
        type=int,
        default=3,
        help='Delay between requests in seconds (default: 3)'
    )

    args = parser.parse_args()

    print('='*80)
    print('Shark-References Species Database Update')
    print('='*80)
    print(f'Start time: {datetime.now()}')
    print()

    # Load existing species (unless --full)
    if args.full:
        print('FULL SCRAPE mode: Ignoring existing data')
        existing_binomials = set()
        existing_data = {}
    else:
        existing_binomials, existing_data = load_existing_species()

    # Fetch current online species list
    online_species = get_online_species_list(delay=args.delay)

    if not online_species:
        print('ERROR: Failed to fetch online species list')
        return 1

    # Compare lists
    new_species, removed_species, unchanged_species = compare_species_lists(
        online_species,
        existing_binomials
    )

    print()
    print('COMPARISON RESULTS')
    print('-'*80)
    print(f'New species:       {len(new_species)}')
    print(f'Removed species:   {len(removed_species)}')
    print(f'Unchanged species: {len(unchanged_species)}')
    print()

    # If no changes and not full mode, exit early
    if not new_species and not removed_species and not args.full:
        print('No changes detected. Database is up to date!')
        return 0

    # Extract details for new species only
    if new_species or args.full:
        print(f'Extracting details for {len(new_species)} new species...')
        print(f'Estimated time: ~{len(new_species) * args.delay / 60:.1f} minutes')
        print()

        all_details = []
        errors = []

        # Load existing detailed data
        if SPECIES_DETAILS_FILE.exists() and not args.full:
            with open(SPECIES_DETAILS_FILE, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['binomial'] in unchanged_species:
                        all_details.append(row)

        # Extract new species
        species_to_extract = [sp for sp in online_species if sp['binomial'] in new_species]

        for idx, species_info in enumerate(species_to_extract):
            binomial = species_info['binomial']
            print(f'[{idx+1}/{len(species_to_extract)}] {binomial}... ', end='', flush=True)

            details, error = extract_species_details(species_info, delay=args.delay)

            if details:
                all_details.append(details)
                print('OK')
            else:
                errors.append({'binomial': binomial, 'error': error})
                print(f'ERROR: {error}')

        # Save updated files
        print()
        print('Saving updated database...')

        # Save species list
        with open(SPECIES_LIST_FILE, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['binomial', 'binomial_url', 'genus', 'species', 'url', 'letter', 'date_checked']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(online_species)
        print(f'  Updated: {SPECIES_LIST_FILE}')

        # Save detailed data
        if all_details:
            with open(SPECIES_DETAILS_FILE, 'w', newline='', encoding='utf-8') as f:
                fieldnames = list(all_details[0].keys())
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(all_details)
            print(f'  Updated: {SPECIES_DETAILS_FILE}')

        # Generate report
        generate_update_report(new_species, removed_species, unchanged_species, errors, UPDATE_REPORT_FILE)
        print(f'  Report: {UPDATE_REPORT_FILE}')

        print()
        print('Update complete!')
        print(f'Successfully updated: {len(new_species)} new species')
        print(f'Errors: {len(errors)} species')

    print()
    print(f'End time: {datetime.now()}')
    print('='*80)

    return 0


if __name__ == '__main__':
    sys.exit(main())
