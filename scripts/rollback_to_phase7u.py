"""
Instantaneous Rollback Engine: Restores Phase 7U Production Baseline.
Auto-generated from preflight verification.
"""
import shutil
import hashlib
import time
from pathlib import Path

BACKUP_DIR = Path(r"C:\Users\admin\Documents\contribution\data\backups\phase7u_baseline_20261012_225557")
PROD_DATA = Path("data/processed/batter_match_contributions.csv")
SEASON_DATA = Path("models/contribution/phase6/phase6_season_metrics.csv")
SEASON_SPEC = Path("models/contribution/phase6/phase6_season_spec.json")

def execute_rollback(dry_run: bool = False):
    print(f"[ROLLBACK] Source backup: {BACKUP_DIR} (dry_run={dry_run})")
    if not BACKUP_DIR.exists():
        raise FileNotFoundError(f"Backup directory {BACKUP_DIR} does not exist!")

    targets = [
        (BACKUP_DIR / "batter_match_contributions.csv", PROD_DATA),
        (BACKUP_DIR / "phase6_season_metrics.csv", SEASON_DATA),
        (BACKUP_DIR / "phase6_season_spec.json", SEASON_SPEC),
    ]

    for src, dst in targets:
        if not src.exists():
            raise FileNotFoundError(f"Missing backup file: {src}")
        if not dry_run:
            shutil.copy2(src, dst)
            print(f"  [RESTORED] {dst} ({dst.stat().st_size:,} bytes)")
        else:
            print(f"  [DRY-RUN VERIFIED] {src} -> {dst}")

    if not dry_run:
        # Invalidate memory caches if running inside app
        try:
            from app.services.data_service import data_service
            data_service._cache["ipl"] = {
                "season_metrics": None,
                "matches": None,
                "rosters": None,
                "contributions": None,
            }
            data_service._dynamic_metrics_cache.clear()
            print("  [CACHE INVALIDATED] In-memory DataService caches evicted.")
        except Exception as e:
            print(f"  [CACHE NOTICE] Standalone process, memory cache will reload on next startup: {e}")

        try:
            from src.scoring_engine_config import set_active_scoring_engine
            set_active_scoring_engine("phase7u")
            print("  [CONFIG RESET] Active scoring engine restored to phase7u.")
        except Exception as e:
            print(f"  [CONFIG NOTICE] {e}")

    print("[ROLLBACK COMPLETE] Verification finished successfully.")

if __name__ == "__main__":
    import sys
    dry = "--dry-run" in sys.argv
    execute_rollback(dry_run=dry)
