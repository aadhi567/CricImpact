"""
Expected Batter Performance Models & Baselines (Phase 4A).

Builds two separate contextual expectation models:
1. ExpectedRunsRFModel: Predicts expected batter runs given entry situation.
2. ExpectedSRRFModel: Predicts expected batter strike rate given entry situation.

Leakage Prevention Audit:
Input features strictly reflect the match state AT THE MOMENT OF ENTRY:
- Batting position
- Entry over & balls remaining in innings
- Wickets in hand (wickets remaining)
- Current team score & run rate at entry
- Innings phase at entry
- Expected final team score at entry (or target)
- Chase information (is_chase, required_rr_at_entry, runs_required_at_entry)

Forbidden as features:
- Actual runs scored in this innings
- Actual balls faced in this innings
- Actual strike rate in this innings
- Actual boundaries / dot balls in this innings
- Dismissal status / kind
- Match result / winner / margin
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

# Ensure repository root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Audited feature lists
BATTER_FEATURE_COLUMNS = [
    "batting_position",
    "entry_over_num",
    "entry_balls_remaining",
    "entry_wickets_remaining",
    "entry_team_runs",
    "entry_rr",
    "entry_phase_code",
    "is_chase_code",
    "required_rr_at_entry_clean",
    "runs_required_at_entry_clean",
    "expected_final_score_at_entry",
]

PHASE_CODE_MAP = {"POWERPLAY": 0, "MIDDLE": 1, "DEATH": 2}


def prepare_batter_model_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract and encode strictly non-leaking entry situation features.
    """
    X = pd.DataFrame(index=df.index)

    X["batting_position"] = df["batting_position"].fillna(4).astype(int)
    # Entry over numeric
    X["entry_over_num"] = df["entry_over"].fillna(0.0).astype(float)
    X["entry_balls_remaining"] = df["entry_balls_remaining"].fillna(120).astype(int)
    X["entry_wickets_remaining"] = df["entry_wickets_remaining"].fillna(10).astype(int)
    entry_score_col = "entry_score" if "entry_score" in df.columns else "entry_team_runs"
    X["entry_team_runs"] = df[entry_score_col].fillna(0).astype(int)

    entry_rr_col = "entry_team_rr" if "entry_team_rr" in df.columns else "entry_rr"
    X["entry_rr"] = df[entry_rr_col].fillna(0.0).astype(float)

    # Phase code
    phase_str = df["entry_phase"].fillna("POWERPLAY").astype(str).str.upper()
    X["entry_phase_code"] = phase_str.map(PHASE_CODE_MAP).fillna(0).astype(int)

    # Chase variables
    if "is_chase" in df.columns:
        is_ch = df["is_chase"].fillna(False).astype(bool)
    else:
        inn_col = df.get("innings", df.get("innings_number", 1))
        is_ch = (inn_col == 2)
    X["is_chase_code"] = is_ch.astype(int)

    req_rr_col = "required_rr_entry" if "required_rr_entry" in df.columns else "required_rr_at_entry"
    runs_req_col = "runs_required_entry" if "runs_required_entry" in df.columns else "runs_required_at_entry"
    X["required_rr_at_entry_clean"] = np.where(is_ch, df[req_rr_col].fillna(0.0), 0.0)
    X["runs_required_at_entry_clean"] = np.where(is_ch, df[runs_req_col].fillna(0.0), 0.0)

    # Situational benchmark: For first innings, expected final total from Phase 3 model.
    # For chases, the actual target score (fixed goal).
    if "expected_final_entry" in df.columns:
        exp_score = df["expected_final_entry"]
    elif "expected_final_score_at_entry" in df.columns:
        exp_score = df["expected_final_score_at_entry"]
    else:
        exp_score = pd.Series(np.nan, index=df.index)

    tgt = df["target"] if "target" in df.columns else pd.Series(np.nan, index=df.index)
    benchmark_final = np.where(is_ch, tgt.fillna(165.0), exp_score.fillna(165.0))
    X["expected_final_score_at_entry"] = pd.Series(benchmark_final, index=df.index).astype(float)

    return X[BATTER_FEATURE_COLUMNS]


# ======================================================================
# Baseline Models
# ======================================================================

class ExpectedRunsBaselines:
    """
    Historical contextual baselines for Expected Batter Runs.
    """

    def __init__(self) -> None:
        self.global_mean: float = 0.0
        self.position_means: Dict[int, float] = {}
        self.phase_means: Dict[str, float] = {}
        self.over_means: Dict[int, float] = {}

    def fit(self, df: pd.DataFrame) -> "ExpectedRunsBaselines":
        self.global_mean = float(df["runs"].mean())
        self.position_means = df.groupby("batting_position")["runs"].mean().to_dict()
        self.phase_means = df.groupby("entry_phase")["runs"].mean().to_dict()
        ov_int = df["entry_over"].fillna(0.0).round().astype(int)
        self.over_means = df.groupby(ov_int)["runs"].mean().to_dict()
        return self

    def predict_global(self, df: pd.DataFrame) -> np.ndarray:
        return np.full(len(df), self.global_mean, dtype=float)

    def predict_position(self, df: pd.DataFrame) -> np.ndarray:
        return df["batting_position"].map(self.position_means).fillna(self.global_mean).to_numpy(dtype=float)

    def predict_phase(self, df: pd.DataFrame) -> np.ndarray:
        return df["entry_phase"].map(self.phase_means).fillna(self.global_mean).to_numpy(dtype=float)

    def predict_over(self, df: pd.DataFrame) -> np.ndarray:
        ov_int = df["entry_over"].fillna(0.0).round().astype(int)
        return ov_int.map(self.over_means).fillna(self.global_mean).to_numpy(dtype=float)


class ExpectedSRBaselines:
    """
    Historical contextual baselines for Expected Batter Strike Rate.
    """

    def __init__(self) -> None:
        self.global_mean: float = 0.0
        self.position_means: Dict[int, float] = {}
        self.phase_means: Dict[str, float] = {}
        self.over_means: Dict[int, float] = {}

    def fit(self, df: pd.DataFrame) -> "ExpectedSRBaselines":
        # Fit on batters who faced at least 1 ball
        valid = df[df["balls_faced"] > 0]
        self.global_mean = float(valid["strike_rate"].mean())
        self.position_means = valid.groupby("batting_position")["strike_rate"].mean().to_dict()
        self.phase_means = valid.groupby("entry_phase")["strike_rate"].mean().to_dict()
        ov_int = valid["entry_over"].fillna(0.0).round().astype(int)
        self.over_means = valid.groupby(ov_int)["strike_rate"].mean().to_dict()
        return self

    def predict_global(self, df: pd.DataFrame) -> np.ndarray:
        return np.full(len(df), self.global_mean, dtype=float)

    def predict_position(self, df: pd.DataFrame) -> np.ndarray:
        return df["batting_position"].map(self.position_means).fillna(self.global_mean).to_numpy(dtype=float)

    def predict_phase(self, df: pd.DataFrame) -> np.ndarray:
        return df["entry_phase"].map(self.phase_means).fillna(self.global_mean).to_numpy(dtype=float)

    def predict_over(self, df: pd.DataFrame) -> np.ndarray:
        ov_int = df["entry_over"].fillna(0.0).round().astype(int)
        return ov_int.map(self.over_means).fillna(self.global_mean).to_numpy(dtype=float)


# ======================================================================
# Machine Learning Models
# ======================================================================

class ExpectedRunsRFModel:
    """
    Random Forest Regressor predicting expected runs for a batter walking in.
    """

    def __init__(
        self,
        n_estimators: int = 100,
        max_depth: int = 8,
        min_samples_split: int = 20,
        min_samples_leaf: int = 10,
        random_state: int = 42,
        n_jobs: int = -1
    ) -> None:
        self.config = {
            "n_estimators": n_estimators,
            "max_depth": max_depth,
            "min_samples_split": min_samples_split,
            "min_samples_leaf": min_samples_leaf,
            "random_state": random_state,
            "n_jobs": n_jobs,
        }
        self.model = RandomForestRegressor(**self.config)
        self.is_fitted: bool = False

    def fit(self, df: pd.DataFrame, y: Optional[pd.Series] = None) -> "ExpectedRunsRFModel":
        X = prepare_batter_model_features(df)
        y_arr = np.asarray(df["runs"] if y is None else y, dtype=float)
        self.model.fit(X, y_arr)
        self.is_fitted = True
        return self

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("Model is not fitted.")
        X = prepare_batter_model_features(df)
        return np.maximum(0.0, self.model.predict(X))

    def get_feature_importances(self) -> Dict[str, float]:
        if not self.is_fitted:
            raise RuntimeError("Model is not fitted.")
        return {
            feat: float(round(imp, 6))
            for feat, imp in zip(BATTER_FEATURE_COLUMNS, self.model.feature_importances_)
        }

    def save(self, filepath: Union[str, Path]) -> None:
        p = Path(filepath)
        p.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"model": self.model, "config": self.config}, p)

    @classmethod
    def load(cls, filepath: Union[str, Path]) -> "ExpectedRunsRFModel":
        data = joblib.load(filepath)
        instance = cls(**data["config"])
        instance.model = data["model"]
        instance.is_fitted = True
        return instance


class ExpectedSRRFModel:
    """
    Random Forest Regressor predicting expected strike rate for a batter walking in.
    """

    def __init__(
        self,
        n_estimators: int = 100,
        max_depth: int = 8,
        min_samples_split: int = 20,
        min_samples_leaf: int = 10,
        random_state: int = 42,
        n_jobs: int = -1
    ) -> None:
        self.config = {
            "n_estimators": n_estimators,
            "max_depth": max_depth,
            "min_samples_split": min_samples_split,
            "min_samples_leaf": min_samples_leaf,
            "random_state": random_state,
            "n_jobs": n_jobs,
        }
        self.model = RandomForestRegressor(**self.config)
        self.is_fitted: bool = False

    def fit(self, df: pd.DataFrame, y: Optional[pd.Series] = None) -> "ExpectedSRRFModel":
        # Fit on batters who faced at least 1 ball
        valid = df[df["balls_faced"] > 0] if "balls_faced" in df.columns else df
        X = prepare_batter_model_features(valid)
        y_arr = np.asarray(valid["strike_rate"] if y is None else y, dtype=float)
        self.model.fit(X, y_arr)
        self.is_fitted = True
        return self

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("Model is not fitted.")
        X = prepare_batter_model_features(df)
        return np.maximum(0.0, self.model.predict(X))

    def get_feature_importances(self) -> Dict[str, float]:
        if not self.is_fitted:
            raise RuntimeError("Model is not fitted.")
        return {
            feat: float(round(imp, 6))
            for feat, imp in zip(BATTER_FEATURE_COLUMNS, self.model.feature_importances_)
        }

    def save(self, filepath: Union[str, Path]) -> None:
        p = Path(filepath)
        p.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"model": self.model, "config": self.config}, p)

    @classmethod
    def load(cls, filepath: Union[str, Path]) -> "ExpectedSRRFModel":
        data = joblib.load(filepath)
        instance = cls(**data["config"])
        instance.model = data["model"]
        instance.is_fitted = True
        return instance


# ======================================================================
# Deviations and Performance Ratios
# ======================================================================

def compute_deviations_and_ratios(
    actual_runs: Union[pd.Series, np.ndarray],
    expected_runs: Union[pd.Series, np.ndarray],
    actual_sr: Union[pd.Series, np.ndarray],
    expected_sr: Union[pd.Series, np.ndarray]
) -> Dict[str, np.ndarray]:
    """
    Compute separate run and strike rate deviations and performance ratios.

    DOES NOT combine them into a single score.
    """
    act_r = np.asarray(actual_runs, dtype=float)
    exp_r = np.asarray(expected_runs, dtype=float)
    act_s = np.asarray(actual_sr, dtype=float)
    exp_s = np.asarray(expected_sr, dtype=float)

    # 1. Deviations
    run_dev = np.round(act_r - exp_r, 2)
    sr_dev = np.round(act_s - exp_s, 2)

    # 2. Performance Ratios (handle zero denominator safely)
    safe_exp_r = np.where(exp_r > 0, exp_r, np.nan)
    safe_exp_s = np.where(exp_s > 0, exp_s, np.nan)

    run_ratio = np.round(act_r / safe_exp_r, 2)
    sr_ratio = np.round(act_s / safe_exp_s, 2)

    return {
        "run_deviation": run_dev,
        "sr_deviation": sr_dev,
        "run_performance_ratio": run_ratio,
        "sr_performance_ratio": sr_ratio,
    }
