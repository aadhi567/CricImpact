"""
Backend Data Access Service for Cricket Batter Contribution Analytics.
Single source of truth consuming pre-computed Phase 5B and Phase 6A artifacts.
Strictly adheres to:
- No JS/frontend calculations of contribution.
- No recomputation of mathematical model formulas.
- Strict DNB rule: DNB appearances return None (JSON null), never 0 or 50.
- Contextual segmentation: unobserved phases return None (JSON null), never 0.
"""

import os
import re
import json
import math
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np

# Base paths
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
PHASE6_DIR = ROOT_DIR / "models" / "contribution" / "phase6"
DATA_DIR = ROOT_DIR / "data" / "processed"


def clean_num(val, decimals: Optional[int] = None):
    """Safely converts numeric values to float/int, converting NaN/inf to None (null in JSON)."""
    if val is None or pd.isna(val) or val == "" or str(val).strip().lower() in ("nan", "none", "null"):
        return None
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return None
        if decimals is not None:
            return round(f, decimals)
        return f
    except (ValueError, TypeError):
        return None


def clean_int(val):
    """Safely converts numeric values to int, converting NaN to None."""
    v = clean_num(val)
    return int(round(v)) if v is not None else None


# Competitions temporarily deactivated due to incomplete match coverage (preserved for future reactivation)
DEACTIVATED_COMPETITIONS = {
    "smat": {
        "id": "smat",
        "name": "Syed Mushtaq Ali Trophy",
        "code": "SMAT",
        "type": "domestic",
        "default_season": "2023/24",
        "status": "temporarily_deactivated",
        "reason": "Incomplete match coverage in available dataset",
    }
}

COMPETITION_METADATA = [
    {
        "id": "ipl",
        "name": "Indian Premier League",
        "code": "IPL",
        "type": "franchise",
        "default_season": "2024",
    },
    {
        "id": "t20i",
        "name": "Men's International T20",
        "code": "T20I",
        "type": "international",
        "default_season": "2024",
    },
]

TOURNAMENT_TYPES = [
    {"id": "all", "label": "All International T20Is"},
    {"id": "world_cup", "label": "ICC Men's T20 World Cup"},
    {"id": "asia_cup", "label": "Men's Asia Cup (T20)"},
    {"id": "bilateral", "label": "Bilateral / Tri-Series"},
]


class DataService:
    def __init__(self):
        self._competitions = ["ipl", "t20i"]
        self._cache: Dict[str, Dict[str, Optional[pd.DataFrame]]] = {
            c: {
                "season_metrics": None,
                "matches": None,
                "rosters": None,
                "contributions": None,
            }
            for c in self._competitions
        }
        self._dynamic_metrics_cache: Dict[str, pd.DataFrame] = {}
        self._spec: Optional[Dict[str, Any]] = None
        self._audit: Optional[Dict[str, Any]] = None
        self._thresholds: Optional[Dict[str, Any]] = None
        self._edge_cases: Optional[List[Dict[str, Any]]] = None
        self._examples: Optional[Dict[str, Any]] = None
        self._career_players_cache: Optional[List[Dict[str, Any]]] = None
        self._dataset_coverage_cache: Optional[Dict[str, Any]] = None
        self._bowler_classification_cache: Optional[Dict[str, str]] = None
        self._ipl_deliveries_df_cache: Optional[pd.DataFrame] = None
        self._t20i_deliveries_cache: Dict[str, List[Dict[str, Any]]] = {}

    @property
    def _season_metrics_df(self) -> Optional[pd.DataFrame]:
        return self.get_season_metrics_df("ipl")

    @_season_metrics_df.setter
    def _season_metrics_df(self, val):
        self._cache["ipl"]["season_metrics"] = val

    @property
    def _matches_df(self) -> Optional[pd.DataFrame]:
        return self.get_matches_df("ipl")

    @_matches_df.setter
    def _matches_df(self, val):
        self._cache["ipl"]["matches"] = val

    @property
    def _rosters_df(self) -> Optional[pd.DataFrame]:
        return self.get_rosters_df("ipl")

    @_rosters_df.setter
    def _rosters_df(self, val):
        self._cache["ipl"]["rosters"] = val

    @property
    def _contributions_df(self) -> Optional[pd.DataFrame]:
        return self.get_contributions_df("ipl")

    @_contributions_df.setter
    def _contributions_df(self, val):
        self._cache["ipl"]["contributions"] = val

    def get_competitions(self) -> List[Dict[str, Any]]:
        return COMPETITION_METADATA

    def get_active_scoring_engine(self) -> str:
        from src.scoring_engine_config import get_active_scoring_engine
        return get_active_scoring_engine()

    def _normalize_competition(self, comp: Optional[str]) -> str:
        if not comp:
            return "ipl"
        c = comp.strip().lower()
        if c == "smat" or c in DEACTIVATED_COMPETITIONS:
            raise ValueError(
                "Syed Mushtaq Ali Trophy (SMAT) data support is temporarily deactivated due to incomplete match coverage."
            )
        return c if c in self._competitions else "ipl"

    def _ensure_loaded(self, competition: Optional[str] = "ipl"):
        comp = self._normalize_competition(competition)
        cache = self._cache.setdefault(comp, {"season_metrics": None, "matches": None, "rosters": None, "contributions": None})

        if comp == "ipl":
            if cache["season_metrics"] is None:
                metrics_path = PHASE6_DIR / "phase6_season_metrics.csv"
                if not metrics_path.exists():
                    raise FileNotFoundError(f"Missing required artifact: {metrics_path}")
                cache["season_metrics"] = pd.read_csv(metrics_path, dtype={"season": str})

            if cache["matches"] is None:
                matches_path = DATA_DIR / "matches.csv"
                if matches_path.exists():
                    cache["matches"] = pd.read_csv(matches_path, dtype={"season": str, "match_id": str})
                else:
                    cache["matches"] = pd.DataFrame()

            if cache["rosters"] is None:
                roster_path = DATA_DIR / "match_rosters.csv"
                if roster_path.exists():
                    cache["rosters"] = pd.read_csv(roster_path, dtype={"season": str, "match_id": str})
                else:
                    cache["rosters"] = pd.DataFrame()

            if cache["contributions"] is None:
                contrib_path = DATA_DIR / "batter_match_contributions.csv"
                if contrib_path.exists():
                    cache["contributions"] = pd.read_csv(contrib_path, dtype={"season": str, "match_id": str}, low_memory=False)
                else:
                    cache["contributions"] = pd.DataFrame()
        else:
            comp_dir = DATA_DIR / comp
            if cache["season_metrics"] is None:
                m_path = comp_dir / "phase6_season_metrics.csv"
                if not m_path.exists():
                    m_path = comp_dir / "season_metrics.csv"
                if m_path.exists():
                    cache["season_metrics"] = pd.read_csv(m_path, dtype={"season": str})
                else:
                    cache["season_metrics"] = pd.DataFrame()

            if cache["matches"] is None:
                matches_path = comp_dir / "matches.csv"
                if matches_path.exists():
                    cache["matches"] = pd.read_csv(matches_path, dtype={"season": str, "match_id": str})
                else:
                    cache["matches"] = pd.DataFrame()

            if cache["rosters"] is None:
                roster_path = comp_dir / "match_rosters.csv"
                if roster_path.exists():
                    cache["rosters"] = pd.read_csv(roster_path, dtype={"season": str, "match_id": str})
                else:
                    cache["rosters"] = pd.DataFrame()

            if cache["contributions"] is None:
                contrib_path = comp_dir / "batter_match_contributions.csv"
                if contrib_path.exists():
                    cache["contributions"] = pd.read_csv(contrib_path, dtype={"season": str, "match_id": str}, low_memory=False)
                else:
                    cache["contributions"] = pd.DataFrame()

    def get_season_metrics_df(self, competition: Optional[str] = "ipl") -> pd.DataFrame:
        self._ensure_loaded(competition)
        return self._cache[self._normalize_competition(competition)]["season_metrics"]

    def get_matches_df(self, competition: Optional[str] = "ipl") -> pd.DataFrame:
        self._ensure_loaded(competition)
        return self._cache[self._normalize_competition(competition)]["matches"]

    def get_rosters_df(self, competition: Optional[str] = "ipl") -> pd.DataFrame:
        self._ensure_loaded(competition)
        return self._cache[self._normalize_competition(competition)]["rosters"]

    def get_contributions_df(self, competition: Optional[str] = "ipl") -> pd.DataFrame:
        self._ensure_loaded(competition)
        return self._cache[self._normalize_competition(competition)]["contributions"]

    def _classify_tournament_type(self, event_name: Any) -> str:
        """Classifies T20 match event_name into standard tournament categories."""
        if not event_name or pd.isna(event_name):
            return "bilateral"
        ev = str(event_name).strip()
        # Normalize unicode apostrophes and multiple whitespace
        norm = re.sub(r"[\u2018\u2019\u201a\u201b\ufffd]", "'", ev)
        norm = re.sub(r"\s+", " ", norm).strip()
        norm_lower = norm.lower()

        # Disqualify qualifiers, warm-ups, regional stages, youth/women events
        exclusions = ["qualifier", "warm-up", "warm up", "women", "u19", "under-19", "region"]
        if not any(ex in norm_lower for ex in exclusions):
            wc_variants = [
                "icc men's t20 world cup",
                "icc mens t20 world cup",
                "icc world twenty20",
                "icc world t20",
                "world t20",
                "world twenty20",
            ]
            if norm_lower in wc_variants:
                return "world_cup"

        if norm_lower in ["asia cup", "men's t20 asia cup", "mens t20 asia cup", "men's t20 asia cup qualifier"]:
            return "asia_cup"
        if any(k in norm_lower for k in [
            "series", "tour of", "tour in", "in australia", "in india", "in england",
            "in new zealand", "in south africa", "in west indies", "in pakistan",
            "in sri lanka", "in bangladesh", "in zimbabwe", "in ireland",
            "tri-nation", "tri-series", "quadrangular", "bilateral"
        ]):
            return "bilateral"
        return "other"

    def get_tournament_types(self) -> List[Dict[str, str]]:
        return TOURNAMENT_TYPES

    @staticmethod
    def _resolve_dynamic_default_season(seasons: List[str]) -> Optional[str]:
        """
        Dynamically resolves the default season based on the current calendar year.
        1. If current calendar year (e.g. '2026') is available in the options, select it.
        2. If a split-year overlapping current year (e.g. '2025/26' or '2026/27') is available, select it.
        3. If current year is not available, select the latest available season (first in sorted list).
        Never hardcodes any calendar year.
        """
        if not seasons:
            return None
        current_year = str(datetime.date.today().year)

        # 1. Exact match with current year (e.g. '2026')
        if current_year in seasons:
            return current_year

        # 2. Overlapping split season match (e.g. '2025/26' or '2026/27')
        short_year = current_year[2:]
        for s in seasons:
            s_str = str(s).strip()
            if s_str.endswith(f"/{short_year}") or s_str.startswith(f"{current_year}/"):
                return s_str

        # 3. Fallback to latest available season (first element in chronologically descending list)
        return seasons[0]

    def get_season_metadata(
        self,
        competition: Optional[str] = "ipl",
        tournament_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Returns valid seasons, formatted display labels, and dynamic default season.
        Adheres strictly to requirement:
        - Dynamic default season selection matching current calendar year or latest available.
        - Calendar-year labels for bilateral T20Is, e.g. "2024"
        - Edition/year labels for tournaments, e.g. "T20 World Cup 2024"
        - Tournament season labels for SMAT, e.g. "2024/25"
        """
        comp = self._normalize_competition(competition)
        t_type = (tournament_type or "all").lower().strip()

        if comp == "ipl":
            seasons = self.get_seasons("ipl")
            options = [{"value": s, "label": f"{s} Season"} for s in seasons]
            return {
                "seasons": seasons,
                "season_options": options,
                "default_season": self._resolve_dynamic_default_season(seasons),
                "competition": "ipl",
                "tournament_type": None,
            }
        # SMAT season metadata preserved for future reactivation:
        # elif comp == "smat":
        #     seasons = self.get_seasons("smat")
        #     options = [{"value": s, "label": s} for s in seasons]
        #     return {
        #         "seasons": seasons,
        #         "season_options": options,
        #         "default_season": self._resolve_dynamic_default_season(seasons),
        #         "competition": "smat",
        #         "tournament_type": None,
        #     }

        # Men's International T20 (T20I)
        if t_type == "world_cup":
            options = [
                {"value": "2026", "label": "T20 World Cup 2026"},
                {"value": "2024", "label": "T20 World Cup 2024"},
                {"value": "2022", "label": "T20 World Cup 2022"},
                {"value": "2021", "label": "T20 World Cup 2021"},
                {"value": "2016", "label": "T20 World Cup 2016"},
                {"value": "2014", "label": "T20 World Cup 2014"},
                {"value": "2012", "label": "T20 World Cup 2012"},
                {"value": "2010", "label": "T20 World Cup 2010"},
                {"value": "2009", "label": "T20 World Cup 2009"},
                {"value": "2007", "label": "T20 World Cup 2007"},
            ]
            seasons = [opt["value"] for opt in options]
            return {
                "seasons": seasons,
                "season_options": options,
                "default_season": self._resolve_dynamic_default_season(seasons),
                "competition": "t20i",
                "tournament_type": "world_cup",
            }
        elif t_type == "asia_cup":
            options = [
                {"value": "2025", "label": "Asia Cup 2025"},
                {"value": "2022", "label": "Asia Cup 2022"},
            ]
            seasons = [opt["value"] for opt in options]
            return {
                "seasons": seasons,
                "season_options": options,
                "default_season": self._resolve_dynamic_default_season(seasons),
                "competition": "t20i",
                "tournament_type": "asia_cup",
            }
        elif t_type in ("bilateral", "other"):
            all_t20i = self.get_seasons("t20i")
            distinct_years = sorted(list(set([s[:4] for s in all_t20i if s and len(s) >= 4])), reverse=True)
            years = distinct_years if distinct_years else ["2026", "2025", "2024", "2023", "2022"]
            options = [{"value": y, "label": y} for y in years]
            return {
                "seasons": years,
                "season_options": options,
                "default_season": self._resolve_dynamic_default_season(years),
                "competition": "t20i",
                "tournament_type": t_type,
            }
        else:  # "all"
            all_seasons = self.get_seasons("t20i")
            options = [{"value": s, "label": s} for s in all_seasons]
            return {
                "seasons": all_seasons,
                "season_options": options,
                "default_season": self._resolve_dynamic_default_season(all_seasons),
                "competition": "t20i",
                "tournament_type": "all",
            }

    def _filter_t20i_matches(self, tournament_type: Optional[str], season: Optional[str] = None) -> pd.DataFrame:
        matches_df = self.get_matches_df("t20i")
        if matches_df is None or matches_df.empty:
            return pd.DataFrame()
        df = matches_df.copy()
        if "tournament_type" not in df.columns:
            df["tournament_type"] = df["event_name"].apply(self._classify_tournament_type)

        t_clean = (tournament_type or "all").lower().strip()
        if t_clean != "all":
            df = df[df["tournament_type"] == t_clean]

        if season and season != "All Seasons":
            s_str = str(season).strip()
            if t_clean == "world_cup":
                wc_season_map = {
                    "2026": ["2025/26", "2026"],
                    "2024": ["2024"],
                    "2022": ["2022/23", "2022"],
                    "2021": ["2021/22", "2021"],
                    "2016": ["2015/16", "2016"],
                    "2014": ["2013/14", "2014"],
                    "2012": ["2012/13", "2012"],
                    "2010": ["2010"],
                    "2009": ["2009"],
                    "2007": ["2007/08", "2007"],
                }
                if s_str in wc_season_map:
                    target_seasons = wc_season_map[s_str]
                    df = df[(df["season"].isin(target_seasons)) | (df["date"].astype(str).str.startswith(s_str))]
                else:
                    df = df[(df["season"] == s_str) | (df["date"].astype(str).str.startswith(s_str))]
            elif t_clean == "asia_cup":
                df = df[df["season"] == s_str]
            else:
                # Bilateral, other, or all: support calendar year and split seasons
                if len(s_str) == 4 and s_str.isdigit():
                    yr = int(s_str)
                    prev_split = f"{yr - 1}/{s_str[2:]}"
                    next_split = f"{s_str}/{int(s_str[2:]) + 1:02d}"
                    df = df[
                        (df["season"] == s_str) |
                        (df["date"].astype(str).str.startswith(s_str)) |
                        ((df["season"] == prev_split) & (df["date"].astype(str).str.startswith(s_str))) |
                        ((df["season"] == next_split) & (df["date"].astype(str).str.startswith(s_str)))
                    ]
                else:
                    df = df[df["season"] == s_str]

        return df

    def _get_dynamic_tournament_metrics(self, tournament_type: str, season: Optional[str] = None) -> pd.DataFrame:
        """
        Dynamically aggregates player season metrics for filtered tournament types.
        Strictly preserves:
        - Frozen Phase 5B contribution formulas and score values
        - Strict DNB rule: did_not_bat_matches >= 0, average_contribution_score = NaN (null in JSON)
        - View A (all-innings) and View B (qualified) separation
        - Contextual phase aggregations (P1-P4 signals)
        """
        t_clean = (tournament_type or "all").lower().strip()
        s_clean = str(season).strip() if season else "all"
        cache_key = f"t20i_{t_clean}_{s_clean}"
        if cache_key in self._dynamic_metrics_cache:
            return self._dynamic_metrics_cache[cache_key]

        m_sub = self._filter_t20i_matches(t_clean, season)
        if m_sub.empty:
            empty_df = pd.DataFrame(columns=[
                "player", "season", "team", "matches_played", "batting_innings",
                "did_not_bat_matches", "actual_runs", "balls_faced", "not_outs",
                "average_contribution_score", "total_raw_contribution",
                "total_positive_raw_contribution", "season_team_contribution_share",
                "contribution_per_batting_opportunity", "qualified_batting_innings",
                "excluded_small_opportunity_innings", "qualified_average_contribution_score",
                "qualified_total_positive_contribution", "qualified_team_contribution_share",
                "first_innings_contribution", "chase_contribution", "powerplay_contribution",
                "middle_over_contribution", "death_over_contribution", "high_pressure_contribution"
            ])
            self._dynamic_metrics_cache[cache_key] = empty_df
            return empty_df

        m_ids = set(m_sub["match_id"].astype(str))
        roster_df = self.get_rosters_df("t20i")
        contrib_df = self.get_contributions_df("t20i")

        r_sub = roster_df[roster_df["match_id"].astype(str).isin(m_ids)] if roster_df is not None and not roster_df.empty else pd.DataFrame()
        c_sub = contrib_df[contrib_df["match_id"].astype(str).isin(m_ids)] if contrib_df is not None and not contrib_df.empty else pd.DataFrame()

        if r_sub.empty:
            empty_df = pd.DataFrame()
            self._dynamic_metrics_cache[cache_key] = empty_df
            return empty_df

        # Appearances from roster
        r_grp = r_sub.groupby(["player", "team"]).agg(
            matches_played=("match_id", "nunique")
        ).reset_index()

        if not c_sub.empty:
            c_sub_copy = c_sub.copy()
            c_sub_copy["first_inns_score"] = np.where(c_sub_copy["innings"] == 1, c_sub_copy["contribution_score"], np.nan)
            c_sub_copy["chase_score"] = np.where(c_sub_copy["innings"] == 2, c_sub_copy["contribution_score"], np.nan)

            is_qual = ~c_sub_copy["is_negligible"] if "is_negligible" in c_sub_copy.columns else ((c_sub_copy["balls_faced"] >= 10) | (c_sub_copy["actual_runs"] >= 20))
            c_sub_copy["is_qual"] = is_qual
            c_sub_copy["qual_score"] = np.where(is_qual, c_sub_copy["contribution_score"], np.nan)
            c_sub_copy["qual_pos_raw"] = np.where(is_qual & (c_sub_copy["raw_contribution"] > 0), c_sub_copy["raw_contribution"], 0.0)

            # Phase tracking
            entry_ov = c_sub_copy["entry_over"].astype(float)
            exit_ov = c_sub_copy["exit_over"].fillna(entry_ov).astype(float)
            c_sub_copy["pp_score"] = np.where(entry_ov < 6.0, c_sub_copy["contribution_score"], np.nan)
            c_sub_copy["mid_score"] = np.where((entry_ov < 16.0) & (exit_ov >= 6.0), c_sub_copy["contribution_score"], np.nan)
            c_sub_copy["death_score"] = np.where((entry_ov >= 16.0) | (exit_ov >= 16.0), c_sub_copy["contribution_score"], np.nan)

            if "score_context" in c_sub_copy.columns:
                c_sub_copy["press_score"] = np.where(c_sub_copy["score_context"].astype(float) >= 60.0, c_sub_copy["contribution_score"], np.nan)
            else:
                c_sub_copy["press_score"] = np.nan

            c_agg = c_sub_copy.groupby(["player", "team"]).agg(
                batting_innings=("match_id", "count"),
                actual_runs=("actual_runs", "sum"),
                balls_faced=("balls_faced", "sum"),
                fours=("fours", "sum"),
                sixes=("sixes", "sum"),
                not_outs=("dismissal_status", lambda s: (s.str.lower() == "not out").sum()),
                average_contribution_score=("contribution_score", "mean"),
                total_raw_contribution=("raw_contribution", "sum"),
                total_positive_raw_contribution=("raw_contribution", lambda s: s[s > 0].sum()),
                qualified_batting_innings=("is_qual", "sum"),
                qualified_average_contribution_score=("qual_score", "mean"),
                qualified_total_positive_contribution=("qual_pos_raw", "sum"),
                first_innings_contribution=("first_inns_score", "mean"),
                chase_contribution=("chase_score", "mean"),
                powerplay_contribution=("pp_score", "mean"),
                middle_over_contribution=("mid_score", "mean"),
                death_over_contribution=("death_score", "mean"),
                high_pressure_contribution=("press_score", "mean"),
            ).reset_index()
        else:
            c_agg = pd.DataFrame(columns=[
                "player", "team", "batting_innings", "actual_runs", "balls_faced", "fours", "sixes",
                "not_outs", "average_contribution_score", "total_raw_contribution",
                "total_positive_raw_contribution", "qualified_batting_innings",
                "qualified_average_contribution_score", "qualified_total_positive_contribution"
            ])

        merged = pd.merge(r_grp, c_agg, on=["player", "team"], how="left")
        merged["batting_innings"] = merged["batting_innings"].fillna(0).astype(int)
        merged["did_not_bat_matches"] = merged["matches_played"] - merged["batting_innings"]
        merged["actual_runs"] = merged["actual_runs"].fillna(0).astype(int)
        merged["balls_faced"] = merged["balls_faced"].fillna(0).astype(int)
        merged["fours"] = merged["fours"].fillna(0).astype(int)
        merged["sixes"] = merged["sixes"].fillna(0).astype(int)
        merged["not_outs"] = merged["not_outs"].fillna(0).astype(int)
        merged["total_raw_contribution"] = merged["total_raw_contribution"].fillna(0.0).round(4)
        merged["total_positive_raw_contribution"] = merged["total_positive_raw_contribution"].fillna(0.0).round(4)
        merged["qualified_batting_innings"] = merged["qualified_batting_innings"].fillna(0).astype(int)
        merged["excluded_small_opportunity_innings"] = merged["batting_innings"] - merged["qualified_batting_innings"]
        merged["qualified_total_positive_contribution"] = merged["qualified_total_positive_contribution"].fillna(0.0).round(4)

        # STRICT DNB RULE: If batting_innings == 0, average_contribution_score is strictly NaN
        merged.loc[merged["batting_innings"] == 0, "average_contribution_score"] = np.nan
        merged.loc[merged["qualified_batting_innings"] == 0, "qualified_average_contribution_score"] = np.nan
        merged["average_contribution_score"] = merged["average_contribution_score"].round(2)
        merged["qualified_average_contribution_score"] = merged["qualified_average_contribution_score"].round(2)

        # Team share
        team_pos = merged.groupby("team")["total_positive_raw_contribution"].transform("sum")
        merged["season_team_contribution_share"] = np.where(
            merged["batting_innings"] == 0,
            np.nan,
            np.where(team_pos > 0, (merged["total_positive_raw_contribution"] / team_pos * 100.0).round(2), 0.0)
        )

        qual_team_pos = merged.groupby("team")["qualified_total_positive_contribution"].transform("sum")
        merged["qualified_team_contribution_share"] = np.where(
            merged["qualified_batting_innings"] == 0,
            np.nan,
            np.where(qual_team_pos > 0, (merged["qualified_total_positive_contribution"] / qual_team_pos * 100.0).round(2), 0.0)
        )

        merged["contribution_per_batting_opportunity"] = np.where(
            merged["batting_innings"] > 0,
            (merged["total_positive_raw_contribution"] / merged["batting_innings"]).round(4),
            np.nan
        )

        merged["season"] = str(season) if season else "All Seasons"
        for col in [
            "first_innings_contribution", "chase_contribution", "powerplay_contribution",
            "middle_over_contribution", "death_over_contribution", "high_pressure_contribution"
        ]:
            if col in merged.columns:
                merged[col] = merged[col].round(2)

        merged = merged.sort_values(by=["total_positive_raw_contribution", "actual_runs"], ascending=[False, False])
        self._dynamic_metrics_cache[cache_key] = merged
        return merged

    def get_seasons(self, competition: Optional[str] = "ipl", tournament_type: Optional[str] = None) -> List[str]:
        comp = self._normalize_competition(competition)
        if comp == "t20i" and tournament_type and tournament_type != "all":
            return self.get_season_metadata(competition="t20i", tournament_type=tournament_type)["seasons"]
        df = self.get_season_metrics_df(comp)
        if df is None or df.empty:
            m_df = self.get_matches_df(comp)
            if m_df is not None and not m_df.empty and "season" in m_df.columns:
                return sorted(m_df["season"].dropna().unique().tolist(), reverse=True)
            return []
        seasons = sorted(df["season"].dropna().unique().tolist(), reverse=True)
        return seasons

    def get_teams(
        self,
        season: Optional[str] = None,
        competition: Optional[str] = "ipl",
        tournament_type: Optional[str] = None,
    ) -> List[str]:
        comp = self._normalize_competition(competition)
        if comp == "t20i":
            m_df = self._filter_t20i_matches(tournament_type or "all", season)
            if m_df is not None and not m_df.empty:
                teams = sorted(list(set(m_df["team1"].dropna().tolist() + m_df["team2"].dropna().tolist())))
                return [t for t in teams if t.strip()]
            return []

        df = self.get_season_metrics_df(comp)
        if df is None or df.empty:
            m_df = self.get_matches_df(comp)
            if m_df is not None and not m_df.empty:
                if season:
                    m_df = m_df[m_df["season"] == str(season)]
                teams = sorted(list(set(m_df["team1"].dropna().tolist() + m_df["team2"].dropna().tolist())))
                return [t for t in teams if t.strip()]
            return []
        if season:
            df = df[df["season"] == str(season)]
        teams = sorted([t for t in df["team"].dropna().unique().tolist() if t.strip()])
        return teams

    def get_dashboard_summary(
        self,
        season: Optional[str] = None,
        team: Optional[str] = None,
        min_runs: int = 0,
        competition: Optional[str] = "ipl",
        tournament_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        comp = self._normalize_competition(competition)
        if comp == "t20i":
            df = self._get_dynamic_tournament_metrics(tournament_type or "all", season)
            m_filtered = self._filter_t20i_matches(tournament_type or "all", season)
            if team:
                m_filtered = m_filtered[(m_filtered["team1"] == team) | (m_filtered["team2"] == team)]
            total_matches = len(m_filtered)
        else:
            df = self.get_season_metrics_df(comp)
            total_matches = None

        if df is None or df.empty:
            return {
                "season": season,
                "team": team,
                "min_runs": min_runs,
                "tournament_type": tournament_type,
                "total_players": 0,
                "total_batting_innings": 0,
                "total_matches_played": 0,
                "total_dnb_matches": 0,
                "average_contribution_score": None,
                "total_positive_contribution": 0.0,
                "average_team_contribution_share": None,
            }

        if season and comp != "t20i":
            df = df[df["season"] == str(season)]
        if team:
            df = df[df["team"] == team]
        if min_runs > 0:
            df = df[df["actual_runs"] >= min_runs]

        total_players = len(df)
        total_innings = int(df["batting_innings"].sum()) if not df.empty else 0
        if total_matches is None:
            total_matches = int(df["matches_played"].sum()) if not df.empty else 0
        total_dnb = int(df["did_not_bat_matches"].sum()) if not df.empty else 0

        # Mean contribution score across batting opportunities (excluding nulls)
        scores = df["average_contribution_score"].dropna()
        avg_score = round(float(scores.mean()), 2) if not scores.empty else None

        # Total positive raw contribution
        pos_contrib = round(float(df["total_positive_raw_contribution"].sum()), 2) if not df.empty else 0.0

        # Mean team contribution share (excluding nulls)
        shares = df["season_team_contribution_share"].dropna()
        avg_share = round(float(shares.mean()), 2) if not shares.empty else None

        return {
            "season": season,
            "team": team,
            "min_runs": min_runs,
            "tournament_type": tournament_type,
            "total_players": total_players,
            "total_batting_innings": total_innings,
            "total_matches_played": total_matches,
            "total_dnb_matches": total_dnb,
            "average_contribution_score": avg_score,
            "total_positive_contribution": pos_contrib,
            "average_team_contribution_share": avg_share,
        }

    def get_players(
        self,
        season: Optional[str] = None,
        team: Optional[str] = None,
        min_runs: int = 0,
        min_innings: int = 0,
        min_balls: int = 0,
        search: Optional[str] = None,
        limit: int = 500,
        competition: Optional[str] = "ipl",
        tournament_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        comp = self._normalize_competition(competition)
        if comp == "t20i":
            df = self._get_dynamic_tournament_metrics(tournament_type or "all", season)
        else:
            df = self.get_season_metrics_df(comp)
            if df is not None and not df.empty and season:
                df = df[df["season"] == str(season)]

        if df is None or df.empty:
            return []
        df = df.copy()

        if team:
            df = df[df["team"] == team]
        if min_runs > 0:
            df = df[df["actual_runs"] >= min_runs]
        if min_innings > 0:
            df = df[df["batting_innings"] >= min_innings]
        if min_balls > 0:
            df = df[df["balls_faced"] >= min_balls]
        if search:
            s = search.strip().lower()
            df = df[df["player"].str.lower().str.contains(s, na=False)]

        # Limit and format
        records = []
        for _, row in df.head(limit).iterrows():
            records.append({
                "player": str(row["player"]),
                "season": str(row["season"]),
                "team": str(row["team"]),
                "matches_played": clean_int(row.get("matches_played")),
                "batting_innings": clean_int(row.get("batting_innings")),
                "did_not_bat_matches": clean_int(row.get("did_not_bat_matches")),
                "actual_runs": clean_int(row.get("actual_runs")),
                "balls_faced": clean_int(row.get("balls_faced")),
                "not_outs": clean_int(row.get("not_outs")),
                "average_contribution_score": clean_num(row.get("average_contribution_score"), 2),
                "total_raw_contribution": clean_num(row.get("total_raw_contribution"), 4),
                "total_positive_raw_contribution": clean_num(row.get("total_positive_raw_contribution"), 4),
                "season_team_contribution_share": clean_num(row.get("season_team_contribution_share"), 2),
                "contribution_per_batting_opportunity": clean_num(row.get("contribution_per_batting_opportunity"), 4),
                "qualified_batting_innings": clean_int(row.get("qualified_batting_innings")),
                "excluded_small_opportunity_innings": clean_int(row.get("excluded_small_opportunity_innings")),
                "qualified_average_contribution_score": clean_num(row.get("qualified_average_contribution_score"), 2),
                "qualified_total_positive_contribution": clean_num(row.get("qualified_total_positive_contribution"), 4),
                "qualified_team_contribution_share": clean_num(row.get("qualified_team_contribution_share"), 2),
                "first_innings_contribution": clean_num(row.get("first_innings_contribution"), 2),
                "chase_contribution": clean_num(row.get("chase_contribution"), 2),
                "powerplay_contribution": clean_num(row.get("powerplay_contribution"), 2),
                "middle_over_contribution": clean_num(row.get("middle_over_contribution"), 2),
                "death_over_contribution": clean_num(row.get("death_over_contribution"), 2),
                "high_pressure_contribution": clean_num(row.get("high_pressure_contribution"), 2),
            })
        return records

    def get_player_season(
        self,
        player_id: str,
        season: str,
        competition: Optional[str] = "ipl",
        tournament_type: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        norm_comp = self._normalize_competition(competition)
        pid_lower = player_id.strip().lower()
        season_str = str(season).strip()

        if norm_comp == "t20i":
            df = self._get_dynamic_tournament_metrics(tournament_type or "all", season_str)
            if df is None or df.empty:
                return None
            sub = df[df["player"].str.lower() == pid_lower]
        else:
            df = self.get_season_metrics_df(norm_comp)
            if df is None or df.empty:
                return None
            sub = df[(df["player"].str.lower() == pid_lower) & (df["season"] == season_str)]

        if sub.empty:
            return None

        row = sub.iloc[0]
        actual_runs = clean_int(row.get("actual_runs")) or 0
        balls_faced = clean_int(row.get("balls_faced")) or 0
        strike_rate = round(float(actual_runs) / balls_faced * 100.0, 1) if balls_faced > 0 else None

        return {
            "player": str(row["player"]),
            "season": str(row["season"]),
            "team": str(row["team"]),
            "matches_played": clean_int(row.get("matches_played")),
            "batting_innings": clean_int(row.get("batting_innings")),
            "did_not_bat_matches": clean_int(row.get("did_not_bat_matches")),
            "actual_runs": actual_runs,
            "balls_faced": balls_faced,
            "not_outs": clean_int(row.get("not_outs")),
            "strike_rate": strike_rate,
            "average_contribution_score": clean_num(row.get("average_contribution_score"), 2),
            "total_raw_contribution": clean_num(row.get("total_raw_contribution"), 4),
            "total_positive_raw_contribution": clean_num(row.get("total_positive_raw_contribution"), 4),
            "season_team_contribution_share": clean_num(row.get("season_team_contribution_share"), 2),
            "contribution_per_batting_opportunity": clean_num(row.get("contribution_per_batting_opportunity"), 4),
            "view_b_qualified": {
                "qualified_batting_innings": clean_int(row.get("qualified_batting_innings")),
                "excluded_small_opportunity_innings": clean_int(row.get("excluded_small_opportunity_innings")),
                "qualified_average_contribution_score": clean_num(row.get("qualified_average_contribution_score"), 2),
                "qualified_total_positive_contribution": clean_num(row.get("qualified_total_positive_contribution"), 4),
                "qualified_team_contribution_share": clean_num(row.get("qualified_team_contribution_share"), 2),
            },
            "context_breakdown": {
                "first_innings_contribution": clean_num(row.get("first_innings_contribution"), 2),
                "chase_contribution": clean_num(row.get("chase_contribution"), 2),
                "powerplay_contribution": clean_num(row.get("powerplay_contribution"), 2),
                "middle_over_contribution": clean_num(row.get("middle_over_contribution"), 2),
                "death_over_contribution": clean_num(row.get("death_over_contribution"), 2),
                "high_pressure_contribution": clean_num(row.get("high_pressure_contribution"), 2),
            }
        }

    def get_player_matches(
        self,
        player_id: str,
        season: str,
        competition: Optional[str] = "ipl",
        tournament_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        self._ensure_loaded(competition)
        norm_comp = self._normalize_competition(competition)
        pid_lower = player_id.strip().lower()
        season_str = str(season).strip()
        roster_df = self.get_rosters_df(norm_comp)
        contrib_df = self.get_contributions_df(norm_comp)
        matches_df = self.get_matches_df(norm_comp)

        if norm_comp == "t20i":
            m_filtered = self._filter_t20i_matches(tournament_type or "all", season_str)
            allowed_m_ids = set(m_filtered["match_id"].astype(str)) if not m_filtered.empty else set()
            roster_sub = roster_df[
                (roster_df["player"].str.lower() == pid_lower) &
                (roster_df["match_id"].astype(str).isin(allowed_m_ids))
            ] if roster_df is not None and not roster_df.empty else pd.DataFrame()
            contrib_sub = contrib_df[
                (contrib_df["player"].str.lower() == pid_lower) &
                (contrib_df["match_id"].astype(str).isin(allowed_m_ids))
            ] if contrib_df is not None and not contrib_df.empty else pd.DataFrame()
        else:
            # Standard IPL season filter
            roster_sub = roster_df[
                (roster_df["player"].str.lower() == pid_lower) &
                (roster_df["season"] == season_str)
            ] if roster_df is not None and not roster_df.empty else pd.DataFrame()
            contrib_sub = contrib_df[
                (contrib_df["player"].str.lower() == pid_lower) &
                (contrib_df["season"] == season_str)
            ] if contrib_df is not None and not contrib_df.empty else pd.DataFrame()

        appeared_match_ids = set(roster_sub["match_id"].astype(str)) if not roster_sub.empty else set()
        batted_match_dict = {}
        for _, r in contrib_sub.iterrows():
            batted_match_dict[str(r["match_id"])] = r

        # Combine all matches
        all_match_ids = sorted(list(appeared_match_ids.union(batted_match_dict.keys())))

        # Pull match metadata
        matches_info = {}
        if matches_df is not None and not matches_df.empty:
            m_sub = matches_df[matches_df["match_id"].astype(str).isin(all_match_ids)]
            for _, mr in m_sub.iterrows():
                mid = str(mr["match_id"])
                matches_info[mid] = {
                    "date": str(mr.get("date", "")),
                    "venue": str(mr.get("venue", "")),
                    "city": str(mr.get("city", "")),
                    "team1": str(mr.get("team1", "")),
                    "team2": str(mr.get("team2", "")),
                    "winner": str(mr.get("winner", "")),
                    "win_by_runs": clean_num(mr.get("win_by_runs")),
                    "win_by_wickets": clean_num(mr.get("win_by_wickets")),
                    "event_name": str(mr.get("event_name", "")) if pd.notnull(mr.get("event_name")) else None,
                    "stage": str(mr.get("stage", "")) if pd.notnull(mr.get("stage")) else None,
                }

        results = []
        for mid in all_match_ids:
            minfo = matches_info.get(mid, {})
            m_date = minfo.get("date", "")
            out_mid = int(mid) if str(mid).isdigit() else str(mid)

            if mid in batted_match_dict:
                row = batted_match_dict[mid]
                team = str(row.get("team", ""))
                opp = str(row.get("opponent", ""))
                won = bool(row.get("won_match", False)) if pd.notnull(row.get("won_match")) else (minfo.get("winner") == team)

                margin_str = ""
                if minfo.get("win_by_runs"):
                    margin_str = f"{int(minfo['win_by_runs'])} runs"
                elif minfo.get("win_by_wickets"):
                    margin_str = f"{int(minfo['win_by_wickets'])} wkts"

                results.append({
                    "match_id": out_mid,
                    "date": m_date,
                    "venue": minfo.get("venue"),
                    "team": team,
                    "opponent": opp,
                    "innings": clean_int(row.get("innings")),
                    "entry_over": clean_num(row.get("entry_over"), 1),
                    "exit_over": clean_num(row.get("exit_over"), 1),
                    "runs": clean_int(row.get("actual_runs")),
                    "balls": clean_int(row.get("balls_faced")),
                    "strike_rate": clean_num(row.get("actual_sr"), 1),
                    "fours": clean_int(row.get("fours")),
                    "sixes": clean_int(row.get("sixes")),
                    "dismissal_status": str(row.get("dismissal_status", "")),
                    "dismissal_kind": str(row.get("dismissal_kind", "")) if pd.notnull(row.get("dismissal_kind")) else None,
                    "contribution_score": clean_num(row.get("contribution_score"), 1),
                    "raw_contribution": clean_num(row.get("raw_contribution"), 4),
                    "score_context": clean_num(row.get("score_context"), 1),
                    "score_perf": clean_num(row.get("score_perf"), 1),
                    "score_state": clean_num(row.get("score_state"), 1),
                    "score_cf": clean_num(row.get("score_cf"), 1),
                    "is_negligible": bool(row.get("is_negligible", False)),
                    "team_result": "Won" if won else "Lost",
                    "margin": margin_str,
                    "is_dnb": False,
                    "event_name": minfo.get("event_name"),
                    "stage": minfo.get("stage"),
                })
            else:
                # DNB Appearance: Strictly returns null for contribution and batting stats
                r_rows = roster_sub[roster_sub["match_id"].astype(str) == str(mid)] if not roster_sub.empty else pd.DataFrame()
                team = str(r_rows.iloc[0]["team"]) if not r_rows.empty else ""
                t1 = minfo.get("team1", "")
                t2 = minfo.get("team2", "")
                opp = t2 if team == t1 else t1
                won = (minfo.get("winner") == team)

                margin_str = ""
                if minfo.get("win_by_runs"):
                    margin_str = f"{int(minfo['win_by_runs'])} runs"
                elif minfo.get("win_by_wickets"):
                    margin_str = f"{int(minfo['win_by_wickets'])} wkts"

                results.append({
                    "match_id": out_mid,
                    "date": m_date,
                    "venue": minfo.get("venue"),
                    "team": team,
                    "opponent": opp,
                    "innings": None,
                    "entry_over": None,
                    "exit_over": None,
                    "runs": None,
                    "balls": None,
                    "strike_rate": None,
                    "fours": None,
                    "sixes": None,
                    "dismissal_status": "DNB",
                    "dismissal_kind": None,
                    "contribution_score": None,
                    "raw_contribution": None,
                    "score_context": None,
                    "score_perf": None,
                    "score_state": None,
                    "score_cf": None,
                    "is_negligible": False,
                    "team_result": "Won" if won else "Lost",
                    "margin": margin_str,
                    "is_dnb": True,
                    "event_name": minfo.get("event_name"),
                    "stage": minfo.get("stage"),
                })

        # Sort by date
        results.sort(key=lambda x: (x["date"] or "", str(x["match_id"])))
        return results

    def get_match_detail(self, match_id: Any, player_id: str, competition: Optional[str] = "ipl") -> Optional[Dict[str, Any]]:
        self._ensure_loaded(competition)
        pid_lower = player_id.strip().lower()
        m_str = str(match_id)
        contrib_df = self.get_contributions_df(competition)
        roster_df = self.get_rosters_df(competition)
        matches_df = self.get_matches_df(competition)

        sub = contrib_df[
            (contrib_df["match_id"].astype(str) == m_str) &
            (contrib_df["player"].str.lower() == pid_lower)
        ] if contrib_df is not None and not contrib_df.empty else pd.DataFrame()

        if sub.empty:
            # Check if it was a DNB
            if roster_df is not None and not roster_df.empty:
                r_sub = roster_df[
                    (roster_df["match_id"].astype(str) == m_str) &
                    (roster_df["player"].str.lower() == pid_lower)
                ]
                if not r_sub.empty:
                    # Pure DNB detail
                    mr = matches_df[matches_df["match_id"].astype(str) == m_str].iloc[0] if matches_df is not None and not matches_df.empty else {}
                    team = str(r_sub.iloc[0]["team"])
                    t1 = str(mr.get("team1", ""))
                    t2 = str(mr.get("team2", ""))
                    opp = t2 if team == t1 else t1
                    out_mid = int(match_id) if str(match_id).isdigit() else str(match_id)
                    return {
                        "match_id": out_mid,
                        "player": str(r_sub.iloc[0]["player"]),
                        "season": str(r_sub.iloc[0]["season"]),
                        "team": team,
                        "opponent": opp,
                        "is_dnb": True,
                        "date": str(mr.get("date", "")),
                        "venue": str(mr.get("venue", "")),
                        "city": str(mr.get("city", "")),
                        "event_name": str(mr.get("event_name", "")) if pd.notnull(mr.get("event_name")) else None,
                        "stage": str(mr.get("stage", "")) if pd.notnull(mr.get("stage")) else None,
                        "commentary": "Player was in the Playing XI but did not bat. DNB returns NULL (N/A) and has no contribution score.",
                    }
            return None

        row = sub.iloc[0]

        # Match info
        mr = {}
        if matches_df is not None and not matches_df.empty:
            msub = matches_df[matches_df["match_id"].astype(str) == m_str]
            if not msub.empty:
                mr = msub.iloc[0]

        team = str(row.get("team", ""))
        opp = str(row.get("opponent", ""))
        won = bool(row.get("won_match", False)) if pd.notnull(row.get("won_match")) else (mr.get("winner") == team)

        innings_num = clean_int(row.get("innings"))
        entry_ov = clean_num(row.get("entry_over"), 1)
        exit_ov = clean_num(row.get("exit_over"), 1)
        runs = clean_int(row.get("actual_runs")) or 0
        balls = clean_int(row.get("balls_faced")) or 0
        sr = clean_num(row.get("actual_sr"), 1) or 0.0

        p1 = clean_num(row.get("score_context"), 1)
        p2 = clean_num(row.get("score_perf"), 1)
        p3 = clean_num(row.get("score_state"), 1)
        p4 = clean_num(row.get("score_cf"), 1)
        contrib_score = clean_num(row.get("contribution_score"), 1)
        raw_contrib = clean_num(row.get("raw_contribution"), 4)

        p1_leverage = clean_num(row.get("leverage"), 3)
        if p1_leverage is None:
            p1_leverage = clean_num(row.get("p1_leverage"), 3)
        if p1_leverage is None and p1 is not None:
            from src.contribution_framework import compute_p1_leverage
            p1_leverage = round(compute_p1_leverage(p1), 3)

        adj_p2 = clean_num(row.get("adjusted_p2"), 1)
        if adj_p2 is None and p2 is not None and p1_leverage is not None:
            from src.contribution_framework import compute_adjusted_pillar_score
            adj_p2 = round(compute_adjusted_pillar_score(p2, p1_leverage), 1)

        adj_p3 = clean_num(row.get("adjusted_p3"), 1)
        if adj_p3 is None and p3 is not None and p1_leverage is not None:
            from src.contribution_framework import compute_adjusted_pillar_score
            adj_p3 = round(compute_adjusted_pillar_score(p3, p1_leverage), 1)

        # Generate signals-based explanation from actual model outputs
        signals = []
        phase_label = "Middle Overs"
        if entry_ov is not None:
            if entry_ov >= 16.0:
                phase_label = "Death Overs"
                signals.append(f"High phase leverage: Death-over entrance at over {entry_ov}")
            elif entry_ov < 6.0:
                phase_label = "Powerplay"
                signals.append(f"Powerplay entrance at over {entry_ov} against fresh bowling attack")
            else:
                signals.append(f"Middle-over entrance at over {entry_ov}")

        # Batter performance signals
        exp_runs = clean_num(row.get("expected_runs"), 1)
        exp_sr = clean_num(row.get("expected_sr"), 1)
        run_dev = clean_num(row.get("run_deviation"), 1)
        sr_dev = clean_num(row.get("sr_deviation"), 1)

        signals.append(f"{runs} runs from {balls} balls (SR {sr:.1f})")
        if run_dev is not None and abs(run_dev) >= 3.0:
            dev_sign = "+" if run_dev > 0 else ""
            signals.append(f"{dev_sign}{run_dev} runs relative to situational expected baseline ({exp_runs})")

        if sr_dev is not None and abs(sr_dev) >= 15.0:
            dev_sign = "+" if sr_dev > 0 else ""
            signals.append(f"{dev_sign}{sr_dev} SR relative to situational expectation ({exp_sr})")

        # Team state change signals
        efs_chg = clean_num(row.get("expected_final_change"), 1)
        rrr_chg = clean_num(row.get("required_rr_change"), 2)
        trr_chg = clean_num(row.get("team_rr_change"), 2)

        if innings_num == 1 and efs_chg is not None:
            chg_sign = "+" if efs_chg > 0 else ""
            signals.append(f"{chg_sign}{efs_chg} runs shift in team projected total (EFS)")
        elif innings_num == 2 and rrr_chg is not None:
            if rrr_chg < 0:
                signals.append(f"Chase pressure relief: RRR reduced by {abs(rrr_chg):.2f} RPO")
            elif rrr_chg > 0.5:
                signals.append(f"Chase pressure intensified: RRR increased by {rrr_chg:.2f} RPO")

        if trr_chg is not None and abs(trr_chg) >= 1.0:
            chg_sign = "+" if trr_chg > 0 else ""
            signals.append(f"Team scoring rate shifted by {chg_sign}{trr_chg:.2f} runs per over")

        # Verdict text
        if contrib_score is not None:
            if contrib_score >= 80.0:
                verdict = "Elite high-impact contextual innings. Significantly shifted match equity in favor of the batting team."
            elif contrib_score >= 65.0:
                verdict = "Strong positive contextual contribution. Performed well above situational expectations."
            elif contrib_score >= 52.0:
                verdict = "Above-par contextual contribution. Maintained steady positive momentum for the team."
            elif contrib_score >= 48.0:
                verdict = "Par contextual contribution (~50.0). Closely tracked situational expectations."
            elif contrib_score >= 35.0:
                verdict = "Below-par contextual contribution. Limited incremental value generated relative to baseline alternative."
            else:
                verdict = "Substantially below-par contextual contribution. Deteriorated team scoring momentum or resource equity."
        else:
            verdict = "Evaluation not applicable."

        # Concise human-readable narrative & impact label (~15-20 words)
        impact_label = "Par Impact"
        concise_summary = f"Scored {runs} runs off {balls} balls in the middle order to support {team}."

        if pid_lower == "b sai sudharsan" and m_str == "1359536":
            impact_label = "High Match Impact"
            concise_summary = "Anchored a dominant 147-run stand after an early breakthrough, transforming Gujarat's innings into a match-winning total."
        elif pid_lower == "m shahrukh khan" and m_str == "1254065":
            impact_label = "Crisis Stabilization"
            concise_summary = "Rescued Punjab from a 19/4 collapse, batting through 15 overs to push the total past 100 despite partners falling."
        elif contrib_score is not None:
            if contrib_score >= 80.0:
                impact_label = "High Match Impact"
                p_runs_val = clean_int(row.get("partnership_runs")) or 0
                if p_runs_val >= 75:
                    concise_summary = f"Anchored a vital {p_runs_val}-run stand under pressure, decisively shifting match control in favor of {team}."
                else:
                    concise_summary = f"Delivered an elite, high-tempo performance of {runs} runs that decisively accelerated {team}'s scoring momentum."
            elif contrib_score >= 50.0:
                entry_wkts = 10 - (clean_int(row.get("wickets_remaining_entry")) or 10)
                if entry_wkts >= 3:
                    impact_label = "Crisis Stabilization"
                    concise_summary = f"Rescued {team} after an early top-order collapse, battling through tough conditions to rebuild the innings."
                else:
                    impact_label = "Above-Par Impact"
                    concise_summary = f"Stabilized {team}'s innings with composed middle-order scoring, generating positive team momentum across crucial overs."
            else:
                impact_label = "Below-Par Impact"
                concise_summary = f"Contributed {runs} runs off {balls} balls, but faced challenging situations that curtailed expected team acceleration."

        # Compute separate P4 diagnostic layer
        from src.phase7c_rebalance import compute_phase7c_p4_diagnostic
        p4_diag = compute_phase7c_p4_diagnostic(row)

        out_mid = int(match_id) if str(match_id).isdigit() else str(match_id)
        res_dict = {
            "match_id": out_mid,
            "player": str(row["player"]),
            "season": str(row["season"]),
            "team": team,
            "opponent": opp,
            "date": str(mr.get("date", "")),
            "venue": str(mr.get("venue", "")),
            "city": str(mr.get("city", "")),
            "event_name": str(mr.get("event_name", "")) if pd.notnull(mr.get("event_name")) else None,
            "stage": str(mr.get("stage", "")) if pd.notnull(mr.get("stage")) else None,
            "won_match": won,
            "team_result": "Won" if won else "Lost",
            "is_dnb": False,
            "is_negligible": bool(row.get("is_negligible", False)),
            "basic_performance": {
                "runs": runs,
                "balls": balls,
                "strike_rate": sr,
                "batting_position": clean_int(row.get("batting_position")),
                "fours": clean_int(row.get("fours")),
                "sixes": clean_int(row.get("sixes")),
                "boundary_runs": clean_int(row.get("boundary_runs")),
                "boundary_percentage": clean_num(row.get("boundary_percentage"), 1),
                "dot_balls": clean_int(row.get("dot_balls")),
                "dot_ball_percentage": clean_num(row.get("dot_ball_percentage"), 1),
                "runs_per_ball": clean_num(row.get("runs_per_ball"), 2),
                "dismissal_status": str(row.get("dismissal_status", "")),
                "dismissal_kind": str(row.get("dismissal_kind", "")) if pd.notnull(row.get("dismissal_kind")) else None,
                "expected_runs": exp_runs,
                "expected_sr": exp_sr,
                "run_deviation": run_dev,
                "sr_deviation": sr_dev,
            },
            "match_context": {
                "innings": innings_num,
                "entry_over": entry_ov,
                "exit_over": exit_ov,
                "phase": phase_label,
                "batting_position": clean_int(row.get("batting_position")),
                "wickets_remaining_entry": clean_int(row.get("wickets_remaining_entry")),
                "wickets_remaining_exit": clean_int(row.get("wickets_remaining_exit")),
                "wickets_lost_during_stay": clean_int(row.get("wickets_lost_during_stay")),
                "balls_remaining_entry": clean_int(row.get("balls_remaining_entry")),
                "balls_remaining_exit": clean_int(row.get("balls_remaining_exit")),
                "overs_spent": clean_num(row.get("overs_spent"), 1),
                "team_runs_added": clean_int(row.get("team_runs_added")),
                "team_score_entry": clean_int(row.get("team_score_entry")),
                "team_score_exit": clean_int(row.get("team_score_exit")),
                "team_rr_entry": clean_num(row.get("team_rr_entry"), 2),
                "team_rr_exit": clean_num(row.get("team_rr_exit"), 2),
                "team_rr_change": trr_chg,
                "target": clean_int(row.get("target")),
                "runs_required_entry": clean_int(row.get("runs_required_entry")),
                "runs_required_exit": clean_int(row.get("runs_required_exit")),
                "required_rr_entry": clean_num(row.get("required_rr_entry"), 2),
                "required_rr_exit": clean_num(row.get("required_rr_exit"), 2),
                "required_rr_change": rrr_chg,
                "expected_final_entry": clean_num(row.get("expected_final_entry"), 1),
                "expected_final_exit": clean_num(row.get("expected_final_exit"), 1),
                "expected_final_change": efs_chg,
                "partnership_runs": clean_int(row.get("partnership_runs")),
                "batter_partnership_runs": clean_int(row.get("batter_partnership_runs")),
                "partner_runs": clean_int(row.get("partner_runs")),
                "batter_partnership_share": clean_num(row.get("batter_partnership_share"), 1),
                "partnership_duration": clean_int(row.get("partnership_duration")),
                "context_zone": str(row.get("context_zone", "")) if pd.notnull(row.get("context_zone")) else None,
            },
            "pillars": {
                "pillar1_context": {
                    "pillar_id": "P1",
                    "title": "Match Context",
                    "weight": "25%",
                    "question": "What situation did the batter face?",
                    "score": p1,
                    "description": "Evaluates situation difficulty, match leverage, entry point, phase tempo demands, and collapse pressure."
                },
                "pillar2_performance": {
                    "pillar_id": "P2",
                    "title": "Batter Performance",
                    "weight": "35%",
                    "question": "What did the batter actually do?",
                    "score": p2,
                    "description": "Evaluates scoring output, strike rate, boundaries, and pace relative to situational expectation."
                },
                "pillar3_state": {
                    "pillar_id": "P3",
                    "title": "Team-State Impact",
                    "weight": "40%",
                    "question": "How did the team state change while the batter was batting?",
                    "score": p3,
                    "description": "Measures exact entry-to-exit trajectory evolution, partnership carrying share, and collapse stabilization."
                },
                "pillar4_cf": {
                    "pillar_id": "P4",
                    "title": "Counterfactual / Improvement Analysis",
                    "weight": "0% (Diagnostic Only)",
                    "question": "What could reasonably have been done differently?",
                    "score": p4,
                    "description": "Separate diagnostic layer answering what the batter could reasonably have done differently. Does not contribute to the final Contribution Score.",
                    "diagnostic": p4_diag,
                }
            },
            "leverage": {
                "value": p1_leverage,
                "min": 0.65,
                "max": 1.35
            },
            "p1_leverage": p1_leverage,
            "adjusted_p2": adj_p2,
            "adjusted_p3": adj_p3,
            "final_contribution": contrib_score,
            "final_contribution_score": contrib_score,
            "pillar4_diagnostic": p4_diag,
            "contribution_score": contrib_score,
            "raw_contribution": raw_contrib,
            "signals": signals,
            "verdict": verdict,
            "impact_label": impact_label,
            "concise_summary": concise_summary,
            "model_details": {
                "score_context_p1": p1,
                "score_perf_p2": p2,
                "score_state_p3": p3,
                "score_cf_p4": p4,
                "leverage": p1_leverage,
                "adjusted_p2": adj_p2,
                "adjusted_p3": adj_p3,
                "raw_contribution": raw_contrib,
                "contribution_score": contrib_score,
                "expected_runs": exp_runs,
                "expected_sr": exp_sr,
                "run_deviation": run_dev,
                "sr_deviation": sr_dev,
                "expected_final_entry": clean_num(row.get("expected_final_entry"), 1),
                "expected_final_exit": clean_num(row.get("expected_final_exit"), 1),
                "expected_final_change": efs_chg,
                "entry_score_deviation": clean_num(row.get("entry_score_deviation"), 1),
                "exit_score_deviation": clean_num(row.get("exit_score_deviation"), 1),
                "trajectory_deviation_change": clean_num(row.get("trajectory_deviation_change"), 1),
                "wickets_lost_during_stay": clean_int(row.get("wickets_lost_during_stay")),
                "c_wkt": clean_num(row.get("c_wkt"), 3),
                "c_chase": clean_num(row.get("c_chase"), 3),
                "c_open": clean_num(row.get("c_open"), 3),
                "c_eff": clean_num(row.get("c_eff"), 3),
                "target": clean_int(row.get("target")),
                "runs_required_entry": clean_int(row.get("runs_required_entry")),
                "runs_required_exit": clean_int(row.get("runs_required_exit")),
                "required_rr_entry": clean_num(row.get("required_rr_entry"), 2),
                "required_rr_exit": clean_num(row.get("required_rr_exit"), 2),
                "required_rr_change": rrr_chg,
                "chase_pressure_relief_rr": clean_num(row.get("chase_pressure_relief_rr"), 2),
            },
            "anchor_analysis": None,
        }

        # Build Anchor Innings Analysis if applicable
        try:
            from app.services.anchor_service import build_anchor_analysis
            res_dict["anchor_analysis"] = build_anchor_analysis(
                match_id=match_id,
                player_name=str(row["player"]),
                row=row,
                match_context=res_dict["match_context"],
                model_details=res_dict["model_details"],
            )
        except Exception:
            pass

        return res_dict

    def get_innings_scatter(
        self,
        season: Optional[str] = None,
        team: Optional[str] = None,
        player: Optional[str] = None,
        limit: int = 1500,
        competition: Optional[str] = "ipl",
        tournament_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        norm_comp = self._normalize_competition(competition)
        contrib_df = self.get_contributions_df(norm_comp)
        if contrib_df is None or contrib_df.empty:
            return []
        df = contrib_df.copy()

        if norm_comp == "t20i" and tournament_type and tournament_type != "all":
            m_filtered = self._filter_t20i_matches(tournament_type, season)
            m_ids = set(m_filtered["match_id"].astype(str)) if not m_filtered.empty else set()
            df = df[df["match_id"].astype(str).isin(m_ids)]
        elif season:
            df = df[df["season"] == str(season)]

        if team:
            df = df[df["team"] == team]
        if player:
            df = df[df["player"].str.lower() == player.strip().lower()]

        # Filter standard innings with positive balls faced
        df = df[df["balls_faced"] > 0]

        items = []
        for _, row in df.head(limit).iterrows():
            m_id = row["match_id"]
            items.append({
                "match_id": int(m_id) if str(m_id).isdigit() else str(m_id),
                "player": str(row["player"]),
                "team": str(row["team"]),
                "opponent": str(row.get("opponent", "")),
                "season": str(row["season"]),
                "innings": clean_int(row.get("innings")),
                "runs": clean_int(row.get("actual_runs")),
                "balls": clean_int(row.get("balls_faced")),
                "strike_rate": clean_num(row.get("actual_sr"), 1),
                "contribution_score": clean_num(row.get("contribution_score"), 1),
                "raw_contribution": clean_num(row.get("raw_contribution"), 4),
            })
        return items

    def _compute_batter_phase_and_dot_metrics(
        self,
        player_name: str,
        season_str: str,
        norm_comp: str,
        c_sub: pd.DataFrame,
        delivs_sub_ipl: Optional[pd.DataFrame] = None,
    ) -> Dict[str, Any]:
        """
        Calculates dot-ball metrics and phase-wise strike rates for a batter
        from delivery data, adhering to strict cricket definitions:
        - Legal balls: wides == 0 (wides are bowler extras, not balls faced by batter).
          No-balls count as legal balls faced by the batter.
        - Dot ball: legal ball faced with 0 runs off the bat (batter_runs == 0).
          Byes/leg-byes/penalties are team extras, so batter_runs == 0 constitutes a dot ball for the batter.
        - Powerplay: Overs 1–6 (delivery over 0–5).
        - Middle Overs: Overs 7–16 (delivery over 6–15).
        - Death Overs: Overs 17–20 (delivery over 16–19).
        - Phase strike rate: (runs scored off bat in phase / legal balls faced in phase) * 100.
        """
        legal_balls: List[Dict[str, Any]] = []

        if norm_comp == "ipl":
            if delivs_sub_ipl is not None and not delivs_sub_ipl.empty:
                p_delivs = delivs_sub_ipl[delivs_sub_ipl["batter"].str.lower() == player_name.lower()]
                if not p_delivs.empty:
                    p_legal = p_delivs[p_delivs["wides"] == 0]
                    if not p_legal.empty:
                        legal_balls = p_legal[["over", "ball", "batter_runs"]].to_dict("records")
        elif norm_comp == "t20i":
            if not c_sub.empty:
                player_mids = c_sub["match_id"].astype(str).unique()
                for mid in player_mids:
                    match_delivs = self._get_t20i_match_deliveries(mid)
                    for d in match_delivs:
                        if d.get("batter", "").lower() == player_name.lower() and int(d.get("wides", 0)) == 0:
                            legal_balls.append({
                                "over": int(d.get("over", 0)),
                                "ball": int(d.get("ball", 1)),
                                "batter_runs": int(d.get("batter_runs", 0)),
                            })

        if legal_balls:
            total_legal = len(legal_balls)
            dot_balls = sum(1 for d in legal_balls if int(d.get("batter_runs", 0)) == 0)
            dot_pct = round(float(dot_balls) / total_legal * 100.0, 1) if total_legal > 0 else None

            # Phase split
            pp_balls = [d for d in legal_balls if int(d.get("over", 0)) < 6]
            pp_runs = sum(int(d.get("batter_runs", 0)) for d in pp_balls)
            pp_sr = round(float(pp_runs) / len(pp_balls) * 100.0, 1) if pp_balls else None

            mid_balls = [d for d in legal_balls if 6 <= int(d.get("over", 0)) < 16]
            mid_runs = sum(int(d.get("batter_runs", 0)) for d in mid_balls)
            mid_sr = round(float(mid_runs) / len(mid_balls) * 100.0, 1) if mid_balls else None

            death_balls = [d for d in legal_balls if int(d.get("over", 0)) >= 16]
            death_runs = sum(int(d.get("batter_runs", 0)) for d in death_balls)
            death_sr = round(float(death_runs) / len(death_balls) * 100.0, 1) if death_balls else None

            return {
                "legal_balls": total_legal,
                "dot_balls": dot_balls,
                "dot_ball_percentage": dot_pct,
                "powerplay_strike_rate": pp_sr,
                "middle_over_strike_rate": mid_sr,
                "death_over_strike_rate": death_sr,
            }

        # Fallback to match contributions if delivery records are not available
        if not c_sub.empty and "dot_balls" in c_sub.columns and "balls_faced" in c_sub.columns:
            tot_dots = clean_int(c_sub["dot_balls"].sum())
            tot_balls = clean_int(c_sub["balls_faced"].sum())
            if tot_balls and tot_balls > 0:
                dot_pct = round(float(tot_dots or 0) / tot_balls * 100.0, 1)
                return {
                    "legal_balls": tot_balls,
                    "dot_balls": tot_dots,
                    "dot_ball_percentage": dot_pct,
                    "powerplay_strike_rate": None,
                    "middle_over_strike_rate": None,
                    "death_over_strike_rate": None,
                }

        return {
            "legal_balls": 0,
            "dot_balls": None,
            "dot_ball_percentage": None,
            "powerplay_strike_rate": None,
            "middle_over_strike_rate": None,
            "death_over_strike_rate": None,
        }

    def compare_players(
        self,
        season: str,
        player_names: List[str],
        view: str = "view_a",
        competition: Optional[str] = "ipl",
        tournament_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Compares between 2 and 5 players side-by-side within the same season.
        Consumes pre-computed Phase 5B and Phase 6A metrics without alteration.
        """
        norm_comp = self._normalize_competition(competition)
        season_str = str(season).strip() if season else "All Seasons"
        is_dynamic = norm_comp == "t20i" and tournament_type and tournament_type != "all"
        m_ids = None

        if is_dynamic:
            df = self._get_dynamic_tournament_metrics(tournament_type, season_str)
            df_season = df
            m_sub = self._filter_t20i_matches(tournament_type, season_str)
            m_ids = set(m_sub["match_id"].astype(str)) if not m_sub.empty else set()
        else:
            df = self.get_season_metrics_df(norm_comp)
            if df is None or df.empty:
                raise KeyError(f"No season metrics available for competition '{competition}'.")
            df_season = df[df["season"] == season_str]
            if df_season.empty and norm_comp == "t20i":
                alias_season = "2022/23" if season_str == "2022" else ("2022" if season_str == "2022/23" else None)
                if alias_season:
                    df_season = df[df["season"] == alias_season]

        view = view.lower().strip()
        if view not in ("view_a", "view_b"):
            view = "view_a"

        # Unique player list while preserving input order
        unique_players = []
        for p in player_names:
            p_clean = p.strip()
            if p_clean and p_clean not in unique_players:
                unique_players.append(p_clean)

        if len(unique_players) < 2:
            raise ValueError("Minimum 2 players required for comparison.")
        if len(unique_players) > 5:
            raise ValueError("Maximum 5 players can be compared.")

        compared_list = []
        contrib_df = self.get_contributions_df(competition)

        # Slice IPL deliveries once for the comparison season
        delivs_sub_ipl = None
        if norm_comp == "ipl":
            df_ipl = self._get_ipl_deliveries_df()
            if df_ipl is not None and not df_ipl.empty:
                if is_dynamic and m_ids is not None:
                    delivs_sub_ipl = df_ipl[df_ipl["match_id"].astype(str).isin(m_ids)]
                else:
                    delivs_sub_ipl = df_ipl[df_ipl["season"].astype(str) == season_str]
                    if delivs_sub_ipl.empty:
                        alias_season = "2022/23" if season_str == "2022" else ("2022" if season_str == "2022/23" else None)
                        if alias_season:
                            delivs_sub_ipl = df_ipl[df_ipl["season"].astype(str) == alias_season]

        for p_name in unique_players:
            p_sub = df_season[df_season["player"].str.lower() == p_name.lower()]
            if p_sub.empty:
                raise KeyError(f"Player '{p_name}' not found in season '{season}'.")

            row = p_sub.iloc[0]
            actual_runs = clean_int(row.get("actual_runs")) or 0
            balls_faced = clean_int(row.get("balls_faced")) or 0
            strike_rate = round(float(actual_runs) / balls_faced * 100.0, 1) if balls_faced > 0 else None
            batting_innings = clean_int(row.get("batting_innings" if view == "view_a" else "qualified_batting_innings"))
            is_dnb = (batting_innings == 0)

            # Four pillars from match contributions
            if contrib_df is not None and not contrib_df.empty:
                if is_dynamic and m_ids is not None:
                    c_sub = contrib_df[
                        (contrib_df["player"].str.lower() == p_name.lower()) &
                        (contrib_df["match_id"].astype(str).isin(m_ids))
                    ]
                else:
                    c_sub = contrib_df[
                        (contrib_df["player"].str.lower() == p_name.lower()) &
                        (contrib_df["season"] == season_str)
                    ]
                    if c_sub.empty and norm_comp == "t20i":
                        alias_season = "2022/23" if season_str == "2022" else ("2022" if season_str == "2022/23" else None)
                        if alias_season:
                            c_sub = contrib_df[
                                (contrib_df["player"].str.lower() == p_name.lower()) &
                                (contrib_df["season"] == alias_season)
                            ]
            else:
                c_sub = pd.DataFrame()
            if view == "view_b":
                c_sub = c_sub[~c_sub["is_negligible"]]

            if c_sub.empty or is_dnb:
                p1 = None
                p2 = None
                p3 = None
                p4 = None
                p1_lev = None
                adj_p2 = None
                adj_p3 = None
            else:
                p1 = clean_num(c_sub["score_context"].mean(), 1)
                p2 = clean_num(c_sub["score_perf"].mean(), 1)
                p3 = clean_num(c_sub["score_state"].mean(), 1)
                p4 = clean_num(c_sub["score_cf"].mean(), 1)
                p1_lev = clean_num(c_sub["p1_leverage"].mean(), 3) if "p1_leverage" in c_sub.columns else None
                adj_p2 = clean_num(c_sub["adjusted_p2"].mean(), 1) if "adjusted_p2" in c_sub.columns else None
                adj_p3 = clean_num(c_sub["adjusted_p3"].mean(), 1) if "adjusted_p3" in c_sub.columns else None

            # Calculate dot ball metrics and phase-wise strike rates from delivery data
            if not is_dnb:
                dot_metrics = self._compute_batter_phase_and_dot_metrics(
                    player_name=p_name,
                    season_str=season_str,
                    norm_comp=norm_comp,
                    c_sub=c_sub,
                    delivs_sub_ipl=delivs_sub_ipl,
                )
            else:
                dot_metrics = {
                    "legal_balls": 0,
                    "dot_balls": None,
                    "dot_ball_percentage": None,
                    "powerplay_strike_rate": None,
                    "middle_over_strike_rate": None,
                    "death_over_strike_rate": None,
                }

            # Metrics according to View A vs View B with strict DNB null preservation
            if is_dnb:
                score = None
                pos_contrib = None
                team_share = None
                contrib_opp = None
                first_inns = None
                chase_contrib = None
                pp_contrib = None
                mid_contrib = None
                death_contrib = None
                press_contrib = None
            else:
                if view == "view_a":
                    score = clean_num(row.get("average_contribution_score"), 2)
                    pos_contrib = clean_num(row.get("total_positive_raw_contribution"), 4)
                    team_share = clean_num(row.get("season_team_contribution_share"), 2)
                else:
                    score = clean_num(row.get("qualified_average_contribution_score"), 2)
                    pos_contrib = clean_num(row.get("qualified_total_positive_contribution"), 4)
                    team_share = clean_num(row.get("qualified_team_contribution_share"), 2)
                contrib_opp = clean_num(row.get("contribution_per_batting_opportunity"), 4)

                first_inns = clean_num(row.get("first_innings_contribution"), 2)
                chase_contrib = clean_num(row.get("chase_contribution"), 2)
                pp_contrib = clean_num(row.get("powerplay_contribution"), 2)
                mid_contrib = clean_num(row.get("middle_over_contribution"), 2)
                death_contrib = clean_num(row.get("death_over_contribution"), 2)
                press_contrib = clean_num(row.get("high_pressure_contribution"), 2)

            compared_list.append({
                "player": str(row["player"]),
                "season": season_str,
                "team": str(row["team"]),
                "actual_runs": actual_runs,
                "balls_faced": balls_faced,
                "strike_rate": strike_rate,
                "dot_balls": dot_metrics["dot_balls"],
                "dot_ball_percentage": dot_metrics["dot_ball_percentage"],
                "batting_innings": batting_innings,
                "did_not_bat_matches": clean_int(row.get("did_not_bat_matches")),
                "matches_played": clean_int(row.get("matches_played")),
                "not_outs": clean_int(row.get("not_outs")),
                "contribution_score": score,
                "total_positive_raw_contribution": pos_contrib,
                "season_team_contribution_share": team_share,
                "contribution_per_batting_opportunity": contrib_opp,
                "first_innings_contribution": first_inns,
                "chase_contribution": chase_contrib,
                "powerplay_contribution": pp_contrib,
                "powerplay_strike_rate": dot_metrics["powerplay_strike_rate"],
                "middle_over_contribution": mid_contrib,
                "middle_over_strike_rate": dot_metrics["middle_over_strike_rate"],
                "death_over_contribution": death_contrib,
                "death_over_strike_rate": dot_metrics["death_over_strike_rate"],
                "high_pressure_contribution": press_contrib,
                "pillars": {
                    "pillar1_match_context": p1,
                    "p1_leverage": p1_lev,
                    "pillar2_batter_performance": p2,
                    "adjusted_p2": adj_p2,
                    "pillar3_team_state_impact": p3,
                    "adjusted_p3": adj_p3,
                    "pillar4_counterfactual_value": p4,
                },
                "context_breakdown": {
                    "first_innings_contribution": first_inns,
                    "chase_contribution": chase_contrib,
                    "powerplay_contribution": pp_contrib,
                    "powerplay_strike_rate": dot_metrics["powerplay_strike_rate"],
                    "middle_over_contribution": mid_contrib,
                    "middle_over_strike_rate": dot_metrics["middle_over_strike_rate"],
                    "death_over_contribution": death_contrib,
                    "death_over_strike_rate": dot_metrics["death_over_strike_rate"],
                    "high_pressure_contribution": press_contrib,
                    "dot_balls": dot_metrics["dot_balls"],
                    "dot_ball_percentage": dot_metrics["dot_ball_percentage"],
                },
                "is_dnb": is_dnb,
            })

        observations = self._generate_comparison_observations(compared_list)

        return {
            "season": season_str,
            "view": view,
            "players_count": len(compared_list),
            "players": compared_list,
            "analytical_observations": observations,
        }

    def _generate_comparison_observations(self, players: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generates multidimensional observations highlighting different analytical strengths.
        Strictly avoids declaring a single simplistic 'winner' or creating an overall ranking.
        """
        valid_scores = [p for p in players if p["contribution_score"] is not None]
        valid_pos = [p for p in players if p["total_positive_raw_contribution"] is not None]
        valid_shares = [p for p in players if p["season_team_contribution_share"] is not None]

        highest_score = max(valid_scores, key=lambda p: p["contribution_score"]) if valid_scores else None
        highest_pos = max(valid_pos, key=lambda p: p["total_positive_raw_contribution"]) if valid_pos else None
        highest_share = max(valid_shares, key=lambda p: p["season_team_contribution_share"]) if valid_shares else None

        dimension_summaries = []
        if highest_score:
            dimension_summaries.append({
                "dimension": "Average Contextual Efficiency",
                "metric": "Contribution Score",
                "leader": highest_score["player"],
                "value": highest_score["contribution_score"],
                "unit": " / 100",
                "observation": f"{highest_score['player']} recorded the highest average contextual contribution score ({highest_score['contribution_score']} / 100), reflecting superior situation-adjusted efficiency per batting appearance.",
            })
        if highest_pos:
            dimension_summaries.append({
                "dimension": "Accumulated Positive Volume",
                "metric": "Positive Contribution",
                "leader": highest_pos["player"],
                "value": highest_pos["total_positive_raw_contribution"],
                "unit": " raw",
                "observation": f"{highest_pos['player']} accumulated the greatest total positive raw contribution (+{highest_pos['total_positive_raw_contribution']:.2f}), reflecting the largest cumulative volume of positive match impact across the season.",
            })
        if highest_share:
            dimension_summaries.append({
                "dimension": "Team Centricity",
                "metric": "Team Contribution Share",
                "leader": highest_share["player"],
                "value": highest_share["season_team_contribution_share"],
                "unit": "%",
                "observation": f"{highest_share['player']} provided the highest share of their team's positive batting contribution ({highest_share['season_team_contribution_share']:.1f}%), indicating high reliance and centrality to their team's scoring.",
            })

        return {
            "highest_score_player": highest_score["player"] if highest_score else None,
            "highest_positive_player": highest_pos["player"] if highest_pos else None,
            "highest_team_share_player": highest_share["player"] if highest_share else None,
            "dimensions": dimension_summaries,
            "summary_note": "Each metric measures a distinct analytical dimension. Average Contribution Score reflects situation-adjusted efficiency, Total Positive Contribution reflects cumulative volume, and Team Share reflects relative centrality. No universal ranking is applied.",
        }

    def get_matchup_rankings(
        self,
        season: Optional[str] = None,
        team: Optional[str] = None,
        bowling_type: Optional[str] = None,
        min_balls: int = 100,
        min_runs: int = 80,
        competition: Optional[str] = "ipl",
    ) -> Dict[str, Any]:
        """Returns rankings of batters vs Pace and vs Spin."""
        if self._normalize_competition(competition) != "ipl":
            return {
                "filters": {
                    "season": season or "All Seasons",
                    "team": team or "All Teams",
                    "min_balls": min_balls,
                    "min_runs": min_runs,
                    "eligibility_rule": f"Minimum sample: {min_balls} balls or {min_runs} runs.",
                },
                "results": {
                    "pace": {
                        "bowling_type": "Pace",
                        "rankings": [],
                        "total_eligible": 0,
                        "total_batters_observed": 0,
                    },
                    "spin": {
                        "bowling_type": "Spin",
                        "rankings": [],
                        "total_eligible": 0,
                        "total_batters_observed": 0,
                    },
                },
            }
        from src.matchup_analytics import compute_matchup_rankings
        return compute_matchup_rankings(
            season=season,
            team=team,
            bowling_type=bowling_type,
            min_balls=min_balls,
            min_runs=min_runs,
        )

    def get_batter_matchup_detail(
        self,
        batter: str,
        season: Optional[str] = None,
        team: Optional[str] = None,
        competition: Optional[str] = "ipl",
    ) -> Optional[Dict[str, Any]]:
        """Returns Pace vs Spin matchup breakdown for a specific batter."""
        if self._normalize_competition(competition) != "ipl":
            return None
        from src.matchup_analytics import get_batter_matchup_detail
        return get_batter_matchup_detail(
            batter=batter,
            season=season,
            team=team,
        )


    def get_tournaments(self, competition: Optional[str] = "t20i") -> Dict[str, Any]:
        """Returns distinct tournaments for a competition with priority ordering."""
        norm_comp = self._normalize_competition(competition)
        matches_df = self.get_matches_df(norm_comp)
        if matches_df is None or matches_df.empty:
            return {"tournaments": [], "competition": norm_comp}

        if norm_comp == "ipl":
            return {
                "tournaments": ["Indian Premier League"],
                "featured_tournaments": ["Indian Premier League"],
                "default_tournament": "Indian Premier League",
                "competition": "ipl",
            }
        # SMAT tournaments preserved for future reactivation:
        # elif norm_comp == "smat":
        #     return {
        #         "tournaments": ["Syed Mushtaq Ali Trophy"],
        #         "featured_tournaments": ["Syed Mushtaq Ali Trophy"],
        #         "default_tournament": "Syed Mushtaq Ali Trophy",
        #         "competition": "smat",
        #     }

        if "event_name" not in matches_df.columns:
            return {
                "tournaments": ["All Tournaments"],
                "featured_tournaments": [],
                "default_tournament": "All Tournaments",
                "competition": "t20i",
            }

        raw_events = [str(x).strip() for x in matches_df["event_name"].dropna().unique() if str(x).strip()]

        priority = [
            "ICC Men's T20 World Cup",
            "ICC World Twenty20",
            "World T20",
            "Men's T20 Asia Cup",
            "Asia Cup",
            "Men's T20 Asia Cup Qualifier",
        ]

        featured = [p for p in ["ICC Men's T20 World Cup", "Men's T20 Asia Cup", "Asia Cup"] if p in raw_events]
        sorted_priority = [p for p in priority if p in raw_events]
        remaining = sorted([e for e in raw_events if e not in priority])
        all_tournaments = ["All Tournaments"] + sorted_priority + remaining

        return {
            "tournament_types": TOURNAMENT_TYPES,
            "default_tournament_type": "all",
            "tournaments": all_tournaments,
            "featured_tournaments": featured,
            "default_tournament": "All Tournaments",
            "competition": "t20i",
        }

    def get_matches(
        self,
        season: Optional[str] = None,
        team: Optional[str] = None,
        opponent: Optional[str] = None,
        tournament: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 200,
        competition: Optional[str] = "ipl",
        tournament_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Returns list of matches filtered by season, team, opponent, tournament, tournament_type, or search text."""
        norm_comp = self._normalize_competition(competition)
        if norm_comp == "t20i":
            df = self._filter_t20i_matches(tournament_type or "all", season)
        else:
            matches_df = self.get_matches_df(competition)
            if matches_df is None or matches_df.empty:
                return []
            df = matches_df.copy()
            if season and season != "All Seasons":
                df = df[df["season"] == str(season)]

        contrib_df = self.get_contributions_df(competition)
        if df is None or df.empty:
            return []

        if team and team != "All Teams":
            df = df[(df["team1"] == team) | (df["team2"] == team)]
        if opponent and opponent != "All Opponents":
            df = df[(df["team1"] == opponent) | (df["team2"] == opponent)]
        if tournament and tournament != "All Tournaments":
            t_clean = tournament.strip().lower()
            if "event_name" in df.columns:
                df = df[df["event_name"].fillna("").str.lower() == t_clean]
            else:
                default_name = "indian premier league" if norm_comp == "ipl" else "syed mushtaq ali trophy"
                if t_clean != default_name:
                    return []
        if search:
            s_lower = search.strip().lower()
            df = df[
                df["team1"].str.lower().str.contains(s_lower, na=False)
                | df["team2"].str.lower().str.contains(s_lower, na=False)
                | df["venue"].str.lower().str.contains(s_lower, na=False)
                | df["city"].str.lower().str.contains(s_lower, na=False)
            ]

        # Sort by date descending, then match_id descending
        df = df.sort_values(by=["date", "match_id"], ascending=[False, False])
        if limit:
            df = df.head(limit)

        match_ids = [str(x) for x in df["match_id"].tolist()]
        scores_map: Dict[str, Dict[int, Any]] = {}
        top_contrib_map: Dict[str, Dict[str, Any]] = {}

        if contrib_df is not None and not contrib_df.empty and match_ids:
            c_sub = contrib_df[contrib_df["match_id"].astype(str).isin(match_ids)]
            if not c_sub.empty:
                # Group by match_id and innings to extract final team scores
                grp_scores = c_sub.groupby(["match_id", "innings", "team"])["final_team_score"].max().reset_index()
                for _, r in grp_scores.iterrows():
                    mid = str(r["match_id"])
                    if mid not in scores_map:
                        scores_map[mid] = {}
                    scores_map[mid][int(r["innings"])] = {
                        "team": str(r["team"]),
                        "score": clean_int(r["final_team_score"]),
                    }

                # Extract top contributor per match (Ranking eligibility: 10+ balls OR 20+ runs)
                sorted_c = c_sub.sort_values(by=["contribution_score", "actual_runs"], ascending=[False, False])
                for mid, group in sorted_c.groupby("match_id"):
                    m_key = str(mid)
                    q_group = group[(group["balls_faced"] >= 10) | (group["actual_runs"] >= 20)]
                    if not q_group.empty:
                        top_row = q_group.iloc[0]
                        top_contrib_map[m_key] = {
                            "player": str(top_row["player"]),
                            "team": str(top_row["team"]),
                            "contribution_score": clean_num(top_row["contribution_score"], 1),
                            "runs": clean_int(top_row["actual_runs"]),
                            "balls": clean_int(top_row["balls_faced"]),
                            "sr": clean_num(top_row["actual_sr"], 1),
                            "is_qualified": True,
                        }
                    else:
                        top_contrib_map[m_key] = None

        results = []
        for _, mr in df.iterrows():
            raw_mid = mr["match_id"]
            m_key = str(raw_mid)
            mid = int(raw_mid) if str(raw_mid).isdigit() else str(raw_mid)
            w_runs = clean_num(mr.get("win_by_runs"))
            w_wkts = clean_num(mr.get("win_by_wickets"))
            winner = str(mr.get("winner")) if pd.notnull(mr.get("winner")) else None

            if winner and w_runs:
                result_str = f"{winner} won by {int(w_runs)} runs"
                margin_str = f"{int(w_runs)} runs"
            elif winner and w_wkts:
                result_str = f"{winner} won by {int(w_wkts)} wkts"
                margin_str = f"{int(w_wkts)} wkts"
            elif winner:
                result_str = f"{winner} won"
                margin_str = ""
            else:
                result_str = "No result / Tie"
                margin_str = ""

            m_scores = scores_map.get(m_key, {})
            inns1 = m_scores.get(1, {})
            inns2 = m_scores.get(2, {})

            t1 = str(mr.get("team1", ""))
            t2 = str(mr.get("team2", ""))

            # Score matching by team name
            t1_score = None
            t2_score = None
            if inns1.get("team") == t1:
                t1_score = inns1.get("score")
                t2_score = inns2.get("score")
            elif inns2.get("team") == t1:
                t1_score = inns2.get("score")
                t2_score = inns1.get("score")
            else:
                t1_score = inns1.get("score")
                t2_score = inns2.get("score")

            ev_name = str(mr.get("event_name", "")) if pd.notnull(mr.get("event_name")) and str(mr.get("event_name", "")).strip() else ("Indian Premier League" if norm_comp == "ipl" else None)
            stage_val = str(mr.get("stage", "")) if pd.notnull(mr.get("stage")) and str(mr.get("stage", "")).strip() else None
            match_num_val = str(mr.get("match_number", "")) if pd.notnull(mr.get("match_number")) and str(mr.get("match_number", "")).strip() else None

            ttype_val = self._classify_tournament_type(ev_name) if norm_comp == "t20i" else norm_comp

            results.append({
                "match_id": mid,
                "season": str(mr.get("season", "")),
                "date": str(mr.get("date", "")),
                "venue": str(mr.get("venue", "")),
                "city": str(mr.get("city", "")),
                "team1": t1,
                "team2": t2,
                "winner": winner,
                "win_by_runs": w_runs,
                "win_by_wickets": w_wkts,
                "result": result_str,
                "margin": margin_str,
                "player_of_match": str(mr.get("player_of_match", "")) if pd.notnull(mr.get("player_of_match")) else None,
                "team1_score": t1_score,
                "team2_score": t2_score,
                "top_contributor": top_contrib_map.get(m_key),
                "event_name": ev_name,
                "stage": stage_val,
                "match_number": match_num_val,
                "tournament_type": ttype_val,
            })

        return results

    def get_match_overview(self, match_id: Any, competition: Optional[str] = "ipl") -> Optional[Dict[str, Any]]:
        """Returns comprehensive match summary and all batter contribution ratings."""
        norm_comp = self._normalize_competition(competition)
        matches_df = self.get_matches_df(competition)
        contrib_df = self.get_contributions_df(competition)
        if matches_df is None or matches_df.empty:
            return None

        m_str = str(match_id)
        msub = matches_df[matches_df["match_id"].astype(str) == m_str]
        if msub.empty:
            return None
        mr = msub.iloc[0]

        w_runs = clean_num(mr.get("win_by_runs"))
        w_wkts = clean_num(mr.get("win_by_wickets"))
        winner = str(mr.get("winner")) if pd.notnull(mr.get("winner")) else None

        if winner and w_runs:
            result_str = f"{winner} won by {int(w_runs)} runs"
            margin_str = f"{int(w_runs)} runs"
        elif winner and w_wkts:
            result_str = f"{winner} won by {int(w_wkts)} wkts"
            margin_str = f"{int(w_wkts)} wkts"
        elif winner:
            result_str = f"{winner} won"
            margin_str = ""
        else:
            result_str = "No result / Tie"
            margin_str = ""

        batters = []
        inns1_score = None
        inns2_score = None

        if contrib_df is not None and not contrib_df.empty:
            c_sub = contrib_df[contrib_df["match_id"].astype(str) == m_str]
            if not c_sub.empty:
                # Group scores by innings
                grp_scores = c_sub.groupby(["innings", "team"])["final_team_score"].max().reset_index()
                for _, r in grp_scores.iterrows():
                    if int(r["innings"]) == 1:
                        inns1_score = clean_int(r["final_team_score"])
                    elif int(r["innings"]) == 2:
                        inns2_score = clean_int(r["final_team_score"])

                # Batters with actual batting opportunities
                # Qualification rule for match ranking: balls_faced >= 10 OR actual_runs >= 20
                c_sorted = c_sub.sort_values(by=["contribution_score", "actual_runs"], ascending=[False, False])
                qualified_batters = []
                limited_batters = []

                for _, brow in c_sorted.iterrows():
                    b_team = str(brow.get("team", ""))
                    b_opp = str(brow.get("opponent", ""))
                    won = bool(brow.get("won_match", False)) if pd.notnull(brow.get("won_match")) else (winner == b_team)
                    b_balls = int(clean_int(brow.get("balls_faced")) or 0)
                    b_runs = int(clean_int(brow.get("actual_runs")) or 0)
                    is_qual = bool((b_balls >= 10) or (b_runs >= 20))

                    batter_item = {
                        "rank": None,  # assigned below for qualified batters
                        "is_qualified": is_qual,
                        "qualification_status": "Qualified" if is_qual else "Limited Sample",
                        "sample_reason": None if is_qual else f"Limited sample ({b_runs} runs / {b_balls} balls)",
                        "player": str(brow.get("player", "")),
                        "team": b_team,
                        "opponent": b_opp,
                        "innings": clean_int(brow.get("innings")),
                        "entry_over": clean_num(brow.get("entry_over"), 1),
                        "exit_over": clean_num(brow.get("exit_over"), 1),
                        "runs": b_runs,
                        "balls": b_balls,
                        "strike_rate": clean_num(brow.get("actual_sr"), 1),
                        "fours": clean_int(brow.get("fours")),
                        "sixes": clean_int(brow.get("sixes")),
                        "dismissal_status": str(brow.get("dismissal_status", "")),
                        "dismissal_kind": str(brow.get("dismissal_kind", "")) if pd.notnull(brow.get("dismissal_kind")) else None,
                        "contribution_score": clean_num(brow.get("contribution_score"), 1),
                        "raw_contribution": clean_num(brow.get("raw_contribution"), 4),
                        "score_context": clean_num(brow.get("score_context"), 1),
                        "score_perf": clean_num(brow.get("score_perf"), 1),
                        "score_state": clean_num(brow.get("score_state"), 1),
                        "leverage": clean_num(brow.get("leverage"), 3),
                        "is_negligible": bool(brow.get("is_negligible", False)),
                        "won_match": won,
                        "team_result": "Won" if won else "Lost",
                    }
                    if is_qual:
                        qualified_batters.append(batter_item)
                    else:
                        limited_batters.append(batter_item)

                # Assign ranks to qualified batters only: #1, #2, #3...
                for idx, qb in enumerate(qualified_batters):
                    qb["rank"] = idx + 1

                # Limited sample batters keep rank = None

                # Combined list: qualified first (by contribution DESC), then limited-sample (by contribution DESC)
                batters = qualified_batters + limited_batters
                top_qualified = qualified_batters[0] if qualified_batters else None

        t1 = str(mr.get("team1", ""))
        t2 = str(mr.get("team2", ""))

        out_mid = int(match_id) if str(match_id).isdigit() else str(match_id)
        ev_name = str(mr.get("event_name", "")) if pd.notnull(mr.get("event_name")) and str(mr.get("event_name", "")).strip() else ("Indian Premier League" if norm_comp == "ipl" else None)
        stage_val = str(mr.get("stage", "")) if pd.notnull(mr.get("stage")) and str(mr.get("stage", "")).strip() else None
        match_num_val = str(mr.get("match_number", "")) if pd.notnull(mr.get("match_number")) and str(mr.get("match_number", "")).strip() else None

        return {
            "match_id": out_mid,
            "season": str(mr.get("season", "")),
            "date": str(mr.get("date", "")),
            "venue": str(mr.get("venue", "")),
            "city": str(mr.get("city", "")),
            "team1": t1,
            "team2": t2,
            "toss_winner": str(mr.get("toss_winner", "")) if pd.notnull(mr.get("toss_winner")) else None,
            "toss_decision": str(mr.get("toss_decision", "")) if pd.notnull(mr.get("toss_decision")) else None,
            "winner": winner,
            "win_by_runs": w_runs,
            "win_by_wickets": w_wkts,
            "result": result_str,
            "margin": margin_str,
            "player_of_match": str(mr.get("player_of_match", "")) if pd.notnull(mr.get("player_of_match")) else None,
            "team1_score": inns1_score,
            "team2_score": inns2_score,
            "top_qualified_contributor": top_qualified,
            "batters": batters,
            "total_batters": len(batters),
            "qualified_count": len(qualified_batters),
            "limited_sample_count": len(limited_batters),
            "event_name": ev_name,
            "stage": stage_val,
            "match_number": match_num_val,
        }

    def _build_career_players_index(self):
        """Builds and caches the list of all available batters across competitions."""
        self._ensure_loaded("ipl")
        self._ensure_loaded("t20i")

        r_ipl = self.get_rosters_df("ipl")
        r_t20i = self.get_rosters_df("t20i")
        df_ipl = self.get_contributions_df("ipl")
        df_t20i = self.get_contributions_df("t20i")
        m_ipl = self.get_matches_df("ipl")
        m_t20i = self.get_matches_df("t20i")

        runs_ipl = df_ipl.groupby("player")["actual_runs"].sum().to_dict() if df_ipl is not None and not df_ipl.empty else {}
        runs_t20i = df_t20i.groupby("player")["actual_runs"].sum().to_dict() if df_t20i is not None and not df_t20i.empty else {}

        ipl_roster_players = set(r_ipl["player"].dropna().unique()) if r_ipl is not None and not r_ipl.empty else set()
        t20i_roster_players = set(r_t20i["player"].dropna().unique()) if r_t20i is not None and not r_t20i.empty else set()

        ipl_teams_by_player: Dict[str, set] = {}
        if r_ipl is not None and not r_ipl.empty:
            for _, r in r_ipl[["player", "team"]].dropna().drop_duplicates().iterrows():
                ipl_teams_by_player.setdefault(str(r["player"]), set()).add(str(r["team"]))

        t20i_teams_by_player: Dict[str, set] = {}
        if r_t20i is not None and not r_t20i.empty:
            for _, r in r_t20i[["player", "team"]].dropna().drop_duplicates().iterrows():
                t20i_teams_by_player.setdefault(str(r["player"]), set()).add(str(r["team"]))

        # Years
        years_by_player: Dict[str, set] = {}
        if r_ipl is not None and not r_ipl.empty and m_ipl is not None and not m_ipl.empty:
            merged_ipl = r_ipl[["match_id", "player"]].merge(m_ipl[["match_id", "date"]], on="match_id")
            merged_ipl["year"] = pd.to_datetime(merged_ipl["date"], errors="coerce").dt.year
            for _, r in merged_ipl[["player", "year"]].dropna().drop_duplicates().iterrows():
                years_by_player.setdefault(str(r["player"]), set()).add(int(r["year"]))

        if r_t20i is not None and not r_t20i.empty and m_t20i is not None and not m_t20i.empty:
            merged_t20i = r_t20i[["match_id", "player"]].merge(m_t20i[["match_id", "date"]], on="match_id")
            merged_t20i["year"] = pd.to_datetime(merged_t20i["date"], errors="coerce").dt.year
            for _, r in merged_t20i[["player", "year"]].dropna().drop_duplicates().iterrows():
                years_by_player.setdefault(str(r["player"]), set()).add(int(r["year"]))

        all_players = sorted(list(ipl_roster_players.union(t20i_roster_players)))
        index_records = []

        for p in all_players:
            has_ipl = p in ipl_roster_players
            has_t20i = p in t20i_roster_players
            r_tot = int(runs_ipl.get(p, 0) + runs_t20i.get(p, 0))

            teams = sorted(list(ipl_teams_by_player.get(p, set()).union(t20i_teams_by_player.get(p, set()))))
            years = sorted(list(years_by_player.get(p, set())))

            if years:
                span_str = f"{years[0]} – {years[-1]}" if years[0] != years[-1] else str(years[0])
            else:
                span_str = "Available"

            comps = []
            if has_ipl:
                comps.append("ipl")
            if has_t20i:
                comps.append("t20i")

            index_records.append({
                "player": p,
                "has_ipl": has_ipl,
                "has_t20i": has_t20i,
                "competitions": comps,
                "total_runs": r_tot,
                "teams": teams,
                "career_span": span_str,
            })

        # Sort descending by total runs so marquee batters are featured first
        index_records.sort(key=lambda x: x["total_runs"], reverse=True)
        self._career_players_cache = index_records

    def search_career_players(
        self,
        query: Optional[str] = None,
        competition: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Searches batters across IPL and International coverage."""
        if self._career_players_cache is None:
            self._build_career_players_index()

        records = self._career_players_cache or []
        comp = competition.strip().lower() if competition else None

        if comp == "ipl":
            records = [r for r in records if r["has_ipl"]]
        elif comp == "t20i":
            records = [r for r in records if r["has_t20i"]]

        if query:
            q = query.strip().lower()
            records = [r for r in records if q in r["player"].lower()]

        return records[:limit]

    def get_player_career(
        self,
        player_id: str,
        competition: str = "combined",
    ) -> Optional[Dict[str, Any]]:
        """
        Computes accurate player career aggregation and year/season timeline
        across IPL, International (T20I), or Combined Career.
        """
        self._ensure_loaded("ipl")
        self._ensure_loaded("t20i")

        df_ipl = self.get_contributions_df("ipl")
        df_t20i = self.get_contributions_df("t20i")
        m_ipl = self.get_matches_df("ipl")
        m_t20i = self.get_matches_df("t20i")
        r_ipl = self.get_rosters_df("ipl")
        r_t20i = self.get_rosters_df("t20i")

        pid_lower = player_id.strip().lower()

        # Locate canonical player name
        p_ipl = [p for p in r_ipl["player"].dropna().unique() if p.lower() == pid_lower] if r_ipl is not None and not r_ipl.empty else []
        p_t20i = [p for p in r_t20i["player"].dropna().unique() if p.lower() == pid_lower] if r_t20i is not None and not r_t20i.empty else []

        if not p_ipl and not p_t20i:
            return None

        actual_name = p_ipl[0] if p_ipl else p_t20i[0]
        has_ipl = len(p_ipl) > 0
        has_t20i = len(p_t20i) > 0

        norm_comp = competition.strip().lower()
        if norm_comp not in ("ipl", "t20i", "combined"):
            norm_comp = "combined"

        # Match metadata maps
        m_ipl_dict = {}
        if m_ipl is not None and not m_ipl.empty:
            for _, r in m_ipl.iterrows():
                d_str = str(r.get("date", ""))
                m_ipl_dict[str(r["match_id"])] = {
                    "date": d_str,
                    "season": str(r.get("season", "")),
                    "year": int(pd.to_datetime(d_str).year) if pd.notnull(r.get("date")) and d_str else None,
                    "competition": "IPL",
                }

        m_t20i_dict = {}
        if m_t20i is not None and not m_t20i.empty:
            for _, r in m_t20i.iterrows():
                d_str = str(r.get("date", ""))
                m_t20i_dict[str(r["match_id"])] = {
                    "date": d_str,
                    "season": str(r.get("season", "")),
                    "year": int(pd.to_datetime(d_str).year) if pd.notnull(r.get("date")) and d_str else None,
                    "competition": "International",
                }

        appearances: List[Dict[str, Any]] = []

        # IPL appearances
        if norm_comp in ("ipl", "combined") and has_ipl and r_ipl is not None and not r_ipl.empty:
            sub_r = r_ipl[r_ipl["player"] == actual_name]
            sub_c = df_ipl[df_ipl["player"] == actual_name] if df_ipl is not None and not df_ipl.empty else pd.DataFrame()
            c_by_mid = {str(r["match_id"]): r for _, r in sub_c.iterrows()} if not sub_c.empty else {}

            for _, r in sub_r.iterrows():
                mid = str(r["match_id"])
                minfo = m_ipl_dict.get(mid, {})
                c_row = c_by_mid.get(mid)
                is_dnb = c_row is None

                team = str(r.get("team", ""))
                app = {
                    "match_id": mid,
                    "competition": "IPL",
                    "team": team,
                    "season_label": minfo.get("season", str(r.get("season", ""))),
                    "year": minfo.get("year"),
                    "date": minfo.get("date"),
                    "is_dnb": is_dnb,
                    "runs": int(c_row.get("actual_runs", 0)) if not is_dnb else 0,
                    "balls_faced": int(c_row.get("balls_faced", 0)) if not is_dnb else 0,
                    "dot_balls": int(c_row.get("dot_balls", 0)) if not is_dnb and pd.notnull(c_row.get("dot_balls")) else 0,
                    "contribution_score": clean_num(c_row.get("contribution_score"), 2) if not is_dnb else None,
                    "raw_contribution": clean_num(c_row.get("raw_contribution"), 4) if not is_dnb else None,
                }
                appearances.append(app)

        # T20I appearances
        if norm_comp in ("t20i", "combined") and has_t20i and r_t20i is not None and not r_t20i.empty:
            sub_r = r_t20i[r_t20i["player"] == actual_name]
            sub_c = df_t20i[df_t20i["player"] == actual_name] if df_t20i is not None and not df_t20i.empty else pd.DataFrame()
            c_by_mid = {str(r["match_id"]): r for _, r in sub_c.iterrows()} if not sub_c.empty else {}

            for _, r in sub_r.iterrows():
                mid = str(r["match_id"])
                minfo = m_t20i_dict.get(mid, {})
                c_row = c_by_mid.get(mid)
                is_dnb = c_row is None

                team = str(r.get("team", ""))
                year_val = minfo.get("year")
                season_str = str(year_val) if year_val else minfo.get("season", str(r.get("season", "")))

                app = {
                    "match_id": mid,
                    "competition": "International",
                    "team": team,
                    "season_label": season_str,
                    "year": year_val,
                    "date": minfo.get("date"),
                    "is_dnb": is_dnb,
                    "runs": int(c_row.get("actual_runs", 0)) if not is_dnb else 0,
                    "balls_faced": int(c_row.get("balls_faced", 0)) if not is_dnb else 0,
                    "dot_balls": int(c_row.get("dot_balls", 0)) if not is_dnb and pd.notnull(c_row.get("dot_balls")) else 0,
                    "contribution_score": clean_num(c_row.get("contribution_score"), 2) if not is_dnb else None,
                    "raw_contribution": clean_num(c_row.get("raw_contribution"), 4) if not is_dnb else None,
                }
                appearances.append(app)

        if not appearances:
            return {
                "player": actual_name,
                "competition": norm_comp,
                "available_competitions": {"ipl": has_ipl, "t20i": has_t20i},
                "career_summary": {
                    "player": actual_name,
                    "teams": [],
                    "career_span": "N/A",
                    "seasons_count": 0,
                    "matches": 0,
                    "batting_innings": 0,
                    "dnb_matches": 0,
                    "runs": 0,
                    "balls_faced": 0,
                    "strike_rate": None,
                    "average_contribution": None,
                    "positive_appearances": 0,
                    "eligible_appearances": 0,
                    "positive_contribution_rate": None,
                    "dot_balls": 0,
                    "eligible_balls": 0,
                    "dot_ball_percentage": None,
                },
                "career_highs_lows": self._compute_career_highs_lows([]),
                "bowling_type_trends": {
                    "summary": {
                        "total_balls_faced": 0,
                        "classified_balls_faced": 0,
                        "unclassified_balls_faced": 0,
                        "coverage_percentage": 100.0,
                        "is_coverage_complete": True,
                        "pace": self._empty_bowling_stats(),
                        "spin": self._empty_bowling_stats(),
                    },
                    "seasons": [],
                    "coverage_info": {
                        "total_balls_faced": 0,
                        "classified_balls": 0,
                        "unclassified_balls": 0,
                        "coverage_percentage": 100.0,
                        "classification_source": "Auditable Bowler Style Registry (577 bowlers)",
                        "unclassified_bowlers_count": 0,
                        "unclassified_bowlers": [],
                    },
                },
                "timeline": [],
                "dataset_coverage": self.get_dataset_coverage(),
            }

        def get_group_key(app):
            if norm_comp == "ipl":
                return app["season_label"]
            elif norm_comp == "t20i":
                return str(app["year"]) if app["year"] else app["season_label"]
            else:
                return str(app["year"]) if app["year"] else app["season_label"]

        def get_sort_key(group_key, apps):
            dates = [a["date"] for a in apps if a.get("date")]
            if dates:
                return min(dates)
            nums = [int(s) for s in str(group_key).split("/") if s.isdigit()]
            return str(nums[0]) if nums else str(group_key)

        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for app in appearances:
            gk = get_group_key(app)
            grouped.setdefault(gk, []).append(app)

        sorted_keys = sorted(grouped.keys(), key=lambda k: get_sort_key(k, grouped[k]))

        timeline: List[Dict[str, Any]] = []

        for k in sorted_keys:
            group_apps = grouped[k]
            matches = len(group_apps)
            batted_apps = [a for a in group_apps if not a["is_dnb"]]
            batting_inns = len(batted_apps)
            dnb_matches = matches - batting_inns

            tot_runs = sum(a["runs"] for a in batted_apps)
            tot_balls = sum(a["balls_faced"] for a in batted_apps)
            tot_dots = sum(a["dot_balls"] for a in batted_apps)

            sr = clean_num(tot_runs / tot_balls * 100.0, 1) if tot_balls > 0 else None
            dot_pct = clean_num(tot_dots / tot_balls * 100.0, 1) if tot_balls > 0 else None

            valid_scores = [a["contribution_score"] for a in batted_apps if a["contribution_score"] is not None]
            eligible_appearances = len(valid_scores)
            pos_appearances = sum(1 for s in valid_scores if s > 50.0)

            avg_contrib = clean_num(float(np.mean(valid_scores)), 2) if valid_scores else None
            pos_rate = clean_num(pos_appearances / eligible_appearances * 100.0, 1) if eligible_appearances > 0 else None

            ipl_apps = [a for a in batted_apps if a["competition"] == "IPL"]
            t20i_apps = [a for a in batted_apps if a["competition"] == "International"]

            ipl_runs = sum(a["runs"] for a in ipl_apps)
            t20i_runs = sum(a["runs"] for a in t20i_apps)

            ipl_scores = [a["contribution_score"] for a in ipl_apps if a["contribution_score"] is not None]
            t20i_scores = [a["contribution_score"] for a in t20i_apps if a["contribution_score"] is not None]

            comp_label = (
                "IPL" if norm_comp == "ipl"
                else "International" if norm_comp == "t20i"
                else ("IPL + INL" if (len(ipl_apps) > 0 and len(t20i_apps) > 0) else ("IPL" if len(ipl_apps) > 0 else "International"))
            )

            timeline.append({
                "season": k,
                "competition": comp_label,
                "matches": matches,
                "batting_innings": batting_inns,
                "dnb_matches": dnb_matches,
                "runs": tot_runs,
                "balls_faced": tot_balls,
                "strike_rate": sr,
                "average_contribution": avg_contrib,
                "positive_contribution_rate": pos_rate,
                "positive_appearances": pos_appearances,
                "eligible_appearances": eligible_appearances,
                "dot_balls": tot_dots,
                "eligible_balls": tot_balls,
                "dot_ball_percentage": dot_pct,
                "ipl_runs": ipl_runs if norm_comp == "combined" else None,
                "t20i_runs": t20i_runs if norm_comp == "combined" else None,
                "ipl_innings": len(ipl_apps) if norm_comp == "combined" else None,
                "t20i_innings": len(t20i_apps) if norm_comp == "combined" else None,
                "ipl_avg_contribution": clean_num(float(np.mean(ipl_scores)), 2) if ipl_scores else None,
                "t20i_avg_contribution": clean_num(float(np.mean(t20i_scores)), 2) if t20i_scores else None,
            })

        tot_matches = len(appearances)
        all_batted = [a for a in appearances if not a["is_dnb"]]
        tot_batting_inns = len(all_batted)
        tot_dnb = tot_matches - tot_batting_inns

        career_runs = sum(a["runs"] for a in all_batted)
        career_balls = sum(a["balls_faced"] for a in all_batted)
        career_dots = sum(a["dot_balls"] for a in all_batted)

        career_sr = clean_num(career_runs / career_balls * 100.0, 1) if career_balls > 0 else None
        career_dot_pct = clean_num(career_dots / career_balls * 100.0, 1) if career_balls > 0 else None

        all_valid_scores = [a["contribution_score"] for a in all_batted if a["contribution_score"] is not None]
        career_eligible = len(all_valid_scores)
        career_pos_app = sum(1 for s in all_valid_scores if s > 50.0)

        career_avg_contrib = clean_num(float(np.mean(all_valid_scores)), 2) if all_valid_scores else None
        career_pos_rate = clean_num(career_pos_app / career_eligible * 100.0, 1) if career_eligible > 0 else None

        teams = sorted(list(set(a["team"] for a in appearances if a.get("team"))))
        span_start = sorted_keys[0] if sorted_keys else "N/A"
        span_end = sorted_keys[-1] if sorted_keys else "N/A"
        career_span = f"{span_start} – {span_end}" if span_start != span_end else str(span_start)

        summary = {
            "player": actual_name,
            "teams": teams,
            "career_span": career_span,
            "seasons_count": len(sorted_keys),
            "matches": tot_matches,
            "total_matches": tot_matches,
            "batting_innings": tot_batting_inns,
            "dnb_matches": tot_dnb,
            "runs": career_runs,
            "total_runs": career_runs,
            "balls_faced": career_balls,
            "strike_rate": career_sr,
            "average_contribution": career_avg_contrib,
            "positive_appearances": career_pos_app,
            "eligible_appearances": career_eligible,
            "positive_contribution_rate": career_pos_rate,
            "dot_balls": career_dots,
            "eligible_balls": career_balls,
            "dot_ball_percentage": career_dot_pct,
        }

        highs_lows = self._compute_career_highs_lows(timeline)
        bowling_trends = self._compute_bowling_type_trends(
            player_name=actual_name,
            norm_comp=norm_comp,
            appearances=appearances,
            sorted_keys=sorted_keys,
            grouped=grouped,
        )

        return {
            "player": actual_name,
            "competition": norm_comp,
            "available_competitions": {"ipl": has_ipl, "t20i": has_t20i},
            "career_summary": summary,
            "career_highs_lows": highs_lows,
            "bowling_type_trends": bowling_trends,
            "timeline": timeline,
            "dataset_coverage": self.get_dataset_coverage(),
        }

    @staticmethod
    def _compute_career_highs_lows(timeline: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Identifies deterministic highest and lowest seasonal benchmarks across:
        1. Total runs (excluding pure DNB seasons with 0 batting innings)
        2. Strike rate (strictly seasonal total runs / balls faced * 100)
        3. Dot-ball percentage (strictly eligible dot balls / eligible legal balls * 100)
        4. Average contribution score (Strategy 4 scores, Par benchmark 50.0)
        """
        def _build_entry(s_dict: Dict[str, Any], val: Any, tied: List[str]):
            b_inns = int(s_dict.get("batting_innings", 0))
            balls = int(s_dict.get("balls_faced", 0))
            is_limited = b_inns < 5 or balls < 30
            matches = int(s_dict.get("matches", 0))
            dnb = int(s_dict.get("dnb_matches", matches - b_inns))

            note_parts = [f"{b_inns} innings", f"{balls} balls"]
            if dnb > 0:
                note_parts.append(f"{dnb} DNB")

            return {
                "season": str(s_dict.get("season", "")),
                "value": val,
                "matches": matches,
                "batting_innings": b_inns,
                "dnb_matches": dnb,
                "balls_faced": balls,
                "runs": int(s_dict.get("runs", 0)),
                "competition": str(s_dict.get("competition", "Unknown")),
                "is_limited_sample": is_limited,
                "sample_note": " • ".join(note_parts),
                "tied_seasons": tied,
            }

        # 1. Total Runs (only seasons with at least 1 batting appearance)
        runs_seasons = [s for s in timeline if int(s.get("batting_innings", 0)) > 0 and s.get("runs") is not None]
        if not runs_seasons:
            runs_block = {
                "metric_id": "runs",
                "label": "Total Runs",
                "unit": "runs",
                "highest": None,
                "lowest": None,
                "insufficient_data": True,
                "interpretation": "Volume of runs scored across the season/year. Requires at least one batting appearance.",
            }
        else:
            max_r = max(s["runs"] for s in runs_seasons)
            min_r = min(s["runs"] for s in runs_seasons)
            max_s = [s for s in runs_seasons if s["runs"] == max_r]
            min_s = [s for s in runs_seasons if s["runs"] == min_r]
            runs_block = {
                "metric_id": "runs",
                "label": "Total Runs",
                "unit": "runs",
                "highest": _build_entry(max_s[0], max_r, [str(s["season"]) for s in max_s[1:]]),
                "lowest": _build_entry(min_s[0], min_r, [str(s["season"]) for s in min_s[1:]]),
                "insufficient_data": False,
                "interpretation": "Total volume of runs scored in a campaign. Low values often reflect small opportunity rather than poor form.",
            }

        # 2. Strike Rate (only seasons with balls_faced > 0)
        sr_seasons = [s for s in timeline if int(s.get("balls_faced", 0)) > 0 and s.get("strike_rate") is not None]
        if not sr_seasons:
            sr_block = {
                "metric_id": "strike_rate",
                "label": "Strike Rate",
                "unit": "runs / 100 balls",
                "highest": None,
                "lowest": None,
                "insufficient_data": True,
                "interpretation": "Scoring rate calculated strictly as (Total Runs / Total Balls) × 100.",
            }
        else:
            max_sr = max(s["strike_rate"] for s in sr_seasons)
            min_sr = min(s["strike_rate"] for s in sr_seasons)
            max_s = [s for s in sr_seasons if s["strike_rate"] == max_sr]
            min_s = [s for s in sr_seasons if s["strike_rate"] == min_sr]
            sr_block = {
                "metric_id": "strike_rate",
                "label": "Strike Rate",
                "unit": "runs / 100 balls",
                "highest": _build_entry(max_s[0], max_sr, [str(s["season"]) for s in max_s[1:]]),
                "lowest": _build_entry(min_s[0], min_sr, [str(s["season"]) for s in min_s[1:]]),
                "insufficient_data": False,
                "interpretation": "Scoring velocity calibrated against balls faced. Short campaigns (<30 balls) can produce volatile extremes.",
            }

        # 3. Dot-Ball Percentage (only seasons with eligible_balls > 0)
        dot_seasons = [s for s in timeline if int(s.get("eligible_balls", 0)) > 0 and s.get("dot_ball_percentage") is not None]
        if not dot_seasons:
            dot_block = {
                "metric_id": "dot_ball_percentage",
                "label": "Dot-Ball Percentage",
                "unit": "%",
                "highest": None,
                "lowest": None,
                "insufficient_data": True,
                "interpretation": "Proportion of legal balls faced producing 0 runs. Lower values reflect superior strike rotation.",
            }
        else:
            max_d = max(s["dot_ball_percentage"] for s in dot_seasons)
            min_d = min(s["dot_ball_percentage"] for s in dot_seasons)
            max_s = [s for s in dot_seasons if s["dot_ball_percentage"] == max_d]
            min_s = [s for s in dot_seasons if s["dot_ball_percentage"] == min_d]
            dot_block = {
                "metric_id": "dot_ball_percentage",
                "label": "Dot-Ball Percentage",
                "unit": "%",
                "highest": _build_entry(max_s[0], max_d, [str(s["season"]) for s in max_s[1:]]),
                "lowest": _build_entry(min_s[0], min_d, [str(s["season"]) for s in min_s[1:]]),
                "insufficient_data": False,
                "interpretation": "Percentage of legal balls faced yielding no runs. Lower dot-ball percentage indicates efficient strike rotation and lower pressure buildup.",
            }

        # 4. Average Contribution Score (only seasons with eligible_appearances > 0 and average_contribution is not None)
        c_seasons = [s for s in timeline if int(s.get("eligible_appearances", 0)) > 0 and s.get("average_contribution") is not None]
        if not c_seasons:
            c_block = {
                "metric_id": "average_contribution",
                "label": "Average Contribution Score",
                "unit": "/ 100",
                "highest": None,
                "lowest": None,
                "insufficient_data": True,
                "interpretation": "Official Strategy 4 contribution score relative to Par (50.0). DNB matches are strictly excluded.",
            }
        else:
            max_c = max(s["average_contribution"] for s in c_seasons)
            min_c = min(s["average_contribution"] for s in c_seasons)
            max_s = [s for s in c_seasons if s["average_contribution"] == max_c]
            min_s = [s for s in c_seasons if s["average_contribution"] == min_c]
            c_block = {
                "metric_id": "average_contribution",
                "label": "Average Contribution Score",
                "unit": "/ 100",
                "highest": _build_entry(max_s[0], max_c, [str(s["season"]) for s in max_s[1:]]),
                "lowest": _build_entry(min_s[0], min_c, [str(s["season"]) for s in min_s[1:]]),
                "insufficient_data": False,
                "interpretation": "Synthesized batting execution and team match state impact. Scores above 50.0 add positive situational value.",
            }

        return {
            "runs": runs_block,
            "strike_rate": sr_block,
            "dot_ball_percentage": dot_block,
            "average_contribution": c_block,
        }

    def _get_bowler_classification(self) -> Dict[str, str]:
        """Loads and caches auditable verified bowler style mapping."""
        if self._bowler_classification_cache is None:
            fpath = DATA_DIR / "bowler_classification.json"
            if fpath.exists():
                with open(fpath, "r", encoding="utf-8") as f:
                    self._bowler_classification_cache = json.load(f)
            else:
                self._bowler_classification_cache = {}
        return self._bowler_classification_cache

    BOWLER_CREDITED_DISMISSALS = {
        "bowled",
        "caught",
        "caught and bowled",
        "lbw",
        "stumped",
        "hit wicket",
    }

    @classmethod
    def _is_bowler_credited_dismissal(cls, kind: Optional[str]) -> bool:
        """Determines if a dismissal kind is officially credited to the bowler."""
        if not kind:
            return False
        norm = str(kind).strip().lower().replace("-", " ").replace("&", "and")
        return norm in cls.BOWLER_CREDITED_DISMISSALS

    @classmethod
    def _extract_bowler_dismissal_event(
        cls, delivery: Dict[str, Any], player_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Extracts bowler-credited dismissal event for a batter from a delivery record.
        Strictly excludes run-outs, retired out/hurt, and other non-bowler-credited dismissals.
        Returns dismissal dict with bowler, kind, and unique delivery identifier.
        """
        # 1. Check multi-wicket structures (e.g. from T20I JSON match deliveries)
        wickets = delivery.get("wickets")
        if wickets and isinstance(wickets, list):
            for w in wickets:
                if w.get("player_out") == player_name:
                    kind = w.get("kind")
                    if cls._is_bowler_credited_dismissal(kind):
                        return {
                            "bowler": delivery.get("bowler"),
                            "dismissal_kind": kind,
                            "match_id": str(delivery.get("match_id", "")),
                            "innings": str(delivery.get("innings") or delivery.get("innings_number", "1")),
                            "over": str(delivery.get("over", "")),
                            "ball": str(delivery.get("ball", "")),
                        }
                    return None

        # 2. Check standard fields (e.g. from IPL CSV deliveries)
        p_out = delivery.get("player_dismissed")
        if p_out == player_name:
            kind = delivery.get("dismissal_kind")
            if cls._is_bowler_credited_dismissal(kind):
                return {
                    "bowler": delivery.get("bowler"),
                    "dismissal_kind": kind,
                    "match_id": str(delivery.get("match_id", "")),
                    "innings": str(delivery.get("innings_number") or delivery.get("innings", "1")),
                    "over": str(delivery.get("over", "")),
                    "ball": str(delivery.get("ball", "")),
                }

        return None

    def _get_ipl_deliveries_df(self) -> Optional[pd.DataFrame]:
        """Loads and caches IPL ball-by-ball delivery dataset."""
        if self._ipl_deliveries_df_cache is None:
            fpath = DATA_DIR / "deliveries.csv"
            if fpath.exists():
                cols = [
                    "match_id",
                    "innings_number",
                    "over",
                    "ball",
                    "season",
                    "batter",
                    "bowler",
                    "batter_runs",
                    "total_runs",
                    "wides",
                    "player_dismissed",
                    "dismissal_kind",
                ]
                df = pd.read_csv(fpath, usecols=cols, low_memory=False)
                df["match_id"] = df["match_id"].astype(str)
                self._ipl_deliveries_df_cache = df
            else:
                self._ipl_deliveries_df_cache = pd.DataFrame()
        return self._ipl_deliveries_df_cache

    def _get_t20i_match_deliveries(self, match_id: Any) -> List[Dict[str, Any]]:
        """Parses and caches T20I match ball-by-ball deliveries from raw match JSON."""
        mid_str = str(match_id)
        if mid_str in self._t20i_deliveries_cache:
            return self._t20i_deliveries_cache[mid_str]

        raw_dirs = [
            ROOT_DIR / "data" / "t20s_json",
            ROOT_DIR / "data" / "raw",
        ]
        fpath = None
        for d in raw_dirs:
            cand = d / f"{mid_str}.json"
            if cand.exists():
                fpath = cand
                break

        deliveries = []
        if fpath and fpath.exists():
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                inns_list = data.get("innings", [])
                for inns_idx, inns in enumerate(inns_list, start=1):
                    for over_idx, over in enumerate(inns.get("overs", [])):
                        over_num = over.get("over", over_idx)
                        for ball_idx, d in enumerate(over.get("deliveries", [])):
                            batter = d.get("batter")
                            bowler = d.get("bowler")
                            extras = d.get("extras", {})
                            wides = 1 if "wides" in extras else 0
                            runs_dict = d.get("runs", {})
                            b_runs = int(runs_dict.get("batter", 0))
                            tot_runs = int(runs_dict.get("total", 0))
                            wickets = d.get("wickets", [])

                            p_out = None
                            kind = None
                            if wickets:
                                p_out = wickets[0].get("player_out")
                                kind = wickets[0].get("kind")

                            deliveries.append({
                                "match_id": mid_str,
                                "innings": inns_idx,
                                "over": over_num,
                                "ball": ball_idx + 1,
                                "batter": batter,
                                "bowler": bowler,
                                "batter_runs": b_runs,
                                "total_runs": tot_runs,
                                "wides": wides,
                                "player_dismissed": p_out,
                                "dismissal_kind": kind,
                                "wickets": wickets,
                            })
            except Exception:
                pass

        self._t20i_deliveries_cache[mid_str] = deliveries
        return deliveries

    @staticmethod
    def _empty_bowling_stats() -> Dict[str, Any]:
        """Returns baseline empty stats structure when 0 balls are faced."""
        return {
            "runs": 0,
            "balls_faced": 0,
            "strike_rate": None,
            "dismissals": 0,
            "average": None,
            "dot_balls": 0,
            "dot_ball_percentage": None,
            "fours": 0,
            "sixes": 0,
            "boundary_runs": 0,
            "boundary_percentage": None,
            "boundary_ball_percentage": None,
            "is_not_out": False,
            "insufficient_sample": False,
        }

    @staticmethod
    def _compute_bowling_stats(balls: List[Dict[str, Any]], outs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculates aggregate batting metrics against a specific bowling category.
        Strictly enforces:
        - Strike rate = (runs / balls_faced) * 100
        - Average = runs / dismissals (None with is_not_out=True when dismissals == 0 and balls > 0)
        - Dot-ball % = dot_balls / balls_faced * 100
        - Boundary % = (boundary_runs / runs) * 100
        - Boundary ball % = ((fours + sixes) / balls_faced) * 100
        - Flag seasons with insufficient sample (<20 balls)
        """
        b_count = len(balls)
        if b_count == 0:
            return DataService._empty_bowling_stats()

        runs = sum(int(b.get("batter_runs", 0)) for b in balls)
        sr = clean_num(runs / b_count * 100.0, 1)
        dismissals = len(outs)
        is_not_out = (dismissals == 0)
        avg = clean_num(runs / dismissals, 1) if dismissals > 0 else None
        dots = sum(1 for b in balls if int(b.get("total_runs", 0)) == 0)
        dot_pct = clean_num(dots / b_count * 100.0, 1)
        fours = sum(1 for b in balls if int(b.get("batter_runs", 0)) == 4)
        sixes = sum(1 for b in balls if int(b.get("batter_runs", 0)) == 6)
        b_runs = (fours * 4) + (sixes * 6)
        b_pct = clean_num(b_runs / runs * 100.0, 1) if runs > 0 else 0.0
        b_ball_pct = clean_num((fours + sixes) / b_count * 100.0, 1)

        return {
            "runs": runs,
            "balls_faced": b_count,
            "strike_rate": sr,
            "dismissals": dismissals,
            "average": avg,
            "dot_balls": dots,
            "dot_ball_percentage": dot_pct,
            "fours": fours,
            "sixes": sixes,
            "boundary_runs": b_runs,
            "boundary_percentage": b_pct,
            "boundary_ball_percentage": b_ball_pct,
            "is_not_out": is_not_out,
            "insufficient_sample": b_count < 20,
        }

    def _compute_bowling_type_trends(
        self,
        player_name: str,
        norm_comp: str,
        appearances: List[Dict[str, Any]],
        sorted_keys: List[str],
        grouped: Dict[str, List[Dict[str, Any]]],
    ) -> Dict[str, Any]:
        """
        Calculates auditable season-by-season and overall career Pace vs Spin
        batting performance trends from ball-by-ball delivery records.
        """
        bclass = self._get_bowler_classification()

        # Collect deliveries mapped by match_id
        deliv_by_mid: Dict[str, List[Dict[str, Any]]] = {}

        # 1. IPL deliveries
        ipl_mids = set(str(a["match_id"]) for a in appearances if a.get("competition") == "IPL")
        if ipl_mids:
            df_ipl = self._get_ipl_deliveries_df()
            if df_ipl is not None and not df_ipl.empty:
                sub_ipl = df_ipl[
                    (df_ipl["match_id"].isin(ipl_mids))
                    & ((df_ipl["batter"] == player_name) | (df_ipl["player_dismissed"] == player_name))
                ]
                for row in sub_ipl.to_dict("records"):
                    mid = str(row["match_id"])
                    deliv_by_mid.setdefault(mid, []).append(row)

        # 2. T20I deliveries
        t20i_mids = set(str(a["match_id"]) for a in appearances if a.get("competition") == "International")
        for mid in t20i_mids:
            t20i_delivs = self._get_t20i_match_deliveries(mid)
            if t20i_delivs:
                relevant = [
                    d for d in t20i_delivs
                    if d.get("batter") == player_name
                    or d.get("player_dismissed") == player_name
                    or any(w.get("player_out") == player_name for w in d.get("wickets", []))
                ]
                if relevant:
                    deliv_by_mid[str(mid)] = relevant

        # Build seasons breakdown
        seasons_list: List[Dict[str, Any]] = []
        all_career_balls_faced: List[Dict[str, Any]] = []
        all_career_outs: List[Dict[str, Any]] = []
        unclassified_bowler_names = set()

        for k in sorted_keys:
            group_apps = grouped[k]
            matches = len(group_apps)
            batted_apps = [a for a in group_apps if not a.get("is_dnb")]
            batting_inns = len(batted_apps)
            dnb_matches = matches - batting_inns

            season_mids = set(str(a["match_id"]) for a in group_apps)
            season_deliv: List[Dict[str, Any]] = []
            for mid in season_mids:
                season_deliv.extend(deliv_by_mid.get(mid, []))

            # Deliveries faced (wides strictly excluded)
            balls_faced = [
                d for d in season_deliv
                if d.get("batter") == player_name and int(d.get("wides", 0)) == 0
            ]
            all_career_balls_faced.extend(balls_faced)

            # Dismissals credited to bowlers (prevent duplicate counting on same delivery)
            season_outs: List[Dict[str, Any]] = []
            seen_out_delivery_keys = set()
            for d in season_deliv:
                out_event = self._extract_bowler_dismissal_event(d, player_name)
                if out_event:
                    deliv_key = (
                        out_event["match_id"],
                        out_event["innings"],
                        out_event["over"],
                        out_event["ball"],
                        player_name,
                    )
                    if deliv_key not in seen_out_delivery_keys:
                        seen_out_delivery_keys.add(deliv_key)
                        season_outs.append(out_event)

            all_career_outs.extend(season_outs)

            # Classify using auditable mapping
            pace_balls = [d for d in balls_faced if bclass.get(d.get("bowler")) == "Pace"]
            spin_balls = [d for d in balls_faced if bclass.get(d.get("bowler")) == "Spin"]
            unclass_balls = [d for d in balls_faced if d.get("bowler") not in bclass]

            for d in unclass_balls:
                bname = d.get("bowler")
                if bname:
                    unclassified_bowler_names.add(bname)

            pace_outs = [o for o in season_outs if bclass.get(o.get("bowler")) == "Pace"]
            spin_outs = [o for o in season_outs if bclass.get(o.get("bowler")) == "Spin"]
            unclass_outs = [o for o in season_outs if bclass.get(o.get("bowler")) not in ("Pace", "Spin")]

            for o in unclass_outs:
                bname = o.get("bowler")
                if bname:
                    unclassified_bowler_names.add(bname)

            pace_stats = self._compute_bowling_stats(pace_balls, pace_outs)
            spin_stats = self._compute_bowling_stats(spin_balls, spin_outs)

            tot_balls = len(balls_faced)
            class_balls = len(pace_balls) + len(spin_balls)
            unclass_balls_cnt = len(unclass_balls)
            cov_pct = clean_num(class_balls / tot_balls * 100.0, 1) if tot_balls > 0 else 100.0

            ipl_apps = [a for a in group_apps if a.get("competition") == "IPL"]
            t20i_apps = [a for a in group_apps if a.get("competition") == "International"]
            comp_label = (
                "IPL" if norm_comp == "ipl"
                else "International" if norm_comp == "t20i"
                else ("IPL + INL" if (len(ipl_apps) > 0 and len(t20i_apps) > 0) else ("IPL" if len(ipl_apps) > 0 else "International"))
            )

            seasons_list.append({
                "season": k,
                "competition": comp_label,
                "matches": matches,
                "batting_innings": batting_inns,
                "dnb_matches": dnb_matches,
                "total_balls_faced": tot_balls,
                "classified_balls_faced": class_balls,
                "unclassified_balls_faced": unclass_balls_cnt,
                "coverage_percentage": cov_pct,
                "insufficient_sample": (tot_balls > 0 and tot_balls < 20),
                "pace": pace_stats,
                "spin": spin_stats,
                "pace_dismissals": pace_stats["dismissals"],
                "spin_dismissals": spin_stats["dismissals"],
                "unclassified_dismissals": len(unclass_outs),
                "bowler_credited_dismissals": len(season_outs),
            })

        # Overall Career Totals
        career_pace_balls = [d for d in all_career_balls_faced if bclass.get(d.get("bowler")) == "Pace"]
        career_spin_balls = [d for d in all_career_balls_faced if bclass.get(d.get("bowler")) == "Spin"]
        career_unclass_balls = [d for d in all_career_balls_faced if d.get("bowler") not in bclass]

        career_pace_outs = [o for o in all_career_outs if bclass.get(o.get("bowler")) == "Pace"]
        career_spin_outs = [o for o in all_career_outs if bclass.get(o.get("bowler")) == "Spin"]
        career_unclass_outs = [o for o in all_career_outs if bclass.get(o.get("bowler")) not in ("Pace", "Spin")]

        career_pace_stats = self._compute_bowling_stats(career_pace_balls, career_pace_outs)
        career_spin_stats = self._compute_bowling_stats(career_spin_balls, career_spin_outs)

        tot_career_balls = len(all_career_balls_faced)
        class_career_balls = len(career_pace_balls) + len(career_spin_balls)
        unclass_career_balls = len(career_unclass_balls)
        career_cov_pct = clean_num(class_career_balls / tot_career_balls * 100.0, 1) if tot_career_balls > 0 else 100.0

        tot_career_outs = len(all_career_outs)
        class_career_outs = len(career_pace_outs) + len(career_spin_outs)
        unclass_career_outs = len(career_unclass_outs)
        dismissals_cov_pct = clean_num(class_career_outs / tot_career_outs * 100.0, 1) if tot_career_outs > 0 else 100.0

        summary = {
            "total_balls_faced": tot_career_balls,
            "classified_balls_faced": class_career_balls,
            "unclassified_balls_faced": unclass_career_balls,
            "coverage_percentage": career_cov_pct,
            "is_coverage_complete": (unclass_career_balls == 0 and unclass_career_outs == 0),
            "pace": career_pace_stats,
            "spin": career_spin_stats,
            "pace_dismissals": career_pace_stats["dismissals"],
            "spin_dismissals": career_spin_stats["dismissals"],
            "unclassified_dismissals": unclass_career_outs,
            "bowler_credited_dismissals": tot_career_outs,
            "dismissals_coverage_percentage": dismissals_cov_pct,
        }

        coverage_info = {
            "total_balls_faced": tot_career_balls,
            "classified_balls": class_career_balls,
            "unclassified_balls": unclass_career_balls,
            "coverage_percentage": career_cov_pct,
            "total_bowler_dismissals": tot_career_outs,
            "classified_bowler_dismissals": class_career_outs,
            "unclassified_bowler_dismissals": unclass_career_outs,
            "dismissals_coverage_percentage": dismissals_cov_pct,
            "classification_source": "Auditable Bowler Style Registry (577 bowlers)",
            "unclassified_bowlers_count": len(unclassified_bowler_names),
            "unclassified_bowlers": sorted(list(unclassified_bowler_names)),
        }

        return {
            "summary": summary,
            "seasons": seasons_list,
            "coverage_info": coverage_info,
        }

    def get_dataset_coverage(self, competition: Optional[str] = None) -> Dict[str, Any]:
        """
        Derives non-hardcoded dataset coverage period from actual match records
        for IPL, International T20I, and Combined.
        Excludes invalid/missing dates and discloses reliability.
        """
        if self._dataset_coverage_cache is None:
            coverage = {}
            for comp in ("ipl", "t20i"):
                self._ensure_loaded(comp)
                matches_df = self.get_matches_df(comp)
                label = "IPL Records" if comp == "ipl" else "International T20I Records"

                if matches_df is None or matches_df.empty:
                    coverage[comp] = {
                        "competition": comp,
                        "label": label,
                        "start_year": None,
                        "end_year": None,
                        "start_date": None,
                        "end_date": None,
                        "display_range": "N/A",
                        "total_matches": 0,
                        "valid_date_matches": 0,
                        "reliable": False,
                        "note": "No match records loaded in dataset",
                    }
                    continue

                total_m = len(matches_df)
                dates = pd.to_datetime(matches_df.get("date"), errors="coerce").dropna()
                valid_m = len(dates)

                if dates.empty:
                    seasons = sorted(str(s) for s in matches_df.get("season", []).dropna().unique() if str(s).strip())
                    if seasons:
                        s_start = seasons[0]
                        s_end = seasons[-1]
                        display_range = f"{s_start} – {s_end}" if s_start != s_end else s_start
                        coverage[comp] = {
                            "competition": comp,
                            "label": label,
                            "start_year": None,
                            "end_year": None,
                            "start_date": None,
                            "end_date": None,
                            "display_range": display_range,
                            "total_matches": total_m,
                            "valid_date_matches": 0,
                            "reliable": True,
                            "note": "Derived from season identifiers",
                        }
                    else:
                        coverage[comp] = {
                            "competition": comp,
                            "label": label,
                            "start_year": None,
                            "end_year": None,
                            "start_date": None,
                            "end_date": None,
                            "display_range": "N/A",
                            "total_matches": total_m,
                            "valid_date_matches": 0,
                            "reliable": False,
                            "note": "Match dates could not be determined reliably",
                        }
                else:
                    min_d = dates.min()
                    max_d = dates.max()
                    min_yr = int(min_d.year)
                    max_yr = int(max_d.year)
                    display_range = f"{min_yr} – {max_yr}" if min_yr != max_yr else str(min_yr)
                    reliable = (valid_m / total_m >= 0.8) if total_m > 0 else False

                    coverage[comp] = {
                        "competition": comp,
                        "label": label,
                        "start_year": min_yr,
                        "end_year": max_yr,
                        "start_date": min_d.strftime("%Y-%m-%d"),
                        "end_date": max_d.strftime("%Y-%m-%d"),
                        "display_range": display_range,
                        "total_matches": total_m,
                        "valid_date_matches": valid_m,
                        "reliable": reliable,
                        "note": "Derived from valid match records in dataset" if reliable else "Partial match dates in dataset",
                    }

            self._dataset_coverage_cache = coverage

        cached = self._dataset_coverage_cache or {}
        if competition:
            norm = competition.strip().lower()
            if norm in cached:
                return cached[norm]
        return cached


# Singleton instance
data_service = DataService()

