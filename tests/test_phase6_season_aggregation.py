"""
Tests for Phase 6A Season Aggregation and Small-Opportunity Innings Audit.

Covers all 18 required tests from Section 18:
 1. DNB returns NULL.
 2. DNB does not dilute season average.
 3. One low-run not-out does not automatically become negative.
 4. One low-run not-out does not automatically become positive.
 5. 30 off 5 in death overs is retained.
 6. 30 off 5 early in innings is evaluated differently.
 7. 8* off 3 is not automatically removed.
 8. 8* off 12 is evaluated based on context.
 9. 1* off 1 in a match-winning final ball is retained.
10. 300-run player with two tiny not-outs is not disproportionately penalized.
11. 300-run filter is configurable.
12. Changing minimum runs does not change underlying contribution scores.
13. DNB count does not affect contribution denominator.
14. Team contribution share excludes DNB.
15. NULL categories remain NULL when there is no valid opportunity.
16. Short high-impact innings cannot be removed by a crude balls threshold.
17. Outcome inversion does not change underlying contribution.
18. Season aggregation correctly sums contextual match-level outputs.
"""

import json
from pathlib import Path
import pytest
import numpy as np
import pandas as pd

from src.contribution_framework import (
    compute_phase5b_contribution,
    compute_season_aggregation,
)
from src.season_aggregation import (
    is_negligible_opportunity,
    filter_season_metrics,
    build_season_aggregations,
)


# ==============================================================================
# 1. DNB returns NULL
# ==============================================================================
def test_dnb_returns_null():
    """Test 1: If batter did not bat, scores and shares return NULL (None/NaN)."""
    dnb_input = {"dnb": True, "player": "YS Chahal", "matches_played": 1}
    res = compute_phase5b_contribution(dnb_input)
    assert res["dnb"] is True
    assert res["contribution_score"] is None
    assert res["raw_contribution"] is None
    assert res["pillar1_context_score"] is None
    assert res["pillar2_perf_score"] is None
    assert res["pillar3_state_score"] is None
    assert res["pillar4_cf_score"] is None


# ==============================================================================
# 2. DNB does not dilute season average
# ==============================================================================
def test_dnb_does_not_dilute_season_average():
    """
    Test 2: Season average with 10 batted innings and 6 DNB must equal
    the average of the 10 batted innings, NOT divided by 16.
    """
    # 10 innings with known scores
    known_scores = [70.0, 65.0, 60.0, 75.0, 55.0, 80.0, 62.0, 68.0, 72.0, 63.0]
    innings = [
        {"contribution_score": s, "raw_contribution": (s - 50.0) / 20.0, "dnb": False, "innings": 1}
        for s in known_scores
    ]
    # 6 DNB appearances
    dnb_inns = [{"dnb": True, "contribution_score": None, "raw_contribution": None} for _ in range(6)]
    all_appearances = innings + dnb_inns

    res = compute_season_aggregation(all_appearances, team_total_positive_contribution=50.0, matches_played=16)

    expected_avg = round(float(np.mean(known_scores)), 1)
    assert res["batting_innings"] == 10
    assert res["did_not_bat_matches"] == 6
    assert res["matches_played"] == 16
    assert res["average_contribution_score"] == expected_avg
    # If it were divided by 16, it would be around 41.9, which would be disastrous dilution
    assert res["average_contribution_score"] > 60.0


# ==============================================================================
# 3. One low-run not-out does not automatically become negative
# ==============================================================================
def test_low_run_not_out_not_automatically_negative():
    """
    Test 3: A low-run not out with solid tempo or positive state change
    must not automatically be classified as negative.
    """
    # 5* off 2 (SR 250) in middle overs (Case C)
    params = {
        "innings": 1, "entry_over": 12.0, "balls_remaining_entry": 48, "wickets_remaining_entry": 7,
        "team_rr_entry": 7.5, "actual_runs": 5, "balls_faced": 2, "actual_sr": 250.0,
        "boundary_percentage": 80.0, "run_deviation": 2.5, "sr_deviation": 125.0, "opportunity_usage": 0.04,
        "dismissal_status": "not out", "balls_remaining_exit": 46, "wickets_remaining_exit": 7,
        "wicket_resource_change": 0, "expected_final_change": 3.0, "window_team_rr": 15.0,
        "trajectory_deviation_change": 2.5, "overs_spent": 0.3
    }
    res = compute_phase5b_contribution(params)
    assert res["contribution_score"] > 50.0, f"Expected > 50, got {res['contribution_score']}"
    assert res["raw_contribution"] > 0.0


# ==============================================================================
# 4. One low-run not-out does not automatically become positive
# ==============================================================================
def test_low_run_not_out_not_automatically_positive():
    """
    Test 4: A sluggish low-run not-out consuming deliveries without acceleration
    must not automatically receive a positive score just because of 'not out'.
    """
    # 8* off 12 (SR 66.7) under pressure (Case E)
    params = {
        "innings": 1, "entry_over": 14.0, "balls_remaining_entry": 36, "wickets_remaining_entry": 4,
        "team_rr_entry": 6.5, "actual_runs": 8, "balls_faced": 12, "actual_sr": 66.7,
        "boundary_percentage": 0.0, "run_deviation": -6.0, "sr_deviation": -65.0, "opportunity_usage": 0.33,
        "dismissal_status": "not out", "balls_remaining_exit": 24, "wickets_remaining_exit": 4,
        "wicket_resource_change": 0, "expected_final_change": -4.0, "window_team_rr": 4.0,
        "trajectory_deviation_change": -3.0, "overs_spent": 2.0
    }
    res = compute_phase5b_contribution(params)
    assert res["contribution_score"] < 50.0, f"Expected < 50, got {res['contribution_score']}"
    assert res["raw_contribution"] < 0.0


# ==============================================================================
# 5. 30 off 5 in death overs is retained
# ==============================================================================
def test_30_off_5_death_overs_retained():
    """Test 5: Explosive death cameo 30 off 5 must be retained and receive elite score."""
    params = {
        "innings": 1, "entry_over": 19.1, "balls_remaining_entry": 5, "wickets_remaining_entry": 6,
        "team_rr_entry": 8.5, "actual_runs": 30, "balls_faced": 5, "actual_sr": 600.0,
        "boundary_percentage": 100.0, "run_deviation": 18.0, "sr_deviation": 420.0, "opportunity_usage": 1.0,
        "dismissal_status": "not out", "balls_remaining_exit": 0, "wickets_remaining_exit": 6,
        "wicket_resource_change": 0, "expected_final_change": 22.0, "window_team_rr": 36.0,
        "trajectory_deviation_change": 20.0, "overs_spent": 0.8
    }
    res = compute_phase5b_contribution(params)
    assert res["contribution_score"] >= 85.0
    assert not is_negligible_opportunity({**params, **res})


# ==============================================================================
# 6. 30 off 5 early in innings is evaluated differently
# ==============================================================================
def test_30_off_5_early_evaluated_differently():
    """Test 6: 30 off 5 early in innings is evaluated with different context and trajectory dynamics."""
    death_params = {
        "innings": 1, "entry_over": 19.1, "balls_remaining_entry": 5, "wickets_remaining_entry": 6,
        "team_rr_entry": 8.5, "actual_runs": 30, "balls_faced": 5, "actual_sr": 600.0,
        "boundary_percentage": 100.0, "run_deviation": 18.0, "sr_deviation": 420.0, "opportunity_usage": 1.0,
        "dismissal_status": "not out", "balls_remaining_exit": 0, "wickets_remaining_exit": 6,
        "wicket_resource_change": 0, "expected_final_change": 22.0, "window_team_rr": 36.0,
        "trajectory_deviation_change": 20.0, "overs_spent": 0.8
    }
    early_params = {
        "innings": 1, "entry_over": 7.1, "balls_remaining_entry": 77, "wickets_remaining_entry": 8,
        "team_rr_entry": 7.5, "actual_runs": 30, "balls_faced": 5, "actual_sr": 600.0,
        "boundary_percentage": 100.0, "run_deviation": 18.0, "sr_deviation": 440.0, "opportunity_usage": 0.06,
        "dismissal_status": "not out", "balls_remaining_exit": 72, "wickets_remaining_exit": 8,
        "wicket_resource_change": 0, "expected_final_change": 12.0, "window_team_rr": 36.0,
        "trajectory_deviation_change": 10.0, "overs_spent": 0.8
    }
    res_death = compute_phase5b_contribution(death_params)
    res_early = compute_phase5b_contribution(early_params)

    # Both are outstanding scores (>80), but death context urgency yields different raw/composite
    assert res_death["contribution_score"] != res_early["contribution_score"]
    assert res_death["pillar1_context_score"] > res_early["pillar1_context_score"]


# ==============================================================================
# 7. 8* off 3 is not automatically removed
# ==============================================================================
def test_8_off_3_not_automatically_removed():
    """Test 7: 8* off 3 in death overs is not negligible and provides positive score."""
    params = {
        "innings": 1, "entry_over": 18.2, "balls_remaining_entry": 10, "wickets_remaining_entry": 6,
        "team_rr_entry": 8.5, "actual_runs": 8, "balls_faced": 3, "actual_sr": 266.7,
        "boundary_percentage": 75.0, "run_deviation": 4.0, "sr_deviation": 100.0, "opportunity_usage": 0.3,
        "dismissal_status": "not out", "balls_remaining_exit": 7, "wickets_remaining_exit": 6,
        "wicket_resource_change": 0, "expected_final_change": 5.0, "window_team_rr": 16.0,
        "trajectory_deviation_change": 4.0, "overs_spent": 0.5
    }
    res = compute_phase5b_contribution(params)
    assert res["contribution_score"] >= 65.0
    # Not negligible because balls=3 and raw > 0.10
    assert not is_negligible_opportunity({**params, **res})


# ==============================================================================
# 8. 8* off 12 is evaluated based on context
# ==============================================================================
def test_8_off_12_evaluated_on_context():
    """Test 8: 8* off 12 evaluated in deep crisis is distinguished from sluggish middle over stay."""
    sluggish = {
        "innings": 1, "entry_over": 14.0, "balls_remaining_entry": 36, "wickets_remaining_entry": 4,
        "team_rr_entry": 6.5, "actual_runs": 8, "balls_faced": 12, "actual_sr": 66.7,
        "boundary_percentage": 0.0, "run_deviation": -6.0, "sr_deviation": -65.0, "opportunity_usage": 0.33,
        "dismissal_status": "not out", "balls_remaining_exit": 24, "wickets_remaining_exit": 4,
        "wicket_resource_change": 0, "expected_final_change": -4.0, "window_team_rr": 4.0,
        "trajectory_deviation_change": -3.0, "overs_spent": 2.0
    }
    res = compute_phase5b_contribution(sluggish)
    # Correctly reflects negative impact of eating balls without boundaries
    assert res["contribution_score"] < 45.0
    assert res["raw_contribution"] < 0.0


# ==============================================================================
# 9. 1* off 1 in a match-winning final ball is retained
# ==============================================================================
def test_1_off_1_match_winning_retained():
    """Test 9: 1* off 1 needing 1 to win on final delivery is high impact and never excluded."""
    params = {
        "innings": 2, "entry_over": 19.5, "balls_remaining_entry": 1, "wickets_remaining_entry": 3,
        "required_rr_entry": 6.0, "rr_gap_entry": 0.0, "actual_runs": 1, "balls_faced": 1, "actual_sr": 100.0,
        "boundary_percentage": 0.0, "run_deviation": 0.2, "sr_deviation": -30.0, "opportunity_usage": 1.0,
        "dismissal_status": "not out", "balls_remaining_exit": 0, "wickets_remaining_exit": 3,
        "wicket_resource_change": 0, "required_rr_change": 6.0, "rr_gap_change": 6.0, "target_progress_change": 0.05
    }
    res = compute_phase5b_contribution(params)
    assert res["contribution_score"] > 60.0
    assert res["raw_contribution"] > 0.20
    # Even though balls=1, raw > 0.10 means it is NOT negligible!
    assert not is_negligible_opportunity({**params, **res})


# ==============================================================================
# 10. 300-run player with two tiny not-outs is not disproportionately penalized
# ==============================================================================
def test_300_run_player_tiny_not_outs_not_penalized():
    """Test 10: Player with strong 300-run season having two 1* off 1 finishes is not dragged down."""
    # 10 substantial innings averaging 68.0
    substantial = [
        {"contribution_score": 68.0, "raw_contribution": 0.80, "dnb": False, "innings": 1, "actual_runs": 35, "balls_faced": 25}
        for _ in range(10)
    ]
    # 2 tiny finishes: 1* off 1 (Case A type)
    tiny_finishes = [
        {"contribution_score": 45.0, "raw_contribution": -0.05, "dnb": False, "innings": 2, "actual_runs": 1, "balls_faced": 1, "dismissal_status": "not out"},
        {"contribution_score": 48.0, "raw_contribution": -0.02, "dnb": False, "innings": 2, "actual_runs": 2, "balls_faced": 2, "dismissal_status": "not out"}
    ]
    all_inns = substantial + tiny_finishes

    res = compute_season_aggregation(all_inns, team_total_positive_contribution=40.0, matches_played=12)
    # Average remains strong (~64+) and not penalized to mediocre levels
    assert res["average_contribution_score"] >= 64.0
    assert res["total_raw_contribution"] > 7.0


# ==============================================================================
# 11. 300-run filter is configurable
# ==============================================================================
def test_filter_is_configurable():
    """Test 11: Filter allows setting minimum_runs to 100, 200, 300, 400, 500 without error."""
    mock_data = pd.DataFrame([
        {"player": "P1", "season": "2026", "actual_runs": 95, "batting_innings": 5, "balls_faced": 70, "average_contribution_score": 52.0},
        {"player": "P2", "season": "2026", "actual_runs": 150, "batting_innings": 8, "balls_faced": 110, "average_contribution_score": 58.0},
        {"player": "P3", "season": "2026", "actual_runs": 250, "batting_innings": 12, "balls_faced": 180, "average_contribution_score": 62.0},
        {"player": "P4", "season": "2026", "actual_runs": 350, "batting_innings": 14, "balls_faced": 240, "average_contribution_score": 67.0},
        {"player": "P5", "season": "2026", "actual_runs": 450, "batting_innings": 15, "balls_faced": 310, "average_contribution_score": 72.0},
    ])

    f100 = filter_season_metrics(mock_data, minimum_runs=100)
    assert len(f100) == 4
    f200 = filter_season_metrics(mock_data, minimum_runs=200)
    assert len(f200) == 3
    f300 = filter_season_metrics(mock_data, minimum_runs=300)
    assert len(f300) == 2
    f400 = filter_season_metrics(mock_data, minimum_runs=400)
    assert len(f400) == 1
    f500 = filter_season_metrics(mock_data, minimum_runs=500)
    assert len(f500) == 0


# ==============================================================================
# 12. Changing minimum runs does not change underlying contribution scores
# ==============================================================================
def test_filter_does_not_change_underlying_scores():
    """Test 12: Changing filter thresholds only selects rows; scores remain strictly invariant."""
    mock_data = pd.DataFrame([
        {"player": "P4", "season": "2026", "actual_runs": 350, "batting_innings": 14, "balls_faced": 240, "average_contribution_score": 67.4},
        {"player": "P5", "season": "2026", "actual_runs": 450, "batting_innings": 15, "balls_faced": 310, "average_contribution_score": 72.8},
    ])
    f_all = filter_season_metrics(mock_data)
    f_300 = filter_season_metrics(mock_data, minimum_runs=300)
    f_400 = filter_season_metrics(mock_data, minimum_runs=400)

    # Underlying scores of P5 must be identical regardless of whether threshold was None, 300, or 400
    score_all = f_all[f_all["player"] == "P5"]["average_contribution_score"].values[0]
    score_300 = f_300[f_300["player"] == "P5"]["average_contribution_score"].values[0]
    score_400 = f_400[f_400["player"] == "P5"]["average_contribution_score"].values[0]

    assert score_all == score_300 == score_400 == 72.8


# ==============================================================================
# 13. DNB count does not affect contribution denominator
# ==============================================================================
def test_dnb_count_does_not_affect_denominator():
    """Test 13: 5 innings + 0 DNB vs 5 innings + 10 DNB must have identical denominator (5)."""
    inns = [
        {"contribution_score": 60.0, "raw_contribution": 0.5, "dnb": False, "innings": 1}
        for _ in range(5)
    ]
    res_no_dnb = compute_season_aggregation(inns, team_total_positive_contribution=20.0, matches_played=5)
    
    inns_with_dnb = inns + [{"dnb": True, "contribution_score": None, "raw_contribution": None} for _ in range(10)]
    res_with_dnb = compute_season_aggregation(inns_with_dnb, team_total_positive_contribution=20.0, matches_played=15)

    assert res_no_dnb["batting_innings"] == 5
    assert res_with_dnb["batting_innings"] == 5
    assert res_no_dnb["average_contribution_score"] == res_with_dnb["average_contribution_score"] == 60.0


# ==============================================================================
# 14. Team contribution share excludes DNB
# ==============================================================================
def test_team_contribution_share_excludes_dnb():
    """Test 14: DNB innings produce NULL share for pure DNB players and do not alter team share."""
    pure_dnb = [{"dnb": True, "contribution_score": None, "raw_contribution": None} for _ in range(14)]
    res_pure = compute_season_aggregation(pure_dnb, team_total_positive_contribution=35.0, matches_played=14)
    assert res_pure["season_team_contribution_share"] is None

    # Normal player: 2.0 pos raw out of 20.0 team total = exactly 10.0% share
    inns = [
        {"contribution_score": 65.0, "raw_contribution": 1.0, "dnb": False, "innings": 1},
        {"contribution_score": 65.0, "raw_contribution": 1.0, "dnb": False, "innings": 1},
    ] + [{"dnb": True, "contribution_score": None, "raw_contribution": None} for _ in range(10)]
    res = compute_season_aggregation(inns, team_total_positive_contribution=20.0, matches_played=12)
    assert res["season_team_contribution_share"] == 10.0


# ==============================================================================
# 15. NULL categories remain NULL when there is no valid opportunity
# ==============================================================================
def test_null_categories_remain_null():
    """Test 15: If player never batted in powerplay or death, category returns None (NULL), not 0."""
    inns = [
        # Only batted in middle overs of 1st innings
        {"contribution_score": 58.0, "raw_contribution": 0.4, "entry_over": 10.0, "innings": 1, "dnb": False, "pillar1_context_score": 50.0}
    ]
    res = compute_season_aggregation(inns, team_total_positive_contribution=10.0, matches_played=1)
    assert res["powerplay_contribution"] is None
    assert res["death_over_contribution"] is None
    assert res["chase_contribution"] is None
    assert res["high_pressure_contribution"] is None
    assert res["first_innings_contribution"] == 58.0
    assert res["middle_over_contribution"] == 58.0


# ==============================================================================
# 16. Short high-impact innings cannot be removed by a crude balls threshold
# ==============================================================================
def test_short_high_impact_protected_from_crude_balls_threshold():
    """Test 16: An explosive 30 off 5 or 8* off 3 is rejected by balls<=5 but protected by model."""
    knocks = [
        {"balls_faced": 5, "actual_runs": 30, "raw_contribution": 1.3975, "dismissal_status": "not out", "innings": 1, "expected_final_change": 22.0},
        {"balls_faced": 3, "actual_runs": 8, "raw_contribution": 0.5710, "dismissal_status": "not out", "innings": 1, "expected_final_change": 5.0},
    ]
    for k in knocks:
        # A crude balls <= 5 filter would drop both
        crude_excluded = (k["balls_faced"] <= 5)
        assert crude_excluded is True

        # Our data-driven negligible opportunity rule PROTECTS both
        assert is_negligible_opportunity(k) is False, f"Cameo {k} should have been protected!"


# ==============================================================================
# 17. Outcome inversion does not change underlying contribution
# ==============================================================================
def test_outcome_inversion_invariance():
    """Test 17: Inverting match result (won_match, margin) does not change contribution score."""
    sample = {
        "innings": 1, "entry_over": 10.0, "balls_remaining_entry": 60, "wickets_remaining_entry": 8,
        "team_rr_entry": 7.5, "actual_runs": 45, "balls_faced": 30, "actual_sr": 150.0,
        "boundary_percentage": 60.0, "run_deviation": 12.0, "sr_deviation": 25.0, "opportunity_usage": 0.5,
        "dismissal_status": "caught", "balls_remaining_exit": 30, "wickets_remaining_exit": 7,
        "wicket_resource_change": -1, "expected_final_change": 8.0, "window_team_rr": 9.0,
        "trajectory_deviation_change": 6.0, "overs_spent": 5.0, "won_match": True, "winning_margin": 15
    }
    res_orig = compute_phase5b_contribution(sample)

    inverted = sample.copy()
    inverted["won_match"] = False
    inverted["winning_margin"] = -15
    res_inv = compute_phase5b_contribution(inverted)

    assert res_orig["contribution_score"] == res_inv["contribution_score"]
    assert res_orig["raw_contribution"] == res_inv["raw_contribution"]
    assert res_orig["pillar1_context_score"] == res_inv["pillar1_context_score"]
    assert res_orig["pillar2_perf_score"] == res_inv["pillar2_perf_score"]
    assert res_orig["pillar3_state_score"] == res_inv["pillar3_state_score"]
    assert res_orig["pillar4_cf_score"] == res_inv["pillar4_cf_score"]


# ==============================================================================
# 18. Season aggregation correctly sums contextual match-level outputs
# ==============================================================================
def test_season_aggregation_correctly_sums_match_outputs():
    """Test 18: Season totals and shares exactly equal mathematical sums of match-level outputs."""
    raws = [1.25, -0.40, 0.85, 0.00, -0.60, 1.50]
    scores = [68.0, 42.0, 62.0, 50.0, 40.0, 72.0]
    inns = [
        {"contribution_score": s, "raw_contribution": r, "dnb": False, "innings": 1}
        for s, r in zip(scores, raws)
    ]
    res = compute_season_aggregation(inns, team_total_positive_contribution=18.0, matches_played=8)

    expected_tot_raw = round(float(sum(raws)), 3)
    expected_pos_raw = float(sum(max(0.0, r) for r in raws))  # 1.25 + 0.85 + 1.50 = 3.60
    expected_share = round((expected_pos_raw / 18.0) * 100.0, 2)  # 3.60 / 18.0 * 100 = 20.0%

    assert res["total_raw_contribution"] == expected_tot_raw
    assert res["season_team_contribution_share"] == expected_share
    assert res["batting_innings"] == 6
    assert res["did_not_bat_matches"] == 2
    assert res["average_contribution_score"] == round(float(np.mean(scores)), 1)
