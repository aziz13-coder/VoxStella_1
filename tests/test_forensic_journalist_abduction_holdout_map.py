import unittest
from pathlib import Path

from tests.forensic_case_replay_utils import load_forensic_replay_cases, make_forensic_replay_app


HOLDOUT_FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "tests"
    / "fixtures"
    / "forensic_external_journalist_abduction_holdout_cases.json"
)


class JournalistAbductionHoldoutMapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = make_forensic_replay_app()
        cls.client = cls.app.test_client()
        cls.cases = {
            case["id"]: case for case in load_forensic_replay_cases(HOLDOUT_FIXTURE_PATH)
        }

    def test_holdout_cases_return_stable_abduction_map_origins_and_roles(self):
        for case_id, case in self.cases.items():
            with self.subTest(case_id=case_id):
                query = dict(case["tested_anchors"][0]["query"])
                query["abduction"] = "1"
                response = self.client.get("/api/astro-clock/forensic", query_string=query)
                self.assertEqual(response.status_code, 200, msg=case_id)
                payload = response.get_json() or {}
                self.assertTrue(payload.get("success"), msg=case_id)
                self.assertIn("abduction_map", payload, msg=case_id)

                abduction_map = payload["abduction_map"]
                map_validation = case.get("map_validation") or {}
                origin_lat, origin_lon = (
                    float(part.strip())
                    for part in case["tested_anchors"][0]["query"]["origin"].split(",", 1)
                )
                self.assertAlmostEqual(float(abduction_map["origin"]["lat"]), origin_lat, places=5)
                self.assertAlmostEqual(float(abduction_map["origin"]["lon"]), origin_lon, places=5)
                self.assertEqual(
                    abduction_map.get("origin_source"),
                    map_validation.get("origin_source_expected"),
                )

                roles = {item.get("role") for item in (abduction_map.get("bearings") or [])}
                self.assertTrue(roles, msg=case_id)
                self.assertIn("H9_ruler", roles, msg=f"{case_id} roles={sorted(roles)}")
                for role in map_validation.get("required_roles") or []:
                    self.assertIn(role, roles, msg=f"{case_id} roles={sorted(roles)}")
                self.assertEqual(
                    map_validation.get("geometry_status"),
                    "not_scored_due_to_missing_public_heading",
                )


if __name__ == "__main__":
    unittest.main()
