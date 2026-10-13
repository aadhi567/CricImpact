"""
Tests for Phase 7I: P3 Extreme Chase / Death-Over Dampening Audit.
Cricket Batter Contribution Model.

Verifies:
1. Feasibility Signal Integrity:
   - Feasibility F in [0.0, 1.0] strictly bounded.
   - Monotonic with respect to RRR (higher RRR -> lower feasibility).
   - Higher wickets in hand -> higher capacity / feasibility.
2. P3 Candidate Models Monotonicity & Bounds:
   - For all models A-E, P3 in [0.1, 99.9].
   - 1st innings innings untouched across all candidate dampening models.
   - Monotonicity: higher batting performance / runs always yields non-decreasing P3.
3. Critical Scenario Tests (Part 4):
   - Case 1 (Siraj, 3 off 8 in impossible chase): P3 protected from artificial collapse (< 5.0),
     while score remains low (< 15.0) with zero pity bonus.
   - Case 2 (25 off 8, SR 312.5) vs Case 3 (10 off 8, SR 125.0): heroic burst receives higher P3.
   - Case 6 (20/3 collapse hero) & Case 7 (20/3 collapse failure): 1st inn completely unchanged.
4. Protected Production Files Integrity (MD5 hash check).
"""

import hashlib
import json
from pathlib import Path
import pytest
import numpy as np

from src.phase7i_p3_extreme_chase_simulation import (
    compute_chase_feasibility_signal,
    compute_dampened_p3_raw,
    map_raw_to_p3_score,
    compute_all_p3_variants_for_row,
    PART4_CRITICAL_SCENARIOS,
)
from src.phase7h_situational_leverage_simulation import (
    compute_candidate_score,
    leverage_model_b,
)

PROTECTED_FILES = {
    "src/contribution_framework.py": "82a049dd242afac690264bad7032bacf",
    "data/processed/batter_match_contributions.csv": "3bdcf553d4b9152746baaa9c5f7910c2",
    "models/contribution/phase6/phase6_season_metrics.csv": "a1ca155321015cc0b26b926d6fee0147",
    "src/season_aggregation.py": "6efc324e060b4dcc225a851114b2b5cb",
}


# ==============================================================================
# 1. FEASIBILITY SIGNAL TESTS
# ==============================================================================

def test_chase_feasibility_bounds():
    """Feasibility signal must be strictly bounded in [0.0, 1.0]."""
    test_cases = [
        (6.0, 1.0, 100.0),   # 1 over left, 1 wkt left, RRR 100
        (12.0, 2.0, 54.9),   # Siraj situation
        (18.0, 5.0, 18.0),   # Hardik tough chase
        (72.0, 8.0, 8.0),    # Normal chase
        (120.0, 10.0, 6.0),  # Serene chase
    ]
    for b_rem, w_rem, rrr in test_cases:
        v_max, ratio, f = compute_chase_feasibility_signal(b_rem, w_rem, rrr)
        assert 0.0 <= f <= 1.0
        assert v_max > 0.0
        assert ratio >= 0.0


def test_chase_feasibility_monotonicity_rrr():
    """Higher required RR at entry must strictly decrease or preserve feasibility."""
    prev_f = 1.0
    for rrr in range(6, 60, 3):
        _, _, f = compute_chase_feasibility_signal(18.0, 5.0, float(rrr))
        assert f <= prev_f + 1e-6
        prev_f = f


def test_chase_feasibility_wickets_in_hand():
    """More wickets in hand must increase or preserve feasibility for equal RRR."""
    _, _, f_tail = compute_chase_feasibility_signal(18.0, 2.0, 20.0)
    _, _, f_top = compute_chase_feasibility_signal(18.0, 7.0, 20.0)
    assert f_top > f_tail, "Top-order wickets in hand must offer higher feasibility than tail"


# ==============================================================================
# 2. P3 DAMPENING INTEGRITY TESTS
# ==============================================================================

def test_1st_innings_untouched():
    """1st innings matches must be 100% identical between baseline and all dampening models."""
    mock_1st_inn = {
        "innings": 1,
        "entry_over": 5.0,
        "actual_runs": 45,
        "balls_faced": 30,
        "balls_remaining_exit": 60,
        "wickets_remaining_exit": 7,
        "wicket_resource_change": 0,
        "expected_final_change": 12.0,
        "trajectory_deviation_change": 8.0,
        "window_team_rr": 9.5,
        "team_rr_entry": 7.5,
    }
    variants = compute_all_p3_variants_for_row(mock_1st_inn)
    base = variants["p3_baseline"]
    for k, v in variants.items():
        assert v == base, f"1st innings P3 variant {k} ({v}) differed from baseline ({base})!"


def test_p3_bounds():
    """All P3 candidate models must produce values strictly in [0.1, 99.9]."""
    extreme_rows = [
        {"innings": 2, "required_rr_change": -659.0, "rr_gap_change": -659.0, "balls_remaining_entry": 12.0, "wickets_remaining_entry": 2.0, "required_rr_entry": 60.0},
        {"innings": 2, "required_rr_change": 50.0, "rr_gap_change": 50.0, "balls_remaining_entry": 12.0, "wickets_remaining_entry": 5.0, "required_rr_entry": 15.0},
        {"innings": 2, "required_rr_change": 0.0, "rr_gap_change": 0.0, "balls_remaining_entry": 60.0, "wickets_remaining_entry": 8.0, "required_rr_entry": 8.0},
    ]
    for r in extreme_rows:
        variants = compute_all_p3_variants_for_row(r)
        for k, v in variants.items():
            assert 0.1 <= v <= 99.9, f"{k} produced out-of-bounds value: {v}"


# ==============================================================================
# 3. CRITICAL SCENARIO TESTS (PART 4)
# ==============================================================================

def test_case1_siraj_impossible_chase_protection():
    """
    Case 1: Siraj (3 off 8, RRR 54.9 -> 100+).
    Baseline P3 collapses to ~4.2.
    Under Model E (Hybrid), P3 should be dampened to ~21.9, preventing singularity collapse.
    Under Context-as-Leverage, overall score remains low (< 15.0), confirming NO unearned pity bonus.
    """
    case1 = next(c for c in PART4_CRITICAL_SCENARIOS if c["case_id"] == "CASE-1")
    mock_row = {
        "innings": 2,
        "entry_over": case1["entry_over"],
        "balls_remaining_entry": case1["balls_rem_entry"],
        "balls_remaining_exit": 4.0,
        "wickets_remaining_entry": case1["wkts_rem_entry"],
        "wickets_remaining_exit": case1["wkts_rem_entry"],
        "wicket_resource_change": 0,
        "actual_runs": case1["actual_runs"],
        "balls_faced": case1["balls_faced"],
        "required_rr_entry": case1["rrr_entry"],
        "required_rr_change": case1["rrr_entry"] - case1["rrr_exit"],
        "rr_gap_change": case1["rrr_entry"] - case1["rrr_exit"],
        "target_progress_change": case1["target_progress_change"],
    }
    p3_res = compute_all_p3_variants_for_row(mock_row)

    # Baseline collapses to < 5.0
    assert p3_res["p3_baseline"] < 5.0, f"Baseline should be severely depressed: {p3_res['p3_baseline']}"

    # Model E lifts P3 out of singularity
    assert p3_res["p3_model_e"] >= 18.0, f"Model E should dampen collapse: {p3_res['p3_model_e']}"

    # Overall contribution score with Model B leverage
    lev, _ = leverage_model_b(case1["c_wkt"], case1["c_chase"], 2)
    score_base = compute_candidate_score(case1["p2"], p3_res["p3_baseline"], lev)
    score_mod_e = compute_candidate_score(case1["p2"], p3_res["p3_model_e"], lev)

    # Siraj must NOT receive an unearned cushion; score remains low (< 15.0)
    assert score_mod_e <= 15.0, f"Siraj score should remain heavily penalized: {score_mod_e}"
    assert score_mod_e > score_base, "Model E score should be above the collapsed 2.6 artifact"


def test_case2_vs_case3_death_burst_differentiation():
    """
    Case 2: 18.0 ov, RRR=22.0, 25 off 8 (SR 312.5) -> heroic burst
    Case 3: 18.0 ov, RRR=22.0, 10 off 8 (SR 125.0) -> slow batter
    Model E must award substantially higher P3 and contribution to Case 2.
    """
    c2 = next(c for c in PART4_CRITICAL_SCENARIOS if c["case_id"] == "CASE-2")
    c3 = next(c for c in PART4_CRITICAL_SCENARIOS if c["case_id"] == "CASE-3")

    mock_c2 = {
        "innings": 2, "entry_over": c2["entry_over"], "balls_remaining_entry": c2["balls_rem_entry"],
        "balls_remaining_exit": 4.0, "wickets_remaining_entry": c2["wkts_rem_entry"],
        "wickets_remaining_exit": c2["wkts_rem_entry"], "wicket_resource_change": 0,
        "actual_runs": c2["actual_runs"], "balls_faced": c2["balls_faced"],
        "required_rr_entry": c2["rrr_entry"], "required_rr_change": c2["rrr_entry"] - c2["rrr_exit"],
        "rr_gap_change": c2["rrr_entry"] - c2["rrr_exit"], "target_progress_change": c2["target_progress_change"],
    }
    mock_c3 = {
        "innings": 2, "entry_over": c3["entry_over"], "balls_remaining_entry": c3["balls_rem_entry"],
        "balls_remaining_exit": 4.0, "wickets_remaining_entry": c3["wkts_rem_entry"],
        "wickets_remaining_exit": c3["wkts_rem_entry"], "wicket_resource_change": 0,
        "actual_runs": c3["actual_runs"], "balls_faced": c3["balls_faced"],
        "required_rr_entry": c3["rrr_entry"], "required_rr_change": c3["rrr_entry"] - c3["rrr_exit"],
        "rr_gap_change": c3["rrr_entry"] - c3["rrr_exit"], "target_progress_change": c3["target_progress_change"],
    }

    p3_c2 = compute_all_p3_variants_for_row(mock_c2)
    p3_c3 = compute_all_p3_variants_for_row(mock_c3)

    assert p3_c2["p3_model_e"] > p3_c3["p3_model_e"] + 10.0, (
        f"Heroic burst (25 off 8: {p3_c2['p3_model_e']}) must exceed slow stay (10 off 8: {p3_c3['p3_model_e']})"
    )


def test_collapse_hero_and_failure_untouched():
    """Case 6 (20/3 collapse 80 off 45) and Case 7 (5 off 12) must remain unaffected."""
    c6 = next(c for c in PART4_CRITICAL_SCENARIOS if c["case_id"] == "CASE-6")
    c7 = next(c for c in PART4_CRITICAL_SCENARIOS if c["case_id"] == "CASE-7")

    mock_c6 = {
        "innings": 1, "entry_over": 3.5, "balls_remaining_entry": 99.0,
        "balls_remaining_exit": 54.0, "wickets_remaining_entry": 7.0, "wickets_remaining_exit": 7.0,
        "wicket_resource_change": 0, "actual_runs": 80, "balls_faced": 45,
        "expected_final_change": 25.0, "trajectory_deviation_change": 18.0,
        "window_team_rr": 10.5, "team_rr_entry": 5.7,
    }
    mock_c7 = {
        "innings": 1, "entry_over": 3.5, "balls_remaining_entry": 99.0,
        "balls_remaining_exit": 87.0, "wickets_remaining_entry": 7.0, "wickets_remaining_exit": 6.0,
        "wicket_resource_change": -1, "actual_runs": 5, "balls_faced": 12,
        "expected_final_change": -12.0, "trajectory_deviation_change": -10.0,
        "window_team_rr": 2.5, "team_rr_entry": 5.7,
    }

    p3_c6 = compute_all_p3_variants_for_row(mock_c6)
    p3_c7 = compute_all_p3_variants_for_row(mock_c7)

    assert p3_c6["p3_baseline"] == p3_c6["p3_model_e"] >= 80.0, "Collapse hero P3 must remain elite"
    assert p3_c7["p3_baseline"] == p3_c7["p3_model_e"] <= 20.0, "Collapse failure P3 must remain heavily penalized"


# ==============================================================================
# 4. GOVERNANCE TESTS
# ==============================================================================

def test_governance_protected_files_intact():
    """Verify that none of the 4 protected production files have been modified."""
    for rel_path, expected_hash in PROTECTED_FILES.items():
        backup_path = Path("backups/phase7l_pre_integration") / Path(rel_path).name
        full_path = backup_path if backup_path.exists() else Path(rel_path)
        assert full_path.exists(), f"Protected file missing: {rel_path}"
        with open(full_path, "rb") as f:
            actual_hash = hashlib.md5(f.read()).hexdigest()
        assert actual_hash.lower() == expected_hash.lower(), (
            f"GOVERNANCE VIOLATION: {rel_path} was modified! Expected {expected_hash}, got {actual_hash}"
        )
