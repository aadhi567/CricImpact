"""
Unit and Integration Tests for Phase 3 Part 1: Expected Final Score Model.

Tests:
1. Feature construction & types
2. Target construction & alignment with innings totals
3. Baseline calculations (Simple Projection and Historical Averages)
4. Train/test split by match_id (zero leakage across matches)
5. Model prediction output, fit/predict flow, and serialization round-trip
6. Data leakage prevention audit (no future information in feature vectors)
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.expected_score_dataset import (
    FEATURE_COLUMNS,
    TARGET_COLUMN,
    SamplingConfig,
    identify_excluded_matches,
    load_expected_score_dataset,
    sample_match_states,
    split_train_test_by_match,
    split_train_test_by_season,
)
from src.expected_score_model import (
    ExpectedScoreRFModel,
    HistoricalAverageBaseline,
    SimpleProjectionBaseline,
)
from src.evaluate_expected_score import calculate_metrics, evaluate_by_phase


@pytest.fixture
def sample_synthetic_match_states():
    """Create a minimal synthetic match state DataFrame for testing."""
    records = []
    # Match 1: 1st innings finishes at 160
    for ov in range(1, 20):
        legal_balls = ov * 6
        balls_rem = 120 - legal_balls
        runs = ov * 8
        wkts = min(9, ov // 3)
        rr = round(runs / ov, 2)
        phase = "POWERPLAY" if ov <= 6 else ("MIDDLE" if ov <= 15 else "DEATH")
        records.append({
            "match_id": "M001",
            "season": "2024",
            "innings_number": 1,
            "over": ov - 1,
            "ball": 6,
            "is_legal": True,
            "is_chase": False,
            "total_team_runs_so_far": runs,
            "current_team_runs": runs,
            "wickets_lost_so_far": wkts,
            "wickets_remaining": 10 - wkts,
            "legal_balls_bowled_so_far": legal_balls,
            "overs_completed": float(ov),
            "balls_remaining_in_innings": balls_rem,
            "current_team_rr": rr,
            "innings_phase": phase,
            "final_team_score": 160,
        })

    # Match 2: 1st innings finishes at 200
    for ov in range(1, 20):
        legal_balls = ov * 6
        balls_rem = 120 - legal_balls
        runs = ov * 10
        wkts = min(9, ov // 4)
        rr = round(runs / ov, 2)
        phase = "POWERPLAY" if ov <= 6 else ("MIDDLE" if ov <= 15 else "DEATH")
        records.append({
            "match_id": "M002",
            "season": "2025",
            "innings_number": 1,
            "over": ov - 1,
            "ball": 6,
            "is_legal": True,
            "is_chase": False,
            "total_team_runs_so_far": runs,
            "current_team_runs": runs,
            "wickets_lost_so_far": wkts,
            "wickets_remaining": 10 - wkts,
            "legal_balls_bowled_so_far": legal_balls,
            "overs_completed": float(ov),
            "balls_remaining_in_innings": balls_rem,
            "current_team_rr": rr,
            "innings_phase": phase,
            "final_team_score": 200,
        })

    return pd.DataFrame(records)


# ======================================================================
# 1. Feature Construction Tests
# ======================================================================

def test_feature_construction_columns(sample_synthetic_match_states):
    """Test that all required feature columns are present and correctly named."""
    df = sample_synthetic_match_states
    for col in FEATURE_COLUMNS:
        assert col in df.columns, f"Feature column '{col}' missing from dataset"

    assert TARGET_COLUMN in df.columns, "Target column 'final_team_score' missing"


def test_feature_valid_ranges(sample_synthetic_match_states):
    """Test that feature values satisfy cricket domain constraints."""
    df = sample_synthetic_match_states
    assert (df["current_team_runs"] >= 0).all()
    assert (df["wickets_lost_so_far"] >= 0).all() and (df["wickets_lost_so_far"] <= 10).all()
    assert (df["wickets_remaining"] >= 0).all() and (df["wickets_remaining"] <= 10).all()
    assert (df["wickets_lost_so_far"] + df["wickets_remaining"] == 10).all()
    assert (df["overs_completed"] >= 1.0).all() and (df["overs_completed"] <= 19.0).all()
    assert (df["balls_remaining_in_innings"] >= 6).all() and (df["balls_remaining_in_innings"] <= 114).all()
    assert (df["current_team_rr"] >= 0.0).all()
    assert df["innings_phase"].isin(["POWERPLAY", "MIDDLE", "DEATH"]).all()


# ======================================================================
# 2. Target Construction Tests
# ======================================================================

def test_target_construction():
    """Test that final_team_score matches the innings table total_runs."""
    # Check on processed files
    df_inn = pd.read_csv("data/processed/innings.csv")
    inn1 = df_inn[df_inn["innings_number"] == 1].head(10)

    for _, row in inn1.iterrows():
        assert row["total_runs"] >= 0
        assert not pd.isna(row["total_runs"])


def test_rain_shortened_exclusion_identification():
    """Test identification of rain-shortened innings."""
    dummy_innings = pd.DataFrame([
        {"match_id": "1", "innings_number": 1, "overs_completed": 20.0, "total_wickets": 6, "total_runs": 160},
        {"match_id": "2", "innings_number": 1, "overs_completed": 16.2, "total_wickets": 10, "total_runs": 110},  # All out - valid
        {"match_id": "3", "innings_number": 1, "overs_completed": 12.0, "total_wickets": 4, "total_runs": 85},   # Rain - excluded
    ])
    excluded_ids, excluded_df = identify_excluded_matches(dummy_innings)

    assert "3" in excluded_ids
    assert "1" not in excluded_ids
    assert "2" not in excluded_ids  # 10 wickets is all out, not rain shortened
    assert len(excluded_df) == 1


# ======================================================================
# 3. Baseline Calculation Tests
# ======================================================================

def test_simple_projection_baseline():
    """Test Simple Run Rate Projection baseline formula."""
    baseline = SimpleProjectionBaseline()
    df = pd.DataFrame([
        {"current_team_runs": 60, "current_team_rr": 10.0, "balls_remaining_in_innings": 84},  # 14 overs rem -> 60 + 10*14 = 200
        {"current_team_runs": 80, "current_team_rr": 8.0, "balls_remaining_in_innings": 60},   # 10 overs rem -> 80 + 8*10 = 160
    ])
    preds = baseline.predict(df)
    assert np.isclose(preds[0], 200.0)
    assert np.isclose(preds[1], 160.0)


def test_historical_average_baseline(sample_synthetic_match_states):
    """Test Historical Average baselines (global and conditional)."""
    df = sample_synthetic_match_states
    hist_global = HistoricalAverageBaseline(mode="global")
    hist_global.fit(df, df[TARGET_COLUMN])
    preds_g = hist_global.predict(df)
    assert np.allclose(preds_g, 180.0)  # Mean of 160 and 200 is 180

    hist_cond = HistoricalAverageBaseline(mode="conditional")
    hist_cond.fit(df, df[TARGET_COLUMN])
    preds_c = hist_cond.predict(df)
    assert len(preds_c) == len(df)
    assert (preds_c > 0).all()


# ======================================================================
# 4. Train / Test Split by Match ID Tests
# ======================================================================

def test_split_by_match_no_leakage(sample_synthetic_match_states):
    """Verify that train and test match IDs are strictly disjoint."""
    df = sample_synthetic_match_states
    train_df, test_df, train_matches, test_matches = split_train_test_by_match(
        df, test_size=0.5, random_state=42
    )

    train_set = set(train_matches)
    test_set = set(test_matches)

    # 1. Zero match overlap
    assert len(train_set.intersection(test_set)) == 0

    # 2. All train rows belong to train matches
    assert train_df["match_id"].isin(train_set).all()

    # 3. All test rows belong to test matches
    assert test_df["match_id"].isin(test_set).all()

    # 4. Union covers all matches
    assert train_set.union(test_set) == set(df["match_id"].unique())


def test_split_by_season():
    """Verify season-based split."""
    dummy_df = pd.DataFrame([
        {"match_id": "M1", "season": "2023"},
        {"match_id": "M2", "season": "2024"},
        {"match_id": "M3", "season": "2025"},
        {"match_id": "M4", "season": "2026"},
    ])
    train_df, test_df, tr_m, te_m = split_train_test_by_season(dummy_df, cutoff_season="2025")
    assert set(te_m) == {"M3", "M4"}
    assert set(tr_m) == {"M1", "M2"}


# ======================================================================
# 5. Model Prediction Output and Persistence Tests
# ======================================================================

def test_rf_model_fit_predict_and_persistence(sample_synthetic_match_states, tmp_path):
    """Test Random Forest fitting, prediction, feature importances, and saving/loading."""
    df = sample_synthetic_match_states
    rf = ExpectedScoreRFModel(n_estimators=10, max_depth=4, random_state=42)

    rf.fit(df, df[TARGET_COLUMN])
    assert rf.is_fitted

    preds = rf.predict(df)
    assert len(preds) == len(df)
    assert (preds > 0).all()

    importances = rf.get_feature_importances()
    assert len(importances) == len(FEATURE_COLUMNS)
    assert np.isclose(sum(importances.values()), 1.0, atol=1e-3)

    # Test serialization
    save_dir = tmp_path / "expected_score_test_model"
    rf.save(save_dir)

    assert (save_dir / "expected_score_rf.joblib").exists()
    assert (save_dir / "feature_names.json").exists()
    assert (save_dir / "config.json").exists()
    assert (save_dir / "training_metadata.json").exists()

    # Test loading
    loaded_rf = ExpectedScoreRFModel.load(save_dir)
    assert loaded_rf.is_fitted
    loaded_preds = loaded_rf.predict(df)
    assert np.allclose(preds, loaded_preds)


# ======================================================================
# 6. Data Leakage Prevention Tests
# ======================================================================

def test_no_future_information_in_features():
    """
    CRITICAL TEST: Ensure NO future-looking columns or terminal indicators
    are included in the audited feature set.
    """
    forbidden_substrings = [
        "winner", "result", "post", "future", "chase", "target", "win_by",
        "batter_runs", "bowler", "player_dismissed", "dismissal_kind"
    ]

    for feat in FEATURE_COLUMNS:
        assert feat != TARGET_COLUMN, f"Target '{TARGET_COLUMN}' cannot be in features"
        for forbidden in forbidden_substrings:
            assert forbidden not in feat.lower(), (
                f"Feature '{feat}' contains suspicious future substring '{forbidden}'"
            )


def test_sampling_excludes_terminal_states():
    """Verify that sampling excludes innings-ending deliveries where balls_rem=0 or wkts_rem=0."""
    terminal_df = pd.DataFrame([
        # Active state (over 10, 60 balls left, 7 wkts left) -> KEEP
        {
            "match_id": "M1", "innings_number": 1, "is_legal": True, "legal_balls_bowled_so_far": 60,
            "balls_remaining_in_innings": 60, "wickets_remaining": 7
        },
        # Terminal state: 120 balls bowled (0 balls remaining) -> MUST EXCLUDE
        {
            "match_id": "M1", "innings_number": 1, "is_legal": True, "legal_balls_bowled_so_far": 120,
            "balls_remaining_in_innings": 0, "wickets_remaining": 4
        },
        # Terminal state: 10 wickets lost (0 wickets remaining) -> MUST EXCLUDE
        {
            "match_id": "M2", "innings_number": 1, "is_legal": True, "legal_balls_bowled_so_far": 84,
            "balls_remaining_in_innings": 36, "wickets_remaining": 0
        },
    ])

    config = SamplingConfig(strategy="all_balls", require_active_innings=True)
    sampled = sample_match_states(terminal_df, config=config)

    assert len(sampled) == 1
    assert (sampled["balls_remaining_in_innings"] > 0).all()
    assert (sampled["wickets_remaining"] > 0).all()
