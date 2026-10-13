"""
Evaluation and Visualization Pipeline for Expected Final Score Model.

Calculates:
- Overall metrics: MAE, RMSE, R² for Baseline 1 (Simple Projection), Baseline 2 (Historical Average), and Random Forest.
- Phase-wise breakdown: POWERPLAY, MIDDLE, and DEATH overs.
- 10+ real unseen test prediction comparisons.
- Visualizations:
  1. Actual vs Predicted Final Score
  2. Prediction Error Distribution
  3. MAE by Innings Phase
  4. Feature Importance
- Persistence of metrics, train/test split match IDs, and full report.
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for headless plotting
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error

# Ensure repository root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.expected_score_dataset import (
    FEATURE_COLUMNS,
    TARGET_COLUMN,
    SamplingConfig,
    load_expected_score_dataset,
    split_train_test_by_match,
    split_train_test_by_season,
)
from src.expected_score_model import (
    ExpectedScoreRFModel,
    HistoricalAverageBaseline,
    SimpleProjectionBaseline,
)


def calculate_metrics(y_true: Union[pd.Series, np.ndarray], y_pred: Union[pd.Series, np.ndarray]) -> Dict[str, float]:
    """
    Calculate regression evaluation metrics: MAE, RMSE, and R².

    Args:
        y_true: Ground truth target values.
        y_pred: Model predictions.

    Returns:
        Dict containing MAE, RMSE, and R² rounded to 4 decimal places.
    """
    y_t = np.asarray(y_true, dtype=float)
    y_p = np.asarray(y_pred, dtype=float)

    mae = float(mean_absolute_error(y_t, y_p))
    rmse = float(root_mean_squared_error(y_t, y_p))
    r2 = float(r2_score(y_t, y_p))

    return {
        "MAE": round(mae, 4),
        "RMSE": round(rmse, 4),
        "R2": round(r2, 4),
    }


def evaluate_by_phase(
    df: pd.DataFrame,
    y_true_col: str,
    y_pred_col: str,
    phase_col: str = "innings_phase"
) -> Dict[str, Dict[str, Any]]:
    """
    Calculate MAE, RMSE, and R² grouped by innings phase.

    Args:
        df: DataFrame containing evaluation data.
        y_true_col: Column name of actual final score.
        y_pred_col: Column name of predicted final score.
        phase_col: Column name of innings phase.

    Returns:
        Dict mapping phase name to its metric dictionary and sample count.
    """
    phases = ["POWERPLAY", "MIDDLE", "DEATH"]
    results: Dict[str, Dict[str, Any]] = {}

    for phase in phases:
        sub = df[df[phase_col] == phase]
        if len(sub) > 0:
            metrics = calculate_metrics(sub[y_true_col], sub[y_pred_col])
            metrics["sample_count"] = int(len(sub))
            results[phase] = metrics
        else:
            results[phase] = {"MAE": 0.0, "RMSE": 0.0, "R2": 0.0, "sample_count": 0}

    # Also compute overall
    overall = calculate_metrics(df[y_true_col], df[y_pred_col])
    overall["sample_count"] = int(len(df))
    results["OVERALL"] = overall

    return results


def select_prediction_examples(
    test_df: pd.DataFrame,
    pred_baseline_col: str = "pred_baseline",
    pred_rf_col: str = "pred_rf",
    n: int = 10,
    random_state: int = 42
) -> List[Dict[str, Any]]:
    """
    Select diverse, real unseen test match states and format prediction comparisons.

    Args:
        test_df: Test set DataFrame with actual scores and predictions.
        pred_baseline_col: Column name for simple projection baseline.
        pred_rf_col: Column name for Random Forest prediction.
        n: Number of examples to select.
        random_state: Fixed random seed.

    Returns:
        List of formatted example dictionaries.
    """
    rng = np.random.default_rng(random_state)

    # Stratify selection across powerplay, middle, and death overs for diversity
    pp = test_df[test_df["innings_phase"] == "POWERPLAY"]
    mid = test_df[test_df["innings_phase"] == "MIDDLE"]
    dth = test_df[test_df["innings_phase"] == "DEATH"]

    n_pp = max(2, n // 4)
    n_dth = max(2, n // 4)
    n_mid = n - n_pp - n_dth

    idx_pp = rng.choice(pp.index, size=min(n_pp, len(pp)), replace=False)
    idx_mid = rng.choice(mid.index, size=min(n_mid, len(mid)), replace=False)
    idx_dth = rng.choice(dth.index, size=min(n_dth, len(dth)), replace=False)

    chosen_indices = np.concatenate([idx_pp, idx_mid, idx_dth])
    sample_rows = test_df.loc[chosen_indices].sort_values(
        by=["match_id", "overs_completed"]
    )

    examples: List[Dict[str, Any]] = []
    for _, row in sample_rows.iterrows():
        act = float(row[TARGET_COLUMN])
        base_p = float(row[pred_baseline_col])
        rf_p = float(row[pred_rf_col])

        examples.append({
            "match_id": str(row["match_id"]),
            "season": str(row.get("season", "N/A")),
            "batting_team": str(row.get("batting_team", "N/A")),
            "bowling_team": str(row.get("bowling_team", "N/A")),
            "over": float(row["overs_completed"]),
            "current_score": int(row["current_team_runs"]),
            "wickets_lost": int(row["wickets_lost_so_far"]),
            "wickets_remaining": int(row["wickets_remaining"]),
            "current_rr": round(float(row["current_team_rr"]), 2),
            "innings_phase": str(row["innings_phase"]),
            "actual_final_score": int(act),
            "simple_projection": round(base_p, 1),
            "rf_prediction": round(rf_p, 1),
            "baseline_abs_error": round(abs(act - base_p), 1),
            "rf_abs_error": round(abs(act - rf_p), 1),
        })

    return examples


def generate_evaluation_plots(
    test_df: pd.DataFrame,
    feature_importances: Dict[str, float],
    phase_metrics_baseline: Dict[str, Dict[str, Any]],
    phase_metrics_rf: Dict[str, Dict[str, Any]],
    output_dir: Union[str, Path]
) -> List[str]:
    """
    Generate and save evaluation plots:
    1. Actual vs Predicted Final Score
    2. Prediction Error Distribution
    3. MAE by Innings Phase
    4. Feature Importance

    Args:
        test_df: Test set DataFrame with predictions.
        feature_importances: Dict of RF feature importances.
        phase_metrics_baseline: Phase metrics for baseline.
        phase_metrics_rf: Phase metrics for Random Forest.
        output_dir: Directory where plots should be saved.

    Returns:
        List of generated plot file paths.
    """
    plot_dir = Path(output_dir)
    plot_dir.mkdir(parents=True, exist_ok=True)
    generated_plots: List[str] = []

    # Styling configuration
    plt.style.use("tableau-colorblind10" if "tableau-colorblind10" in plt.style.available else "default")
    plt.rcParams["font.sans-serif"] = "DejaVu Sans"
    plt.rcParams["font.size"] = 10

    # -------------------------------------------------------------
    # Plot 1: Actual vs Predicted Final Score (Random Forest)
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8, 7), dpi=150)
    y_true = test_df[TARGET_COLUMN].to_numpy()
    y_pred_rf = test_df["pred_rf"].to_numpy()

    # Scatter colored by phase
    phase_colors = {"POWERPLAY": "#1f77b4", "MIDDLE": "#2ca02c", "DEATH": "#d62728"}
    for phase, color in phase_colors.items():
        mask = test_df["innings_phase"] == phase
        ax.scatter(
            y_true[mask],
            y_pred_rf[mask],
            alpha=0.35,
            label=f"{phase} (n={mask.sum()})",
            color=color,
            s=18,
            edgecolors="none"
        )

    # Reference diagonal y = x
    min_val = min(y_true.min(), y_pred_rf.min()) - 10
    max_val = max(y_true.max(), y_pred_rf.max()) + 10
    ax.plot([min_val, max_val], [min_val, max_val], "k--", alpha=0.8, linewidth=1.5, label="Perfect Prediction (y = x)")

    ax.set_xlim(min_val, max_val)
    ax.set_ylim(min_val, max_val)
    ax.set_xlabel("Actual Final Team Score", fontsize=11, fontweight="bold")
    ax.set_ylabel("Predicted Final Team Score (RF)", fontsize=11, fontweight="bold")
    ax.set_title("Actual vs Predicted Final Score (Test Set)", fontsize=13, fontweight="bold", pad=12)
    ax.legend(frameon=True, loc="upper left")
    ax.grid(True, linestyle=":", alpha=0.6)

    p1_path = plot_dir / "actual_vs_predicted.png"
    plt.tight_layout()
    plt.savefig(p1_path)
    plt.close(fig)
    generated_plots.append(str(p1_path))

    # -------------------------------------------------------------
    # Plot 2: Prediction Error Distribution (Residuals)
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8, 6), dpi=150)
    err_rf = test_df["pred_rf"] - test_df[TARGET_COLUMN]
    err_base = test_df["pred_baseline"] - test_df[TARGET_COLUMN]

    # Clip extreme baseline outliers for readability in plot
    err_base_clipped = np.clip(err_base, -80, 80)
    err_rf_clipped = np.clip(err_rf, -80, 80)

    bins = np.linspace(-70, 70, 50)
    ax.hist(err_base_clipped, bins=bins, alpha=0.45, label=f"Simple Baseline (std={err_base.std():.1f})", color="#e74c3c", density=True)
    ax.hist(err_rf_clipped, bins=bins, alpha=0.65, label=f"Random Forest (std={err_rf.std():.1f})", color="#2980b9", density=True)

    ax.axvline(0, color="black", linestyle="--", linewidth=1.2, alpha=0.8)
    ax.set_xlabel("Prediction Error (Predicted - Actual Runs)", fontsize=11, fontweight="bold")
    ax.set_ylabel("Density", fontsize=11, fontweight="bold")
    ax.set_title("Prediction Error Distribution (Residuals)", fontsize=13, fontweight="bold", pad=12)
    ax.legend(frameon=True, loc="upper right")
    ax.grid(True, linestyle=":", alpha=0.6)

    p2_path = plot_dir / "prediction_error_distribution.png"
    plt.tight_layout()
    plt.savefig(p2_path)
    plt.close(fig)
    generated_plots.append(str(p2_path))

    # -------------------------------------------------------------
    # Plot 3: MAE by Innings Phase
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8, 5.5), dpi=150)
    categories = ["POWERPLAY", "MIDDLE", "DEATH", "OVERALL"]

    base_maes = [phase_metrics_baseline[cat]["MAE"] for cat in categories]
    rf_maes = [phase_metrics_rf[cat]["MAE"] for cat in categories]

    x = np.arange(len(categories))
    width = 0.35

    rects1 = ax.bar(x - width / 2, base_maes, width, label="Simple Projection Baseline", color="#e74c3c", alpha=0.85)
    rects2 = ax.bar(x + width / 2, rf_maes, width, label="Random Forest", color="#27ae60", alpha=0.85)

    ax.set_ylabel("Mean Absolute Error (Runs)", fontsize=11, fontweight="bold")
    ax.set_title("Mean Absolute Error (MAE) by Innings Phase", fontsize=13, fontweight="bold", pad=12)
    ax.set_xticks(x)
    ax.set_xticklabels(["Powerplay\n(Overs 1–6)", "Middle Overs\n(Overs 7–15)", "Death Overs\n(Overs 16–19)", "Overall\n(All Overs)"], fontsize=10)
    ax.legend(frameon=True)
    ax.grid(True, axis="y", linestyle=":", alpha=0.6)

    # Attach values on top of bars
    def autolabel(rects):
        for rect in rects:
            height = rect.get_height()
            ax.annotate(
                f"{height:.1f}",
                xy=(rect.get_x() + rect.get_width() / 2, height),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontweight="bold",
                fontsize=9
            )

    autolabel(rects1)
    autolabel(rects2)

    p3_path = plot_dir / "mae_by_phase.png"
    plt.tight_layout()
    plt.savefig(p3_path)
    plt.close(fig)
    generated_plots.append(str(p3_path))

    # -------------------------------------------------------------
    # Plot 4: Feature Importance
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8, 5), dpi=150)
    sorted_features = sorted(feature_importances.items(), key=lambda kv: kv[1], reverse=True)
    feat_names = [k for k, _ in sorted_features][::-1]
    importances = [v for _, v in sorted_features][::-1]

    y_pos = np.arange(len(feat_names))
    bars = ax.barh(y_pos, importances, color="#3498db", alpha=0.85, edgecolor="#2980b9")

    ax.set_yticks(y_pos)
    ax.set_yticklabels(feat_names, fontsize=10)
    ax.set_xlabel("Relative Importance (Gini)", fontsize=11, fontweight="bold")
    ax.set_title("Random Forest Feature Importances", fontsize=13, fontweight="bold", pad=12)
    ax.grid(True, axis="x", linestyle=":", alpha=0.6)

    for bar in bars:
        width_val = bar.get_width()
        ax.annotate(
            f"{width_val:.3f}",
            xy=(width_val, bar.get_y() + bar.get_height() / 2),
            xytext=(4, 0),
            textcoords="offset points",
            ha="left",
            va="center",
            fontsize=9,
            fontweight="bold"
        )

    ax.set_xlim(0, max(importances) * 1.15)
    p4_path = plot_dir / "feature_importance.png"
    plt.tight_layout()
    plt.savefig(p4_path)
    plt.close(fig)
    generated_plots.append(str(p4_path))

    return generated_plots


def run_pipeline(
    match_state_path: str = "data/processed/match_state.csv",
    innings_path: str = "data/processed/innings.csv",
    output_dir: str = "models/expected_score",
    test_size: float = 0.2,
    random_state: int = 42,
) -> Dict[str, Any]:
    """
    Execute the complete end-to-end Expected Score pipeline:
    1. Load and sample non-leaking intermediate match states.
    2. Split train/test strictly by match ID (80/20).
    3. Also perform secondary season-based validation.
    4. Fit and evaluate Baselines (Simple Projection & Historical Average).
    5. Fit and evaluate Random Forest.
    6. Break down errors by phase.
    7. Select and format 10+ real test prediction examples.
    8. Generate evaluation plots.
    9. Persist model, metadata, metrics, and documentation.

    Args:
        match_state_path: Path to match_state.csv.
        innings_path: Path to innings.csv.
        output_dir: Directory to save model artifacts.
        test_size: Test proportion for match-level split (0.2).
        random_state: Fixed seed (42).

    Returns:
        Comprehensive report dictionary.
    """
    out_dir = Path(output_dir)
    plots_dir = out_dir / "plots"
    out_dir.mkdir(parents=True, exist_ok=True)
    plots_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("PHASE 3 PART 1: EXPECTED FINAL SCORE MODEL PIPELINE")
    print("=" * 60)

    # 1. Dataset loading and sampling
    config = SamplingConfig(strategy="end_of_over", min_over=1, max_over=19)
    print("\n[1/7] Loading data and sampling intermediate match states...")
    df, meta = load_expected_score_dataset(
        match_state_path=match_state_path,
        innings_path=innings_path,
        config=config,
    )
    print(f"  Total raw first innings:    {meta['total_raw_first_innings']}")
    print(f"  Excluded rain/incomplete:   {meta['excluded_matches_count']}")
    print(f"  Usable first innings:       {meta['usable_first_innings']}")
    print(f"  Total sampled match states: {meta['total_sampled_states']}")

    # 2. Match-level train/test split
    print(f"\n[2/7] Splitting by Match ID ({int((1-test_size)*100)}% train / {int(test_size*100)}% test, seed={random_state})...")
    train_df, test_df, train_matches, test_matches = split_train_test_by_match(
        df, test_size=test_size, random_state=random_state
    )
    print(f"  Train matches: {len(train_matches)} | Train states: {len(train_df)}")
    print(f"  Test matches:  {len(test_matches)} | Test states:  {len(test_df)}")

    # 3. Fit Baselines
    print("\n[3/7] Computing Baselines...")
    baseline_simple = SimpleProjectionBaseline()
    test_df["pred_baseline"] = baseline_simple.predict(test_df)

    baseline_hist_cond = HistoricalAverageBaseline(mode="conditional")
    baseline_hist_cond.fit(train_df, train_df[TARGET_COLUMN])
    test_df["pred_hist_cond"] = baseline_hist_cond.predict(test_df)

    baseline_hist_global = HistoricalAverageBaseline(mode="global")
    baseline_hist_global.fit(train_df, train_df[TARGET_COLUMN])
    test_df["pred_hist_global"] = baseline_hist_global.predict(test_df)

    # 4. Fit Random Forest
    print("\n[4/7] Training RandomForestRegressor...")
    rf_model = ExpectedScoreRFModel(
        n_estimators=100,
        max_depth=12,
        min_samples_split=10,
        min_samples_leaf=5,
        random_state=random_state,
        n_jobs=-1,
    )
    rf_model.fit(train_df, train_df[TARGET_COLUMN])
    test_df["pred_rf"] = rf_model.predict(test_df)

    # 5. Evaluate overall & phase metrics
    print("\n[5/7] Evaluating models...")
    y_true = test_df[TARGET_COLUMN].to_numpy()

    metrics_base_simple = calculate_metrics(y_true, test_df["pred_baseline"])
    metrics_hist_cond = calculate_metrics(y_true, test_df["pred_hist_cond"])
    metrics_hist_global = calculate_metrics(y_true, test_df["pred_hist_global"])
    metrics_rf = calculate_metrics(y_true, test_df["pred_rf"])

    phase_base_simple = evaluate_by_phase(test_df, TARGET_COLUMN, "pred_baseline")
    phase_rf = evaluate_by_phase(test_df, TARGET_COLUMN, "pred_rf")

    print(f"  Baseline 1 (Simple RR):      MAE={metrics_base_simple['MAE']:.2f}, RMSE={metrics_base_simple['RMSE']:.2f}, R2={metrics_base_simple['R2']:.4f}")
    print(f"  Baseline 2 (Hist Over Mean): MAE={metrics_hist_cond['MAE']:.2f}, RMSE={metrics_hist_cond['RMSE']:.2f}, R2={metrics_hist_cond['R2']:.4f}")
    print(f"  Random Forest Model:         MAE={metrics_rf['MAE']:.2f}, RMSE={metrics_rf['RMSE']:.2f}, R2={metrics_rf['R2']:.4f}")

    rf_outperformed_baseline = metrics_rf["MAE"] < metrics_base_simple["MAE"]
    print(f"  Did Random Forest outperform Simple Baseline? {'YES (Significantly)' if rf_outperformed_baseline else 'NO'}")

    # Feature importances
    feat_importances = rf_model.get_feature_importances()
    print("\n  Feature Importances:")
    for feat, imp in sorted(feat_importances.items(), key=lambda x: x[1], reverse=True):
        print(f"    - {feat:30s}: {imp:.4f}")

    # 6. Secondary Season Validation
    print("\n[6/7] Running Secondary Season-based Validation (Train <=2024, Test 2025-2026)...")
    season_train_df, season_test_df, s_train_m, s_test_m = split_train_test_by_season(
        df, cutoff_season="2025"
    )
    rf_season = ExpectedScoreRFModel(
        n_estimators=100, max_depth=12, min_samples_split=10, min_samples_leaf=5, random_state=random_state, n_jobs=-1
    )
    rf_season.fit(season_train_df, season_train_df[TARGET_COLUMN])
    season_test_df["pred_baseline"] = baseline_simple.predict(season_test_df)
    season_test_df["pred_rf"] = rf_season.predict(season_test_df)

    season_metrics_base = calculate_metrics(season_test_df[TARGET_COLUMN], season_test_df["pred_baseline"])
    season_metrics_rf = calculate_metrics(season_test_df[TARGET_COLUMN], season_test_df["pred_rf"])
    print(f"  Season Holdout Baseline MAE: {season_metrics_base['MAE']:.2f}, RMSE: {season_metrics_base['RMSE']:.2f}, R2={season_metrics_base['R2']:.4f}")
    print(f"  Season Holdout RF MAE:       {season_metrics_rf['MAE']:.2f}, RMSE: {season_metrics_rf['RMSE']:.2f}, R2={season_metrics_rf['R2']:.4f}")

    # 7. Select real unseen prediction examples
    print("\n[7/7] Selecting real test prediction examples and generating plots...")
    prediction_examples = select_prediction_examples(
        test_df, pred_baseline_col="pred_baseline", pred_rf_col="pred_rf", n=12, random_state=random_state
    )

    # Generate plots
    plot_files = generate_evaluation_plots(
        test_df=test_df,
        feature_importances=feat_importances,
        phase_metrics_baseline=phase_base_simple,
        phase_metrics_rf=phase_rf,
        output_dir=plots_dir,
    )
    print(f"  Saved {len(plot_files)} plots to {plots_dir}")

    # Save artifacts
    rf_model.save(
        out_dir,
        metadata={
            "metrics": {
                "baseline_simple": metrics_base_simple,
                "baseline_historical_conditional": metrics_hist_cond,
                "baseline_historical_global": metrics_hist_global,
                "random_forest": metrics_rf,
                "phase_metrics_baseline": phase_base_simple,
                "phase_metrics_rf": phase_rf,
                "season_validation": {
                    "train_matches": len(s_train_m),
                    "test_matches": len(s_test_m),
                    "baseline": season_metrics_base,
                    "random_forest": season_metrics_rf,
                },
            },
            "train_samples": len(train_df),
            "test_samples": len(test_df),
            "train_matches_count": len(train_matches),
            "test_matches_count": len(test_matches),
        },
    )

    # Save metrics json separately for clean access
    with open(out_dir / "metrics.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "baseline_simple": metrics_base_simple,
                "baseline_historical_conditional": metrics_hist_cond,
                "baseline_historical_global": metrics_hist_global,
                "random_forest": metrics_rf,
                "phase_metrics_baseline": phase_base_simple,
                "phase_metrics_rf": phase_rf,
                "season_validation": {
                    "train_matches": len(s_train_m),
                    "test_matches": len(s_test_m),
                    "baseline": season_metrics_base,
                    "random_forest": season_metrics_rf,
                },
            },
            f,
            indent=2,
        )

    # Save train/test match IDs
    with open(out_dir / "train_test_split.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "match_split": {
                    "train_match_ids": [str(m) for m in train_matches],
                    "test_match_ids": [str(m) for m in test_matches],
                    "random_state": random_state,
                    "test_size": test_size,
                },
                "season_split": {
                    "train_match_ids": [str(m) for m in s_train_m],
                    "test_match_ids": [str(m) for m in s_test_m],
                    "cutoff_season": "2025",
                },
            },
            f,
            indent=2,
        )

    # Save prediction examples
    with open(out_dir / "test_prediction_examples.json", "w", encoding="utf-8") as f:
        json.dump(prediction_examples, f, indent=2)

    report = {
        "usable_innings": meta["usable_first_innings"],
        "total_sampled_states": meta["total_sampled_states"],
        "train_matches_count": len(train_matches),
        "test_matches_count": len(test_matches),
        "train_states_count": len(train_df),
        "test_states_count": len(test_df),
        "baseline_metrics": metrics_base_simple,
        "rf_metrics": metrics_rf,
        "phase_metrics_baseline": phase_base_simple,
        "phase_metrics_rf": phase_rf,
        "feature_importances": feat_importances,
        "prediction_examples": prediction_examples,
        "excluded_matches": meta["excluded_matches_summary"],
        "rf_outperformed_baseline": rf_outperformed_baseline,
        "plot_files": plot_files,
    }

    print("\nPipeline completed successfully!")
    print("=" * 60)
    return report


if __name__ == "__main__":
    run_pipeline()
