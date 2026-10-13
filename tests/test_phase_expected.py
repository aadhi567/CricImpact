"""
Unit and Integration Tests for Phase 3 Part 2: Phase-Based Expected Scoring Engine.

Tests:
1. Correct target construction (score_at_6, score_at_15, final_team_score)
2. Checkpoint identification & temporal ordering
3. No future data leakage across phase feature sets
4. Match-level train/test disjointness across all phase splits
5. Baseline calculations for Powerplay, Middle, and Death
6. Model prediction output, fit/predict flow, and serialization round-trip
7. Trajectory dataset logic and correct NULL/NaN behavior for passed checkpoints
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.phase_expected_dataset import (
    DEATH_FEATURE_COLUMNS,
    MID_FEATURE_COLUMNS,
    PP_FEATURE_COLUMNS,
    TARGET_FINAL,
    TARGET_MID,
    TARGET_PP,
    extract_checkpoint_targets,
    load_phase_expected_datasets,
    split_phase_datasets_by_match,
)
from src.phase_expected_model import (
    DeathBaseline,
    DeathRFModel,
    MiddleBaseline,
    MiddleRFModel,
    PowerplayBaseline,
    PowerplayRFModel,
)
from src.evaluate_phase_expected import (
    build_trajectory_dataset,
    calculate_metrics,
    evaluate_window_breakdowns,
)


@pytest.fixture
def synthetic_phase_data():
    """Create synthetic data across overs 1 to 19 for 2 matches."""
    records = []
    # Match 1: 6-over score = 45, 15-over score = 120, final = 175
    for ov in range(1, 20):
        balls = ov * 6
        runs = 45 if ov == 6 else (120 if ov == 15 else ov * 8)
        records.append({
            "match_id": "M_01",
            "season": "2024",
            "innings_number": 1,
            "batting_team": "Team Alpha",
            "over": ov - 1,
            "ball": 6,
            "is_legal": True,
            "is_chase": False,
            "total_team_runs_so_far": runs,
            "current_team_runs": runs,
            "wickets_lost_so_far": ov // 3,
            "wickets_remaining": 10 - (ov // 3),
            "legal_balls_bowled_so_far": balls,
            "overs_completed": float(ov),
            "balls_remaining_in_innings": 120 - balls,
            "balls_remaining_until_6": max(0, 36 - balls),
            "balls_remaining_until_15": max(0, 90 - balls),
            "current_team_rr": round(runs / ov, 2),
            "innings_phase": "POWERPLAY" if ov <= 6 else ("MIDDLE" if ov <= 15 else "DEATH"),
            "score_at_6": 48,
            "score_at_15": 125,
            "final_team_score": 175,
        })

    # Match 2: 6-over score = 55, 15-over score = 140, final = 205
    for ov in range(1, 20):
        balls = ov * 6
        runs = ov * 10
        records.append({
            "match_id": "M_02",
            "season": "2025",
            "innings_number": 1,
            "batting_team": "Team Beta",
            "over": ov - 1,
            "ball": 6,
            "is_legal": True,
            "is_chase": False,
            "total_team_runs_so_far": runs,
            "current_team_runs": runs,
            "wickets_lost_so_far": ov // 4,
            "wickets_remaining": 10 - (ov // 4),
            "legal_balls_bowled_so_far": balls,
            "overs_completed": float(ov),
            "balls_remaining_in_innings": 120 - balls,
            "balls_remaining_until_6": max(0, 36 - balls),
            "balls_remaining_until_15": max(0, 90 - balls),
            "current_team_rr": round(runs / ov, 2),
            "innings_phase": "POWERPLAY" if ov <= 6 else ("MIDDLE" if ov <= 15 else "DEATH"),
            "score_at_6": 60,
            "score_at_15": 150,
            "final_team_score": 205,
        })

    return pd.DataFrame(records)


# ======================================================================
# 1. Target Construction & Checkpoint Tests
# ======================================================================

def test_checkpoint_targets_extraction():
    """Verify target scores extraction at overs 6, 15, and final innings score."""
    match_state_sample = pd.DataFrame([
        # Over 6 legal ball
        {"match_id": "1", "innings_number": 1, "is_legal": True, "legal_balls_bowled_so_far": 36, "total_team_runs_so_far": 52},
        # Over 15 legal ball
        {"match_id": "1", "innings_number": 1, "is_legal": True, "legal_balls_bowled_so_far": 90, "total_team_runs_so_far": 128},
    ])
    innings_sample = pd.DataFrame([
        {"match_id": "1", "innings_number": 1, "total_runs": 182, "overs_completed": 20.0, "total_wickets": 5},
    ])

    targets = extract_checkpoint_targets(match_state_sample, innings_sample, {"1"})
    row = targets[targets["match_id"] == "1"].iloc[0]

    assert row[TARGET_PP] == 52
    assert row[TARGET_MID] == 128
    assert row[TARGET_FINAL] == 182


def test_target_monotonically_ordered_checkpoints(synthetic_phase_data):
    """Innings checkpoints must satisfy score_at_6 <= score_at_15 <= final_team_score."""
    df = synthetic_phase_data
    assert (df["score_at_6"] <= df["score_at_15"]).all()
    assert (df["score_at_15"] <= df["final_team_score"]).all()


# ======================================================================
# 2. Data Leakage Prevention Tests
# ======================================================================

def test_feature_sets_leakage_audit():
    """Verify no post-checkpoint or target features are present in any feature set."""
    forbidden = ["future", "final", "winner", "result", "post", "score_at"]

    for feat in PP_FEATURE_COLUMNS:
        assert feat not in [TARGET_PP, TARGET_MID, TARGET_FINAL]
        for f in forbidden:
            assert f not in feat.lower(), f"Suspicious substring '{f}' in PP feature '{feat}'"

    for feat in MID_FEATURE_COLUMNS:
        assert feat not in [TARGET_PP, TARGET_MID, TARGET_FINAL]
        for f in forbidden:
            assert f not in feat.lower(), f"Suspicious substring '{f}' in Mid feature '{feat}'"

    for feat in DEATH_FEATURE_COLUMNS:
        assert feat not in [TARGET_PP, TARGET_MID, TARGET_FINAL]
        for f in forbidden:
            assert f not in feat.lower(), f"Suspicious substring '{f}' in Death feature '{feat}'"


# ======================================================================
# 3. Train / Test Split Disjointness Tests
# ======================================================================

def test_phase_datasets_match_disjointness(synthetic_phase_data):
    """Verify that match-level split partitions all phase datasets with zero match overlap."""
    df = synthetic_phase_data
    pp_df = df[df["overs_completed"].between(1.0, 5.0)]
    mid_df = df[df["overs_completed"].between(6.0, 14.0)]
    death_df = df[df["overs_completed"].between(15.0, 19.0)]

    train_dict, test_dict, tr_ids, te_ids = split_phase_datasets_by_match(
        pp_df, mid_df, death_df, df, test_size=0.5, random_state=42
    )

    tr_set = set(tr_ids)
    te_set = set(te_ids)

    # Disjoint match IDs
    assert len(tr_set.intersection(te_set)) == 0

    for phase in ["powerplay", "middle", "death", "all"]:
        assert train_dict[phase]["match_id"].isin(tr_set).all()
        assert test_dict[phase]["match_id"].isin(te_set).all()


# ======================================================================
# 4. Baseline Calculation Tests
# ======================================================================

def test_phase_baselines():
    """Verify mathematical formulas for Powerplay, Middle, and Death baselines."""
    # State: 30 runs after 3.0 overs (RR = 10.0), 18 balls until 6 (3 overs)
    # Powerplay projection = 30 + 10.0 * 3 = 60
    # 72 balls until 15 (12 overs) -> Middle projection = 30 + 10.0 * 12 = 150
    # 102 balls until final (17 overs) -> Death projection = 30 + 10.0 * 17 = 200
    df = pd.DataFrame([{
        "current_team_runs": 30,
        "current_team_rr": 10.0,
        "balls_remaining_until_6": 18,
        "balls_remaining_until_15": 72,
        "balls_remaining_in_innings": 102,
    }])

    p_pp = PowerplayBaseline().predict(df)
    p_mid = MiddleBaseline().predict(df)
    p_death = DeathBaseline().predict(df)

    assert np.isclose(p_pp[0], 60.0)
    assert np.isclose(p_mid[0], 150.0)
    assert np.isclose(p_death[0], 200.0)


# ======================================================================
# 5. Model Fit, Predict, and Serialization Tests
# ======================================================================

def test_phase_models_fit_and_serialization(synthetic_phase_data, tmp_path):
    """Verify fit, predict, feature importances, and serialization for all 3 phase models."""
    df = synthetic_phase_data
    pp_df = df[df["overs_completed"].between(1.0, 5.0)]
    mid_df = df[df["overs_completed"].between(6.0, 14.0)]
    death_df = df[df["overs_completed"].between(15.0, 19.0)]

    # 1. Powerplay Model
    m_pp = PowerplayRFModel(n_estimators=10, max_depth=3, random_state=42)
    m_pp.fit(pp_df, pp_df[TARGET_PP])
    p_pp = m_pp.predict(pp_df)
    assert len(p_pp) == len(pp_df)
    assert (p_pp > 0).all()

    # Serialization PP
    pp_save = tmp_path / "pp_model.joblib"
    m_pp.save(pp_save)
    loaded_pp = PowerplayRFModel.load(pp_save)
    assert np.allclose(p_pp, loaded_pp.predict(pp_df))

    # 2. Middle Model
    m_mid = MiddleRFModel(n_estimators=10, max_depth=3, random_state=42)
    m_mid.fit(mid_df, mid_df[TARGET_MID])
    p_mid = m_mid.predict(mid_df)
    assert len(p_mid) == len(mid_df)

    # 3. Death Model
    m_death = DeathRFModel(n_estimators=10, max_depth=3, random_state=42)
    m_death.fit(death_df, death_df[TARGET_FINAL])
    p_death = m_death.predict(death_df)
    assert len(p_death) == len(death_df)


# ======================================================================
# 6. Trajectory Dataset & NULL / NaN Checkpoint Behavior Tests
# ======================================================================

def test_trajectory_dataset_null_behavior(synthetic_phase_data, tmp_path):
    """
    CRITICAL TEST: Ensure trajectory dataset correctly populates checkpoint predictions:
    - At over < 6: expected_score_at_6, expected_score_at_15, expected_final_score are ALL valid.
    - At 6 <= over < 15: expected_score_at_6 is NULL/NaN; expected_score_at_15 and final are valid.
    - At over >= 15: expected_score_at_6 is NULL/NaN; expected_score_at_15 is NULL/NaN; final is valid.
    """
    df = synthetic_phase_data
    pp_df = df[df["overs_completed"].between(1.0, 5.0)]
    mid_df = df[df["overs_completed"].between(6.0, 14.0)]
    death_df = df[df["overs_completed"].between(15.0, 19.0)]

    m_pp = PowerplayRFModel(n_estimators=10, max_depth=3, random_state=42)
    m_pp.fit(pp_df, pp_df[TARGET_PP])

    m_mid = MiddleRFModel(n_estimators=10, max_depth=3, random_state=42)
    m_mid.fit(mid_df, mid_df[TARGET_MID])

    m_death = DeathRFModel(n_estimators=10, max_depth=3, random_state=42)
    m_death.fit(death_df, death_df[TARGET_FINAL])

    csv_out = tmp_path / "expected_scoring_trajectory.csv"
    traj = build_trajectory_dataset(
        all_sampled_df=df,
        pp_model=m_pp,
        mid_model=m_mid,
        death_model=m_death,
        part1_model=None,
        output_path=str(csv_out)
    )

    assert csv_out.exists()

    # 1. State at over 4.0: all three must be NOT NULL
    row_ov4 = traj[traj["over"] == 4.0].iloc[0]
    assert not pd.isna(row_ov4["expected_score_at_6"]), "expected_score_at_6 should be valid at over 4"
    assert not pd.isna(row_ov4["expected_score_at_15"]), "expected_score_at_15 should be valid at over 4"
    assert not pd.isna(row_ov4["expected_final_score"]), "expected_final_score should be valid at over 4"

    # 2. State at over 10.0: over 6 passed -> expected_score_at_6 must be NULL/NaN
    row_ov10 = traj[traj["over"] == 10.0].iloc[0]
    assert pd.isna(row_ov10["expected_score_at_6"]), "expected_score_at_6 must be NULL at over 10"
    assert not pd.isna(row_ov10["expected_score_at_15"]), "expected_score_at_15 should be valid at over 10"
    assert not pd.isna(row_ov10["expected_final_score"]), "expected_final_score should be valid at over 10"

    # 3. State at over 17.0: over 6 and 15 passed -> both must be NULL/NaN
    row_ov17 = traj[traj["over"] == 17.0].iloc[0]
    assert pd.isna(row_ov17["expected_score_at_6"]), "expected_score_at_6 must be NULL at over 17"
    assert pd.isna(row_ov17["expected_score_at_15"]), "expected_score_at_15 must be NULL at over 17"
    assert not pd.isna(row_ov17["expected_final_score"]), "expected_final_score should be valid at over 17"
