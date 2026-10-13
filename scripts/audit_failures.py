"""
Audit Failure Modes A through H across all 19,111 innings in the dataset.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.inspect_p3_dataset import decompose_p3


def load_dataset():
    df = pd.read_csv("data/processed/batter_match_contributions.csv", low_memory=False)
    # Decompose P3
    p3_records = []
    for _, r in df.iterrows():
        p3_records.append(decompose_p3(r))
    df_p3 = pd.DataFrame(p3_records)
    # rename columns to avoid clash
    df_p3 = df_p3.add_prefix("p3_")
    merged = pd.concat([df, df_p3], axis=1)
    return merged


def investigate_failures(df):
    print(f"Total innings: {len(df):,}")

    print("\n========================================================")
    print("FAILURE MODE A: Low individual impact, but very high P3")
    print("Criteria: actual_runs <= 15, score_perf <= 40, score_state >= 70, balls >= 10")
    print("========================================================")
    f_a = df[(df["actual_runs"] <= 15) & (df["score_perf"] <= 40.0) & (df["score_state"] >= 70.0) & (df["balls_faced"] >= 10)]
    print(f"Count matching Failure A: {len(f_a)}")
    for _, r in f_a.head(8).iterrows():
        print(f"  {r['player']} ({r['season']}, M{r['match_id']}): {r['actual_runs']} ({r['balls_faced']}b, SR {r['actual_sr']:.1f}) | P1: {r['score_context']:.1f} | P2: {r['score_perf']:.1f} | P3: {r['score_state']:.1f} | z_macro: {r['p3_z_macro']:.2f}, z_partner: {r['p3_z_partner']:.2f}, z_stab: {r['p3_z_collapse']:.2f} | team_runs_added: {r.get('team_runs_added')}")

    print("\n========================================================")
    print("FAILURE MODE B: High individual impact, but low P3 due to partner")
    print("Criteria: actual_runs >= 40, actual_sr >= 140, score_perf >= 75, score_state <= 40")
    print("========================================================")
    f_b = df[(df["actual_runs"] >= 40) & (df["actual_sr"] >= 140.0) & (df["score_perf"] >= 75.0) & (df["score_state"] <= 40.0)]
    print(f"Count matching Failure B: {len(f_b)}")
    for _, r in f_b.head(8).iterrows():
        print(f"  {r['player']} ({r['season']}, M{r['match_id']}): {r['actual_runs']} ({r['balls_faced']}b, SR {r['actual_sr']:.1f}) | P2: {r['score_perf']:.1f} | P3: {r['score_state']:.1f} | z_macro: {r['p3_z_macro']:.2f}, z_partner: {r['p3_z_partner']:.2f}, b_share: {r['batter_partnership_share']:.2f}, partner_sr: {r['p3_partner_sr']:.1f} | EFS chg: {r.get('expected_final_change')} | RRR chg: {r.get('required_rr_change')}")

    print("\n========================================================")
    print("FAILURE MODE C: Batter enters during collapse and receives excessive P3 purely from entry")
    print("Criteria: wickets_remaining_entry <= 4, entry_over <= 8.0, actual_runs <= 15, score_state >= 65")
    print("========================================================")
    f_c = df[(df["wickets_remaining_entry"] <= 4) & (df["entry_over"] <= 8.0) & (df["actual_runs"] <= 15) & (df["score_state"] >= 65.0)]
    print(f"Count matching Failure C: {len(f_c)}")
    for _, r in f_c.head(8).iterrows():
        print(f"  {r['player']} ({r['season']}, M{r['match_id']}): {r['actual_runs']} ({r['balls_faced']}b) | entry: {r['entry_over']} ov ({10-r['wickets_remaining_entry']} wkts down) | P3: {r['score_state']:.1f} | z_macro: {r['p3_z_macro']:.2f}, z_partner: {r['p3_z_partner']:.2f}, z_stab: {r['p3_z_collapse']:.2f}")

    print("\n========================================================")
    print("FAILURE MODE D: Batter benefits from already strong team position and receives excessive P3")
    print("Criteria: team_rr_entry >= 10.0, actual_runs <= 15, actual_sr <= 110, score_state >= 65, balls >= 8")
    print("========================================================")
    f_d = df[(df["team_rr_entry"] >= 10.0) & (df["actual_runs"] <= 15) & (df["actual_sr"] <= 110.0) & (df["score_state"] >= 65.0) & (df["balls_faced"] >= 8)]
    print(f"Count matching Failure D: {len(f_d)}")
    for _, r in f_d.head(8).iterrows():
        print(f"  {r['player']} ({r['season']}, M{r['match_id']}): {r['actual_runs']} ({r['balls_faced']}b, SR {r['actual_sr']:.1f}) | team_rr_entry: {r['team_rr_entry']} | P3: {r['score_state']:.1f} | z_macro: {r['p3_z_macro']:.2f}, z_partner: {r['p3_z_partner']:.2f}")

    print("\n========================================================")
    print("FAILURE MODE E: Partner accelerated, but batter gets high P3 while partner has lower P3")
    print("Criteria: partner_runs >= 40, partner_sr >= actual_sr + 40, actual_sr <= 115, score_state >= 60, balls >= 15")
    print("========================================================")
    f_e = df[(df["partner_runs"] >= 40) & (df["p3_partner_sr"] >= df["actual_sr"] + 40.0) & (df["actual_sr"] <= 115.0) & (df["score_state"] >= 60.0) & (df["balls_faced"] >= 15)]
    print(f"Count matching Failure E: {len(f_e)}")
    for _, r in f_e.head(8).iterrows():
        print(f"  {r['player']} ({r['season']}, M{r['match_id']}): {r['actual_runs']} ({r['balls_faced']}b, SR {r['actual_sr']:.1f}) | Partner: {r['partner_runs']} ({r['p3_partner_balls']}b, SR {r['p3_partner_sr']:.1f}) | P3: {r['score_state']:.1f} | P2: {r['score_perf']:.1f} | z_macro: {r['p3_z_macro']:.2f}, z_partner: {r['p3_z_partner']:.2f}")

    print("\n========================================================")
    print("FAILURE MODE F: Losing-team batter unfairly suppressed despite strong performance")
    print("Criteria: won_match == 0, actual_runs >= 50, actual_sr >= 140, score_state <= 35")
    print("========================================================")
    f_f = df[(df["won_match"] == 0) & (df["actual_runs"] >= 50) & (df["actual_sr"] >= 140.0) & (df["score_state"] <= 35.0)]
    print(f"Count matching Failure F: {len(f_f)}")
    for _, r in f_f.head(8).iterrows():
        print(f"  {r['player']} ({r['season']}, M{r['match_id']}): {r['actual_runs']} ({r['balls_faced']}b, SR {r['actual_sr']:.1f}) | P3: {r['score_state']:.1f} | P2: {r['score_perf']:.1f} | z_macro: {r['p3_z_macro']:.2f}, z_partner: {r['p3_z_partner']:.2f}, EFS chg: {r.get('expected_final_change')}, RRR chg: {r.get('required_rr_change')}")

    print("\n========================================================")
    print("FAILURE MODE G: Winning-team batter gets excessive P3 despite making little difference")
    print("Criteria: won_match == 1, actual_runs <= 15, balls_faced >= 12, actual_sr <= 90, score_state >= 60")
    print("========================================================")
    f_g = df[(df["won_match"] == 1) & (df["actual_runs"] <= 15) & (df["balls_faced"] >= 12) & (df["actual_sr"] <= 90.0) & (df["score_state"] >= 60.0)]
    print(f"Count matching Failure G: {len(f_g)}")
    for _, r in f_g.head(8).iterrows():
        print(f"  {r['player']} ({r['season']}, M{r['match_id']}): {r['actual_runs']} ({r['balls_faced']}b, SR {r['actual_sr']:.1f}) | P3: {r['score_state']:.1f} | P2: {r['score_perf']:.1f} | z_macro: {r['p3_z_macro']:.2f}, z_partner: {r['p3_z_partner']:.2f}")

    print("\n========================================================")
    print("FAILURE MODE H: P3 duplicates P2 too strongly (|P3 - P2| <= 3.0 across whole dataset)")
    print("========================================================")
    diff = (df["score_state"] - df["score_perf"]).abs()
    print(f"Mean |P3 - P2|: {diff.mean():.2f}")
    print(f"Median |P3 - P2|: {diff.median():.2f}")
    print(f"Percentage of innings where |P3 - P2| <= 5.0: {(diff <= 5.0).mean() * 100:.1f}%")
    print(f"Percentage of innings where |P3 - P2| >= 20.0: {(diff >= 20.0).mean() * 100:.1f}%")


if __name__ == "__main__":
    df = load_dataset()
    investigate_failures(df)
