from __future__ import annotations

import sys
import unittest
from pathlib import Path


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.horary_engine.children_doctrine import (  # noqa: E402
    evaluate_children_adoption_snapshot,
)
from backend.horary_engine.pregnancy_doctrine import (  # noqa: E402
    analyze_pregnancy_question_text,
    evaluate_pregnancy_conception_snapshot,
    evaluate_pregnancy_diagnosis_snapshot,
)
from backend.horary_engine.relationship_doctrine import (  # noqa: E402
    analyze_relationship_question_text,
)
from backend.models import Aspect, Planet, Sign  # noqa: E402
from backend.question_analyzer import TraditionalHoraryQuestionAnalyzer  # noqa: E402
from backend.taxonomy import Category  # noqa: E402


class HoraryBookSlice2RulesTest(unittest.TestCase):
    def setUp(self):
        self.analyzer = TraditionalHoraryQuestionAnalyzer()

    def test_relationship_find_question_prefers_relationship_not_lost_object(self):
        analysis = self.analyzer.analyze_question("Will I find a new relationship and when?")

        self.assertEqual(analysis["question_type"], Category.RELATIONSHIP)
        self.assertEqual(analysis["relevant_houses"], [1, 7])
        self.assertEqual(analysis["significators"]["quesited_house"], 7)

    def test_adoption_question_turns_to_other_parents_child(self):
        analysis = self.analyzer.analyze_question("Will they put the baby up for adoption?")

        self.assertEqual(analysis["question_type"], Category.CHILDREN)
        self.assertEqual(analysis["relevant_houses"], [1, 7, 11])
        self.assertEqual(analysis["significators"]["subject_house"], 7)
        self.assertEqual(analysis["significators"]["child_house"], 11)
        self.assertEqual(analysis["significators"]["quesited_house"], 11)

    def test_relationship_last_question_gets_durability_family(self):
        analysis = analyze_relationship_question_text("Will the relationship last?")
        self.assertEqual(analysis["family"], "durability")

    def test_pregnancy_question_families_split_diagnosis_from_conception(self):
        diagnosis = analyze_pregnancy_question_text("Am I pregnant?")
        conception = analyze_pregnancy_question_text("Will I conceive?")

        self.assertEqual(diagnosis["family"], "diagnosis")
        self.assertEqual(conception["family"], "conception")

    def test_my_own_child_question_stays_first_person_not_third_person_child(self):
        analysis = self.analyzer.analyze_question("Any chance of having my own child?")

        self.assertEqual(analysis["question_type"], Category.CHILDREN)
        self.assertEqual(analysis["relevant_houses"], [1, 5])
        self.assertEqual(analysis["significators"]["querent_house"], 1)
        self.assertEqual(analysis["significators"]["quesited_house"], 5)
        self.assertFalse(analysis["third_person_analysis"]["is_third_person"])

    def test_pregnancy_diagnosis_snapshot_denies_applying_future_connection(self):
        evaluation = evaluate_pregnancy_diagnosis_snapshot(
            {
                "family": "diagnosis",
                "querent_name": "Mercury",
                "quesited_name": "Saturn",
                "quesited_house": 1,
                "quesited_sign": Sign.VIRGO,
                "quesited_dignity": 2,
                "quesited_speed": 0.05,
                "aspect_name": "Trine",
                "aspect_applying": True,
                "aspect_distance": 0.9,
            }
        )

        self.assertTrue(evaluation["applies"])
        self.assertEqual(evaluation["result"], "NO")
        self.assertTrue(any("connection forming later" in item["rule"] for item in evaluation["reasoning"]))

    def test_pregnancy_conception_snapshot_accepts_strong_moon_to_child_testimony(self):
        evaluation = evaluate_pregnancy_conception_snapshot(
            {
                "family": "conception",
                "querent_name": "Sun",
                "quesited_name": "Jupiter",
                "querent_house": 6,
                "quesited_house": 11,
                "querent_dignity": -1,
                "quesited_dignity": 2,
                "quesited_retrograde": True,
                "moon_sign": Sign.CANCER,
                "moon_dignity": 7,
                "quesited_sign": Sign.CANCER,
                "moon_next_planet": Planet.JUPITER,
                "moon_next_aspect": Aspect.CONJUNCTION,
                "moon_next_applying": True,
            }
        )

        self.assertTrue(evaluation["applies"])
        self.assertEqual(evaluation["result"], "YES")

    def test_adoption_snapshot_denies_when_child_remains_with_parents(self):
        evaluation = evaluate_children_adoption_snapshot(
            {
                "family": "adoption",
                "subject_house": 7,
                "child_house": 11,
                "child_planet_name": "Venus",
                "child_planet_house": 7,
                "child_sign": Sign.TAURUS,
                "child_dignity": 5,
            }
        )

        self.assertTrue(evaluation["applies"])
        self.assertEqual(evaluation["result"], "NO")
        self.assertTrue(any("parents' house" in item["rule"] for item in evaluation["reasoning"]))


if __name__ == "__main__":
    unittest.main()
