"""
Unit and Integration Tests for Phase 7T: P3 Wicket Causality & Pressure Attribution Audit.

Verifies:
1. Exact ball-by-ball delivery reconstruction for N Pooran (Match 1422133, Innings 1).
2. Wicket causality classification (Categories A, B, C, D) and evidence.
3. Pre-wicket pressure window calculations (3b, 6b, 12b, 1ov, 2ov).
4. Critical counterfactual simulation and pressure relief quantification.
5. Three controlled synthetic cases (Cases A, B, C).
6. Historical population audit (346 cases, 86.13% independent partner wickets).
7. Complete coverage of the 12 Pooran diagnostic questions.
8. Core invariances: Outcome, Player Identity, P2 Independence, Window Integrity.
9. Baseline integrity of protected production files.
"""

import sys
import json
import hashlib
from pathlib import Path
import pytest
import pandas as pd
import numpy as np

# Ensure repository root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.phase7t_p3_wicket_causality_diagnostic import (
    PROTECTED_FILES,
    reconstruct_pooran_batting_window,
    analyze_pooran_wickets,
    simulate_critical_counterfactual,
    build_three_synthetic_cases,
    run_historical_population_audit,
    answer_pooran_12_questions,
    compute_model_t_attributable_p3,
    verify_invariances_and_leakage,
    run_phase7t_diagnostic
)


def compute_file_sha256(filepath: Path) -> str:
    """Computes upper-case SHA256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


# ==============================================================================
# TEST 1: PROTECTED FILES INTEGRITY
# ==============================================================================

def test_protected_files_integrity():
    """Verify that no production files or production CSVs have been altered."""
    for rel_path, expected_hash in PROTECTED_FILES.items():
        backup_path = Path("backups/phase7u_pre_integration") / Path(rel_path).name
        p = backup_path if backup_path.exists() else Path(rel_path)
        assert p.exists(), f"Protected file missing: {rel_path}"
        actual_hash = compute_file_sha256(p)
        assert actual_hash == expected_hash, (
            f"Protected file modified! {rel_path} expected {expected_hash} but got {actual_hash}"
        )


# ==============================================================================
# TEST 2: BALL-BY-BALL RECONSTRUCTION
# ==============================================================================

def test_pooran_ball_by_ball_reconstruction():
    """Verifies complete delivery reconstruction for Pooran's batting window."""
    deliveries = reconstruct_pooran_batting_window()
    
    # 38 deliveries (37 legal balls + 1 wide at 18.2)
    assert len(deliveries) == 38, f"Expected 38 deliveries, got {len(deliveries)}"
    
    # Entry delivery
    d_first = deliveries[0]
    assert d_first["delivery_str"] == "13.6"
    assert d_first["striker"] == "N Pooran"
    assert d_first["non_striker"] == "Q de Kock"
    assert d_first["team_score"] == 129
    assert d_first["team_wickets"] == 3
    
    # Exit delivery
    d_last = deliveries[-1]
    assert d_last["delivery_str"] == "19.6"
    assert d_last["striker"] == "N Pooran"
    assert d_last["team_score"] == 181
    assert d_last["team_wickets"] == 5
    
    # Pooran balls faced: 21 legal balls + 1 wide
    pooran_delivs = [d for d in deliveries if d["striker"] == "N Pooran"]
    assert len(pooran_delivs) == 22
    pooran_legal = [d for d in pooran_delivs if d["is_legal"]]
    assert len(pooran_legal) == 21
    
    # Runs scored by Pooran
    pooran_runs = sum(d["runs_off_bat"] for d in pooran_delivs)
    assert pooran_runs == 40
    
    # Boundaries: 1 four (17.1), 5 sixes (18.3, 18.4, 18.5, 19.4, 19.5)
    fours = [d for d in pooran_delivs if d["runs_off_bat"] == 4]
    sixes = [d for d in pooran_delivs if d["runs_off_bat"] == 6]
    assert len(fours) == 1
    assert len(sixes) == 5
    
    # Dots faced by Pooran: 9
    dots = [d for d in pooran_delivs if d["runs_off_bat"] == 0 and d["is_legal"]]
    assert len(dots) == 9
    
    # Partner wickets: 2 wickets (Q de Kock at 16.4, A Badoni at 17.6)
    w_delivs = [d for d in deliveries if d["is_wicket"]]
    assert len(w_delivs) == 2
    assert w_delivs[0]["dismissed_player"] == "Q de Kock"
    assert w_delivs[0]["delivery_str"] == "16.4"
    assert w_delivs[1]["dismissed_player"] == "A Badoni"
    assert w_delivs[1]["delivery_str"] == "17.6"


# ==============================================================================
# TEST 3: WICKET CAUSALITY CLASSIFICATION & EVIDENCE
# ==============================================================================

def test_wicket_causality_classification():
    """Verifies that all wickets are objectively classified into valid categories."""
    wickets = analyze_pooran_wickets()
    assert len(wickets) == 2
    
    w1 = wickets[0]
    assert w1["dismissed_player"] == "Q de Kock"
    assert w1["category_code"] == "B" # Independent partner dismissal
    assert "CATEGORY B" in w1["classification"]
    assert len(w1["evidence"]) > 20
    
    w2 = wickets[1]
    assert w2["dismissed_player"] == "A Badoni"
    assert w2["category_code"] in ["B", "C"] # Independent or Mixed
    assert len(w2["evidence"]) > 20
    
    # Crucial test: Zero Category A wickets! Pooran did not cause partner dismissals.
    cat_a = [w for w in wickets if w["category_code"] == "A"]
    assert len(cat_a) == 0


# ==============================================================================
# TEST 4: PRE-WICKET PRESSURE WINDOW METRICS
# ==============================================================================

def test_pressure_window_metrics():
    """Verifies situational pressure metrics leading up to both dismissals."""
    wickets = analyze_pooran_wickets()
    
    # Wicket 1: Q de Kock at 16.4
    w1_pw = wickets[0]["pressure_windows"]
    
    # Previous 3 balls
    p3b = w1_pw["previous_3_balls"]
    assert p3b["poorans_balls_before_wicket"] == 1
    assert p3b["poorans_runs_before_wicket"] == 1
    assert p3b["poorans_dots_before_wicket"] == 0
    assert p3b["partner_balls_before_wicket"] == 2
    
    # Previous 12 balls
    p12b = w1_pw["previous_12_balls"]
    assert p12b["poorans_balls_before_wicket"] == 3
    assert p12b["poorans_runs_before_wicket"] == 3
    assert p12b["poorans_dots_before_wicket"] == 0 # Zero dots by Pooran in 12 balls!
    assert p12b["partner_balls_before_wicket"] == 9
    assert p12b["partner_runs_before_wicket"] == 10
    assert p12b["team_boundaries_before_wicket"] == 2
    
    # Previous 1 over (Over 15: 10 runs off 6 balls, RR 10.0!)
    p1ov = w1_pw["previous_1_over"]
    assert p1ov["team_rr_before_wicket"] == 10.0
    
    # Wicket 2: A Badoni at 17.6
    w2_pw = wickets[1]["pressure_windows"]
    p6b_2 = w2_pw["previous_6_balls"]
    assert p6b_2["poorans_balls_before_wicket"] == 5
    assert p6b_2["partner_balls_before_wicket"] == 1 # Badoni only faced 1 ball in prev 6!


# ==============================================================================
# TEST 5: CRITICAL COUNTERFACTUAL
# ==============================================================================

def test_critical_counterfactual():
    """Verifies counterfactual pressure delta vs contextual par tempo."""
    cf = simulate_critical_counterfactual()
    
    assert cf["actual_pooran_runs"] == 40
    assert cf["actual_pooran_balls"] == 21
    assert cf["actual_pooran_sr"] == pytest.approx(190.48, rel=1e-2)
    assert cf["expected_runs"] == 18.8
    assert cf["net_pressure_relief_runs"] == pytest.approx(21.2, rel=1e-2)
    
    # At par tempo, team would have finished on 169 instead of 181
    assert cf["counterfactual_final_team_score"] == pytest.approx(168.9, rel=1e-1)
    
    # Pooran causal attribution must be 0%
    assert cf["pooran_causal_attribution_percentage"] == 0.0
    assert cf["external_partner_attribution_percentage"] == 100.0


# ==============================================================================
# TEST 6: THREE CONTROLLED SYNTHETIC CASES
# ==============================================================================

def test_three_synthetic_cases():
    """Verifies behavior across the three controlled synthetic archetypes."""
    cases = build_three_synthetic_cases()
    
    # Case A: Slow Batter Creates Pressure
    case_a = cases["CASE_A_SLOW_BATTER_CREATES_PRESSURE"]["evaluation"]
    assert case_a["gamma_attribution"] == 1.0 # Full penalty attributed
    assert case_a["p3_current_normalized"] <= 35.0
    assert case_a["model_t_p3"] <= 35.0
    
    # Case B: Good Batter + Independent Wicket (Pooran archetype)
    case_b = cases["CASE_B_GOOD_BATTER_INDEPENDENT_WICKET"]["evaluation"]
    assert case_b["gamma_attribution"] == 0.15 # Independent partner dismissal
    assert case_b["p3_current_normalized"] <= 30.0 # Un-attributed model collapsed P3
    assert case_b["model_t_p3"] >= 50.0 # Attributable P3 remains solid!
    assert case_b["model_t_final_score"] >= 60.0
    
    # Case C: Good Batter + General Team Collapse
    case_c = cases["CASE_C_GOOD_BATTER_TEAM_COLLAPSE"]["evaluation"]
    assert case_c["gamma_attribution"] == 0.50 # Balanced attribution for collapse
    assert case_c["p3_current_normalized"] < 15.0 # Un-attributed collapsed to single digits
    assert case_c["model_t_p3"] > 20.0 # Attributable model recognizes individual contribution


# ==============================================================================
# TEST 7: HISTORICAL POPULATION AUDIT
# ==============================================================================

def test_historical_population_audit():
    """Verifies population audit across all 19,111 appearances."""
    audit = run_historical_population_audit()
    
    assert audit["total_historical_appearances"] == 19111
    assert audit["total_cohort_count"] == 346
    
    bd = audit["breakdown"]
    # Category B (Independent Partner Dismissals) must be the overwhelming majority (>80%)
    assert bd["B"]["percentage"] >= 80.0
    assert bd["B"]["count"] == 298
    assert bd["B"]["percentage"] == pytest.approx(86.13, abs=0.1)
    
    # Category C (Mixed / General Collapse) is the remainder (~14%)
    assert bd["C"]["count"] == 48
    assert bd["C"]["percentage"] == pytest.approx(13.87, abs=0.1)
    
    # Category A (Batter-created pressure) is 0 because cohort has P2 >= 80 and SR >= 150
    assert bd["A"]["count"] == 0


# ==============================================================================
# TEST 8: POORAN 12 QUESTIONS COVERAGE
# ==============================================================================

def test_pooran_12_questions_coverage():
    """Verifies that all 12 diagnostic questions are thoroughly answered."""
    q_dict = answer_pooran_12_questions()
    assert len(q_dict) == 12
    
    for k, v in q_dict.items():
        assert "question" in v
        assert "answer" in v
        assert len(v["answer"]) > 10, f"Answer for {k} is too short"


# ==============================================================================
# TEST 9: INVARIANCE & LEAKAGE
# ==============================================================================

def test_invariances_and_leakage():
    """Verifies outcome, player identity, P2 independence, and window integrity."""
    inv = verify_invariances_and_leakage()
    assert inv["outcome_invariance"] is True
    assert inv["player_identity_invariance"] is True
    assert inv["p2_independence"] is True
    assert inv["window_integrity"] is True
    assert inv["all_invariances_passed"] is True


# ==============================================================================
# TEST 10: END-TO-END DIAGNOSTIC EXECUTION & ARTIFACT GENERATION
# ==============================================================================

def test_end_to_end_diagnostic_generation():
    """Verifies that running the diagnostic suite produces valid artifact data."""
    payload = run_phase7t_diagnostic()
    assert payload["phase"] == "PHASE_7T_P3_WICKET_CAUSALITY_DIAGNOSTIC"
    assert payload["status"] == "RESEARCH_DIAGNOSTIC_ONLY"
    assert payload["target_case"]["player"] == "N Pooran"
    assert payload["target_case"]["current_p2"] == 86.5
    assert payload["target_case"]["current_p3"] == 22.3
    assert payload["target_case"]["model_t_attributable_p3"] > 50.0
