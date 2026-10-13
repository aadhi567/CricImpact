"""
Unit and Regression Tests for Phase 7C: Core Contribution Model Rebalancing (25/35/40).

Tests:
1. 25/35/40 Weighting Formulation (P1: 25%, P2: 35%, P3: 40%).
2. P4 Exclusion from main Contribution Score (0% weight).
3. P3 Team-State Impact signals (macro trajectory, RRR relief, collapse recovery, resource equity).
4. Partnership and Non-Striker calculations (partner runs, partner balls, partner SR, carrying share).
5. Strict Outcome Invariance (zero leakage of match result into contribution scores).
6. Strict DNB and NULL preservation.
7. Validation across all 20 required Phase 7C edge cases.
8. Compatibility with Phase 6A season aggregation and Team Contribution Share attribution.
"""

import pytest
import numpy as np
import pandas as pd

from src.phase7c_rebalance import (
    compute_phase7c_p3,
    compute_phase7c_contribution,
    compute_phase7c_p4_diagnostic,
    evaluate_phase7c_edge_cases,
    evaluate_phase7c_leakage,
    PHASE7C_WEIGHTS,
)
from src.partnership_context import (
    extract_all_partnerships_from_deliveries,
    build_partnerships_lookup,
    compute_batter_partnership_profile,
)
from src.contribution_framework import compute_season_aggregation


# ==============================================================================
# 1. 25/35/40 WEIGHTING FORMULATION & P4 EXCLUSION
# ==============================================================================
def test_phase7c_weighting_and_p4_exclusion():
    """Verify Model A uses 25% P1, 35% P2, 40% P3, with P4 excluded from the main score."""
    row = {
        "innings": 1,
        "actual_runs": 45,
        "balls_faced": 30,
        "actual_sr": 150.0,
        "entry_over": 8.0,
        "expected_final_change": 15.0,
        "trajectory_deviation_change": 8.0,
        "window_team_rr": 8.8,
        "team_rr_entry": 7.2,
        "partnership_runs": 65,
        "batter_partnership_share": 45.0 / 65.0,
        "partner_runs": 20,
        "balls_remaining_entry": 72,
        "balls_remaining_exit": 30,
        "wickets_remaining_entry": 8,
        "wickets_remaining_exit": 7,
        "expected_runs": 25.0,
        "expected_sr": 125.0,
    }

    res = compute_phase7c_contribution(row)

    # Weights verification
    w = res["weights"]
    assert w["pillar1_match_context"] == "25%"
    assert w["pillar2_batter_performance"] == "35%"
    assert w["pillar3_team_state_impact"] == "40%"
    assert w["pillar4_counterfactual"] == "Diagnostic only"

    # Score calculation verification: 0.25 * P1 + 0.35 * P2 + 0.40 * P3
    p1 = res["pillar1_context_score"]
    p2 = res["pillar2_perf_score"]
    p3 = res["pillar3_state_score"]
    expected_score = round(0.25 * p1 + 0.35 * p2 + 0.40 * p3, 1)
    assert res["contribution_score"] == expected_score

    # P4 diagnostic layer presence and score independence
    p4_diag = res["pillar4_diagnostic"]
    assert p4_diag is not None
    assert p4_diag["pillar_id"] == "P4"
    assert "strategic_recommendation" in p4_diag
    assert "possible_improvement_area" in p4_diag

    # P4 independence test: arbitrarily modifying expected runs or counterfactuals changes 0.0 of main score
    row_alt_cf = row.copy()
    row_alt_cf["expected_runs"] = 45.0  # radically alter counterfactual expectation
    row_alt_cf["expected_sr"] = 180.0
    res_alt = compute_phase7c_contribution(row_alt_cf)
    assert res_alt["contribution_score"] == res["contribution_score"]
    assert res_alt["raw_contribution"] == res["raw_contribution"]


# ==============================================================================
# 2. P3 TEAM-STATE SIGNALS (TRAJECTORY, COLLAPSE, RESOURCE)
# ==============================================================================
def test_phase7c_p3_team_state_signals():
    """Verify P3 evaluates macro trajectory, pressure liquidation, and collapse recovery."""
    # Case A: 20/4 -> 90/5 (Rescue & Stabilization)
    collapse_rescue = {
        "innings": 1,
        "actual_runs": 45,
        "balls_faced": 35,
        "actual_sr": 128.6,
        "expected_final_change": 26.0,
        "trajectory_deviation_change": 18.0,
        "window_team_rr": 7.8,
        "team_rr_entry": 5.4,
        "partnership_runs": 75,
        "batter_partnership_share": 45.0 / 75.0,
        "partner_runs": 30,
        "balls_remaining_entry": 98,
        "balls_remaining_exit": 35,
        "wickets_remaining_entry": 6,
        "wickets_remaining_exit": 5,
        "wickets_lost_during_stay": 1,
    }
    p3_rescue = compute_phase7c_p3(collapse_rescue)
    assert p3_rescue > 0.80, "Collapse rescue must generate substantial positive P3 team-state impact"

    # Case B: 120/1 -> 150/6 (Innings Stalled & Tail Exposed)
    collapse_worsened = {
        "innings": 1,
        "actual_runs": 15,
        "balls_faced": 18,
        "actual_sr": 83.3,
        "expected_final_change": -22.0,
        "trajectory_deviation_change": -18.0,
        "window_team_rr": 6.0,
        "team_rr_entry": 9.5,
        "partnership_runs": 30,
        "batter_partnership_share": 15.0 / 30.0,
        "partner_runs": 15,
        "balls_remaining_entry": 54,
        "balls_remaining_exit": 24,
        "wickets_remaining_entry": 9,
        "wickets_remaining_exit": 4,
        "wickets_lost_during_stay": 5,
        "wicket_resource_change": -5,
    }
    p3_worsened = compute_phase7c_p3(collapse_worsened)
    assert p3_worsened < -0.80, "Stalling innings with multiple wickets lost must produce negative P3 impact"

    # Monotonicity: higher required RR reduction in chase increases P3
    chase_high_relief = {
        "innings": 2, "actual_runs": 30, "balls_faced": 18, "actual_sr": 166.7,
        "required_rr_change": 3.5, "target_progress_change": 0.25,
        "partnership_runs": 45, "batter_partnership_share": 30.0 / 45.0,
    }
    chase_low_relief = {
        "innings": 2, "actual_runs": 30, "balls_faced": 18, "actual_sr": 166.7,
        "required_rr_change": -2.0, "target_progress_change": 0.25,
        "partnership_runs": 45, "batter_partnership_share": 30.0 / 45.0,
    }
    assert compute_phase7c_p3(chase_high_relief) > compute_phase7c_p3(chase_low_relief)


# ==============================================================================
# 3. PARTNERSHIP AND NON-STRIKER CALCULATIONS
# ==============================================================================
def test_phase7c_partnership_and_non_striker_dynamics():
    """Verify partner balls, partner runs, partner SR, and carrying status."""
    # Synthetic deliveries for an innings:
    # Over 1: Batter A (striker) hits 4, 1, then Partner B hits 0, 0, 1, Batter A hits 6
    # Total balls = 6: Batter A faced 3 balls (11 runs), Partner B faced 3 balls (1 run)
    delivs = [
        {"match_id": 1, "innings_number": 1, "batter": "Batter A", "non_striker": "Partner B", "batter_runs": 4, "total_runs": 4, "wides": 0, "noballs": 0, "player_dismissed": None},
        {"match_id": 1, "innings_number": 1, "batter": "Batter A", "non_striker": "Partner B", "batter_runs": 1, "total_runs": 1, "wides": 0, "noballs": 0, "player_dismissed": None},
        {"match_id": 1, "innings_number": 1, "batter": "Partner B", "non_striker": "Batter A", "batter_runs": 0, "total_runs": 0, "wides": 0, "noballs": 0, "player_dismissed": None},
        {"match_id": 1, "innings_number": 1, "batter": "Partner B", "non_striker": "Batter A", "batter_runs": 0, "total_runs": 0, "wides": 0, "noballs": 0, "player_dismissed": None},
        {"match_id": 1, "innings_number": 1, "batter": "Partner B", "non_striker": "Batter A", "batter_runs": 1, "total_runs": 1, "wides": 0, "noballs": 0, "player_dismissed": None},
        {"match_id": 1, "innings_number": 1, "batter": "Batter A", "non_striker": "Partner B", "batter_runs": 6, "total_runs": 6, "wides": 0, "noballs": 0, "player_dismissed": None},
    ]
    df_delivs = pd.DataFrame(delivs)
    p_list = extract_all_partnerships_from_deliveries(df_delivs)
    lookup = build_partnerships_lookup(p_list)

    prof_a = compute_batter_partnership_profile(1, 1, "Batter A", lookup)
    assert prof_a["batter_runs_in_partnerships"] == 11
    assert prof_a["batter_balls_in_partnerships"] == 3
    assert prof_a["partner_runs"] == 1
    assert prof_a["partner_balls"] == 3
    assert prof_a["partner_sr"] == round(1 / 3 * 100.0, 2)
    assert prof_a["batter_partnership_share"] == round(11 / 12, 3)

    prof_b = compute_batter_partnership_profile(1, 1, "Partner B", lookup)
    assert prof_b["batter_runs_in_partnerships"] == 1
    assert prof_b["partner_runs"] == 11


# ==============================================================================
# 4. STRICT OUTCOME INVARIANCE (ZERO LEAKAGE)
# ==============================================================================
def test_phase7c_outcome_invariance():
    """Verify that inverting match outcome fields changes 0.0 of P1, P2, P3, and final score."""
    row = {
        "innings": 1,
        "entry_over": 5.0,
        "balls_faced": 40,
        "actual_runs": 70,
        "actual_sr": 175.0,
        "expected_final_change": 25.0,
        "trajectory_deviation_change": 15.0,
        "window_team_rr": 9.5,
        "team_rr_entry": 7.0,
        "partnership_runs": 90,
        "batter_partnership_share": 70.0 / 90.0,
        "partner_runs": 20,
        "balls_remaining_entry": 90,
        "balls_remaining_exit": 20,
        "wickets_remaining_entry": 8,
        "wickets_remaining_exit": 6,
        "won_match": False,
        "winning_margin": 45,
        "final_team_score": 175,
    }

    res_orig = compute_phase7c_contribution(row)

    # Invert match outcome fields
    row_inverted = row.copy()
    row_inverted["won_match"] = True
    row_inverted["winning_margin"] = 0
    row_inverted["final_team_score"] = 220

    res_inv = compute_phase7c_contribution(row_inverted)

    assert res_orig["pillar1_context_score"] == res_inv["pillar1_context_score"]
    assert res_orig["pillar2_perf_score"] == res_inv["pillar2_perf_score"]
    assert res_orig["pillar3_state_score"] == res_inv["pillar3_state_score"]
    assert res_orig["contribution_score"] == res_inv["contribution_score"]
    assert res_orig["raw_contribution"] == res_inv["raw_contribution"]


# ==============================================================================
# 5. STRICT DNB AND NULL PRESERVATION
# ==============================================================================
def test_phase7c_dnb_and_null_preservation():
    """Verify DNB appearances strictly return NULL and are never treated as 0 or 50."""
    dnb_row = {"dnb": True, "player": "YS Chahal", "matches_played": 1}
    res = compute_phase7c_contribution(dnb_row)

    assert res["dnb"] is True
    assert res["contribution_score"] is None
    assert res["raw_contribution"] is None
    assert res["pillar1_context_score"] is None
    assert res["pillar2_perf_score"] is None
    assert res["pillar3_state_score"] is None
    assert res["pillar4_diagnostic"] is None


# ==============================================================================
# 6. ALL 20 REQUIRED EDGE CASES
# ==============================================================================
def test_phase7c_all_20_edge_cases():
    """Verify all 20 edge cases from Section 11 pass validation under Model A (25/35/40)."""
    eval_res = evaluate_phase7c_edge_cases()
    assert eval_res["total_edge_cases"] == 20
    cases_by_id = {c["case_id"]: c for c in eval_res["cases"]}

    # Case 1: 30 off 5 death overs -> Elite score (>75.0 under linear composite, high tier)
    assert cases_by_id[1]["model_a_score"] > 75.0
    assert cases_by_id[1]["p2_perf_score"] > 90.0

    # Case 2: 30 off 5 early overs -> Strong positive (>75.0)
    assert cases_by_id[2]["model_a_score"] > 75.0

    # Case 3: 1 off 1 to win the match -> Non-negligible, positive execution
    assert cases_by_id[3]["model_a_score"] is not None
    assert cases_by_id[3]["p3_state_score"] > 60.0  # Strong state change

    # Case 7: 20 off 25 high RRR -> Substantially below par (<40.0)
    assert cases_by_id[7]["model_a_score"] < 40.0

    # Case 9 vs Case 10: Losing hero vs Winning passenger
    assert cases_by_id[9]["model_a_score"] > 75.0  # Hero in losing effort
    assert cases_by_id[10]["model_a_score"] < 40.0  # Passenger in winning effort

    # Case 11: Batter carrying partnership -> High score
    assert cases_by_id[11]["model_a_score"] > 70.0

    # Case 14: Collapse recovery (20/4 -> 95/5) -> High score
    assert cases_by_id[14]["model_a_score"] > 72.0

    # Case 16: DNB -> strictly None
    assert cases_by_id[16]["model_a_score"] is None
    assert cases_by_id[16]["is_dnb"] is True

    # Case 18: 8* off 3 cameo -> protected (>62.0)
    assert cases_by_id[18]["model_a_score"] > 62.0

    # Case 20: 22* off 7 chase finisher -> Elite (>82.0)
    assert cases_by_id[20]["model_a_score"] > 82.0


# ==============================================================================
# 7. SEASON AGGREGATION & TEAM CONTRIBUTION SHARE COMPATIBILITY
# ==============================================================================
def test_phase7c_season_aggregation_compatibility():
    """Verify Phase 7C outputs plug directly into season aggregation and Team Share attribution."""
    # 5 innings evaluated under Phase 7C
    raw_inns = [
        {"innings": 1, "actual_runs": 65, "balls_faced": 40, "actual_sr": 162.5, "expected_final_change": 20.0, "window_team_rr": 9.5, "team_rr_entry": 7.5, "partnership_runs": 85, "batter_partnership_share": 65.0/85.0},
        {"innings": 2, "actual_runs": 45, "balls_faced": 30, "actual_sr": 150.0, "required_rr_change": 1.5, "target_progress_change": 0.28, "partnership_runs": 60, "batter_partnership_share": 45.0/60.0},
        {"innings": 1, "actual_runs": 12, "balls_faced": 15, "actual_sr": 80.0, "expected_final_change": -10.0, "window_team_rr": 6.5, "team_rr_entry": 8.5, "partnership_runs": 25, "batter_partnership_share": 12.0/25.0},
    ]
    eval_inns = []
    for inn in raw_inns:
        res = compute_phase7c_contribution(inn)
        eval_inns.append({
            "contribution_score": res["contribution_score"],
            "raw_contribution": res["raw_contribution"],
            "innings": inn["innings"],
            "dnb": False,
        })
    # Add 2 DNB matches
    eval_inns.append({"dnb": True, "contribution_score": None, "raw_contribution": None})
    eval_inns.append({"dnb": True, "contribution_score": None, "raw_contribution": None})

    season_agg = compute_season_aggregation(eval_inns, team_total_positive_contribution=15.0, matches_played=5)

    assert season_agg["matches_played"] == 5
    assert season_agg["batting_innings"] == 3
    assert season_agg["did_not_bat_matches"] == 2
    assert season_agg["average_contribution_score"] is not None
    assert season_agg["season_team_contribution_share"] is not None
    assert season_agg["season_team_contribution_share"] > 0.0
