"""
Abstract Base Class for Cricket API Adapters.
Ensures provider-agnostic integration for T20 cricket data ingestion.
Strictly enforces T20 format verification and rejection of non-T20 matches.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple


# Canonical T20 format identifiers across different cricket data providers
VALID_T20_FORMAT_TOKENS = {
    "t20",
    "t20i",
    "it20",
    "twenty20",
    "twenty-20",
}

# Explicitly excluded non-T20 format identifiers
EXCLUDED_NON_T20_TOKENS = {
    "odi",
    "one-day",
    "one day",
    "list a",
    "lista",
    "test",
    "first-class",
    "first class",
    "fc",
    "ranji",
    "ranji trophy",
    "vijay hazare",
    "duleep trophy",
    "irani cup",
    "mdm",
}

# Supported Indian & International T20 tournament identifiers / keywords
SUPPORTED_T20_COMPETITIONS = {
    "ipl": "Indian Premier League",
    "indian premier league": "Indian Premier League",
    "t20i": "International T20",
    "india t20i": "India International T20",
    "wpl": "Women's Premier League",
    "women's premier league": "Women's Premier League",
    "wt20i": "Women's International T20",
    "women's t20i": "Women's International T20",
    "women's t20": "Women's T20",
}

# Deactivated competitions (preserved for future reactivation)
DEACTIVATED_T20_COMPETITIONS = {
    "smat": "Syed Mushtaq Ali Trophy",
    "syed mushtaq ali": "Syed Mushtaq Ali Trophy",
    "syed mushtaq ali trophy": "Syed Mushtaq Ali Trophy",
}


class CricketApiAdapter(ABC):
    """
    Abstract Base Class for replaceable Cricket API backend adapters.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Unique identifier for the API provider."""
        pass

    @abstractmethod
    def validate_t20_format(self, match_metadata: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validates whether a match is officially a T20 match using provider metadata.
        
        Strict match format restrictions:
        - Must be verified as T20 from official provider metadata (matchType, format, match_type).
        - Rain-shortened matches in non-T20 formats (e.g. 15-over ODI) must be REJECTED.
        - Test, First-class, Ranji Trophy, ODI, List A matches must be REJECTED.
        
        Returns:
            Tuple[bool, str]: (is_valid_t20, reason_description)
        """
        pass

    @abstractmethod
    def get_completed_matches(self, limit: int = 25) -> List[Dict[str, Any]]:
        """
        Discovers recently completed matches from the provider.
        Returns a list of match metadata dictionaries.
        """
        pass

    @abstractmethod
    def fetch_match_details(self, match_id: str) -> Dict[str, Any]:
        """
        Fetches full match details including scorecards, rosters, and outcomes.
        """
        pass

    @abstractmethod
    def fetch_ball_by_ball(self, match_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Fetches ball-by-ball delivery event logs if supported by the provider tier.
        Returns None if ball-by-ball is unavailable on provider/tier.
        """
        pass
