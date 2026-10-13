"""
Data loader and processing pipeline for IPL ball-by-ball Cricsheet JSON data.

Extracts structured datasets:
1. matches: match-level metadata and outcomes
2. innings: innings-level totals and context
3. deliveries: delivery-by-delivery events (legal & extras)
4. batter_innings: batter-level innings statistics
"""

import os
import sys
import json
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import pandas as pd

# Ensure UTF-8 output encoding on Windows console
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def parse_single_match(
    filepath: Path | str,
    match_dict: Optional[Dict[str, Any]] = None
) -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Parse a single Cricsheet IPL match JSON data structure.

    Args:
        filepath: Path to the JSON file (or identifier string).
        match_dict: Parsed JSON dict. If None, it will be loaded from filepath.

    Returns:
        Tuple containing:
            - match_row (dict)
            - innings_rows (list of dicts)
            - delivery_rows (list of dicts)
            - batter_innings_rows (list of dicts)
    """
    if match_dict is None:
        with open(filepath, "r", encoding="utf-8") as fp:
            match_dict = json.load(fp)

    path_obj = Path(filepath)
    match_id = path_obj.stem

    info = match_dict.get("info", {})
    season = str(info.get("season", ""))
    dates = info.get("dates", [])
    date_val = str(dates[0]) if dates else None
    venue = info.get("venue")
    city = info.get("city")  # None if missing (e.g. 51 IPL matches have no city in info)

    teams = info.get("teams", [])
    team1 = teams[0] if len(teams) > 0 else None
    team2 = teams[1] if len(teams) > 1 else None

    toss = info.get("toss", {})
    toss_winner = toss.get("winner")
    toss_decision = toss.get("decision")

    outcome = info.get("outcome", {})
    # For tied matches with super over (eliminator), outcome has 'eliminator'
    winner = outcome.get("winner") or outcome.get("eliminator")
    by_info = outcome.get("by", {})
    win_by_runs = by_info.get("runs")
    win_by_wickets = by_info.get("wickets")

    pom = info.get("player_of_match")
    if isinstance(pom, list):
        player_of_match = ", ".join(str(p) for p in pom)
    elif pom is not None:
        player_of_match = str(pom)
    else:
        player_of_match = None

    raw_innings = match_dict.get("innings", [])
    innings_count = len(raw_innings)

    match_row = {
        "match_id": match_id,
        "season": season,
        "date": date_val,
        "venue": venue,
        "city": city,
        "team1": team1,
        "team2": team2,
        "toss_winner": toss_winner,
        "toss_decision": toss_decision,
        "winner": winner,
        "win_by_runs": win_by_runs,
        "win_by_wickets": win_by_wickets,
        "player_of_match": player_of_match,
        "innings_count": innings_count,
    }

    innings_rows: List[Dict[str, Any]] = []
    delivery_rows: List[Dict[str, Any]] = []
    batter_innings_rows: List[Dict[str, Any]] = []

    for inn_idx, inn in enumerate(raw_innings):
        innings_number = inn_idx + 1
        batting_team = inn.get("team")
        bowling_team = team2 if batting_team == team1 else team1

        target_runs = inn.get("target", {}).get("runs") if "target" in inn else None
        is_chase = (innings_number % 2 == 0)

        inn_total_runs = 0
        inn_legal_balls = 0
        inn_wickets = 0

        seen_batters_order: List[str] = []
        batters_stat: Dict[str, Dict[str, int]] = {}
        dismissals_in_inn: Dict[str, str] = {}

        overs_data = inn.get("overs", [])
        for over_obj in overs_data:
            over_num = over_obj.get("over", 0)
            deliveries = over_obj.get("deliveries", [])
            for b_idx, deliv in enumerate(deliveries):
                ball_num = b_idx + 1
                batter = deliv.get("batter")
                non_striker = deliv.get("non_striker")
                bowler = deliv.get("bowler")

                runs_info = deliv.get("runs", {})
                b_runs = runs_info.get("batter", 0)
                e_runs = runs_info.get("extras", 0)
                tot_runs = runs_info.get("total", 0)

                extras_info = deliv.get("extras", {})
                extra_type = ", ".join(extras_info.keys()) if extras_info else None
                wides_cnt = extras_info.get("wides", 0)
                noballs_cnt = extras_info.get("noballs", 0)
                byes_cnt = extras_info.get("byes", 0)
                legbyes_cnt = extras_info.get("legbyes", 0)
                penalty_cnt = extras_info.get("penalty", 0)

                is_wide = "wides" in extras_info
                is_noball = "noballs" in extras_info
                is_legal = (not is_wide) and (not is_noball)

                inn_total_runs += tot_runs
                if is_legal:
                    inn_legal_balls += 1

                wickets_list = deliv.get("wickets", [])
                p_dismissed = None
                d_kind = None
                if wickets_list:
                    w0 = wickets_list[0]
                    p_dismissed = w0.get("player_out")
                    d_kind = w0.get("kind")
                    # In cricket rules, retired hurt does not count as a lost wicket for the team
                    if d_kind != "retired hurt":
                        inn_wickets += 1
                    if p_dismissed:
                        dismissals_in_inn[p_dismissed] = d_kind

                delivery_rows.append({
                    "match_id": match_id,
                    "season": season,
                    "innings_number": innings_number,
                    "over": over_num,
                    "ball": ball_num,
                    "batting_team": batting_team,
                    "bowling_team": bowling_team,
                    "batter": batter,
                    "non_striker": non_striker,
                    "bowler": bowler,
                    "batter_runs": b_runs,
                    "extras_runs": e_runs,
                    "total_runs": tot_runs,
                    "extra_type": extra_type,
                    "player_dismissed": p_dismissed,
                    "dismissal_kind": d_kind,
                    "is_wicket": bool(wickets_list),
                    "wides": wides_cnt,
                    "noballs": noballs_cnt,
                    "byes": byes_cnt,
                    "legbyes": legbyes_cnt,
                    "penalty": penalty_cnt,
                })

                # Track order of batters appearing at the crease
                for p in [batter, non_striker]:
                    if p and p not in seen_batters_order:
                        seen_batters_order.append(p)

                # Track batter stats
                if batter:
                    if batter not in batters_stat:
                        batters_stat[batter] = {
                            "runs": 0,
                            "balls_faced": 0,
                            "fours": 0,
                            "sixes": 0,
                            "dot_balls": 0,
                        }
                    batters_stat[batter]["runs"] += b_runs
                    # Wides do not count as a ball faced by the batter
                    if not is_wide:
                        batters_stat[batter]["balls_faced"] += 1
                        # Dot ball: ball faced where total runs scored on delivery is 0
                        if tot_runs == 0:
                            batters_stat[batter]["dot_balls"] += 1
                    if b_runs == 4:
                        batters_stat[batter]["fours"] += 1
                    elif b_runs == 6:
                        batters_stat[batter]["sixes"] += 1

        completed_overs = inn_legal_balls // 6
        rem_balls = inn_legal_balls % 6
        overs_completed = round(completed_overs + rem_balls / 10, 1)

        innings_rows.append({
            "match_id": match_id,
            "season": season,
            "innings_number": innings_number,
            "batting_team": batting_team,
            "bowling_team": bowling_team,
            "total_runs": inn_total_runs,
            "total_wickets": inn_wickets,
            "overs_completed": overs_completed,
            "target": target_runs,
            "is_chase": is_chase,
        })

        # Generate batter innings rows for all batters who came to the crease
        for pos, player in enumerate(seen_batters_order, 1):
            st = batters_stat.get(player, {
                "runs": 0,
                "balls_faced": 0,
                "fours": 0,
                "sixes": 0,
                "dot_balls": 0,
            })

            if player in dismissals_in_inn:
                d_k = dismissals_in_inn[player]
                if d_k == "retired hurt":
                    d_status = "retired hurt"
                else:
                    d_status = "out"
                d_kind = d_k
            else:
                d_status = "not out"
                d_kind = None

            batter_innings_rows.append({
                "match_id": match_id,
                "season": season,
                "innings_number": innings_number,
                "batting_team": batting_team,
                "bowling_team": bowling_team,
                "batter": player,
                "batting_position": pos,
                "runs": st["runs"],
                "balls_faced": st["balls_faced"],
                "fours": st["fours"],
                "sixes": st["sixes"],
                "dot_balls": st["dot_balls"],
                "dismissal_status": d_status,
                "dismissal_kind": d_kind,
                "team_runs": inn_total_runs,
                "team_wickets": inn_wickets,
                "team_overs": overs_completed,
                "team_balls": inn_legal_balls,
                "team_balls/overs": overs_completed,
            })

    return match_row, innings_rows, delivery_rows, batter_innings_rows


def load_and_process_matches(
    raw_dir: Path | str = "data/raw",
    processed_dir: Optional[Path | str] = "data/processed",
    save: bool = True
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, List[Tuple[str, str]]]:
    """
    Read all .json match files from raw_dir, process every match,
    and convert into structured DataFrames.

    Args:
        raw_dir: Directory containing raw Cricsheet JSON files.
        processed_dir: Directory to save processed CSVs (if save=True).
        save: If True, writes matches.csv, innings.csv, deliveries.csv, batter_innings.csv.

    Returns:
        Tuple: (matches_df, innings_df, deliveries_df, batter_innings_df, failed_files)
    """
    raw_path = Path(raw_dir)
    if not raw_path.exists():
        raise FileNotFoundError(f"Raw data directory does not exist: {raw_path}")

    json_files = sorted([f for f in raw_path.iterdir() if f.suffix == ".json"])
    logger.info(f"Found {len(json_files)} JSON files in {raw_path}")

    matches_list: List[Dict[str, Any]] = []
    innings_list: List[Dict[str, Any]] = []
    deliveries_list: List[Dict[str, Any]] = []
    batter_innings_list: List[Dict[str, Any]] = []
    failed_files: List[Tuple[str, str]] = []

    for file_path in json_files:
        try:
            m_row, inn_rows, deliv_rows, bat_rows = parse_single_match(file_path)
            matches_list.append(m_row)
            innings_list.extend(inn_rows)
            deliveries_list.extend(deliv_rows)
            batter_innings_list.extend(bat_rows)
        except Exception as exc:
            error_msg = f"{type(exc).__name__}: {str(exc)}"
            logger.error(f"Failed to process {file_path.name}: {error_msg}")
            failed_files.append((file_path.name, error_msg))

    logger.info(f"Successfully processed {len(matches_list)} matches.")
    if failed_files:
        logger.warning(f"Failed to process {len(failed_files)} files: {failed_files}")

    matches_df = pd.DataFrame(matches_list)
    innings_df = pd.DataFrame(innings_list)
    deliveries_df = pd.DataFrame(deliveries_list)
    batter_innings_df = pd.DataFrame(batter_innings_list)

    if save and processed_dir:
        out_path = Path(processed_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        matches_file = out_path / "matches.csv"
        innings_file = out_path / "innings.csv"
        deliveries_file = out_path / "deliveries.csv"
        batter_innings_file = out_path / "batter_innings.csv"

        matches_df.to_csv(matches_file, index=False, encoding="utf-8")
        innings_df.to_csv(innings_file, index=False, encoding="utf-8")
        deliveries_df.to_csv(deliveries_file, index=False, encoding="utf-8")
        batter_innings_df.to_csv(batter_innings_file, index=False, encoding="utf-8")

        logger.info(f"Saved matches to {matches_file} ({len(matches_df)} rows)")
        logger.info(f"Saved innings to {innings_file} ({len(innings_df)} rows)")
        logger.info(f"Saved deliveries to {deliveries_file} ({len(deliveries_df)} rows)")
        logger.info(f"Saved batter_innings to {batter_innings_file} ({len(batter_innings_df)} rows)")

    return matches_df, innings_df, deliveries_df, batter_innings_df, failed_files


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process raw IPL Cricsheet JSON files into structured datasets.")
    parser.add_argument("--raw-dir", type=str, default="data/raw", help="Path to raw JSON directory")
    parser.add_argument("--processed-dir", type=str, default="data/processed", help="Path to processed output directory")
    parser.add_argument("--no-save", action="store_true", help="Do not write CSV files to disk")

    args = parser.parse_args()
    matches_df, innings_df, deliveries_df, batter_innings_df, failed = load_and_process_matches(
        raw_dir=args.raw_dir,
        processed_dir=args.processed_dir,
        save=not args.no_save
    )

    print("\n--- DATA LOADING COMPLETE ---")
    print(f"Matches processed: {len(matches_df)}")
    print(f"Innings processed: {len(innings_df)}")
    print(f"Deliveries processed: {len(deliveries_df)}")
    print(f"Batter-innings processed: {len(batter_innings_df)}")
    if failed:
        print(f"WARNING: {len(failed)} files could not be processed:")
        for fn, err in failed:
            print(f"  {fn}: {err}")
    else:
        print("All JSON files processed successfully with 0 errors.")
