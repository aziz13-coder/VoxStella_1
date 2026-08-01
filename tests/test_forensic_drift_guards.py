from pathlib import Path
import sys
import unittest


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.forensic.engine import evaluate, load_knowledge
from backend.forensic.features import extract_features


KNOWLEDGE_DIR = repo_root / "backend" / "forensic" / "knowledge"


def _rule_ids(findings):
    return {finding.get("id") for finding in findings}


class ForensicDriftGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rules = load_knowledge(str(KNOWLEDGE_DIR))

    def test_wide_hard_aspect_does_not_mark_house_ruler_as_hard_afflicted(self):
        dashboard = {
            "planets": [
                {"planet": "Moon", "longitude": 110.0, "house": 1, "sign": "Cancer"},
                {"planet": "Sun", "longitude": 123.0, "house": 3, "sign": "Leo"},
                {"planet": "Mercury", "longitude": 95.0, "house": 4, "sign": "Cancer"},
                {"planet": "Saturn", "longitude": 230.7, "house": 9, "sign": "Scorpio"},
            ],
            "house_rulers": {"1": "Mercury", "4": "Sun", "5": "Mercury", "7": "Jupiter", "8": "Mars"},
            "house_cusps": [90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0, 0.0, 30.0, 60.0],
            "all_aspects": [
                {"planet1": "Sun", "planet2": "Saturn", "aspect": "Square", "applying": False, "orb": 7.74},
            ],
        }

        features = extract_features(dashboard)
        self.assertFalse(features["houses"]["fourth_ruler_hard_afflicted"])

    def test_family_and_child_rules_do_not_fire_from_cancer_moon_and_light_home_overlap(self):
        dashboard = {
            "planets": [
                {"planet": "Moon", "longitude": 110.0, "house": 1, "sign": "Cancer"},
                {"planet": "Sun", "longitude": 123.0, "house": 3, "sign": "Leo"},
                {"planet": "Mercury", "longitude": 95.0, "house": 4, "sign": "Cancer"},
                {"planet": "Saturn", "longitude": 230.7, "house": 9, "sign": "Scorpio"},
            ],
            "house_rulers": {"1": "Mercury", "4": "Sun", "5": "Mercury", "7": "Jupiter", "8": "Mars"},
            "house_cusps": [90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0, 0.0, 30.0, 60.0],
            "all_aspects": [
                {"planet1": "Sun", "planet2": "Saturn", "aspect": "Square", "applying": False, "orb": 7.74},
            ],
        }

        ids = _rule_ids(evaluate(extract_features(dashboard), self.rules))
        self.assertNotIn("family_domestic_moon_signature", ids)
        self.assertNotIn("family_home_axis_under_pressure", ids)
        self.assertNotIn("child_family_overlap", ids)

    def test_abduction_rule_requires_explicit_abductor_signal(self):
        dashboard = {
            "planets": [
                {"planet": "Moon", "longitude": 110.0, "house": 12, "sign": "Cancer"},
                {"planet": "Venus", "longitude": 100.0, "house": 12, "sign": "Cancer"},
                {"planet": "Saturn", "longitude": 280.0, "house": 10, "sign": "Capricorn"},
                {"planet": "Sun", "longitude": 50.0, "house": 2, "sign": "Taurus"},
            ],
            "house_rulers": {"1": "Moon", "4": "Venus", "5": "Mars", "7": "Saturn", "8": "Jupiter", "11": "Venus"},
            "house_cusps": [90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0, 0.0, 30.0, 60.0],
            "all_aspects": [
                {"planet1": "Moon", "planet2": "Saturn", "aspect": "Trine", "applying": False, "orb": 2.0},
            ],
        }

        ids = _rule_ids(evaluate(extract_features(dashboard), self.rules))
        self.assertNotIn("abduction_missing_person_signature", ids)
        self.assertNotIn("abduction_transport_or_public_seizure_signature", ids)

    def test_abduction_transport_rule_does_not_fire_from_public_homicide_without_movement_axis(self):
        dashboard = {
            "planets": [
                {"planet": "Venus", "longitude": 260.0, "house": 8, "sign": "Sagittarius"},
                {"planet": "Mercury", "longitude": 15.0, "house": 10, "sign": "Aries"},
                {"planet": "Moon", "longitude": 140.0, "house": 5, "sign": "Leo"},
                {"planet": "Saturn", "longitude": 18.0, "house": 10, "sign": "Aries"},
                {"planet": "Mars", "longitude": 200.0, "house": 7, "sign": "Libra"},
            ],
            "house_rulers": {"1": "Venus", "3": "Jupiter", "7": "Mercury", "8": "Mars", "9": "Saturn", "10": "Moon"},
            "house_cusps": [240.0, 270.0, 300.0, 330.0, 0.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0, 210.0],
            "all_aspects": [
                {"planet1": "Moon", "planet2": "Saturn", "aspect": "Square", "applying": True, "orb": 2.0},
            ],
        }

        ids = _rule_ids(evaluate(extract_features(dashboard), self.rules))
        self.assertNotIn("abduction_transport_or_public_seizure_signature", ids)
        self.assertNotIn("abduction_public_place_seizure_signature", ids)

    def test_child_rule_does_not_fire_from_moon_in_fifth_without_direct_child_stress(self):
        dashboard = {
            "planets": [
                {"planet": "Mercury", "longitude": 250.0, "house": 8, "sign": "Sagittarius"},
                {"planet": "Moon", "longitude": 130.0, "house": 5, "sign": "Leo"},
                {"planet": "Venus", "longitude": 20.0, "house": 1, "sign": "Aries"},
                {"planet": "Mars", "longitude": 170.0, "house": 6, "sign": "Virgo"},
                {"planet": "Saturn", "longitude": 300.0, "house": 9, "sign": "Aquarius"},
            ],
            "house_rulers": {"1": "Mercury", "3": "Jupiter", "5": "Moon", "7": "Venus", "8": "Mars", "9": "Saturn", "10": "Jupiter"},
            "house_cusps": [0.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0],
            "all_aspects": [
                {"planet1": "Mercury", "planet2": "Saturn", "aspect": "Square", "applying": False, "orb": 2.0},
            ],
        }

        ids = _rule_ids(evaluate(extract_features(dashboard), self.rules))
        self.assertNotIn("child_house_under_stress", ids)

    def test_abduction_worksite_rule_does_not_fire_from_work_overlap_without_public_or_coercive_pressure(self):
        dashboard = {
            "planets": [
                {"planet": "Mercury", "longitude": 155.0, "house": 6, "sign": "Virgo"},
                {"planet": "Venus", "longitude": 150.0, "house": 6, "sign": "Virgo"},
                {"planet": "Jupiter", "longitude": 153.0, "house": 6, "sign": "Virgo"},
                {"planet": "Moon", "longitude": 45.0, "house": 2, "sign": "Taurus"},
                {"planet": "Saturn", "longitude": 15.0, "house": 10, "sign": "Aries"},
            ],
            "house_rulers": {"1": "Mercury", "3": "Venus", "6": "Jupiter", "7": "Jupiter", "9": "Moon", "10": "Sun"},
            "house_cusps": [0.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0],
            "all_aspects": [
                {"planet1": "Moon", "planet2": "Saturn", "aspect": "Trine", "applying": False, "orb": 0.0},
            ],
        }

        ids = _rule_ids(evaluate(extract_features(dashboard), self.rules))
        self.assertNotIn("abduction_worksite_or_assignment_seizure_signature", ids)

    def test_partner_rules_do_not_fire_from_home_entry_service_pretext_pattern(self):
        dashboard = {
            "planets": [
                {"planet": "Jupiter", "longitude": 74.39, "house": 7, "sign": "Gemini"},
                {"planet": "Mercury", "longitude": 58.04, "house": 6, "sign": "Taurus"},
                {"planet": "Moon", "longitude": 221.0, "house": 11, "sign": "Scorpio"},
                {"planet": "Venus", "longitude": 102.51, "house": 8, "sign": "Cancer"},
                {"planet": "Saturn", "longitude": 282.51, "house": 2, "sign": "Capricorn"},
                {"planet": "Mars", "longitude": 268.79, "house": 1, "sign": "Sagittarius"},
            ],
            "house_rulers": {"1": "Jupiter", "4": "Jupiter", "6": "Venus", "7": "Mercury", "8": "Moon", "10": "Mercury"},
            "house_cusps": [240.0, 270.0, 300.0, 330.0, 0.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0, 210.0],
            "all_aspects": [
                {"planet1": "Moon", "planet2": "Saturn", "aspect": "Square", "applying": True, "orb": 1.0},
                {"planet1": "Venus", "planet2": "Saturn", "aspect": "Opposition", "applying": False, "orb": 0.63},
            ],
        }

        ids = _rule_ids(evaluate(extract_features(dashboard), self.rules))
        self.assertIn("violence_home_entry_service_pretext_pattern", ids)
        self.assertNotIn("domestic_partner_known_spouse_homicide", ids)
        self.assertNotIn("domestic_partner_axis_contact", ids)

    def test_public_assignment_seizure_rule_requires_mercury_deception_not_mute_sign_noise(self):
        dashboard = {
            "planets": [
                {"planet": "Saturn", "longitude": 285.0, "house": 12, "sign": "Capricorn"},
                {"planet": "Moon", "longitude": 215.0, "house": 9, "sign": "Scorpio"},
                {"planet": "Mars", "longitude": 15.0, "house": 7, "sign": "Aries"},
                {"planet": "Venus", "longitude": 85.0, "house": 6, "sign": "Gemini"},
                {"planet": "Jupiter", "longitude": 40.0, "house": 4, "sign": "Taurus"},
                {"planet": "Sun", "longitude": 83.0, "house": 6, "sign": "Gemini"},
            ],
            "house_rulers": {"1": "Saturn", "3": "Mars", "4": "Venus", "6": "Mercury", "7": "Moon", "8": "Sun", "9": "Venus", "10": "Mars"},
            "house_cusps": [330.0, 0.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0],
            "all_aspects": [
                {"planet1": "Venus", "planet2": "Saturn", "aspect": "Opposition", "applying": False, "orb": 2.0},
            ],
            "solar_conditions": {
                "combustion": [{"planet": "Jupiter"}],
            },
        }

        ids = _rule_ids(evaluate(extract_features(dashboard), self.rules))
        self.assertNotIn("abduction_deceptive_public_or_assignment_seizure_signature", ids)

    def test_home_entry_service_rule_does_not_fire_from_disaster_chart_with_fourth_to_seventh_and_sixth_to_eighth(self):
        dashboard = {
            "planets": [
                {"planet": "Moon", "longitude": 255.0, "house": 6, "sign": "Sagittarius"},
                {"planet": "Venus", "longitude": 15.0, "house": 7, "sign": "Aries"},
                {"planet": "Jupiter", "longitude": 285.0, "house": 8, "sign": "Capricorn"},
                {"planet": "Saturn", "longitude": 95.0, "house": 3, "sign": "Cancer"},
                {"planet": "Mercury", "longitude": 276.0, "house": 6, "sign": "Capricorn", "retrograde": True},
            ],
            "house_rulers": {"1": "Moon", "4": "Venus", "6": "Jupiter", "7": "Saturn", "8": "Mars", "10": "Mercury", "11": "Venus"},
            "house_cusps": [90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0, 0.0, 30.0, 60.0],
            "all_aspects": [
                {"planet1": "Moon", "planet2": "Venus", "aspect": "Trine", "applying": False, "orb": 0.5},
            ],
            "solar_conditions": {
                "cazimi": [{"planet": "Venus"}],
            },
        }

        ids = _rule_ids(evaluate(extract_features(dashboard), self.rules))
        self.assertNotIn("violence_home_entry_service_pretext_pattern", ids)

    def test_transient_hospitality_rule_requires_venus_or_taurus_hospitality_testimony(self):
        dashboard = {
            "planets": [
                {"planet": "Mercury", "longitude": 95.0, "house": 3, "sign": "Cancer"},
                {"planet": "Moon", "longitude": 100.0, "house": 3, "sign": "Cancer"},
                {"planet": "Saturn", "longitude": 110.0, "house": 3, "sign": "Cancer"},
                {"planet": "Sun", "longitude": 130.0, "house": 5, "sign": "Leo"},
                {"planet": "Venus", "longitude": 155.0, "house": 5, "sign": "Virgo"},
                {"planet": "Mars", "longitude": 158.0, "house": 5, "sign": "Virgo"},
                {"planet": "Jupiter", "longitude": 162.0, "house": 5, "sign": "Virgo"},
            ],
            "house_rulers": {"1": "Mercury", "3": "Moon", "5": "Sun", "7": "Mars", "8": "Jupiter", "9": "Saturn", "10": "Saturn"},
            "house_cusps": [90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0, 0.0, 30.0, 60.0],
            "all_aspects": [
                {"planet1": "Mercury", "planet2": "Venus", "aspect": "Sextile", "applying": False, "orb": 0.0},
            ],
        }

        ids = _rule_ids(evaluate(extract_features(dashboard), self.rules))
        self.assertNotIn("abduction_transient_hospitality_seizure_signature", ids)

    def test_public_rules_do_not_fire_from_angular_sun_and_single_tenth_signal(self):
        dashboard = {
            "planets": [
                {"planet": "Sun", "longitude": 100.0, "house": 1, "sign": "Cancer"},
                {"planet": "Moon", "longitude": 280.0, "house": 6, "sign": "Capricorn"},
                {"planet": "Saturn", "longitude": 10.0, "house": 10, "sign": "Aries"},
                {"planet": "Venus", "longitude": 130.0, "house": 11, "sign": "Leo"},
                {"planet": "Jupiter", "longitude": 140.0, "house": 3, "sign": "Leo"},
            ],
            "house_rulers": {"1": "Sun", "3": "Sun", "4": "Venus", "5": "Jupiter", "7": "Saturn", "8": "Mars", "10": "Venus", "11": "Jupiter"},
            "house_cusps": [90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0, 0.0, 30.0, 60.0],
            "all_aspects": [
                {"planet1": "Sun", "planet2": "Saturn", "aspect": "Square", "applying": True, "orb": 2.2},
            ],
        }

        ids = _rule_ids(evaluate(extract_features(dashboard), self.rules))
        self.assertNotIn("public_or_authority_axis_foregrounded", ids)
        self.assertNotIn("public_axis_saturated", ids)
        self.assertNotIn("public_figure_or_leader_axis", ids)

    def test_public_rule_does_not_fire_from_tenth_count_plus_eighth_rulership_alone(self):
        dashboard = {
            "planets": [
                {"planet": "Sun", "longitude": 10.0, "house": 10, "sign": "Aries"},
                {"planet": "Moon", "longitude": 85.0, "house": 3, "sign": "Gemini"},
                {"planet": "Venus", "longitude": 350.0, "house": 9, "sign": "Pisces"},
                {"planet": "Saturn", "longitude": 130.0, "house": 7, "sign": "Leo"},
            ],
            "house_rulers": {"1": "Venus", "4": "Saturn", "5": "Saturn", "7": "Mars", "8": "Venus", "10": "Moon", "11": "Sun"},
            "house_cusps": [90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0, 0.0, 30.0, 60.0],
            "all_aspects": [
                {"planet1": "Sun", "planet2": "Saturn", "aspect": "Square", "applying": True, "orb": 1.5},
            ],
        }

        ids = _rule_ids(evaluate(extract_features(dashboard), self.rules))
        self.assertNotIn("public_or_authority_axis_foregrounded", ids)
        self.assertNotIn("public_figure_or_leader_axis", ids)

    def test_public_leader_rule_fires_from_angular_sun_and_tenth_axis_link(self):
        dashboard = {
            "planets": [
                {"planet": "Sun", "longitude": 5.0, "house": 7, "sign": "Aries"},
                {"planet": "Moon", "longitude": 250.0, "house": 9, "sign": "Sagittarius"},
                {"planet": "Venus", "longitude": 175.0, "house": 6, "sign": "Virgo"},
                {"planet": "Mars", "longitude": 15.0, "house": 7, "sign": "Aries"},
                {"planet": "Saturn", "longitude": 190.0, "house": 8, "sign": "Libra"},
            ],
            "house_rulers": {"1": "Venus", "3": "Jupiter", "4": "Saturn", "5": "Saturn", "7": "Mars", "8": "Venus", "10": "Moon", "11": "Sun"},
            "house_cusps": [120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0, 0.0, 30.0, 60.0, 90.0],
            "all_aspects": [
                {"planet1": "Sun", "planet2": "Saturn", "aspect": "Opposition", "applying": True, "orb": 5.0},
            ],
        }

        ids = _rule_ids(evaluate(extract_features(dashboard), self.rules))
        self.assertIn("public_figure_or_leader_axis", ids)

    def test_public_rule_fires_from_tenth_ruler_axis_and_moon_under_attack(self):
        dashboard = {
            "planets": [
                {"planet": "Sun", "longitude": 100.0, "house": 10, "sign": "Cancer"},
                {"planet": "Moon", "longitude": 15.0, "house": 1, "sign": "Aries"},
                {"planet": "Venus", "longitude": 265.0, "house": 9, "sign": "Sagittarius"},
                {"planet": "Mars", "longitude": 195.0, "house": 7, "sign": "Libra"},
                {"planet": "Saturn", "longitude": 283.0, "house": 8, "sign": "Capricorn"},
            ],
            "house_rulers": {"1": "Venus", "3": "Jupiter", "4": "Saturn", "7": "Mars", "8": "Venus", "10": "Moon", "11": "Sun"},
            "house_cusps": [0.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0],
            "all_aspects": [
                {"planet1": "Moon", "planet2": "Mars", "aspect": "Opposition", "applying": True, "orb": 0.0},
            ],
        }

        ids = _rule_ids(evaluate(extract_features(dashboard), self.rules))
        self.assertIn("public_or_authority_axis_foregrounded", ids)

    def test_waterborne_disaster_rule_requires_travel_marker_not_public_marker(self):
        dashboard = {
            "planets": [
                {"planet": "Moon", "longitude": 280.0, "house": 9, "sign": "Capricorn"},
                {"planet": "Venus", "longitude": 40.0, "house": 2, "sign": "Taurus"},
                {"planet": "Mars", "longitude": 10.0, "house": 7, "sign": "Aries"},
                {"planet": "Sun", "longitude": 120.0, "house": 4, "sign": "Leo"},
            ],
            "house_rulers": {"1": "Venus", "3": "Moon", "4": "Moon", "5": "Sun", "7": "Mars", "8": "Jupiter", "10": "Venus", "11": "Sun"},
            "house_cusps": [30.0, 60.0, 90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0, 0.0],
            "all_aspects": [
                {"planet1": "Moon", "planet2": "Mars", "aspect": "Square", "applying": True, "orb": 0.3},
            ],
        }

        ids = _rule_ids(evaluate(extract_features(dashboard), self.rules))
        self.assertNotIn("waterborne_accident_or_disaster_pattern", ids)

    def test_family_child_rules_can_fire_from_child_house_plus_parental_axis_under_hidden_pressure(self):
        dashboard = {
            "planets": [
                {"planet": "Mercury", "longitude": 95.0, "house": 12, "sign": "Cancer"},
                {"planet": "Moon", "longitude": 145.0, "house": 5, "sign": "Leo"},
                {"planet": "Jupiter", "longitude": 15.0, "house": 10, "sign": "Aries"},
                {"planet": "Saturn", "longitude": 205.0, "house": 7, "sign": "Libra"},
                {"planet": "Mars", "longitude": 305.0, "house": 10, "sign": "Aquarius"},
            ],
            "house_rulers": {"1": "Mercury", "3": "Mars", "4": "Jupiter", "5": "Saturn", "7": "Jupiter", "8": "Moon", "10": "Mercury", "11": "Moon"},
            "house_cusps": [90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0, 0.0, 30.0, 60.0],
            "all_aspects": [
                {"planet1": "Jupiter", "planet2": "Mars", "aspect": "Square", "applying": True, "orb": 1.0},
                {"planet1": "Mercury", "planet2": "Saturn", "aspect": "Trine", "applying": False, "orb": 0.6},
            ],
        }

        ids = _rule_ids(evaluate(extract_features(dashboard), self.rules))
        self.assertIn("family_parental_axis_homicide", ids)
        self.assertIn("child_family_overlap", ids)

    def test_disaster_rules_back_off_when_deceptive_public_assignment_seizure_structure_is_present(self):
        dashboard = {
            "planets": [
                {"planet": "Jupiter", "longitude": 250.0, "house": 1, "sign": "Sagittarius"},
                {"planet": "Mercury", "longitude": 315.0, "house": 2, "sign": "Aquarius", "retrograde": True},
                {"planet": "Sun", "longitude": 318.0, "house": 2, "sign": "Aquarius"},
                {"planet": "Moon", "longitude": 350.0, "house": 3, "sign": "Pisces"},
                {"planet": "Saturn", "longitude": 105.0, "house": 9, "sign": "Cancer"},
                {"planet": "Mars", "longitude": 15.0, "house": 7, "sign": "Aries"},
            ],
            "house_rulers": {"1": "Jupiter", "3": "Saturn", "7": "Mercury", "8": "Sun", "9": "Moon", "10": "Mercury"},
            "house_cusps": [90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0, 0.0, 30.0, 60.0],
            "all_aspects": [
                {"planet1": "Moon", "planet2": "Mars", "aspect": "Conjunction", "applying": False, "orb": 5.0},
            ],
            "solar_conditions": {
                "combustion": [{"planet": "Mercury"}],
            },
        }

        ids = _rule_ids(evaluate(extract_features(dashboard), self.rules))
        self.assertIn("abduction_deceptive_public_or_assignment_seizure_signature", ids)
        travel = next(
            finding
            for finding in evaluate(extract_features(dashboard), self.rules)
            if finding["id"] == "travel_accident_or_disaster_pattern"
        )
        self.assertFalse(travel["scoring_eligible"])
        self.assertNotIn("waterborne_accident_or_disaster_pattern", ids)

    def test_disaster_rules_back_off_when_known_person_social_concealment_pattern_is_present(self):
        dashboard = {
            "planets": [
                {"planet": "Mars", "longitude": 80.0, "house": 3, "sign": "Gemini"},
                {"planet": "Venus", "longitude": 30.0, "house": 2, "sign": "Taurus"},
                {"planet": "Mercury", "longitude": 230.0, "house": 1, "sign": "Scorpio"},
                {"planet": "Sun", "longitude": 200.0, "house": 12, "sign": "Libra"},
                {"planet": "Moon", "longitude": 355.0, "house": 6, "sign": "Pisces"},
                {"planet": "Saturn", "longitude": 20.0, "house": 10, "sign": "Aries"},
            ],
            "house_rulers": {"1": "Mars", "3": "Moon", "5": "Mars", "7": "Venus", "8": "Mercury", "10": "Mercury", "11": "Venus"},
            "house_cusps": [90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0, 0.0, 30.0, 60.0],
            "all_aspects": [
                {"planet1": "Moon", "planet2": "Saturn", "aspect": "Conjunction", "applying": True, "orb": 5.0},
            ],
        }

        ids = _rule_ids(evaluate(extract_features(dashboard), self.rules))
        self.assertIn("violence_known_person_social_concealment_pattern", ids)
        self.assertNotIn("waterborne_accident_or_disaster_pattern", ids)


if __name__ == "__main__":
    unittest.main()
