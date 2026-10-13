"""
Inspect and audit P3 across the full dataset of 19,111 innings.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.phase7c_rebalance import compute_phase7c_p3, PHASE7C_P3_PARAMS
from src.contribution_framework import normalize_pillar_score


def decompose_p3(row):
    """Decompose P3 into its 4 sub-components exactly as computed in compute_phase7c_p3."""
    innings = int(row.get("innings", 1))
    if innings > 2:
        return None

    actual_runs = float(row.get("actual_runs", 0))
    balls_faced = float(row.get("balls_faced", 0))
    actual_sr = float(row.get("actual_sr", 0.0))

    # 1. Macro Trajectory & Pressure Transformation (45%)
    if innings == 1:
        efs_chg = row.get("expected_final_change")
        if pd.notnull(efs_chg):
            z_efs = float(efs_chg) / 12.0
            traj_dev_chg = float(row.get("trajectory_deviation_change", 0.0)) / 10.0
            window_rr = float(row.get("window_team_rr", 7.5))
            team_rr_entry = float(row.get("team_rr_entry", 7.5))
            accel = np.clip((window_rr - team_rr_entry) / 3.0, -3.0, 3.0)
            z_macro = 0.50 * z_efs + 0.25 * traj_dev_chg + 0.25 * accel
        else:
            window_rr = float(row.get("window_team_rr", 7.5))
            team_rr_entry = float(row.get("team_rr_entry", 7.5))
            accel = np.clip((window_rr - team_rr_entry) / 3.0, -3.0, 3.0)
            runs_added = float(row.get("team_runs_added", actual_runs))
            overs_spent = max(0.2, float(row.get("overs_spent", 1.0)))
            z_macro = 0.60 * accel + 0.40 * ((runs_added - overs_spent * 8.0) / 10.0)
    else:
        rrr_chg = np.clip(float(row.get("required_rr_change", 0.0)), -12.0, 12.0)
        t_prog = float(row.get("target_progress_change", 0.0))
        z_rrr = rrr_chg / 3.0
        z_prog = (t_prog - 0.15) / 0.15
        z_macro = 0.65 * z_rrr + 0.35 * z_prog

    # 2. Partnership & Non-Striker Context (30%)
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
    z_partner = 0.50 * z_share + 0.35 * z_sr_diff + synergy_bonus

    # 3. Collapse Recovery & Stabilization Context (15%)
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
    z_collapse = z_stab

    # 4. Resource Trade-Off & Wicket Equity (10%)
    balls_rem_exit = float(row.get("balls_remaining_exit", 0))
    wkts_rem_exit = float(row.get("wickets_remaining_exit", 5))
    wkt_res_chg = float(row.get("wicket_resource_change", 0))

    if wkt_res_chg < 0:
        base_cost = (balls_rem_exit / 120.0) * (10.0 / max(1.0, wkts_rem_exit + 2.0)) * 0.5
        offset = min(base_cost * 0.7, max(0.0, actual_runs - 15.0) * 0.02)
        s_res = -(base_cost - offset)
    else:
        s_res = 0.15 * (wkts_rem_exit / 10.0)
    z_wicket_equity = s_res

    p3_raw = 0.45 * z_macro + 0.30 * z_partner + 0.15 * z_collapse + 0.10 * z_wicket_equity
    z3 = (p3_raw - PHASE7C_P3_PARAMS["p3_mean"]) / PHASE7C_P3_PARAMS["p3_std"]
    score_p3 = normalize_pillar_score(z3, k=PHASE7C_P3_PARAMS["p3_scale"])

    return {
        "z_macro": round(float(z_macro), 4),
        "z_partner": round(float(z_partner), 4),
        "z_collapse": round(float(z_collapse), 4),
        "z_wicket_equity": round(float(z_wicket_equity), 4),
        "p3_raw": round(float(p3_raw), 4),
        "z3": round(float(z3), 4),
        "score_p3": round(float(score_p3), 1),
        "partner_runs": round(float(p_runs), 1),
        "partner_balls": int(partner_balls),
        "partner_sr": round(float(partner_sr), 1),
        "is_carrying": is_carrying,
        "is_mutual": is_mutual,
        "synergy_bonus": synergy_bonus,
    }


def main():
    print("Loading datasets...")
    df_contrib = pd.read_csv("data/processed/batter_match_contributions.csv", low_memory=False)
    print(f"Loaded {len(df_contrib):,} innings.")

    # Filter standard innings
    df_std = df_contrib[df_contrib["innings"] <= 2].copy()
    print(f"Standard innings: {len(df_std):,}")

    # Compute correlations
    corrs = {
        "corr_p2_p3": float(df_std["score_perf"].corr(df_std["score_state"])),
        "corr_runs_p3": float(df_std["actual_runs"].corr(df_std["score_state"])),
        "corr_sr_p3": float(df_std["actual_sr"].corr(df_std["score_state"])),
        "corr_share_p3": float(df_std["batter_partnership_share"].corr(df_std["score_state"])),
        "corr_p1_p3": float(df_std["score_context"].corr(df_std["score_state"])),
        "corr_p3_won": float(df_std["won_match"].corr(df_std["score_state"])),
        "corr_p2_won": float(df_std["won_match"].corr(df_std["score_perf"])),
        "corr_contrib_won": float(df_std["won_match"].corr(df_std["contribution_score"])),
    }
    # For innings 1: corr with EFS change
    inn1 = df_std[(df_std["innings"] == 1) & df_std["expected_final_change"].notnull()]
    corrs["corr_efs_chg_p3_inn1"] = float(inn1["expected_final_change"].corr(inn1["score_state"]))

    # For innings 2: corr with RRR change
    inn2 = df_std[(df_std["innings"] == 2) & df_std["required_rr_change"].notnull()]
    corrs["corr_rrr_chg_p3_inn2"] = float(inn2["required_rr_change"].corr(inn2["score_state"]))

    print("\n--- Correlation Analysis ---")
    for k, v in corrs.items():
        print(f"  {k}: {v:.4f}")

    # P3 distribution
    print("\n--- P3 Score Distribution ---")
    print(df_std["score_state"].describe().round(2))


if __name__ == "__main__":
    main()
