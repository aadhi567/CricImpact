"""
Partnership Tracking and Extraction Module.

Identifies, tracks, and extracts all partnerships across an innings:
- Partnership start/end scores, wickets, overs
- Partnership runs, balls, run rate
- Individual batter contributions, boundaries, dot balls, and run shares
- Complete mathematical reconciliation with innings total runs.
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# Ensure repository root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from src.innings_context import legal_balls_to_overs, calculate_team_run_rate


def extract_innings_partnerships(
    match_id: str,
    innings_number: int,
    batting_team: str,
    deliveries_list: List[Dict[str, Any]]
) -> tuple[List[Dict[str, Any]], List[int]]:
    """
    Extract all partnerships for an innings from its delivery sequence.

    Args:
        match_id: Match identifier string.
        innings_number: 1, 2, 3, etc.
        batting_team: Name of the batting team.
        deliveries_list: Chronologically ordered delivery dictionaries for this innings.

    Returns:
        tuple:
            - partnerships_rows (list of dicts)
            - delivery_partnership_ids (list of partnership_ids mapped 1:1 to deliveries)
    """
    partnerships: List[Dict[str, Any]] = []
    deliv_partnership_ids: List[int] = []

    if not deliveries_list:
        return partnerships, deliv_partnership_ids

    partnership_id = 1
    d0 = deliveries_list[0]
    p_b1 = d0.get("batter")
    p_b2 = d0.get("non_striker")

    # Start states
    p_start_score = 0
    p_start_wickets = 0
    p_start_over = 0.0

    # Accumulators for current partnership
    p_runs = 0
    p_balls = 0  # legal balls

    b1_runs = 0
    b1_balls = 0
    b1_fours = 0
    b1_sixes = 0
    b1_dots = 0

    b2_runs = 0
    b2_balls = 0
    b2_fours = 0
    b2_sixes = 0
    b2_dots = 0

    current_team_score = 0
    current_team_wickets = 0
    current_legal_balls = 0

    survivor: Optional[str] = None
    next_partnership_pending = False

    for deliv in deliveries_list:
        striker = deliv.get("batter")
        non_striker = deliv.get("non_striker")
        b_runs = int(deliv.get("batter_runs", 0))
        tot_runs = int(deliv.get("total_runs", 0))
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

        is_wicket = p_dismissed is not None

        # If a new partnership starts with this delivery
        if next_partnership_pending:
            partnership_id += 1
            p_start_score = current_team_score
            p_start_wickets = current_team_wickets
            p_start_over = legal_balls_to_overs(current_legal_balls)

            # Determine batter_1 (survivor) and batter_2 (incoming batter)
            if survivor and survivor in (striker, non_striker):
                p_b1 = survivor
                p_b2 = non_striker if striker == survivor else striker
            else:
                p_b1 = striker
                p_b2 = non_striker

            # Reset partnership accumulators
            p_runs = 0
            p_balls = 0
            b1_runs, b1_balls, b1_fours, b1_sixes, b1_dots = 0, 0, 0, 0, 0
            b2_runs, b2_balls, b2_fours, b2_sixes, b2_dots = 0, 0, 0, 0, 0
            survivor = None
            next_partnership_pending = False

        # Tag delivery with its partnership ID
        deliv_partnership_ids.append(partnership_id)

        # Update innings totals
        current_team_score += tot_runs
        if is_legal:
            current_legal_balls += 1
        if is_wicket and d_kind != "retired hurt":
            current_team_wickets += 1

        # Update partnership totals
        p_runs += tot_runs
        if is_legal:
            p_balls += 1

        # Update individual batter stats in partnership
        if striker == p_b1:
            b1_runs += b_runs
            if not is_wide:
                b1_balls += 1
                if tot_runs == 0:
                    b1_dots += 1
            if b_runs == 4:
                b1_fours += 1
            elif b_runs == 6:
                b1_sixes += 1
        elif striker == p_b2:
            b2_runs += b_runs
            if not is_wide:
                b2_balls += 1
                if tot_runs == 0:
                    b2_dots += 1
            if b_runs == 4:
                b2_fours += 1
            elif b_runs == 6:
                b2_sixes += 1
        else:
            # Fallback if batter was not initialized (e.g. unexpected batsman substitution)
            if p_b1 is None:
                p_b1 = striker
                b1_runs += b_runs
                if not is_wide:
                    b1_balls += 1
            elif p_b2 is None:
                p_b2 = striker
                b2_runs += b_runs
                if not is_wide:
                    b2_balls += 1

        # Check if partnership ended on this ball
        if p_dismissed is not None:
            # Partnership ends on this delivery
            end_score = current_team_score
            end_wickets = current_team_wickets
            end_over = legal_balls_to_overs(current_legal_balls)
            p_rr = calculate_team_run_rate(p_runs, p_balls)

            b1_bound = b1_fours * 4 + b1_sixes * 6
            b2_bound = b2_fours * 4 + b2_sixes * 6
            b1_share = round((b1_runs / p_runs) * 100.0, 2) if p_runs > 0 else 0.0
            b2_share = round((b2_runs / p_runs) * 100.0, 2) if p_runs > 0 else 0.0

            partnerships.append({
                "match_id": match_id,
                "innings_number": innings_number,
                "batting_team": batting_team,
                "partnership_id": partnership_id,
                "batter_1": p_b1,
                "batter_2": p_b2,
                "partnership_start_score": p_start_score,
                "partnership_start_wickets": p_start_wickets,
                "partnership_start_over": p_start_over,
                "partnership_end_score": end_score,
                "partnership_end_wickets": end_wickets,
                "partnership_end_over": end_over,
                "partnership_runs": p_runs,
                "partnership_balls": p_balls,
                "partnership_rr": p_rr,
                "batter_1_runs_in_partnership": b1_runs,
                "batter_2_runs_in_partnership": b2_runs,
                "batter_1_run_share": b1_share,
                "batter_2_run_share": b2_share,
                "batter_1_boundary_runs": b1_bound,
                "batter_2_boundary_runs": b2_bound,
                "batter_1_dot_balls": b1_dots,
                "batter_2_dot_balls": b2_dots,
            })

            # Identify survivor for the next partnership
            if p_dismissed == p_b1:
                survivor = p_b2
            elif p_dismissed == p_b2:
                survivor = p_b1
            else:
                # E.g. non-striker got run out who was neither? Survivor is whoever remained
                survivor = non_striker if p_dismissed == striker else striker

            next_partnership_pending = True

    # If innings finished without ending the active partnership (e.g. completed overs, chase won)
    if not next_partnership_pending and p_b1 is not None:
        end_score = current_team_score
        end_wickets = current_team_wickets
        end_over = legal_balls_to_overs(current_legal_balls)
        p_rr = calculate_team_run_rate(p_runs, p_balls)

        b1_bound = b1_fours * 4 + b1_sixes * 6
        b2_bound = b2_fours * 4 + b2_sixes * 6
        b1_share = round((b1_runs / p_runs) * 100.0, 2) if p_runs > 0 else 0.0
        b2_share = round((b2_runs / p_runs) * 100.0, 2) if p_runs > 0 else 0.0

        partnerships.append({
            "match_id": match_id,
            "innings_number": innings_number,
            "batting_team": batting_team,
            "partnership_id": partnership_id,
            "batter_1": p_b1,
            "batter_2": p_b2,
            "partnership_start_score": p_start_score,
            "partnership_start_wickets": p_start_wickets,
            "partnership_start_over": p_start_over,
            "partnership_end_score": end_score,
            "partnership_end_wickets": end_wickets,
            "partnership_end_over": end_over,
            "partnership_runs": p_runs,
            "partnership_balls": p_balls,
            "partnership_rr": p_rr,
            "batter_1_runs_in_partnership": b1_runs,
            "batter_2_runs_in_partnership": b2_runs,
            "batter_1_run_share": b1_share,
            "batter_2_run_share": b2_share,
            "batter_1_boundary_runs": b1_bound,
            "batter_2_boundary_runs": b2_bound,
            "batter_1_dot_balls": b1_dots,
            "batter_2_dot_balls": b2_dots,
        })

    return partnerships, deliv_partnership_ids
