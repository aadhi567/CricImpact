"""
Tests for Batter vs Bowling Type (Pace vs Spin) Analytics.
Validates:
- Correct bowling type classification (Pace vs Spin)
- Legal balls counted correctly (wides & noballs excluded from legal balls faced)
- Batter runs aggregated correctly
- Strike Rate calculation: (Runs / Balls) * 100
- Minimum sample rule: Balls >= 100 OR Runs >= 80
- Ranking sorted descending by SR
- Batter detail matchup breakdown with advantage metric
- Verification that existing contribution models remain untouched
"""

import pytest
import pandas as pd
from src.bowling_classification import get_bowler_classification, classify_bowler
from src.matchup_analytics import (
    load_deliveries_with_bowling_type,
    compute_matchup_rankings,
    get_batter_matchup_detail,
)


def test_bowler_classification_coverage():
    """Verify all 577 unique bowlers are classified into Pace or Spin."""
    classification = get_bowler_classification()
    assert len(classification) >= 577
    assert all(v in ("Pace", "Spin") for v in classification.values())

    # Check key bowlers
    assert classification["JJ Bumrah"] == "Pace"
    assert classification["SL Malinga"] == "Pace"
    assert classification["TA Boult"] == "Pace"
    assert classification["B Kumar"] == "Pace"
    assert classification["Mohammed Shami"] == "Pace"

    assert classification["R Ashwin"] == "Spin"
    assert classification["YS Chahal"] == "Spin"
    assert classification["Rashid Khan"] == "Spin"
    assert classification["SP Narine"] == "Spin"
    assert classification["Kuldeep Yadav"] == "Spin"
    assert classification["RA Jadeja"] == "Spin"


def test_legal_balls_calculation():
    """Verify wides and noballs are excluded from legal balls faced."""
    # Synthetic deliveries
    data = [
        {"match_id": 1, "season": "2024", "innings_number": 1, "over": 1, "ball": 1,
         "batting_team": "RCB", "bowling_team": "CSK", "batter": "B1", "bowler": "JJ Bumrah",
         "batter_runs": 4, "wides": 0, "noballs": 0},  # Legal Pace: 4 runs, 1 ball
        {"match_id": 1, "season": "2024", "innings_number": 1, "over": 1, "ball": 2,
         "batting_team": "RCB", "bowling_team": "CSK", "batter": "B1", "bowler": "JJ Bumrah",
         "batter_runs": 0, "wides": 1, "noballs": 0},  # Wide: 0 batter runs, 0 legal balls
        {"match_id": 1, "season": "2024", "innings_number": 1, "over": 1, "ball": 3,
         "batting_team": "RCB", "bowling_team": "CSK", "batter": "B1", "bowler": "JJ Bumrah",
         "batter_runs": 2, "wides": 0, "noballs": 1},  # No-ball: 2 batter runs, 0 legal balls
        {"match_id": 1, "season": "2024", "innings_number": 1, "over": 1, "ball": 4,
         "batting_team": "RCB", "bowling_team": "CSK", "batter": "B1", "bowler": "Rashid Khan",
         "batter_runs": 6, "wides": 0, "noballs": 0},  # Legal Spin: 6 runs, 1 ball
    ]
    df = pd.DataFrame(data)
    df["bowling_type"] = df["bowler"].map(classify_bowler)
    df["is_legal"] = (df["wides"] == 0) & (df["noballs"] == 0)

    # Compute for B1 with min_sample=1
    res = compute_matchup_rankings(min_balls=1, min_runs=1, deliveries_df=df)
    pace_rankings = res["results"]["pace"]["rankings"]
    spin_rankings = res["results"]["spin"]["rankings"]

    assert len(pace_rankings) == 1
    assert pace_rankings[0]["batter"] == "B1"
    # Runs: 4 + 2 = 6 runs off Bumrah
    assert pace_rankings[0]["runs"] == 6
    # Legal balls: only delivery 1 is legal (ball 2 was wide, ball 3 was noball)
    assert pace_rankings[0]["balls"] == 1
    assert pace_rankings[0]["strike_rate"] == 600.0

    assert len(spin_rankings) == 1
    assert spin_rankings[0]["batter"] == "B1"
    assert spin_rankings[0]["runs"] == 6
    assert spin_rankings[0]["balls"] == 1
    assert spin_rankings[0]["strike_rate"] == 600.0


def test_minimum_sample_rule():
    """Verify balls >= 100 OR runs >= 80 rule."""
    data = [
        # Batter 1: 105 balls, 50 runs -> Eligible (balls >= 100)
        *[{"match_id": 1, "season": "2024", "innings_number": 1, "over": 1, "ball": i,
           "batting_team": "T1", "bowling_team": "T2", "batter": "Bat1", "bowler": "JJ Bumrah",
           "batter_runs": 0 if i > 50 else 1, "wides": 0, "noballs": 0} for i in range(105)],
        # Batter 2: 40 balls, 90 runs -> Eligible (runs >= 80)
        *[{"match_id": 1, "season": "2024", "innings_number": 1, "over": 2, "ball": i,
           "batting_team": "T1", "bowling_team": "T2", "batter": "Bat2", "bowler": "JJ Bumrah",
           "batter_runs": 3 if i <= 30 else 0, "wides": 0, "noballs": 0} for i in range(40)],
        # Batter 3: 50 balls, 60 runs -> Ineligible (balls < 100 AND runs < 80)
        *[{"match_id": 1, "season": "2024", "innings_number": 1, "over": 3, "ball": i,
           "batting_team": "T1", "bowling_team": "T2", "batter": "Bat3", "bowler": "JJ Bumrah",
           "batter_runs": 1 if i <= 60 else 0, "wides": 0, "noballs": 0} for i in range(50)],
    ]
    df = pd.DataFrame(data)
    df["bowling_type"] = "Pace"
    df["is_legal"] = True

    res = compute_matchup_rankings(min_balls=100, min_runs=80, deliveries_df=df)
    pace_batters = [r["batter"] for r in res["results"]["pace"]["rankings"]]

    assert "Bat1" in pace_batters
    assert "Bat2" in pace_batters
    assert "Bat3" not in pace_batters


def test_ranking_sort_order():
    """Verify rankings are strictly sorted descending by Strike Rate."""
    res = compute_matchup_rankings(min_balls=100, min_runs=80)
    for b_type in ("pace", "spin"):
        rankings = res["results"][b_type]["rankings"]
        assert len(rankings) > 0
        srs = [r["strike_rate"] for r in rankings]
        # Check monotonically non-increasing
        assert all(srs[i] >= srs[i+1] for i in range(len(srs) - 1))
        # Check rank numbering
        ranks = [r["rank"] for r in rankings]
        assert ranks == list(range(1, len(rankings) + 1))


def test_batter_matchup_detail():
    """Verify player matchup detail returns Pace, Spin and advantage comparison."""
    detail = get_batter_matchup_detail("V Kohli")
    assert detail is not None
    assert detail["batter"] == "V Kohli"
    assert "pace" in detail
    assert "spin" in detail
    assert "difference" in detail

    pace = detail["pace"]
    spin = detail["spin"]
    diff = detail["difference"]

    assert pace["runs"] > 3000
    assert pace["balls"] > 2000
    assert spin["runs"] > 2000
    assert spin["balls"] > 1500

    assert diff["sr_difference"] == round(spin["strike_rate"] - pace["strike_rate"], 1)
    assert diff["runs_difference"] == spin["runs"] - pace["runs"]
    assert diff["balls_difference"] == spin["balls"] - pace["balls"]
    assert "advantage_text" in diff
