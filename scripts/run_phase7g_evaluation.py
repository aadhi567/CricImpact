"""
Phase 7G comprehensive evaluation script:
Simulates all P3 candidate corrections across 19,111 innings and the 18 required stress tests.
"""
import sys
import json
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.phase7g_simulation import compute_corrected_p3, compute_phase7g_contribution


def load_dataset():
    df = pd.read_csv("data/processed/batter_match_contributions.csv", low_memory=False)
    return df


def evaluate_alternatives(df):
    print("=== 1. Evaluating P3 Correction Alternatives across 19,111 Innings ===")
    
    configs = {
        "Phase 7D Production (25/35/40)": None,
        "Phase 7F Baseline + Leverage (Uncorrected P3)": ("baseline", "baseline", "baseline"),
        "Candidate 1 (Mode 1A + 2A + 3A)": ("mode_1a_sr_capped", "mode_2a_share_dampening", "mode_3a_exec_gate"),
        "Candidate 2 (Mode 1B + 2C + 3B)": ("mode_1b_continuous", "mode_2c_hybrid", "mode_3b_target_discount"),
        "Candidate 3 (Mode 1C + 2B + 3C)": ("mode_1c_prog_reweight", "mode_2b_escalated_diff", "mode_3c_pace_cap"),
    }

    results = {}
    p7d_scores = df["contribution_score"].dropna()

    for name, cfg in configs.items():
        if cfg is None:
            # Phase 7D production
            results[name] = {
                "mean": round(float(p7d_scores.mean()), 2),
                "median": round(float(p7d_scores.median()), 2),
                "std": round(float(p7d_scores.std()), 2),
                "q10": round(float(p7d_scores.quantile(0.10)), 1),
                "q90": round(float(p7d_scores.quantile(0.90)), 1),
                "min": round(float(p7d_scores.min()), 1),
                "max": round(float(p7d_scores.max()), 1),
                "corr_with_p7d": 1.0000,
                "corr_with_p7f": None,
                "p2_p3_corr": round(float(df["score_perf"].corr(df["score_state"])), 4),
            }
        else:
            d_mode, c_mode, l_mode = cfg
            scores = []
            p3s = []
            p2s = []
            for _, r in df.iterrows():
                res = compute_phase7g_contribution(r, death_rrr_mode=d_mode, coattail_mode=c_mode, low_target_mode=l_mode)
                scores.append(res["contribution_score"])
                p3s.append(res["p3_score"])
                p2s.append(res["p2_score"])
            
            s_ser = pd.Series(scores, dtype=float).dropna()
            p3_ser = pd.Series(p3s, dtype=float).dropna()
            p2_ser = pd.Series(p2s, dtype=float).dropna()
            
            corr_p7d = float(s_ser.corr(p7d_scores))
            p2_p3_corr = float(p2_ser.corr(p3_ser))
            
            results[name] = {
                "mean": round(float(s_ser.mean()), 2),
                "median": round(float(s_ser.median()), 2),
                "std": round(float(s_ser.std()), 2),
                "q10": round(float(s_ser.quantile(0.10)), 1),
                "q90": round(float(s_ser.quantile(0.90)), 1),
                "min": round(float(s_ser.min()), 1),
                "max": round(float(s_ser.max()), 1),
                "corr_with_p7d": round(corr_p7d, 4),
                "p2_p3_corr": round(p2_p3_corr, 4),
                "series": s_ser,
            }

    # Inter-candidate correlations with Phase 7F baseline
    base_ser = results["Phase 7F Baseline + Leverage (Uncorrected P3)"]["series"]
    for name in ["Candidate 1 (Mode 1A + 2A + 3A)", "Candidate 2 (Mode 1B + 2C + 3B)", "Candidate 3 (Mode 1C + 2B + 3C)"]:
        results[name]["corr_with_p7f"] = round(float(results[name]["series"].corr(base_ser)), 4)
        del results[name]["series"]
    del results["Phase 7F Baseline + Leverage (Uncorrected P3)"]["series"]

    return results


def test_specific_failure_cases(df):
    print("\n=== 2. Testing Specific Known Issue Cases ===")
    
    # Issue 1: Russell (M1178410)
    r_russell = df[(df["player"] == "AD Russell") & (df["match_id"] == 1178410)].iloc[0]
    # Issue 2: Dhawan (M1082627)
    r_dhawan = df[(df["player"] == "S Dhawan") & (df["match_id"] == 1082627)].iloc[0]
    # Issue 3: Smith (M1082645)
    r_smith = df[(df["player"] == "SPD Smith") & (df["match_id"] == 1082645)].iloc[0]

    test_players = [
        ("Issue 1: Death RRR Blowout", r_russell),
        ("Issue 2: Partner Coattail", r_dhawan),
        ("Issue 3: Low-Target Chase", r_smith),
    ]

    modes = {
        "Phase 7D (25/35/40)": None,
        "Phase 7F (Leverage + Baseline P3)": ("baseline", "baseline", "baseline"),
        "Candidate 1 (1A + 2A + 3A)": ("mode_1a_sr_capped", "mode_2a_share_dampening", "mode_3a_exec_gate"),
        "Candidate 2 (1B + 2C + 3B)": ("mode_1b_continuous", "mode_2c_hybrid", "mode_3b_target_discount"),
        "Candidate 3 (1C + 2B + 3C)": ("mode_1c_prog_reweight", "mode_2b_escalated_diff", "mode_3c_pace_cap"),
    }

    comparison = {}
    for title, row in test_players:
        player_res = {}
        for m_name, cfg in modes.items():
            if cfg is None:
                player_res[m_name] = {
                    "p3": round(float(row["score_state"]), 1),
                    "contrib": round(float(row["contribution_score"]), 1),
                }
            else:
                d_m, c_m, l_m = cfg
                res = compute_phase7g_contribution(row, death_rrr_mode=d_m, coattail_mode=c_m, low_target_mode=l_m)
                player_res[m_name] = {
                    "p3": res["p3_score"],
                    "contrib": res["contribution_score"],
                    "adj_p2": res["adj_p2"],
                    "adj_p3": res["adj_p3"],
                }
        comparison[f"{title}: {row['player']} ({int(row['actual_runs'])} off {int(row['balls_faced'])}b)"] = player_res

    return comparison


def test_18_stress_tests():
    print("\n=== 3. Running 18 Mandatory Stress Tests ===")
    
    stress_scenarios = [
        {
            "id": 1, "name": "Opener at 0/0 + excellent batting",
            "row": {"innings": 1, "entry_over": 0.0, "balls_faced": 50, "actual_runs": 85, "actual_sr": 170.0, "score_context": 37.3, "score_perf": 88.0, "expected_final_change": 24.0, "trajectory_deviation_change": 15.0, "team_rr_entry": 0.0, "window_team_rr": 10.2, "partnership_runs": 110, "batter_partnership_share": 0.77, "partner_runs": 25, "overs_spent": 11.0, "wickets_remaining_entry": 10, "wickets_remaining_exit": 9, "balls_remaining_entry": 120, "balls_remaining_exit": 54, "wicket_resource_change": -0.10}
        },
        {
            "id": 2, "name": "Opener at 0/0 + poor batting",
            "row": {"innings": 1, "entry_over": 0.0, "balls_faced": 20, "actual_runs": 12, "actual_sr": 60.0, "score_context": 37.3, "score_perf": 22.0, "expected_final_change": -18.0, "trajectory_deviation_change": -12.0, "team_rr_entry": 0.0, "window_team_rr": 3.6, "partnership_runs": 20, "batter_partnership_share": 0.60, "partner_runs": 8, "overs_spent": 5.5, "wickets_remaining_entry": 10, "wickets_remaining_exit": 9, "balls_remaining_entry": 120, "balls_remaining_exit": 87, "wicket_resource_change": -0.30}
        },
        {
            "id": 3, "name": "Batter entering at 20/3 + excellent batting",
            "row": {"innings": 1, "entry_over": 3.4, "balls_faced": 45, "actual_runs": 75, "actual_sr": 166.7, "score_context": 75.0, "score_perf": 86.0, "expected_final_change": 32.0, "trajectory_deviation_change": 20.0, "team_rr_entry": 5.5, "window_team_rr": 9.8, "partnership_runs": 95, "batter_partnership_share": 0.79, "partner_runs": 20, "overs_spent": 9.5, "wickets_remaining_entry": 7, "wickets_remaining_exit": 6, "balls_remaining_entry": 98, "balls_remaining_exit": 41, "wicket_resource_change": -0.15}
        },
        {
            "id": 4, "name": "Batter entering at 20/3 + poor batting",
            "row": {"innings": 1, "entry_over": 3.4, "balls_faced": 12, "actual_runs": 5, "actual_sr": 41.7, "score_context": 75.0, "score_perf": 18.0, "expected_final_change": -22.0, "trajectory_deviation_change": -15.0, "team_rr_entry": 5.5, "window_team_rr": 2.5, "partnership_runs": 8, "batter_partnership_share": 0.62, "partner_runs": 3, "overs_spent": 3.2, "wickets_remaining_entry": 7, "wickets_remaining_exit": 6, "balls_remaining_entry": 98, "balls_remaining_exit": 79, "wicket_resource_change": -0.45}
        },
        {
            "id": 5, "name": "Batter entering at 145/1 chasing 160",
            "row": {"innings": 2, "entry_over": 17.2, "balls_faced": 10, "actual_runs": 16, "actual_sr": 160.0, "score_context": 22.0, "score_perf": 55.0, "target": 160, "required_rr_entry": 3.4, "required_rr_exit": 0.0, "required_rr_change": 3.4, "target_progress_change": 0.10, "partnership_runs": 16, "batter_partnership_share": 1.0, "partner_runs": 0, "overs_spent": 1.8, "wickets_remaining_entry": 9, "wickets_remaining_exit": 9, "balls_remaining_entry": 16, "balls_remaining_exit": 5, "wicket_resource_change": 0.0}
        },
        {
            "id": 6, "name": "Death-over excellent batter in a losing chase",
            "row": {"innings": 2, "entry_over": 15.2, "balls_faced": 25, "actual_runs": 65, "actual_sr": 260.0, "score_context": 72.0, "score_perf": 93.0, "target": 215, "required_rr_entry": 14.5, "required_rr_exit": 36.0, "required_rr_change": -21.5, "target_progress_change": 0.35, "partnership_runs": 75, "batter_partnership_share": 0.86, "partner_runs": 10, "overs_spent": 4.1, "wickets_remaining_entry": 5, "wickets_remaining_exit": 2, "balls_remaining_entry": 28, "balls_remaining_exit": 3, "wicket_resource_change": -0.50}
        },
        {
            "id": 7, "name": "Death-over poor batter in a losing chase",
            "row": {"innings": 2, "entry_over": 16.0, "balls_faced": 12, "actual_runs": 8, "actual_sr": 66.7, "score_context": 75.0, "score_perf": 22.0, "target": 190, "required_rr_entry": 12.0, "required_rr_exit": 28.0, "required_rr_change": -16.0, "target_progress_change": 0.04, "partnership_runs": 12, "batter_partnership_share": 0.67, "partner_runs": 4, "overs_spent": 2.5, "wickets_remaining_entry": 6, "wickets_remaining_exit": 4, "balls_remaining_entry": 24, "balls_remaining_exit": 9, "wicket_resource_change": -0.60}
        },
        {
            "id": 8, "name": "Explosive partner + weak batter (Dhawan/Warner)",
            "row": {"innings": 1, "entry_over": 0.0, "balls_faced": 30, "actual_runs": 29, "actual_sr": 96.7, "score_context": 37.3, "score_perf": 52.0, "expected_final_change": 42.0, "trajectory_deviation_change": 25.0, "team_rr_entry": 0.0, "window_team_rr": 12.3, "partnership_runs": 139, "batter_partnership_share": 0.209, "partner_runs": 110, "overs_spent": 11.4, "wickets_remaining_entry": 10, "wickets_remaining_exit": 9, "balls_remaining_entry": 120, "balls_remaining_exit": 52, "wicket_resource_change": -0.10}
        },
        {
            "id": 9, "name": "Weak partner + carrying batter (Nair/Miller)",
            "row": {"innings": 2, "entry_over": 5.2, "balls_faced": 33, "actual_runs": 50, "actual_sr": 151.5, "score_context": 49.6, "score_perf": 80.2, "target": 165, "required_rr_entry": 8.5, "required_rr_exit": 6.8, "required_rr_change": 1.7, "target_progress_change": 0.35, "partnership_runs": 74, "batter_partnership_share": 0.676, "partner_runs": 24, "overs_spent": 10.5, "wickets_remaining_entry": 8, "wickets_remaining_exit": 7, "balls_remaining_entry": 88, "balls_remaining_exit": 25, "wicket_resource_change": -0.15}
        },
        {
            "id": 10, "name": "Mutual acceleration (Yuvraj/Henriques)",
            "row": {"innings": 1, "entry_over": 10.4, "balls_faced": 27, "actual_runs": 62, "actual_sr": 229.6, "score_context": 28.1, "score_perf": 93.1, "expected_final_change": 38.0, "trajectory_deviation_change": 22.0, "team_rr_entry": 7.5, "window_team_rr": 12.1, "partnership_runs": 97, "batter_partnership_share": 0.639, "partner_runs": 35, "overs_spent": 8.0, "wickets_remaining_entry": 8, "wickets_remaining_exit": 7, "balls_remaining_entry": 56, "balls_remaining_exit": 8, "wicket_resource_change": -0.05}
        },
        {
            "id": 11, "name": "Low-target chase + slow batter (Smith in 94 target)",
            "row": {"innings": 2, "entry_over": 8.2, "balls_faced": 18, "actual_runs": 15, "actual_sr": 83.3, "score_context": 24.0, "score_perf": 45.0, "target": 94, "required_rr_entry": 4.5, "required_rr_exit": 2.8, "required_rr_change": 1.7, "target_progress_change": 0.16, "partnership_runs": 28, "batter_partnership_share": 0.536, "partner_runs": 13, "overs_spent": 4.5, "wickets_remaining_entry": 8, "wickets_remaining_exit": 8, "balls_remaining_entry": 70, "balls_remaining_exit": 43, "wicket_resource_change": 0.0}
        },
        {
            "id": 12, "name": "Low-target chase + excellent batter (aggressive finish)",
            "row": {"innings": 2, "entry_over": 8.2, "balls_faced": 14, "actual_runs": 32, "actual_sr": 228.6, "score_context": 24.0, "score_perf": 82.0, "target": 94, "required_rr_entry": 4.5, "required_rr_exit": 0.0, "required_rr_change": 4.5, "target_progress_change": 0.34, "partnership_runs": 38, "batter_partnership_share": 0.842, "partner_runs": 6, "overs_spent": 2.8, "wickets_remaining_entry": 8, "wickets_remaining_exit": 8, "balls_remaining_entry": 70, "balls_remaining_exit": 53, "wicket_resource_change": 0.0}
        },
        {
            "id": 13, "name": "Losing-team hero (de Villiers 89* off 46)",
            "row": {"innings": 1, "entry_over": 4.2, "balls_faced": 46, "actual_runs": 89, "actual_sr": 193.5, "score_context": 55.0, "score_perf": 97.8, "expected_final_change": 28.0, "trajectory_deviation_change": 18.0, "team_rr_entry": 6.2, "window_team_rr": 9.4, "partnership_runs": 105, "batter_partnership_share": 0.848, "partner_runs": 16, "overs_spent": 15.4, "wickets_remaining_entry": 8, "wickets_remaining_exit": 6, "balls_remaining_entry": 94, "balls_remaining_exit": 2, "wicket_resource_change": 0.15, "won_match": False}
        },
        {
            "id": 14, "name": "Winning-team passenger (Henriques 9 off 16)",
            "row": {"innings": 2, "entry_over": 6.2, "balls_faced": 16, "actual_runs": 9, "actual_sr": 56.2, "score_context": 42.0, "score_perf": 24.9, "target": 135, "required_rr_entry": 6.2, "required_rr_exit": 7.4, "required_rr_change": -1.2, "target_progress_change": 0.07, "partnership_runs": 18, "batter_partnership_share": 0.50, "partner_runs": 9, "overs_spent": 4.2, "wickets_remaining_entry": 8, "wickets_remaining_exit": 7, "balls_remaining_entry": 82, "balls_remaining_exit": 57, "wicket_resource_change": -0.27, "won_match": True}
        },
        {
            "id": 15, "name": "DNB appearance",
            "row": {"dnb": True, "balls_faced": np.nan, "actual_runs": np.nan}
        },
        {
            "id": 16, "name": "Pure Powerplay innings (Abhishek Sharma)",
            "row": {"innings": 1, "entry_over": 0.2, "balls_faced": 8, "actual_runs": 7, "actual_sr": 87.5, "score_context": 37.3, "score_perf": 43.7, "expected_final_change": -5.0, "trajectory_deviation_change": -3.0, "team_rr_entry": 0.0, "window_team_rr": 6.0, "partnership_runs": 14, "batter_partnership_share": 0.50, "partner_runs": 7, "overs_spent": 1.9, "wickets_remaining_entry": 10, "wickets_remaining_exit": 9, "balls_remaining_entry": 118, "balls_remaining_exit": 107, "wicket_resource_change": -0.25}
        },
        {
            "id": 17, "name": "Middle-over overlap (overs 7 to 15)",
            "row": {"innings": 1, "entry_over": 6.4, "balls_faced": 35, "actual_runs": 45, "actual_sr": 128.6, "score_context": 48.0, "score_perf": 62.0, "expected_final_change": 12.0, "trajectory_deviation_change": 8.0, "team_rr_entry": 7.8, "window_team_rr": 8.4, "partnership_runs": 65, "batter_partnership_share": 0.692, "partner_runs": 20, "overs_spent": 8.2, "wickets_remaining_entry": 8, "wickets_remaining_exit": 7, "balls_remaining_entry": 80, "balls_remaining_exit": 31, "wicket_resource_change": -0.10}
        },
        {
            "id": 18, "name": "Death-over-only innings (30 off 5 burst)",
            "row": {"innings": 1, "entry_over": 19.1, "balls_faced": 5, "actual_runs": 30, "actual_sr": 600.0, "score_context": 90.0, "score_perf": 98.0, "expected_final_change": 22.0, "trajectory_deviation_change": 18.0, "team_rr_entry": 8.5, "window_team_rr": 36.0, "partnership_runs": 30, "batter_partnership_share": 1.0, "partner_runs": 0, "overs_spent": 0.9, "wickets_remaining_entry": 6, "wickets_remaining_exit": 6, "balls_remaining_entry": 5, "balls_remaining_exit": 0, "wicket_resource_change": 0.15}
        },
    ]

    stress_results = []
    for sc in stress_scenarios:
        row = sc["row"]
        # Candidate 1 (Mode 1A + 2A + 3A)
        res_c1 = compute_phase7g_contribution(row, death_rrr_mode="mode_1a_sr_capped", coattail_mode="mode_2a_share_dampening", low_target_mode="mode_3a_exec_gate")
        # Baseline P7F
        res_p7f = compute_phase7g_contribution(row, death_rrr_mode="baseline", coattail_mode="baseline", low_target_mode="baseline")
        
        stress_results.append({
            "id": sc["id"],
            "name": sc["name"],
            "candidate_1_score": res_c1["contribution_score"],
            "candidate_1_p3": res_c1["p3_score"],
            "p7f_baseline_score": res_p7f["contribution_score"],
            "p7f_baseline_p3": res_p7f["p3_score"],
            "leverage": res_c1["leverage"],
            "dnb": res_c1["dnb"],
        })
    return stress_results


def main():
    df = load_dataset()
    dist_results = evaluate_alternatives(df)
    issue_cases = test_specific_failure_cases(df)
    stress_results = test_18_stress_tests()

    print("\n--- Summary of Candidate Distributions ---")
    for k, v in dist_results.items():
        print(f"{k}: Mean={v['mean']}, Median={v['median']}, Std={v['std']}, Corr(P7D)={v['corr_with_p7d']}, P2/P3 Corr={v['p2_p3_corr']}")

    print("\n--- Summary of Failure Cases ---")
    for k, v in issue_cases.items():
        print(f"\n{k}:")
        for m, data in v.items():
            print(f"   {m}: P3={data['p3']}, Contrib={data['contrib']}")

    print("\n--- Stress Tests Sample (First 5) ---")
    for s in stress_results[:5]:
        print(f"#{s['id']} {s['name']}: Cand1={s['candidate_1_score']} (P3={s['candidate_1_p3']}) vs P7F={s['p7f_baseline_score']} (P3={s['p7f_baseline_p3']})")

    # Save to JSON
    out_dict = {
        "candidate_distributions": dist_results,
        "failure_case_evaluations": issue_cases,
        "stress_test_evaluations": stress_results,
    }
    with open("models/contribution/phase7/phase7g_p3_correction_validation.json", "w", encoding="utf-8") as f:
        json.dump(out_dict, f, indent=2)
    print("\nSaved evaluation results to models/contribution/phase7/phase7g_p3_correction_validation.json")


if __name__ == "__main__":
    main()
