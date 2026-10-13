"""
Mock Cricket API Adapter for Testing and Simulation.
Provides deterministic responses representing:
- Valid completed T20 match (IPL / T20I / SMAT / WPL)
- Non-T20 match (ODI / Test / Ranji / rain-shortened ODI)
- Batter innings with active batting opportunities and strict DNB appearances
"""

from typing import Dict, Any, List, Optional, Tuple
from app.adapters.base import (
    CricketApiAdapter,
    VALID_T20_FORMAT_TOKENS,
    EXCLUDED_NON_T20_TOKENS,
)


class MockCricketApiAdapter(CricketApiAdapter):
    """
    Deterministic mock adapter for automated testing.
    """

    def __init__(self):
        self._matches_db: Dict[str, Dict[str, Any]] = {}
        self._setup_mock_database()

    @property
    def provider_name(self) -> str:
        return "mock"

    def _setup_mock_database(self):
        # 1. Valid T20 Match: Mumbai Indians vs Chennai Super Kings (IPL T20)
        self._matches_db["mock_t20_ipl_001"] = {
            "id": "mock_t20_ipl_001",
            "name": "Mumbai Indians vs Chennai Super Kings, Final",
            "matchType": "t20",
            "season": "2024",
            "date": "2024-05-26",
            "venue": "Narendra Modi Stadium, Ahmedabad",
            "city": "Ahmedabad",
            "status": "Chennai Super Kings won by 5 wickets",
            "teams": ["Mumbai Indians", "Chennai Super Kings"],
            "toss": {"winner": "Chennai Super Kings", "decision": "field"},
            "outcome": {"winner": "Chennai Super Kings", "by": {"wickets": 5}},
            "scorecard": {
                "innings": [
                    {
                        "innings_number": 1,
                        "team": "Mumbai Indians",
                        "total_runs": 182,
                        "total_wickets": 6,
                        "overs": 20.0,
                        "batters": [
                            {"player": "RG Sharma", "runs": 45, "balls": 28, "fours": 5, "sixes": 2, "dismissal_status": "out", "dismissal_kind": "caught", "entry_over": 0.0, "exit_over": 8.2},
                            {"player": "Ishan Kishan", "runs": 23, "balls": 18, "fours": 3, "sixes": 0, "dismissal_status": "out", "dismissal_kind": "bowled", "entry_over": 0.0, "exit_over": 5.4},
                            {"player": "SA Yadav", "runs": 62, "balls": 34, "fours": 6, "sixes": 4, "dismissal_status": "out", "dismissal_kind": "caught", "entry_over": 5.4, "exit_over": 17.1},
                            {"player": "HH Pandya", "runs": 30, "balls": 16, "fours": 2, "sixes": 2, "dismissal_status": "not out", "dismissal_kind": None, "entry_over": 8.2, "exit_over": 20.0},
                            {"player": "TH David", "runs": 12, "balls": 8, "fours": 1, "sixes": 1, "dismissal_status": "out", "dismissal_kind": "run out", "entry_over": 17.1, "exit_over": 19.2},
                            {"player": "JJ Bumrah", "runs": 0, "balls": 0, "dnb": True, "dismissal_status": "dnb"},
                        ],
                    },
                    {
                        "innings_number": 2,
                        "team": "Chennai Super Kings",
                        "target": 183,
                        "total_runs": 185,
                        "total_wickets": 5,
                        "overs": 19.3,
                        "batters": [
                            {"player": "RD Gaikwad", "runs": 55, "balls": 38, "fours": 6, "sixes": 2, "dismissal_status": "out", "dismissal_kind": "caught", "entry_over": 0.0, "exit_over": 12.1},
                            {"player": "R Ravindra", "runs": 35, "balls": 20, "fours": 4, "sixes": 2, "dismissal_status": "out", "dismissal_kind": "caught", "entry_over": 0.0, "exit_over": 6.3},
                            {"player": "S Dube", "runs": 48, "balls": 24, "fours": 2, "sixes": 5, "dismissal_status": "not out", "dismissal_kind": None, "entry_over": 6.3, "exit_over": 19.3},
                            {"player": "MS Dhoni", "runs": 0, "balls": 0, "dnb": True, "dismissal_status": "dnb"},
                        ],
                    },
                ]
            },
        }

        # 2. Excluded Non-T20 Match: India vs Australia ODI (50 overs)
        self._matches_db["mock_odi_002"] = {
            "id": "mock_odi_002",
            "name": "India vs Australia, 1st ODI",
            "matchType": "odi",
            "season": "2024",
            "status": "India won by 5 wickets",
        }

        # 3. Excluded Rain-shortened Match (18 overs, but officially an ODI!)
        self._matches_db["mock_curtailed_odi_003"] = {
            "id": "mock_curtailed_odi_003",
            "name": "England vs New Zealand (Rain Reduced to 18 Overs)",
            "matchType": "odi",
            "status": "England won by 20 runs (DLS)",
        }

        # 4. Excluded Ranji Trophy Match (First-Class multi-day)
        self._matches_db["mock_ranji_004"] = {
            "id": "mock_ranji_004",
            "name": "Mumbai vs Karnataka, Ranji Trophy Semi-Final",
            "matchType": "first-class",
            "status": "Mumbai won by 120 runs",
        }

    def validate_t20_format(self, match_metadata: Dict[str, Any]) -> Tuple[bool, str]:
        match_type = str(match_metadata.get("matchType") or match_metadata.get("match_type") or "").strip().lower()
        title = str(match_metadata.get("name") or match_metadata.get("title") or "").lower()

        for ex in EXCLUDED_NON_T20_TOKENS:
            if match_type == ex or f" {ex} " in f" {match_type} " or f" {ex} " in f" {title} ":
                return False, f"Non-T20 format detected ('{match_type}' / '{ex}')"

        if not match_type:
            return False, "Missing official format metadata; cannot verify as T20"

        if match_type in VALID_T20_FORMAT_TOKENS:
            return True, f"Verified T20 match format: '{match_type}'"

        return False, f"Format '{match_type}' is not an authorized T20 competition"

    def get_completed_matches(self, limit: int = 25) -> List[Dict[str, Any]]:
        completed = []
        for m_id, m in self._matches_db.items():
            is_t20, _ = self.validate_t20_format(m)
            if is_t20:
                completed.append(m)
        return completed[:limit]

    def fetch_match_details(self, match_id: str) -> Dict[str, Any]:
        if match_id not in self._matches_db:
            raise KeyError(f"Mock match '{match_id}' not found.")
        m = self._matches_db[match_id]
        is_t20, reason = self.validate_t20_format(m)
        if not is_t20:
            raise ValueError(f"Match '{match_id}' is not an eligible T20 match: {reason}")
        return m

    def fetch_ball_by_ball(self, match_id: str) -> Optional[List[Dict[str, Any]]]:
        return []
