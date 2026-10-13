"""
Batter Innings Exact Entry & Exit Trajectory Engine (Phase 4A - Chase Corrected).

Key Capabilities:
1. Strict separation of First Innings vs Second Innings (Chase) pathways:
   - First Innings: Uses Phase 3 Expected Final Score model (expected_final_entry,
     expected_final_exit, expected_final_change, entry_score_deviation,
     exit_score_deviation, trajectory_deviation_change). Excludes rain-shortened matches (<19.5 ov & <10 wkts).
   - Second Innings / Chase: Strictly NULL for first-innings expected final score.
     Instead captures exact chase metrics: target, runs_required_entry, runs_required_exit,
     required_rr_entry, required_rr_exit, required_rr_change, rr_gap_entry, rr_gap_exit,
     rr_gap_change, runs_required_reduction, target_progress_entry, target_progress_exit,
     target_progress_change.
   - Super Overs (innings > 2): Handled as separate special cases; both 20-over 1st innings
     trajectory and standard 20-over chase metrics are set to NaN.
2. Identifies exact entry delivery/state (e.g. 7.2 overs) and exit delivery/state (e.g. 13.4 overs)
   for every batter innings (no forcing to arbitrary 6-over or 15-over checkpoints).
3. Standardized schema aligned with Phase 4A audit requirements.
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd

# Ensure repository root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.expected_score_model import ExpectedScoreRFModel


def compute_historical_par_curve(
    match_state_path: str = "data/processed/match_state.csv",
    innings_path: str = "data/processed/innings.csv"
) -> Dict[int, float]:
    """
    Compute the historical average first-innings score curve by legal ball bowled (0 to 120).
    Excludes rain-shortened / incomplete first innings (<19.5 overs and <10 wickets).

    Returns:
        Dict mapping legal balls bowled (0..120) to average historical score.
    """
    df_ms = pd.read_csv(match_state_path, low_memory=False)
    df_inn = pd.read_csv(innings_path)

    # Valid complete first innings only
    inn1 = df_inn[df_inn["innings_number"] == 1]
    short_rain = inn1[(inn1["overs_completed"] < 19.5) & (inn1["total_wickets"] < 10)]
    excluded = set(short_rain["match_id"])

    ms1 = df_ms[(df_ms["innings_number"] == 1) & (~df_ms["match_id"].isin(excluded))]
    ms1_legal = ms1[ms1["is_legal"].astype(bool)]

    # Group by legal balls bowled so far (1..120)
    avg_series = ms1_legal.groupby("legal_balls_bowled_so_far")["total_team_runs_so_far"].mean()
    curve = {0: 0.0}
    for b in range(1, 121):
        if b in avg_series.index:
            curve[b] = round(float(avg_series[b]), 2)
        else:
            prev_b = max([k for k in curve.keys() if k < b])
            curve[b] = curve[prev_b]

    return curve


def extract_batter_trajectories(
    batter_context_path: str = "data/processed/batter_context.csv",
    partnerships_path: str = "data/processed/partnerships.csv",
    innings_path: str = "data/processed/innings.csv",
    deliveries_path: str = "data/processed/deliveries.csv",
    part1_model_path: str = "models/expected_score",
    par_curve: Optional[Dict[int, float]] = None,
) -> pd.DataFrame:
    """
    Extract exact entry and exit state, trajectory metrics, chase dynamics,
    and partnership context for every batter innings.

    Strictly separates:
    - First innings: 20-over Expected Final Score model & trajectory deviation.
    - Second innings / Chase: Chase context (Target, Required RR, RR Gap, Target Progress).
      First-innings trajectory fields are set to NaN.
    - Super overs (innings > 2): Set to NaN for both 20-over trajectory and standard chase.
    """
    df_bc = pd.read_csv(batter_context_path, low_memory=False)
    df_part = pd.read_csv(partnerships_path)
    df_inn = pd.read_csv(innings_path)

    if par_curve is None:
        par_curve = compute_historical_par_curve(innings_path=innings_path)

    # Load Phase 3 Part 1 model for first-innings expected final score calculation
    rf_expected_final = ExpectedScoreRFModel.load(part1_model_path)

    # Identify rain-shortened 1st innings to exclude from 20-over trajectory model
    inn1 = df_inn[df_inn["innings_number"] == 1]
    rain_shortened_1st_matches: Set[Any] = set(
        inn1[(inn1["overs_completed"] < 19.5) & (inn1["total_wickets"] < 10)]["match_id"]
    )

    # -------------------------------------------------------------
    # 1. Exact Entry and Exit Ball & Over Parsing
    # -------------------------------------------------------------
    # In cricket float notation: e.g. 7.2 -> over 7, ball 2
    entry_overs_full = df_bc["entry_over"].fillna(0.0).astype(float)
    df_bc["entry_over_int"] = entry_overs_full.astype(int)
    df_bc["entry_ball"] = np.round((entry_overs_full - df_bc["entry_over_int"]) * 10).astype(int)
    # Total legal balls bowled at entry
    df_bc["entry_legal_balls"] = df_bc["entry_over_int"] * 6 + df_bc["entry_ball"]

    exit_overs_full = df_bc["dismissal_over"].fillna(df_bc["entry_over"]).astype(float)
    df_bc["exit_over_int"] = exit_overs_full.astype(int)
    df_bc["exit_ball"] = np.round((exit_overs_full - df_bc["exit_over_int"]) * 10).astype(int)
    # Total legal balls bowled at exit
    df_bc["exit_legal_balls"] = df_bc["exit_over_int"] * 6 + df_bc["exit_ball"]

    # Entry & Exit core states
    df_bc["entry_score"] = df_bc["entry_score"].fillna(0).astype(int)
    df_bc["entry_team_runs"] = df_bc["entry_score"]  # backward-compatible alias
    df_bc["entry_wickets_lost"] = df_bc["entry_wickets"].fillna(0).astype(int)
    df_bc["entry_wickets_remaining"] = (10 - df_bc["entry_wickets_lost"]).clip(lower=0)
    df_bc["entry_balls_remaining"] = df_bc["entry_balls_remaining"].fillna(120).astype(int)
    df_bc["entry_phase"] = df_bc["entry_innings_phase"].fillna("POWERPLAY").astype(str)

    # Entry team run rate (safe calculation from legal balls)
    df_bc["entry_team_rr"] = np.where(
        df_bc["entry_legal_balls"] > 0,
        np.round(df_bc["entry_score"] * 6.0 / df_bc["entry_legal_balls"], 2),
        0.0
    )
    df_bc["entry_rr"] = df_bc["entry_team_rr"]  # alias

    df_bc["exit_score"] = df_bc["dismissal_score"].fillna(df_bc["entry_score"]).astype(int)
    df_bc["exit_team_runs"] = df_bc["exit_score"]  # backward-compatible alias
    df_bc["exit_wickets_lost"] = df_bc["dismissal_wickets"].fillna(df_bc["entry_wickets_lost"]).astype(int)
    df_bc["exit_wickets_remaining"] = (10 - df_bc["exit_wickets_lost"]).clip(lower=0)
    df_bc["exit_balls_remaining"] = df_bc["dismissal_balls_remaining"].fillna(0).astype(int)
    df_bc["exit_phase"] = df_bc["dismissal_innings_phase"].fillna("DEATH").astype(str)

    # Exit team run rate (safe calculation from legal balls)
    df_bc["exit_team_rr"] = np.where(
        df_bc["exit_legal_balls"] > 0,
        np.round(df_bc["exit_score"] * 6.0 / df_bc["exit_legal_balls"], 2),
        0.0
    )
    df_bc["exit_rr"] = df_bc["exit_team_rr"]  # alias

    # Actual team runs change while batter was at crease (for all innings)
    df_bc["actual_team_runs_change"] = (df_bc["exit_score"] - df_bc["entry_score"]).clip(lower=0)

    # Standardized aliases
    df_bc["innings"] = df_bc["innings_number"]
    df_bc["team"] = df_bc["batting_team"]
    df_bc["opponent"] = df_bc["bowling_team"]
    df_bc["player"] = df_bc["batter"]
    df_bc["exit_over"] = df_bc["dismissal_over"]

    # -------------------------------------------------------------
    # 2. First-Innings Trajectory Pathway (ONLY for complete 1st innings)
    # -------------------------------------------------------------
    is_valid_1st = (df_bc["innings_number"] == 1) & (~df_bc["match_id"].isin(rain_shortened_1st_matches))

    exp_final_entry = np.full(len(df_bc), np.nan)
    exp_final_exit = np.full(len(df_bc), np.nan)
    exp_final_change = np.full(len(df_bc), np.nan)
    entry_score_dev = np.full(len(df_bc), np.nan)
    exit_score_dev = np.full(len(df_bc), np.nan)
    traj_dev_change = np.full(len(df_bc), np.nan)

    if is_valid_1st.any():
        df_1st = df_bc[is_valid_1st]
        entry_overs_1st = entry_overs_full[is_valid_1st]
        exit_overs_1st = exit_overs_full[is_valid_1st]

        # Feature vectors for entry
        entry_prep = pd.DataFrame({
            "current_team_runs": df_1st["entry_score"],
            "wickets_lost_so_far": df_1st["entry_wickets_lost"],
            "wickets_remaining": df_1st["entry_wickets_remaining"],
            "overs_completed": entry_overs_1st,
            "balls_remaining_in_innings": df_1st["entry_balls_remaining"],
            "current_team_rr": df_1st["entry_team_rr"],
            "innings_phase": df_1st["entry_phase"],
        })
        preds_entry = rf_expected_final.predict(entry_prep)

        # Feature vectors for exit
        exit_prep = pd.DataFrame({
            "current_team_runs": df_1st["exit_score"],
            "wickets_lost_so_far": df_1st["exit_wickets_lost"],
            "wickets_remaining": df_1st["exit_wickets_remaining"],
            "overs_completed": exit_overs_1st,
            "balls_remaining_in_innings": df_1st["exit_balls_remaining"],
            "current_team_rr": df_1st["exit_team_rr"],
            "innings_phase": df_1st["exit_phase"],
        })
        preds_exit = rf_expected_final.predict(exit_prep)

        # Terminal exit state (innings ended, balls_rem == 0 or 10 wkts down)
        is_terminal = (df_1st["exit_balls_remaining"] == 0) | (df_1st["exit_wickets_lost"] >= 10)
        preds_exit = np.where(is_terminal, df_1st["exit_score"], preds_exit)

        # Par curve lookups
        max_b = max(par_curve.keys())
        par_entry = df_1st["entry_legal_balls"].clip(0, max_b).map(par_curve).fillna(0.0)
        par_exit = df_1st["exit_legal_balls"].clip(0, max_b).map(par_curve).fillna(par_curve[max_b])

        idx_1st = df_1st.index
        exp_final_entry[idx_1st] = np.round(preds_entry, 1)
        exp_final_exit[idx_1st] = np.round(preds_exit, 1)
        exp_final_change[idx_1st] = np.round(preds_exit - preds_entry, 1)
        entry_score_dev[idx_1st] = np.round(df_1st["entry_score"] - par_entry, 1)
        exit_score_dev[idx_1st] = np.round(df_1st["exit_score"] - par_exit, 1)
        traj_dev_change[idx_1st] = np.round(exit_score_dev[idx_1st] - entry_score_dev[idx_1st], 1)

    df_bc["expected_final_entry"] = exp_final_entry
    df_bc["expected_final_exit"] = exp_final_exit
    df_bc["expected_final_change"] = exp_final_change
    df_bc["entry_score_deviation"] = entry_score_dev
    df_bc["exit_score_deviation"] = exit_score_dev
    df_bc["trajectory_deviation_change"] = traj_dev_change

    # Backward-compatible aliases
    df_bc["expected_final_score_at_entry"] = df_bc["expected_final_entry"]
    df_bc["expected_final_score_at_exit"] = df_bc["expected_final_exit"]

    # -------------------------------------------------------------
    # 3. Chase Pathway (ONLY for Second Innings, innings_number == 2)
    # -------------------------------------------------------------
    is_chase = (df_bc["innings_number"] == 2)
    df_bc["is_chase"] = is_chase

    runs_req_entry = np.full(len(df_bc), np.nan)
    runs_req_exit = np.full(len(df_bc), np.nan)
    req_rr_entry = np.full(len(df_bc), np.nan)
    req_rr_exit = np.full(len(df_bc), np.nan)
    req_rr_change = np.full(len(df_bc), np.nan)
    rr_gap_en = np.full(len(df_bc), np.nan)
    rr_gap_ex = np.full(len(df_bc), np.nan)
    rr_gap_chg = np.full(len(df_bc), np.nan)
    runs_req_reduction = np.full(len(df_bc), np.nan)
    tp_entry = np.full(len(df_bc), np.nan)
    tp_exit = np.full(len(df_bc), np.nan)
    tp_change = np.full(len(df_bc), np.nan)

    if is_chase.any():
        df_ch = df_bc[is_chase]
        idx_ch = df_ch.index

        tgt = df_ch["target"].astype(float)
        en_sc = df_ch["entry_score"].astype(float)
        ex_sc = df_ch["exit_score"].astype(float)
        en_br = df_ch["entry_balls_remaining"].astype(int)
        ex_br = df_ch["exit_balls_remaining"].astype(int)
        en_rr_val = df_ch["entry_team_rr"].astype(float)
        ex_rr_val = df_ch["exit_team_rr"].astype(float)

        # Runs required (cannot be negative)
        r_entry = np.maximum(0.0, tgt - en_sc)
        r_exit = np.maximum(0.0, tgt - ex_sc)

        # Required run rate: runs_required * 6 / balls_remaining
        rrr_en = np.where(r_entry <= 0, 0.0, np.where(en_br > 0, np.round(r_entry * 6.0 / en_br, 2), 0.0))
        rrr_ex = np.where(r_exit <= 0, 0.0, np.where(ex_br > 0, np.round(r_exit * 6.0 / ex_br, 2), 0.0))

        # RR Gap: current_rr - required_rr
        gap_en = np.round(en_rr_val - rrr_en, 2)
        gap_ex = np.round(ex_rr_val - rrr_ex, 2)

        # Required RR Change: RequiredRREntry - RequiredRRExit (Section 5: positive means required RR decreased!)
        rrr_chg = np.round(rrr_en - rrr_ex, 2)

        # RR Gap Change: RRGapExit - RRGapEntry (Section 5: positive means scoring rate moved closer to/beyond req rate)
        gap_chg = np.round(gap_ex - gap_en, 2)

        # Runs Required Reduction: RunsRequiredEntry - RunsRequiredExit (Section 6)
        r_reduc = np.round(r_entry - r_exit, 1)

        # Target Progress: Score / Target
        prog_en = np.where(tgt > 0, np.round(en_sc / tgt, 4), 0.0)
        prog_ex = np.where(tgt > 0, np.round(ex_sc / tgt, 4), 0.0)
        prog_chg = np.round(prog_ex - prog_en, 4)

        runs_req_entry[idx_ch] = r_entry
        runs_req_exit[idx_ch] = r_exit
        req_rr_entry[idx_ch] = rrr_en
        req_rr_exit[idx_ch] = rrr_ex
        req_rr_change[idx_ch] = rrr_chg
        rr_gap_en[idx_ch] = gap_en
        rr_gap_ex[idx_ch] = gap_ex
        rr_gap_chg[idx_ch] = gap_chg
        runs_req_reduction[idx_ch] = r_reduc
        tp_entry[idx_ch] = prog_en
        tp_exit[idx_ch] = prog_ex
        tp_change[idx_ch] = prog_chg

    # Assign chase variables (strictly NULL for 1st innings)
    df_bc["runs_required_entry"] = runs_req_entry
    df_bc["runs_required_exit"] = runs_req_exit
    df_bc["required_rr_entry"] = req_rr_entry
    df_bc["required_rr_exit"] = req_rr_exit
    df_bc["required_rr_change"] = req_rr_change
    df_bc["rr_gap_entry"] = rr_gap_en
    df_bc["rr_gap_exit"] = rr_gap_ex
    df_bc["rr_gap_change"] = rr_gap_chg
    df_bc["runs_required_reduction"] = runs_req_reduction
    df_bc["target_progress_entry"] = tp_entry
    df_bc["target_progress_exit"] = tp_exit
    df_bc["target_progress_change"] = tp_change

    # Backward-compatible chase aliases
    df_bc["target_score"] = df_bc["target"].where(is_chase, np.nan)
    df_bc["runs_required_at_entry"] = df_bc["runs_required_entry"]
    df_bc["runs_required_at_exit"] = df_bc["runs_required_exit"]
    df_bc["required_rr_at_entry"] = df_bc["required_rr_entry"]
    df_bc["required_rr_at_exit"] = df_bc["required_rr_exit"]
    df_bc["team_rr_at_entry"] = df_bc["entry_team_rr"].where(is_chase, np.nan)
    df_bc["team_rr_at_exit"] = df_bc["exit_team_rr"].where(is_chase, np.nan)
    df_bc["team_rr_minus_required_rr_change"] = df_bc["rr_gap_change"]

    # -------------------------------------------------------------
    # 4. Partnership Aggregations
    # -------------------------------------------------------------
    p_map: Dict[Tuple[Any, int, str], Dict[str, Any]] = {}

    for (m_id, inn_num, p1), group in df_part.groupby(["match_id", "innings_number", "batter_1"]):
        key = (m_id, inn_num, p1)
        if key not in p_map:
            p_map[key] = {"tot_runs": 0, "b_runs": 0, "partner_runs": 0, "balls": 0}
        p_map[key]["tot_runs"] += int(group["partnership_runs"].sum())
        p_map[key]["b_runs"] += int(group["batter_1_runs_in_partnership"].sum())
        p_map[key]["partner_runs"] += int(group["batter_2_runs_in_partnership"].sum())
        p_map[key]["balls"] += int(group["partnership_balls"].sum())

    for (m_id, inn_num, p2), group in df_part.groupby(["match_id", "innings_number", "batter_2"]):
        key = (m_id, inn_num, p2)
        if key not in p_map:
            p_map[key] = {"tot_runs": 0, "b_runs": 0, "partner_runs": 0, "balls": 0}
        p_map[key]["tot_runs"] += int(group["partnership_runs"].sum())
        p_map[key]["b_runs"] += int(group["batter_2_runs_in_partnership"].sum())
        p_map[key]["partner_runs"] += int(group["batter_1_runs_in_partnership"].sum())
        p_map[key]["balls"] += int(group["partnership_balls"].sum())

    tot_part_runs = []
    b_part_runs = []
    pr_runs_list = []
    part_durations = []

    for _, row in df_bc.iterrows():
        key = (row["match_id"], row["innings_number"], row["batter"])
        if key in p_map:
            p_info = p_map[key]
            p_runs = p_info["tot_runs"]
            b_runs = p_info["b_runs"]
            pr_runs = p_info["partner_runs"]
            p_balls = p_info["balls"]

            tot_part_runs.append(p_runs)
            b_part_runs.append(b_runs)
            pr_runs_list.append(pr_runs)
            part_durations.append(p_balls)
        else:
            tot_part_runs.append(row["actual_team_runs_change"])
            b_part_runs.append(row["runs"])
            pr_runs_list.append(max(0, row["actual_team_runs_change"] - row["runs"]))
            part_durations.append(row["balls"])

    df_bc["partnership_runs"] = tot_part_runs
    df_bc["batter_partnership_runs"] = b_part_runs
    df_bc["partner_runs"] = pr_runs_list
    df_bc["partner_partnership_runs"] = pr_runs_list  # alias
    df_bc["partnership_duration"] = part_durations
    df_bc["batter_partnership_share"] = np.where(
        df_bc["partnership_runs"] > 0,
        np.round(df_bc["batter_partnership_runs"] / df_bc["partnership_runs"], 3),
        0.0
    )
    df_bc["batter_share_of_partnership_runs"] = np.round(df_bc["batter_partnership_share"] * 100.0, 2)

    # -------------------------------------------------------------
    # 5. Batter Performance Metrics
    # -------------------------------------------------------------
    df_bc = df_bc.copy()
    df_bc["actual_runs"] = df_bc["runs"].fillna(0).astype(int)
    df_bc["balls_faced"] = df_bc["balls"].fillna(0).astype(int)
    df_bc["actual_sr"] = df_bc["strike_rate"].fillna(0.0).astype(float)
    df_bc["dot_balls"] = df_bc["dot_balls"].fillna(0).astype(int)
    df_bc["dot_ball_percentage"] = np.where(
        df_bc["balls_faced"] > 0,
        np.round(df_bc["dot_balls"] / df_bc["balls_faced"], 3),
        0.0
    )
    df_bc["fours"] = df_bc["fours"].fillna(0).astype(int)
    df_bc["sixes"] = df_bc["sixes"].fillna(0).astype(int)
    df_bc["boundary_runs"] = df_bc["boundary_runs"].fillna(df_bc["fours"] * 4 + df_bc["sixes"] * 6).astype(int)
    df_bc["opposition_team"] = df_bc["bowling_team"]

    return df_bc
