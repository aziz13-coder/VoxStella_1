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


class ForensicDirectionalRuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rules = load_knowledge(str(KNOWLEDGE_DIR))

    def test_abduction_child_and_violence_rules_fire_from_grounded_overlap(self):
        dashboard = {
            "planets": [
                {"planet": "Venus", "longitude": 350.0, "house": 12, "sign": "Pisces"},
                {"planet": "Mars", "longitude": 100.0, "house": 4, "sign": "Cancer"},
                {"planet": "Moon", "longitude": 145.0, "house": 5, "sign": "Leo"},
                {"planet": "Saturn", "longitude": 275.0, "house": 9, "sign": "Capricorn"},
                {"planet": "Sun", "longitude": 148.0, "house": 5, "sign": "Leo"},
                {"planet": "Neptune", "longitude": 100.0, "house": 12, "sign": "Cancer"},
            ],
            "house_rulers": {"1": "Venus", "5": "Moon", "7": "Mars", "8": "Venus"},
            "house_cusps": [330.0, 0.0, 30.0, 90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0],
            "all_aspects": [
                {"planet1": "Moon", "planet2": "Saturn", "aspect": "Square", "applying": True, "orb": 1.2},
                {"planet1": "Mars", "planet2": "Neptune", "aspect": "Conjunction", "applying": True, "orb": 0.0},
            ],
        }

        findings = evaluate(extract_features(dashboard), self.rules)
        ids = _rule_ids(findings)
        self.assertIn("violence_life_death_overlap", ids)
        self.assertIn("child_house_under_stress", ids)
        self.assertIn("abduction_missing_person_signature", ids)

    def test_abduction_transport_rule_fires_from_abductor_plus_movement_and_coercion(self):
        dashboard = {
            "planets": [
                {"planet": "Saturn", "longitude": 170.0, "house": 6, "sign": "Virgo"},
                {"planet": "Sun", "longitude": 252.0, "house": 8, "sign": "Sagittarius"},
                {"planet": "Moon", "longitude": 41.0, "house": 3, "sign": "Taurus"},
                {"planet": "Mars", "longitude": 41.2, "house": 3, "sign": "Taurus"},
                {"planet": "Venus", "longitude": 300.0, "house": 10, "sign": "Aquarius"},
                {"planet": "Jupiter", "longitude": 247.0, "house": 8, "sign": "Sagittarius"},
            ],
            "house_rulers": {"1": "Saturn", "3": "Venus", "7": "Sun", "8": "Mars", "9": "Jupiter", "11": "Jupiter"},
            "house_cusps": [15.0, 45.0, 75.0, 105.0, 135.0, 165.0, 195.0, 225.0, 255.0, 285.0, 315.0, 345.0],
            "all_aspects": [
                {"planet1": "Moon", "planet2": "Mars", "aspect": "Conjunction", "applying": False, "orb": 0.2},
            ],
        }

        findings = evaluate(extract_features(dashboard), self.rules)
        ids = _rule_ids(findings)
        self.assertIn("abduction_transport_or_public_seizure_signature", ids)

    def test_abduction_public_place_rule_fires_from_public_meeting_plus_hidden_custody_pressure(self):
        dashboard = {
            "planets": [
                {"planet": "Mercury", "longitude": 275.0, "house": 8, "sign": "Capricorn"},
                {"planet": "Sun", "longitude": 15.0, "house": 10, "sign": "Aries"},
                {"planet": "Mars", "longitude": 20.0, "house": 8, "sign": "Aries"},
                {"planet": "Moon", "longitude": 140.0, "house": 5, "sign": "Leo"},
                {"planet": "Saturn", "longitude": 200.0, "house": 7, "sign": "Libra"},
            ],
            "house_rulers": {"1": "Mercury", "3": "Venus", "7": "Sun", "8": "Saturn", "9": "Moon", "10": "Mars"},
            "house_cusps": [240.0, 270.0, 300.0, 330.0, 0.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0, 210.0],
            "all_aspects": [
                {"planet1": "Mercury", "planet2": "Saturn", "aspect": "Square", "applying": True, "orb": 1.0},
            ],
        }

        findings = evaluate(extract_features(dashboard), self.rules)
        ids = _rule_ids(findings)
        self.assertIn("abduction_public_place_seizure_signature", ids)

    def test_abduction_worksite_rule_fires_from_assignment_meeting_plus_public_coercion(self):
        dashboard = {
            "planets": [
                {"planet": "Mercury", "longitude": 155.0, "house": 6, "sign": "Virgo"},
                {"planet": "Venus", "longitude": 150.0, "house": 6, "sign": "Virgo"},
                {"planet": "Mars", "longitude": 158.0, "house": 6, "sign": "Virgo"},
                {"planet": "Jupiter", "longitude": 153.0, "house": 6, "sign": "Virgo"},
                {"planet": "Moon", "longitude": 45.0, "house": 2, "sign": "Taurus"},
                {"planet": "Saturn", "longitude": 230.0, "house": 8, "sign": "Scorpio"},
            ],
            "house_rulers": {"1": "Mercury", "3": "Venus", "5": "Mars", "6": "Jupiter", "7": "Jupiter", "9": "Moon", "10": "Saturn"},
            "house_cusps": [0.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0],
            "all_aspects": [
                {"planet1": "Saturn", "planet2": "Mercury", "aspect": "Sextile", "applying": False, "orb": 5.0},
                {"planet1": "Saturn", "planet2": "Jupiter", "aspect": "Sextile", "applying": False, "orb": 2.0},
            ],
        }

        findings = evaluate(extract_features(dashboard), self.rules)
        ids = _rule_ids(findings)
        self.assertIn("abduction_worksite_or_assignment_seizure_signature", ids)

    def test_abduction_assignment_route_rule_fires_from_work_link_plus_travel_and_public_pressure(self):
        dashboard = {
            "planets": [
                {"planet": "Mercury", "longitude": 308.5, "house": 8, "sign": "Aquarius"},
                {"planet": "Sun", "longitude": 315.7, "house": 9, "sign": "Aquarius"},
                {"planet": "Moon", "longitude": 253.2, "house": 6, "sign": "Sagittarius"},
                {"planet": "Mars", "longitude": 268.4, "house": 7, "sign": "Sagittarius"},
                {"planet": "Jupiter", "longitude": 198.9, "house": 5, "sign": "Libra"},
                {"planet": "Saturn", "longitude": 112.2, "house": 2, "sign": "Cancer"},
                {"planet": "Venus", "longitude": 302.2, "house": 8, "sign": "Aquarius"},
            ],
            "house_rulers": {"1": "Mercury", "3": "Sun", "6": "Mars", "7": "Jupiter", "8": "Saturn", "9": "Saturn", "10": "Jupiter"},
            "house_cusps": [87.09, 111.65, 133.53, 158.71, 193.07, 233.81, 267.09, 291.65, 313.53, 338.71, 13.07, 53.81],
            "all_aspects": [
                {"planet1": "Jupiter", "planet2": "Saturn", "aspect": "Square", "applying": True, "orb": 3.33},
                {"planet1": "Sun", "planet2": "Jupiter", "aspect": "Trine", "applying": True, "orb": 3.13},
            ],
        }

        findings = evaluate(extract_features(dashboard), self.rules)
        ids = _rule_ids(findings)
        self.assertIn("abduction_worksite_or_assignment_seizure_signature", ids)

    def test_abduction_transient_hospitality_rule_fires_from_hotel_style_seizure_pattern(self):
        dashboard = {
            "planets": [
                {"planet": "Venus", "longitude": 95.0, "house": 3, "sign": "Cancer"},
                {"planet": "Moon", "longitude": 100.0, "house": 3, "sign": "Cancer"},
                {"planet": "Saturn", "longitude": 110.0, "house": 3, "sign": "Cancer"},
                {"planet": "Sun", "longitude": 130.0, "house": 5, "sign": "Leo"},
                {"planet": "Mercury", "longitude": 155.0, "house": 5, "sign": "Virgo"},
                {"planet": "Mars", "longitude": 158.0, "house": 5, "sign": "Virgo"},
                {"planet": "Jupiter", "longitude": 162.0, "house": 5, "sign": "Virgo"},
                {"planet": "North Node", "longitude": 35.0, "house": 1, "sign": "Taurus"},
            ],
            "house_rulers": {"1": "Venus", "3": "Moon", "5": "Sun", "7": "Mars", "8": "Jupiter", "9": "Saturn", "10": "Saturn"},
            "house_cusps": [30.0, 60.0, 90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0, 0.0],
            "all_aspects": [
                {"planet1": "Mercury", "planet2": "North Node", "aspect": "Trine", "applying": False, "orb": 0.0},
            ],
        }

        findings = evaluate(extract_features(dashboard), self.rules)
        ids = _rule_ids(findings)
        self.assertIn("abduction_transient_hospitality_seizure_signature", ids)

    def test_domestic_rule_fires_without_promoting_family_label_from_home_overlap_alone(self):
        dashboard = {
            "planets": [
                {"planet": "Jupiter", "longitude": 355.0, "house": 12, "sign": "Pisces"},
                {"planet": "Mercury", "longitude": 25.0, "house": 2, "sign": "Aries"},
                {"planet": "Moon", "longitude": 95.0, "house": 4, "sign": "Cancer"},
                {"planet": "Venus", "longitude": 188.0, "house": 7, "sign": "Libra"},
                {"planet": "Saturn", "longitude": 278.0, "house": 10, "sign": "Capricorn"},
            ],
            "house_rulers": {"1": "Jupiter", "4": "Moon", "7": "Mercury", "8": "Mars"},
            "house_cusps": [330.0, 0.0, 30.0, 90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0],
            "all_aspects": [
                {"planet1": "Jupiter", "planet2": "Mercury", "aspect": "Square", "applying": True, "orb": 0.8},
                {"planet1": "Venus", "planet2": "Saturn", "aspect": "Square", "applying": False, "orb": 1.1},
            ],
        }

        findings = evaluate(extract_features(dashboard), self.rules)
        ids = _rule_ids(findings)
        self.assertIn("domestic_partner_axis_contact", ids)
        self.assertNotIn("family_domestic_moon_signature", ids)
        self.assertNotIn("family_home_axis_under_pressure", ids)

    def test_water_rule_fires_from_water_moon_and_hidden_neptune(self):
        dashboard = {
            "planets": [
                {"planet": "Mercury", "longitude": 108.0, "house": 4, "sign": "Cancer"},
                {"planet": "Moon", "longitude": 98.0, "house": 8, "sign": "Cancer"},
                {"planet": "Mars", "longitude": 278.0, "house": 2, "sign": "Capricorn"},
                {"planet": "Neptune", "longitude": 340.0, "house": 12, "sign": "Pisces"},
            ],
            "house_rulers": {"1": "Mercury", "4": "Moon", "7": "Jupiter", "8": "Saturn"},
            "house_cusps": [330.0, 0.0, 30.0, 90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0],
            "all_aspects": [
                {"planet1": "Moon", "planet2": "Mars", "aspect": "Opposition", "applying": True, "orb": 0.7},
            ],
        }

        findings = evaluate(extract_features(dashboard), self.rules)
        ids = _rule_ids(findings)
        self.assertIn("water_disappearance_signatures", ids)

    def test_family_cluster_and_hidden_8th_malefic_rules_fire_for_child_family_homicide_pattern(self):
        dashboard = {
            "planets": [
                {"planet": "Sun", "longitude": 85.0, "house": 5, "sign": "Gemini"},
                {"planet": "Moon", "longitude": 332.0, "house": 12, "sign": "Pisces"},
                {"planet": "Jupiter", "longitude": 82.0, "house": 5, "sign": "Gemini"},
                {"planet": "Saturn", "longitude": 215.0, "house": 8, "sign": "Scorpio"},
                {"planet": "Mars", "longitude": 130.0, "house": 5, "sign": "Leo"},
            ],
            "house_rulers": {"1": "Sun", "4": "Venus", "5": "Jupiter", "7": "Saturn", "8": "Saturn", "10": "Mars"},
            "house_cusps": [60.0, 90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0, 0.0, 30.0],
            "all_aspects": [
                {"planet1": "Moon", "planet2": "Saturn", "aspect": "Opposition", "applying": True, "orb": 0.8},
            ],
        }

        findings = evaluate(extract_features(dashboard), self.rules)
        ids = _rule_ids(findings)
        self.assertIn("family_child_rulers_clustered", ids)
        self.assertIn("violence_malefic_in_8th_with_hidden_context", ids)

    def test_child_rule_fires_from_fifth_house_malefic_filicide_pattern(self):
        dashboard = {
            "planets": [
                {"planet": "Sun", "longitude": 45.0, "house": 5, "sign": "Taurus"},
                {"planet": "Mercury", "longitude": 50.0, "house": 5, "sign": "Taurus"},
                {"planet": "Mars", "longitude": 70.0, "house": 5, "sign": "Gemini"},
                {"planet": "Moon", "longitude": 170.0, "house": 8, "sign": "Virgo"},
                {"planet": "Jupiter", "longitude": 255.0, "house": 12, "sign": "Sagittarius"},
                {"planet": "Saturn", "longitude": 190.0, "house": 10, "sign": "Libra"},
                {"planet": "Venus", "longitude": 100.0, "house": 7, "sign": "Cancer"},
            ],
            "house_rulers": {"1": "Jupiter", "4": "Mars", "5": "Venus", "7": "Mercury", "8": "Moon", "10": "Venus"},
            "house_cusps": [240.0, 270.0, 300.0, 330.0, 0.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0, 210.0],
            "all_aspects": [],
        }

        findings = evaluate(extract_features(dashboard), self.rules)
        ids = _rule_ids(findings)
        self.assertIn("child_house_under_stress", ids)

    def test_witness_and_friend_rules_fire_from_3rd_11th_links(self):
        dashboard = {
            "planets": [
                {"planet": "Venus", "longitude": 15.0, "house": 10, "sign": "Aries"},
                {"planet": "Moon", "longitude": 345.0, "house": 12, "sign": "Pisces"},
                {"planet": "Mercury", "longitude": 115.0, "house": 9, "sign": "Cancer"},
                {"planet": "Mars", "longitude": 305.0, "house": 11, "sign": "Aquarius"},
                {"planet": "Saturn", "longitude": 210.0, "house": 8, "sign": "Scorpio"},
            ],
            "house_rulers": {"1": "Venus", "3": "Moon", "7": "Mars", "8": "Venus", "10": "Moon", "11": "Mercury"},
            "house_cusps": [180.0, 210.0, 240.0, 270.0, 300.0, 330.0, 0.0, 30.0, 60.0, 90.0, 120.0, 150.0],
            "all_aspects": [
                {"planet1": "Venus", "planet2": "Mars", "aspect": "Sextile", "applying": True, "orb": 0.6},
            ],
        }

        findings = evaluate(extract_features(dashboard), self.rules)
        ids = _rule_ids(findings)
        self.assertIn("witness_or_accomplice_signature", ids)
        self.assertIn("friend_or_associate_axis_active", ids)

    def test_public_axis_rule_fires_from_tenth_ruler_foregrounded_with_hidden_victim(self):
        dashboard = {
            "planets": [
                {"planet": "Sun", "longitude": 350.0, "house": 12, "sign": "Pisces"},
                {"planet": "Moon", "longitude": 220.0, "house": 4, "sign": "Scorpio"},
                {"planet": "Venus", "longitude": 12.0, "house": 1, "sign": "Aries"},
                {"planet": "Mars", "longitude": 45.0, "house": 2, "sign": "Taurus"},
                {"planet": "Saturn", "longitude": 265.0, "house": 9, "sign": "Sagittarius"},
            ],
            "house_rulers": {"1": "Sun", "4": "Mars", "7": "Saturn", "8": "Jupiter", "10": "Venus"},
            "house_cusps": [330.0, 0.0, 30.0, 90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0],
            "all_aspects": [
                {"planet1": "Sun", "planet2": "Moon", "aspect": "Trine", "applying": False, "orb": 0.4},
            ],
        }

        findings = evaluate(extract_features(dashboard), self.rules)
        ids = _rule_ids(findings)
        self.assertIn("public_or_authority_axis_foregrounded", ids)

    def test_partner_linked_homicide_rule_fires_for_known_spouse_pattern(self):
        dashboard = {
            "planets": [
                {"planet": "Jupiter", "longitude": 74.39, "house": 7, "sign": "Gemini"},
                {"planet": "Mercury", "longitude": 58.04, "house": 6, "sign": "Taurus"},
                {"planet": "Moon", "longitude": 194.06, "house": 10, "sign": "Libra"},
                {"planet": "Venus", "longitude": 5.39, "house": 4, "sign": "Aries"},
                {"planet": "Saturn", "longitude": 61.75, "house": 6, "sign": "Gemini"},
                {"planet": "Mars", "longitude": 268.79, "house": 1, "sign": "Sagittarius"},
            ],
            "house_rulers": {"1": "Jupiter", "4": "Jupiter", "5": "Mars", "7": "Mercury", "8": "Moon", "10": "Mercury"},
            "house_cusps": [240.0, 270.0, 300.0, 330.0, 0.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0, 210.0],
            "all_aspects": [
                {"planet1": "Mercury", "planet2": "Saturn", "aspect": "Conjunction", "applying": True, "orb": 3.7},
                {"planet1": "Moon", "planet2": "Venus", "aspect": "Opposition", "applying": False, "orb": 8.7},
            ],
        }

        findings = evaluate(extract_features(dashboard), self.rules)
        ids = _rule_ids(findings)
        self.assertIn("domestic_partner_known_spouse_homicide", ids)

    def test_home_entry_service_pretext_violence_rule_fires_from_home_and_service_axes(self):
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

        findings = evaluate(extract_features(dashboard), self.rules)
        ids = _rule_ids(findings)
        self.assertIn("violence_home_entry_service_pretext_pattern", ids)

    def test_parental_homicide_and_public_saturation_rules_fire_from_5th_10th_cluster(self):
        dashboard = {
            "planets": [
                {"planet": "Sun", "longitude": 12.25, "house": 10, "sign": "Aries"},
                {"planet": "Moon", "longitude": 15.70, "house": 10, "sign": "Aries"},
                {"planet": "Mercury", "longitude": 31.11, "house": 10, "sign": "Taurus"},
                {"planet": "Mars", "longitude": 238.26, "house": 5, "sign": "Scorpio"},
                {"planet": "Saturn", "longitude": 225.26, "house": 5, "sign": "Scorpio"},
                {"planet": "Jupiter", "longitude": 281.76, "house": 6, "sign": "Capricorn"},
                {"planet": "Venus", "longitude": 352.57, "house": 9, "sign": "Pisces"},
            ],
            "house_rulers": {"1": "Moon", "4": "Venus", "5": "Mars", "7": "Saturn", "8": "Jupiter", "10": "Mars", "11": "Venus", "3": "Mercury"},
            "house_cusps": [90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0, 0.0, 30.0, 60.0],
            "all_aspects": [
                {"planet1": "Sun", "planet2": "Jupiter", "aspect": "Square", "applying": False, "orb": 0.5},
                {"planet1": "Moon", "planet2": "Jupiter", "aspect": "Square", "applying": False, "orb": 3.9},
            ],
        }

        findings = evaluate(extract_features(dashboard), self.rules)
        ids = _rule_ids(findings)
        self.assertIn("family_parental_axis_homicide", ids)
        self.assertIn("public_axis_saturated", ids)

    def test_disaster_rules_fire_without_family_child_or_domestic_false_positives(self):
        dashboard = {
            "planets": [
                {"planet": "Sun", "longitude": 70.0, "house": 5, "sign": "Gemini"},
                {"planet": "Moon", "longitude": 340.0, "house": 9, "sign": "Pisces"},
                {"planet": "Mercury", "longitude": 72.0, "house": 5, "sign": "Gemini"},
                {"planet": "Venus", "longitude": 121.0, "house": 4, "sign": "Leo"},
                {"planet": "Mars", "longitude": 160.0, "house": 4, "sign": "Virgo"},
                {"planet": "Saturn", "longitude": 170.0, "house": 9, "sign": "Virgo"},
            ],
            "house_rulers": {"1": "Saturn", "3": "Saturn", "4": "Jupiter", "5": "Venus", "7": "Moon", "8": "Sun", "10": "Mercury"},
            "house_cusps": [270.0, 300.0, 330.0, 360.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0, 210.0, 240.0],
            "all_aspects": [
                {"planet1": "Moon", "planet2": "Mars", "aspect": "Opposition", "applying": True, "orb": 0.0},
            ],
        }

        findings = evaluate(extract_features(dashboard), self.rules)
        ids = _rule_ids(findings)
        self.assertIn("travel_accident_or_disaster_pattern", ids)
        self.assertNotIn("child_house_under_stress", ids)
        self.assertNotIn("family_home_axis_under_pressure", ids)
        self.assertNotIn("domestic_partner_axis_contact", ids)

    def test_waterborne_disaster_rule_avoids_abduction_and_child_false_positive(self):
        dashboard = {
            "planets": [
                {"planet": "Sun", "longitude": 125.0, "house": 5, "sign": "Leo"},
                {"planet": "Moon", "longitude": 170.0, "house": 2, "sign": "Virgo"},
                {"planet": "Mercury", "longitude": 302.0, "house": 7, "sign": "Aquarius"},
                {"planet": "Venus", "longitude": 50.0, "house": 7, "sign": "Taurus"},
                {"planet": "Mars", "longitude": 40.0, "house": 2, "sign": "Taurus"},
                {"planet": "Saturn", "longitude": 333.0, "house": 3, "sign": "Pisces"},
            ],
            "house_rulers": {"1": "Sun", "3": "Venus", "4": "Mars", "5": "Jupiter", "7": "Saturn", "8": "Jupiter", "10": "Venus"},
            "house_cusps": [120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0, 0.0, 30.0, 60.0, 90.0],
            "all_aspects": [
                {"planet1": "Moon", "planet2": "Mars", "aspect": "Square", "applying": True, "orb": 1.5},
            ],
        }

        findings = evaluate(extract_features(dashboard), self.rules)
        ids = _rule_ids(findings)
        self.assertIn("waterborne_accident_or_disaster_pattern", ids)
        self.assertNotIn("abduction_missing_person_signature", ids)
        self.assertNotIn("child_house_under_stress", ids)

    def test_partner_home_axis_rule_does_not_fire_from_home_overlap_alone(self):
        dashboard = {
            "planets": [
                {"planet": "Jupiter", "longitude": 120.0, "house": 4, "sign": "Leo"},
                {"planet": "Mercury", "longitude": 122.0, "house": 4, "sign": "Leo"},
                {"planet": "Moon", "longitude": 150.0, "house": 6, "sign": "Virgo"},
                {"planet": "Venus", "longitude": 158.0, "house": 6, "sign": "Virgo"},
                {"planet": "Saturn", "longitude": 20.0, "house": 7, "sign": "Aries"},
            ],
            "house_rulers": {"1": "Jupiter", "4": "Mercury", "7": "Mercury", "8": "Mars", "11": "Saturn"},
            "house_cusps": [30.0, 60.0, 90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0, 0.0],
            "all_aspects": [
                {"planet1": "Jupiter", "planet2": "Mercury", "aspect": "Conjunction", "applying": False, "orb": 2.0},
                {"planet1": "Moon", "planet2": "Venus", "aspect": "Conjunction", "applying": False, "orb": 8.0},
            ],
        }

        findings = evaluate(extract_features(dashboard), self.rules)
        ids = _rule_ids(findings)
        self.assertNotIn("domestic_partner_near_home_axis", ids)

    def test_air_disaster_rule_fires_from_aquarian_launch_and_hidden_traveler_axis(self):
        dashboard = {
            "planets": [
                {"planet": "Sun", "longitude": 115.7, "house": 6, "sign": "Cancer"},
                {"planet": "Moon", "longitude": 141.2, "house": 7, "sign": "Leo"},
                {"planet": "Mercury", "longitude": 123.3, "house": 7, "sign": "Leo"},
                {"planet": "Venus", "longitude": 76.0, "house": 5, "sign": "Gemini"},
                {"planet": "Mars", "longitude": 84.7, "house": 5, "sign": "Gemini"},
                {"planet": "Jupiter", "longitude": 281.1, "house": 12, "sign": "Capricorn", "retrograde": True},
                {"planet": "Saturn", "longitude": 7.4, "house": 2, "sign": "Aries"},
                {"planet": "North Node", "longitude": 191.9, "house": 8, "sign": "Libra", "retrograde": True},
            ],
            "house_rulers": {"1": "Saturn", "3": "Mars", "4": "Venus", "5": "Mercury", "7": "Sun", "8": "Mercury", "10": "Mars", "11": "Jupiter"},
            "house_cusps": [300.09, 345.19, 27.32, 53.15, 72.07, 91.67, 120.09, 165.19, 207.32, 233.15, 252.07, 271.67],
            "all_aspects": [
                {"planet1": "Mercury", "planet2": "Sun", "aspect": "Conjunction", "applying": False, "orb": 7.62},
            ],
            "solar_conditions": {
                "combustion": [{"planet": "Mercury"}],
            },
        }

        findings = evaluate(extract_features(dashboard), self.rules)
        ids = _rule_ids(findings)
        self.assertIn("air_disaster_launch_pattern", ids)

    def test_structural_catastrophe_rule_fires_from_capricorn_axis_and_cazimi_cluster(self):
        dashboard = {
            "planets": [
                {"planet": "Sun", "longitude": 292.6, "house": 7, "sign": "Capricorn"},
                {"planet": "Moon", "longitude": 266.5, "house": 6, "sign": "Sagittarius"},
                {"planet": "Mercury", "longitude": 276.1, "house": 6, "sign": "Capricorn", "retrograde": True},
                {"planet": "Venus", "longitude": 292.8, "house": 7, "sign": "Capricorn"},
                {"planet": "Mars", "longitude": 136.0, "house": 2, "sign": "Leo", "retrograde": True},
                {"planet": "Jupiter", "longitude": 328.9, "house": 8, "sign": "Aquarius"},
                {"planet": "Saturn", "longitude": 184.7, "house": 3, "sign": "Libra"},
                {"planet": "North Node", "longitude": 291.0, "house": 7, "sign": "Capricorn", "retrograde": True},
            ],
            "house_rulers": {"1": "Moon", "3": "Mercury", "4": "Venus", "5": "Mars", "7": "Saturn", "8": "Saturn", "10": "Mars", "11": "Venus"},
            "house_cusps": [106.06, 132.13, 159.23, 190.28, 224.71, 257.56, 286.06, 312.13, 339.23, 10.28, 44.71, 77.56],
            "all_aspects": [
                {"planet1": "Moon", "planet2": "Saturn", "aspect": "Square", "applying": True, "orb": 8.14},
            ],
            "solar_conditions": {
                "cazimi": [{"planet": "Venus"}],
            },
        }

        findings = evaluate(extract_features(dashboard), self.rules)
        ids = _rule_ids(findings)
        self.assertIn("structural_catastrophe_pattern", ids)

    def test_family_parricide_rule_fires_from_parental_axis_and_child_cluster(self):
        dashboard = {
            "planets": [
                {"planet": "Sun", "longitude": 128.5, "house": 4, "sign": "Leo"},
                {"planet": "Moon", "longitude": 306.6, "house": 10, "sign": "Aquarius"},
                {"planet": "Mercury", "longitude": 122.6, "house": 4, "sign": "Leo", "retrograde": True},
                {"planet": "Venus", "longitude": 102.6, "house": 3, "sign": "Cancer"},
                {"planet": "Mars", "longitude": 104.1, "house": 3, "sign": "Cancer"},
                {"planet": "Jupiter", "longitude": 109.0, "house": 4, "sign": "Cancer"},
                {"planet": "Saturn", "longitude": 359.3, "house": 12, "sign": "Pisces", "retrograde": True},
            ],
            "house_rulers": {"1": "Mars", "4": "Moon", "5": "Sun", "7": "Venus", "8": "Jupiter", "10": "Saturn", "11": "Saturn"},
            "house_cusps": [28.65, 63.12, 87.58, 108.69, 132.77, 166.52, 208.65, 243.12, 267.58, 288.69, 312.77, 346.52],
            "all_aspects": [
                {"planet1": "Moon", "planet2": "Sun", "aspect": "Opposition", "applying": True, "orb": 1.87},
                {"planet1": "Moon", "planet2": "Mercury", "aspect": "Opposition", "applying": False, "orb": 4.07},
                {"planet1": "Mars", "planet2": "Venus", "aspect": "Conjunction", "applying": True, "orb": 1.45},
                {"planet1": "Mars", "planet2": "Jupiter", "aspect": "Conjunction", "applying": True, "orb": 4.96},
                {"planet1": "Venus", "planet2": "Jupiter", "aspect": "Conjunction", "applying": True, "orb": 6.41},
            ],
        }

        findings = evaluate(extract_features(dashboard), self.rules)
        ids = _rule_ids(findings)
        self.assertIn("family_parricide_homicide_cluster", ids)

    def test_cancer_moon_and_home_ruler_in_4th_do_not_force_family_or_child_labels(self):
        dashboard = {
            "planets": [
                {"planet": "Venus", "longitude": 202.0, "house": 2, "sign": "Libra"},
                {"planet": "Moon", "longitude": 110.0, "house": 9, "sign": "Cancer"},
                {"planet": "Mercury", "longitude": 225.0, "house": 2, "sign": "Scorpio"},
                {"planet": "Sun", "longitude": 230.0, "house": 2, "sign": "Scorpio"},
                {"planet": "Mars", "longitude": 70.0, "house": 9, "sign": "Gemini"},
                {"planet": "Jupiter", "longitude": 350.0, "house": 5, "sign": "Pisces"},
                {"planet": "Saturn", "longitude": 305.0, "house": 4, "sign": "Aquarius"},
            ],
            "house_rulers": {"1": "Venus", "4": "Saturn", "5": "Jupiter", "7": "Mars", "8": "Venus"},
            "house_cusps": [180.0, 210.0, 240.0, 270.0, 300.0, 330.0, 0.0, 30.0, 60.0, 90.0, 120.0, 150.0],
            "all_aspects": [
                {"planet1": "Mercury", "planet2": "Sun", "aspect": "Conjunction", "applying": False, "orb": 5.0},
                {"planet1": "Jupiter", "planet2": "Mercury", "aspect": "Trine", "applying": False, "orb": 5.0},
            ],
            "solar_conditions": {
                "combustion": [{"planet": "Mercury"}],
            },
        }

        findings = evaluate(extract_features(dashboard), self.rules)
        ids = _rule_ids(findings)
        self.assertIn("violence_life_death_overlap", ids)
        self.assertNotIn("family_domestic_moon_signature", ids)
        self.assertNotIn("family_home_axis_under_pressure", ids)
        self.assertNotIn("child_family_overlap", ids)

    def test_abduction_social_rule_fires_from_group_setting_plus_hidden_custody(self):
        dashboard = {
            "planets": [
                {"planet": "Mars", "longitude": 80.0, "house": 3, "sign": "Gemini"},
                {"planet": "Venus", "longitude": 135.0, "house": 5, "sign": "Leo"},
                {"planet": "Mercury", "longitude": 150.0, "house": 5, "sign": "Virgo", "retrograde": True},
                {"planet": "Sun", "longitude": 140.0, "house": 5, "sign": "Leo"},
                {"planet": "Jupiter", "longitude": 345.0, "house": 12, "sign": "Pisces"},
                {"planet": "Moon", "longitude": 220.0, "house": 1, "sign": "Scorpio"},
            ],
            "house_rulers": {"1": "Mars", "5": "Jupiter", "7": "Venus", "8": "Saturn", "11": "Mercury"},
            "house_cusps": [210.0, 240.0, 270.0, 300.0, 330.0, 0.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0],
            "all_aspects": [
                {"planet1": "Mars", "planet2": "Venus", "aspect": "Square", "applying": True, "orb": 5.0},
            ],
            "solar_conditions": {
                "combustion": [{"planet": "Mercury"}],
            },
        }

        ids = _rule_ids(evaluate(extract_features(dashboard), self.rules))
        self.assertIn("abduction_social_or_group_gathering_seizure_signature", ids)

    def test_abduction_deceptive_public_assignment_rule_fires_from_shared_7th_10th_axis(self):
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
            "house_cusps": [240.0, 270.0, 300.0, 330.0, 0.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0, 210.0],
            "all_aspects": [
                {"planet1": "Moon", "planet2": "Mars", "aspect": "Conjunction", "applying": False, "orb": 5.0},
            ],
            "solar_conditions": {
                "combustion": [{"planet": "Mercury"}],
            },
        }

        ids = _rule_ids(evaluate(extract_features(dashboard), self.rules))
        self.assertIn("abduction_deceptive_public_or_assignment_seizure_signature", ids)

    def test_friend_rule_fires_from_shared_seventh_and_eleventh_ruler(self):
        dashboard = {
            "planets": [
                {"planet": "Mars", "longitude": 80.0, "house": 3, "sign": "Gemini"},
                {"planet": "Venus", "longitude": 30.0, "house": 2, "sign": "Taurus"},
                {"planet": "Sun", "longitude": 200.0, "house": 12, "sign": "Libra"},
                {"planet": "Moon", "longitude": 110.0, "house": 6, "sign": "Cancer"},
                {"planet": "Saturn", "longitude": 20.0, "house": 10, "sign": "Aries"},
            ],
            "house_rulers": {"1": "Mars", "5": "Mars", "7": "Venus", "8": "Mercury", "10": "Mercury", "11": "Venus"},
            "house_cusps": [60.0, 90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0, 0.0, 30.0],
            "all_aspects": [
                {"planet1": "Moon", "planet2": "Saturn", "aspect": "Square", "applying": True, "orb": 0.5},
            ],
        }

        ids = _rule_ids(evaluate(extract_features(dashboard), self.rules))
        self.assertIn("friend_or_associate_axis_active", ids)

    def test_known_person_social_concealment_violence_rule_fires_from_after_hours_pattern(self):
        dashboard = {
            "planets": [
                {"planet": "Mars", "longitude": 80.0, "house": 3, "sign": "Gemini"},
                {"planet": "Venus", "longitude": 30.0, "house": 2, "sign": "Taurus"},
                {"planet": "Mercury", "longitude": 230.0, "house": 1, "sign": "Scorpio"},
                {"planet": "Sun", "longitude": 200.0, "house": 12, "sign": "Libra"},
                {"planet": "Moon", "longitude": 110.0, "house": 6, "sign": "Cancer"},
                {"planet": "Saturn", "longitude": 20.0, "house": 10, "sign": "Aries"},
            ],
            "house_rulers": {"1": "Mars", "5": "Mars", "7": "Venus", "8": "Mercury", "10": "Mercury", "11": "Venus"},
            "house_cusps": [60.0, 90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0, 0.0, 30.0],
            "all_aspects": [
                {"planet1": "Moon", "planet2": "Saturn", "aspect": "Square", "applying": True, "orb": 0.5},
            ],
        }

        ids = _rule_ids(evaluate(extract_features(dashboard), self.rules))
        self.assertIn("violence_known_person_social_concealment_pattern", ids)


if __name__ == "__main__":
    unittest.main()
