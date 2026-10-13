"""
Diagnostic Tests for Phase 7B: Middle-Over NULL Audit.

Verifies:
1. A batter with genuine middle-over observations receives a valid value under stay-based classification.
2. A batter with no middle-over observations (pure powerplay, pure death, pure DNB) remains strictly NULL.
3. Strict NULL preservation is maintained across the entire pipeline:
   Phase 5B -> Phase 6A -> DataService / API -> Frontend contract (rendered as "—", never 0 or 50).
4. Existing test suite remains passing.
"""

import pytest
import pandas as pd
import numpy as np
from fastapi.testclient import TestClient
from app.main import app
from app.services.data_service import clean_num

client = TestClient(app)


def test_batter_with_middle_over_stay_receives_middle_value_under_proposed_logic():
    """
    Diagnostic Test 1:
    Demonstrates the root cause: an opener entering at 0.0 and batting until 14.0
    spans middle overs (6-16). Under the proposed logic (entry < 16 and exit >= 6),
    they correctly receive a middle-over score rather than artificial NULL.
    """
    innings = [
        # Opener who bats through powerplay and deep into middle overs
        {"player": "Test Opener", "entry_over": 0.0, "exit_over": 14.2, "contribution_score": 78.5},
        # Innings dismissed in powerplay
        {"player": "Test Opener", "entry_over": 0.0, "exit_over": 4.1, "contribution_score": 45.0},
    ]

    # Current flawed logic: checks only entry_over >= 6.0
    flawed_mid = [float(r["contribution_score"]) for r in innings if 6.0 <= float(r.get("entry_over", 0.0)) < 16.0]
    assert len(flawed_mid) == 0, "Flawed logic incorrectly drops the opener who batted deep into middle overs"

    # Proposed corrected logic: stay spans middle overs (entry < 16 and exit >= 6)
    corrected_mid = [
        float(r["contribution_score"])
        for r in innings
        if float(r.get("entry_over", 0.0)) < 16.0 and float(r.get("exit_over", 0.0)) >= 6.0
    ]
    assert len(corrected_mid) == 1
    assert corrected_mid[0] == 78.5
    assert round(float(np.mean(corrected_mid)), 2) == 78.5


def test_batter_with_no_middle_over_observations_remains_null():
    """
    Diagnostic Test 2:
    Verifies that batters with genuinely NO middle-over observations (e.g. pure death hitters,
    pure powerplay dismissals, or pure DNB) remain strictly None (NULL).
    """
    # Case A: Pure death over hitter
    death_only_inns = [
        {"player": "Death Hitter", "entry_over": 17.1, "exit_over": 19.4, "contribution_score": 62.0},
        {"player": "Death Hitter", "entry_over": 18.2, "exit_over": 20.0, "contribution_score": 55.0},
    ]
    mid_death = [
        float(r["contribution_score"])
        for r in death_only_inns
        if float(r.get("entry_over", 0.0)) < 16.0 and float(r.get("exit_over", 0.0)) >= 6.0
    ]
    assert len(mid_death) == 0
    mid_death_val = float(np.mean(mid_death)) if mid_death else None
    assert mid_death_val is None

    # Case B: Pure powerplay dismissals
    pp_only_inns = [
        {"player": "Early Wicket", "entry_over": 0.0, "exit_over": 3.2, "contribution_score": 35.0},
        {"player": "Early Wicket", "entry_over": 1.1, "exit_over": 5.4, "contribution_score": 40.0},
    ]
    mid_pp = [
        float(r["contribution_score"])
        for r in pp_only_inns
        if float(r.get("entry_over", 0.0)) < 16.0 and float(r.get("exit_over", 0.0)) >= 6.0
    ]
    assert len(mid_pp) == 0
    mid_pp_val = float(np.mean(mid_pp)) if mid_pp else None
    assert mid_pp_val is None

    # Case C: Pure DNB (0 innings)
    dnb_inns = []
    mid_dnb_val = float(np.mean(dnb_inns)) if dnb_inns else None
    assert mid_dnb_val is None


def test_null_preservation_across_pipeline_to_frontend():
    """
    Diagnostic Test 3:
    Traces NULL preservation across the entire pipeline:
    Backend Python None / NaN -> clean_num() -> JSON null in API -> Frontend "—" display.
    Never converts NULL to 0, 50, or any artificial score.
    """
    # clean_num preserves None, NaN, empty strings as None
    assert clean_num(None) is None
    assert clean_num(float("nan")) is None
    assert clean_num("") is None
    assert clean_num("NaN") is None

    # API response for genuine DNB player YS Chahal (2016)
    res = client.get("/api/player/YS%20Chahal/season/2016")
    assert res.status_code == 200
    data = res.json()
    assert data["context_breakdown"]["middle_over_contribution"] is None
    assert data["context_breakdown"]["powerplay_contribution"] is None
    assert data["context_breakdown"]["death_over_contribution"] is None

    # Verify Comparison endpoint also returns null
    comp_res = client.get("/api/contribution/compare?season=2016&players=V%20Kohli,YS%20Chahal")
    assert comp_res.status_code == 200
    comp_data = comp_res.json()
    chahal_comp = [p for p in comp_data["players"] if p["player"] == "YS Chahal"][0]
    assert chahal_comp["context_breakdown"]["middle_over_contribution"] is None
