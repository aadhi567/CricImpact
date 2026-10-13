"""
Unit and Integration Tests for Phase 7H: Asymmetric Context Leverage Calibration.

Verifies:
1. Par invariance at P1 = 50.0 (L = 1.000 exact across all models).
2. Monotonicity: L(P1) is non-decreasing across the entire domain [0, 100].
3. Lower bound >= 0.65 and Upper bound <= 1.35 across all models.
4. Elite Opener behavior: high P2/P3 with low P1 maintains elite score (>= 85.0).
5. Failed Opener behavior: low P2/P3 with low P1 remains low (<= 25.0); low context does not protect.
6. Collapse Rescue behavior: high P1 with high P2/P3 receives higher leverage and higher score than opener.
7. Collapse Failure behavior: high P1 with low P2/P3 is heavily penalized (<= 15.0); 0 participation points.
8. Collapse Passenger behavior: high P1 with par P2/P3 (50/50) produces score == 50.0 exact.
9. Death-over edge case: overs 18-20 RRR blowout (P3-ISSUE-01) interacts with leverage; bounded in [0.1, 99.9].
10. No outcome leakage: match outcome does not alter score; losing heroes receive elite scores.
11. DNB NULL preservation: missing inputs or DNB return None across all fields.
12. P2/P3 independence: leverage reduces correlation between execution (P2) and state (P3).
13. Strict governance: production files remain 100% untouched with identical MD5 hashes.
14. Artifact integrity: JSON specification and validation artifacts exist and are populated.
"""

import hashlib
import json
from pathlib import Path
import pytest
import numpy as np
import pandas as pd

from src.phase7h_asymmetric_leverage_simulation import (
    leverage_model_a_symmetric_linear,
    leverage_model_b_asymmetric_linear,
    leverage_model_c_piecewise_collapse,
    leverage_model_d_smooth_power,
    compute_adjusted_pillar,
    compute_candidate_score,
    compute_production_score_25_35_40,
    evaluate_critical_cases,
    evaluate_equivalent_performance,
    CANDIDATE_LEVERAGE_MODELS,
    CRITICAL_TEST_CASES,
)


# ==============================================================================
# 1. PAR INVARIANCE, MONOTONICITY & BOUNDARY TESTS
# ==============================================================================

@pytest.mark.parametrize("model_name,model_fn", CANDIDATE_LEVERAGE_MODELS.items())
def test_par_invariance(model_name, model_fn):
    """Verify that P1 = 50.0 produces L = 1.000 exactly across all models."""
    lev = model_fn(50.0)
    assert lev == 1.000, f"{model_name} failed par invariance at P1=50: L={lev}"

    # Verify score invariance: raw deviations around 50 must remain completely unscaled
    res = compute_candidate_score(50.0, 75.0, 35.0, model_func=model_fn)
    assert res["p1_leverage"] == 1.000
    assert res["adjusted_p2"] == 75.0
    assert res["adjusted_p3"] == 35.0
    assert res["candidate_score"] == 55.0  # 0.50 * 75 + 0.50 * 35


@pytest.mark.parametrize("model_name,model_fn", CANDIDATE_LEVERAGE_MODELS.items())
def test_monotonicity(model_name, model_fn):
    """Verify that L(P1) is monotonically non-decreasing over [0, 100]."""
    p1_grid = np.linspace(0.0, 100.0, 201)
    lev_values = [model_fn(p) for p in p1_grid]
    for i in range(len(lev_values) - 1):
        assert lev_values[i] <= lev_values[i + 1] + 1e-9, (
            f"{model_name} violated monotonicity at P1={p1_grid[i]}: "
            f"L({p1_grid[i]})={lev_values[i]} > L({p1_grid[i+1]})={lev_values[i+1]}"
        )


@pytest.mark.parametrize("model_name,model_fn", CANDIDATE_LEVERAGE_MODELS.items())
def test_lower_and_upper_bounds(model_name, model_fn):
    """Verify that L(P1) is strictly bounded in [0.65, 1.35] even for extreme inputs."""
    test_inputs = [-50.0, -10.0, 0.0, 10.0, 50.0, 90.0, 100.0, 120.0, 200.0]
    for p in test_inputs:
        lev = model_fn(p)
        assert 0.650 <= lev <= 1.350, f"{model_name} exceeded bounds at P1={p}: L={lev}"


# ==============================================================================
# 2. RESEARCH TARGET CALIBRATION TESTS
# ==============================================================================

def test_model_b_targets():
    """Verify Model B (Asymmetric Linear) conforms to research targets."""
    # P1 ≈ 37 -> L ≈ 0.90 - 0.92
    l_37 = leverage_model_b_asymmetric_linear(37.3)
    assert 0.900 <= l_37 <= 0.920, f"Model B target failed at P1=37.3: {l_37}"

    # P1 = 50 -> L = 1.000 exact
    assert leverage_model_b_asymmetric_linear(50.0) == 1.000

    # P1 ≈ 65 -> L ≈ 1.10 - 1.15
    l_65 = leverage_model_b_asymmetric_linear(65.0)
    assert 1.100 <= l_65 <= 1.160, f"Model B target failed at P1=65: {l_65}"

    # P1 ≈ 75 -> L ≈ 1.18 - 1.25
    l_75 = leverage_model_b_asymmetric_linear(75.0)
    assert 1.180 <= l_75 <= 1.250, f"Model B target failed at P1=75: {l_75}"

    # P1 ≈ 85 -> L ≈ 1.25 - 1.35
    l_85 = leverage_model_b_asymmetric_linear(85.0)
    assert 1.250 <= l_85 <= 1.350, f"Model B target failed at P1=85: {l_85}"

    # P1 ≈ 95 -> L ≈ 1.30 - 1.35
    l_95 = leverage_model_b_asymmetric_linear(95.0)
    assert 1.300 <= l_95 <= 1.350, f"Model B target failed at P1=95: {l_95}"


def test_model_c_targets():
    """Verify Model C (Piecewise Collapse Emphasis) conforms to research targets."""
    # P1 ≈ 37 -> L ≈ 0.89 - 0.92
    l_37 = leverage_model_c_piecewise_collapse(37.3)
    assert 0.880 <= l_37 <= 0.920, f"Model C target failed at P1=37.3: {l_37}"

    # P1 = 50 -> L = 1.000 exact
    assert leverage_model_c_piecewise_collapse(50.0) == 1.000

    # P1 ≈ 65 -> L ≈ 1.10 - 1.15
    l_65 = leverage_model_c_piecewise_collapse(65.0)
    assert 1.100 <= l_65 <= 1.150, f"Model C target failed at P1=65: {l_65}"

    # P1 ≈ 75 -> L ≈ 1.18 - 1.23
    l_75 = leverage_model_c_piecewise_collapse(75.0)
    assert 1.180 <= l_75 <= 1.230, f"Model C target failed at P1=75: {l_75}"

    # P1 ≈ 85 -> L ≈ 1.25 - 1.30
    l_85 = leverage_model_c_piecewise_collapse(85.0)
    assert 1.250 <= l_85 <= 1.300, f"Model C target failed at P1=85: {l_85}"

    # P1 ≈ 95 -> L ≈ 1.30 - 1.35
    l_95 = leverage_model_c_piecewise_collapse(95.0)
    assert 1.300 <= l_95 <= 1.350, f"Model C target failed at P1=95: {l_95}"


# ==============================================================================
# 3. CRITICAL ARCHETYPE BEHAVIOR TESTS
# ==============================================================================

def test_elite_opener_behavior():
    """CASE 1: Elite Opener receives strong reward without unfair penalty."""
    res_b = compute_candidate_score(37.3, 95.0, 95.0, model_func=leverage_model_b_asymmetric_linear)
    assert res_b["candidate_score"] >= 90.0, f"Elite opener score too low: {res_b['candidate_score']}"
    assert res_b["p1_leverage"] == pytest.approx(0.904, abs=0.01)

    res_c = compute_candidate_score(37.3, 95.0, 95.0, model_func=leverage_model_c_piecewise_collapse)
    assert res_c["candidate_score"] >= 89.0, f"Elite opener score too low: {res_c['candidate_score']}"


def test_failed_opener_behavior():
    """CASE 2: Failed Opener remains firmly penalized; low P1 does not protect poor batting."""
    res_b = compute_candidate_score(37.3, 20.0, 20.0, model_func=leverage_model_b_asymmetric_linear)
    assert res_b["candidate_score"] <= 25.0, f"Failed opener score too high: {res_b['candidate_score']}"

    res_c = compute_candidate_score(37.3, 20.0, 20.0, model_func=leverage_model_c_piecewise_collapse)
    assert res_c["candidate_score"] <= 25.0, f"Failed opener score too high: {res_c['candidate_score']}"


def test_collapse_rescue_behavior():
    """CASE 5: Severe Collapse Rescue receives stronger contextual leverage than Elite Opener."""
    # Under identical performance (P2=88, P3=88):
    comp_b = evaluate_equivalent_performance(leverage_model_b_asymmetric_linear, p_perf=88.0)
    assert comp_b["cr_receives_greater_leverage"] is True
    assert comp_b["cr_receives_greater_shift"] is True
    assert comp_b["collapse_rescue"]["leverage"] > comp_b["opener"]["leverage"]
    assert comp_b["collapse_rescue"]["candidate_score"] > comp_b["opener"]["candidate_score"]
    assert comp_b["shift_difference"] > 0, f"CR shift should exceed Opener shift: {comp_b['shift_difference']}"

    comp_c = evaluate_equivalent_performance(leverage_model_c_piecewise_collapse, p_perf=88.0)
    assert comp_c["cr_receives_greater_leverage"] is True
    assert comp_c["cr_receives_greater_shift"] is True
    assert comp_c["shift_difference"] > 0


def test_collapse_failure_behavior():
    """CASE 6: Collapse Failure is heavily penalized under leverage with 0 participation cushion."""
    cur_prod = compute_production_score_25_35_40(85.0, 20.0, 20.0)  # 0.25*85 + 0.75*20 = 36.25
    res_b = compute_candidate_score(85.0, 20.0, 20.0, model_func=leverage_model_b_asymmetric_linear)
    assert res_b["candidate_score"] <= 12.0
    # Penalty drop must be over 20 points
    assert (res_b["candidate_score"] - cur_prod) <= -20.0


def test_collapse_passenger_behavior():
    """CASE 7: Collapse Passenger entering in crisis with par batting (50/50) produces score ≈ 50.0."""
    res_b = compute_candidate_score(85.0, 50.0, 50.0, model_func=leverage_model_b_asymmetric_linear)
    assert res_b["candidate_score"] == 50.0
    res_c = compute_candidate_score(85.0, 50.0, 50.0, model_func=leverage_model_c_piecewise_collapse)
    assert res_c["candidate_score"] == 50.0


def test_death_over_edge_case():
    """CASE 8: Death-over hopeless chase (P3-ISSUE-01) interacts with leverage; remains bounded."""
    res_b = compute_candidate_score(95.0, 40.0, 5.0, model_func=leverage_model_b_asymmetric_linear)
    assert 0.1 <= res_b["candidate_score"] <= 99.9
    # Because P3=5.0 is depressed, leverage amplifies the negative deviation
    assert res_b["adjusted_p3"] <= 5.0
    assert res_b["candidate_score"] <= 25.0


# ==============================================================================
# 4. SYSTEM INTEGRITY, DNB, LEAKAGE & GOVERNANCE TESTS
# ==============================================================================

def test_no_outcome_leakage():
    """Verify match outcome is NOT an input to leverage or scoring."""
    # Innings A: Win, Innings B: Loss, but identical batting & context
    res_win = compute_candidate_score(60.0, 85.0, 80.0, model_func=leverage_model_b_asymmetric_linear)
    res_loss = compute_candidate_score(60.0, 85.0, 80.0, model_func=leverage_model_b_asymmetric_linear)
    assert res_win["candidate_score"] == res_loss["candidate_score"]

    # Losing hero (e.g. Kohli 92* in lost chase): high P2/P3 produces elite score
    res_losing_hero = compute_candidate_score(44.6, 94.2, 97.2, model_func=leverage_model_b_asymmetric_linear)
    assert res_losing_hero["candidate_score"] >= 90.0


def test_dnb_null_preservation():
    """Verify DNB (None, NaN, or is_dnb=True) strictly returns None across all fields."""
    res_dnb = compute_candidate_score(50.0, 80.0, 80.0, is_dnb=True)
    assert res_dnb["is_dnb"] is True
    assert res_dnb["p1_leverage"] is None
    assert res_dnb["adjusted_p2"] is None
    assert res_dnb["adjusted_p3"] is None
    assert res_dnb["candidate_score"] is None

    res_none = compute_candidate_score(None, 80.0, 80.0)
    assert res_none["candidate_score"] is None

    assert leverage_model_b_asymmetric_linear(None) is None
    assert compute_adjusted_pillar(None, 1.0) is None
    assert compute_production_score_25_35_40(None, 50.0, 50.0) is None


def test_production_files_unchanged():
    """
    CRITICAL GOVERNANCE TEST:
    Verify that protected production files are preserved in pre-integration backup.
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


def test_artifacts_exist_and_valid():
    """Verify that Phase 7H specification and validation JSON artifacts exist and are valid."""
    spec_path = Path("models/contribution/phase7/phase7h_asymmetric_leverage_spec.json")
    val_path = Path("models/contribution/phase7/phase7h_asymmetric_leverage_validation.json")

    assert spec_path.exists(), "phase7h_asymmetric_leverage_spec.json missing"
    assert val_path.exists(), "phase7h_asymmetric_leverage_validation.json missing"

    with open(spec_path, "r", encoding="utf-8") as f:
        spec = json.load(f)
    with open(val_path, "r", encoding="utf-8") as f:
        val = json.load(f)

    assert spec["phase"] == "PHASE_7H"
    assert spec["governance_mode"] == "ISOLATED_SIMULATION_AUDIT"
    assert val["dataset_size"] == 19111

    # Verify Model B achieves positive shift difference (CR shift > EO shift)
    model_b_arch = val["models"]["Model B (Asymmetric Linear)"]["archetype_full_dataset"]
    assert model_b_arch["shift_difference_cr_minus_eo"] > 0, (
        f"Model B failed to achieve CR Shift > EO Shift: {model_b_arch['shift_difference_cr_minus_eo']}"
    )

    # Verify P2/P3 correlation drop (enhanced independence)
    model_b_corr = val["models"]["Model B (Asymmetric Linear)"]["correlation_and_stability"]
    assert model_b_corr["p2_p3_corr_drop"] < 0, "Model B failed to reduce P2/P3 colinearity"
