from __future__ import annotations

import unittest
from types import SimpleNamespace

from backend.horary_engine.engine import HoraryEngine
from backend.models import Planet, PlanetPosition, Sign, SolarAnalysis, SolarCondition
from backend.taxonomy import Category

from tests.horary_generic_gate_utils import (
    load_generic_gate_corpus,
    replay_generic_gate_case,
)


class HoraryGenericGateRulesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus = {entry["id"]: entry for entry in load_generic_gate_corpus()}
        cls.engine = HoraryEngine().engine

    def _replay(self, case_id: str):
        return replay_generic_gate_case(self.corpus[case_id])

    def _build_chart(self, quesited_dignity=5, retrograde=False, solar_condition=SolarCondition.FREE):
        quesited = PlanetPosition(
            planet=Planet.VENUS,
            longitude=45.0,
            latitude=0.0,
            house=10,
            sign=Sign.TAURUS,
            dignity_score=quesited_dignity,
            retrograde=retrograde,
            speed=1.2,
        )
        querent = PlanetPosition(
            planet=Planet.MARS,
            longitude=10.0,
            latitude=0.0,
            house=1,
            sign=Sign.ARIES,
            dignity_score=2,
            retrograde=False,
            speed=0.7,
        )
        moon = PlanetPosition(
            planet=Planet.MOON,
            longitude=12.0,
            latitude=0.0,
            house=1,
            sign=Sign.ARIES,
            dignity_score=0,
            retrograde=False,
            speed=13.0,
        )
        return SimpleNamespace(
            planets={
                Planet.MARS: querent,
                Planet.VENUS: quesited,
                Planet.MOON: moon,
            },
            solar_analyses={
                Planet.VENUS: SolarAnalysis(
                    planet=Planet.VENUS,
                    distance_from_sun=40.0,
                    condition=solar_condition,
                )
            },
        )

    def test_denial_controls_remain_no_under_secondary_balance(self):
        denial_controls = [
            "masters_program_no_perfection_no",
            "will_my_tenant_send_full_payment",
            "will_i_profit_from_this_bet",
            "divorce_no_manual_review",
            "pay_rise_article_spec",
        ]

        for case_id in denial_controls:
            with self.subTest(case_id=case_id):
                replayed = self._replay(case_id)
                self.assertEqual(replayed["verdict"], "NO")
                self.assertEqual(
                    replayed["perfection_type"], "denial_secondary_balance"
                )

    def test_strongest_mixed_occurrence_case_now_returns_unclear(self):
        replayed = self._replay("marriage_no_manual_review")

        self.assertEqual(replayed["verdict"], "UNCLEAR")
        self.assertEqual(
            replayed["perfection_type"], "mixed_or_inconclusive_secondary_balance"
        )
        self.assertGreaterEqual(
            (replayed["raw"].get("traditional_factors") or {}).get(
                "secondary_balance_score", 0
            ),
            6,
        )

    def test_quality_path_case_remains_outside_generic_occurrence_balance(self):
        replayed = self._replay(
            "is_there_any_hope_for_us_getting_back_together_should_i_wait_for_her"
        )

        self.assertEqual(replayed["verdict"], "NO")
        self.assertEqual(replayed["perfection_type"], "none")

    def test_mild_mixed_cases_do_not_flip_affirmative(self):
        for case_id in [
            "will_investing_in_this_business_prove_profitable_for_me",
            "will_i_get_the_job_at_uw",
        ]:
            with self.subTest(case_id=case_id):
                replayed = self._replay(case_id)
                self.assertNotEqual(replayed["verdict"], "YES")

    def test_reception_without_connecting_testimony_caps_at_unclear(self):
        chart = self._build_chart()

        result = self.engine._evaluate_generic_secondary_balance(
            chart,
            Planet.MARS,
            Planet.VENUS,
            Category.CAREER,
            True,
            {"void_of_course": False},
            {"result": None, "reason": None, "decisive": False},
            {
                "favorable": True,
                "total_score": 15,
                "reason": "Jupiter supports both significators",
            },
            False,
            {
                "traditional_strength": 8,
                "type": "mixed_reception",
                "mutual": "mixed_reception",
            },
        )

        self.assertTrue(result["applies"])
        self.assertEqual(result["result"], "UNCLEAR")
        self.assertEqual(result["bucket"], "mixed_or_inconclusive_secondary_balance")
        self.assertGreaterEqual(result["score"], 8)
        self.assertIn("lacks a strong traditional bridge", result["reasoning"][0]["rule"])

    def test_decisive_moon_bridge_can_still_produce_generic_yes(self):
        chart = self._build_chart()

        result = self.engine._evaluate_generic_secondary_balance(
            chart,
            Planet.MARS,
            Planet.VENUS,
            Category.CAREER,
            True,
            {"void_of_course": False},
            {
                "result": "YES",
                "reason": "Moon applies decisively to the quesited",
                "decisive": True,
            },
            {
                "favorable": True,
                "total_score": 15,
                "reason": "Jupiter supports both significators",
            },
            False,
            {
                "traditional_strength": 8,
                "type": "mixed_reception",
                "mutual": "mixed_reception",
            },
        )

        self.assertTrue(result["applies"])
        self.assertEqual(result["result"], "YES")
        self.assertEqual(result["bucket"], "affirmative_secondary_balance")
        self.assertIn("strong connecting testimony", result["reasoning"][0]["rule"])


if __name__ == "__main__":
    unittest.main()
