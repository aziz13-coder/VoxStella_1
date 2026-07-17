import json
import unittest
from pathlib import Path

from tests.forensic_case_corpus_utils import compare_case_to_forensic_output
from tests.forensic_case_replay_utils import make_forensic_replay_app


FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "tests"
    / "fixtures"
    / "forensic_worst_ex_ever_cases.json"
)

EXPECTED_CASE_IDS = [
    "worst_ex_geoffrey_paschel_2019_ipv_kidnapping",
    "worst_ex_alisha_canales_mcguire_2017_murder_for_hire",
    "worst_ex_rosa_hill_2009_custody_family_attack",
    "worst_ex_scott_freeman_2006_route_abduction_survivor",
]

EXPECTED_BACKLOG_IDS = [
    "worst_ex_wade_wilson_2019_double_homicide",
    "worst_ex_benjamin_foster_2023_ipv_captivity",
    "worst_ex_jerry_ramrattan_2009_rape_frameup",
    "worst_ex_joyce_pelzer_2011_2018_homicide_cycle",
]


def load_worst_ex_benchmark_cases():
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return payload, payload.get("cases") or [], payload.get("candidate_backlog") or []


def build_worst_ex_benchmark_query(case):
    query = dict(case.get("query") or {})
    datetime_local = query.pop("datetime_local", None)
    if datetime_local:
        query["datetime"] = datetime_local
    return {key: str(value) for key, value in query.items() if value is not None}


class ForensicWorstExEverBenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = make_forensic_replay_app()
        cls.client = cls.app.test_client()
        cls.fixture, cls.cases, cls.backlog = load_worst_ex_benchmark_cases()

    def test_fixture_tracks_runnable_and_holdout_cases(self):
        self.assertEqual([case["id"] for case in self.cases], EXPECTED_CASE_IDS)
        self.assertEqual([case["id"] for case in self.backlog], EXPECTED_BACKLOG_IDS)

        source_ids = {source["id"] for source in self.fixture.get("sources") or []}
        self.assertGreaterEqual(len(source_ids), 10)

        for case in self.cases:
            with self.subTest(case_id=case["id"]):
                self.assertIn(case["netflix_source_id"], source_ids)
                for source_id in case.get("event_source_ids") or []:
                    self.assertIn(source_id, source_ids)
                self.assertIn(case["event_anchor"]["metadata_confidence"], {"high", "medium"})
                self.assertTrue(case["expected_primary_axes"])
                self.assertTrue(case["expected_survivability"]["levels"])
                self.assertTrue(case["expected_survivability"]["bands"])
                self.assertIn(
                    case["current_comparison_baseline"]["status"],
                    {"aligned", "partially_aligned", "misaligned"},
                )

        for case in self.backlog:
            with self.subTest(backlog_case_id=case["id"]):
                self.assertNotIn("query", case)
                self.assertIn(case["netflix_source_id"], source_ids)
                self.assertTrue(case.get("hold_reason"))
                self.assertTrue(case.get("expected_primary_axes"))
                for source_id in case.get("event_source_ids") or []:
                    self.assertIn(source_id, source_ids)

    def test_live_route_comparison_matches_current_output_baseline(self):
        for case in self.cases:
            with self.subTest(case_id=case["id"]):
                response = self.client.get(
                    "/api/astro-clock/forensic",
                    query_string=build_worst_ex_benchmark_query(case),
                )
                self.assertEqual(response.status_code, 200)
                payload = response.get_json() or {}
                self.assertTrue(payload.get("success"))

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
                    query_string=build_worst_ex_benchmark_query(case),
                )
                self.assertEqual(response.status_code, 200)
                payload = response.get_json() or {}
                self.assertTrue(payload.get("success"))
                survivability = payload.get("survivability") or {}
                expected = case["expected_survivability"]

                self.assertIn(
                    survivability.get("level"),
                    set(expected["levels"]),
                    msg={
                        "case_id": case["id"],
                        "survivability": survivability,
                        "categories": payload.get("categories"),
                        "findings": [f.get("title") for f in (payload.get("findings") or [])[:8]],
                    },
                )
                self.assertIn(
                    survivability.get("outcome_band"),
                    set(expected["bands"]),
                    msg={
                        "case_id": case["id"],
                        "survivability": survivability,
                        "categories": payload.get("categories"),
                        "findings": [f.get("title") for f in (payload.get("findings") or [])[:8]],
                    },
                )


if __name__ == "__main__":
    unittest.main()
