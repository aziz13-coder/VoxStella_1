from __future__ import annotations

import unittest

from tests.horary_generic_gate_utils import load_generic_gate_corpus


class HoraryGenericGateCorpusTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus = load_generic_gate_corpus()

    def test_corpus_contains_expected_seed_size(self):
        self.assertGreaterEqual(len(self.corpus), 8)

    def test_every_entry_is_a_no_route_case(self):
        for entry in self.corpus:
            self.assertEqual(entry["current_expected_perfection_type"], "none")
            self.assertEqual(entry["question_family"], "occurrence")

    def test_corpus_contains_both_denial_controls_and_mixed_candidates(self):
        buckets = {entry["target_bucket"] for entry in self.corpus}
        self.assertIn("denial_secondary_balance", buckets)
        self.assertIn("mixed_or_inconclusive_secondary_balance", buckets)


if __name__ == "__main__":
    unittest.main()
