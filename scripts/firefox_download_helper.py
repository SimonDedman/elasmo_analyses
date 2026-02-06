#!/usr/bin/env python3
"""
Firefox automation helper to download papers from Primo search.

This script controls your existing Firefox browser using pyautogui.
It will:
1. Click "Search" links from the HTML page to open Primo searches
2. Find and click "Download PDF" links on Primo results
3. Close tabs and move to next paper

Usage:
    ./venv/bin/python scripts/firefox_download_helper.py

Prerequisites:
- Firefox open with the elsevier_primo_search.html page
- Logged into FIU Library
"""

import pyautogui
import time
import subprocess
import sqlite3
from pathlib import Path

# Settings
PAUSE_BETWEEN_PAPERS = 2  # seconds
PAGE_LOAD_WAIT = 4  # seconds to wait for page to load
DOWNLOAD_WAIT = 3  # seconds to wait for download to start

# Paths
PROJECT_DIR = Path(__file__).parent.parent
DB_PATH = PROJECT_DIR / "database" / "download_tracker.db"

# pyautogui settings
pyautogui.PAUSE = 0.3  # Add small pause between actions
pyautogui.FAILSAFE = True  # Move mouse to corner to abort


def get_firefox_window():
    """Find Firefox window ID using xdotool."""
    try:
        result = subprocess.run(
            ['xdotool', 'search', '--name', 'Mozilla Firefox'],
            capture_output=True, text=True
        )
        windows = result.stdout.strip().split('\n')
        return windows[0] if windows and windows[0] else None
    except:
        return None


def focus_firefox():
    """Focus the Firefox window."""
    try:
        subprocess.run(['xdotool', 'search', '--name', 'Mozilla Firefox', 'windowactivate'],
                      capture_output=True)
        time.sleep(0.3)
        return True
    except:
        return False


def click_search_button():
    """Try to find and click a Search button using image recognition or coordinates."""
    # Method 1: Try to find blue "Search" button by looking for it on screen
    # This requires a screenshot of the button saved as a template

    # Method 2: Use keyboard navigation
    # Tab through the page to find links

    # For now, we'll use a simple approach:
    # The user positions their mouse near the first unchecked Search button
    # and we click there, then use Tab to move to next ones

    pyautogui.click()  # Click where mouse is
    time.sleep(0.5)


def open_link_in_new_tab():
    """Middle-click to open link in new tab, or Ctrl+click."""
    pyautogui.keyDown('ctrl')
    pyautogui.click()
    pyautogui.keyUp('ctrl')
    time.sleep(0.3)


def wait_for_page_load(seconds=PAGE_LOAD_WAIT):
    """Wait for page to load."""
    time.sleep(seconds)


def find_and_click_pdf_link():
    """Try to find and click Download PDF or LibKey link."""
    # Use Ctrl+F to find "Download PDF"
    pyautogui.hotkey('ctrl', 'f')
    time.sleep(0.5)

    # Type search term
    pyautogui.typewrite('Download PDF', interval=0.02)
    time.sleep(0.5)

    # Press Enter to find
    pyautogui.press('enter')
    time.sleep(0.3)

    # Press Escape to close find bar
    pyautogui.press('escape')
    time.sleep(0.3)

    # The found text should be highlighted - try clicking on it
    # First, press Enter while in find mode would have scrolled to it
    # Now we need to click it - this is tricky

    # Alternative: Press Tab to navigate to links, Enter to click
    # Let's try clicking near where the highlight might be

    # For Primo, the Download PDF link is usually in a specific location
    # Let's try pressing Tab a few times to get to it
    for _ in range(5):
        pyautogui.press('tab')
        time.sleep(0.1)

    pyautogui.press('enter')
    time.sleep(1)

    return True


def close_current_tab():
    """Close the current Firefox tab."""
    pyautogui.hotkey('ctrl', 'w')
    time.sleep(0.3)


def scroll_down_in_list():
    """Scroll down in the paper list to see next items."""
    pyautogui.scroll(-3)  # Negative = scroll down
    time.sleep(0.2)


def mark_checkbox():
    """Try to click the checkbox for the current item."""
    # This is tricky - we need to go back to the HTML tab and click the checkbox
    # For now, we'll skip this and let user do manual cleanup
    pass


def run_batch(num_papers=10):
    """Process a batch of papers."""

    print("=" * 60)
    print("Firefox Download Helper")
    print("=" * 60)
    print()
    print("SETUP:")
    print("1. Make sure Firefox is open with elsevier_primo_search.html")
    print("2. Make sure you're logged into FIU Library")
    print("3. Position your mouse over the FIRST 'Search' button to click")
    print("4. Press Enter here when ready...")
    print()
    print("CONTROLS:")
    print("- Move mouse to top-left corner to ABORT")
    print("- The script will Ctrl+click each Search button")
    print()

    input(">>> Press Enter when Firefox is ready and mouse is positioned... <<<")

    print()
    print(f"Starting to process {num_papers} papers...")
    print("Move mouse to top-left corner to abort!")
    print()

    time.sleep(1)

    # Focus Firefox
    if not focus_firefox():
        print("Could not focus Firefox window!")
        return

    time.sleep(0.5)

    downloaded = 0
    failed = 0

    for i in range(num_papers):
        print(f"\n[{i+1}/{num_papers}] Processing paper...")

        try:
            # Step 1: Ctrl+click on Search button to open in new tab
            print("  Opening search in new tab...")
            open_link_in_new_tab()

            # Step 2: Wait for the new tab to load
            wait_for_page_load(PAGE_LOAD_WAIT)

            # Step 3: Try to find and click Download PDF
            print("  Looking for Download PDF link...")
            find_and_click_pdf_link()

            # Step 4: Wait for download to start
            time.sleep(DOWNLOAD_WAIT)

            # Step 5: Close the Primo/PDF tab
            print("  Closing tab...")
            close_current_tab()
            time.sleep(0.5)

            # Step 6: In the HTML list, move to next Search button
            # Press Tab twice (checkbox, then Search button)
            pyautogui.press('tab')
            time.sleep(0.1)
            pyautogui.press('tab')
            time.sleep(0.1)

            downloaded += 1
            print(f"  Done! ({downloaded} completed)")

        except pyautogui.FailSafeException:
            print("\n\nABORTED - Mouse moved to corner")
            break
        except Exception as e:
            print(f"  Error: {e}")
            failed += 1
            # Try to recover by closing tab and continuing
            try:
                close_current_tab()
                pyautogui.press('tab')
                pyautogui.press('tab')
            except:
                pass

        time.sleep(PAUSE_BETWEEN_PAPERS)

    print()
    print("=" * 60)
    print(f"Completed: {downloaded}")
    print(f"Failed: {failed}")
    print("=" * 60)
    print()
    print("PDFs should be in your Downloads folder.")
    print("Run Claude to process them when ready.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--count', type=int, default=10, help='Number of papers to process')
    args = parser.parse_args()

    run_batch(args.count)
