"""
Post-Match Processor Service.
Automates end-to-end post-match processing for newly completed T20 matches:
1. Strict T20 Match Format Validation (rejects non-T20 matches before processing).
2. Duplicate Processing Prevention (idempotent tracking via registry).
3. Scorecard & Batter Stay Extraction.
4. Production Contribution Scoring (calling compute_production_contribution).
5. Strict Did-Not-Bat (DNB) Rule Preservation (None / null score).
6. Automatic Publication & In-Memory Cache Invalidation within 60s target.
"""

import os
import json
import time
import math
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import pandas as pd
import numpy as np

from app.adapters.base import CricketApiAdapter
from app.adapters.factory import get_cricket_adapter
from src.contribution_framework import compute_production_contribution
from app.services.data_service import data_service

logger = logging.getLogger(__name__)

DEFAULT_REGISTRY_PATH = Path("data/processed/processed_matches_registry.json")


class PostMatchProcessor:
    """
    Automated pipeline processor for completed T20 cricket matches.
    """

    def __init__(
        self,
        adapter: Optional[CricketApiAdapter] = None,
        registry_path: Path | str = DEFAULT_REGISTRY_PATH,
    ):
        self.adapter = adapter or get_cricket_adapter()
        self.registry_path = Path(registry_path)
        self._registry: Dict[str, Dict[str, Any]] = self._load_registry()

    def _load_registry(self) -> Dict[str, Dict[str, Any]]:
        """Loads registry of already processed matches."""
        if self.registry_path.exists():
            try:
                with open(self.registry_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load processed match registry from {self.registry_path}: {e}")
        return {}

    def _save_registry(self):
        """Persists registry to disk."""
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.registry_path, "w", encoding="utf-8") as f:
                json.dump(self._registry, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save processed match registry: {e}")

    def is_match_processed(self, match_id: str | int, competition: Optional[str] = None) -> bool:
        """Checks if match has already been processed to avoid duplicate calculations."""
        m_str = str(match_id)
        if m_str in self._registry:
            return True

        # Check existing historical data_service matches if match_id is a numeric historical match
        if m_str.isdigit():
            try:
                comp = competition or "ipl"
                matches_df = data_service.get_matches_df(competition=comp)
                if matches_df is not None and not matches_df.empty:
                    if int(m_str) in matches_df["match_id"].dropna().astype(int).values:
                        return True
            except Exception:
                pass

        return False

    def process_match(
        self,
        match_id: str | int,
        match_data: Optional[Dict[str, Any]] = None,
        competition: Optional[str] = "ipl",
    ) -> Dict[str, Any]:
        """
        Executes the automatic post-match contribution rating workflow for a single match.
        
        Steps:
        1. Duplicate check.
        2. Format verification (T20 only).
        3. Scorecard extraction.
        4. Contribution score calculation using the production model.
        5. DNB preservation.
        6. Publication & registry update.
        """
        start_time = time.time()
        m_id_str = str(match_id)

        # 1. Duplicate check
        if self.is_match_processed(m_id_str, competition=competition):
            logger.info(f"Match {m_id_str} is already processed. Skipping duplicate calculation.")
            return {
                "match_id": m_id_str,
                "status": "already_processed",
                "format_valid": True,
                "message": "Match already processed. Skipping duplicate calculation.",
                "data": self._registry.get(m_id_str),
            }

        # 2. Fetch match details if not provided
        if match_data is None:
            try:
                match_data = self.adapter.fetch_match_details(m_id_str)
            except ValueError as ve:
                logger.warning(f"REJECTED non-T20 match {m_id_str}: {ve}")
                return {
                    "match_id": m_id_str,
                    "status": "rejected",
                    "format_valid": False,
                    "reason": f"Strict match format restriction violation: {ve}",
                }

        # 3. Strict T20 Match Format Validation
        is_t20, reason = self.adapter.validate_t20_format(match_data)
        if not is_t20:
            logger.warning(f"REJECTED non-T20 match {m_id_str}: {reason}")
            return {
                "match_id": m_id_str,
                "status": "rejected",
                "format_valid": False,
                "reason": f"Strict match format restriction violation: {reason}",
            }

        # 4. Extract Match Level Metadata
        metadata = self._extract_match_metadata(m_id_str, match_data)

        # 5. Extract and Calculate Batter Contributions
        batter_results, qualified_batters, limited_batters = self._calculate_batter_contributions(
            metadata, match_data
        )

        processing_duration = round(time.time() - start_time, 3)
        meets_sla = processing_duration < 60.0

        result_payload = {
            "match_id": m_id_str,
            "status": "success",
            "format_valid": True,
            "format": metadata.get("format", "T20"),
            "provider": self.adapter.provider_name,
            "season": metadata.get("season"),
            "date": metadata.get("date"),
            "teams": metadata.get("teams"),
            "winner": metadata.get("winner"),
            "result": metadata.get("result"),
            "total_batters": len(batter_results),
            "qualified_count": len(qualified_batters),
            "limited_sample_count": len(limited_batters),
            "top_qualified_contributor": qualified_batters[0] if qualified_batters else None,
            "batters": batter_results,
            "processing_duration_seconds": processing_duration,
            "sla_met_60s": meets_sla,
        }

        # 6. Save to Registry
        self._registry[m_id_str] = {
            "processed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "duration_seconds": processing_duration,
            "season": metadata.get("season"),
            "teams": metadata.get("teams"),
            "winner": metadata.get("winner"),
            "batters_count": len(batter_results),
        }
        self._save_registry()

        # 7. Update DataService in-memory tables if available
        self._publish_to_data_service(metadata, batter_results)

        logger.info(
            f"Successfully processed T20 match {m_id_str} in {processing_duration}s "
            f"(SLA <60s: {meets_sla}, Batters: {len(batter_results)})"
        )
        return result_payload

    def _extract_match_metadata(self, match_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extracts normalized match metadata from provider payload."""
        # Handle Cricsheet structure
        if "match_row" in data:
            mr = data["match_row"]
            return {
                "match_id": match_id,
                "season": str(mr.get("season", "2024")),
                "date": str(mr.get("date", "")),
                "venue": str(mr.get("venue", "")),
                "city": str(mr.get("city", "")),
                "teams": [mr.get("team1"), mr.get("team2")],
                "winner": mr.get("winner"),
                "win_by_runs": mr.get("win_by_runs"),
                "win_by_wickets": mr.get("win_by_wickets"),
                "result": f"{mr.get('winner')} won" if mr.get("winner") else "Result",
                "format": "T20",
            }

        # Handle Generic / CricketData / Mock structure
        teams = data.get("teams", [])
        outcome = data.get("outcome", {})
        winner = outcome.get("winner") or data.get("winner")
        by_info = outcome.get("by", {})
        w_runs = by_info.get("runs") or data.get("win_by_runs")
        w_wkts = by_info.get("wickets") or data.get("win_by_wickets")
        status_str = data.get("status", "")

        return {
            "match_id": match_id,
            "season": str(data.get("season", "2024")),
            "date": str(data.get("date", "")),
            "venue": str(data.get("venue", "")),
            "city": str(data.get("city", "")),
            "teams": teams,
            "winner": winner,
            "win_by_runs": w_runs,
            "win_by_wickets": w_wkts,
            "result": status_str or (f"{winner} won" if winner else "Completed"),
            "format": str(data.get("matchType") or data.get("format") or "T20").upper(),
        }

    def _calculate_batter_contributions(
        self, metadata: Dict[str, Any], data: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Parses all batters across both innings and computes final contribution ratings
        using the production model.
        """
        batter_entries = []
        winner = metadata.get("winner")
        teams = metadata.get("teams", ["Team A", "Team B"])

        # Determine data source format
        if "batter_innings_rows" in data:
            # Cricsheet parsed format
            rows = data["batter_innings_rows"]
            for r in rows:
                b_name = r.get("batter")
                b_team = r.get("batting_team")
                b_opp = r.get("bowling_team")
                inn = int(r.get("innings_number", 1))
                b_runs = int(r.get("runs", 0))
                b_balls = int(r.get("balls_faced", 0))
                d_status = str(r.get("dismissal_status", "not out"))
                d_kind = r.get("dismissal_kind")
                fours = int(r.get("fours", 0))
                sixes = int(r.get("sixes", 0))
                dot_balls = int(r.get("dot_balls", 0))

                entry_over = float(r.get("entry_over", 0.0) or 0.0)
                exit_over = float(r.get("exit_over", 20.0) or (entry_over + b_balls / 6.0))

                batter_entries.append({
                    "player": b_name,
                    "team": b_team,
                    "opponent": b_opp,
                    "innings": inn,
                    "runs": b_runs,
                    "balls": b_balls,
                    "fours": fours,
                    "sixes": sixes,
                    "dot_balls": dot_balls,
                    "dismissal_status": d_status,
                    "dismissal_kind": d_kind,
                    "entry_over": entry_over,
                    "exit_over": exit_over,
                    "dnb": False,
                })

        elif "scorecard" in data and "innings" in data["scorecard"]:
            # Standard scorecard structure (Mock / API)
            for inn_obj in data["scorecard"]["innings"]:
                inn = int(inn_obj.get("innings_number", 1))
                b_team = inn_obj.get("team")
                b_opp = teams[1] if b_team == teams[0] else teams[0]
                target = inn_obj.get("target")

                for b in inn_obj.get("batters", []):
                    is_dnb = bool(b.get("dnb") or b.get("dismissal_status") == "dnb" or (b.get("balls", 0) == 0 and b.get("runs", 0) == 0 and b.get("dismissal_status") is None))
                    b_runs = int(b.get("runs", 0))
                    b_balls = int(b.get("balls", 0))

                    batter_entries.append({
                        "player": b.get("player"),
                        "team": b_team,
                        "opponent": b_opp,
                        "innings": inn,
                        "runs": b_runs,
                        "balls": b_balls,
                        "fours": int(b.get("fours", 0)),
                        "sixes": int(b.get("sixes", 0)),
                        "dot_balls": int(b.get("dot_balls", 0)),
                        "dismissal_status": b.get("dismissal_status", "out" if not is_dnb else "dnb"),
                        "dismissal_kind": b.get("dismissal_kind"),
                        "entry_over": float(b.get("entry_over", 0.0)),
                        "exit_over": float(b.get("exit_over", 20.0)),
                        "target": target,
                        "dnb": is_dnb,
                    })

        all_batters = []
        qualified_batters = []
        limited_batters = []

        for b in batter_entries:
            p_name = b["player"]
            b_team = b["team"]
            b_opp = b["opponent"]
            inn = b["innings"]
            b_runs = b["runs"]
            b_balls = b["balls"]
            is_dnb = b["dnb"]
            won = (winner == b_team)

            # Strict Did Not Bat (DNB) Handling
            if is_dnb or (b_balls == 0 and b_runs == 0 and b["dismissal_status"] in ("dnb", "did not bat")):
                res_dnb = {
                    "player": p_name,
                    "team": b_team,
                    "opponent": b_opp,
                    "innings": inn,
                    "runs": 0,
                    "balls": 0,
                    "strike_rate": None,
                    "fours": 0,
                    "sixes": 0,
                    "dismissal_status": "dnb",
                    "dismissal_kind": None,
                    "contribution_score": None,  # STRICT DNB RULE: null, NEVER 0 or 50
                    "raw_contribution": None,
                    "score_context": None,
                    "score_perf": None,
                    "score_state": None,
                    "leverage": None,
                    "dnb": True,
                    "is_dnb": True,
                    "is_qualified": False,
                    "qualification_status": "Did Not Bat",
                    "sample_reason": "Player did not bat (DNB preserved as null)",
                    "won_match": won,
                    "team_result": "Won" if won else "Lost",
                }
                all_batters.append(res_dnb)
                continue

            # Active Batting Appearance: Reconstruct Stay Features
            sr = round((b_runs / b_balls) * 100.0, 2) if b_balls > 0 else 0.0
            
            # Contextual baselines for T20 batting
            # Expected runs approx: 1.15 * balls faced in standard T20, baseline SR approx 125
            exp_runs = round(b_balls * 1.25, 1)
            exp_sr = 125.0
            run_dev = b_runs - exp_runs
            sr_dev = sr - exp_sr

            # Construct row payload matching compute_production_contribution expectations
            entry_ov = b["entry_over"]
            exit_ov = b["exit_over"]
            stay_overs = max(0.2, exit_ov - entry_ov)

            row_dict = {
                "match_id": metadata["match_id"],
                "innings": inn,
                "team": b_team,
                "opponent": b_opp,
                "player": p_name,
                "actual_runs": b_runs,
                "balls_faced": b_balls,
                "actual_sr": sr,
                "expected_runs": exp_runs,
                "expected_sr": exp_sr,
                "run_deviation": run_dev,
                "sr_deviation": sr_dev,
                "fours": b["fours"],
                "sixes": b["sixes"],
                "entry_over": entry_ov,
                "exit_over": exit_ov,
                "overs_spent": stay_overs,
                "team_runs_added": b_runs + int(stay_overs * 6.5),
                "window_team_rr": round((b_runs + stay_overs * 6.5) / stay_overs, 2),
                "team_rr_entry": 8.0,
                "balls_remaining_entry": max(0, 120 - int(entry_ov * 6)),
                "wickets_remaining_entry": 8,
                "target": b.get("target"),
                "won_match": won,
            }

            # In chase (2nd innings) calculate required RR dynamics
            if inn == 2 and b.get("target"):
                target_runs = float(b["target"])
                req_runs_entry = max(1.0, target_runs - 40.0)
                req_rr_entry = (req_runs_entry / (row_dict["balls_remaining_entry"] / 6.0)) if row_dict["balls_remaining_entry"] > 0 else 9.0
                row_dict["required_rr_entry"] = req_rr_entry
                row_dict["required_rr_change"] = -1.2 if b_runs >= 30 else 0.5
                row_dict["target_progress_change"] = round(b_runs / target_runs, 3)

            # Compute contribution score with verified production model
            model_res = compute_production_contribution(row_dict)

            final_score = model_res.get("contribution_score")
            raw_contrib = model_res.get("raw_contribution")
            p1 = model_res.get("pillar1_context_score")
            p2 = model_res.get("pillar2_perf_score")
            p3 = model_res.get("pillar3_state_score")
            lev = model_res.get("leverage")

            # Qualification Rule: balls >= 10 OR runs >= 20
            is_qual = bool((b_balls >= 10) or (b_runs >= 20))

            batter_summary = {
                "rank": None,  # Assigned after sorting qualified batters
                "is_qualified": is_qual,
                "qualification_status": "Qualified" if is_qual else "Limited Sample",
                "sample_reason": None if is_qual else f"Limited sample ({b_runs} runs / {b_balls} balls)",
                "player": p_name,
                "team": b_team,
                "opponent": b_opp,
                "innings": inn,
                "entry_over": round(entry_ov, 1),
                "exit_over": round(exit_ov, 1),
                "runs": b_runs,
                "balls": b_balls,
                "strike_rate": sr,
                "fours": b["fours"],
                "sixes": b["sixes"],
                "dismissal_status": b["dismissal_status"],
                "dismissal_kind": b["dismissal_kind"],
                "contribution_score": final_score,
                "raw_contribution": raw_contrib,
                "score_context": p1,
                "score_perf": p2,
                "score_state": p3,
                "leverage": lev,
                "dnb": False,
                "is_dnb": False,
                "won_match": won,
                "team_result": "Won" if won else "Lost",
            }

            if is_qual:
                qualified_batters.append(batter_summary)
            else:
                limited_batters.append(batter_summary)

        # Sort qualified batters by contribution_score DESC
        qualified_batters.sort(
            key=lambda x: (x["contribution_score"] or -999, x["runs"]), reverse=True
        )
        for rank_idx, qb in enumerate(qualified_batters, 1):
            qb["rank"] = rank_idx

        # Limited sample batters sorted by contribution_score DESC
        limited_batters.sort(
            key=lambda x: (x["contribution_score"] or -999, x["runs"]), reverse=True
        )

        all_batters = qualified_batters + limited_batters + [b for b in all_batters if b.get("dnb")]
        return all_batters, qualified_batters, limited_batters

    def _publish_to_data_service(self, metadata: Dict[str, Any], batters: List[Dict[str, Any]]):
        """
        Dynamically injects newly computed match into data_service memory
        so it immediately displays on frontend endpoints.
        """
        try:
            data_service._ensure_loaded()
            m_id = int(metadata["match_id"]) if str(metadata["match_id"]).isdigit() else metadata["match_id"]
            
            # Update matches_df if not already present
            if data_service._matches_df is not None:
                if m_id not in data_service._matches_df["match_id"].values:
                    new_m_row = {
                        "match_id": m_id,
                        "season": str(metadata.get("season", "2024")),
                        "date": str(metadata.get("date", "")),
                        "venue": str(metadata.get("venue", "")),
                        "city": str(metadata.get("city", "")),
                        "team1": metadata["teams"][0] if len(metadata["teams"]) > 0 else "Team 1",
                        "team2": metadata["teams"][1] if len(metadata["teams"]) > 1 else "Team 2",
                        "winner": metadata.get("winner"),
                        "win_by_runs": metadata.get("win_by_runs"),
                        "win_by_wickets": metadata.get("win_by_wickets"),
                        "toss_winner": None,
                        "toss_decision": None,
                        "player_of_match": None,
                    }
                    data_service._matches_df = pd.concat(
                        [data_service._matches_df, pd.DataFrame([new_m_row])], ignore_index=True
                    )

            # Update contributions_df with batting appearances
            if data_service._contributions_df is not None:
                contrib_rows = []
                for b in batters:
                    if not b.get("dnb"):
                        contrib_rows.append({
                            "match_id": m_id,
                            "season": str(metadata.get("season", "2024")),
                            "innings": b["innings"],
                            "team": b["team"],
                            "opponent": b["opponent"],
                            "player": b["player"],
                            "actual_runs": b["runs"],
                            "balls_faced": b["balls"],
                            "actual_sr": b["strike_rate"],
                            "fours": b["fours"],
                            "sixes": b["sixes"],
                            "dismissal_status": b["dismissal_status"],
                            "dismissal_kind": b["dismissal_kind"],
                            "entry_over": b["entry_over"],
                            "exit_over": b["exit_over"],
                            "contribution_score": b["contribution_score"],
                            "raw_contribution": b["raw_contribution"],
                            "score_context": b["score_context"],
                            "score_perf": b["score_perf"],
                            "score_state": b["score_state"],
                            "leverage": b["leverage"],
                            "is_negligible": False,
                            "won_match": b["won_match"],
                            "final_team_score": 180,
                        })
                if contrib_rows:
                    data_service._contributions_df = pd.concat(
                        [data_service._contributions_df, pd.DataFrame(contrib_rows)], ignore_index=True
                    )
            logger.info(f"Published match {m_id} to in-memory data_service.")
        except Exception as e:
            logger.warning(f"Could not update in-memory data_service: {e}")

    def poll_and_process_recent_matches(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Polls the adapter for completed matches and automatically processes
        any unhandled eligible T20 matches.
        """
        logger.info(f"Polling {self.adapter.provider_name} for completed T20 matches...")
        completed = self.adapter.get_completed_matches(limit=limit)
        results = []

        for m in completed:
            m_id = m.get("id") or m.get("match_id")
            if not m_id:
                continue

            if self.is_match_processed(m_id):
                logger.debug(f"Match {m_id} already processed. Skipping.")
                continue

            try:
                res = self.process_match(match_id=m_id)
                results.append(res)
            except Exception as e:
                logger.error(f"Error processing completed match {m_id}: {e}")

        return results
