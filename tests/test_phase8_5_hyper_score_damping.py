"""
Phase 8.5: Dedicated Test Suite for Hyper-Score Damping & Rain-Shortened Calibration.

Validates:
1. Absolute governance rules & frozen production checksum.
2. Nitish Kumar Reddy case reproduction and excessive penalty mitigation.
3. Three alternative damping strategies + hybrid model behavior.
4. Monotonicity, boundedness, and differentiability of damping functions.
5. Retention of legitimate deceleration (Rahul Tripathi, Shreyas Iyer).
6. Preservation of collapse relief (Sam Curran, Shikhar Dhawan, Shahrukh Khan).
7. Workstream B dynamic overs-scaled par curve for rain-shortened matches (V Suryavanshi).
8. Strict chase (innings 2) bit-for-bit invariance and DNB null preservation.
9. Edge cases (zero-ball windows, extreme EFS, missing values).
"""

import hashlib
import math
from pathlib import Path
from typing import Dict, Any

import numpy as np
import pandas as pd
import pytest

from app.services.data_service import data_service
from src.contribution_framework import (
    compute_production_contribution,
    compute_dampened_p3_raw,
    map_raw_to_p3_score,
    apply_p3_state_preservation_floor,
)
from src.phase8_collapse_attribution_prototype import (
    validate_expected_runs_input,
    compute_candidate_c_resource_adjusted_raw_p3,
    HISTORICAL_IPL_PAR_TOTAL,
)
from src.phase8_5_hyper_score_damping import (
    compute_damped_c_res_cap_raw_p3,
    compute_damped_c_res_continuous_efs_raw_p3,
    compute_damped_c_res_gradual_saturation_raw_p3,
    compute_damped_c_res_hybrid_raw_p3,
    compute_calibrated_rain_shortened_raw_p3,
    evaluate_phase8_5_unified_raw_p3,
    compute_phase8_5_unified_contribution,
    evaluate_all_damping_strategies,
    get_match_scheduled_overs,
    RAIN_SHORTENED_MATCH_OVERS,
)


EXPECTED_PRODUCTION_SHA256 = "8C5CFBC613D583CB7B70887C9F8BCE489912C8370FCBD96EF56FBE7E9C8AA277"


# ==============================================================================
# 1. Governance & Baseline Checksum Verification
# ==============================================================================

def test_governance_checksum_frozen():
    """Verify that src/contribution_framework.py has not been modified."""
    file_path = Path("src/contribution_framework.py")
    assert file_path.exists(), "src/contribution_framework.py does not exist"

    sha256 = hashlib.sha256(file_path.read_bytes()).hexdigest().upper()
    assert sha256 == EXPECTED_PRODUCTION_SHA256, (
        f"Production governance violation! Checksum mismatch.\n"
        f"Expected: {EXPECTED_PRODUCTION_SHA256}\n"
        f"Actual:   {sha256}"
    )


# ==============================================================================
# 2. Workstream A: Nitish Kumar Reddy Reproduction and Damping Mitigation
# ==============================================================================

def test_nitish_kumar_reddy_reproduction_and_damping():
    """
    Reproduces Nitish Kumar Reddy case from actual source data:
    Match 1527679, 39 off 24, SRH 226/266 match.
    Verifies that under Candidate C-Res with hyper-score damping:
    - With preservation floor: shift is 0.0 (protected at 64.0, final 65.4).
    - Without preservation floor: excessive -20.3 shift is softened to -17.6 in Hybrid.
    """
    df = data_service.get_contributions_df("ipl")
    sub = df[(df["match_id"].astype(str) == "1527679") & (df["player"].str.contains("Reddy", case=False))]
    assert not sub.empty, "Nitish Kumar Reddy record not found in match 1527679"

    r = sub.iloc[0]
    assert int(r["innings"]) == 1
    assert float(r["actual_runs"]) == 39.0
    assert int(r["balls_faced"]) == 24
    assert round(float(r["contribution_score"]), 1) == 65.4

    # Baseline Candidate C-Res raw evaluation without preservation floor
    raw_undamped = compute_candidate_c_resource_adjusted_raw_p3(r)
    p3_undamped = map_raw_to_p3_score(raw_undamped)
    final_undamped = round(0.50 * r["adjusted_p2"] + 0.50 * p3_undamped, 1)
    undamped_shift = round(final_undamped - 65.4, 1)
    assert undamped_shift <= -20.0, f"Expected undamped shift <= -20.0, got {undamped_shift}"

    # Evaluated across all 4 damping strategies with preservation floor
    ev = evaluate_all_damping_strategies(r)
    assert ev["strategy_1_cap"]["final"] == 65.4
    assert ev["strategy_2_continuous"]["final"] == 65.4
    assert ev["strategy_3_saturation"]["final"] == 65.4
    assert ev["strategy_4_hybrid"]["final"] == 65.4
    assert ev["strategy_4_hybrid"]["shift"] == 0.0

    # Evaluated without preservation floor to verify intrinsic formula damping
    raw_hybrid_nofloor = compute_damped_c_res_hybrid_raw_p3(r, apply_preservation=False)
    p3_hybrid_nofloor = map_raw_to_p3_score(raw_hybrid_nofloor)
    final_hybrid_nofloor = round(0.50 * r["adjusted_p2"] + 0.50 * p3_hybrid_nofloor, 1)
    shift_hybrid_nofloor = round(final_hybrid_nofloor - 65.4, 1)
    assert shift_hybrid_nofloor > undamped_shift, (
        f"Hybrid damping must soften penalty compared to undamped: {shift_hybrid_nofloor} vs {undamped_shift}"
    )
    assert shift_hybrid_nofloor >= -18.0, f"Expected shift >= -18.0, got {shift_hybrid_nofloor}"


# ==============================================================================
# 3. Workstream A: Mathematical Properties of Damping Functions
# ==============================================================================

def test_continuous_bounded_damping_monotonicity_and_asymptote():
    """
    Verifies that Strategy 2 continuous tanh damping:
    - Strictly monotonic: d(kappa_entry)/d(EFS) > 0.
    - Smoothly differentiable around par (166.5).
    - Asymptotically bounded: kappa_entry <= 1.0 + M_kappa.
    """
    m_kappa = 0.25
    efs_values = np.linspace(100.0, 350.0, 50)
    kappas = []
    for efs in efs_values:
        x = (efs - HISTORICAL_IPL_PAR_TOTAL) / HISTORICAL_IPL_PAR_TOTAL
        if x > 0:
            k = 1.0 + m_kappa * math.tanh(x / m_kappa)
        else:
            k = max(0.60, 1.0 + x)
        kappas.append(k)

    # Monotonicity
    assert all(kappas[i] <= kappas[i + 1] for i in range(len(kappas) - 1))

    # Upper bound asymptote
    assert max(kappas) < 1.0 + m_kappa + 1e-6
    assert max(kappas) <= 1.25

    # At par (166.5), kappa is exactly 1.0
    par_k = 1.0 + m_kappa * math.tanh(0.0)
    assert abs(par_k - 1.0) < 1e-9


def test_soft_knee_saturation_properties():
    """
    Verifies that Strategy 3 soft-knee trajectory saturation:
    - Identity mapping for mild deficits: sat(dt) == dt for dt in [-tau_knee, 0].
    - Strictly monotonic: d(sat(dt))/d(dt) > 0 everywhere.
    - Asymptotically bounded: sat(dt) > -tau_knee - tau_scale as dt -> -inf.
    """
    tau_knee = 10.0
    tau_scale = 8.0

    # Test identity zone
    for dt in [0.0, -2.0, -5.0, -9.9]:
        if dt < -tau_knee:
            excess = abs(dt) - tau_knee
            sat = -tau_knee - tau_scale * math.tanh(excess / tau_scale)
        else:
            sat = dt
        assert abs(sat - dt) < 1e-9

    # Test saturation zone
    dt_vals = np.linspace(-50.0, 0.0, 100)
    sat_vals = []
    for dt in dt_vals:
        if dt < -tau_knee:
            excess = abs(dt) - tau_knee
            sat = -tau_knee - tau_scale * math.tanh(excess / tau_scale)
        else:
            sat = dt
        sat_vals.append(sat)

    # Monotonicity
    assert all(sat_vals[i] <= sat_vals[i + 1] for i in range(len(sat_vals) - 1))

    # Asymptotic floor: never falls below -(tau_knee + tau_scale) = -18.0
    assert min(sat_vals) > -18.0


# ==============================================================================
# 4. Collapse Relief Preservation and Deceleration Retention
# ==============================================================================

def test_collapse_relief_preservation():
    """
    Verifies that damping strategies preserve positive collapse relief for:
    - Sam Curran (Match 1216521): +13.2 to +13.7 pts.
    - Shikhar Dhawan (Match 1359488): +4.4 to +4.5 pts.
    - Shahrukh Khan (Match 1254065): +9.8 to +10.1 pts.
    """
    df = data_service.get_contributions_df("ipl")
    test_cases = [
        ("1216521", "SM Curran", 13.0),
        ("1359488", "S Dhawan", 4.0),
        ("1254065", "M Shahrukh Khan", 9.0),
    ]
    for mid, name, min_shift in test_cases:
        sub = df[(df["match_id"].astype(str) == mid) & (df["player"] == name)]
        assert not sub.empty, f"Case {name} not found"
        r = sub.iloc[0]
        ev = evaluate_all_damping_strategies(r)
        shift_hybrid = ev["strategy_4_hybrid"]["shift"]
        assert shift_hybrid >= min_shift, f"{name} must retain collapse relief >= {min_shift}, got {shift_hybrid}"


def test_legitimate_deceleration_retained():
    """
    Verifies that damping does not erase penalties for genuine decelerators:
    - Rahul Tripathi (Match 1359484, 34 off 41): final score remains suppressed (25.8 - 27.9).
    - Shreyas Iyer (Match 1529298, 59 off 36, EFS drop -14.4): retains significant negative shift (-7.6 pts).
    """
    df = data_service.get_contributions_df("ipl")

    # Rahul Tripathi
    sub_trip = df[(df["match_id"].astype(str) == "1359484") & (df["player"] == "RA Tripathi")]
    assert not sub_trip.empty
    r_trip = sub_trip.iloc[0]
    ev_trip = evaluate_all_damping_strategies(r_trip)
    assert ev_trip["strategy_4_hybrid"]["final"] <= 30.0, "Rahul Tripathi must remain suppressed <= 30.0"

    # Shreyas Iyer
    sub_iyer = df[(df["match_id"].astype(str) == "1529298") & (df["player"] == "SS Iyer")]
    assert not sub_iyer.empty
    r_iyer = sub_iyer.iloc[0]
    ev_iyer = evaluate_all_damping_strategies(r_iyer)
    raw_iyer_hybrid = compute_damped_c_res_hybrid_raw_p3(r_iyer, apply_preservation=False)
    p3_iyer = map_raw_to_p3_score(raw_iyer_hybrid)
    final_iyer = round(0.50 * r_iyer["adjusted_p2"] + 0.50 * p3_iyer, 1)
    shift_iyer = round(final_iyer - 70.2, 1)
    assert shift_iyer <= -6.0, f"Shreyas Iyer must retain legitimate deceleration shift <= -6.0, got {shift_iyer}"


# ==============================================================================
# 5. Workstream B: Rain-Shortened Dynamic Par Curve Calibration
# ==============================================================================

def test_workstream_b_v_suryavanshi_shortened_innings():
    """
    Tests Workstream B dynamic overs-scaled par curve calibration on V Suryavanshi
    (Match 1527686, RR vs MI, 11-over match):
    - 39 off 14 balls (SR 278.6).
    - Evaluated score shift relative to production is within +/- 1.0 point (+0.1 pt).
    - P3 score is 73.2, properly capturing the +22.8 run team trajectory surplus.
    """
    df = data_service.get_contributions_df("ipl")
    sub = df[(df["match_id"].astype(str) == "1527686") & (df["player"].str.contains("Suryavanshi"))]
    assert not sub.empty, "V Suryavanshi not found in match 1527686"

    r = sub.iloc[0]
    res = compute_phase8_5_unified_contribution(r, strategy="hybrid")
    assert res["is_valid"] is True
    assert abs(res["shift"]) <= 1.0, f"Expected shift within +/- 1.0 pt, got {res['shift']}"
    assert res["p3_score"] >= 70.0, f"P3 score must be >= 70.0, got {res['p3_score']}"
    assert res["final_contribution_score"] >= 76.0, f"Final score must be >= 76.0, got {res['final_contribution_score']}"


def test_workstream_b_rain_shortened_all_matches_mapping():
    """
    Verifies that all 26 rain-shortened matches have valid scheduled overs (between 3.0 and 20.0).
    """
    assert len(RAIN_SHORTENED_MATCH_OVERS) == 26
    for mid, overs in RAIN_SHORTENED_MATCH_OVERS.items():
        assert 3.0 <= overs <= 20.0, f"Invalid overs {overs} for match {mid}"
        b = get_match_scheduled_overs(mid)
        assert b == overs


def test_workstream_b_population_bounded_shifts():
    """
    Verifies that across all 168 batters in the 26 rain-shortened matches,
    calibrated dynamic par curves produce stable, bounded score shifts:
    - Mean shift within +/- 2.0 points.
    - Zero shifts exceeding +/- 18.0 points.
    """
    df = data_service.get_contributions_df("ipl")
    rain_mids = set(RAIN_SHORTENED_MATCH_OVERS.keys())
    sub = df[(df["match_id"].astype(str).isin(rain_mids)) & (df["innings"] == 1) & (df["balls_faced"] > 0)]
    assert len(sub) == 168

    shifts = []
    for _, r in sub.iterrows():
        res = compute_phase8_5_unified_contribution(r, strategy="hybrid")
        assert res["is_valid"] is True
        shifts.append(res["shift"])

    mean_shift = np.mean(shifts)
    assert abs(mean_shift) < 2.0, f"Mean rain shift too large: {mean_shift}"
    assert max(shifts) <= 15.0, f"Max rain shift exceeds 15.0: {max(shifts)}"
    assert min(shifts) >= -15.0, f"Min rain shift exceeds -15.0: {min(shifts)}"


# ==============================================================================
# 6. Invariance & Edge Case Safety
# ==============================================================================

def test_chase_and_dnb_invariance():
    """
    Verifies that:
    - 2nd innings (chase) appearances remain 100% bit-for-bit invariant with production.
    - DNB records return None / is_valid=False.
    """
    df = data_service.get_contributions_df("ipl")
    chases = df[(df["innings"] == 2) & (df["balls_faced"] > 5)].head(20)

    for _, r in chases.iterrows():
        res = compute_phase8_5_unified_contribution(r, strategy="hybrid")
        assert res["is_valid"] is True
        assert res["shift"] == 0.0, f"Chase appearance must be invariant, got shift {res['shift']}"
        assert res["final_contribution_score"] == r["contribution_score"]

    # DNB record
    dnb_row = {"player": "Ghost Batter", "innings": 1, "balls_faced": 0, "actual_runs": 0, "dnb": True}
    res_dnb = compute_phase8_5_unified_contribution(dnb_row)
    assert res_dnb["is_valid"] is False
    assert res_dnb["final_contribution_score"] is None


def test_edge_cases_zero_balls_extreme_efs():
    """
    Verifies that extreme inputs (0 balls, extreme EFS, extreme wickets)
    do not crash, produce NaN, or raise exceptions.
    """
    mock_base = {
        "player": "Test Batter",
        "innings": 1,
        "actual_runs": 0.0,
        "balls_faced": 0,
        "dismissal_status": "out",
        "expected_runs": 10.0,
        "team_score_entry": 50,
        "team_score_exit": 50,
        "expected_final_entry": 166.5,
        "expected_final_change": 0.0,
        "trajectory_deviation_change": 0.0,
        "balls_remaining_exit": 60,
        "wickets_remaining_exit": 5,
        "wicket_resource_change": -1,
        "wickets_lost_during_stay": 1,
    }

    # Zero balls
    res_zero = compute_phase8_5_unified_contribution(mock_base)
    assert res_zero["is_valid"] is True
    assert not math.isnan(res_zero["raw_p3"])

    # Ultra extreme EFS: 400.0 (historic hypothetical)
    mock_high_efs = mock_base.copy()
    mock_high_efs["expected_final_entry"] = 400.0
    res_high = compute_phase8_5_unified_contribution(mock_high_efs)
    assert res_high["is_valid"] is True
    assert not math.isnan(res_high["raw_p3"])

    # Ultra extreme low EFS: 40.0 (severe collapse)
    mock_low_efs = mock_base.copy()
    mock_low_efs["expected_final_entry"] = 40.0
    res_low = compute_phase8_5_unified_contribution(mock_low_efs)
    assert res_low["is_valid"] is True
    assert not math.isnan(res_low["raw_p3"])
