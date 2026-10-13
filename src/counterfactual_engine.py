"""
Counterfactual Performance Engine (Phase 4B).

Objective:
Answers: "Given the exact match situation when the batter walked in and the opportunity
consumed, what could the batter reasonably have done differently to improve the team's position?"

Methodological Integrity & Anti-Leakage Rules:
1. Inputs strictly limited to information available at entry and during the batter's window:
   - entry_score, entry_team_rr, wickets_remaining_entry, balls_remaining_entry
   - batting_position, entry_phase
   - expected_runs, expected_sr
   - balls_faced (opportunity consumed)
   - partner_runs, partnership_duration
   - 1st innings: expected_final_entry
   - Chases: target, runs_required_entry, required_rr_entry, rr_gap_entry
2. Strictly FORBIDDEN as counterfactual inputs:
   - Final match result (won_match, winner)
   - Final winning margin
   - Opponent match performance
   - Post-exit team scoring or wickets
   - "Runs needed to win" / retrospective match margins
3. Generates 4 plausible, model-grounded counterfactual profiles:
   - CF_Par: Performed at exact situational expectation (expected_runs, expected_sr).
   - CF_Accelerated: Scored at elevated tempo (+20 SR or boundary acceleration).
   - CF_Preserved: Scored actual runs but preserved wicket (remained not out at exit).
   - CF_Rotation: Converted 3 dot balls into singles (improved strike rotation).
4. Simulates resulting team state transformation under each scenario without knowing future outcome.
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

# Ensure repository root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.expected_score_model import ExpectedScoreRFModel


class CounterfactualEngine:
    """
    Evaluates alternative batting trajectories grounded strictly in pre-exit context.
    """

    def __init__(self, part1_model_path: str = "models/expected_score"):
        self.rf_expected_final = ExpectedScoreRFModel.load(part1_model_path)

    def evaluate_batter_counterfactuals(self, row: Union[pd.Series, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Evaluate plausible counterfactual scenarios for a single batter innings.
        """
        # Extract situation at entry
        innings = int(row.get("innings", row.get("innings_number", 1)))
        is_chase = (innings == 2)

        entry_score = int(row.get("team_score_entry", row.get("entry_score", 0)))
        entry_wkts_lost = int(row.get("entry_wickets_lost", 0))
        entry_wkts_rem = int(row.get("wickets_remaining_entry", 10 - entry_wkts_lost))
        entry_balls_rem = int(row.get("balls_remaining_entry", row.get("entry_balls_remaining", 120)))
        entry_over = float(row.get("entry_over", 0.0))
        entry_team_rr = float(row.get("team_rr_entry", row.get("entry_team_rr", 0.0)))
        entry_phase = str(row.get("entry_phase", "MIDDLE"))

        # Actual performance and window
        actual_runs = int(row.get("actual_runs", row.get("runs", 0)))
        balls_faced = int(row.get("balls_faced", row.get("balls", 0)))
        actual_sr = float(row.get("actual_sr", row.get("strike_rate", 0.0)))
        expected_runs = float(row.get("expected_runs", actual_runs))
        expected_sr = float(row.get("expected_sr", actual_sr))
        dismissal_status = str(row.get("dismissal_status", "out"))

        exit_score = int(row.get("team_score_exit", row.get("exit_score", entry_score + actual_runs)))
        exit_wkts_lost = int(row.get("exit_wickets_lost", entry_wkts_lost + (1 if dismissal_status == "out" else 0)))
        exit_wkts_rem = int(row.get("wickets_remaining_exit", 10 - exit_wkts_lost))
        exit_balls_rem = int(row.get("balls_remaining_exit", row.get("exit_balls_remaining", 0)))
        exit_over = float(row.get("exit_over", entry_over + round(balls_faced / 6.0, 1)))
        exit_team_rr = float(row.get("team_rr_exit", row.get("exit_team_rr", entry_team_rr)))
        exit_phase = str(row.get("exit_phase", entry_phase))

        partner_runs = int(row.get("partner_runs", max(0, (exit_score - entry_score) - actual_runs)))

        # Actual trajectory change
        actual_expected_final_change = row.get("expected_final_change")
        actual_rrr_change = row.get("required_rr_change")

        # -------------------------------------------------------------
        # Scenario 1: Par Expectation (CF_Par)
        # -------------------------------------------------------------
        # What if batter scored exactly at situational expected runs & SR?
        cf_par_runs = round(expected_runs, 1)
        cf_par_exit_score = entry_score + int(round(cf_par_runs)) + partner_runs

        # -------------------------------------------------------------
        # Scenario 2: Accelerated Tempo (+20 SR or +1 boundary) (CF_Accel)
        # -------------------------------------------------------------
        additional_runs = max(2, int(np.round(balls_faced * 0.20)))
        cf_accel_runs = actual_runs + additional_runs
        cf_accel_exit_score = entry_score + cf_accel_runs + partner_runs

        # -------------------------------------------------------------
        # Scenario 3: Wicket Preservation (CF_Preserve)
        # -------------------------------------------------------------
        # What if batter scored actual runs but was NOT dismissed?
        cf_preserve_wkts_lost = max(entry_wkts_lost, exit_wkts_lost - (1 if dismissal_status == "out" else 0))
        cf_preserve_wkts_rem = 10 - cf_preserve_wkts_lost

        # -------------------------------------------------------------
        # Scenario 4: Strike Rotation (CF_Rotation)
        # -------------------------------------------------------------
        # What if batter converted 3 dot balls into strike-rotating singles?
        cf_rot_runs = actual_runs + min(3, int(row.get("dot_balls", 3)))
        cf_rot_exit_score = entry_score + cf_rot_runs + partner_runs

        cf_results: Dict[str, Any] = {
            "player": str(row.get("player", row.get("batter", "Unknown"))),
            "match_id": str(row.get("match_id", "")),
            "innings": innings,
            "actual_runs": actual_runs,
            "balls_faced": balls_faced,
            "actual_sr": actual_sr,
            "expected_runs": expected_runs,
            "expected_sr": expected_sr,
            "opportunity_usage": float(row.get("opportunity_usage", round(balls_faced / max(1, entry_balls_rem), 4))),
            "scenarios": {}
        }

        # -------------------------------------------------------------
        # Trajectory Simulation for 1st Innings
        # -------------------------------------------------------------
        if not is_chase and pd.notnull(row.get("expected_final_entry")):
            exp_final_entry = float(row.get("expected_final_entry", 165.0))

            def _sim_1st_innings_final(sim_exit_score: int, sim_wkts_lost: int) -> float:
                sim_wkts_rem = max(0, 10 - sim_wkts_lost)
                if exit_balls_rem == 0 or sim_wkts_rem == 0:
                    return float(sim_exit_score)

                sim_overs_bowled = 20.0 - (exit_balls_rem / 6.0)
                sim_rr = round(sim_exit_score / sim_overs_bowled, 2) if sim_overs_bowled > 0 else 0.0

                df_sim = pd.DataFrame([{
                    "current_team_runs": sim_exit_score,
                    "wickets_lost_so_far": sim_wkts_lost,
                    "wickets_remaining": sim_wkts_rem,
                    "overs_completed": exit_over,
                    "balls_remaining_in_innings": exit_balls_rem,
                    "current_team_rr": sim_rr,
                    "innings_phase": exit_phase,
                }])
                pred = float(self.rf_expected_final.predict(df_sim)[0])
                return round(pred, 1)

            # Evaluate each scenario
            final_par = _sim_1st_innings_final(cf_par_exit_score, exit_wkts_lost)
            chg_par = round(final_par - exp_final_entry, 1)

            final_accel = _sim_1st_innings_final(cf_accel_exit_score, exit_wkts_lost)
            chg_accel = round(final_accel - exp_final_entry, 1)

            final_preserve = _sim_1st_innings_final(exit_score, cf_preserve_wkts_lost)
            chg_preserve = round(final_preserve - exp_final_entry, 1)

            final_rot = _sim_1st_innings_final(cf_rot_exit_score, exit_wkts_lost)
            chg_rot = round(final_rot - exp_final_entry, 1)

            act_chg = float(actual_expected_final_change) if pd.notnull(actual_expected_final_change) else 0.0

            cf_results["scenarios"] = {
                "CF_Par": {
                    "hypothetical_runs": cf_par_runs,
                    "simulated_expected_final_exit": final_par,
                    "simulated_expected_final_change": chg_par,
                    "trajectory_gap_vs_actual": round(chg_par - act_chg, 1),
                },
                "CF_Accelerated": {
                    "hypothetical_runs": cf_accel_runs,
                    "additional_runs": additional_runs,
                    "simulated_expected_final_exit": final_accel,
                    "simulated_expected_final_change": chg_accel,
                    "trajectory_gain_vs_actual": round(chg_accel - act_chg, 1),
                },
                "CF_Wicket_Preserved": {
                    "hypothetical_wickets_remaining": cf_preserve_wkts_rem,
                    "simulated_expected_final_exit": final_preserve,
                    "simulated_expected_final_change": chg_preserve,
                    "wicket_preservation_value": round(chg_preserve - act_chg, 1),
                },
                "CF_Strike_Rotation": {
                    "hypothetical_runs": cf_rot_runs,
                    "simulated_expected_final_exit": final_rot,
                    "simulated_expected_final_change": chg_rot,
                    "rotation_gain_vs_actual": round(chg_rot - act_chg, 1),
                }
            }

        # -------------------------------------------------------------
        # Trajectory Simulation for Chases
        # -------------------------------------------------------------
        elif is_chase and pd.notnull(row.get("target")):
            target = float(row.get("target", 180.0))
            req_rr_entry = float(row.get("required_rr_entry", 9.0))
            act_rrr_chg = float(actual_rrr_change) if pd.notnull(actual_rrr_change) else 0.0

            def _sim_chase_rrr(sim_exit_score: int) -> float:
                req_rem = max(0.0, target - sim_exit_score)
                if req_rem <= 0 or exit_balls_rem <= 0:
                    return 0.0
                return round(req_rem * 6.0 / exit_balls_rem, 2)

            sim_rrr_par = _sim_chase_rrr(cf_par_exit_score)
            sim_rrr_chg_par = round(req_rr_entry - sim_rrr_par, 2)

            sim_rrr_accel = _sim_chase_rrr(cf_accel_exit_score)
            sim_rrr_chg_accel = round(req_rr_entry - sim_rrr_accel, 2)

            sim_rrr_rot = _sim_chase_rrr(cf_rot_exit_score)
            sim_rrr_chg_rot = round(req_rr_entry - sim_rrr_rot, 2)

            cf_results["scenarios"] = {
                "CF_Par": {
                    "hypothetical_runs": cf_par_runs,
                    "simulated_required_rr_exit": sim_rrr_par,
                    "simulated_required_rr_change": sim_rrr_chg_par,
                    "rrr_relief_gap_vs_actual": round(sim_rrr_chg_par - act_rrr_chg, 2),
                },
                "CF_Accelerated": {
                    "hypothetical_runs": cf_accel_runs,
                    "additional_runs": additional_runs,
                    "simulated_required_rr_exit": sim_rrr_accel,
                    "simulated_required_rr_change": sim_rrr_chg_accel,
                    "additional_rrr_reduction_vs_actual": round(sim_rrr_chg_accel - act_rrr_chg, 2),
                },
                "CF_Wicket_Preserved": {
                    "hypothetical_wickets_remaining": cf_preserve_wkts_rem,
                    "resource_preserved": 1 if dismissal_status == "out" else 0,
                    "commentary": "Maintains batting depth for subsequent death overs."
                },
                "CF_Strike_Rotation": {
                    "hypothetical_runs": cf_rot_runs,
                    "simulated_required_rr_exit": sim_rrr_rot,
                    "simulated_required_rr_change": sim_rrr_chg_rot,
                    "rotation_rrr_relief_gain": round(sim_rrr_chg_rot - act_rrr_chg, 2),
                }
            }

        return cf_results
