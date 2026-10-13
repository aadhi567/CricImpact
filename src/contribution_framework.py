"""
Phase 5A: Final Batter Contribution Framework.

Provides the mathematical components, normalization algorithms, outcome leverage
alternatives, and team contribution share attribution methods for evaluating
batter contribution without arbitrary hand-tuned weights.
"""

from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd


# ==============================================================================
# 1. CORE COMPONENT FORMULATIONS
# ==============================================================================

def compute_individual_performance_score(
    run_deviation: float,
    sr_deviation: float,
    opportunity_usage: float = 0.5,
    std_run_dev: float = 14.5,
    std_sr_dev: float = 48.0,
) -> float:
    """
    Standardized Individual Performance Component (S_ind).
    Combines run deviation and strike-rate deviation on a standardized z-scale,
    avoiding arbitrary unit bias between runs and percentage points.
    
    Formula:
        z_run = run_deviation / std_run_dev
        z_sr  = sr_deviation / std_sr_dev
        S_ind = z_run + 0.5 * z_sr * sqrt(min(1.0, opportunity_usage))
    
    The SR deviation is scaled by opportunity usage to prevent 1-ball 600 SR
    bursts from dominating without run volume.
    """
    if pd.isna(run_deviation):
        run_deviation = 0.0
    if pd.isna(sr_deviation):
        sr_deviation = 0.0
    if pd.isna(opportunity_usage) or opportunity_usage <= 0:
        opp_factor = 0.2
    else:
        opp_factor = np.sqrt(min(1.0, float(opportunity_usage)))

    z_run = float(run_deviation) / max(1.0, std_run_dev)
    z_sr = float(sr_deviation) / max(1.0, std_sr_dev)

    return float(z_run + 0.5 * z_sr * opp_factor)


def compute_state_impact_score(
    innings: int,
    expected_final_change: Optional[float] = None,
    required_rr_change: Optional[float] = None,
    runs_required_reduction: Optional[float] = None,
    target_progress_change: Optional[float] = None,
    overs_remaining_entry: float = 10.0,
    std_traj_change: float = 12.0,
    std_rrr_change: float = 2.5,
) -> float:
    """
    Standardized Team-State Impact Component (S_state).
    
    First Innings:
        Measures projected final score improvement (expected_final_change in runs).
        z_state = expected_final_change / std_traj_change
        
    Second Innings (Chase):
        Measures pressure relief via RRR reduction and runs required liquidation.
        Equivalent runs of relief = required_rr_change * overs_remaining_at_entry / 2
        z_state = (required_rr_change / std_rrr_change) * 0.7 + (target_progress_change * 3.0) * 0.3
    """
    if innings == 1:
        if expected_final_change is None or pd.isna(expected_final_change):
            return 0.0
        return float(expected_final_change) / max(1.0, std_traj_change)
    else:
        # Chase state impact
        rrr_chg = 0.0 if (required_rr_change is None or pd.isna(required_rr_change)) else float(required_rr_change)
        t_prog = 0.0 if (target_progress_change is None or pd.isna(target_progress_change)) else float(target_progress_change)
        
        # Standardize RRR change
        z_rrr = rrr_chg / max(0.5, std_rrr_change)
        # Target progress is between 0 and 1 (typically 0.1 to 0.4 for a solid knock)
        z_prog = (t_prog - 0.15) / 0.15  # centered around average knock
        
        return float(0.75 * z_rrr + 0.25 * z_prog)


def compute_resource_tradeoff_score(
    wicket_resource_change: int,
    balls_remaining_exit: int,
    wickets_remaining_exit: int,
    actual_runs: float,
    expected_runs: float,
) -> float:
    """
    Dynamic Resource Trade-Off Component (S_res).
    Investigates scoring benefit achieved relative to resources consumed.
    
    A wicket lost in over 19.5 (balls_remaining=1) has near-zero resource penalty.
    A wicket lost in over 3.2 (balls_remaining=100) with wickets_remaining=6
    has substantial resource penalty.
    
    Cost of Wicket = (balls_remaining_exit / 120.0) * (1.0 / max(1, wickets_remaining_exit)) * 1.5
    """
    if pd.isna(wicket_resource_change) or wicket_resource_change >= 0:
        # Not dismissed or no wicket lost during batter's stay
        # Bonus for preserving wicket: proportional to remaining balls and wickets in hand
        preservation_bonus = 0.15 * (float(wickets_remaining_exit) / 10.0)
        return float(preservation_bonus)
    
    # Batter was dismissed (wicket_resource_change < 0)
    balls_rem = max(0, min(120, int(balls_remaining_exit)))
    wkts_rem = max(1, min(10, int(wickets_remaining_exit)))
    
    # Dynamic wicket cost: high in early/middle overs when wickets are scarce
    wicket_cost = (balls_rem / 120.0) * (10.0 / float(wkts_rem + 2)) * 0.5
    
    # Mitigate penalty if batter scored significantly above expectation
    run_dev = actual_runs - expected_runs
    if run_dev > 15:
        # Explosive innings offsets wicket cost
        offset = min(wicket_cost * 0.7, (run_dev - 15) * 0.02)
        wicket_cost -= offset

    return float(-wicket_cost)


# ==============================================================================
# 2. OUTCOME LEVERAGE ALTERNATIVES
# ==============================================================================

def calculate_outcome_leverage(
    won_match: Optional[bool],
    winning_margin: Optional[float],
    margin_type: Optional[str],
    method: str = "margin_sensitive",
) -> float:
    """
    Evaluates 4 mathematically defensible Outcome Linkage Alternatives (L_outcome).
    
    Alternative 1: 'invariant'
        Outcome weight = 1.0 (pure situational performance, 0 outcome leakage).
        
    Alternative 2: 'binary_step'
        Won = 1.15, Lost = 0.85 (crude step multiplier).
        
    Alternative 3: 'margin_sensitive' (Recommended)
        Close matches (win/loss by <= 10 runs or <= 2 wickets) have leverage close to 1.0.
        Decisive wins slightly amplify contribution (up to 1.15).
        Decisive blowout losses gently dampen without erasing performance (floor at 0.85).
        
    Alternative 4: 'state_outcome_convergence'
        Leverage determined by whether the batter's state trajectory direction aligned
        with final match state.
    """
    if method == "invariant" or won_match is None or pd.isna(won_match):
        return 1.0
    
    won = bool(won_match)
    margin = 10.0 if (winning_margin is None or pd.isna(winning_margin)) else float(winning_margin)
    mtype = "runs" if (margin_type is None or pd.isna(margin_type)) else str(margin_type).lower()
    
    if method == "binary_step":
        return 1.15 if won else 0.85
    
    elif method == "margin_sensitive":
        # Convert wicket margin to rough run equivalence (~10 runs per wicket)
        margin_runs = margin * 10.0 if "wicket" in mtype else margin
        # Closeness factor: 1.0 if margin == 0, tapering as margin grows
        closeness = np.exp(-margin_runs / 35.0)
        
        if won:
            # In decisive wins, win bonus up to +15%
            return float(1.0 + 0.15 * (1.0 - 0.5 * closeness))
        else:
            # In close losses (high closeness), very minimal penalty (-2% to -5%)
            # In blowout losses, maximum penalty is capped at -15%
            penalty = 0.15 * (1.0 - closeness)
            return float(max(0.85, 1.0 - penalty))
            
    elif method == "state_outcome_convergence":
        # Convergent alignment
        return 1.10 if won else 0.90
        
    return 1.0


# ==============================================================================
# 3. RAW CONTRIBUTION COMPOSITE
# ==============================================================================

def compute_raw_contribution(
    row: pd.Series,
    outcome_method: str = "margin_sensitive",
    w_ind: float = 0.45,
    w_state: float = 0.40,
    w_res: float = 0.15,
) -> float:
    """
    Computes Raw Batter Contribution C_raw.
    
    Components:
        S_ind:   Individual standardized performance
        S_state: Team-state transformation
        S_res:   Resource trade-off & preservation
        L_out:   Retrospective outcome leverage
        
    C_raw = (w_ind * S_ind + w_state * S_state + w_res * S_res) * L_out
    """
    s_ind = compute_individual_performance_score(
        run_deviation=row.get("run_deviation", 0.0),
        sr_deviation=row.get("sr_deviation", 0.0),
        opportunity_usage=row.get("opportunity_usage", 0.5),
    )
    
    innings = int(row.get("innings", 1))
    s_state = compute_state_impact_score(
        innings=innings,
        expected_final_change=row.get("expected_final_change"),
        required_rr_change=row.get("required_rr_change"),
        runs_required_reduction=row.get("runs_required_reduction"),
        target_progress_change=row.get("target_progress_change"),
        overs_remaining_entry=row.get("overs_remaining_entry", 10.0),
    )
    
    s_res = compute_resource_tradeoff_score(
        wicket_resource_change=row.get("wicket_resource_change", 0),
        balls_remaining_exit=row.get("balls_remaining_exit", 0),
        wickets_remaining_exit=row.get("wickets_remaining_exit", 5),
        actual_runs=row.get("actual_runs", 0.0),
        expected_runs=row.get("expected_runs", 0.0),
    )
    
    l_out = calculate_outcome_leverage(
        won_match=row.get("won_match"),
        winning_margin=row.get("winning_margin"),
        margin_type=row.get("margin_type"),
        method=outcome_method,
    )
    
    base_contrib = (w_ind * s_ind) + (w_state * s_state) + (w_res * s_res)
    return float(base_contrib * l_out)


# ==============================================================================
# 4. NORMALIZATION ALTERNATIVES (0 TO 100 SCORE)
# ==============================================================================

def normalize_contribution_score(
    raw_score: float,
    method: str = "logistic",
    reference_params: Optional[Dict[str, float]] = None,
) -> float:
    """
    Normalizes Raw Contribution Score into an interpretable [0, 100] scale.
    Par / median performance corresponds to 50.0.
    
    Tested Methods:
    1. 'min_max':
       Linear scaling between min_val and max_val. Sensitive to extreme historical outliers.
    2. 'percentile':
       Empirical CDF rank between 0 and 100.
    3. 'robust':
       Centered by median and scaled by IQR: 50 + 20 * (x - median) / IQR, clipped to [0, 100].
    4. 'logistic' (Recommended):
       Smooth sigmoid mapping centered at par=50:
       Score = 100 / (1 + exp(-k * (raw_score - center)))
       Provides smooth continuous grading without artificial clipping at boundaries.
    """
    params = reference_params or {"center": 0.0, "scale": 0.85, "min_val": -3.5, "max_val": 8.0}
    
    if method == "min_max":
        min_v = params.get("min_val", -3.5)
        max_v = params.get("max_val", 8.0)
        norm = (raw_score - min_v) / max(0.1, (max_v - min_v)) * 100.0
        return float(np.clip(norm, 0.0, 100.0))
        
    elif method == "robust":
        med = params.get("center", 0.0)
        iqr = params.get("scale", 1.2)
        score = 50.0 + 25.0 * ((raw_score - med) / max(0.5, iqr))
        return float(np.clip(score, 0.0, 100.0))
        
    elif method == "logistic":
        center = params.get("center", 0.0)
        k = params.get("scale", 0.85)  # sensitivity slope
        # Sigmoid centered at 50
        score = 100.0 / (1.0 + np.exp(-k * (raw_score - center)))
        return float(np.clip(score, 0.1, 99.9))
        
    elif method == "percentile":
        # Fallback to linear rank approx if empirical distribution not passed
        return float(np.clip(50.0 + 20.0 * raw_score, 0.0, 100.0))
        
    return float(np.clip(raw_score, 0.0, 100.0))


# ==============================================================================
# 5. TEAM CONTRIBUTION SHARE ATTRIBUTION METHODS
# ==============================================================================

def compute_team_contribution_shares(
    raw_scores: List[float],
    method: str = "rectified_positive",
    temperature: float = 1.0,
) -> List[float]:
    """
    Computes Team Contribution Share (%) for all batters in a team innings.
    
    Tested Methods:
    1. 'rectified_positive' (Recommended):
       Credit is attributed exclusively to batters who generated positive value added.
       share_i = max(0, C_i) / sum_j(max(0, C_j)) * 100
       Batters with C_i <= 0 receive 0.0% share.
       If all batters are <= 0, share is distributed uniformly among batters who faced balls.
       
    2. 'softmax':
       share_i = exp(C_i / tau) / sum_j(exp(C_j / tau)) * 100
       Strictly positive shares for all batters, but shifts baseline.
       
    3. 'linear_offset':
       Shifts all scores by the worst batter: C_i' = C_i - min(C).
       share_i = C_i' / sum_j(C_j') * 100
       
    4. 'signed_net':
       share_i = C_i / sum_j(C_j) * 100
       Allows negative percentages and >100% shares for dominant batters.
    """
    n = len(raw_scores)
    if n == 0:
        return []
    if n == 1:
        return [100.0]
        
    arr = np.array(raw_scores, dtype=float)
    
    if method == "rectified_positive":
        rectified = np.maximum(0.0, arr)
        pos_sum = np.sum(rectified)
        if pos_sum > 1e-6:
            shares = (rectified / pos_sum) * 100.0
            return [round(float(s), 2) for s in shares]
        else:
            # All batters had non-positive impact (e.g. collapsed for 49)
            # Equal division among participants
            return [round(100.0 / n, 2)] * n
            
    elif method == "softmax":
        tau = max(0.1, temperature)
        # Shift for numerical stability
        shifted = (arr - np.max(arr)) / tau
        exp_vals = np.exp(shifted)
        shares = (exp_vals / np.sum(exp_vals)) * 100.0
        return [round(float(s), 2) for s in shares]
        
    elif method == "linear_offset":
        min_v = np.min(arr)
        shifted = arr - min_v + 0.1  # small epsilon
        shares = (shifted / np.sum(shifted)) * 100.0
        return [round(float(s), 2) for s in shares]
        
    elif method == "signed_net":
        total_net = np.sum(arr)
        if abs(total_net) > 1e-4:
            shares = (arr / total_net) * 100.0
            return [round(float(s), 2) for s in shares]
        else:
            return [round(100.0 / n, 2)] * n

    return [round(100.0 / n, 2)] * n


# ==============================================================================
# 6. PHASE 5B: FOUR-PILLAR CONTEXTUAL CONTRIBUTION FRAMEWORK
# ==============================================================================

# Validated empirical parameters across standard 20-over batter innings (innings <= 2)
PHASE5B_EMPIRICAL_PARAMS = {
    "pillar1_mean": 0.413,
    "pillar1_std": 1.114,
    "pillar2_mean": -0.068,
    "pillar2_std": 1.029,
    "pillar3_mean": 0.159,
    "pillar3_std": 1.513,
    "pillar4_mean": 0.127,
    "pillar4_std": 0.948,
    "composite_center": -0.138,
    "composite_scale": 1.40,
    "pillar_scale": 1.40,
}


def compute_pillar1_match_context(
    row: Any,
    death_urgency_weight: float = 1.2,
    collapse_pressure_weight: float = 0.45,
    platform_pressure_weight: float = 0.35,
) -> float:
    """
    Pillar 1: Match Context Score (Raw).
    Evaluates the exact situation faced by the batter at entry:
    - Phase: Powerplay (0-6), Middle (6-16), Death (16-20)
    - Wickets remaining, balls remaining, collapse pressure
    - Team RR at entry (1st innings) vs platform pressure
    - Required RR at entry, RR gap (2nd innings)
    - Batting position
    
    Coefficients rationale (Section 8):
    - death_urgency (1.2): Death overs (16-20) demand immediate scoring tempo.
    - collapse_pressure (0.45): Overs per wicket remaining; acute risk when wickets are scarce.
    - platform_pressure (0.35): Pressure to accelerate when current run rate is depressed.
    """
    innings = int(row.get("innings", 1))
    if innings > 2:
        return np.nan  # Super Over: excluded from normal 20-over contribution calculations

    entry_over = float(row.get("entry_over", 0.0))
    balls_rem_entry = float(row.get("balls_remaining_entry", 120))
    wkts_rem_entry = float(row.get("wickets_remaining_entry", 10))
    team_rr_entry = float(row.get("team_rr_entry", 7.5))

    # Early-over window: 0.0 through 4.0 overs
    # Opening batters entering with few balls bowled are NOT judged against
    # an artificial pre-entry run-rate baseline. Context is driven primarily by wickets lost.
    if entry_over <= 4.0:
        death_urgency = 0.0
        # Wicket-driven collapse context: evaluate genuine early wickets lost
        wkts_lost = max(0.0, 10.0 - wkts_rem_entry)
        if wkts_lost == 0:
            collapse_pressure = 0.0  # Normal opening: calm/neutral context
        else:
            # Genuine early collapse pressure scaled by early wickets lost
            collapse_pressure = min(3.5, 0.50 + (wkts_lost - 1) * 0.75)

        if innings == 1:
            # Pre-entry RR must NOT contribute to P1 pressure in early-over window
            rr_pressure = 0.0
            raw = collapse_pressure_weight * collapse_pressure
            return float(raw)
        else:
            req_rr_entry = np.clip(float(row.get("required_rr_entry", 8.5)), 0.0, 24.0)
            # Pre-entry RR gap must NOT contribute to P1 pressure in early-over window
            rr_gap = 0.0
            chase_pressure = (req_rr_entry - 8.5) / 3.0
            raw = chase_pressure + collapse_pressure_weight * collapse_pressure
            return float(raw)

    # Phase leverage: death overs urgency (highest in last 4 overs)
    death_urgency = max(0.0, (entry_over - 15.0) / 4.0) if entry_over >= 15.0 else 0.0
    
    # Wicket scarcity ratio: overs remaining per wicket in hand
    overs_per_wkt = (balls_rem_entry / 6.0) / max(1.0, wkts_rem_entry)
    collapse_pressure = np.clip((overs_per_wkt - 1.5) / 1.0, -1.5, 2.5)

    if innings == 1:
        # Platform pressure
        rr_pressure = np.clip((7.5 - team_rr_entry) / 2.5, -2.0, 2.0)
        raw = death_urgency_weight * death_urgency + collapse_pressure_weight * collapse_pressure + platform_pressure_weight * rr_pressure
        return float(raw)
    else:
        req_rr_entry = np.clip(float(row.get("required_rr_entry", 8.5)), 0.0, 24.0)
        rr_gap = np.clip(float(row.get("rr_gap_entry", 0.0)), -4.0, 8.0)
        chase_pressure = (req_rr_entry - 8.5) / 3.0 + 0.35 * (rr_gap / 2.5)
        raw = chase_pressure + (death_urgency_weight * 0.67) * death_urgency + (collapse_pressure_weight * 0.67) * collapse_pressure
        return float(raw)


def compute_pillar2_batter_performance(row: Any) -> float:
    """
    Pillar 2: Batter Performance Score (Raw).
    Evaluates what the batter actually did:
    - Runs, Balls faced, Strike Rate
    - Boundary percentage / contribution
    - Relative scoring pace vs team RR / required RR
    - Expected Runs & Expected SR (supporting baseline only, strictly <= 15% weight)
    - Dismissal status
    
    CRITICAL: Does NOT automatically penalize short innings.
    Performance quality is evaluated directly without an artificial balls-faced dampener.
    """
    actual_runs = float(row.get("actual_runs", 0))
    balls_faced = float(row.get("balls_faced", 0))
    actual_sr = float(row.get("actual_sr", 0.0))
    bnd_pct = float(row.get("boundary_percentage", 0.0))
    run_dev = float(row.get("run_deviation", 0.0))
    sr_dev = float(row.get("sr_deviation", 0.0))
    innings = int(row.get("innings", 1))
    dismissal_status = str(row.get("dismissal_status", "out")).lower()

    # Standardized volume
    z_runs = (actual_runs - 19.8) / 21.6

    # Direct actual performance quality without balls_faced dampener
    z_sr = np.clip((actual_sr - 125.0) / 50.0, -3.0, 3.5) if balls_faced > 0 else 0.0

    # Relative pace in RPO (SR * 0.06 is RPO)
    batter_rpo = (actual_sr * 0.06) if balls_faced > 0 else 0.0
    if innings == 1:
        team_rr = float(row.get("team_rr_entry", 7.5))
        z_pace = np.clip((batter_rpo - team_rr) / 3.5, -3.0, 3.5) if balls_faced > 0 else 0.0
    else:
        req_rr = min(24.0, float(row.get("required_rr_entry", 8.5)))
        z_pace = np.clip((batter_rpo - req_rr) / 3.5, -3.0, 3.5) if balls_faced > 0 else 0.0

    # Boundary impact (quality of scoring)
    z_bnd = np.clip((bnd_pct - 45.0) / 30.0, -2.5, 2.5) if balls_faced > 0 else 0.0

    # Supporting expected baseline (strictly <= 15% weight, NOT ground truth)
    z_base = 0.7 * (run_dev / 14.5) + 0.3 * np.clip(sr_dev / 48.0, -3.0, 3.0)

    bonus_not_out = 0.25 if (dismissal_status != "out" and balls_faced >= 1) else 0.0

    raw = 0.35 * z_runs + 0.25 * z_sr + 0.20 * z_pace + 0.10 * z_bnd + 0.10 * z_base + bonus_not_out
    return float(raw)


# ==============================================================================
# Phase 7U — P3 Wicket Causality Attribution (Model T)
# ==============================================================================

P3_WICKET_ATTR_INDEPENDENT_GAMMA: float = 0.15
P3_WICKET_ATTR_COLLAPSE_GAMMA: float = 0.50
P3_WICKET_ATTR_STAGNATION_GAMMA: float = 0.70
P3_WICKET_ATTR_CAUSED_GAMMA: float = 1.00


def compute_attributable_team_state_efs(
    row: Any,
    gamma_independent: float = P3_WICKET_ATTR_INDEPENDENT_GAMMA,
    gamma_collapse: float = P3_WICKET_ATTR_COLLAPSE_GAMMA,
    gamma_stagnation: float = P3_WICKET_ATTR_STAGNATION_GAMMA,
    gamma_caused: float = P3_WICKET_ATTR_CAUSED_GAMMA,
) -> Tuple[float, float, str]:
    """
    Phase 7U Model T: Attributable Team-State Impact Decomposition.

    Decomposes team-state change into:
        Delta EFS = Delta R_batter + External Drag
    where:
        Delta R_batter = actual_runs - expected_runs
        External Drag = Delta EFS - Delta R_batter

    Applies causal attribution factor gamma_attr in [0.15, 1.00]:
        Attributable Delta EFS = Delta R_batter + gamma_attr * External Drag

    Classification:
        - Category A: Batter caused pressure (dots% >= 50% & SR ratio < 1.15,
                      or SR < 100 on 10+ balls, or Delta R <= 0) -> gamma = 1.00
        - Category B: Independent partner dismissals (SR ratio >= 1.25 or SR >= 150,
                      dots% < 45%, Delta R > 0) -> gamma = 0.15
        - Category C: Mixed / multi-wicket collapse (partner wkts >= 2) -> gamma = 0.50
        - General Stagnation: partner wickets without qualifying Category B -> gamma = 0.70
        - No partner wickets or positive drag or minimal involvement (<6 balls, <10 runs)
          or golden duck (<=1 ball, 0 runs) -> gamma = 1.00 (Delta EFS unchanged).

    Returns:
        (attributable_efs_change, gamma_attr, attribution_category)
    """
    innings = int(row.get("innings", 1))
    if innings != 1:
        return float(row.get("expected_final_change", 0.0)), 1.0, "CHASE"

    efs_chg = row.get("expected_final_change")
    if efs_chg is None or pd.isna(efs_chg):
        return np.nan, 1.0, "MISSING"

    efs_chg = float(efs_chg)
    runs = float(row.get("actual_runs", 0.0))
    exp_runs = float(row.get("expected_runs", runs))
    delta_r = runs - exp_runs
    external_drag = efs_chg - delta_r

    # If external drag is positive, team state improved above batter's contribution
    if external_drag >= 0.0:
        return efs_chg, 1.0, "POSITIVE_DRAG"

    wkts_lost = row.get("wickets_lost_during_stay")
    if wkts_lost is None or pd.isna(wkts_lost):
        return efs_chg, 1.0, "UNKNOWN_WICKETS"

    wkts_lost = int(wkts_lost)
    if wkts_lost == 0:
        return efs_chg, 1.0, "NO_WICKETS"

    is_dismissed = (str(row.get("dismissal_status", "out")).lower() == "out")
    partner_wkts = max(0, wkts_lost - 1) if is_dismissed else wkts_lost
    if partner_wkts == 0:
        return efs_chg, 1.0, "NO_PARTNER_WICKETS"

    balls = int(row.get("balls_faced", 0))
    # Anti-free-rider gate: Golden ducks and minimal cameo stays receive no relief
    if (balls <= 1 and runs == 0.0) or (balls < 6 and runs < 10.0):
        return efs_chg, 1.0, "MINIMAL_STAY"

    dots_pct = float(row.get("dot_ball_percentage", 30.0))
    sr_ratio = float(row.get("sr_performance_ratio", 1.0))
    act_sr = float(row.get("actual_sr", (runs / max(1, balls)) * 100.0))

    # Category A: Evaluated batter created pressure or underperformed
    if (dots_pct >= 50.0 and sr_ratio < 1.15) or (act_sr < 100.0 and balls >= 10) or delta_r <= 0.0:
        gamma = gamma_caused
        cat = "CATEGORY_A"
    # Category C: Severe multi-wicket collapse (>= 3 partner wickets)
    elif partner_wkts >= 3:
        gamma = gamma_collapse
        cat = "CATEGORY_C"
    # Category B: Batter scored efficiently while partner was dismissed independently
    elif (sr_ratio >= 1.25 or act_sr >= 150.0) and dots_pct < 45.0 and delta_r > 0.0:
        gamma = gamma_independent
        cat = "CATEGORY_B"
    # Category C: 2 partner wickets collapse
    elif partner_wkts >= 2:
        gamma = gamma_collapse
        cat = "CATEGORY_C"
    # General team stagnation with 1 partner wicket
    else:
        gamma = gamma_stagnation
        cat = "CATEGORY_C"

    attr_efs = delta_r + gamma * external_drag
    return float(attr_efs), float(gamma), str(cat)


def compute_pillar3_team_state_impact(row: Any, apply_attribution: bool = True) -> float:
    """
    Pillar 3: Team-State Impact Score (Raw).
    Measures change in team's position over exact entry -> exit window:
    - 1st innings: Expected Final Score Change (delta EFS), scoring acceleration, trajectory change
      with Phase 7U Wicket Causality Attribution.
    - 2nd innings: Required RR relief (delta RRR), RR gap reduction, target progress
    - Dynamic wicket resource cost
    """
    innings = int(row.get("innings", 1))
    if innings > 2:
        return np.nan  # Super Over: excluded from normal 20-over contribution calculations

    actual_runs = float(row.get("actual_runs", 0))
    balls_rem_exit = float(row.get("balls_remaining_exit", 0))
    wkts_rem_exit = float(row.get("wickets_remaining_exit", 5))
    wkt_res_chg = float(row.get("wicket_resource_change", 0))

    # Dynamic wicket cost (Section 10):
    # Wicket at 19.5 has ~0 penalty; wicket at 3.2 has notable penalty.
    # High run knock offsets penalty.
    if wkt_res_chg < 0:
        base_cost = (balls_rem_exit / 120.0) * (10.0 / max(1.0, wkts_rem_exit + 2.0)) * 0.5
        offset = min(base_cost * 0.7, max(0.0, actual_runs - 15.0) * 0.02)
        s_res = -(base_cost - offset)
    else:
        s_res = 0.15 * (wkts_rem_exit / 10.0)

    if innings == 1:
        efs_chg = row.get("expected_final_change")
        if pd.notnull(efs_chg):
            if apply_attribution:
                efs_chg, _, _ = compute_attributable_team_state_efs(row)
            z_efs = float(efs_chg) / 12.0
            traj_dev_chg = float(row.get("trajectory_deviation_change", 0.0)) / 10.0
            window_rr = float(row.get("window_team_rr", 7.5))
            team_rr_entry = float(row.get("team_rr_entry", 7.5))
            accel = np.clip((window_rr - team_rr_entry) / 3.0, -3.0, 3.0)
            raw = 0.50 * z_efs + 0.25 * traj_dev_chg + 0.25 * accel + s_res
            return float(raw)
        else:
            # Rain-shortened or unmodelled 1st innings (Phase 7O Early-Over P3 Stabilization)
            window_rr = float(row.get("window_team_rr", 7.5))
            team_rr_entry = float(row.get("team_rr_entry", 7.5))
            entry_over = float(row.get("entry_over", 0.0))
            if entry_over < 4.0:
                full_ov = int(entry_over)
                sub_ball = int(round((entry_over - full_ov) * 10.0))
                balls_bowled = full_ov * 6 + sub_ball
                alpha = min(1.0, balls_bowled / 24.0)
                effective_rr_entry = alpha * team_rr_entry + (1.0 - alpha) * 10.0
            else:
                effective_rr_entry = team_rr_entry
            accel = np.clip((window_rr - effective_rr_entry) / 3.0, -3.0, 3.0)
            runs_added = float(row.get("team_runs_added", actual_runs))
            overs_spent = max(0.2, float(row.get("overs_spent", 1.0)))
            raw = 0.60 * accel + 0.40 * ((runs_added - overs_spent * 8.0) / 10.0) + s_res
            return float(raw)
    else:
        # Chase (innings == 2)
        rrr_chg = np.clip(float(row.get("required_rr_change", 0.0)), -12.0, 12.0)
        rr_gap_chg = np.clip(float(row.get("rr_gap_change", 0.0)), -12.0, 12.0)
        t_prog = float(row.get("target_progress_change", 0.0))

        z_rrr = rrr_chg / 3.0
        z_gap = rr_gap_chg / 3.0
        z_prog = (t_prog - 0.15) / 0.15
        raw = 0.50 * z_rrr + 0.25 * z_gap + 0.25 * z_prog + s_res
        return float(raw)


def compute_pillar4_counterfactual_value(row: Any) -> float:
    """
    Pillar 4: Counterfactual Value Score (Raw).
    Answers: 'Given exact situation faced, what could batter reasonably have done differently?'
    Constructs a realistic alternative based on match phase, wickets, RRR/team RR, and balls faced.
    Evaluates net state trajectory delivered above the realistic counterfactual.
    """
    innings = int(row.get("innings", 1))
    if innings > 2:
        return np.nan  # Super Over: excluded from normal 20-over contribution calculations

    actual_runs = float(row.get("actual_runs", 0))
    balls_faced = float(row.get("balls_faced", 0))
    entry_over = float(row.get("entry_over", 0.0))
    wkts_rem_entry = float(row.get("wickets_remaining_entry", 10))

    if balls_faced <= 0:
        return 0.0

    # Base realistic situational scoring tempo
    if entry_over < 6.0:
        base_sr = 120.0
    elif entry_over < 16.0:
        base_sr = 125.0
    else:
        base_sr = 150.0 + min(25.0, (entry_over - 16.0) * 8.0)

    # Collapse adjustment: realistic batter must consolidate
    if wkts_rem_entry <= 4 and entry_over < 14.0:
        base_sr -= 15.0

    # Chase requirement adjustment
    if innings == 2:
        req_rr_entry = float(row.get("required_rr_entry", 8.5))
        if req_rr_entry > 11.0:
            base_sr = max(base_sr, min(165.0, req_rr_entry * 12.0))
        elif req_rr_entry < 6.0:
            base_sr = min(base_sr, 115.0)

    cf_realistic_runs = balls_faced * (base_sr / 100.0)
    delta_runs = actual_runs - cf_realistic_runs

    if innings == 1:
        efs_chg = row.get("expected_final_change")
        if pd.notnull(efs_chg):
            cf_efs_chg = (cf_realistic_runs - 19.8) * 0.5
            delta_traj = float(efs_chg) - cf_efs_chg
        else:
            delta_traj = delta_runs
        raw = (delta_runs / 14.0) * 0.6 + (delta_traj / 12.0) * 0.4
    else:
        rrr_chg = np.clip(float(row.get("required_rr_change", 0.0)), -12.0, 12.0)
        balls_rem_exit = float(row.get("balls_remaining_exit", 60))
        if balls_rem_exit > 0:
            cf_rrr_chg = np.clip((delta_runs * 6.0 / balls_rem_exit), -8.0, 8.0)
        else:
            cf_rrr_chg = 0.0
        delta_rrr_relief = rrr_chg - cf_rrr_chg
        raw = (delta_runs / 14.0) * 0.5 + (delta_rrr_relief / 2.5) * 0.5

    return float(raw)


def normalize_pillar_score(z_score: float, k: float = 1.40) -> float:
    """
    Normalizes a standardized component z-score to a [0, 100] scale.
    Par (z = 0.0) maps exactly to 50.0.
    """
    if z_score is None or pd.isna(z_score):
        return None
    val = 100.0 / (1.0 + np.exp(-k * z_score))
    return float(np.clip(val, 0.1, 99.9))


def compute_phase5b_contribution(
    row: Any,
    weights: Optional[Dict[str, float]] = None,
    params: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Full Phase 5B Batter Contribution Evaluator.
    Computes all four standardized pillars with 25% equal conceptual weighting:
      Pillar 1: Match Context
      Pillar 2: Batter Performance
      Pillar 3: Team-State Impact
      Pillar 4: Counterfactual Value
      
    Outputs:
      Output A: Contribution Score (0 to 100, par ~ 50.0)
      Output B: Raw Composite Contribution (used for season and match share)
      Individual Normalized Pillar Scores (0 to 100, par ~ 50.0)
      
    Did-Not-Bat (DNB) Rule:
      If player never came to the crease, returns None (NULL) for all scores.
      
    Super Over Rule:
      Super overs (innings > 2) are excluded from the standard 20-over framework (returns None).
    """
    p = params or PHASE5B_EMPIRICAL_PARAMS
    w = weights or {"w_context": 0.25, "w_perf": 0.25, "w_state": 0.25, "w_cf": 0.25}

    # Section 17 & 18: Did-Not-Bat Rule
    # If the player never came to crease, score = NULL, share = NULL
    if (
        row.get("dnb") is True
        or row.get("did_not_bat") is True
        or (pd.isna(row.get("balls_faced")) and pd.isna(row.get("actual_runs")))
    ):
        return {
            "dnb": True,
            "super_over": False,
            "raw_contribution": None,
            "contribution_score": None,
            "pillar1_context_score": None,
            "pillar2_perf_score": None,
            "pillar3_state_score": None,
            "pillar4_cf_score": None,
            "z_context": None,
            "z_perf": None,
            "z_state": None,
            "z_cf": None,
        }

    # Section 7: Super Over Rule
    innings = int(row.get("innings", 1))
    if innings > 2:
        return {
            "dnb": False,
            "super_over": True,
            "raw_contribution": None,
            "contribution_score": None,
            "pillar1_context_score": None,
            "pillar2_perf_score": None,
            "pillar3_state_score": None,
            "pillar4_cf_score": None,
            "z_context": None,
            "z_perf": None,
            "z_state": None,
            "z_cf": None,
            "commentary": "Super Overs are excluded from standard 20-over contribution calculations."
        }

    # 1. Compute raw scores for all 4 pillars
    p1_raw = compute_pillar1_match_context(row)
    p2_raw = compute_pillar2_batter_performance(row)
    p3_raw = compute_pillar3_team_state_impact(row)
    p4_raw = compute_pillar4_counterfactual_value(row)

    # 2. Standardize to unit variance (eliminates scale distortion)
    z1 = (p1_raw - p["pillar1_mean"]) / p["pillar1_std"]
    z2 = (p2_raw - p["pillar2_mean"]) / p["pillar2_std"]
    z3 = (p3_raw - p["pillar3_mean"]) / p["pillar3_std"]
    z4 = (p4_raw - p["pillar4_mean"]) / p["pillar4_std"]

    # 3. Individual Pillar Scores (0 to 100, Par = 50.0)
    score_p1 = normalize_pillar_score(z1, k=p["pillar_scale"])
    score_p2 = normalize_pillar_score(z2, k=p["pillar_scale"])
    score_p3 = normalize_pillar_score(z3, k=p["pillar_scale"])
    score_p4 = normalize_pillar_score(z4, k=p["pillar_scale"])

    # 4. Equal Conceptual Priority (25% each)
    c_raw = (
        w["w_context"] * z1
        + w["w_perf"] * z2
        + w["w_state"] * z3
        + w["w_cf"] * z4
    )

    # 5. Output A: Final Contribution Score (0 to 100, Par = 50.0)
    center = p["composite_center"]
    scale = p["composite_scale"]
    contrib_score = 100.0 / (1.0 + np.exp(-scale * (c_raw - center)))
    contrib_score = float(np.clip(contrib_score, 0.1, 99.9))

    return {
        "dnb": False,
        "raw_contribution": round(float(c_raw), 4),
        "contribution_score": round(contrib_score, 1),
        "pillar1_context_score": round(score_p1, 1),
        "pillar2_perf_score": round(score_p2, 1),
        "pillar3_state_score": round(score_p3, 1),
        "pillar4_cf_score": round(score_p4, 1),
        "z_context": round(float(z1), 3),
        "z_perf": round(float(z2), 3),
        "z_state": round(float(z3), 3),
        "z_cf": round(float(z4), 3),
    }


def compute_season_aggregation(
    player_innings: List[Dict[str, Any]],
    team_total_positive_contribution: float,
    matches_played: int,
) -> Dict[str, Any]:
    """
    Aggregates player contribution across a season following Section 18 & 19:
    - Never dilutes with DNB matches
    - Rectified positive season contribution share
    - Detailed breakdowns by situation and phase
    """
    batting_inns = [inn for inn in player_innings if not inn.get("dnb", False) and inn.get("contribution_score") is not None]
    num_batted = len(batting_inns)
    dnb_matches = max(0, matches_played - num_batted)

    if num_batted == 0:
        return {
            "matches_played": matches_played,
            "batting_innings": 0,
            "did_not_bat_matches": dnb_matches,
            "average_contribution_score": None,
            "total_raw_contribution": 0.0,
            "season_team_contribution_share": None,
            "contribution_per_batting_opportunity": None,
            "first_innings_contribution": None,
            "chase_contribution": None,
            "powerplay_contribution": None,
            "middle_over_contribution": None,
            "death_over_contribution": None,
            "high_pressure_contribution": None,
        }

    scores = [inn["contribution_score"] for inn in batting_inns]
    raws = [inn["raw_contribution"] for inn in batting_inns]
    avg_score = float(np.mean(scores))
    tot_raw = float(np.sum(raws))
    contrib_per_opp = tot_raw / num_batted

    # Season Team Contribution Share: sum of player positive raw / sum of team positive raw
    player_positive_raw = float(np.sum([max(0.0, r) for r in raws]))
    if team_total_positive_contribution > 1e-6:
        season_share = round((player_positive_raw / team_total_positive_contribution) * 100.0, 2)
    else:
        season_share = 0.0

    # Situational breakdowns
    inn1 = [inn["contribution_score"] for inn in batting_inns if inn.get("innings") == 1]
    inn2 = [inn["contribution_score"] for inn in batting_inns if inn.get("innings") == 2]
    pp = [inn["contribution_score"] for inn in batting_inns if float(inn.get("entry_over", 0.0)) < 6.0]
    mid = []
    for inn in batting_inns:
        entry = float(inn.get("entry_over", 0.0))
        exit_val = inn.get("exit_over")
        exit_o = entry if (exit_val is None or (isinstance(exit_val, float) and np.isnan(exit_val))) else float(exit_val)
        if entry < 16.0 and exit_o >= 6.0:
            mid.append(inn["contribution_score"])
    death = [inn["contribution_score"] for inn in batting_inns if float(inn.get("entry_over", 0.0)) >= 16.0]
    high_press = [inn["contribution_score"] for inn in batting_inns if inn.get("pillar1_context_score", 50.0) >= 60.0]

    return {
        "matches_played": matches_played,
        "batting_innings": num_batted,
        "did_not_bat_matches": dnb_matches,
        "average_contribution_score": round(avg_score, 1),
        "total_raw_contribution": round(tot_raw, 3),
        "total_contribution": round(tot_raw, 3),
        "season_team_contribution_share": season_share,
        "contribution_per_batting_opportunity": round(contrib_per_opp, 3),
        "first_innings_contribution": round(float(np.mean(inn1)), 1) if inn1 else None,
        "chase_contribution": round(float(np.mean(inn2)), 1) if inn2 else None,
        "powerplay_contribution": round(float(np.mean(pp)), 1) if pp else None,
        "middle_over_contribution": round(float(np.mean(mid)), 1) if mid else None,
        "death_over_contribution": round(float(np.mean(death)), 1) if death else None,
        "high_pressure_contribution": round(float(np.mean(high_press)), 1) if high_press else None,
    }


# ==============================================================================
# PHASE 7L: APPROVED PRODUCTION CONTEXT-AS-LEVERAGE ARCHITECTURE
# ==============================================================================

import math

# Standardization parameters for Pillar 3 (P3)
P3_STANDARDIZATION_MEAN = 0.159
P3_STANDARDIZATION_STD = 1.513
P3_STANDARDIZATION_SCALE = 1.40


def compute_wicket_crisis_signal(
    entry_over: float,
    wickets_remaining_entry: float,
    balls_remaining_entry: float,
) -> float:
    """
    Context Dimension A: Wicket Crisis Pressure Signal (C_wkt).
    Physical cricket state inputs:
    - Wickets lost at entry: W_lost = 10 - wickets_remaining_entry
    - Overs completed at entry: entry_over
    - Wickets lost relative to overs completed (loss rate)
    - Early collapse severity (e.g. 3+ wickets lost inside powerplay)
    - Wickets remaining vs balls remaining (scarcity ratio)

    Returns a normalized situational pressure score on a 0-100 scale:
    - 0/0 at 0.0 overs: ~35.0 (calm platform, zero crisis)
    - Ordinary progression: ~50.0 (par)
    - Early collapse (e.g. 20/3 at 3.5 overs): ~72.0 - 75.0 (crisis)
    - Catastrophic collapse (e.g. 30/5 at 5.0 overs): ~88.0 - 92.0 (extreme crisis)
    """
    wkts_rem = max(1.0, min(10.0, float(wickets_remaining_entry)))
    wkts_lost = max(0.0, 10.0 - wkts_rem)
    t = max(0.0, min(20.0, float(entry_over)))
    balls_rem = max(0.0, min(120.0, float(balls_remaining_entry)))

    if t <= 0.2 and wkts_lost == 0:
        return 35.0

    loss_rate = wkts_lost / max(0.8, t)
    scarcity = (balls_rem / 6.0) / wkts_rem

    loss_rate_z = (loss_rate - 0.30) / 0.25
    scarcity_z = (scarcity - 1.8) / 0.8

    crisis_raw = 0.55 * loss_rate_z + 0.45 * scarcity_z
    c_wkt = 50.0 + 20.0 * float(np.tanh(crisis_raw))

    if t <= 6.0 and wkts_lost >= 3:
        severity_bonus = min(15.0, (wkts_lost - 2.0) * 5.0)
        c_wkt += severity_bonus

    return float(np.clip(c_wkt, 10.0, 95.0))


def compute_chase_pressure_signal(
    innings: int,
    entry_over: float,
    team_rr_entry: float,
    target: float = 0.0,
    required_rr_entry: float = 0.0,
    rr_gap_entry: float = 0.0,
) -> float:
    """
    Context Dimension B: Chase Pressure Signal (C_chase).
    Evaluates:
    - Target size relative to historical T20 par (~165)
    - Required run rate at entry relative to par (8.25)
    - Current run rate and run rate gap (RRR - CRR)
    - For 1st innings: reflects platform rate pressure relative to 8.0 par tempo.

    Returns a normalized situational pressure score on a 0-100 scale:
    - Low-target chase (0/0 chasing 115, RRR=5.75): ~32.1 (low pressure)
    - Standard chase (0/0 chasing 165, RRR=8.25): ~50.0 (par pressure)
    - Steep chase (0/0 chasing 208, RRR=10.4): ~66.5 (high chase pressure)
    - 1st innings normal tempo: ~50.0
    """
    inn = int(innings)
    t = max(0.0, min(20.0, float(entry_over)))
    crr = max(0.0, float(team_rr_entry))

    if inn == 1:
        if t <= 4.0:
            return 50.0
        rr_dev = (7.5 - crr) / 2.0
        c_chase = 50.0 + 10.0 * float(np.tanh(rr_dev))
        return float(np.clip(c_chase, 20.0, 80.0))

    tgt = max(0.0, float(target))
    rrr = min(24.0, max(0.0, float(required_rr_entry)))
    gap = min(8.0, max(-4.0, float(rr_gap_entry)))

    target_pressure = (tgt - 165.0) / 30.0
    rrr_pressure = (rrr - 8.25) / 2.5
    gap_pressure = (gap / 2.5) if t > 4.0 else 0.0

    chase_raw = 0.55 * rrr_pressure + 0.35 * target_pressure + 0.10 * gap_pressure
    c_chase = 50.0 + 22.0 * float(np.tanh(chase_raw))

    return float(np.clip(c_chase, 10.0, 95.0))


def compute_opening_opportunity_signal(
    entry_over: float,
    wickets_remaining_entry: float,
    balls_remaining_entry: float,
) -> float:
    """
    Context Dimension C: Opening / Early-Innings Opportunity Signal (C_open).
    """
    t = float(entry_over)
    wkts_rem = float(wickets_remaining_entry)

    if t <= 0.2 and wkts_rem >= 10:
        return 38.0
    elif t <= 2.0 and wkts_rem >= 9:
        return 42.0
    elif t <= 6.0 and wkts_rem >= 8:
        return 48.0
    else:
        return 50.0


def compute_match_state_leverage_classification(
    c_wkt: float,
    c_chase: float,
) -> str:
    """
    Context Dimension D: Match-State Leverage Classification.
    Zones:
    1. EXTREME CRISIS: C_wkt >= 65 and C_chase >= 60
    2. COLLAPSE PRESSURE: C_wkt >= 65
    3. HIGH CHASE PRESSURE: C_chase >= 60
    4. LOW CONTEXT PRESSURE: C_wkt < 40 and C_chase < 42
    5. NORMAL CONTEXT: all others
    """
    if c_wkt >= 65.0 and c_chase >= 60.0:
        return "EXTREME CRISIS"
    elif c_wkt >= 65.0:
        return "COLLAPSE PRESSURE"
    elif c_chase >= 60.0:
        return "HIGH CHASE PRESSURE"
    elif c_wkt < 40.0 and c_chase < 42.0:
        return "LOW CONTEXT PRESSURE"
    else:
        return "NORMAL CONTEXT"


def leverage_model_b(
    c_wkt: float,
    c_chase: float,
    innings: int = 1,
    alpha_low: float = 0.38,
    alpha_high: float = 0.48,
) -> Tuple[float, float]:
    """
    Approved Phase 7H Composite Dual-Slope Leverage Model (Model B).
    - 1st innings: C_eff = 0.65 * C_wkt + 0.35 * C_chase
    - 2nd innings: C_eff = 0.55 * C_wkt + 0.45 * C_chase
    - C_eff < 50.0: L = 1.0 + alpha_low * ((C_eff - 50.0) / 50.0)
    - C_eff >= 50.0: L = 1.0 + alpha_high * ((C_eff - 50.0) / 50.0)
    Bounded strictly in [0.65, 1.35]. Par L(50.0) = 1.000 exactly.
    """
    w_wkt = 0.65 if int(innings) == 1 else 0.55
    c_eff = w_wkt * float(c_wkt) + (1.0 - w_wkt) * float(c_chase)
    dev = (c_eff - 50.0) / 50.0
    alpha = alpha_high if dev >= 0.0 else alpha_low
    lev = 1.0 + alpha * dev
    return float(np.clip(lev, 0.65, 1.35)), float(c_eff)


def compute_context_and_leverage(row: Any) -> Dict[str, Any]:
    """
    Computes situational context signals and Model B leverage L for a batter match row.
    """
    innings = int(row.get("innings", 1))
    entry_over = float(row.get("entry_over", 0.0))
    wkts_rem = float(row.get("wickets_remaining_entry", row.get("wkts_rem_entry", 10.0)))
    balls_rem = float(row.get("balls_remaining_entry", row.get("balls_rem_entry", 120.0)))
    team_rr = float(row.get("team_rr_entry", row.get("team_rr", 7.5)))
    target = float(row.get("target", 0.0)) if innings == 2 else 0.0
    req_rr = float(row.get("required_rr_entry", row.get("req_rr", 0.0))) if innings == 2 else 0.0

    c_wkt = compute_wicket_crisis_signal(entry_over, wkts_rem, balls_rem)
    c_chase = compute_chase_pressure_signal(innings, entry_over, team_rr, target, req_rr)
    c_open = compute_opening_opportunity_signal(entry_over, wkts_rem, balls_rem)
    zone = compute_match_state_leverage_classification(c_wkt, c_chase)
    lev, c_eff = leverage_model_b(c_wkt, c_chase, innings)

    return {
        "c_wkt": round(c_wkt, 1),
        "c_chase": round(c_chase, 1),
        "c_open": round(c_open, 1),
        "c_eff": round(c_eff, 1),
        "c_match": zone,
        "context_zone": zone,
        "leverage": round(lev, 3),
    }


def compute_chase_feasibility_signal(
    balls_remaining_entry: float,
    wickets_remaining_entry: float,
    required_rr_entry: float,
) -> Tuple[float, float, float]:
    """
    Phase 7I Model E Chase Feasibility Signal (F_chase in [0.0, 1.0]).
    Uses ONLY physical match state at entry:
    - balls_remaining_entry
    - wickets_remaining_entry
    - required_rr_entry
    Zero future information, zero outcome leakage.
    """
    b_rem = max(1.0, float(balls_remaining_entry))
    w_rem = max(1.0, min(10.0, float(wickets_remaining_entry)))
    rrr = min(120.0, max(0.0, float(required_rr_entry)))

    wkt_adj = 3.0 * float(np.tanh((w_rem - 3.5) / 2.0))
    burst_adj = 4.0 * (12.0 / (b_rem + 6.0))
    v_max = 12.0 + wkt_adj + burst_adj

    ratio = rrr / max(6.0, v_max)
    f_chase = 1.0 / (1.0 + math.exp(4.0 * (ratio - 1.25)))
    return float(v_max), float(ratio), float(np.clip(f_chase, 0.0, 1.0))


def map_raw_to_p3_score(raw_val: float) -> float:
    """Standardizes and maps raw P3 to normalized 0.1-99.9 scale."""
    z = (float(raw_val) - P3_STANDARDIZATION_MEAN) / P3_STANDARDIZATION_STD
    val = 100.0 / (1.0 + math.exp(-P3_STANDARDIZATION_SCALE * z))
    return float(np.clip(val, 0.1, 99.9))


# ==============================================================================
# Phase 7Q — Decoupled State-Preservation Floor
# ==============================================================================

# Phase 7Q — Decoupled State-Preservation Floor
# ==============================================================================

P3_PRESERVATION_FLOOR_DEFAULT: float = 64.0


def check_p3_preservation_eligibility(row: Any) -> bool:
    """
    Phase 7Q Model B Anti-Free-Rider Preservation Eligibility Gate.

    Evaluates whether a batting performance satisfies ALL required conditions
    for the state-preservation floor, strictly independent of P2:
    - Condition A: Strong inherited team state (1st inn: EFS >= 180.0; 2nd inn: RRR <= 7.5)
    - Condition B: Team state maintained (1st inn: delta_EFS >= -2.5; 2nd inn: delta_RRR >= -0.5, TargetProgress >= 0.20)
    - Condition C: Batter personally contributed at strong tempo (1st inn: Personal RR >= 8.5 RPO; 2nd inn: Personal RR >= RRR_entry)
    - Condition D: Minimum involvement (balls_faced >= 8 OR actual_runs >= 15)
    - Condition E: No golden duck (0 off 1 or 0 balls) and strict DNB exclusion.
    """
    if row is None or pd.isna(row.get("balls_faced")):
        return False

    # Strict DNB and missing check
    if (
        row.get("dnb") is True
        or row.get("did_not_bat") is True
        or row.get("is_dnb") is True
    ):
        return False

    try:
        balls = int(row.get("balls_faced", 0))
        runs = float(row.get("actual_runs", 0.0))
    except (ValueError, TypeError):
        return False

    # Gate 6 & Gate 5: Golden duck and minimum involvement exclusion
    if (balls <= 1 and runs == 0.0) or (balls < 8 and runs < 15.0):
        return False

    personal_rr = (runs / max(1, balls)) * 6.0

    try:
        innings = int(row.get("innings", 1))
    except (ValueError, TypeError):
        innings = 1

    if innings == 1:
        efs_en = row.get("expected_final_entry")
        efs_chg = row.get("expected_final_change")
        w_rr = row.get("window_team_rr")

        if pd.isna(efs_en) or pd.isna(efs_chg) or pd.isna(w_rr):
            return False

        try:
            efs_en = float(efs_en)
            efs_chg = float(efs_chg)
            w_rr = float(w_rr)
        except (ValueError, TypeError):
            return False

        # All 4 Gates for 1st Innings:
        # 1. Strong inherited platform: EFS >= 180.0
        # 2. No material deterioration: delta_EFS >= -2.5
        # 3. High window team tempo: window_rr >= 9.0 RPO
        # 4. Anti-free-rider personal tempo: personal_rr >= 8.5 RPO
        return (
            efs_en >= 180.0
            and efs_chg >= -2.5
            and w_rr >= 9.0
            and personal_rr >= 8.5
        )

    elif innings == 2:
        rrr_en = row.get("required_rr_entry")
        rrr_chg = row.get("required_rr_change")
        t_prog = row.get("target_progress_change")

        if pd.isna(rrr_en) or pd.isna(rrr_chg) or pd.isna(t_prog):
            return False

        try:
            rrr_en = float(rrr_en)
            rrr_chg = float(rrr_chg)
            t_prog = float(t_prog)
        except (ValueError, TypeError):
            return False

        # All 4 Gates for 2nd Innings:
        # 1. Strong inherited platform: RRR <= 7.5
        # 2. No blowout: delta_RRR >= -0.5
        # 3. Meaningful chase progress: target_progress_change >= 0.20
        # 4. Anti-free-rider personal tempo: personal_rr >= required_rr_entry
        return (
            rrr_en <= 7.5
            and rrr_chg >= -0.5
            and t_prog >= 0.20
            and personal_rr >= rrr_en
        )

    return False


def apply_p3_state_preservation_floor(
    raw_p3: float,
    row: Any,
    floor_score: float = P3_PRESERVATION_FLOOR_DEFAULT,
) -> float:
    """
    Phase 7Q Decoupled State-Preservation Floor with Anti-Free-Rider Gate (Raw Space).

    Prevents P3 from collapsing into the low 50s when an elite team state is
    successfully preserved by an active batter, without coupling P3 to P2.

    If qualifying:
        raw_p3 = max(raw_p3, floor_raw)
    Where floor_raw maps directly to floor_score (default: 64.0) via map_raw_to_p3_score.
    """
    if pd.isna(raw_p3):
        return raw_p3

    if not check_p3_preservation_eligibility(row):
        return raw_p3

    clamped_floor = max(0.1, min(99.9, float(floor_score)))
    z_target = -math.log(100.0 / clamped_floor - 1.0) / P3_STANDARDIZATION_SCALE
    floor_raw = P3_STANDARDIZATION_MEAN + z_target * P3_STANDARDIZATION_STD
    return max(float(raw_p3), floor_raw)


def apply_p3_score_preservation_floor(
    p3_score: float,
    row: Any,
    floor_score: float = P3_PRESERVATION_FLOOR_DEFAULT,
) -> float:
    """
    Phase 7Q Decoupled State-Preservation Floor (P3 Score Space):
        P3 = max(p3_score, floor_score) if qualifying else p3_score.
    """
    if pd.isna(p3_score):
        return p3_score

    if not check_p3_preservation_eligibility(row):
        return p3_score

    return max(float(p3_score), float(floor_score))


def compute_dampened_p3_raw(
    row: Any,
    strategy: str = "model_e",
    apply_preservation: bool = True,
    apply_attribution: bool = True,
    floor_score: float = P3_PRESERVATION_FLOOR_DEFAULT,
) -> float:
    """
    Phase 7I Model E Feasibility-Gated Soft Saturation for Pillar 3 (Team-State Impact)
    with Phase 7Q Decoupled State-Preservation Floor and Phase 7U Wicket Causality Attribution.
    1st innings: Invariant baseline calculation with causal attribution and preservation floor.
    2nd innings: Soft saturation bounded by feasibility capacity cap = 4.0 + 6.0 * F_chase,
                 with preservation floor for controlled chases.
    """
    innings = int(row.get("innings", 1))
    if innings > 2:
        return np.nan

    actual_runs = float(row.get("actual_runs", 0))
    balls_rem_exit = float(row.get("balls_remaining_exit", 0))
    wkts_rem_exit = float(row.get("wickets_remaining_exit", 5))
    wkt_res_chg = float(row.get("wicket_resource_change", 0))

    # Dynamic wicket cost
    if wkt_res_chg < 0:
        base_cost = (balls_rem_exit / 120.0) * (10.0 / max(1.0, wkts_rem_exit + 2.0)) * 0.5
        offset = min(base_cost * 0.7, max(0.0, actual_runs - 15.0) * 0.02)
        s_res = -(base_cost - offset)
    else:
        s_res = 0.15 * (wkts_rem_exit / 10.0)

    # 1st Innings: Invariant baseline with causal attribution
    if innings == 1:
        efs_chg = row.get("expected_final_change")
        if pd.notnull(efs_chg):
            if apply_attribution:
                efs_chg, _, _ = compute_attributable_team_state_efs(row)
            z_efs = float(efs_chg) / 12.0
            traj_dev_chg = float(row.get("trajectory_deviation_change", 0.0)) / 10.0
            window_rr = float(row.get("window_team_rr", 7.5))
            team_rr_entry = float(row.get("team_rr_entry", 7.5))
            accel = np.clip((window_rr - team_rr_entry) / 3.0, -3.0, 3.0)
            raw = 0.50 * z_efs + 0.25 * traj_dev_chg + 0.25 * accel + s_res
            if apply_preservation:
                raw = apply_p3_state_preservation_floor(raw, row, floor_score=floor_score)
            return float(raw)
        else:
            # Rain-shortened or unmodelled 1st innings (Phase 7O Early-Over P3 Stabilization)
            window_rr = float(row.get("window_team_rr", 7.5))
            team_rr_entry = float(row.get("team_rr_entry", 7.5))
            entry_over = float(row.get("entry_over", 0.0))
            if entry_over < 4.0:
                full_ov = int(entry_over)
                sub_ball = int(round((entry_over - full_ov) * 10.0))
                balls_bowled = full_ov * 6 + sub_ball
                alpha = min(1.0, balls_bowled / 24.0)
                effective_rr_entry = alpha * team_rr_entry + (1.0 - alpha) * 10.0
            else:
                effective_rr_entry = team_rr_entry
            accel = np.clip((window_rr - effective_rr_entry) / 3.0, -3.0, 3.0)
            runs_added = float(row.get("team_runs_added", actual_runs))
            overs_spent = max(0.2, float(row.get("overs_spent", 1.0)))
            raw = 0.60 * accel + 0.40 * ((runs_added - overs_spent * 8.0) / 10.0) + s_res
            if apply_preservation:
                raw = apply_p3_state_preservation_floor(raw, row, floor_score=floor_score)
            return float(raw)

    # 2nd Innings (Chase)
    rrr_chg = float(row.get("required_rr_change", 0.0))
    rr_gap_chg = float(row.get("rr_gap_change", 0.0))
    t_prog = float(row.get("target_progress_change", 0.0))
    z_prog = (t_prog - 0.15) / 0.15

    b_rem = float(row.get("balls_remaining_entry", 30.0))
    w_rem = float(row.get("wickets_remaining_entry", 5.0))
    rrr_entry = float(row.get("required_rr_entry", 9.0))

    if strategy == "baseline":
        r_eff = np.clip(rrr_chg, -12.0, 12.0)
        g_eff = np.clip(rr_gap_chg, -12.0, 12.0)
    elif strategy == "model_e":
        _, _, f_chase = compute_chase_feasibility_signal(b_rem, w_rem, rrr_entry)
        pen_cap = 4.0 + 6.0 * f_chase
        if rrr_chg < 0:
            r_eff = -pen_cap * float(np.tanh(abs(rrr_chg) / pen_cap))
            g_eff = -pen_cap * float(np.tanh(abs(rr_gap_chg) / pen_cap))
        else:
            r_eff = min(12.0, rrr_chg)
            g_eff = min(12.0, rr_gap_chg)
    else:
        raise ValueError(f"Unknown P3 dampening strategy: {strategy}")

    z_rrr = r_eff / 3.0
    z_gap = g_eff / 3.0
    raw = 0.50 * z_rrr + 0.25 * z_gap + 0.25 * z_prog + s_res
    if apply_preservation:
        raw = apply_p3_state_preservation_floor(raw, row, floor_score=floor_score)
    return float(raw)


def compute_adjusted_pillar(
    raw_score: Optional[float],
    leverage: Optional[float],
) -> Optional[float]:
    """
    Adjusts an execution pillar (P2 or P3) by context leverage around par = 50.0.
    Formula:
        Adjusted = clip(50.0 + (Raw - 50.0) * Leverage, 0.1, 99.9)
    """
    if raw_score is None or pd.isna(raw_score) or leverage is None or pd.isna(leverage):
        return None
    adj = 50.0 + (float(raw_score) - 50.0) * float(leverage)
    return float(np.clip(adj, 0.1, 99.9))


# Public backwards compatibility alias
compute_adjusted_pillar_score = compute_adjusted_pillar


def compute_candidate_score(
    p2: Optional[float],
    p3: Optional[float],
    leverage: Optional[float],
) -> Optional[float]:
    """
    Context-as-Leverage Score Formulation:
        Adjusted P2 = clip(50 + (P2 - 50) * L, 0.1, 99.9)
        Adjusted P3 = clip(50 + (P3 - 50) * L, 0.1, 99.9)
        Final Score = clip(0.50 * Adjusted P2 + 0.50 * Adjusted P3, 0.1, 99.9)
    """
    if p2 is None or p3 is None or leverage is None or pd.isna(p2) or pd.isna(p3) or pd.isna(leverage):
        return None
    adj_p2 = compute_adjusted_pillar(p2, leverage)
    adj_p3 = compute_adjusted_pillar(p3, leverage)
    return round(float(np.clip(0.50 * adj_p2 + 0.50 * adj_p3, 0.1, 99.9)), 1)


def compute_p1_leverage(
    p1: Optional[float],
    p1_baseline: float = 50.0,
    alpha: float = 0.35,
) -> float:
    """
    Public backwards-compatible scalar P1 linear bounded leverage function.
    """
    if p1 is None or pd.isna(p1):
        return 1.0
    lev = 1.0 + alpha * ((float(p1) - p1_baseline) / 50.0)
    return float(np.clip(lev, 0.65, 1.35))


def compute_production_contribution(
    row: Any,
    weights: Optional[Dict[str, float]] = None,
    params: Optional[Dict[str, float]] = None,
    model_version: str = "phase7u",
    apply_preservation: Optional[bool] = None,
    apply_attribution: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Phase 7U Approved Production Batter Contribution Model:
    Context-as-Leverage Architecture with Decoupled State-Preservation Floor
    and Phase 7U Model T Wicket Causality Attribution.

    Formulas:
        Context: Composite Dual-Slope Model B (L in [0.65, 1.35])
        P3: Model E Feasibility-Gated Soft Saturation with Phase 7Q Preservation Floor
            and Phase 7U Wicket Causality Attribution (Model T)
        Adjusted_P2 = clip(50 + (P2 - 50) * L, 0.1, 99.9)
        Adjusted_P3 = clip(50 + (P3_dampened - 50) * L, 0.1, 99.9)
        Final Contribution Score = 0.50 * Adjusted_P2 + 0.50 * Adjusted_P3
    """
    if apply_preservation is None:
        apply_preservation = (model_version.lower() not in ["phase7d", "phase7l", "phase7o"])
    if apply_attribution is None:
        apply_attribution = (model_version.lower() not in ["phase7d", "phase7l", "phase7o", "phase7q_unattributed"])

    # Strict Did-Not-Bat (DNB) Rule
    if (
        row.get("dnb") is True
        or row.get("did_not_bat") is True
        or row.get("is_dnb") is True
        or (
            pd.isna(row.get("balls_faced"))
            and pd.isna(row.get("actual_runs"))
            and not ("score_perf" in row or "p2" in row)
        )
    ):
        return {
            "dnb": True,
            "is_dnb": True,
            "super_over": False,
            "raw_contribution": None,
            "contribution_score": None,
            "final_contribution": None,
            "final_contribution_score": None,
            "pillar1_context_score": None,
            "pillar2_perf_score": None,
            "pillar3_state_score": None,
            "pillar4_diagnostic": None,
            "adjusted_p2": None,
            "adjusted_p3": None,
            "leverage": None,
            "c_wkt": None,
            "c_chase": None,
            "c_open": None,
            "c_eff": None,
            "context_zone": None,
            "gamma_attribution": None,
            "attribution_category": None,
            "weights": {
                "architecture": "Phase 7L Context-as-Leverage (50% Adjusted P2 + 50% Adjusted P3)",
                "context_model": "Composite Dual-Slope Model B (Bounded L in [0.65, 1.35])",
                "p3_model": "Model E Feasibility-Gated Soft Saturation with Phase 7U Wicket Causality Attribution",
                "pillar1_match_context": "Leverage signal only (0% direct)",
                "pillar2_adjusted_performance": "50%",
                "pillar3_adjusted_state_impact": "50%",
                "pillar4_counterfactual": "Diagnostic only (0%)",
            },
        }

    # Super Over Rule
    innings = int(row.get("innings", 1))
    if innings > 2:
        return {
            "dnb": False,
            "is_dnb": False,
            "super_over": True,
            "raw_contribution": None,
            "contribution_score": None,
            "final_contribution": None,
            "final_contribution_score": None,
            "pillar1_context_score": None,
            "pillar2_perf_score": None,
            "pillar3_state_score": None,
            "pillar4_diagnostic": None,
            "adjusted_p2": None,
            "adjusted_p3": None,
            "leverage": None,
            "gamma_attribution": None,
            "attribution_category": None,
            "commentary": "Super Overs are excluded from standard 20-over contribution calculations.",
        }

    # Legacy Phase 7D / Custom Weights Fallback
    if weights is not None or model_version.lower() == "phase7d":
        from src.phase7c_rebalance import (
            PHASE5B_EMPIRICAL_PARAMS,
            PHASE7C_P3_PARAMS,
            compute_pillar1_match_context,
            compute_pillar2_batter_performance,
            compute_phase7c_p3,
            compute_phase7c_p4_diagnostic,
        )
        p = params or PHASE5B_EMPIRICAL_PARAMS
        p3_params = PHASE7C_P3_PARAMS

        p1_raw = compute_pillar1_match_context(row)
        p2_raw = compute_pillar2_batter_performance(row)
        p3_raw = compute_phase7c_p3(row)

        z1 = (p1_raw - p["pillar1_mean"]) / p["pillar1_std"]
        z2 = (p2_raw - p["pillar2_mean"]) / p["pillar2_std"]
        z3 = (p3_raw - p3_params["p3_mean"]) / p3_params["p3_std"]

        score_p1 = normalize_pillar_score(z1, k=p["pillar_scale"])
        score_p2 = normalize_pillar_score(z2, k=p["pillar_scale"])
        score_p3 = normalize_pillar_score(z3, k=p3_params["p3_scale"])

        w1 = weights.get("pillar1_match_context", 0.25) if weights else 0.25
        w2 = weights.get("pillar2_batter_performance", 0.35) if weights else 0.35
        w3 = weights.get("pillar3_team_state_impact", 0.40) if weights else 0.40

        contrib_score = float(np.clip(w1 * score_p1 + w2 * score_p2 + w3 * score_p3, 0.1, 99.9))
        c_raw = w1 * z1 + w2 * z2 + w3 * z3
        p4_diag = compute_phase7c_p4_diagnostic(row)

        return {
            "dnb": False,
            "is_dnb": False,
            "super_over": False,
            "contribution_score": round(contrib_score, 1),
            "final_contribution_score": round(contrib_score, 1),
            "raw_contribution": round(float(c_raw), 4),
            "pillar1_context_score": round(score_p1, 1),
            "pillar2_perf_score": round(score_p2, 1),
            "pillar3_state_score": round(score_p3, 1),
            "pillar4_diagnostic": p4_diag,
            "z_context": round(float(z1), 3),
            "z_perf": round(float(z2), 3),
            "z_state": round(float(z3), 3),
            "gamma_attribution": None,
            "attribution_category": None,
            "weights": {
                "pillar1_match_context": "25%",
                "pillar2_batter_performance": "35%",
                "pillar3_team_state_impact": "40%",
                "pillar4_counterfactual": "Diagnostic only (0%)",
            },
        }

    # ==========================================================================
    # Approved Phase 7L Production Engine
    # ==========================================================================
    # 1. Situational Context & Leverage (Phase 7H Model B)
    ctx = compute_context_and_leverage(row)
    lev = ctx["leverage"]
    c_eff = ctx["c_eff"]

    # 2. Batter Performance (P2)
    if "score_perf" in row or "p2" in row or "raw_p2" in row:
        p2 = float(row.get("score_perf", row.get("p2", row.get("raw_p2", 50.0))))
        clamped_p2 = max(0.1, min(99.9, p2))
        z2 = -math.log(100.0 / clamped_p2 - 1.0) / 1.4
    else:
        from src.phase7c_rebalance import compute_pillar2_batter_performance, PHASE5B_EMPIRICAL_PARAMS
        p = params or PHASE5B_EMPIRICAL_PARAMS
        p2_raw = compute_pillar2_batter_performance(row)
        z2 = (p2_raw - p["pillar2_mean"]) / p["pillar2_std"]
        p2 = normalize_pillar_score(z2, k=p["pillar_scale"])

    # Attribution signals
    attr_gamma = 1.0
    attr_cat = "NONE"
    if "expected_final_change" in row and pd.notnull(row.get("expected_final_change")):
        if apply_attribution:
            _, attr_gamma, attr_cat = compute_attributable_team_state_efs(row)

    # 3. Team-State Impact (P3 Model E)
    if "dampened_p3" in row:
        p3_dampened = float(row["dampened_p3"])
        if apply_preservation:
            p3_dampened = apply_p3_score_preservation_floor(p3_dampened, row)
        clamped_p3 = max(0.1, min(99.9, p3_dampened))
        z3 = -math.log(100.0 / clamped_p3 - 1.0) / 1.4
    elif "p3" in row:
        p3_dampened = float(row["p3"])
        if apply_preservation:
            p3_dampened = apply_p3_score_preservation_floor(p3_dampened, row)
        clamped_p3 = max(0.1, min(99.9, p3_dampened))
        z3 = -math.log(100.0 / clamped_p3 - 1.0) / 1.4
    elif "expected_final_change" in row or "required_rr_change" in row:
        p3_damp_raw = compute_dampened_p3_raw(row, strategy="model_e", apply_preservation=False, apply_attribution=apply_attribution)
        p3_dampened = map_raw_to_p3_score(p3_damp_raw)
        if apply_preservation:
            p3_dampened = apply_p3_score_preservation_floor(p3_dampened, row)
        clamped_p3 = max(0.1, min(99.9, p3_dampened))
        z3 = -math.log(100.0 / clamped_p3 - 1.0) / 1.4
    elif "score_state" in row:
        p3_dampened = float(row["score_state"])
        if apply_preservation:
            p3_dampened = apply_p3_score_preservation_floor(p3_dampened, row)
        clamped_p3 = max(0.1, min(99.9, p3_dampened))
        z3 = -math.log(100.0 / clamped_p3 - 1.0) / 1.4
    else:
        p3_damp_raw = compute_dampened_p3_raw(row, strategy="model_e", apply_preservation=False, apply_attribution=apply_attribution)
        p3_dampened = map_raw_to_p3_score(p3_damp_raw)
        if apply_preservation:
            p3_dampened = apply_p3_score_preservation_floor(p3_dampened, row)
        clamped_p3 = max(0.1, min(99.9, p3_dampened))
        z3 = -math.log(100.0 / clamped_p3 - 1.0) / 1.4

    # 4. Context-as-Leverage Adjustment around Par (50.0)
    adj_p2 = float(np.clip(50.0 + (p2 - 50.0) * lev, 0.1, 99.9))
    adj_p3 = float(np.clip(50.0 + (p3_dampened - 50.0) * lev, 0.1, 99.9))

    # 5. Final 50/50 Production Contribution Score
    final_score = float(np.clip(0.50 * adj_p2 + 0.50 * adj_p3, 0.1, 99.9))

    # 6. Raw Contribution in Z-space (for Team Contribution Share attribution)
    c_raw = 0.50 * (z2 * lev) + 0.50 * (z3 * lev)

    # 7. Diagnostic P4
    p4_diag = None
    try:
        from src.phase7c_rebalance import compute_phase7c_p4_diagnostic
        p4_diag = compute_phase7c_p4_diagnostic(row)
    except Exception:
        p4_diag = None

    return {
        "model_version": model_version,
        "dnb": False,
        "is_dnb": False,
        "super_over": False,
        "contribution_score": round(final_score, 1),
        "final_contribution": round(final_score, 1),
        "final_contribution_score": round(final_score, 1),
        "raw_contribution": round(float(c_raw), 4),
        "pillar1_context_score": round(c_eff, 1),
        "pillar2_perf_score": round(p2, 1),
        "pillar3_state_score": round(p3_dampened, 1),
        "adjusted_p2": round(adj_p2, 1),
        "adjusted_p3": round(adj_p3, 1),
        "leverage": round(lev, 3),
        "c_wkt": ctx["c_wkt"],
        "c_chase": ctx["c_chase"],
        "c_open": ctx["c_open"],
        "c_eff": ctx["c_eff"],
        "context_zone": ctx["context_zone"],
        "gamma_attribution": attr_gamma,
        "attribution_category": attr_cat,
        "pillar4_diagnostic": p4_diag,
        "z_perf": round(float(z2), 3),
        "z_state": round(float(z3), 3),
        "weights": {
            "architecture": "Phase 7L Context-as-Leverage (50% Adjusted P2 + 50% Adjusted P3)",
            "context_model": "Composite Dual-Slope Model B (Bounded L in [0.65, 1.35])",
            "p3_model": "Model E Feasibility-Gated Soft Saturation with Phase 7U Wicket Causality Attribution",
            "pillar1_match_context": "Leverage signal only (0% direct)",
            "pillar2_adjusted_performance": "50%",
            "pillar3_adjusted_state_impact": "50%",
            "pillar4_counterfactual": "Diagnostic only (0%)",
        },
    }


# Production Model Alias
compute_contribution_score = compute_production_contribution


