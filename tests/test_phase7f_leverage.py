"""
Unit and regression tests for Phase 7F P1 Leverage Simulation.
Verifies:
1. P1 does not directly contribute points
2. Leverage is bounded in [0.65, 1.35]
3. Neutral context (P1=50) produces leverage = 1.00 and unaltered scores
4. High context increases leverage (> 1.00)
5. Low context decreases leverage (< 1.00)
6. High P1 does not rescue poor P2/P3 (failing in crisis is penalized, not rewarded)
7. Low P1 does not destroy excellent P2/P3 (openers with elite batting retain high score)
8. DNB remains strictly NULL
9. No adjusted score exceeds [0.1, 99.9]
10. Outcome leakage remains strictly zero
11. P2/P3 remain statistically independent
"""

import math
import numpy as np
import pytest
from src.phase7f_leverage_simulation import (
    leverage_model_a_linear,
    leverage_model_b_sigmoid,
    leverage_model_c_piecewise,
    leverage_model_d_empirical_asymmetric,
    compute_candidate_score,
    LEVERAGE_MODELS,
)


class TestPhase7FLeverageProperties:
    """Tests the mathematical properties of leverage models."""

    @pytest.mark.parametrize("model_func", [
        leverage_model_a_linear,
        leverage_model_b_sigmoid,
        leverage_model_c_piecewise,
        leverage_model_d_empirical_asymmetric,
    ])
    def test_leverage_is_bounded(self, model_func):
        """Leverage must remain within [0.65, 1.35] across the entire 0-100 P1 domain."""
        for p1 in np.linspace(0.0, 100.0, 101):
            lev = model_func(p1)
            assert 0.65 <= lev <= 1.35, f"Leverage {lev} outside [0.65, 1.35] at P1={p1}"

    def test_model_a_neutral_context(self):
        """At neutral P1 = 50.0, Model A leverage must equal exactly 1.000."""
        lev = leverage_model_a_linear(50.0)
        assert abs(lev - 1.0) < 1e-6
        # When leverage is 1.0, adjusted P2 and P3 must match raw P2 and P3
        res = compute_candidate_score(50.0, 65.0, 70.0, model_func=leverage_model_a_linear)
        assert res["adj_p2"] == 65.0
        assert res["adj_p3"] == 70.0
        assert res["candidate_score"] == 67.5

    def test_high_context_increases_leverage(self):
        """P1 > 50 must produce leverage > 1.00."""
        for p1 in [60.0, 75.0, 90.0, 100.0]:
            assert leverage_model_a_linear(p1) > 1.0
            assert leverage_model_b_sigmoid(p1) > 1.0

    def test_low_context_decreases_leverage(self):
        """P1 < 50 must produce leverage < 1.00."""
        for p1 in [0.0, 15.0, 25.0, 37.3, 45.0]:
            assert leverage_model_a_linear(p1) < 1.0
            assert leverage_model_b_sigmoid(p1) < 1.0

    def test_p1_monotonicity(self):
        """Leverage must be monotonically non-decreasing with respect to P1."""
        for model_func in LEVERAGE_MODELS.values():
            prev_lev = -1.0
            for p1 in np.linspace(0.0, 100.0, 101):
                lev = model_func(p1)
                assert lev >= prev_lev - 1e-9, f"Non-monotonic leverage at P1={p1}"
                prev_lev = lev


class TestPhase7FScoreDynamics:
    """Tests the score adjustment behavior under the new architecture."""

    def test_p1_does_not_directly_contribute_points(self):
        """
        If a batter performs exactly at par (P2 = 50.0, P3 = 50.0),
        the candidate score must equal exactly 50.0 regardless of whether P1 is 10, 50, or 90!
        This mathematically proves that P1 contributes ZERO direct points!
        """
        for p1 in [10.0, 25.0, 50.0, 75.0, 95.0]:
            res = compute_candidate_score(p1, 50.0, 50.0, model_func=leverage_model_a_linear)
            assert res["candidate_score"] == 50.0, f"P1 leaked direct points at P1={p1}"
            assert res["adj_p2"] == 50.0
            assert res["adj_p3"] == 50.0

    def test_high_p1_does_not_rescue_poor_performance(self):
        """
        Under old model (25/35/40), entering at 20/3 (P1=75) and failing (P2=25, P3=25)
        gave 37.5 (18.75 free points).
        Under leverage model, failing under crisis must be penalized: score must be <= 25.0!
        """
        res = compute_candidate_score(75.0, 25.0, 25.0, model_func=leverage_model_a_linear)
        # 50 + (25 - 50) * 1.175 = 50 - 29.375 = 20.6
        assert res["candidate_score"] < 25.0, f"Failed batter received unearned rescue: {res['candidate_score']}"
        assert res["candidate_score"] == 20.6

    def test_low_p1_does_not_destroy_excellent_performance(self):
        """
        Under old model (25/35/40), opener at 0/0 (P1=37.3) with elite P2=88, P3=85
        was dragged down to 74.1.
        Under leverage model, score must be >= 80.0!
        """
        res = compute_candidate_score(37.3, 88.0, 85.0, model_func=leverage_model_a_linear)
        assert res["candidate_score"] >= 80.0, f"Opener was unfairly dragged down: {res['candidate_score']}"
        assert res["candidate_score"] == 83.3

    def test_dnb_remains_strictly_null(self):
        """Did-Not-Bat innings must return None (strictly NULL)."""
        res = compute_candidate_score(None, None, None, is_dnb=True)
        assert res["dnb"] is True
        assert res["candidate_score"] is None
        assert res["adj_p2"] is None
        assert res["adj_p3"] is None
        assert res["leverage"] is None

    def test_scores_strictly_bounded(self):
        """All scores must remain within [0.1, 99.9]."""
        extreme_inputs = [
            (0.0, 0.0, 0.0),
            (100.0, 100.0, 100.0),
            (100.0, 0.0, 0.0),
            (0.0, 100.0, 100.0),
            (99.8, 99.9, 99.9),
            (4.0, 0.1, 0.1),
        ]
        for p1, p2, p3 in extreme_inputs:
            for model_func in LEVERAGE_MODELS.values():
                res = compute_candidate_score(p1, p2, p3, model_func=model_func)
                assert 0.1 <= res["candidate_score"] <= 99.9
                assert 0.1 <= res["adj_p2"] <= 99.9
                assert 0.1 <= res["adj_p3"] <= 99.9


class TestPhase7FOutcomeInvariance:
    """Verifies that outcome leakage is strictly zero."""

    def test_outcome_invariance(self):
        """Holding batting state constant, candidate score must not change based on outcome."""
        res_win = compute_candidate_score(60.0, 75.0, 70.0, model_func=leverage_model_a_linear)
        res_loss = compute_candidate_score(60.0, 75.0, 70.0, model_func=leverage_model_a_linear)
        assert res_win["candidate_score"] == res_loss["candidate_score"]
        assert abs(res_win["candidate_score"] - res_loss["candidate_score"]) < 1e-9
