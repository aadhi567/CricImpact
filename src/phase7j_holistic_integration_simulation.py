"""
Phase 7J: Holistic Context-as-Leverage Integration Simulation Module.
Cricket Batter Contribution Model.

ISOLATED RESEARCH MODULE — DOES NOT MODIFY PRODUCTION PIPELINES.

Integrates:
1. Phase 7H Situational Leverage Architecture (Composite Dual-Slope Model B context signal):
   - Adjusted P2 = clip(50 + (P2 - 50) * L, 0.1, 99.9)
   - Adjusted P3 = clip(50 + (P3_dampened - 50) * L, 0.1, 99.9)
   - Overall Contribution = 0.50 * Adjusted P2 + 0.50 * Adjusted P3
   - Context is NOT a direct scoring pillar (P1 contributes 0 direct points).
   - Leverage bounded strictly in [0.65, 1.35]; Par Invariance L(50.0) == 1.000.
2. Phase 7I Model E P3 Extreme-Chase Dampening:
   - Feasibility-gated soft saturation based on F_chase in [0.0, 1.0].
   - Relieves denominator blowout in late death chases without distorting recoverable games.
   - 1st innings matches remain 100% untouched.
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
    compute_opening_opportunity_signal,
    compute_match_state_leverage_classification,
    leverage_model_b,
    compute_adjusted_pillar,
    compute_candidate_score,
    compute_production_score_25_35_40,
)
from src.phase7i_p3_extreme_chase_simulation import (
    compute_chase_feasibility_signal,
    compute_dampened_p3_raw,
    map_raw_to_p3_score,
)


# ==============================================================================
# 1. HOLISTIC SCORING ENGINE
# ==============================================================================

def compute_phase7j_context_and_leverage(row: Any) -> Dict[str, Any]:
    """
    Computes complete Phase 7J context signals and situational leverage multiplier L:
    - C_wkt: Wicket crisis pressure (0-100 scale, par = 50.0)
    - C_chase: Chase pressure (0-100 scale, par = 50.0)
    - C_open: Opening builder opportunity (par = 50.0)
    - C_match: 5-zone match classification
    - C_eff: Composite effective difficulty
    - Leverage L: Composite Dual-Slope bounded in [0.65, 1.35], L(50.0) = 1.000
    """
    innings = int(row.get("innings", 1))
    entry_over = float(row.get("entry_over", 0.0))
    wkts_rem = float(row.get("wickets_remaining_entry", row.get("wkts_rem_entry", 10.0)))
    balls_rem = float(row.get("balls_remaining_entry", row.get("balls_rem_entry", 120.0)))
    team_rr = float(row.get("team_rr_entry", row.get("team_rr", 7.5)))
    target = float(row.get("target", 0.0)) if innings == 2 else 0.0
    req_rr = float(row.get("required_rr_entry", row.get("req_rr", 0.0))) if innings == 2 else 0.0

    c_wkt = compute_wicket_crisis_signal(entry_over, wkts_rem, balls_rem)
    c_chase = compute_chase_pressure_signal(innings, entry_over, team_rr, target, req_rr)
    c_open = compute_opening_opportunity_signal(entry_over, wkts_rem, balls_rem)
    zone = compute_match_state_leverage_classification(c_wkt, c_chase)

    lev, c_eff = leverage_model_b(c_wkt, c_chase, innings)

    return {
        "c_wkt": round(c_wkt, 1),
        "c_chase": round(c_chase, 1),
        "c_open": round(c_open, 1),
        "c_eff": round(c_eff, 1),
        "context_zone": zone,
        "leverage": round(lev, 3),
    }


def compute_phase7j_contribution(
    row: Any,
    p3_strategy: str = "model_e",
) -> Dict[str, Any]:
    """
    Computes complete Phase 7J contribution assessment for a batter innings:
    - P2: Unmodified batting execution
    - P3: Model E feasibility-gated soft saturation
    - L: Phase 7H Composite Dual-Slope leverage
    - Adjusted P2 = clip(50 + (P2 - 50) * L, 0.1, 99.9)
    - Adjusted P3 = clip(50 + (P3 - 50) * L, 0.1, 99.9)
    - Overall = 0.50 * Adjusted P2 + 0.50 * Adjusted P3
    - Preserves DNB as None.
    """
    # DNB check
    if row.get("is_dnb", False) or pd.isna(row.get("actual_runs")) and pd.isna(row.get("balls_faced")):
        return {
            "is_dnb": True,
            "p2": None,
            "p3": None,
            "leverage": None,
            "adjusted_p2": None,
            "adjusted_p3": None,
            "contribution_score": None,
        }

    p2 = float(row.get("score_perf", 50.0))

    # P3 computation with Model E dampening
    raw_p3 = compute_dampened_p3_raw(row, strategy=p3_strategy)
    p3 = map_raw_to_p3_score(raw_p3)

    ctx = compute_phase7j_context_and_leverage(row)
    lev = ctx["leverage"]

    adj_p2 = compute_adjusted_pillar(p2, lev)
    adj_p3 = compute_adjusted_pillar(p3, lev)
    score = round(float(np.clip(0.50 * adj_p2 + 0.50 * adj_p3, 0.1, 99.9)), 1)

    return {
        "is_dnb": False,
        "p2": round(p2, 1),
        "p3": round(p3, 1),
        "c_wkt": ctx["c_wkt"],
        "c_chase": ctx["c_chase"],
        "c_eff": ctx["c_eff"],
        "context_zone": ctx["context_zone"],
        "leverage": lev,
        "adjusted_p2": round(adj_p2, 1),
        "adjusted_p3": round(adj_p3, 1),
        "contribution_score": score,
    }


# ==============================================================================
# 2. REQUIRED CORE SCENARIOS (A THROUGH N)
# ==============================================================================

CORE_SCENARIOS_SPEC = [
    {
        "id": "A",
        "name": "0/0 Elite Opener",
        "description": "1st inn, enters 0/0, scores 80 (P2=90, P3=85)",
        "innings": 1,
        "entry_over": 0.0,
        "balls_rem_entry": 120.0,
        "wkts_rem_entry": 10.0,
        "target": 0.0,
        "req_rr": 0.0,
        "p2": 90.0,
        "p3": 85.0,
        "won_match": True,
    },
    {
        "id": "B",
        "name": "20/3 Elite Collapse Rescue",
        "description": "1st inn, enters 20/3, scores 80 (same P2=90, P3=85)",
        "innings": 1,
        "entry_over": 3.5,
        "balls_rem_entry": 99.0,
        "wkts_rem_entry": 7.0,
        "target": 0.0,
        "req_rr": 0.0,
        "p2": 90.0,
        "p3": 85.0,
        "won_match": True,
    },
    {
        "id": "C",
        "name": "0/0 Opener Failure",
        "description": "1st inn, enters 0/0, fails cheaply (P2=15, P3=20)",
        "innings": 1,
        "entry_over": 0.0,
        "balls_rem_entry": 120.0,
        "wkts_rem_entry": 10.0,
        "target": 0.0,
        "req_rr": 0.0,
        "p2": 15.0,
        "p3": 20.0,
        "won_match": False,
    },
    {
        "id": "D",
        "name": "20/3 Crisis Failure",
        "description": "1st inn, enters 20/3, fails cheaply (same P2=15, P3=20)",
        "innings": 1,
        "entry_over": 3.5,
        "balls_rem_entry": 99.0,
        "wkts_rem_entry": 7.0,
        "target": 0.0,
        "req_rr": 0.0,
        "p2": 15.0,
        "p3": 20.0,
        "won_match": False,
    },
    {
        "id": "E",
        "name": "0/0 Chase Modest Target (115)",
        "description": "2nd inn chasing 115, strong batter (P2=90, P3=85)",
        "innings": 2,
        "entry_over": 0.0,
        "balls_rem_entry": 120.0,
        "wkts_rem_entry": 10.0,
        "target": 115.0,
        "req_rr": 5.75,
        "p2": 90.0,
        "p3": 85.0,
        "won_match": True,
    },
    {
        "id": "F",
        "name": "0/0 Chase Steep Target (184)",
        "description": "2nd inn chasing 184, same strong batter (P2=90, P3=85)",
        "innings": 2,
        "entry_over": 0.0,
        "balls_rem_entry": 120.0,
        "wkts_rem_entry": 10.0,
        "target": 184.0,
        "req_rr": 9.20,
        "p2": 90.0,
        "p3": 85.0,
        "won_match": True,
    },
    {
        "id": "G",
        "name": "0/0 Chase High Target (208)",
        "description": "2nd inn chasing 208, same strong batter (P2=90, P3=85)",
        "innings": 2,
        "entry_over": 0.0,
        "balls_rem_entry": 120.0,
        "wkts_rem_entry": 10.0,
        "target": 208.0,
        "req_rr": 10.40,
        "p2": 90.0,
        "p3": 85.0,
        "won_match": True,
    },
    {
        "id": "H",
        "name": "20/3 Collapse Hero (80 runs)",
        "description": "1st inn, enters 20/3, blasts match-winning 80 (P2=94, P3=92)",
        "innings": 1,
        "entry_over": 3.5,
        "balls_rem_entry": 99.0,
        "wkts_rem_entry": 7.0,
        "target": 0.0,
        "req_rr": 0.0,
        "p2": 94.0,
        "p3": 92.0,
        "won_match": True,
    },
    {
        "id": "I",
        "name": "Impossible Chase Tailender (3 off 8)",
        "description": "2nd inn, enters 17.4 ov, 14 balls rem, RRR 54.9, scores 3 (P2=16.7, P3=22.0)",
        "innings": 2,
        "entry_over": 17.4,
        "balls_rem_entry": 14.0,
        "wkts_rem_entry": 2.0,
        "target": 232.0,
        "req_rr": 54.9,
        "p2": 16.7,
        "p3": 22.0,
        "won_match": False,
    },
    {
        "id": "J",
        "name": "Impossible Chase Hero (65 off 25)",
        "description": "2nd inn, enters 12.0 ov, RRR 16.6, blasts 65 off 25 (P2=93.1, P3=58.0)",
        "innings": 2,
        "entry_over": 12.0,
        "balls_rem_entry": 48.0,
        "wkts_rem_entry": 6.0,
        "target": 214.0,
        "req_rr": 16.6,
        "p2": 93.1,
        "p3": 58.0,
        "won_match": False,
    },
    {
        "id": "K",
        "name": "Feasible Death Chase Failure (1 off 3)",
        "description": "2nd inn, enters 18.4 ov, RRR 14.25 (recoverable), fails 1 off 3 (P2=10.9, P3=12.0)",
        "innings": 2,
        "entry_over": 18.4,
        "balls_rem_entry": 8.0,
        "wkts_rem_entry": 5.0,
        "target": 187.0,
        "req_rr": 14.25,
        "p2": 10.9,
        "p3": 12.0,
        "won_match": False,
    },
    {
        "id": "L",
        "name": "Feasible Death Chase Finish (35 off 15)",
        "description": "2nd inn, enters 17.0 ov, RRR 18.0, wins with 35 off 15 (P2=92.0, P3=78.8)",
        "innings": 2,
        "entry_over": 17.0,
        "balls_rem_entry": 18.0,
        "wkts_rem_entry": 5.0,
        "target": 180.0,
        "req_rr": 18.0,
        "p2": 92.0,
        "p3": 78.8,
        "won_match": True,
    },
    {
        "id": "M",
        "name": "Winning Passenger",
        "description": "Low execution (P2=20, P3=25) on winning team",
        "innings": 2,
        "entry_over": 18.0,
        "balls_rem_entry": 12.0,
        "wkts_rem_entry": 8.0,
        "target": 150.0,
        "req_rr": 6.0,
        "p2": 20.0,
        "p3": 25.0,
        "won_match": True,
    },
    {
        "id": "N",
        "name": "Losing Hero",
        "description": "High execution (P2=90, P3=80) on losing team",
        "innings": 2,
        "entry_over": 14.0,
        "balls_rem_entry": 36.0,
        "wkts_rem_entry": 4.0,
        "target": 210.0,
        "req_rr": 15.0,
        "p2": 90.0,
        "p3": 80.0,
        "won_match": False,
    },
]


# ==============================================================================
# 3. SIMULATION ENGINE ACROSS DATASET & 75+ REAL MATCHES
# ==============================================================================

def run_phase7j_simulation(
    data_path: str = "data/processed/batter_match_contributions.csv",
) -> Dict[str, Any]:
    """
    Executes complete holistic integration simulation:
    - All 19,111 innings with Model E P3 dampening and Phase 7H leverage
    - All 14 Core Scenarios A through N
    - 75+ Curated Real IPL Match Innings
    - Full Population Statistics & Subgroup Analyses
    - Strict Invariance Verifications
    """
    print(f"Loading {data_path}...")
    df = pd.read_csv(data_path, low_memory=False)
    n_total = len(df)
    print(f"Loaded {n_total:,} batter innings.")

    # 1. Compute Phase 7J scores across all rows
    p2_list = []
    p3_damp_list = []
    lev_list = []
    adj_p2_list = []
    adj_p3_list = []
    score_7j_list = []
    c_wkt_list = []
    c_chase_list = []
    c_eff_list = []
    zone_list = []

    for idx, row in df.iterrows():
        res = compute_phase7j_contribution(row, p3_strategy="model_e")
        p2_list.append(res["p2"])
        p3_damp_list.append(res["p3"])
        lev_list.append(res["leverage"])
        adj_p2_list.append(res["adjusted_p2"])
        adj_p3_list.append(res["adjusted_p3"])
        score_7j_list.append(res["contribution_score"])
        c_wkt_list.append(res["c_wkt"])
        c_chase_list.append(res["c_chase"])
        c_eff_list.append(res["c_eff"])
        zone_list.append(res["context_zone"])

    df["phase7j_p2"] = p2_list
    df["phase7j_p3"] = p3_damp_list
    df["phase7j_leverage"] = lev_list
    df["phase7j_adj_p2"] = adj_p2_list
    df["phase7j_adj_p3"] = adj_p3_list
    df["phase7j_score"] = score_7j_list
    df["c_wkt"] = c_wkt_list
    df["c_chase"] = c_chase_list
    df["c_eff"] = c_eff_list
    df["context_zone"] = zone_list

    # 2. Population Statistics
    score_s = df["phase7j_score"].dropna()
    prod_s = df["contribution_score"].dropna()

    diff_s = score_s - prod_s

    pearson_corr = float(score_s.corr(prod_s, method="pearson"))
    spearman_corr = float(score_s.corr(prod_s, method="spearman"))

    p2_p3_corr_before = float(df["phase7j_p2"].corr(df["phase7j_p3"]))
    p2_p3_corr_after = float(df["phase7j_adj_p2"].corr(df["phase7j_adj_p3"]))

    pop_stats = {
        "dataset_size": n_total,
        "pearson_vs_production": round(pearson_corr, 4),
        "spearman_vs_production": round(spearman_corr, 4),
        "mean_score": round(float(score_s.mean()), 2),
        "median_score": round(float(score_s.median()), 2),
        "std_score": round(float(score_s.std()), 2),
        "q10": round(float(score_s.quantile(0.10)), 2),
        "q25": round(float(score_s.quantile(0.25)), 2),
        "q50": round(float(score_s.quantile(0.50)), 2),
        "q75": round(float(score_s.quantile(0.75)), 2),
        "q90": round(float(score_s.quantile(0.90)), 2),
        "min": round(float(score_s.min()), 2),
        "max": round(float(score_s.max()), 2),
        "scores_below_5": int((score_s < 5.0).sum()),
        "scores_below_10": int((score_s < 10.0).sum()),
        "scores_above_90": int((score_s > 90.0).sum()),
        "clipped_floor_0_1": int((score_s <= 0.1).sum()),
        "clipped_ceil_99_9": int((score_s >= 99.9).sum()),
        "mean_diff_vs_prod": round(float(diff_s.mean()), 2),
        "median_diff_vs_prod": round(float(diff_s.median()), 2),
        "p2_p3_corr_before_leverage": round(p2_p3_corr_before, 4),
        "p2_p3_corr_after_leverage": round(p2_p3_corr_after, 4),
    }

    # 3. Leverage Distribution
    lev_s = df["phase7j_leverage"].dropna()
    lev_stats = {
        "mean": round(float(lev_s.mean()), 3),
        "std": round(float(lev_s.std()), 3),
        "median": round(float(lev_s.median()), 3),
        "min": round(float(lev_s.min()), 3),
        "max": round(float(lev_s.max()), 3),
        "pct_at_floor_0_65": round(float((lev_s <= 0.6501).mean() * 100), 2),
        "pct_at_ceil_1_35": round(float((lev_s >= 1.3499).mean() * 100), 2),
    }

    # 4. Subgroup Analysis
    def get_subgroup_stats(sub_df, name):
        sc = sub_df["phase7j_score"].dropna()
        pr = sub_df["contribution_score"].dropna()
        return {
            "name": name,
            "count": len(sc),
            "mean_score": round(float(sc.mean()), 2),
            "median_score": round(float(sc.median()), 2),
            "std_score": round(float(sc.std()), 2),
            "spearman_vs_prod": round(float(sc.corr(pr, method="spearman")), 4),
        }

    subgroups = {
        "inn1": get_subgroup_stats(df[df["innings"] == 1], "1st Innings"),
        "inn2": get_subgroup_stats(df[df["innings"] == 2], "2nd Innings"),
        "powerplay": get_subgroup_stats(df[df["entry_over"] <= 6.0], "Powerplay Entry"),
        "middle": get_subgroup_stats(df[df["entry_over"].between(6.0, 15.0)], "Middle Overs Entry"),
        "death": get_subgroup_stats(df[df["entry_over"] >= 15.0], "Death Overs Entry"),
        "collapse": get_subgroup_stats(df[df["context_zone"] == "COLLAPSE PRESSURE"], "Collapse Entry"),
        "normal": get_subgroup_stats(df[df["context_zone"] == "NORMAL CONTEXT"], "Normal Context Entry"),
        "extreme_crisis": get_subgroup_stats(df[df["context_zone"] == "EXTREME CRISIS"], "Extreme Crisis Entry"),
    }

    # 5. Evaluate Core Scenarios A through N
    core_scenarios_results = []
    for sc in CORE_SCENARIOS_SPEC:
        mock_row = {
            "innings": sc["innings"],
            "entry_over": sc["entry_over"],
            "balls_remaining_entry": sc["balls_rem_entry"],
            "balls_remaining_exit": max(0.0, sc["balls_rem_entry"] - 20.0),
            "wickets_remaining_entry": sc["wkts_rem_entry"],
            "wickets_remaining_exit": sc["wkts_rem_entry"],
            "wicket_resource_change": 0,
            "actual_runs": 80 if "80" in sc["name"] else (5 if "5" in sc["name"] or "Fail" in sc["name"] else 30),
            "balls_faced": 45 if "80" in sc["name"] else (12 if "5" in sc["name"] or "Fail" in sc["name"] else 20),
            "target": sc["target"],
            "required_rr_entry": sc["req_rr"],
            "required_rr_change": 0.0,
            "rr_gap_change": 0.0,
            "target_progress_change": 0.35 if sc["p3"] >= 80 else 0.05,
            "score_perf": sc["p2"],
            "won_match": sc["won_match"],
            "is_dnb": False,
        }
        ctx = compute_phase7j_context_and_leverage(mock_row)
        lev = ctx["leverage"]
        adj_p2 = compute_adjusted_pillar(sc["p2"], lev)
        adj_p3 = compute_adjusted_pillar(sc["p3"], lev)
        score_val = round(float(0.50 * adj_p2 + 0.50 * adj_p3), 1)

        core_scenarios_results.append({
            "id": sc["id"],
            "name": sc["name"],
            "description": sc["description"],
            "p2": sc["p2"],
            "p3": sc["p3"],
            "c_wkt": ctx["c_wkt"],
            "c_chase": ctx["c_chase"],
            "c_eff": ctx["c_eff"],
            "context_zone": ctx["context_zone"],
            "leverage": lev,
            "adjusted_p2": round(adj_p2, 1),
            "adjusted_p3": round(adj_p3, 1),
            "final_score": score_val,
        })

    # 6. Curated 75+ Real IPL Innings Sample
    sample_indices = []

    # 1. Elite openers (1st inn 0/0, 70+ runs)
    sample_indices.extend(df[(df["innings"]==1) & (df["entry_over"]<=0.1) & (df["wickets_remaining_entry"]==10) & (df["actual_runs"]>=70)].head(6).index.tolist())
    # 2. Failed openers (1st inn 0/0, <= 5 runs)
    sample_indices.extend(df[(df["innings"]==1) & (df["entry_over"]<=0.1) & (df["wickets_remaining_entry"]==10) & (df["actual_runs"]<=5) & (df["balls_faced"]<=10)].head(6).index.tolist())
    # 3. Elite chase openers (2nd inn 0/0, target >= 170, 70+ runs)
    sample_indices.extend(df[(df["innings"]==2) & (df["entry_over"]<=0.1) & (df["wickets_remaining_entry"]==10) & (df["target"]>=170) & (df["actual_runs"]>=70)].head(6).index.tolist())
    # 4. Failed chase openers (2nd inn 0/0, target >= 160, <= 5 runs)
    sample_indices.extend(df[(df["innings"]==2) & (df["entry_over"]<=0.1) & (df["wickets_remaining_entry"]==10) & (df["target"]>=160) & (df["actual_runs"]<=5)].head(6).index.tolist())
    # 5. Early collapse rescuers (entry_over <= 5.0, wkts_rem <= 7, runs >= 60)
    sample_indices.extend(df[(df["entry_over"]<=5.0) & (df["wickets_remaining_entry"]<=7) & (df["actual_runs"]>=60)].head(6).index.tolist())
    # 6. Collapse failures (entry_over <= 5.0, wkts_rem <= 7, runs <= 5)
    sample_indices.extend(df[(df["entry_over"]<=5.0) & (df["wickets_remaining_entry"]<=7) & (df["actual_runs"]<=5)].head(6).index.tolist())
    # 7. Middle-order normal batters (entry_over 7-12, wkts_rem 7-8, P1 45-55, runs 30-55)
    sample_indices.extend(df[(df["entry_over"].between(7.0, 12.0)) & (df["wickets_remaining_entry"].isin([7, 8])) & (df["score_context"].between(45, 55)) & (df["actual_runs"].between(30, 55))].head(6).index.tolist())
    # 8. Finishers (entry_over 14-17, runs >= 25, balls <= 18, sr >= 160)
    sample_indices.extend(df[(df["entry_over"].between(14.0, 17.0)) & (df["actual_runs"]>=25) & (df["balls_faced"]<=18) & (df["actual_sr"]>=160)].head(6).index.tolist())
    # 9. Death-over batters (entry_over >= 18.0, runs >= 20, balls <= 12)
    sample_indices.extend(df[(df["entry_over"]>=18.0) & (df["actual_runs"]>=20) & (df["balls_faced"]<=12)].head(6).index.tolist())
    # 10. Low-target chase batters (innings 2, target <= 130, runs >= 40)
    sample_indices.extend(df[(df["innings"]==2) & (df["target"]<=130) & (df["actual_runs"]>=40)].head(6).index.tolist())
    # 11. High-RRR chase batters (innings 2, required_rr_entry >= 12.0, runs >= 30, balls >= 10)
    sample_indices.extend(df[(df["innings"]==2) & (df["required_rr_entry"]>=12.0) & (df["actual_runs"]>=30) & (df["balls_faced"]>=10)].head(6).index.tolist())
    # 12. Impossible chases & tailenders (innings 2, entry_over >= 16.0, required_rr_entry >= 25.0, actual_runs <= 10)
    sample_indices.extend(df[(df["innings"]==2) & (df["entry_over"]>=16.0) & (df["required_rr_entry"]>=25.0) & (df["actual_runs"]<=10)].head(8).index.tolist())
    # 13. Losing heroes (innings 2, won_match == False, actual_runs >= 35, actual_sr >= 180, entry_over >= 10.0)
    sample_indices.extend(df[(df["innings"]==2) & (~df["won_match"]) & (df["actual_runs"]>=35) & (df["actual_sr"]>=180) & (df["entry_over"]>=10.0)].head(8).index.tolist())
    # 14. Winning passengers (innings 2, won_match == True, actual_runs <= 10, balls_faced <= 10, score_perf <= 30)
    sample_indices.extend(df[(df["innings"]==2) & (df["won_match"]) & (df["actual_runs"]<=10) & (df["balls_faced"]<=10) & (df["score_perf"]<=30)].head(6).index.tolist())
    # 15. Key iconic explicit indices
    explicit_keys = [2005, 2371, 1684, 3120, 14, 15, 100, 2011]
    sample_indices.extend(explicit_keys)

    # Deduplicate and keep >= 75
    sample_indices = list(dict.fromkeys(sample_indices))[:80]
    sample_real_df = df.loc[sample_indices]

    real_75_results = []
    for idx, r in sample_real_df.iterrows():
        diff = round(float(r["phase7j_score"]) - float(r["contribution_score"]), 1)
        cricket_interp = ""
        if r["phase7j_score"] >= 85.0:
            cricket_interp = "Match-defining performance amplified by pressure/execution"
        elif r["phase7j_score"] <= 20.0:
            cricket_interp = "Severe failure with amplified negative deviation under pressure"
        elif diff >= 5.0:
            cricket_interp = "Significant merit gain: elevated by crisis context / death execution"
        elif diff <= -5.0:
            cricket_interp = "Removed unearned P1 cushion from passive/low performance"
        else:
            cricket_interp = "Balanced stable contribution tracking production baseline"

        real_75_results.append({
            "index": int(idx),
            "match_id": int(r["match_id"]),
            "player": str(r["player"]),
            "innings": int(r["innings"]),
            "entry_over": float(r["entry_over"]),
            "wickets_at_entry": int(10 - float(r["wickets_remaining_entry"])),
            "target": round(float(r["target"]), 1) if r["innings"] == 2 else 0.0,
            "RRR_at_entry": round(float(r["required_rr_entry"]), 1) if r["innings"] == 2 else 0.0,
            "runs": int(r["actual_runs"]),
            "balls": int(r["balls_faced"]),
            "SR": round(float(r["actual_sr"]), 1),
            "P2": round(float(r["phase7j_p2"]), 1),
            "P3": round(float(r["phase7j_p3"]), 1),
            "c_wkt": float(r["c_wkt"]),
            "c_chase": float(r["c_chase"]),
            "c_eff": float(r["c_eff"]),
            "context_zone": str(r["context_zone"]),
            "leverage": float(r["phase7j_leverage"]),
            "adjusted_P2": float(r["phase7j_adj_p2"]),
            "adjusted_P3": float(r["phase7j_adj_p3"]),
            "final_contribution": float(r["phase7j_score"]),
            "production_score": round(float(r["contribution_score"]), 1),
            "difference": diff,
            "cricket_interpretation": cricket_interp,
        })

    # 7. Non-Negotiable Invariance Audits
    # A. DNB remains NULL
    dnb_test = compute_phase7j_contribution({"is_dnb": True})
    dnb_null_preserved = (dnb_test["contribution_score"] is None)

    # B. Match outcome invariance: changing won_match True <-> False produces zero score change
    test_row_win = df.iloc[100].to_dict()
    test_row_win["won_match"] = True
    test_row_loss = df.iloc[100].to_dict()
    test_row_loss["won_match"] = False
    sc_win = compute_phase7j_contribution(test_row_win)["contribution_score"]
    sc_loss = compute_phase7j_contribution(test_row_loss)["contribution_score"]
    outcome_invariant = (sc_win == sc_loss)

    # C. Player identity invariance: changing player name produces zero context change
    test_row_p1 = df.iloc[100].to_dict()
    test_row_p1["player"] = "Player A"
    test_row_p2 = df.iloc[100].to_dict()
    test_row_p2["player"] = "Player B"
    ctx_p1 = compute_phase7j_context_and_leverage(test_row_p1)["leverage"]
    ctx_p2 = compute_phase7j_context_and_leverage(test_row_p2)["leverage"]
    player_invariant = (ctx_p1 == ctx_p2)

    # D. 1st innings feasibility invariance
    inn1_rows = df[df["innings"] == 1].head(100)
    inn1_invariant = True
    for _, r in inn1_rows.iterrows():
        p3_base = map_raw_to_p3_score(compute_dampened_p3_raw(r, "baseline"))
        p3_hyb = map_raw_to_p3_score(compute_dampened_p3_raw(r, "model_e"))
        if abs(p3_base - p3_hyb) > 1e-4:
            inn1_invariant = False
            break

    invariance_results = {
        "dnb_null_preserved": dnb_null_preserved,
        "outcome_invariance": outcome_invariant,
        "player_identity_invariance": player_invariant,
        "inn1_feasibility_invariance": inn1_invariant,
        "p3_issue_01_reduced": (pop_stats["scores_below_5"] < 25),
    }

    results = {
        "status": "COMPLETED",
        "population_statistics": pop_stats,
        "leverage_statistics": lev_stats,
        "subgroup_statistics": subgroups,
        "core_scenarios": core_scenarios_results,
        "real_75_sample": real_75_results,
        "invariance_audits": invariance_results,
    }

    return results


def main():
    print("=" * 80)
    print("PHASE 7J: HOLISTIC CONTEXT-AS-LEVERAGE INTEGRATION SIMULATION")
    print("=" * 80)

    results = run_phase7j_simulation()

    out_path = Path("models/contribution/phase7/phase7j_holistic_integration_validation.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\n[Artifact Generated] Successfully wrote validation artifact to {out_path}")
    print("=" * 80)


if __name__ == "__main__":
    main()
