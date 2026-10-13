"""
Evaluation & Artifact Generation Pipeline for Phase 4A (Chase Corrected).

Key Capabilities:
1. Strict separation between First Innings (Expected Final Score & Trajectory Deviation)
   and Second Innings / Chase (Target, Required RR, RR Gap, Runs Required Reduction, Target Progress).
2. Evaluates Expected Runs and Expected Strike Rate models against baselines.
3. Generates enriched batter performance dataset (data/processed/batter_performance_dataset.csv)
   with standardized columns as specified in Phase 4A audit requirements.
4. Generates 8 evaluation plots under models/expected_batter/plots/.
5. Selects 12 diverse unseen validation examples across all 4 performance quadrants.
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error

# Ensure repository root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.batter_trajectory import extract_batter_trajectories
from src.expected_batter_model import (
    BATTER_FEATURE_COLUMNS,
    ExpectedRunsBaselines,
    ExpectedRunsRFModel,
    ExpectedSRBaselines,
    ExpectedSRRFModel,
    compute_deviations_and_ratios,
)


def calculate_regression_metrics(y_true: Union[pd.Series, np.ndarray], y_pred: Union[pd.Series, np.ndarray]) -> Dict[str, float]:
    """Calculate MAE, RMSE, and R2 regression metrics."""
    yt = np.asarray(y_true, dtype=float)
    yp = np.asarray(y_pred, dtype=float)
    mask = ~np.isnan(yt) & ~np.isnan(yp)
    yt = yt[mask]
    yp = yp[mask]

    if len(yt) == 0:
        return {"MAE": np.nan, "RMSE": np.nan, "R2": np.nan}

    mae = float(mean_absolute_error(yt, yp))
    rmse = float(root_mean_squared_error(yt, yp))
    r2 = float(r2_score(yt, yp))

    return {
        "MAE": round(mae, 2),
        "RMSE": round(rmse, 2),
        "R2": round(r2, 4),
    }


def split_batter_dataset_by_match(
    df: pd.DataFrame,
    test_size: float = 0.2,
    random_state: int = 42
) -> Tuple[pd.DataFrame, pd.DataFrame, List[Any], List[Any]]:
    """Split batter dataset strictly by MATCH ID to prevent leakage."""
    unique_matches = np.array(sorted(df["match_id"].unique()))
    rng = np.random.default_rng(random_state)
    n_test = int(np.round(test_size * len(unique_matches)))
    test_indices = rng.choice(len(unique_matches), size=n_test, replace=False)
    test_matches_set = set(unique_matches[test_indices])
    train_matches_set = set(unique_matches) - test_matches_set

    train_df = df[df["match_id"].isin(train_matches_set)].copy().reset_index(drop=True)
    test_df = df[df["match_id"].isin(test_matches_set)].copy().reset_index(drop=True)

    return train_df, test_df, sorted(list(train_matches_set)), sorted(list(test_matches_set))


def select_diverse_unseen_examples(
    test_df: pd.DataFrame,
    n: int = 12,
    random_state: int = 42
) -> List[Dict[str, Any]]:
    """
    Select diverse real test examples spanning:
    - Quadrant 1: runs > exp, SR < exp (Anchor / Accumulator)
    - Quadrant 2: runs < exp, SR > exp (Blaster / Quick cameo)
    - Quadrant 3: both > exp (Outstanding dominant innings)
    - Quadrant 4: both < exp (Underperformance)
    - Chases, First innings, and Not-out innings.
    """
    valid = test_df[test_df["balls_faced"] >= 5].copy()

    # Define quadrants
    q1 = valid[(valid["run_deviation"] > 4) & (valid["sr_deviation"] < -8)]   # Runs up, SR down
    q2 = valid[(valid["run_deviation"] < -4) & (valid["sr_deviation"] > 15)]  # Runs down, SR up
    q3 = valid[(valid["run_deviation"] > 8) & (valid["sr_deviation"] > 10)]   # Both up
    q4 = valid[(valid["run_deviation"] < -6) & (valid["sr_deviation"] < -15)]  # Both down

    rng = np.random.default_rng(random_state)
    sel_indices = []
    for q_df in [q1, q2, q3, q4]:
        if len(q_df) > 0:
            k = min(3, len(q_df))
            sel_indices.extend(rng.choice(q_df.index, size=k, replace=False))

    if len(sel_indices) < n:
        rem = set(valid.index) - set(sel_indices)
        sel_indices.extend(rng.choice(list(rem), size=n - len(sel_indices), replace=False))

    examples_df = test_df.loc[sel_indices[:n]].copy()
    examples: List[Dict[str, Any]] = []

    for _, row in examples_df.iterrows():
        is_ch = bool(row["innings"] == 2)
        ex_dict: Dict[str, Any] = {
            "player": str(row["player"]),
            "match_id": str(row["match_id"]),
            "season": str(row["season"]),
            "innings_type": "Chase (2nd Innings)" if is_ch else "First Innings",
            "batting_position": int(row["batting_position"]),
            "dismissal_status": str(row["dismissal_status"]),
            "entry_state": f"{int(row['entry_score'])}/{int(row['entry_wickets_lost'])} at over {row['entry_over']} (RR: {row['entry_team_rr']:.2f})",
            "exit_state": f"{int(row['exit_score'])}/{int(row['exit_wickets_lost'])} at over {row['exit_over']} (RR: {row['exit_team_rr']:.2f})",
            "actual_team_runs_change": int(row["actual_team_runs_change"]),
            "batter_actual_runs": int(row["actual_runs"]),
            "batter_balls_faced": int(row["balls_faced"]),
            "batter_actual_sr": float(row["actual_sr"]),
            "batter_fours": int(row["fours"]),
            "batter_sixes": int(row["sixes"]),
            "expected_runs": float(row["expected_runs"]),
            "run_deviation": float(row["run_deviation"]),
            "expected_sr": float(row["expected_sr"]),
            "sr_deviation": float(row["sr_deviation"]),
            "run_performance_ratio": None if pd.isna(row["run_performance_ratio"]) else float(row["run_performance_ratio"]),
            "sr_performance_ratio": None if pd.isna(row["sr_performance_ratio"]) else float(row["sr_performance_ratio"]),
            "partnership_runs": int(row["partnership_runs"]),
            "batter_partnership_runs": int(row["batter_partnership_runs"]),
            "partner_runs": int(row["partner_runs"]),
            "batter_partnership_share": float(row["batter_partnership_share"]),
        }

        if is_ch:
            # Strictly Chase metrics
            ex_dict["expected_final_entry"] = None
            ex_dict["expected_final_exit"] = None
            ex_dict["expected_final_change"] = None
            ex_dict["entry_score_deviation"] = None
            ex_dict["exit_score_deviation"] = None
            ex_dict["trajectory_deviation_change"] = None
            ex_dict["target"] = float(row["target"])
            ex_dict["runs_required_entry"] = float(row["runs_required_entry"])
            ex_dict["runs_required_exit"] = float(row["runs_required_exit"])
            ex_dict["required_rr_entry"] = float(row["required_rr_entry"])
            ex_dict["required_rr_exit"] = float(row["required_rr_exit"])
            ex_dict["required_rr_change"] = float(row["required_rr_change"])
            ex_dict["rr_gap_entry"] = float(row["rr_gap_entry"])
            ex_dict["rr_gap_exit"] = float(row["rr_gap_exit"])
            ex_dict["rr_gap_change"] = float(row["rr_gap_change"])
            ex_dict["runs_required_reduction"] = float(row["runs_required_reduction"])
            ex_dict["target_progress_change"] = float(row["target_progress_change"])
        else:
            # Strictly First-Innings trajectory metrics
            ex_dict["expected_final_entry"] = None if pd.isna(row["expected_final_entry"]) else float(row["expected_final_entry"])
            ex_dict["expected_final_exit"] = None if pd.isna(row["expected_final_exit"]) else float(row["expected_final_exit"])
            ex_dict["expected_final_change"] = None if pd.isna(row["expected_final_change"]) else float(row["expected_final_change"])
            ex_dict["entry_score_deviation"] = None if pd.isna(row["entry_score_deviation"]) else float(row["entry_score_deviation"])
            ex_dict["exit_score_deviation"] = None if pd.isna(row["exit_score_deviation"]) else float(row["exit_score_deviation"])
            ex_dict["trajectory_deviation_change"] = None if pd.isna(row["trajectory_deviation_change"]) else float(row["trajectory_deviation_change"])
            ex_dict["target"] = None
            ex_dict["runs_required_entry"] = None
            ex_dict["runs_required_exit"] = None
            ex_dict["required_rr_entry"] = None
            ex_dict["required_rr_exit"] = None
            ex_dict["required_rr_change"] = None
            ex_dict["rr_gap_entry"] = None
            ex_dict["rr_gap_exit"] = None
            ex_dict["rr_gap_change"] = None
            ex_dict["runs_required_reduction"] = None
            ex_dict["target_progress_change"] = None

        examples.append(ex_dict)

    return examples


def generate_evaluation_visualizations(
    test_df: pd.DataFrame,
    phase_metrics: Dict[str, Dict[str, Any]],
    position_metrics: Dict[str, Dict[str, Any]],
    output_dir: Union[str, Path]
) -> List[str]:
    """Generate all 8 requested figures under models/expected_batter/plots/."""
    plot_dir = Path(output_dir)
    plot_dir.mkdir(parents=True, exist_ok=True)
    generated_plots = []

    plt.style.use("tableau-colorblind10" if "tableau-colorblind10" in plt.style.available else "default")
    plt.rcParams["font.sans-serif"] = "DejaVu Sans"
    plt.rcParams["font.size"] = 10

    # 1. Actual vs Predicted Runs
    fig, ax = plt.subplots(figsize=(7, 6), dpi=150)
    y_true_r = test_df["actual_runs"].to_numpy()
    y_pred_r = test_df["expected_runs"].to_numpy()
    ax.scatter(y_true_r, y_pred_r, alpha=0.25, color="#1f77b4", s=15, edgecolors="none")
    max_r = max(y_true_r.max(), y_pred_r.max()) + 5
    ax.plot([0, max_r], [0, max_r], "r--", linewidth=1.5, label="Perfect Prediction (y=x)")
    ax.set_xlabel("Actual Batter Runs", fontweight="bold")
    ax.set_ylabel("Expected Batter Runs", fontweight="bold")
    ax.set_title("Actual vs Expected Batter Runs (Test Set)", fontweight="bold", pad=12)
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(frameon=True)
    p1 = plot_dir / "actual_vs_predicted_runs.png"
    plt.tight_layout()
    plt.savefig(p1)
    plt.close(fig)
    generated_plots.append(str(p1))

    # 2. Actual vs Predicted Strike Rate (for batters facing > 0 balls)
    fig, ax = plt.subplots(figsize=(7, 6), dpi=150)
    valid_sr_test = test_df[test_df["balls_faced"] > 0]
    y_true_s = valid_sr_test["actual_sr"].to_numpy()
    y_pred_s = valid_sr_test["expected_sr"].to_numpy()
    ax.scatter(y_true_s, y_pred_s, alpha=0.25, color="#2ca02c", s=15, edgecolors="none")
    max_s = min(300, max(y_true_s.max(), y_pred_s.max()))
    ax.plot([0, max_s], [0, max_s], "r--", linewidth=1.5, label="Perfect Prediction (y=x)")
    ax.set_xlim(0, 320)
    ax.set_ylim(0, 220)
    ax.set_xlabel("Actual Strike Rate", fontweight="bold")
    ax.set_ylabel("Expected Strike Rate", fontweight="bold")
    ax.set_title("Actual vs Expected Batter Strike Rate", fontweight="bold", pad=12)
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(frameon=True)
    p2 = plot_dir / "actual_vs_predicted_sr.png"
    plt.tight_layout()
    plt.savefig(p2)
    plt.close(fig)
    generated_plots.append(str(p2))

    # 3. Run Prediction Error Distribution (Run Deviation)
    fig, ax = plt.subplots(figsize=(7, 5), dpi=150)
    run_err = test_df["run_deviation"].to_numpy()
    bins_r = np.linspace(-40, 80, 50)
    ax.hist(run_err, bins=bins_r, color="#3498db", alpha=0.75, edgecolor="#2980b9", density=True)
    ax.axvline(0, color="black", linestyle="--", linewidth=1.2)
    ax.set_xlabel("Run Deviation (Actual Runs - Expected Runs)", fontweight="bold")
    ax.set_ylabel("Density", fontweight="bold")
    ax.set_title("Run Deviation Distribution", fontweight="bold", pad=12)
    ax.grid(True, linestyle=":", alpha=0.6)
    p3 = plot_dir / "run_prediction_error_distribution.png"
    plt.tight_layout()
    plt.savefig(p3)
    plt.close(fig)
    generated_plots.append(str(p3))

    # 4. SR Prediction Error Distribution (SR Deviation)
    fig, ax = plt.subplots(figsize=(7, 5), dpi=150)
    sr_err = valid_sr_test["sr_deviation"].to_numpy()
    bins_s = np.linspace(-150, 200, 50)
    ax.hist(sr_err, bins=bins_s, color="#e67e22", alpha=0.75, edgecolor="#d35400", density=True)
    ax.axvline(0, color="black", linestyle="--", linewidth=1.2)
    ax.set_xlabel("Strike Rate Deviation (Actual SR - Expected SR)", fontweight="bold")
    ax.set_ylabel("Density", fontweight="bold")
    ax.set_title("Strike Rate Deviation Distribution", fontweight="bold", pad=12)
    ax.grid(True, linestyle=":", alpha=0.6)
    p4 = plot_dir / "sr_prediction_error_distribution.png"
    plt.tight_layout()
    plt.savefig(p4)
    plt.close(fig)
    generated_plots.append(str(p4))

    # 5. MAE by Innings Phase
    fig, ax = plt.subplots(figsize=(8, 5), dpi=150)
    phases = ["POWERPLAY", "MIDDLE", "DEATH"]
    run_maes_p = [phase_metrics[ph]["runs_mae"] for ph in phases]
    sr_maes_p = [phase_metrics[ph]["sr_mae"] for ph in phases]

    x_p = np.arange(len(phases))
    w = 0.35
    ax.bar(x_p - w/2, run_maes_p, w, label="Expected Runs MAE", color="#1f77b4", alpha=0.85)
    ax.set_ylabel("Runs MAE", fontweight="bold", color="#1f77b4")
    ax.set_xticks(x_p)
    ax.set_xticklabels(phases, fontweight="bold")
    ax.grid(True, axis="y", linestyle=":", alpha=0.6)

    ax2 = ax.twinx()
    ax2.bar(x_p + w/2, sr_maes_p, w, label="Expected SR MAE", color="#e67e22", alpha=0.85)
    ax2.set_ylabel("Strike Rate MAE", fontweight="bold", color="#e67e22")

    ax.set_title("Prediction Error (MAE) by Innings Phase", fontweight="bold", pad=12)
    p5 = plot_dir / "mae_by_innings_phase.png"
    plt.tight_layout()
    plt.savefig(p5)
    plt.close(fig)
    generated_plots.append(str(p5))

    # 6. MAE by Batting Position Group
    fig, ax = plt.subplots(figsize=(8, 5), dpi=150)
    pos_groups = ["Top Order (1-3)", "Middle Order (4-6)", "Lower Order (7+)"]
    run_maes_pos = [position_metrics[pg]["runs_mae"] for pg in pos_groups]
    sr_maes_pos = [position_metrics[pg]["sr_mae"] for pg in pos_groups]

    x_pos = np.arange(len(pos_groups))
    ax.bar(x_pos - w/2, run_maes_pos, w, label="Expected Runs MAE", color="#27ae60", alpha=0.85)
    ax.set_ylabel("Runs MAE", fontweight="bold", color="#27ae60")
    ax.set_xticks(x_pos)
    ax.set_xticklabels(pos_groups, fontweight="bold")
    ax.grid(True, axis="y", linestyle=":", alpha=0.6)

    ax2 = ax.twinx()
    ax2.bar(x_pos + w/2, sr_maes_pos, w, label="Expected SR MAE", color="#8e44ad", alpha=0.85)
    ax2.set_ylabel("Strike Rate MAE", fontweight="bold", color="#8e44ad")

    ax.set_title("Prediction Error (MAE) by Batting Order Position", fontweight="bold", pad=12)
    p6 = plot_dir / "mae_by_batting_position.png"
    plt.tight_layout()
    plt.savefig(p6)
    plt.close(fig)
    generated_plots.append(str(p6))

    # 7. Exact Entry-to-Exit Expected Final Score Change Distribution (First Innings ONLY)
    fig, ax = plt.subplots(figsize=(7, 5), dpi=150)
    inn1_test = test_df[(test_df["innings"] == 1) & test_df["expected_final_change"].notnull()]
    final_changes = inn1_test["expected_final_change"].to_numpy()
    bins_c = np.linspace(-35, 45, 45)
    ax.hist(final_changes, bins=bins_c, color="#16a085", alpha=0.8, edgecolor="#0e6655")
    ax.axvline(0, color="black", linestyle="--", linewidth=1.2)
    ax.set_xlabel("Expected Final Score Change (Exit - Entry)", fontweight="bold")
    ax.set_ylabel("Count of Batter Innings", fontweight="bold")
    ax.set_title("First-Innings Expected Final Score Trajectory Change (1st Innings Only)", fontweight="bold", pad=12)
    ax.grid(True, linestyle=":", alpha=0.6)
    p7 = plot_dir / "entry_exit_expected_final_change.png"
    plt.tight_layout()
    plt.savefig(p7)
    plt.close(fig)
    generated_plots.append(str(p7))

    # 8. Trajectory Deviation Change Distribution (First Innings ONLY)
    fig, ax = plt.subplots(figsize=(7, 5), dpi=150)
    traj_dev_changes = test_df.loc[test_df["innings"] == 1, "trajectory_deviation_change"].dropna().to_numpy()
    bins_td = np.linspace(-40, 50, 45)
    ax.hist(traj_dev_changes, bins=bins_td, color="#9b59b6", alpha=0.8, edgecolor="#8e44ad")
    ax.axvline(0, color="black", linestyle="--", linewidth=1.2)
    ax.set_xlabel("Trajectory Deviation Change (Exit Dev - Entry Dev)", fontweight="bold")
    ax.set_ylabel("Count of Batter Innings", fontweight="bold")
    ax.set_title("Trajectory Deviation Shift (1st Innings Only)", fontweight="bold", pad=12)
    ax.grid(True, linestyle=":", alpha=0.6)
    p8 = plot_dir / "trajectory_deviation_change.png"
    plt.tight_layout()
    plt.savefig(p8)
    plt.close(fig)
    generated_plots.append(str(p8))

    return generated_plots


def run_phase4a_pipeline(
    output_dir: str = "models/expected_batter",
    dataset_output_path: str = "data/processed/batter_performance_dataset.csv",
    test_size: float = 0.2,
    random_state: int = 42
) -> Dict[str, Any]:
    """
    Execute full Phase 4A pipeline with chase correction and enriched dataset.
    """
    out_dir = Path(output_dir)
    plots_dir = out_dir / "plots"
    out_dir.mkdir(parents=True, exist_ok=True)
    plots_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 65)
    print("PHASE 4A: BATTER SITUATIONAL TRAJECTORY & EXPECTATION ENGINE (AUDITED)")
    print("=" * 65)

    # 1. Trajectory Extraction (with strict 1st innings vs chase separation)
    print("\n[1/7] Extracting exact entry/exit trajectories and match situations...")
    df = extract_batter_trajectories()
    print(f"  Total Batter Innings: {len(df)}")
    print(f"  Total Matches:        {df['match_id'].nunique()}")
    print(f"  Total Seasons:        {df['season'].nunique()}")
    print(f"  1st Innings (non-null expected_final_entry): {df['expected_final_entry'].notnull().sum()}")
    print(f"  Chase Innings (non-null required_rr_entry):  {df['required_rr_entry'].notnull().sum()}")

    # 2. Match-Level Split
    print(f"\n[2/7] Splitting by Match ID (80% train / 20% test, seed={random_state})...")
    train_df, test_df, train_matches, test_matches = split_batter_dataset_by_match(
        df, test_size=test_size, random_state=random_state
    )
    print(f"  Train Matches: {len(train_matches)} | Train Batter Innings: {len(train_df)}")
    print(f"  Test Matches:  {len(test_matches)} | Test Batter Innings:  {len(test_df)}")

    # 3. Expected Runs Model & Baselines
    print("\n[3/7] Training Expected Runs Model and Baselines...")
    runs_baselines = ExpectedRunsBaselines().fit(train_df)
    rf_runs = ExpectedRunsRFModel(random_state=random_state)
    rf_runs.fit(train_df)

    test_runs_true = test_df["actual_runs"]
    test_runs_base_global = runs_baselines.predict_global(test_df)
    test_runs_base_pos = runs_baselines.predict_position(test_df)
    test_runs_base_phase = runs_baselines.predict_phase(test_df)
    test_runs_base_over = runs_baselines.predict_over(test_df)
    test_runs_rf = rf_runs.predict(test_df)

    m_runs_global = calculate_regression_metrics(test_runs_true, test_runs_base_global)
    m_runs_pos = calculate_regression_metrics(test_runs_true, test_runs_base_pos)
    m_runs_phase = calculate_regression_metrics(test_runs_true, test_runs_base_phase)
    m_runs_over = calculate_regression_metrics(test_runs_true, test_runs_base_over)
    m_runs_rf = calculate_regression_metrics(test_runs_true, test_runs_rf)

    print(f"  Global Mean Baseline:       MAE={m_runs_global['MAE']}, RMSE={m_runs_global['RMSE']}, R2={m_runs_global['R2']}")
    print(f"  Batting Position Baseline:  MAE={m_runs_pos['MAE']}, RMSE={m_runs_pos['RMSE']}, R2={m_runs_pos['R2']}")
    print(f"  Innings Phase Baseline:     MAE={m_runs_phase['MAE']}, RMSE={m_runs_phase['RMSE']}, R2={m_runs_phase['R2']}")
    print(f"  Entry Over Baseline:        MAE={m_runs_over['MAE']}, RMSE={m_runs_over['RMSE']}, R2={m_runs_over['R2']}")
    print(f"  Random Forest Expected Runs: MAE={m_runs_rf['MAE']}, RMSE={m_runs_rf['RMSE']}, R2={m_runs_rf['R2']}")

    # 4. Expected Strike Rate Model & Baselines (balls faced > 0)
    print("\n[4/7] Training Expected Strike Rate Model and Baselines...")
    train_sr_sub = train_df[train_df["balls_faced"] > 0]
    test_sr_sub = test_df[test_df["balls_faced"] > 0]

    sr_baselines = ExpectedSRBaselines().fit(train_sr_sub)
    rf_sr = ExpectedSRRFModel(random_state=random_state)
    rf_sr.fit(train_sr_sub)

    test_sr_true = test_sr_sub["actual_sr"]
    test_sr_base_global = sr_baselines.predict_global(test_sr_sub)
    test_sr_base_pos = sr_baselines.predict_position(test_sr_sub)
    test_sr_base_phase = sr_baselines.predict_phase(test_sr_sub)
    test_sr_base_over = sr_baselines.predict_over(test_sr_sub)
    test_sr_rf = rf_sr.predict(test_sr_sub)

    m_sr_global = calculate_regression_metrics(test_sr_true, test_sr_base_global)
    m_sr_pos = calculate_regression_metrics(test_sr_true, test_sr_base_pos)
    m_sr_phase = calculate_regression_metrics(test_sr_true, test_sr_base_phase)
    m_sr_over = calculate_regression_metrics(test_sr_true, test_sr_base_over)
    m_sr_rf = calculate_regression_metrics(test_sr_true, test_sr_rf)

    print(f"  Global Mean SR Baseline:       MAE={m_sr_global['MAE']}, RMSE={m_sr_global['RMSE']}, R2={m_sr_global['R2']}")
    print(f"  Batting Position SR Baseline:  MAE={m_sr_pos['MAE']}, RMSE={m_sr_pos['RMSE']}, R2={m_sr_pos['R2']}")
    print(f"  Innings Phase SR Baseline:     MAE={m_sr_phase['MAE']}, RMSE={m_sr_phase['RMSE']}, R2={m_sr_phase['R2']}")
    print(f"  Entry Over SR Baseline:        MAE={m_sr_over['MAE']}, RMSE={m_sr_over['RMSE']}, R2={m_sr_over['R2']}")
    print(f"  Random Forest Expected SR:     MAE={m_sr_rf['MAE']}, RMSE={m_sr_rf['RMSE']}, R2={m_sr_rf['R2']}")

    # 5. Attach Predictions, Deviations, and Performance Ratios to Entire Dataset
    print("\n[5/7] Computing deviations, ratios, and building enriched performance dataset...")
    df["expected_runs"] = np.round(rf_runs.predict(df), 1)
    df["expected_sr"] = np.round(rf_sr.predict(df), 1)

    dev_results = compute_deviations_and_ratios(
        actual_runs=df["actual_runs"],
        expected_runs=df["expected_runs"],
        actual_sr=df["actual_sr"],
        expected_sr=df["expected_sr"],
    )
    for k, v in dev_results.items():
        df[k] = v

    # Re-slice test_df from df with all computed columns synchronized
    test_df = df[df["match_id"].isin(test_matches)].copy().reset_index(drop=True)

    # Standardized output dataset schema as specified in Section 9
    dataset_cols = [
        # Match Context
        "match_id", "season", "innings", "team", "opponent", "target",
        # Batter Context
        "player", "batting_position", "entry_ball", "exit_ball", "entry_over", "exit_over",
        # Entry State
        "entry_score", "entry_wickets_lost", "entry_wickets_remaining", "entry_balls_remaining", "entry_team_rr",
        # Exit State
        "exit_score", "exit_wickets_lost", "exit_wickets_remaining", "exit_balls_remaining", "exit_team_rr",
        # Dismissal info
        "dismissal_status", "dismissal_kind",
        # Batter Performance
        "actual_runs", "expected_runs", "run_deviation", "run_performance_ratio",
        "actual_sr", "expected_sr", "sr_deviation", "sr_performance_ratio",
        "balls_faced", "dot_balls", "dot_ball_percentage", "fours", "sixes", "boundary_runs",
        # Partnership Context
        "partnership_runs", "batter_partnership_runs", "partner_runs", "batter_partnership_share", "partnership_duration",
        # First-Innings Trajectory (NULL for 2nd innings / super overs)
        "expected_final_entry", "expected_final_exit", "expected_final_change",
        "entry_score_deviation", "exit_score_deviation", "trajectory_deviation_change",
        # Chase Context (NULL for 1st innings / super overs)
        "runs_required_entry", "runs_required_exit", "required_rr_entry", "required_rr_exit", "required_rr_change",
        "rr_gap_entry", "rr_gap_exit", "rr_gap_change", "runs_required_reduction",
        "target_progress_entry", "target_progress_exit", "target_progress_change"
    ]

    # Also keep backward-compatible aliases in CSV for previous phase script compatibility
    aliases = {
        "batter": df["player"],
        "runs": df["actual_runs"],
        "strike_rate": df["actual_sr"],
        "innings_number": df["innings"],
        "batting_team": df["team"],
        "bowling_team": df["opponent"],
        "opposition_team": df["opponent"],
        "entry_team_runs": df["entry_score"],
        "exit_team_runs": df["exit_score"],
        "entry_rr": df["entry_team_rr"],
        "exit_rr": df["exit_team_rr"],
        "expected_final_score_at_entry": df["expected_final_entry"],
        "expected_final_score_at_exit": df["expected_final_exit"],
        "required_rr_at_entry": df["required_rr_entry"],
        "required_rr_at_exit": df["required_rr_exit"],
        "runs_required_at_entry": df["runs_required_entry"],
        "runs_required_at_exit": df["runs_required_exit"],
        "is_chase": (df["innings"] == 2),
        "actual_team_runs_change": df["actual_team_runs_change"],
    }
    for alias_name, series_val in aliases.items():
        if alias_name not in df.columns:
            df[alias_name] = series_val

    all_output_cols = dataset_cols + [col for col in aliases.keys() if col not in dataset_cols]

    ds_file = Path(dataset_output_path)
    ds_file.parent.mkdir(parents=True, exist_ok=True)
    df[all_output_cols].to_csv(ds_file, index=False)
    print(f"  Saved {len(df)} batter innings to {dataset_output_path}")

    # 6. Contextual Evaluations
    print("\n[6/7] Computing contextual evaluations (Phase, Position, Chase)...")

    # A. By Phase
    phase_metrics: Dict[str, Dict[str, Any]] = {}
    for ph in ["POWERPLAY", "MIDDLE", "DEATH"]:
        sub = test_df[test_df["entry_phase"] == ph]
        sub_sr = sub[sub["balls_faced"] > 0]
        phase_metrics[ph] = {
            "count": len(sub),
            "runs_mae": round(float(mean_absolute_error(sub["actual_runs"], sub["expected_runs"])), 2),
            "runs_rmse": round(float(root_mean_squared_error(sub["actual_runs"], sub["expected_runs"])), 2),
            "runs_r2": round(float(r2_score(sub["actual_runs"], sub["expected_runs"])), 4),
            "sr_mae": round(float(mean_absolute_error(sub_sr["actual_sr"], sub_sr["expected_sr"])), 2),
            "sr_rmse": round(float(root_mean_squared_error(sub_sr["actual_sr"], sub_sr["expected_sr"])), 2),
            "sr_r2": round(float(r2_score(sub_sr["actual_sr"], sub_sr["expected_sr"])), 4),
        }
        print(f"    Phase {ph:10s} (n={len(sub)}): Runs MAE={phase_metrics[ph]['runs_mae']}, SR MAE={phase_metrics[ph]['sr_mae']}")

    # B. By Batting Position
    pos_groups = {
        "Top Order (1-3)": [1, 2, 3],
        "Middle Order (4-6)": [4, 5, 6],
        "Lower Order (7+)": list(range(7, 12)),
    }
    position_metrics: Dict[str, Dict[str, Any]] = {}
    for pg_name, positions in pos_groups.items():
        sub = test_df[test_df["batting_position"].isin(positions)]
        sub_sr = sub[sub["balls_faced"] > 0]
        position_metrics[pg_name] = {
            "count": len(sub),
            "runs_mae": round(float(mean_absolute_error(sub["actual_runs"], sub["expected_runs"])), 2),
            "runs_rmse": round(float(root_mean_squared_error(sub["actual_runs"], sub["expected_runs"])), 2),
            "runs_r2": round(float(r2_score(sub["actual_runs"], sub["expected_runs"])), 4),
            "sr_mae": round(float(mean_absolute_error(sub_sr["actual_sr"], sub_sr["expected_sr"])), 2),
            "sr_rmse": round(float(root_mean_squared_error(sub_sr["actual_sr"], sub_sr["expected_sr"])), 2),
            "sr_r2": round(float(r2_score(sub_sr["actual_sr"], sub_sr["expected_sr"])), 4),
        }
        print(f"    Position {pg_name:18s} (n={len(sub)}): Runs MAE={position_metrics[pg_name]['runs_mae']}, SR MAE={position_metrics[pg_name]['sr_mae']}")

    # C. By Chase Required Run Rate
    chase_sub = test_df[test_df["innings"] == 2].copy()
    chase_rrr_bins = {
        "Low RRR (<7)": chase_sub[chase_sub["required_rr_entry"] < 7.0],
        "Moderate RRR (7-10)": chase_sub[(chase_sub["required_rr_entry"] >= 7.0) & (chase_sub["required_rr_entry"] <= 10.0)],
        "High RRR (>10)": chase_sub[chase_sub["required_rr_entry"] > 10.0],
    }
    chase_metrics: Dict[str, Dict[str, Any]] = {}
    for rrr_name, sub in chase_rrr_bins.items():
        sub_sr = sub[sub["balls_faced"] > 0]
        if len(sub) > 0:
            chase_metrics[rrr_name] = {
                "count": len(sub),
                "runs_mae": round(float(mean_absolute_error(sub["actual_runs"], sub["expected_runs"])), 2),
                "runs_rmse": round(float(root_mean_squared_error(sub["actual_runs"], sub["expected_runs"])), 2),
                "sr_mae": round(float(mean_absolute_error(sub_sr["actual_sr"], sub_sr["expected_sr"])), 2) if len(sub_sr) > 0 else 0.0,
            }
            print(f"    Chase {rrr_name:20s} (n={len(sub)}): Runs MAE={chase_metrics[rrr_name]['runs_mae']}, SR MAE={chase_metrics[rrr_name]['sr_mae']}")

    # 7. Diverse Unseen Examples & Visualizations
    print("\n[7/7] Selecting diverse unseen examples and generating plots...")
    unseen_examples = select_diverse_unseen_examples(test_df, n=12, random_state=random_state)
    plot_files = generate_evaluation_visualizations(
        test_df=test_df,
        phase_metrics=phase_metrics,
        position_metrics=position_metrics,
        output_dir=plots_dir
    )
    print(f"  Generated {len(plot_files)} plots in {plots_dir}")

    # Feature importances
    feat_imp_runs = rf_runs.get_feature_importances()
    feat_imp_sr = rf_sr.get_feature_importances()

    # Save models
    rf_runs.save(out_dir / "expected_runs_model.joblib")
    rf_sr.save(out_dir / "expected_sr_model.joblib")

    # Save feature names
    with open(out_dir / "feature_names.json", "w", encoding="utf-8") as f:
        json.dump(BATTER_FEATURE_COLUMNS, f, indent=2)

    # Save configs and metrics
    metrics_all = {
        "dataset_summary": {
            "total_batter_innings": len(df),
            "train_batter_innings": len(train_df),
            "test_batter_innings": len(test_df),
            "total_matches": df["match_id"].nunique(),
            "train_matches": len(train_matches),
            "test_matches": len(test_matches),
            "total_seasons": df["season"].nunique(),
            "first_innings_with_trajectory": int(df["expected_final_entry"].notnull().sum()),
            "chase_innings_with_context": int(df["required_rr_entry"].notnull().sum()),
        },
        "expected_runs": {
            "random_forest": m_runs_rf,
            "baselines": {
                "global_mean": m_runs_global,
                "batting_position": m_runs_pos,
                "innings_phase": m_runs_phase,
                "entry_over": m_runs_over,
            },
            "feature_importances": feat_imp_runs,
        },
        "expected_strike_rate": {
            "random_forest": m_sr_rf,
            "baselines": {
                "global_mean": m_sr_global,
                "batting_position": m_sr_pos,
                "innings_phase": m_sr_phase,
                "entry_over": m_sr_over,
            },
            "feature_importances": feat_imp_sr,
        },
        "contextual_evaluations": {
            "by_phase": phase_metrics,
            "by_batting_position": position_metrics,
            "by_chase_rrr": chase_metrics,
        },
    }

    with open(out_dir / "metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics_all, f, indent=2)

    with open(out_dir / "unseen_examples.json", "w", encoding="utf-8") as f:
        json.dump(unseen_examples, f, indent=2)

    with open(out_dir / "train_test_split.json", "w", encoding="utf-8") as f:
        json.dump({
            "test_size": test_size,
            "random_state": random_state,
            "n_train_matches": len(train_matches),
            "n_test_matches": len(test_matches),
            "train_matches": [str(m) for m in train_matches],
            "test_matches": [str(m) for m in test_matches],
        }, f, indent=2)

    with open(out_dir / "config.json", "w", encoding="utf-8") as f:
        json.dump({
            "model_type": "RandomForestRegressor",
            "runs_model_config": rf_runs.config,
            "sr_model_config": rf_sr.config,
            "features": BATTER_FEATURE_COLUMNS,
            "dataset_output_path": dataset_output_path,
        }, f, indent=2)

    print("\nPhase 4A Pipeline Completed Successfully!")
    print("=" * 65)

    return metrics_all


if __name__ == "__main__":
    run_phase4a_pipeline()
