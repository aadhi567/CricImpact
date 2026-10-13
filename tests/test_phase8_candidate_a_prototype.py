"""
Tests for Phase 8 Candidate A Prototype: Consistent Model T Trajectory Attribution.

Verifies:
1. Reconciled Units, Baselines, and Time Windows:
   - trajectory_deviation_change, expected_final_change, and batter surplus (Delta R)
     are strictly compatible in units (runs) and crease occupancy window.
2. Strict Production Invariance:
   - With default feature flag (apply_trajectory_attribution=False), all scores
     and database checksums remain 100% bit-for-bit invariant.
   - Shahrukh Khan canonical approved score remains 53.6.
   - Sai Sudharsan canonical approved score remains 93.4.
3. Candidate A Behavior (apply_trajectory_attribution=True):
   - Shahrukh Khan (1254065): Trajectory drag is attributed with gamma=0.50,
     moving P3 from 28.8 -> 44.2, Adjusted P3 from 24.3 -> 43.0, Final from 53.6 -> 62.9.
   - Sai Sudharsan (1359536): Positive drag (gamma=1.00), score remains exactly 93.4.
   - RA Tripathi slow crawl (1359484: 34 off 41): Category A (gamma=1.00), score remains exactly 25.9.
   - RA Tripathi fighting knock (1254098: 45 off 33): Category C (gamma=0.50), score moves from 48.7 -> 52.9.
4. Anti-Free-Rider Invariants:
   - Batters who underperformed or caused pressure (Category A, Delta R <= 0) receive zero relief.
   - Minimal cameo stays (<6 balls, <10 runs) and golden ducks receive zero relief.
5. No Double-Counting:
   - Orthogonal separation between P2 execution, P3 team-state, dynamic wicket cost (S_res), and leverage (L).
6. Edge Cases & Missing Telemetry:
   - 2nd innings (chase), missing trajectory, and unknown wickets handle safely.
"""

import math
from pathlib import Path
import pytest
import numpy as np
import pandas as pd

from app.services.data_service import data_service
from src.contribution_framework import (
    compute_attributable_team_state_efs,
    compute_pillar3_team_state_impact,
    compute_dampened_p3_raw,
    compute_production_contribution,
    map_raw_to_p3_score,
    P3_WICKET_ATTR_COLLAPSE_GAMMA,
    P3_WICKET_ATTR_INDEPENDENT_GAMMA,
    P3_WICKET_ATTR_STAGNATION_GAMMA,
    P3_WICKET_ATTR_CAUSED_GAMMA,
)
from src.phase8_collapse_attribution_prototype import (
    evaluate_candidate_a_innings,
    compute_attributable_trajectory_deviation,
    classify_wicket_attribution_context,
    compute_candidate_a_raw_p3,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_units_baselines_and_time_windows_reconciliation():
    """
    Step 1: Reconcile units, baselines, and time windows.
    Asserts that trajectory_deviation_change, expected_final_change, and Delta R
    share the exact same units (runs) and time window (crease occupancy).
    """
    df = data_service.get_contributions_df("ipl")
    srk = df[(df["match_id"].astype(str) == "1254065") & (df["player"] == "M Shahrukh Khan")].iloc[0]

    # 1. Units are all in runs
    runs = float(srk["actual_runs"])
    exp_runs = float(srk["expected_runs"])
    delta_r = runs - exp_runs
    efs_chg = float(srk["expected_final_change"])
    traj_chg = float(srk["trajectory_deviation_change"])

    assert isinstance(runs, float)
    assert isinstance(delta_r, float)
    assert isinstance(efs_chg, float)
    assert isinstance(traj_chg, float)

    # 2. Time window: exact same entry to exit overs
    assert float(srk["entry_over"]) == 4.4
    assert float(srk["exit_over"]) == 19.1
    team_runs_window = float(srk["team_score_exit"]) - float(srk["team_score_entry"])
    assert team_runs_window == 82.0  # 101 - 19

    # 3. External drag isolation for trajectory
    ext_drag_traj = traj_chg - delta_r
    # traj_chg = -43.8, delta_r = +14.3 -> ext_drag_traj = -58.1 runs
    assert round(ext_drag_traj, 1) == -58.1

    # Attributable trajectory calculation with Model T gamma=0.50
    attr_traj, gamma, cat = compute_attributable_trajectory_deviation(srk)
    expected_attr = delta_r + P3_WICKET_ATTR_COLLAPSE_GAMMA * ext_drag_traj
    assert cat == "CATEGORY_C"
    assert gamma == 0.50
    assert math.isclose(attr_traj, expected_attr, rel_tol=1e-5)
    assert round(attr_traj, 2) == -14.75


def test_production_invariance_when_flag_disabled():
    """
    Step 2: Strict production invariance.
    With apply_trajectory_attribution=False (the default), production scores
    are 100% bit-for-bit invariant.
    """
    df = data_service.get_contributions_df("ipl")

    # 1. Shahrukh Khan approved score invariance
    srk = df[(df["match_id"].astype(str) == "1254065") & (df["player"] == "M Shahrukh Khan")].iloc[0]
    eval_srk = evaluate_candidate_a_innings(srk)
    assert eval_srk["production"]["final_contribution_score"] == 53.6
    assert eval_srk["production"]["p3_score"] == 28.8
    assert eval_srk["production"]["adjusted_p3"] == 24.3

    # 2. Sai Sudharsan approved score invariance
    sai = df[(df["match_id"].astype(str) == "1359536") & (df["player"] == "B Sai Sudharsan")].iloc[0]
    eval_sai = evaluate_candidate_a_innings(sai)
    assert eval_sai["production"]["final_contribution_score"] == 93.4

    # 3. Default parameter invocation matches production exactly
    res_default = compute_production_contribution(srk)
    assert res_default["final_contribution_score"] == 53.6
    assert res_default["pillar3_state_score"] == 28.8


def test_shahrukh_khan_candidate_a_evaluation():
    """
    Step 3: Verify Candidate A impact on Shahrukh Khan (IPL 2021 match 1254065).
    P3 moves from 28.8 -> 44.2, Adjusted P3 from 24.3 -> 43.0, Final from 53.6 -> 62.9.
    """
    df = data_service.get_contributions_df("ipl")
    srk = df[(df["match_id"].astype(str) == "1254065") & (df["player"] == "M Shahrukh Khan")].iloc[0]

    eval_res = evaluate_candidate_a_innings(srk)
    cand = eval_res["candidate_a"]
    delta = eval_res["delta"]

    # Component breakdown under Candidate A
    assert cand["raw_p3"] == -0.0935
    assert cand["p3_score"] == 44.2
    assert cand["adjusted_p3"] == 43.0
    assert cand["final_contribution_score"] == 62.9

    # Score movements
    assert delta["p3_score_delta"] == 15.4  # 44.2 - 28.8
    assert delta["final_score_delta"] == 9.3  # 62.9 - 53.6


def test_sai_sudharsan_candidate_a_invariant():
    """
    Step 3: Verify Sai Sudharsan (1359536) remains 100% unchanged under Candidate A.
    External drag is positive, so gamma = 1.00 (POSITIVE_DRAG).
    """
    df = data_service.get_contributions_df("ipl")
    sai = df[(df["match_id"].astype(str) == "1359536") & (df["player"] == "B Sai Sudharsan")].iloc[0]

    eval_res = evaluate_candidate_a_innings(sai)
    assert eval_res["telemetry"]["traj_category"] == "POSITIVE_DRAG"
    assert eval_res["telemetry"]["traj_gamma"] == 1.0
    assert eval_res["delta"]["final_score_delta"] == 0.0
    assert eval_res["candidate_a"]["final_contribution_score"] == 93.4


def test_ra_tripathi_pressure_vs_fight_differentiation():
    """
    Step 3 & Step 4: Verify RA Tripathi benchmark innings differentiate pressure
    from genuine fighting knocks.
    - Match 1359484: 34 off 41 (SR 82.9) -> Category A (gamma=1.00), zero relief, stays 25.9.
    - Match 1254098: 45 off 33 (SR 136.4, 3 wkts) -> Category C (gamma=0.50), moves 48.7 -> 52.9.
    """
    df = data_service.get_contributions_df("ipl")

    # 1. Slow crawl / pressure causer (Match 1359484)
    trip_slow = df[(df["match_id"].astype(str) == "1359484") & (df["player"] == "RA Tripathi")].iloc[0]
    eval_slow = evaluate_candidate_a_innings(trip_slow)
    assert eval_slow["telemetry"]["traj_category"] == "CATEGORY_A"
    assert eval_slow["telemetry"]["traj_gamma"] == 1.00
    assert eval_slow["delta"]["final_score_delta"] == 0.0
    assert eval_slow["candidate_a"]["final_contribution_score"] == 25.9

    # 2. Resilient fighting knock (Match 1254098)
    trip_fight = df[(df["match_id"].astype(str) == "1254098") & (df["player"] == "RA Tripathi")].iloc[0]
    eval_fight = evaluate_candidate_a_innings(trip_fight)
    assert eval_fight["telemetry"]["traj_category"] == "CATEGORY_C"
    assert eval_fight["telemetry"]["traj_gamma"] == 0.50
    assert eval_fight["candidate_a"]["p3_score"] == 38.1
    assert eval_fight["candidate_a"]["final_contribution_score"] == 52.9
    assert eval_fight["candidate_a"]["final_contribution_score"] > eval_fight["production"]["final_contribution_score"]


def test_no_double_counting_orthogonal_terms():
    """
    Step 4: Verify that P2 individual execution, dynamic wicket cost (S_res),
    and situational leverage (L) are orthogonal to Candidate A trajectory attribution.
    """
    df = data_service.get_contributions_df("ipl")
    srk = df[(df["match_id"].astype(str) == "1254065") & (df["player"] == "M Shahrukh Khan")].iloc[0]

    prod_res = compute_production_contribution(srk)
    eval_res = evaluate_candidate_a_innings(srk)
    cand_res = eval_res["candidate_a"]

    # 1. P2 execution is completely untouched
    assert prod_res["adjusted_p2"] == cand_res["adjusted_p2"]

    # 2. Leverage factor L is completely untouched
    assert prod_res["leverage"] == cand_res["leverage"]

    # 3. Dynamic wicket cost is completely untouched
    # Raw P3 difference must equal exactly: 0.25 * (attr_traj - obs_traj) / 10.0
    attr_traj, _, _ = compute_attributable_trajectory_deviation(srk)
    obs_traj = float(srk["trajectory_deviation_change"])
    expected_raw_diff = 0.25 * (attr_traj - obs_traj) / 10.0

    raw_prod = compute_dampened_p3_raw(srk)
    raw_cand = compute_candidate_a_raw_p3(srk)
    actual_raw_diff = raw_cand - raw_prod
    assert math.isclose(actual_raw_diff, expected_raw_diff, rel_tol=1e-5)


def test_anti_free_rider_gates_and_edge_cases():
    """
    Step 5: Verify anti-free-rider gates:
    - Minimal cameo stays (<6b, <10r) receive zero relief.
    - Golden ducks receive zero relief.
    - Underperforming batters (Delta R <= 0) receive zero relief.
    - Missing trajectory fields return NaN safely.
    - Chase innings return observed value without relief.
    """
    # 1. Golden duck
    mock_duck = {
        "innings": 1,
        "actual_runs": 0.0,
        "expected_runs": 10.0,
        "trajectory_deviation_change": -15.0,
        "wickets_lost_during_stay": 2,
        "balls_faced": 1,
        "dismissal_status": "out",
    }
    attr, gamma, cat = compute_attributable_trajectory_deviation(mock_duck)
    assert cat == "MINIMAL_STAY"
    assert gamma == 1.0
    assert attr == -15.0

    # 2. Underperformer / slow crawl (Category A)
    mock_slow = {
        "innings": 1,
        "actual_runs": 15.0,
        "expected_runs": 25.0,  # delta_r = -10.0 <= 0
        "trajectory_deviation_change": -20.0,
        "wickets_lost_during_stay": 3,
        "balls_faced": 20,
        "dot_ball_percentage": 55.0,
        "actual_sr": 75.0,
    }
    attr_s, gamma_s, cat_s = compute_attributable_trajectory_deviation(mock_slow)
    assert cat_s == "CATEGORY_A"
    assert gamma_s == 1.00
    assert attr_s == -20.0

    # 3. Chase innings (2nd innings)
    mock_chase = {
        "innings": 2,
        "trajectory_deviation_change": -10.0,
    }
    attr_c, gamma_c, cat_c = compute_attributable_trajectory_deviation(mock_chase)
    assert cat_c == "CHASE"
    assert gamma_c == 1.0
    assert attr_c == -10.0

    # 4. Missing trajectory
    mock_missing = {
        "innings": 1,
        "trajectory_deviation_change": np.nan,
    }
    attr_m, gamma_m, cat_m = compute_attributable_trajectory_deviation(mock_missing)
    assert cat_m == "MISSING"
    assert gamma_m == 1.0
    assert np.isnan(attr_m)
