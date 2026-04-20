import unittest

from tests.horary_book_examples_utils import (
    load_book_replay_corpus,
    replay_book_case,
)


CORPUS = load_book_replay_corpus()
REPLAY_CACHE = {}


def replay_cached(case):
    cached = REPLAY_CACHE.get(case["id"])
    if cached is not None:
        return cached
    replayed = replay_book_case(case)
    REPLAY_CACHE[case["id"]] = replayed
    return replayed


class HoraryBookExamplesReplayTest(unittest.TestCase):
    def test_book_replay_corpus_has_expected_shape(self):
        self.assertGreaterEqual(len(CORPUS), 30)
        aligned = [case for case in CORPUS if case["source_alignment"]]
        mismatched = [case for case in CORPUS if not case["source_alignment"]]
        self.assertGreaterEqual(len(aligned), 27)
        self.assertEqual(len(mismatched), 3)

    def test_book_replay_cases_reconstruct_book_ascendants(self):
        for case in CORPUS:
            with self.subTest(case=case["id"]):
                replayed = replay_cached(case)
                self.assertEqual(replayed["ascendant_sign"], case["header_asc_sign"])
                self.assertLessEqual(
                    abs(float(replayed["ascendant_degree_in_sign"]) - float(case["header_asc_degree"])),
                    1.2,
                )

    def test_book_replay_cases_match_current_engine_observations(self):
        for case in CORPUS:
            with self.subTest(case=case["id"]):
                replayed = replay_cached(case)
                self.assertEqual(replayed["verdict"], case["engine_expected_verdict"])
                self.assertEqual(replayed["category"], case["engine_expected_category"])
                self.assertEqual(replayed["perfection_type"], case["engine_expected_perfection_type"])
                self.assertEqual(replayed["houses"], case["engine_expected_houses"])
                self.assertEqual(replayed["significator_houses"], case["engine_expected_significator_houses"])

                rules = replayed["reasoning"]
                for snippet in case.get("engine_expected_reasoning_contains", []):
                    self.assertTrue(
                        any(snippet in rule for rule in rules),
                        f"Expected engine reasoning snippet not found for {case['id']}: {snippet}",
                    )

    def test_source_aligned_cases_match_book_route(self):
        for case in CORPUS:
            if not case["source_alignment"]:
                continue
            with self.subTest(case=case["id"]):
                replayed = replay_cached(case)
                self.assertEqual(replayed["verdict"], case["book_expected_verdict"])
                self.assertEqual(replayed["category"], case["book_expected_category"])
                self.assertEqual(replayed["houses"], case["book_expected_primary_houses"])

    def test_known_disagreement_cases_are_explicitly_tracked(self):
        for case in CORPUS:
            if case["source_alignment"]:
                continue
            with self.subTest(case=case["id"]):
                replayed = replay_cached(case)
                self.assertTrue(case["mismatch_notes"])
                route_diff = replayed["houses"] != case["book_expected_primary_houses"]
                category_diff = replayed["category"] != case["book_expected_category"]
                verdict_diff = replayed["verdict"] != case["book_expected_verdict"]
                self.assertTrue(
                    route_diff or category_diff or verdict_diff,
                    f"Expected at least one tracked disagreement for {case['id']}",
                )

    def test_known_book_disagreements_are_explicitly_tracked(self):
        mismatched = [case["id"] for case in CORPUS if not case["source_alignment"]]
        self.assertEqual(
            mismatched,
            [
                "will_we_rent_the_house",
                "will_grandfather_survive_this_time",
                "will_barrett_win",
            ],
        )


if __name__ == "__main__":
    unittest.main()
