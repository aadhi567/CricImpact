"""
Phase 7U: Dedicated Test Suite for P3 Wicket Causality Attribution (Model T).
Cricket Batter Contribution Model.

Verifies:
TEST A — Pooran Anchor Case (Match 1422133: 40 off 21, independent wickets -> gamma = 0.15, P3 ~ 52.2, Final ~ 67.8)
TEST B — Slow Batter Creates Pressure (10 off 15, high dots, low SR -> gamma = 1.0, P3 <= 30)
TEST C — Good Batter + Independent Wicket (efficient batter -> gamma = 0.15, P3 substantially higher than un-attributed model)
TEST D — Mixed Team Collapse (3+ partner wickets -> intermediate gamma = 0.50)
TEST E — Golden Duck (0 off 1 -> gamma = 1.0, no relief)
TEST F — Passenger Rejection (low personal tempo -> gamma = 1.0, no free ride)
TEST G — Normal 20-over Match (no partner wickets / positive drag -> unchanged, gamma = 1.0)
TEST H — Chase Context (2nd innings -> unchanged)
TEST I — Outcome Invariance (won_match True vs False -> delta = 0)
TEST J — Player Identity Invariance (Player A vs Player B -> delta = 0)
TEST K — Window Integrity (future / post-exit information -> delta = 0)
TEST L — DNB Strict Preservation (DNB remains None)
TEST M — P2 Independence (changing P2 parameters does not change P3)
TEST N — Phase 7O Compatibility (early-over stabilization unmodified)
TEST O — Governance and Backup Verification (backups and checksums match)
"""

import sys
from pathlib import Path
import pytest
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.contribution_framework import (
    P3_WICKET_ATTR_INDEPENDENT_GAMMA,
    P3_WICKET_ATTR_COLLAPSE_GAMMA,
    P3_WICKET_ATTR_STAGNATION_GAMMA,
    P3_WICKET_ATTR_CAUSED_GAMMA,
    compute_attributable_team_state_efs,
    compute_dampened_p3_raw,
    map_raw_to_p3_score,
    compute_production_contribution,
)
from src.phase7u_p3_wicket_causality import (
    evaluate_pooran_anchor_case,
    run_free_rider_audit,
    run_leakage_and_invariance_audit,
    verify_governance_and_backups,
)


# ==============================================================================
# TEST A: POORAN ANCHOR CASE
# ==============================================================================

def test_a_pooran_anchor_case():
    """
    N Pooran: Match 1422133, Innings 1.
    40 off 21 balls, SR 190.48.
    P2 = 86.5.
    Both partner wickets (de Kock, Badoni) are independent dismissals.
    Attribution: gamma = 0.15 (Category B).
    P3 must not remain near 22.3; must increase naturally to ~52.2.
    Final contribution score should increase from ~54.0 to ~67.8.
    """
    res = evaluate_pooran_anchor_case()

    assert res["attribution_gamma"] == 0.15, f"Expected gamma 0.15, got {res['attribution_gamma']}"
    assert res["attribution_category"] == "CATEGORY_B"

    # Pre-7U baseline
    p3_pre = res["pre_7u"]["p3"]
    final_pre = res["pre_7u"]["final_score"]
    assert 22.0 <= p3_pre <= 23.0, f"Expected un-attributed P3 ~22.3, got {p3_pre}"
    assert 53.5 <= final_pre <= 54.5, f"Expected un-attributed Final ~54.0, got {final_pre}"

    # Post-7U Model T
    p3_post = res["post_7u"]["p3"]
    final_post = res["post_7u"]["final_score"]
    assert 51.5 <= p3_post <= 53.5, f"Expected corrected P3 in [51.5, 53.5], got {p3_post}"
    assert 67.0 <= final_post <= 68.5, f"Expected corrected Final in [67.0, 68.5], got {final_post}"

    # Verify P2 and leverage invariance
    assert res["deltas"]["p2_invariant"] is True
    assert res["deltas"]["leverage_invariant"] is True


# ==============================================================================
# TEST B: SLOW BATTER CREATES PRESSURE
# ==============================================================================

def test_b_slow_batter_creates_pressure():
    """
    Slow batter crawls at 10 off 15 balls (SR 66.7, 60% dots).
    Partner takes forced risk and gets dismissed.
    Model T must classify as Category A (gamma = 1.0) and retain full penalty (P3 <= 30).
    """
    slow_row = pd.Series({
        "innings": 1,
        "actual_runs": 10.0,
        "expected_runs": 18.0,
        "actual_sr": 66.67,
        "expected_sr": 130.0,
        "sr_performance_ratio": 0.51,
        "balls_faced": 15,
        "dot_balls": 9,
        "dot_ball_percentage": 60.0,
        "expected_final_change": -22.0,
        "trajectory_deviation_change": -12.0,
        "wicket_resource_change": -1,
        "balls_remaining_exit": 40,
        "wickets_remaining_exit": 6,
        "overs_spent": 4.0,
        "team_rr_entry": 8.5,
        "window_team_rr": 6.2,
        "wickets_lost_during_stay": 2,
        "dismissal_status": "out",
        "score_perf": 28.0,
    })

    attr_efs, gamma, cat = compute_attributable_team_state_efs(slow_row)
    assert gamma == 1.0, f"Expected gamma 1.0 for slow batter, got {gamma}"
    assert cat == "CATEGORY_A"

    res = compute_production_contribution(slow_row)
    assert res["pillar3_state_score"] <= 30.0, f"Expected P3 <= 30, got {res['pillar3_state_score']}"
    assert res["gamma_attribution"] == 1.0
    assert res["attribution_category"] == "CATEGORY_A"


# ==============================================================================
# TEST C: GOOD BATTER + INDEPENDENT WICKET
# ==============================================================================

def test_c_good_batter_independent_wicket():
    """
    Good batter scores 40 off 20 balls (SR 200, 30% dots).
    Partner independently gets dismissed while team EFS drops by 18 runs.
    Model T must recognize Category B (gamma = 0.15) and substantially elevate P3.
    """
    good_row = pd.Series({
        "innings": 1,
        "actual_runs": 40.0,
        "expected_runs": 20.0,
        "actual_sr": 200.0,
        "expected_sr": 135.0,
        "sr_performance_ratio": 1.48,
        "balls_faced": 20,
        "dot_balls": 6,
        "dot_ball_percentage": 30.0,
        "expected_final_change": -18.0,
        "trajectory_deviation_change": -8.0,
        "wicket_resource_change": 0,
        "balls_remaining_exit": 10,
        "wickets_remaining_exit": 6,
        "overs_spent": 5.0,
        "team_rr_entry": 9.0,
        "window_team_rr": 9.2,
        "wickets_lost_during_stay": 1,
        "dismissal_status": "not out",
        "score_perf": 88.0,
    })

    attr_efs, gamma, cat = compute_attributable_team_state_efs(good_row)
    assert gamma == 0.15
    assert cat == "CATEGORY_B"

    res_unattributed = compute_production_contribution(good_row, apply_attribution=False)
    res_model_t = compute_production_contribution(good_row, apply_attribution=True)

    assert res_model_t["pillar3_state_score"] >= 50.0
    assert res_model_t["pillar3_state_score"] > res_unattributed["pillar3_state_score"] + 15.0


# ==============================================================================
# TEST D: MIXED TEAM COLLAPSE
# ==============================================================================

def test_d_mixed_team_collapse():
    """
    Batter scores 35 off 22 balls, but 4 partner wickets tumble at the other end.
    Evidence indicates severe multi-wicket collapse (Category C).
    Model T should assign gamma = 0.50 (intermediate attribution).
    """
    collapse_row = pd.Series({
        "innings": 1,
        "actual_runs": 35.0,
        "expected_runs": 22.0,
        "actual_sr": 159.09,
        "expected_sr": 130.0,
        "sr_performance_ratio": 1.22,
        "balls_faced": 22,
        "dot_balls": 8,
        "dot_ball_percentage": 36.36,
        "expected_final_change": -35.0,
        "trajectory_deviation_change": -20.0,
        "wicket_resource_change": 0,
        "balls_remaining_exit": 20,
        "wickets_remaining_exit": 3,
        "overs_spent": 7.0,
        "team_rr_entry": 8.5,
        "window_team_rr": 6.8,
        "wickets_lost_during_stay": 4,
        "dismissal_status": "not out",
        "score_perf": 75.0,
    })

    attr_efs, gamma, cat = compute_attributable_team_state_efs(collapse_row)
    assert gamma == 0.50, f"Expected gamma 0.50 for multi-wicket collapse, got {gamma}"
    assert cat == "CATEGORY_C"


# ==============================================================================
# TEST E: GOLDEN DUCK
# ==============================================================================

def test_e_golden_duck_exclusion():
    """
    Golden duck (0 off 1) receives zero relief.
    Gamma remains 1.0, full team decline charged.
    """
    gd_row = pd.Series({
        "innings": 1,
        "actual_runs": 0.0,
        "expected_runs": 1.2,
        "actual_sr": 0.0,
        "balls_faced": 1,
        "dot_ball_percentage": 100.0,
        "expected_final_change": -12.0,
        "wickets_lost_during_stay": 2,
        "dismissal_status": "out",
    })

    attr_efs, gamma, cat = compute_attributable_team_state_efs(gd_row)
    assert gamma == 1.0, f"Golden duck must receive gamma 1.0, got {gamma}"
    assert cat == "MINIMAL_STAY"


# ==============================================================================
# TEST F: PASSENGER REJECTION
# ==============================================================================

def test_f_passenger_rejection():
    """
    Passenger: 8 off 12 balls (SR 66.7), dot % = 58%.
    Partner hits big and then gets dismissed.
    Passenger must NOT receive high P3 or independent partner relief.
    """
    pass_row = pd.Series({
        "innings": 1,
        "actual_runs": 8.0,
        "expected_runs": 15.0,
        "actual_sr": 66.67,
        "balls_faced": 12,
        "dot_ball_percentage": 58.33,
        "sr_performance_ratio": 0.65,
        "expected_final_change": -14.0,
        "trajectory_deviation_change": -8.0,
        "window_team_rr": 7.0,
        "team_rr_entry": 8.5,
        "wickets_lost_during_stay": 2,
        "dismissal_status": "out",
        "wicket_resource_change": -1,
        "balls_remaining_exit": 50,
        "wickets_remaining_exit": 5,
    })

    attr_efs, gamma, cat = compute_attributable_team_state_efs(pass_row)
    assert gamma == 1.0, f"Passenger must receive gamma 1.0, got {gamma}"
    assert cat == "CATEGORY_A"

    res = compute_production_contribution(pass_row)
    assert res["pillar3_state_score"] <= 35.0


# ==============================================================================
# TEST G: NORMAL 20-OVER MATCH (NO ATTRIBUTION RELEVANT)
# ==============================================================================

def test_g_normal_match_unchanged():
    """
    Normal match where team EFS increases or no partner wickets fell.
    Attribution must leave EFS change and P3 bitwise/numerically unchanged.
    """
    normal_row = pd.Series({
        "innings": 1,
        "actual_runs": 45.0,
        "expected_runs": 30.0,
        "balls_faced": 25,
        "actual_sr": 180.0,
        "dot_ball_percentage": 28.0,
        "expected_final_change": 14.5,  # positive drag
        "trajectory_deviation_change": 10.0,
        "wicket_resource_change": 0,
        "balls_remaining_exit": 15,
        "wickets_remaining_exit": 7,
        "window_team_rr": 10.5,
        "team_rr_entry": 8.0,
        "wickets_lost_during_stay": 0,
        "dismissal_status": "not out",
        "score_perf": 82.0,
    })

    attr_efs, gamma, cat = compute_attributable_team_state_efs(normal_row)
    assert gamma == 1.0
    assert attr_efs == 14.5
    assert cat in ["POSITIVE_DRAG", "NO_WICKETS"]

    res_pre = compute_production_contribution(normal_row, apply_attribution=False)
    res_post = compute_production_contribution(normal_row, apply_attribution=True)
    assert res_pre["pillar3_state_score"] == res_post["pillar3_state_score"]
    assert res_pre["final_contribution_score"] == res_post["final_contribution_score"]


# ==============================================================================
# TEST H: CHASE CONTEXT
# ==============================================================================

def test_h_chase_context():
    """
    Second innings (chase).
    Model T returns gamma = 1.0 and category 'CHASE' without modifying RRR logic.
    """
    chase_row = pd.Series({
        "innings": 2,
        "actual_runs": 50.0,
        "expected_runs": 35.0,
        "balls_faced": 28,
        "required_rr_change": 2.5,
        "rr_gap_change": 1.8,
        "target_progress_change": 0.35,
        "required_rr_entry": 9.2,
        "balls_remaining_entry": 60,
        "wickets_remaining_entry": 7,
        "wicket_resource_change": 0,
        "balls_remaining_exit": 25,
        "wickets_remaining_exit": 7,
        "dismissal_status": "not out",
        "score_perf": 80.0,
    })

    attr_efs, gamma, cat = compute_attributable_team_state_efs(chase_row)
    assert gamma == 1.0
    assert cat == "CHASE"

    res_pre = compute_production_contribution(chase_row, apply_attribution=False)
    res_post = compute_production_contribution(chase_row, apply_attribution=True)
    assert res_pre["pillar3_state_score"] == res_post["pillar3_state_score"]
    assert res_pre["final_contribution_score"] == res_post["final_contribution_score"]


# ==============================================================================
# TEST I: OUTCOME INVARIANCE
# ==============================================================================

def test_i_outcome_invariance():
    """won_match True vs False produces identical scores."""
    audit = run_leakage_and_invariance_audit()
    assert audit["outcome_invariance"]["passed"] is True
    assert audit["outcome_invariance"]["delta"] == 0.0


# ==============================================================================
# TEST J: PLAYER IDENTITY INVARIANCE
# ==============================================================================

def test_j_player_identity_invariance():
    """Changing player identity produces identical scores."""
    audit = run_leakage_and_invariance_audit()
    assert audit["player_identity_invariance"]["passed"] is True
    assert audit["player_identity_invariance"]["delta"] == 0.0


# ==============================================================================
# TEST K: WINDOW INTEGRITY
# ==============================================================================

def test_k_window_integrity():
    """Post-exit or future match information has zero impact on contribution score."""
    audit = run_leakage_and_invariance_audit()
    assert audit["future_information_invariance"]["passed"] is True
    assert audit["future_information_invariance"]["delta"] == 0.0


# ==============================================================================
# TEST L: DNB STRICT PRESERVATION
# ==============================================================================

def test_l_dnb_preservation():
    """DNB innings return contribution_score = None and dnb = True."""
    audit = run_leakage_and_invariance_audit()
    assert audit["dnb_preservation"]["passed"] is True


# ==============================================================================
# TEST M: P2 INDEPENDENCE
# ==============================================================================

def test_m_p2_independence():
    """P3 does NOT directly depend on P2 score (P3 != f(P2))."""
    audit = run_leakage_and_invariance_audit()
    assert audit["p2_independence"]["passed"] is True
    assert audit["p2_independence"]["delta_p3"] == 0.0


# ==============================================================================
# TEST N: PHASE 7O COMPATIBILITY
# ==============================================================================

def test_n_phase7o_compatibility():
    """Unmodelled and early-over 1st innings remain compatible with Phase 7O."""
    audit = run_leakage_and_invariance_audit()
    assert audit["phase7o_compatibility"]["passed"] is True


# ==============================================================================
# TEST O: GOVERNANCE AND BACKUPS
# ==============================================================================

def test_o_governance_and_backups():
    """Verify that pre-integration backup exists with valid SHA256 and MD5."""
    gov = verify_governance_and_backups()
    assert gov["all_passed"] is True, f"Governance failure: {gov['checks']}"
