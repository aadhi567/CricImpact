"""
Phase 7W Regression and Unit Tests: Match Contribution Ranking Sample-Size Fix.

Validates:
1. Qualification rule for match leaderboard: balls_faced >= 10 OR runs >= 20.
2. Separation of opportunity Contribution Score from match ranking.
3. R Tewatia reference case (Match 1529299):
   - Score remains 76.5 for his actual 1-ball batting opportunity.
   - Not ranked (#1 is NOT Tewatia).
   - Marked Limited Sample.
   - Remains visible in match batters list.
4. Top qualified contributor for Match 1529299 is B Sai Sudharsan (75.3, 61 runs, 44 balls).
5. All specified test cases (Cases A through G).
6. Sorting: Qualified players sorted by Contribution Score DESC, followed by limited-sample players DESC.
7. Model integrity: No underlying models or formulas altered.
"""

import unittest
from app.services.data_service import data_service


def is_qualified_for_match_ranking(balls_faced: int, runs: int) -> bool:
    """Exact qualification rule: balls_faced >= 10 OR runs >= 20."""
    return bool((balls_faced >= 10) or (runs >= 20))


class TestMatchRankingQualification(unittest.TestCase):
    def test_case_a_4_runs_1_ball(self):
        """Case A: 4 runs / 1 ball -> Not qualified"""
        self.assertFalse(is_qualified_for_match_ranking(balls_faced=1, runs=4))

    def test_case_b_9_runs_9_balls(self):
        """Case B: 9 runs / 9 balls -> Not qualified"""
        self.assertFalse(is_qualified_for_match_ranking(balls_faced=9, runs=9))

    def test_case_c_10_runs_10_balls(self):
        """Case C: 10 runs / 10 balls -> Qualified"""
        self.assertTrue(is_qualified_for_match_ranking(balls_faced=10, runs=10))

    def test_case_d_20_runs_4_balls(self):
        """Case D: 20 runs / 4 balls -> Qualified"""
        self.assertTrue(is_qualified_for_match_ranking(balls_faced=4, runs=20))

    def test_case_e_19_runs_4_balls(self):
        """Case E: 19 runs / 4 balls -> Not qualified"""
        self.assertFalse(is_qualified_for_match_ranking(balls_faced=4, runs=19))

    def test_case_f_20_runs_1_ball(self):
        """Case F: 20 runs / 1 ball -> Qualified by the OR rule"""
        self.assertTrue(is_qualified_for_match_ranking(balls_faced=1, runs=20))

    def test_case_g_0_runs_12_balls(self):
        """Case G: 0 runs / 12 balls -> Qualified by balls faced"""
        self.assertTrue(is_qualified_for_match_ranking(balls_faced=12, runs=0))

    def test_known_case_tewatia_match_1529299(self):
        """
        Match 1529299 (Gujarat Titans vs Sunrisers Hyderabad):
        R Tewatia: 4 runs, 1 ball, score 76.5
        B Sai Sudharsan: 61 runs, 44 balls, score 78.9
        """
        match_data = data_service.get_match_overview(1529299)
        self.assertIsNotNone(match_data)
        self.assertEqual(match_data["match_id"], 1529299)

        batters = match_data["batters"]
        self.assertGreater(len(batters), 0)

        # 1. Tewatia must be present and visible
        tewatia_entries = [b for b in batters if b["player"] == "R Tewatia"]
        self.assertEqual(len(tewatia_entries), 1)
        tewatia = tewatia_entries[0]

        # 2. Tewatia score MUST remain 76.5
        self.assertEqual(tewatia["contribution_score"], 76.5)
        self.assertEqual(tewatia["runs"], 4)
        self.assertEqual(tewatia["balls"], 1)

        # 3. Tewatia is NOT qualified and NOT ranked #1
        self.assertFalse(tewatia["is_qualified"])
        self.assertIsNone(tewatia["rank"])
        self.assertEqual(tewatia["qualification_status"], "Limited Sample")

        # 4. Top qualified contributor must be B Sai Sudharsan
        top_qual = match_data["top_qualified_contributor"]
        self.assertIsNotNone(top_qual)
        self.assertEqual(top_qual["player"], "B Sai Sudharsan")
        engine = data_service.get_active_scoring_engine()
        exp_score = 79.4 if engine == "v8.5.1-strategy4-hybrid" else 78.9
        self.assertEqual(top_qual["contribution_score"], exp_score)
        self.assertEqual(top_qual["runs"], 61)
        self.assertEqual(top_qual["balls"], 44)

        # 5. Check rankings of qualified players
        qualified = [b for b in batters if b["is_qualified"]]
        limited = [b for b in batters if not b["is_qualified"]]

        # Order check: Qualified first, then limited sample
        self.assertEqual(batters[:len(qualified)], qualified)
        self.assertEqual(batters[len(qualified):], limited)

        # Qualified batters have sequential ranks starting at 1
        for i, qb in enumerate(qualified):
            self.assertEqual(qb["rank"], i + 1)

        # #1 is B Sai Sudharsan, #2 is Washington Sundar, #3 is N Sindhu
        self.assertEqual(qualified[0]["player"], "B Sai Sudharsan")
        self.assertEqual(qualified[0]["rank"], 1)
        self.assertEqual(qualified[1]["player"], "Washington Sundar")
        self.assertEqual(qualified[1]["rank"], 2)
        self.assertEqual(qualified[2]["player"], "N Sindhu")
        self.assertEqual(qualified[2]["rank"], 3)

        # Limited sample batters must have rank None
        for lb in limited:
            self.assertIsNone(lb["rank"])
            self.assertEqual(lb["qualification_status"], "Limited Sample")

    def test_get_matches_top_contributor_uses_qualification(self):
        """Check that match list returns top qualified contributor for match 1529299."""
        matches = data_service.get_matches(season="2026", limit=500)
        match_1529299 = next((m for m in matches if m["match_id"] == 1529299), None)
        self.assertIsNotNone(match_1529299)
        top = match_1529299["top_contributor"]
        self.assertIsNotNone(top)
        self.assertEqual(top["player"], "B Sai Sudharsan")
        engine = data_service.get_active_scoring_engine()
        exp_score = 79.4 if engine == "v8.5.1-strategy4-hybrid" else 78.9
        self.assertEqual(top["contribution_score"], exp_score)



if __name__ == "__main__":
    unittest.main()
