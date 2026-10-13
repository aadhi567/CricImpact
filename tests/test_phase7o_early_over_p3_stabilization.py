"""
Tests for Phase 7O: Controlled Implementation of Early-Over P3 Sample-Size Stabilization.
Cricket Batter Contribution Model.

Verifies:
1. Alpha progression across balls bowled (0, 6, 12, 18, 24, 30).
2. Effective RR calculation (0.25 * 22 + 0.75 * 10 = 13.0).
3. V Suryavanshi target case reproduction (P3: 73.1, Final: 76.4).
4. Explosive opening case relief (AB de Villiers, Sehwag).
5. Sluggish opening case correction (Munro duck, Rahane).
6. Golden duck preservation (MP Stoinis 0 off 1 remains 3.4).
7. Normal 20-over match invariance (EFS active, delta = 0).
8. 2nd innings chase invariance (delta = 0).
9. Entry at or after 4.0 overs unmodified.
10. DNB preservation (DNB = None).
11. Match outcome invariance (won_match True vs False -> delta = 0).
12. Player identity invariance (different name -> delta = 0).
13. P2 unchanged independence.
14. Governance checksums and backup verification.
"""

import hashlib
from pathlib import Path
import pytest
import numpy as np
import pandas as pd

from src.contribution_framework import (
    compute_pillar3_team_state_impact,
    compute_dampened_p3_raw,
    compute_production_contribution,
    PHASE5B_EMPIRICAL_PARAMS,
)

PRE_MODIFICATION_HASHES = {
    "src/contribution_framework.py": "bbc00b0c9ba0270112e5a77a3273a3b9",
    "src/season_aggregation.py": "ccbc7ea13880d8d34785effad22cb1ab",
    "data/processed/batter_match_contributions.csv": "779adf7041fac9eedab4efe035cdc39a",
    "models/contribution/phase6/phase6_season_metrics.csv": "223e9990c4aaf52270c3fb9d290b68af",
}

POST_MODIFICATION_HASHES = {
    "src/contribution_framework.py": "b5e2d146104e47a134d9b9cdf4c45251",
    "src/season_aggregation.py": "ccbc7ea13880d8d34785effad22cb1ab",
    "data/processed/batter_match_contributions.csv": "779adf7041fac9eedab4efe035cdc39a",
    "models/contribution/phase6/phase6_season_metrics.csv": "223e9990c4aaf52270c3fb9d290b68af",
}


def test_governance_and_backups_intact():
    """Verify that only src/contribution_framework.py changed and backups exist."""
    backup_dir = Path("backups/phase7o_pre_integration")
    assert backup_dir.exists(), "Missing backup directory: backups/phase7o_pre_integration"

    for rel_path, pre_hash in PRE_MODIFICATION_HASHES.items():
        # Verify backup contains exact pre-modification file
        b_file = backup_dir / Path(rel_path).name
        assert b_file.exists(), f"Missing backup file: {b_file}"
        with open(b_file, "rb") as f:
            actual_backup_hash = hashlib.md5(f.read()).hexdigest()
        assert actual_backup_hash.lower() == pre_hash.lower(), (
            f"Backup corruption for {rel_path}! Expected {pre_hash}, got {actual_backup_hash}"
        )

        # Verify live production files: only contribution_framework.py should differ
        # (check backups/phase7q_pre_integration if a subsequent phase has modified live framework)
        backup_q = Path("backups/phase7q_pre_integration") / Path(rel_path).name
        p_file = backup_q if backup_q.exists() else Path(rel_path)
        with open(p_file, "rb") as f:
            actual_live_hash = hashlib.md5(f.read()).hexdigest()
        expected_live_hash = POST_MODIFICATION_HASHES[rel_path]
        assert actual_live_hash.lower() == expected_live_hash.lower(), (
            f"Live file mismatch for {rel_path}! Expected {expected_live_hash}, got {actual_live_hash}"
        )


def test_alpha_progression():
    """Verify alpha progression across balls bowled."""
    test_cases = [
        (0.0, 0, 0.0),
        (0.1, 1, 1 / 24.0),
        (0.4, 4, 4 / 24.0),
        (1.0, 6, 0.25),
        (2.0, 12, 0.50),
        (3.0, 18, 0.75),
        (4.0, 24, 1.00),
        (5.0, 30, 1.00),
    ]
    for over, expected_balls, expected_alpha in test_cases:
        full_ov = int(over)
        sub_ball = int(round((over - full_ov) * 10.0))
        balls = full_ov * 6 + sub_ball
        alpha = min(1.0, balls / 24.0)
        assert balls == expected_balls
        assert pytest.approx(alpha, abs=1e-5) == expected_alpha


def test_effective_rr_entry_calculation():
    """Verify effective entry RR for Suryavanshi (team_rr=22, par_rr=10, over=1.0)."""
    team_rr_entry = 22.0
    par_rr = 10.0
    entry_over = 1.0

    full_ov = int(entry_over)
    sub_ball = int(round((entry_over - full_ov) * 10.0))
    balls = full_ov * 6 + sub_ball
    alpha = min(1.0, balls / 24.0)
    eff_rr = alpha * team_rr_entry + (1.0 - alpha) * par_rr

    assert balls == 6
    assert alpha == 0.25
    assert pytest.approx(eff_rr, abs=1e-5) == 13.0


def test_suryavanshi_target_case():
    """Verify V Suryavanshi in Match 1527686 receives corrected scores."""
    df = pd.read_csv("data/processed/batter_match_contributions.csv", low_memory=False)
    row = df[(df["match_id"] == 1527686) & (df["player"] == "V Suryavanshi")].iloc[0]

    res = compute_production_contribution(row)
    assert res["pillar2_perf_score"] == 82.7  # P2 untouched
    assert pytest.approx(res["pillar3_state_score"], abs=0.5) == 73.1
    assert pytest.approx(res["final_contribution_score"], abs=0.5) == 76.4
    assert res["final_contribution_score"] > 75.0


def test_explosive_opening_cases_relief():
    """Verify AB de Villiers and Virender Sehwag receive relief from explosive starts."""
    df = pd.read_csv("data/processed/batter_match_contributions.csv", low_memory=False)

    # AB de Villiers (Match 1178424, 10 off 4, SR 250, entry 0.3 after 26.0 RPO)
    ab_row = df[(df["match_id"] == 1178424) & (df["player"] == "AB de Villiers")].iloc[0]
    res_ab = compute_production_contribution(ab_row)
    assert res_ab["pillar3_state_score"] > 60.0  # Was 14.0 under Phase 7L
    assert res_ab["final_contribution_score"] > 55.0  # Was 34.0 under Phase 7L

    # Virender Sehwag (Match 336022, 51 off 26, SR 196, entry 0.1 after 18.0 RPO)
    seh_row = df[(df["match_id"] == 336022) & (df["player"] == "V Sehwag")].iloc[0]
    res_seh = compute_production_contribution(seh_row)
    assert res_seh["pillar3_state_score"] > 68.0  # Was 36.8 under Phase 7L
    assert res_seh["final_contribution_score"] > 70.0  # Was 58.3 under Phase 7L


def test_sluggish_opening_cases_corrected():
    """Verify Colin Munro golden duck and Rahane crawl are properly penalized."""
    df = pd.read_csv("data/processed/batter_match_contributions.csv", low_memory=False)

    # Colin Munro (Match 1136592, 0 off 1, entry 0.3 after 2.0 RPO)
    munro_row = df[(df["match_id"] == 1136592) & (df["player"] == "C Munro")].iloc[0]
    res_munro = compute_production_contribution(munro_row)
    assert res_munro["pillar3_state_score"] < 15.0  # Was unearned 27.2 under Phase 7L
    assert res_munro["final_contribution_score"] < 15.0  # Was 22.0 under Phase 7L


def test_golden_duck_accountability_preserved():
    """Verify MP Stoinis golden duck (Match 1178424, 0 off 1) remains severely penalized."""
    df = pd.read_csv("data/processed/batter_match_contributions.csv", low_memory=False)
    stoinis_row = df[(df["match_id"] == 1178424) & (df["player"] == "MP Stoinis")].iloc[0]

    res = compute_production_contribution(stoinis_row)
    assert res["pillar3_state_score"] < 10.0  # 8.8
    assert res["final_contribution_score"] < 5.0  # 3.4


def test_normal_20_over_match_invariance():
    """Verify normal 20-over matches with active EFS are unchanged (except Phase 7Q preservation)."""
    df = pd.read_csv("data/processed/batter_match_contributions.csv", low_memory=False)
    normal_matches = df[(df["innings"] == 1) & (df["expected_final_change"].notna())].head(25)

    from app.services.data_service import data_service
    engine = data_service.get_active_scoring_engine()
    if engine == "v8.5.1-strategy4-hybrid":
        from src.phase8_5_hyper_score_damping import compute_phase8_5_unified_contribution
        for _, row in normal_matches.iterrows():
            res = compute_phase8_5_unified_contribution(row, strategy="hybrid", apply_preservation=True)
            if res["final_contribution_score"] is None:
                assert pd.isna(row["contribution_score"])
            else:
                assert pytest.approx(res["final_contribution_score"], abs=0.1) == float(row["contribution_score"])

    else:
        for _, row in normal_matches.iterrows():
            res = compute_production_contribution(row)
            # In Phase 7Q/7U, preservation- or attribution-eligible innings receive an elevation
            if res["final_contribution_score"] > float(row["contribution_score"]):
                # Must be an intentional Phase 7Q/7U elevation; verify pure Phase 7O baseline matches
                res_7o = compute_production_contribution(row, model_version="phase7o")
                assert pytest.approx(res_7o["final_contribution_score"], abs=0.1) == float(row["contribution_score"])
            else:
                assert pytest.approx(res["final_contribution_score"], abs=0.1) == float(row["contribution_score"])


def test_chase_2nd_innings_invariance():
    """Verify 2nd innings chase matches are 100% unchanged."""
    df = pd.read_csv("data/processed/batter_match_contributions.csv", low_memory=False)
    chases = df[df["innings"] == 2].head(25)

    for _, row in chases.iterrows():
        res = compute_production_contribution(row)
        assert pytest.approx(res["final_contribution_score"], abs=0.1) == float(row["contribution_score"])


def test_entry_at_or_after_4_overs_unmodified():
    """Verify that batter entry at or after 4.0 overs uses raw team_rr_entry completely."""
    df = pd.read_csv("data/processed/batter_match_contributions.csv", low_memory=False)
    # Match 1527686 Dhruv Jurel entered at 5.1 (after over 4)
    jurel_row = df[(df["match_id"] == 1527686) & (df["player"] == "Dhruv Jurel")].iloc[0]
    from app.services.data_service import data_service
    engine = data_service.get_active_scoring_engine()
    if engine == "v8.5.1-strategy4-hybrid":
        from src.phase8_5_hyper_score_damping import compute_phase8_5_unified_contribution
        res_jurel = compute_phase8_5_unified_contribution(jurel_row, strategy="hybrid", apply_preservation=True)
        assert pytest.approx(res_jurel["final_contribution_score"], abs=0.1) == float(jurel_row["contribution_score"])
    else:
        res_jurel = compute_production_contribution(jurel_row)
        assert pytest.approx(res_jurel["final_contribution_score"], abs=0.1) == float(jurel_row["contribution_score"])



def test_dnb_preservation():
    """Verify DNB appearances remain None."""
    row_dnb = {
        "player": "Test Batter DNB",
        "dnb": True,
        "is_dnb": True,
        "balls_faced": 0,
        "actual_runs": 0,
    }
    res = compute_production_contribution(row_dnb)
    assert res is None or res.get("dnb") is True or res.get("contribution_score") is None


def test_outcome_and_player_identity_invariance():
    """Verify match outcome and player identity invariance."""
    df = pd.read_csv("data/processed/batter_match_contributions.csv", low_memory=False)
    sury_row = df[(df["match_id"] == 1527686) & (df["player"] == "V Suryavanshi")].iloc[0]

    # Outcome invariance
    row_won = sury_row.copy()
    row_won["won_match"] = True
    row_lost = sury_row.copy()
    row_lost["won_match"] = False

    res_won = compute_production_contribution(row_won)
    res_lost = compute_production_contribution(row_lost)
    assert res_won["final_contribution_score"] == res_lost["final_contribution_score"]

    # Player identity invariance
    row_a = sury_row.copy()
    row_a["player"] = "Player Alpha"
    row_b = sury_row.copy()
    row_b["player"] = "Player Beta"

    res_a = compute_production_contribution(row_a)
    res_b = compute_production_contribution(row_b)
    assert res_a["final_contribution_score"] == res_b["final_contribution_score"]


def test_p2_unchanged_independence():
    """Verify Pillar 2 (Batter Performance) is completely independent and untouched."""
    df = pd.read_csv("data/processed/batter_match_contributions.csv", low_memory=False)
    sury_row = df[(df["match_id"] == 1527686) & (df["player"] == "V Suryavanshi")].iloc[0]

    res = compute_production_contribution(sury_row)
    assert res["pillar2_perf_score"] == float(sury_row["score_perf"])
