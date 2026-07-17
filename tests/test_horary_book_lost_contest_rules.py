from __future__ import annotations

import sys
import unittest
from pathlib import Path


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.horary_engine.competition_doctrine import (  # noqa: E402
    evaluate_champion_defense_snapshot,
    evaluate_public_office_contest_snapshot,
)
from backend.horary_engine.lost_object_doctrine import (  # noqa: E402
    evaluate_lost_object_discovery_snapshot,
)
from backend.models import Aspect, Planet  # noqa: E402
from backend.question_analyzer import TraditionalHoraryQuestionAnalyzer  # noqa: E402
from backend.taxonomy import Category  # noqa: E402


class HoraryBookLostContestRulesTest(unittest.TestCase):
    def setUp(self):
        self.analyzer = TraditionalHoraryQuestionAnalyzer()

    def test_atm_card_question_routes_as_lost_object_document(self):
        analysis = self.analyzer.analyze_question("Where Is My ATM Card?")

        self.assertEqual(analysis["question_type"], Category.LOST_OBJECT)
        self.assertEqual(analysis["relevant_houses"], [1, 2])
        self.assertEqual(analysis["significators"]["quesited_house"], 2)
        self.assertEqual(analysis["significators"]["lost_object_family"], "discovery_timing")
        self.assertEqual(analysis["significators"]["natural_object_significator"], Planet.MERCURY)

    def test_passport_question_stays_lost_object_not_education(self):
        analysis = self.analyzer.analyze_question("Where's My Passport?")

        self.assertEqual(analysis["question_type"], Category.LOST_OBJECT)
        self.assertEqual(analysis["relevant_houses"], [1, 2])
        self.assertEqual(analysis["significators"]["quesited_house"], 2)
        self.assertEqual(analysis["significators"]["natural_object_significator"], Planet.MERCURY)
        self.assertEqual(analysis["significators"]["passport_family"], "passport_lost_document")
        self.assertEqual(analysis["significators"]["document_house"], 2)

    def test_romney_question_routes_as_public_office_contest(self):
        analysis = self.analyzer.analyze_question("Will Romney Win the US Presidency?")

        self.assertEqual(analysis["question_type"], Category.CAREER)
        self.assertEqual(analysis["relevant_houses"], [1, 10])
        self.assertEqual(analysis["significators"]["quesited_house"], 10)
        self.assertEqual(
            analysis["significators"]["competition_family"],
            "contest_public_office",
        )
        self.assertIsNone(analysis["immigration_analysis"])

    def test_champion_question_routes_as_title_defense(self):
        analysis = self.analyzer.analyze_question("Will the Champion Retain His Belt?")

        self.assertEqual(analysis["question_type"], Category.GENERAL)
        self.assertEqual(analysis["relevant_houses"], [10, 4])
        self.assertEqual(analysis["significators"]["querent_house"], 10)
        self.assertEqual(analysis["significators"]["quesited_house"], 4)
        self.assertEqual(
            analysis["significators"]["competition_family"],
            "contest_champion_vs_challenger",
        )

    def test_lost_object_snapshot_can_recover_under_beams_document(self):
        evaluation = evaluate_lost_object_discovery_snapshot(
            {
                "family": "discovery_timing",
                "object_type": "document",
                "object_name": "Mercury",
                "object_house": 6,
                "object_angularity": "cadent",
                "object_sign": "Libra",
                "object_dignity": -2,
                "object_retrograde": False,
                "object_solar_condition": "Under the Beams",
                "perfection_type": None,
                "traditional_strength": 0,
                "one_way": [],
                "moon_next_planet": None,
                "moon_next_aspect": None,
                "moon_next_applying": None,
                "moon_last_planet": Planet.VENUS,
                "moon_last_aspect": Aspect.SEXTILE,
                "natural_name": "Mercury",
                "natural_dignity": 1,
                "natural_house": 10,
            }
        )

        self.assertTrue(evaluation["applies"])
        self.assertEqual(evaluation["result"], "YES")

    def test_public_office_snapshot_denies_weaker_challenger(self):
        evaluation = evaluate_public_office_contest_snapshot(
            {
                "family": "contest_public_office",
                "candidate_name": "Mars",
                "candidate_dignity": -1,
                "candidate_house": 3,
                "candidate_retrograde": False,
                "office_name": "Sun",
                "office_dignity": 4,
                "office_house": 10,
                "office_retrograde": False,
                "moon_next_planet": "Sun",
                "moon_next_aspect": Aspect.TRINE,
                "moon_next_applying": True,
            }
        )

        self.assertTrue(evaluation["applies"])
        self.assertEqual(evaluation["result"], "NO")

    def test_champion_snapshot_supports_title_holder_advantage(self):
        evaluation = evaluate_champion_defense_snapshot(
            {
                "family": "contest_champion_vs_challenger",
                "champion_name": "Saturn",
                "champion_dignity": 3,
                "champion_house": 10,
                "champion_retrograde": False,
                "challenger_name": "Mars",
                "challenger_dignity": 0,
                "challenger_house": 4,
                "challenger_retrograde": True,
                "moon_next_planet": "Jupiter",
                "moon_next_aspect": Aspect.SEXTILE,
                "moon_next_applying": True,
            }
        )

        self.assertTrue(evaluation["applies"])
        self.assertEqual(evaluation["result"], "YES")


if __name__ == "__main__":
    unittest.main()
