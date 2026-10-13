"""
Phase-Specific Expected Scoring Models & Baselines.

Implements dedicated models and baselines for each checkpoint:
1. Powerplay Model & Baseline (Target: score_at_6)
2. Middle Model & Baseline (Target: score_at_15)
3. Death Model & Baseline (Target: final_team_score)
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

from src.phase_expected_dataset import (
    DEATH_FEATURE_COLUMNS,
    MID_FEATURE_COLUMNS,
    PP_FEATURE_COLUMNS,
    TARGET_FINAL,
    TARGET_MID,
    TARGET_PP,
)

PHASE_MAPPING = {
    "POWERPLAY": 0,
    "MIDDLE": 1,
    "DEATH": 2,
}


# ======================================================================
# Baselines
# ======================================================================

class PowerplayBaseline:
    """
    Baseline for Powerplay: Current run rate extrapolated to the end of over 6.

    Formula:
        projected_6 = current_team_runs + (current_team_rr * (balls_remaining_until_6 / 6.0))
    """

    def __init__(self) -> None:
        self.name = "Powerplay RR Extrapolation (Over 6)"

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        runs = X["current_team_runs"].to_numpy(dtype=float)
        rr = X["current_team_rr"].to_numpy(dtype=float)
        balls_rem = X["balls_remaining_until_6"].to_numpy(dtype=float)
        return runs + (rr * (balls_rem / 6.0))


class MiddleBaseline:
    """
    Baseline for Middle Overs: Current run rate extrapolated to the end of over 15.

    Formula:
        projected_15 = current_team_runs + (current_team_rr * (balls_remaining_until_15 / 6.0))
    """

    def __init__(self) -> None:
        self.name = "Middle RR Extrapolation (Over 15)"

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        runs = X["current_team_runs"].to_numpy(dtype=float)
        rr = X["current_team_rr"].to_numpy(dtype=float)
        balls_rem = X["balls_remaining_until_15"].to_numpy(dtype=float)
        return runs + (rr * (balls_rem / 6.0))


class DeathBaseline:
    """
    Baseline for Death Overs: Current run rate extrapolated to the end of the innings.

    Formula:
        projected_final = current_team_runs + (current_team_rr * (balls_remaining_in_innings / 6.0))
    """

    def __init__(self) -> None:
        self.name = "Death RR Extrapolation (Final Score)"

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        runs = X["current_team_runs"].to_numpy(dtype=float)
        rr = X["current_team_rr"].to_numpy(dtype=float)
        balls_rem = X["balls_remaining_in_innings"].to_numpy(dtype=float)
        return runs + (rr * (balls_rem / 6.0))


class PhaseConditionalHistoricalBaseline:
    """
    Historical conditional average baseline for a specific checkpoint target.

    Formula:
        projected = current_team_runs + E[remaining_runs_to_checkpoint | overs_completed]
    """

    def __init__(self, target_name: str) -> None:
        self.target_name = target_name
        self.conditional_runs_added_: Dict[float, float] = {}
        self.global_target_mean_: float = 0.0

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "PhaseConditionalHistoricalBaseline":
        self.global_target_mean_ = float(y.mean())
        runs_added = y - X["current_team_runs"]
        temp_df = pd.DataFrame({
            "overs_completed": X["overs_completed"],
            "runs_added": runs_added,
        })
        self.conditional_runs_added_ = (
            temp_df.groupby("overs_completed")["runs_added"].mean().to_dict()
        )
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        runs = X["current_team_runs"].to_numpy(dtype=float)
        overs = X["overs_completed"].to_list()
        fallback = self.global_target_mean_ - float(np.mean(runs))
        added = np.array(
            [self.conditional_runs_added_.get(ov, fallback) for ov in overs],
            dtype=float,
        )
        return runs + added


# ======================================================================
# Random Forest Model Wrapper
# ======================================================================

class PhaseRFModel:
    """
    General Random Forest model for checkpoint expected score prediction.
    """

    def __init__(
        self,
        feature_columns: List[str],
        target_name: str,
        n_estimators: int = 100,
        max_depth: int = 10,
        min_samples_split: int = 10,
        min_samples_leaf: int = 5,
        random_state: int = 42,
        n_jobs: int = -1,
    ) -> None:
        self.feature_columns = list(feature_columns)
        self.target_name = target_name
        self.config: Dict[str, Any] = {
            "feature_columns": self.feature_columns,
            "target_name": self.target_name,
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
        self.is_fitted: bool = False

    def _prepare_features(self, X: pd.DataFrame) -> pd.DataFrame:
        missing = [col for col in self.feature_columns if col not in X.columns]
        if missing:
            raise ValueError(f"Missing required feature columns: {missing}")

        X_prep = X[self.feature_columns].copy()
        if "innings_phase" in X_prep.columns and X_prep["innings_phase"].dtype == "object":
            X_prep["innings_phase"] = X_prep["innings_phase"].map(PHASE_MAPPING).fillna(0)

        for col in self.feature_columns:
            X_prep[col] = pd.to_numeric(X_prep[col], errors="coerce").fillna(0)

        return X_prep

    def fit(self, X: pd.DataFrame, y: Union[pd.Series, np.ndarray]) -> "PhaseRFModel":
        X_prep = self._prepare_features(X)
        y_arr = np.asarray(y, dtype=float)
        self.model.fit(X_prep, y_arr)
        self.is_fitted = True
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("Model is not fitted. Call fit() first.")
        X_prep = self._prepare_features(X)
        return self.model.predict(X_prep)

    def get_feature_importances(self) -> Dict[str, float]:
        if not self.is_fitted:
            raise RuntimeError("Model is not fitted.")
        importances = self.model.feature_importances_
        return {
            feat: float(round(imp, 6))
            for feat, imp in zip(self.feature_columns, importances)
        }

    def save(self, filepath: Union[str, Path]) -> None:
        p = Path(filepath)
        p.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({
            "model": self.model,
            "feature_columns": self.feature_columns,
            "target_name": self.target_name,
            "config": self.config,
        }, p)

    @classmethod
    def load(cls, filepath: Union[str, Path]) -> "PhaseRFModel":
        p = Path(filepath)
        data = joblib.load(p)
        config = dict(data["config"])
        feat_cols = config.pop("feature_columns", None)
        tgt_name = config.pop("target_name", None)

        if cls is PhaseRFModel:
            instance = cls(
                feature_columns=feat_cols,
                target_name=tgt_name,
                **config
            )
        else:
            instance = cls(**config)

        instance.model = data["model"]
        instance.feature_columns = feat_cols
        instance.target_name = tgt_name
        instance.is_fitted = True
        return instance


# Concrete sub-models for clean semantic interfaces
class PowerplayRFModel(PhaseRFModel):
    def __init__(self, **kwargs) -> None:
        kwargs.pop("feature_columns", None)
        kwargs.pop("target_name", None)
        super().__init__(feature_columns=PP_FEATURE_COLUMNS, target_name=TARGET_PP, **kwargs)


class MiddleRFModel(PhaseRFModel):
    def __init__(self, **kwargs) -> None:
        kwargs.pop("feature_columns", None)
        kwargs.pop("target_name", None)
        super().__init__(feature_columns=MID_FEATURE_COLUMNS, target_name=TARGET_MID, **kwargs)


class DeathRFModel(PhaseRFModel):
    def __init__(self, **kwargs) -> None:
        kwargs.pop("feature_columns", None)
        kwargs.pop("target_name", None)
        super().__init__(feature_columns=DEATH_FEATURE_COLUMNS, target_name=TARGET_FINAL, **kwargs)
