"""
Phase 7G: P3 Correction + P1 Leverage Stress Test Simulation Module.

ISOLATED RESEARCH MODULE — DOES NOT MODIFY PRODUCTION PIPELINES.
Investigates corrections for:
1. Issue 1: Death-Overs RRR Blowout (e.g. Russell 65 off 25 in lost chase)
2. Issue 2: Partner Coattail Effect (e.g. Dhawan 29 off 30 vs Warner 126 off 59)
   - Distinguishes legitimate supporting anchor from passenger/coattail
3. Issue 3: Low-Target Chase Artifact (e.g. Smith 15 off 18 in low-pressure chase)

Architecture Under Research:
  L(P1) = clip(1.0 + 0.35 * ((P1 - 50.0) / 50.0), 0.65, 1.35)
  Adjusted P2 = clip(50.0 + (P2 - 50.0) * L(P1), 0.1, 99.9)
  Adjusted P3 = clip(50.0 + (P3 - 50.0) * L(P1), 0.1, 99.9)
  Final 50/50 Contribution = 0.50 * Adjusted P2 + 0.50 * Adjusted P3
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.phase7c_rebalance import PHASE7C_P3_PARAMS
from src.contribution_framework import normalize_pillar_score


def leverage_model_a_linear(p1: float) -> float:
    """
    Model A Linear Bounded Leverage:
    L(P1) = clip(1.0 + 0.35 * ((P1 - 50.0) / 50.0), 0.65, 1.35)
    Invariants:
      P1 = 50 -> L = 1.0
      P1 = 100 -> L = 1.35
      P1 = 0 -> L = 0.65
    """
    if p1 is None or pd.isna(p1):
        return 1.0
    val = 1.0 + 0.35 * ((float(p1) - 50.0) / 50.0)
    return float(np.clip(val, 0.65, 1.35))


def compute_corrected_p3(
    row: Any,
    death_rrr_mode: str = "mode_1a_sr_capped",  # 'baseline', 'mode_1a_sr_capped', 'mode_1b_continuous', 'mode_1c_prog_reweight', 'mode_1d_impossible_gate'
    coattail_mode: str = "mode_2d_anchor_aware",  # 'baseline', 'mode_2a_share_dampening', 'mode_2b_escalated_diff', 'mode_2c_hybrid', 'mode_2d_anchor_aware'
    low_target_mode: str = "mode_3c_pace_cap",  # 'baseline', 'mode_3a_exec_gate', 'mode_3b_target_discount', 'mode_3c_pace_cap'
) -> Dict[str, Any]:
    """
    Computes P3 with parameterized treatments for:
    - Issue 1: Death-Overs RRR Blowout
    - Issue 2: Partner Coattail Effect (with anchor distinction)
    - Issue 3: Low-Target Chase Artifact
    """
    innings = int(row.get("innings", 1))
    if innings > 2:
        return {
            "p3_score": np.nan, "p3_raw": np.nan, "z3": np.nan,
            "z_macro": np.nan, "z_partner": np.nan, "z_collapse": np.nan, "z_wicket_equity": np.nan,
            "is_coattail": False, "is_anchor": False,
        }

    actual_runs = float(row.get("actual_runs", 0))
    balls_faced = float(row.get("balls_faced", 0))
    actual_sr = float(row.get("actual_sr", 0.0))
    target = float(row.get("target", 160)) if pd.notnull(row.get("target")) else 160.0
    balls_rem_exit = float(row.get("balls_remaining_exit", 0))
    wkts_rem_exit = float(row.get("wickets_remaining_exit", 5))

    # ---------------------------------------------------------
    # Sub-component 1: Macro Trajectory
    # ---------------------------------------------------------
    if innings == 1:
        efs_chg = row.get("expected_final_change")
        if pd.notnull(efs_chg):
            z_efs = float(efs_chg) / 12.0
            traj_dev_chg = float(row.get("trajectory_deviation_change", 0.0)) / 10.0
            window_rr = float(row.get("window_team_rr", 7.5))
            team_rr_entry = float(row.get("team_rr_entry", 7.5))
            accel = np.clip((window_rr - team_rr_entry) / 3.0, -3.0, 3.0)
            macro_score = 0.50 * z_efs + 0.25 * traj_dev_chg + 0.25 * accel
        else:
            window_rr = float(row.get("window_team_rr", 7.5))
            team_rr_entry = float(row.get("team_rr_entry", 7.5))
            accel = np.clip((window_rr - team_rr_entry) / 3.0, -3.0, 3.0)
            runs_added = float(row.get("team_runs_added", actual_runs))
            overs_spent = max(0.2, float(row.get("overs_spent", 1.0)))
            macro_score = 0.60 * accel + 0.40 * ((runs_added - overs_spent * 8.0) / 10.0)
    else:
        # Chase (innings == 2)
        raw_rrr_chg = float(row.get("required_rr_change", 0.0))
        t_prog = float(row.get("target_progress_change", 0.0))
        req_rr_entry = float(row.get("required_rr_entry", 8.5))

        # --- ISSUE 1: Death-Overs RRR Blowout Correction ---
        rrr_chg = raw_rrr_chg
        if death_rrr_mode == "baseline":
            rrr_chg = np.clip(raw_rrr_chg, -12.0, 12.0)
            z_rrr = rrr_chg / 3.0
            z_prog = (t_prog - 0.15) / 0.15
            macro_score = 0.65 * z_rrr + 0.35 * z_prog
        elif death_rrr_mode == "mode_1a_sr_capped":
            # Cap RRR deterioration penalty when balls_rem_exit <= 12 and batter SR is high
            if balls_rem_exit <= 12 and balls_faced >= 5 and raw_rrr_chg < 0:
                if actual_sr >= 160.0:
                    rrr_chg = max(raw_rrr_chg, -3.0)  # capped at -1.0 std dev
                elif actual_sr >= 130.0:
                    rrr_chg = max(raw_rrr_chg, -6.0)  # capped at -2.0 std dev
                else:
                    rrr_chg = np.clip(raw_rrr_chg, -12.0, 12.0)
            else:
                rrr_chg = np.clip(raw_rrr_chg, -12.0, 12.0)
            z_rrr = rrr_chg / 3.0
            z_prog = (t_prog - 0.15) / 0.15
            macro_score = 0.65 * z_rrr + 0.35 * z_prog
        elif death_rrr_mode == "mode_1b_continuous":
            if balls_rem_exit <= 18 and raw_rrr_chg < 0 and balls_faced >= 5:
                sr_surplus = max(0.0, (actual_sr - 130.0) / 40.0)
                offset = min(-raw_rrr_chg * 0.70, sr_surplus * 6.0)
                rrr_chg = np.clip(raw_rrr_chg + offset, -12.0, 12.0)
            else:
                rrr_chg = np.clip(raw_rrr_chg, -12.0, 12.0)
            z_rrr = rrr_chg / 3.0
            z_prog = (t_prog - 0.15) / 0.15
            macro_score = 0.65 * z_rrr + 0.35 * z_prog
        elif death_rrr_mode == "mode_1c_prog_reweight":
            rrr_chg = np.clip(raw_rrr_chg, -12.0, 12.0)
            z_rrr = rrr_chg / 3.0
            z_prog = (t_prog - 0.15) / 0.15
            if balls_rem_exit <= 12 and actual_sr >= 150.0 and balls_faced >= 5:
                macro_score = 0.30 * max(-2.0, z_rrr) + 0.70 * z_prog
            else:
                macro_score = 0.65 * z_rrr + 0.35 * z_prog
        elif death_rrr_mode == "mode_1d_impossible_gate":
            # If entering into an already near-impossible chase (req_rr >= 14), don't blame batter for exit RRR
            if balls_rem_exit <= 12 and req_rr_entry >= 14.0 and actual_sr >= 160.0 and balls_faced >= 5:
                rrr_chg = max(raw_rrr_chg, -2.0)
            elif balls_rem_exit <= 12 and balls_faced >= 5 and raw_rrr_chg < 0 and actual_sr >= 130.0:
                rrr_chg = max(raw_rrr_chg, -5.0)
            else:
                rrr_chg = np.clip(raw_rrr_chg, -12.0, 12.0)
            z_rrr = rrr_chg / 3.0
            z_prog = (t_prog - 0.15) / 0.15
            macro_score = 0.65 * z_rrr + 0.35 * z_prog
        else:
            rrr_chg = np.clip(raw_rrr_chg, -12.0, 12.0)
            z_rrr = rrr_chg / 3.0
            z_prog = (t_prog - 0.15) / 0.15
            macro_score = 0.65 * z_rrr + 0.35 * z_prog

        # --- ISSUE 3: Low-Target Chase Artifact Correction ---
        if target <= 125.0 and macro_score > 0:
            if low_target_mode == "mode_3a_exec_gate":
                if actual_sr < 110.0 and balls_faced >= 10:
                    dampen = max(0.20, actual_sr / 120.0)
                    macro_score *= dampen
            elif low_target_mode == "mode_3b_target_discount":
                target_ratio = min(1.0, target / 150.0)
                macro_score = macro_score * (0.50 + 0.50 * target_ratio)
            elif low_target_mode == "mode_3c_pace_cap":
                # Cap macro score at 0.30 if SR < 100 in comfortable chase
                if actual_sr < 100.0 and req_rr_entry <= 7.0 and balls_faced >= 10:
                    macro_score = min(0.30, macro_score)

    # ---------------------------------------------------------
    # Sub-component 2: Partnership & Non-Striker Context
    # ---------------------------------------------------------
    part_runs = float(row.get("partnership_runs", actual_runs))
    b_share = float(row.get("batter_partnership_share", 0.5 if actual_runs > 0 else 0.0))
    p_runs = float(row.get("partner_runs", max(0, part_runs - actual_runs)))

    z_share = np.clip((b_share - 0.50) / 0.25, -2.0, 2.0) if part_runs > 0 else 0.0

    overs_spent = max(0.1, float(row.get("overs_spent", balls_faced / 6.0)))
    partner_balls = max(0, int(overs_spent * 6) - int(balls_faced))
    partner_sr = float(row.get("partner_sr", (p_runs / partner_balls * 100.0) if partner_balls > 0 else 0.0))

    z_sr_diff = np.clip((actual_sr - partner_sr) / 60.0, -2.5, 2.5) if (partner_balls > 3 and balls_faced > 3) else 0.0

    is_carrying = bool(b_share >= 0.65 and actual_sr >= 130.0 and partner_sr <= 115.0 and actual_runs >= 20)
    is_mutual = bool(actual_sr >= 140.0 and partner_sr >= 135.0 and part_runs >= 40)
    synergy_bonus = 0.30 if is_carrying else (0.20 if is_mutual else 0.0)

    part_score = 0.50 * z_share + 0.35 * z_sr_diff + synergy_bonus

    # --- ISSUE 2: Partner Coattail vs Supporting Anchor ---
    is_coattail = bool(
        macro_score > 0
        and part_runs >= 35
        and (b_share < 0.30 or (p_runs >= 2.5 * max(1.0, actual_runs) and partner_sr >= actual_sr + 30.0))
    )

    # Legitimate Supporting Anchor detection:
    # Batter rotates strike (SR >= 115 and balls >= 15), partner is explosive, partnership > 50
    is_supporting_anchor = bool(
        is_coattail
        and actual_sr >= 115.0
        and balls_faced >= 15
        and partner_sr >= 155.0
    )

    if is_coattail:
        if coattail_mode == "mode_2a_share_dampening":
            share_factor = max(0.20, min(1.0, 2.0 * b_share))
            macro_score *= share_factor
        elif coattail_mode == "mode_2b_escalated_diff":
            extra_penalty = min(1.20, 0.40 * ((partner_sr - actual_sr) / 40.0))
            part_score -= extra_penalty
        elif coattail_mode == "mode_2c_hybrid":
            share_factor = max(0.25, min(1.0, 2.0 * b_share))
            macro_score *= share_factor
            extra_penalty = min(0.60, 0.25 * ((partner_sr - actual_sr) / 40.0))
            part_score -= extra_penalty
        elif coattail_mode == "mode_2d_anchor_aware":
            if is_supporting_anchor:
                # Legitimate supporting anchor: generous floor on macro, milder penalty
                share_factor = max(0.55, min(1.0, 2.5 * b_share))
                macro_score *= share_factor
                extra_penalty = min(0.30, 0.15 * ((partner_sr - actual_sr) / 40.0))
                part_score -= extra_penalty
            else:
                # Pure coattail passenger: deep dampening
                share_factor = max(0.20, min(1.0, 1.8 * b_share))
                macro_score *= share_factor
                extra_penalty = min(0.65, 0.30 * ((partner_sr - actual_sr) / 40.0))
                part_score -= extra_penalty

    # ---------------------------------------------------------
    # Sub-component 3: Collapse Recovery
    # ---------------------------------------------------------
    balls_rem_entry = float(row.get("balls_remaining_entry", 120))
    wkts_rem_entry = float(row.get("wickets_remaining_entry", 10))
    wkts_lost = float(row.get("wickets_lost_during_stay", 0))
    overs_per_wkt_entry = (balls_rem_entry / 6.0) / max(1.0, wkts_rem_entry)

    if overs_per_wkt_entry >= 1.8 and actual_runs >= 20:
        z_stab = min(2.0, (actual_runs - 15.0) / 20.0) * min(1.5, overs_per_wkt_entry / 1.5)
        if wkts_lost >= 3:
            z_stab -= (wkts_lost - 2) * 0.25
    else:
        z_stab = 0.0
        if wkts_lost >= 4 and actual_runs < 20:
            z_stab = -0.45

    # ---------------------------------------------------------
    # Sub-component 4: Wicket Equity
    # ---------------------------------------------------------
    wkt_res_chg = float(row.get("wicket_resource_change", 0))
    if wkt_res_chg < 0:
        base_cost = (balls_rem_exit / 120.0) * (10.0 / max(1.0, wkts_rem_exit + 2.0)) * 0.5
        offset = min(base_cost * 0.7, max(0.0, actual_runs - 15.0) * 0.02)
        s_res = -(base_cost - offset)
    else:
        s_res = 0.15 * (wkts_rem_exit / 10.0)

    # ---------------------------------------------------------
    # Composite Raw P3 and Standardized Normalization
    # ---------------------------------------------------------
    p3_raw = 0.45 * macro_score + 0.30 * part_score + 0.15 * z_stab + 0.10 * s_res
    z3 = (p3_raw - PHASE7C_P3_PARAMS["p3_mean"]) / PHASE7C_P3_PARAMS["p3_std"]
    score_p3 = normalize_pillar_score(z3, k=PHASE7C_P3_PARAMS["p3_scale"])

    return {
        "p3_score": round(float(score_p3), 1),
        "p3_raw": round(float(p3_raw), 4),
        "z3": round(float(z3), 4),
        "z_macro": round(float(macro_score), 4),
        "z_partner": round(float(part_score), 4),
        "z_collapse": round(float(z_stab), 4),
        "z_wicket_equity": round(float(s_res), 4),
        "is_coattail": is_coattail,
        "is_anchor": is_supporting_anchor,
    }


def compute_phase7g_contribution(
    row: Any,
    death_rrr_mode: str = "mode_1a_sr_capped",
    coattail_mode: str = "mode_2d_anchor_aware",
    low_target_mode: str = "mode_3c_pace_cap",
) -> Dict[str, Any]:
    """
    Computes Phase 7G Contribution Score:
      L(P1) = clip(1.0 + 0.35 * ((P1 - 50.0) / 50.0), 0.65, 1.35)
      Adjusted P2 = clip(50.0 + (P2 - 50.0) * L(P1), 0.1, 99.9)
      Adjusted P3 = clip(50.0 + (P3 - 50.0) * L(P1), 0.1, 99.9)
      Final 50/50 = 0.50 * Adjusted P2 + 0.50 * Adjusted P3
    """
    # Strict DNB rule
    if (
        row.get("dnb") is True
        or row.get("did_not_bat") is True
        or (pd.isna(row.get("balls_faced")) and pd.isna(row.get("actual_runs")))
    ):
        return {
            "dnb": True,
            "super_over": False,
            "contribution_score": None,
            "adj_p2": None,
            "adj_p3": None,
            "p1_score": None,
            "p2_score": None,
            "p3_score": None,
            "p3_raw": None,
            "leverage": None,
            "current_production_score": row.get("contribution_score"),
            "score_difference": None,
        }

    # Super over
    if int(row.get("innings", 1)) > 2:
        return {
            "dnb": False,
            "super_over": True,
            "contribution_score": None,
            "adj_p2": None,
            "adj_p3": None,
            "p1_score": None,
            "p2_score": None,
            "p3_score": None,
            "p3_raw": None,
            "leverage": None,
            "current_production_score": row.get("contribution_score"),
            "score_difference": None,
        }

    p1 = float(row.get("score_context", 50.0))
    p2 = float(row.get("score_perf", 50.0))

    # Compute corrected P3
    p3_res = compute_corrected_p3(
        row,
        death_rrr_mode=death_rrr_mode,
        coattail_mode=coattail_mode,
        low_target_mode=low_target_mode,
    )
    p3 = p3_res["p3_score"]

    # Model A linear bounded leverage
    lev = leverage_model_a_linear(p1)

    adj_p2 = float(np.clip(50.0 + (p2 - 50.0) * lev, 0.1, 99.9))
    adj_p3 = float(np.clip(50.0 + (p3 - 50.0) * lev, 0.1, 99.9))

    cand_score = float(np.clip(0.50 * adj_p2 + 0.50 * adj_p3, 0.1, 99.9))

    # Compare with current 25/35/40 production score
    curr_score = row.get("contribution_score")
    if pd.isna(curr_score) or curr_score is None:
        curr_score = 0.25 * p1 + 0.35 * p2 + 0.40 * float(row.get("score_state", 50.0))
        curr_score = round(float(np.clip(curr_score, 0.1, 99.9)), 1)
    else:
        curr_score = round(float(curr_score), 1)

    return {
        "dnb": False,
        "super_over": False,
        "contribution_score": round(cand_score, 1),
        "adj_p2": round(adj_p2, 1),
        "adj_p3": round(adj_p3, 1),
        "p1_score": round(p1, 1),
        "p2_score": round(p2, 1),
        "p3_score": round(p3, 1),
        "p3_raw": p3_res["p3_raw"],
        "leverage": round(lev, 3),
        "current_production_score": curr_score,
        "score_difference": round(cand_score - curr_score, 1),
        "z_macro": p3_res["z_macro"],
        "z_partner": p3_res["z_partner"],
        "z_collapse": p3_res["z_collapse"],
        "z_wicket_equity": p3_res["z_wicket_equity"],
        "is_coattail": p3_res["is_coattail"],
        "is_anchor": p3_res["is_anchor"],
    }
