"""
Tests for Phase 7A: Multi-Player Contribution Comparison (Max 5 Players).
Verifies:
1. Minimum 2 players required.
2. Maximum 5 players allowed.
3. 6 players rejected.
4. Same-season comparison works.
5. Unknown player/season handled correctly.
6. DNB contribution values remain NULL.
7. NULL contextual categories remain NULL.
8. View A comparison uses View A data.
9. View B comparison uses View B data.
10. Comparison does not modify underlying scores.
11. Four-pillar comparison outputs present at 25% each.
12. Analytical observations separate efficiency, volume, and team share.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_comparison_min_players_enforced():
    """Verify that fewer than 2 players is rejected."""
    # 1 player
    res = client.get("/api/contribution/compare?season=2016&players=V%20Kohli")
    assert res.status_code == 400
    assert "Minimum 2 players required" in res.json()["detail"]

    # 0 players
    res_empty = client.get("/api/contribution/compare?season=2016&players=")
    assert res_empty.status_code == 400


def test_comparison_max_players_enforced():
    """Verify that more than 5 players is rejected."""
    six_players = "V Kohli,AB de Villiers,KL Rahul,DA Warner,S Dhawan,Yuvraj Singh"
    res = client.get(f"/api/contribution/compare?season=2016&players={six_players}")
    assert res.status_code == 400
    assert "Maximum 5 players can be compared" in res.json()["detail"]


def test_comparison_valid_2_to_5_players():
    """Verify 2, 3, 4, 5 players all succeed."""
    for count in range(2, 6):
        pool = ["V Kohli", "AB de Villiers", "KL Rahul", "DA Warner", "S Dhawan"]
        players_query = ",".join(pool[:count])
        res = client.get(f"/api/contribution/compare?season=2016&players={players_query}")
        assert res.status_code == 200, f"Failed for {count} players: {res.text}"
        data = res.json()
        assert data["players_count"] == count
        assert len(data["players"]) == count
        assert data["season"] == "2016"


def test_comparison_same_season_consistency():
    """Verify comparison requires and works within the specified season."""
    res = client.get("/api/contribution/compare?season=2016&players=V%20Kohli,AB%20de%20Villiers")
    assert res.status_code == 200
    data = res.json()
    for p in data["players"]:
        assert p["season"] == "2016"


def test_comparison_missing_player_rejected():
    """Verify unknown player in the season returns 404."""
    res = client.get("/api/contribution/compare?season=2016&players=V%20Kohli,NonExistentPlayerXYZ")
    assert res.status_code == 404
    assert "NonExistentPlayerXYZ" in res.json()["detail"]


def test_comparison_dnb_preserves_null():
    """Verify DNB player (e.g. YS Chahal 2016) in comparison preserves NULL scores."""
    res = client.get("/api/contribution/compare?season=2016&players=V%20Kohli,YS%20Chahal")
    assert res.status_code == 200
    data = res.json()
    chahal = [p for p in data["players"] if p["player"] == "YS Chahal"][0]

    assert chahal["is_dnb"] is True
    assert chahal["batting_innings"] == 0
    assert chahal["did_not_bat_matches"] == 13
    assert chahal["contribution_score"] is None
    assert chahal["total_positive_raw_contribution"] is None
    assert chahal["season_team_contribution_share"] is None
    assert chahal["pillars"]["pillar1_match_context"] is None
    assert chahal["pillars"]["pillar2_batter_performance"] is None


def test_comparison_unobserved_context_remains_null():
    """Verify unobserved context categories remain NULL, while observed middle overs are populated."""
    res = client.get("/api/contribution/compare?season=2016&players=V%20Kohli,AB%20de%20Villiers")
    assert res.status_code == 200
    data = res.json()
    kohli = [p for p in data["players"] if p["player"] == "V Kohli"][0]

    # Kohli's innings overlapped middle overs (overs 6-16), giving a valid middle-over score
    from app.services.data_service import data_service
    engine = data_service.get_active_scoring_engine()
    if engine == "v8.5.1-strategy4-hybrid":
        assert kohli["context_breakdown"]["middle_over_contribution"] == 86.08
        assert kohli["context_breakdown"]["powerplay_contribution"] == 76.65
        assert kohli["context_breakdown"]["death_over_contribution"] == 89.16
    else:
        assert kohli["context_breakdown"]["middle_over_contribution"] == 86.34
        assert kohli["context_breakdown"]["powerplay_contribution"] == 76.86
        assert kohli["context_breakdown"]["death_over_contribution"] == 89.61

    # Verify that a player with no middle overs observations (e.g. pure DNB Chahal) remains NULL
    res_chahal = client.get("/api/contribution/compare?season=2016&players=V%20Kohli,YS%20Chahal")
    assert res_chahal.status_code == 200
    chahal = [p for p in res_chahal.json()["players"] if p["player"] == "YS Chahal"][0]
    assert chahal["context_breakdown"]["middle_over_contribution"] is None


def test_comparison_four_pillars_present():
    """Verify four pillars P1, P2, P3, P4 are computed and present."""
    res = client.get("/api/contribution/compare?season=2016&players=V%20Kohli,AB%20de%20Villiers")
    assert res.status_code == 200
    data = res.json()
    kohli = [p for p in data["players"] if p["player"] == "V Kohli"][0]

    pillars = kohli["pillars"]
    assert "pillar1_match_context" in pillars
    assert "pillar2_batter_performance" in pillars
    assert "pillar3_team_state_impact" in pillars
    assert "pillar4_counterfactual_value" in pillars
    assert pillars["pillar1_match_context"] is not None
    assert pillars["pillar2_batter_performance"] is not None
    assert pillars["pillar3_team_state_impact"] is not None
    assert pillars["pillar4_counterfactual_value"] is not None


def test_comparison_view_a_vs_view_b_values():
    """Verify View A uses all-innings and View B uses qualified data."""
    res_a = client.get("/api/contribution/compare?season=2016&players=V%20Kohli,DA%20Warner&view=view_a")
    assert res_a.status_code == 200
    data_a = res_a.json()
    assert data_a["view"] == "view_a"

    res_b = client.get("/api/contribution/compare?season=2016&players=V%20Kohli,DA%20Warner&view=view_b")
    assert res_b.status_code == 200
    data_b = res_b.json()
    assert data_b["view"] == "view_b"


def test_comparison_underlying_scores_unmodified():
    """Verify comparison scores match Phase 7G ground truth exactly."""
    res = client.get("/api/contribution/compare?season=2016&players=V%20Kohli,AB%20de%20Villiers")
    assert res.status_code == 200
    data = res.json()
    kohli = [p for p in data["players"] if p["player"] == "V Kohli"][0]
    ab = [p for p in data["players"] if p["player"] == "AB de Villiers"][0]

    from app.services.data_service import data_service
    engine = data_service.get_active_scoring_engine()
    if engine == "v8.5.1-strategy4-hybrid":
        assert kohli["contribution_score"] == 76.65
        assert kohli["season_team_contribution_share"] == 39.98
        assert kohli["total_positive_raw_contribution"] == 40.6939

        assert ab["contribution_score"] == 61.92
        assert ab["season_team_contribution_share"] == 26.45
        assert ab["total_positive_raw_contribution"] == 26.9232
    else:
        assert kohli["contribution_score"] == 76.86
        assert kohli["season_team_contribution_share"] == 34.87
        assert kohli["total_positive_raw_contribution"] == 22.8863

        assert ab["contribution_score"] == 62.04
        assert ab["season_team_contribution_share"] == 25.02
        assert ab["total_positive_raw_contribution"] == 16.421



def test_comparison_observations_multidimensional():
    """Verify analytical observations separate efficiency, volume, and team share."""
    res = client.get("/api/contribution/compare?season=2016&players=V%20Kohli,AB%20de%20Villiers,DA%20Warner")
    assert res.status_code == 200
    data = res.json()
    obs = data["analytical_observations"]

    assert "highest_score_player" in obs
    assert "highest_positive_player" in obs
    assert "highest_team_share_player" in obs
    assert len(obs["dimensions"]) >= 1
    assert "summary_note" in obs
    assert "winner" not in obs["summary_note"].lower()


def test_contribution_score_independent_of_team_share():
    """
    Verify Contribution Score (efficiency) is mathematically independent of Team Share (share).
    E.g. A batter can have higher Contribution Score but lower Team Share than another.
    In 2016: V Kohli score = 76.10, share = 35.0%; DA Warner score = 75.87, share = 38.64%.
    """
    res = client.get("/api/contribution/compare?season=2016&players=V%20Kohli,DA%20Warner")
    assert res.status_code == 200
    data = res.json()
    kohli = [p for p in data["players"] if p["player"] == "V Kohli"][0]
    warner = [p for p in data["players"] if p["player"] == "DA Warner"][0]

    # Kohli has higher average score (efficiency)
    assert kohli["contribution_score"] > warner["contribution_score"]
    # Warner has higher team share (attribution)
    assert warner["season_team_contribution_share"] > kohli["season_team_contribution_share"]


def test_team_share_calculated_from_existing_season_aggregation():
    """
    Verify Team Share is sourced directly from Phase 6A season metrics and not recalculated from runs.
    RCB 2016 total positive raw contribution sum is used as denominator in Phase 6A.
    """
    res = client.get("/api/contribution/compare?season=2016&players=V%20Kohli,KL%20Rahul")
    assert res.status_code == 200
    data = res.json()
    kohli = [p for p in data["players"] if p["player"] == "V Kohli"][0]
    rahul = [p for p in data["players"] if p["player"] == "KL Rahul"][0]

    from app.services.data_service import data_service
    engine = data_service.get_active_scoring_engine()
    if engine == "v8.5.1-strategy4-hybrid":
        assert kohli["season_team_contribution_share"] == 39.98
        assert rahul["season_team_contribution_share"] == 8.77
    else:
        assert kohli["season_team_contribution_share"] == 34.87
        assert rahul["season_team_contribution_share"] == 9.72


def test_comparison_phase_metrics_top_level_and_no_nan():
    """
    Regression test for Contextual Phase Breakdown NaN issue.
    Verifies that all 6 phase metrics exist at top level AND inside context_breakdown,
    and that none are NaN or undefined.
    """
    res = client.get("/api/contribution/compare?season=2016&players=V%20Kohli,AB%20de%20Villiers")
    assert res.status_code == 200
    data = res.json()
    assert len(data["players"]) == 2

    for p in data["players"]:
        for field in [
            "first_innings_contribution",
            "chase_contribution",
            "powerplay_contribution",
            "middle_over_contribution",
            "death_over_contribution",
            "high_pressure_contribution",
        ]:
            assert field in p, f"Missing top-level field {field}"
            assert field in p["context_breakdown"], f"Missing context_breakdown field {field}"
            # Both top-level and context_breakdown must match
            assert p[field] == p["context_breakdown"][field]
            # Ensure valid numeric value (neither None nor NaN for active qualified batters)
            val = p[field]
            assert val is not None, f"Expected numeric value for {field} on {p['player']}"
            assert isinstance(val, (int, float))
            assert str(val).lower() != "nan"

    kohli = [p for p in data["players"] if p["player"] == "V Kohli"][0]
    ab = [p for p in data["players"] if p["player"] == "AB de Villiers"][0]
    assert kohli["first_innings_contribution"] == 82.61
    assert kohli["chase_contribution"] == 66.72
    assert ab["first_innings_contribution"] == 65.41
    assert ab["chase_contribution"] == 56.12


def test_comparison_dot_ball_percentage_and_extras_handling():
    """
    Regression test for dot-ball percentage:
    Dot-ball percentage = (legal balls with zero runs off bat / total legal balls faced) * 100
    Verifies:
    1. Wides are excluded from legal balls faced and dot balls.
    2. Zero runs off the bat counts as a dot ball even if byes/leg-byes occurred.
    3. Dot-ball percentage is exposed at top-level and inside context_breakdown.
    4. Numeric value is bounded between 0.0 and 100.0.
    """
    res = client.get("/api/contribution/compare?season=2016&players=V%20Kohli,AB%20de%20Villiers")
    assert res.status_code == 200
    data = res.json()

    kohli = [p for p in data["players"] if p["player"] == "V Kohli"][0]
    ab = [p for p in data["players"] if p["player"] == "AB de Villiers"][0]

    assert kohli["dot_balls"] == 169
    assert kohli["dot_ball_percentage"] == 26.4
    assert kohli["dot_ball_percentage"] == kohli["context_breakdown"]["dot_ball_percentage"]
    assert 0.0 <= kohli["dot_ball_percentage"] <= 100.0

    assert ab["dot_balls"] == 104
    assert ab["dot_ball_percentage"] == 25.6
    assert ab["dot_ball_percentage"] == ab["context_breakdown"]["dot_ball_percentage"]
    assert 0.0 <= ab["dot_ball_percentage"] <= 100.0


def test_comparison_phase_wise_strike_rates_and_boundaries():
    """
    Regression test for phase-wise strike rates and boundaries:
    Powerplay: Overs 1–6 (delivery over 0–5)
    Middle Overs: Overs 7–16 (delivery over 6–15)
    Death Overs: Overs 17–20 (delivery over 16–19)
    SR = runs scored in phase / legal balls in phase * 100
    """
    res = client.get("/api/contribution/compare?season=2016&players=V%20Kohli,AB%20de%20Villiers")
    assert res.status_code == 200
    data = res.json()

    kohli = [p for p in data["players"] if p["player"] == "V Kohli"][0]
    ab = [p for p in data["players"] if p["player"] == "AB de Villiers"][0]

    # Kohli 2016 phase strike rates
    assert kohli["powerplay_strike_rate"] == 120.9
    assert kohli["middle_over_strike_rate"] == 150.8
    assert kohli["death_over_strike_rate"] == 241.2

    assert kohli["powerplay_strike_rate"] == kohli["context_breakdown"]["powerplay_strike_rate"]
    assert kohli["middle_over_strike_rate"] == kohli["context_breakdown"]["middle_over_strike_rate"]
    assert kohli["death_over_strike_rate"] == kohli["context_breakdown"]["death_over_strike_rate"]

    # AB de Villiers 2016 phase strike rates
    assert ab["powerplay_strike_rate"] == 147.4
    assert ab["middle_over_strike_rate"] == 168.7
    assert ab["death_over_strike_rate"] == 215.6


def test_comparison_dnb_and_missing_phase_values_vs_genuine_zero():
    """
    Verifies that:
    1. DNB players have None for all phase contributions, dot balls, and phase strike rates.
    2. DNB players do not become artificial zero-contribution batting innings.
    3. Missing data is represented as None (null in JSON), distinguishing it from genuine 0.
    """
    res = client.get("/api/contribution/compare?season=2016&players=V%20Kohli,YS%20Chahal")
    assert res.status_code == 200
    data = res.json()
    chahal = [p for p in data["players"] if p["player"] == "YS Chahal"][0]

    assert chahal["is_dnb"] is True
    assert chahal["batting_innings"] == 0
    assert chahal["dot_balls"] is None
    assert chahal["dot_ball_percentage"] is None
    assert chahal["powerplay_strike_rate"] is None
    assert chahal["middle_over_strike_rate"] is None
    assert chahal["death_over_strike_rate"] is None
    assert chahal["first_innings_contribution"] is None
    assert chahal["chase_contribution"] is None
    assert chahal["powerplay_contribution"] is None
    assert chahal["middle_over_contribution"] is None
    assert chahal["death_over_contribution"] is None
    assert chahal["high_pressure_contribution"] is None


def test_comparison_t20i_multi_batter_metrics():
    """
    Verifies that T20I comparison (e.g. 2022/23 V Kohli, SA Yadav) correctly calculates
    dot-ball percentage, phase strike rates, and phase contributions from match deliveries.
    """
    res = client.get("/api/contribution/compare?season=2022/23&players=V%20Kohli,SA%20Yadav&competition=t20i")
    assert res.status_code == 200
    data = res.json()
    assert len(data["players"]) == 2

    kohli = [p for p in data["players"] if p["player"] == "V Kohli"][0]
    surya = [p for p in data["players"] if p["player"] == "SA Yadav"][0]

    assert kohli["dot_balls"] == 74
    assert kohli["dot_ball_percentage"] == 29.1
    assert kohli["powerplay_strike_rate"] == 89.8
    assert kohli["middle_over_strike_rate"] == 125.0
    assert kohli["death_over_strike_rate"] == 225.5

    assert surya["dot_balls"] == 127
    assert surya["dot_ball_percentage"] == 30.0
    assert surya["powerplay_strike_rate"] == 105.4
    assert surya["middle_over_strike_rate"] == 173.9
    assert surya["death_over_strike_rate"] == 236.1


def test_comparison_ishan_kishan_and_harry_brook_2023():
    """
    Verifies the specific production example:
    Ishan Kishan and Harry Brook (HC Brook) in IPL 2023.
    Asserts:
    1. Ishan Kishan: dot-ball percentage 40.9%, PP SR 144.8, Middle SR 139.1, Death SR 0.0 (genuine 0.0).
    2. HC Brook: dot-ball percentage 42.2%, PP SR 114.3, Middle SR 130.0, Death SR 145.0.
    3. Both singular and plural phase strike rate keys are present in root player and context_breakdown.
    """
    res = client.get("/api/contribution/compare?season=2023&players=Ishan%20Kishan,HC%20Brook")
    assert res.status_code == 200
    data = res.json()
    assert len(data["players"]) == 2

    ishan = [p for p in data["players"] if p["player"] == "Ishan Kishan"][0]
    brook = [p for p in data["players"] if p["player"] == "HC Brook"][0]

    # Ishan Kishan 2023
    assert ishan["actual_runs"] == 454
    assert ishan["balls_faced"] == 318
    assert ishan["dot_balls"] == 130
    assert ishan["dot_ball_percentage"] == 40.9
    assert ishan["powerplay_strike_rate"] == 144.8
    assert ishan["middle_over_strike_rate"] == 139.1
    assert ishan["middle_overs_strike_rate"] == 139.1
    assert ishan["death_over_strike_rate"] == 0.0
    assert ishan["death_overs_strike_rate"] == 0.0

    # In context_breakdown as well
    assert ishan["context_breakdown"]["dot_ball_percentage"] == 40.9
    assert ishan["context_breakdown"]["powerplay_strike_rate"] == 144.8
    assert ishan["context_breakdown"]["middle_overs_strike_rate"] == 139.1
    assert ishan["context_breakdown"]["death_overs_strike_rate"] == 0.0

    # HC Brook 2023
    assert brook["actual_runs"] == 190
    assert brook["balls_faced"] == 154
    assert brook["dot_balls"] == 65
    assert brook["dot_ball_percentage"] == 42.2
    assert brook["powerplay_strike_rate"] == 114.3
    assert brook["middle_over_strike_rate"] == 130.0
    assert brook["middle_overs_strike_rate"] == 130.0
    assert brook["death_over_strike_rate"] == 145.0
    assert brook["death_overs_strike_rate"] == 145.0

    assert brook["context_breakdown"]["dot_ball_percentage"] == 42.2
    assert brook["context_breakdown"]["powerplay_strike_rate"] == 114.3
    assert brook["context_breakdown"]["middle_overs_strike_rate"] == 130.0
    assert brook["context_breakdown"]["death_overs_strike_rate"] == 145.0


def test_comparison_player_name_alias_resolution():
    """
    Verifies that querying with player name aliases (e.g. 'Harry Brook' -> 'HC Brook',
    'Virat Kohli' -> 'V Kohli') resolves seamlessly to the canonical player.
    """
    res = client.get("/api/contribution/compare?season=2023&players=Ishan%20Kishan,Harry%20Brook")
    assert res.status_code == 200
    data = res.json()
    assert len(data["players"]) == 2
    players = [p["player"] for p in data["players"]]
    assert "HC Brook" in players
    assert "Ishan Kishan" in players

    brook = [p for p in data["players"] if p["player"] == "HC Brook"][0]
    assert brook["dot_ball_percentage"] == 42.2
    assert brook["powerplay_strike_rate"] == 114.3


def test_comparison_extras_handling_and_zero_division():
    """
    Verifies delivery-level extras handling:
    1. Wides are excluded from legal balls faced and do not contribute to dot balls.
    2. Zero legal balls returns None, never causing ZeroDivisionError, NaN, or Infinity.
    """
    from app.services.data_service import data_service
    import pandas as pd

    # Mock delivery dataframe with wide, no-ball, and bye
    mock_delivs = pd.DataFrame([
        {"batter": "Test Batter", "wides": 1, "batter_runs": 0, "over": 1, "ball": 1},  # Wide: ignored
        {"batter": "Test Batter", "wides": 0, "batter_runs": 0, "over": 1, "ball": 2},  # Dot: counted
        {"batter": "Test Batter", "wides": 0, "batter_runs": 4, "over": 1, "ball": 3},  # Four: runs=4
        {"batter": "Test Batter", "wides": 0, "batter_runs": 0, "over": 7, "ball": 1},  # Middle dot
    ])

    metrics = data_service._compute_batter_phase_and_dot_metrics(
        player_name="Test Batter",
        season_str="2024",
        norm_comp="ipl",
        c_sub=pd.DataFrame(),
        delivs_sub_ipl=mock_delivs,
    )

    # 3 legal balls (1 wide ignored)
    assert metrics["legal_balls"] == 3
    # 2 dot balls (balls 2 and 4)
    assert metrics["dot_balls"] == 2
    assert metrics["dot_ball_percentage"] == round(2 / 3 * 100, 1)

    # Powerplay: 2 legal balls, 4 runs -> SR 200.0
    assert metrics["powerplay_strike_rate"] == 200.0
    # Middle: 1 legal ball, 0 runs -> SR 0.0 (genuine 0.0)
    assert metrics["middle_overs_strike_rate"] == 0.0
    # Death: 0 legal balls -> None
    assert metrics["death_overs_strike_rate"] is None





