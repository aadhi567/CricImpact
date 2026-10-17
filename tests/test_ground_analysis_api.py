"""
Tests for Ground Analysis API endpoints and aggregation logic.
Validates:
- Country and venue filtering.
- Competition filtering (IPL, T20I, Combined).
- Rolling five-year date boundaries and all-time boundaries.
- First- and second-innings score aggregation (average, median, min, max, exclusion of DLS/rain shortened innings).
- Defend vs Chase outcome classification (verifying winner matches batting 1st vs batting 2nd).
- Ties, super overs, no-results, and DLS handling.
- Denominator correctness for win percentages (decided matches only).
- Historical winning score benchmarks.
- Error handling (invalid competition, invalid period, invalid date ranges, unknown venue 404).
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.ground_service import (
    ground_service,
    DLS_MATCH_IDS,
    SUPER_OVER_MATCH_IDS,
    NO_RESULT_MATCH_IDS,
)

client = TestClient(app)


def test_get_ground_analysis_venues_combined():
    """Test retrieving venue list for combined competitions."""
    res = client.get("/api/ground-analysis/venues?competition=combined")
    assert res.status_code == 200
    data = res.json()
    assert data["competition"] == "combined"
    assert len(data["venues"]) > 50
    assert len(data["countries"]) >= 20
    assert data["default_venue"] == "Wankhede Stadium, Mumbai"

    # Verify Wankhede is in venue list and has both IPL and T20I counts
    wankhede = next((v for v in data["venues"] if v["id"] == "Wankhede Stadium, Mumbai"), None)
    assert wankhede is not None
    assert wankhede["ipl_matches"] > 0
    assert wankhede["t20i_matches"] > 0
    assert wankhede["total_matches"] == wankhede["ipl_matches"] + wankhede["t20i_matches"]


def test_get_ground_analysis_venues_competition_filtering():
    """Test that venues update based on IPL vs T20I competition filter."""
    # IPL only
    res_ipl = client.get("/api/ground-analysis/venues?competition=ipl")
    assert res_ipl.status_code == 200
    data_ipl = res_ipl.json()
    assert data_ipl["competition"] == "ipl"
    # All venues in IPL filter should have at least 1 IPL match
    for v in data_ipl["venues"]:
        assert v["ipl_matches"] > 0

    # T20I only
    res_t20i = client.get("/api/ground-analysis/venues?competition=t20i")
    assert res_t20i.status_code == 200
    data_t20i = res_t20i.json()
    assert data_t20i["competition"] == "t20i"
    for v in data_t20i["venues"]:
        assert v["t20i_matches"] > 0


def test_get_ground_analysis_venues_country_filtering():
    """Test filtering venues by country."""
    res = client.get("/api/ground-analysis/venues?competition=combined&country=Australia")
    assert res.status_code == 200
    data = res.json()
    assert data["selected_country"] == "Australia"
    for v in data["venues"]:
        assert v["country"] == "Australia"
    # Ensure Melbourne Cricket Ground is present
    mcg = next((v for v in data["venues"] if "Melbourne" in v["name"]), None)
    assert mcg is not None


def test_get_ground_analysis_detail_wankhede_rolling_5yr():
    """Test ground analysis calculation for Wankhede Stadium with default 5-year rolling window."""
    res = client.get("/api/ground-analysis/venue/Wankhede Stadium, Mumbai?competition=combined&period=rolling_5yr")
    assert res.status_code == 200
    data = res.json()

    # 1. Venue info & summary
    assert data["venue_info"]["name"] == "Wankhede Stadium, Mumbai"
    assert data["venue_info"]["city"] == "Mumbai"
    assert data["venue_info"]["country"] == "India"
    assert data["summary"]["total_matches_in_period"] > 0
    assert data["summary"]["total_matches_all_time"] >= data["summary"]["total_matches_in_period"]
    assert "data_coverage_notice" in data["summary"]

    # 2. Scoring Profile
    p1 = data["scoring_profile"]["first_innings"]
    p2 = data["scoring_profile"]["second_innings"]
    assert p1["sample_count"] > 0
    assert p1["avg_score"] > 140
    assert p1["median_score"] > 140
    assert p1["highest"]["runs"] >= p1["lowest"]["runs"]
    assert p2["sample_count"] > 0
    assert p2["highest"]["runs"] >= p2["lowest"]["runs"]
    assert "rain/DLS" in p1["eligibility_note"]

    # 3. Chase vs Defend
    cd = data["chase_vs_defend"]
    assert cd["total_matches"] == data["summary"]["total_matches_in_period"]
    assert cd["decided_matches"] == cd["defend_wins"] + cd["chase_wins"]
    if cd["decided_matches"] > 0:
        assert round(cd["defend_pct"] + cd["chase_pct"], 1) == 100.0

    # Denominator check: ties and no results are NOT in decided_matches
    assert cd["total_matches"] == cd["decided_matches"] + cd["ties_super_overs"] + cd["no_results_abandoned"]

    # 4. Benchmarks
    b = data["historical_winning_scores"]
    assert b["sample_adequate"] is True
    assert b["lowest_successful_defense"] is not None
    assert b["lowest_successful_chase"] is not None
    assert b["highest_successful_chase"] is not None
    assert b["typical_winning_score"]["overall_median"] is not None

    # 5. Year Trends
    assert len(data["year_trends"]) > 0
    for yt in data["year_trends"]:
        assert yt["matches"] >= yt["decided_matches"]
        assert yt["decided_matches"] == yt["defend_wins"] + yt["chase_wins"]

    # 6. Recent Matches
    assert len(data["recent_matches"]) > 0
    assert len(data["recent_matches"]) <= 50
    # Matches must be sorted newest first
    dates = [m["date"] for m in data["recent_matches"]]
    assert dates == sorted(dates, reverse=True)


def test_get_ground_analysis_all_time_period():
    """Test analysis with all_time period to verify full span coverage."""
    res_5yr = client.get("/api/ground-analysis/venue/Wankhede Stadium, Mumbai?period=rolling_5yr")
    res_all = client.get("/api/ground-analysis/venue/Wankhede Stadium, Mumbai?period=all_time")

    assert res_5yr.status_code == 200
    assert res_all.status_code == 200

    d_5yr = res_5yr.json()
    d_all = res_all.json()

    assert d_all["summary"]["total_matches_in_period"] == d_all["summary"]["total_matches_all_time"]
    assert d_all["summary"]["total_matches_in_period"] >= d_5yr["summary"]["total_matches_in_period"]
    assert d_all["summary"]["earliest_date_in_scope"] == d_all["summary"]["dataset_earliest_date"]


def test_outcome_classification_correctness():
    """Verify that defend vs chase classification correctly attributes winners based on batting order."""
    res = client.get("/api/ground-analysis/venue/Wankhede Stadium, Mumbai?period=all_time")
    assert res.status_code == 200
    matches = res.json()["recent_matches"]

    for m in matches:
        if m["is_no_result"]:
            assert m["result_type"] == "no_result"
        elif m["is_super_over"]:
            assert m["result_type"] == "tie_super_over"
        elif m["winner"] and m["winner"] != "N/A":
            if m["winner"] == m["innings1_team"]:
                assert m["result_type"] == "defend_win"
            elif m["winner"] == m["innings2_team"]:
                assert m["result_type"] == "chase_win"


def test_rain_shortened_and_dls_excluded_from_standard_profile():
    """Verify that matches identified as DLS are excluded from the standard 20-over scoring profile."""
    # Find a venue with DLS matches, e.g. Eden Gardens or M Chinnaswamy Stadium
    res = client.get("/api/ground-analysis/venue/M Chinnaswamy Stadium, Bengaluru?period=all_time")
    assert res.status_code == 200
    data = res.json()

    # Look for any DLS match in recent matches
    dls_in_matches = [m for m in data["recent_matches"] if m["is_dls"]]
    for dls_m in dls_in_matches:
        assert dls_m["match_id"] in DLS_MATCH_IDS

    # Highest and lowest benchmarks should not be a DLS match
    if data["historical_winning_scores"]["lowest_successful_defense"]:
        assert data["historical_winning_scores"]["lowest_successful_defense"]["match_id"] not in DLS_MATCH_IDS
    if data["historical_winning_scores"]["highest_successful_chase"]:
        assert data["historical_winning_scores"]["highest_successful_chase"]["match_id"] not in DLS_MATCH_IDS


def test_alias_matching_resolves_to_canonical():
    """Test that requesting a venue with a raw alias returns the canonical venue."""
    res = client.get("/api/ground-analysis/venue/Wankhede Stadium")
    assert res.status_code == 200
    data = res.json()
    assert data["venue_info"]["name"] == "Wankhede Stadium, Mumbai"


def test_unknown_venue_returns_404():
    """Test that requesting an unknown venue returns 404."""
    res = client.get("/api/ground-analysis/venue/NonExistentStadiumXYZ")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_invalid_parameters_error_handling():
    """Test error handling for invalid competition, period, or date parameters."""
    # Invalid competition
    res_comp = client.get("/api/ground-analysis/venues?competition=invalid_league")
    assert res_comp.status_code == 400

    # Invalid period
    res_period = client.get("/api/ground-analysis/venue/Wankhede Stadium, Mumbai?period=invalid_period")
    assert res_period.status_code == 400

    # Invalid date bounds: start_date > end_date
    res_dates = client.get(
        "/api/ground-analysis/venue/Wankhede Stadium, Mumbai?period=custom&start_date=2025-01-01&end_date=2024-01-01"
    )
    assert res_dates.status_code == 400
    assert "cannot be after" in res_dates.json()["detail"]


def test_empty_matches_venue_sample_adequate_flag():
    """Test that a venue with < 3 matches sets sample_adequate=False with an informative warning."""
    # Query a low sample venue if available, or test helper
    venues_res = client.get("/api/ground-analysis/venues?competition=t20i")
    assert venues_res.status_code == 200
    venues = venues_res.json()["venues"]
    low_sample_v = next((v for v in venues if v["total_matches"] < 3), None)

    if low_sample_v:
        detail_res = client.get(f"/api/ground-analysis/venue/{low_sample_v['id']}?competition=t20i&period=all_time")
        assert detail_res.status_code == 200
        d = detail_res.json()
        assert d["historical_winning_scores"]["sample_adequate"] is False
        assert "Limited match sample size" in d["historical_winning_scores"]["warning"]


def test_phase_analysis_structure_and_scope_disclosure():
    """Verify that phase_analysis is returned with correct scope_summary and phase keys."""
    res = client.get("/api/ground-analysis/venue/Wankhede Stadium, Mumbai?competition=combined&period=rolling_5yr")
    assert res.status_code == 200
    data = res.json()
    assert "phase_analysis" in data
    pa = data["phase_analysis"]

    # Scope summary checks
    assert "scope_summary" in pa
    scope = pa["scope_summary"]
    assert "total_matches_in_period" in scope
    assert "eligible_standard_matches" in scope
    assert "excluded_matches" in scope
    assert "unknown_matches" in scope
    assert "disclosure_text" in scope
    assert scope["total_matches_in_period"] == scope["eligible_standard_matches"] + scope["excluded_matches"] + scope["unknown_matches"]
    assert "standard 20-over matches" in scope["disclosure_text"]

    # Innings views presence
    for view in ("first_innings", "second_innings", "combined"):
        assert view in pa
        assert "powerplay" in pa[view]
        assert "middle" in pa[view]
        assert "death" in pa[view]

        # Verify each card has required attributes
        for ph in ("powerplay", "middle", "death"):
            card = pa[view][ph]
            assert "phase_id" in card
            assert "phase_name" in card
            assert "overs_range" in card
            assert "avg_runs" in card
            assert "median_runs" in card
            assert "run_rate" in card
            assert "avg_wickets" in card
            assert "dot_percentage" in card
            assert "boundary_percentage" in card
            assert "highest" in card
            assert "lowest" in card
            assert "sample_innings" in card
            assert "sample_matches" in card


def test_phase_metrics_calculations():
    """Verify that phase metric values and percentages fall within expected cricket mathematical bounds."""
    res = client.get("/api/ground-analysis/venue/Wankhede Stadium, Mumbai?competition=combined&period=rolling_5yr")
    assert res.status_code == 200
    pa = res.json()["phase_analysis"]
    comb = pa["combined"]

    for ph_key in ("powerplay", "middle", "death"):
        ph = comb[ph_key]
        if ph["sample_innings"] > 0:
            assert ph["avg_runs"] > 0
            assert ph["median_runs"] > 0
            assert ph["run_rate"] > 0
            assert 0.0 <= ph["dot_percentage"] <= 100.0
            assert 0.0 <= ph["boundary_percentage"] <= 100.0
            assert ph["highest"]["runs"] >= ph["lowest"]["runs"]
            assert ph["highest"]["runs"] >= ph["median_runs"]
            assert ph["lowest"]["runs"] <= ph["median_runs"]
            # Check context fields in highest/lowest
            assert "score_str" in ph["highest"]
            assert "opponent" in ph["highest"]
            assert "date" in ph["highest"]
            assert "match_id" in ph["highest"]


def test_unplayed_phase_exclusion():
    """Verify that unplayed phases (e.g. death overs not reached in chase) are excluded rather than counted as 0 runs."""
    res = client.get("/api/ground-analysis/venue/Wankhede Stadium, Mumbai?competition=combined&period=all_time")
    assert res.status_code == 200
    pa = res.json()["phase_analysis"]
    inn2 = pa["second_innings"]

    # In 2nd innings, some matches finish before death overs (overs 16-20).
    # Thus, powerplay sample_innings must be >= death overs sample_innings
    assert inn2["powerplay"]["sample_innings"] >= inn2["death"]["sample_innings"]

    # Lowest death score should NEVER be 0 if only played phases are included
    if inn2["death"]["sample_innings"] > 0:
        assert inn2["death"]["lowest"]["runs"] > 0
        assert inn2["death"]["avg_runs"] > 10.0


def test_rain_and_reduced_matches_excluded_from_phase_averages():
    """Verify that rain-shortened/DLS matches are excluded from phase averages but marked in recent matches."""
    res = client.get("/api/ground-analysis/venue/M Chinnaswamy Stadium, Bengaluru?competition=ipl&period=all_time")
    assert res.status_code == 200
    data = res.json()
    pa = data["phase_analysis"]
    scope = pa["scope_summary"]

    # Chinnaswamy has documented rain/DLS matches in IPL history
    assert scope["excluded_matches"] > 0
    assert scope["eligible_standard_matches"] < scope["total_matches_in_period"]

    # Verify that recent_matches has condition_label and is_standard_20ov
    for m in data["recent_matches"]:
        assert "condition_label" in m
        assert "is_standard_20ov" in m
        if m["is_dls"]:
            assert m["is_standard_20ov"] is False
            assert "Rain-interrupted" in m["condition_label"] or "DLS" in m["condition_label"]

    # Highest and lowest in phase analysis must not belong to DLS matches
    for view in ("first_innings", "second_innings", "combined"):
        for ph in ("powerplay", "middle", "death"):
            h = pa[view][ph]["highest"]
            l = pa[view][ph]["lowest"]
            if h:
                assert str(h["match_id"]) not in DLS_MATCH_IDS
            if l:
                assert str(l["match_id"]) not in DLS_MATCH_IDS


def test_phase_innings_views_separation():
    """Verify that 1st innings, 2nd innings, and combined phase profiles are distinct."""
    res = client.get("/api/ground-analysis/venue/Wankhede Stadium, Mumbai?competition=combined&period=all_time")
    assert res.status_code == 200
    pa = res.json()["phase_analysis"]

    inn1_pp = pa["first_innings"]["powerplay"]
    inn2_pp = pa["second_innings"]["powerplay"]
    comb_pp = pa["combined"]["powerplay"]

    # Sample innings: combined should equal inn1 + inn2 (when both innings are standard)
    assert comb_pp["sample_innings"] == inn1_pp["sample_innings"] + inn2_pp["sample_innings"]

    # Comparison chart checks
    chart = pa["comparison_chart"]
    assert len(chart) == 3  # powerplay, middle, death
    for item in chart:
        assert "phase_id" in item
        assert "phase_name" in item
        assert "first_innings_avg_runs" in item
        assert "second_innings_avg_runs" in item
        assert "combined_avg_runs" in item
        assert "first_innings_run_rate" in item
        assert "second_innings_run_rate" in item


def test_progression_insights_and_year_trends():
    """Verify progression insights and annual phase trends structure."""
    res = client.get("/api/ground-analysis/venue/Wankhede Stadium, Mumbai?competition=combined&period=rolling_5yr")
    assert res.status_code == 200
    pa = res.json()["phase_analysis"]

    insights = pa["progression_insights"]
    assert "powerplay_run_rate" in insights
    assert "middle_run_rate" in insights
    assert "death_run_rate" in insights
    assert "rate_insight" in insights
    assert "wicket_insight" in insights
    assert "context_note" in insights
    assert "tactical phase approaches" in insights["context_note"]
    assert insights["is_reliable"] is True

    # Year trends checks
    trends = pa["year_trends"]
    assert len(trends) > 0
    for yr_data in trends:
        assert "year" in yr_data
        assert "matches" in yr_data
        assert "powerplay_avg_runs" in yr_data
        assert "middle_avg_runs" in yr_data
        assert "death_avg_runs" in yr_data


def test_death_phase_at_point_one_overs_excluded():
    """Prove that a death phase ending at 0.1 overs (or any <5.0 overs) is strictly excluded."""
    # Query Wankhede Stadium all-time and check Death Overs
    res = client.get("/api/ground-analysis/venue/Wankhede Stadium, Mumbai?competition=combined&period=all_time")
    assert res.status_code == 200
    pa = res.json()["phase_analysis"]

    for view in ("first_innings", "second_innings", "combined"):
        death_card = pa[view]["death"]
        if death_card["sample_innings"] > 0:
            # Lowest death score must be a full 5-over phase (30 legal balls, 5.0 ov)
            assert death_card["lowest"]["legal_balls"] >= 30
            assert death_card["lowest"]["overs_str"] == "5.0 ov"
            # It must not be an incomplete 0.1 over or early chase ending
            assert death_card["lowest"]["runs"] >= 15
            assert "0.1 ov" not in death_card["lowest"]["score_str"]
            assert "0.2 ov" not in death_card["lowest"]["score_str"]

    # Verify directly via phase summaries that match 1082636 (where 2nd inn death was 2/0 in 0.1 ov) has complete=False
    phases_data = ground_service._phases_data.get("phases", {})
    m_1082636 = phases_data.get("1082636", {}).get("2", {}).get("death", {})
    assert m_1082636.get("legal_balls") == 1
    assert m_1082636.get("complete") is False


def test_death_phase_completed_for_all_five_overs_is_eligible():
    """Prove that a death phase completed for all five overs (30 legal balls) is eligible."""
    res = client.get("/api/ground-analysis/venue/Wankhede Stadium, Mumbai?competition=combined&period=all_time")
    assert res.status_code == 200
    pa = res.json()["phase_analysis"]

    # 1st innings matches that lasted 20 overs have full 5-over death phases
    inn1_death = pa["first_innings"]["death"]
    assert inn1_death["sample_innings"] > 0
    assert inn1_death["highest"]["legal_balls"] >= 30
    assert inn1_death["highest"]["overs_str"] == "5.0 ov"
    assert inn1_death["lowest"]["legal_balls"] >= 30
    assert inn1_death["lowest"]["overs_str"] == "5.0 ov"
    assert inn1_death["avg_runs"] > 30.0


def test_chase_ending_in_death_overs_contributes_completed_pp_and_middle_not_death():
    """Prove that a chase ending at 18.x overs contributes completed Powerplay and Middle Overs but not Death Overs."""
    # Match 1082600 chased down the target at 18.4 overs
    phases_data = ground_service._phases_data.get("phases", {})
    inn2_phases = phases_data.get("1082600", {}).get("2", {})

    # Powerplay was fully completed (overs 1-6)
    assert inn2_phases["powerplay"]["complete"] is True
    assert inn2_phases["powerplay"]["legal_balls"] == 36

    # Middle Overs was fully completed (overs 7-15)
    assert inn2_phases["middle"]["complete"] is True
    assert inn2_phases["middle"]["legal_balls"] == 54

    # Death Overs was incomplete (ended at 18.4 overs, 22 legal balls)
    assert inn2_phases["death"]["complete"] is False
    assert inn2_phases["death"]["legal_balls"] < 30


def test_all_out_innings_contributes_completed_earlier_phases_not_unplayed():
    """Prove that an innings bowled all-out in middle overs contributes completed Powerplay but not Middle or Death."""
    # Match 1082617 inn 2 was bowled all out at 9.4 overs
    phases_data = ground_service._phases_data.get("phases", {})
    inn2_phases = phases_data.get("1082617", {}).get("2", {})

    # Powerplay was fully completed
    assert inn2_phases["powerplay"]["complete"] is True
    assert inn2_phases["powerplay"]["legal_balls"] == 36

    # Middle Overs was terminated by all-out at 9.4 overs before completing over 15
    assert inn2_phases["middle"]["complete"] is False
    assert inn2_phases["middle"]["legal_balls"] < 54

    # Death Overs was not played
    assert inn2_phases.get("death", {}).get("complete", False) is False


def test_rain_reduced_matches_remain_excluded_from_standard_phase_statistics():
    """Prove that rain-reduced matches remain strictly excluded from standard 20-over phase statistics."""
    # Verify via phase data that DLS match 336022 has complete=False across all phases
    phases_data = ground_service._phases_data.get("phases", {})
    conditions = ground_service._phases_data.get("conditions", {})

    assert conditions.get("336022", {}).get("is_standard_20ov") is False
    for inn in ("1", "2"):
        for ph in ("powerplay", "middle", "death"):
            p_rec = phases_data.get("336022", {}).get(inn, {}).get(ph, {})
            if p_rec:
                assert p_rec.get("complete") is False


def test_metrics_consistency_across_all_metrics():
    """Prove that averages, medians, highest/lowest scores, run rates, wickets, and percentages use identical eligibility."""
    res = client.get("/api/ground-analysis/venue/Wankhede Stadium, Mumbai?competition=combined&period=all_time")
    assert res.status_code == 200
    pa = res.json()["phase_analysis"]

    # Natural progression: Innings that complete Death <= Innings that complete Middle <= Innings that complete PP
    inn2 = pa["second_innings"]
    assert inn2["powerplay"]["sample_innings"] >= inn2["middle"]["sample_innings"]
    assert inn2["middle"]["sample_innings"] >= inn2["death"]["sample_innings"]

    for view in ("first_innings", "second_innings", "combined"):
        for ph in ("powerplay", "middle", "death"):
            card = pa[view][ph]
            if card["sample_innings"] > 0:
                # All metrics are computed and non-null
                assert card["avg_runs"] is not None
                assert card["median_runs"] is not None
                assert card["run_rate"] is not None
                assert card["avg_wickets"] is not None
                assert card["dot_percentage"] is not None
                assert card["boundary_percentage"] is not None
                assert card["highest"] is not None
                assert card["lowest"] is not None
                # Both highest and lowest have complete overs
                if ph == "powerplay":
                    assert card["highest"]["legal_balls"] >= 35
                    assert card["lowest"]["legal_balls"] >= 35
                elif ph == "middle":
                    assert card["highest"]["legal_balls"] >= 53
                    assert card["lowest"]["legal_balls"] >= 53
                elif ph == "death":
                    assert card["highest"]["legal_balls"] >= 30
                    assert card["lowest"]["legal_balls"] >= 30
