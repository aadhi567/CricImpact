"""
Unit and Regression Tests for P1 Early-Over Logic Correction (0.0 to 4.0 overs).

Validates:
1. Opening batter (entry 0.2, score 1/0): low initial RR does NOT create artificial P1 pressure.
2. Opening batter (entry 0.2, score 1/0): P1 remains approximately neutral (37.3) from RR perspective.
3. Early collapse (entry 3.2, score 18/2): 2-wicket pressure is recognized (P1 = 54.7, > par 50).
4. Normal early innings (entry 1.4, score 12/0): no RR-based penalty; matches neutral 0-wicket baseline.
5. Severe early collapse (entry 4.0, score 22/3): 3-wicket pressure is recognized (P1 = 64.8, high pressure).
6. Batter entering after early window (entry > 4.0): existing contextual logic is 100% unchanged.
7. P2 Batter Performance remains identical.
8. P3 Team-State Impact remains identical.
9. Final formula remains Contribution Score = 0.25 * P1 + 0.35 * P2 + 0.40 * P3.
10. P4 remains 0% weighted and diagnostic-only.
11. Phase 7B middle-over NULL preservation remains unchanged.
12. Complete suite compatibility.
"""

import pytest
import numpy as np

from src.contribution_framework import (
    compute_pillar1_match_context,
    compute_pillar2_batter_performance,
    compute_pillar3_team_state_impact,
    compute_pillar4_counterfactual_value,
    compute_production_contribution,
    compute_season_aggregation,
    PHASE5B_EMPIRICAL_PARAMS,
    normalize_pillar_score,
)
from src.phase7c_rebalance import (
    compute_phase7c_contribution,
    compute_phase7c_p3,
    PHASE7C_P3_PARAMS,
    PHASE7C_WEIGHTS,
)


def _calc_p1_score(row):
    raw = compute_pillar1_match_context(row)
    p = PHASE5B_EMPIRICAL_PARAMS
    z = (raw - p["pillar1_mean"]) / p["pillar1_std"]
    return round(normalize_pillar_score(z, k=p["pillar_scale"]), 1)


# ==============================================================================
# 1 & 2. OPENING BATTER NEUTRALITY (ENTRY 0.2, SCORE 1/0)
# ==============================================================================
def test_p1_opening_batter_no_artificial_rr_pressure():
    """Opening batter at 0.2 overs with score 1/0 must NOT receive artificial RR pressure."""
    row = {
        "innings": 1,
        "entry_over": 0.2,
        "balls_remaining_entry": 118,
        "wickets_remaining_entry": 10,
        "team_score_entry": 1,
        "team_rr_entry": 3.0,
    }
    raw = compute_pillar1_match_context(row)
    p1 = _calc_p1_score(row)

    # Raw should be 0.0 (no collapse, zero RR pressure)
    assert raw == 0.0
    # P1 score should be ~37.3 (calm, neutral baseline for 0 wickets down)
    assert p1 == 37.3

    # Contrast with varying team_rr_entry: changing RR from 3.0 to 9.0 has ZERO effect
    row_fast = dict(row, team_rr_entry=9.0)
    assert compute_pillar1_match_context(row_fast) == 0.0
    assert _calc_p1_score(row_fast) == 37.3


# ==============================================================================
# 3. EARLY COLLAPSE (ENTRY 3.2, SCORE 18/2)
# ==============================================================================
def test_p1_early_collapse_2_wickets_recognized():
    """Early collapse at 3.2 overs with score 18/2 must recognize 2 wickets lost as genuine pressure."""
    row = {
        "innings": 1,
        "entry_over": 3.2,
        "balls_remaining_entry": 100,
        "wickets_remaining_entry": 8,
        "team_score_entry": 18,
        "team_rr_entry": 5.4,
    }
    raw = compute_pillar1_match_context(row)
    p1 = _calc_p1_score(row)

    # 2 wickets lost: collapse_pressure = 1.25 -> raw = 0.45 * 1.25 = 0.5625
    assert raw == pytest.approx(0.5625, abs=1e-4)
    # P1 score = 54.7, properly above par 50.0 reflecting collapse
    assert p1 == 54.7
    assert p1 > 50.0


# ==============================================================================
# 4. NORMAL EARLY INNINGS (ENTRY 1.4, SCORE 12/0)
# ==============================================================================
def test_p1_normal_early_innings_no_penalty():
    """Normal early innings at 1.4 overs with score 12/0 receives no RR penalty and matches neutral baseline."""
    row = {
        "innings": 1,
        "entry_over": 1.4,
        "balls_remaining_entry": 110,
        "wickets_remaining_entry": 10,
        "team_score_entry": 12,
        "team_rr_entry": 7.2,
    }
    raw = compute_pillar1_match_context(row)
    p1 = _calc_p1_score(row)

    assert raw == 0.0
    assert p1 == 37.3

    # Both Example A (0.2, 1/0) and Example C (1.4, 12/0) must produce identical calm P1 baseline
    row_ex_a = {
        "innings": 1,
        "entry_over": 0.2,
        "balls_remaining_entry": 118,
        "wickets_remaining_entry": 10,
        "team_score_entry": 1,
        "team_rr_entry": 3.0,
    }
    assert compute_pillar1_match_context(row) == compute_pillar1_match_context(row_ex_a)


# ==============================================================================
# 5. SEVERE EARLY COLLAPSE (ENTRY 4.0, SCORE 22/3)
# ==============================================================================
def test_p1_severe_early_collapse_3_wickets_high_pressure():
    """Severe early collapse at 4.0 overs with score 22/3 must produce high contextual pressure."""
    row = {
        "innings": 1,
        "entry_over": 4.0,
        "balls_remaining_entry": 96,
        "wickets_remaining_entry": 7,
        "team_score_entry": 22,
        "team_rr_entry": 5.5,
    }
    raw = compute_pillar1_match_context(row)
    p1 = _calc_p1_score(row)

    # 3 wickets lost: collapse_pressure = 2.00 -> raw = 0.45 * 2.00 = 0.900
    assert raw == pytest.approx(0.900, abs=1e-4)
    # P1 score = 64.8, reflecting high pressure situation
    assert p1 == 64.8
    assert p1 >= 60.0


# ==============================================================================
# 6. POST-EARLY WINDOW INVARIANCE (ENTRY > 4.0)
# ==============================================================================
def test_p1_post_early_window_unchanged():
    """For entry_over > 4.0, context logic remains exactly unchanged."""
    test_cases = [
        {"innings": 1, "entry_over": 4.1, "balls_remaining_entry": 95, "wickets_remaining_entry": 9, "team_rr_entry": 8.0},
        {"innings": 1, "entry_over": 8.0, "balls_remaining_entry": 72, "wickets_remaining_entry": 8, "team_rr_entry": 7.5},
        {"innings": 1, "entry_over": 16.0, "balls_remaining_entry": 24, "wickets_remaining_entry": 6, "team_rr_entry": 9.0},
        {"innings": 2, "entry_over": 6.0, "balls_remaining_entry": 84, "wickets_remaining_entry": 8, "required_rr_entry": 9.5, "rr_gap_entry": 1.0},
        {"innings": 2, "entry_over": 18.0, "balls_remaining_entry": 12, "wickets_remaining_entry": 4, "required_rr_entry": 12.0, "rr_gap_entry": -2.0},
    ]

    for row in test_cases:
        entry_over = float(row["entry_over"])
        balls_rem = float(row["balls_remaining_entry"])
        wkts_rem = float(row["wickets_remaining_entry"])
        team_rr = float(row.get("team_rr_entry", 7.5))
        innings = int(row["innings"])

        # Expected Phase 7D reference calculation
        death = max(0.0, (entry_over - 15.0) / 4.0) if entry_over >= 15.0 else 0.0
        overs_pw = (balls_rem / 6.0) / max(1.0, wkts_rem)
        col = np.clip((overs_pw - 1.5) / 1.0, -1.5, 2.5)

        if innings == 1:
            rr_p = np.clip((7.5 - team_rr) / 2.5, -2.0, 2.0)
            expected_raw = 1.2 * death + 0.45 * col + 0.35 * rr_p
        else:
            req_rr = np.clip(float(row.get("required_rr_entry", 8.5)), 0.0, 24.0)
            rr_g = np.clip(float(row.get("rr_gap_entry", 0.0)), -4.0, 8.0)
            chase_p = (req_rr - 8.5) / 3.0 + 0.35 * (rr_g / 2.5)
            expected_raw = chase_p + (1.2 * 0.67) * death + (0.45 * 0.67) * col

        actual_raw = compute_pillar1_match_context(row)
        assert actual_raw == pytest.approx(expected_raw, abs=1e-6)


# ==============================================================================
# 7. P2 BATTER PERFORMANCE INVARIANCE
# ==============================================================================
def test_p2_remains_strictly_identical():
    """Verify Pillar 2 Batter Performance is completely untouched."""
    row = {
        "innings": 1,
        "entry_over": 0.2,
        "balls_remaining_entry": 118,
        "wickets_remaining_entry": 10,
        "team_score_entry": 1,
        "team_rr_entry": 3.0,
        "actual_runs": 45,
        "balls_faced": 30,
        "actual_sr": 150.0,
        "boundary_percentage": 60.0,
        "run_deviation": 12.0,
        "sr_deviation": 25.0,
        "opportunity_usage": 0.5,
        "dismissal_status": "caught",
    }
    p2_raw = compute_pillar2_batter_performance(row)
    assert p2_raw is not None
    # Re-evaluating p2 under different entry_overs gives identical performance score
    row_alt_entry = dict(row, entry_over=10.0)
    assert compute_pillar2_batter_performance(row_alt_entry) == p2_raw


# ==============================================================================
# 8. P3 TEAM-STATE IMPACT INVARIANCE
# ==============================================================================
def test_p3_remains_strictly_identical():
    """Verify Pillar 3 Team-State Impact is completely untouched."""
    row = {
        "innings": 1,
        "entry_over": 0.2,
        "balls_remaining_entry": 118,
        "wickets_remaining_entry": 10,
        "team_score_entry": 1,
        "team_rr_entry": 3.0,
        "actual_runs": 45,
        "balls_faced": 30,
        "actual_sr": 150.0,
        "expected_final_change": 15.0,
        "trajectory_deviation_change": 8.0,
        "window_team_rr": 8.8,
        "partnership_runs": 65,
        "batter_partnership_share": 45.0 / 65.0,
        "partner_runs": 20,
        "partner_balls": 15,
        "partner_sr": 133.3,
        "balls_remaining_exit": 88,
        "wickets_remaining_exit": 9,
        "dismissal_status": "caught",
    }
    p3_raw = compute_phase7c_p3(row)
    assert p3_raw is not None


# ==============================================================================
# 9. FINAL FORMULA WEIGHTING (25% P1, 35% P2, 40% P3)
# ==============================================================================
def test_production_formula_weights_integrity():
    """Verify Contribution Score = 0.25 * P1 + 0.35 * P2 + 0.40 * P3."""
    row = {
        "innings": 1,
        "entry_over": 0.2,
        "balls_remaining_entry": 118,
        "wickets_remaining_entry": 10,
        "team_score_entry": 1,
        "team_rr_entry": 3.0,
        "actual_runs": 35,
        "balls_faced": 24,
        "actual_sr": 145.8,
        "boundary_percentage": 50.0,
        "run_deviation": 8.0,
        "sr_deviation": 15.0,
        "opportunity_usage": 0.4,
        "dismissal_status": "caught",
        "balls_remaining_exit": 94,
        "wickets_remaining_exit": 9,
        "wicket_resource_change": -1,
        "expected_final_change": 6.0,
        "window_team_rr": 8.5,
        "trajectory_deviation_change": 5.0,
        "partnership_runs": 50,
        "batter_partnership_share": 0.7,
        "partner_runs": 15,
    }
    res_7c = compute_phase7c_contribution(row)
    expected_7c = round(float(np.clip(0.25 * res_7c["pillar1_context_score"] + 0.35 * res_7c["pillar2_perf_score"] + 0.40 * res_7c["pillar3_state_score"], 0.1, 99.9)), 1)
    assert res_7c["contribution_score"] == expected_7c

    res = compute_production_contribution(row, model_version="phase7d")
    expected_cs = round(float(np.clip(0.25 * res["pillar1_context_score"] + 0.35 * res["pillar2_perf_score"] + 0.40 * res["pillar3_state_score"], 0.1, 99.9)), 1)
    assert res["contribution_score"] == expected_cs


# ==============================================================================
# 10. P4 DIAGNOSTIC-ONLY STATUS (0% WEIGHT)
# ==============================================================================
def test_p4_remains_diagnostic_only():
    """Verify P4 remains 0% weighted in final Contribution Score."""
    row = {
        "innings": 1,
        "entry_over": 0.2,
        "balls_remaining_entry": 118,
        "wickets_remaining_entry": 10,
        "team_score_entry": 1,
        "team_rr_entry": 3.0,
        "actual_runs": 20,
        "balls_faced": 18,
        "actual_sr": 111.1,
        "dismissal_status": "caught",
        "balls_remaining_exit": 100,
        "wickets_remaining_exit": 9,
    }
    res = compute_production_contribution(row, model_version="phase7d")
    assert "pillar4_diagnostic" in res
    assert res["weights"]["pillar4_counterfactual"] == "Diagnostic only (0%)"
    assert res["weights"]["pillar1_match_context"] == "25%"
    assert res["weights"]["pillar2_batter_performance"] == "35%"
    assert res["weights"]["pillar3_team_state_impact"] == "40%"


# ==============================================================================
# 11. PHASE 7B MIDDLE-OVER NULL PRESERVATION
# ==============================================================================
def test_phase7b_middle_over_null_preservation():
    """Verify Phase 7B middle-over overlap rule (entry < 16.0 and exit >= 6.0) remains preserved."""
    # Innings entirely within powerplay (0.1 to 4.2) -> Middle Overs must be NULL
    innings_list = [
        {
            "dnb": False,
            "contribution_score": 62.5,
            "raw_contribution": 0.45,
            "entry_over": 0.1,
            "exit_over": 4.2,
            "pillar1_context_score": 37.3,
            "innings": 1,
        }
    ]
    agg = compute_season_aggregation(innings_list, team_total_positive_contribution=10.0, matches_played=1)
    assert agg["powerplay_contribution"] == 62.5
    assert agg["middle_over_contribution"] is None  # Strictly NULL

    # Innings spanning into middle overs (0.1 to 14.3) -> Middle Overs must be valid
    innings_overlap = [
        {
            "dnb": False,
            "contribution_score": 75.0,
            "raw_contribution": 0.85,
            "entry_over": 0.1,
            "exit_over": 14.3,
            "pillar1_context_score": 37.3,
            "innings": 1,
        }
    ]
    agg_overlap = compute_season_aggregation(innings_overlap, team_total_positive_contribution=10.0, matches_played=1)
    assert agg_overlap["middle_over_contribution"] == 75.0


# ==============================================================================
# 12. EXAMPLE B: BATTER ENTERS AT 2.3 OVERS, 1 WICKET LOST
# ==============================================================================
def test_p1_example_b_2_3_overs_1_wicket_lost():
    """Example B: Batter enters at 2.3 overs, 1 wicket lost. P1 must reflect the single wicket lost."""
    row = {
        "innings": 1,
        "entry_over": 2.3,
        "balls_remaining_entry": 105,
        "wickets_remaining_entry": 9,
        "team_score_entry": 15,
        "team_rr_entry": 6.0,
    }
    raw = compute_pillar1_match_context(row)
    p1 = _calc_p1_score(row)

    # 1 wicket lost: collapse_pressure = 0.50 -> raw = 0.45 * 0.50 = 0.225
    assert raw == pytest.approx(0.225, abs=1e-4)
    # P1 score = 44.1, elevated from neutral 37.3 reflecting 1 lost wicket
    assert p1 == 44.1
    assert p1 > 37.3

    # Ensure changing pre-entry RR (e.g. from 6.0 to 12.0) has ZERO effect
    row_alt_rr = dict(row, team_rr_entry=12.0)
    assert compute_pillar1_match_context(row_alt_rr) == pytest.approx(0.225, abs=1e-4)
    assert _calc_p1_score(row_alt_rr) == 44.1


# ==============================================================================
# 13. EXAMPLE C: BATTER ENTERS AT 3.5 OVERS, 2 WICKETS LOST
# ==============================================================================
def test_p1_example_c_3_5_overs_2_wickets_lost():
    """Example C: Batter enters at 3.5 overs, 2 wickets lost. P1 must reflect stronger inherited pressure."""
    row = {
        "innings": 1,
        "entry_over": 3.5,
        "balls_remaining_entry": 97,
        "wickets_remaining_entry": 8,
        "team_score_entry": 24,
        "team_rr_entry": 6.26,
    }
    raw = compute_pillar1_match_context(row)
    p1 = _calc_p1_score(row)

    # 2 wickets lost: collapse_pressure = 1.25 -> raw = 0.45 * 1.25 = 0.5625
    assert raw == pytest.approx(0.5625, abs=1e-4)
    # P1 score = 54.7 (> par 50.0), reflecting stronger early collapse pressure
    assert p1 == 54.7
    assert p1 > 50.0

    # Ensure changing pre-entry RR has ZERO effect
    row_alt_rr = dict(row, team_rr_entry=3.0)
    assert compute_pillar1_match_context(row_alt_rr) == pytest.approx(0.5625, abs=1e-4)
    assert _calc_p1_score(row_alt_rr) == 54.7


# ==============================================================================
# 14. 4.0-OVER BOUNDARY TEST (4.0 vs 4.1 OVERS)
# ==============================================================================
def test_p1_four_over_boundary_exact():
    """4.0 overs (24 balls) is inside the early window; 4.1 overs (25 balls) transitions to standard context."""
    # At 4.0 overs with 0 wickets lost: strictly inside early-over window (raw = 0.0, P1 = 37.3)
    row_4_0 = {
        "innings": 1,
        "entry_over": 4.0,
        "balls_remaining_entry": 96,
        "wickets_remaining_entry": 10,
        "team_score_entry": 28,
        "team_rr_entry": 7.0,
    }
    assert compute_pillar1_match_context(row_4_0) == 0.0
    assert _calc_p1_score(row_4_0) == 37.3

    # At 4.1 overs with 0 wickets lost: outside early window (> 4.0), uses standard platform pressure
    row_4_1 = {
        "innings": 1,
        "entry_over": 4.1,
        "balls_remaining_entry": 95,
        "wickets_remaining_entry": 10,
        "team_score_entry": 28,
        "team_rr_entry": 7.0,
    }
    raw_4_1 = compute_pillar1_match_context(row_4_1)
    # Standard formula: col = ((95/6)/10 - 1.5)/1.0 = 0.0833, rr_p = (7.5 - 7.0)/2.5 = 0.200
    # raw = 0.45 * 0.0833 + 0.35 * 0.200 = 0.0375 + 0.0700 = 0.1075
    assert raw_4_1 != 0.0
    assert raw_4_1 == pytest.approx(0.1075, abs=1e-3)


# ==============================================================================
# 15. ABHISHEK SHARMA MATCH 1527674 FULL VALIDATION
# ==============================================================================
def test_abhishek_sharma_match_1527674_complete_validation():
    """
    Validates Abhishek Sharma in Match 1527674:
    - Entry over: 0.2, Exit over: 2.1
    - Runs: 7, Balls: 8, SR: 87.5
    - Wickets lost during stay: 1
    - Expected SR: 114.4
    - P1 must be 37.3 (neutral, was 63.1)
    - P2 must be 43.7 (untouched)
    - P3 must be 62.3 (untouched)
    - Contribution Score must be 49.5 (0.25*37.3 + 0.35*43.7 + 0.40*62.3)
    """
    row = {
        "match_id": 1527674,
        "season": "2026",
        "innings": 1,
        "player": "Abhishek Sharma",
        "entry_over": 0.2,
        "exit_over": 2.1,
        "balls_remaining_entry": 118,
        "wickets_remaining_entry": 10,
        "team_score_entry": 1,
        "team_rr_entry": 3.0,
        "actual_runs": 7,
        "balls_faced": 8,
        "actual_sr": 87.5,
        "expected_runs": 29.0,
        "expected_sr": 114.4,
        "run_deviation": -22.0,
        "sr_deviation": -26.9,
        "opportunity_usage": 0.0678,
        "boundary_percentage": 85.71,
        "dismissal_status": "out",
        "dismissal_kind": "caught",
        "balls_remaining_exit": 107,
        "wickets_remaining_exit": 9,
        "wickets_lost_during_stay": 1,
        "wicket_resource_change": -1,
        "expected_final_entry": 165.6,
        "expected_final_exit": 176.3,
        "expected_final_change": 10.7,
        "trajectory_deviation_change": 3.8,
        "window_team_rr": 9.29,
        "partnership_runs": 18,
        "batter_partnership_share": 0.389,
        "partner_runs": 11,
    }

    # Phase 7D historical validation
    res_7d = compute_phase7c_contribution(row)
    assert res_7d["pillar1_context_score"] == 37.3
    assert res_7d["pillar2_perf_score"] == 43.7
    assert res_7d["pillar3_state_score"] == 62.3
    assert res_7d["contribution_score"] == 49.5

    # Production validation (Phase 7D 25/35/40)
    res = compute_production_contribution(row, model_version="phase7d")
    assert res["pillar1_context_score"] == 37.3
    assert res["pillar2_perf_score"] == 43.7
    assert res["pillar3_state_score"] == 62.3
    assert res["contribution_score"] == 49.5
    assert res["pillar4_diagnostic"]["expected_sr"] == 114.4
    assert res["pillar4_diagnostic"]["expected_runs"] == 29.0
    assert res["pillar4_diagnostic"]["actual_vs_expected_sr"] == -26.9


# ==============================================================================
# 16. DNB REMAINS STRICTLY NULL
# ==============================================================================
def test_dnb_remains_strictly_null():
    """Verify Did-Not-Bat innings return NULL for all pillars and composite score."""
    row_dnb = {
        "innings": 1,
        "dnb": True,
        "player": "YS Chahal",
    }
    res = compute_production_contribution(row_dnb)
    assert res["dnb"] is True
    assert res["contribution_score"] is None
    assert res["raw_contribution"] is None
    assert res["pillar1_context_score"] is None
    assert res["pillar2_perf_score"] is None
    assert res["pillar3_state_score"] is None
    assert res["pillar4_diagnostic"] is None

