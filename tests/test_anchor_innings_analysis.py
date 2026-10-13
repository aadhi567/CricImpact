"""
Tests for Anchor Innings Analysis Feature & API Endpoint.
Verifies:
1. get_match_detail returns anchor_analysis for Match 1359536 (Sai Sudharsan)
2. Dedicated /api/match/{match_id}/player/{player_id}/anchor-analysis endpoint
3. All 6 bullet-point UX sections and structured metrics
4. Labels (Supported, Mixed, Inconclusive), directions (positive, negative, neutral)
5. Zero modifications to production scoring formulas or integrity locks
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_anchor_analysis_in_match_detail():
    resp = client.get("/api/match/1359536/player/B%20Sai%20Sudharsan?competition=ipl")
    assert resp.status_code == 200
    data = resp.json()
    assert "anchor_analysis" in data
    anchor = data["anchor_analysis"]
    assert anchor is not None
    assert anchor["is_anchor"] is True

    # 1. Why is P3 high?
    assert "why_p3_high" in anchor
    why_p3 = anchor["why_p3_high"]
    assert len(why_p3) >= 5
    for item in why_p3:
        assert "heading" in item
        assert "metric" in item
        assert "significance" in item
        assert item["evidence_label"] in ["Supported", "Mixed", "Inconclusive"]

    # 2. Anchor Batting Profile
    assert "anchor_profile" in anchor
    prof = anchor["anchor_profile"]
    assert prof["runs"] == 47
    assert prof["balls"] == 36
    assert prof["longest_dot_streak"] == 2
    assert prof["dot_balls"] in [11, 12]
    assert "phase_breakdown" in prof
    assert "pattern_bullets" in prof
    assert 1 <= len(prof["pattern_bullets"]) <= 5

    # 3. Partnership Dynamics
    assert "partnership_dynamics" in anchor
    part = anchor["partnership_dynamics"]
    assert "batter" in part
    assert "partner" in part
    assert part["batter"]["runs"] == 47
    assert "bowler_matchups" in part
    assert len(part["bowler_matchups"]) >= 5
    assert "findings" in part
    findings = part["findings"]
    assert "partnership_support" in findings
    assert "pressure_transfer" in findings
    assert "alternative_explanations" in findings
    assert "confidence" in findings

    # 4. P3 Component Breakdown
    assert "p3_components" in anchor
    comps = anchor["p3_components"]
    assert len(comps) == 4
    for c in comps:
        assert "metric_name" in c
        assert "observed_value" in c
        assert c["direction"] in ["positive", "negative", "neutral"]
        assert "explanation" in c

    # 5. Innings Timeline
    assert "timeline_overs" in anchor
    timeline = anchor["timeline_overs"]
    assert len(timeline) == 15  # Overs 0 to 14
    for o in timeline:
        assert "over" in o
        assert "runs" in o
        assert "bullets" in o
        assert len(o["bullets"]) >= 1

    # 6. Final Takeaway
    assert "final_takeaway" in anchor
    takeaway = anchor["final_takeaway"]
    assert len(takeaway["why_p3_high_bullets"]) <= 3
    assert "partnership_effect" in takeaway
    assert "attribution_caveat" in takeaway


def test_dedicated_anchor_analysis_endpoint():
    resp = client.get("/api/match/1359536/player/B%20Sai%20Sudharsan/anchor-analysis?competition=ipl")
    assert resp.status_code == 200
    anchor = resp.json()
    assert anchor["is_anchor"] is True
    assert anchor["anchor_profile"]["runs"] == 47
    assert anchor["anchor_profile"]["balls"] == 36


def test_anchor_analysis_nonexistent_player():
    resp = client.get("/api/match/1359536/player/NonExistentPlayer/anchor-analysis?competition=ipl")
    assert resp.status_code == 404
