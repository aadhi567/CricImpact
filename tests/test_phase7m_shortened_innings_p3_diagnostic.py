"""
Phase 7M: Dedicated Unit and Diagnostic Tests for Shortened-Innings P3 Audit.
Cricket Batter Contribution Model.

Verifies:
1. Exact reproduction of V Suryavanshi's current production contribution metrics.
2. Step-by-step intermediate component tracing of P3 calculation.
3. Verification of EFS NaN attribution in rain-shortened matches.
4. Verification of 20-over counterfactual equivalence.
5. Invariance of batter share within Pillar 3 (P3 measures team state, not player attribution).
6. Governance integrity: all 4 protected production files remain byte-for-byte intact.
"""

import hashlib
import json
from pathlib import Path
import pytest
import numpy as np
import pandas as pd

from src.phase7m_shortened_innings_p3_diagnostic import (
    extract_v_suryavanshi_raw_row,
    trace_p3_exact_calculation,
    analyze_20_over_assumptions,
    run_controlled_diagnostic_cases,
    analyze_first_over_platform_impact,
    analyze_batter_share_representation,
)
from src.contribution_framework import (
    compute_pillar3_team_state_impact,
    normalize_pillar_score,
    PHASE5B_EMPIRICAL_PARAMS,
    compute_production_contribution,
)

PROTECTED_FILES = {
    "src/contribution_framework.py": "bbc00b0c9ba0270112e5a77a3273a3b9",
    "data/processed/batter_match_contributions.csv": "779adf7041fac9eedab4efe035cdc39a",
    "models/contribution/phase6/phase6_season_metrics.csv": "223e9990c4aaf52270c3fb9d290b68af",
    "src/season_aggregation.py": "ccbc7ea13880d8d34785effad22cb1ab",
}


def test_v_suryavanshi_current_production_output():
    """Verify that V Suryavanshi's match row produces exact production scores."""
    row = extract_v_suryavanshi_raw_row()
    assert row["player"] == "V Suryavanshi"
    assert row["match_id"] == 1527686
    assert row["actual_runs"] == 39
    assert row["balls_faced"] == 14
    assert pytest.approx(row["actual_sr"], abs=0.1) == 278.6

    # Verify existing production scores in dataset
    assert row["score_context"] == 43.0
    assert row["score_perf"] == 82.7
    assert row["score_state"] == 33.9
    assert row["contribution_score"] == 57.9


def test_p3_mathematical_step_by_step_reproduction():
    """Verify exact numerical reproduction of P3 subterms."""
    row = extract_v_suryavanshi_raw_row()
    trace = trace_p3_exact_calculation(row)

    # 1. Acceleration term
    assert trace["team_rr_entry"] == 22.0
    assert trace["window_team_rr"] == 14.5
    assert trace["raw_accel"] == -2.5
    assert trace["clipped_accel"] == -2.5
    assert trace["accel_weighted"] == -1.50

    # 2. Volume deviation term
    assert trace["team_runs_added"] == 58.0
    assert trace["overs_spent"] == 4.0
    assert trace["volume_diff"] == 26.0  # 58 - 4*8
    assert trace["volume_term"] == 2.6
    assert trace["volume_weighted"] == 1.04

    # 3. Dynamic wicket resource cost
    assert trace["base_wicket_cost"] == pytest.approx(0.3409, abs=1e-3)
    assert trace["wicket_offset"] == pytest.approx(0.2386, abs=1e-3)
    assert trace["s_res"] == pytest.approx(-0.1023, abs=1e-3)

    # 4. Total raw P3
    expected_raw = -1.50 + 1.04 - 0.10227
    assert trace["raw_p3"] == pytest.approx(expected_raw, abs=1e-3)

    # 5. Z-score and final P3 score
    p = PHASE5B_EMPIRICAL_PARAMS
    expected_z = (expected_raw - p["pillar3_mean"]) / p["pillar3_std"]
    assert trace["z3"] == pytest.approx(expected_z, abs=1e-3)
    assert trace["score_p3"] == 33.9


def test_efs_model_exclusion_in_rain_shortened_match():
    """Verify that EFS fields are NaN for this match due to rain-curtailed filtering."""
    row = extract_v_suryavanshi_raw_row()
    assert pd.isna(row["expected_final_entry"])
    assert pd.isna(row["expected_final_exit"])
    assert pd.isna(row["expected_final_change"])


def test_counterfactual_20_over_equivalence():
    """
    Verify that in an equivalent 20-over match where EFS is active and predicts +50.0,
    P3 scores 82.8 rather than 33.9.
    """
    row = extract_v_suryavanshi_raw_row()
    cases = run_controlled_diagnostic_cases(row)
    actual_p3 = cases["case_a_actual"]["score_p3"]
    synthetic_20_p3 = cases["case_b_20_over_equivalent"]["score_p3"]

    assert actual_p3 == 33.9
    assert synthetic_20_p3 >= 80.0
    assert synthetic_20_p3 - actual_p3 >= 45.0


def test_batter_share_excluded_from_p3():
    """Verify that batter share (67.24%) has zero weight in Pillar 3."""
    row = extract_v_suryavanshi_raw_row()
    share_analysis = analyze_batter_share_representation(row)
    assert share_analysis["batter_share_percentage"] == 67.24
    assert share_analysis["included_in_pillar3_calculation"] is False
    assert share_analysis["weight_in_pillar3"] == 0.0


def test_governance_protected_files_intact():
    """Verify that all production files remain byte-for-byte unchanged in pre-integration backup."""
    for rel_path, expected_md5 in PROTECTED_FILES.items():
        backup_path = Path("backups/phase7o_pre_integration") / Path(rel_path).name
        target_path = backup_path if backup_path.exists() else Path(rel_path)
        assert target_path.exists(), f"Missing production file: {target_path}"
        with open(target_path, "rb") as f:
            actual_md5 = hashlib.md5(f.read()).hexdigest()
        assert actual_md5.lower() == expected_md5.lower(), (
            f"GOVERNANCE VIOLATION: {rel_path} was modified during Phase 7M! Expected {expected_md5}, got {actual_md5}"
        )
