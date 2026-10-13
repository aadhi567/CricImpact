"""
Tests for dynamic default-season resolution and format integrity across competitions.
Ensures no hardcoded years are used, current year is dynamically matched when available,
and latest available season is selected when current year is absent.
"""

import datetime
from fastapi.testclient import TestClient
from app.main import app
from app.services.data_service import data_service

client = TestClient(app)


def test_dynamic_season_resolution_logic():
    """Verify data_service._resolve_dynamic_default_season logic."""
    current_year = str(datetime.date.today().year)
    prev_year = str(datetime.date.today().year - 1)
    short_current = current_year[2:]

    # 1. Exact match
    seasons_exact = [current_year, prev_year, "2020"]
    assert data_service._resolve_dynamic_default_season(seasons_exact) == current_year

    # 2. Overlapping split year match (e.g. 2025/26 for 2026)
    split_season = f"{prev_year}/{short_current}"
    seasons_split = [split_season, "2023/24", "2022/23"]
    assert data_service._resolve_dynamic_default_season(seasons_split) == split_season

    # 3. Missing current year -> falls back to latest available season
    historical = ["2023", "2022", "2021"]
    assert data_service._resolve_dynamic_default_season(historical) == "2023"

    # 4. Empty list -> None
    assert data_service._resolve_dynamic_default_season([]) is None


def test_api_seasons_dynamic_default_ipl():
    """Verify /api/seasons?competition=ipl dynamically resolves current year if present."""
    current_year = str(datetime.date.today().year)
    res = client.get("/api/seasons?competition=ipl")
    assert res.status_code == 200
    data = res.json()
    assert "seasons" in data
    assert "default_season" in data
    if current_year in data["seasons"]:
        assert data["default_season"] == current_year
    else:
        assert data["default_season"] == data["seasons"][0]


def test_api_seasons_dynamic_default_t20i():
    """Verify /api/seasons?competition=t20i dynamically resolves current year."""
    current_year = str(datetime.date.today().year)
    res = client.get("/api/seasons?competition=t20i")
    assert res.status_code == 200
    data = res.json()
    if current_year in data["seasons"]:
        assert data["default_season"] == current_year
    else:
        assert data["default_season"] == data["seasons"][0]


def test_api_seasons_dynamic_default_smat():
    """Verify /api/seasons?competition=smat returns 400 due to temporary deactivation."""
    res = client.get("/api/seasons?competition=smat")
    assert res.status_code == 400
    assert "temporarily deactivated" in res.json()["detail"]


def test_api_seasons_tournament_types_dynamic():
    """Verify World Cup, Asia Cup, and Bilateral dynamic defaulting."""
    current_year = str(datetime.date.today().year)

    # World Cup
    res_wc = client.get("/api/seasons?competition=t20i&tournament_type=world_cup")
    assert res_wc.status_code == 200
    data_wc = res_wc.json()
    if current_year in data_wc["seasons"]:
        assert data_wc["default_season"] == current_year
    else:
        assert data_wc["default_season"] == data_wc["seasons"][0]

    # Asia Cup (options: 2025, 2022) -> latest available 2025
    res_ac = client.get("/api/seasons?competition=t20i&tournament_type=asia_cup")
    assert res_ac.status_code == 200
    data_ac = res_ac.json()
    assert data_ac["default_season"] == "2025"
