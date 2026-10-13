"""
Phase 7D Comprehensive Verification Script.

Executes:
1. API responses verification (/api/health, /api/players, /api/player/..., /api/match/..., /api/contribution/compare).
2. Player comparison with up to 5 players.
3. Strict DNB and NULL preservation verification.
4. Middle-over overlap verification.
5. Score distribution comparison: Old Model (Phase 6 25/25/25/25) vs New Model (Phase 7D 25/35/40).
6. Outcome leakage invariance check on production calculation.
"""

import json
from pathlib import Path
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from app.main import app
from src.contribution_framework import compute_production_contribution

client = TestClient(app)


def verify_all():
    print("============================================================")
    print("PHASE 7D PRODUCTION INTEGRATION VERIFICATION")
    print("============================================================")

    # 1. API Verification
    print("\n[Step 1/6] Verifying API Endpoints...")
    r_health = client.get("/api/health").json()
    assert r_health["status"] == "healthy"
    print("  [OK] /api/health: healthy")

    r_summary = client.get("/api/dashboard/summary?season=2016").json()
    assert r_summary["total_players"] > 0
    print(f"  [OK] /api/dashboard/summary: {r_summary['total_players']} players, avg score {r_summary['average_contribution_score']}")

    # Player profile
    r_kohli = client.get("/api/player/V%20Kohli/season/2016").json()
    assert r_kohli["average_contribution_score"] == 71.8
    assert r_kohli["season_team_contribution_share"] == 37.95
    assert r_kohli["context_breakdown"]["middle_over_contribution"] == 78.78
    print(f"  [OK] /api/player/V Kohli/season/2016: Score=71.8, Share=37.95%, Mid=78.78")

    # DNB player profile
    r_chahal = client.get("/api/player/YS%20Chahal/season/2016").json()
    assert r_chahal["average_contribution_score"] is None
    assert r_chahal["season_team_contribution_share"] is None
    assert r_chahal["did_not_bat_matches"] == 13
    assert r_chahal["batting_innings"] == 0
    print("  [OK] /api/player/YS Chahal/season/2016: Strict NULL preserved (DNB=13, Inns=0)")

    # Match detail
    r_match = client.get("/api/match/980907/player/V%20Kohli").json()
    assert r_match["contribution_score"] == 86.3
    assert r_match["pillars"]["pillar1_context"]["weight"] == "25%"
    assert r_match["pillars"]["pillar2_performance"]["weight"] == "35%"
    assert r_match["pillars"]["pillar3_state"]["weight"] == "40%"
    assert r_match["pillars"]["pillar4_cf"]["weight"] == "0% (Diagnostic Only)"
    assert "pillar4_diagnostic" in r_match
    print("  [OK] /api/match/980907/player/V Kohli: Score=86.3, P1=25%, P2=35%, P3=40%, P4=0% (Diagnostic)")

    # 2. Player Comparison with up to 5 players
    print("\n[Step 2/6] Verifying Player Comparison (up to 5 players)...")
    players_query = "V Kohli,AB de Villiers,DA Warner,KL Rahul,YS Chahal"
    r_comp = client.get(f"/api/contribution/compare?season=2016&players={players_query}").json()
    assert r_comp["players_count"] == 5
    print(f"  [OK] 5-Player comparison succeeded with {len(r_comp['players'])} players:")
    for p in r_comp["players"]:
        score_str = str(p["contribution_score"]) if p["contribution_score"] is not None else "None"
        share_str = f"{p['season_team_contribution_share']}%" if p["season_team_contribution_share"] is not None else "None"
        mid_str = str(p["context_breakdown"]["middle_over_contribution"]) if p["context_breakdown"]["middle_over_contribution"] is not None else "None"
        print(f"    - {p['player']}: Score={score_str}, Share={share_str}, Mid-Over={mid_str}, is_dnb={p['is_dnb']}")

    # Check boundaries (min 2, max 5)
    r_1 = client.get("/api/contribution/compare?season=2016&players=V%20Kohli")
    assert r_1.status_code == 400
    r_6 = client.get("/api/contribution/compare?season=2016&players=V%20Kohli,AB%20de%20Villiers,DA%20Warner,KL%20Rahul,YS%20Chahal,RG%20Sharma")
    assert r_6.status_code == 400
    print("  [OK] Rejection of 1 player and 6 players confirmed (valid range [2, 5]).")

    # 3. Middle-Over Overlap Verification
    print("\n[Step 3/6] Verifying Middle-Over Overlap Logic (entry < 16 AND exit >= 6)...")
    df_season = pd.read_csv("models/contribution/phase6/phase6_season_metrics.csv")
    openers_with_mid = [("V Kohli", "2016"), ("DA Warner", "2016"), ("JC Buttler", "2022"), ("Shubman Gill", "2023")]
    for op, season in openers_with_mid:
        sub = df_season[(df_season["player"] == op) & (df_season["season"].astype(str) == str(season))]
        val = sub.iloc[0]["middle_over_contribution"]
        assert pd.notnull(val) and val > 50.0
        print(f"  [OK] {op} ({season}): valid middle-over contribution = {val:.2f}")

    # Bowler without middle over
    bk = df_season[(df_season["player"] == "B Kumar") & (df_season["season"].astype(str) == "2016")].iloc[0]
    assert pd.isna(bk["middle_over_contribution"])
    print("  [OK] B Kumar 2016: middle-over contribution is strictly NULL (no middle-over stay)")

    # 4. Score Distribution Audit (Old Model vs New Model)
    print("\n[Step 4/6] Comparing Old vs New Score Distributions across 19,111 innings...")
    bmc_bak = pd.read_csv("data/processed/batter_match_contributions_v6_backup.csv", low_memory=False)
    bmc_prod = pd.read_csv("data/processed/batter_match_contributions.csv", low_memory=False)

    s_old = bmc_bak["contribution_score"].dropna()
    s_new = bmc_prod["contribution_score"].dropna()

    dist_stats = {
        "Old Model (25/25/25/25)": {
            "count": len(s_old),
            "mean": round(float(s_old.mean()), 2),
            "std": round(float(s_old.std()), 2),
            "median": round(float(s_old.median()), 2),
            "q10": round(float(s_old.quantile(0.10)), 2),
            "q25": round(float(s_old.quantile(0.25)), 2),
            "q75": round(float(s_old.quantile(0.75)), 2),
            "q90": round(float(s_old.quantile(0.90)), 2),
            "min": round(float(s_old.min()), 2),
            "max": round(float(s_old.max()), 2),
        },
        "New Model (25/35/40)": {
            "count": len(s_new),
            "mean": round(float(s_new.mean()), 2),
            "std": round(float(s_new.std()), 2),
            "median": round(float(s_new.median()), 2),
            "q10": round(float(s_new.quantile(0.10)), 2),
            "q25": round(float(s_new.quantile(0.25)), 2),
            "q75": round(float(s_new.quantile(0.75)), 2),
            "q90": round(float(s_new.quantile(0.90)), 2),
            "min": round(float(s_new.min()), 2),
            "max": round(float(s_new.max()), 2),
        },
        "correlation": round(float(s_old.corr(s_new)), 4)
    }

    print(f"  Old Model (25/25/25/25): Mean={dist_stats['Old Model (25/25/25/25)']['mean']}, Std={dist_stats['Old Model (25/25/25/25)']['std']}, Median={dist_stats['Old Model (25/25/25/25)']['median']}")
    print(f"  New Model (25/35/40):     Mean={dist_stats['New Model (25/35/40)']['mean']}, Std={dist_stats['New Model (25/35/40)']['std']}, Median={dist_stats['New Model (25/35/40)']['median']}")
    print(f"  Innings Correlation: r = {dist_stats['correlation']}")

    # Player-season distribution
    p6_bak = pd.read_csv("models/contribution/phase6/phase6_season_metrics_v6_backup.csv")
    p7_prod = pd.read_csv("models/contribution/phase6/phase6_season_metrics.csv")
    ps_old = p6_bak["average_contribution_score"].dropna()
    ps_new = p7_prod["average_contribution_score"].dropna()
    print(f"  Player-Season Correlation across {len(ps_old)} qualified profiles: r = {ps_old.corr(ps_new):.4f}")

    # 5. Outcome Leakage Invariance Audit
    print("\n[Step 5/6] Verifying Outcome Leakage Invariance on Production Model...")
    sample_rows = bmc_prod.head(200).to_dict(orient="records")
    diffs = []
    for r in sample_rows:
        orig_res = compute_production_contribution(r)
        
        # Invert match outcome fields
        r_inv = r.copy()
        r_inv["won_match"] = not bool(r.get("won_match", False))
        r_inv["winning_margin"] = -float(r.get("winning_margin", 10.0))
        r_inv["target_reached"] = not bool(r.get("target_reached", False))
        
        inv_res = compute_production_contribution(r_inv)
        if orig_res.get("contribution_score") is not None and inv_res.get("contribution_score") is not None:
            diffs.append(abs(orig_res["contribution_score"] - inv_res["contribution_score"]))

    max_shift = max(diffs) if diffs else 0.0
    assert max_shift == 0.0
    print(f"  [OK] Maximum score shift under match outcome inversion = {max_shift:.4f} (Zero outcome leakage)")

    # 6. Team Contribution Share Rectification
    print("\n[Step 6/6] Verifying Positive Attribution Formula Integrity...")
    # sum(max(0, player_c_raw)) / sum(max(0, team_c_raw)) * 100
    rcb_2016 = p7_prod[(p7_prod["team"] == "Royal Challengers Bangalore") & (p7_prod["season"].astype(str) == "2016")]
    pos_raw_sum = rcb_2016["total_positive_raw_contribution"].sum()
    share_sum = rcb_2016["season_team_contribution_share"].dropna().sum()
    assert 99.0 <= share_sum <= 101.0
    print(f"  [OK] RCB 2016 Team Share Sum = {share_sum:.2f}% (perfect roster positive attribution)")

    print("\n============================================================")
    print("ALL VERIFICATIONS COMPLETED SUCCESSFULLY!")
    print("============================================================")


if __name__ == "__main__":
    verify_all()
