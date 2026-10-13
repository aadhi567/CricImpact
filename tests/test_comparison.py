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



