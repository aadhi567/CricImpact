"""
Unit and Integration Tests for Phase 7P:
Vaibhav Suryavanshi P3 Chase-vs-First-Innings Diagnostic Audit.
"""

import sys
import json
import pytest
from pathlib import Path
import pandas as pd
import numpy as np

# Ensure repository root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.phase7p_vaibhav_p3_chase_diagnostic import (
    CASE_A_MATCH_ID,
    CASE_B_MATCH_ID,
    P3_STANDARDIZATION_MEAN,
    P3_STANDARDIZATION_STD,
    P3_STANDARDIZATION_SCALE,
    extract_entry_exit_state,
    decompose_p3_components,
    compute_case_scoring_summary,
    analyze_chase_mechanics,
    analyze_first_innings_mechanics,
    evaluate_double_counting_interaction,
    generate_side_by_side_comparison,
    run_counterfactual_simulations,
    run_population_level_audit,
    audit_window_integrity_and_leakage,
    audit_p2_p3_separation,
    classify_root_cause,
    evaluate_candidate_corrections,
)


@pytest.fixture(scope="module")
def df_contributions():
    path = Path("data/processed/batter_match_contributions.csv")
    assert path.exists(), f"Missing dataset: {path}"
    return pd.read_csv(path, low_memory=False)


@pytest.fixture(scope="module")
def row_case_a(df_contributions):
    sub = df_contributions[(df_contributions["player"] == "V Suryavanshi") & (df_contributions["match_id"] == CASE_A_MATCH_ID)]
    assert not sub.empty, "Case A (Match 1527676) not found in dataset."
    return sub.iloc[0]


@pytest.fixture(scope="module")
def row_case_b(df_contributions):
    sub = df_contributions[(df_contributions["player"] == "V Suryavanshi") & (df_contributions["match_id"] == CASE_B_MATCH_ID)]
    assert not sub.empty, "Case B (Match 1527682) not found in dataset."
    return sub.iloc[0]


# ==============================================================================
# 1. STATE RECONSTRUCTION TESTS
# ==============================================================================

def test_case_a_state_extraction(row_case_a):
    st = extract_entry_exit_state(row_case_a)
    assert st["match_id"] == CASE_A_MATCH_ID
    assert st["innings"] == 2
    
    # Entry
    assert st["entry_state"]["over"] == 0.2
    assert st["entry_state"]["team_score"] == 3.0
    assert st["entry_state"]["required_rr"] == pytest.approx(6.36, abs=0.01)
    assert st["entry_state"]["balls_remaining"] == 118
    assert st["entry_state"]["wickets_remaining"] == 10.0
    
    # Exit
    assert st["exit_state"]["over"] == 6.2
    assert st["exit_state"]["team_score"] == 75.0
    assert st["exit_state"]["required_rr"] == pytest.approx(3.88, abs=0.01)
    assert st["exit_state"]["balls_remaining"] == 82
    assert st["exit_state"]["wickets_remaining"] == 9.0
    
    # Batter window
    bw = st["batter_window"]
    assert bw["runs"] == 52.0
    assert bw["balls"] == 17
    assert bw["sr"] == pytest.approx(305.88, abs=0.01)
    assert bw["fours"] == 4
    assert bw["sixes"] == 5
    assert bw["team_runs_added"] == 72.0
    assert bw["partnership_share"] == pytest.approx(0.693, abs=0.01)


def test_case_b_state_extraction(row_case_b):
    st = extract_entry_exit_state(row_case_b)
    assert st["match_id"] == CASE_B_MATCH_ID
    assert st["innings"] == 1
    
    # Entry
    assert st["entry_state"]["over"] == 0.1
    assert st["entry_state"]["team_score"] == 1.0
    assert st["entry_state"]["team_rr"] == pytest.approx(6.0, abs=0.01)
    assert st["entry_state"]["efs"] == pytest.approx(169.7, abs=0.1)
    assert st["entry_state"]["balls_remaining"] == 119
    assert st["entry_state"]["wickets_remaining"] == 10.0
    
    # Exit
    assert st["exit_state"]["over"] == 6.2
    assert st["exit_state"]["team_score"] == 70.0
    assert st["exit_state"]["team_rr"] == pytest.approx(11.05, abs=0.05)
    assert st["exit_state"]["efs"] == pytest.approx(213.1, abs=0.1)
    assert st["exit_state"]["balls_remaining"] == 82
    assert st["exit_state"]["wickets_remaining"] == 9.0
    
    # Batter window
    bw = st["batter_window"]
    assert bw["runs"] == 31.0
    assert bw["balls"] == 18
    assert bw["sr"] == pytest.approx(172.22, abs=0.01)
    assert bw["team_runs_added"] == 69.0
    assert bw["partnership_share"] == pytest.approx(0.443, abs=0.01)


# ==============================================================================
# 2. P3 MATHEMATICAL COMPONENT DECOMPOSITION TESTS
# ==============================================================================

def test_case_a_p3_decomposition(row_case_a):
    decomp = decompose_p3_components(row_case_a)
    assert decomp["innings"] == 2
    comp = decomp["components"]
    
    # Chase metrics
    assert comp["rrr_change"] == pytest.approx(2.48, abs=0.01)
    assert comp["z_rrr"] == pytest.approx(2.48 / 3.0, abs=1e-4)
    assert comp["term_rrr_weighted (50%)"] == pytest.approx(0.50 * (2.48 / 3.0), abs=1e-4)
    
    assert comp["rr_gap_change"] == pytest.approx(5.32, abs=0.01)
    assert comp["z_gap"] == pytest.approx(5.32 / 3.0, abs=1e-4)
    assert comp["term_gap_weighted (25%)"] == pytest.approx(0.25 * (5.32 / 3.0), abs=1e-4)
    
    assert comp["target_progress_change"] == pytest.approx(0.5625, abs=1e-4)
    assert comp["z_prog"] == pytest.approx((0.5625 - 0.15) / 0.15, abs=1e-4)
    assert comp["term_prog_weighted (25%)"] == pytest.approx(0.25 * ((0.5625 - 0.15) / 0.15), abs=1e-4)
    
    assert comp["s_res_resource_tradeoff"] == pytest.approx(-0.09318, abs=1e-4)
    assert decomp["raw_p3"] == pytest.approx(1.4510, abs=1e-3)
    assert decomp["normalization"]["score_state"] == pytest.approx(76.8, abs=0.1)


def test_case_b_p3_decomposition(row_case_b):
    decomp = decompose_p3_components(row_case_b)
    assert decomp["innings"] == 1
    comp = decomp["components"]
    
    # 1st Innings metrics
    assert comp["efs_change_runs"] == pytest.approx(43.4, abs=0.1)
    assert comp["z_efs"] == pytest.approx(43.4 / 12.0, abs=1e-4)
    assert comp["term_efs_weighted (50%)"] == pytest.approx(0.50 * (43.4 / 12.0), abs=1e-4)
    
    assert comp["trajectory_deviation_change"] == pytest.approx(20.2, abs=0.1)
    assert comp["z_traj"] == pytest.approx(20.2 / 10.0, abs=1e-4)
    assert comp["term_traj_weighted (25%)"] == pytest.approx(0.25 * (20.2 / 10.0), abs=1e-4)
    
    assert comp["scoring_acceleration"] == pytest.approx((11.18 - 6.0) / 3.0, abs=0.01)
    assert comp["term_accel_weighted (25%)"] == pytest.approx(0.25 * ((11.18 - 6.0) / 3.0), abs=0.01)
    
    assert comp["s_res_resource_tradeoff"] == pytest.approx(-0.09318, abs=1e-4)
    assert decomp["raw_p3"] == pytest.approx(2.6518, abs=1e-3)
    assert decomp["normalization"]["score_state"] == pytest.approx(90.9, abs=0.1)


def test_dynamic_wicket_resource_equivalence(row_case_a, row_case_b):
    dp_a = decompose_p3_components(row_case_a)
    dp_b = decompose_p3_components(row_case_b)
    
    res_a = dp_a["res_tradeoff"]
    res_b = dp_b["res_tradeoff"]
    
    # Both lost 1 wicket in over 6.2 with 82 balls and 9 wickets remaining
    assert res_a["balls_remaining_exit"] == res_b["balls_remaining_exit"] == 82.0
    assert res_a["wickets_remaining_exit"] == res_b["wickets_remaining_exit"] == 9.0
    assert res_a["base_cost"] == pytest.approx(res_b["base_cost"], abs=1e-5)
    
    # Both hit the max 70% explosive run offset cap
    assert res_a["explosive_offset"] == pytest.approx(res_a["base_cost"] * 0.7, abs=1e-5)
    assert res_b["explosive_offset"] == pytest.approx(res_b["base_cost"] * 0.7, abs=1e-5)
    assert res_a["s_res"] == pytest.approx(res_b["s_res"], abs=1e-5)
    assert res_a["s_res"] == pytest.approx(-0.09318, abs=1e-4)


# ==============================================================================
# 3. LEVERAGE, ADJUSTMENTS, & DOUBLE COUNTING TESTS
# ==============================================================================

def test_p1_leverage_and_final_scoring(row_case_a, row_case_b):
    sc_a = compute_case_scoring_summary(row_case_a)
    sc_b = compute_case_scoring_summary(row_case_b)
    
    # Case A
    assert sc_a["score_perf_p2"] == 96.8
    assert sc_a["score_state_p3"] == 76.8
    assert sc_a["c_chase"] == pytest.approx(34.8, abs=0.2)
    assert sc_a["c_eff"] == pytest.approx(34.9, abs=0.2)
    assert sc_a["leverage"] == pytest.approx(0.885, abs=0.01)
    assert sc_a["adjusted_p2"] == pytest.approx(91.4, abs=0.5)
    assert sc_a["adjusted_p3"] == pytest.approx(73.7, abs=0.5)
    assert sc_a["final_score"] == pytest.approx(82.6, abs=0.2)
    
    # Case B
    assert sc_b["score_perf_p2"] == 77.4
    assert sc_b["score_state_p3"] == 90.9
    assert sc_b["c_chase"] == 50.0  # 1st innings neutral early-over
    assert sc_b["c_eff"] == pytest.approx(40.2, abs=0.2)
    assert sc_b["leverage"] == pytest.approx(0.926, abs=0.01)
    assert sc_b["adjusted_p2"] == pytest.approx(75.4, abs=0.5)
    assert sc_b["adjusted_p3"] == pytest.approx(87.9, abs=0.5)
    assert sc_b["final_score"] == pytest.approx(81.6, abs=0.2)


def test_double_counting_interaction(row_case_a, row_case_b):
    dc = evaluate_double_counting_interaction(row_case_a, row_case_b)
    assert dc["is_double_counted"] is True
    assert dc["case_a_leverage"] < 1.0
    assert dc["case_a_p3_lost_to_leverage"] > 3.0  # Erased 3.1 points from P3


# ==============================================================================
# 4. COUNTERFACTUAL SIMULATION TESTS
# ==============================================================================

def test_counterfactual_scenarios(row_case_a, row_case_b):
    cfs = run_counterfactual_simulations(row_case_a, row_case_b)
    
    # CF A: Case A evaluated as 1st innings knock
    cf_a = cfs["counterfactual_a_case_a_as_inn1"]
    assert cf_a["p3"] > 88.0  # P3 jumps to ~90.2
    assert cf_a["final_score"] > 88.0  # Final score jumps to ~89.9
    
    # CF E: Case B evaluated as 180 chase
    cf_e = cfs["counterfactual_e_case_b_as_chase"]
    assert cf_e["p3"] < 70.0  # P3 drops from 90.9 to ~67.7
    assert cf_e["final_score"] < 72.0  # Final score drops from 81.6 to ~69.6
    
    # CF B & C: Holding RRR or Team RR constant
    cf_b = cfs["counterfactual_b_hold_rrr_constant"]
    assert cf_b["p3"] < 70.0  # Without RRR reduction, P3 drops to 65.1
    
    cf_c = cfs["counterfactual_c_hold_team_rr_constant"]
    assert cf_c["p3"] < 75.0  # Without team RR acceleration, P3 drops to 72.6
    
    # CF D: Monotonic response to RRR relief
    cf_d = cfs["counterfactual_d_vary_rrr_relief"]
    p3_d_low = cf_d["rrr_relief_0.5"]["p3"]
    p3_d_mid = cf_d["rrr_relief_2.48"]["p3"]
    p3_d_high = cf_d["rrr_relief_8.0"]["p3"]
    assert p3_d_low < p3_d_mid < p3_d_high


# ==============================================================================
# 5. POPULATION AUDIT & LEAKAGE INVARIANCE TESTS
# ==============================================================================

def test_population_audit_properties(df_contributions):
    pop = run_population_level_audit(df_contributions)
    
    # Powerplay openers with SR >= 200 and balls >= 15
    pp = pop["powerplay_openers_comparison"]
    assert pp["inn1_count"] >= 80
    assert pp["inn2_count"] >= 100
    assert pp["inn1_mean_p3"] > 90.0
    assert pp["inn2_mean_p3"] < 80.0
    # Systematic P3 gap of ~15-16 points
    assert pp["p3_gap"] > 14.0
    
    # Correlation between P2 and P3 is lower in chases due to target-scale compression
    ov = pop["overall_distribution"]
    assert ov["corr_p2_p3_inn1"] > ov["corr_p2_p3_inn2"]


def test_window_integrity_and_zero_leakage(row_case_a, row_case_b):
    leak = audit_window_integrity_and_leakage(row_case_a, row_case_b)
    assert leak["leakage_audit_passed"] is True
    for t in leak["tests"]:
        assert t["passed_zero_leakage"] is True
        assert t["difference"] == 0.0


def test_p2_p3_metric_separation(row_case_a, row_case_b):
    sep = audit_p2_p3_separation(row_case_a, row_case_b)
    # Direct batter runs are only used in s_res offset, not in macro trajectory
    assert "actual_runs" in sep["p2_metrics"]
    assert "expected_final_change" in sep["p3_metrics_inn1"]
    assert "required_rr_change" in sep["p3_metrics_inn2"]


def test_root_cause_classification():
    rc = classify_root_cause()
    assert rc["classification"].startswith("C.")
    assert "contextual imbalance specifically affecting chases" in rc["classification"]


# ==============================================================================
# 6. CANDIDATE CORRECTIONS EVALUATION TESTS
# ==============================================================================

def test_candidate_corrections_evaluation(row_case_a, row_case_b):
    cand = evaluate_candidate_corrections(row_case_a, row_case_b)
    
    # 1st innings (Case B) must be 100% invariant
    assert cand["candidate_1_run_equivalent_relief"]["case_b"]["p3"] == 90.9
    assert cand["candidate_2_relative_rrr_relief"]["case_b"]["p3"] == 90.9
    assert cand["candidate_3_target_progress_rebalance"]["case_b"]["p3"] == 90.9
    
    # Case A P3 should rise towards parity under candidate models
    c1_p3 = cand["candidate_1_run_equivalent_relief"]["case_a"]["p3"]
    c2_p3 = cand["candidate_2_relative_rrr_relief"]["case_a"]["p3"]
    c3_p3 = cand["candidate_3_target_progress_rebalance"]["case_a"]["p3"]
    
    assert c1_p3 >= 82.0
    assert c2_p3 >= 82.0
    assert c3_p3 >= 82.0


# ==============================================================================
# 7. GOVERNANCE TESTS
# ==============================================================================

def test_governance_files_exist_and_readable():
    for fpath in [
        "src/contribution_framework.py",
        "src/season_aggregation.py",
        "data/processed/batter_match_contributions.csv",
        "models/contribution/phase6/phase6_season_metrics.csv"
    ]:
        p = Path(fpath)
        assert p.exists(), f"Protected file missing: {fpath}"
        assert p.stat().st_size > 0, f"Protected file empty: {fpath}"
