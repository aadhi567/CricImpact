"""
Cricsheet Feed Adapter Implementation.
Connects to Cricsheet open match JSON data feeds (cricsheet.org).
Provides 100% ball-by-ball fidelity identical to our existing 1,243 match training dataset.
Covers IPL, T20Is, Syed Mushtaq Ali Trophy (SMAT), and WPL with zero cost and no rate limits.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from app.adapters.base import (
    CricketApiAdapter,
    VALID_T20_FORMAT_TOKENS,
    EXCLUDED_NON_T20_TOKENS,
)
from src.data_loader import parse_single_match

logger = logging.getLogger(__name__)


class CricsheetFeedAdapter(CricketApiAdapter):
    """
    Adapter for Cricsheet JSON matches.
    Can ingest from a directory of downloaded Cricsheet JSON files,
    automated download feed, or webhook payload.
    """

    def __init__(self, feed_dir: Optional[str] = None):
        self.feed_dir = Path(feed_dir or "data/raw")

    @property
    def provider_name(self) -> str:
        return "cricsheet.org"

    def validate_t20_format(self, match_metadata: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validates match format using Cricsheet's info.match_type metadata.
        Standard Cricsheet T20 values: 'T20', 'IT20'.
        Non-T20 values to reject: 'ODI', 'MDM' (Multi-day/First-class/Test).
        """
        info = match_metadata.get("info", match_metadata)
        match_type = str(info.get("match_type", "")).strip().lower()
        event_info = info.get("event", {})
        event_name = str(event_info.get("name", "")).lower()

        # Check explicit exclusions
        for ex in EXCLUDED_NON_T20_TOKENS:
            if match_type == ex or f" {ex} " in f" {match_type} " or f" {ex} " in f" {event_name} ":
                return False, f"Non-T20 format detected ('{match_type}' / '{ex}' in '{event_name}')"

        if not match_type:
            return False, "Missing official Cricsheet 'match_type' metadata"

        if match_type in VALID_T20_FORMAT_TOKENS:
            return True, f"Verified T20 match format: '{match_type}'"

        return False, f"Format '{match_type}' is not an authorized T20 competition"

    def get_completed_matches(self, limit: int = 25) -> List[Dict[str, Any]]:
        """
        Scans the feed directory for available completed JSON matches.
        """
        if not self.feed_dir.exists():
            return []

        json_files = sorted(self.feed_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        completed = []

        for jf in json_files:
            try:
                with open(jf, "r", encoding="utf-8") as f:
                    data = json.load(f)
                info = data.get("info", {})
                is_t20, reason = self.validate_t20_format(data)
                if is_t20:
                    completed.append({
                        "id": jf.stem,
                        "filepath": str(jf),
                        "season": str(info.get("season", "")),
                        "teams": info.get("teams", []),
                        "dates": info.get("dates", []),
                        "venue": info.get("venue"),
                        "outcome": info.get("outcome", {}),
                    })
                if len(completed) >= limit:
                    break
            except Exception as e:
                logger.error(f"Error reading Cricsheet match {jf}: {e}")

        return completed

    def fetch_match_details(self, match_id: str) -> Dict[str, Any]:
        """
        Loads and parses match data using src.data_loader.parse_single_match.
        Returns parsed match, innings, deliveries, and batter_innings data.
        """
        # Search in feed directory
        jf = self.feed_dir / f"{match_id}.json"
        if not jf.exists():
            # Search recursively if needed
            matches = list(self.feed_dir.glob(f"**/{match_id}.json"))
            if matches:
                jf = matches[0]
            else:
                raise FileNotFoundError(f"Cricsheet match file for ID '{match_id}' not found in {self.feed_dir}")

        with open(jf, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        is_t20, reason = self.validate_t20_format(raw_data)
        if not is_t20:
            raise ValueError(f"Match {match_id} is not an eligible T20 match: {reason}")

        m_row, inn_rows, deliv_rows, batter_rows = parse_single_match(filepath=jf, match_dict=raw_data)

        return {
            "match_id": match_id,
            "raw_json": raw_data,
            "match_row": m_row,
            "innings_rows": inn_rows,
            "delivery_rows": deliv_rows,
            "batter_innings_rows": batter_rows,
        }

    def fetch_ball_by_ball(self, match_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Returns full structured delivery rows for the match.
        """
        details = self.fetch_match_details(match_id)
        return details.get("delivery_rows")
