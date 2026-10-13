"""
Query real IPL player matches for Phase 7G report.
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.phase7g_simulation import compute_phase7g_contribution

def main():
    df = pd.read_csv("data/processed/batter_match_contributions.csv", low_memory=False)

    print("=================================================================")
    print("1. DEATH-OVER HITTERS IN LOSING CHASES (balls_rem <= 12, SR >= 160)")
    print("=================================================================")
    cond1 = (
        (df["balls_remaining_exit"] <= 12)
        & (df["actual_sr"] >= 160)
        & (df["won_match"] == False)
        & (df["balls_faced"] >= 15)
        & (df["innings"] == 2)
    )
    cases1 = df[cond1].sort_values("actual_runs", ascending=False).head(5)
    for _, r in cases1.iterrows():
        b_res = compute_phase7g_contribution(r, "baseline", "baseline", "baseline")
        g_res = compute_phase7g_contribution(r, "mode_1a_sr_capped", "mode_2c_hybrid", "mode_3c_pace_cap")
        print(f"{r['player']} {int(r['actual_runs'])} ({int(r['balls_faced'])}b, SR {r['actual_sr']:.1f}) [Match {r['match_id']}]:")
        print(f"   P7D Production: P3={r['score_state']:.1f}, Final={r['contribution_score']:.1f}")
        print(f"   P7F Baseline:   P3={b_res['p3_score']}, Final={b_res['contribution_score']} (AdjP2={b_res['adj_p2']}, AdjP3={b_res['adj_p3']})")
        print(f"   P7G Corrected:  P3={g_res['p3_score']}, Final={g_res['contribution_score']} (AdjP2={g_res['adj_p2']}, AdjP3={g_res['adj_p3']})")

    print("\n=================================================================")
    print("2. PARTNER COATTAIL INNINGS (Partner >= 2.5x runs or share < 30%)")
    print("=================================================================")
    cond2 = (
        (df["partnership_runs"] >= 50)
        & (df["batter_partnership_share"] <= 0.28)
        & (df["balls_faced"] >= 15)
        & (df["actual_sr"] <= 110)
    )
    cases2 = df[cond2].sort_values("partnership_runs", ascending=False).head(5)
    for _, r in cases2.iterrows():
        b_res = compute_phase7g_contribution(r, "baseline", "baseline", "baseline")
        g_res = compute_phase7g_contribution(r, "mode_1a_sr_capped", "mode_2c_hybrid", "mode_3c_pace_cap")
        print(f"{r['player']} {int(r['actual_runs'])} ({int(r['balls_faced'])}b) in {int(r['partnership_runs'])} part [Match {r['match_id']}]:")
        print(f"   P7D Production: P3={r['score_state']:.1f}, Final={r['contribution_score']:.1f}")
        print(f"   P7F Baseline:   P3={b_res['p3_score']}, Final={b_res['contribution_score']}")
        print(f"   P7G Corrected:  P3={g_res['p3_score']}, Final={g_res['contribution_score']}")

    print("\n=================================================================")
    print("3. LOW-TARGET CHASE ANCHORS (Target <= 125, SR <= 100)")
    print("=================================================================")
    cond3 = (
        (df["innings"] == 2)
        & (df["target"] <= 125)
        & (df["actual_sr"] <= 100)
        & (df["balls_faced"] >= 15)
    )
    cases3 = df[cond3].sort_values("target", ascending=True).head(5)
    for _, r in cases3.iterrows():
        b_res = compute_phase7g_contribution(r, "baseline", "baseline", "baseline")
        g_res = compute_phase7g_contribution(r, "mode_1a_sr_capped", "mode_2c_hybrid", "mode_3c_pace_cap")
        print(f"{r['player']} {int(r['actual_runs'])} ({int(r['balls_faced'])}b) chasing {int(r['target'])} [Match {r['match_id']}]:")
        print(f"   P7D Production: P3={r['score_state']:.1f}, Final={r['contribution_score']:.1f}")
        print(f"   P7F Baseline:   P3={b_res['p3_score']}, Final={b_res['contribution_score']}")
        print(f"   P7G Corrected:  P3={g_res['p3_score']}, Final={g_res['contribution_score']}")

    print("\n=================================================================")
    print("4. COLLAPSE RESCUERS (Entering <= 30/3, Runs >= 50)")
    print("=================================================================")
    cond4 = (
        (df["wickets_remaining_entry"] <= 7)
        & (df["balls_remaining_entry"] >= 85)
        & (df["actual_runs"] >= 50)
    )
    cases4 = df[cond4].sort_values("actual_runs", ascending=False).head(4)
    for _, r in cases4.iterrows():
        b_res = compute_phase7g_contribution(r, "baseline", "baseline", "baseline")
        g_res = compute_phase7g_contribution(r, "mode_1a_sr_capped", "mode_2c_hybrid", "mode_3c_pace_cap")
        print(f"{r['player']} {int(r['actual_runs'])} ({int(r['balls_faced'])}b) from entry wkts={int(10-r['wickets_remaining_entry'])} [Match {r['match_id']}]:")
        print(f"   P7D Production: P3={r['score_state']:.1f}, Final={r['contribution_score']:.1f}")
        print(f"   P7F Baseline:   P3={b_res['p3_score']}, Final={b_res['contribution_score']}")
        print(f"   P7G Corrected:  P3={g_res['p3_score']}, Final={g_res['contribution_score']}")

    print("\n=================================================================")
    print("5. LOSING-TEAM HEROES (Won=False, Runs >= 70, SR >= 160)")
    print("=================================================================")
    cond5 = (
        (df["won_match"] == False)
        & (df["actual_runs"] >= 70)
        & (df["actual_sr"] >= 160)
    )
    cases5 = df[cond5].sort_values("actual_runs", ascending=False).head(4)
    for _, r in cases5.iterrows():
        b_res = compute_phase7g_contribution(r, "baseline", "baseline", "baseline")
        g_res = compute_phase7g_contribution(r, "mode_1a_sr_capped", "mode_2c_hybrid", "mode_3c_pace_cap")
        print(f"{r['player']} {int(r['actual_runs'])} ({int(r['balls_faced'])}b, lost match) [Match {r['match_id']}]:")
        print(f"   P7D Production: P3={r['score_state']:.1f}, Final={r['contribution_score']:.1f}")
        print(f"   P7F Baseline:   P3={b_res['p3_score']}, Final={b_res['contribution_score']}")
        print(f"   P7G Corrected:  P3={g_res['p3_score']}, Final={g_res['contribution_score']}")

if __name__ == "__main__":
    main()
