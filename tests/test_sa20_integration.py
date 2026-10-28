"""
Comprehensive integration and regression tests for SA20 competition in CricImpact.
Verifies:
1. Dataset artifact presence, completeness (130 matches, 29,020 deliveries), and DNB preservation.
2. Complete competition isolation (SA20 matches never leak into IPL, T20I, or SMAT totals).
3. Production API endpoints for SA20: competitions, seasons, teams, dashboard summary,
   matches, players, player comparison, career analytics, and ground analysis.
4. Strategy 4 contribution bounds [0.0, 100.0] and DNB null score invariants.
"""

from pathlib import Path
import pytest
import pandas as pd
from fastapi.testclient import TestClient

from app.main import app
from app.services.data_service import data_service
from app.services.ground_service import ground_service

client = TestClient(app)

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
SA20_DIR = DATA_DIR / "sa20"


def test_sa20_dataset_artifacts_exist():
    """Verify all 5 required processed SA20 artifacts exist and meet schema requirements."""
    matches_csv = SA20_DIR / "matches.csv"
    rosters_csv = SA20_DIR / "match_rosters.csv"
    contrib_csv = SA20_DIR / "batter_match_contributions.csv"
    delivs_csv = SA20_DIR / "deliveries.csv"
    metrics_csv = SA20_DIR / "phase6_season_metrics.csv"

    assert matches_csv.exists(), "matches.csv must exist"
    assert rosters_csv.exists(), "match_rosters.csv must exist"
    assert contrib_csv.exists(), "batter_match_contributions.csv must exist"
    assert delivs_csv.exists(), "deliveries.csv must exist"
    assert metrics_csv.exists(), "phase6_season_metrics.csv must exist"

    df_matches = pd.read_csv(matches_csv)
    assert len(df_matches) == 130, f"Expected 130 SA20 matches, got {len(df_matches)}"

    df_delivs = pd.read_csv(delivs_csv)
    assert len(df_delivs) == 29020, f"Expected 29,020 SA20 deliveries, got {len(df_delivs)}"

    df_contrib = pd.read_csv(contrib_csv)
    assert len(df_contrib) == 2031, f"Expected 2,031 contribution rows, got {len(df_contrib)}"

    df_rosters = pd.read_csv(rosters_csv)
    assert len(df_rosters) == 2860, f"Expected 2,860 roster rows (130 * 22), got {len(df_rosters)}"


def test_sa20_dnb_and_contribution_bounds():
    """Verify Strategy 4 invariants: bounds in [0.0, 100.0] and DNB null preservation."""
    df_contrib = pd.read_csv(SA20_DIR / "batter_match_contributions.csv")
    scores = df_contrib["contribution_score"].dropna()
    assert (scores >= 0.0).all() and (scores <= 100.0).all(), "Contribution scores must be strictly bounded in [0.0, 100.0]"

    # Verify season metrics DNB rules
    df_metrics = pd.read_csv(SA20_DIR / "phase6_season_metrics.csv")
    dnb_rows = df_metrics[df_metrics["batting_innings"] == 0]
    assert len(dnb_rows) == 30, f"Expected 30 DNB season records in SA20, got {len(dnb_rows)}"
    assert dnb_rows["average_contribution_score"].isna().all(), "DNB rows must have NaN average_contribution_score"
    assert dnb_rows["season_team_contribution_share"].isna().all(), "DNB rows must have NaN season_team_contribution_share"


def test_sa20_isolation_from_ipl_and_t20i():
    """Regression test ensuring SA20 match IDs and records NEVER leak into IPL, T20I, or SMAT."""
    sa20_matches = set(pd.read_csv(SA20_DIR / "matches.csv")["match_id"].astype(str))

    # IPL isolation
    ipl_matches_df = data_service.get_matches_df("ipl")
    ipl_match_ids = set(ipl_matches_df["match_id"].astype(str))
    overlap_ipl = sa20_matches.intersection(ipl_match_ids)
    assert not overlap_ipl, f"SA20 match IDs leaked into IPL dataset: {overlap_ipl}"

    # T20I isolation
    t20i_matches_df = data_service.get_matches_df("t20i")
    t20i_match_ids = set(t20i_matches_df["match_id"].astype(str))
    overlap_t20i = sa20_matches.intersection(t20i_match_ids)
    assert not overlap_t20i, f"SA20 match IDs leaked into T20I dataset: {overlap_t20i}"

    # Verify querying IPL does not return SA20 matches
    res_ipl = client.get("/api/matches?competition=ipl&limit=1000")
    assert res_ipl.status_code == 200
    returned_mids = {str(m["match_id"]) for m in res_ipl.json()["matches"]}
    assert not sa20_matches.intersection(returned_mids), "API /api/matches?competition=ipl returned SA20 matches!"

    # Verify SMAT remains deactivated
    res_smat = client.get("/api/matches?competition=smat")
    assert res_smat.status_code == 400
    assert "temporarily deactivated" in res_smat.json()["detail"]


def test_api_competitions_includes_sa20():
    """Verify /api/competitions registers SA20 alongside IPL and T20I."""
    res = client.get("/api/competitions")
    assert res.status_code == 200
    comps = res.json()["competitions"]
    comp_map = {c["id"]: c for c in comps}
    assert "sa20" in comp_map
    sa20 = comp_map["sa20"]
    assert sa20["code"] == "SA20"
    assert sa20["type"] == "franchise"
    assert sa20["default_season"] == "2025/26"


def test_api_sa20_coverage():
    """Verify /api/competitions/coverage returns accurate SA20 dataset bounds."""
    res = client.get("/api/competitions/coverage?competition=sa20")
    assert res.status_code == 200
    data = res.json()
    assert data["competition"] == "sa20"
    assert data["total_matches"] == 130
    assert data["valid_date_matches"] == 130
    assert data["start_date"] == "2023-01-10"
    assert data["end_date"] == "2026-01-25"
    assert data["reliable"] is True


def test_api_sa20_seasons():
    """Verify /api/seasons?competition=sa20 returns the 4 historical SA20 seasons."""
    res = client.get("/api/seasons?competition=sa20")
    assert res.status_code == 200
    data = res.json()
    expected_seasons = ["2025/26", "2024/25", "2023/24", "2022/23"]
    assert data["seasons"] == expected_seasons
    assert data["default_season"] == "2025/26"
    assert data["competition"] == "sa20"


def test_api_sa20_teams():
    """Verify /api/teams?competition=sa20 returns all 6 official SA20 franchises."""
    res = client.get("/api/teams?competition=sa20")
    assert res.status_code == 200
    teams = res.json()["teams"]
    expected_teams = [
        "Durban's Super Giants",
        "Joburg Super Kings",
        "MI Cape Town",
        "Paarl Royals",
        "Pretoria Capitals",
        "Sunrisers Eastern Cape",
    ]
    assert sorted(teams) == sorted(expected_teams)


def test_api_sa20_dashboard_summary():
    """Verify /api/dashboard/summary?competition=sa20 returns valid aggregate metrics."""
    res = client.get("/api/dashboard/summary?competition=sa20&season=2025/26")
    assert res.status_code == 200
    summary = res.json()
    assert summary["season"] == "2025/26"
    assert summary["total_players"] > 0
    assert summary["total_batting_innings"] > 0
    assert summary["total_matches_played"] > 0
    assert summary["average_contribution_score"] > 0.0


def test_api_sa20_matches_endpoint():
    """Verify /api/matches?competition=sa20 returns correctly structured match records."""
    res = client.get("/api/matches?competition=sa20&season=2025/26")
    assert res.status_code == 200
    data = res.json()
    matches = data["matches"]
    assert len(matches) == 31  # 2025/26 has 31 played matches
    sample = matches[0]
    assert "match_id" in sample
    assert sample["season"] == "2025/26"
    assert sample["event_name"] == "SA20"
    assert sample["winner"] is not None


def test_api_sa20_players_and_comparison():
    """Verify player season endpoints and player comparison for SA20."""
    res_players = client.get("/api/players?competition=sa20&season=2025/26")
    assert res_players.status_code == 200
    players = res_players.json()["players"]
    assert len(players) > 0
    player_names = {p["player"] for p in players}
    assert "H Klaasen" in player_names

    # Comparison endpoint
    res_comp = client.get("/api/contribution/compare?players=H Klaasen,AK Markram&season=2025/26&competition=sa20")
    assert res_comp.status_code == 200
    comp_data = res_comp.json()
    assert len(comp_data["players"]) == 2
    for p in comp_data["players"]:
        assert p["balls_faced"] > 0
        assert p["dot_ball_percentage"] is not None
        assert p["powerplay_strike_rate"] is not None or p["middle_over_strike_rate"] is not None or p["death_over_strike_rate"] is not None


def test_api_sa20_career_integration():
    """Verify player career trajectory and multi-competition timeline with SA20."""
    # Career search
    res_search = client.get("/api/players/search?q=Klaasen")
    assert res_search.status_code == 200
    results = res_search.json()
    klaasen = next((p for p in results if p["player"] == "H Klaasen"), None)
    assert klaasen is not None
    assert klaasen["has_sa20"] is True
    assert "sa20" in klaasen["competitions"]

    # SA20 standalone career view
    res_career_sa20 = client.get("/api/player/H%20Klaasen/career?competition=sa20")
    assert res_career_sa20.status_code == 200
    c_sa20 = res_career_sa20.json()
    assert len(c_sa20["timeline"]) == 4  # Played in all 4 seasons
    assert c_sa20["available_competitions"]["sa20"] is True

    # Combined career view includes SA20
    res_career_comb = client.get("/api/player/H%20Klaasen/career?competition=combined")
    assert res_career_comb.status_code == 200
    c_comb = res_career_comb.json()
    timeline_years = {entry["season"]: entry for entry in c_comb["timeline"]}
    # '2023' year has SA20 runs
    assert "2023" in timeline_years
    assert timeline_years["2023"]["sa20_runs"] is not None
    assert timeline_years["2023"]["sa20_runs"] > 0
    assert "SA20" in timeline_years["2023"]["competition"]


def test_api_sa20_ground_analysis():
    """Verify Ground Analysis endpoint supports SA20 venues."""
    res_venues = client.get("/api/ground-analysis/venues?competition=sa20")
    assert res_venues.status_code == 200
    venues_data = res_venues.json()
    assert venues_data["competition"] == "sa20"
    assert len(venues_data["venues"]) == 6
    venue_names = {v["name"] for v in venues_data["venues"]}
    assert "The Wanderers Stadium, Johannesburg" in venue_names
    assert "Newlands, Cape Town" in venue_names

    # Detail analysis for an SA20 venue
    res_detail = client.get("/api/ground-analysis/venue/Newlands,%20Cape%20Town?competition=sa20&period=all_time")
    assert res_detail.status_code == 200
    detail = res_detail.json()
    assert detail["filters"]["competition"] == "sa20"
    assert detail["summary"]["total_matches_in_period"] > 0
    assert detail["scoring_profile"]["first_innings"]["sample_count"] > 0
    assert detail["chase_vs_defend"]["total_matches"] > 0
