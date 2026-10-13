"""
Phase-Based Expected Scoring Dataset Builder & Checkpoint Targets.

Builds datasets and targets for the three connected match checkpoints:
1. TARGET A: expected_score_at_6_overs (Powerplay target, 36 legal balls)
2. TARGET B: expected_score_at_15_overs (Middle-overs target, 90 legal balls)
3. TARGET C: expected_final_score (Death/Innings target, end of innings)

Strictly prevents future leakage:
- Powerplay model uses only states from overs 1–5 and features known then.
- Middle model uses only states prior to over 15 (overs 6–14) and features known then.
- Death model uses only states after over 15 (overs 15–19) and features known then.
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd

# Ensure repository root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.expected_score_dataset import (
    identify_excluded_matches,
    SamplingConfig,
)

# Feature definitions for each checkpoint model
PP_FEATURE_COLUMNS = [
    "current_team_runs",
    "wickets_lost_so_far",
    "wickets_remaining",
    "overs_completed",
    "balls_remaining_until_6",
    "current_team_rr",
    "innings_phase",
]

MID_FEATURE_COLUMNS = [
    "current_team_runs",
    "wickets_lost_so_far",
    "wickets_remaining",
    "overs_completed",
    "balls_remaining_until_15",
    "current_team_rr",
    "innings_phase",
]

DEATH_FEATURE_COLUMNS = [
    "current_team_runs",
    "wickets_lost_so_far",
    "wickets_remaining",
    "overs_completed",
    "balls_remaining_in_innings",
    "current_team_rr",
    "innings_phase",
]

TARGET_PP = "score_at_6"
TARGET_MID = "score_at_15"
TARGET_FINAL = "final_team_score"


def extract_checkpoint_targets(
    match_state_df: pd.DataFrame,
    innings_df: pd.DataFrame,
    valid_match_ids: Set[Any]
) -> pd.DataFrame:
    """
    Extract exact team total score at over 6, over 15, and final score for valid matches.

    Args:
        match_state_df: Full match state DataFrame.
        innings_df: Processed innings DataFrame.
        valid_match_ids: Set of valid match IDs.

    Returns:
        DataFrame with columns [match_id, score_at_6, score_at_15, final_team_score].
    """
    ms_valid = match_state_df[
        (match_state_df["innings_number"] == 1) &
        (match_state_df["match_id"].isin(valid_match_ids))
    ].copy()

    # 1. Score after 6.0 overs (36 legal balls)
    score_6_series = (
        ms_valid[ms_valid["is_legal"].astype(bool) & (ms_valid["legal_balls_bowled_so_far"] == 36)]
        .groupby("match_id")["total_team_runs_so_far"]
        .last()
    )

    # 2. Score after 15.0 overs (90 legal balls)
    score_15_series = (
        ms_valid[ms_valid["is_legal"].astype(bool) & (ms_valid["legal_balls_bowled_so_far"] == 90)]
        .groupby("match_id")["total_team_runs_so_far"]
        .last()
    )

    # 3. Final score from innings.csv
    inn_valid = innings_df[
        (innings_df["innings_number"] == 1) &
        (innings_df["match_id"].isin(valid_match_ids))
    ]
    final_score_series = inn_valid.set_index("match_id")["total_runs"]

    # Combine into target table
    targets_df = pd.DataFrame(index=list(valid_match_ids))
    targets_df.index.name = "match_id"
    targets_df[TARGET_PP] = score_6_series
    targets_df[TARGET_MID] = score_15_series
    targets_df[TARGET_FINAL] = final_score_series

    # If an innings ended (all-out) between 14.0 and 15.0 overs, score_at_15 is final score
    targets_df[TARGET_MID] = targets_df[TARGET_MID].combine_first(targets_df[TARGET_FINAL])

    return targets_df.reset_index()


def load_phase_expected_datasets(
    match_state_path: str = "data/processed/match_state.csv",
    innings_path: str = "data/processed/innings.csv",
    config: Optional[SamplingConfig] = None
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """
    Load and construct partitioned phase datasets for Powerplay, Middle, and Death models.

    Args:
        match_state_path: Path to match_state.csv.
        innings_path: Path to innings.csv.
        config: Optional SamplingConfig.

    Returns:
        Tuple of (powerplay_df, middle_df, death_df, all_sampled_df, metadata_dict).
    """
    if config is None:
        config = SamplingConfig(strategy="end_of_over", min_over=1, max_over=19)

    # 1. Load data
    df_ms = pd.read_csv(match_state_path, low_memory=False)
    df_inn = pd.read_csv(innings_path)

    # 2. Filter first innings & identify exclusions
    inn1 = df_inn[df_inn["innings_number"] == 1].copy()
    total_raw_innings = len(inn1)
    excluded_match_ids, excluded_df = identify_excluded_matches(inn1)
    valid_match_ids = set(inn1["match_id"]) - excluded_match_ids

    # 3. Extract exact checkpoint targets
    targets_df = extract_checkpoint_targets(df_ms, df_inn, valid_match_ids)
    target_map_6 = targets_df.set_index("match_id")[TARGET_PP].to_dict()
    target_map_15 = targets_df.set_index("match_id")[TARGET_MID].to_dict()
    target_map_final = targets_df.set_index("match_id")[TARGET_FINAL].to_dict()

    # 4. Filter match_state to non-chase 1st innings of valid matches
    valid_ms = df_ms[
        (df_ms["innings_number"] == 1) &
        (~df_ms["is_chase"].fillna(False).astype(bool)) &
        (df_ms["match_id"].isin(valid_match_ids))
    ].copy()

    # 5. Filter active intermediate states (wickets > 0 and balls_remaining > 0)
    valid_ms = valid_ms[
        (valid_ms["wickets_remaining"] > 0) &
        (valid_ms["balls_remaining_in_innings"] > 0)
    ]

    # Sample at end of each completed over 1..19
    target_overs = list(range(config.min_over, config.max_over + 1))
    target_balls = [ov * 6 for ov in target_overs]
    sampled = valid_ms[
        valid_ms["is_legal"].astype(bool) &
        valid_ms["legal_balls_bowled_so_far"].isin(target_balls)
    ].copy()

    # Attach targets and computed distance metrics
    sampled["current_team_runs"] = sampled["total_team_runs_so_far"]
    sampled[TARGET_PP] = sampled["match_id"].map(target_map_6)
    sampled[TARGET_MID] = sampled["match_id"].map(target_map_15)
    sampled[TARGET_FINAL] = sampled["match_id"].map(target_map_final)

    # Checkpoint distances
    sampled["balls_remaining_until_6"] = (36 - sampled["legal_balls_bowled_so_far"]).clip(lower=0)
    sampled["balls_remaining_until_15"] = (90 - sampled["legal_balls_bowled_so_far"]).clip(lower=0)

    # 6. Partition by Phase
    # Powerplay: overs 1.0 to 5.0 (overs 1–5, targeting score at 6.0)
    pp_df = sampled[sampled["overs_completed"].between(1.0, 5.0)].copy().reset_index(drop=True)

    # Middle: overs 6.0 to 14.0 (targeting score at 15.0)
    mid_df = sampled[sampled["overs_completed"].between(6.0, 14.0)].copy().reset_index(drop=True)

    # Death: overs 15.0 to 19.0 (targeting final score)
    death_df = sampled[sampled["overs_completed"].between(15.0, 19.0)].copy().reset_index(drop=True)

    metadata: Dict[str, Any] = {
        "total_raw_first_innings": total_raw_innings,
        "usable_first_innings": len(valid_match_ids),
        "excluded_matches_count": len(excluded_match_ids),
        "total_sampled_states": len(sampled),
        "powerplay_states_count": len(pp_df),
        "middle_states_count": len(mid_df),
        "death_states_count": len(death_df),
        "target_pp_name": TARGET_PP,
        "target_mid_name": TARGET_MID,
        "target_final_name": TARGET_FINAL,
        "features_pp": PP_FEATURE_COLUMNS,
        "features_mid": MID_FEATURE_COLUMNS,
        "features_death": DEATH_FEATURE_COLUMNS,
    }

    return pp_df, mid_df, death_df, sampled, metadata


def split_phase_datasets_by_match(
    pp_df: pd.DataFrame,
    mid_df: pd.DataFrame,
    death_df: pd.DataFrame,
    all_df: pd.DataFrame,
    test_size: float = 0.2,
    random_state: int = 42
) -> Tuple[Dict[str, pd.DataFrame], Dict[str, pd.DataFrame], List[Any], List[Any]]:
    """
    Split all phase datasets strictly by MATCH ID using a shared partition.

    Guarantees:
    - Zero match overlap between train and test across all three models.
    - Consistency across Powerplay, Middle, Death, and overall trajectory evaluation.

    Args:
        pp_df: Powerplay DataFrame.
        mid_df: Middle-overs DataFrame.
        death_df: Death-overs DataFrame.
        all_df: All sampled states DataFrame.
        test_size: Proportion of matches for test set.
        random_state: Fixed random seed.

    Returns:
        Tuple of (train_dict, test_dict, train_match_ids, test_match_ids).
        train_dict and test_dict contain keys: 'powerplay', 'middle', 'death', 'all'.
    """
    unique_matches = np.array(sorted(all_df["match_id"].unique()))
    rng = np.random.default_rng(random_state)

    n_test = int(np.round(test_size * len(unique_matches)))
    test_match_indices = rng.choice(len(unique_matches), size=n_test, replace=False)

    test_matches_set = set(unique_matches[test_match_indices])
    train_matches_set = set(unique_matches) - test_matches_set

    train_dict = {
        "powerplay": pp_df[pp_df["match_id"].isin(train_matches_set)].copy().reset_index(drop=True),
        "middle": mid_df[mid_df["match_id"].isin(train_matches_set)].copy().reset_index(drop=True),
        "death": death_df[death_df["match_id"].isin(train_matches_set)].copy().reset_index(drop=True),
        "all": all_df[all_df["match_id"].isin(train_matches_set)].copy().reset_index(drop=True),
    }

    test_dict = {
        "powerplay": pp_df[pp_df["match_id"].isin(test_matches_set)].copy().reset_index(drop=True),
        "middle": mid_df[mid_df["match_id"].isin(test_matches_set)].copy().reset_index(drop=True),
        "death": death_df[death_df["match_id"].isin(test_matches_set)].copy().reset_index(drop=True),
        "all": all_df[all_df["match_id"].isin(test_matches_set)].copy().reset_index(drop=True),
    }

    train_match_ids = sorted(list(train_matches_set))
    test_match_ids = sorted(list(test_matches_set))

    return train_dict, test_dict, train_match_ids, test_match_ids
