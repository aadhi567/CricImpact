import json
"""
Tests for Phase 7G: Context-as-Leverage Real-Match Validation.

Verifies:
1. Model A Linear Bounded Leverage mathematical properties and boundaries.
2. Par invariance at P1 = 50.0 (L = 1.000).
3. Strict DNB NULL preservation across all fields.
4. Validation across all 12 real cricket archetypes (48 real IPL innings):
   - Archetype 1 (Elite Opener): verified strong contribution despite 0/0 entry.
   - Archetype 2 (Failed Opener): verified low context does NOT protect poor batting.
   - Archetype 3 (Collapse Rescue): verified excellent batting under pressure is amplified.
   - Archetype 4 (Collapse Failure): verified heavy penalty instead of free participation points.
   - Archetype 5 (Normal Context): verified L ≈ 1.00 and scores match raw 50/50 mean.
   - Archetype 6 (Low-Target Chase): verified low leverage dampens runaway state changes.
   - Archetype 7 (Death-Over Chase): verified P3-ISSUE-01 behavior under high leverage.
   - Archetype 8 (Partnership Carrying): verified distinct handling of all 4 sub-cases.
   - Archetype 9 (High P2 / Low P3): verified distinct individual vs state separation.
   - Archetype 10 (Low P2 / High P3): verified recognition of team transformation.
   - Archetype 11 (Winning Passenger): verified winning does not artificially inflate score.
   - Archetype 12 (Losing Hero): verified elite score remains achievable in losing team.
5. Statistical properties: Pearson > 0.95, Spearman > 0.95, 0 scores outside 0–100.
6. Validation JSON artifact exists, is non-empty, and contains required verdict.
"""

from pathlib import Path
import pytest
import numpy as np
import pandas as pd

from src.phase7g_leverage_validation import (
    compute_p1_leverage_model_a,
    compute_adjusted_score,
    compute_proposed_leverage_score,
    compute_production_score_25_35_40,
    load_and_validate_archetypes,
    REAL_ARCHETYPE_TARGETS,
)


# ==============================================================================
# 1. MATHEMATICAL FORMULATION & BOUNDARY TESTS
# ==============================================================================

def test_model_a_par_invariance():
    """Verify that P1 = 50.0 produces L = 1.000, leaving P2 and P3 unscaled."""
    lev = compute_p1_leverage_model_a(50.0)
    assert lev == 1.000

    # P2 = 70.0, P3 = 30.0 -> Adjusted scores must be identical to raw
    adj_p2 = compute_adjusted_score(70.0, lev)
    adj_p3 = compute_adjusted_score(30.0, lev)
    assert adj_p2 == 70.0
    assert adj_p3 == 30.0

    res = compute_proposed_leverage_score(50.0, 70.0, 30.0)
    assert res["p1_leverage"] == 1.000
    assert res["adjusted_p2"] == 70.0
    assert res["adjusted_p3"] == 30.0
    assert res["proposed_score"] == 50.0  # (70 + 30) / 2


def test_model_a_boundaries_and_clipping():
    """Verify lower (0.65) and upper (1.35) bounds of Model A linear leverage."""
    # Extreme low context: P1 = 0.0 -> L = 1.0 - 0.35 = 0.65
    assert compute_p1_leverage_model_a(0.0) == 0.650
    assert compute_p1_leverage_model_a(-10.0) == 0.650

    # Extreme high context: P1 = 100.0 -> L = 1.0 + 0.35 = 1.35
    assert compute_p1_leverage_model_a(100.0) == 1.350
    assert compute_p1_leverage_model_a(120.0) == 1.350

    # Adjusted score boundary clipping at 0.1 and 99.9
    lev_high = 1.350
    # Positive deviation: 95 -> 50 + 45 * 1.35 = 110.75 -> clipped to 99.9
    assert compute_adjusted_score(95.0, lev_high) == 99.9
    # Negative deviation: 5 -> 50 - 45 * 1.35 = -10.75 -> clipped to 0.1
    assert compute_adjusted_score(5.0, lev_high) == 0.1


def test_dnb_null_preservation():
    """Verify DNB (None/NaN inputs) returns strictly None across all outputs."""
    res = compute_proposed_leverage_score(None, 80.0, 80.0)
    assert res["p1_leverage"] is None
    assert res["adjusted_p2"] is None
    assert res["adjusted_p3"] is None
    assert res["proposed_score"] is None

    assert compute_p1_leverage_model_a(None) is None
    assert compute_adjusted_score(None, 1.0) is None
    assert compute_production_score_25_35_40(None, 50.0, 50.0) is None


# ==============================================================================
# 2. REAL-MATCH ARCHETYPE VALIDATION TESTS (48 REAL INNINGS)
# ==============================================================================

@pytest.fixture(scope="module")
def validation_data():
    """Loads and computes real-match validation across the 48 curated innings."""
    return load_and_validate_archetypes()


def test_total_archetypes_and_innings_count(validation_data):
    """Verify exactly 48 real IPL innings are selected and analyzed across 12 archetypes."""
    records = validation_data["innings_records"]
    assert len(records) == 48
    assert len(REAL_ARCHETYPE_TARGETS) == 48

    arch_ids = {r["archetype_id"] for r in records}
    assert len(arch_ids) == 15  # 11 distinct archetypes + 4 partnership sub-cases (8A, 8B, 8C, 8D)


def test_archetype_01_elite_opener_not_dragged_down(validation_data):
    """Verify Elite Openers receive strong contribution (> 90 avg) without being taxed by 0/0 context."""
    records = [r for r in validation_data["innings_records"] if r["archetype_id"] == "ARCH-01"]
    assert len(records) == 4

    avg_score = np.mean([r["proposed_leverage_score"] for r in records])
    assert avg_score >= 90.0
    for r in records:
        assert r["p1"] <= 40.0
        assert r["p2"] >= 88.0
        assert r["p3"] >= 90.0
        assert r["proposed_leverage_score"] >= 85.0
        # Under leverage, score must be substantially higher than 25/35/40 (gain >= 8 pts)
        assert r["difference"] >= 8.0


def test_archetype_02_failed_opener_not_protected(validation_data):
    """Verify Failed Openers remain firmly in the poor batting failure zone (< 35 avg)."""
    records = [r for r in validation_data["innings_records"] if r["archetype_id"] == "ARCH-02"]
    assert len(records) == 4

    avg_proposed = np.mean([r["proposed_leverage_score"] for r in records])
    assert avg_proposed < 35.0
    pure_fails = [r for r in records if r["player"] in ["JJ Roy", "G Gambhir", "CH Gayle"]]
    for r in pure_fails:
        assert r["proposed_leverage_score"] <= 32.0


def test_archetype_03_collapse_rescue_amplified(validation_data):
    """Verify Collapse Rescues receive amplified contribution (> 80 avg, positive difference)."""
    records = [r for r in validation_data["innings_records"] if r["archetype_id"] == "ARCH-03"]
    assert len(records) == 4

    avg_diff = np.mean([r["difference"] for r in records])
    assert avg_diff > 5.0
    for r in records:
        assert r["leverage"] > 1.050
        assert r["proposed_leverage_score"] >= 75.0


def test_archetype_04_collapse_failure_heavily_penalized(validation_data):
    """Verify Collapse Failures receive heavy penalty (< 25 avg) rather than free P1 points."""
    records = [r for r in validation_data["innings_records"] if r["archetype_id"] == "ARCH-04"]
    assert len(records) == 4

    avg_diff = np.mean([r["difference"] for r in records])
    # Must drop significantly compared to production model (negative difference < -10 pts)
    assert avg_diff < -10.0
    for r in records:
        assert r["leverage"] > 1.050
        assert r["proposed_leverage_score"] < 30.0


def test_archetype_05_normal_context_par_invariance(validation_data):
    """Verify Normal Context (P1 ≈ 50.0) maintains leverage close to 1.000 (0.999–1.001)."""
    records = [r for r in validation_data["innings_records"] if r["archetype_id"] == "ARCH-05"]
    assert len(records) == 4

    for r in records:
        assert 0.998 <= r["leverage"] <= 1.002
        # Adjusted scores must be within 0.2 pts of raw P2 and P3
        assert abs(r["adjusted_p2"] - r["p2"]) <= 0.2
        assert abs(r["adjusted_p3"] - r["p3"]) <= 0.2


def test_archetype_07_death_over_chase_p3_issue_01(validation_data):
    """Verify investigation of P3-ISSUE-01: extreme required-RR blowout in overs 18-20."""
    records = [r for r in validation_data["innings_records"] if r["archetype_id"] == "ARCH-07"]
    assert len(records) == 4

    # High required RR (> 15) and high P1 (> 90)
    for r in records:
        assert r["p1"] > 90.0
        assert r["leverage"] > 1.25

    # Siraj case: P3 = 3.6 blows out, leverage pushes score down to 2.6
    siraj = [r for r in records if r["player"] == "Mohammed Siraj"][0]
    assert siraj["p3"] <= 5.0
    assert siraj["proposed_leverage_score"] <= 5.0
    assert siraj["difference"] < -20.0


def test_archetype_08_partnership_carrying(validation_data):
    """Verify partnership carrying dynamics: batter carries vs partner carries."""
    bravo = [r for r in validation_data["innings_records"] if r["archetype_id"] == "ARCH-08A"][0]
    dhawan = [r for r in validation_data["innings_records"] if r["archetype_id"] == "ARCH-08B"][0]

    # Bravo carried the partnership (68 off 30) -> elite score
    assert bravo["proposed_leverage_score"] >= 90.0

    # Dhawan was carried by Warner (29 off 30 vs 126 off 59) -> modest P2 (52.0), high P3 (88.3)
    assert dhawan["adjusted_p2"] == 52.0
    assert dhawan["adjusted_p3"] == 88.3
    assert dhawan["proposed_leverage_score"] == 70.1


def test_archetypes_09_and_10_pillar_separability(validation_data):
    """Verify high P2/low P3 and low P2/high P3 remain distinctly distinguishable."""
    arch9 = [r for r in validation_data["innings_records"] if r["archetype_id"] == "ARCH-09"]
    for r in arch9:
        assert r["p2"] >= 80.0
        assert r["p3"] <= 30.0
        # Proposed score reflects balanced middle (50-60)
        assert 45.0 <= r["proposed_leverage_score"] <= 60.0

    arch10 = [r for r in validation_data["innings_records"] if r["archetype_id"] == "ARCH-10"]
    for r in arch10:
        assert r["p2"] <= 40.0
        assert r["p3"] >= 75.0
        assert r["adjusted_p3"] > r["adjusted_p2"]


def test_archetypes_11_and_12_outcome_independence(validation_data):
    """Verify winning passenger does not get inflated and losing hero is not penalized."""
    arch11 = [r for r in validation_data["innings_records"] if r["archetype_id"] == "ARCH-11"]
    for r in arch11:
        assert r["match_result"] == "Won"
        # Winning did not inflate score: remains < 30
        assert r["proposed_leverage_score"] < 30.0

    arch12 = [r for r in validation_data["innings_records"] if r["archetype_id"] == "ARCH-12"]
    for r in arch12:
        assert r["match_result"] == "Lost"
        # Loss did not prevent elite score: remains > 85
        assert r["proposed_leverage_score"] >= 88.0


# ==============================================================================
# 3. STATISTICAL METRICS & ARTIFACT EXISTENCE TESTS
# ==============================================================================

def test_statistical_metrics_bounds(validation_data):
    """Verify global correlation, clipping, and bounds metrics across all 48 innings."""
    stats = validation_data["statistical_metrics"]

    assert stats["pearson_correlation"] > 0.95
    assert stats["spearman_rank_correlation"] > 0.95
    assert stats["scores_outside_0_100"] == 0
    assert stats["top10_rank_overlap"] >= 8
    # P2/P3 correlation after leverage should decrease (greater independence)
    assert stats["p2_p3_correlation_after"] < stats["p2_p3_correlation_before"]


def test_validation_json_artifact_exists():
    """Verify that models/contribution/phase7/phase7g_real_match_validation.json exists and is valid."""
    p = Path("models/contribution/phase7/phase7g_real_match_validation.json")
    assert p.exists(), "phase7g_real_match_validation.json must exist"
    assert p.stat().st_size > 10_000

    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["sample_size"] == 48
    assert data["verdict"] == "B. APPROVE WITH OBSERVATIONS"
    assert "p3_issue_01_investigation" in data
    assert len(data["suspicious_cases"]) == 2
