"""
CricketLiveApi Adapter Implementation.
Connects to CricketLiveApi (cricketliveapi.com) REST API.

CRITICAL RESEARCH FINDING:
The official CricketLiveApi free tier (100 calls/day, 5 req/min) EXPLICITLY disables
scorecard data and player statistics (marked with an X in official pricing).
Access to scorecards requires at least the Starter tier (₹499/mo), and commentary
requires the Pro tier (₹999/mo).
This adapter documents these exact constraints and validates tiers before attempting
unauthorized scorecard extractions.
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


class CricketLiveApiAdapter(CricketApiAdapter):
    """
    Adapter for CricketLiveApi (cricketliveapi.com).
    Free Tier: 100 calls/day, 5 req/min (Live scores & schedule only; NO scorecards).
    Starter Tier: ₹499/mo (Includes scorecards).
    Pro Tier: ₹999/mo (Includes ball-by-ball commentary).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://cricketliveapi.com/api/v1/",
        tier: str = "free",
    ):
        self.api_key = api_key or os.environ.get("CRICKETLIVEAPI_KEY", "")
        self.base_url = base_url.rstrip("/") + "/"
        self.tier = (tier or os.environ.get("CRICKETLIVEAPI_TIER", "free")).lower()
        self._daily_calls_count = 0
        self.daily_limit = 100 if self.tier == "free" else 1000

    @property
    def provider_name(self) -> str:
        return "cricketliveapi.com"

    def validate_t20_format(self, match_metadata: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validates match format using CricketLiveApi format/match_type metadata.
        """
        match_type = str(
            match_metadata.get("match_type") or match_metadata.get("format") or ""
        ).strip().lower()
        title = str(match_metadata.get("title") or match_metadata.get("name") or "").lower()

        # Check explicit exclusions
        for ex in EXCLUDED_NON_T20_TOKENS:
            if match_type == ex or f" {ex} " in f" {match_type} " or f" {ex} " in f" {title} ":
                return False, f"Non-T20 format detected ('{match_type}' / '{ex}' in '{title}')"

        if not match_type:
            return False, "Missing official format metadata; cannot verify T20 format"

        if match_type in VALID_T20_FORMAT_TOKENS:
            return True, f"Verified T20 match format: '{match_type}'"

        return False, f"Format '{match_type}' is not an authorized T20 competition"

    def get_completed_matches(self, limit: int = 25) -> List[Dict[str, Any]]:
        """
        Discovers completed matches.
        """
        if not self.api_key:
            raise ValueError("CricketLiveApi API key is missing.")

        url = f"{self.base_url}matches/completed"
        headers = {"X-API-Key": self.api_key}
        resp = httpx.get(url, headers=headers, timeout=10.0)
        self._daily_calls_count += 1
        resp.raise_for_status()
        matches = resp.json().get("matches", [])

        completed_t20 = []
        for m in matches:
            is_t20, reason = self.validate_t20_format(m)
            if is_t20:
                completed_t20.append(m)
            else:
                logger.debug(f"Skipping match {m.get('id')}: {reason}")

        return completed_t20[:limit]

    def fetch_match_details(self, match_id: str) -> Dict[str, Any]:
        """
        Fetches match scorecard.
        Enforces tier verification: CricketLiveApi free tier does not support scorecards.
        """
        if self.tier == "free":
            raise PermissionError(
                "CricketLiveApi Free Tier does NOT include scorecard data or player statistics "
                "(requires Starter plan at ₹499/mo). Please upgrade tier or use CricketData.org / Cricsheet."
            )

        if not self.api_key:
            raise ValueError("CricketLiveApi API key is missing.")

        url = f"{self.base_url}matches/{match_id}/scorecard"
        headers = {"X-API-Key": self.api_key}
        resp = httpx.get(url, headers=headers, timeout=10.0)
        self._daily_calls_count += 1
        resp.raise_for_status()
        data = resp.json()

        is_t20, reason = self.validate_t20_format(data)
        if not is_t20:
            raise ValueError(f"Match {match_id} is not an eligible T20 match: {reason}")

        return data

    def fetch_ball_by_ball(self, match_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Fetches ball-by-ball commentary (requires Pro tier).
        """
        if self.tier in ("free", "starter"):
            logger.warning("CricketLiveApi requires Pro tier (₹999/mo) for ball-by-ball commentary.")
            return None

        url = f"{self.base_url}matches/{match_id}/commentary"
        headers = {"X-API-Key": self.api_key}
        try:
            resp = httpx.get(url, headers=headers, timeout=10.0)
            self._daily_calls_count += 1
            resp.raise_for_status()
            return resp.json().get("commentary", [])
        except Exception as e:
            logger.error(f"Failed to fetch CricketLiveApi commentary: {e}")
            return None
