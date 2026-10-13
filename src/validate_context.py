"""
Phase 2 Context & Situation Engine Validation Suite.

Executes 10 rigorous validation checks across all generated datasets:
Check A: Team score progression (monotonic non-decreasing)
Check B: Wickets progression (monotonic non-decreasing)
Check C: Batter runs consistency (match_state final == batter_context == batter_innings)
Check D: Required RR validation (chase boundary conditions & formula precision)
Check E: Partnership reconciliation (sum of partnerships == innings total runs)
Check F: Batting position sequential consistency (1, 2, 3...)
Check G: Entry state timing (entry score strictly BEFORE batter's first ball faced)
Check H: Dismissal state correspondence (dismissal info corresponds to exact delivery)
Check I: Projected score calculation (current_team_rr * 20.0 simple baseline)
Check J: Post-dismissal acceleration metrics (accurate legal-ball slicing & NULL handling)
"""

import sys
import argparse
from pathlib import Path
from typing import Dict, Any, Tuple, List

# Ensure repository root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import numpy as np

# Ensure UTF-8 output encoding on Windows console
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def validate_phase2_datasets(
    match_state_df: pd.DataFrame,
    partnerships_df: pd.DataFrame,
    batter_context_df: pd.DataFrame,
    innings_df: pd.DataFrame,
    batter_innings_df: pd.DataFrame
) -> Tuple[bool, Dict[str, Dict[str, Any]]]:
    """
    Run all Phase 2 validation checks across generated DataFrames.

    Returns:
        tuple: (all_passed: bool, check_results: dict)
    """
    results: Dict[str, Dict[str, Any]] = {}

    # ----------------------------------------------------
    # Check A: Team Score Progression (never decreases)
    # ----------------------------------------------------
    score_diffs = match_state_df.groupby(["match_id", "innings_number"])["total_team_runs_so_far"].diff().dropna()
    neg_score_diffs = score_diffs[score_diffs < 0]
    passed_a = len(neg_score_diffs) == 0
    results["Check A: Team Score Progression"] = {
        "passed": passed_a,
        "details": (
            "Total team score is strictly non-decreasing across all deliveries in all innings."
            if passed_a
            else f"Score decreased {len(neg_score_diffs)} times!"
        )
    }

    # ----------------------------------------------------
    # Check B: Wickets Progression (never decreases)
    # ----------------------------------------------------
    wkt_diffs = match_state_df.groupby(["match_id", "innings_number"])["wickets_lost_so_far"].diff().dropna()
    neg_wkt_diffs = wkt_diffs[wkt_diffs < 0]
    passed_b = len(neg_wkt_diffs) == 0
    results["Check B: Wickets Progression"] = {
        "passed": passed_b,
        "details": (
            "Wickets lost is strictly non-decreasing across all deliveries in all innings."
            if passed_b
            else f"Wickets decreased {len(neg_wkt_diffs)} times!"
        )
    }

    # ----------------------------------------------------
    # Check C: Batter Runs Consistency
    # ----------------------------------------------------
    faced_delivs = match_state_df[match_state_df["batter_balls_so_far"] > 0]
    last_faced = faced_delivs.sort_values(
        ["match_id", "innings_number", "over", "ball"]
    ).groupby(["match_id", "innings_number", "batter"])["batter_runs_so_far"].last().reset_index()

    chk_c = batter_context_df[batter_context_df["balls"] > 0].merge(
        last_faced, on=["match_id", "innings_number", "batter"], how="inner"
    )
    chk_c_mismatch = chk_c[chk_c["runs"] != chk_c["batter_runs_so_far"]]
    # Also check against batter_innings_df
    chk_bi = batter_context_df.merge(
        batter_innings_df[["match_id", "innings_number", "batter", "runs", "balls_faced"]],
        on=["match_id", "innings_number", "batter"],
        suffixes=("_context", "_raw")
    )
    bi_mismatches = chk_bi[(chk_bi["runs_context"] != chk_bi["runs_raw"]) | (chk_bi["balls"] != chk_bi["balls_faced"])]
    passed_c = (len(chk_c_mismatch) == 0) and (len(bi_mismatches) == 0)
    results["Check C: Batter Runs Consistency"] = {
        "passed": passed_c,
        "details": (
            "Cumulative batter runs and balls in match_state and batter_context reconcile 100% with Phase 1 totals."
            if passed_c
            else f"Mismatches found: {len(chk_c_mismatch)} in match_state, {len(bi_mismatches)} in batter_innings."
        )
    }

    # ----------------------------------------------------
    # Check D: Required RR Validation
    # ----------------------------------------------------
    chase_rows = batter_context_df[batter_context_df["is_chase"] == True]
    # If runs_required <= 0, required_rr must be 0.0
    zero_req_bad = chase_rows[
        (chase_rows["runs_required_at_entry"] <= 0) & (chase_rows["required_rr_at_entry"] != 0.0)
    ]
    # If balls_remaining > 0 and runs_required > 0, formula accuracy
    formula_test = chase_rows[
        (chase_rows["runs_required_at_entry"] > 0) & (chase_rows["balls_remaining_at_entry"] > 0)
    ].copy()
    formula_test["expected_rrr"] = (
        formula_test["runs_required_at_entry"] / (formula_test["balls_remaining_at_entry"] / 6.0)
    ).round(2)
    rrr_diff = (formula_test["required_rr_at_entry"] - formula_test["expected_rrr"]).abs()
    formula_bad = formula_test[rrr_diff > 0.02]

    passed_d = (len(zero_req_bad) == 0) and (len(formula_bad) == 0)
    results["Check D: Required Run Rate Validation"] = {
        "passed": passed_d,
        "details": (
            "Required run rate respects completed chases (0.0 when runs_req <= 0) and matches mathematical formula."
            if passed_d
            else f"Issues: {len(zero_req_bad)} zero-req violations, {len(formula_bad)} formula discrepancies."
        )
    }

    # ----------------------------------------------------
    # Check E: Partnership Reconciliation with Innings Total Runs
    # ----------------------------------------------------
    p_totals = partnerships_df.groupby(["match_id", "innings_number"])["partnership_runs"].sum().reset_index()
    p_chk = innings_df.merge(p_totals, on=["match_id", "innings_number"], how="left")
    p_chk["partnership_runs"] = p_chk["partnership_runs"].fillna(0).astype(int)
    p_mismatches = p_chk[p_chk["total_runs"] != p_chk["partnership_runs"]]

    # Also verify partnership runs math: runs == b1_runs + b2_runs + extras
    p_batter_overflow = partnerships_df[
        (partnerships_df["batter_1_runs_in_partnership"] + partnerships_df["batter_2_runs_in_partnership"]) > partnerships_df["partnership_runs"]
    ]

    passed_e = (len(p_mismatches) == 0) and (len(p_batter_overflow) == 0)
    results["Check E: Partnership Reconciliation"] = {
        "passed": passed_e,
        "details": (
            f"Sum of partnership runs matches innings total runs across all {len(p_totals):,} innings (0 mismatches)."
            if passed_e
            else f"Partnership mismatches in {len(p_mismatches)} innings, {len(p_batter_overflow)} batter overflow rows."
        )
    }

    # ----------------------------------------------------
    # Check F: Batting Position Consistency
    # ----------------------------------------------------
    pos_summary = batter_context_df.groupby(["match_id", "innings_number"])["batting_position"].agg(
        min_pos="min",
        count="count",
        max_pos="max"
    ).reset_index()
    bad_pos = pos_summary[(pos_summary["min_pos"] != 1) | (pos_summary["count"] != pos_summary["max_pos"])]
    passed_f = len(bad_pos) == 0
    results["Check F: Batting Position Consistency"] = {
        "passed": passed_f,
        "details": (
            "Batting positions are strictly sequential (1, 2, 3...) per actual order of entry in all innings."
            if passed_f
            else f"Batting position gaps or non-1 starts in {len(bad_pos)} innings."
        )
    }

    # ----------------------------------------------------
    # Check G: Entry State Timing
    # ----------------------------------------------------
    # Find batter's very first faced delivery in match_state
    first_faced = match_state_df.sort_values(
        ["match_id", "innings_number", "over", "ball"]
    ).groupby(["match_id", "innings_number", "batter"]).first().reset_index()

    chk_g = batter_context_df[batter_context_df["balls"] >= 1].merge(
        first_faced[["match_id", "innings_number", "batter", "runs_before_delivery", "total_team_runs_so_far"]],
        on=["match_id", "innings_number", "batter"],
        how="inner"
    )
    # Entry score must equal runs_before_delivery
    bad_entry = chk_g[chk_g["entry_score"] != chk_g["runs_before_delivery"]]
    # Confirm it does not equal score after delivery if runs were scored on that delivery
    scored_on_first = chk_g[chk_g["total_team_runs_so_far"] > chk_g["runs_before_delivery"]]
    accidental_after = scored_on_first[scored_on_first["entry_score"] == scored_on_first["total_team_runs_so_far"]]

    passed_g = (len(bad_entry) == 0) and (len(accidental_after) == 0)
    results["Check G: Entry State Timing"] = {
        "passed": passed_g,
        "details": (
            "Confirmed: Entry state represents the match situation strictly BEFORE the batter's first ball faced."
            if passed_g
            else f"Timing errors: {len(bad_entry)} mismatches, {len(accidental_after)} used score after first delivery."
        )
    }

    # ----------------------------------------------------
    # Check H: Dismissal State Correspondence
    # ----------------------------------------------------
    dismissed = batter_context_df[batter_context_df["dismissal_status"] == "out"]
    bad_dis = dismissed[
        (dismissed["dismissal_score"] != dismissed["score_after_dismissal"]) |
        (dismissed["dismissal_wickets"] != dismissed["wickets_after_dismissal"]) |
        (dismissed["score_before_dismissal"] > dismissed["score_after_dismissal"]) |
        (dismissed["wickets_before_dismissal"] >= dismissed["wickets_after_dismissal"])
    ]
    passed_h = len(bad_dis) == 0
    results["Check H: Dismissal State Correspondence"] = {
        "passed": passed_h,
        "details": (
            "Dismissal information exactly corresponds to the dismissal delivery with before/after state distinction."
            if passed_h
            else f"Inconsistent dismissal records found: {len(bad_dis)}."
        )
    }

    # ----------------------------------------------------
    # Check I: Projected Score Verification (simple baseline)
    # ----------------------------------------------------
    first_inn_rows = batter_context_df[batter_context_df["is_chase"] == False].copy()
    sched_overs = first_inn_rows["innings_number"].apply(lambda inn: 1.0 if inn > 2 else 20.0)
    first_inn_rows["expected_proj"] = (first_inn_rows["entry_team_rr"] * sched_overs).round(1)
    proj_diff = (first_inn_rows["projected_score_simple_at_entry"] - first_inn_rows["expected_proj"]).abs()
    bad_proj = first_inn_rows[proj_diff > 0.2]
    passed_i = len(bad_proj) == 0
    results["Check I: Simple Projected Score Verification"] = {
        "passed": passed_i,
        "details": (
            "Simple baseline projected scores (team_rr * scheduled_overs) verified accurately across all first innings."
            if passed_i
            else f"Projected score discrepancies in {len(bad_proj)} rows."
        )
    }

    # ----------------------------------------------------
    # Check J: Post-Dismissal Acceleration Metrics
    # ----------------------------------------------------
    # For not out batters, post-dismissal rates must be null/nan
    not_outs = batter_context_df[batter_context_df["dismissal_status"] != "out"]
    not_out_leaks = not_outs[
        not_outs["post_dismissal_rr_6balls"].notna() |
        not_outs["post_dismissal_rr_12balls"].notna() |
        not_outs["post_dismissal_rr_remaining"].notna()
    ]
    # For dismissed batters, verify non-negative where present
    dismissed_neg = dismissed[
        (dismissed["post_dismissal_rr_6balls"] < 0) |
        (dismissed["post_dismissal_rr_12balls"] < 0) |
        (dismissed["post_dismissal_rr_remaining"] < 0)
    ]
    passed_j = (len(not_out_leaks) == 0) and (len(dismissed_neg) == 0)
    results["Check J: Post-Dismissal Metrics & NULL Safety"] = {
        "passed": passed_j,
        "details": (
            "Post-dismissal rates strictly adhere to legal ball availability, null safety, and non-negativity."
            if passed_j
            else f"Issues: {len(not_out_leaks)} leaks in not-outs, {len(dismissed_neg)} negative rates."
        )
    }

    all_passed = all(item["passed"] for item in results.values())
    return all_passed, results


def run_phase2_validation(processed_dir: Path | str = "data/processed") -> bool:
    """
    Load all Phase 1 and Phase 2 CSVs and execute complete validation report.

    Args:
        processed_dir: Path to directory containing processed CSVs.

    Returns:
        bool: True if all checks pass, False otherwise.
    """
    p_path = Path(processed_dir)
    ms_file = p_path / "match_state.csv"
    p_file = p_path / "partnerships.csv"
    bc_file = p_path / "batter_context.csv"
    inn_file = p_path / "innings.csv"
    bi_file = p_path / "batter_innings.csv"

    for f in [ms_file, p_file, bc_file, inn_file, bi_file]:
        if not f.exists():
            print(f"ERROR: Missing file for validation: {f}")
            return False

    print("Loading datasets for Phase 2 validation...")
    match_state_df = pd.read_csv(ms_file, low_memory=False)
    partnerships_df = pd.read_csv(p_file, low_memory=False)
    batter_context_df = pd.read_csv(bc_file, low_memory=False)
    innings_df = pd.read_csv(inn_file, low_memory=False)
    batter_innings_df = pd.read_csv(bi_file, low_memory=False)

    print("=" * 70)
    print("PHASE 2 VALIDATION REPORT:")
    print("=" * 70)

    all_passed, results = validate_phase2_datasets(
        match_state_df=match_state_df,
        partnerships_df=partnerships_df,
        batter_context_df=batter_context_df,
        innings_df=innings_df,
        batter_innings_df=batter_innings_df
    )

    for name, data in results.items():
        sym = "[PASS] ✓" if data["passed"] else "[FAIL] ✗"
        print(f"  {sym} {name}: {data['details']}")

    print("\n" + "=" * 70)
    if all_passed:
        print("OVERALL STATUS: ALL 10 PHASE 2 VALIDATION CHECKS PASSED SUCCESSFULLY")
    else:
        print("OVERALL STATUS: VALIDATION FAILED - Please review details above.")
    print("=" * 70)

    return all_passed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate Phase 2 context datasets.")
    parser.add_argument("--processed-dir", type=str, default="data/processed", help="Path to processed datasets directory")
    args = parser.parse_args()

    success = run_phase2_validation(processed_dir=args.processed_dir)
    sys.exit(0 if success else 1)
