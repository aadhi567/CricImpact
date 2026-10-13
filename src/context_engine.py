"""
Phase 2 Context Engine Orchestrator.

Processes delivery data and match metadata to generate:
1. data/processed/match_state.csv (Ball-by-ball complete situation)
2. data/processed/partnerships.csv (Partnership-level context)
3. data/processed/batter_context.csv (Batter innings context)
"""

import sys
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

# Ensure repository root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import numpy as np

from src.innings_context import (
    legal_balls_to_overs,
    calculate_team_run_rate,
    calculate_batter_strike_rate,
    calculate_batter_run_rate,
    get_innings_phase,
    calculate_projected_score_simple,
)
from src.chase_context import calculate_runs_required, calculate_required_run_rate
from src.partnership import extract_innings_partnerships
from src.match_state import build_innings_match_state

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def process_context_engine(
    processed_dir: Path | str = "data/processed",
    save: bool = True
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Run Phase 2 Situation & Context Engine across all processed IPL matches.

    Args:
        processed_dir: Directory containing Phase 1 CSV files and target for Phase 2 CSVs.
        save: If True, saves match_state.csv, partnerships.csv, and batter_context.csv.

    Returns:
        tuple: (match_state_df, partnerships_df, batter_context_df)
    """
    p_path = Path(processed_dir)
    matches_file = p_path / "matches.csv"
    innings_file = p_path / "innings.csv"
    deliveries_file = p_path / "deliveries.csv"
    batter_innings_file = p_path / "batter_innings.csv"

    for f in [matches_file, innings_file, deliveries_file, batter_innings_file]:
        if not f.exists():
            raise FileNotFoundError(f"Missing required Phase 1 dataset: {f}")

    logger.info("Loading Phase 1 processed datasets...")
    matches_df = pd.read_csv(matches_file, low_memory=False)
    innings_df = pd.read_csv(innings_file, low_memory=False)
    deliveries_df = pd.read_csv(deliveries_file, low_memory=False)
    batter_innings_df = pd.read_csv(batter_innings_file, low_memory=False)

    logger.info(
        f"Loaded {len(matches_df)} matches, {len(innings_df)} innings, "
        f"{len(deliveries_df)} deliveries, {len(batter_innings_df)} batter-innings."
    )

    # Build lookup map for innings: (match_id, innings_number) -> innings row dict
    innings_map: Dict[Tuple[str, int], Dict[str, Any]] = {}
    for _, row in innings_df.iterrows():
        key = (str(row["match_id"]), int(row["innings_number"]))
        innings_map[key] = row.to_dict()

    # Pre-group deliveries by (match_id, innings_number) preserving sequence
    logger.info("Grouping deliveries by match and innings...")
    grouped_delivs: Dict[Tuple[str, int], List[Dict[str, Any]]] = {}
    for deliv_dict in deliveries_df.to_dict(orient="records"):
        m_id = str(deliv_dict["match_id"])
        inn_num = int(deliv_dict["innings_number"])
        key = (m_id, inn_num)
        if key not in grouped_delivs:
            grouped_delivs[key] = []
        grouped_delivs[key].append(deliv_dict)

    all_partnerships: List[Dict[str, Any]] = []
    all_match_states: List[Dict[str, Any]] = []
    # Map (match_id, innings_number) -> match_state records for batter context extraction
    inn_match_states_map: Dict[Tuple[str, int], List[Dict[str, Any]]] = {}
    # Map (match_id, innings_number) -> list of partnerships
    inn_partnerships_map: Dict[Tuple[str, int], List[Dict[str, Any]]] = {}

    logger.info("Generating match state and partnerships for all innings...")
    for key, delivs in grouped_delivs.items():
        m_id, inn_num = key
        inn_info = innings_map.get(key, {})
        batting_team = inn_info.get("batting_team", delivs[0].get("batting_team", ""))
        bowling_team = inn_info.get("bowling_team", delivs[0].get("bowling_team", ""))
        season = str(delivs[0].get("season", ""))

        target_val = inn_info.get("target")
        is_chase = bool(inn_info.get("is_chase", inn_num % 2 == 0))

        # Handle target derivation for super-over chases or missing targets in chase
        if is_chase and (pd.isna(target_val) or target_val is None):
            prev_inn_key = (m_id, inn_num - 1)
            if prev_inn_key in innings_map:
                prev_runs = innings_map[prev_inn_key].get("total_runs", 0)
                target_val = prev_runs + 1

        target_int = int(target_val) if (target_val is not None and not pd.isna(target_val)) else None

        # Scheduled overs: default 20.0 for T20, 1.0 for super overs (innings > 2)
        scheduled_overs = 1.0 if inn_num > 2 else 20.0

        # Extract partnerships
        partnerships, deliv_p_ids = extract_innings_partnerships(
            match_id=m_id,
            innings_number=inn_num,
            batting_team=batting_team,
            deliveries_list=delivs
        )
        all_partnerships.extend(partnerships)
        inn_partnerships_map[key] = partnerships

        # Build ball-by-ball match state
        m_states = build_innings_match_state(
            match_id=m_id,
            season=season,
            innings_number=inn_num,
            batting_team=batting_team,
            bowling_team=bowling_team,
            deliveries_list=delivs,
            target=target_int,
            scheduled_overs=scheduled_overs,
            format="T20",
            delivery_partnership_ids=deliv_p_ids
        )
        all_match_states.extend(m_states)
        inn_match_states_map[key] = m_states

    logger.info("Extracting batter context dataset for all batter innings...")
    batter_context_rows: List[Dict[str, Any]] = []

    for b_row in batter_innings_df.to_dict(orient="records"):
        m_id = str(b_row["match_id"])
        inn_num = int(b_row["innings_number"])
        player = str(b_row["batter"])
        key = (m_id, inn_num)

        season = str(b_row.get("season", ""))
        batting_team = str(b_row.get("batting_team", ""))
        bowling_team = str(b_row.get("bowling_team", ""))
        b_pos = int(b_row.get("batting_position", 0))
        runs = int(b_row.get("runs", 0))
        balls = int(b_row.get("balls_faced", 0))
        fours = int(b_row.get("fours", 0))
        sixes = int(b_row.get("sixes", 0))
        dot_balls = int(b_row.get("dot_balls", 0))
        d_status = str(b_row.get("dismissal_status", "not out"))
        d_kind = b_row.get("dismissal_kind")
        boundary_runs = fours * 4 + sixes * 6
        strike_rate = calculate_batter_strike_rate(runs, balls)
        run_rate = calculate_batter_run_rate(runs, balls)

        inn_info = innings_map.get(key, {})
        target_val = inn_info.get("target")
        is_chase = bool(inn_info.get("is_chase", inn_num % 2 == 0))
        if is_chase and (pd.isna(target_val) or target_val is None):
            prev_inn_key = (m_id, inn_num - 1)
            if prev_inn_key in innings_map:
                prev_runs = innings_map[prev_inn_key].get("total_runs", 0)
                target_val = prev_runs + 1
        target_int = int(target_val) if (target_val is not None and not pd.isna(target_val)) else None
        scheduled_overs = 1.0 if inn_num > 2 else 20.0

        m_states = inn_match_states_map.get(key, [])
        num_delivs = len(m_states)

        # ----------------------------------------------------
        # 1. ENTRY CONTEXT
        # Situation immediately BEFORE the batter's first ball faced
        # ----------------------------------------------------
        first_faced_idx: Optional[int] = None
        first_seen_idx: Optional[int] = None

        for idx, ms in enumerate(m_states):
            if ms["batter"] == player:
                if first_faced_idx is None:
                    first_faced_idx = idx
            if ms["batter"] == player or ms["non_striker"] == player:
                if first_seen_idx is None:
                    first_seen_idx = idx
            if first_faced_idx is not None and first_seen_idx is not None:
                break

        # If batter faced at least one delivery, entry point is first ball faced
        # If batter faced 0 balls, entry point is first appearance as non-striker
        entry_idx = first_faced_idx if first_faced_idx is not None else first_seen_idx

        if entry_idx is not None and entry_idx < num_delivs:
            entry_ms = m_states[entry_idx]
            entry_over = entry_ms["overs_before_delivery"]
            entry_score = entry_ms["runs_before_delivery"]
            entry_wickets = entry_ms["wickets_before_delivery"]
            entry_team_rr = entry_ms["team_rr_before_delivery"]
            entry_wickets_rem = 10 - entry_wickets
            entry_balls_rem = entry_ms["balls_remaining_before_delivery"]
            entry_phase = entry_ms["phase_before_delivery"]
            entry_batters_rem = entry_ms["batters_yet_to_bat"]
        else:
            # Fallback if no deliveries found (e.g. edge cases)
            entry_over = 0.0
            entry_score = 0
            entry_wickets = 0
            entry_team_rr = 0.0
            entry_wickets_rem = 10
            entry_balls_rem = int(scheduled_overs * 6)
            entry_phase = "POWERPLAY"
            entry_batters_rem = 9

        # ----------------------------------------------------
        # 2. DISMISSAL / END CONTEXT
        # ----------------------------------------------------
        dismissal_idx: Optional[int] = None
        if d_status == "out":
            # Search for the delivery where player was dismissed
            for idx, ms in enumerate(m_states):
                if ms["player_dismissed"] == player:
                    dismissal_idx = idx
                    break

        if dismissal_idx is not None:
            # Dismissed: state after the dismissal delivery represents fall of wicket
            dis_ms = m_states[dismissal_idx]
            dismissal_over = dis_ms["overs_completed"]
            dismissal_score = dis_ms["total_team_runs_so_far"]
            dismissal_wickets = dis_ms["wickets_lost_so_far"]
            dismissal_team_rr = dis_ms["current_team_rr"]
            dismissal_wickets_rem = dis_ms["wickets_remaining"]
            dismissal_balls_rem = dis_ms["balls_remaining_in_innings"]
            dismissal_phase = dis_ms["innings_phase"]

            # Explicit before vs after dismissal delivery states
            score_before_dismissal = dis_ms["runs_before_delivery"]
            score_after_dismissal = dis_ms["total_team_runs_so_far"]
            wickets_before_dismissal = dis_ms["wickets_before_delivery"]
            wickets_after_dismissal = dis_ms["wickets_lost_so_far"]
            rr_before_dismissal = dis_ms["team_rr_before_delivery"]
            rr_after_dismissal = dis_ms["current_team_rr"]
            proj_before_dis = calculate_projected_score_simple(rr_before_dismissal, scheduled_overs)
            proj_after_dis = calculate_projected_score_simple(rr_after_dismissal, scheduled_overs)

            # Post-dismissal scoring rates
            subsequent_delivs = m_states[dismissal_idx + 1:]
            legal_subsequent = [d for d in subsequent_delivs if d["is_legal"]]
            total_legal_sub = len(legal_subsequent)

            # Next 6 legal balls
            if total_legal_sub >= 6:
                # Find the slice containing up to the 6th legal delivery
                legal_seen = 0
                runs_6 = 0
                for d in subsequent_delivs:
                    runs_6 += d["total_runs"]
                    if d["is_legal"]:
                        legal_seen += 1
                    if legal_seen == 6:
                        break
                post_dis_rr_6 = round(runs_6 / (6 / 6.0), 2)
            else:
                post_dis_rr_6 = None

            # Next 12 legal balls
            if total_legal_sub >= 12:
                legal_seen = 0
                runs_12 = 0
                for d in subsequent_delivs:
                    runs_12 += d["total_runs"]
                    if d["is_legal"]:
                        legal_seen += 1
                    if legal_seen == 12:
                        break
                post_dis_rr_12 = round(runs_12 / (12 / 6.0), 2)
            else:
                post_dis_rr_12 = None

            # Remaining innings
            if total_legal_sub >= 1:
                runs_rem = sum(d["total_runs"] for d in subsequent_delivs)
                post_dis_rr_rem = round(runs_rem / (total_legal_sub / 6.0), 2)
            else:
                post_dis_rr_rem = None

        else:
            # Not out: End-of-innings state
            if m_states:
                last_ms = m_states[-1]
                dismissal_over = last_ms["overs_completed"]
                dismissal_score = last_ms["total_team_runs_so_far"]
                dismissal_wickets = last_ms["wickets_lost_so_far"]
                dismissal_team_rr = last_ms["current_team_rr"]
                dismissal_wickets_rem = last_ms["wickets_remaining"]
                dismissal_balls_rem = last_ms["balls_remaining_in_innings"]
                dismissal_phase = last_ms["innings_phase"]
            else:
                dismissal_over = entry_over
                dismissal_score = entry_score
                dismissal_wickets = entry_wickets
                dismissal_team_rr = entry_team_rr
                dismissal_wickets_rem = entry_wickets_rem
                dismissal_balls_rem = entry_balls_rem
                dismissal_phase = entry_phase

            score_before_dismissal = None
            score_after_dismissal = None
            wickets_before_dismissal = None
            wickets_after_dismissal = None
            rr_before_dismissal = None
            rr_after_dismissal = None
            proj_before_dis = None
            proj_after_dis = None
            post_dis_rr_6 = None
            post_dis_rr_12 = None
            post_dis_rr_rem = None

        # ----------------------------------------------------
        # 3. CHASE CONTEXT
        # ----------------------------------------------------
        if is_chase and target_int is not None:
            runs_req_entry = calculate_runs_required(target_int, entry_score)
            runs_req_dis = calculate_runs_required(target_int, dismissal_score)
            rrr_entry = calculate_required_run_rate(runs_req_entry, entry_balls_rem)
            rrr_dis = calculate_required_run_rate(runs_req_dis, dismissal_balls_rem)
            balls_rem_entry = entry_balls_rem
            balls_rem_dis = dismissal_balls_rem
        else:
            runs_req_entry = None
            runs_req_dis = None
            rrr_entry = None
            rrr_dis = None
            balls_rem_entry = None
            balls_rem_dis = None

        # ----------------------------------------------------
        # 4. FIRST-INNINGS CONTEXT
        # ----------------------------------------------------
        if not is_chase:
            proj_entry = calculate_projected_score_simple(entry_team_rr, scheduled_overs)
            proj_dis = calculate_projected_score_simple(dismissal_team_rr, scheduled_overs)
        else:
            proj_entry = None
            proj_dis = None

        # ----------------------------------------------------
        # 5. PARTNERSHIP CONTEXT FOR THIS BATTER
        # Aggregated across all partnerships batter was involved in
        # ----------------------------------------------------
        ps_in_inn = inn_partnerships_map.get(key, [])
        bat_partnerships = [
            p for p in ps_in_inn
            if p["batter_1"] == player or p["batter_2"] == player
        ]
        p_runs_total = sum(p["partnership_runs"] for p in bat_partnerships)
        p_balls_total = sum(p["partnership_balls"] for p in bat_partnerships)
        p_rr_total = calculate_team_run_rate(p_runs_total, p_balls_total)
        p_share = round((runs / p_runs_total) * 100.0, 2) if p_runs_total > 0 else 0.0

        batter_context_rows.append({
            # Identification
            "match_id": m_id,
            "season": season,
            "innings_number": inn_num,
            "batting_team": batting_team,
            "bowling_team": bowling_team,
            "batter": player,
            # Basic Performance
            "runs": runs,
            "balls": balls,
            "strike_rate": strike_rate,
            "run_rate": run_rate,
            "fours": fours,
            "sixes": sixes,
            "dot_balls": dot_balls,
            "boundary_runs": boundary_runs,
            # Entry Context
            "entry_over": entry_over,
            "entry_score": entry_score,
            "entry_wickets": entry_wickets,
            "entry_team_rr": entry_team_rr,
            "entry_wickets_remaining": entry_wickets_rem,
            "entry_balls_remaining": entry_balls_rem,
            "entry_innings_phase": entry_phase,
            "batting_position": b_pos,
            "entry_batters_remaining": entry_batters_rem,
            # Dismissal / End Context
            "dismissal_over": dismissal_over,
            "dismissal_score": dismissal_score,
            "dismissal_wickets": dismissal_wickets,
            "dismissal_team_rr": dismissal_team_rr,
            "dismissal_wickets_remaining": dismissal_wickets_rem,
            "dismissal_balls_remaining": dismissal_balls_rem,
            "dismissal_innings_phase": dismissal_phase,
            "dismissal_status": d_status,
            "dismissal_kind": d_kind,
            # Chase Context
            "target": target_int,
            "is_chase": is_chase,
            "required_rr_at_entry": rrr_entry,
            "required_rr_at_dismissal": rrr_dis,
            "runs_required_at_entry": runs_req_entry,
            "runs_required_at_dismissal": runs_req_dis,
            "balls_remaining_at_entry": balls_rem_entry,
            "balls_remaining_at_dismissal": balls_rem_dis,
            # First-Innings Context
            "projected_score_simple_at_entry": proj_entry,
            "projected_score_simple_at_dismissal": proj_dis,
            # Partnership
            "partnership_runs": p_runs_total,
            "partnership_balls": p_balls_total,
            "partnership_rr": p_rr_total,
            "player_partnership_run_share": p_share,
            # Post-Dismissal Detailed States
            "score_before_dismissal": score_before_dismissal,
            "score_after_dismissal": score_after_dismissal,
            "wickets_before_dismissal": wickets_before_dismissal,
            "wickets_after_dismissal": wickets_after_dismissal,
            "rr_before_dismissal": rr_before_dismissal,
            "rr_after_dismissal": rr_after_dismissal,
            "projected_score_before_dismissal": proj_before_dis,
            "projected_score_after_dismissal": proj_after_dis,
            "post_dismissal_rr_6balls": post_dis_rr_6,
            "post_dismissal_rr_12balls": post_dis_rr_12,
            "post_dismissal_rr_remaining": post_dis_rr_rem,
        })

    match_state_df = pd.DataFrame(all_match_states)
    partnerships_df = pd.DataFrame(all_partnerships)
    batter_context_df = pd.DataFrame(batter_context_rows)

    if save:
        match_state_file = p_path / "match_state.csv"
        partnerships_file = p_path / "partnerships.csv"
        batter_context_file = p_path / "batter_context.csv"

        logger.info(f"Saving match state dataset to {match_state_file} ({len(match_state_df):,} rows)...")
        match_state_df.to_csv(match_state_file, index=False, encoding="utf-8")

        logger.info(f"Saving partnerships dataset to {partnerships_file} ({len(partnerships_df):,} rows)...")
        partnerships_df.to_csv(partnerships_file, index=False, encoding="utf-8")

        logger.info(f"Saving batter context dataset to {batter_context_file} ({len(batter_context_df):,} rows)...")
        batter_context_df.to_csv(batter_context_file, index=False, encoding="utf-8")

    return match_state_df, partnerships_df, batter_context_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Phase 2 Situation & Context Engine.")
    parser.add_argument("--processed-dir", type=str, default="data/processed", help="Path to processed datasets directory")
    parser.add_argument("--no-save", action="store_true", help="Do not save CSVs to disk")

    args = parser.parse_args()
    ms_df, p_df, bc_df = process_context_engine(
        processed_dir=args.processed_dir,
        save=not args.no_save
    )

    print("\n" + "=" * 60)
    print("PHASE 2 CONTEXT ENGINE PROCESSING COMPLETE")
    print(f"Match State deliveries: {len(ms_df):,}")
    print(f"Partnerships tracked:    {len(p_df):,}")
    print(f"Batter Context records:  {len(bc_df):,}")
    print("=" * 60)
