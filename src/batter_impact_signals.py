"""
Batter Impact Signals & State Transformation Engine (Phase 4B).

Builds comprehensive impact signals across:
1. Actual Individual Batter Performance (runs, SR, runs_per_ball, opportunity_usage, boundary metrics).
2. Team State Transformation (overs_spent, window_team_rr, team_rr_change, team_runs_added).
3. Batting Resource Transformation (wicket_resource_change, wickets_lost_during_stay, overs_remaining).
4. First-Innings Trajectory Shifts (expected_final_entry, exit, change, trajectory_deviation_change).
5. Chase State Transformation (required_rr_change, rr_gap_change, runs_required_reduction, chase_pressure_relief_rr, relative_rr_relief).
6. Partnership Dynamics (partnership_runs, partner_runs, batter_partnership_share, partnership_duration).
7. Retrospective Post-Exit Observations (post_exit_runs, post_exit_overs, post_exit_rr, post_exit_wickets_lost, post_exit_rr_change, final_team_score).
8. Match Outcome Context (won_match, winning_margin, margin_type, target_reached).

Output:
data/processed/batter_impact_signals.csv
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# Ensure repository root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def build_batter_impact_signals(
    performance_dataset_path: str = "data/processed/batter_performance_dataset.csv",
    innings_path: str = "data/processed/innings.csv",
    matches_path: str = "data/processed/matches.csv",
    output_path: str = "data/processed/batter_impact_signals.csv",
) -> pd.DataFrame:
    """
    Load Phase 4A batter performance dataset, attach post-exit observations and
    match outcomes, calculate all Phase 4B impact and transformation signals,
    and save data/processed/batter_impact_signals.csv.
    """
    df = pd.read_csv(performance_dataset_path, low_memory=False)
    df_inn = pd.read_csv(innings_path)
    df_m = pd.read_csv(matches_path)

    # -------------------------------------------------------------
    # 1. Identity & Core Entry/Exit Alignment
    # -------------------------------------------------------------
    # Standardize column naming
    if "player" not in df.columns and "batter" in df.columns:
        df["player"] = df["batter"]
    if "innings" not in df.columns and "innings_number" in df.columns:
        df["innings"] = df["innings_number"]
    if "team" not in df.columns and "batting_team" in df.columns:
        df["team"] = df["batting_team"]
    if "opponent" not in df.columns and "bowling_team" in df.columns:
        df["opponent"] = df["bowling_team"]

    # -------------------------------------------------------------
    # 2. Individual Batter Performance & Opportunity Usage
    # -------------------------------------------------------------
    # Actuals & Deviations
    actual_runs = df["actual_runs"].fillna(df.get("runs", 0)).astype(int)
    balls_faced = df["balls_faced"].fillna(df.get("balls", 0)).astype(int)
    actual_sr = df["actual_sr"].fillna(df.get("strike_rate", 0.0)).astype(float)
    expected_runs = df["expected_runs"].astype(float)
    expected_sr = df["expected_sr"].astype(float)

    df["actual_runs"] = actual_runs
    df["balls_faced"] = balls_faced
    df["actual_sr"] = actual_sr
    df["expected_runs"] = expected_runs
    df["expected_sr"] = expected_sr

    # Deviations & Ratios
    df["run_deviation"] = np.round(actual_runs - expected_runs, 2)
    df["sr_deviation"] = np.round(actual_sr - expected_sr, 2)
    df["run_performance_ratio"] = np.where(
        expected_runs > 0,
        np.round(actual_runs / expected_runs, 3),
        np.nan
    )
    df["sr_performance_ratio"] = np.where(
        expected_sr > 0,
        np.round(actual_sr / expected_sr, 3),
        np.nan
    )

    # Runs per ball
    df["runs_per_ball"] = np.where(
        balls_faced > 0,
        np.round(actual_runs / balls_faced, 3),
        0.0
    )

    # Opportunity Usage: balls faced relative to balls available at entry
    balls_available = df["entry_balls_remaining"].fillna(120).astype(int)
    df["opportunity_usage"] = np.where(
        balls_available > 0,
        np.round(balls_faced / balls_available, 4),
        0.0
    )

    # Boundaries and Dots
    fours = df["fours"].fillna(0).astype(int)
    sixes = df["sixes"].fillna(0).astype(int)
    df["fours"] = fours
    df["sixes"] = sixes
    df["boundary_runs"] = fours * 4 + sixes * 6

    df["boundary_percentage"] = np.where(
        actual_runs > 0,
        np.round((df["boundary_runs"] / actual_runs) * 100.0, 2),
        0.0
    )
    df["boundary_runs_per_ball"] = np.where(
        balls_faced > 0,
        np.round(df["boundary_runs"] / balls_faced, 3),
        0.0
    )

    dot_balls = df["dot_balls"].fillna(0).astype(int)
    df["dot_balls"] = dot_balls
    df["dot_ball_percentage"] = np.where(
        balls_faced > 0,
        np.round((dot_balls / balls_faced) * 100.0, 2),
        0.0
    )

    # -------------------------------------------------------------
    # 3. Team State Transformation During Batter Window
    # -------------------------------------------------------------
    df["team_score_entry"] = df["entry_score"].astype(int)
    df["team_score_exit"] = df["exit_score"].astype(int)
    df["team_runs_added"] = df["team_score_exit"] - df["team_score_entry"]

    df["team_rr_entry"] = df["entry_team_rr"].astype(float)
    df["team_rr_exit"] = df["exit_team_rr"].astype(float)
    df["team_rr_change"] = np.round(df["team_rr_exit"] - df["team_rr_entry"], 2)

    # Legal balls bowled during batter's stay
    entry_over_int = df["entry_over"].astype(float).astype(int)
    entry_ball = np.round((df["entry_over"].astype(float) - entry_over_int) * 10).astype(int)
    entry_legal_balls = entry_over_int * 6 + entry_ball

    exit_over_val = df["exit_over"].fillna(df["entry_over"]).astype(float)
    exit_over_int = exit_over_val.astype(int)
    exit_ball = np.round((exit_over_val - exit_over_int) * 10).astype(int)
    exit_legal_balls = exit_over_int * 6 + exit_ball

    balls_spent = np.maximum(0, exit_legal_balls - entry_legal_balls)
    overs_spent = np.round(balls_spent / 6.0, 2)
    df["overs_spent"] = overs_spent

    df["window_team_rr"] = np.where(
        overs_spent > 0,
        np.round(df["team_runs_added"] / overs_spent, 2),
        0.0
    )

    # -------------------------------------------------------------
    # 4. Batting Resource Transformation
    # -------------------------------------------------------------
    df["wickets_remaining_entry"] = df["entry_wickets_remaining"].astype(int)
    df["wickets_remaining_exit"] = df["exit_wickets_remaining"].astype(int)
    df["wickets_lost_during_stay"] = np.maximum(
        0, df["wickets_remaining_entry"] - df["wickets_remaining_exit"]
    )
    df["wicket_resource_change"] = df["wickets_remaining_exit"] - df["wickets_remaining_entry"]

    df["balls_remaining_entry"] = df["entry_balls_remaining"].astype(int)
    df["balls_remaining_exit"] = df["exit_balls_remaining"].astype(int)
    df["overs_remaining_entry"] = np.round(df["balls_remaining_entry"] / 6.0, 2)
    df["overs_remaining_exit"] = np.round(df["balls_remaining_exit"] / 6.0, 2)

    # -------------------------------------------------------------
    # 5. First-Innings Trajectory Shifts (Strictly NULL for 2nd innings)
    # -------------------------------------------------------------
    # Preserved exactly from Phase 4A
    is_1st = (df["innings"] == 1)
    df["expected_final_entry"] = df["expected_final_entry"].where(is_1st, np.nan)
    df["expected_final_exit"] = df["expected_final_exit"].where(is_1st, np.nan)
    df["expected_final_change"] = df["expected_final_change"].where(is_1st, np.nan)
    df["entry_score_deviation"] = df["entry_score_deviation"].where(is_1st, np.nan)
    df["exit_score_deviation"] = df["exit_score_deviation"].where(is_1st, np.nan)
    df["trajectory_deviation_change"] = df["trajectory_deviation_change"].where(is_1st, np.nan)

    # -------------------------------------------------------------
    # 6. Chase State Transformation (Strictly NULL for 1st innings)
    # -------------------------------------------------------------
    is_chase = (df["innings"] == 2)
    df["target"] = df["target"].where(is_chase, np.nan)
    df["runs_required_entry"] = df["runs_required_entry"].where(is_chase, np.nan)
    df["runs_required_exit"] = df["runs_required_exit"].where(is_chase, np.nan)
    df["required_rr_entry"] = df["required_rr_entry"].where(is_chase, np.nan)
    df["required_rr_exit"] = df["required_rr_exit"].where(is_chase, np.nan)
    df["required_rr_change"] = df["required_rr_change"].where(is_chase, np.nan)
    df["rr_gap_entry"] = df["rr_gap_entry"].where(is_chase, np.nan)
    df["rr_gap_exit"] = df["rr_gap_exit"].where(is_chase, np.nan)
    df["rr_gap_change"] = df["rr_gap_change"].where(is_chase, np.nan)
    df["runs_required_reduction"] = df["runs_required_reduction"].where(is_chase, np.nan)
    df["target_progress_entry"] = df["target_progress_entry"].where(is_chase, np.nan)
    df["target_progress_exit"] = df["target_progress_exit"].where(is_chase, np.nan)
    df["target_progress_change"] = df["target_progress_change"].where(is_chase, np.nan)

    # Chase Pressure Relief (Section 17)
    df["chase_pressure_relief_rr"] = df["required_rr_change"]
    df["relative_rr_relief"] = np.where(
        is_chase & (df["required_rr_entry"] > 0),
        np.round(df["required_rr_change"] / df["required_rr_entry"], 4),
        np.nan
    )

    # -------------------------------------------------------------
    # 7. Partnership Dynamics
    # -------------------------------------------------------------
    part_runs = df["partnership_runs"].fillna(0).astype(int)
    b_part_runs = df["batter_partnership_runs"].fillna(0).astype(int)
    df["partnership_runs"] = part_runs
    df["batter_partnership_runs"] = b_part_runs
    df["partner_runs"] = np.maximum(0, part_runs - b_part_runs)
    df["batter_partnership_share"] = np.where(
        part_runs > 0,
        np.round(b_part_runs / part_runs, 3),
        0.0
    )
    df["partnership_duration"] = df["partnership_duration"].fillna(0).astype(int)

    # -------------------------------------------------------------
    # 8. Post-Exit Retrospective Observations (Retrospective layer only)
    # -------------------------------------------------------------
    df = df.copy()
    # Join final team score, total wickets, and total overs from innings.csv
    inn_map = df_inn.set_index(["match_id", "innings_number"]).to_dict("index")

    post_exit_runs_list = []
    post_exit_overs_list = []
    post_exit_rr_list = []
    post_exit_wkts_list = []
    post_exit_rr_change_list = []
    final_team_scores = []

    for _, row in df.iterrows():
        key = (row["match_id"], row["innings"])
        if key in inn_map:
            inn_info = inn_map[key]
            tot_runs = int(inn_info["total_runs"])
            tot_wkts = int(inn_info["total_wickets"])
            tot_ov = float(inn_info["overs_completed"])

            tot_ov_int = int(tot_ov)
            tot_balls_in_inn = tot_ov_int * 6 + int(np.round((tot_ov - tot_ov_int) * 10))

            ex_ov = float(row["exit_over"]) if pd.notnull(row["exit_over"]) else float(row["entry_over"])
            ex_ov_int = int(ex_ov)
            ex_balls_in_inn = ex_ov_int * 6 + int(np.round((ex_ov - ex_ov_int) * 10))

            # Balls remaining in innings after batter exit
            rem_balls_after = max(0, tot_balls_in_inn - ex_balls_in_inn)
            rem_overs_after = round(rem_balls_after / 6.0, 2)

            pe_runs = max(0, tot_runs - int(row["exit_score"]))
            pe_wkts = max(0, tot_wkts - int(row["exit_wickets_lost"]))
            pe_rr = round(pe_runs / rem_overs_after, 2) if rem_overs_after > 0 else 0.0
            pe_rr_chg = round(pe_rr - float(row["exit_team_rr"]), 2) if rem_overs_after > 0 else 0.0

            post_exit_runs_list.append(pe_runs)
            post_exit_overs_list.append(rem_overs_after)
            post_exit_rr_list.append(pe_rr)
            post_exit_wkts_list.append(pe_wkts)
            post_exit_rr_change_list.append(pe_rr_chg)
            final_team_scores.append(tot_runs)
        else:
            post_exit_runs_list.append(0)
            post_exit_overs_list.append(0.0)
            post_exit_rr_list.append(0.0)
            post_exit_wkts_list.append(0)
            post_exit_rr_change_list.append(0.0)
            final_team_scores.append(int(row["exit_score"]))

    df["post_exit_runs"] = post_exit_runs_list
    df["post_exit_overs"] = post_exit_overs_list
    df["post_exit_rr"] = post_exit_rr_list
    df["post_exit_wickets_lost"] = post_exit_wkts_list
    df["post_exit_rr_change"] = post_exit_rr_change_list
    df["final_team_score"] = final_team_scores

    # -------------------------------------------------------------
    # 9. Retrospective Match Outcome (Dataset B layer)
    # -------------------------------------------------------------
    match_map = df_m.set_index("match_id").to_dict("index")
    won_match_list = []
    winning_margin_list = []
    margin_type_list = []
    target_reached_list = []

    for _, row in df.iterrows():
        mid = row["match_id"]
        team_name = row["team"]
        if mid in match_map:
            m_info = match_map[mid]
            w = m_info["winner"]
            is_win = (w == team_name) if pd.notnull(w) else False
            won_match_list.append(is_win)

            if pd.notnull(m_info.get("win_by_runs")) and m_info["win_by_runs"] > 0:
                winning_margin_list.append(float(m_info["win_by_runs"]))
                margin_type_list.append("runs")
            elif pd.notnull(m_info.get("win_by_wickets")) and m_info["win_by_wickets"] > 0:
                winning_margin_list.append(float(m_info["win_by_wickets"]))
                margin_type_list.append("wickets")
            else:
                winning_margin_list.append(0.0)
                margin_type_list.append("tie/super_over")

            # Target reached flag for chases
            if row["innings"] == 2 and pd.notnull(row["target"]):
                target_reached_list.append(bool(row["final_team_score"] >= row["target"]))
            else:
                target_reached_list.append(None)
        else:
            won_match_list.append(False)
            winning_margin_list.append(0.0)
            margin_type_list.append("unknown")
            target_reached_list.append(None)

    df["won_match"] = won_match_list
    df["winning_margin"] = winning_margin_list
    df["margin_type"] = margin_type_list
    df["target_reached"] = target_reached_list

    # -------------------------------------------------------------
    # 10. Reorder & Save Standardized Schema (Section 29)
    # -------------------------------------------------------------
    standard_cols = [
        # Identity
        "match_id", "season", "innings", "team", "opponent", "player", "batting_position",
        # Entry / Exit
        "entry_ball", "exit_ball", "entry_over", "exit_over", "dismissal_status", "dismissal_kind",
        # Batter Performance
        "actual_runs", "expected_runs", "run_deviation", "run_performance_ratio",
        "actual_sr", "expected_sr", "sr_deviation", "sr_performance_ratio",
        "balls_faced", "runs_per_ball", "opportunity_usage",
        # Boundaries / Dots
        "fours", "sixes", "boundary_runs", "boundary_percentage", "boundary_runs_per_ball",
        "dot_balls", "dot_ball_percentage",
        # Team State
        "team_score_entry", "team_score_exit", "team_rr_entry", "team_rr_exit", "team_rr_change",
        "team_runs_added", "overs_spent", "window_team_rr",
        "wickets_remaining_entry", "wickets_remaining_exit", "wickets_lost_during_stay",
        "balls_remaining_entry", "balls_remaining_exit",
        # First Innings Trajectory
        "expected_final_entry", "expected_final_exit", "expected_final_change",
        "entry_score_deviation", "exit_score_deviation", "trajectory_deviation_change",
        # Chase State
        "target", "runs_required_entry", "runs_required_exit",
        "required_rr_entry", "required_rr_exit", "required_rr_change",
        "rr_gap_entry", "rr_gap_exit", "rr_gap_change",
        "runs_required_reduction", "target_progress_entry", "target_progress_exit", "target_progress_change",
        "chase_pressure_relief_rr", "relative_rr_relief",
        # Resource
        "wicket_resource_change", "overs_remaining_entry", "overs_remaining_exit",
        # Partnership
        "partnership_runs", "batter_partnership_runs", "partner_runs",
        "batter_partnership_share", "partnership_duration",
        # Post-Exit Retrospective
        "post_exit_runs", "post_exit_overs", "post_exit_rr", "post_exit_wickets_lost",
        "post_exit_rr_change", "final_team_score",
        # Retrospective Match Outcome (Dataset B)
        "won_match", "winning_margin", "margin_type", "target_reached"
    ]

    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    df[standard_cols].to_csv(out_p, index=False)
    print(f"Saved {len(df)} batter impact signals to {output_path}")

    return df[standard_cols]


if __name__ == "__main__":
    build_batter_impact_signals()
