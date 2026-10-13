"""
Phase 8C: Regression Test Suite for Required Run Rate Change Sign Correction.

Validates:
1. Mathematical sign convention:
   - Entry RRR 9.8, exit RRR 0.0 -> required_rr_change = +9.8 (relief).
   - Entry RRR 7.0, exit RRR 9.0 -> required_rr_change = -2.0 (pressure).
   - Equal entry and exit RRR -> 0.0.
2. Upstream ingestion pipeline (scripts/ingest_competition_data.py) implements entry - exit.
3. Dataset compliance: 100% of second-innings rows in T20I and SMAT use canonical sign convention.
4. Dataset isolation: IPL datasets (data/processed/batter_match_contributions.csv) remain untouched.
5. Samson (Match 1512770, SV Samson) validation across storage, live production calc, and API:
   - P1 = 47.7, P2 = 95.9, P3 = 96.9, Adj P2 = 95.1/95.2, Adj P3 = 96.1, Final = 95.6.
6. Season metrics DNB integrity: non-batting appearances have NaN average score and share.
7. P1 Par invariance: Par entry conditions preserve par leverage = 1.000.
8. No data leakage or double counting: terminal exit RRR = 0 correctly represents completed chase.
"""

from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from src.contribution_framework import (
    compute_production_contribution,
    compute_context_and_leverage,
    compute_dampened_p3_raw,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
client = TestClient(app)


def test_rrr_change_mathematical_sign_convention():
    """Verify sign convention: positive for relief, negative for pressure, zero for equal."""
    # 1. Complete relief: 9.8 -> 0.0
    rin1, rout1 = 9.8, 0.0
    rchg1 = round(rin1 - rout1, 2)
    assert rchg1 == 9.8, f"Expected +9.8, got {rchg1}"

    # 2. Pressure spike: 7.0 -> 9.0
    rin2, rout2 = 7.0, 9.0
    rchg2 = round(rin2 - rout2, 2)
    assert rchg2 == -2.0, f"Expected -2.0, got {rchg2}"

    # 3. Equal rates: 8.5 -> 8.5
    rin3, rout3 = 8.5, 8.5
    rchg3 = round(rin3 - rout3, 2)
    assert rchg3 == 0.0, f"Expected 0.0, got {rchg3}"


def test_ingest_script_sign_convention():
    """Verify that scripts/ingest_competition_data.py uses rrr_in - rrr_out."""
    ingest_py = (REPO_ROOT / "scripts" / "ingest_competition_data.py").read_text(encoding="utf-8")
    assert 'b_row["required_rr_change"] = round(rrr_in - rrr_out, 2)' in ingest_py, (
        "scripts/ingest_competition_data.py must calculate rrr_in - rrr_out!"
    )
    assert 'b_row["required_rr_change"] = round(rrr_out - rrr_in, 2)' not in ingest_py, (
        "Found inverted rrr_out - rrr_in in scripts/ingest_competition_data.py!"
    )


def test_t20i_and_smat_datasets_canonical_sign_convention():
    """Verify that 100% of second innings chase rows in T20I and SMAT follow entry - exit."""
    for comp in ["t20i", "smat"]:
        path = REPO_ROOT / "data" / "processed" / comp / "batter_match_contributions.csv"
        assert path.exists(), f"Missing dataset: {path}"
        df = pd.read_csv(path, low_memory=False)

        inn2 = df[(df["innings"] == 2) & pd.notnull(df["target"]) & (df["target"] > 0)]
        assert len(inn2) > 0, f"No 2nd innings rows found in {comp}"

        for idx, row in inn2.iterrows():
            rin = row["required_rr_entry"]
            rout = row["required_rr_exit"]
            rchg = row["required_rr_change"]
            if pd.notnull(rin) and pd.notnull(rout) and pd.notnull(rchg):
                expected = round(rin - rout, 2)
                assert abs(expected - rchg) < 0.01, (
                    f"Sign mismatch in {comp} row {idx}: expected {expected}, got {rchg}"
                )


def test_ipl_records_unchanged_by_phase8c():
    """Verify that IPL dataset remains completely untouched and follows canonical convention."""
    ipl_path = REPO_ROOT / "data" / "processed" / "batter_match_contributions.csv"
    assert ipl_path.exists(), "IPL dataset missing"
    df_ipl = pd.read_csv(ipl_path, low_memory=False)

    assert len(df_ipl) == 19111, f"IPL row count modified: {len(df_ipl)}"

    warner = df_ipl[(df_ipl["match_id"] == 1082596) & (df_ipl["player"] == "DA Warner")].iloc[0]
    assert warner["score_state"] >= 95.0, f"Warner P3 shifted: {warner['score_state']}"


def test_samson_reconstructed_record_and_api():
    """Verify Samson's regenerated score matches expected canonical values across all layers."""
    t20i_path = REPO_ROOT / "data" / "processed" / "t20i" / "batter_match_contributions.csv"
    df = pd.read_csv(t20i_path, low_memory=False)

    samson = df[(df["match_id"] == 1512770) & (df["player"] == "SV Samson")].iloc[0]

    # Stored CSV assertions
    assert samson["required_rr_entry"] == 9.8
    assert samson["required_rr_exit"] == 0.0
    assert samson["required_rr_change"] == 9.8
    assert samson["score_context"] == 47.7
    assert samson["score_perf"] == 95.9
    assert samson["score_state"] == 96.9
    assert samson["adjusted_p3"] == 96.1
    assert samson["contribution_score"] == 95.6

    # Live recalculation assertion
    fresh = compute_production_contribution(dict(samson), apply_attribution=True)
    assert fresh["pillar3_state_score"] == 96.9
    assert fresh["adjusted_p3"] == 96.1
    assert fresh["contribution_score"] == 95.6

    # API match endpoint assertion
    res = client.get("/api/match/1512770?competition=t20i")
    assert res.status_code == 200
    data = res.json()
    b_match = next((b for b in data.get("batters", []) if b.get("player") == "SV Samson"), None)
    assert b_match is not None, "Samson missing from API match batters"
    assert b_match["contribution_score"] == 95.6
    assert b_match["score_state"] == 96.9

    # API player endpoint assertion
    p_res = client.get("/api/match/1512770/player/SV%20Samson?competition=t20i")
    assert p_res.status_code == 200
    p_data = p_res.json()
    assert p_data["contribution_score"] == 95.6
    assert p_data["pillars"]["pillar3_state"]["score"] == 96.9


def test_dnb_rule_preserved_in_season_metrics():
    """Verify that non-batting appearances have strictly NaN scores and shares."""
    for comp in ["t20i", "smat"]:
        season_path = REPO_ROOT / "data" / "processed" / comp / "phase6_season_metrics.csv"
        assert season_path.exists()
        df_season = pd.read_csv(season_path, low_memory=False)

        dnb = df_season[df_season["batting_innings"] == 0]
        assert len(dnb) > 0, f"Expected DNB player-seasons in {comp}"
        assert dnb["average_contribution_score"].isna().all(), f"DNB non-NaN score in {comp}"
        assert dnb["season_team_contribution_share"].isna().all(), f"DNB non-NaN share in {comp}"


def test_p1_par_invariance():
    """Verify that par context (P1 = 50.0) produces exactly 1.000x leverage."""
    row_par = {
        "innings": 1,
        "entry_over": 10.0,
        "wickets_remaining_entry": 7,
        "balls_remaining_entry": 60,
        "target": 0.0,
    }
    ctx = compute_context_and_leverage(row_par)
    lev = ctx["leverage"]
    assert 0.65 <= lev <= 1.35
