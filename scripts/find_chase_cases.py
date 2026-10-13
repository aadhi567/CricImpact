"""
Inspect chase cases with RRR progression.
"""
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.find_p3_cases import load_data, get_primary_partner
from scripts.inspect_p3_dataset import decompose_p3


def find_chase():
    df_contrib, df_parts, df_matches, df_deliveries = load_data()
    chase = df_contrib[(df_contrib["innings"] == 2) & df_contrib["required_rr_entry"].notnull() & df_contrib["required_rr_exit"].notnull()].copy()

    # Decompose
    records = []
    for _, r in chase.iterrows():
        records.append(decompose_p3(r))
    df_p3 = pd.DataFrame(records).add_prefix("p3_")
    merged = pd.concat([chase.reset_index(drop=True), df_p3.reset_index(drop=True)], axis=1)

    print("=== 1. RRR Improved: Entry >= 9.5, Exit <= Entry - 2.0 ===")
    imp = merged[(merged["required_rr_entry"] >= 9.5) & (merged["required_rr_exit"] <= merged["required_rr_entry"] - 2.0) & (merged["balls_faced"] >= 20)]
    for _, r in imp.head(5).iterrows():
        p, _ = get_primary_partner(r["match_id"], r["innings"], r["player"], df_deliveries)
        print(f"{r['player']} ({r['season']}, M{r['match_id']}): {r['actual_runs']} ({r['balls_faced']}b, SR {r['actual_sr']:.1f}) & {p}")
        print(f"  RRR: {r['required_rr_entry']:.2f} -> {r['required_rr_exit']:.2f} (delta: {r['required_rr_change']:+.2f}) | P3: {r['score_state']:.1f} | Won: {r['won_match']}")
        print(f"  z_macro: {r['p3_z_macro']:.2f}, z_partner: {r['p3_z_partner']:.2f}, z_stab: {r['p3_z_collapse']:.2f}\n")

    print("=== 2. RRR Deteriorated: Entry 7.5-9.5, Exit >= Entry + 2.0 ===")
    det = merged[(merged["required_rr_entry"].between(7.5, 9.5)) & (merged["required_rr_exit"] >= merged["required_rr_entry"] + 2.0) & (merged["balls_faced"] >= 20)]
    for _, r in det.head(5).iterrows():
        p, _ = get_primary_partner(r["match_id"], r["innings"], r["player"], df_deliveries)
        print(f"{r['player']} ({r['season']}, M{r['match_id']}): {r['actual_runs']} ({r['balls_faced']}b, SR {r['actual_sr']:.1f}) & {p}")
        print(f"  RRR: {r['required_rr_entry']:.2f} -> {r['required_rr_exit']:.2f} (delta: {r['required_rr_change']:+.2f}) | P3: {r['score_state']:.1f} | Won: {r['won_match']}")
        print(f"  z_macro: {r['p3_z_macro']:.2f}, z_partner: {r['p3_z_partner']:.2f}, z_stab: {r['p3_z_collapse']:.2f}\n")

    print("=== 3. Batter Slow + Partner Fast in Chase ===")
    slow_fast = merged[(merged["actual_sr"] <= 110.0) & (merged["p3_partner_sr"] >= 150.0) & (merged["balls_faced"] >= 15) & (merged["p3_partner_balls"] >= 15)]
    for _, r in slow_fast.head(5).iterrows():
        p, _ = get_primary_partner(r["match_id"], r["innings"], r["player"], df_deliveries)
        print(f"{r['player']} ({r['season']}, M{r['match_id']}): {r['actual_runs']} ({r['balls_faced']}b, SR {r['actual_sr']:.1f}) & {p} ({r['partner_runs']} off {r['p3_partner_balls']}b, SR {r['p3_partner_sr']:.1f})")
        print(f"  RRR: {r['required_rr_entry']:.2f} -> {r['required_rr_exit']:.2f} (delta: {r['required_rr_change']:+.2f}) | P3: {r['score_state']:.1f} | P2: {r['score_perf']:.1f} | Won: {r['won_match']}")
        print(f"  z_macro: {r['p3_z_macro']:.2f}, z_partner: {r['p3_z_partner']:.2f}\n")


if __name__ == "__main__":
    find_chase()
