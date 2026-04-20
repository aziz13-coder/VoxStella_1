from pathlib import Path
import sys
import unittest


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.forensic.engine import evaluate, load_knowledge
from backend.forensic.features import extract_features


KNOWLEDGE_DIR = repo_root / "backend" / "forensic" / "knowledge"
DEFAULT_CUSPS = [0.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0]


def _rule_ids(findings):
    return {finding.get("id") for finding in findings}


def _dashboard(planets, *, aspects=None, house_rulers=None, solar_conditions=None, house_cusps=None):
    return {
        "planets": planets,
        "all_aspects": aspects or [],
        "house_rulers": house_rulers or {},
        "house_cusps": house_cusps or list(DEFAULT_CUSPS),
        "solar_conditions": solar_conditions or {},
    }


class ForensicDeceptionRuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rules = load_knowledge(str(KNOWLEDGE_DIR))

    def _ids_for(self, dashboard):
        return _rule_ids(evaluate(extract_features(dashboard), self.rules))

    def test_mercury_neptune_hidden_cluster_fires_core_deception_rules(self):
        dashboard = _dashboard(
            [
                {"planet": "Sun", "longitude": 100.0, "house": 12, "sign": "Cancer"},
                {"planet": "Mercury", "longitude": 101.0, "house": 12, "sign": "Cancer", "retrograde": True},
                {"planet": "Neptune", "longitude": 102.0, "house": 12, "sign": "Cancer"},
                {"planet": "Moon", "longitude": 210.0, "house": 4, "sign": "Scorpio"},
            ],
            aspects=[
                {"planet1": "Mercury", "planet2": "Neptune", "aspect": "Conjunction", "applying": True, "orb": 1.0},
            ],
            house_rulers={"7": "Mercury"},
            solar_conditions={
                "combustion": [{"planet": "Mercury", "phase": "applying"}],
            },
        )

        ids = self._ids_for(dashboard)
        self.assertIn("mercury_neptune_aspect", ids)
        self.assertIn("mercury_retrograde", ids)
        self.assertIn("mercury_combust", ids)
        self.assertIn("mercury_combust_applying", ids)
        self.assertIn("mercury_in_12th", ids)
        self.assertIn("mercury_in_mute_sign", ids)
        self.assertIn("neptune_personal_planets", ids)
        self.assertIn("neptune_in_7th_or_12th", ids)
        self.assertIn("twelfth_house_emphasis_deception", ids)
        self.assertIn("seventh_ruler_in_12th", ids)
        self.assertIn("sun_or_moon_in_12th", ids)

    def test_neptune_angular_coverup_and_mars_opposition_rules_fire(self):
        dashboard = _dashboard(
            [
                {"planet": "Neptune", "longitude": 270.0, "house": 10, "sign": "Capricorn"},
                {"planet": "Saturn", "longitude": 90.0, "house": 4, "sign": "Cancer"},
                {"planet": "Mars", "longitude": 90.0, "house": 1, "sign": "Cancer"},
                {"planet": "Sun", "longitude": 10.0, "house": 2, "sign": "Aries"},
            ],
            aspects=[
                {"planet1": "Mars", "planet2": "Neptune", "aspect": "Opposition", "applying": True, "orb": 0.0},
                {"planet1": "Saturn", "planet2": "Neptune", "aspect": "Opposition", "applying": True, "orb": 0.0},
            ],
        )

        ids = self._ids_for(dashboard)
        self.assertIn("neptune_angular_strong", ids)
        self.assertIn("mars_neptune_opposition", ids)
        self.assertIn("saturn_neptune_coverup", ids)

    def test_mars_neptune_square_rule_fires(self):
        dashboard = _dashboard(
            [
                {"planet": "Neptune", "longitude": 10.0, "house": 5, "sign": "Aries"},
                {"planet": "Mars", "longitude": 100.0, "house": 8, "sign": "Cancer"},
                {"planet": "Moon", "longitude": 220.0, "house": 11, "sign": "Scorpio"},
            ],
            aspects=[
                {"planet1": "Mars", "planet2": "Neptune", "aspect": "Square", "applying": True, "orb": 0.0},
            ],
        )

        ids = self._ids_for(dashboard)
        self.assertIn("mars_neptune_square", ids)

    def test_venus_saturn_relationship_deception_rules_fire(self):
        dashboard = _dashboard(
            [
                {"planet": "Venus", "longitude": 15.0, "house": 5, "sign": "Aries"},
                {"planet": "Saturn", "longitude": 285.0, "house": 10, "sign": "Capricorn"},
                {"planet": "Mercury", "longitude": 65.0, "house": 7, "sign": "Gemini"},
            ],
            aspects=[
                {"planet1": "Venus", "planet2": "Saturn", "aspect": "Square", "applying": False, "orb": 0.0},
            ],
        )

        ids = self._ids_for(dashboard)
        self.assertIn("venus_saturn_hard", ids)
        self.assertIn("venus_detriment_with_saturn", ids)

    def test_mute_sign_geometry_rules_fire(self):
        dashboard = _dashboard(
            [
                {"planet": "Sun", "longitude": 15.0, "house": 1, "sign": "Aries"},
            ],
            house_cusps=[90.0, 120.0, 210.0, 330.0, 0.0, 30.0, 180.0, 210.0, 330.0, 0.0, 30.0, 60.0],
        )

        ids = self._ids_for(dashboard)
        self.assertIn("mute_signs_on_angles", ids)
        self.assertIn("mute_signs_on_3rd_or_9th", ids)

    def test_north_node_deception_rules_fire_in_eighth(self):
        dashboard = _dashboard(
            [
                {"planet": "North Node", "longitude": 205.0, "house": 8, "sign": "Libra", "retrograde": True},
                {"planet": "Neptune", "longitude": 206.0, "house": 2, "sign": "Libra"},
                {"planet": "Mercury", "longitude": 45.0, "house": 3, "sign": "Taurus"},
            ],
            aspects=[
                {"planet1": "North Node", "planet2": "Neptune", "aspect": "Conjunction", "applying": True, "orb": 1.0},
            ],
        )

        ids = self._ids_for(dashboard)
        self.assertIn("north_node_in_8th", ids)
        self.assertIn("node_with_neptune_or_mercury", ids)

    def test_north_node_in_fourth_rule_fires(self):
        dashboard = _dashboard(
            [
                {"planet": "North Node", "longitude": 105.0, "house": 4, "sign": "Cancer", "retrograde": True},
                {"planet": "Moon", "longitude": 110.0, "house": 4, "sign": "Cancer"},
            ],
        )

        ids = self._ids_for(dashboard)
        self.assertIn("north_node_in_4th", ids)

    def test_truth_rule_fires_for_jupiter_mercury_easy_aspect(self):
        dashboard = _dashboard(
            [
                {"planet": "Mercury", "longitude": 15.0, "house": 3, "sign": "Aries"},
                {"planet": "Jupiter", "longitude": 135.0, "house": 7, "sign": "Leo"},
                {"planet": "Moon", "longitude": 250.0, "house": 9, "sign": "Sagittarius"},
            ],
            aspects=[
                {"planet1": "Jupiter", "planet2": "Mercury", "aspect": "Trine", "applying": True, "orb": 0.0},
            ],
        )

        ids = self._ids_for(dashboard)
        self.assertIn("truth_jupiter_mercury_easy", ids)


if __name__ == "__main__":
    unittest.main()
