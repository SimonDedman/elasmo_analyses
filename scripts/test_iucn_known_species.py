#!/usr/bin/env python3
"""Test bypass with well-known species."""

import undetected_chromedriver as uc
import time
import re

def test_known_species():
    """Test with species we know exist on IUCN."""

    # Well-known species that definitely have IUCN pages
    test_species = [
        ("Carcharodon", "carcharias", "Great White Shark"),
        ("Sphyrna", "mokarran", "Great Hammerhead"),
        ("Rhincodon", "typus", "Whale Shark"),
        ("Pristis", "pristis", "Common Sawfish"),
        ("Carcharhinus", "leucas", "Bull Shark"),
    ]

    print("=" * 80)
    print("TESTING KNOWN SPECIES")
    print("=" * 80)

    driver = uc.Chrome()

    try:
        for genus, species, common_name in test_species:
            print(f"\n[Testing: {common_name}] {genus} {species}")
            print("-" * 80)

            url = f"https://www.iucnredlist.org/species/{genus.lower()}-{species.lower()}"
            print(f"URL: {url}")

            driver.get(url)
            time.sleep(5)

            title = driver.title
            print(f"Title: {title}")

            if "Just a moment" in title or "Cloudflare" in title:
                print("❌ BLOCKED by Cloudflare")
            elif "404" in title or "doesn't exist" in title:
                print("⚠️  404 - trying search...")

                # Try search instead
                search_url = f"https://www.iucnredlist.org/search?query={genus}+{species}"
                print(f"Search URL: {search_url}")
                driver.get(search_url)
                time.sleep(5)

                search_title = driver.title
                print(f"Search title: {search_title}")

                if "Just a moment" in search_title:
                    print("❌ Search BLOCKED")
                else:
                    print("✅ Search worked!")
                    # Look for species links
                    page_source = driver.page_source
                    species_links = re.findall(r'href="(/species/[^"]+)"', page_source)
                    if species_links:
                        print(f"   Found {len(species_links)} species links:")
                        for link in species_links[:3]:
                            print(f"     • https://www.iucnredlist.org{link}")
            else:
                print("✅ SUCCESS! Page loaded")
                # Look for PDFs
                page_source = driver.page_source
                pdf_urls = re.findall(r'href="([^"]*\.pdf[^"]*)"', page_source, re.IGNORECASE)
                if pdf_urls:
                    print(f"   📄 Found {len(pdf_urls)} PDF link(s)")
                else:
                    print("   No PDFs found")

            time.sleep(3)

    finally:
        driver.quit()

    print("\n" + "=" * 80)


if __name__ == "__main__":
    test_known_species()
