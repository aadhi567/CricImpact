"""
Script to evaluate isolated P3 correction alternatives across 19,111 innings.
Analyzes each correction independently to measure:
- Number of affected innings
- Average shift in P3 and Contribution
- Key cases (Russell, Dhawan, Smith)
- Impact on P2/P3 correlation and overall distribution
- Outcome leakage verification
"""
import sys
import json
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.phase7g_simulation import compute_corrected_p3, compute_phase7g_contribution
from src.phase7f_leverage_simulation import leverage_model_a_linear


def main():
    df = pd.read_csv("data/processed/batter_match_contributions.csv", low_memory=False)
    p7d_scores = df["contribution_score"].dropna()

    # Baseline Phase 7F with uncorrected P3
    p7f_scores = []
    p7f_p3s = []
    for _, r in df.iterrows():
        res = compute_phase7g_contribution(r, death_rrr_mode="baseline", coattail_mode="baseline", low_target_mode="baseline")
        p7f_scores.append(res["contribution_score"])
        p7f_p3s.append(res["p3_score"])
    df["p7f_score"] = p7f_scores
    df["p7f_p3"] = p7f_p3s

    p2_ser = df["score_perf"].dropna()

    print("=== ISOLATED ISSUE 1: DEATH-OVER RRR BLOWOUT ===")
    d_modes = ["baseline", "mode_1a_sr_capped", "mode_1b_continuous", "mode_1c_prog_reweight"]
    d_results = {}
    for m in d_modes:
        p3_list = []
        c_list = []
        for _, r in df.iterrows():
            res = compute_phase7g_contribution(r, death_rrr_mode=m, coattail_mode="baseline", low_target_mode="baseline")
            p3_list.append(res["p3_score"])
            c_list.append(res["contribution_score"])
        
        p3_s = pd.Series(p3_list).dropna()
        c_s = pd.Series(c_list).dropna()
        
        diff = c_s - df["p7f_score"].dropna()
        affected = (diff.abs() > 0.1).sum()
        
        # Test Russell M1178410
        r_russell = df[(df["player"] == "AD Russell") & (df["match_id"] == 1178410)].iloc[0]
        res_russell = compute_phase7g_contribution(r_russell, death_rrr_mode=m, coattail_mode="baseline", low_target_mode="baseline")

        d_results[m] = {
            "mean": round(float(c_s.mean()), 2),
            "std": round(float(c_s.std()), 2),
            "affected_count": int(affected),
            "mean_shift_on_affected": round(float(diff[diff.abs() > 0.1].mean()) if affected > 0 else 0.0, 2),
            "p2_p3_corr": round(float(p2_ser.corr(p3_s)), 4),
            "russell_p3": res_russell["p3_score"],
            "russell_contrib": res_russell["contribution_score"],
        }
        print(f"{m:22s}: Affected={affected:4d}, Mean={d_results[m]['mean']}, P2/P3 Corr={d_results[m]['p2_p3_corr']}, Russell P3={res_russell['p3_score']}, Score={res_russell['contribution_score']}")

    print("\n=== ISOLATED ISSUE 2: PARTNER COATTAIL EFFECT ===")
    c_modes = ["baseline", "mode_2a_share_dampening", "mode_2b_escalated_diff", "mode_2c_hybrid"]
    c_results = {}
    for m in c_modes:
        p3_list = []
        c_list = []
        for _, r in df.iterrows():
            res = compute_phase7g_contribution(r, death_rrr_mode="baseline", coattail_mode=m, low_target_mode="baseline")
            p3_list.append(res["p3_score"])
            c_list.append(res["contribution_score"])
        
        p3_s = pd.Series(p3_list).dropna()
        c_s = pd.Series(c_list).dropna()
        
        diff = c_s - df["p7f_score"].dropna()
        affected = (diff.abs() > 0.1).sum()
        
        # Test Dhawan M1082627
        r_dhawan = df[(df["player"] == "S Dhawan") & (df["match_id"] == 1082627)].iloc[0]
        res_dhawan = compute_phase7g_contribution(r_dhawan, death_rrr_mode="baseline", coattail_mode=m, low_target_mode="baseline")

        c_results[m] = {
            "mean": round(float(c_s.mean()), 2),
            "std": round(float(c_s.std()), 2),
            "affected_count": int(affected),
            "mean_shift_on_affected": round(float(diff[diff.abs() > 0.1].mean()) if affected > 0 else 0.0, 2),
            "p2_p3_corr": round(float(p2_ser.corr(p3_s)), 4),
            "dhawan_p3": res_dhawan["p3_score"],
            "dhawan_contrib": res_dhawan["contribution_score"],
        }
        print(f"{m:24s}: Affected={affected:4d}, Mean={c_results[m]['mean']}, P2/P3 Corr={c_results[m]['p2_p3_corr']}, Dhawan P3={res_dhawan['p3_score']}, Score={res_dhawan['contribution_score']}")

    print("\n=== ISOLATED ISSUE 3: LOW-TARGET CHASE ARTIFACT ===")
    l_modes = ["baseline", "mode_3a_exec_gate", "mode_3b_target_discount", "mode_3c_pace_cap"]
    l_results = {}
    for m in l_modes:
        p3_list = []
        c_list = []
        for _, r in df.iterrows():
            res = compute_phase7g_contribution(r, death_rrr_mode="baseline", coattail_mode="baseline", low_target_mode=m)
            p3_list.append(res["p3_score"])
            c_list.append(res["contribution_score"])
        
        p3_s = pd.Series(p3_list).dropna()
        c_s = pd.Series(c_list).dropna()
        
        diff = c_s - df["p7f_score"].dropna()
        affected = (diff.abs() > 0.1).sum()
        
        # Test Smith M1082645
        r_smith = df[(df["player"] == "SPD Smith") & (df["match_id"] == 1082645)].iloc[0]
        res_smith = compute_phase7g_contribution(r_smith, death_rrr_mode="baseline", coattail_mode="baseline", low_target_mode=m)

        l_results[m] = {
            "mean": round(float(c_s.mean()), 2),
            "std": round(float(c_s.std()), 2),
            "affected_count": int(affected),
            "mean_shift_on_affected": round(float(diff[diff.abs() > 0.1].mean()) if affected > 0 else 0.0, 2),
            "p2_p3_corr": round(float(p2_ser.corr(p3_s)), 4),
            "smith_p3": res_smith["p3_score"],
            "smith_contrib": res_smith["contribution_score"],
        }
        print(f"{m:24s}: Affected={affected:4d}, Mean={l_results[m]['mean']}, P2/P3 Corr={l_results[m]['p2_p3_corr']}, Smith P3={res_smith['p3_score']}, Score={res_smith['contribution_score']}")

    # Check Outcome Leakage
    print("\n=== CHECKING OUTCOME LEAKAGE ===")
    c1_scores = []
    for _, r in df.iterrows():
        res = compute_phase7g_contribution(r, death_rrr_mode="mode_1a_sr_capped", coattail_mode="mode_2a_share_dampening", low_target_mode="mode_3a_exec_gate")
        c1_scores.append(res["contribution_score"])
    df["c1_score"] = c1_scores

    valid_df = df.dropna(subset=["c1_score", "won_match"]).copy()
    valid_df["won_match_int"] = valid_df["won_match"].astype(int)
    
    # Outcome leakage test: verify no match outcome columns are used in inputs
    import inspect
    from src.phase7g_simulation import compute_corrected_p3
    src_lines = inspect.getsource(compute_corrected_p3)
    forbidden_terms = ["won_match", "match_winner", "margin", "result", "winner"]
    leakage_detected = any(f'"{term}"' in src_lines or f"'{term}'" in src_lines for term in forbidden_terms)
    print(f"Code-level outcome leakage detected in compute_corrected_p3: {leakage_detected}")

    # Save isolated results
    isolated_out = {
        "issue_1_death_rrr": d_results,
        "issue_2_coattail": c_results,
        "issue_3_low_target": l_results,
        "outcome_leakage_detected": leakage_detected,
    }
    with open("models/contribution/phase7/phase7g_isolated_analysis.json", "w", encoding="utf-8") as f:
        json.dump(isolated_out, f, indent=2)
    print("Saved isolated analysis to models/contribution/phase7/phase7g_isolated_analysis.json")


if __name__ == "__main__":
    main()
