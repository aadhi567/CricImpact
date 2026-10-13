"""
CricketData.org / CricAPI Adapter Implementation.
Connects to CricketData.org (api.cricapi.com/v1/) REST API.
Enforces strict T20 format validation, quota throttling, and scorecard extraction.
"""

import os
import logging
from typing import Dict, Any, List, Optional, Tuple
import httpx

from app.adapters.base import (
    CricketApiAdapter,
    VALID_T20_FORMAT_TOKENS,
    EXCLUDED_NON_T20_TOKENS,
)

logger = logging.getLogger(__name__)


class CricketDataOrgAdapter(CricketApiAdapter):
    """
    Adapter for CricketData.org (formerly CricAPI).
    Official base URL: https://api.cricapi.com/v1/
    Free-tier quota: 100 calls/day.
    """

    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.cricapi.com/v1/"):
        self.api_key = api_key or os.environ.get("CRICKETDATA_API_KEY", "")
        self.base_url = base_url.rstrip("/") + "/"
        self._daily_calls_count = 0
        self.daily_limit = 100

    @property
    def provider_name(self) -> str:
        return "cricketdata.org"

    def validate_t20_format(self, match_metadata: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validates match format using CricketData.org metadata.
        Checks 'matchType' field (e.g. 't20', 't20i').
        """
        match_type = str(match_metadata.get("matchType", "")).strip().lower()
        series_name = str(match_metadata.get("name", "")).lower()

        # Check explicit exclusions
        for ex in EXCLUDED_NON_T20_TOKENS:
            if match_type == ex or f" {ex} " in f" {match_type} " or f" {ex} " in f" {series_name} ":
                return False, f"Non-T20 format detected ('{match_type}' / '{ex}' in '{series_name}')"

        if not match_type:
            return False, "Missing official 'matchType' metadata; format cannot be verified as T20"

        if match_type in VALID_T20_FORMAT_TOKENS:
            return True, f"Verified T20 match format: '{match_type}'"

        return False, f"Format '{match_type}' is not an authorized T20 competition"

    def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Internal helper with quota tracking and error handling."""
        if not self.api_key:
            raise ValueError(
                "CricketData.org API key is missing. Set the CRICKETDATA_API_KEY environment variable "
                "or pass api_key to the adapter."
            )

        if self._daily_calls_count >= self.daily_limit:
            raise RuntimeError(
                f"CricketData.org daily free-tier limit of {self.daily_limit} calls reached. "
                "Throttling to prevent quota overages."
            )

        req_params = {"apikey": self.api_key}
        if params:
            req_params.update(params)

        url = f"{self.base_url}{endpoint}"
        logger.info(f"Calling CricketData.org [{endpoint}] (Call #{self._daily_calls_count + 1}/{self.daily_limit})")
        
        try:
            resp = httpx.get(url, params=req_params, timeout=10.0)
            self._daily_calls_count += 1
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") != "success":
                reason = data.get("reason") or data.get("message") or "Unknown API error"
                raise RuntimeError(f"CricketData.org API returned unsuccessful status: {reason}")
            return data
        except httpx.HTTPError as e:
            logger.error(f"CricketData.org request error on {endpoint}: {e}")
            raise

    def get_completed_matches(self, limit: int = 25) -> List[Dict[str, Any]]:
        """
        Discovers completed matches via currentMatches endpoint.
        Filters for matches where matchEnded == True and verifies format.
        """
        data = self._make_request("currentMatches")
        matches = data.get("data", [])
        completed = []
        for m in matches:
            is_ended = m.get("matchEnded", False) or "won" in str(m.get("status", "")).lower()
            if is_ended:
                is_t20, reason = self.validate_t20_format(m)
                if is_t20:
                    completed.append({
                        "id": str(m.get("id")),
                        "name": m.get("name"),
                        "matchType": m.get("matchType"),
                        "status": m.get("status"),
                        "venue": m.get("venue"),
                        "date": m.get("date"),
                        "dateTimeGMT": m.get("dateTimeGMT"),
                        "teams": m.get("teams", []),
                    })
                else:
                    logger.debug(f"Skipping match {m.get('id')} ({m.get('name')}): {reason}")

        return completed[:limit]

    def fetch_match_details(self, match_id: str) -> Dict[str, Any]:
        """
        Fetches match scorecard from match_scorecard endpoint.
        """
        data = self._make_request("match_scorecard", {"id": match_id})
        match_data = data.get("data", {})
        
        # Verify format
        is_t20, reason = self.validate_t20_format(match_data)
        if not is_t20:
            raise ValueError(f"Match {match_id} is not an eligible T20 match: {reason}")

        return match_data

    def fetch_ball_by_ball(self, match_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Fetches ball-by-ball commentary (match_bbb) if accessible.
        """
        try:
            data = self._make_request("match_bbb", {"id": match_id})
            return data.get("data", {}).get("bbb", [])
        except Exception as e:
            logger.warning(f"Ball-by-ball endpoint unavailable for match {match_id}: {e}")
            return None
