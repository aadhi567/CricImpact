import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.ground_service import ground_service
from src.matchup_analytics import compute_matchup_rankings, get_batter_matchup_detail

client = TestClient(app)

def test_ground_analysis_sa20_venues():
    """Verify SA20 venues are indexed and returned when competition=sa20."""
    response = client.get("/api/ground-analysis/venues?competition=sa20")
    assert response.status_code == 200
    data = response.json()
    assert data["total_venues"] == 6
    venue_ids = [v["id"] for v in data["venues"]]
    assert any("Wanderers" in v for v in venue_ids)
    assert any("Kingsmead" in v for v in venue_ids)
    assert any("SuperSport" in v or "Centurion" in v for v in venue_ids)

def test_ground_analysis_venue_with_plus_encoding():
    """Verify venue paths containing '+' as spaces are properly handled without 502/404."""
    # Test Wankhede Stadium with '+' encoding
    response = client.get("/api/ground-analysis/venue/Wankhede+Stadium%2C+Mumbai")
    assert response.status_code == 200
    data = response.json()
    assert "Wankhede" in data["venue_info"]["name"]
    assert data["summary"]["total_matches_in_period"] > 0

    # Test an SA20 venue
    response = client.get("/api/ground-analysis/venue/Wanderers+Stadium%2C+Johannesburg?competition=sa20")
    assert response.status_code == 200
    data_sa20 = response.json()
    assert "Wanderers" in data_sa20["venue_info"]["name"]
    assert data_sa20["summary"]["total_matches_in_period"] > 0
    # Verify competition label on match list
    for match in data_sa20["recent_matches"]:
        assert match["competition"] == "SA20"

def test_sa20_pace_vs_spin_matchups_isolation():
    """Verify SA20 matchups use SA20 deliveries only and do not mix IPL data."""
    sa20_rankings = compute_matchup_rankings(competition="sa20", min_balls=20, min_runs=20)
    assert "results" in sa20_rankings
    pace_batters = [r["batter"] for r in sa20_rankings["results"]["pace"]["rankings"]]
    spin_batters = [r["batter"] for r in sa20_rankings["results"]["spin"]["rankings"]]

    # H Klaasen is a prominent SA20 batter
    assert "H Klaasen" in pace_batters or "H Klaasen" in spin_batters
    # V Kohli does not play in SA20 and must NOT be in SA20 rankings
    assert "V Kohli" not in pace_batters
    assert "V Kohli" not in spin_batters

def test_sa20_matchups_api_endpoints():
    """Test API endpoints for SA20 matchup rankings and player detail."""
    resp = client.get("/api/matchups/rankings?competition=sa20")
    assert resp.status_code == 200
    body = resp.json()
    assert "results" in body
    assert "pace" in body["results"]
    assert len(body["results"]["pace"]["rankings"]) > 0

    # Detail for H Klaasen
    resp_player = client.get("/api/matchups/player/H%20Klaasen?competition=sa20")
    assert resp_player.status_code == 200
    body_p = resp_player.json()
    assert body_p["batter"] == "H Klaasen"
    assert body_p["pace"]["runs"] > 0

def test_player_analysis_api_season_with_slash():
    """Verify player endpoints can handle seasons with slashes (e.g. SA20 2025/26)."""
    # Test encoded slash
    resp = client.get("/api/player/H%20Klaasen/season/2025%2F26?competition=sa20")
    assert resp.status_code == 200
    data = resp.json()
    assert data["player"] == "H Klaasen"
    assert data["season"] == "2025/26"
