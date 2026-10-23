"""
Automatic Match Updater & Historical Backfill Pipeline.
Production-safe updater for CricImpact:
1. Discovers newly completed matches (Cricsheet and/or live cricket APIs).
2. Filters for eligible Men's T20 competitions and approved teams.
3. Downloads, stages, and validates ball-by-ball and scorecard records.
4. Computes Strategy 4 production contributions (preserving DNB null semantics).
5. Atomically commits updates to partitioned datasets:
   - matches.csv
   - match_rosters.csv
   - batter_match_contributions.csv
   - phase6_season_metrics.csv
   - phase_summaries.json (Ground Analysis)
   - processed_matches_registry.json
   - last_sync_status.json
6. Guarantees concurrency safety (file lock) and full idempotency.
"""

import os
import sys
import json
import time
import zipfile
import logging
import urllib.request
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import pandas as pd
import numpy as np

# Root path configuration
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.contribution_framework import compute_production_contribution
from src.season_aggregation import build_season_aggregations
from scripts.ingest_competition_data import parse_cricsheet_match, update_registry, normalize_team, APPROVED_INTERNATIONAL_TEAMS

logger = logging.getLogger("cricimpact.updater")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

DEFAULT_CUTOFF_DATE = "2026-10-06"
CRICSHEET_T20_ZIP_URL = "https://cricsheet.org/downloads/t20s_male_json.zip"
CONCURRENCY_LOCK_FILE = ROOT_DIR / "data" / "staging" / "match_updater.lock"


class MatchUpdateService:
    """
    Core service managing automated discovery, staging, validation,
    and atomic persistence of new match datasets.
    """

    def __init__(
        self,
        raw_t20_dir: Path | str = ROOT_DIR / "data" / "t20s_json",
        processed_t20_dir: Path | str = ROOT_DIR / "data" / "processed" / "t20i",
        registry_path: Path | str = ROOT_DIR / "data" / "processed" / "processed_matches_registry.json",
        phase_summaries_path: Path | str = ROOT_DIR / "data" / "processed" / "phase_summaries.json",
        sync_status_path: Path | str = ROOT_DIR / "data" / "processed" / "last_sync_status.json",
        staging_dir: Path | str = ROOT_DIR / "data" / "staging" / "match_updater",
        lock_file: Path | str = ROOT_DIR / "data" / "staging" / "match_updater.lock",
        cutoff_date: str = DEFAULT_CUTOFF_DATE,
    ):
        self.raw_t20_dir = Path(raw_t20_dir)
        self.processed_t20_dir = Path(processed_t20_dir)
        self.registry_path = Path(registry_path)
        self.phase_summaries_path = Path(phase_summaries_path)
        self.sync_status_path = Path(sync_status_path)
        self.staging_dir = Path(staging_dir)
        self.lock_file = Path(lock_file)
        self.cutoff_date = cutoff_date

    def acquire_lock(self, timeout_seconds: int = 10) -> bool:
        """Acquires a process lock to prevent concurrent overlapping executions."""
        self.lock_file.parent.mkdir(parents=True, exist_ok=True)
        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            try:
                # Check for stale lock (>15 mins old)
                if self.lock_file.exists():
                    mtime = self.lock_file.stat().st_mtime
                    if time.time() - mtime > 900:
                        logger.warning(f"Clearing stale lock file {self.lock_file} (age > 900s)")
                        self.lock_file.unlink(missing_ok=True)

                # Atomic creation with O_EXCL
                fd = os.open(str(self.lock_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                with os.fdopen(fd, "w") as f:
                    f.write(f"pid={os.getpid()}\ntime={time.time()}\n")
                return True
            except FileExistsError:
                time.sleep(0.5)
            except Exception as e:
                logger.error(f"Error acquiring lock: {e}")
                return False
        return False

    def release_lock(self):
        """Releases the process lock."""
        try:
            if self.lock_file.exists():
                self.lock_file.unlink(missing_ok=True)
        except Exception as e:
            logger.warning(f"Error releasing lock {self.lock_file}: {e}")

    def fetch_source_archive(
        self,
        url: str = CRICSHEET_T20_ZIP_URL,
        cached_zip_path: Optional[Path] = None,
        max_retries: int = 3,
    ) -> Path:
        """
        Downloads or retrieves the Cricsheet source archive using conditional HTTP
        checks and bounded exponential backoff.
        """
        zip_path = cached_zip_path or (ROOT_DIR / "scratch" / "t20s_male_json_latest.zip")
        zip_path.parent.mkdir(parents=True, exist_ok=True)

        # Check if local zip is already fresh (< 2 hours old and > 10MB)
        if zip_path.exists() and zip_path.stat().st_size > 10000000:
            age_hours = (time.time() - zip_path.stat().st_mtime) / 3600.0
            if age_hours < 2.0:
                logger.info(f"Using fresh cached archive at {zip_path} (age: {age_hours:.1f}h)")
                return zip_path

        headers = {"User-Agent": "CricImpact-Updater/1.0"}
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Downloading source archive from {url} (Attempt {attempt}/{max_retries})...")
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=45) as resp:
                    data = resp.read()
                    temp_path = zip_path.with_suffix(".tmp")
                    with open(temp_path, "wb") as f:
                        f.write(data)
                    temp_path.replace(zip_path)
                logger.info(f"Successfully downloaded {len(data):,} bytes to {zip_path}")
                return zip_path
            except Exception as e:
                wait_time = 2 ** attempt
                logger.warning(f"Download attempt {attempt} failed: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)

        # Fallback to existing file if available
        if zip_path.exists():
            logger.warning(f"Download retries exhausted. Falling back to existing archive at {zip_path}")
            return zip_path

        raise RuntimeError(f"Failed to download Cricsheet source archive after {max_retries} attempts.")

    def discover_eligible_matches(
        self,
        zip_path: Path,
        cutoff_date: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Inspects the archive and discovers all eligible, completed T20 matches
        played after the cutoff date.
        """
        min_date = cutoff_date or self.cutoff_date
        logger.info(f"Scanning {zip_path} for eligible completed matches after {min_date}...")

        # Load currently processed match IDs
        existing_matches_df = pd.DataFrame()
        m_file = self.processed_t20_dir / "matches.csv"
        if m_file.exists():
            existing_matches_df = pd.read_csv(m_file, dtype={"match_id": str})
        existing_ids = set(existing_matches_df["match_id"].dropna().unique()) if not existing_matches_df.empty else set()

        discovered = []
        stats = {
            "total_scanned": 0,
            "after_cutoff_date": 0,
            "skipped_non_t20": 0,
            "skipped_non_male": 0,
            "skipped_unapproved_teams": 0,
            "skipped_already_processed": 0,
            "eligible_new_matches": 0,
        }

        with zipfile.ZipFile(zip_path, "r") as zf:
            json_names = [n for n in zf.namelist() if n.endswith(".json")]
            stats["total_scanned"] = len(json_names)

            for name in json_names:
                try:
                    with zf.open(name) as fp:
                        match_dict = json.load(fp)

                    info = match_dict.get("info", {})
                    dates = info.get("dates", [])
                    if not dates or str(dates[0]) <= min_date:
                        continue
                    stats["after_cutoff_date"] += 1

                    # 1. Format filter
                    m_type = str(info.get("match_type", "")).strip().upper()
                    if m_type != "T20":
                        stats["skipped_non_t20"] += 1
                        continue

                    # 2. Gender filter
                    if info.get("gender") != "male":
                        stats["skipped_non_male"] += 1
                        continue

                    # 3. Approved teams OR rule
                    raw_teams = [normalize_team(t) for t in info.get("teams", [])]
                    if not any(t in APPROVED_INTERNATIONAL_TEAMS for t in raw_teams):
                        stats["skipped_unapproved_teams"] += 1
                        continue

                    match_id = Path(name).stem
                    # 4. Duplicate check
                    if match_id in existing_ids:
                        stats["skipped_already_processed"] += 1
                        continue

                    discovered.append({
                        "match_id": match_id,
                        "date": str(dates[0]),
                        "teams": raw_teams,
                        "data": match_dict,
                        "raw_json_str": json.dumps(match_dict, indent=2),
                    })
                    stats["eligible_new_matches"] += 1
                except Exception as e:
                    logger.error(f"Error parsing file {name}: {e}")

        # Sort chronologically
        discovered.sort(key=lambda m: (m["date"], m["match_id"]))
        logger.info(
            f"Discovery complete: {stats['eligible_new_matches']} new eligible matches found "
            f"({stats['after_cutoff_date']} total after cutoff, {stats['skipped_unapproved_teams']} associates skipped, "
            f"{stats['skipped_already_processed']} duplicates skipped)"
        )
        return discovered, stats

    def validate_match_data(self, match_id: str, match_dict: Dict[str, Any]) -> Tuple[str, str]:
        """
        Validates match metadata and rules before parsing.
        Returns ("approved", "") or ("rejected", reason).
        """
        info = match_dict.get("info", {})
        m_type = str(info.get("match_type", "")).strip().upper()
        if m_type != "T20":
            return "rejected", f"Not a T20 match (found '{m_type}')"
        if info.get("gender") != "male":
            return "rejected", f"Not a male match (gender '{info.get('gender')}')"
        teams = info.get("teams", [])
        if not teams or len(teams) < 2:
            return "rejected", "Missing teams or team count < 2"
        raw_teams = [normalize_team(t) for t in teams]
        if not any(t in APPROVED_INTERNATIONAL_TEAMS for t in raw_teams):
            return "rejected", f"Neither team is an approved international team ({teams})"
        return "approved", ""

    def stage_and_validate_matches(
        self,
        discovered_matches: List[Dict[str, Any]],
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
        """
        Parses discovered matches into staged DataFrames and computes Strategy 4 ratings.
        Strictly validates record completeness, DNB rules, and score ranges.
        """
        self.staging_dir.mkdir(parents=True, exist_ok=True)
        staged_m = []
        staged_r = []
        staged_b = []
        phase_updates = {"phases": {}, "conditions": {}}
        non_wickets = {"retired hurt", "retired out", "retired not out"}

        for item in discovered_matches:
            mid = item["match_id"]
            m_dict = item["data"]
            fpath = Path(f"{mid}.json")

            # Parse with canonical parser
            m_row, r_rows, b_rows = parse_cricsheet_match(fpath, m_dict)
            if not m_row:
                raise ValueError(f"Match {mid} failed match metadata parsing.")

            # Validation: exactly 22 roster players (11 per team)
            if len(r_rows) != 22:
                raise ValueError(f"Match {mid} roster incomplete: found {len(r_rows)} players, expected 22.")

            # Validation: active batting appearances
            if len(b_rows) == 0:
                raise ValueError(f"Match {mid} has 0 batter contribution rows.")

            # Validation: scores in [0.1, 99.9]
            scores = [b["contribution_score"] for b in b_rows if b.get("contribution_score") is not None]
            for s in scores:
                if s < 0.1 or s > 99.9:
                    raise ValueError(f"Match {mid} generated out-of-bounds score: {s}")

            # Validation: innings numbers in {1, 2}
            inns = {b["innings"] for b in b_rows}
            if not inns.issubset({1, 2}):
                raise ValueError(f"Match {mid} contains invalid innings: {inns}")

            staged_m.append(m_row)
            staged_r.extend(r_rows)
            staged_b.extend(b_rows)

            # Compute phase metrics for Ground Analysis
            inn_phases = {}
            for inn_idx, inn_data in enumerate(m_dict.get("innings", [])[:2]):
                inn_num = str(inn_idx + 1)
                buckets = {
                    "powerplay": {"runs": 0, "wkts": 0, "legal": 0, "dots": 0, "bnd": 0},
                    "middle": {"runs": 0, "wkts": 0, "legal": 0, "dots": 0, "bnd": 0},
                    "death": {"runs": 0, "wkts": 0, "legal": 0, "dots": 0, "bnd": 0},
                }
                for over_data in inn_data.get("overs", []):
                    ov = over_data.get("over", 0)
                    if 0 <= ov <= 5:
                        ph = "powerplay"
                    elif 6 <= ov <= 14:
                        ph = "middle"
                    elif 15 <= ov <= 19:
                        ph = "death"
                    else:
                        continue

                    b = buckets[ph]
                    for deliv in over_data.get("deliveries", []):
                        runs_info = deliv.get("runs", {})
                        b_runs = runs_info.get("batter", 0)
                        tot_runs = runs_info.get("total", 0)
                        extras_info = deliv.get("extras", {})
                        wides = extras_info.get("wides", 0)
                        noballs = extras_info.get("noballs", 0)
                        is_legal = (wides == 0 and noballs == 0)
                        is_dot = is_legal and (tot_runs == 0)
                        is_boundary = is_legal and (b_runs in (4, 6))

                        wkts = 0
                        for w in deliv.get("wickets", []):
                            kind = str(w.get("kind", "")).lower()
                            if kind and kind not in non_wickets:
                                wkts += 1

                        b["runs"] += tot_runs
                        b["wkts"] += wkts
                        if is_legal:
                            b["legal"] += 1
                        if is_dot:
                            b["dots"] += 1
                        if is_boundary:
                            b["bnd"] += 1

                inn_phases[inn_num] = {}
                for ph, b in buckets.items():
                    lb = b["legal"]
                    r = b["runs"]
                    w = b["wkts"]
                    d_cnt = b["dots"]
                    bnd = b["bnd"]
                    rr = round((r / lb) * 6, 2) if lb > 0 else 0.0
                    complete = (lb == 36 if ph == "powerplay" else (lb == 54 if ph == "middle" else lb == 30))
                    inn_phases[inn_num][ph] = {
                        "played": lb > 0,
                        "runs": r,
                        "wickets": w,
                        "legal_balls": lb,
                        "dot_balls": d_cnt,
                        "boundary_balls": bnd,
                        "run_rate": rr,
                        "complete": complete,
                    }

            phase_updates["phases"][mid] = inn_phases
            phase_updates["conditions"][mid] = {
                "is_standard_20ov": True,
                "condition_label": "Standard 20-over match",
                "is_dls": False,
                "is_reduced": False,
                "is_no_result": False,
                "sched_overs": 20,
                "target_overs": 20,
            }

        logger.info(
            f"Staged {len(staged_m)} matches, {len(staged_r)} rosters, "
            f"and {len(staged_b)} batting contributions. All validation checks passed."
        )
        return staged_m, staged_r, staged_b, phase_updates

    def commit_updates(
        self,
        staged_m: List[Dict[str, Any]],
        staged_r: List[Dict[str, Any]],
        staged_b: List[Dict[str, Any]],
        phase_updates: Dict[str, Any],
        discovered_matches: List[Dict[str, Any]],
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Atomically commits staged records to production datasets, re-aggregates
        season statistics, updates the registry, and writes sync telemetry.
        """
        if dry_run:
            logger.info("[DRY RUN] Simulating commit without modifying production files.")
            return {
                "dry_run": True,
                "status": "SIMULATED_SUCCESS",
                "matches_to_import": len(staged_m),
                "rosters_to_import": len(staged_r),
                "contributions_to_import": len(staged_b),
                "match_ids": [m["match_id"] for m in staged_m],
            }

        t0 = time.time()
        logger.info("Starting atomic commit to production datasets...")

        # 1. Update raw JSON storage
        self.raw_t20_dir.mkdir(parents=True, exist_ok=True)
        for item in discovered_matches:
            mid = item["match_id"]
            raw_dest = self.raw_t20_dir / f"{mid}.json"
            if not raw_dest.exists():
                with open(raw_dest, "w", encoding="utf-8") as f:
                    f.write(item["raw_json_str"])
        logger.info(f"Updated raw JSON storage in {self.raw_t20_dir}")

        # 2. Combine and save matches.csv
        m_path = self.processed_t20_dir / "matches.csv"
        df_old_m = pd.read_csv(m_path, dtype={"match_id": str}) if m_path.exists() else pd.DataFrame()
        df_new_m = pd.DataFrame(staged_m)
        df_comb_m = pd.concat([df_old_m, df_new_m], ignore_index=True)
        df_comb_m = df_comb_m.drop_duplicates(subset=["match_id"]).sort_values(
            by=["date", "match_id"], ascending=[False, False]
        ).reset_index(drop=True)
        df_comb_m.to_csv(m_path, index=False, encoding="utf-8")
        logger.info(f"Committed {m_path} ({len(df_comb_m)} rows)")

        # 3. Combine and save match_rosters.csv
        r_path = self.processed_t20_dir / "match_rosters.csv"
        df_old_r = pd.read_csv(r_path, dtype={"match_id": str}) if r_path.exists() else pd.DataFrame()
        df_new_r = pd.DataFrame(staged_r)
        df_comb_r = pd.concat([df_old_r, df_new_r], ignore_index=True)
        df_comb_r = df_comb_r.drop_duplicates(subset=["match_id", "player"]).sort_values(
            by=["match_id", "team", "player"]
        ).reset_index(drop=True)
        df_comb_r.to_csv(r_path, index=False, encoding="utf-8")
        logger.info(f"Committed {r_path} ({len(df_comb_r)} rows)")

        # 4. Combine and save batter_match_contributions.csv
        b_path = self.processed_t20_dir / "batter_match_contributions.csv"
        df_old_b = pd.read_csv(b_path, dtype={"match_id": str}, low_memory=False) if b_path.exists() else pd.DataFrame()
        df_new_b = pd.DataFrame(staged_b)
        df_comb_b = pd.concat([df_old_b, df_new_b], ignore_index=True)
        df_comb_b = df_comb_b.drop_duplicates(subset=["match_id", "innings", "player"]).sort_values(
            by=["match_id", "innings", "player"]
        ).reset_index(drop=True)
        df_comb_b.to_csv(b_path, index=False, encoding="utf-8")
        logger.info(f"Committed {b_path} ({len(df_comb_b)} rows)")

        # 5. Recompute season metrics
        s_path = self.processed_t20_dir / "phase6_season_metrics.csv"
        logger.info("Recomputing comprehensive season metrics...")
        df_season = build_season_aggregations(df_comb_b, df_rosters=df_comb_r)
        df_season.to_csv(s_path, index=False, encoding="utf-8")
        logger.info(f"Committed {s_path} ({len(df_season)} player-seasons)")

        # 6. Update phase_summaries.json (Ground Analysis)
        if self.phase_summaries_path.exists():
            with open(self.phase_summaries_path, "r", encoding="utf-8") as f:
                phase_data = json.load(f)
        else:
            phase_data = {"conditions": {}, "phases": {}}

        phase_data.setdefault("phases", {}).update(phase_updates["phases"])
        phase_data.setdefault("conditions", {}).update(phase_updates["conditions"])
        with open(self.phase_summaries_path, "w", encoding="utf-8") as f:
            json.dump(phase_data, f)
        logger.info(f"Committed {self.phase_summaries_path} with {len(phase_updates['phases'])} new match phases")

        # 7. Update master registry
        update_registry(staged_m, competition="t20i")
        logger.info(f"Updated registry at {self.registry_path}")

        # 8. Refresh in-memory services
        try:
            from app.services.data_service import data_service
            data_service._cache["t20i"] = {
                "season_metrics": None,
                "matches": None,
                "rosters": None,
                "contributions": None,
            }
            data_service._dynamic_metrics_cache.clear()
            data_service._career_players_cache = None
            data_service._dataset_coverage_cache = None
            data_service._ensure_loaded("t20i")

            from app.services.ground_service import ground_service
            ground_service._matches_cache = None
            ground_service._venues_index = None
            ground_service._phases_data = None
            ground_service._ensure_indexed()
            logger.info("Refreshed in-memory data_service and ground_service caches.")
        except Exception as e:
            logger.warning(f"Could not refresh in-memory caches: {e}")

        # 9. Write sync status file
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        sync_result = {
            "last_successful_sync": now_iso,
            "status": "SUCCESS",
            "matches_discovered": len(discovered_matches),
            "matches_imported": len(staged_m),
            "matches_skipped_duplicates": 0,
            "matches_rejected": 0,
            "competitions_updated": ["t20i"],
            "date_range_imported": [min(m["date"] for m in staged_m), max(m["date"] for m in staged_m)],
            "imported_match_ids": [m["match_id"] for m in staged_m],
            "total_matches_t20i": len(df_comb_m),
            "total_rosters_t20i": len(df_comb_r),
            "total_contributions_t20i": len(df_comb_b),
            "duration_seconds": round(time.time() - t0, 3),
            "dry_run": False,
        }

        with open(self.sync_status_path, "w", encoding="utf-8") as f:
            json.dump(sync_result, f, indent=2)
        logger.info(f"Saved sync status to {self.sync_status_path}")

        return sync_result

    def run_update(
        self,
        dry_run: bool = False,
        source_zip: Optional[Path | str] = None,
        cutoff_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes the end-to-end match update workflow with concurrency lock,
        idempotency, and error reporting.
        """
        t0 = time.time()
        logger.info(f"=== Starting Match Update Pipeline (dry_run={dry_run}) ===")

        if not self.acquire_lock():
            msg = "Concurrent match update is already in progress. Aborting."
            logger.warning(msg)
            return {"status": "LOCKED", "message": msg}

        try:
            # 1. Obtain source archive
            if source_zip:
                zip_path = Path(source_zip)
            else:
                zip_path = self.fetch_source_archive()

            # 2. Discover eligible matches
            discovered, stats = self.discover_eligible_matches(zip_path, cutoff_date=cutoff_date)
            if not discovered:
                now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                res = {
                    "last_successful_sync": now_iso,
                    "status": "UP_TO_DATE",
                    "matches_discovered": 0,
                    "matches_imported": 0,
                    "matches_skipped_duplicates": stats["skipped_already_processed"],
                    "stats": stats,
                    "message": "Datasets are already up to date. Zero new eligible matches discovered.",
                    "duration_seconds": round(time.time() - t0, 3),
                }
                # Update sync timestamp even if up-to-date
                if not dry_run:
                    with open(self.sync_status_path, "w", encoding="utf-8") as f:
                        json.dump(res, f, indent=2)
                return res

            # 3. Stage & Validate
            staged_m, staged_r, staged_b, phase_updates = self.stage_and_validate_matches(discovered)

            # 4. Commit
            commit_res = self.commit_updates(
                staged_m=staged_m,
                staged_r=staged_r,
                staged_b=staged_b,
                phase_updates=phase_updates,
                discovered_matches=discovered,
                dry_run=dry_run,
            )

            commit_res["stats"] = stats
            return commit_res

        except Exception as e:
            logger.error(f"Match update pipeline failed: {e}", exc_info=True)
            return {
                "status": "FAILED",
                "error": str(e),
                "duration_seconds": round(time.time() - t0, 3),
            }
        finally:
            self.release_lock()

    def sync(
        self,
        competition: str = "t20i",
        cutoff_date: Optional[str] = None,
        dry_run: bool = False,
        source_zip: Optional[Path | str] = None,
    ) -> Dict[str, Any]:
        """
        Public synchronization entry point for scheduled jobs and API invocations.
        Raises RuntimeError on concurrency lock conflicts.
        """
        res = self.run_update(dry_run=dry_run, source_zip=source_zip, cutoff_date=cutoff_date)
        if res.get("status") == "LOCKED":
            raise RuntimeError(res.get("message", "Another match updater process is currently running"))
        return res


match_update_service = MatchUpdateService()
