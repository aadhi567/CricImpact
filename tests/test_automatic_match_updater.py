"""
Test Suite for CricImpact Automatic Match Updater System.
Validates:
1. Duplicate match detection and idempotency.
2. Stable match ID assignment and referential integrity.
3. Partial/malformed source data rejection and error handling.
4. Concurrency lock protection (preventing overlapping runs).
5. Registry and sync status tracking.
6. Strict DNB null preservation and Strategy 4 mathematical invariants.
7. Derived dataset refreshes (matches, rosters, contributions, season metrics, ground phase summaries).
8. Pipeline API endpoints (/api/pipeline/status, /api/pipeline/sync-status, /api/pipeline/sync).
9. End-to-end verification of backfilled matches after October 6, 2026.
"""

import json
import os
import shutil
import tempfile
from pathlib import Path
import pytest
import pandas as pd
from fastapi.testclient import TestClient

from app.main import app
from app.services.match_updater import MatchUpdateService, CONCURRENCY_LOCK_FILE
from app.services.data_service import data_service
from app.services.ground_service import ground_service

client = TestClient(app)

ROOT_DIR = Path(__file__).resolve().parent.parent
T20I_DIR = ROOT_DIR / "data" / "processed" / "t20i"
REGISTRY_PATH = ROOT_DIR / "data" / "processed" / "processed_matches_registry.json"
LAST_SYNC_FILE = ROOT_DIR / "data" / "processed" / "last_sync_status.json"

BACKFILLED_MATCH_IDS = ["1529231", "1550708", "1529232", "1550709", "1550710"]


def test_1_backfilled_matches_integrity():
    """Verify that all 5 post-cutoff backfilled matches are registered and committed."""
    assert REGISTRY_PATH.exists()
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        registry = json.load(f)

    df_matches = pd.read_csv(T20I_DIR / "matches.csv", dtype={"match_id": str})
    df_rosters = pd.read_csv(T20I_DIR / "match_rosters.csv", dtype={"match_id": str})
    df_contrib = pd.read_csv(T20I_DIR / "batter_match_contributions.csv", dtype={"match_id": str}, low_memory=False)

    match_ids_set = set(df_matches["match_id"])
    assert len(df_matches) == 1503, f"Expected 1503 total T20I matches, got {len(df_matches)}"

    for mid in BACKFILLED_MATCH_IDS:
        # Match in registry
        assert mid in registry, f"Match {mid} missing from registry"
        reg_entry = registry[mid]
        assert str(reg_entry["competition"]).lower() == "t20i"
        assert reg_entry["format"] == "T20"
        assert "processed_at" in reg_entry

        # Match in matches.csv
        assert mid in match_ids_set, f"Match {mid} missing from matches.csv"
        m_row = df_matches[df_matches["match_id"] == mid].iloc[0]
        assert str(m_row["date"]) > "2026-10-06", f"Match {mid} date {m_row['date']} not after cutoff"

        # Match has exactly 22 roster entries
        m_rosters = df_rosters[df_rosters["match_id"] == mid]
        assert len(m_rosters) == 22, f"Match {mid} expected 22 players on roster, got {len(m_rosters)}"
        assert not m_rosters.duplicated(subset=["player"]).any()

        # Match has batter contributions
        m_contrib = df_contrib[df_contrib["match_id"] == mid]
        assert len(m_contrib) > 0, f"Match {mid} has no batter contributions"

        # Strict DNB rule: all entries in contributions are actual batters who faced >= 1 ball or got out
        for _, c_row in m_contrib.iterrows():
            score = c_row.get("contribution_score")
            assert pd.notna(score), f"Contribution score should not be null for active batter in {mid}"
            assert 0.0 <= float(score) <= 100.0, f"Contribution score out of [0, 100] bound in {mid}"


def test_2_updater_idempotency_and_duplicate_detection():
    """Verify that running the updater again detects all matches as duplicates and does not duplicate rows."""
    updater = MatchUpdateService()
    # Execute a run against the local zip or directory
    result = updater.sync(competition="t20i", cutoff_date="2026-10-06", dry_run=False)

    assert result["status"] == "UP_TO_DATE"
    assert result["matches_imported"] == 0
    assert result["matches_discovered"] == 0
    assert result["matches_skipped_duplicates"] >= 5

    # Check that datasets still have exact counts
    df_matches = pd.read_csv(T20I_DIR / "matches.csv", dtype={"match_id": str})
    assert len(df_matches) == 1503, "Repeated run altered match count!"
    assert not df_matches.duplicated(subset=["match_id"]).any(), "Duplicate match IDs found!"

    df_rosters = pd.read_csv(T20I_DIR / "match_rosters.csv", dtype={"match_id": str})
    assert len(df_rosters) == 33070, "Repeated run altered roster count!"
    assert not df_rosters.duplicated(subset=["match_id", "player"]).any(), "Duplicate roster entries found!"

    df_contrib = pd.read_csv(T20I_DIR / "batter_match_contributions.csv", dtype={"match_id": str}, low_memory=False)
    assert len(df_contrib) == 24112, "Repeated run altered contribution count!"
    assert not df_contrib.duplicated(subset=["match_id", "innings", "player"]).any(), "Duplicate contribution entries found!"


def test_3_dry_run_mode_does_not_mutate_state():
    """Verify that dry_run=True does not write to disk or alter datasets."""
    mtime_before = (T20I_DIR / "matches.csv").stat().st_mtime
    updater = MatchUpdateService()
    result = updater.sync(competition="t20i", cutoff_date="2026-10-06", dry_run=True)

    assert result["status"] in ("DRY_RUN_COMPLETE", "UP_TO_DATE")
    mtime_after = (T20I_DIR / "matches.csv").stat().st_mtime
    assert mtime_before == mtime_after, "Dry run mutated matches.csv!"


def test_4_concurrency_lock_handling():
    """Verify that updater prevents overlapping runs when lockfile exists."""
    lock_file = Path(CONCURRENCY_LOCK_FILE)
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Create artificial lock file
    with open(lock_file, "w") as f:
        f.write("fake_pid_12345")

    try:
        updater = MatchUpdateService()
        with pytest.raises(RuntimeError, match="Concurrent match update is already in progress"):
            updater.sync(competition="t20i", cutoff_date="2026-10-06", dry_run=False)
    finally:
        if lock_file.exists():
            lock_file.unlink()


def test_5_malformed_source_data_rejection():
    """Verify that malformed or incomplete match data is safely rejected without corrupting datasets."""
    updater = MatchUpdateService()

    # Incomplete info (missing teams)
    bad_data_1 = {
        "info": {"match_type": "T20", "gender": "male", "dates": ["2026-10-10"]},
        "innings": []
    }
    status, reason = updater.validate_match_data("bad_1", bad_data_1)
    assert status == "rejected"
    assert "Missing teams or team count" in reason

    # Unapproved teams
    bad_data_2 = {
        "info": {
            "match_type": "T20",
            "gender": "male",
            "dates": ["2026-10-10"],
            "teams": ["Bhutan", "Maldives"],
            "players": {"Bhutan": ["P1"], "Maldives": ["P2"]},
        },
        "innings": []
    }
    status, reason = updater.validate_match_data("bad_2", bad_data_2)
    assert status == "rejected"
    assert "Neither team is an approved international team" in reason

    # Non-T20 match
    bad_data_3 = {
        "info": {
            "match_type": "ODI",
            "gender": "male",
            "dates": ["2026-10-10"],
            "teams": ["India", "Pakistan"],
            "players": {"India": ["P1"], "Pakistan": ["P2"]},
        },
        "innings": []
    }
    status, reason = updater.validate_match_data("bad_3", bad_data_3)
    assert status == "rejected"
    assert "Not a T20 match" in reason


def test_6_ground_analysis_integration():
    """Verify that Ground Analysis phase summaries and venue indexes include the backfilled matches."""
    # Ranchi venue: Match 1529231 (India vs West Indies, 2026-10-09)
    ranchi_analysis = ground_service.get_ground_analysis(
        venue_id="JSCA International Stadium Complex, Ranchi",
        competition="t20i",
        period="all_time",
    )
    assert ranchi_analysis is not None, "Ranchi venue should be found in ground analysis"
    assert ranchi_analysis["summary"]["total_matches_in_period"] >= 4, "Expected at least 4 T20I matches at Ranchi"

    # Rawalpindi venue: Matches 1550708, 1550709, 1550710 (Pakistan vs Sri Lanka, Oct 2026)
    pindi_analysis = ground_service.get_ground_analysis(
        venue_id="Rawalpindi Cricket Stadium",
        competition="t20i",
        period="all_time",
    )
    assert pindi_analysis is not None, "Rawalpindi venue should be found in ground analysis"
    assert pindi_analysis["summary"]["total_matches_in_period"] >= 8, "Expected matches at Rawalpindi"

    # Verify phase summaries file contains the backfilled match IDs
    phase_sum_path = ROOT_DIR / "data" / "processed" / "phase_summaries.json"
    assert phase_sum_path.exists()
    with open(phase_sum_path, "r", encoding="utf-8") as f:
        phases = json.load(f)

    for mid in BACKFILLED_MATCH_IDS:
        assert mid in phases["phases"], f"Match {mid} missing from phases['phases']"
        assert mid in phases["conditions"], f"Match {mid} missing from phases['conditions']"


def test_7_pipeline_api_endpoints():
    """Verify FastAPI pipeline status, sync-status, and sync endpoints."""
    # 1. Pipeline status
    res_status = client.get("/api/pipeline/status")
    assert res_status.status_code == 200
    st_data = res_status.json()
    assert st_data["status"] == "ready"
    assert st_data["processed_matches_count"] >= 1500
    assert "last_sync" in st_data
    assert st_data["last_sync"] is not None

    # 2. Pipeline sync status
    res_sync_st = client.get("/api/pipeline/sync-status")
    assert res_sync_st.status_code == 200
    sync_data = res_sync_st.json()
    assert "last_successful_sync" in sync_data
    assert sync_data["status"] in ("SUCCESS", "UP_TO_DATE")

    # 3. Pipeline dry-run sync trigger
    res_sync = client.post("/api/pipeline/sync?dry_run=true&competition=t20i")
    assert res_sync.status_code == 200
    trigger_data = res_sync.json()
    assert trigger_data["status"] in ("DRY_RUN_COMPLETE", "UP_TO_DATE")


def test_8_end_to_end_player_and_match_apis():
    """Verify that match overview and player profile APIs return data for backfilled matches."""
    # Match 1529231 overview
    res_match = client.get("/api/match/1529231?competition=t20i")
    assert res_match.status_code == 200
    match_data = res_match.json()
    assert str(match_data["match_id"]) == "1529231"
    assert "India" in (match_data["team1"], match_data["team2"])
    assert "West Indies" in (match_data["team1"], match_data["team2"])
    assert len(match_data["batters"]) >= 10, "Expected at least 10 batting performances"

    # Verify Shai Hope top scored in match 1529231 (102 runs)
    hope_found = False
    for batter in match_data["batters"]:
        if "Hope" in batter["player"]:
            assert batter["runs"] == 102
            assert batter["contribution_score"] is not None
            assert batter["contribution_score"] > 80.0
            hope_found = True
    assert hope_found, "Shai Hope century record not found in match 1529231 overview"

    # Match 1550708 overview (Pakistan vs Sri Lanka)
    res_pindi = client.get("/api/match/1550708?competition=t20i")
    assert res_pindi.status_code == 200
    pindi_data = res_pindi.json()
    assert str(pindi_data["match_id"]) == "1550708"
    assert "Pakistan" in (pindi_data["team1"], pindi_data["team2"])
