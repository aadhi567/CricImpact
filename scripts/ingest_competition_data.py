"""
Competition Data Ingestion Pipeline.
Supports Men's International T20Is (2022+) and Syed Mushtaq Ali Trophy (SMAT 2022+).

Invariants:
1. Strict match format restriction: T20 ONLY (rejects Tests, ODIs, FC, List A).
2. Strict gender filter: Men's cricket ONLY (info.gender == 'male').
3. Strict timeframe: 2022 onwards (min_date >= 2022-01-01).
4. Zero modification to existing IPL datasets (data/raw/ and root data/processed/ remain frozen).
5. Output partitioning: isolated directories data/processed/{competition}/.
6. Strict Did-Not-Bat (DNB) rule: 0-batting appearance player-seasons have NaN score and share.
7. Model invariance: uses unchanged compute_production_contribution from src/contribution_framework.py.
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import pandas as pd
import numpy as np

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.contribution_framework import compute_production_contribution
from src.season_aggregation import (
    is_negligible_opportunity,
    build_season_aggregations,
)

REGISTRY_PATH = Path("data/processed/processed_matches_registry.json")
WORLD_CUP_BASELINE_DIR = Path("data/backups/world_cup_baseline")

APPROVED_INTERNATIONAL_TEAMS = {
    "India", "Australia", "South Africa", "New Zealand", "Bangladesh",
    "England", "Pakistan", "Afghanistan", "Sri Lanka", "Zimbabwe",
    "West Indies", "Ireland", "Scotland", "United States of America"
}

TEAM_ALIASES = {
    "USA": "United States of America",
    "United States": "United States of America",
    "U.S.A.": "United States of America",
}

def normalize_team(t: Optional[str]) -> Optional[str]:
    if not t:
        return t
    t_clean = str(t).strip()
    return TEAM_ALIASES.get(t_clean, t_clean)


def update_registry(match_records: List[Dict[str, Any]], competition: str):
    """Updates the processed matches registry for idempotent tracking."""
    registry = {}
    if REGISTRY_PATH.exists():
        try:
            with open(REGISTRY_PATH, "r", encoding="utf-8") as fp:
                registry = json.load(fp)
        except Exception:
            registry = {}

    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    for m in match_records:
        mid_str = str(m["match_id"])
        registry[mid_str] = {
            "competition": competition.upper(),
            "format": "T20",
            "processed_at": now_iso,
            "season": str(m.get("season", "")),
            "date": str(m.get("date", "")),
            "teams": [m.get("team1"), m.get("team2")],
            "winner": m.get("winner"),
        }

    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REGISTRY_PATH, "w", encoding="utf-8") as fp:
        json.dump(registry, fp, indent=2, default=str)


def parse_cricsheet_match(
    filepath: Path,
    match_dict: Dict[str, Any]
) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Parses a single Cricsheet match JSON into:
    - match_row
    - roster_rows (all 11 players for both teams)
    - batter_contribution_rows (all active batting appearances with production scores)
    """
    match_id = filepath.stem
    info = match_dict.get("info", {})

    # Strict Validation: Male T20 only
    if info.get("gender") != "male":
        return None, [], []
    if str(info.get("match_type", "")).upper() != "T20":
        return None, [], []

    season = str(info.get("season", "")).strip()
    dates = info.get("dates", [])
    date_val = str(dates[0]) if dates else None
    venue = info.get("venue")
    city = info.get("city")
    teams = [normalize_team(t) for t in info.get("teams", [])]
    team1 = teams[0] if len(teams) > 0 else None
    team2 = teams[1] if len(teams) > 1 else None

    toss = info.get("toss", {})
    toss_winner = normalize_team(toss.get("winner"))
    toss_decision = toss.get("decision")

    outcome = info.get("outcome", {})
    winner = outcome.get("winner") or outcome.get("eliminator")
    if winner:
        winner = normalize_team(winner)
    by_info = outcome.get("by", {})
    win_by_runs = by_info.get("runs")
    win_by_wickets = by_info.get("wickets")
    pom = info.get("player_of_match")
    player_of_match = ", ".join(str(p) for p in pom) if isinstance(pom, list) else (str(pom) if pom else None)

    raw_innings = match_dict.get("innings", [])
    event_obj = info.get("event")
    event_name = ""
    stage = ""
    match_number = ""
    if isinstance(event_obj, dict):
        event_name = str(event_obj.get("name", "")).strip()
        stage = str(event_obj.get("stage", "")).strip()
        match_number = str(event_obj.get("match_number", "")).strip()
    elif isinstance(event_obj, str):
        event_name = event_obj.strip()

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
        "innings_count": len(raw_innings),
        "event_name": event_name,
        "stage": stage,
        "match_number": match_number,
    }

    # Extract Playing XI rosters
    roster_rows = []
    players_dict = info.get("players", {})
    for t_name, p_list in players_dict.items():
        norm_t_name = normalize_team(t_name)
        for p in p_list:
            roster_rows.append({
                "match_id": match_id,
                "season": season,
                "team": norm_t_name,
                "player": p,
            })

    # Parse deliveries and batter innings
    batter_rows = []
    first_innings_total = 0

    for inn_idx, inn in enumerate(raw_innings[:2]):  # Innings 1 and 2 only (exclude super overs)
        innings_num = inn_idx + 1
        batting_team = normalize_team(inn.get("team"))
        bowling_team = team2 if batting_team == team1 else team1
        target_runs = inn.get("target", {}).get("runs") if "target" in inn else None
        if innings_num == 2 and (target_runs is None or target_runs == 0):
            target_runs = first_innings_total + 1

        legal_balls = 0
        total_runs = 0
        wickets_down = 0

        batters_stat: Dict[str, Dict[str, int]] = {}
        batter_entry: Dict[str, Dict[str, Any]] = {}
        batter_exit: Dict[str, Dict[str, Any]] = {}
        seen_order: List[str] = []

        overs_data = inn.get("overs", [])
        for over_obj in overs_data:
            over_num = over_obj.get("over", 0)
            deliveries = over_obj.get("deliveries", [])
            for b_idx, deliv in enumerate(deliveries):
                b_num = b_idx + 1
                batter = deliv.get("batter")
                non_striker = deliv.get("non_striker")

                runs_info = deliv.get("runs", {})
                b_runs = runs_info.get("batter", 0)
                tot_runs = runs_info.get("total", 0)
                extras_info = deliv.get("extras", {})
                is_wide = "wides" in extras_info
                is_noball = "noballs" in extras_info
                is_legal = (not is_wide) and (not is_noball)

                over_decimal = round(over_num + (b_num - 1) / 10.0, 1)
                for p in [batter, non_striker]:
                    if p and p not in batter_entry:
                        seen_order.append(p)
                        batter_entry[p] = {
                            "over": over_decimal,
                            "balls_bowled": legal_balls,
                            "team_score": total_runs,
                            "team_rr": round(total_runs / (legal_balls / 6.0), 2) if legal_balls >= 6 else (total_runs if legal_balls > 0 else 0.0),
                            "wickets_down": wickets_down,
                            "balls_rem": max(0, 120 - legal_balls),
                            "wickets_rem": max(0, 10 - wickets_down),
                        }

                if batter not in batters_stat:
                    batters_stat[batter] = {
                        "runs": 0, "balls": 0, "fours": 0, "sixes": 0, "dot_balls": 0,
                    }
                batters_stat[batter]["runs"] += b_runs
                if not is_wide:
                    batters_stat[batter]["balls"] += 1
                    if tot_runs == 0:
                        batters_stat[batter]["dot_balls"] += 1
                if b_runs == 4:
                    batters_stat[batter]["fours"] += 1
                elif b_runs == 6:
                    batters_stat[batter]["sixes"] += 1

                total_runs += tot_runs
                if is_legal:
                    legal_balls += 1

                wickets_list = deliv.get("wickets", [])
                if wickets_list:
                    for w in wickets_list:
                        p_out = w.get("player_out")
                        kind = w.get("kind")
                        if kind != "retired hurt":
                            wickets_down += 1
                        if p_out:
                            exit_dec = round(over_num + b_num / 10.0, 1)
                            batter_exit[p_out] = {
                                "over": exit_dec,
                                "balls_bowled": legal_balls,
                                "team_score": total_runs,
                                "team_rr": round(total_runs / (legal_balls / 6.0), 2) if legal_balls >= 6 else total_runs,
                                "wickets_down": wickets_down,
                                "balls_rem": max(0, 120 - legal_balls),
                                "wickets_rem": max(0, 10 - wickets_down),
                                "dismissal_status": "retired hurt" if kind == "retired hurt" else "out",
                                "dismissal_kind": kind,
                            }

        end_over_dec = round((legal_balls // 6) + (legal_balls % 6) / 10.0, 1)
        for p in seen_order:
            if p not in batter_exit:
                batter_exit[p] = {
                    "over": end_over_dec,
                    "balls_bowled": legal_balls,
                    "team_score": total_runs,
                    "team_rr": round(total_runs / (legal_balls / 6.0), 2) if legal_balls >= 6 else total_runs,
                    "wickets_down": wickets_down,
                    "balls_rem": max(0, 120 - legal_balls),
                    "wickets_rem": max(0, 10 - wickets_down),
                    "dismissal_status": "not out",
                    "dismissal_kind": None,
                }

        won_m = (winner == batting_team)
        margin = win_by_runs if win_by_runs else (win_by_wickets if win_by_wickets else 10.0)
        m_type = "runs" if win_by_runs else ("wickets" if win_by_wickets else "runs")

        for pos, player in enumerate(seen_order, 1):
            st = batters_stat.get(player, {"runs": 0, "balls": 0, "fours": 0, "sixes": 0, "dot_balls": 0})
            ent = batter_entry.get(player, {"over": 0.0, "balls_bowled": 0, "team_score": 0, "team_rr": 7.5, "wickets_down": 0, "balls_rem": 120, "wickets_rem": 10})
            ex = batter_exit.get(player, {"over": 20.0, "balls_bowled": legal_balls, "team_score": total_runs, "team_rr": 7.5, "wickets_down": wickets_down, "balls_rem": 0, "wickets_rem": 5, "dismissal_status": "not out", "dismissal_kind": None})

            b_runs = st["runs"]
            b_balls = st["balls"]
            sr = round((b_runs / b_balls) * 100.0, 2) if b_balls > 0 else 0.0
            exp_runs = round(b_balls * 1.25, 1)
            exp_sr = 125.0
            run_dev = round(b_runs - exp_runs, 1)
            sr_dev = round(sr - exp_sr, 1)

            entry_ov = ent["over"]
            exit_ov = ex["over"]
            stay_balls = max(b_balls, ex["balls_bowled"] - ent["balls_bowled"])
            overs_spent = max(0.2, round(stay_balls / 6.0, 2))
            runs_added = max(b_runs, ex["team_score"] - ent["team_score"])
            w_rr = round(runs_added / overs_spent, 2) if overs_spent > 0 else 0.0

            b_runs_tot = st["fours"] * 4 + st["sixes"] * 6
            bnd_pct = round((b_runs_tot / b_runs) * 100.0, 2) if b_runs > 0 else 0.0
            dot_pct = round((st["dot_balls"] / b_balls) * 100.0, 2) if b_balls > 0 else 0.0

            b_row = {
                "match_id": match_id,
                "season": season,
                "innings": innings_num,
                "team": batting_team,
                "opponent": bowling_team,
                "player": player,
                "batting_position": pos,
                "entry_ball": ent["balls_bowled"],
                "exit_ball": ex["balls_bowled"],
                "entry_over": entry_ov,
                "exit_over": exit_ov,
                "dismissal_status": ex["dismissal_status"],
                "dismissal_kind": ex["dismissal_kind"],
                "actual_runs": b_runs,
                "expected_runs": exp_runs,
                "run_deviation": run_dev,
                "run_performance_ratio": round(b_runs / exp_runs, 3) if exp_runs > 0 else np.nan,
                "actual_sr": sr,
                "expected_sr": exp_sr,
                "sr_deviation": sr_dev,
                "sr_performance_ratio": round(sr / exp_sr, 3) if exp_sr > 0 else np.nan,
                "balls_faced": b_balls,
                "runs_per_ball": round(b_runs / b_balls, 3) if b_balls > 0 else 0.0,
                "opportunity_usage": round(b_balls / ent["balls_rem"], 4) if ent["balls_rem"] > 0 else 0.0,
                "fours": st["fours"],
                "sixes": st["sixes"],
                "boundary_runs": b_runs_tot,
                "boundary_percentage": bnd_pct,
                "boundary_runs_per_ball": round(b_runs_tot / b_balls, 3) if b_balls > 0 else 0.0,
                "dot_balls": st["dot_balls"],
                "dot_ball_percentage": dot_pct,
                "team_score_entry": ent["team_score"],
                "team_score_exit": ex["team_score"],
                "team_rr_entry": ent["team_rr"],
                "team_rr_exit": ex["team_rr"],
                "team_rr_change": round(ex["team_rr"] - ent["team_rr"], 2),
                "team_runs_added": runs_added,
                "overs_spent": overs_spent,
                "window_team_rr": w_rr,
                "wickets_remaining_entry": ent["wickets_rem"],
                "wickets_remaining_exit": ex["wickets_rem"],
                "wickets_lost_during_stay": max(0, ent["wickets_rem"] - ex["wickets_rem"]),
                "balls_remaining_entry": ent["balls_rem"],
                "balls_remaining_exit": ex["balls_rem"],
                "expected_final_entry": None,
                "expected_final_exit": None,
                "expected_final_change": None,
                "entry_score_deviation": None,
                "exit_score_deviation": None,
                "trajectory_deviation_change": None,
                "target": float(target_runs) if (innings_num == 2 and target_runs) else 0.0,
                "runs_required_entry": max(0, target_runs - ent["team_score"]) if (innings_num == 2 and target_runs) else 0,
                "runs_required_exit": max(0, target_runs - ex["team_score"]) if (innings_num == 2 and target_runs) else 0,
                "wicket_resource_change": ex["wickets_rem"] - ent["wickets_rem"],
                "overs_remaining_entry": round(ent["balls_rem"] / 6.0, 2),
                "overs_remaining_exit": round(ex["balls_rem"] / 6.0, 2),
                "partnership_runs": runs_added,
                "batter_partnership_runs": b_runs,
                "partner_runs": max(0, runs_added - b_runs),
                "batter_partnership_share": round(b_runs / runs_added, 3) if runs_added > 0 else 0.0,
                "partnership_duration": stay_balls,
                "post_exit_runs": max(0, total_runs - ex["team_score"]),
                "post_exit_overs": round(ex["balls_rem"] / 6.0, 2),
                "post_exit_rr": round((total_runs - ex["team_score"]) / max(0.1, ex["balls_rem"] / 6.0), 2) if ex["balls_rem"] > 0 else 0.0,
                "post_exit_wickets_lost": max(0, (10 - wickets_down) - ex["wickets_rem"]),
                "post_exit_rr_change": 0.0,
                "final_team_score": total_runs,
                "won_match": won_m,
                "winning_margin": margin,
                "margin_type": m_type,
                "target_reached": (total_runs >= target_runs) if (innings_num == 2 and target_runs) else None,
            }

            if innings_num == 2 and target_runs:
                req_entry = max(1.0, target_runs - ent["team_score"])
                req_exit = max(0.0, target_runs - ex["team_score"])
                rrr_in = round(req_entry / (ent["balls_rem"] / 6.0), 2) if ent["balls_rem"] > 0 else 9.0
                rrr_out = round(req_exit / (ex["balls_rem"] / 6.0), 2) if ex["balls_rem"] > 0 else (0.0 if req_exit == 0 else 36.0)
                b_row["required_rr_entry"] = rrr_in
                b_row["required_rr_exit"] = rrr_out
                b_row["required_rr_change"] = round(rrr_in - rrr_out, 2)
                b_row["rr_gap_entry"] = round(rrr_in - ent["team_rr"], 2)
                b_row["rr_gap_exit"] = round(rrr_out - ex["team_rr"], 2)
                b_row["rr_gap_change"] = b_row["required_rr_change"]
                b_row["chase_pressure_relief_rr"] = b_row["required_rr_change"]
                b_row["target_progress_entry"] = round(ent["team_score"] / target_runs, 3)
                b_row["target_progress_exit"] = round(ex["team_score"] / target_runs, 3)
                b_row["target_progress_change"] = round(b_row["target_progress_exit"] - b_row["target_progress_entry"], 3)
                b_row["runs_required_reduction"] = runs_added
            else:
                b_row["required_rr_entry"] = 0.0
                b_row["required_rr_exit"] = 0.0
                b_row["required_rr_change"] = 0.0
                b_row["rr_gap_entry"] = 0.0
                b_row["rr_gap_exit"] = 0.0
                b_row["rr_gap_change"] = 0.0
                b_row["target_progress_entry"] = 0.0
                b_row["target_progress_exit"] = 0.0
                b_row["target_progress_change"] = 0.0
                b_row["runs_required_reduction"] = 0

            # Production model scoring
            model_res = compute_production_contribution(b_row)
            b_row["contribution_score"] = model_res["contribution_score"]
            b_row["raw_contribution"] = model_res["raw_contribution"]
            b_row["score_context"] = model_res["pillar1_context_score"]
            b_row["score_perf"] = model_res["pillar2_perf_score"]
            b_row["score_state"] = model_res["pillar3_state_score"]
            b_row["score_cf"] = 50.0
            b_row["adjusted_p2"] = model_res["adjusted_p2"]
            b_row["adjusted_p3"] = model_res["adjusted_p3"]
            b_row["leverage"] = model_res["leverage"]
            b_row["c_wkt"] = model_res["c_wkt"]
            b_row["c_chase"] = model_res["c_chase"]
            b_row["c_open"] = model_res["c_open"]
            b_row["c_eff"] = model_res["c_eff"]
            b_row["context_zone"] = model_res["context_zone"]
            batter_rows.append(b_row)

        if innings_num == 1:
            first_innings_total = total_runs

    return match_row, roster_rows, batter_rows


def ingest_competition(
    competition: str,
    raw_dir: Path,
    out_dir: Path,
    min_date: str = "2022-01-01",
    max_matches: Optional[int] = None,
):
    """Ingests raw JSON files, processes contributions, and generates competition artifacts."""
    print(f"\n=======================================================")
    print(f"Starting Ingestion for Competition: {competition.upper()}")
    print(f"Source Directory: {raw_dir}")
    print(f"Output Directory: {out_dir}")
    print(f"Earliest Date: {min_date}")
    print(f"=======================================================")

    t0 = time.time()
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load baseline World Cup records if ingesting t20i
    df_wc_matches = pd.DataFrame()
    df_wc_rosters = pd.DataFrame()
    df_wc_contrib = pd.DataFrame()
    wc_baseline_ids = set()

    if competition == "t20i" and WORLD_CUP_BASELINE_DIR.exists():
        wc_m_path = WORLD_CUP_BASELINE_DIR / "world_cup_matches.csv"
        wc_r_path = WORLD_CUP_BASELINE_DIR / "world_cup_match_rosters.csv"
        wc_c_path = WORLD_CUP_BASELINE_DIR / "world_cup_batter_match_contributions.csv"
        if wc_m_path.exists() and wc_r_path.exists() and wc_c_path.exists():
            df_wc_matches = pd.read_csv(wc_m_path, dtype={"match_id": str, "season": str})
            df_wc_rosters = pd.read_csv(wc_r_path, dtype={"match_id": str, "season": str})
            df_wc_contrib = pd.read_csv(wc_c_path, dtype={"match_id": str, "season": str}, low_memory=False)
            wc_baseline_ids = set(df_wc_matches["match_id"].unique())
            print(f"Loaded {len(df_wc_matches)} World Cup baseline matches (preserved read-only from snapshot).")

    json_files = sorted(list(raw_dir.glob("*.json")))
    print(f"Discovered {len(json_files)} total raw JSON files in {raw_dir}")

    matches_list = []
    rosters_list = []
    batters_list = []
    skipped_count = 0

    for idx, fpath in enumerate(json_files):
        # If World Cup baseline match, skip raw parse because baseline snapshot is used directly
        if competition == "t20i" and fpath.stem in wc_baseline_ids:
            continue

        try:
            with open(fpath, "r", encoding="utf-8") as fp:
                match_dict = json.load(fp)

            info = match_dict.get("info", {})
            # Filter gender
            if info.get("gender") != "male":
                skipped_count += 1
                continue
            # Filter match format
            if str(info.get("match_type", "")).upper() != "T20":
                skipped_count += 1
                continue
            # Filter date
            dates = info.get("dates", [])
            if not dates or str(dates[0]) < min_date:
                skipped_count += 1
                continue

            # Team Scope Filter for International T20Is (Phase 2):
            if competition == "t20i":
                raw_teams = [normalize_team(t) for t in info.get("teams", [])]
                if not any(t in APPROVED_INTERNATIONAL_TEAMS for t in raw_teams):
                    skipped_count += 1
                    continue

            m_row, r_rows, b_rows = parse_cricsheet_match(fpath, match_dict)
            if m_row is None:
                skipped_count += 1
                continue

            matches_list.append(m_row)
            rosters_list.extend(r_rows)
            batters_list.extend(b_rows)

            if max_matches and len(matches_list) >= max_matches:
                print(f"Reached max matches limit ({max_matches}). Stopping scan.")
                break

            if len(matches_list) % 250 == 0:
                print(f"  Processed {len(matches_list)} matches ({len(batters_list)} batting innings)...")

        except Exception as e:
            print(f"Warning: Failed processing {fpath.name}: {e}")
            skipped_count += 1

    t_parse = time.time()
    print(f"\nParsing complete in {t_parse - t0:.2f}s:")
    print(f"  Total Valid Matches: {len(matches_list):,}")
    print(f"  Total Roster Entries: {len(rosters_list):,}")
    print(f"  Total Batting Innings: {len(batters_list):,}")
    print(f"  Skipped Files: {skipped_count:,}")

    df_new_matches = pd.DataFrame(matches_list) if matches_list else pd.DataFrame()
    df_new_rosters = pd.DataFrame(rosters_list) if rosters_list else pd.DataFrame()
    df_new_batters = pd.DataFrame(batters_list) if batters_list else pd.DataFrame()

    if competition == "t20i" and not df_wc_matches.empty:
        df_matches = pd.concat([df_wc_matches, df_new_matches], ignore_index=True)
        df_rosters = pd.concat([df_wc_rosters, df_new_rosters], ignore_index=True)
        df_batters = pd.concat([df_wc_contrib, df_new_batters], ignore_index=True)
    else:
        df_matches = df_new_matches
        df_rosters = df_new_rosters
        df_batters = df_new_batters

    if df_matches.empty:
        print(f"ERROR: No valid matches found for {competition}. Aborting.")
        return

    # Deduplicate matches
    df_matches = df_matches.drop_duplicates(subset=["match_id"]).sort_values(by=["date", "match_id"], ascending=[False, False]).reset_index(drop=True)
    df_rosters = df_rosters.sort_values(by=["match_id", "team", "player"]).reset_index(drop=True)
    df_batters = df_batters.sort_values(by=["match_id", "innings", "player"]).reset_index(drop=True)

    # Save partitioned CSVs
    matches_csv = out_dir / "matches.csv"
    rosters_csv = out_dir / "match_rosters.csv"
    batters_csv = out_dir / "batter_match_contributions.csv"
    season_metrics_csv = out_dir / "phase6_season_metrics.csv"

    print("\nSaving raw extracted datasets...")
    df_matches.to_csv(matches_csv, index=False, encoding="utf-8")
    df_rosters.to_csv(rosters_csv, index=False, encoding="utf-8")
    df_batters.to_csv(batters_csv, index=False, encoding="utf-8")
    print(f"  Saved {matches_csv} ({len(df_matches)} rows)")
    print(f"  Saved {rosters_csv} ({len(df_rosters)} rows)")
    print(f"  Saved {batters_csv} ({len(df_batters)} rows)")

    # Generate Season Aggregations
    print("\nComputing comprehensive season aggregations (View A & View B)...")
    t_season = time.time()
    df_season = build_season_aggregations(df_batters, df_rosters=df_rosters)
    df_season.to_csv(season_metrics_csv, index=False, encoding="utf-8")
    print(f"  Saved {season_metrics_csv} ({len(df_season)} player-seasons in {time.time() - t_season:.2f}s)")

    # Data Quality & Integrity Audits
    print("\nRunning Data Integrity Verification:")
    # 1. World Cup Baseline Isolation
    if competition == "t20i" and not df_wc_matches.empty:
        wc_check_m = df_matches[df_matches["match_id"].isin(wc_baseline_ids)]
        wc_check_r = df_rosters[df_rosters["match_id"].isin(wc_baseline_ids)]
        wc_check_c = df_batters[df_batters["match_id"].isin(wc_baseline_ids)]
        assert len(wc_check_m) == len(df_wc_matches) == 132, "World Cup match preservation assertion failed!"
        assert len(wc_check_r) == len(df_wc_rosters) == 2905, "World Cup roster preservation assertion failed!"
        assert len(wc_check_c) == len(df_wc_contrib) == 2168, "World Cup contribution preservation assertion failed!"
        print("  [PASS] World Cup Absolute Preservation VERIFIED (132 matches, 2905 rosters, 2168 contributions).")

    # 2. DNB Rule
    dnb_players = df_season[df_season["batting_innings"] == 0]
    print(f"  Verified {len(dnb_players)} DNB player-seasons.")
    if len(dnb_players) > 0:
        assert dnb_players["average_contribution_score"].isna().all(), "DNB players must have NULL average score!"
        assert dnb_players["season_team_contribution_share"].isna().all(), "DNB players must have NULL team share!"
        print("  [PASS] Strict DNB Rule PASSED (100% NULL scores for non-batters).")

    # 3. Score bounds [0.1, 99.9]
    valid_scores = df_batters["contribution_score"].dropna()
    assert (valid_scores >= 0.1).all() and (valid_scores <= 99.9).all(), "Scores out of bounds [0.1, 99.9]!"
    print(f"  [PASS] Score Bounds PASSED ({valid_scores.min():.1f} to {valid_scores.max():.1f}).")

    # 4. Duplicate checks
    assert not df_matches.duplicated(subset=["match_id"]).any(), "Duplicate match IDs found!"
    print("  [PASS] Zero duplicate match IDs.")

    # Update processed registry
    all_match_records = df_matches.to_dict(orient="records")
    update_registry(all_match_records, competition)
    print(f"  [PASS] Updated {REGISTRY_PATH} with {len(df_matches)} matches.")

    t_total = time.time() - t0
    print(f"\nCOMPLETED INGESTION for {competition.upper()} in {t_total:.2f}s!")


def main():
    parser = argparse.ArgumentParser(description="Ingest multi-competition T20 data.")
    parser.add_argument("--competition", choices=["t20i", "smat", "all"], default="all", help="Competition to ingest")
    parser.add_argument("--min-date", default="2022-01-01", help="Earliest match date")
    parser.add_argument("--max-matches", type=int, default=None, help="Optional max matches to process per competition")
    args = parser.parse_args()

    comps = ["t20i", "smat"] if args.competition == "all" else [args.competition]

    for c in comps:
        if c == "t20i":
            raw = Path("data/t20s_json")
            out = Path("data/processed/t20i")
        elif c == "smat":
            raw = Path("data/smat_json")
            out = Path("data/processed/smat")
        else:
            continue

        if not raw.exists():
            print(f"Warning: Raw directory for {c} does not exist ({raw}). Skipping.")
            continue

        ingest_competition(
            competition=c,
            raw_dir=raw,
            out_dir=out,
            min_date=args.min_date,
            max_matches=args.max_matches,
        )


if __name__ == "__main__":
    main()
