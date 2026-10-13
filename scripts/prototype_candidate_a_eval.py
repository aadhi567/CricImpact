"""
Evaluation script for Candidate A: Model T Attribution for Trajectory Deviation Change.
Controlled prototype evaluating:
1. Reconciled units, baselines, and time windows.
2. Impact on Shahrukh Khan, RA Tripathi, Sai Sudharsan, and full cohorts.
3. Verification of zero double-counting.
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from app.services.data_service import data_service
from src.contribution_framework import (
    compute_attributable_team_state_efs,
    compute_dampened_p3_raw,
    map_raw_to_p3_score,
    apply_p3_state_preservation_floor,
    apply_p3_score_preservation_floor,
    compute_production_contribution,
    P3_WICKET_ATTR_COLLAPSE_GAMMA,
    P3_WICKET_ATTR_INDEPENDENT_GAMMA,
    P3_WICKET_ATTR_STAGNATION_GAMMA,
    P3_WICKET_ATTR_CAUSED_GAMMA,
)


def compute_attributable_trajectory_deviation(
    row: pd.Series,
    gamma_independent: float = P3_WICKET_ATTR_INDEPENDENT_GAMMA,
    gamma_collapse: float = P3_WICKET_ATTR_COLLAPSE_GAMMA,
    gamma_stagnation: float = P3_WICKET_ATTR_STAGNATION_GAMMA,
    gamma_caused: float = P3_WICKET_ATTR_CAUSED_GAMMA,
):
    """
    Candidate A: Consistent Model T attribution applied to trajectory_deviation_change.
    """
    innings = int(row.get("innings", 1))
    if innings != 1:
        return float(row.get("trajectory_deviation_change", 0.0)), 1.0, "CHASE"

    traj_chg = row.get("trajectory_deviation_change")
    if traj_chg is None or pd.isna(traj_chg):
        return np.nan, 1.0, "MISSING"

    traj_chg = float(traj_chg)
    runs = float(row.get("actual_runs", 0.0))
    exp_runs = float(row.get("expected_runs", runs))
    delta_r = runs - exp_runs
    ext_drag_traj = traj_chg - delta_r

    if ext_drag_traj >= 0.0:
        return traj_chg, 1.0, "POSITIVE_DRAG"

    wkts_lost = row.get("wickets_lost_during_stay")
    if wkts_lost is None or pd.isna(wkts_lost):
        return traj_chg, 1.0, "UNKNOWN_WICKETS"

    wkts_lost = int(wkts_lost)
    if wkts_lost == 0:
        return traj_chg, 1.0, "NO_WICKETS"

    is_dismissed = (str(row.get("dismissal_status", "out")).lower() == "out")
    partner_wkts = max(0, wkts_lost - 1) if is_dismissed else wkts_lost
    if partner_wkts == 0:
        return traj_chg, 1.0, "NO_PARTNER_WICKETS"

    balls = int(row.get("balls_faced", 0))
    # Anti-free-rider gate
    if (balls <= 1 and runs == 0.0) or (balls < 6 and runs < 10.0):
        return traj_chg, 1.0, "MINIMAL_STAY"

    dots_pct = float(row.get("dot_ball_percentage", 30.0))
    sr_ratio = float(row.get("sr_performance_ratio", 1.0))
    act_sr = float(row.get("actual_sr", (runs / max(1, balls)) * 100.0))

    if (dots_pct >= 50.0 and sr_ratio < 1.15) or (act_sr < 100.0 and balls >= 10) or delta_r <= 0.0:
        gamma = gamma_caused
        cat = "CATEGORY_A"
    elif partner_wkts >= 3:
        gamma = gamma_collapse
        cat = "CATEGORY_C"
    elif (sr_ratio >= 1.25 or act_sr >= 150.0) and dots_pct < 45.0 and delta_r > 0.0:
        gamma = gamma_independent
        cat = "CATEGORY_B"
    elif partner_wkts >= 2:
        gamma = gamma_collapse
        cat = "CATEGORY_C"
    else:
        gamma = gamma_stagnation
        cat = "CATEGORY_C"

    attr_traj = delta_r + gamma * ext_drag_traj
    return float(attr_traj), float(gamma), str(cat)


def compute_candidate_p3(row: pd.Series, enable_candidate_a: bool = False):
    """
    Computes P3 raw and mapped score with/without Candidate A trajectory attribution.
    """
    innings = int(row.get("innings", 1))
    if innings > 2:
        return np.nan, np.nan

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

    if innings == 1:
        efs_chg = row.get("expected_final_change")
        if pd.notnull(efs_chg):
            # EFS always has Model T attribution in Phase 7U
            attr_efs, _, _ = compute_attributable_team_state_efs(row)
            z_efs = float(attr_efs) / 12.0

            traj_val = float(row.get("trajectory_deviation_change", 0.0))
            if enable_candidate_a:
                attr_traj, _, _ = compute_attributable_trajectory_deviation(row)
                traj_val = attr_traj

            traj_dev_chg = traj_val / 10.0
            window_rr = float(row.get("window_team_rr", 7.5))
            team_rr_entry = float(row.get("team_rr_entry", 7.5))
            accel = np.clip((window_rr - team_rr_entry) / 3.0, -3.0, 3.0)
            raw = 0.50 * z_efs + 0.25 * traj_dev_chg + 0.25 * accel + s_res
            raw = apply_p3_state_preservation_floor(raw, row)
            p3 = map_raw_to_p3_score(raw)
            p3 = apply_p3_score_preservation_floor(p3, row)
            return raw, p3

    # If 2nd innings or unmodelled, same as standard
    raw = compute_dampened_p3_raw(row, apply_attribution=True, apply_preservation=True)
    p3 = map_raw_to_p3_score(raw)
    p3 = apply_p3_score_preservation_floor(p3, row)
    return raw, p3


def compute_candidate_contribution(row: pd.Series, enable_candidate_a: bool = False):
    """
    Computes full contribution score (P1, P2, P3) under Candidate A.
    """
    raw_p3, cand_p3 = compute_candidate_p3(row, enable_candidate_a=enable_candidate_a)
    
    # We construct a mock row with the candidate P3 to run through compute_production_contribution
    row_copy = row.copy()
    row_copy["dampened_p3"] = cand_p3
    res = compute_production_contribution(row_copy)
    return res, raw_p3, cand_p3


if __name__ == "__main__":
    df = data_service.get_contributions_df("ipl")
    print(f"Loaded {len(df)} IPL innings.")

    # 1. Shahrukh Khan
    srk = df[(df["match_id"].astype(str) == "1254065") & (df["player"] == "M Shahrukh Khan")].iloc[0]
    res_orig, raw_orig, p3_orig = compute_candidate_contribution(srk, enable_candidate_a=False)
    res_cand, raw_cand, p3_cand = compute_candidate_contribution(srk, enable_candidate_a=True)
    print("\n--- 1. M Shahrukh Khan (1254065: 47 off 36, 19/4 -> 101/8) ---")
    print(f"Orig: Raw P3={raw_orig:.4f}, P3={p3_orig:.1f}, Adj P3={res_orig['adjusted_p3']:.1f}, Final={res_orig['final_contribution_score']:.1f}")
    print(f"Cand: Raw P3={raw_cand:.4f}, P3={p3_cand:.1f}, Adj P3={res_cand['adjusted_p3']:.1f}, Final={res_cand['final_contribution_score']:.1f}")

    # 2. Sai Sudharsan
    sai = df[(df["match_id"].astype(str) == "1359536") & (df["player"] == "B Sai Sudharsan")].iloc[0]
    res_orig, raw_orig, p3_orig = compute_candidate_contribution(sai, enable_candidate_a=False)
    res_cand, raw_cand, p3_cand = compute_candidate_contribution(sai, enable_candidate_a=True)
    print("\n--- 2. B Sai Sudharsan (1359536: 47 off 36, 0/1 -> 133/2) ---")
    print(f"Orig: Raw P3={raw_orig:.4f}, P3={p3_orig:.1f}, Adj P3={res_orig['adjusted_p3']:.1f}, Final={res_orig['final_contribution_score']:.1f}")
    print(f"Cand: Raw P3={raw_cand:.4f}, P3={p3_cand:.1f}, Adj P3={res_cand['adjusted_p3']:.1f}, Final={res_cand['final_contribution_score']:.1f}")

    # 3. RA Tripathi Cases
    tripathi_cases = [1359484, 1254098, 1136613, 1082603, 1304111]
    print("\n--- 3. RA Tripathi Benchmark Innings ---")
    for mid in tripathi_cases:
        matches = df[(df["match_id"].astype(str) == str(mid)) & (df["player"] == "RA Tripathi")]
        if not matches.empty:
            t_row = matches.iloc[0]
            res_o, raw_o, p3_o = compute_candidate_contribution(t_row, enable_candidate_a=False)
            res_c, raw_c, p3_c = compute_candidate_contribution(t_row, enable_candidate_a=True)
            print(f"Match {mid} ({t_row['actual_runs']} off {t_row['balls_faced']}):")
            print(f"  Orig: Raw P3={raw_o:.3f}, P3={p3_o:.1f}, Final={res_o['final_contribution_score']:.1f}")
            print(f"  Cand: Raw P3={raw_c:.3f}, P3={p3_c:.1f}, Final={res_c['final_contribution_score']:.1f}")

    # 4. Cohort Analysis across all 1st Innings

    print("\n--- 4. Full Cohort Analysis across 1st Innings ---")
    inn1_df = df[df["innings"] == 1].copy()

    # Pre-calculate candidate values for all 1st innings
    results = []
    for idx, row in inn1_df.iterrows():
        raw_o, p3_o = compute_candidate_p3(row, enable_candidate_a=False)
        raw_c, p3_c = compute_candidate_p3(row, enable_candidate_a=True)
        results.append({
            "idx": idx,
            "match_id": row["match_id"],
            "player": row["player"],
            "season": row["season"],
            "actual_runs": row["actual_runs"],
            "balls_faced": row["balls_faced"],
            "actual_sr": row["actual_sr"],
            "wickets_lost_during_stay": row.get("wickets_lost_during_stay", 0),
            "dot_ball_percentage": row.get("dot_ball_percentage", 0),
            "expected_runs": row.get("expected_runs", row["actual_runs"]),
            "expected_final_change": row.get("expected_final_change", 0),
            "trajectory_deviation_change": row.get("trajectory_deviation_change", 0),
            "raw_p3_orig": raw_o,
            "raw_p3_cand": raw_c,
            "p3_orig": p3_o,
            "p3_cand": p3_c,
            "delta_p3": p3_c - p3_o,
        })
    res_df = pd.DataFrame(results)

    total_1st = len(res_df)
    changed = res_df[res_df["delta_p3"].abs() > 0.05]
    print(f"Total 1st innings: {total_1st}")
    print(f"Innings changed (> 0.05 P3 delta): {len(changed)} ({len(changed)/total_1st*100:.1f}%)")
    print(f"Innings unchanged (<= 0.05 P3 delta): {total_1st - len(changed)} ({(total_1st - len(changed))/total_1st*100:.1f}%)")

    # Cohort A: Collapse Resisters (wkts >= 3, runs >= 30, SR >= 120, delta_r > 0)
    cohort_heroes = res_df[
        (res_df["wickets_lost_during_stay"] >= 3)
        & (res_df["actual_runs"] >= 30)
        & (res_df["actual_sr"] >= 120)
        & (res_df["actual_runs"] > res_df["expected_runs"])
        & (res_df["trajectory_deviation_change"] < 0)
    ]
    print(f"\nCohort A: Collapse Resisters with Negative Trajectory (n={len(cohort_heroes)})")
    print(f"  Mean P3 Orig: {cohort_heroes['p3_orig'].mean():.1f} -> Cand: {cohort_heroes['p3_cand'].mean():.1f} (Avg Delta: +{cohort_heroes['delta_p3'].mean():.1f})")
    print("  Top 5 affected:")
    for _, r in cohort_heroes.sort_values(by="delta_p3", ascending=False).head(5).iterrows():
        print(f"    {r['player']} ({r['season']}, M{r['match_id']}): {r['actual_runs']} off {r['balls_faced']}b ({r['wickets_lost_during_stay']} wkts), P3: {r['p3_orig']:.1f} -> {r['p3_cand']:.1f} (+{r['delta_p3']:.1f})")

    # Cohort B: Slow Crawlers (SR < 100 on 15+ balls, delta_r <= 0)
    cohort_slow = res_df[
        (res_df["balls_faced"] >= 15)
        & (res_df["actual_sr"] < 100)
        & (res_df["actual_runs"] <= res_df["expected_runs"])
    ]
    print(f"\nCohort B: Slow Crawlers (n={len(cohort_slow)})")
    print(f"  Mean P3 Orig: {cohort_slow['p3_orig'].mean():.1f} -> Cand: {cohort_slow['p3_cand'].mean():.1f} (Avg Delta: {cohort_slow['delta_p3'].mean():.2f})")
    print(f"  Max change in slow crawlers: {cohort_slow['delta_p3'].abs().max():.3f}")

    # Cohort C: Pressure Creators (dots% >= 50%, delta_r <= 0, wkts >= 2)
    cohort_pressure = res_df[
        (res_df["dot_ball_percentage"] >= 50.0)
        & (res_df["actual_runs"] <= res_df["expected_runs"])
        & (res_df["wickets_lost_during_stay"] >= 2)
    ]
    print(f"\nCohort C: Pressure Creators (n={len(cohort_pressure)})")
    print(f"  Mean P3 Orig: {cohort_pressure['p3_orig'].mean():.1f} -> Cand: {cohort_pressure['p3_cand'].mean():.1f} (Avg Delta: {cohort_pressure['delta_p3'].mean():.2f})")
    print(f"  Max change in pressure creators: {cohort_pressure['delta_p3'].abs().max():.3f}")

    # Cohort D: Stable Platform (traj_dev > 0, delta_r > 0, wkts <= 2)
    cohort_stable = res_df[
        (res_df["trajectory_deviation_change"] > 0)
        & (res_df["actual_runs"] > res_df["expected_runs"])
        & (res_df["wickets_lost_during_stay"] <= 2)
    ]
    print(f"\nCohort D: Stable Platform Builders (n={len(cohort_stable)})")
    print(f"  Mean P3 Orig: {cohort_stable['p3_orig'].mean():.1f} -> Cand: {cohort_stable['p3_cand'].mean():.1f} (Avg Delta: {cohort_stable['delta_p3'].mean():.2f})")
    print(f"  Max change in stable platform: {cohort_stable['delta_p3'].abs().max():.3f}")

