"""
Expected Final Score Dataset Builder & Sampling Engine.

Prepares non-leaking intermediate first-innings match states for predicting
the final team score in T20 cricket.

Key Responsibilities:
1. Filters exclusively for first innings (innings_number == 1, non-chase).
2. Filters out rain-shortened / incomplete / abandoned innings with transparent audit.
3. Configurable sampling strategy (e.g. end of completed overs 1..19).
4. Strictly intermediate states: excludes final delivery / zero resources states.
5. No future information leakage: all features are strictly known at that exact moment.
6. Match-level and season-level train/test splits.
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd

# Ensure repository root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# Feature list explicitly audited for leakage prevention
FEATURE_COLUMNS = [
    "current_team_runs",
    "wickets_lost_so_far",
    "wickets_remaining",
    "overs_completed",
    "balls_remaining_in_innings",
    "current_team_rr",
    "innings_phase",
]

TARGET_COLUMN = "final_team_score"

FEATURE_AVAILABILITY_AUDIT = {
    "current_team_runs": "Cumulative runs scored up to current completed delivery/over. Known in real time on the scoreboard.",
    "wickets_lost_so_far": "Cumulative wickets lost up to current completed delivery/over. Known in real time on the scoreboard.",
    "wickets_remaining": "Resources remaining (10 - wickets_lost_so_far). Known in real time.",
    "overs_completed": "Completed overs in cricket notation (legal_balls / 6). Known in real time.",
    "balls_remaining_in_innings": "Scheduled legal balls (120 for 20 ov) minus legal balls bowled so far. Fully known in real time.",
    "current_team_rr": "Current run rate (current_team_runs / (legal_balls / 6)). Standard live broadcast statistic.",
    "innings_phase": "Chronological phase derived purely from overs completed (Powerplay: <=6, Middle: 6..15, Death: 15..20). Known in real time.",
}


@dataclass
class SamplingConfig:
    """
    Configuration for intermediate match-state sampling.

    Attributes:
        strategy: 'end_of_over' (default), 'every_n_overs', or 'all_balls'.
        every_n_overs: Interval when strategy is 'every_n_overs' (default 1).
        min_over: Minimum completed over to sample (default 1).
        max_over: Maximum completed over to sample (default 19).
        exclude_rain_shortened: Exclude matches where 1st innings ended prematurely (<19.5 ov & <10 wkts).
        exclude_super_overs: Exclude innings_number > 2.
        require_active_innings: Require wickets_remaining > 0 and balls_remaining > 0.
    """
    strategy: str = "end_of_over"
    every_n_overs: int = 1
    min_over: int = 1
    max_over: int = 19
    exclude_rain_shortened: bool = True
    exclude_super_overs: bool = True
    require_active_innings: bool = True


def identify_excluded_matches(
    innings_df: pd.DataFrame,
    min_overs_for_full_innings: float = 19.5,
    max_wickets_all_out: int = 10
) -> Tuple[Set[Any], pd.DataFrame]:
    """
    Identify and document unusual, rain-shortened, or incomplete first innings.

    A standard T20 first innings completes when either:
    1. Scheduled 20 overs are reached (recorded as >= 19.5 overs).
    2. The batting team is bowled out (all 10 wickets lost).

    Innings ending with < 19.5 overs and < 10 wickets are truncated by rain,
    bad light, abandonment, or revised DLS regulations. In these cases, the
    observed final score does not reflect a full 20-over effort, so they are
    excluded from the 20-over expected final score model to prevent corrupting
    target distributions.

    Args:
        innings_df: Processed innings DataFrame.
        min_overs_for_full_innings: Minimum overs threshold for complete innings.
        max_wickets_all_out: Wickets count representing all out.

    Returns:
        Tuple of (set of excluded match_ids, DataFrame detailing exclusions).
    """
    inn1 = innings_df[innings_df["innings_number"] == 1].copy()

    # Incomplete: fewer than 19.5 overs AND fewer than 10 wickets
    is_rain_shortened = (inn1["overs_completed"] < min_overs_for_full_innings) & (
        inn1["total_wickets"] < max_wickets_all_out
    )

    excluded_df = inn1[is_rain_shortened].copy()
    excluded_df["exclusion_reason"] = excluded_df.apply(
        lambda r: (
            f"Rain-shortened or incomplete 1st innings: only {r['overs_completed']} overs "
            f"bowled with {int(r['total_wickets'])} wickets lost (not all-out)."
        ),
        axis=1
    )

    excluded_match_ids = set(excluded_df["match_id"].tolist())
    return excluded_match_ids, excluded_df


def sample_match_states(
    match_state_df: pd.DataFrame,
    config: Optional[SamplingConfig] = None
) -> pd.DataFrame:
    """
    Apply configurable sampling to intermediate match states.

    By default, extracts the exact state at the conclusion of each completed over
    (overs 1, 2, ..., 19).

    Prevents terminal state inclusion (do not sample when balls_remaining == 0
    or wickets_remaining == 0, where final score is already reached).

    Args:
        match_state_df: Match state DataFrame filtered to valid first innings.
        config: SamplingConfig instance.

    Returns:
        Filtered DataFrame containing sampled intermediate match states.
    """
    if config is None:
        config = SamplingConfig()

    df = match_state_df.copy()

    # Enforce active innings (no terminal states)
    if config.require_active_innings:
        df = df[(df["wickets_remaining"] > 0) & (df["balls_remaining_in_innings"] > 0)]

    if config.strategy in ("end_of_over", "every_n_overs"):
        step = config.every_n_overs if config.strategy == "every_n_overs" else 1
        target_overs = list(range(config.min_over, config.max_over + 1, step))
        target_balls = [ov * 6 for ov in target_overs]

        # In cricket, an over ends on the legal delivery that reaches ov * 6 legal balls.
        # Filtering is_legal == True and legal_balls_bowled_so_far in target_balls guarantees
        # exactly ONE observation per completed over per match.
        sampled = df[
            df["is_legal"].astype(bool) & df["legal_balls_bowled_so_far"].isin(target_balls)
        ].copy()

    elif config.strategy == "all_balls":
        sampled = df.copy()

    else:
        raise ValueError(f"Unknown sampling strategy: {config.strategy}")

    return sampled


def load_expected_score_dataset(
    match_state_path: str = "data/processed/match_state.csv",
    innings_path: str = "data/processed/innings.csv",
    config: Optional[SamplingConfig] = None
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Load and prepare the full expected score training and evaluation dataset.

    Args:
        match_state_path: Path to match_state.csv.
        innings_path: Path to innings.csv.
        config: SamplingConfig instance.

    Returns:
        Tuple of (clean sampled DataFrame with features and target, metadata dictionary).
    """
    if config is None:
        config = SamplingConfig()

    # 1. Load data
    df_ms = pd.read_csv(match_state_path, low_memory=False)
    df_inn = pd.read_csv(innings_path)

    # 2. First innings only
    inn1 = df_inn[df_inn["innings_number"] == 1].copy()
    total_raw_innings = len(inn1)

    # 3. Identify and audit excluded matches
    excluded_match_ids, excluded_df = identify_excluded_matches(inn1)
    usable_innings_count = total_raw_innings - len(excluded_match_ids)

    # 4. Filter match_state to non-chase first innings of valid matches
    valid_ms = df_ms[
        (df_ms["innings_number"] == 1) &
        (~df_ms["is_chase"].fillna(False).astype(bool)) &
        (~df_ms["match_id"].isin(excluded_match_ids))
    ].copy()

    # 5. Attach target: final_team_score
    # Innings total_runs is verified identical to last delivery total_team_runs_so_far
    final_score_map = inn1.set_index("match_id")["total_runs"].to_dict()
    valid_ms[TARGET_COLUMN] = valid_ms["match_id"].map(final_score_map)

    # 6. Standardize feature names
    valid_ms["current_team_runs"] = valid_ms["total_team_runs_so_far"]

    # 7. Apply sampling
    sampled_df = sample_match_states(valid_ms, config=config)

    # 8. Sort deterministically
    sampled_df = sampled_df.sort_values(
        by=["match_id", "legal_balls_bowled_so_far"]
    ).reset_index(drop=True)

    metadata: Dict[str, Any] = {
        "total_raw_first_innings": total_raw_innings,
        "usable_first_innings": usable_innings_count,
        "excluded_matches_count": len(excluded_match_ids),
        "excluded_matches_summary": excluded_df[
            ["match_id", "season", "total_runs", "total_wickets", "overs_completed", "exclusion_reason"]
        ].to_dict(orient="records"),
        "total_sampled_states": len(sampled_df),
        "sampling_strategy": config.strategy,
        "min_over": config.min_over,
        "max_over": config.max_over,
        "feature_columns": FEATURE_COLUMNS,
        "target_column": TARGET_COLUMN,
        "feature_availability_audit": FEATURE_AVAILABILITY_AUDIT,
    }

    return sampled_df, metadata


def split_train_test_by_match(
    df: pd.DataFrame,
    test_size: float = 0.2,
    random_state: int = 42
) -> Tuple[pd.DataFrame, pd.DataFrame, List[Any], List[Any]]:
    """
    Split dataset by MATCH ID to strictly avoid data leakage across related states.

    Args:
        df: Prepared match states DataFrame.
        test_size: Proportion of matches for the test set (default 0.2).
        random_state: Fixed random seed for reproducibility.

    Returns:
        Tuple of (train_df, test_df, train_match_ids, test_match_ids).
    """
    unique_matches = np.array(sorted(df["match_id"].unique()))
    rng = np.random.default_rng(random_state)

    n_test = int(np.round(test_size * len(unique_matches)))
    test_match_indices = rng.choice(len(unique_matches), size=n_test, replace=False)

    test_matches_set = set(unique_matches[test_match_indices])
    train_matches_set = set(unique_matches) - test_matches_set

    train_df = df[df["match_id"].isin(train_matches_set)].copy().reset_index(drop=True)
    test_df = df[df["match_id"].isin(test_matches_set)].copy().reset_index(drop=True)

    return train_df, test_df, sorted(list(train_matches_set)), sorted(list(test_matches_set))


def split_train_test_by_season(
    df: pd.DataFrame,
    test_seasons: Optional[List[str]] = None,
    cutoff_season: str = "2025"
) -> Tuple[pd.DataFrame, pd.DataFrame, List[Any], List[Any]]:
    """
    Split dataset by season for temporal validation (train on historical, test on recent).

    Args:
        df: Prepared match states DataFrame.
        test_seasons: Explicit list of seasons for test set. If None, uses seasons >= cutoff_season.
        cutoff_season: Cutoff season string if test_seasons is not provided.

    Returns:
        Tuple of (train_df, test_df, train_match_ids, test_match_ids).
    """
    seasons_str = df["season"].astype(str)

    if test_seasons is not None:
        is_test = seasons_str.isin(test_seasons)
    else:
        # Default: seasons starting at or after cutoff
        is_test = seasons_str >= cutoff_season

    test_df = df[is_test].copy().reset_index(drop=True)
    train_df = df[~is_test].copy().reset_index(drop=True)

    train_match_ids = sorted(train_df["match_id"].unique().tolist())
    test_match_ids = sorted(test_df["match_id"].unique().tolist())

    return train_df, test_df, train_match_ids, test_match_ids
