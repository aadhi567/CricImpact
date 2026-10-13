"""
Phase 7G: Unit and Regression Tests for P3 Corrections & P1 Leverage Coupling.
Validates:
1. Issue 1: Death-Over RRR Blowout Correction (Real & Synthetic)
2. Issue 2: Partner Coattail Dampening (Real & Synthetic)
3. Issue 3: Low-Target Chase Execution Gating (Real & Synthetic)
4. Context-as-Leverage Architecture Invariants
5. Strict Outcome Invariance (Zero Leakage)
6. DNB & Edge-Case Handling
7. 18 Mandatory Stress Scenarios
"""
import pytest
import numpy as np
import pandas as pd
from typing import Dict, Any

from src.phase7g_simulation import compute_corrected_p3, compute_phase7g_contribution
from src.phase7f_leverage_simulation import leverage_model_a_linear


from pathlib import Path


@pytest.fixture(scope="module")
def df_matches():
    bak = Path("data/processed/batter_match_contributions_v7d_backup.csv")
    csv_path = str(bak) if bak.exists() else "data/processed/batter_match_contributions.csv"
    df = pd.read_csv(csv_path, low_memory=False)
    return df


class TestIssue1DeathRRRBlowout:
    """Issue 1: Test that high-SR batting in dying chases is not crushed by asymptotic RRR."""

    def test_russell_real_match_death_blowout_relief(self, df_matches):
        # AD Russell 65 off 25, SR 260.0 in lost chase (M1178410)
        row = df_matches[(df_matches["player"] == "AD Russell") & (df_matches["match_id"] == 1178410)].iloc[0]
        res_base = compute_phase7g_contribution(row, death_rrr_mode="baseline")
        res_corr = compute_phase7g_contribution(row, death_rrr_mode="mode_1a_sr_capped")

        # Baseline P3 is severely depressed (18.6)
        assert res_base["p3_score"] == 18.6
        # Corrected P3 is restored to above-par (> 50)
        assert res_corr["p3_score"] >= 55.0
        # Contribution score reflects heroics (> 75)
        assert res_corr["contribution_score"] >= 78.0

    def test_poor_death_batter_remains_penalized(self):
        # Poor death batter: 8 off 12 balls, SR 66.7, RRR worsening
        row = {
            "innings": 2,
            "balls_faced": 12,
            "actual_runs": 8,
            "actual_sr": 66.7,
            "balls_remaining_exit": 9,
            "required_rr_change": -16.0,
            "target_progress_change": 0.04,
            "partnership_runs": 12,
            "batter_partnership_share": 0.67,
            "partner_runs": 4,
            "overs_spent": 2.5,
            "score_context": 75.0,
            "score_perf": 22.0,
            "wickets_remaining_exit": 4,
        }
        res_base = compute_phase7g_contribution(row, death_rrr_mode="baseline")
        res_corr = compute_phase7g_contribution(row, death_rrr_mode="mode_1a_sr_capped")

        # Both baseline and corrected must heavily penalize poor death batting
        assert res_corr["p3_score"] <= 15.0
        assert res_corr["contribution_score"] <= 15.0
        # Correction does not offer unearned relief to slow batters
        assert abs(res_corr["p3_score"] - res_base["p3_score"]) < 1.0


class TestIssue2PartnerCoattail:
    """Issue 2: Test that batters free-riding on explosive partners have P3 properly dampened."""

    def test_dhawan_real_match_coattail_dampened(self, df_matches):
        # S Dhawan 29 off 30 while Warner hits 126 off 59 (M1082627)
        row = df_matches[(df_matches["player"] == "S Dhawan") & (df_matches["match_id"] == 1082627)].iloc[0]
        res_base = compute_phase7g_contribution(row, coattail_mode="baseline")
        res_corr = compute_phase7g_contribution(row, coattail_mode="mode_2c_hybrid")

        # Uncorrected baseline gave absurd P3 = 92.0
        assert res_base["p3_score"] == 92.0
        # Corrected P3 is dampened to par range [50, 60]
        assert 50.0 <= res_corr["p3_score"] <= 58.0
        # Contribution score is close to par [50, 56]
        assert 50.0 <= res_corr["contribution_score"] <= 55.0

    def test_carrying_batter_preserves_full_credit(self):
        # Carrying batter: 50 off 33 (SR 151.5) while partner makes 24 off 30 (SR 80.0)
        row = {
            "innings": 2,
            "balls_faced": 33,
            "actual_runs": 50,
            "actual_sr": 151.5,
            "required_rr_change": 1.7,
            "target_progress_change": 0.35,
            "partnership_runs": 74,
            "batter_partnership_share": 0.676,
            "partner_runs": 24,
            "overs_spent": 10.5,
            "score_context": 49.6,
            "score_perf": 80.2,
            "wickets_remaining_exit": 7,
        }
        res_base = compute_phase7g_contribution(row, coattail_mode="baseline")
        res_corr = compute_phase7g_contribution(row, coattail_mode="mode_2c_hybrid")

        # Carrying batter must not be dampened
        assert res_corr["p3_score"] >= 80.0
        assert abs(res_corr["p3_score"] - res_base["p3_score"]) < 1.0


class TestIssue3LowTargetChase:
    """Issue 3: Test that low-target cruise control does not inflate slow batting."""

    def test_smith_real_match_low_target_pace_cap(self, df_matches):
        # SPD Smith 15 off 18 (SR 83.3) chasing 94 (M1082645)
        row = df_matches[(df_matches["player"] == "SPD Smith") & (df_matches["match_id"] == 1082645)].iloc[0]
        res_base = compute_phase7g_contribution(row, low_target_mode="baseline")
        res_corr = compute_phase7g_contribution(row, low_target_mode="mode_3c_pace_cap")

        # Baseline inflated P3 to 68.2
        assert res_base["p3_score"] == 68.2
        # Corrected P3 is restricted to par/sub-par (< 50)
        assert res_corr["p3_score"] <= 48.0
        # Final contribution is appropriately modest (<= 50)
        assert res_corr["contribution_score"] <= 50.0

    def test_aggressive_finisher_in_low_target_retains_high_score(self):
        # Finisher hitting 32 off 14 (SR 228.6) to finish low target
        row = {
            "innings": 2,
            "target": 94,
            "balls_faced": 14,
            "actual_runs": 32,
            "actual_sr": 228.6,
            "required_rr_entry": 4.5,
            "required_rr_exit": 0.0,
            "required_rr_change": 4.5,
            "target_progress_change": 0.34,
            "partnership_runs": 38,
            "batter_partnership_share": 0.842,
            "partner_runs": 6,
            "overs_spent": 2.8,
            "score_context": 24.0,
            "score_perf": 82.0,
            "wickets_remaining_exit": 8,
        }
        res_corr = compute_phase7g_contribution(row, low_target_mode="mode_3c_pace_cap")
        # Aggressive batter is not throttled
        assert res_corr["p3_score"] >= 75.0
        assert res_corr["contribution_score"] >= 70.0


class TestArchitecturalInvariants:
    """Test leverage bounds, score bounds, DNB logic, and outcome invariance."""

    def test_leverage_bounds(self):
        # Range of P1 values from 0 to 100
        for p1 in np.linspace(0, 100, 101):
            lev = leverage_model_a_linear(p1)
            assert 0.65 <= lev <= 1.35
        # Par P1 = 50 gives exactly 1.0
        assert abs(leverage_model_a_linear(50.0) - 1.0) < 1e-6

    def test_score_clip_bounds(self):
        # Extreme positive
        row_max = {
            "innings": 1, "balls_faced": 60, "actual_runs": 160, "actual_sr": 266.7,
            "score_context": 95.0, "score_perf": 99.9, "expected_final_change": 60.0,
            "trajectory_deviation_change": 30.0, "team_rr_entry": 0.0, "window_team_rr": 16.0,
            "partnership_runs": 180, "batter_partnership_share": 0.89, "partner_runs": 20,
            "overs_spent": 10.0, "wickets_remaining_exit": 9,
        }
        res_max = compute_phase7g_contribution(row_max)
        assert res_max["contribution_score"] <= 99.9

        # Extreme negative
        row_min = {
            "innings": 1, "balls_faced": 25, "actual_runs": 3, "actual_sr": 12.0,
            "score_context": 95.0, "score_perf": 0.1, "expected_final_change": -40.0,
            "trajectory_deviation_change": -25.0, "team_rr_entry": 8.0, "window_team_rr": 1.5,
            "partnership_runs": 10, "batter_partnership_share": 0.3, "partner_runs": 7,
            "overs_spent": 6.0, "wickets_remaining_exit": 5, "wickets_lost_during_stay": 4,
        }
        res_min = compute_phase7g_contribution(row_min)
        assert res_min["contribution_score"] >= 0.1

    def test_dnb_preservation(self):
        row_dnb = {"dnb": True, "balls_faced": np.nan, "actual_runs": np.nan}
        res_dnb = compute_phase7g_contribution(row_dnb)
        assert res_dnb["dnb"] is True
        assert res_dnb["contribution_score"] is None
        assert res_dnb["p3_score"] is None
        assert res_dnb["leverage"] is None

    def test_outcome_invariance(self):
        # Adding match outcome fields must have 0.000 effect on calculation
        base_row = {
            "innings": 2, "balls_faced": 30, "actual_runs": 55, "actual_sr": 183.3,
            "target": 180, "required_rr_change": 2.5, "target_progress_change": 0.30,
            "partnership_runs": 70, "batter_partnership_share": 0.78, "partner_runs": 15,
            "overs_spent": 5.0, "score_context": 55.0, "score_perf": 82.0,
            "wickets_remaining_exit": 7, "balls_remaining_exit": 20,
        }
        res_clean = compute_phase7g_contribution(base_row)

        win_row = base_row.copy()
        win_row.update({"won_match": True, "match_winner": "Team A", "win_margin": 20})
        res_win = compute_phase7g_contribution(win_row)

        loss_row = base_row.copy()
        loss_row.update({"won_match": False, "match_winner": "Team B", "win_margin": -5})
        res_loss = compute_phase7g_contribution(loss_row)

        assert res_clean["contribution_score"] == res_win["contribution_score"]
        assert res_clean["contribution_score"] == res_loss["contribution_score"]
        assert res_clean["p3_score"] == res_win["p3_score"]
        assert res_clean["p3_score"] == res_loss["p3_score"]


class TestStressScenarios:
    """Verifies that all 18 stress scenarios execute cleanly without errors."""

    def test_all_18_stress_scenarios(self):
        from scripts.run_phase7g_evaluation import test_18_stress_tests
        results = test_18_stress_tests()
        assert len(results) == 18
        for r in results:
            if r["dnb"]:
                assert r["candidate_1_score"] is None
            else:
                assert 0.1 <= r["candidate_1_score"] <= 99.9
                assert 0.1 <= r["candidate_1_p3"] <= 99.9
