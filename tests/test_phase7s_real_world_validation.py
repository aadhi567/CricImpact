"""
Phase 7S: Real-World Player/Match Validation & Score Semantics Test Suite.
Validates real IPL player/match performances across Archetypes A through T,
comparative context triples, high-P2/low-P3 audits, and governance invariances.
"""

import pandas as pd
import pytest

from src.phase7s_real_world_validation import (
    CSV_PATH,
    verify_protected_files_integrity,
    select_real_historical_cases,
    run_comparative_triples_analysis,
    run_top50_high_p2_low_p3_audit,
    run_high_p2_high_p3_audit,
    run_final_score_patterns_audit,
    run_leverage_check_audit,
    run_full_invariance_checks,
    generate_phase7s_audit_data,
)


@pytest.fixture(scope="module")
def df_contributions():
    return pd.read_csv(CSV_PATH, low_memory=False)


def test_governance_and_protected_files():
    """Verify that all protected baseline production files remain byte-for-byte unchanged."""
    res = verify_protected_files_integrity()
    assert res["all_protected_files_intact"] is True, f"Integrity check failed: {res}"
    for filepath, details in res["files"].items():
        assert details["matched"] is True, f"File {filepath} hash mismatch: {details}"


def test_real_historical_cases_count_and_coverage(df_contributions):
    """Verify that 40 real IPL cases covering Archetypes A through T are evaluated cleanly."""
    cases = select_real_historical_cases(df_contributions)
    assert len(cases) >= 40, f"Expected at least 40 cases, got {len(cases)}"

    archetypes_present = set(c["archetype_code"] for c in cases)
    expected_archetypes = {chr(ord('A') + i) for i in range(20)}  # A through T
    assert expected_archetypes.issubset(archetypes_present), f"Missing archetypes: {expected_archetypes - archetypes_present}"

    for c in cases:
        assert c["player"] is not None and len(c["player"]) > 0
        assert c["match_id"] > 0
        assert 0.1 <= c["p2"] <= 99.9
        assert 0.1 <= c["raw_p3"] <= 99.9
        assert 0.1 <= c["final_score"] <= 99.9
        assert 0.65 <= c["leverage"] <= 1.35
        assert len(c["interpretation"]) > 20


def test_comparative_triples_behavior(df_contributions):
    """Verify the controlled comparison triple of batters with ~50 off ~25 balls."""
    triples = run_comparative_triples_analysis(df_contributions)

    p_a = triples["player_a_preservation"]
    p_b = triples["player_b_transformation"]
    p_c = triples["player_c_difficult_chase"]

    # All three players have similar individual execution (~84 to ~87)
    assert abs(p_a["p2"] - p_b["p2"]) <= 5.0
    assert abs(p_b["p2"] - p_c["p2"]) <= 5.0

    # Final contribution scores reflect team context:
    # Pollard (difficult chase) > Pooran (crisis transformation) > Karthik (strong platform preservation)
    assert p_c["final_score"] > p_b["final_score"] > p_a["final_score"]
    assert p_a["final_score"] >= 70.0
    assert p_b["final_score"] >= 85.0
    assert p_c["final_score"] >= 90.0


def test_top50_high_p2_low_p3_no_model_defects(df_contributions):
    """Verify that in the top 50 extreme P2/P3 gap cases, zero model defects exist."""
    audit = run_top50_high_p2_low_p3_audit(df_contributions)
    assert audit["total_audited"] == 50
    assert audit["classifications"]["suspicious_cases"] == 0
    total_valid = (
        audit["classifications"]["legitimate_deterioration"] +
        audit["classifications"]["legitimate_cameo_low_involvement"] +
        audit["classifications"]["legitimate_slow_team_window"] +
        audit["classifications"]["sub_elite_flat_platform"]
    )
    assert total_valid == 50


def test_high_p2_high_p3_characteristics(df_contributions):
    """Verify characteristics of high P2 and high P3 cohort."""
    audit = run_high_p2_high_p3_audit(df_contributions)
    assert audit["count"] > 1000
    assert audit["mean_runs"] >= 50.0
    assert audit["mean_sr"] >= 150.0


def test_final_score_patterns_consistency(df_contributions):
    """Verify the 4 quadrants of Final Score behavior."""
    patterns = run_final_score_patterns_audit(df_contributions)
    assert patterns["p2_ge_85_final_sub_60"]["count"] > 0
    assert patterns["p2_ge_85_final_ge_80"]["count"] > 1000
    assert patterns["p3_ge_80_final_sub_70"]["count"] > 0
    assert patterns["p3_ge_80_final_ge_80"]["count"] > 1000


def test_leverage_scaling_audit(df_contributions):
    """Verify that leverage scales context appropriately for high-quality batting."""
    audit = run_leverage_check_audit(df_contributions)
    assert audit["low_leverage_high_p2"]["count"] > 0
    assert audit["high_leverage_high_p2"]["count"] > 0


def test_full_invariances_and_leakage(df_contributions):
    """Verify player identity, match outcome, DNB, and P2/P3 independence invariances."""
    invar = run_full_invariance_checks(df_contributions)
    assert invar["all_invariances_passed"] is True
    assert invar["player_identity_invariance_delta"] == 0.0
    assert invar["outcome_invariance_delta"] == 0.0
    assert invar["dnb_strict_preservation"] is True
    assert invar["p2_p3_independence_delta"] == 0.0


def test_final_decision_gate():
    """Verify that the decision gate recommendation is Option A."""
    data = generate_phase7s_audit_data()
    rec = data["final_decision_gate"]["recommendation"]
    assert "A. MODEL BEHAVIOR VALIDATED — NO CHANGE REQUIRED" in rec
