"""
Chase Context & Required Run Rate Calculation Module.

Provides utilities for:
1. Derivation and verification of chase targets.
2. Runs required calculations (handling completed chases).
3. Required run rate (RRR) calculations with boundary condition safety.
"""

from typing import Optional, Dict, Any


def calculate_runs_required(target: Optional[int], current_runs: int) -> Optional[int]:
    """
    Calculate the runs required to win the match.

    If target is None (first innings), returns None.
    If current_runs >= target, chase is complete; returns 0.

    Args:
        target: Target score set by the opposition (runs + 1).
        current_runs: Team runs scored so far.

    Returns:
        int or None: Runs required (>= 0), or None for non-chase innings.
    """
    if target is None:
        return None
    return max(0, int(target) - int(current_runs))


def calculate_required_run_rate(
    runs_required: Optional[int],
    balls_remaining: int
) -> Optional[float]:
    """
    Calculate the required run rate (RRR) per 6 legal balls.

    Formula:
        required_rr = (runs_required / balls_remaining) * 6

    Rules:
    - If target is None (not a chase), returns None.
    - If runs_required <= 0 (chase completed/won), returns 0.0 (never negative).
    - If balls_remaining <= 0 and runs_required > 0, returns 99.99 (target not reached in allotted balls).
    - If balls_remaining > 0, returns round((runs_required / balls_remaining) * 6, 2).

    Args:
        runs_required: Runs needed to win, or None.
        balls_remaining: Legal deliveries remaining in the innings.

    Returns:
        float or None: Required run rate rounded to 2 decimal places.
    """
    if runs_required is None:
        return None

    if runs_required <= 0:
        return 0.0

    if balls_remaining <= 0:
        return 99.99

    return round((runs_required / (balls_remaining / 6.0)), 2)


def get_chase_metrics(
    target: Optional[int],
    current_runs: int,
    balls_remaining: int
) -> Dict[str, Any]:
    """
    Generate complete chase context metrics for a given point in the innings.

    Args:
        target: Target score for the innings (None if 1st innings).
        current_runs: Total runs scored by the chasing team so far.
        balls_remaining: Scheduled legal balls remaining.

    Returns:
        dict: Containing target, is_chase, runs_required, balls_remaining, required_run_rate.
    """
    is_chase = target is not None
    runs_req = calculate_runs_required(target, current_runs)
    rrr = calculate_required_run_rate(runs_req, balls_remaining)

    return {
        "target": target,
        "is_chase": is_chase,
        "runs_required": runs_req,
        "balls_remaining": balls_remaining if is_chase else None,
        "required_run_rate": rrr,
    }
