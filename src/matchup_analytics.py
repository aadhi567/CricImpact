"""
Batter vs Bowling Type Matchup Analytics Engine.

Calculates batting performance against:
1. Pace
2. Spin

Metrics:
- Legal Balls Faced (excluding wides and no-balls)
- Batter Runs
- Strike Rate = (Runs / Balls Faced) * 100

Minimum Sample Rule:
- Balls Faced >= 100 OR Runs >= 80

IMPORTANT: This is an independent cricket analytics feature.
It does NOT modify Contribution Score, P1, P2, P3, C_RAW,
season aggregation, or any existing contribution calculations.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np

from src.bowling_classification import get_bowler_classification

_ROOT_DIR = Path(__file__).resolve().parent.parent
_DELIVERIES_CSV = _ROOT_DIR / "data" / "processed" / "deliveries.csv"

_PRECOMPUTED_MATCHUPS_DF: Optional[pd.DataFrame] = None


def load_deliveries_with_bowling_type(deliveries_path: Optional[Path] = None) -> pd.DataFrame:
    """
    Loads deliveries and annotates each delivery with bowling_type ('Pace' or 'Spin')
    and is_legal (True if not wide and not no-ball).
    """
    path = deliveries_path or _DELIVERIES_CSV
    if not path.exists():
        raise FileNotFoundError(f"Deliveries dataset not found at {path}")

    # Only load columns needed for matchup analytics
    cols = [
        "match_id", "season", "innings_number", "over", "ball",
        "batting_team", "bowling_team", "batter", "bowler",
        "batter_runs", "wides", "noballs"
    ]
    df = pd.read_csv(path, usecols=cols, dtype={"season": str}, low_memory=False)

    bowler_map = get_bowler_classification()
    df["bowling_type"] = df["bowler"].map(bowler_map).fillna("Pace")
    df["is_legal"] = (df["wides"] == 0) & (df["noballs"] == 0)
    return df


def get_annotated_deliveries() -> pd.DataFrame:
    """Singleton getter for deliveries with bowling type."""
    global _PRECOMPUTED_MATCHUPS_DF
    if _PRECOMPUTED_MATCHUPS_DF is None:
        _PRECOMPUTED_MATCHUPS_DF = load_deliveries_with_bowling_type()
    return _PRECOMPUTED_MATCHUPS_DF


def compute_matchup_rankings(
    season: Optional[str] = None,
    team: Optional[str] = None,
    bowling_type: Optional[str] = None,  # "Pace", "Spin", or None (both)
    min_balls: int = 100,
    min_runs: int = 80,
    deliveries_df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """
    Computes top batters vs Pace and vs Spin.

    Eligibility Rule:
        Balls Faced >= min_balls OR Runs >= min_runs

    Sort:
        Descending by Strike Rate.
    """
    df = deliveries_df if deliveries_df is not None else get_annotated_deliveries()

    # Apply filters
    filtered_df = df
    if season and str(season).lower() not in ("all", "all seasons", "none"):
        filtered_df = filtered_df[filtered_df["season"] == str(season)]
    if team and str(team).lower() not in ("all", "all teams", "none"):
        filtered_df = filtered_df[filtered_df["batting_team"] == team]

    # Target bowling types to calculate
    b_types = []
    if bowling_type and bowling_type.lower() in ("pace", "spin"):
        b_types = [bowling_type.capitalize()]
    else:
        b_types = ["Pace", "Spin"]

    results = {}
    for bt in b_types:
        bt_df = filtered_df[filtered_df["bowling_type"] == bt]
        
        # 1. Batter runs
        runs_series = bt_df.groupby("batter")["batter_runs"].sum()
        
        # 2. Legal balls faced (no wides, no no-balls)
        legal_df = bt_df[bt_df["is_legal"]]
        balls_series = legal_df.groupby("batter").size()

        # Combine into DataFrame
        all_batters = sorted(list(set(runs_series.index).union(set(balls_series.index))))
        stat_df = pd.DataFrame({
            "batter": all_batters,
            "runs": [int(runs_series.get(b, 0)) for b in all_batters],
            "balls": [int(balls_series.get(b, 0)) for b in all_batters],
        })

        # Calculate SR (avoid div by zero)
        stat_df["strike_rate"] = np.where(
            stat_df["balls"] > 0,
            np.round((stat_df["runs"] / stat_df["balls"]) * 100.0, 1),
            0.0
        )

        # 4. Minimum sample rule
        eligible_mask = (stat_df["balls"] >= min_balls) | (stat_df["runs"] >= min_runs)
        stat_df["is_eligible"] = eligible_mask

        # Filter to eligible
        qualified_df = stat_df[stat_df["is_eligible"]].copy()

        # 5. Sort by SR descending, with runs descending and balls ascending as tie-breakers
        qualified_df = qualified_df.sort_values(
            by=["strike_rate", "runs", "balls"],
            ascending=[False, False, True]
        ).reset_index(drop=True)

        # 6. Assign rank
        qualified_df["rank"] = range(1, len(qualified_df) + 1)

        records = qualified_df.to_dict(orient="records")
        results[bt.lower()] = {
            "bowling_type": bt,
            "rankings": records,
            "total_eligible": len(records),
            "total_batters_observed": len(stat_df),
        }

    return {
        "filters": {
            "season": season or "All Seasons",
            "team": team or "All Teams",
            "min_balls": min_balls,
            "min_runs": min_runs,
            "eligibility_rule": f"Minimum sample: {min_balls} balls or {min_runs} runs.",
        },
        "results": results,
    }


def get_batter_matchup_detail(
    batter: str,
    season: Optional[str] = None,
    team: Optional[str] = None,
    deliveries_df: Optional[pd.DataFrame] = None,
) -> Optional[Dict[str, Any]]:
    """
    Returns matchup breakdown (Pace vs Spin) for a specific batter.
    Includes difference in SR, runs, and balls.
    """
    df = deliveries_df if deliveries_df is not None else get_annotated_deliveries()
    
    b_df = df[df["batter"] == batter]
    if b_df.empty:
        return None

    if season and str(season).lower() not in ("all", "all seasons", "none"):
        b_df = b_df[b_df["season"] == str(season)]
    if team and str(team).lower() not in ("all", "all teams", "none"):
        b_df = b_df[b_df["batting_team"] == team]

    if b_df.empty:
        return None

    def _stats_for(b_type: str) -> Dict[str, Any]:
        sub = b_df[b_df["bowling_type"] == b_type]
        runs = int(sub["batter_runs"].sum())
        balls = int(sub[sub["is_legal"]].shape[0])
        sr = round((runs / balls * 100.0), 1) if balls > 0 else 0.0
        return {
            "bowling_type": b_type,
            "runs": runs,
            "balls": balls,
            "strike_rate": sr,
        }

    pace_stats = _stats_for("Pace")
    spin_stats = _stats_for("Spin")

    # Advantage calculation
    sr_diff = round(spin_stats["strike_rate"] - pace_stats["strike_rate"], 1)
    runs_diff = spin_stats["runs"] - pace_stats["runs"]
    balls_diff = spin_stats["balls"] - pace_stats["balls"]

    if sr_diff > 0:
        advantage_text = f"Spin advantage: +{sr_diff} SR"
        advantage_type = "Spin"
    elif sr_diff < 0:
        advantage_text = f"Pace advantage: +{abs(sr_diff)} SR"
        advantage_type = "Pace"
    else:
        advantage_text = "Neutral: identical SR vs Pace & Spin"
        advantage_type = "Neutral"

    return {
        "batter": batter,
        "season": season or "All Seasons",
        "team": team or "All Teams",
        "pace": pace_stats,
        "spin": spin_stats,
        "difference": {
            "sr_difference": sr_diff,
            "runs_difference": runs_diff,
            "balls_difference": balls_diff,
            "advantage_text": advantage_text,
            "advantage_type": advantage_type,
        },
        "note": "This is purely matchup performance, not the Contribution Score.",
    }
