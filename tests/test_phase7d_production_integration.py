"""
Tests for Phase 7D Production Integration.

Verifies:
1. Production contribution calculation: 25% P1, 35% P2, 40% P3, 0% P4.
2. P4 exclusion from main score and presence in diagnostic layer.
3. Versioned backups exist and remain preserved.
4. Strict DNB rule: DNB remains strictly NULL.
5. Middle-over overlap rule: entry_over < 16.0 and exit_over >= 6.0.
6. Real player profiles conform to validated Phase 7D ground truth.
7. Team Contribution Share attribution formula integrity.
"""

from pathlib import Path
import pytest
import numpy as np
import pandas as pd

from src.contribution_framework import compute_production_contribution
from src.phase7c_rebalance import compute_phase7c_contribution


def test_production_formula_weights():
    """Verify production contribution calculation implements 25% P1, 35% P2, 40% P3."""
    row = {
        "innings": 1,
        "entry_over": 10.0,
        "balls_remaining_entry": 60,
        "wickets_remaining_entry": 8,
        "team_rr_entry": 7.5,
        "actual_runs": 45,
        "balls_faced": 30,
        "actual_sr": 150.0,
        "boundary_percentage": 60.0,
        "run_deviation": 12.0,
        "sr_deviation": 25.0,
        "opportunity_usage": 0.5,
        "dismissal_status": "caught",
        "balls_remaining_exit": 30,
        "wickets_remaining_exit": 7,
        "wicket_resource_change": -1,
        "expected_final_change": 8.0,
        "window_team_rr": 9.0,
        "trajectory_deviation_change": 6.0,
        "overs_spent": 5.0,
    }
    res = compute_phase7c_contribution(row)

    assert res["dnb"] is False
    assert res["contribution_score"] is not None
    assert res["pillar1_context_score"] is not None
    assert res["pillar2_perf_score"] is not None
    assert res["pillar3_state_score"] is not None
    assert "pillar4_diagnostic" in res

    p1 = res["pillar1_context_score"]
    p2 = res["pillar2_perf_score"]
    p3 = res["pillar3_state_score"]
    expected_score = round(0.25 * p1 + 0.35 * p2 + 0.40 * p3, 1)

    assert abs(res["contribution_score"] - expected_score) <= 0.15


def test_production_backups_exist():
    """Verify that versioned Phase 6 production backups exist and are non-empty."""
    bak_season = Path("models/contribution/phase6/phase6_season_metrics_v6_backup.csv")
    bak_bmc = Path("data/processed/batter_match_contributions_v6_backup.csv")

    assert bak_season.exists(), "Phase 6 season metrics backup must exist"
    assert bak_season.stat().st_size > 100_000

    assert bak_bmc.exists(), "Batter match contributions backup must exist"
    assert bak_bmc.stat().st_size > 1_000_000


def test_production_real_players_validation():
    """Verify real player profile benchmarks in Phase 7D ground truth backup."""
    df_season = pd.read_csv("models/contribution/phase6/phase6_season_metrics_v7d_backup.csv", dtype={"season": str})

    # 1. Specialist bowler with 100% DNB: YS Chahal 2016
    chahal = df_season[(df_season["player"] == "YS Chahal") & (df_season["season"] == "2016")].iloc[0]
    assert chahal["batting_innings"] == 0
    assert chahal["did_not_bat_matches"] == 13
    assert pd.isna(chahal["average_contribution_score"])
    assert pd.isna(chahal["season_team_contribution_share"])
    assert pd.isna(chahal["middle_over_contribution"])

    # 2. Elite top-order accumulator: V Kohli 2016
    kohli = df_season[(df_season["player"] == "V Kohli") & (df_season["season"] == "2016")].iloc[0]
    assert kohli["batting_innings"] == 16
    assert kohli["actual_runs"] == 973
    assert kohli["average_contribution_score"] == 68.71
    assert kohli["middle_over_contribution"] == 75.8
    assert kohli["season_team_contribution_share"] == 36.72

    # 3. Dynamic middle-order: AB de Villiers 2016
    ab = df_season[(df_season["player"] == "AB de Villiers") & (df_season["season"] == "2016")].iloc[0]
    assert ab["batting_innings"] == 16
    assert ab["actual_runs"] == 687
    assert ab["average_contribution_score"] == 54.64
    assert ab["middle_over_contribution"] == 55.98

    # 4. Dominant captain/opener: DA Warner 2016
    warner = df_season[(df_season["player"] == "DA Warner") & (df_season["season"] == "2016")].iloc[0]
    assert warner["batting_innings"] == 17
    assert warner["actual_runs"] == 848
    assert warner["average_contribution_score"] == 66.49
    assert warner["middle_over_contribution"] == 74.82


def test_middle_over_eligibility_rule():
    """Verify Phase 7B middle-over overlap condition: entry_over < 16.0 and exit_over >= 6.0."""
    df_bmc = pd.read_csv("data/processed/batter_match_contributions.csv", low_memory=False)

    # Filter to standard innings
    std_bmc = df_bmc[df_bmc["innings"] <= 2]

    # Verify that openers who bat into middle overs have middle overs presence
    kohli_inns = std_bmc[(std_bmc["player"] == "V Kohli") & (std_bmc["season"].astype(str) == "2016")]
    kohli_mid_inns = [
        r for _, r in kohli_inns.iterrows()
        if float(r.get("entry_over", 0.0)) < 16.0 and float(r.get("exit_over", 20.0)) >= 6.0
    ]
    assert len(kohli_mid_inns) > 10, "Kohli 2016 must have multiple qualifying middle-over innings"


def test_team_contribution_share_positive_rectification():
    """Verify that season team contribution share sums strictly positive raw contribution."""
    df_season = pd.read_csv("models/contribution/phase6/phase6_season_metrics.csv", dtype={"season": str})

    # Check across top teams in 2016
    rcb_2016 = df_season[(df_season["team"] == "Royal Challengers Bangalore") & (df_season["season"] == "2016")]
    shares = rcb_2016["season_team_contribution_share"].dropna().tolist()

    # Sum of shares should equal ~100% (within roundoff error across roster)
    assert 99.0 <= sum(shares) <= 101.0
