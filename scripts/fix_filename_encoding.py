#!/usr/bin/env python3
"""
Fix character encoding issues in PDF filenames.

Common issues:
- Ã© → é (French e with acute)
- Ã¤ → ä (German a with umlaut)
- Ã¼ → ü (German u with umlaut)
- Ã¶ → ö (German o with umlaut)
- â€™ → ' (apostrophe)
- Ã¨ → è (e with grave)

These occur when UTF-8 characters are incorrectly interpreted as Latin-1.
"""

import os
from pathlib import Path
import unicodedata

pdf_base = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")

# Common UTF-8 mojibake patterns (incorrectly decoded as Latin-1)
ENCODING_FIXES = {
    'Ã©': 'é',  # e-acute
    'Ã¨': 'è',  # e-grave
    'Ã¤': 'ä',  # a-umlaut
    'Ã¼': 'ü',  # u-umlaut
    'Ã¶': 'ö',  # o-umlaut
    'Ã ': 'à',  # a-grave
    'Ã§': 'ç',  # c-cedilla
    'Ã¯': 'ï',  # i-diaeresis
    'â€™': "'",  # apostrophe
    'â€"': '—',  # em dash
    'â€"': '–',  # en dash
    'â€œ': '"',  # left double quote
    'â€': '"',  # right double quote
    'Ã': 'É',   # E-acute (capital)
}


def fix_encoding(text):
    """Fix mojibake in text."""
    for wrong, correct in ENCODING_FIXES.items():
        text = text.replace(wrong, correct)
    return text


def is_safe_rename(old_path, new_path):
    """Check if rename is safe (target doesn't exist)."""
    return not new_path.exists()


def main():
    print("=" * 80)
    print("FIXING FILENAME ENCODING ISSUES")
    print("=" * 80)

    # Find all PDFs
    all_pdfs = list(pdf_base.glob("*/*.pdf"))
    print(f"\nScanning {len(all_pdfs):,} PDFs...")

    # Find files with encoding issues
    problem_files = []

    for pdf_path in all_pdfs:
        filename = pdf_path.name

        # Check if filename contains mojibake patterns
        has_issue = any(pattern in filename for pattern in ENCODING_FIXES.keys())

        if has_issue:
            problem_files.append(pdf_path)

    print(f"\nFound {len(problem_files)} files with encoding issues")

    if len(problem_files) == 0:
        print("\n✓ No files need fixing!")
        return

    # Show problematic files
    print("\nFiles with encoding issues:")
    print()

    for idx, pdf_path in enumerate(problem_files[:20], 1):
        fixed_name = fix_encoding(pdf_path.name)
        print(f"{idx}. Original: {pdf_path.name}")
        print(f"   Fixed:    {fixed_name}")
        print()

    if len(problem_files) > 20:
        print(f"   ... and {len(problem_files) - 20} more")

    # Ask for confirmation
    print("\n" + "=" * 80)
    print("RENAME FILES?")
    print("=" * 80)
    print(f"\nThis will rename {len(problem_files)} files")
    print("Original filenames will be lost!")
    print()

    response = input("Type 'RENAME' to proceed: ")

    if response != 'RENAME':
        print("\n❌ Cancelled - no files renamed")
        return

    # Rename files
    print("\n🔄 Renaming files...")

    renamed_count = 0
    failed_count = 0
    skipped_count = 0

    for pdf_path in problem_files:
        old_name = pdf_path.name
        new_name = fix_encoding(old_name)
        new_path = pdf_path.parent / new_name

        # Check if safe
        if not is_safe_rename(pdf_path, new_path):
            print(f"⚠️  Skip (target exists): {old_name} → {new_name}")
            skipped_count += 1
            continue

        # Rename
        try:
            pdf_path.rename(new_path)
            renamed_count += 1

            if renamed_count % 10 == 0:
                print(f"  Progress: {renamed_count}/{len(problem_files)}")

        except Exception as e:
            print(f"❌ Failed: {old_name}")
            print(f"   Error: {e}")
            failed_count += 1

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"\nRenamed: {renamed_count}")
    print(f"Skipped: {skipped_count} (target exists)")
    print(f"Failed: {failed_count}")

    print("\n✓ Complete!")


if __name__ == "__main__":
    main()
