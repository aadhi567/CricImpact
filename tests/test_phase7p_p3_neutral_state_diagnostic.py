"""
Unit and Integration Tests for Phase 7P P3 Neutral-State Calibration Diagnostic.

STRICTLY DIAGNOSTIC AND RESEARCH:
- Validates synthetic scenarios, edge cases, candidate models, and invariance tests.
- Verifies protected files remain unmodified.
"""

import sys
import json
import math
import hashlib
from pathlib import Path
import pytest
import pandas as pd
import numpy as np

# Ensure repository root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.phase7p_p3_neutral_state_diagnostic import (
    PROTECTED_FILES,
    verify_protected_files,
    model_a_current,
    model_b_floor,
    model_c_continuous,
    model_d_headroom,
    make_synthetic_row,
    evaluate_innings_across_models,
    build_synthetic_experiment,
    build_edge_case_matrix,
    run_leakage_and_invariance_audit
)


def test_protected_files_integrity():
    """Verify that all protected files remain byte-for-byte unmodified."""
    res = verify_protected_files()
    assert res["all_passed"], f"Protected file modification detected: {res['files']}"


def test_synthetic_scenarios_ordering():
    """
    Verify the fundamental conceptual ordering:
    Scenario A (Weak Entry -> Big Transformation)
    > Scenario B (Avg Entry -> Good Transformation)
    > Scenario C (Strong Entry -> Maintained State)
    > Scenario D (Strong Entry -> Deterioration).
    """
    exp = build_synthetic_experiment()
    sc_a = exp["scenario_a_weak_entry_transform"]
    sc_b = exp["scenario_b_avg_entry_transform"]
    sc_c = exp["scenario_c_strong_entry_maintain"]
    sc_d = exp["scenario_d_strong_entry_deteriorate"]
    
    # Model A ordering
    assert sc_a["model_a"]["p3"] > sc_b["model_a"]["p3"], "Scenario A should have higher P3 than B in Model A"
    assert sc_b["model_a"]["p3"] > sc_c["model_a"]["p3"], "Scenario B should have higher P3 than C in Model A"
    assert sc_c["model_a"]["p3"] > sc_d["model_a"]["p3"], "Scenario C should have higher P3 than D in Model A"
    
    # Check that in Model A, Scenario C exhibits compression around low 50s
    assert 45.0 <= sc_c["model_a"]["p3"] <= 58.0, f"Model A Scenario C should be compressed near ~50: {sc_c['model_a']['p3']}"
    
    # Model B ordering
    assert sc_a["model_b"]["p3"] > sc_b["model_b"]["p3"]
    assert sc_b["model_b"]["p3"] > sc_c["model_b"]["p3"]
    assert sc_c["model_b"]["p3"] > sc_d["model_b"]["p3"]
    
    # In Model B, Scenario C should be elevated above the compressed 50s
    assert sc_c["model_b"]["p3"] >= 60.0, f"Model B Scenario C should be at or above 60.0: {sc_c['model_b']['p3']}"
    assert sc_d["model_b"]["p3"] < 25.0, f"Model B Scenario D (collapse) should remain heavily penalized: {sc_d['model_b']['p3']}"


def test_anti_free_rider_protection():
    """
    Verify that a passenger batting at low strike rate (8 off 12 balls, SR 66.7)
    in a strong team state does NOT receive preservation floor credit in Model B.
    """
    exp = build_synthetic_experiment()
    passenger = exp["counterfactual_passenger_in_strong_platform"]
    maintainer = exp["scenario_c_strong_entry_maintain"]
    
    # Passenger has personal tempo of 4.0 RPO (< 8.5 RPO required threshold)
    assert passenger["model_b"]["p3"] < 55.0, f"Passenger must NOT receive preservation floor: {passenger['model_b']['p3']}"
    assert maintainer["model_b"]["p3"] >= 60.0, f"Legitimate maintainer must receive preservation credit: {maintainer['model_b']['p3']}"
    assert maintainer["model_b"]["p3"] > passenger["model_b"]["p3"] + 5.0


def test_golden_duck_exclusion():
    """Verify that a golden duck (0 off 1) in a strong state receives zero preservation credit."""
    exp = build_synthetic_experiment()
    duck = exp["counterfactual_golden_duck_in_strong_platform"]
    
    # Model B must give exact same score as Model A (no floor applied)
    assert duck["model_b"]["raw_p3"] == duck["model_a"]["raw_p3"], "Golden duck must not be granted preservation floor"
    assert duck["model_b"]["p3"] < 25.0, f"Golden duck should be penalized for wicket loss: {duck['model_b']['p3']}"


def test_edge_case_matrix_completeness():
    """Verify that all 14 edge cases (A through N) are evaluated, and Case N (DNB) is None."""
    matrix = build_edge_case_matrix()
    assert len(matrix) == 14, f"Expected 14 edge cases, got {len(matrix)}"
    
    ids = [ec["id"] for ec in matrix]
    expected_ids = [f"Case {chr(ord('A') + i)}" for i in range(14)]
    assert ids == expected_ids
    
    # Case N (DNB) verification
    dnb_case = matrix[-1]
    assert dnb_case["id"] == "Case N"
    assert dnb_case["p2"] is None
    assert dnb_case["model_a"]["p3"] is None
    assert dnb_case["model_b"]["p3"] is None


def test_leakage_and_invariance_audits():
    """Verify outcome invariance, player identity invariance, and P2/P3 independence."""
    df = pd.read_csv("data/processed/batter_match_contributions.csv", low_memory=False)
    audit = run_leakage_and_invariance_audit(df)
    
    assert audit["future_match_outcome_invariance"]["passed"], "Future match outcome must not affect P3"
    assert audit["player_identity_invariance"]["passed"], "Player identity must not affect P3"
    assert audit["p2_p3_independence_verified"]["low_p2_high_p3_exists"], "Low P2 + High P3 must be mathematically possible"
    assert audit["p2_p3_independence_verified"]["high_p2_low_p3_exists"], "High P2 + Low P3 must be mathematically possible"
    assert audit["golden_duck_exclusion"]["passed"], "Golden duck must be excluded from preservation floor"
    assert audit["dnb_preservation"]["passed"], "DNB must remain preserved"


def test_diagnostic_json_artifact_exists_and_valid():
    """Verify the JSON diagnostic artifact exists and has all required sections."""
    path = Path("models/contribution/phase7/phase7p_p3_neutral_state_diagnostic.json")
    assert path.exists(), f"Artifact not found at {path}"
    
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    required_keys = [
        "phase", "sub_topic", "protected_files_integrity",
        "synthetic_experiments", "edge_case_matrix", "population_distribution",
        "real_case_studies", "leakage_and_invariance_audit", "diagnostic_conclusions"
    ]
    for k in required_keys:
        assert k in data, f"Missing required key: {k}"
        
    assert data["phase"] == "PHASE_7P"
    assert data["protected_files_integrity"]["all_passed"] is True
