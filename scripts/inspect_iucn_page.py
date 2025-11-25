#!/usr/bin/env python3
"""
inspect_iucn_page.py

Diagnostic script to inspect actual IUCN Red List page structure.
Helps understand what selectors and PDF locations are available.

Usage:
    ./venv/bin/python scripts/inspect_iucn_page.py "Carcharodon carcharias"
"""

import sys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
import time
import re

def inspect_species_page(genus: str, species: str):
    """Inspect an IUCN species page to understand structure."""

    # Setup browser
    options = ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    species_name = f"{genus} {species}"

    print("=" * 80)
    print(f"INSPECTING IUCN PAGE: {species_name}")
    print("=" * 80)

    try:
        # Try multiple URL patterns
        urls_to_try = [
            f"https://www.iucnredlist.org/species/{genus.lower()}-{species.lower()}",
            f"https://www.iucnredlist.org/species/{genus.capitalize()}-{species.lower()}",
            f"https://www.iucnredlist.org/search?query={genus}+{species}"
        ]

        for url in urls_to_try:
            print(f"\n{'=' * 80}")
            print(f"URL: {url}")
            print("=" * 80)

            driver.get(url)
            time.sleep(3)  # Wait for page load

            # Check for 404 or error
            if "404" in driver.title or "Not Found" in driver.title:
                print("❌ Page not found (404)")
                continue

            print(f"✅ Page title: {driver.page_source[:200]}")

            # Get page source
            page_source = driver.page_source

            # Look for PDF links
            print("\n" + "-" * 80)
            print("PDF LINKS FOUND:")
            print("-" * 80)
            pdf_matches = re.findall(r'href="([^"]*\.pdf[^"]*)"', page_source, re.IGNORECASE)
            if pdf_matches:
                for i, pdf_url in enumerate(pdf_matches[:5], 1):
                    print(f"  {i}. {pdf_url}")
            else:
                print("  No .pdf links found in page source")

            # Look for download buttons/links
            print("\n" + "-" * 80)
            print("DOWNLOAD-RELATED ELEMENTS:")
            print("-" * 80)
            download_matches = re.findall(r'<a[^>]*download[^>]*>.*?</a>', page_source, re.IGNORECASE)
            if download_matches:
                for i, match in enumerate(download_matches[:5], 1):
                    print(f"  {i}. {match[:200]}")
            else:
                print("  No download links found")

            # Look for "assessment" links
            print("\n" + "-" * 80)
            print("ASSESSMENT-RELATED LINKS:")
            print("-" * 80)
            assessment_matches = re.findall(r'<a[^>]*assessment[^>]*href="([^"]+)"', page_source, re.IGNORECASE)
            if assessment_matches:
                for i, match in enumerate(assessment_matches[:5], 1):
                    print(f"  {i}. {match}")
            else:
                print("  No assessment links found")

            # Check if it's a search results page
            if "search" in url:
                print("\n" + "-" * 80)
                print("SEARCH RESULTS:")
                print("-" * 80)
                # Look for species result links
                species_links = re.findall(r'href="(/species/[^"]+)"', page_source)
                if species_links:
                    print(f"  Found {len(species_links)} species links:")
                    for i, link in enumerate(species_links[:3], 1):
                        full_url = f"https://www.iucnredlist.org{link}"
                        print(f"    {i}. {full_url}")

                    # Try first result
                    if species_links:
                        first_result = f"https://www.iucnredlist.org{species_links[0]}"
                        print(f"\n  Trying first result: {first_result}")
                        driver.get(first_result)
                        time.sleep(3)

                        # Re-check for PDFs on species page
                        page_source = driver.page_source
                        pdf_matches = re.findall(r'href="([^"]*\.pdf[^"]*)"', page_source, re.IGNORECASE)
                        if pdf_matches:
                            print(f"  ✅ PDFs found on species page:")
                            for i, pdf_url in enumerate(pdf_matches[:5], 1):
                                print(f"    {i}. {pdf_url}")
                        else:
                            print("  ❌ No PDFs found on species page")

                        # Save page source to file for inspection
                        with open("/tmp/iucn_species_page.html", "w") as f:
                            f.write(page_source)
                        print(f"\n  💾 Full page source saved to: /tmp/iucn_species_page.html")

                        return  # Success, stop trying other URLs

    except Exception as e:
        print(f"\n❌ ERROR: {e}")

    finally:
        driver.quit()

    print("\n" + "=" * 80)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: ./venv/bin/python scripts/inspect_iucn_page.py 'Genus species'")
        print("Example: ./venv/bin/python scripts/inspect_iucn_page.py 'Carcharodon carcharias'")
        sys.exit(1)

    species_full = sys.argv[1]
    parts = species_full.split()

    if len(parts) != 2:
        print("Error: Please provide species name as 'Genus species'")
        sys.exit(1)

    genus, species = parts
    inspect_species_page(genus, species)
