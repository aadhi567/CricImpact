"""
Tests for FastAPI Matchup Analytics Endpoints.
"""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_matchup_rankings_endpoint():
    res = client.get("/api/matchups/rankings?min_balls=100&min_runs=80")
    assert res.status_code == 200
    data = res.json()
    assert "filters" in data
    assert "results" in data
    assert "pace" in data["results"]
    assert "spin" in data["results"]

    pace_ranks = data["results"]["pace"]["rankings"]
    spin_ranks = data["results"]["spin"]["rankings"]

    assert len(pace_ranks) > 0
    assert len(spin_ranks) > 0

    # Check structure of top row
    top_pace = pace_ranks[0]
    assert "rank" in top_pace
    assert "batter" in top_pace
    assert "balls" in top_pace
    assert "runs" in top_pace
    assert "strike_rate" in top_pace
    assert top_pace["rank"] == 1
    assert (top_pace["balls"] >= 100) or (top_pace["runs"] >= 80)


def test_matchup_rankings_season_filter():
    res = client.get("/api/matchups/rankings?season=2024&min_balls=50&min_runs=40")
    assert res.status_code == 200
    data = res.json()
    assert data["filters"]["season"] == "2024"
    assert "pace" in data["results"]
    assert "spin" in data["results"]


def test_batter_matchup_detail_endpoint():
    res = client.get("/api/matchups/player/V%20Kohli")
    assert res.status_code == 200
    data = res.json()
    assert data["batter"] == "V Kohli"
    assert "pace" in data
    assert "spin" in data
    assert "difference" in data
    assert data["pace"]["runs"] > 0
    assert data["spin"]["runs"] > 0
    assert "advantage_text" in data["difference"]


def test_batter_matchup_detail_not_found():
    res = client.get("/api/matchups/player/NonExistentPlayerXYZ")
    assert res.status_code == 404
