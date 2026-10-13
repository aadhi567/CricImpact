"""
Unit and Integration Tests for Phase 5A: Final Batter Contribution Framework.

Tests cover:
1. Contribution Score scale properties (0 to 100, par ~ 50.0).
2. Team Contribution Share attribution methods (sum to 100%, non-negative rectified).
3. Monotonicity and sensitivity properties (runs, SR, expected runs, wicket loss, chase RRR).
4. Outcome linkage behavior (losing-team hero, winning-team passenger).
5. Counterfactual separation and outcome leakage audit.
6. Edge case handling (5-ball cameo, death-overs, late entry, zero-ball innings).
"""

import pytest
import numpy as np
import pandas as pd

from src.contribution_framework import (
    compute_individual_performance_score,
    compute_state_impact_score,
    compute_resource_tradeoff_score,
    calculate_outcome_leverage,
    compute_raw_contribution,
    normalize_contribution_score,
    compute_team_contribution_shares,
)
from src.counterfactual_engine import CounterfactualEngine


# ----------------------------------------------------------------------
# 1. Output A: Contribution Score Scale Properties (0 to 100)
# ----------------------------------------------------------------------
def test_contribution_score_bounds_and_par():
    ref_params = {"center": 0.0, "scale": 0.85, "min_val": -3.5, "max_val": 8.0}
    
    # Par performance (C_raw = 0.0) should map exactly to 50.0
    par_score = normalize_contribution_score(0.0, method="logistic", reference_params=ref_params)
    assert 49.5 <= par_score <= 50.5
    
    # Extreme negative performance should stay bounded in (0, 100)
    neg_score = normalize_contribution_score(-5.0, method="logistic", reference_params=ref_params)
    assert 0.0 < neg_score < 10.0
    
    # Extreme positive performance should stay bounded in (0, 100)
    pos_score = normalize_contribution_score(10.0, method="logistic", reference_params=ref_params)
    assert 95.0 < pos_score < 100.0


# ----------------------------------------------------------------------
# 2. Output B: Team Contribution Share Properties
# ----------------------------------------------------------------------
def test_team_contribution_share_sum_and_rectification():
    # Innings with positive and negative contributors
    raw_scores = [2.5, 1.2, -0.8, -1.5, 0.5]
    shares = compute_team_contribution_shares(raw_scores, method="rectified_positive")
    
    # Sum should equal 100% (within rounding)
    assert abs(sum(shares) - 100.0) < 0.2
    
    # Negative contributors should receive 0.0% share
    assert shares[2] == 0.0
    assert shares[3] == 0.0
    
    # Highest contributor should have the highest share
    assert shares[0] > shares[1] > shares[4]


def test_team_contribution_share_collapse_handling():
    # Innings where all batters had non-positive impact (team collapsed for 49)
    raw_scores = [-1.2, -0.8, -2.1, -0.5, -1.0]
    shares = compute_team_contribution_shares(raw_scores, method="rectified_positive")
    
    # Should fall back gracefully to equal division (100 / N)
    assert len(shares) == 5
    assert abs(sum(shares) - 100.0) < 0.2
    assert shares[0] == 20.0


def test_team_contribution_share_single_batter():
    # Single batter in chase or lone scorer
    shares = compute_team_contribution_shares([3.5], method="rectified_positive")
    assert shares == [100.0]


# ----------------------------------------------------------------------
# 3. Monotonicity & Sensitivity Tests
# ----------------------------------------------------------------------
def test_monotonicity_actual_runs():
    base_row = {
        "actual_runs": 25.0,
        "expected_runs": 20.0,
        "run_deviation": 5.0,
        "actual_sr": 130.0,
        "expected_sr": 130.0,
        "sr_deviation": 0.0,
        "opportunity_usage": 0.5,
        "innings": 1,
        "expected_final_change": 5.0,
        "wicket_resource_change": 0,
        "balls_remaining_exit": 40,
        "wickets_remaining_exit": 7,
        "won_match": True,
        "winning_margin": 10.0,
        "margin_type": "runs"
    }
    
    base_c = compute_raw_contribution(base_row)
    
    # Batter scores 15 more runs with everything else constant
    better_row = base_row.copy()
    better_row["actual_runs"] += 15.0
    better_row["run_deviation"] += 15.0
    better_row["expected_final_change"] += 15.0
    better_c = compute_raw_contribution(better_row)
    
    assert better_c > base_c


def test_monotonicity_expected_runs():
    base_row = {
        "actual_runs": 30.0,
        "expected_runs": 20.0,
        "run_deviation": 10.0,
        "actual_sr": 140.0,
        "expected_sr": 130.0,
        "sr_deviation": 10.0,
        "opportunity_usage": 0.5,
        "innings": 1,
        "expected_final_change": 10.0,
        "wicket_resource_change": 0,
        "balls_remaining_exit": 30,
        "wickets_remaining_exit": 6,
        "won_match": True,
        "winning_margin": 15.0,
        "margin_type": "runs"
    }
    
    base_c = compute_raw_contribution(base_row)
    
    # If situation was much easier (expected runs higher), deviation is lower
    easier_row = base_row.copy()
    easier_row["expected_runs"] += 15.0
    easier_row["run_deviation"] -= 15.0
    easier_c = compute_raw_contribution(easier_row)
    
    assert easier_c < base_c


def test_resource_tradeoff_wicket_penalty():
    # Batter A: 20 off 6, not dismissed (70/4 -> 90/4)
    # Batter B: 20 off 6, dismissed (70/4 -> 90/5)
    row_a = {
        "actual_runs": 20.0,
        "expected_runs": 10.0,
        "run_deviation": 10.0,
        "actual_sr": 333.3,
        "expected_sr": 140.0,
        "sr_deviation": 193.3,
        "opportunity_usage": 0.2,
        "innings": 1,
        "expected_final_change": 15.0,
        "wicket_resource_change": 0,
        "balls_remaining_exit": 50,
        "wickets_remaining_exit": 6,
        "won_match": True,
        "winning_margin": 20.0,
        "margin_type": "runs"
    }
    
    row_b = row_a.copy()
    row_b["wicket_resource_change"] = -1
    row_b["wickets_remaining_exit"] = 5
    
    score_a = compute_raw_contribution(row_a)
    score_b = compute_raw_contribution(row_b)
    
    # Batter A preserved wicket resource; Batter B consumed a wicket
    assert score_a > score_b


def test_chase_required_rr_reduction():
    chase_row_base = {
        "actual_runs": 35.0,
        "expected_runs": 25.0,
        "run_deviation": 10.0,
        "actual_sr": 150.0,
        "expected_sr": 135.0,
        "sr_deviation": 15.0,
        "opportunity_usage": 0.4,
        "innings": 2,
        "required_rr_change": 0.0,  # Par RRR
        "runs_required_reduction": 35.0,
        "target_progress_change": 0.20,
        "wicket_resource_change": 0,
        "balls_remaining_exit": 40,
        "wickets_remaining_exit": 7,
        "won_match": True,
        "winning_margin": 4.0,
        "margin_type": "wickets"
    }
    
    chase_row_pressure_relief = chase_row_base.copy()
    chase_row_pressure_relief["required_rr_change"] = 3.5  # Substantial pressure relief
    
    c_base = compute_raw_contribution(chase_row_base)
    c_relief = compute_raw_contribution(chase_row_pressure_relief)
    
    assert c_relief > c_base


# ----------------------------------------------------------------------
# 4. Outcome Linkage Behavior
# ----------------------------------------------------------------------
def test_losing_team_hero_remains_high():
    # Heroic 75 off 42 in a match the team lost by 2 runs
    hero_row = {
        "actual_runs": 75.0,
        "expected_runs": 26.0,
        "run_deviation": 49.0,
        "actual_sr": 178.6,
        "expected_sr": 130.0,
        "sr_deviation": 48.6,
        "opportunity_usage": 0.5,
        "innings": 2,
        "required_rr_change": 2.8,
        "runs_required_reduction": 75.0,
        "target_progress_change": 0.45,
        "wicket_resource_change": -1,
        "balls_remaining_exit": 1,
        "wickets_remaining_exit": 2,
        "won_match": False,
        "winning_margin": 2.0,  # Narrow loss
        "margin_type": "runs"
    }
    
    raw_c = compute_raw_contribution(hero_row, outcome_method="margin_sensitive")
    norm_score = normalize_contribution_score(raw_c, method="logistic")
    
    # Despite losing, score must be comfortably above 75 (elite territory)
    assert norm_score >= 75.0


def test_winning_team_passenger_remains_moderate():
    # 8 off 12 balls in a comfortable 50-run win
    passenger_row = {
        "actual_runs": 8.0,
        "expected_runs": 18.0,
        "run_deviation": -10.0,
        "actual_sr": 66.7,
        "expected_sr": 130.0,
        "sr_deviation": -63.3,
        "opportunity_usage": 0.3,
        "innings": 1,
        "expected_final_change": -8.0,
        "wicket_resource_change": -1,
        "balls_remaining_exit": 40,
        "wickets_remaining_exit": 6,
        "won_match": True,
        "winning_margin": 50.0,  # Blowout win
        "margin_type": "runs"
    }
    
    raw_c = compute_raw_contribution(passenger_row, outcome_method="margin_sensitive")
    norm_score = normalize_contribution_score(raw_c, method="logistic")
    
    # Must NOT receive high contribution merely because team won
    assert norm_score <= 45.0


# ----------------------------------------------------------------------
# 5. Counterfactual Invariance & Leakage Prevention
# ----------------------------------------------------------------------
def test_counterfactual_outcome_invariance():
    cf_engine = CounterfactualEngine()
    
    batter_row = pd.Series({
        "player": "Test Batter",
        "match_id": 999999,
        "innings": 1,
        "entry_ball": 1,
        "entry_over": 0.0,
        "wickets_remaining_entry": 10,
        "team_score_entry": 0,
        "balls_remaining_entry": 120,
        "team_rr_entry": 0.0,
        "actual_runs": 45,
        "balls_faced": 30,
        "expected_runs": 30.0,
        "expected_sr": 130.0,
        "expected_final_entry": 160.0,
        "expected_final_exit": 175.0,
        "expected_final_change": 15.0,
        "wicket_resource_change": -1,
        "overs_remaining_entry": 20.0,
        "target": None,
        "required_rr_entry": None,
        # Retrospective outcome fields
        "won_match": True,
        "winning_margin": 10.0,
        "final_team_score": 180,
        "post_exit_runs": 60,
    })
    
    cf_orig = cf_engine.evaluate_batter_counterfactuals(batter_row)
    
    # Tamper with retrospective outcome data
    altered_row = batter_row.copy()
    altered_row["won_match"] = False
    altered_row["winning_margin"] = 100.0
    altered_row["final_team_score"] = 90
    altered_row["post_exit_runs"] = 5
    
    cf_alt = cf_engine.evaluate_batter_counterfactuals(altered_row)
    
    # Counterfactual projections MUST be identical
    assert cf_orig["scenarios"]["CF_Par"] == cf_alt["scenarios"]["CF_Par"]
    assert cf_orig["scenarios"]["CF_Accelerated"] == cf_alt["scenarios"]["CF_Accelerated"]
    assert cf_orig["scenarios"]["CF_Wicket_Preserved"] == cf_alt["scenarios"]["CF_Wicket_Preserved"]


# ----------------------------------------------------------------------
# 6. Edge Cases Coverage
# ----------------------------------------------------------------------
def test_five_ball_cameo_evaluation():
    # 5 balls, 30 runs in death overs (over 19.1)
    cameo_row = {
        "actual_runs": 30.0,
        "expected_runs": 9.0,
        "run_deviation": 21.0,
        "actual_sr": 600.0,
        "expected_sr": 180.0,
        "sr_deviation": 420.0,
        "opportunity_usage": 0.1,
        "innings": 1,
        "expected_final_change": 21.0,
        "wicket_resource_change": 0,
        "balls_remaining_exit": 1,
        "wickets_remaining_exit": 5,
        "won_match": True,
        "winning_margin": 12.0,
        "margin_type": "runs"
    }
    
    raw_c = compute_raw_contribution(cameo_row)
    norm_score = normalize_contribution_score(raw_c, method="logistic")
    
    # Must receive high recognition (> 75) without artificial sample-size penalty
    assert norm_score >= 75.0


def test_zero_ball_innings():
    # Run out at non-striker's end or 0 balls faced
    zero_ball_row = {
        "actual_runs": 0.0,
        "expected_runs": 0.0,
        "run_deviation": 0.0,
        "actual_sr": 0.0,
        "expected_sr": 120.0,
        "sr_deviation": -120.0,
        "opportunity_usage": 0.0,
        "innings": 1,
        "expected_final_change": 0.0,
        "wicket_resource_change": -1,
        "balls_remaining_exit": 10,
        "wickets_remaining_exit": 4,
        "won_match": True,
        "winning_margin": 5.0,
        "margin_type": "runs"
    }
    
    raw_c = compute_raw_contribution(zero_ball_row)
    norm_score = normalize_contribution_score(raw_c, method="logistic")
    
    # Below par (< 50) due to lost wicket with zero runs added
    assert norm_score < 50.0
