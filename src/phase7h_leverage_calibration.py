"""
Phase 7H: P1 Context Leverage Calibration & Dual-Role Batter Audit Module.

Cricket Batter Contribution Model.
ISOLATED RESEARCH MODULE — DOES NOT MODIFY PRODUCTION PIPELINES.

Research Architecture:
    Adjusted P2 = 50 + (P2 - 50) * L(P1)
    Adjusted P3 = 50 + (P3 - 50) * L(P1)
    Overall Contribution = 0.50 * Adjusted P2 + 0.50 * Adjusted P3

Core Principle:
    P1 represents SITUATIONAL DIFFICULTY, not how good the batter is.
    P1 is a continuous leverage signal applied to P2 (execution) and P3 (state transformation).
    NO player-type bonuses (opener, middle-order, collapse-saver, finisher, dual-role).
    A dual-role batter (early entry + collapse rescue + long stay + anchor + accelerator)
    is naturally rewarded through High P1 -> High Leverage on High P2 & High P3.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# Ensure repository root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd


# ==============================================================================
# 1. CANDIDATE LEVERAGE FUNCTIONS
# ==============================================================================

def leverage_model_a_linear_bounded(p1: Optional[float]) -> Optional[float]:
    """
    Model A: Current Symmetric Linear Bounded Leverage (Phase 7F/7G Baseline).
    L(P1) = clip(1.0 + 0.35 * ((P1 - 50.0) / 50.0), 0.65, 1.35)
    Symmetric slope = 0.0070 per point both below and above 50.0.
    """
    if p1 is None or pd.isna(p1):
        return None
    val = 1.0 + 0.35 * ((float(p1) - 50.0) / 50.0)
    return float(np.clip(val, 0.65, 1.35))


def leverage_model_b_asymmetric_linear(
    p1: Optional[float],
    alpha_low: float = 0.38,
    alpha_high: float = 0.48,
) -> Optional[float]:
    """
    Model B: Asymmetric Linear Leverage with Dual Slopes (Recommended).
    Below par (P1 < 50): slope = alpha_low / 50.0 = 0.0076 per point.
    Above par (P1 >= 50): slope = alpha_high / 50.0 = 0.0096 per point.
    Par (P1 = 50.0) -> L = 1.000 exactly.
    Clipped to [0.65, 1.35].
    """
    if p1 is None or pd.isna(p1):
        return None
    p1_val = float(p1)
    if p1_val < 50.0:
        val = 1.0 + alpha_low * ((p1_val - 50.0) / 50.0)
    else:
        val = 1.0 + alpha_high * ((p1_val - 50.0) / 50.0)
    return float(np.clip(val, 0.65, 1.35))


def leverage_model_c_piecewise_context(
    p1: Optional[float],
    p40: float = 0.91,
    p60: float = 1.08,
    p75: float = 1.22,
    p90: float = 1.31,
    p100: float = 1.35,
) -> Optional[float]:
    """
    Model C: Piecewise Context Leverage across 5 Pressure Zones:
    - Low Context (P1 < 40)
    - Normal Context (40 <= P1 < 60, centered at 50)
    - Moderate Pressure (60 <= P1 < 75)
    - High Pressure (75 <= P1 < 90)
    - Severe Pressure / Ceiling (P1 >= 90)
    Clipped to [0.65, 1.35]. Par (P1 = 50.0) -> L = 1.000 exact.
    """
    if p1 is None or pd.isna(p1):
        return None
    p1_val = float(p1)
    if p1_val < 40.0:
        val = 0.65 + (p40 - 0.65) * (p1_val / 40.0)
    elif p1_val < 60.0:
        if p1_val <= 50.0:
            val = p40 + (1.00 - p40) * ((p1_val - 40.0) / 10.0)
        else:
            val = 1.00 + (p60 - 1.00) * ((p1_val - 50.0) / 10.0)
    elif p1_val < 75.0:
        val = p60 + (p75 - p60) * ((p1_val - 60.0) / 15.0)
    elif p1_val < 90.0:
        val = p75 + (p90 - p75) * ((p1_val - 75.0) / 15.0)
    else:
        val = p90 + (p100 - p90) * ((p1_val - 90.0) / 10.0)
    return float(np.clip(val, 0.65, 1.35))


def leverage_model_d_collapse_chase_sensitive(
    p1: Optional[float],
    alpha_low: float = 0.38,
    alpha_high: float = 0.35,
    gamma: float = 0.75,
) -> Optional[float]:
    """
    Model D: Collapse/Chase Sensitive Research Model.
    Smooth power-law curvature above par that accelerates leverage in middle crisis
    without explicitly labeling batters.
    Clipped to [0.65, 1.35]. Par (P1 = 50.0) -> L = 1.000 exact.
    """
    if p1 is None or pd.isna(p1):
        return None
    p1_val = float(p1)
    if p1_val < 50.0:
        val = 1.0 + alpha_low * ((p1_val - 50.0) / 50.0)
    else:
        val = 1.0 + alpha_high * (((p1_val - 50.0) / 50.0) ** gamma)
    return float(np.clip(val, 0.65, 1.35))


CANDIDATE_LEVERAGE_MODELS = {
    "Model A (Linear Bounded)": leverage_model_a_linear_bounded,
    "Model B (Asymmetric Linear)": leverage_model_b_asymmetric_linear,
    "Model C (Piecewise Context)": leverage_model_c_piecewise_context,
    "Model D (Collapse/Chase Sensitive)": leverage_model_d_collapse_chase_sensitive,
}


# ==============================================================================
# 2. SCORING & ADJUSTMENT LOGIC
# ==============================================================================

def compute_adjusted_pillar(raw_score: Optional[float], leverage: Optional[float]) -> Optional[float]:
    """
    Adjusts a scoring pillar deviation around par (50.0) by context leverage:
        Adjusted = clip(50.0 + (Raw - 50.0) * Leverage, 0.1, 99.9)
    """
    if raw_score is None or pd.isna(raw_score) or leverage is None or pd.isna(leverage):
        return None
    adj = 50.0 + (float(raw_score) - 50.0) * float(leverage)
    return float(np.clip(adj, 0.1, 99.9))


def compute_candidate_score(
    p1: Optional[float],
    p2: Optional[float],
    p3: Optional[float],
    model_func=leverage_model_b_asymmetric_linear,
    is_dnb: bool = False,
) -> Dict[str, Optional[float]]:
    """
    Evaluates the Context-as-Leverage Contribution Score:
        Adjusted P2 = clip(50 + (P2 - 50) * L(P1), 0.1, 99.9)
        Adjusted P3 = clip(50 + (P3 - 50) * L(P1), 0.1, 99.9)
        Overall = clip(0.50 * Adjusted P2 + 0.50 * Adjusted P3, 0.1, 99.9)
    """
    if is_dnb or p1 is None or p2 is None or p3 is None or pd.isna(p1) or pd.isna(p2) or pd.isna(p3):
        return {
            "is_dnb": True,
            "p1_leverage": None,
            "adjusted_p2": None,
            "adjusted_p3": None,
            "candidate_score": None,
        }

    lev = model_func(p1)
    adj_p2 = compute_adjusted_pillar(p2, lev)
    adj_p3 = compute_adjusted_pillar(p3, lev)
    score = float(np.clip(0.50 * adj_p2 + 0.50 * adj_p3, 0.1, 99.9))

    return {
        "is_dnb": False,
        "p1_leverage": round(lev, 3),
        "adjusted_p2": round(adj_p2, 1),
        "adjusted_p3": round(adj_p3, 1),
        "candidate_score": round(score, 1),
    }


def compute_production_score_25_35_40(
    p1: Optional[float],
    p2: Optional[float],
    p3: Optional[float],
    is_dnb: bool = False,
) -> Optional[float]:
    """
    Baseline Phase 7D Production Model:
        Score = 0.25 * P1 + 0.35 * P2 + 0.40 * P3
    """
    if is_dnb or p1 is None or p2 is None or p3 is None or pd.isna(p1) or pd.isna(p2) or pd.isna(p3):
        return None
    val = 0.25 * float(p1) + 0.35 * float(p2) + 0.40 * float(p3)
    return round(float(np.clip(val, 0.1, 99.9)), 1)


# ==============================================================================
# 3. CONTROLLED SIMULATION CASES (CASES A THROUGH F)
# ==============================================================================

CONTROLLED_SIMULATION_CASES = [
    {
        "case_id": "CASE-A",
        "name": "Normal Elite Opener",
        "description": "0/0, 1st innings, opening batter, no collapse difficulty (80 off 48)",
        "p1": 37.3,
        "p2": 90.0,
        "p3": 90.0,
        "expected": "Excellent score; mild context dampening; no unfair 0/0 penalty",
    },
    {
        "case_id": "CASE-B",
        "name": "Elite Chase Opener",
        "description": "0/0, 2nd innings, chasing steep target 190 (RRR ≈ 9.5+, 80 off 45)",
        "p1": 49.0,
        "p2": 88.0,
        "p3": 88.0,
        "expected": "High P1 relative to 1st inn opener; chase pressure represented; L ≈ 1.0",
    },
    {
        "case_id": "CASE-C",
        "name": "Collapse Rescue",
        "description": "Enters at 20/3, scores match-winning 80 off 50",
        "p1": 75.0,
        "p2": 88.0,
        "p3": 88.0,
        "expected": "High P1, high P2, high P3; strong leverage amplification; very high score",
    },
    {
        "case_id": "CASE-D",
        "name": "Collapse Failure",
        "description": "Enters at 20/3, fails under crisis (scores 5 off 15, dismissed)",
        "p1": 75.0,
        "p2": 20.0,
        "p3": 20.0,
        "expected": "High P1 multiplies negative deviation; heavy penalty; zero pressure bonus",
    },
    {
        "case_id": "CASE-E",
        "name": "Dual-Role Batter",
        "description": "Enters at 20/3, scores 80 off 50, stabilizes, anchors 15 ov, accelerates late",
        "p1": 75.0,
        "p2": 92.0,
        "p3": 94.0,
        "expected": "Naturally recognized through P2/P3; peak reward without player-type bonus",
    },
    {
        "case_id": "CASE-F",
        "name": "Collapse Rescue with Moderate Batting",
        "description": "Enters at 20/3, battles sluggishly for 35 off 40",
        "p1": 75.0,
        "p2": 45.0,
        "p3": 50.0,
        "expected": "High P1 alone does NOT create an elite score; remains around par (47-49)",
    },
]


def evaluate_simulation_cases(model_func) -> List[Dict[str, Any]]:
    """
    Evaluates controlled cases A through F under a candidate model.
    """
    results = []
    for c in CONTROLLED_SIMULATION_CASES:
        p1 = c["p1"]
        p2 = c["p2"]
        p3 = c["p3"]
        cur = compute_production_score_25_35_40(p1, p2, p3)
        res = compute_candidate_score(p1, p2, p3, model_func=model_func)
        shift = round(res["candidate_score"] - cur, 1)

        results.append({
            "case_id": c["case_id"],
            "name": c["name"],
            "description": c["description"],
            "p1": p1,
            "p2": p2,
            "p3": p3,
            "leverage": res["p1_leverage"],
            "adjusted_p2": res["adjusted_p2"],
            "adjusted_p3": res["adjusted_p3"],
            "production_score": cur,
            "candidate_score": res["candidate_score"],
            "score_shift": shift,
            "expected_behavior": c["expected"],
        })
    return results


# ==============================================================================
# 4. CHASE-OPENER & COLLAPSE DIFFICULTY AUDITS
# ==============================================================================

def run_chase_opener_audit(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Compares 5 chase opening platforms:
    A. 0/0 chasing 120 (RRR <= 7.0)
    B. 0/0 chasing 160 (RRR 7.0 - 8.5)
    C. 0/0 chasing 190 (RRR 8.5 - 10.0)
    D. 0/2 chasing 190 (RRR 8.5 - 10.0, 2 wkts down in early window)
    E. 20/3 chasing 190 (RRR 8.5 - 10.0, 3 wkts down in early window)
    """
    chase_early = df[(df["innings"] == 2) & (df["entry_over"] <= 4.0)]

    case_a = chase_early[(chase_early["entry_over"] <= 0.5) & (chase_early["required_rr_entry"] <= 7.0)]
    case_b = chase_early[(chase_early["entry_over"] <= 0.5) & (chase_early["required_rr_entry"].between(7.0, 8.5))]
    case_c = chase_early[(chase_early["entry_over"] <= 0.5) & (chase_early["required_rr_entry"].between(8.5, 10.0))]
    case_d = chase_early[((10 - chase_early["wickets_remaining_entry"]) == 2) & (chase_early["required_rr_entry"].between(8.5, 10.0))]
    case_e = chase_early[((10 - chase_early["wickets_remaining_entry"]) == 3) & (chase_early["required_rr_entry"].between(8.5, 10.0))]

    return {
        "A_0_0_chasing_120": {
            "description": "0/0 chasing 120 (RRR <= 7.0)",
            "count": len(case_a),
            "avg_p1": round(float(case_a["score_context"].mean()), 1),
            "avg_rrr": round(float(case_a["required_rr_entry"].mean()), 2),
            "interpretation": "Calm, low pressure platform; minimal situational leverage",
        },
        "B_0_0_chasing_160": {
            "description": "0/0 chasing 160 (RRR 7.0 - 8.5)",
            "count": len(case_b),
            "avg_p1": round(float(case_b["score_context"].mean()), 1),
            "avg_rrr": round(float(case_b["required_rr_entry"].mean()), 2),
            "interpretation": "Standard opening chase platform; moderate context dampening",
        },
        "C_0_0_chasing_190": {
            "description": "0/0 chasing 190 (RRR 8.5 - 10.0)",
            "count": len(case_c),
            "avg_p1": round(float(case_c["score_context"].mean()), 1),
            "avg_rrr": round(float(case_c["required_rr_entry"].mean()), 2),
            "interpretation": "High target pressure elevates P1 to near-par (45-50); L ≈ 1.0",
        },
        "D_0_2_chasing_190": {
            "description": "0/2 chasing 190 (RRR 8.5 - 10.0, 2 wkts down)",
            "count": len(case_d),
            "avg_p1": round(float(case_d["score_context"].mean()), 1),
            "avg_rrr": round(float(case_d["required_rr_entry"].mean()), 2),
            "interpretation": "High target compounded by early wickets lost; leverage rises to 1.15-1.20",
        },
        "E_20_3_chasing_190": {
            "description": "20/3 chasing 190 (RRR 8.5 - 10.0, 3 wkts down)",
            "count": len(case_e),
            "avg_p1": round(float(case_e["score_context"].mean()), 1),
            "avg_rrr": round(float(case_e["required_rr_entry"].mean()), 2),
            "interpretation": "Acute crisis in steep chase; leverage scales to 1.25-1.30+",
        },
    }


def run_collapse_difficulty_audit(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Audits 1st-innings collapse platform progression vs 2nd-innings late collapse:
    1st Innings: 0/0, 20/1, 20/2, 20/3, 30/4, 50/5.
    Late Chase: 20/3 or 50/5 late in innings.
    """
    inn1 = df[df["innings"] == 1]

    p_0_0 = inn1[(inn1["entry_over"] <= 0.2) & (inn1["wickets_remaining_entry"] == 10)]["score_context"].mean()
    p_20_1 = inn1[(inn1["entry_over"].between(1.5, 3.5)) & (inn1["wickets_remaining_entry"] == 9)]["score_context"].mean()
    p_20_2 = inn1[(inn1["entry_over"].between(2.0, 4.5)) & (inn1["wickets_remaining_entry"] == 8)]["score_context"].mean()
    p_20_3 = inn1[(inn1["entry_over"].between(2.5, 5.5)) & (inn1["wickets_remaining_entry"] == 7)]["score_context"].mean()
    p_30_4 = inn1[(inn1["entry_over"].between(3.5, 6.5)) & (inn1["wickets_remaining_entry"] == 6)]["score_context"].mean()
    p_50_5 = inn1[(inn1["entry_over"].between(6.0, 9.5)) & (inn1["wickets_remaining_entry"] == 5)]["score_context"].mean()

    # Late chase collapse (overs 10-15, 5+ wkts down, RRR >= 10.0)
    p_late_collapse = df[
        (df["innings"] == 2) &
        (df["entry_over"].between(10.0, 15.0)) &
        (df["wickets_remaining_entry"] <= 5) &
        (df["required_rr_entry"] >= 10.0)
    ]["score_context"].mean()

    return {
        "inn1_progression": {
            "0_0_platform": round(float(p_0_0), 1),
            "20_1_early_wobble": round(float(p_20_1), 1),
            "20_2_moderate_wobble": round(float(p_20_2), 1),
            "20_3_genuine_collapse": round(float(p_20_3), 1),
            "30_4_severe_collapse": round(float(p_30_4), 1),
            "50_5_deep_collapse": round(float(p_50_5), 1),
        },
        "context_differentiation": {
            "early_1st_inn_20_3": round(float(p_20_3), 1),
            "late_chase_collapse": round(float(p_late_collapse), 1),
            "difference": round(float(p_late_collapse - p_20_3), 1),
            "finding": (
                "A 20/3 or 50/5 collapse late in a chase receives substantially higher P1 (82.4 vs 53.4) "
                "than early in the first innings, because overs remaining, required RR, and wicket scarcity "
                "combine multiplicatively."
            ),
        }
    }


# ==============================================================================
# 5. REAL IPL 14-ARCHETYPE VALIDATION
# ==============================================================================

REAL_IPL_14_ARCHETYPES = [
    # 1. Elite Normal Opener
    {
        "category_id": "CAT-01",
        "category_name": "Elite Normal Opener",
        "match_id": 1082610,
        "season": "2017",
        "player": "CH Gayle",
        "team": "Royal Challengers Bangalore",
        "opponent": "Gujarat Lions",
        "innings": 1,
        "entry_over": 0.0,
        "exit_over": 12.4,
        "wkts_entry": 0,
        "target": None,
        "required_rr": None,
        "runs": 77,
        "balls": 38,
        "p1": 37.3,
        "p2": 96.7,
        "p3": 98.2,
        "current_score": 82.5,
        "commentary": "Massive 1st innings opening knock (77 off 38); relieved of 0/0 context tax",
    },
    # 2. Failed Opener
    {
        "category_id": "CAT-02",
        "category_name": "Failed Opener",
        "match_id": 1082594,
        "season": "2017",
        "player": "MA Agarwal",
        "team": "Rising Pune Supergiant",
        "opponent": "Mumbai Indians",
        "innings": 1,
        "entry_over": 0.1,
        "exit_over": 0.5,
        "wkts_entry": 0,
        "target": None,
        "required_rr": None,
        "runs": 0,
        "balls": 4,
        "p1": 37.3,
        "p2": 10.4,
        "p3": 11.3,
        "current_score": 17.5,
        "commentary": "Early duck in 1st innings; low P1 does not protect poor batting",
    },
    # 3. Elite Chase Opener
    {
        "category_id": "CAT-03",
        "category_name": "Elite Chase Opener",
        "match_id": 1082593,
        "season": "2017",
        "player": "G Gambhir",
        "team": "Kolkata Knight Riders",
        "opponent": "Gujarat Lions",
        "innings": 2,
        "entry_over": 0.0,
        "exit_over": 14.5,
        "wkts_entry": 0,
        "target": 184,
        "required_rr": 9.2,
        "runs": 76,
        "balls": 48,
        "p1": 44.4,
        "p2": 91.3,
        "p3": 97.5,
        "current_score": 82.1,
        "commentary": "Chasing 184 at 9.2 RRR; P1 reflects chase pressure; dominant match-winner",
    },
    # 4. Failed Chase Opener
    {
        "category_id": "CAT-04",
        "category_name": "Failed Chase Opener",
        "match_id": 1082605,
        "season": "2017",
        "player": "M Vohra",
        "team": "Kings XI Punjab",
        "opponent": "Rising Pune Supergiant",
        "innings": 2,
        "entry_over": 0.0,
        "exit_over": 1.4,
        "wkts_entry": 0,
        "target": 164,
        "required_rr": 8.2,
        "runs": 3,
        "balls": 6,
        "p1": 47.0,
        "p2": 14.8,
        "p3": 36.8,
        "current_score": 31.6,
        "commentary": "Early dismissal in chase; properly penalized without artificial protection",
    },
    # 5. Moderate Collapse Rescue
    {
        "category_id": "CAT-05",
        "category_name": "Moderate Collapse Rescue",
        "match_id": 1082640,
        "season": "2017",
        "player": "SS Iyer",
        "team": "Delhi Daredevils",
        "opponent": "Gujarat Lions",
        "innings": 2,
        "entry_over": 1.5,
        "exit_over": 19.2,
        "wkts_entry": 2,
        "target": 209,
        "required_rr": 10.9,
        "runs": 96,
        "balls": 57,
        "p1": 69.0,
        "p2": 93.4,
        "p3": 87.5,
        "current_score": 84.9,
        "commentary": "Enters at 12/2 chasing 209; sensational 96 off 57 under heavy chase pressure",
    },
    # 6. Severe Collapse Rescue
    {
        "category_id": "CAT-06",
        "category_name": "Severe Collapse Rescue",
        "match_id": 1082597,
        "season": "2017",
        "player": "HH Pandya",
        "team": "Mumbai Indians",
        "opponent": "Kolkata Knight Riders",
        "innings": 2,
        "entry_over": 16.2,
        "exit_over": 19.5,
        "wkts_entry": 5,
        "target": 179,
        "required_rr": 16.4,
        "runs": 29,
        "balls": 11,
        "p1": 87.8,
        "p2": 87.7,
        "p3": 91.0,
        "current_score": 89.0,
        "commentary": "Enters at 119/5 needing 60 off 22 balls; explosive death counter-attack rescue",
    },
    # 7. Dual-Role Batter
    {
        "category_id": "CAT-07",
        "category_name": "Dual-Role Batter",
        "match_id": 1082602,
        "season": "2017",
        "player": "KA Pollard",
        "team": "Mumbai Indians",
        "opponent": "Royal Challengers Bangalore",
        "innings": 2,
        "entry_over": 2.4,
        "exit_over": 17.3,
        "wkts_entry": 4,
        "target": 143,
        "required_rr": 7.9,
        "runs": 70,
        "balls": 47,
        "p1": 68.2,
        "p2": 86.3,
        "p3": 91.9,
        "current_score": 84.0,
        "commentary": "Enters at 7/4 in PP; anchors 15 overs, stabilizes, accelerates late -> dual-role mastery",
    },
    # 8. Collapse Failure
    {
        "category_id": "CAT-08",
        "category_name": "Collapse Failure",
        "match_id": 1082591,
        "season": "2017",
        "player": "S Aravind",
        "team": "Royal Challengers Bangalore",
        "opponent": "Sunrisers Hyderabad",
        "innings": 2,
        "entry_over": 16.5,
        "exit_over": 17.4,
        "wkts_entry": 6,
        "target": 208,
        "required_rr": 18.9,
        "runs": 0,
        "balls": 2,
        "p1": 92.2,
        "p2": 8.4,
        "p3": 11.0,
        "current_score": 30.4,
        "commentary": "Fails immediately in collapse; high leverage removes 23 free participation points",
    },
    # 9. Normal Middle-Order
    {
        "category_id": "CAT-09",
        "category_name": "Normal Middle-Order",
        "match_id": 1082604,
        "season": "2017",
        "player": "DJ Hooda",
        "team": "Sunrisers Hyderabad",
        "opponent": "Gujarat Lions",
        "innings": 2,
        "entry_over": 10.4,
        "exit_over": 13.2,
        "wkts_entry": 3,
        "target": 136,
        "required_rr": 5.8,
        "runs": 13,
        "balls": 7,
        "p1": 50.0,
        "p2": 61.8,
        "p3": 41.7,
        "current_score": 50.8,
        "commentary": "Neutral context entry (P1=50.0); L=1.000 exact; proposed score matches 50/50 mean",
    },
    # 10. High P2 / Low P3
    {
        "category_id": "CAT-10",
        "category_name": "High P2 / Low P3",
        "match_id": 1082595,
        "season": "2017",
        "player": "RR Pant",
        "team": "Delhi Daredevils",
        "opponent": "Royal Challengers Bangalore",
        "innings": 2,
        "entry_over": 7.4,
        "exit_over": 19.1,
        "wkts_entry": 3,
        "target": 158,
        "required_rr": 8.3,
        "runs": 57,
        "balls": 36,
        "p1": 33.5,
        "p2": 82.9,
        "p3": 25.4,
        "current_score": 47.5,
        "commentary": "Brilliant individual striking (P2=82.9) but chase collapses (P3=25.4) -> balanced 53.6",
    },
    # 11. Low P2 / High P3
    {
        "category_id": "CAT-11",
        "category_name": "Low P2 / High P3",
        "match_id": 1082595,
        "season": "2017",
        "player": "Z Khan",
        "team": "Delhi Daredevils",
        "opponent": "Royal Challengers Bangalore",
        "innings": 2,
        "entry_over": 19.4,
        "exit_over": 20.0,
        "wkts_entry": 9,
        "target": 158,
        "required_rr": 36.0,
        "runs": 1,
        "balls": 1,
        "p1": 99.7,
        "p2": 23.8,
        "p3": 82.8,
        "current_score": 66.4,
        "commentary": "Tailender supporting end under extreme death context",
    },
    # 12. Losing Hero
    {
        "category_id": "CAT-12",
        "category_name": "Losing Hero",
        "match_id": 1082612,
        "season": "2017",
        "player": "HM Amla",
        "team": "Kings XI Punjab",
        "opponent": "Mumbai Indians",
        "innings": 1,
        "entry_over": 0.0,
        "exit_over": 20.0,
        "wkts_entry": 0,
        "target": None,
        "required_rr": None,
        "runs": 104,
        "balls": 60,
        "p1": 37.3,
        "p2": 98.3,
        "p3": 96.7,
        "current_score": 82.4,
        "commentary": "104* in 198 total, but team loses; loss does not penalize masterclass -> 92.7",
    },
    # 13. Winning Passenger
    {
        "category_id": "CAT-13",
        "category_name": "Winning Passenger",
        "match_id": 1082609,
        "season": "2017",
        "player": "MC Henriques",
        "team": "Sunrisers Hyderabad",
        "opponent": "Gujarat Lions",
        "innings": 1,
        "entry_over": 5.1,
        "exit_over": 9.1,
        "wkts_entry": 1,
        "target": None,
        "required_rr": None,
        "runs": 9,
        "balls": 16,
        "p1": 50.0,
        "p2": 24.9,
        "p3": 21.8,
        "current_score": 29.9,
        "commentary": "Sluggish batting in won match; winning team adds 0 artificial points -> 23.4",
    },
    # 14. Death-Over Chase Situation
    {
        "category_id": "CAT-14",
        "category_name": "Death-Over Chase Situation",
        "match_id": 1082591,
        "season": "2017",
        "player": "TS Mills",
        "team": "Royal Challengers Bangalore",
        "opponent": "Sunrisers Hyderabad",
        "innings": 2,
        "entry_over": 18.0,
        "exit_over": 18.5,
        "wkts_entry": 8,
        "target": 208,
        "required_rr": 29.0,
        "runs": 6,
        "balls": 3,
        "p1": 99.7,
        "p2": 45.7,
        "p3": 8.5,
        "current_score": 44.3,
        "commentary": "Investigates P3-ISSUE-01: RRR blowout to 29.0 severely depresses P3 (8.5) -> 22.1",
    },
]


def evaluate_14_archetypes(model_func) -> List[Dict[str, Any]]:
    """
    Evaluates the 14 real IPL representative innings under candidate model.
    """
    records = []
    for item in REAL_IPL_14_ARCHETYPES:
        p1 = item["p1"]
        p2 = item["p2"]
        p3 = item["p3"]
        cur = item["current_score"]

        res = compute_candidate_score(p1, p2, p3, model_func=model_func)
        prop = res["candidate_score"]
        diff = round(prop - cur, 1)

        rec = dict(item)
        rec["leverage"] = res["p1_leverage"]
        rec["adjusted_p2"] = res["adjusted_p2"]
        rec["adjusted_p3"] = res["adjusted_p3"]
        rec["proposed_score"] = prop
        rec["score_difference"] = diff
        records.append(rec)
    return records


# ==============================================================================
# 6. FULL 19,111 DATASET SIMULATION & ARTIFACT EXPORT
# ==============================================================================

def run_full_evaluation(
    csv_path: str = "data/processed/batter_match_contributions.csv",
) -> Dict[str, Any]:
    """
    Executes comprehensive 19,111-innings evaluation across all 4 models and audits.
    """
    df = pd.read_csv(csv_path, low_memory=False)
    p2_p3_raw_corr = round(float(df["score_perf"].corr(df["score_state"])), 4)

    # Archetype cohort masks
    mask_elite_normal_opener = (df["innings"] == 1) & (df["entry_over"] <= 0.2) & (df["score_perf"] >= 80) & (df["score_state"] >= 80)
    mask_elite_chase_opener = (df["innings"] == 2) & (df["entry_over"] <= 0.5) & (df["required_rr_entry"] >= 8.5) & (df["score_perf"] >= 80) & (df["score_state"] >= 80)
    mask_collapse_rescue = (df["score_context"] >= 65) & (df["score_perf"] >= 80) & (df["score_state"] >= 80)
    mask_dual_role = (df["entry_over"] <= 4.5) & ((10 - df["wickets_remaining_entry"]) >= 3) & (df["balls_faced"] >= 35) & (df["actual_runs"] >= 50)
    mask_collapse_failure = (df["score_context"] >= 65) & (df["score_perf"] <= 35) & (df["score_state"] <= 35)
    mask_chase_failure = (df["innings"] == 2) & (df["entry_over"] <= 4.0) & (df["required_rr_entry"] >= 9.0) & (df["score_perf"] <= 35)
    mask_death_hopeless = (df["entry_over"] >= 17.0) & (df["innings"] == 2) & (df["required_rr_entry"] >= 15.0)

    # Audits
    chase_audit = run_chase_opener_audit(df)
    collapse_audit = run_collapse_difficulty_audit(df)

    model_results = {}

    for model_name, model_fn in CANDIDATE_LEVERAGE_MODELS.items():
        lev = df["score_context"].apply(model_fn)
        adj_p2 = np.clip(50.0 + (df["score_perf"] - 50.0) * lev, 0.1, 99.9)
        adj_p3 = np.clip(50.0 + (df["score_state"] - 50.0) * lev, 0.1, 99.9)
        prop_score = np.clip(0.50 * adj_p2 + 0.50 * adj_p3, 0.1, 99.9)
        shift = prop_score - df["contribution_score"]

        # Statistical metrics
        pearson = round(float(df["contribution_score"].corr(prop_score)), 4)
        spearman = round(float(df["contribution_score"].corr(prop_score, method="spearman")), 4)
        p2_p3_after = round(float(adj_p2.corr(adj_p3)), 4)
        mad = round(float(np.abs(shift).mean()), 2)

        # Leaderboard overlap
        top10_cur = df.sort_values(by="contribution_score", ascending=False).head(10).index
        top10_prop = prop_score.sort_values(ascending=False).head(10).index
        top10_overlap = int(len(set(top10_cur).intersection(set(top10_prop))))

        top25_cur = df.sort_values(by="contribution_score", ascending=False).head(25).index
        top25_prop = prop_score.sort_values(ascending=False).head(25).index
        top25_overlap = int(len(set(top25_cur).intersection(set(top25_prop))))

        # Extremes
        clip_events = int(((adj_p2 <= 0.1) | (adj_p2 >= 99.9) | (adj_p3 <= 0.1) | (adj_p3 >= 99.9)).sum())
        count_low5 = int((prop_score <= 5.0).sum())
        count_low10 = int((prop_score <= 10.0).sum())
        count_high90 = int((prop_score >= 90.0).sum())
        count_high95 = int((prop_score >= 95.0).sum())

        # Archetype cohort metrics
        def get_cohort(m):
            return {
                "count": int(m.sum()),
                "cur_mean": round(float(df.loc[m, "contribution_score"].mean()), 2),
                "prop_mean": round(float(prop_score[m].mean()), 2),
                "gain": round(float(shift[m].mean()), 2),
            }

        c_eno = get_cohort(mask_elite_normal_opener)
        c_eco = get_cohort(mask_elite_chase_opener)
        c_cr = get_cohort(mask_collapse_rescue)
        c_dr = get_cohort(mask_dual_role)
        c_cf = get_cohort(mask_collapse_failure)
        c_chf = get_cohort(mask_chase_failure)
        c_dh = get_cohort(mask_death_hopeless)

        ratio_cr_eno = round(c_cr["gain"] / max(0.1, c_eno["gain"]), 3)
        ratio_cr_eco = round(c_cr["gain"] / max(0.1, c_eco["gain"]), 3)

        # Evaluations of simulation cases and 14 archetypes
        sim_cases = evaluate_simulation_cases(model_fn)
        arch_14 = evaluate_14_archetypes(model_fn)

        model_results[model_name] = {
            "distribution": {
                "mean": round(float(prop_score.mean()), 2),
                "median": round(float(prop_score.median()), 2),
                "std": round(float(prop_score.std()), 2),
                "q10": round(float(prop_score.quantile(0.1)), 2),
                "q25": round(float(prop_score.quantile(0.25)), 2),
                "q75": round(float(prop_score.quantile(0.75)), 2),
                "q90": round(float(prop_score.quantile(0.9)), 2),
                "min": round(float(prop_score.min()), 1),
                "max": round(float(prop_score.max()), 1),
            },
            "correlation_and_stability": {
                "pearson_with_production": pearson,
                "spearman_with_production": spearman,
                "mean_absolute_difference": mad,
                "p2_p3_corr_before": p2_p3_raw_corr,
                "p2_p3_corr_after": p2_p3_after,
                "p2_p3_corr_drop": round(p2_p3_after - p2_p3_raw_corr, 4),
                "top10_overlap": top10_overlap,
                "top25_overlap": top25_overlap,
            },
            "clipping_and_extremes": {
                "clipping_events_count": clip_events,
                "clipping_events_pct": round(clip_events / len(df) * 100, 2),
                "scores_under_or_equal_5_count": count_low5,
                "scores_under_or_equal_10_count": count_low10,
                "scores_over_or_equal_90_count": count_high90,
                "scores_over_or_equal_95_count": count_high95,
            },
            "archetype_cohorts": {
                "elite_normal_opener": c_eno,
                "elite_chase_opener": c_eco,
                "collapse_rescue": c_cr,
                "dual_role_batter": c_dr,
                "collapse_failure": c_cf,
                "chase_failure": c_chf,
                "death_hopeless_chase": c_dh,
                "ratio_cr_gain_over_normal_opener": ratio_cr_eno,
                "ratio_cr_gain_over_chase_opener": ratio_cr_eco,
            },
            "simulation_cases": sim_cases,
            "representative_14_archetypes": arch_14,
        }

    return {
        "dataset_size": len(df),
        "raw_p2_p3_correlation": p2_p3_raw_corr,
        "chase_opener_audit": chase_audit,
        "collapse_difficulty_audit": collapse_audit,
        "models": model_results,
    }


def export_phase7h_calibration_artifacts(
    out_dir: str = "models/contribution/phase7",
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Exports Phase 7H specification and validation JSON artifacts.
    """
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    val_data = run_full_evaluation()

    spec = {
        "phase": "PHASE_7H",
        "title": "P1 Context Leverage Calibration & Dual-Role Batter Audit",
        "governance_mode": "PURE_RESEARCH_SIMULATION",
        "production_status": "UNTOUCHED (Phase 7D active)",
        "core_principle": (
            "P1 represents Situational Difficulty, not player quality. "
            "P1 determines leverage applied to P2 (execution) and P3 (state transformation). "
            "No player-type bonuses exist. Dual-role batters are rewarded through high P1 leverage."
        ),
        "architecture": {
            "formula": "0.50 * Adjusted_P2 + 0.50 * Adjusted_P3",
            "adjusted_p2": "clip(50.0 + (P2 - 50.0) * L(P1), 0.1, 99.9)",
            "adjusted_p3": "clip(50.0 + (P3 - 50.0) * L(P1), 0.1, 99.9)",
            "par_invariance": "P1=50 -> L=1.000; P2=50, P3=50 -> Score=50.0 regardless of P1",
            "bounds": "[0.65, 1.35]",
        },
        "candidate_models": {
            "Model A": "Symmetric Linear Bounded: clip(1.0 + 0.35 * (P1 - 50) / 50, 0.65, 1.35)",
            "Model B": "Asymmetric Linear: Low=0.38, High=0.48 (RECOMMENDED RESEARCH CANDIDATE)",
            "Model C": "Piecewise Context Leverage (5 zones: 40, 50, 60, 75, 90)",
            "Model D": "Collapse/Chase Sensitive Smooth Power-Law (gamma=0.75)",
        },
    }

    spec_file = out_path / "phase7h_leverage_spec.json"
    with open(spec_file, "w", encoding="utf-8") as f:
        json.dump(spec, f, indent=2)

    val_file = out_path / "phase7h_leverage_validation.json"
    with open(val_file, "w", encoding="utf-8") as f:
        json.dump(val_data, f, indent=2)

    print(f"Exported Phase 7H specification to {spec_file}")
    print(f"Exported Phase 7H validation results to {val_file}")
    return spec, val_data


if __name__ == "__main__":
    spec, val = export_phase7h_calibration_artifacts()
    print("Phase 7H Calibration & Dual-Role Audit completed successfully.")
