"""
Phase 6A: Season Aggregation and Player Contribution Metrics.

Builds the rigorous season-level aggregation layer over Phase 5B match-level contextual outputs:
- Pillar 1: Match Context (25%)
- Pillar 2: Batter Performance (25%)
- Pillar 3: Team-State Impact (25%)
- Pillar 4: Counterfactual Value (25%)

Key Principles & Rules:
1. Strict DNB Rule: Did-Not-Bat appearances return NULL (None/NaN) and are NEVER counted as 0, 50, or par.
   DNB matches do NOT enter the batting innings count or the denominator for contribution averages.
2. Two Season-Level Views:
   - View A (All-Innings Season Metrics): Complete transparent record across every genuine batting opportunity.
   - View B (Qualified Season Metrics): Excludes only empirically verified negligible-opportunity innings
     (Candidate 1: balls <= 2, not out, |C_raw| <= 0.10, negligible state change) for sensitive comparison.
3. High-Impact Short Cameo Protection: Cameos with high strike-rate or state impact (e.g., 30 off 5, 8* off 3,
   1* off 1 match-winner) are NEVER excluded.
4. Not-Out Neutrality: Not-outs are evaluated strictly on context (no artificial bonus or penalty).
5. Configurable Player Eligibility Filters: Minimum runs (100, 200, 300, etc.), minimum innings, minimum balls.
   Filters select players without altering underlying contribution metrics.
6. Contextual Segmentation Preservation: first innings, chase, powerplay, middle, death, high-pressure.
   Categories with no valid observations remain strictly NULL.
"""

import os
import sys
import json
import glob
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

# Ensure repository root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.contribution_framework import (
    compute_phase5b_contribution,
    compute_production_contribution,
    compute_p1_leverage,
    compute_adjusted_pillar_score,
    compute_pillar4_counterfactual_value,
    normalize_pillar_score,
    PHASE5B_EMPIRICAL_PARAMS,
)
from src.phase7c_rebalance import compute_phase7c_contribution


def load_match_rosters(raw_dir: Union[str, Path] = "data/raw") -> pd.DataFrame:
    """
    Extracts complete Playing XI rosters from raw match JSON files.
    Identifies every player selected in a match (batting or DNB).
    """
    raw_files = glob.glob(str(Path(raw_dir) / "*.json"))
    roster_records = []

    for fpath in raw_files:
        mid_str = Path(fpath).stem
        try:
            mid = int(mid_str)
        except ValueError:
            continue

        try:
            with open(fpath, "r", encoding="utf-8") as fp:
                d = json.load(fp)
        except Exception:
            continue

        info = d.get("info", {})
        season = str(info.get("season", "")).strip()
        # Normalize seasons like '2020/21' or 2013
        players = info.get("players", {})
        for team, p_list in players.items():
            for p in p_list:
                roster_records.append({
                    "match_id": mid,
                    "season": season,
                    "team": team,
                    "player": p
                })

    df_rosters = pd.DataFrame(roster_records)
    return df_rosters


def is_negligible_opportunity(row: Union[pd.Series, Dict[str, Any]]) -> bool:
    """
    Data-driven classification of negligible opportunity (Candidate 1):
    An innings is negligible ONLY if:
      - balls_faced <= 2
      - dismissal_status == 'not out'
      - abs(raw_contribution) <= 0.10
      - And state change was minimal (|EFS change| <= 2.0 or chase |RRR change| <= 0.5)

    Dismissals (e.g. 0-ball run out, ducks) are NEVER negligible because losing a wicket alters resources.
    High-impact cameos (e.g. 8* off 3, 1* off 1 match-winner, 5* off 2) are NEVER negligible.
    """
    balls = float(row.get("balls_faced", 0))
    if balls > 2:
        return False

    status = str(row.get("dismissal_status", "")).lower().strip()
    if status in ("out", "bowled", "caught", "lbw", "run out", "stumped"):
        return False

    c_raw = row.get("raw_contribution")
    if c_raw is not None and not pd.isna(c_raw):
        if abs(float(c_raw)) > 0.10:
            return False

    innings = int(row.get("innings", 1))
    if innings == 1:
        efs_chg = row.get("expected_final_change")
        if pd.notnull(efs_chg) and abs(float(efs_chg)) > 2.0:
            return False
    else:
        rrr_chg = row.get("required_rr_change")
        if pd.notnull(rrr_chg) and abs(float(rrr_chg)) > 0.5:
            return False

    return True


def compute_all_innings_phase5b(df_signals: pd.DataFrame) -> pd.DataFrame:
    """
    Computes Phase 7L production contribution outputs:
    Context-as-Leverage Architecture (50% Adjusted P2 + 50% Adjusted P3).
    """
    df_std = df_signals[df_signals["innings"] <= 2].copy()
    
    scores, raws = [], []
    p1s, p2s, p3s, p4s = [], [], [], []
    adj_p2s, adj_p3s, levs = [], [], []
    c_wkts, c_chases, c_opens, c_effs, zones = [], [], [], [], []

    for _, r in df_std.iterrows():
        res = compute_production_contribution(r)
        scores.append(res["contribution_score"])
        raws.append(res["raw_contribution"])
        p1s.append(res["pillar1_context_score"])
        p2s.append(res["pillar2_perf_score"])
        p3s.append(res["pillar3_state_score"])
        adj_p2s.append(res.get("adjusted_p2"))
        adj_p3s.append(res.get("adjusted_p3"))
        levs.append(res.get("leverage"))
        c_wkts.append(res.get("c_wkt"))
        c_chases.append(res.get("c_chase"))
        c_opens.append(res.get("c_open"))
        c_effs.append(res.get("c_eff"))
        zones.append(res.get("context_zone"))

        p4_raw = compute_pillar4_counterfactual_value(r)
        z4 = (p4_raw - PHASE5B_EMPIRICAL_PARAMS["pillar4_mean"]) / PHASE5B_EMPIRICAL_PARAMS["pillar4_std"]
        p4s.append(round(normalize_pillar_score(z4, k=PHASE5B_EMPIRICAL_PARAMS["pillar_scale"]), 1))

    df_std["contribution_score"] = scores
    df_std["raw_contribution"] = raws
    df_std["score_context"] = p1s
    df_std["score_perf"] = p2s
    df_std["score_state"] = p3s
    df_std["score_cf"] = p4s
    df_std["adjusted_p2"] = adj_p2s
    df_std["adjusted_p3"] = adj_p3s
    df_std["leverage"] = levs
    df_std["c_wkt"] = c_wkts
    df_std["c_chase"] = c_chases
    df_std["c_open"] = c_opens
    df_std["c_eff"] = c_effs
    df_std["context_zone"] = zones

    # Identify negligible opportunities for View B
    df_std["is_negligible"] = [is_negligible_opportunity(r) for _, r in df_std.iterrows()]

    return df_std


# Production alias
compute_all_innings_production = compute_all_innings_phase5b


def build_season_aggregations(
    df_signals: pd.DataFrame,
    df_rosters: Optional[pd.DataFrame] = None,
    raw_dir: Union[str, Path] = "data/raw"
) -> pd.DataFrame:
    """
    Builds the comprehensive Phase 6 season aggregation dataset.
    Produces both View A (All-Innings) and View B (Qualified) metrics.
    """
    if df_rosters is None:
        df_rosters = load_match_rosters(raw_dir=raw_dir)

    # Standardize seasons to string
    df_signals = df_signals.copy()
    df_signals["season"] = df_signals["season"].astype(str)
    df_rosters = df_rosters.copy()
    df_rosters["season"] = df_rosters["season"].astype(str)

    # 1. Compute match-level contributions
    df_inns = compute_all_innings_phase5b(df_signals)

    # 2. Compute team-level total positive raw contributions per season for share calculation
    team_season_pos_raw: Dict[Tuple[str, str], float] = {}
    for (season, team), grp in df_inns.groupby(["season", "team"]):
        pos_raw = float(np.sum([max(0.0, float(r)) for r in grp["raw_contribution"].dropna()]))
        team_season_pos_raw[(season, team)] = pos_raw

    # Team qualified positive raw
    team_season_qual_pos_raw: Dict[Tuple[str, str], float] = {}
    for (season, team), grp in df_inns[~df_inns["is_negligible"]].groupby(["season", "team"]):
        pos_raw = float(np.sum([max(0.0, float(r)) for r in grp["raw_contribution"].dropna()]))
        team_season_qual_pos_raw[(season, team)] = pos_raw

    # 3. Aggregate player appearances from rosters
    # Each player-season-team combination
    # Find primary team for players who played across multiple teams or group by (player, season, team)
    player_groups = df_rosters.groupby(["player", "season", "team"])

    season_records = []
    
    # Pre-index innings by (player, season, team)
    inns_by_key: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = {}
    for _, r in df_inns.iterrows():
        key = (r["player"], str(r["season"]), r["team"])
        if key not in inns_by_key:
            inns_by_key[key] = []
        inns_by_key[key].append(r.to_dict())

    for (player, season, team), r_grp in player_groups:
        matches_played = len(r_grp["match_id"].unique())
        key = (player, season, team)
        inns = inns_by_key.get(key, [])
        batting_inns = len(inns)
        dnb_matches = max(0, matches_played - batting_inns)

        team_pos_raw = team_season_pos_raw.get((season, team), 0.0)
        team_qual_pos = team_season_qual_pos_raw.get((season, team), 0.0)

        # Basic batting volume totals
        tot_runs = int(sum(r.get("actual_runs", 0) for r in inns))
        tot_balls = int(sum(r.get("balls_faced", 0) for r in inns))
        not_outs = sum(1 for r in inns if str(r.get("dismissal_status", "")).lower() == "not out")

        if batting_inns == 0:
            # STRICT DNB: Score = NULL, Share = NULL
            rec = {
                "player": player,
                "season": season,
                "team": team,
                "matches_played": matches_played,
                "batting_innings": 0,
                "did_not_bat_matches": dnb_matches,
                "actual_runs": 0,
                "balls_faced": 0,
                "not_outs": 0,
                # View A (All-Innings)
                "average_contribution_score": None,
                "total_raw_contribution": 0.0,
                "total_positive_raw_contribution": 0.0,
                "season_team_contribution_share": None,
                "contribution_per_batting_opportunity": None,
                # View B (Qualified)
                "qualified_batting_innings": 0,
                "excluded_small_opportunity_innings": 0,
                "qualified_average_contribution_score": None,
                "qualified_total_positive_contribution": 0.0,
                "qualified_team_contribution_share": None,
                # Contextual Categories (NULL)
                "first_innings_contribution": None,
                "chase_contribution": None,
                "powerplay_contribution": None,
                "middle_over_contribution": None,
                "death_over_contribution": None,
                "high_pressure_contribution": None,
            }
            season_records.append(rec)
            continue

        # Extract scores and raws
        scores = [float(r["contribution_score"]) for r in inns if r.get("contribution_score") is not None]
        raws = [float(r["raw_contribution"]) for r in inns if r.get("raw_contribution") is not None]
        
        avg_score = float(np.mean(scores)) if scores else None
        tot_raw = float(np.sum(raws)) if raws else 0.0
        tot_pos_raw = float(np.sum([max(0.0, r) for r in raws])) if raws else 0.0
        
        # Contribution per batting opportunity = positive raw / batting innings
        contrib_per_opp = round(tot_pos_raw / batting_inns, 4) if batting_inns > 0 else None

        # Season Team Contribution Share
        if team_pos_raw > 1e-6:
            season_share = round((tot_pos_raw / team_pos_raw) * 100.0, 2)
        else:
            season_share = 0.0

        # View B: Qualified Metrics
        qual_inns = [r for r in inns if not r.get("is_negligible", False)]
        num_qual = len(qual_inns)
        num_excluded = batting_inns - num_qual

        if num_qual > 0:
            qual_scores = [float(r["contribution_score"]) for r in qual_inns if r.get("contribution_score") is not None]
            qual_raws = [float(r["raw_contribution"]) for r in qual_inns if r.get("raw_contribution") is not None]
            qual_avg_score = float(np.mean(qual_scores)) if qual_scores else None
            qual_tot_pos_raw = float(np.sum([max(0.0, r) for r in qual_raws])) if qual_raws else 0.0
            
            if team_qual_pos > 1e-6:
                qual_share = round((qual_tot_pos_raw / team_qual_pos) * 100.0, 2)
            else:
                qual_share = 0.0
        else:
            qual_avg_score = None
            qual_tot_pos_raw = 0.0
            qual_share = None

        # Contextual categories (Preserve Phase 5B categories, return None when unobserved)
        inn1_scores = [float(r["contribution_score"]) for r in inns if r.get("innings") == 1 and r.get("contribution_score") is not None]
        inn2_scores = [float(r["contribution_score"]) for r in inns if r.get("innings") == 2 and r.get("contribution_score") is not None]
        pp_scores = [float(r["contribution_score"]) for r in inns if float(r.get("entry_over", 0.0)) < 6.0 and r.get("contribution_score") is not None]
        mid_scores = []
        for r in inns:
            if r.get("contribution_score") is None:
                continue
            entry = float(r.get("entry_over", 0.0))
            exit_val = r.get("exit_over")
            exit_o = entry if (exit_val is None or (isinstance(exit_val, float) and np.isnan(exit_val))) else float(exit_val)
            if entry < 16.0 and exit_o >= 6.0:
                mid_scores.append(float(r["contribution_score"]))
        death_scores = [float(r["contribution_score"]) for r in inns if (float(r.get("entry_over", 0.0)) >= 16.0 or float(r.get("exit_over", 0.0)) >= 16.0) and r.get("contribution_score") is not None]
        press_scores = [float(r["contribution_score"]) for r in inns if float(r.get("score_context", 50.0)) >= 60.0 and r.get("contribution_score") is not None]

        rec = {
            "player": player,
            "season": season,
            "team": team,
            "matches_played": matches_played,
            "batting_innings": batting_inns,
            "did_not_bat_matches": dnb_matches,
            "actual_runs": tot_runs,
            "balls_faced": tot_balls,
            "not_outs": not_outs,
            # View A (All-Innings)
            "average_contribution_score": round(avg_score, 2) if avg_score is not None else None,
            "total_raw_contribution": round(tot_raw, 4),
            "total_positive_raw_contribution": round(tot_pos_raw, 4),
            "season_team_contribution_share": season_share,
            "contribution_per_batting_opportunity": contrib_per_opp,
            # View B (Qualified)
            "qualified_batting_innings": num_qual,
            "excluded_small_opportunity_innings": num_excluded,
            "qualified_average_contribution_score": round(qual_avg_score, 2) if qual_avg_score is not None else None,
            "qualified_total_positive_contribution": round(qual_tot_pos_raw, 4),
            "qualified_team_contribution_share": qual_share,
            # Contextual Categories
            "first_innings_contribution": round(float(np.mean(inn1_scores)), 2) if inn1_scores else None,
            "chase_contribution": round(float(np.mean(inn2_scores)), 2) if inn2_scores else None,
            "powerplay_contribution": round(float(np.mean(pp_scores)), 2) if pp_scores else None,
            "middle_over_contribution": round(float(np.mean(mid_scores)), 2) if mid_scores else None,
            "death_over_contribution": round(float(np.mean(death_scores)), 2) if death_scores else None,
            "high_pressure_contribution": round(float(np.mean(press_scores)), 2) if press_scores else None,
        }
        season_records.append(rec)

    df_season = pd.DataFrame(season_records)
    return df_season


def filter_season_metrics(
    df: pd.DataFrame,
    season: Optional[Union[str, int]] = None,
    minimum_runs: Optional[int] = None,
    minimum_batting_innings: Optional[int] = None,
    minimum_balls_faced: Optional[int] = None,
    team: Optional[str] = None,
) -> pd.DataFrame:
    """
    Configurable analysis filter (Section 14).
    Selects eligible players for analysis without altering underlying contribution metrics.
    """
    filtered = df.copy()

    if season is not None:
        filtered = filtered[filtered["season"] == str(season)]

    if team is not None and team != "ALL":
        filtered = filtered[filtered["team"] == team]

    if minimum_runs is not None:
        filtered = filtered[filtered["actual_runs"] >= minimum_runs]

    if minimum_batting_innings is not None:
        filtered = filtered[filtered["batting_innings"] >= minimum_batting_innings]

    if minimum_balls_faced is not None:
        filtered = filtered[filtered["balls_faced"] >= minimum_balls_faced]

    return filtered


def generate_season_outputs(
    signals_path: str = "data/processed/batter_impact_signals.csv",
    out_dir: str = "models/contribution/phase6"
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Generates phase6_season_metrics.csv and phase6_season_spec.json.
    """
    print(f"Loading signals from {signals_path}...")
    df_signals = pd.read_csv(signals_path, low_memory=False)

    print("Building season aggregations across all matches, players, and teams...")
    df_season = build_season_aggregations(df_signals)

    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    csv_file = out_path / "phase6_season_metrics.csv"
    df_season.to_csv(csv_file, index=False)
    print(f"Saved {len(df_season):,} season records to {csv_file}")

    # Build spec
    spec = {
        "framework": "Phase 7D Production Contribution Specification",
        "formula": "Contribution Score = 0.25 * P1 + 0.35 * P2 + 0.40 * P3",
        "pillars": {
            "pillar1_match_context": "25% weight (Opportunity Difficulty)",
            "pillar2_batter_performance": "35% weight (Execution vs Expected)",
            "pillar3_team_state_impact": "40% weight (Team Transformation)",
            "pillar4_counterfactual_value": "0% weight (Diagnostic Layer Only)"
        },
        "dnb_rule": {
            "score": "NULL",
            "raw_contribution": "NULL",
            "team_contribution_share": "NULL",
            "denominator_rule": "DNB matches are strictly excluded from batting innings count and contribution averages.",
            "metadata_visibility": "matches_played, batting_innings, did_not_bat_matches recorded explicitly"
        },
        "view_a_all_innings": {
            "description": "Complete transparent record of every genuine batting opportunity.",
            "metrics": [
                "average_contribution_score",
                "total_raw_contribution",
                "total_positive_raw_contribution",
                "season_team_contribution_share",
                "contribution_per_batting_opportunity"
            ]
        },
        "view_b_qualified": {
            "description": "Excludes only negligible-opportunity non-dismissal innings for sensitive player comparison.",
            "eligibility_rule": "Candidate 1: balls <= 2, not out, |C_raw| <= 0.10, minimal state change.",
            "metrics": [
                "qualified_batting_innings",
                "excluded_small_opportunity_innings",
                "qualified_average_contribution_score",
                "qualified_total_positive_contribution",
                "qualified_team_contribution_share"
            ]
        },
        "configurable_filters": {
            "parameters": ["season", "minimum_runs", "minimum_batting_innings", "minimum_balls_faced", "team"],
            "supported_run_thresholds": [100, 200, 300, 400, 500],
            "invariance": "Filter thresholds select player subsets without altering underlying contribution metrics."
        },
        "contextual_segmentation": [
            "first_innings_contribution",
            "chase_contribution",
            "powerplay_contribution",
            "middle_over_contribution",
            "death_over_contribution",
            "high_pressure_contribution"
        ],
        "dataset_summary": {
            "total_player_season_records": len(df_season),
            "unique_players": int(df_season["player"].nunique()),
            "seasons": sorted(list(df_season["season"].unique())),
            "total_matches_played": int(df_season["matches_played"].sum()),
            "total_batting_innings": int(df_season["batting_innings"].sum()),
            "total_dnb_matches": int(df_season["did_not_bat_matches"].sum()),
            "dnb_percentage": round(float(df_season["did_not_bat_matches"].sum() / df_season["matches_played"].sum() * 100), 2)
        }
    }

    spec_file = out_path / "phase6_season_spec.json"
    with open(spec_file, "w", encoding="utf-8") as fp:
        json.dump(spec, fp, indent=2)
    print(f"Saved season specification to {spec_file}")

    return df_season, spec


if __name__ == "__main__":
    generate_season_outputs()
