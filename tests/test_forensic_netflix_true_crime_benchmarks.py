import json
import unittest
from pathlib import Path

from tests.forensic_case_corpus_utils import compare_case_to_forensic_output
from tests.forensic_case_replay_utils import make_forensic_replay_app


FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "tests"
    / "fixtures"
    / "forensic_netflix_true_crime_2025_2026_cases.json"
)

EXPECTED_CASE_IDS = [
    "moriah_wilson_cycling_murder",
    "mackenzie_shirilla_the_crash",
    "elizabeth_smart_abduction",
    "ajike_owens_perfect_neighbor",
    "jason_corbett_deadly_american_marriage",
    "shannan_gilbert_lisk_911_anchor",
]

EXPECTED_SURVIVABILITY = {
    "moriah_wilson_cycling_murder": {
        "levels": {"Lower"},
        "bands": {"fatal_pressure_dominant"},
    },
    "mackenzie_shirilla_the_crash": {
        "levels": {"Lower"},
        "bands": {"fatal_pressure_dominant"},
    },
    "elizabeth_smart_abduction": {
        "levels": {"Moderate", "Higher"},
        "bands": {"risk_loaded_survival", "release_favored"},
    },
    "ajike_owens_perfect_neighbor": {
        "levels": {"Lower"},
        "bands": {"fatal_pressure_dominant"},
    },
    "jason_corbett_deadly_american_marriage": {
        "levels": {"Lower"},
        "bands": {"fatal_pressure_dominant"},
    },
    "shannan_gilbert_lisk_911_anchor": {
        "levels": {"Moderate", "Lower"},
        "bands": {"risk_loaded_survival", "fatal_pressure_dominant"},
    },
}


def load_netflix_benchmark_cases():
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return payload, payload.get("cases") or []


def build_netflix_benchmark_query(case):
    query = dict(case.get("query") or {})
    datetime_local = query.pop("datetime_local", None)
    if datetime_local:
        query["datetime"] = datetime_local
    return {key: str(value) for key, value in query.items() if value is not None}


class ForensicNetflixTrueCrimeBenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = make_forensic_replay_app()
        cls.client = cls.app.test_client()
        cls.fixture, cls.cases = load_netflix_benchmark_cases()

    def test_fixture_tracks_six_recent_netflix_cases(self):
        self.assertEqual([case["id"] for case in self.cases], EXPECTED_CASE_IDS)
        source_ids = {source["id"] for source in self.fixture.get("sources") or []}
        self.assertGreaterEqual(len(source_ids), 10)
        for case in self.cases:
            with self.subTest(case_id=case["id"]):
                self.assertIn(case["netflix_source_id"], source_ids)
                for source_id in case.get("event_source_ids") or []:
                    self.assertIn(source_id, source_ids)
                self.assertIn(case["event_anchor"]["metadata_confidence"], {"high", "medium"})
                self.assertTrue(case["expected_primary_axes"])
                self.assertIn(
                    case["current_comparison_baseline"]["status"],
                    {"aligned", "partially_aligned", "misaligned"},
                )

    def test_live_route_comparison_matches_current_output_baseline(self):
        for case in self.cases:
            with self.subTest(case_id=case["id"]):
                response = self.client.get(
                    "/api/astro-clock/forensic",
                    query_string=build_netflix_benchmark_query(case),
                )
                self.assertEqual(response.status_code, 200)
                payload = response.get_json() or {}
                self.assertTrue(payload.get("success"))
                self.assertTrue(payload.get("survivability"))

                comparison = compare_case_to_forensic_output(case, payload)
                self.assertEqual(
                    comparison,
                    case["current_comparison_baseline"],
                    msg=(
                        f"{case['id']} comparison={comparison} "
                        f"categories={payload.get('categories')} "
                        f"findings={[f.get('title') for f in (payload.get('findings') or [])[:8]]}"
                    ),
                )

    def test_survivability_tracks_real_event_outcome_direction(self):
        for case in self.cases:
            with self.subTest(case_id=case["id"]):
                response = self.client.get(
                    "/api/astro-clock/forensic",
                    query_string=build_netflix_benchmark_query(case),
                )
                self.assertEqual(response.status_code, 200)
                payload = response.get_json() or {}
                self.assertTrue(payload.get("success"))
                survivability = payload.get("survivability") or {}
                expected = EXPECTED_SURVIVABILITY[case["id"]]

                self.assertIn(
                    survivability.get("level"),
                    expected["levels"],
                    msg={
                        "case_id": case["id"],
                        "survivability": survivability,
                        "categories": payload.get("categories"),
                        "findings": [f.get("title") for f in (payload.get("findings") or [])[:8]],
                    },
                )
                self.assertIn(
                    survivability.get("outcome_band"),
                    expected["bands"],
                    msg={
                        "case_id": case["id"],
                        "survivability": survivability,
                        "categories": payload.get("categories"),
                        "findings": [f.get("title") for f in (payload.get("findings") or [])[:8]],
                    },
                )


if __name__ == "__main__":
    unittest.main()
