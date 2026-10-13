import re
import pytest
from app.services.data_service import data_service


def test_api_values_shahrukh_khan():
    """Verify backend API values for Shahrukh Khan (match 1254065)."""
    detail = data_service.get_match_detail("1254065", "M Shahrukh Khan", "ipl")
    assert detail is not None
    assert detail["player"] == "M Shahrukh Khan"
    assert detail["is_dnb"] is False

    engine = data_service.get_active_scoring_engine()
    if engine == "v8.5.1-strategy4-hybrid":
        assert detail["contribution_score"] == 63.7
    else:
        assert detail["contribution_score"] == 53.6

    # Check P2
    p2 = detail["pillars"]["pillar2_performance"]["score"]
    assert p2 == 77.1
    assert detail["adjusted_p2"] == 82.8

    # Check P3
    p3 = detail["pillars"]["pillar3_state"]["score"]
    if engine == "v8.5.1-strategy4-hybrid":
        assert p3 == 45.5
        assert detail["adjusted_p3"] == 44.5
    else:
        assert p3 == 28.8
        assert detail["adjusted_p3"] == 24.3

    # Check P1 & leverage
    p1 = detail["pillars"]["pillar1_context"]["score"]
    assert p1 == 72.0
    assert abs(detail["p1_leverage"] - 1.212) < 0.01

    # Check 50/50 math
    expected_score = round(0.5 * detail["adjusted_p2"] + 0.5 * detail["adjusted_p3"], 1)
    assert abs(detail["contribution_score"] - expected_score) <= 0.15

    # Basic stats
    basic = detail["basic_performance"]
    assert basic["runs"] == 47
    assert basic["balls"] == 36
    assert basic["strike_rate"] == 130.6
    assert basic["fours"] == 4
    assert basic["sixes"] == 2


def test_api_values_sai_sudharsan():
    """Verify backend API values for B Sai Sudharsan (match 1359536)."""
    detail = data_service.get_match_detail("1359536", "B Sai Sudharsan", "ipl")
    assert detail is not None
    assert detail["player"] == "B Sai Sudharsan"
    assert detail["contribution_score"] == 93.4
    assert detail["is_dnb"] is False

    engine = data_service.get_active_scoring_engine()
    p2 = detail["pillars"]["pillar2_performance"]["score"]
    assert p2 == 82.9
    assert detail["adjusted_p2"] == 86.9

    p3 = detail["pillars"]["pillar3_state"]["score"]
    if engine == "v8.5.1-strategy4-hybrid":
        assert p3 == 96.3
    else:
        assert p3 == 96.7
    assert detail["adjusted_p3"] == 99.9


    basic = detail["basic_performance"]
    assert basic["runs"] == 47
    assert basic["balls"] == 36


def test_api_values_chase_match():
    """Verify backend API handles 2nd innings chase match."""
    detail = data_service.get_match_detail("1082591", "CH Gayle", "ipl")
    assert detail is not None
    assert detail["match_context"]["innings"] == 2
    assert detail["match_context"]["target"] == 208
    assert detail["contribution_score"] is not None
    assert 0 <= detail["contribution_score"] <= 100


def test_api_values_dnb_preservation():
    """Verify DNB matches return is_dnb=True and null contribution score."""
    detail = data_service.get_match_detail("1082591", "NV Ojha", "ipl")
    assert detail is not None
    assert detail["is_dnb"] is True
    assert "contribution_score" not in detail or detail.get("contribution_score") is None


def test_frontend_match_detail_three_primary_sections():
    """Verify MatchDetail.jsx contains exactly the three requested primary sections."""
    with open("frontend/src/pages/MatchDetail.jsx", "r", encoding="utf-8") as f:
        content = f.read()

    # Must contain section 1, 2, and 3
    assert "1. Batting Performance" in content, "Missing Section 1: Batting Performance"
    assert "2. Team Contribution" in content, "Missing Section 2: Team Contribution"
    assert "3. Overall Performance" in content, "Missing Section 3: Overall Performance"

    # Verify no other primary sections exist
    section_headers = re.findall(r'<h2[^>]*>\s*(\d+\.\s*[^<]+)</h2>', content)
    assert len(section_headers) == 3, f"Expected exactly 3 primary section h2 headers, got: {section_headers}"
    assert section_headers[0].strip() == "1. Batting Performance"
    assert section_headers[1].strip() == "2. Team Contribution"
    assert section_headers[2].strip() == "3. Overall Performance"


def test_frontend_match_detail_no_forbidden_fields():
    """Verify MatchDetail.jsx does not display expected runs, EFS, or observed-vs-attributed runs."""
    with open("frontend/src/pages/MatchDetail.jsx", "r", encoding="utf-8") as f:
        content = f.read()

    # Strictly forbidden UI terms
    forbidden_terms = [
        "expected runs",
        "expected batter runs",
        "expected_runs",
        "expected_sr",
        "run_deviation",
        "sr_deviation",
        "expected_final",
        "expected final score",
        "EFS",
        "observed-versus-attributed",
        "observed_versus_attributed",
        "Drag_ext",
        "external partner drag",
    ]
    for term in forbidden_terms:
        assert term.lower() not in content.lower(), f"Forbidden term '{term}' found in MatchDetail.jsx"


def test_frontend_match_detail_scores_out_of_100():
    """Verify MatchDetail.jsx shows P2, P3, and overall scores out of 100."""
    with open("frontend/src/pages/MatchDetail.jsx", "r", encoding="utf-8") as f:
        content = f.read()

    assert "/ 100" in content, "Scores must be explicitly shown out of 100"
    assert "50/50" in content, "Must explain the 50/50 weighting"
    assert "0.50 × Adjusted P2 + 0.50 × Adjusted P3" in content, "Must include 50/50 formula"
    assert "list-disc" in content, "Must use bullet points"
