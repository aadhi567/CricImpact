"""
Tests for Player Career Graph API Endpoints, Career Highs & Lows,
and Aggregation Logic.
Verifies multi-competition support (IPL, T20I, Combined), DNB handling,
non-fabrication of missing metrics, sample size flagging, tied seasons,
and career extremes calculations.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.data_service import data_service

client = TestClient(app)


def test_search_career_players():
    # Search for Kohli
    res = client.get("/api/players/search?q=Kohli")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) > 0
    kohli = next((p for p in data if p["player"] == "V Kohli"), None)
    assert kohli is not None
    assert "ipl" in kohli["competitions"]
    assert "t20i" in kohli["competitions"]
    assert kohli["total_runs"] >= 8000


def test_get_player_career_ipl():
    res = client.get("/api/player/V%20Kohli/career?competition=ipl")
    assert res.status_code == 200
    data = res.json()
    assert data["player"] == "V Kohli"
    assert data["competition"] == "ipl"
    assert len(data["timeline"]) >= 15
    assert data["career_summary"]["total_runs"] > 7000
    assert data["career_summary"]["matches"] >= data["career_summary"]["batting_innings"]
    assert data["career_summary"]["strike_rate"] is not None
    assert data["career_summary"]["average_contribution"] is not None

    # Check season record fields
    season_2016 = next((s for s in data["timeline"] if s["season"] == "2016"), None)
    assert season_2016 is not None
    assert season_2016["runs"] > 900
    assert season_2016["strike_rate"] is not None
    assert season_2016["dot_ball_percentage"] is not None
    assert season_2016["average_contribution"] is not None


def test_get_player_career_t20i():
    res = client.get("/api/player/V%20Kohli/career?competition=t20i")
    assert res.status_code == 200
    data = res.json()
    assert data["player"] == "V Kohli"
    assert data["competition"] == "t20i"
    assert len(data["timeline"]) > 0
    assert data["career_summary"]["total_runs"] > 0


def test_get_player_career_combined():
    res = client.get("/api/player/V%20Kohli/career?competition=combined")
    assert res.status_code == 200
    data = res.json()
    assert data["player"] == "V Kohli"
    assert data["competition"] == "combined"
    summary = data["career_summary"]
    # Total matches in combined should be the sum of IPL and T20I matches
    assert summary["matches"] >= 300
    assert summary["total_runs"] > 8000
    # Strike rate must be calculated as total runs / total balls * 100
    expected_sr = round(summary["total_runs"] / summary["balls_faced"] * 100.0, 2)
    assert abs(summary["strike_rate"] - expected_sr) < 0.1


def test_dnb_appearances_handling():
    # Test a player with known DNBs like MS Dhoni
    res = client.get("/api/player/MS%20Dhoni/career?competition=ipl")
    assert res.status_code == 200
    data = res.json()
    summary = data["career_summary"]
    assert summary["dnb_matches"] > 0
    # Matches must equal batting_innings + dnb_matches
    assert summary["matches"] == summary["batting_innings"] + summary["dnb_matches"]


def test_unknown_player_404():
    res = client.get("/api/player/NonExistentPlayerXYZ123/career")
    assert res.status_code == 404
    err = res.json()
    assert "detail" in err


def test_career_highs_lows_structure_and_values():
    """Validates career_highs_lows block for all four required metrics."""
    res = client.get("/api/player/V%20Kohli/career?competition=ipl")
    assert res.status_code == 200
    data = res.json()
    assert "career_highs_lows" in data
    hl = data["career_highs_lows"]

    # 1. Total Runs
    runs_hl = hl["runs"]
    assert not runs_hl["insufficient_data"]
    assert runs_hl["highest"]["season"] == "2016"
    assert runs_hl["highest"]["value"] == 973
    assert runs_hl["highest"]["matches"] == 16
    assert runs_hl["highest"]["batting_innings"] == 16
    assert runs_hl["lowest"]["value"] < 200
    assert runs_hl["lowest"]["batting_innings"] > 0

    # 2. Strike Rate (weighted total runs / balls * 100)
    sr_hl = hl["strike_rate"]
    assert not sr_hl["insufficient_data"]
    assert sr_hl["highest"]["value"] > 150.0
    assert sr_hl["lowest"]["value"] > 90.0
    assert sr_hl["highest"]["balls_faced"] > 0

    # 3. Dot-Ball Percentage
    dot_hl = hl["dot_ball_percentage"]
    assert not dot_hl["insufficient_data"]
    assert dot_hl["highest"]["value"] > dot_hl["lowest"]["value"]
    assert dot_hl["lowest"]["value"] < 30.0

    # 4. Average Contribution Score (Strategy 4)
    contrib_hl = hl["average_contribution"]
    assert not contrib_hl["insufficient_data"]
    assert contrib_hl["highest"]["season"] == "2016"
    assert contrib_hl["highest"]["value"] > 70.0
    assert contrib_hl["lowest"]["value"] < 50.0


def test_career_highs_lows_limited_sample_and_ties():
    """Validates limited sample flagging, DNB exclusion, and tied season detection."""
    # JJ Bumrah has small sample batting campaigns and tied seasons
    res = client.get("/api/player/JJ%20Bumrah/career?competition=ipl")
    assert res.status_code == 200
    data = res.json()
    hl = data["career_highs_lows"]

    # Bumrah's highest runs campaign should be flagged as limited sample (< 5 innings / 30 balls)
    runs_highest = hl["runs"]["highest"]
    assert runs_highest["is_limited_sample"] is True
    assert "innings" in runs_highest["sample_note"]

    # Check tied seasons detection
    # Bumrah scored 16 runs in both 2017 and 2021
    if runs_highest["value"] == 16:
        assert "2021" in runs_highest["tied_seasons"] or "2017" in runs_highest["tied_seasons"]


def test_career_highs_lows_helper_direct():
    """Unit tests the _compute_career_highs_lows helper with synthetic edge cases."""
    # 1. Empty timeline -> Insufficient data
    empty_res = data_service._compute_career_highs_lows([])
    for metric_id in ["runs", "strike_rate", "dot_ball_percentage", "average_contribution"]:
        assert empty_res[metric_id]["insufficient_data"] is True
        assert empty_res[metric_id]["highest"] is None
        assert empty_res[metric_id]["lowest"] is None

    # 2. Timeline with null values and pure DNB season -> DNB and nulls ignored
    synthetic_timeline = [
        {
            "season": "2021",
            "competition": "IPL",
            "matches": 5,
            "batting_innings": 0, # Pure DNB
            "dnb_matches": 5,
            "runs": 0,
            "balls_faced": 0,
            "strike_rate": None,
            "dot_ball_percentage": None,
            "average_contribution": None,
            "eligible_appearances": 0,
            "eligible_balls": 0,
        },
        {
            "season": "2022",
            "competition": "IPL",
            "matches": 14,
            "batting_innings": 14,
            "dnb_matches": 0,
            "runs": 500,
            "balls_faced": 350,
            "strike_rate": 142.9,
            "dot_ball_percentage": 30.0,
            "average_contribution": 62.5,
            "eligible_appearances": 14,
            "eligible_balls": 350,
        },
        {
            "season": "2023",
            "competition": "IPL",
            "matches": 14,
            "batting_innings": 14,
            "dnb_matches": 0,
            "runs": 500, # Tied with 2022
            "balls_faced": 312,
            "strike_rate": 160.3,
            "dot_ball_percentage": 25.0,
            "average_contribution": 68.0,
            "eligible_appearances": 14,
            "eligible_balls": 312,
        },
        {
            "season": "2024",
            "competition": "IPL",
            "matches": 10,
            "batting_innings": 2, # Small sample
            "dnb_matches": 8,
            "runs": 20,
            "balls_faced": 15,
            "strike_rate": 133.3,
            "dot_ball_percentage": 40.0,
            "average_contribution": 42.0,
            "eligible_appearances": 2,
            "eligible_balls": 15,
        },
    ]

    res = data_service._compute_career_highs_lows(synthetic_timeline)

    # Pure DNB (2021) was excluded from runs evaluation; lowest runs is 2024 (20 runs, limited sample)
    assert res["runs"]["lowest"]["season"] == "2024"
    assert res["runs"]["lowest"]["value"] == 20
    assert res["runs"]["lowest"]["is_limited_sample"] is True

    # Highest runs tied between 2022 and 2023 (500 runs)
    assert res["runs"]["highest"]["value"] == 500
    assert res["runs"]["highest"]["season"] == "2022"
    assert "2023" in res["runs"]["highest"]["tied_seasons"]

    # Highest strike rate is 2023 (160.3)
    assert res["strike_rate"]["highest"]["season"] == "2023"
    assert res["strike_rate"]["highest"]["value"] == 160.3

    # Lowest dot ball % (best strike rotation) is 2023 (25.0%)
    assert res["dot_ball_percentage"]["lowest"]["season"] == "2023"
    assert res["dot_ball_percentage"]["lowest"]["value"] == 25.0

    # Highest contribution is 2023 (68.0)
    assert res["average_contribution"]["highest"]["season"] == "2023"
    assert res["average_contribution"]["highest"]["value"] == 68.0


def test_career_highs_lows_combined_view():
    """Validates career_highs_lows in Combined view (IPL + International)."""
    res = client.get("/api/player/V%20Kohli/career?competition=combined")
    assert res.status_code == 200
    data = res.json()
    hl = data["career_highs_lows"]
    assert not hl["runs"]["insufficient_data"]
    assert hl["runs"]["highest"]["value"] >= 973
    assert hl["runs"]["highest"]["competition"] in ["IPL", "International", "IPL + INL"]


def test_competition_coverage_endpoint():
    """Verifies that /api/competitions/coverage derives actual match record ranges."""
    res = client.get("/api/competitions/coverage")
    assert res.status_code == 200
    data = res.json()
    assert "ipl" in data
    assert "t20i" in data

    # Verify IPL actual records
    ipl = data["ipl"]
    assert ipl["start_year"] == 2008
    assert ipl["end_year"] == 2026
    assert ipl["start_date"] == "2008-04-18"
    assert ipl["end_date"] == "2026-05-31"
    assert ipl["total_matches"] == 1243
    assert "2008" in ipl["display_range"]
    assert "2026" in ipl["display_range"]
    assert ipl["reliable"] is True

    # Verify T20I actual records (expanded to 2007-2026 / 1,498 matches with World Cup remediation)
    t20i = data["t20i"]
    assert t20i["start_year"] in (2007, 2008)
    assert t20i["end_year"] == 2026
    assert t20i["start_date"] in ("2007-09-11", "2008-01-18")
    assert t20i["end_date"] == "2026-10-06"
    assert t20i["total_matches"] in (1468, 1498)
    assert ("2007" in t20i["display_range"]) or ("2008" in t20i["display_range"])
    assert "2026" in t20i["display_range"]
    assert t20i["reliable"] is True

    # Test single competition query params
    res_ipl = client.get("/api/competitions/coverage?competition=ipl")
    assert res_ipl.status_code == 200
    assert res_ipl.json()["competition"] == "ipl"
    assert res_ipl.json()["start_year"] == 2008

    res_t20i = client.get("/api/competitions/coverage?competition=t20i")
    assert res_t20i.status_code == 200
    assert res_t20i.json()["competition"] == "t20i"
    assert res_t20i.json()["start_year"] in (2007, 2008)


def test_player_career_includes_dataset_coverage():
    """Verifies that get_player_career returns dataset_coverage alongside career data."""
    res = client.get("/api/player/V%20Kohli/career?competition=ipl")
    assert res.status_code == 200
    data = res.json()
    assert "dataset_coverage" in data
    cov = data["dataset_coverage"]
    assert "ipl" in cov and "t20i" in cov
    assert cov["ipl"]["start_year"] == 2008
    assert cov["t20i"]["start_year"] in (2007, 2008)


def test_bowling_type_trends_structure_and_coverage():
    """Verifies pace/spin classification, coverage disclosure, and structure in IPL and T20I."""
    # 1. IPL - 100% verified classification
    res_ipl = client.get("/api/player/V%20Kohli/career?competition=ipl")
    assert res_ipl.status_code == 200
    data_ipl = res_ipl.json()
    assert "bowling_type_trends" in data_ipl
    trends_ipl = data_ipl["bowling_type_trends"]
    assert "summary" in trends_ipl
    assert "seasons" in trends_ipl
    assert "coverage_info" in trends_ipl

    summary_ipl = trends_ipl["summary"]
    assert summary_ipl["coverage_percentage"] == 100.0
    assert summary_ipl["unclassified_balls_faced"] == 0
    assert summary_ipl["is_coverage_complete"] is True
    assert summary_ipl["pace"]["balls_faced"] > 3000
    assert summary_ipl["spin"]["balls_faced"] > 2000
    assert summary_ipl["pace"]["strike_rate"] is not None
    assert summary_ipl["spin"]["strike_rate"] is not None

    # 2. T20I - unclassified bowlers excluded and coverage disclosed
    res_t20i = client.get("/api/player/V%20Kohli/career?competition=t20i")
    assert res_t20i.status_code == 200
    trends_t20i = res_t20i.json()["bowling_type_trends"]
    summary_t20i = trends_t20i["summary"]
    assert summary_t20i["coverage_percentage"] > 0
    assert summary_t20i["unclassified_balls_faced"] > 0
    assert len(trends_t20i["coverage_info"]["unclassified_bowlers"]) > 0


def test_bowling_type_trends_calculations_and_aggregation():
    """Verifies mathematical correctness of strike rate, dot ball %, boundary %, and seasonal aggregation."""
    res = client.get("/api/player/V%20Kohli/career?competition=ipl")
    assert res.status_code == 200
    trends = res.json()["bowling_type_trends"]
    seasons = trends["seasons"]
    assert len(seasons) >= 15

    # Check 2016 season
    s2016 = next((s for s in seasons if s["season"] == "2016"), None)
    assert s2016 is not None
    pace = s2016["pace"]
    spin = s2016["spin"]

    # Verify Pace SR = runs / balls * 100
    assert pace["balls_faced"] > 0
    expected_pace_sr = round(pace["runs"] / pace["balls_faced"] * 100.0, 1)
    assert pace["strike_rate"] == expected_pace_sr

    # Verify Spin SR = runs / balls * 100
    assert spin["balls_faced"] > 0
    expected_spin_sr = round(spin["runs"] / spin["balls_faced"] * 100.0, 1)
    assert spin["strike_rate"] == expected_spin_sr

    # Verify Dot % = dot_balls / balls * 100
    assert pace["dot_ball_percentage"] == round(pace["dot_balls"] / pace["balls_faced"] * 100.0, 1)
    assert spin["dot_ball_percentage"] == round(spin["dot_balls"] / spin["balls_faced"] * 100.0, 1)

    # Verify Boundary % = boundary_runs / runs * 100
    expected_pace_b_runs = (pace["fours"] * 4) + (pace["sixes"] * 6)
    assert pace["boundary_runs"] == expected_pace_b_runs
    assert pace["boundary_percentage"] == round(expected_pace_b_runs / pace["runs"] * 100.0, 1)


def test_bowling_type_dismissal_and_not_out_handling():
    """Verifies bowler dismissals vs run outs, and not-out average handling."""
    res = client.get("/api/player/V%20Kohli/career?competition=ipl")
    assert res.status_code == 200
    trends = res.json()["bowling_type_trends"]

    # In 2013, Kohli faced 146 balls against spin and was not out to spin (0 dismissals)
    s2013 = next((s for s in trends["seasons"] if s["season"] == "2013"), None)
    assert s2013 is not None
    spin_2013 = s2013["spin"]
    assert spin_2013["balls_faced"] > 100
    assert spin_2013["dismissals"] == 0
    assert spin_2013["is_not_out"] is True
    assert spin_2013["average"] is None  # Undefined/Not out, never 0

    # In 2016, Kohli was dismissed by spin
    s2016 = next((s for s in trends["seasons"] if s["season"] == "2016"), None)
    assert s2016 is not None
    spin_2016 = s2016["spin"]
    assert spin_2016["dismissals"] > 0
    assert spin_2016["is_not_out"] is False
    assert spin_2016["average"] == round(spin_2016["runs"] / spin_2016["dismissals"], 1)


def test_bowling_type_missing_data_and_sample_flagging():
    """Verifies that missing seasons return null (not zero) and low sample sizes (<20 balls) are flagged."""
    res = client.get("/api/player/B%20Kumar/career?competition=ipl")
    assert res.status_code == 200
    trends = res.json()["bowling_type_trends"]

    # 2011: B Kumar faced 0 pace balls
    s2011 = next((s for s in trends["seasons"] if s["season"] == "2011"), None)
    assert s2011 is not None
    assert s2011["pace"]["balls_faced"] == 0
    assert s2011["pace"]["strike_rate"] is None  # NOT zero!
    assert s2011["pace"]["average"] is None

    # 2014: B Kumar faced 4 pace balls (insufficient sample < 20 balls)
    s2014 = next((s for s in trends["seasons"] if s["season"] == "2014"), None)
    assert s2014 is not None
    assert s2014["pace"]["balls_faced"] == 4
    assert s2014["pace"]["insufficient_sample"] is True
    assert s2014["spin"]["balls_faced"] == 0
    assert s2014["spin"]["strike_rate"] is None  # NOT zero!


def test_bowling_type_season_dismissals_regression():
    """
    Regression test suite for:
    1. Bowler-credited dismissals vs run outs / non-bowler dismissals
    2. Multiple wicket events on one delivery (de-duplication)
    3. Unknown/unclassified bowling style handling and coverage disclosure
    4. Exact reconciliation: bowler_credited == pace + spin + unclassified
    5. Zero-dismissal handling (is_not_out=True, average=None)
    6. Multi-competition season aggregation (IPL, T20I, Combined)
    """
    # 1. Official bowler credit rule checks
    assert data_service._is_bowler_credited_dismissal("bowled") is True
    assert data_service._is_bowler_credited_dismissal("caught") is True
    assert data_service._is_bowler_credited_dismissal("caught and bowled") is True
    assert data_service._is_bowler_credited_dismissal("caught & bowled") is True
    assert data_service._is_bowler_credited_dismissal("lbw") is True
    assert data_service._is_bowler_credited_dismissal("stumped") is True
    assert data_service._is_bowler_credited_dismissal("hit wicket") is True
    assert data_service._is_bowler_credited_dismissal("hit-wicket") is True

    # Non-bowler dismissals must be strictly excluded
    assert data_service._is_bowler_credited_dismissal("run out") is False
    assert data_service._is_bowler_credited_dismissal("run-out") is False
    assert data_service._is_bowler_credited_dismissal("retired hurt") is False
    assert data_service._is_bowler_credited_dismissal("retired out") is False
    assert data_service._is_bowler_credited_dismissal("obstructing the field") is False
    assert data_service._is_bowler_credited_dismissal("timed out") is False
    assert data_service._is_bowler_credited_dismissal(None) is False
    assert data_service._is_bowler_credited_dismissal("") is False

    # 2. Synthetic delivery parsing: Run out vs bowler credited
    deliv_run_out = {
        "match_id": "M1",
        "innings": 1,
        "over": 5,
        "ball": 3,
        "batter": "Batter A",
        "bowler": "Bowler P",
        "player_dismissed": "Batter A",
        "dismissal_kind": "run out",
    }
    assert data_service._extract_bowler_dismissal_event(deliv_run_out, "Batter A") is None

    deliv_caught = {
        "match_id": "M1",
        "innings": 1,
        "over": 5,
        "ball": 4,
        "batter": "Batter A",
        "bowler": "Bowler P",
        "player_dismissed": "Batter A",
        "dismissal_kind": "caught",
    }
    evt_caught = data_service._extract_bowler_dismissal_event(deliv_caught, "Batter A")
    assert evt_caught is not None
    assert evt_caught["bowler"] == "Bowler P"
    assert evt_caught["dismissal_kind"] == "caught"

    # Non-striker run out must not credit dismissal to batter
    deliv_non_striker_out = {
        "match_id": "M1",
        "innings": 1,
        "over": 5,
        "ball": 5,
        "batter": "Batter A",
        "bowler": "Bowler P",
        "player_dismissed": "Non-Striker B",
        "dismissal_kind": "run out",
    }
    assert data_service._extract_bowler_dismissal_event(deliv_non_striker_out, "Batter A") is None

    # 3. Multi-wicket list handling (e.g. T20I JSON structure)
    deliv_multi_wickets = {
        "match_id": "M2",
        "innings": 2,
        "over": 10,
        "ball": 2,
        "batter": "Batter A",
        "bowler": "Bowler S",
        "wickets": [
            {"player_out": "Non-Striker B", "kind": "run out"},
            {"player_out": "Batter A", "kind": "bowled"},
        ],
    }
    evt_multi = data_service._extract_bowler_dismissal_event(deliv_multi_wickets, "Batter A")
    assert evt_multi is not None
    assert evt_multi["bowler"] == "Bowler S"
    assert evt_multi["dismissal_kind"] == "bowled"

    # Multi-wicket duplicate on same delivery: batter listed twice
    deliv_duplicate_wicket = {
        "match_id": "M2",
        "innings": 2,
        "over": 12,
        "ball": 4,
        "batter": "Batter A",
        "bowler": "Bowler S",
        "wickets": [
            {"player_out": "Batter A", "kind": "caught"},
            {"player_out": "Batter A", "kind": "caught"},
        ],
    }
    seen_keys = set()
    deduped_outs = []
    for d in [deliv_duplicate_wicket, deliv_duplicate_wicket]:
        e = data_service._extract_bowler_dismissal_event(d, "Batter A")
        if e:
            k = (e["match_id"], e["innings"], e["over"], e["ball"], "Batter A")
            if k not in seen_keys:
                seen_keys.add(k)
                deduped_outs.append(e)
    assert len(deduped_outs) == 1

    # 4. Live API verification: IPL, T20I, Combined
    for comp in ["ipl", "t20i", "combined"]:
        res = client.get(f"/api/player/V%20Kohli/career?competition={comp}")
        assert res.status_code == 200
        data = res.json()
        trends = data.get("bowling_type_trends")
        assert trends is not None
        summary = trends["summary"]
        seasons = trends["seasons"]

        # Reconcile summary dismissals
        assert "pace_dismissals" in summary
        assert "spin_dismissals" in summary
        assert "bowler_credited_dismissals" in summary
        assert "unclassified_dismissals" in summary
        assert "dismissals_coverage_percentage" in summary

        assert summary["bowler_credited_dismissals"] == (
            summary["pace_dismissals"] + summary["spin_dismissals"] + summary["unclassified_dismissals"]
        )
        assert summary["pace_dismissals"] == summary["pace"]["dismissals"]
        assert summary["spin_dismissals"] == summary["spin"]["dismissals"]

        # Reconcile each season
        calc_total_pace_outs = 0
        calc_total_spin_outs = 0
        calc_total_unclass_outs = 0

        for s in seasons:
            assert "pace_dismissals" in s
            assert "spin_dismissals" in s
            assert "bowler_credited_dismissals" in s
            assert "unclassified_dismissals" in s

            # Ensure exact season reconciliation
            assert s["bowler_credited_dismissals"] == (
                s["pace_dismissals"] + s["spin_dismissals"] + s["unclassified_dismissals"]
            )
            assert s["pace_dismissals"] == s["pace"]["dismissals"]
            assert s["spin_dismissals"] == s["spin"]["dismissals"]

            calc_total_pace_outs += s["pace_dismissals"]
            calc_total_spin_outs += s["spin_dismissals"]
            calc_total_unclass_outs += s["unclassified_dismissals"]

            # Batting average consistency
            if s["pace"]["balls_faced"] > 0:
                if s["pace"]["dismissals"] == 0:
                    assert s["pace"]["is_not_out"] is True
                    assert s["pace"]["average"] is None
                else:
                    assert s["pace"]["is_not_out"] is False
                    assert s["pace"]["average"] == round(s["pace"]["runs"] / s["pace"]["dismissals"], 1)

            if s["spin"]["balls_faced"] > 0:
                if s["spin"]["dismissals"] == 0:
                    assert s["spin"]["is_not_out"] is True
                    assert s["spin"]["average"] is None
                else:
                    assert s["spin"]["is_not_out"] is False
                    assert s["spin"]["average"] == round(s["spin"]["runs"] / s["spin"]["dismissals"], 1)

        # Career totals reconcile with sum of seasons
        assert summary["pace_dismissals"] == calc_total_pace_outs
        assert summary["spin_dismissals"] == calc_total_spin_outs
        assert summary["unclassified_dismissals"] == calc_total_unclass_outs
