"""
Expected Score Models & Baselines.

Implements:
1. Baseline 1: Simple Run Rate Projection (current_score + current_rr * overs_remaining)
2. Baseline 2: Historical Average Baselines (global mean & conditional remaining runs)
3. Primary ML Model: RandomForestRegressor with modest, interpretable hyperparameters.
4. Model serialization, configuration persistence, and feature importance reporting.
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

# Ensure repository root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.expected_score_dataset import FEATURE_COLUMNS, TARGET_COLUMN


# Phase mapping for tree-based modeling
PHASE_MAPPING = {
    "POWERPLAY": 0,
    "MIDDLE": 1,
    "DEATH": 2,
}
REVERSE_PHASE_MAPPING = {v: k for k, v in PHASE_MAPPING.items()}


class SimpleProjectionBaseline:
    """
    Baseline 1: Standard cricket run-rate extrapolation.

    Formula:
        projected_score = current_team_runs + (current_team_rr * (balls_remaining / 6.0))
    """

    def __init__(self) -> None:
        self.name = "Simple Run-Rate Projection"

    def fit(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> "SimpleProjectionBaseline":
        """No fitting required for simple projection."""
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Compute projected score for each row in X.

        Args:
            X: DataFrame containing 'current_team_runs', 'current_team_rr', and 'balls_remaining_in_innings'.

        Returns:
            1D numpy array of projected final scores.
        """
        runs = X["current_team_runs"].to_numpy(dtype=float)
        rr = X["current_team_rr"].to_numpy(dtype=float)
        balls_rem = X["balls_remaining_in_innings"].to_numpy(dtype=float)
        overs_rem = balls_rem / 6.0

        projected = runs + (rr * overs_rem)
        return projected


class HistoricalAverageBaseline:
    """
    Baseline 2: Historical average benchmarks computed strictly from training data.

    Supports two variants:
    1. 'global': Unconditional historical mean final innings score.
    2. 'conditional': Historical mean runs scored in the remainder of the innings
       from the given completed over: current_team_runs + E[remaining_runs | overs_completed].
    """

    def __init__(self, mode: str = "conditional") -> None:
        """
        Args:
            mode: 'conditional' (default) or 'global'.
        """
        self.name = f"Historical Average ({mode})"
        self.mode = mode
        self.global_mean_: float = 0.0
        self.conditional_remaining_means_: Dict[float, float] = {}

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "HistoricalAverageBaseline":
        """
        Fit historical averages on training observations.

        Args:
            X: Training features containing 'current_team_runs' and 'overs_completed'.
            y: Training target (final_team_score).

        Returns:
            self
        """
        self.global_mean_ = float(y.mean())

        # Remaining runs from state to innings end
        remaining_runs = y - X["current_team_runs"]
        temp_df = pd.DataFrame({
            "overs_completed": X["overs_completed"],
            "remaining_runs": remaining_runs,
        })
        self.conditional_remaining_means_ = (
            temp_df.groupby("overs_completed")["remaining_runs"]
            .mean()
            .to_dict()
        )
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Predict using historical average.

        Args:
            X: Features DataFrame.

        Returns:
            1D numpy array of predictions.
        """
        if self.mode == "global":
            return np.full(len(X), self.global_mean_, dtype=float)

        elif self.mode == "conditional":
            runs = X["current_team_runs"].to_numpy(dtype=float)
            overs = X["overs_completed"].to_list()
            # Fallback to global remaining mean if unseen over
            mean_all_rem = self.global_mean_ - float(np.mean(runs))
            rem_preds = np.array(
                [self.conditional_remaining_means_.get(ov, mean_all_rem) for ov in overs],
                dtype=float,
            )
            return runs + rem_preds

        else:
            raise ValueError(f"Unknown mode: {self.mode}")


class ExpectedScoreRFModel:
    """
    Random Forest model for predicting first-innings expected final score.

    Uses sensible, modest hyperparameters to avoid overfitting while capturing
    non-linear resource interactions (wickets lost, overs elapsed, acceleration).
    """

    def __init__(
        self,
        n_estimators: int = 100,
        max_depth: int = 12,
        min_samples_split: int = 10,
        min_samples_leaf: int = 5,
        random_state: int = 42,
        n_jobs: int = -1,
    ) -> None:
        """
        Initialize Random Forest model with modest, interpretable hyperparameters.
        """
        self.config: Dict[str, Any] = {
            "n_estimators": n_estimators,
            "max_depth": max_depth,
            "min_samples_split": min_samples_split,
            "min_samples_leaf": min_samples_leaf,
            "random_state": random_state,
            "n_jobs": n_jobs,
        }
        self.model = RandomForestRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            min_samples_split=min_samples_split,
            min_samples_leaf=min_samples_leaf,
            random_state=random_state,
            n_jobs=n_jobs,
        )
        self.feature_columns: List[str] = list(FEATURE_COLUMNS)
        self.is_fitted: bool = False

    def _prepare_features(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        Encode categorical features (innings_phase) and verify feature order.

        Args:
            X: Input DataFrame containing required features.

        Returns:
            Preprocessed DataFrame ready for scikit-learn.
        """
        missing = [col for col in self.feature_columns if col not in X.columns]
        if missing:
            raise ValueError(f"Missing required feature columns: {missing}")

        X_prep = X[self.feature_columns].copy()

        # Map innings_phase to ordinal numeric representation
        if X_prep["innings_phase"].dtype == "object":
            X_prep["innings_phase"] = X_prep["innings_phase"].map(PHASE_MAPPING)

        # Ensure numeric dtypes
        for col in self.feature_columns:
            X_prep[col] = pd.to_numeric(X_prep[col], errors="coerce")

        return X_prep

    def fit(self, X: pd.DataFrame, y: Union[pd.Series, np.ndarray]) -> "ExpectedScoreRFModel":
        """
        Fit the Random Forest Regressor.

        Args:
            X: Feature matrix DataFrame.
            y: Target vector (final_team_score).

        Returns:
            self
        """
        X_prep = self._prepare_features(X)
        y_arr = np.asarray(y, dtype=float)
        self.model.fit(X_prep, y_arr)
        self.is_fitted = True
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Predict expected final score.

        Args:
            X: Feature matrix DataFrame.

        Returns:
            1D numpy array of predicted final scores.
        """
        if not self.is_fitted:
            raise RuntimeError("Model is not fitted yet. Call fit() first.")
        X_prep = self._prepare_features(X)
        return self.model.predict(X_prep)

    def get_feature_importances(self) -> Dict[str, float]:
        """
        Extract Gini feature importances.

        Returns:
            Dict mapping feature name to normalized importance.
        """
        if not self.is_fitted:
            raise RuntimeError("Model is not fitted yet.")
        importances = self.model.feature_importances_
        return {
            feat: float(round(imp, 6))
            for feat, imp in zip(self.feature_columns, importances)
        }

    def save(self, output_dir: Union[str, Path], metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Save trained model, feature names, configuration, and metadata.

        Args:
            output_dir: Target directory path.
            metadata: Optional additional metadata dict to persist.
        """
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        # 1. Save trained model
        joblib.dump(self.model, out_path / "expected_score_rf.joblib")

        # 2. Save feature list
        with open(out_path / "feature_names.json", "w", encoding="utf-8") as f:
            json.dump(self.feature_columns, f, indent=2)

        # 3. Save model configuration
        with open(out_path / "config.json", "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2)

        # 4. Save metadata and feature importances
        meta_to_save: Dict[str, Any] = {
            "model_type": "RandomForestRegressor",
            "feature_columns": self.feature_columns,
            "feature_importances": self.get_feature_importances(),
            "config": self.config,
        }
        if metadata:
            meta_to_save.update(metadata)

        with open(out_path / "training_metadata.json", "w", encoding="utf-8") as f:
            json.dump(meta_to_save, f, indent=2, default=str)

    @classmethod
    def load(cls, model_dir: Union[str, Path]) -> "ExpectedScoreRFModel":
        """
        Load trained model from directory.

        Args:
            model_dir: Path to model directory.

        Returns:
            Loaded ExpectedScoreRFModel instance.
        """
        m_path = Path(model_dir)
        with open(m_path / "config.json", "r", encoding="utf-8") as f:
            config = json.load(f)

        instance = cls(**config)
        instance.model = joblib.load(m_path / "expected_score_rf.joblib")

        with open(m_path / "feature_names.json", "r", encoding="utf-8") as f:
            instance.feature_columns = json.load(f)

        instance.is_fitted = True
        return instance
