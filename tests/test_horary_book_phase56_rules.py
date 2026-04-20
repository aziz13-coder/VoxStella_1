from __future__ import annotations

import datetime
import sys
from pathlib import Path
import unittest


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.models import HoraryChart, Planet, PlanetPosition, Sign  # noqa: E402
from backend.question_analyzer import TraditionalHoraryQuestionAnalyzer  # noqa: E402
from backend.taxonomy import Category, resolve  # noqa: E402


def _pos(planet: Planet, longitude: float, house: int, speed: float = 1.0) -> PlanetPosition:
    sign = list(Sign)[int((longitude % 360) // 30)]
    return PlanetPosition(
        planet=planet,
        longitude=longitude,
        latitude=0.0,
        house=house,
        sign=sign,
        dignity_score=0,
        essential_dignity=0,
        accidental_dignity=0,
        retrograde=False,
        speed=speed,
    )


def _minimal_chart() -> HoraryChart:
    return HoraryChart(
        date_time=datetime.datetime(2024, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc),
        date_time_utc=datetime.datetime(2024, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc),
        timezone_info="UTC",
        location=(0.0, 0.0),
        location_name="Test",
        planets={
            Planet.SUN: _pos(Planet.SUN, 10.0, 1),
            Planet.MOON: _pos(Planet.MOON, 190.0, 7, 12.0),
            Planet.MERCURY: _pos(Planet.MERCURY, 95.0, 4),
            Planet.VENUS: _pos(Planet.VENUS, 110.0, 4),
            Planet.MARS: _pos(Planet.MARS, 300.0, 11),
            Planet.JUPITER: _pos(Planet.JUPITER, 205.0, 7),
            Planet.SATURN: _pos(Planet.SATURN, 330.0, 1, 0.1),
        },
        aspects=[],
        houses=[i * 30.0 for i in range(12)],
        house_rulers={
            1: Planet.SATURN,
            2: Planet.MARS,
            3: Planet.VENUS,
            4: Planet.VENUS,
            5: Planet.SUN,
            6: Planet.MERCURY,
            7: Planet.MOON,
            8: Planet.MERCURY,
            9: Planet.JUPITER,
            10: Planet.SUN,
            11: Planet.MARS,
            12: Planet.JUPITER,
        },
        ascendant=0.0,
        midheaven=90.0,
        julian_day=2451545.0,
    )


class HoraryBookPhase56RulesTest(unittest.TestCase):
    def setUp(self):
        self.analyzer = TraditionalHoraryQuestionAnalyzer()

    def test_phase56_route_questions_hit_expected_houses(self):
        cases = [
            ("Will I get a good yearly review of my work?", Category.CAREER, [1, 10], 10),
            ("Will my tenant send full payment?", Category.MONEY, [1, 7, 8], 8),
            ("Will I profit from this bet?", Category.MONEY, [1, 2, 8], 8),
            ("Will investing in this business prove profitable for me?", Category.MONEY, [1, 10, 11], 11),
            ("Will the bank foreclose?", Category.MONEY, [1, 7], 7),
            ("Should I move to my friend's house?", Category.PROPERTY, [1, 11], 11),
            ("Should I buy this flat?", Category.PROPERTY, [1, 4, 10], 4),
            ("Will we rent the house?", Category.PROPERTY, [1, 7, 4], 4),
        ]
        for question, category, houses, quesited_house in cases:
            with self.subTest(question=question):
                analysis = self.analyzer.analyze_question(question)
                self.assertEqual(analysis["question_type"], category)
                self.assertEqual(analysis["relevant_houses"], houses)
                self.assertEqual(analysis["significators"]["quesited_house"], quesited_house)

    def test_resolver_prefers_explicit_quesited_house_over_second_manual_house(self):
        chart = _minimal_chart()
        resolved = resolve(
            chart,
            Category.PROPERTY,
            manual_houses=[1, 7, 4],
            significator_info={"querent_house": 1, "quesited_house": 4},
        )

        self.assertTrue(resolved["valid"])
        self.assertEqual(resolved["querent_house"], 1)
        self.assertEqual(resolved["quesited_house"], 4)
        self.assertEqual(resolved["quesited"], Planet.VENUS)


if __name__ == "__main__":
    unittest.main()
