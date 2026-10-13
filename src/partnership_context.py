"""
Phase 7C: Partnership & Non-Striker Context Engine.

Reconstructs and extracts active partnership windows and non-striker dynamics
from delivery-level ball-by-ball data for every batter innings:
- batter runs, partner runs, batter balls, partner balls
- batter SR vs partner SR
- partnership total runs and duration
- batter partnership share (relative scoring responsibility)
- partnership carry indicator (batter driving score while partner struggles)
- partner accelerating indicator (partner attacking while batter anchors)
- mutual acceleration indicator (both batters scoring at high tempo)
- wickets lost during partnership
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd

# Ensure repository root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def extract_all_partnerships_from_deliveries(df_deliveries: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Extracts all partnership instances across matches and innings from delivery records.
    Optimized for execution across hundreds of thousands of balls in ~2 seconds.
    """
    records = df_deliveries[[
        "match_id", "innings_number", "batter", "non_striker",
        "batter_runs", "total_runs", "wides", "noballs", "player_dismissed"
    ]].to_dict("records")

    partnerships = []
    current_key = None
    p_id = 0
    b1, b2 = None, None
    b1_runs, b1_balls = 0, 0
    b2_runs, b2_balls = 0, 0
    p_runs, p_balls = 0, 0
    survivor = None
    pending_new = True

    for row in records:
        mid = row["match_id"]
        inn = row["innings_number"]
        key = (mid, inn)

        if key != current_key:
            # End previous partnership if innings transitioned
            if current_key is not None and not pending_new and b1 is not None:
                partnerships.append({
                    "match_id": current_key[0],
                    "innings": current_key[1],
                    "partnership_id": p_id,
                    "batter_1": b1,
                    "batter_2": b2,
                    "b1_runs": b1_runs,
                    "b1_balls": b1_balls,
                    "b2_runs": b2_runs,
                    "b2_balls": b2_balls,
                    "partnership_runs": p_runs,
                    "partnership_balls": p_balls,
                    "wicket_fell": 0,
                    "dismissed_player": None,
                })
            current_key = key
            p_id = 1
            b1 = row["batter"]
            b2 = row["non_striker"]
            b1_runs, b1_balls = 0, 0
            b2_runs, b2_balls = 0, 0
            p_runs, p_balls = 0, 0
            survivor = None
            pending_new = False

        striker = row["batter"]
        non_striker = row["non_striker"]
        b_runs = int(row["batter_runs"] or 0)
        tot_runs = int(row["total_runs"] or 0)
        is_legal = (row["wides"] == 0) and (row["noballs"] == 0)

        p_dismissed = row["player_dismissed"]
        if pd.isna(p_dismissed) or str(p_dismissed).strip().lower() in ("", "nan", "none"):
            p_dismissed = None
        else:
            p_dismissed = str(p_dismissed).strip()

        if pending_new:
            p_id += 1
            if survivor and survivor in (striker, non_striker):
                b1 = survivor
                b2 = non_striker if striker == survivor else striker
            else:
                b1 = striker
                b2 = non_striker
            b1_runs, b1_balls = 0, 0
            b2_runs, b2_balls = 0, 0
            p_runs, p_balls = 0, 0
            survivor = None
            pending_new = False

        p_runs += tot_runs
        if is_legal:
            p_balls += 1

        if striker == b1:
            b1_runs += b_runs
            if is_legal:
                b1_balls += 1
        elif striker == b2:
            b2_runs += b_runs
            if is_legal:
                b2_balls += 1
        else:
            if b1 is None:
                b1 = striker
                b1_runs += b_runs
                if is_legal:
                    b1_balls += 1
            elif b2 is None:
                b2 = striker
                b2_runs += b_runs
                if is_legal:
                    b2_balls += 1

        if p_dismissed is not None:
            partnerships.append({
                "match_id": mid,
                "innings": inn,
                "partnership_id": p_id,
                "batter_1": b1,
                "batter_2": b2,
                "b1_runs": b1_runs,
                "b1_balls": b1_balls,
                "b2_runs": b2_runs,
                "b2_balls": b2_balls,
                "partnership_runs": p_runs,
                "partnership_balls": p_balls,
                "wicket_fell": 1,
                "dismissed_player": p_dismissed,
            })
            survivor = b2 if p_dismissed == b1 else b1
            pending_new = True

    if current_key is not None and not pending_new and b1 is not None:
        partnerships.append({
            "match_id": current_key[0],
            "innings": current_key[1],
            "partnership_id": p_id,
            "batter_1": b1,
            "batter_2": b2,
            "b1_runs": b1_runs,
            "b1_balls": b1_balls,
            "b2_runs": b2_runs,
            "b2_balls": b2_balls,
            "partnership_runs": p_runs,
            "partnership_balls": p_balls,
            "wicket_fell": 0,
            "dismissed_player": None,
        })

    return partnerships


def build_partnerships_lookup(partnerships_list: List[Dict[str, Any]]) -> Dict[Tuple[int, int], List[Dict[str, Any]]]:
    """Indexes partnerships by (match_id, innings)."""
    lookup: Dict[Tuple[int, int], List[Dict[str, Any]]] = {}
    for p in partnerships_list:
        key = (int(p["match_id"]), int(p["innings"]))
        if key not in lookup:
            lookup[key] = []
        lookup[key].append(p)
    return lookup


def compute_batter_partnership_profile(
    match_id: int,
    innings: int,
    player: str,
    partnerships_by_key: Dict[Tuple[int, int], List[Dict[str, Any]]],
    balls_faced: Optional[int] = None,
    actual_runs: Optional[int] = None,
    actual_sr: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Computes aggregated partnership and non-striker metrics for a specific batter stay.
    """
    key = (int(match_id), int(innings))
    parts = partnerships_by_key.get(key, [])

    b_runs_tot = 0
    b_balls_tot = 0
    p_runs_tot = 0
    p_balls_tot = 0
    part_runs_tot = 0
    part_balls_tot = 0
    wkts_during_parts = 0
    detailed_partners = []

    for p in parts:
        is_b1 = (p["batter_1"] == player)
        is_b2 = (p["batter_2"] == player)

        if not (is_b1 or is_b2):
            continue

        partner_name = p["batter_2"] if is_b1 else p["batter_1"]
        b_r = p["b1_runs"] if is_b1 else p["b2_runs"]
        b_b = p["b1_balls"] if is_b1 else p["b2_balls"]
        p_r = p["b2_runs"] if is_b1 else p["b1_runs"]
        p_b = p["b2_balls"] if is_b1 else p["b1_balls"]
        pr_runs = p["partnership_runs"]
        pr_balls = p["partnership_balls"]
        w_fell = p["wicket_fell"]

        b_runs_tot += b_r
        b_balls_tot += b_b
        p_runs_tot += p_r
        p_balls_tot += p_b
        part_runs_tot += pr_runs
        part_balls_tot += pr_balls
        wkts_during_parts += w_fell

        p_sr_single = round((p_r / p_b * 100.0), 1) if p_b > 0 else 0.0
        b_sr_single = round((b_r / b_b * 100.0), 1) if b_b > 0 else 0.0
        share_single = round((b_r / pr_runs * 100.0), 1) if pr_runs > 0 else 0.0

        detailed_partners.append({
            "partner": partner_name,
            "batter_runs": b_r,
            "batter_balls": b_b,
            "batter_sr": b_sr_single,
            "partner_runs": p_r,
            "partner_balls": p_b,
            "partner_sr": p_sr_single,
            "partnership_runs": pr_runs,
            "partnership_balls": pr_balls,
            "batter_share_pct": share_single,
            "wicket_fell": bool(w_fell),
        })

    # Use input actuals if available, otherwise calculated
    effective_b_runs = actual_runs if actual_runs is not None else b_runs_tot
    effective_b_balls = balls_faced if balls_faced is not None else b_balls_tot
    if actual_sr is not None:
        effective_b_sr = float(actual_sr)
    else:
        effective_b_sr = round((effective_b_runs / effective_b_balls * 100.0), 2) if effective_b_balls > 0 else 0.0

    partner_sr = round((p_runs_tot / p_balls_tot * 100.0), 2) if p_balls_tot > 0 else 0.0
    batter_part_share = round((effective_b_runs / part_runs_tot), 3) if part_runs_tot > 0 else 0.0
    sr_vs_partner = round(effective_b_sr - partner_sr, 2) if (p_balls_tot > 0 and effective_b_balls > 0) else 0.0

    # Categorical Dynamics
    is_carrying = bool(
        batter_part_share >= 0.65
        and effective_b_sr >= 130.0
        and partner_sr <= 115.0
        and effective_b_runs >= 20
    )
    is_partner_accelerating = bool(
        partner_sr >= 160.0
        and p_runs_tot >= 25
        and effective_b_sr < partner_sr
    )
    is_mutual_acceleration = bool(
        effective_b_sr >= 140.0
        and partner_sr >= 140.0
        and part_runs_tot >= 40
    )

    return {
        "num_partnerships": len(detailed_partners),
        "partnership_runs": part_runs_tot,
        "partnership_balls": part_balls_tot,
        "batter_runs_in_partnerships": effective_b_runs,
        "batter_balls_in_partnerships": effective_b_balls,
        "partner_runs": p_runs_tot,
        "partner_balls": p_balls_tot,
        "batter_sr": effective_b_sr,
        "partner_sr": partner_sr,
        "batter_partnership_share": batter_part_share,
        "sr_diff_vs_partner": sr_vs_partner,
        "carrying_partnership": is_carrying,
        "partner_accelerating": is_partner_accelerating,
        "mutual_acceleration": is_mutual_acceleration,
        "wickets_during_partnerships": wkts_during_parts,
        "detailed_partners": detailed_partners,
    }
