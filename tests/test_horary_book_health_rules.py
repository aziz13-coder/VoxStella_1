from __future__ import annotations

import sys
import unittest
from pathlib import Path


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.horary_engine.health_doctrine import (  # noqa: E402
    analyze_health_question_text,
    evaluate_health_diagnosis_snapshot,
    evaluate_health_progression_snapshot,
)
from backend.horary_engine.pet_doctrine import (  # noqa: E402
    analyze_pet_question_text,
    evaluate_pet_recovery_snapshot,
)
from backend.models import Aspect, Planet, Sign  # noqa: E402
from backend.question_analyzer import TraditionalHoraryQuestionAnalyzer  # noqa: E402
from backend.taxonomy import Category  # noqa: E402


class HoraryBookHealthRulesTest(unittest.TestCase):
    def setUp(self):
        self.analyzer = TraditionalHoraryQuestionAnalyzer()

    def test_mothers_tumor_routes_to_turned_health_houses(self):
        analysis = self.analyzer.analyze_question("Will Mum's Tumor Stop Growing?")

        self.assertEqual(analysis["question_type"], Category.HEALTH)
        self.assertEqual(analysis["health_analysis"]["family"], "progression")
        self.assertEqual(analysis["relevant_houses"], [10, 3])
        self.assertEqual(analysis["significators"]["querent_house"], 10)
        self.assertEqual(analysis["significators"]["quesited_house"], 3)

    def test_multiple_sclerosis_routes_to_health_diagnosis(self):
        analysis = self.analyzer.analyze_question("Is It Multiple Sclerosis?")

        self.assertEqual(analysis["question_type"], Category.HEALTH)
        self.assertEqual(analysis["health_analysis"]["family"], "diagnosis")
        self.assertEqual(analysis["relevant_houses"], [1, 6])
        self.assertEqual(analysis["significators"]["quesited_house"], 6)

    def test_pet_survival_question_gets_recovery_family(self):
        analysis = self.analyzer.analyze_question("Will my dog get better? Will it survive?")

        self.assertEqual(analysis["question_type"], Category.PET)
        self.assertEqual(analysis["pet_analysis"]["family"], "recovery")
        self.assertEqual(analysis["relevant_houses"], [1, 6])

    def test_grandfather_survival_routes_to_death_edge_category(self):
        analysis = self.analyzer.analyze_question("Will Grandfather Survive This Time?")

        self.assertEqual(analysis["question_type"], Category.DEATH)
        self.assertEqual(analysis["relevant_houses"], [4, 11])
        self.assertEqual(analysis["significators"]["quesited_house"], 11)

    def test_health_diagnosis_snapshot_defaults_to_no_without_present_state_contact(self):
        evaluation = evaluate_health_diagnosis_snapshot(
            {
                "family": "diagnosis",
                "subject_name": "Mercury",
                "subject_house": 1,
                "subject_sign": Sign.GEMINI,
                "illness_name": "Venus",
                "illness_house": 8,
                "illness_sign": Sign.CAPRICORN,
                "illness_dignity": 5,
                "aspect_name": None,
                "aspect_applying": None,
                "moon_next_planet": Planet.VENUS,
                "moon_next_aspect": Aspect.TRINE,
                "moon_next_applying": True,
            }
        )

        self.assertTrue(evaluation["applies"])
        self.assertEqual(evaluation["result"], "NO")

    def test_health_progression_snapshot_supports_stabilizing_fixed_sign_case(self):
        evaluation = evaluate_health_progression_snapshot(
            {
                "family": "progression",
                "subject_name": "Venus",
                "subject_house": 10,
                "subject_sign": Sign.TAURUS,
                "subject_dignity": 4,
                "illness_name": "Venus",
                "illness_house": 10,
                "illness_sign": Sign.TAURUS,
                "illness_dignity": 4,
                "illness_retrograde": False,
                "same_ruler": True,
                "moon_next_planet": Planet.JUPITER,
                "moon_next_aspect": Aspect.SEXTILE,
                "moon_next_applying": True,
            }
        )

        self.assertTrue(evaluation["applies"])
        self.assertEqual(evaluation["result"], "YES")

    def test_pet_recovery_snapshot_accepts_strong_safety_balance(self):
        evaluation = evaluate_pet_recovery_snapshot(
            {
                "family": "recovery",
                "pet_name": "Mercury",
                "pet_house": 9,
                "pet_sign": Sign.LIBRA,
                "pet_dignity": -1,
                "pet_retrograde": False,
                "pet_solar_condition": "Free of Sun",
                "pet_safety_score": 11,
                "moon_score": 3,
                "moon_next_planet": Planet.JUPITER,
                "moon_next_aspect": Aspect.SEXTILE,
                "moon_next_applying": True,
            }
        )

        self.assertTrue(evaluation["applies"])
        self.assertEqual(evaluation["result"], "YES")

    def test_analyze_pet_question_text_detects_recovery(self):
        analysis = analyze_pet_question_text("Will my dog get better? Will it survive?")
        self.assertEqual(analysis["family"], "recovery")

    def test_analyze_health_question_text_detects_progression(self):
        analysis = analyze_health_question_text("Will Mum's tumor stop growing?")
        self.assertEqual(analysis["family"], "progression")


if __name__ == "__main__":
    unittest.main()
