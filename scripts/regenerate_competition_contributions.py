"""
Phase 8C: Controlled Regeneration of Competition Contributions (T20I and SMAT).
Applies the verified canonical required_rr_change = required_rr_entry - required_rr_exit,
re-computes production contribution scores via compute_production_contribution(),
and rebuilds season aggregations while preserving all match and player identifiers.
"""

import sys
import time
from pathlib import Path
from typing import List, Optional

import pandas as pd
import numpy as np

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.contribution_framework import compute_production_contribution
from src.season_aggregation import (
    is_negligible_opportunity,
    build_season_aggregations,
)


def regenerate_partition(
    competition: str,
    base_dir: Optional[Path] = None,
) -> None:
    t0 = time.time()
    comp_dir = (base_dir or Path("data/processed")) / competition
    if not comp_dir.exists():
        raise FileNotFoundError(f"Partition directory not found: {comp_dir}")

    batters_csv = comp_dir / "batter_match_contributions.csv"
    rosters_csv = comp_dir / "match_rosters.csv"
    season_csv = comp_dir / "phase6_season_metrics.csv"

    print(f"\n=======================================================")
    print(f"Phase 8C Controlled Regeneration for: {competition.upper()}")
    print(f"Partition Directory: {comp_dir}")
    print(f"=======================================================")

    df = pd.read_csv(batters_csv, low_memory=False)
    n_rows = len(df)
    print(f"Loaded {n_rows:,} batting records from {batters_csv}")

    # Verify input integrity
    assert "required_rr_entry" in df.columns
    assert "required_rr_exit" in df.columns
    assert "required_rr_change" in df.columns

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

    # Apply canonical sign convention and recompute production scores
    for idx, r in df.iterrows():
        r_dict = dict(r)
        innings = int(r_dict.get("innings", 1))
        target = r_dict.get("target")

        if innings == 2 and pd.notnull(target) and float(target) > 0:
            rin = float(r_dict.get("required_rr_entry", 9.0))
            rout = float(r_dict.get("required_rr_exit", 0.0))
            # Canonical: entry - exit (positive = relief)
            rchg = round(rin - rout, 2)
            r_dict["required_rr_change"] = rchg
            r_dict["rr_gap_change"] = rchg
            r_dict["chase_pressure_relief_rr"] = rchg
            df.at[idx, "required_rr_change"] = rchg
            df.at[idx, "rr_gap_change"] = rchg
            if "chase_pressure_relief_rr" in df.columns:
                df.at[idx, "chase_pressure_relief_rr"] = rchg

        # Compute production score with Phase 7U attribution enabled
        res = compute_production_contribution(r_dict, apply_attribution=True)

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

    if "score_cf" not in df.columns:
        df["score_cf"] = 50.0

    # Re-evaluate is_negligible
    if "is_negligible" in df.columns:
        is_neg = [is_negligible_opportunity(r) for _, r in df.iterrows()]
        df["is_negligible"] = is_neg

    # Integrity verification before writing
    assert len(df) == n_rows, f"Row count mismatch: {len(df)} vs {n_rows}"
    valid_scores = df["contribution_score"].dropna()
    assert (valid_scores >= 0.1).all() and (valid_scores <= 99.9).all(), "Score bounds violated [0.1, 99.9]!"
    assert not df.duplicated(subset=["match_id", "innings", "player"]).any(), "Duplicate batter rows found!"

    # Save regenerated contributions
    df.to_csv(batters_csv, index=False)
    print(f"Saved regenerated {batters_csv} ({len(df):,} rows)")

    # Recompute season aggregations
    if rosters_csv.exists():
        print(f"Building season metrics using rosters from {rosters_csv}...")
        df_rosters = pd.read_csv(rosters_csv, low_memory=False)
        t_s0 = time.time()
        df_season = build_season_aggregations(df, df_rosters=df_rosters)
        
        # Verify DNB rule
        dnb_players = df_season[df_season["batting_innings"] == 0]
        if len(dnb_players) > 0:
            assert dnb_players["average_contribution_score"].isna().all(), "DNB players must have NULL average score!"
            assert dnb_players["season_team_contribution_share"].isna().all(), "DNB players must have NULL team share!"
            print(f"Verified DNB rule: {len(dnb_players)} non-batting player-seasons have NaN scores.")

        df_season.to_csv(season_csv, index=False)
        print(f"Saved {season_csv} ({len(df_season):,} player-seasons in {time.time() - t_s0:.2f}s)")

    print(f"Partition {competition.upper()} completed in {time.time() - t0:.2f}s.")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Phase 8C Competition Regeneration")
    parser.add_argument("--competition", choices=["t20i", "smat", "all"], default="all")
    args = parser.parse_args()

    comps = ["smat", "t20i"] if args.competition == "all" else [args.competition]
    for c in comps:
        regenerate_partition(c)


if __name__ == "__main__":
    main()
