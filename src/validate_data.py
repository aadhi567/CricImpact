"""
Validation module for processed IPL datasets.

Performs data integrity and consistency checks:
1. Match IDs uniqueness in matches.csv
2. Innings count consistency between matches and innings datasets
3. Winner consistency (winner must be one of the participating teams)
4. Toss consistency (toss winner must be one of the participating teams)
5. Team consistency (team1 != team2)
6. Delivery uniqueness (no duplicate deliveries per match/innings/over/ball)
7. Non-negative runs in deliveries and batter innings
8. Delivery run math (batter_runs + extras_runs == total_runs)
9. Innings run totals matching sum of delivery runs
10. Batter innings run totals + extras matching innings total runs
11. Total wickets in innings matching batter dismissals
12. Overs and ball numbers validity (over >= 0, ball >= 1)
13. Dismissed players validation (must appear at the crease in that innings)

Outputs a comprehensive validation report and exits with appropriate status code.
"""

import sys
import argparse
from pathlib import Path
from typing import Dict, Any, List, Tuple
import pandas as pd

# Ensure UTF-8 output encoding on Windows console
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def validate_datasets(
    matches_df: pd.DataFrame,
    innings_df: pd.DataFrame,
    deliveries_df: pd.DataFrame,
    batter_innings_df: pd.DataFrame
) -> Tuple[bool, Dict[str, Dict[str, Any]]]:
    """
    Run comprehensive consistency checks across all four datasets.

    Returns:
        Tuple: (all_passed: bool, check_results: dict)
    """
    results: Dict[str, Dict[str, Any]] = {}

    # Check 1: Match IDs Unique
    is_unique = matches_df["match_id"].is_unique
    dup_match_ids = matches_df[matches_df["match_id"].duplicated()]["match_id"].tolist()
    results["Match IDs Unique"] = {
        "passed": is_unique,
        "details": "All match IDs are unique." if is_unique else f"Duplicate match IDs found: {dup_match_ids}"
    }

    # Check 2: Winner Consistency (winner is one of team1, team2)
    with_winner = matches_df[matches_df["winner"].notna() & (matches_df["winner"] != "")]
    invalid_winners = with_winner[
        (with_winner["winner"] != with_winner["team1"]) &
        (with_winner["winner"] != with_winner["team2"])
    ]
    passed_winner = len(invalid_winners) == 0
    results["Winner Consistency"] = {
        "passed": passed_winner,
        "details": (
            "All non-empty winners are valid participating teams."
            if passed_winner
            else f"Invalid winner entries: {invalid_winners[['match_id', 'winner', 'team1', 'team2']].to_dict(orient='records')}"
        )
    }

    # Check 3: Toss Winner Consistency
    invalid_toss = matches_df[
        matches_df["toss_winner"].notna() &
        (matches_df["toss_winner"] != matches_df["team1"]) &
        (matches_df["toss_winner"] != matches_df["team2"])
    ]
    passed_toss = len(invalid_toss) == 0
    results["Toss Winner Consistency"] = {
        "passed": passed_toss,
        "details": (
            "All toss winners are valid participating teams."
            if passed_toss
            else f"Invalid toss winners: {invalid_toss[['match_id', 'toss_winner', 'team1', 'team2']].to_dict(orient='records')}"
        )
    }

    # Check 4: Team Pair Consistency (team1 != team2)
    same_teams = matches_df[matches_df["team1"] == matches_df["team2"]]
    passed_teams = len(same_teams) == 0
    results["Team Distinction"] = {
        "passed": passed_teams,
        "details": (
            "No match has identical opposing teams."
            if passed_teams
            else f"Matches with identical teams: {same_teams['match_id'].tolist()}"
        )
    }

    # Check 5: Innings Count Match
    inn_counts = innings_df.groupby("match_id").size().reset_index(name="actual_innings_count")
    merged_inns = matches_df.merge(inn_counts, on="match_id", how="left")
    inn_mismatches = merged_inns[merged_inns["innings_count"] != merged_inns["actual_innings_count"]]
    passed_inns = len(inn_mismatches) == 0
    results["Innings Count Consistency"] = {
        "passed": passed_inns,
        "details": (
            "Innings counts match between matches.csv and innings.csv."
            if passed_inns
            else f"Innings count mismatches: {inn_mismatches[['match_id', 'innings_count', 'actual_innings_count']].to_dict(orient='records')}"
        )
    }

    # Check 6: Delivery Uniqueness (no duplicate match_id, innings_number, over, ball)
    deliv_dups = deliveries_df[deliveries_df.duplicated(subset=["match_id", "innings_number", "over", "ball"], keep=False)]
    passed_dups = len(deliv_dups) == 0
    results["Delivery Uniqueness"] = {
        "passed": passed_dups,
        "details": (
            "Zero duplicate delivery entries."
            if passed_dups
            else f"{len(deliv_dups)} duplicate deliveries found in matches: {deliv_dups['match_id'].unique().tolist()}"
        )
    }

    # Check 7: Non-negative Runs in Deliveries
    neg_deliv = deliveries_df[
        (deliveries_df["batter_runs"] < 0) |
        (deliveries_df["extras_runs"] < 0) |
        (deliveries_df["total_runs"] < 0)
    ]
    passed_neg_deliv = len(neg_deliv) == 0
    results["Delivery Runs Non-negative"] = {
        "passed": passed_neg_deliv,
        "details": (
            "All delivery run fields (batter, extras, total) are >= 0."
            if passed_neg_deliv
            else f"Negative runs found in deliveries for matches: {neg_deliv['match_id'].unique().tolist()}"
        )
    }

    # Check 8: Delivery Total Runs Calculation (batter_runs + extras_runs == total_runs)
    math_mismatch = deliveries_df[deliveries_df["batter_runs"] + deliveries_df["extras_runs"] != deliveries_df["total_runs"]]
    passed_math = len(math_mismatch) == 0
    results["Delivery Runs Calculation"] = {
        "passed": passed_math,
        "details": (
            "Every delivery satisfies: batter_runs + extras_runs == total_runs."
            if passed_math
            else f"Calculation mismatches found: {math_mismatch[['match_id', 'innings_number', 'over', 'ball', 'batter_runs', 'extras_runs', 'total_runs']].head(5).to_dict(orient='records')}"
        )
    }

    # Check 9: Innings Total Runs == Sum of Delivery Total Runs
    deliv_totals = deliveries_df.groupby(["match_id", "innings_number"]).agg(
        sum_total_runs=("total_runs", "sum"),
        sum_extras_runs=("extras_runs", "sum"),
        sum_batter_runs=("batter_runs", "sum")
    ).reset_index()
    inn_chk = innings_df.merge(deliv_totals, on=["match_id", "innings_number"], how="left")
    inn_run_mismatches = inn_chk[inn_chk["total_runs"] != inn_chk["sum_total_runs"]]
    passed_inn_runs = len(inn_run_mismatches) == 0
    results["Innings Total Runs Agreement"] = {
        "passed": passed_inn_runs,
        "details": (
            "Innings total_runs agrees with sum of deliveries for all innings."
            if passed_inn_runs
            else f"Innings run mismatches: {inn_run_mismatches[['match_id', 'innings_number', 'total_runs', 'sum_total_runs']].to_dict(orient='records')}"
        )
    }

    # Check 10: Batter Runs + Extras == Innings Total Runs
    bat_sums = batter_innings_df.groupby(["match_id", "innings_number"])["runs"].sum().reset_index(name="sum_batter_inn_runs")
    inn_bat_chk = inn_chk.merge(bat_sums, on=["match_id", "innings_number"], how="left")
    inn_bat_chk["sum_batter_inn_runs"] = inn_bat_chk["sum_batter_inn_runs"].fillna(0)
    inn_bat_mismatches = inn_bat_chk[inn_bat_chk["total_runs"] != (inn_bat_chk["sum_batter_inn_runs"] + inn_bat_chk["sum_extras_runs"])]
    passed_bat_totals = len(inn_bat_mismatches) == 0
    results["Batter Totals + Extras Agreement"] = {
        "passed": passed_bat_totals,
        "details": (
            "Sum of batter runs + extras equals innings total for all innings."
            if passed_bat_totals
            else f"Batter totals mismatches: {inn_bat_mismatches[['match_id', 'innings_number', 'total_runs', 'sum_batter_inn_runs', 'sum_extras_runs']].to_dict(orient='records')}"
        )
    }

    # Check 11: Batter Innings Runs Non-negative
    neg_batter = batter_innings_df[batter_innings_df["runs"] < 0]
    passed_neg_bat = len(neg_batter) == 0
    results["Batter Runs Non-negative"] = {
        "passed": passed_neg_bat,
        "details": (
            "All batter runs are >= 0."
            if passed_neg_bat
            else f"Negative batter runs found: {neg_batter[['match_id', 'batter', 'runs']].to_dict(orient='records')}"
        )
    }

    # Check 12: Overs and Ball Numbers Validity
    invalid_overs = deliveries_df[(deliveries_df["over"] < 0) | (deliveries_df["over"] > 20)]
    invalid_balls = deliveries_df[deliveries_df["ball"] < 1]
    passed_overs_balls = (len(invalid_overs) == 0) and (len(invalid_balls) == 0)
    results["Ball Numbers and Overs Validity"] = {
        "passed": passed_overs_balls,
        "details": (
            "All overs are within [0, 20] and all ball numbers are >= 1."
            if passed_overs_balls
            else f"Invalid overs/balls: {len(invalid_overs)} invalid overs, {len(invalid_balls)} invalid balls."
        )
    }

    # Check 13: Dismissed Players Appeared in Relevant Innings
    # Build set of all batters/non-strikers present per (match_id, innings_number)
    grouped_crease = deliveries_df.groupby(["match_id", "innings_number"])
    crease_map: Dict[Tuple[str, int], set] = {}
    for (m_id, inn_n), grp in grouped_crease:
        players = set(grp["batter"].dropna().unique()).union(set(grp["non_striker"].dropna().unique()))
        crease_map[(str(m_id), int(inn_n))] = players

    dismissals = deliveries_df[deliveries_df["player_dismissed"].notna()]
    ghost_dismissals = []
    for _, row in dismissals.iterrows():
        key = (str(row["match_id"]), int(row["innings_number"]))
        allowed_players = crease_map.get(key, set())
        if row["player_dismissed"] not in allowed_players:
            ghost_dismissals.append({
                "match_id": row["match_id"],
                "innings_number": row["innings_number"],
                "player_dismissed": row["player_dismissed"]
            })

    passed_dismissed = len(ghost_dismissals) == 0
    results["Dismissed Players Innings Consistency"] = {
        "passed": passed_dismissed,
        "details": (
            "All dismissed players were active at the crease in the relevant innings."
            if passed_dismissed
            else f"Dismissed players not at crease: {ghost_dismissals[:5]}"
        )
    }

    # Check 14: Total Wickets Agreement with Batter Dismissals ('out')
    outs = batter_innings_df[batter_innings_df["dismissal_status"] == "out"].groupby(
        ["match_id", "innings_number"]
    ).size().reset_index(name="bat_outs_count")
    inn_wkt_chk = innings_df.merge(outs, on=["match_id", "innings_number"], how="left")
    inn_wkt_chk["bat_outs_count"] = inn_wkt_chk["bat_outs_count"].fillna(0).astype(int)
    wkt_mismatches = inn_wkt_chk[inn_wkt_chk["total_wickets"] != inn_wkt_chk["bat_outs_count"]]
    passed_wkts = len(wkt_mismatches) == 0
    results["Total Wickets Consistency"] = {
        "passed": passed_wkts,
        "details": (
            "Total wickets in innings agrees with batter 'out' dismissals."
            if passed_wkts
            else f"Wicket count mismatches: {wkt_mismatches[['match_id', 'innings_number', 'total_wickets', 'bat_outs_count']].to_dict(orient='records')}"
        )
    }

    all_passed = all(item["passed"] for item in results.values())
    return all_passed, results


def run_validation(processed_dir: Path | str = "data/processed") -> bool:
    """
    Load CSV files from processed_dir, execute validation, and print report.

    Args:
        processed_dir: Path to directory containing the 4 processed CSVs.

    Returns:
        bool: True if all checks pass, False otherwise.
    """
    p_path = Path(processed_dir)
    m_file = p_path / "matches.csv"
    inn_file = p_path / "innings.csv"
    del_file = p_path / "deliveries.csv"
    bat_file = p_path / "batter_innings.csv"

    for f in [m_file, inn_file, del_file, bat_file]:
        if not f.exists():
            print(f"ERROR: Missing processed file: {f}")
            return False

    matches_df = pd.read_csv(m_file, low_memory=False)
    innings_df = pd.read_csv(inn_file, low_memory=False)
    deliveries_df = pd.read_csv(del_file, low_memory=False)
    batter_innings_df = pd.read_csv(bat_file, low_memory=False)

    print("=" * 60)
    print("DATA PROCESSING SUMMARY:")
    print(f"MATCHES PROCESSED: {len(matches_df):,}")
    print(f"INNINGS PROCESSED: {len(innings_df):,}")
    print(f"DELIVERIES PROCESSED: {len(deliveries_df):,}")
    print(f"BATTER INNINGS PROCESSED: {len(batter_innings_df):,}")
    print("=" * 60)
    print("\nVALIDATION REPORT:")

    all_passed, results = validate_datasets(
        matches_df=matches_df,
        innings_df=innings_df,
        deliveries_df=deliveries_df,
        batter_innings_df=batter_innings_df
    )

    for check_name, data in results.items():
        symbol = "[PASS] ✓" if data["passed"] else "[FAIL] ✗"
        print(f"  {symbol} {check_name}: {data['details']}")

    print("\n" + "=" * 60)
    if all_passed:
        print("OVERALL STATUS: ALL VALIDATION CHECKS PASSED SUCCESSFULLY")
    else:
        print("OVERALL STATUS: VALIDATION FAILED - Please review details above.")
    print("=" * 60)

    return all_passed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate processed IPL datasets.")
    parser.add_argument("--processed-dir", type=str, default="data/processed", help="Path to processed datasets directory")
    args = parser.parse_args()

    success = run_validation(processed_dir=args.processed_dir)
    sys.exit(0 if success else 1)
