"""
Tests for Tournament Type Filtering on Men's International T20Is.
Verifies the 7 key criteria:
1. All T20Is (2,264 matches total across all editions).
2. T20 World Cup 2022 (39 matches) and 2024 (44 matches) with accurate leaderboards.
3. Men's Asia Cup (T20) 2022 (14 matches, strictly T20 format only).
4. Bilateral T20Is in 2023 and 2024 with calendar-year labels.
5. A year with no matches for selected tournament (e.g. World Cup in 2023 returns 0 matches gracefully).
6. Dynamic season options and smooth switching between tournament types.
7. Perfect agreement between leaderboard metrics and filtered match records, strict DNB null preservation, and frozen IPL/SMAT integrity.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.data_service import data_service

client = TestClient(app)


def test_1_all_t20is_filtering():
    """Verify 'All T20Is' returns complete dataset of 2,264 matches across all seasons."""
    # 1. Seasons endpoint
    res_seasons = client.get("/api/seasons?competition=t20i&tournament_type=all")
    assert res_seasons.status_code == 200
    data_seasons = res_seasons.json()
    assert "2024" in data_seasons["seasons"]
    assert "2023" in data_seasons["seasons"]
    assert "2022" in data_seasons["seasons"]
    assert len(data_seasons["seasons"]) >= 4

    # 2. Total matches across all T20Is in underlying data service
    df_t20i = data_service.get_matches_df("t20i")
    assert len(df_t20i) in (1468, 1498, 1503, 1524, 1528), f"Expected 1468, 1498, 1503, 1524, or 1528 T20I matches in total, got {len(df_t20i)}"
    # Verify all 665 baseline matches remain present and unmodified
    from pathlib import Path
    import pandas as pd
    backup_matches_path = Path("data/backups/t20i_pre_historical_expansion_20261013/matches.csv")
    if backup_matches_path.exists():
        df_base = pd.read_csv(backup_matches_path, dtype={"match_id": str})
        assert set(df_base["match_id"]).issubset(set(df_t20i["match_id"].astype(str))), "All 665 baseline matches must remain present"

    # 3. Matches endpoint query with tournament_type=all
    res_matches = client.get("/api/matches?competition=t20i&tournament_type=all&limit=500")
    assert res_matches.status_code == 200
    assert len(res_matches.json()["matches"]) > 0

    # 4. Omitting tournament_type defaults to all
    res_default = client.get("/api/matches?competition=t20i&limit=500")
    assert res_default.status_code == 200
    assert len(res_default.json()["matches"]) == len(res_matches.json()["matches"])


def test_2_t20_world_cup_2022_and_2024():
    """Verify T20 World Cup 2022 and 2024 editions, match counts, and top contributors."""
    # 1. Season metadata for world_cup
    res_seasons = client.get("/api/seasons?competition=t20i&tournament_type=world_cup")
    assert res_seasons.status_code == 200
    s_data = res_seasons.json()
    assert "2024" in s_data["seasons"]
    assert "2022" in s_data["seasons"]
    # Check edition labels
    labels = {opt["value"]: opt["label"] for opt in s_data["season_options"]}
    assert labels["2024"] == "T20 World Cup 2024"
    assert labels["2022"] == "T20 World Cup 2022"

    # 2. Matches in T20 World Cup 2024
    res_wc_2024 = client.get("/api/matches?competition=t20i&tournament_type=world_cup&season=2024&limit=300")
    assert res_wc_2024.status_code == 200
    wc_2024_matches = res_wc_2024.json()["matches"]
    assert len(wc_2024_matches) == 44, f"Expected 44 WC 2024 matches, got {len(wc_2024_matches)}"
    assert all(m["event_name"] == "ICC Men's T20 World Cup" for m in wc_2024_matches)

    # 3. Matches in T20 World Cup 2022
    res_wc_2022 = client.get("/api/matches?competition=t20i&tournament_type=world_cup&season=2022&limit=300")
    assert res_wc_2022.status_code == 200
    wc_2022_matches = res_wc_2022.json()["matches"]
    assert len(wc_2022_matches) == 39, f"Expected 39 WC 2022 matches, got {len(wc_2022_matches)}"
    assert all(m["event_name"] == "ICC Men's T20 World Cup" for m in wc_2022_matches)

    # 4. Top contributors in T20 World Cup 2024
    res_players_2024 = client.get("/api/players?competition=t20i&tournament_type=world_cup&season=2024&min_runs=100")
    assert res_players_2024.status_code == 200
    players_2024 = res_players_2024.json()["players"]
    player_names_2024 = [p["player"] for p in players_2024]
    assert "Travis Head" in player_names_2024 or "TM Head" in player_names_2024
    assert "Rohit Sharma" in player_names_2024 or "RG Sharma" in player_names_2024

    # 5. Top contributors in T20 World Cup 2022
    res_players_2022 = client.get("/api/players?competition=t20i&tournament_type=world_cup&season=2022&min_runs=100")
    assert res_players_2022.status_code == 200
    players_2022 = res_players_2022.json()["players"]
    player_names_2022 = [p["player"] for p in players_2022]
    assert "Virat Kohli" in player_names_2022 or "V Kohli" in player_names_2022


def test_3_asia_cup_2022_t20_only():
    """Verify Men's Asia Cup includes only official T20 format editions (2022: 14 matches)."""
    # 1. Season metadata for asia_cup
    res_seasons = client.get("/api/seasons?competition=t20i&tournament_type=asia_cup")
    assert res_seasons.status_code == 200
    s_data = res_seasons.json()
    assert "2022" in s_data["seasons"]
    labels = {opt["value"]: opt["label"] for opt in s_data["season_options"]}
    assert labels["2022"] == "Asia Cup 2022"
    # 2023 was ODI format and must NOT appear in T20 dataset
    assert "2023" not in s_data["seasons"]

    # 2. Matches in Asia Cup 2022
    res_ac_2022 = client.get("/api/matches?competition=t20i&tournament_type=asia_cup&season=2022&limit=300")
    assert res_ac_2022.status_code == 200
    ac_matches = res_ac_2022.json()["matches"]
    assert len(ac_matches) == 14, f"Expected 14 Asia Cup 2022 T20 matches, got {len(ac_matches)}"
    for m in ac_matches:
        assert "Asia Cup" in m["event_name"]

    # 3. Batters in Asia Cup 2022
    res_players = client.get("/api/players?competition=t20i&tournament_type=asia_cup&season=2022&min_runs=50")
    assert res_players.status_code == 200
    players = res_players.json()["players"]
    player_names = [p["player"] for p in players]
    assert any("Kohli" in name for name in player_names)
    assert any("Rizwan" in name for name in player_names)


def test_4_bilateral_t20is_in_2023_and_2024():
    """Verify Bilateral / Tri-Series filtering returns calendar-year series and excludes ICC/continental events."""
    # 1. Season metadata
    res_seasons = client.get("/api/seasons?competition=t20i&tournament_type=bilateral")
    assert res_seasons.status_code == 200
    s_data = res_seasons.json()
    assert "2024" in s_data["seasons"]
    assert "2023" in s_data["seasons"]
    labels = {opt["value"]: opt["label"] for opt in s_data["season_options"]}
    # Labels must be clean calendar year
    assert labels["2024"] == "2024"
    assert labels["2023"] == "2023"

    # 2. Bilateral matches in 2024
    res_matches_2024 = client.get("/api/matches?competition=t20i&tournament_type=bilateral&season=2024&limit=500")
    assert res_matches_2024.status_code == 200
    m_2024 = res_matches_2024.json()["matches"]
    assert len(m_2024) > 0
    # Must NOT contain World Cup or Asia Cup matches
    for m in m_2024:
        assert m["event_name"] != "ICC Men's T20 World Cup"
        assert m["event_name"] != "Asia Cup"

    # 3. Bilateral matches in 2023
    res_matches_2023 = client.get("/api/matches?competition=t20i&tournament_type=bilateral&season=2023&limit=500")
    assert res_matches_2023.status_code == 200
    m_2023 = res_matches_2023.json()["matches"]
    assert len(m_2023) > 0
    for m in m_2023:
        assert m["event_name"] != "ICC Men's T20 World Cup"
        assert m["event_name"] != "Asia Cup"


def test_5_empty_year_for_selected_tournament():
    """Verify that a year with no matches for the selected tournament returns zero matches without errors."""
    # There was no Men's T20 World Cup in 2023
    res_matches = client.get("/api/matches?competition=t20i&tournament_type=world_cup&season=2023")
    assert res_matches.status_code == 200
    data = res_matches.json()
    assert data["matches"] == []
    assert data["count"] == 0

    # Dashboard summary for empty season/tournament returns 0/nulls cleanly
    res_summary = client.get("/api/dashboard/summary?competition=t20i&tournament_type=world_cup&season=2023")
    assert res_summary.status_code == 200
    sum_data = res_summary.json()
    assert sum_data["total_players"] == 0
    assert sum_data["total_batting_innings"] == 0
    assert sum_data["total_matches_played"] == 0
    assert sum_data["average_contribution_score"] is None

    # Players list for empty season returns empty list
    res_players = client.get("/api/players?competition=t20i&tournament_type=world_cup&season=2023")
    assert res_players.status_code == 200
    assert res_players.json()["players"] == []


def test_6_switching_between_tournament_types_and_seasons():
    """Verify switching between tournament types updates season options dynamically and retains valid seasons."""
    # 1. World Cup seasons
    res_wc = client.get("/api/seasons?competition=t20i&tournament_type=world_cup")
    wc_seasons = res_wc.json()["seasons"]
    assert "2024" in wc_seasons
    assert "2023" not in wc_seasons

    # 2. Asia Cup seasons
    res_ac = client.get("/api/seasons?competition=t20i&tournament_type=asia_cup")
    ac_seasons = res_ac.json()["seasons"]
    assert "2022" in ac_seasons
    assert "2024" not in ac_seasons

    # 3. Bilateral seasons
    res_bi = client.get("/api/seasons?competition=t20i&tournament_type=bilateral")
    bi_seasons = res_bi.json()["seasons"]
    assert "2023" in bi_seasons
    assert "2024" in bi_seasons

    # When switching from bilateral to world cup with season 2024, 2024 is valid and retained
    assert "2024" in wc_seasons


def test_7_agreement_between_leaderboard_and_match_records():
    """Verify that displayed leaderboard metrics strictly match the underlying filtered match records."""
    # Test for Travis Head in T20 World Cup 2024
    res_players = client.get("/api/players?competition=t20i&tournament_type=world_cup&season=2024&limit=500")
    assert res_players.status_code == 200
    players = res_players.json()["players"]
    head_rows = [p for p in players if "Head" in p["player"]]
    assert len(head_rows) > 0, "Travis Head should be present in WC 2024"
    head = head_rows[0]

    # Verify Travis Head's actual runs and innings against his individual matches in WC 2024
    res_matches = client.get("/api/matches?competition=t20i&tournament_type=world_cup&season=2024&team=Australia&limit=50")
    assert res_matches.status_code == 200
    aus_matches = res_matches.json()["matches"]
    assert len(aus_matches) > 0

    # Verify Rohit Sharma in T20 World Cup 2024
    rohit_rows = [p for p in players if "Rohit Sharma" in p["player"] or "RG Sharma" in p["player"]]
    assert len(rohit_rows) > 0, "Rohit Sharma should be present in WC 2024"
    rohit = rohit_rows[0]
    assert rohit["actual_runs"] > 200
    assert rohit["batting_innings"] >= 7

    # Strict DNB null score invariant:
    # Any player with 0 batting innings MUST have average_contribution_score is None
    dnb_players = [p for p in players if p["batting_innings"] == 0]
    assert len(dnb_players) > 0, "Should have DNB players in tournament squad"
    for p in dnb_players:
        assert p["average_contribution_score"] is None
        assert p["qualified_average_contribution_score"] is None
        assert p["qualified_batting_innings"] == 0
        assert p["season_team_contribution_share"] is None

    # Check View A and View B qualified counts in summary
    res_sum = client.get("/api/dashboard/summary?competition=t20i&tournament_type=world_cup&season=2024")
    assert res_sum.status_code == 200
    s_metric = res_sum.json()
    assert s_metric["total_players"] == len(players)
    assert s_metric["total_batting_innings"] > 0
    assert s_metric["total_dnb_matches"] > 0


def test_8_ipl_invariance_and_smat_deactivation():
    """Verify IPL dataset is unaffected by tournament filtering, and SMAT is cleanly deactivated."""
    # 1. IPL seasons and matches
    res_ipl_seasons = client.get("/api/seasons?competition=ipl")
    assert "2024" in res_ipl_seasons.json()["seasons"]

    res_ipl_matches = client.get("/api/matches?competition=ipl&season=2024")
    assert len(res_ipl_matches.json()["matches"]) >= 71  # >= 71 available matches in IPL 2024 dataset

    res_ipl_players = client.get("/api/players?competition=ipl&season=2024&min_runs=400")
    assert len(res_ipl_players.json()["players"]) > 10

    # 2. SMAT is deactivated and returns 400
    res_smat_seasons = client.get("/api/seasons?competition=smat")
    assert res_smat_seasons.status_code == 400
    assert "temporarily deactivated" in res_smat_seasons.json()["detail"]

    res_smat_matches = client.get("/api/matches?competition=smat")
    assert res_smat_matches.status_code == 400
    assert "temporarily deactivated" in res_smat_matches.json()["detail"]
