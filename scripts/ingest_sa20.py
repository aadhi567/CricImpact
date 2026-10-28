"""
SA20 Competition Ingestion Adapter for CricImpact.
Ingests Cricsheet JSON v1.2.0 files from data/raw/sa20/sat_json.zip into data/processed/sa20/.

Adheres strictly to CricImpact architectural invariants:
1. Isolated storage: data/processed/sa20/ (never touches IPL or T20I processed datasets).
2. Model invariance: uses unchanged compute_production_contribution (Strategy 4).
3. DNB rule: non-batting appearances have NaN/null contribution score and team share.
4. Schema normalization: matches.csv, match_rosters.csv, batter_match_contributions.csv,
   phase6_season_metrics.csv, deliveries.csv.
5. Idempotent registry: updates data/processed/processed_matches_registry.json.
6. Ground analytics: updates conditions and phase statistics in data/processed/phase_summaries.json.
"""

import json
import time
import zipfile
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import pandas as pd
import numpy as np

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.contribution_framework import compute_production_contribution
from src.season_aggregation import build_season_aggregations

ROOT_DIR = Path(__file__).resolve().parent.parent
ZIP_PATH = ROOT_DIR / "data" / "raw" / "sa20" / "sat_json.zip"
OUT_DIR = ROOT_DIR / "data" / "processed" / "sa20"
REGISTRY_PATH = ROOT_DIR / "data" / "processed" / "processed_matches_registry.json"
PHASE_SUMMARIES_PATH = ROOT_DIR / "data" / "processed" / "phase_summaries.json"

SA20_TEAMS = {
    "Sunrisers Eastern Cape",
    "Paarl Royals",
    "Joburg Super Kings",
    "MI Cape Town",
    "Pretoria Capitals",
    "Durban's Super Giants",
}

TEAM_ALIASES = {
    "Durban Super Giants": "Durban's Super Giants",
    "Durbans Super Giants": "Durban's Super Giants",
}


def normalize_team(t: Optional[str]) -> Optional[str]:
    if not t:
        return t
    t_clean = str(t).strip()
    return TEAM_ALIASES.get(t_clean, t_clean)


def parse_sa20_match(
    mid: str,
    match_dict: Dict[str, Any]
) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any], Dict[str, Any]]:
    """
    Parses a single Cricsheet SA20 match JSON into:
    - match_row
    - roster_rows
    - batter_rows (with Strategy 4 production score)
    - delivery_rows
    - condition_dict (for phase_summaries.json)
    - phase_dict (for phase_summaries.json)
    """
    info = match_dict.get("info", {})

    if info.get("gender") != "male" or str(info.get("match_type", "")).upper() != "T20":
        return None, [], [], [], {}, {}

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
    event_obj = info.get("event", {})
    event_name = ""
    stage = ""
    match_number = ""
    if isinstance(event_obj, dict):
        event_name = str(event_obj.get("name", "SA20")).strip()
        stage = str(event_obj.get("stage", "")).strip()
        match_number = str(event_obj.get("match_number", "")).strip()
    elif isinstance(event_obj, str):
        event_name = event_obj.strip()

    if not event_name:
        event_name = "SA20"

    match_row = {
        "match_id": mid,
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
                "match_id": mid,
                "season": season,
                "team": norm_t_name,
                "player": p,
            })

    # Deliveries and Batter Innings Extraction
    delivery_rows = []
    batter_rows = []
    first_innings_total = 0

    # Extract all deliveries (including super overs) for deliveries.csv
    for inn_idx, inn in enumerate(raw_innings):
        innings_num = inn_idx + 1
        batting_team = normalize_team(inn.get("team"))
        bowling_team = team2 if batting_team == team1 else team1
        for over_obj in inn.get("overs", []):
            over_num = over_obj.get("over", 0)
            for b_idx, deliv in enumerate(over_obj.get("deliveries", [])):
                b_num = b_idx + 1
                batter = deliv.get("batter")
                non_striker = deliv.get("non_striker")
                bowler = deliv.get("bowler")

                runs_info = deliv.get("runs", {})
                b_runs = runs_info.get("batter", 0)
                tot_runs = runs_info.get("total", 0)
                extras_info = deliv.get("extras", {})
                extra_type = ", ".join(extras_info.keys()) if extras_info else None
                wides = int(extras_info.get("wides", 0))
                noballs = int(extras_info.get("noballs", 0))
                byes = int(extras_info.get("byes", 0))
                legbyes = int(extras_info.get("legbyes", 0))
                penalty = int(extras_info.get("penalty", 0))

                wickets_list = deliv.get("wickets", [])
                p_out = wickets_list[0].get("player_out") if wickets_list else None
                kind = wickets_list[0].get("kind") if wickets_list else None
                is_wicket = bool(wickets_list)

                delivery_rows.append({
                    "match_id": mid,
                    "season": season,
                    "innings_number": innings_num,
                    "over": over_num,
                    "ball": b_num,
                    "batting_team": batting_team,
                    "bowling_team": bowling_team,
                    "batter": batter,
                    "non_striker": non_striker,
                    "bowler": bowler,
                    "batter_runs": b_runs,
                    "extras_runs": tot_runs - b_runs,
                    "total_runs": tot_runs,
                    "extra_type": extra_type,
                    "player_dismissed": p_out,
                    "dismissal_kind": kind,
                    "is_wicket": is_wicket,
                    "wides": wides,
                    "noballs": noballs,
                    "byes": byes,
                    "legbyes": legbyes,
                    "penalty": penalty,
                })

    # Phase tracking for ground analysis
    # Phases: Powerplay (0-5 overs, balls 1-36), Middle (6-14 overs, balls 37-90), Death (15-19 overs, balls 91-120)
    inn_phases = {}

    for inn_idx, inn in enumerate(raw_innings[:2]):  # Innings 1 and 2 only for Strategy 4 contribution models
        innings_num = inn_idx + 1
        batting_team = normalize_team(inn.get("team"))
        bowling_team = team2 if batting_team == team1 else team1
        target_runs = inn.get("target", {}).get("runs") if "target" in inn else None
        if innings_num == 2 and (target_runs is None or target_runs == 0) and first_innings_total > 0:
            target_runs = first_innings_total + 1

        legal_balls = 0
        total_runs = 0
        wickets_down = 0

        batters_stat: Dict[str, Dict[str, int]] = {}
        batter_entry: Dict[str, Dict[str, Any]] = {}
        batter_exit: Dict[str, Dict[str, Any]] = {}
        seen_order: List[str] = []

        # Phase aggregates: powerplay (ov 0-5), middle (ov 6-14), death (ov 15-19)
        phase_stats = {
            "powerplay": {"runs": 0, "wickets": 0, "legal_balls": 0},
            "middle": {"runs": 0, "wickets": 0, "legal_balls": 0},
            "death": {"runs": 0, "wickets": 0, "legal_balls": 0},
        }

        overs_data = inn.get("overs", [])
        for over_obj in overs_data:
            over_num = over_obj.get("over", 0)
            deliveries = over_obj.get("deliveries", [])
            for b_idx, deliv in enumerate(deliveries):
                b_num = b_idx + 1
                batter = deliv.get("batter")
                non_striker = deliv.get("non_striker")
                bowler = deliv.get("bowler")

                runs_info = deliv.get("runs", {})
                b_runs = runs_info.get("batter", 0)
                tot_runs = runs_info.get("total", 0)
                extras_info = deliv.get("extras", {})
                extra_type = ", ".join(extras_info.keys()) if extras_info else None
                wides = int(extras_info.get("wides", 0))
                noballs = int(extras_info.get("noballs", 0))
                byes = int(extras_info.get("byes", 0))
                legbyes = int(extras_info.get("legbyes", 0))
                penalty = int(extras_info.get("penalty", 0))

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

                # Phase assignment
                if over_num < 6:
                    p_name = "powerplay"
                elif over_num < 15:
                    p_name = "middle"
                else:
                    p_name = "death"

                phase_stats[p_name]["runs"] += tot_runs
                if is_legal:
                    phase_stats[p_name]["legal_balls"] += 1

                wickets_list = deliv.get("wickets", [])
                p_out = wickets_list[0].get("player_out") if wickets_list else None
                kind = wickets_list[0].get("kind") if wickets_list else None
                is_wicket = bool(wickets_list)

                if wickets_list:
                    for w in wickets_list:
                        p_o = w.get("player_out")
                        k = w.get("kind")
                        if k != "retired hurt":
                            wickets_down += 1
                            phase_stats[p_name]["wickets"] += 1
                        if p_o:
                            exit_dec = round(over_num + b_num / 10.0, 1)
                            batter_exit[p_o] = {
                                "over": exit_dec,
                                "balls_bowled": legal_balls,
                                "team_score": total_runs,
                                "team_rr": round(total_runs / (legal_balls / 6.0), 2) if legal_balls >= 6 else total_runs,
                                "wickets_down": wickets_down,
                                "balls_rem": max(0, 120 - legal_balls),
                                "wickets_rem": max(0, 10 - wickets_down),
                                "dismissal_status": "retired hurt" if k == "retired hurt" else "out",
                                "dismissal_kind": k,
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
                "match_id": mid,
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

            # Strategy 4 Production Model Scoring
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

        inn_phases[f"innings{innings_num}"] = {
            "team": batting_team,
            "runs": total_runs,
            "wickets": wickets_down,
            "overs": round(legal_balls / 6.0, 1),
            "phases": phase_stats,
        }

        if innings_num == 1:
            first_innings_total = total_runs

    # Condition determination
    method = outcome.get("method")
    res_str = outcome.get("result")
    is_dls = method == "D/L" or "method" in outcome
    is_no_result = res_str in ("no result", "abandoned") or not winner or len(raw_innings) < 2
    is_standard_20ov = not (is_dls or is_no_result)
    cond_label = "Standard 20-over match" if is_standard_20ov else ("Rain-interrupted / DLS" if is_dls else "Reduced overs (non-DLS)")

    condition_info = {
        "is_standard_20ov": is_standard_20ov,
        "condition_label": cond_label,
        "is_dls": is_dls,
        "is_reduced": is_dls or is_no_result,
        "is_no_result": is_no_result,
        "sched_overs": 20,
        "target_overs": 20,
    }

    return match_row, roster_rows, batter_rows, delivery_rows, condition_info, inn_phases


def run_ingestion():
    print(f"=======================================================")
    print(f"Starting SA20 Ingestion Pipeline")
    print(f"Source Archive: {ZIP_PATH}")
    print(f"Destination Directory: {OUT_DIR}")
    print(f"=======================================================")

    t0 = time.time()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    matches_list = []
    rosters_list = []
    batters_list = []
    deliveries_list = []
    conditions_dict = {}
    phases_dict = {}

    with zipfile.ZipFile(ZIP_PATH, "r") as z:
        json_names = sorted([n for n in z.namelist() if n.endswith(".json")])
        print(f"Found {len(json_names)} JSON files in archive.")

        for idx, jname in enumerate(json_names, 1):
            mid = jname.replace(".json", "")
            with z.open(jname) as fp:
                match_dict = json.load(fp)

            m_row, r_rows, b_rows, d_rows, c_info, p_info = parse_sa20_match(mid, match_dict)
            if m_row is None:
                continue

            matches_list.append(m_row)
            rosters_list.extend(r_rows)
            batters_list.extend(b_rows)
            deliveries_list.extend(d_rows)
            conditions_dict[mid] = c_info
            phases_dict[mid] = p_info

    df_matches = pd.DataFrame(matches_list)
    df_rosters = pd.DataFrame(rosters_list)
    df_batters = pd.DataFrame(batters_list)
    df_deliveries = pd.DataFrame(deliveries_list)

    # Sort and deduplicate
    df_matches = df_matches.drop_duplicates(subset=["match_id"]).sort_values(by=["date", "match_id"], ascending=[False, False]).reset_index(drop=True)
    df_rosters = df_rosters.sort_values(by=["match_id", "team", "player"]).reset_index(drop=True)
    df_batters = df_batters.sort_values(by=["match_id", "innings", "player"]).reset_index(drop=True)
    df_deliveries = df_deliveries.sort_values(by=["match_id", "innings_number", "over", "ball"]).reset_index(drop=True)

    # Save CSVs
    matches_csv = OUT_DIR / "matches.csv"
    rosters_csv = OUT_DIR / "match_rosters.csv"
    batters_csv = OUT_DIR / "batter_match_contributions.csv"
    deliveries_csv = OUT_DIR / "deliveries.csv"
    season_metrics_csv = OUT_DIR / "phase6_season_metrics.csv"

    print("\nSaving SA20 normalized datasets:")
    df_matches.to_csv(matches_csv, index=False, encoding="utf-8")
    print(f"  Saved {matches_csv} ({len(df_matches)} matches, {matches_csv.stat().st_size / 1024:.1f} KB)")
    df_rosters.to_csv(rosters_csv, index=False, encoding="utf-8")
    print(f"  Saved {rosters_csv} ({len(df_rosters)} roster rows, {rosters_csv.stat().st_size / 1024:.1f} KB)")
    df_batters.to_csv(batters_csv, index=False, encoding="utf-8")
    print(f"  Saved {batters_csv} ({len(df_batters)} batter contributions, {batters_csv.stat().st_size / 1024:.1f} KB)")
    df_deliveries.to_csv(deliveries_csv, index=False, encoding="utf-8")
    print(f"  Saved {deliveries_csv} ({len(df_deliveries)} deliveries, {deliveries_csv.stat().st_size / (1024*1024):.2f} MB)")

    # Compute season aggregations
    print("\nComputing comprehensive season aggregations (View A & View B)...")
    t_season = time.time()
    df_season = build_season_aggregations(df_batters, df_rosters=df_rosters)
    df_season.to_csv(season_metrics_csv, index=False, encoding="utf-8")
    print(f"  Saved {season_metrics_csv} ({len(df_season)} player-seasons in {time.time() - t_season:.2f}s)")

    # Data Quality & Integrity Audits
    print("\nData Quality Verification:")
    # 1. Total records check
    assert len(df_matches) == 130, f"Expected 130 matches, found {len(df_matches)}"
    assert len(df_deliveries) == 29020, f"Expected 29,020 deliveries, found {len(df_deliveries)}"
    print(f"  [PASS] 130 matches and 29,020 deliveries verified.")

    # 2. Strict DNB rule
    dnb_players = df_season[df_season["batting_innings"] == 0]
    print(f"  Checking {len(dnb_players)} DNB player-seasons...")
    if len(dnb_players) > 0:
        assert dnb_players["average_contribution_score"].isna().all(), "DNB players must have NULL average score!"
        assert dnb_players["season_team_contribution_share"].isna().all(), "DNB players must have NULL team share!"
        print("  [PASS] Strict DNB Rule PASSED (100% NULL scores for non-batting appearances).")

    # 3. Score bounds [0.1, 99.9]
    valid_scores = df_batters["contribution_score"].dropna()
    assert (valid_scores >= 0.1).all() and (valid_scores <= 99.9).all(), "Scores out of bounds [0.1, 99.9]!"
    print(f"  [PASS] Score bounds verified ({valid_scores.min():.2f} to {valid_scores.max():.2f}).")

    # 4. Zero duplicate match IDs
    assert not df_matches.duplicated(subset=["match_id"]).any(), "Duplicate match IDs found!"
    print("  [PASS] Zero duplicate match IDs.")

    # 5. Update processed matches registry
    print("\nUpdating processed_matches_registry.json...")
    registry = {}
    if REGISTRY_PATH.exists():
        try:
            with open(REGISTRY_PATH, "r", encoding="utf-8") as fp:
                registry = json.load(fp)
        except Exception:
            registry = {}

    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    for m in matches_list:
        mid_str = str(m["match_id"])
        registry[mid_str] = {
            "competition": "SA20",
            "format": "T20",
            "processed_at": now_iso,
            "season": str(m.get("season", "")),
            "date": str(m.get("date", "")),
            "teams": [m.get("team1"), m.get("team2")],
            "winner": m.get("winner"),
        }

    with open(REGISTRY_PATH, "w", encoding="utf-8") as fp:
        json.dump(registry, fp, indent=2, default=str)
    print(f"  [PASS] Registry updated with {len(matches_list)} SA20 matches.")

    # 6. Update phase_summaries.json (Ground Analysis)
    print("\nUpdating phase_summaries.json for Ground Analysis...")
    phase_data = {"conditions": {}, "phases": {}}
    if PHASE_SUMMARIES_PATH.exists():
        try:
            with open(PHASE_SUMMARIES_PATH, "r", encoding="utf-8") as fp:
                phase_data = json.load(fp)
        except Exception:
            phase_data = {"conditions": {}, "phases": {}}

    phase_data.setdefault("conditions", {}).update(conditions_dict)
    phase_data.setdefault("phases", {}).update(phases_dict)

    with open(PHASE_SUMMARIES_PATH, "w", encoding="utf-8") as fp:
        json.dump(phase_data, fp)
    print(f"  [PASS] phase_summaries.json updated with {len(conditions_dict)} SA20 matches.")

    print(f"\n=======================================================")
    print(f"SA20 Ingestion Complete in {time.time() - t0:.2f}s")
    print(f"=======================================================")


if __name__ == "__main__":
    run_ingestion()
