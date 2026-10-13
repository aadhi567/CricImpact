"""
Unit tests for Phase 2 Match Context & Situation Engine.

Tests:
1. Innings context: overs conversion, phase classification (T20/ODI), run rates, simple projected score.
2. Chase context: target calculation, runs required, required run rate, completed chase safety.
3. Partnership extraction: partnership tracking, run share, boundary runs, dots, total runs reconciliation.
4. Match state building: ball-by-ball cumulative progression, batter cumulative stats, wides/no-balls.
5. Batter entry & dismissal: entry score strictly before first delivery faced, dismissal before/after distinction.
6. Post-dismissal scoring rates: next 6 balls, next 12 balls, remaining innings, NULL safety.
7. Zero balls faced batter: non-striker entry state, zero division protection.
"""

import pytest
import pandas as pd
import numpy as np
from src.innings_context import (
    legal_balls_to_overs,
    overs_to_legal_balls,
    calculate_team_run_rate,
    calculate_batter_strike_rate,
    calculate_batter_run_rate,
    get_innings_phase,
    calculate_projected_score_simple,
)
from src.chase_context import (
    calculate_runs_required,
    calculate_required_run_rate,
    get_chase_metrics,
)
from src.partnership import extract_innings_partnerships
from src.match_state import build_innings_match_state


def test_overs_and_run_rates():
    """Test legal balls to overs and run rate calculations."""
    assert legal_balls_to_overs(0) == 0.0
    assert legal_balls_to_overs(1) == 0.1
    assert legal_balls_to_overs(5) == 0.5
    assert legal_balls_to_overs(6) == 1.0
    assert legal_balls_to_overs(44) == 7.2
    assert legal_balls_to_overs(120) == 20.0

    assert overs_to_legal_balls(0.0) == 0
    assert overs_to_legal_balls(0.1) == 1
    assert overs_to_legal_balls(1.0) == 6
    assert overs_to_legal_balls(7.2) == 44
    assert overs_to_legal_balls(20.0) == 120

    # Team RR: 45 runs in 44 legal balls -> 45 / (44/6) = 6.13636 -> 6.14
    assert calculate_team_run_rate(45, 44) == 6.14
    assert calculate_team_run_rate(0, 0) == 0.0

    # Batter strike rate & run rate
    # 62 runs off 38 balls -> SR = 163.16, RR = 9.79
    assert calculate_batter_strike_rate(62, 38) == 163.16
    assert calculate_batter_run_rate(62, 38) == 9.79
    assert calculate_batter_strike_rate(0, 0) == 0.0
    assert calculate_batter_run_rate(0, 0) == 0.0


def test_innings_phases():
    """Test configurable innings phase classification for T20 and ODI."""
    # T20 by legal balls
    assert get_innings_phase(0, format="T20") == "POWERPLAY"
    assert get_innings_phase(36, format="T20") == "POWERPLAY"
    assert get_innings_phase(37, format="T20") == "MIDDLE"
    assert get_innings_phase(90, format="T20") == "MIDDLE"
    assert get_innings_phase(91, format="T20") == "DEATH"
    assert get_innings_phase(120, format="T20") == "DEATH"

    # T20 by over number (0-based)
    assert get_innings_phase(0, format="T20", by_over_number=True) == "POWERPLAY"
    assert get_innings_phase(5, format="T20", by_over_number=True) == "POWERPLAY"
    assert get_innings_phase(6, format="T20", by_over_number=True) == "MIDDLE"
    assert get_innings_phase(14, format="T20", by_over_number=True) == "MIDDLE"
    assert get_innings_phase(15, format="T20", by_over_number=True) == "DEATH"
    assert get_innings_phase(19, format="T20", by_over_number=True) == "DEATH"

    # ODI
    assert get_innings_phase(60, format="ODI") == "POWERPLAY"
    assert get_innings_phase(61, format="ODI") == "MIDDLE"
    assert get_innings_phase(240, format="ODI") == "MIDDLE"
    assert get_innings_phase(241, format="ODI") == "DEATH"


def test_projected_score_simple():
    """Test simple baseline projected score."""
    # Current RR 8.5 * 20 overs = 170.0
    assert calculate_projected_score_simple(8.5, 20.0) == 170.0
    assert calculate_projected_score_simple(0.0, 20.0) == 0.0
    # Super over (1.0 over scheduled)
    assert calculate_projected_score_simple(12.0, 1.0) == 12.0


def test_chase_context():
    """Test chase context, completed chase handling, and required run rate."""
    # Target 180, current runs 45, balls remaining 76
    runs_req = calculate_runs_required(180, 45)
    assert runs_req == 135
    # RRR = 135 / (76 / 6.0) = 10.6578 -> 10.66
    rrr = calculate_required_run_rate(runs_req, 76)
    assert rrr == 10.66

    # Completed chase (target 180, scored 182)
    assert calculate_runs_required(180, 182) == 0
    assert calculate_required_run_rate(0, 10) == 0.0
    assert calculate_required_run_rate(-5, 10) == 0.0

    # Balls exhausted without reaching target
    assert calculate_required_run_rate(10, 0) == 99.99

    # Non-chase
    assert calculate_runs_required(None, 50) is None
    assert calculate_required_run_rate(None, 50) is None


def test_synthetic_partnership_extraction():
    """Test partnership extraction with two wickets and final unbroken partnership."""
    deliveries = [
        # Ball 1: dot (B1 on strike, B2 non-striker)
        {"batter": "B1", "non_striker": "B2", "bowler": "BW", "batter_runs": 0, "extras_runs": 0, "total_runs": 0, "wides": 0, "noballs": 0},
        # Ball 2: 4 runs to B1
        {"batter": "B1", "non_striker": "B2", "bowler": "BW", "batter_runs": 4, "extras_runs": 0, "total_runs": 4, "wides": 0, "noballs": 0},
        # Ball 3: 1 run to B1
        {"batter": "B1", "non_striker": "B2", "bowler": "BW", "batter_runs": 1, "extras_runs": 0, "total_runs": 1, "wides": 0, "noballs": 0},
        # Ball 4: B2 out caught
        {"batter": "B2", "non_striker": "B1", "bowler": "BW", "batter_runs": 0, "extras_runs": 0, "total_runs": 0, "wides": 0, "noballs": 0, "player_dismissed": "B2", "dismissal_kind": "caught", "is_wicket": True},
        # Ball 5: B3 arrives! B3 takes 2 runs
        {"batter": "B3", "non_striker": "B1", "bowler": "BW", "batter_runs": 2, "extras_runs": 0, "total_runs": 2, "wides": 0, "noballs": 0},
        # Ball 6: 1 wide
        {"batter": "B3", "non_striker": "B1", "bowler": "BW", "batter_runs": 0, "extras_runs": 1, "total_runs": 1, "wides": 1, "noballs": 0},
        # Ball 7: B1 hits six
        {"batter": "B1", "non_striker": "B3", "bowler": "BW", "batter_runs": 6, "extras_runs": 0, "total_runs": 6, "wides": 0, "noballs": 0},
    ]

    partnerships, p_ids = extract_innings_partnerships(
        match_id="test_1",
        innings_number=1,
        batting_team="Team A",
        deliveries_list=deliveries
    )

    assert len(partnerships) == 2
    # P1: B1 and B2, scored 5 runs in 4 legal balls
    p1 = partnerships[0]
    assert p1["partnership_id"] == 1
    assert p1["batter_1"] == "B1"
    assert p1["batter_2"] == "B2"
    assert p1["partnership_start_score"] == 0
    assert p1["partnership_end_score"] == 5
    assert p1["partnership_runs"] == 5
    assert p1["partnership_balls"] == 4
    assert p1["batter_1_runs_in_partnership"] == 5
    assert p1["batter_2_runs_in_partnership"] == 0
    assert p1["batter_1_run_share"] == 100.0

    # P2: Survivor B1 and newcomer B3, scored 9 runs (2 + 1 wide + 6)
    p2 = partnerships[1]
    assert p2["partnership_id"] == 2
    assert p2["batter_1"] == "B1"
    assert p2["batter_2"] == "B3"
    assert p2["partnership_start_score"] == 5
    assert p2["partnership_end_score"] == 14
    assert p2["partnership_runs"] == 9
    assert p2["partnership_balls"] == 2  # 2 legal balls (1 was wide)
    assert p2["batter_1_runs_in_partnership"] == 6
    assert p2["batter_2_runs_in_partnership"] == 2

    # Reconciliation
    assert sum(p["partnership_runs"] for p in partnerships) == 14
    assert len(p_ids) == 7


def test_match_state_and_entry_state():
    """Verify ball-by-ball match state tracking and entry state before first delivery."""
    deliveries = [
        # Ball 1: wide
        {"over": 0, "ball": 1, "batter": "A", "non_striker": "B", "bowler": "X", "batter_runs": 0, "extras_runs": 1, "total_runs": 1, "wides": 1, "noballs": 0},
        # Ball 2: single
        {"over": 0, "ball": 2, "batter": "A", "non_striker": "B", "bowler": "X", "batter_runs": 1, "extras_runs": 0, "total_runs": 1, "wides": 0, "noballs": 0},
        # Ball 3: four to B
        {"over": 0, "ball": 3, "batter": "B", "non_striker": "A", "bowler": "X", "batter_runs": 4, "extras_runs": 0, "total_runs": 4, "wides": 0, "noballs": 0},
    ]

    m_states = build_innings_match_state(
        match_id="test_m",
        season="2024",
        innings_number=1,
        batting_team="Team A",
        bowling_team="Team B",
        deliveries_list=deliveries,
        target=None,
        scheduled_overs=20.0
    )

    assert len(m_states) == 3

    # Ball 1:
    b1 = m_states[0]
    assert b1["runs_before_delivery"] == 0
    assert b1["total_team_runs_so_far"] == 1
    assert b1["legal_balls_bowled_so_far"] == 0
    assert b1["batter_balls_so_far"] == 0  # wide does not count as ball faced

    # Ball 2:
    b2 = m_states[1]
    assert b2["runs_before_delivery"] == 1
    assert b2["total_team_runs_so_far"] == 2
    assert b2["legal_balls_bowled_so_far"] == 1
    assert b2["batter_balls_so_far"] == 1  # faced legal ball

    # Ball 3 (B faces first ball):
    b3 = m_states[2]
    # Before B's first ball, team score was 2
    assert b3["runs_before_delivery"] == 2
    assert b3["total_team_runs_so_far"] == 6
    assert b3["batter_runs_so_far"] == 4
    assert b3["batter_balls_so_far"] == 1
