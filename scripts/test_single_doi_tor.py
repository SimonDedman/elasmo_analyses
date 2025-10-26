#!/usr/bin/env python3
"""
test_single_doi_tor.py

Test single DOI download via Tor to verify setup is working.

Usage:
    python3 test_single_doi_tor.py 10.1242/jeb.059667

Author: Simon Dedman / Claude
Date: 2025-10-23
"""

import sys
import socks
import socket
import requests
from bs4 import BeautifulSoup
import time

def setup_tor():
    """Setup Tor proxy."""
    try:
        socks.set_default_proxy(socks.SOCKS5, "localhost", 9050)
        socket.socket = socks.socksocket
        return True
    except Exception as e:
        print(f"❌ Failed to setup Tor: {e}")
        return False

def test_connection():
    """Test Tor connection."""
    try:
        response = requests.get("https://api.ipify.org?format=json", timeout=30)
        ip = response.json()['ip']
        print(f"✅ Connected via Tor - IP: {ip}")
        return True
    except Exception as e:
        print(f"❌ Tor connection failed: {e}")
        return False

def test_doi(doi, mirror="https://sci-hub.se"):
    """Test downloading a single DOI."""
    url = f"{mirror}/{doi}"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    print(f"\n{'='*80}")
    print(f"Testing DOI: {doi}")
    print(f"Sci-Hub URL: {url}")
    print(f"{'='*80}\n")

    try:
        print("⏳ Requesting page...")
        response = requests.get(url, headers=headers, timeout=45)

        print(f"✅ Response received")
        print(f"   Status: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('Content-Type', 'N/A')}")
        print(f"   Content-Length: {len(response.content):,} bytes")

        # Check if PDF
        if response.content[:4] == b'%PDF':
            print(f"\n🎉 SUCCESS! Got PDF directly")
            print(f"   PDF size: {len(response.content):,} bytes")
            return True

        # Check for error
        if len(response.content) < 100:
            print(f"\n❌ FAILED: Short response")
            print(f"   Response: {response.text}")
            return False

        # Parse HTML
        print(f"\n📄 Got HTML page, looking for PDF link...")
        soup = BeautifulSoup(response.text, 'html.parser')

        # Check for "not found"
        if 'not found' in response.text.lower()[:1000]:
            print(f"❌ Paper not found in Sci-Hub")
            return False

        # Look for PDF embed
        embed_tag = soup.find('embed', {'type': 'application/pdf'})
        if embed_tag and embed_tag.get('src'):
            pdf_url = embed_tag['src']
            if pdf_url.startswith('//'):
                pdf_url = f"https:{pdf_url}"
            print(f"✅ Found PDF embed: {pdf_url[:80]}...")

            # Download PDF
            print(f"⏳ Downloading PDF...")
            time.sleep(1)
            pdf_response = requests.get(pdf_url, headers=headers, timeout=45)

            if pdf_response.content[:4] == b'%PDF':
                print(f"\n🎉 SUCCESS! Downloaded PDF")
                print(f"   PDF size: {len(pdf_response.content):,} bytes")
                return True
            else:
                print(f"❌ Downloaded file is not a PDF")
                return False

        # Look for iframe
        iframe_tag = soup.find('iframe', src=lambda x: x and '.pdf' in x)
        if iframe_tag:
            print(f"✅ Found iframe with PDF")
            return True

        # Look for button
        button = soup.find('button', id='save')
        if button:
            print(f"✅ Found save button (would need JavaScript execution)")
            print(f"   onclick: {button.get('onclick', 'N/A')[:80]}...")
            return False  # Can't execute JS in this test

        print(f"\n❌ Could not find PDF link in page")
        print(f"\nFirst 500 chars of HTML:")
        print(response.text[:500])
        return False

    except requests.exceptions.Timeout:
        print(f"❌ Request timed out")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 test_single_doi_tor.py DOI")
        print("Example: python3 test_single_doi_tor.py 10.1242/jeb.059667")
        sys.exit(1)

    doi = sys.argv[1]

    print("\n" + "="*80)
    print("TOR + SCI-HUB TEST")
    print("="*80)

    # Setup Tor
    print("\n1. Setting up Tor proxy...")
    if not setup_tor():
        print("\n❌ Tor setup failed")
        print("Make sure Tor is running: sudo systemctl status tor")
        sys.exit(1)

    # Test connection
    print("\n2. Testing Tor connection...")
    if not test_connection():
        print("\n❌ Tor not working")
        sys.exit(1)

    # Test Sci-Hub
    print("\n3. Testing Sci-Hub access...")
    mirrors = ["https://sci-hub.se", "https://sci-hub.ru", "https://sci-hub.wf"]

    for mirror in mirrors:
        print(f"\n{'='*80}")
        print(f"Trying mirror: {mirror}")
        print(f"{'='*80}")

        success = test_doi(doi, mirror)

        if success:
            print(f"\n{'='*80}")
            print(f"✅ SUCCESS with mirror: {mirror}")
            print(f"{'='*80}")
            print(f"\nRecommendation: Use this mirror for bulk download")
            print(f"Command: python3 scripts/download_via_scihub_tor.py --mirror {mirrors.index(mirror)}")
            break

        time.sleep(3)
    else:
        print(f"\n{'='*80}")
        print(f"❌ All mirrors failed")
        print(f"{'='*80}")
        print(f"\nPossible issues:")
        print(f"  1. Sci-Hub is blocking Tor exit nodes")
        print(f"  2. Paper not available in Sci-Hub")
        print(f"  3. Need to rotate Tor identity")
        print(f"\nTry:")
        print(f"  - Restart Tor: sudo systemctl restart tor")
        print(f"  - Different DOI: python3 test_single_doi_tor.py 10.1038/s41598-018-38270-3")
        print(f"  - Check Tor logs: sudo journalctl -u tor -n 50")

if __name__ == "__main__":
    main()
