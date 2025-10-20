#!/usr/bin/env python3
"""
Test different search operators on shark-references.com to understand how they work.
This helps us determine if the + operator actually functions as "required term" or not.
"""

import requests
from bs4 import BeautifulSoup
import json

def test_query(query, description=""):
    """Test a single query and show results"""
    url = 'https://shark-references.com/index.php/search/search'
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'X-Requested-With': 'XMLHttpRequest'
    }

    data = {'query_fulltext': query, 'page': 0}

    print(f"\n{'='*80}")
    if description:
        print(f"TEST: {description}")
    print(f"Query: '{query}'")
    print('-' * 80)

    try:
        response = requests.post(url, data=data, headers=headers, timeout=30)
        json_data = response.json()

        total_results = int(json_data.get('itemCount', 0))
        print(f"Total results: {total_results}")

        if total_results == 0:
            print("❌ No results found")
            return

        # Parse first 3 results
        soup = BeautifulSoup(json_data['results'], 'html.parser')
        entries = soup.find_all('div', class_='list-entry')[:3]

        print(f"\nFirst {len(entries)} results:")
        for i, entry in enumerate(entries, 1):
            text = entry.get_text(separator=' ', strip=True)
            text_lower = text.lower()

            # Check which terms are present
            has_acoustic = 'acoustic' in text_lower
            has_telemetry = 'telemetry' in text_lower
            has_shark = 'shark' in text_lower

            print(f"\n  [{i}] {text[:200]}...")
            print(f"      Contains 'acoustic': {has_acoustic}")
            print(f"      Contains 'telemetry': {has_telemetry}")
            print(f"      Contains 'shark': {has_shark}")

    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    """Test various search operators"""

    print("=" * 80)
    print("SHARK-REFERENCES.COM SEARCH OPERATOR TEST")
    print("=" * 80)
    print("\nThis script tests how different search operators actually work on the website.")
    print("We'll test with terms 'acoustic' and 'telemetry'")

    # Test 1: Plus operator (supposedly means "required")
    test_query(
        "+acoustic +telemetry",
        "Plus operator - supposedly means both terms REQUIRED"
    )

    # Test 2: Just two terms
    test_query(
        "acoustic telemetry",
        "Two terms without operators - OR behavior expected"
    )

    # Test 3: Quoted phrase
    test_query(
        '"acoustic telemetry"',
        "Quoted phrase - exact phrase match"
    )

    # Test 4: AND operator
    test_query(
        "acoustic AND telemetry",
        "AND operator - explicit AND"
    )

    # Test 5: Single term to verify search works
    test_query(
        "acoustic",
        "Single term - baseline test"
    )

    # Test 6: Check if shark is required (all papers should have it)
    test_query(
        "+shark +acoustic +telemetry",
        "Three required terms - should all contain shark, acoustic, telemetry"
    )

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("""
Based on the results above, you can see:

1. If results for '+acoustic +telemetry' do NOT all contain both terms
   → The + operator is BROKEN and we MUST filter client-side

2. If results DO all contain both terms
   → The + operator WORKS and we can remove our filtering

3. Check the result counts:
   - If '+acoustic +telemetry' has FEWER results than 'acoustic telemetry'
     → The + operator might be working
   - If they have the SAME or MORE results
     → The + operator is definitely broken
    """)

if __name__ == '__main__':
    main()
