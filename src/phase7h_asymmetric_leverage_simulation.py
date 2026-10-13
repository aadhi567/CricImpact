"""
Phase 7H: Asymmetric Context Leverage Calibration Simulation Module.

Cricket Batter Contribution Model.
ISOLATED RESEARCH MODULE — DOES NOT MODIFY PRODUCTION PIPELINES.

Investigates asymmetric context leverage functions:
    Adjusted P2 = clip(50 + (P2 - 50) * L(P1), 0.1, 99.9)
    Adjusted P3 = clip(50 + (P3 - 50) * L(P1), 0.1, 99.9)
    Overall Contribution = 0.50 * Adjusted P2 + 0.50 * Adjusted P3

P1 is a CONTEXT / LEVERAGE SIGNAL ONLY.
P1 does NOT contribute direct points to the final score.

Candidate Leverage Functions:
    Model A: Symmetric Linear Bounded Baseline
    Model B: Asymmetric Linear (dual slope below and above par)
    Model C: Piecewise Collapse Emphasis
    Model D: Smooth Power-Law Asymmetric
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# Ensure repository root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

from src.phase7g_leverage_validation import REAL_ARCHETYPE_TARGETS


# ==============================================================================
# 1. CANDIDATE LEVERAGE FUNCTIONS
# ==============================================================================

def leverage_model_a_symmetric_linear(p1: Optional[float]) -> Optional[float]:
    """
    Model A: Current Symmetric Linear Bounded Leverage (Baseline Phase 7F/7G).
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
    Model B: Asymmetric Linear Leverage with Dual Slopes.
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


def leverage_model_c_piecewise_collapse(
    p1: Optional[float],
    p40: float = 0.91,
    p60: float = 1.08,
    p75: float = 1.22,
    p90: float = 1.31,
    p100: float = 1.35,
) -> Optional[float]:
    """
    Model C: Piecewise Collapse Emphasis Leverage.
    P1 < 40: mild dampening (0.65 at 0 to p40 at 40).
    40 <= P1 < 60: approximately neutral around 50 (p40 at 40, 1.00 at 50, p60 at 60).
    60 <= P1 < 75: moderate amplification (p60 at 60 to p75 at 75).
    75 <= P1 < 90: strong amplification (p75 at 75 to p90 at 90).
    P1 >= 90: maximum controlled amplification (p90 at 90 to p100 at 100).
    Clipped to [0.65, 1.35].
    Par (P1 = 50.0) -> L = 1.000 exactly.
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


def leverage_model_d_smooth_power(
    p1: Optional[float],
    alpha_low: float = 0.38,
    alpha_high: float = 0.35,
    gamma: float = 0.75,
) -> Optional[float]:
    """
    Model D: Smooth Power-Law Asymmetric Leverage.
    Below par (P1 < 50): linear mild dampening L = 1.0 + alpha_low * (P1 - 50) / 50.
    Above par (P1 >= 50): concave power curve L = 1.0 + alpha_high * ((P1 - 50) / 50)^gamma.
    Clipped to [0.65, 1.35].
    Par (P1 = 50.0) -> L = 1.000 exactly.
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
    "Model A (Symmetric Linear)": leverage_model_a_symmetric_linear,
    "Model B (Asymmetric Linear)": leverage_model_b_asymmetric_linear,
    "Model C (Piecewise Collapse)": leverage_model_c_piecewise_collapse,
    "Model D (Smooth Power-Law)": leverage_model_d_smooth_power,
}


# ==============================================================================
# 2. SCORE ADJUSTMENT & EVALUATION ENGINE
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
    Active Phase 7D Production Model Baseline:
        Score = 0.25 * P1 + 0.35 * P2 + 0.40 * P3
    """
    if is_dnb or p1 is None or p2 is None or p3 is None or pd.isna(p1) or pd.isna(p2) or pd.isna(p3):
        return None
    val = 0.25 * float(p1) + 0.35 * float(p2) + 0.40 * float(p3)
    return round(float(np.clip(val, 0.1, 99.9)), 1)


# ==============================================================================
# 3. CRITICAL ARCHETYPE TEST CASES
# ==============================================================================

CRITICAL_TEST_CASES = [
    {
        "case_id": "CASE-01",
        "name": "Elite Opener",
        "description": "Opening batter facing calm platform (0/0) with elite individual & team execution",
        "p1": 37.3,
        "p2": 95.0,
        "p3": 95.0,
        "expected_behavior": "Excellent score; small context dampening; not unfairly penalized",
    },
    {
        "case_id": "CASE-02",
        "name": "Failed Opener",
        "description": "Opening batter failing cheaply under calm platform",
        "p1": 37.3,
        "p2": 20.0,
        "p3": 20.0,
        "expected_behavior": "Low contribution; low P1 must NOT protect poor batting",
    },
    {
        "case_id": "CASE-03",
        "name": "Normal Batter",
        "description": "Par context entry with high execution",
        "p1": 50.0,
        "p2": 80.0,
        "p3": 80.0,
        "expected_behavior": "L = 1.000 exact; zero leverage distortion; score matches raw 50/50 mean",
    },
    {
        "case_id": "CASE-04",
        "name": "Moderate Collapse Rescue",
        "description": "Batting after moderate top-order wobble (e.g. 35/3, P1 ≈ 70)",
        "p1": 70.0,
        "p2": 85.0,
        "p3": 85.0,
        "expected_behavior": "Higher contextual reward than an equivalent opener",
    },
    {
        "case_id": "CASE-05",
        "name": "Severe Collapse Rescue",
        "description": "Heroic rescue from catastrophic collapse (e.g. 25/4, P1 ≈ 85)",
        "p1": 85.0,
        "p2": 95.0,
        "p3": 95.0,
        "expected_behavior": "Strongest legitimate reward; receives MORE contextual leverage than elite opener",
    },
    {
        "case_id": "CASE-06",
        "name": "Collapse Failure",
        "description": "Batter entering in crisis and failing immediately (scores 2 off 4, out)",
        "p1": 85.0,
        "p2": 20.0,
        "p3": 20.0,
        "expected_behavior": "Strong penalty; zero participation cushion; no points for crisis entry",
    },
    {
        "case_id": "CASE-07",
        "name": "Collapse Passenger",
        "description": "Batter entering in crisis and batting exactly at par (50/50)",
        "p1": 85.0,
        "p2": 50.0,
        "p3": 50.0,
        "expected_behavior": "Score ≈ 50.0; high P1 alone must NEVER create a high score",
    },
    {
        "case_id": "CASE-08",
        "name": "Death-Over Hopeless Chase",
        "description": "Batter entering in overs 18-20 with mathematical RRR blowout (P3-ISSUE-01)",
        "p1": 95.0,
        "p2": 40.0,
        "p3": 5.0,
        "expected_behavior": "Investigate carefully; high leverage amplifies P3 blowout downward; separate reporting",
    },
]


def evaluate_critical_cases(model_func) -> List[Dict[str, Any]]:
    """
    Evaluates the 8 critical archetypes under a given leverage function.
    """
    results = []
    for c in CRITICAL_TEST_CASES:
        p1 = c["p1"]
        p2 = c["p2"]
        p3 = c["p3"]
        cur_score = compute_production_score_25_35_40(p1, p2, p3)
        res = compute_candidate_score(p1, p2, p3, model_func=model_func)
        lev = res["p1_leverage"]
        adj_p2 = res["adjusted_p2"]
        adj_p3 = res["adjusted_p3"]
        cand_score = res["candidate_score"]
        diff = round(cand_score - cur_score, 1)

        results.append({
            "case_id": c["case_id"],
            "name": c["name"],
            "description": c["description"],
            "p1": p1,
            "p2": p2,
            "p3": p3,
            "leverage": lev,
            "adjusted_p2": adj_p2,
            "adjusted_p3": adj_p3,
            "production_score": cur_score,
            "candidate_score": cand_score,
            "score_shift": diff,
            "expected_behavior": c["expected_behavior"],
        })
    return results


def evaluate_equivalent_performance(
    model_func,
    p_perf: float = 88.0,
) -> Dict[str, Any]:
    """
    Compares Elite Opener vs Severe Collapse Rescue with IDENTICAL batting performance.
    P1_opener = 37.3, P1_collapse = 85.0.
    """
    res_opener = compute_candidate_score(37.3, p_perf, p_perf, model_func=model_func)
    prod_opener = compute_production_score_25_35_40(37.3, p_perf, p_perf)
    shift_opener = round(res_opener["candidate_score"] - prod_opener, 1)

    res_collapse = compute_candidate_score(85.0, p_perf, p_perf, model_func=model_func)
    prod_collapse = compute_production_score_25_35_40(85.0, p_perf, p_perf)
    shift_collapse = round(res_collapse["candidate_score"] - prod_collapse, 1)

    diff_shift = round(shift_collapse - shift_opener, 1)
    ratio = round(res_collapse["candidate_score"] / res_opener["candidate_score"], 3)
    lev_ratio = round(res_collapse["p1_leverage"] / res_opener["p1_leverage"], 3)

    return {
        "p_perf": p_perf,
        "opener": {
            "p1": 37.3,
            "leverage": res_opener["p1_leverage"],
            "production_score": prod_opener,
            "candidate_score": res_opener["candidate_score"],
            "shift": shift_opener,
        },
        "collapse_rescue": {
            "p1": 85.0,
            "leverage": res_collapse["p1_leverage"],
            "production_score": prod_collapse,
            "candidate_score": res_collapse["candidate_score"],
            "shift": shift_collapse,
        },
        "shift_difference": diff_shift,
        "score_ratio": ratio,
        "leverage_ratio": lev_ratio,
        "cr_receives_greater_leverage": bool(res_collapse["p1_leverage"] > res_opener["p1_leverage"]),
        "cr_receives_greater_shift": bool(shift_collapse > shift_opener),
    }


# ==============================================================================
# 4. FULL DATASET (19,111 INNINGS) & 48-INNINGS SAMPLE EVALUATION
# ==============================================================================

def evaluate_sample_48_innings(
    df: pd.DataFrame,
    model_func,
) -> Dict[str, Any]:
    """
    Evaluates the 48 real IPL innings sample from Phase 7G under a candidate model.
    """
    records = []
    for mid, ply, arch_id, arch_name, desc in REAL_ARCHETYPE_TARGETS:
        match_rows = df[(df["match_id"] == mid) & (df["player"] == ply)]
        if len(match_rows) == 0:
            continue
        r = match_rows.iloc[0]
        p1 = float(r["score_context"])
        p2 = float(r["score_perf"])
        p3 = float(r["score_state"])
        cur = float(r["contribution_score"])

        res = compute_candidate_score(p1, p2, p3, model_func=model_func)
        prop = res["candidate_score"]
        diff = round(prop - cur, 1)

        records.append({
            "match_id": int(mid),
            "player": str(ply),
            "archetype_id": arch_id,
            "archetype_name": arch_name,
            "p1": round(p1, 1),
            "p2": round(p2, 1),
            "p3": round(p3, 1),
            "leverage": res["p1_leverage"],
            "adjusted_p2": res["adjusted_p2"],
            "adjusted_p3": res["adjusted_p3"],
            "current_production_score": cur,
            "proposed_score": prop,
            "difference": diff,
        })

    df_sample = pd.DataFrame(records)
    arch_summary = {}
    for arch_id, grp in df_sample.groupby("archetype_id"):
        arch_summary[arch_id] = {
            "name": grp["archetype_name"].iloc[0],
            "count": len(grp),
            "avg_p1": round(float(grp["p1"].mean()), 1),
            "avg_leverage": round(float(grp["leverage"].mean()), 3),
            "avg_current": round(float(grp["current_production_score"].mean()), 1),
            "avg_proposed": round(float(grp["proposed_score"].mean()), 1),
            "avg_difference": round(float(grp["difference"].mean()), 1),
        }

    return {
        "innings_count": len(df_sample),
        "archetype_summaries": arch_summary,
        "sample_records": records,
    }


def evaluate_full_dataset(
    csv_path: str = "data/processed/batter_match_contributions.csv",
) -> Dict[str, Any]:
    """
    Executes full 19,111-innings evaluation across all 4 candidate models.
    """
    df = pd.read_csv(csv_path, low_memory=False)
    p2_p3_raw_corr = round(float(df["score_perf"].corr(df["score_state"])), 4)

    # Pre-define archetype masks across 19,111 innings:
    mask_elite_opener = (df["batting_position"].isin([1, 2])) & (df["score_perf"] >= 80) & (df["score_state"] >= 80)
    mask_collapse_rescue = (df["score_context"] >= 65) & (df["score_perf"] >= 80) & (df["score_state"] >= 80)
    mask_severe_collapse_rescue = (df["score_context"] >= 75) & (df["score_perf"] >= 80) & (df["score_state"] >= 80)
    mask_failed_opener = (df["batting_position"].isin([1, 2])) & (df["score_perf"] <= 35) & (df["score_state"] <= 35)
    mask_collapse_failure = (df["score_context"] >= 65) & (df["score_perf"] <= 35) & (df["score_state"] <= 35)
    mask_collapse_passenger = (df["score_context"] >= 65) & (df["score_perf"].between(45, 55)) & (df["score_state"].between(45, 55))
    mask_normal_context = (df["score_context"].between(48, 52))
    mask_death_hopeless = (df["entry_over"] >= 17.0) & (df["innings"] == 2) & (df["required_rr_entry"] >= 15.0)

    model_evaluations = {}

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

        # Rank stability
        top10_cur = df.sort_values(by="contribution_score", ascending=False).head(10).index
        top10_prop = prop_score.sort_values(ascending=False).head(10).index
        top10_overlap = int(len(set(top10_cur).intersection(set(top10_prop))))

        top20_cur = df.sort_values(by="contribution_score", ascending=False).head(20).index
        top20_prop = prop_score.sort_values(ascending=False).head(20).index
        top20_overlap = int(len(set(top20_cur).intersection(set(top20_prop))))

        # Extremes and clipping
        clip_events = int(((adj_p2 <= 0.1) | (adj_p2 >= 99.9) | (adj_p3 <= 0.1) | (adj_p3 >= 99.9)).sum())
        count_low5 = int((prop_score <= 5.0).sum())
        count_high95 = int((prop_score >= 95.0).sum())

        # Archetype metrics
        eo_cur = round(float(df.loc[mask_elite_opener, "contribution_score"].mean()), 2)
        eo_prop = round(float(prop_score[mask_elite_opener].mean()), 2)
        eo_shift = round(float(shift[mask_elite_opener].mean()), 2)

        cr_cur = round(float(df.loc[mask_collapse_rescue, "contribution_score"].mean()), 2)
        cr_prop = round(float(prop_score[mask_collapse_rescue].mean()), 2)
        cr_shift = round(float(shift[mask_collapse_rescue].mean()), 2)

        scr_cur = round(float(df.loc[mask_severe_collapse_rescue, "contribution_score"].mean()), 2)
        scr_prop = round(float(prop_score[mask_severe_collapse_rescue].mean()), 2)
        scr_shift = round(float(shift[mask_severe_collapse_rescue].mean()), 2)

        fo_cur = round(float(df.loc[mask_failed_opener, "contribution_score"].mean()), 2)
        fo_prop = round(float(prop_score[mask_failed_opener].mean()), 2)
        fo_shift = round(float(shift[mask_failed_opener].mean()), 2)

        cf_cur = round(float(df.loc[mask_collapse_failure, "contribution_score"].mean()), 2)
        cf_prop = round(float(prop_score[mask_collapse_failure].mean()), 2)
        cf_shift = round(float(shift[mask_collapse_failure].mean()), 2)

        cp_cur = round(float(df.loc[mask_collapse_passenger, "contribution_score"].mean()), 2)
        cp_prop = round(float(prop_score[mask_collapse_passenger].mean()), 2)
        cp_shift = round(float(shift[mask_collapse_passenger].mean()), 2)

        norm_cur = round(float(df.loc[mask_normal_context, "contribution_score"].mean()), 2)
        norm_prop = round(float(prop_score[mask_normal_context].mean()), 2)
        norm_shift = round(float(shift[mask_normal_context].mean()), 2)

        dh_cur = round(float(df.loc[mask_death_hopeless, "contribution_score"].mean()), 2)
        dh_prop = round(float(prop_score[mask_death_hopeless].mean()), 2)
        dh_shift = round(float(shift[mask_death_hopeless].mean()), 2)
        dh_low5 = int((prop_score[mask_death_hopeless] <= 5.0).sum())

        diff_cr_eo = round(cr_shift - eo_shift, 2)
        ratio_cr_eo = round(cr_prop / eo_prop, 3)

        # 48 innings sample evaluation
        sample_eval = evaluate_sample_48_innings(df, model_fn)

        # Controlled equivalent performance test
        equiv_perf = evaluate_equivalent_performance(model_fn, p_perf=88.0)

        # Critical cases
        crit_cases = evaluate_critical_cases(model_fn)

        model_evaluations[model_name] = {
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
                "top20_overlap": top20_overlap,
            },
            "clipping_and_extremes": {
                "clipping_events_count": clip_events,
                "clipping_events_pct": round(clip_events / len(df) * 100, 2),
                "scores_under_or_equal_5_count": count_low5,
                "scores_under_or_equal_5_pct": round(count_low5 / len(df) * 100, 2),
                "scores_over_or_equal_95_count": count_high95,
                "scores_over_or_equal_95_pct": round(count_high95 / len(df) * 100, 2),
            },
            "archetype_full_dataset": {
                "elite_opener": {
                    "count": int(mask_elite_opener.sum()),
                    "current_mean": eo_cur,
                    "proposed_mean": eo_prop,
                    "score_shift": eo_shift,
                },
                "collapse_rescue": {
                    "count": int(mask_collapse_rescue.sum()),
                    "current_mean": cr_cur,
                    "proposed_mean": cr_prop,
                    "score_shift": cr_shift,
                },
                "severe_collapse_rescue": {
                    "count": int(mask_severe_collapse_rescue.sum()),
                    "current_mean": scr_cur,
                    "proposed_mean": scr_prop,
                    "score_shift": scr_shift,
                },
                "shift_difference_cr_minus_eo": diff_cr_eo,
                "score_ratio_cr_over_eo": ratio_cr_eo,
                "failed_opener": {
                    "count": int(mask_failed_opener.sum()),
                    "current_mean": fo_cur,
                    "proposed_mean": fo_prop,
                    "score_shift": fo_shift,
                },
                "collapse_failure": {
                    "count": int(mask_collapse_failure.sum()),
                    "current_mean": cf_cur,
                    "proposed_mean": cf_prop,
                    "score_shift": cf_shift,
                },
                "collapse_passenger": {
                    "count": int(mask_collapse_passenger.sum()),
                    "current_mean": cp_cur,
                    "proposed_mean": cp_prop,
                    "score_shift": cp_shift,
                },
                "normal_context": {
                    "count": int(mask_normal_context.sum()),
                    "current_mean": norm_cur,
                    "proposed_mean": norm_prop,
                    "score_shift": norm_shift,
                },
                "death_hopeless_chase": {
                    "count": int(mask_death_hopeless.sum()),
                    "current_mean": dh_cur,
                    "proposed_mean": dh_prop,
                    "score_shift": dh_shift,
                    "low5_count": dh_low5,
                    "low5_pct": round(dh_low5 / int(mask_death_hopeless.sum()) * 100, 1),
                },
            },
            "controlled_equivalent_performance": equiv_perf,
            "critical_cases": crit_cases,
            "sample_48_innings": sample_eval,
        }

    return {
        "dataset_size": len(df),
        "raw_p2_p3_correlation": p2_p3_raw_corr,
        "models": model_evaluations,
    }


# ==============================================================================
# 5. ARTIFACT EXPORT
# ==============================================================================

def export_phase7h_artifacts(
    out_dir: str = "models/contribution/phase7",
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Computes full simulation and exports Phase 7H specification and validation JSONs.
    """
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    validation_results = evaluate_full_dataset()

    spec = {
        "phase": "PHASE_7H",
        "title": "Asymmetric Context Leverage Calibration",
        "governance_mode": "ISOLATED_SIMULATION_AUDIT",
        "production_status": "UNTOUCHED (Phase 7D 25/35/40 active in production)",
        "objective": (
            "Investigate asymmetric context leverage curves to ensure genuine collapse rescue "
            "receives greater contextual leverage and score shift than comfortable opening platforms."
        ),
        "evaluated_architecture": {
            "p1_role": "Context / Leverage Signal Only (0 direct points)",
            "p2_formula": "Adjusted_P2 = clip(50.0 + (P2 - 50.0) * L(P1), 0.1, 99.9)",
            "p3_formula": "Adjusted_P3 = clip(50.0 + (P3 - 50.0) * L(P1), 0.1, 99.9)",
            "contribution_score": "0.50 * Adjusted_P2 + 0.50 * Adjusted_P3",
            "par_invariance": "P1 = 50.0 -> L(P1) = 1.000 exactly",
            "bounds": "[0.65, 1.35]",
        },
        "candidate_models": {
            "Model A": {
                "name": "Symmetric Linear Bounded",
                "formula": "clip(1.0 + 0.35 * ((P1 - 50.0) / 50.0), 0.65, 1.35)",
                "slope_low": 0.0070,
                "slope_high": 0.0070,
            },
            "Model B": {
                "name": "Asymmetric Linear",
                "formula": "if P1 < 50: 1.0 + 0.38 * ((P1 - 50) / 50); else: 1.0 + 0.48 * ((P1 - 50) / 50); clip [0.65, 1.35]",
                "slope_low": 0.0076,
                "slope_high": 0.0096,
                "status": "RECOMMENDED_RESEARCH_CANDIDATE",
            },
            "Model C": {
                "name": "Piecewise Collapse Emphasis",
                "breakpoints": {
                    "0": 0.65,
                    "40": 0.91,
                    "50": 1.00,
                    "60": 1.08,
                    "75": 1.22,
                    "90": 1.31,
                    "100": 1.35,
                },
                "status": "ALTERNATIVE_CANDIDATE",
            },
            "Model D": {
                "name": "Smooth Power-Law Asymmetric",
                "formula": "if P1 < 50: 1.0 + 0.38 * ((P1 - 50) / 50); else: 1.0 + 0.35 * (((P1 - 50) / 50) ^ 0.75); clip [0.65, 1.35]",
                "status": "EVALUATED_CANDIDATE",
            },
        },
        "research_targets": {
            "p1_37": "0.90 - 0.92",
            "p1_50": "1.000 exact",
            "p1_65": "1.10 - 1.15",
            "p1_75": "1.18 - 1.23",
            "p1_85": "1.25 - 1.35",
            "p1_95": "1.30 - 1.35",
            "min_leverage": "0.65",
            "max_leverage": "1.35",
        },
        "p3_issue_01_interaction": (
            "Death-over hopeless chases (overs 18-20, RRR >= 15) suffer from raw P3 blowout (< 10.0). "
            "Because P1 is extreme (> 95), leverage amplifies this downward distortion, causing ~20% "
            "of hopeless chase entries to hit the 0.1-5.0 floor. P3-ISSUE-01 must be damped in Phase 7I "
            "before any production deployment."
        ),
    }

    spec_file = out_path / "phase7h_asymmetric_leverage_spec.json"
    with open(spec_file, "w", encoding="utf-8") as f:
        json.dump(spec, f, indent=2)

    val_file = out_path / "phase7h_asymmetric_leverage_validation.json"
    with open(val_file, "w", encoding="utf-8") as f:
        json.dump(validation_results, f, indent=2)

    print(f"Exported Phase 7H specification to {spec_file}")
    print(f"Exported Phase 7H validation results to {val_file}")

    return spec, validation_results


if __name__ == "__main__":
    spec, val = export_phase7h_artifacts()
    print("\nPhase 7H Simulation Complete. Evaluated models across 19,111 innings.")
