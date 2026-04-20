from pathlib import Path
import sys
import unittest


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.forensic.engine import evaluate, load_knowledge
from backend.forensic.features import compute_dominance, extract_features


KNOWLEDGE_DIR = repo_root / "backend" / "forensic" / "knowledge"
DEFAULT_CUSPS = [0.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0]


def _rule_ids(findings):
    return {finding.get("id") for finding in findings}


def _dashboard(planets, *, aspects=None, house_rulers=None, house_cusps=None, sect=None, solar_conditions=None):
    return {
        "planets": planets,
        "all_aspects": aspects or [],
        "house_rulers": house_rulers or {},
        "house_cusps": house_cusps or list(DEFAULT_CUSPS),
        "sect": sect or {},
        "solar_conditions": solar_conditions or {},
    }


class ForensicCoreRuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rules = load_knowledge(str(KNOWLEDGE_DIR))

    def _ids_for(self, dashboard):
        return _rule_ids(evaluate(extract_features(dashboard), self.rules))

    def test_base_rules_fire_for_out_of_sect_mars_and_applying_moon_square(self):
        dashboard = _dashboard(
            [
                {"planet": "Moon", "longitude": 10.0, "house": 1, "sign": "Aries"},
                {"planet": "Mars", "longitude": 100.0, "house": 10, "sign": "Cancer"},
                {"planet": "Sun", "longitude": 220.0, "house": 7, "sign": "Scorpio"},
            ],
            aspects=[
                {"planet1": "Moon", "planet2": "Mars", "aspect": "Square", "applying": True, "orb": 0.0},
            ],
            sect={"chart_sect": "diurnal"},
        )

        ids = self._ids_for(dashboard)
        self.assertIn("sect_malefic_out_of_sect", ids)
        self.assertIn("moon_applying_malefic_hard", ids)

    def test_degree_signature_rules_fire_for_anaretic_ingress_middegree_and_via_combusta(self):
        dashboard = _dashboard(
            [
                {"planet": "Sun", "longitude": 29.4, "house": 1, "sign": "Aries"},
                {"planet": "Moon", "longitude": 209.4, "house": 8, "sign": "Libra"},
                {"planet": "Mercury", "longitude": 0.2, "house": 2, "sign": "Aries"},
                {"planet": "Jupiter", "longitude": 135.0, "house": 5, "sign": "Leo"},
            ],
        )

        ids = self._ids_for(dashboard)
        self.assertIn("any_anaretic_planet", ids)
        self.assertIn("any_anaretic_planet_any", ids)
        self.assertIn("moon_via_combusta", ids)
        self.assertIn("planet_ingress", ids)
        self.assertIn("mid_degree_focus", ids)

    def test_house_rules_fire_for_first_ruler_8th_overlap_twelfth_emphasis_and_malefic_in_6th(self):
        dashboard = _dashboard(
            [
                {"planet": "Venus", "longitude": 15.0, "house": 8, "sign": "Aries"},
                {"planet": "Mars", "longitude": 160.0, "house": 6, "sign": "Virgo"},
                {"planet": "Moon", "longitude": 330.0, "house": 12, "sign": "Pisces"},
                {"planet": "Saturn", "longitude": 335.0, "house": 12, "sign": "Pisces"},
            ],
            house_rulers={"1": "Venus", "8": "Venus"},
        )

        ids = self._ids_for(dashboard)
        self.assertIn("first_ruler_in_8th", ids)
        self.assertIn("first_ruler_rules_8th", ids)
        self.assertIn("strong_12th_emphasis", ids)
        self.assertIn("malefics_in_6th", ids)

    def test_remaining_directional_violence_rules_fire(self):
        dashboard = _dashboard(
            [
                {"planet": "Moon", "longitude": 210.0, "house": 8, "sign": "Scorpio"},
                {"planet": "Mars", "longitude": 300.0, "house": 10, "sign": "Aquarius"},
                {"planet": "Venus", "longitude": 340.0, "house": 12, "sign": "Pisces"},
            ],
            aspects=[
                {"planet1": "Moon", "planet2": "Mars", "aspect": "Square", "applying": True, "orb": 0.0},
            ],
            house_rulers={"1": "Venus", "8": "Mars"},
        )

        ids = self._ids_for(dashboard)
        self.assertIn("violence_moon_under_death_pressure", ids)
        self.assertIn("violence_hidden_victim_with_angular_malefic", ids)


class ForensicDominanceTests(unittest.TestCase):
    def test_compute_dominance_scores_extremely_dominant_planet(self):
        features = {
            "planets": {
                "Sun": {
                    "house": 1,
                    "angular": True,
                    "retrograde": False,
                    "essential_dignity_raw": "domicile",
                    "dignities": [],
                },
                "Moon": {
                    "house": 4,
                    "angular": True,
                    "retrograde": False,
                    "essential_dignity_raw": "",
                    "dignities": [],
                },
            },
            "aspects": {
                "Sun_to_Moon": {
                    "type": "conjunction",
                    "applying": True,
                },
            },
        }

        dominance = compute_dominance(features)
        sun = dominance["planets"]["Sun"]
        self.assertEqual(sun["score"], 81)
        self.assertEqual(sun["level"], "Extremely Dominant")
        self.assertEqual(sun["breakdown"]["angular"], 30)
        self.assertEqual(sun["breakdown"]["house"], 20)
        self.assertEqual(sun["breakdown"]["essential"], 25)
        self.assertEqual(sun["breakdown"]["motion"], 0)
        self.assertEqual(sun["breakdown"]["aspects"], 6)

    def test_compute_dominance_marks_retrograde_cadent_planet_as_weak(self):
        features = {
            "planets": {
                "Mercury": {
                    "house": 3,
                    "angular": False,
                    "retrograde": True,
                    "essential_dignity_raw": "",
                    "dignities": [],
                },
            },
            "aspects": {},
        }

        dominance = compute_dominance(features)
        mercury = dominance["planets"]["Mercury"]
        self.assertEqual(mercury["score"], -5)
        self.assertEqual(mercury["level"], "Weak")
        self.assertEqual(mercury["breakdown"]["motion"], -5)
        self.assertEqual(mercury["breakdown"]["aspects"], 0)


if __name__ == "__main__":
    unittest.main()
