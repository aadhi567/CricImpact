"""
Tests for Phase 8: Missing-Value Safety and Input Validation.

Verifies:
1. Missing (None), NaN, Infinite (+/- inf), and negative expected_runs are caught explicitly.
2. Invalid inputs are NEVER silently converted into normal scores.
3. Established DNB null rules are strictly preserved (DNB records return None).
4. Invalid inputs do not propagate NaN into P1, P2, P3, or final scores.
5. Valid inputs evaluate deterministically across Production and Candidates A, B, C.
"""

import math
import numpy as np
import pytest

from src.phase8_collapse_attribution_prototype import (
    validate_expected_runs_input,
    evaluate_all_candidates,
    compute_candidate_a_raw_p3,
    compute_candidate_b_raw_p3,
    compute_candidate_c_raw_p3,
)


def test_missing_expected_runs():
    """Verify missing (None) expected_runs is caught safely and does not propagate NaN."""
    row = {
        "player": "Test Batter",
        "match_id": "999001",
        "innings": 1,
        "actual_runs": 25.0,
        "balls_faced": 18,
        "expected_runs": None,
        "trajectory_deviation_change": -10.0,
        "expected_final_change": -5.0,
    }
    is_valid, val, err = validate_expected_runs_input(row)
    assert is_valid is False
    assert val is None
    assert err == "MISSING_EXPECTED_RUNS"

    res = evaluate_all_candidates(row)
    assert res["is_valid"] is False
    assert res["error"] == "MISSING_EXPECTED_RUNS"
    assert res["production"]["final_contribution_score"] is None
    assert res["candidate_a"]["final_contribution_score"] is None
    assert res["candidate_b"]["final_contribution_score"] is None
    assert res["candidate_c"]["final_contribution_score"] is None


def test_nan_expected_runs():
    """Verify NaN expected_runs is caught safely and does not propagate NaN."""
    row = {
        "player": "Test Batter",
        "match_id": "999002",
        "innings": 1,
        "actual_runs": 25.0,
        "balls_faced": 18,
        "expected_runs": float("nan"),
        "trajectory_deviation_change": -10.0,
        "expected_final_change": -5.0,
    }
    is_valid, val, err = validate_expected_runs_input(row)
    assert is_valid is False
    assert val is None
    assert err == "NAN_EXPECTED_RUNS"

    res = evaluate_all_candidates(row)
    assert res["is_valid"] is False
    assert res["error"] == "NAN_EXPECTED_RUNS"
    assert res["candidate_a"]["final_contribution_score"] is None
    assert res["candidate_b"]["final_contribution_score"] is None
    assert res["candidate_c"]["final_contribution_score"] is None


def test_infinite_expected_runs():
    """Verify +inf and -inf expected_runs are caught safely."""
    row_pos = {
        "player": "Test Batter",
        "match_id": "999003",
        "innings": 1,
        "actual_runs": 25.0,
        "balls_faced": 18,
        "expected_runs": float("inf"),
        "trajectory_deviation_change": -10.0,
        "expected_final_change": -5.0,
    }
    is_valid, val, err = validate_expected_runs_input(row_pos)
    assert is_valid is False
    assert err == "INFINITE_EXPECTED_RUNS"

    row_neg = dict(row_pos, expected_runs=float("-inf"))
    is_valid_neg, _, err_neg = validate_expected_runs_input(row_neg)
    assert is_valid_neg is False
    assert err_neg == "INFINITE_EXPECTED_RUNS"


def test_negative_expected_runs():
    """Verify negative expected_runs (< 0) is flagged as invalid."""
    row = {
        "player": "Test Batter",
        "match_id": "999004",
        "innings": 1,
        "actual_runs": 15.0,
        "balls_faced": 10,
        "expected_runs": -4.5,
    }
    is_valid, val, err = validate_expected_runs_input(row)
    assert is_valid is False
    assert err == "NEGATIVE_EXPECTED_RUNS"


def test_non_numeric_expected_runs():
    """Verify string or non-numeric expected_runs is flagged."""
    row = {
        "player": "Test Batter",
        "match_id": "999005",
        "innings": 1,
        "actual_runs": 15.0,
        "balls_faced": 10,
        "expected_runs": "corrupt_data",
    }
    is_valid, val, err = validate_expected_runs_input(row)
    assert is_valid is False
    assert err == "NON_NUMERIC_EXPECTED_RUNS"


def test_dnb_preservation():
    """Verify DNB records are preserved as null and not assigned a contribution score."""
    dnb_row = {
        "player": "DNB Player",
        "match_id": "999006",
        "innings": 1,
        "actual_runs": 0.0,
        "balls_faced": 0,
        "dnb": True,
        "expected_runs": 0.0,
    }
    is_valid, val, err = validate_expected_runs_input(dnb_row)
    assert is_valid is False
    assert err == "DNB_RECORD"

    res = evaluate_all_candidates(dnb_row)
    assert res["is_valid"] is False
    assert res["production"]["final_contribution_score"] is None
    assert res["candidate_a"]["final_contribution_score"] is None
    assert res["candidate_b"]["final_contribution_score"] is None
    assert res["candidate_c"]["final_contribution_score"] is None


def test_valid_input_determinism():
    """Verify valid inputs process properly across all candidates without NaN."""
    valid_row = {
        "player": "Solid Batter",
        "match_id": "999007",
        "innings": 1,
        "actual_runs": 45.0,
        "balls_faced": 30,
        "expected_runs": 35.0,
        "trajectory_deviation_change": -8.0,
        "expected_final_change": 4.0,
        "entry_over": 6.0,
        "dismissal_over": 15.0,
        "wickets_lost_during_stay": 2,
        "balls_remaining_exit": 30,
        "wickets_remaining_exit": 6,
        "wicket_resource_change": -1,
        "window_team_rr": 8.0,
        "team_rr_entry": 7.5,
        "expected_final_entry": 160.0,
        "dot_ball_percentage": 30.0,
        "actual_sr": 150.0,
        "sr_performance_ratio": 1.25,
        "dismissal_status": "out",
        "innings_number": 1,
    }
    res = evaluate_all_candidates(valid_row)
    assert res["is_valid"] is True
    assert res["delta_r"] == 10.0

    # Ensure no candidate produced NaN
    for cand in ["production", "candidate_a", "candidate_b", "candidate_c"]:
        score = res[cand]["final_contribution_score"]
        assert score is not None
        assert not math.isnan(score)
        assert 0.1 <= score <= 99.9
