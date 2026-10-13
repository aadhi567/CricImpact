"""
Phase 7F: P1 Leverage Calibration & P2/P3 Integration Simulation Module.

ISOLATED RESEARCH MODULE — DOES NOT MODIFY PRODUCTION PIPELINES.
Investigates the architectural shift from direct P1 point contribution:
  Old (Phase 7D): 0.25 * P1 + 0.35 * P2 + 0.40 * P3
To P1 as a Context / Difficulty / Leverage Signal:
  P1 = Context / Leverage Signal L(P1)
  Adjusted P2 = 50 + (P2 - 50) * L(P1)
  Adjusted P3 = 50 + (P3 - 50) * L(P1)
  Overall Contribution = 0.50 * Adjusted P2 + 0.50 * Adjusted P3
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd

# Ensure repository root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# -------------------------------------------------------------
# 1. Candidate Leverage Functions
# -------------------------------------------------------------

def leverage_model_a_linear(p1: float, p1_baseline: float = 50.0, alpha: float = 0.35) -> float:
    """
    Model A: Linear Bounded Leverage.
    L(P1) = 1.0 + alpha * (P1 - P1_0) / 50.0, clipped to [0.65, 1.35].
    """
    if p1 is None or pd.isna(p1):
        return 1.0
    lev = 1.0 + alpha * (float(p1) - p1_baseline) / 50.0
    return float(np.clip(lev, 0.65, 1.35))


def leverage_model_b_sigmoid(p1: float, p1_baseline: float = 50.0, k: float = 0.06) -> float:
    """
    Model B: Soft Sigmoid (Logistic) Leverage.
    L(P1) = 0.65 + 0.70 / (1 + exp(-k * (P1 - P1_0))), smooth S-curve in [0.65, 1.35].
    """
    if p1 is None or pd.isna(p1):
        return 1.0
    diff = float(p1) - p1_baseline
    sigmoid = 1.0 / (1.0 + np.exp(-k * diff))
    lev = 0.65 + 0.70 * sigmoid
    return float(np.clip(lev, 0.65, 1.35))


def leverage_model_c_piecewise(p1: float, deadband_low: float = 42.0, deadband_high: float = 58.0) -> float:
    """
    Model C: Piecewise Deadband Leverage.
    Neutral zone [42, 58] where L = 1.00; scales out to [0.65, 1.35] beyond.
    """
    if p1 is None or pd.isna(p1):
        return 1.0
    val = float(p1)
    if deadband_low <= val <= deadband_high:
        return 1.0
    elif val > deadband_high:
        lev = 1.0 + 0.35 * (val - deadband_high) / (100.0 - deadband_high)
        return float(np.clip(lev, 1.0, 1.35))
    else:
        lev = 1.0 - 0.35 * (deadband_low - val) / deadband_low
        return float(np.clip(lev, 0.65, 1.0))


def leverage_model_d_empirical_asymmetric(p1: float, p1_anchor: float = 45.0) -> float:
    """
    Model D: Empirically Calibrated Asymmetric Leverage.
    Anchored around empirical mean (45.0).
    High crisis scales up to 1.35 with power 0.85; low difficulty tapers gently down to 0.70.
    """
    if p1 is None or pd.isna(p1):
        return 1.0
    val = float(p1)
    if val >= p1_anchor:
        norm = (val - p1_anchor) / (100.0 - p1_anchor)
        lev = 1.0 + 0.35 * (norm ** 0.85)
        return float(np.clip(lev, 1.0, 1.35))
    else:
        norm = (p1_anchor - val) / p1_anchor
        lev = 1.0 - 0.30 * norm
        return float(np.clip(lev, 0.70, 1.0))


LEVERAGE_MODELS = {
    "Model A (Linear Bounded)": leverage_model_a_linear,
    "Model B (Soft Sigmoid)": leverage_model_b_sigmoid,
    "Model C (Piecewise Deadband)": leverage_model_c_piecewise,
    "Model D (Empirical Asymmetric)": leverage_model_d_empirical_asymmetric,
}


# -------------------------------------------------------------
# 2. Score Adjustment Logic
# -------------------------------------------------------------

def compute_candidate_score(
    p1: Optional[float],
    p2: Optional[float],
    p3: Optional[float],
    model_func=leverage_model_a_linear,
    is_dnb: bool = False,
) -> Dict[str, Any]:
    """
    Computes Phase 7F candidate score:
      Adjusted P2 = 50 + (P2 - 50) * Leverage
      Adjusted P3 = 50 + (P3 - 50) * Leverage
      Overall = 0.50 * Adjusted P2 + 0.50 * Adjusted P3
    """
    if is_dnb or p2 is None or p3 is None or pd.isna(p2) or pd.isna(p3):
        return {
            "dnb": True,
            "leverage": None,
            "adj_p2": None,
            "adj_p3": None,
            "candidate_score": None,
        }

    # Compute leverage
    p1_val = float(p1) if (p1 is not None and not pd.isna(p1)) else 50.0
    p2_val = float(p2)
    p3_val = float(p3)

    lev = model_func(p1_val)

    adj_p2 = float(np.clip(50.0 + (p2_val - 50.0) * lev, 0.1, 99.9))
    adj_p3 = float(np.clip(50.0 + (p3_val - 50.0) * lev, 0.1, 99.9))

    cand_score = float(np.clip(0.50 * adj_p2 + 0.50 * adj_p3, 0.1, 99.9))

    return {
        "dnb": False,
        "leverage": round(lev, 3),
        "adj_p2": round(adj_p2, 1),
        "adj_p3": round(adj_p3, 1),
        "candidate_score": round(cand_score, 1),
    }
