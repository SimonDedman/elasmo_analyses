#!/usr/bin/env python3
"""
Find duplicate PDFs in the SharkPapers collection - IMPROVED VERSION.

Handles special cases:
1. Reply papers (separate publications, NOT duplicates)
2. Supplementary materials (keep and link to main paper)
3. Errata/Corrections (separate publications, NOT duplicates)
4. Different versions (_v1, _v2)

Strategy:
- Prefer Dropbox naming convention (abbreviated titles)
- Keep reply papers, SM files, corrections as separate
- Remove only true duplicates (same paper, different naming)
"""

import hashlib
from pathlib import Path
from collections import defaultdict
import re
from difflib import SequenceMatcher

# Paths
pdf_base = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")
project_base = Path("/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel")

# Special paper types that are NOT duplicates
SPECIAL_TYPES = {
    'reply': ['reply', 'response to', 'rejoinder'],
    'correction': ['correction', 'corrigendum', 'erratum', 'errata'],
    'supplementary': [' sm.pdf', ' sm ', '_sm.pdf', '_sm_', 'supplementary', 'supplement'],
    'commentary': ['commentary', 'comment on'],
}


def get_file_hash(file_path, block_size=65536):
    """Calculate MD5 hash of file."""
    hasher = hashlib.md5()
    try:
        with open(file_path, 'rb') as f:
            while True:
                data = f.read(block_size)
                if not data:
                    break
                hasher.update(data)
        return hasher.hexdigest()
    except Exception as e:
        print(f"Error hashing {file_path}: {e}")
        return None


def classify_paper_type(filename):
    """
    Classify paper into types: main, reply, correction, supplementary, commentary.

    Returns:
        str: paper type
    """
    filename_lower = filename.lower()

    # Check for supplementary material
    for pattern in SPECIAL_TYPES['supplementary']:
        if pattern in filename_lower:
            return 'supplementary'

    # Check for reply
    for pattern in SPECIAL_TYPES['reply']:
        if pattern in filename_lower:
            return 'reply'

    # Check for correction
    for pattern in SPECIAL_TYPES['correction']:
        if pattern in filename_lower:
            return 'correction'

    # Check for commentary
    for pattern in SPECIAL_TYPES['commentary']:
        if pattern in filename_lower:
            return 'commentary'

    return 'main'


def parse_filename(filename):
    """
    Parse PDF filename into components.

    Returns:
        dict with author, year, title, paper_type
    """
    # Remove .pdf extension
    name = filename.replace('.pdf', '')

    # Classify paper type
    paper_type = classify_paper_type(filename)

    # Split by dots
    parts = name.split('.')

    if len(parts) < 3:
        return None

    # Extract author (first part)
    author = parts[0]

    # Extract year (should be YYYY format)
    year = None
    for part in parts[1:5]:  # Check first few parts
        if re.match(r'^(19|20)\d{2}$', part):
            year = part
            break

    if not year:
        return None

    # Extract title (everything after year)
    year_idx = parts.index(year)
    title_parts = parts[year_idx + 1:]
    title = ' '.join(title_parts)

    return {
        'author': author.lower(),
        'year': year,
        'title': title.lower(),
        'filename': filename,
        'paper_type': paper_type
    }


def title_similarity(title1, title2):
    """Calculate similarity ratio between two titles (0-1)."""
    return SequenceMatcher(None, title1.lower(), title2.lower()).ratio()


def is_abbreviated_title(title):
    """Determine if title looks abbreviated (Dropbox style)."""
    words = title.split()
    abbrev_indicators = ['etal', 'j ', ' j', 'spp', 'var', 'abund']
    has_abbrev = any(indicator in title.lower() for indicator in abbrev_indicators)
    is_short = len(title) < 80
    common_words = sum(1 for w in words if w.lower() in ['of', 'the', 'and', 'in', 'a', 'an', 'for', 'with'])
    has_many_common = common_words >= 3

    if is_short and has_abbrev:
        return True
    elif len(title) < 50:
        return True
    elif len(title) > 100 and has_many_common:
        return False
    else:
        return is_short


def find_duplicates_by_hash():
    """Find exact duplicates by MD5 hash."""
    print("=" * 80)
    print("FINDING EXACT DUPLICATES (by MD5 hash)")
    print("=" * 80)

    hash_map = defaultdict(list)

    all_pdfs = list(pdf_base.glob("*/*.pdf"))
    print(f"\nAnalyzing {len(all_pdfs):,} PDFs...")

    for pdf_path in all_pdfs:
        file_hash = get_file_hash(pdf_path)
        if file_hash:
            hash_map[file_hash].append(pdf_path)

    duplicates = {h: files for h, files in hash_map.items() if len(files) > 1}
    print(f"\nFound {len(duplicates)} sets of exact duplicates")

    return duplicates


def find_duplicates_by_metadata():
    """Find likely duplicates by author/year/similar title."""
    print("\n" + "=" * 80)
    print("FINDING LIKELY DUPLICATES (by author/year/title)")
    print("=" * 80)

    all_pdfs = list(pdf_base.glob("*/*.pdf"))
    parsed = []

    for pdf_path in all_pdfs:
        info = parse_filename(pdf_path.name)
        if info:
            info['path'] = pdf_path
            info['size'] = pdf_path.stat().st_size
            parsed.append(info)

    print(f"\nSuccessfully parsed {len(parsed):,} filenames")

    # Separate by paper type
    by_type = defaultdict(list)
    for item in parsed:
        by_type[item['paper_type']].append(item)

    print(f"\nPaper types:")
    for ptype, items in by_type.items():
        print(f"  {ptype:15s}: {len(items):>4} papers")

    # Group MAIN papers by author + year
    groups = defaultdict(list)
    for item in by_type['main']:
        key = f"{item['author']}_{item['year']}"
        groups[key].append(item)

    # Find duplicates within each group
    likely_duplicates = []

    for key, items in groups.items():
        if len(items) < 2:
            continue

        # Compare all pairs
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                item1 = items[i]
                item2 = items[j]

                # Calculate title similarity
                similarity = title_similarity(item1['title'], item2['title'])

                # Consider duplicates if:
                # - High title similarity (> 0.6) OR
                # - Exact same file size
                if similarity > 0.6 or item1['size'] == item2['size']:
                    likely_duplicates.append({
                        'file1': item1,
                        'file2': item2,
                        'similarity': similarity,
                        'size_match': item1['size'] == item2['size']
                    })

    print(f"\nFound {len(likely_duplicates)} likely duplicate pairs (main papers only)")

    return likely_duplicates, by_type


def create_supplementary_mapping(by_type):
    """
    Create mapping of supplementary materials to main papers.

    Returns:
        dict: {sm_file: main_paper_file}
    """
    print("\n" + "=" * 80)
    print("MAPPING SUPPLEMENTARY MATERIALS TO MAIN PAPERS")
    print("=" * 80)

    sm_mapping = {}

    main_papers = by_type['main']
    sm_papers = by_type['supplementary']

    print(f"\nMain papers: {len(main_papers)}")
    print(f"Supplementary materials: {len(sm_papers)}")

    if len(sm_papers) == 0:
        print("\n✓ No supplementary materials found")
        return sm_mapping

    print(f"\nMatching SM files to main papers...")

    for sm_item in sm_papers:
        # Remove SM indicators from title to match with main paper
        sm_title_clean = sm_item['title']
        for pattern in SPECIAL_TYPES['supplementary']:
            sm_title_clean = sm_title_clean.replace(pattern.strip(), '')
        sm_title_clean = sm_title_clean.strip()

        # Find matching main paper (same author + year + similar title)
        best_match = None
        best_similarity = 0

        for main_item in main_papers:
            if main_item['author'] == sm_item['author'] and main_item['year'] == sm_item['year']:
                similarity = title_similarity(sm_title_clean, main_item['title'])
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = main_item

        if best_match and best_similarity > 0.5:
            sm_mapping[str(sm_item['path'])] = {
                'sm_file': sm_item['path'],
                'main_file': best_match['path'],
                'sm_filename': sm_item['filename'],
                'main_filename': best_match['filename'],
                'similarity': best_similarity
            }
            print(f"  ✓ Matched: {sm_item['filename']}")
            print(f"           → {best_match['filename']}")
            print(f"           (similarity: {best_similarity:.2f})")
        else:
            print(f"  ⚠️  No match: {sm_item['filename']}")

    print(f"\n✓ Mapped {len(sm_mapping)} supplementary files to main papers")

    return sm_mapping


def recommend_removal(duplicates):
    """Recommend which duplicates to remove."""
    print("\n" + "=" * 80)
    print("DUPLICATE REMOVAL RECOMMENDATIONS")
    print("=" * 80)

    recommendations = []

    for dup in duplicates:
        file1 = dup['file1']
        file2 = dup['file2']

        # Determine which is abbreviated (Dropbox) vs full (Sci-Hub)
        title1_abbrev = is_abbreviated_title(file1['title'])
        title2_abbrev = is_abbreviated_title(file2['title'])

        # Decide which to keep
        if title1_abbrev and not title2_abbrev:
            keep = file1
            remove = file2
            reason = "Keep Dropbox naming (abbreviated)"
        elif title2_abbrev and not title1_abbrev:
            keep = file2
            remove = file1
            reason = "Keep Dropbox naming (abbreviated)"
        elif len(file1['title']) < len(file2['title']):
            keep = file1
            remove = file2
            reason = "Keep shorter title (likely abbreviated)"
        else:
            keep = file2
            remove = file1
            reason = "Keep shorter title (likely abbreviated)"

        recommendations.append({
            'keep': keep,
            'remove': remove,
            'reason': reason,
            'similarity': dup['similarity']
        })

    return recommendations


def main():
    print("=" * 80)
    print("PDF DUPLICATE FINDER - IMPROVED")
    print("=" * 80)

    # Find exact duplicates by hash
    hash_duplicates = find_duplicates_by_hash()

    # Find likely duplicates by metadata
    metadata_duplicates, by_type = find_duplicates_by_metadata()

    # Create supplementary material mapping
    sm_mapping = create_supplementary_mapping(by_type)

    # Generate recommendations
    if metadata_duplicates:
        recommendations = recommend_removal(metadata_duplicates)

        print(f"\nShowing top 30 duplicate pairs (MAIN papers only):")
        print()

        for idx, rec in enumerate(recommendations[:30], 1):
            keep = rec['keep']
            remove = rec['remove']

            print(f"{idx}. KEEP:   {keep['filename']}")
            print(f"   REMOVE: {remove['filename']}")
            print(f"   Reason: {rec['reason']} (similarity: {rec['similarity']:.2f})")
            print()

        # Save recommendations to CSV
        import pandas as pd

        df_data = []
        for rec in recommendations:
            df_data.append({
                'keep_file': str(rec['keep']['path']),
                'remove_file': str(rec['remove']['path']),
                'keep_filename': rec['keep']['filename'],
                'remove_filename': rec['remove']['filename'],
                'similarity': rec['similarity'],
                'reason': rec['reason'],
                'size_match': rec['keep']['size'] == rec['remove']['size'],
                'keep_size': rec['keep']['size'],
                'remove_size': rec['remove']['size']
            })

        df = pd.DataFrame(df_data)
        output_csv = project_base / "outputs/duplicate_pdfs_to_remove.csv"
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_csv, index=False)

        # Save SM mapping
        if sm_mapping:
            sm_data = []
            for sm_path, mapping in sm_mapping.items():
                sm_data.append({
                    'sm_file': str(mapping['sm_file']),
                    'main_file': str(mapping['main_file']),
                    'sm_filename': mapping['sm_filename'],
                    'main_filename': mapping['main_filename'],
                    'similarity': mapping['similarity']
                })

            df_sm = pd.DataFrame(sm_data)
            sm_csv = project_base / "outputs/supplementary_materials_mapping.csv"
            df_sm.to_csv(sm_csv, index=False)
            print(f"\n✓ SM mapping saved to: {sm_csv}")

        print("=" * 80)
        print(f"SUMMARY")
        print("=" * 80)
        print(f"\nDuplicate pairs found: {len(recommendations)}")
        print(f"Supplementary materials: {len(sm_mapping)}")
        print(f"Reply papers: {len(by_type['reply'])}")
        print(f"Corrections: {len(by_type['correction'])}")
        print(f"Commentaries: {len(by_type['commentary'])}")
        print(f"\nRecommendations saved to: {output_csv}")
        print()
        print("Next steps:")
        print("  1. Review: cat outputs/duplicate_pdfs_to_remove.csv")
        print("  2. Review SM mapping: cat outputs/supplementary_materials_mapping.csv")
        print("  3. Remove duplicates: Use remove_duplicate_pdfs.py script")

    else:
        print("\n✓ No duplicates found!")


if __name__ == "__main__":
    main()
