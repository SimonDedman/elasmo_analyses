#!/usr/bin/env python3
"""
Cascade Downloader for Shared Paper Pool

Attempts to download papers through multiple methods in order of success rate:
1. Sci-Hub via Tor (80% success)
2. Unpaywall (35% success)
3. Direct PDF URL (45% success)
4. ResearchGate (30% success)

Papers that succeed are marked as downloaded and removed from the queue.
Papers that fail cascade to the next method.

Author: Claude Code
Date: 2026-01-08
"""

import pandas as pd
import subprocess
import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/cascade_download.log'),
        logging.StreamHandler()
    ]
)

PROJECT_ROOT = Path(__file__).parent.parent
POOL_DIR = PROJECT_ROOT / "outputs" / "download_pools"
PDF_DIR = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")


class CascadeDownloader:
    """Manages cascade downloading through multiple methods"""

    def __init__(self, input_file: Path, dry_run: bool = False):
        self.input_file = input_file
        self.dry_run = dry_run
        self.results = {
            'scihub': {'success': 0, 'fail': 0},
            'unpaywall': {'success': 0, 'fail': 0},
            'direct': {'success': 0, 'fail': 0},
            'researchgate': {'success': 0, 'fail': 0},
        }

        # Load the pool
        self.pool = pd.read_csv(input_file)
        logging.info(f"Loaded {len(self.pool):,} papers from {input_file.name}")

        # Create working directory
        self.work_dir = PROJECT_ROOT / "outputs" / "cascade_work"
        self.work_dir.mkdir(exist_ok=True)

    def run_cascade(self, start_step: int = 1):
        """Run the full cascade"""

        remaining = self.pool.copy()

        steps = [
            (1, 'scihub', 'Sci-Hub via Tor', 'download_via_scihub_tor.py'),
            (2, 'unpaywall', 'Unpaywall', 'download_unpaywall.py'),
            (3, 'direct', 'Direct PDF URL', 'download_pdfs_from_database.py'),
            (4, 'researchgate', 'ResearchGate', 'download_researchgate.py'),
        ]

        for step_num, method, name, script in steps:
            if step_num < start_step:
                continue

            if len(remaining) == 0:
                logging.info("No papers remaining - cascade complete!")
                break

            logging.info(f"\n{'='*70}")
            logging.info(f"STEP {step_num}: {name}")
            logging.info(f"Papers to attempt: {len(remaining):,}")
            logging.info(f"{'='*70}")

            # Save remaining to temp file
            temp_input = self.work_dir / f"step{step_num}_{method}_input.csv"
            remaining.to_csv(temp_input, index=False)

            if self.dry_run:
                logging.info(f"[DRY RUN] Would run: python3 {script} --input {temp_input}")
                # Simulate 50% success for dry run
                success_count = len(remaining) // 2
                fail_count = len(remaining) - success_count
            else:
                # Run the downloader script
                success_count, fail_count, remaining = self._run_downloader(
                    script, temp_input, method
                )

            self.results[method]['success'] = success_count
            self.results[method]['fail'] = fail_count

            logging.info(f"Step {step_num} complete: {success_count:,} success, {fail_count:,} fail")

            # Save failures for next step
            if len(remaining) > 0:
                fail_file = self.work_dir / f"step{step_num}_{method}_failures.csv"
                remaining.to_csv(fail_file, index=False)

        self._print_summary()

    def _run_downloader(self, script: str, input_file: Path, method: str):
        """Run a specific downloader script and parse results"""

        script_path = PROJECT_ROOT / "scripts" / script

        if not script_path.exists():
            logging.warning(f"Script not found: {script_path}")
            # Return all as failures
            remaining = pd.read_csv(input_file)
            return 0, len(remaining), remaining

        # Run the script
        cmd = [sys.executable, str(script_path), '--input', str(input_file)]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600*6)

            # Parse log file for results
            log_file = PROJECT_ROOT / "logs" / f"{method}_download_log.csv"
            if log_file.exists():
                log_df = pd.read_csv(log_file)
                recent = log_df[log_df['timestamp'] > datetime.now().isoformat()[:10]]
                success = len(recent[recent['status'] == 'success'])
                fail = len(recent[recent['status'] != 'success'])

                # Get remaining (failures)
                input_df = pd.read_csv(input_file)
                success_ids = recent[recent['status'] == 'success']['literature_id'].tolist()
                remaining = input_df[~input_df['literature_id'].isin(success_ids)]

                return success, fail, remaining
            else:
                remaining = pd.read_csv(input_file)
                return 0, len(remaining), remaining

        except subprocess.TimeoutExpired:
            logging.error(f"Timeout running {script}")
            remaining = pd.read_csv(input_file)
            return 0, len(remaining), remaining
        except Exception as e:
            logging.error(f"Error running {script}: {e}")
            remaining = pd.read_csv(input_file)
            return 0, len(remaining), remaining

    def _print_summary(self):
        """Print final summary"""

        logging.info(f"\n\n{'='*70}")
        logging.info("CASCADE DOWNLOAD SUMMARY")
        logging.info(f"{'='*70}")

        total_success = sum(r['success'] for r in self.results.values())
        total_fail = self.results['researchgate']['fail']  # Final failures

        logging.info(f"\n{'Method':<20} {'Success':>10} {'Fail':>10}")
        logging.info("-"*40)
        for method, result in self.results.items():
            logging.info(f"{method:<20} {result['success']:>10,} {result['fail']:>10,}")
        logging.info("-"*40)
        logging.info(f"{'TOTAL SUCCESS':<20} {total_success:>10,}")
        logging.info(f"{'REMAINING FAILURES':<20} {total_fail:>10,}")


def main():
    parser = argparse.ArgumentParser(
        description='Cascade downloader for shared paper pool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full cascade on shared pool
  python3 cascade_downloader.py --input outputs/download_pools/shared_cascade_pool.csv

  # Dry run to see what would happen
  python3 cascade_downloader.py --input outputs/download_pools/shared_cascade_pool.csv --dry-run

  # Start from step 2 (skip Sci-Hub)
  python3 cascade_downloader.py --input outputs/download_pools/shared_cascade_pool.csv --start-step 2
        """
    )

    parser.add_argument('--input', type=Path, required=True,
                       help='Input CSV file with papers to download')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without downloading')
    parser.add_argument('--start-step', type=int, default=1,
                       help='Step to start from (1=Sci-Hub, 2=Unpaywall, 3=Direct, 4=RG)')

    args = parser.parse_args()

    if not args.input.exists():
        logging.error(f"Input file not found: {args.input}")
        return 1

    downloader = CascadeDownloader(args.input, dry_run=args.dry_run)
    downloader.run_cascade(start_step=args.start_step)

    return 0


if __name__ == "__main__":
    sys.exit(main())
