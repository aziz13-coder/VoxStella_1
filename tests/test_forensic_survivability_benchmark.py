import unittest
from pathlib import Path

from tests.forensic_case_replay_utils import load_forensic_replay_cases, make_forensic_replay_app


REPO_ROOT = Path(__file__).resolve().parents[1]
JOURNALIST_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "forensic_external_journalist_abduction_candidates.json"
JOURNALIST_HOLDOUT_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "forensic_external_journalist_abduction_holdout_cases.json"
HOMICIDE_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "forensic_external_homicide_season3_cases.json"


class ForensicSurvivabilityBenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = make_forensic_replay_app()
        cls.client = cls.app.test_client()
        cls.journalist_cases = {
            case["id"]: case for case in load_forensic_replay_cases(JOURNALIST_FIXTURE)
        }
        cls.journalist_holdout_cases = {
            case["id"]: case for case in load_forensic_replay_cases(JOURNALIST_HOLDOUT_FIXTURE)
        }
        cls.homicide_cases = {
            case["id"]: case for case in load_forensic_replay_cases(HOMICIDE_FIXTURE)
        }

    def _route_survivability(self, case, query_override=None):
        anchor = (case.get("tested_anchors") or [None])[0]
        self.assertIsNotNone(anchor, msg=f"Case {case['id']} has no tested anchor")
        query = dict(anchor["query"])
        if query_override:
            query.update(query_override)
        response = self.client.get("/api/astro-clock/forensic", query_string=query)
        self.assertEqual(response.status_code, 200)
        payload = response.get_json() or {}
        self.assertTrue(payload.get("success"))
        self.assertIn("survivability", payload)
        return payload["survivability"], payload

    def test_resolved_journalist_abductions_stay_out_of_lower_survivability_band(self):
        cases = [
            ("rory_carroll_sadr_city_abduction", {}),
            ("giuliana_sgrena_baghdad_abduction", {"case_type": "adult_female"}),
            ("jill_carroll_adil_abduction", {"case_type": "adult_female"}),
            ("james_brandon_basra_abduction", {}),
        ]
        for case_id, query_override in cases:
            with self.subTest(case_id=case_id):
                survivability, payload = self._route_survivability(
                    self.journalist_cases[case_id],
                    query_override=query_override,
                )
                self.assertIn(
                    survivability.get("level"),
                    {"Moderate", "Higher"},
                    msg={
                        "case_id": case_id,
                        "survivability": survivability,
                        "categories": payload.get("categories"),
                        "findings": [f.get("title") for f in (payload.get("findings") or [])[:8]],
                    },
                )

    def test_clean_release_style_abductions_gain_release_favored_band(self):
        cases = [
            ("james_brandon_basra_abduction", self.journalist_cases, {}),
            ("meutya_hafid_ramadi_abduction_holdout", self.journalist_holdout_cases, {"case_type": "adult_female"}),
            ("romanian_journalists_jadriya_abduction_holdout", self.journalist_holdout_cases, {}),
        ]
        for case_id, case_map, query_override in cases:
            with self.subTest(case_id=case_id):
                survivability, payload = self._route_survivability(
                    case_map[case_id],
                    query_override=query_override,
                )
                self.assertEqual(
                    survivability.get("outcome_band"),
                    "release_favored",
                    msg={
                        "case_id": case_id,
                        "survivability": survivability,
                        "categories": payload.get("categories"),
                        "findings": [f.get("title") for f in (payload.get("findings") or [])[:8]],
                    },
                )

    def test_risk_loaded_abductions_stay_in_risk_loaded_survival_band(self):
        cases = [
            ("rory_carroll_sadr_city_abduction", self.journalist_cases, {}),
            ("giuliana_sgrena_baghdad_abduction", self.journalist_cases, {"case_type": "adult_female"}),
            ("jill_carroll_adil_abduction", self.journalist_cases, {"case_type": "adult_female"}),
            ("phil_sands_baghdad_abduction_holdout", self.journalist_holdout_cases, {}),
            ("alan_johnston_gaza_abduction", self.journalist_cases, {}),
        ]
        for case_id, case_map, query_override in cases:
            with self.subTest(case_id=case_id):
                survivability, payload = self._route_survivability(
                    case_map[case_id],
                    query_override=query_override,
                )
                self.assertEqual(
                    survivability.get("outcome_band"),
                    "risk_loaded_survival",
                    msg={
                        "case_id": case_id,
                        "survivability": survivability,
                        "categories": payload.get("categories"),
                        "findings": [f.get("title") for f in (payload.get("findings") or [])[:8]],
                    },
                )

    def test_clear_fatal_homicide_anchors_stay_in_lower_survivability_band(self):
        cases = [
            ("joey_comunale_party_monster", {}),
            ("sylvie_cachay_soho_horror", {"case_type": "adult_female"}),
            ("lourdes_gonzalez_your_eyes_or_your_life", {"case_type": "adult_female"}),
        ]
        for case_id, query_override in cases:
            with self.subTest(case_id=case_id):
                survivability, payload = self._route_survivability(
                    self.homicide_cases[case_id],
                    query_override=query_override,
                )
                self.assertEqual(
                    survivability.get("level"),
                    "Lower",
                    msg={
                        "case_id": case_id,
                        "survivability": survivability,
                        "categories": payload.get("categories"),
                        "findings": [f.get("title") for f in (payload.get("findings") or [])[:8]],
                    },
                )
                self.assertEqual(survivability.get("outcome_band"), "fatal_pressure_dominant")


if __name__ == "__main__":
    unittest.main()
