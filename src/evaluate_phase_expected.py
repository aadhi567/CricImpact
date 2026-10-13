"""
Phase-Based Expected Scoring Evaluation, Calibration & Trajectory Pipeline.

Evaluates:
1. Powerplay Model (Target: score_at_6) & Baseline
2. Middle-Over Model (Target: score_at_15) & Baseline
3. Death-Over Model (Target: final_team_score) & Baseline
4. Prediction error breakdown by sub-phase over windows.
5. Detailed comparison with Phase 3 Part 1 model on death overs.
6. Connected trajectory generation for data/processed/expected_scoring_trajectory.csv.
7. Visualizations:
   - Actual vs Predicted (Powerplay)
   - Actual vs Predicted (Middle)
   - Actual vs Predicted (Death)
   - MAE by Prediction Window
   - Feature Importance Comparison
   - Trajectory Progression for Unseen Test Matches
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import matplotlib
matplotlib.use("Agg")  # Non-interactive headless backend
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error

# Ensure repository root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.expected_score_model import ExpectedScoreRFModel
from src.phase_expected_dataset import (
    DEATH_FEATURE_COLUMNS,
    MID_FEATURE_COLUMNS,
    PP_FEATURE_COLUMNS,
    TARGET_FINAL,
    TARGET_MID,
    TARGET_PP,
    load_phase_expected_datasets,
    split_phase_datasets_by_match,
)
from src.phase_expected_model import (
    DeathBaseline,
    DeathRFModel,
    MiddleBaseline,
    MiddleRFModel,
    PhaseConditionalHistoricalBaseline,
    PowerplayBaseline,
    PowerplayRFModel,
)


def calculate_metrics(y_true: Union[pd.Series, np.ndarray], y_pred: Union[pd.Series, np.ndarray]) -> Dict[str, float]:
    """Calculate regression metrics: MAE, RMSE, and R²."""
    y_t = np.asarray(y_true, dtype=float)
    y_p = np.asarray(y_pred, dtype=float)
    return {
        "MAE": round(float(mean_absolute_error(y_t, y_p)), 4),
        "RMSE": round(float(root_mean_squared_error(y_t, y_p)), 4),
        "R2": round(float(r2_score(y_t, y_p)), 4),
    }


def evaluate_window_breakdowns(
    df: pd.DataFrame,
    target_col: str,
    pred_col: str,
    windows: Dict[str, List[float]]
) -> Dict[str, Dict[str, Any]]:
    """
    Calculate metrics across specified over intervals (e.g. overs 1-2, 3-4, 5).
    """
    results: Dict[str, Dict[str, Any]] = {}
    for window_name, overs in windows.items():
        sub = df[df["overs_completed"].isin(overs)]
        if len(sub) > 0:
            m = calculate_metrics(sub[target_col], sub[pred_col])
            m["sample_count"] = int(len(sub))
            results[window_name] = m
        else:
            results[window_name] = {"MAE": 0.0, "RMSE": 0.0, "R2": 0.0, "sample_count": 0}
    return results


def build_trajectory_dataset(
    all_sampled_df: pd.DataFrame,
    pp_model: PowerplayRFModel,
    mid_model: MiddleRFModel,
    death_model: DeathRFModel,
    part1_model: Optional[ExpectedScoreRFModel] = None,
    output_path: str = "data/processed/expected_scoring_trajectory.csv"
) -> pd.DataFrame:
    """
    Construct the full expected scoring trajectory dataset.

    For each suitable first-innings match state:
    - expected_score_at_6: populated when over < 6.0, else NaN/None
    - expected_score_at_15: populated when over < 15.0, else NaN/None
    - expected_final_score: populated for all intermediate overs < 20.0
    """
    base_cols = [
        "match_id",
        "season",
        "innings_number",
        "batting_team",
        "overs_completed",
        "current_team_runs",
        "wickets_lost_so_far",
        "current_team_rr",
    ]
    present_cols = [c for c in base_cols if c in all_sampled_df.columns]
    traj_df = all_sampled_df[present_cols].copy()
    if "batting_team" not in traj_df.columns:
        traj_df["batting_team"] = "Unknown"
    if "overs_completed" in traj_df.columns:
        traj_df = traj_df.rename(columns={"overs_completed": "over"})
    elif "over" not in traj_df.columns:
        traj_df["over"] = 0.0

    # Initialize columns as float (allowing NaN for NULL)
    traj_df["expected_score_at_6"] = np.nan
    traj_df["expected_score_at_15"] = np.nan
    traj_df["expected_final_score"] = np.nan

    # 1. Expected score at 6 (valid for overs < 6.0)
    mask_pp = all_sampled_df["overs_completed"] < 6.0
    if mask_pp.any():
        preds_6 = pp_model.predict(all_sampled_df[mask_pp])
        traj_df.loc[mask_pp, "expected_score_at_6"] = np.round(preds_6, 1)

    # 2. Expected score at 15 (valid for overs < 15.0)
    mask_mid = all_sampled_df["overs_completed"] < 15.0
    if mask_mid.any():
        preds_15 = mid_model.predict(all_sampled_df[mask_mid])
        traj_df.loc[mask_mid, "expected_score_at_15"] = np.round(preds_15, 1)

    # 3. Expected final score (valid for all intermediate overs < 20.0)
    # Use dedicated Death model for death overs (>= 15.0)
    # Use Part 1 model for earlier overs (< 15.0) if provided, or Death model
    mask_death = all_sampled_df["overs_completed"] >= 15.0
    if mask_death.any():
        preds_final_death = death_model.predict(all_sampled_df[mask_death])
        traj_df.loc[mask_death, "expected_final_score"] = np.round(preds_final_death, 1)

    mask_pre_death = all_sampled_df["overs_completed"] < 15.0
    if mask_pre_death.any():
        if part1_model is not None:
            preds_final_early = part1_model.predict(all_sampled_df[mask_pre_death])
        else:
            preds_final_early = death_model.predict(all_sampled_df[mask_pre_death])
        traj_df.loc[mask_pre_death, "expected_final_score"] = np.round(preds_final_early, 1)

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    traj_df.to_csv(out_file, index=False)
    return traj_df


def extract_trajectory_examples(
    all_df: pd.DataFrame,
    traj_df: pd.DataFrame,
    test_match_ids: List[Any],
    n_matches: int = 10,
    random_state: int = 42
) -> List[Dict[str, Any]]:
    """
    Extract multi-checkpoint trajectories for real unseen test matches to inspect calibration.
    """
    rng = np.random.default_rng(random_state)
    chosen_matches = rng.choice(test_match_ids, size=min(n_matches, len(test_match_ids)), replace=False)

    examples: List[Dict[str, Any]] = []
    for m_id in chosen_matches:
        m_traj = traj_df[traj_df["match_id"] == m_id].sort_values("over")
        m_raw = all_df[all_df["match_id"] == m_id].sort_values("overs_completed")

        if len(m_traj) == 0:
            continue

        act_6 = float(m_raw[TARGET_PP].iloc[0])
        act_15 = float(m_raw[TARGET_MID].iloc[0])
        act_final = float(m_raw[TARGET_FINAL].iloc[0])
        b_team = str(m_traj["batting_team"].iloc[0])
        season = str(m_raw["season"].iloc[0])

        states_list = []
        for _, row in m_traj.iterrows():
            ov = float(row["over"])
            states_list.append({
                "over": ov,
                "score_wickets": f"{int(row['current_team_runs'])}/{int(row['wickets_lost_so_far'])}",
                "rr": round(float(row["current_team_rr"]), 2),
                "expected_score_at_6": None if pd.isna(row["expected_score_at_6"]) else float(row["expected_score_at_6"]),
                "expected_score_at_15": None if pd.isna(row["expected_score_at_15"]) else float(row["expected_score_at_15"]),
                "expected_final_score": None if pd.isna(row["expected_final_score"]) else float(row["expected_final_score"]),
            })

        examples.append({
            "match_id": str(m_id),
            "season": season,
            "batting_team": b_team,
            "actual_score_at_6": int(act_6),
            "actual_score_at_15": int(act_15),
            "actual_final_score": int(act_final),
            "trajectory": states_list,
        })

    return examples


def generate_phase_evaluation_plots(
    test_pp: pd.DataFrame,
    test_mid: pd.DataFrame,
    test_death: pd.DataFrame,
    pp_window_metrics: Dict[str, Dict[str, Any]],
    mid_window_metrics: Dict[str, Dict[str, Any]],
    death_window_metrics: Dict[str, Dict[str, Any]],
    pp_importances: Dict[str, float],
    mid_importances: Dict[str, float],
    death_importances: Dict[str, float],
    trajectory_examples: List[Dict[str, Any]],
    output_dir: Union[str, Path]
) -> List[str]:
    """Generate all 6 required visualization figures."""
    plot_dir = Path(output_dir)
    plot_dir.mkdir(parents=True, exist_ok=True)
    generated_plots: List[str] = []

    plt.style.use("tableau-colorblind10" if "tableau-colorblind10" in plt.style.available else "default")
    plt.rcParams["font.sans-serif"] = "DejaVu Sans"
    plt.rcParams["font.size"] = 10

    # 1. Actual vs Predicted Powerplay Score
    fig, ax = plt.subplots(figsize=(7, 6), dpi=150)
    y_true_pp = test_pp[TARGET_PP].to_numpy()
    y_pred_pp = test_pp["pred_rf"].to_numpy()
    ax.scatter(y_true_pp, y_pred_pp, alpha=0.35, color="#1f77b4", s=20, label=f"Powerplay States (n={len(test_pp)})")
    min_v, max_v = min(y_true_pp.min(), y_pred_pp.min()) - 5, max(y_true_pp.max(), y_pred_pp.max()) + 5
    ax.plot([min_v, max_v], [min_v, max_v], "r--", linewidth=1.5, label="Perfect Prediction (y=x)")
    ax.set_xlabel("Actual Team Score at Over 6", fontweight="bold")
    ax.set_ylabel("Predicted Score at Over 6 (RF)", fontweight="bold")
    ax.set_title("Powerplay Model: Actual vs Predicted 6-Over Score", fontweight="bold", pad=12)
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(frameon=True)
    p1 = plot_dir / "actual_vs_predicted_pp.png"
    plt.tight_layout()
    plt.savefig(p1)
    plt.close(fig)
    generated_plots.append(str(p1))

    # 2. Actual vs Predicted 15-Over Score
    fig, ax = plt.subplots(figsize=(7, 6), dpi=150)
    y_true_mid = test_mid[TARGET_MID].to_numpy()
    y_pred_mid = test_mid["pred_rf"].to_numpy()
    ax.scatter(y_true_mid, y_pred_mid, alpha=0.35, color="#2ca02c", s=20, label=f"Middle States (n={len(test_mid)})")
    min_v, max_v = min(y_true_mid.min(), y_pred_mid.min()) - 10, max(y_true_mid.max(), y_pred_mid.max()) + 10
    ax.plot([min_v, max_v], [min_v, max_v], "r--", linewidth=1.5, label="Perfect Prediction (y=x)")
    ax.set_xlabel("Actual Team Score at Over 15", fontweight="bold")
    ax.set_ylabel("Predicted Score at Over 15 (RF)", fontweight="bold")
    ax.set_title("Middle Model: Actual vs Predicted 15-Over Score", fontweight="bold", pad=12)
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(frameon=True)
    p2 = plot_dir / "actual_vs_predicted_mid.png"
    plt.tight_layout()
    plt.savefig(p2)
    plt.close(fig)
    generated_plots.append(str(p2))

    # 3. Actual vs Predicted Final Score (Death Model)
    fig, ax = plt.subplots(figsize=(7, 6), dpi=150)
    y_true_death = test_death[TARGET_FINAL].to_numpy()
    y_pred_death = test_death["pred_rf"].to_numpy()
    ax.scatter(y_true_death, y_pred_death, alpha=0.35, color="#d62728", s=20, label=f"Death States (n={len(test_death)})")
    min_v, max_v = min(y_true_death.min(), y_pred_death.min()) - 10, max(y_true_death.max(), y_pred_death.max()) + 10
    ax.plot([min_v, max_v], [min_v, max_v], "k--", linewidth=1.5, label="Perfect Prediction (y=x)")
    ax.set_xlabel("Actual Final Team Score", fontweight="bold")
    ax.set_ylabel("Predicted Final Score (Death RF)", fontweight="bold")
    ax.set_title("Death Model: Actual vs Predicted Final Score", fontweight="bold", pad=12)
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(frameon=True)
    p3 = plot_dir / "actual_vs_predicted_death.png"
    plt.tight_layout()
    plt.savefig(p3)
    plt.close(fig)
    generated_plots.append(str(p3))

    # 4. MAE by Prediction Window
    fig, ax = plt.subplots(figsize=(10, 5.5), dpi=150)
    windows_labels = []
    base_maes = []
    rf_maes = []

    # Powerplay windows
    for w in ["overs 1–2", "overs 3–4", "over 5"]:
        windows_labels.append(f"PP\n{w}")
        base_maes.append(pp_window_metrics[w]["baseline_mae"])
        rf_maes.append(pp_window_metrics[w]["rf_mae"])

    # Middle windows
    for w in ["overs 6–9", "overs 10–12", "overs 13–14"]:
        windows_labels.append(f"Mid\n{w}")
        base_maes.append(mid_window_metrics[w]["baseline_mae"])
        rf_maes.append(mid_window_metrics[w]["rf_mae"])

    # Death windows
    for w in ["over 15", "over 16", "over 17", "over 18", "over 19"]:
        windows_labels.append(f"Death\n{w}")
        base_maes.append(death_window_metrics[w]["baseline_mae"])
        rf_maes.append(death_window_metrics[w]["rf_mae"])

    x_idx = np.arange(len(windows_labels))
    w_width = 0.35
    ax.bar(x_idx - w_width / 2, base_maes, w_width, label="Simple Baseline", color="#e74c3c", alpha=0.85)
    ax.bar(x_idx + w_width / 2, rf_maes, w_width, label="Random Forest", color="#27ae60", alpha=0.85)
    ax.set_ylabel("Mean Absolute Error (Runs)", fontweight="bold")
    ax.set_title("Prediction Error (MAE) by Sub-Phase Over Windows", fontweight="bold", pad=12)
    ax.set_xticks(x_idx)
    ax.set_xticklabels(windows_labels, fontsize=8.5)
    ax.grid(True, axis="y", linestyle=":", alpha=0.6)
    ax.legend(frameon=True)
    p4 = plot_dir / "mae_by_prediction_window.png"
    plt.tight_layout()
    plt.savefig(p4)
    plt.close(fig)
    generated_plots.append(str(p4))

    # 5. Feature Importance Comparison Across Models
    fig, ax = plt.subplots(figsize=(9, 5.5), dpi=150)
    all_features = [
        "current_team_rr",
        "current_team_runs",
        "wickets_remaining",
        "wickets_lost_so_far",
        "overs_completed",
        "distance_to_checkpoint",
    ]
    # Map distance feature per model
    pp_dist = pp_importances.get("balls_remaining_until_6", 0.0)
    mid_dist = mid_importances.get("balls_remaining_until_15", 0.0)
    dth_dist = death_importances.get("balls_remaining_in_innings", 0.0)

    pp_vals = [pp_importances.get(f, pp_dist if f == "distance_to_checkpoint" else 0.0) for f in all_features]
    mid_vals = [mid_importances.get(f, mid_dist if f == "distance_to_checkpoint" else 0.0) for f in all_features]
    dth_vals = [death_importances.get(f, dth_dist if f == "distance_to_checkpoint" else 0.0) for f in all_features]

    x_feat = np.arange(len(all_features))
    bar_w = 0.25
    ax.bar(x_feat - bar_w, pp_vals, bar_w, label="Powerplay Model (Score @ 6)", color="#1f77b4", alpha=0.85)
    ax.bar(x_feat, mid_vals, bar_w, label="Middle Model (Score @ 15)", color="#2ca02c", alpha=0.85)
    ax.bar(x_feat + bar_w, dth_vals, bar_w, label="Death Model (Final Score)", color="#d62728", alpha=0.85)
    ax.set_xticks(x_feat)
    ax.set_xticklabels([f.replace("_", " ").title() for f in all_features], fontsize=9)
    ax.set_ylabel("Gini Importance", fontweight="bold")
    ax.set_title("Feature Importance Evolution Across Innings Checkpoints", fontweight="bold", pad=12)
    ax.grid(True, axis="y", linestyle=":", alpha=0.6)
    ax.legend(frameon=True)
    p5 = plot_dir / "feature_importance_comparison.png"
    plt.tight_layout()
    plt.savefig(p5)
    plt.close(fig)
    generated_plots.append(str(p5))

    # 6. Example Expected-Score Trajectories for Several Unseen Matches
    fig, axes = plt.subplots(2, 2, figsize=(12, 9), dpi=150)
    flat_axes = axes.flatten()
    for idx, ex in enumerate(trajectory_examples[:4]):
        ax_i = flat_axes[idx]
        traj = ex["trajectory"]
        overs_x = [t["over"] for t in traj]
        runs_so_far = [int(t["score_wickets"].split("/")[0]) for t in traj]
        exp_final = [t["expected_final_score"] for t in traj]
        exp_6 = [t["expected_score_at_6"] for t in traj if t["expected_score_at_6"] is not None]
        ov_6 = [t["over"] for t in traj if t["expected_score_at_6"] is not None]
        exp_15 = [t["expected_score_at_15"] for t in traj if t["expected_score_at_15"] is not None]
        ov_15 = [t["over"] for t in traj if t["expected_score_at_15"] is not None]

        ax_i.plot(overs_x, runs_so_far, "k-o", label="Current Runs", markersize=4, linewidth=1.5)
        ax_i.plot(overs_x, exp_final, "r--s", label="Expected Final", markersize=3, linewidth=1.2)
        if exp_6:
            ax_i.plot(ov_6, exp_6, "b:^", label="Expected @ 6", markersize=3)
        if exp_15:
            ax_i.plot(ov_15, exp_15, "g:d", label="Expected @ 15", markersize=3)

        # Actual checkpoints markers
        ax_i.scatter([6.0], [ex["actual_score_at_6"]], color="blue", marker="*", s=90, label=f"Act @ 6 ({ex['actual_score_at_6']})", zorder=5)
        ax_i.scatter([15.0], [ex["actual_score_at_15"]], color="green", marker="*", s=90, label=f"Act @ 15 ({ex['actual_score_at_15']})", zorder=5)
        ax_i.scatter([overs_x[-1]], [ex["actual_final_score"]], color="red", marker="*", s=90, label=f"Act Final ({ex['actual_final_score']})", zorder=5)

        ax_i.set_title(f"Match {ex['match_id']}: {ex['batting_team']} ({ex['season']})", fontsize=10, fontweight="bold")
        ax_i.set_xlabel("Overs Completed", fontsize=9)
        ax_i.set_ylabel("Runs", fontsize=9)
        ax_i.grid(True, linestyle=":", alpha=0.6)
        if idx == 0:
            ax_i.legend(frameon=True, fontsize=7.5, loc="upper left")

    p6 = plot_dir / "trajectory_examples.png"
    plt.tight_layout()
    plt.savefig(p6)
    plt.close(fig)
    generated_plots.append(str(p6))

    return generated_plots


def run_phase_scoring_pipeline(
    output_dir: str = "models/expected_score_phase",
    test_size: float = 0.2,
    random_state: int = 42
) -> Dict[str, Any]:
    """
    Execute full Phase 3 Part 2 pipeline.
    """
    out_dir = Path(output_dir)
    plots_dir = out_dir / "plots"
    out_dir.mkdir(parents=True, exist_ok=True)
    plots_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 65)
    print("PHASE 3 PART 2: PHASE-BASED EXPECTED SCORING ENGINE")
    print("=" * 65)

    # 1. Load data
    print("\n[1/7] Loading partitioned phase datasets and targets...")
    pp_df, mid_df, death_df, all_df, meta = load_phase_expected_datasets()
    print(f"  Usable 1st Innings:   {meta['usable_first_innings']}")
    print(f"  Total States:         {meta['total_sampled_states']}")
    print(f"  Powerplay States (1-5): {meta['powerplay_states_count']}")
    print(f"  Middle States (6-14):   {meta['middle_states_count']}")
    print(f"  Death States (15-19):   {meta['death_states_count']}")

    # 2. Match-level split
    print(f"\n[2/7] Splitting datasets by Match ID (80% train / 20% test, seed={random_state})...")
    train_dict, test_dict, train_m, test_m = split_phase_datasets_by_match(
        pp_df, mid_df, death_df, all_df, test_size=test_size, random_state=random_state
    )
    print(f"  Train Matches: {len(train_m)} | Test Matches: {len(test_m)}")

    # 3. Model Training
    print("\n[3/7] Training Phase-Specific Models and Baselines...")

    # Powerplay Model
    print("  -> Training Powerplay Model (Target: score_at_6)...")
    pp_model = PowerplayRFModel(random_state=random_state)
    pp_model.fit(train_dict["powerplay"], train_dict["powerplay"][TARGET_PP])
    pp_base = PowerplayBaseline()

    # Middle Model
    print("  -> Training Middle Model (Target: score_at_15)...")
    mid_model = MiddleRFModel(random_state=random_state)
    mid_model.fit(train_dict["middle"], train_dict["middle"][TARGET_MID])
    mid_base = MiddleBaseline()

    # Death Model
    print("  -> Training Death Model (Target: final_team_score)...")
    death_model = DeathRFModel(random_state=random_state)
    death_model.fit(train_dict["death"], train_dict["death"][TARGET_FINAL])
    death_base = DeathBaseline()

    # Load Part 1 Model for comparison & early final trajectory
    part1_model_path = Path("models/expected_score")
    part1_model = ExpectedScoreRFModel.load(part1_model_path) if part1_model_path.exists() else None

    # 4. Model Evaluation
    print("\n[4/7] Evaluating Test Predictions...")
    test_pp = test_dict["powerplay"].copy()
    test_mid = test_dict["middle"].copy()
    test_death = test_dict["death"].copy()

    # Predictions
    test_pp["pred_base"] = pp_base.predict(test_pp)
    test_pp["pred_rf"] = pp_model.predict(test_pp)

    test_mid["pred_base"] = mid_base.predict(test_mid)
    test_mid["pred_rf"] = mid_model.predict(test_mid)

    test_death["pred_base"] = death_base.predict(test_death)
    test_death["pred_rf"] = death_model.predict(test_death)
    if part1_model is not None:
        test_death["pred_part1"] = part1_model.predict(test_death)

    # Metrics
    m_pp_base = calculate_metrics(test_pp[TARGET_PP], test_pp["pred_base"])
    m_pp_rf = calculate_metrics(test_pp[TARGET_PP], test_pp["pred_rf"])

    m_mid_base = calculate_metrics(test_mid[TARGET_MID], test_mid["pred_base"])
    m_mid_rf = calculate_metrics(test_mid[TARGET_MID], test_mid["pred_rf"])

    m_death_base = calculate_metrics(test_death[TARGET_FINAL], test_death["pred_base"])
    m_death_rf = calculate_metrics(test_death[TARGET_FINAL], test_death["pred_rf"])
    m_death_part1 = (
        calculate_metrics(test_death[TARGET_FINAL], test_death["pred_part1"])
        if part1_model is not None else None
    )

    print("\n  ================ EVALUATION COMPARISON TABLE ================")
    print(f"  {'Model':<16} | {'Target':<14} | {'Test States':<11} | {'Base MAE':<9} | {'RF MAE':<8} | {'Base R2':<9} | {'RF R2':<8}")
    print(f"  {'-'*16}-|-{'-'*14}-|-{'-'*11}-|-{'-'*9}-|-{'-'*8}-|-{'-'*9}-|-{'-'*8}")
    print(f"  {'Powerplay':<16} | {'score_at_6':<14} | {len(test_pp):<11} | {m_pp_base['MAE']:<9.2f} | {m_pp_rf['MAE']:<8.2f} | {m_pp_base['R2']:<9.4f} | {m_pp_rf['R2']:<8.4f}")
    print(f"  {'Middle':<16} | {'score_at_15':<14} | {len(test_mid):<11} | {m_mid_base['MAE']:<9.2f} | {m_mid_rf['MAE']:<8.2f} | {m_mid_base['R2']:<9.4f} | {m_mid_rf['R2']:<8.4f}")
    print(f"  {'Death':<16} | {'final_score':<14} | {len(test_death):<11} | {m_death_base['MAE']:<9.2f} | {m_death_rf['MAE']:<8.2f} | {m_death_base['R2']:<9.4f} | {m_death_rf['R2']:<8.4f}")
    print("  =============================================================")

    # 5. Window Breakdown Evaluations
    print("\n[5/7] Computing Phase-Window Error Breakdowns...")
    pp_windows = {
        "overs 1–2": [1.0, 2.0],
        "overs 3–4": [3.0, 4.0],
        "over 5": [5.0],
    }
    pp_window_res = {}
    for w_name, ovs in pp_windows.items():
        sub = test_pp[test_pp["overs_completed"].isin(ovs)]
        pp_window_res[w_name] = {
            "baseline_mae": round(float(mean_absolute_error(sub[TARGET_PP], sub["pred_base"])), 2),
            "rf_mae": round(float(mean_absolute_error(sub[TARGET_PP], sub["pred_rf"])), 2),
            "rf_rmse": round(float(root_mean_squared_error(sub[TARGET_PP], sub["pred_rf"])), 2),
            "rf_r2": round(float(r2_score(sub[TARGET_PP], sub["pred_rf"])), 4),
            "count": len(sub),
        }
        print(f"    PP {w_name:12s} (n={len(sub)}): Base MAE={pp_window_res[w_name]['baseline_mae']:.2f}, RF MAE={pp_window_res[w_name]['rf_mae']:.2f}, RF R2={pp_window_res[w_name]['rf_r2']:.4f}")

    mid_windows = {
        "overs 6–9": [6.0, 7.0, 8.0, 9.0],
        "overs 10–12": [10.0, 11.0, 12.0],
        "overs 13–14": [13.0, 14.0],
    }
    mid_window_res = {}
    for w_name, ovs in mid_windows.items():
        sub = test_mid[test_mid["overs_completed"].isin(ovs)]
        mid_window_res[w_name] = {
            "baseline_mae": round(float(mean_absolute_error(sub[TARGET_MID], sub["pred_base"])), 2),
            "rf_mae": round(float(mean_absolute_error(sub[TARGET_MID], sub["pred_rf"])), 2),
            "rf_rmse": round(float(root_mean_squared_error(sub[TARGET_MID], sub["pred_rf"])), 2),
            "rf_r2": round(float(r2_score(sub[TARGET_MID], sub["pred_rf"])), 4),
            "count": len(sub),
        }
        print(f"    Mid {w_name:12s} (n={len(sub)}): Base MAE={mid_window_res[w_name]['baseline_mae']:.2f}, RF MAE={mid_window_res[w_name]['rf_mae']:.2f}, RF R2={mid_window_res[w_name]['rf_r2']:.4f}")

    death_windows = {
        "over 15": [15.0],
        "over 16": [16.0],
        "over 17": [17.0],
        "over 18": [18.0],
        "over 19": [19.0],
    }
    death_window_res = {}
    for w_name, ovs in death_windows.items():
        sub = test_death[test_death["overs_completed"].isin(ovs)]
        death_window_res[w_name] = {
            "baseline_mae": round(float(mean_absolute_error(sub[TARGET_FINAL], sub["pred_base"])), 2),
            "rf_mae": round(float(mean_absolute_error(sub[TARGET_FINAL], sub["pred_rf"])), 2),
            "rf_rmse": round(float(root_mean_squared_error(sub[TARGET_FINAL], sub["pred_rf"])), 2),
            "rf_r2": round(float(r2_score(sub[TARGET_FINAL], sub["pred_rf"])), 4),
            "count": len(sub),
        }
        print(f"    Death {w_name:12s} (n={len(sub)}): Base MAE={death_window_res[w_name]['baseline_mae']:.2f}, RF MAE={death_window_res[w_name]['rf_mae']:.2f}, RF R2={death_window_res[w_name]['rf_r2']:.4f}")

    # 6. Build Trajectory Dataset
    print("\n[6/7] Building Trajectory Dataset (data/processed/expected_scoring_trajectory.csv)...")
    traj_df = build_trajectory_dataset(
        all_sampled_df=all_df,
        pp_model=pp_model,
        mid_model=mid_model,
        death_model=death_model,
        part1_model=part1_model,
        output_path="data/processed/expected_scoring_trajectory.csv"
    )
    print(f"  Generated {len(traj_df)} trajectory records across {traj_df['match_id'].nunique()} matches.")

    # Extract 10+ real unseen test match trajectories for calibration inspection
    traj_examples = extract_trajectory_examples(
        all_df=all_df,
        traj_df=traj_df,
        test_match_ids=test_m,
        n_matches=12,
        random_state=random_state
    )

    # 7. Generate Plots & Save Artifacts
    print("\n[7/7] Generating Plots and Saving Artifacts...")
    pp_imp = pp_model.get_feature_importances()
    mid_imp = mid_model.get_feature_importances()
    death_imp = death_model.get_feature_importances()

    plot_files = generate_phase_evaluation_plots(
        test_pp=test_pp,
        test_mid=test_mid,
        test_death=test_death,
        pp_window_metrics=pp_window_res,
        mid_window_metrics=mid_window_res,
        death_window_metrics=death_window_res,
        pp_importances=pp_imp,
        mid_importances=mid_imp,
        death_importances=death_imp,
        trajectory_examples=traj_examples,
        output_dir=plots_dir
    )
    print(f"  Generated {len(plot_files)} plots in {plots_dir}")

    # Save models
    pp_model.save(out_dir / "powerplay_model.joblib")
    mid_model.save(out_dir / "middle_model.joblib")
    death_model.save(out_dir / "death_model.joblib")

    # Save feature names
    with open(out_dir / "feature_names_pp.json", "w", encoding="utf-8") as f:
        json.dump(PP_FEATURE_COLUMNS, f, indent=2)
    with open(out_dir / "feature_names_mid.json", "w", encoding="utf-8") as f:
        json.dump(MID_FEATURE_COLUMNS, f, indent=2)
    with open(out_dir / "feature_names_death.json", "w", encoding="utf-8") as f:
        json.dump(DEATH_FEATURE_COLUMNS, f, indent=2)

    # Save configs and metrics
    metrics_summary = {
        "powerplay_model": {
            "target": TARGET_PP,
            "test_states": len(test_pp),
            "baseline": m_pp_base,
            "random_forest": m_pp_rf,
            "window_breakdown": pp_window_res,
            "feature_importances": pp_imp,
        },
        "middle_model": {
            "target": TARGET_MID,
            "test_states": len(test_mid),
            "baseline": m_mid_base,
            "random_forest": m_mid_rf,
            "window_breakdown": mid_window_res,
            "feature_importances": mid_imp,
        },
        "death_model": {
            "target": TARGET_FINAL,
            "test_states": len(test_death),
            "baseline": m_death_base,
            "random_forest": m_death_rf,
            "comparison_part1_model": m_death_part1,
            "window_breakdown": death_window_res,
            "feature_importances": death_imp,
        },
    }

    with open(out_dir / "metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics_summary, f, indent=2)

    with open(out_dir / "config.json", "w", encoding="utf-8") as f:
        json.dump({
            "test_size": test_size,
            "random_state": random_state,
            "powerplay_config": pp_model.config,
            "middle_config": mid_model.config,
            "death_config": death_model.config,
        }, f, indent=2)

    with open(out_dir / "train_test_split.json", "w", encoding="utf-8") as f:
        json.dump({
            "train_match_ids": [str(m) for m in train_m],
            "test_match_ids": [str(m) for m in test_m],
            "train_matches_count": len(train_m),
            "test_matches_count": len(test_m),
        }, f, indent=2)

    with open(out_dir / "trajectory_examples.json", "w", encoding="utf-8") as f:
        json.dump(traj_examples, f, indent=2)

    print("\nPhase-Based Expected Scoring Pipeline completed successfully!")
    print("=" * 65)

    return {
        "metrics_summary": metrics_summary,
        "plot_files": plot_files,
        "trajectory_examples": traj_examples,
        "metadata": meta,
    }


if __name__ == "__main__":
    run_phase_scoring_pipeline()
