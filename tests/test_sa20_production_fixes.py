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
    # Verify default SA20 thresholds and explanatory rule text
    assert body["filters"]["min_balls"] == 30
    assert body["filters"]["min_runs"] == 40
    assert body["filters"]["eligibility_rule"] == "Minimum sample rule: 30 legal balls OR 40 runs."

    # Detail for H Klaasen
    resp_player = client.get("/api/matchups/player/H%20Klaasen?competition=sa20")
    assert resp_player.status_code == 200
    body_p = resp_player.json()
    assert body_p["batter"] == "H Klaasen"
    assert body_p["pace"]["runs"] > 0
    assert body_p["eligibility_rule"] == "Minimum sample rule: 30 legal balls OR 40 runs."
    assert body_p["pace"]["is_eligible"] is True
    assert body_p["spin"]["is_eligible"] is True


def test_sa20_eligibility_boundary_rules():
    """
    Validate SA20 Matchups eligibility boundary rules:
    - Rule: legal_balls_faced >= 30 OR runs_scored >= 40.
    - Boundaries:
      1. 29 balls and 39 runs -> ineligible.
      2. 30 balls and 20 runs -> eligible.
      3. 10 balls and 40 runs -> eligible.
      4. 29 balls and 39 runs must remain ineligible.
    - Thresholds evaluated separately for Pace and Spin.
    - IPL thresholds (100 balls or 80 runs) remain untouched.
    """
    import pandas as pd
    from src.bowling_classification import classify_bowler

    rows = []

    # 1. Bat_29B_39R (Pace): 29 legal balls, 39 runs
    # 19 balls of 1 run (19R) + 10 balls of 2 runs (20R) = 29B, 39R
    for i in range(19):
        rows.append({"match_id": 1, "season": "2024", "innings_number": 1, "over": 1, "ball": i + 1,
                     "batting_team": "T1", "bowling_team": "T2", "batter": "Bat_29B_39R", "bowler": "JJ Bumrah",
                     "batter_runs": 1, "wides": 0, "noballs": 0})
    for i in range(10):
        rows.append({"match_id": 1, "season": "2024", "innings_number": 1, "over": 2, "ball": i + 1,
                     "batting_team": "T1", "bowling_team": "T2", "batter": "Bat_29B_39R", "bowler": "JJ Bumrah",
                     "batter_runs": 2, "wides": 0, "noballs": 0})

    # 2. Bat_30B_20R (Pace): 30 legal balls, 20 runs
    # 20 balls of 1 run (20R) + 10 balls of 0 runs (0R) = 30B, 20R
    for i in range(20):
        rows.append({"match_id": 1, "season": "2024", "innings_number": 1, "over": 3, "ball": i + 1,
                     "batting_team": "T1", "bowling_team": "T2", "batter": "Bat_30B_20R", "bowler": "JJ Bumrah",
                     "batter_runs": 1, "wides": 0, "noballs": 0})
    for i in range(10):
        rows.append({"match_id": 1, "season": "2024", "innings_number": 1, "over": 4, "ball": i + 1,
                     "batting_team": "T1", "bowling_team": "T2", "batter": "Bat_30B_20R", "bowler": "JJ Bumrah",
                     "batter_runs": 0, "wides": 0, "noballs": 0})

    # 3. Bat_10B_40R (Pace): 10 legal balls, 40 runs
    # 10 balls of 4 runs = 10B, 40R
    for i in range(10):
        rows.append({"match_id": 1, "season": "2024", "innings_number": 1, "over": 5, "ball": i + 1,
                     "batting_team": "T1", "bowling_team": "T2", "batter": "Bat_10B_40R", "bowler": "JJ Bumrah",
                     "batter_runs": 4, "wides": 0, "noballs": 0})

    # 4. Bat_Spin_Split: Eligible vs Pace (30B, 20R) but Ineligible vs Spin (29B, 39R)
    # vs Pace: 30 balls, 20 runs
    for i in range(20):
        rows.append({"match_id": 1, "season": "2024", "innings_number": 1, "over": 6, "ball": i + 1,
                     "batting_team": "T1", "bowling_team": "T2", "batter": "Bat_Split", "bowler": "JJ Bumrah",
                     "batter_runs": 1, "wides": 0, "noballs": 0})
    for i in range(10):
        rows.append({"match_id": 1, "season": "2024", "innings_number": 1, "over": 7, "ball": i + 1,
                     "batting_team": "T1", "bowling_team": "T2", "batter": "Bat_Split", "bowler": "JJ Bumrah",
                     "batter_runs": 0, "wides": 0, "noballs": 0})
    # vs Spin: 29 balls, 39 runs (Rashid Khan is classified Spin)
    for i in range(19):
        rows.append({"match_id": 1, "season": "2024", "innings_number": 1, "over": 8, "ball": i + 1,
                     "batting_team": "T1", "bowling_team": "T2", "batter": "Bat_Split", "bowler": "Rashid Khan",
                     "batter_runs": 1, "wides": 0, "noballs": 0})
    for i in range(10):
        rows.append({"match_id": 1, "season": "2024", "innings_number": 1, "over": 9, "ball": i + 1,
                     "batting_team": "T1", "bowling_team": "T2", "batter": "Bat_Split", "bowler": "Rashid Khan",
                     "batter_runs": 2, "wides": 0, "noballs": 0})

    df = pd.DataFrame(rows)
    df["bowling_type"] = df["bowler"].map(classify_bowler)
    df["is_legal"] = (df["wides"] == 0) & (df["noballs"] == 0)

    # --- Test SA20 default eligibility rule (30B or 40R) ---
    res_sa20 = compute_matchup_rankings(competition="sa20", deliveries_df=df)
    pace_batters = [r["batter"] for r in res_sa20["results"]["pace"]["rankings"]]
    spin_batters = [r["batter"] for r in res_sa20["results"]["spin"]["rankings"]]

    # Boundary 1: 29 balls and 39 runs -> ineligible
    assert "Bat_29B_39R" not in pace_batters
    # Boundary 2: 30 balls and 20 runs -> eligible
    assert "Bat_30B_20R" in pace_batters
    # Boundary 3: 10 balls and 40 runs -> eligible
    assert "Bat_10B_40R" in pace_batters
    # Boundary 4: 29 balls and 39 runs must remain ineligible
    assert "Bat_29B_39R" not in pace_batters

    # Separate thresholds for Pace and Spin:
    # Bat_Split has 30B/20R vs Pace (eligible) and 29B/39R vs Spin (ineligible)
    assert "Bat_Split" in pace_batters
    assert "Bat_Split" not in spin_batters

    # Verify batter detail reflects separate eligibility
    detail_split = get_batter_matchup_detail("Bat_Split", competition="sa20", deliveries_df=df)
    assert detail_split is not None
    assert detail_split["pace"]["balls"] == 30
    assert detail_split["pace"]["runs"] == 20
    assert detail_split["pace"]["is_eligible"] is True
    assert detail_split["spin"]["balls"] == 29
    assert detail_split["spin"]["runs"] == 39
    assert detail_split["spin"]["is_eligible"] is False
    assert detail_split["eligibility_rule"] == "Minimum sample rule: 30 legal balls OR 40 runs."

    detail_ineligible = get_batter_matchup_detail("Bat_29B_39R", competition="sa20", deliveries_df=df)
    assert detail_ineligible is not None
    assert detail_ineligible["pace"]["balls"] == 29
    assert detail_ineligible["pace"]["runs"] == 39
    assert detail_ineligible["pace"]["is_eligible"] is False

    # --- Test IPL rule (100B or 80R) remains unchanged ---
    res_ipl = compute_matchup_rankings(competition="ipl", deliveries_df=df)
    ipl_pace_batters = [r["batter"] for r in res_ipl["results"]["pace"]["rankings"]]
    # None of these batters should qualify under IPL (since all have balls < 100 AND runs < 80)
    assert "Bat_29B_39R" not in ipl_pace_batters
    assert "Bat_30B_20R" not in ipl_pace_batters
    assert "Bat_10B_40R" not in ipl_pace_batters
    assert "Bat_Split" not in ipl_pace_batters

def test_player_analysis_api_season_with_slash():
    """Verify player endpoints can handle seasons with slashes (e.g. SA20 2025/26)."""
    # Test encoded slash
    resp = client.get("/api/player/H%20Klaasen/season/2025%2F26?competition=sa20")
    assert resp.status_code == 200
    data = resp.json()
    assert data["player"] == "H Klaasen"
    assert data["season"] == "2025/26"


def test_sa20_ground_analysis_phase_metrics_populated():
    """Verify SA20 Ground Analysis returns populated phase metrics and sample counts."""
    # Reset cached phases data to guarantee fresh test
    ground_service._phases_data = None
    ground_service._matches_cache = None

    response = client.get("/api/ground-analysis/venue/Newlands%2C+Cape+Town?competition=sa20")
    assert response.status_code == 200
    data = response.json()
    assert "phase_analysis" in data
    pa = data["phase_analysis"]

    # Scope disclosure
    sc = pa["scope_summary"]
    assert sc["total_matches_in_period"] == 23
    assert sc["eligible_standard_matches"] == 21
    assert sc["excluded_matches"] == 2

    # Combined phases
    comb = pa["combined"]
    pp = comb["powerplay"]
    mid = comb["middle"]
    dth = comb["death"]

    assert pp["sample_innings"] == 42
    assert pp["sample_matches"] == 21
    assert pp["avg_runs"] == 47.8
    assert pp["run_rate"] == 7.97
    assert pp["avg_wickets"] == 1.33

    assert mid["sample_innings"] == 37
    assert mid["sample_matches"] == 21
    assert mid["avg_runs"] == 70.7
    assert mid["run_rate"] == 7.86

    assert dth["sample_innings"] == 23
    assert dth["sample_matches"] == 19
    assert dth["avg_runs"] == 49.9
    assert dth["run_rate"] == 9.98

    # 1st vs 2nd innings separation
    first_pp = pa["first_innings"]["powerplay"]
    second_pp = pa["second_innings"]["powerplay"]
    assert first_pp["sample_innings"] == 21
    assert second_pp["sample_innings"] == 21
    assert first_pp["avg_runs"] is not None
    assert second_pp["avg_runs"] is not None

    # Progression insights
    prog = pa["progression_insights"]
    assert prog["is_reliable"] is True
    assert prog["powerplay_run_rate"] == 7.97
    assert prog["middle_run_rate"] == 7.86
    assert prog["death_run_rate"] == 9.98

    # Year trends
    y_trends = pa["year_trends"]
    years = [y["year"] for y in y_trends]
    assert 2023 in years
    assert 2024 in years
    assert 2025 in years
    assert 2026 in years
    for y in y_trends:
        assert y["powerplay_avg_runs"] is not None
        assert y["middle_avg_runs"] is not None


def test_sa20_ground_analysis_all_six_venues():
    """Verify all 6 SA20 venues return populated phase metrics for standard 20-over matches."""
    venues = [
        "Newlands, Cape Town",
        "The Wanderers Stadium, Johannesburg",
        "SuperSport Park, Centurion",
        "Kingsmead, Durban",
        "Boland Park, Paarl",
        "St George's Park, Gqeberha",
    ]

    for v in venues:
        res = client.get(f"/api/ground-analysis/venue/{v}?competition=sa20")
        assert res.status_code == 200, f"Failed for venue {v}"
        pa = res.json()["phase_analysis"]
        comb = pa["combined"]
        assert comb["powerplay"]["sample_innings"] > 0, f"Powerplay 0 for {v}"
        assert comb["middle"]["sample_innings"] > 0, f"Middle 0 for {v}"
        assert comb["death"]["sample_innings"] > 0, f"Death 0 for {v}"
        assert comb["powerplay"]["avg_runs"] > 0, f"PP avg runs invalid for {v}"
        assert comb["middle"]["avg_runs"] > 0, f"Mid avg runs invalid for {v}"
        assert comb["death"]["avg_runs"] > 0, f"Death avg runs invalid for {v}"


def test_ground_analysis_competition_isolation_and_ipl_preservation():
    """Verify competition isolation: SA20 does not pollute IPL or T20I phase metrics."""
    # IPL Wankhede
    res_ipl = client.get("/api/ground-analysis/venue/Wankhede Stadium, Mumbai?competition=ipl")
    assert res_ipl.status_code == 200
    pa_ipl = res_ipl.json()["phase_analysis"]
    # IPL Wankhede combined powerplay has 96 sample innings and 52.8 avg runs
    assert pa_ipl["combined"]["powerplay"]["sample_innings"] == 96
    assert pa_ipl["combined"]["powerplay"]["avg_runs"] == 52.8

    # SuperSport Park with SA20 vs T20I
    res_sa20 = client.get("/api/ground-analysis/venue/SuperSport Park, Centurion?competition=sa20")
    assert res_sa20.status_code == 200
    pa_sa20 = res_sa20.json()["phase_analysis"]
    # SuperSport Park in SA20 has 21 eligible standard matches
    assert pa_sa20["scope_summary"]["eligible_standard_matches"] == 21
    assert pa_sa20["combined"]["powerplay"]["sample_innings"] == 42
    for m in res_sa20.json()["recent_matches"]:
        assert m["competition_code"] == "sa20"
