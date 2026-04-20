import io
import logging
import unittest
from pathlib import Path

from tests.forensic_case_replay_utils import (
    load_forensic_replay_cases,
    make_forensic_replay_app,
)


BENCHMARK_FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "tests"
    / "fixtures"
    / "forensic_external_journalist_abduction_candidates.json"
)


class JournalistAbductionMapBenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = make_forensic_replay_app()
        cls.client = cls.app.test_client()
        cls.cases = {
            case["id"]: case for case in load_forensic_replay_cases(BENCHMARK_FIXTURE_PATH)
        }

    def _fetch_case_payload(self, case_id):
        case = self.cases[case_id]
        query = dict(case["tested_anchors"][0]["query"])
        query["abduction"] = "1"
        response = self.client.get("/api/astro-clock/forensic", query_string=query)
        self.assertEqual(response.status_code, 200, msg=case_id)
        payload = response.get_json() or {}
        self.assertTrue(payload.get("success"), msg=case_id)
        self.assertIn("abduction_map", payload, msg=case_id)
        return case, payload

    def test_live_map_payload_matches_frozen_origin_and_role_expectations(self):
        for case_id in self.cases:
            with self.subTest(case_id=case_id):
                case, payload = self._fetch_case_payload(case_id)
                abduction_map = payload["abduction_map"]
                map_validation = case.get("map_validation") or {}

                origin_lat, origin_lon = (
                    float(part.strip())
                    for part in case["tested_anchors"][0]["query"]["origin"].split(",", 1)
                )
                self.assertAlmostEqual(
                    float(abduction_map["origin"]["lat"]), origin_lat, places=5
                )
                self.assertAlmostEqual(
                    float(abduction_map["origin"]["lon"]), origin_lon, places=5
                )
                self.assertEqual(
                    abduction_map.get("origin_source"),
                    map_validation.get("origin_source_expected"),
                )

                roles = {item.get("role") for item in (abduction_map.get("bearings") or [])}
                self.assertTrue(roles, msg=case_id)
                self.assertIn("H9_ruler", roles, msg=f"{case_id} roles={sorted(roles)}")
                for role in map_validation.get("required_roles") or []:
                    self.assertIn(role, roles, msg=f"{case_id} roles={sorted(roles)}")

    def test_current_six_case_set_skips_geometry_scoring_without_public_heading_data(self):
        for case_id, case in self.cases.items():
            with self.subTest(case_id=case_id):
                map_validation = case.get("map_validation") or {}
                self.assertEqual(
                    map_validation.get("geometry_status"),
                    "not_scored_due_to_missing_public_heading",
                )

    def test_live_map_requests_do_not_emit_moon_fallback_warning(self):
        logger = logging.getLogger("astro_clock_engine")
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        logger.addHandler(handler)
        original_propagate = logger.propagate
        logger.propagate = False
        logger.setLevel(logging.WARNING)
        try:
            for case_id in self.cases:
                with self.subTest(case_id=case_id):
                    stream.seek(0)
                    stream.truncate(0)
                    self._fetch_case_payload(case_id)
                    self.assertNotIn("Moon position not found in chart", stream.getvalue())
        finally:
            logger.removeHandler(handler)
            logger.propagate = original_propagate


if __name__ == "__main__":
    unittest.main()
