"""
Step 1 & 2: Audit existing P1 implementation and empirical distribution.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.contribution_framework import compute_pillar1_match_context, PHASE5B_EMPIRICAL_PARAMS, normalize_pillar_score


def audit_p1_logic():
    print("=== Step 1: P1 Implementation Audit ===")
    # 1. Signals determining P1:
    print("1. Signals: entry_over, balls_remaining_entry, wickets_remaining_entry, team_rr_entry (inn 1), required_rr_entry (inn 2), rr_gap_entry (inn 2)")
    # 2. Phase 7D PP correction:
    print("2. Early-over window: entry_over <= 4.0 overs")
    print("   - death_urgency = 0.0")
    print("   - wkts_lost = 10 - wkts_rem_entry")
    print("   - if wkts_lost == 0: collapse_pressure = 0.0, rr_pressure = 0.0 -> raw = 0.0 -> P1 = 37.3")
    print("   - if wkts_lost == 1: collapse_pressure = 0.50 -> raw = 0.225 -> P1 = 44.1")
    print("   - if wkts_lost == 2: collapse_pressure = 1.25 -> raw = 0.5625 -> P1 = 54.7")
    print("   - if wkts_lost >= 3: collapse_pressure = min(3.5, 0.50 + (wkts_lost - 1) * 0.75)")


def audit_p1_distribution():
    print("\n=== Step 2: P1 Empirical Distribution (19,111 Innings) ===")
    df = pd.read_csv("data/processed/batter_match_contributions.csv", low_memory=False)
    p1 = df["score_context"].dropna()
    
    stats = {
        "count": len(p1),
        "mean": round(float(p1.mean()), 2),
        "median": round(float(p1.median()), 2),
        "std": round(float(p1.std()), 2),
        "min": round(float(p1.min()), 2),
        "q10": round(float(p1.quantile(0.10)), 2),
        "q25": round(float(p1.quantile(0.25)), 2),
        "q50": round(float(p1.quantile(0.50)), 2),
        "q75": round(float(p1.quantile(0.75)), 2),
        "q90": round(float(p1.quantile(0.90)), 2),
        "max": round(float(p1.max()), 2),
    }
    for k, v in stats.items():
        print(f"  {k}: {v}")
    return stats


if __name__ == "__main__":
    audit_p1_logic()
    audit_p1_distribution()
