"""
Phase 7L: Production Pipeline Data Regeneration Script.
Regenerates:
1. data/processed/batter_match_contributions.csv
2. models/contribution/phase6/phase6_season_metrics.csv
"""

import time
import shutil
import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.contribution_framework import compute_production_contribution
from src.season_aggregation import (
    is_negligible_opportunity,
    build_season_aggregations,
    load_match_rosters,
)


def regenerate_match_contributions(
    input_path: str = "data/processed/batter_match_contributions.csv",
    output_path: str = "data/processed/batter_match_contributions.csv",
) -> pd.DataFrame:
    print(f"[Phase 7L] Loading match dataset from {input_path}...")
    df = pd.read_csv(input_path, low_memory=False)
    n_rows = len(df)
    print(f"[Phase 7L] Loaded {n_rows:,} rows.")

    scores = []
    raws = []
    p1s = []
    p2s = []
    p3s = []
    adj_p2s = []
    adj_p3s = []
    levs = []
    c_wkts = []
    c_chases = []
    c_opens = []
    c_effs = []
    zones = []

    t0 = time.time()
    for idx, r in df.iterrows():
        res = compute_production_contribution(r)
        scores.append(res["contribution_score"])
        raws.append(res["raw_contribution"])
        p1s.append(res["pillar1_context_score"])
        p2s.append(res["pillar2_perf_score"])
        p3s.append(res["pillar3_state_score"])
        adj_p2s.append(res["adjusted_p2"])
        adj_p3s.append(res["adjusted_p3"])
        levs.append(res["leverage"])
        c_wkts.append(res["c_wkt"])
        c_chases.append(res["c_chase"])
        c_opens.append(res["c_open"])
        c_effs.append(res["c_eff"])
        zones.append(res["context_zone"])

    df["contribution_score"] = scores
    df["raw_contribution"] = raws
    df["score_context"] = p1s
    df["score_perf"] = p2s
    df["score_state"] = p3s
    df["adjusted_p2"] = adj_p2s
    df["adjusted_p3"] = adj_p3s
    df["leverage"] = levs
    df["c_wkt"] = c_wkts
    df["c_chase"] = c_chases
    df["c_open"] = c_opens
    df["c_eff"] = c_effs
    df["context_zone"] = zones

    # Re-evaluate is_negligible with updated raw contributions
    is_neg = [is_negligible_opportunity(r) for _, r in df.iterrows()]
    df["is_negligible"] = is_neg

    t1 = time.time()
    print(f"[Phase 7L] Computed all production scores in {t1 - t0:.2f}s.")

    # Data Integrity Checks
    assert len(df) == n_rows, f"Row count changed: {len(df)} vs {n_rows}"
    assert df["contribution_score"].notnull().all(), "Found NULL contribution_score in batting innings!"
    assert (df["contribution_score"] >= 0.1).all() and (df["contribution_score"] <= 99.9).all(), "Scores out of bounds [0.1, 99.9]"
    assert not df.duplicated(subset=["match_id", "innings", "player"]).any(), "Found duplicate batter-match rows!"

    # Save regenerated file
    df.to_csv(output_path, index=False)
    print(f"[Phase 7L] Successfully saved regenerated match dataset to {output_path}")
    return df


def regenerate_season_metrics(
    df_signals: pd.DataFrame,
    output_path: str = "models/contribution/phase6/phase6_season_metrics.csv",
    raw_dir: str = "data/raw",
) -> pd.DataFrame:
    print(f"[Phase 7L] Building season aggregations from updated match contributions...")
    t0 = time.time()
    df_rosters = load_match_rosters(raw_dir=raw_dir)
    print(f"[Phase 7L] Loaded {len(df_rosters):,} roster entries.")

    df_season = build_season_aggregations(df_signals, df_rosters=df_rosters, raw_dir=raw_dir)
    t1 = time.time()
    print(f"[Phase 7L] Built season aggregations for {len(df_season):,} player-seasons in {t1 - t0:.2f}s.")

    # Data Integrity Checks
    assert "average_contribution_score" in df_season.columns
    assert "season_team_contribution_share" in df_season.columns

    # Verify DNB rule: player with 0 batting innings must have NULL average score
    dnb_players = df_season[df_season["batting_innings"] == 0]
    assert len(dnb_players) > 0, "Expected DNB player-seasons"
    assert dnb_players["average_contribution_score"].isna().all(), "DNB players must have NaN/NULL average score"
    assert dnb_players["season_team_contribution_share"].isna().all(), "DNB players must have NaN/NULL season share"

    # Save regenerated season metrics
    df_season.to_csv(output_path, index=False)
    print(f"[Phase 7L] Successfully saved regenerated season metrics to {output_path}")
    return df_season


if __name__ == "__main__":
    print("[Phase 7L] Starting production pipeline regeneration...")
    df_bmc = regenerate_match_contributions()
    df_season = regenerate_season_metrics(df_bmc)
    print("[Phase 7L] Production pipeline regeneration complete.")
