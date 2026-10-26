"""
Regression Test Suite for Pace vs Spin Analytics in International Cricket (T20I) & IPL.
Proves that:
1. IPL Pace/Spin metrics remain completely unchanged.
2. T20I Pace/Spin metrics are accurately populated for players with qualifying deliveries.
3. Multiple international players and seasons are handled correctly.
4. Career totals mathematically agree with sum of seasonal aggregates.
5. Players with no qualifying observations show unavailable data (None), not fabricated zeros.
6. Classification coverage is distinct from batting observation coverage.
7. Production container environment (no raw JSON match files) works without failure.
"""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.services.data_service import data_service

client = TestClient(app)


def test_ipl_pace_spin_metrics_unchanged():
    """Verifies that IPL Pace/Spin metrics remain exact and untouched."""
    res = client.get("/api/player/V%20Kohli/career?competition=ipl")
    assert res.status_code == 200
    trends = res.json()["bowling_type_trends"]
    summary = trends["summary"]

    assert summary["total_balls_faced"] == 6930
    assert summary["classified_balls_faced"] == 6930
    assert summary["unclassified_balls_faced"] == 0
    assert summary["coverage_percentage"] == 100.0
    assert summary["is_coverage_complete"] is True

    pace = summary["pace"]
    assert pace["balls_faced"] == 4208
    assert pace["runs"] == 5924
    assert pace["strike_rate"] == 140.8
    assert pace["dismissals"] == 161
    assert pace["average"] == 36.8

    spin = summary["spin"]
    assert spin["balls_faced"] == 2722
    assert spin["runs"] == 3422
    assert spin["strike_rate"] == 125.7
    assert spin["dismissals"] == 61
    assert spin["average"] == 56.1

    assert summary["pace_dismissals"] == 161
    assert summary["spin_dismissals"] == 61
    assert summary["bowler_credited_dismissals"] == 222
    assert summary["dismissals_coverage_percentage"] == 100.0


def test_t20i_pace_spin_populated_for_qualifying_players():
    """Verifies that T20I Pace/Spin metrics are populated from deliveries dataset."""
    res = client.get("/api/player/V%20Kohli/career?competition=t20i")
    assert res.status_code == 200
    trends = res.json()["bowling_type_trends"]
    summary = trends["summary"]

    assert summary["total_balls_faced"] == 2917
    assert summary["classified_balls_faced"] == 1975
    assert summary["unclassified_balls_faced"] == 942
    assert summary["coverage_percentage"] == 67.7
    assert summary["is_coverage_complete"] is False

    pace = summary["pace"]
    assert pace["balls_faced"] == 1323
    assert pace["runs"] == 1957
    assert pace["strike_rate"] == 147.9
    assert pace["dismissals"] == 34
    assert pace["average"] == 57.6

    spin = summary["spin"]
    assert spin["balls_faced"] == 652
    assert spin["runs"] == 802
    assert spin["strike_rate"] == 123.0
    assert spin["dismissals"] == 14
    assert spin["average"] == 57.3

    assert summary["pace_dismissals"] == 34
    assert summary["spin_dismissals"] == 14
    assert summary["unclassified_dismissals"] == 28
    assert summary["bowler_credited_dismissals"] == 76
    assert summary["dismissals_coverage_percentage"] == 63.2

    # Verify seasons
    seasons = trends["seasons"]
    assert len(seasons) == 14
    s2024 = next((s for s in seasons if s["season"] == "2024"), None)
    assert s2024 is not None
    assert s2024["competition"] == "International"
    assert s2024["total_balls_faced"] == 110
    assert s2024["pace"]["runs"] == 74
    assert s2024["pace"]["balls_faced"] == 58
    assert s2024["pace"]["strike_rate"] == 127.6
    assert s2024["spin"]["runs"] == 32
    assert s2024["spin"]["balls_faced"] == 25
    assert s2024["spin"]["strike_rate"] == 128.0


def test_multiple_international_players_and_seasons():
    """Verifies that multiple international players and seasons are correctly calculated."""
    players = ["Babar Azam", "JC Buttler", "RG Sharma", "SA Yadav", "DA Warner"]
    for p in players:
        res = client.get(f"/api/player/{p.replace(' ', '%20')}/career?competition=t20i")
        assert res.status_code == 200, f"Failed for player {p}"
        data = res.json()
        assert "bowling_type_trends" in data
        trends = data["bowling_type_trends"]
        summary = trends["summary"]

        assert summary["total_balls_faced"] > 1000, f"{p} total balls too low"
        assert summary["pace"]["balls_faced"] > 500, f"{p} pace balls too low"
        assert summary["spin"]["balls_faced"] > 300, f"{p} spin balls too low"
        assert summary["pace"]["strike_rate"] is not None
        assert summary["spin"]["strike_rate"] is not None
        assert summary["coverage_percentage"] > 50.0
        assert len(trends["seasons"]) >= 5, f"{p} seasons count too low"


def test_career_totals_agree_with_seasonal_aggregates():
    """Verifies that overall career totals agree with the sum of seasonal aggregates."""
    for comp in ("ipl", "t20i"):
        res = client.get(f"/api/player/V%20Kohli/career?competition={comp}")
        assert res.status_code == 200
        trends = res.json()["bowling_type_trends"]
        summary = trends["summary"]
        seasons = trends["seasons"]

        sum_pace_balls = sum(s["pace"]["balls_faced"] for s in seasons)
        sum_pace_runs = sum(s["pace"]["runs"] for s in seasons)
        sum_pace_outs = sum(s["pace_dismissals"] for s in seasons)

        sum_spin_balls = sum(s["spin"]["balls_faced"] for s in seasons)
        sum_spin_runs = sum(s["spin"]["runs"] for s in seasons)
        sum_spin_outs = sum(s["spin_dismissals"] for s in seasons)

        sum_total_balls = sum(s["total_balls_faced"] for s in seasons)
        sum_total_outs = sum(s["bowler_credited_dismissals"] for s in seasons)

        assert summary["pace"]["balls_faced"] == sum_pace_balls
        assert summary["pace"]["runs"] == sum_pace_runs
        assert summary["pace_dismissals"] == sum_pace_outs

        assert summary["spin"]["balls_faced"] == sum_spin_balls
        assert summary["spin"]["runs"] == sum_spin_runs
        assert summary["spin_dismissals"] == sum_spin_outs

        assert summary["total_balls_faced"] == sum_total_balls
        assert summary["bowler_credited_dismissals"] == sum_total_outs


def test_zero_qualifying_observations_show_unavailable_data():
    """Verifies that players with 0 qualifying observations show None, not fabricated zeros."""
    res = client.get("/api/player/J%20Hurley/career?competition=t20i")
    assert res.status_code == 200
    trends = res.json()["bowling_type_trends"]
    summary = trends["summary"]
    cov_info = trends["coverage_info"]

    assert summary["total_balls_faced"] == 0
    assert summary["classified_balls_faced"] == 0
    assert summary["unclassified_balls_faced"] == 0
    assert summary["coverage_percentage"] is None
    assert summary["is_coverage_complete"] is False
    assert summary["dismissals_coverage_percentage"] is None

    assert summary["pace"]["balls_faced"] == 0
    assert summary["pace"]["runs"] == 0
    assert summary["pace"]["strike_rate"] is None
    assert summary["pace"]["average"] is None
    assert summary["spin"]["balls_faced"] == 0
    assert summary["spin"]["runs"] == 0
    assert summary["spin"]["strike_rate"] is None
    assert summary["spin"]["average"] is None

    assert cov_info["coverage_percentage"] is None
    assert cov_info["dismissals_coverage_percentage"] is None


def test_classification_coverage_distinct_from_batting_observation_coverage():
    """Proves that classification coverage does not falsely report 100% on 0 observations."""
    # 1. Zero observation player must NOT be 100% verified
    res_zero = client.get("/api/player/J%20Hurley/career?competition=t20i")
    trends_zero = res_zero.json()["bowling_type_trends"]
    assert trends_zero["summary"]["coverage_percentage"] is None
    assert trends_zero["summary"]["is_coverage_complete"] is False

    # 2. Qualifying player with complete classification (Kohli IPL) is 100% verified
    res_ipl = client.get("/api/player/V%20Kohli/career?competition=ipl")
    trends_ipl = res_ipl.json()["bowling_type_trends"]
    assert trends_ipl["summary"]["coverage_percentage"] == 100.0
    assert trends_ipl["summary"]["is_coverage_complete"] is True
    assert trends_ipl["summary"]["total_balls_faced"] > 5000


def test_production_simulation_no_raw_json_access():
    """
    Simulates Google Cloud Run container environment where data/t20s_json/ and
    data/raw/ are excluded by .dockerignore. Ensures the pipeline works 100%
    from data/processed/t20i/deliveries.csv without calling _get_t20i_match_deliveries.
    """
    with patch.object(
        data_service,
        "_get_t20i_match_deliveries",
        side_effect=RuntimeError("CRITICAL: Raw JSON should not be accessed in production!"),
    ):
        res = client.get("/api/player/Babar%20Azam/career?competition=t20i")
        assert res.status_code == 200
        summary = res.json()["bowling_type_trends"]["summary"]
        assert summary["total_balls_faced"] == 3542
        assert summary["pace"]["balls_faced"] == 1409
        assert summary["spin"]["balls_faced"] == 887
        assert summary["coverage_percentage"] == 64.8
