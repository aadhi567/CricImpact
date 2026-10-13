"""
Unit and Integration Tests for Phase 7Q: Decoupled P3 State-Preservation Floor.
Cricket Batter Contribution Model.

Verifies:
1. Eligible strong-state preservation (P3 moves into 60-64 region).
2. High existing P3 remains unchanged (no bonus added).
3. Strong-state deterioration not protected (P3 remains low).
4. Anti-free-rider passenger rejection (personal RR < 8.5 gets no floor).
5. Golden duck exclusion (0 off 1 gets no floor).
6. DNB preservation (DNB = None).
7. First innings tempo gate (personal RR >= 8.5 and window RR >= 9.0).
8. Chase RRR gate (personal RR >= RRR_entry and target progress >= 0.20).
9. Delta EFS threshold (delta EFS < -2.5 gets no floor).
10. Minimum involvement gate (balls_faced >= 8 or actual_runs >= 15).
11. P2/P3 mathematical independence (P2 variation has zero impact on P3 floor eligibility).
12. Player identity invariance (player name has zero impact on score).
13. Match outcome invariance (won_match has zero impact on score).
14. Phase 7O compatibility (early-over stabilization unmodified).
15. Governance checksums and backup verification.
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
    map_raw_to_p3_score,
    apply_p3_state_preservation_floor,
    compute_dampened_p3_raw,
    compute_pillar2_batter_performance,
    compute_context_and_leverage,
    compute_adjusted_pillar,
    compute_production_contribution,
    PHASE5B_EMPIRICAL_PARAMS,
)

from src.phase7q_p3_state_preservation import (
    make_synthetic_row,
    evaluate_innings_phase7o_vs_phase7q,
    PRE_MODIFICATION_HASHES,
    verify_governance_and_backups,
)


def test_governance_and_backups_intact():
    """Verify that protected files exist in backup with exact SHA256 hashes."""
    gov = verify_governance_and_backups()
    assert gov["all_passed"], f"Governance failure: {gov['files']}"


def test_eligible_strong_state_preservation():
    """
    Scenario C: Strong inherited state maintained.
    Batter scores 50 off 25 balls, entry at 110/1 in 10 ov (EFS 205), exit at 165/2 in 14.1 ov (EFS 207).
    Under Phase 7O, P3 is compressed near 52.5.
    Under Phase 7Q, P3 must elevate into the approved 60-64 region.
    """
    row_c = make_synthetic_row(
        entry_over=10.0, exit_over=14.1, entry_score=110.0, exit_score=165.0,
        team_rr_entry=11.0, team_rr_exit=11.7, efs_entry=205.0, efs_exit=207.0,
        traj_dev_chg=1.0, wkts_rem_entry=9, wkts_rem_exit=8,
    )
    raw_7o = compute_dampened_p3_raw(row_c, strategy="model_e", apply_preservation=False)
    p3_7o = map_raw_to_p3_score(raw_7o)
    assert 50.0 <= p3_7o <= 55.0, f"Expected Phase 7O P3 ~ 52.5, got {p3_7o}"

    raw_7q = compute_dampened_p3_raw(row_c, strategy="model_e", apply_preservation=True)
    p3_7q = map_raw_to_p3_score(raw_7q)
    assert 60.0 <= p3_7q <= 64.0, f"Expected Phase 7Q P3 in [60.0, 64.0], got {p3_7q}"
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
    raw_sub_7o = compute_dampened_p3_raw(r_sub, apply_preservation=False)
    raw_sub_7q = compute_dampened_p3_raw(r_sub, apply_preservation=True)
    assert pytest.approx(raw_sub_7q, abs=1e-5) == raw_sub_7o

    # 6 balls, 16 runs (actual_runs >= 15) -> qualifies! (e.g. BCJ Cutting Match 1082591)
    df = pd.read_csv("data/processed/batter_match_contributions.csv", low_memory=False)
    r_cutting = df[(df["match_id"] == 1082591) & (df["player"] == "BCJ Cutting")].iloc[0]
    raw_cut_7o = compute_dampened_p3_raw(r_cutting, apply_preservation=False)
    raw_cut_7q = compute_dampened_p3_raw(r_cutting, apply_preservation=True)
    assert raw_cut_7q > raw_cut_7o
    assert map_raw_to_p3_score(raw_cut_7q) > map_raw_to_p3_score(raw_cut_7o)


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
    assert pytest.approx(compute_dampened_p3_raw(r_low_efs, apply_preservation=True), abs=1e-5) == compute_dampened_p3_raw(r_low_efs, apply_preservation=False)

    # 2. delta_efs = -3.0 (< -2.5) -> no preservation floor
    r_collapse = make_synthetic_row(efs_entry=200.0, efs_exit=197.0)
    assert pytest.approx(compute_dampened_p3_raw(r_collapse, apply_preservation=True), abs=1e-5) == compute_dampened_p3_raw(r_collapse, apply_preservation=False)

    # 3. window_team_rr = 8.0 (< 9.0) -> no preservation floor
    r_slow_team = make_synthetic_row(
        entry_over=10.0, exit_over=15.0, entry_score=110.0, exit_score=145.0,  # 35 runs in 5 ov = 7.0 RPO
        efs_entry=200.0, efs_exit=200.0,
    )
    assert pytest.approx(compute_dampened_p3_raw(r_slow_team, apply_preservation=True), abs=1e-5) == compute_dampened_p3_raw(r_slow_team, apply_preservation=False)

    # 4. personal_rr = 7.5 (< 8.5) -> no preservation floor
    r_slow_personal = make_synthetic_row(
        balls_faced=20, actual_runs=25,  # 25 off 20 = 7.5 RPO
        entry_score=110.0, exit_score=165.0, efs_entry=200.0, efs_exit=200.0,
    )
    assert pytest.approx(compute_dampened_p3_raw(r_slow_personal, apply_preservation=True), abs=1e-5) == compute_dampened_p3_raw(r_slow_personal, apply_preservation=False)


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
    assert pytest.approx(compute_dampened_p3_raw(r_high_rrr, apply_preservation=True), abs=1e-5) == compute_dampened_p3_raw(r_high_rrr, apply_preservation=False)

    # 2. Chase blowout (rrr_change = -1.0 < -0.5) -> no preservation floor
    r_blowout = make_synthetic_row(
        innings=2, required_rr_entry=6.0, required_rr_change=-1.0, target_progress_change=0.25,
        actual_runs=30, balls_faced=15,
    )
    assert pytest.approx(compute_dampened_p3_raw(r_blowout, apply_preservation=True), abs=1e-5) == compute_dampened_p3_raw(r_blowout, apply_preservation=False)

    # 3. Insufficient target progress (< 0.20) -> no preservation floor
    r_little_prog = make_synthetic_row(
        innings=2, required_rr_entry=6.0, required_rr_change=0.5, target_progress_change=0.10,
        actual_runs=20, balls_faced=10,
    )
    assert pytest.approx(compute_dampened_p3_raw(r_little_prog, apply_preservation=True), abs=1e-5) == compute_dampened_p3_raw(r_little_prog, apply_preservation=False)

    # 4. Chase Passenger: personal RR below entry RRR -> rejected
    r_chase_pass = make_synthetic_row(
        innings=2, required_rr_entry=7.0, required_rr_change=1.0, target_progress_change=0.30,
        actual_runs=10, balls_faced=15,  # personal RR = 4.0 < 7.0
    )
    assert pytest.approx(compute_dampened_p3_raw(r_chase_pass, apply_preservation=True), abs=1e-5) == compute_dampened_p3_raw(r_chase_pass, apply_preservation=False)


def test_dnb_strict_preservation():
    """Verify DNB appearances strictly remain None."""
    row_dnb = pd.Series({"player": "Test Batter DNB", "is_dnb": True, "balls_faced": np.nan, "actual_runs": np.nan, "innings": 1})
    res = compute_production_contribution(row_dnb)
    assert res["is_dnb"] is True
    assert res["final_contribution_score"] is None
    assert res["pillar3_state_score"] is None
    assert res["pillar2_perf_score"] is None


def test_p2_p3_mathematical_independence():
    """
    CRITICAL MANDATORY TEST:
    P3 preservation eligibility must NOT directly depend on P2 or score_perf.
    - Vary P2/actual_sr while keeping situational and team-state variables constant -> P3 unchanged.
    - Vary team-state variables while keeping individual batting execution constant -> P3 changes appropriately.
    """
    # 1. Fix team state, change batting execution score_perf
    base_row = make_synthetic_row(
        entry_over=10.0, exit_over=14.1, balls_faced=20, actual_runs=35, fours=3, sixes=1,
        entry_score=110.0, exit_score=165.0, efs_entry=205.0, efs_exit=207.0,
    )
    row_perf_low = base_row.copy()
    row_perf_low["score_perf"] = 55.0

    row_perf_high = base_row.copy()
    row_perf_high["score_perf"] = 92.0

    p3_low = compute_dampened_p3_raw(row_perf_low, strategy="model_e", apply_preservation=True)
    p3_high = compute_dampened_p3_raw(row_perf_high, strategy="model_e", apply_preservation=True)
    assert pytest.approx(p3_low, abs=1e-7) == p3_high, "P3 must not change when individual P2 varies!"

    # 2. Fix individual execution, vary team state (weak vs strong entry)
    r_weak_team = base_row.copy()
    r_weak_team["expected_final_entry"] = 135.0
    r_weak_team["expected_final_change"] = 30.0

    r_strong_team = base_row.copy()
    r_strong_team["expected_final_entry"] = 205.0
    r_strong_team["expected_final_change"] = 2.0

    raw_weak = compute_dampened_p3_raw(r_weak_team, strategy="model_e", apply_preservation=True)
    raw_strong = compute_dampened_p3_raw(r_strong_team, strategy="model_e", apply_preservation=True)
    assert raw_weak != raw_strong, "P3 must respond to team-state variables!"


def test_player_identity_invariance():
    """Verify player identity has zero impact on P3 and final contribution score."""
    row_a = make_synthetic_row(entry_score=110.0, exit_score=165.0, efs_entry=205.0, efs_exit=207.0)
    row_a["player"] = "Player Alpha"

    row_b = row_a.copy()
    row_b["player"] = "Player Beta"

    res_a = compute_production_contribution(row_a)
    res_b = compute_production_contribution(row_b)
    assert res_a["pillar3_state_score"] == res_b["pillar3_state_score"]
    assert res_a["final_contribution_score"] == res_b["final_contribution_score"]


def test_match_outcome_invariance():
    """Verify future match winner/result has zero impact on P3 and final contribution score."""
    row = make_synthetic_row(entry_score=110.0, exit_score=165.0, efs_entry=205.0, efs_exit=207.0)

    row_won = row.copy()
    row_won["match_winner"] = "Team Won"
    row_won["won_match"] = True

    row_lost = row.copy()
    row_lost["match_winner"] = "Team Lost"
    row_lost["won_match"] = False

    res_won = compute_production_contribution(row_won)
    res_lost = compute_production_contribution(row_lost)
    assert res_won["pillar3_state_score"] == res_lost["pillar3_state_score"]
    assert res_won["final_contribution_score"] == res_lost["final_contribution_score"]


def test_phase7o_early_over_stabilization_compatibility():
    """Verify that Phase 7O early-over stabilization logic remains 100% active and uncorrupted."""
    df = pd.read_csv("data/processed/batter_match_contributions.csv", low_memory=False)

    # AB de Villiers (Match 1178424): early-over entry at 0.3 overs with explosive tempo
    ab_row = df[(df["match_id"] == 1178424) & (df["player"] == "AB de Villiers")].iloc[0]
    res_ab = compute_production_contribution(ab_row)
    assert res_ab["final_contribution_score"] > 55.0

    # MP Stoinis golden duck (Match 1178424, 0 off 1)
    stoinis_row = df[(df["match_id"] == 1178424) & (df["player"] == "MP Stoinis")].iloc[0]
    res_stoinis = compute_production_contribution(stoinis_row)
    assert res_stoinis["pillar3_state_score"] < 10.0
    assert res_stoinis["final_contribution_score"] < 5.0
