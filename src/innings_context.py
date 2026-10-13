"""
Innings Context & Phase Classification Module.

Provides utilities for:
1. Cricket overs conversion (balls <-> over notation).
2. Run rate and strike rate calculations.
3. Configurable innings phase classification (T20, ODI).
4. Simple baseline projected score calculation.
"""

from typing import Union


def legal_balls_to_overs(legal_balls: int) -> float:
    """
    Convert a count of legal balls to cricket over notation (e.g. 44 balls -> 7.2 overs).

    Args:
        legal_balls: Non-negative integer count of legal balls.

    Returns:
        float: Cricket overs notation (e.g., 0.0, 1.5, 7.2, 20.0).
    """
    if legal_balls <= 0:
        return 0.0
    completed_overs = legal_balls // 6
    remaining_balls = legal_balls % 6
    return round(completed_overs + remaining_balls / 10.0, 1)


def overs_to_legal_balls(overs: float) -> int:
    """
    Convert cricket over notation to total legal balls (e.g. 7.2 overs -> 44 balls).

    Args:
        overs: Cricket over notation (e.g. 7.2).

    Returns:
        int: Total legal balls.
    """
    if overs <= 0.0:
        return 0
    full_overs = int(overs)
    rem_balls = int(round((overs - full_overs) * 10))
    return full_overs * 6 + rem_balls


def calculate_team_run_rate(runs: int, legal_balls: int) -> float:
    """
    Calculate the current team run rate from total runs and legal balls.

    Formula: runs / (legal_balls / 6.0)

    Args:
        runs: Total runs scored.
        legal_balls: Total legal balls bowled.

    Returns:
        float: Run rate rounded to 2 decimal places, or 0.0 if legal_balls == 0.
    """
    if legal_balls <= 0:
        return 0.0
    return round(runs / (legal_balls / 6.0), 2)


def calculate_batter_strike_rate(runs: int, balls_faced: int) -> float:
    """
    Calculate batter strike rate.

    Formula: (runs / balls_faced) * 100

    Args:
        runs: Runs scored off the bat.
        balls_faced: Legal deliveries plus no-balls faced (wides excluded).

    Returns:
        float: Strike rate rounded to 2 decimal places, or 0.0 if balls_faced == 0.
    """
    if balls_faced <= 0:
        return 0.0
    return round((runs / balls_faced) * 100.0, 2)


def calculate_batter_run_rate(runs: int, balls_faced: int) -> float:
    """
    Calculate batter individual run rate.

    Formula: (runs / balls_faced) * 6

    Args:
        runs: Runs scored off the bat.
        balls_faced: Legal deliveries plus no-balls faced (wides excluded).

    Returns:
        float: Individual run rate rounded to 2 decimal places, or 0.0 if balls_faced == 0.
    """
    if balls_faced <= 0:
        return 0.0
    return round((runs / balls_faced) * 6.0, 2)


def get_innings_phase(
    value: Union[int, float],
    format: str = "T20",
    by_over_number: bool = False
) -> str:
    """
    Classify the innings phase based on delivery over number or legal balls bowled.

    Configurable for different match formats (T20, ODI).

    For T20:
      - Overs 1–6 (over numbers 0–5 or 0–36 legal balls): POWERPLAY
      - Overs 7–15 (over numbers 6–14 or 37–90 legal balls): MIDDLE
      - Overs 16–20 (over numbers 15–19+ or 91+ legal balls): DEATH

    For ODI:
      - Overs 1–10 (over numbers 0–9 or 0–60 legal balls): POWERPLAY
      - Overs 11–40 (over numbers 10–39 or 61–240 legal balls): MIDDLE
      - Overs 41–50 (over numbers 40–49+ or 241+ legal balls): DEATH

    Args:
        value: 0-based over index if by_over_number=True, else total legal balls bowled.
        format: Match format ('T20' or 'ODI').
        by_over_number: If True, value is the 0-based over number of the delivery (0 to 19).

    Returns:
        str: 'POWERPLAY', 'MIDDLE', or 'DEATH'.
    """
    fmt = format.upper()
    if fmt == "T20":
        if by_over_number:
            over_num = int(value)
            if over_num < 6:
                return "POWERPLAY"
            elif over_num < 15:
                return "MIDDLE"
            else:
                return "DEATH"
        else:
            balls = int(value)
            if balls <= 36:
                return "POWERPLAY"
            elif balls <= 90:
                return "MIDDLE"
            else:
                return "DEATH"

    elif fmt == "ODI":
        if by_over_number:
            over_num = int(value)
            if over_num < 10:
                return "POWERPLAY"
            elif over_num < 40:
                return "MIDDLE"
            else:
                return "DEATH"
        else:
            balls = int(value)
            if balls <= 60:
                return "POWERPLAY"
            elif balls <= 240:
                return "MIDDLE"
            else:
                return "DEATH"

    # Default fallback to T20
    return "POWERPLAY" if value <= 36 else ("MIDDLE" if value <= 90 else "DEATH")


def calculate_projected_score_simple(current_team_rr: float, total_overs: float = 20.0) -> float:
    """
    Calculate simple baseline projected score.

    NOTE: This is a simple baseline extrapolation (current_run_rate * total_overs)
    and NOT the final expected-score or win-probability model, which will be built
    in Phase 3.

    Formula:
        projected_score_simple = current_run_rate * total_overs

    Args:
        current_team_rr: Current team run rate.
        total_overs: Scheduled innings overs (default 20.0 for T20).

    Returns:
        float: Simple projected total runs, rounded to 1 decimal place.
    """
    if current_team_rr <= 0.0:
        return 0.0
    return round(current_team_rr * total_overs, 1)
