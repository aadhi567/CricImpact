"""
Phase 7G: Unit and Regression Tests for P3 Corrections & P1 Leverage Stress Test.
Imports from isolated simulation module: src/phase7g_p3_correction_simulation.py

Validates:
1. Conceptual Invariants:
   - P1 = 50 -> L = 1.0, Adj P2 = P2, Adj P3 = P3
   - P2 = 50 & P3 = 50 -> Final = 50.0 for any P1
   - High P1 amplifies success and penalizes failure
   - Low P1 dampens success and dampens penalty
   - DNB strictly preserved as NULL
   - Outcome invariance (zero leakage)
2. Issue 1: Death-Over RRR Blowout Correction (Russell case & poor batter distinction)
3. Issue 2: Partner Coattail Effect & Supporting Anchor Distinction (Dhawan case & anchor preservation)
4. Issue 3: Low-Target Chase Artifact (Smith case & aggressive finisher preservation)
5. 15 Required Archetypes Execution
"""

import pytest
import numpy as np
import pandas as pd
from typing import Dict, Any

from src.phase7g_p3_correction_simulation import (
    leverage_model_a_linear,
    compute_corrected_p3,
    compute_phase7g_contribution,
)


from pathlib import Path


@pytest.fixture(scope="module")
def df_matches():
    bak = Path("data/processed/batter_match_contributions_v7d_backup.csv")
    csv_path = str(bak) if bak.exists() else "data/processed/batter_match_contributions.csv"
    df = pd.read_csv(csv_path, low_memory=False)
    return df


class TestConceptualInvariants:
    """Verifies the core architectural invariants of Context-as-Leverage."""

    def test_par_p1_produces_unit_leverage(self):
        # P1 = 50 -> L(P1) = 1.0
        assert abs(leverage_model_a_linear(50.0) - 1.0) < 1e-6

    def test_par_p2_p3_produces_50_for_all_p1(self):
        # P2 = 50 and P3 = 50 -> Final = 50.0 regardless of P1
        for test_p1 in [0.0, 10.0, 25.0, 37.3, 50.0, 75.0, 89.2, 100.0]:
            lev = leverage_model_a_linear(test_p1)
            adj_p2 = float(np.clip(50.0 + (50.0 - 50.0) * lev, 0.1, 99.9))
            adj_p3 = float(np.clip(50.0 + (50.0 - 50.0) * lev, 0.1, 99.9))
            final = 0.50 * adj_p2 + 0.50 * adj_p3
            assert abs(final - 50.0) < 1e-6

    def test_high_p1_amplifies_success_and_failure(self):
        # P1 = 85.0 -> L = 1.245
        lev = leverage_model_a_linear(85.0)
        assert lev > 1.0
        good_adj = 50.0 + (80.0 - 50.0) * lev
        bad_adj = 50.0 + (20.0 - 50.0) * lev
        assert good_adj > 80.0
        assert bad_adj < 20.0

    def test_low_p1_dampens_success_and_failure(self):
        # P1 = 15.0 -> L = 0.755
        lev = leverage_model_a_linear(15.0)
        assert lev < 1.0
        good_adj = 50.0 + (80.0 - 50.0) * lev
        bad_adj = 50.0 + (20.0 - 50.0) * lev
        assert good_adj < 80.0
        assert bad_adj > 20.0

    def test_dnb_preservation(self):
        res = compute_phase7g_contribution({"dnb": True, "balls_faced": np.nan, "actual_runs": np.nan})
        assert res["dnb"] is True
        assert res["contribution_score"] is None
        assert res["adj_p2"] is None
        assert res["adj_p3"] is None
        assert res["leverage"] is None

    def test_outcome_invariance(self):
        row = {
            "innings": 2, "balls_faced": 25, "actual_runs": 45, "actual_sr": 180.0,
            "target": 175, "required_rr_change": 2.0, "target_progress_change": 0.25,
            "partnership_runs": 60, "batter_partnership_share": 0.75, "partner_runs": 15,
            "overs_spent": 4.5, "score_context": 55.0, "score_perf": 80.0,
            "wickets_remaining_exit": 7, "balls_remaining_exit": 25,
        }
        res_neutral = compute_phase7g_contribution(row)
        res_win = compute_phase7g_contribution({**row, "won_match": True, "win_margin": 15})
        res_loss = compute_phase7g_contribution({**row, "won_match": False, "win_margin": -15})
        assert res_neutral["contribution_score"] == res_win["contribution_score"]
        assert res_neutral["contribution_score"] == res_loss["contribution_score"]


class TestIssue1DeathRRRCorrections:
    """Validates Issue 1: Death-over RRR blowout solutions."""

    def test_russell_death_blowout_fixed(self, df_matches):
        # AD Russell 65 off 25, SR 260.0 in lost chase (Match 1178410)
        row = df_matches[(df_matches["player"] == "AD Russell") & (df_matches["match_id"] == 1178410)].iloc[0]
        res_base = compute_phase7g_contribution(row, death_rrr_mode="baseline")
        res_corr = compute_phase7g_contribution(row, death_rrr_mode="mode_1a_sr_capped")

        # Baseline was crushed to 18.6
        assert res_base["p3_score"] == 18.6
        # Mode 1A restores P3 to above-par (> 50) and contribution to elite tier (> 75)
        assert res_corr["p3_score"] >= 55.0
        assert res_corr["contribution_score"] >= 78.0

    def test_poor_death_batter_remains_heavily_penalized(self):
        # 8 off 12 balls, SR 66.7 in dying chase
        row = {
            "innings": 2, "balls_faced": 12, "actual_runs": 8, "actual_sr": 66.7,
            "balls_remaining_exit": 8, "required_rr_change": -18.0, "target_progress_change": 0.04,
            "partnership_runs": 12, "batter_partnership_share": 0.67, "partner_runs": 4,
            "overs_spent": 2.5, "score_context": 75.0, "score_perf": 22.0, "wickets_remaining_exit": 4,
        }
        res = compute_phase7g_contribution(row, death_rrr_mode="mode_1a_sr_capped")
        assert res["p3_score"] <= 15.0
        assert res["contribution_score"] <= 15.0


class TestIssue2PartnerCoattailCorrections:
    """Validates Issue 2: Partner coattail dampening while preserving supporting anchors."""

    def test_dhawan_coattail_dampened(self, df_matches):
        # S Dhawan 29 off 30 vs Warner 126 off 59 (Match 1082627)
        row = df_matches[(df_matches["player"] == "S Dhawan") & (df_matches["match_id"] == 1082627)].iloc[0]
        res_base = compute_phase7g_contribution(row, coattail_mode="baseline")
        res_corr = compute_phase7g_contribution(row, coattail_mode="mode_2d_anchor_aware")

        # Baseline was inflated to 92.0
        assert res_base["p3_score"] == 92.0
        # Corrected is brought down near par [48, 55]
        assert 48.0 <= res_corr["p3_score"] <= 55.0
        assert 48.0 <= res_corr["contribution_score"] <= 54.0

    def test_supporting_anchor_preserved(self):
        # Legitimate supporting anchor: 36 off 28 (SR 128.6) rotating strike while partner attacks at 180
        row = {
            "innings": 1, "entry_over": 5.2, "balls_faced": 28, "actual_runs": 36, "actual_sr": 128.6,
            "score_context": 42.0, "score_perf": 61.5, "expected_final_change": 22.0, "trajectory_deviation_change": 12.0,
            "team_rr_entry": 7.0, "window_team_rr": 9.8, "partnership_runs": 85, "batter_partnership_share": 0.424,
            "partner_runs": 49, "overs_spent": 8.5, "wickets_remaining_entry": 9, "wickets_remaining_exit": 8,
            "balls_remaining_entry": 88, "balls_remaining_exit": 37, "wicket_resource_change": -0.10,
        }
        res = compute_phase7g_contribution(row, coattail_mode="mode_2d_anchor_aware")
        # Anchor is preserved above par (> 60)
        assert res["p3_score"] >= 60.0
        assert res["contribution_score"] >= 60.0


class TestIssue3LowTargetChase:
    """Validates Issue 3: Low target pace cap."""

    def test_smith_low_target_pace_cap(self, df_matches):
        # SPD Smith 15 off 18 (SR 83.3) chasing 94 (Match 1082645)
        row = df_matches[(df_matches["player"] == "SPD Smith") & (df_matches["match_id"] == 1082645)].iloc[0]
        res_base = compute_phase7g_contribution(row, low_target_mode="baseline")
        res_corr = compute_phase7g_contribution(row, low_target_mode="mode_3c_pace_cap")

        # Baseline was inflated to 68.2
        assert res_base["p3_score"] == 68.2
        # Corrected is capped at or below par (<= 48.0)
        assert res_corr["p3_score"] <= 48.0
        assert res_corr["contribution_score"] <= 50.0

    def test_aggressive_finisher_in_low_target_retains_high_score(self):
        # 32 off 14 (SR 228.6) to finish low target
        row = {
            "innings": 2, "target": 94, "balls_faced": 14, "actual_runs": 32, "actual_sr": 228.6,
            "required_rr_entry": 4.5, "required_rr_exit": 0.0, "required_rr_change": 4.5,
            "target_progress_change": 0.34, "partnership_runs": 38, "batter_partnership_share": 0.842,
            "partner_runs": 6, "overs_spent": 2.8, "score_context": 24.0, "score_perf": 82.0,
            "wickets_remaining_exit": 8,
        }
        res = compute_phase7g_contribution(row, low_target_mode="mode_3c_pace_cap")
        assert res["p3_score"] >= 75.0
        assert res["contribution_score"] >= 70.0


class TestRequired15Archetypes:
    """Executes and verifies all 15 required archetypes."""

    def test_all_15_archetypes_run(self):
        from scripts.run_phase7g_full_audit import run_15_required_archetypes
        results = run_15_required_archetypes()
        assert len(results) == 15
        for r in results:
            if r["id"] == 15:
                assert r["final_50_50"] is None
            else:
                assert 0.1 <= r["final_50_50"] <= 99.9
                assert 0.65 <= r["leverage"] <= 1.35
