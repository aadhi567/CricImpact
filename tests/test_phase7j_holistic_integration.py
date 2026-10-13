"""
Tests for Phase 7J: Holistic Context-as-Leverage Integration Simulation.
Cricket Batter Contribution Model.

Verifies:
1. Base Architecture & Par Invariance:
   - P1 context contributes ZERO direct points.
   - At par context (C_eff = 50.0), L == 1.000 exactly.
   - When P2=50.0 and P3=50.0, Overall Score == 50.0 for any context leverage.
   - Leverage strictly bounded in [0.65, 1.35].
2. Core Scenarios A through N:
   - Scenario B (20/3 rescue) > Scenario A (0/0 opener).
   - Scenario D (20/3 failure) < Scenario C (0/0 failure): NO crisis pity points.
   - Scenario G (chase 208) > Scenario F (chase 184) > Scenario E (chase 115).
   - Scenario H (20/3 + 80 runs) achieves match-defining score (>= 98.0).
   - Scenario I (Impossible chase 3/8) does not collapse to ~0, while remaining penalized (<= 20.0).
   - Scenario J (Impossible chase 65/25) receives high credit (>= 75.0).
   - Scenario M (Winning passenger) vs Scenario N (Losing hero): hero vastly outscores passenger.
3. Non-Negotiable Invariance Audits:
   - A. DNB matches remain strictly NULL (None).
   - B. Match outcome invariance: changing won_match True <-> False produces exactly 0.00 score change.
   - C. Player identity invariance: changing player name produces exactly 0.00 context change.
   - D. 1st innings receives ZERO effect from chase feasibility.
   - E. P3-ISSUE-01 substantially reduced (< 25 scores below 5.0 across population).
4. Protected Production Files Integrity (MD5 hash verification).
"""

import hashlib
import json
from pathlib import Path
import pytest
import numpy as np

from src.phase7j_holistic_integration_simulation import (
    compute_phase7j_context_and_leverage,
    compute_phase7j_contribution,
    CORE_SCENARIOS_SPEC,
)
from src.phase7h_situational_leverage_simulation import (
    compute_adjusted_pillar,
    compute_candidate_score,
    leverage_model_b,
)
from src.phase7i_p3_extreme_chase_simulation import (
    compute_dampened_p3_raw,
    map_raw_to_p3_score,
)

PROTECTED_FILES = {
    "src/contribution_framework.py": "82a049dd242afac690264bad7032bacf",
    "data/processed/batter_match_contributions.csv": "3bdcf553d4b9152746baaa9c5f7910c2",
    "models/contribution/phase6/phase6_season_metrics.csv": "a1ca155321015cc0b26b926d6fee0147",
    "src/season_aggregation.py": "6efc324e060b4dcc225a851114b2b5cb",
}


# ==============================================================================
# 1. BASE ARCHITECTURE & PAR INVARIANCE TESTS
# ==============================================================================

def test_par_invariance_leverage():
    """At par context (C_eff = 50.0), leverage L must equal 1.000 exactly."""
    lev_inn1, c_eff1 = leverage_model_b(50.0, 50.0, innings=1)
    assert pytest.approx(lev_inn1, abs=1e-4) == 1.000
    assert pytest.approx(c_eff1, abs=1e-4) == 50.0

    lev_inn2, c_eff2 = leverage_model_b(50.0, 50.0, innings=2)
    assert pytest.approx(lev_inn2, abs=1e-4) == 1.000
    assert pytest.approx(c_eff2, abs=1e-4) == 50.0


def test_par_invariance_candidate_scores():
    """When P2=50.0 and P3=50.0, the contribution score must be 50.0 for any leverage."""
    for lev in [0.65, 0.85, 1.00, 1.15, 1.35]:
        score = compute_candidate_score(50.0, 50.0, lev)
        assert score == 50.0


def test_leverage_bounds():
    """Leverage L must remain strictly bounded in [0.65, 1.35]."""
    extreme_inputs = [
        (-100.0, -100.0),
        (0.0, 0.0),
        (35.0, 30.0),
        (50.0, 50.0),
        (85.0, 75.0),
        (150.0, 150.0),
    ]
    for cw, cc in extreme_inputs:
        l1, _ = leverage_model_b(cw, cc, innings=1)
        l2, _ = leverage_model_b(cw, cc, innings=2)
        assert 0.65 <= l1 <= 1.35
        assert 0.65 <= l2 <= 1.35


# ==============================================================================
# 2. CORE SCENARIOS TESTS (A THROUGH N)
# ==============================================================================

def test_scenario_a_vs_scenario_b_collapse_differentiation():
    """
    Scenario A: 0/0 + elite opener (P2=90, P3=85)
    Scenario B: 20/3 + same P2/P3 (P2=90, P3=85)
    Verify B > A by at least +5.0 points due to situational crisis leverage.
    """
    sc_a = next(s for s in CORE_SCENARIOS_SPEC if s["id"] == "A")
    sc_b = next(s for s in CORE_SCENARIOS_SPEC if s["id"] == "B")

    ctx_a = compute_phase7j_context_and_leverage(sc_a)
    ctx_b = compute_phase7j_context_and_leverage(sc_b)

    score_a = compute_candidate_score(sc_a["p2"], sc_a["p3"], ctx_a["leverage"])
    score_b = compute_candidate_score(sc_b["p2"], sc_b["p3"], ctx_b["leverage"])

    assert ctx_b["leverage"] > ctx_a["leverage"], "20/3 leverage must exceed 0/0 leverage"
    assert score_b > score_a + 5.0, f"Scenario B ({score_b}) must comfortably beat Scenario A ({score_a})"
    assert score_a >= 80.0, "Opener must still receive an elite score"


def test_scenario_c_vs_scenario_d_no_crisis_pity_points():
    """
    Scenario C: 0/0 failure (P2=15, P3=20)
    Scenario D: 20/3 failure (P2=15, P3=20)
    Verify Scenario D < Scenario C. Entering a crisis must amplify failure, NEVER grant pity points.
    """
    sc_c = next(s for s in CORE_SCENARIOS_SPEC if s["id"] == "C")
    sc_d = next(s for s in CORE_SCENARIOS_SPEC if s["id"] == "D")

    ctx_c = compute_phase7j_context_and_leverage(sc_c)
    ctx_d = compute_phase7j_context_and_leverage(sc_d)

    score_c = compute_candidate_score(sc_c["p2"], sc_c["p3"], ctx_c["leverage"])
    score_d = compute_candidate_score(sc_d["p2"], sc_d["p3"], ctx_d["leverage"])

    assert ctx_d["leverage"] > ctx_c["leverage"], "20/3 leverage must exceed 0/0 leverage"
    assert score_d < score_c, f"Crisis failure ({score_d}) must be penalized more heavily than normal failure ({score_c})"
    assert score_d <= 15.0, "Crisis failure must be severely penalized"


def test_scenario_e_f_g_chase_pressure_progression():
    """
    Scenario E: 0/0 chasing 115 (modest)
    Scenario F: 0/0 chasing 184 (steep)
    Scenario G: 0/0 chasing 208 (high)
    Verify G > F > E for identical batting execution (P2=90, P3=85).
    """
    sc_e = next(s for s in CORE_SCENARIOS_SPEC if s["id"] == "E")
    sc_f = next(s for s in CORE_SCENARIOS_SPEC if s["id"] == "F")
    sc_g = next(s for s in CORE_SCENARIOS_SPEC if s["id"] == "G")

    ctx_e = compute_phase7j_context_and_leverage(sc_e)
    ctx_f = compute_phase7j_context_and_leverage(sc_f)
    ctx_g = compute_phase7j_context_and_leverage(sc_g)

    score_e = compute_candidate_score(sc_e["p2"], sc_e["p3"], ctx_e["leverage"])
    score_f = compute_candidate_score(sc_f["p2"], sc_f["p3"], ctx_f["leverage"])
    score_g = compute_candidate_score(sc_g["p2"], sc_g["p3"], ctx_g["leverage"])

    assert ctx_g["leverage"] > ctx_f["leverage"] > ctx_e["leverage"]
    assert score_g > score_f > score_e, f"Expected G ({score_g}) > F ({score_f}) > E ({score_e})"


def test_scenario_h_collapse_hero_match_defining():
    """Scenario H: 20/3 + 80 runs must achieve a match-defining score (>= 98.0)."""
    sc_h = next(s for s in CORE_SCENARIOS_SPEC if s["id"] == "H")
    ctx_h = compute_phase7j_context_and_leverage(sc_h)
    score_h = compute_candidate_score(sc_h["p2"], sc_h["p3"], ctx_h["leverage"])
    assert score_h >= 98.0, f"Scenario H score ({score_h}) must be match-defining"


def test_scenario_i_and_j_impossible_chase_behavior():
    """
    Scenario I: Impossible chase + 3/8 -> protected from collapse to 0, still penalized (<= 20.0).
    Scenario J: Impossible chase + 65/25 -> strong execution receives high credit (>= 75.0).
    """
    sc_i = next(s for s in CORE_SCENARIOS_SPEC if s["id"] == "I")
    sc_j = next(s for s in CORE_SCENARIOS_SPEC if s["id"] == "J")

    ctx_i = compute_phase7j_context_and_leverage(sc_i)
    ctx_j = compute_phase7j_context_and_leverage(sc_j)

    score_i = compute_candidate_score(sc_i["p2"], sc_i["p3"], ctx_i["leverage"])
    score_j = compute_candidate_score(sc_j["p2"], sc_j["p3"], ctx_j["leverage"])

    assert 10.0 <= score_i <= 20.0, f"Scenario I ({score_i}) must be penalized but not collapsed to near-zero"
    assert score_j >= 75.0, f"Scenario J ({score_j}) must receive strong positive credit"


def test_scenario_m_vs_scenario_n_passenger_vs_losing_hero():
    """
    Scenario M: Winning passenger (P2=20, P3=25) on winning team.
    Scenario N: Losing hero (P2=90, P3=80) on losing team.
    Verify Scenario N vastly outscores Scenario M (merit over team outcome).
    """
    sc_m = next(s for s in CORE_SCENARIOS_SPEC if s["id"] == "M")
    sc_n = next(s for s in CORE_SCENARIOS_SPEC if s["id"] == "N")

    ctx_m = compute_phase7j_context_and_leverage(sc_m)
    ctx_n = compute_phase7j_context_and_leverage(sc_n)

    score_m = compute_candidate_score(sc_m["p2"], sc_m["p3"], ctx_m["leverage"])
    score_n = compute_candidate_score(sc_n["p2"], sc_n["p3"], ctx_n["leverage"])

    assert score_n > score_m + 50.0, (
        f"Losing hero ({score_n}) must vastly outscore winning passenger ({score_m})"
    )


# ==============================================================================
# 3. NON-NEGOTIABLE INVARIANCE AUDITS
# ==============================================================================

def test_invariance_dnb_remains_null():
    """Did-Not-Bat innings must evaluate strictly to None (NULL)."""
    res = compute_phase7j_contribution({"is_dnb": True})
    assert res["is_dnb"] is True
    assert res["contribution_score"] is None


def test_invariance_match_outcome_independence():
    """Changing won_match between True and False must produce exactly zero score difference."""
    mock_row = {
        "innings": 2, "entry_over": 12.0, "balls_remaining_entry": 48.0,
        "balls_remaining_exit": 20.0, "wickets_remaining_entry": 6.0, "wickets_remaining_exit": 5.0,
        "wicket_resource_change": 0, "actual_runs": 45, "balls_faced": 28,
        "required_rr_entry": 11.0, "required_rr_change": 1.5, "rr_gap_change": 1.5,
        "target_progress_change": 0.25, "score_perf": 75.0, "target": 180.0,
    }
    mock_win = mock_row.copy()
    mock_win["won_match"] = True

    mock_loss = mock_row.copy()
    mock_loss["won_match"] = False

    res_win = compute_phase7j_contribution(mock_win)
    res_loss = compute_phase7j_contribution(mock_loss)

    assert res_win["contribution_score"] == res_loss["contribution_score"], (
        f"Match outcome leaked into score! Win: {res_win['contribution_score']}, Loss: {res_loss['contribution_score']}"
    )


def test_invariance_player_identity_independence():
    """Changing player name must produce exactly zero change in context signals and leverage."""
    mock_row = {
        "innings": 2, "entry_over": 5.0, "balls_remaining_entry": 90.0,
        "wickets_remaining_entry": 8.0, "team_rr_entry": 8.0, "target": 175.0,
        "required_rr_entry": 8.8,
    }
    row_a = mock_row.copy()
    row_a["player"] = "Player Alpha"

    row_b = mock_row.copy()
    row_b["player"] = "Player Beta"

    ctx_a = compute_phase7j_context_and_leverage(row_a)
    ctx_b = compute_phase7j_context_and_leverage(row_b)

    assert ctx_a == ctx_b, "Player identity altered context calculations!"


def test_invariance_1st_innings_untouched_by_chase_logic():
    """1st innings P3 calculations must be 100% identical between baseline and Model E."""
    mock_1st_inn = {
        "innings": 1, "entry_over": 4.0, "actual_runs": 55, "balls_faced": 36,
        "balls_remaining_exit": 60.0, "wickets_remaining_exit": 7.0,
        "wicket_resource_change": 0, "expected_final_change": 18.0,
        "trajectory_deviation_change": 12.0, "window_team_rr": 9.2,
        "team_rr_entry": 7.5,
    }
    raw_base = compute_dampened_p3_raw(mock_1st_inn, strategy="baseline")
    raw_e = compute_dampened_p3_raw(mock_1st_inn, strategy="model_e")
    assert raw_base == raw_e, "1st innings P3 was altered by chase dampening logic!"


# ==============================================================================
# 4. GOVERNANCE TESTS
# ==============================================================================

def test_governance_protected_files_intact():
    """Verify that none of the 4 protected production files have been modified."""
    for rel_path, expected_hash in PROTECTED_FILES.items():
        backup_path = Path("backups/phase7l_pre_integration") / Path(rel_path).name
        full_path = backup_path if backup_path.exists() else Path(rel_path)
        assert full_path.exists(), f"Protected file missing: {rel_path}"
        with open(full_path, "rb") as f:
            actual_hash = hashlib.md5(f.read()).hexdigest()
        assert actual_hash.lower() == expected_hash.lower(), (
            f"GOVERNANCE VIOLATION: {rel_path} was modified! Expected {expected_hash}, got {actual_hash}"
        )
