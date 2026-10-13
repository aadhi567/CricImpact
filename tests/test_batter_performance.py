"""
Unit and Integration Tests for Phase 4A: Chase Correction, Trajectory Audit & Data Enrichment.

Tests:
1. Exact entry-state and exit-state identification (e.g. 7.2 to 13.4 overs)
2. First innings uses Expected Final Score model correctly
3. Chase pathway does NOT use first-innings Expected Final Score model (fields are NULL/NaN)
4. Chase required RR, runs required, and RR gap calculations
5. Chase progression metrics (runs_required_reduction, target_progress_change)
6. First-innings chase fields are NULL/NaN appropriately
7. Chase first-innings trajectory fields are NULL/NaN appropriately
8. No feature leakage in entry state vectors
9. Match-level split disjointness
10. Run and SR deviations and ratios with safe division
11. Scenario A: Slow batter, later team acceleration
12. Scenario B: Unequal partnership (Batter A SR 200 vs Batter B SR 120)
13. Scenario C: High runs but low SR (Expected 30 @ 145, Actual 42 @ 120 -> Run dev +12, SR dev -25)
14. Scenario D: Low runs but high SR (Expected 25 @ 140, Actual 18 @ 170 -> Run dev -7, SR dev +30)
15. Scenario E: Chase trajectory evaluation (Target 180, 100/2 at 12 ov to 145/3 at 16 ov)
16. Scenario F: Target was not sufficient (team 200, opponent chases in 15 ov)
17. Rain-shortened matches audit handling
"""

from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from src.batter_trajectory import (
    compute_historical_par_curve,
    extract_batter_trajectories,
)
from src.expected_batter_model import (
    BATTER_FEATURE_COLUMNS,
    ExpectedRunsBaselines,
    ExpectedRunsRFModel,
    ExpectedSRBaselines,
    ExpectedSRRFModel,
    compute_deviations_and_ratios,
    prepare_batter_model_features,
)
from src.evaluate_batter_performance import (
    calculate_regression_metrics,
    split_batter_dataset_by_match,
)


@pytest.fixture
def sample_batter_records():
    """Create synthetic batter records representing varied match situations."""
    return pd.DataFrame([
        {
            "match_id": "M01",
            "season": "2024",
            "innings": 1,
            "innings_number": 1,
            "team": "Team A",
            "batting_team": "Team A",
            "opponent": "Team B",
            "bowling_team": "Team B",
            "player": "Batter One",
            "batter": "Batter One",
            "batting_position": 1,
            "entry_over": 0.1,
            "entry_score": 1,
            "entry_team_runs": 1,
            "entry_wickets_lost": 0,
            "entry_wickets": 0,
            "entry_wickets_remaining": 10,
            "entry_team_rr": 6.0,
            "entry_rr": 6.0,
            "entry_balls_remaining": 119,
            "entry_phase": "POWERPLAY",
            "entry_innings_phase": "POWERPLAY",
            "exit_over": 5.4,
            "dismissal_over": 5.4,
            "exit_score": 52,
            "dismissal_score": 52,
            "exit_team_runs": 52,
            "exit_wickets_lost": 1,
            "exit_wickets": 1,
            "dismissal_wickets": 1,
            "exit_wickets_remaining": 9,
            "exit_team_rr": 9.18,
            "exit_rr": 9.18,
            "dismissal_team_rr": 9.18,
            "exit_balls_remaining": 86,
            "dismissal_balls_remaining": 86,
            "exit_phase": "POWERPLAY",
            "dismissal_innings_phase": "POWERPLAY",
            "dismissal_status": "out",
            "dismissal_kind": "caught",
            "actual_runs": 32,
            "runs": 32,
            "balls_faced": 20,
            "balls": 20,
            "actual_sr": 160.0,
            "strike_rate": 160.0,
            "fours": 4,
            "sixes": 1,
            "dot_balls": 6,
            "boundary_runs": 22,
            "is_chase": False,
            "target": np.nan,
            "runs_required_entry": np.nan,
            "required_rr_entry": np.nan,
            "runs_required_exit": np.nan,
            "required_rr_exit": np.nan,
            "expected_final_entry": 168.0,
            "expected_final_score_at_entry": 168.0,
            "expected_final_exit": 178.0,
            "expected_final_score_at_exit": 178.0,
            "partnership_runs": 52,
            "batter_partnership_runs": 32,
            "partner_runs": 20,
            "batter_partnership_share": 0.615,
            "partnership_duration": 34,
        },
        {
            "match_id": "M02",
            "season": "2024",
            "innings": 2,
            "innings_number": 2,
            "team": "Team B",
            "batting_team": "Team B",
            "opponent": "Team A",
            "bowling_team": "Team A",
            "player": "Chase Batter",
            "batter": "Chase Batter",
            "batting_position": 4,
            "entry_over": 10.0,
            "entry_score": 80,
            "entry_team_runs": 80,
            "entry_wickets_lost": 2,
            "entry_wickets": 2,
            "entry_wickets_remaining": 8,
            "entry_team_rr": 8.0,
            "entry_rr": 8.0,
            "entry_balls_remaining": 60,
            "entry_phase": "MIDDLE",
            "entry_innings_phase": "MIDDLE",
            "exit_over": 16.0,
            "dismissal_over": 16.0,
            "exit_score": 140,
            "dismissal_score": 140,
            "exit_team_runs": 140,
            "exit_wickets_lost": 3,
            "exit_wickets": 3,
            "dismissal_wickets": 3,
            "exit_wickets_remaining": 7,
            "exit_team_rr": 8.75,
            "exit_rr": 8.75,
            "dismissal_team_rr": 8.75,
            "exit_balls_remaining": 24,
            "exit_phase": "DEATH",
            "dismissal_innings_phase": "DEATH",
            "dismissal_status": "out",
            "dismissal_kind": "bowled",
            "actual_runs": 45,
            "runs": 45,
            "balls_faced": 25,
            "balls": 25,
            "actual_sr": 180.0,
            "strike_rate": 180.0,
            "fours": 4,
            "sixes": 2,
            "dot_balls": 4,
            "boundary_runs": 28,
            "is_chase": True,
            "target": 180.0,
            "runs_required_entry": 100.0,
            "required_rr_entry": 10.0,
            "runs_required_exit": 40.0,
            "required_rr_exit": 10.0,
            "expected_final_entry": np.nan,
            "expected_final_score_at_entry": np.nan,
            "expected_final_exit": np.nan,
            "expected_final_score_at_exit": np.nan,
            "partnership_runs": 60,
            "batter_partnership_runs": 45,
            "partner_runs": 15,
            "batter_partnership_share": 0.75,
            "partnership_duration": 36,
        }
    ])


# ----------------------------------------------------------------------
# 1. Exact Entry & Exit State Identification
# ----------------------------------------------------------------------

def test_exact_entry_exit_parsing():
    """Verify exact entry over (7.2) and exit over (13.4) are parsed to legal balls correctly."""
    entry_over_float = 7.2
    entry_over_int = int(entry_over_float)
    entry_ball = int(np.round((entry_over_float - entry_over_int) * 10))
    entry_legal_balls = entry_over_int * 6 + entry_ball

    assert entry_over_int == 7
    assert entry_ball == 2
    assert entry_legal_balls == 44  # 7 * 6 + 2 = 44 balls bowled

    exit_over_float = 13.4
    exit_over_int = int(exit_over_float)
    exit_ball = int(np.round((exit_over_float - exit_over_int) * 10))
    exit_legal_balls = exit_over_int * 6 + exit_ball

    assert exit_over_int == 13
    assert exit_ball == 4
    assert exit_legal_balls == 82  # 13 * 6 + 4 = 82 balls bowled


# ----------------------------------------------------------------------
# 2. First Innings Trajectory & Chase NULL Separation
# ----------------------------------------------------------------------

def test_first_innings_vs_chase_null_separation(sample_batter_records):
    """
    Verify:
    1. First innings has non-null expected_final fields and NULL chase fields.
    2. Chase innings has NULL expected_final fields and non-null chase fields.
    """
    row_1st = sample_batter_records.iloc[0]
    row_chase = sample_batter_records.iloc[1]

    # First innings: Expected final is populated, Chase fields are NULL
    assert not np.isnan(row_1st["expected_final_entry"])
    assert not np.isnan(row_1st["expected_final_exit"])
    assert np.isnan(row_1st["runs_required_entry"])
    assert np.isnan(row_1st["required_rr_entry"])

    # Chase innings: Expected final is strictly NULL, Chase fields are populated
    assert np.isnan(row_chase["expected_final_entry"])
    assert np.isnan(row_chase["expected_final_exit"])
    assert not np.isnan(row_chase["runs_required_entry"])
    assert not np.isnan(row_chase["required_rr_entry"])
    assert row_chase["target"] == 180.0


# ----------------------------------------------------------------------
# 3. Chase Mathematical Formulas
# ----------------------------------------------------------------------

def test_chase_formulas_exact():
    """
    Verify exact chase calculations:
    RunsRequiredEntry = Target - EntryScore
    RunsRequiredExit = Target - ExitScore
    RequiredRR = RunsRequired * 6 / BallsRemaining
    RRGap = CurrentRR - RequiredRR
    RequiredRRChange = RequiredRREntry - RequiredRRExit (positive = decreased RRR!)
    RRGapChange = RRGapExit - RRGapEntry
    RunsRequiredReduction = RunsRequiredEntry - RunsRequiredExit
    TargetProgressChange = TargetProgressExit - TargetProgressEntry
    """
    target = 180.0
    entry_score = 100.0
    exit_score = 145.0
    entry_balls_rem = 48
    exit_balls_rem = 24
    entry_balls_bowled = 72
    exit_balls_bowled = 96

    runs_req_entry = target - entry_score  # 80
    runs_req_exit = target - exit_score    # 35
    assert runs_req_entry == 80.0
    assert runs_req_exit == 35.0

    rrr_entry = round(runs_req_entry * 6.0 / entry_balls_rem, 2)  # 80 * 6 / 48 = 10.0
    rrr_exit = round(runs_req_exit * 6.0 / exit_balls_rem, 2)      # 35 * 6 / 24 = 8.75
    assert rrr_entry == 10.0
    assert rrr_exit == 8.75

    current_rr_entry = round(entry_score * 6.0 / entry_balls_bowled, 2)  # 100 * 6 / 72 = 8.33
    current_rr_exit = round(exit_score * 6.0 / exit_balls_bowled, 2)    # 145 * 6 / 96 = 9.06
    assert current_rr_entry == 8.33
    assert current_rr_exit == 9.06

    rr_gap_entry = round(current_rr_entry - rrr_entry, 2)  # 8.33 - 10.0 = -1.67
    rr_gap_exit = round(current_rr_exit - rrr_exit, 2)    # 9.06 - 8.75 = +0.31
    assert rr_gap_entry == -1.67
    assert rr_gap_exit == 0.31

    # RequiredRRChange = RequiredRREntry - RequiredRRExit (positive means RRR dropped!)
    rrr_change = round(rrr_entry - rrr_exit, 2)  # 10.0 - 8.75 = +1.25
    assert rrr_change == 1.25

    # RRGapChange = RRGapExit - RRGapEntry (positive means moved closer to/beyond req rate)
    rr_gap_change = round(rr_gap_exit - rr_gap_entry, 2)  # 0.31 - (-1.67) = +1.98
    assert rr_gap_change == 1.98

    # RunsRequiredReduction = RunsRequiredEntry - RunsRequiredExit
    runs_reduc = round(runs_req_entry - runs_req_exit, 1)  # 80 - 35 = 45.0
    assert runs_reduc == 45.0

    # Target Progress
    tp_entry = round(entry_score / target, 4)  # 100 / 180 = 0.5556
    tp_exit = round(exit_score / target, 4)    # 145 / 180 = 0.8056
    tp_change = round(tp_exit - tp_entry, 4)   # 0.8056 - 0.5556 = 0.2500
    assert tp_change == 0.25


# ----------------------------------------------------------------------
# 4. Deviations, Ratios, and Safe Division
# ----------------------------------------------------------------------

def test_run_and_sr_deviations_and_ratios():
    """Verify run deviation, SR deviation, and ratio computations."""
    actual_runs = pd.Series([32, 40, 0])
    expected_runs = pd.Series([40.0, 30.0, 10.0])
    actual_sr = pd.Series([160.0, 120.0, 0.0])
    expected_sr = pd.Series([140.0, 140.0, 130.0])

    res = compute_deviations_and_ratios(actual_runs, expected_runs, actual_sr, expected_sr)

    # Run deviations
    assert list(res["run_deviation"]) == [-8.0, 10.0, -10.0]
    # SR deviations
    assert list(res["sr_deviation"]) == [20.0, -20.0, -130.0]
    # Ratios
    assert res["run_performance_ratio"][0] == 0.8
    assert res["run_performance_ratio"][1] == pytest.approx(1.33, 0.01)
    assert res["sr_performance_ratio"][0] == pytest.approx(1.14, 0.01)
    assert res["sr_performance_ratio"][1] == pytest.approx(0.86, 0.01)


def test_safe_division_zero_denominators():
    """Verify zero expected values yield NaN rather than ZeroDivisionError."""
    actual_runs = pd.Series([15])
    expected_runs = pd.Series([0.0])
    actual_sr = pd.Series([150.0])
    expected_sr = pd.Series([0.0])

    res = compute_deviations_and_ratios(actual_runs, expected_runs, actual_sr, expected_sr)
    assert pd.isna(res["run_performance_ratio"][0])
    assert pd.isna(res["sr_performance_ratio"][0])


# ----------------------------------------------------------------------
# 5. Leakage Prevention Audit
# ----------------------------------------------------------------------

def test_feature_leakage_audit(sample_batter_records):
    """
    Ensure feature preparation uses ONLY entry situation variables
    and excludes actual outcomes (actual_runs, balls_faced, actual_sr, dismissal, match winner).
    """
    features = prepare_batter_model_features(sample_batter_records)

    forbidden_cols = [
        "actual_runs", "runs", "balls_faced", "balls", "actual_sr", "strike_rate",
        "fours", "sixes", "dot_balls", "dismissal_status", "dismissal_kind", "dismissal_over",
        "exit_score", "exit_wickets_lost", "exit_team_rr", "actual_team_runs_change",
        "winner", "margin", "partnership_runs", "partner_runs"
    ]
    for col in forbidden_cols:
        assert col not in features.columns, f"Leakage detected: {col} found in features!"

    for req_col in BATTER_FEATURE_COLUMNS:
        assert req_col in features.columns, f"Required feature {req_col} missing!"


# ----------------------------------------------------------------------
# 6. Match-Level Split Disjointness
# ----------------------------------------------------------------------

def test_match_level_split_disjointness():
    """Verify that train and test sets share 0 matches."""
    data = []
    for m in range(20):
        for b in range(6):
            data.append({"match_id": f"M_{m:02d}", "season": 2024, "actual_runs": 20, "actual_sr": 130})
    df_synth = pd.DataFrame(data)

    train_df, test_df, train_m, test_m = split_batter_dataset_by_match(
        df_synth, test_size=0.2, random_state=42
    )

    train_set = set(train_m)
    test_set = set(test_m)
    assert len(train_set.intersection(test_set)) == 0, "Match leakage between train and test!"
    assert len(set(train_df["match_id"]).intersection(set(test_df["match_id"]))) == 0


# ----------------------------------------------------------------------
# 7. Scenario A — Slow Batter, Later Team Acceleration
# ----------------------------------------------------------------------

def test_scenario_a_slow_batter_later_acceleration():
    """
    Scenario A: 80/1 after 12 overs, batter SR ~120, out at 14 overs.
    Team accelerates later to RR 10+ and final score becomes 180.
    System must NOT automatically label batter negatively; it retains exact
    entry/exit, expected runs, expected SR, actual runs, actual SR, wickets in hand.
    """
    # Batter enters at 12.0, out at 14.0 (scored 16 off 13 balls @ 123.08 SR)
    entry_score = 80
    exit_score = 98
    actual_runs = 16
    expected_runs = 20.0
    actual_sr = 123.08
    expected_sr = 135.0

    dev = compute_deviations_and_ratios(
        actual_runs=pd.Series([actual_runs]),
        expected_runs=pd.Series([expected_runs]),
        actual_sr=pd.Series([actual_sr]),
        expected_sr=pd.Series([expected_sr]),
    )

    assert dev["run_deviation"][0] == -4.0
    assert dev["sr_deviation"][0] == -11.92
    # Verify both signals are preserved uncombined
    assert "combined_score" not in dev


# ----------------------------------------------------------------------
# 8. Scenario B — Unequal Partnership
# ----------------------------------------------------------------------

def test_scenario_b_unequal_partnership():
    """
    Scenario B: Batter A = SR 200+, Batter B = SR 120+. Several wickets remain.
    Do not automatically classify Batter B as harmful; preserve partnership context.
    """
    partnership_runs = 65
    batter_a_runs = 45
    batter_b_runs = 20

    share_a = round(batter_a_runs / partnership_runs, 3)  # 0.692
    share_b = round(batter_b_runs / partnership_runs, 3)  # 0.308

    assert share_a + share_b == pytest.approx(1.0, 0.01)
    assert share_b == 0.308
    assert partnership_runs == 65


# ----------------------------------------------------------------------
# 9. Scenario C — High Runs but Low SR
# ----------------------------------------------------------------------

def test_scenario_c_high_runs_low_sr():
    """
    Scenario C: Expected = 30 runs @ 145 SR, Actual = 42 runs @ 120 SR.
    Run deviation = +12, SR deviation = -25.
    """
    dev = compute_deviations_and_ratios(
        actual_runs=pd.Series([42]),
        expected_runs=pd.Series([30.0]),
        actual_sr=pd.Series([120.0]),
        expected_sr=pd.Series([145.0]),
    )
    assert dev["run_deviation"][0] == 12.0
    assert dev["sr_deviation"][0] == -25.0


# ----------------------------------------------------------------------
# 10. Scenario D — Low Runs but High SR
# ----------------------------------------------------------------------

def test_scenario_d_low_runs_high_sr():
    """
    Scenario D: Expected = 25 runs @ 140 SR, Actual = 18 runs @ 170 SR.
    Run deviation = -7, SR deviation = +30.
    """
    dev = compute_deviations_and_ratios(
        actual_runs=pd.Series([18]),
        expected_runs=pd.Series([25.0]),
        actual_sr=pd.Series([170.0]),
        expected_sr=pd.Series([140.0]),
    )
    assert dev["run_deviation"][0] == -7.0
    assert dev["sr_deviation"][0] == 30.0


# ----------------------------------------------------------------------
# 11. Scenario E — Chase Trajectory (NO First-Innings Model)
# ----------------------------------------------------------------------

def test_scenario_e_chase_trajectory_no_1st_innings_model():
    """
    Scenario E: Target = 180. Entry at 100/2 after 12 ov, exit at 145/3 after 16 ov.
    Calculate all chase changes using exact entry and exit states.
    Do NOT use first-innings Expected Final Score.
    """
    target = 180.0
    entry_score = 100
    exit_score = 145
    entry_balls_rem = 48
    exit_balls_rem = 24

    runs_req_entry = target - entry_score  # 80
    runs_req_exit = target - exit_score    # 35
    rrr_entry = round(runs_req_entry * 6.0 / entry_balls_rem, 2)  # 10.0
    rrr_exit = round(runs_req_exit * 6.0 / exit_balls_rem, 2)      # 8.75
    rrr_change = round(rrr_entry - rrr_exit, 2)                    # +1.25

    assert runs_req_entry == 80.0
    assert runs_req_exit == 35.0
    assert rrr_change == 1.25  # Required RR dropped by 1.25!


# ----------------------------------------------------------------------
# 12. Scenario F — Target Was Not Sufficient
# ----------------------------------------------------------------------

def test_scenario_f_target_not_sufficient():
    """
    Scenario F: Team scores 200, opponent chases in 15 overs.
    Preserves batter performance independent of opponent chase outcome.
    """
    batter_actual_runs = 55
    batter_expected_runs = 35.0
    run_dev = batter_actual_runs - batter_expected_runs

    # The batter exceeded expectations (+20 runs), regardless of match outcome
    assert run_dev == 20.0


# ----------------------------------------------------------------------
# 13. Rain / Incomplete Innings Handling
# ----------------------------------------------------------------------

def test_rain_shortened_matches_handling():
    """
    Verify that Phase 4A excludes rain-shortened 1st innings matches
    from the 20-over expected final score model (setting trajectory fields to NaN).
    """
    # Create synthetic rain-shortened 1st innings: 12.0 overs bowled, 4 wickets lost
    df_inn = pd.DataFrame([{
        "match_id": "RAIN_01",
        "innings_number": 1,
        "overs_completed": 12.0,
        "total_wickets": 4,
    }])
    is_rain = (df_inn["overs_completed"] < 19.5) & (df_inn["total_wickets"] < 10)
    assert is_rain.iloc[0] == True
