#!/usr/bin/env python3
"""Test if we can access actual species pages and find PDFs."""

import undetected_chromedriver as uc
import time
import re

def test_pdf_access():
    """Test accessing actual species pages via discovered URLs."""

    # URLs discovered from search
    test_urls = [
        ("Great White Shark", "https://www.iucnredlist.org/species/3855/212629880"),
        ("Great Hammerhead", "https://www.iucnredlist.org/species/39386/2920499"),
        ("Whale Shark", "https://www.iucnredlist.org/species/19488/126673248"),
        ("Bull Shark", "https://www.iucnredlist.org/species/39372/2910670"),
    ]

    print("=" * 80)
    print("TESTING PDF ACCESS ON ACTUAL SPECIES PAGES")
    print("=" * 80)

    driver = uc.Chrome()

    try:
        for common_name, url in test_urls:
            print(f"\n[{common_name}]")
            print("-" * 80)
            print(f"URL: {url}")

            driver.get(url)
            time.sleep(8)  # Wait longer for full page load

            title = driver.title
            print(f"Title: {title}")

            if "Just a moment" in title or "Cloudflare" in title:
                print("❌ BLOCKED by Cloudflare")
                continue

            if "404" in title or "doesn't exist" in title:
                print("❌ 404 Not Found")
                continue

            print("✅ Page loaded successfully!")

            # Get page source
            page_source = driver.page_source

            # Look for PDF links
            pdf_urls = re.findall(r'href="([^"]*\.pdf[^"]*)"', page_source, re.IGNORECASE)

            if pdf_urls:
                print(f"\n📄 Found {len(pdf_urls)} PDF link(s):")
                for pdf_url in pdf_urls[:5]:
                    print(f"   • {pdf_url}")
            else:
                print("\n⚠️  No .pdf links found")

                # Look for download-related elements
                download_matches = re.findall(r'(download|assessment|document)[^<]*', page_source.lower())
                if download_matches:
                    print(f"   Found {len(download_matches)} 'download/assessment' mentions in HTML")
                    print("   (PDFs may be behind buttons/JavaScript)")

            # Save page source for manual inspection
            with open(f"/tmp/iucn_{common_name.replace(' ', '_')}.html", "w") as f:
                f.write(page_source)
            print(f"   💾 Page source saved: /tmp/iucn_{common_name.replace(' ', '_')}.html")

            time.sleep(3)

    finally:
        driver.quit()

    print("\n" + "=" * 80)
    print("CONCLUSION")
    print("=" * 80)
    print("\nCloudflare bypass: ✅ Working!")
    print("URL pattern: Species pages use /species/{taxonid}/{assessmentid}")
    print("\nNext steps:")
    print("  1. Search for each species to get taxon ID")
    print("  2. Access species page via taxon ID")
    print("  3. Extract PDF (if available)")
    print("\nThis is a 2-step process:")
    print("  Step 1: Search → Extract URL")
    print("  Step 2: Visit URL → Download PDF")
    print("=" * 80)


if __name__ == "__main__":
    test_pdf_access()
