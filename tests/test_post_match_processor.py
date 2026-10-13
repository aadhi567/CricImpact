"""
Integration Tests for Post-Match Rating Pipeline.
Verifies:
1. Rejection of non-T20 formats before calculation.
2. Calculation of production contribution scores for completed T20 matches.
3. Strict DNB rule preservation (null, never 0 or 50).
4. Duplicate match processing prevention.
5. Latency under 60-second SLA.
6. FastAPI pipeline endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.adapters.mock_adapter import MockCricketApiAdapter
from app.services.post_match_processor import PostMatchProcessor

client = TestClient(app)


def test_post_match_processor_valid_t20(tmp_path):
    """Verify end-to-end processing of a completed T20 match."""
    registry_file = tmp_path / "test_registry.json"
    adapter = MockCricketApiAdapter()
    processor = PostMatchProcessor(adapter=adapter, registry_path=registry_file)

    res = processor.process_match("mock_t20_ipl_001")

    assert res["status"] == "success"
    assert res["format_valid"] is True
    assert res["format"] == "T20"
    assert res["sla_met_60s"] is True
    assert res["processing_duration_seconds"] < 5.0  # Well within 60s
    assert res["total_batters"] > 0
    assert res["qualified_count"] > 0

    batters = res["batters"]
    
    # Check eligible batters who batted
    sa_yadav = next((b for b in batters if b["player"] == "SA Yadav"), None)
    assert sa_yadav is not None
    assert sa_yadav["runs"] == 62
    assert sa_yadav["balls"] == 34
    assert sa_yadav["is_qualified"] is True
    assert sa_yadav["rank"] is not None
    assert sa_yadav["contribution_score"] is not None
    assert 0.1 <= sa_yadav["contribution_score"] <= 99.9

    # Check Strict DNB Preservation: JJ Bumrah and MS Dhoni did not bat
    bumrah = next((b for b in batters if b["player"] == "JJ Bumrah"), None)
    assert bumrah is not None
    assert bumrah["dnb"] is True
    assert bumrah["contribution_score"] is None  # MUST BE None (null in JSON)
    assert bumrah["raw_contribution"] is None
    assert bumrah["qualification_status"] == "Did Not Bat"

    dhoni = next((b for b in batters if b["player"] == "MS Dhoni"), None)
    assert dhoni is not None
    assert dhoni["dnb"] is True
    assert dhoni["contribution_score"] is None


def test_post_match_processor_duplicate_prevention(tmp_path):
    """Verify duplicate processing is prevented."""
    registry_file = tmp_path / "test_registry.json"
    adapter = MockCricketApiAdapter()
    processor = PostMatchProcessor(adapter=adapter, registry_path=registry_file)

    # First run
    res1 = processor.process_match("mock_t20_ipl_001")
    assert res1["status"] == "success"

    # Second run for same match
    res2 = processor.process_match("mock_t20_ipl_001")
    assert res2["status"] == "already_processed"
    assert "Skipping duplicate calculation" in res2["message"]


def test_post_match_processor_strict_non_t20_rejection(tmp_path):
    """Verify non-T20 matches are rejected before calculation."""
    registry_file = tmp_path / "test_registry.json"
    adapter = MockCricketApiAdapter()
    processor = PostMatchProcessor(adapter=adapter, registry_path=registry_file)

    # 1. Reject standard ODI
    res_odi = processor.process_match("mock_odi_002")
    assert res_odi["status"] == "rejected"
    assert res_odi["format_valid"] is False
    assert "Strict match format restriction violation" in res_odi["reason"]

    # 2. Reject rain-shortened ODI (18 overs per side)
    res_curtailed = processor.process_match("mock_curtailed_odi_003")
    assert res_curtailed["status"] == "rejected"
    assert res_curtailed["format_valid"] is False
    assert "Strict match format restriction violation" in res_curtailed["reason"]

    # 3. Reject Ranji Trophy match
    res_ranji = processor.process_match("mock_ranji_004")
    assert res_ranji["status"] == "rejected"
    assert res_ranji["format_valid"] is False
    assert "Strict match format restriction violation" in res_ranji["reason"]


def test_fastapi_pipeline_endpoints():
    """Verify FastAPI pipeline endpoints via HTTP TestClient."""
    # Process valid T20 match
    res = client.post("/api/pipeline/process-match/mock_t20_ipl_001?provider=mock")
    assert res.status_code == 200
    data = res.json()
    assert data["format_valid"] is True
    assert data["status"] in ("success", "already_processed")

    # Reject non-T20 match (400 Bad Request)
    res_reject = client.post("/api/pipeline/process-match/mock_odi_002?provider=mock")
    assert res_reject.status_code == 400
    assert "Non-T20 format" in res_reject.json()["detail"]

    # Check status endpoint
    res_status = client.get("/api/pipeline/status")
    assert res_status.status_code == 200
    status_data = res_status.json()
    assert status_data["status"] == "ready"
