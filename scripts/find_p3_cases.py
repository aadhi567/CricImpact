"""
Detailed candidate finder for Phase 7E P3 validation cases.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.inspect_p3_dataset import decompose_p3


def load_data():
    df_contrib = pd.read_csv("data/processed/batter_match_contributions.csv", low_memory=False)
    df_parts = pd.read_csv("data/processed/partnerships.csv", low_memory=False)
    df_matches = pd.read_csv("data/processed/matches.csv", low_memory=False)
    df_deliveries = pd.read_csv("data/processed/deliveries.csv", low_memory=False)
    return df_contrib, df_parts, df_matches, df_deliveries


def get_primary_partner(match_id, innings, player, df_deliveries):
    """Find the primary non-striker for this player in this innings from deliveries."""
    m_del = df_deliveries[(df_deliveries["match_id"] == match_id) & (df_deliveries["innings_number"] == innings)]
    # Deliveries where player was striker: partner is non_striker
    striker_del = m_del[m_del["batter"] == player]
    # Deliveries where player was non-striker: partner is batter
    non_striker_del = m_del[m_del["non_striker"] == player]
    
    partner_counts = {}
    for p in striker_del["non_striker"]:
        partner_counts[p] = partner_counts.get(p, 0) + 1
    for p in non_striker_del["batter"]:
        partner_counts[p] = partner_counts.get(p, 0) + 1
        
    if not partner_counts:
        return "Unknown", 0
    top_partner = max(partner_counts.items(), key=lambda x: x[1])
    return top_partner[0], top_partner[1]


def find_cases():
    df_contrib, df_parts, df_matches, df_deliveries = load_data()
    print(f"Total innings: {len(df_contrib):,}")
    
    # Enrich each row with decomposed P3
    records = []
    for idx, r in df_contrib.iterrows():
        p3_info = decompose_p3(r)
        records.append(p3_info)
    df_decomp = pd.DataFrame(records)
    df = pd.concat([df_contrib, df_decomp], axis=1)

    print("\n--- Searching for Category Candidates ---")

    # 1. 5 Strong Positive P3
    c1 = df[(df["score_state"] >= 88.0) & (df["actual_runs"] >= 50) & (df["balls_faced"] >= 25)].head(15)
    print("\n[Category 1: Strong Positive P3]")
    for _, r in c1.head(6).iterrows():
        p, _ = get_primary_partner(r["match_id"], r["innings"], r["player"], df_deliveries)
        print(f"{r['player']} ({r['season']}, M{r['match_id']}) - Partner: {p} | Runs: {r['actual_runs']} ({r['balls_faced']}b, SR {r['actual_sr']:.1f}) | P3: {r['score_state']} | P2: {r['score_perf']} | C: {r['contribution_score']} | Won: {r['won_match']}")

    # 2. 5 Neutral P3 (47-53)
    c2 = df[(df["score_state"] >= 48.0) & (df["score_state"] <= 52.0) & (df["balls_faced"] >= 15)].head(15)
    print("\n[Category 2: Neutral P3]")
    for _, r in c2.head(6).iterrows():
        p, _ = get_primary_partner(r["match_id"], r["innings"], r["player"], df_deliveries)
        print(f"{r['player']} ({r['season']}, M{r['match_id']}) - Partner: {p} | Runs: {r['actual_runs']} ({r['balls_faced']}b, SR {r['actual_sr']:.1f}) | P3: {r['score_state']} | P2: {r['score_perf']} | C: {r['contribution_score']} | Won: {r['won_match']}")

    # 3. 5 Weak Negative P3
    c3 = df[(df["score_state"] <= 20.0) & (df["balls_faced"] >= 15)].head(15)
    print("\n[Category 3: Weak Negative P3]")
    for _, r in c3.head(6).iterrows():
        p, _ = get_primary_partner(r["match_id"], r["innings"], r["player"], df_deliveries)
        print(f"{r['player']} ({r['season']}, M{r['match_id']}) - Partner: {p} | Runs: {r['actual_runs']} ({r['balls_faced']}b, SR {r['actual_sr']:.1f}) | P3: {r['score_state']} | P2: {r['score_perf']} | C: {r['contribution_score']} | Won: {r['won_match']}")

    # 4. Collapse Recovery (Entry wkts lost >= 3 or 4, actual runs >= 30, z_collapse > 0)
    c4 = df[(df["wickets_remaining_entry"] <= 6) & (df["entry_over"] <= 8.0) & (df["actual_runs"] >= 35) & (df["z_collapse"] > 0)].head(15)
    print("\n[Category 4: Collapse Recovery]")
    for _, r in c4.head(6).iterrows():
        p, _ = get_primary_partner(r["match_id"], r["innings"], r["player"], df_deliveries)
        print(f"{r['player']} ({r['season']}, M{r['match_id']}) - Partner: {p} | Entry: {r['entry_over']} ov ({10-r['wickets_remaining_entry']} wkts down) | Runs: {r['actual_runs']} ({r['balls_faced']}b) | z_stab: {r['z_collapse']} | P3: {r['score_state']} | C: {r['contribution_score']}")

    # Stable baseline (Opposite of collapse: e.g. entry at 120/2, entry_over ~ 12-14)
    c4_opp = df[(df["wickets_remaining_entry"] >= 8) & (df["entry_over"] >= 10.0) & (df["entry_over"] <= 14.0) & (df["actual_runs"] >= 30)].head(10)
    print("\n[Category 4 Opp: Stable Baseline entry (no collapse)]")
    for _, r in c4_opp.head(4).iterrows():
        p, _ = get_primary_partner(r["match_id"], r["innings"], r["player"], df_deliveries)
        print(f"{r['player']} ({r['season']}, M{r['match_id']}) - Partner: {p} | Entry: {r['entry_over']} ov ({10-r['wickets_remaining_entry']} wkts down) | Runs: {r['actual_runs']} ({r['balls_faced']}b) | z_stab: {r['z_collapse']} | P3: {r['score_state']}")

    # 5. High-Pressure Chase (innings 2, required_rr_entry >= 10.0, balls_faced >= 20)
    c5 = df[(df["innings"] == 2) & (df["required_rr_entry"] >= 10.0) & (df["balls_faced"] >= 20)].head(15)
    print("\n[Category 5: High-Pressure Chase]")
    for _, r in c5.head(6).iterrows():
        p, _ = get_primary_partner(r["match_id"], r["innings"], r["player"], df_deliveries)
        print(f"{r['player']} ({r['season']}, M{r['match_id']}) - Partner: {p} | RRR entry: {r['required_rr_entry']:.1f} -> exit: {r['required_rr_exit']:.1f} (chg: {r['required_rr_change']:.1f}) | Runs: {r['actual_runs']} ({r['balls_faced']}b) | P3: {r['score_state']} | Won: {r['won_match']}")

    # 6. Partnership Carrying (is_carrying == True)
    c6 = df[df["is_carrying"] == True].head(15)
    print("\n[Category 6: Partnership Carrying]")
    for _, r in c6.head(6).iterrows():
        p, _ = get_primary_partner(r["match_id"], r["innings"], r["player"], df_deliveries)
        print(f"{r['player']} ({r['season']}, M{r['match_id']}) - Partner: {p} | Batter: {r['actual_runs']} ({r['balls_faced']}b, SR {r['actual_sr']:.1f}) | Partner: {r['partner_runs']} ({r['partner_balls']}b, SR {r['partner_sr']:.1f}) | Share: {r['batter_partnership_share']:.1%} | P3: {r['score_state']}")

    # 7. Non-Striker Faster than Batter (partner_sr >= actual_sr + 35, both balls >= 15)
    c7 = df[(df["partner_sr"] >= df["actual_sr"] + 35.0) & (df["partner_balls"] >= 15) & (df["balls_faced"] >= 15)].head(15)
    print("\n[Category 7: Partner Faster than Batter]")
    for _, r in c7.head(6).iterrows():
        p, _ = get_primary_partner(r["match_id"], r["innings"], r["player"], df_deliveries)
        print(f"{r['player']} ({r['season']}, M{r['match_id']}) - Partner: {p} | Batter: {r['actual_runs']} ({r['balls_faced']}b, SR {r['actual_sr']:.1f}) | Partner: {r['partner_runs']} ({r['partner_balls']}b, SR {r['partner_sr']:.1f}) | P3: {r['score_state']} | P2: {r['score_perf']}")

    # 8. Mutual Acceleration (is_mutual == True)
    c8 = df[df["is_mutual"] == True].head(15)
    print("\n[Category 8: Mutual Acceleration]")
    for _, r in c8.head(6).iterrows():
        p, _ = get_primary_partner(r["match_id"], r["innings"], r["player"], df_deliveries)
        print(f"{r['player']} ({r['season']}, M{r['match_id']}) - Partner: {p} | Batter: {r['actual_runs']} ({r['balls_faced']}b, SR {r['actual_sr']:.1f}) | Partner: {r['partner_runs']} ({r['partner_balls']}b, SR {r['partner_sr']:.1f}) | Total: {r['partnership_runs']} | P3: {r['score_state']}")

    # 9. Lost Match Despite Strong Batter Contribution (won_match == 0, score_perf >= 75, score_state >= 70)
    c9 = df[(df["won_match"] == 0) & (df["score_perf"] >= 75.0) & (df["score_state"] >= 70.0)].head(15)
    print("\n[Category 9: Lost Match Despite Strong Batter]")
    for _, r in c9.head(6).iterrows():
        p, _ = get_primary_partner(r["match_id"], r["innings"], r["player"], df_deliveries)
        print(f"{r['player']} ({r['season']}, M{r['match_id']}) - Partner: {p} | Runs: {r['actual_runs']} ({r['balls_faced']}b, SR {r['actual_sr']:.1f}) | P3: {r['score_state']} | P2: {r['score_perf']} | C: {r['contribution_score']} | Won: 0")

    # 10. Won Match Despite Modest Individual Output (won_match == 1, actual_runs <= 25, score_perf <= 48, balls_faced >= 15)
    c10 = df[(df["won_match"] == 1) & (df["actual_runs"] <= 25) & (df["score_perf"] <= 48.0) & (df["balls_faced"] >= 15)].head(15)
    print("\n[Category 10: Won Match Despite Modest Output]")
    for _, r in c10.head(6).iterrows():
        p, _ = get_primary_partner(r["match_id"], r["innings"], r["player"], df_deliveries)
        print(f"{r['player']} ({r['season']}, M{r['match_id']}) - Partner: {p} | Runs: {r['actual_runs']} ({r['balls_faced']}b, SR {r['actual_sr']:.1f}) | P3: {r['score_state']} | P2: {r['score_perf']} | C: {r['contribution_score']} | Won: 1")


if __name__ == "__main__":
    find_cases()
