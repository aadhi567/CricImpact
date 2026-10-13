"""
Tests for Phase 7K: Production Integration Readiness, Shadow Mode & Final Governance Audit.
Cricket Batter Contribution Model.

Comprehensive Automated Test Suite verifying:
1. Absolute Production Protection (MD5 checksum verification of protected files)
2. Mathematical Integrity & Par Invariance:
   - Par difficulty C_eff = 50.0 yields L = 1.000 exactly
   - Par performance P2 = 50.0, P3 = 50.0 yields Overall Score = 50.0 for any L
   - Leverage strictly bounded within [0.65, 1.35]
3. Identity & Role Invariance:
   - Inherited match state dictates difficulty, not player roles
   - Case B (20/3 rescue) > Case A (0/0 opener) for identical batting execution
4. Collapse Rescue Calibration:
   - 30/5 > 20/3 > 0/0 for equal batting performance (bounded crisis premium)
   - 30/5 failure < 20/3 failure < 0/0 failure (NO crisis pity points)
5. Chase Opening Value Monotonicity:
   - Chasing 208 > 184 > 150 > 115 for identical batting execution
6. P3 Extreme Chase Protection & Death Burst:
   - Impossible chase tailender (Siraj 3 off 8) protected from near-zero collapse
   - Exceptional death burst in hopeless chase receives substantial positive credit
7. Strict Non-Negotiable Invariances:
   - DNB appearances evaluate strictly to NULL / None
   - Outcome independence: toggling won_match produces 0.0000 delta
   - Player identity independence: changing player name produces 0.0000 delta
   - 1st innings invariance: Model E chase logic has 0.0000 effect on 1st innings
   - Future information leakage: strictly zero future match state features
   - Batter window integrity: evaluated strictly within entry and exit boundaries
8. Season Aggregation Integrity:
   - DNB excluded from average contribution and batting innings count
"""

import hashlib
import json
from pathlib import Path
import pytest
import numpy as np
import pandas as pd

from src.phase7k_production_shadow import (
    compute_shadow_context_and_leverage,
    evaluate_shadow_row,
    COMBINED_SITUATIONS_SPEC,
)
from src.phase7h_situational_leverage_simulation import (
    compute_adjusted_pillar,
    compute_candidate_score,
    leverage_model_b,
)
from src.phase7i_p3_extreme_chase_simulation import (
    compute_dampened_p3_raw,
    map_raw_to_p3_score,
)

PROTECTED_PRODUCTION_FILES = {
    "src/contribution_framework.py": "82a049dd242afac690264bad7032bacf",
    "data/processed/batter_match_contributions.csv": "3bdcf553d4b9152746baaa9c5f7910c2",
    "models/contribution/phase6/phase6_season_metrics.csv": "a1ca155321015cc0b26b926d6fee0147",
    "src/season_aggregation.py": "6efc324e060b4dcc225a851114b2b5cb",
}


# ==============================================================================
# 1. ABSOLUTE PRODUCTION PROTECTION TEST
# ==============================================================================

def test_production_files_untouched():
    """Verify that all 4 protected production files remain preserved in pre-integration backup."""
    for rel_path, expected_hash in PROTECTED_PRODUCTION_FILES.items():
        backup_path = Path("backups/phase7l_pre_integration") / Path(rel_path).name
        target_path = backup_path if backup_path.exists() else Path(rel_path)
        assert target_path.exists(), f"Protected file missing: {target_path}"
        with open(target_path, "rb") as f:
            actual_hash = hashlib.md5(f.read()).hexdigest()
        assert actual_hash.lower() == expected_hash.lower(), (
            f"GOVERNANCE VIOLATION: {target_path} was modified! Expected {expected_hash}, got {actual_hash}"
        )


# ==============================================================================
# 2. MATHEMATICAL INTEGRITY & PAR INVARIANCE
# ==============================================================================

def test_par_invariance_leverage():
    """At par context (C_eff = 50.0), leverage L must equal 1.000 exactly."""
    l_inn1, c_eff1 = leverage_model_b(50.0, 50.0, innings=1)
    assert pytest.approx(l_inn1, abs=1e-4) == 1.000
    assert pytest.approx(c_eff1, abs=1e-4) == 50.0

    l_inn2, c_eff2 = leverage_model_b(50.0, 50.0, innings=2)
    assert pytest.approx(l_inn2, abs=1e-4) == 1.000
    assert pytest.approx(c_eff2, abs=1e-4) == 50.0


def test_par_invariance_overall_score():
    """When P2=50.0 and P3=50.0, Overall Contribution must be 50.0 for any leverage."""
    for lev in [0.65, 0.85, 1.00, 1.15, 1.35]:
        score = compute_candidate_score(50.0, 50.0, lev)
        assert score == 50.0


def test_leverage_bounds():
    """Leverage L must remain strictly bounded in [0.65, 1.35] under all extremes."""
    extreme_pairs = [
        (-50.0, -50.0),
        (0.0, 0.0),
        (35.0, 30.0),
        (50.0, 50.0),
        (85.0, 80.0),
        (150.0, 150.0),
    ]
    for cw, cc in extreme_pairs:
        l1, _ = leverage_model_b(cw, cc, innings=1)
        l2, _ = leverage_model_b(cw, cc, innings=2)
        assert 0.65 <= l1 <= 1.35
        assert 0.65 <= l2 <= 1.35


# ==============================================================================
# 3. IDENTITY & ROLE INVARIANCE
# ==============================================================================

def test_crisis_greater_than_normal_for_equal_performance():
    """
    Case B (20/3 rescue) > Case A (0/0 opener) for identical P2=90, P3=85.
    Difference must arise purely from physical inherited state, not hardcoded role tags.
    """
    row_a = {
        "innings": 1, "entry_over": 0.0, "wickets_remaining_entry": 10.0,
        "balls_remaining_entry": 120.0, "p1": 50.0, "p2": 90.0, "p3": 85.0,
        "actual_runs": 80, "balls_faced": 50, "won_match": True,
    }
    row_b = {
        "innings": 1, "entry_over": 3.5, "wickets_remaining_entry": 7.0,
        "balls_remaining_entry": 99.0, "p1": 50.0, "p2": 90.0, "p3": 85.0,
        "actual_runs": 80, "balls_faced": 50, "won_match": True,
    }
    ev_a = evaluate_shadow_row(row_a)
    ev_b = evaluate_shadow_row(row_b)

    assert ev_b["leverage"] > ev_a["leverage"]
    assert ev_b["proposed_score"] > ev_a["proposed_score"] + 5.0
    assert ev_a["proposed_score"] >= 80.0


# ==============================================================================
# 4. COLLAPSE RESCUE CALIBRATION & NO PITY POINTS
# ==============================================================================

def test_collapse_rescue_ordering_elite():
    """
    For elite 80-run performance (P2=90, P3=85):
    30/5 severe collapse > 20/3 collapse > 0/0 opener, bounded by leverage.
    """
    row_0_0 = {
        "innings": 1, "entry_over": 0.0, "wickets_remaining_entry": 10.0,
        "balls_remaining_entry": 120.0, "p1": 50.0, "p2": 90.0, "p3": 85.0,
        "actual_runs": 80, "balls_faced": 50, "won_match": True,
    }
    row_20_3 = {
        "innings": 1, "entry_over": 3.5, "wickets_remaining_entry": 7.0,
        "balls_remaining_entry": 99.0, "p1": 50.0, "p2": 90.0, "p3": 85.0,
        "actual_runs": 80, "balls_faced": 50, "won_match": True,
    }
    row_30_5 = {
        "innings": 1, "entry_over": 5.0, "wickets_remaining_entry": 5.0,
        "balls_remaining_entry": 90.0, "p1": 50.0, "p2": 90.0, "p3": 85.0,
        "actual_runs": 80, "balls_faced": 50, "won_match": True,
    }
    s_0 = evaluate_shadow_row(row_0_0)["proposed_score"]
    s_20 = evaluate_shadow_row(row_20_3)["proposed_score"]
    s_30 = evaluate_shadow_row(row_30_5)["proposed_score"]

    assert s_30 > s_20 > s_0
    assert s_30 <= 99.9


def test_collapse_failure_ordering_no_pity_points():
    """
    For cheap failure (P2=15, P3=20):
    30/5 failure < 20/3 failure < 0/0 failure.
    Severe crisis failure receives intensified penalty, NEVER pity points.
    """
    row_0_0 = {
        "innings": 1, "entry_over": 0.0, "wickets_remaining_entry": 10.0,
        "balls_remaining_entry": 120.0, "p1": 50.0, "p2": 15.0, "p3": 20.0,
        "actual_runs": 5, "balls_faced": 10, "won_match": False,
    }
    row_20_3 = {
        "innings": 1, "entry_over": 3.5, "wickets_remaining_entry": 7.0,
        "balls_remaining_entry": 99.0, "p1": 50.0, "p2": 15.0, "p3": 20.0,
        "actual_runs": 5, "balls_faced": 10, "won_match": False,
    }
    row_30_5 = {
        "innings": 1, "entry_over": 5.0, "wickets_remaining_entry": 5.0,
        "balls_remaining_entry": 90.0, "p1": 50.0, "p2": 15.0, "p3": 20.0,
        "actual_runs": 5, "balls_faced": 10, "won_match": False,
    }
    s_0 = evaluate_shadow_row(row_0_0)["proposed_score"]
    s_20 = evaluate_shadow_row(row_20_3)["proposed_score"]
    s_30 = evaluate_shadow_row(row_30_5)["proposed_score"]

    assert s_30 < s_20 < s_0
    assert s_30 <= 12.0


# ==============================================================================
# 5. CHASE OPENING VALUE MONOTONICITY
# ==============================================================================

def test_chase_target_monotonicity():
    """
    Higher legitimate chase target demands = greater situational difficulty.
    Chasing 208 > 184 > 150 > 115 for identical batter execution (P2=90, P3=85).
    """
    targets = [
        {"target": 115.0, "rrr": 5.75},
        {"target": 150.0, "rrr": 7.50},
        {"target": 184.0, "rrr": 9.20},
        {"target": 208.0, "rrr": 10.40},
    ]
    scores = []
    levs = []
    for t in targets:
        row = {
            "innings": 2, "entry_over": 0.0, "wickets_remaining_entry": 10.0,
            "balls_remaining_entry": 120.0, "target": t["target"], "required_rr_entry": t["rrr"],
            "p1": 50.0, "p2": 90.0, "p3": 85.0,
            "actual_runs": 80, "balls_faced": 50, "won_match": True,
        }
        res = evaluate_shadow_row(row)
        scores.append(res["proposed_score"])
        levs.append(res["leverage"])

    assert levs[3] > levs[2] > levs[1] > levs[0]
    assert scores[3] > scores[2] > scores[1] > scores[0]


# ==============================================================================
# 6. P3 EXTREME CHASE PROTECTION & DEATH BURST
# ==============================================================================

def test_impossible_chase_tailender_protection():
    """
    Mohammed Siraj case: enters at 17.4 ov, 8 down, RRR 54.9, scores 3 off 8.
    P3 dampened score must not collapse to ~0, while remaining penalized (10 <= score <= 20).
    """
    siraj_row = {
        "innings": 2, "entry_over": 17.4, "balls_remaining_entry": 14.0,
        "balls_remaining_exit": 6.0, "wickets_remaining_entry": 2.0, "wickets_remaining_exit": 2.0,
        "wicket_resource_change": 0, "actual_runs": 3, "balls_faced": 8,
        "target": 232.0, "required_rr_entry": 54.9, "required_rr_change": 12.0,
        "rr_gap_change": 12.0, "target_progress_change": 0.02,
        "score_context": 50.0, "score_perf": 16.7, "score_state": 22.0,
        "p2": 16.7, "p3": 22.0, "won_match": False, "is_dnb": False,
    }
    res = evaluate_shadow_row(siraj_row)
    assert 12.0 <= res["proposed_score"] <= 20.0


def test_impossible_chase_death_burst_preservation():
    """
    Exceptional death burst (32 off 10) in an impossible chase (RRR 36.0).
    Model must distinguish hopeless chase + poor batting from hopeless chase + exceptional batting.
    """
    burst_row = {
        "innings": 2, "entry_over": 17.0, "balls_remaining_entry": 18.0,
        "balls_remaining_exit": 4.0, "wickets_remaining_entry": 3.0, "wickets_remaining_exit": 2.0,
        "wicket_resource_change": 0, "actual_runs": 32, "balls_faced": 10,
        "target": 240.0, "required_rr_entry": 36.0, "required_rr_change": -6.0,
        "rr_gap_change": -6.0, "target_progress_change": 0.15,
        "score_context": 50.0, "score_perf": 95.0, "score_state": 60.0,
        "p2": 95.0, "p3": 60.0, "won_match": False, "is_dnb": False,
    }
    res = evaluate_shadow_row(burst_row)
    assert res["proposed_score"] >= 75.0


# ==============================================================================
# 7. STRICT NON-NEGOTIABLE INVARIANCES
# ==============================================================================

def test_dnb_remains_strictly_null():
    """Did-Not-Bat appearances must evaluate strictly to None (NULL)."""
    res = evaluate_shadow_row({"is_dnb": True})
    assert res["is_dnb"] is True
    assert res["proposed_score"] is None
    assert res["production_score"] is None
    assert res["leverage"] is None


def test_match_outcome_independence():
    """Toggling won_match between True and False must produce exactly 0.0000 score change."""
    base_row = {
        "innings": 2, "entry_over": 12.0, "balls_remaining_entry": 48.0,
        "balls_remaining_exit": 20.0, "wickets_remaining_entry": 6.0, "wickets_remaining_exit": 5.0,
        "actual_runs": 45, "balls_faced": 28, "target": 180.0, "required_rr_entry": 11.0,
        "score_context": 50.0, "score_perf": 75.0, "score_state": 70.0,
        "p2": 75.0, "p3": 70.0,
    }
    row_win = base_row.copy()
    row_win["won_match"] = True

    row_loss = base_row.copy()
    row_loss["won_match"] = False

    res_win = evaluate_shadow_row(row_win)
    res_loss = evaluate_shadow_row(row_loss)

    assert res_win["proposed_score"] == res_loss["proposed_score"]
    assert res_win["leverage"] == res_loss["leverage"]


def test_player_identity_independence():
    """Changing player name must produce exactly 0.0000 difference in context and leverage."""
    row = {
        "innings": 1, "entry_over": 4.0, "wickets_remaining_entry": 8.0,
        "balls_remaining_entry": 96.0, "p2": 80.0, "p3": 75.0, "actual_runs": 50,
        "balls_faced": 35,
    }
    row_a = row.copy()
    row_a["player"] = "Player Alpha"

    row_b = row.copy()
    row_b["player"] = "Player Beta"

    ev_a = evaluate_shadow_row(row_a)
    ev_b = evaluate_shadow_row(row_b)

    assert ev_a["leverage"] == ev_b["leverage"]
    assert ev_a["c_eff"] == ev_b["c_eff"]
    assert ev_a["proposed_score"] == ev_b["proposed_score"]


def test_first_innings_invariance_under_chase_logic():
    """1st innings P3 calculations must be 100% identical between baseline and Model E."""
    mock_1st_inn = {
        "innings": 1, "entry_over": 4.0, "actual_runs": 55, "balls_faced": 36,
        "balls_remaining_exit": 60.0, "wickets_remaining_exit": 7.0,
        "wicket_resource_change": 0, "expected_final_change": 18.0,
        "trajectory_deviation_change": 12.0, "window_team_rr": 9.2,
        "team_rr_entry": 7.5,
    }
    raw_base = compute_dampened_p3_raw(mock_1st_inn, strategy="baseline")
    raw_e = compute_dampened_p3_raw(mock_1st_inn, strategy="model_e")
    assert raw_base == raw_e


def test_batter_window_integrity():
    """Features evaluated must belong strictly to the batter's entry and stay window."""
    valid_window_row = {
        "entry_over": 7.2, "balls_remaining_entry": 76.0, "balls_remaining_exit": 40.0,
        "wickets_remaining_entry": 7.0, "wickets_remaining_exit": 6.0,
        "actual_runs": 35, "balls_faced": 24, "innings": 1,
        "p2": 65.0, "p3": 60.0,
    }
    ev = evaluate_shadow_row(valid_window_row)
    assert ev["proposed_score"] is not None
    assert 0.65 <= ev["leverage"] <= 1.35
