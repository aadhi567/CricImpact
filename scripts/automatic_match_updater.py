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
    parser.add_argument(
        "--competition",
        type=str,
        default="t20i",
        help="Competition identifier: 't20i' or 'ipl' (default: 't20i').",
    )
    parser.add_argument(
        "--force-download",
        action="store_true",
        help="Force re-downloading upstream archive from Cricsheet even if cached locally.",
    )
    args = parser.parse_args()

    print("==================================================================")
    print("CRICIMPACT AUTOMATIC MATCH UPDATER")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'PRODUCTION COMMIT'}")
    print(f"Competition: {args.competition}")
    print(f"Cutoff Date: {args.cutoff_date}")
    print(f"Source Archive: {args.source_zip or ('Force-fetch Cricsheet' if args.force_download else 'Auto-fetch latest Cricsheet')}")
    print("==================================================================")

    res = match_update_service.run_update(
        dry_run=args.dry_run,
        source_zip=args.source_zip,
        cutoff_date=args.cutoff_date,
        competition=args.competition,
        force_download=args.force_download,
    )

    print("\n------------------------------------------------------------------")
    print("EXECUTION RESULT & TELEMETRY:")
    print(f"Status: {res.get('status')}")
    print(f"Latest Upstream Publication: {res.get('upstream_publication_date', 'N/A')} ({res.get('upstream_last_modified', 'N/A')})")
    print(f"Latest Source Match Date: {res.get('latest_source_match_date', 'N/A')}")
    print(f"Latest Locally Imported Match Date: {res.get('latest_imported_match_date', 'N/A')}")
    print(f"Latest Production Match Date: {res.get('latest_production_match_date', 'N/A')}")

    investigated = res.get("investigated_targets", {})
    if investigated:
        print("\nInvestigated Target Matches (Post-Oct 13):")
        for mid, info in investigated.items():
            print(f"  - [{mid}] {info.get('fixture', mid)} ({info.get('date')}): {info.get('status')} - {info.get('reason')}")

    if res.get("status") in ("SUCCESS", "SIMULATED_SUCCESS"):
        print(f"\nMatches Imported: {res.get('matches_imported', res.get('matches_to_import'))}")
        print(f"Imported Match IDs: {res.get('imported_match_ids', res.get('match_ids'))}")
        print(f"Total T20I Matches: {res.get('total_matches_t20i')}")
        print(f"Execution Duration: {res.get('duration_seconds')}s")
        sys.exit(0)
    elif res.get("status") == "UP_TO_DATE":
        print(f"\nMessage: {res.get('message')}")
        print(f"Matches Discovered: {res.get('matches_discovered', 0)}")
        print(f"Matches Skipped (Duplicates): {res.get('matches_skipped_duplicates', 0)}")
        stats = res.get("stats", {})
        print(f"Matches Skipped (Unapproved/Associate Teams): {stats.get('skipped_unapproved_teams', 0)}")
        print(f"Execution Duration: {res.get('duration_seconds')}s")
        sys.exit(0)
    else:
        print(f"Error: {res.get('error', res.get('message', 'Unknown failure'))}")
        sys.exit(1)


if __name__ == "__main__":
    main()
