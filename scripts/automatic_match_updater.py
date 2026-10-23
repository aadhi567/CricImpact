"""
CLI Tool for CricImpact Automatic Match Updater.

Usage:
    python scripts/automatic_match_updater.py [--dry-run] [--source-zip PATH] [--cutoff-date YYYY-MM-DD]
"""

import sys
import argparse
from pathlib import Path

# Ensure root directory is on path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.services.match_updater import match_update_service


def main():
    parser = argparse.ArgumentParser(description="CricImpact Automatic Match Updater & Backfill")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate discovery, staging, and scoring without writing to production datasets.",
    )
    parser.add_argument(
        "--source-zip",
        type=str,
        default=None,
        help="Optional path to local Cricsheet zip archive (skips remote download).",
    )
    parser.add_argument(
        "--cutoff-date",
        type=str,
        default="2026-10-06",
        help="Cutoff date for match discovery (default: 2026-10-06).",
    )
    args = parser.parse_args()

    print("==================================================================")
    print("CRICIMPACT AUTOMATIC MATCH UPDATER")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'PRODUCTION COMMIT'}")
    print(f"Cutoff Date: {args.cutoff_date}")
    print(f"Source Archive: {args.source_zip or 'Auto-fetch latest Cricsheet'}")
    print("==================================================================")

    res = match_update_service.run_update(
        dry_run=args.dry_run,
        source_zip=args.source_zip,
        cutoff_date=args.cutoff_date,
    )

    print("\n------------------------------------------------------------------")
    print("EXECUTION RESULT:")
    print(f"Status: {res.get('status')}")
    if res.get("status") in ("SUCCESS", "SIMULATED_SUCCESS"):
        print(f"Matches Imported: {res.get('matches_imported', res.get('matches_to_import'))}")
        print(f"Imported Match IDs: {res.get('imported_match_ids', res.get('match_ids'))}")
        print(f"Total T20I Matches: {res.get('total_matches_t20i')}")
        print(f"Execution Duration: {res.get('duration_seconds')}s")
        sys.exit(0)
    elif res.get("status") == "UP_TO_DATE":
        print("Datasets are already up to date.")
        print(f"Execution Duration: {res.get('duration_seconds')}s")
        sys.exit(0)
    else:
        print(f"Error: {res.get('error', res.get('message', 'Unknown failure'))}")
        sys.exit(1)


if __name__ == "__main__":
    main()
