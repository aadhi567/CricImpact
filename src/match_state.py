"""
Match State & Delivery Situation Engine.

Constructs the comprehensive ball-by-ball match state table:
- Cumulative team scores, wickets, overs, balls remaining, run rates
- Exact match state before and after every delivery
- Batter cumulative performance at every ball faced
- Innings phase classification
- Chase requirements (target, runs required, required run rate)
- Baseline simple projected score (for first innings)
- Batting resources (wickets remaining, batters yet to bat)
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# Ensure repository root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from src.innings_context import (
    legal_balls_to_overs,
    calculate_team_run_rate,
    calculate_batter_strike_rate,
    calculate_batter_run_rate,
    get_innings_phase,
    calculate_projected_score_simple,
)
from src.chase_context import calculate_runs_required, calculate_required_run_rate


def build_innings_match_state(
    match_id: str,
    season: str,
    innings_number: int,
    batting_team: str,
    bowling_team: str,
    deliveries_list: List[Dict[str, Any]],
    target: Optional[int] = None,
    scheduled_overs: float = 20.0,
    format: str = "T20",
    delivery_partnership_ids: Optional[List[int]] = None
) -> List[Dict[str, Any]]:
    """
    Build ball-by-ball match state records for a single innings.

    Args:
        match_id: Match identifier string.
        season: IPL season string.
        innings_number: Innings sequence number (1, 2, 3, etc.).
        batting_team: Team batting.
        bowling_team: Team bowling.
        deliveries_list: List of delivery dictionaries in chronological order.
        target: Chase target score, or None for first innings.
        scheduled_overs: Maximum overs scheduled for the innings (default 20.0).
        format: Match format ('T20' or 'ODI').
        delivery_partnership_ids: Precomputed list of partnership IDs mapping to deliveries.

    Returns:
        List of delivery match state dictionaries.
    """
    records: List[Dict[str, Any]] = []
    if not deliveries_list:
        return records

    is_chase = target is not None
    scheduled_legal_balls = int(scheduled_overs * 6)

    # Innings cumulative state
    cum_runs = 0
    cum_wickets = 0
    cum_legal_balls = 0

    # Batter stats tracking: batter -> {runs, balls, fours, sixes, dots}
    batter_stats: Dict[str, Dict[str, int]] = {}
    seen_batters: List[str] = []

    # First add openers
    if deliveries_list:
        d0 = deliveries_list[0]
        for p in [d0.get("batter"), d0.get("non_striker")]:
            if p and p not in seen_batters:
                seen_batters.append(p)

    for idx, deliv in enumerate(deliveries_list):
        over_num = int(deliv.get("over", 0))
        ball_num = int(deliv.get("ball", 1))
        striker = str(deliv.get("batter", ""))
        non_striker = str(deliv.get("non_striker", ""))
        bowler = str(deliv.get("bowler", ""))

        b_runs = int(deliv.get("batter_runs", 0))
        e_runs = int(deliv.get("extras_runs", 0))
        tot_runs = int(deliv.get("total_runs", 0))
        extra_type = deliv.get("extra_type")
        wides = int(deliv.get("wides", 0))
        noballs = int(deliv.get("noballs", 0))

        is_wide = wides > 0
        is_noball = noballs > 0
        is_legal = (not is_wide) and (not is_noball)

        p_dismissed_raw = deliv.get("player_dismissed")
        if pd.isna(p_dismissed_raw) or str(p_dismissed_raw).strip().lower() in ("", "nan", "none"):
            p_dismissed = None
        else:
            p_dismissed = str(p_dismissed_raw).strip()

        d_kind_raw = deliv.get("dismissal_kind")
        if pd.isna(d_kind_raw) or str(d_kind_raw).strip().lower() in ("", "nan", "none"):
            d_kind = None
        else:
            d_kind = str(d_kind_raw).strip()

        is_wicket_flag = p_dismissed is not None

        # State BEFORE this delivery
        runs_before = cum_runs
        wickets_before = cum_wickets
        legal_balls_before = cum_legal_balls
        overs_before = legal_balls_to_overs(legal_balls_before)
        rr_before = calculate_team_run_rate(runs_before, legal_balls_before)
        phase_before = get_innings_phase(legal_balls_before, format=format)
        balls_rem_before = max(0, scheduled_legal_balls - legal_balls_before)

        # Track seen batters order for resources remaining
        for p in [striker, non_striker]:
            if p and p not in seen_batters:
                seen_batters.append(p)
        batters_yet_to_bat = max(0, 11 - len(seen_batters))

        # Initialize striker stat tracking if new
        if striker not in batter_stats:
            batter_stats[striker] = {
                "runs": 0,
                "balls": 0,
                "fours": 0,
                "sixes": 0,
                "dots": 0,
            }

        # Apply delivery outcomes to cumulative innings state
        cum_runs += tot_runs
        if is_legal:
            cum_legal_balls += 1
        if is_wicket_flag and d_kind != "retired hurt":
            cum_wickets += 1

        # Apply delivery outcomes to striker stat tracking
        # Wides do not count as balls faced by the batter
        if not is_wide:
            batter_stats[striker]["balls"] += 1
            if tot_runs == 0:
                batter_stats[striker]["dots"] += 1

        batter_stats[striker]["runs"] += b_runs
        if b_runs == 4:
            batter_stats[striker]["fours"] += 1
        elif b_runs == 6:
            batter_stats[striker]["sixes"] += 1

        # State AFTER this delivery
        runs_after = cum_runs
        wickets_after = cum_wickets
        legal_balls_after = cum_legal_balls
        overs_after = legal_balls_to_overs(legal_balls_after)
        rr_after = calculate_team_run_rate(runs_after, legal_balls_after)
        wickets_rem_after = max(0, 10 - wickets_after)
        balls_rem_after = max(0, scheduled_legal_balls - legal_balls_after)
        phase_after = get_innings_phase(legal_balls_after, format=format)

        # Batter state after this delivery
        b_st = batter_stats[striker]
        b_runs_so_far = b_st["runs"]
        b_balls_so_far = b_st["balls"]
        b_fours_so_far = b_st["fours"]
        b_sixes_so_far = b_st["sixes"]
        b_dots_so_far = b_st["dots"]
        b_sr_so_far = calculate_batter_strike_rate(b_runs_so_far, b_balls_so_far)
        b_rr_so_far = calculate_batter_run_rate(b_runs_so_far, b_balls_so_far)

        # Chase & First Innings projections
        runs_req = calculate_runs_required(target, runs_after) if is_chase else None
        rrr = calculate_required_run_rate(runs_req, balls_rem_after) if is_chase else None
        proj_score_simple = calculate_projected_score_simple(rr_after, total_overs=scheduled_overs)

        partnership_id = delivery_partnership_ids[idx] if delivery_partnership_ids and idx < len(delivery_partnership_ids) else None

        records.append({
            "match_id": match_id,
            "season": season,
            "innings_number": innings_number,
            "batting_team": batting_team,
            "bowling_team": bowling_team,
            "over": over_num,
            "ball": ball_num,
            "batter": striker,
            "non_striker": non_striker,
            "bowler": bowler,
            "batter_runs": b_runs,
            "extras_runs": e_runs,
            "total_runs": tot_runs,
            "extra_type": extra_type,
            "is_legal": is_legal,
            "is_wicket": is_wicket_flag,
            "player_dismissed": p_dismissed,
            "dismissal_kind": d_kind,
            # State BEFORE delivery
            "runs_before_delivery": runs_before,
            "wickets_before_delivery": wickets_before,
            "legal_balls_before_delivery": legal_balls_before,
            "overs_before_delivery": overs_before,
            "team_rr_before_delivery": rr_before,
            "balls_remaining_before_delivery": balls_rem_before,
            "phase_before_delivery": phase_before,
            # State AFTER delivery
            "total_team_runs_so_far": runs_after,
            "wickets_lost_so_far": wickets_after,
            "wickets_remaining": wickets_rem_after,
            "legal_balls_bowled_so_far": legal_balls_after,
            "overs_completed": overs_after,
            "balls_remaining_in_innings": balls_rem_after,
            "current_team_rr": rr_after,
            "innings_phase": phase_after,
            # Batter state so far
            "batter_runs_so_far": b_runs_so_far,
            "batter_balls_so_far": b_balls_so_far,
            "batter_strike_rate": b_sr_so_far,
            "batter_fours_so_far": b_fours_so_far,
            "batter_sixes_so_far": b_sixes_so_far,
            "batter_dot_balls_so_far": b_dots_so_far,
            "batter_run_rate": b_rr_so_far,
            # Context & Chase
            "is_chase": is_chase,
            "target": target,
            "runs_required": runs_req,
            "required_run_rate": rrr,
            "projected_score_simple": proj_score_simple,
            "partnership_id": partnership_id,
            "batters_yet_to_bat": batters_yet_to_bat,
        })

    return records
