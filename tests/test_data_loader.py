"""
Pytest unit tests for the IPL data loading and processing pipeline.
Uses a mock sample match and small real sample match to test:
- JSON loading and error handling
- Innings extraction and metadata
- Delivery extraction, legal vs illegal balls, extras
- Batter statistics (runs, balls faced, boundaries, dots, dismissals, position)
- Totals consistency (deliveries sum vs innings total vs batter total)
"""

import os
import json
import pytest
import pandas as pd
from pathlib import Path
from src.data_loader import parse_single_match, load_and_process_matches
from src.validate_data import validate_datasets


@pytest.fixture
def sample_match_data():
    """Returns a synthetic Cricsheet-style match dictionary."""
    return {
        "meta": {"data_version": "1.1.0", "created": "2024-01-01"},
        "info": {
            "season": "2024",
            "dates": ["2024-03-22"],
            "venue": "M Chinnaswamy Stadium, Bengaluru",
            "city": "Bengaluru",
            "teams": ["Royal Challengers Bengaluru", "Chennai Super Kings"],
            "toss": {
                "winner": "Royal Challengers Bengaluru",
                "decision": "bat"
            },
            "outcome": {
                "winner": "Chennai Super Kings",
                "by": {"wickets": 6}
            },
            "player_of_match": ["Mustafizur Rahman"],
        },
        "innings": [
            {
                "team": "Royal Challengers Bengaluru",
                "overs": [
                    {
                        "over": 0,
                        "deliveries": [
                            # Ball 1: dot
                            {
                                "batter": "V Kohli",
                                "non_striker": "F du Plessis",
                                "bowler": "DL Chahar",
                                "runs": {"batter": 0, "extras": 0, "total": 0}
                            },
                            # Ball 2: wide (extra 1)
                            {
                                "batter": "V Kohli",
                                "non_striker": "F du Plessis",
                                "bowler": "DL Chahar",
                                "runs": {"batter": 0, "extras": 1, "total": 1},
                                "extras": {"wides": 1}
                            },
                            # Ball 3: four
                            {
                                "batter": "V Kohli",
                                "non_striker": "F du Plessis",
                                "bowler": "DL Chahar",
                                "runs": {"batter": 4, "extras": 0, "total": 4}
                            },
                            # Ball 4: single
                            {
                                "batter": "V Kohli",
                                "non_striker": "F du Plessis",
                                "bowler": "DL Chahar",
                                "runs": {"batter": 1, "extras": 0, "total": 1}
                            },
                            # Ball 5: six
                            {
                                "batter": "F du Plessis",
                                "non_striker": "V Kohli",
                                "bowler": "DL Chahar",
                                "runs": {"batter": 6, "extras": 0, "total": 6}
                            },
                            # Ball 6: no-ball with 1 run off bat + 1 extra
                            {
                                "batter": "F du Plessis",
                                "non_striker": "V Kohli",
                                "bowler": "DL Chahar",
                                "runs": {"batter": 1, "extras": 1, "total": 2},
                                "extras": {"noballs": 1}
                            },
                            # Ball 7 (free hit): wicket
                            {
                                "batter": "F du Plessis",
                                "non_striker": "V Kohli",
                                "bowler": "DL Chahar",
                                "runs": {"batter": 0, "extras": 0, "total": 0},
                                "wickets": [
                                    {
                                        "kind": "caught",
                                        "player_out": "F du Plessis",
                                        "fielders": [{"name": "RD Gaikwad"}]
                                    }
                                ]
                            }
                        ]
                    }
                ]
            },
            {
                "team": "Chennai Super Kings",
                "target": {"runs": 15, "overs": 20},
                "overs": [
                    {
                        "over": 0,
                        "deliveries": [
                            {
                                "batter": "RD Gaikwad",
                                "non_striker": "R Ravindra",
                                "bowler": "Mohammed Siraj",
                                "runs": {"batter": 6, "extras": 0, "total": 6}
                            },
                            {
                                "batter": "RD Gaikwad",
                                "non_striker": "R Ravindra",
                                "bowler": "Mohammed Siraj",
                                "runs": {"batter": 6, "extras": 0, "total": 6}
                            },
                            {
                                "batter": "RD Gaikwad",
                                "non_striker": "R Ravindra",
                                "bowler": "Mohammed Siraj",
                                "runs": {"batter": 4, "extras": 0, "total": 4}
                            }
                        ]
                    }
                ]
            }
        ]
    }


def test_json_loading(tmp_path, sample_match_data):
    """Test loading and parsing a JSON match file."""
    test_file = tmp_path / "test_match_999999.json"
    with open(test_file, "w", encoding="utf-8") as f:
        json.dump(sample_match_data, f)

    m_row, inn_rows, deliv_rows, bat_rows = parse_single_match(test_file)

    assert m_row["match_id"] == "test_match_999999"
    assert m_row["season"] == "2024"
    assert m_row["venue"] == "M Chinnaswamy Stadium, Bengaluru"
    assert m_row["city"] == "Bengaluru"
    assert m_row["team1"] == "Royal Challengers Bengaluru"
    assert m_row["team2"] == "Chennai Super Kings"
    assert m_row["winner"] == "Chennai Super Kings"
    assert m_row["win_by_wickets"] == 6
    assert m_row["player_of_match"] == "Mustafizur Rahman"
    assert m_row["innings_count"] == 2


def test_missing_optional_fields(tmp_path):
    """Ensure missing optional JSON fields (city, winner, by, POM) do not raise errors."""
    minimal_match = {
        "info": {
            "season": 2008,
            "dates": ["2008-04-18"],
            "teams": ["Kolkata Knight Riders", "Royal Challengers Bangalore"],
            "toss": {"winner": "Royal Challengers Bangalore", "decision": "field"},
            "outcome": {"result": "no result"}
        },
        "innings": []
    }
    test_file = tmp_path / "minimal_match.json"
    with open(test_file, "w", encoding="utf-8") as f:
        json.dump(minimal_match, f)

    m_row, inn_rows, deliv_rows, bat_rows = parse_single_match(test_file)
    assert m_row["city"] is None
    assert m_row["winner"] is None
    assert m_row["win_by_runs"] is None
    assert m_row["win_by_wickets"] is None
    assert m_row["player_of_match"] is None
    assert m_row["innings_count"] == 0
    assert len(inn_rows) == 0


def test_innings_extraction(tmp_path, sample_match_data):
    """Test extraction of innings metadata, targets, and chase status."""
    test_file = tmp_path / "sample.json"
    with open(test_file, "w", encoding="utf-8") as f:
        json.dump(sample_match_data, f)

    _, inn_rows, _, _ = parse_single_match(test_file)

    assert len(inn_rows) == 2

    # Innings 1 (batting first)
    inn1 = inn_rows[0]
    assert inn1["innings_number"] == 1
    assert inn1["batting_team"] == "Royal Challengers Bengaluru"
    assert inn1["bowling_team"] == "Chennai Super Kings"
    assert inn1["total_runs"] == 14  # 0 + 1 (wide) + 4 + 1 + 6 + 2 (nb) + 0 = 14
    assert inn1["total_wickets"] == 1
    assert inn1["target"] is None
    assert inn1["is_chase"] is False
    # 7 deliveries: 1 wide, 1 no-ball, 5 legal deliveries -> 0.5 overs
    assert inn1["overs_completed"] == 0.5

    # Innings 2 (chasing)
    inn2 = inn_rows[1]
    assert inn2["innings_number"] == 2
    assert inn2["batting_team"] == "Chennai Super Kings"
    assert inn2["bowling_team"] == "Royal Challengers Bengaluru"
    assert inn2["total_runs"] == 16  # 6 + 6 + 4
    assert inn2["target"] == 15
    assert inn2["is_chase"] is True


def test_delivery_extraction(tmp_path, sample_match_data):
    """Test delivery attributes, extras handling, and dismissal info."""
    test_file = tmp_path / "sample.json"
    with open(test_file, "w", encoding="utf-8") as f:
        json.dump(sample_match_data, f)

    _, _, deliv_rows, _ = parse_single_match(test_file)

    # Total 7 deliveries in innings 1 + 3 in innings 2 = 10
    assert len(deliv_rows) == 10

    # Test wide delivery (innings 1, delivery 2)
    wide_deliv = deliv_rows[1]
    assert wide_deliv["ball"] == 2
    assert wide_deliv["batter"] == "V Kohli"
    assert wide_deliv["extras_runs"] == 1
    assert wide_deliv["wides"] == 1
    assert wide_deliv["extra_type"] == "wides"
    assert wide_deliv["total_runs"] == 1

    # Test wicket delivery (innings 1, delivery 7)
    wkt_deliv = deliv_rows[6]
    assert wkt_deliv["player_dismissed"] == "F du Plessis"
    assert wkt_deliv["dismissal_kind"] == "caught"
    assert wkt_deliv["is_wicket"] is True


def test_batter_statistics(tmp_path, sample_match_data):
    """Test batter statistics calculation: runs, balls faced, boundaries, dots, dismissals, position."""
    test_file = tmp_path / "sample.json"
    with open(test_file, "w", encoding="utf-8") as f:
        json.dump(sample_match_data, f)

    _, _, _, bat_rows = parse_single_match(test_file)

    # In Innings 1: V Kohli (pos 1), F du Plessis (pos 2)
    rcb_batters = {b["batter"]: b for b in bat_rows if b["innings_number"] == 1}

    kohli = rcb_batters["V Kohli"]
    assert kohli["batting_position"] == 1
    assert kohli["runs"] == 5  # 0 + 4 + 1
    # Kohli faced: ball 1 (dot), ball 2 (wide - not faced), ball 3 (4), ball 4 (1) -> 3 balls faced
    assert kohli["balls_faced"] == 3
    assert kohli["fours"] == 1
    assert kohli["sixes"] == 0
    assert kohli["dot_balls"] == 1
    assert kohli["dismissal_status"] == "not out"
    assert kohli["dismissal_kind"] is None

    faf = rcb_batters["F du Plessis"]
    assert faf["batting_position"] == 2
    assert faf["runs"] == 7  # 6 + 1 (nb) + 0
    # Faf faced: ball 5 (6), ball 6 (nb - counts as faced), ball 7 (wkt - 0) -> 3 balls faced
    assert faf["balls_faced"] == 3
    assert faf["fours"] == 0
    assert faf["sixes"] == 1
    assert faf["dot_balls"] == 1  # ball 7 is dot (total_runs=0)
    assert faf["dismissal_status"] == "out"
    assert faf["dismissal_kind"] == "caught"


def test_totals_consistency(tmp_path, sample_match_data):
    """Test cross-dataset consistency on the sample match."""
    test_file = tmp_path / "sample.json"
    with open(test_file, "w", encoding="utf-8") as f:
        json.dump(sample_match_data, f)

    out_dir = tmp_path / "processed"
    matches_df, innings_df, deliveries_df, batter_innings_df, failed = load_and_process_matches(
        raw_dir=tmp_path,
        processed_dir=out_dir,
        save=True
    )

    assert len(failed) == 0

    all_passed, results = validate_datasets(
        matches_df=matches_df,
        innings_df=innings_df,
        deliveries_df=deliveries_df,
        batter_innings_df=batter_innings_df
    )

    for check_name, data in results.items():
        assert data["passed"], f"Validation check failed: {check_name} -> {data['details']}"
    assert all_passed


def test_real_match_sample():
    """Test loading and validating one actual Cricsheet match file from data/raw/."""
    raw_dir = Path("data/raw")
    if not raw_dir.exists():
        pytest.skip("data/raw not present in current directory")

    files = list(raw_dir.glob("*.json"))
    if not files:
        pytest.skip("No JSON files in data/raw")

    sample_file = files[0]
    m_row, inn_rows, deliv_rows, bat_rows = parse_single_match(sample_file)

    assert m_row["match_id"] == sample_file.stem
    assert len(inn_rows) >= 1
    assert len(deliv_rows) >= 1
    assert len(bat_rows) >= 1

    # Check run math on real match
    deliv_df = pd.DataFrame(deliv_rows)
    assert (deliv_df["batter_runs"] + deliv_df["extras_runs"] == deliv_df["total_runs"]).all()
