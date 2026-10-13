"""
Unit Tests for Cricket API Adapters.
Verifies format validation, strict non-T20 rejection, quota throttling, and factory instantiation.
"""

import pytest
from app.adapters.base import CricketApiAdapter
from app.adapters.factory import get_cricket_adapter
from app.adapters.mock_adapter import MockCricketApiAdapter
from app.adapters.cricketdata_adapter import CricketDataOrgAdapter
from app.adapters.cricketliveapi_adapter import CricketLiveApiAdapter
from app.adapters.cricsheet_adapter import CricsheetFeedAdapter


def test_adapter_factory():
    """Verify factory returns appropriate adapter instances."""
    a_mock = get_cricket_adapter("mock")
    assert isinstance(a_mock, MockCricketApiAdapter)
    assert a_mock.provider_name == "mock"

    a_cricdata = get_cricket_adapter("cricketdata.org", api_key="dummy_key")
    assert isinstance(a_cricdata, CricketDataOrgAdapter)
    assert a_cricdata.provider_name == "cricketdata.org"

    a_live = get_cricket_adapter("cricketliveapi", api_key="dummy_key")
    assert isinstance(a_live, CricketLiveApiAdapter)
    assert a_live.provider_name == "cricketliveapi.com"

    a_cricsheet = get_cricket_adapter("cricsheet")
    assert isinstance(a_cricsheet, CricsheetFeedAdapter)
    assert a_cricsheet.provider_name == "cricsheet.org"

    with pytest.raises(ValueError, match="Unsupported Cricket API provider"):
        get_cricket_adapter("unknown_provider")


def test_mock_adapter_t20_validation():
    """Verify mock adapter accurately validates T20 and rejects non-T20 formats."""
    adapter = MockCricketApiAdapter()

    # Valid T20
    is_t20, reason = adapter.validate_t20_format({"matchType": "t20", "name": "IPL Match"})
    assert is_t20 is True
    assert "Verified T20" in reason

    is_t20_i, _ = adapter.validate_t20_format({"matchType": "t20i", "name": "India vs Aus"})
    assert is_t20_i is True

    # Reject ODI
    is_odi, reason_odi = adapter.validate_t20_format({"matchType": "odi", "name": "IND vs AUS ODI"})
    assert is_odi is False
    assert "Non-T20" in reason_odi

    # Reject Rain-shortened match (18 overs, but officially an ODI!)
    is_curtailed, reason_curtailed = adapter.validate_t20_format({
        "matchType": "odi",
        "name": "ENG vs NZ 18 overs per side",
    })
    assert is_curtailed is False
    assert "Non-T20" in reason_curtailed

    # Reject First-Class / Ranji Trophy
    is_ranji, reason_ranji = adapter.validate_t20_format({
        "matchType": "first-class",
        "name": "Mumbai vs Karnataka Ranji Trophy",
    })
    assert is_ranji is False
    assert "Non-T20" in reason_ranji

    # Reject missing format metadata
    is_empty, reason_empty = adapter.validate_t20_format({})
    assert is_empty is False
    assert "Missing" in reason_empty


def test_cricketdata_adapter_validation_and_quota():
    """Verify CricketDataOrg adapter format validation and quota protection."""
    adapter = CricketDataOrgAdapter(api_key="dummy_test_key")

    assert adapter.validate_t20_format({"matchType": "t20"})[0] is True
    assert adapter.validate_t20_format({"matchType": "T20I"})[0] is True
    assert adapter.validate_t20_format({"matchType": "odi"})[0] is False
    assert adapter.validate_t20_format({"matchType": "test"})[0] is False
    assert adapter.validate_t20_format({"matchType": "list a"})[0] is False

    # Test quota limit enforcement
    adapter._daily_calls_count = 100
    with pytest.raises(RuntimeError, match="daily free-tier limit of 100 calls reached"):
        adapter._make_request("currentMatches")


def test_cricketliveapi_free_tier_scorecard_gating():
    """Verify CricketLiveApi adapter blocks scorecard access on free tier with explicit error."""
    adapter = CricketLiveApiAdapter(api_key="test_key", tier="free")
    assert adapter.tier == "free"

    # Scorecard access on free tier MUST raise PermissionError detailing the Starter plan requirement
    with pytest.raises(PermissionError, match="Free Tier does NOT include scorecard data"):
        adapter.fetch_match_details("any_match_id")

    # Commentary requires Pro tier
    assert adapter.fetch_ball_by_ball("any_match_id") is None


def test_cricsheet_adapter_format_validation():
    """Verify Cricsheet adapter recognizes Cricsheet match_type format."""
    adapter = CricsheetFeedAdapter()

    assert adapter.validate_t20_format({"info": {"match_type": "T20"}})[0] is True
    assert adapter.validate_t20_format({"info": {"match_type": "IT20"}})[0] is True
    assert adapter.validate_t20_format({"info": {"match_type": "ODI"}})[0] is False
    assert adapter.validate_t20_format({"info": {"match_type": "MDM"}})[0] is False
