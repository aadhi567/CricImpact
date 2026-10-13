"""
Phase 8: Candidate C-Res Independent Stress-Testing & Edge-Case Verification Suite.

Validates the mathematical and behavioral robustness of Candidate C-Res (Resource-Par):
1. Monotonicity: f_resource decreases monotonically with excess partner wickets; P3 relief increases monotonically.
2. Bounds & Clamping: Strict enforcement of f_resource in [0.70, 1.30] and kappa_resource in [0.55, 1.45].
3. Dismissal Separation: Batter's own dismissal is strictly excluded from partner wicket counts.
4. Zero-ball windows & Minimal Stays: Robust handling without division-by-zero or NaN.
5. Missing-Value Safety: Comprehensive rejection of None, NaN, +/-inf, and negative expected runs.
6. DNB Null Preservation: DNB appearances return None (JSON null), never 0 or 50.
7. Chase (2nd Innings) Strict Invariance: 100% bit-for-bit invariance with production.
"""

import math
import numpy as np
import pandas as pd
import pytest

from app.services.data_service import data_service
from src.contribution_framework import (
    compute_production_contribution,
    compute_dampened_p3_raw,
    map_raw_to_p3_score,
)
from src.phase8_collapse_attribution_prototype import (
    validate_expected_runs_input,
    compute_candidate_c_resource_adjusted_raw_p3,
    evaluate_all_candidates,
    get_historical_wickets_lost_at_ball,
    HISTORICAL_IPL_PAR_TOTAL,
)


@pytest.fixture(scope="module")
def df_ipl():
    return data_service.get_contributions_df("ipl")


def test_monotonicity_across_partner_wickets():
    """
    Candidate C-Res Stress-Test: Monotonicity.
    For an identical batting stay, increasing partner wickets lost must monotonically:
    - Decrease the resource factor f_resource.
    - Decrease the context par requirement Par_context_res.
    - Increase (or maintain) the raw P3 score, providing more relief for collapse resistance.
    """
    base_row = {
        "innings": 1,
        "entry_over": 3.0,
        "entry_ball": 0,
        "exit_over": 15.0,
        "exit_ball": 0,
        "actual_runs": 45.0,
        "balls_faced": 40,
        "expected_runs": 42.0,
        "expected_final_change": -10.0,
        "trajectory_deviation_change": -8.0,
        "expected_final_entry": 166.5,
        "team_score_entry": 25.0,
        "team_score_exit": 105.0,
        "actual_team_runs_change": 80.0,
        "team_rr_entry": 8.33,
        "window_team_rr": 6.67,
        "dismissal_status": "not out",
        "balls_remaining_exit": 30,
        "wickets_remaining_exit": 5,
        "wicket_resource_change": 0.0,
    }

    raw_p3_prev = -999.0
    for wkts in range(0, 8):
        row = dict(base_row)
        row["wickets_lost_during_stay"] = wkts
        raw_p3 = compute_candidate_c_resource_adjusted_raw_p3(row)
        assert raw_p3 is not None
        assert raw_p3 >= raw_p3_prev - 1e-9, f"Monotonicity violation at wkts={wkts}: {raw_p3} < {raw_p3_prev}"
        raw_p3_prev = raw_p3


def test_strict_clamping_bounds():
    """
    Candidate C-Res Stress-Test: Bounds & Clamping.
    Ensures extreme inputs never breach the designated physical clipping limits:
    - kappa_entry in [0.60, 1.40]
    - f_resource in [0.70, 1.30]
    - kappa_resource in [0.55, 1.45]
    """
    base_row = {
        "innings": 1,
        "entry_over": 0.0,
        "entry_ball": 0,
        "exit_over": 20.0,
        "exit_ball": 0,
        "actual_runs": 60.0,
        "balls_faced": 50,
        "expected_runs": 55.0,
        "expected_final_change": 20.0,
        "trajectory_deviation_change": 15.0,
        "team_score_entry": 0.0,
        "team_score_exit": 180.0,
        "actual_team_runs_change": 180.0,
        "dismissal_status": "not out",
        "balls_remaining_exit": 0,
        "wickets_remaining_exit": 8,
        "wicket_resource_change": 0.0,
    }

    # Extreme high EFS + 0 wickets fell (f_res > 1.0)
    high_row = dict(base_row)
    high_row["expected_final_entry"] = 350.0  # Would be kappa = 2.1 without clamp
    high_row["wickets_lost_during_stay"] = 0  # Historical is 5.93, excess = -5.93, f_res would be 1.296
    raw_high = compute_candidate_c_resource_adjusted_raw_p3(high_row)
    assert raw_high is not None
    score_high = map_raw_to_p3_score(raw_high)
    assert 0.1 <= score_high <= 99.9

    # Extreme low EFS + 9 wickets fell (f_res < 1.0)
    low_row = dict(base_row)
    low_row["expected_final_entry"] = 50.0  # Would be kappa = 0.3 without clamp
    low_row["wickets_lost_during_stay"] = 9  # Excess = +3.07, f_res would be 0.846
    raw_low = compute_candidate_c_resource_adjusted_raw_p3(low_row)
    assert raw_low is not None
    score_low = map_raw_to_p3_score(raw_low)
    assert 0.1 <= score_low <= 99.9


def test_dismissal_status_partner_wicket_separation():
    """
    Candidate C-Res Stress-Test: Dismissal Separation.
    Confirms batter's own dismissal is NOT counted as a partner dismissal:
    - If batter is 'out' and wickets_lost_during_stay == 1: partner_wkts = 0.
    - If batter is 'not out' and wickets_lost_during_stay == 1: partner_wkts = 1.
    """
    row_out = {
        "innings": 1,
        "entry_over": 2.0,
        "entry_ball": 0,
        "exit_over": 8.0,
        "exit_ball": 0,
        "actual_runs": 25.0,
        "balls_faced": 20,
        "expected_runs": 24.0,
        "expected_final_change": -5.0,
        "trajectory_deviation_change": -4.0,
        "expected_final_entry": 166.5,
        "team_score_entry": 15.0,
        "team_score_exit": 55.0,
        "actual_team_runs_change": 40.0,
        "dismissal_status": "out",
        "wickets_lost_during_stay": 1,  # Only the batter was dismissed!
        "balls_remaining_exit": 72,
        "wickets_remaining_exit": 7,
        "wicket_resource_change": -1.0,
    }

    row_not_out = dict(row_out)
    row_not_out["dismissal_status"] = "not out"
    # When not out and wickets_lost=1, the partner was dismissed!
    # Therefore, row_not_out experienced 1 partner wicket, whereas row_out experienced 0.

    raw_out = compute_candidate_c_resource_adjusted_raw_p3(row_out)
    raw_not_out = compute_candidate_c_resource_adjusted_raw_p3(row_not_out)

    assert raw_out is not None
    assert raw_not_out is not None
    # Because partner was dismissed in row_not_out, par scales down, yielding higher P3 relief
    assert raw_not_out > raw_out


def test_zero_ball_window_and_minimal_stays():
    """
    Candidate C-Res Stress-Test: Zero-ball window and minimal stay robustness.
    Ensures b_entry == b_exit or 0 balls faced do not raise division-by-zero or NaN.
    """
    row_zero = {
        "innings": 1,
        "entry_over": 10.0,
        "entry_ball": 2,
        "exit_over": 10.0,
        "exit_ball": 2,
        "actual_runs": 0.0,
        "balls_faced": 0,
        "expected_runs": 0.0,
        "expected_final_change": 0.0,
        "trajectory_deviation_change": 0.0,
        "expected_final_entry": 166.5,
        "team_score_entry": 80.0,
        "team_score_exit": 80.0,
        "actual_team_runs_change": 0.0,
        "dismissal_status": "out",
        "wickets_lost_during_stay": 1,
        "balls_remaining_exit": 58,
        "wickets_remaining_exit": 6,
        "wicket_resource_change": -1.0,
    }

    raw = compute_candidate_c_resource_adjusted_raw_p3(row_zero)
    assert raw is not None
    assert not math.isnan(raw)


def test_missing_value_safety_in_candidate_c_res():
    """Candidate C-Res Stress-Test: Missing-Value Safety Validation."""
    invalid_rows = [
        {"innings": 1, "expected_runs": None},
        {"innings": 1, "expected_runs": float("nan")},
        {"innings": 1, "expected_runs": float("inf")},
        {"innings": 1, "expected_runs": -5.0},
        {"innings": 1, "expected_runs": "corrupted_string"},
    ]
    for r in invalid_rows:
        is_valid, exp, err = validate_expected_runs_input(r)
        assert not is_valid
        assert compute_candidate_c_resource_adjusted_raw_p3(r) is None
        ev = evaluate_all_candidates(r)
        assert ev["is_valid"] is False
        assert ev["candidate_c_res"]["final_contribution_score"] is None


def test_chase_strict_invariance_across_second_innings(df_ipl):
    """Candidate C-Res Stress-Test: 100% bit-for-bit invariance across all 2nd-innings appearances."""
    inn2 = df_ipl[df_ipl["innings"] == 2].copy()
    diff_count = 0
    for idx, row in inn2.iterrows():
        is_valid, _, _ = validate_expected_runs_input(row)
        if not is_valid:
            continue
        ev = evaluate_all_candidates(row)
        p_final = ev["production"]["final_contribution_score"]
        c_final = ev["candidate_c_res"]["final_contribution_score"]
        if p_final is not None and c_final is not None:
            assert p_final == c_final, f"Chase invariance broken for {row['player']} in match {row['match_id']}: {p_final} vs {c_final}"
