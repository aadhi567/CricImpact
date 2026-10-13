"""
Unit and Integration Tests for Phase 7Q: Decoupled P3 Neutral-State Preservation Floor.
Cricket Batter Contribution Model.

Verifies:
1. Eligible strong-state preservation (P3 elevates to 64.0 floor).
2. High existing P3 remains unchanged (no bonus added).
3. Strong-state deterioration not protected (P3 remains low, Delta EFS < -2.5 rejected).
4. Anti-free-rider passenger rejection (personal RR < 8.5 gets no floor).
5. Golden duck exclusion (0 off 1 gets no floor).
6. DNB preservation (DNB = None).
7. First innings tempo and state gates (EFS >= 180, window RR >= 9.0, personal RR >= 8.5).
8. Chase RRR and progress gates (RRR <= 7.5, delta RRR >= -0.5, progress >= 0.20, personal RR >= RRR_entry).
9. Below-minimum involvement gate (balls_faced < 8 and actual_runs < 15 gets no floor).
10. Minimum involvement qualification (balls_faced >= 8 OR actual_runs >= 15).
11. P2/P3 mathematical independence (varying P2 has 0.00 impact on P3 score or eligibility).
12. Player identity invariance (player name has 0.00 impact on P3 or final contribution).
13. Match outcome invariance (future match result has 0.00 impact on P3 or final contribution).
14. Phase 7O compatibility (early-over stabilization unmodified).
15. Governance checksums and backup verification.
16. Sensitivity analysis range consistency (floors 60-64 behave monotonically).
"""

import math
import hashlib
from pathlib import Path
import pytest
import numpy as np
import pandas as pd

from src.contribution_framework import (
    P3_STANDARDIZATION_MEAN,
    P3_STANDARDIZATION_STD,
    P3_STANDARDIZATION_SCALE,
    P3_PRESERVATION_FLOOR_DEFAULT,
    map_raw_to_p3_score,
    check_p3_preservation_eligibility,
    apply_p3_state_preservation_floor,
    apply_p3_score_preservation_floor,
    compute_dampened_p3_raw,
    compute_pillar2_batter_performance,
    compute_context_and_leverage,
    compute_adjusted_pillar,
    compute_production_contribution,
    PHASE5B_EMPIRICAL_PARAMS,
)

from src.phase7q_p3_neutral_state_preservation import (
    make_synthetic_row,
    evaluate_innings_phase7o_vs_phase7q,
    PRE_MODIFICATION_HASHES,
    verify_governance_and_backups,
)


def test_governance_and_backups_intact():
    """Verify that protected files exist in backup with exact SHA256 and MD5 hashes."""
    gov = verify_governance_and_backups()
    assert gov["all_passed"], f"Governance failure: {gov['files']}"


def test_eligible_strong_state_preservation():
    """
    Scenario C: Strong inherited state maintained.
    Batter scores 50 off 25 balls, entry at 110/1 in 10 ov (EFS 205), exit at 165/2 in 14.1 ov (EFS 207).
    Under Phase 7O, P3 is compressed near 52.5.
    Under Phase 7Q, P3 must elevate to the approved 64.0 preservation floor.
    """
    row_c = make_synthetic_row(
        entry_over=10.0, exit_over=14.1, entry_score=110.0, exit_score=165.0,
        team_rr_entry=11.0, team_rr_exit=11.7, efs_entry=205.0, efs_exit=207.0,
        traj_dev_chg=1.0, wkts_rem_entry=9, wkts_rem_exit=8,
    )
    assert check_p3_preservation_eligibility(row_c) is True

    raw_7o = compute_dampened_p3_raw(row_c, strategy="model_e", apply_preservation=False)
    p3_7o = map_raw_to_p3_score(raw_7o)
    assert 50.0 <= p3_7o <= 55.0, f"Expected Phase 7O P3 ~ 52.5, got {p3_7o}"

    raw_7q = compute_dampened_p3_raw(row_c, strategy="model_e", apply_preservation=True)
    p3_7q = map_raw_to_p3_score(raw_7q)
    assert pytest.approx(p3_7q, abs=0.1) == 64.0, f"Expected Phase 7Q P3 ~ 64.0, got {p3_7q}"
    assert p3_7q > p3_7o, "Phase 7Q must be higher than Phase 7O for preserved state"


def test_high_existing_p3_remains_unchanged():
    """
    Scenario A & B: Large transformation already produces high P3.
    Preservation floor must behave strictly as a floor (max(raw, floor)), NOT an additive bonus.
    """
    # Scenario A: Weak Entry -> Transform
    row_a = make_synthetic_row(
        entry_over=10.0, exit_over=14.1, entry_score=50.0, exit_score=105.0,
        team_rr_entry=5.0, team_rr_exit=7.45, efs_entry=135.0, efs_exit=168.0,
        traj_dev_chg=20.0, wkts_rem_entry=6, wkts_rem_exit=5,
    )
    raw_7o_a = compute_dampened_p3_raw(row_a, strategy="model_e", apply_preservation=False)
    raw_7q_a = compute_dampened_p3_raw(row_a, strategy="model_e", apply_preservation=True)
    assert pytest.approx(raw_7q_a, abs=1e-5) == raw_7o_a
    assert map_raw_to_p3_score(raw_7q_a) > 85.0

    # Scenario B: Average Entry -> Transform
    row_b = make_synthetic_row(
        entry_over=10.0, exit_over=14.1, entry_score=80.0, exit_score=135.0,
        team_rr_entry=8.0, team_rr_exit=9.57, efs_entry=165.0, efs_exit=182.0,
        traj_dev_chg=10.0, wkts_rem_entry=8, wkts_rem_exit=7,
    )
    raw_7o_b = compute_dampened_p3_raw(row_b, strategy="model_e", apply_preservation=False)
    raw_7q_b = compute_dampened_p3_raw(row_b, strategy="model_e", apply_preservation=True)
    assert pytest.approx(raw_7q_b, abs=1e-5) == raw_7o_b
    assert map_raw_to_p3_score(raw_7q_b) > 70.0


def test_qualifying_maintenance_with_p3_already_above_floor():
    """
    If an appearance qualifies for the preservation floor but already has P3 > 64.0,
    P3 must remain strictly unchanged (no artificial boost).
    """
    row_high = make_synthetic_row(
        entry_over=10.0, exit_over=14.1, entry_score=110.0, exit_score=180.0,  # 70 runs added in 4.1 ov!
        team_rr_entry=11.0, team_rr_exit=12.7, efs_entry=205.0, efs_exit=225.0,
        traj_dev_chg=15.0, wkts_rem_entry=9, wkts_rem_exit=8,
    )
    raw_7o = compute_dampened_p3_raw(row_high, apply_preservation=False)
    p3_7o = map_raw_to_p3_score(raw_7o)
    assert p3_7o > 64.0, f"Expected P3 > 64.0, got {p3_7o}"

    raw_7q = compute_dampened_p3_raw(row_high, apply_preservation=True)
    p3_7q = map_raw_to_p3_score(raw_7q)
    assert pytest.approx(p3_7q, abs=1e-5) == p3_7o, "P3 already > 64.0 must remain identical"


def test_strong_state_deterioration_not_protected():
    """
    Scenario D: Strong Entry -> Deterioration.
    Batter scores 15 off 20 balls (SR 75.0), team crawls, EFS collapses from 205 to 175 (delta EFS = -30).
    Must NOT receive preservation floor; P3 must remain severely depressed (< 20.0).
    """
    row_d = make_synthetic_row(
        entry_over=10.0, exit_over=14.1, balls_faced=20, actual_runs=15, fours=1, sixes=0,
        entry_score=110.0, exit_score=128.0, team_rr_entry=11.0, team_rr_exit=9.08,
        efs_entry=205.0, efs_exit=175.0, traj_dev_chg=-25.0, wkts_rem_entry=9, wkts_rem_exit=8,
    )
    assert check_p3_preservation_eligibility(row_d) is False
    raw_7o = compute_dampened_p3_raw(row_d, strategy="model_e", apply_preservation=False)
    raw_7q = compute_dampened_p3_raw(row_d, strategy="model_e", apply_preservation=True)
    assert pytest.approx(raw_7q, abs=1e-5) == raw_7o
    assert map_raw_to_p3_score(raw_7q) < 15.0


def test_passenger_rejection_anti_free_rider():
    """
    Passenger: Batter scores 8 off 12 balls (SR 66.7, personal RR = 4.0 RPO) in strong team platform.
    Partner scores rapidly, so team state remains high.
    Anti-free-rider gate (personal_rr >= 8.5) must strictly reject passenger from preservation floor.
    """
    row_passenger = make_synthetic_row(
        entry_over=10.0, exit_over=14.1, balls_faced=12, actual_runs=8, fours=0, sixes=0,
        entry_score=110.0, exit_score=165.0, team_rr_entry=11.0, team_rr_exit=11.7,
        efs_entry=205.0, efs_exit=207.0, traj_dev_chg=1.0, wkts_rem_entry=9, wkts_rem_exit=8,
    )
    assert check_p3_preservation_eligibility(row_passenger) is False
    raw_7o = compute_dampened_p3_raw(row_passenger, strategy="model_e", apply_preservation=False)
    raw_7q = compute_dampened_p3_raw(row_passenger, strategy="model_e", apply_preservation=True)
    assert pytest.approx(raw_7q, abs=1e-5) == raw_7o
    assert map_raw_to_p3_score(raw_7q) <= 51.0


def test_golden_duck_exclusion():
    """
    Golden Duck (0 off 1) in strong team state must NEVER receive preservation credit.
    """
    row_duck = make_synthetic_row(
        entry_over=10.0, exit_over=10.1, balls_faced=1, actual_runs=0, fours=0, sixes=0,
        entry_score=110.0, exit_score=110.0, team_rr_entry=11.0, team_rr_exit=10.82,
        efs_entry=205.0, efs_exit=196.0, traj_dev_chg=-9.0, wkts_rem_entry=9, wkts_rem_exit=8,
    )
    assert check_p3_preservation_eligibility(row_duck) is False
    raw_7o = compute_dampened_p3_raw(row_duck, strategy="model_e", apply_preservation=False)
    raw_7q = compute_dampened_p3_raw(row_duck, strategy="model_e", apply_preservation=True)
    assert pytest.approx(raw_7q, abs=1e-5) == raw_7o
    assert map_raw_to_p3_score(raw_7q) < 20.0


def test_minimum_involvement_gate():
    """
    Involvement requirement: balls_faced >= 8 OR actual_runs >= 15.
    A batter with 6 balls and 5 runs does NOT qualify.
    A batter with 6 balls and 16 runs DOES qualify (e.g. Ben Cutting).
    """
    # 6 balls, 5 runs -> no floor
    r_sub = make_synthetic_row(
        balls_faced=6, actual_runs=5, entry_score=110.0, exit_score=130.0,
        team_rr_entry=11.0, team_rr_exit=11.5, efs_entry=205.0, efs_exit=205.0,
    )
    assert check_p3_preservation_eligibility(r_sub) is False
    raw_sub_7o = compute_dampened_p3_raw(r_sub, apply_preservation=False)
    raw_sub_7q = compute_dampened_p3_raw(r_sub, apply_preservation=True)
    assert pytest.approx(raw_sub_7q, abs=1e-5) == raw_sub_7o

    # 6 balls, 16 runs (actual_runs >= 15) -> qualifies! (e.g. BCJ Cutting Match 1082591)
    df = pd.read_csv("data/processed/batter_match_contributions.csv", low_memory=False)
    r_cutting = df[(df["match_id"] == 1082591) & (df["player"] == "BCJ Cutting")].iloc[0]
    assert check_p3_preservation_eligibility(r_cutting) is True
    raw_cut_7o = compute_dampened_p3_raw(r_cutting, apply_preservation=False)
    raw_cut_7q = compute_dampened_p3_raw(r_cutting, apply_preservation=True)
    assert raw_cut_7q > raw_cut_7o
    assert map_raw_to_p3_score(raw_cut_7q) == 64.0


def test_first_innings_tempo_and_state_gates():
    """
    Verify 1st innings gates:
    - efs_entry >= 180.0
    - delta_efs >= -2.5
    - window_team_rr >= 9.0
    - personal_rr >= 8.5
    """
    # 1. efs_entry = 175.0 (< 180.0) -> no preservation floor
    r_low_efs = make_synthetic_row(efs_entry=175.0, efs_exit=177.0)
    assert check_p3_preservation_eligibility(r_low_efs) is False

    # 2. delta_efs = -3.0 (< -2.5) -> no preservation floor
    r_collapse = make_synthetic_row(efs_entry=200.0, efs_exit=197.0)
    assert check_p3_preservation_eligibility(r_collapse) is False

    # 3. window_team_rr = 7.0 (< 9.0) -> no preservation floor
    r_slow_team = make_synthetic_row(
        entry_over=10.0, exit_over=15.0, entry_score=110.0, exit_score=145.0,  # 35 runs in 5 ov = 7.0 RPO
        efs_entry=200.0, efs_exit=200.0,
    )
    assert check_p3_preservation_eligibility(r_slow_team) is False

    # 4. personal_rr = 7.5 (< 8.5) -> no preservation floor
    r_slow_personal = make_synthetic_row(
        balls_faced=20, actual_runs=25,  # 25 off 20 = 7.5 RPO
        entry_score=110.0, exit_score=165.0, efs_entry=200.0, efs_exit=200.0,
    )
    assert check_p3_preservation_eligibility(r_slow_personal) is False


def test_chase_rrr_and_progress_gates():
    """
    Verify 2nd innings chase gates:
    - rrr_entry <= 7.5
    - rrr_change >= -0.5
    - target_progress_change >= 0.20
    - personal_rr >= rrr_entry
    """
    # 1. High entry RRR (9.5 > 7.5) -> not eligible for preservation floor
    r_high_rrr = make_synthetic_row(
        innings=2, required_rr_entry=9.5, required_rr_change=0.5, target_progress_change=0.25,
        actual_runs=30, balls_faced=15,  # personal RR = 12.0
    )
    assert check_p3_preservation_eligibility(r_high_rrr) is False

    # 2. Chase blowout (rrr_change = -1.0 < -0.5) -> no preservation floor
    r_blowout = make_synthetic_row(
        innings=2, required_rr_entry=6.0, required_rr_change=-1.0, target_progress_change=0.25,
        actual_runs=30, balls_faced=15,
    )
    assert check_p3_preservation_eligibility(r_blowout) is False

    # 3. Insufficient target progress (< 0.20) -> no preservation floor
    r_little_prog = make_synthetic_row(
        innings=2, required_rr_entry=6.0, required_rr_change=0.5, target_progress_change=0.10,
        actual_runs=20, balls_faced=10,
    )
    assert check_p3_preservation_eligibility(r_little_prog) is False

    # 4. Chase Passenger: personal RR below entry RRR -> rejected
    r_chase_pass = make_synthetic_row(
        innings=2, required_rr_entry=7.0, required_rr_change=1.0, target_progress_change=0.30,
        actual_runs=10, balls_faced=15,  # personal RR = 4.0 < 7.0
    )
    assert check_p3_preservation_eligibility(r_chase_pass) is False


def test_dnb_strict_preservation():
    """Verify DNB appearances strictly remain None."""
    row_dnb = pd.Series({"balls_faced": np.nan, "actual_runs": np.nan, "innings": 1, "is_dnb": True})
    assert check_p3_preservation_eligibility(row_dnb) is False

    res = compute_production_contribution(row_dnb, apply_preservation=True)
    assert res["dnb"] is True
    assert res["pillar3_state_score"] is None
    assert res["final_contribution_score"] is None


def test_p2_p3_mathematical_independence():
    """
    CRITICAL ARCHITECTURAL MANDATE:
    P3 does NOT directly depend on P2 (score_perf).
    Varying P2 while holding team state and batting performance parameters constant
    must yield ZERO delta in P3 floor eligibility and P3 score.
    """
    row_base = make_synthetic_row(
        entry_over=10.0, exit_over=14.1, entry_score=110.0, exit_score=165.0,
        team_rr_entry=11.0, team_rr_exit=11.7, efs_entry=205.0, efs_exit=207.0,
        traj_dev_chg=1.0, wkts_rem_entry=9, wkts_rem_exit=8,
    )

    p3_scores = []
    p2_test_values = [55.0, 70.0, 85.0, 92.0, 99.0]
    for p2_val in p2_test_values:
        r = row_base.copy()
        r["score_perf"] = p2_val
        r["p2"] = p2_val
        raw_p3 = compute_dampened_p3_raw(r, strategy="model_e", apply_preservation=True)
        p3_scores.append(map_raw_to_p3_score(raw_p3))

    for score in p3_scores[1:]:
        assert pytest.approx(score, abs=1e-7) == p3_scores[0], f"P3 varied with P2! {p3_scores}"


def test_player_identity_invariance():
    """Verify that changing player identity has zero impact on P3 or final score."""
    row = make_synthetic_row(
        entry_over=10.0, exit_over=14.1, entry_score=110.0, exit_score=165.0,
        team_rr_entry=11.0, team_rr_exit=11.7, efs_entry=205.0, efs_exit=207.0,
    )
    row_player1 = row.copy()
    row_player1["player"] = "Player Alpha"

    row_player2 = row.copy()
    row_player2["player"] = "Player Beta"

    res1 = compute_production_contribution(row_player1, apply_preservation=True)
    res2 = compute_production_contribution(row_player2, apply_preservation=True)

    assert res1["pillar3_state_score"] == res2["pillar3_state_score"]
    assert res1["final_contribution_score"] == res2["final_contribution_score"]


def test_match_outcome_invariance():
    """Verify that match outcome (won_match=True/False) has zero impact on P3 or final score."""
    row = make_synthetic_row(
        entry_over=10.0, exit_over=14.1, entry_score=110.0, exit_score=165.0,
        team_rr_entry=11.0, team_rr_exit=11.7, efs_entry=205.0, efs_exit=207.0,
    )
    row_win = row.copy()
    row_win["won_match"] = True

    row_loss = row.copy()
    row_loss["won_match"] = False

    res_win = compute_production_contribution(row_win, apply_preservation=True)
    res_loss = compute_production_contribution(row_loss, apply_preservation=True)

    assert res_win["pillar3_state_score"] == res_loss["pillar3_state_score"]
    assert res_win["final_contribution_score"] == res_loss["final_contribution_score"]


def test_phase7o_shortened_innings_compatibility():
    """
    Phase 7O early-over stabilization must remain intact for shortened or unmodelled 1st innings.
    Preservation floor does not alter Phase 7O fallback behavior unless gates qualify.
    """
    row_short = pd.Series({
        "innings": 1,
        "entry_over": 1.2,
        "team_rr_entry": 18.0,
        "window_team_rr": 12.0,
        "actual_runs": 20,
        "balls_faced": 10,
        "overs_spent": 1.4,
        "team_runs_added": 28,
        "expected_final_change": np.nan,  # triggers Phase 7O fallback
        "balls_remaining_exit": 20,
        "wickets_remaining_exit": 4,
        "wicket_resource_change": 0,
        "is_dnb": False,
        "dnb": False,
    })
    raw_7o = compute_dampened_p3_raw(row_short, strategy="model_e", apply_preservation=False)
    raw_7q = compute_dampened_p3_raw(row_short, strategy="model_e", apply_preservation=True)
    # Since expected_final_entry is NaN, check_p3_preservation_eligibility returns False, leaving raw identical
    assert pytest.approx(raw_7q, abs=1e-5) == raw_7o


def test_sensitivity_monotonicity():
    """Verify that varying floor_score from 60 to 64 behaves monotonically for a qualifying row."""
    row = make_synthetic_row(
        entry_over=10.0, exit_over=14.1, entry_score=110.0, exit_score=165.0,
        team_rr_entry=11.0, team_rr_exit=11.7, efs_entry=205.0, efs_exit=207.0,
    )
    p3_values = []
    for fl in [60.0, 61.0, 62.0, 63.0, 64.0]:
        raw = compute_dampened_p3_raw(row, apply_preservation=True, floor_score=fl)
        p3_values.append(map_raw_to_p3_score(raw))

    for i in range(len(p3_values) - 1):
        assert p3_values[i + 1] >= p3_values[i], f"Non-monotonic floor behavior: {p3_values}"
        assert pytest.approx(p3_values[i], abs=0.1) == [60.0, 61.0, 62.0, 63.0, 64.0][i]
