"""
Find real match examples for the 4 specific Non-Striker Dynamics archetypes.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.find_p3_cases import load_data, get_primary_partner
from scripts.inspect_p3_dataset import decompose_p3


def find_archetypes():
    df_contrib, df_parts, df_matches, df_deliveries = load_data()

    # Decompose P3
    p3_records = []
    for _, r in df_contrib.iterrows():
        p3_records.append(decompose_p3(r))
    df_p3 = pd.DataFrame(p3_records).add_prefix("p3_")
    df = pd.concat([df_contrib, df_p3], axis=1)

    print("--- 1. Batter carries partner (Batter ~60 off 40, Partner ~20 off 30) ---")
    c1 = df[
        (df["actual_runs"].between(50, 75)) &
        (df["balls_faced"].between(30, 50)) &
        (df["actual_sr"].between(130, 175)) &
        (df["partner_runs"].between(15, 30)) &
        (df["p3_partner_balls"].between(20, 40)) &
        (df["p3_partner_sr"] <= 110.0) &
        (df["batter_partnership_share"] >= 0.65)
    ]
    print(f"Found {len(c1)} matches:")
    for _, r in c1.head(5).iterrows():
        p, _ = get_primary_partner(r["match_id"], r["innings"], r["player"], df_deliveries)
        print(f"Match {r['match_id']} ({r['season']}, Inn {r['innings']}): {r['player']} ({r['actual_runs']} off {r['balls_faced']}b, SR {r['actual_sr']:.1f}) & {p} ({r['partner_runs']} off {r['p3_partner_balls']}b, SR {r['p3_partner_sr']:.1f})")
        print(f"   Batter Share: {r['batter_partnership_share']:.1%}, is_carrying: {r['p3_is_carrying']}")
        print(f"   P3: {r['score_state']:.1f} (raw: {r['p3_p3_raw']:.3f}, z_macro: {r['p3_z_macro']:.2f}, z_part: {r['p3_z_partner']:.2f}, z_stab: {r['p3_z_collapse']:.2f}, z_eq: {r['p3_z_wicket_equity']:.2f})")
        print(f"   P1: {r['score_context']:.1f}, P2: {r['score_perf']:.1f}, Overall: {r['contribution_score']:.1f}\n")

    print("--- 2. Partner faster contributor (Batter ~20 off 18, Partner ~35 off 22) ---")
    c2 = df[
        (df["actual_runs"].between(15, 28)) &
        (df["balls_faced"].between(14, 25)) &
        (df["actual_sr"].between(100, 130)) &
        (df["partner_runs"].between(30, 48)) &
        (df["p3_partner_balls"].between(16, 30)) &
        (df["p3_partner_sr"] >= 140.0)
    ]
    print(f"Found {len(c2)} matches:")
    for _, r in c2.head(5).iterrows():
        p, _ = get_primary_partner(r["match_id"], r["innings"], r["player"], df_deliveries)
        print(f"Match {r['match_id']} ({r['season']}, Inn {r['innings']}): {r['player']} ({r['actual_runs']} off {r['balls_faced']}b, SR {r['actual_sr']:.1f}) & {p} ({r['partner_runs']} off {r['p3_partner_balls']}b, SR {r['p3_partner_sr']:.1f})")
        print(f"   Batter Share: {r['batter_partnership_share']:.1%}, is_carrying: {r['p3_is_carrying']}")
        print(f"   P3: {r['score_state']:.1f} (raw: {r['p3_p3_raw']:.3f}, z_macro: {r['p3_z_macro']:.2f}, z_part: {r['p3_z_partner']:.2f}, z_stab: {r['p3_z_collapse']:.2f}, z_eq: {r['p3_z_wicket_equity']:.2f})")
        print(f"   P1: {r['score_context']:.1f}, P2: {r['score_perf']:.1f}, Overall: {r['contribution_score']:.1f}\n")

    print("--- 3. Mutual acceleration (Both SR >= 140, Total >= 40) ---")
    c3 = df[
        (df["actual_runs"] >= 25) &
        (df["balls_faced"] >= 12) &
        (df["actual_sr"] >= 145.0) &
        (df["partner_runs"] >= 25) &
        (df["p3_partner_balls"] >= 12) &
        (df["p3_partner_sr"] >= 145.0) &
        (df["partnership_runs"] >= 50)
    ]
    print(f"Found {len(c3)} matches:")
    for _, r in c3.head(5).iterrows():
        p, _ = get_primary_partner(r["match_id"], r["innings"], r["player"], df_deliveries)
        print(f"Match {r['match_id']} ({r['season']}, Inn {r['innings']}): {r['player']} ({r['actual_runs']} off {r['balls_faced']}b, SR {r['actual_sr']:.1f}) & {p} ({r['partner_runs']} off {r['p3_partner_balls']}b, SR {r['p3_partner_sr']:.1f})")
        print(f"   Batter Share: {r['batter_partnership_share']:.1%}, is_mutual: {r['p3_is_mutual']}, synergy: {r['p3_synergy_bonus']}")
        print(f"   P3: {r['score_state']:.1f} (raw: {r['p3_p3_raw']:.3f}, z_macro: {r['p3_z_macro']:.2f}, z_part: {r['p3_z_partner']:.2f}, z_stab: {r['p3_z_collapse']:.2f}, z_eq: {r['p3_z_wicket_equity']:.2f})")
        print(f"   P1: {r['score_context']:.1f}, P2: {r['score_perf']:.1f}, Overall: {r['contribution_score']:.1f}\n")

    print("--- 4. Stable anchor + aggressive partner (Batter ~35 off 30, Partner ~55 off 25) ---")
    c4 = df[
        (df["actual_runs"].between(28, 42)) &
        (df["balls_faced"].between(24, 36)) &
        (df["actual_sr"].between(100, 125)) &
        (df["partner_runs"].between(45, 75)) &
        (df["p3_partner_balls"].between(20, 35)) &
        (df["p3_partner_sr"] >= 170.0)
    ]
    print(f"Found {len(c4)} matches:")
    for _, r in c4.head(5).iterrows():
        p, _ = get_primary_partner(r["match_id"], r["innings"], r["player"], df_deliveries)
        print(f"Match {r['match_id']} ({r['season']}, Inn {r['innings']}): {r['player']} ({r['actual_runs']} off {r['balls_faced']}b, SR {r['actual_sr']:.1f}) & {p} ({r['partner_runs']} off {r['p3_partner_balls']}b, SR {r['p3_partner_sr']:.1f})")
        print(f"   Batter Share: {r['batter_partnership_share']:.1%}")
        print(f"   P3: {r['score_state']:.1f} (raw: {r['p3_p3_raw']:.3f}, z_macro: {r['p3_z_macro']:.2f}, z_part: {r['p3_z_partner']:.2f}, z_stab: {r['p3_z_collapse']:.2f}, z_eq: {r['p3_z_wicket_equity']:.2f})")
        print(f"   P1: {r['score_context']:.1f}, P2: {r['score_perf']:.1f}, Overall: {r['contribution_score']:.1f}\n")


if __name__ == "__main__":
    find_archetypes()
