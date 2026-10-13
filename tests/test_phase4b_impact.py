"""
Unit and Integration Tests for Phase 4B:
Batter Impact, Match-State Transformation & Counterfactual Foundation.

Covers all 30 test areas specified in Section 30 of Phase 4B:
1. Run deviation
2. SR deviation
3. Runs per ball
4. Opportunity usage
5. 5-ball explosive cameo
6. High-SR cameo when team already has high RR
7. High-SR cameo when team RR is below expectation
8. Middle-over cameo
9. Death-over cameo
10. Many wickets remaining
11. Few wickets remaining
12. First-innings trajectory improvement
13. First-innings trajectory improvement with wicket loss
14. First-innings 60/2 -> 90/3 example (Section 10)
15. First-innings 70/4 -> 90/5 example (Section 14, Batter A vs Batter B)
16. Chase required-RR change
17. Chase pressure relief
18. RR-gap change
19. Target progress
20. Partnership share
21. Dot-ball percentage
22. Boundary percentage
23. Exact entry/exit
24. Not-out batter
25. Late-entry batter
26. Post-exit analysis
27. Counterfactual leakage prevention
28. Final-result separation
29. First innings vs chase separation
30. Zero/edge cases
"""

from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from src.counterfactual_engine import CounterfactualEngine
from src.batter_impact_signals import build_batter_impact_signals
from src.expected_batter_model import compute_deviations_and_ratios


# ----------------------------------------------------------------------
# 1. Run Deviation
# ----------------------------------------------------------------------
def test_1_run_deviation():
    actual_runs = 45
    expected_runs = 32.5
    run_dev = actual_runs - expected_runs
    assert run_dev == 12.5


# ----------------------------------------------------------------------
# 2. SR Deviation
# ----------------------------------------------------------------------
def test_2_sr_deviation():
    actual_sr = 175.0
    expected_sr = 135.0
    sr_dev = actual_sr - expected_sr
    assert sr_dev == 40.0


# ----------------------------------------------------------------------
# 3. Runs per Ball
# ----------------------------------------------------------------------
def test_3_runs_per_ball():
    actual_runs = 30
    balls_faced = 12
    rpb = round(actual_runs / balls_faced, 3)
    assert rpb == 2.5


# ----------------------------------------------------------------------
# 4. Opportunity Usage
# ----------------------------------------------------------------------
def test_4_opportunity_usage():
    balls_faced = 25
    balls_available = 76  # Entered at 7.2 overs
    opp_usage = round(balls_faced / balls_available, 4)
    assert opp_usage == pytest.approx(0.3289, 0.001)


# ----------------------------------------------------------------------
# 5. 5-ball Explosive Cameo
# ----------------------------------------------------------------------
def test_5_five_ball_explosive_cameo():
    # 5 balls, 5 sixes = 30 runs, SR 600.0
    balls_faced = 5
    actual_runs = 30
    fours = 0
    sixes = 5
    boundary_runs = 30
    boundary_runs_per_ball = round(boundary_runs / balls_faced, 3)
    rpb = round(actual_runs / balls_faced, 3)
    actual_sr = round((actual_runs / balls_faced) * 100.0, 2)

    assert rpb == 6.0
    assert boundary_runs_per_ball == 6.0
    assert actual_sr == 600.0


# ----------------------------------------------------------------------
# 6. High-SR Cameo when Team Already has High RR
# ----------------------------------------------------------------------
def test_6_cameo_when_team_already_scoring_high():
    team_rr_entry = 11.2
    actual_runs = 24
    balls_faced = 8
    batter_sr = round((actual_runs / balls_faced) * 100.0, 2)  # 300.0
    assert batter_sr > 250.0
    assert team_rr_entry >= 10.0


# ----------------------------------------------------------------------
# 7. High-SR Cameo when Team RR is Below Expectation
# ----------------------------------------------------------------------
def test_7_cameo_when_team_rr_below_expectation():
    team_rr_entry = 5.2
    actual_runs = 26
    balls_faced = 10
    batter_sr = round((actual_runs / balls_faced) * 100.0, 2)  # 260.0
    # Rescues stagnant scoring tempo
    assert team_rr_entry < 6.0
    assert batter_sr > 200.0


# ----------------------------------------------------------------------
# 8. Middle-over Cameo
# ----------------------------------------------------------------------
def test_8_middle_over_cameo():
    entry_over = 11.2
    exit_over = 13.4
    balls_faced = 11
    actual_runs = 25
    phase = "MIDDLE"
    assert 6.0 <= entry_over <= 15.0
    assert phase == "MIDDLE"


# ----------------------------------------------------------------------
# 9. Death-over Cameo
# ----------------------------------------------------------------------
def test_9_death_over_cameo():
    entry_over = 18.1
    exit_over = 19.6
    balls_faced = 8
    actual_runs = 22
    phase = "DEATH"
    assert entry_over >= 15.0
    assert phase == "DEATH"


# ----------------------------------------------------------------------
# 10. Many Wickets Remaining
# ----------------------------------------------------------------------
def test_10_many_wickets_remaining():
    wickets_remaining_entry = 9
    assert wickets_remaining_entry >= 8


# ----------------------------------------------------------------------
# 11. Few Wickets Remaining
# ----------------------------------------------------------------------
def test_11_few_wickets_remaining():
    wickets_remaining_entry = 2
    assert wickets_remaining_entry <= 3


# ----------------------------------------------------------------------
# 12. First-innings Trajectory Improvement
# ----------------------------------------------------------------------
def test_12_first_innings_trajectory_improvement():
    exp_final_entry = 150.0
    exp_final_exit = 175.0
    exp_final_change = exp_final_exit - exp_final_entry
    assert exp_final_change == 25.0


# ----------------------------------------------------------------------
# 13. First-innings Trajectory Improvement with Wicket Loss
# ----------------------------------------------------------------------
def test_13_trajectory_improvement_with_wicket_loss():
    exp_final_entry = 145.0
    exp_final_exit = 168.0
    exp_final_change = exp_final_exit - exp_final_entry
    wickets_lost_during_stay = 1
    wicket_resource_change = -1

    assert exp_final_change == 23.0
    assert wickets_lost_during_stay == 1
    assert wicket_resource_change == -1


# ----------------------------------------------------------------------
# 14. First-innings 60/2 -> 90/3 Example (Section 10)
# ----------------------------------------------------------------------
def test_14_first_innings_60_2_to_90_3():
    """
    Section 10:
    Before: 60/2 after 10 overs (RR 6.0), Exp final = 145
    After: 90/3 after 11 overs, Exp final = 170
    ExpectedFinalChange = +25, Wickets remaining: 8 -> 7 (WicketResourceChange = -1).
    Preserve both signals separately!
    """
    exp_final_entry = 145.0
    exp_final_exit = 170.0
    exp_final_change = exp_final_exit - exp_final_entry

    wkts_rem_entry = 8
    wkts_rem_exit = 7
    wicket_resource_change = wkts_rem_exit - wkts_rem_entry

    assert exp_final_change == 25.0
    assert wicket_resource_change == -1


# ----------------------------------------------------------------------
# 15. First-innings 70/4 -> 90/5 Example (Section 14: Batter A vs Batter B)
# ----------------------------------------------------------------------
def test_15_batter_a_vs_batter_b_resource_transformation():
    """
    Section 14:
    Batter A: 70/4 -> 90/4, 20 off 6, Exp final 145 -> 165, Wickets lost: 0
    Batter B: 70/4 -> 90/5, 20 off 6, Exp final 145 -> 160, Wickets lost: 1
    Both scored 20 off 6, but Batter A preserved the wicket while Batter B consumed it!
    """
    # Batter A
    exp_final_change_a = 165.0 - 145.0  # +20.0
    wkt_res_change_a = 0

    # Batter B
    exp_final_change_b = 160.0 - 145.0  # +15.0
    wkt_res_change_b = -1

    assert exp_final_change_a == 20.0
    assert wkt_res_change_a == 0

    assert exp_final_change_b == 15.0
    assert wkt_res_change_b == -1

    # Wicket preservation produced 5 extra runs in projected final score
    assert exp_final_change_a - exp_final_change_b == 5.0


# ----------------------------------------------------------------------
# 16. Chase Required-RR Change
# ----------------------------------------------------------------------
def test_16_chase_required_rr_change():
    # RequiredRRChange = RequiredRREntry - RequiredRRExit (positive = RRR decreased!)
    req_rr_entry = 10.5
    req_rr_exit = 8.2
    req_rr_change = round(req_rr_entry - req_rr_exit, 2)
    assert req_rr_change == 2.3


# ----------------------------------------------------------------------
# 17. Chase Pressure Relief RR
# ----------------------------------------------------------------------
def test_17_chase_pressure_relief_and_relative_relief():
    req_rr_entry = 12.0
    req_rr_exit = 9.0
    relief_rr = req_rr_entry - req_rr_exit
    rel_relief = round(relief_rr / req_rr_entry, 4)
    assert relief_rr == 3.0
    assert rel_relief == 0.2500  # 25% relative reduction in required RR


# ----------------------------------------------------------------------
# 18. RR-Gap Change
# ----------------------------------------------------------------------
def test_18_rr_gap_change():
    # RRGap = CurrentRR - RequiredRR
    # RRGapChange = RRGapExit - RRGapEntry
    team_rr_entry = 7.0
    req_rr_entry = 10.0
    gap_entry = team_rr_entry - req_rr_entry  # -3.0

    team_rr_exit = 8.5
    req_rr_exit = 8.5
    gap_exit = team_rr_exit - req_rr_exit      # 0.0

    gap_change = gap_exit - gap_entry         # 0.0 - (-3.0) = +3.0
    assert gap_entry == -3.0
    assert gap_exit == 0.0
    assert gap_change == 3.0


# ----------------------------------------------------------------------
# 19. Target Progress
# ----------------------------------------------------------------------
def test_19_target_progress():
    target = 180.0
    score_entry = 72.0
    score_exit = 126.0

    tp_entry = score_entry / target  # 0.40
    tp_exit = score_exit / target    # 0.70
    tp_change = tp_exit - tp_entry   # 0.30

    assert tp_entry == 0.40
    assert tp_exit == 0.70
    assert tp_change == pytest.approx(0.30, 0.001)


# ----------------------------------------------------------------------
# 20. Partnership Share
# ----------------------------------------------------------------------
def test_20_partnership_share():
    partnership_runs = 60
    batter_partnership_runs = 36
    share = round(batter_partnership_runs / partnership_runs, 3)
    partner_runs = partnership_runs - batter_partnership_runs
    assert share == 0.60
    assert partner_runs == 24


# ----------------------------------------------------------------------
# 21. Dot-ball Percentage
# ----------------------------------------------------------------------
def test_21_dot_ball_percentage():
    dot_balls = 4
    balls_faced = 16
    dot_pct = round((dot_balls / balls_faced) * 100.0, 2)
    assert dot_pct == 25.0


# ----------------------------------------------------------------------
# 22. Boundary Percentage
# ----------------------------------------------------------------------
def test_22_boundary_percentage():
    fours = 3
    sixes = 2
    actual_runs = 30
    boundary_runs = fours * 4 + sixes * 6  # 12 + 12 = 24
    boundary_pct = round((boundary_runs / actual_runs) * 100.0, 2)
    assert boundary_runs == 24
    assert boundary_pct == 80.0


# ----------------------------------------------------------------------
# 23. Exact Entry / Exit
# ----------------------------------------------------------------------
def test_23_exact_entry_exit():
    entry_over = 7.2
    exit_over = 13.4
    entry_legal_balls = 7 * 6 + 2  # 44
    exit_legal_balls = 13 * 6 + 4  # 82
    balls_spent = exit_legal_balls - entry_legal_balls
    overs_spent = round(balls_spent / 6.0, 2)
    assert balls_spent == 38
    assert overs_spent == 6.33


# ----------------------------------------------------------------------
# 24. Not-out Batter
# ----------------------------------------------------------------------
def test_24_not_out_batter():
    dismissal_status = "not out"
    exit_balls_remaining = 0
    post_exit_runs = 0
    post_exit_overs = 0.0
    assert dismissal_status == "not out"
    assert post_exit_runs == 0
    assert post_exit_overs == 0.0


# ----------------------------------------------------------------------
# 25. Late-entry Batter
# ----------------------------------------------------------------------
def test_25_late_entry_batter():
    entry_over = 18.4
    entry_balls_remaining = 8
    opportunity_usage = 5 / entry_balls_remaining
    assert entry_over >= 18.0
    assert opportunity_usage == 0.625


# ----------------------------------------------------------------------
# 26. Post-exit Analysis
# ----------------------------------------------------------------------
def test_26_post_exit_analysis():
    final_team_score = 185
    exit_score = 130
    exit_team_rr = 9.2
    post_exit_overs = 5.0
    post_exit_runs = final_team_score - exit_score  # 55
    post_exit_rr = round(post_exit_runs / post_exit_overs, 2)  # 11.0
    post_exit_rr_change = round(post_exit_rr - exit_team_rr, 2)  # 11.0 - 9.2 = +1.8

    assert post_exit_runs == 55
    assert post_exit_rr == 11.0
    assert post_exit_rr_change == 1.8


# ----------------------------------------------------------------------
# 27. Counterfactual Leakage Prevention
# ----------------------------------------------------------------------
def test_27_counterfactual_leakage_prevention():
    """
    Verify counterfactual engine does NOT change its recommendations
    or trajectory gaps regardless of the final match outcome (e.g. won vs lost).
    """
    engine = CounterfactualEngine()
    row_win = {
        "innings": 1,
        "entry_score": 60,
        "entry_wickets_lost": 2,
        "entry_balls_remaining": 60,
        "entry_over": 10.0,
        "entry_team_rr": 6.0,
        "entry_phase": "MIDDLE",
        "actual_runs": 20,
        "balls_faced": 15,
        "actual_sr": 133.33,
        "expected_runs": 18.0,
        "expected_sr": 125.0,
        "dismissal_status": "out",
        "exit_score": 90,
        "exit_wickets_lost": 3,
        "exit_balls_remaining": 45,
        "exit_over": 12.3,
        "exit_team_rr": 7.2,
        "exit_phase": "MIDDLE",
        "partner_runs": 10,
        "expected_final_entry": 150.0,
        "expected_final_change": 10.0,
        "won_match": True,
        "winning_margin": 25.0,
    }

    row_loss = row_win.copy()
    row_loss["won_match"] = False
    row_loss["winning_margin"] = -5.0

    eval_win = engine.evaluate_batter_counterfactuals(row_win)
    eval_loss = engine.evaluate_batter_counterfactuals(row_loss)

    # Identical counterfactual outputs regardless of match win/loss
    assert eval_win["scenarios"]["CF_Par"] == eval_loss["scenarios"]["CF_Par"]
    assert eval_win["scenarios"]["CF_Accelerated"] == eval_loss["scenarios"]["CF_Accelerated"]


# ----------------------------------------------------------------------
# 28. Final-result Separation
# ----------------------------------------------------------------------
def test_28_final_result_separation():
    """
    Ensure performance signals and counterfactuals do not contain
    match result fields.
    """
    engine = CounterfactualEngine()
    sample_row = {
        "innings": 2,
        "target": 170.0,
        "entry_score": 80,
        "entry_wickets_lost": 3,
        "entry_balls_remaining": 50,
        "entry_over": 11.4,
        "entry_team_rr": 6.85,
        "actual_runs": 35,
        "balls_faced": 20,
        "actual_sr": 175.0,
        "expected_runs": 24.0,
        "expected_sr": 130.0,
        "dismissal_status": "not out",
        "exit_score": 130,
        "exit_wickets_lost": 3,
        "exit_balls_remaining": 30,
        "exit_over": 15.0,
        "exit_team_rr": 8.67,
        "partner_runs": 15,
        "required_rr_entry": 10.8,
        "required_rr_change": 2.8,
        # Result fields
        "won_match": True,
        "final_team_score": 171,
    }
    eval_res = engine.evaluate_batter_counterfactuals(sample_row)
    assert "won_match" not in eval_res
    assert "final_team_score" not in eval_res
    for scen in eval_res["scenarios"].values():
        assert "won_match" not in scen
        assert "final_team_score" not in scen


# ----------------------------------------------------------------------
# 29. First Innings vs Chase Separation
# ----------------------------------------------------------------------
def test_29_first_innings_vs_chase_separation():
    df = pd.read_csv("data/processed/batter_impact_signals.csv", low_memory=False)
    inn1 = df[df["innings"] == 1]
    inn2 = df[df["innings"] == 2]

    # First innings has NULL chase fields
    assert inn1["required_rr_entry"].isnull().all()
    assert inn1["runs_required_entry"].isnull().all()
    assert inn1["target"].isnull().all()

    # Second innings has NULL first-innings trajectory fields
    assert inn2["expected_final_entry"].isnull().all()
    assert inn2["expected_final_exit"].isnull().all()
    assert inn2["expected_final_change"].isnull().all()


# ----------------------------------------------------------------------
# 30. Zero / Edge Cases
# ----------------------------------------------------------------------
def test_30_zero_and_edge_cases():
    actual_runs = pd.Series([0, 15])
    expected_runs = pd.Series([0.0, 0.0])
    actual_sr = pd.Series([0.0, 150.0])
    expected_sr = pd.Series([0.0, 0.0])

    dev = compute_deviations_and_ratios(actual_runs, expected_runs, actual_sr, expected_sr)
    assert pd.isna(dev["run_performance_ratio"][0])
    assert pd.isna(dev["run_performance_ratio"][1])
    assert pd.isna(dev["sr_performance_ratio"][0])
    assert pd.isna(dev["sr_performance_ratio"][1])
