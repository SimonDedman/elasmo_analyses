#!/usr/bin/env python3
"""
download_iucn_via_api_and_pdf.py

Download IUCN Red List assessment PDFs using API + direct PDF URL pattern.

Strategy:
1. Use IUCN API to get species assessment IDs
2. Construct PDF URLs: https://www.iucnredlist.org/species/pdf/{assessmentid}
3. Download PDFs with requests (or undetected-chromedriver if Cloudflare blocks)

Author: Simon Dedman / Claude
Date: 2025-11-17
"""

import pandas as pd
import requests
from pathlib import Path
from datetime import datetime
import time
from tqdm import tqdm
import logging

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).parent.parent
INPUT_FILE = BASE_DIR / "outputs/iucn_species_cleaned.csv"
OUTPUT_DIR = BASE_DIR / "outputs/SharkPapers"
LOG_FILE = BASE_DIR / "logs/iucn_api_pdf_download_log.csv"

# IUCN API
IUCN_API_KEY = "u1kqr4aah4uyK8nMD8bRVjq4e69sDcE2o6oW"
IUCN_API_BASE = "https://apiv3.iucnredlist.org/api/v3"

# Rate limiting
API_DELAY = 0.5  # API allows good rate
PDF_DELAY = 2.0  # Be respectful with PDF downloads

# User agent
USER_AGENT = "SharkResearchBot/1.0 (mailto:simondedman@gmail.com; Research purposes)"

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler(BASE_DIR / "logs/iucn_api_pdf.log"),
        logging.StreamHandler()
    ]
)

# ============================================================================
# API FUNCTIONS
# ============================================================================

def get_species_assessment(genus: str, species: str) -> dict:
    """
    Get species assessment info from IUCN API.

    Returns dict with taxonid, assessment_id, category, etc.
    """
    try:
        species_name = f"{genus} {species}"
        url = f"{IUCN_API_BASE}/species/{species_name}"
        params = {'token': IUCN_API_KEY}
        headers = {'User-Agent': USER_AGENT}

        response = requests.get(url, params=params, headers=headers, timeout=30)

        if response.status_code == 200:
            data = response.json()
            result = data.get('result', [])

            if result and len(result) > 0:
                assessment = result[0]
                return {
                    'found': True,
                    'taxonid': assessment.get('taxonid'),
                    'assessment_id': assessment.get('assessmentid'),
                    'scientific_name': assessment.get('scientific_name'),
                    'category': assessment.get('category'),
                    'population_trend': assessment.get('population_trend'),
                    'main_common_name': assessment.get('main_common_name'),
                }

        return {'found': False}

    except Exception as e:
        logging.error(f"API error for {genus} {species}: {e}")
        return {'found': False, 'error': str(e)}


# ============================================================================
# PDF DOWNLOAD FUNCTIONS
# ============================================================================

def download_pdf_direct(assessment_id: str, literature_id: str, species_name: str) -> dict:
    """
    Download PDF using direct URL pattern.

    PDF URL: https://www.iucnredlist.org/species/pdf/{assessmentid}
    """
    try:
        # Construct PDF URL
        pdf_url = f"https://www.iucnredlist.org/species/pdf/{assessment_id}"

        # Construct filename
        safe_species = species_name.replace(' ', '_')
        filename = f"{literature_id}_{safe_species}_{assessment_id}.pdf"
        output_path = OUTPUT_DIR / filename

        # Check if already exists
        if output_path.exists():
            logging.info(f"Already exists: {filename}")
            return {
                'status': 'already_exists',
                'filename': filename,
                'size_bytes': output_path.stat().st_size,
                'pdf_url': pdf_url
            }

        # Download PDF
        headers = {'User-Agent': USER_AGENT}
        response = requests.get(pdf_url, headers=headers, timeout=60, stream=True)

        if response.status_code == 200:
            # Check content type
            content_type = response.headers.get('Content-Type', '')

            # Save PDF
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            file_size = output_path.stat().st_size

            # Verify it's a real PDF (not error page)
            if file_size < 1024:  # Less than 1KB
                # Might be error page
                with open(output_path, 'rb') as f:
                    first_bytes = f.read(4)
                    if first_bytes != b'%PDF':
                        output_path.unlink()
                        return {
                            'status': 'not_pdf',
                            'size_bytes': file_size,
                            'pdf_url': pdf_url
                        }

            # Check if it's HTML error page
            if 'html' in content_type.lower():
                output_path.unlink()
                return {
                    'status': 'html_response',
                    'content_type': content_type,
                    'pdf_url': pdf_url
                }

            logging.info(f"Downloaded: {filename} ({file_size:,} bytes)")
            return {
                'status': 'success',
                'filename': filename,
                'size_bytes': file_size,
                'pdf_url': pdf_url
            }

        elif response.status_code == 403:
            # Cloudflare blocking - need undetected-chromedriver
            return {
                'status': 'cloudflare_blocked',
                'pdf_url': pdf_url,
                'status_code': 403
            }

        else:
            return {
                'status': 'http_error',
                'status_code': response.status_code,
                'pdf_url': pdf_url
            }

    except Exception as e:
        logging.error(f"Error downloading PDF for {species_name}: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }


# ============================================================================
# MAIN PROCESSING
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Download IUCN PDFs via API + direct URLs")
    parser.add_argument('--test', action='store_true', help="Test mode: only process 10 species")
    parser.add_argument('--max-papers', type=int, help="Maximum papers to process")
    args = parser.parse_args()

    print("=" * 80)
    print("IUCN RED LIST API + PDF DOWNLOADER")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\nUsing API token: {IUCN_API_KEY[:10]}...")

    # Create directories
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (BASE_DIR / "logs").mkdir(exist_ok=True)

    # Load species list
    if not INPUT_FILE.exists():
        print(f"\n❌ Input file not found: {INPUT_FILE}")
        return

    df = pd.read_csv(INPUT_FILE)

    # Filter for individual assessments with species names
    df = df[
        (df['paper_type'] == 'individual_assessment') &
        (df['species_name'].notna())
    ].copy()

    print(f"\n📊 Loaded {len(df):,} species for download")

    # Apply limits
    if args.test:
        df = df.head(10)
        print(f"🧪 Test mode: processing {len(df)} species")
    elif args.max_papers:
        df = df.head(args.max_papers)
        print(f"📊 Limited to: {args.max_papers:,} species")

    # Load existing results to avoid re-processing
    existing_results = []
    if LOG_FILE.exists():
        existing_df = pd.read_csv(LOG_FILE)
        existing_ids = set(existing_df['literature_id'].values)
        df = df[~df['literature_id'].isin(existing_ids)]
        print(f"✅ Skipping {len(existing_ids):,} already processed")
        print(f"📊 Remaining to process: {len(df):,}")
        existing_results = existing_df.to_dict('records')

    if len(df) == 0:
        print("\n✅ All species already processed!")
        return

    # Process species
    print("\n" + "=" * 80)
    print(f"PROCESSING {len(df):,} SPECIES")
    print("=" * 80)

    results = existing_results.copy()

    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Downloading"):
        literature_id = row['literature_id']
        genus = row['genus']
        species = row['species']
        species_name = f"{genus} {species}"

        result = {
            'literature_id': literature_id,
            'genus': genus,
            'species': species,
            'species_name': species_name,
            'year': row['year'],
            'title': row['title'],
            'timestamp': datetime.now().isoformat()
        }

        # Step 1: Get assessment ID from API
        assessment_info = get_species_assessment(genus, species)
        time.sleep(API_DELAY)

        if not assessment_info.get('found'):
            result['status'] = 'not_found_in_api'
            result['message'] = assessment_info.get('error', 'Species not found in IUCN database')
            results.append(result)
            continue

        # Add assessment info to result
        result['taxonid'] = assessment_info.get('taxonid')
        result['assessment_id'] = assessment_info.get('assessment_id')
        result['category'] = assessment_info.get('category')
        result['population_trend'] = assessment_info.get('population_trend')
        result['main_common_name'] = assessment_info.get('main_common_name')

        # Step 2: Download PDF using assessment ID
        assessment_id = assessment_info.get('assessment_id')
        if not assessment_id:
            result['status'] = 'no_assessment_id'
            result['message'] = 'API returned species but no assessment ID'
            results.append(result)
            continue

        download_result = download_pdf_direct(assessment_id, str(literature_id), species_name)
        time.sleep(PDF_DELAY)

        # Merge download result
        result.update(download_result)
        results.append(result)

        # Save progress every 50 species
        if len(results) % 50 == 0:
            results_df = pd.DataFrame(results)
            results_df.to_csv(LOG_FILE, index=False)
            logging.info(f"Progress saved: {len(results)} species processed")

    # Final save
    results_df = pd.DataFrame(results)
    results_df.to_csv(LOG_FILE, index=False)

    # Summary
    print("\n" + "=" * 80)
    print("DOWNLOAD SUMMARY")
    print("=" * 80)

    processed = len(results) - len(existing_results)
    success = len(results_df[results_df['status'] == 'success'])
    already_exists = len(results_df[results_df['status'] == 'already_exists'])
    not_found_api = len(results_df[results_df['status'] == 'not_found_in_api'])
    cloudflare = len(results_df[results_df['status'] == 'cloudflare_blocked'])
    total_pdfs = success + already_exists

    print(f"\n📊 Processed this session: {processed:,}")
    print(f"✅ New PDFs downloaded: {success:,}")
    print(f"📄 Already existed: {already_exists:,}")
    print(f"📊 Total PDFs: {total_pdfs:,}")
    print(f"📈 Success rate: {total_pdfs/len(results)*100:.1f}%")

    print(f"\nBreakdown by status:")
    for status, group in results_df.groupby('status'):
        print(f"  {status:25s}: {len(group):>5,}")

    if cloudflare > 0:
        print(f"\n⚠️  {cloudflare} PDFs blocked by Cloudflare")
        print("   These would need undetected-chromedriver to download")

    if not_found_api > 0:
        print(f"\n⚠️  {not_found_api} species not found in IUCN API")
        print("   These may not have assessments or use different names")

    print(f"\n📂 PDFs saved to: {OUTPUT_DIR}")
    print(f"📄 Log file: {LOG_FILE}")
    print("=" * 80)


if __name__ == "__main__":
    main()
