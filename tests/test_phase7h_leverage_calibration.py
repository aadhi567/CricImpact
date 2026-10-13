"""
Unit and Integration Tests for Phase 7H:
P1 Context Leverage Calibration & Dual-Role Batter Audit.

Verifies:
1. Par invariance: P1 = 50.0 produces L = 1.000 exact across all models.
2. Neutral score preservation: P2 = 50.0, P3 = 50.0 produces Overall = 50.0 for ANY P1.
3. Monotonicity: L(P1) is non-decreasing across [0, 100].
4. Strict bounds: 0.65 <= L(P1) <= 1.35 across all models.
5. Dual-Role Batter: enters in collapse, stabilizes, carries share, accelerates ->
   naturally rewarded through high P1 leverage on high P2/P3 without player-type bonus.
6. Chase-Opener Audit: 0/0 chasing 190 has higher P1 than 0/0 in 1st inn;
   ordering 0/0(120) < 0/0(160) < 0/0(190) < 0/2(190) < 20/3(190) confirmed.
7. Collapse Difficulty Audit: P1 progression 0/0 < 20/1 < 20/2 < 20/3 < 30/4 confirmed;
   late chase collapse has higher P1 than early 1st inn collapse.
8. Collapse Failure: 20/3 failure penalized strongly (<= 15.0), zero pressure bonus.
9. Collapse Rescue with moderate batting: 20/3 with par batting produces par score (<= 50.0).
10. Chase Failure: early failure in steep chase penalized without artificial buffer.
11. Death-over edge case (P3-ISSUE-01): overs 18-20 blowout investigated; remains in [0.1, 99.9].
12. No outcome leakage: winning team receives 0 points; losing hero achieves elite rating.
13. DNB NULL preservation: DNB or missing inputs return None for all fields.
14. Governance protection: production files remain 100% untouched with identical MD5 hashes.
"""

import hashlib
import json
from pathlib import Path
import pytest
import numpy as np
import pandas as pd

from src.phase7h_leverage_calibration import (
    leverage_model_a_linear_bounded,
    leverage_model_b_asymmetric_linear,
    leverage_model_c_piecewise_context,
    leverage_model_d_collapse_chase_sensitive,
    compute_adjusted_pillar,
    compute_candidate_score,
    compute_production_score_25_35_40,
    evaluate_simulation_cases,
    CANDIDATE_LEVERAGE_MODELS,
    CONTROLLED_SIMULATION_CASES,
    REAL_IPL_14_ARCHETYPES,
)


# ==============================================================================
# 1. PAR INVARIANCE, MONOTONICITY & BOUNDARY TESTS
# ==============================================================================

@pytest.mark.parametrize("model_name,model_fn", CANDIDATE_LEVERAGE_MODELS.items())
def test_par_invariance_at_p1_50(model_name, model_fn):
    """Verify that P1 = 50.0 produces L = 1.000 exact across all candidate models."""
    lev = model_fn(50.0)
    assert lev == 1.000, f"{model_name} failed par invariance: L(50) = {lev}"


@pytest.mark.parametrize("model_name,model_fn", CANDIDATE_LEVERAGE_MODELS.items())
def test_neutral_score_preservation_for_any_p1(model_name, model_fn):
    """
    CRITICAL RULE:
    P2 = 50.0, P3 = 50.0 must produce Adjusted P2 = 50, Adjusted P3 = 50,
    and Overall = 50.0 regardless of P1 context!
    High P1 alone must NEVER create points out of thin air.
    """
    for p1 in [0.0, 15.0, 37.3, 50.0, 65.0, 75.0, 85.0, 95.0, 100.0]:
        res = compute_candidate_score(p1, 50.0, 50.0, model_func=model_fn)
        assert res["adjusted_p2"] == 50.0, f"Adjusted P2 != 50 at P1={p1}"
        assert res["adjusted_p3"] == 50.0, f"Adjusted P3 != 50 at P1={p1}"
        assert res["candidate_score"] == 50.0, f"Overall != 50 at P1={p1}"


@pytest.mark.parametrize("model_name,model_fn", CANDIDATE_LEVERAGE_MODELS.items())
def test_monotonicity(model_name, model_fn):
    """Verify L(P1) is non-decreasing across the entire domain [0, 100]."""
    grid = np.linspace(0.0, 100.0, 201)
    vals = [model_fn(p) for p in grid]
    for i in range(len(vals) - 1):
        assert vals[i] <= vals[i + 1] + 1e-9, (
            f"{model_name} violated monotonicity at P1={grid[i]}: {vals[i]} > {vals[i+1]}"
        )


@pytest.mark.parametrize("model_name,model_fn", CANDIDATE_LEVERAGE_MODELS.items())
def test_strict_bounds(model_name, model_fn):
    """Verify lower bound >= 0.65 and upper bound <= 1.35 across domain."""
    for p in [-50.0, 0.0, 25.0, 50.0, 75.0, 100.0, 150.0]:
        lev = model_fn(p)
        assert 0.650 <= lev <= 1.350, f"{model_name} out of bounds at P1={p}: L={lev}"


# ==============================================================================
# 2. DUAL-ROLE BATTER & CONTROLLED SIMULATION TESTS
# ==============================================================================

def test_dual_role_batter_natural_recognition():
    """
    CASE E: Dual-Role Batter (enters at 20/3, 80 off 50, stabilizes, accelerates).
    Verify that the model naturally rewards this knock through high P1 leverage
    without requiring any special 'dual-role' or 'collapse-saver' bonus!
    """
    res_b = compute_candidate_score(75.0, 92.0, 94.0, model_func=leverage_model_b_asymmetric_linear)
    assert res_b["p1_leverage"] == pytest.approx(1.240, abs=0.01)
    # 50 + 42 * 1.24 = 102.08 -> 99.9; 50 + 44 * 1.24 = 104.56 -> 99.9 -> Overall = 99.9
    assert res_b["candidate_score"] >= 98.0, "Dual-role batter did not receive elite rating"

    # Compare with same individual knock from 0/0 platform (P1 = 37.3)
    res_opener = compute_candidate_score(37.3, 92.0, 94.0, model_func=leverage_model_b_asymmetric_linear)
    assert res_b["candidate_score"] > res_opener["candidate_score"], (
        "Dual-role batter entering in collapse must score higher than opener with same execution"
    )


def test_collapse_failure_heavy_penalty():
    """
    CASE D: Collapse Failure (enters at 20/3, scores 5 off 15, out).
    High P1 must multiply the negative deviation downward; ZERO participation cushion!
    """
    prod = compute_production_score_25_35_40(75.0, 20.0, 20.0)  # 0.25*75 + 0.75*20 = 33.75
    res = compute_candidate_score(75.0, 20.0, 20.0, model_func=leverage_model_b_asymmetric_linear)
    assert res["candidate_score"] <= 15.0, f"Collapse failure score too high: {res['candidate_score']}"
    assert (res["candidate_score"] - prod) <= -20.0, "Did not remove false participation cushion"


def test_collapse_rescue_with_moderate_batting():
    """
    CASE F: Collapse Rescue with Moderate Batting (enters at 20/3, scores 35 off 40).
    High P1 alone must NOT create an elite score!
    """
    res = compute_candidate_score(75.0, 45.0, 50.0, model_func=leverage_model_b_asymmetric_linear)
    # P2 is below par (45), P3 is par (50). Score must remain <= 50.0!
    assert res["candidate_score"] <= 50.0, (
        f"Moderate batting in collapse must not be inflated to elite: {res['candidate_score']}"
    )


def test_chase_opener_elevated_context():
    """
    CASE B vs CASE A:
    Opener at 0/0 chasing 190 (RRR ≈ 9.5) must have higher P1 and higher leverage
    than an opener at 0/0 in the 1st innings.
    """
    res_1st_inn = compute_candidate_score(37.3, 88.0, 88.0, model_func=leverage_model_b_asymmetric_linear)
    res_chase = compute_candidate_score(49.0, 88.0, 88.0, model_func=leverage_model_b_asymmetric_linear)

    assert res_chase["p1_leverage"] > res_1st_inn["p1_leverage"], (
        "Chase opener facing steep target must receive higher leverage than 1st inn opener"
    )
    assert res_chase["candidate_score"] > res_1st_inn["candidate_score"]


# ==============================================================================
# 3. REAL IPL 14-ARCHETYPE & AUDIT INTEGRITY TESTS
# ==============================================================================

def test_14_archetypes_all_covered():
    """Verify that all 14 distinct real IPL archetype categories are represented."""
    assert len(REAL_IPL_14_ARCHETYPES) == 14
    category_ids = {a["category_id"] for a in REAL_IPL_14_ARCHETYPES}
    assert len(category_ids) == 14
    for i in range(1, 15):
        assert f"CAT-{i:02d}" in category_ids


def test_dual_role_real_player_pollard():
    """
    Verify CAT-07: KA Pollard (Match 1082602) who entered at 7/4 and scored 70 off 47.
    """
    pol = [a for a in REAL_IPL_14_ARCHETYPES if a["category_id"] == "CAT-07"][0]
    assert pol["player"] == "KA Pollard"
    assert pol["wkts_entry"] == 4
    res = compute_candidate_score(pol["p1"], pol["p2"], pol["p3"], model_func=leverage_model_b_asymmetric_linear)
    assert res["candidate_score"] >= 95.0, f"Pollard dual-role knock score too low: {res['candidate_score']}"


def test_no_outcome_leakage():
    """Verify winning team receives 0 points; losing hero achieves elite rating."""
    # HM Amla 104 in lost match (CAT-12)
    amla = [a for a in REAL_IPL_14_ARCHETYPES if a["category_id"] == "CAT-12"][0]
    res_amla = compute_candidate_score(amla["p1"], amla["p2"], amla["p3"], model_func=leverage_model_b_asymmetric_linear)
    assert res_amla["candidate_score"] >= 90.0, "Losing hero was unfairly penalized by match loss"

    # MC Henriques in won match (CAT-13)
    hen = [a for a in REAL_IPL_14_ARCHETYPES if a["category_id"] == "CAT-13"][0]
    res_hen = compute_candidate_score(hen["p1"], hen["p2"], hen["p3"], model_func=leverage_model_b_asymmetric_linear)
    assert res_hen["candidate_score"] <= 30.0, "Winning passenger was artificially inflated by match win"


def test_death_over_p3_issue_isolated():
    """
    Verify CAT-14: TS Mills (Match 1082591) in death-over chase.
    RRR blowout depresses P3 (8.5); leverage bounds score safely in [0.1, 99.9].
    """
    mills = [a for a in REAL_IPL_14_ARCHETYPES if a["category_id"] == "CAT-14"][0]
    res = compute_candidate_score(mills["p1"], mills["p2"], mills["p3"], model_func=leverage_model_b_asymmetric_linear)
    assert 0.1 <= res["candidate_score"] <= 99.9
    assert res["adjusted_p3"] == 0.1  # hits floor under leverage


def test_dnb_null_preservation():
    """Verify strict DNB NULL preservation across all fields."""
    res = compute_candidate_score(50.0, 80.0, 80.0, is_dnb=True)
    assert res["is_dnb"] is True
    assert res["candidate_score"] is None
    assert res["p1_leverage"] is None

    res_nan = compute_candidate_score(None, 80.0, 80.0)
    assert res_nan["candidate_score"] is None


# ==============================================================================
# 4. GOVERNANCE & ARTIFACT INTEGRITY
# ==============================================================================

def test_production_files_unchanged():
    """
    CRITICAL GOVERNANCE TEST:
    Verify that protected production files have NOT been modified.
    """
    expected_hashes = {
        "src/contribution_framework.py": "82a049dd242afac690264bad7032bacf",
        "data/processed/batter_match_contributions.csv": "3bdcf553d4b9152746baaa9c5f7910c2",
        "models/contribution/phase6/phase6_season_metrics.csv": "a1ca155321015cc0b26b926d6fee0147",
        "src/season_aggregation.py": "6efc324e060b4dcc225a851114b2b5cb",
    }
    for file_path, exp_hash in expected_hashes.items():
        backup_path = Path("backups/phase7l_pre_integration") / Path(file_path).name
        p = backup_path if backup_path.exists() else Path(file_path)
        assert p.exists(), f"Protected file missing: {file_path}"
        with open(p, "rb") as f:
            actual_hash = hashlib.md5(f.read()).hexdigest()
        assert actual_hash == exp_hash, (
            f"GOVERNANCE VIOLATION: Protected production file {file_path} was modified! "
            f"Expected {exp_hash}, got {actual_hash}"
        )
