"""
Unit and Integration Tests for Phase 5B: Contextual Batter Contribution Model.

Tests cover:
1. Four Pillars Calculation & Equal 25% Conceptual Priority (P1, P2, P3, P4).
2. Output A Scale Properties (0 to 100 continuous, Par ~ 50.0).
3. Output B Team Contribution Share Properties (rectified positive attribution, sum to 100%).
4. Section 17 & 18: Did-Not-Bat (DNB) Rule (NULL score, NULL share, no dilution).
5. Section 18: Genuine short batting innings (1 run not out evaluated, NOT NULL).
6. Section 20: All 16 Required Tests (including Section 15 Cameo Cases A through D).
7. Section 19: Season Aggregation Methodology (reporting all required fields).
8. Section 21: Strict Leakage Audit & Complete Outcome Invariance.
9. Section 8: Pillar 1 Context Coefficients Sensitivity & Robustness.
"""

import pytest
import numpy as np
import pandas as pd

from src.contribution_framework import (
    compute_pillar1_match_context,
    compute_pillar2_batter_performance,
    compute_pillar3_team_state_impact,
    compute_pillar4_counterfactual_value,
    normalize_pillar_score,
    compute_phase5b_contribution,
    compute_season_aggregation,
    compute_team_contribution_shares,
    PHASE5B_EMPIRICAL_PARAMS,
)


# ----------------------------------------------------------------------
# 1. Four Pillars & Equal Conceptual Weighting (25% each)
# ----------------------------------------------------------------------
def test_four_pillars_computation_and_weights():
    sample_row = {
        "innings": 1,
        "entry_over": 10.0,
        "balls_remaining_entry": 60,
        "wickets_remaining_entry": 7,
        "team_rr_entry": 7.5,
        "actual_runs": 30.0,
        "balls_faced": 20,
        "actual_sr": 150.0,
        "boundary_percentage": 50.0,
        "run_deviation": 8.0,
        "sr_deviation": 20.0,
        "opportunity_usage": 0.33,
        "dismissal_status": "not out",
        "balls_remaining_exit": 40,
        "wickets_remaining_exit": 7,
        "wicket_resource_change": 0,
        "expected_final_change": 10.0,
        "window_team_rr": 9.0,
        "trajectory_deviation_change": 8.0,
        "overs_spent": 3.3,
    }

    res = compute_phase5b_contribution(sample_row)

    # All 4 pillar z-scores and normalized scores must exist and be finite
    for k in ["z_context", "z_perf", "z_state", "z_cf"]:
        assert res[k] is not None
        assert np.isfinite(res[k])

    for k in ["pillar1_context_score", "pillar2_perf_score", "pillar3_state_score", "pillar4_cf_score"]:
        assert res[k] is not None
        assert 0.1 <= res[k] <= 99.9

    # Output A must be bounded and finite
    assert 0.1 <= res["contribution_score"] <= 99.9
    assert np.isfinite(res["raw_contribution"])

    # Verify mathematical equal weighting in raw contribution (25% each)
    expected_c_raw = round(0.25 * res["z_context"] + 0.25 * res["z_perf"] + 0.25 * res["z_state"] + 0.25 * res["z_cf"], 4)
    assert abs(res["raw_contribution"] - expected_c_raw) < 1e-3


def test_contribution_score_par_calibration():
    # Par benchmark verification:
    # A situational median performance aligns with Par ~ 50.0
    par_row = {
        "innings": 1,
        "entry_over": 10.0,
        "balls_remaining_entry": 60,
        "wickets_remaining_entry": 8,
        "team_rr_entry": 7.5,
        "actual_runs": 19.8,
        "balls_faced": 16,
        "actual_sr": 125.0,
        "boundary_percentage": 45.0,
        "run_deviation": 0.0,
        "sr_deviation": 0.0,
        "opportunity_usage": 0.27,
        "dismissal_status": "out",
        "balls_remaining_exit": 44,
        "wickets_remaining_exit": 7,
        "wicket_resource_change": -1,
        "expected_final_change": 0.0,
        "window_team_rr": 7.5,
        "trajectory_deviation_change": 0.0,
        "overs_spent": 2.7,
    }
    res = compute_phase5b_contribution(par_row)
    assert 45.0 <= res["contribution_score"] <= 55.0


# ----------------------------------------------------------------------
# 2. Output B: Team Contribution Share Properties
# ----------------------------------------------------------------------
def test_team_contribution_share_rectification_and_sum():
    raw_scores = [1.8, 0.9, -0.5, -1.2, 0.3]
    shares = compute_team_contribution_shares(raw_scores, method="rectified_positive")

    # Sum of shares should equal 100%
    assert abs(sum(shares) - 100.0) < 0.2

    # Negative contributors get 0.0% share
    assert shares[2] == 0.0
    assert shares[3] == 0.0

    # Highest contributor gets highest share
    assert shares[0] > shares[1] > shares[4]


def test_team_contribution_share_collapse_innings():
    # If all batters have non-positive impact (team collapses for 49)
    raw_scores = [-1.5, -0.8, -2.0, -1.1, -0.6]
    shares = compute_team_contribution_shares(raw_scores, method="rectified_positive")
    assert len(shares) == 5
    assert abs(sum(shares) - 100.0) < 0.2
    assert shares[0] == 20.0


# ----------------------------------------------------------------------
# 3. Section 17 & 18: DNB Rule vs Genuine Batting
# ----------------------------------------------------------------------
def test_did_not_bat_rule_returns_null():
    dnb_case = {"dnb": True, "player": "YS Chahal"}
    res = compute_phase5b_contribution(dnb_case)

    # Must be strictly None (NULL), never 0.0
    assert res["dnb"] is True
    assert res["contribution_score"] is None
    assert res["raw_contribution"] is None
    assert res["pillar1_context_score"] is None
    assert res["pillar2_perf_score"] is None
    assert res["pillar3_state_score"] is None
    assert res["pillar4_cf_score"] is None


def test_genuine_short_batting_is_evaluated():
    # Section 18: If batter actually participated in a batting event (e.g. 1* off 1 ball),
    # this is genuine batting and MUST be evaluated (not NULL)
    short_inns = {
        "innings": 2,
        "entry_over": 19.5,
        "balls_remaining_entry": 1,
        "wickets_remaining_entry": 5,
        "required_rr_entry": 6.0,
        "rr_gap_entry": 0.0,
        "actual_runs": 1,
        "balls_faced": 1,
        "actual_sr": 100.0,
        "boundary_percentage": 0.0,
        "run_deviation": 0.2,
        "sr_deviation": -25.0,
        "opportunity_usage": 1.0,
        "dismissal_status": "not out",
        "balls_remaining_exit": 0,
        "wickets_remaining_exit": 5,
        "wicket_resource_change": 0,
        "required_rr_change": 6.0,
        "rr_gap_change": 6.0,
        "target_progress_change": 0.05,
    }
    res = compute_phase5b_contribution(short_inns)
    assert res["dnb"] is False
    assert res["contribution_score"] is not None
    assert res["contribution_score"] > 50.0  # Delivered win under pressure


# ----------------------------------------------------------------------
# 4. Section 20: All 16 Required Tests (including Section 15 Cases A-D)
# ----------------------------------------------------------------------

# Required Test 1: 5 balls, 30 runs in death overs (Section 15 Case A)
def test_req_01_death_overs_cameo():
    row = {
        "innings": 1, "entry_over": 19.1, "balls_remaining_entry": 5, "wickets_remaining_entry": 6,
        "team_rr_entry": 8.5, "actual_runs": 30, "balls_faced": 5, "actual_sr": 600.0,
        "boundary_percentage": 100.0, "run_deviation": 18.0, "sr_deviation": 420.0,
        "opportunity_usage": 1.0, "dismissal_status": "not out", "balls_remaining_exit": 0,
        "wickets_remaining_exit": 6, "wicket_resource_change": 0, "expected_final_change": 22.0,
        "window_team_rr": 36.0, "trajectory_deviation_change": 20.0, "overs_spent": 0.8
    }
    res = compute_phase5b_contribution(row)
    # High performance recognition, no short-innings dampener on SR
    assert res["pillar2_perf_score"] >= 95.0
    assert res["contribution_score"] >= 85.0


# Required Test 2: 5 balls, 30 runs early in innings (Section 15 Case B)
def test_req_02_early_cameo():
    row_early = {
        "innings": 1, "entry_over": 7.1, "balls_remaining_entry": 77, "wickets_remaining_entry": 8,
        "team_rr_entry": 7.5, "actual_runs": 30, "balls_faced": 5, "actual_sr": 600.0,
        "boundary_percentage": 100.0, "run_deviation": 18.0, "sr_deviation": 440.0,
        "opportunity_usage": 0.06, "dismissal_status": "not out", "balls_remaining_exit": 72,
        "wickets_remaining_exit": 8, "wicket_resource_change": 0, "expected_final_change": 12.0,
        "window_team_rr": 36.0, "trajectory_deviation_change": 10.0, "overs_spent": 0.8
    }
    res_early = compute_phase5b_contribution(row_early)
    
    row_death = {
        "innings": 1, "entry_over": 19.1, "balls_remaining_entry": 5, "wickets_remaining_entry": 6,
        "team_rr_entry": 8.5, "actual_runs": 30, "balls_faced": 5, "actual_sr": 600.0,
        "boundary_percentage": 100.0, "run_deviation": 18.0, "sr_deviation": 420.0,
        "opportunity_usage": 1.0, "dismissal_status": "not out", "balls_remaining_exit": 0,
        "wickets_remaining_exit": 6, "wicket_resource_change": 0, "expected_final_change": 22.0,
        "window_team_rr": 36.0, "trajectory_deviation_change": 20.0, "overs_spent": 0.8
    }
    res_death = compute_phase5b_contribution(row_death)

    # Section 4 & 15: Performance is equally explosive in both, but complete contribution differs
    assert res_early["pillar2_perf_score"] == res_death["pillar2_perf_score"]
    assert res_early["pillar1_context_score"] < res_death["pillar1_context_score"]
    assert res_early["contribution_score"] < res_death["contribution_score"]


# Required Test 3: 5 balls, 30 runs when team RR is already very high (Section 15 Case C)
def test_req_03_high_team_rr_cameo():
    row_high_rr = {
        "innings": 1, "entry_over": 16.0, "balls_remaining_entry": 24, "wickets_remaining_entry": 8,
        "team_rr_entry": 12.0, "actual_runs": 30, "balls_faced": 5, "actual_sr": 600.0,
        "boundary_percentage": 100.0, "run_deviation": 16.0, "sr_deviation": 400.0,
        "opportunity_usage": 0.2, "dismissal_status": "not out", "balls_remaining_exit": 19,
        "wickets_remaining_exit": 8, "wicket_resource_change": 0, "expected_final_change": 15.0,
        "window_team_rr": 36.0, "trajectory_deviation_change": 12.0, "overs_spent": 0.8
    }
    res_high_rr = compute_phase5b_contribution(row_high_rr)

    row_death = {
        "innings": 1, "entry_over": 19.1, "balls_remaining_entry": 5, "wickets_remaining_entry": 6,
        "team_rr_entry": 8.5, "actual_runs": 30, "balls_faced": 5, "actual_sr": 600.0,
        "boundary_percentage": 100.0, "run_deviation": 18.0, "sr_deviation": 420.0,
        "opportunity_usage": 1.0, "dismissal_status": "not out", "balls_remaining_exit": 0,
        "wickets_remaining_exit": 6, "wicket_resource_change": 0, "expected_final_change": 22.0,
        "window_team_rr": 36.0, "trajectory_deviation_change": 20.0, "overs_spent": 0.8
    }
    res_death = compute_phase5b_contribution(row_death)

    # Section 15 Case C: Do not over-hype solely on SR 600; incremental team impact is lower than Case A
    assert res_high_rr["contribution_score"] < res_death["contribution_score"]
    assert res_high_rr["pillar1_context_score"] < res_death["pillar1_context_score"]


# Required Test 4: High-SR short cameo under pressure (Section 15 Case D)
def test_req_04_high_sr_short_cameo_under_pressure():
    row_pressure = {
        "innings": 2, "entry_over": 16.0, "balls_remaining_entry": 24, "wickets_remaining_entry": 6,
        "team_rr_entry": 6.0, "required_rr_entry": 10.0, "rr_gap_entry": 4.0, "actual_runs": 20,
        "balls_faced": 5, "actual_sr": 400.0, "boundary_percentage": 100.0, "run_deviation": 12.0,
        "sr_deviation": 250.0, "opportunity_usage": 0.21, "dismissal_status": "not out",
        "balls_remaining_exit": 19, "wickets_remaining_exit": 6, "wicket_resource_change": 0,
        "required_rr_change": 2.5, "rr_gap_change": 2.5, "target_progress_change": 0.18
    }
    res = compute_phase5b_contribution(row_pressure)
    # Section 15 Case D: Meaningful positive contribution because it shifts match situation under pressure
    assert res["contribution_score"] >= 75.0
    assert res["pillar1_context_score"] >= 65.0
    assert res["pillar2_perf_score"] >= 90.0


# Required Test 5: Slow innings followed by acceleration (Section 14)
def test_req_05_slow_innings_followed_by_acceleration():
    row_slow = {
        "innings": 1, "entry_over": 10.0, "balls_remaining_entry": 60, "wickets_remaining_entry": 8,
        "team_rr_entry": 6.0, "actual_runs": 20, "balls_faced": 26, "actual_sr": 76.9,
        "boundary_percentage": 30.0, "run_deviation": -8.0, "sr_deviation": -45.0,
        "opportunity_usage": 0.43, "dismissal_status": "out", "balls_remaining_exit": 34,
        "wickets_remaining_exit": 7, "wicket_resource_change": -1, "expected_final_change": -6.0,
        "window_team_rr": 5.5, "trajectory_deviation_change": -5.0, "overs_spent": 4.3
    }
    res = compute_phase5b_contribution(row_slow)
    # Subpar pacing (30-45 score), but not catastrophically blamed
    assert 30.0 <= res["contribution_score"] <= 45.0


# Required Test 6: High runs but low SR
def test_req_06_high_runs_low_sr():
    row_high_runs_low_sr = {
        "innings": 1, "entry_over": 2.0, "balls_remaining_entry": 108, "wickets_remaining_entry": 9,
        "team_rr_entry": 8.5, "actual_runs": 50, "balls_faced": 48, "actual_sr": 104.2,
        "boundary_percentage": 40.0, "run_deviation": 15.0, "sr_deviation": -20.0,
        "opportunity_usage": 0.44, "dismissal_status": "out", "balls_remaining_exit": 60,
        "wickets_remaining_exit": 7, "wicket_resource_change": -1, "expected_final_change": -2.0,
        "window_team_rr": 6.25, "trajectory_deviation_change": -4.0, "overs_spent": 8.0
    }
    res = compute_phase5b_contribution(row_high_runs_low_sr)
    # Volume is recognized in P2 (~62.3), but pacing and counterfactual dampen score (38-46)
    assert res["pillar2_perf_score"] > 55.0
    assert 38.0 <= res["contribution_score"] <= 48.0


# Required Test 7: Heroic innings in losing team
def test_req_07_heroic_knock_in_losing_team():
    row_heroic = {
        "innings": 2, "entry_over": 3.0, "balls_remaining_entry": 102, "wickets_remaining_entry": 8,
        "required_rr_entry": 10.2, "rr_gap_entry": 3.0, "actual_runs": 82, "balls_faced": 45, "actual_sr": 182.2,
        "boundary_percentage": 72.0, "run_deviation": 48.0, "sr_deviation": 45.0,
        "opportunity_usage": 0.44, "dismissal_status": "out", "balls_remaining_exit": 3,
        "wickets_remaining_exit": 3, "wicket_resource_change": -1, "required_rr_change": 4.5,
        "rr_gap_change": 4.5, "target_progress_change": 0.45, "won_match": False
    }
    res = compute_phase5b_contribution(row_heroic)
    assert res["contribution_score"] >= 80.0


# Required Test 8: Low contribution in winning team
def test_req_08_low_contribution_in_winning_team():
    row_passenger = {
        "innings": 1, "entry_over": 17.0, "balls_remaining_entry": 18, "wickets_remaining_entry": 7,
        "team_rr_entry": 10.0, "actual_runs": 5, "balls_faced": 4, "actual_sr": 125.0,
        "boundary_percentage": 0.0, "run_deviation": -3.0, "sr_deviation": -20.0,
        "opportunity_usage": 0.22, "dismissal_status": "out", "balls_remaining_exit": 14,
        "wickets_remaining_exit": 6, "wicket_resource_change": -1, "expected_final_change": -2.0,
        "window_team_rr": 7.5, "trajectory_deviation_change": -2.0, "overs_spent": 0.7,
        "won_match": True
    }
    res = compute_phase5b_contribution(row_passenger)
    assert 38.0 <= res["contribution_score"] <= 46.0


# Required Test 9: Batter enters 7.2 and exits 13.4 (Section 10 & 12)
def test_req_09_exact_entry_exit_window_7_2_to_13_4():
    row_window = {
        "innings": 1, "entry_over": 7.2, "balls_remaining_entry": 76, "wickets_remaining_entry": 8,
        "team_rr_entry": 7.4, "actual_runs": 35, "balls_faced": 24, "actual_sr": 145.8,
        "boundary_percentage": 55.0, "run_deviation": 8.0, "sr_deviation": 15.0,
        "opportunity_usage": 0.31, "dismissal_status": "out", "balls_remaining_exit": 38,
        "wickets_remaining_exit": 7, "wicket_resource_change": -1, "expected_final_change": 8.0,
        "window_team_rr": 8.2, "trajectory_deviation_change": 6.0, "overs_spent": 6.2
    }
    res = compute_phase5b_contribution(row_window)
    # Strictly evaluated over 7.2 to 13.4 (6.2 overs spent)
    assert res["contribution_score"] >= 58.0


# Required Test 10: Batter remains not-out until innings end (Section 12)
def test_req_10_not_out_until_innings_end():
    row_not_out = {
        "innings": 1, "entry_over": 14.2, "balls_remaining_entry": 34, "wickets_remaining_entry": 7,
        "team_rr_entry": 8.0, "actual_runs": 42, "balls_faced": 22, "actual_sr": 190.9,
        "boundary_percentage": 65.0, "run_deviation": 18.0, "sr_deviation": 45.0,
        "opportunity_usage": 0.65, "dismissal_status": "not out", "balls_remaining_exit": 0,
        "wickets_remaining_exit": 7, "wicket_resource_change": 0, "expected_final_change": 18.0,
        "window_team_rr": 11.4, "trajectory_deviation_change": 15.0, "overs_spent": 5.4
    }
    res = compute_phase5b_contribution(row_not_out)
    assert res["contribution_score"] >= 72.0


# Required Test 11: Zero-ball appearance
def test_req_11_zero_ball_appearance():
    row_zero = {
        "innings": 1, "entry_over": 19.4, "balls_remaining_entry": 2, "wickets_remaining_entry": 4,
        "team_rr_entry": 8.5, "actual_runs": 0, "balls_faced": 0, "actual_sr": 0.0,
        "boundary_percentage": 0.0, "run_deviation": -1.0, "sr_deviation": 0.0,
        "opportunity_usage": 0.0, "dismissal_status": "out", "balls_remaining_exit": 1,
        "wickets_remaining_exit": 3, "wicket_resource_change": -1, "expected_final_change": -1.0,
        "window_team_rr": 0.0, "trajectory_deviation_change": -1.0, "overs_spent": 0.1
    }
    res = compute_phase5b_contribution(row_zero)
    # Genuine batting appearance facing 0 balls: evaluated gracefully, no crash, not NULL
    assert res["dnb"] is False
    assert res["contribution_score"] is not None
    assert 40.0 <= res["contribution_score"] <= 55.0


# Required Test 12: Player did not bat (Section 17)
def test_req_12_player_did_not_bat():
    res = compute_phase5b_contribution({"dnb": True, "player": "YS Chahal"})
    assert res["dnb"] is True
    assert res["contribution_score"] is None
    assert res["raw_contribution"] is None


# Required Test 13: Super Over exclusion (Section 7)
def test_req_13_super_over_exclusion():
    # Super Overs (innings > 2) return NaN in raw pillars and None for contribution score
    row_so = {"innings": 3, "actual_runs": 15, "balls_faced": 5, "actual_sr": 300.0}
    
    assert np.isnan(compute_pillar1_match_context(row_so))
    assert np.isnan(compute_pillar3_team_state_impact(row_so))
    assert np.isnan(compute_pillar4_counterfactual_value(row_so))
    
    res = compute_phase5b_contribution(row_so)
    assert res["super_over"] is True
    assert res["contribution_score"] is None
    assert res["raw_contribution"] is None


# Required Test 14: Rain-shortened innings (Section 20)
def test_req_14_rain_shortened_innings():
    row_rain = {
        "innings": 1, "entry_over": 3.0, "balls_remaining_entry": 42, "wickets_remaining_entry": 9,
        "team_rr_entry": 8.0, "actual_runs": 28, "balls_faced": 14, "actual_sr": 200.0,
        "boundary_percentage": 70.0, "run_deviation": 10.0, "sr_deviation": 60.0,
        "opportunity_usage": 0.33, "dismissal_status": "not out", "balls_remaining_exit": 14,
        "wickets_remaining_exit": 8, "wicket_resource_change": 0, "expected_final_change": None,
        "team_runs_added": 40, "window_team_rr": 13.3, "overs_spent": 3.0
    }
    res = compute_phase5b_contribution(row_rain)
    assert np.isfinite(res["contribution_score"])
    assert res["contribution_score"] >= 70.0


# Required Test 15: High required RR chase (Section 13)
def test_req_15_high_required_rr_chase():
    row_chase_high = {
        "innings": 2, "entry_over": 14.0, "balls_remaining_entry": 36, "wickets_remaining_entry": 6,
        "required_rr_entry": 14.0, "rr_gap_entry": 5.0, "actual_runs": 45, "balls_faced": 20,
        "actual_sr": 225.0, "boundary_percentage": 75.0, "run_deviation": 22.0, "sr_deviation": 65.0,
        "opportunity_usage": 0.55, "dismissal_status": "not out", "balls_remaining_exit": 16,
        "wickets_remaining_exit": 6, "wicket_resource_change": 0, "required_rr_change": 3.5,
        "rr_gap_change": 3.5, "target_progress_change": 0.35
    }
    res = compute_phase5b_contribution(row_chase_high)
    assert res["pillar1_context_score"] >= 85.0
    assert res["contribution_score"] >= 80.0


# Required Test 16: Low required RR chase (Section 18)
def test_req_16_low_required_rr_chase():
    row_chase_low = {
        "innings": 2, "entry_over": 18.4, "balls_remaining_entry": 8, "wickets_remaining_entry": 8,
        "required_rr_entry": 3.0, "rr_gap_entry": -5.0, "actual_runs": 1, "balls_faced": 2, "actual_sr": 50.0,
        "boundary_percentage": 0.0, "run_deviation": -1.0, "sr_deviation": -60.0,
        "opportunity_usage": 0.25, "dismissal_status": "not out", "balls_remaining_exit": 6,
        "wickets_remaining_exit": 8, "wicket_resource_change": 0, "required_rr_change": 0.5,
        "rr_gap_change": 0.5, "target_progress_change": 0.02
    }
    res = compute_phase5b_contribution(row_chase_low)
    assert res["contribution_score"] is not None
    assert 25.0 <= res["contribution_score"] <= 38.0


# ----------------------------------------------------------------------
# 5. Section 19: Season Aggregation Methodology
# ----------------------------------------------------------------------
def test_season_aggregation_fields_and_no_dilution():
    player_inns = [
        {"dnb": False, "contribution_score": 75.0, "raw_contribution": 1.2, "innings": 1, "entry_over": 5.0, "pillar1_context_score": 55.0},
        {"dnb": False, "contribution_score": 85.0, "raw_contribution": 1.8, "innings": 2, "entry_over": 16.0, "pillar1_context_score": 70.0},
        {"dnb": False, "contribution_score": 45.0, "raw_contribution": -0.2, "innings": 1, "entry_over": 10.0, "pillar1_context_score": 48.0},
        {"dnb": False, "contribution_score": 65.0, "raw_contribution": 0.8, "innings": 2, "entry_over": 8.0, "pillar1_context_score": 62.0},
    ]
    team_total_pos = 10.0

    agg = compute_season_aggregation(player_inns, team_total_positive_contribution=team_total_pos, matches_played=6)

    # Required fields from Section 19
    assert agg["matches_played"] == 6
    assert agg["batting_innings"] == 4
    assert agg["did_not_bat_matches"] == 2
    assert agg["average_contribution_score"] == 67.5  # Mean of [75, 85, 45, 65] - NO dilution by DNB!
    assert agg["total_contribution"] == 3.6
    assert agg["season_team_contribution_share"] == 38.0


# ----------------------------------------------------------------------
# 6. Section 21: Strict Leakage Audit & Outcome Invariance
# ----------------------------------------------------------------------
def test_leakage_audit_outcome_invariance():
    row_win = {
        "innings": 1, "entry_over": 10.0, "balls_remaining_entry": 60, "wickets_remaining_entry": 7,
        "team_rr_entry": 7.5, "actual_runs": 30.0, "balls_faced": 20, "actual_sr": 150.0,
        "boundary_percentage": 50.0, "run_deviation": 8.0, "sr_deviation": 20.0,
        "opportunity_usage": 0.33, "dismissal_status": "not out", "balls_remaining_exit": 40,
        "wickets_remaining_exit": 7, "wicket_resource_change": 0, "expected_final_change": 10.0,
        "window_team_rr": 9.0, "trajectory_deviation_change": 8.0, "overs_spent": 3.3,
        "won_match": True, "winning_margin": 45.0, "margin_type": "runs"
    }
    row_loss = row_win.copy()
    row_loss["won_match"] = False
    row_loss["winning_margin"] = 2.0
    row_loss["margin_type"] = "runs"

    res_win = compute_phase5b_contribution(row_win)
    res_loss = compute_phase5b_contribution(row_loss)

    assert res_win["pillar1_context_score"] == res_loss["pillar1_context_score"]
    assert res_win["pillar2_perf_score"] == res_loss["pillar2_perf_score"]
    assert res_win["pillar3_state_score"] == res_loss["pillar3_state_score"]
    assert res_win["pillar4_cf_score"] == res_loss["pillar4_cf_score"]
    assert res_win["contribution_score"] == res_loss["contribution_score"]


# ----------------------------------------------------------------------
# 7. Section 8: Pillar 1 Coefficients Sensitivity & Robustness
# ----------------------------------------------------------------------
def test_p1_coefficients_sensitivity():
    death_row = {
        "innings": 1, "entry_over": 19.1, "balls_remaining_entry": 5, "wickets_remaining_entry": 6,
        "team_rr_entry": 8.5, "actual_runs": 30, "balls_faced": 5, "actual_sr": 600.0,
        "boundary_percentage": 100.0, "run_deviation": 18.0, "sr_deviation": 420.0,
        "opportunity_usage": 1.0, "dismissal_status": "not out", "balls_remaining_exit": 0,
        "wickets_remaining_exit": 6, "wicket_resource_change": 0, "expected_final_change": 22.0,
        "window_team_rr": 36.0, "trajectory_deviation_change": 20.0, "overs_spent": 0.8
    }
    base_res = compute_phase5b_contribution(death_row)
    base_score = base_res["contribution_score"]

    # Vary death urgency weight from 0.9 (-25%) to 1.5 (+25%)
    p1_low = compute_pillar1_match_context(death_row, death_urgency_weight=0.9)
    z1_low = (p1_low - PHASE5B_EMPIRICAL_PARAMS["pillar1_mean"]) / PHASE5B_EMPIRICAL_PARAMS["pillar1_std"]
    c_low = 0.25 * z1_low + 0.25 * base_res["z_perf"] + 0.25 * base_res["z_state"] + 0.25 * base_res["z_cf"]
    score_low = 100.0 / (1.0 + np.exp(-1.4 * (c_low - PHASE5B_EMPIRICAL_PARAMS["composite_center"])))

    # Shift is small (<= 1.5 points on 100-point scale)
    assert abs(score_low - base_score) <= 1.5
