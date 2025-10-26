#!/usr/bin/env python3
"""
Consolidate YYYY and YYYY.0 folders in SharkPapers directory.

This script:
1. Finds all YYYY.0 folders
2. Checks if corresponding YYYY folder exists
3. Moves PDFs from YYYY.0 to YYYY (or renames if YYYY doesn't exist)
4. Removes empty YYYY.0 folders
5. Logs all actions for review
"""

import os
import shutil
from pathlib import Path
from datetime import datetime

# Base directory
base_dir = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")
log_file = Path("logs/folder_consolidation_log.txt")

def consolidate_folders():
    """Consolidate YYYY.0 folders into YYYY folders."""

    actions = []
    errors = []

    # Create log directory if needed
    log_file.parent.mkdir(exist_ok=True)

    # Find all YYYY.0 folders
    decimal_folders = sorted([f for f in base_dir.iterdir() if f.is_dir() and f.name.endswith('.0')])

    print(f"Found {len(decimal_folders)} folders with '.0' suffix")
    print("=" * 80)

    for decimal_folder in decimal_folders:
        year_with_decimal = decimal_folder.name  # e.g., "2021.0"
        year_clean = year_with_decimal.replace('.0', '')  # e.g., "2021"
        clean_folder = base_dir / year_clean

        # Count PDFs in decimal folder
        pdf_files = list(decimal_folder.glob("*.pdf"))
        pdf_count = len(pdf_files)

        if pdf_count == 0:
            print(f"\n{year_with_decimal}: No PDFs, will remove empty folder")
            actions.append(f"REMOVE_EMPTY: {year_with_decimal} (0 PDFs)")
            try:
                decimal_folder.rmdir()
                print(f"  ✓ Removed empty folder")
            except Exception as e:
                errors.append(f"ERROR removing {year_with_decimal}: {e}")
                print(f"  ✗ Error: {e}")
            continue

        # Check if clean folder exists
        if clean_folder.exists():
            # Move PDFs from YYYY.0 to YYYY
            print(f"\n{year_with_decimal} → {year_clean}: Moving {pdf_count} PDFs")
            actions.append(f"MERGE: {year_with_decimal} → {year_clean} ({pdf_count} PDFs)")

            moved = 0
            skipped = 0

            for pdf in pdf_files:
                target = clean_folder / pdf.name

                # Check if file already exists in target
                if target.exists():
                    # Check if they're the same file
                    if pdf.stat().st_size == target.stat().st_size:
                        skipped += 1
                        pdf.unlink()  # Remove duplicate
                    else:
                        # Different files with same name - rename with suffix
                        suffix = 1
                        while target.exists():
                            stem = pdf.stem
                            target = clean_folder / f"{stem}_dup{suffix}.pdf"
                            suffix += 1
                        shutil.move(str(pdf), str(target))
                        moved += 1
                else:
                    shutil.move(str(pdf), str(target))
                    moved += 1

            print(f"  ✓ Moved: {moved}, Skipped duplicates: {skipped}")

            # Remove empty decimal folder
            try:
                decimal_folder.rmdir()
                print(f"  ✓ Removed {year_with_decimal} folder")
            except Exception as e:
                errors.append(f"ERROR removing {year_with_decimal}: {e}")
                print(f"  ✗ Could not remove folder: {e}")

        else:
            # Just rename YYYY.0 to YYYY
            print(f"\n{year_with_decimal} → {year_clean}: Renaming folder ({pdf_count} PDFs)")
            actions.append(f"RENAME: {year_with_decimal} → {year_clean} ({pdf_count} PDFs)")

            try:
                decimal_folder.rename(clean_folder)
                print(f"  ✓ Renamed")
            except Exception as e:
                errors.append(f"ERROR renaming {year_with_decimal}: {e}")
                print(f"  ✗ Error: {e}")

    # Write log
    print("\n" + "=" * 80)
    print("CONSOLIDATION COMPLETE")
    print("=" * 80)

    with open(log_file, 'w') as f:
        f.write(f"Folder Consolidation Log\n")
        f.write(f"Date: {datetime.now()}\n")
        f.write(f"=" * 80 + "\n\n")

        f.write(f"Actions Taken ({len(actions)}):\n")
        f.write("-" * 80 + "\n")
        for action in actions:
            f.write(f"{action}\n")

        if errors:
            f.write(f"\nErrors ({len(errors)}):\n")
            f.write("-" * 80 + "\n")
            for error in errors:
                f.write(f"{error}\n")

    print(f"\nActions: {len(actions)}")
    print(f"Errors: {len(errors)}")
    print(f"\nLog saved to: {log_file}")

    # Final summary
    print("\n" + "=" * 80)
    print("FINAL FOLDER COUNT")
    print("=" * 80)

    year_folders = sorted([f for f in base_dir.iterdir() if f.is_dir() and f.name.replace('.0', '').isdigit()])

    total_pdfs = 0
    for folder in year_folders:
        pdf_count = len(list(folder.glob("*.pdf")))
        total_pdfs += pdf_count
        if pdf_count > 0:
            print(f"{folder.name}: {pdf_count} PDFs")

    print(f"\nTotal PDFs: {total_pdfs:,}")
    print(f"Total year folders: {len(year_folders)}")

if __name__ == "__main__":
    consolidate_folders()
