"""
Phase 7I: P3 Extreme Chase / Death-Over Dampening Audit Simulation Module.
Cricket Batter Contribution Model.

ISOLATED RESEARCH MODULE — DOES NOT MODIFY PRODUCTION PIPELINES.

Investigates P3-ISSUE-01:
In overs 18-20 of already nearly impossible chases, required run rate can become
mathematically extreme (30+, 40+, etc.), causing P3 to collapse toward 0 even when
the batter is making a meaningful contribution or is a tailender entering an impossible state.
When Context-as-Leverage multiplier (Phase 7H Model B) is applied, this negative deviation
is amplified further.

This module evaluates five candidate dampening models:
- Model A: RRR Cap
- Model B: Soft RRR Saturation
- Model C: Feasibility-Weighted RRR
- Model D: Balls-Remaining Weighted Penalty
- Model E: Hybrid (Feasibility-Gated Soft Saturation) [Recommended]
"""

import json
import math
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# Ensure repository root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

from src.phase7h_situational_leverage_simulation import (
    compute_wicket_crisis_signal,
    compute_chase_pressure_signal,
    leverage_model_b,
    compute_adjusted_pillar,
    compute_candidate_score,
    compute_production_score_25_35_40,
)

# Empirical standardization parameters for Pillar 3 (P3)
P3_MEAN = 0.159
P3_STD = 1.513
PILLAR_SCALE = 1.40


# ==============================================================================
# 1. CHASE FEASIBILITY & RUNAWAY SIGNAL
# ==============================================================================

def compute_chase_feasibility_signal(
    balls_remaining_entry: float,
    wickets_remaining_entry: float,
    required_rr_entry: float,
) -> Tuple[float, float, float]:
    """
    Evaluates whether the 2nd innings chase was realistically recoverable at entry.
    Does NOT use match outcome as input.

    Physical model:
    - Upper bound velocity (V_max): maximum realistic scoring rate in T20 death overs
      Base = 12.0 (2.0 runs/ball = SR 200).
      Wicket capacity adjustment: up to +3.0 with top order, down to -3.0 with tailenders.
      Ball scarcity burst: up to +4.0 when <= 12 balls remain.
    - Demand-to-capacity ratio: rho = RRR_entry / V_max.
    - Chase Feasibility (F_chase in [0.0, 1.0]):
      F >= 0.8: Difficult but realistically recoverable chase.
      0.2 <= F < 0.8: Extremely difficult chase.
      F < 0.2: Mathematically / realistically near-impossible chase.

    Returns:
        (V_max, ratio, F_chase)
    """
    b_rem = max(1.0, float(balls_remaining_entry))
    w_rem = max(1.0, min(10.0, float(wickets_remaining_entry)))
    rrr = min(120.0, max(0.0, float(required_rr_entry)))

    wkt_adj = 3.0 * float(np.tanh((w_rem - 3.5) / 2.0))
    burst_adj = 4.0 * (12.0 / (b_rem + 6.0))
    v_max = 12.0 + wkt_adj + burst_adj

    ratio = rrr / max(6.0, v_max)
    # Sigmoidal decay centered at ratio = 1.25
    f_chase = 1.0 / (1.0 + math.exp(4.0 * (ratio - 1.25)))
    return float(v_max), float(ratio), float(np.clip(f_chase, 0.0, 1.0))


# ==============================================================================
# 2. CANDIDATE P3 DAMPENING STRATEGIES
# ==============================================================================

def map_raw_to_p3_score(raw_val: float) -> float:
    """Standardizes and maps raw P3 to normalized 0.1-99.9 scale."""
    z = (float(raw_val) - P3_MEAN) / P3_STD
    val = 100.0 / (1.0 + math.exp(-PILLAR_SCALE * z))
    return float(np.clip(val, 0.1, 99.9))


def compute_dampened_p3_raw(
    row: Any,
    strategy: str = "baseline",
) -> float:
    """
    Computes raw Pillar 3 value under different chase RRR dampening strategies:
    - 'baseline': Unmodified production formula.
    - 'model_a': RRR Cap (hard cap at -4.5 if entry RRR >= 18.0).
    - 'model_b': Soft RRR Saturation (-5.0 tanh).
    - 'model_c': Feasibility-Weighted RRR (penalty cap modulated by F_chase).
    - 'model_d': Balls-Remaining Weighted Penalty.
    - 'model_e': Hybrid (Feasibility-Gated Soft Saturation) [Recommended].
    """
    innings = int(row.get("innings", 1))
    if innings > 2:
        return np.nan

    actual_runs = float(row.get("actual_runs", 0))
    balls_rem_exit = float(row.get("balls_remaining_exit", 0))
    wkts_rem_exit = float(row.get("wickets_remaining_exit", 5))
    wkt_res_chg = float(row.get("wicket_resource_change", 0))

    # Dynamic wicket cost
    if wkt_res_chg < 0:
        base_cost = (balls_rem_exit / 120.0) * (10.0 / max(1.0, wkts_rem_exit + 2.0)) * 0.5
        offset = min(base_cost * 0.7, max(0.0, actual_runs - 15.0) * 0.02)
        s_res = -(base_cost - offset)
    else:
        s_res = 0.15 * (wkts_rem_exit / 10.0)

    # 1st Innings: Not subject to chase RRR runaway; identical across all strategies
    if innings == 1:
        efs_chg = row.get("expected_final_change")
        if pd.notnull(efs_chg):
            z_efs = float(efs_chg) / 12.0
            traj_dev_chg = float(row.get("trajectory_deviation_change", 0.0)) / 10.0
            window_rr = float(row.get("window_team_rr", 7.5))
            team_rr_entry = float(row.get("team_rr_entry", 7.5))
            accel = np.clip((window_rr - team_rr_entry) / 3.0, -3.0, 3.0)
            raw = 0.50 * z_efs + 0.25 * traj_dev_chg + 0.25 * accel + s_res
            return float(raw)
        else:
            window_rr = float(row.get("window_team_rr", 7.5))
            team_rr_entry = float(row.get("team_rr_entry", 7.5))
            accel = np.clip((window_rr - team_rr_entry) / 3.0, -3.0, 3.0)
            runs_added = float(row.get("team_runs_added", actual_runs))
            overs_spent = max(0.2, float(row.get("overs_spent", 1.0)))
            raw = 0.60 * accel + 0.40 * ((runs_added - overs_spent * 8.0) / 10.0) + s_res
            return float(raw)

    # 2nd Innings (Chase)
    rrr_chg = float(row.get("required_rr_change", 0.0))
    rr_gap_chg = float(row.get("rr_gap_change", 0.0))
    t_prog = float(row.get("target_progress_change", 0.0))
    z_prog = (t_prog - 0.15) / 0.15

    b_rem = float(row.get("balls_remaining_entry", 30.0))
    w_rem = float(row.get("wickets_remaining_entry", 5.0))
    rrr_entry = float(row.get("required_rr_entry", 9.0))

    if strategy == "baseline":
        r_eff = np.clip(rrr_chg, -12.0, 12.0)
        g_eff = np.clip(rr_gap_chg, -12.0, 12.0)

    elif strategy == "model_a":
        # Model A: RRR Cap (hard cap at -4.5 if entry RRR >= 18.0)
        if rrr_entry >= 18.0 and rrr_chg < 0:
            r_eff = max(-4.5, rrr_chg)
            g_eff = max(-4.5, rr_gap_chg)
        else:
            r_eff = np.clip(rrr_chg, -12.0, 12.0)
            g_eff = np.clip(rr_gap_chg, -12.0, 12.0)

    elif strategy == "model_b":
        # Model B: Soft RRR Saturation (-5.0 tanh on negative deterioration)
        if rrr_chg < 0:
            r_eff = -5.0 * float(np.tanh(abs(rrr_chg) / 5.0))
            g_eff = -5.0 * float(np.tanh(abs(rr_gap_chg) / 5.0))
        else:
            r_eff = min(12.0, rrr_chg)
            g_eff = min(12.0, rr_gap_chg)

    elif strategy == "model_c":
        # Model C: Feasibility-Weighted RRR
        _, _, f_chase = compute_chase_feasibility_signal(b_rem, w_rem, rrr_entry)
        pen_cap = 4.0 + 8.0 * f_chase
        if rrr_chg < 0:
            r_eff = max(-pen_cap, rrr_chg)
            g_eff = max(-pen_cap, rr_gap_chg)
        else:
            r_eff = min(12.0, rrr_chg)
            g_eff = min(12.0, rr_gap_chg)

    elif strategy == "model_d":
        # Model D: Balls-Remaining Weighted Penalty
        pen_cap = 4.0 + 8.0 * min(1.0, max(0.1, b_rem / 24.0))
        if rrr_chg < 0:
            r_eff = max(-pen_cap, rrr_chg)
            g_eff = max(-pen_cap, rr_gap_chg)
        else:
            r_eff = min(12.0, rrr_chg)
            g_eff = min(12.0, rr_gap_chg)

    elif strategy == "model_e":
        # Model E: Hybrid (Feasibility-Gated Soft Saturation) [Recommended]
        _, _, f_chase = compute_chase_feasibility_signal(b_rem, w_rem, rrr_entry)
        pen_cap = 4.0 + 6.0 * f_chase
        if rrr_chg < 0:
            r_eff = -pen_cap * float(np.tanh(abs(rrr_chg) / pen_cap))
            g_eff = -pen_cap * float(np.tanh(abs(rr_gap_chg) / pen_cap))
        else:
            r_eff = min(12.0, rrr_chg)
            g_eff = min(12.0, rr_gap_chg)

    else:
        raise ValueError(f"Unknown P3 dampening strategy: {strategy}")

    z_rrr = r_eff / 3.0
    z_gap = g_eff / 3.0
    raw = 0.50 * z_rrr + 0.25 * z_gap + 0.25 * z_prog + s_res
    return float(raw)


def compute_all_p3_variants_for_row(row: Any) -> Dict[str, float]:
    """Computes normalized 0-100 P3 score for all candidate strategies."""
    res = {}
    for st in ["baseline", "model_a", "model_b", "model_c", "model_d", "model_e"]:
        raw = compute_dampened_p3_raw(row, strategy=st)
        res[f"p3_{st}"] = round(map_raw_to_p3_score(raw), 1)
    return res


# ==============================================================================
# 3. CRITICAL TEST SCENARIOS (PART 4 SPECIFICATION)
# ==============================================================================

PART4_CRITICAL_SCENARIOS = [
    {
        "case_id": "CASE-1",
        "name": "Siraj Impossible Chase",
        "description": "18.0 ov, RRR=54.9->100+, scores 3 off 8, P2 low",
        "innings": 2,
        "entry_over": 18.0,
        "balls_rem_entry": 12.0,
        "wkts_rem_entry": 2.0,
        "rrr_entry": 54.9,
        "rrr_exit": 100.0,
        "actual_runs": 3,
        "balls_faced": 8,
        "p2": 16.7,
        "target_progress_change": 0.02,
        "c_wkt": 74.0,
        "c_chase": 71.8,
    },
    {
        "case_id": "CASE-2",
        "name": "Death Explosive Burst",
        "description": "18.0 ov, RRR=22.0, scores 25 off 8, SR=312.5",
        "innings": 2,
        "entry_over": 18.0,
        "balls_rem_entry": 12.0,
        "wkts_rem_entry": 5.0,
        "rrr_entry": 22.0,
        "rrr_exit": 28.5,
        "actual_runs": 25,
        "balls_faced": 8,
        "p2": 95.0,
        "target_progress_change": 0.40,
        "c_wkt": 52.0,
        "c_chase": 71.0,
    },
    {
        "case_id": "CASE-3",
        "name": "Death Slow Batter in Steep Chase",
        "description": "18.0 ov, RRR=22.0, scores 10 off 8, SR=125.0",
        "innings": 2,
        "entry_over": 18.0,
        "balls_rem_entry": 12.0,
        "wkts_rem_entry": 5.0,
        "rrr_entry": 22.0,
        "rrr_exit": 51.0,
        "actual_runs": 10,
        "balls_faced": 8,
        "p2": 25.0,
        "target_progress_change": 0.10,
        "c_wkt": 52.0,
        "c_chase": 71.0,
    },
    {
        "case_id": "CASE-4",
        "name": "High-Quality Middle/Death Chase Effort",
        "description": "16.0 ov, RRR=14.0, scores 30 off 15, SR=200.0",
        "innings": 2,
        "entry_over": 16.0,
        "balls_rem_entry": 24.0,
        "wkts_rem_entry": 6.0,
        "rrr_entry": 14.0,
        "rrr_exit": 14.7,
        "actual_runs": 30,
        "balls_faced": 15,
        "p2": 82.0,
        "target_progress_change": 0.35,
        "c_wkt": 48.0,
        "c_chase": 64.0,
    },
    {
        "case_id": "CASE-5",
        "name": "Match-Winning Near-Miracle Finish",
        "description": "17.0 ov, RRR=18.0, scores 35 off 15, SR=233.3 (pulls RRR down)",
        "innings": 2,
        "entry_over": 17.0,
        "balls_rem_entry": 18.0,
        "wkts_rem_entry": 5.0,
        "rrr_entry": 18.0,
        "rrr_exit": 14.0,
        "actual_runs": 35,
        "balls_faced": 15,
        "p2": 92.0,
        "target_progress_change": 0.45,
        "c_wkt": 50.0,
        "c_chase": 68.0,
    },
    {
        "case_id": "CASE-6",
        "name": "20/3 Collapse Hero",
        "description": "1st inn, enters 20/3, scores 80 off 45",
        "innings": 1,
        "entry_over": 3.5,
        "balls_rem_entry": 99.0,
        "wkts_rem_entry": 7.0,
        "rrr_entry": 0.0,
        "rrr_exit": 0.0,
        "actual_runs": 80,
        "balls_faced": 45,
        "p2": 92.0,
        "target_progress_change": 0.0,
        "c_wkt": 72.1,
        "c_chase": 50.0,
    },
    {
        "case_id": "CASE-7",
        "name": "20/3 Collapse Failure",
        "description": "1st inn, enters 20/3, scores 5 off 12",
        "innings": 1,
        "entry_over": 3.5,
        "balls_rem_entry": 99.0,
        "wkts_rem_entry": 7.0,
        "rrr_entry": 0.0,
        "rrr_exit": 0.0,
        "actual_runs": 5,
        "balls_faced": 12,
        "p2": 15.0,
        "target_progress_change": 0.0,
        "c_wkt": 72.1,
        "c_chase": 50.0,
    },
    {
        "case_id": "CASE-8",
        "name": "Controlled Anchor Chase",
        "description": "2nd inn, RRR=8.0, scores 50 off 35",
        "innings": 2,
        "entry_over": 8.0,
        "balls_rem_entry": 72.0,
        "wkts_rem_entry": 8.0,
        "rrr_entry": 8.0,
        "rrr_exit": 6.5,
        "actual_runs": 50,
        "balls_faced": 35,
        "p2": 78.0,
        "target_progress_change": 0.35,
        "c_wkt": 44.0,
        "c_chase": 50.0,
    },
]


# ==============================================================================
# 4. FULL DATASET SIMULATION ENGINE
# ==============================================================================

def run_phase7i_simulation(
    data_path: str = "data/processed/batter_match_contributions.csv",
) -> Dict[str, Any]:
    """
    Executes full dataset audit across all 19,111 innings in IPL dataset:
    - Calculates baseline P3 and candidate dampened P3 variants (Models A, B, C, D, E)
    - Applies Phase 7H Model B Composite Dual-Slope leverage L to candidate P3 variants
    - Evaluates the 8 critical scenarios from Part 4
    - Validates 50 curated real IPL match examples across tailenders, heroes, finishers, and failures
    - Computes distribution metrics, rank correlations, and clipping audits
    """
    print(f"Loading {data_path}...")
    df = pd.read_csv(data_path, low_memory=False)
    n_total = len(df)
    print(f"Loaded {n_total:,} batter innings.")

    # 1. Compute P3 variants and Context-as-Leverage scores across all innings
    feasibility_list = []
    ratio_list = []

    p3_base_list = []
    p3_a_list = []
    p3_b_list = []
    p3_c_list = []
    p3_d_list = []
    p3_e_list = []

    score_base_list = []
    score_a_list = []
    score_b_list = []
    score_c_list = []
    score_d_list = []
    score_e_list = []

    lev_b_list = []

    for idx, row in df.iterrows():
        inn = int(row.get("innings", 1))
        t = float(row.get("entry_over", 0.0))
        b_rem = float(row.get("balls_remaining_entry", 120.0))
        w_rem = float(row.get("wickets_remaining_entry", 10.0))
        rrr = float(row.get("required_rr_entry", 0.0))
        p2 = float(row.get("score_perf", 50.0))

        # Feasibility signal (for 2nd innings)
        if inn == 2:
            _, rat, f = compute_chase_feasibility_signal(b_rem, w_rem, rrr)
        else:
            rat = 0.0
            f = 1.0
        feasibility_list.append(round(f, 4))
        ratio_list.append(round(rat, 2))

        # P3 variants
        raw_base = compute_dampened_p3_raw(row, "baseline")
        raw_a = compute_dampened_p3_raw(row, "model_a")
        raw_b = compute_dampened_p3_raw(row, "model_b")
        raw_c = compute_dampened_p3_raw(row, "model_c")
        raw_d = compute_dampened_p3_raw(row, "model_d")
        raw_e = compute_dampened_p3_raw(row, "model_e")

        p3_base = map_raw_to_p3_score(raw_base)
        p3_a = map_raw_to_p3_score(raw_a)
        p3_b = map_raw_to_p3_score(raw_b)
        p3_c = map_raw_to_p3_score(raw_c)
        p3_d = map_raw_to_p3_score(raw_d)
        p3_e = map_raw_to_p3_score(raw_e)

        p3_base_list.append(round(p3_base, 1))
        p3_a_list.append(round(p3_a, 1))
        p3_b_list.append(round(p3_b, 1))
        p3_c_list.append(round(p3_c, 1))
        p3_d_list.append(round(p3_d, 1))
        p3_e_list.append(round(p3_e, 1))

        # Context-as-Leverage using Phase 7H Model B Composite Dual-Slope
        cw = compute_wicket_crisis_signal(t, w_rem, b_rem)
        cc = compute_chase_pressure_signal(inn, t, float(row.get("team_rr_entry", 7.5)), float(row.get("target", 0.0)), rrr)
        lev_b, _ = leverage_model_b(cw, cc, inn)
        lev_b_list.append(round(lev_b, 3))

        # Overall Contribution Scores under Context-as-Leverage
        sc_base = compute_candidate_score(p2, p3_base, lev_b)
        sc_a = compute_candidate_score(p2, p3_a, lev_b)
        sc_b = compute_candidate_score(p2, p3_b, lev_b)
        sc_c = compute_candidate_score(p2, p3_c, lev_b)
        sc_d = compute_candidate_score(p2, p3_d, lev_b)
        sc_e = compute_candidate_score(p2, p3_e, lev_b)

        score_base_list.append(sc_base)
        score_a_list.append(sc_a)
        score_b_list.append(sc_b)
        score_c_list.append(sc_c)
        score_d_list.append(sc_d)
        score_e_list.append(sc_e)

    df["feasibility"] = feasibility_list
    df["feas_ratio"] = ratio_list
    df["lev_model_b"] = lev_b_list

    df["p3_base"] = p3_base_list
    df["p3_model_a"] = p3_a_list
    df["p3_model_b"] = p3_b_list
    df["p3_model_c"] = p3_c_list
    df["p3_model_d"] = p3_d_list
    df["p3_model_e"] = p3_e_list

    df["score_base"] = score_base_list
    df["score_model_a"] = score_a_list
    df["score_model_b"] = score_b_list
    df["score_model_c"] = score_c_list
    df["score_model_d"] = score_d_list
    df["score_model_e"] = score_e_list

    # 2. P3 Distribution Statistics across All Innings
    p3_stats = {}
    for col, name in [
        ("p3_base", "Baseline P3 (Unmodified)"),
        ("p3_model_a", "Model A (RRR Cap)"),
        ("p3_model_b", "Model B (Soft Saturation)"),
        ("p3_model_c", "Model C (Feasibility Weighted)"),
        ("p3_model_d", "Model D (Balls Remaining)"),
        ("p3_model_e", "Model E (Hybrid)"),
    ]:
        s = df[col]
        p3_stats[name] = {
            "mean": round(float(s.mean()), 2),
            "std": round(float(s.std()), 2),
            "median": round(float(s.median()), 2),
            "q10": round(float(s.quantile(0.10)), 2),
            "q25": round(float(s.quantile(0.25)), 2),
            "q75": round(float(s.quantile(0.75)), 2),
            "q90": round(float(s.quantile(0.90)), 2),
            "min": round(float(s.min()), 2),
            "max": round(float(s.max()), 2),
            "pct_below_5": round(float((s < 5.0).mean() * 100), 2),
            "pct_below_10": round(float((s < 10.0).mean() * 100), 2),
            "pct_above_95": round(float((s > 95.0).mean() * 100), 2),
        }

    # 3. Overall Contribution Score Statistics across All Innings
    score_stats = {}
    for col, name in [
        ("contribution_score", "Production 7D (25/35/40)"),
        ("score_base", "Phase 7H Base (Undampened P3)"),
        ("score_model_a", "Model A (RRR Cap)"),
        ("score_model_b", "Model B (Soft Saturation)"),
        ("score_model_c", "Model C (Feasibility Weighted)"),
        ("score_model_d", "Model D (Balls Remaining)"),
        ("score_model_e", "Model E (Hybrid) [Recommended]"),
    ]:
        s = df[col].dropna()
        score_stats[name] = {
            "mean": round(float(s.mean()), 2),
            "std": round(float(s.std()), 2),
            "median": round(float(s.median()), 2),
            "q10": round(float(s.quantile(0.10)), 2),
            "q25": round(float(s.quantile(0.25)), 2),
            "q75": round(float(s.quantile(0.75)), 2),
            "q90": round(float(s.quantile(0.90)), 2),
            "min": round(float(s.min()), 2),
            "max": round(float(s.max()), 2),
            "num_clipped_0_1": int((s <= 0.1).sum()),
            "num_clipped_99_9": int((s >= 99.9).sum()),
            "num_below_5": int((s < 5.0).sum()),
            "num_above_95": int((s > 95.0).sum()),
        }

    # 4. Correlation & Rank Stability
    rank_correlations = {}
    for col, name in [
        ("score_model_a", "Model A"),
        ("score_model_b", "Model B"),
        ("score_model_c", "Model C"),
        ("score_model_d", "Model D"),
        ("score_model_e", "Model E"),
    ]:
        corr_prod = float(df[col].corr(df["contribution_score"], method="spearman"))
        corr_7h = float(df[col].corr(df["score_base"], method="spearman"))
        corr_p2 = float(df[col].corr(df["score_perf"]))
        rank_correlations[name] = {
            "spearman_vs_production": round(corr_prod, 4),
            "spearman_vs_phase7h_base": round(corr_7h, 4),
            "score_vs_p2_correlation": round(corr_p2, 4),
        }

    # 5. Feasibility Breakdown in 2nd Innings
    inn2_df = df[df["innings"] == 2]
    feas_dist = {
        "recoverable_count": int((inn2_df["feasibility"] >= 0.8).sum()),
        "extreme_count": int((inn2_df["feasibility"].between(0.2, 0.8)).sum()),
        "impossible_count": int((inn2_df["feasibility"] < 0.2).sum()),
    }

    # 6. Evaluation of Part 4 Critical Scenarios
    part4_results = []
    for sc in PART4_CRITICAL_SCENARIOS:
        # Create a mock row
        mock_row = {
            "innings": sc["innings"],
            "entry_over": sc["entry_over"],
            "balls_remaining_entry": sc["balls_rem_entry"],
            "balls_remaining_exit": max(0.0, sc["balls_rem_entry"] - sc["balls_faced"]),
            "wickets_remaining_entry": sc["wkts_rem_entry"],
            "wickets_remaining_exit": sc["wkts_rem_entry"],
            "wicket_resource_change": 0,
            "actual_runs": sc["actual_runs"],
            "balls_faced": sc["balls_faced"],
            "required_rr_entry": sc["rrr_entry"],
            "required_rr_change": sc["rrr_entry"] - sc["rrr_exit"],
            "rr_gap_change": sc["rrr_entry"] - sc["rrr_exit"],
            "target_progress_change": sc["target_progress_change"],
            "expected_final_change": 15.0 if sc["actual_runs"] >= 50 else -10.0,
            "trajectory_deviation_change": 10.0 if sc["actual_runs"] >= 50 else -8.0,
            "window_team_rr": 10.0 if sc["actual_runs"] >= 50 else 4.0,
            "team_rr_entry": 7.5,
        }
        cw = sc["c_wkt"]
        cc = sc["c_chase"]
        lev, _ = leverage_model_b(cw, cc, sc["innings"])
        p2 = sc["p2"]

        p3_res = compute_all_p3_variants_for_row(mock_row)

        score_res = {}
        for st in ["baseline", "model_a", "model_b", "model_c", "model_d", "model_e"]:
            score_res[f"score_{st}"] = compute_candidate_score(p2, p3_res[f"p3_{st}"], lev)

        part4_results.append({
            "case_id": sc["case_id"],
            "name": sc["name"],
            "p2": p2,
            "leverage": round(lev, 3),
            "p3_variants": p3_res,
            "score_variants": score_res,
        })

    # 7. Curate 50 Real IPL Innings Validation Sample
    # Sample categories:
    # 1. Tailenders in impossible chases (15)
    # 2. Losing heroes (12)
    # 3. Successful finishers (10)
    # 4. Failed late chases (8)
    # 5. Collapse heroes & failures (5)
    sample_indices = []

    # Tailenders in impossible chases
    tail_candidates = df[(df["innings"] == 2) & (df["entry_over"] >= 16.0) & (df["required_rr_entry"] >= 25.0) & (df["actual_runs"] <= 10)]
    sample_indices.extend(tail_candidates.head(15).index.tolist())

    # Key iconic player cases explicitly required:
    # 2005: Siraj (impossible chase)
    # 2371: Andre Russell (65 off 25, losing hero)
    # 1684: Yuvraj Singh (1 off 3, late chase failure)
    # 3120: RA Tripathi (36 off 16, steep chase hero)
    # 14: TS Mills (6 off 3, impossible chase)
    # 15: YS Chahal (3 off 7, impossible chase)
    # 100: Hardik Pandya (29 off 11, successful finisher)
    # 2011: MS Dhoni (75* off 46 from 27/3, collapse hero)
    explicit_keys = [2005, 2371, 1684, 3120, 14, 15, 100, 2011]
    sample_indices.extend(explicit_keys)

    # Losing heroes
    hero_candidates = df[(df["innings"] == 2) & (~df["won_match"]) & (df["actual_runs"] >= 35) & (df["actual_sr"] >= 180) & (df["entry_over"] >= 10.0)]
    sample_indices.extend(hero_candidates.head(15).index.tolist())

    # Successful finishers
    finisher_candidates = df[(df["innings"] == 2) & (df["won_match"]) & (df["actual_runs"] >= 25) & (df["actual_sr"] >= 160) & (df["entry_over"] >= 14.0)]
    sample_indices.extend(finisher_candidates.head(15).index.tolist())

    # Failed late chases
    fail_candidates = df[(df["innings"] == 2) & (~df["won_match"]) & (df["entry_over"] >= 14.0) & (df["actual_runs"] <= 15) & (df["actual_sr"] <= 120)]
    sample_indices.extend(fail_candidates.head(15).index.tolist())

    # Collapse heroes and failures (1st innings)
    collapse_candidates = df[(df["innings"] == 1) & (df["entry_over"] <= 5.0) & (df["wickets_remaining_entry"] <= 7)]
    sample_indices.extend(collapse_candidates.head(10).index.tolist())

    # Ensure uniqueness and take at least 50
    sample_indices = list(dict.fromkeys(sample_indices))[:55]
    sample_50_df = df.loc[sample_indices]

    real_50_results = []
    for idx, r in sample_50_df.iterrows():
        real_50_results.append({
            "index": int(idx),
            "match_id": int(r["match_id"]),
            "player": str(r["player"]),
            "innings": int(r["innings"]),
            "entry_over": float(r["entry_over"]),
            "actual_runs": int(r["actual_runs"]),
            "balls_faced": int(r["balls_faced"]),
            "required_rr_entry": round(float(r["required_rr_entry"]), 1) if r["innings"] == 2 else 0.0,
            "won_match": bool(r["won_match"]),
            "p2": round(float(r["score_perf"]), 1),
            "p3_base": float(r["p3_base"]),
            "p3_model_b": float(r["p3_model_b"]),
            "p3_model_e": float(r["p3_model_e"]),
            "prod_score": round(float(r["contribution_score"]), 1),
            "score_base": float(r["score_base"]),
            "score_model_b": float(r["score_model_b"]),
            "score_model_e": float(r["score_model_e"]),
        })

    results = {
        "status": "COMPLETED",
        "dataset_size": n_total,
        "p3_stats": p3_stats,
        "score_stats": score_stats,
        "rank_correlations": rank_correlations,
        "feasibility_distribution": feas_dist,
        "part4_critical_scenarios": part4_results,
        "real_50_sample": real_50_results,
    }

    return results


def main():
    print("=" * 80)
    print("PHASE 7I: P3 EXTREME CHASE / DEATH-OVER DAMPENING AUDIT SIMULATION")
    print("=" * 80)

    results = run_phase7i_simulation()

    out_path = Path("models/contribution/phase7/phase7i_p3_extreme_chase_validation.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\n[Artifact Generated] Successfully wrote validation artifact to {out_path}")
    print("=" * 80)


if __name__ == "__main__":
    main()
