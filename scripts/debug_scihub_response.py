#!/usr/bin/env python3
"""
debug_scihub_response.py

Debug script to see what Sci-Hub actually returns for test DOIs.
"""

import requests
import sys
from pathlib import Path

# Test DOIs from our database
TEST_DOIS = [
    "10.1111/joa.14278",  # 2025
    "10.1007/s10641-020-01025-z",  # 2020
    "10.1578/am.46.3.2020.254",  # 2020
]

SCIHUB_MIRROR = "https://sci-hub.st"
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

print("=" * 80)
print("SCI-HUB DEBUG - Checking actual responses")
print("=" * 80)

for doi in TEST_DOIS:
    print(f"\n{'=' * 80}")
    print(f"Testing DOI: {doi}")
    print(f"{'=' * 80}")

    # Construct URL
    doi_url = f"http://dx.doi.org/{doi}"
    scihub_url = f"{SCIHUB_MIRROR}/{doi_url}"

    print(f"URL: {scihub_url}")

    try:
        headers = {
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }

        response = requests.get(scihub_url, headers=headers, timeout=30, allow_redirects=True)

        print(f"Status Code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type', 'unknown')}")
        print(f"Final URL: {response.url}")
        print(f"Response Length: {len(response.text)} chars")

        # Check for common indicators
        indicators = {
            'Статья отсутствует в базе': 'Article missing (Russian)',
            'article not found': 'Article not found (English)',
            'Article is not found': 'Article not found (capitalized)',
            '.pdf': 'PDF mentioned',
            '<iframe': 'Iframe (potential PDF embed)',
            '<embed': 'Embed tag',
            'location.href': 'JavaScript redirect',
        }

        print(f"\nContent Analysis:")
        for phrase, description in indicators.items():
            if phrase in response.text:
                print(f"  ✅ FOUND: {description} ({phrase})")
            else:
                print(f"  ❌ NOT FOUND: {description}")

        # Save HTML to file for inspection
        output_file = Path(f"/tmp/scihub_debug_{doi.replace('/', '_')}.html")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(response.text)
        print(f"\n💾 Full HTML saved to: {output_file}")

        # Show first 500 chars
        print(f"\nFirst 500 characters of response:")
        print("-" * 80)
        print(response.text[:500])
        print("-" * 80)

    except Exception as e:
        print(f"❌ Error: {e}")

print(f"\n{'=' * 80}")
print("DEBUG COMPLETE")
print(f"{'=' * 80}")
print("\nReview the saved HTML files in /tmp/ to see actual Sci-Hub responses")
