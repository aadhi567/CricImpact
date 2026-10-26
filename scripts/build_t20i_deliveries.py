"""
Build T20I Deliveries Dataset.
Extracts ball-by-ball delivery records from raw Cricsheet T20 matches
for all matches registered in data/processed/t20i/matches.csv.
Saves the result to data/processed/t20i/deliveries.csv using the
exact same standard schema as data/processed/deliveries.csv (IPL).
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent

MATCHES_CSV = ROOT_DIR / "data" / "processed" / "t20i" / "matches.csv"
OUTPUT_CSV = ROOT_DIR / "data" / "processed" / "t20i" / "deliveries.csv"

RAW_DIRS = [
    ROOT_DIR / "data" / "t20s_json",
    ROOT_DIR / "data" / "raw",
]

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


def build_t20i_deliveries(
    matches_csv: Path = MATCHES_CSV,
    output_csv: Path = OUTPUT_CSV,
) -> pd.DataFrame:
    if not matches_csv.exists():
        raise FileNotFoundError(f"Matches CSV not found at {matches_csv}")

    m_df = pd.read_csv(matches_csv, dtype={"match_id": str})
    print(f"Loaded {len(m_df)} matches from {matches_csv}")

    # Build match info lookup
    m_info_map: Dict[str, Dict[str, Any]] = {}
    for _, row in m_df.iterrows():
        mid = str(row["match_id"])
        m_info_map[mid] = {
            "season": str(row.get("season", "")),
            "team1": normalize_team(row.get("team1")),
            "team2": normalize_team(row.get("team2")),
        }

    t0 = time.time()
    deliv_rows: List[Dict[str, Any]] = []
    missing_files = 0
    matches_processed = 0

    for mid, minfo in m_info_map.items():
        fpath = None
        for d in RAW_DIRS:
            cand = d / f"{mid}.json"
            if cand.exists():
                fpath = cand
                break

        if not fpath:
            missing_files += 1
            continue

        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load {fpath}: {e}")
            continue

        matches_processed += 1
        info = data.get("info", {})
        raw_teams = [normalize_team(t) for t in info.get("teams", [])]
        team1 = raw_teams[0] if len(raw_teams) > 0 else minfo["team1"]
        team2 = raw_teams[1] if len(raw_teams) > 1 else minfo["team2"]
        season_str = str(info.get("season", minfo["season"])).strip()

        for inn_idx, inn in enumerate(data.get("innings", []), start=1):
            batting_team = normalize_team(inn.get("team"))
            bowling_team = team2 if batting_team == team1 else team1

            for over_obj in inn.get("overs", []):
                over_num = over_obj.get("over", 0)
                for b_idx, deliv in enumerate(over_obj.get("deliveries", [])):
                    ball_num = b_idx + 1
                    batter = deliv.get("batter")
                    non_striker = deliv.get("non_striker")
                    bowler = deliv.get("bowler")

                    runs_dict = deliv.get("runs", {})
                    b_runs = int(runs_dict.get("batter", 0))
                    e_runs = int(runs_dict.get("extras", 0))
                    tot_runs = int(runs_dict.get("total", 0))

                    extras = deliv.get("extras", {})
                    extra_type = ", ".join(extras.keys()) if extras else None
                    wides = int(extras.get("wides", 0))
                    noballs = int(extras.get("noballs", 0))
                    byes = int(extras.get("byes", 0))
                    legbyes = int(extras.get("legbyes", 0))
                    penalty = int(extras.get("penalty", 0))

                    wickets = deliv.get("wickets", [])
                    p_out = wickets[0].get("player_out") if wickets else None
                    kind = wickets[0].get("kind") if wickets else None
                    is_wicket = bool(wickets)

                    deliv_rows.append({
                        "match_id": mid,
                        "season": season_str,
                        "innings_number": inn_idx,
                        "over": over_num,
                        "ball": ball_num,
                        "batting_team": batting_team,
                        "bowling_team": bowling_team,
                        "batter": batter,
                        "non_striker": non_striker,
                        "bowler": bowler,
                        "batter_runs": b_runs,
                        "extras_runs": e_runs,
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

    duration = time.time() - t0
    print(f"Processed {matches_processed} matches ({missing_files} missing) in {duration:.2f}s")
    print(f"Extracted {len(deliv_rows)} deliveries")

    df_out = pd.DataFrame(deliv_rows)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    df_out.to_csv(output_csv, index=False, encoding="utf-8")
    print(f"Saved to {output_csv} ({output_csv.stat().st_size / (1024 * 1024):.2f} MB)")

    return df_out


if __name__ == "__main__":
    build_t20i_deliveries()
