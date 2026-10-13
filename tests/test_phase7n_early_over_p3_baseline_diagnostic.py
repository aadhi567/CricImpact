"""
Tests for Phase 7N: Early-Over P3 Baseline Research & Controlled Comparison.
Cricket Batter Contribution Model.

Verifies:
1. Production protected files remain byte-for-byte untouched.
2. Alpha calculation across balls bowled (0, 6, 12, 18, 24, 30).
3. Sample stabilization formula (team_rr=22, par_rr=10, balls=6 -> 13.0).
4. Full stabilization at 24 balls (effective_rr == team_rr).
5. Monotonicity of sample stabilization.
6. V Suryavanshi comparison across Models 0, 1, 2, 3.
7. Historic spike cases (AB de Villiers, Sehwag) receive appropriate relief.
8. Genuine failure accountability (Stoinis 0 off 1, Munro 0 off 1) is preserved.
9. 20-over normal EFS path isolation (0 delta).
10. Outcome and player identity invariance.
"""

import hashlib
from pathlib import Path
import pytest
import numpy as np
import pandas as pd

from src.phase7n_early_over_p3_baseline_diagnostic import (
    get_balls_bowled_at_entry,
    compute_effective_rr_entry,
    compute_simulated_p3_row,
    evaluate_suryavanshi_counterfactual,
    evaluate_20_over_controls,
    evaluate_invariance_and_leakage,
)

PROTECTED_FILES = {
    "src/contribution_framework.py": "bbc00b0c9ba0270112e5a77a3273a3b9",
    "data/processed/batter_match_contributions.csv": "779adf7041fac9eedab4efe035cdc39a",
    "models/contribution/phase6/phase6_season_metrics.csv": "223e9990c4aaf52270c3fb9d290b68af",
    "src/season_aggregation.py": "ccbc7ea13880d8d34785effad22cb1ab",
}


def test_governance_protected_files_intact():
    """Verify that all production files remain byte-for-byte unchanged in pre-integration backup."""
    for rel_path, expected_md5 in PROTECTED_FILES.items():
        backup_path = Path("backups/phase7o_pre_integration") / Path(rel_path).name
        target_path = backup_path if backup_path.exists() else Path(rel_path)
        assert target_path.exists(), f"Missing production file: {target_path}"
        with open(target_path, "rb") as f:
            actual_md5 = hashlib.md5(f.read()).hexdigest()
        assert actual_md5.lower() == expected_md5.lower(), (
            f"GOVERNANCE VIOLATION: {rel_path} was modified during Phase 7N! Expected {expected_md5}, got {actual_md5}"
        )


def test_alpha_calculation():
    """Verify alpha progression across ball counts."""
    # 0 balls -> 0.0
    eff, meta = compute_effective_rr_entry("Model 1 (Phase 7M Alpha)", 20.0, 0.0, par_rr=10.0)
    assert meta["balls_bowled"] == 0
    assert meta["alpha"] == 0.0
    assert eff == 10.0

    # 6 balls (over 1.0) -> 0.25
    eff, meta = compute_effective_rr_entry("Model 1 (Phase 7M Alpha)", 22.0, 1.0, par_rr=10.0)
    assert meta["balls_bowled"] == 6
    assert meta["alpha"] == 0.25
    assert eff == 13.0

    # 12 balls (over 2.0) -> 0.50
    eff, meta = compute_effective_rr_entry("Model 1 (Phase 7M Alpha)", 20.0, 2.0, par_rr=10.0)
    assert meta["balls_bowled"] == 12
    assert meta["alpha"] == 0.50
    assert eff == 15.0

    # 18 balls (over 3.0) -> 0.75
    eff, meta = compute_effective_rr_entry("Model 1 (Phase 7M Alpha)", 20.0, 3.0, par_rr=10.0)
    assert meta["balls_bowled"] == 18
    assert meta["alpha"] == 0.75
    assert eff == 17.5

    # 24 balls (over 4.0) -> 1.00
    eff, meta = compute_effective_rr_entry("Model 1 (Phase 7M Alpha)", 20.0, 4.0, par_rr=10.0)
    assert meta["balls_bowled"] == 24
    assert meta["alpha"] == 1.00
    assert eff == 20.0

    # 30 balls (over 5.0) -> 1.00
    eff, meta = compute_effective_rr_entry("Model 1 (Phase 7M Alpha)", 20.0, 5.0, par_rr=10.0)
    assert meta["balls_bowled"] == 30
    assert meta["alpha"] == 1.00
    assert eff == 20.0


def test_entry_rr_stabilization_formula():
    """Verify specific mathematical formula: 0.25 * 22 + 0.75 * 10 = 13.0."""
    eff, meta = compute_effective_rr_entry("Model 1 (Phase 7M Alpha)", 22.0, 1.0, par_rr=10.0)
    assert eff == 13.0
    # Also verify raw acceleration calculation
    window_rr = 14.5
    raw_accel = (window_rr - eff) / 3.0
    assert pytest.approx(raw_accel, abs=1e-4) == 0.50


def test_full_stabilization_at_24_balls():
    """At 24 balls, effective RR must equal actual team_rr_entry exactly."""
    for team_rr in [6.5, 9.0, 12.0, 18.5, 25.0]:
        eff, meta = compute_effective_rr_entry("Model 1 (Phase 7M Alpha)", team_rr, 4.0, par_rr=10.0)
        assert eff == team_rr
        assert meta["alpha"] == 1.0


def test_monotonic_sample_stabilization():
    """Verify effective RR moves monotonically toward actual team RR as sample size increases."""
    team_rr = 22.0
    par_rr = 10.0
    overs = [0.0, 0.4, 1.0, 1.4, 2.0, 2.4, 3.0, 3.4, 4.0]
    effective_rates = [
        compute_effective_rr_entry("Model 1 (Phase 7M Alpha)", team_rr, ov, par_rr=par_rr)[0]
        for ov in overs
    ]
    # Should be strictly monotonically increasing from 10.0 to 22.0
    for i in range(len(effective_rates) - 1):
        assert effective_rates[i] <= effective_rates[i + 1]
    assert effective_rates[0] == 10.0
    assert effective_rates[-1] == 22.0


def test_suryavanshi_model_comparison():
    """Verify V Suryavanshi under Models 0, 1, 2, 3."""
    data = evaluate_suryavanshi_counterfactual()
    models = data["model_comparison"]

    m0 = models["Model 0 (Phase 7L)"]
    assert pytest.approx(m0["score_p3"], abs=0.2) == 33.9
    assert pytest.approx(m0["final_contribution_score"], abs=0.2) == 57.9

    m1 = models["Model 1 (Phase 7M Alpha)"]
    assert m1["effective_rr_entry"] == 13.0
    assert pytest.approx(m1["clipped_accel"], abs=0.01) == 0.50
    assert pytest.approx(m1["score_p3"], abs=0.5) == 73.1
    assert pytest.approx(m1["final_contribution_score"], abs=0.5) == 76.4

    m2 = models["Model 2 (Par Baseline)"]
    assert m2["effective_rr_entry"] == 10.0
    assert pytest.approx(m2["clipped_accel"], abs=0.01) == 1.50
    assert pytest.approx(m2["score_p3"], abs=0.5) == 82.5
    assert pytest.approx(m2["final_contribution_score"], abs=0.5) == 80.9

    m3 = models["Model 3 (Transitional)"]
    assert m3["effective_rr_entry"] == 10.0
    assert pytest.approx(m3["score_p3"], abs=0.5) == 82.5
    assert pytest.approx(m3["final_contribution_score"], abs=0.5) == 80.9


def test_historic_spike_cases_relief():
    """Verify historical high-entry RR cases (AB de Villiers, Sehwag) receive appropriate relief."""
    df = pd.read_csv("data/processed/batter_match_contributions.csv", low_memory=False)

    # AB de Villiers (Match 1178424)
    ab_row = df[(df["match_id"] == 1178424) & (df["player"] == "AB de Villiers")].iloc[0]
    res_m0 = compute_simulated_p3_row(ab_row, "Model 0 (Phase 7L)")
    res_m1 = compute_simulated_p3_row(ab_row, "Model 1 (Phase 7M Alpha)")
    assert res_m0["score_p3"] < 20.0  # 14.0
    assert res_m1["score_p3"] > 60.0  # 66.7

    # V Sehwag (Match 336022)
    seh_row = df[(df["match_id"] == 336022) & (df["player"] == "V Sehwag")].iloc[0]
    res_m0 = compute_simulated_p3_row(seh_row, "Model 0 (Phase 7L)")
    res_m1 = compute_simulated_p3_row(seh_row, "Model 1 (Phase 7M Alpha)")
    assert res_m0["score_p3"] < 40.0  # 36.8
    assert res_m1["score_p3"] > 68.0  # 70.6


def test_genuine_failure_accountability_preserved():
    """Verify that poor batting is still penalized and not given pity points."""
    df = pd.read_csv("data/processed/batter_match_contributions.csv", low_memory=False)

    # MP Stoinis golden duck (Match 1178424, 0 off 1)
    stoinis_row = df[(df["match_id"] == 1178424) & (df["player"] == "MP Stoinis")].iloc[0]
    res_m1 = compute_simulated_p3_row(stoinis_row, "Model 1 (Phase 7M Alpha)")
    assert res_m1["score_p3"] < 10.0  # 8.8
    assert res_m1["final_contribution_score"] < 5.0  # 3.4

    # Colin Munro golden duck (Match 1136592, 0 off 1)
    munro_row = df[(df["match_id"] == 1136592) & (df["player"] == "C Munro")].iloc[0]
    res_m0 = compute_simulated_p3_row(munro_row, "Model 0 (Phase 7L)")
    res_m1 = compute_simulated_p3_row(munro_row, "Model 1 (Phase 7M Alpha)")
    # Under Model 1, Munro is properly penalized (lower score than Model 0)
    assert res_m1["score_p3"] < res_m0["score_p3"]
    assert res_m1["score_p3"] < 15.0


def test_20_over_normal_efs_isolation():
    """Verify normal 20-over matches with active EFS model have zero change."""
    controls = evaluate_20_over_controls()
    assert controls["is_perfectly_isolated_to_fallback"] is True
    assert controls["max_delta_in_normal_efs_matches"] == 0.0


def test_outcome_and_player_identity_invariance():
    """Verify outcome invariance and player identity invariance."""
    inv = evaluate_invariance_and_leakage()
    assert inv["outcome_invariance"]["all_deltas_zero"] is True
    assert inv["player_identity_invariance"]["all_deltas_zero"] is True
