#!/usr/bin/env python3
"""
test_iucn_access.py

Test whether the IUCN Red List site can be reached by an automated browser.

This script attempts to load 10 IUCN species pages with a Playwright browser and
counts how many are served normally and how many hit a Cloudflare challenge page.

Browser layer (21 Oct 2026, licence): it now uses Playwright through
scripts/lib/browser.py instead of undetected-chromedriver (GPL-3.0). Playwright must
be installed first (pip install playwright; python -m playwright install chromium).
It no longer attempts to evade bot detection. Sites that block automated browsers
(e.g. Cloudflare challenges) will block it; fetch those papers by hand or through an
approved route. The file name is kept for existing references.

Author: Simon Dedman / Claude
Date: 2025-11-17
"""

import pandas as pd
from pathlib import Path
import time
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.browser import launch_driver, playwright_available, INSTALL_HINT

BASE_DIR = Path(__file__).parent.parent
INPUT_FILE = BASE_DIR / "outputs/iucn_species_cleaned.csv"

def test_cloudflare_bypass():
    """Test whether an automated browser is served normally by the IUCN website."""

    print("=" * 80)
    print("IUCN AUTOMATED-BROWSER ACCESS TEST")
    print("=" * 80)
    print("\nTesting a Playwright browser on IUCN Red List website...")

    # Load test species
    df = pd.read_csv(INPUT_FILE)
    test_species = df.head(10)

    print(f"\nTest species:")
    for idx, row in test_species.iterrows():
        print(f"  {idx+1}. {row['species_name']} ({row['year']})")

    # Initialise Playwright browser
    print("\n" + "-" * 80)
    print("Initialising Playwright browser...")
    print("-" * 80)

    if not playwright_available():
        raise RuntimeError(INSTALL_HINT)

    # Don't use headless for first test - easier to debug
    driver = launch_driver(headless=False)

    results = []

    try:
        for idx, row in test_species.iterrows():
            genus = row['genus']
            species = row['species']
            species_name = f"{genus} {species}"

            print(f"\n[{idx+1}/10] Testing: {species_name}")
            print("-" * 80)

            # Try direct species page
            url = f"https://www.iucnredlist.org/species/{genus.lower()}-{species.lower()}"
            print(f"URL: {url}")

            try:
                driver.get(url)
                time.sleep(5)  # Wait for page load

                # Check page title
                title = driver.title
                print(f"Page title: {title}")

                # Check if we got through Cloudflare
                if "Just a moment" in title or "Cloudflare" in title:
                    print("❌ BLOCKED: Cloudflare challenge page")
                    results.append({
                        'species': species_name,
                        'url': url,
                        'status': 'blocked',
                        'title': title
                    })
                    continue

                # Check for 404
                if "404" in title or "Not Found" in title:
                    print("⚠️  404: Species page not found")
                    results.append({
                        'species': species_name,
                        'url': url,
                        'status': '404',
                        'title': title
                    })
                    continue

                # Success! Check for PDF
                print("✅ SUCCESS: Page served normally (no Cloudflare challenge)")

                # Look for PDF links
                page_source = driver.page_source
                pdf_urls = re.findall(r'href="([^"]*\.pdf[^"]*)"', page_source, re.IGNORECASE)

                if pdf_urls:
                    print(f"📄 Found {len(pdf_urls)} PDF link(s):")
                    for pdf_url in pdf_urls[:3]:
                        print(f"   • {pdf_url}")
                    results.append({
                        'species': species_name,
                        'url': url,
                        'status': 'success_with_pdf',
                        'title': title,
                        'pdf_count': len(pdf_urls)
                    })
                else:
                    print("⚠️  No PDF links found on page")
                    results.append({
                        'species': species_name,
                        'url': url,
                        'status': 'success_no_pdf',
                        'title': title,
                        'pdf_count': 0
                    })

            except Exception as e:
                print(f"❌ ERROR: {e}")
                results.append({
                    'species': species_name,
                    'url': url,
                    'status': 'error',
                    'error': str(e)
                })

            # Respectful delay
            time.sleep(3)

    finally:
        print("\n" + "-" * 80)
        print("Closing browser...")
        driver.quit()

    # Summary
    print("\n" + "=" * 80)
    print("TEST RESULTS SUMMARY")
    print("=" * 80)

    results_df = pd.DataFrame(results)

    blocked = len(results_df[results_df['status'] == 'blocked'])
    success_with_pdf = len(results_df[results_df['status'] == 'success_with_pdf'])
    success_no_pdf = len(results_df[results_df['status'] == 'success_no_pdf'])
    not_found = len(results_df[results_df['status'] == '404'])
    errors = len(results_df[results_df['status'] == 'error'])

    total_success = success_with_pdf + success_no_pdf

    print(f"\nTotal tested: {len(results_df)}")
    print(f"\n✅ Served normally: {total_success}/{len(results_df)}")
    print(f"   • With PDF links: {success_with_pdf}")
    print(f"   • Without PDF links: {success_no_pdf}")
    print(f"\n❌ Blocked by Cloudflare: {blocked}/{len(results_df)}")
    print(f"⚠️  404 Not Found: {not_found}/{len(results_df)}")
    print(f"❌ Errors: {errors}/{len(results_df)}")

    # Verdict
    print("\n" + "=" * 80)
    print("VERDICT")
    print("=" * 80)

    access_rate = (total_success / len(results_df)) * 100 if len(results_df) > 0 else 0

    if access_rate >= 80:
        print(f"\n🎉 SUCCESS! Access rate: {access_rate:.1f}%")
        print("\n✅ Recommendation: pages are being served; a full scraper run may be worthwhile")
        print(f"   Expected yield: {int(1098 * access_rate / 100)} PDFs")
    elif access_rate >= 50:
        print(f"\n⚠️  PARTIAL SUCCESS! Access rate: {access_rate:.1f}%")
        print("\n   May be worth running full scraper, but results will be incomplete")
        print(f"   Expected yield: {int(1098 * access_rate / 100)} PDFs")
    elif access_rate > 0:
        print(f"\n❌ LOW SUCCESS! Access rate: {access_rate:.1f}%")
        print("\n   Not recommended to run full scraper")
        print("   Consider alternative approaches (Google Scholar, API metadata)")
    else:
        print(f"\n❌ FAILED! Access rate: 0%")
        print("\n   Cloudflare blocking is too strong")
        print("   Recommend: Defer IUCN individual assessments")
        print("   Already have: 62 regional reports from SSG website")

    print("\n" + "=" * 80)

    return results_df


if __name__ == "__main__":
    test_cloudflare_bypass()
