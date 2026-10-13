import sys
sys.path.insert(0, '.')
import pandas as pd
import numpy as np

from src.contribution_framework import compute_pillar1_match_context, PHASE5B_EMPIRICAL_PARAMS, normalize_pillar_score

df = pd.read_csv('data/processed/batter_match_contributions.csv', low_memory=False)

p = PHASE5B_EMPIRICAL_PARAMS

# Filter standard innings
df_eval = df[df['innings'] <= 2].copy()

from src.contribution_framework import compute_production_contribution

p1_new_scores = []
cs_new_scores = []

for idx, row in df_eval.iterrows():
    r = row.to_dict()
    res = compute_production_contribution(r)
    p1_new_scores.append(res['pillar1_context_score'])
    cs_new_scores.append(res['contribution_score'])

df_eval['p1_after'] = p1_new_scores
df_eval['cs_after'] = cs_new_scores
df_eval['p1_before'] = df_eval['score_context']
df_eval['cs_before'] = df_eval['contribution_score']
df_eval['p1_diff'] = df_eval['p1_after'] - df_eval['p1_before']
df_eval['cs_diff'] = df_eval['cs_after'] - df_eval['cs_before']

# Verify post-4.0 overs invariance
post_4 = df_eval[df_eval['entry_over'] > 4.0]
max_p1_post4 = post_4['p1_diff'].abs().max()
max_cs_post4 = post_4['cs_diff'].abs().max()
print(f"Post-4.0 overs count: {len(post_4)}")
print(f"Max abs P1 diff (entry_over > 4.0): {max_p1_post4:.4f}")
print(f"Max abs CS diff (entry_over > 4.0): {max_cs_post4:.4f}")

# Early-overs analysis
early = df_eval[df_eval['entry_over'] <= 4.0]
changed_mask = early['cs_diff'] != 0.0

print(f"\n--- Early-Over Window (entry_over <= 4.0) ---")
print(f"Total early-over innings: {len(early)}")
print(f"Innings affected: {changed_mask.sum()} ({changed_mask.sum() / len(early) * 100:.2f}%)")
print(f"Mean CS change: {early['cs_diff'].mean():+.3f}")
print(f"Median CS change: {early['cs_diff'].median():+.3f}")
print(f"Min CS change: {early['cs_diff'].min():+.1f}")
print(f"Max CS change: {early['cs_diff'].max():+.1f}")

# Overall dataset
total_changed = (df_eval['cs_diff'] != 0.0).sum()
print(f"\n--- Overall Dataset ---")
print(f"Total standard innings: {len(df_eval)}")
print(f"Total innings affected: {total_changed} ({total_changed / len(df_eval) * 100:.2f}%)")
print(f"Overall Mean CS change: {df_eval['cs_diff'].mean():+.3f}")
print(f"Overall Median CS change: {df_eval['cs_diff'].median():+.3f}")

cols = ['player', 'season', 'innings', 'entry_over', 'wickets_remaining_entry', 'team_rr_entry', 'p1_before', 'p1_after', 'cs_before', 'cs_after', 'cs_diff']

print("\n--- Top 5 Positive Score Changes (Early collapse recognized) ---")
print(early.sort_values(by='cs_diff', ascending=False)[cols].head(5).to_string(index=False))

print("\n--- Top 5 Negative Score Changes (Artificial pre-entry RR removed) ---")
print(early.sort_values(by='cs_diff', ascending=True)[cols].head(5).to_string(index=False))

print("\n--- Standard Opening Batters (Entry 0.0 to 0.3, 0 wickets down) ---")
openers = early[(early['entry_over'] <= 0.3) & (early['wickets_remaining_entry'] == 10)]
print(openers[cols].head(5).to_string(index=False))
