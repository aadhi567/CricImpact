"""
Tests for Multi-Competition API Architecture with SMAT Temporary Deactivation.
Verifies:
1. /api/competitions listing contains active competitions (IPL, T20I) and excludes deactivated SMAT.
2. Backward-compatible default to 'ipl'.
3. Competition filtering across seasons, teams, dashboard summary, players, matches.
4. Correct querying of T20I (2,264 matches) and complete preservation of IPL dataset.
5. Strict preservation of DNB rules across active competitions.
6. Temporary reversible deactivation of SMAT (returns HTTP 400 with explicit explanatory detail).
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.data_service import data_service

client = TestClient(app)


def test_api_competitions_list():
    res = client.get("/api/competitions")
    assert res.status_code == 200
    data = res.json()
    assert "competitions" in data
    assert data["default_competition"] == "ipl"
    comp_ids = [c["id"] for c in data["competitions"]]
    assert "ipl" in comp_ids
    assert "t20i" in comp_ids
    assert "smat" not in comp_ids


def test_api_seasons_multi_competition():
    # 1. Default (IPL)
    res_default = client.get("/api/seasons")
    assert res_default.status_code == 200
    data_default = res_default.json()
    assert "2024" in data_default["seasons"]
    assert data_default["total_seasons"] >= 15

    # 2. Explicit IPL
    res_ipl = client.get("/api/seasons?competition=ipl")
    assert res_ipl.status_code == 200
    data_ipl = res_ipl.json()
    assert data_ipl["seasons"] == data_default["seasons"]

    # 3. T20I populated seasons (2022+)
    res_t20i = client.get("/api/seasons?competition=t20i")
    assert res_t20i.status_code == 200
    data_t20i = res_t20i.json()
    assert "2024" in data_t20i["seasons"]
    assert len(data_t20i["seasons"]) >= 4

    # 4. SMAT temporarily deactivated -> 400
    res_smat = client.get("/api/seasons?competition=smat")
    assert res_smat.status_code == 400
    assert "temporarily deactivated" in res_smat.json()["detail"]


def test_api_teams_multi_competition():
    # IPL teams
    res_ipl = client.get("/api/teams?season=2024&competition=ipl")
    assert res_ipl.status_code == 200
    ipl_teams = res_ipl.json()["teams"]
    assert "Chennai Super Kings" in ipl_teams
    assert "Kolkata Knight Riders" in ipl_teams

    # T20I teams
    res_t20i = client.get("/api/teams?competition=t20i")
    assert res_t20i.status_code == 200
    t20i_teams = res_t20i.json()["teams"]
    assert "India" in t20i_teams
    assert "Australia" in t20i_teams
    assert "England" in t20i_teams

    # SMAT teams -> 400 (deactivated)
    res_smat = client.get("/api/teams?competition=smat")
    assert res_smat.status_code == 400
    assert "temporarily deactivated" in res_smat.json()["detail"]


def test_api_dashboard_summary_multi_competition():
    # IPL dashboard summary
    res_ipl = client.get("/api/dashboard/summary?season=2024&competition=ipl")
    assert res_ipl.status_code == 200
    data_ipl = res_ipl.json()
    assert data_ipl["total_players"] > 0
    assert data_ipl["total_batting_innings"] > 0

    # T20I dashboard summary
    res_t20i = client.get("/api/dashboard/summary?season=2024&competition=t20i")
    assert res_t20i.status_code == 200
    data_t20i = res_t20i.json()
    assert data_t20i["total_players"] > 0
    assert data_t20i["total_batting_innings"] > 0

    # SMAT dashboard summary -> 400 (deactivated)
    res_smat = client.get("/api/dashboard/summary?season=2023/24&competition=smat")
    assert res_smat.status_code == 400
    assert "temporarily deactivated" in res_smat.json()["detail"]


def test_api_players_multi_competition():
    res_ipl = client.get("/api/players?season=2024&competition=ipl")
    assert res_ipl.status_code == 200
    assert len(res_ipl.json()["players"]) > 0

    res_t20i = client.get("/api/players?season=2024&competition=t20i")
    assert res_t20i.status_code == 200
    assert len(res_t20i.json()["players"]) > 0

    # SMAT players -> 400 (deactivated)
    res_smat = client.get("/api/players?season=2023/24&competition=smat")
    assert res_smat.status_code == 400
    assert "temporarily deactivated" in res_smat.json()["detail"]


def test_api_matches_multi_competition():
    res_ipl = client.get("/api/matches?season=2024&competition=ipl")
    assert res_ipl.status_code == 200
    assert len(res_ipl.json()["matches"]) > 0

    res_t20i = client.get("/api/matches?competition=t20i")
    assert res_t20i.status_code == 200
    assert len(res_t20i.json()["matches"]) > 0

    # SMAT matches -> 400 (deactivated)
    res_smat = client.get("/api/matches?competition=smat")
    assert res_smat.status_code == 400
    assert "temporarily deactivated" in res_smat.json()["detail"]


def test_strict_dnb_preservation_across_competitions():
    # Verify in T20I season metrics that DNB entries have null average_contribution_score
    df_t20i = data_service.get_season_metrics_df(competition="t20i")
    dnb_t20i = df_t20i[df_t20i["batting_innings"] == 0]
    assert len(dnb_t20i) > 0, "Expected DNB entries in T20I"
    assert dnb_t20i["average_contribution_score"].isna().all()
    assert dnb_t20i["season_team_contribution_share"].isna().all()

    # Verify that directly querying SMAT data raises ValueError for deactivation
    with pytest.raises(ValueError, match="temporarily deactivated"):
        data_service.get_season_metrics_df(competition="smat")


def test_api_tournaments_and_filtering():
    # 1. /api/tournaments for t20i
    res_t20i = client.get("/api/tournaments?competition=t20i")
    assert res_t20i.status_code == 200
    data_t20i = res_t20i.json()
    assert "tournaments" in data_t20i
    assert "ICC Men's T20 World Cup" in data_t20i["tournaments"]
    assert any("Asia Cup" in t for t in data_t20i["tournaments"])

    # 2. Filter matches by ICC Men's T20 World Cup
    res_wc = client.get("/api/matches?competition=t20i&tournament=ICC Men's T20 World Cup&limit=300")
    assert res_wc.status_code == 200
    wc_matches = res_wc.json()["matches"]
    assert len(wc_matches) > 0
    assert all(m["event_name"] == "ICC Men's T20 World Cup" for m in wc_matches)

    # 3. Filter matches by Asia Cup (8 in 2022 + 11 in 2016 = 19 matches)
    res_asia = client.get("/api/matches?competition=t20i&tournament=Asia Cup&limit=300")
    assert res_asia.status_code == 200
    asia_matches = res_asia.json()["matches"]
    assert len(asia_matches) == 19
    assert all(m["event_name"] == "Asia Cup" for m in asia_matches)

    # 4. Tournaments for IPL
    res_ipl = client.get("/api/tournaments?competition=ipl")
    assert res_ipl.status_code == 200
    assert "Indian Premier League" in res_ipl.json()["tournaments"]

    # 5. Tournaments for SMAT -> 400 (deactivated)
    res_smat = client.get("/api/tournaments?competition=smat")
    assert res_smat.status_code == 400
    assert "temporarily deactivated" in res_smat.json()["detail"]


def test_smat_deactivation_across_all_endpoints():
    """Verify that all endpoints reject SMAT with HTTP 400 and never leak records."""
    endpoints = [
        "/api/seasons?competition=smat",
        "/api/teams?competition=smat",
        "/api/dashboard/summary?competition=smat",
        "/api/players?competition=smat",
        "/api/matches?competition=smat",
        "/api/tournaments?competition=smat",
        "/api/charts/scatter?competition=smat",
        "/api/matchups/rankings?competition=smat",
    ]
    for ep in endpoints:
        res = client.get(ep)
        assert res.status_code == 400, f"Expected 400 for {ep}, got {res.status_code}"
        assert "temporarily deactivated" in res.json()["detail"]
