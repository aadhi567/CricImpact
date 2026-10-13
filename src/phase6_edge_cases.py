"""
Phase 6A Critical Edge Cases Evaluator and Validator.

Explicitly evaluates and records the 10 critical scenarios specified in Section 5:
- CASE A: 1* off 1, team already comfortably ahead, little remaining opportunity
- CASE B: 1* off 1, team needs 1 run from 1 ball, batter wins the match
- CASE C: 5* off 2, normal middle-over situation
- CASE D: 8* off 3, death overs
- CASE E: 8* off 12, team under pressure
- CASE F: 30 off 5, 19th/20th over, large positive team-state impact
- CASE G: 30 off 5, early overs, large balls remaining
- CASE H: 5* off 3, team already scoring at a very high RR
- CASE I: 5* off 3, team struggling with multiple wickets lost
- CASE J: 0 balls faced, run-out/non-striker dismissal or equivalent valid zero-ball event
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.contribution_framework import (
    compute_phase5b_contribution,
    PHASE5B_EMPIRICAL_PARAMS,
)

CRITICAL_EDGE_CASES: List[Dict[str, Any]] = [
    {
        "case_id": "CASE A",
        "title": "1* off 1, team already comfortably ahead",
        "description": "Enters needing 3 off 8 balls (RRR 3.0) with 8 wickets in hand. Scores 1* off 1 ball, victory already assured.",
        "params": {
            "innings": 2, "entry_over": 18.4, "balls_remaining_entry": 8, "wickets_remaining_entry": 8,
            "required_rr_entry": 3.0, "rr_gap_entry": -5.0, "actual_runs": 1, "balls_faced": 1, "actual_sr": 100.0,
            "boundary_percentage": 0.0, "run_deviation": 0.0, "sr_deviation": -20.0, "opportunity_usage": 0.12,
            "dismissal_status": "not out", "balls_remaining_exit": 7, "wickets_remaining_exit": 8, "wicket_resource_change": 0,
            "required_rr_change": 0.5, "rr_gap_change": 0.5, "target_progress_change": 0.02
        },
        "expectation": "Genuine batting evaluation, low incremental contribution (~30-36), definitely NOT NULL."
    },
    {
        "case_id": "CASE B",
        "title": "1* off 1, team needs 1 run from 1 ball to win",
        "description": "Final delivery of match, 1 run needed with 3 wickets in hand. Batter scores 1 to seal victory.",
        "params": {
            "innings": 2, "entry_over": 19.5, "balls_remaining_entry": 1, "wickets_remaining_entry": 3,
            "required_rr_entry": 6.0, "rr_gap_entry": 0.0, "actual_runs": 1, "balls_faced": 1, "actual_sr": 100.0,
            "boundary_percentage": 0.0, "run_deviation": 0.2, "sr_deviation": -30.0, "opportunity_usage": 1.0,
            "dismissal_status": "not out", "balls_remaining_exit": 0, "wickets_remaining_exit": 3, "wicket_resource_change": 0,
            "required_rr_change": 6.0, "rr_gap_change": 6.0, "target_progress_change": 0.05
        },
        "expectation": "Meaningful positive contribution (>60) due to delivering match-winning victory under maximum pressure."
    },
    {
        "case_id": "CASE C",
        "title": "5* off 2, normal middle-over situation",
        "description": "Enters over 12.0 at 95/3, hits 5* off 2 deliveries (SR 250) in standard middle overs.",
        "params": {
            "innings": 1, "entry_over": 12.0, "balls_remaining_entry": 48, "wickets_remaining_entry": 7,
            "team_rr_entry": 7.5, "actual_runs": 5, "balls_faced": 2, "actual_sr": 250.0,
            "boundary_percentage": 80.0, "run_deviation": 2.5, "sr_deviation": 125.0, "opportunity_usage": 0.04,
            "dismissal_status": "not out", "balls_remaining_exit": 46, "wickets_remaining_exit": 7, "wicket_resource_change": 0,
            "expected_final_change": 3.0, "window_team_rr": 15.0, "trajectory_deviation_change": 2.5, "overs_spent": 0.3
        },
        "expectation": "Positive above-par cameo (~55-65) with high strike rate over short opportunity."
    },
    {
        "case_id": "CASE D",
        "title": "8* off 3, death overs",
        "description": "Enters over 18.2 at 155/4, scores 8* off 3 balls (SR 266.7) in high-leverage death phase.",
        "params": {
            "innings": 1, "entry_over": 18.2, "balls_remaining_entry": 10, "wickets_remaining_entry": 6,
            "team_rr_entry": 8.5, "actual_runs": 8, "balls_faced": 3, "actual_sr": 266.7,
            "boundary_percentage": 75.0, "run_deviation": 4.0, "sr_deviation": 100.0, "opportunity_usage": 0.3,
            "dismissal_status": "not out", "balls_remaining_exit": 7, "wickets_remaining_exit": 6, "wicket_resource_change": 0,
            "expected_final_change": 5.0, "window_team_rr": 16.0, "trajectory_deviation_change": 4.0, "overs_spent": 0.5
        },
        "expectation": "Strong positive contribution (>65) recognizing high death urgency and accelerated tempo."
    },
    {
        "case_id": "CASE E",
        "title": "8* off 12, team under pressure",
        "description": "Enters over 14.0 at 90/6, scores 8* off 12 balls (SR 66.7) while team needs urgent acceleration.",
        "params": {
            "innings": 1, "entry_over": 14.0, "balls_remaining_entry": 36, "wickets_remaining_entry": 4,
            "team_rr_entry": 6.5, "actual_runs": 8, "balls_faced": 12, "actual_sr": 66.7,
            "boundary_percentage": 0.0, "run_deviation": -6.0, "sr_deviation": -65.0, "opportunity_usage": 0.33,
            "dismissal_status": "not out", "balls_remaining_exit": 24, "wickets_remaining_exit": 4, "wicket_resource_change": 0,
            "expected_final_change": -4.0, "window_team_rr": 4.0, "trajectory_deviation_change": -3.0, "overs_spent": 2.0
        },
        "expectation": "Subpar contribution (30-40) due to low tempo consuming 12 valuable balls without acceleration."
    },
    {
        "case_id": "CASE F",
        "title": "30 off 5, 19th/20th over, large positive team-state impact",
        "description": "Enters over 19.1 at 160/5, hits 5 sixes (30 off 5, SR 600) to propel team from 160 to 190.",
        "params": {
            "innings": 1, "entry_over": 19.1, "balls_remaining_entry": 5, "wickets_remaining_entry": 6,
            "team_rr_entry": 8.5, "actual_runs": 30, "balls_faced": 5, "actual_sr": 600.0,
            "boundary_percentage": 100.0, "run_deviation": 18.0, "sr_deviation": 420.0, "opportunity_usage": 1.0,
            "dismissal_status": "not out", "balls_remaining_exit": 0, "wickets_remaining_exit": 6, "wicket_resource_change": 0,
            "expected_final_change": 22.0, "window_team_rr": 36.0, "trajectory_deviation_change": 20.0, "overs_spent": 0.8
        },
        "expectation": "Elite contribution score (~89.6) with strong performance recognition and large team trajectory surge."
    },
    {
        "case_id": "CASE G",
        "title": "30 off 5, early overs, large balls remaining",
        "description": "Enters over 7.1 at 75/0, scores 30 off 5 balls (SR 600) in early middle overs.",
        "params": {
            "innings": 1, "entry_over": 7.1, "balls_remaining_entry": 77, "wickets_remaining_entry": 8,
            "team_rr_entry": 7.5, "actual_runs": 30, "balls_faced": 5, "actual_sr": 600.0,
            "boundary_percentage": 100.0, "run_deviation": 18.0, "sr_deviation": 440.0, "opportunity_usage": 0.06,
            "dismissal_status": "not out", "balls_remaining_exit": 72, "wickets_remaining_exit": 8, "wicket_resource_change": 0,
            "expected_final_change": 12.0, "window_team_rr": 36.0, "trajectory_deviation_change": 10.0, "overs_spent": 0.8
        },
        "expectation": "Evaluated differently from Case F (~85.8 vs ~89.6): same explosive P2 (96.4), but lower context urgency."
    },
    {
        "case_id": "CASE H",
        "title": "5* off 3, team already scoring at a very high RR",
        "description": "Team at 180/2 at over 15.0 scoring at 12.0 RR; scores 5* off 3 balls (SR 166.7).",
        "params": {
            "innings": 1, "entry_over": 15.0, "balls_remaining_entry": 30, "wickets_remaining_entry": 8,
            "team_rr_entry": 12.0, "actual_runs": 5, "balls_faced": 3, "actual_sr": 166.7,
            "boundary_percentage": 80.0, "run_deviation": 0.5, "sr_deviation": 15.0, "opportunity_usage": 0.1,
            "dismissal_status": "not out", "balls_remaining_exit": 27, "wickets_remaining_exit": 8, "wicket_resource_change": 0,
            "expected_final_change": 1.0, "window_team_rr": 10.0, "trajectory_deviation_change": 0.0, "overs_spent": 0.5
        },
        "expectation": "Moderate score (~50-55): avoids over-hyping when team platform was already scoring rapidly."
    },
    {
        "case_id": "CASE I",
        "title": "5* off 3, team struggling with multiple wickets lost",
        "description": "Team at 28/4 at over 4.0 under acute collapse pressure; scores 5* off 3 balls (SR 166.7).",
        "params": {
            "innings": 1, "entry_over": 4.0, "balls_remaining_entry": 96, "wickets_remaining_entry": 4,
            "team_rr_entry": 5.5, "actual_runs": 5, "balls_faced": 3, "actual_sr": 166.7,
            "boundary_percentage": 80.0, "run_deviation": 1.5, "sr_deviation": 40.0, "opportunity_usage": 0.03,
            "dismissal_status": "not out", "balls_remaining_exit": 93, "wickets_remaining_exit": 4, "wicket_resource_change": 0,
            "expected_final_change": 2.0, "window_team_rr": 10.0, "trajectory_deviation_change": 1.5, "overs_spent": 0.5
        },
        "expectation": "Higher context urgency and score (~60-66) than Case H due to crisis collapse pressure."
    },
    {
        "case_id": "CASE J",
        "title": "0 balls faced, run-out/non-striker dismissal",
        "description": "Enters over 19.4 at non-striker end, run out without facing a delivery.",
        "params": {
            "innings": 1, "entry_over": 19.4, "balls_remaining_entry": 2, "wickets_remaining_entry": 4,
            "team_rr_entry": 8.5, "actual_runs": 0, "balls_faced": 0, "actual_sr": 0.0,
            "boundary_percentage": 0.0, "run_deviation": -1.0, "sr_deviation": 0.0, "opportunity_usage": 0.0,
            "dismissal_status": "out", "balls_remaining_exit": 1, "wickets_remaining_exit": 3, "wicket_resource_change": -1,
            "expected_final_change": -1.0, "window_team_rr": 0.0, "trajectory_deviation_change": -1.0, "overs_spent": 0.1
        },
        "expectation": "Genuine batting event; evaluates gracefully (~45-50) without zero-division error, definitely NOT NULL."
    }
]


def evaluate_and_save_edge_cases():
    results = []
    for ec in CRITICAL_EDGE_CASES:
        res = compute_phase5b_contribution(ec["params"])
        entry = {
            "case_id": ec["case_id"],
            "title": ec["title"],
            "description": ec["description"],
            "expectation": ec["expectation"],
            "contribution_score": res["contribution_score"],
            "raw_contribution": res["raw_contribution"],
            "pillar1_context_score": res["pillar1_context_score"],
            "pillar2_perf_score": res["pillar2_perf_score"],
            "pillar3_state_score": res["pillar3_state_score"],
            "pillar4_cf_score": res["pillar4_cf_score"],
            "dnb": res.get("dnb", False),
            "super_over": res.get("super_over", False),
        }
        results.append(entry)

    out_dir = Path("models/contribution/phase6")
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "phase6_edge_cases.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"Saved {len(results)} critical edge cases to phase6_edge_cases.json")
    return results


if __name__ == "__main__":
    evaluate_and_save_edge_cases()
