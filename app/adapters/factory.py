"""
Cricket API Adapter Factory.
Provides instantiation of configured or selected cricket API adapters.
Enables pluggable switching between data providers without modifying core math.
"""

import os
from typing import Optional
from app.adapters.base import CricketApiAdapter
from app.adapters.cricketdata_adapter import CricketDataOrgAdapter
from app.adapters.cricketliveapi_adapter import CricketLiveApiAdapter
from app.adapters.cricsheet_adapter import CricsheetFeedAdapter
from app.adapters.mock_adapter import MockCricketApiAdapter


def get_cricket_adapter(provider_name: Optional[str] = None, **kwargs) -> CricketApiAdapter:
    """
    Factory function returning the appropriate CricketApiAdapter instance.
    
    Args:
        provider_name: 'cricketdata.org' (or 'cricapi'), 'cricketliveapi',
                       'cricsheet', or 'mock'.
                       If None, reads from CRICKET_API_PROVIDER env var.
    """
    selected = (provider_name or os.environ.get("CRICKET_API_PROVIDER", "cricketdata.org")).lower().strip()

    if selected in ("cricketdata", "cricketdata.org", "cricapi"):
        return CricketDataOrgAdapter(api_key=kwargs.get("api_key"))

    elif selected in ("cricketliveapi", "cricketliveapi.com"):
        return CricketLiveApiAdapter(
            api_key=kwargs.get("api_key"),
            tier=kwargs.get("tier", "free"),
        )

    elif selected in ("cricsheet", "cricsheet.org", "feed"):
        return CricsheetFeedAdapter(feed_dir=kwargs.get("feed_dir"))

    elif selected in ("mock", "test"):
        return MockCricketApiAdapter()

    else:
        raise ValueError(
            f"Unsupported Cricket API provider: '{selected}'. "
            "Supported providers: 'cricketdata.org', 'cricketliveapi', 'cricsheet', 'mock'."
        )
