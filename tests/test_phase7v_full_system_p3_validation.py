"""
Phase 7V Test Suite — Full-System P3 Validation, Calibration & Behavioral Audit.

Verifies:
1. Governance: Production files and datasets are 100% intact and unaltered.
2. Behavior Matrix: Complete population distribution across P2 x P3 matrix and correlation.
3. Expected Behavior Scenarios: Canonical Cases A through J evaluate correctly.
4. Phase 7O Stabilization: Early-over sample-size stabilization remains intact.
5. Phase 7U Attribution: Wicket causality attribution behaves as designed without leakage.
6. Chase Validation: Second innings audit, no outcome leakage, leverage properly captured.
7. Shortened-Innings Validation: Phase 7O and Phase 7U non-interference verified.
8. Extreme Cases: All 7 categories populated with >= 10 cases and all 16 required fields.
9. Population Statistics: Correct distributions and counts across 19,111 appearances.
10. Invariance & Leakage: Invariance to match outcome, identity, future info, and P2 independence.
11. Calibration Question: Neutral par centered at 50.0 verified.
12. Decision Gate: Confirms Decision A (Validated and ready for freeze).
"""

import json
import pytest
import pandas as pd
import numpy as np
from pathlib import Path

from src.phase7v_full_system_p3_validation import (
    REPO_ROOT,
    PROTECTED_FILE_CHECKSUMS,
    verify_governance_and_backups,
    audit_p2_p3_behavior_matrix,
    build_expected_p3_behavior_matrix,
    verify_phase7o_stabilization,
    verify_phase7u_attribution,
    audit_chase_second_innings,
    audit_shortened_innings,
    extract_historical_extreme_cases,
    compute_population_statistics,
    evaluate_calibration_question,
    run_invariance_and_leakage_audit,
    compute_production_contribution,
)


@pytest.fixture(scope="module")
def df_appearances():
    df_path = REPO_ROOT / "data" / "processed" / "batter_match_contributions.csv"
    assert df_path.exists(), f"Missing dataset: {df_path}"
    return pd.read_csv(df_path, low_memory=False)


@pytest.fixture(scope="module")
def validation_json():
    json_path = REPO_ROOT / "models" / "contribution" / "phase7" / "phase7v_full_system_p3_validation.json"
    assert json_path.exists(), f"Missing validation JSON: {json_path}"
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ==============================================================================
# 1. GOVERNANCE AND PROTECTED FILES INTEGRITY
# ==============================================================================

def test_governance_and_backups():
    """Verify all protected files exist and match baseline SHA256/MD5 hashes."""
    gov = verify_governance_and_backups()
    assert gov["all_protected_files_intact"] is True
    assert gov["backup_verified"] is True
    for path, info in gov["files"].items():
        assert info["matched"] is True, f"File {path} has modified hash!"


# ==============================================================================
# 2. P2 x P3 BEHAVIOR MATRIX & CORRELATION
# ==============================================================================

def test_p2_p3_behavior_matrix(df_appearances):
    """Verify matrix classifications and the High P2 / Mid P3 scrutiny breakdown."""
    matrix = audit_p2_p3_behavior_matrix(df_appearances)
    assert matrix["total_valid_appearances"] == 19111

    counts = matrix["counts"]
    total_classified = sum(counts.values())
    assert total_classified == 19111

    # Check key categories exist and are populated
    assert counts["A_low_p2_low_p3"] > 6000
    assert counts["D_high_p2_high_p3"] > 3000
    assert counts["C_high_p2_moderate_p3"] > 1000
    assert counts["B_high_p2_low_p3"] > 400

    # Scrutiny breakdown for High P2 + Mid P3 in [40, 60]
    breakdown = matrix["high_p2_mid_p3_breakdown"]
    assert breakdown["3_independent_partner_collapse"] > 250
    assert breakdown["2_successful_state_maintenance"] > 100
    assert breakdown["1_genuine_team_failure"] > 50


# ==============================================================================
# 3. EXPECTED P3 BEHAVIOR SCENARIOS (CASES A THROUGH J)
# ==============================================================================

def test_expected_scenarios_all_valid():
    """Verify all 10 canonical scenarios evaluate to valid: True."""
    matrix = build_expected_p3_behavior_matrix()
    assert matrix["all_scenarios_valid"] is True

    scenarios = matrix["scenarios"]
    assert len(scenarios) == 10

    # Case A: Poor batting + team decline -> Low P2, Low P3
    assert scenarios["CASE_A_POOR_BATTING_TEAM_DECLINE"]["p2"] < 30.0
    assert scenarios["CASE_A_POOR_BATTING_TEAM_DECLINE"]["p3"] < 25.0

    # Case B: Excellent batting + weak inherited + major improvement -> High P2, High P3
    assert scenarios["CASE_B_EXCELLENT_BATTING_MAJOR_IMPROVEMENT"]["p2"] > 85.0
    assert scenarios["CASE_B_EXCELLENT_BATTING_MAJOR_IMPROVEMENT"]["p3"] > 85.0

    # Case C: Excellent batting + elite inherited + maintenance -> High P2, moderate P3
    assert scenarios["CASE_C_EXCELLENT_BATTING_STATE_MAINTENANCE"]["p2"] > 80.0
    assert 60.0 <= scenarios["CASE_C_EXCELLENT_BATTING_STATE_MAINTENANCE"]["p3"] <= 70.0

    # Case D: Pooran archetype (independent partner wickets) -> High P2, moderate P3 with relief
    assert scenarios["CASE_D_GOOD_BATTER_INDEPENDENT_WICKETS"]["p2"] > 85.0
    assert scenarios["CASE_D_GOOD_BATTER_INDEPENDENT_WICKETS"]["gamma"] == 0.15
    assert 50.0 <= scenarios["CASE_D_GOOD_BATTER_INDEPENDENT_WICKETS"]["p3"] <= 60.0

    # Case E: Batter-caused pressure -> No relief (gamma = 1.0), low P3
    assert scenarios["CASE_E_BATTER_CAUSED_PRESSURE_WICKET"]["gamma"] == 1.0
    assert scenarios["CASE_E_BATTER_CAUSED_PRESSURE_WICKET"]["p3"] <= 35.0

    # Case F: Golden duck -> Very low P2, very low P3, no relief
    assert scenarios["CASE_F_GOLDEN_DUCK"]["p2"] <= 20.0
    assert scenarios["CASE_F_GOLDEN_DUCK"]["p3"] <= 25.0
    assert scenarios["CASE_F_GOLDEN_DUCK"]["gamma"] == 1.0

    # Case G: Slow crawl -> Low P2, low P3, no relief
    assert scenarios["CASE_G_SLOW_CRAWL"]["p2"] <= 30.0
    assert scenarios["CASE_G_SLOW_CRAWL"]["p3"] <= 30.0
    assert scenarios["CASE_G_SLOW_CRAWL"]["gamma"] == 1.0

    # Case H: Passenger in easy chase -> Low P2, Low/Moderate P3, no free ride
    assert scenarios["CASE_H_PASSENGER_EASY_CHASE"]["p2"] <= 35.0
    assert scenarios["CASE_H_PASSENGER_EASY_CHASE"]["p3"] <= 45.0

    # Case I: Strong chase knock -> High P2, High P3
    assert scenarios["CASE_I_STRONG_CHASE_CONTRIBUTION"]["p2"] >= 80.0
    assert scenarios["CASE_I_STRONG_CHASE_CONTRIBUTION"]["p3"] >= 75.0

    # Case J: Shortened innings early over -> Valid P3 produced
    assert scenarios["CASE_J_SHORTENED_INNINGS_EARLY_OVER"]["p3"] is not None


# ==============================================================================
# 4. PHASE 7O EARLY-OVER STABILIZATION
# ==============================================================================

def test_phase7o_stabilization(df_appearances):
    """Verify early-over sample-size stabilization works across entry overs."""
    p7o = verify_phase7o_stabilization(df_appearances)
    assert p7o["phase7o_status"] == "STABLE_AND_ACTIVE"
    assert p7o["all_alpha_tests_passed"] is True

    prog = p7o["alpha_progression_tests"]
    assert len(prog) == 7
    # Check weights alpha grow smoothly as overs advance towards 4.0
    alphas = [t["computed_alpha"] for t in prog]
    assert alphas[0] < alphas[1] < alphas[2] < alphas[3] < alphas[4] < alphas[5]
    assert alphas[5] == 1.0
    assert alphas[6] == 1.0


# ==============================================================================
# 5. PHASE 7U WICKET CAUSALITY ATTRIBUTION
# ==============================================================================

def test_phase7u_attribution(df_appearances):
    """Verify partner wicket attribution categories and gamma distribution."""
    p7u = verify_phase7u_attribution(df_appearances)
    assert p7u["phase7u_status"] == "VALIDATED_AND_ACTIVE"

    gamma_dist = p7u["gamma_distribution"]
    assert gamma_dist["1.00"] > 10000
    assert gamma_dist["0.15"] > 500

    pooran = p7u["pooran_anchor_verification"]
    assert pooran["passed"] is True
    assert pooran["gamma"] == 0.15
    assert pooran["p3"] >= 50.0


# ==============================================================================
# 6. CHASE SECOND INNINGS AUDIT
# ==============================================================================

def test_chase_second_innings_audit(df_appearances):
    """Verify 2nd innings audit, outcome invariance and leverage mechanics."""
    chase = audit_chase_second_innings(df_appearances)
    assert chase["total_chase_appearances"] > 8000
    assert "ZERO_LEAKAGE" in chase["outcome_leakage_status"]
    assert len(chase["sample_high_p2_low_p3_cases"]) > 0
    assert len(chase["sample_low_p2_high_p3_cases"]) > 0


# ==============================================================================
# 7. SHORTENED INNINGS AUDIT
# ==============================================================================

def test_shortened_innings_audit(df_appearances):
    """Verify shortened innings behavior and non-interference between 7O and 7U."""
    shortened = audit_shortened_innings(df_appearances)
    assert shortened["non_interference_with_phase7u"] is True
    assert shortened["total_unmodelled_first_innings"] == 172
    assert shortened["percentage_of_population"] > 0.0


# ==============================================================================
# 8. HISTORICAL EXTREME CASES EXTRACTION
# ==============================================================================

def test_historical_extreme_cases(df_appearances):
    """Verify at least 10 cases in each of the 7 categories with all 16 required fields."""
    cases = extract_historical_extreme_cases(df_appearances)
    assert len(cases) == 7

    required_fields = [
        "player", "match_id", "innings", "runs", "balls", "SR",
        "P2", "P3", "final_contribution", "entry_state", "exit_state",
        "EFS_delta", "partner_wickets", "gamma_attr", "leverage",
        "classification", "diagnostic_explanation"
    ]

    for cat_name, cat_cases in cases.items():
        assert len(cat_cases) >= 10, f"Category {cat_name} has fewer than 10 cases ({len(cat_cases)})"
        for c in cat_cases:
            for field in required_fields:
                assert field in c, f"Missing field {field} in category {cat_name} case {c.get('player')}"


# ==============================================================================
# 9. POPULATION STATISTICS
# ==============================================================================

def test_population_statistics(df_appearances):
    """Verify population metrics, correlations, and distributions."""
    stats = compute_population_statistics(df_appearances)
    assert stats["total_valid_appearances"] == 19111

    # Check correlation: P2 and P3 must be moderately positively correlated
    assert 0.55 <= stats["correlation_p2_p3"]["pearson"] <= 0.70

    # Check distribution means
    assert 45.0 <= stats["p2_distribution"]["mean"] <= 55.0
    assert 45.0 <= stats["p3_distribution"]["mean"] <= 55.0


# ==============================================================================
# 10. CALIBRATION QUESTION (NEUTRAL PAR AT 50.0)
# ==============================================================================

def test_calibration_par_centered_at_50():
    """Verify empirical rationale for centering P3 neutral par at 50.0."""
    calib = evaluate_calibration_question()
    assert calib["recommended_neutral_point"] == 50.0
    assert "Context-as-Leverage" in calib["mathematical_justification"]
    assert "neutral_team_state_impact" in calib["state_distinctions"]
    assert "successful_state_maintenance" in calib["state_distinctions"]


# ==============================================================================
# 11. INVARIANCE AND LEAKAGE AUDIT
# ==============================================================================

def test_invariance_and_leakage():
    """Verify all 7 mandatory invariances pass without leakage."""
    invariances = run_invariance_and_leakage_audit()
    assert invariances["all_invariances_passed"] is True
    assert invariances["outcome_invariance"]["passed"] is True
    assert invariances["player_identity_invariance"]["passed"] is True
    assert invariances["p2_independence"]["passed"] is True
    assert invariances["future_information_invariance"]["passed"] is True
    assert invariances["dnb_preservation"]["passed"] is True
    assert invariances["super_over_exclusion"]["passed"] is True
    assert invariances["phase7o_compatibility"]["passed"] is True


# ==============================================================================
# 12. FINAL DECISION GATE
# ==============================================================================

def test_final_decision_gate(validation_json):
    """Verify final decision gate confirms ready for freeze with 0 production modifications."""
    gate = validation_json["final_decision_gate"]
    assert gate["decision"] == "A. P3 architecture is validated and ready for freeze."
    assert gate["production_files_modified"] == 0
    assert gate["production_datasets_modified"] == 0
