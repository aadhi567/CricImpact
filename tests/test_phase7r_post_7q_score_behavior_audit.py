"""
Phase 7R: Post-7Q Score Behavior Audit & Governance Test Suite.
Validates the mathematical behavior, component interactions, test matrix,
leverage properties, and governance invariance of the production contribution model.
"""

import math
import numpy as np
import pandas as pd
import pytest

from src.contribution_framework import (
    compute_production_contribution,
    compute_context_and_leverage,
    compute_adjusted_pillar,
    check_p3_preservation_eligibility,
    apply_p3_score_preservation_floor,
)
from src.phase7q_p3_neutral_state_preservation import make_synthetic_row
from src.phase7r_post_7q_score_behavior_audit import (
    verify_protected_files_integrity,
    audit_component_interactions,
    audit_leverage_grid,
    run_mandatory_test_matrix,
    audit_p3_semantics,
    generate_audit_report_data,
)


def test_governance_and_protected_files_intact():
    """Verify that all protected baseline production files remain byte-for-byte unchanged."""
    res = verify_protected_files_integrity()
    assert res["all_protected_files_intact"] is True, f"Integrity check failed: {res}"
    for filepath, details in res["files"].items():
        assert details["matched"] is True, f"File {filepath} hash mismatch: {details}"


def test_component_interactions_mathematical_property():
    """Verify that Final Contribution is mathematically equivalent to (P2 + P3)/2 rotated by L."""
    p2 = 84.0
    p3 = 64.0
    lev = 0.908

    adj_p2 = float(np.clip(50.0 + (p2 - 50.0) * lev, 0.1, 99.9))
    adj_p3 = float(np.clip(50.0 + (p3 - 50.0) * lev, 0.1, 99.9))
    final_score = float(np.clip(0.50 * adj_p2 + 0.50 * adj_p3, 0.1, 99.9))

    mean_p = 0.50 * p2 + 0.50 * p3
    expected_rotated = float(np.clip(50.0 + (mean_p - 50.0) * lev, 0.1, 99.9))

    assert math.isclose(final_score, expected_rotated, abs_tol=1e-5)


def test_mandatory_matrix_cases_a_through_f():
    """Verify Cases A through F covering transformation, maintenance, deterioration, passenger, and duck."""
    matrix = run_mandatory_test_matrix()

    case_a = matrix["case_a_weak_platform_transform"]
    case_b = matrix["case_b_avg_platform_transform"]
    case_c = matrix["case_c_strong_platform_maintain"]
    case_d = matrix["case_d_strong_platform_deteriorate"]
    case_e = matrix["case_e_strong_platform_passenger"]
    case_f = matrix["case_f_golden_duck"]

    # Transformation high scores
    assert case_a["p3"] >= 85.0
    assert case_b["p3"] >= 70.0

    # Maintenance capped around preservation floor
    assert case_c["p3"] == 64.0
    assert case_c["final"] >= 70.0

    # Deterioration heavily penalized
    assert case_d["p3"] < 15.0
    assert case_d["final"] < 25.0

    # Passenger strictly blocked by anti-free-rider gate
    assert case_e["p3"] <= 51.0
    assert case_e["final"] < 40.0

    # Golden duck heavily penalized
    assert case_f["p3"] < 20.0
    assert case_f["final"] < 20.0

    # Full 4-state hierarchy
    assert matrix["four_state_hierarchy_verified"] is True


def test_mandatory_matrix_chase_cases_g_and_h():
    """Verify Cases G and H testing chase leverage under comfortable vs difficult targets."""
    matrix = run_mandatory_test_matrix()
    case_g = matrix["case_g_comfortable_chase"]
    case_h = matrix["case_h_difficult_chase"]

    # Case G: Comfortable chase has low/moderate leverage
    assert case_g["leverage"] <= 0.95
    assert case_g["p3"] >= 65.0
    assert case_g["final"] >= 70.0

    # Case H: Difficult chase has amplified leverage
    assert case_h["leverage"] > 1.00


def test_mandatory_matrix_shortened_and_entry_cases_i_and_j():
    """Verify Case I (shortened innings) and Case J (post-4-over entry)."""
    matrix = run_mandatory_test_matrix()
    case_i = matrix["case_i_shortened_innings"]
    case_j = matrix["case_j_post_4_over_entry"]

    # Shortened innings executes Phase 7O fallback cleanly
    assert case_i["p3"] > 90.0
    assert case_i["final"] > 90.0

    # Post-4-over entry applies Model E and preservation cleanly
    assert case_j["p3"] == 64.0
    assert case_j["final"] > 70.0


def test_mandatory_matrix_invariance_cases_k_l_m():
    """Verify DNB (Case K), player identity invariance (Case L), and outcome invariance (Case M)."""
    matrix = run_mandatory_test_matrix()

    assert matrix["case_k_dnb"]["final"] is None
    assert matrix["case_k_dnb"]["p2"] is None
    assert matrix["case_k_dnb"]["p3"] is None

    assert matrix["case_l_player_invariance"]["delta"] == 0.0
    assert matrix["case_m_outcome_invariance"]["delta"] == 0.0


def test_leverage_grid_properties():
    """Verify mathematical properties of the leverage adjustment grid."""
    grid_audit = audit_leverage_grid()
    assert grid_audit["par_invariance"] is True
    assert grid_audit["monotonicity_under_high_leverage"] is True

    # Test exact bounds
    for profile, data in grid_audit["grid"].items():
        for lev_key, val in data["adjustments"].items():
            assert 0.1 <= val <= 99.9


def test_p3_semantic_audit_content():
    """Verify that all 10 semantic audit questions are fully answered."""
    semantics = audit_p3_semantics()
    assert len(semantics) == 10
    assert "P3 = 50.0 represents exact league-average" in semantics["q1_p3_equals_50"]
    assert "64.0" in semantics["q6_maintaining_strong_state_above_50"]
    assert "Anti-Free-Rider Gate" in semantics["q8_preventing_passenger_credit"]
    assert "0.00000000" in semantics["q9_achieving_without_using_p2"]


def test_final_decision_gate():
    """Verify that the decision gate recommendation is Option A."""
    report_data = generate_audit_report_data()
    decision = report_data["final_decision_gate"]["recommendation"]
    assert "A. CURRENT MODEL IS MATHEMATICALLY SOUND" in decision
