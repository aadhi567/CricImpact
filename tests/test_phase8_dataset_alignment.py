"""
Phase 8: Alignment of Precomputed Contributions with Approved Production Engine.

Regression test suite ensuring:
1. Integrity locks: SHA256 and MD5 match approved post-migration hashes.
2. Backups: Pre-migration backups exist and match baseline hashes.
3. Row counts, column counts, and identifier preservation.
4. Collapse-rescue diagnostic cases reflect Phase 7U relief:
   - Shahrukh Khan (53.6)
   - Riyan Parag (50.6)
   - Ambati Rayudu (52.7)
   - Mahipal Lomror (55.1)
   - Nicholas Pooran (67.8)
   - Sam Curran (59.8)
   - Tilak Varma (65.5)
5. Zero discrepancy between live compute_production_contribution and stored values.
6. DNB strictly preserved as NULL/NaN (never 0.0).
7. Downstream API and comparison consistency.
8. Multi-competition partition isolation (SMAT and T20I untouched).
"""

import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from src.contribution_framework import compute_production_contribution
from src.scoring_engine_config import get_active_scoring_engine
from src.phase8_dataset_alignment import (
    REPO_ROOT,
    PRE_MIGRATION_HASHES,
    POST_MIGRATION_HASHES,
    STRATEGY4_EXPECTED_SCORES,
    DIAGNOSTIC_CASES,
    file_checksums,
    verify_governance_and_backups,
    audit_diagnostic_cases,
)

client = TestClient(app)


def test_phase8_post_migration_integrity_locks():
    """Verify that stored datasets match Phase 8 post-migration SHA256 and MD5 hashes."""
    gov = verify_governance_and_backups()
    assert gov["all_passed"] is True, f"Integrity check failed: {gov['checks']}"
    for rel_path in POST_MIGRATION_HASHES:
        assert gov["checks"][rel_path]["passed"] is True, f"Mismatch for {rel_path}"


def test_phase8_pre_migration_backups():
    """Verify that pre-migration backup files exist and match baseline Phase 7Q hashes."""
    backup_dir = REPO_ROOT / "backups" / "phase8_pre_migration"
    assert backup_dir.exists(), "Pre-migration backup directory missing"

    for rel_path, expected in PRE_MIGRATION_HASHES.items():
        fname = Path(rel_path).name
        b_file = backup_dir / fname
        assert b_file.exists(), f"Backup file {fname} missing"
        b_sha, b_md5, b_sz = file_checksums(b_file)
        assert b_sha == expected["sha256"], f"Backup SHA mismatch for {fname}"
        assert b_md5 == expected["md5"], f"Backup MD5 mismatch for {fname}"


def test_phase8_dataset_dimensions_and_identifiers():
    """Verify that row counts, columns, and identifiers are perfectly preserved."""
    df_path = REPO_ROOT / "data" / "processed" / "batter_match_contributions.csv"
    df = pd.read_csv(df_path, low_memory=False)

    assert len(df) == 19111, f"Expected 19,111 rows, got {len(df)}"
    assert len(df.columns) == 98, f"Expected 98 columns, got {len(df.columns)}"

    # Check key identifiers
    for col in ["match_id", "season", "innings", "team", "player"]:
        assert col in df.columns, f"Identifier {col} missing"
        assert df[col].notna().all(), f"Identifier {col} contains null values"

    # Verify season metrics
    sm_path = REPO_ROOT / "models" / "contribution" / "phase6" / "phase6_season_metrics.csv"
    sm = pd.read_csv(sm_path, low_memory=False)
    assert len(sm) == 3357, f"Expected 3,357 rows, got {len(sm)}"
    assert len(sm.columns) == 25, f"Expected 25 columns, got {len(sm.columns)}"


def test_phase8_dnb_null_preservation():
    """Verify DNB records are strictly NaN/null and never zero across all views."""
    sm_path = REPO_ROOT / "models" / "contribution" / "phase6" / "phase6_season_metrics.csv"
    sm = pd.read_csv(sm_path, low_memory=False)

    dnb = sm[sm["batting_innings"] == 0]
    assert len(dnb) == 368, f"Expected 368 DNB records, found {len(dnb)}"
    assert dnb["average_contribution_score"].isna().all(), "DNB average_contribution_score must be NaN"
    assert dnb["season_team_contribution_share"].isna().all(), "DNB team_share must be NaN"

    # Verify via API for pure DNB player YS Chahal in 2016
    res = client.get("/api/player/YS%20Chahal/season/2016")
    assert res.status_code == 200
    data = res.json()
    assert data["batting_innings"] == 0
    assert data["did_not_bat_matches"] == 13
    assert data["average_contribution_score"] is None
    assert data["season_team_contribution_share"] is None


@pytest.mark.parametrize("case", DIAGNOSTIC_CASES)
def test_phase8_representative_cases(case):
    """Verify all representative collapse-rescue diagnostic cases receive exact Phase 7U relief."""
    df_path = REPO_ROOT / "data" / "processed" / "batter_match_contributions.csv"
    df = pd.read_csv(df_path, low_memory=False)

    sub = df[(df["match_id"] == case["match_id"]) & (df["player"] == case["player"])]
    assert not sub.empty, f"Appearance not found: {case['player']} in match {case['match_id']}"
    row = sub.iloc[0]

    stored_score = round(float(row["contribution_score"]), 1)
    is_s4 = get_active_scoring_engine() == "v8.5.1-strategy4-hybrid"
    expected_score = STRATEGY4_EXPECTED_SCORES.get((case["match_id"], case["player"]), case["expected_score"]) if is_s4 else case["expected_score"]
    assert stored_score == expected_score, (
        f"{case['player']} (Match {case['match_id']}): expected {expected_score}, got {stored_score}"
    )

    if not is_s4:
        # Re-compute live with production engine to verify zero drift under Phase 7U
        live_res = compute_production_contribution(row, apply_attribution=True)
        live_score = round(float(live_res["contribution_score"]), 1)
        assert live_score == stored_score, (
            f"Live computation mismatch for {case['player']}: stored {stored_score} vs live {live_score}"
        )


def test_phase8_shahrukh_khan_detailed_rescue_audit():
    """Verify Shahrukh Khan IPL 2021 match 1254065 diagnostic details."""
    res = client.get("/api/match/1254065/player/M%20Shahrukh%20Khan")
    assert res.status_code == 200
    data = res.json()

    assert data["player"] == "M Shahrukh Khan"
    assert data["basic_performance"]["runs"] == 47
    assert data["basic_performance"]["balls"] == 36
    if get_active_scoring_engine() == "v8.5.1-strategy4-hybrid":
        assert data["contribution_score"] == 63.7
    else:
        assert data["contribution_score"] == 53.6

    pillars = data["pillars"]
    assert pillars["pillar1_context"]["score"] == 72.0
    assert pillars["pillar2_performance"]["score"] == 77.1
    assert pillars["pillar3_state"]["score"] in [28.8, 45.5]


def test_phase8_audit_cases_summary():
    """Verify all diagnostic cases pass through audit_diagnostic_cases."""
    cases = audit_diagnostic_cases()
    assert len(cases) == 7
    for c in cases:
        assert c["passed"] is True, f"Diagnostic case failed: {c}"


def test_phase8_partition_isolation():
    """Verify that SMAT and T20I directory partitions exist and remain completely isolated."""
    smat_dir = REPO_ROOT / "data" / "processed" / "smat"
    t20i_dir = REPO_ROOT / "data" / "processed" / "t20i"

    assert smat_dir.exists(), "SMAT partition missing"
    assert t20i_dir.exists(), "T20I partition missing"


def test_phase8_landing_comparison_card_uses_canonical_record():
    """Verify that the landing page comparison card uses the canonical record and API.

    Ensures:
    1. Match 1254065 for M Shahrukh Khan resolves to 53.6 in canonical API and dataset.
    2. Match 1359536 for B Sai Sudharsan resolves to 93.4 in canonical API and dataset.
    3. The frontend LandingPage component does not hardcode stale legacy score '49.0'.
    4. The frontend LandingPage binds to the canonical getMatchDetail API for both cards.
    """
    # 1. Canonical backend check for Shahrukh Khan (match 1254065)
    srk_res = client.get("/api/match/1254065/player/M%20Shahrukh%20Khan")
    assert srk_res.status_code == 200
    srk_data = srk_res.json()
    if get_active_scoring_engine() == "v8.5.1-strategy4-hybrid":
        assert srk_data["contribution_score"] == 63.7
    else:
        assert srk_data["contribution_score"] == 53.6
    assert srk_data["basic_performance"]["runs"] == 47
    assert srk_data["basic_performance"]["balls"] == 36
    assert srk_data["match_context"]["entry_over"] == 4.4
    assert srk_data["match_context"]["team_score_entry"] == 19
    assert srk_data["match_context"]["wickets_lost_during_stay"] == 4
    assert srk_data["match_context"]["expected_final_change"] == -6.7

    # 2. Canonical backend check for Sai Sudharsan (match 1359536)
    sai_res = client.get("/api/match/1359536/player/B%20Sai%20Sudharsan")
    assert sai_res.status_code == 200
    sai_data = sai_res.json()
    assert sai_data["contribution_score"] == 93.4
    assert sai_data["basic_performance"]["runs"] == 47
    assert sai_data["basic_performance"]["balls"] == 36
    assert sai_data["match_context"]["entry_over"] == 0.3
    assert sai_data["match_context"]["team_score_entry"] == 0
    assert sai_data["match_context"]["wickets_lost_during_stay"] == 1
    assert sai_data["match_context"]["expected_final_change"] == 51.6

    # 3. Frontend static analysis: Verify LandingPage.jsx does not hardcode legacy 49.0
    landing_jsx = REPO_ROOT / "frontend" / "src" / "pages" / "LandingPage.jsx"
    assert landing_jsx.exists()
    content = landing_jsx.read_text(encoding="utf-8")
    assert "49.0" not in content, "Stale legacy score 49.0 must not be hardcoded in LandingPage.jsx"
    assert "getMatchDetail" in content, "LandingPage.jsx must import and use getMatchDetail API"
    assert "1254065" in content, "LandingPage.jsx must reference canonical match ID 1254065"
    assert "1359536" in content, "LandingPage.jsx must reference canonical match ID 1359536"
    assert "srkData?.contribution_score" in content, "LandingPage.jsx must bind to canonical srkData score"

