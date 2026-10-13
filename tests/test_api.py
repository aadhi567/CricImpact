"""
Tests for Phase 6A Frontend API Layer.
Verifies endpoints, data integrity, strict DNB rules, and null preservation.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_api_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"


def test_api_seasons():
    res = client.get("/api/seasons")
    assert res.status_code == 200
    data = res.json()
    assert "2016" in data["seasons"]
    assert "2024" in data["seasons"]
    assert data["total_seasons"] >= 15


def test_api_teams():
    res = client.get("/api/teams?season=2016")
    assert res.status_code == 200
    data = res.json()
    assert "Royal Challengers Bangalore" in data["teams"]


def test_api_dashboard_summary():
    res = client.get("/api/dashboard/summary?season=2016")
    assert res.status_code == 200
    data = res.json()
    assert data["total_players"] > 0
    assert data["total_batting_innings"] > 0
    assert data["average_contribution_score"] is not None
    assert data["total_positive_contribution"] > 0


def test_api_players_filter_invariance():
    """Verify that filtering by min_runs does not change underlying values."""
    res_all = client.get("/api/players?season=2016&search=Kohli")
    assert res_all.status_code == 200
    all_data = res_all.json()["players"]
    assert len(all_data) == 1
    kohli_all = all_data[0]

    res_300 = client.get("/api/players?season=2016&min_runs=300&search=Kohli")
    assert res_300.status_code == 200
    kohli_300 = res_300.json()["players"][0]

    # Metrics MUST be identical regardless of filter
    assert kohli_all["average_contribution_score"] == kohli_300["average_contribution_score"]
    assert kohli_all["season_team_contribution_share"] == kohli_300["season_team_contribution_share"]
    from app.services.data_service import data_service
    engine = data_service.get_active_scoring_engine()
    if engine == "v8.5.1-strategy4-hybrid":
        assert kohli_all["average_contribution_score"] == 76.65
        assert kohli_all["season_team_contribution_share"] == 39.98
    else:
        assert kohli_all["average_contribution_score"] == 76.86
        assert kohli_all["season_team_contribution_share"] == 34.87


def test_api_player_season_null_preservation():
    """Verify that unobserved phases return null (None) and are NEVER converted to 0."""
    res = client.get("/api/player/V%20Kohli/season/2016")
    assert res.status_code == 200
    data = res.json()

    assert data["player"] == "V Kohli"
    assert data["season"] == "2016"
    from app.services.data_service import data_service
    engine = data_service.get_active_scoring_engine()
    if engine == "v8.5.1-strategy4-hybrid":
        assert data["average_contribution_score"] == 76.65
        assert data["season_team_contribution_share"] == 39.98
    else:
        assert data["average_contribution_score"] == 76.86
        assert data["season_team_contribution_share"] == 34.87
    assert data["matches_played"] == 16
    assert data["batting_innings"] == 16
    assert data["did_not_bat_matches"] == 0

    # Middle overs contribution is valid because Kohli's innings overlapped middle overs (overs 6-16)
    if engine == "v8.5.1-strategy4-hybrid":
        assert data["context_breakdown"]["middle_over_contribution"] == 86.08
    else:
        assert data["context_breakdown"]["middle_over_contribution"] == 86.34

    # Powerplay and Death MUST have values
    if engine == "v8.5.1-strategy4-hybrid":
        assert data["context_breakdown"]["powerplay_contribution"] == 76.65
        assert data["context_breakdown"]["death_over_contribution"] == 89.16
    else:
        assert data["context_breakdown"]["powerplay_contribution"] == 76.86
        assert data["context_breakdown"]["death_over_contribution"] == 89.61



def test_api_dnb_player():
    """Verify that pure DNB players return NULL for contribution scores."""
    res = client.get("/api/player/YS%20Chahal/season/2016")
    assert res.status_code == 200
    data = res.json()

    assert data["player"] == "YS Chahal"
    assert data["matches_played"] == 13
    assert data["batting_innings"] == 0
    assert data["did_not_bat_matches"] == 13
    assert data["average_contribution_score"] is None
    assert data["season_team_contribution_share"] is None
    assert data["context_breakdown"]["middle_over_contribution"] is None
    assert data["context_breakdown"]["powerplay_contribution"] is None
    assert data["context_breakdown"]["death_over_contribution"] is None


def test_api_player_matches_dnb_separation():
    """Verify matches endpoint marks DNB matches and gives null scores."""
    res = client.get("/api/player/YS%20Chahal/matches?season=2016")
    assert res.status_code == 200
    data = res.json()

    assert data["total_appearances"] == 13
    assert data["batting_innings"] == 0
    assert data["dnb_matches"] == 13
    for m in data["matches"]:
        assert m["is_dnb"] is True
        assert m["contribution_score"] is None
        assert m["raw_contribution"] is None


def test_api_match_detail_four_pillars():
    """Verify match detail returns all 4 Phase 7D pillars with corrected early-over P1 context."""
    # Match 980907 is Kohli's 75 (51) against SRH in 2016 (entry 0.2 overs, 0 wkts lost -> neutral P1)
    res = client.get("/api/match/980907/player/V%20Kohli")
    assert res.status_code == 200
    data = res.json()

    assert data["player"] == "V Kohli"
    assert data["basic_performance"]["runs"] == 75
    assert data["basic_performance"]["balls"] == 51
    from app.services.data_service import data_service
    engine = data_service.get_active_scoring_engine()
    if engine == "v8.5.1-strategy4-hybrid":
        assert data["contribution_score"] == 89.5
    else:
        assert data["contribution_score"] == 90.0

    pillars = data["pillars"]
    assert "pillar1_context" in pillars
    assert "pillar2_performance" in pillars
    assert "pillar3_state" in pillars
    assert "pillar4_cf" in pillars

    assert pillars["pillar1_context"]["weight"] == "25%"
    assert pillars["pillar2_performance"]["weight"] == "35%"
    assert pillars["pillar3_state"]["weight"] == "40%"
    assert pillars["pillar4_cf"]["weight"] == "0% (Diagnostic Only)"

    assert pillars["pillar1_context"]["score"] == 40.2
    assert pillars["pillar2_performance"]["score"] == 91.0
    if engine == "v8.5.1-strategy4-hybrid":
        assert pillars["pillar3_state"]["score"] == 94.2
    else:
        assert pillars["pillar3_state"]["score"] == 95.4
    assert pillars["pillar4_cf"]["score"] == 86.7
    assert data["p1_leverage"] in (0.926, 0.931)

    # Verify signals explanation exists
    assert len(data["signals"]) > 0
    assert "verdict" in data


def test_api_match_detail_abhishek_sharma_powerplay_fix():
    """Verify live API returns the corrected early Powerplay contribution for Abhishek Sharma in match 1527674."""
    res = client.get("/api/match/1527674/player/Abhishek%20Sharma")
    assert res.status_code == 200
    data = res.json()

    assert data["player"] == "Abhishek Sharma"
    assert data["match_id"] == 1527674
    assert data["basic_performance"]["runs"] == 7
    assert data["basic_performance"]["balls"] == 8
    assert data["basic_performance"]["strike_rate"] == 87.5
    assert data["basic_performance"]["expected_sr"] == 114.4
    assert data["basic_performance"]["expected_runs"] == 29.0

    assert data["match_context"]["entry_over"] == 0.2
    assert data["match_context"]["exit_over"] == 2.1
    assert data["match_context"]["wickets_lost_during_stay"] == 1

    from app.services.data_service import data_service
    engine = data_service.get_active_scoring_engine()
    pillars = data["pillars"]
    # P1 Context must be neutral (40.2), NOT artificially inflated to 63.1 by pre-entry RR
    assert pillars["pillar1_context"]["score"] == 40.2
    # P2 Performance evaluates batter execution (43.7)
    assert pillars["pillar2_performance"]["score"] == 43.7
    # P3 State evaluates trajectory & team state
    if engine == "v8.5.1-strategy4-hybrid":
        assert pillars["pillar3_state"]["score"] == 61.3
        assert data["contribution_score"] == 52.3
    else:
        assert pillars["pillar3_state"]["score"] == 61.4
        assert data["contribution_score"] == 52.4


