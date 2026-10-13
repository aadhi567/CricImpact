"""
Print summary of Phase 7F results.
"""
import json

with open("models/contribution/phase7/phase7f_leverage_validation.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print("--- Distribution Comparison ---")
for k, v in data["distribution_comparison"].items():
    print(f"{k}: mean={v['mean']}, median={v['median']}, std={v['std']}, q10={v['q10']}, q90={v['q90']}, corr_curr={v.get('corr_with_current_production')}")

print("\n--- P2/P3 Independence ---")
for k, v in data["p2_p3_independence"].items():
    print(f"  {k}: {v}")

print("\n--- Step 6 Cases A-E ---")
for c in data["step6_specific_cases"]:
    print(f"{c['id']}: {c['title']}")
    print(f"   P1={c['p1']}, P2={c['p2']}, P3={c['p3']} -> Curr(25/35/40)={c['current_score_25_35_40']}, Lev={c['leverage']} -> Cand={c['candidate_score']} (Diff={c['diff']:+0.1f})")

print("\n--- Player Ranking Stability ---")
print("Rank correlation (Spearman):", data["player_rankings_stability"]["player_rank_correlation_spearman"])
print("Pearson correlation:", data["player_rankings_stability"]["player_correlation_pearson"])
print("\nTop 10 players comparison:")
for p in data["player_rankings_stability"]["top25_comparison"][:10]:
    print(f"  {p['player']}: curr={p['curr_avg']} (rank {p['curr_rank']}) -> cand={p['cand_avg']} (rank {p['cand_rank']}), shift={p['rank_shift']:+d}")
